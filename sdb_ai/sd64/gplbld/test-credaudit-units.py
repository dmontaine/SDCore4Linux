#!/usr/bin/env python3
"""test-credaudit-units.py - S.298: a person's own SD password change is in SD's audit trail.

Windows row 379 audits "cred-own set" and "cred-own refused"; the owner, 22 Nov 2026: "Linux adds them".  The root helper
gplbld/sd-elevate writes the lines itself (cred_audit), so the audit daemon stamps them user=root from the kernel's
credentials and no session can forge one.  Free: no sudo, no install.

  A  the helper through --dry-run on a fixture register (SUDO_USER / SUDO_UID as sudo sets them): a set that is allowed
     prints "audit: cred-own set account=<a>"; a refusal after the caller is proven to be the account prints
     "audit: cred-own refused account=<a> mode=<m> reason=<word>"; a refusal before that (not through sudo, the uid does not
     match) and a query or verify that succeeds print no audit line (the control rows)
  B  the functions between "# BEGIN cred_audit_functions" and its END, cut out and run for real: one datagram
     "SDAUDIT1 ? <text>" on a scratch socket bound by this test; with no daemon, the line appended to a scratch trail with
     user=root; a trail that is a link, or absent, is not written and not created
  C  cred_reason makes one safe word of any message
  D  text: die audits only through CRED_AUDIT_ACCT, which is set after the uid check and cleared after the write

Prints what it ran; a part that ran nothing fails.
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, 'sd-elevate')

rows = 0
fails = 0


def check(row, ok, what, got=''):
    global rows, fails
    rows += 1
    print('  [%s] %s  %s' % ('PASS' if ok else 'FAIL', row, what))
    if not ok:
        fails += 1
        if got:
            print('         got: %s' % got.strip().replace('\n', ' | ')[:300])


def block(text):
    m = re.search(r'(?ms)^# BEGIN cred_audit_functions\n(.*?)^# END cred_audit_functions\n', text)
    return m.group(1) if m else ''


def part_a():
    import base64
    try:
        import pwd
        me = pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        print('  [SKIP] A: this user has no name')
        return
    uid = os.getuid()
    acct = me.lower()
    fx = tempfile.mkdtemp(prefix='credaudit-')
    try:
        os.makedirs(os.path.join(fx, 'accounts'))
        os.makedirs(os.path.join(fx, '$cred'))
        with open(os.path.join(fx, 'accounts', acct), 'w') as f:
            f.write('/home/sd/user_accounts/%s\n\nsdu_%s\n\n\n' % (acct, acct))
        k_old = base64.b64encode(b'\x01' * 32).decode()
        k_new = base64.b64encode(b'\x02' * 32).decode()
        salt = base64.b64encode(b'\x03' * 16).decode()

        def run(mode, lines=None, user=me, u=uid):
            env = dict(os.environ, SD_SYS_ROOT_FIXTURE=fx)
            env.pop('SUDO_USER', None)
            env.pop('SUDO_UID', None)
            if user is not None:
                env['SUDO_USER'] = user
                env['SUDO_UID'] = str(u)
            inp = None if lines is None else '\n'.join(lines) + '\n'
            print('  run: SUDO_USER=%s SUDO_UID=%s bash %s --dry-run cred-own %s (stdin %d lines)' % (user, u, HELPER, mode, 0 if lines is None else len(lines)))
            p = subprocess.run(['bash', HELPER, '--dry-run', 'cred-own', mode], input=inp, capture_output=True, text=True, env=env)
            return p.returncode, (p.stdout or '') + (p.stderr or '')

        def rec(cur, it='600000'):
            return [cur, '2', 'SCRAM-SHA-256', salt, it, k_new, k_new]

        def audits(out):
            return [l for l in out.splitlines() if ': audit: ' in l]

        code, out = run('set', rec(''))
        check('A1', code == 0 and audits(out) == ['sd-elevate: audit: cred-own set account=%s' % acct], 'an allowed first set is audited as set, once', out)
        code, out = run('set', rec('', it='12'))
        check('A2', code != 0 and audits(out) == ['sd-elevate: audit: cred-own refused account=%s mode=set reason=iterations-12-is-outside-4096-10000000' % acct],
              'a refused set (bad input) is audited as refused, with mode and a one-word reason', out)
        code, out = run('set', rec(''), user=None)
        check('A3', code != 0 and 'only through sudo' in out and not audits(out), 'control: not through sudo - refused, no account proven, no audit line', out)
        code, out = run('set', rec(''), u=uid + 1)
        check('A4', code != 0 and 'does not match' in out and not audits(out), 'control: SUDO_UID does not match - refused, no audit line', out)
        code, out = run('query')
        check('A5', code == 0 and not audits(out), 'control: a query that succeeds writes no audit line', out)
        with open(os.path.join(fx, '$cred', acct), 'w') as f:
            f.write('2\nSCRAM-SHA-256\n%s\n600000\n%s\n%s\n' % (salt, k_old, k_old))
        code, out = run('verify', [k_new])
        check('A6', code != 0 and audits(out) == ['sd-elevate: audit: cred-own refused account=%s mode=verify reason=the-current-password-is-not-correct' % acct],
              'a wrong current password at verify is audited as refused', out)
        code, out = run('verify', [k_old])
        check('A7', code == 0 and not audits(out), 'control: a right current password at verify writes no audit line', out)
        code, out = run('set', rec(k_new))
        check('A8', code != 0 and 'mode=set reason=the-current-password-is-not-correct' in out, 'a wrong current password at set is audited as refused', out)
        code, out = run('set', rec(k_old))
        check('A9', code == 0 and audits(out) == ['sd-elevate: audit: cred-own set account=%s' % acct], 'the right current password: audited as set', out)
        code, out = run('bogus')
        check('A10', code != 0 and 'mode=other reason=' in out, 'an unknown mode is audited with mode=other, never the typed word', out)
    finally:
        shutil.rmtree(fx, ignore_errors=True)


def bash_fn(fns, sock, sysdir, call):
    script = 'PROG=sd-elevate\nDRY=0\nSD_AUDIT_SOCK_REAL=%s\nSD_SYS_ROOT=%s\nlogger() { printf "LOGGER %%s\\n" "$*"; }\n%s\n%s\n' % (sock, sysdir, fns, call)
    p = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def part_b(fns):
    d = tempfile.mkdtemp(prefix='credaudit-b-')
    try:
        sock = os.path.join(d, 'audit.sock')
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        srv.bind(sock)
        srv.settimeout(5)
        sysdir = os.path.join(d, 'sys')
        os.makedirs(sysdir)
        print('  B: socket %s, trail %s/audit' % (sock, sysdir))
        code, out = bash_fn(fns, sock, sysdir, 'cred_audit "cred-own set account=zed"')
        try:
            data = srv.recv(4096)
        except socket.timeout:
            data = b''
        check('B1', code == 0 and data == b'SDAUDIT1 ? cred-own set account=zed', 'one datagram, AUDIT_MAGIC "? " and the text', data.decode(errors='replace') + ' ' + out)
        check('B1a', not os.path.exists(os.path.join(sysdir, 'audit')), 'with the daemon there, the trail itself is not touched')
        srv.close()
        os.unlink(sock)
        trail = os.path.join(sysdir, 'audit')
        with open(trail, 'w') as f:
            f.write('earlier line\n')
        code, out = bash_fn(fns, sock, sysdir, 'cred_audit "cred-own refused account=zed mode=set reason=x"')
        with open(trail) as f:
            lines = f.read().splitlines()
        ok = len(lines) == 2 and lines[0] == 'earlier line' and re.match(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d user=root( sudo=\S+)? uid=\? pid=\d+ cred-own refused account=zed mode=set reason=x$', lines[1])
        check('B2', code == 0 and bool(ok), 'no daemon: the line is appended to the trail as the daemon writes it, user=root', '\n'.join(lines) + ' ' + out)
        os.unlink(trail)
        code, out = bash_fn(fns, sock, sysdir, 'cred_audit "cred-own set account=zed"')
        check('B3', code == 0 and not os.path.exists(trail) and 'LOGGER -t sd-elevate cred-own: the audit line was not written: cred-own set account=zed' in out, 'no daemon and no trail: nothing is created; the system log says so', out)
        target = os.path.join(d, 'elsewhere')
        open(target, 'w').close()
        os.symlink(target, trail)
        code, out = bash_fn(fns, sock, sysdir, 'cred_audit "cred-own set account=zed"')
        check('B4', code == 0 and os.path.getsize(target) == 0, 'a trail that is a link is not written through')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def part_c(fns):
    cases = [
        ("the current password is not correct", "the-current-password-is-not-correct"),
        ("'$acct' has a password; the current one is required", "acct-has-a-password-the-current-one-is-required"),
        ("x" * 100, "x" * 60),
        ("$(id) ; rm -rf / = account=root", "id-rm-rf-account-root"),
    ]
    for i, (msg, want) in enumerate(cases, 1):
        code, out = bash_fn(fns, '/nonexistent', '/nonexistent', 'cred_reason %s' % shlex_quote(msg))
        check('C%d' % i, out == want, 'cred_reason %r -> %r' % (msg[:40], want), out)


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


def part_d(text):
    m = re.search(r'(?ms)^die\(\) \{\n(.*?)^\}', text)
    die = m.group(1) if m else ''
    check('D1', 'CRED_AUDIT_ACCT' in die and 'cred_audit "cred-own refused account=' in die and die.find('cred_audit') < die.find('exit 2'), 'die audits a cred-own refusal before it exits, only when CRED_AUDIT_ACCT is set')
    m = re.search(r'(?ms)^cred_own\(\) \{\n(.*?)^\}', text)
    co = m.group(1) if m else ''
    i_uid = co.find('does not match SUDO_UID')
    i_set = co.find('CRED_AUDIT_ACCT=$acct')
    i_write = co.find('mv -f -- "$tmp" "$cfile"')
    i_clear = co.find("CRED_AUDIT_ACCT=''")
    i_aud = co.rfind('cred_audit "cred-own set account=$acct"')
    check('D2', 0 < i_uid < i_set < i_write < i_clear < i_aud, 'CRED_AUDIT_ACCT is set after the uid check, cleared after the write, and the set line comes after that')
    fns = block(text)
    sh = re.sub(r"(?s)python3 -I -c '.*?' ", ' ', fns)          # the shell of the block, the Python's own sys.exit taken out
    sh = re.sub(r'(?m)#.*$', '', sh)                            # and its comments ("Nothing here calls die")
    check('D3', 'python3 -I -c' in fns and not re.search(r'\b(die|exit)\b', sh), 'the audit functions never call die or exit (the shell; the embedded Python is not the shell)', sh)


def main():
    print('test-credaudit-units: helper %s' % HELPER)
    if not os.path.isfile(HELPER):
        print('FAIL: the helper is missing; nothing was checked')
        return 1
    with open(HELPER) as f:
        text = f.read()
    fns = block(text)
    if not fns:
        print('FAIL: no "# BEGIN cred_audit_functions" block; nothing was checked')
        return 1
    part_a()
    part_b(fns)
    part_c(fns)
    part_d(text)
    if rows == 0:
        print('FAIL: no row ran')
        return 1
    print('test-credaudit-units: %d rows, %d failed' % (rows, fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
