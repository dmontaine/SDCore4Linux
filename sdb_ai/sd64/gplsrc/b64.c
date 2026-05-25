/* B64.C
 * Base64 encoding/decoding.
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
 * 31 Dec 23 SD Launch - prior history suppressed
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * This module is adapted from source code published by Bob Trower.
 * Copyright (c) Trantor Standard Systems Inc., 2001
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 *
 * Standard alphabet per RFC 4648 section 4 (not URL-safe variant 5).
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#ifdef B64_UNIT_TEST
#include "tests/b64_utypes.h"
#else
#include "sd.h"
#endif
#include <ctype.h>

/* RFC 4648 base64 alphabet */
static const char cb64[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

#define B64_LUT_INVALID 255
#define B64_LUT_PAD 254

static unsigned char b64_decode_lut[256];
static bool b64_tables_ready = 0;

static void b64_init_tables(void) {
  int i;

  if (b64_tables_ready)
    return;

  for (i = 0; i < 256; i++)
    b64_decode_lut[i] = B64_LUT_INVALID;

  for (i = 0; cb64[i] != '\0'; i++)
    b64_decode_lut[(unsigned char)cb64[i]] = (unsigned char)i;

  b64_decode_lut[(unsigned char)'='] = B64_LUT_PAD;
  b64_tables_ready = 1;
}

static void b64_free_chain(STRING_CHUNK* str) {
  STRING_CHUNK* next;

  while (str != NULL) {
    next = str->next;
    s_free(str);
    str = next;
  }
}

/* Pop next raw byte from chunk chain; return FALSE at end of input. */
static bool b64_pop_byte(STRING_CHUNK** chunk, char** p, int* bytes_left,
                         unsigned char* out) {
  while (*chunk != NULL) {
    if (*bytes_left > 0) {
      *out = (unsigned char)*((*p)++);
      (*bytes_left)--;
      return 1;
    }
    *chunk = (*chunk)->next;
    if (*chunk != NULL) {
      *p = (*chunk)->data;
      *bytes_left = (*chunk)->bytes;
    }
  }
  return FALSE;
}

/* Classify input byte for decode. Returns 0-63, B64_LUT_PAD, B64_LUT_INVALID. */
static unsigned char b64_decode_class(unsigned char c) {
  return b64_decode_lut[c];
}

/* b64encode() - Base64 encode with RFC 4648 padding */

STRING_CHUNK* b64encode(STRING_CHUNK* str) {
  unsigned char in[3];
  char out[4];
  int i;
  int len;
  STRING_CHUNK* tgt;
  char* p;
  int bytes_left;
  int32_t remaining;
  int32_t alloc_hint;

  if (str == NULL)
    return NULL;

  b64_init_tables();

  remaining = str->string_len;
  if (remaining <= 0) {
    int16_t actual;

    tgt = s_alloc(1, &actual);
    tgt->string_len = 0;
    tgt->bytes = 0;
    tgt->ref_ct = 1;
    return tgt;
  }

  alloc_hint = (int32_t)(((int64)remaining * 4) / 3 + 4);
  ts_init(&tgt, alloc_hint);

  p = str->data;
  bytes_left = str->bytes;

  while (remaining > 0) {
    len = (remaining >= 3) ? 3 : (int)remaining;

    for (i = 0; i < 3; i++) {
      if (i < len) {
        if (!b64_pop_byte(&str, &p, &bytes_left, &in[i])) {
          b64_free_chain(tgt);
          return NULL; /* string_len inconsistent with chunk data */
        }
      } else {
        in[i] = 0;
      }
    }

    remaining -= len;

    out[0] = cb64[in[0] >> 2];
    out[1] = cb64[((in[0] & 0x03) << 4) | ((in[1] & 0xf0) >> 4)];
    out[2] = (len > 1) ? cb64[((in[1] & 0x0f) << 2) | ((in[2] & 0xc0) >> 6)] : '=';
    out[3] = (len > 2) ? cb64[in[2] & 0x3f] : '=';

    ts_copy(out, 4);
  }

  ts_terminate();
  return tgt;
}

/* Read one sextet or padding marker; skip whitespace. Returns:
 *   1 = data or padding byte stored in *value
 *   0 = end of input
 *  -1 = invalid character
 */
static int b64_read_sextet(STRING_CHUNK** chunk, char** p, int* bytes_left,
                           unsigned char* value, bool* is_pad) {
  unsigned char c;
  unsigned char cls;

  *is_pad = FALSE;

  while (b64_pop_byte(chunk, p, bytes_left, &c)) {
    cls = b64_decode_class(c);
    if (cls <= 63) {
      *value = cls;
      return 1;
    }
    if (cls == B64_LUT_PAD) {
      *value = 0;
      *is_pad = 1;
      return 1;
    }
    if (isspace(c))
      continue;
    return -1;
  }

  return 0;
}

/* b64decode() - Base64 decode; returns NULL on invalid or truncated input */

STRING_CHUNK* b64decode(STRING_CHUNK* str) {
  unsigned char in[4];
  unsigned char out[3];
  int i;
  int out_len;
  STRING_CHUNK* tgt;
  char* p;
  int bytes_left;
  bool is_pad;
  bool done;
  unsigned char v;
  int rc;

  if (str == NULL)
    return NULL;

  b64_init_tables();

  if (str->string_len <= 0) {
    int16_t actual;

    tgt = s_alloc(1, &actual);
    tgt->string_len = 0;
    tgt->bytes = 0;
    tgt->ref_ct = 1;
    return tgt;
  }

  ts_init(&tgt, str->string_len);

  p = str->data;
  bytes_left = str->bytes;

  for (;;) {
    int filled = 0;
    int first_pad = -1;
    bool quartet_pad = FALSE;

    done = FALSE;

    for (i = 0; i < 4; i++) {
      rc = b64_read_sextet(&str, &p, &bytes_left, &v, &is_pad);
      if (rc < 0) {
        b64_free_chain(tgt);
        return NULL;
      }
      if (rc == 0) {
        if (filled == 0) {
          done = 1;
          break;
        }
        b64_free_chain(tgt);
        return NULL; /* truncated final quartet */
      }

      if (is_pad) {
        if (i < 2) {
          b64_free_chain(tgt);
          return NULL;
        }
        if (first_pad < 0)
          first_pad = i;
        quartet_pad = TRUE;
        in[i] = 0;
        filled++;
        continue;
      }

      if (quartet_pad) {
        b64_free_chain(tgt);
        return NULL; /* data sextet after padding */
      }

      in[i] = v;
      filled++;
    }

    if (done)
      break;

    if (filled == 0)
      break;

    if (quartet_pad) {
      if (first_pad < 2 || filled != 4) {
        b64_free_chain(tgt);
        return NULL;
      }
      out_len = first_pad - 1;
    } else {
      if (filled != 4) {
        b64_free_chain(tgt);
        return NULL;
      }
      out_len = 3;
    }

    out[0] = (unsigned char)((in[0] << 2) | (in[1] >> 4));
    out[1] = (unsigned char)((in[1] << 4) | (in[2] >> 2));
    out[2] = (unsigned char)(((in[2] << 6) & 0xc0) | in[3]);

    ts_copy((char*)out, out_len);

    /* After a padded block, only whitespace may follow. */
    if (quartet_pad) {
      unsigned char c;

      while (b64_pop_byte(&str, &p, &bytes_left, &c)) {
        if (b64_decode_class(c) == B64_LUT_PAD)
          continue;
        if (isspace(c))
          continue;
        b64_free_chain(tgt);
        return NULL;
      }
      break;
    }
  }

  ts_terminate();
  return tgt;
}

/* END-CODE */
