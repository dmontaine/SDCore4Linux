/* SDLNXD.C
 * SD Linux daemon.
 * Copyright (c) 2007 Ladybridge Systems, All Rights Reserved
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
 * 24 Oct 26 dm  W.11 F4, option C2 (the owner: "Start C2"): the daemon bounds what one uid may add to the trail (AUDIT_RATE_MAX in AUDIT_RATE_WINDOW seconds, then ONE line
 *               saying how many were dropped) and rotates the file by size as it writes, with audit_rotate_file() (audit_rot.c), the code "sd -start" uses.
 * 24 Oct 26 dm  W.11 F4, option C1 (the owner: "b then c"): this daemon is the audit trail's writer.  It listens on a Unix datagram socket (SD_AUDIT_SOCK), takes the user and
 *               the pid of each record from the kernel's credentials on the datagram and appends the line to the audit file; the main loop waits in poll() instead of sleep().
 * 24 Oct 26 dm  W.11 F1 (security-model evaluation): this daemon runs as root, so it no longer takes the system directory from the shared
 *               segment, which any process that can attach may change.  The directory is found from the daemon's own executable
 *               (own_sysdir()), "sd -cleanup" is started with execl and no shell, and the error log is opened under the same directory.
 * 16 Oct 26 dm  The scan for lost processes runs every CLEANUP seconds (sd.conf, 30 to 3600, default 300) - QM4 gaps.
 * 10 Sep 26 dm  Parity audit: a semaphore failure prints its reason before
 *               exit(2) (UPSTREAM_FIXES 3, the Windows port's proposal).
 * 31 Dec 23 SD launch - prior history suppressed
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE /* struct ucred and SCM_CREDENTIALS (the audit socket) */
#endif
#define Public
#define init(a) = a
#include "sd.h"

#include <time.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <pwd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <signal.h>
#include <sched.h>
#include <limits.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>

int shmid; /* Shared memory id */

bool terminate = FALSE;

/* W.11 F1: the system directory, taken from this program's own path (<sysdir>/bin/sdlnxd), NOT from the shared segment. */
static char own_sysdir_path[PATH_MAX + 1];

static bool own_sysdir(void) {
  char exe[PATH_MAX + 1];
  char* slash;
  ssize_t n;
  struct stat st;
  char sdpath[PATH_MAX + 16];

  if ((n = readlink("/proc/self/exe", exe, PATH_MAX)) <= 0)
    return FALSE;
  exe[n] = '\0';
  if ((slash = strrchr(exe, '/')) == NULL)
    return FALSE;
  *slash = '\0'; /* .../bin */
  if (((slash = strrchr(exe, '/')) == NULL) || (strcmp(slash, "/bin") != 0))
    return FALSE;
  *slash = '\0'; /* the system directory */
  if (exe[0] == '\0')
    return FALSE;
  if (snprintf(sdpath, sizeof(sdpath), "%s/bin/sd", exe) >= (int)sizeof(sdpath))
    return FALSE;
  if ((stat(sdpath, &st) != 0) || !S_ISREG(st.st_mode) || (access(sdpath, X_OK) != 0))
    return FALSE;
  strcpy(own_sysdir_path, exe);
  return TRUE;
}

void check_lost_users(void);

void signal_handler(int signum);

void log_message(char* msg);

/* ======================================================================
   The audit trail's writer.  W.11 F4, option C1 (24 Oct 26, the owner: "b then c").

   Sessions run as the user, so for as long as they appended to the audit file themselves the file had to be writable by the group, and a member of the group could add
   a line that claimed any user, uid or pid.  Now a session sends the record here (k_error.c audit_to_daemon()) and this daemon, which is root, appends it: the user
   and the pid on the line come from the credentials the KERNEL attaches to the datagram (SO_PASSCRED / SCM_CREDENTIALS), never from the text.  The text is the sender's
   and goes after the stamped fields.  The one field still taken from the sender is the SD user number (uid=), which this daemon cannot check.

   Everything here is input from any SD user, in a process that runs as root: the buffers are fixed, a datagram is read whole or dropped, the format string is
   never the sender's, the path comes from the daemon's own executable (own_sysdir(), F1), and a bad datagram is dropped and counted - it never ends the loop.            */

#define AUDIT_MSG_MAX 1900      /* bytes of text kept */
#define AUDIT_RATE_SLOTS 128    /* uids whose current window is remembered */

static int audit_sock = -1;
static bool audit_sock_made = FALSE;
static unsigned long audit_dropped = 0;       /* datagrams refused: no credentials, not ours, too long, nothing in it */
static unsigned long audit_unwritten = 0;     /* records accepted but not appended (the file would not open or write) */
static unsigned long audit_limited = 0;       /* records dropped by the per-uid rate bound (C2) */
static unsigned long audit_rotate_failed = 0; /* rotations that were due and could not be done (C2) */
static time_t audit_rotate_after = 0;         /* after a failed rotation, no new attempt before this audit_clock() second */

/* C2: what one uid has added in its current window.  The table is the daemon's own memory; nothing in it comes from the text of a datagram. */
typedef struct {
  uid_t uid;
  pid_t pid;            /* the last sender's: the line that reports a flood names it */
  time_t start;         /* audit_clock() when this window began; 0 = the slot is free */
  unsigned long count;  /* records taken in this window */
  unsigned long dropped;
} AUDIT_RATE;

static AUDIT_RATE audit_rate[AUDIT_RATE_SLOTS];

/* the user name for a uid, safe to put on a line; a tiny cache so that a burst does not ask NSS for every record */
static void audit_user_name(uid_t uid, char* out, size_t outsz) {
  static struct { uid_t uid; time_t at; char name[64]; } cache[8];
  static int next = 0;
  time_t now = time(NULL);
  struct passwd* pw;
  char* p;
  int i;

  for (i = 0; i < 8; i++) {
    if ((cache[i].at != 0) && (cache[i].uid == uid) && (now - cache[i].at < 60)) {
      snprintf(out, outsz, "%s", cache[i].name);
      return;
    }
  }
  pw = getpwuid(uid);
  if (pw != NULL)
    snprintf(out, outsz, "%.60s", pw->pw_name);
  else
    snprintf(out, outsz, "%u", (unsigned)uid);
  for (p = out; *p != '\0'; p++) {
    if (!(isalnum((unsigned char)*p) || (*p == '.') || (*p == '_') || (*p == '-')))
      *p = '?';
  }
  cache[next].uid = uid;
  cache[next].at = now;
  snprintf(cache[next].name, sizeof(cache[next].name), "%s", out);
  next = (next + 1) % 8;
}

/* /proc/<pid>/loginuid is the user who logged in, and survives su and sudo; the kernel sets it, the process cannot.  "" when it is the same as the uid, unset, or unreadable
   (the process may be gone by now). */
static void audit_login_name(pid_t pid, uid_t uid, char* out, size_t outsz) {
  char path[48];
  char text[24];
  FILE* fp;
  unsigned long v;
  char* end;

  out[0] = '\0';
  snprintf(path, sizeof(path), "/proc/%d/loginuid", (int)pid);
  if ((fp = fopen(path, "r")) == NULL)
    return;
  if (fgets(text, sizeof(text), fp) == NULL) {
    fclose(fp);
    return;
  }
  fclose(fp);
  v = strtoul(text, &end, 10);
  if ((end == text) || (v == 4294967295UL) || ((uid_t)v == uid))
    return;
  audit_user_name((uid_t)v, out, outsz);
}

/* Seconds on the monotonic clock, plus one so that 0 can mean "none".  The wall clock can be set back; a rate window must not be. */
static time_t audit_clock(void) {
  struct timespec t;

  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + 1;
}

/* One line of the trail: the time, the daemon's stamp (user, login user, the claimed SD user number, pid), then the text as an ARGUMENT - never as the format.
   0 when it does not fit. */
static int audit_format_line(char* line, size_t linesz, const char* user, const char* login, const char* who, int pid, const char* msg) {
  time_t timenow = time(NULL);
  struct tm lt;
  int len;

  localtime_r(&timenow, &lt);
  len = snprintf(line, linesz, "%04d-%02d-%02d %02d:%02d:%02d user=%s%s%s uid=%s pid=%d %s\n",
                 lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec, user,
                 (login[0] != '\0') ? " sudo=" : "", login, who, pid, msg);
  if ((len <= 0) || (len >= (int)linesz))
    return 0;
  return len;
}

/* Append one finished line to the trail.  C2: the file is rotated first when it has reached AUDIT_ROTATE_BYTES, under the error log's semaphore (a session that is
   appending itself, because it could not reach this daemon, holds it), by the code "sd -start" uses.  A rotation that fails is counted and not tried again for a minute:
   the trail stays whole and keeps growing, as it does there. */
static void audit_emit_line(const char* line, int len) {
  char path[PATH_MAX + 16];
  struct stat st;
  time_t now;
  int fd;

  if (snprintf(path, sizeof(path), "%s%caudit", own_sysdir_path, DS) >= (int)sizeof(path)) {
    audit_unwritten++;
    return;
  }
  now = audit_clock();
  if ((now >= audit_rotate_after) && (lstat(path, &st) == 0) && S_ISREG(st.st_mode) && (st.st_size >= AUDIT_ROTATE_BYTES)) {
    StartExclusive(ERRLOG_SEM, 70);
    if (audit_rotate_file(path, AUDIT_ROTATE_BYTES) < 0) {
      audit_rotate_failed++;
      audit_rotate_after = now + 60;
    }
    EndExclusive(ERRLOG_SEM);
  }
  fd = open(path, O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);
  if ((fd < 0) || (write(fd, line, len) != len))
    audit_unwritten++;
  if (fd >= 0)
    close(fd);
}

/* C2: ONE line, in the trail's own shape, saying that a uid sent more than the bound allows in a window.  The user is the credentials' (audit_user_name), the pid the last
   sender's, and the text is numbers and constants only. */
static void audit_rate_note(const AUDIT_RATE* s) {
  char user[64];
  char msg[96];
  char line[256];
  int len;

  audit_user_name(s->uid, user, sizeof(user));
  snprintf(msg, sizeof(msg), "audit rate limit dropped=%lu taken=%lu limit=%d window=%d", s->dropped, s->count, AUDIT_RATE_MAX, AUDIT_RATE_WINDOW);
  len = audit_format_line(line, sizeof(line), user, "", "?", (int)s->pid, msg);
  if (len > 0)
    audit_emit_line(line, len);
  else
    audit_unwritten++;
}

/* The window of this slot is over, or the slot is wanted for another uid: write its line if it dropped anything. */
static void audit_rate_close(AUDIT_RATE* s) {
  if (s->dropped > 0)
    audit_rate_note(s);
  s->dropped = 0;
}

/* C2: may this uid add a record now?  At most AUDIT_RATE_MAX in a window of AUDIT_RATE_WINDOW seconds, counted per uid from the credentials; the rest are dropped here and
   counted.  The journal copy that every session sends is not limited by this, so a dropped record still has one. */
static bool audit_rate_take(uid_t uid, pid_t pid) {
  time_t now = audit_clock();
  AUDIT_RATE* s = NULL;
  AUDIT_RATE* oldest = &audit_rate[0];
  int i;

  for (i = 0; i < AUDIT_RATE_SLOTS; i++) {
    if ((audit_rate[i].start != 0) && (audit_rate[i].uid == uid)) {
      s = &audit_rate[i];
      break;
    }
  }
  if (s == NULL) {
    for (i = 0; i < AUDIT_RATE_SLOTS; i++) {
      if (audit_rate[i].start == 0) {
        s = &audit_rate[i];
        break;
      }
      if (audit_rate[i].start < oldest->start)
        oldest = &audit_rate[i];
    }
    if (s == NULL) { /* the table is full: the oldest window goes, with its line */
      audit_rate_close(oldest);
      s = oldest;
    }
    memset(s, 0, sizeof(*s));
    s->uid = uid;
    s->start = now;
  } else if (now - s->start >= AUDIT_RATE_WINDOW) {
    audit_rate_close(s);
    s->start = now;
    s->count = 0;
  }
  s->pid = pid;
  if (s->count >= AUDIT_RATE_MAX) {
    s->dropped++;
    audit_limited++;
    return FALSE;
  }
  s->count++;
  return TRUE;
}

/* Every tick, and once more on the way out: the lines for the windows that are over (for all of them on the way out), and the slots they free. */
static void audit_rate_sweep(bool all) {
  time_t now = audit_clock();
  int i;

  for (i = 0; i < AUDIT_RATE_SLOTS; i++) {
    if (audit_rate[i].start == 0)
      continue;
    if (all || (now - audit_rate[i].start >= AUDIT_RATE_WINDOW)) {
      audit_rate_close(&audit_rate[i]);
      if (now - audit_rate[i].start >= AUDIT_RATE_WINDOW)
        audit_rate[i].start = 0;
    }
  }
}

static void audit_write_record(const struct ucred* cred, char* buf, ssize_t n) {
  size_t magic = strlen(AUDIT_MAGIC);
  char who[16];
  char* p;
  char* msg;
  char user[64];
  char login[64];
  char line[AUDIT_MSG_MAX + 512];
  int len;
  int i;

  buf[n] = '\0';
  if ((n < (ssize_t)(magic + 3)) || (strncmp(buf, AUDIT_MAGIC, magic) != 0)) {
    audit_dropped++;
    return;
  }
  p = buf + magic;
  if ((p[0] == '?') && (p[1] == ' ')) {
    strcpy(who, "?");
    msg = p + 2;
  } else {
    for (i = 0; (i < 9) && isdigit((unsigned char)p[i]); i++)
      who[i] = p[i];
    if ((i == 0) || (p[i] != ' ')) {
      audit_dropped++;
      return;
    }
    who[i] = '\0';
    msg = p + i + 1;
  }
  if (*msg == '\0') {
    audit_dropped++;
    return;
  }
  for (p = msg; *p != '\0'; p++) {
    if (((unsigned char)*p < 32) || ((unsigned char)*p == 127) || ((unsigned char)*p >= 248))
      *p = '?';
  }
  if (strlen(msg) > AUDIT_MSG_MAX)
    msg[AUDIT_MSG_MAX] = '\0';

  /* C2: a well-formed record from a uid that has used up its window is dropped here (and counted), before anything is looked up or formatted for it */
  if (!audit_rate_take(cred->uid, cred->pid))
    return;

  audit_user_name(cred->uid, user, sizeof(user));
  audit_login_name(cred->pid, cred->uid, login, sizeof(login));

  len = audit_format_line(line, sizeof(line), user, login, who, (int)cred->pid, msg);
  if (len == 0) {
    audit_dropped++;
    return;
  }
  audit_emit_line(line, len);
}

static void audit_receive_one(void) {
  char buf[AUDIT_DGRAM_MAX + 1];
  struct iovec iov;
  union { struct cmsghdr h; char b[CMSG_SPACE(sizeof(struct ucred))]; } ctl;
  struct msghdr mh;
  struct cmsghdr* c;
  struct ucred cred;
  bool have_cred = FALSE;
  ssize_t n;

  memset(&mh, 0, sizeof(mh));
  memset(&ctl, 0, sizeof(ctl));
  iov.iov_base = buf;
  iov.iov_len = sizeof(buf);
  mh.msg_iov = &iov;
  mh.msg_iovlen = 1;
  mh.msg_control = ctl.b;
  mh.msg_controllen = sizeof(ctl.b);
  n = recvmsg(audit_sock, &mh, MSG_DONTWAIT | MSG_CMSG_CLOEXEC);
  if (n < 0)
    return;
  if ((mh.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) || (n > AUDIT_DGRAM_MAX)) {
    audit_dropped++;
    return;
  }
  for (c = CMSG_FIRSTHDR(&mh); c != NULL; c = CMSG_NXTHDR(&mh, c)) {
    if ((c->cmsg_level == SOL_SOCKET) && (c->cmsg_type == SCM_CREDENTIALS) && (c->cmsg_len >= CMSG_LEN(sizeof(struct ucred)))) {
      memcpy(&cred, CMSG_DATA(c), sizeof(cred));
      have_cred = TRUE;
    }
  }
  if (!have_cred) {
    audit_dropped++;
    return;
  }
  audit_write_record(&cred, buf, n);
}

/* Make the socket.  False (and a line in errlog) when it cannot be made: the daemon goes on with its other work, and the sessions fall back to the file. */
static bool audit_socket_open(void) {
  struct sockaddr_un sa;
  struct stat st;
  struct group* gr;
  char dir[sizeof(sa.sun_path)];
  char* slash;
  mode_t old;
  int on = 1;

  if (strlen(SD_AUDIT_SOCK) >= sizeof(sa.sun_path))
    return FALSE;
  strcpy(dir, SD_AUDIT_SOCK);
  if (((slash = strrchr(dir, '/')) == NULL) || (slash == dir))
    return FALSE;
  *slash = '\0';
  if ((mkdir(dir, 0755) != 0) && (errno != EEXIST)) {
    log_message("audit socket: cannot make its directory");
    return FALSE;
  }
  /* the directory is what keeps another user from making this name: ours, and as root not open to the group or others */
  if ((lstat(dir, &st) != 0) || !S_ISDIR(st.st_mode) || (st.st_uid != geteuid()) || ((geteuid() == 0) && (st.st_mode & (S_IWGRP | S_IWOTH)))) {
    log_message("audit socket: its directory is not ours or can be written by others");
    return FALSE;
  }
  if ((audit_sock = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0)) < 0)
    return FALSE;
  if (setsockopt(audit_sock, SOL_SOCKET, SO_PASSCRED, &on, sizeof(on)) != 0) {
    close(audit_sock);
    audit_sock = -1;
    return FALSE;
  }
  memset(&sa, 0, sizeof(sa));
  sa.sun_family = AF_UNIX;
  strcpy(sa.sun_path, SD_AUDIT_SOCK);
  (void)unlink(SD_AUDIT_SOCK); /* a left-over from a daemon that was killed */
  old = umask(0177);           /* root only until the group and the mode are set */
  if (bind(audit_sock, (struct sockaddr*)&sa, sizeof(sa)) != 0) {
    umask(old);
    log_message("audit socket: cannot bind it");
    close(audit_sock);
    audit_sock = -1;
    return FALSE;
  }
  umask(old);
  if ((gr = getgrnam("sdusers")) != NULL)
    (void)chown(SD_AUDIT_SOCK, (uid_t)-1, gr->gr_gid);
  (void)chmod(SD_AUDIT_SOCK, 0660);
  audit_sock_made = TRUE;
  return TRUE;
}

/* Take records for up to this many seconds (the loop's tick), then return so that the rest of the daemon's work is done on time. */
static void audit_serve(int seconds) {
  struct timespec t0, now;
  struct pollfd pfd;
  long left_ms;

  clock_gettime(CLOCK_MONOTONIC, &t0);
  for (;;) {
    clock_gettime(CLOCK_MONOTONIC, &now);
    left_ms = (long)seconds * 1000L - ((now.tv_sec - t0.tv_sec) * 1000L + (now.tv_nsec - t0.tv_nsec) / 1000000L);
    if (terminate || (left_ms <= 0))
      return;
    if (audit_sock < 0) {
      (void)poll(NULL, 0, (int)left_ms);
      continue;
    }
    pfd.fd = audit_sock;
    pfd.events = POLLIN;
    pfd.revents = 0;
    if ((poll(&pfd, 1, (int)left_ms) > 0) && (pfd.revents & POLLIN))
      audit_receive_one();
  }
}

/* ====================================================================== */

#define TICK_SECONDS 10

int main() {
  char errmsg[80];
  int elapsed = 0;  /* seconds since the last scan for lost processes */
  int interval;     /* CLEANUP */

  process.user_no = -2; /* Mark as sdlnxd for semaphore table */

  if (!own_sysdir()) {
    fprintf(stderr, "sdlnxd: cannot find the system directory from its own path (it must run as <sysdir>/bin/sdlnxd)\n");
    exit(3);
  }

  signal(SIGTERM, signal_handler);

  /* Attach the shared memory segment */

  if (((shmid = shmget(SD_SHM_KEY, 0, 0666)) == -1) ||
      (((sysseg = (SYSSEG*)shmat(shmid, NULL, 0))) == (void*)(-1))) {
    exit(1);
  }

  /* Get access to semaphores */

  /* 10 Sep 26 dm - Parity audit (UPSTREAM_FIXES 3, the port's proposal):
     errmsg has just been filled in with the reason and was discarded, so a
     daemon that would not start left nothing anywhere to read.  log_message()
     cannot be used this early - it takes ERRLOG_SEM, and the semaphores are
     precisely what failed - so stderr it is. */
  if (!get_semaphores(FALSE, errmsg)) {
    fprintf(stderr, "sdlnxd: %s\n", errmsg);
    exit(2);
  }

  /* Set process id into shared memory */

  sysseg->sdlnxd_pid = getpid();

  /* W.11 F4, option C1: the audit trail's writer.  Without the socket the sessions append to the file themselves, as before. */
  (void)audit_socket_open();

  /* ========================= Main loop ========================= */

  /* 16 Oct 26 dm - QM4 gaps, CLEANUP.  The scan for lost processes runs every CLEANUP seconds (30 to 3600, 300 unless sd.conf
     says otherwise; it was a fixed five minutes).  The loop wakes every ten seconds so that the shortest interval is kept to
     within one tick and so that a terminate signal is acted on without waiting out a minute.  A segment that holds no usable
     value (one made by an older build) gets the five minutes it always had.                                              */

  while (!terminate) {
    interval = sysseg->cleanup;
    if ((interval < 30) || (interval > 3600))
      interval = 300;

    elapsed += TICK_SECONDS;
    if (elapsed >= interval) {
      elapsed = 0;
      check_lost_users();
    }

    audit_serve(TICK_SECONDS); /* takes audit records until the tick is up (it was sleep(TICK_SECONDS)) */
    audit_rate_sweep(FALSE);   /* C2: the line for each rate window that is over */

    if ((audit_dropped != 0) || (audit_unwritten != 0) || (audit_limited != 0) || (audit_rotate_failed != 0)) {
      char note[200];

      snprintf(note, sizeof(note), "audit: %lu datagram(s) refused, %lu record(s) not written, %lu over the rate bound, %lu rotation(s) failed, since the last note",
               audit_dropped, audit_unwritten, audit_limited, audit_rotate_failed);
      audit_dropped = 0;
      audit_unwritten = 0;
      audit_limited = 0;
      audit_rotate_failed = 0;
      log_message(note);
    }
  }

  /* Tidy up on our way out */

  audit_rate_sweep(TRUE); /* C2: a window that dropped records has its line even if it is not over */

  if (audit_sock >= 0)
    close(audit_sock);
  if (audit_sock_made)
    (void)unlink(SD_AUDIT_SOCK);

  shmdt((void*)sysseg); /* Dettach shared memory */

  return 0;
}

/* ======================================================================
   check_lost_users()  -  Clear down "lost" processes                     */

void check_lost_users() {
  USER_ENTRY* uptr;
  int32_t pid;
  int16_t u;
  int16_t num_checked = 0;
  bool lost_user_detected = FALSE;
  char cmd[MAX_PATHNAME_LEN + 10];

  StartExclusive(SHORT_CODE, 69);

  for (u = 1; u <= sysseg->max_users; u++) {
    uptr = UPtr(u);
    pid = uptr->pid;
    if (uptr->uid) {
      if ((++num_checked % 5) == 0) {
        /* Be nice - don't hold sempahore for entire table scan */

        EndExclusive(SHORT_CODE);
        RelinquishTimeslice;
        StartExclusive(SHORT_CODE, 69);
        if (uptr->uid == 0)
          continue; /* User logged out */
      }

      if (kill(pid, 0) && (errno != EPERM)) {
        lost_user_detected = TRUE;
        break;
      }
    }
  }

  EndExclusive(SHORT_CODE);

  if (lost_user_detected) {
    /* Fire off a SD session to clear down the users. Although it would be
      nice to do the whole job here, there are so many dependencies that
      sdlnxd ends up carrying around most of SD.                          */
    // converted to snprintf() -gwb 25Feb20
    /* Modified by Composer AI - 2026/06/10.
       Single-quote the executable path so spaces or shell metacharacters
       in the (administrator controlled) system directory cannot break or
       inject into the command. Also do not execute the command at all if
       it would have been truncated, instead of running a mangled path. */
    /* if (snprintf(cmd, MAX_PATHNAME_LEN + 10, "%s/bin/sd -cleanup", sysseg->sysdir) >= (MAX_PATHNAME_LEN + 10)) {
        printf(
            "Overflowed path/filename buffer. Truncated to:\n%s/bin/sd "
            "-cleanup",
            sysseg->sysdir);
      }
    system(cmd); */
    /* 24 Oct 26 dm - W.11 F1: the program is <own sysdir>/bin/sd, started with execl (no shell), never a path read from the segment. */
    if (snprintf(cmd, sizeof(cmd), "%s/bin/sd", own_sysdir_path) >= (int)sizeof(cmd)) {
        printf(
            "Overflowed path/filename buffer. Cleanup not run for:\n%s/bin/sd "
            "-cleanup",
            own_sysdir_path);
      } else {
        pid_t child = fork();
        if (child == 0) {
          execl(cmd, "sd", "-cleanup", (char*)NULL);
          _exit(127);
        } else if (child > 0) {
          waitpid(child, NULL, 0);
        }
      }
    /* -------------------- */
  }
}

/* ======================================================================
   Signal handler                                                         */

void signal_handler(signum) int signum;
{
  switch (signum) {
    case SIGTERM:
      signal(SIGTERM, SIG_IGN);
      terminate = TRUE;
      break;
  }
}

/* ======================================================================
   log_message()  -  Add message to error log                             */

void log_message(char* msg) {
  int errlog;
  time_t timenow;
  struct tm* ltime;
  int bytes;
#define BUFF_SIZE 4096
  char buff[BUFF_SIZE];
  static char* month_names[12] = {
      "January", "February", "March",     "April",   "May",      "June",
      "July",    "August",   "September", "October", "November", "December"};

  if (sysseg->errlog) {
    StartExclusive(ERRLOG_SEM, 71);

    /* W.11 F1: not the segment's copy; snprintf, because this runs as root and the path can be up to PATH_MAX long */
    if (snprintf(buff, BUFF_SIZE, "%s%cerrlog", own_sysdir_path, DS) >= BUFF_SIZE)
      errlog = -1;
    else
      errlog = open(buff, O_RDWR | O_CREAT | O_BINARY, 0777);

    /* Modified by Composer AI - 2026/06/10.
       If the open() failed, "bytes" was used uninitialized and write()/
       close() were called with a negative file descriptor. Move the
       write and close inside the successful-open branch. */
    /* if (errlog >= 0) {
      lseek(errlog, 0, SEEK_END);

      timenow = time(NULL);
      ltime = localtime(&timenow);

      bytes = sprintf(buff, "%02d %.3s %02d %02d:%02d:%02d [sdlnxd]:%s   %s%s",
                      ltime->tm_mday, month_names[ltime->tm_mon],
                      ltime->tm_year % 100, ltime->tm_hour, ltime->tm_min,
                      ltime->tm_sec, Newline, msg, Newline);
    }

    write(errlog, buff, bytes);

    close(errlog); */
    if (errlog >= 0) {
      lseek(errlog, 0, SEEK_END);

      timenow = time(NULL);
      ltime = localtime(&timenow);

      bytes = sprintf(buff, "%02d %.3s %02d %02d:%02d:%02d [sdlnxd]:%s   %s%s",
                      ltime->tm_mday, month_names[ltime->tm_mon],
                      ltime->tm_year % 100, ltime->tm_hour, ltime->tm_min,
                      ltime->tm_sec, Newline, msg, Newline);

      write(errlog, buff, bytes);

      close(errlog);
    }
    /* -------------------- */

    EndExclusive(ERRLOG_SEM);
  }
}

/* END-CODE */
