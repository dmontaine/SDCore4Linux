#!/usr/bin/env python3
"""test-netpreflight-units.py - installsdcore.sh's net_preflight, run and ordered.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-netpreflight-units.py
  python3 .../test-netpreflight-units.py --selftest

No sudo, no install, no sd, no internet.  Exit 0 all checks passed, 1 a check
failed, 2 it could not run.  Written 4 Oct 26 for S.57.

WHAT IT CHECKS.  net_preflight is cut out of the installer between its own
header and closing brace and RUN, under the installer's own `set` and `IFS`
lines (test-install-pass3.sh's lesson, S.48: a block tested without the
installer's options passed while the real installs stopped), against a
listener this test opens on 127.0.0.1, a port it opened and closed, and a name
that cannot resolve.  Then the CALL is checked by position: it must come
before the first question, before `sudo -v`, and after the "already installed"
refusal, and it must name github.com and 443.

WHAT IT DOES NOT CHECK.  Whether github.com is reachable from here (it never
asks), and whether the installer as a whole stops cleanly on an offline
computer: that is a run on a computer or a network namespace with no network.

--selftest mutates the installer in the ways the check could plausibly be
broken and requires each mutant to be CAUGHT.
"""

import os
import re
import socket
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLER = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir, "installsdcore.sh"))
PROXY_VARS = ("https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY", "SD_SKIP_NET_CHECK")


def cut_function(src):
    """The text of net_preflight() { ... } and its start line, or (None, 0)."""
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("net_preflight() {"):
            for j in range(i + 1, len(lines)):
                if lines[j] == "}":
                    return "\n".join(lines[i:j + 1]), i + 1
    return None, 0


def option_lines(src):
    """The installer's own `set -...` and `IFS=` lines."""
    return "\n".join(l for l in src.splitlines() if re.match(r"^(set -|IFS=)", l))


def run_fn(src, host, port, env_extra=None):
    """Run net_preflight HOST PORT under the installer's options.  (rc, output)."""
    fn, _ = cut_function(src)
    script = "%s\nRED=; NC=\n%s\nnet_preflight %s %s\necho REACHED-END\n" % (
        option_lines(src), fn, host, port)
    env = {k: v for k, v in os.environ.items() if k not in PROXY_VARS}
    env.update(env_extra or {})
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        p = subprocess.run(["bash", path], env=env, capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(path)
    return p.returncode, p.stdout + p.stderr


def code_line(src, pattern):
    """First line number of a non-comment line matching pattern, or None."""
    for n, line in enumerate(src.splitlines(), 1):
        if not line.lstrip().startswith("#") and re.search(pattern, line):
            return n
    return None


def checks(src):
    """[(name, ok, detail)]"""
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    fn, fline = cut_function(src)
    ck("net_preflight is defined in the installer", fn is not None, "line %s" % fline)
    if fn is None:
        return out

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    open_port = listener.getsockname()[1]
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    closed_port = closed.getsockname()[1]
    closed.close()   # nothing listens here now

    rc, o = run_fn(src, "127.0.0.1", open_port)
    ck("reachable host and port: goes on quietly",
       rc == 0 and "REACHED-END" in o and o.strip() == "REACHED-END", "rc=%s out=%r" % (rc, o))

    rc, o = run_fn(src, "127.0.0.1", closed_port)
    ck("closed port: refuses, exit 1, before going on",
       rc == 1 and "REACHED-END" not in o, "rc=%s" % rc)
    ck("closed port: says it cannot connect, and what it will not have done",
       ("cannot connect to 127.0.0.1 port %d" % closed_port) in o and "Nothing has been changed" in o,
       o.strip().splitlines()[0] if o.strip() else "no output")
    ck("closed port: names the override for a proxy it cannot see", "SD_SKIP_NET_CHECK=1" in o)
    ck("closed port: says the stick carries the installer and documentation, not SD",
       "USB stick carries this installer and the documentation, not SD" in o)

    rc, o = run_fn(src, "sd-no-such-host.invalid", 443)
    ck("name that does not resolve: refuses with 'cannot look up'",
       rc == 1 and "cannot look up sd-no-such-host.invalid" in o and "REACHED-END" not in o,
       "rc=%s" % rc)

    for v in ("https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
        rc, o = run_fn(src, "127.0.0.1", closed_port, {v: "http://proxy.invalid:3128"})
        ck("%s set: does not test, goes on" % v, rc == 0 and "REACHED-END" in o, "rc=%s" % rc)
    rc, o = run_fn(src, "127.0.0.1", closed_port, {"https_proxy": ""})
    ck("https_proxy set but EMPTY: still tests, refuses", rc == 1 and "REACHED-END" not in o, "rc=%s" % rc)

    rc, o = run_fn(src, "127.0.0.1", closed_port, {"SD_SKIP_NET_CHECK": "1"})
    ck("SD_SKIP_NET_CHECK=1: goes on", rc == 0 and "REACHED-END" in o, "rc=%s" % rc)
    rc, o = run_fn(src, "127.0.0.1", closed_port, {"SD_SKIP_NET_CHECK": "0"})
    ck("SD_SKIP_NET_CHECK=0: does not skip", rc == 1 and "REACHED-END" not in o, "rc=%s" % rc)

    listener.close()

    # The call: position and arguments.
    call = code_line(src, r"^net_preflight\s+\S+\s+\S+")
    ck("the installer calls net_preflight", call is not None, "line %s" % call)
    m = re.search(r"^net_preflight\s+(\S+)\s+(\S+)", src, re.M)
    ck("the call names github.com and 443", bool(m) and (m.group(1), m.group(2)) == ("github.com", "443"),
       str(m.groups() if m else None))
    gate = code_line(src, r'^if \[ -f\s+"/usr/local/sdsys/bin/sd" \]')
    ask = code_line(src, r'^read -r -p "Continue\?')
    sudo = code_line(src, r"^if ! sudo -v")
    ck("after the 'already installed' refusal", call and gate and gate < call, "gate %s call %s" % (gate, call))
    ck("before the first question (Continue?)", call and ask and call < ask, "call %s ask %s" % (call, ask))
    ck("before the first sudo", call and sudo and call < sudo, "call %s sudo %s" % (call, sudo))
    host = re.search(r'^REPO_URL="https://([^/"]+)', src, re.M)
    ck("the host it tests is the host the installer clones from",
       bool(host) and bool(m) and host.group(1) == m.group(1), "%s vs %s" % (host and host.group(1), m and m.group(1)))
    return out


def mutants(src):
    """(name, mutated source) - each is a plausible way to break this."""
    fn, _ = cut_function(src)
    res = []
    if fn is None:
        return res
    proxy_loop = re.search(r"  for v in https_proxy.*?\n  done\n", fn, re.S)
    if proxy_loop:
        res.append(("proxy variables no longer skip the test", src.replace(proxy_loop.group(0), "")))
    res.append(("the override no longer skips", src.replace('[ "${SD_SKIP_NET_CHECK:-}" = "1" ] && return 0', ":")))
    res.append(("a closed port is no longer a refusal", src.replace('elif ! timeout 8 bash -c', 'elif false && ! timeout 8 bash -c')))
    res.append(("a name that does not resolve is no longer a refusal", src.replace('if ! getent hosts "$host"', 'if false && ! getent hosts "$host"')))
    res.append(("it refuses everything", src.replace("  else\n    return 0\n  fi\n  printf", "  fi\n  printf")))
    res.append(("the call moves after the first sudo",
                src.replace("net_preflight github.com 443\n", "", 1).replace("if ! sudo -v; then", "net_preflight github.com 443\nif ! sudo -v; then", 1)))
    res.append(("the call is deleted", src.replace("net_preflight github.com 443\n", "", 1)))
    res.append(("the call tests the wrong port", src.replace("net_preflight github.com 443", "net_preflight github.com 80", 1)))
    return res


def main():
    if "--selftest" in sys.argv:
        src = open(INSTALLER).read()
        base = checks(src)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated installer already fails:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(src)
        for name, msrc in ms:
            if msrc == src:
                print("  [NOT APPLIED] %s - the mutation did not change the source" % name)
                bad += 1
                continue
            caught = [n for n, ok, _ in checks(msrc) if not ok]
            if caught:
                print("  [caught] %s  (%d check(s) failed)" % (name, len(caught)))
            else:
                print("  [MISSED] %s" % name)
                bad += 1
        print("test-netpreflight-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0

    if not os.path.isfile(INSTALLER):
        print("test-netpreflight-units: CANNOT RUN - no installer at %s" % INSTALLER)
        return 2
    src = open(INSTALLER).read()
    print("installer : %s" % INSTALLER)
    res = checks(src)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail) + ")"))
        fails += 0 if ok else 1
    print("test-netpreflight-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
