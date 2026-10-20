/* MASTERS.C
 * S.67 stage 1 - the master files of the SDSYS account: voc_master, dict_master and master_state, kept in step with the accounts, ACCOUNT TO MASTER.
 * Copyright (c) 2026 SD Core for Linux
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
 * 19 Oct 26 dm  The independent verifier's findings on stages 1 and 2, fixed.  F1 the master files and their dictionaries are 0700 and 0600 (the group they were
 *               given was never set, and the group of an SDSYS session is sdusers); F2 mst_deliver copies the account out of the table it was found in (the table
 *               is read again inside the write, which freed what the audit line then read); F3 a save is judged against the record the session READ
 *               (masters_note_read; a blind save of a record the account has is refused), not against master_state, which moves at every drain; F4 the
 *               comparison is made again INSIDE dh_write, under the file's own group lock (masters_cas_check), so a plain WRITE in the window is not lost;
 *               F5 an account whose directory cannot be listed keeps its dictionary copies; F6 a *.dic that links out of the account is not the account's;
 *               F7 SYNC.MASTERS and CHECK.MASTERS read each master file once (an index sorted by key), not once per account, and sync has one op for all
 *               accounts (syncall); a dictionary key in capitals finds the dictionary; a journal line is never glued to an unterminated one; messages
 *               11583, 11584 and 11586 fit k_error and say "Nothing was changed" before the key can push it out.
 * 19 Oct 26 dm  Stage 2 (D7, owner 17 Oct 2026, warned): MASTER TO ACCOUNT.  When SDSYS saves a record of voc_master or dict_master the kernel
 *               compares the account's current record with master_state, and REFUSES (DHE_MASTER_REFUSED, nothing changed) if they differ; else it
 *               takes the account's record with a try-lock that never waits, writes the account's own file itself, brings master_state up to date and
 *               writes an audit line.  A delete of a master record, a save inside a transaction and a save by anyone but the administrator are
 *               refused.  A new VOC or dictionary is given group write where the account's directory has it (masters_fix_modes), CHECK.MASTERS
 *               lists what a master edit could not be written into (nonwritable, norights), and the stage 1 writes to the masters are marked so
 *               that they are not taken for saves.
 * 19 Oct 26 dm  New (S.67 stage 1, owner's request of 17 Oct: "two master files, voc_master and dict_master in the SDSYS account ...
 *               synchronized so that SDSYS can edit any account Voc or Dict record by editing its copy").  THIS FILE WAS THE ACCOUNT-TO-MASTER
 *               HALF; the master-to-account half (SDSYS saves a master record and the kernel writes the account's file) is stage 2, below.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 *  THE HOOK (called from the DH layer, so that every writer passes it - $internal programs, restores and the kernel's own writes included):
 *   masters_note_record()   a record of a VOC or a dictionary was written or deleted (dh_write, dh_delete)
 *   masters_note_dh()       a VOC or dictionary was cleared (dh_clear)
 *   masters_note_name()     a VOC or dictionary file was created, removed or renamed (dh_create_file, OSPATH delete, OSRENAME, !OSCOPY)
 *  Each appends ONE line - account, kind, op, file, record id: KEYS, never data - to <sysdir>/$master.journal with a single O_APPEND
 *  write, the way the audit file is written: the file is made by the administrator (never by a session, which would then own it), mode
 *  0620, and a session that finds it missing says nothing.  A journal that cannot be written NEVER stops the user's write: it sets a flag
 *  in the shared segment (stale) that CHECK.MASTERS and LIST.MASTER.PENDING report; a journal at its size limit is not appended to and sets
 *  the resync flag.  Inside a transaction the writes reach the DH layer at COMMIT, so the line is delivered at commit and a rollback
 *  delivers nothing: the hook needs no transaction code of its own.
 *
 *  THE DRAIN (masters_open_hook, and the K_MASTERS ops): when the administrator opens voc_master, dict_master or master_state, or runs
 *  SYNC.MASTERS, the journal from the saved position to its end is read, each distinct key (or, for a file-level line, each distinct file)
 *  is made to match the account's CURRENT state, and master_state records the position.  The drain applies state, not the lines'
 *  contents, so it is idempotent: a line seen twice, or after a crash, does no harm.
 *
 *  THE KEYS.  voc_master  account*id      dict_master  account*file*id      master_state  v*account*id and d*account*file*id (a kind
 *  letter, because a VOC record called file*id would otherwise have the key of a dictionary record) and $journal (the drain's position).
 *  The master key is cut at the first one or two asterisks only.  The account of a dictionary is the account whose DIRECTORY holds it (the
 *  longest registered path that is a prefix of the dictionary's), and file is its path below that directory with ".dic" taken off.
 *  A key longer than MAXIDLEN (minus the two characters of the state key) cannot be mirrored - a master file holding a longer id could not
 *  be opened again - and is counted and reported, never dropped silently.
 *
 *  master_state keeps, for every mirrored key, the checksum of the account's record as last copied and the time.  (Stage 2 compared a save with
 *  it; since the verifier's F3 a save is compared with the record the session READ, and master_state is consulted only for a key the session did
 *  not read, to see that the account has not deleted what the copy still holds.)
 *
 *  MASTER TO ACCOUNT (stage 2).  masters_before_write is called by dh_write for EVERY write, first of all, and does nothing for a file that is not
 *  voc_master or dict_master (one flag test once the file's name has been looked at).  For those two it is the whole of D7:
 *    1 only the administrator; 2 the key (account*id, account*file*id) names a registered account and, for a dictionary, a dictionary it has;
 *    3 the account's files can be written by THIS process (access(), and why not if they cannot: the mode, a session that began before SDSYS
 *      joined the group, a group SDSYS is not in); 4 the account's record is locked by a try-lock that returns at once (lock_record with no_wait),
 *      unless this process holds it already; 5 the record as it is now has the checksum of the record THIS SESSION READ (masters_note_read keeps the
 *      last 128) - the account has not changed it since - else REFUSED and nothing is lost; a key the session did not read may create a record and
 *      may not overwrite one; 6 the account's file is written HERE, by this process (so it needs the group), through dh_write like any other
 *      writer, which journals it, and which asks the comparison of 5 again (masters_cas_check) with the record's group locked; 7 master_state and
 *      the session's read are brought up to date; 8 the lock is let go; 9 the audit line.
 *  Every refusal comes back as DHE_MASTER_REFUSED with its reason in masters_refusal_text(); op_write and op_delete print it unless the statement has
 *  ON ERROR.  A DELETE of a master record is refused (the plan says SDSYS SAVES; deleting a copy is not deleting the account's record), and so is a
 *  save or a delete inside a transaction (the write reaches the DH layer at COMMIT, where a refusal would be half way through other writes).
 *  The stage 1 code writes the masters itself (the drain, the syncs): those writes go through mst_mwrite / mst_mdelete, which raise mst_inside for the
 *  one call, so they are not taken for saves.
 *
 *  Public:
 *   masters_note_record  masters_note_dh  masters_note_name  masters_open_hook  masters_request
 *   masters_before_write  masters_before_delete  masters_txn_refusal  masters_refusal_text  masters_fix_modes
 *   masters_note_read  masters_cas_check  (and the int masters_cas_on)
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "dh_int.h"
#include "syscom.h"
#include "header.h"
#include "config.h"

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <limits.h>
#include <pwd.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

/* k_error() never returns (see op_dio3.c) */
void k_error(char msg[], ...) __attribute__((noreturn));
bool fullpath(char *path, char *name);

#define MST_VOC 1
#define MST_DICT 2

#define MST_JOURNAL_NAME "$master.journal"
#define MST_VOC_MASTER "voc_master"
#define MST_DICT_MASTER "dict_master"
#define MST_STATE "master_state"
#define MST_STATE_JOURNAL "$journal"

#define MST_JOURNAL_CAP (4L * 1024L * 1024L) /* a journal this big is not appended to; the resync flag is set instead */
#define MST_READ_MAX (16L * 1024L * 1024L)    /* the most one drain reads in one go */
#define MST_ACC_AGE 60                        /* seconds before the account table is read again */
#define MST_ACC_MISS 5                        /* ... and the least between two reads caused by a miss */
#define MST_CHECK_ROWS 2000                   /* the most difference rows CHECK returns */
#define MST_FILE_MAX 200                      /* the longest dictionary name the journal carries */
#define MST_SYSTEM_ACCOUNT "sdsys"            /* the administrator's own account: its files belong to the user that runs SDSYS's sessions */

/* the answers of K_MASTERS: the first field */
#define MSA_OK 0
#define MSA_NOTSET 1
#define MSA_REFUSED 2
#define MSA_ARGS 3
#define MSA_NOACC 4
#define MSA_ERR 5

/* what one key's sync did */
#define MS_SAME 0
#define MS_WROTE 1
#define MS_DELETED 2
#define MS_ABSENT 3
#define MS_LONG 4
#define MS_ERR 5

/* ======================================================================
   Small containers                                                       */

/* a list of record ids: each entry is a length byte then the id */
typedef struct {
  unsigned char *d;
  size_t len;
  size_t cap;
  int n;
} MST_IDS;

Private void mst_ids_free(MST_IDS *l) {
  free(l->d);
  l->d = NULL;
  l->len = l->cap = 0;
  l->n = 0;
}

Private bool mst_ids_add(MST_IDS *l, const char *id, int len) {
  if ((len < 0) || (len > 255))
    return FALSE;
  if (l->len + 1 + (size_t)len > l->cap) {
    size_t ncap = (l->cap == 0) ? 4096 : l->cap * 2;
    unsigned char *nd;

    while (ncap < l->len + 1 + (size_t)len)
      ncap *= 2;
    nd = (unsigned char *)realloc(l->d, ncap);
    if (nd == NULL)
      return FALSE;
    l->d = nd;
    l->cap = ncap;
  }
  l->d[l->len++] = (unsigned char)len;
  memcpy(l->d + l->len, id, (size_t)len);
  l->len += (size_t)len;
  l->n++;
  return TRUE;
}

/* a growing byte buffer, for answers */
typedef struct {
  char *b;
  size_t len;
  size_t cap;
  bool oom;
} MST_BUF;

Private void mst_buf_free(MST_BUF *x) {
  free(x->b);
  x->b = NULL;
  x->len = x->cap = 0;
}

Private void mst_buf_add(MST_BUF *x, const char *s, size_t n) {
  if (x->oom)
    return;
  if (x->len + n + 1 > x->cap) {
    size_t ncap = (x->cap == 0) ? 1024 : x->cap * 2;
    char *nb;

    while (ncap < x->len + n + 1)
      ncap *= 2;
    nb = (char *)realloc(x->b, ncap);
    if (nb == NULL) {
      x->oom = TRUE;
      return;
    }
    x->b = nb;
    x->cap = ncap;
  }
  memcpy(x->b + x->len, s, n);
  x->len += n;
  x->b[x->len] = '\0';
}

Private void mst_buf_str(MST_BUF *x, const char *s) {
  mst_buf_add(x, s, strlen(s));
}

Private void mst_buf_num(MST_BUF *x, long v) {
  char t[32];

  snprintf(t, sizeof(t), "%ld", v);
  mst_buf_str(x, t);
}

/* a field or value mark may not come out of an id into an answer */
Private void mst_buf_text(MST_BUF *x, const char *s, int len) {
  int i;
  char c;

  for (i = 0; i < len; i++) {
    c = s[i];
    if (((unsigned char)c >= 0xFD) || ((unsigned char)c < 32))
      c = '?';
    mst_buf_add(x, &c, 1);
  }
}

#define MST_FM FIELD_MARK
#define MST_VM VALUE_MARK

Private int mst_fold(int c) {
  return ((c >= 'a') && (c <= 'z')) ? (c - 32) : c;
}

/* ids compare as the NOCASE files compare them: ASCII case folded, the shorter first on a tie */
Private int mst_id_cmp(const char *a, int alen, const char *b, int blen) {
  int i, n = (alen < blen) ? alen : blen;

  for (i = 0; i < n; i++) {
    int x = mst_fold((unsigned char)a[i]);
    int y = mst_fold((unsigned char)b[i]);

    if (x != y)
      return x - y;
  }
  return alen - blen;
}

/* a sorted index over an id list, for membership tests */
typedef struct {
  const MST_IDS *l;
  size_t *off;
  int n;
} MST_SET;

Private const MST_IDS *mst_sort_ctx = NULL;

Private int mst_set_cmp(const void *pa, const void *pb) {
  size_t a = *(const size_t *)pa;
  size_t b = *(const size_t *)pb;

  return mst_id_cmp((const char *)mst_sort_ctx->d + a + 1, mst_sort_ctx->d[a], (const char *)mst_sort_ctx->d + b + 1, mst_sort_ctx->d[b]);
}

Private bool mst_set_build(MST_SET *s, const MST_IDS *l) {
  size_t p;
  int i = 0;

  s->l = l;
  s->n = l->n;
  s->off = (size_t *)malloc(sizeof(size_t) * (size_t)(l->n > 0 ? l->n : 1));
  if (s->off == NULL)
    return FALSE;
  for (p = 0; p < l->len; p += 1 + (size_t)l->d[p])
    s->off[i++] = p;
  mst_sort_ctx = l;
  qsort(s->off, (size_t)s->n, sizeof(size_t), mst_set_cmp);
  return TRUE;
}

Private bool mst_set_has(const MST_SET *s, const char *id, int len) {
  int lo = 0, hi = s->n - 1;

  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    size_t o = s->off[mid];
    int c = mst_id_cmp((const char *)s->l->d + o + 1, s->l->d[o], id, len);

    if (c == 0)
      return TRUE;
    if (c < 0)
      lo = mid + 1;
    else
      hi = mid - 1;
  }
  return FALSE;
}

Private void mst_set_free(MST_SET *s) {
  free(s->off);
  s->off = NULL;
  s->n = 0;
}

/* ======================================================================
   The shared segment's flags, and the paths                              */

Private void mst_flag(u_int16_t bit) {
  if (sysseg == NULL)
    return;
  __sync_fetch_and_or(&sysseg->masters_flags, bit);
  if (bit == MST_F_STALE)
    __sync_fetch_and_add(&sysseg->masters_failed, 1);
  else
    __sync_fetch_and_add(&sysseg->masters_dropped, 1);
}

Private bool mst_sysfile(const char *name, char *out, size_t outsz) {
  if (sysseg == NULL)
    return FALSE;
  return snprintf(out, outsz, "%s%c%s", sysseg->sysdir, DS, name) < (int)outsz;
}

/* the system directory as the OS resolves it, once */
Private const char *mst_sysdir_real(void) {
  static char real[PATH_MAX + 1];
  static bool have = FALSE;

  if (!have) {
    char dir[MAX_PATHNAME_LEN + 1];

    if (sysseg == NULL)
      return NULL;
    snprintf(dir, sizeof(dir), "%s", (const char *)sysseg->sysdir);
    if (realpath(dir, real) == NULL)
      return NULL;
    have = TRUE;
  }
  return real;
}

/* ======================================================================
   The accounts: which directory is whose.  The register is <sysdir>/accounts/<name>, line 1 the path.  The table is read again after a
   minute, and (no oftener than every five seconds) when a path is not found in it, so that an account made after this process began
   is seen.                                                                                                                         */

typedef struct {
  char name[MAX_ACCOUNT_NAME_LEN + 1];
  char root[MAX_PATHNAME_LEN + 1];
  size_t rlen;
} MST_ACC;

/* THE TABLE IS REPLACED BY A READ, AND A READ CAN COME FROM ANY CALL THAT CLASSIFIES A PATH (the hook inside every write, mst_acc_for_path).  So nothing keeps a
   pointer into acc_tab across a call that can write or open a file: mst_acc_by_name gives a COPY, and the loops copy the entry they work on (verifier F2: a pointer
   kept across the inner write read freed memory in the audit line). */
Private MST_ACC *acc_tab = NULL;
Private int *acc_sorted = NULL; /* the indexes of acc_tab in name order (case blind), for a binary search by name */
Private int acc_n = 0;
Private time_t acc_loaded = 0;
Private time_t acc_miss_load = 0;
Private const MST_ACC *mst_acc_ctx = NULL; /* the table being sorted by name (qsort has no argument for it) */

Private int mst_acc_cmp(const void *pa, const void *pb) {
  const MST_ACC *a = (const MST_ACC *)pa;
  const MST_ACC *b = (const MST_ACC *)pb;

  if (a->rlen != b->rlen)
    return (a->rlen > b->rlen) ? -1 : 1; /* the longest root first: the account that holds a path is the nearest one */
  return strcmp(a->name, b->name);
}

Private int mst_acc_idx_cmp(const void *pa, const void *pb) {
  return strcasecmp(mst_acc_ctx[*(const int *)pa].name, mst_acc_ctx[*(const int *)pb].name);
}

Private bool mst_valid_account_name(const char *n) {
  size_t i, len = strlen(n);

  if ((len == 0) || (len > MAX_ACCOUNT_NAME_LEN))
    return FALSE;
  for (i = 0; i < len; i++) {
    unsigned char c = (unsigned char)n[i];

    if (!(((c >= 'a') && (c <= 'z')) || ((c >= 'A') && (c <= 'Z')) || ((c >= '0') && (c <= '9')) || (c == '.') || (c == '_') || (c == '-')))
      return FALSE;
  }
  return TRUE;
}

Private void mst_acc_load(void) {
  char regdir[MAX_PATHNAME_LEN + 1];
  char recpath[MAX_PATHNAME_LEN * 2 + 2];
  char body[4096];
  char root[PATH_MAX + 1];
  DIR *d;
  struct dirent *ent;
  FILE *fp;
  size_t got, n, i;
  char *p;
  MST_ACC *tab = NULL;
  int *idx = NULL;
  int cnt = 0, cap = 0;

  acc_loaded = time(NULL);
  if (!mst_sysfile("accounts", regdir, sizeof(regdir)))
    return;
  if ((d = opendir(regdir)) == NULL)
    return;
  while ((ent = readdir(d)) != NULL) {
    if ((ent->d_name[0] == '.') || (ent->d_name[0] == '%') || (strchr(ent->d_name, '/') != NULL) || !mst_valid_account_name(ent->d_name))
      continue;
    if (snprintf(recpath, sizeof(recpath), "%s%c%s", regdir, DS, ent->d_name) >= (int)sizeof(recpath))
      continue;
    if ((fp = fopen(recpath, "r")) == NULL)
      continue;
    got = fread(body, 1, sizeof(body) - 1, fp);
    fclose(fp);
    body[got] = '\0';
    if ((p = strchr(body, '\n')) != NULL)
      *p = '\0';
    n = strlen(body);
    while ((n > 0) && ((body[n - 1] == '\r') || (body[n - 1] == ' ')))
      body[--n] = '\0';
    if ((body[0] != '/') || (n > PATH_MAX) || (realpath(body, root) == NULL))
      continue;
    n = strlen(root);
    while ((n > 1) && (root[n - 1] == '/'))
      root[--n] = '\0';
    if ((n <= 1) || (n > MAX_PATHNAME_LEN))
      continue;
    if (cnt == cap) {
      MST_ACC *nt;

      cap = (cap == 0) ? 32 : cap * 2;
      nt = (MST_ACC *)realloc(tab, sizeof(MST_ACC) * (size_t)cap);
      if (nt == NULL)
        break;
      tab = nt;
    }
    snprintf(tab[cnt].name, sizeof(tab[cnt].name), "%.*s", MAX_ACCOUNT_NAME_LEN, ent->d_name); /* already checked: at most that long */
    for (i = 0; tab[cnt].name[i] != '\0'; i++)
      tab[cnt].name[i] = (char)tolower((unsigned char)tab[cnt].name[i]);
    snprintf(tab[cnt].root, sizeof(tab[cnt].root), "%.*s", MAX_PATHNAME_LEN, root);                /* and this one too (n above) */
    tab[cnt].rlen = n;
    cnt++;
  }
  closedir(d);
  if (cnt > 1)
    qsort(tab, (size_t)cnt, sizeof(MST_ACC), mst_acc_cmp);
  if (cnt > 0) {
    idx = (int *)malloc(sizeof(int) * (size_t)cnt);
    if (idx != NULL) {
      for (i = 0; i < (size_t)cnt; i++)
        idx[i] = (int)i;
      mst_acc_ctx = tab;
      qsort(idx, (size_t)cnt, sizeof(int), mst_acc_idx_cmp);
    }
  }
  free(acc_tab);
  free(acc_sorted);
  acc_tab = tab;
  acc_sorted = idx; /* NULL when there was no memory or no account: mst_acc_find then looks at every entry */
  acc_n = cnt;
}

/* the index in acc_tab of the account of that name (case blind), or -1 */
Private int mst_acc_find(const char *name) {
  int lo = 0, hi = acc_n - 1, i;

  if (acc_sorted == NULL) {
    for (i = 0; i < acc_n; i++) {
      if (strcasecmp(acc_tab[i].name, name) == 0)
        return i;
    }
    return -1;
  }
  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    int c = strcasecmp(acc_tab[acc_sorted[mid]].name, name);

    if (c == 0)
      return acc_sorted[mid];
    if (c < 0)
      lo = mid + 1;
    else
      hi = mid - 1;
  }
  return -1;
}

Private const MST_ACC *mst_acc_scan_path(const char *canon, const char **rel) {
  int i;

  for (i = 0; i < acc_n; i++) {
    if ((strncmp(canon, acc_tab[i].root, acc_tab[i].rlen) == 0) && ((canon[acc_tab[i].rlen] == '/') || (canon[acc_tab[i].rlen] == '\0'))) {
      *rel = canon + acc_tab[i].rlen + ((canon[acc_tab[i].rlen] == '/') ? 1 : 0);
      return &acc_tab[i];
    }
  }
  return NULL;
}

Private const MST_ACC *mst_acc_for_path(const char *canon, const char **rel) {
  const MST_ACC *a;
  time_t now = time(NULL);

  if ((acc_loaded == 0) || (now < acc_loaded) || ((now - acc_loaded) >= MST_ACC_AGE))
    mst_acc_load();
  a = mst_acc_scan_path(canon, rel);
  if ((a == NULL) && ((acc_miss_load == 0) || (now < acc_miss_load) || ((now - acc_miss_load) >= MST_ACC_MISS))) {
    acc_miss_load = now;
    mst_acc_load();
    a = mst_acc_scan_path(canon, rel);
  }
  return a;
}

/* The account of that name, COPIED into OUT (see the note on acc_tab).  The table is used as it is when it has been read and the name is in it; a name that is not
   in it is looked for again after a fresh read, because the administrator may be naming an account made a moment ago. */
Private bool mst_acc_by_name(const char *name, MST_ACC *out) {
  int pass, i;

  for (pass = 0; pass < 2; pass++) {
    if ((pass == 1) || (acc_loaded == 0))
      mst_acc_load();
    if ((i = mst_acc_find(name)) >= 0) {
      *out = acc_tab[i];
      return TRUE;
    }
  }
  return FALSE;
}

/* ======================================================================
   Classification: is this pathname a VOC or a dictionary of an account?                                                           */

Private int mst_name_kind(const char *path) {
  const char *last = strrchr(path, '/');
  size_t n;

  last = (last == NULL) ? path : last + 1;
  n = strlen(last);
  if ((n == 3) && (strcasecmp(last, "voc") == 0))
    return MST_VOC;
  if ((n > 4) && (strcasecmp(last + n - 4, ".dic") == 0))
    return MST_DICT;
  return 0;
}

/* The account, and the file ("" for the VOC, else the dictionary's path below the account's directory without .dic), of a canonical path.
   A path below a dictionary is that dictionary's.  Not a mirrored place (no account holds it, or the name has an asterisk, or is too long to
   journal): 0.                                                                                                                       */
Private int mst_classify(const char *canon, char *acct, size_t acctsz, char *file, size_t filesz) {
  const MST_ACC *a;
  const char *rel;
  const char *p;
  const char *end;
  size_t n;

  if ((canon == NULL) || (canon[0] != '/'))
    return 0;
  if ((a = mst_acc_for_path(canon, &rel)) == NULL)
    return 0;
  if (snprintf(acct, acctsz, "%s", a->name) >= (int)acctsz)
    return 0;
  file[0] = '\0';
  if ((strcmp(rel, "voc") == 0) || (strncmp(rel, "voc/", 4) == 0))
    return MST_VOC;
  for (p = rel; *p != '\0';) {
    end = strchr(p, '/');
    n = (end == NULL) ? strlen(p) : (size_t)(end - p);
    if ((n > 4) && (strncasecmp(p + n - 4, ".dic", 4) == 0)) {
      size_t flen = (size_t)(p + n - 4 - rel);

      if ((flen == 0) || (flen > MST_FILE_MAX) || (flen >= filesz))
        return 0;
      memcpy(file, rel, flen);
      file[flen] = '\0';
      if (strchr(file, '*') != NULL)
        return 0;
      return MST_DICT;
    }
    if (end == NULL)
      break;
    p = end + 1;
  }
  return 0;
}

/* ======================================================================
   The journal line                                                       */

Private int mst_enc(char *out, size_t outsz, const char *s, int len) {
  int i;
  size_t o = 0;

  if (len == 0) {
    if (outsz < 2)
      return -1;
    out[0] = '-';
    out[1] = '\0';
    return 1;
  }
  for (i = 0; i < len; i++) {
    unsigned char c = (unsigned char)s[i];

    if ((c <= 0x20) || (c == '%') || (c >= 0x7F) || ((i == 0) && (len == 1) && (c == '-'))) {
      if (o + 3 >= outsz)
        return -1;
      snprintf(out + o, outsz - o, "%%%02X", c);
      o += 3;
    } else {
      if (o + 1 >= outsz)
        return -1;
      out[o++] = (char)c;
    }
  }
  out[o] = '\0';
  return (int)o;
}

Private int mst_dec(char *out, size_t outsz, const char *s) {
  size_t o = 0;

  if ((s[0] == '-') && (s[1] == '\0')) {
    out[0] = '\0';
    return 0;
  }
  while (*s != '\0') {
    if (o + 1 >= outsz)
      return -1;
    if ((s[0] == '%') && isxdigit((unsigned char)s[1]) && isxdigit((unsigned char)s[2])) {
      char h[3] = {s[1], s[2], '\0'};

      out[o++] = (char)strtol(h, NULL, 16);
      s += 3;
    } else {
      out[o++] = *s++;
    }
  }
  out[o] = '\0';
  return (int)o;
}

/* The master files exist (a system that has been set up)? */
Private bool mst_masters_present(void) {
  char p[MAX_PATHNAME_LEN + 16];
  struct stat sb;

  if ((sysseg == NULL) || (snprintf(p, sizeof(p), "%s%c%s%c%%0", (const char *)sysseg->sysdir, DS, MST_VOC_MASTER, DS) >= (int)sizeof(p)))
    return FALSE;
  return stat(p, &sb) == 0;
}

/* The journal opened for appending: -1 when it cannot be, and then the flags say why.  This is the FIRST thing the hook does, before it works out whose file
   was written: a system with no master files costs one failed open and nothing else.  A journal that is not there on a system that HAS master files is a
   lost journal (somebody moved it), and every line that would have gone into it is lost: that raises the stale flag like any other failed write.
   Nothing here creates the journal; mst_init does (a file made by a session would be owned by that session's user).                                 */
Private int mst_journal_open(void) {
  char path[MAX_PATHNAME_LEN + 1];
  int fd;

  if (!mst_sysfile(MST_JOURNAL_NAME, path, sizeof(path)))
    return -1;
  fd = open(path, O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0) {
    if ((errno != ENOENT) || mst_masters_present())
      mst_flag(MST_F_STALE);
    return -1;
  }
  return fd;
}

/* One line, one write, to the journal FD that mst_journal_open gave, which this closes.  The caller has the keys; nothing else goes in. */
Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len) {
  char fenc[MST_FILE_MAX * 3 + 4];
  char ienc[256 * 3 + 4];
  char line[1600]; /* at most 10 + 2 + 2 + 33 + 604 + 772 + 6 bytes, under PIPE_BUF, so the append is atomic */
  int len;
  struct stat st;
  bool have_size;

  if ((mst_enc(fenc, sizeof(fenc), file, (int)strlen(file)) < 0) || (mst_enc(ienc, sizeof(ienc), id, id_len) < 0)) {
    close(fd);
    mst_flag(MST_F_STALE);
    return;
  }
  len = snprintf(line, sizeof(line), "%lld %c %c %s %s %s\n", (long long)time(NULL), (kind == MST_VOC) ? 'v' : 'd', op, acct, fenc, ienc);
  if ((len <= 0) || (len >= (int)sizeof(line))) {
    close(fd);
    mst_flag(MST_F_STALE);
    return;
  }
  /* The size test and the append are made under the same semaphore as the drain's truncation (below), so an entry cannot fall between the
     drain's last look at the size and its truncate.  ERRLOG_SEM is the audit file's. */
  StartExclusive(ERRLOG_SEM, 72);
  have_size = (fstat(fd, &st) == 0);
  if (have_size && (st.st_size >= MST_JOURNAL_CAP)) {
    mst_flag(MST_F_RESYNC);
  } else {
    ssize_t w = write(fd, line, (size_t)len);

    if (w != len) {
      /* A short write leaves the front of a line at the end of the journal, and the next line would be glued to it and refused with it.  We hold the semaphore every
         SD appender and the drain's truncation take, so the size we read is still the size: cut back to it. */
      if ((w > 0) && have_size)
        (void)ftruncate(fd, st.st_size);
      mst_flag(MST_F_STALE);
    }
  }
  EndExclusive(ERRLOG_SEM);
  close(fd);
}

/* ======================================================================
   The hook                                                               */

void masters_note_record(DH_FILE *dh, char op, const char *id, int id_len) {
  int kind, fd;
  char acct[MAX_ACCOUNT_NAME_LEN + 1];
  char file[MST_FILE_MAX + 2];

  if ((dh == NULL) || (dh->flags & DHF_MST_NONE))
    return;
  if (!(dh->flags & (DHF_MST_VOC | DHF_MST_DICT))) {
    kind = mst_name_kind((const char *)FPtr(dh->file_id)->pathname);
    if (kind == 0) {
      dh->flags |= DHF_MST_NONE;
      return;
    }
    dh->flags |= (kind == MST_VOC) ? DHF_MST_VOC : DHF_MST_DICT;
  }
  kind = (dh->flags & DHF_MST_VOC) ? MST_VOC : MST_DICT;
  if ((fd = mst_journal_open()) < 0) /* no journal: nothing more to do, and nothing worked out */
    return;
  if (mst_classify((const char *)FPtr(dh->file_id)->pathname, acct, sizeof(acct), file, sizeof(file)) != kind) {
    close(fd);
    return;
  }
  mst_journal_line(fd, kind, op, acct, file, id, id_len);
}

void masters_note_dh(DH_FILE *dh, char op) {
  masters_note_record(dh, op, "", 0);
}

/* A VOC or dictionary file, or something below one, was made, removed, renamed or copied into.  NAME may be relative and need not exist
   (sdrealpath resolves what is there and keeps the rest), so this may be called after a delete. */
void masters_note_name(const char *name, char op) {
  char full[PATH_MAX + 1];
  char acct[MAX_ACCOUNT_NAME_LEN + 1];
  char file[MST_FILE_MAX + 2];
  int kind, fd;

  /* a quick refusal for a name that cannot be, or lie below, a VOC or a dictionary (every name SD makes is lower case) */
  if ((name == NULL) || (name[0] == '\0') || (strlen(name) > MAX_PATHNAME_LEN) || ((strstr(name, ".dic") == NULL) && (strstr(name, "voc") == NULL)))
    return;
  if ((fd = mst_journal_open()) < 0)
    return;
  if (!fullpath(full, (char *)name) || ((kind = mst_classify(full, acct, sizeof(acct), file, sizeof(file))) == 0)) {
    close(fd);
    return;
  }
  mst_journal_line(fd, kind, op, acct, file, "", 0);
}

/* ======================================================================
   The master files                                                       */

typedef struct {
  char path[MAX_PATHNAME_LEN + 1];
  DH_FILE *dh;
  bool absent; /* dh is NULL because there is no such file (as opposed to one that could not be opened) */
} MST_H;

/* the sorted keys of one master, read once (see mst_ctx_index below) */
typedef struct {
  MST_IDS ids;
  MST_SET set;
  bool have;
} MST_INDEX;

typedef struct {
  DH_FILE *vm, *dm, *st; /* the three masters */
  MST_INDEX *ix[3];       /* the sorted keys of voc_master, dict_master and master_state, when the operation is over every account (else NULL) */
  MST_H h[32];            /* account files opened during this operation */
  int nh;
  int rr;                 /* next slot to give up when the cache is full */
  bool last_absent;       /* set by mst_acct_file: a NULL answer meant "no such file", not "could not be opened" */
  long wrote, deleted, same, toolong, errs, files, recs;
} MST_CTX;

Private void mst_index_free(MST_INDEX *ix);

Private DH_FILE *mst_open_path(const char *path) {
  char p[MAX_PATHNAME_LEN + 1];

  if (snprintf(p, sizeof(p), "%s", path) >= (int)sizeof(p))
    return NULL;
  return dh_open(p);
}

Private bool mst_master_path(const char *name, char *out, size_t outsz) {
  return mst_sysfile(name, out, outsz);
}

Private bool mst_ctx_open(MST_CTX *cx) {
  char p[MAX_PATHNAME_LEN + 1];

  memset(cx, 0, sizeof(*cx));
  if (!mst_master_path(MST_VOC_MASTER, p, sizeof(p)) || ((cx->vm = mst_open_path(p)) == NULL))
    goto fail;
  if (!mst_master_path(MST_DICT_MASTER, p, sizeof(p)) || ((cx->dm = mst_open_path(p)) == NULL))
    goto fail;
  if (!mst_master_path(MST_STATE, p, sizeof(p)) || ((cx->st = mst_open_path(p)) == NULL))
    goto fail;
  return TRUE;
fail:
  if (cx->vm != NULL)
    dh_close(cx->vm);
  if (cx->dm != NULL)
    dh_close(cx->dm);
  cx->vm = cx->dm = cx->st = NULL;
  return FALSE;
}

Private void mst_ctx_close(MST_CTX *cx) {
  int i;

  for (i = 0; i < cx->nh; i++) {
    if (cx->h[i].dh != NULL)
      dh_close(cx->h[i].dh);
  }
  cx->nh = 0;
  for (i = 0; i < 3; i++) {
    if (cx->ix[i] != NULL) {
      mst_index_free(cx->ix[i]);
      free(cx->ix[i]);
      cx->ix[i] = NULL;
    }
  }
  if (cx->vm != NULL)
    dh_close(cx->vm);
  if (cx->dm != NULL)
    dh_close(cx->dm);
  if (cx->st != NULL)
    dh_close(cx->st);
  cx->vm = cx->dm = cx->st = NULL;
}

/* Does PATH, as the operating system resolves it, lie inside the directory ROOT (a canonical path, as the account table holds)?  TRUE also when it cannot be resolved
   (nothing there, or no right to look): the caller's own tests say "not there" or "cannot be opened" in those cases.  REAL gets the resolved path when there is one. */
Private bool mst_inside_root(const char *path, const char *root, char *real, size_t realsz) {
  char r[PATH_MAX + 1];
  size_t rl = strlen(root);

  real[0] = '\0';
  if (realpath(path, r) == NULL)
    return TRUE;
  snprintf(real, realsz, "%s", r);
  return (strncmp(r, root, rl) == 0) && (r[rl] == '/');
}

/* An account's VOC or dictionary, opened (or remembered from earlier in this operation).  NULL when it could not be: cx->last_absent then says
   whether that is because THERE IS NO SUCH FILE (the account holds nothing there, and its master copies are to go) or because it exists and could
   not be opened (a permission, a file with an id longer than MAXIDLEN, damage: the master copies are to be LEFT ALONE and the failure counted - a
   copy is never deleted for want of being able to read the original).

   19 Oct 26 (verifier F6): THE ACCOUNT'S FILE IS A FILE IN THE ACCOUNT.  A name.dic (or a voc) that is a link to a place outside the account's directory - another
   account's dictionary, say - is not this account's file: it counts as NOT THERE (so no copy is made of it under this account's keys, and a save to it is refused as
   "the account has no dictionary of that name"), and nothing is opened through it.  After the open the file's device and inode are compared with those of the path as
   it was resolved, so a link put in the place between the test and the open opens nothing.                                                                       */
Private DH_FILE *mst_acct_file(MST_CTX *cx, int kind, const char *root, const char *file) {
  char path[MAX_PATHNAME_LEN + 1];
  char sub[MAX_PATHNAME_LEN + 8];
  char real[PATH_MAX + 1];
  struct stat sb, rs;
  int i;
  DH_FILE *dh = NULL;
  bool absent = FALSE;

  cx->last_absent = FALSE;
  if (kind == MST_VOC) {
    if (snprintf(path, sizeof(path), "%s%cvoc", root, DS) >= (int)sizeof(path))
      return NULL;
  } else {
    if (snprintf(path, sizeof(path), "%s%c%s.dic", root, DS, file) >= (int)sizeof(path))
      return NULL;
  }
  for (i = 0; i < cx->nh; i++) {
    if (strcmp(cx->h[i].path, path) == 0) {
      cx->last_absent = cx->h[i].absent;
      return cx->h[i].dh;
    }
  }
  if (!mst_inside_root(path, root, real, sizeof(real))) {
    absent = TRUE; /* a link out of the account: not the account's file */
  } else {
    dh = mst_open_path(path);
    if ((dh != NULL) && (real[0] != '\0') && (stat(real, &rs) == 0)) {
      FILE_ENTRY *fe = FPtr(dh->file_id);

      if (((fe->device != 0) || (fe->inode != 0)) && ((fe->device != (u_int32_t)rs.st_dev) || (fe->inode != (u_int32_t)rs.st_ino))) {
        dh_close(dh); /* not the file the path resolved to a moment ago: it was changed under us */
        dh = NULL;
      }
    } else if (dh == NULL) {
      absent = (snprintf(sub, sizeof(sub), "%s%c%%0", path, DS) < (int)sizeof(sub)) && (stat(sub, &sb) != 0) && (errno == ENOENT);
    }
  }
  if (cx->nh >= (int)(sizeof(cx->h) / sizeof(cx->h[0]))) {
    i = cx->rr++ % cx->nh;
    if (cx->h[i].dh != NULL)
      dh_close(cx->h[i].dh);
  } else {
    i = cx->nh++;
  }
  snprintf(cx->h[i].path, sizeof(cx->h[i].path), "%s", path);
  cx->h[i].dh = dh;
  cx->h[i].absent = absent;
  cx->last_absent = absent;
  return dh;
}

/* a record's bytes, chunk by chunk */
Private bool mst_str_equal(STRING_CHUNK *a, STRING_CHUNK *b) {
  size_t ai = 0, bi = 0;
  STRING_CHUNK *ca = a, *cb = b;

  for (;;) {
    while ((ca != NULL) && (ai >= (size_t)ca->bytes)) {
      ca = ca->next;
      ai = 0;
    }
    while ((cb != NULL) && (bi >= (size_t)cb->bytes)) {
      cb = cb->next;
      bi = 0;
    }
    if ((ca == NULL) || (cb == NULL))
      return (ca == NULL) && (cb == NULL);
    if (ca->data[ai++] != cb->data[bi++])
      return FALSE;
  }
}

/* FNV-1a, 64 bits, as 16 hex digits */
Private void mst_checksum(STRING_CHUNK *s, char *out) {
  unsigned long long h = 14695981039346656037ULL;
  STRING_CHUNK *c;
  int i;

  for (c = s; c != NULL; c = c->next) {
    for (i = 0; i < c->bytes; i++) {
      h ^= (unsigned char)c->data[i];
      h *= 1099511628211ULL;
    }
  }
  snprintf(out, 17, "%016llx", h);
}

Private long mst_str_len(STRING_CHUNK *s) {
  long n = 0;
  STRING_CHUNK *c;

  for (c = s; c != NULL; c = c->next)
    n += c->bytes;
  return n;
}

/* the master key and the state key of a record; the length of the master key, or -1 when it cannot be mirrored */
Private int mst_keys(int kind, const char *acct, const char *file, const char *id, int id_len, char *mkey, char *skey) {
  int n;
  int limit = sysseg->maxidlen - 2; /* the state key is two characters longer than the master key */

  if (limit > MAX_KEY_LEN - 2)
    limit = MAX_KEY_LEN - 2;
  if (kind == MST_VOC) {
    n = (int)strlen(acct) + 1 + id_len;
    if (n > limit)
      return -1;
    sprintf(mkey, "%s*", acct);
    memcpy(mkey + strlen(acct) + 1, id, (size_t)id_len);
  } else {
    n = (int)strlen(acct) + 1 + (int)strlen(file) + 1 + id_len;
    if (n > limit)
      return -1;
    sprintf(mkey, "%s*%s*", acct, file);
    memcpy(mkey + strlen(mkey), id, (size_t)id_len);
  }
  mkey[n] = '\0';
  skey[0] = (kind == MST_VOC) ? 'v' : 'd';
  skey[1] = '*';
  memcpy(skey + 2, mkey, (size_t)n);
  skey[n + 2] = '\0';
  return n;
}

/* Stage 2.  The stage 1 code writes and deletes records of voc_master and dict_master itself (the drain, the syncs, the drop).  dh_write and dh_delete ask
   masters_before_write / masters_before_delete first, and for a master file that is the question "is this a save by SDSYS?"; mst_inside is how the code
   in this file says "no, it is mine".  It is raised for the ONE call and put back, never across a stretch of code, so that a k_error out of the middle of
   a drain cannot leave it up (it can only be up while dh_write or dh_delete is running). */
Private int mst_inside = 0;

Private bool mst_mwrite(DH_FILE *dh, char *key, int16_t klen, STRING_CHUNK *rec) {
  bool ok;

  mst_inside++;
  ok = dh_write(dh, key, klen, rec);
  mst_inside--;
  return ok;
}

Private bool mst_mdelete(DH_FILE *dh, char *key, int16_t klen) {
  bool ok;

  mst_inside++;
  ok = dh_delete(dh, key, klen);
  mst_inside--;
  return ok;
}

/* write a small record (a state record) from a C buffer */
Private bool mst_put(DH_FILE *dh, const char *key, int klen, const char *data, int dlen) {
  DESCRIPTOR d;
  bool ok;

  k_put_string((char *)data, dlen, &d);
  ok = dh_write(dh, (char *)key, (int16_t)klen, d.data.str.saddr);
  k_release(&d);
  return ok;
}

/* the state record of a key, parsed: the checksum (16 hex digits or empty) */
Private bool mst_state_get(MST_CTX *cx, const char *skey, int sklen, char *cks) {
  STRING_CHUNK *s;
  bool found;
  char buf[128];
  long n;
  STRING_CHUNK *c;
  int i, o = 0;

  cks[0] = '\0';
  s = dh_read(cx->st, (char *)skey, (int16_t)sklen, NULL);
  found = (dh_err == 0);
  if (found && (s != NULL)) {
    n = mst_str_len(s);
    for (c = s; (c != NULL) && (o < (int)sizeof(buf) - 1); c = c->next) {
      for (i = 0; (i < c->bytes) && (o < (int)sizeof(buf) - 1); i++)
        buf[o++] = c->data[i];
    }
    buf[o] = '\0';
    (void)n;
    for (i = 0; (buf[i] != '\0') && (buf[i] != MST_FM) && (i < 16); i++)
      cks[i] = buf[i];
    cks[i] = '\0';
  }
  k_deref_string(s);
  return found;
}

/* ======================================================================
   One key made to match the account                                      */

Private int mst_sync_key(MST_CTX *cx, int kind, const char *acct, const char *root, const char *file, const char *id, int id_len) {
  char mkey[512], skey[520];
  char actual[256];
  int mk;
  DH_FILE *adh, *mdh;
  STRING_CHUNK *rec = NULL, *mrec = NULL;
  bool found = FALSE, mfound;
  int rc;
  char cks[17], scks[17];
  char sv[64];
  int svl;

  memset(actual, 0, sizeof(actual));
  memcpy(actual, id, (size_t)id_len);
  if (mst_keys(kind, acct, file, id, id_len, mkey, skey) < 0) {
    cx->toolong++;
    return MS_LONG;
  }
  adh = mst_acct_file(cx, kind, root, file);
  mdh = (kind == MST_VOC) ? cx->vm : cx->dm;
  if (adh != NULL) {
    rec = dh_read(adh, (char *)id, (int16_t)id_len, actual);
    if (dh_err == 0) {
      found = TRUE;
    } else if (dh_err != DHE_RECORD_NOT_FOUND) {
      cx->errs++;
      return MS_ERR;
    }
  } else if (!cx->last_absent) {
    cx->errs++; /* the file is there and cannot be opened: say nothing about its records, and delete no copy of them */
    return MS_ERR;
  }
  if (found) /* the key as the account stores the id */
    mk = mst_keys(kind, acct, file, actual, id_len, mkey, skey);
  else
    mk = (int)strlen(mkey);

  mrec = dh_read(mdh, mkey, (int16_t)mk, NULL);
  mfound = (dh_err == 0);
  if ((dh_err != 0) && (dh_err != DHE_RECORD_NOT_FOUND)) {
    k_deref_string(rec);
    cx->errs++;
    return MS_ERR;
  }

  if (!found) {
    rc = MS_ABSENT;
    if (mfound) {
      if (!mst_mdelete(mdh, mkey, (int16_t)mk)) {
        cx->errs++;
        rc = MS_ERR;
      } else {
        cx->deleted++;
        rc = MS_DELETED;
      }
    }
    {
      STRING_CHUNK *sr = dh_read(cx->st, skey, (int16_t)(mk + 2), NULL);

      if (dh_err == 0)
        (void)dh_delete(cx->st, skey, (int16_t)(mk + 2));
      k_deref_string(sr);
    }
    k_deref_string(mrec);
    return rc;
  }

  rc = MS_SAME;
  if (!mfound || !mst_str_equal(rec, mrec)) {
    if (!mst_mwrite(mdh, mkey, (int16_t)mk, rec)) {
      cx->errs++;
      k_deref_string(rec);
      k_deref_string(mrec);
      return MS_ERR;
    }
    cx->wrote++;
    rc = MS_WROTE;
  } else {
    cx->same++;
  }
  mst_checksum(rec, cks);
  (void)mst_state_get(cx, skey, mk + 2, scks);
  if (strcmp(cks, scks) != 0) {
    svl = snprintf(sv, sizeof(sv), "%s%c%lld%c", cks, MST_FM, (long long)time(NULL), MST_FM);
    if (!mst_put(cx->st, skey, mk + 2, sv, svl))
      cx->errs++;
  }
  k_deref_string(rec);
  k_deref_string(mrec);
  return rc;
}

/* every id of a hashed file, in a list.  FALSE when the file could not be read through. */
Private bool mst_scan_ids(DH_FILE *dh, MST_IDS *out) {
  FILE_ENTRY *fptr = FPtr(dh->file_id);
  DH_BLOCK *buff = (DH_BLOCK *)(&dh_buffer);
  int32_t group, grp;
  int16_t group_bytes = (int16_t)(dh->group_size);
  int16_t lock_slot, subfile, rec_offset, used_bytes;
  DH_RECORD *rec_ptr;

  while (fptr->file_lock < 0)
    Sleep(1000); /* clearfile in progress, as dh_read waits */
  for (group = 1; group <= fptr->params.modulus; group++) {
    StartExclusive(FILE_TABLE_LOCK, 73);
    lock_slot = GetGroupReadLock(dh, group);
    EndExclusive(FILE_TABLE_LOCK);
    subfile = PRIMARY_SUBFILE;
    grp = group;
    do {
      if (!dh_read_group(dh, subfile, grp, (char *)buff, group_bytes)) {
        FreeGroupReadLock(lock_slot);
        return FALSE;
      }
      used_bytes = buff->used_bytes;
      if ((used_bytes <= 0) || (used_bytes > group_bytes)) {
        FreeGroupReadLock(lock_slot);
        return FALSE;
      }
      rec_offset = offsetof(DH_BLOCK, record);
      while (rec_offset < used_bytes) {
        rec_ptr = (DH_RECORD *)(((char *)buff) + rec_offset);
        if (rec_ptr->next <= 0)
          break;
        if (!mst_ids_add(out, rec_ptr->id, rec_ptr->id_len)) {
          FreeGroupReadLock(lock_slot);
          return FALSE;
        }
        rec_offset += rec_ptr->next;
      }
      subfile = OVERFLOW_SUBFILE;
      grp = GetFwdLink(dh, buff->next);
    } while (grp != 0);
    FreeGroupReadLock(lock_slot);
  }
  return TRUE;
}

/* Master keys of a file, to be matched with what the account holds.  KEYS is a list of whole master keys. */
typedef struct {
  const char *prefix; /* "acct*" or "acct*file*" */
  size_t plen;
  MST_IDS *out;
} MST_FILTER;

Private bool mst_scan_prefixed(DH_FILE *dh, const char *prefix, MST_IDS *out) {
  MST_IDS all = {NULL, 0, 0, 0};
  size_t p, plen = strlen(prefix);
  bool ok = mst_scan_ids(dh, &all);

  for (p = 0; ok && (p < all.len); p += 1 + (size_t)all.d[p]) {
    if ((all.d[p] >= plen) && (strncasecmp((const char *)all.d + p + 1, prefix, plen) == 0)) {
      if (!mst_ids_add(out, (const char *)all.d + p + 1, all.d[p]))
        ok = FALSE;
    }
  }
  mst_ids_free(&all);
  return ok;
}

/* ----------------------------------------------------------------------
   The keys of a master file read ONCE, sorted, so that the keys of one account are found by a binary search (verifier F7).  Every per-account step used to scan the whole
   of voc_master, dict_master and master_state for the keys that begin  account*  - which is quadratic in the number of accounts.  The index is built by the operations
   that visit every account (syncall, check, the drain's whole-file lines) and is NOT kept between operations.  What an account's own sync writes or deletes is that
   account's keys, which no other account looks for, so an index taken before the first account is synced is as good for the last.  The keys are in the order of
   mst_id_cmp, which is the lexicographic order of the folded bytes, so the keys that begin with a prefix are next to each other.                          */

Private bool mst_index_build(DH_FILE *dh, MST_INDEX *ix) {
  memset(ix, 0, sizeof(*ix));
  if (!mst_scan_ids(dh, &ix->ids) || !mst_set_build(&ix->set, &ix->ids)) {
    mst_ids_free(&ix->ids);
    return FALSE;
  }
  ix->have = TRUE;
  return TRUE;
}

Private void mst_index_free(MST_INDEX *ix) {
  if (ix->have)
    mst_set_free(&ix->set);
  mst_ids_free(&ix->ids);
  ix->have = FALSE;
}

/* 0 when KEY begins with PREFIX (case blind); else where it sorts, before (<0) or after (>0) every key that does */
Private int mst_prefix_cmp(const char *key, int klen, const char *prefix, size_t plen) {
  size_t n = ((size_t)klen < plen) ? (size_t)klen : plen, i;

  for (i = 0; i < n; i++) {
    int x = mst_fold((unsigned char)key[i]);
    int y = mst_fold((unsigned char)prefix[i]);

    if (x != y)
      return x - y;
  }
  return ((size_t)klen < plen) ? -1 : 0;
}

/* the keys of the index that begin with PREFIX, added to OUT */
Private bool mst_index_slice(const MST_INDEX *ix, const char *prefix, MST_IDS *out) {
  size_t plen = strlen(prefix);
  int lo = 0, hi = ix->set.n;

  while (lo < hi) { /* the first key that does not sort before the prefix */
    int mid = (lo + hi) / 2;
    size_t o = ix->set.off[mid];

    if (mst_prefix_cmp((const char *)ix->ids.d + o + 1, ix->ids.d[o], prefix, plen) < 0)
      lo = mid + 1;
    else
      hi = mid;
  }
  for (; lo < ix->set.n; lo++) {
    size_t o = ix->set.off[lo];

    if (mst_prefix_cmp((const char *)ix->ids.d + o + 1, ix->ids.d[o], prefix, plen) != 0)
      break;
    if (!mst_ids_add(out, (const char *)ix->ids.d + o + 1, ix->ids.d[o]))
      return FALSE;
  }
  return TRUE;
}

#define MST_IX_VOC 0
#define MST_IX_DICT 1
#define MST_IX_STATE 2

/* Build the indexes of the masters into CX (those that can be built: an operation goes on without one, scanning).  Done once, by an operation over every account.
   WITH_STATE: master_state as well (a check does not read it). */
Private void mst_ctx_index(MST_CTX *cx, bool with_state) {
  DH_FILE *dh[3];
  int i;

  dh[MST_IX_VOC] = cx->vm;
  dh[MST_IX_DICT] = cx->dm;
  dh[MST_IX_STATE] = cx->st;
  for (i = 0; i < (with_state ? 3 : 2); i++) {
    cx->ix[i] = (MST_INDEX *)calloc(1, sizeof(MST_INDEX));
    if ((cx->ix[i] != NULL) && !mst_index_build(dh[i], cx->ix[i])) {
      free(cx->ix[i]);
      cx->ix[i] = NULL;
    }
  }
}

/* the keys of one master that begin with PREFIX: from the index when the operation has one, else by scanning the file.  FALSE when they could not be read. */
Private bool mst_keys_of(MST_CTX *cx, int which, const char *prefix, MST_IDS *out) {
  DH_FILE *dh = (which == MST_IX_VOC) ? cx->vm : ((which == MST_IX_DICT) ? cx->dm : cx->st);

  if ((cx->ix[which] != NULL) && cx->ix[which]->have)
    return mst_index_slice(cx->ix[which], prefix, out);
  return mst_scan_prefixed(dh, prefix, out);
}

Private void mst_delete_keys(MST_CTX *cx, int kind, const MST_IDS *keys) {
  size_t p;
  DH_FILE *mdh = (kind == MST_VOC) ? cx->vm : cx->dm;
  char skey[520];
  const char *k;
  int kl;

  for (p = 0; p < keys->len; p += 1 + (size_t)keys->d[p]) {
    k = (const char *)keys->d + p + 1;
    kl = keys->d[p];
    (void)mst_mdelete(mdh, (char *)k, (int16_t)kl);
    cx->deleted++;
    if (kl + 2 < (int)sizeof(skey)) {
      skey[0] = (kind == MST_VOC) ? 'v' : 'd';
      skey[1] = '*';
      memcpy(skey + 2, k, (size_t)kl);
      (void)dh_delete(cx->st, skey, (int16_t)(kl + 2));
    }
  }
}

/* A whole file made to match: every record of the account's file is synced, and every master key of the scope that the account no longer
   has is removed.  MKEYS: the master keys of the scope (whole keys), PREFIXLEN the length of "acct*" or "acct*file*" in them. */
Private void mst_sync_file(MST_CTX *cx, int kind, const char *acct, const char *root, const char *file, const MST_IDS *mkeys, size_t prefixlen) {
  DH_FILE *adh = mst_acct_file(cx, kind, root, file);
  MST_IDS ids = {NULL, 0, 0, 0};
  MST_IDS gone = {NULL, 0, 0, 0};
  MST_SET set;
  size_t p;
  bool have_set = FALSE;

  bool absent = cx->last_absent; /* read at once: mst_sync_key asks for files too */

  cx->files++;
  if ((adh != NULL) && mst_scan_ids(adh, &ids)) {
    for (p = 0; p < ids.len; p += 1 + (size_t)ids.d[p]) {
      cx->recs++;
      (void)mst_sync_key(cx, kind, acct, root, file, (const char *)ids.d + p + 1, ids.d[p]);
    }
    have_set = mst_set_build(&set, &ids);
  } else if ((adh != NULL) || !absent) {
    cx->errs++; /* could not be opened, or could not be read through: leave the master copies alone */
    mst_ids_free(&ids);
    return;
  } else {
    have_set = mst_set_build(&set, &ids); /* no file: the account holds nothing */
  }
  if (have_set && (mkeys != NULL)) {
    for (p = 0; p < mkeys->len; p += 1 + (size_t)mkeys->d[p]) {
      if (mkeys->d[p] < prefixlen)
        continue;
      if (!mst_set_has(&set, (const char *)mkeys->d + p + 1 + prefixlen, (int)(mkeys->d[p] - prefixlen)))
        (void)mst_ids_add(&gone, (const char *)mkeys->d + p + 1, mkeys->d[p]);
    }
    mst_delete_keys(cx, kind, &gone);
  }
  if (have_set)
    mst_set_free(&set);
  mst_ids_free(&gone);
  mst_ids_free(&ids);
}

/* ======================================================================
   The dictionaries an account holds: its top-level *.dic directories, and those its VOC points at that lie below its directory.      */

Private int mst_cmp_str(const void *a, const void *b) {
  return strcmp(*(char *const *)a, *(char *const *)b);
}

Private void mst_names_add(char ***names, int *n, int *cap, const char *s) {
  int i;
  char **nn;

  for (i = 0; i < *n; i++) {
    if (strcmp((*names)[i], s) == 0)
      return;
  }
  if (*n == *cap) {
    *cap = (*cap == 0) ? 32 : *cap * 2;
    nn = (char **)realloc(*names, sizeof(char *) * (size_t)*cap);
    if (nn == NULL)
      return;
    *names = nn;
  }
  (*names)[*n] = strdup(s);
  if ((*names)[*n] != NULL)
    (*n)++;
}

Private void mst_names_free(char **names, int n) {
  int i;

  for (i = 0; i < n; i++)
    free(names[i]);
  free(names);
}

/* a dictionary file name acceptable as a key part: no asterisk, no control character, no .. component, not absolute */
Private bool mst_file_ok(const char *f) {
  size_t i, n = strlen(f);
  const char *p;

  if ((n == 0) || (n > MST_FILE_MAX) || (f[0] == '/'))
    return FALSE;
  for (i = 0; i < n; i++) {
    if (((unsigned char)f[i] < 33) || ((unsigned char)f[i] > 126) || (f[i] == '*'))
      return FALSE;
  }
  for (p = f; *p != '\0';) {
    const char *e = strchr(p, '/');
    size_t cl = (e == NULL) ? strlen(p) : (size_t)(e - p);

    if ((cl == 0) || ((cl == 1) && (p[0] == '.')) || ((cl == 2) && (p[0] == '.') && (p[1] == '.')))
      return FALSE;
    if (e == NULL)
      break;
    p = e + 1;
  }
  return TRUE;
}

/* The dictionaries the account holds, by name, in NAMES (sorted).  The answer is TRUE only when the list is COMPLETE: the account's directory could be listed and its VOC
   could be read (or there is none).  When it is not, the caller must not take a dictionary's absence from the list to mean the account no longer has it (verifier F5:
   an account whose directory SDSYS could not list lost every dictionary copy, as "files the account no longer has"). */
Private bool mst_account_dicts(MST_CTX *cx, const MST_ACC *a, char ***names, int *n) {
  int cap = 0;
  DIR *d;
  struct dirent *ent;
  char dpath[MAX_PATHNAME_LEN * 2 + 8];
  char p[MAX_PATHNAME_LEN * 2 + 16];
  char lreal[PATH_MAX + 1];
  struct stat sb;
  size_t l;
  DH_FILE *vdh;
  MST_IDS vids = {NULL, 0, 0, 0};
  size_t o;
  char f[MST_FILE_MAX + 8];
  bool complete = TRUE;

  *names = NULL;
  *n = 0;
  if ((d = opendir(a->root)) != NULL) {
    while ((ent = readdir(d)) != NULL) {
      l = strlen(ent->d_name);
      if ((l <= 4) || (strcasecmp(ent->d_name + l - 4, ".dic") != 0))
        continue;
      if (snprintf(dpath, sizeof(dpath), "%s/%s", a->root, ent->d_name) >= (int)sizeof(dpath))
        continue;
      if (snprintf(p, sizeof(p), "%s/%%0", dpath) >= (int)sizeof(p))
        continue;
      if (stat(p, &sb) != 0)
        continue;
      if (!mst_inside_root(dpath, a->root, lreal, sizeof(lreal)))
        continue; /* a link out of the account: another account's dictionary, or nobody's (verifier F6) */
      snprintf(f, sizeof(f), "%.*s", (int)(l - 4), ent->d_name);
      if (mst_file_ok(f))
        mst_names_add(names, n, &cap, f);
    }
    closedir(d);
  } else {
    complete = FALSE;
  }
  /* and those the VOC points at: an F entry whose field 3 is a path that ends .dic below the account's directory */
  vdh = mst_acct_file(cx, MST_VOC, a->root, "");
  if (vdh == NULL) {
    if (!cx->last_absent)
      complete = FALSE; /* the VOC is there and cannot be opened: the dictionaries it names are not known */
  } else if (!mst_scan_ids(vdh, &vids)) {
    complete = FALSE;
  } else {
    for (o = 0; o < vids.len; o += 1 + (size_t)vids.d[o]) {
      STRING_CHUNK *rec = dh_read(vdh, (char *)vids.d + o + 1, vids.d[o], NULL);
      char buf[2 * MAX_PATHNAME_LEN + 8];
      int i, w = 0, field = 1;
      char fld3[MAX_PATHNAME_LEN + 1];
      int f3 = 0;
      char real[PATH_MAX + 1];
      char full[2 * MAX_PATHNAME_LEN + 4];
      STRING_CHUNK *c;

      if ((dh_err != 0) || (rec == NULL)) {
        k_deref_string(rec);
        continue;
      }
      for (c = rec; c != NULL; c = c->next) {
        for (i = 0; i < c->bytes; i++) {
          char ch = c->data[i];

          if (ch == MST_FM) {
            field++;
            if (field > 3)
              break;
            continue;
          }
          if ((field == 1) && (w < (int)sizeof(buf) - 1))
            buf[w++] = ch;
          if ((field == 3) && (f3 < (int)sizeof(fld3) - 1))
            fld3[f3++] = ch;
        }
        if (field > 3)
          break;
      }
      buf[w] = '\0';
      fld3[f3] = '\0';
      k_deref_string(rec);
      if ((w == 0) || (toupper((unsigned char)buf[0]) != 'F') || (f3 <= 4) || (strchr(fld3, '@') != NULL))
        continue;
      if (fld3[0] == '/')
        snprintf(full, sizeof(full), "%s", fld3);
      else
        snprintf(full, sizeof(full), "%s/%s", a->root, fld3);
      if (realpath(full, real) == NULL)
        continue;
      l = strlen(real);
      if ((l <= a->rlen + 5) || (strncmp(real, a->root, a->rlen) != 0) || (real[a->rlen] != '/') || (strcasecmp(real + l - 4, ".dic") != 0))
        continue;
      snprintf(f, sizeof(f), "%.*s", (int)(l - a->rlen - 1 - 4), real + a->rlen + 1);
      if (mst_file_ok(f))
        mst_names_add(names, n, &cap, f);
    }
  }
  mst_ids_free(&vids);
  if (*n > 1)
    qsort(*names, (size_t)*n, sizeof(char *), mst_cmp_str);
  return complete;
}

/* ======================================================================
   An account synced, checked, dropped                                    */

typedef struct {
  long voc, dfiles, drecs, wrote, removed, notmirrored, errs;
} MST_SYNCRES;

Private int mst_file_cmp_prefix(const char *key, int klen, const char *acct, char *filebuf, size_t fsz) {
  /* dictionary key acct*file*id: copy the file part into FILEBUF.  0 when the key has no second asterisk. */
  size_t al = strlen(acct);
  const char *s, *e;

  if ((klen < (int)al + 2) || (strncasecmp(key, acct, al) != 0) || (key[al] != '*'))
    return 0;
  s = key + al + 1;
  e = memchr(s, '*', (size_t)(klen - (int)al - 1));
  if ((e == NULL) || ((size_t)(e - s) >= fsz))
    return 0;
  memcpy(filebuf, s, (size_t)(e - s));
  filebuf[e - s] = '\0';
  return 1;
}

Private bool mst_sync_account(MST_CTX *cx, const MST_ACC *a, MST_SYNCRES *res) {
  char **dn = NULL;
  int dnn = 0, i;
  MST_IDS vkeys = {NULL, 0, 0, 0};
  MST_IDS dkeys = {NULL, 0, 0, 0};
  char prefix[MAX_ACCOUNT_NAME_LEN + 4];
  char sub[MST_FILE_MAX + MAX_ACCOUNT_NAME_LEN + 8];
  long before_wrote = cx->wrote, before_del = cx->deleted, before_long = cx->toolong, before_errs = cx->errs, before_recs = cx->recs;
  size_t p;
  char filebuf[MST_FILE_MAX + 4];
  MST_IDS stale_state = {NULL, 0, 0, 0};
  MST_IDS skeys = {NULL, 0, 0, 0};
  bool dcomplete;

  snprintf(prefix, sizeof(prefix), "%s*", a->name);
  if (!mst_keys_of(cx, MST_IX_VOC, prefix, &vkeys) || !mst_keys_of(cx, MST_IX_DICT, prefix, &dkeys)) {
    cx->errs++;
    mst_ids_free(&vkeys);
    mst_ids_free(&dkeys);
    return FALSE;
  }
  dcomplete = mst_account_dicts(cx, a, &dn, &dnn);
  if (!dcomplete)
    cx->errs++; /* the list of the account's dictionaries is not complete: the pruning below is skipped, and the sync says so */

  /* the VOC */
  mst_sync_file(cx, MST_VOC, a->name, a->root, "", &vkeys, strlen(prefix));
  res->voc = cx->recs - before_recs;
  before_recs = cx->recs;

  /* each dictionary the account holds, with its own slice of the master keys */
  for (i = 0; i < dnn; i++) {
    MST_IDS slice = {NULL, 0, 0, 0};

    snprintf(sub, sizeof(sub), "%s%s*", prefix, dn[i]);
    for (p = 0; p < dkeys.len; p += 1 + (size_t)dkeys.d[p]) {
      if ((dkeys.d[p] >= strlen(sub)) && (strncasecmp((const char *)dkeys.d + p + 1, sub, strlen(sub)) == 0))
        (void)mst_ids_add(&slice, (const char *)dkeys.d + p + 1, dkeys.d[p]);
    }
    mst_sync_file(cx, MST_DICT, a->name, a->root, dn[i], &slice, strlen(sub));
    mst_ids_free(&slice);
  }
  res->dfiles = dnn;
  res->drecs = cx->recs - before_recs;

  /* master keys of dictionary files the account no longer has - but only when the list of its dictionaries is complete (verifier F5) */
  if (dcomplete) {
    MST_IDS gone = {NULL, 0, 0, 0};

    for (p = 0; p < dkeys.len; p += 1 + (size_t)dkeys.d[p]) {
      bool known = FALSE;

      if (mst_file_cmp_prefix((const char *)dkeys.d + p + 1, dkeys.d[p], a->name, filebuf, sizeof(filebuf))) {
        for (i = 0; i < dnn; i++) {
          if (strcasecmp(dn[i], filebuf) == 0) {
            known = TRUE;
            break;
          }
        }
      }
      if (!known)
        (void)mst_ids_add(&gone, (const char *)dkeys.d + p + 1, dkeys.d[p]);
    }
    mst_delete_keys(cx, MST_DICT, &gone);
    mst_ids_free(&gone);
  }

  /* state records that no master key backs */
  snprintf(sub, sizeof(sub), "v*%s*", a->name);
  (void)mst_keys_of(cx, MST_IX_STATE, sub, &skeys);
  snprintf(sub, sizeof(sub), "d*%s*", a->name);
  (void)mst_keys_of(cx, MST_IX_STATE, sub, &skeys);
  for (p = 0; p < skeys.len; p += 1 + (size_t)skeys.d[p]) {
    const char *sk = (const char *)skeys.d + p + 1;
    int sl = skeys.d[p];
    STRING_CHUNK *m;

    m = dh_read((sk[0] == 'v') ? cx->vm : cx->dm, (char *)sk + 2, (int16_t)(sl - 2), NULL);
    if (dh_err == DHE_RECORD_NOT_FOUND) {
      (void)mst_ids_add(&stale_state, sk, sl);
    }
    k_deref_string(m);
  }
  for (p = 0; p < stale_state.len; p += 1 + (size_t)stale_state.d[p])
    (void)dh_delete(cx->st, (char *)stale_state.d + p + 1, stale_state.d[p]);

  res->wrote = cx->wrote - before_wrote;
  res->removed = cx->deleted - before_del;
  res->notmirrored = cx->toolong - before_long;
  res->errs = cx->errs - before_errs;
  mst_names_free(dn, dnn);
  mst_ids_free(&vkeys);
  mst_ids_free(&dkeys);
  mst_ids_free(&skeys);
  mst_ids_free(&stale_state);
  return TRUE;
}

/* drop every master copy of an account (DELETE.ACCOUNT) */
Private long mst_drop_account(MST_CTX *cx, const char *acct) {
  MST_IDS keys = {NULL, 0, 0, 0};
  char prefix[MAX_ACCOUNT_NAME_LEN + 4];
  char sub[MAX_ACCOUNT_NAME_LEN + 8];
  long before = cx->deleted;

  snprintf(prefix, sizeof(prefix), "%s*", acct);
  if (mst_scan_prefixed(cx->vm, prefix, &keys))
    mst_delete_keys(cx, MST_VOC, &keys);
  mst_ids_free(&keys);
  if (mst_scan_prefixed(cx->dm, prefix, &keys))
    mst_delete_keys(cx, MST_DICT, &keys);
  mst_ids_free(&keys);
  snprintf(sub, sizeof(sub), "v*%s*", acct);
  if (mst_scan_prefixed(cx->st, sub, &keys)) {
    size_t p;

    for (p = 0; p < keys.len; p += 1 + (size_t)keys.d[p])
      (void)dh_delete(cx->st, (char *)keys.d + p + 1, keys.d[p]);
  }
  mst_ids_free(&keys);
  snprintf(sub, sizeof(sub), "d*%s*", acct);
  if (mst_scan_prefixed(cx->st, sub, &keys)) {
    size_t p;

    for (p = 0; p < keys.len; p += 1 + (size_t)keys.d[p])
      (void)dh_delete(cx->st, (char *)keys.d + p + 1, keys.d[p]);
  }
  mst_ids_free(&keys);
  return cx->deleted - before;
}

/* Is this name in the register?  The table first, then the register record itself: a record that could not be read into the table (a transient failure)
   is still an account, and its copies are not an orphan's. */
Private bool mst_in_register(const char *name) {
  char p[2 * MAX_PATHNAME_LEN + 8];
  struct stat sb;

  if (mst_acc_find(name) >= 0)
    return TRUE;
  if (!mst_valid_account_name(name) || (sysseg == NULL))
    return FALSE;
  return (snprintf(p, sizeof(p), "%s%caccounts%c%s", (const char *)sysseg->sysdir, DS, DS, name) < (int)sizeof(p)) && (stat(p, &sb) == 0);
}

/* master keys (and state keys) of accounts that are not in the register at all */
Private long mst_drop_orphans(MST_CTX *cx) {
  long total = 0;
  int pass;
  MST_IDS all = {NULL, 0, 0, 0};
  MST_IDS gone = {NULL, 0, 0, 0};
  size_t p;

  mst_acc_load();
  if (acc_n == 0)
    return 0; /* a register that could not be read is not a register with no accounts in it: every copy would be called an orphan */
  for (pass = 0; pass < 3; pass++) {
    DH_FILE *dh = (pass == 0) ? cx->vm : ((pass == 1) ? cx->dm : cx->st);

    if (!mst_scan_ids(dh, &all)) {
      mst_ids_free(&all);
      continue;
    }
    for (p = 0; p < all.len; p += 1 + (size_t)all.d[p]) {
      const char *k = (const char *)all.d + p + 1;
      int kl = all.d[p];
      const char *a = k;
      int al = kl;
      const char *star;
      char name[MAX_ACCOUNT_NAME_LEN + 4];
      bool known;

      if (pass == 2) {
        if ((kl < 4) || (k[1] != '*'))
          continue; /* $journal and any key of no known shape are not orphans */
        a = k + 2; /* the account follows the kind letter and its asterisk */
        al = kl - 2;
      }
      star = memchr(a, '*', (size_t)al);
      if ((star == NULL) || ((size_t)(star - a) > MAX_ACCOUNT_NAME_LEN))
        continue;
      memcpy(name, a, (size_t)(star - a));
      name[star - a] = '\0';
      known = mst_in_register(name);
      if (!known)
        (void)mst_ids_add(&gone, k, all.d[p]);
    }
    for (p = 0; p < gone.len; p += 1 + (size_t)gone.d[p]) {
      (void)mst_mdelete(dh, (char *)gone.d + p + 1, gone.d[p]);
      total++;
    }
    mst_ids_free(&all);
    mst_ids_free(&gone);
  }
  return total;
}

/* ======================================================================
   CHECK: the same walk, read only                                        */

typedef struct {
  MST_BUF rows;
  long nrows, ndiff;
} MST_CHECK;

Private void mst_row(MST_CHECK *ck, const char *type, const char *acct, const char *what, const char *file, const char *id, int id_len) {
  ck->ndiff++;
  if (ck->nrows >= MST_CHECK_ROWS) {
    return;
  }
  ck->nrows++;
  mst_buf_add(&ck->rows, (const char *)&(char){MST_FM}, 1);
  mst_buf_str(&ck->rows, type);
  mst_buf_add(&ck->rows, (const char *)&(char){MST_VM}, 1);
  mst_buf_str(&ck->rows, acct);
  mst_buf_add(&ck->rows, (const char *)&(char){MST_VM}, 1);
  mst_buf_str(&ck->rows, what);
  if ((file != NULL) && (file[0] != '\0')) {
    mst_buf_add(&ck->rows, " ", 1);
    mst_buf_text(&ck->rows, file, (int)strlen(file));
  }
  if (id != NULL) {
    mst_buf_add(&ck->rows, " ", 1);
    mst_buf_text(&ck->rows, id, id_len);
  }
}

/* Is this hashed file - its directory and its two subfiles - writable by its GROUP?  Stage 2 writes a master edit into an account's file as a member of
   the account's group (sdsys joins every account's group, D7), so the mode must say the group may: the directory rwx (775, setgid) and %0 and %1 rw (664). */
Private bool mst_group_writable(const char *dirpath) {
  char p[MAX_PATHNAME_LEN + 8];
  struct stat sb;
  int i;

  if ((stat(dirpath, &sb) != 0) || ((sb.st_mode & (S_IWGRP | S_IXGRP)) != (S_IWGRP | S_IXGRP)))
    return FALSE;
  for (i = 0; i < 2; i++) {
    snprintf(p, sizeof(p), "%s/%%%d", dirpath, i);
    if (stat(p, &sb) != 0)
      return FALSE;
    if (!(sb.st_mode & S_IWGRP))
      return FALSE;
  }
  return TRUE;
}

/* ----------------------------------------------------------------------
   Can THIS process write the hashed file whose directory is DIRPATH, and if it cannot, why not?  The question a master edit has to ask BEFORE it
   changes anything, and the one CHECK.MASTERS asks of every account.  access() answers it (it uses the process's real ids and the groups it was
   STARTED with); the answer to "why" is read off the mode and the group lists:
     MST_W_MODE       the mode itself does not let this process write: the group has no write bit, or this process is the owner and the owner has none
     MST_W_STALE      the group may write, this process is not in the group, but the group's member list in /etc/group names this user: the session
                      began before the user was added, and a session's groups are fixed when it starts (D7: sign on again)
     MST_W_NOTMEMBER  the group may write and the user is not in it at all
     MST_W_NOWRITE    the mode and the groups look right and it still cannot (a mount, an ACL, the directory's search bit)
   It needs write on %0 and %1 and search on the directory; GNAME gets the file's group.                                                  */

#define MST_W_OK 0
#define MST_W_MODE 1
#define MST_W_STALE 2
#define MST_W_NOTMEMBER 3
#define MST_W_NOWRITE 4

Private bool mst_gid_in_groups(gid_t gid) {
  gid_t *list;
  int n, i;
  bool found = FALSE;

  if (getegid() == gid)
    return TRUE;
  if ((n = getgroups(0, NULL)) <= 0)
    return FALSE;
  if ((list = (gid_t *)malloc(sizeof(gid_t) * (size_t)n)) == NULL)
    return FALSE;
  n = getgroups(n, list);
  for (i = 0; i < n; i++) {
    if (list[i] == gid)
      found = TRUE;
  }
  free(list);
  return found;
}

/* does /etc/group (or the passwd file's primary group) say that the user running this process is in the group? */
Private bool mst_user_listed(gid_t gid) {
  struct passwd *pw = getpwuid(geteuid());
  struct group *gr;
  char **m;

  if (pw == NULL)
    return FALSE;
  if (pw->pw_gid == gid)
    return TRUE;
  if ((gr = getgrgid(gid)) == NULL)
    return FALSE;
  for (m = gr->gr_mem; (m != NULL) && (*m != NULL); m++) {
    if (strcmp(*m, pw->pw_name) == 0)
      return TRUE;
  }
  return FALSE;
}

Private int mst_write_why(const struct stat *sb) {
  if (sb->st_uid == geteuid())
    return (sb->st_mode & S_IWUSR) ? MST_W_NOWRITE : MST_W_MODE; /* the owner's class applies to the owner, whatever the group bits say */
  if (!(sb->st_mode & S_IWGRP))
    return MST_W_MODE;
  if (mst_gid_in_groups(sb->st_gid))
    return MST_W_NOWRITE;
  return mst_user_listed(sb->st_gid) ? MST_W_STALE : MST_W_NOTMEMBER;
}

Private int mst_write_check(const char *dirpath, char *gname, size_t gsz) {
  char p[MAX_PATHNAME_LEN + 8];
  struct stat sb;
  struct group *gr;
  int i;

  gname[0] = '\0';
  for (i = 0; i < 3; i++) {
    if (i == 0)
      snprintf(p, sizeof(p), "%s", dirpath);
    else
      snprintf(p, sizeof(p), "%s/%%%d", dirpath, i - 1);
    if (stat(p, &sb) != 0)
      return MST_W_NOWRITE;
    if ((gr = getgrgid(sb.st_gid)) != NULL)
      snprintf(gname, gsz, "%s", gr->gr_name);
    else
      snprintf(gname, gsz, "%u", (unsigned)sb.st_gid);
    if (access(p, (i == 0) ? X_OK : W_OK) != 0)
      return mst_write_why(&sb);
  }
  return MST_W_OK;
}

Private const char *mst_why_word(int why) {
  switch (why) {
    case MST_W_MODE:
      return "mode";
    case MST_W_STALE:
      return "stale-session";
    case MST_W_NOTMEMBER:
      return "not-a-member";
    default:
      return "no-write";
  }
}

Private void mst_check_file(MST_CTX *cx, MST_CHECK *ck, int kind, const char *acct, const char *root, const char *file, const MST_IDS *mkeys, size_t prefixlen) {
  DH_FILE *adh = mst_acct_file(cx, kind, root, file);
  DH_FILE *mdh = (kind == MST_VOC) ? cx->vm : cx->dm;
  MST_IDS ids = {NULL, 0, 0, 0};
  MST_SET set;
  bool have_set;
  size_t p;
  char mkey[512], skey[520];
  char actual[256];
  int mk;
  char path[MAX_PATHNAME_LEN + 8];
  const char *what = (kind == MST_VOC) ? "voc" : "dict";

  if ((adh == NULL) && !cx->last_absent) { /* there, and cannot be opened: nothing can be said about its records */
    mst_row(ck, "unreadable", acct, what, file, NULL, 0);
    return;
  }
  if (adh != NULL) {
    if (!mst_scan_ids(adh, &ids)) {
      mst_row(ck, "unreadable", acct, what, file, NULL, 0);
      mst_ids_free(&ids);
      return;
    }
    if (kind == MST_VOC)
      snprintf(path, sizeof(path), "%s/voc", root);
    else
      snprintf(path, sizeof(path), "%s/%s.dic", root, file);
    /* The group-bit test is for a file SDSYS writes as a MEMBER of the account's group.  The SDSYS account's own files (the master files' dictionaries among them,
       0700 since verifier F1) are the sdsys user's own, written as their owner: for them only the real test below is asked. */
    if (strcasecmp(acct, MST_SYSTEM_ACCOUNT) != 0 && !mst_group_writable(path)) {
      mst_row(ck, "nonwritable", acct, what, file, NULL, 0);
    } else {
      /* the mode is right: can THIS session write it?  (an account made after this session began; a group SDSYS is not in) */
      char gname[64];
      int why = mst_write_check(path, gname, sizeof(gname));

      if (why != MST_W_OK) {
        const char *w = mst_why_word(why);

        mst_row(ck, "norights", acct, what, file, w, (int)strlen(w));
      }
    }
  }
  for (p = 0; p < ids.len; p += 1 + (size_t)ids.d[p]) {
    STRING_CHUNK *rec, *mrec;
    int id_len = ids.d[p];
    const char *id = (const char *)ids.d + p + 1;

    memcpy(actual, id, (size_t)id_len);
    if (mst_keys(kind, acct, file, id, id_len, mkey, skey) < 0) {
      mst_row(ck, "toolong", acct, what, file, id, id_len);
      continue;
    }
    mk = (int)strlen(mkey);
    rec = dh_read(adh, (char *)id, (int16_t)id_len, actual);
    if (dh_err != 0) {
      k_deref_string(rec);
      continue;
    }
    mrec = dh_read(mdh, mkey, (int16_t)mk, NULL);
    if (dh_err == DHE_RECORD_NOT_FOUND)
      mst_row(ck, "missing", acct, what, file, id, id_len);
    else if (dh_err == 0 && !mst_str_equal(rec, mrec))
      mst_row(ck, "differs", acct, what, file, id, id_len);
    k_deref_string(rec);
    k_deref_string(mrec);
  }
  have_set = mst_set_build(&set, &ids);
  if (have_set && (mkeys != NULL)) {
    for (p = 0; p < mkeys->len; p += 1 + (size_t)mkeys->d[p]) {
      if (mkeys->d[p] < prefixlen)
        continue;
      if (!mst_set_has(&set, (const char *)mkeys->d + p + 1 + prefixlen, (int)(mkeys->d[p] - prefixlen)))
        mst_row(ck, "extra", acct, what, file, (const char *)mkeys->d + p + 1 + prefixlen, (int)(mkeys->d[p] - prefixlen));
    }
  }
  if (have_set)
    mst_set_free(&set);
  mst_ids_free(&ids);
}

Private void mst_check_account(MST_CTX *cx, MST_CHECK *ck, const MST_ACC *a) {
  char **dn = NULL;
  int dnn = 0, i;
  MST_IDS vkeys = {NULL, 0, 0, 0};
  MST_IDS dkeys = {NULL, 0, 0, 0};
  char prefix[MAX_ACCOUNT_NAME_LEN + 4];
  char sub[MST_FILE_MAX + MAX_ACCOUNT_NAME_LEN + 8];
  char filebuf[MST_FILE_MAX + 4];
  size_t p;
  bool dcomplete;

  snprintf(prefix, sizeof(prefix), "%s*", a->name);
  if (!mst_keys_of(cx, MST_IX_VOC, prefix, &vkeys) || !mst_keys_of(cx, MST_IX_DICT, prefix, &dkeys)) {
    mst_row(ck, "unreadable", a->name, "master", NULL, NULL, 0);
    mst_ids_free(&vkeys);
    mst_ids_free(&dkeys);
    return;
  }
  dcomplete = mst_account_dicts(cx, a, &dn, &dnn);
  if (!dcomplete)
    mst_row(ck, "unreadable", a->name, "dict", NULL, NULL, 0); /* the list of its dictionaries is not complete: no copy is called extra below */
  mst_check_file(cx, ck, MST_VOC, a->name, a->root, "", &vkeys, strlen(prefix));
  for (i = 0; i < dnn; i++) {
    MST_IDS slice = {NULL, 0, 0, 0};

    snprintf(sub, sizeof(sub), "%s%s*", prefix, dn[i]);
    for (p = 0; p < dkeys.len; p += 1 + (size_t)dkeys.d[p]) {
      if ((dkeys.d[p] >= strlen(sub)) && (strncasecmp((const char *)dkeys.d + p + 1, sub, strlen(sub)) == 0))
        (void)mst_ids_add(&slice, (const char *)dkeys.d + p + 1, dkeys.d[p]);
    }
    mst_check_file(cx, ck, MST_DICT, a->name, a->root, dn[i], &slice, strlen(sub));
    mst_ids_free(&slice);
  }
  for (p = 0; dcomplete && (p < dkeys.len); p += 1 + (size_t)dkeys.d[p]) {
    bool known = FALSE;

    if (mst_file_cmp_prefix((const char *)dkeys.d + p + 1, dkeys.d[p], a->name, filebuf, sizeof(filebuf))) {
      for (i = 0; i < dnn; i++) {
        if (strcasecmp(dn[i], filebuf) == 0) {
          known = TRUE;
          break;
        }
      }
    }
    if (!known)
      mst_row(ck, "extra", a->name, "dict", NULL, (const char *)dkeys.d + p + 1 + strlen(prefix), (int)(dkeys.d[p] - strlen(prefix)));
  }
  mst_names_free(dn, dnn);
  mst_ids_free(&vkeys);
  mst_ids_free(&dkeys);
}

/* master keys whose account is not registered */
Private void mst_check_orphans(MST_CTX *cx, MST_CHECK *ck) {
  int pass;
  MST_IDS all = {NULL, 0, 0, 0};
  size_t p;

  mst_acc_load();
  if (acc_n == 0)
    return; /* as in mst_drop_orphans: an unreadable register is not an empty one */
  for (pass = 0; pass < 2; pass++) {
    DH_FILE *dh = (pass == 0) ? cx->vm : cx->dm;

    if (!mst_scan_ids(dh, &all)) {
      mst_ids_free(&all);
      continue;
    }
    for (p = 0; p < all.len; p += 1 + (size_t)all.d[p]) {
      const char *k = (const char *)all.d + p + 1;
      int kl = all.d[p];
      const char *star = memchr(k, '*', (size_t)kl);
      char name[MAX_ACCOUNT_NAME_LEN + 4];
      bool known;

      if ((star == NULL) || ((size_t)(star - k) > MAX_ACCOUNT_NAME_LEN))
        continue;
      memcpy(name, k, (size_t)(star - k));
      name[star - k] = '\0';
      known = mst_in_register(name);
      if (!known)
        mst_row(ck, "extra", name, (pass == 0) ? "voc" : "dict", NULL, star + 1, (int)(kl - (star - k) - 1));
    }
    mst_ids_free(&all);
  }
}

/* ======================================================================
   The journal, read and drained                                          */

typedef struct {
  char kind, op;
  char acct[MAX_ACCOUNT_NAME_LEN + 1];
  char file[MST_FILE_MAX + 2];
  char id[260];
  int id_len;
} MST_EVT;

Private int mst_parse_line(char *line, MST_EVT *ev) {
  char *f[7];
  int n = 0;
  char *p = line;
  char tmp[MAX_PATHNAME_LEN * 3];

  while ((n < 7) && (p != NULL)) {
    f[n++] = p;
    p = strchr(p, ' ');
    if (p != NULL)
      *p++ = '\0';
  }
  if ((n != 6) || (p != NULL))
    return 0;
  if ((strspn(f[0], "0123456789") != strlen(f[0])) || (f[0][0] == '\0'))
    return 0;
  if (((f[1][0] != 'v') && (f[1][0] != 'd')) || (f[1][1] != '\0'))
    return 0;
  if ((strchr("wdcnx", f[2][0]) == NULL) || (f[2][1] != '\0'))
    return 0;
  if (!mst_valid_account_name(f[3]))
    return 0;
  ev->kind = f[1][0];
  ev->op = f[2][0];
  snprintf(ev->acct, sizeof(ev->acct), "%s", f[3]);
  if (mst_dec(tmp, sizeof(tmp), f[4]) < 0)
    return 0;
  if (strlen(tmp) > MST_FILE_MAX)
    return 0;
  snprintf(ev->file, sizeof(ev->file), "%.*s", MST_FILE_MAX, tmp);
  if ((ev->kind == 'd') && !mst_file_ok(ev->file))
    return 0;
  if ((ev->kind == 'v') && (ev->file[0] != '\0'))
    return 0;
  ev->id_len = mst_dec(tmp, sizeof(tmp), f[5]);
  if ((ev->id_len < 0) || (ev->id_len > 255))
    return 0;
  memcpy(ev->id, tmp, (size_t)ev->id_len);
  ev->id[ev->id_len] = '\0';
  if (((ev->op == 'w') || (ev->op == 'd')) && (ev->id_len == 0))
    return 0;
  return 1;
}

typedef struct {
  long lines, bad, skipped, keys, files, errs;
  long size, offset_before, offset_after;
  int compacted;
} MST_DRAIN;

Private int mst_evt_cmp(const void *pa, const void *pb) {
  const MST_EVT *a = (const MST_EVT *)pa;
  const MST_EVT *b = (const MST_EVT *)pb;
  int c;

  if (a->kind != b->kind)
    return a->kind - b->kind;
  if ((c = strcasecmp(a->acct, b->acct)) != 0)
    return c;
  if ((c = strcasecmp(a->file, b->file)) != 0)
    return c;
  /* file-level lines (c n x) first, so that a key line of a file that is being synced whole can be dropped */
  if (((a->op == 'w') || (a->op == 'd')) != ((b->op == 'w') || (b->op == 'd')))
    return ((a->op == 'w') || (a->op == 'd')) ? 1 : -1;
  return mst_id_cmp(a->id, a->id_len, b->id, b->id_len);
}

/* read the journal state: position and inode */
Private void mst_jstate_get(MST_CTX *cx, long *offset, long *ino, long *total) {
  STRING_CHUNK *s, *c;
  char buf[128];
  int i, o = 0;
  char *f2, *f3, *f4;

  *offset = 0;
  *ino = 0;
  *total = 0;
  s = dh_read(cx->st, MST_STATE_JOURNAL, (int16_t)strlen(MST_STATE_JOURNAL), NULL);
  if ((dh_err == 0) && (s != NULL)) {
    for (c = s; (c != NULL) && (o < (int)sizeof(buf) - 1); c = c->next) {
      for (i = 0; (i < c->bytes) && (o < (int)sizeof(buf) - 1); i++)
        buf[o++] = c->data[i];
    }
    buf[o] = '\0';
    *offset = atol(buf);
    f2 = strchr(buf, MST_FM);
    if (f2 != NULL) {
      *ino = atol(f2 + 1);
      f3 = strchr(f2 + 1, MST_FM);
      if (f3 != NULL) {
        f4 = strchr(f3 + 1, MST_FM);
        if (f4 != NULL)
          *total = atol(f4 + 1);
      }
    }
  }
  k_deref_string(s);
}

Private void mst_jstate_put(MST_CTX *cx, long offset, long ino, long total) {
  char sv[128];
  int l = snprintf(sv, sizeof(sv), "%ld%c%ld%c%lld%c%ld%c", offset, MST_FM, ino, MST_FM, (long long)time(NULL), MST_FM, total, MST_FM);

  if (!mst_put(cx->st, MST_STATE_JOURNAL, (int)strlen(MST_STATE_JOURNAL), sv, l))
    cx->errs++;
}

/* Apply the journal from START (or from where the last drain stopped, when START is negative) to its end. */
Private int mst_drain(MST_CTX *cx, long start, MST_DRAIN *res) {
  char jpath[MAX_PATHNAME_LEN + 1];
  int fd;
  struct stat st;
  long offset, sino, total, n, i;
  long saved_off, saved_ino;
  char *buf;
  ssize_t got;
  MST_EVT *ev = NULL;
  long nev = 0, evcap = 0;
  long consumed;
  bool can_write = TRUE;
  char *lstart, *nl;

  memset(res, 0, sizeof(*res));
  if (!mst_sysfile(MST_JOURNAL_NAME, jpath, sizeof(jpath)))
    return MSA_NOTSET;
  fd = open(jpath, O_RDWR | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0) {
    if (errno == ENOENT)
      return MSA_NOTSET;
    can_write = FALSE;
    fd = open(jpath, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0)
      return MSA_ERR;
  }
  if (flock(fd, LOCK_EX) != 0) {
    close(fd);
    return MSA_ERR;
  }
  if (fstat(fd, &st) != 0) {
    close(fd);
    return MSA_ERR;
  }
  mst_jstate_get(cx, &offset, &sino, &total);
  saved_off = offset;
  saved_ino = sino;
  if ((sino != (long)st.st_ino) || (offset > (long)st.st_size) || (offset < 0))
    offset = 0;
  if (start >= 0)
    offset = (start > (long)st.st_size) ? (long)st.st_size : start;
  res->size = (long)st.st_size;
  res->offset_before = offset;
  n = (long)st.st_size - offset;
  if (n > MST_READ_MAX)
    n = MST_READ_MAX;
  consumed = offset;
  if (n > 0) {
    buf = (char *)malloc((size_t)n + 1);
    if (buf == NULL) {
      flock(fd, LOCK_UN);
      close(fd);
      return MSA_ERR;
    }
    got = pread(fd, buf, (size_t)n, offset);
    if (got < 0)
      got = 0;
    buf[got] = '\0';
    /* only whole lines */
    lstart = buf;
    while ((lstart < buf + got) && ((nl = memchr(lstart, '\n', (size_t)(buf + got - lstart))) != NULL)) {
      *nl = '\0';
      consumed += (long)(nl - lstart) + 1;
      res->lines++;
      if (lstart[0] != '\0') {
        MST_EVT e;

        if (mst_parse_line(lstart, &e)) {
          if (nev == evcap) {
            MST_EVT *ne;

            evcap = (evcap == 0) ? 1024 : evcap * 2;
            ne = (MST_EVT *)realloc(ev, sizeof(MST_EVT) * (size_t)evcap);
            if (ne == NULL)
              break;
            ev = ne;
          }
          ev[nev++] = e;
        } else {
          res->bad++;
        }
      } else {
        res->bad++;
      }
      lstart = nl + 1;
    }
    free(buf);
  }

  /* the registered accounts only */
  mst_acc_load();
  {
    long keep = 0;

    for (i = 0; i < nev; i++) {
      if (mst_acc_find(ev[i].acct) >= 0)
        ev[keep++] = ev[i];
      else
        res->skipped++;
    }
    nev = keep;
  }
  if (nev > 1)
    qsort(ev, (size_t)nev, sizeof(MST_EVT), mst_evt_cmp);

  /* the master keys of every file that is to be synced whole, found with one scan of each master (an index, so that each file's keys are found by a search) */
  {
    MST_INDEX vall, dall;
    bool need_v = FALSE, need_d = FALSE, have_v = FALSE, have_d = FALSE;
    long j;

    for (i = 0; i < nev; i++) {
      if ((ev[i].op == 'w') || (ev[i].op == 'd'))
        continue;
      if (ev[i].kind == 'v')
        need_v = TRUE;
      else
        need_d = TRUE;
    }
    if (need_v && !(have_v = mst_index_build(cx->vm, &vall)))
      cx->errs++;
    if (need_d && !(have_d = mst_index_build(cx->dm, &dall)))
      cx->errs++;

    for (i = 0; i < nev;) {
      MST_EVT *e = &ev[i];
      bool filelevel = (e->op != 'w') && (e->op != 'd');
      MST_ACC acc; /* a copy: see the note on acc_tab */
      const MST_ACC *a = mst_acc_by_name(e->acct, &acc) ? &acc : NULL;
      int kind = (e->kind == 'v') ? MST_VOC : MST_DICT;

      if (a == NULL) {
        res->skipped++;
        i++;
        continue;
      }
      if (filelevel) {
        MST_IDS slice = {NULL, 0, 0, 0};
        char sub[MST_FILE_MAX + MAX_ACCOUNT_NAME_LEN + 8];

        if (kind == MST_VOC)
          snprintf(sub, sizeof(sub), "%s*", a->name);
        else
          snprintf(sub, sizeof(sub), "%s*%s*", a->name, e->file);
        if ((kind == MST_VOC) ? have_v : have_d)
          (void)mst_index_slice((kind == MST_VOC) ? &vall : &dall, sub, &slice);
        mst_sync_file(cx, kind, a->name, a->root, e->file, &slice, strlen(sub));
        mst_ids_free(&slice);
        res->files++;
        /* skip every other line of the same file: the whole file has been made to match, whatever they said */
        for (j = i + 1; (j < nev) && (ev[j].kind == e->kind) && (strcasecmp(ev[j].acct, e->acct) == 0) && (strcasecmp(ev[j].file, e->file) == 0); j++) {
        }
        i = j;
      } else {
        /* the file-level lines sort first, so a file synced whole was skipped over above; a key line here is for a file not synced whole */
        long k = i;

        (void)mst_sync_key(cx, kind, a->name, a->root, e->file, e->id, e->id_len);
        res->keys++;
        /* identical neighbours (same key) are one key */
        while ((k + 1 < nev) && (ev[k + 1].kind == e->kind) && (strcasecmp(ev[k + 1].acct, e->acct) == 0) && (strcasecmp(ev[k + 1].file, e->file) == 0) &&
               ((ev[k + 1].op == 'w') || (ev[k + 1].op == 'd')) && (mst_id_cmp(ev[k + 1].id, ev[k + 1].id_len, e->id, e->id_len) == 0))
          k++;
        i = k + 1;
      }
    }
    if (have_v)
      mst_index_free(&vall);
    if (have_d)
      mst_index_free(&dall);
  }
  free(ev);
  res->errs = cx->errs;

  /* position, and the truncation when everything up to the end has been taken */
  res->offset_after = consumed;
  if (can_write && (consumed > 0) && (consumed == (long)st.st_size)) {
    StartExclusive(ERRLOG_SEM, 74);
    if ((fstat(fd, &st) == 0) && ((long)st.st_size == consumed) && (ftruncate(fd, 0) == 0)) {
      res->offset_after = 0;
      res->compacted = 1;
    }
    EndExclusive(ERRLOG_SEM);
  } else if (can_write && (consumed < (long)st.st_size)) {
    /* The journal ends in a line with no newline (a writer that died half way, or one forged: the file is group-writable by every SD user so that they can
       append).  The next appended line would be glued to it and both refused, and a legitimate change would be lost from the journal.  End the line: it is then a
       line of its own, refused by the next drain.  Under the semaphore every SD appender takes, so no line is being written as we look. */
    StartExclusive(ERRLOG_SEM, 74);
    if ((fstat(fd, &st) == 0) && ((long)st.st_size > consumed)) {
      char last = '\n';

      if ((pread(fd, &last, 1, st.st_size - 1) == 1) && (last != '\n'))
        (void)pwrite(fd, "\n", 1, st.st_size);
    }
    EndExclusive(ERRLOG_SEM);
  }
  /* The position is written only when it, the journal or the count moved: a drain that found nothing changes no byte of master_state (CHECK.MASTERS,
     which drains first, is read only because of this) */
  if ((res->offset_after != saved_off) || ((long)st.st_ino != saved_ino) || (res->keys + res->files > 0))
    mst_jstate_put(cx, res->offset_after, (long)st.st_ino, total + res->keys + res->files);
  flock(fd, LOCK_UN);
  close(fd);
  return MSA_OK;
}

/* ======================================================================
   The open hook                                                          */

/* Which master file is this canonical path: 1 voc_master, 2 dict_master, 3 master_state, 0 none of them */
Private int mst_master_which(const char *canon) {
  static char vm[PATH_MAX + 16], dm[PATH_MAX + 16], st[PATH_MAX + 16];
  static bool have = FALSE;
  char tmp[PATH_MAX + 16];
  size_t n;
  const char *real;

  if (!have) {
    real = mst_sysdir_real();
    if (real == NULL)
      return 0;
    snprintf(vm, sizeof(vm), "%s/%s", real, MST_VOC_MASTER);
    snprintf(dm, sizeof(dm), "%s/%s", real, MST_DICT_MASTER);
    snprintf(st, sizeof(st), "%s/%s", real, MST_STATE);
    have = TRUE;
  }
  snprintf(tmp, sizeof(tmp), "%s", canon);
  n = strlen(tmp);
  while ((n > 1) && (tmp[n - 1] == '/'))
    tmp[--n] = '\0';
  if (strcmp(tmp, vm) == 0)
    return 1;
  if (strcmp(tmp, dm) == 0)
    return 2;
  if (strcmp(tmp, st) == 0)
    return 3;
  return 0;
}

Private bool mst_is_master_path(const char *canon) {
  return mst_master_which(canon) != 0;
}

void masters_open_hook(const char *canon) {
  static bool busy = FALSE;
  MST_CTX cx;
  MST_DRAIN dr;

  if (busy || (my_uptr == NULL) || !(my_uptr->flags & USR_ADMIN) || (canon == NULL) || !mst_is_master_path(canon))
    return;
  busy = TRUE;
  if (mst_ctx_open(&cx)) {
    (void)mst_drain(&cx, -1, &dr);
    mst_ctx_close(&cx);
  }
  busy = FALSE;
}

/* ======================================================================
   K_MASTERS: the administrator's ops                                     */

Private void mst_answer(DESCRIPTOR *result, MST_BUF *b) {
  if (b->oom || (b->b == NULL)) {
    k_put_c_string("5", result);
  } else {
    k_put_string(b->b, (int)b->len, result);
  }
  mst_buf_free(b);
}

Private void mst_status(MST_BUF *b, int st) {
  mst_buf_num(b, st);
}

Private void mst_fld(MST_BUF *b, long v) {
  mst_buf_add(b, (const char *)&(char){MST_FM}, 1);
  mst_buf_num(b, v);
}

Private void mst_fld_s(MST_BUF *b, const char *s) {
  mst_buf_add(b, (const char *)&(char){MST_FM}, 1);
  mst_buf_str(b, s);
}

/* a number after a value mark, inside a field */
Private void mst_vm_num(MST_BUF *b, long v) {
  mst_buf_add(b, (const char *)&(char){MST_VM}, 1);
  mst_buf_num(b, v);
}

/* A copy of the whole table of accounts, read afresh, for an operation that goes through every account (the caller frees it).  A copy, because the table is replaced
   whenever anything in the process classifies a path (see the note on acc_tab).  NULL when there is no account or no memory. */
Private MST_ACC *mst_acc_snapshot(int *n) {
  MST_ACC *c;

  *n = 0;
  mst_acc_load();
  if (acc_n <= 0)
    return NULL;
  c = (MST_ACC *)malloc(sizeof(MST_ACC) * (size_t)acc_n);
  if (c == NULL)
    return NULL;
  memcpy(c, acc_tab, sizeof(MST_ACC) * (size_t)acc_n);
  *n = acc_n;
  return c;
}

/* the set-up state: the journal and the three masters are there */
Private bool mst_is_set_up(void) {
  char p[MAX_PATHNAME_LEN + 1];
  struct stat sb;
  const char *names[3] = {MST_VOC_MASTER, MST_DICT_MASTER, MST_STATE};
  int i;

  if (!mst_sysfile(MST_JOURNAL_NAME, p, sizeof(p)) || (lstat(p, &sb) != 0) || !S_ISREG(sb.st_mode))
    return FALSE;
  for (i = 0; i < 3; i++) {
    char q[MAX_PATHNAME_LEN + 8];

    if (!mst_sysfile(names[i], p, sizeof(p)))
      return FALSE;
    snprintf(q, sizeof(q), "%s/%%0", p);
    if (stat(q, &sb) != 0)
      return FALSE;
  }
  return TRUE;
}

/* make the journal, and set the modes of the journal and the master files; what was done, as text */
Private void mst_init(MST_BUF *out) {
  char p[MAX_PATHNAME_LEN + 1];
  char q[MAX_PATHNAME_LEN + 16];
  int fd;
  struct stat sb;
  uid_t want_uid = (uid_t)-1;
  gid_t sdusers_gid = (gid_t)-1, sys_gid = (gid_t)-1;
  struct passwd *pw;
  struct group *gr;
  const char *names[3] = {MST_VOC_MASTER, MST_DICT_MASTER, MST_STATE};
  int i, j;
  long modes = 0;

  if ((pw = getpwnam("sdsys")) != NULL) {
    want_uid = pw->pw_uid;
    sys_gid = pw->pw_gid; /* the sdsys user's own group.  (There is NO group called sdsys: asking for one gave -1 and the files kept the group of the process that made them.) */
  }
  if ((gr = getgrnam("sdusers")) != NULL)
    sdusers_gid = gr->gr_gid;

  if (!mst_sysfile(MST_JOURNAL_NAME, p, sizeof(p))) {
    mst_buf_str(out, "nojournalpath");
    return;
  }
  if (lstat(p, &sb) == 0) {
    mst_buf_str(out, S_ISREG(sb.st_mode) ? "journal=exists" : "journal=notafile");
    if (!S_ISREG(sb.st_mode))
      return;
    fd = open(p, O_RDWR | O_NOFOLLOW | O_CLOEXEC);
  } else {
    fd = open(p, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0620);
    mst_buf_str(out, (fd >= 0) ? "journal=created" : "journal=failed");
  }
  if (fd >= 0) {
    (void)fchmod(fd, 0620);
    if (getuid() == 0)
      (void)fchown(fd, want_uid, sdusers_gid);
    else if (sdusers_gid != (gid_t)-1)
      (void)fchown(fd, (uid_t)-1, sdusers_gid);
    close(fd);
    modes++;
  }
  /* The master files and their dictionaries: THE SDSYS USER ALONE (verifier F1).  They hold every account's Q-pointer paths and I-types, and nothing but the
     administrator's session may read them: no group bit and no other bit, whatever group the process that made them was in (an SDSYS session is in sdusers, which
     every SD user is in - the group these files used to get, with group rwx).  Root bypasses the mode, and the installer's root session hands them to sdsys. */
  for (i = 0; i < 3; i++) {
    for (j = 0; j < 2; j++) {
      char dirpath[MAX_PATHNAME_LEN + 16];
      int k;

      if (!mst_sysfile(names[i], p, sizeof(p)))
        continue;
      snprintf(dirpath, sizeof(dirpath), "%s%s", p, (j == 0) ? "" : ".dic");
      if (stat(dirpath, &sb) != 0)
        continue;
      if (chmod(dirpath, 0700) == 0)
        modes++;
      if (getuid() == 0)
        (void)chown(dirpath, want_uid, sys_gid);
      for (k = 0; k < 2; k++) {
        if (snprintf(q, sizeof(q), "%s/%%%d", dirpath, k) >= (int)sizeof(q))
          continue;
        if (stat(q, &sb) != 0)
          continue;
        if (chmod(q, 0600) == 0)
          modes++;
        if (getuid() == 0)
          (void)chown(q, want_uid, sys_gid);
      }
    }
  }
  mst_buf_str(out, " modes=");
  mst_buf_num(out, modes);
}

/* the number of lines waiting, and the journal's size and position */
Private int mst_pending(MST_CTX *cx, long *size, long *offset, long *entries, long *total) {
  char jp[MAX_PATHNAME_LEN + 1];
  struct stat st;
  long ino, n;
  int fd;
  char *buf;
  ssize_t got;
  long i;

  *size = *offset = *entries = *total = 0;
  if (!mst_sysfile(MST_JOURNAL_NAME, jp, sizeof(jp)) || (stat(jp, &st) != 0))
    return MSA_NOTSET;
  *size = (long)st.st_size;
  mst_jstate_get(cx, offset, &ino, total);
  if ((ino != (long)st.st_ino) || (*offset > *size))
    *offset = 0;
  n = *size - *offset;
  if (n > MST_READ_MAX)
    n = MST_READ_MAX;
  if (n <= 0)
    return MSA_OK;
  fd = open(jp, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0)
    return MSA_ERR;
  buf = (char *)malloc((size_t)n);
  if (buf == NULL) {
    close(fd);
    return MSA_ERR;
  }
  got = pread(fd, buf, (size_t)n, *offset);
  for (i = 0; i < got; i++) {
    if (buf[i] == '\n')
      (*entries)++;
  }
  free(buf);
  close(fd);
  return MSA_OK;
}

Private void mst_peek(MST_CTX *cx, long maxlines, MST_BUF *out) {
  char jp[MAX_PATHNAME_LEN + 1];
  struct stat st;
  long ino, offset, total, n, lines = 0;
  int fd;
  char *buf, *s, *nl;
  ssize_t got;

  if (!mst_sysfile(MST_JOURNAL_NAME, jp, sizeof(jp)) || (stat(jp, &st) != 0))
    return;
  mst_jstate_get(cx, &offset, &ino, &total);
  if ((ino != (long)st.st_ino) || (offset > (long)st.st_size))
    offset = 0;
  n = (long)st.st_size - offset;
  if (n > 1024 * 1024)
    n = 1024 * 1024;
  if (n <= 0)
    return;
  fd = open(jp, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0)
    return;
  buf = (char *)malloc((size_t)n + 1);
  if (buf == NULL) {
    close(fd);
    return;
  }
  got = pread(fd, buf, (size_t)n, offset);
  if (got < 0)
    got = 0;
  buf[got] = '\0';
  s = buf;
  while ((lines < maxlines) && (s < buf + got) && ((nl = memchr(s, '\n', (size_t)(buf + got - s))) != NULL)) {
    *nl = '\0';
    mst_buf_add(out, (const char *)&(char){MST_FM}, 1);
    mst_buf_text(out, s, (int)(nl - s));
    lines++;
    s = nl + 1;
  }
  free(buf);
  close(fd);
}

/* One request: OP then FM then the argument.  The answer is a string whose first field is the status. */
void masters_request(const char *req, DESCRIPTOR *result) {
  char op[32];
  const char *arg = "";
  const char *fm;
  MST_BUF out = {NULL, 0, 0, FALSE};
  MST_CTX cx;
  bool admin = (my_uptr != NULL) && ((my_uptr->flags & USR_ADMIN) != 0);

  fm = strchr(req, MST_FM);
  if (fm != NULL) {
    size_t l = (size_t)(fm - req);

    if (l >= sizeof(op))
      l = sizeof(op) - 1;
    memcpy(op, req, l);
    op[l] = '\0';
    arg = fm + 1;
  } else {
    snprintf(op, sizeof(op), "%s", req);
  }

  /* "ready" is the one question any $internal program may ask; "note" adds a journal line for a path and is what !OSCOPY uses */
  if (strcmp(op, "ready") == 0) {
    mst_status(&out, MSA_OK);
    mst_fld(&out, mst_is_set_up() ? 1 : 0);
    mst_answer(result, &out);
    return;
  }
  if (strcmp(op, "note") == 0) {
    masters_note_name(arg, 'n');
    mst_status(&out, MSA_OK);
    mst_answer(result, &out);
    return;
  }
  if (!admin) {
    mst_status(&out, MSA_REFUSED);
    mst_answer(result, &out);
    return;
  }

  /* 19 Oct 26 stage 2: why the last save of a master record in THIS session was refused (empty when it was not, or none was made).  An editor that
     catches the refusal as a bare "write error 8910" (ED does) asks for the sentence; the verbs check.masters and list.master.pending print it. */
  if (strcmp(op, "refusal") == 0) {
    mst_status(&out, MSA_OK);
    mst_fld_s(&out, masters_refusal_text());
    mst_answer(result, &out);
    return;
  }

  if (strcmp(op, "init") == 0) {
    mst_status(&out, MSA_OK);
    mst_buf_add(&out, (const char *)&(char){MST_FM}, 1);
    mst_init(&out);
    mst_answer(result, &out);
    return;
  }

  if (!mst_is_set_up()) {
    mst_status(&out, MSA_NOTSET);
    mst_answer(result, &out);
    return;
  }
  if (!mst_ctx_open(&cx)) {
    mst_status(&out, MSA_ERR);
    mst_fld_s(&out, "master files cannot be opened");
    mst_answer(result, &out);
    return;
  }

  if (strcmp(op, "pending") == 0) {
    long size, offset, entries, total;
    unsigned flags = sysseg->masters_flags;

    (void)mst_pending(&cx, &size, &offset, &entries, &total);
    mst_status(&out, MSA_OK);
    mst_fld(&out, size);
    mst_fld(&out, offset);
    mst_fld(&out, entries);
    mst_fld(&out, (long)flags);
    mst_fld(&out, (long)sysseg->masters_failed);
    mst_fld(&out, total);
    mst_fld(&out, (long)sysseg->masters_dropped);
  } else if (strcmp(op, "peek") == 0) {
    mst_status(&out, MSA_OK);
    mst_peek(&cx, atol(arg) > 0 ? atol(arg) : 20, &out);
  } else if (strcmp(op, "drain") == 0) {
    MST_DRAIN dr;
    int rc = mst_drain(&cx, -1, &dr);

    mst_status(&out, rc);
    mst_fld(&out, dr.lines);
    mst_fld(&out, dr.keys);
    mst_fld(&out, dr.files);
    mst_fld(&out, dr.errs);
    mst_fld(&out, dr.bad + dr.skipped);
    mst_fld(&out, dr.compacted);
  } else if (strcmp(op, "sync") == 0) {
    MST_ACC acc;
    MST_SYNCRES r;

    if (!mst_acc_by_name(arg, &acc)) {
      mst_status(&out, MSA_NOACC);
    } else {
      memset(&r, 0, sizeof(r));
      (void)mst_sync_account(&cx, &acc, &r);
      mst_status(&out, MSA_OK);
      mst_fld(&out, r.voc);
      mst_fld(&out, r.dfiles);
      mst_fld(&out, r.drecs);
      mst_fld(&out, r.wrote);
      mst_fld(&out, r.removed);
      mst_fld(&out, r.notmirrored);
      mst_fld(&out, r.errs);
    }
  } else if (strcmp(op, "syncall") == 0) {
    /* Every registered account in ONE call (verifier F7): each master file is read once, into an index, and each account's keys are found in it.  One field per
       account, in the order of "accounts": its name, then the seven numbers "sync" gives, separated by value marks. */
    int n = 0, i;
    MST_ACC *all = mst_acc_snapshot(&n);

    mst_status(&out, MSA_OK);
    if (all != NULL) {
      mst_ctx_index(&cx, TRUE);
      for (i = 0; i < n; i++) {
        MST_SYNCRES r;

        memset(&r, 0, sizeof(r));
        (void)mst_sync_account(&cx, &all[i], &r);
        mst_buf_add(&out, (const char *)&(char){MST_FM}, 1);
        mst_buf_str(&out, all[i].name);
        mst_vm_num(&out, r.voc);
        mst_vm_num(&out, r.dfiles);
        mst_vm_num(&out, r.drecs);
        mst_vm_num(&out, r.wrote);
        mst_vm_num(&out, r.removed);
        mst_vm_num(&out, r.notmirrored);
        mst_vm_num(&out, r.errs);
      }
      free(all);
    }
  } else if (strcmp(op, "syncbegin") == 0) {
    char jp[MAX_PATHNAME_LEN + 1];
    struct stat st;
    long size = 0;

    /* the position to drain from at the end, and the flags down: a failure from here on sets them again */
    if (mst_sysfile(MST_JOURNAL_NAME, jp, sizeof(jp)) && (stat(jp, &st) == 0))
      size = (long)st.st_size;
    __sync_fetch_and_and(&sysseg->masters_flags, (u_int16_t)~(MST_F_STALE | MST_F_RESYNC));
    mst_status(&out, MSA_OK);
    mst_fld(&out, size);
  } else if (strcmp(op, "syncend") == 0) {
    MST_DRAIN dr;
    long dropped = mst_drop_orphans(&cx);
    int rc = mst_drain(&cx, atol(arg), &dr);

    mst_status(&out, rc);
    mst_fld(&out, dr.keys);
    mst_fld(&out, dr.files);
    mst_fld(&out, dropped);
    mst_fld(&out, dr.errs);
  } else if (strcmp(op, "drop") == 0) {
    mst_status(&out, MSA_OK);
    mst_fld(&out, mst_drop_account(&cx, arg));
  } else if (strcmp(op, "check") == 0) {
    MST_CHECK ck;
    long accounts = 0;
    int i;

    memset(&ck, 0, sizeof(ck));
    mst_acc_load();
    if (arg[0] != '\0') {
      MST_ACC acc;

      if (!mst_acc_by_name(arg, &acc)) {
        mst_status(&out, MSA_NOACC);
        mst_ctx_close(&cx);
        mst_answer(result, &out);
        return;
      }
      mst_check_account(&cx, &ck, &acc);
      accounts = 1;
    } else {
      int n = 0;
      MST_ACC *all = mst_acc_snapshot(&n);

      if (all != NULL) {
        mst_ctx_index(&cx, FALSE); /* each master read once, not once per account (verifier F7) */
        for (i = 0; i < n; i++) {
          mst_check_account(&cx, &ck, &all[i]);
          accounts++;
        }
        free(all);
      }
      mst_check_orphans(&cx, &ck);
    }
    mst_status(&out, MSA_OK);
    mst_fld(&out, accounts);
    mst_fld(&out, ck.ndiff);
    mst_fld(&out, (long)sysseg->masters_flags);
    mst_fld(&out, (long)sysseg->masters_failed);
    mst_fld(&out, (long)sysseg->masters_dropped);
    if (ck.rows.b != NULL)
      mst_buf_add(&out, ck.rows.b, ck.rows.len);
    if (ck.ndiff > ck.nrows) {
      mst_buf_add(&out, (const char *)&(char){MST_FM}, 1);
      mst_buf_str(&out, "truncated");
    }
    mst_buf_free(&ck.rows);
  } else if (strcmp(op, "accounts") == 0) {
    int i;

    mst_acc_load();
    mst_status(&out, MSA_OK);
    for (i = 0; i < acc_n; i++)
      mst_fld_s(&out, acc_tab[i].name);
  } else {
    mst_status(&out, MSA_ARGS);
  }
  mst_ctx_close(&cx);
  mst_answer(result, &out);
}

/* ======================================================================
   MASTER TO ACCOUNT (stage 2, D7)                                        */

/* The reason for the last refusal, as a sentence: set by mst_refuse(), read by op_write and op_delete (masters_refusal_text) */
Private char mst_refusal_buf[1400];

/* Messages 11580 to 11592, 11595 and 11596 are written for C: printf's %s where the arguments go, three at most (test-masters-units.py holds them to that, and to
   the room k_error gives a message: 231 characters once the arguments are in). */
#define MSG_BADKEY 11580
#define MSG_NOACCOUNT 11581
#define MSG_NOFILE 11582
#define MSG_CHANGED 11583
#define MSG_LOCKED 11584
#define MSG_MODE 11585
#define MSG_STALE 11586
#define MSG_NOTMEMBER 11587
#define MSG_DELETE 11588
#define MSG_TXN 11589
#define MSG_NOTADMIN 11590
#define MSG_WRITEFAIL 11591
#define MSG_NOSTATE 11592
#define MSG_NOLOCK 11595
#define MSG_NOTREAD 11596

Private int mst_refuse(int msg, const char *a, const char *b, const char *c) {
  snprintf(mst_refusal_buf, sizeof(mst_refusal_buf), sysmsg(msg), (a != NULL) ? a : "", (b != NULL) ? b : "", (c != NULL) ? c : "");
  return DHE_MASTER_REFUSED;
}

const char *masters_refusal_text(void) {
  return mst_refusal_buf;
}

/* a key as it can be shown: a control byte or a byte above DEL is a question mark, and it is cut short (at 60: with the account, a group or a user beside it the
   sentence has to fit what k_error has room for, and the part that says nothing was changed must not be the part that is cut off) */
#define MST_SHOWN_MAX 60
#define MST_SHOWN_AUDIT 150 /* the audit line is not a message and has the room: it names the whole id */
Private void mst_shown(char *dst, size_t dsz, const char *s, int len, size_t most) {
  size_t i, o = 0;

  for (i = 0; (i < (size_t)len) && (o + 1 < dsz) && (o < most); i++) {
    unsigned char c = (unsigned char)s[i];

    dst[o++] = ((c < 32) || (c > 126)) ? '?' : (char)c;
  }
  dst[o] = '\0';
}

/* Which of the two files that deliver a saved record this DH_FILE is: MST_VOC (voc_master), MST_DICT (dict_master) or 0.  Worked out from the file's
   pathname once per open file and kept in its flags, so that a write to any other file costs one test of a bit. */
Private int mst_master_kind(DH_FILE *dh) {
  int w;

  if (dh->flags & DHF_MST_NOMASTER)
    return 0;
  if (dh->flags & DHF_MST_VM)
    return MST_VOC;
  if (dh->flags & DHF_MST_DM)
    return MST_DICT;
  w = mst_master_which((const char *)FPtr(dh->file_id)->pathname);
  if (w == 1) {
    dh->flags |= DHF_MST_VM;
    return MST_VOC;
  }
  if (w == 2) {
    dh->flags |= DHF_MST_DM;
    return MST_DICT;
  }
  dh->flags |= DHF_MST_NOMASTER;
  return 0;
}

/* the directory of an account's VOC or dictionary */
Private void mst_account_file_path(int kind, const char *root, const char *file, char *out, size_t outsz) {
  if (kind == MST_VOC)
    snprintf(out, outsz, "%s%cvoc", root, DS);
  else
    snprintf(out, outsz, "%s%c%s.dic", root, DS, file);
}

/* ----------------------------------------------------------------------
   WHAT THIS SESSION HAS READ (verifier F3).  A save of a master record is an edit of a record the session READ, and it is judged against that record: the account's
   record must still be the one that was read.  op_read tells us (masters_note_read) of every read of voc_master or dict_master: the key and the checksum of what came
   back, or "" for a record that was not there.  The last MST_READ_N keys are kept, in a ring; a key that has fallen out of it counts as not read, and the save is refused
   with a message that says to read it again.  Nothing here is shared: it is this process's memory.                                                                 */
#define MST_READ_N 128

typedef struct {
  unsigned char kind; /* MST_VOC or MST_DICT; 0 for a slot never used */
  unsigned char idlen;
  char id[256];
  char cks[17]; /* the checksum of the record as it was read; "" when the read found none */
} MST_READ;

Private MST_READ mst_reads[MST_READ_N];
Private int mst_read_next = 0;

Private MST_READ *mst_read_find(int kind, const char *id, int id_len) {
  int i;

  for (i = 0; i < MST_READ_N; i++) {
    MST_READ *r = &mst_reads[i];

    if ((r->kind == kind) && ((int)r->idlen == id_len) && (mst_id_cmp(r->id, r->idlen, id, id_len) == 0))
      return r;
  }
  return NULL;
}

Private void mst_read_put(int kind, const char *id, int id_len, const char *cks) {
  MST_READ *r;

  if ((id_len < 1) || (id_len > 255))
    return;
  if ((r = mst_read_find(kind, id, id_len)) == NULL) {
    r = &mst_reads[mst_read_next];
    mst_read_next = (mst_read_next + 1) % MST_READ_N;
  }
  r->kind = (unsigned char)kind;
  r->idlen = (unsigned char)id_len;
  memcpy(r->id, id, (size_t)id_len);
  snprintf(r->cks, sizeof(r->cks), "%s", cks);
}

/* op_read calls this after every read of a DYNAMIC file (the one place a program's READ, READU, READV and MATREAD all pass).  A file that is not voc_master or dict_master
   costs the test of one bit once the file's name has been looked at (mst_master_kind sets it). */
void masters_note_read(DH_FILE *dh, const char *id, int id_len, STRING_CHUNK *rec, int err) {
  int kind;
  char cks[17];

  if ((dh == NULL) || (dh->flags & DHF_MST_NOMASTER))
    return;
  if ((kind = mst_master_kind(dh)) == 0)
    return;
  if (err == 0)
    mst_checksum(rec, cks);
  else if (err == DHE_RECORD_NOT_FOUND)
    cks[0] = '\0';
  else
    return;
  mst_read_put(kind, id, id_len, cks);
}

/* ----------------------------------------------------------------------
   THE COMPARISON INSIDE THE WRITE (verifier F4).  mst_deliver has compared the account's record with what the session read; between that and its write an account's
   user may WRITE the record with a plain WRITE, which takes no record lock and which the try-lock therefore cannot see.  So mst_deliver arms this (masters_cas_on, the
   file, the key and the checksum it accepted) and dh_write, when it has the record's group locked and has found the record - or found there is none - asks
   masters_cas_check before it changes a byte.  A different checksum fails the write with DHE_MASTER_REFUSED and the words of message 11583 are in the refusal buffer;
   nothing has been changed.  It answers for the one write that was armed for it - the file and the key must be the ones armed - and is spent when it has answered. */
int masters_cas_on = 0;

Private struct {
  DH_FILE *dh;
  char id[256];
  int idlen;
  char expect[17]; /* the checksum the account's record must have; "" for a record that must not be there */
  char keytxt[64];
  char acct[MAX_ACCOUNT_NAME_LEN + 4];
} mst_cas;

int masters_cas_check(DH_FILE *dh, const char *id, int id_len, STRING_CHUNK *current, bool found) {
  char cks[17];

  if (!masters_cas_on || (dh != mst_cas.dh) || (id_len != mst_cas.idlen) || (memcmp(id, mst_cas.id, (size_t)id_len) != 0))
    return 0; /* not the write that was armed */
  masters_cas_on = 0;
  if (found)
    mst_checksum(current, cks);
  else
    cks[0] = '\0';
  if (strcmp(cks, mst_cas.expect) == 0)
    return 0;
  return mst_refuse(MSG_CHANGED, mst_cas.keytxt, mst_cas.acct, NULL);
}

/* The way out of mst_deliver for every refusal made after the lock was asked for (a refactor of five copies of the same three lines, 19 Oct 26): the lock goes back when THIS
   call took it, what the call opened is closed, and the words are those of MSG with its arguments.  MSG 0: the refusal buffer holds the words already (the comparison inside
   the write set them) and only the status is returned. */
Private int mst_deliver_stop(MST_CTX *cx, FILE_VAR *fv, bool took, const char *rid, int rid_len, int msg, const char *a, const char *b, const char *c) {
  if (took)
    unlock_record(fv, (char *)rid, (int16_t)rid_len);
  mst_ctx_close(cx);
  if (msg == 0)
    return DHE_MASTER_REFUSED;
  return mst_refuse(msg, a, b, c);
}

/* SDSYS saves the record ID of voc_master (WHICH = MST_VOC) or dict_master (MST_DICT): the whole of D7.  0 to go on and write the master record too,
   else DHE_MASTER_REFUSED with nothing changed anywhere.  Called by dh_write before it does anything. */
Private int mst_deliver(int which, char *id, int id_len, STRING_CHUNK *data) {
  char keytxt[MST_SHOWN_MAX + 4];
  char acct[MAX_ACCOUNT_NAME_LEN + 4];
  char file[MST_FILE_MAX + 4];
  char path[MAX_PATHNAME_LEN + 16];
  char gname[64];
  char mkey[512], skey[520];
  char actual[256];
  char cks[17], scks[17], ncks[17];
  char sv[64];
  char line[1000], idtxt[160], filetxt[MST_FILE_MAX + 12], whattxt[MST_FILE_MAX + MAX_ACCOUNT_NAME_LEN + 40];
  char num[32];
  const char *p1, *p2, *rid;
  int rid_len, acctlen, filelen, mk, svl, why, lk, k;
  MST_ACC acc; /* a COPY of the account's table entry: the table is read again inside the write below (see the note on acc_tab) */
  const MST_ACC *a = &acc;
  MST_CTX cx;
  DH_FILE *adh;
  FILE_VAR fv;
  STRING_CHUNK *rec;
  MST_READ *rd;
  bool found, took = FALSE, wok;

  mst_refusal_buf[0] = '\0';
  mst_shown(keytxt, sizeof(keytxt), id, id_len, MST_SHOWN_MAX);

  /* 1 the administrator, signed on at a terminal, and nobody else */
  if ((my_uptr == NULL) || !(my_uptr->flags & USR_ADMIN))
    return mst_refuse(MSG_NOTADMIN, keytxt, NULL, NULL);

  /* 2 the key: account*id, or account*file*id with the first one or two asterisks the separators (an id may hold more) */
  p1 = memchr(id, '*', (size_t)id_len);
  if ((p1 == NULL) || (p1 == id) || ((acctlen = (int)(p1 - id)) > MAX_ACCOUNT_NAME_LEN))
    return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);
  memcpy(acct, id, (size_t)acctlen);
  acct[acctlen] = '\0';
  file[0] = '\0';
  if (which == MST_VOC) {
    rid = p1 + 1;
    rid_len = id_len - acctlen - 1;
  } else {
    p2 = memchr(p1 + 1, '*', (size_t)(id_len - acctlen - 1));
    if ((p2 == NULL) || (p2 == p1 + 1) || ((filelen = (int)(p2 - (p1 + 1))) > MST_FILE_MAX))
      return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);
    memcpy(file, p1 + 1, (size_t)filelen);
    file[filelen] = '\0';
    if (!mst_file_ok(file))
      return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);
    rid = p2 + 1;
    rid_len = (int)((id + id_len) - rid);
  }
  if ((rid_len < 1) || (rid_len > 255) || !mst_valid_account_name(acct))
    return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);
  mst_shown(idtxt, sizeof(idtxt), rid, rid_len, MST_SHOWN_AUDIT);

  /* the account must be registered (the register is read afresh for a name the administrator gives) */
  if (!mst_acc_by_name(acct, &acc))
    return mst_refuse(MSG_NOACCOUNT, keytxt, acct, NULL);

  memset(&cx, 0, sizeof(cx));
  if (!mst_master_path(MST_STATE, path, sizeof(path)) || ((cx.st = mst_open_path(path)) == NULL))
    return mst_refuse(MSG_NOSTATE, keytxt, "master_state", NULL);
  adh = mst_acct_file(&cx, which, a->root, file);
  if ((adh == NULL) && cx.last_absent && (which == MST_DICT)) {
    /* The key's file part is case blind like the master file, and every dictionary SD makes is named in lower case: ZMONE*ZMF3*X is zmone's zmf3.dic.  (A dictionary
       that is really there under a capital was found by the first try.) */
    for (k = 0; file[k] != '\0'; k++) {
      if ((file[k] >= 'A') && (file[k] <= 'Z')) {
        for (; file[k] != '\0'; k++)
          file[k] = (char)tolower((unsigned char)file[k]);
        adh = mst_acct_file(&cx, which, a->root, file);
        break;
      }
    }
  }
  snprintf(filetxt, sizeof(filetxt), "%s", (which == MST_VOC) ? "voc" : "");
  if (which == MST_DICT)
    snprintf(filetxt, sizeof(filetxt), "%s.dic", file);
  snprintf(whattxt, sizeof(whattxt), "%s of %s", (which == MST_VOC) ? "VOC" : filetxt, a->name); /* "VOC of zmone", "zmf9.dic of zmone" */
  if (strlen(whattxt) > 60) {
    whattxt[57] = '.';
    whattxt[58] = '.';
    whattxt[59] = '.';
    whattxt[60] = '\0'; /* the sentence has the room k_error gives it, and no more */
  }
  mst_account_file_path(which, a->root, file, path, sizeof(path));
  if (adh == NULL) {
    if (cx.last_absent) {
      mst_ctx_close(&cx);
      return mst_refuse(MSG_NOFILE, keytxt, (which == MST_VOC) ? "VOC" : "dictionary of that name", NULL);
    }
    /* it is there and cannot be opened: say why in the words of the write test below */
    why = mst_write_check(path, gname, sizeof(gname));
    mst_ctx_close(&cx);
    if (why == MST_W_OK) /* it could be written and still would not open: the file itself is wrong */
      return mst_refuse(MSG_WRITEFAIL, keytxt, "the file would not open", NULL);
    goto refuse_rights;
  }

  /* 3 can this process write the file?  Before a lock is taken or a byte is written */
  why = mst_write_check(path, gname, sizeof(gname));
  if (why != MST_W_OK) {
    mst_ctx_close(&cx);
    goto refuse_rights;
  }

  /* the keys of master_state: from the stored spelling when the record is there, as stage 1 makes them */
  if (mst_keys(which, a->name, file, rid, rid_len, mkey, skey) < 0) {
    mst_ctx_close(&cx);
    return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);
  }
  mk = (int)strlen(mkey);

  /* 4 the account's record, locked by a try-lock that returns at once.  The account's own process may hold this record and be waiting on the master;
     waiting here would be a deadlock nobody could see.  A lock this process already holds (SDSYS signed on to the account) is used and left alone. */
  memset(&fv, 0, sizeof(fv));
  fv.type = DYNAMIC_FILE;
  fv.file_id = adh->file_id;
  fv.index = -2; /* belongs to no file variable of the program */
  if (!check_lock(&fv, (char *)rid, (int16_t)rid_len)) {
    lk = lock_record(&fv, (char *)rid, (int16_t)rid_len, TRUE, 0, TRUE);
    if (lk != 0) {
      snprintf(num, sizeof(num), "%d", lk);
      mst_ctx_close(&cx);
      if (lk > 0)
        return mst_refuse(MSG_LOCKED, keytxt, num, NULL);
      return mst_refuse(MSG_NOLOCK, keytxt, NULL, NULL); /* the lock table is full, a deadlock was seen or the limit is reached: no user holds it */
    }
    took = TRUE;
  }

  /* 5 the account's record as it is NOW against the record this session READ (verifier F3).  master_state is the version of the last DRAIN, and a drain that
     comes between the read and the save - a second open of the master, CHECK.MASTERS - moves it to the account's newer record; compared with that, a save made from
     the older copy would overwrite the account's change.  So the comparison is with what the session read (masters_note_read).  A key it did not read counts as
     not read: it may create a record (the account has none and master_state has none), and may not overwrite one. */
  memset(actual, 0, sizeof(actual));
  rec = dh_read(adh, (char *)rid, (int16_t)rid_len, actual);
  found = (dh_err == 0);
  if (!found && (dh_err != DHE_RECORD_NOT_FOUND)) {
    k_deref_string(rec);
    return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_NOSTATE, keytxt, "the account's record", NULL);
  }
  if (found)
    mst_checksum(rec, cks);
  else
    cks[0] = '\0';
  k_deref_string(rec);
  rd = mst_read_find(which, (const char *)id, id_len);
  if (rd != NULL) {
    if (strcmp(cks, rd->cks) != 0) /* the account's record is no longer the one that was read */
      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_CHANGED, keytxt, a->name, NULL);
  } else {
    (void)mst_state_get(&cx, skey, mk + 2, scks);
    if (cks[0] != '\0') /* not read, and the account has the record */
      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_NOTREAD, keytxt, NULL, NULL);
    if (scks[0] != '\0') /* not read, the account has none now, and master_state remembers that it had one: the account deleted it */
      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_CHANGED, keytxt, a->name, NULL);
  }

  /* 6 write the account's own file, here, like any other writer (dh_write journals it for the drain, and keeps its indices).  The comparison is made AGAIN inside the
     write, under the file's own lock on the record's group (masters_cas_check, called by dh_write when it has found the record or found there is none): a plain WRITE by
     the account's user needs no record lock, and one that landed after the test above would have been overwritten without a sign (verifier F4). */
  snprintf(mst_cas.expect, sizeof(mst_cas.expect), "%s", cks);
  snprintf(mst_cas.keytxt, sizeof(mst_cas.keytxt), "%s", keytxt);
  snprintf(mst_cas.acct, sizeof(mst_cas.acct), "%s", a->name);
  memcpy(mst_cas.id, rid, (size_t)rid_len);
  mst_cas.idlen = rid_len;
  mst_cas.dh = adh;
  masters_cas_on = 1;
  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);
  masters_cas_on = 0;
  if (!wok) {
    if ((int)dh_err == DHE_MASTER_REFUSED) /* the comparison in the write refused it, and its words are in the refusal buffer already */
      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, 0, NULL, NULL, NULL);
    snprintf(num, sizeof(num), "%d", (int)dh_err);
    return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_WRITEFAIL, keytxt, num, NULL);
  }

  /* 7 master_state follows, and so does what this session has read of the key, so that a second save with no re-read in between is not refused as a change */
  mst_checksum(data, ncks);
  svl = snprintf(sv, sizeof(sv), "%s%c%lld%c", ncks, MST_FM, (long long)time(NULL), MST_FM);
  (void)mst_put(cx.st, skey, mk + 2, sv, svl);
  mst_read_put(which, (const char *)id, id_len, ncks);

  /* 8 the lock goes back */
  if (took)
    unlock_record(&fv, (char *)rid, (int16_t)rid_len);
  mst_ctx_close(&cx);

  /* 9 the audit line: who (audit_message adds the user and the process), what was written where */
  snprintf(line, sizeof(line), "master edit account=%s file=%s id=%s", a->name, filetxt, idtxt);
  audit_message(line);
  return 0;

refuse_rights:
  switch (why) {
    case MST_W_STALE:
      return mst_refuse(MSG_STALE, keytxt, gname, NULL);
    case MST_W_NOTMEMBER:
      return mst_refuse(MSG_NOTMEMBER, keytxt, gname, gname);
    default:
      return mst_refuse(MSG_MODE, keytxt, whattxt, NULL);
  }
}

int masters_before_write(DH_FILE *dh, char *id, int id_len, STRING_CHUNK *data) {
  int kind;

  if ((dh == NULL) || (dh->flags & DHF_MST_NOMASTER))
    return 0;
  if (((kind = mst_master_kind(dh)) == 0) || (mst_inside > 0))
    return 0;
  return mst_deliver(kind, id, id_len, data);
}

/* A DELETE of a master record is refused: the plan says SDSYS SAVES a master record, and deleting a copy is not deleting the account's record.  (The
   owner can decide that a delete should be delivered; it is a different act, and it is not decided.) */
int masters_before_delete(DH_FILE *dh, char *id, int id_len) {
  char keytxt[MST_SHOWN_MAX + 4];

  if ((dh == NULL) || (dh->flags & DHF_MST_NOMASTER))
    return 0;
  if ((mst_master_kind(dh) == 0) || (mst_inside > 0))
    return 0;
  mst_shown(keytxt, sizeof(keytxt), id, id_len, MST_SHOWN_MAX);
  return mst_refuse(MSG_DELETE, keytxt, NULL, NULL);
}

/* A write or a delete of a master record inside a transaction: the statement is refused before it reaches the transaction's cache, because the DH layer
   sees it only at COMMIT, where a refusal would come half way through the other writes of the transaction. */
int masters_txn_refusal(DH_FILE *dh, char *id, int id_len) {
  char keytxt[MST_SHOWN_MAX + 4];

  if ((dh == NULL) || (dh->flags & DHF_MST_NOMASTER))
    return 0;
  if ((mst_master_kind(dh) == 0) || (mst_inside > 0))
    return 0;
  mst_shown(keytxt, sizeof(keytxt), id, id_len, MST_SHOWN_MAX);
  return mst_refuse(MSG_TXN, keytxt, NULL, NULL);
}

/* ======================================================================
   THE MODES OF WHAT SD MAKES (stage 2)

   A VOC or a dictionary that has just been made is given group write - the directory g+rwx and setgid, %0 and %1 g+rw - where the account's directory
   has it, so that SDSYS (a member of the group) can write a master edit into it whatever the UMASK of the session that made it.  Only the GROUP bits
   are added, nothing is taken away and the other bits are not touched.  The rule is the account directory's own: if its group may write there, the
   group may write the VOC and the dictionaries, which it could already delete and make again; if the group may not (a directory of 755), nothing is
   added, and in particular nothing is added for a group that the account directory does not give write to.  Done on descriptors opened with O_NOFOLLOW
   and fchmod, so a link put in the place of the new directory by somebody else cannot aim the chmod at another file; only what this process made
   (owner = the effective user) and what has the account directory's group is changed.  A refusal changes nothing and is not an error. */
void masters_fix_modes(const char *path) {
  char full[PATH_MAX + 1];
  const MST_ACC *a;
  const char *rel, *base;
  struct stat ra, ds, fs;
  size_t n;
  int dfd, ffd, i;
  static const char *subs[2] = {"%0", "%1"};

  if ((path == NULL) || ((n = strlen(path)) < 3) || (n > MAX_PATHNAME_LEN))
    return;
  if (!(((n > 4) && (strcasecmp(path + n - 4, ".dic") == 0)) || (strcasecmp(path + n - 3, "voc") == 0)))
    return;
  if (!fullpath(full, (char *)path) || ((a = mst_acc_for_path(full, &rel)) == NULL))
    return;
  base = strrchr(rel, '/');
  base = (base == NULL) ? rel : base + 1;
  n = strlen(base);
  if (!((strcmp(rel, "voc") == 0) || ((n > 4) && (strcasecmp(base + n - 4, ".dic") == 0))))
    return;
  if ((stat(a->root, &ra) != 0) || !(ra.st_mode & S_IWGRP))
    return;
  if ((dfd = open(full, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)) < 0)
    return;
  if ((fstat(dfd, &ds) != 0) || !S_ISDIR(ds.st_mode) || (ds.st_uid != geteuid()) || (ds.st_gid != ra.st_gid)) {
    close(dfd);
    return;
  }
  (void)fchmod(dfd, (mode_t)((ds.st_mode & 07777) | S_IRWXG | S_ISGID));
  for (i = 0; i < 2; i++) {
    if ((ffd = openat(dfd, subs[i], O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)) < 0)
      continue;
    if ((fstat(ffd, &fs) == 0) && S_ISREG(fs.st_mode) && (fs.st_uid == geteuid()) && (fs.st_gid == ra.st_gid))
      (void)fchmod(ffd, (mode_t)((fs.st_mode & 07777) | S_IRGRP | S_IWGRP));
    close(ffd);
  }
  close(dfd);
}

/* END-CODE */
