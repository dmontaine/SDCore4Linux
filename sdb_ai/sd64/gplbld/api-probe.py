#!/usr/bin/env python3
"""api-probe.py - one SD API session through the installed client library.

W.4, 14 Sep 2026.  Connects over TCP with SDConnect - the network login, so
APISRVR's vb.login and then vb.account - runs the given commands with
SDExecute, optionally holds the connection open so a witness can read the
server process's /proc entry, and disconnects.

  SD_PROBE_PASSWORD=... python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/api-probe.py \
      --user <name> --account <name> [--hold SECONDS] [--] COMMAND...

No sudo of its own.  It needs a Linux user whose password is known, which in
this project means a throwaway made by an owner-run witness.

THE PASSWORD COMES FROM THE ENVIRONMENT, NEVER THE COMMAND LINE, which would
put it in the process list - the port's sd-connect.exe took it as an argument
and its verifiers had to say so.  Only its length is printed.

IT PRINTS WHAT IT DID, not what it concluded: the library, host, port, user
and account it passed; SDConnect's return value; SDError's text on a refusal;
and each command with its output and error code.

Exit 0 connected and every command ran; 1 the server refused the connection;
2 it could not run (no password, no library) - including when it was given
nothing to do, because a connection that runs nothing measures nothing.
"""

import argparse
import ctypes
import os
import sys
import time

DEFAULT_LIB = "/usr/local/sdsys/bin/sdclilib.so"


def say(text):
    print(text)
    sys.stdout.flush()


def text_of(raw):
    return raw.decode("utf-8", errors="replace") if raw else ""


def main(argv):
    ap = argparse.ArgumentParser(description="One SD API session over TCP.")
    ap.add_argument("--lib", default=DEFAULT_LIB)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4243)
    ap.add_argument("--user", required=True)
    ap.add_argument("--account", required=True)
    ap.add_argument("--hold", type=float, default=0.0,
                    help="seconds to keep the connection open after the commands")
    ap.add_argument("commands", nargs="*")
    a = ap.parse_args(argv)

    pw = os.environ.get("SD_PROBE_PASSWORD")
    say("api-probe")
    say("  lib      : %s" % a.lib)
    say("  host     : %s  port %d" % (a.host, a.port))
    say("  user     : %s" % a.user)
    say("  account  : %s" % a.account)
    say("  password : %s" % ("from SD_PROBE_PASSWORD, %d characters" % len(pw)
                             if pw is not None else "SD_PROBE_PASSWORD is not set"))
    say("  commands : %d   hold: %gs" % (len(a.commands), a.hold))

    if pw is None:
        say("api-probe: CANNOT RUN - SD_PROBE_PASSWORD is not set.")
        return 2
    if not a.commands and a.hold <= 0:
        say("api-probe: CANNOT RUN - no command and no hold, so a connection would measure nothing.")
        return 2
    try:
        lib = ctypes.CDLL(a.lib)
    except OSError as e:
        say("api-probe: CANNOT RUN - cannot load %s: %s" % (a.lib, e))
        return 2

    lib.SDConnect.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                              ctypes.c_char_p, ctypes.c_char_p]
    lib.SDConnect.restype = ctypes.c_int
    lib.SDError.argtypes = []
    lib.SDError.restype = ctypes.c_char_p
    lib.SDExecute.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    lib.SDExecute.restype = ctypes.c_char_p
    lib.SDDisconnect.argtypes = []
    lib.SDDisconnect.restype = None

    rc = lib.SDConnect(a.host.encode(), a.port, a.user.encode(), pw.encode(),
                       a.account.encode())
    say("SDConnect returned %d" % rc)
    if not rc:
        say("SDError: %s" % text_of(lib.SDError()))
        return 1

    for cmd in a.commands:
        say("> %s" % cmd)
        err = ctypes.c_int(0)
        out = text_of(lib.SDExecute(cmd.encode(), ctypes.byref(err)))
        lines = out.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        while lines and lines[-1] == "":
            lines.pop()
        for line in lines:
            say("| %s" % line)
        say("  (err %d)" % err.value)

    if a.hold > 0:
        say("holding the connection %gs" % a.hold)
        time.sleep(a.hold)
    lib.SDDisconnect()
    say("disconnected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
