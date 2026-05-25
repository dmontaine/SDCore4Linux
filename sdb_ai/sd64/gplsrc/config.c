/* CONFIG.C
 * Configuration file processing
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
 * rev 0.9.0 Jan 25 mab add CREATUSR - allow create.account to create os user
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * Parses sd.conf.  Only the [SD] section is applied; other sections log a
 * warning.  Parameters (under [SD]) include:
 *   APILOGIN, CMDSTACK, CODEPAGE, CREATUSR, DEADLOCK, DEBUG (bit flags, |=),
 *   DUMPDIR, ERRLOG, EXCLREM, FDS, FILERULE (|=), FIXUSERS, FLTDIFF,
 *   FSYNC (|=), GDI, GRPDIR, GRPSIZE, INTPREC, JNLDIR, JNLMODE, LPTRHIGH,
 *   LPTRWIDE, MAXCALL, MAXIDLEN, MUSTLOCK, NETFILES (|=), NUMFILES,
 *   NUMLOCKS, NUMUSERS, OBJECTS, OBJMEM, PDUMP (|=), PORTMAP, RECCACHE,
 *   RINGWAIT, SAFEDIR, SDCLIENT (|=), SDSYS, SH, SH1, SORTMEM, SORTMRG,
 *   SORTWORK, SPOOLER, STARTUP, TEMPDIR, TERMINFO, TXCHAR, USRDIR, YEARBASE
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "config.h"
#include "revstamp.h"
#include <limits.h>
#include <time.h>

#define CONFIG_LINE_LEN (MAX_PATHNAME_LEN + 64)
#define CONFIG_SECTION_LEN 32
#define CONFIG_MAX_KB 1048576 /* max SORTMEM/OBJMEM/ERRLOG size in kb */

#define CONFIG_SET_STR(dest, src, param)                                     \
  do {                                                                       \
    if (!config_set_string((dest), sizeof(dest), (src), (param), errmsg))    \
      goto exit_read_config;                                                 \
  } while (0)

Private bool rangecheck(char* param, int value, int min_val, int max_val,
                        char* errmsg);
Private bool config_set_string(char* dest, size_t dest_size, const char* src,
                               const char* param, char* errmsg);
Private bool config_line_too_long(const char* rec, size_t rec_size);
Private bool config_kb_value(int kb, int32_t* bytes, const char* param,
                             char* errmsg);

/* ====================================================================== */

Private bool config_set_string(char* dest, size_t dest_size, const char* src,
                               const char* param, char* errmsg) {
  if (snprintf(dest, dest_size, "%s", src) >= (int)dest_size) {
    sprintf(errmsg, "Value too long for %s configuration parameter", param);
    return FALSE;
  }
  return TRUE;
}

Private bool config_line_too_long(const char* rec, size_t rec_size) {
  size_t len = strlen(rec);

  if (len == 0)
    return FALSE;
  if (strchr(rec, '\n') != NULL)
    return FALSE;
  if (len < rec_size - 1)
    return FALSE;
  return TRUE;
}

Private bool config_kb_value(int kb, int32_t* bytes, const char* param,
                             char* errmsg) {
  if (kb < 0 || kb > CONFIG_MAX_KB) {
    sprintf(errmsg, "Invalid %s value %d (kb limit %d)", param, kb,
            CONFIG_MAX_KB);
    return FALSE;
  }
  *bytes = (int32_t)kb * 1024L;
  return TRUE;
}

/* ====================================================================== */

struct CONFIG* read_config(char* errmsg) {
  FILE* fu = NULL;
  char path[MAX_PATHNAME_LEN + 1];
  char rec[CONFIG_LINE_LEN];
  char section[CONFIG_SECTION_LEN] = "";
  char* p;
  struct CONFIG* cfg;
  double flt;
  int n;
  bool status = FALSE;
  int n2;
  int n3;
  struct stat statbuf;

  cfg = (struct CONFIG*)k_alloc(1, sizeof(struct CONFIG));
  if (cfg == NULL) {
    sprintf(errmsg, "Unable to allocate CONFIG memory.");
    return NULL;
  }

  memset((char*)cfg, 0, sizeof(struct CONFIG));

  /* Set defaults for private configuration parameters */
  /* !!CONFIG!! */

  pcfg.codepage = 0;
  pcfg.create_user = 1;
  pcfg.dumpdir[0] = '\0';
  pcfg.exclrem = 0;
  pcfg.filerule = 0;
  pcfg.fltdiff = 0.0000000000291;
  pcfg.fsync = 0;
  pcfg.gdi = 0;
  snprintf(pcfg.grpdir, sizeof(pcfg.grpdir), "/home/sd/group_accounts");
  pcfg.grpsize = 1;
  pcfg.intprec = 13;
  pcfg.lptrhigh = 66;
  pcfg.lptrwide = 80;
  pcfg.maxcall = 10000;
  pcfg.must_lock = FALSE;
  pcfg.objects = 0;
  pcfg.objmem = 0;
  pcfg.sdclient_mode = 0;
  pcfg.api_login = 1;
  pcfg.reccache = 0;
  pcfg.ringwait = TRUE;
  pcfg.safedir = FALSE;
  pcfg.sh[0] = '\0';
  pcfg.sh1[0] = '\0';
  pcfg.sortmem = 1048576;
  pcfg.sortmrg = 4;
  pcfg.sortworkdir[0] = '\0';
  pcfg.tempdir[0] = '\0';
  pcfg.spooler[0] = '\0';
  pcfg.terminfodir[0] = '\0';
  pcfg.txchar = TRUE;
  snprintf(pcfg.usrdir, sizeof(pcfg.usrdir), "/home/sd/user_accounts");
  pcfg.yearbase = 1930;

  cfg->cmdstack = 99;
  cfg->numfiles = 80;
  cfg->numlocks = 100;
  cfg->maxidlen = 63;
  cfg->fds_limit = SHRT_MAX;
  cfg->max_users = 1;

  fu = fopen(config_path, "r");
  if (fu == NULL) {
    sprintf(errmsg, "%s not found.", config_path);
    goto exit_read_config;
  }

  while (fgets(rec, sizeof(rec), fu) != NULL) {
    if (config_line_too_long(rec, sizeof(rec))) {
      sprintf(errmsg, "Configuration line too long (max %d characters)",
              (int)sizeof(rec) - 2);
      goto exit_read_config;
    }

    if ((p = strchr(rec, '\n')) != NULL)
      *p = '\0';

    if ((rec[0] == '#') || (rec[0] == '\0'))
      continue;

    if (rec[0] == '[') {
      p = strchr(rec, ']');
      if (p != NULL)
        *p = '\0';
      if (snprintf(section, sizeof(section), "%s", rec + 1) >=
          (int)sizeof(section)) {
        sprintf(errmsg, "Section name too long");
        goto exit_read_config;
      }
      UpperCaseString(section);
      continue;
    }

    if (strcmp(section, "SD")) {
      if (section[0] == '\0')
        fprintf(stderr,
                "Warning: ignoring configuration line before [SD]: %s\n",
                rec);
      else
        fprintf(stderr,
                "Warning: ignoring configuration line in [%s]: %s\n", section,
                rec);
      continue;
    }

    if (sscanf(rec, "NUMUSERS=%d", &n) == 1)
      cfg->max_users = n;
    /* !!CONFIG!! */
    else if (sscanf(rec, "CMDSTACK=%d", &n) == 1)
      cfg->cmdstack = n;
    else if (sscanf(rec, "CODEPAGE=%d", &n) == 1)
      pcfg.codepage = n;
    else if (sscanf(rec, "CREATUSR=%d", &n) == 1)
      pcfg.create_user = (n != 0);
    else if (sscanf(rec, "DEADLOCK=%d", &n) == 1)
      cfg->deadlock = (n != 0);
    else if (sscanf(rec, "DEBUG=%d", &n) == 1) /* bit flags; repeated lines |= */
      cfg->debug |= n;
    else if (strncmp(rec, "DUMPDIR=", 8) == 0)
      CONFIG_SET_STR(pcfg.dumpdir, rec + 8, "DUMPDIR");
    else if (sscanf(rec, "ERRLOG=%d", &n) == 1) {
      if (!config_kb_value(n, (int32_t*)&cfg->errlog, "ERRLOG", errmsg))
        goto exit_read_config;
    } else if (sscanf(rec, "EXCLREM=%d", &n) == 1)
      pcfg.exclrem = (n != 0);
    else if (sscanf(rec, "FDS=%d", &n) == 1)
      cfg->fds_limit = n;
    else if (sscanf(rec, "FILERULE=%d", &n) == 1) /* |= accumulates flags */
      pcfg.filerule |= n;
    else if (sscanf(rec, "FIXUSERS=%d,%d", &n, &n2) == 2) {
      cfg->fixusers_base = n;
      cfg->fixusers_range = n2;
    } else if (sscanf(rec, "FLTDIFF=%lf", &flt) ==
               1) /* assumes '.' decimal separator */
      pcfg.fltdiff = flt;
    else if (sscanf(rec, "FSYNC=%d", &n) == 1) /* |= accumulates flags */
      pcfg.fsync |= n;
    else if (sscanf(rec, "GDI=%d", &n) == 1)
      pcfg.gdi = (n != 0);
    else if (sscanf(rec, "GRPSIZE=%d", &n) == 1)
      pcfg.grpsize = n;
    else if (strncmp(rec, "GRPDIR=", 7) == 0)
      CONFIG_SET_STR(pcfg.grpdir, rec + 7, "GRPDIR");
    else if (sscanf(rec, "INTPREC=%d", &n) == 1)
      pcfg.intprec = n;
    else if (strncmp(rec, "JNLDIR=", 7) == 0)
      CONFIG_SET_STR(cfg->jnldir, rec + 7, "JNLDIR");
    else if (sscanf(rec, "JNLMODE=%d", &n) == 1)
      cfg->jnlmode = n;
    else if (sscanf(rec, "LPTRHIGH=%d", &n) == 1)
      pcfg.lptrhigh = n;
    else if (sscanf(rec, "LPTRWIDE=%d", &n) == 1)
      pcfg.lptrwide = n;
    else if (sscanf(rec, "MAXCALL=%d", &n) == 1)
      pcfg.maxcall = n;
    else if (sscanf(rec, "MAXIDLEN=%d", &n) == 1)
      cfg->maxidlen = n;
    else if (sscanf(rec, "MUSTLOCK=%d", &n) == 1)
      pcfg.must_lock = n != 0;
    else if (sscanf(rec, "NETFILES=%d", &n) == 1) /* |= accumulates flags */
      cfg->netfiles |= n;
    else if (sscanf(rec, "NUMFILES=%d", &n) == 1)
      cfg->numfiles = n;
    else if (sscanf(rec, "NUMLOCKS=%d", &n) == 1)
      cfg->numlocks = n;
    else if (sscanf(rec, "OBJECTS=%d", &n) == 1)
      pcfg.objects = n;
    else if (sscanf(rec, "OBJMEM=%d", &n) == 1) {
      if (!config_kb_value(n, &pcfg.objmem, "OBJMEM", errmsg))
        goto exit_read_config;
    } else if (sscanf(rec, "PDUMP=%d", &n) == 1) /* |= accumulates flags */
      cfg->pdump |= n;
    else if (sscanf(rec, "PORTMAP=%d,%d,%d", &n, &n2, &n3) == 3) {
      cfg->portmap_base_port = n;
      cfg->portmap_base_user = n2;
      cfg->portmap_range = n3;
    } else if (sscanf(rec, "SDCLIENT=%d", &n) == 1) /* |= accumulates flags */
      pcfg.sdclient_mode |= n;
    else if (sscanf(rec, "APILOGIN=%d", &n) == 1)
      pcfg.api_login = n;
    else if (strncmp(rec, "SDSYS=", 6) == 0) {
      /* Flash mode keeps sysdir from shared segment; do not overwrite. */
      if (!(command_options & CMD_FLASH))
        CONFIG_SET_STR(cfg->sysdir, rec + 6, "SDSYS");
    } else if (sscanf(rec, "RECCACHE=%d", &n) == 1)
      pcfg.reccache = n;
    else if (sscanf(rec, "RINGWAIT=%d", &n) == 1)
      pcfg.ringwait = (n != 0);
    else if (sscanf(rec, "SAFEDIR=%d", &n) == 1)
      pcfg.safedir = (n != 0);
    else if (strncmp(rec, "SH=", 3) == 0)
      CONFIG_SET_STR(pcfg.sh, rec + 3, "SH");
    else if (strncmp(rec, "SH1=", 4) == 0)
      CONFIG_SET_STR(pcfg.sh1, rec + 4, "SH1");
    else if (sscanf(rec, "SORTMEM=%d", &n) == 1) {
      if (!config_kb_value(n, &pcfg.sortmem, "SORTMEM", errmsg))
        goto exit_read_config;
    } else if (sscanf(rec, "SORTMRG=%d", &n) == 1)
      pcfg.sortmrg = n;
    else if (strncmp(rec, "SORTWORK=", 9) == 0)
      CONFIG_SET_STR(pcfg.sortworkdir, rec + 9, "SORTWORK");
    else if (strncmp(rec, "SPOOLER=", 8) == 0)
      CONFIG_SET_STR(pcfg.spooler, rec + 8, "SPOOLER");
    else if (strncmp(rec, "STARTUP=", 8) == 0)
      CONFIG_SET_STR(cfg->startup, rec + 8, "STARTUP");
    else if (strncmp(rec, "TEMPDIR=", 8) == 0)
      CONFIG_SET_STR(pcfg.tempdir, rec + 8, "TEMPDIR");
    else if (strncmp(rec, "TERMINFO=", 9) == 0)
      CONFIG_SET_STR(pcfg.terminfodir, rec + 9, "TERMINFO");
    else if (sscanf(rec, "TXCHAR=%d", &n) == 1)
      pcfg.txchar = (n != 0);
    else if (strncmp(rec, "USRDIR=", 7) == 0)
      CONFIG_SET_STR(pcfg.usrdir, rec + 7, "USRDIR");
    else if (sscanf(rec, "YEARBASE=%d", &n) == 1)
      pcfg.yearbase = n;
    else {
      sprintf(errmsg, "Unrecognised configuration parameter '%s'", rec);
      goto exit_read_config;
    }
  }

  if (pcfg.tempdir[0] != '\0') {
    if ((stat(pcfg.tempdir, &statbuf) != 0) ||
        (!(statbuf.st_mode & S_IFDIR))) {
      pcfg.tempdir[0] = '\0';
    }
  }

  if (pcfg.tempdir[0] == '\0') {
    p = getenv("TMP");
    if (!config_set_string(pcfg.tempdir, sizeof(pcfg.tempdir),
                           (p == NULL) ? "/tmp" : p, "TEMPDIR", errmsg))
      goto exit_read_config;
  }

  if (pcfg.sortworkdir[0] != '\0') {
    if ((stat(pcfg.sortworkdir, &statbuf) != 0) ||
        (!(statbuf.st_mode & S_IFDIR))) {
      pcfg.sortworkdir[0] = '\0';
    }
  }

  if (pcfg.sortworkdir[0] == '\0') {
    if (!config_set_string(pcfg.sortworkdir, sizeof(pcfg.sortworkdir),
                           pcfg.tempdir, "SORTWORK", errmsg))
      goto exit_read_config;
  }

  if (cfg->sysdir[0] == '\0') {
    sprintf(errmsg, "No SDSYS parameter in configuration file.");
    goto exit_read_config;
  }

  if ((cfg->portmap_range) &&
      (cfg->portmap_base_user + cfg->portmap_range - 1 > MIN_HI_USER_NO)) {
    sprintf(errmsg, "PORTMAP user numbers extend beyond %d.", MIN_HI_USER_NO);
    goto exit_read_config;
  }

  if (cfg->fixusers_base) {
    if (cfg->fixusers_base + cfg->fixusers_range - 1 > MIN_HI_USER_NO) {
      sprintf(errmsg, "FIXUSERS user numbers extend beyond %d.", MIN_HI_USER_NO);
      goto exit_read_config;
    }

    if (cfg->portmap_range) {
      if (((cfg->portmap_base_user >= cfg->fixusers_base) &&
           (cfg->portmap_base_user <
            cfg->fixusers_base + cfg->fixusers_range)) ||
          ((cfg->fixusers_base >= cfg->portmap_base_user) &&
           (cfg->fixusers_base <
            cfg->portmap_base_user + cfg->portmap_range))) {
        sprintf(errmsg, "PORTMAP and FIXUSERS user numbers overlap.");
        goto exit_read_config;
      }
    }
  }

  if ((cfg->errlog != 0) && (cfg->errlog < 10240))
    cfg->errlog = 10240;

  if (!rangecheck("NUMUSERS", cfg->max_users, 1, MIN_HI_USER_NO, errmsg) ||
      !rangecheck("NUMFILES", cfg->numfiles, 1, 32767, errmsg) ||
      !rangecheck("NUMLOCKS", cfg->numlocks, 1, 32767, errmsg) ||
      !rangecheck("FDS", cfg->fds_limit, 1, SHRT_MAX, errmsg) ||
      !rangecheck("CMDSTACK", cfg->cmdstack, 1, 9999, errmsg) ||
      !rangecheck("YEARBASE", pcfg.yearbase, 1900, 2100, errmsg) ||
      !rangecheck("OBJECTS", pcfg.objects, 0, 32767, errmsg) ||
      !rangecheck("GRPSIZE", pcfg.grpsize, 1, MAX_GROUP_SIZE, errmsg) ||
      !rangecheck("INTPREC", pcfg.intprec, 0, 14, errmsg) ||
      !rangecheck("LPTRHIGH", pcfg.lptrhigh, 10, 32767, errmsg) ||
      !rangecheck("LPTRWIDE", pcfg.lptrwide, 10, 1000, errmsg) ||
      !rangecheck("MAXCALL", pcfg.maxcall, 10, 1000000, errmsg) ||
      !rangecheck("RECCACHE", pcfg.reccache, 0, 32, errmsg) ||
      !rangecheck("SORTMRG", pcfg.sortmrg, 2, 10, errmsg) ||
      !rangecheck("MAXIDLEN", cfg->maxidlen, 63, MAX_ID_LEN, errmsg)) {
    goto exit_read_config;
  }

  if (snprintf(path, MAX_PATHNAME_LEN + 1, "%s%cgcat%c$CPROC", cfg->sysdir, DS,
               DS) >= (MAX_PATHNAME_LEN + 1)) {
    sprintf(errmsg, "Overflowed path/filename length with: '%s%cgcat%c$CPROC'.",
            cfg->sysdir, DS, DS);
    goto exit_read_config;
  }
  if (access(path, 0)) {
    sprintf(errmsg, "Global catalogue missing or corrupt.");
    goto exit_read_config;
  }

  status = TRUE;

exit_read_config:
  if (fu != NULL)
    fclose(fu);

  if (status)
    return cfg;

  k_free(cfg);
  return NULL;
}

/* ======================================================================
   rangecheck()  -  Validate a critical configuration parameter           */

Private bool rangecheck(char* param, int value, int min_val, int max_val,
                        char* errmsg) {
  if ((value < min_val) || (value > max_val)) {
    sprintf(errmsg, "Invalid %s configuration parameter value %d (allowed %d-%d)",
            param, value, min_val, max_val);
    return FALSE;
  }

  return TRUE;
}

/* END-CODE */
