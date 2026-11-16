#!/usr/bin/env python3
#
# test-sdsysapi-units.py - S.256, remote administration through the API (remote.sdsys api).  Free: no install, no sudo, no SD.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sdsysapi-units.py [--selftest]
#
# START-HISTORY:
# 16 Nov 26 dm  New (S.256).
# END-HISTORY
#
# WHAT IT HOLDS (the owner, 16 Nov 2026: "deliver closed and secure and let the admin decide to loosen"; "Full admin rights only if API into
# SDSYS"; listed addresses, ranges too, the word any alone; "Local always, remote by switch"):
#   H   the root helper's sdsys-api function, cut out of gplbld/sd-elevate and RUN on a scratch file (need_root and logger stubbed): on writes
#       "on" and the entries in standard form, root's 0600 by one rename; a bad entry, a /0, any with another entry, 33 entries and a link at
#       the file are refused and leave the file as it was; off removes it; status reports it.
#   A   apisrvr, as text: the remote arm reads the setting before its refusal 10174 and asks !addrmatch before 14116; the local arm asks
#       system(43) (10922) and then system(44) (10195) before it admits; the administrator's flag is set in ONE place, under sdsys.api.from,
#       AFTER K$ASSUME.USER, and the audit line after it.
#   R   remotesdsys, as text: the administrator first; every address checked character by character before os.execute; any only alone.
#   C   the kernel: linuxio.c reads /proc/<cr.pid>/loginuid into peer_login_user and leaves it empty for an unset login uid; SYSTEM(44).
#   M   the messages; the deleter removes the setting only when the configuration is deleted; !addrmatch never matches a length of 0.
# NOT HERE: whether a remote client is admitted (the VM witness, with the clean-room client from another machine) and the bit rule itself
# (sandbox-addrmatch.py, against Python's ipaddress).

import os
import re
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(SD64, "..", ".."))
GPL = os.path.join(SD64, "sdsys", "gpl.bp")
MSG = os.path.join(SD64, "sdsys", "messages")
FILES = {
    "elevate": os.path.join(HERE, "sd-elevate"),
    "apisrvr": os.path.join(GPL, "apisrvr"),
    "remote": os.path.join(GPL, "remotesdsys"),
    "addrmatch": os.path.join(GPL, "addrmatch"),
    "linuxio": os.path.join(SD64, "gplsrc", "linuxio.c"),
    "opsys": os.path.join(SD64, "gplsrc", "op_sys.c"),
    "kernelh": os.path.join(SD64, "gplsrc", "kernel.h"),
    "deleter": os.path.join(REPO, "deletesdcore.sh"),
}


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    for n in ("10174", "10195", "10922", "11923", "14116", "14117", "14118", "14119", "14120"):
        try:
            with open(os.path.join(MSG, n), encoding="latin-1") as f:
                raw["m" + n] = f.read()
        except OSError:
            raw["m" + n] = ""
    return raw


def code(s):
    """BASIC text with comment lines and ;* tails taken out."""
    out = []
    for line in s.split("\n"):
        t = line.lstrip()
        if t.startswith("*") or t.startswith("!"):
            continue
        c = line.find(";*")
        out.append(line if c < 0 else line[:c])
    return "\n".join(out)


def ordered(text, *needles):
    pos = -1
    for n in needles:
        i = text.find(n, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def helper_fn(elevate):
    m = re.search(r"\nSDSYS_API_FILE=.*?\nsdsys_api\(\) \{.*?\n\}\n", elevate, re.S)
    return m.group(0) if m else ""


def run_helper(fn, path, *args, pre=None):
    """Run sdsys_api ARGS on a scratch file; returns (rc, stdout+stderr, file content or None, mode or None)."""
    script = ("set -u\nDRY=0\nPROG=sd-elevate\nneed_root() { :; }\ndie() { echo \"die: $*\" >&2; exit 2; }\n"
              "logger() { :; }\n" + fn + "\nSDSYS_API_FILE=%s\n" % path +
              "sdsys_api \"$@\"\n")
    if pre:
        pre()
    p = subprocess.run(["bash", "-c", script, "x"] + list(args), capture_output=True, text=True, timeout=60)
    try:
        with open(path) as f:
            content = f.read()
        mode = stat.S_IMODE(os.lstat(path).st_mode)
    except OSError:
        content, mode = None, None
    return p.returncode, p.stdout + p.stderr, content, mode


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    api = code(raw["apisrvr"])
    rem = code(raw["remote"])
    am = code(raw["addrmatch"])
    ck("N0", "NULL CASE: every file and message was found and is not empty",
       all(len(raw[k]) > 200 for k in FILES) and all(raw["m" + n].strip() for n in ("10174", "10195", "10922", "11923", "14116", "14117", "14118", "14119", "14120")),
       repr([k for k in FILES if len(raw[k]) <= 200]))

    # H - the helper, run
    fn = helper_fn(raw["elevate"])
    ck("H0", "the helper's SDSYS_API_FILE and sdsys_api() were cut out of sd-elevate", "sdsys_api()" in fn and "ipaddress" in fn, fn[:80])
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "sdsys-api")
        rc, out, c, mode = run_helper(fn, f, "on", "192.168.1.99/24", "2001:0DB8::0001", "10.0.0.5", "192.168.1.0/24")
        ck("H1", "on writes 'on' then each entry in standard form (host bits cleared, IPv6 short, an address /32 or /128, a repeat once), mode 0600",
           rc == 0 and c == "on\n192.168.1.0/24\n2001:db8::1/128\n10.0.0.5/32\n" and mode == 0o600, repr((rc, c, oct(mode or 0), out[-200:])))
        rc, out, cm, _m = run_helper(fn, f + ".mapped", "on", "::ffff:192.168.1.5", "::ffff:10.1.2.0/120")
        ck("H1b", "an IPv4-mapped IPv6 entry is written as its IPv4 form (a single address /32, a /120 as /24), the form a mapped peer is compared in",
           rc == 0 and cm == "on\n192.168.1.5/32\n10.1.2.0/24\n", repr((rc, cm, out[-160:])))
        rc, out, c2, _m = run_helper(fn, f, "status")
        ck("H2", "status reports on and the entries", rc == 0 and "on, from 192.168.1.0/24 2001:db8::1/128 10.0.0.5/32" in out, out)
        for i, args, why in (("H3", ("on", "10.0.0.1", "not-an-address"), "an entry that is not an address"),
                             ("H4", ("on", "0.0.0.0/0"), "a /0 range"),
                             ("H5", ("on", "::/0"), "an IPv6 /0 range"),
                             ("H6", ("on", "any", "10.0.0.1"), "any with another entry"),
                             ("H7", ("on",) + tuple("10.0.%d.1" % k for k in range(33)), "33 entries")):
            rc, out, c3, _m = run_helper(fn, f, *args)
            ck(i, "on with %s is refused and leaves the file as it was" % why, rc != 0 and c3 == c, repr((rc, c3, out[-160:])))
        rc, out, c4, mode = run_helper(fn, f, "on", "any")
        ck("H8", "on any alone writes 'on' then 'any', mode 0600", rc == 0 and c4 == "on\nany\n" and mode == 0o600, repr((rc, c4, out[-160:])))
        rc, out, c5, _m = run_helper(fn, f, "off")
        ck("H9", "off removes the file and says off", rc == 0 and c5 is None and "off" in out, repr((rc, c5, out)))
        rc, out, _c, _m = run_helper(fn, f, "status")
        ck("H10", "status with no file says off", rc == 0 and out.strip().endswith(": off"), out)
        tgt = os.path.join(d, "elsewhere")

        def mklink():
            open(tgt, "w").close()
            os.symlink(tgt, f)
        rc, out, _c, _m = run_helper(fn, f, "on", "10.0.0.1", pre=mklink)
        with open(tgt) as g:
            tc = g.read()
        ck("H11", "a link at the file is refused and what it points at is not written", rc != 0 and tc == "" and os.path.islink(f), repr((rc, tc, out[-120:])))

    # A - apisrvr
    remote_arm = api[api.find("sdsys.api.from = ''"):api.find("if downcase(scram.user) = 'sdsys' and sdsys.api.from = '' then")]
    ck("A1", "the remote arm reads the setting, refuses 10174 when it is off, asks !addrmatch and refuses 14116 when it says no, then admits",
       ordered(remote_arm, "if downcase(scram.user) = 'sdsys' and not(api.peer.local) then", "gosub read.sdsys.api", "if not(sdsys.api.on) then",
               "sysmsg(10174)", "goto exit.vb.scram.fail", "call !addrmatch(sdsys.api.peer, sdsys.api.list, sdsys.api.listed)",
               "if not(sdsys.api.listed) then", "sysmsg(14116, api.peer.addr)", "goto exit.vb.scram.fail", "sdsys.api.from = sdsys.api.peer"),
       remote_arm[:200])
    local_arm = api[api.find("if downcase(scram.user) = 'sdsys' and sdsys.api.from = '' then"):]
    ck("A2", "the local arm asks the socket and system(43) (10922), then system(44) (10195), and only then admits",
       ordered(local_arm, "system(43)", "if api.peer.addr[1,1] # '/' then sdsys.api.ok = @false", "sysmsg(10922)", "goto exit.vb.scram.fail",
               "system(44)", "if api.peer.login # 'sdsys' then", "sysmsg(10195)", "goto exit.vb.scram.fail", "sdsys.api.from = 'this machine'"), "")
    ck("A3", "the administrator's flag is set in ONE place in apisrvr, under sdsys.api.from, after K$ASSUME.USER, and the audit line after it",
       api.count("kernel(K$ADMINISTRATOR, 1)") == 1 and api.count("kernel(K$ADMINISTRATOR,1)") == 0
       and ordered(api, "if not(kernel(K$ASSUME.USER, scram.user)) then", "if sdsys.api.from # '' then", "void kernel(K$ADMINISTRATOR, 1)",
                   "'elevation granted reason=sdsys api from=' : sdsys.api.from", "logged.in = @true"),
       repr(api.count("kernel(K$ADMINISTRATOR, 1)")))
    ck("A4", "the setting is read from /etc/sdcore/sdsys-api and only a first line 'on' turns it on",
       "$define SDSYS.API.FILE '/etc/sdcore/sdsys-api'" in raw["apisrvr"]
       and ordered(api, "read.sdsys.api:", "sdsys.api.on = @false", "openseq SDSYS.API.FILE readonly to sdsys.api.f then",
                   "readseq sdsys.api.line from sdsys.api.f then", "if downcase(trim(sdsys.api.line)) = 'on' then", "sdsys.api.on = @true",
                   "close sdsys.api.f", "end else", "close sdsys.api.f", "return") and "closeseq" not in api.lower(), "")
    # 16 Nov 26: OSREAD is a call of !osread, an ordinary program held to the account's OS gate, and a session that has not entered an account
    # does not pass it: on the VM every login read the setting as off.  The apisrvr itself must open the file.
    ck("A5", "the setting is NOT read with OSREAD (which is gated, and read nothing on a real install), only by this $internal program's OPENSEQ",
       not re.search(r"^\s*osread\b", api, re.M | re.I), "")

    # R - remotesdsys
    ck("R1", "remote.sdsys asks for the administrator before it reads a word", ordered(rem, "if not(kernel(K$ADMINISTRATOR, -1)) then", "words = trim(@sentence)"), "")
    ck("R2", "every address is checked character by character (hex digits, '.', ':', '/', at most 64) before any os.execute that could carry it",
       ordered(rem, "convert '0123456789abcdefABCDEF.:/' to '' in chk", "if chk # '' or len(a) < 1 or len(a) > 64 then", "sysmsg(14118, a)",
               "os.execute HELPER : ' sdsys-api ' : action"), "")
    ck("R3", "any is taken only alone (14119 otherwise)", ordered(rem, "if downcase(a) = 'any' then", "if nwords # argn + 1 then", "sysmsg(14119)", "addrs = 'any'"), "")
    ck("R4", "the helper is the only program run, with the verbs sdsys-ssh and sdsys-api",
       set(re.findall(r"os\.execute HELPER : ' (sdsys-\w+)", rem)) == {"sdsys-ssh", "sdsys-api"} and rem.count("os.execute") == rem.count("os.execute HELPER"),
       repr(re.findall(r"os\.execute[^\n]*", rem)))

    # C - the kernel
    lio = raw["linuxio"]
    ck("C1", "linuxio.c reads /proc/<cr.pid>/loginuid into peer_login_user, and an unset login uid leaves it empty",
       ordered(lio, "SO_PEERCRED, &cr, &crlen", '"/proc/%d/loginuid", (int)cr.pid', "lu != 4294967295UL", "strncpy(peer_login_user"), "")
    ck("C2", "SYSTEM(44) answers peer_login_user; kernel.h declares it",
       re.search(r"case 44:[^\n]*\n\s*k_put_c_string\(peer_login_user, descr\);", raw["opsys"]) is not None
       and "Public char peer_login_user[MAX_USERNAME_LEN + 1] init(\"\");" in raw["kernelh"], "")

    # M - messages, the deleter, !addrmatch
    ck("M1", "14116 names the address (%1); 14117 the addresses; 14120 says every address on the internet; 11923 shows api on, api on any and api off",
       "%1" in raw["m14116"] and "%1" in raw["m14117"] and "internet" in raw["m14120"]
       and "api {on address ... | off}" in raw["m11923"] and "API ON ANY" in raw["m11923"], "")
    dl = raw["deleter"]
    blk = dl[dl.find("# SDSYSAPI-BEGIN"):dl.find("# SDSYSAPI-END")]
    ck("M2", "the deleter removes the setting only when the configuration is deleted (an upgrade keeps it)",
       'if [ "$conf_deleted" = yes ]' in blk and "sudo rm -f /etc/sdcore/sdsys-api" in blk and dl.count("/etc/sdcore/sdsys-api") == 3, blk[:200])
    ck("M3", "!addrmatch is internal, never matches a length under 1, and takes the word any",
       "$internal" in raw["addrmatch"] and "if plen >= 1 and plen <= len(atb.bits) then" in am and "if e = 'any' then ok = @true" in am, "")
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if r[key].count(old) != 1:
            raise KeyError("%s: the text to change is found %d times, not once: %r" % (key, r[key].count(old), old[:60]))
        r[key] = r[key].replace(old, new)
        return r
    return f


MUTANTS = [
    ("the remote arm does not read the setting", "A1", sub("apisrvr", "                  gosub read.sdsys.api\n", "")),
    ("an unlisted address is admitted", "A1", sub("apisrvr", "                  if not(sdsys.api.listed) then\n", "                  if @false then\n")),
    ("the local arm forgets the login test", "A2", sub("apisrvr", "                  if api.peer.login # 'sdsys' then\n", "                  if @false then\n")),
    ("the flag for every API login", "A3", sub("apisrvr", "               if sdsys.api.from # '' then\n                  void kernel(K$ADMINISTRATOR, 1)",
                                                 "               if @true then\n                  void kernel(K$ADMINISTRATOR, 1)")),
    ("any first line turns it on", "A4", sub("apisrvr", "if downcase(trim(sdsys.api.line)) = 'on' then", "if @true then")),
    ("the gated OSREAD comes back", "A5", sub("apisrvr", "               sdsys.api.list = ''\n               openseq", "               sdsys.api.list = ''\n               osread x from SDSYS.API.FILE else null\n               openseq")),
    ("an address reaches the shell unchecked", "R2", sub("remote", "      if chk # '' or len(a) < 1 or len(a) > 64 then", "      if @false then")),
    ("any is taken with others", "R3", sub("remote", "         if nwords # argn + 1 then", "         if @false then")),
    ("the helper accepts a /0", "H4", sub("elevate", "        sys.exit(1)\n    if n.prefixlen == 0:", "        sys.exit(1)\n    if False:")),
    ("a mapped entry is kept in IPv6 form", "H1b", sub("elevate", "    if n.version == 6 and n.prefixlen >= 96 and n.network_address.ipv4_mapped is not None:", "    if False:")),
    ("the helper's file is readable by others", "H1", sub("elevate", '      chmod 0600 -- "$tmp" ||', '      chmod 0644 -- "$tmp" ||')),
    ("the helper follows a link", "H11", sub("elevate", '      [[ ! -L $SDSYS_API_FILE ]] || die "$SDSYS_API_FILE is a link: refused"\n', "")),
    ("the helper takes any with others", "H6", sub("elevate", '        [[ $# -eq 1 ]] || die "sdsys-api on any takes no other address"\n', "")),
    ("an unset login uid is a user", "C1", sub("linuxio", "lu != 4294967295UL && ", "")),
    ("an upgrade loses the setting", "M2", sub("deleter", 'if [ "$conf_deleted" = yes ] && sudo test -e /etc/sdcore/sdsys-api; then', "if sudo test -e /etc/sdcore/sdsys-api; then")),
    ("a /0 matches", "M3", sub("addrmatch", "if plen >= 1 and plen <= len(atb.bits) then", "if plen >= 0 and plen <= len(atb.bits) then")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:240]))
        bad += 0 if ok else 1
    return bad


def main(argv):
    raw = load()
    print("test-sdsysapi-units: files " + ", ".join("%s=%s" % (k, FILES[k]) for k in ("elevate", "apisrvr", "remote")))
    if "--selftest" in argv:
        rows = checks(raw)
        if any(not r[2] for r in rows):
            report(rows)
            print("selftest: the real files do not pass")
            return 1
        missed = 0
        for name, row_id, mut in MUTANTS:
            try:
                failed_ids = [r[0] for r in checks(mut(raw)) if not r[2]]
            except KeyError as e:
                print("  [MISSED] %s: %s" % (name, e))
                missed += 1
                continue
            if row_id in failed_ids:
                print("  [PASS] selftest: %s is caught by %s (failed: %s)" % (name, row_id, " ".join(failed_ids)))
            else:
                print("  [MISSED] %s: %s did not fail (failed: %s)" % (name, row_id, " ".join(failed_ids) or "none"))
                missed += 1
        print("selftest: %d mutants, %d not caught" % (len(MUTANTS), missed))
        return 0 if missed == 0 else 1
    rows = checks(raw)
    bad = report(rows)
    print("test-sdsysapi-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
