#!/usr/bin/env python3
#
# sandbox-tool-remote.py - the remote access page, TOOL.REMOTE, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A9; plan .claude/plan-fullscreen-toolkit.md section 5).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-remote.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session opens TOOL.REMOTE on a 140 by 43 terminal.  Two SDNet servers are defined with the REAL set.server (typed pins, so nothing is dialled), and the
# page's delete runs the REAL delete.server.  The judge is SD: LIST.SERVERS, LISTU, REMOTE.API and REMOTE.SSH are run by a separate administrator session and the page's rows are compared
# with what they print; the register is read by a Python reader.
#
# WHAT A SANDBOX CANNOT DO.  Changing a door opens a socket unit and a firewall rule as root, and SET.SERVER's connect step needs a server to dial: no row here shows a door opened or a
# key trusted (those are witness rows on a real install).  What the rows do show: the page's lists are SD's own; every guard refuses before a box; every box is what the page says it is,
# a door turned ON wants OPEN typed and a wrong word runs nothing, Cancel runs nothing; the sentence the page builds is the one the verb receives; the delete really removes one definition.
#
#   R0   an ordinary account has no tool.remote; a VOC entry that points at the program gets the page's own refusal
#   R1   the page opens: one audit line; the doors' first lines are the verbs'; the doors view lists the verbs' words
#   R2   A and S: a bad word is refused before a box; local shows its sentence; on wants OPEN typed (a wrong word runs nothing); Esc runs nothing
#   R3   the routes view: one row for each USER account (a Python reader of the register), the NET gate, and the doors the account's Linux user's REAL groups give (17 Nov 26: none
#        for a user that does not exist; zzme's user is whoever runs this, judged against that user's groups, so the row no longer depends on what the host's user is in)
#   R4   the servers view: the rows are LIST.SERVERS's; X shows 'delete.server', Esc runs nothing, Run removes exactly that definition (LIST.SERVERS afterwards)
#   R5   N: every field is checked and refused in words at the first that is wrong; a good set shows the set.server sentence and says the terminal is given to the verb; Esc defines nothing
#   R6   the connected view: a second session is listed with its account, as LISTU gives; the counts line
#   R7   the TLS view is a view of text and never shows a private key; the mouse, F1, a small window, an input that ends
#   R8   (S.95 stage 1b, S.106; run before R7, which ends the page) REMOTE.SDSYS: not an ordinary account's verb; a bad keyword (recovery and local too) gets the usage; view 6 lists the
#        verb's report; O and F show their boxes, R and L open none, and Esc runs nothing.  NOT HELD: ssh opened or shut for sdsys (sudo; the VM).  ON and OFF are never run here: on a machine
#        where the sandbox user could sudo the helper they would really open or shut ssh for sdsys
#   local (S.267, 18 Nov 26; run before R7) the sdsys view's two fields, Local ssh users and Local API users: each shows the helper's words or, in a sandbox (no root helper),
#        'not read: ' and the verb's first line, without the page failing; Up / Down choose the list X and U act on; U refuses a bad name in 14184's words, shows the add sentence
#        and 14179 / 14180 in a box, and a WRONG name typed again runs nothing; Esc runs nothing; C shows the clear sentence; the keys do nothing on another view.  NOTHING IS
#        RUN: no add, remove or clear (on a machine where the sandbox user could sudo the helper they would really change the lists).  NOT HELD: a real add / remove / clear,
#        a list read, X's pick of real names, the helper's refusal of a real name (the VM witness).
#   --only=NAME[,NAME] (18 Nov 26) runs the build, the fixtures and R1 (which opens the page), then only the sections named: r0 r2 r3 r4 r5 r6 r8 local r7.
# NOT HELD: a door opened or closed, a key trusted, the terminal handed to set.server (the VM), the help text itself (sandbox-docs.py).
import getpass
import grp
import importlib.util
import pwd
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


sh = _load("sandbox_home_for_toolremote", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
LAST_LISTU = []
MUTANT = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ACC = "zzhd"
OTHER = "zzhm"
PIN_A = "ab" * 32
PIN_B = "0123456789abcdef" * 4
WRITER = """   open 'voc' to v else
      crt 'ZZRW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$tool_remote' to v, 'ztrem' on error
      crt 'ZZRW refused ':status()
      stop
   end
   crt 'ZZRW written'
end
"""

MUTANTS = {
    # name: (old text of the sandbox's tool_remote, new text, the row ids that must fail and no others, the last section run)
    "on-needs-no-word": ("      case aw = 'on'\n         typed = 'open'", "      case aw = 'on'\n         typed = ''", ["R2"], "R2"),
    "delete-first-server": ("   d = defs<ci>\n   word = d<1, 1>\n   gosub plain.word", "   d = defs<1>\n   word = d<1, 1>\n   gosub plain.word", ["R4"], "R4"),
    "port-unchecked": ("(s.port + 0) > 65535", "(s.port + 0) > 99999", ["R5"], "R5"),
}

# a user account with its net gate on, one with it off, and a group account, beside the sandbox's fixture accounts
HAND = {
    "zzaa": ("sdu_zzaa", ["no", "no", "no", "no", "no", "no"], ["", "", "yes"]),
    "zzab": ("sdu_zzab", ["no", "no", "no", "no", "no", "no"], ["", "", "no"]),
    "zzgrp": ("sdg_zzgrp", ["no", "no", "no", "no", "no", "no"], ["", "", ""]),
    # 17 Nov 26 (S.62, L4 C4): a user account whose Linux user is the one running this suite, which EXISTS, so R3b always judges one row against real groups
    "zzme": ("sdu_" + getpass.getuser(), ["no", "no", "no", "no", "no", "no"], ["", "", "no"]),
}


def sys_accounts():
    return os.path.join(sh.SYS, "accounts")


def register_ids():
    return sorted(n for n in os.listdir(sys_accounts()) if n != "sdsys")


def make_hand_accounts():
    for name, (grp, gates, rest) in HAND.items():
        path = os.path.join(sh.BOX, "group_accounts" if grp.startswith("sdg_") else "user_accounts", name)
        os.makedirs(path, exist_ok=True)
        g.reg_write(name, [path, "hand-made", grp, "", "", ""] + gates + rest + [""])


def read_fields(name):
    return g.reg_read(name)


def user_accounts():
    return [n for n in register_ids() if (read_fields(n)[2] if len(read_fields(n)) > 2 else "").startswith("sdu_")]


def audit_lines():
    try:
        return [ln for ln in open(os.path.join(sh.SYS, "audit"), "rb").read().decode("latin-1").split("\n") if ln != ""]
    except OSError:
        return []


def list_servers():
    """The LIST.SERVERS lines, asked of SD by a separate administrator session: [(name, address, account/mode, pin, allowed)]."""
    out = g.adm(["LIST.SERVERS"])
    res = []
    for ln in out:
        f = ln.split()
        if len(f) >= 5 and ":" in f[1]:
            res.append((f[0], f[1], f[2], f[3], f[4]))
    return res


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def st(h):
    return h.line(40)


def setup_pages():
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_remote"), os.path.join(sh.SYS, "gpl.bp", "tool_remote"))
    out = g.adm(["BASIC gpl.bp tool_remote"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_remote did not compile in the sandbox:\n" + "\n".join(out[-8:]))
    with open(os.path.join(sh.SYS, "audit"), "ab"):                 # a session appends to the audit file and never makes it
        pass
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzrw"), WRITER)
    make_hand_accounts()


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_remote")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_remote"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    """A session on tool.remote on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.remote\r", idle=4.5)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.8):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def top(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(2, 6)))

    def rows(self):
        return [self.line(y)[3:137].rstrip().rstrip("|").rstrip() for y in range(9, 26)]

    def detail(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(28, 39)))

    def ask(self, text, existing=""):
        self.h.typed("\x7f" * len(existing) + text + "\r", idle=1.0)

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def box_open(p):
    T = norm(p.text())
    return "Cancel" in T and "Run" in T


# ------------------------------------------------------------------------------------------------------------------------------- the sections

def section_r0():
    say("\n--- R0: an ordinary account")
    out = g.plain(ACC, ["tool.remote"])
    T = norm(" ".join(out))
    arow("R0a", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)", "About this view" not in T and "Remote access" not in T and len(out) > 0, T[:300])
    out = g.plain(ACC, ["BASIC bp zzrw", "RUN bp zzrw"])
    wrote = has(out, r"^ZZRW written$")
    out = g.plain(ACC, ["ztrem"])
    T = norm(" ".join(out))
    arow("R0b", "a VOC entry an ordinary account made for the program gets the page's own refusal (message 11800), not 'not a command', and no page", wrote and "is for the administrator only" in T and "About this view" not in T, repr((wrote, T[:300])))


def section_r1():
    say("\n--- R1: the page opens")
    ap = g.adm(["REMOTE.API"])
    ss = g.adm(["REMOTE.SSH"])
    ap1 = norm(next((x for x in ap if x.strip()), ""))
    ss1 = norm(next((x for x in ss if x.strip()), ""))
    arow("R1a", "the two verbs, run with no keyword by a separate administrator session, answered something (the null case: the instrument measured); in a sandbox they cannot reach a socket unit or a firewall, so what they say is their refusal or report",
         ap1 != "" and ss1 != "", repr((ap1[:80], ss1[:80])))
    a0 = len(audit_lines())
    p = Page()
    if "About this view" not in p.text():
        dump(p.h)
        bail("tool.remote never drew its page, so no row below can be believed")
    mine = [ln for ln in audit_lines()[a0:] if " tool " in ln]
    arow("R1b", "opening the page wrote one audit line, 'tool start app=tool.remote', and no other 'tool' line", len(mine) == 1 and mine[0].endswith("tool start app=tool.remote"), repr(mine))
    top = p.top()
    ap_lines = [norm(x) for x in ap if x.strip()]
    ss_lines = [norm(x) for x in ss if x.strip()]
    m_api = re.search(r"API: (.*?) ssh: ", top)
    m_ssh = re.search(r" ssh: (.*?) \d+ SDNet server", top)
    arow("R1c", "the top box shows a line of each verb's report after 'API:' and 'ssh:' (the first the page's own capture gave; the verb's lines are not in a fixed order when a root helper writes to the error stream too)",
         m_api is not None and m_ssh is not None and any(m_api.group(1)[:50] in x for x in ap_lines) and any(m_ssh.group(1)[:50] in x for x in ss_lines), top[:300])
    rows = [norm(r) for r in p.rows() if r.strip()]
    verb_lines = ap_lines + ss_lines
    # the page's capture also holds the root helper's own error lines ('sudo: ...'), which a plain session leaves out of the verb's output: every line the verbs print is a row (cut at the row's width),
    # and a row that is not one of them is one of those
    missing = [x for x in verb_lines if not any(x.startswith(r) or r.startswith(x[:134]) for r in rows)]
    extra = [r for r in rows if not any(x.startswith(r) for x in verb_lines) and not r.startswith("sudo:")]
    arow("R1d", "the doors view lists the words of REMOTE.API and REMOTE.SSH: every line the verbs print is a row, and any other row is the root helper's own 'sudo:' line", not missing and not extra and len(rows) >= 1, repr((missing[:2], extra[:2], rows[:3], [p.line(y)[:14] for y in range(8, 16)])))   # the raw left edge of the first rows: a row that starts at column 0 is a carriage return in the text
    return p


def section_r2(p):
    say("\n--- R2: the doors")
    a0 = len(audit_lines())
    # S.244 (1), 15 Nov 26: A and S choose from a LIST that starts on off; Up moves, Enter chooses
    p.key("a", 1.2)
    T = norm(p.text())
    p.key("esc", 1.0)
    arow("R2a", "A shows a list (on, local, off) instead of a typed word, and Esc on it runs nothing and shows no box",
         "The API door (REMOTE.API)" in T and "other computers may connect" in T and "only this computer" in T and "no API socket" in T and "nothing was run" in st(p) and not box_open(p), T[-500:])
    p.key("a", 1.2)
    p.key("up", 0.4)
    p.key("enter", 1.2)
    T = norm(p.text())
    arow("R2b", "A with local shows 'remote.api local' and what it does, in a box with Run and Cancel", box_open(p) and "remote.api local" in T and "127.0.0.1:4247 only" in T, T[-400:])
    p.key("esc", 1.0)
    p.key("a", 1.2)
    p.key("home", 0.4)
    p.key("enter", 1.2)
    T = norm(p.text())
    arow("R2c", "A with on shows 'remote.api on', says it listens on EVERY address and opens the firewall, in a box", box_open(p) and "remote.api on" in T and "EVERY address" in T, T[-500:])
    p.h.typed("r", idle=1.5)
    p.h.typed("opne\r", idle=1.5)
    arow("R2d", "Run asks for the word open (S.244 (5): shown in lower case); a wrong word runs nothing: the status line says so and the audit trail has no remote.api line", "open" in st(p) and "OPEN" not in st(p) and "ran (status" not in st(p) and not [ln for ln in audit_lines()[a0:] if "remote.api" in ln], st(p))
    p.key("s", 1.2)
    T = norm(p.text())
    p.key("esc", 1.0)
    arow("R2e", "S shows a list (on, off) instead of a typed word; Esc runs nothing", "The ssh door (REMOTE.SSH)" in T and "the firewall allows port 22" in T and "only this computer over ssh" in T and "nothing was run" in st(p) and not box_open(p), T[-500:])
    p.key("s", 1.2)
    p.key("home", 0.4)
    p.key("enter", 1.2)
    T = norm(p.text())
    arow("R2f", "S with on shows 'remote.ssh on' in a box that says the firewall will allow port 22 and that it never moves the ssh server", box_open(p) and "remote.ssh on" in T and "port 22" in T and "never the ssh server" in T, T[-500:])
    p.key("esc", 1.0)
    arow("R2g", "nothing was run: the audit trail has no remote.api and no remote.ssh line", not [ln for ln in audit_lines()[a0:] if "remote.api" in ln or "remote.ssh" in ln], "")


def section_r3(p):
    say("\n--- R3: the routes")
    p.key("2", 1.5)
    users = user_accounts()
    rows = [r for r in p.rows() if r.strip()]
    names = [r[:20].strip() for r in rows]
    arow("R3a", "the routes view has one row for each USER account of the register, in name order, and no other (%s)" % " ".join(users), names == users, repr((names, users)))
    # 17 Nov 26 (S.62, L4 C4): the doors are what the account's Linux user's real groups give, read here with the grp module, so a row is right on a host where that user exists
    # and is in sdssh / sdapi / sdfiles... (the sandbox user's own sdu_<user> account, made by another suite on a shared sandbox, showed doors and the row failed).  A user that does
    # not exist is in no group: no door and 'no remote door', as before.  The rows that were judged against a real user are counted and printed.
    def real_groups(user):
        try:
            pw = pwd.getpwnam(user)
        except KeyError:
            return None
        mine = {gr.gr_name for gr in grp.getgrall() if user in gr.gr_mem}
        try:
            mine.add(grp.getgrgid(pw.pw_gid).gr_name)
        except KeyError:
            pass
        return mine
    bad = []
    real = []
    for r in rows:
        name = r[:20].strip()
        f = read_fields(name)
        net = "yes" if f[14].strip().upper() == "YES" else "no"
        cells = r[20:].split()
        lu = f[2][4:] if len(f) > 2 and f[2].startswith("sdu_") else ""
        rg = real_groups(lu) if lu else None
        if rg is None:
            want = ["no", "no", "no", "no", "no", net]
            reach = "no remote door"
        else:
            real.append(lu)
            yn = ["yes" if x in rg else "no" for x in ("sdssh", "sdapi", "sdfiles", "sdfileswrite", "sdfilesadmin")]
            want = yn + [net]
            reach = None if "yes" in yn[:3] else "no remote door"
        if cells[:6] != want or (reach is not None and reach not in r):
            bad.append((name, cells[:8], want))
    arow("R3b", "each row shows the doors its Linux user's groups give (none, and 'no remote door', for a user that does not exist on this host: the sandbox's own fixtures), the NET gate as the register "
         "has it (judged against the real groups of %d existing user(s): %s; zzme's user exists, so at least one)" % (len(real), " ".join(real) or "none"),
         not bad and len(rows) == len(users) and len(real) >= 1, repr((bad[:2], real)))
    T = p.detail()
    arow("R3c", "the foot box explains the groups sdssh, sdapi, sdfiles and that the switches are TOOL.GATES's", "sdssh" in T and "sdapi" in T and "sdfiles" in T and "TOOL.GATES" in T, T[:300])


def section_r4(p):
    say("\n--- R4: the servers")
    g.adm(["SET.SERVER alpha 192.0.2.1 4247 remoteacct %s READ ACCOUNTS zzaa NO.QUERY" % PIN_A])
    g.adm(["SET.SERVER beta host.example 4249 other %s WRITE NO.QUERY" % PIN_B])
    want = list_servers()
    arow("R4a", "the fixture servers exist as LIST.SERVERS (the real verb) says: alpha and beta, set with typed pins so nothing was dialled (the null case: the instrument measured)", sorted(w[0] for w in want) == ["alpha", "beta"], repr(want))
    first, victim = want[0][0], want[1][0]                                          # the verb's order; the delete is tried on the SECOND, so a page that sends the first is caught
    p.key("f5", 1.5)
    p.key("3", 1.5)
    rows = [r for r in p.rows() if r.strip()]
    got = []
    for r in rows:
        f = r.split()
        if len(f) >= 5:
            got.append((f[0], f[1], f[2], f[3], f[4]))
    arow("R4b", "the servers view has a row for each definition, and each row's name, address, remote account and mode, pin shortened and local accounts are LIST.SERVERS's", got == want, repr((got, want)))
    def to_server(name):
        p.key("home", 0.6)
        for _ in range(12):
            if ("Under the cursor: " + name + " at") in p.detail():
                return True
            p.key("down", 0.4)
        return False
    on_victim = to_server(victim)
    d = p.detail()
    pin = PIN_A if victim == "alpha" else PIN_B
    arow("R4c", "the foot box for %s shows its full 64-digit pin and who may use it" % victim, on_victim and pin in d and ("Local accounts that may use it: " + ("zzaa" if victim == "alpha" else "none")) in d, d[:300])
    a0 = len(audit_lines())
    p.key("x", 1.5)
    T = norm(p.text())
    arow("R4d", "X on %s shows 'delete.server %s' and what it does in a box" % (victim, victim), box_open(p) and ("delete.server " + victim) in T and "removed from the servers file" in T, T[-400:])
    p.key("esc", 1.0)
    arow("R4e", "Esc runs nothing: both definitions are still there and the audit trail has no delete line", sorted(w[0] for w in list_servers()) == ["alpha", "beta"] and not [ln for ln in audit_lines()[a0:] if "delete.server" in ln], st(p))
    p.key("x", 1.5)
    p.h.typed("r", idle=4.0)
    after = list_servers()
    arow("R4f", "Run: the real verb removed %s and only %s (LIST.SERVERS afterwards: %s), and the page shows the same" % (victim, victim, first), [w[0] for w in after] == [first] and any(first in r for r in p.rows()) and not any(victim in r.split()[:1] for r in p.rows() if r.strip())
         and ("delete.server " + victim + " ran (status") in st(p), repr((after, p.rows()[:2], st(p))))


def section_r5(p):
    say("\n--- R5: define")
    a0 = len(audit_lines())
    before = [w[0] for w in list_servers()]

    def start():
        p.key("n", 1.2)

    # S.88: N is one form (name, host, port, account, pin, mode, local accounts); Tab between the entries, Return presses Define; a refusal is said in the form, which stays until Esc
    # S.244 (15 Nov 26): every entry opens EMPTY (the port and the pin take their default, shown beside them, when left empty) and Files is a selector on read

    def fill(vals):
        """vals: the seven answers (None leaves the field as it starts); the sixth, Files, is a choice: 'write' is the space bar"""
        parts = []
        for i, v in enumerate(vals):
            if i == 5:
                parts.append(" " if v == "write" else "")
            else:
                parts.append("" if v is None else v)
        p.h.typed("\t".join(parts) + "\r", idle=1.5)

    def refused(words):
        T = norm(p.text())
        p.key("esc", 1.0)
        return words in T

    start()
    fill(["1abc", None, None, None, None, None, None])
    arow("R5a", "a name that does not start with a letter is refused in words, in the form", refused("a server name is a lower case letter and up to 15 lower case letters or digits"), st(p))
    start()
    fill(["gamma", "-bad.example", None, None, None, None, None])
    arow("R5b", "a host that starts with a hyphen is refused", refused("a host is letters, digits, dots, hyphens and colons"), st(p))
    start()
    fill(["gamma", "good.example", "99999", None, None, None, None])
    arow("R5c", "a port above 65535 is refused", refused("a port is a number from 1 to 65535"), st(p))
    start()
    fill(["gamma", "good.example", None, "remote acct", None, None, None])
    arow("R5d", "a remote account with a space is refused", refused("a remote account is up to 32 letters"), st(p))
    start()
    fill(["gamma", "good.example", None, "remoteacct", "xyz", None, None])
    arow("R5e", "a pin that is neither connect nor 64 hexadecimal digits is refused", refused("a pin is the word connect or exactly 64 hexadecimal digits"), st(p))
    start()
    p.key("n", 1.2)
    T = norm(p.text())
    p.key("esc", 1.0)
    arow("R5f", "S.244: Files is a choice [READ | write], not typed, and the port and pin entries open empty with their defaults beside them",
         "[READ write]" in T and "default: 4247" in T and "default: connect" in T, T[-600:])     # norm() takes the bars out
    start()
    fill(["gamma", "good.example", None, "remoteacct", None, None, "nosuchacct"])
    arow("R5g", "a local account that is not a registered USER account is refused", refused("each local account must be a registered USER account"), st(p))
    start()
    fill(["gamma", "good.example", None, "remoteacct", None, "write", "zzaa,zzab"])
    T = norm(p.text())
    arow("R5h", "a good set shows 'set.server gamma good.example 4247 remoteacct connect write accounts zzaa,zzab' in a box that says the terminal is given to the verb and shows no no.query",
         box_open(p) and "set.server gamma good.example 4247 remoteacct connect write accounts zzaa,zzab" in T and "The terminal is given to the verb" in T and "no.query" not in T, T[-600:])
    p.key("esc", 1.0)
    arow("R5i", "nothing was defined: LIST.SERVERS shows the servers it showed and the audit trail has no set.server line", [w[0] for w in list_servers()] == before and not [ln for ln in audit_lines()[a0:] if "set.server" in ln], repr(list_servers()))


def section_r6(p):
    say("\n--- R6: connected now")
    other = H(account=OTHER)
    try:
        p.key("4", 1.5)
        p.key("f5", 2.0)
        lu = g.adm(["LISTU"])
        n_listu = len([ln for ln in lu if re.match(r"^\*?\s*\d+\s+\d+\s", ln)]) - 1                   # the LISTU session itself is not one the page saw
        rows = [r for r in p.rows() if r.strip()]
        mine = [r for r in rows if r.split()[3:4] == [OTHER]]
        arow("R6a", "the connected view lists the session signed on in %s with its kind (user), its login user and its account, and as many rows as LISTU shows sessions (%d)" % (OTHER, n_listu),
             len(mine) == 1 and mine[0].split()[1] == "user" and len(rows) == n_listu, repr((rows, n_listu)))
        T = p.detail()
        arow("R6b", "the foot box counts the sessions by kind", re.search(r"\d+ user, \d+ api, \d+ sdnet, \d+ phantom\.", T) is not None, T[-200:])
    finally:
        other.end()
    time.sleep(2.0)


def section_r8(p):
    say("\n--- R8: the sdsys login view and REMOTE.SDSYS (S.95 stage 1b, S.106)")
    out = g.plain(ACC, ["remote.sdsys"])
    T = norm(" ".join(out))
    arow("R8a", "an ordinary account has no remote.sdsys (SDSYS's VOC alone has the verb): no report and no usage", len(out) > 0 and "sdsys-arm" not in T and "remote.sdsys on off" not in T and "opens ssh for sdsys" not in T, T[:300])
    a0 = len(audit_lines())
    # 17 Nov 26 (S.62, L4 C4): the usage follows the verb, which gained its ssh and api forms in S.256 (3f8d2fa2); two of those forms that are refused join the four
    out = g.adm(["REMOTE.SDSYS BOGUS", "REMOTE.SDSYS ON EXTRA", "REMOTE.SDSYS RECOVERY", "REMOTE.SDSYS LOCAL ON", "REMOTE.SDSYS SSH ON EXTRA", "REMOTE.SDSYS API OFF 10.0.0.1"])
    T = norm(" ".join(out))
    arow("R8b", "a keyword that is not on or off (recovery and local went with the authenticator code), a second word after one, a word after ssh on, and an address after api off, "
         "each get the usage (11923, with its ssh and api forms) and run nothing: six times the usage, no audit line",
         T.count("remote.sdsys {on off} remote.sdsys ssh {on off} remote.sdsys api {on address ... off}") == 6     # norm() makes the bars spaces
         and not [ln for ln in audit_lines()[a0:] if "remote.sdsys" in ln], T[:300])
    # ON and OFF are NEVER run here: on a machine where the sandbox user could sudo the helper they would really open or shut ssh for sdsys (the VM witness's rows)
    rep = [norm(x) for x in g.adm(["REMOTE.SDSYS"]) if x.strip()]
    p.key("6", 4.0)
    p.key("f5", 4.0)
    T = p.text()
    rows = [norm(r) for r in p.rows() if r.strip() and not r.startswith(("Local ssh users:", "Local API users:"))]     # 18 Nov 26 (S.267): the two fields under the report are section local's
    arow("R8c", "key 6 shows the sdsys login view (its box title and header) and its rows are what REMOTE.SDSYS printed for a separate administrator session (a sandbox cannot reach the root helper, so that is "
         "its refusal; any other row is the helper's own 'sudo:' line)",
         "The sdsys login over ssh" in T and "REMOTE.SDSYS, with no keyword" in T and len(rep) >= 1 and len(rows) >= 1
         and all(any(x.startswith(r) or r.startswith(x[:134]) for x in rep) or r.startswith("sudo:") for r in rows), repr((rows[:4], rep[:4])))
    a0 = len(audit_lines())
    p.key("o", 1.5)
    T = norm(p.text())
    arow("R8d", "O shows 'remote.sdsys on' in a box that says sdsys can then sign in with its password, that nothing else stands between the network and the administrator, and wants a word typed",
         box_open(p) and "remote.sdsys on" in T and "password" in T and "word open typed" in T, T[-500:])
    p.key("esc", 1.2)
    p.key("f", 1.5)
    T = norm(p.text())
    arow("R8e", "F shows 'remote.sdsys off' in a box that says sshd is shut to sdsys", box_open(p) and "remote.sdsys off" in T and "shut to sdsys" in T, T[-500:])
    p.key("esc", 1.2)
    p.key("r", 1.5)
    T = norm(p.text())
    arow("R8f", "R opens no box any more (the recovery codes went with the authenticator code), and neither does L", not box_open(p) and "recovery" not in T.lower(), T[-300:])
    p.key("l", 1.5)
    arow("R8g", "L opens no box either", not box_open(p), st(p))
    p.key("1", 3.0)
    p.key("o", 1.5)
    arow("R8h", "Esc ran nothing (no remote.sdsys audit line), and O on the doors view opens no box", not box_open(p) and not [ln for ln in audit_lines()[a0:] if "remote.sdsys" in ln], st(p))


def section_local(p):
    """S.267: the two fields of the sdsys view (Local ssh users, Local API users) and the U, X and C boxes.  A sandbox has no root helper, so local.sdsys cannot read either list
    here: each field must then say 'not read: ' with the verb's first line, and the page must go on.  Nothing is ever RUN: on a machine where the sandbox user could sudo the
    helper, Run would really change the lists (the VM witness's rows); the add box is answered with a WRONG name, the others with Esc."""
    say("\n--- local (S.267): the two fields of local.sdsys on the sdsys view")
    rep = [norm(x) for x in g.adm(["LOCAL.SDSYS"]) if x.strip()]
    a0 = len(audit_lines())
    p.key("6", 4.0)
    p.key("f5", 4.0)
    T = p.text()
    rows = p.rows()
    f_ssh = next((r for r in rows if r.startswith("Local ssh users: ")), None)
    f_api = next((r for r in rows if r.startswith("Local API users: ")), None)

    def field_ok(f):
        if f is None:
            return False
        v = f.split(": ", 1)[1]
        return v == "none listed" or v.startswith("not read: ") and len(v) > len("not read: ") or v.startswith("unsafe") or re.fullmatch(r"[a-z_][a-z0-9_-]*( [a-z_][a-z0-9_-]*)*( \.\.\.)?", v) is not None
    arow("L1", "key 6 shows the two fields under the report, Local ssh users then Local API users, each either the helper's words (none listed, the names, unsafe) or 'not read: ' with the verb's first line "
         "(a sandbox cannot reach the root helper); a separate administrator session's local.sdsys printed something (the null case), and the page is still drawn",
         "About this view" in T and field_ok(f_ssh) and field_ok(f_api) and rows.index(f_api) == rows.index(f_ssh) + 1 and len(rep) >= 1, repr((f_ssh, f_api, rep[:3])))
    readable = f_ssh is not None and not f_ssh.split(": ", 1)[1].startswith("not read: ")
    # Esc only when X opened its list of names: with no box open, Esc on the page goes back to the doors view (the page's Esc rule)
    p.key("down", 1.0)
    p.key("x", 1.5)
    s_api = st(p)
    if readable:
        p.key("esc", 1.0)
    p.key("up", 1.0)
    p.key("x", 1.5)
    s_ssh = st(p)
    if readable:
        p.key("esc", 1.0)
    say("    fields: %r / %r" % (f_ssh, f_api))
    arow("L2", "Down puts the cursor on Local API users and Up on Local ssh users: X then names that list (with no list read there is no name to remove, and no box opens)",
         readable or ("Local API users: no name is listed" in s_api and "Local ssh users: no name is listed" in s_ssh and not box_open(p)), repr((s_api, s_ssh)))
    p.key("u", 1.5)
    T = norm(p.text())
    asked = "Linux user name to add to Local ssh users" in T
    p.ask("Bad!Name")
    s = st(p)
    arow("L3", "U asks for a name; one that is not a Linux user name is refused in 14184's words before any box", asked and "is not a Linux user name" in s and not box_open(p), repr((asked, s)))
    p.key("u", 1.5)
    p.ask("zzlocal")
    T = norm(p.text())
    arow("L4", "U with a good name shows 'local.sdsys ssh add zzlocal no.query' in a box with Run and Cancel that says what listing means (14179: the administrator, ssh -t zzlocal@localhost sd-sdsys)",
         box_open(p) and "local.sdsys ssh add zzlocal no.query" in T and "administrator" in T and "zzlocal@localhost" in T, T[-600:])
    p.key("r", 1.5)
    T = norm(p.text())
    wants = "zzlocal" in T
    p.ask("zzother")
    s = st(p)
    arow("L5", "Run asks for the name typed again; a different name runs nothing (11810 names the name asked for)", wants and "nothing was run" in s and "zzlocal" in s, repr((wants, s)))
    p.key("u", 1.5)
    p.ask("zzlocal")
    p.key("esc", 1.2)
    s = st(p)
    arow("L6", "Esc (Cancel) at the add box runs nothing", "nothing was run" in s and not box_open(p), s)
    p.key("down", 1.0)
    p.key("u", 1.5)
    p.ask("zzlocal")
    T = norm(p.text())
    arow("L7", "on Local API users U shows 'local.sdsys api add zzlocal no.query' and 14180's words (the Unix socket of the API)", box_open(p) and "local.sdsys api add zzlocal no.query" in T and "Unix socket" in T, T[-600:])
    p.key("esc", 1.2)
    p.key("c", 1.5)
    T = norm(p.text())
    arow("L8", "C shows 'local.sdsys api clear' in a box that says it tightens; Esc runs nothing", box_open(p) and "local.sdsys api clear" in T and "tightens" in T, T[-600:])
    p.key("esc", 1.2)
    p.key("1", 3.0)
    p.key("u", 1.5)
    T = norm(p.text())
    arow("L9", "U on the doors view asks nothing (the keys are the sdsys view's alone), and no local.sdsys audit line was written in this section (nothing ran)",
         "Linux user name to add" not in T and not box_open(p) and not [ln for ln in audit_lines()[a0:] if "local.sdsys" in ln], T[-300:])


def section_r7(p):
    say("\n--- R7: TLS, the mouse, F1, a small window, an input that ends")
    p.key("5", 4.0)
    T = p.text()
    arow("R7a", "the TLS view draws (its box title, the public-key sentence in the foot box) and shows no key material (no PEM block)", "TLS identity of this machine" in T and "public key" in T and "-----BEGIN" not in T, T[-300:])
    p.key("3", 1.2)
    p.key("home", 0.6)
    name1 = p.rows()[0].split()[0]
    p.h.click(20, 9)
    arow("R7b", "a click on the first server row puts the cursor there (the foot box names it: %s)" % name1, ("Under the cursor: " + name1 + " at") in p.detail(), p.detail()[-300:])
    p.h.click(135, 2)
    T = norm(p.text())
    arow("R7c", "a click on the [?] reaches the help box ($tk_help says help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("R7d", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.remote\r", idle=3.0)
    T = h.text()
    arow("R7e", "a window under 140 by 43 gets no page (the toolkit's one size check)", "About this view" not in T and "Remote access" not in T, T[-300:])
    h.end()
    env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(sh.BOX, "r7-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.remote\n")
    pr.stdin.flush()
    time.sleep(5)
    pr.stdin.close()
    try:
        pr.wait(timeout=20)
        ended = True
    except subprocess.TimeoutExpired:
        ended = False
        pr.kill()
        pr.wait()
    fh.close()
    with open(os.path.join(sh.BOX, "r7-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("R7f", "a page whose input ends ends by itself within 20 seconds; the output shows it did start (the null case)", ended and "About this view" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


SECTIONS = ["r0", "r2", "r3", "r4", "r5", "r6", "r8", "local", "r7"]     # 18 Nov 26 (S.267): --only=NAME[,NAME]; R1 opens the page and always runs (with the build and the fixtures)


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-remote.py <dir> [--build] [--mutant=%s] [--only=%s]" % ("|".join(MUTANTS), ",".join(SECTIONS)))
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), None)
    if only is not None:
        only = [w.strip().lower() for w in only.split(",") if w.strip()]
        if not only or any(w not in SECTIONS for w in only) or mutant is not None:
            bail("usage: --only=NAME[,NAME] with NAME one of %s, and not with --mutant" % ",".join(SECTIONS))
        say("sandbox-tool-remote: --only=%s (R1, which opens the page, always runs)" % ",".join(only))
    global MUTANT
    MUTANT = mutant
    if only is not None:
        p = None
        try:
            sh.setup("sandbox-tool-remote.py")
            setup_pages()
            if "r0" in only:
                section_r0()
            p = section_r1()
            for name, fn in (("r2", section_r2), ("r3", section_r3), ("r4", section_r4), ("r5", section_r5), ("r6", section_r6), ("r8", section_r8), ("local", section_local), ("r7", section_r7)):
                if name in only:
                    fn(p)
            if "r7" not in only:
                p.quit()
        finally:
            sh.teardown()
        say("\nsandbox-tool-remote: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
        return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1
    last = MUTANTS[mutant][3] if mutant else "R7"
    order = ["R2", "R3", "R4", "R5", "R6", "R7"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    p = None
    try:
        sh.setup("sandbox-tool-remote.py")
        setup_pages()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-remote: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_r0()
        p = section_r1()
        if run("R2"):
            section_r2(p)
        if mutant is None:
            section_r3(p)
        if run("R4"):
            section_r4(p)
        if run("R5"):
            section_r5(p)
        if mutant is None:
            section_r6(p)
            section_r8(p)
            section_local(p)
            section_r7(p)
        else:
            p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-remote: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"R\d+", i).group(0) for i in FAILED_IDS if re.match(r"R\d+", i)})
        ok = want == got
        say("sandbox-tool-remote: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
