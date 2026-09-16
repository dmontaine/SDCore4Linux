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
 * 15 Sep 26 dm - read SD_CONFIG, not SCARLET_CONFIG, and bound the copy.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * The variable is SD_CONFIG (SD_CONFIG_ENV in sddefs.h, where the reasoning
 * is).  It was SCARLET_CONFIG here while sdclilib.c read SD_CONFIG, so
 * setting the one you would expect configured the server or the client but
 * never both.  SCARLET_CONFIG is not read any more.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

/* ====================================================================== */

bool GetConfigPath(char *inipath) { 

  char* p;

  /* Callers pass a buffer of MAX_PATHNAME_LEN + 1.  Nothing here may write
     more than that - the environment supplies the string, so it is not ours
     to trust.                                                              */

  p = getenv(SD_CONFIG_ENV);
  if ((p != NULL) && (*p != '\0')) {
    snprintf(inipath, MAX_PATHNAME_LEN + 1, "%s", p);
  } else {
    snprintf(inipath, MAX_PATHNAME_LEN + 1, "%s", SD_CONFIG_DEFAULT);
  }

  return TRUE;
}

/* END-CODE */
