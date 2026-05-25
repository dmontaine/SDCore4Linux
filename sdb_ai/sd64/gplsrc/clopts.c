/* CLOPTS.C
 * Special command line option processing
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
 * 31 Dec 23 SD Launch - prior history suppressed
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 * CLI helpers (from sd.c): -K kill user(s), -U show users, -CLEANUP,
 * -SUSPEND / -RESUME. recover_users() is for the running kernel only
 * (not a separate sd command-line flag); see op_kernel.c.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include <signal.h>
#include <stdlib.h>
#include "sd.h"
#include "locks.h"

/* StartExclusive() debug ids for this module */
#define CLOPTS_LOCK_RECOVER 45
#define CLOPTS_LOCK_KILL 68
#define CLOPTS_LOCK_CLEANUP 59

#define CLOPTS_ORIGIN_LEN (MAX_TTYNAME_LEN + 1 + MAX_SOCKET_ADDR_STR_LEN + 4)

Private void kill_process(USER_ENTRY* uptr);
Private bool process_exists(int pid);
Private void remove_user(USER_ENTRY* uptr);

/* ======================================================================
   recover_users()  -  Recover licence space for vanished users
   Caller must already have sysseg bound (in-process / kernel API).       */

bool recover_users() {
  bool status = FALSE;
  USER_ENTRY* uptr;
  int32_t pid;
  int16_t u;
  int16_t user_no;

  StartExclusive(FILE_TABLE_LOCK, CLOPTS_LOCK_RECOVER);
  StartExclusive(REC_LOCK_SEM, CLOPTS_LOCK_RECOVER);
  StartExclusive(GROUP_LOCK_SEM, CLOPTS_LOCK_RECOVER);
  StartExclusive(SHORT_CODE, CLOPTS_LOCK_RECOVER);

  for (u = 1; u <= sysseg->max_users; u++) {
    uptr = UPtr(u);
    user_no = uptr->uid;
    pid = uptr->pid;
    if (uptr->uid) {
      if (!process_exists(pid)) {
        remove_user(uptr);
        tio_printf("Removed user %d (pid %d)\n", (int)user_no, pid);
        status = TRUE;
      }
    }
  }

  EndExclusive(SHORT_CODE);
  EndExclusive(GROUP_LOCK_SEM);
  EndExclusive(REC_LOCK_SEM);
  EndExclusive(FILE_TABLE_LOCK);

  return status;
}

/* ======================================================================
   show_users()  -  Display user information (SD -U)                      */

void show_users() {
  int i;
  USER_ENTRY* uptr;
  char origin[CLOPTS_ORIGIN_LEN];

  if (!attach_shared_memory()) {
    fprintf(stderr, "SD is not active.\n");
    return;
  }

  printf(" Uid Pid........ Puid Origin................. Username\n");
  for (i = 1; i <= sysseg->max_users; i++) {
    uptr = UPtr(i);
    if (uptr->uid != 0) {
      if (uptr->ttyname[0] != '\0')
        snprintf(origin, sizeof(origin), "%s %s", (char*)(uptr->ttyname),
                 (char*)(uptr->ip_addr));
      else
        snprintf(origin, sizeof(origin), "%s", (char*)(uptr->ip_addr));
      printf("%4hd %11d %4d %-23s %-32s\n", uptr->uid, uptr->pid,
             (int)(uptr->puid), origin, uptr->username);
    }
  }

  unbind_sysseg();
}

/* ======================================================================
   kill_user()  -  Kill user process command line option                  */

void kill_user(char* user) {
  USER_ENTRY* uptr;
  int16_t u;
  char errmsg[80 + 1];
  int16_t uid;
  char* endp;
  long n;

  if (!attach_shared_memory()) {
    fprintf(stderr, "SD is not active.\n");
    return;
  }

  if (!get_semaphores(FALSE, errmsg)) {
    fprintf(stderr, "Cannot access semaphores.\n");
    unbind_sysseg();
    return;
  }

  StartExclusive(FILE_TABLE_LOCK, CLOPTS_LOCK_KILL);
  StartExclusive(REC_LOCK_SEM, CLOPTS_LOCK_KILL);
  StartExclusive(GROUP_LOCK_SEM, CLOPTS_LOCK_KILL);
  StartExclusive(SHORT_CODE, CLOPTS_LOCK_KILL);

  if (user == NULL) { /* Kill all users; also remove stale table entries */
    log_printf("External request to terminate all SD users.\n");
    for (u = 1; u <= sysseg->max_users; u++) {
      uptr = UPtr(u);
      if (uptr->uid != 0)
        kill_process(uptr);
    }
  } else if (IsDigit(*user)) { /* Kill user by user number */
    n = strtol(user, &endp, 10);
    if ((*endp != '\0') || (n < 1) || (n > sysseg->hi_user_no)) {
      fprintf(stderr, "Invalid user number.\n");
    } else {
      uid = (int16_t)n;
      log_printf("External request to terminate SD user %d.\n", uid);
      uptr = UserPtr(uid);
      if (uptr != NULL)
        kill_process(uptr);
      else
        fprintf(stderr, "User %d is not active.\n", uid);
    }
  } else { /* Kill user by login name */
    log_printf("External request to terminate SD sessions for user %s.\n",
               user);
    for (u = 1; u <= sysseg->max_users; u++) {
      uptr = UPtr(u);
      if ((uptr->uid != 0) && !stricmp((char*)(uptr->username), user))
        kill_process(uptr);
    }
  }

  EndExclusive(SHORT_CODE);
  EndExclusive(GROUP_LOCK_SEM);
  EndExclusive(REC_LOCK_SEM);
  EndExclusive(FILE_TABLE_LOCK);

  unbind_sysseg();
}

/* ======================================================================
   kill_process()  -  Kill a SD process                                   */

Private void kill_process(USER_ENTRY* uptr) {
  int16_t user_no;
  int pid;

  user_no = uptr->uid;
  pid = uptr->pid;

  if (process_exists(pid)) {
    uptr->events |= (uptr->flags & USR_LOGOUT) ? EVT_LOGOUT : EVT_TERMINATE;
    uptr->flags |= USR_LOGOUT;
  } else {
    remove_user(uptr);
    printf("Removed user %d (pid %d).\n", (int)user_no, pid);
  }
}

/* ======================================================================
   cleanup()  -  Clean up user tables from lost processes                 */

void cleanup() {
  USER_ENTRY* uptr;
  int16_t u;
  int16_t user_no;
  int pid;
  char username[MAX_USERNAME_LEN + 1];
  char errmsg[80 + 1];

  if (!attach_shared_memory()) {
    fprintf(stderr, "SD is not active.\n");
    return;
  }

  if (!get_semaphores(FALSE, errmsg)) {
    fprintf(stderr, "Cannot access semaphores.\n");
    unbind_sysseg();
    return;
  }

  StartExclusive(FILE_TABLE_LOCK, CLOPTS_LOCK_CLEANUP);
  StartExclusive(REC_LOCK_SEM, CLOPTS_LOCK_CLEANUP);
  StartExclusive(GROUP_LOCK_SEM, CLOPTS_LOCK_CLEANUP);
  StartExclusive(SHORT_CODE, CLOPTS_LOCK_CLEANUP);

  for (u = 1; u <= sysseg->max_users; u++) {
    uptr = UPtr(u);
    if (uptr->uid != 0) {
      pid = uptr->pid;
      if (!process_exists(pid)) {
        user_no = uptr->uid;
        strcpy(username, (char*)(uptr->username));
        remove_user(uptr);
        log_printf("Cleanup removed user %d (pid %d, %s).\n", (int)user_no, pid,
                   username);
      }
    }
  }

  EndExclusive(SHORT_CODE);
  EndExclusive(GROUP_LOCK_SEM);
  EndExclusive(REC_LOCK_SEM);
  EndExclusive(FILE_TABLE_LOCK);

  unbind_sysseg();
}

/* ======================================================================
   suspend_resume()  -  Set or clear SSF_SUSPEND (admin CLI).
   No semaphore: acceptable for admin tooling; concurrent sd may race.    */

void suspend_resume(bool suspend) {
  if (!attach_shared_memory()) {
    fprintf(stderr, "SD is not active.\n");
    return;
  }

  if (suspend)
    sysseg->flags |= SSF_SUSPEND;
  else
    sysseg->flags &= ~SSF_SUSPEND;

  unbind_sysseg();
}

/* ====================================================================== */

Private bool process_exists(int pid) {
  if (pid <= 0)
    return FALSE;
  return (!kill(pid, 0) || (errno == EPERM));
}

/* ====================================================================== */

Private void remove_user(USER_ENTRY* uptr) {
  int16_t i;
  int16_t user_no;
  FILE_ENTRY* fptr;
  RLOCK_ENTRY* lptr;
  GLOCK_ENTRY* gptr;
  u_int16_t* ufm;

  user_no = uptr->uid;

  /* Clear task locks held by this user (use uid, not process.user_no). */

  for (i = 0; i < 64; i++) {
    if (sysseg->task_locks[i] == user_no)
      sysseg->task_locks[i] = 0;
  }

  for (i = 1; i <= sysseg->used_files; i++) {
    fptr = FPtr(i);
    if (fptr->ref_ct != 0) {
      if (abs(fptr->file_lock) == user_no) {
        fptr->file_lock = 0;
        clear_waiters(-i);
      }
    }
  }

  for (i = 1; i <= sysseg->numlocks; i++) {
    lptr = RLPtr(i);

    if ((lptr->hash != 0) && (lptr->owner == user_no)) {
      (RLPtr(lptr->hash)->count)--;
      (sysseg->rl_count)--;
      (FPtr(lptr->file_id)->lock_count)--;
      lptr->hash = 0;
      if (lptr->waiters)
        clear_waiters(i);
    }
  }

  for (i = 1; i <= sysseg->num_glocks; i++) {
    gptr = GLPtr(i);

    if ((gptr->hash != 0) && (gptr->owner == user_no)) {
      (GLPtr(gptr->hash)->count)--;
      gptr->hash = 0;
    }
  }

  if (!(sysseg->flags & SSF_NO_FILE_CLEANUP)) {
    for (i = 1; i <= sysseg->numfiles; i++) {
      ufm = UFMPtr(uptr, i);
      if (*ufm) {
        fptr = FPtr(i);
        fptr->ref_ct = abs(fptr->ref_ct) - *ufm;
      }
    }
  }

  ReleaseLicence(uptr);
}

/* END-CODE */
