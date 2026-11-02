/* sd_jobmark.h
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
 * 02 Nov 26 dm  S.102 stage 3 - written.  Checked by gplbld/test-jobmark-units.py, which
 *               drives sd_job_name() on scratch files through gplbld/verify-jobmark.c.
 * END-HISTORY
 */

#ifndef SD_JOBMARK_H
#define SD_JOBMARK_H

#include <stddef.h>
#include <sys/types.h>

#define SD_JOB_CGROUP_FILE  "/proc/self/cgroup"
#define SD_JOB_DIR          "/etc/sdcore/jobs.d"
#define SD_JOB_NAME_MAX     32

/* 0, with the job's name in NAME, when ALL of these hold; -1 otherwise (and NAME is empty):
 *   - CGROUP_FILE is exactly one line "0::/system.slice/sdcore-job-<name>.service": systemd put this process into that unit's cgroup, and only root can
 *     (measured 2 Nov 26 on Debian 13: the sdsys user can neither write its pid into the unit's cgroup.procs nor start a system unit);
 *   - <name> is a job name (1 to 32 characters: a lower case letter, then lower case letters, digits and dashes, not ending in a dash);
 *   - JOBS_DIR and its parent are directories owned by OWNER and not writable by group or others, opened without following a link;
 *   - JOBS_DIR/<name> is a regular file with one link, owned by OWNER, not writable by group or others, opened without following a link;
 *   - its "name=" line is <name> and its "command=" line is exactly COMMAND (the session's own command line - the kernel passes the argv text).
 * OWNER is 0 in production; the check passes its own uid. */
int sd_job_name(const char *cgroup_file, const char *jobs_dir, const char *command, uid_t owner, char *name, size_t namesz);

/* The job this process was admitted as, for the audit trail (every line of the run ends " job=<name>"); empty when none. */
extern char sd_job_active[SD_JOB_NAME_MAX + 1];

#endif
