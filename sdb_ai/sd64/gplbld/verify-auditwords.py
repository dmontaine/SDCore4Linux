#!/usr/bin/env python3
"""verify-auditwords.py - every EVENT WORD in the install's own audit file is lower case.

    sudo python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/verify-auditwords.py
    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/verify-auditwords.py --selftest
    sudo python3 .../verify-auditwords.py --file /usr/local/sdsys/audit.1      (a rotated file)

WHY.  PAL-24 stage 1 (owner, 7 Oct 2026: "All lower case") made the audit trail's event words lower
case, and test-auditwords-units.py proves it from the SOURCE (every kernel(K$AUDIT, ...) call in
gpl.bp).  A source scan cannot see a word that reaches the trail through a variable or a program the
scan does not cover, so this reads what the install actually WROTE.  Taken from the Windows port's
verify-auditwords.ps1 (its mail 2026-10-08T2400, item 3): the same line shape, the same rule.

A RECORD is  YYYY-MM-DD HH:MM:SS user=NAME [sudo=NAME] uid=N pid=N <event words> key=value ...
(gplsrc/k_error.c audit_message).  The EVENT WORDS are the tokens before the first token that holds
an '=' - the same cut as test-auditwords-units.py's head_of.  A value after an '=' is what a person
typed (an account name, a reason) and keeps its case.  A record with no key=value at all has only its
first token checked (a typed argument may follow it, as in Solo's  deny.verbs add WHO - now who).

THE FILE IS sdsys:sdusers 0620 - an ordinary user cannot read it, so this is run with sudo, and
prints what it was given: the path, its size, how many lines it read, how many it could not parse.
It refuses the null case out loud: a missing, unreadable or empty file, or one with no parsable
record, is exit 2 and not a pass.

--selftest needs no install: it runs the rule over a fixture and breaks it each way (mutants) and
every one must be caught, with the controls (a capital in a VALUE, a typed argument) passing.
Exit 0 pass, 1 a capital was found (or a mutant escaped), 2 nothing could be measured."""
import os
import re
import sys

DEFAULT = '/usr/local/sdsys/audit'
RECORD = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) user=(\S+?)(?: sudo=(\S+))? uid=(\S+) pid=(\S+) (.+)$')
HERE = os.path.dirname(os.path.abspath(__file__))
GPL = os.path.normpath(os.path.join(HERE, '..', 'sdsys', 'gpl.bp'))
CALL = re.compile(r"kernel\(\s*K\$AUDIT\s*,\s*'([^']*)'")


def event_words(msg):
    """The tokens before the first token holding '='; with none, only the first token."""
    toks = [t for t in msg.split(' ') if t != '']
    words = []
    for t in toks:
        if '=' in t:
            return words, True
        words.append(t)
    return words[:1], False


def check(lines):
    """Returns (parsed, unparsed, [(line number, event words, text)], {head: count}, no_kv)."""
    parsed = 0
    unparsed = []
    bad = []
    heads = {}
    no_kv = 0
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip('\n')
        if line == '':
            continue
        m = RECORD.match(line)
        if not m:
            unparsed.append((n, line))
            continue
        parsed += 1
        words, has_kv = event_words(m.group(6))
        if not has_kv:
            no_kv += 1
        head = ' '.join(words)
        heads[head.lower()] = heads.get(head.lower(), 0) + 1
        if re.search(r'[A-Z]', head):
            bad.append((n, head, line))
    return parsed, unparsed, bad, heads, no_kv


def source_heads():
    """The event heads the source can write (literal text before the first '='), for NOT SEEN."""
    out = set()
    if not os.path.isdir(GPL):
        return out
    for name in os.listdir(GPL):
        p = os.path.join(GPL, name)
        if not os.path.isfile(p):
            continue
        with open(p, 'rb') as fh:
            for line in fh.read().decode('utf-8', 'replace').split('\n'):
                if line.strip().startswith('*'):
                    continue
                m = CALL.search(line)
                if m:
                    words = []
                    for t in m.group(1).split(' '):
                        if t == '' or '=' in t:
                            break
                        words.append(t)
                    if words:
                        out.add(' '.join(words).lower())
    return out


def measure(path):
    print('verify-auditwords: reading %s' % path)
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as fh:
            text = fh.read().decode('utf-8', 'replace')
    except OSError as e:
        print('verify-auditwords: NOTHING MEASURED - cannot read the file (%s). It is sdsys:sdusers 0620: run with sudo.' % e)
        return 2
    lines = text.split('\n')
    parsed, unparsed, bad, heads, no_kv = check(lines)
    print('  size %d bytes, %d lines, %d records parsed, %d not parsed, %d with no key=value (first token checked)'
          % (size, len([x for x in lines if x != '']), parsed, len(unparsed), no_kv))
    if parsed == 0:
        print('verify-auditwords: NOTHING MEASURED - no record in the file parsed (a reader that sees nothing is broken, or the file is empty).')
        return 2
    for h in sorted(heads):
        print('  %5d  %s' % (heads[h], h))
    want = source_heads()
    if want:
        seen = sorted(w for w in want if w in heads)
        miss = sorted(w for w in want if w not in heads)
        print('  events the source can write: %d, seen in this file: %d' % (len(want), len(seen)))
        for w in miss:
            print('    NOT SEEN: %s' % w)
    for n, line in unparsed[:5]:
        print('  [UNPARSED line %d] %s' % (n, line[:160]))
    for n, head, line in bad[:10]:
        print('  [FAIL line %d] event words "%s" hold a capital: %s' % (n, head, line[:200]))
    if bad:
        print('verify-auditwords: FAIL - %d record(s) with a capital in the event words' % len(bad))
        return 1
    if unparsed:
        print('verify-auditwords: FAIL - %d line(s) are not audit records (the reader and the writer disagree)' % len(unparsed))
        return 1
    print('verify-auditwords: PASS - %d records, every event word lower case' % parsed)
    return 0


GOOD = [
    '2026-10-08 18:46:01 user=don uid=1000 pid=4242 login account=don',
    '2026-10-08 18:46:02 user=? uid=? pid=? login refused account=zz reason=wrong password',
    '2026-10-08 18:46:03 user=sdsys sudo=don uid=1005 pid=7 elevation granted reason=sdsys login',
    '2026-10-08 18:46:04 user=don uid=1000 pid=9 api refused user=Fred reason=No Credential',
    '2026-10-08 18:46:05 user=don uid=1000 pid=9 modify.account add account=ZZUser',
    '2026-10-08 18:46:06 user=don uid=1000 pid=9 deny.verbs add WHO - now who',
]


def selftest():
    ok = bad = 0

    def row(name, cond, detail=''):
        nonlocal ok, bad
        if cond:
            ok += 1
            print('  [PASS] ' + name)
        else:
            bad += 1
            print('  [FAIL] ' + name + ('   <- ' + detail if detail else ''))

    def verdict(lines):
        parsed, unparsed, found, _, _ = check(lines)
        return parsed, len(unparsed), len(found)

    p, u, f = verdict(GOOD)
    row('control: the fixture (capitals only in VALUES and a typed argument) parses 6, no failure', (p, u, f) == (6, 0, 0), repr((p, u, f)))
    p, u, f = verdict([GOOD[0].replace('login account', 'LOGIN account')])
    row('mutant: a capital first event word is caught', f == 1, repr((p, u, f)))
    p, u, f = verdict([GOOD[1].replace('login refused', 'login Refused')])
    row('mutant: a capital second event word is caught', f == 1, repr((p, u, f)))
    p, u, f = verdict([GOOD[2].replace('elevation granted', 'Elevation granted')])
    row('mutant: a capital on a record with a sudo= stamp is caught', f == 1, repr((p, u, f)))
    p, u, f = verdict([GOOD[3].replace('api refused', 'API refused')])
    row('mutant: the 7 Oct case (API REFUSED) is caught', f == 1, repr((p, u, f)))
    p, u, f = verdict([GOOD[5].replace('deny.verbs', 'Deny.verbs')])
    row('mutant: a capital first token of a record with no key=value is caught', f == 1, repr((p, u, f)))
    p, u, f = verdict(['2026-10-08 18:46:07 pid=1 login account=don'])
    row('mutant: a line that is not a record counts as unparsed, not as a pass', (p, u, f) == (0, 1, 0), repr((p, u, f)))
    p, u, f = verdict([])
    row('null case: no lines parse nothing', (p, u, f) == (0, 0, 0), repr((p, u, f)))
    import tempfile
    d = tempfile.mkdtemp(prefix='auditwords-')
    try:
        for label, content, want in (('an empty file', '', 2), ('a file with no record', 'garbage\n', 2),
                                     ('a good file', '\n'.join(GOOD) + '\n', 0),
                                     ('a file with one capital', '\n'.join(GOOD[:2] + [GOOD[0].replace('login', 'Login')]) + '\n', 1)):
            fp = os.path.join(d, 'audit')
            with open(fp, 'w') as fh:
                fh.write(content)
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = measure(fp)
            row('end to end: %s exits %d' % (label, want), rc == want, 'exit %d' % rc)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = measure(os.path.join(d, 'no-such-file'))
        row('end to end: a missing file exits 2 and says so', rc == 2 and 'NOTHING MEASURED' in buf.getvalue(), 'exit %d' % rc)
    finally:
        for name in os.listdir(d):
            os.remove(os.path.join(d, name))
        os.rmdir(d)
    print('verify-auditwords --selftest: %d passed, %d failed' % (ok, bad))
    return 0 if bad == 0 else 1


def main(argv):
    if '--selftest' in argv:
        return selftest()
    path = DEFAULT
    if '--file' in argv:
        i = argv.index('--file')
        if i + 1 >= len(argv):
            print('verify-auditwords: --file needs a path')
            return 2
        path = argv[i + 1]
    return measure(path)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
