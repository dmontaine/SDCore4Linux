#!/usr/bin/env python3
"""test-createacct-units.py - three S.62 changes to create_account, as invariants.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-createacct-units.py
  python3 .../test-createacct-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it
could not run.  Written 8 Oct 26 for the line-by-line read of create_account
against the Windows port (owner: "1 yes, 2 yes if possible, 3 fix"):

  A  10161 and 10162 warn, without refusing, when a route has nothing behind it
     (Windows RELEASE_1.1 125): ssh by whether sshd is installed, the API by
     whether sdclient.socket is active.
  B  A refused password UNWINDS the Linux user just made (Windows, owner 21 Aug
     26): userdel-home, then plain userdel, then 10086 only when the user is
     READ OFF the system as gone, else 10130.
  C  ATTACH is honoured for a USER account only.

***IT READS create_account AS TEXT AND DOES NOT RUN BASIC.*** It cannot say a
warning appears or a user is removed - only that the code is still written, in
the order that makes it true.  The sandbox run of 8 Oct (CREATE.ACCOUNT USER
with a password the shim refuses) printed 10086 and made no account; the two
warnings and a real userdel are owed to an install.  A green run here is
evidence that nothing has deleted or reordered the code, nothing more.

--selftest mutates the source in the ways these changes could plausibly be
broken and requires each mutation to be CAUGHT, and each mutation to match its
text exactly once: an injection that changed nothing is not a test.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
CA = os.path.join(SDSYS, "gpl.bp", "create_account")
MESSAGES = os.path.join(SDSYS, "messages")

SSHD_TEST = "access.ssh and not(ospath('/usr/sbin/sshd', OS$EXISTS))"
API_EXEC = 'OS.EXECUTE "systemctl is-active --quiet sdclient.socket 2>/dev/null"'
API_TEST = "if OS.ERROR() # 0 then"
W10161 = "crt sysmsg(10161, acc.uname)"
W10162 = "crt sysmsg(10162, acc.uname)"
ROUTE_LAST = "crt sysmsg(10079, acc.uname)"
PW_FAIL = "if not(set_passwd(acc.uname)) then"
PROMPT = "crt sysmsg(10008):"
AGAIN = "if upcase(yn) = 'Y' then goto PW.TRY.AGAIN"
UD_HOME = 'OS.EXECUTE "sudo /usr/local/sbin/sd-elevate userdel-home ":acc.uname'
UD_PLAIN = 'OS.EXECUTE "sudo /usr/local/sbin/sd-elevate userdel ":acc.uname'
GONE = "if is_user(acc.uname) then"
E10130 = "err = 10130:@vm:acc.uname"
E10086 = "err = 10086"
RC = "@system.return.code = -ER$NOT.CREATED"
AFTER_UNWIND = "uid = acc.uname"
ATTACH_GATE = "acc.type = 'USER' and kernel(K$INTERNAL, -1) and ospath(attach.marker, OS$EXISTS)"


def code_lines(src):
    """(line number, text) for every line that is not a full-line comment."""
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("*"):
            continue
        out.append((i, line))
    return out


def first(lines, needle, start=0):
    for k in range(start, len(lines)):
        if needle in lines[k][1]:
            return k
    return None


def count(lines, needle, lo, hi):
    if lo is None or hi is None:
        return 0
    return sum(1 for k in range(lo, hi) if needle in lines[k][1])


def check(src, messages):
    """Return [(name, ok, detail)]."""
    rows = []

    def row(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    L = code_lines(src)
    route = first(L, ROUTE_LAST)
    i61 = first(L, W10161, route or 0)
    i62 = first(L, W10162, route or 0)
    grp = first(L, "gosub create.group", route or 0)

    # A - the two warnings
    row("A1 10161 is shown when access.ssh is set and sshd is not installed",
        i61 is not None and first(L, SSHD_TEST, max(i61 - 2, 0)) is not None
        and first(L, SSHD_TEST, max(i61 - 2, 0)) < i61,
        "no '%s' just before the 10161 line" % SSHD_TEST)
    ex = first(L, API_EXEC, route or 0)
    er = first(L, API_TEST, ex or 0)
    ap = first(L, "if access.api then", (route or 0) + 1)
    row("A2 10162 is shown when access.api is set and sdclient.socket is not active",
        None not in (i62, ex, er, ap) and ap < ex < er < i62,
        "need 'if access.api', the systemctl is-active call, 'OS.ERROR() # 0', then 10162, in that order")
    row("A3 both warnings come after the route line and before the sdu_ group is made",
        None not in (route, i61, i62, grp) and route < i61 < i62 < grp,
        "route=%s 10161=%s 10162=%s create.group=%s" % (route, i61, i62, grp))
    if None not in (i61, i62):
        span = range(max(i61 - 2, 0), i62 + 3)
        bad = [L[k][0] for k in span if any(t in L[k][1] for t in ("goto exit.create", "err =", "return"))]
        row("A4 the warnings do not refuse: no err, goto or return in their span", not bad,
            "line(s) %s" % bad)
    else:
        row("A4 the warnings do not refuse: no err, goto or return in their span", False, "warnings not found")

    # B - the unwind
    pw = first(L, PW_FAIL)
    pr = first(L, PROMPT, pw or 0)
    ag = first(L, AGAIN, pw or 0)
    uh = first(L, UD_HOME, pw or 0)
    up = first(L, UD_PLAIN, uh or 0)
    e30 = first(L, E10130, up or 0)
    e86 = first(L, E10086, up or 0)
    rc = first(L, RC, uh or 0)
    gx = first(L, "goto exit.create", e86 or 0)
    af = first(L, AFTER_UNWIND, pw or 0)
    row("B1 a userdel-home and then a plain userdel follow the failed password",
        None not in (pw, uh, up) and pw < uh < up,
        "pw=%s userdel-home=%s userdel=%s" % (pw, uh, up))
    row("B2 the unwind comes after the retry prompt and its 'Y' loop, not before",
        None not in (pr, ag, uh) and pr < ag < uh,
        "prompt=%s again=%s userdel-home=%s" % (pr, ag, uh))
    row("B3 the user is read back (is_user) twice: before the fallback and before choosing the message",
        None not in (uh, e30) and count(L, GONE, uh, e30 + 1) >= 2,   # the detail below tolerates a missing anchor
        "is_user reads between userdel-home and 10130: %s" % count(L, GONE, uh, None if e30 is None else e30 + 1))
    row("B4 10130 (still there) precedes 10086 (nothing created), 10086 in the else branch",
        None not in (e30, e86) and e30 < e86 and first(L, "end else", e30) is not None
        and first(L, "end else", e30) < e86,
        "10130=%s 10086=%s" % (e30, e86))
    row("B5 the return code is negative before the message is chosen",
        None not in (rc, e30) and rc < e30,
        "return.code=%s 10130=%s" % (rc, e30))
    row("B6 the unwind ends at exit.create and before the account is built",
        None not in (gx, af) and gx < af,
        "goto=%s uid=%s" % (gx, af))

    # C - ATTACH
    row("C1 ATTACH is honoured only for acc.type USER", first(L, ATTACH_GATE) is not None,
        "no '%s'" % ATTACH_GATE)

    # M - the messages
    for n, needs_arg in (("10086", False), ("10130", True), ("10161", True), ("10162", True)):
        text = messages.get(n)
        ok = text is not None and text.strip() != "" and (("%1" in text) == needs_arg)
        row("M%s message %s exists%s" % (n, n, " and names the account (%1)" if needs_arg else " with no argument"),
            ok, "missing or wrong shape" if not ok else "")
    return rows


def load():
    with open(CA, encoding="utf-8", errors="replace") as f:
        src = f.read()
    msgs = {}
    for n in ("10086", "10130", "10161", "10162"):
        p = os.path.join(MESSAGES, n)
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                msgs[n] = f.read()
    return src, msgs


def report(rows):
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        bad += 0 if ok else 1
    return bad


# (name, old text, new text) - each old text must occur exactly once in the source
MUTANTS = [
    ("10161 line deleted", W10161, "null"),
    ("sshd test dropped", "not(ospath('/usr/sbin/sshd', OS$EXISTS))", "@false"),
    ("10161 refuses", W10161, W10161 + " ; goto exit.create"),
    ("10162 line deleted", W10162, "null"),
    ("API test inverted", API_TEST, "if OS.ERROR() = 0 then"),
    ("API call removed", API_EXEC, "null"),
    ("10162 refuses", W10162, W10162 + " ; err = 10162"),
    ("userdel-home deleted", UD_HOME, "null"),
    ("plain userdel deleted", UD_PLAIN, "null"),
    ("10086 renumbered", E10086, "err = 10099"),
    ("user not read back", GONE + "\n             err = 10130", "if @false then\n             err = 10130"),
    ("10130 renamed", E10130, "err = 10131:@vm:acc.uname"),
    ("return code lost", "          " + RC + "\n          if is_user", "          if is_user"),
    ("ATTACH gate loses USER", ATTACH_GATE, "kernel(K$INTERNAL, -1) and ospath(attach.marker, OS$EXISTS)"),
]


def selftest():
    src, msgs = load()
    base = check(src, msgs)
    print("control (unmutated source):")
    if report(base):
        print("selftest: the control itself fails, so every mutant below would prove nothing")
        return 1
    missed = 0
    print("\nmutants (each must fail at least one row):")
    for name, old, new in MUTANTS:
        n = src.count(old)
        if n != 1:
            print("  [FAIL] %-28s the injected text matched %d time(s), needs exactly 1" % (name, n))
            missed += 1
            continue
        failed = [r[0] for r in check(src.replace(old, new), msgs) if not r[1]]
        if failed:
            print("  [PASS] %-28s caught by %s" % (name, failed[0].split(" ")[0]))
        else:
            print("  [FAIL] %-28s NOT caught" % name)
            missed += 1
    for n in ("10086", "10130", "10161", "10162"):
        m2 = dict(msgs)
        del m2[n]
        failed = [r[0] for r in check(src, m2) if not r[1]]
        if failed:
            print("  [PASS] message %s deleted        caught by %s" % (n, failed[0].split(" ")[0]))
        else:
            print("  [FAIL] message %s deleted        NOT caught" % n)
            missed += 1
    print("\nselftest: %s" % ("all mutants caught" if not missed else "%d mutant(s) missed" % missed))
    return 1 if missed else 0


def main():
    if not os.path.isfile(CA):
        print("test-createacct-units: cannot read %s" % CA)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    src, msgs = load()
    rows = check(src, msgs)
    bad = report(rows)
    print("\ntest-createacct-units: %d passed, %d failed." % (len(rows) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
