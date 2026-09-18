/* SDEXT_EGUID.C
 * Set / restore euid/egid for SD via SDEXT (op_sdext.c) 
 * Copyright (c)2025 The SD Developers, All Rights Reserved
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
 * to do- add STATUS() = 0 successful call, or  STATUS() = 1 unsuccessful call
 * 
 * START-HISTORY:
 * rev 0.9.0 Jan 25 mab initial commit
 * 18 Sep 26 dm TEARDOWN (S.26).  The group reload no longer asks for euid 0:
 *               the administrator is a local sdsys session, which is never
 *               root, and CPROC's logto calls EUID_SET for it so a LOGTO
 *               picks up account groups created since the session started.
 *               initgroups() only grants the caller groups it is genuinely a
 *               member of, so reloading for every caller is safe.
 * 14 Sep 26 dm  SD_EUID_SET reloads root's supplementary groups before the
 *               drop, so a session sees account groups created since it
 *               started (PROJECT_STATUS S.2).
  * START-DESCRIPTION:
 *
 *
 * END-DESCRIPTION
 *
 * defined in keys.h
*
 * START-CODE
 */


#include "sd.h"
#include <linux/limits.h>
#include <pwd.h>
#include <grp.h>

#include "keys.h"

/* caller_uid, caller_gid need to hang around for restore */
uid_t caller_uid = -1;  /* uid saved with SD_EUID_SET call*/
gid_t caller_gid = -1;  /* gid saved with SD_EUID_SET call*/

void sdext_eguid_set(int key, char* Arg){

  struct passwd *pwd;
  int myResult;
   
  process.status = 0;   /* setup status() value */
  myResult = 0;         /* init result response */
  /*Evaluate KEY */
  
  switch (key) {

    case SD_EUID_SET : /* set user id */
      /* Arg is the passed user name */
      
      caller_uid = getuid ();  // returns the real UID of the current process
      caller_gid = getgid();   // returns the real group ID of the current process

      /* 14 Sep 26 dm - S.2.  Reload the supplementary groups while still root.
         seteuid() keeps the group list the process started with, and the
         euid drop below leaves file access to those groups (root is a member
         of every sdu_<account> group; sdsys often is not).  So a sudo sd
         session could not LOGTO an account whose group was created after it
         started: a fatal 3001 at CPROC's openpath "voc".  Witnessed 14 Sep
         2026 with root run without sdu_don (setpriv --groups 979); with the
         group, the same LOGTO entered don.  This runs at
         session start and after every privileged verb (CPROC's drop back), so
         the list is current then.  It grants root no group it is not already
         a member of.  A failure keeps the old list and is not an error: the
         drop still happens exactly as before.  getpwuid() before getpwnam()
         below, which reuses the same static buffer.

         18 Sep 26 dm - TEARDOWN (S.26).  NOT ROOT-ONLY ANY MORE.  The
         administrator is now a local sdsys session (never euid 0), and
         CPROC's logto calls this function for it, so the reload must apply
         to the sdsys caller too - otherwise the S.2 defect returns for the
         administrator.  initgroups() installs the caller's own real group
         list and nothing else, so doing it for every caller is safe; the
         caller cannot gain a group it is not a member of.                    */
      pwd = getpwuid(caller_uid);
      if (pwd != NULL)
        (void)initgroups(pwd->pw_name, caller_gid);

      /* attempt to set to user uid */
      /* first get users uid         */
      pwd = getpwnam(Arg);
      if (pwd != NULL) {
        /* got user, now set effective UID and GID to whats defined for user */
        if ((setegid(pwd->pw_gid) == 0) && (seteuid(pwd->pw_uid) == 0)){
          strncpy(process.username, Arg, MAX_USERNAME_LEN+1);   // worked, change sd process user name to match
        }else{
          myResult =  SD_EUID_SET_Err; // Couldn't set proess to uid / gid of user 
          process.status = errno;      // return os error in status()
        } 

      } else {
        myResult =  SD_EUID_PWD_Err;    // Couldn't get pwd of user   
    
      }
     
      process.status = myResult;
      InitDescr(e_stack, INTEGER);
      (e_stack++)->data.value = (int32_t)myResult;
      break;

    case SD_EUID_RESTORE: /* Restore euid    */
      /* Modified by Composer AI - 2026/06/10.
         caller_uid is uid_t (unsigned), so "caller_uid < 0" is always false
         and the "RESTORE before SET" error could never be reported. Compare
         against the (uid_t)-1 sentinel it is initialized with instead. */
      /* if (caller_uid < 0){ */
      if (caller_uid == (uid_t)-1){
      /* -------------------- */
        myResult =  SD_EUID_NSET_Err; /* SD_EUID_RESTORE called before SD_EUID_SET */ 
      } else {
        if (((setegid(caller_gid) == 0) && (seteuid(caller_uid) == 0)) == FALSE){
           myResult =  SD_EUID_RST_Err; /* Couldn't return proess to uid / gid of caller */
           process.status = errno;      // return os error in status()
        }
      }

      process.status = myResult;
      InitDescr(e_stack, INTEGER);
      (e_stack++)->data.value = (int32_t)myResult;
      break;

  }

  return;
}
