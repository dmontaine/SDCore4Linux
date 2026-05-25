/* LNXPORT.C
 * Port i/o opcodes for Linux/FreeBSD
 * Copyright (c) 2005 Ladybridge Systems, All Rights Reserved
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
 * 31 Dec 23 SD launch - prior history suppressed
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * closeport()       Close a port
 * is_port()         Does name reference a port?
 * openport()        Open a port
 * readport()        Read data from a port
 * writeport()       Write data to a port
 * op_getport()      GET.PORT.PARAMS()
 * op_setport()      SET.PORT.PARAMS()
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "sdnet.h"

#include <errno.h>
#include <sys/ioctl.h>
#include <termios.h>

static bool set_port_baud(struct termios* tty, int baud) {
  speed_t speed;

  switch (baud) {
    case 110:
      speed = B110;
      break;
    case 300:
      speed = B300;
      break;
    case 600:
      speed = B600;
      break;
    case 1200:
      speed = B1200;
      break;
    case 2400:
      speed = B2400;
      break;
    case 4800:
      speed = B4800;
      break;
    case 9600:
      speed = B9600;
      break;
    case 19200:
      speed = B19200;
      break;
    case 38400:
      speed = B38400;
      break;
#ifdef TTY_50_75_134_150_200_1800
    case 50:
      speed = B50;
      break;
    case 75:
      speed = B75;
      break;
    case 134:
      speed = B134;
      break;
    case 150:
      speed = B150;
      break;
    case 200:
      speed = B200;
      break;
    case 1800:
      speed = B1800;
      break;
#endif
#ifdef TTY_57600_115200_230400
    case 57600:
      speed = B57600;
      break;
    case 115200:
      speed = B115200;
      break;
    case 230400:
      speed = B230400;
      break;
#endif
    default:
      return FALSE;
  }

  if (cfsetispeed(tty, speed) != 0 || cfsetospeed(tty, speed) != 0)
    return FALSE;
  return TRUE;
}

static int baud_from_speed(speed_t speed) {
  switch (speed) {
    case B110:
      return 110;
    case B300:
      return 300;
    case B600:
      return 600;
    case B1200:
      return 1200;
    case B2400:
      return 2400;
    case B4800:
      return 4800;
    case B9600:
      return 9600;
    case B19200:
      return 19200;
    case B38400:
      return 38400;
#ifdef TTY_50_75_134_150_200_1800
    case B50:
      return 50;
    case B75:
      return 75;
    case B134:
      return 134;
    case B150:
      return 150;
    case B200:
      return 200;
    case B1800:
      return 1800;
#endif
#ifdef TTY_57600_115200_230400
    case B57600:
      return 57600;
    case B115200:
      return 115200;
    case B230400:
      return 230400;
#endif
    default:
      return 0;
  }
}

/* ======================================================================
   closeport()  -  Close a port                                           */

void closeport(int hPort) {
  if (hPort >= 0)
    (void)close(hPort);
}

/* ======================================================================
   is_port()  -  Check if name references a port                          */

bool is_port(char* name) {
  int fu;
  bool result = FALSE;

  if (name == NULL)
    return FALSE;

  if (memcmp(name, "/dev/", 5) == 0) {
    fu = open(name, O_RDONLY | O_NONBLOCK);
    if (fu >= 0) {
      result = isatty(fu);
      (void)close(fu);
    }
  }

  return result;
}

/* ======================================================================
   openport()  -  Open a port                                             */

int openport(char* name) {
  int hPort;

  if (name == NULL || name[0] == '\0') {
    process.os_error = EINVAL;
    return -1;
  }

  hPort = open(name, O_RDWR | O_NONBLOCK, S_IREAD | S_IWRITE);
  if (hPort < 0)
    process.os_error = errno;
  return hPort;
}

/* ======================================================================
   readport()  -  Read data from port                                     */

int readport(int hPort, char* str, int16_t bytes) {
  ssize_t n;

  if (str == NULL || bytes <= 0 || hPort < 0)
    return 0;

  n = read(hPort, str, (size_t)bytes);
  if (n < 0)
    process.os_error = errno;
  return (int)n;
}

/* ======================================================================
   writeport()  -  Write data to port                                     */

bool writeport(int hPort, char* str, int16_t bytes) {
  ssize_t n;

  if (bytes <= 0)
    return TRUE;
  if (str == NULL || hPort < 0)
    return FALSE;

  n = write(hPort, str, (size_t)bytes);
  return (n == (ssize_t)bytes);
}

/* ======================================================================
   op_getport()  -  GET.PORT.PARAMS()                                     */

void op_getport() {
  /* Stack:

     |=============================|=============================|
     |            BEFORE           |           AFTER             |
     |=============================|=============================|
 top |  ADDR to file variable      | Dynamic array               |
     |=============================|=============================|
                    
 */

  DESCRIPTOR* descr;
  FILE_VAR* fvar;
  SQ_FILE* sq_file;
  STRING_CHUNK* str = NULL;
  int n1, n2, n3, n4, n5;
  speed_t ospeed;

  struct termios tty_settings;

  descr = e_stack - 1;
  k_get_file(descr);
  fvar = descr->data.fvar;

  ts_init(&str, 128);

  if (fvar->type != SEQ_FILE) {
    process.status = ER_NSEQ;
    goto exit_op_getport;
  }

  sq_file = fvar->access.seq.sq_file;
  if (!(sq_file->flags & SQ_PORT)) {
    process.status = ER_NPORT;
    goto exit_op_getport;
  }

  if (tcgetattr(sq_file->fu, &tty_settings) != 0) {
    process.status = ER_NPORT;
    process.os_error = errno;
    goto exit_op_getport;
  }

  ospeed = cfgetospeed(&tty_settings);
  n1 = baud_from_speed(ospeed);

  /* Parity */

  if ((tty_settings.c_cflag & PARENB) == 0)
    n2 = 0;
  else
    n2 = (tty_settings.c_cflag & PARODD) ? 1 : 2;

  /* Byte size */

  n3 = 8;
  switch (tty_settings.c_cflag & CSIZE) {
    case CS5:
      n3 = 5;
      break;
    case CS6:
      n3 = 6;
      break;
    case CS7:
      n3 = 7;
      break;
    case CS8:
      n3 = 8;
      break;
    default:
      break;
  }

  /* Stop bits */

  n4 = (tty_settings.c_cflag & CSTOPB) ? 2 : 1;

  /* Status bits */

  n5 = 0;
  if (ioctl(sq_file->fu, TIOCMGET, &n5) < 0)
    n5 = 0;

  ts_printf(
      "%s\xfe%d\xfe%d\xfe%d\xfe%d\xfe%d\xfe%d\xfe%d\xfe%d",
      (sq_file->pathname != NULL) ? sq_file->pathname : "",
      n1,
      n2,
      n3,
      n4,
      (n5 & TIOCM_CTS) != 0,
      (n5 & TIOCM_DSR) != 0,
      (n5 & TIOCM_RNG) != 0,
      (n5 & TIOCM_CAR) != 0);

  process.status = 0;

exit_op_getport:
  ts_terminate();

  k_release(descr);
  InitDescr(descr, STRING);
  descr->data.str.saddr = str;
}

/* ======================================================================
   op_setport()  -  SET.PORT.PARAMS()                                     */

void op_setport() {
  /* Stack:

     |=============================|=============================|
     |            BEFORE           |           AFTER             |
     |=============================|=============================|
 top |  Dynamic array              | 1 = OK, 0  = Error          |
     |-----------------------------|-----------------------------|
     |  ADDR to file variable      |                             |
     |=============================|=============================|

     If an error is reported, STATUS() contains the o/s error number.
 */

  DESCRIPTOR* descr;
  FILE_VAR* fvar;
  SQ_FILE* sq_file;
  char params[256 + 1];
  struct termios tty_settings;
  int n1, n2, n3, n4;
  char* p;

  descr = e_stack - 1; /* New parameters */
  if (k_get_c_string(descr, params, 256) < 0) {
    process.status = ER_LENGTH;
    goto exit_op_setport;
  }

  descr = e_stack - 2; /* File variable */
  k_get_file(descr);
  fvar = descr->data.fvar;

  if (fvar->type != SEQ_FILE) {
    process.status = ER_NSEQ;
    goto exit_op_setport;
  }

  sq_file = fvar->access.seq.sq_file;
  if (!(sq_file->flags & SQ_PORT)) {
    process.status = ER_NPORT;
    goto exit_op_setport;
  }

  p = strchr(params, '\xfe');
  if ((p == NULL) ||
      (sscanf(p + 1, "%d\xfe%d\xfe%d\xfe%d", &n1, &n2, &n3, &n4) != 4)) {
    process.status = ER_PARAMS;
    goto exit_op_setport;
  }

  if (n2 < 0 || n2 > 2 || (n4 != 1 && n4 != 2)) {
    process.status = ER_PARAMS;
    goto exit_op_setport;
  }

  if (tcgetattr(sq_file->fu, &tty_settings) != 0) {
    process.status = ER_NPORT;
    process.os_error = errno;
    goto exit_op_setport;
  }

  if (!set_port_baud(&tty_settings, n1)) {
    process.status = ER_PARAMS;
    goto exit_op_setport;
  }

  /* Parity */

  if (n2) {
    tty_settings.c_cflag |= PARENB;
    if (n2 == 1)
      tty_settings.c_cflag |= PARODD;
    else
      tty_settings.c_cflag &= ~PARODD;
  } else
    tty_settings.c_cflag &= ~PARENB;

  /* Byte size */

  tty_settings.c_cflag &= ~CSIZE;
  switch (n3) {
    case 5:
      tty_settings.c_cflag |= CS5;
      break;
    case 6:
      tty_settings.c_cflag |= CS6;
      break;
    case 7:
      tty_settings.c_cflag |= CS7;
      break;
    case 8:
      tty_settings.c_cflag |= CS8;
      break;
    default:
      process.status = ER_PARAMS;
      goto exit_op_setport;
  }

  /* Stop bits */

  if (n4 == 2)
    tty_settings.c_cflag |= CSTOPB;
  else
    tty_settings.c_cflag &= ~CSTOPB;

  if (tcsetattr(sq_file->fu, TCSANOW, &tty_settings) != 0) {
    process.os_error = errno;
    process.status = ER_PARAMS;
  } else
    process.status = 0;

exit_op_setport:
  k_dismiss();
  k_dismiss();

  InitDescr(e_stack, INTEGER);
  (e_stack++)->data.value = (process.status == 0);
}

/* END-CODE */
