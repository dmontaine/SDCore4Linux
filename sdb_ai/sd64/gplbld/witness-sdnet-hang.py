#!/usr/bin/env python3
"""witness-sdnet-hang.py - a server that hangs, for S.73 item 2 on a REAL install (3 Nov 2026, track G).  The servers are netfake.py's (beside this file), the ones
sandbox-netfile.py's timeout section measures in a sandbox; this runs one of them on 127.0.0.1 for an installed SD to dial.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-hang.py silent  [STATEFILE]
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-hang.py ack|first CERT KEY [STATEFILE]

  silent      netfake.SilentListener: accepts the TCP connection and never answers the TLS hello (the hang AT THE HELLO; NETWAIT bounds it, message 11445 / 11470)
  ack         netfake.PartialRecordServer cut='ack': the handshake completes, then the one-byte Ack is sent as HALF a TLS record (MID-RECORD at the start of the session; NETREPLY bounds it,
              "No acknowledgement from 127.0.0.1:<port> at the start of the session")
  first       cut='first': the Ack is whole, client-first is read, the reply is sent as HALF a record (MID-RECORD in the login; "No reply from 127.0.0.1:<port> during the login ...")

It prints "PORT <n>" (also written to STATEFILE when given, so a caller started in the background can read it), then serves until it reads end of file on stdin or is
killed, and at the end prints what it saw: for silent the connections accepted and closed by the client, for ack / first netfake's own log (the cut, the bytes sent, the seconds
from the cut to the client's close).  No sudo of its own; no sd.  Exit 0 when it served, 2 when it could not start.
"""
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netfake  # noqa: E402

STOP = [False]


def main(argv):
    if not argv or argv[0] not in ("silent", "ack", "first"):
        print("usage: witness-sdnet-hang.py silent [STATEFILE] | ack|first CERT KEY [STATEFILE]")
        return 2
    mode = argv[0]
    if mode == "silent":
        state = argv[1] if len(argv) > 1 else None
        srv = netfake.SilentListener()
    else:
        if len(argv) < 3 or not (os.path.isfile(argv[1]) and os.path.isfile(argv[2])):
            print("witness-sdnet-hang: CANNOT RUN - %s needs CERT and KEY files" % mode)
            return 2
        state = argv[3] if len(argv) > 3 else None
        srv = netfake.PartialRecordServer(argv[1], argv[2], cut=mode, hold=60.0)
    print("witness-sdnet-hang %s on 127.0.0.1" % mode)
    print("PORT %d" % srv.port, flush=True)
    if state:
        with open(state, "w") as fh:
            fh.write("%d\n" % srv.port)
    signal.signal(signal.SIGTERM, lambda *_: STOP.__setitem__(0, True))
    t0 = time.time()
    try:
        while not STOP[0] and time.time() - t0 < 900:
            if not sys.stdin.isatty() and sys.stdin.readable():
                import select
                r, _, _ = select.select([sys.stdin], [], [], 0.5)
                if r and sys.stdin.readline() == "":
                    break
            else:
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    if mode == "silent":
        print("SAW accepted=%d closed_by_client=%d" % (srv.accepted, srv.count_closed()), flush=True)
    else:
        for e in srv.log:
            print("SAW %r" % (e,), flush=True)
    srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
