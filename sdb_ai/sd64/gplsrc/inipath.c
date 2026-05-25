/* INIPATH.C
 * Get system paths
 * Copyright (c) 2004 Ladybridge Systems, All Rights Reserved
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
 * GetConfigPath()  -  Fill inipath with the configuration file pathname.
 *
 * Uses SD_CONFIG if set and non-empty, else "/etc/sd.conf".  Returns FALSE
 * if inipath is NULL or the path would exceed MAX_PATHNAME_LEN.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#define DEFAULT_CONFIG_PATH "/etc/sd.conf"

/* ====================================================================== */

bool GetConfigPath(char* inipath) {
  const char* src;
  const char* p;
  int n;

  if (inipath == NULL)
    return FALSE;

  p = getenv("SD_CONFIG");
  if (p != NULL && p[0] != '\0')
    src = p;
  else
    src = DEFAULT_CONFIG_PATH;

  n = snprintf(inipath, MAX_PATHNAME_LEN + 1, "%s", src);
  if (n < 0 || n > MAX_PATHNAME_LEN)
    return FALSE;

  return TRUE;
}

/* END-CODE */
