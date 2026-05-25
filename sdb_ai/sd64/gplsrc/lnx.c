/* LNX.C
 * Linux specific functions
 * Copyright (c) 2003 Ladybridge Systems, All Rights Reserved
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
 * Linux-specific helpers.  sdsendmail() pipes message text to the system
 * mail(1) command; attachments are not implemented on this platform.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#include <ctype.h>
#include <stdarg.h>

#define MAIL_CMD_SIZE 8192
#define MAIL_TEMPNAME_SIZE 32
#define MAX_MAIL_FIELD_LEN 4096

/* Addresses and recipient lists: printable, no shell metacharacters. */

static bool mail_field_safe(const char* s) {
  const unsigned char* p;

  if (s == NULL)
    return TRUE;

  if (strlen(s) > MAX_MAIL_FIELD_LEN)
    return FALSE;

  for (p = (const unsigned char*)s; *p != '\0'; p++) {
    if (*p < ' ' || *p == 0x7f)
      return FALSE;
    if (!isalnum(*p) && strchr("@.,-_+ ", (int)*p) == NULL)
      return FALSE;
  }
  return TRUE;
}

/* Subject lines: reject shell metacharacters (quoted via shell escaping). */

static bool mail_subject_safe(const char* s) {
  const unsigned char* p;

  if (s == NULL)
    return FALSE;

  if (strlen(s) > 255)
    return FALSE;

  for (p = (const unsigned char*)s; *p != '\0'; p++) {
    if (*p < ' ' || *p == 0x7f)
      return FALSE;
    switch (*p) {
      case ';':
      case '|':
      case '&':
      case '$':
      case '`':
      case '"':
      case '\\':
      case '<':
      case '>':
      case '!':
      case '*':
      case '?':
      case '[':
      case ']':
      case '{':
      case '}':
      case '(':
      case ')':
      case '\n':
      case '\r':
      case '\t':
        return FALSE;
      /* Single quotes are allowed; append_shell_quoted() escapes them. */
      default:
        break;
    }
  }
  return TRUE;
}

static bool append_shell_quoted(char** pp, char* end, const char* s) {
  char* p;
  const char* q;

  if (pp == NULL || *pp == NULL || end == NULL || s == NULL)
    return FALSE;

  p = *pp;
  if (p + 1 >= end)
    return FALSE;
  *(p++) = '\'';

  for (q = s; *q != '\0'; q++) {
    if (*q == '\'') {
      if (p + 4 >= end)
        return FALSE;
      memcpy(p, "'\\''", 4);
      p += 4;
    } else {
      if (p + 1 >= end)
        return FALSE;
      *(p++) = *q;
    }
  }

  if (p + 2 >= end)
    return FALSE;
  *(p++) = '\'';
  *p = '\0';
  *pp = p;
  return TRUE;
}

static bool cmd_append(char** pp, char* end, const char* fmt, ...) {
  va_list ap;
  int n;
  size_t rem;

  if (pp == NULL || *pp == NULL || end <= *pp)
    return FALSE;

  rem = (size_t)(end - *pp);
  va_start(ap, fmt);
  n = vsnprintf(*pp, rem, fmt, ap);
  va_end(ap);
  if (n < 0 || (size_t)n >= rem)
    return FALSE;
  *pp += n;
  return TRUE;
}

/* ======================================================================
   sdsendmail()  -  Send email                                            */

bool sdsendmail(char* sender,
                char* recipients,
                char* cc_recipients,
                char* bcc_recipients,
                char* subject,
                char* text,
                char* attachments) {
  bool status = FALSE;
  char tempname[MAIL_TEMPNAME_SIZE];
  char command[MAIL_CMD_SIZE];
  char* p;
  char* end;
  int tfu;
  int n;
  int st;
  const char* body;
  bool temp_created = FALSE;

  (void)attachments; /* Not supported on Linux */

  if (my_uptr == NULL || subject == NULL) {
    process.status = ER_NO_TEMP;
    goto exit_sendmail;
  }

  if (!mail_subject_safe(subject) || !mail_field_safe(recipients) ||
      !mail_field_safe(cc_recipients) || !mail_field_safe(bcc_recipients) ||
      !mail_field_safe(sender)) {
    process.status = ER_NO_TEMP;
    goto exit_sendmail;
  }

  if (snprintf(tempname, sizeof(tempname), ".sd_mail%u",
               (unsigned)my_uptr->uid) >= (int)sizeof(tempname)) {
    process.status = ER_NO_TEMP;
    process.os_error = errno;
    goto exit_sendmail;
  }

  tfu = open(tempname, O_RDWR | O_CREAT | O_TRUNC, default_access);
  if (tfu < 0) {
    process.status = ER_NO_TEMP;
    process.os_error = errno;
    goto exit_sendmail;
  }
  temp_created = TRUE;

  body = (text != NULL) ? text : null_string;
  n = (int)strlen(body);
  if (write(tfu, body, (size_t)n) != n) {
    process.status = ER_NO_TEMP;
    process.os_error = errno;
    close(tfu);
    remove(tempname);
    goto exit_sendmail;
  }

  if (close(tfu) != 0) {
    process.status = ER_NO_TEMP;
    process.os_error = errno;
    remove(tempname);
    goto exit_sendmail;
  }
  tfu = -1;

  p = command;
  end = command + MAIL_CMD_SIZE;

  if (!cmd_append(&p, end, "mail -s "))
    goto exit_sendmail_cmd;
  if (!append_shell_quoted(&p, end, subject))
    goto exit_sendmail_cmd;

  if (sender != NULL && sender[0] != '\0') {
    if (!cmd_append(&p, end, " -r "))
      goto exit_sendmail_cmd;
    if (!append_shell_quoted(&p, end, sender))
      goto exit_sendmail_cmd;
  }

  if (cc_recipients != NULL && cc_recipients[0] != '\0') {
    if (!cmd_append(&p, end, " -c "))
      goto exit_sendmail_cmd;
    if (!append_shell_quoted(&p, end, cc_recipients))
      goto exit_sendmail_cmd;
  }

  if (bcc_recipients != NULL && bcc_recipients[0] != '\0') {
    if (!cmd_append(&p, end, " -b "))
      goto exit_sendmail_cmd;
    if (!append_shell_quoted(&p, end, bcc_recipients))
      goto exit_sendmail_cmd;
  }

  if (recipients != NULL && recipients[0] != '\0') {
    if (!cmd_append(&p, end, " "))
      goto exit_sendmail_cmd;
    if (!append_shell_quoted(&p, end, recipients))
      goto exit_sendmail_cmd;
  }

  if (!cmd_append(&p, end, " <"))
    goto exit_sendmail_cmd;
  if (!append_shell_quoted(&p, end, tempname))
    goto exit_sendmail_cmd;

  st = system(command);
  if (st != 0) {
    process.status = ER_NO_TEMP;
    process.os_error = errno;
    remove(tempname);
    goto exit_sendmail;
  }

  remove(tempname);
  temp_created = FALSE;
  status = TRUE;
  goto exit_sendmail;

exit_sendmail_cmd:
  process.status = ER_NO_TEMP;
  if (temp_created)
    remove(tempname);

exit_sendmail:
  return status;
}

/* END-CODE */
