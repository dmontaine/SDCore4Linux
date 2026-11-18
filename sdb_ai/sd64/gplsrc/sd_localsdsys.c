/* sd_localsdsys.c
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
 * 18 Nov 26 dm  S.267 - written.  See sd_localsdsys.h for the rules and gplbld/test-localsdsys-units.py for the check.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * The owner, 17 and 18 Nov 2026: the administrator may reach SDSYS by ssh FROM THIS COMPUTER without logging out and in as sdsys, restricted to
 * the Linux users he lists, and the same for the API's Unix socket; both lists empty as delivered.  The way in is
 *
 *     ssh -t <listed user>@localhost sd-sdsys
 *
 * which sd (or ssh-forcecommand's refusal arm) hands to /usr/local/bin/sd-sdsys, which runs "sudo -n sd-elevate sdsys-session": the root helper
 * checks the facts below and starts sd as the sdsys user, and CPROC then asks this file the same questions (kernel(K$SDSYS.LOCAL)) and asks for
 * the SD password of sdsys before it grants anything.  Neither the helper nor the kernel is trusted alone.
 *
 * EVERY FACT IS THE OPERATING SYSTEM'S: the audit login uid (PAM sets it once at login, every descendant inherits it, only root can write it);
 * the cgroup (systemd-logind puts an ssh login's processes into user-<uid>.slice/session-<id>.scope, a cgroup only root can move a process into);
 * logind's root-written state file for that session (sshd as the PAM service, remote, from a literal loopback address); and the lists, root's
 * files in /etc/sdcore.  NOTHING HERE READS AN ENVIRONMENT VARIABLE OR AN ARGUMENT A BASIC PROGRAM CHOSE (sdsys_local_detect() reads two, and
 * only to decide whether to run the wrapper, which grants nothing).  Every doubt is a refusal.
 *
 * END-DESCRIPTION
 */

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <netinet/in.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "sd_localsdsys.h"

#define TEXT_MAX   8192
#define ST_OK      0
#define ST_ABSENT  1
#define ST_UNSAFE  2

const char *sd_local_why = "";

/* ^[a-z_][a-z0-9_-]{0,31}$ - the helper's valid_name(), the names it writes */
static int name_ok(const char *n)
{
    size_t len = strlen(n), i;

    if (len < 1 || len > SD_LOCAL_NAME_MAX) return 0;
    if (!((n[0] >= 'a' && n[0] <= 'z') || n[0] == '_')) return 0;
    for (i = 1; i < len; i++) {
        char c = n[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-')) return 0;
    }
    return 1;
}

/* A descriptor's own facts: of TYPE, owned by OWNER, not writable by group or others; a file also has one link and is under TEXT_MAX bytes. */
static int safe_fd(int fd, mode_t type, uid_t owner)
{
    struct stat st;

    if (fstat(fd, &st) != 0) return 0;
    if ((st.st_mode & S_IFMT) != type) return 0;
    if (st.st_uid != owner || (st.st_mode & 022) != 0) return 0;
    if (type == S_IFREG && (st.st_nlink != 1 || st.st_size >= TEXT_MAX)) return 0;
    return 1;
}

/* Opens PATH for reading when it, its directory and that directory's parent are all safe; the descriptor, or -1 with *STATE ST_ABSENT (the
 * directory or the file is not there) or ST_UNSAFE (anything else: a link, a wrong owner or mode, a second link, not a regular file). */
static int open_safe(const char *path, uid_t owner, int *state)
{
    char dir[512], parent[512];
    const char *base;
    char *slash;
    int pfd, dfd, fd;

    *state = ST_UNSAFE;
    if (path == NULL || path[0] != '/' || strlen(path) >= sizeof dir) return -1;
    strcpy(dir, path);
    slash = strrchr(dir, '/');
    if (slash == NULL || slash == dir || slash[1] == '\0') return -1;
    *slash = '\0';
    base = path + (slash - dir) + 1;
    strcpy(parent, dir);
    slash = strrchr(parent, '/');
    if (slash == NULL) return -1;
    if (slash == parent) slash[1] = '\0'; else *slash = '\0';

    pfd = open(parent, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (pfd < 0) return -1;
    if (!safe_fd(pfd, S_IFDIR, owner)) { close(pfd); return -1; }
    close(pfd);

    dfd = open(dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dfd < 0) {
        if (errno == ENOENT) *state = ST_ABSENT;
        return -1;
    }
    if (!safe_fd(dfd, S_IFDIR, owner)) { close(dfd); return -1; }

    fd = openat(dfd, base, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    close(dfd);
    if (fd < 0) {
        if (errno == ENOENT) *state = ST_ABSENT;
        return -1;
    }
    if (!safe_fd(fd, S_IFREG, owner)) { close(fd); return -1; }
    *state = ST_OK;
    return fd;
}

/* The whole text of FD (closed here) into BUF; -1 when it cannot be read, is too long or holds a NUL. */
static int read_text(int fd, char *buf, size_t size)
{
    size_t got = 0;
    ssize_t n;

    for (;;) {
        n = read(fd, buf + got, size - 1 - got);
        if (n < 0) { if (errno == EINTR) continue; close(fd); return -1; }
        if (n == 0) break;
        got += (size_t)n;
        if (got >= size - 1) { close(fd); return -1; }
    }
    close(fd);
    buf[got] = '\0';
    if (memchr(buf, '\0', got) != NULL) return -1;
    return (int)got;
}

/* A small /proc file that holds one decimal number (a newline after it allowed) into *V; -1 when it is anything else. */
static int read_number(const char *path, unsigned long *v)
{
    char buf[32], *end;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    ssize_t n;

    if (fd < 0) return -1;
    n = read(fd, buf, sizeof buf - 1);
    close(fd);
    if (n <= 0) return -1;
    buf[n] = '\0';
    if (buf[n - 1] == '\n') buf[--n] = '\0';
    if (n < 1 || n > 10) return -1;
    for (ssize_t i = 0; i < n; i++) if (buf[i] < '0' || buf[i] > '9') return -1;
    errno = 0;
    *v = strtoul(buf, &end, 10);
    if (errno != 0 || *end != '\0' || *v > 4294967295UL) return -1;
    return 0;
}

/* The list at PATH into NAMES; the number of names (0 to 32), or -1 with *WHY set.  An absent file is an empty list. */
static int read_list(const char *path, uid_t owner, char names[][SD_LOCAL_NAME_MAX + 1], const char **why)
{
    char text[TEXT_MAX];
    char *p, *e;
    int state, fd, count = 0;

    fd = open_safe(path, owner, &state);
    if (fd < 0) {
        if (state == ST_ABSENT) return 0;
        *why = "list-unsafe";
        return -1;
    }
    if (read_text(fd, text, sizeof text) < 0) { *why = "list-unsafe"; return -1; }
    p = text;
    while (*p) {
        e = strchr(p, '\n');
        if (e == NULL) e = p + strlen(p);
        if ((size_t)(e - p) > SD_LOCAL_NAME_MAX || count >= SD_LOCAL_MAX_NAMES) { *why = "list-unsafe"; return -1; }
        memcpy(names[count], p, (size_t)(e - p));
        names[count][e - p] = '\0';
        if (!name_ok(names[count])) { *why = "list-unsafe"; return -1; }
        count++;
        p = (*e == '\n') ? e + 1 : e;
    }
    return count;
}

static int on_list(char names[][SD_LOCAL_NAME_MAX + 1], int count, const char *name)
{
    int i;

    for (i = 0; i < count; i++) if (strcmp(names[i], name) == 0) return 1;
    return 0;
}

/* NAME is a user who may be listed: not root, not sdsys, uid 1000 or more, in GROUP.  Its uid into *UID. */
static int user_ok(const char *name, const char *group, uid_t *uid)
{
    struct passwd *pw;
    struct group *gr;
    gid_t want, base, *list;
    int n = 64, i, ok = 0;

    if (!name_ok(name) || strcmp(name, "root") == 0 || strcmp(name, "sdsys") == 0) return 0;
    if (group == NULL || group[0] == '\0') return 0;
    pw = getpwnam(name);
    if (pw == NULL || pw->pw_uid == 0 || pw->pw_uid < SD_LOCAL_UID_MIN) return 0;
    *uid = pw->pw_uid;
    base = pw->pw_gid;
    gr = getgrnam(group);
    if (gr == NULL) return 0;
    want = gr->gr_gid;
    for (;;) {
        int got = n;
        list = malloc((size_t)n * sizeof(gid_t));
        if (list == NULL) return 0;
        if (getgrouplist(name, base, list, &got) >= 0) {
            for (i = 0; i < got; i++) if (list[i] == want) ok = 1;
            free(list);
            return ok;
        }
        free(list);
        if (got <= n || got > 65536) return 0;
        n = got;
    }
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

/* A LITERAL loopback address: dotted IPv4 in 127.0.0.0/8, or the IPv6 loopback.  A host name - localhost too - is not one. */
static int loopback_literal(const char *h)
{
    struct in_addr a4;
    struct in6_addr a6;

    if (inet_pton(AF_INET, h, &a4) == 1) return (ntohl(a4.s_addr) >> 24) == 127;
    if (inet_pton(AF_INET6, h, &a6) == 1) return IN6_IS_ADDR_LOOPBACK(&a6);
    return 0;
}

int sd_local_ssh_user(const struct sd_local_facts *f, char *name, size_t namesz, const char **why)
{
    char names[SD_LOCAL_MAX_NAMES][SD_LOCAL_NAME_MAX + 1];
    char user[SD_LOCAL_NAME_MAX + 1], cg[512], want[512], id[40], text[TEXT_MAX], val[256], path[600], num[24];
    unsigned long lu, sid;
    struct passwd *pw;
    uid_t uid = 0;
    int count, fd, state;
    size_t len, plen, i;

    *why = "list-unsafe";
    if (name == NULL || namesz < SD_LOCAL_NAME_MAX + 1 || f == NULL) return -1;
    name[0] = '\0';

    /* the list first: an empty list always answers list-empty */
    count = read_list(f->list, f->owner, names, why);
    if (count < 0) return -1;
    if (count == 0) { *why = "list-empty"; return -1; }

    /* who logged in */
    if (read_number(f->loginuid, &lu) != 0 || lu == 4294967295UL) { *why = "no-login"; return -1; }
    pw = getpwuid((uid_t)lu);
    if (pw == NULL || strlen(pw->pw_name) > SD_LOCAL_NAME_MAX) { *why = "no-user"; return -1; }
    strcpy(user, pw->pw_name);
    if (!user_ok(user, f->group, &uid) || uid != (uid_t)lu) { *why = "not-sd-user"; return -1; }
    if (!on_list(names, count, user)) { *why = "not-listed"; return -1; }

    /* the login session this process is in: exactly one line, the session scope of that user */
    fd = open(f->cgroup, O_RDONLY | O_CLOEXEC);
    if (fd < 0) { *why = "no-session"; return -1; }
    {
        ssize_t n = read(fd, cg, sizeof cg - 1);
        close(fd);
        if (n <= 0) { *why = "no-session"; return -1; }
        cg[n] = '\0';
        len = (size_t)n;
    }
    if (cg[len - 1] != '\n' || strchr(cg, '\n') != cg + len - 1) { *why = "no-session"; return -1; }
    cg[--len] = '\0';
    snprintf(want, sizeof want, "0::/user.slice/user-%lu.slice/session-", lu);
    plen = strlen(want);
    if (len <= plen + 6 || strncmp(cg, want, plen) != 0 || strcmp(cg + len - 6, ".scope") != 0) { *why = "no-session"; return -1; }
    if (len - plen - 6 >= sizeof id || len - plen - 6 > 32) { *why = "no-session"; return -1; }
    memcpy(id, cg + plen, len - plen - 6);
    id[len - plen - 6] = '\0';
    for (i = 0; id[i]; i++) {
        if (!((id[i] >= 'a' && id[i] <= 'z') || (id[i] >= '0' && id[i] <= '9'))) { *why = "no-session"; return -1; }
    }

    /* logind's record of that session */
    if (snprintf(path, sizeof path, "%s/%s", f->sessions, id) >= (int)sizeof path) { *why = "no-session"; return -1; }
    fd = open_safe(path, f->owner, &state);
    if (fd < 0) { *why = (state == ST_ABSENT) ? "no-session" : "session-unsafe"; return -1; }
    if (read_text(fd, text, sizeof text) < 0) { *why = "session-unsafe"; return -1; }
    snprintf(num, sizeof num, "%lu", lu);
    if (!line_value(text, "UID", val, sizeof val) || strcmp(val, num) != 0) { *why = "other-user"; return -1; }
    snprintf(want, sizeof want, "session-%s.scope", id);
    if (!line_value(text, "SCOPE", val, sizeof val) || strcmp(val, want) != 0) { *why = "no-session"; return -1; }
    if (read_number(f->sessionid, &sid) != 0 || sid == 4294967295UL) { *why = "other-session"; return -1; }
    snprintf(num, sizeof num, "%lu", sid);
    if (!line_value(text, "AUDIT", val, sizeof val) || strcmp(val, num) != 0) { *why = "other-session"; return -1; }
    if (!line_value(text, "SERVICE", val, sizeof val) || strcmp(val, "sshd") != 0) { *why = "not-ssh"; return -1; }
    if (!line_value(text, "REMOTE", val, sizeof val) || strcmp(val, "1") != 0) { *why = "not-ssh"; return -1; }
    if (!line_value(text, "REMOTE_HOST", val, sizeof val) || !loopback_literal(val)) { *why = "not-local"; return -1; }

    strcpy(name, user);
    *why = "";
    return 0;
}

int sd_local_listed(const char *list, const char *user, const char *group, uid_t owner, const char **why)
{
    char names[SD_LOCAL_MAX_NAMES][SD_LOCAL_NAME_MAX + 1];
    uid_t uid = 0;
    int count;

    *why = "list-unsafe";
    count = read_list(list, owner, names, why);
    if (count < 0) return 0;
    if (count == 0) { *why = "list-empty"; return 0; }
    if (user == NULL || !user_ok(user, group, &uid)) { *why = "not-sd-user"; return 0; }
    if (!on_list(names, count, user)) { *why = "not-listed"; return 0; }
    *why = "";
    return 1;
}

void sdsys_local_detect(int argc)
{
    const char *cmd = getenv("SSH_ORIGINAL_COMMAND");
    const char *conn = getenv("SSH_CONNECTION");

    if ((argc != 1) || (cmd == NULL) || (conn == NULL) || (strcmp(cmd, SD_LOCAL_COMMAND) != 0)) return;
    if ((geteuid() != getuid()) || (getegid() != getgid())) return;
    execl(SD_LOCAL_WRAPPER, SD_LOCAL_COMMAND, (char *)NULL);
    fprintf(stderr, "sd: %s could not be started (%s)\n", SD_LOCAL_WRAPPER, strerror(errno));
    exit(1);
}
