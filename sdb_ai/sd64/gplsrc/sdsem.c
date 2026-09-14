/* SDSEM.C
 * Semaphore functions.
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
 * rev 0.9.0 Jan 25 d-chou add IPC_NOWAIT and RelinquishTimeslice (sched_yield) to LockSemaphore
 * 14 Sep 26 dm  SEM_UNDO on lock and unlock, and release_owned_semaphores()
 *               for the fatal-signal path (W.0, owner's ruling of 14 Sep 26).
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include <sys/sem.h>
#include <sched.h>

/* ======================================================================
   get_semaphores()  -  Get inter-process semaphores                      */

bool get_semaphores(bool create, char* errmsg) {
/* Linux only - Create rather than attach to existing? */

  int16_t i;

  union semun {
    int val;                   /* Value for SETVAL */
    struct semid_ds* buf;      /* Buffer for IPC_STAT, IPC_SET */
    u_int16_t* array; /* Array for GETALL, SETALL */
    struct seminfo* __buf;     /* Buffer for IPC_INFO */
  } seminit;

  seminit.val = 1;

  if ((semid = semget(SD_SEM_KEY, 0, 0666)) != -1) {
    /* Semaphores already exist */

    if (!create)
      return TRUE;

    strcpy(errmsg, "SD is already started");
    return FALSE;
  }

  if (errno != ENOENT) {
    sprintf(errmsg, "Error %d getting semaphores", errno);
    return FALSE;
  }

  /* Semaphores do not already exist */

  if (!create) {
    strcpy(errmsg, "SD has not been started");
    return FALSE;
  }

  /* Create new semaphores */

  if ((semid = semget(SD_SEM_KEY, NUM_SEMAPHORES,
                      IPC_CREAT | IPC_EXCL | 0666)) != -1) {
    /* Initialise the semaphores */

    for (i = 0; i < NUM_SEMAPHORES; i++)
      semctl(semid, i, SETVAL, seminit);
  } else {
    sprintf(errmsg, "Error %d allocating semaphores", errno);
    return FALSE;
  }

  return TRUE;
}

/* ====================================================================== */

void delete_semaphores() {
  if ((semid = semget(SD_SEM_KEY, 0, 0666)) != -1) {
    semctl(semid, 0, IPC_RMID);
  }
}

/* ======================================================================
   Variants on StartExclusive and EndExclusive for use with no shared mem */

/* 14 Sep 26 dm - W.0, owner's ruling of 14 Sep 26: SEM_UNDO ON BOTH HALVES.
   A process that died holding a semaphore used to leave it taken, and every
   other SD process then spun in LockSemaphore for ever - the system-wide wedge
   of 11 Sep 26.  With SEM_UNDO the kernel gives a dead process's semaphore back.
   THE COST, ACCEPTED BY THE RULING: the next taker may find the shared structure
   that semaphore protects half-updated, where before it found nothing at all.
   BOTH operations carry the flag or the kernel's per-process adjustment would
   not return to zero, and the undo at exit would add a release nobody took -
   two holders at once.  That is also why nothing may lock in one process and
   unlock in another: measured 14 Sep, no semaphore is held across a fork
   (op_kernel.c ends its section before the phantom fork; bind_sysseg locks and
   unlocks SHORT_CODE in the one process). */
void LockSemaphore(int semno) {
// rev 0.9.0
  static struct sembuf sem_lock = {0, -1, IPC_NOWAIT | SEM_UNDO};
  sem_lock.sem_num = semno;
  while (semop(semid, &sem_lock, 1)) {
// rev 0.9.0     
  	RelinquishTimeslice;
  }
}

void UnlockSemaphore(int semno) {
  static struct sembuf sem_unlock = {0, 1, SEM_UNDO};
  sem_unlock.sem_num = semno;
  semop(semid, &sem_unlock, 1);
}

/* ====================================================================== */

void StartExclusive(int semno, int16_t where) {
  register SEMAPHORE_ENTRY* semptr;

  LockSemaphore(semno);
  semptr = (((SEMAPHORE_ENTRY*)(((char*)sysseg) + sysseg->semaphore_table)) +
            (semno));
  semptr->owner = process.user_no;
  semptr->where = where;
}

void EndExclusive(int semno) {
  register SEMAPHORE_ENTRY* semptr;

  semptr = (((SEMAPHORE_ENTRY*)(((char*)sysseg) + sysseg->semaphore_table)) +
            (semno));
  semptr->owner = 0;
  UnlockSemaphore(semno);
}

/* ======================================================================
   release_owned_semaphores()  -  Give back what this process holds, on a fault

   14 Sep 26 dm - W.0, owner's ruling of 14 Sep 26: the fatal-signal path
   releases the semaphores its own process holds, before anything else in the
   handler - log_message() takes ERRLOG_SEM, so a fault while holding it would
   otherwise wait on itself.  It sees only what StartExclusive recorded in the
   owner table; a fault between the lock and the owner being set, or the raw
   LockSemaphore(SHORT_CODE) in bind_sysseg, is left to SEM_UNDO at exit.  The
   two cover each other; neither alone covers kill -9.                       */

void release_owned_semaphores() {
  register SEMAPHORE_ENTRY* semptr;
  int i;

  if (sysseg == NULL)
    return;

  for (i = 0; i < NUM_SEMAPHORES; i++) {
    semptr = (((SEMAPHORE_ENTRY*)(((char*)sysseg) + sysseg->semaphore_table)) + i);
    if ((semptr->owner != 0) && (semptr->owner == process.user_no))
      EndExclusive(i);
  }
}

/* END-CODE */
