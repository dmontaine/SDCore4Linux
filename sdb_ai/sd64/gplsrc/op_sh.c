/* OP_SH.C
 * Shell command execution
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
 * 18 Oct 26 dm S.65 slice 3e: edit_kind_of_net_name(): which S.64 kind (VOC, dictionary, program file) the name of a file on another SD
 *           server says it is; a "dict " prefix is a dictionary. net_gate() and K_EDIT_OK / K_EDIT_KIND use it through the file variable.
 * 17 Oct 26 dm S.64 part 2: the private catalogue directory (the value of $PRIVATE.CATALOGUE, "cat" by default, resolved against
 *           the account directory as the OS resolves it, never by the bare name) is a PROGRAM FILE: edit_kind_of_path() answers
 *           EDIT_PROG for it and edit_os_path_refusal() for it and for anything below it. The scan of a last component moved to
 *           edit_kind_of_name(), because edit_os_path_refusal() classifies bare components. edit_os_path_refusal() takes
 *           include_leaf: OPENSEQ, DELETESEQ and a print file name a plain file as the final component, and that name is a
 *           record, not a program file. edit_leaf_counts() decides it for OSCOPY's target and OSPATH's delete (a directory or
 *           anything that is not a plain file counts).
 * 17 Oct 26 dm S.64: edit_kind_of_path(), edit_permitted() and edit_ok_for_path(): which of a VOC, a dictionary and a
 *           program file a pathname is, and whether the session may save a change to it (the gates voc.edit, dict.edit
 *           and bp.edit, loaded at sign-on into the user table's gates word). op_dio3.c asks them before a write, a
 *           delete or a clear; K_EDIT_OK and K_EDIT_KIND let a $internal program ask the same question.
 * 13 Oct 26 dm S.63: os_permitted() is back, and the gate now reaches OS paths. OS.EXECUTE and the SH
 *           verb are refused (10053, 10054, the Windows port's wording) to an account that has not been
 *           given them; OPENSEQ and OPENPATH by pathname are refused (ER_PERM) outside the account's own
 *           directory unless it holds OS.EXECUTE; K_PATH_OK lets an $internal program (SED) ask the same
 *           question on the user's behalf. SH and OS.EXECUTE are OFF by default and SDSYS switches them
 *           (owner, 13 Oct 2026: the tiers were to go and the gates to stay).
 * 18 Sep 26 dm Teardown (S.27): os_permitted() and its refusal are gone.
 *           OS.EXECUTE and the SH verb now run at the account's own Linux
 *           permissions - the euid drop already made a session the account's
 *           OS user, and SD keeps no second wall (owner's teardown of the
 *           tier model, 18 Sep 2026).
 * 10 Sep 26 dm  Parity audit: the SH1 clparse bound is 8, so a long configured
 *               SH1 cannot write past argv (the Windows port's PRE_RELEASE 174).
 * 09 Sep 26 dm PRE_RELEASE 23 commit 2: os_permitted() also honours USR_OS_EXEC,
 *           the per-account ACC$OS.EXEC grant loaded at account entry, so an
 *           administrator can give a named non-admin account OS.EXECUTE.
 * 09 Sep 26 dm PRE_RELEASE 23 commit 1: os_permitted() gates OS.EXECUTE to a
 *           $internal program or an administrator (owner's model, 9 Sep 26:
 *           "os.execute and shell are off for anyone but administrators").
 *           op_sh() was previously ungated.  The per-account ACC$OS.EXEC grant
 *           that widens this to named non-admins is commit 2.
 * 31 Dec 23 SD launch - prior history suppressed
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "header.h"
#include "syscom.h"
#include "tio.h"
#include "config.h"
#include <signal.h>
#include <dirent.h>
#include <grp.h>
#include <strings.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <sys/wait.h>

/* Modified by Composer AI - 2026/06/10.
   k_error() never returns, but the analyzer cannot see that across
   translation units. */
void k_error(char msg[], ...) __attribute__((noreturn));
/* -------------------- */

void set_term(bool trap_break);
void set_old_tty_modes(void);
void set_new_tty_modes(void);
void op_capture(void);

Private void sh(bool capture);
Private void sh_execute(char *command);
Private int clparse(char *p, char *argv[], int maxargs);
Private bool os_permitted(void);
Private bool path_inside_dir(const char *rootdir, const char *name);

int ChildPipe = -1;
bool in_sh = FALSE; /* 0562 Doing SH command? */

#define MAX_SH_COMMAND_LENGTH 32000
Private char *cmd_str = NULL;

/* ======================================================================
   op_sh()  -  Launch a DOS command                                       */

void op_sh() {
  /* Stack:

     |=============================|=============================|
     |            BEFORE           |           AFTER             |
     |=============================|=============================|
 top |  Command to execute         |                             |
     |=============================|=============================|
 */

  sh(FALSE);
}

/* ======================================================================
   op_shcap  -  Launch SH command, capturing output                       */

void op_shcap() {
  /* Stack:

     |=============================|=============================|
     |            BEFORE           |           AFTER             |
     |=============================|=============================|
 top |  ADDR to capture variable   |                             |
     |-----------------------------|-----------------------------|
     |  Command to execute         |                             |
     |=============================|=============================|
 */

  DESCRIPTOR temp;

  /* Swap top two stack items so that the command is on top */

  temp = *(e_stack - 1);
  *(e_stack - 1) = *(e_stack - 2);
  *(e_stack - 2) = temp;

  sh(TRUE);
}

/* ======================================================================
   The OS-access gates (13 Oct 26, S.63).

   os_gate_open()  -  has THIS ACCOUNT been given OS access?  The administrator always has it; anyone else
   has it only if SDSYS switched it on (MODIFY.ACCOUNT OS-ON), which LOGIN and CPROC logto load into the
   session at account entry.  It does NOT look at HDR_INTERNAL, because the question it answers is about
   the person, not about the program: an $internal program that acts for the user (SED opening a file by
   pathname) is exempt from the gate itself and must not become the way round it.

   os_permitted()  -  may THIS PROGRAM run OS.EXECUTE or the SH verb?  Three answers, in the Windows
   port's order: a $internal system program (every shipped OS.EXECUTE caller is one) is trusted; otherwise
   the account must hold the gate.  The SH verb and "!" are gated by CPROC at the prompt (os.command, on
   K_SH) and reach here as an internal caller.

   os_path_ok_for_account()  -  may this account open this OS pathname with OPENSEQ or OPENPATH?  Yes if
   it holds the gate; otherwise only inside its own directory (the process's working directory, which is
   the account, set by LOGIN and CPROC and not changeable from BASIC).  The name is resolved with
   realpath() before the comparison - the longest part that exists, then the rest - so ".." and a symbolic
   link inside the account that points out of it do not get round it.  A path it cannot resolve is a no.

   os_path_open_ok()  -  the same for a caller: an $internal program is trusted, anyone else is asked.   */

bool os_gate_open(void) {
  return (my_uptr->flags & (USR_ADMIN | USR_OS_EXEC)) != 0;
}

Private bool os_permitted(void) {
  if (process.program.flags & HDR_INTERNAL)
    return TRUE;
  return os_gate_open();
}

/* 13 Oct 26 (second sitting): the test is "inside THIS directory", and the account's own directory is the
   case where the directory is the working directory (rootdir NULL).  A directory given is for a path reached
   through a Q-pointer into another account (os_path_inside, K_PATH_IN), whose own tree a restricted account
   may then use.  A relative name is relative to the directory asked about.                                  */
/* resolve_name()  -  The pathname NAME, relative to the directory CWD when it is not absolute, with ".." and links resolved
   as far as it exists (16 Oct 26: the middle of path_inside_dir, taken out so that the SD.ACCOUNTS test uses the same one).
   RESOLVED has room for 2 * PATH_MAX + 2.  False when it cannot be resolved.                                           */
Private bool resolve_name(const char *cwd, const char *name, char *resolved) {
  char work[2 * PATH_MAX + 2];
  char tail[PATH_MAX + 1];
  char *p;
  size_t n;

  if (name[0] == '/') {
    if (strlen(name) > PATH_MAX)
      return FALSE;
    strcpy(work, name);
  } else {
    if (strlen(cwd) + strlen(name) + 2 > sizeof(work))
      return FALSE;
    strcpy(work, cwd);
    strcat(work, "/");
    strcat(work, name);
  }

  /* Resolve what exists; whatever does not yet exist (a file about to be created) is the tail, and a tail
     may not contain ".." because there is nothing to resolve it against. */
  tail[0] = '\0';
  for (;;) {
    if (realpath(work, resolved) != NULL)
      break;
    p = strrchr(work, '/');
    if (p == NULL)
      return FALSE;
    if ((strcmp(p + 1, "..") == 0) || (strcmp(p + 1, ".") == 0))
      return FALSE;
    if (p[1] != '\0') {
      /* prepend this component to the tail */
      n = strlen(p + 1);
      if (n + strlen(tail) + 2 > sizeof(tail))
        return FALSE;
      if (tail[0] != '\0') {
        memmove(tail + n + 1, tail, strlen(tail) + 1);
        tail[n] = '/';
        memcpy(tail, p + 1, n);
      } else {
        memcpy(tail, p + 1, n + 1);
      }
    }
    if (p == work) {
      /* only the root is left */
      strcpy(resolved, "/");
      break;
    }
    *p = '\0';
  }

  if (tail[0] != '\0') {
    if (strlen(resolved) + strlen(tail) + 2 > 2 * PATH_MAX + 2)    /* RESOLVED is a pointer here: not sizeof */
      return FALSE;
    if (strcmp(resolved, "/") != 0)
      strcat(resolved, "/");
    strcat(resolved, tail);
  }
  return TRUE;
}

Private bool path_inside_dir(const char *rootdir, const char *name) {
  char cwd[PATH_MAX + 1];
  char root[PATH_MAX + 1];
  char resolved[2 * PATH_MAX + 2];      /* realpath() needs PATH_MAX; the tail is appended after it */
  size_t root_len;

  if ((name == NULL) || (name[0] == '\0'))
    return FALSE;
  if (rootdir != NULL) {
    if ((rootdir[0] != '/') || (strlen(rootdir) > PATH_MAX))
      return FALSE;
    strcpy(cwd, rootdir);
  } else if (getcwd(cwd, sizeof(cwd)) == NULL)
    return FALSE;
  if (realpath(cwd, root) == NULL)
    return FALSE;
  if (!resolve_name(cwd, name, resolved))
    return FALSE;

  root_len = strlen(root);
  while ((root_len > 1) && (root[root_len - 1] == '/'))
    root[--root_len] = '\0';
  if (root_len == 1)           /* an account at "/" would contain the whole machine: refuse */
    return FALSE;

  if (strncmp(resolved, root, root_len) != 0)
    return FALSE;
  return (resolved[root_len] == '\0') || (resolved[root_len] == '/');
}

/* ======================================================================
   The SD.ACCOUNTS gate (16 Oct 26, QM4 gap 22; the owner: "one that gives access to any file in any SD account directory the
   user has logto access to").  Between "its own account only" and OS.EXECUTE, which reaches the whole machine: with the gate an
   account reaches any file under the directory of an account its user could LOGTO - the register's group is one the user is in,
   and the account is not suspended - EXCEPT the VOC of that account (voc and voc.dic at the top of it), which is the account's
   own control record set.  SDSYS and OS.EXECUTE pass before this is asked.  The register is read a record at a time, as
   LOGTO reads it: line 1 the path, line 3 the group, line 5 SUSPENDED.  A path that is not absolute is skipped.             */

Private bool user_in_group(const char *group) {
  struct group *g;
  gid_t list[NGROUPS_MAX + 1];
  int n, i;

  if ((group == NULL) || (group[0] == '\0') || ((g = getgrnam(group)) == NULL))
    return FALSE;
  if ((g->gr_gid == getegid()) || (g->gr_gid == getgid()))
    return TRUE;
  n = getgroups(NGROUPS_MAX, list);
  for (i = 0; i < n; i++) {
    if (list[i] == g->gr_gid)
      return TRUE;
  }
  return FALSE;
}

bool os_sd_accounts_open(void) {
  return (my_uptr->flags & (USR_ADMIN | USR_OS_EXEC | USR_SD_ACCOUNTS)) != 0;
}

Private bool path_in_enterable_account(const char *name) {
  char cwd[PATH_MAX + 1];
  char resolved[2 * PATH_MAX + 2];
  char regdir[PATH_MAX + 1];
  char recpath[PATH_MAX + 1];
  char body[4096];
  char root[PATH_MAX + 1];
  char *line[6];
  char *p;
  DIR *d;
  struct dirent *ent;
  FILE *fp;
  size_t got, root_len, i;
  bool found = FALSE;

  if ((name == NULL) || (name[0] == '\0') || (getcwd(cwd, sizeof(cwd)) == NULL) || !resolve_name(cwd, name, resolved))
    return FALSE;
  if (snprintf(regdir, sizeof(regdir), "%s%caccounts", sysseg->sysdir, DS) >= (int)sizeof(regdir))
    return FALSE;
  if ((d = opendir(regdir)) == NULL)
    return FALSE;
  while (!found && ((ent = readdir(d)) != NULL)) {
    if ((ent->d_name[0] == '.') || (ent->d_name[0] == '%') || (strchr(ent->d_name, '/') != NULL))
      continue;
    if (snprintf(recpath, sizeof(recpath), "%s%c%s", regdir, DS, ent->d_name) >= (int)sizeof(recpath))
      continue;
    if ((fp = fopen(recpath, "r")) == NULL)
      continue;
    got = fread(body, 1, sizeof(body) - 1, fp);
    fclose(fp);
    body[got] = '\0';
    p = body;
    for (i = 0; i < 6; i++) { /* the first lines of the record; one that is missing is empty */
      if (p == NULL) {
        line[i] = body + got;
        continue;
      }
      line[i] = p;
      if ((p = strchr(p, '\n')) != NULL)
        *p++ = '\0';
    }
    if ((line[0][0] != '/') || (strlen(line[0]) > PATH_MAX) || (realpath(line[0], root) == NULL))
      continue;
    if (!strcasecmp(line[4], "SUSPENDED"))
      continue;
    root_len = strlen(root);
    while ((root_len > 1) && (root[root_len - 1] == '/'))
      root[--root_len] = '\0';
    if (root_len <= 1)
      continue;
    if ((strncmp(resolved, root, root_len) != 0) || ((resolved[root_len] != '\0') && (resolved[root_len] != '/')))
      continue;
    if (!user_in_group(line[2]))
      continue;
    /* The VOC of the account is not part of what this gate opens */
    p = resolved + root_len;
    if (*p == '/')
      p++;
    if ((strncmp(p, "voc", 3) == 0) && ((p[3] == '\0') || (p[3] == '/') || (strncmp(p + 3, ".dic", 4) == 0 && (p[7] == '\0' || p[7] == '/'))))
      found = FALSE; /* and it is in no other account */
    else
      found = TRUE;
    break;
  }
  closedir(d);
  return found;
}

bool os_path_ok_for_account(const char *name) {
  if (os_gate_open())
    return TRUE;
  if (path_inside_dir(NULL, name))
    return TRUE;
  return (my_uptr->flags & USR_SD_ACCOUNTS) && path_in_enterable_account(name);
}

/* os_path_inside()  -  is this pathname inside THAT directory?  The OS gate is not asked: this is the geometry
   alone, for a BASIC program (_voc_ref) that has already decided a directory is one the account may use.  */
bool os_path_inside(const char *rootdir, const char *name) {
  return path_inside_dir(rootdir, name);
}

bool os_path_open_ok(const char *name) {
  if (process.program.flags & HDR_INTERNAL)
    return TRUE;
  return os_path_ok_for_account(name);
}

/* ======================================================================
   last_component()  -  The final component of a pathname, trailing slashes ignored.  Returns a pointer into PATH and sets
   *LEN to its length, which is 0 for a null name or a bare "/".                                                       */

Private const char *last_component(const char *path, size_t *len) {
  const char *last;
  const char *p;
  size_t n;

  *len = 0;
  if (path == NULL)
    return NULL;
  n = strlen(path);
  while ((n > 0) && (path[n - 1] == '/'))
    n--;
  if (n == 0)
    return NULL;
  last = path;
  for (p = path; p < path + n; p++) {
    if (*p == '/')
      last = p + 1;
  }
  *len = (size_t)((path + n) - last);
  return last;
}

/* ======================================================================
   edit_kind_of_name()  -  Which of the three guarded kinds of file does the LAST COMPONENT of this name say it is?

   17 Oct 26 dm, S.64 (owner, 17 Oct: the gates voc.edit, bp.edit and dict.edit).  By the last component of the pathname
   of the OPEN file, not by the name that was typed, so a Q-pointer or an F-pointer to one is caught (Linux Solo's
   voc_write_refused() does the same for the VOC alone).  Case does not matter; every name SD makes is lower case.
     VOC          voc
     dictionary   anything ending .dic         (voc.dic is the dictionary of the VOC, not the VOC)
     program      bp, bp.out, anything ending .bp or .bp.out
   bp.out is in because an object file written straight into it is the same as compiling one (owner's D3, 17 Oct, said
   "bp or *.bp"; the object directory is part of that meaning and the plan file says so).  A trailing slash is ignored.

   Names only.  edit_os_path_refusal() classifies the bare components of a path with this; the private catalogue is a place,
   not a name, and is added by edit_kind_of_path() for the pathname of a file.                                          */

Private int edit_kind_of_name(const char *path) {
  const char *last;
  size_t n;

  last = last_component(path, &n);
  if (n == 0)
    return EDIT_NONE;

  if ((n == 3) && (strncasecmp(last, "voc", 3) == 0))
    return EDIT_VOC;
  if ((n > 4) && (strncasecmp(last + n - 4, ".dic", 4) == 0))
    return EDIT_DICT;
  if ((n == 2) && (strncasecmp(last, "bp", 2) == 0))
    return EDIT_PROG;
  if ((n == 6) && (strncasecmp(last, "bp.out", 6) == 0))
    return EDIT_PROG;
  if ((n > 3) && (strncasecmp(last + n - 3, ".bp", 3) == 0))
    return EDIT_PROG;
  if ((n > 7) && (strncasecmp(last + n - 7, ".bp.out", 7) == 0))
    return EDIT_PROG;
  return EDIT_NONE;
}

/* ======================================================================
   The private catalogue as a program file (17 Oct 26 dm, S.64 part 2, from the review).

   CATALOG, DELETE.CATALOG and DECATALOG are refused without bp.edit (message 11408) because they change the code a command
   finds, and the catalogue is a plain directory: with nothing here, OPENPATH "cat" and DELETE / CLEARFILE / WRITE on it, a
   Q- or F-pointer to it, OSCOPY into it and OSPATH on it did the same thing with no gate.  So the directory is a program file.

   WHICH DIRECTORY: the one the kernel loads commands from, private_catalogue (set by the K$PRIVATE.CATALOGUE key from the
   $PRIVATE.CATALOGUE entry of the VOC, "cat" when there is none), resolved against the account directory as a pathname is
   resolved by the OS gate.  NOT by the bare name "cat": a data directory that happens to be called cat somewhere else is
   an ordinary file.  The gate follows the configured catalogue, and a catalogue outside the account is still one.

   The private catalogue is a per-process variable, like the account directory, so nothing here is shared between users.    */

/* private_catalogue_dir()  -  the private catalogue directory, resolved, in CAT (room for 2 * PATH_MAX + 2) without a trailing
   slash.  CWD is the account directory.  False when there is none, it cannot be resolved, or it would be the root.         */
Private bool private_catalogue_dir(const char *cwd, char *cat) {
  size_t n;

  if ((private_catalogue[0] == '\0') || !resolve_name(cwd, private_catalogue, cat))
    return FALSE;
  n = strlen(cat);
  while ((n > 1) && (cat[n - 1] == '/'))
    cat[--n] = '\0';
  return (n > 1);
}

/* catalogue_position()  -  where is this RESOLVED pathname against the private catalogue?  0 elsewhere, 1 the directory itself,
   2 something below it.                                                                                                    */
Private int catalogue_position(const char *cwd, const char *resolved) {
  char cat[2 * PATH_MAX + 2];
  size_t n;

  if (!private_catalogue_dir(cwd, cat))
    return 0;
  n = strlen(cat);
  if (strncmp(resolved, cat, n) != 0)
    return 0;
  if (resolved[n] == '\0')
    return 1;
  return (resolved[n] == '/') ? 2 : 0;
}

/* path_is_private_catalogue()  -  is this the pathname OF the private catalogue directory (the pathname of an open file)?
   edit_kind_of_path() is asked before every WRITE a session makes to a file it may not be allowed to change, so the test
   that costs something - two realpath() calls - is made only when the last component is the catalogue's own name.        */
Private bool path_is_private_catalogue(const char *path) {
  char cwd[PATH_MAX + 1];
  char resolved[2 * PATH_MAX + 2];
  const char *last;
  const char *cat_last;
  size_t n, cat_n;

  last = last_component(path, &n);
  cat_last = last_component(private_catalogue, &cat_n);
  if ((n == 0) || (cat_n == 0) || (n != cat_n) || (strncasecmp(last, cat_last, n) != 0))
    return FALSE;
  /* Same final name: now by place.  A name that cannot be placed is taken as the catalogue (a gate that fails open on a path it
     cannot read is decoration); only a file of the catalogue's own name reaches here. */
  if ((getcwd(cwd, sizeof(cwd)) == NULL) || !resolve_name(cwd, path, resolved))
    return TRUE;
  return catalogue_position(cwd, resolved) == 1;
}

/* ======================================================================
   edit_kind_of_path()  -  Which of the three guarded kinds of file is this?  The PATHNAME of an open file: by its last
   component (edit_kind_of_name), or the private catalogue directory, which is a program file.                          */

int edit_kind_of_path(const char *path) {
  int kind = edit_kind_of_name(path);

  if ((kind == EDIT_NONE) && path_is_private_catalogue(path))
    return EDIT_PROG;
  return kind;
}

/* ======================================================================
   edit_kind_of_net_name()  -  The same question for the NAME of a file on another SD server (S.65 slice 3e), which is how a remote
   file is told apart: "voc", "<name>.dic", "bp", "bp.out", "<name>.bp", "<name>.bp.out", or "dict <name>" for the dictionary part of
   any file.  The name has no '/' (the handler refuses one), so edit_kind_of_name() sees all of it.  NOT edit_kind_of_path(): its
   private catalogue test resolves a path against this process's directory, which says nothing about a name on another machine.  */

int edit_kind_of_net_name(const char *name) {
  if (strncasecmp(name, "dict ", 5) == 0)
    return EDIT_DICT;
  return edit_kind_of_name(name);
}

/* edit_permitted()  -  may THIS SESSION save a change to a file of that kind?  The administrator may always; anybody else
   needs the gate for the kind, loaded at sign-on (UG_x in the user table's gates word) from the register.            */

bool edit_permitted(int kind) {
  if (my_uptr->flags & USR_ADMIN)
    return TRUE;
  switch (kind) {
    case EDIT_VOC:
      return (my_uptr->gates & UG_VOC_EDIT) != 0;
    case EDIT_DICT:
      return (my_uptr->gates & UG_DICT_EDIT) != 0;
    case EDIT_PROG:
      return (my_uptr->gates & UG_BP_EDIT) != 0;
  }
  return TRUE;
}

bool edit_ok_for_path(const char *path) {
  int kind = edit_kind_of_path(path);

  return (kind == EDIT_NONE) || edit_permitted(kind);
}

/* edit_os_path_refusal()  -  the OS-PATH routes to the same files: OPENSEQ, DELETESEQ, OSRENAME, a print file, OSCOPY.

   A program file's records are files of a directory, so OPENSEQ 'bp','prog' and WRITESEQ change one as WRITE would, past the test
   in op_dio3.c; a dictionary or the VOC can be corrupted the same way.  So the pathname a program gives is looked at for a
   component that names a VOC, a dictionary or a program file: the path is resolved as the OS gate resolves it, and every component
   below the account's own directory is classified (edit_kind_of_name).  Returns EDIT_NONE when the session may go on, or the kind
   it may not change.  Read-only use is not asked: the callers use this where they would write, create, delete or rename.

   INCLUDE_LEAF says whether the FINAL component is classified too.  A caller that names a plain file there - OPENSEQ, DELETESEQ and
   a print file make or remove a regular file, never a directory - passes FALSE: the final name is a record of whatever file holds
   it, and a record called x.bp in an ordinary directory file is not a program file (the kernel judges the file, not the record).
   A caller whose final component may itself be a directory - the target of OSCOPY, which can be a directory, OSPATH deleting or
   making one - passes TRUE.  CREATE.FILE and OPENTEMP pass FALSE: the name they make is the new file, and a new file called bp or
   x.dic is what CREATE.FILE makes without the gate; it is what they put INSIDE a guarded directory that is refused.  Every
   directory below the final component is classified either way.

   The private catalogue directory, and anything below it, is a program file as well (see edit_kind_of_path), whichever of its
   own names the final component has; the catalogue itself counts only when INCLUDE_LEAF.

   NOT COVERED, and said in the documentation: an account that holds OS.EXECUTE or SH reaches the files from the shell as it
   always could, so a path outside the account's own directory is not looked at for such an account.  For one that reaches another
   account's directory through SD.ACCOUNTS the whole resolved path is searched (the other account's own catalogue is not known to
   this process and is not recognised).  A path that cannot be resolved is refused.                                           */

int edit_os_path_refusal(const char *name, bool include_leaf) {
  char cwd[PATH_MAX + 1];
  char root[PATH_MAX + 1];
  char resolved[2 * PATH_MAX + 2];
  const char *rel;
  char comp[PATH_MAX + 1];
  const char *p;
  const char *more;
  size_t root_len, n;
  int kind;
  int cat_pos;

  if (my_uptr->flags & USR_ADMIN)
    return EDIT_NONE;
  if ((name == NULL) || (name[0] == '\0'))
    return EDIT_NONE;
  if ((getcwd(cwd, sizeof(cwd)) == NULL) || !resolve_name(cwd, name, resolved) || (realpath(cwd, root) == NULL))
    return EDIT_VOC; /* cannot tell: refuse (a gate that fails open on a path it cannot read is decoration) */

  root_len = strlen(root);
  while ((root_len > 1) && (root[root_len - 1] == '/'))
    root[--root_len] = '\0';

  if ((root_len > 1) && (strncmp(resolved, root, root_len) == 0) &&
      ((resolved[root_len] == '\0') || (resolved[root_len] == '/'))) {
    rel = resolved + root_len; /* inside the account's own directory: look below it */
  } else if (my_uptr->flags & USR_OS_EXEC) {
    return EDIT_NONE; /* OS.EXECUTE: the whole machine, and a shell; not covered */
  } else {
    rel = resolved; /* another account's directory through SD.ACCOUNTS: the whole path */
  }

  /* 17 Oct 26 dm, S.64 part 2: the private catalogue is a program file, found by PLACE (resolved, as the loader reaches it) and not by its name */
  cat_pos = catalogue_position(cwd, resolved);
  if (((cat_pos == 2) || ((cat_pos == 1) && include_leaf)) && !edit_permitted(EDIT_PROG))
    return EDIT_PROG;

  for (p = rel; *p != '\0';) {
    while (*p == '/')
      p++;
    n = 0;
    while ((p[n] != '\0') && (p[n] != '/'))
      n++;
    more = p + n;
    while (*more == '/')
      more++;
    if ((n > 0) && (n < sizeof(comp)) && (include_leaf || (*more != '\0'))) {
      memcpy(comp, p, n);
      comp[n] = '\0';
      kind = edit_kind_of_name(comp);
      if ((kind != EDIT_NONE) && !edit_permitted(kind))
        return kind;
    }
    p += n;
  }
  return EDIT_NONE;
}

/* edit_leaf_counts()  -  for a caller that DELETES, or COPIES INTO, an OS pathname whose final name may be a plain file or a directory
   (OSCOPY's target, OSPATH's delete): does that final name need classifying (include_leaf TRUE)?  Only if it is there and is not a plain
   file.  A plain file called x.bp or x.dic is a record of whatever directory holds it, not a program file or a dictionary; a name not
   made yet becomes a plain file when copied to, and there is nothing to delete.  A link, which could be to a directory, counts.      */

bool edit_leaf_counts(const char *name) {
  struct stat sb;

  if ((name == NULL) || (name[0] == '\0') || (lstat(name, &sb) != 0))
    return FALSE;
  return !S_ISREG(sb.st_mode);
}

/* ======================================================================
   sh()  -  Execute shell command                                         */

Private void sh(bool capture) {
  DESCRIPTOR *descr;
  STRING_CHUNK *str;
  int bytes;

  /* 13 Oct 26 S.63: refuse before the stack is touched, so a refusal leaves it as it was found - the
     Windows port's placement.  k_error() does not return.                                            */
  if (!os_permitted())
    k_error(sysmsg(10054), process.username);

  descr = e_stack - 1;
  k_get_string(descr);
  str = descr->data.str.saddr;
  bytes = (str != NULL) ? str->string_len : 0;
  if (bytes > MAX_SH_COMMAND_LENGTH) {
    process.status = ER_LENGTH;
    k_dismiss();
  } else {
    if (cmd_str != NULL)
      k_free(cmd_str); /* From an earlier k_error() */

    cmd_str = k_alloc(111, bytes + MAX_PATHNAME_LEN + 10); /* Allow for strcat on Windows */
    k_get_c_string(descr, cmd_str, bytes);
    k_dismiss();

    if (capture) {
      /* Set up capture mechanism */

      if (capturing) /* This is a nested EXECUTE...CAPTURING structure */
      {
        process.program.flags |= PF_CAPTURING;

        if (capture_head != NULL) /* Stack data already captured */
        {
          process.program.saved_capture_head = capture_head;
          process.program.saved_capture_tail = capture_tail;
        }
      }

      capture_head = NULL;
      capturing = TRUE;
      stack_display_pu();
    }

    sh_execute(cmd_str);
    k_free(cmd_str);
    cmd_str = NULL;

    if (capture) {
      op_capture(); /* Use op_capture() to save the command output */
    }
  }
}

/* ======================================================================
   sh_execute()  -  Execute SH command                                    */

Private void sh_execute(char *command) {
#define PIPE_BUFFER_SIZE 2048
  char buffer[PIPE_BUFFER_SIZE];
  bool saved_trap_break_char;
  bool saved_pagination;
  bool use_output_pipe;
  /* Modified by Composer AI - 2026/06/10.
     Initialize pipe fd pairs so paths that skip pipe() do not read
     indeterminate values; use -1 for unused slots. */
  /* int ChildToSDPipe[2]; */
  int ChildToSDPipe[2] = {-1, -1};
  bool use_input_pipe;
  /* int SDToChildPipe[2]; */
  int SDToChildPipe[2] = {-1, -1};
  /* -------------------- */
  char *argv[10];
  int cpid;
  int16_t i;
  int bytes;
  int child_status;

  char dflt_sh[] = "/bin/bash -i";
  char dflt_sh1[] = "/bin/bash -c";

  saved_trap_break_char = trap_break_char;
  saved_pagination = (tio.dsp.flags & PU_PAGINATE) != 0;

  process.status = 0;
  process.os_error = 0;

  flush_dh_cache();

  /* Turn off pagination.  Much as it would be nice, we get thoroughly
    confused about whether input is for the executed command or a response
    to the end of page prompt.                                             */

  tio.dsp.flags &= ~PU_PAGINATE;

  set_old_tty_modes();
  in_sh = TRUE; /* 0562 */

  /* If the user entered SD from the operating system command prompt, we
    can simply let the child process take over our stdout and stderr.
    If they have come in from a network or we need to capture the output
    for some reason, we must use a pipe. Although it sounds simpler always
    to use the pipe, this has some impact on the executed commands if they
    check the device type of the standard file handles.                     */

  use_output_pipe = capturing                          /* Trap output for EXECUTE CAPTURING */
                    || (connection_type != CN_CONSOLE) /* Not a direct connection */
                    || (tio.como_file >= 0);           /* Real como file */

  /* Similarly, on the input side, we need to use a pipe to feed the shell
    process if the real source of input is a socket. This allows us to
    perform input editing and avoids the shell moaning that stdin is not
    suitable.                                                             */

  use_input_pipe = (connection_type == CN_SOCKET);

  if (use_output_pipe && pipe(ChildToSDPipe)) {
    k_error("Cannot create child output pipe");
  }

  if (use_input_pipe && pipe(SDToChildPipe)) {
    /* Modified by Composer AI - 2026/06/10.
       Close the output pipe if input pipe creation fails. */
    if (use_output_pipe) {
      close(ChildToSDPipe[0]);
      close(ChildToSDPipe[1]);
    }
    /* -------------------- */
    k_error("Cannot create child input pipe");
  }

  /* 0420 Disable sigchld handler
    We need to do this to prevent the handler catching termination of
    the child process created below to execute this command.           */

  signal(SIGCHLD, SIG_DFL);

  cpid = fork();
  if (cpid == 0) /* Child process */
  {
    if (use_output_pipe) {
      dup2(ChildToSDPipe[1], 1);
      dup2(ChildToSDPipe[1], 2);
    }

    if (use_input_pipe) {
      dup2(SDToChildPipe[0], 0);
    }

    for (i = 3; i < 1024; i++)
      close(i);

    if (command[0] == '\0') /* Interactive shell */
    {
      clparse((pcfg.sh[0] != '\0') ? pcfg.sh : dflt_sh, argv, 10);
    } else /* Single command */
    {
      /* 10 Sep 26 dm - Parity audit: 8, NOT 9 (the Windows port's fix, its
         PRE_RELEASE_FIXES 174).  clparse returns AT MOST maxargs, and the two
         lines below write argv[i] and argv[i + 1]; argv holds 10 pointers, so a
         maxargs of 9 could write argv[10], one past the end, for any configured
         SH1 of nine or more space-separated tokens.  Reachable from the config
         file.  The interactive branch above keeps 10: it appends nothing. */
      i = clparse((pcfg.sh1[0] != '\0') ? pcfg.sh1 : dflt_sh1, argv, 8);
      argv[i] = command;
      argv[i + 1] = NULL;
    }

    execv(argv[0], argv);
  } else if (cpid == -1) /* Error */
  {
    /* Modified by Composer AI - 2026/06/10.
       fork() failed; close any pipes that were opened. */
    if (use_output_pipe) {
      close(ChildToSDPipe[0]);
      close(ChildToSDPipe[1]);
    }
    if (use_input_pipe) {
      close(SDToChildPipe[0]);
      close(SDToChildPipe[1]);
    }
    /* -------------------- */
    k_error("Failed to start");
  } else /* Parent process */
  {
    if (use_input_pipe) {
      ChildPipe = SDToChildPipe[1];
      close(SDToChildPipe[0]);
    }

    if (use_output_pipe) {
      close(ChildToSDPipe[1]);

      while ((bytes = read(ChildToSDPipe[0], buffer, PIPE_BUFFER_SIZE)) > 0) {
        tio_display_string(buffer, bytes, TRUE, FALSE);
      }

      close(ChildToSDPipe[0]);
    }

    waitpid(cpid, &child_status, 0);
    process.os_error = WEXITSTATUS(child_status); /* 0420 */

    /* 0420 Re-enable sigchld handler and clear any backlog */

    signal(SIGCHLD, sigchld_handler);
    while (waitpid(-1, &child_status, WNOHANG) > 0) {
    }

    if (use_input_pipe) {
      ChildPipe = -1;
      close(SDToChildPipe[1]);
    }
  }

  set_new_tty_modes();
  in_sh = FALSE; /* 0562 */

  if (saved_pagination)
    tio.dsp.flags |= PU_PAGINATE;
  else
    tio.dsp.flags &= ~PU_PAGINATE;
  set_term(saved_trap_break_char);
}

/* ======================================================================
   clparse()  -  Parse a command line into an argv array                  */

Private int clparse(char *p, char *argv[], int maxargs) {
  int argc; /* resolves CWE-197 */

  /* Although this works for our purposes, it isn't perfect. It really
    should handle quotes and \ escapes.                                */

  for (argc = 0; argc < maxargs; argc++) {
    if ((argv[argc] = strtok(p, " ")) == NULL)
      break;
    p = NULL;
  }

  return argc;
}

/* END-CODE */
