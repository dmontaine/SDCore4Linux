/* CONFIG.H
 * Configuration data
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
 * START-HISTORY
 * 31 Dec 23 SD launch - prior history suppressed
 * rev 0.9.0 Jan 25 mab add create_user
 * 14 Sep 26 dm  S.18: api_login removed (APILOGIN retired).
 * 19 Oct 26 dm  netwait and netreply are 32 bit (verifier finding of the SDNet finish): a value in sd.conf is read into an int and a 16 bit field wrapped 65541 to 5 before rangecheck saw it.
 * 14 Nov 26 dm  S.242 stage 1: xfer, xferfile, xferslot, xferwait, xferidle, xfermax, xferkind - file transfer over the ssh login (delivered off).
 * 17 Nov 26 dm  S.62 (NETDIRS, the owner's decision of 17 Nov): netdirs, per process, MAX_NETDIRS_LEN 191 (what one sd.conf line holds after "NETDIRS=").
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

/* !!CONFIG!! All places requiring changes for config parameters are marked */

struct CONFIG {
 
  int16_t max_users;               /* User limit */
  char sysdir[MAX_PATHNAME_LEN+1];
  int16_t cmdstack;                /* CMDSTACK: Command stack depth */
  bool deadlock;                   /* DEADLOCK: 0 allow, 1 trap deadlocks, 2 trap and save the locks */
  u_int16_t debug;                 /* DEBUG:    Controls debug features */
  int errlog;                      /* ERRLOG:   Max errlog size in bytes, 0 if disabled */
  int16_t fds_limit;               /* FDS */
  int16_t lgnwait;                 /* LGNWAIT:  Tenths of a second a login waits for a spare user number */
  int16_t userpool;                /* USERPOOL: Highest user number to allocate; 0 = lowest free number first */
  int16_t usplit;                  /* USPLIT:   1 = interactive users take the lowest free user number, all other processes the highest (15 Oct 26) */
  int16_t cleanup;                 /* CLEANUP:  Seconds between scans for processes that ended abnormally, 30 to 3600, default 300 (16 Oct 26) */
  int16_t phantoms_base;           /* PHANTOMS: Lowest user number reserved for PHANTOM ... USER n, and... (16 Oct 26) */
  int16_t phantoms_range;          /*           ...how many are reserved; 0 = none */
  int16_t maxidlen;                /* MAXIDLEN: Maximum record id length */
  int16_t netfiles;                /* NETFILES:
                                      0x0001    Allow outgoing NFS
                                      0x0002    Allow incoming SDNet   */
  int16_t numfiles;                /* NUMFILES: Maximum number of files open */
  int16_t numlocks;                /* NUMLOCKS: Maximum number of record locks */
  int16_t pdump;                   /* PDUMP:    PDUMP mode flags */
  char startup[80+1];              /* STARTUP: Startup command */
 };


/* The most closed dynamic files DHCACHE may ask to be kept open (the cache is in op_dio1.c) */
#define MAX_DH_CACHE_SIZE 1024

/* Config parameters loaded per process to allow local changes */

#define MAX_SH_CMD_LEN 80
/* 17 Nov 26 dm - S.62, NETDIRS.  read_config() reads a line of at most 199 characters, so 191 is all "NETDIRS=" leaves; a longer value is refused
   by name (config.c), never cut: a cut list could end in a SHORTER directory, which would admit more than the administrator wrote. */
#define MAX_NETDIRS_LEN 191
struct PCFG  {
/* 27 Oct 26 dm - S.87: CODEPAGE, CREATUSR, EXCLREM, GDI, RINGWAIT, TXCHAR (and APILOGIN, FIXUSERS, JNLDIR, JNLMODE, PORTMAP in the shared part) are gone. */
  int16_t dhcache;                      /* DHCACHE:  Closed dynamic files kept open for quick reopening */
  char dumpdir[MAX_PATHNAME_LEN+1];     /* DUMPDIR:  Directory for process dump files */
  double fltdiff;                       /* FLTDIFF : Wide zero for float comparisons */
  int16_t fsync;                        /* FSYNC:    Controls when to do fsync() */
 /* 20240219 mab create-account based on type (user / group / other) */  
  char grpdir[MAX_PATHNAME_LEN+1];      /* GRPDIR:   Parent Directory for group accounts */
  int16_t grpsize;                      /* GRPSIZE:  Default group size (1-8) */
  int16_t intprec;                      /* INTPREC:  Precision for INT() etc */
  int16_t lptrhigh;                     /* LPTRHIGH: Default printer lines */
  int16_t lptrwide;                     /* LPTRWIDE: Default printer width */
  int maxcall;                          /* MAXCALL:  Maximum call depth */
  int32_t maxrlock;                     /* MAXRLOCK: Record locks one process may hold, 0 = no limit */
  bool must_lock;                       /* MUSTLOCK: Enforce locking rules */
  int16_t objects;                      /* OBJECTS:  Max loaded objects */
  int32_t objmem;                       /* OBJMEM:   Object size limit, zero = none */
  int32_t netwait;                      /* NETWAIT:  Seconds to wait for a connection to a remote SDNet server, 1 to 3600 (19 Oct 26, K8d).  32 bit, not 16: sd.conf is read into an int and a 16 bit field wrapped 65541 to 5 BEFORE the range test */
  int32_t netreply;                     /* NETREPLY: Seconds to wait for each reply of a remote SDNet server, 1 to 3600 (19 Oct 26, K8d; eight characters: CONFIG() reads no longer name).  32 bit for the same reason */
  /* 17 Nov 26 dm - S.62.  NETDIRS: directories outside its own account, separated by ";", that a session held to its account by the OS gate
     (os_path_ok_for_account(), op_sh.c) may still reach, to read and to write.  Delivered EMPTY, which confines it to its account.  PER PROCESS,
     NOT IN THE SHARED SEGMENT (W.11 F9: a member of sdusers can write the segment, and a list read from it would be a way to widen access):
     every session reads it from sd.conf itself, so an edit reaches the sessions started after it.  Not readable with CONFIG(). */
  char netdirs[MAX_NETDIRS_LEN+1];      /* NETDIRS:  Directories outside the account a gated session may reach */
  int16_t pwdelay;                      /* PWDELAY:  Seconds paused after a failed network login */
  int16_t sdclient_mode;                /* SDCLIENT: 0 = any, 1 = no open/exec, 2 = restricted call */
  int16_t reccache;                     /* RECCACHE: Record cache size */
  bool safedir;                         /* SAFEDIR:  Use careful update on dir file write */
  char sh[MAX_SH_CMD_LEN+1];            /* SH:       Command to run interactive shell */
  char sh1[MAX_SH_CMD_LEN+1];           /* SH1:      Command to run single shell */
  int32_t sortmem;                      /* SORTMEM: Limit on in-memory sort size */
  int16_t sortmrg;                      /* SORTMRG: Number of files in merge */
  char screentheme[32+1];               /* SCREENTHEME: the screen library's default theme (13 Oct 26) */
  char sortworkdir[MAX_PATHNAME_LEN+1]; /* SORTWORK */
  char spooler[MAX_PATHNAME_LEN+1];     /* SPOOLER: Non-default spooler */
  char tempdir[MAX_PATHNAME_LEN+1];     /* TEMPDIR */
  char terminfodir[MAX_PATHNAME_LEN+1]; /* TERMINFO */
  char timezone[64+1];                  /* TIMEZONE: the zone the epoch functions use, null = the process's own TZ (15 Oct 26) */
/* 20240219 mab create-account based on type (user / group / other) */  
  char usrdir[MAX_PATHNAME_LEN+1];      /* USRDIR:   Parent Directory for user accounts */
  /* 14 Nov 26 dm - S.242, file transfer over the ssh login (RECEIVE / SEND).  Per process: the transfer server reads sd.conf itself, as every
     session does, so nothing in the shared segment decides it.  XFER is the system-wide switch, delivered 0 (the register's ACC$XFER is the
     per-account one).  Sizes in kilobytes, times in seconds; the defaults are the owner's of 14 Nov ("10 MB file / 100 MB slot", "60 minutes"). */
  int16_t xfer;                         /* XFER:     0 = no file transfer on this system, 1 = accounts with xfer-on may transfer */
  int32_t xferfile;                     /* XFERFILE: largest file, kilobytes (10240) */
  int32_t xferslot;                     /* XFERSLOT: most bytes one slot takes, kilobytes (102400) */
  int32_t xferwait;                     /* XFERWAIT: seconds a slot waits for its first connection (600) */
  int32_t xferidle;                     /* XFERIDLE: seconds a slot stays open after its last file closes (120) */
  int32_t xfermax;                      /* XFERMAX:  seconds a slot may stay open at most, 0 = no ceiling (3600) */
  char xferkind[128+1];                 /* XFERKIND: extensions a file must have, comma separated; null = any plain-text file */
  int16_t yearbase;                     /* YEARBASE: Two digit year start */
 };

Public struct PCFG pcfg;

/* END-CODE */
