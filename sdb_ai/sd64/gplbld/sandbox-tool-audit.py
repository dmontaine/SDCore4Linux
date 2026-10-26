#!/usr/bin/env python3
#
# sandbox-tool-audit.py - the audit trail page, TOOL.AUDIT, and its reader $AUDIT_READ, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A5; plan
# .claude/plan-fullscreen-toolkit.md section 5).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-audit.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the reader and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN, the person who runs this suite) opens TOOL.AUDIT on a 140 by 43 terminal.  The sandbox's audit file is REPLACED by a fixture this
# suite writes: 1,500 lines, the first 1,000 of about 100 bytes and the last 500 of about 600 (about 450 kilobytes, so seven 64 kilobyte blocks, and the newest 200 lines alone take two
# block boundaries), five users, one with sudo, six events, a line with spaces in a value, a line of 2,000 characters, a line with a byte of the mark range, an upper case account name,
# and a rotated file beside it with two decoys that are not audit files.  (The first fixture had short lines only, so 200 lines never crossed a boundary and the mutant that throws away
# the piece of a line held across a boundary, carry-lost, survived: found by running it, 25 Oct.)
#
# THE INSTRUMENT.  The page is judged against the FILE, not against itself: a Python reader written from the documented line format (not from the BASIC) parses the same bytes and
# gives the lines a filter must pass; for every case the page's row text, its count and the lines it saved (X writes them to a record of the $HOLD file, which is read from the disk) are
# compared with that.  The lines the page shows for a filter that passes more than it loads are the NEWEST ones; the records saved by X after the page has gone back to the start of the
# file must equal the file line for line, which is the check that no block boundary lost or doubled a line.
#
#   A0   an ordinary account has no tool.audit; a VOC entry that points at the program is refused for the administrator's page only; $audit_read refuses an ordinary program
#   A1   the page opens: one audit line; the top box; the last 17 rows equal the file's last 17 lines; the newest 200 are loaded
#   A2   Page Up past the first loaded line reads further back to the start of the file: the count is the file's, and the lines saved equal the file's (block boundaries, the
#        2,000-character line, the mark-range byte as a question mark)
#   A3   the filters one by one and together (event, account without regard to case, user or sudo user, text with spaces, from and to by prefix) against the Python reader;
#        Esc leaves them as they were; a bad time is refused; C clears them
#   A4   D goes to the first line at or after a time (loading older lines as far as it must), and says so when no loaded line is
#   A5   a last line with no line feed is not shown (by F5, and by a fresh read from the end); when it is finished it is shown; follow mode shows new lines and stops
#   A6   O shows the rotated file and cycles over the audit files only (the decoys are not offered)
#   A7   X saves what is loaded and writes its audit line
#   A8   the mouse, F1, a small window, an input that ends; an emptied file (rotation) is read again
# NOT HELD: a real install's file (owner, mode 600, the append-only attribute) and the daemon that writes it (W.11 F4's witness), the help text itself (sandbox-docs.py).
import datetime
import getpass
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_toolaudit", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
MUTANT = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ACC = "zzhd"
PROBE = """   call $audit_read('size', '', '', '', o, e)
   crt 'ZZAR size=[':o:'] err=[':e:']'
end
"""
WRITER = """   open 'voc' to v else
      crt 'ZZAW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$tool_audit' to v, 'ztaud' on error
      crt 'ZZAW refused ':status()
      stop
   end
   crt 'ZZAW written'
end
"""

MUTANTS = {
    # name: (old text of the sandbox's audit_read, new text, the row ids that must fail and no others, the last section run)
    "back-partial": ("            if buf[len(buf), 1] # LF then\n", "            if 0 then\n", ["A5"], "A5"),                               # a last piece with no line feed is taken for a line when reading from the end
    "fwd-partial": ("      nlines = dcount(buf, LF) - 1\n", "      nlines = dcount(buf, LF)\n", ["A5"], "A5"),                  # ... and when reading forward
    "carry-lost": ("      carry = buf[1, k]\n", "      carry = ''\n", ["A2"], "A2"),                                    # the piece of a line left at the start of a block is thrown away
    "sudo-ignored": ("      if downcase(p.user) # downcase(s) and downcase(p.sudo) # downcase(s) then okl = 0\n", "      if downcase(p.user) # downcase(s) then okl = 0\n", ["A3"], "A3"),
}

# ------------------------------------------------------------------------------------------------------------------------------- the fixture and the Python reader

USERS = [("fred", 1001, ""), ("zzhd", 1002, ""), ("sdsys", 1003, ""), ("marge", 1004, "sdsys"), ("zzhm", 1005, "don")]
EVENTS = [("login", ["account={a}", "from=local"]), ("modify.account net-on", ["account={a}"]), ("api refused", ["request=29", "reason=os gate off", "user={u}"]),
          ("tool start", ["app=tool.gates"]), ("backup.account", ["account={a}", "file=SD-host-{a}.zip"]), ("set.tile off", ["tile=ide", "account={a}"])]
ACCOUNTS = ["fred", "zzhd", "zzhm", "marge", "shared"]
N_FIXTURE = 1500
BASE = datetime.datetime(2026, 10, 20, 8, 0, 0)
STEP = 190


def fixture_lines():
    out = []
    for i in range(N_FIXTURE):
        t = BASE + datetime.timedelta(seconds=STEP * i)
        u, uid, sudo = USERS[i % len(USERS)]
        ev, pairs = EVENTS[i % len(EVENTS)]
        a = ACCOUNTS[(i // 3) % len(ACCOUNTS)]
        if i == 100:
            a = "Fred"
        ps = [p.format(a=a, u=u) for p in pairs]
        if i == 250:
            ps.append("reason=the gate was off")
        if i == 700:
            ps.append("note=" + "x" * 1900)
        if i == 900:
            ps.append("note=a\xfbb")
        if i >= 1000:
            ps.append("note=" + "n" * 500)               # 600-byte lines: 200 of them are 120 kilobytes, so loading them takes two block boundaries, every line crossing one passing any filter
        ps.append("seq=%d" % i)
        head = "%s user=%s%s uid=%d pid=%d" % (t.strftime("%Y-%m-%d %H:%M:%S"), u, (" sudo=" + sudo) if sudo else "", uid, 20000 + i)
        out.append(head + " " + ev + " " + " ".join(ps))
    return out


def rotated_lines():
    out = []
    for i in range(40):
        t = datetime.datetime(2026, 10, 1, 12, 0, 0) + datetime.timedelta(seconds=60 * i)
        out.append("%s user=sdsys uid=1003 pid=%d old.event account=rot%d seq=%d" % (t.strftime("%Y-%m-%d %H:%M:%S"), 100 + i, i % 3, i))
    return out


HDR = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) user=(\S+)(?: sudo=(\S+))? uid=(\S+) pid=(\S+)(?: (.*))?$")


def parse(line):
    m = HDR.match(line)
    if not m:
        return None
    stamp, user, sudo, uid, pid, rest = m.groups()
    toks = (rest or "").split()
    i = 0
    event = []
    while i < len(toks) and "=" not in toks[i]:
        event.append(toks[i])
        i += 1
    pairs = []
    for t in toks[i:]:
        if "=" in t:
            pairs.append(t)
        elif pairs:
            pairs[-1] += " " + t
    return {"stamp": stamp, "user": user, "sudo": sudo or "", "uid": uid, "pid": pid, "event": event, "pairs": pairs}


def passes(line, f):
    if f.get("from") and line[:len(f["from"])] < f["from"]:
        return False
    if f.get("to") and line[:len(f["to"])] > f["to"]:
        return False
    if f.get("text") and f["text"].lower() not in line.lower():
        return False
    if f.get("event") or f.get("account") or f.get("user"):
        p = parse(line)
        if p is None:
            return False
        if f.get("event") and f["event"].lower() not in " ".join(p["event"]).lower():
            return False
        if f.get("account") and not any(x.lower() == "account=" + f["account"].lower() for x in p["pairs"]):
            return False
        if f.get("user") and f["user"].lower() not in (p["user"].lower(), p["sudo"].lower()):
            return False
    return True


def row_text(line):
    p = parse(line)
    t = p["stamp"][:19].ljust(19) + " " + p["user"][:10].ljust(10) + " " + " ".join(p["event"])[:28].ljust(28) + " " + "  ".join(p["pairs"])
    return t[:134].rstrip()


def audit_path(name="audit"):
    return os.path.join(sh.SYS, name)


def file_lines(name="audit"):
    """The complete lines of the audit file as the reader must give them: a last piece with no line feed left out, the marks (248 to 255) read as a question mark."""
    data = open(audit_path(name), "rb").read()
    if data and not data.endswith(b"\n"):
        data = data[:data.rfind(b"\n") + 1]
    txt = data.decode("latin-1")
    txt = "".join("?" if 248 <= ord(c) <= 255 else c for c in txt)
    return [ln for ln in txt.split("\n") if ln != ""]


def put_fixture():
    with open(audit_path(), "wb") as f:
        f.write(("\n".join(fixture_lines()) + "\n").encode("latin-1"))
    with open(audit_path("audit.20261001-120000"), "wb") as f:
        f.write(("\n".join(rotated_lines()) + "\n").encode("latin-1"))
    for decoy in ("audit.junk", "audit.20261001-12000x"):
        with open(audit_path(decoy), "wb") as f:
            f.write(b"2026-10-01 12:00:00 user=nobody uid=1 pid=1 decoy\n")


def append(text):
    with open(audit_path(), "ab") as f:
        f.write(text.encode("latin-1"))


def new_line(tag, n):
    t = datetime.datetime(2026, 10, 25, 9, 0, 0) + datetime.timedelta(seconds=n)
    return "%s user=fred uid=1001 pid=%d zz.%s account=fred seq=%d" % (t.strftime("%Y-%m-%d %H:%M:%S"), 40000 + n, tag, n)


# ------------------------------------------------------------------------------------------------------------------------------- the page

def arow(rid, name, ok, detail=""):
    """A row with an id (A3 ...): the mutant mode compares the ids that failed with the ids that had to."""
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def st(h):
    return h.line(40)


def hold_records():
    d = os.path.join(sh.SYS, "$hold")
    try:
        return sorted(n for n in os.listdir(d) if n.startswith("audit."))
    except OSError:
        return []


def setup_pages():
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "audit_read"), os.path.join(sh.SYS, "gpl.bp", "audit_read"))
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_audit"), os.path.join(sh.SYS, "gpl.bp", "tool_audit"))
    for prog in ("audit_read", "tool_audit"):
        out = g.adm(["BASIC gpl.bp " + prog], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (prog, "\n".join(out[-8:])))
    out = g.adm(["CATALOG gpl.bp audit_read tool_audit"], internal=True)
    # the ordinary programs are compiled into the account that runs them
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzar"), PROBE)
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzaw"), WRITER)


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "audit_read")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp audit_read"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant reader did not compile:\n" + "\n".join(out[-8:]))
    g.adm(["CATALOG gpl.bp audit_read"], internal=True)


class Page:
    """A session on tool.audit on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.audit\r", idle=4.0)
        self.flt = ["", "", "", "", "", ""]

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.6):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def top(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(2, 6)))

    def loaded(self):
        m = re.search(r"Lines loaded: (\d+)", self.top())
        return int(m.group(1)) if m else None

    def rows(self):
        return [self.line(y)[3:137].rstrip() for y in range(9, 26)]

    def first_detail(self):
        return self.line(28)[3:137].rstrip()

    def ask(self, text, existing=""):
        self.h.typed("\x7f" * len(existing) + text + "\r", idle=0.9)

    def set_filters(self, vals):
        """F, then the six questions; vals is from to event account user text."""
        self.h.typed("f", idle=1.2)
        for i, v in enumerate(vals):
            self.ask(v, self.flt[i])
        self.flt = list(vals)
        self.h.s.settle(1.2)

    def end(self):
        self.h.end()

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def want_rows(lines):
    """The 17 rows the list shows with the cursor on the last of the lines given."""
    last = lines[-17:]
    return [row_text(ln) for ln in last] + [""] * (17 - len(last))


def want_filter(f):
    return [ln for ln in file_lines() if passes(ln, f)]


def flt_dict(vals):
    return dict(zip(["from", "to", "event", "account", "user", "text"], vals))


# ------------------------------------------------------------------------------------------------------------------------------- the sections

def section_a0():
    say("\n--- A0: an ordinary account")
    out = g.plain(ACC, ["tool.audit"])
    T = norm(" ".join(out))
    arow("A0a", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)", "Audit trail" not in T and "The line under the cursor" not in T and len(out) > 0, T[:300])
    out = g.plain(ACC, ["BASIC bp zzaw", "RUN bp zzaw"])
    wrote = has(out, r"^ZZAW written$")
    out = g.plain(ACC, ["ztaud"])
    T = norm(" ".join(out))
    arow("A0b", "a VOC entry an ordinary account made for the program gets the page's own refusal (message 11800) and no page; the entry was written, so the refusal is not 'not a command'",
         wrote and "is for the administrator only" in T and "Audit trail" not in T and "The line under the cursor" not in T, repr((wrote, T[:300])))
    out = g.plain(ACC, ["BASIC bp zzar"])
    compiled = has(out, r"^Compiled 1 program\(s\) with no errors")
    if compiled:
        run = g.plain(ACC, ["RUN bp zzar"])
        T = norm(" ".join(run))
        ok = "ZZAR size=[] err=[" in T and "administrator" in T
    else:
        T = norm(" ".join(out))
        ok = len(out) > 0 and "Compiled 1 program(s) with no errors" not in T
    arow("A0c", "$audit_read in an ordinary account's program gives no size: refused to compile, or run with the administrator-only message and no data (the null case: some output)", ok, T[:300])


def section_a1():
    say("\n--- A1: the page opens")
    put_fixture()
    p = Page()
    T = p.text()
    if "The line under the cursor" not in T:
        dump(p.h)
        bail("tool.audit never drew its page, so no row below can be believed")
    lines = file_lines()
    starts = [ln for ln in lines if ln.endswith(" tool start app=tool.audit")]
    arow("A1a", "opening the page wrote one audit line, 'tool start app=tool.audit', after the fixture", len(starts) == 1 and lines[-1].endswith("tool start app=tool.audit"), repr(lines[-2:]))
    top = p.top()
    size = os.path.getsize(audit_path())
    arow("A1b", "the top box names the file, its size in bytes as the disk gives it, 200 lines loaded, and that older lines remain",
         "File: audit (%d bytes)" % size in top and p.loaded() == 200 and "Older lines: more in the file" in top and "Follow: off" in top, repr(top[:260]))
    got = p.rows()
    want = want_rows(lines)
    arow("A1c", "the 17 rows are the file's last 17 lines, as time, user, event words and pairs (a Python reader parses the same bytes)", got == want,
         repr([(a, b) for a, b in zip(got, want) if a != b][:2]))
    detail = p.first_detail()
    arow("A1d", "the box at the foot shows the line under the cursor (the newest): its first row is the start of that line", detail == lines[-1][:134].rstrip(), repr((detail, lines[-1][:134])))
    return p


def section_a2(p):
    say("\n--- A2: back to the start of the file")
    lines = file_lines()
    n_before = len(hold_records())
    for _ in range(14):
        p.key("pgup", 0.5)
        for _ in range(60):
            if p.loaded() == len(lines) or "start of the file" in st(p.h):
                break
            p.key("pgup", 0.4)
        if p.loaded() == len(lines):
            break
    arow("A2a", "going back loads the whole file: the count is the number of lines the file has (%d)" % len(lines), p.loaded() == len(lines), "loaded %s, file %d" % (p.loaded(), len(lines)))
    p.key("home", 0.6)
    arow("A2b", "Home puts the cursor on the first line: the first row is the file's first line", p.rows()[0] == row_text(lines[0]) and p.first_detail() == lines[0][:134].rstrip(), repr((p.rows()[0], row_text(lines[0]))))
    p.key("x", 1.2)
    recs = hold_records()
    new = [r for r in recs if r not in recs[:0]][-1] if len(recs) > n_before else None
    saved = None
    if new:
        saved = [ln.rstrip("\r") for ln in open(os.path.join(sh.SYS, "$hold", new), "rb").read().decode("latin-1").split("\n")]
        while saved and saved[-1] == "":
            saved.pop()
    arow("A2c", "X saves what is loaded: the record holds the file's lines, all of them, in order, the 2,000-character line and the mark-range byte (as ?) included",
         saved == lines, "record %s: %s lines, file %d; first difference %s" % (new, len(saved) if saved else None, len(lines),
                                                                               next(((i, saved[i][:60], lines[i][:60]) for i in range(min(len(saved), len(lines))) if saved[i] != lines[i]), None) if saved else None))
    arow("A2d", "the page says how many it saved and where", ("%d lines saved as record" % len(lines)) in st(p.h), st(p.h))
    return new


def section_a3(p):
    say("\n--- A3: the filters")
    p.key("end", 1.0)

    def case(rid, label, vals, expect_nonempty=True):
        f = flt_dict(vals)
        want = want_filter(f)
        p.set_filters(vals)
        n = p.loaded()
        got = p.rows()
        ok = n == min(len(want), 200) and got == want_rows(want[-200:] if len(want) > 200 else want) and (len(want) > 0 or not expect_nonempty)
        arow(rid, "%s: %d line(s) pass and the page loads %d, its rows equal the Python reader's last ones" % (label, len(want), min(len(want), 200)), ok,
             "page %s, want %d; first difference %s" % (n, len(want), next(((a, b) for a, b in zip(got, want_rows(want[-200:])) if a != b), None)))
        return want

    case("A3a", "event modify.account", ["", "", "modify.account", "", "", ""])
    w = case("A3b", "account fred without regard to case (the file has account=Fred too)", ["", "", "", "fred", "", ""])
    arow("A3b2", "the upper case account=Fred line is among those that pass", any("account=Fred " in ln for ln in w) or any(ln.endswith("account=Fred") for ln in w) or any("account=Fred" in ln for ln in w), "")
    case("A3c", "user sdsys (a line passes by user= or by sudo=)", ["", "", "", "", "sdsys", ""])
    case("A3d", "text 'gate was off' (a value with spaces)", ["", "", "", "", "", "gate was off"])
    case("A3e", "from 2026-10-22 12 to 2026-10-22 18 (a time stamp by prefix)", ["2026-10-22 12", "2026-10-22 18", "", "", "", ""])
    case("A3f", "event api refused and account zzhd and user zzhd together", ["", "", "api refused", "zzhd", "zzhd", ""], expect_nonempty=False)
    before = list(p.flt)
    p.h.typed("f", idle=1.2)
    p.ask("2026-10-01", before[0])
    p.ask("", before[1])
    p.h.key("esc", idle=1.2)
    arow("A3g", "Esc at the third question leaves every filter as it was (the first two answers are not kept)", p.loaded() is not None and "From: 2026-10-01" not in p.top(), p.top()[:200])
    p.h.typed("f", idle=1.2)
    p.ask("abc", before[0])
    arow("A3h", "a time with letters in it is refused in words and the filters stay", "a time looks like 2026-10-25" in st(p.h), st(p.h))
    p.h.key("esc", idle=0.8)
    p.key("c", 1.5)
    top = p.top()
    arow("A3i", "C clears the filters: all six say any, and the newest 200 are loaded again", top.count(": any") + top.count("To: any") >= 6 and p.loaded() == 200 and p.rows() == want_rows(file_lines()), top[:260])
    p.flt = ["", "", "", "", "", ""]


def section_a4(p):
    say("\n--- A4: go to a time")
    lines = file_lines()
    target = "2026-10-21 09:30"
    first = next(ln for ln in lines if ln[:len(target)] >= target)
    p.h.typed("d", idle=1.2)
    p.ask(target)
    arow("A4a", "D goes to the first line at or after 2026-10-21 09:30: the line under the cursor is the one the Python reader finds (older lines had to be loaded)", p.first_detail() == first[:134].rstrip() and p.loaded() > 200,
         repr((p.first_detail(), first[:100], p.loaded())))
    p.h.typed("d", idle=1.2)
    p.ask("2027-01-01")
    arow("A4b", "a time after the last line is answered in words, and the cursor does not move", "no loaded line is at or after 2027-01-01" in st(p.h) and p.first_detail() == first[:134].rstrip(), st(p.h))


def section_a5(p):
    say("\n--- A5: a last line with no line feed")
    p.key("c", 1.5)
    base = file_lines()
    whole = [new_line("whole", i) for i in range(3)]
    part = new_line("partial", 99)
    append("\n".join(whole) + "\n" + part[:40])
    p.key("f5", 1.5)
    T = p.text()
    arow("A5a", "F5 shows the three whole lines and not the unfinished one (its text is nowhere on the screen)", "3 new lines" in st(p.h) and "zz.partial" not in T and p.rows()[-1] == row_text(whole[-1]), repr((st(p.h), p.rows()[-2:])))
    p.key("c", 1.5)
    T = p.text()
    arow("A5b", "a fresh read from the end (C) leaves it out too", "zz.partial" not in T and p.rows()[-1] == row_text(whole[-1]) and p.loaded() == 200, repr(p.rows()[-2:]))
    append(part[40:] + "\n")
    p.key("f5", 1.5)
    arow("A5c", "when the line is finished F5 shows it, once", "1 new line" in st(p.h) and p.rows()[-1] == row_text(part) and p.text().count("zz.partial") >= 1, repr((st(p.h), p.rows()[-1][:80])))
    p.key("l", 1.0)
    more = [new_line("follow", 200 + i) for i in range(2)]
    append("\n".join(more) + "\n")
    time.sleep(4.5)
    p.h.s.settle(1.0)
    arow("A5d", "L follows the file: two lines written since appear within a few seconds with nothing pressed, the cursor on the newest, and the box says Follow: on",
         p.rows()[-1] == row_text(more[-1]) and p.rows()[-2] == row_text(more[-2]) and "Follow: on" in p.top() and p.first_detail() == more[-1][:134].rstrip(), repr((p.rows()[-2:], p.top()[:120])))
    p.key("l", 1.0)
    late = new_line("late", 300)
    append(late + "\n")
    time.sleep(4.5)
    p.h.s.settle(1.0)
    arow("A5e", "L again stops following: a line written now is not shown until F5", "zz.late" not in p.text() and "Follow: off" in p.top(), repr(p.rows()[-1][:80]))
    p.key("f5", 1.5)
    arow("A5f", "... and F5 shows it", p.rows()[-1] == row_text(late), repr(p.rows()[-1][:80]))


def section_a6(p):
    say("\n--- A6: another audit file")
    p.key("o", 2.0)
    top = p.top()
    rl = file_lines("audit.20261001-120000")
    arow("A6a", "O shows the rotated file: its name, its size from the disk, its 40 lines, and none of the live file's", "File: audit.20261001-120000 (%d bytes)" % os.path.getsize(audit_path("audit.20261001-120000")) in top
         and p.loaded() == 40 and p.rows()[-1] == row_text(rl[-1]) and "Older lines: none" in top, repr(top[:260]))
    p.key("o", 2.0)
    arow("A6b", "O again is the live file: the two decoys (audit.junk, audit.20261001-12000x) are not audit files and are not offered", "File: audit (" in p.top() and "audit.junk" not in p.text(), p.top()[:160])


def section_a7(p, saved_record):
    say("\n--- A7: saving the lines shown")
    n0 = len(hold_records())
    lines_before = file_lines()
    p.key("c", 1.5)
    loaded = p.loaded()
    p.key("x", 1.5)
    recs = hold_records()
    new = [r for r in recs if r != saved_record][-1] if len(recs) > n0 else None
    saved = None
    if new:
        saved = open(os.path.join(sh.SYS, "$hold", new), "rb").read().decode("latin-1").split("\n")
        while saved and saved[-1] == "":
            saved.pop()
    want = lines_before[-loaded:]                  # the file as it was when X was pressed: the save adds its own audit line after the lines it holds
    arow("A7a", "X saves the newest %s lines the page holds, equal to the file's last ones" % loaded, saved == want, "record %s %s lines vs %s" % (new, len(saved) if saved else None, len(want)))
    audit = file_lines()
    mine = [ln for ln in audit if " tool export app=tool.audit " in ln]
    arow("A7b", "each save wrote its own audit line: 'tool export app=tool.audit lines=N record=ID'", len(mine) >= 2 and re.search(r"tool export app=tool\.audit lines=%d record=%s$" % (loaded, re.escape(new or "?")), mine[-1]) is not None, repr(mine[-2:]))


def section_a8(p):
    say("\n--- A8: the mouse, F1, a small window, an input that ends, a file that is emptied")
    p.key("c", 1.5)
    want = file_lines()
    p.h.click(20, 12)
    arow("A8a", "a click on the fourth row puts the cursor there: the box at the foot shows that row's line (its first 60 characters: a line of 600 bytes wraps at a word, not at 134)", p.first_detail()[:60] == want[-14][:60], repr((p.first_detail()[:60], want[-14][:60])))
    p.h.click(135, 2)
    T = norm(p.text())
    arow("A8b", "a click on the [?] reaches the help box ($tk_help says help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("A8c", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    open(audit_path(), "wb").close()
    p.key("f5", 1.5)
    arow("A8d", "an emptied file (a rotation) is read again from its end: nothing to show, said so, and the foot box says there is no line", "rotated" in st(p.h) and p.loaded() == 0 and "There is no line to show" in p.text(), repr((st(p.h), p.loaded())))
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.audit\r", idle=3.0)
    T = h.text()
    arow("A8e", "a window under 140 by 43 gets no page (the toolkit's one size check)", "The line under the cursor" not in T and "Audit trail" not in T, T[-300:])
    h.end()
    put_fixture()
    env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(sh.BOX, "a8-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.audit\n")
    pr.stdin.flush()
    time.sleep(4)
    pr.stdin.close()
    try:
        pr.wait(timeout=20)
        ended = True
    except subprocess.TimeoutExpired:
        ended = False
        pr.kill()
        pr.wait()
    fh.close()
    with open(os.path.join(sh.BOX, "a8-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("A8f", "a page whose input ends ends by itself within 20 seconds; the output shows it did start (the null case)", ended and "The line under the cursor" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-audit.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    global MUTANT
    MUTANT = mutant
    last = MUTANTS[mutant][3] if mutant else "A8"
    order = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    p = None
    try:
        sh.setup("sandbox-tool-audit.py")
        setup_pages()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-audit: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_a0()
        p = section_a1()
        saved = section_a2(p) if run("A2") else None
        if run("A3"):
            section_a3(p)
        if run("A4"):
            section_a4(p)
        if run("A5"):
            section_a5(p)
        if mutant is None:
            section_a6(p)
            section_a7(p, saved)
            section_a8(p)
        else:
            p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-audit: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"A\d+", i).group(0) for i in FAILED_IDS if re.match(r"A\d+", i)})
        ok = want == got
        say("sandbox-tool-audit: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
