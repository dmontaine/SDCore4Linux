#!/usr/bin/env python3
"""verify-auditwords.py - every EVENT WORD this install wrote to its audit file is lower case.

    sudo python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/verify-auditwords.py
    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/verify-auditwords.py --selftest
    sudo python3 .../verify-auditwords.py --since '2026-10-08 15:06:45'     (judge from this moment on)
    sudo python3 .../verify-auditwords.py --all                              (judge the whole file)
    sudo python3 .../verify-auditwords.py --file /usr/local/sdsys/audit.1    (a rotated file)
    python3 .../verify-auditwords.py --file /home/USER/SDCoreSolo/audit      (SD Core for Linux Solo: the
        file is the user's own, no sudo; its stamp is the "date" line of ~/SDCoreSolo/.sdcore-install.
        The same file is kept byte-identical in both Linux trees.)

WHY.  PAL-24 stage 1 (owner, 7 Oct 2026: "All lower case") made the audit trail's event words lower
case, and test-auditwords-units.py proves it from the SOURCE (every kernel(K$AUDIT, ...) call in
gpl.bp).  A source scan cannot see a word that reaches the trail through a variable or a program the
scan does not cover, so this reads what the install actually WROTE.  Taken from the Windows port's
verify-auditwords.ps1 (its mail 2026-10-08T2400, item 3): the same line shape, the same rule.

THE FILE OUTLIVES THE INSTALL.  A keep-accounts reinstall keeps /usr/local/sdsys/audit, so it holds
records written by older builds - the owner's first run, 8 Oct, found 258 capitals, all of them from
4 Oct, three days before the change.  So the verdict is on the records written BY THIS INSTALL:
those stamped at or after  installed=  in /usr/local/sdsys/.sdcore-install (the file
assert-current.py reads), or after --since.  THE OLDER RECORDS ARE NOT HIDDEN: it prints how many
there are, how many hold a capital and the newest such one, so a capital that is NOT history is seen
at once.  --all judges everything (and fails on history); with no stamp and no --since it judges
everything and says why.

A RECORD is  YYYY-MM-DD HH:MM:SS user=NAME [sudo=NAME] uid=N pid=N <event words> key=value ...
(gplsrc/k_error.c audit_message).  The EVENT WORDS are the tokens before the first token that holds
an '=' - the same cut as test-auditwords-units.py's head_of - AND the key word itself (the text up
to the first '='), which is also SD's: a capital in  Account=  fails (decided 9 Oct, as Windows does).  A value after an '=' is what a person
typed (an account name, a reason) and keeps its case.  A record with no key=value at all has only its
first token checked (a typed argument may follow it, as in Solo's  deny.verbs add WHO - now who).

THE FILE IS sdsys:sdusers 0620 - an ordinary user cannot read it, so this is run with sudo, and
prints what it was given: the path, its size, how many lines it read, how many it could not parse.
It refuses the null case out loud: a missing, unreadable or empty file, a file with no parsable
record, or a scope (--since) that leaves no record to judge, is exit 2 and not a pass.

--selftest needs no install: it runs the rule over a fixture and breaks it each way (mutants) and
every one must be caught, with the controls (a capital in a VALUE, a typed argument, a capital
older than the scope) passing.
CONTROL (taken from the Windows port, 9 Oct): at least one judged record must start with the word
login, or it is a FAIL - a reader that recognises nothing must not pass.
Exit 0 pass, 1 a capital was found in the judged records, no login record, or a mutant escaped,
2 nothing measured."""
import os
import re
import sys

DEFAULT = '/usr/local/sdsys/audit'
STAMP_NAME = '.sdcore-install'
RECORD = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) user=(\S+?)(?: sudo=(\S+))? uid=(\S+) pid=(\S+) (.+)$')
STAMP_FORMAT = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$')
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


def check(lines, since=None):
    """Returns a dict: judged, older, unparsed, bad (judged records with a capital), older_bad,
    heads (raw event words of the judged records -> count), no_kv.  A record is OLDER when its
    stamp sorts before `since` (the stamps are fixed-width, so a string compare is a time compare)."""
    r = {'judged': 0, 'older': 0, 'unparsed': [], 'bad': [], 'older_bad': [], 'heads': {}, 'no_kv': 0}
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip('\n')
        if line == '':
            continue
        m = RECORD.match(line)
        if not m:
            r['unparsed'].append((n, line))
            continue
        words, has_kv = event_words(m.group(6))
        head = ' '.join(words)
        # the key word before the first '=' is SD's own word too (Windows judges it, 9 Oct): Account= fails
        cut = m.group(6).split('=', 1)[0] if has_kv else head
        capital = re.search(r'[A-Z]', cut) is not None
        if since is not None and m.group(1) < since:
            r['older'] += 1
            if capital:
                r['older_bad'].append((n, m.group(1), head))
            continue
        r['judged'] += 1
        if not has_kv:
            r['no_kv'] += 1
        r['heads'][head] = r['heads'].get(head, 0) + 1
        if capital:
            r['bad'].append((n, head, line))
    return r


def login_count(heads):
    """The control (Windows verify-auditwords.ps1 has it): records whose first event word is login,
    case blind - a capital one is caught by the main rule, this only asks that the reader saw a sign-in."""
    return sum(n for h, n in heads.items() if h.lower().split(' ')[0] == 'login')


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


def not_seen(want, heads):
    """Splits the source's event heads into seen and not seen.  A written head may carry a value after
    the words the source holds (modify.account route api, the route being a word, not a key=value)."""
    have = [h.lower() for h in heads]
    seen = sorted(w for w in want if any(h == w or h.startswith(w + ' ') for h in have))
    return seen, sorted(w for w in want if w not in seen)


SOLO_DATE = re.compile(r'^(\d{4}-\d\d-\d\d)T(\d\d:\d\d:\d\d)')


def stamp_installed(audit_path):
    """(installed time, stamp path) from the install stamp beside the audit file, or (None, path).
    The full product writes  installed=YYYY-MM-DD HH:MM:SS;  Solo writes  date 2026-10-08T18:28:12-07:00
    (the audit's own stamps are local time, so the date and time are taken as written)."""
    sp = os.path.join(os.path.dirname(os.path.abspath(audit_path)), STAMP_NAME)
    try:
        with open(sp, 'r', encoding='utf-8') as fh:
            for line in fh.read().splitlines():
                line = line.strip()
                if line.startswith('installed='):
                    v = line.split('=', 1)[1].strip()
                    if STAMP_FORMAT.match(v):
                        return v, sp
                elif line.startswith('date '):
                    m = SOLO_DATE.match(line[5:].strip())
                    if m:
                        return m.group(1) + ' ' + m.group(2), sp
    except OSError:
        pass
    return None, sp


def measure(path, since=None, judge_all=False):
    print('verify-auditwords: reading %s' % path)
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as fh:
            text = fh.read().decode('utf-8', 'replace')
    except OSError as e:
        print('verify-auditwords: NOTHING MEASURED - cannot read the file (%s). It is sdsys:sdusers 0620: run with sudo.' % e)
        return 2
    if judge_all:
        scope = None
        print('  scope: the WHOLE file (--all) - older builds\' records are judged too')
    elif since is not None:
        scope = since
        print('  scope: records stamped %s or later (--since)' % scope)
    else:
        scope, sp = stamp_installed(path)
        if scope is None:
            print('  scope: the WHOLE file - no usable install time in %s, and no --since' % sp)
        else:
            print('  scope: records stamped %s or later (the install time in %s)' % (scope, sp))
    lines = text.split('\n')
    r = check(lines, scope)
    total = r['judged'] + r['older'] + len(r['unparsed'])
    print('  size %d bytes, %d lines: %d judged, %d older than the scope (not judged), %d not parsed; %d judged with no key=value (first token checked)'
          % (size, len([x for x in lines if x != '']), r['judged'], r['older'], len(r['unparsed']), r['no_kv']))
    if r['older']:
        if r['older_bad']:
            n, t, h = r['older_bad'][-1]
            print('  older records with a capital: %d; the NEWEST is line %d at %s: "%s"' % (len(r['older_bad']), n, t, h))
        else:
            print('  older records with a capital: 0')
    if r['judged'] == 0:
        print('verify-auditwords: NOTHING MEASURED - no record %s (a reader that judges nothing proves nothing).'
              % ('parsed' if total == 0 or r['older'] == 0 else 'is at or after the scope'))
        return 2
    for h in sorted(r['heads']):
        print('  %5d  %s' % (r['heads'][h], h))
    logins = login_count(r['heads'])
    print('  control: %d judged "login" record(s)' % logins)
    want = source_heads()
    if want:
        seen, miss = not_seen(want, r['heads'])
        print('  events the source can write: %d, seen in the judged records: %d' % (len(want), len(seen)))
        for w in miss:
            print('    NOT SEEN: %s' % w)
    for n, line in r['unparsed'][:5]:
        print('  [UNPARSED line %d] %s' % (n, line[:160]))
    for n, head, line in r['bad'][:10]:
        print('  [FAIL line %d] event words "%s" hold a capital: %s' % (n, head, line[:200]))
    if r['bad']:
        print('verify-auditwords: FAIL - %d judged record(s) with a capital in the event words' % len(r['bad']))
        return 1
    if r['unparsed']:
        print('verify-auditwords: FAIL - %d line(s) are not audit records (the reader and the writer disagree)' % len(r['unparsed']))
        return 1
    if logins == 0:
        print('verify-auditwords: FAIL - CONTROL: no "login" record among the judged ones, so this reader may be recognising nothing (a sign-in writes one)')
        return 1
    print('verify-auditwords: PASS - %d judged records, every event word lower case' % r['judged'])
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
    import contextlib
    import io
    import tempfile
    ok = bad = 0

    def row(name, cond, detail=''):
        nonlocal ok, bad
        if cond:
            ok += 1
            print('  [PASS] ' + name)
        else:
            bad += 1
            print('  [FAIL] ' + name + ('   <- ' + detail if detail else ''))

    def verdict(lines, since=None):
        r = check(lines, since)
        return r['judged'], len(r['unparsed']), len(r['bad']), r['older'], len(r['older_bad'])

    row('control: the fixture (capitals only in VALUES and a typed argument) judges 6, no failure',
        verdict(GOOD) == (6, 0, 0, 0, 0), repr(verdict(GOOD)))
    for label, i, a, b in (('a capital first event word', 0, 'login account', 'LOGIN account'),
                           ('a capital second event word', 1, 'login refused', 'login Refused'),
                           ('a capital on a record with a sudo= stamp', 2, 'elevation granted', 'Elevation granted'),
                           ('the 7 Oct case (API REFUSED)', 3, 'api refused', 'API refused'),
                           ('a capital first token of a record with no key=value', 5, 'deny.verbs', 'Deny.verbs')):
        v = verdict([GOOD[i].replace(a, b)])
        row('mutant: %s is caught' % label, v == (1, 0, 1, 0, 0), repr(v))
    v = verdict([GOOD[0].replace('account=', 'Account=')])
    row('mutant: a capital KEY word (Account=) is caught', v == (1, 0, 1, 0, 0), repr(v))
    v = verdict([GOOD[3].replace('user=Fred', 'user=Fred Reason=x')])
    row('control: a capital in a VALUE or after the first key is not judged', v == (1, 0, 0, 0, 0), repr(v))
    v = verdict(['2026-10-08 18:46:07 pid=1 login account=don'])
    row('mutant: a line that is not a record counts as unparsed, not as a pass', v == (0, 1, 0, 0, 0), repr(v))
    v = verdict([])
    row('null case: no lines judge nothing', v == (0, 0, 0, 0, 0), repr(v))
    old = '2026-10-04 14:59:25 user=root sudo=don uid=2 pid=54875 LOGIN account=sdsys'
    v = verdict([old] + GOOD, '2026-10-08 15:06:45')
    row('control: a capital OLDER than the scope is counted, reported, and not judged', v == (6, 0, 0, 1, 1), repr(v))
    v = verdict([old] + GOOD, '2026-10-04 00:00:00')
    row('mutant: the same capital INSIDE the scope is judged and caught', v == (7, 0, 1, 0, 0), repr(v))
    v = verdict(GOOD + [old.replace('2026-10-04 14:59:25', '2026-10-08 18:59:00')], '2026-10-08 15:06:45')
    row('mutant: a capital stamped after the scope is caught even when older ones exist', v[2] == 1, repr(v))
    v = verdict(GOOD, '2027-01-01 00:00:00')
    row('null case: a scope after every record judges nothing', v == (0, 0, 0, 6, 0), repr(v))
    seen, miss = not_seen({'modify.account route', 'remote.ssh', 'login'}, {'modify.account route api': 3, 'LOGIN': 1})
    row('NOT SEEN: a head with a value after it counts as seen, and a head never written does not',
        seen == ['login', 'modify.account route'] and miss == ['remote.ssh'], repr((seen, miss)))
    d = tempfile.mkdtemp(prefix='auditwords-')
    fp = os.path.join(d, 'audit')

    def e2e(content, want, label, **kw):
        with open(fp, 'w') as fh:
            fh.write(content)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = measure(fp, **kw)
        row('end to end: %s exits %d' % (label, want), rc == want, 'exit %d' % rc)
        return buf.getvalue()

    try:
        e2e('', 2, 'an empty file')
        e2e('garbage\n', 2, 'a file with no record')
        e2e('\n'.join(GOOD) + '\n', 0, 'a good file with no stamp (judges all)')
        e2e('\n'.join(GOOD[:2] + [GOOD[0].replace('login', 'Login')]) + '\n', 1, 'a file with one capital')
        text = e2e('\n'.join(GOOD[3:]) + '\n', 1, 'lower-case records but no login (the control)')
        row('...and it names the control', 'CONTROL' in text)
        row('control: "api login" is not a sign-in', login_count({'api login': 2, 'login refused': 1, 'Login': 1}) == 2)
        text = e2e(old + '\n' + '\n'.join(GOOD) + '\n', 1, 'history with a capital and no stamp (judges all, fails)')
        row('...and it says the whole file was judged because no stamp exists', 'no usable install time' in text)
        with open(os.path.join(d, STAMP_NAME), 'w') as fh:
            fh.write('commit 5f9d1fb\ndate 2026-10-08T18:28:12-07:00\nmode unmanaged\n')
        text = e2e(old + '\n' + '\n'.join(GOOD) + '\n', 0, 'history with a capital before a SOLO-format stamp')
        row('...and the Solo stamp\'s scope is read as written, not shifted', 'records stamped 2026-10-08 18:28:12 or later' in text)
        with open(os.path.join(d, STAMP_NAME), 'w') as fh:
            fh.write('commit=abc\ninstalled=2026-10-08 15:06:45\n')
        text = e2e(old + '\n' + '\n'.join(GOOD) + '\n', 0, 'history with a capital before the install stamp')
        row('...and it still prints the older capital (not hidden)', 'older records with a capital: 1' in text and '2026-10-04 14:59:25' in text)
        e2e(old + '\n' + '\n'.join(GOOD) + '\n', 1, 'the same file with --all', judge_all=True)
        e2e(old.replace('2026-10-04 14:59:25', '2026-10-08 16:00:00') + '\n' + '\n'.join(GOOD) + '\n', 1,
            'a capital written after the install stamp')
        e2e('\n'.join(GOOD) + '\n', 2, 'a stamp after every record (nothing to judge)', since='2027-01-01 00:00:00')
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
    since = None
    if '--file' in argv:
        i = argv.index('--file')
        if i + 1 >= len(argv):
            print('verify-auditwords: --file needs a path')
            return 2
        path = argv[i + 1]
    if '--since' in argv:
        i = argv.index('--since')
        if i + 1 >= len(argv) or not STAMP_FORMAT.match(argv[i + 1]):
            print("verify-auditwords: --since needs 'YYYY-MM-DD HH:MM:SS'")
            return 2
        since = argv[i + 1]
    return measure(path, since, '--all' in argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
