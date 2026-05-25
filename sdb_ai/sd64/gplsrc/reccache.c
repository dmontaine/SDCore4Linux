/* RECCACHE.C
 * Record cache management.
 * Copyright (c) 2005 Ladybridge Systems, All Rights Reserved
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
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "config.h"

typedef struct REC_CACHE_ENTRY REC_CACHE_ENTRY;
struct REC_CACHE_ENTRY {
  REC_CACHE_ENTRY* next;
  REC_CACHE_ENTRY* prev;
  int16_t file_no;  /* File table index */
  u_int32_t upd_ct; /* File's upd_ct value when cached */
  STRING_CHUNK* data; /* Record data, NULL if null string */
  int16_t id_len;   /* Length of record id */
  char id[MAX_ID_LEN]; /* Id, not null terminated */
};

Private REC_CACHE_ENTRY* rec_cache_head = NULL;
Private REC_CACHE_ENTRY* rec_cache_tail = NULL;
Private int16_t rec_cache_size = 0; /* Current size */

static void rec_cache_release_data(STRING_CHUNK* str) {
  if ((str != NULL) && (--(str->ref_ct) == 0))
    s_free(str);
}

static bool rec_cache_valid_args(int16_t fno, int16_t id_len, char* id) {
  if (fno < 1 || fno > sysseg->used_files)
    return FALSE;
  if (id_len < 0 || id_len > MAX_ID_LEN)
    return FALSE;
  if (id_len > 0 && id == NULL)
    return FALSE;
  return TRUE;
}

static bool rec_cache_id_match(FILE_ENTRY* fptr,
                               REC_CACHE_ENTRY* p,
                               char* id,
                               int16_t id_len) {
  if (p->id_len != id_len)
    return FALSE;
  if (fptr->flags & DHF_NOCASE)
    return MemCompareNoCase(id, p->id, id_len) == 0;
  return memcmp(p->id, id, (size_t)id_len) == 0;
}

/* ======================================================================
   init_record_cache()  -  Initialise record cache                        */

void init_record_cache(void) {
  REC_CACHE_ENTRY* p;
  int16_t target;

  target = pcfg.reccache;
  if (target < 0)
    target = 0;
  else if (target > 32)
    target = 32;

  /* Expand cache */

  while (rec_cache_size < target) {
    p = (REC_CACHE_ENTRY*)k_alloc(71, sizeof(REC_CACHE_ENTRY));
    if (p == NULL)
      break;
    p->next = NULL;
    p->prev = rec_cache_tail;
    p->file_no = -1;
    p->id_len = 0;
    p->data = NULL;
    if (rec_cache_head == NULL)
      rec_cache_head = p;
    else
      rec_cache_tail->next = p;
    rec_cache_tail = p;
    rec_cache_size++;
  }

  /* Contract cache */

  while (rec_cache_size > target) {
    p = rec_cache_tail;
    rec_cache_tail = p->prev;
    if (rec_cache_tail != NULL)
      rec_cache_tail->next = NULL;

    rec_cache_release_data(p->data);

    k_free(p);

    if (--rec_cache_size == 0)
      rec_cache_head = NULL;
  }
}

/* ======================================================================
   cache_record()  -  Add record to cache                                 */

void cache_record(int16_t fno, /* File table index */
                  int16_t id_len,
                  char* id,
                  STRING_CHUNK* data) {
  REC_CACHE_ENTRY* p;

  if (!rec_cache_size || !rec_cache_valid_args(fno, id_len, id))
    return;

  /* Release the oldest entry.  It doesn't matter if there is another
    version of this record in the cache as we could never find it.   */

  p = rec_cache_tail;
  rec_cache_release_data(p->data);

  if (p != rec_cache_head) /* Not already at head */
  {
    /* Dechain */

    rec_cache_tail = p->prev;
    rec_cache_tail->next = NULL;

    /* Rechain at head */

    rec_cache_head->prev = p;
    p->next = rec_cache_head;
    p->prev = NULL;
    rec_cache_head = p;
  }

  /* Enter details of new record */

  p->file_no = fno;
  p->upd_ct = FPtr(fno)->upd_ct;
  p->data = data;
  if (data != NULL)
    data->ref_ct++;
  p->id_len = id_len;
  if (id_len > 0)
    memcpy(p->id, id, (size_t)id_len);
}

/* ======================================================================
   scan_record_cache()  -  Search for a record in the cache
   Returns pointer to string via data argument, incrementing ref count    */

bool scan_record_cache(int16_t fno,
                       int16_t id_len,
                       char* id,
                       STRING_CHUNK** data) {
  REC_CACHE_ENTRY* p;
  FILE_ENTRY* fptr;
  u_int32_t upd_ct;

  if (data == NULL || !rec_cache_valid_args(fno, id_len, id))
    return FALSE;

  fptr = FPtr(fno);
  upd_ct = fptr->upd_ct;
  for (p = rec_cache_head; p != NULL; p = p->next) {
    if ((p->upd_ct == upd_ct) && (p->file_no == fno) &&
        rec_cache_id_match(fptr, p, id, id_len)) {
      if ((*data = p->data) != NULL)
        p->data->ref_ct++;

      if (p != rec_cache_head) {
        /* Move to head of cache */

        p->prev->next = p->next;

        if (p == rec_cache_tail)
          rec_cache_tail = p->prev;
        else
          p->next->prev = p->prev;

        rec_cache_head->prev = p;
        p->next = rec_cache_head;
        p->prev = NULL;
        rec_cache_head = p;
      }

      return TRUE;
    }
  }

  return FALSE;
}

/* ======================================================================
   dump_rec_cache()  -  Log current cache contents (debug)                */

void dump_rec_cache(void) {
  REC_CACHE_ENTRY* p;
  int slot;

  log_printf("Record cache: %d slot(s), limit %d\n", (int)rec_cache_size,
             (int)pcfg.reccache);
  if (rec_cache_head == NULL)
    return;

  for (p = rec_cache_head, slot = 1; p != NULL; p = p->next, slot++) {
    const char* path;

    if (p->file_no >= 1 && p->file_no <= sysseg->used_files)
      path = (char*)(FPtr(p->file_no)->pathname);
    else
      path = "?";

    log_printf("  [%d] file %d (%s) upd_ct=%u id_len=%d id=%.*s %s\n", slot,
               (int)p->file_no, path, (unsigned)p->upd_ct, (int)p->id_len,
               (int)p->id_len, p->id, (p->data != NULL) ? "cached" : "null");
  }
}

/* END-CODE */
