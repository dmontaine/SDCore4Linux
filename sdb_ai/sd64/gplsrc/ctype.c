/* CTYPE.C
 * Character type handling and associated functions.
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
 * START-HISTORY 
 * 31 Dec 23 SD launch - prior history suppressed
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * This module replaces all the standard casing and character type functions
 * to enable support of user defined collation sequences and upper/lower case
 * pairing rules. By encapsulating all these functions here, future changes
 * should be relatively easy to implement.
 *
 * Although the C library provides locale support functions, these are not
 * immediately applicable here because Q_M requires binary transparency and
 * the ability to sort right justified strings (amongst other problems).
 *
 * It is likely that Q_M will be adapted to support Unicode and all the
 * associated locale related operations in the long term future.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"

#define EXTRACT_MAX_SRC_LEN 16777216

/* Non-heap empty string returned only when malloc fails for Extract/CNullString. */
static char extract_static_empty[1] = { '\0' };

Private char* CNullString(void);

/* ======================================================================
   Set default_character maps
   Maps are byte-indexed (0..255); Unicode/locale is not handled here.     */

void set_default_character_maps(void) {
  int i;
  int j;
  for (i = 0; i < 256; i++) {
    uc_chars[i] = (char)i;
    lc_chars[i] = (char)i;
    char_types[i] = 0;
  }

  for (i = 'a', j = 'A'; i <= 'z'; i++, j++) {
    uc_chars[i] = j;
    lc_chars[j] = i;
    char_types[i] |= CT_ALPHA;
    char_types[j] |= CT_ALPHA;
  }

  for (i = '0'; i <= '9'; i++) {
    char_types[i] |= CT_DIGIT;
  }

  for (i = 33; i <= 126; i++) {
    char_types[i] |= CT_GRAPH;
  }

  char_types[U_TEXT_MARK] |= CT_MARK;
  char_types[U_SUBVALUE_MARK] |= CT_MARK | CT_DELIM;
  char_types[U_VALUE_MARK] |= CT_MARK | CT_DELIM;
  char_types[U_FIELD_MARK] |= CT_MARK | CT_DELIM;
  char_types[U_ITEM_MARK] |= CT_MARK;
}

/* ======================================================================
   LowerCaseString()  -  Convert string to lower case                     */

char* LowerCaseString(char* s) {
  char* p;

  if (s == NULL)
    return NULL;

  p = s;
  while ((*p = LowerCase(*p)) != '\0') {
    p++;
  }
  return s;
}

/* ======================================================================
   MemCompareNoCase()  -  Case insensitive variant of memcmp
   Uses UpperCase() on each byte; not locale-aware.                       */

int MemCompareNoCase(char* p, char* q, int16_t len) {
  signed char c;

  if (p == NULL || q == NULL) {
    if (p == q)
      return 0;
    return (p == NULL) ? -1 : 1;
  }

  while (len--) {
    if ((c = UpperCase(*p) - UpperCase(*q)) != 0)
      return c;
    p++;
    q++;
  }

  return 0;
}

/* ======================================================================
   memichr()  -  Case insensitive variant of memchr()                     */

char* memichr(char* s, char c, int n) {
  if (s == NULL)
    return NULL;

  c = UpperCase(c);

  while (n--) {
    if (UpperCase(*s) == c)
      return s;
    s++;
  }

  return NULL;
}

/* ======================================================================
   memucpy()  -  Copy a specified number of bytes, converting to uppercase */

void memucpy(char* tgt, char* src, int16_t len) {
  if (tgt == NULL || src == NULL)
    return;

  while (len--)
    *(tgt++) = UpperCase(*(src++));
}

/* ======================================================================
   sort_compare()  -  Compare two strings for sorting                     */

int sort_compare(char* s1, char* s2, int16_t bytes, bool nocase) {
  if (s1 == NULL || s2 == NULL) {
    if (s1 == s2)
      return 0;
    return (s1 == NULL) ? -1 : 1;
  }
  if (nocase)
    return MemCompareNoCase(s1, s2, bytes);
  return memcmp(s1, s2, bytes);
}

/* ======================================================================
   StringCompLenNoCase()  -  Case insensitive variant of strncmp          */

int StringCompLenNoCase(char* p, char* q, int16_t len) {
  char c;

  if (p == NULL || q == NULL) {
    if (p == q)
      return 0;
    return (p == NULL) ? -1 : 1;
  }

  while (len--) {
    if (((c = UpperCase(*p) - UpperCase(*q)) != 0) || (*p == '\0') ||
        (*q == '\0'))
      return c;
    p++;
    q++;
  }

  return 0;
}

/* ======================================================================
   UpperCaseMem()  -  Uppercase specified number of bytes                 */

void UpperCaseMem(char* str, int16_t len) {
  char c;

  if (str == NULL)
    return;

  while (len--) {
    c = UpperCase(*str);
    *(str++) = c;
  }
}

/* ======================================================================
   UpperCaseString()  -  Convert string to upper case                     */

char* UpperCaseString(char* s) {
  char* p;

  if (s == NULL)
    return NULL;

  p = s;
  while ((*p = UpperCase(*p)) != '\0') {
    p++;
  }

  return s;
}

/* ======================================================================
   Dcount()  -  Count fields, values or subvalues
   Only the first byte of delim_str is used (single-character delimiter). */

int Dcount(char* src, char* delim_str) {
  int32_t src_len;
  char* p;
  int32_t ct = 0;
  char delim;

  if (src == NULL || delim_str == NULL || delim_str[0] == '\0')
    return 0;

  delim = delim_str[0];

  src_len = strlen(src);
  if (src_len != 0) {
    ct = 1;
    while ((p = memchr(src, delim, src_len)) != NULL) {
      src_len -= (1 + p - src);
      src = p + 1;
      ct++;
    }
  }

  return ct;
}

/* ======================================================================
   Extract()  -  Extract field, value or subvalue
   Returns malloc'd string; use free_extract_string() to release.
   fno/vno/svno less than 1 are treated as 1 (whole field/value).
   Field 0 with vno>0 addresses the attribute portion before the first
   field mark (see op_dio2.c OSPATH chown parameters).                    */

char* Extract(char* src, int fno, int vno, int svno) {
  int32_t src_len;
  char* p;
  char* result;

  if (src == NULL)
    goto null_result;

  src_len = strlen(src);
  if (src_len == 0 || src_len > EXTRACT_MAX_SRC_LEN)
    goto null_result;

  /* Step 1  -  Initialise variables */

  if (fno < 1)
    fno = 1;

  /* Step 2  -  Position to start of item */

  while (--fno) {
    p = memchr(src, FIELD_MARK, src_len);
    if (p == NULL)
      goto null_result;
    src_len -= (1 + p - src);
    src = p + 1;
  }
  p = memchr(src, FIELD_MARK, src_len);
  if (p != NULL)
    src_len = p - src;

  if (vno < 1)
    goto done;

  while (--vno) {
    p = memchr(src, VALUE_MARK, src_len);
    if (p == NULL)
      goto null_result;
    src_len -= (1 + p - src);
    src = p + 1;
  }

  p = memchr(src, VALUE_MARK, src_len);
  if (p != NULL)
    src_len = p - src;

  if (svno < 1)
    goto done;

  while (--svno) {
    p = memchr(src, SUBVALUE_MARK, src_len);
    if (p == NULL)
      goto null_result;
    src_len -= (1 + p - src);
    src = p + 1;
  }
  p = memchr(src, SUBVALUE_MARK, src_len);
  if (p != NULL)
    src_len = p - src;

done:
  result = malloc((size_t)src_len + 1);
  if (result == NULL)
    goto null_result;
  memcpy(result, src, (size_t)src_len);
  result[src_len] = '\0';
  return result;

null_result:
  return CNullString();
}

/* ======================================================================
   free_extract_string()  -  Release result from Extract()               */

void free_extract_string(char* p) {
  if (p != NULL && p != extract_static_empty)
    free(p);
}

Private char* CNullString(void) {
  char* p;

  p = malloc(1);
  if (p == NULL)
    return extract_static_empty;
  p[0] = '\0';
  return p;
}

/* END-CODE */
