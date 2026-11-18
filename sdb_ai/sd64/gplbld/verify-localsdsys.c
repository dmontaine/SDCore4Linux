/* verify-localsdsys.c - drives gplsrc/sd_localsdsys.c for gplbld/test-localsdsys-units.py (S.267, 18 Nov 2026).
 *
 *   verify-localsdsys ssh LIST LOGINUID SESSIONID CGROUP SESSIONS GROUP [OWNER]
 *   verify-localsdsys api LIST USER GROUP
 *
 * ssh: prints "user=<name> why=" and exits 0 when sd_local_ssh_user() answers a user, "user= why=<word>" and exits 1 when it does not.
 * api: prints "listed=1 why=" and exits 0, or "listed=0 why=<word>" and exits 1.
 * The owner every file must have is this process's own uid (the kernel asks for root's: 0), or OWNER when it is given (so that a test that is
 * not root can still show a file of the wrong owner refused).  The paths are this program's ARGUMENTS: the product reads only the fixed paths
 * of sd_localsdsys.h and no environment variable.  No other output.                                                                      */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "sd_localsdsys.h"

int main(int argc, char **argv)
{
    char name[SD_LOCAL_NAME_MAX + 1];
    const char *why = "";

    if ((argc == 8 || argc == 9) && strcmp(argv[1], "ssh") == 0) {
        struct sd_local_facts f;
        f.list = argv[2];
        f.loginuid = argv[3];
        f.sessionid = argv[4];
        f.cgroup = argv[5];
        f.sessions = argv[6];
        f.group = argv[7];
        f.owner = (argc == 9) ? (uid_t)strtoul(argv[8], NULL, 10) : geteuid();
        if (sd_local_ssh_user(&f, name, sizeof name, &why) == 0) {
            printf("user=%s why=\n", name);
            return 0;
        }
        printf("user= why=%s\n", why);
        return 1;
    }
    if (argc == 5 && strcmp(argv[1], "api") == 0) {
        if (sd_local_listed(argv[2], argv[3], argv[4], geteuid(), &why) == 1) {
            printf("listed=1 why=\n");
            return 0;
        }
        printf("listed=0 why=%s\n", why);
        return 1;
    }
    fprintf(stderr, "usage: verify-localsdsys ssh LIST LOGINUID SESSIONID CGROUP SESSIONS GROUP [OWNER] | api LIST USER GROUP\n");
    return 2;
}
