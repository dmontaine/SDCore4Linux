/* Character maps required by the standalone client library. */

void set_default_character_maps(void) {
  int i;
  int j;

  for (i = 0; i < 256; i++) {
    uc_chars[i] = (char)i;
    lc_chars[i] = (char)i;
    char_types[i] = 0;
  }

  for (i = 'a', j = 'A'; i <= 'z'; i++, j++) {
    uc_chars[i] = (char)j;
    lc_chars[j] = (char)i;
    char_types[i] |= CT_ALPHA;
    char_types[j] |= CT_ALPHA;
  }

  for (i = '0'; i <= '9'; i++)
    char_types[i] |= CT_DIGIT;

  for (i = 33; i <= 126; i++)
    char_types[i] |= CT_GRAPH;

  char_types[U_TEXT_MARK] |= CT_MARK;
  char_types[U_SUBVALUE_MARK] |= CT_MARK | CT_DELIM;
  char_types[U_VALUE_MARK] |= CT_MARK | CT_DELIM;
  char_types[U_FIELD_MARK] |= CT_MARK | CT_DELIM;
  char_types[U_ITEM_MARK] |= CT_MARK;
}

