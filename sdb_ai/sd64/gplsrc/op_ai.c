/* OP_AI.C
 * The kernel's side of the in-SD AI helper (S.69 step 2; plan .claude/plan-ai-step2.md).
 * Copyright (c) 2026, SD Core for Linux.  This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License, version 3 or later.
 *
 * START-HISTORY:
 * 23 Oct 26 dm  New.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * KERNEL(K$AI.START, system : FM : maxtokens : FM : prompt)   sends one request to the helper (gplbld/sd-ai) on its Unix socket and returns at once.
 * KERNEL(K$AI.POLL, 0)       asks whether the answer is in.
 * KERNEL(K$AI.CANCEL, 0)     gives the request up.
 * KERNEL(K$AI.STATUS, 0)     asks the helper for its status line (provider, model, key set, whether THIS caller's uid is in the AI group) and waits at most two seconds.
 *
 *   Answers are strings:   START   OK   |  ERR : FM : busy | toobig | internal | nohelper | bad
 *                          POLL    W (waiting)  |  D : FM : the helper's reply line (JSON)  |  E : FM : nohelper | timeout | toobig | closed | none
 *                          CANCEL  OK
 *                          STATUS  D : FM : the helper's status line  |  E : FM : nohelper | timeout | internal
 *
 * THIS IS A TRANSPORT AND NOTHING ELSE.  It decides nothing about who may use the AI: the helper does, from the uid it reads off the connection (SO_PEERCRED), so a caller
 * that skips this file and talks to the socket itself gets the same answer.  What this file adds is what only the kernel can promise:
 *   - only a $internal program may call it (the library and the verbs; an account's own program cannot), and a call from any other program is refused with ERR internal;
 *   - the request that can be sent is an ask and nothing else (the helper's administrator operations are not reachable from here), built here from the three
 *     arguments: every byte of text is escaped, and a byte above 127 becomes ? (English only; nothing is sent that is not plain ASCII);
 *   - THE AUDIT LINE IS WRITTEN HERE, BEFORE THE CONNECTION IS MADE:  ai request account=<account> program=<the running program> bytes.out=<n>  (audit_message stamps
 *     the user and the process itself), so a crash or a refusal still leaves the record, and no caller can choose what is written;
 *   - one request at a time per process, a total limit of 340 seconds, a reply of at most 512 KB, and nothing left open when the request is over.
 * The socket is /run/sd-ai/sock; SD_AI_SOCKET in the environment names another (the tests; the product never sets it, and it can only point a session at a socket
 * of its own user's choosing: the helper at the other end of the real one still asks who is calling).
 *
 * END-DESCRIPTION
 */

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#include "sd.h"
#include "header.h"
#include "keys.h"

#define AI_DEFAULT_SOCKET "/run/sd-ai/sock"
#define AI_REQ_MAX 262144 /* system + prompt, in bytes, as the caller gave them */
#define AI_REPLY_MAX 524288
#define AI_DEADLINE 340 /* seconds, from the start of a request */
#define AI_CONNECT_MS 2000

Private struct {
  int fd;
  bool active;
  char* buf;
  size_t len;
  size_t cap;
  time_t started;
} ai = {-1, 0, NULL, 0, 0, 0};

Private void ai_reset(void) {
  if (ai.fd >= 0)
    close(ai.fd);
  ai.fd = -1;
  ai.active = 0;
  if (ai.buf != NULL)
    free(ai.buf);
  ai.buf = NULL;
  ai.len = ai.cap = 0;
}

Private const char* ai_socket_path(void) {
  const char* p = getenv("SD_AI_SOCKET");
  struct sockaddr_un probe;

  if ((p != NULL) && (*p != '\0') && (strlen(p) < sizeof(probe.sun_path)))
    return p;
  return AI_DEFAULT_SOCKET;
}

/* Connect to the helper's socket; the descriptor is non-blocking.  -1 when there is no helper to talk to. */
Private int ai_connect(void) {
  struct sockaddr_un addr;
  int fd;
  const char* path = ai_socket_path();

  fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
  if (fd < 0)
    return -1;
  memset(&addr, 0, sizeof(addr));
  addr.sun_family = AF_UNIX;
  strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
  if (connect(fd, (struct sockaddr*)&addr, sizeof(addr)) != 0) {
    close(fd);
    return -1;
  }
  (void)fcntl(fd, F_SETFL, fcntl(fd, F_GETFL, 0) | O_NONBLOCK);
  return fd;
}

/* Send all of buf; 0 if the helper does not take it within two seconds a piece. */
Private bool ai_send_all(int fd, const char* buf, size_t len) {
  size_t done = 0;
  ssize_t n;
  struct pollfd pfd;

  while (done < len) {
    n = write(fd, buf + done, len - done);
    if (n > 0) {
      done += (size_t)n;
      continue;
    }
    if ((n < 0) && (errno != EAGAIN) && (errno != EWOULDBLOCK) && (errno != EINTR))
      return 0;
    pfd.fd = fd;
    pfd.events = POLLOUT;
    pfd.revents = 0;
    if (poll(&pfd, 1, AI_CONNECT_MS) <= 0)
      return 0;
  }
  return 1;
}

/* Append to out the JSON string for in[0..n): quotes, backslash and control characters escaped, a byte above 127 written as ?.  Returns the new length. */
Private size_t ai_json_string(char* out, size_t pos, const char* in, size_t n) {
  static const char hex[] = "0123456789abcdef";
  size_t i;

  out[pos++] = '"';
  for (i = 0; i < n; i++) {
    u_char c = (u_char)in[i];
    if (c == '"' || c == '\\') {
      out[pos++] = '\\';
      out[pos++] = (char)c;
    } else if (c == '\n') {
      out[pos++] = '\\';
      out[pos++] = 'n';
    } else if (c == '\t') {
      out[pos++] = '\\';
      out[pos++] = 't';
    } else if (c < 32 || c == 127) {
      out[pos++] = '\\';
      out[pos++] = 'u';
      out[pos++] = '0';
      out[pos++] = '0';
      out[pos++] = hex[c >> 4];
      out[pos++] = hex[c & 15];
    } else if (c >= 128) {
      out[pos++] = '?';
    } else {
      out[pos++] = (char)c;
    }
  }
  out[pos++] = '"';
  return pos;
}

Private void ai_answer(const char* a, const char* b, DESCRIPTOR* result) {
  char* s;
  size_t n = strlen(a) + 1 + ((b != NULL) ? strlen(b) : 0) + 1;

  s = (char*)malloc(n);
  if (s == NULL) {
    k_put_c_string("E\376none", result);
    return;
  }
  strcpy(s, a);
  if (b != NULL) {
    size_t l = strlen(s);
    s[l] = (char)FIELD_MARK;
    strcpy(s + l + 1, b);
  }
  k_put_c_string(s, result);
  free(s);
}

Private void ai_start(DESCRIPTOR* descr, DESCRIPTOR* result) {
  char* arg;
  char* system;
  char* prompt;
  char* maxt;
  char* p;
  char* req;
  const char* pname;
  size_t cap;
  size_t pos;
  int n;
  int maxtokens = 0;
  char audit[200];

  if (ai.active) {
    ai_answer("ERR", "busy", result);
    return;
  }
  arg = (char*)malloc(AI_REQ_MAX + 64);
  if (arg == NULL) {
    ai_answer("ERR", "bad", result);
    return;
  }
  n = k_get_c_string(descr, arg, AI_REQ_MAX + 32);
  if (n < 0 || n > AI_REQ_MAX) {
    free(arg);
    ai_answer("ERR", "toobig", result);
    return;
  }
  arg[n] = '\0';
  /* system : FM : maxtokens : FM : prompt.  The prompt is last so that a mark byte inside it cannot move a field: the first two marks cut, the rest is the prompt. */
  system = arg;
  p = strchr(system, FIELD_MARK);
  if (p == NULL) {
    free(arg);
    ai_answer("ERR", "bad", result);
    return;
  }
  *p = '\0';
  maxt = p + 1;
  p = strchr(maxt, FIELD_MARK);
  if (p == NULL) {
    free(arg);
    ai_answer("ERR", "bad", result);
    return;
  }
  *p = '\0';
  prompt = p + 1;
  maxtokens = atoi(maxt);
  if (maxtokens < 1)
    maxtokens = 1;
  if (maxtokens > 100000)
    maxtokens = 100000;

  /* THE AUDIT LINE: before anything is sent, from the kernel's own state.  It names the account and the program that called, and the size; never the text. */
  /* The audit line gives the name a person knows: a catalogued program is named $name and one run from a file by its whole path, so the $ and the directory are left off. */
  pname = ProgramName(c_base);
  if (strrchr(pname, '/') != NULL)
    pname = strrchr(pname, '/') + 1;
  if (*pname == '$')
    pname++;
  snprintf(audit, sizeof(audit), "ai request account=%s program=%s bytes.out=%d", account(), pname, (int)(strlen(system) + strlen(prompt)));
  audit_message(audit);

  cap = (6 * (strlen(system) + strlen(prompt))) + 256;
  req = (char*)malloc(cap);
  if (req == NULL) {
    free(arg);
    ai_answer("ERR", "bad", result);
    return;
  }
  pos = 0;
  pos += (size_t)sprintf(req + pos, "{\"v\":1,\"op\":\"ask\",\"system\":");
  pos = ai_json_string(req, pos, system, strlen(system));
  pos += (size_t)sprintf(req + pos, ",\"prompt\":");
  pos = ai_json_string(req, pos, prompt, strlen(prompt));
  pos += (size_t)sprintf(req + pos, ",\"maxtokens\":%d}\n", maxtokens);
  free(arg);

  ai.fd = ai_connect();
  if (ai.fd < 0) {
    free(req);
    ai_answer("ERR", "nohelper", result);
    return;
  }
  if (!ai_send_all(ai.fd, req, pos)) {
    free(req);
    ai_reset();
    ai_answer("ERR", "nohelper", result);
    return;
  }
  free(req);
  ai.active = 1;
  ai.started = time(NULL);
  ai.len = 0;
  ai_answer("OK", NULL, result);
}

Private void ai_poll(DESCRIPTOR* result) {
  struct pollfd pfd;
  ssize_t n;
  char* nl;

  if (!ai.active) {
    ai_answer("E", "none", result);
    return;
  }
  if ((time(NULL) - ai.started) > AI_DEADLINE) {
    ai_reset();
    ai_answer("E", "timeout", result);
    return;
  }
  for (;;) {
    pfd.fd = ai.fd;
    pfd.events = POLLIN;
    pfd.revents = 0;
    if (poll(&pfd, 1, 0) <= 0)
      break;
    if ((ai.cap - ai.len) < 4096) {
      size_t ncap = (ai.cap == 0) ? 16384 : (ai.cap * 2);
      char* nb;
      if (ncap > (AI_REPLY_MAX + 16384)) {
        ai_reset();
        ai_answer("E", "toobig", result);
        return;
      }
      nb = (char*)realloc(ai.buf, ncap);
      if (nb == NULL) {
        ai_reset();
        ai_answer("E", "toobig", result);
        return;
      }
      ai.buf = nb;
      ai.cap = ncap;
    }
    n = read(ai.fd, ai.buf + ai.len, ai.cap - ai.len - 1);
    if (n > 0) {
      ai.len += (size_t)n;
      ai.buf[ai.len] = '\0';
      if (strchr(ai.buf, '\n') != NULL)
        break;
      continue;
    }
    if ((n < 0) && ((errno == EAGAIN) || (errno == EWOULDBLOCK) || (errno == EINTR)))
      break;
    break; /* end of file or an error: judged below from what was read */
  }
  if (ai.buf != NULL && ai.len > 0) {
    ai.buf[ai.len] = '\0';
    nl = strchr(ai.buf, '\n');
    if (nl != NULL) {
      *nl = '\0';
      ai_answer("D", ai.buf, result);
      ai_reset();
      return;
    }
  }
  /* no complete line yet: still waiting, unless the helper has hung up */
  pfd.fd = ai.fd;
  pfd.events = POLLIN | POLLHUP;
  pfd.revents = 0;
  if ((poll(&pfd, 1, 0) > 0) && (pfd.revents & POLLHUP) && !(pfd.revents & POLLIN)) {
    ai_reset();
    ai_answer("E", "closed", result);
    return;
  }
  ai_answer("W", NULL, result);
}

/* The helper's status line: a request of its own, answered or given up within two seconds. */
Private void ai_status(DESCRIPTOR* result) {
  static const char req[] = "{\"v\":1,\"op\":\"status\"}\n";
  char buf[65536];
  size_t len = 0;
  int fd;
  struct pollfd pfd;
  ssize_t n;
  char* nl;
  int waited = 0;

  fd = ai_connect();
  if (fd < 0) {
    ai_answer("E", "nohelper", result);
    return;
  }
  if (!ai_send_all(fd, req, sizeof(req) - 1)) {
    close(fd);
    ai_answer("E", "nohelper", result);
    return;
  }
  while (waited < 2000 && len < sizeof(buf) - 1) {
    pfd.fd = fd;
    pfd.events = POLLIN;
    pfd.revents = 0;
    if (poll(&pfd, 1, 100) <= 0) {
      waited += 100;
      continue;
    }
    n = read(fd, buf + len, sizeof(buf) - 1 - len);
    if (n <= 0)
      break;
    len += (size_t)n;
    buf[len] = '\0';
    if (strchr(buf, '\n') != NULL)
      break;
  }
  close(fd);
  buf[len] = '\0';
  nl = strchr(buf, '\n');
  if (nl == NULL) {
    ai_answer("E", (len == 0) ? "timeout" : "nohelper", result);
    return;
  }
  *nl = '\0';
  ai_answer("D", buf, result);
}

/* The four calls.  result is the descriptor op_kernel() will put on the stack; descr is the argument. */
void k_ai(int action, DESCRIPTOR* descr, DESCRIPTOR* result) {
  if (!(process.program.flags & HDR_INTERNAL)) {
    ai_answer("ERR", "internal", result);
    return;
  }
  switch (action) {
    case K_AI_START:
      ai_start(descr, result);
      break;
    case K_AI_POLL:
      ai_poll(result);
      break;
    case K_AI_CANCEL:
      ai_reset();
      ai_answer("OK", NULL, result);
      break;
    case K_AI_STATUS:
      ai_status(result);
      break;
    default:
      ai_answer("ERR", "bad", result);
      break;
  }
}

/* END-CODE */
