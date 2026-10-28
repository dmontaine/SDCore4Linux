/* SYSSEG.C
 * System shared segment management
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
 * 25 Oct 26 dm  Option A of the daemon's restart: start_sd(with_daemon).  The fork of sdlnxd is start_lnxd(), which "sd -start -nodaemon" leaves out because
 *               sd-lnxd.service starts (and restarts) it.  A child whose exec fails now ends (_exit(1)) instead of returning to the caller.
 * 24 Oct 26 dm  W.11 F9: a session takes pcfg and the system directory from the configuration file (session_trust()), not from the segment's template
 *               and sysdir; start_sd() asks sd_sysdir().  The segment still holds both, for display.
 * 24 Oct 26 dm  W.11 F1: the shared segment is made 0660 and given to the group sdusers (create_shared_segment()), not 0666.
 * 13 Sep 26 dm  The startup command runs in the sdsys account, its lower-case
 *               name (plan M: account names are lower case).
 * 11 Sep 26 dm  start_sd() rotates the audit trail, as the port's does
 *               (PORT_ADOPTION 13).
 * 10 Sep 26 dm  Parity audit: start_sd() reports a failed fork() instead of
 *               claiming SD started (the Windows port's fix; UPSTREAM_FIXES 3).
 * 08 Sep 26 "sd -stop" signalled unvalidated pids, so a stale entry with pid 0
 *           made kill(0, SIGTERM) terminate the caller's whole process group.
 * 31 Dec 23 SD launch - prior history suppressed
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include <signal.h>
#include <time.h>
#include <grp.h>
/* 20240126 mab add syslog */
#include <syslog.h>

#include "sd.h"
#include "locks.h"
#include "config.h"
#include "revstamp.h"

/* Special interfaces in sdsem.c for use before shared memory created */

void LockSemaphore(int semno);
void UnlockSemaphore(int semno);

#define SYSSEG_REVSTAMP \
  (((u_int32_t)MAJOR_REV << 16) | ((u_int32_t)MINOR_REV << 8) | BUILD)

#include <sys/ipc.h>
#include <sys/shm.h>

void dump_config(void);

Private bool create_shared_segment(int32_t bytes,
                                   struct CONFIG* cfg,
                                   char* errmsg);

Private bool session_trust(char* errmsg);

/* ====================================================================== */

bool bind_sysseg(bool create, char* errmsg) {
  /* 13Jan22 gwb A bit of refactoring.
   *         renamed "pcode_fu" to "pcode_fd"  It holds a file descriptor, 
   *         not whatever the hell "fu" is. :)
   */

  /* Linux only - Create rather than attach to existing? */

  bool status = FALSE;
  int32_t sharedMemSize;
  int32_t offset;
  int16_t num_glocks;
  struct CONFIG* cfg = NULL;
  int16_t max_users;
  int16_t rlock_entry_size;
  int16_t hi_user_no;
  int user_map_size;
  char path[MAX_PATHNAME_LEN + 1];
  int pcode_fd;
  struct stat statBuf;
  int pcode_len;
  int16_t user_entry_size;

  /* Get the semaphores. If this fails, return directly rather than jumping
    to the normal error exit as we do not need to release the semaphores.   */

  if (!get_semaphores(create, errmsg))
    return FALSE;

  /* 
   * Try to open existing shared segment.
   * Use SHORT_CODE semaphore to prevent two users trying to create the
   * shared segment at once.  We cannot use StartExclusive as this uses
   * the shared segment.                      
   */

  LockSemaphore(SHORT_CODE);

  if (attach_shared_memory()) {
    /* The shared memory is already initialised */

    UnlockSemaphore(SHORT_CODE);

    if (sysseg->revstamp != SYSSEG_REVSTAMP) {
      sprintf(errmsg, "Shared memory revstamp mismatch (%08X %08X)",
              sysseg->revstamp, SYSSEG_REVSTAMP);
      unbind_sysseg();
      goto exit_bind_sysseg;
    }

    if (create) {
      strcpy(errmsg, "SD is already started.");
      goto exit_bind_sysseg;
    }

    /* 24 Oct 26 dm - W.11 F9.  This process's configuration and system directory come from the configuration file, not from the template
       and the directory the starter left in the segment: any member of sdusers can write those.  A failure RETURNS: exit_bind_sysseg
       would run stop_sd(), which signals every process in the user table and removes the segment - a bad line in sd.conf must refuse a
       new session, not end everybody's. */

    if (!session_trust(errmsg)) {
      unbind_sysseg();
      sysseg = NULL;
      return FALSE;
    }
    status = TRUE;
    goto exit_bind_sysseg;
  }

  /* If we arrive here, the shared segment does not already exist.
    Create a new shared segment and populate it.                   */

  if (!create) {
    strcpy(errmsg, "SD has not been started.");
    goto exit_bind_sysseg;
  }

  /* Read the config file */

  if ((cfg = read_config(errmsg)) == NULL)
    goto exit_bind_sysseg;

  sd_sysdir_trust(cfg->sysdir); /* W.11 F9: the starter's own copy, for sd_sysdir() below and in start_sd() */

  max_users = cfg->max_users;

  num_glocks = max_users * 3; /* Worst case in split, src, tgt, grp 0 */

  sharedMemSize = sizeof(SYSSEG);
  sharedMemSize += cfg->numfiles * sizeof(struct FILE_ENTRY);

  rlock_entry_size = (offsetof(RLOCK_ENTRY, id) + MAX_ID_LEN + 3) & ~3;
  sharedMemSize += cfg->numlocks * rlock_entry_size;

  sharedMemSize += num_glocks * sizeof(struct GLOCK_ENTRY);

  sharedMemSize += NUM_SEMAPHORES * sizeof(SEMAPHORE_ENTRY);

  user_entry_size =
      sizeof(struct USER_ENTRY) + (cfg->numfiles * sizeof(int16_t));
  sharedMemSize += max_users * user_entry_size;

  /* Work out size of user map based on highest user number. Users are
    allocated user numbers in a cycle from 1 to hi_user_no. This upper
    limit has a minimum value of MIN_HI_USER_NO but must be expanded if
    the licence results in more than this number of simultaneous processes. */

  /* USERPOOL (openQM item 551): the highest user number is the greater of it and the
    number of processes the licence allows; the default MIN_HI_USER_NO is 1023.  Zero
    makes the bound the licence count and, in assign_user_no(), takes the lowest free
    number each time instead of cycling.                                              */
  hi_user_no = max(max_users, cfg->userpool);
  user_map_size = (hi_user_no + 1) * sizeof(int16_t);
  sharedMemSize += user_map_size;

  /* Find size of pcode */
  /* converted to snprintf() -gwb 22Feb20 */
  if (snprintf(path, MAX_PATHNAME_LEN + 1, "%s%cbin%cpcode", cfg->sysdir, DS, DS) >= (MAX_PATHNAME_LEN + 1)) {
    fprintf(stderr, "Overflowed file/pathname length in bind_sysseg())!\n");
    goto exit_bind_sysseg;
  }
  if (((pcode_fd = open(path, O_RDONLY | O_BINARY)) < 0) || fstat(pcode_fd, &statBuf)) {
    /* return an error message, not a number that has to be looked up! */
    sprintf(errmsg, "Cannot read pcode file - %s.", strerror(errno)); 
    goto exit_bind_sysseg;
  }

  pcode_len = statBuf.st_size;
  sharedMemSize += pcode_len;

  /* Make space for template pcfg structure */

  sharedMemSize += sizeof(struct PCFG);

  /* Create the shared segment */

  if (!create_shared_segment(sharedMemSize, cfg, errmsg)) {
    goto exit_bind_sysseg;
  }

  memset((char*)sysseg, '\0', sharedMemSize);

  sysseg->revstamp = SYSSEG_REVSTAMP;
  sysseg->shmem_size = sharedMemSize;
  sysseg->start_time = (int64_t)time(NULL);

  sysseg->flags |= SSF_SECURE; /* Secure until we know otherwise */
  sysseg->prtjob = 1;
  sysseg->next_txn_id = 1;

  /* Licence data */

  sysseg->max_users = max_users; /* Total, all process types */

  /* Copy global configuration parameters to sysseg */

  /* !!CONFIG!! */
  sysseg->cmdstack = cfg->cmdstack;                   /* CMDSTACK */
  sysseg->deadlock = cfg->deadlock;                   /* DEADLOCK */
  sysseg->errlog = cfg->errlog;                       /* ERRLOG */
  sysseg->fds_limit = cfg->fds_limit;                 /* FDS */
  sysseg->maxidlen = cfg->maxidlen;                   /* MAXIDLEN */
  sysseg->netfiles = cfg->netfiles;                   /* NETFILES */
  sysseg->pdump = cfg->pdump;                         /* PDUMP */
  strcpy((char*)(sysseg->sysdir), cfg->sysdir);       /* SDSYS */
  strcpy((char*)(sysseg->startup), cfg->startup);     /* STARTUP */
  sysseg->userpool = cfg->userpool;                   /* USERPOOL */
  sysseg->usplit = cfg->usplit;                       /* USPLIT */
  sysseg->cleanup = cfg->cleanup;                     /* CLEANUP */
  sysseg->phantoms_base = cfg->phantoms_base;         /* PHANTOMS */
  sysseg->phantoms_range = cfg->phantoms_range;
  sysseg->lgnwait = cfg->lgnwait;                     /* LGNWAIT */

  /* Create dynamically sized parts of segment */

  offset = sizeof(SYSSEG);
  sysseg->numfiles = cfg->numfiles;
  sysseg->file_table = offset;
  offset += (cfg->numfiles * sizeof(struct FILE_ENTRY));

  sysseg->numlocks = cfg->numlocks;
  sysseg->rlock_table = offset;
  sysseg->rlock_entry_size = rlock_entry_size;
  offset += (cfg->numlocks * rlock_entry_size);

  sysseg->num_glocks = num_glocks;
  sysseg->glock_table = offset;
  offset += (num_glocks * sizeof(struct GLOCK_ENTRY));

  sysseg->semaphore_table = offset;
  offset += NUM_SEMAPHORES * sizeof(SEMAPHORE_ENTRY);

  sysseg->user_table = offset;
  sysseg->user_entry_size = user_entry_size;
  offset += max_users * user_entry_size;

  sysseg->hi_user_no = hi_user_no;
  sysseg->user_map = offset;
  offset += user_map_size;

  /* Load pcode */

  sysseg->pcode_offset = offset;
  sysseg->pcode_len = pcode_len;

  if (read(pcode_fd, ((char*)sysseg) + offset, pcode_len) != pcode_len) {
    sprintf(errmsg, "Unable to load pcode [%d].\n", errno);
    goto exit_bind_sysseg;
  }

  close(pcode_fd);
  offset += pcode_len;

  /* Copy our pcfg to become the template for new processes */

  sysseg->pcfg_offset = offset;
  memcpy(((char*)sysseg) + offset, &pcfg, sizeof(struct PCFG));
  offset += sizeof(struct PCFG);

  UnlockSemaphore(SHORT_CODE);

  /* Reset file stats timer. This must be done after creating the dynamic
    tables as sdtime() may reference user table. Furthermore, because
    sdtime() may end up calling raise_event(), which requires the short
    code semaphore, we need to be very sinful and do this operation after
    releasing the semaphore that we already hold. Given that we are
    creating the shared memory, the risk of collision is extremely low
    and the effect would be unimportant anyway.                          */

  sysseg->global_stats.reset = sdtime();

  status = TRUE;

  if (cfg != NULL)
    k_free(cfg);

exit_bind_sysseg:

  if (!status)
    stop_sd();

  return status;
}

/* ======================================================================
   create_shared_segment()                                                */

Private bool create_shared_segment(int32_t bytes,
                                   struct CONFIG* cfg,
                                   char* errmsg) {
  int shmid;
  struct shmid_ds shm_ds;
  struct group* sd_gr;

  /* 24 Oct 26 dm - W.11 F1 (security-model evaluation): 0660 and the group sdusers, not 0666.  With 0666 every local user could attach and
     change the tables every SD process, the root daemon included, trusts.  A machine with no group sdusers keeps the creator's group
     (more restrictive, never wider). */
  if ((shmid = shmget(SD_SHM_KEY, bytes, IPC_CREAT | 0660)) == -1) {
    sprintf(errmsg, "Error %d creating shared segment.", errno);
    return FALSE;
  }

  if (shmctl(shmid, IPC_STAT, &shm_ds) == 0) {
    if ((sd_gr = getgrnam("sdusers")) != NULL)
      shm_ds.shm_perm.gid = sd_gr->gr_gid;
    shm_ds.shm_perm.mode = (shm_ds.shm_perm.mode & ~0777) | 0660;
    (void)shmctl(shmid, IPC_SET, &shm_ds);
  }

  if ((sysseg = (SYSSEG*)shmat(shmid, NULL, 0)) == (void*)(-1)) {
    sprintf(errmsg, "Error %d attaching to new shared segment.", errno);
    return FALSE;
  }

  return TRUE;
}

/* ======================================================================
   session_trust()  -  W.11 F9: a session's configuration and system directory

   The process configuration (pcfg: SH, SPOOLER, USRDIR, GRPDIR, DUMPDIR, TEMPDIR ...) and the system directory used to be copied from what the starter
   left in the segment.  A member of sdusers with a shell can write that, and the next session of anybody, SDSYS included, would have run his shell
   command or loaded his global catalogue.  So a session reads the configuration file itself, with the same function the starter used (read_config()
   fills pcfg), and keeps ITS system directory.  The segment's copy stays for display and is compared once: a difference is the segment having been
   written, or this process having been pointed at another configuration, and goes to syslog; the file wins either way.

   Behaviour this changes: sd.conf is read by every new session, so an edit of a path or a command (SH=, SPOOLER=, USRDIR= ...) reaches a session
   started after it without a restart (the counters in the segment still need one), and a bad line in sd.conf refuses a new session with the message the
   starter gives, until it is repaired.  A refusal returns to the caller with the segment detached; it does not touch the running SD.         */

Private bool session_trust(char* errmsg) {
  struct CONFIG* c;
  char cfgerr[400 + 1];

  cfgerr[0] = '\0';
  memset(&pcfg, 0, sizeof(pcfg)); /* the template used to replace every byte of it */
  if ((c = read_config(cfgerr)) == NULL) {
    snprintf(errmsg, 80 + 1, "%.80s", cfgerr);
    return FALSE;
  }
  sd_sysdir_trust(c->sysdir);
  if (strcmp((const char *)(sysseg->sysdir), c->sysdir) != 0)
    syslog(LOG_WARNING, "sd: the shared segment's system directory differs from the configuration file's (%s); the configuration file is used", c->sysdir);
  k_free(c);
  return TRUE;
}

/* ======================================================================
   Attach to shared memory segment                                        */

bool attach_shared_memory() {
  int shmid;

  if ((shmid = shmget(SD_SHM_KEY, 0, 0666)) != -1) {
    if ((sysseg = (SYSSEG*)shmat(shmid, NULL, 0)) == (void*)(-1)) {
      fprintf(stderr, "Error %d attaching to shared segment.\n", errno);
      return FALSE;
    }
    return TRUE;
  }

  return FALSE;
}

/* ====================================================================== */

void unbind_sysseg() {
  shmdt((void*)sysseg);
}

/* ======================================================================
   start_lnxd()  -  Start the sdlnxd daemon as a child of this process

   25 Oct 26 dm - taken out of start_sd() so that "sd -start -nodaemon" can leave it out: under systemd the daemon is its own unit (sd-lnxd.service), which
   restarts it if it dies, and a second one forked here would be a second daemon.  The code is what start_sd() had, with one change: a child whose exec fails ENDS.
   It used to fall out of the if and return TRUE, so "sd -start" printed its success line twice and the child went on as if it were the caller.
   False only when fork() failed.                                                */

Private bool start_lnxd(void) {
  int cpid;
  int i;
  char path[MAX_PATHNAME_LEN + 1];

  cpid = fork();

  /* 10 Sep 26 dm - Parity audit: A FAILED fork() USED TO LOOK LIKE SUCCESS, the
     Windows port's fix (its sysseg.c, 16 Aug 2026; UPSTREAM_FIXES 3).  fork()
     returns -1, which is not 0, so it fell into the parent branch: sdlnxd was
     never started, nothing said so, and "sd -start" reported that SD had
     started - with the segment and semaphores bind_sysseg() had just made left
     behind to break every later session.  The segment is deliberately not torn
     down here; clearing it is sd -stop's job, and the message says so. */
  if (cpid < 0) {
    fprintf(stderr, "Cannot start sdlnxd - fork() failed: %s\n", strerror(errno));
    fprintf(stderr, "Run sd -stop to clear what this left behind.\n");
    return FALSE;
  }

  if (cpid == 0) { /* Child process */
    for (i = 3; i < 1024; i++)
      close(i);
    daemon(1, 1);
    /* converted to snprintf() -gwb 22Feb20 */
    if (snprintf(path, MAX_PATHNAME_LEN + 1, "%s/bin/sdlnxd", sd_sysdir()) >=
        (MAX_PATHNAME_LEN + 1)) {
      fprintf(stderr, "Overflowed file/pathname length in start_sd()!\n");
      _exit(1);
    }
    execl(path, path, NULL);
    _exit(1); /* the exec failed: this child must not go on as if it were sd */
  }

  /* Moved to sdlnxd:   sysseg->sdlnxd_pid = cpid;   -ve if it failed to start */
  return TRUE;
}

/* ======================================================================
   start_sd()  -  with_daemon FALSE is "sd -start -nodaemon": everything but
   the fork of sdlnxd, which the service unit sd-lnxd.service does instead.  */

bool start_sd(bool with_daemon) {
  char errmsg[80 + 1];
  int cpid;
  int i;
  char path[MAX_PATHNAME_LEN + 1];

  if (!bind_sysseg(TRUE, errmsg)) {
    fprintf(stderr, "%s\n", errmsg);
    return FALSE;
  }

  /* 11 Sep 26 dm - PORT_ADOPTION 13, as the port's start_sd().  Here because
     this is the one moment that is both root (the service runs sd -start) and
     has no session running: only root can lift the trail's append-only
     attribute to rename it, and rotating while somebody appends is the other
     thing to avoid.  After bind_sysseg(), which makes sysseg->sysdir readable. */

  audit_rotate();

  /* Start sdlnxd dameon */

  sysseg->sdlnxd_pid = -1; /* Stays -ve if fails to start */
  if (with_daemon && !start_lnxd())
    return FALSE;

  /* Run startup command, if defined */

  if (sysseg->startup[0] != '\0') {
    cpid = fork();
    if (cpid == 0) { /* Child process */
      for (i = 3; i < 1024; i++)
        close(i);
      daemon(1, 1);
      /* converted to snprintf() -gwb 22Feb20 */
      if (snprintf(path, MAX_PATHNAME_LEN + 1, "%s/bin/sd", sd_sysdir()) >=
          (MAX_PATHNAME_LEN + 1)) {
        fprintf(stderr, "Overflowed file/pathname length in start_sd()!\n");
        _exit(1);
      } else {
        /* 12 Oct 26 dm - openQM item 91: @TTY in a process started by STARTUP is "startup".  Login
           (kernel.c) sees this variable, uses it once and removes it, so nothing the startup process
           runs inherits it; a phantom it starts is "phantom" as before. */
        setenv("SD_STARTUP", "1", 1);
        execl(path, path, "-asdsys", sysseg->startup, NULL);
        _exit(1);
      }
    }
  }

  return TRUE;
}

/* ======================================================================
   stop_sd()                                                              */

bool stop_sd() {
  int shmid;
  struct shmid_ds shm;
  int16_t i;
  USER_ENTRY* uptr;

  if ((shmid = shmget(SD_SHM_KEY, 0, 0666)) != -1) {
    if (shmctl(shmid, IPC_STAT, &shm)) {
 /* 20240126 mab add syslog */
      syslog (LOG_INFO, "Error %d getting shm status, id :%d", errno, shmid);
      fprintf(stderr, "Error %d getting shm status\n", errno);
      return FALSE;
    }

    if (shm.shm_nattch) {
      if ((sysseg = (SYSSEG*)shmat(shmid, NULL, 0)) != (void*)(-1)) {
        /* Send all SD processes the SIGTERM signal */

        /* 08 Sep 26  The pid was not validated before being signalled.  A stale
           user table entry whose uid is set but whose pid is 0 turned this into
           kill(0, SIGTERM), which POSIX defines as "every process in my process
           group" -- so "sd -stop" run from a script or a terminal could
           terminate the script, the shell, and anything else running alongside
           it, reporting nothing.  A negative pid addresses a process group in
           the same way.  Signal only a real process id.  */
        for (i = 1; i <= sysseg->max_users; i++) {
          uptr = UPtr(i);
          if (uptr->uid && (uptr->pid > 0)) {
            kill(uptr->pid, SIGTERM);
          }
        }

        /* Shutdown the sdlnxd daemon if it is running */

        if (sysseg->sdlnxd_pid > 0)
          kill(sysseg->sdlnxd_pid, SIGTERM);

        /* Dettach the shared memory */

        shmdt((void*)sysseg);
        sysseg = NULL;
      }

      for (i = 10; i; i--) {
        if (shmctl(shmid, IPC_STAT, &shm))
          break; /* Error getting data */
        if (shm.shm_nattch == 0)
          break; /* Everyone has gone */
        sleep(1);
      }
    }
  }

  if (shmid != -1) {
    if (shmctl(shmid, IPC_RMID, &shm)) {
/* 20240126 mab add syslog */      
      syslog (LOG_INFO, "Error %d deleting shared memory, id :%d", errno, shmid);
      fprintf(stderr, "Error %d deleting shared memory\n", errno);
      return FALSE;
    }
  }

  delete_semaphores();

  return TRUE;
}

/* END-CODE */
