#!/usr/bin/env python3
# mknanosyntax.py - generate nano's SD BASIC syntax file from the compiler.
#
#   cd sdb_ai/sd64 && python3 gplbld/mknanosyntax.py \
#       sdsys/GPL.BP/BCOMP gplbld/nanocfg/sdbasic.nanorc
#
# 10 Sep 26 - Owner, 10 Sep 2026: Microsoft Edit is not packaged for Linux, so
# the NANO verb runs nano here, and nano is to have SD BASIC highlighting as
# micro does.  This is gplbld/mkbasicsyntax.py's extraction (the Windows port's
# script, ported 9 Sep) with a nanorc writer instead of micro's YAML.  THE
# EXTRACTION IS DUPLICATED RATHER THAN IMPORTED because mkbasicsyntax.py is the
# port's script and runs at top level on sys.argv; keeping it byte-close to the
# port matters more than sharing forty lines.  If BCOMP's table names change,
# change both.
#
# ***RUN AT BUILD TIME, NEVER AT INSTALL TIME.***  It reads the SOURCE tree's
# BCOMP; an installed system has one too, and the command would appear to work
# there while describing whatever that install happens to be.
#
# WHAT IT REFUSES, OUT LOUD: an empty table (a renamed table would otherwise
# produce a file that highlights nothing), and a regex GNU grep -E cannot
# compile - nano uses the same POSIX extended syntax with the same \< \>
# extensions, and a bad rule makes nano print an error at every start.
import re
import subprocess
import sys

if len(sys.argv) != 3:
    sys.exit('usage: mknanosyntax.py <GPL.BP/BCOMP> <out.nanorc>')

BCOMP = sys.argv[1]
OUT = sys.argv[2]

with open(BCOMP, 'r', encoding='latin-1', newline='') as f:
    src = f.read()

# Same tables, same collection rule, as mkbasicsyntax.py.
TABLES = {
    'statements': ['statements'],
    'non.debug.statements': ['non.debug.statements'],
    'restricted.statements': ['restricted.statements'],
    'reserved.names': ['reserved.names'],
    'intrinsics': ['intrinsics'],
}

WORD = re.compile(r'"([A-Z][A-Z0-9.$]*)"')

print('mknanosyntax: reading', BCOMP)
collected = {}
for label, names in TABLES.items():
    words = set()
    for line in src.split('\n'):
        stripped = line.strip()
        if stripped.startswith('*'):
            continue
        for n in names:
            if re.match(re.escape(n) + r'\s*(<[^>]*>)?\s*:?=', stripped):
                words.update(WORD.findall(stripped))
    collected[label] = sorted(words)
    print('  %-24s %d word(s)' % (label, len(words)))
    if not words:
        sys.exit('mknanosyntax: %s came back empty - refusing to write' % label)

statements = sorted(set(collected['statements']) |
                    set(collected['non.debug.statements']) |
                    set(collected['restricted.statements']))
reserved = collected['reserved.names']
intrinsics = collected['intrinsics']


def alt(words):
    """POSIX ERE alternation, LONGEST FIRST so a name is not cut short by a
    shorter one that prefixes it.  "." and "$" are the only metacharacters the
    names can hold, and both are escaped with one backslash - a nanorc regex
    is not a YAML string, so there is no second level of escaping."""
    ordered = sorted(words, key=lambda w: (-len(w), w))
    return '|'.join(w.replace('.', r'\.').replace('$', r'\$') for w in ordered)


# (colour, case-insensitive?, regex, comment).  nano applies rules in order and
# a later rule paints over an earlier one, so comments and strings come LAST:
# a keyword inside a string or a comment must not show as a keyword.
RULES = [
    ('brightcyan', True, r'\<(' + alt(statements) + r')\>',
     'Statements - %d names from BCOMP' % len(statements)),
    ('brightmagenta', True, r'\<(' + alt(reserved) + r')\>',
     'Reserved words inside statements - %d names' % len(reserved)),
    ('brightgreen', True, r'\<(' + alt(intrinsics) + r')\>',
     'Intrinsic functions - %d names' % len(intrinsics)),
    ('yellow', False, r'@[A-Za-z][A-Za-z0-9.]*', '@VARIABLES, @FM and the rest'),
    ('brightred', False, r'^[[:space:]]*\$[A-Za-z][A-Za-z0-9.]*',
     '$INCLUDE, $CATALOG, $INTERNAL - compiler directives'),
    ('cyan', False, r'^[[:space:]]*[A-Za-z][A-Za-z0-9.$]*:', 'Labels'),
    ('brightyellow', False, r'\<[0-9]+(\.[0-9]+)?\>', 'Numbers'),
    ('green', False, r'"[^"]*"', 'Double-quoted strings'),
    ('green', False, r"'[^']*'", 'Single-quoted strings'),
    ('brightblue', False, r'^[[:space:]]*[*!].*',
     'A comment: "*" or "!" first on the line'),
    ('brightblue', False, r';[[:space:]]*\*.*', 'A trailing ";*" comment'),
]

# Prove each regex compiles before writing anything.  GNU grep -E is the probe:
# exit 2 means the expression is invalid, 0 or 1 means it compiled.
bad = 0
for colour, icase, rx, note in RULES:
    p = subprocess.run(['/usr/bin/grep', '-E', '-e', rx, '/dev/null'],
                       capture_output=True, text=True)
    if p.returncode == 2:
        bad += 1
        print('  BAD REGEX (%s): %s' % (note, p.stderr.strip()))
if bad:
    sys.exit('mknanosyntax: %d rule(s) do not compile - refusing to write' % bad)
print('  %d rule(s), all compile under grep -E' % len(RULES))

lines = [
    '## SD BASIC, for the NANO verb of SD Core for Linux.',
    '##',
    '## GENERATED FROM THE COMPILER\'S OWN TABLES by gplbld/mknanosyntax.py, which',
    '## reads sdsys/GPL.BP/BCOMP.  Do not hand-edit: regenerate it, or the',
    '## highlighting and the language drift apart.',
    '##',
    '## DETECTION IS ON THE WORKING COPY\'S NAME, not on the record\'s.  GPL.BP/EDIT',
    '## writes a BP record to $HOLD as "<record>.editing.sdbasic" precisely so',
    '## that this can match.  The installer places this file in /usr/share/nano,',
    '## which /etc/nanorc includes.',
    '##',
    '## KNOWN LIMIT: \\< and \\> are word boundaries, so a name ending in "$" is not',
    '## matched at its end and shows uncoloured.  It costs colour, not correctness.',
    '',
    'syntax sdbasic "\\.sdbasic$"',
    'comment "*"',
    '',
]
for colour, icase, rx, note in RULES:
    lines.append('## ' + note)
    lines.append('%s %s "%s"' % ('icolor' if icase else 'color', colour, rx))
lines.append('')

with open(OUT, 'w', encoding='latin-1', newline='\n') as f:
    f.write('\n'.join(lines))

print('mknanosyntax: wrote', OUT)
