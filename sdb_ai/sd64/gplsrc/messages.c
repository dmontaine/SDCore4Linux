/* MESSAGES.C
 * Message handler.
 * Copyright (c) 2006 Ladybridge Systems, All Rights Reserved
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
 * rev 0.9.1 Mar 25 mab correct output of messages with embedded newline
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * The message library (SDSYS MESSAGES file) uses numbers to identify
 * messages. For non-English texts, the message number is prefixed by a
 * language code of up to three letters.
 *
 * Message numbers are groups according to their role. Open source
 * developers should use numbers in the range 10000 to 19999.
 *
 * Messages that are called from SDBasic using the sysmsg() function
 * can include up to four arguments referenced as %1 to %4. These tokens
 * may appear in any order.
 *
 * Messages that are called for C, use conventional printf style tokens
 * and are therefore both type and order sensitive.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#define MSG_ALLOC_ID 82
#define MSG_MAX_RECORD 65536
#define MSG_ID_SIZE 16

Private char prefix[3 + 1] = ""; /* Language prefix */

char* month_names[12] = {"January",   "February", "March",    "April",
                         "May",       "June",     "July",     "August",
                         "September", "October",  "November", "December"};
char* day_names[7] = {"Monday", "Tuesday",  "Wednesday", "Thursday",
                      "Friday", "Saturday", "Sunday"};

Private char* message = NULL;
Private int message_len;
Private int msg_dir_state; /* 0 = unchecked, 1 = OK, -1 = missing */
Private char fallback_msg[256];

/* Grow the shared message buffer to hold at least need bytes (with NUL). */

static bool grow_message_buf(int need) {
  int n;
  char* nb;

  if (need <= 0 || need > MSG_MAX_RECORD)
    return FALSE;

  if (message != NULL && need <= message_len)
    return TRUE;

  n = ((need + 127) / 128) * 128;
  if (message != NULL)
    k_free(message);
  nb = (char*)k_alloc(MSG_ALLOC_ID, n);
  if (nb == NULL)
    return FALSE;
  message = nb;
  message_len = n;
  return TRUE;
}

/* Return TRUE if the MESSAGES file exists (probe once). */

static bool messages_dir_ok(void) {
  char path[MAX_PATHNAME_LEN + 1];
  int fd;

  if (msg_dir_state != 0)
    return (msg_dir_state > 0);

  msg_dir_state = -1;
  if (sysseg == NULL)
    return FALSE;

  if (snprintf(path, sizeof(path), "%s%cMESSAGES", sysseg->sysdir, DS) >=
      (int)sizeof(path))
    return FALSE;

  fd = open(path, O_RDONLY);
  if (fd >= 0) {
    (void)close(fd);
    msg_dir_state = 1;
    return TRUE;
  }
  return FALSE;
}

static void format_not_found(char* id) {
  snprintf(fallback_msg, sizeof(fallback_msg), "[%s] Message not found", id);
}

static void format_no_file(int msg_no) {
  snprintf(fallback_msg, sizeof(fallback_msg),
           "[%d] Message file not found(%d %d).", msg_no, (int)dh_err,
           process.os_error);
}

static void process_message_escapes(char* text) {
  char* p;
  size_t len;
  size_t n;

  if (text == NULL || text[0] == '\0')
    return;

  len = strlen(text);
  if (len > 0 && text[len - 1] == '\n')
    text[--len] = '\0';

  p = text;
  n = len;
  while (n > 0) {
    char* q;

    q = memchr(p, '\n', n);
    if (q == NULL)
      break;
    *q = FIELD_MARK;
    n -= (size_t)(q + 1 - p);
    p = q + 1;
  }

  p = text;
  while ((p = strchr(p, '\\')) != NULL) {
    if (p[1] == '\0')
      break;
    switch (p[1]) {
      case 'n':
        *p = '\n';
        /* rev 0.9.1: newline display expects CR following LF */
        p[1] = '\r';
        break;
      case 't':
        *p = '\t';
        memmove(p + 1, p + 2, strlen(p + 2) + 1);
        break;
      default:
        break;
    }
    p++;
  }
}

/* ======================================================================
   Select a language                                                      */

bool load_language(char* language_prefix) {
  static bool loaded = FALSE;
  static char* default_months =
      "January,February,March,April,May,June,July,August,September,October,"
      "November,December";
  static char* default_days =
      "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday";
  char* p;
  int16_t i;

  if (language_prefix == NULL)
    language_prefix = "";

  if (strlen(language_prefix) > 3)
    return FALSE;

  snprintf(prefix, sizeof(prefix), "%s", language_prefix);

  if (loaded) {
    k_free(month_names[0]);
    k_free(day_names[0]);
  }

  p = sysmsg(1500);
  if ((p == NULL) || (*p == '[') || (strdcount(p, ',') != 12))
    p = default_months;

  month_names[0] = (char*)k_alloc(83, strlen(p) + 1);
  if (month_names[0] == NULL)
    return FALSE;
  strcpy(month_names[0], p);
  (void)strtok(month_names[0], ",");
  for (i = 1; i < 12; i++)
    month_names[i] = strtok(NULL, ",");

  p = sysmsg(1501);
  if ((p == NULL) || (*p == '[') || (strdcount(p, ',') != 7))
    p = default_days;

  day_names[0] = (char*)k_alloc(84, strlen(p) + 1);
  if (day_names[0] == NULL) {
    k_free(month_names[0]);
    month_names[0] = "January";
    month_names[1] = "February";
    month_names[2] = "March";
    month_names[3] = "April";
    month_names[4] = "May";
    month_names[5] = "June";
    month_names[6] = "July";
    month_names[7] = "August";
    month_names[8] = "September";
    month_names[9] = "October";
    month_names[10] = "November";
    month_names[11] = "December";
    return FALSE;
  }
  strcpy(day_names[0], p);
  (void)strtok(day_names[0], ",");
  for (i = 1; i < 7; i++)
    day_names[i] = strtok(NULL, ",");

  loaded = TRUE;
  return TRUE;
}

/* ======================================================================
   sysmsg()  -  Return message text                                       */

char* sysmsg(int msg_no) {
  char id[MSG_ID_SIZE];
  char path[MAX_PATHNAME_LEN + 1];
  int msg_rec;
  struct stat msg_stat;
  int msg_size;
  ssize_t got;

  msg_rec = -1;

  if (!grow_message_buf(128)) {
    snprintf(fallback_msg, sizeof(fallback_msg), "[%d] Message buffer error",
             msg_no);
    return fallback_msg;
  }

  if (!messages_dir_ok()) {
    format_no_file(msg_no);
    return fallback_msg;
  }

  if (prefix[0] != '\0') {
    snprintf(id, sizeof(id), "%s%d", prefix, msg_no);
    if (snprintf(path, sizeof(path), "%s%cMESSAGES%c%s", sysseg->sysdir, DS,
                 DS, id) >= (int)sizeof(path)) {
      snprintf(fallback_msg, sizeof(fallback_msg),
               "[%d] Message path too long", msg_no);
      return fallback_msg;
    }
    msg_rec = open(path, O_RDONLY);
  }

  if (msg_rec < 0) {
    snprintf(id, sizeof(id), "%d", msg_no);
    if (snprintf(path, sizeof(path), "%s%cMESSAGES%c%s", sysseg->sysdir, DS,
                 DS, id) >= (int)sizeof(path)) {
      snprintf(fallback_msg, sizeof(fallback_msg),
               "[%d] Message path too long", msg_no);
      return fallback_msg;
    }
    msg_rec = open(path, O_RDONLY);
  }

  if (msg_rec < 0) {
    format_not_found(id);
    return fallback_msg;
  }

  if (fstat(msg_rec, &msg_stat) != 0 || msg_stat.st_size < 0 ||
      msg_stat.st_size > MSG_MAX_RECORD) {
    (void)close(msg_rec);
    format_not_found(id);
    return fallback_msg;
  }

  msg_size = (int)msg_stat.st_size;
  if (!grow_message_buf(msg_size + 1)) {
    (void)close(msg_rec);
    snprintf(fallback_msg, sizeof(fallback_msg), "[%d] Message too large",
             msg_no);
    return fallback_msg;
  }

  got = read(msg_rec, message, (size_t)msg_size);
  (void)close(msg_rec);

  if (got != (ssize_t)msg_size) {
    format_not_found(id);
    return fallback_msg;
  }

  message[msg_size] = '\0';
  process_message_escapes(message);
  return message;
}

/* ======================================================================
   op_sysmsg()  -  Return message text to SDBasic program                 */

void op_sysmsg() {
  /* Stack:

      |================================|=============================|
      |            BEFORE              |           AFTER             |
      |================================|=============================|
  top |  Arguments (perhaps)           | Message text                |
      |--------------------------------|-----------------------------|
      |  Key                           |                             |
      |================================|=============================|

      Opcode is followed by single byte argument count
 */

  DESCRIPTOR* descr;
  int16_t arg_ct;
  int saved_process_status;
  int saved_os_error;
  char* msg;

  saved_process_status = process.status;
  saved_os_error = process.os_error;

  arg_ct = *(pc++);

  descr = e_stack - (1 + arg_ct);
  GetNum(descr);
  msg = sysmsg(descr->data.value);
  k_put_c_string(msg, descr);

  if ((strchr(msg, '%') != NULL) || arg_ct) {
    while (arg_ct++ < 4) {
      InitDescr(e_stack, STRING);
      (e_stack++)->data.str.saddr = NULL;
    }

    InitDescr(e_stack, INTEGER);
    (e_stack++)->data.value = saved_process_status;

    InitDescr(e_stack, INTEGER);
    (e_stack++)->data.value = saved_os_error;

    k_recurse(pcode_msgargs, 7);
  }
}

/* END-CODE */
