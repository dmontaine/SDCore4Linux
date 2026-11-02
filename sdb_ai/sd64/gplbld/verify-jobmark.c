/* verify-jobmark.c - drives gplsrc/sd_jobmark.c's sd_job_name() for gplbld/test-jobmark-units.py (S.102 stage 3, 2 Nov 2026).
 *
 *   verify-jobmark CGROUP_FILE JOBS_DIR COMMAND
 *
 * Prints "job=<name>" and exits 0 when sd_job_name() answers a name, prints "job=" and exits 1 when it does not.  The owner it asks for is
 * this process's own uid (the kernel asks for root's: 0).  No other output.                                                              */
#include <stdio.h>
#include <unistd.h>

#include "sd_jobmark.h"

int main(int argc, char **argv)
{
    char name[SD_JOB_NAME_MAX + 1];

    if (argc != 4) {
        fprintf(stderr, "usage: verify-jobmark CGROUP_FILE JOBS_DIR COMMAND\n");
        return 2;
    }
    if (sd_job_name(argv[1], argv[2], argv[3], geteuid(), name, sizeof name) == 0) {
        printf("job=%s\n", name);
        return 0;
    }
    printf("job=\n");
    return 1;
}
