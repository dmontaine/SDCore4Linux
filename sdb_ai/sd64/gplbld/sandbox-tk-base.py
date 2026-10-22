#!/usr/bin/env python3
#
# sandbox-tk-base.py - the toolkit's shared base, slice 1 (TK-0.1: the frame, the key table and the function-key row), on a pseudo-terminal.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-base.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.  The throw-away app `tktest` (gpl.bp/tool_tktest, catalogued $tool_tktest) is given a VOC entry by this suite and by nothing else: it is not a verb of the product.
#
# START-HISTORY:
# 22 Oct 26 dm  New (S.75, TK-0.1).  Rows written BEFORE the programs; run red on a tree without them.
# END-HISTORY
#
# WHAT IS HELD (plan .claude/plan-fullscreen-toolkit.md 2.1, 2.2, 2.12): at 140 by 43 the foot of the screen is, top to bottom, the status line (row 40, reverse video, the pane in
# brackets first, then the message), the border (row 41), and the function keys (row 42, the added 43rd line); the function-key row names only the keys the focused pane uses, in the
# key table's order, and changes when the focus does; a key the table disables is not shown; the keys do what their labels say (Tab, F1, F3 on pane A only, F5 on pane B only, Ctrl-Q);
# a bigger window is used whole (the rows move to its foot); a window under 140 by 43 is refused with the library's message 11197 before the screen is taken; Ctrl-Q leaves and gives the
# prompt back; and when the input ENDS the app ends and does not spin (a piped session: wall time and the child's own CPU).
#
# THE INSTRUMENT.  Each row reads the screen the emulator holds (termscreen.py) after the keys were typed; a row passes on the words it prints when it ran to the end, and the suite stops
# (exit 2) if the app never drew its frame.  The border is judged with LC_ALL=C, where the library's line character is the plain "-".  NOT HELD HERE: the refusal of a non-administrator
# for audience `admin` (the sandbox's session is the administrator; the check is a text check in test-tkbase-units.py and a later witness), a UTF-8 border, the mouse.
import os
import re
import resource
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession    # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-B]|\x1b[=>78M]")
passed = failed = skipped = 0

F_A = "F1 help  F3 sort  Tab next  ^Q quit"
F_B = "F1 help  F5 refresh  Tab next  ^Q quit"

KEYS = {"F1": "\x1bOP", "F3": "\x1bOR", "F5": "\x1b[15~", "TAB": "\t", "CTRLQ": "\x11", "CTRLS": "\x13", "F7": "\x1b[18~", "F8": "\x1b[19~", "ENTER": "\r", "ESC": "\x1b",
        "LEFT": "\x1bOD", "RIGHT": "\x1bOC", "F2": "\x1bOQ", "F9": "\x1b[20~", "F10": "\x1b[21~", "F11": "\x1b[23~", "F12": "\x1b[24~", "PGDN": "\x1b[6~", "F4": "\x1bOS", "F6": "\x1b[17~", "UP": "\x1bOA", "DOWN": "\x1bOB", "HOME": "\x1b[1~", "END": "\x1b[4~", "SPACE": " ", "CTRLU": "\x15"}
F_D = "F1 help  F7 confirm  F8 typed  Tab next  ^Q quit"


def say(s=""):
    print(s, flush=True)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def skip(name, why):
    global skipped
    skipped += 1
    say("  [SKIP] %s: %s" % (name, why))


def bail(msg):
    say("sandbox-tk-base: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A session in internal mode (sd -internal), the only place a $internal program compiles; the sandbox tool's own `sess` cannot (as sandbox-sortord.py's isess)."""
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd"), "-internal"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=os.path.join(box, "sys"), env=env)
    try:
        out, _ = p.communicate(body.encode("latin-1"), timeout=300)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        return ""
    return ANSI.sub("", out.decode("latin-1", "replace")).split(":TERM 200,9999", 1)[-1]


class Term:
    def __init__(self, box, cmd, cols=140, rows=43):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.cols, self.rows = cols, rows
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.0)

    def lines(self):
        return self.s.screen.lines()

    def line(self, r):
        L = self.lines()
        return L[r].rstrip() if r < len(L) else ""

    def rev(self, r):
        return self.s.screen.reverse(r)

    def key(self, name):
        self.s.type(KEYS[name], idle=0.5)

    def end(self):
        self.s.type("\x11", idle=0.3)
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


# TK-0.2.  A $internal program calls $tk_gate_info and $tk_run in an internal session and prints one line for each; the numbers in it are the TK.G.* fields of tk.h
# (test-tkgates-units.py holds them).  The sentinel is a real effect: create.file zztkrunf.  Every refusal below is a sentence that WOULD make the file if it ran.
RUNPROG = """$internal
   crt 'TKRUN begin'
   call $tk_gate_info('list', ids)
   crt 'GL ' : dcount(ids, @fm) : ' ' : ids<1> : ' ' : ids<dcount(ids, @fm)>
   call $tk_gate_info('sh', g)
   crt 'GSH ' : g<3> : ' ' : g<4> : ' ' : g<8> : ' ' : g<11> : ' ' : g<15>
   call $tk_gate_info('nosuch', g)
   crt 'GNO [' : g : ']'
   call $tk_gate_info('sockets', g)
   crt 'GSK ' : g<15> : ' [' : g<3> : ']'
   allow = 'who.am.i create.file'
   tag = 'T1' ; sentence = 'who.am.i' ; gosub go
   tag = 'T2' ; sentence = 'WHO.AM.I' ; gosub go
   tag = 'T3' ; sentence = 'sh ls' ; gosub go
   tag = 'T4' ; sentence = 'who' ; gosub go
   tag = 'T5' ; sentence = 'who.am.i x;sh' ; gosub go
   tag = 'T6' ; sentence = "who.am.i 'x'" ; gosub go
   tag = 'T7' ; sentence = 'who.am.i' : char(9) : 'x' ; gosub go
   tag = 'T8' ; sentence = 'who.am.i x' : @vm ; gosub go
   tag = 'T9' ; sentence = '' ; gosub go
   tag = 'T10' ; sentence = '   ' ; gosub go
   tag = 'T11' ; sentence = 'who.am.i ' : str('a', 600) ; gosub go
   tag = 'T12' ; sentence = 'who.am.i' : str(' a', 41) ; gosub go
   tag = 'T13' ; sentence = 'who.am.i' : str(' a', 39) ; gosub go
   tag = 'T14' ; sentence = 'who.am.i `x`' ; gosub go
   tag = 'T15' ; sentence = 'who.am.i $x' ; gosub go
   tag = 'S1' ; sentence = 'create.file zztkrunf;ls dynamic' ; gosub go
   tag = 'S2' ; sentence = 'CREATE.FILE zztkrunf dynamic' ; gosub go
   tag = 'S3' ; sentence = "create.file zztkrunf 'dynamic'" ; gosub go
   open 'zztkrunf' to f then
      crt 'SENT after-refusals EXISTS'
      close f
   end else crt 'SENT after-refusals ABSENT'
   tag = 'S4' ; sentence = 'create.file zztkrunf dynamic' ; gosub go
   open 'zztkrunf' to f then
      crt 'SENT after-run EXISTS'
      close f
   end else crt 'SENT after-run ABSENT'
   execute 'delete.file zztkrunf force' capturing o2
   crt 'TKRUN end'
   stop
go:
   call $tk_run(allow, sentence, out, st, err)
   crt tag : ' st=' : st : ' err=[' : err : '] ran=' : (if index(out, 'Admin?', 1) > 0 then 1 else 0)
   return
end
"""


def runtime_rows(box, made):
    say("\n--- the gate table and the one place a tool runs a command (TK-0.2)")
    with open(os.path.join(box, "sys", "bp", "zztkrun"), "w", encoding="latin-1") as f:
        f.write(RUNPROG)
    made.append("zztkrun")
    out = sess(box, "DELETE.FILE zztkrunf FORCE", "BASIC bp zztkrun", "RUN bp zztkrun")
    if not re.search(r"^TKRUN begin\s*$", out, re.M) or not re.search(r"^TKRUN end\s*$", out, re.M):
        say(out[-1200:])
        bail("the TK-0.2 program did not run to its end, so no row below can be believed")
    got = {}
    for m in re.finditer(r"^(\w+) st=(-?\d+) err=\[(.*)\] ran=(\d)\s*$", out, re.M):
        got[m.group(1)] = (int(m.group(2)), m.group(3), int(m.group(4)))
    line = lambda pat: re.search(pat, out, re.M)
    row("$tk_gate_info 'list' returns the 15 ids, the first ssh and the last the planned sockets", line(r"^GL 15 ssh sockets\s*$") is not None, out[-300:])
    row("a gate by id returns its words, kernel key, conflict slot and status: sh = sh-on sh-off K$SH SH built", line(r"^GSH sh-on sh-off K\$SH SH built\s*$") is not None, "")
    row("an id that is not in the table returns nothing", line(r"^GNO \[\]\s*$") is not None, "")
    row("a planned gate shows as planned and has no word to run", line(r"^GSK planned \[\]\s*$") is not None, "")

    NOTALLOWED, CHAR, EMPTY, LONG = "is not one of the commands this tool may run", "has a character that a command word may not have", "there is nothing to run", "the command is too long to run"
    want = [
        ("T1", "an allowed command runs: who.am.i (no message, it ran, and its own words came back)", lambda e, r: e == "" and r == 1),
        ("T2", "the first word is compared as typed: WHO.AM.I in capitals is refused (11805) and did not run", lambda e, r: NOTALLOWED in e and r == 0),
        ("T3", "a command that is not in the list (sh ls) is refused (11805)", lambda e, r: NOTALLOWED in e and r == 0),
        ("T4", "the first word is compared whole: 'who' is not 'who.am.i'", lambda e, r: NOTALLOWED in e and r == 0),
        ("T5", "a semicolon in an argument is refused (11806): the command did not run", lambda e, r: CHAR in e and r == 0),
        ("T6", "a quote in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("T7", "a tab joins the next word to the first, which is then not in the list", lambda e, r: NOTALLOWED in e and r == 0),
        ("T8", "a value mark in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("T9", "an empty sentence is refused (11804)", lambda e, r: EMPTY in e and r == 0),
        ("T10", "a sentence of spaces is refused (11804)", lambda e, r: EMPTY in e and r == 0),
        ("T11", "a sentence of 600 characters is refused (11807)", lambda e, r: LONG in e and r == 0),
        ("T12", "a sentence of 42 words is refused (11807)", lambda e, r: LONG in e and r == 0),
        ("T13", "a sentence of exactly 40 words is run (the boundary)", lambda e, r: e == "" and r == 1),
        ("T14", "a backtick in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("T15", "a dollar sign in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("S1", "create.file with a second command after a semicolon is refused (11806)", lambda e, r: CHAR in e),
        ("S2", "CREATE.FILE in capitals is refused (11805)", lambda e, r: NOTALLOWED in e),
        ("S3", "create.file with a quoted word is refused (11806)", lambda e, r: CHAR in e),
        ("S4", "create.file zztkrunf dynamic, as the tool would build it, is run: no message", lambda e, r: e == ""),
    ]
    for tag, what, test in want:
        g = got.get(tag)
        row("%s: %s" % (tag, what), g is not None and test(g[1], g[2]), repr(g))
    row("THE SENTINEL: after S1, S2 and S3 (each would have made the file) the file zztkrunf does not exist", line(r"^SENT after-refusals ABSENT\s*$") is not None, out[-400:])
    row("...and after S4, which was allowed, it does (so the sentinel can fire)", line(r"^SENT after-run EXISTS\s*$") is not None, out[-400:])


# TK-0.3.  $tk_gates reads the sandbox's own register (sys/accounts) in an internal session.  The fixtures are records this suite writes and deletes (zztk*); the
# fields are the register's (keys.h): 1 path, 3 Linux group, 5 suspension, 7 sh, 8 os, 9 sd, 10 voc, 11 bp, 12 dict, 13 shared.read, 14 shared.write, 15 net.
IDS = ["ssh", "api", "sh", "os", "sd", "voc", "bp", "dict", "net", "shared-read", "shared-write", "files", "files-write", "files-admin", "sockets"]
ROUTE_GROUP = {"ssh": "sdssh", "api": "sdapi", "files": "sdfiles", "files-write": "sdfileswrite", "files-admin": "sdfilesadmin"}
REG = {"sh": 7, "os": 8, "sd": 9, "voc": 10, "bp": 11, "dict": 12, "shared-read": 13, "shared-write": 14, "net": 15}
#            name        group            suspension   values of fields 7 to 15 (sh os sd voc bp dict shared.read shared.write net)
FIXTURES = [("zztkon", "sdu_zztkon", "", "yes,yes,yes,yes,yes,yes,yes,yes,yes"),
            ("zztkoff", "sdu_zztkoff", "", "no,no,no,no,no,no,no,no,no"),
            ("zztkblank", "sdu_zztkblank", "", ",,,,,,,,"),
            ("zztkmix", "sdu_zztkmix", "SUSPENDED", "yes,no,,YES, yes ,maybe,No,Yes,no"),
            ("zztkgrp", "sdg_zztkgrp", "", "yes,,,,,,,,"),
            ("zztkoth", "plainname", "", "yes,,,,,,,,"),
            ("zztkreal", "sdu_@USER@", "", ",,,,,,,,"),
            ("ZZTKUP", "sdu_zztkup", "", "yes,yes,yes,yes,yes,yes,yes,yes,yes")]       # registered under an upper-case name: only the name check can refuse it
SHOWS = [("on", "zztkon"), ("off", "zztkoff"), ("blank", "zztkblank"), ("mix", "zztkmix"), ("grp", "zztkgrp"), ("oth", "zztkoth"), ("real", "zztkreal"),
         ("none", "zznone"), ("upper", "ZZTKON"), ("upfix", "ZZTKUP"), ("empty", ""), ("quote", "a'b"), ("semi", "zztkon;x")]


def gates_program(user):
    p = ["$internal", "   crt 'TKG begin'", "   openpath @sdsys:@ds:'accounts' to f else crt 'TKG noreg' ; stop"]
    for nm, grp, sus, vals in FIXTURES:
        p.append("   nm = '%s' ; grp = '%s' ; sus = '%s' ; vals = '%s' ; gosub mk" % (nm, grp.replace("@USER@", user), sus, vals))
    for tag, nm in SHOWS:
        p.append('   tag = "%s" ; nm = "%s" ; gosub show' % (tag, nm))
    p.append("   read x from f, 'ZZTKON' then crt 'TKG upper-found' else crt 'TKG upper-missing'")
    p.append("   read x from f, 'ZZTKUP' then crt 'TKG up-found' else crt 'TKG up-missing'")
    for nm, grp, sus, vals in FIXTURES:
        p.append("   delete f, '%s'" % nm)
    for nm, grp, sus, vals in FIXTURES:
        p.append("   read x from f, '%s' then crt 'TKG left %s'" % (nm, nm))
    p += ["   crt 'TKG end'", "   stop",
          "mk:", "   rec = ''", "   rec<1> = '/tmp/' : nm", "   rec<2> = 'tkgates fixture'", "   rec<3> = grp", "   rec<5> = sus",
          "   for k = 1 to 9", "      rec<6 + k> = field(vals, ',', k)", "   next k", "   write rec to f, nm", "   return",
          "show:", "   call $tk_gates(nm, g, info, err)",
          "   outl = 'G ' : tag : ' err=[' : err : '] type=' : info<1> : ' susp=' : info<2> : ' user=' : info<3> : ' |'",
          "   for k = 1 to dcount(g, @fm)", "      outl := ' ' : g<k, 1> : '=' : g<k, 2>", "   next k", "   crt outl", "   return", "end", ""]
    return "\n".join(p)


def etc_group_members(group):
    try:
        for ln in open("/etc/group", encoding="latin-1"):
            f = ln.rstrip("\n").split(":")
            if f[0] == group and len(f) > 3:
                return [m for m in f[3].split(",") if m]
    except OSError:
        pass
    return []


def gates_rows(box, made):
    import getpass
    user = getpass.getuser()
    say("\n--- $tk_gates: every gate of one account, read from the register (TK-0.3)")
    with open(os.path.join(box, "sys", "bp", "zztkgates"), "w", encoding="latin-1") as f:
        f.write(gates_program(user))
    made.append("zztkgates")
    out = sess(box, "BASIC bp zztkgates", "RUN bp zztkgates")
    if not re.search(r"^TKG begin\s*$", out, re.M) or not re.search(r"^TKG end\s*$", out, re.M):
        say(out[-1500:])
        bail("the TK-0.3 program did not run to its end, so no row below can be believed")
    got = {}
    for m in re.finditer(r"^G (\w+) err=\[(.*)\] type=(\w*) susp=(\w*) user=(\S*) \|(.*)$", out, re.M):
        got[m.group(1)] = (m.group(2), m.group(3), m.group(4), m.group(5), dict(x.split("=", 1) for x in m.group(6).split()))
    expect_routes = {i: ("1" if user in etc_group_members(g) else "0") for i, g in ROUTE_GROUP.items()}

    def states(tag):
        return got[tag][4] if tag in got else {}

    def reg_expect(vals, default_on_ids=("shared-read",)):
        out_ = {}
        for i, fno in REG.items():
            raw = vals[fno - 7].strip().upper()
            out_[i] = ("1" if raw != "NO" else "0") if i in default_on_ids else ("1" if raw == "YES" else "0")
        return out_

    v = {nm: vals.split(",") for nm, _g, _s, vals in FIXTURES}
    for tag, nm, typ, susp in (("on", "zztkon", "USER", "0"), ("off", "zztkoff", "USER", "0"), ("blank", "zztkblank", "USER", "0"), ("mix", "zztkmix", "USER", "1")):
        e = dict(reg_expect(v[nm]), sockets="", **{i: "0" for i in ROUTE_GROUP})
        g = got.get(tag)
        row("%s (%s): type USER, suspension %s, and all 15 gates in the table's order with the states the fields give: %s" % (tag, nm, susp, " ".join("%s=%s" % (i, e[i]) for i in IDS)),
            g is not None and g[0] == "" and g[1] == typ and g[2] == susp and g[3] == nm and states(tag) == e and list(states(tag)) == IDS, repr(g))
    row("blank means ON for shared-read only: the blank record has shared-read=1 and every other register gate 0", states("blank").get("shared-read") == "1" and all(states("blank").get(i) == "0" for i in REG if i != "shared-read"), repr(states("blank")))
    row("the word is read as upper case with spaces trimmed: ' yes ' and 'YES' are on, 'maybe' and an empty field are off, 'No' turns shared-read off", states("mix").get("bp") == "1" and states("mix").get("voc") == "1"
        and states("mix").get("dict") == "0" and states("mix").get("sd") == "0" and states("mix").get("shared-read") == "0", repr(states("mix")))
    e = dict(reg_expect(v["zztkgrp"]), sockets="", **{i: "na" for i in ROUTE_GROUP})
    row("a GROUP account (sdg_): type GROUP, the register gates from its fields and every route gate 'na' (a group has no person to be in a Linux group)",
        "grp" in got and got["grp"][0] == "" and got["grp"][1] == "GROUP" and got["grp"][3] == "" and states("grp") == e, repr(got.get("grp")))
    e = dict(reg_expect(v["zztkoth"]), sockets="", **{i: "na" for i in ROUTE_GROUP})
    row("an account whose group is neither (OTHER): the same, route gates 'na'", "oth" in got and got["oth"][1] == "OTHER" and states("oth") == e, repr(got.get("oth")))
    e = dict(reg_expect(v["zztkreal"]), sockets="", **expect_routes)
    members = [i for i, x in expect_routes.items() if x == "1"]
    row("the sandbox's own Linux user (%s): the route gates equal that user's membership in /etc/group (%s)" % (user, ("in " + ", ".join(ROUTE_GROUP[i] for i in members)) if members else "in none of the five groups"),
        "real" in got and got["real"][1] == "USER" and got["real"][3] == user and states("real") == e, repr(got.get("real")))
    if not members:
        skip("a route gate that is ON", "this user is in none of sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin on this machine: only the off side is seen here (the on side is the VM witness)")
    for tag, nm in (("none", "zznone"), ("empty", ""), ("quote", "a'b"), ("semi", "zztkon;x")):
        g = got.get(tag)
        row("%s: %r is refused with 11808 and nothing is returned" % (tag, nm), g is not None and "is not a registered account" in g[0] and g[1] == "" and g[4] == {}, repr(g))
    g = got.get("upper")
    say("    [measured] a plain READ of ZZTKON finds zztkon: %s (the register is read with case, so ZZTKON above is refused partly because nothing is called that)"
        % ("yes" if re.search(r"^TKG upper-found\s*$", out, re.M) else "no"))
    row("ZZTKON is refused with 11808 and nothing is returned", g is not None and "is not a registered account" in g[0] and g[4] == {}, repr(g))
    up = got.get("upfix")
    row("THE SENTINEL: ZZTKUP, a record that EXISTS under that exact upper-case name (a plain read finds it), is refused: only the name check can do that",
        re.search(r"^TKG up-found\s*$", out, re.M) is not None and up is not None and "is not a registered account" in up[0] and up[4] == {}, repr(up))
    row("...and the same record by its own name was answered a moment before (so the sentinel can fire)", "on" in got and got["on"][0] == "", "")
    row("the fixtures are gone: the program deleted the eight records it wrote, and a read of each afterwards finds none", re.search(r"^TKG left ", out, re.M) is None, out[-300:])


# TK-0.5 (G3).  `tktest table N` drives sl_table directly inside the toolkit frame: 12 rows by default, N rows when given.  The status line says where the table is
# (cur=<name> shown=<n> sort=<col>/<dir> filter=[<text>] marks=<names>), so a row reads the table's state from the screen, and the cells from the rows above it.
NAMES12 = ["delta", "alpha", "echo", "charlie", "bravo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo", "lima"]
CITIES = ["Albany", "Boston", "Chicago", "Denver", "Elgin", "Fresno"]
F_T = "F1 help  F3 sort  F4 filter  F6 refresh  Tab next  ^Q quit"
SLOW = 20.0            # seconds one table action may take on 6,000 rows: generous, the measured times are printed


def tdata(n):
    """The rows tool_tktest builds (t.build): name, quantity, check, city."""
    out = []
    for r in range(1, n + 1):
        nm = NAMES12[r - 1] if r <= 12 else "row%05d" % r
        out.append([nm, str((r * 7) % 100), str(r % 2), CITIES[r % 6]])
    return out


def trline(rw, lead=" "):
    chk = "[x] " if int(rw[2]) else "[ ] "
    return (lead + rw[0].ljust(14)[:14] + " " + rw[1].rjust(6) + " " + chk + " " + rw[3].ljust(10)[:10]).rstrip()


def tstate(t):
    m = re.search(r"cur=(\S*) shown=(\d+) sort=(\d+)/(\d+) filter=\[(.*?)\] marks=(\S*)", t.line(40))
    if not m:
        return None
    return {"cur": m.group(1), "shown": int(m.group(2)), "sort": (int(m.group(3)), int(m.group(4))), "filter": m.group(5), "marks": [x for x in m.group(6).split(",") if x]}


def tscreen(t, n):
    """The n rows of the table below its heading, as the screen shows them (the scroll bar column cut off)."""
    return [t.line(2 + i)[:69].rstrip() for i in range(n)]


def table_rows(box, made):
    say("\n--- the table additions (TK-0.5, G3): row styles, check cells, filter, refresh by key")
    d = tdata(12)
    t = Term(box, "tktest table")
    if "F1 help" not in "\n".join(t.lines()):
        say("\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
        bail("tktest table never drew its function-key row, so no row below can be believed")
    row("`tktest table` starts on pane T: the function-key row names F3, F4 and F6: %r" % F_T, t.line(42) == F_T, repr(t.line(42)))
    head = (" " + "Name".ljust(14) + " " + "Qty".rjust(6) + " " + " On " + " " + "City").rstrip()
    row("the heading names the four columns (the check column's heading centred in its four cells)", t.line(1)[:69].rstrip() == head, repr(t.line(1)[:69]))
    row("the twelve rows are drawn in the order of rows, a check cell is [x] for 1 and [ ] for 0, Qty is right-aligned (the first row has the focus)",
        tscreen(t, 12) == [trline(r, " ") for r in d] and t.line(14)[:69].strip() == "", repr(tscreen(t, 12)))
    st = tstate(t)
    row("the status line starts: current row delta, 12 shown, not sorted, no filter, nothing marked", st == {"cur": "delta", "shown": 12, "sort": (0, 0), "filter": "", "marks": []}, repr(st))
    sc = t.s.screen
    say("    [measured] in the default theme (mono) a 'disabled' row (charlie) is drawn %r, a plain row %r: mono draws 'disabled' and 'error' as text, so a row style shows only in a colour theme" % (sc.style(5, 3), sc.style(3, 3)))

    t.key("F4")
    row("F4 asks for a filter (a small entry box titled Filter)", "Filter" in "\n".join(t.lines()), "\n".join(t.lines())[-300:])
    t.s.type("an\r", idle=0.8)
    want = [r for r in d if any("an" in c.lower() for c in r)]
    st = tstate(t)
    say("    [measured] rows holding 'an' (in any cell, any case): %s" % ", ".join(r[0] for r in want))
    row("filter 'an': only the rows that hold it are shown, in their order, nothing else on the rows below; the status says %d shown and the filter" % len(want),
        tscreen(t, len(want)) == [trline(r, " ") for r in want] and t.line(2 + len(want))[:69].strip() == "" and st is not None and st["shown"] == len(want) and st["filter"] == "an"
        and st["cur"] == want[0][0], repr((tscreen(t, len(want) + 1), st)))
    t.key("F3")
    st = tstate(t)
    srt = sorted(want, key=lambda r: r[0].lower())
    row("F3 sorts the filtered rows by Name: still only those rows, now in name order; sort 1/1", tscreen(t, len(srt)) == [trline(r, " ") for r in srt] and st["sort"] == (1, 1) and st["shown"] == len(want), repr((tscreen(t, len(srt)), st)))
    t.key("F3")
    srt = sorted(want, key=lambda r: r[0].lower(), reverse=True)
    row("F3 again: name order reversed, filter kept; sort 1/2", tscreen(t, len(srt)) == [trline(r, " ") for r in srt] and tstate(t)["sort"] == (1, 2), repr(tscreen(t, len(srt))))
    t.key("F3")
    row("F3 a third time: the order of rows again (sort 0/0), the filter still in force", tscreen(t, len(want)) == [trline(r, " ") for r in want] and tstate(t)["sort"] == (0, 0) and tstate(t)["filter"] == "an", repr(tstate(t)))
    t.key("F4")
    t.s.type("\x15zzz\r", idle=0.8)
    st = tstate(t)
    row("a filter nothing matches (zzz): no rows, shown 0, no current row", st is not None and st["shown"] == 0 and st["cur"] == "" and t.line(2)[:69].strip() == "", repr((st, t.line(2)[:69])))
    t.key("F4")
    t.s.type("\x15\r", idle=0.8)
    st = tstate(t)
    row("an empty filter: all twelve rows are back, in the order of rows", tscreen(t, 12) == [trline(r, " ") for r in d] and st["shown"] == 12 and st["filter"] == "", repr(st))

    # sort, mark two rows, then new rows (a sort keeps the current row, so Home first)
    t.key("F3")
    t.key("HOME")
    t.key("DOWN")
    t.key("DOWN")
    t.key("SPACE")
    t.key("DOWN")
    t.key("DOWN")
    t.key("SPACE")
    t.key("UP")
    st = tstate(t)
    row("sorted by Name, delta current, charlie and echo marked", st == {"cur": "delta", "shown": 12, "sort": (1, 1), "filter": "", "marks": ["charlie", "echo"]}, repr(st))
    t.key("F6")
    nd = [["mike", "55", "1", "Boston"]]
    for r in reversed(d):
        if r[0] != "bravo":
            nd.append([r[0], "99" if r[0] == "echo" else r[1], r[2], r[3]])
    snd = sorted(nd, key=lambda r: r[0].lower())
    st = tstate(t)
    marks = [m for m in ("charlie", "echo")]
    lines = tscreen(t, 12)
    row("F6 gives new rows (bravo gone, mike new, echo's quantity 99, the old order reversed): shown in the SORT in force (Name, up), not in the order they were given",
        lines == [trline(r, "*" if r[0] in marks else " ") for r in snd], repr(lines))
    row("...and the current row is still delta, the marks are still charlie and echo (kept by the key although their places changed), the sort is still Name up, 12 shown",
        st == {"cur": "delta", "shown": 12, "sort": (1, 1), "filter": "", "marks": ["charlie", "echo"]}, repr(st))
    t.end()

    # the row styles, in a theme that draws them (classic: 'disabled' and 'error' have colours of their own)
    t = Term(box, "tktest table 12 classic")
    sc = t.s.screen
    names0 = [r[0] for r in d]
    srow = lambda nm: 2 + names0.index(nm)
    plain, dis = sc.style(srow("golf"), 3), sc.style(srow("charlie"), 3)
    say("    [measured] classic: a plain row %r, a 'disabled' row (charlie, Elgin) %r" % (plain, dis))
    row("classic theme: the row with the rowstyle 'disabled' (charlie) is drawn in that style, the rows around it (bravo, echo) and the rest are drawn in the text style",
        dis != plain and sc.style(srow("bravo"), 3) == plain == sc.style(srow("echo"), 3) == sc.style(srow("lima"), 3), repr((plain, dis, sc.style(srow("bravo"), 3), sc.style(srow("echo"), 3))))
    t.key("F6")
    nm_now = [r[0] for r in [["mike"]] + [r for r in reversed(d) if r[0] != "bravo"]]
    srow2 = lambda nm: 2 + nm_now.index(nm)
    sc = t.s.screen
    plain2 = sc.style(srow2("golf"), 3)
    kind = {nm: ("plain" if sc.style(srow2(nm), 3) == plain2 else "disabled" if sc.style(srow2(nm), 3) == dis else "other") for nm in nm_now}
    say("    [measured] row styles after F6 (rows are in the new order): %s" % ", ".join("%s %s" % (nm, kind[nm]) for nm in nm_now))
    row("after F6 the new rowstyle went with the new rows, each at its NEW place: charlie and juliet (both in Elgin) 'disabled', echo (quantity 99) in a style of its own ('error'), "
        "every other row (mike, new, included) plain",
        all(kind[nm] == "disabled" for nm in ("charlie", "juliet")) and kind["echo"] == "other" and all(kind[nm] == "plain" for nm in nm_now if nm not in ("charlie", "juliet", "echo", "delta")), repr(kind))
    row("...(delta, the current row, which the refresh moved to the last place, is in the highlight style, as it is the row with the focus)", kind["delta"] == "other" and sc.style(srow2("delta"), 3) != sc.style(srow2("echo"), 3), repr(kind["delta"]))
    t.key("F3")
    nm_sorted = sorted(nm_now, key=str.lower)
    sc = t.s.screen
    kind = {nm: ("plain" if sc.style(2 + nm_sorted.index(nm), 3) == plain2 else "disabled" if sc.style(2 + nm_sorted.index(nm), 3) == dis else "other") for nm in nm_sorted}
    row("sorted by Name the row styles follow the ROWS, not the places on the screen: charlie and juliet 'disabled', echo 'error', the rest plain (delta is current)",
        all(kind[nm] == "disabled" for nm in ("charlie", "juliet")) and kind["echo"] == "other" and all(kind[nm] == "plain" for nm in nm_sorted if nm not in ("charlie", "juliet", "echo", "delta")), repr(kind))
    t.end()

    # the current row is the one that goes
    t = Term(box, "tktest table")
    t.key("F3")
    t.key("HOME")
    t.key("DOWN")
    st0 = tstate(t)
    t.key("F6")
    st = tstate(t)
    row("when the current row is the one that is gone (bravo, second in name order) the current row is the one now in its place (charlie)", st0["cur"] == "bravo" and st is not None and st["cur"] == "charlie" and st["sort"] == (1, 1), repr((st0, st)))
    t.end()

    # six thousand rows
    say("    --- 6,000 rows")
    t0 = time.time()
    t = Term(box, "tktest table 6000")
    t_start = time.time() - t0
    big = tdata(6000)
    st = tstate(t)
    say("    [measured] start with 6,000 rows: %.1f s" % t_start)
    row("6,000 rows: the first screenful is drawn and the status says 6000 shown", st is not None and st["shown"] == 6000 and tscreen(t, 19) == [trline(r, " ") for r in big[:19]], repr((st, tscreen(t, 3))))

    def timed(name, send, cond):
        """Type the keys without waiting for quiet, then poll the screen until cond holds: the time is until the screen says so (a sort is SD working, not writing)."""
        t1 = time.time()
        send()
        el = SLOW + 10
        while time.time() - t1 < SLOW + 10:
            t.s.settle(0.25)
            s_ = tstate(t)
            if s_ is not None and cond(s_):
                el = time.time() - t1
                break
        say("    [measured] %s: %.1f s until the status line said so (the harness's own settling adds about 0.25 s)" % (name, el))
        row("%s: the screen says so within %.0f s" % (name, SLOW), el < SLOW, "%.1f s, status %r" % (el, tstate(t)))
        return el

    def typ(*names):
        t.s.type("".join(KEYS[n] for n in names), settle=False)

    timed("F3 sort by Name", lambda: typ("F3"), lambda s_: s_["sort"] == (1, 1))
    t.s.settle(0.5)
    row("...the rows are in name order from the top: alpha first (delta, the current row, is the fourth)", t.line(2)[:69].rstrip().startswith(" alpha") and tstate(t)["cur"] == "delta", repr((t.line(2)[:40], tstate(t))))
    timed("End (last row)", lambda: typ("END"), lambda s_: s_["cur"] == "row06000")
    t.key("UP")
    t.key("SPACE")
    st = tstate(t)
    row("the last but one row marked", st is not None and st["marks"] == ["row05999"] and st["cur"] == "row05999", repr(st))
    timed("F6 refresh", lambda: typ("F6"), lambda s_: s_["cur"] == "row05999" and s_["marks"] == ["row05999"] and s_["shown"] == 6000 and s_["sort"] == (1, 1))
    t.s.settle(0.5)
    last = [l[:69].rstrip() for l in t.lines()[2:22]]
    row("...the current row and the mark are kept by the key, the sort too, and the current row is where it was in the window (the last rows are on the screen)",
        any("row05999" in l for l in last) and any("row06000" in l for l in last) and any(l.startswith("*row05999") for l in last), repr(last[-4:]))
    nmatch = len([r for r in big if "row0059" in r[0]])
    t.key("F4")
    timed("filter row0059 (%d rows match)" % nmatch, lambda: t.s.type("row0059\r", settle=False), lambda s_: s_["filter"] == "row0059" and s_["shown"] == nmatch)
    row("...the mark stays on the row the filter hides... or shows: it is KEPT (marks stay on rows the filter hides)", tstate(t) is not None and tstate(t)["marks"] == ["row05999"], repr(tstate(t)))
    t.end()


# TK-0.6 (G1).  `tktest pick N` opens the pick window (sl_pickwin) over N entries on F9 (one) and F10 (several) and puts what was chosen in the status line
# ("picked 8 (who)", "picked 1,3 (list,count)", "cancelled").  The window's geometry is worked out here from the same rules and the rows are read from the screen.
PV = "list,sort,count,copy,delete.file,create.file,modify.account,who,listu,logto,catalog,basic".split(",")
PD = ["show records of a file", "show records in order", "count the records", "copy records to a file", "remove a file", "make a file", "change an account", "who is signed on",
      "list the users", "enter another account", "make a program a command", "compile a program"]
PH = ["LIST shows the records of a file on the screen", "SORT is LIST in the order of an attribute", "COUNT says how many records match", "COPY puts records into another file",
      "DELETE.FILE removes a file and its dictionary", "CREATE.FILE makes a file and a dictionary for it", "MODIFY.ACCOUNT changes the gates of an account",
      "WHO says who is signed on and as whom", "LISTU lists the users signed on", "LOGTO enters another account", "CATALOG makes a program a command", "BASIC compiles a program"]
F_P = "F1 help  F9 pick  F10 multi  F11 file  F12 files  Tab next  ^Q quit"


def pitems(n):
    out = []
    for q in range(1, n + 1):
        if q <= 12:
            out.append([PV[q - 1], PD[q - 1], PH[q - 1]])
        else:
            out.append(["item%05d" % q, "the %dth entry" % q, "help for item %d" % q])
    return out


def pgeom(items, multi, title="Pick a command", scrw=140, scrh=43):
    nw = min(30, max(4, max(len(i[0]) for i in items)))
    dw = max(len(i[1]) for i in items)
    lead = 4 if multi else 1
    lh = max(3, min(len(items), max(3, scrh - 8)))
    lw = min(scrw - 4, max(lead + nw + 2 + dw + 1, 44, len(title) + 4))
    bw, bh = lw + 2, lh + 4
    bx, by = (scrw - bw) // 2, (scrh - bh) // 2
    return dict(nw=nw, lead=lead, lh=lh, lw=lw, bw=bw, bh=bh, bx=bx, by=by, x0=bx + 1, yf=by + 1, y1=by + 2, yh=by + 2 + lh)


def prowtext(it, g, multi, picked=False, bar=False):
    tw = g["lw"] - (1 if bar else 0)
    lead = ("[x] " if picked else "[ ] ") if multi else " "
    return (lead + it[0][:g["nw"]].ljust(g["nw"]) + "  " + it[1])[:tw].rstrip()


def pmatch(items, f):
    return [i for i, it in enumerate(items) if f.lower() in (it[0] + " " + it[1]).lower()]


def pfl(t, g):
    """The filter line of the window without the border: the text inside, trailing spaces off."""
    return t.line(g["yf"])[g["x0"]:g["x0"] + g["lw"]].rstrip()


def pshow(t, g, items, idx, multi=False, picked=(), bar=None):
    """The rows of the window as the screen shows them, compared with the entries idx (indices into items) in order.  bar: the scroll bar column is there (by default
    when the entries shown are more than the rows; pass True when the window is scrolled to the last rows)."""
    if bar is None:
        bar = len(idx) > g["lh"]
    want = [prowtext(items[i], g, multi, i in picked, bar) for i in idx[:g["lh"]]]
    got = [t.line(g["y1"] + r)[g["x0"]:g["x0"] + g["lw"] - (1 if bar else 0)].rstrip() for r in range(len(want))]
    return got == want, got, want


def pick_rows(box, made):
    say("\n--- the pick window (TK-0.6, G1): type to narrow, two columns, a help line, several picks")
    its = pitems(12)
    g = pgeom(its, False)
    t = Term(box, "tktest pick")
    if "F1 help" not in "\n".join(t.lines()):
        say("\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
        bail("tktest pick never drew its function-key row, so no row below can be believed")
    row("`tktest pick` starts on pane P: the function-key row names F9 and F10: %r" % F_P, t.line(42) == F_P, repr(t.line(42)))
    t.key("F9")
    scr_ = lambda: t.lines()
    ok, got, want = pshow(t, g, its, list(range(12)))
    row("F9 opens the window: the title in the top border, the filter line (label, empty field, '12 of 12'), and all twelve entries in two columns (name, then description)",
        "Pick a command" in t.line(g["by"]) and t.line(g["by"])[g["bx"]] == "+" and t.line(g["yf"])[g["x0"]:g["x0"] + g["lw"]].startswith(" filter:") and pfl(t, g).endswith("12 of 12") and ok,
        repr((t.line(g["by"])[g["bx"]:g["bx"] + 30], t.line(g["yf"])[g["bx"]:g["bx"] + g["bw"]], got[:2], want[:2])))
    row("the first entry is the current one, in reverse video; the help line holds the reminder that ? gives help", t.rev(g["y1"]) is not None and "list" in t.rev(g["y1"]) and "sort" not in t.rev(g["y1"]) and "? shows help" in t.line(g["yh"]),
        repr((t.rev(g["y1"]), t.line(g["yh"])[g["x0"]:g["x0"] + 60])))
    t.s.type("li", idle=0.6)
    idx = pmatch(its, "li")
    ok, got, want = pshow(t, g, its, idx)
    say("    [measured] entries holding 'li' in the name or the description: %s" % ", ".join(its[i][0] for i in idx))
    row("typing 'li' narrows the list to the entries that hold it in the name OR the description (%d of 12), in their order; the filter line says so; the window did not change size"
        % len(idx), ok and pfl(t, g).endswith("%d of 12" % len(idx)) and "filter: li" in t.line(g["yf"]) and t.line(g["by"] + g["bh"] - 1)[g["bx"]] == "+"
        and t.line(g["y1"] + len(idx))[g["x0"]:g["x0"] + g["lw"]].strip() == "", repr((got, want, t.line(g["yf"])[g["x0"]:g["x0"] + g["lw"]])))
    t.s.type("\x7f", idle=0.6)
    idx = pmatch(its, "l")
    ok, got, want = pshow(t, g, its, idx)
    row("Backspace widens it: 'l' (%d entries)" % len(idx), ok and "filter: l" in t.line(g["yf"]) and "filter: li" not in t.line(g["yf"]), repr((got, want)))
    t.s.type("\x15", idle=0.6)
    ok, got, want = pshow(t, g, its, list(range(12)))
    row("Ctrl-U empties the filter: all twelve again", ok and pfl(t, g).endswith("12 of 12"), repr((got, want)))
    t.s.type("signed", idle=0.6)
    ok, got, want = pshow(t, g, its, pmatch(its, "signed"))
    row("'signed' is in one description only (who): the list is that one entry", ok and len(pmatch(its, "signed")) == 1 and pfl(t, g).endswith("1 of 12"), repr((got, want)))
    t.key("ENTER")
    row("Enter answers the number of the entry IN THE LIST (8), not its place among the entries shown (1): the status line says picked 8 (who); the window is gone and the foot of the screen is back",
        "picked 8 (who)" in t.line(40) and "Pick a command" not in "\n".join(t.lines()) and t.line(42) == F_P and t.line(41) == "-" * 140, repr((t.line(40), t.line(42))))

    t.key("F9")
    t.s.type("zzz", idle=0.6)
    row("a filter nothing matches: no entries, 'nothing matches' in the first row, '0 of 12'", "nothing matches" in t.line(g["y1"]) and pfl(t, g).endswith("0 of 12"), repr((t.line(g["y1"]), t.line(g["yf"]))))
    t.key("ENTER")
    row("Enter with nothing shown does nothing: the window is still open", "Pick a command" in "\n".join(t.lines()), "")
    t.key("ESC")
    row("Esc closes it: the status line says cancelled, the screen under the window is back", "cancelled" in t.line(40) and "Pick a command" not in "\n".join(t.lines()) and t.line(42) == F_P, repr((t.line(40), t.line(42))))

    t.key("F9")
    t.key("DOWN")
    t.key("DOWN")
    t.s.type("?", idle=0.6)
    row("? shows the help of the entry the person is on (count): on the help line, and the ? did not go into the filter",
        PH[2] in t.line(g["yh"]) and "filter:" in t.line(g["yf"]) and "?" not in t.line(g["yf"]).replace("? ", ""), repr((t.line(g["yh"])[g["x0"]:g["x0"] + 70], t.line(g["yf"])[g["x0"]:g["x0"] + 40])))
    t.key("DOWN")
    row("the help follows the highlight: the next entry (copy)", PH[3] in t.line(g["yh"]), repr(t.line(g["yh"])[g["x0"]:g["x0"] + 70]))
    t.s.type("?", idle=0.6)
    row("? again hides it: the reminder is back", "? shows help" in t.line(g["yh"]) and PH[3] not in t.line(g["yh"]), repr(t.line(g["yh"])[g["x0"]:g["x0"] + 70]))
    t.key("ENTER")
    row("Enter on the fourth entry: picked 4 (copy)", "picked 4 (copy)" in t.line(40), repr(t.line(40)))

    # several
    gm = pgeom(its, True, "Pick commands")
    t.key("F10")
    ok, got, want = pshow(t, gm, its, list(range(12)), True)
    row("F10 opens the window for several: each entry starts [ ]", ok, repr((got[:2], want[:2])))
    t.key("SPACE")
    t.key("DOWN")
    t.key("DOWN")
    t.key("SPACE")
    ok, got, want = pshow(t, gm, its, list(range(12)), True, picked=(0, 2))
    row("Space picks the entry it is on: list and count are [x] (the space did not go into the filter), the first line says 2 marked", ok and pfl(t, gm).endswith("2 marked  12 of 12"), repr((got[:4], want[:4], t.line(gm["yf"]).rstrip()[-30:])))
    t.s.type("o", idle=0.6)
    idx = pmatch(its, "o")
    ok, got, want = pshow(t, gm, its, idx, True, picked=(0, 2))
    row("a filter ('o') hides some entries; the marks stay on the entries (list and count, if shown, are [x]) and the count still says 2 marked", ok and "2 marked" in t.line(gm["yf"]), repr((got, want)))
    t.s.type("\x15", idle=0.6)
    t.key("ENTER")
    row("Enter answers the entries picked, by their numbers in the list, in the order they were picked: picked 1,3 (list,count)", "picked 1,3 (list,count)" in t.line(40), repr(t.line(40)))
    t.key("F10")
    t.key("DOWN")
    t.key("ENTER")
    row("Enter with nothing picked answers the entry the person is on: picked 2 (sort)", "picked 2 (sort)" in t.line(40), repr(t.line(40)))
    t.key("F10")
    t.key("SPACE")
    t.s.type("who", idle=0.6)
    t.key("ENTER")
    row("a mark on an entry the filter hides still counts: list was picked, 'who' was typed, Enter answers the PICK (1) and not the entry shown (8)", "picked 1 (list)" in t.line(40), repr(t.line(40)))

    t.key("F10")
    t.s.type("who", idle=0.6)
    t.key("SPACE")
    t.s.type("\x15", idle=0.6)
    ok, got, want = pshow(t, gm, its, list(range(12)), True, picked=(7,))
    row("a pick made while the filter shows the entry at another place is the ENTRY's: with 'who' typed (place 1) it was picked, with the filter emptied it is who (8) that is [x], and no other",
        ok and "1 marked" in pfl(t, gm), repr((got, want)))
    t.key("ENTER")
    row("...and Enter answers 8 (who), not 1", "picked 8 (who)" in t.line(40), repr(t.line(40)))

    # the mouse
    t.key("F9")
    xy = lambda r_: (gm["x0"] + 3, g["y1"] + r_)
    def click(x, y, rel=True):
        t.s.type("\x1b[<0;%d;%dM" % (x + 1, y + 1) + ("\x1b[<0;%d;%dm" % (x + 1, y + 1) if rel else ""), idle=0.6)
    click(g["x0"] + 3, g["y1"] + 2)
    row("a click on the third entry makes it current (reverse video on count); the window stays open", "count" in t.rev(g["y1"] + 2) and "Pick a command" in "\n".join(t.lines()), repr(t.rev(g["y1"] + 2)))
    click(g["x0"] + 3, g["y1"] + 2)
    row("a second click on it is Enter: picked 3 (count)", "picked 3 (count)" in t.line(40) and "Pick a command" not in "\n".join(t.lines()), repr(t.line(40)))
    t.key("F9")
    click(2, 3)
    row("a click outside the window is Esc: cancelled", "cancelled" in t.line(40) and "Pick a command" not in "\n".join(t.lines()), repr(t.line(40)))
    t.end()

    # more entries than rows: a scroll bar, End, the last entry
    its100 = pitems(100)
    g100 = pgeom(its100, False)
    t = Term(box, "tktest pick 100")
    t.key("F9")
    ok, got, want = pshow(t, g100, its100, list(range(100)))
    row("100 entries in %d rows: the first %d are shown and the right-hand column is a scroll bar (^ at the top, v at the bottom)" % (g100["lh"], g100["lh"]),
        ok and t.line(g100["y1"])[g100["x0"] + g100["lw"] - 1] == "^" and t.line(g100["y1"] + g100["lh"] - 1)[g100["x0"] + g100["lw"] - 1] == "v", repr((got[:2], want[:2], t.line(g100["y1"])[g100["x0"]:g100["x0"] + g100["lw"]])))
    t.key("END")
    ok, got, want = pshow(t, g100, its100, list(range(100 - g100["lh"], 100)), bar=True)
    row("End: the last entry is current and the window has scrolled to the last %d" % g100["lh"], ok and "item00100" in t.rev(g100["y1"] + g100["lh"] - 1), repr((got[-2:], want[-2:])))
    t.s.type("\x15", idle=0.5)
    t.s.type("item0005", idle=0.6)
    row("typing 'item0005' leaves item00050 to item00059: ten entries, no scroll bar any more", pshow(t, g100, its100, pmatch(its100, "item0005"))[0] and pfl(t, g100).endswith("10 of 100"), repr(pshow(t, g100, its100, pmatch(its100, "item0005"))[1:]))
    t.key("ENTER")
    row("Enter answers 50 (the number in the list of the first entry shown)", "picked 50 (item00050)" in t.line(40), repr(t.line(40)))
    t.end()

    # five thousand entries
    its5k = pitems(5000)
    g5k = pgeom(its5k, False)
    t0 = time.time()
    t = Term(box, "tktest pick 5000")
    say("    [measured] start with 5,000 entries: %.1f s" % (time.time() - t0))

    def waitfor(cond, limit=SLOW + 10):
        t1 = time.time()
        while time.time() - t1 < limit:
            t.s.settle(0.25)
            if cond():
                return time.time() - t1
        return limit

    t.s.type(KEYS["F9"], settle=False)
    el = waitfor(lambda: "Pick a command" in "\n".join(t.lines()))
    say("    [measured] F9 over 5,000 entries until the window is drawn: %.1f s" % el)
    row("F9 over 5,000 entries: the window is drawn within %.0f s" % SLOW, el < SLOW, "%.1f s" % el)
    t.s.type("item049", settle=False)
    want5k = pmatch(its5k, "item049")
    el = waitfor(lambda: pfl(t, g5k).endswith("%d of 5000" % len(want5k)))
    say("    [measured] typing 'item049' (%d match) over 5,000 entries: %.1f s" % (len(want5k), el))
    row("typing a filter over 5,000 entries: %d entries shown within %.0f s" % (len(want5k), SLOW), el < SLOW, "%.1f s, %r" % (el, t.line(g5k["yf"]).rstrip()[-30:]))
    t.s.type(KEYS["END"] + KEYS["ENTER"], settle=False)
    el = waitfor(lambda: "picked" in t.line(40))
    row("End, Enter: the last of the matches is answered by its number in the list (%d)" % (want5k[-1] + 1), "picked %d (%s)" % (want5k[-1] + 1, its5k[want5k[-1]][0]) in t.line(40), repr(t.line(40)))
    t.end()

    # a pipe: F9, then the input ends with the window open
    say("    --- on a pipe: F9, then the input ends with the window open")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
    t0 = time.time()
    try:
        outp, _ = p.communicate(b"\nTERM 140,43\ntktest pick\n\x1b[20~", timeout=20)
        ended = True
    except subprocess.TimeoutExpired:
        os.kill(p.pid, 1)
        time.sleep(1)
        p.kill()
        outp, _ = p.communicate()
        ended = False
    took = time.time() - t0
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    seen = b"Pick a command" in outp
    say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s, the window was drawn on the pipe: %s" % (ended, took, cpu, "yes" if seen else "no"))
    row("a piped session whose input ends with the window open ends within 20 s and does not spin (under 3 s of CPU): the end of the input is Esc", ended and cpu < 3.0, "%.1f s, %.2f s" % (took, cpu))
    if not seen:
        skip("the window was open when the input ended", "the pipe did not decode F9 into the key, so the window was never drawn")


# TK-0.8.  `tktest slider` shows a form with two SCREEN SLIDER switches and a check box; the label under them reads "sh=<v> os=<v> chk=<v> last=<id>=<v> n=<changes>" (n counts
# the change events of SCREEN WAIT, so a Left on a switch that is already off, which must report nothing, is seen as n not moving).  F2 sets the switches from the program.
def slider_rows(box, made):
    say("\n--- the slider, an on / off switch (TK-0.8)")
    t = Term(box, "tktest slider")

    def where(txt):
        for r_, l_ in enumerate(t.lines()):
            c_ = l_.find(txt)
            if c_ >= 0:
                return r_, c_
        return None

    def logline():
        m_ = re.search(r"sh=(\d) os=(\d) chk=(\d) last=(\S+) n=(\d+)", "\n".join(t.lines()))
        return m_.groups() if m_ else None

    if where("Shell (sh)") is None:
        say("\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
        bail("tktest slider never drew its form, so no row below can be believed")
    row("the form is drawn: sh is off ([O--]), os starts on ([==O], VALUE 1), the plain check box is [ ], the label reads sh=0 os=1 chk=0 last=none n=0",
        where("[O--] Shell (sh)") is not None and where("[==O] OS.EXECUTE") is not None and where("[ ] a plain check box") is not None and logline() == ("0", "1", "0", "none", "0"), repr((logline(), t.line(8)[40:92])))
    r1, c1 = where("[O--] Shell (sh)") or (0, 0)
    row("the first switch has the focus: its text is in reverse video and the second's is not", "Shell" in t.rev(r1) and "OS.EXECUTE" not in t.rev(r1), repr(t.rev(r1)))
    t.key("SPACE")
    row("Space slides it the other way: sh is on ([==O] Shell (sh)); one change event: last=sh=1 n=1", where("[==O] Shell (sh)") is not None and where("[O--] Shell (sh)") is None and logline() == ("1", "1", "0", "sh=1", "1"), repr(logline()))
    t.key("LEFT")
    row("Left slides it off ([O--]); n=2", where("[O--] Shell (sh)") is not None and logline() == ("0", "1", "0", "sh=0", "2"), repr(logline()))
    t.key("LEFT")
    row("Left again on a switch that is already off changes nothing and reports nothing: n is still 2", where("[O--] Shell (sh)") is not None and logline() == ("0", "1", "0", "sh=0", "2"), repr(logline()))
    t.key("RIGHT")
    t.key("RIGHT")
    row("Right slides it on, a second Right changes nothing: [==O] Shell (sh), n=3", where("[==O] Shell (sh)") is not None and logline() == ("1", "1", "0", "sh=1", "3"), repr(logline()))
    t.key("TAB")
    r2, c2 = where("[==O] OS.EXECUTE") or (0, 0)
    row("Tab moves the focus to the second switch: its text is in reverse video, the first's is not, no change event (n=3)", "OS.EXECUTE" in t.rev(r2) and "Shell" not in t.rev(r1) and logline()[4] == "3", repr((t.rev(r2), logline())))
    t.key("LEFT")
    row("Left on it slides os off ([O--] OS.EXECUTE); n=4", where("[O--] OS.EXECUTE") is not None and logline() == ("1", "0", "0", "os=0", "4"), repr(logline()))
    t.key("TAB")
    t.key("SPACE")
    row("Tab to the check box and Space: it is [x] (the check box still works beside the switches); n=5", where("[x] a plain check box") is not None and logline() == ("1", "0", "1", "chk=1", "5"), repr(logline()))
    r2, c2 = where("[O--] OS.EXECUTE") or where("[==O] OS.EXECUTE") or (0, 0)
    t.s.type("\x1b[<0;%d;%dM\x1b[<0;%d;%dm" % (c2 + 3, r2 + 1, c2 + 3, r2 + 1), idle=0.6)
    click = lambda: t.s.type("\x1b[<0;%d;%dM\x1b[<0;%d;%dm" % (c2 + 3, r2 + 1, c2 + 3, r2 + 1), idle=0.6)
    row("a click on the second switch, which has not the focus, slides it the other way (os is on again, [==O] OS.EXECUTE) and gives it the focus: the form reports the FOCUS, as for a check box, so n is still 5",
        where("[==O] OS.EXECUTE") is not None and logline() == ("1", "1", "1", "chk=1", "5") and "OS.EXECUTE" in t.rev(r2), repr((logline(), t.rev(r2))))
    click()
    row("a second click, now that it has the focus, slides it off again ([O--]) and is a change event: n=6, last=os=0", where("[O--] OS.EXECUTE") is not None and logline() == ("1", "0", "1", "os=0", "6"), repr(logline()))
    click()
    row("a third click slides it on: n=7, last=os=1", where("[==O] OS.EXECUTE") is not None and logline() == ("1", "1", "1", "os=1", "7"), repr(logline()))
    t.key("F2")
    row("SCREEN SET ... VALUE from the program: F2 sets sh to 5 (any non-zero is on: SCREEN GET answers 1, not 5) and os to 0 ([O--]); the switches are redrawn and no change event is made (n is still 7)",
        where("[==O] Shell (sh)") is not None and where("[O--] OS.EXECUTE") is not None and logline() == ("1", "0", "1", "set", "7"), repr(logline()))
    t.key("ENTER")
    row("Enter (the switch does not take it) presses the form's default button: the form is gone and the status line says sliders sh=1 os=0 chk=1 pressed=ok",
        "sliders sh=1 os=0 chk=1 pressed=ok" in t.line(40) and where("Shell (sh)") is None, repr(t.line(40)))
    t.end()

    t = Term(box, "tktest slider")
    t.key("ESC")
    row("Esc is a cancel event: the form is gone and the status line says pressed=cancel with the values it had (sh=0 os=1 chk=0)", "sliders sh=0 os=1 chk=0 pressed=cancel" in t.line(40), repr(t.line(40)))
    t.end()

    say("    --- on a pipe: the input ends with the form up")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
    t0 = time.time()
    try:
        outp, _ = p.communicate(b"\nTERM 140,43\ntktest slider\n", timeout=20)
        ended = True
    except subprocess.TimeoutExpired:
        os.kill(p.pid, 1)
        time.sleep(1)
        p.kill()
        outp, _ = p.communicate()
        ended = False
    took = time.time() - t0
    r1_ = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1_.ru_utime - r0.ru_utime) + (r1_.ru_stime - r0.ru_stime)
    say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s, the form was drawn on the pipe: %s" % (ended, took, cpu, "yes" if b"Shell (sh)" in outp else "no"))
    row("a piped session whose input ends with the form up ends within 20 s and does not spin (under 3 s of CPU)", ended and cpu < 3.0, "%.1f s, %.2f s" % (took, cpu))


# TK-0.7 (G1, the paged source).  `tktest pick 12 50 1000` opens, on F11 (one record id) and F12 (several, with the first attribute as the description), the pick window over
# the record ids of the file zzpkfile (6,000 records rec00001 to rec06000, attribute 1 'shelf <n mod 50>'), reading a page of 50 at most 1,000 ids at a time.
PKPROG = """$internal
   execute 'create.file zzpkfile dynamic' capturing o1
   open 'zzpkfile' to f else crt 'PKF noopen' ; stop
   for n = 1 to 6000
      rec = 'shelf-' : mod(n, 50)
      write rec to f, 'rec' : str('0', 5 - len(n)) : n
   next n
   crt 'PKF done 6000'
end
"""
PKIDS = ["rec%05d" % q for q in range(1, 6001)]
PKDESC = {("rec%05d" % q): "shelf-%d" % (q % 50) for q in range(1, 6001)}


def pkgeom(multi, dfield, title, scrw=140, scrh=43):
    nw = 12
    dw = 30 if dfield else 0
    lead = 4 if multi else 1
    lh = max(3, scrh - 8)
    lw = min(scrw - 4, max(lead + nw + 2 + dw + 1, 44, len(title) + 4))
    bw, bh = lw + 2, lh + 4
    bx, by = (scrw - bw) // 2, (scrh - bh) // 2
    return dict(nw=nw, lead=lead, lh=lh, lw=lw, bw=bw, bh=bh, bx=bx, by=by, x0=bx + 1, yf=by + 1, y1=by + 2, yh=by + 2 + lh)


def pkrows(t, g, ids, multi=False, picked=(), dfield=False, bar=True):
    """The rows shown, compared with the ids given (the first lh of them): ok, got, want."""
    tw = g["lw"] - (1 if bar else 0)
    want = []
    for i in ids[:g["lh"]]:
        lead = ("[x] " if i in picked else "[ ] ") if multi else " "
        want.append((lead + i.ljust(g["nw"])[:g["nw"]] + "  " + (PKDESC[i] if dfield else ""))[:tw].rstrip())
    got = [t.line(g["y1"] + r)[g["x0"]:g["x0"] + tw].rstrip() for r in range(len(want))]
    return got == want, got, want


def pickfile_rows(box, made):
    say("\n--- the pick window over a file's record ids, a page at a time (TK-0.7, G1)")
    with open(os.path.join(box, "sys", "bp", "zztkpkf"), "w", encoding="latin-1") as f:
        f.write(PKPROG)
    made.append("zztkpkf")
    out = sess(box, "DELETE.FILE zzpkfile FORCE", "BASIC bp zztkpkf", "RUN bp zztkpkf")
    if not re.search(r"^PKF done 6000\s*$", out, re.M):
        say(out[-1200:])
        bail("the program that makes the 6,000 records of zzpkfile did not finish, so no row below can be believed")
    try:
        g = pkgeom(False, False, "Pick a record")
        t = Term(box, "tktest pick 12 50 1000")
        if "F1 help" not in "\n".join(t.lines()):
            bail("tktest pick never drew its function-key row, so no row below can be believed")
        row("the function-key row names F11 and F12: %r" % F_P, t.line(42) == F_P, repr(t.line(42)))
        t.key("F11")
        ok, got, want = pkrows(t, g, PKIDS)
        cnt = pfl(t, g)
        say("    [measured] the first line of the window: %r" % cnt[-30:])
        row("F11 opens the window over the file: title, the first %d ids in order (rec00001 ...), and only a page of 50 has been read: '50 or more shown', not 6000" % g["lh"],
            "Pick a record" in t.line(g["by"]) and ok and cnt.endswith("50 or more shown"), repr((got[:2], want[:2], cnt)))
        row("the scroll bar is there (more may come) and the first id is current", t.line(g["y1"])[g["x0"] + g["lw"] - 1] == "^" and "rec00001" in t.rev(g["y1"]), repr(t.rev(g["y1"])))
        t.key("DOWN")
        t.s.type(KEYS["DOWN"] * 20, idle=0.6)
        for _ in range(3):
            t.key("PGDN")
        m = re.search(r"(\d+) or more shown", pfl(t, g))
        say("    [measured] after 21 Downs and 3 Page Downs: %s" % (m.group(0) if m else pfl(t, g)[-30:]))
        row("moving down reads more only as the cursor nears the end of what has been read: the count has grown past 50 and is far under 6000 (the cursor is on about row 100)",
            m is not None and 100 <= int(m.group(1)) < 1000, repr(pfl(t, g)[-30:]))
        t0 = time.time()
        t.s.type(KEYS["END"], settle=False)
        el = SLOW + 10
        while time.time() - t0 < SLOW + 10:
            t.s.settle(0.25)
            if pfl(t, g).endswith("6000 shown"):
                el = time.time() - t0
                break
        say("    [measured] End over 6,000 ids (120 pages of 50, 1,000 ids a read): %.1f s" % el)
        ok, got, want = pkrows(t, g, PKIDS[-g["lh"]:])
        row("End reads on to the end of the file (within %.0f s): '6000 shown' (no 'or more'), the last %d ids are on the screen and rec06000 is current" % (SLOW, g["lh"]),
            el < SLOW and ok and "rec06000" in t.rev(g["y1"] + g["lh"] - 1), "%.1f s %r" % (el, (got[-2:], want[-2:], pfl(t, g)[-30:])))
        t.key("ENTER")
        row("Enter answers the record id, not a number: the status line says picked rec06000", "picked rec06000" in t.line(40), repr(t.line(40)))

        t.key("F11")
        t.s.type("rec0001", idle=1.0)
        ten = [i for i in PKIDS if "rec0001" in i.lower()]
        ok, got, want = pkrows(t, g, ten, bar=False)
        row("typing 'rec0001' restarts the read with the filter: the ten ids that hold it (%s ... %s) and, since not every id has been looked at, '10 or more shown'" % (ten[0], ten[-1]),
            len(ten) == 10 and ok and pfl(t, g).endswith("10 or more shown"), repr((got, want, pfl(t, g)[-30:])))
        t.s.type(KEYS["END"], idle=1.0)
        row("End reads on to the end of the file: '10 shown' now, the same ten ids", pfl(t, g).endswith("10 shown") and pkrows(t, g, ten, bar=False)[0], repr(pfl(t, g)[-30:]))
        t.key("ENTER")
        row("Enter answers the last of them: picked rec00019", "picked rec00019" in t.line(40), repr(t.line(40)))

        # a filter that few ids match: nothing in the first reads
        t.key("F11")
        t.s.type("rec0500", idle=1.0)
        first = t.line(g["y1"])[g["x0"]:g["x0"] + g["lw"]]
        srch = re.search(r"(\d+) records searched", first)
        row("typing 'rec0500': the ten ids that hold it are far into the file, so the first reads find none: '0 or more shown' and the first row says how many ids were searched (and that a key that moves down goes on); "
            "the window is not full, so it read twice (the restart and the read that keeps it full), 2000 ids of 1000 each",
            pfl(t, g).endswith("0 or more shown") and "none yet" in first and srch is not None and int(srch.group(1)) == 2000, repr((first, pfl(t, g)[-30:])))
        downs = 0
        while downs < 10 and "rec05000" not in "\n".join(t.lines()):
            t.key("DOWN")
            downs += 1
        say("    [measured] Downs until rec05000 appeared: %d" % downs)
        row("each Down reads on: within a few of them the matches appear (rec05000 ...)", "rec05000" in "\n".join(t.lines()) and downs <= 6, repr(downs))
        t.s.type(KEYS["END"], idle=1.0)
        tenb = ["rec%05d" % q for q in range(5000, 5010)]
        row("End: '10 shown', rec05000 to rec05009", pfl(t, g).endswith("10 shown") and pkrows(t, g, tenb, bar=False)[0], repr(pfl(t, g)[-30:]))
        t.key("ESC")
        row("Esc closes it: cancelled, the window gone", "cancelled" in t.line(40) and "Pick a record" not in "\n".join(t.lines()), repr(t.line(40)))

        # several, with the first attribute as the description; picks are kept by id across a new read
        gm = pkgeom(True, True, "Pick records")
        t.key("F12")
        ok, got, want = pkrows(t, gm, PKIDS, True, (), True)
        row("F12: several, with the description beside each id (rec00001 shelf-1, rec00002 shelf-2 ...)", ok, repr((got[:3], want[:3])))
        t.key("SPACE")
        t.s.type("shelf-7", idle=1.0)
        shown = [t.line(gm["y1"] + r)[gm["x0"]:gm["x0"] + gm["lw"] - 1].rstrip() for r in range(2)]
        row("typing 'shelf-7' filters on the DESCRIPTION: the first id is rec00007 (shelf-7), its mark is not [x] (the mark was on rec00001, which the filter hides)",
            shown[0].startswith("[ ] rec00007") and "shelf-7" in shown[0] and "1 marked" in pfl(t, gm), repr((shown, pfl(t, gm))))
        t.key("SPACE")
        t.s.type("\x15", idle=1.0)
        ok, got, want = pkrows(t, gm, PKIDS, True, ("rec00001", "rec00007"), True)
        row("emptying the filter reads from the first id again: rec00001 and rec00007 are [x], by their ids, and the count says 2 marked", ok and "2 marked" in pfl(t, gm), repr((got[:8], pfl(t, gm)[-30:])))
        t.key("ENTER")
        row("Enter answers the ids picked, in the order they were picked: picked rec00001,rec00007", "picked rec00001,rec00007" in t.line(40), repr(t.line(40)))
        t.end()

        # a pipe: F11, then the input ends with the window open
        say("    --- on a pipe: F11, then the input ends with the window open")
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
        t0 = time.time()
        try:
            outp, _ = p.communicate(b"\nTERM 140,43\ntktest pick 12 50 1000\n\x1b[23~", timeout=20)
            ended = True
        except subprocess.TimeoutExpired:
            os.kill(p.pid, 1)
            time.sleep(1)
            p.kill()
            outp, _ = p.communicate()
            ended = False
        took = time.time() - t0
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        seen = b"Pick a record" in outp
        say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s, the window was drawn on the pipe: %s" % (ended, took, cpu, "yes" if seen else "no"))
        row("a piped session whose input ends with the paged window open ends within 20 s and does not spin (under 3 s of CPU)", ended and cpu < 3.0, "%.1f s, %.2f s" % (took, cpu))
        if not seen:
            skip("the window was open when the input ended", "the pipe did not decode F11 into the key, so the window was never drawn")
    finally:
        sess(box, "DELETE.FILE zzpkfile FORCE")


# TK-0.4 (G4).  Part 1, an internal session: $tk_explain for gates of each kind.  Part 2, a pseudo-terminal: `tktest dialogs` (F7 a Run / Cancel box for
# `create.file zztkdlg1 dynamic`, F8 the same with a typed name `zztkdlg2`); the DISK is the evidence of what ran.  Part 3, a pipe: F7, then the input ends.
EXPLAINCASES = [("shon", "sh", 1), ("shoff", "sh", 0), ("vocon", "voc", 1), ("vocoff", "voc", 0), ("srdoff", "shared-read", 0), ("srdon", "shared-read", 1), ("neton", "net", 1),
                ("filesoff", "files", 0), ("filesadmon", "files-admin", 1), ("nosuch", "nosuch", 1), ("sockets", "sockets", 1)]


def explain_program():
    p = ["$internal", "   crt 'TKE begin'"]
    for tag, gid, on in EXPLAINCASES:
        p.append("   tag = '%s' ; id = '%s' ; on = %d ; gosub go" % (tag, gid, on))
    p += ["   crt 'TKE end'", "   stop", "go:", "   call $tk_explain(id, on, lines, typed)", "   crt 'E ' : tag : ' typed=' : typed : ' n=' : dcount(lines, @fm)",
          "   for k = 1 to dcount(lines, @fm)", "      crt 'E ' : tag : ' L' : k : ' ' : lines<k>", "   next k", "   return", "end", ""]
    return "\n".join(p)


def msg_text(n, *args):
    """A message of the tree as the program prints it (sdsys/messages/N with %1 .. filled in)."""
    with open(os.path.join(HERE, "..", "sdsys", "messages", str(n)), encoding="latin-1") as f:
        t = f.read().rstrip("\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%%%d" % i, a)
    return t


def on_disk(box, name):
    r = subprocess.run(["find", os.path.join(box, "sys"), os.path.join(box, "user_accounts"), "-maxdepth", "3", "-name", name], capture_output=True, text=True)
    return bool(r.stdout.strip())


def dialogs_rows(box, made):
    say("\n--- the confirm boxes (TK-0.4, G4)")
    with open(os.path.join(box, "sys", "bp", "zztkexp"), "w", encoding="latin-1") as f:
        f.write(explain_program())
    made.append("zztkexp")
    out = sess(box, "BASIC bp zztkexp", "RUN bp zztkexp")
    if not re.search(r"^TKE begin\s*$", out, re.M) or not re.search(r"^TKE end\s*$", out, re.M):
        say(out[-1500:])
        bail("the TK-0.4 explain program did not run to its end, so no row below can be believed")
    ex = {}
    for m in re.finditer(r"^E (\w+) typed=(\d+) n=(\d+)\s*$", out, re.M):
        ex[m.group(1)] = [int(m.group(2)), int(m.group(3)), []]
    for m in re.finditer(r"^E (\w+) L(\d+) (.*?)\s*$", out, re.M):
        if m.group(1) in ex:
            ex[m.group(1)][2].append(m.group(3))
    L = lambda tag: ex.get(tag, [None, None, []])[2]
    beyond, dflt_off, dflt_on = msg_text(11819), msg_text(11817), msg_text(11818)
    row("sh on: the box asks for the typed name; five lines: the title (11820), what ON allows, when, the delivered-off line, the beyond-SD line",
        ex.get("shon", [None])[0] == 1 and len(L("shon")) == 5 and L("shon")[0] == "Shell (sh), turning it on" and L("shon")[1].startswith("turned on it allows: use the SH verb")
        and L("shon")[2] == "takes effect: next account entry" and L("shon")[3] == dflt_off and L("shon")[4] == beyond, repr(ex.get("shon")))
    row("sh off: no typed name; four lines: title, what it still allows, when, beyond SD; NO delivered-off line", ex.get("shoff", [None])[0] == 0 and len(L("shoff")) == 4
        and L("shoff")[0] == "Shell (sh), turning it off" and L("shoff")[1].startswith("turned off it still allows: everything inside SD") and dflt_off not in L("shoff") and L("shoff")[3] == beyond, repr(ex.get("shoff")))
    row("voc on (not beyond SD): no typed name, four lines with the delivered-off line and 'next sign-on only', no beyond-SD line",
        ex.get("vocon", [None])[0] == 0 and len(L("vocon")) == 4 and "takes effect: next sign-on only" in L("vocon") and dflt_off in L("vocon") and beyond not in L("vocon"), repr(ex.get("vocon")))
    row("voc off: three lines, no delivered line", ex.get("vocoff", [None])[0] == 0 and len(L("vocoff")) == 3 and dflt_off not in L("vocoff") and dflt_on not in L("vocoff"), repr(ex.get("vocoff")))
    row("shared-read off (delivered ON): the 'delivered on; you are turning it off' line (11818) is there and the delivered-off one is not", dflt_on in L("srdoff") and dflt_off not in L("srdoff") and ex.get("srdoff", [None])[0] == 0, repr(ex.get("srdoff")))
    row("shared-read on (delivered ON): neither delivered line", dflt_on not in L("srdon") and dflt_off not in L("srdon") and len(L("srdon")) == 3, repr(ex.get("srdon")))
    row("net on and files-admin on reach beyond SD: the typed name is asked for and the warning is there", all(ex.get(t, [None])[0] == 1 and beyond in L(t) for t in ("neton", "filesadmon")), repr((ex.get("neton"), ex.get("filesadmon"))))
    row("files OFF reaches beyond SD but turning OFF asks for no typed name (it is a tightening)", ex.get("filesoff", [None])[0] == 0 and beyond in L("filesoff"), repr(ex.get("filesoff")))
    row("a gate that is not in the table, and the planned one (sockets), give no lines and no typed name", ex.get("nosuch") == [0, 0, []] and ex.get("sockets") == [0, 0, []], repr((ex.get("nosuch"), ex.get("sockets"))))

    # part 2: the boxes on a pseudo-terminal
    say("    --- on a pseudo-terminal (140 by 43)")
    t = Term(box, "tktest dialogs")
    if "F1 help" not in "\n".join(t.lines()):
        say("\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
        bail("tktest dialogs never drew its function-key row, so no row below can be believed")
    row("`tktest dialogs` starts on pane D: its function-key row names F7 and F8: %r" % F_D, t.line(42) == F_D, repr(t.line(42)))
    scr = lambda: "\n".join(t.lines())

    def box_up():
        s = scr()
        return "Run this command?" in s

    t.key("F7")
    s = scr()
    row("F7 opens the box: the title, 'this will run:', the exact command, the explanation lines and the two buttons",
        "Run this command?" in s and "this will run:" in s and "create.file zztkdlg1 dynamic" in s and "Shell (sh), turning it on" in s and "[ Run ]" in s and "[ Cancel ]" in s, s[-600:])
    t.key("ENTER")
    row("Enter alone does NOT run it: the default button is Cancel; the box is gone, the status line says nothing was run, the foot of the screen is back, and nothing is on the disk",
        not box_up() and "nothing was run" in t.line(40) and t.line(42) == F_D and not on_disk(box, "zztkdlg1"), repr((t.line(40), t.line(42), on_disk(box, "zztkdlg1"))))
    t.key("F7")
    t.key("ESC")
    row("Esc cancels: nothing was run and nothing is on the disk", not box_up() and "nothing was run" in t.line(40) and not on_disk(box, "zztkdlg1"), repr((t.line(40), on_disk(box, "zztkdlg1"))))
    t.key("F8")
    s = scr()
    row("F8 opens the box for the other command, with the beyond-SD warning (net on)", "create.file zztkdlg2 dynamic" in s and "Remote files (net), turning it on" in s and msg_text(11819) in s, s[-500:])
    t.s.type("r", idle=0.6)
    s = scr()
    row("choosing Run by its letter asks for the name: 'type zztkdlg2 to run it'", "type zztkdlg2 to run it" in s, s[-500:])
    t.s.type("nope\r", idle=0.6)
    row("a wrong name runs nothing: the status line says what name was asked for, and nothing is on the disk",
        "nothing was run: what was typed is not zztkdlg2" in t.line(40) and not on_disk(box, "zztkdlg2"), repr((t.line(40), on_disk(box, "zztkdlg2"))))
    t.key("F8")
    t.s.type("r", idle=0.6)
    t.s.type("ZZTKDLG2\r", idle=0.8)
    row("the name is compared exactly: ZZTKDLG2 is not zztkdlg2, so nothing runs and nothing is on the disk",
        "nothing was run: what was typed is not zztkdlg2" in t.line(40) and not on_disk(box, "zztkdlg2"), repr((t.line(40), on_disk(box, "zztkdlg2"))))
    t.key("F8")
    t.s.type("r", idle=0.6)
    t.key("ESC")
    row("Esc at the name asks nothing more and runs nothing: the status line is the plain 'nothing was run', not the wrong-name message",
        not box_up() and t.line(40).rstrip().endswith("nothing was run") and "what was typed" not in t.line(40) and "type zztkdlg2" not in scr() and not on_disk(box, "zztkdlg2"), repr((t.line(40), on_disk(box, "zztkdlg2"))))
    t.key("F8")
    t.key("ENTER")
    row("Enter on the first box of the typed flow is Cancel too: nothing on the disk", not box_up() and not on_disk(box, "zztkdlg2"), repr(on_disk(box, "zztkdlg2")))
    t.key("F8")
    t.s.type("r", idle=0.6)
    t.s.type("zztkdlg2\r", idle=1.2)
    row("the right name runs it: the command went through $tk_run (the status line says it ran) and the file IS on the disk (so the sentinel can fire)",
        "ran, status" in t.line(40) and on_disk(box, "zztkdlg2"), repr((t.line(40), on_disk(box, "zztkdlg2"))))
    t.key("F7")
    t.s.type("r", idle=1.2)
    row("Run chosen by its letter in the plain box runs it: the file IS on the disk", "ran, status" in t.line(40) and on_disk(box, "zztkdlg1"), repr((t.line(40), on_disk(box, "zztkdlg1"))))
    row("...and the frame is whole after all the boxes: the function-key row and the border are where they were", t.line(42) == F_D and t.line(41) == "-" * 140, repr((t.line(41)[:20], t.line(42))))
    t.end()
    sess(box, "DELETE.FILE zztkdlg1 FORCE", "DELETE.FILE zztkdlg2 FORCE")
    row("(cleanup) both files were removed again, so the pipe row below starts from nothing", not on_disk(box, "zztkdlg1") and not on_disk(box, "zztkdlg2"), "")

    # part 3: a pipe, F7 typed, then the input ends with the box open
    say("    --- on a pipe: F7, then the input ends with the box open")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
    t0 = time.time()
    try:
        outp, _ = p.communicate(b"\nTERM 140,43\ntktest dialogs\n\x1b[18~", timeout=20)
        ended = True
    except subprocess.TimeoutExpired:
        os.kill(p.pid, 1)
        time.sleep(1)
        p.kill()
        outp, _ = p.communicate()
        ended = False
    took = time.time() - t0
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    seen = b"Run this command?" in outp
    say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s, the box was drawn on the pipe: %s" % (ended, took, cpu, "yes" if seen else "no"))
    row("a piped session whose input ends with the box open ends within 20 s, does not spin (under 3 s of CPU) and runs nothing: no file on the disk", ended and cpu < 3.0 and not on_disk(box, "zztkdlg1"), "%.1f s, %.2f s" % (took, cpu))
    if not seen:
        skip("the box was open when the input ended", "the pipe did not decode F7 into the key, so the box was never drawn: the row above shows only that nothing ran")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tk-base.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-tk-base: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tk-base: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    made = []
    try:
        with open(os.path.join(box, "sys", "bp", "zztkvoc"), "w", encoding="latin-1") as f:
            f.write("$internal\n   open 'VOC' to v else crt 'TKVOC no voc' ; stop\n   write 'V':@fm:'CA':@fm:'$tool_tktest' to v, 'tktest'\n   crt 'TKVOC done'\nend\n")
        made.append("zztkvoc")
        out = sess(box, "BASIC bp zztkvoc", "RUN bp zztkvoc")
        row("SETUP: the VOC entry tktest (the throw-away app, catalogued $tool_tktest) is written", re.search(r"^TKVOC done\s*$", out, re.M) is not None, out[-300:])
        who = sess(box, "WHO.AM.I")
        is_admin = re.search(r"Admin\?\s*:\s*Yes", who) is not None
        say("    (the sandbox session is %s)" % ("an administrator" if is_admin else "NOT an administrator"))

        say("\n--- a window of 140 by 43: the foot of the screen")
        t = Term(box, "tktest")
        if "F1 help" not in "\n".join(t.lines()):
            say("    screen after the command:\n" + "\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
            bail("the app never drew its function-key row, so no row below can be believed")
        row("the function-key row is row 42 (the added 43rd line) and names exactly the keys pane A uses, in table order: %r" % F_A, t.line(42) == F_A, repr(t.line(42)))
        row("...in the bar's style: the text is in reverse video", F_A in t.rev(42), repr(t.rev(42)))
        row("the border is row 41: 140 plain characters across (LC_ALL=C)", t.line(41) == "-" * 140, repr(t.line(41)[:60]))
        row("the status line is row 40, in reverse video, and starts with the pane in brackets: [A]", t.line(40).startswith("[A]") and "[A]" in t.rev(40), repr(t.line(40)))
        row("a key the table disables (Ctrl-S, save) is not shown", "^S" not in t.line(42), repr(t.line(42)))
        t.key("TAB")
        row("Tab moves the focus: the function-key row now names the keys of pane B: %r" % F_B, t.line(42) == F_B, repr(t.line(42)))
        row("...and the status line shows [B]", t.line(40).startswith("[B]"), repr(t.line(40)))
        t.key("F1")
        row("F1 (help, every pane): the status line carries the message after the pane: 'help for pane B'", t.line(40).startswith("[B]") and "help for pane B" in t.line(40), repr(t.line(40)))
        t.key("F3")
        row("F3 (sort) is pane A's key: on pane B it does nothing (the message is still the help one)", "help for pane B" in t.line(40) and "sorted" not in t.line(40), repr(t.line(40)))
        t.key("F5")
        row("F5 (refresh) is pane B's key: the message is 'refreshed'", "refreshed" in t.line(40), repr(t.line(40)))
        t.key("TAB")
        row("Tab again: back to pane A, its keys, [A]", t.line(42) == F_A and t.line(40).startswith("[A]"), repr((t.line(42), t.line(40))))
        t.key("F3")
        row("F3 on pane A: 'sorted'", "sorted" in t.line(40), repr(t.line(40)))
        t.key("CTRLQ")
        t.s.settle(0.8)
        L = "\n".join(t.lines())
        row("Ctrl-Q leaves the app and gives the prompt back: no function-key row any more, and SD answers a command", "F1 help" not in L, L[-300:])
        t.s.type("WHO\r", idle=0.8)
        row("...the session is still alive after the app", re.search(r"(?m)^\d+ \w+", "\n".join(t.lines())) is not None or "WHO" in "\n".join(t.lines()), "\n".join(t.lines())[-200:])
        t.end()

        say("\n--- a window bigger than 43 rows is used whole")
        t = Term(box, "tktest", cols=160, rows=50)
        row("at 160 by 50 the function-key row is the LAST row (49), the border above it (48), the status line above that (47)",
            t.line(49) == F_A and t.line(48) == "-" * 160 and t.line(47).startswith("[A]"), repr((t.line(47)[:20], t.line(48)[:20], t.line(49), t.line(42)[:20])))
        t.end()

        say("\n--- a window under 140 by 43 is refused before the screen is taken")
        t = Term(box, "tktest", cols=100, rows=30)
        L = "\n".join(t.lines())
        row("the library's message 11197 names the app and both sizes: 'at least 140 columns by 43 lines; this one is 100 by 30'",
            "at least 140 columns by 43 lines" in L and "100 by 30" in L, L[-300:])
        row("...and no frame was drawn", "F1 help" not in L and not any(l.strip() == "-" * 100 for l in t.lines()), "")
        t.end()

        say("\n--- the audience")
        if is_admin:
            t = Term(box, "tktest admin")
            row("audience admin in an administrator's session: the frame is drawn (the refusal for anyone else is a text check)", t.line(42) == F_A, repr(t.line(42)))
            row("...and the right end of row 0 names the app and the audience: 'administrator'", "administrator" in t.line(0), repr(t.line(0)))
            t.end()
        else:
            skip("audience admin", "the sandbox session is not an administrator, so the frame cannot be shown for it")

        runtime_rows(box, made)
        gates_rows(box, made)
        dialogs_rows(box, made)
        table_rows(box, made)
        pick_rows(box, made)
        pickfile_rows(box, made)
        slider_rows(box, made)

        say("\n--- the end of the input ends the app (a pipe; TERM 140,43 typed so that the window is big enough)")
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)         # the children reaped so far (the pty runs above); this child's own CPU is the difference
        p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
        t0 = time.time()
        p.stdin.write(b"\nTERM 140,43\ntktest\n")
        p.stdin.flush()
        p.stdin.close()
        ended = False
        while time.time() - t0 < 15:
            if p.poll() is not None:
                ended = True
                break
            time.sleep(0.2)
        took = time.time() - t0
        if not ended:
            os.kill(p.pid, 1)           # SIGHUP first: SD lets go of what it holds; a killed session keeps its slot
            time.sleep(1)
            if p.poll() is None:
                p.kill()
        p.wait()
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s" % (ended, took, cpu))
        row("a piped session whose input ENDS ends the app within 15 s (it does not wait for a key that cannot come)", ended, "%.1f s" % took)
        row("...and did not spin: under 3 s of CPU (a loop that takes the end of input for an empty key uses all of it)", ended and cpu < 3.0, "%.2f s" % cpu)
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p_ = os.path.join(box, "sys", d, nm)
                if os.path.exists(p_):
                    os.remove(p_)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-tk-base: %d passed, %d failed, %d skipped" % (passed, failed, skipped))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
