#!/usr/bin/env python3
"""test-remotesdsys-units.py - the REMOTE.SDSYS verb (`gpl.bp/remotesdsys`, S.95 stage 1b) as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-remotesdsys-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the verb's BASIC as text, with comments removed.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT A CODE IS SET UP OR THAT
A SECRET IS SHOWN***: those are the root helper's (`sd-elevate totp-*`, `sd-totp`), which a sandbox cannot run; that is a VM row.  What a text check is for: the
properties that keep the secret and the recovery codes where they belong - the administrator is asked first; ON and RECOVERY refuse while COMO records the
session, BEFORE the helper is called; the helper is the only thing run, always `sudo -n` with a fixed verb; the code reaches it on STANDARD INPUT from a file in
a private 0700 directory and never on a command line; the code is checked to be 6 to 8 digits before it is handed over, at most three times; the audit line
holds the keyword and the status and nothing the helper printed; the lines echoed on a failure leave out secret=, uri= and recovery=; the variables are
cleared and the screen is cleared after Enter; the program writes no other file.  Those are ORDER and ABSENCE, and an edit that moves one still compiles.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
MSGS = (11923, 11924, 11925, 11926, 11927, 11928, 11929, 11939, 11945)
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
    others = []
    for name in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, name)
        if name != "remotesdsys" and os.path.isfile(p):
            with open(p, encoding="latin-1") as f:
                t = f.read()
            if re.search(r"\b(%s)\b" % "|".join(str(n) for n in MSGS), strip_bas(t)) and re.search(r"sysmsg\(\s*(%s)\b" % "|".join(str(n) for n in MSGS), t):
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


def block(text, label):
    m = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][a-z.0-9]*:\s*$|^end\s*$", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    pg = strip_bas(raw["prog"])
    main = pg[: pg.find("do.on:")] if "do.on:" in pg else pg
    on = block(pg, "do.on")
    rec = block(pg, "do.recovery")
    off = block(pg, "do.off")
    cc = block(pg, "confirm.code")
    mk = block(pg, "make.pdir")
    so = block(pg, "show.out")
    cs = block(pg, "clear.screen")

    ck("RS0", "NULL CASE: the verb, its VOC entry and its nine messages were found and are not empty (a check on nothing would pass)",
       len(pg) > 3000 and raw["voc"].strip() != "" and all(raw["m%d" % n].strip() != "" for n in MSGS), "%d" % len(pg))
    ck("RS1", "the verb is an internal program catalogued as $remotesdsys; SDSYS's VOC has it (V CA $remotesdsys) and the shared VOC (newvoc) does NOT",
       re.search(r"^\$internal\s*\nprogram \$remote\.sdsys\s*\n\$catalog \$remotesdsys\b", pg, re.M) is not None and raw["voc"].split("\n")[:3] == ["V", "CA", "$remotesdsys"] and raw["newvoc_has"] == "",
       repr((raw["voc"][:30], raw["newvoc_has"])))
    i_adm = pg.find("if not(kernel(K$ADMINISTRATOR, -1)) then")
    i_first = min([x for x in (pg.find("os.execute"), pg.find("call @parser")) if x >= 0] or [10 ** 9])
    ck("RS2", "the administrator is asked FIRST (message 2001 and stop), before the sentence is parsed and before anything is run",
       0 < i_adm < i_first and re.search(r"if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\s*\n\s*stop sysmsg\(2001\)", pg) is not None, "adm %d first %d" % (i_adm, i_first))
    ck("RS3", "the keyword is on, recovery, off or local only (else the usage, 11923), local takes on or off (else the usage), nothing after, all tested before any change",
       "if action # 'on' and action # 'recovery' and action # 'off' and action # 'local' then" in main and main.count("stop sysmsg(11923)") == 3 and "if token.type # PARSER$END then" in main
       and "if extra # 'on' and extra # 'off' then" in main
       and 0 < main.find("if action # 'on'") < main.find("if extra # 'on'") < main.find("gosub do.on"), "")
    i_como = main.find("if (action = 'on' or action = 'recovery') and system(SYS$COMO_ON) then")
    ck("RS4", "ON and RECOVERY REFUSE while a COMO file records the session (SYSTEM(1033), message 11925), BEFORE either is called; OFF and LOCAL show nothing secret and are not refused",
       0 < i_como < main.find("gosub do.on") and i_como < main.find("gosub do.recovery")
       and re.search(r"if \(action = 'on' or action = 'recovery'\) and system\(SYS\$COMO_ON\) then\s*\n[^\n]*\n\s*stop sysmsg\(11925\)", main) is not None, "como %d" % i_como)
    execs = re.findall(r"os\.execute ([^\n]*)", pg)
    helper_execs = [e for e in execs if "HELPER" in e]
    other_execs = [e for e in execs if "HELPER" not in e and e != "cmd capturing out"]
    ck("RS5", "THE HELPER IS THE ONLY THING RUN, with sudo -n and a FIXED verb: every os.execute is HELPER (or cmd, built from HELPER) with totp-status, totp-off or the cmd of run.cmd; "
       "the others only make, fill and remove the private directory and the code file; no execute, perform, chain or phantom",
       "$define HELPER     '%s'" % HELPER in pg and sorted(helper_execs) == sorted(["HELPER : ' totp-status'", "HELPER : ' totp-off'", "HELPER : ' totp-local ' : field(action, ' ', 2)"]) and "os.execute cmd capturing out" in pg
       and sorted(re.findall(r"cmd = (HELPER[^\n]*)", pg)) == sorted(["HELPER : ' totp-begin 2>&1'", "HELPER : ' totp-recovery 2>&1'", "HELPER : \" totp-confirm < '\" : c.path : \"' 2>&1\""])
       and all(e.startswith('"umask 077 && ') or e.startswith('"rm -') for e in other_execs) and len(other_execs) == 4
       and not re.search(r"^\s*(execute|perform|chain|phantom)\b", pg, re.M), repr((helper_execs, other_execs)))
    ck("RS6", "THE CODE IS NEVER ON A COMMAND LINE: confirm.code writes it to a file in the private directory and gives the helper that file on standard input, then removes the file; "
       "no os.execute names the code",
       0 < cc.find("os.execute \"umask 077 && : > '\" : c.path") < cc.find("openseq c.path to c.f") < cc.find("writeseq code to c.f") < cc.find("close c.f\n   cmd") < cc.find("gosub run.cmd") < cc.find("os.execute \"rm -f -- '\" : c.path")
       and "c.path = pdir : '/c'" in cc and not any("code" in e for e in execs + re.findall(r"cmd = ([^\n]*)", pg)), cc[:200])
    ck("RS7", "the private directory is made with umask 077 and mkdir (which refuses a name that exists, a planted link included), under /tmp with the user number, and is removed after the tries",
       "os.execute \"umask 077 && mkdir -- '\" : pdir : \"'\"" in mk and "pdir = '/tmp/sd-totp.' : @userno" in mk and "if os.error() # 0 then pdir = ''" in mk
       and 0 < on.find("gosub make.pdir") < on.find("for try = 1 to CODE.TRIES") < on.find("gosub drop.pdir") and "if pdir = '' then" in on, "")
    ck("RS8", "the code is 6 to 8 digits, tested BEFORE it is handed over; at most CODE.TRIES (3) tries; an empty answer stops; a code the helper threw away (discarded) stops",
       "$define CODE.TRIES 3" in pg and "if len(code) < 6 or len(code) > 8 or not(code matches '0N') then" in on and 0 < on.find("if len(code) < 6") < on.find("gosub confirm.code")
       and "if code = '' then exit" in on and "if refused = 'discarded' then exit" in on, "")
    ck("RS9", "WHAT IS ECHOED HOLDS NO SECRET: show.out leaves out secret=, uri= and recovery= lines; the secret and the link are cleared once shown; the code is cleared after each try and at the end",
       "if out<i>[1, 7] # 'secret=' and out<i>[1, 4] # 'uri=' and out<i>[1, 9] # 'recovery=' then crt" in so
       and on.find("crt '  Secret: ' : secret") < on.find("secret = '' ; uri = ''", on.find("crt '  Secret: '")) and len(re.findall(r"(?m)^\s*code = ''\s*$", on)) == 2, "")
    aud = re.findall(r"kernel\(K\$AUDIT, ([^\n]*)\)", pg)
    ck("RS10", "ONE audit line, after the work, holding the keyword and the helper's status only (lower case, never out, secret, uri or code)",
       aud == ["'remote.sdsys ' : action : ' status=' : rc"] and main.find("kernel(K$AUDIT") > main.find("end case") > 0, repr(aud))
    ck("RS11", "the screen is cleared after the secret or the codes were shown: ON (when a secret was shown) and RECOVERY end with clear.screen, which waits for Enter and clears with @(-1)",
       on.count("gosub clear.screen") == 2 and rec.count("gosub clear.screen") == 1 and 0 < cs.find("input junk") < cs.find("crt @(-1)")
       and re.search(r"gosub show\.codes[\s\S]*gosub clear\.screen", rec) is not None, "")
    ck("RS12", "THE PROGRAM WRITES NO OTHER FILE: one openseq (the code file), one writeseq (the code), no write, delete, logmsg or errlog; nothing is printed with display (which a phantom would log)",
       pg.count("openseq ") == 1 and pg.count("writeseq ") == 1 and not re.search(r"^\s*(write|writev|writeu|matwrite|delete|deleteseq|logmsg)\b", pg, re.M) and "errlog" not in pg and not re.search(r"^\s*display\b", pg, re.M), "")
    ck("RS13", "OFF runs only the helper's totp-off, which closes sshd for sdsys FIRST (sd-elevate's order); it shows its words and nothing is captured",
       off.count("os.execute") == 1 and "os.execute HELPER : ' totp-off'" in off and "capturing" not in off, off[:120])
    used = sorted(set(int(x) for x in re.findall(r"sysmsg\((\d+)", pg)))
    ck("RS14", "the nine messages are the Linux block's (11000-11999), each used by this verb and by no other program; 2001 is the administrator refusal",
       used == sorted(list(MSGS) + [2001]) and all(11000 <= n < 12000 for n in MSGS) and raw["others"] == "", repr((used, raw["others"])))
    m = raw["m11923"]
    ck("RS15", "the usage is lower case where it names the command (remote.sdsys on | recovery | off | local on | local off) and says what each word does and that no keyword changes nothing",
       m.startswith("remote.sdsys on | recovery | off | local on | local off") and "REMOTE.SDSYS" not in m and "changes nothing" in m and "COMO OFF" in raw["m11925"], m[:60])
    loc = block(pg, "do.local")
    ck("RS16", "S.101 stage D: LOCAL ON / OFF runs only the helper's totp-local with the word on or off that the parse checked, shows its words (nothing captured), and the audit line says 'local on|off'",
       loc.count("os.execute") == 1 and "os.execute HELPER : ' totp-local ' : field(action, ' ', 2)" in loc and "capturing" not in loc
       and "action = 'local ' : extra" in main and "case action[1, 5] = 'local'" in main, loc[:120])
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
    ("any keyword is taken", "RS3", sub("prog", "   if action # 'on' and action # 'recovery' and action # 'off' and action # 'local' then", "   if action = '' then")),
    ("local takes any word", "RS3", sub("prog", "      if extra # 'on' and extra # 'off' then", "      if extra = '' then")),
    ("COMO is not asked", "RS4", sub("prog", "   if (action = 'on' or action = 'recovery') and system(SYS$COMO_ON) then", "   if 0 then")),
    ("COMO is asked only for on", "RS4", sub("prog", "   if (action = 'on' or action = 'recovery') and system(SYS$COMO_ON) then", "   if action = 'on' and system(SYS$COMO_ON) then")),
    ("local captures its output", "RS16", sub("prog", "   os.execute HELPER : ' totp-local ' : field(action, ' ', 2)\n", "   os.execute HELPER : ' totp-local ' : field(action, ' ', 2) capturing out\n")),
    ("the helper is run without -n", "RS5", sub("prog", "$define HELPER     'sudo -n /usr/local/sbin/sd-elevate'", "$define HELPER     'sudo /usr/local/sbin/sd-elevate'")),
    ("a shell command is run", "RS5", sub("prog", "   pdir = ''\n\n   parser", "   pdir = ''\n   os.execute 'id'\n\n   parser")),
    ("the code goes on the command line", "RS6", sub("prog", "   cmd = HELPER : \" totp-confirm < '\" : c.path : \"' 2>&1\"", "   cmd = 'printf \"' : code : '\\n\" | ' : HELPER : ' totp-confirm 2>&1'")),
    ("the code file is left behind", "RS6", sub("prog", "   os.execute \"rm -f -- '\" : c.path : \"'\"\n", "")),
    ("the directory is made without umask", "RS7", sub("prog", "   os.execute \"umask 077 && mkdir -- '\" : pdir : \"'\"", "   os.execute \"mkdir -p -- '\" : pdir : \"'\"")),
    ("the directory is not removed", "RS7", sub("prog", "   code = ''\n   gosub drop.pdir\n", "   code = ''\n")),
    ("any code is handed over", "RS8", sub("prog", "      if len(code) < 6 or len(code) > 8 or not(code matches '0N') then", "      if 0 then")),
    ("unlimited tries", "RS8", sub("prog", "$define CODE.TRIES 3", "$define CODE.TRIES 99")),
    ("a failure echoes the secret line", "RS9", sub("prog", "      if out<i>[1, 7] # 'secret=' and out<i>[1, 4] # 'uri=' and out<i>[1, 9] # 'recovery=' then crt", "      if out<i>[1, 4] # 'uri=' and out<i>[1, 9] # 'recovery=' then crt")),
    ("the secret is kept", "RS9", sub("prog", "   crt sysmsg(11926)  ;* put it into the app; it is shown this once\n   secret = '' ; uri = ''\n", "   crt sysmsg(11926)  ;* put it into the app; it is shown this once\n")),
    ("the audit line carries the helper's words", "RS10", sub("prog", "kernel(K$AUDIT, 'remote.sdsys ' : action : ' status=' : rc)", "kernel(K$AUDIT, 'remote.sdsys ' : action : ' status=' : rc : ' ' : out)")),
    ("the codes stay on the screen", "RS11", sub("prog", "   crt sysmsg(11939)\n   out = ''\n   gosub clear.screen\n", "   crt sysmsg(11939)\n   out = ''\n")),
    ("the screen is not cleared", "RS11", sub("prog", "   crt @(-1) :\n", "")),
    ("the secret is written to a file", "RS12", sub("prog", "   crt sysmsg(11926)  ;* put", "   openseq '/tmp/s' to s.f then writeseq secret to s.f else null\n   crt sysmsg(11926)  ;* put")),
    ("the code is logged", "RS12", sub("prog", "      gosub confirm.code\n", "      logmsg code\n      gosub confirm.code\n")),
    ("OFF captures its output", "RS13", sub("prog", "   os.execute HELPER : ' totp-off'\n", "   os.execute HELPER : ' totp-off' capturing out\n")),
    ("a message of another program is used", "RS14", setkey("others", "remotessh")),
    ("the usage names the command in capitals", "RS15", sub("m11923", "remote.sdsys on | recovery | off", "REMOTE.SDSYS on | recovery | off")),
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
