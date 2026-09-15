/* LINUXIO.C
 * Linux low level terminal driver functions
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
 * 14 Sep 26 dm S.18: login_user() removed with the getpeereid() peer capture
 *           that fed it - request 24 is retired, nothing calls either.
 * 14 Sep 26 dm login_user loads the user's supplementary groups (initgroups)
 *           before the uid drop, on both paths; an API session had none (S.15).
 * 13 Sep 26 dm case inversion starts OFF on both connection paths (plan M: typed
 *           input is not case-flipped; PTERM CASE INVERT still turns it on).
 * 10 Sep 26 dm accept PF_INET for the API server only (reverses the AF_UNIX-only
 *           restriction for that path); TCP API access is gated by SD login plus
 *           the installer's bind/firewall choice.  See start_connection().
 * 20240219 mab move to only allow AF_UNIX socket types
 * 31 Dec 23 SD launch - prior history suppressed
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 */

#include "sd.h"
#include "config.h"
#include "err.h"
#include "header.h"
#include "sdnet.h"
#include "sdtermlb.h"
#include "telnet.h"
#include "tio.h"

#include <netdb.h>
#include <pwd.h>
#include <grp.h>
#include <signal.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/time.h>
#include <time.h>

#include <sched.h>
#include <syslog.h>

/* 14 Sep 26 dm - S.18.  <bsd/unistd.h> (getpeereid, libbsd) and <crypt.h>
   went with login_user(), their only user; so did the peer_* globals.     */

Public int ChildPipe;
Public bool in_sh; /* 0562 Doing SH command? */

#define RING_SIZE 1024
Private volatile char ring_buff[RING_SIZE];
Private volatile int16_t ring_in = 0;
Private volatile int16_t ring_out = 0;

Private void io_handler(int sig);
Private int stdin_modes;
Private void do_input(void);
Private bool input_handler_enabled = TRUE;
Private bool piped_input = FALSE;
Private bool connection_lost = FALSE;

/* Keyboard */

Private int ttyin = 0;
Private struct termios old_tty_settings;
Private struct termios new_tty_settings;
Private bool tty_modes_saved = FALSE;
Private int16_t type_ahead = -1;

Private void signal_handler(int signum);

void set_term(bool trap_break);
void set_old_tty_modes(void);
void set_new_tty_modes(void);
bool negotiate_telnet_parameter(void);

/* ======================================================================
   start_connection()  -  Start Linux socket / pipe based connection      */

bool start_connection(int unused) {
  socklen_t n;
  /* 20240219 mab move to only allow AF_UNIX socket types */
  /* 20240127 mab mods to handle IPv6 */
  /* mostly a copy of what was done in OP_SKT.C, op_accptskt() by gwb & gcb back in Apr of 09, thanks! */

  struct sockaddr_storage sa;

/* 20240219 mab rebrand VBSRVR to APISRVR */ 
  if (is_sdApiSrvr)
    strcpy(command_processor, "$APISRVR");
    
/* 20240219 mab rebrand VBSRVR to APISRVR */
  if (connection_type == CN_SOCKET) {
    if (is_sdApiSrvr) {
     // flag = TRUE;
     // setsockopt(0, IPPROTO_TCP, TCP_NODELAY, (char *)&flag, sizeof(int));
      /* Fire an Ack character up the connection to start the conversation.
         This is necessary because Linux loses anything we send before the
         new process is up and running so Q_M_Client isn't going to talk until
         we go first. The Ack comes from Q_M_Svc on NT style systems.          */

      send(0, "\x06", 1, 0);
    } 
  /* 20240127 mab mods to handle IPv6 */
    n = sizeof(sa);
    getsockname(0, (struct sockaddr *)&sa, &n);
    switch (sa.ss_family){
      case PF_UNIX:
        struct sockaddr_un* sU =  (struct sockaddr_un*)&sa;
        /* pull out UNIX Socket path */
        strncpy(ip_addr,sU->sun_path,MAX_SOCKET_ADDR_STR_LEN-1);
        /* 14 Sep 26 dm - S.18.  The peer's uid was read here with getpeereid()
           for login_user()'s APILOGIN=0 branch, which ran the session as that
           uid in place of a password.  Both are gone: a Unix-socket connection
           authenticates by SCRAM (APISRVR requests 47/48) exactly as a TCP one
           does.  NOT a group gate: the socket is srw-rw-rw- root:sdusers
           (measured 14 Sep 26, SocketGroup without SocketMode), so any local
           user reaches it, as any reaches 127.0.0.1:4243.  The socket is kept
           - an ssh -L tunnel reaches it.                                      */
        syslog(LOG_INFO, "Connection over Unix socket %s", ip_addr);
        break;

      case PF_INET:
        /* 10 Sep 26 dm - accept TCP, but for the API server ONLY, deliberately
           reversing the 2024-02-19 "AF_UNIX only" restriction for that one path.
           A TCP peer has no Unix uid, so getpeereid() is NOT called and the peer
           stays unassigned - the API server authenticates the connection by SD
           user name / password (APISRVR SDConnect).  The listener binds
           127.0.0.1:4243 by default; installsdai.sh opens it to 0.0.0.0:4243 and
           the firewall only on "Allow API access".  A non-API TCP connection is
           still refused.  ip_addr/port_no here are the local (listener) end, as
           for the AF_UNIX case above. */
        {
          struct sockaddr_in* s = (struct sockaddr_in*)&sa;
          port_no = ntohs(s->sin_port);
          if (inet_ntop(AF_INET, &s->sin_addr, ip_addr, MAX_SOCKET_ADDR_STR_LEN) == NULL)
            strncpy(ip_addr, "?", MAX_SOCKET_ADDR_STR_LEN - 1);
          if (!is_sdApiSrvr) {
            syslog(LOG_INFO, "Refusing PF_INET connection (not API server) on %s", ip_addr);
            return FALSE; /* Error */
          }
          syslog(LOG_INFO, "API connection over TCP on %s port %d (SD login required)", ip_addr, port_no);
        }
        break;

      case PF_INET6:
/*        struct sockaddr_in6* s6 = (struct sockaddr_in6*)&sa;
          port_no = ntohs(s6->sin6_port);
          if (inet_ntop(AF_INET6, &s6->sin6_addr, ip_addr, MAX_IP_ADDR_STR_LEN) ==  NULL) {
            process.status = ER_BADADDR;
          }
*/
          syslog (LOG_INFO,"Invalid Network Socket Type PF_INET6");
          return FALSE; /* Error */ 
      break;

      default:
          syslog (LOG_INFO,"Invalid Network Socket Type UNKNOW");
          return FALSE; /* Error */ 
    }

    /* Create output buffer */

    outbuf = (char *)malloc(OUTBUF_SIZE);
    if (outbuf == NULL) {
      printf("Unable to allocate socket output buffer\n");
      return FALSE; /* Error */
    }
  }

  /* 13 Sep 26 dm - OFF, not TRUE.  Inversion on by default meant a session was
     un-inverted only by the VOC login paragraph's PTERM CASE NOINVERT: an
     account without that paragraph had every typed letter case-flipped, which
     was measured on install 80bd15c (PTERM DISPLAY "Case inversion: On") and
     made a lower-case record id arrive upper case. */
  case_inversion = FALSE;
  set_term(TRUE);

  /* Set up signal handler */

  signal(SIGINT, signal_handler);
  signal(SIGHUP, signal_handler);
  signal(SIGTERM, signal_handler);

  /* Set up a signal handler to catch SIGIO generated by arrival of
     input data.                                                       */

  signal(SIGIO, io_handler);
  fcntl(0, F_SETOWN, (int)getpid());
  fcntl(0, F_SETFL, fcntl(0, F_GETFL) | O_NONBLOCK | O_ASYNC);

 

  return TRUE;
}

/* ====================================================================== */

bool init_console() {
  struct stat statbuf;

  /* ----------------------- Display ------------------------ */

  tio.dsp.width = 120;
  tio.dsp.lines_per_page = 36;

  if (connection_type == CN_CONSOLE) {
    /* ----------------------- Keyboard ----------------------- */

    /* Fetch the current terminal settings and attempt to set new ones. */

    ttyin = 0;
    if (!tcgetattr(ttyin, &old_tty_settings)) {
      tty_modes_saved = TRUE;

      /* Construct desired settings */

      new_tty_settings = old_tty_settings;

      new_tty_settings.c_iflag &= ~ISTRIP; /* 8 bit input */
      new_tty_settings.c_iflag |= IGNPAR;  /* Disable parity */
      new_tty_settings.c_iflag &= ~ICRNL;  /* Do not map CR to NL */
      new_tty_settings.c_iflag &= ~IGNCR;  /* Do not discard CR */
      new_tty_settings.c_iflag &= ~INLCR;  /* Do not map NL to CR */
      new_tty_settings.c_iflag &= ~IXON;   /* Kill X-on/off for output... */
      new_tty_settings.c_iflag &= ~IXOFF;  /* ...and input */

      new_tty_settings.c_oflag &= ~OPOST; /* Do not convert LF to CRLF */

      new_tty_settings.c_cflag &= ~CSIZE; /* Enable... */
      new_tty_settings.c_cflag |= CS8;    /* ...8 bit operation */

      new_tty_settings.c_lflag &= ~ICANON; /* No erase/kill processing */
      new_tty_settings.c_lflag |= ISIG;    /* Enable signal processing */
      new_tty_settings.c_lflag &= ~ECHO;   /* Half duplex */
      new_tty_settings.c_lflag &= ~ECHONL; /* No echo of linefeed */

      new_tty_settings.c_cc[VMIN] = 1;     /* Single character input */
      new_tty_settings.c_cc[VQUIT] = '\0'; /* No quit character */
      new_tty_settings.c_cc[VSUSP] = '\0'; /* No suspend character */
      new_tty_settings.c_cc[VEOF] = '\0';  /* No eof character */

      /* Attempt to set device to this mode */

      tcsetattr(ttyin, TCSANOW, &new_tty_settings);
    }
  }

  case_inversion = FALSE;   /* 13 Sep 26 dm - off by default; see the socket path */
  set_term(TRUE);

  fstat(0, &statbuf);
  if (S_ISFIFO(statbuf.st_mode))
    piped_input = TRUE;

  /* Set up signal handler  0351 */

  signal(SIGINT, signal_handler);
  signal(SIGHUP, signal_handler);
  signal(SIGTERM, signal_handler);

  /* Set up a signal handler to catch SIGIO generated by arrival of
     input data.                                                       */

  if (!piped_input) {
    signal(SIGIO, io_handler);
    fcntl(0, F_SETOWN, (int)getpid());
    stdin_modes = fcntl(0, F_GETFL);
    fcntl(0, F_SETFL, stdin_modes | O_NONBLOCK | O_ASYNC);
  }

  return TRUE;
}

/* ======================================================================
   set_term()  -  Set or reset terminal modes                             */

void set_term(trap_break) bool trap_break; /* Treat break char as a break? */
{
  trap_break_char = trap_break;

  if (connection_type == CN_CONSOLE) {
    if (trap_break_char)
      new_tty_settings.c_lflag |= ISIG;
    else
      new_tty_settings.c_lflag &= ~ISIG;
    set_new_tty_modes();
  }
}

/* ======================================================================
   shut_console()  -  Shutdown console functions                          */

void shut_console() {
  if (connection_type == CN_CONSOLE) {
    set_old_tty_modes();

    /* Remove signal handler for SIGIO */

    if (!piped_input) {
      signal(SIGIO, SIG_DFL);
      fcntl(0, F_SETOWN, (int)getpid());
      fcntl(0, F_SETFL, stdin_modes);
    }
  }
}

/* ======================================================================
   set_old_tty_modes()  -  Reset tty to modes it had on entry             */

void set_old_tty_modes() {
  if (tty_modes_saved)
    tcsetattr(ttyin, TCSANOW, &old_tty_settings);
}

/* ======================================================================
   set_new_tty_modes()  -  Reset tty to modes required by SD              */

void set_new_tty_modes() {
  tcsetattr(ttyin, TCSANOW, &new_tty_settings);
}

/* ====================================================================== */

bool write_console(char *p, int bytes) {
  int n;

  while (bytes) {
    n = write(1, p, bytes);
    if (n < 0) /* An error occured */
    {
      if (errno != EAGAIN)
        return FALSE;
      sched_yield();
    } else {
      bytes -= n;
      p += n;
    }
  }

  return TRUE;
}

/* ======================================================================
   Low level keyboard handling functions                                  */

bool keyready() {
  /* If there is type-ahead, we can return immediately */

  if (type_ahead >= 0)
    return TRUE;

  if (piped_input)
    return TRUE;

  input_handler_enabled = FALSE;

  /* Check if there is anything pending on stdin. We may have had
     the SIGIO handler disabled when this arrived.                       */

  if (sdpoll(0, 0) > 0) {
    /* There is something waiting.  Go get it as a type ahead character */
    type_ahead = (char)keyin(0);
  } else {
    /* Ok, so there's nothing out in the Linux world. Is there anything
       in our ring buffer?                                              */

    if (ring_in == ring_out) {
      input_handler_enabled = TRUE;
      return FALSE;
    }

    type_ahead = ring_buff[ring_out];
    ring_out = (ring_out + 1) % RING_SIZE;
  }

  input_handler_enabled = TRUE;
  return TRUE;
}

int16_t keyin(timeout) int timeout; /* Milliseconds */
{
  char c;
  struct timeval tv;
  int64 t1;
  int64 t2;
  int td;
  int poll_ret;
  bool using_autologout = FALSE;

  /* Disable the signal handler. Once this is done, no input can arrive
     from anywhere else. We can then safely test the ring buffer. Because
     we use a signal handler rather than multi-threading, the two styles
     of input cannot be running simulataneously.                          */

  input_handler_enabled = FALSE;

  if (type_ahead >= 0) /* 0211 */
  {
    c = type_ahead;
    type_ahead = -1;
    goto exit_keyin;
  } else {
    if (piped_input) {
      if (read(0, &c, 1) <= 0) {
        process.status = ER_EOF;
        return -1;
      }

      if (c == 10)
        c = inewline;
      goto exit_keyin;
    }

    if (autologout)
      using_autologout = (autologout < timeout) || !timeout;
    if (using_autologout)
      timeout = autologout;

    if (timeout) {
      gettimeofday(&tv, NULL);
      t1 = (((int64)(tv.tv_sec)) * 1000) + (tv.tv_usec / 1000);
    }

    while (ring_in == ring_out) /* Nothing in ring buffer */
    {
      /* Do our own i/o wait so that we can handle events while we are
         waiting. The paths that return special values all re-enable the
         signal handler. If any input arrives between the call to poll()
         and re-enabling the handler, it will be picked up by the next
         call to keyin() or keyready() as it will still be in the queue. */

      do {
        poll_ret = sdpoll(0, (timeout && timeout < 1000) ? timeout : 1000);

        /* 0188 Added check for EINTR so that signals do not cause us
           to terminate the process.                                  */

        if ((poll_ret < 0) && (errno != EINTR)) {
          connection_lost = TRUE;
          k_exit_cause = K_TERMINATE;
        }

        if ((my_uptr != NULL) && (my_uptr->events))
          process_events();

        if (k_exit_cause & K_INTERRUPT) {
          /* Force our way out for logout, etc */
          input_handler_enabled = TRUE;
          return 0;
        }

        if (timeout) {
          gettimeofday(&tv, NULL);
          t2 = (((int64)(tv.tv_sec)) * 1000) + (tv.tv_usec / 1000);
          td = t2 - t1;
          timeout -= td;
          t1 = t2;
          if (timeout <= 0) {
            input_handler_enabled = TRUE;

            if (using_autologout) {
              log_printf("%s\n", sysmsg(2503)); /* Inactivity timer expired -
                                                   Process logged out */
              Sleep(3000);
              k_exit_cause = K_TERMINATE;
            }

            process.status = ER_TIMEOUT;
            return -1;
          }
        }
      } while (poll_ret <= 0);

      /* There should be something waiting for us.  Because we may choose
         to discard whatever is waiting (NUL, quit key, etc), we must go
         round the loop again to check if there is now anything in the
         ring buffer.                                                      */

      do_input();
    }

    /* Grab the character from the ring buffer */

    c = ring_buff[ring_out];
    ring_out = (ring_out + 1) % RING_SIZE;
  }

exit_keyin:

  /* Re-enable the handler. As above, any input arriving in the final
     moments before it was re-enabled will be picked up later.         */

  input_handler_enabled = TRUE;
  return (int16_t)((u_char)c);
}

void io_handler(int sig) {
  /* Collect the input and re-enable the signal */

  if (input_handler_enabled && !in_sh)
    do_input(); /* 0562 */
  signal(SIGIO, io_handler);
}

Private void do_input() {
  char c;
  int16_t n;
  static bool last_was_cr = TRUE; /* May need to skip leading NUL/LF */

again:
  while (!connection_lost) {
    if (sdpoll(0, 0) <= 0)
      break;

    n = (ring_in + 1) % RING_SIZE;
    if (n == ring_out)
      return; /* Ring buffer is full */

    if (read(0, &c, 1) <= 0) {
      if (errno == EAGAIN)
        goto again; /* 0429 io_handler() stole our data */

      connection_lost = TRUE;     /* Lost connection */
      k_exit_cause = K_TERMINATE; /* 0393 */
      c = 0;                      /* 0338 */
                                  // 0338     return;
    }
/* 20240219 mab rebrand VBSRVR to APISRVR */
    if (!is_sdApiSrvr) {
      if (c == tio.break_char) /* The break key */
      {
        if (trap_break_char) {
          break_key();
          continue;
        }
      } else {
        if (((u_char)c == TN_IAC) && telnet_negotiation) {
          (void)negotiate_telnet_parameter();
          continue;
        }
      }
    }

    if (!telnet_binary_mode_in) {
      if (last_was_cr) {
        last_was_cr = FALSE;
        if (c == 0)
          continue; /* Ignore NUL after CR */
        if (c == 10)
          continue; /* Ignore LF after CR */
      }
      last_was_cr = (c == 13);

      if (c == 13)
        c = inewline;
    } else
      last_was_cr = FALSE; /* Ready for exit from binary mode */

    if (ChildPipe >= 0) {
      if (c == inewline)
        c = 10;
      tio_display_string(&c, 1, TRUE, FALSE);
      write(ChildPipe, &c, 1);
    } else {
      /* Pop this character into the ring buffer */

      ring_buff[ring_in] = c;
      ring_in = (ring_in + 1) % RING_SIZE;
    }
  }
}

/* ======================================================================
   inblk()  -  Input a block from the ring buffer                         */

STRING_CHUNK *inblk(int max_bytes) {
  int n;
  int16_t actual_size;
  STRING_CHUNK *str = NULL;
  char *p;
  int bytes;

  n = (ring_in + RING_SIZE - ring_out) % RING_SIZE; /* Bytes in buffer */
  if (n > max_bytes)
    n = max_bytes;

  if (n != 0) {
    str = s_alloc(n, &actual_size); /* Will never be smaller than n */
    str->ref_ct = 1;
    str->string_len = n;
    str->bytes = n;

    bytes = min(RING_SIZE - ring_out, n); /* Portion up to end of ring buffer */
    p = str->data;
    memcpy(p, ((char *)ring_buff) + ring_out, bytes);
    ring_out = (ring_out + bytes) % RING_SIZE;
    n -= bytes;

    if (n) /* More at start of buffer */
    {
      p += bytes;
      memcpy(p, (char *)ring_buff, n);
      ring_out = n;
    }
  }

  return str;
}

/* ======================================================================
   save_screen()  -  Save screen image                                    */

bool save_screen(scrn, x, y, w, h) SCREEN_IMAGE *scrn;
int16_t x;
int16_t y;
int16_t w;
int16_t h;
{
  char *p;
  char *q;
  static int32_t image_id = 0;
  int n;

  if (connection_type == CN_SOCKET) {
    scrn->id = image_id++;
    p = sdtgetstr("sreg");
    if (p != NULL) {
      q = tparm(&n, p, (int)(scrn->id), (int)x, (int)y, (int)w, (int)h);
      write_socket(q, n, TRUE);
    }
  }

  return TRUE;
}

/* ====================================================================== */

void restore_screen(scrn, restore_cursor) SCREEN_IMAGE *scrn;
bool restore_cursor;
{
  char *p;
  char *q;
  int n;

  if (connection_type == CN_SOCKET) {
    p = sdtgetstr("rreg");
    if (p != NULL) {
      q = tparm(&n, p, (int)(scrn->id), (int)(scrn->x), (int)(scrn->y), (int)restore_cursor);
      write_socket(q, n, TRUE);
    }
  }
}

/* Interludes to map onto Windows style interfaces */

bool read_socket(str, bytes) char *str;
int bytes;
{
  while (bytes--)
    *(str++) = (char)keyin(0);
  return 1;
}

char socket_byte() {
  char c;

  read(0, &c, 1);

  return c;
}

/* ======================================================================
   login_user()  -  REMOVED 14 Sep 26 dm, S.18 (the Windows port removed its
   own 17 Aug 26).

   It authenticated APISRVR's request 24, the cleartext network login, by
   two paths: APILOGIN=1 checked the password against /etc/shadow with
   crypt() and dropped to that user; APILOGIN=0 skipped the password and
   dropped to the Unix-socket peer uid getpeereid() had read in
   start_connection().  Request 24 was retired by SCRAM phase 5 (9fd52d9,
   witnessed 171/171) and its handler no longer calls login(), so neither
   path had a caller.  The API now proves the password with SCRAM against
   $cred (APISRVR requests 47/48), sets the name with K$SET.USERNAME and
   takes the Linux identity - initgroups, setgid, setuid, the S.15 order -
   with K$ASSUME.USER (op_kernel.c).                                        */

/* ======================================================================
   Signal handler                                                         */

void signal_handler(signum) int signum;
{
  switch (signum) {
    case SIGINT:
      break_key();
      break;

    case SIGHUP:
    case SIGTERM:
      signal(SIGHUP, SIG_IGN);
      signal(SIGTERM, SIG_IGN);
      log_printf("Received termination signal %d\n", signum);
      if (my_uptr != NULL)
        my_uptr->events |= EVT_TERMINATE; /* 0393 */
      break;
  }
}

/* ======================================================================
   flush_outbuf()  -  Flush socket output buffer                          */

bool flush_outbuf() {
  if (outbuf_bytes) {
    if (!write_console(outbuf, outbuf_bytes))
      return FALSE;
    outbuf_bytes = 0;
  }

  return TRUE;
}

/* ====================================================================== */

int sdpoll(int fd, int timeout) {
#ifdef DO_NOT_USE_POLL
  fd_set fds;
  struct timeval tv;

  FD_ZERO(&fds);
  FD_SET(fd, &fds);
  tv.tv_sec = timeout / 1000;
  tv.tv_usec = (timeout % 1000) * 1000;
  return select(1, &fds, NULL, NULL, &tv);
#else
  struct pollfd fds[1];

  fds[0].fd = fd;
  fds[0].events = POLLIN;

  return poll(fds, 1, timeout);
#endif
}

/* END-CODE */
