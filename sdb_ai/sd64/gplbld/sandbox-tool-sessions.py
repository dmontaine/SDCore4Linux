#!/usr/bin/env python3
#
# sandbox-tool-sessions.py - the sessions and locks page, TOOL.SESSIONS, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A4; plan .claude/plan-fullscreen-toolkit.md
# section 5).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-sessions.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN, the person who runs this suite) opens TOOL.SESSIONS on a 140 by 43 terminal.  Other sessions are REAL ones, piped sessions
# kept open that run a program (zzslk, compiled into the sandbox's SDSYS bp file) which takes locks and then sleeps until it is logged out: A holds two record locks, B waits for one of
# A's (a WAIT row), C holds three record locks whose ids are a safe word, a word UNLOCK reads as a keyword (all) and an id with a space, D holds a file lock.  The page runs the REAL
# logout, unlock and inhibit.login verbs.
#
# THE INSTRUMENT.  Every outcome is read from SD, not from the page: LIST.READU for what is locked, LISTU for who is signed on, the process itself (is it alive), the file
# login.inhibit, a new ordinary session asking to sign in, and the audit file.  A page that drew a row, or said it ran a command, is not taken to have done it.
#
#   S0   an ordinary account has no tool.sessions
#   S1   the page opens: one audit line; the boxes; the headings; the sessions that are signed on (read from LISTU and LIST.READU) and the locks (from LIST.READU), both in the lists
#   S2   the explanation under the row: a waiting row is not a lock and U refuses it; a record lock shows its command; a file lock shows 'filelock'
#   S3   the session the page runs in is not offered for logout
#   S4   logout: Esc runs nothing; a wrong number runs nothing; the number runs it - the process ends, the locks are released and B gets the lock it was waiting for
#   S5   a refresh keeps the cursor on the same user, not the same row, when a lower numbered session signs on above it; the list is read again without a key
#   S6   unlock: Esc runs nothing; Run releases ONE lock and the holder stays signed on; an id that is a keyword or has a space is refused before the box; a file lock is released
#   S7   inhibit.login: on and off through the box; the file; a new ordinary session is refused while it is on; the audit lines
#   S8   the mouse, F5, F1, Tab; a window under 140 by 43 gets no page; the page ends when its input ends
# NOT HELD: a lock whose holder has no session (a sandbox cannot make one), a real install, the help text itself (sandbox-docs.py).
import getpass
import importlib.util
import os
import re
import shutil
import signal
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


sh = _load("sandbox_home_for_toolsessions", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
LIVES = []
MUTANT = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

HOLDER = """   role = upcase(field(@sentence, ' ', 4))
   open 'zzslk' to f else
      crt 'ZZSLK no file'
      stop
   end
   open 'zzslk2' to f2 else
      crt 'ZZSLK no file2'
      stop
   end
   begin case
      case role = 'A'
         readu r from f, 'rec1' else null
         readu r from f, 'rec9' else null
      case role = 'B'
         readu r from f, 'rec1' else null
      case role = 'C'
         readu r from f, 'rec3' else null
         readu r from f, 'all' else null
         readu r from f, 'rec x' else null
      case role = 'D'
         filelock f2
      case role = 'E'
         readu r from f, 'rec5' else null
   end case
   crt 'ZZSLK holding ' : role
   loop
      sleep 1
   repeat
end
"""

MUTANTS = {
    # name: (old text of the sandbox's tool_sessions, new text, the row ids that must fail and no others, the last section run)
    "logout-own": ("   if uid = @userno then\n      msg = 'that is the session you are in; Ctrl-Q leaves the page'\n      return\n   end\n", "", ["S3"], "S3"),
    "no-typed-number": ("   typed = uid\n", "   typed = ''\n", ["S4"], "S4"),
    "cursor-by-row": ("      for i = 1 to ns\n         if udata<i, 1> = sel.u then", "      for i = 1 to 0\n         if udata<i, 1> = sel.u then", ["S5"], "S5"),
    "unlock-unsafe-id": ("         word = uid2\n         gosub plain.word\n         if plain then", "         word = uid2\n         plain = 1\n         if plain then", ["S6"], "S6"),
}


def arow(rid, name, ok, detail=""):
    """A row with an id (S3 ...): the mutant mode compares the ids that failed with the ids that had to."""
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def box():
    return sh.BOX


def st(h):
    return h.line(40)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def audit_off():
    path = os.path.join(sh.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    if off is None:
        return None
    try:
        with open(os.path.join(sh.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


class Live:
    """A session on a pipe kept open, running a program that takes locks and sleeps until it is logged out."""

    def __init__(self, role):
        self.role = role
        env = dict(os.environ, SD_CONFIG=os.path.join(box(), "sd.conf"), SDTEST_ADMIN="1")
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_TTY", None)
        self.out = os.path.join(box(), "live-%s-%d.out" % (role, len(LIVES)))
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\nRUN bp zzslk %s\n" % role)
        self.p.stdin.flush()
        say("    > live %s: pid %d, RUN bp zzslk %s" % (role, self.p.pid, role))
        LIVES.append(self)

    def text(self):
        self.fh.flush()
        with open(self.out, errors="replace") as f:
            return ANSI.sub("", f.read())

    def alive(self):
        return self.p.poll() is None

    def wait(self, seconds):
        try:
            self.p.wait(timeout=seconds)
            return True
        except subprocess.TimeoutExpired:
            return False

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def lock_table():
    """[(user, file, path, type, id)] from LIST.READU WAIT, asked of SD by a separate administrator session."""
    out = g.adm(["LIST.READU WAIT"])
    rows = []
    for ln in out:
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(FX|SX|RU|RL|WAIT)\b\s*(.*)$", ln)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(3), m.group(4), m.group(5).strip().lower()))     # the lock table holds record ids in upper case
    return rows


def users_now():
    """{user: pid} from LISTU, asked of SD by a separate administrator session."""
    out = g.adm(["LISTU"])
    res = {}
    for ln in out:
        m = re.match(r"^\*?\s*(\d+)\s+(\d+)\s", ln)
        if m:
            res[int(m.group(1))] = int(m.group(2))
    return res


def until(fn, seconds, every=1.0):
    end = time.time() + seconds
    while True:
        v = fn()
        if v:
            return v
        if time.time() > end:
            return v
        time.sleep(every)


def uid_of(role, locks=None):
    """The user number of a role, from the lock table: A holds rec1 (RU), B waits for rec1, C holds rec3, D holds a file lock."""
    locks = locks if locks is not None else lock_table()
    for u, f, p, t, i in locks:
        if role == "A" and t == "RU" and i == "rec1":
            return u
        if role == "B" and t == "WAIT" and i == "rec1":
            return u
        if role == "C" and t == "RU" and i == "rec3":
            return u
        if role == "D" and t == "FX":
            return u
    return None


def setup_sessions():
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_sessions"), os.path.join(sh.SYS, "gpl.bp", "tool_sessions"))
    out = g.adm(["BASIC gpl.bp tool_sessions"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_sessions did not compile in the sandbox:\n" + "\n".join(out[-8:]))
    g.put(os.path.join(sh.SYS, "bp", "zzslk"), HOLDER)
    out = g.adm(["CREATE.FILE zzslk", "CREATE.FILE zzslk2", "BASIC bp zzslk"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the holder program did not compile:\n" + "\n".join(out[-8:]))


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_sessions")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_sessions"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    """A session on tool.sessions on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.sessions\r", idle=3.5)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.6):
        if len(name) == 1:                         # a letter is typed; the harness's key table has the named keys only
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def typed(self, s, idle=0.9):
        self.h.typed(s, idle=idle)

    def idle(self, seconds):
        self.h.s.settle(seconds)

    def sessions(self):
        out = {}
        for n in range(3, 14):
            ln = self.line(n)
            u = ln[5:10].strip()
            if u.isdigit():
                out[int(u)] = dict(mark=ln[3:5].strip(), pid=ln[12:20].strip(), kind=ln[35:43].strip(), luser=ln[43:58].strip(), acct=ln[58:78].strip(), state=ln[104:].strip().rstrip("|").strip(), row=n)
        return out

    def locks(self):
        out = []
        for n in range(18, 28):
            ln = self.line(n)
            u = ln[3:8].strip()
            if u.isdigit():
                out.append(dict(uid=int(u), file=ln[10:15].strip(), path=ln[17:47].strip(), type=ln[48:53].strip(), id=ln[53:85].strip().lower(), since=ln[85:98].strip(), holder=ln[98:].strip().rstrip("|").strip(), row=n))
        return out

    def detail(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(31, 38)))

    def pane(self):
        m = re.match(r"\[(\w+)\]", st(self.h).strip())
        return m.group(1) if m else ""

    def focus(self, pane):
        if self.pane() != pane:
            self.key("tab", 0.8)

    def to_session(self, uid):
        """Cursor to the session of this user number; the list is read every 3 seconds, so a session that signed on a moment ago may take that long to show."""
        for _ in range(8):
            if uid in self.sessions():
                break
            self.idle(1.5)
        self.focus("Sessions")
        self.key("home", 0.5)
        rows = sorted(self.sessions())
        for _ in range(rows.index(uid)):
            self.key("down", 0.35)

    def to_lock(self, pred):
        for _ in range(8):
            if any(pred(r) for r in self.locks()):
                break
            self.idle(1.5)
        self.focus("Locks")
        self.key("home", 0.5)
        rows = self.locks()
        idx = next(i for i, r in enumerate(rows) if pred(r))
        for _ in range(idx):
            self.key("down", 0.35)
        return rows[idx]

    def end(self):
        self.h.end()

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def section_s0():
    say("\n--- S0: an ordinary account has no tool.sessions")
    out = g.plain("zzhd", ["tool.sessions"])
    T = norm(" ".join(out))
    arow("S0", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)",
         "The row under the cursor" not in T and "Pid" not in T and len(out) > 0, T[:300])


def start_holders():
    say("\n--- the holders")
    a = Live("A")
    until(lambda: any(t == "RU" and i == "rec1" for _u, _f, _p, t, i in lock_table()), 25)
    b = Live("B")
    until(lambda: any(t == "WAIT" and i == "rec1" for _u, _f, _p, t, i in lock_table()), 25)
    locks = lock_table()
    ua, ub = uid_of("A", locks), uid_of("B", locks)
    say("    LIST.READU: %s" % (locks,))
    if ua is None or ub is None:
        bail("the holders A and B did not take their locks (A %s, B %s), so no row below can be believed" % (ua, ub))
    return a, b, ua, ub


def section_s1(a, b, ua, ub):
    say("\n--- S1: opening the page")
    a0 = audit_off()
    p = Page()
    T = p.text()
    if "The row under the cursor" not in T:
        dump(p.h)
        bail("tool.sessions never drew its page, so no row below can be believed")
    new = audit_new(a0) or ""
    arow("S1a", "opening the page writes one audit line, 'tool start app=tool.sessions', and no other", len(re.findall(r"tool start app=tool\.sessions$", new, re.M)) == 1 and "tool run" not in new, repr(new[-200:]))
    arow("S1b", "the three boxes and a [?] at the end of the first box", all(w in T for w in ("Sessions", "Locks", "The row under the cursor")) and "[?]" in p.line(2), T[:300])
    head = p.line(2)
    arow("S1c", "the session headings", all(w in head for w in ("User", "Pid", "Logged in", "Kind", "Login user", "Account", "Where from", "State")), head)
    hl = p.line(17)
    arow("S1d", "the lock headings", all(w in hl for w in ("User", "File", "Path", "Type", "Record id", "Since", "Holder")), hl)
    S = p.sessions()
    mine = [u for u, r in S.items() if r["mark"] == "*"]
    arow("S1e", "the session the page runs in is marked with a star and says 'you'; it is a user session in the account sdsys of the login user",
         len(mine) == 1 and "you" in S[mine[0]]["state"] and S[mine[0]]["kind"] == "user" and S[mine[0]]["acct"] == "sdsys" and S[mine[0]]["luser"] == ME, repr(S))
    now = users_now()
    arow("S1f", "A and B are listed with their kind and login user, and the user numbers and process ids the page shows are the ones LISTU gives",
         ua in S and ub in S and S[ua]["kind"] == "user" and S[ub]["luser"] == ME and all(int(S[u]["pid"]) == now.get(u) for u in (ua, ub)), repr((S, now)))
    L = p.locks()
    types = sorted((r["uid"], r["type"], r["id"]) for r in L)
    want = sorted([(ua, "RU", "rec1"), (ua, "RU", "rec9"), (ub, "WAIT", "rec1")])
    arow("S1g", "the lock list has A's two record locks and B's waiting row, each with its file number and a holder 'signed on'", types == want and all(r["holder"] == "signed on" and r["file"].isdigit() for r in L), repr(L))
    arow("S1h", "the counts line names the number of sessions and says logins are allowed; the lock limit line is there", re.search(r"\d+ sessions: \d+ users, \d+ phantoms, \d+ API\.", p.line(14)) is not None and "Logins are allowed" in p.line(14)
         and "Record lock limit" in p.line(28), repr((p.line(14)[:120], p.line(28)[:100])))
    return p


def section_s2(p, ua, ub):
    say("\n--- S2: the row under the cursor")
    r = p.to_lock(lambda r: r["type"] == "WAIT")
    D = p.detail()
    arow("S2a", "a waiting row is explained as waiting, and not as a lock", "is WAITING for a lock on record rec1" in D.replace("REC1", "rec1") and "A waiting row is not a lock" in D, D[:300])
    a0 = audit_off()
    p.key("u", 0.9)
    arow("S2b", "U on a waiting row says so, opens no box and runs nothing", "A waiting row is not a lock" in st(p.h) and "taken out of the lock table" not in norm(p.text()) and "tool run" not in (audit_new(a0) or ""), repr((st(p.h), audit_new(a0))))
    p.to_lock(lambda r: r["type"] == "RU" and r["id"] == "rec1")
    D = p.detail()
    fid = next(x["file"] for x in p.locks() if x["id"] == "rec1" and x["type"] == "RU")
    arow("S2c", "a record lock is explained with the holder, the record, the file and the exact command", ("User %d holds a read and update lock on record rec1 in file %s" % (ua, fid)) in D.replace("REC1", "rec1") and ("The command is: unlock file %s user %d rec1." % (fid, ua)) in D and "The holder is signed on" in D, D[:400])
    p.focus("Sessions")
    p.to_session(ua)
    D = p.detail()
    arow("S2d", "a session is explained: its user number, its process, the account, how many locks it holds, and what L does", ("User %d, process" % ua) in D and "It holds 2 locks" in D and ("The command is: logout %d." % ua) in D, D[:400])


def section_s3(p):
    say("\n--- S3: the session the page runs in")
    S = p.sessions()
    me = next(u for u, r in S.items() if r["mark"] == "*")
    p.to_session(me)
    a0 = audit_off()
    p.key("l", 1.0)
    T = norm(p.text())
    arow("S3", "L on the session the page runs in says so, opens no box, and runs nothing",
         "that is the session you are in" in st(p.h) and "Type the number" not in T and "tool run" not in (audit_new(a0) or ""), repr((st(p.h), T[-200:])))


def section_s4(p, a, b, ua, ub):
    say("\n--- S4: logout")
    p.to_session(ua)
    a0 = audit_off()
    p.key("l", 1.5)
    T = norm(p.text())
    arow("S4a", "L shows the command, what it does and that the number is typed again", ("logout %d" % ua) in T and "Type the number %d" % ua in T and "the entry is cleared instead" in T, T[-700:])
    p.key("esc", 1.2)
    arow("S4b", "Esc runs nothing: the session is alive and the audit trail has no run line", "nothing was run" in st(p.h) and a.alive() and pid_alive(a.p.pid) and "tool run" not in (audit_new(a0) or ""), repr((st(p.h), a.alive())))
    p.typed("l", idle=1.3)
    p.typed("r", idle=1.3)
    p.typed("999\r", idle=1.8)
    arow("S4c", "a number that is not the session's runs nothing", a.alive() and pid_alive(a.p.pid) and "tool run" not in (audit_new(a0) or "") and any(r[0] == ua for r in lock_table()), repr((st(p.h), audit_new(a0))))
    if MUTANT == "no-typed-number":                 # the mutant ran the logout at the Run above: the rows after this one depend on A being alive
        return
    p.typed("l", idle=1.3)
    p.typed("r", idle=1.3)
    p.typed("%d\r" % ua, idle=2.5)
    new = audit_new(a0) or ""
    arow("S4d", "the number typed: the audit trail has the page's line with the command and its status 0", re.search(r"tool run app=tool\.sessions command=logout %d status=0$" % ua, new, re.M) is not None, repr(new[-300:]))
    ended = a.wait(20)
    p.idle(0.8)
    arow("S4e", "the session A is gone: its process ended, LISTU does not list it, and the page says it asked", ended and not pid_alive(a.p.pid) and ua not in users_now() and ("Force logout initiated for user %d" % ua) in st(p.h), repr((ended, st(p.h))))
    p.idle(4.0)
    S = p.sessions()
    L = p.locks()
    rec1 = [r for r in L if r["id"] == "rec1"]
    arow("S4f", "A's locks were released and B, which was waiting, has the lock now: the page (read again without a key) shows no WAIT row, no lock of A's, and B holding rec1; LIST.READU agrees",
         ua not in S and ub in S and not any(r["uid"] == ua for r in L) and not any(r["type"] == "WAIT" for r in L) and [(r["uid"], r["type"]) for r in rec1] == [(ub, "RU")]
         and (ub, "RU", "rec1") in [(u, t, i) for u, _f, _p, t, i in lock_table()] and not any(u == ua for u, *_ in lock_table()), repr((sorted(S), L, lock_table())))


def section_s5(p, b, ub):
    say("\n--- S5: a refresh keeps the cursor on the same user")
    e = Live("D")
    until(lambda: any(t == "FX" for _u, _f, _p, t, _i in lock_table()), 25)
    ud = uid_of("D")
    say("    D is user %s; B is user %s" % (ud, ub))
    p.idle(4.0)
    me = next((u for u, r in p.sessions().items() if r["mark"] == "*"), None)
    p.to_session(me)
    D0 = p.detail()
    S0 = sorted(p.sessions())
    arow("S5a", "the sessions are B, this session and D, in that order, and the cursor is on this session (the middle one)", S0 == sorted([ub, me, ud]) and S0[1] == me and ("User %d, process" % me) in D0, repr((S0, D0[:120])))
    out = g.adm(["LOGOUT %d" % ub])
    gone = b.wait(20)
    p.idle(4.5)
    S = p.sessions()
    D1 = p.detail()
    arow("S5b", "B, the session ABOVE the cursor, was logged out from outside: the page read the list again by itself, B is gone, and the cursor is still on this session (the box below still explains user %d), "
         "not on the row number it had, which now holds D" % me, gone and ub not in S and me in S and ud in S and ("User %d, process" % me) in D1, repr((sorted(S), D1[:160], out[-2:])))
    return e, ud


def section_s6(p, c, uc, d, ud):
    say("\n--- S6: unlock")
    a0 = audit_off()
    r = p.to_lock(lambda r: r["uid"] == uc and r["id"] == "rec3")
    D = p.detail()
    cmd = "unlock file %s user %d rec3" % (r["file"], uc)
    arow("S6a", "the command for a record lock is shown under the row", ("The command is: %s." % cmd) in D, D[:300])
    p.key("u", 1.5)
    T = norm(p.text())
    arow("S6b", "U shows the command and what it does", cmd in T and "is taken out of the lock table now" in T and "The holder is signed on and is not told" in T, T[-600:])
    p.key("esc", 1.2)
    arow("S6c", "Esc runs nothing: the lock is still in the table and the audit trail has no run line", "nothing was run" in st(p.h) and (uc, "RU", "rec3") in [(u, t, i) for u, _f, _p, t, i in lock_table()] and "tool run" not in (audit_new(a0) or ""), repr((st(p.h), audit_new(a0))))
    p.typed("u", idle=1.3)
    p.typed("r", idle=2.5)
    new = audit_new(a0) or ""
    now = [(u, t, i) for u, _f, _p, t, i in lock_table()]
    arow("S6d", "Run: the lock is gone from LIST.READU, C's other locks and its session are not, and the audit trail has the page's line with the command",
         (uc, "RU", "rec3") not in now and (uc, "RU", "all") in now and c.alive() and uc in users_now() and re.search(r"tool run app=tool\.sessions command=%s status=0$" % re.escape(cmd), new, re.M) is not None, repr((now, new[-300:])))
    p.idle(3.5)
    arow("S6e", "the page no longer lists the released lock and still lists C's others", not any(x["uid"] == uc and x["id"] == "rec3" for x in p.locks()) and any(x["uid"] == uc and x["id"] == "all" for x in p.locks()), repr(p.locks()))
    for lock_id, why in (("all", "a record id that is a word UNLOCK reads as a keyword"), ("rec x", "a record id with a space")):
        a1 = audit_off()
        p.to_lock(lambda r, i=lock_id: r["uid"] == uc and r["id"] == i)
        p.key("u", 1.2)
        T = norm(p.text())
        arow("S6f" if lock_id == "all" else "S6g", "U on %s is refused in words before any box opens, and runs nothing" % why,
             "will not put in a command" in st(p.h) + " " + p.detail() and "taken out of the lock table" not in T and "tool run" not in (audit_new(a1) or "") and (uc, "RU", lock_id) in [(u, t, i) for u, _f, _p, t, i in lock_table()], repr((st(p.h), p.detail()[:300])))
        p.key("esc", 1.0)                          # a page without the refusal opens a box here (the mutant); close it so that the rows after this one still read the page
    a2 = audit_off()
    p.to_lock(lambda r: r["type"] == "FX")
    D = p.detail()
    fx = next(x for x in p.locks() if x["type"] == "FX")
    fcmd = "unlock file %s user %d filelock" % (fx["file"], ud)
    p.key("u", 1.3)
    T = norm(p.text())
    p.typed("r", idle=2.5)
    new = audit_new(a2) or ""
    arow("S6h", "a file lock: the command ends in filelock; Run releases it (LIST.READU has no FX) and D is still signed on",
         fcmd in T and ud in users_now() and not any(t == "FX" for _u, _f, _p, t, _i in lock_table()) and d.alive() and re.search(r"command=%s status=0$" % re.escape(fcmd), new, re.M) is not None, repr((T[-300:], lock_table(), new[-200:])))


def section_s10(p):
    say("\n--- S10: a session whose process is gone (killed from outside SD)")
    e = Live("E")
    until(lambda: any(i == "rec5" for _u, _f, _p, _t, i in lock_table()), 25)
    ue = next((u for u, _f, _p, _t, i in lock_table() if i == "rec5"), None)
    if ue is None:
        bail("holder E did not take its lock")
    os.kill(e.p.pid, signal.SIGKILL)
    e.wait(5)
    time.sleep(1.0)
    now = lock_table()
    arow("S10a", "the killed session keeps its entry and its lock: LISTU still lists user %s and LIST.READU still shows rec5 (SD does not notice by itself; the page cannot either)" % ue,
         not pid_alive(e.p.pid) and ue in users_now() and any(u == ue and i == "rec5" for u, _f, _p, _t, i in now), repr((users_now(), now)))
    p.idle(4.0)
    S = p.sessions()
    arow("S10b", "the page lists it like any other session", ue in S and S[ue]["kind"] == "user", repr(sorted(S)))
    a0 = audit_off()
    p.to_session(ue)
    p.key("l", 1.5)
    T = norm(p.text())
    arow("S10c", "L offers the logout of a session whose process is gone, and the box says the entry is cleared instead", ("logout %d" % ue) in T and "the entry is cleared instead" in T, T[-500:])
    p.typed("r", idle=1.3)
    p.typed("%d\r" % ue, idle=2.5)
    new = audit_new(a0) or ""
    arow("S10d", "Run: the verb says it reaped the user because the process was gone (the page shows that line), LISTU no longer lists the user and LIST.READU no longer shows its lock; the page's audit line has the command",
         ("LOGOUT reaped user %d" % ue) in st(p.h) and "process was gone" in st(p.h) and ue not in users_now() and not any(u == ue for u, *_ in lock_table()) and re.search(r"command=logout %d status=0$" % ue, new, re.M) is not None, repr((st(p.h), users_now(), lock_table(), new[-200:])))
    p.idle(3.5)
    arow("S10e", "the page no longer lists the session or its lock", ue not in p.sessions() and not any(x["uid"] == ue for x in p.locks()), repr((sorted(p.sessions()), p.locks())))


def section_s7(p):
    say("\n--- S7: inhibit.login")
    f = os.path.join(sh.SYS, "login.inhibit")
    a0 = audit_off()
    p.focus("Sessions")
    p.key("i", 1.5)
    T = norm(p.text())
    arow("S7a", "I shows inhibit.login on and what it does", "inhibit.login on" in T and "No new session can sign in" in T, T[-500:])
    p.key("esc", 1.2)
    arow("S7b", "Esc runs nothing: no login.inhibit file", not os.path.exists(f) and "nothing was run" in st(p.h) and "tool run" not in (audit_new(a0) or ""), repr((os.path.exists(f), st(p.h))))
    p.typed("i", idle=1.3)
    p.typed("r", idle=2.5)
    new = audit_new(a0) or ""
    out = g.plain("zzhd", ["WHO"])
    arow("S7c", "Run: login.inhibit exists, the page says logins are inhibited, a new ordinary session is refused, and both the page's line and the verb's own are in the audit trail",
         os.path.exists(f) and "Logins are inhibited by" in p.line(14) and has(out, r"(?i)not accepting new sessions|inhibited") and re.search(r"tool run app=tool\.sessions command=inhibit\.login on status=\d+$", new, re.M) is not None
         and re.search(r"^.*inhibit\.login on$", new, re.M) is not None, repr((os.path.exists(f), p.line(14)[:100], out[:3], new[-300:])))
    a1 = audit_off()
    p.key("i", 1.3)
    T = norm(p.text())
    arow("S7d", "I while logins are inhibited offers inhibit.login off", "inhibit.login off" in T and "New sessions may sign in again" in T, T[-500:])
    p.typed("r", idle=2.5)
    out = g.plain("zzhd", ["WHO"])
    arow("S7e", "Run: login.inhibit is gone, the page says logins are allowed and a new ordinary session signs in", not os.path.exists(f) and "Logins are allowed" in p.line(14) and not has(out, r"(?i)not accepting new sessions")
         and re.search(r"command=inhibit\.login off status=\d+$", audit_new(a1) or "", re.M) is not None, repr((os.path.exists(f), p.line(14)[:100], out[:3])))


def section_s8(p):
    say("\n--- S8: the mouse, F5, F1, Tab")
    S = p.sessions()
    rows = sorted(S)
    p.focus("Locks")
    target = rows[0]
    p.h.click(20, S[target]["row"])
    D = p.detail()
    arow("S8a", "a click on a session row puts the cursor there and the focus on the sessions list", p.pane() == "Sessions" and ("User %d, process" % target) in D, repr((p.pane(), D[:120])))
    L = p.locks()
    if L:
        p.h.click(20, L[0]["row"])
        arow("S8b", "a click on a lock row puts the cursor there and the focus on the locks list", p.pane() == "Locks" and ("User %d" % L[0]["uid"]) in p.detail(), repr((p.pane(), p.detail()[:120])))
    p.key("tab", 0.8)
    arow("S8c", "Tab changes the list", p.pane() == "Sessions", p.pane())
    p.key("f5", 1.5)
    arow("S8d", "F5 reads again and says so", "asked the system again" in st(p.h), st(p.h))
    p.h.click(135, 2)
    T = norm(p.text())
    arow("S8e", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("S8f", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    p.key("esc", 1.0)
    p.quit()


def section_s9():
    say("\n--- S9: a small window, and an input that ends")
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.sessions\r", idle=3.0)
    T = h.text()
    arow("S9a", "a window under 140 by 43 gets no page (the toolkit's one size check)", "The row under the cursor" not in T and "Pid" not in T, T[-300:])
    h.end()
    env = dict(os.environ, SD_CONFIG=os.path.join(box(), "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(box(), "s9-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.sessions\n")
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
    with open(os.path.join(box(), "s9-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("S9b", "a page whose input ends (the pipe is closed after 4 seconds) ends by itself within 20 seconds; the output shows it did start (the null case: a program that never began would end too)",
         ended and "The row under the cursor" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


def teardown_live():
    try:
        g.adm(["LOGOUT ALL"])
    except Exception:
        pass
    for lv in LIVES:
        lv.wait(5)
        lv.kill()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-sessions.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    last = MUTANTS[mutant][3] if mutant else "S9"
    global MUTANT
    MUTANT = mutant
    order = ["S3", "S4", "S5", "S6", "S7", "S8", "S9"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    try:
        sh.setup("sandbox-tool-sessions.py")
        setup_sessions()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-sessions: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_s0()
        a, b, ua, ub = start_holders()
        p = section_s1(a, b, ua, ub)
        if mutant is None:
            section_s2(p, ua, ub)
        if run("S3"):
            section_s3(p)
        if run("S4"):
            section_s4(p, a, b, ua, ub)
        if run("S5"):
            d, ud = section_s5(p, b, ub)
        if run("S6"):
            c = Live("C")
            until(lambda: any(t == "RU" and i == "rec3" for _u, _f, _p, t, i in lock_table()), 25)
            uc = uid_of("C")
            if uc is None:
                bail("holder C did not take its locks")
            section_s6(p, c, uc, d, ud)
        if mutant is None:
            section_s10(p)
            section_s7(p)
            section_s8(p)
            section_s9()
        else:
            p.quit()
    finally:
        teardown_live()
        sh.teardown()
    say("\nsandbox-tool-sessions: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"S\d+", i).group(0) for i in FAILED_IDS if re.match(r"S\d+", i)})
        ok = want == got
        say("sandbox-tool-sessions: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
