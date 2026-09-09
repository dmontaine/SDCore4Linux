# check_msg_len.py - does a message fit k_error()'s buffer once sysmsg() has
# expanded it?  messages.c turns a literal backslash-n into LF followed by CR
# (two characters), and k_error writes at offset n after a 10-byte "%08X: "
# prefix, so the room is sizeof(s) - n = (3 * 80 + 1) - 10 = 231.
#
#   python3 gplbld/check-msglen.py sdsys/MESSAGES/10099
#
# Copied BYTE-FOR-BYTE from SD Core for Windows (its gplbld/check-msglen.py) on
# the owner's instruction of 9 Sep 2026, and copied rather than adapted because
# every constant it hard-codes was checked against THIS tree first and all four
# match: MAX_ERROR_LINES 3 and MAX_EMSG_LEN 80 (gplsrc/sddefs.h:124-125), the
# same buffer declaration char s[(MAX_ERROR_LINES * MAX_EMSG_LEN) + 1] and the
# 10-byte "%08X: " prefix (gplsrc/k_error.c:160,212), the D1 fix that makes the
# bound sizeof(s) - n rather than a second constant to keep in step
# (k_error.c:226), and the backslash-n to LF+CR substitution
# (gplsrc/messages.c:337-340).  IF ANY OF THOSE CHANGES, THIS SCRIPT IS WRONG
# AND WILL NOT SAY SO - it hard-codes 231.
#
# The bound is compiled in, so no unit test could have caught the defect this
# exists for; in the port it was found by measuring a message that came back
# cut mid-word.  Note the refusal at the end: a run that substituted no escapes
# measured nothing and exits 2 rather than passing.
import sys

BS_N = chr(92) + 'n'          # a literal backslash followed by n
LFCR = chr(10) + chr(13)      # what messages.c substitutes for it
BOUND = (3 * 80 + 1) - 10

path = sys.argv[1]
raw = open(path, 'rb').read().decode('ascii')
if raw.endswith(chr(10)):
    raw = raw[:-1]

rendered = raw.replace(BS_N, LFCR).replace('%d', '3023')
lines = rendered.split(LFCR)

print('file            : %s' % path)
print('file bytes      : %d' % len(raw))
print('escapes found   : %d   (a 0 here would mean the check measured nothing)'
      % raw.count(BS_N))
print('rendered length : %d' % len(rendered))
print('bound           : %d' % BOUND)
print('fits            : %s' % (len(rendered) <= BOUND))
print('lines           : %d   (k_error is sized for %d)' % (len(lines), 3))
for i, l in enumerate(lines):
    print('  %d (%2d chars) | %s' % (i + 1, len(l), l))

if raw.count(BS_N) == 0:
    print('REFUSED: no escapes were found, so nothing was substituted.')
    sys.exit(2)
sys.exit(0 if len(rendered) <= BOUND else 1)
