#!/usr/bin/env python3
#
# ai-runner.py - systemd's side of sd-ai for the TESTS: a Unix socket whose every connection is handed to the helper, as `Accept=true` hands it a
# connection as fd 0 and 1 (S.69 step 2, plan .claude/plan-ai-step2.md).  Test-only: it is not installed and nothing in the product starts it.
#
#   python3 ai-runner.py --socket PATH --state DIR --providers FILE [--admin-user NAME] [--gate-group NAME]
#
# The helper is loaded as a module in this process and each connection is served in a forked child, so the caller's uid still comes from SO_PEERCRED of the
# real connection.  --admin-user and --gate-group replace the two names the installed helper has fixed (sdsys, sdaiusers) with the test's own user and group:
# that is the only change, and it is made here, never in the helper.  Prints "ready" on stdout when it listens.  Stops on SIGTERM.
#
# START-HISTORY:
# 23 Oct 26 dm  New.
# END-HISTORY

import importlib.machinery
import importlib.util
import os
import signal
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_helper(path=None):
    path = path or os.path.join(HERE, "sd-ai")
    loader = importlib.machinery.SourceFileLoader("sdai_runner", path)
    spec = importlib.util.spec_from_loader("sdai_runner", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def main(argv):
    opts = {"--socket": None, "--state": None, "--providers": None, "--admin-user": None, "--gate-group": None, "--helper": None}
    i = 1
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            sys.stderr.write("usage: ai-runner.py --socket PATH --state DIR --providers FILE [--admin-user NAME] [--gate-group NAME] [--helper FILE]\n")
            return 2
    if not (opts["--socket"] and opts["--state"] and opts["--providers"]):
        sys.stderr.write("ai-runner: --socket, --state and --providers are required\n")
        return 2
    mod = load_helper(opts["--helper"])
    if opts["--admin-user"]:
        mod.ADMIN_USER = opts["--admin-user"]
    if opts["--gate-group"]:
        mod.GATE_GROUP = opts["--gate-group"]
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)               # children are not waited for
    try:
        os.unlink(opts["--socket"])
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(opts["--socket"])
    os.chmod(opts["--socket"], 0o660)
    srv.listen(16)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    print("ready", flush=True)
    while True:
        conn, _ = srv.accept()
        if os.fork() == 0:
            srv.close()
            try:
                mod.serve(conn.fileno(), conn.fileno(), opts["--state"], opts["--providers"], sys.stderr.write)
            finally:
                conn.close()
                os._exit(0)
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
