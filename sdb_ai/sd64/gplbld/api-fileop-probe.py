#!/usr/bin/env python3
"""api-fileop-probe.py - one SD API session that opens ONE file and reads, writes or deletes records in it through the installed client library.

3 Nov 2026 (track G, the testing phase).  api-probe.py runs TCL commands (SDExecute), so a refusal it sees is the kernel's, inside a command.  The
API server ALSO guards the file requests it serves itself (apisrvr's check.edit, S.64 part 2: its program is $internal, which the kernel's edit
test lets through), and the shared account's door (S.66, 11513) is the same routine.  Those are reached only by SDOpen / SDWrite / SDDelete, which
this probe sends.  witness-release-run.sh sections 13o and 13p use it.

  SD_PROBE_PASSWORD=... python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/api-fileop-probe.py \\
      --user <name> --account <name> --file <name> OP...

  OP is  read:ID   write:ID=TEXT   delete:ID     (TEXT has no field marks: one field)

No sudo of its own; the password comes from the environment, never the command line, and only its length is printed.

IT PRINTS WHAT IT DID: the library, host, port, user, account and file it passed; SDConnect's and SDOpen's return values; for each op the call, SDStatus()
and SDError()'s text (a refusal's reason), and what a read returned.  Lines it writes start with "P " (the caller anchors on them).

Exit 0 connected, opened and sent every op (what the answers MEAN is the caller's to judge); 1 the connection or the open was refused; 2 it could not run
(no password, no library, no op: a session that sends nothing measures nothing).
"""

import argparse
import ctypes
import os
import sys

DEFAULT_LIB = "/usr/local/sdsys/bin/sdclilib.so"


def say(text):
    print("P " + text)
    sys.stdout.flush()


def text_of(raw):
    return raw.decode("utf-8", errors="replace") if raw else ""


def main(argv):
    ap = argparse.ArgumentParser(description="One SD API session: open a file and read, write or delete records.")
    ap.add_argument("--lib", default=DEFAULT_LIB)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4247)
    ap.add_argument("--user", required=True)
    ap.add_argument("--account", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("ops", nargs="*")
    a = ap.parse_args(argv)

    pw = os.environ.get("SD_PROBE_PASSWORD")
    say("api-fileop-probe")
    say("  lib      : %s" % a.lib)
    say("  host     : %s  port %d" % (a.host, a.port))
    say("  user     : %s   account: %s   file: %s" % (a.user, a.account, a.file))
    say("  password : %s" % ("from SD_PROBE_PASSWORD, %d characters" % len(pw) if pw is not None else "SD_PROBE_PASSWORD is not set"))
    say("  ops      : %s" % (" ".join(a.ops) or "(none)"))
    if pw is None:
        say("CANNOT RUN - SD_PROBE_PASSWORD is not set.")
        return 2
    if not a.ops:
        say("CANNOT RUN - no op: a session that sends nothing measures nothing.")
        return 2
    for op in a.ops:
        kind = op.split(":", 1)[0]
        if kind not in ("read", "write", "delete") or ":" not in op or (kind == "write" and "=" not in op):
            say("CANNOT RUN - the op %r is not read:ID, write:ID=TEXT or delete:ID" % op)
            return 2
    try:
        lib = ctypes.CDLL(a.lib)
    except OSError as e:
        say("CANNOT RUN - cannot load %s: %s" % (a.lib, e))
        return 2

    lib.SDConnect.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.SDConnect.restype = ctypes.c_int
    lib.SDError.argtypes = []
    lib.SDError.restype = ctypes.c_char_p
    lib.SDStatus.argtypes = []
    lib.SDStatus.restype = ctypes.c_int
    lib.SDOpen.argtypes = [ctypes.c_char_p]
    lib.SDOpen.restype = ctypes.c_int
    lib.SDRead.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    lib.SDRead.restype = ctypes.c_char_p
    lib.SDWrite.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p]
    lib.SDWrite.restype = None
    lib.SDDelete.argtypes = [ctypes.c_int, ctypes.c_char_p]
    lib.SDDelete.restype = None
    lib.SDClose.argtypes = [ctypes.c_int]
    lib.SDClose.restype = None
    lib.SDDisconnect.argtypes = []
    lib.SDDisconnect.restype = None

    rc = lib.SDConnect(a.host.encode(), a.port, a.user.encode(), pw.encode(), a.account.encode())
    say("SDConnect returned %d" % rc)
    if not rc:
        say("SDError: %s" % text_of(lib.SDError()))
        return 1
    fno = lib.SDOpen(a.file.encode())
    say("SDOpen(%s) returned %d  status %d  error: %s" % (a.file, fno, lib.SDStatus(), text_of(lib.SDError()) if not fno else ""))
    if not fno:
        lib.SDDisconnect()
        say("disconnected")
        return 1
    for op in a.ops:
        kind, rest = op.split(":", 1)
        if kind == "read":
            err = ctypes.c_int(0)
            out = text_of(lib.SDRead(fno, rest.encode(), ctypes.byref(err)))
            say("SDRead(%s) err %d  status %d  record: [%s]" % (rest, err.value, lib.SDStatus(), out.replace("\xfe", "^")))
        elif kind == "write":
            rid, data = rest.split("=", 1)
            lib.SDWrite(fno, rid.encode(), data.encode())
            st = lib.SDStatus()
            say("SDWrite(%s) status %d  error: [%s]" % (rid, st, text_of(lib.SDError())))
        else:
            lib.SDDelete(fno, rest.encode())
            st = lib.SDStatus()
            say("SDDelete(%s) status %d  error: [%s]" % (rest, st, text_of(lib.SDError())))
    lib.SDClose(fno)
    lib.SDDisconnect()
    say("disconnected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
