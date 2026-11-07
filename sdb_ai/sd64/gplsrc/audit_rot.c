/* AUDIT_ROT.C
 * Start a new audit file when the current one is large.
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
 * 07 Nov 26 dm  S.159 (Kimi review): a rotation whose new trail cannot be made with the old one's owner and mode is undone and
 *               returns -1, not 1 (the trail used to stay absent).
 * 24 Oct 26 dm  W.11 F4, option C2: moved out of k_error.c audit_rotate() so that the audit daemon (sdlnxd.c), which is now the trail's writer, rotates by size with the
 *               same code that "sd -start" uses.  The caller holds ERRLOG_SEM.  One change to the body: a rotation whose new name is already taken is refused, not
 *               done (rename() replaced the file there; the sandbox suite saw two rotations in one second leave one rotated file).
 * 11 Sep 26 dm  PORT_ADOPTION 13, the port's audit_rotate() (k_error.c).
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * audit_rotate_file()     Rename the audit file and start a new one if it has reached a size
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#include <time.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <linux/fs.h>

/* ======================================================================
   audit_rotate_file()  -  Start a new audit file if the current one has reached limit bytes

   Returns 1 when the file was rotated, 0 when there was nothing to do, -1 when it should have been and could not (the attribute would not lift, the rename failed, a rotated file of that second is already there, or the new trail could not be made
   with the old one's owner and mode - then the rename is undone).

   Called with ERRLOG_SEM held, by the kernel at "sd -start" (k_error.c audit_rotate(), root, no session running) and by the audit daemon as it writes (sdlnxd.c): only
   root can lift the append-only attribute a rename needs, and a rotation under an append is the other thing to avoid.  A machine whose daemon is not running rotates only
   at a start; with the daemon it rotates as it goes.

   THE NEW FILE CARRIES THE OLD ONE'S OWNER, MODE AND ATTRIBUTE - the Linux form of the port copying the ACL.  A plain rename would leave the next writer to create it, and
   a trail a session creates is one it can rewrite (and audit_message() does not create).  THE ROTATED FILE GETS ITS ATTRIBUTE BACK TOO, so an old trail is as hard to
   alter as the live one; pruning one is the site's decision and starts with "chattr -a".

   If the attribute is set and cannot be lifted, nothing is renamed - the trail stays whole and keeps growing.  On a filesystem without the attribute the rename still
   happens and nothing is set; the installer is what said so.                                                                                                            */

int audit_rotate_file(const char* path, long limit) {
  time_t timenow;
  struct tm* ltime;
  struct stat statbuf;
  struct stat existing;
  int fd;
  int newfd;
  int flags = 0;
  int newflags = 0;
  int result = 0;
  bool had_append = FALSE;
  char rotated[MAX_PATHNAME_LEN + 1];

  if ((path == NULL) || (*path == '\0'))
    return 0;

  if ((lstat(path, &statbuf) == 0) && S_ISREG(statbuf.st_mode) && (statbuf.st_size >= limit)) {
    timenow = time(NULL);
    ltime = localtime(&timenow);

    if (snprintf(rotated, sizeof(rotated), "%s.%04d%02d%02d-%02d%02d%02d", path,
                 ltime->tm_year + 1900, ltime->tm_mon + 1, ltime->tm_mday,
                 ltime->tm_hour, ltime->tm_min, ltime->tm_sec) <
        (int)sizeof(rotated)) {
      /* The name has a second's resolution, and rename() replaces what is there.  Two rotations in one second (a start straight after the daemon rotated) would destroy the
         first rotated file, so a name that is taken refuses the rotation: the trail stays whole and the caller tries again later. */
      if ((lstat(rotated, &existing) == 0) || (errno != ENOENT))
        return -1;
      fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
      if (fd >= 0) {
        if ((ioctl(fd, FS_IOC_GETFLAGS, &flags) == 0) && (flags & FS_APPEND_FL)) {
          had_append = TRUE;
          flags &= ~FS_APPEND_FL;
          if (ioctl(fd, FS_IOC_SETFLAGS, &flags) != 0) {
            close(fd); /* cannot lift it: leave the trail whole */
            return -1;
          }
        }

        if (rename(path, rotated) == 0) {
          /* 7 Nov 26 S.159 (Kimi review, finding 4): result was 1 as soon as the
             rename worked, so a new trail that could not be made (or not given
             the old one's owner and mode) was reported as a rotation; every
             later append opens without O_CREAT, and the size test no longer
             matched a missing file, so the trail stayed absent.  Success now
             needs the new file made with the owner and mode; otherwise the old
             trail is renamed back over it, and the caller is told -1
             (the daemon tries again in a minute).  The append attribute is
             still best effort, as it is on the rotated file.                  */
          newfd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
                       statbuf.st_mode & 07777);
          if ((newfd >= 0) && (fchown(newfd, statbuf.st_uid, statbuf.st_gid) == 0) &&
              (fchmod(newfd, statbuf.st_mode & 07777) == 0)) {
            result = 1;
            if (had_append && (ioctl(newfd, FS_IOC_GETFLAGS, &newflags) == 0)) {
              newflags |= FS_APPEND_FL;
              (void)ioctl(newfd, FS_IOC_SETFLAGS, &newflags);
            }
          } else {
            result = -1;
            /* The old trail back in its place.  When the open worked, the rename replaces the empty file it made in
               one step (nothing is unlinked: test-auditwriter-units.py R9); when it did not, only into an empty name. */
            if ((newfd >= 0) || ((lstat(path, &existing) != 0) && (errno == ENOENT)))
              (void)rename(rotated, path);
          }
          if (newfd >= 0)
            close(newfd);
        } else {
          result = -1;
        }

        /* Back on: the rotated file if the rename worked, the unrenamed trail
           if it did not - fd is the same inode either way.                  */
        if (had_append) {
          flags |= FS_APPEND_FL;
          (void)ioctl(fd, FS_IOC_SETFLAGS, &flags);
        }
        close(fd);
      }
    }
  }

  return result;
}
