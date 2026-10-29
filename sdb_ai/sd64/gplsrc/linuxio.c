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
 * 28 Oct 26 dm  S.88 review of L2: keyin_idle_ms() gives the inactivity clock (idle_waited, 0 unless the last wait ended by its own timeout) to kernel(K$AUTOLOGOUT, -2), so the
 *               IDE's countdown reads the clock AUTOLOGOUT really uses.
 * 28 Oct 26 dm  S.88 phase 2 (S3): AUTOLOGOUT measures idle time ACROSS keyin() calls.  A wait that ends by its own timeout
 *               no longer starts the inactivity clock again, so the screen library's one-second polling cannot keep a
 *               session alive; a byte of input or an interrupt starts it again as before.  A program that never gives keyin()
 *               a timeout waits exactly as it did.
 * 28 Oct 26 dm  S.88 phase 2 review: with nothing carried the AUTOLOGOUT test is the old strict "period < timeout" again, so a
 *               timed wait equal to the period is a plain timeout as before; "<=" applies only to a carried clock.  KNOWN AND
 *               INTENDED: a program that polls the keyboard with very short timed KEYINs and works between them counts as
 *               waiting - the polls add up with nothing typed and AUTOLOGOUT eventually logs it out; only a key resets it.
 * 27 Oct 26 dm  S.87 batch 14: terminal input case inversion (INVCASE, PTERM CASE) is removed; a session starts as it always did with it off.
 * 18 Oct 26 dm init_console() starts the display at DEFAULT_WIDTH by DEFAULT_DEPTH (140 by 42, was
 *           120 by 36) instead of two literals; a tty still overrides it (read_window_size()).
 * 15 Oct 26 dm do_input(): end of file was tested against a stale errno, so after
 *           any earlier EAGAIN a session whose client had gone looped for ever.
 * 07 Oct 26 dm PAL-1 stage 3a: the API command processor is $apisrvr, lower case.
 * 15 Sep 26 dm S.19: every API connection goes through a TLS 1.3 relay
 *           (sd_tlssrv.c), started after the peer is recorded; the Ack moved
 *           after it, inside TLS.  Identity in <sd.conf's dir>/sd-tls.
 * 14 Sep 26 dm S.17: a TCP API connection records the PEER's address and port
 *           (getpeername), not the listener's, so APISRVR can tell local from not.
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

/* 19 Sep 26 dm - _GNU_SOURCE, AND IT MUST PRECEDE EVERY INCLUDE.  struct ucred
   and SO_PEERCRED are glibc extensions gated on it; -std=gnu17 does NOT imply
   it (measured: without this the file fails with "storage size of 'cr' isn't
   known", with it the same code compiles clean).  Defined here rather than in
   the Makefile's C_FLAGS so it changes this file's feature set and no other. */
#define _GNU_SOURCE

#include "sd.h"
#include "config.h"
#include "err.h"
#include "header.h"
#include "sdnet.h"
#include "sdtermlb.h"
#include "telnet.h"
#include "tio.h"
#include "sd_tls.h"

#include <netdb.h>
#include <pwd.h>
#include <grp.h>
#include <signal.h>
#include <sys/ioctl.h>
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

/* 13 Oct 26 dm - THE TERMINAL'S OWN SIZE.  Until now SD never asked the tty how big it was: the display was terminfo's 120 by
   36 (since 18 Oct 26, 140 by 42) unless the user typed TERM w,h or the environment happened to carry COLUMNS and LINES, so a program on an 80 by 24 terminal
   drew for 120 by 36 (LIST paged at 36 lines, @(x, y) past the real edge went off the screen).  The tty is asked at start-up
   and again at every SIGWINCH, and the answer becomes the display's width and lines per page.  TERM w,h still sets them by
   hand, and holds until the next resize.  Nothing is read when there is no tty (a pipe, a phantom, the API).
   win_cols and win_rows are what the tty last said (0 0: it has not been able to); winch_seen is set when the display has
   changed and its data lines per page (set_data_lines() in op_tio.c, which is not safe in a signal handler) are yet to be
   worked out.                                                                                                             */
Private int win_cols = 0;
Private int win_rows = 0;
Private volatile sig_atomic_t winch_seen = 0;
Private bool read_window_size(void);
Private void winch_handler(int sig);

/* Keyboard */

Private int ttyin = 0;
Private struct termios old_tty_settings;
Private struct termios new_tty_settings;
Private bool tty_modes_saved = FALSE;
Private int16_t type_ahead = -1;

/* 28 Oct 26 dm - S.88 phase 2 (S3): THE INACTIVITY CLOCK OF AUTOLOGOUT.  idle_waited is the time, in milliseconds, that keyin()
   has spent waiting with nothing typed since the last real input.  idle_carry says that the last keyin() ended because ITS
   OWN TIMEOUT ran out: only then does the next keyin() go on counting from idle_waited.  Any other end - a byte of input, an
   interrupt (the break key, a logout) - leaves idle_carry FALSE and the next wait starts the clock from 0, as every wait did
   before.  The time a program spends between two waits (drawing, computing) is NOT counted: only time spent waiting is.  */
Private int64 idle_waited = 0;
Private bool idle_carry = FALSE;

Private void signal_handler(int signum);

void set_term(bool trap_break);
void set_old_tty_modes(void);
void set_new_tty_modes(void);
bool negotiate_telnet_parameter(void);

/* ======================================================================
   api_tls_dir()  -  Where the API's TLS relay keeps the server identity

   15 Sep 26 dm - S.19.  Beside sd.conf: <its directory>/sd-tls, normally
   /etc/sd-tls.  NOT under SDSYS, for two reasons measured in installsdcore.sh:
   the installer runs chown -R sdsys and chmod -R 755 over SDSYS, which would
   leave the key readable and fail the relay's owner check; and the sdsys
   account owns SDSYS, so it could rename a root-owned directory away and
   force a silent new key.  /etc is root's.  Derived from config_path because
   this runs before bind_sysseg() - there is no sysseg->sysdir yet.       */

Private bool api_tls_dir(char *out, size_t len) {
  char *slash = strrchr(config_path, '/');
  int n;

  if (slash == NULL || slash == config_path)
    return FALSE;
  n = snprintf(out, len, "%.*s/sd-tls", (int)(slash - config_path),
               config_path);
  return (n > 0) && ((size_t)n < len);
}

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
    strcpy(command_processor, "$apisrvr");
    
/* 20240219 mab rebrand VBSRVR to APISRVR */
  if (connection_type == CN_SOCKET) {
    if (is_sdApiSrvr) {
     // flag = TRUE;
     // setsockopt(0, IPPROTO_TCP, TCP_NODELAY, (char *)&flag, sizeof(int));
      /* 15 Sep 26 dm - S.19: the Ack moved below the peer capture, after the
         TLS relay starts, so that it travels inside TLS.  The client still
         waits for it before speaking.                                     */
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
           user reaches it, as any reaches 127.0.0.1:4247.  The socket is kept
           - an ssh -L tunnel reaches it.                                      */
        /* 19 Sep 26 dm - AND THE PEER'S CREDENTIAL IS READ AGAIN, AS A CHECK
           AND NEVER AS AN AUTHENTICATION - which is the distinction S.18 was
           right about.  SCRAM still proves who the caller is; this only says
           which local user the connecting PROCESS runs as, so APISRVR can
           require that SDSYS's API session really is sdsys on this machine
           (owner's ruling, 19 Sep 2026: sdsys keeps local API access, and it
           is worth a second password to have it).
           SO_PEERCRED, not getpeereid(): the same answer without bringing back
           the libbsd dependency S.18 removed.
           HERE, NOT LATER: below this switch the TLS relay takes descriptor 0,
           and from that point the credential would describe the relay, exactly
           as the comment on getpeername() says of the address.
           FAILURE LEAVES peer_user EMPTY, and empty is refused by the caller.  */
        {
          struct ucred cr;
          socklen_t crlen = sizeof(cr);
          struct passwd *pw;

          if (getsockopt(0, SOL_SOCKET, SO_PEERCRED, &cr, &crlen) == 0
              && (pw = getpwuid(cr.uid)) != NULL) {
            strncpy(peer_user, pw->pw_name, MAX_USERNAME_LEN);
            peer_user[MAX_USERNAME_LEN] = '\0';
            syslog(LOG_INFO, "Connection over Unix socket %s from uid %d (%s)",
                   ip_addr, (int)cr.uid, peer_user);
          } else {
            syslog(LOG_INFO, "Connection over Unix socket %s; no peer "
                             "credential (SO_PEERCRED failed)", ip_addr);
          }
        }
        break;

      case PF_INET:
        /* 10 Sep 26 dm - accept TCP, but for the API server ONLY, deliberately
           reversing the 2024-02-19 "AF_UNIX only" restriction for that one path.
           The API server authenticates the connection by SCRAM (APISRVR
           requests 47/48).  The listener binds 127.0.0.1:4247 by default
           (4243 before 2 Oct 26 - the owner fixed SD Core's ports then);
           installsdcore.sh opens it to 0.0.0.0:4247 and the firewall only on
           "Allow API access".  A non-API TCP connection is still refused.

           14 Sep 26 dm - S.17: ip_addr/port_no are now the PEER's, from
           getpeername(), as the Windows port's are.  They were the listener's
           own end (getsockname): the address a connection was SENT TO, not
           where it came from.  The two usually agree about loopback, but not
           always - a connection forwarded to 127.0.0.1 from elsewhere would
           have read as local - and the question APISRVR asks of system(42)
           (!peer_local) is where it came from.  A failed getpeername() leaves
           "?", which !peer_local does not call local, so the gate refuses
           rather than guessing. */
        {
          struct sockaddr_storage pa;
          socklen_t palen = sizeof(pa);
          struct sockaddr_in* s = (struct sockaddr_in*)&pa;
          if ((getpeername(0, (struct sockaddr *)&pa, &palen) != 0) || (pa.ss_family != AF_INET)) {
            strncpy(ip_addr, "?", MAX_SOCKET_ADDR_STR_LEN - 1);
            port_no = 0;
          } else {
            port_no = ntohs(s->sin_port);
            if (inet_ntop(AF_INET, &s->sin_addr, ip_addr, MAX_SOCKET_ADDR_STR_LEN) == NULL)
              strncpy(ip_addr, "?", MAX_SOCKET_ADDR_STR_LEN - 1);
          }
          if (!is_sdApiSrvr) {
            syslog(LOG_INFO, "Refusing PF_INET connection (not API server) from %s", ip_addr);
            return FALSE; /* Error */
          }
          syslog(LOG_INFO, "API connection over TCP from %s port %d (SD login required)", ip_addr, port_no);
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

    /* 15 Sep 26 dm - S.19: EVERY API CONNECTION IS TLS 1.3, over TCP and over
       the Unix socket alike - an ssh -L tunnel to either must keep working,
       and one rule has no downgrade branch to get wrong.  AFTER the peer is
       recorded above: once descriptor 0 is the relay's socketpair,
       getpeername() would describe the relay.  BEFORE the ACK, so the ACK
       and everything after it travel inside TLS.  BEFORE bind_sysseg(), so
       the relay never maps SD's shared memory.  See sd_tlssrv.c.          */
    if (is_sdApiSrvr) {
      char tls_dir[MAX_PATHNAME_LEN + 16];
      char tls_err[512];

      if (!api_tls_dir(tls_dir, sizeof(tls_dir))) {
        syslog(LOG_ERR, "API connection refused: no usable SDSYS= in %s",
               config_path);
        return FALSE;
      }
      if (!sd_tls_relay_start(tls_dir, SD_TLS_HANDSHAKE_MS, tls_err,
                              sizeof(tls_err))) {
        syslog(LOG_INFO, "API connection from %s refused: %s", ip_addr,
               tls_err);
        return FALSE;
      }

      /* Fire an Ack character up the connection to start the conversation.
         Moved here from the top of this function by S.19: it now goes
         through the relay, inside TLS.                                    */
      send(0, "\x06", 1, 0);
    }

    /* Create output buffer */

    outbuf = (char *)malloc(OUTBUF_SIZE);
    if (outbuf == NULL) {
      printf("Unable to allocate socket output buffer\n");
      return FALSE; /* Error */
    }
  }

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

  /* 18 Oct 26 dm - what a session with no tty to ask has until LOGIN sets it (from LINES and COLUMNS, terminfo or
     DEFAULT.WIDTH/DEPTH): 140 by 42, tio.h.  A tty replaces it at once, below (read_window_size()).             */

  tio.dsp.width = DEFAULT_WIDTH;
  tio.dsp.lines_per_page = DEFAULT_DEPTH;

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

  /* 13 Oct 26 dm - the terminal's own size, now and at every resize (see win_cols above) */

  if (read_window_size())
    winch_seen = 1;
  signal(SIGWINCH, winch_handler);

  return TRUE;
}

/* ======================================================================
   read_window_size()  -  Ask the tty how big it is
   Returns TRUE and sets the display's width and lines per page if it said.
   Only ioctl() and plain stores, so it is safe in a signal handler.  The
   least width and depth are LOGIN's (MIN.WIDTH 20, MIN.DEPTH 10).         */

Private bool read_window_size() {
  struct winsize ws;

  if ((ioctl(0, TIOCGWINSZ, &ws) != 0) || (ws.ws_col == 0) || (ws.ws_row == 0))
    return FALSE;

  win_cols = ws.ws_col;
  win_rows = ws.ws_row;
  tio.dsp.width = (win_cols < 20) ? 20 : win_cols;
  tio.dsp.lines_per_page = (win_rows < 10) ? 10 : win_rows;
  return TRUE;
}

/* ======================================================================
   winch_handler()  -  SIGWINCH: the terminal has been resized            */

Private void winch_handler(sig) int sig;
{
  (void)sig;
  if (read_window_size())
    winch_seen = 1;
}

/* ======================================================================
   console_resized()  -  Has the display changed since the data lines per
   page were last worked out?  Answers once per change.                    */

Public bool console_resized() {
  if (!winch_seen)
    return FALSE;
  winch_seen = 0;
  return TRUE;
}

/* ======================================================================
   console_window_size()  -  What the tty last said its size was
   Returns FALSE (and leaves *cols and *rows alone) if it never has.       */

Public bool console_window_size(cols, rows) int *cols;
int *rows;
{
  if ((win_cols == 0) || (win_rows == 0))
    return FALSE;
  *cols = win_cols;
  *rows = win_rows;
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

  /* 20 Oct 26 dm - S.71: nothing is ready from a connection that has gone, and nothing will be.  A hung-up descriptor is always
     "readable", so poll() below said there was something, keyin() gave back a character, and CLEARINPUT (op_clrinput(), and the
     input clearing in the break handler) turned for ever on `while (keyready()) keyin(0)`.  The ring still counts: what arrived before
     the loss is ready.                                                                                                              */
  if (connection_lost && (ring_in == ring_out)) {
    k_exit_cause = K_TERMINATE;
    return FALSE;
  }

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

/* ======================================================================
   type_ahead_count()  -  Characters waiting to be read (SYSTEM(14), 15 Oct 26, QM4 gaps Q-18)

   The one the kernel has taken from the terminal ahead of time, the ring buffer the input signal handler fills, and what
   the operating system still holds for stdin.  For piped input the third is whatever is in the pipe now, so the figure
   is a snapshot (the manual calls it unreliable for piped input, and so it is here).                                    */

int32_t type_ahead_count() {
  int32_t n;
  int waiting = 0;

  input_handler_enabled = FALSE;
  n = (type_ahead >= 0) ? 1 : 0;
  n += (ring_in - ring_out + RING_SIZE) % RING_SIZE;
  if (ioctl(0, FIONREAD, &waiting) == 0 && waiting > 0)
    n += waiting;
  input_handler_enabled = TRUE;
  return n;
}

/* 28 Oct 26 dm - S.88 review of L2: the inactivity clock, for kernel(K$AUTOLOGOUT, -2): how long this process has waited with nothing typed, in milliseconds, as AUTOLOGOUT
   itself will judge it at the next keyin() - the clock runs on only while the last wait ended by its own timeout, so after a key (or an interrupt) it is 0.  Read only, and only
   the process's own.  The IDE's countdown used to GUESS this from what it could see (a wait that took long, a change in the editor) and was late by an AI wait and by a stall. */
int32_t keyin_idle_ms(void) {
  int64 ms = idle_carry ? idle_waited : 0;

  return (ms > 0x7FFFFFFF) ? 0x7FFFFFFF : (int32_t)ms;
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
  int64 idle_left = 0; /* ms of inactivity AUTOLOGOUT still allows */

  /* Disable the signal handler. Once this is done, no input can arrive
     from anywhere else. We can then safely test the ring buffer. Because
     we use a signal handler rather than multi-threading, the two styles
     of input cannot be running simulataneously.                          */

  input_handler_enabled = FALSE;

  /* 28 Oct 26 dm - S.88 phase 2 (S3): the inactivity clock goes on only from a wait that ended by its own timeout */
  if (!idle_carry)
    idle_waited = 0;
  idle_carry = FALSE;

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

    /* 28 Oct 26 dm - S.88 phase 2 (S3): AUTOLOGOUT is measured against the time ALREADY waited with nothing typed
       (idle_waited), not from the start of this call.  It used to be "(autologout < timeout) || !timeout" with the
       whole period every call, so a program that waited a second at a time (the screen library's $sl_key, the IDE,
       the home screen, every tool page) restarted the period every second and was never logged out.  The wait now
       ends at whichever comes first: the caller's own timeout (a plain timeout, the clock carried to the next call)
       or the rest of the inactivity period (the logout, as before).  A wait with no timeout of its own takes the
       rest of the period, which is the whole period unless a timed wait came before it with nothing typed.     */
    /* 28 Oct 26 dm - S.88 phase 2 review: with nothing carried (idle_waited is 0) the test is the old strict one, so a timed
       wait EQUAL to the AUTOLOGOUT period is a plain timeout as it always was; only a carried clock ends a wait at the
       logout when the rest of the period equals the caller's timeout (the inactivity has then reached the whole period). */
    if (autologout) {
      idle_left = (int64)autologout - idle_waited;
      if (idle_left < 1)
        idle_left = 1;
      if (!timeout)
        using_autologout = TRUE;
      else if (idle_waited == 0)
        using_autologout = (idle_left < (int64)timeout);
      else
        using_autologout = (idle_left <= (int64)timeout);
    }
    if (using_autologout)
      timeout = (int)idle_left;

    if (timeout) {
      gettimeofday(&tv, NULL);
      t1 = (((int64)(tv.tv_sec)) * 1000) + (tv.tv_usec / 1000);
    }

    while (ring_in == ring_out) /* Nothing in ring buffer */
    {
      /* 20 Oct 26 dm - S.71: A LOST CONNECTION IS FINAL.  Once do_input() has seen the end of the connection there is nothing more
         to wait for, and the loop below cannot leave on its own: poll() says POLLHUP at once and the connection is never read
         again (do_input() does nothing after the loss), so the only way out was k_exit_cause holding an interrupt bit.  Measured
         with gdb on a spinning server: connection_lost 1, k_exit_cause 0 - something had cleared it (what is NOT established; the
         candidate is kernel.c zeroing it when a program starts, after the input signal had recorded the loss), and an API
         server whose client went before its first request polled at 100% of a processor for ever.  So the loss is told again here,
         every time, whatever cleared k_exit_cause: terminate, and give back 0 as every other interrupt does, without waiting.  The
         ring is read first (the test is inside this loop), so what the client sent before it went is still read.              */
      if (connection_lost) {
        k_exit_cause = K_TERMINATE;
        input_handler_enabled = TRUE;
        return 0;
      }

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
          idle_waited += td; /* 28 Oct 26 S.88 (S3): the time waited with nothing typed */
          t1 = t2;
          if (timeout <= 0) {
            input_handler_enabled = TRUE;

            if (using_autologout) {
              log_printf("%s\n", sysmsg(2503)); /* Inactivity timer expired -
                                                   Process logged out */
              Sleep(3000);
              k_exit_cause = K_TERMINATE;
            } else {
              idle_carry = TRUE; /* 28 Oct 26 S.88 (S3): the caller's own timeout: the next wait goes on counting */
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

  /* 12 Oct 26 (openQM item 155): PTERM MARK - ctrl-\ (28), ctrl-] (29) and
     ctrl-^ (30) typed at the keyboard are the subvalue, value and field marks,
     in that order (openQM item 254 had the first two swapped). */
  if (mark_input) {
    switch ((u_char)c) {
      case 28:
        c = SUBVALUE_MARK;
        break;
      case 29:
        c = VALUE_MARK;
        break;
      case 30:
        c = FIELD_MARK;
        break;
    }
  }

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
  ssize_t got;
  static bool last_was_cr = TRUE; /* May need to skip leading NUL/LF */

again:
  while (!connection_lost) {
    if (sdpoll(0, 0) <= 0)
      break;

    n = (ring_in + 1) % RING_SIZE;
    if (n == ring_out)
      return; /* Ring buffer is full */

    got = read(0, &c, 1);

    /* 15 Oct 26 - errno is only meaningful after a read that returned -1.  End of file (0) leaves it as it was, so an
       EAGAIN left by any earlier call (a lock attempt that failed, a write that would have blocked) made this test
       send an ended connection round the loop for ever: poll said hung up, read said nothing, errno still said try
       again.  Two API sessions busy on one file left servers running at 100% of a processor after their clients had
       gone.                                                                                                      */
    if ((got < 0) && (errno == EAGAIN))
      goto again; /* 0429 io_handler() stole our data */

    if (got <= 0) {
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
  /* 13 Oct 26: the terminal no longer keeps the image.  It used to be asked to, with the 'sreg' capability, by
     AccuTerm and by SDTerm, neither of which SD supports now; SAVE.SCREEN() gives an image that holds nothing
     outside this process and RESTORE.SCREEN writes nothing.  (The library's SCREEN statement keeps its own
     shadow of what it draws and puts it back itself.) */
  static int32_t image_id = 0;

  scrn->id = image_id++;
  return TRUE;
}

/* ====================================================================== */

void restore_screen(scrn, restore_cursor) SCREEN_IMAGE *scrn;
bool restore_cursor;
{
  /* nothing: see save_screen() */
}

/* Interludes to map onto Windows style interfaces */

/* 20 Oct 26 dm - S.71: read_socket() gave up on nothing.  It took keyin(0) once for each byte asked for and never looked at what keyin()
   said, so a connection that had gone, or a process told to terminate, turned the rest of the read into a loop of zero bytes
   (and, behind op_readpkt(), one 16 KB chunk of memory for every 16,358 of them, for a length of 1,651,663,207).  keyin() answers 0 with
   an interrupt cause set when it has given up (a lost connection sets K_TERMINATE, as above), or -1 at the end of piped input: the
   read ends there, FALSE and ER_EOF, as the callers already test.                                                                 */
bool read_socket(str, bytes) char *str;
int bytes;
{
  int16_t c;

  while (bytes--) {
    c = keyin(0);
    if ((c < 0) || ((c == 0) && (k_exit_cause & K_INTERRUPT))) {
      process.status = ER_EOF;
      return FALSE;
    }
    *(str++) = (char)c;
  }
  return TRUE;
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
