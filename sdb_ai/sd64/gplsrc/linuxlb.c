/* LINUXLB.C
 * Windows library substitutes for Linux
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
 * 31 Dec 23 SD launch - prior history suppressed
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 * Linux portability shims: file length, username, path canonicalisation,
 * sleep.  Callers of itoa()/Ltoa() must supply a buffer of at least 24 bytes.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#include <limits.h>
#include <pwd.h>
#include <time.h>

#ifndef __APPLE__
#include <crypt.h>
#endif

#define ITOA_BUF_MIN 24

/* ======================================================================
   filelength64()  -  Return file size in bytes                           */

int64 filelength64(int fd) {
  struct stat statbuf;

  if (fstat(fd, &statbuf) != 0)
    return (int64)-1;
  return statbuf.st_size;
}

/* ======================================================================
   IsAdmin()  -  Is this user an administrator at the o/s level?          */

bool IsAdmin(void) {
  return (getuid() == 0);
}

/* ======================================================================
   itoa()  -  Convert integer to string                                   */

char* itoa(int value, char* string, int radix) {
  (void)radix;
  snprintf(string, ITOA_BUF_MIN, "%d", value);
  return string;
}

/* ======================================================================
   Ltoa()  -  Convert long integer to string                              */

char* Ltoa(int32_t value, char* string, int radix) {
  (void)radix;
  snprintf(string, ITOA_BUF_MIN, "%d", value);
  return string;
}

/* ======================================================================
   GetUserName()  -  Return user name for logged in user.                 */

bool GetUserName(char* name, u_int32_t* bytes) {
  struct passwd* pw;
  size_t len;
  size_t buf_sz;

  if (name == NULL || bytes == NULL || *bytes == 0)
    return FALSE;

  pw = getpwuid(getuid());
  if (pw == NULL || pw->pw_name == NULL) {
    name[0] = '\0';
    *bytes = 0;
    return FALSE;
  }

  len = strlen(pw->pw_name);
  buf_sz = (size_t)*bytes;
  if (len >= buf_sz)
    len = buf_sz - 1;

  memcpy(name, pw->pw_name, len);
  name[len] = '\0';
  *bytes = (u_int32_t)len;
  return TRUE;
}

/* ======================================================================
   sdrealpath()  -  Emulation of realpath() with extension to handle
                    pathnames that do not exist.                          */

char* sdrealpath(char* inpath,  /* Supplied path */
                 char* outpath) /* Full path (PATH_MAX bytes) */
{
  char* tgt;
  char* p;
  char* q;
  struct stat st;
  int n;
  int link_depth = 0;
  char link_buf[PATH_MAX + 1];
  size_t remain;

  if (inpath == NULL || outpath == NULL)
    return NULL;

  switch (inpath[0]) {
    case '/': /* Absolute pathname */
      outpath[0] = '/';
      tgt = outpath + 1;
      break;

    case '\0': /* Null pathname - error */
      return NULL;

    default: /* Relative pathname - get current directory */
      if (getcwd(outpath, PATH_MAX) == NULL)
        return NULL;
      tgt = strchr(outpath, '\0');
      if (tgt == NULL)
        return NULL;
      break;
  }

  p = inpath; /* Source pointer */
  while (*p != '\0') {
    /* Skip over multiple delimiters */
    while (*p == '/')
      p++;
    if (*p == '\0')
      break;

    /* Find next delimiter or end of inpath */
    q = p;
    while (*q != '\0' && *q != '/')
      q++;
    n = (int)(q - p);
    if (n == 0)
      break;

    if ((*p == '.') && (n == 1)) /* . reference */
    {
      /* Nothing to do */
    } else if ((*p == '.') && (*(p + 1) == '.') && (n == 2)) /* .. reference */
    {
      /* Revert one level unless already at root */
      if (tgt > outpath + 1) {
        while (*((--tgt) - 1) != '/') {
        }
      }
    } else /* Name reference */
    {
      if (tgt > outpath && *(tgt - 1) != '/')
        *(tgt++) = '/';

      /* Append this name unless it would overrun the buffer */

      if ((size_t)(tgt + n - outpath) >= PATH_MAX)
        return NULL;

      memcpy(tgt, p, (size_t)n);
      tgt += n;
      *tgt = '\0';
      p = q;

      /* Check the path exists and whether it is a symlink */

      if (lstat(outpath, &st) < 0) {
        if (errno != ENOENT)
          return NULL;

        /* Glue remaining components for paths that do not exist yet */

        if (*p != '\0') {
          remain = strlen(p);
          if ((size_t)(tgt - outpath) + 1 + remain >= PATH_MAX)
            return NULL;

          *(tgt++) = '/';
          memcpy(tgt, p, remain + 1);
        }
        return outpath;
      }

      if (S_ISLNK(st.st_mode)) {
        if (++link_depth > 20)
          return NULL; /* Symlinks too deep */

        n = (int)readlink(outpath, link_buf, PATH_MAX);
        if (n < 0 || n >= PATH_MAX)
          return NULL;

        link_buf[n] = '\0';

        if (link_buf[0] == '/') /* It's an absolute symlink */
        {
          snprintf(outpath, PATH_MAX + 1, "%s", link_buf);
          tgt = strchr(outpath, '\0');
          if (tgt == NULL)
            return NULL;
        } else {
          /* Back up one level unless already at root directory */
          if (tgt > outpath + 1) {
            while (*((--tgt) - 1) != '/') {
            }
          }

          if ((size_t)(tgt + n - outpath) >= PATH_MAX)
            return NULL;

          memcpy(tgt, link_buf, (size_t)n);
          tgt += n;
          *tgt = '\0';
        }
      }
    }

    p = q;
    if (*p == '/')
      p++;
  }

  /* Remove trailing / if present unless root directory reference */

  if (tgt > outpath + 1 && *(tgt - 1) == '/')
    tgt--;
  *tgt = '\0';

  return outpath;
}

/* ======================================================================
   Sleep()  -  Sleep for period in milliseconds                           */

void Sleep(int32_t n) {
  struct timespec period;
  struct timespec remaining;

  if (n < 0)
    n = 0;

  period.tv_sec = n / 1000;
  period.tv_nsec = (long)((n % 1000) * 1000000);
  nanosleep(&period, &remaining);
}

/* END-CODE */
