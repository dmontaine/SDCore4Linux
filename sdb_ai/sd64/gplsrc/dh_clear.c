/* DH_CLEAR.C
 * Clear file
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
 * dh_clear()  -  Remove all records from a dynamic hash file.
 *
 * Clears alternate-key subfiles first, reinitialises primary data groups,
 * truncates the overflow subfile, then writes the on-disk header.  The
 * alternate-key map in the header is preserved.  The caller must hold
 * exclusive access (e.g. op_clrfile).  Requires a writable DH_FILE.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "dh_int.h"

/* ====================================================================== */

static bool valid_akno(int16_t akno) {
  return (akno >= 0) && (akno < MAX_INDICES);
}

static bool ak_in_map(u_int32_t ak_map, int16_t akno) {
  if (!valid_akno(akno))
    return FALSE;
  return (ak_map & (1u << (unsigned)akno)) != 0;
}

/* ====================================================================== */

bool dh_clear(DH_FILE* dh_file) {
  bool status = FALSE;
  FILE_ENTRY* fptr;
  int32_t new_modulus;
  int32_t mod_value;
  int32_t group;
  int group_size_bytes;
  u_int32_t ak_map;
  int16_t akno;

  dh_err = 0;
  process.os_error = 0;

  if (dh_file == NULL) {
    dh_err = DHE_FILE_NOT_OPEN;
    return FALSE;
  }

  if (dh_file->flags & DHF_RDONLY) {
    dh_err = DHE_EXCLUSIVE;
    return FALSE;
  }

  fptr = FPtr(dh_file->file_id);
  if (fptr == NULL) {
    dh_err = DHE_NOT_A_FILE;
    return FALSE;
  }

  dh_end_select_file(dh_file); /* Kill any select */

  /* Read primary header (preserve ak_map); validate before mutating file */

  if (!FDS_open(dh_file, PRIMARY_SUBFILE))
    goto exit_dh_clear;

  if (!dh_read_group(dh_file, PRIMARY_SUBFILE, 0, dh_buffer,
                     (int16_t)(dh_file->header_bytes))) {
    goto exit_dh_clear;
  }

  ak_map = ((DH_HEADER*)dh_buffer)->ak_map;
  dh_file->ak_map = ak_map;

  new_modulus = fptr->params.min_modulus;
  if (new_modulus < 1) {
    dh_err = DHE_ILLEGAL_MIN_MODULUS;
    goto exit_dh_clear;
  }
  if (new_modulus > fptr->params.modulus) {
    dh_err = DHE_ILLEGAL_MIN_MODULUS;
    goto exit_dh_clear;
  }

  group_size_bytes = dh_file->group_size;
  if (group_size_bytes <= 0 || group_size_bytes > DH_MAX_GROUP_SIZE_BYTES) {
    dh_err = DHE_ILLEGAL_GROUP_SIZE;
    goto exit_dh_clear;
  }

  /* Clear alternate keys before wiping primary/overflow data */

  for (akno = 0; akno < MAX_INDICES; akno++) {
    if (ak_in_map(ak_map, akno)) {
      if (!ak_clear(dh_file, AK_BASE_SUBFILE + akno))
        goto exit_dh_clear;
    }
  }

  /* Initialise data groups (raw Seek/Write; caller holds file lock) */

  memset(dh_buffer, 0, group_size_bytes);
  ((DH_BLOCK*)(dh_buffer))->used_bytes = BLOCK_HEADER_SIZE;
  ((DH_BLOCK*)(dh_buffer))->block_type = DHT_DATA;

  if (Seek(dh_file->sf[PRIMARY_SUBFILE].fu, (int64)(dh_file->header_bytes),
           SEEK_SET) < 0) {
    dh_err = DHE_SEEK_ERROR;
    process.os_error = OSError;
    goto exit_dh_clear;
  }

  for (group = 1; group <= new_modulus; group++) {
    if (Write(dh_file->sf[PRIMARY_SUBFILE].fu, dh_buffer, group_size_bytes) <
        0) {
      dh_err = DHE_INIT_DATA_ERROR;
      process.os_error = OSError;
      goto exit_dh_clear;
    }
  }

  if (!SetFileSize(dh_file->sf[PRIMARY_SUBFILE].fu,
                   GroupOffset(dh_file, ((int64)new_modulus) + 1))) {
    if (dh_err == 0)
      dh_err = DHE_WRITE_ERROR;
    goto exit_dh_clear;
  }

  if (!FDS_open(dh_file, OVERFLOW_SUBFILE))
    goto exit_dh_clear;

  if (!SetFileSize(dh_file->sf[OVERFLOW_SUBFILE].fu, dh_file->header_bytes)) {
    if (dh_err == 0)
      dh_err = DHE_WRITE_ERROR;
    goto exit_dh_clear;
  }

  /* Update in-memory parameters and persist header only after data clear */

  fptr->params.modulus = new_modulus;
  fptr->params.load_bytes = 0;
  fptr->params.free_chain = 0;
  fptr->params.longest_id = 0;
  fptr->record_count = 0;

  for (mod_value = 1; mod_value < new_modulus; mod_value <<= 1) {
  }
  fptr->params.mod_value = mod_value;

  dh_file->flags |= FILE_UPDATED;
  if (!dh_flush_header(dh_file)) {
    if (dh_err == 0)
      dh_err = DHE_PSFH_WRITE_ERROR;
    goto exit_dh_clear;
  }

  StartExclusive(FILE_TABLE_LOCK, 44);
  fptr->stats.clears++;
  sysseg->global_stats.clears++;
  EndExclusive(FILE_TABLE_LOCK);

  status = TRUE;

exit_dh_clear:

  return status;
}

/* END-CODE */
