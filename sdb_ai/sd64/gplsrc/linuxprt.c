/* LINUXPRT.C
 * Printer i/o (Linux)
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
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * Linux printers work by diverting the output to the prt subdirectory of
 * the Q_M_SYS account and then feeding this file to the Linux spooler (lp).
 * Spool command lines are built with bounded buffers and shell-safe quoting.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "tio.h"
#include "config.h"

#include <ctype.h>
#include <stdarg.h>

#define SPOOL_CMD_SIZE 4096
#define MAX_PRINTER_NAME_LEN 127
#define MAX_SPOOL_TEXT_LEN 512

void to_file(PRINT_UNIT* pu, char* str, int16_t bytes);

/* Return FALSE if s contains shell metacharacters or control characters. */

static bool spool_text_safe(const char* s) {
  const unsigned char* p;

  if (s == NULL)
    return TRUE;

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
      case '\'':
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
      default:
        break;
    }
  }
  return TRUE;
}

/* Append a shell single-quoted argument; embedded quotes use '\''. */

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
   to_printer  -  Send text to printer                                    */

void to_printer(PRINT_UNIT* pu, char* str, int16_t bytes) {
  to_file(pu, str, bytes);
}

/* ======================================================================
   validate_printer()  -  Check printer name is valid                     */

bool validate_printer(char* printer_name) {
  const unsigned char* p;
  size_t len;

  if (printer_name == NULL)
    return TRUE; /* Default destination */

  len = strlen(printer_name);
  if (len == 0 || len > MAX_PRINTER_NAME_LEN)
    return FALSE;

  for (p = (const unsigned char*)printer_name; *p != '\0'; p++) {
    if (!isalnum(*p) && *p != '_' && *p != '-' && *p != '.' && *p != '@')
      return FALSE;
  }
  return TRUE;
}

/* ======================================================================
   end_printer()  -  End access to printer                                */

void end_printer(PRINT_UNIT* pu) {
  if (pu == NULL)
    return;

  if (!(pu->flags & PU_KEEP_OPEN))
    end_file(pu);
}

/* ======================================================================
   spool_print_job()                                                      */

void spool_print_job(PRINT_UNIT* pu) {
  char cmd[SPOOL_CMD_SIZE];
  char* p;
  char* end;
  const char* spool_cmd;
  int st;

  if (pu == NULL || pu->file.pathname == NULL || pu->file.pathname[0] == '\0')
    return;

  p = cmd;
  end = cmd + SPOOL_CMD_SIZE;

  if (pu->spooler != NULL && pu->spooler[0] != '\0') {
    if (!spool_text_safe(pu->spooler) ||
        strlen(pu->spooler) > MAX_PATHNAME_LEN)
      return;
    spool_cmd = pu->spooler;
  } else if (pcfg.spooler[0] != '\0') {
    if (!spool_text_safe(pcfg.spooler))
      return;
    spool_cmd = pcfg.spooler;
  } else {
    spool_cmd = "lp";
  }

  if (!cmd_append(&p, end, "%s ", spool_cmd))
    return;

  if (pu->copies > 1) {
    if (!cmd_append(&p, end, "-n %d ", (int)pu->copies))
      return;
  }

  if (pu->printer_name != NULL && pu->printer_name[0] != '\0') {
    if (!validate_printer(pu->printer_name))
      return;
    if (!cmd_append(&p, end, "-d "))
      return;
    if (!append_shell_quoted(&p, end, pu->printer_name))
      return;
    if (!cmd_append(&p, end, " "))
      return;
  }

  if (pu->banner != NULL && pu->banner[0] != '\0') {
    if (!spool_text_safe(pu->banner) || strlen(pu->banner) > MAX_SPOOL_TEXT_LEN)
      return;
    if (!cmd_append(&p, end, "-t "))
      return;
    if (!append_shell_quoted(&p, end, pu->banner))
      return;
    if (!cmd_append(&p, end, " "))
      return;
  }

  if (pu->options != NULL && pu->options[0] != '\0') {
    if (!spool_text_safe(pu->options) ||
        strlen(pu->options) > MAX_SPOOL_TEXT_LEN)
      return;
    if (!cmd_append(&p, end, "-o "))
      return;
    if (!append_shell_quoted(&p, end, pu->options))
      return;
    if (!cmd_append(&p, end, " "))
      return;
  }

  if (pu->flags & PU_LAND) {
    if (!cmd_append(&p, end, "-o landscape "))
      return;
  }

  if (!cmd_append(&p, end, " "))
    return;
  if (!append_shell_quoted(&p, end, pu->file.pathname))
    return;
  if (!cmd_append(&p, end, " > /dev/null"))
    return;

  st = system(cmd);
  (void)st; /* Spool failure is non-fatal; job file may still exist */
}

/* END-CODE */
