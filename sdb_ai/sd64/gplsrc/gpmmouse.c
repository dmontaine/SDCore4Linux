/* GPMMOUSE.C
 * The Linux console's mouse, through the gpm daemon.
 * Copyright (c) 2026, SD Core for Linux.  This program is free software; you can redistribute
 * it and/or modify it under the terms of the GNU General Public License, version 3 or later.
 *
 * START-HISTORY:
 * 31 Oct 26 dm  New (S.94, the full-screen tools on a bare Linux console).  The console ignores xterm's mouse modes, so a session on a text console never saw the mouse.  gpm is the
 *               daemon that reads the mouse there; a client connects to its socket, says which virtual console it is on, and is sent a record for every movement, button and wheel
 *               turn.  This turns those records into the xterm SGR reports (ESC [ < b ; x ; y M or m) that the screen library already reads, so nothing above the input
 *               layer knows the difference.  The layout of the two records was read from gpm.h 1.20.7 and checked against a live daemon on a Debian 13 console (a virtual
 *               mouse through /dev/uinput; .claude/vmtools/console-gpmprobe.py).  No libgpm: the records are small and the library would be a build dependency on three distributions.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * gpm_enable()          connect to the daemon for this session's console; 1 connected, 0 not (not a text console, no daemon, refused)
 * gpm_disable()         disconnect
 * gpm_fd()              the socket, or -1: input.c waits on it with the keyboard
 * gpm_peek_report(buf)  the next report as bytes (0 if none); the record is read from the socket as needed, the report stays until gpm_report_done()
 * gpm_report_done()     the report just peeked has been taken
 *
 * THE DAEMON IS NOT TRUSTED FOR WHAT IT SENDS, ONLY FOR WHERE THE MOUSE IS: every field used is range checked, and what comes out is only ever a mouse report - a record can
 * never put a typed character into the input.  A connection that gives a short or odd read is dropped, not guessed at.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "sddefs.h"
#include "gpmmouse.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/un.h>

/* gpm.h 1.20.7: struct Gpm_Connect and struct Gpm_Event, as the daemon reads and writes them on /dev/gpmctl */
typedef struct {
  unsigned short eventMask, defaultMask, minMod, maxMod;
  int pid;
  int vc;
} GPM_CONNECT;

typedef struct {
  unsigned char buttons, modifiers;
  unsigned short vc;
  short dx, dy, x, y;
  int type;
  int clicks;
  int margin;
  short wdx, wdy;
} GPM_EVENT;

_Static_assert(sizeof(GPM_CONNECT) == 16, "Gpm_Connect is 16 bytes");
_Static_assert(sizeof(GPM_EVENT) == 28, "Gpm_Event is 28 bytes");

#define GPM_MOVE 1
#define GPM_DRAG 2
#define GPM_DOWN 4
#define GPM_UP 8
#define GPM_BARE 0x0f
#define GPM_HARD 256
#define GPM_B_RIGHT 1
#define GPM_B_MIDDLE 2
#define GPM_B_LEFT 4
#define GPM_MOD_SHIFT 1
#define GPM_MOD_CTRL 4
#define GPM_MOD_ALT 8

#define REPORT_MAX 32 /* ESC [ < 99 ; 99999 ; 99999 M is 18 bytes */

Private int gpm_sock = -1;
Private char report[REPORT_MAX];
Private int report_len = 0;
Private GPM_EVENT pending;       /* the record being turned into reports: a press with two buttons is two */
Private bool have_pending = FALSE;
Private int pending_buttons = 0; /* the buttons of `pending` still to report */
Private unsigned char held = 0;  /* the buttons held down now: a drag is reported for the first of them */
Private time_t partial_since = 0; /* when the socket first held less than a whole record: a daemon that never finishes one is dropped, not waited on with the processor */

/* ======================================================================
   console_vt()  -  the number of the virtual console that is this session's input, or 0 if it is not one

   A text console is a character device with major 4 and a minor of 1 to 63 (tty1 to tty63).  Serial lines (minor 64 and up), pseudo terminals, pipes and sockets are not.  The
   sandbox builds define SD_GPM_ANY_TTY so that a test session on a pseudo terminal can talk to a stand-in daemon.                                                         */

Private int console_vt() {
  struct stat st;

  if (fstat(0, &st) != 0 || !S_ISCHR(st.st_mode))
    return 0;
#if SD_GPM_ANY_TTY
  return 1;
#else
  if (major(st.st_rdev) != 4 || minor(st.st_rdev) < 1 || minor(st.st_rdev) > 63)
    return 0;
  return (int)minor(st.st_rdev);
#endif
}

/* ======================================================================
   gpm_enable()  -  connect                                                                                                                                          */

int gpm_enable() {
  struct sockaddr_un sa;
  GPM_CONNECT conn;
  int vt;
  int s;

  if (gpm_sock >= 0)
    return 1;
  vt = console_vt();
  if (vt == 0)
    return 0;
  if (strlen(SD_GPM_SOCK) >= sizeof(sa.sun_path))
    return 0;

  s = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
  if (s < 0)
    return 0;
  memset(&sa, 0, sizeof(sa));
  sa.sun_family = AF_UNIX;
  strcpy(sa.sun_path, SD_GPM_SOCK);
  if (connect(s, (struct sockaddr *)&sa, sizeof(sa)) != 0) {
    close(s);
    return 0;
  }

  /* All events to us; gpm keeps its own handling of MOVE (it draws the pointer) and of nothing else: no selection or paste while a program owns the mouse.  What libgpm gives
     ncurses, and what a client that wants a pointer must ask for.                                                                                                          */
  memset(&conn, 0, sizeof(conn));
  conn.eventMask = 0xFFFF;
  conn.defaultMask = GPM_MOVE | GPM_HARD;
  conn.minMod = 0;
  conn.maxMod = 0xFFFF;
  conn.pid = (int)getpid();
  conn.vc = vt;
  if (write(s, &conn, sizeof(conn)) != (ssize_t)sizeof(conn)) {
    close(s);
    return 0;
  }

  /* Data on the socket is input like a key: the same SIGIO the keyboard raises (linuxio.c io_handler) */
  fcntl(s, F_SETOWN, (int)getpid());
  fcntl(s, F_SETFL, fcntl(s, F_GETFL) | O_NONBLOCK | O_ASYNC);

  gpm_sock = s;
  report_len = 0;
  have_pending = FALSE;
  pending_buttons = 0;
  held = 0;
  return 1;
}

/* ======================================================================
   gpm_disable()                                                                                                                                                       */

void gpm_disable() {
  if (gpm_sock >= 0)
    close(gpm_sock);
  gpm_sock = -1;
  report_len = 0;
  have_pending = FALSE;
  pending_buttons = 0;
  held = 0;
  partial_since = 0;
}

int gpm_fd() {
  return gpm_sock;
}

/* ======================================================================
   put_report()  -  ESC [ < b ; x ; y M|m  into `report`                                                                                                              */

Private void put_report(int b, int x, int y, int up) {
  if (x < 1)
    x = 1;
  if (y < 1)
    y = 1;
  if (x > 9999)
    x = 9999;
  if (y > 9999)
    y = 9999;
  report_len = snprintf(report, REPORT_MAX, "\033[<%d;%d;%d%c", b, x, y, up ? 'm' : 'M');
}

/* The xterm button number of one gpm button */
Private int sgr_button(int gpm_button) {
  if (gpm_button & GPM_B_LEFT)
    return 0;
  if (gpm_button & GPM_B_MIDDLE)
    return 1;
  return 2;
}

/* The xterm modifier bits: shift 4, meta 8, control 16 */
Private int sgr_mods(int m) {
  int r = 0;

  if (m & GPM_MOD_SHIFT)
    r += 4;
  if (m & GPM_MOD_ALT)
    r += 8;
  if (m & GPM_MOD_CTRL)
    r += 16;
  return r;
}

/* ======================================================================
   next_from_pending()  -  the next report of the record in hand, if it makes one                                                                                    */

Private bool next_from_pending() {
  int bare, b, mods;
  int bit;

  if (!have_pending)
    return FALSE;
  bare = pending.type & GPM_BARE;
  mods = sgr_mods(pending.modifiers);

  /* A wheel turn arrives as a MOVE with a vertical (or horizontal) displacement of the wheel and no button: 64 is up, 65 down, 66 and 67 sideways (SD ignores those) */
  if (bare == GPM_MOVE && (pending.wdy != 0 || pending.wdx != 0)) {
    have_pending = FALSE;
    if (pending.wdy != 0)
      b = (pending.wdy > 0) ? 64 : 65;
    else
      b = (pending.wdx > 0) ? 67 : 66;
    put_report(b + mods, pending.x, pending.y, 0);
    return TRUE;
  }

  if (bare == GPM_DOWN || bare == GPM_UP) {
    /* one report for each button the record names, in the order left, middle, right */
    for (bit = GPM_B_LEFT; bit >= GPM_B_RIGHT; bit >>= 1) {
      if (pending_buttons & bit) {
        pending_buttons &= ~bit;
        if (bare == GPM_DOWN)
          held |= (unsigned char)bit;
        else
          held &= (unsigned char)~bit;
        put_report(sgr_button(bit) + mods, pending.x, pending.y, bare == GPM_UP);
        if (pending_buttons == 0)
          have_pending = FALSE;
        return TRUE;
      }
    }
    have_pending = FALSE;
    return FALSE;
  }

  have_pending = FALSE;
  if (bare == GPM_DRAG && held != 0) {
    /* motion with a button held: 32 added to the button of the first one held (xterm's mode 1002) */
    bit = (held & GPM_B_LEFT) ? GPM_B_LEFT : ((held & GPM_B_MIDDLE) ? GPM_B_MIDDLE : GPM_B_RIGHT);
    put_report(sgr_button(bit) + 32 + mods, pending.x, pending.y, 0);
    return TRUE;
  }
  return FALSE; /* a plain move: SD asked for no motion without a button */
}

/* ======================================================================
   gpm_peek_report()  -  the next report, or 0 when there is none now                                                                                                */

int gpm_peek_report(char *buf) {
  ssize_t got;
  GPM_EVENT ev;

  if (gpm_sock < 0)
    return 0;
  for (;;) {
    if (report_len > 0) {
      memcpy(buf, report, (size_t)report_len);
      return report_len;
    }
    if (next_from_pending())
      continue;

    got = recv(gpm_sock, &ev, sizeof(ev), MSG_PEEK | MSG_DONTWAIT);
    if (got < 0) {
      if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)
        return 0;
      gpm_disable(); /* any other error: the daemon is gone */
      return 0;
    }
    if (got == 0) {
      gpm_disable(); /* closed */
      return 0;
    }
    if (got < (ssize_t)sizeof(ev)) {
      /* part of a record: wait for the rest, never act on half of one - but not for ever (poll() calls the socket readable all the while) */
      if (partial_since == 0)
        partial_since = time(NULL);
      else if (time(NULL) - partial_since > 2)
        gpm_disable();
      return 0;
    }
    partial_since = 0;
    got = recv(gpm_sock, &ev, sizeof(ev), MSG_DONTWAIT);
    if (got != (ssize_t)sizeof(ev)) {
      gpm_disable();
      return 0;
    }
    pending = ev;
    have_pending = TRUE;
    pending_buttons = ev.buttons & (GPM_B_LEFT | GPM_B_MIDDLE | GPM_B_RIGHT);
  }
}

void gpm_report_done() {
  report_len = 0;
}

/* END-CODE */
