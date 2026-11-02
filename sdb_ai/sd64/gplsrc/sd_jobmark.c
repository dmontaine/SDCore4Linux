/* sd_jobmark.c
 * Is THIS process a scheduled administrator job of SD's, started by systemd from a root-owned definition (S.102 stage 3)?
 * Copyright (c) 2026 The SD Developers, All Rights Reserved
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
 * 02 Nov 26 dm  S.102 stage 3 - written.  See sd_jobmark.h for the rule and gplbld/test-jobmark-units.py for the check.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * A scheduled job of the administrator runs as the sdsys user with no login behind it (a systemd unit has no login uid), so CPROC's usual question - was
 * the LOGIN sdsys's own - has no answer for it.  What does answer is the kernel's cgroup: systemd puts the unit's processes into
 * /system.slice/sdcore-job-<name>.service, and nothing the sdsys user can do moves a process there.  The job's definition is a file only root writes
 * (sd-elevate job-set), and the command it names must be the very command this session was started with, so a process that inherited the cgroup (a
 * child the job started) cannot use it to run anything else.  NOTHING HERE TRUSTS AN ENVIRONMENT VARIABLE OR AN ARGUMENT A BASIC PROGRAM CHOSE.
 *
 * END-DESCRIPTION
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "sd_jobmark.h"

#define CG_PREFIX  "0::/system.slice/sdcore-job-"
#define CG_SUFFIX  ".service"
#define DEF_MAX    4096

char sd_job_active[SD_JOB_NAME_MAX + 1];

static int name_ok(const char *n)
{
    size_t len = strlen(n), i;

    if (len < 1 || len > SD_JOB_NAME_MAX) return 0;
    if (!(n[0] >= 'a' && n[0] <= 'z')) return 0;
    if (n[len - 1] == '-') return 0;
    for (i = 1; i < len; i++) {
        char c = n[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) return 0;
    }
    return 1;
}

/* A directory or file descriptor's own facts: of TYPE, owned by OWNER, not writable by group or others. */
static int safe_fd(int fd, mode_t type, uid_t owner)
{
    struct stat st;

    if (fstat(fd, &st) != 0) return 0;
    if ((st.st_mode & S_IFMT) != type) return 0;
    if (st.st_uid != owner || (st.st_mode & 022) != 0) return 0;
    if (type == S_IFREG && (st.st_nlink != 1 || st.st_size >= DEF_MAX)) return 0;
    return 1;
}

/* The value of the line "KEY=..." of TEXT, copied to OUT; 0 when there is none, it is too long, or the key appears twice. */
static int line_value(const char *text, const char *key, char *out, size_t outsz)
{
    size_t klen = strlen(key);
    const char *p = text, *e, *found = NULL;
    size_t vlen = 0;

    while (*p) {
        e = strchr(p, '\n');
        if (e == NULL) e = p + strlen(p);
        if ((size_t)(e - p) > klen && strncmp(p, key, klen) == 0 && p[klen] == '=') {
            if (found != NULL) return 0;
            found = p + klen + 1;
            vlen = (size_t)(e - found);
        }
        p = (*e == '\n') ? e + 1 : e;
    }
    if (found == NULL || vlen >= outsz) return 0;
    memcpy(out, found, vlen);
    out[vlen] = '\0';
    return 1;
}

int sd_job_name(const char *cgroup_file, const char *jobs_dir, const char *command, uid_t owner, char *name, size_t namesz)
{
    char cg[256], parent[512], def[DEF_MAX], val[DEF_MAX], cand[SD_JOB_NAME_MAX + 1];
    size_t plen = strlen(CG_PREFIX), slen = strlen(CG_SUFFIX), len;
    char *slash;
    ssize_t n;
    int fd, dfd, pfd;

    if (name == NULL || namesz < SD_JOB_NAME_MAX + 1) return -1;
    name[0] = '\0';
    if (command == NULL || command[0] == '\0') return -1;

    /* the cgroup: exactly one line, and it is a job unit's */
    fd = open(cgroup_file, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return -1;
    n = read(fd, cg, sizeof cg - 1);
    close(fd);
    if (n <= 0) return -1;
    cg[n] = '\0';
    len = (size_t)n;
    if (cg[len - 1] != '\n' || strchr(cg, '\n') != cg + len - 1) return -1;
    cg[--len] = '\0';
    if (len <= plen + slen || strncmp(cg, CG_PREFIX, plen) != 0 || strcmp(cg + len - slen, CG_SUFFIX) != 0) return -1;
    len -= plen + slen;
    if (len > SD_JOB_NAME_MAX) return -1;
    memcpy(cand, cg + plen, len);
    cand[len] = '\0';
    if (!name_ok(cand)) return -1;

    /* the directory of definitions, and the one above it, are root's and closed to others */
    if (strlen(jobs_dir) >= sizeof parent) return -1;
    strcpy(parent, jobs_dir);
    slash = strrchr(parent, '/');
    if (slash == NULL || slash == parent) return -1;
    *slash = '\0';
    pfd = open(parent, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (pfd < 0) return -1;
    if (!safe_fd(pfd, S_IFDIR, owner)) { close(pfd); return -1; }
    close(pfd);
    dfd = open(jobs_dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dfd < 0) return -1;
    if (!safe_fd(dfd, S_IFDIR, owner)) { close(dfd); return -1; }

    /* the definition: a plain root file, named as the unit, naming this very command */
    fd = openat(dfd, cand, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    close(dfd);
    if (fd < 0) return -1;
    if (!safe_fd(fd, S_IFREG, owner)) { close(fd); return -1; }
    n = read(fd, def, sizeof def - 1);
    close(fd);
    if (n <= 0) return -1;
    def[n] = '\0';
    if (memchr(def, '\0', (size_t)n) != NULL) return -1;
    if (!line_value(def, "name", val, sizeof val) || strcmp(val, cand) != 0) return -1;
    if (!line_value(def, "command", val, sizeof val) || strcmp(val, command) != 0) return -1;
    strcpy(name, cand);
    return 0;
}
