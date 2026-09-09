/* TXN.C
 * Transaction Management
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
 *  8 Sep 26 Linux port - the directory-file arms of op_txncmt() now map the
 *           record id before touching the disk.  dir_write()'s second parameter
 *           is a MAPPED id (op_dio3.c passes map_t1_id()'s output outside a
 *           transaction); both arms here were handed txn->id, which is the RAW
 *           id, because op_dio3.c caches the id the statement used.  A WRITE
 *           inside a transaction therefore created a file the matching READ
 *           could never find, and a DELETE removed a path that never existed,
 *           tolerated the ENOENT and reported success - neither needing an
 *           induced fault; an ordinary successful commit was enough.  The cache
 *           is right to hold the raw id and is unchanged.  UPSTREAM_FIXES 36
 *           (plan A2).
 *  8 Sep 26 Linux port - the directory-file delete at commit now tests remove()
 *           and carries the S_IFREG guard, copying the non-transactional twin
 *           (op_dio3.c).  It was a bare remove() with its return discarded - the
 *           only arm of the four that checked nothing - so a delete that failed
 *           inside a transaction was reported as done and the record stayed on
 *           disk.  UPSTREAM_FIXES 31 (plan A3).
 *  8 Sep 26 Linux port - op_txncmt() now leaves the transaction level it
 *           commits.  It undid neither half of what op_txnbgn() did, so
 *           txn_depth only ever climbed (SYSTEM(1008) could not answer "am I in
 *           a transaction") and a NESTED commit orphaned the outer
 *           transaction's cache on txn_stack - process.txn_id was zeroed above,
 *           so the outer COMMIT then wrote an empty cache and its records were
 *           lost silently.  The reinstate-and-decrement block is lifted out of
 *           rollback() into end_txn_level() and called from both, because
 *           having it in one place with one caller is what the defect was.
 *           UPSTREAM_FIXES 17 (plan A4).
 * 31 Dec 23 SD launch - prior history suppressed
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "dh_int.h"
#include "config.h"

typedef struct TXN_CACHE TXN_CACHE;
struct TXN_CACHE {
  TXN_CACHE* next;
  int16_t mode;
#define TXN_WRITE 1
#define TXN_DELETE 2
#define TXN_CLOSE 3
  FILE_VAR* fvar;    /* File */
  STRING_CHUNK* str; /* Data to write */
  int16_t id_len;
  char id[1];
};

Private TXN_CACHE* txn_head = NULL;
Private TXN_CACHE* txn_tail = NULL;
Private int16_t txn_cproc_level;
Private bool journalled_txn; /* Journalled update in this txn? */

int txn_depth = 0;           /* Also accessed by op_sys.c */
u_int32_t commit_txn_id; /* Also needed by dh_jnl.c */

typedef struct TXN_STACK TXN_STACK;
struct TXN_STACK {
  TXN_STACK* next;
  u_int32_t txn_id;  /* Previous transaction id */
  int16_t cproc_level; /* Command process level of previous transaction */
  bool journalled_txn;
  TXN_CACHE* txn_head;
  TXN_CACHE* txn_tail;
};

#define IdMatch(id1, id2, id_len)                 \
  (((nocase) ? MemCompareNoCase(id1, id2, id_len) \
             : memcmp(id1, id2, id_len)) == 0)

Private TXN_STACK* txn_stack = NULL;

Private TXN_CACHE* alloc_txn(int16_t id_len);
Private void rollback(void);
Private void end_txn_level(void);
Private void clear_parent(int16_t fno, char* id, int16_t id_len);

/* ======================================================================
   op_txnbgn()  -  Begin transaction                                      */

void op_txnbgn() {
  TXN_STACK* stk;

  if (process.txn_id != 0) /* Nested transaction */
  {
    stk = (TXN_STACK*)k_alloc(81, sizeof(TXN_STACK));
    stk->next = txn_stack;
    stk->txn_id = process.txn_id;
    stk->cproc_level = cproc_level;
    stk->journalled_txn = journalled_txn;
    stk->txn_head = txn_head;
    stk->txn_tail = txn_tail;
    txn_stack = stk;

    txn_head = NULL;
    txn_tail = NULL;
  }

  txn_depth++;
  txn_cproc_level = cproc_level;

  StartExclusive(SHORT_CODE, 58);
  if ((process.txn_id = (sysseg->next_txn_id)++) == 0) {
    /* Wrapped  -  Hopefully the oldest transactions are not stacked */
    process.txn_id = (sysseg->next_txn_id)++;
  }
  EndExclusive(SHORT_CODE);

  journalled_txn = FALSE;
}

/* ======================================================================
   op_txncmt()  -  Commit transaction                                     */

void op_txncmt() {
  TXN_CACHE* txn;
  TXN_CACHE* next_txn;
  FILE_VAR* fvar;
  FILE_ENTRY* fptr;
  DH_FILE* dh_file;
  char path[MAX_PATHNAME_LEN + 1];
  STRING_CHUNK* str;
  struct stat statbuf; /* A3: the S_IFREG guard in the delete arm below */
  /* A2: the cached id is the RAW one; the disk wants the MAPPED one.  Sized as
     op_dio3.c sizes it - every mapped character can become two.            */
  char mapped_id[2 * MAX_ID_LEN + 1];

  if (sysseg->flags & SSF_SUSPEND)
    suspend_updates();

  /* 0323 Clear process.txn_id so that close action doesn't loop */

  commit_txn_id = process.txn_id;
  process.txn_id = 0;

  /* Commit all actions */

  for (txn = txn_head; txn != NULL; txn = next_txn) {
    fvar = txn->fvar;

    switch (txn->mode) {
      case TXN_WRITE:
        switch (fvar->type) {
          case DYNAMIC_FILE:
            dh_file = fvar->access.dh.dh_file;

            if (!dh_write(dh_file, txn->id, txn->id_len, txn->str)) {
              k_error(sysmsg(1422));
              goto exit_op_txncmt;
            }
            dh_file->flags |= DHF_FSYNC;
            break;

          case DIRECTORY_FILE:
            /* A2 (UPSTREAM_FIXES 36): map the raw cached id to the filename
               dir_write() expects, exactly as the non-transactional twin does
               at op_dio3.c:838/849.  The failure return cannot fire here - both
               entry points call map_t1_id() and refuse ER_IID before anything
               is cached - but a silent skip would be the null case the
               instrument rules refuse, so it raises 1422 like every other
               failure in this arm. */
            if (!map_t1_id(txn->id, txn->id_len, mapped_id)) {
              process.status = -ER_IID;
              k_error(sysmsg(1422));
              goto exit_op_txncmt;
            }

            if (!dir_write(fvar, mapped_id, txn->str)) {
              k_error(sysmsg(1422));
              goto exit_op_txncmt;
            }
            break;
        }

        if (((str = txn->str) != NULL) && (--(str->ref_ct) == 0))
          s_free(str);

        clear_parent(fvar->file_id, txn->id, txn->id_len);
        break;

      case TXN_DELETE:
        switch (fvar->type) {
          case DYNAMIC_FILE:
            dh_file = fvar->access.dh.dh_file;
            if ((!dh_delete(dh_file, txn->id, txn->id_len)) &&
                (dh_err != DHE_RECORD_NOT_FOUND)) {
              k_error(sysmsg(1423));
              goto exit_op_txncmt;
            }
            dh_file->flags |= DHF_FSYNC;
            break;

          case DIRECTORY_FILE:
            /* A2 (UPSTREAM_FIXES 36): map the raw cached id here too, and
               BEFORE the counters - they were incremented first, so an id that
               could not be mapped would have counted a delete that never
               happened.  It cannot fire today (op_dio3.c:362 validates before
               caching) but a statistic raised by a path that then refuses is
               the null case in miniature. */
            if (!map_t1_id(txn->id, txn->id_len, mapped_id)) {
              process.status = -ER_IID;
              k_error(sysmsg(1423));
              goto exit_op_txncmt;
            }

            /* Increment statistics and transaction counters */

            StartExclusive(FILE_TABLE_LOCK, 50);
            sysseg->global_stats.deletes++;
            fptr = FPtr(fvar->file_id);
            fptr->upd_ct++;
            EndExclusive(FILE_TABLE_LOCK);
            /* converted sprintf() -gwb 22Feb20 */
            if (snprintf(path, MAX_PATHNAME_LEN + 1, "%s%c%s", fptr->pathname,
                         DS, mapped_id) >= (MAX_PATHNAME_LEN + 1)) {
               /* TODO should log more detail here */
               k_error("Overflowed path/filename length in op_txncmt()!");
            } else {
              /* A3 (UPSTREAM_FIXES 31): test the delete.  This was a bare
                 remove() with its return discarded - the only arm of the four
                 that checked nothing - so a delete that failed inside a
                 transaction was reported as done and the record stayed on disk.
                 The shape below is this switch's own (the dh_delete arm above
                 raises 1423) and matches the non-transactional twin at
                 op_dio3.c:390-403.  ENOENT is tolerated, exactly as
                 DHE_RECORD_NOT_FOUND is above: the record is gone, which is what
                 was asked for. */

              /* 0408 Check that this really is a file, not CON, COMn, LPTn */
              if (!stat(path, &statbuf) && !(statbuf.st_mode & S_IFREG)) {
                process.status = -ER_IID;
                k_error(sysmsg(1423));
                goto exit_op_txncmt;
              }

              if (remove(path) < 0) {
                process.os_error = errno;
                if (process.os_error != ENOENT) {
                  process.status = -ER_PERM;
                  log_permissions_error(fvar);
                  k_error(sysmsg(1423));
                  goto exit_op_txncmt;
                }
              }
            }
            break;
        }

        clear_parent(fvar->file_id, txn->id, txn->id_len);
        break;

      case TXN_CLOSE:
        fvar = txn->fvar;
        if (--(fvar->ref_ct) == 0)
          dio_close(fvar);
        break;
    }

    next_txn = txn->next;
    k_free(txn);
  }

  txn_head = NULL;
  txn_tail = NULL;

  /* If we are synchronising at transaction commit, run down the DH file
    chain, doing an fsync() for each file marked as needing it.          */

  if (pcfg.fsync & 0x0002) {
    for (dh_file = dh_file_head; dh_file != NULL;
         dh_file = dh_file->next_file) {
      if (dh_file->flags & DHF_FSYNC) {
        dh_fsync(dh_file, PRIMARY_SUBFILE);
        dh_fsync(dh_file, OVERFLOW_SUBFILE);
      }
    }
  }

  /* Release all locks acquired during this transaction */

  unlock_txn(commit_txn_id);

  /* A4 (UPSTREAM_FIXES 17): leave the transaction level this commit ended,
     which this function never did.  See end_txn_level().  DELIBERATELY BEFORE
     THE LABEL, so the write/delete error paths above - which have already
     called k_error() on a broken transaction - do not pop a level as though
     they had committed.  (That leaves a separate, pre-existing gap: on those
     error paths process.txn_id was zeroed at the top, so txn_abort() and
     op_txnrbk() find nothing and the level stays counted.  That is a different
     defect - it needs a decision about the records already written, not a
     decrement - and is left for the commit-rollback work, plan A1.)          */

  end_txn_level();

exit_op_txncmt:
  return;
}

/* ======================================================================
   op_txnend()  -  End transaction                                        */

void op_txnend() {
  if (process.txn_id == 0)
    k_error(sysmsg(1424));

  rollback();
}

/* ======================================================================
   op_txnrbk()  -  Rollback transactions at this or higher command level  */

void op_txnrbk() {
  if ((process.txn_id != 0) && (txn_cproc_level >= cproc_level)) {
    tio_printf(sysmsg(1425));
  }

  while ((process.txn_id != 0) && (txn_cproc_level >= cproc_level)) {
    rollback();
  }
}

/* ======================================================================
   txn_abort()  -  Roll back at abort/logout/terminate/etc                */

void txn_abort() {
  if (process.txn_id) {
    tio_printf(sysmsg(1426));
    while (process.txn_id)
      rollback();
  }
}

/* ======================================================================
   txn_close()  -  Close file in transaction                              */

bool txn_close(FILE_VAR* fvar) {
  bool status = FALSE;
  TXN_CACHE* txn;

  fvar->ref_ct++; /* Ensure doesn't really get closed */

  /* Allocate memory for TXN_CACHE entry */

  txn = alloc_txn(0);
  if (txn == NULL)
    goto exit_txn_close;

  txn->mode = TXN_CLOSE;
  txn->fvar = fvar;

  status = TRUE;

exit_txn_close:
  return status;
}

/* ======================================================================
   txn_delete()  -  Delete record via transaction cache                   */

bool txn_delete(FILE_VAR* fvar, char* id, int16_t id_len) {
  bool status = FALSE;
  TXN_CACHE* txn;
  STRING_CHUNK* str;
  int16_t fno;
  FILE_ENTRY* fptr;
  bool nocase;

  /* Scan cache for an existing entry for this file */

  fno = fvar->file_id;
  fptr = FPtr(fno);
  nocase = (fptr->flags & DHF_NOCASE) != 0;

  for (txn = txn_head; txn != NULL; txn = txn->next) {
    if ((txn->fvar->file_id == fno)        /* Right file... */
        && (txn->id_len == id_len)         /* ...right id length... */
        && (IdMatch(txn->id, id, id_len))) /* ...right id */
    {
      switch (txn->mode) {
        case TXN_WRITE: /* Replace write with delete */
          txn->mode = TXN_DELETE;
          if ((str = txn->str) != NULL) {
            if (--(str->ref_ct) == 0)
              s_free(str);
            txn->str = NULL;
          }
          goto exit_txn_delete_ok;

        case TXN_DELETE: /* Deleted twice! */
          goto exit_txn_delete_ok;
      }
    }
  }

  /* Allocate memory for TXN_CACHE entry */

  txn = alloc_txn(id_len);
  if (txn == NULL)
    goto exit_txn_delete;

  txn->mode = TXN_DELETE;
  txn->fvar = fvar;
  txn->id_len = id_len;
  memcpy(txn->id, id, id_len);

exit_txn_delete_ok:
  status = TRUE;

exit_txn_delete:
  return status;
}

/* ======================================================================
   txn_open()  -  Try to reopen a file from the cache                     */

FILE_VAR* txn_open(char* pathname) {
  TXN_CACHE* txn;
  TXN_CACHE* prev_txn = NULL;
  FILE_VAR* fvar;
  FILE_ENTRY* fptr;

  /* Scan for a close for this file */

  for (txn = txn_head; txn != NULL; txn = txn->next) {
    if (txn->mode == TXN_CLOSE) {
      fvar = txn->fvar;
      fptr = FPtr(fvar->file_id);
      if (!strcmp((char*)(fptr->pathname), pathname)) /* Right file */
      {
        /* We have found the right file. The VOC name may be wrong but this
          will be fixed by the caller. All we are trying to do is avoid
          creating a new fvar from scratch as this could leave us with a
          cache chain packed full of close/open pairs (e.g. TRANS() loop)  */

        /* Remove the close entry for this file */

        if (prev_txn == NULL)
          txn_head = txn->next;
        else
          prev_txn->next = txn->next;
        if (txn == txn_tail)
          txn_tail = prev_txn;

        /* The fvar reference count still reflects the old open */

        return fvar;
      }
    }

    prev_txn = txn;
  }

  return NULL;
}

/* ======================================================================
   txn_read()  -  Attempt to read record from cache

   It is the caller's responsibility to increment the string reference
   count if the string is to be retained.                                  */

int16_t txn_read(FILE_VAR* fvar,
                   char* id,
                   int16_t id_len,
                   char* actual_id,
                   STRING_CHUNK** str) {
  int16_t status = 0;
  TXN_CACHE* head;
  TXN_STACK* stack;
  TXN_CACHE* txn;
  int16_t fno;
  FILE_ENTRY* fptr;
  bool nocase;

  fno = fvar->file_id;
  fptr = FPtr(fno);
  nocase = (fptr->flags & DHF_NOCASE) != 0;

  head = txn_head;
  stack = txn_stack;
  while (1) {
    for (txn = head; txn != NULL; txn = txn->next) {
      if ((txn->fvar->file_id == fno)        /* Right file... */
          && (txn->id_len == id_len)         /* ...right id length... */
          && (IdMatch(txn->id, id, id_len))) /* ...right id */
      {
        switch (txn->mode) {
          case TXN_WRITE:
            status = TXC_FOUND;
            memcpy(actual_id, txn->id, id_len);
            *str = txn->str;
            goto exit_txn_read;

          case TXN_DELETE:
            status = TXC_DELETED;
            memcpy(actual_id, txn->id, id_len);
            goto exit_txn_read;
        }
      }
    }

    if (status)
      break; /* Found in this transaction */

    if (stack == NULL)
      break;                /* Not nested */
    head = stack->txn_head; /* Drop down to parent transaction */
    stack = stack->next;
  }

exit_txn_read:
  return status;
}

/* ======================================================================
   txn_write()  -  Write record to transaction cache                      */

bool txn_write(FILE_VAR* fvar, char* id, int16_t id_len, STRING_CHUNK* str) {
  bool status = FALSE;
  TXN_CACHE* txn;
  STRING_CHUNK* old_str;
  int16_t fno;
  FILE_ENTRY* fptr;
  bool nocase;

  /* Scan cache for an existing entry for this file */

  fno = fvar->file_id;
  fptr = FPtr(fno);
  nocase = (fptr->flags & DHF_NOCASE) != 0;

  for (txn = txn_head; txn != NULL; txn = txn->next) {
    if ((txn->fvar->file_id == fno)        /* Right file... */
        && (txn->id_len == id_len)         /* ...right id length... */
        && (IdMatch(txn->id, id, id_len))) /* ...right id */
    {
      switch (txn->mode) {
        case TXN_WRITE: /* Replace write new write */
          if ((old_str = txn->str) != NULL) {
            if (--(old_str->ref_ct) == 0)
              s_free(old_str);
          }
          txn->str = str;
          goto exit_txn_write_ok;

        case TXN_DELETE: /* Replace delete with write */
          txn->mode = TXN_WRITE;
          txn->str = str;
          if (str != NULL)
            str->ref_ct++;
          goto exit_txn_write_ok;
      }
    }
  }

  /* Allocate memory for TXN_CACHE entry */

  txn = alloc_txn(id_len);
  if (txn == NULL)
    goto exit_txn_write;

  txn->mode = TXN_WRITE;
  txn->fvar = fvar;
  txn->str = str;
  if (str != NULL)
    str->ref_ct++;
  txn->id_len = id_len;
  memcpy(txn->id, id, id_len);

exit_txn_write_ok:
  status = TRUE;

exit_txn_write:
  return status;
}

/* ======================================================================
   alloc_txn()  -  Allocate transaction cache entry                       */

Private TXN_CACHE* alloc_txn(int16_t id_len) {
  TXN_CACHE* txn;
  int bytes;

  bytes = sizeof(TXN_CACHE) + id_len;
  txn = (TXN_CACHE*)k_alloc(21, bytes);
  if (txn == NULL)
    process.status = -ER_MEM;
  else {
    memset(txn, 0, bytes);

    /* Add to chain */

    if (txn_head == NULL)
      txn_head = txn;
    else
      txn_tail->next = txn;
    txn_tail = txn;
  }

  return txn;
}

/* ======================================================================
   rollback()  -  Roll back top level transaction                         */

Private void rollback() {
  TXN_CACHE* txn;
  TXN_CACHE* next_txn;
  FILE_VAR* fvar;
  STRING_CHUNK* str;
  u_int32_t saved_txn_id;

  /* Remove all uncommitted actions */

  for (txn = txn_head; txn != NULL; txn = next_txn) {
    switch (txn->mode) {
      case TXN_WRITE:
        if (((str = txn->str) != NULL) && (--(str->ref_ct) == 0))
          s_free(str);
        break;

      case TXN_DELETE:
        break;

      case TXN_CLOSE:
        fvar = txn->fvar;
        if (--(fvar->ref_ct) == 0) {
          saved_txn_id = process.txn_id; /* 0468 */
          process.txn_id = 0;
          dio_close(fvar);
          process.txn_id = saved_txn_id;
        }
        break;
    }

    next_txn = txn->next;
    k_free(txn);
  }

  txn_head = NULL;
  txn_tail = NULL;

  /* Release all locks acquired during this transaction */

  unlock_txn(process.txn_id);

  /* Exit from this transaction */

  end_txn_level();
}

/* ======================================================================
   end_txn_level()  -  Leave one transaction level, reinstating the parent

   A4 (UPSTREAM_FIXES 17) - LIFTED OUT OF rollback() SO THAT COMMIT CAN DO IT
   TOO.  op_txnbgn() does two things - increments txn_depth, and if a
   transaction is already running pushes that one onto txn_stack.  rollback()
   undid both; op_txncmt() undid NEITHER, and BCOMP's st.commit jumps past the
   OP.TXNEND that would have called rollback(), so on the committed path nothing
   ever reversed them.  It is one function rather than two copies because the
   defect was exactly that the bookkeeping lived in one place with one caller.

   THE unlock STAYS WITH THE CALLER and is not moved in here: the two pass
   different ids.  rollback() unlocks process.txn_id, still the running
   transaction at that point, while op_txncmt() has already zeroed
   process.txn_id (so the close action does not loop) and unlocks the saved
   commit_txn_id.  Folding that in would have to re-derive which id to use.   */

Private void end_txn_level() {
  TXN_STACK* stk;

  if ((stk = txn_stack) != NULL) /* Reinstate nested transaction */
  {
    process.txn_id = stk->txn_id;
    txn_cproc_level = stk->cproc_level;
    journalled_txn = stk->journalled_txn;
    txn_head = stk->txn_head;
    txn_tail = stk->txn_tail;
    txn_stack = stk->next;
    k_free(stk);
  } else
    process.txn_id = 0;

  txn_depth--;
}

/* ======================================================================
   clear_parent()  -  Clear references to record from parent txns         */

Private void clear_parent(int16_t fno,    /* File number */
                          char* id,         /* Record id and... */
                          int16_t id_len) /* ...id length */
{
  TXN_STACK* stack;
  TXN_CACHE* txn;
  TXN_CACHE* prev;
  TXN_CACHE* next;
  STRING_CHUNK* str;
  FILE_ENTRY* fptr;
  bool nocase;

  fptr = FPtr(fno);
  nocase = (fptr->flags & DHF_NOCASE) != 0;

  /* Modified by Composer AI - 2026/06/10.
     Use-after-free: when an entry was dechained and k_free'd, the for
     loop update clause still executed "prev = txn", leaving prev
     pointing at freed memory; a later removal in the same scan then
     wrote through it ("prev->next = ..."). Only advance prev when the
     current entry was NOT removed. */
  /* for (stack = txn_stack; stack != NULL; stack = stack->next) {
    prev = NULL;
    for (txn = stack->txn_head; txn != NULL; prev = txn, txn = next) {
      next = txn->next;
      switch (txn->mode) {
        case TXN_WRITE:
        case TXN_DELETE:
          if ((txn->fvar->file_id == fno) && (txn->id_len == id_len) &&
              (IdMatch(txn->id, id, id_len))) {
            if (txn->mode == TXN_WRITE) {
              if (((str = txn->str) != NULL) && (--(str->ref_ct) == 0))
                s_free(str);
            }

            / * Dechain this entry * /

            if (prev == NULL)
              stack->txn_head = txn->next;
            else
              prev->next = txn->next;
            if (txn->next == NULL)
              stack->txn_tail = prev;
            k_free(txn);
          }
          break;
      }
    }
  } */
  for (stack = txn_stack; stack != NULL; stack = stack->next) {
    prev = NULL;
    for (txn = stack->txn_head; txn != NULL; txn = next) {
      bool removed = FALSE;

      next = txn->next;
      switch (txn->mode) {
        case TXN_WRITE:
        case TXN_DELETE:
          if ((txn->fvar->file_id == fno) && (txn->id_len == id_len) &&
              (IdMatch(txn->id, id, id_len))) {
            if (txn->mode == TXN_WRITE) {
              if (((str = txn->str) != NULL) && (--(str->ref_ct) == 0))
                s_free(str);
            }

            /* Dechain this entry */

            if (prev == NULL)
              stack->txn_head = txn->next;
            else
              prev->next = txn->next;
            if (txn->next == NULL)
              stack->txn_tail = prev;
            k_free(txn);
            removed = TRUE;
          }
          break;
      }
      if (!removed)
        prev = txn;
    }
  }
  /* -------------------- */
}

/* END-CODE */
