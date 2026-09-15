/* SD_TLSSRV.C
 * TLS for the SD API transport: the server's relay process.
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
 * START-HISTORY:
 * 15 Sep 26 dm The certificate's name is built here instead of being borrowed
 *              from the certificate: OpenSSL 4 returns X509_get_subject_name()
 *              const, and the first build against real libssl-dev headers
 *              (4.0.1) warned.  gplbld/test-tls-relay.py is the check.
 * 15 Sep 26 dm S.19: created.  See sd_tls.h.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * sd_tls_relay_start() is called by start_connection() with descriptor 0 the
 * client's connection.  It forks:
 *
 *   the relay    keeps the connection, loads the server identity, stops being
 *                root, does the TLS handshake, sends sd the 32-byte channel
 *                binding, then copies bytes both ways until either side ends.
 *   sd           gets one end of a socketpair as descriptors 0 and 1, reads
 *                the binding, and carries on exactly as before.
 *
 * ORDER IN THE RELAY IS THE SECURITY PROPERTY: the identity file is read as
 * root, and root is given up before one byte from the network is parsed.
 *
 * THE IDENTITY is one file, <identity_dir>/api.pem, holding the private key
 * and a self-signed certificate.  One file, written to a temporary name and
 * renamed, so two first connections at once cannot leave a key beside the
 * other's certificate.  It is refused unless it and its directory belong to
 * the process's own user and nobody else can read the file.
 *
 * END-DESCRIPTION
 */

#include "sd_tls.h"

#include <stdbool.h>                  /* not from sd_tls.h - see there */

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <pwd.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <syslog.h>
#include <unistd.h>

#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rand.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>

#define RELAY_BUFFER 16384
#define RELAY_EXIT_IDENTITY 2
#define RELAY_EXIT_PRIVILEGE 3
#define RELAY_EXIT_HANDSHAKE 4
#define RELAY_EXIT_BINDING 5

static unsigned char server_binding[SD_TLS_BINDING_BYTES];
static bool have_binding = false;

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

/* ======================================================================
   The identity                                                           */

static bool private_to_me(const struct stat* st, bool is_dir) {
  if (st->st_uid != geteuid())
    return false;
  if (is_dir)
    return S_ISDIR(st->st_mode) && (st->st_mode & 022) == 0;
  return S_ISREG(st->st_mode) && (st->st_mode & 077) == 0;
}

static bool create_identity(const char* path, EVP_PKEY** pkey_out,
                            X509** cert_out, char* errmsg, size_t errlen) {
  EVP_PKEY* pkey = NULL;
  X509* cert = NULL;
  X509_NAME* name = NULL;
  unsigned char serial[8];
  char tmp[4096];
  int fd = -1;
  FILE* fp = NULL;
  bool ok = false;

  pkey = EVP_PKEY_Q_keygen(NULL, NULL, "ED25519");
  cert = X509_new();
  if (pkey == NULL || cert == NULL) {
    sd_tls_error_text("cannot generate the server key", errmsg, errlen);
    goto done;
  }

  if (RAND_bytes(serial, sizeof(serial)) != 1) {
    sd_tls_error_text("cannot generate a serial number", errmsg, errlen);
    goto done;
  }
  serial[0] &= 0x7F;
  {
    BIGNUM* bn = BN_bin2bn(serial, sizeof(serial), NULL);
    bool set = bn != NULL &&
               BN_to_ASN1_INTEGER(bn, X509_get_serialNumber(cert)) != NULL;
    BN_free(bn);
    if (!set) {
      sd_tls_error_text("cannot set the serial number", errmsg, errlen);
      goto done;
    }
  }

  /* A NAME OF OUR OWN, NOT THE CERTIFICATE'S.  This read the certificate's
     empty name and filled it in, which OpenSSL 3 allowed and OpenSSL 4 does
     not: X509_get_subject_name() now returns a const pointer, and the first
     build against real libssl-dev headers (4.0.1, installed by this release's
     own installer change) warned -Wdiscarded-qualifiers here.  Building the
     name and setting it works on both, because X509_set_subject_name and
     X509_set_issuer_name each COPY it - which is why it is freed at done:,
     on the success path as well.  Behaviour is unchanged: the same CN, and
     issuer equal to subject, as a self-signed certificate needs.  */
  name = X509_NAME_new();
  if (name == NULL) {
    sd_tls_error_text("cannot build the certificate name", errmsg, errlen);
    goto done;
  }
  if (X509_set_version(cert, 2) != 1 ||
      X509_gmtime_adj(X509_getm_notBefore(cert), -86400L) == NULL ||
      X509_time_adj_ex(X509_getm_notAfter(cert), 36500, 0, NULL) == NULL ||
      X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                                 (const unsigned char*)"SD Core API", -1, -1,
                                 0) != 1 ||
      X509_set_subject_name(cert, name) != 1 ||
      X509_set_issuer_name(cert, name) != 1 ||
      X509_set_pubkey(cert, pkey) != 1 ||
      X509_sign(cert, pkey, NULL) <= 0) {
    sd_tls_error_text("cannot build the server certificate", errmsg, errlen);
    goto done;
  }

  if (snprintf(tmp, sizeof(tmp), "%s.XXXXXX", path) >= (int)sizeof(tmp)) {
    snprintf(errmsg, errlen, "identity path too long");
    goto done;
  }
  fd = mkstemp(tmp);               /* mode 0600 */
  if (fd < 0) {
    snprintf(errmsg, errlen, "cannot create %.300s: %s", tmp, strerror(errno));
    goto done;
  }
  fp = fdopen(fd, "w");
  if (fp == NULL) {
    snprintf(errmsg, errlen, "cannot open %.300s: %s", tmp, strerror(errno));
    close(fd);
    unlink(tmp);
    goto done;
  }
  if (PEM_write_PrivateKey(fp, pkey, NULL, NULL, 0, NULL, NULL) != 1 ||
      PEM_write_X509(fp, cert) != 1 || fflush(fp) != 0 ||
      fsync(fileno(fp)) != 0) {
    sd_tls_error_text("cannot write the server identity", errmsg, errlen);
    fclose(fp);
    unlink(tmp);
    goto done;
  }
  fclose(fp);
  if (rename(tmp, path) != 0) {
    snprintf(errmsg, errlen, "cannot rename %.300s: %s", tmp, strerror(errno));
    unlink(tmp);
    goto done;
  }

  syslog(LOG_INFO, "SD API TLS: created server identity %s", path);
  ok = true;

done:
  X509_NAME_free(name);           /* the certificate holds its own copy */
  if (ok) {
    *pkey_out = pkey;
    *cert_out = cert;
  } else {
    EVP_PKEY_free(pkey);
    X509_free(cert);
  }
  return ok;
}

static bool load_identity(SSL_CTX* ctx, const char* dir, char* errmsg,
                          size_t errlen) {
  char path[4096];
  struct stat st;
  EVP_PKEY* pkey = NULL;
  X509* cert = NULL;
  int fd;
  bool ok = false;

  if (snprintf(path, sizeof(path), "%s/%s", dir, SD_TLS_IDENTITY_FILE) >=
      (int)sizeof(path)) {
    snprintf(errmsg, errlen, "identity path too long");
    return false;
  }

  if (mkdir(dir, 0700) != 0 && errno != EEXIST) {
    snprintf(errmsg, errlen, "cannot create %s: %s", dir, strerror(errno));
    return false;
  }
  if (lstat(dir, &st) != 0 || !private_to_me(&st, true)) {
    snprintf(errmsg, errlen,
             "%s is not a directory owned by uid %d and closed to others",
             dir, (int)geteuid());
    return false;
  }

  fd = open(path, O_RDONLY | O_NOFOLLOW);
  if (fd < 0 && errno == ENOENT) {
    if (!create_identity(path, &pkey, &cert, errmsg, errlen))
      return false;
  } else if (fd < 0) {
    snprintf(errmsg, errlen, "cannot open %.300s: %s", path, strerror(errno));
    return false;
  } else {
    FILE* fp;

    if (fstat(fd, &st) != 0 || !private_to_me(&st, false)) {
      snprintf(errmsg, errlen,
               "%.300s refused: it must be a file owned by uid %d that nobody "
               "else can read", path, (int)geteuid());
      close(fd);
      return false;
    }
    fp = fdopen(fd, "r");
    if (fp == NULL) {
      close(fd);
      snprintf(errmsg, errlen, "cannot read %.300s", path);
      return false;
    }
    pkey = PEM_read_PrivateKey(fp, NULL, NULL, NULL);
    cert = PEM_read_X509(fp, NULL, NULL, NULL);
    fclose(fp);
    if (pkey == NULL || cert == NULL) {
      sd_tls_error_text("cannot parse the server identity", errmsg, errlen);
      goto done;
    }
  }

  if (SSL_CTX_use_certificate(ctx, cert) != 1 ||
      SSL_CTX_use_PrivateKey(ctx, pkey) != 1 ||
      SSL_CTX_check_private_key(ctx) != 1) {
    sd_tls_error_text("the server identity does not load", errmsg, errlen);
    goto done;
  }
  ok = true;

done:
  EVP_PKEY_free(pkey);
  X509_free(cert);
  return ok;
}

/* ======================================================================
   drop_privilege()  -  root -> nobody, for good                          */

static bool drop_privilege(char* errmsg, size_t errlen) {
  struct passwd* pw;

  if (geteuid() != 0)
    return true;   /* nothing to give up; the caller is not root */

  pw = getpwnam("nobody");
  if (pw == NULL) {
    snprintf(errmsg, errlen, "no 'nobody' user to run the TLS relay as");
    return false;
  }
  if (chdir("/") != 0 || setgroups(0, NULL) != 0 ||
      setgid(pw->pw_gid) != 0 || setuid(pw->pw_uid) != 0) {
    snprintf(errmsg, errlen, "cannot become nobody: %s", strerror(errno));
    return false;
  }
  if (setuid(0) == 0 || geteuid() == 0) {
    snprintf(errmsg, errlen, "root could be regained after the drop");
    return false;
  }
  (void)prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
  return true;
}

/* ======================================================================
   relay()  -  copy both ways until either side ends                      */

static bool ssl_write_all(SSL* ssl, const char* p, int len) {
  while (len > 0) {
    int n = SSL_write(ssl, p, len);
    int e;

    if (n > 0) {
      p += n;
      len -= n;
      continue;
    }
    e = SSL_get_error(ssl, n);
    if (e == SSL_ERROR_WANT_READ || e == SSL_ERROR_WANT_WRITE)
      continue;
    if (e == SSL_ERROR_SYSCALL && errno == EINTR)
      continue;
    return false;
  }
  return true;
}

static void relay(SSL* ssl, int net_fd, int app_fd) {
  char buf[RELAY_BUFFER];

  for (;;) {
    struct pollfd p[2];

    p[0].fd = net_fd;
    p[0].events = POLLIN;
    p[0].revents = 0;
    p[1].fd = app_fd;
    p[1].events = POLLIN;
    p[1].revents = 0;

    /* Decrypted bytes OpenSSL already holds are invisible to poll(). */
    if (SSL_pending(ssl) > 0) {
      p[0].revents = POLLIN;
    } else if (poll(p, 2, -1) < 0) {
      if (errno == EINTR)
        continue;
      return;
    }

    if (p[0].revents & (POLLIN | POLLHUP | POLLERR)) {
      int n = SSL_read(ssl, buf, sizeof(buf));
      if (n <= 0) {
        int e = SSL_get_error(ssl, n);
        if (e == SSL_ERROR_WANT_READ || e == SSL_ERROR_WANT_WRITE)
          continue;
        return;
      }
      if (!write_all(app_fd, buf, (size_t)n))
        return;
    }

    if (p[1].revents & (POLLIN | POLLHUP | POLLERR)) {
      ssize_t n = read(app_fd, buf, sizeof(buf));
      if (n < 0 && errno == EINTR)
        continue;
      if (n <= 0)
        return;
      if (!ssl_write_all(ssl, buf, (int)n))
        return;
    }
  }
}

static void relay_process(const char* dir, int timeout_ms, int app_fd) {
  char err[512];
  SSL_CTX* ctx;
  SSL* ssl;
  unsigned char binding[SD_TLS_BINDING_BYTES];
  const int net_fd = 0;

  signal(SIGPIPE, SIG_IGN);
  signal(SIGCHLD, SIG_DFL);
  signal(SIGHUP, SIG_DFL);
  signal(SIGTERM, SIG_DFL);
  signal(SIGINT, SIG_DFL);
  close(1);                        /* the same connection as 0 */

  ctx = SSL_CTX_new(TLS_server_method());
  if (ctx == NULL || !sd_tls_restrict_ctx(ctx)) {
    sd_tls_error_text("cannot set up TLS", err, sizeof(err));
    syslog(LOG_ERR, "SD API TLS: %s", err);
    _exit(RELAY_EXIT_IDENTITY);
  }
  /* No resumption: every session is a full handshake with its own binding. */
  SSL_CTX_set_num_tickets(ctx, 0);
  SSL_CTX_set_session_cache_mode(ctx, SSL_SESS_CACHE_OFF);

  if (!load_identity(ctx, dir, err, sizeof(err))) {
    syslog(LOG_ERR, "SD API TLS: %s", err);
    _exit(RELAY_EXIT_IDENTITY);
  }

  if (!drop_privilege(err, sizeof(err))) {
    syslog(LOG_ERR, "SD API TLS: %s", err);
    _exit(RELAY_EXIT_PRIVILEGE);
  }

  ssl = SSL_new(ctx);
  if (ssl == NULL || SSL_set_fd(ssl, net_fd) != 1) {
    sd_tls_error_text("cannot set up TLS", err, sizeof(err));
    syslog(LOG_ERR, "SD API TLS: %s", err);
    _exit(RELAY_EXIT_HANDSHAKE);
  }

  if (!sd_tls_handshake(ssl, net_fd, timeout_ms, true, err, sizeof(err))) {
    syslog(LOG_INFO, "SD API TLS: connection refused: %s", err);
    _exit(RELAY_EXIT_HANDSHAKE);
  }

  if (!sd_tls_export_binding(ssl, binding) ||
      !write_all(app_fd, binding, sizeof(binding))) {
    syslog(LOG_ERR, "SD API TLS: cannot hand over the channel binding");
    _exit(RELAY_EXIT_BINDING);
  }

  relay(ssl, net_fd, app_fd);
  (void)SSL_shutdown(ssl);
  _exit(0);
}

/* ======================================================================
   sd_tls_relay_start()                                                   */

int sd_tls_relay_start(const char* identity_dir, int timeout_ms,
                       char* errmsg, size_t errlen) {
  int sp[2];
  pid_t pid;
  size_t got = 0;

  /* STDERR MAY BE THE CONNECTION TOO.  sdclient@.service sets only
     StandardInput=socket, and systemd's StandardOutput/StandardError default
     to inherit - so descriptor 2 is the client's socket.  Left there, anything
     either process wrote to stderr would reach the client as plaintext in the
     middle of the TLS stream, and sd would hold the connection open after the
     relay ended.  Pointed at /dev/null before the fork, for both processes;
     the relay reports through syslog. */
  {
    struct stat s0;
    struct stat s2;

    if (fstat(0, &s0) == 0 && fstat(2, &s2) == 0 && s0.st_dev == s2.st_dev &&
        s0.st_ino == s2.st_ino) {
      int null_fd = open("/dev/null", O_WRONLY);
      if (null_fd < 0 || dup2(null_fd, 2) < 0) {
        snprintf(errmsg, errlen, "cannot detach stderr from the connection");
        return false;
      }
      if (null_fd != 2)
        close(null_fd);
    }
  }

  if (socketpair(AF_UNIX, SOCK_STREAM, 0, sp) != 0) {
    snprintf(errmsg, errlen, "socketpair: %s", strerror(errno));
    return false;
  }

  pid = fork();
  if (pid < 0) {
    snprintf(errmsg, errlen, "fork: %s", strerror(errno));
    close(sp[0]);
    close(sp[1]);
    return false;
  }
  if (pid == 0) {
    close(sp[0]);
    relay_process(identity_dir, timeout_ms, sp[1]);
    _exit(1);                      /* not reached */
  }

  /* sd: its connection becomes the socketpair.  Closing its copies of the
     network descriptor matters - when the relay ends, the client must see
     the connection close, not a socket sd still holds open. */
  close(sp[1]);
  if (dup2(sp[0], 0) < 0 || dup2(sp[0], 1) < 0) {
    snprintf(errmsg, errlen, "dup2: %s", strerror(errno));
    return false;
  }
  if (sp[0] > 1)
    close(sp[0]);

  /* The binding is the relay's first 32 bytes.  End of file here is every
     refusal: no identity, a failed handshake, a client that never spoke. */
  while (got < SD_TLS_BINDING_BYTES) {
    struct pollfd p;
    ssize_t n;
    int pr;

    p.fd = 0;
    p.events = POLLIN;
    p.revents = 0;
    pr = poll(&p, 1, timeout_ms + 5000);
    if (pr < 0 && errno == EINTR)
      continue;
    if (pr <= 0) {
      snprintf(errmsg, errlen, "TLS relay did not answer");
      return false;
    }
    n = read(0, server_binding + got, SD_TLS_BINDING_BYTES - got);
    if (n < 0 && errno == EINTR)
      continue;
    if (n <= 0) {
      snprintf(errmsg, errlen,
               "TLS relay ended before the session started (see syslog)");
      return false;
    }
    got += (size_t)n;
  }

  have_binding = true;
  return true;
}

const unsigned char* sd_tls_server_binding(void) {
  return have_binding ? server_binding : NULL;
}

/* END-CODE */
