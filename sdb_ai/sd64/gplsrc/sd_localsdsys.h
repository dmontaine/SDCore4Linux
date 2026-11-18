/* sd_localsdsys.h
 * Is THIS process a listed user's ssh login from this computer, reaching SDSYS (S.267)?  And is a user on the local API list?
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
 * 18 Nov 26 dm  S.267 - written.  Checked by gplbld/test-localsdsys-units.py, which drives sd_local_ssh_user() and sd_local_listed()
 *               on scratch files through gplbld/verify-localsdsys.c.
 * END-HISTORY
 */

#ifndef SD_LOCALSDSYS_H
#define SD_LOCALSDSYS_H

#include <stddef.h>
#include <sys/types.h>

/* The production paths.  The kernel passes these and nothing else; only the verify program (a test) passes others. */
#define SD_LOCAL_SSH_LIST    "/etc/sdcore/sdsys-local-ssh"
#define SD_LOCAL_API_LIST    "/etc/sdcore/sdsys-local-api"
#define SD_LOCAL_LOGINUID    "/proc/self/loginuid"
#define SD_LOCAL_SESSIONID   "/proc/self/sessionid"
#define SD_LOCAL_CGROUP      "/proc/self/cgroup"
#define SD_LOCAL_SESSIONS    "/run/systemd/sessions"
#define SD_LOCAL_GROUP       "sdusers"
#define SD_LOCAL_WRAPPER     "/usr/local/bin/sd-sdsys"
#define SD_LOCAL_COMMAND     "sd-sdsys"
#define SD_LOCAL_NAME_MAX    32
#define SD_LOCAL_MAX_NAMES   32
#define SD_LOCAL_UID_MIN     1000

/* The facts sd_local_ssh_user() reads.  OWNER is the uid every file and directory must belong to: 0 in production; the check passes its own. */
struct sd_local_facts {
  const char *list;        /* the ssh list */
  const char *loginuid;    /* this process's audit login uid */
  const char *sessionid;   /* this process's audit session id */
  const char *cgroup;      /* this process's cgroup */
  const char *sessions;    /* logind's state directory */
  const char *group;       /* the group a listed user must be in */
  uid_t owner;
};

/* 0, with the Linux user's name in NAME, when ALL of these hold; -1 otherwise (NAME empty, *WHY a short lower-case reason word):
 *   - the list is safe (a regular file with one link, owned by OWNER, not writable by group or others, opened without following a link, in a
 *     directory and a parent of which the same is true) and holds 1 to 32 lines, each a name ^[a-z_][a-z0-9_-]{0,31}$  (list-empty, list-unsafe);
 *   - the audit login uid is set (no-login), belongs to a user (no-user) who is not root or sdsys, has a uid of 1000 or more and is in GROUP
 *     (not-sd-user), and whose name is on the list (not-listed);
 *   - the cgroup is exactly one line "0::/user.slice/user-<uid>.slice/session-<id>.scope" for that uid (no-session);
 *   - SESSIONS/<id> is safe as the list is (session-unsafe; absent: no-session), says UID= that uid (other-user), SCOPE=session-<id>.scope
 *     (no-session), AUDIT= this process's audit session id (other-session), SERVICE=sshd and REMOTE=1 (not-ssh), and REMOTE_HOST= a literal
 *     loopback address, 127.0.0.0/8 or ::1, never a host name (not-local).
 * The list is read FIRST, so that an empty list always answers list-empty (CPROC writes today's audit line then). */
int sd_local_ssh_user(const struct sd_local_facts *f, char *name, size_t namesz, const char **why);

/* 1 when USER is on the list LIST (held to the same rules) and is a user who is not root or sdsys, has a uid of 1000 or more and is in GROUP;
 * 0 otherwise, with *WHY set (list-empty, list-unsafe, not-sd-user, not-listed). */
int sd_local_listed(const char *list, const char *user, const char *group, uid_t owner, const char **why);

/* sd.c main(), after xfer_detect(): an ssh login whose forced command is sd and whose requested command is exactly "sd-sdsys" is handed to the
 * wrapper SD_LOCAL_WRAPPER (sudo -n sd-elevate sdsys-session), which decides.  Nothing is granted here. */
void sdsys_local_detect(int argc);

/* The reason word of the last answer of kernel(K$SDSYS.LOCAL, ...) in this process, for the audit line. */
extern const char *sd_local_why;

#endif
