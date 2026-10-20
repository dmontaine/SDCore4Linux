#!/usr/bin/env python3
"""witness-sdnet-probe.py - the wire probe the SDNet witnesses use.  (19 Oct 26, the S.65 finish; from the private w21-apiprobe.py that ran on the
VM on 18 Oct, extended with the second mode.)

    python3 witness-sdnet-probe.py MODE HOST PORT USER PWFILE ACCOUNT FILE ID

Run as an ordinary user, by a witness script that has made the password file (mode 0600, the user's own) and is not printing it.  It loads the
installed client library (WL_SDSYS, default /usr/local/sdsys: bin/sdclilib.so is opened by a relative path, so it changes directory there),
connects over TCP to HOST:PORT as USER, enters ACCOUNT, opens FILE and sends the requests of MODE one at a time:

    files   6 read (control, allowed), 7 readl, 8 readlw, 9 readu, 10 readuw, 16 write, 17 writeu, 18 delete, 19 deleteu, 30 lock record,
            15 release (control, allowed).  The requests the write group governs (S.65).  It WRITES: FILE gets ID-w and ID-wu, and ID is
            deleted, when the login may write; use a scratch file.
    gaps    20 call, 21 execute, 22 respond, 23 end command, 54 transaction, 61 open sequential file, and a SECOND request 3 (SDLogto).  None is
            in the files-only allow table (!apifilesok), so a files-only login must be refused every one whether or not it has the write
            group, and nothing is dispatched.  Request 29 (open SDNet file) has no function in the client library, so it is not sent here;
            gplbld/sandbox-req29.py sends it on the wire.

For each request it prints the call, the library's SDStatus() and SDError() text.  A refusal also prints, from the library itself, a line
"<call> generated an abort event<text of the answer>" (stdout or stderr: the caller redirects both), and the witness anchors its rows on that
text AND on the server's audit line.  Every line this program writes starts with "P " so that the caller can anchor on it; the password is read
from PWFILE and never printed.

Exit 0 when the connection and the open worked (what the rows say is the caller's job), 2 when it could not run (nothing was sent that counts).
"""
import ctypes
import os
import sys

FILES = 'files'
GAPS = 'gaps'


def main(argv):
    if len(argv) != 9 or argv[1] not in (FILES, GAPS):
        print('P USAGE witness-sdnet-probe.py files|gaps HOST PORT USER PWFILE ACCOUNT FILE ID')
        return 2
    mode, host, port, user, pwfile, account, fname, rid = argv[1:9]
    sdsys = os.environ.get('WL_SDSYS', '/usr/local/sdsys')
    try:
        pw = open(pwfile).read().strip().encode()
    except OSError as e:
        print('P CANNOT RUN: the password file cannot be read (%s)' % e)
        return 2
    if not pw:
        print('P CANNOT RUN: the password file is empty')
        return 2
    try:
        sys.path.insert(0, os.path.join(sdsys, 'syscom'))
        os.chdir(os.path.join(sdsys, 'bin'))
        import sdclient as c
    except Exception as e:  # the library or its binding is not where the install puts it
        print('P CANNOT RUN: the client library cannot be loaded (%s)' % e)
        return 2
    rid_b = rid.encode()
    print('P INPUTS mode=%s host=%s port=%s user=%s account=%s file=%s id=%s (password read from %s, not printed)'
          % (mode, host, port, user, account, fname, rid, pwfile))
    sess = c.SDConnect(host.encode(), int(port), user.encode(), pw, account.encode())
    if sess <= 0:
        err = c.SDError()
        print('P CONNECT FAILED session=%s status=%s error=[%s]' % (sess, c.SDStatus(), (err or b'').decode('latin-1')))
        return 2
    print('P CONNECT ok session=%s' % sess)
    fno = c.SDOpen(fname.encode())
    if fno <= 0:
        print('P OPEN FAILED fno=%s status=%s error=[%s]' % (fno, c.SDStatus(), (c.SDError() or b'').decode('latin-1')))
        return 2
    print('P OPEN ok fno=%s' % fno)

    def show(label, extra=''):
        st = c.SDStatus()
        err = (c.SDError() or b'').decode('latin-1').replace('\n', ' ')
        print('P %-30s status=%s %s error=[%s]' % (label, st, extra, err))
        sys.stdout.flush()

    st = ctypes.c_int(0)
    if mode == FILES:
        r = c.SDRead(fno, rid_b, ctypes.byref(st)); show('6 SDRead (control)', 'ret=%s' % (r is not None))
        r = c.SDReadl(fno, rid_b, 0, ctypes.byref(st)); show('7 SDReadl', 'wait=0')
        r = c.SDReadl(fno, rid_b, 1, ctypes.byref(st)); show('8 SDReadl wait', 'wait=1')
        r = c.SDReadu(fno, rid_b, 0, ctypes.byref(st)); show('9 SDReadu', 'wait=0')
        r = c.SDReadu(fno, rid_b, 1, ctypes.byref(st)); show('10 SDReadu wait', 'wait=1')
        c.SDWrite(fno, rid_b + b'-w', b'written by the probe'); show('16 SDWrite')
        c.SDWriteu(fno, rid_b + b'-wu', b'written by the probe'); show('17 SDWriteu')
        c.SDDelete(fno, rid_b); show('18 SDDelete')
        c.SDDeleteu(fno, rid_b); show('19 SDDeleteu')
        c.SDRecordlock(fno, rid_b, 0, 0); show('30 SDRecordlock')
        c.SDRelease(fno, rid_b); show('15 SDRelease (control)')
    else:
        c.SDCall(b'zzprobe', 0); show('20 SDCall')
        c.SDExecute(b'LIST.SERVERS', ctypes.byref(st)); show('21 SDExecute')
        # The library sends 22 and 23 only while a command is executing (it tests the session's context first and returns), and a files-only login
        # cannot be executing one, so these two calls put nothing on the wire: the server is never asked, and the script expects NO refusal for them.
        # The server's refusal of 22 and 23 is proved on the wire by sandbox-net.py (the "never" list).
        c.SDRespond(b'y', ctypes.byref(st)); show('22 SDRespond', '(not sent)')
        c.SDEndCommand(); show('23 SDEndCommand', '(not sent)')
        c.SDTxn(1); show('54 SDTxn')
        c.SDOpenSeq(b'bp', b'zzprobe', 0); show('61 SDOpenSeq')
        c.SDLogto(account.encode()); show('3 SDLogto (the second 3)')
        r = c.SDRead(fno, rid_b, ctypes.byref(st)); show('6 SDRead (control, still allowed)', 'ret=%s' % (r is not None))
    c.SDClose(fno)
    c.SDDisconnect()
    print('P DONE')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
