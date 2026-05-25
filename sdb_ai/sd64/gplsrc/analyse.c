/* ANALYSE.C
 * Analyze DH and directory files
 * Copyright (c) 2006 Ladybridge Systems, All Rights Reserved
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
 *
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#ifndef ANALYSE_UNIT_TEST
#include "dh_int.h"
#endif
#include <stdint.h>
#include <inttypes.h>

#ifdef ANALYSE_UNIT_TEST
#undef Private
#undef FPtr
#define Private
extern FILE_ENTRY* analyse_ut_fentry(void);
#define FPtr(n) (analyse_ut_fentry())
#endif

/* Worst case: 31 comma-separated fields (29x int32, 2x int64). */
#define ANALYSE_DH_RESULT_SIZE 512
#define ANALYSE_DIR_RESULT_SIZE 128

#define DIR_WALK_OK 1
#define DIR_WALK_ERROR 0
#define DIR_WALK_INTERRUPT (-1)

typedef struct {
  int32_t record_count;
  int64 total_bytes;
  int64 smallest;
  int64 largest;
} DIR_WALK_STATS;

Private bool dh_analyse(DH_FILE* dh_file, char* result, size_t result_size);
Private bool dir_analyse(FILE_VAR* fvar, char* result, size_t result_size);
Private int dir_walk_regular_files(FILE_ENTRY* fptr, DIR_WALK_STATS* stats,
                                     const char* caller);

/* ====================================================================== */

#ifndef ANALYSE_UNIT_TEST

void op_analyse() {
  DESCRIPTOR* descr;
  FILE_VAR* fvar;
  char result[ANALYSE_DH_RESULT_SIZE];

  descr = e_stack - 1;
  k_get_file(descr);
  fvar = descr->data.fvar;
  k_dismiss();

  switch (fvar->type) {
    case DYNAMIC_FILE:
      if (!dh_analyse(fvar->access.dh.dh_file, result, sizeof(result)))
        result[0] = '\0';
      break;

    case DIRECTORY_FILE:
      if (!dir_analyse(fvar, result, sizeof(result)))
        result[0] = '\0';
      break;

    default:
      k_error("Illegal file type for ANALYSE");
  }

  k_put_c_string(result, e_stack++);
}

#endif /* !ANALYSE_UNIT_TEST */

/* ====================================================================== */

#ifndef ANALYSE_UNIT_TEST

Private bool dh_analyse(DH_FILE* dh_file, /* File descriptor */
                        char* result,     /* Result string */
                        size_t result_size) {
  bool status = FALSE;
  int32_t group;
  int16_t group_bytes;
  DH_BLOCK* buff;
  DH_RECORD* rec_ptr;
  DH_BIG_BLOCK big_buff;
  int32_t grp;
  FILE_ENTRY* fptr;
  int16_t subfile;
  int16_t lock_slot = 0;
  int16_t rec_offset;
  int16_t used_bytes;
  int16_t rec_bytes;
  int32_t record_len;
  int32_t recs_in_group;   /* Records in group being processed */
  int32_t blocks_in_group; /* Blocks in group being processed */
  int32_t used_bytes_in_group;
  int32_t non_numeric_ids = 0;

  /* Group statistics */
  int32_t empty_groups = 0;            /* Groups with no records */
  int32_t overflowed_groups = 0;       /* Single overflow block */
  int32_t badly_overflowed_groups = 0; /* Multiple overflow blocks */
  int32_t smallest_group = INT32_MAX;  /* Blocks in smallest group */
  int32_t largest_group = 0;           /* Blocks in largest group */
  int32_t total_blocks = 0;            /* Total blocks in all groups */

  /* Per group statistics */
  int32_t min_recs_per_group = INT32_MAX;  /* Minimum records per group */
  int32_t max_recs_per_group = 0;          /* Maximum records per group */
  int32_t min_bytes_per_group = INT32_MAX; /* Min used bytes per group */
  int32_t max_bytes_per_group = 0;         /* Max used bytes per group */

  /* Record statistics for normal records */
  int32_t record_count = 0;            /* Number of records */
  int32_t smallest_record = INT32_MAX; /* Smallest record size */
  int32_t largest_record = 0;          /* Largest record size */
  int64 total_record_bytes = 0;        /* Total used space */

  /* Record statistics for large records */
  int32_t large_record_count = 0;          /* Number of records */
  int32_t smallest_lrg_record = INT32_MAX; /* Smallest record size */
  int32_t largest_lrg_record = 0;          /* Largest record size */
  int64 total_lrg_record_bytes = 0;        /* Total used space */

  /* Record length statistics */
  int32_t histogram[11] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
  /* 16 bytes - 8k bytes, over 8k */

  int16_t i;
  int32_t n;
  char* p;
  int nwritten;

  dh_err = 0;
  process.os_error = 0;

  buff = (DH_BLOCK*)(&dh_buffer);

  fptr = FPtr(dh_file->file_id);
  while (fptr->file_lock < 0)
    Sleep(1000); /* Clearfile in progress */

  /* Hold off splits/merges for the whole scan (see inhibit_count in dh_split). */

  StartExclusive(FILE_TABLE_LOCK, 1);
  fptr->inhibit_count++;
  EndExclusive(FILE_TABLE_LOCK);

  group_bytes = (int16_t)(dh_file->group_size);
  for (group = 1; group <= fptr->params.modulus; group++) {
    if (my_uptr->events)
      process_events();

    if (k_exit_cause & K_INTERRUPT) /* User interrupt or logout*/
    {
      goto exit_dh_analyse;
    }

    /* Lock group */

    lock_slot = GetGroupReadLock(dh_file, group);

    /* Process this group */

    subfile = PRIMARY_SUBFILE;
    grp = group;

    recs_in_group = 0;
    blocks_in_group = 0;
    used_bytes_in_group = 0;

    do {
      blocks_in_group++;

      /* Read group */

      if (!dh_read_group(dh_file, subfile, grp, (char*)buff, group_bytes)) {
        goto exit_dh_analyse;
      }

      /* Scan group */

      used_bytes = buff->used_bytes;
      if ((used_bytes == 0) || (used_bytes > group_bytes)) {
        log_printf(
            "DH_ANALYSE: Invalid byte count (x%04X) in subfile %d, group %d\n"
            "of file %s\n",
            used_bytes, (int)subfile, grp, fptr->pathname);
        dh_err = DHE_POINTER_ERROR;
        goto exit_dh_analyse;
      }

      used_bytes_in_group += used_bytes;

      rec_offset = offsetof(DH_BLOCK, record);
      while (rec_offset < used_bytes) {
        rec_ptr = (DH_RECORD*)(((char*)buff) + rec_offset);
        rec_bytes = rec_ptr->next;

        if ((rec_bytes < RECORD_HEADER_SIZE) ||
            (rec_offset + rec_bytes > used_bytes) ||
            (rec_offset + rec_bytes <= rec_offset)) {
          log_printf(
              "DH_ANALYSE: Invalid record size (%d) at offset %d in subfile "
              "%d, group %d\nof file %s\n",
              rec_bytes, rec_offset, (int)subfile, grp, fptr->pathname);
          dh_err = DHE_POINTER_ERROR;
          goto exit_dh_analyse;
        }

        recs_in_group++;

        for (i = 0, p = rec_ptr->id; i < rec_ptr->id_len; i++, p++) {
          if (!IsDigit(*p)) {
            non_numeric_ids++;
            break;
          }
        }

        if (rec_ptr->flags & DH_BIG_REC) /* Large record */
        {
          if (!dh_read_group(dh_file, OVERFLOW_SUBFILE,
                             GetFwdLink(dh_file, rec_ptr->data.big_rec),
                             (char*)(&big_buff), DH_BIG_BLOCK_SIZE)) {
            goto exit_dh_analyse;
          }

          record_len = rec_bytes + big_buff.data_len;
          large_record_count++;
          if (record_len < smallest_lrg_record)
            smallest_lrg_record = record_len;
          if (record_len > largest_lrg_record)
            largest_lrg_record = record_len;
          total_lrg_record_bytes += record_len;
        } else /* Not large record */
        {
          record_count++;
          record_len = rec_bytes;
          if (rec_bytes < smallest_record)
            smallest_record = rec_bytes;
          if (rec_bytes > largest_record)
            largest_record = rec_bytes;
          total_record_bytes += rec_bytes;
        }

        for (i = 0, n = 16; i < 10; n <<= 1, i++) {
          if (record_len <= n) {
            histogram[i] += 1;
            goto histogram_done;
          }
        }
        histogram[10] += 1;
      histogram_done:

        rec_offset += rec_bytes;
      }

      /* Move to next group buffer */

      subfile = OVERFLOW_SUBFILE;
      grp = GetFwdLink(dh_file, buff->next);
    } while (grp != 0);

    /* Unlock group */

    FreeGroupReadLock(lock_slot);
    lock_slot = 0;

    /* Accumulate figures from this group */

    if (recs_in_group == 0)
      empty_groups++;

    switch (blocks_in_group) {
      case 1:
        break;
      case 2:
        overflowed_groups++;
        break;
      default:
        badly_overflowed_groups++;
        break;
    }

    if (recs_in_group > max_recs_per_group)
      max_recs_per_group = recs_in_group;
    if (recs_in_group < min_recs_per_group)
      min_recs_per_group = recs_in_group;

    if (blocks_in_group > largest_group)
      largest_group = blocks_in_group;
    if (blocks_in_group < smallest_group)
      smallest_group = blocks_in_group;

    if (used_bytes_in_group > max_bytes_per_group)
      max_bytes_per_group = used_bytes_in_group;
    if (used_bytes_in_group < min_bytes_per_group)
      min_bytes_per_group = used_bytes_in_group;

    total_blocks += blocks_in_group;
  }

  status = TRUE;

exit_dh_analyse:
  if (lock_slot)
    FreeGroupReadLock(lock_slot);

  /* Decrement inhibit count now that we have finished */

  StartExclusive(FILE_TABLE_LOCK, 2);
  fptr->inhibit_count--;
  EndExclusive(FILE_TABLE_LOCK);

  if (!status)
    return FALSE;

  /* Construct return string */

  if (largest_group == 0)
    smallest_group = 0;
  if (max_recs_per_group == 0)
    min_recs_per_group = 0;
  if (max_bytes_per_group == 0)
    min_bytes_per_group = 0;
  if (largest_record == 0)
    smallest_record = 0;
  if (largest_lrg_record == 0)
    smallest_lrg_record = 0;

  /*                 1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
   * 16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31*/

  nwritten = snprintf(
      result, result_size,
      "%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32
      ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32
      ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId64 ",%" PRId32 ",%" PRId32
      ",%" PRId64 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32
      ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32
      ",%" PRId32,
      fptr->params.modulus,    /*  1 Modulus */
      empty_groups,            /*  2 Groups with no records */
      overflowed_groups,       /*  3 Single overflow groups */
      badly_overflowed_groups, /*  4 Badly overflowed groups */
      min_bytes_per_group,     /*  5 Minimum used bytes per group */
      max_bytes_per_group,     /*  6 Maximum used bytes per group */
      smallest_group,          /*  7 Minimum blocks per group */
      largest_group,           /*  8 Maximum blocks per group */
      total_blocks,            /*  9 Total used blocks (excl large recs) */
      min_recs_per_group,      /* 10 Minimum records per group */
      max_recs_per_group,      /* 11 Maximum records per group */
      record_count,            /* 12 Number of non-large records */
      large_record_count,      /* 13 Number of large records */
      smallest_record,         /* 14 Minimum bytes per non-large record */
      largest_record,          /* 15 Maximum bytes per non-large record */
      total_record_bytes,      /* 16 Total non-large record space */
      smallest_lrg_record,     /* 17 Minimum bytes per large record */
      largest_lrg_record,      /* 18 Maximum bytes per large record */
      total_lrg_record_bytes,  /* 19 Total large record space */
      histogram[0],            /* 20 Records up to 16 bytes */
      histogram[1],            /* 21 Records up to 32 bytes */
      histogram[2],            /* 22 Records up to 64 bytes */
      histogram[3],            /* 23 Records up to 128 bytes */
      histogram[4],            /* 24 Records up to 256 bytes */
      histogram[5],            /* 25 Records up to 512 bytes */
      histogram[6],            /* 26 Records up to 1k bytes */
      histogram[7],            /* 27 Records up to 2k bytes */
      histogram[8],            /* 28 Records up to 4k bytes */
      histogram[9],            /* 29 Records up to 8k bytes */
      histogram[10],           /* 30 Records over 8k bytes */
      non_numeric_ids);        /* 31 Records with non-numeric ids */

  if (nwritten < 0 || (size_t)nwritten >= result_size) {
    log_printf("DH_ANALYSE: Result string overflow (%d bytes needed)\n",
               nwritten);
    result[0] = '\0';
    return FALSE;
  }

  return TRUE;
}

#endif /* !ANALYSE_UNIT_TEST */

/* ======================================================================
   dir_walk_regular_files()  -  Scan directory regular files             */

Private int dir_walk_regular_files(FILE_ENTRY* fptr, DIR_WALK_STATS* stats,
                                   const char* caller) {
  char name[MAX_PATHNAME_LEN + 1];
  char parent_name[MAX_PATHNAME_LEN + 1];
  int parent_len;
  DIR* dfu;
  struct dirent* dp;
  struct stat statbuf;

  stats->record_count = 0;
  stats->total_bytes = 0;
  stats->smallest = INT64_MAX;
  stats->largest = 0;

  if ((dfu = opendir((char*)(fptr->pathname))) == NULL) {
    log_printf("%s: Cannot open directory %s (%s)\n", caller, fptr->pathname,
               strerror(errno));
    return DIR_WALK_ERROR;
  }

  strcpy(parent_name, (char*)(fptr->pathname));
  parent_len = strlen(parent_name);
  if (parent_name[parent_len - 1] == DS)
    parent_name[parent_len - 1] = '\0';

  while ((dp = readdir(dfu)) != NULL) {
    if (my_uptr->events)
      process_events();

    if (k_exit_cause & K_INTERRUPT) /* User interrupt or logout */
    {
      closedir(dfu);
      return DIR_WALK_INTERRUPT;
    }

    if (snprintf(name, MAX_PATHNAME_LEN + 1, "%s%c%s", parent_name, DS,
                 dp->d_name) >= (MAX_PATHNAME_LEN + 1)) {
      log_printf("%s: Overflowed directory/filename path length for %s%c%s\n",
                 caller, parent_name, DS, dp->d_name);
      closedir(dfu);
      k_error("Overflowed directory/filename path length.");
      return DIR_WALK_ERROR;
    }

    if (stat(name, &statbuf)) {
      log_printf("%s: stat(%s) failed (%s)\n", caller, name, strerror(errno));
      closedir(dfu);
      return DIR_WALK_ERROR;
    }

    if (statbuf.st_mode & S_IFREG) {
      stats->record_count++;
      stats->total_bytes += statbuf.st_size;
      if (statbuf.st_size < stats->smallest)
        stats->smallest = statbuf.st_size;
      if (statbuf.st_size > stats->largest)
        stats->largest = statbuf.st_size;
    }
  }

  closedir(dfu);
  return DIR_WALK_OK;
}

/* ======================================================================
   dir_analyse()  -  Analyse a directory file                             */

Private bool dir_analyse(FILE_VAR* fvar, char* result, size_t result_size) {
  (void)fvar;
  FILE_ENTRY* fptr;
  DIR_WALK_STATS stats;
  int walk_status;
  int nwritten;

  fptr = FPtr(fvar->file_id);

  walk_status = dir_walk_regular_files(fptr, &stats, "dir_analyse");
  if (walk_status != DIR_WALK_OK)
    return FALSE;

  if (stats.largest == 0)
    stats.smallest = 0;

  nwritten =
      snprintf(result, result_size, "%" PRId32 ",%" PRId64 ",%" PRId64 ",%" PRId64,
               stats.record_count, stats.total_bytes, stats.smallest,
               stats.largest);

  if (nwritten < 0 || (size_t)nwritten >= result_size) {
    log_printf("dir_analyse: Result string overflow (%d bytes needed)\n",
               nwritten);
    result[0] = '\0';
    return FALSE;
  }

  return TRUE;
}

/* ====================================================================== */

int64 dir_filesize(FILE_VAR* fvar) {
  (void)fvar;
  FILE_ENTRY* fptr;
  DIR_WALK_STATS stats;
  int walk_status;

  fptr = FPtr(fvar->file_id);

  walk_status = dir_walk_regular_files(fptr, &stats, "dir_filesize");
  if (walk_status == DIR_WALK_INTERRUPT)
    return -1;
  if (walk_status != DIR_WALK_OK)
    return -1;

  return stats.total_bytes;
}

/* END-CODE */
