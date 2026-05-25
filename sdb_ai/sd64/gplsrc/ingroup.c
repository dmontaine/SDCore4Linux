/* INGROUP.C
 * Test whether user is in a named group.
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
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 * in_group()  -  Return non-zero if the effective user is a member of the
 * named Unix group (primary or supplementary).  Results are cached for the
 * lifetime of the process; group membership changes are not detected.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include <sys/types.h>
#include <stdlib.h>
#include <string.h>

#include <unistd.h>
#include <grp.h>

typedef struct GROUP_INFO GROUP_INFO;
struct GROUP_INFO {
  GROUP_INFO* next;
  int16_t member;
  char name[1]; /* Flexible trailing storage for group name + NUL */
};

static GROUP_INFO* gi_head = NULL;
static gid_t* groups = NULL;
static int num_groups = -1; /* -1 = not yet queried */

/* ====================================================================== */

static int load_supplementary_groups(void) {
  int n;

  if (num_groups >= 0)
    return 1;

  n = getgroups(0, NULL);
  if (n < 0) {
    num_groups = 0;
    return 0;
  }

  if (n == 0) {
    num_groups = 0;
    return 1;
  }

  groups = (gid_t*)malloc((size_t)n * sizeof(gid_t));
  if (groups == NULL) {
    num_groups = 0;
    return 0;
  }

  num_groups = getgroups(n, groups);
  if (num_groups < 0) {
    free(groups);
    groups = NULL;
    num_groups = 0;
    return 0;
  }

  return 1;
}

/* ====================================================================== */

static int supplementary_contains(gid_t group_id) {
  int i;

  if (!load_supplementary_groups())
    return 0;

  for (i = 0; i < num_groups; i++) {
    if (groups[i] == group_id)
      return 1;
  }

  return 0;
}

/* ====================================================================== */

static void cache_result(char* group_name, int16_t member) {
  GROUP_INFO* gi;
  size_t name_len;
  size_t alloc_size;

  name_len = strlen(group_name);
  alloc_size = sizeof(GROUP_INFO) + name_len;
  gi = (GROUP_INFO*)malloc(alloc_size);
  if (gi == NULL)
    return;

  memcpy(gi->name, group_name, name_len + 1);
  gi->member = member;
  gi->next = gi_head;
  gi_head = gi;
}

/* ====================================================================== */

int16_t in_group(char* group_name) {
  int16_t status = 0;
  GROUP_INFO* gi;
  struct group* grp;
  gid_t group_id;

  if (group_name == NULL || group_name[0] == '\0')
    return 0;

  /* Have we already identified membership of this group? */

  for (gi = gi_head; gi != NULL; gi = gi->next) {
    if (!strcmp(group_name, gi->name))
      return gi->member;
  }

  grp = getgrnam(group_name);
  if (grp != NULL) {
    group_id = grp->gr_gid;

    if (group_id == getegid()) {
      status = 1;
    } else if (supplementary_contains(group_id) != 0) {
      status = 1;
    }
  }

  cache_result(group_name, status);

  return status;
}

/* END-CODE */
