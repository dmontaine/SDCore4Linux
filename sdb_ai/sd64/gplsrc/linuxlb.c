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
 * 10 Sep 26 dm  Parity audit: sdrealpath() keeps resolving . and .. after a
 *               component that does not exist (UPSTREAM_FIXES 10).
 * 31 Dec 23 SD launch - prior history suppressed
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#include <pwd.h>
#include <time.h>

#ifndef __APPLE__
#include <crypt.h>
#endif

/* ======================================================================
   filelength64()  -  Return file size in bytes                           */

int64 filelength64(fd) int fd;
{
  struct stat statbuf;

  fstat(fd, &statbuf);
  return statbuf.st_size;
}

/* ======================================================================
   IsAdmin() is GONE - 09 Sep 26 dm, PRE_RELEASE 18 commit 2.

   It was "return (getuid() == 0)", and PRE_RELEASE 18 listed it as one of the
   two tests to replace.  Entry 19 had already removed its only call site (the
   "|| IsAdmin()" in K_ADMINISTRATOR), so by 09 Sep 26 it was dead: the whole
   tree held one definition and one declaration and no caller.

   IT IS DELETED RATHER THAN LEFT because it answers the wrong question and
   reads as though it answers the right one.  "Is this process root" is not
   this system's definition of an administrator - that is sdadmin membership
   AND a registered ADMINISTRATOR tier, decided in CPROC's grant.administrator
   and read through kernel(K$ADMINISTRATOR,-1).  The port's IsAdmin() asks
   getgrouplist(), which is a third question again; do not copy it in.        */

/* ======================================================================
   itoa()  -  Convert integer to string                                   */

char* itoa(value, string, radix) int value;
char* string;
int radix; /* Ignored */
{
  sprintf(string, "%d", value);
  return string;
}

/* ======================================================================
   Ltoa()  -  Convert long integer to string                              */

char* Ltoa(value, string, radix) int32_t value;
char* string;
int radix; /* Ignored */
{
  sprintf(string, "%d", value);
  return string;
}

/* ======================================================================
   GetUserName()  -  Return user name for logged in user.                 */

bool GetUserName(name, bytes) char* name;
u_int32_t* bytes; /* Buffer size - updated to actual size on exit */
{
  char* p;
  int n = 0;
  struct passwd* pw;

  pw = getpwuid(getuid());
  p = (pw == NULL) ? NULL : (pw->pw_name);

  if (p != NULL) {
    n = strlen(p);
    /* Modified by Composer AI - 2026/06/10.
       The truncation test was inverted: a name shorter than the buffer
       was padded by copying bytes from beyond the end of the password
       entry (returning a wrong length), and a name longer than the
       buffer was copied in full, overflowing it. Truncate only when the
       name does not fit. */
    /* if (*bytes >= n)
      n = *bytes - 1; */
    if (n >= (int)*bytes)
      n = *bytes - 1;
    /* -------------------- */
    memcpy(name, p, n);
  }
  *(name + n) = '\0';
  *bytes = n;

  return TRUE;
}

/* ======================================================================
   sdrealpath()  -  Emulation of realpath() with extension to handle
                    pathnames that do not exist.                          */

char* sdrealpath(char* inpath,  /* Supplied path */
                 char* outpath) /* Full path */
{
  char* tgt;
  char* p;
  char* q;
  struct stat st;
  int n;
  int link_depth = 0;
  char link_buf[PATH_MAX + 1];

  switch (inpath[0]) {
    case '/': /* Absolute pathname */
      outpath[0] = '/';
      tgt = outpath + 1;
      break;

    case '\0': /* Null pathname - error */
      return NULL;

    default: /* Relative pathname - get current directory */
      getcwd(outpath, PATH_MAX);
      tgt = strchr(outpath, '\0');
      break;
  }

  p = inpath; /* Source pointer */
  while (*p != '\0') {
    /* Skip over multiple delimiters */
    while (*p == '/')
      p++;

    /* Find next delimiter or end of inpath */
    q = p;
    while (*q != '\0' && *q != '/')
      q++;
    n = q - p;

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
      if (*(tgt - 1) != '/')
        *(tgt++) = '/';

      /* Append this name unless it would overrun the buffer */

      if (tgt + n - outpath >= PATH_MAX)
        return NULL;

      memcpy(tgt, p, n);
      p = q + 1;
      tgt += n;
      *tgt = '\0';

      /* Check the path exists and whether it is a symlink */

      if (lstat(outpath, &st) < 0) {
        if (errno != ENOENT)
          return NULL;

        /* 10 Sep 26 dm - Parity audit: KEEP RESOLVING, the Windows port's
           proposal (UPSTREAM_FIXES 10).  This glued the rest of the input on
           the end UNPROCESSED and returned, so any "." or ".." after the first
           component that does not exist survived:
             /data/live/nofile/../../../sdsys  came back unchanged,
           while the same path with every component present resolved.  Two
           spellings of one file compared unequal, and a "resolve, then check
           it is under the root" test was defeated by one made-up name.

           The component does not exist, so there is no symlink to follow;
           carry on with the next one.  p IS RESET TO q FIRST, and that is the
           part the proposal's "move the advance" means: p was set to q + 1
           above, which for the LAST component is one past the terminator, and
           continue would skip the "p = q" at the bottom of the loop.  A caller
           creating a file still gets a path back - now a resolved one. */
        p = q;
        continue;
      }

      if (S_ISLNK(st.st_mode)) {
        if (++link_depth > 20)
          return NULL; /* Symlinks too deep */

        n = readlink(outpath, link_buf, PATH_MAX);
        if (n < 0)
          return NULL;

        link_buf[n] = '\0';

        if (link_buf[0] == '/') /* It's an absolute symlink */
        {
          strcpy(outpath, link_buf);
          tgt = outpath + n;
        } else {
          /* Back up one level unless already at root directory */
          if (tgt > outpath + 1)
            while (*((--tgt) - 1) != '/') {
            }

          if (tgt + n - outpath >= PATH_MAX)
            return NULL;

          strcpy(tgt, link_buf);
          tgt += n;
        }
      }
    }

    p = q;
  }

  /* Remove trailing / if present unless root directory reference */

  if (tgt > outpath + 1 && *(tgt - 1) == '/')
    tgt--;
  *tgt = '\0';

  return outpath;
}

/* ======================================================================
   Sleep()  -  Sleep for period in milliseconds                           */

void Sleep(n) int32_t n;
{
  struct timespec period;
  struct timespec remaining;

  period.tv_sec = n / 1000;
  period.tv_nsec = (n % 1000) * 1000000;
  nanosleep(&period, &remaining);
}

/* END-CODE */
