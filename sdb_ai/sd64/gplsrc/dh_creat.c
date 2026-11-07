/* DH_CREAT.C
 * Create file
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
 * 07 Nov 26 dm  S.159: acct_group_modes() calls fullpath_n() with its PATH_MAX buffer (fullpath() now stops at 256 bytes).
 * 02 Nov 26 dm  S.96 M6: the master-file copies (S.67) are retired; the journal note of a new VOC or dictionary goes with masters.c, and the group
 *               write that masters_fix_modes gave a new VOC or dictionary is KEPT, moved here as acct_group_modes() (tool.entries needs it).
 * 19 Oct 26 dm  S.67 stage 2: and calls masters_fix_modes() (a new VOC or dictionary is given its group's write bit where the account's directory has it).
 * 19 Oct 26 dm  S.67 stage 1: a created VOC or dictionary calls masters_note_name() (journalled for the master files).
 * rev 0.9.0 Jan 25 mab change dyn file prefix to %
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
#include "dh_int.h"

#include <ctype.h>
#include <dirent.h>
#include <fcntl.h>
#include <grp.h>
#include <limits.h>
#include <pwd.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <unistd.h>

Private void acct_group_modes(const char *path);

/* ====================================================================== */

bool dh_create_file(char path[],
                    int16_t group_size,  /* -ve sets default */
                    int32_t min_modulus,  /* -ve sets default */
                    int32_t big_rec_size, /* -ve sets default */
                    int16_t merge_load,  /* -ve sets default */
                    int16_t split_load,  /* -ve sets default */
                    u_int32_t flags,
                    int16_t version) /* -ve sets default */
{
  bool status = FALSE;
  char primary_subfile[MAX_PATHNAME_LEN + 1];
  char overflow_subfile[MAX_PATHNAME_LEN + 1];
  bool primary_subfile_created = FALSE;
  bool overflow_subfile_created = FALSE;
  OSFILE fu = INVALID_FILE_HANDLE;
  struct DH_HEADER header;
  int header_bytes;
  int group_size_bytes;
  int32_t group;
  double file_size;

  dh_err = 0;
  process.os_error = 0;

  /* Validate arguments */

  if (group_size < 0) {
    group_size = DEFAULT_GROUP_SIZE;
  } else if ((group_size < 1) || (group_size > MAX_GROUP_SIZE)) {
    dh_err = DHE_ILLEGAL_GROUP_SIZE;
    goto exit_dh_create_file;
  }
  group_size_bytes = group_size * DH_GROUP_MULTIPLIER;

  if (min_modulus < 1) {
    min_modulus = DEFAULT_MIN_MODULUS;
  } else if (min_modulus < 1) {
    dh_err = DHE_ILLEGAL_MIN_MODULUS;
    goto exit_dh_create_file;
  }

  if (big_rec_size < 0) {
    big_rec_size = (int32_t)((group_size_bytes)*0.8);
  } else if (big_rec_size > group_size_bytes - BLOCK_HEADER_SIZE) {
    big_rec_size = group_size_bytes - BLOCK_HEADER_SIZE;
  }

  if (merge_load < 0) {
    merge_load = DEFAULT_MERGE_LOAD;
  } else if (merge_load > 99) {
    dh_err = DHE_ILLEGAL_MERGE_LOAD;
    goto exit_dh_create_file;
  }

  if (split_load < 0) {
    split_load = DEFAULT_SPLIT_LOAD;
  } else if (split_load <= merge_load) {
    dh_err = DHE_ILLEGAL_SPLIT_LOAD;
    goto exit_dh_create_file;
  }

  /* !!FILE_VERSION!! */
  if (version < 0) {
    version = DH_VERSION;
  } else if (version > DH_VERSION) {
    dh_err = DHE_VERSION;
    goto exit_dh_create_file;
  }

  header_bytes = DHHeaderSize(version, group_size_bytes);

  if (version < 2) {
    /* Check if file exceeds 2Gb */

    file_size = (((double)group_size_bytes) * min_modulus) + header_bytes;
    if (file_size > (u_int32_t)0x80000000L) {
      dh_err = DHE_SIZE;
      goto exit_dh_create_file;
    }
  }

  /* Check if directory to hold subfiles exists */

  if (access(path, 0) == 0) {
    dh_err = DHE_FILE_EXISTS;
    goto exit_dh_create_file;
  }

  /* Create directory */

  if (!make_path(path)) {
    dh_err = DHE_CREATE_DIR_ERR;
    process.os_error = OSError;
    goto exit_dh_create_file;
  }

  /* Create primary subfile */
/* rev 0.9.0 */
  sprintf(primary_subfile, "%s%c%%0", path, DS);
  fu = dio_open(primary_subfile, DIO_NEW);

  if (!ValidFileHandle(fu)) {
    dh_err = DHE_CREATE0_ERR;
    process.os_error = OSError;
    goto exit_dh_create_file;
  }

  primary_subfile_created = TRUE;

  /* Write primary subfile header */

  memset((char*)&header, 0, sizeof(header));
  header.magic = DH_PRIMARY;
  header.file_version = (u_char)version;
  header.group_size = group_size_bytes;
  header.flags = (u_int16_t)(flags & DHF_CREATE);
  header.params.modulus = min_modulus;
  header.params.min_modulus = min_modulus;
  header.params.big_rec_size = big_rec_size;
  header.params.split_load = split_load;
  header.params.merge_load = merge_load;
  header.params.load_bytes = 0;
  header.params.extended_load_bytes = 0;
  header.params.free_chain = 0;
  header.creation_timestamp = sdtime();
  header.record_count = 1; /* Actually zero, see dh_fmt.h */

  /* Calculate mod_value as next power of two >= min_modulus */

  for (header.params.mod_value = 1; header.params.mod_value < min_modulus;
       header.params.mod_value <<= 1) {
  }

  memset(dh_buffer, 0, header_bytes);
  memcpy(dh_buffer, (char*)(&header), sizeof(header));
  if (Write(fu, dh_buffer, header_bytes) < 0) {
    dh_err = DHE_PSFH_WRITE_ERROR;
    process.os_error = OSError;
    goto exit_dh_create_file;
  }

  /* Initialise data groups */

  memset(dh_buffer, 0, group_size_bytes);
  ((DH_BLOCK*)(dh_buffer))->used_bytes = BLOCK_HEADER_SIZE;
  ((DH_BLOCK*)(dh_buffer))->block_type = DHT_DATA;

  for (group = 1; group <= min_modulus; group++) {
    if (Write(fu, dh_buffer, group_size_bytes) < 0) {
      dh_err = DHE_INIT_DATA_ERROR;
      process.os_error = OSError;
      goto exit_dh_create_file;
    }
  }

  CloseFile(fu);
  fu = INVALID_FILE_HANDLE;

  /* Create overflow subfile */
/* rev 0.9.0 */
  sprintf(overflow_subfile, "%s%c%%1", path, DS);
  fu = dio_open(overflow_subfile, DIO_NEW);

  if (!ValidFileHandle(fu)) {
    dh_err = DHE_CREATE1_ERR;
    process.os_error = OSError;
    goto exit_dh_create_file;
  }

  /* Write overflow subfile header */

  memset((char*)(&header), 0, sizeof(header));
  header.magic = DH_OVERFLOW;
  header.group_size = group_size_bytes;

  memset(dh_buffer, 0, header_bytes);
  memcpy(dh_buffer, (char*)(&header), sizeof(header));

  if (Write(fu, dh_buffer, header_bytes) < 0) {
    dh_err = DHE_OSFH_WRITE_ERROR;
    process.os_error = OSError;
    goto exit_dh_create_file;
  }

  CloseFile(fu);
  fu = INVALID_FILE_HANDLE;

  status = TRUE;

  /* 19 Oct 26 S.67 stage 2, kept by S.96 M6 (2 Nov 26): the group of the account may write a new VOC or dictionary, where the account's own directory
     lets that group write (whatever the UMASK of this session): SDSYS, a member of the group, edits the account's VOC and dictionaries in place
     (tool.entries).  Never an error. */
  acct_group_modes(path);

exit_dh_create_file:
  if (status == FALSE) {
    if (ValidFileHandle(fu))
      CloseFile(fu);

    if (primary_subfile_created)
      remove(primary_subfile);

    if (overflow_subfile_created)
      remove(overflow_subfile);
  }

  return status;
}

/* ======================================================================
   THE MODES OF A NEW VOC OR DICTIONARY (S.67 stage 2, masters_fix_modes; moved here unchanged in what it does by S.96 M6, 2 Nov 26, when masters.c
   was retired: tool.entries writes into an account's own VOC and dictionaries as SDSYS, a member of the account's group, and needs what this gives).

   A VOC or a dictionary that has just been made is given group write - the directory g+rwx and setgid, %0 and %1 g+rw - where the account's directory
   has it, so that SDSYS (a member of the group) can write into it whatever the UMASK of the session that made it.  Only the GROUP bits are added,
   nothing is taken away and the other bits are not touched.  The rule is the account directory's own: if its group may write there, the group may
   write the VOC and the dictionaries, which it could already delete and make again; if the group may not (a directory of 755), nothing is added.
   Done on descriptors opened with O_NOFOLLOW and fchmod, so a link put in the place of the new directory by somebody else cannot aim the chmod at
   another file; only what this process made (owner = the effective user) and what has the account directory's group is changed.  And only where
   the sdsys user is in the account directory's group (F6, C2).  A refusal changes nothing and is not an error.  The account of the path is the
   registered account whose directory is the nearest prefix of it (the register, <sysdir>/accounts/<name>, line 1 the path), read at each call:
   a VOC or a dictionary is made seldom.                                                                                                       */

#define ACCT_SDSYS_USER "sdsys"

/* is the sdsys user in the group GID - its own primary group, or a name in the group's member list?  TRUE when there is no sdsys user on the machine
   (a sandbox on a machine with no install) */
Private bool acct_sdsys_in_group(gid_t gid) {
  struct passwd *pw = getpwnam(ACCT_SDSYS_USER);
  struct group *gr;
  char **m;

  if (pw == NULL)
    return TRUE;
  if (pw->pw_gid == gid)
    return TRUE;
  if ((gr = getgrgid(gid)) == NULL)
    return FALSE;
  for (m = gr->gr_mem; (m != NULL) && (*m != NULL); m++) {
    if (strcmp(*m, ACCT_SDSYS_USER) == 0)
      return TRUE;
  }
  return FALSE;
}

Private bool acct_valid_name(const char *n) {
  size_t i, len = strlen(n);

  if ((len == 0) || (len > MAX_ACCOUNT_NAME_LEN))
    return FALSE;
  for (i = 0; i < len; i++) {
    unsigned char c = (unsigned char)n[i];

    if (!(((c >= 'a') && (c <= 'z')) || ((c >= 'A') && (c <= 'Z')) || ((c >= '0') && (c <= '9')) || (c == '.') || (c == '_') || (c == '-')))
      return FALSE;
  }
  return TRUE;
}

/* the directory (as the OS resolves it) of the registered account that holds CANON, the nearest one, into ROOT; REL is set to the part of CANON
   below it.  FALSE when no registered account holds it. */
Private bool acct_root_for_path(const char *canon, char *root, size_t rootsz, const char **rel) {
  char regdir[MAX_PATHNAME_LEN + 1];
  char recpath[MAX_PATHNAME_LEN * 2 + 2];
  char body[4096];
  char real[PATH_MAX + 1];
  DIR *d;
  struct dirent *ent;
  FILE *fp;
  size_t got, n, best = 0;
  char *p;

  if ((sysseg == NULL) || (snprintf(regdir, sizeof(regdir), "%s%c%s", sd_sysdir(), DS, "accounts") >= (int)sizeof(regdir)))
    return FALSE;
  if ((d = opendir(regdir)) == NULL)
    return FALSE;
  while ((ent = readdir(d)) != NULL) {
    if ((ent->d_name[0] == '.') || (ent->d_name[0] == '%') || (strchr(ent->d_name, '/') != NULL) || !acct_valid_name(ent->d_name))
      continue;
    if (snprintf(recpath, sizeof(recpath), "%s%c%s", regdir, DS, ent->d_name) >= (int)sizeof(recpath))
      continue;
    if ((fp = fopen(recpath, "r")) == NULL)
      continue;
    got = fread(body, 1, sizeof(body) - 1, fp);
    fclose(fp);
    body[got] = '\0';
    if ((p = strchr(body, '\n')) != NULL)
      *p = '\0';
    n = strlen(body);
    while ((n > 0) && ((body[n - 1] == '\r') || (body[n - 1] == ' ')))
      body[--n] = '\0';
    if ((body[0] != '/') || (n > PATH_MAX) || (realpath(body, real) == NULL))
      continue;
    n = strlen(real);
    while ((n > 1) && (real[n - 1] == '/'))
      real[--n] = '\0';
    if ((n <= 1) || (n > MAX_PATHNAME_LEN) || (n >= rootsz) || (n <= best))
      continue;
    if ((strncmp(canon, real, n) == 0) && ((canon[n] == '/') || (canon[n] == '\0'))) {
      memcpy(root, real, n + 1);
      best = n;
    }
  }
  closedir(d);
  if (best == 0)
    return FALSE;
  *rel = canon + best + ((canon[best] == '/') ? 1 : 0);
  return TRUE;
}

Private void acct_group_modes(const char *path) {
  char full[PATH_MAX + 1];
  char root[MAX_PATHNAME_LEN + 1];
  const char *rel, *base;
  struct stat ra, ds, fs;
  size_t n;
  int dfd, ffd, i;
  static const char *subs[2] = {"%0", "%1"};

  if ((path == NULL) || ((n = strlen(path)) < 3) || (n > MAX_PATHNAME_LEN))
    return;
  if (!(((n > 4) && (strcasecmp(path + n - 4, ".dic") == 0)) || (strcasecmp(path + n - 3, "voc") == 0)))
    return;
  if (!fullpath_n(full, (char *)path, sizeof(full)) || !acct_root_for_path(full, root, sizeof(root), &rel))
    return;
  base = strrchr(rel, '/');
  base = (base == NULL) ? rel : base + 1;
  n = strlen(base);
  if (!((strcmp(rel, "voc") == 0) || ((n > 4) && (strcasecmp(base + n - 4, ".dic") == 0))))
    return;
  if ((stat(root, &ra) != 0) || !(ra.st_mode & S_IWGRP))
    return;
  if (!acct_sdsys_in_group(ra.st_gid)) /* F6 (C2): group write is forced only where the sdsys user is in the group */
    return;
  if ((dfd = open(full, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)) < 0)
    return;
  if ((fstat(dfd, &ds) != 0) || !S_ISDIR(ds.st_mode) || (ds.st_uid != geteuid()) || (ds.st_gid != ra.st_gid)) {
    close(dfd);
    return;
  }
  (void)fchmod(dfd, (mode_t)((ds.st_mode & 07777) | S_IRWXG | S_ISGID));
  for (i = 0; i < 2; i++) {
    if ((ffd = openat(dfd, subs[i], O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)) < 0)
      continue;
    if ((fstat(ffd, &fs) == 0) && S_ISREG(fs.st_mode) && (fs.st_uid == geteuid()) && (fs.st_gid == ra.st_gid))
      (void)fchmod(ffd, (mode_t)((fs.st_mode & 07777) | S_IRGRP | S_IWGRP));
    close(ffd);
  }
  close(dfd);
}

/* END-CODE */
