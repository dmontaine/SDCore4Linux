#!/usr/bin/env python3
"""test-remotesdsys-units.py - the REMOTE.SDSYS verb (`gpl.bp/remotesdsys`, S.95 stage 1b, rewritten for S.106) as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-remotesdsys-units.py [--selftest]

2 Nov 26 dm S.106 (owner: "remove the authenticator from both local and remote logins, we will depend on just password authentication for this release"): the verb is ON | OFF and runs
only `sudo -n /usr/local/sbin/sd-elevate sdsys-ssh`; everything that handled a secret, a code or a recovery code (the COMO refusal, the private directory, the code file, the screen clearing,
RECOVERY and LOCAL) is gone, and this file holds that ABSENCE as well as the verb's order.

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the verb's BASIC as text, with comments removed.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT SSH IS OPENED FOR SDSYS***: that is the root
helper's (`sd-elevate sdsys-ssh`, `test-sd-elevate.py --only=sdsys-ssh`, and `test-sshd-sdsys.py` for the sshd side), and the real sshd on a real install is a VM row.  What a text check is for: the properties
that keep the administrator's door where it belongs - the administrator is asked first; the keyword is parsed and checked BEFORE anything is run; the helper is the only thing run, always `sudo -n`
with a fixed verb and a word the parse checked; the audit line holds the keyword and the status and nothing the helper printed; the program writes no file; no trace of the authenticator
code is left.  Those are ORDER and ABSENCE, and an edit that moves one still compiles.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
MSGS = (11923, 11924, 11929)
GONE = (11190, 11925, 11926, 11927, 11928, 11939, 11945)          # the authenticator code's messages, deleted by S.106 (the numbers stay this port's and are not reused)
FILES = {
    "prog": os.path.join(GPL, "remotesdsys"),
    "voc": os.path.join(SDSYS, "voc_template", "remote.sdsys"),
}
for _n in MSGS:
    FILES["m%d" % _n] = os.path.join(SDSYS, "messages", str(_n))
NEWVOC = os.path.join(SDSYS, "newvoc", "remote.sdsys")
HELPER = "sudo -n /usr/local/sbin/sd-elevate"


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    raw["newvoc_has"] = "1" if os.path.exists(NEWVOC) else ""
    raw["gone_left"] = " ".join(str(n) for n in GONE if os.path.exists(os.path.join(SDSYS, "messages", str(n))))
    others = []
    for name in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, name)
        if name != "remotesdsys" and os.path.isfile(p):
            with open(p, encoding="latin-1") as f:
                t = f.read()
            if re.search(r"sysmsg\(\s*(%s)\b" % "|".join(str(n) for n in MSGS + GONE), strip_bas(t)):
                others.append(name)
    raw["others"] = " ".join(others)
    return raw


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    pg = strip_bas(raw["prog"])
    report = pg[: pg.find("   action = downcase(trim(action))")] if "   action = downcase(trim(action))" in pg else pg

    ck("RS0", "NULL CASE: the verb, its VOC entry and its three messages were found and are not empty (a check on nothing would pass)",
       len(pg) > 900 and raw["voc"].strip() != "" and all(raw["m%d" % n].strip() != "" for n in MSGS), "%d" % len(pg))
    ck("RS1", "the verb is an internal program catalogued as $remotesdsys; SDSYS's VOC has it (V CA $remotesdsys) and the shared VOC (newvoc) does NOT",
       re.search(r"^\$internal\s*\nprogram \$remote\.sdsys\s*\n\$catalog \$remotesdsys\b", pg, re.M) is not None and raw["voc"].split("\n")[:3] == ["V", "CA", "$remotesdsys"] and raw["newvoc_has"] == "",
       repr((raw["voc"][:30], raw["newvoc_has"])))
    i_adm = pg.find("if not(kernel(K$ADMINISTRATOR, -1)) then")
    i_first = min([x for x in (pg.find("os.execute"), pg.find("call @parser")) if x >= 0] or [10 ** 9])
    ck("RS2", "the administrator is asked FIRST (message 2001 and stop), before the sentence is parsed and before anything is run",
       0 < i_adm < i_first and re.search(r"if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\s*\n\s*stop sysmsg\(2001\)", pg) is not None, "adm %d first %d" % (i_adm, i_first))
    i_run = pg.find("os.execute HELPER : ' sdsys-ssh ' : action")
    ck("RS3", "the keyword is on or off only (else the usage, 11923), nothing after it (else the usage), both tested BEFORE the helper is run with the word",
       "if action # 'on' and action # 'off' then" in pg and pg.count("stop sysmsg(11923)") == 2 and "if token.type # PARSER$END then" in pg
       and 0 < pg.find("if action # 'on' and action # 'off'") < pg.find("if token.type # PARSER$END then", pg.find("if action # 'on'")) < i_run, "run %d" % i_run)
    execs = re.findall(r"os\.execute ([^\n]*)", pg)
    ck("RS4", "THE HELPER IS THE ONLY THING RUN, with sudo -n and a FIXED verb: the report is `sdsys-ssh status`, the change is `sdsys-ssh` and the word the parse checked; nothing is captured; "
       "no execute, perform, chain or phantom",
       "$define HELPER     '%s'" % HELPER in pg and sorted(execs) == sorted(["HELPER : ' sdsys-ssh status'", "HELPER : ' sdsys-ssh ' : action"]) and "capturing" not in pg
       and not re.search(r"^\s*(execute|perform|chain|phantom)\b", pg, re.M), repr(execs))
    ck("RS5", "no keyword REPORTS and changes nothing: the report is run only on an empty keyword, and ends in `stop` before the keyword is looked at",
       "if token.type = PARSER$END or action = '' then" in report and report.count("os.execute") == 1 and re.search(r"os\.execute HELPER : ' sdsys-ssh status'[\s\S]*\n      stop\n   end", report) is not None
       and "os.execute" not in pg[pg.find("action = downcase(trim(action))"):pg.find("os.execute HELPER : ' sdsys-ssh ' : action")], "")
    aud = re.findall(r"kernel\(K\$AUDIT, ([^\n]*)\)", pg)
    ck("RS6", "ONE audit line, after the work, holding the keyword and the helper's status only (lower case, never what the helper printed)",
       aud == ["'remote.sdsys ' : action : ' status=' : rc"] and pg.find("kernel(K$AUDIT") > i_run > 0, repr(aud))
    ck("RS7", "THE PROGRAM WRITES NO FILE: no openseq, writeseq, write, delete, logmsg or errlog, and nothing is printed with display (which a phantom would log)",
       not re.search(r"\b(openseq|writeseq|writeblk)\b", pg) and not re.search(r"^\s*(write|writev|writeu|matwrite|delete|deleteseq|logmsg)\b", pg, re.M) and "errlog" not in pg and not re.search(r"^\s*display\b", pg, re.M), "")
    ck("RS8", "S.106: NOTHING OF THE AUTHENTICATOR CODE IS LEFT in the program's code: no secret, code, recovery, COMO, private directory, screen clearing, totp or local word",
       not any(w in pg.lower() for w in ("totp", "secret", "recovery", "authenticator", "como", "pdir", "c.path", "clear.screen", "otpauth", "'local'", "umask")), "")
    ck("RS9", "the success sentence (11929) is shown only for a change to ON that the helper reported done (rc 0); a failure shows 11924 with the word and the status and not the success sentence",
       re.search(r"if rc # 0 then\s*\n\s*crt sysmsg\(11924, action, rc\)\s*\n\s*end else\s*\n\s*if action = 'on' then crt sysmsg\(11929\)", pg) is not None, "")
    used = sorted(set(int(x) for x in re.findall(r"sysmsg\((\d+)", pg)))
    ck("RS10", "the three messages are the Linux block's (11000-11999), each used by this verb and by no other program; 2001 is the administrator refusal; none of the deleted ones is used or present",
       used == sorted(list(MSGS) + [2001]) and all(11000 <= n < 12000 for n in MSGS) and raw["others"] == "" and raw["gone_left"] == "", repr((used, raw["others"], raw["gone_left"])))
    m = raw["m11923"]
    ck("RS11", "the usage is lower case where it names the command (remote.sdsys on | off), says what each word does and that no keyword changes nothing, and names no code",
       m.startswith("remote.sdsys on | off") and "REMOTE.SDSYS" not in m and "changes nothing" in m and not any(w in (m + raw["m11924"] + raw["m11929"]).lower() for w in ("authenticator", "recovery", "totp", "secret")), m[:60])
    ck("RS12", "the success sentence says the truth about what ON does: other computers, the password, and that nothing else stands between the network and the administrator; and how to shut it",
       "password" in raw["m11929"] and "nothing else stands" in raw["m11929"].replace("\n", " ") and "remote.sdsys off" in raw["m11929"], raw["m11929"][:80])
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if old not in r[key]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (key, old[:60]))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


def setkey(key, val):
    def f(raw):
        r = dict(raw)
        r[key] = val
        return r
    return f


MUTANTS = [
    ("an ordinary account gets the verb", "RS1", setkey("newvoc_has", "1")),
    ("the administrator is asked after the parse", "RS2", sub("prog", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001)  ;* Command requires administrator privileges\n   end\n", "")),
    ("any keyword is taken", "RS3", sub("prog", "   if action # 'on' and action # 'off' then", "   if action = '' then")),
    ("words after the keyword are allowed", "RS3", sub("prog", "   if token.type # PARSER$END then\n      @system.return.code = -ER$ARGS\n      stop sysmsg(11923)\n   end\n", "")),
    ("the helper is run without -n", "RS4", sub("prog", "$define HELPER     'sudo -n /usr/local/sbin/sd-elevate'", "$define HELPER     'sudo /usr/local/sbin/sd-elevate'")),
    ("a shell command is run", "RS4", sub("prog", "   action = ''\n   extra = ''\n", "   action = ''\n   extra = ''\n   os.execute 'id'\n")),
    ("the helper's output is captured", "RS4", sub("prog", "   os.execute HELPER : ' sdsys-ssh ' : action\n", "   os.execute HELPER : ' sdsys-ssh ' : action capturing out\n")),
    ("the word typed reaches the helper unchecked", "RS4", sub("prog", "   os.execute HELPER : ' sdsys-ssh ' : action\n", "   os.execute HELPER : ' sdsys-ssh ' : @sentence\n")),
    ("no keyword changes something", "RS5", sub("prog", "      os.execute HELPER : ' sdsys-ssh status'\n", "      os.execute HELPER : ' sdsys-ssh off'\n")),
    ("the report does not stop", "RS5", sub("prog", "         crt sysmsg(11924, 'report', rc)\n      end\n      stop\n   end", "         crt sysmsg(11924, 'report', rc)\n      end\n   end")),
    ("the audit line carries the helper's words", "RS6", sub("prog", "kernel(K$AUDIT, 'remote.sdsys ' : action : ' status=' : rc)", "kernel(K$AUDIT, 'remote.sdsys ' : action : ' status=' : rc : ' ' : out)")),
    ("the audit line is before the work", "RS6", sub("prog", "   void kernel(K$AUDIT, 'remote.sdsys ' : action : ' status=' : rc)\n", "")),
    ("a file is written", "RS7", sub("prog", "   rc = os.error()\n   if rc # 0 then\n      crt sysmsg(11924, action, rc)", "   rc = os.error()\n   openseq '/tmp/s' to s.f then writeseq action to s.f else null\n   if rc # 0 then\n      crt sysmsg(11924, action, rc)")),
    ("the word local comes back", "RS8", sub("prog", "   action = ''\n   extra = ''\n", "   action = ''\n   extra = ''\n   if action = 'local' then null\n")),
    ("the word totp comes back", "RS8", sub("prog", "   action = ''\n   extra = ''\n", "   action = ''\n   extra = ''\n   os.execute HELPER : ' totp-status'\n")),
    ("a COMO guard comes back", "RS8", sub("prog", "   action = ''\n   extra = ''\n", "   action = ''\n   extra = ''\n   if system(SYS$COMO_ON) then null\n")),
    ("the success sentence is shown for a failure too", "RS9", sub("prog", "      if action = 'on' then crt sysmsg(11929)  ;* ssh is open for sdsys", "      crt sysmsg(11929)  ;* ssh is open for sdsys")),
    ("a message of another program is used", "RS10", setkey("others", "remotessh")),
    ("a deleted message comes back", "RS10", setkey("gone_left", "11926")),
    ("the usage names the command in capitals", "RS11", sub("m11923", "remote.sdsys on | off", "REMOTE.SDSYS on | off")),
    ("the usage mentions the code", "RS11", sub("m11923", "ON        opens ssh for sdsys", "ON        opens ssh for sdsys, with an authenticator code")),
    ("the success sentence leaves out the risk", "RS12", sub("m11929", "and nothing else stands between the network and the administrator", "and that is all")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:200]))
        bad += 0 if ok else 1
    return bad


def selftest(raw):
    base = [r[0] for r in checks(raw) if not r[2]]
    if base:
        print("selftest: the unchanged tree fails %s, so a mutant's own failure cannot be told from the tree's; run the plain check first" % base)
        return 1
    holes = 0
    for name, want, mut in MUTANTS:
        try:
            m = mut(raw)
        except KeyError as exc:
            print("  [FAIL] selftest: %s  <- %s" % (name, exc))
            holes += 1
            continue
        failed = sorted({r[0] for r in checks(m) if not r[2]})
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        holes += 0 if hit else 1
    print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    raw = load()
    print("test-remotesdsys-units: tree %s" % SDSYS)
    print("test-remotesdsys-units: files %s" % " ".join(FILES[k] for k in ("prog", "voc")))
    if "--selftest" in sys.argv[1:]:
        return selftest(raw)
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-remotesdsys-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
