#!/usr/bin/env python3
#
# sandbox-tool-gates.py - the gate matrix, TOOL.GATES, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A2; plan .claude/plan-fullscreen-toolkit.md section 5).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-gates.py <dir> [--build] [--mutant=NAME] [--only=NAME[,NAME]]
#
# --only (2 Nov 26) runs the named sections: cell queue run several route needs tighten filter who mouse refresh group small allon leave.  The set-up and G0-G1 (opening the page)
# always run.  The sections up to group were written to run in that order on one page and some read what an earlier one left (G13a reads the gates G9 and G10 turned off, which a fresh
# sandbox also has off); only `leave` has been run alone.
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN, the person who runs this suite) opens TOOL.GATES on a 140 by 43 terminal.  The register holds five accounts, written by hand
# with every field: the sandbox user's own (a USER account named after the Linux user, so that the route words, which take the account name for the Linux user, have a real user for
# the real sd-elevate's dry run), zzg2 (a USER account with sh, os, sd on and a person in sdssh), zzg3 (USER, suspended), zzgg (a GROUP account) and zzgo (an OTHER account).  Group
# gates are membership of Linux groups, which a sandbox cannot change: modify.account runs with the helper stood in by a script that edits a SCRATCH group file, and the group lookups
# of modify.account and of $tk_gates read that file (sandbox-filesgrp.py's method).  The page runs the REAL modify.account.
#
# THE INSTRUMENT.  Every outcome is read from the DISK: the register record, the scratch group file, the helper's call log and the audit file.  A row that says "nothing was run" is
# judged by those, and a page that drew a cell is not taken to have changed it.
#
#   G0       an ordinary account has no tool.gates; opening it writes one audit line and changes nothing
#   G1       the boxes, the sixteen column headings, the five rows with their kind and cells, the counts line
#   G2       the cell under the cursor is described; the arrows move it; ssh and api say they are one setting; a group account's route cells are dashes; sockets are planned
#   G3-G4    Enter queues the opposite state (a star), again takes it back; nothing is run or audited; R with nothing queued says so
#   G5       a gate that is off as delivered: the command and its effect, the tighter-choice sentence, Esc runs nothing, a wrong name runs nothing, the name runs it, the register says yes
#   G6       turning it OFF needs no name
#   G7       several cells of one account are ONE command, in the table's order, and the verb's closing line is shown; G7h / G7i (9 Nov 26, S.186): a held R (six
#            at once) opens the box and does not answer it, and Esc leaves the queue and the register as they were
#   G8       ssh and api: one word for the pair (ssh, api, both, none), the scratch group file is the evidence
#   G9       files-write needs files and files-admin needs files-write: refused by the page before the box, nothing runs; both together run
#   G10-G11  T queues OFF for every gate that is off as delivered and on now and leaves shared-read; U drops what is queued
#   G12      F changes which accounts are shown
#   G13      who can reach the operating system; the live sessions of the account under the cursor
#   G14-G16  the mouse; F1; F5 reads the machine again and keeps the queue; the null case (no account)
#   G17      sh and os for a group account are refused in words; a window under 140 by 43 gets no page
#   G19      (2 Nov 26, S.88 P10, section leave) Ctrl-Q with nothing queued leaves at once; with a change queued it asks in $tk_confirm's box (Run the changes, Leave without them,
#            Cancel): Enter is Cancel, File > Quit asks too, Esc on the page opens the bar and does not leave, Leave without them runs nothing, Run the changes goes through R's own
#            box (Esc there keeps the page and the queue; Run and the name run it, and the page closes).  Whether the page has gone is judged by DISPLAY at the TCL prompt.
# NOT HELD: the installer, the real systemd, sudo and the real /etc/group (the route and files groups change through the stand-in), the help text itself (test-help-units.py).
import getpass
import importlib.util
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_toolgates", "sandbox-home.py")
fg = _load("sandbox_filesgrp_for_toolgates", "sandbox-filesgrp.py")
q3 = fg.q3
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = fg.ME
FAILED_IDS = []

HEAD = ["ssh", "api", "sh", "os", "sd", "voc", "bp", "dict", "net", "sh-rd", "sh-wr", "files", "f-wr", "f-adm", "ai", "home", "sock"]     # 7 Nov 26 S.166: home
IDS = ["ssh", "api", "sh", "os", "sd", "voc", "bp", "dict", "net", "shared-read", "shared-write", "files", "files-write", "files-admin", "ai", "home", "sockets"]
NC = len(IDS)
G2, G3, GG, GO = "zzg2", "zzg3", "zzgg", "zzgo"
NAMES = [ME, G2, G3, GG, GO]


def arow(rid, name, ok, detail=""):
    """A row with an id (G3 ...): the mutant mode compares the ids that failed with the ids that had to."""
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


MUTANTS = {
    # name: (old text of the sandbox's tool_gates, new text, the row ids that must fail and no others)
    "no-typed-name": ("      typed = anm<av>\n   end\n   el<-1> = 'A running session", "      typed = ''\n   end\n   el<-1> = 'A running session", ["G5"]),
    "route-both-wrong": ("         case fin<rs> = 1 and fin<ra> = 1\n            rword = 'both'", "         case fin<rs> = 1 and fin<ra> = 1\n            rword = 'ssh'", ["G8"]),   # rword since the rw/RW clash fix (2 Nov 26 review: rw was found 0 times)
    "tighten-queues-on": ("         aq<av, k> = 0\n         n.q += 1", "         aq<av, k> = 1\n         n.q += 1", ["G10"]),
    "needs-not-checked": ("      if fin<fw> = 1 and fin<fi> # 1 then bad =", "      if @false then bad =", ["G9"]),
    "all-on-skips-test": ("      gosub cell.why\n      if why = '' then\n         aq<av, k> = (if ast<av, k> = tv", "      why = ''\n      if why = '' then\n         aq<av, k> = (if ast<av, k> = tv", ["G18"]),
    # 2 Nov 26, S.88 P10: the leave question
    "leave-at-once": ("      case nm = 'ctrl-q'\n         gosub leave.ask\n", "      case nm = 'ctrl-q'\n         done = 1\n", ["G19"]),
    "leave-default": ("'&Run the changes,&Leave without them,&Cancel'", "'&Run the changes,&Cancel,&Leave without them'", ["G19"]),
}
SECTIONS = ("cell", "queue", "run", "several", "route", "needs", "tighten", "filter", "who", "mouse", "refresh", "group", "home", "small", "allon", "leave")
ONLY = None


def chosen(name):
    """Is section NAME to run (--only)?  Not called want: main() has a local of that name in the mutant mode."""
    return ONLY is None or name in ONLY


def box():
    return sh.BOX


def st(h):
    return h.line(40)


def regf(name):
    return g.reg_read(name)


def field(name, n):
    f = regf(name)
    return f[n - 1] if len(f) >= n else ""


def groups():
    return fg.read_group()


def calls():
    return fg.read_calls()


def snapshot():
    """Every register record and the scratch group file, as bytes: the 'nothing changed' evidence."""
    snap = {}
    for n in NAMES:
        with open(os.path.join(sh.SYS, "accounts", n), "rb") as f:
            snap[n] = f.read()
    with open(os.path.join(box(), "grp", "group"), "rb") as f:
        snap["group"] = f.read()
    snap["calls"] = len(calls())
    return snap


def write_groups(members):
    """The scratch group file: ME in sdusers and the members given for each route group (a dict group -> list)."""
    order = [("sdusers", 2000, [ME]), ("sdssh", 2010, []), ("sdapi", 2011, []), ("sdfiles", 2001, []), ("sdfileswrite", 2002, []), ("sdfilesadmin", 2003, []), ("sdaiusers", 2004, [])]
    lines = ["root:x:0:"]
    for nm, gid, base in order:
        lines.append(fg.grp_line(nm, gid, members.get(nm, base)))
    lines.append(fg.grp_line("wheel", 10, []))
    g.put(os.path.join(box(), "grp", "group"), "\n".join(lines))


def reg_record(name, grp, sh_="no", os_="no", sd="no", voc="no", bp="no", dict_="no", srd="", swr="", net="no", susp=""):
    path = os.path.join(box(), "user_accounts", name)
    return [path, "", grp, "", susp, "", sh_, os_, sd, voc, bp, dict_, srd, swr, net, "", "", ""]


def write_register():
    recs = {ME: reg_record(ME, "sdu_" + ME),
            G2: reg_record(G2, "sdu_zzother2", "yes", "yes", "yes"),
            G3: reg_record(G3, "sdu_zzother3", susp="SUSPENDED"),
            GG: reg_record(GG, "sdg_zzgg", sd="yes"),
            GO: reg_record(GO, "zzgother")}
    for n, rec in recs.items():
        os.makedirs(os.path.join(box(), "user_accounts", n), exist_ok=True)
        g.put(os.path.join(sh.SYS, "accounts", n), "\n".join(rec) + "\n")


def setup_gates():
    """The stand-in for the helper, the scratch groups, the patched programs and the accounts."""
    b = box()
    q3.BOX, q3.SYS, q3.SD = b, sh.SYS, os.path.join(sh.SYS, "bin", "sd")
    os.makedirs(os.path.join(b, "grp", "fakebin"), exist_ok=True)
    shim = os.path.join(b, "grp", "elevate-shim")
    g.put(shim, fg.SHIM % {"box": b, "elevate": os.path.join(HERE, "sd-elevate")})
    os.chmod(shim, 0o755)
    getent = os.path.join(b, "grp", "fakebin", "getent")
    g.put(getent, fg.GETENT % {"box": b})
    os.chmod(getent, 0o755)
    g.put(os.path.join(b, "grp", "calls.log"), "")
    write_groups({"sdssh": ["zzother2"]})
    fg.patch_modifya(None)
    src = open(os.path.join(TREE, "sdsys", "gpl.bp", "tk_gates"), encoding="utf-8", errors="replace").read()
    old = "deffun is_grp_member(user,group) calling '!is_grp_member'"
    if src.count(old) != 1:
        bail("the tree's tk_gates has its group lookup %d times, not once" % src.count(old))
    g.put(os.path.join(sh.SYS, "gpl.bp", "tk_gates"), src.replace(old, "deffun is_grp_member(user,group) calling '!zzgm'"))
    out = q3.adm(["BASIC gpl.bp tk_gates"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the patched tk_gates did not compile:\n" + "\n".join(out[-6:]))
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_gates"), os.path.join(sh.SYS, "gpl.bp", "tool_gates"))
    compile_page()
    # the sandbox user's own account has a real directory and VOC, so that a live ordinary session can be in it; every account's register record is then written by hand
    g.FIXTURES[ME] = ("no", "no")
    g.build_account(ME)
    write_register()
    if sorted(NAMES) != sorted(NAMES, key=lambda s: s.encode()):
        bail("the names do not sort the way the page sorts them")


def compile_page():
    out = q3.adm(["BASIC gpl.bp tool_gates"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_gates did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def mutate(name):
    old, new, _kills = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_gates")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))


class Page:
    """A session on tool.gates, with the cursor position kept."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.gates\r", idle=3.0)
        self.r = 0                                   # the row under the cursor, counted from 0 among the rows shown
        self.c = 0                                   # the column under the cursor, counted from 0
        self.shown = sorted(NAMES)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.6):
        self.h.key(name, idle=idle)

    def typed(self, s, idle=0.9):
        self.h.typed(s, idle=idle)

    def to(self, name, gate, shown=None):
        """Move the cursor to the cell of an account and a gate id."""
        shown = shown or self.shown
        want_r, want_c = shown.index(name), IDS.index(gate)
        while self.r < want_r:
            self.key("down", 0.35)
            self.r += 1
        while self.r > want_r:
            self.key("up", 0.35)
            self.r -= 1
        while self.c < want_c:
            self.key("right", 0.35)
            self.c += 1
        while self.c > want_c:
            self.key("left", 0.35)
            self.c -= 1

    def rows(self):
        """{account: (kind, [16 cells])} for the rows on the screen."""
        out = {}
        for n in range(3, 17):
            line = self.line(n)
            nm = line[3:23].strip()
            if not nm:
                continue
            out[nm] = (line[23:29].strip(), [line[29 + 6 * i:35 + 6 * i].strip() for i in range(NC)], line[29 + 6 * NC:138].strip())
        return out

    def cell(self, name, gate):
        return self.rows()[name][1][IDS.index(gate)]

    def boxb(self):
        return [self.line(n)[3:138].rstrip() for n in range(21, 30)]

    def counts(self):
        return self.line(17)[3:138].rstrip(), self.line(18)[3:138].rstrip()

    def end(self):
        self.h.end()

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def open_page():
    p = Page()
    if "Gates by account" not in p.text():
        dump(p.h)
        bail("tool.gates never drew its page, so no row below can be believed")
    return p


def home_default():
    """S.166: the home cell of an account whose start field is blank: off when SDSYS's start.default says terminal, else ON (no file is the home screen)"""
    try:
        with open(os.path.join(sh.SYS, "start.default"), encoding="latin-1") as f:
            word = f.readline().strip().lower()
    except OSError:
        word = ""
    return "off" if word == "terminal" else "ON"


def expect_cells(me_overrides=None):
    """What the five rows should say with the register and groups as they are at the start."""
    me = ["off"] * NC
    me[IDS.index("shared-read")] = "ON"
    me[IDS.index("home")] = home_default()       # S.166: the register's start field is blank, so the cell is the system's default (the sandbox's set-up writes terminal)
    me[IDS.index("sockets")] = "plan"
    z2 = list(me)
    for k in ("ssh", "sh", "os", "sd"):
        z2[IDS.index(k)] = "ON"
    z3 = list(me)
    gg = list(me)
    for k in ("ssh", "api", "files", "files-write", "files-admin", "ai"):
        gg[IDS.index(k)] = "-"
    gg[IDS.index("sd")] = "ON"
    go = list(gg)
    go[IDS.index("sd")] = "off"
    exp = {ME: ("user", me), G2: ("user", z2), G3: ("user", z3), GG: ("group", gg), GO: ("other", go)}
    for k, v in (me_overrides or {}).items():
        exp[ME][1][IDS.index(k)] = v
    return exp


HOME_FIXTURES = ("zzhd", "zzhm", "zzht", "zzhs", "zzhv")      # sandbox-home.py's accounts: not part of this suite's five, so their register records are held aside after G0
HELD = []


def hold_home_fixtures():
    hold = os.path.join(box(), "hold-home")
    os.makedirs(hold, exist_ok=True)
    for n in HOME_FIXTURES:
        src = os.path.join(sh.SYS, "accounts", n)
        if os.path.exists(src):
            shutil.move(src, os.path.join(hold, n))
            HELD.append(n)


def restore_home_fixtures():
    hold = os.path.join(box(), "hold-home")
    for n in HELD:
        if os.path.exists(os.path.join(hold, n)):
            shutil.move(os.path.join(hold, n), os.path.join(sh.SYS, "accounts", n))
    del HELD[:]
    shutil.rmtree(hold, ignore_errors=True)


def section_open():
    say("\n--- opening the page")
    h0 = H(account="zzhd")                    # a pseudo-terminal: a piped run at TERM 200,9999 would have the page draw 9,994 rows
    h0.typed("tool.gates\r", idle=3.5)
    T0 = h0.text()
    arow("G0", "an ordinary account cannot reach the MATRIX: its verb tool.gates is the holder's read-only page (sandbox-tool-mygates.py's), and SDSYS's VOC alone has the matrix",
         "Gates by account" not in T0 and "What this account may do" in T0, T0[:300])
    h0.key("ctrl-q", idle=1.2)
    h0.end()
    hold_home_fixtures()
    snap = snapshot()
    a0 = fg.audit_off()
    p = open_page()
    new = fg.audit_new(a0) or ""
    arow("G0b", "opening the page writes one audit line, 'tool start app=tool.gates', and changes nothing: every register record and the group file are as they were, the helper was not called",
         len(re.findall(r"tool start app=tool\.gates$", new, re.M)) == 1 and snapshot() == snap, repr((new[-160:], snapshot() == snap)))
    T = p.text()
    arow("G1a", "the four boxes", all(w in T for w in ("Gates by account", "The cell under the cursor", "Who can reach the operating system", "Sessions of the account under the cursor")), T[:300])
    head = [p.line(2)[29 + 6 * i:35 + 6 * i].strip() for i in range(NC)]
    arow("G1b", "the seventeen column headings, in the order modify.account carries them out", head == HEAD and p.line(2)[3:9] == "Accoun", repr(head))
    rows = p.rows()
    exp = expect_cells()
    ok = sorted(rows) == sorted(NAMES) and all(rows[n][0] == exp[n][0] and rows[n][1] == exp[n][1] for n in NAMES)
    arow("G1c", "five rows, SDSYS not among them, by name: each with its kind and its sixteen cells read from the register and the scratch groups (ON, off, a dash for a route on a group or "
         "other account, plan for sockets, shared-read ON as delivered)", ok, repr({n: (rows[n][0], rows[n][1]) for n in rows}))
    arow("G1d", "the suspended account says so at the end of its row (susp: seventeen cells leave five columns)", rows[G3][2] == "susp" and rows[G2][2] == "" , repr((rows[G3][2], rows[G2][2])))
    c1, c2 = p.counts()
    arow("G1e", "the counts: all accounts, 5 of 5, one with a gate on that reaches beyond SD (zzg2; zzgg has sd on, which is also beyond SD: two)", c1.startswith("all accounts: 5 of 5 accounts.  2 with a gate on"), repr(c1))
    arow("G1f", "nothing is queued yet", c2.startswith("Nothing queued for"), repr(c2))
    arow("G1g", "a [?] at the end of the first box", p.line(2)[134:137] == "[?]", repr(p.line(2)[130:139]))
    return p


def section_cell(p):
    say("\n--- the cell under the cursor")
    first = sorted(NAMES)[0]
    B = p.boxb()
    arow("G2a", "the first cell is described: the account and the gate, the two words, what ON allows and what OFF still allows, when a change reaches the person",
         B[0].startswith(first + " (user)  -  Remote terminal [ssh]") and any("Words: ssh turns it on, none turns it off" in x for x in B)
         and any(x.startswith("ON allows: sign in to SD over ssh") for x in B) and any(x.startswith("OFF still allows: sign in at the machine's own keyboard") for x in B)
         and any("A change reaches the person: next login." in x for x in B) and any("This gate reaches BEYOND SD." in x for x in B), repr(B[:6]))
    arow("G2b", "ssh and api are said to be one setting", any("ssh and api are ONE setting" in x for x in B), repr(B))
    p.key("right")
    p.c += 1
    B = p.boxb()
    arow("G2c", "Right moves to api: the box is about api now", "[api]" in B[0] and any("Words: api turns it on, none turns it off" in x for x in B), repr(B[:3]))
    p.to(GG, "ssh")
    B = p.boxb()
    arow("G2d", "a route on a group account is a dash and the box says it does not apply", p.cell(GG, "ssh") == "-" and any("does not apply to a group account" in x for x in B), repr((p.cell(GG, "ssh"), B[:3])))
    p.to(GG, "sh")
    B = p.boxb()
    arow("G2e", "a shell on a group account: off, and the box says modify.account refuses it in either direction", any("modify.account refuses sh for it, in either direction" in x for x in B), repr(B[:3]))
    p.to(GG, "sockets")
    B = p.boxb()
    arow("G2f", "sockets is planned: a plan cell and a sentence that says it is not built", p.cell(GG, "sockets") == "plan" and any("planned and not built yet" in x for x in B), repr((p.cell(GG, "sockets"), B[:3])))
    p.to(ME, "sh")


def section_queue(p):
    say("\n--- queueing")
    snap = snapshot()
    a0 = fg.audit_off()
    p.to(ME, "sh")
    p.key("enter")
    cell = p.cell(ME, "sh")
    c1, c2 = p.counts()
    arow("G3a", "Enter queues the opposite state: the cell says ON* and the counts line says one change is queued for the account", cell == "ON*" and c2.startswith("Queued for %s: 1 change." % ME), repr((cell, c2)))
    arow("G3b", "nothing was run or audited: every record, the group file and the helper's call log are as they were", snapshot() == snap and (fg.audit_new(a0) or "") == "", repr(fg.audit_new(a0)))
    p.key("enter")
    cell = p.cell(ME, "sh")
    arow("G3c", "Enter again takes it back: the cell is off with no star and nothing is queued", cell == "off" and p.counts()[1].startswith("Nothing queued for"), repr((cell, p.counts())))
    p.key("enter")
    p.to(ME, "sockets")
    p.key("enter")
    arow("G3d", "Enter on a planned gate queues nothing and says why", p.cell(ME, "sockets") == "plan" and "planned and not built" in st(p.h), repr((p.cell(ME, "sockets"), st(p.h))))
    p.to(GG, "files")
    p.key("enter")
    arow("G3e", "Enter on a route cell of a group account queues nothing and says why", p.cell(GG, "files") == "-" and "does not apply to a group account" in st(p.h), repr((p.cell(GG, "files"), st(p.h))))
    p.to(ME, "sh")
    p.typed("u")
    arow("G4a", "U drops what is queued and says how many", p.cell(ME, "sh") == "off" and "dropped the 1 queued change of %s" % ME in st(p.h), repr((p.cell(ME, "sh"), st(p.h))))
    p.typed("r")
    arow("G4b", "R with nothing queued says so and opens no box", "nothing is queued for %s" % ME in st(p.h) and "modify.account" not in p.text(), repr(st(p.h)))


def section_run_on(p):
    say("\n--- G5: a gate that is off as delivered, turned ON")
    p.to(ME, "sh")
    p.key("enter")
    p.typed("r", idle=1.5)
    T = p.text()
    arow("G5a", "R shows the command, the effect, the delivered-off and tighter-choice sentences, and asks for the name", "modify.account %s sh-on" % ME in T and "A gate that is off as delivered is being turned ON." in T
         and "Leaving it off is the tighter choice" in T and "so the account name has to be typed" in T, T[-900:])
    a0 = fg.audit_off()
    snap = snapshot()
    p.key("esc", idle=1.2)
    arow("G5b", "Esc is Cancel: nothing was run (the status line says so), the register field is still no, the queue is still there", "nothing was run" in st(p.h) and field(ME, 7) == "no" and snapshot() == snap
         and p.cell(ME, "sh") == "ON*", repr((st(p.h), field(ME, 7), p.cell(ME, "sh"))))
    p.typed("r", idle=1.3)                         # R opens the box again; r in the box is Run, which asks for the name
    p.typed("r", idle=1.3)
    p.typed("nope\r", idle=1.6)
    arow("G5c", "a name that is not the account's runs nothing", field(ME, 7) == "no" and snapshot() == snap and (fg.audit_new(a0) or "") == "", repr((field(ME, 7), fg.audit_new(a0))))
    p.typed("r", idle=1.3)
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=2.5)
    new = fg.audit_new(a0) or ""
    arow("G5", "the account's name typed: the register field 7 says yes (read from the disk), the cell says ON with no star, the audit trail has the verb's line, and the page shows the verb's words",
         field(ME, 7) == "yes" and p.cell(ME, "sh") == "ON" and re.search(r"modify\.account sh-on account=%s$" % re.escape(ME), new, re.M) is not None and p.counts()[1].startswith("Nothing queued"),
         repr((field(ME, 7), p.cell(ME, "sh"), new[-200:], st(p.h))))
    if STOP_AFTER_G5:                            # the mutant mode: the rows after this one depend on what this one did
        return
    say("\n--- G6: turned OFF")
    a1 = fg.audit_off()
    p.key("enter")
    p.typed("r", idle=1.5)
    T = p.text()
    arow("G6a", "the OFF box shows modify.account NAME sh-off, says what it will still do, and asks for no name", "modify.account %s sh-off" % ME in T and "it will still be able to" in T and "so the account name has to be typed" not in T, T[-700:])
    p.typed("r", idle=2.5)
    new = fg.audit_new(a1) or ""
    arow("G6", "Run: the register field is no again and the audit trail has the verb's line", field(ME, 7) == "no" and p.cell(ME, "sh") == "off" and re.search(r"modify\.account sh-off account=%s$" % re.escape(ME), new, re.M) is not None,
         repr((field(ME, 7), new[-200:])))
    say("\n--- G6c: a long explanation line is not cut (24 Oct 26: the confirm box cut a line at its edge)")
    p.to(ME, "ai")
    p.key("enter")
    p.typed("r", idle=1.5)
    T = re.sub(r"[|\s]+", " ", p.text())
    arow("G6c", "the box for the ai gate, whose sentence about what ON allows is 150 characters, shows that sentence to its last words and not cut at the edge of the box", "leaves this machine for that provider" in T, T[-700:])
    p.key("esc", idle=1.2)
    p.typed("u", idle=0.8)


def section_several(p):
    say("\n--- G7: several cells of one account are one command")
    a0 = fg.audit_off()
    for gate in ("sh", "os", "voc"):
        p.to(ME, gate)
        p.key("enter")
    arow("G7a", "three cells queued: three stars and the counts line says 3 changes", [p.cell(ME, k) for k in ("sh", "os", "voc")] == ["ON*", "ON*", "ON*"] and p.counts()[1].startswith("Queued for %s: 3 changes." % ME), repr(p.counts()))
    # 9 Nov 26 (S.186, Fable's review): a HELD R - six r at once, as a terminal's key repeat sends them - opens the box and does not answer it.  R is the page's run key
    # and the box's Run letter; before $tk_confirm threw away the keys typed ahead, the second r chose Run and the name question was up.
    p.typed("rrrrrr", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G7h", "a held R (six at once) opens the Run/Cancel box showing the command, and no more: not the name question, nothing written",
         "modify.account %s sh-on os-on voc-on" % ME in T and ("Type %s to run it" % ME) not in T and field(ME, 7) == "no", repr((T[-500:], field(ME, 7))))
    p.key("esc")
    arow("G7i", "Esc cancels: the queue is still there (3 changes) and the register is unchanged",
         p.counts()[1].startswith("Queued for %s: 3 changes." % ME) and field(ME, 7) == "no", repr((p.counts(), field(ME, 7))))
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G7b", "ONE command with the words in the table's order: modify.account NAME sh-on os-on voc-on", "modify.account %s sh-on os-on voc-on" % ME in T, T[-800:])
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=3.0)
    new = fg.audit_new(a0) or ""
    arow("G7", "the register says yes in the three fields (7, 8, 10) and no in 9, 11, 12; one audit line for each word; the verb's closing line is on the status line",
         [field(ME, n) for n in (7, 8, 10, 9, 11, 12)] == ["yes", "yes", "yes", "no", "no", "no"]
         and all(re.search(r"modify\.account %s account=%s$" % (w, re.escape(ME)), new, re.M) for w in ("sh-on", "os-on", "voc-on")) and "3 actions carried out" in st(p.h), repr(([field(ME, n) for n in (7, 8, 10)], new[-300:], st(p.h))))


def section_route(p):
    say("\n--- G8: ssh and api are one setting")
    c0 = len(calls())
    p.to(ME, "ssh")
    p.key("enter")
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G8a", "ssh ON alone: the word sent is ssh, and the page says ssh and api are one setting", "modify.account %s ssh" % ME in T and "the word sent is ssh, which gives ssh ON and api off" in T, T[-700:])
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=3.0)
    gr = groups()
    arow("G8b", "the scratch group file has the person in sdssh and not in sdapi; the helper was called once (addgroup sdssh); the cell says ON", ME in gr.get("sdssh", []) and ME not in gr.get("sdapi", [])
         and len(calls()) == c0 + 1 and calls()[-1].split()[:1] == ["addgroup"] and p.cell(ME, "ssh") == "ON", repr((gr.get("sdssh"), gr.get("sdapi"), calls()[c0:])))
    p.to(ME, "api")
    p.key("enter")
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G8c", "api ON while ssh is ON: the word is both", "modify.account %s both" % ME in T and "the word sent is both, which gives ssh ON and api ON" in T, T[-700:])
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=3.0)
    gr = groups()
    arow("G8d", "both groups hold the person", ME in gr.get("sdssh", []) and ME in gr.get("sdapi", []) and p.cell(ME, "api") == "ON" and p.cell(ME, "ssh") == "ON", repr((gr.get("sdssh"), gr.get("sdapi"))))
    p.to(ME, "ssh")
    p.key("enter")
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G8e", "ssh OFF while api is ON: the word is api (the one word that gives the pair), and no name is asked for", "modify.account %s api" % ME in T and "the word sent is api, which gives ssh off and api ON" in T and "so the account name has to be typed" not in T, T[-700:])
    p.typed("r", idle=3.0)
    gr = groups()
    arow("G8f", "the person is out of sdssh and still in sdapi", ME not in gr.get("sdssh", []) and ME in gr.get("sdapi", []) and p.cell(ME, "ssh") == "off" and p.cell(ME, "api") == "ON", repr((gr.get("sdssh"), gr.get("sdapi"))))
    p.key("enter")
    p.to(ME, "api")
    p.key("enter")
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G8g", "ssh ON and api OFF in one queue: the word is ssh", "modify.account %s ssh" % ME in T and "which gives ssh ON and api off" in T, T[-700:])
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=3.0)
    p.to(ME, "ssh")
    p.key("enter")
    p.typed("r", idle=1.3)
    p.typed("r", idle=3.0)
    gr = groups()
    arow("G8", "ssh OFF with api already off: the word is none; neither group holds the person", ME not in gr.get("sdssh", []) and ME not in gr.get("sdapi", []) and p.cell(ME, "ssh") == "off" and p.cell(ME, "api") == "off", repr((gr.get("sdssh"), gr.get("sdapi"))))


def section_needs(p):
    say("\n--- G9: files-write needs files, files-admin needs files-write")
    c0 = len(calls())
    snap = snapshot()
    p.to(ME, "files-write")
    p.key("enter")
    p.typed("r", idle=1.2)
    arow("G9a", "files-write ON alone is refused by the page before any box is opened, in words, and nothing is run", "files-write needs files" in st(p.h) and "modify.account" not in p.text() and snapshot() == snap, repr(st(p.h)))
    p.key("enter")
    p.to(ME, "files-admin")
    p.key("enter")
    p.typed("r", idle=1.2)
    arow("G9b", "files-admin ON alone is refused the same way (it needs files-write)", "files-admin needs files-write" in st(p.h) and "modify.account" not in p.text() and snapshot() == snap, repr(st(p.h)))
    p.key("enter")
    p.to(ME, "files")
    p.key("enter")
    p.to(ME, "files-write")
    p.key("enter")
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G9c", "files ON and files-write ON together: one command, files-on then files-write-on, and the name is asked for", "modify.account %s files-on files-write-on" % ME in T and "so the account name has to be typed" in T, T[-700:])
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=3.5)
    gr = groups()
    arow("G9", "both groups hold the person (the scratch file), the cells say ON, the helper added both", ME in gr.get("sdfiles", []) and ME in gr.get("sdfileswrite", []) and p.cell(ME, "files") == "ON" and p.cell(ME, "files-write") == "ON"
         and len(calls()) >= c0 + 2, repr((gr.get("sdfiles"), gr.get("sdfileswrite"), calls()[c0:])))
    snap = snapshot()
    p.to(ME, "files")
    p.key("enter")
    p.typed("r", idle=1.2)
    arow("G9d", "files OFF while files-write stays ON is refused by the page, and nothing is run", "files-write needs files" in st(p.h) and snapshot() == snap, repr(st(p.h)))
    p.key("enter")
    p.to(ME, "files-write")
    p.key("enter")
    p.to(ME, "files")
    p.key("enter")
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G9e", "files OFF and files-write OFF together are allowed: one command", "modify.account %s files-off files-write-off" % ME in T, T[-600:])
    p.typed("r", idle=3.5)
    gr = groups()
    arow("G9f", "the person is out of both groups", ME not in gr.get("sdfiles", []) and ME not in gr.get("sdfileswrite", []) and p.cell(ME, "files") == "off", repr((gr.get("sdfiles"), gr.get("sdfileswrite"))))


def section_tighten(p):
    say("\n--- G10-G11: tighten, drop")
    # the person has sh, os, voc on (G7) and shared-read on as delivered; give it two more gates by hand so that T has several to take away
    rec = regf(ME)
    for n in (7, 8, 9, 10, 15):                  # sh, os, sd, voc and net ON, by hand (the section runs alone in the mutant mode)
        rec[n - 1] = "yes"
    g.put(os.path.join(sh.SYS, "accounts", ME), "\n".join(rec[:18]) + "\n")
    p.key("f5", idle=2.0)
    arow("G10a", "F5 reads the machine again: the by-hand register change (sd and net ON) shows", p.cell(ME, "sd") == "ON" and p.cell(ME, "net") == "ON", repr(p.rows()[ME]))
    p.to(ME, "sh")
    p.typed("t", idle=1.2)
    cells = p.rows()[ME][1]
    stars = [HEAD[i] for i, x in enumerate(cells) if x.endswith("*")]
    arow("G10b", "T queues OFF for sh, os, sd, voc and net (on now and off as delivered) and for nothing else: shared-read, which is on as delivered, is left alone",
         sorted(stars) == sorted(["sh", "os", "sd", "voc", "net"]) and all(cells[IDS.index(k)] == "off*" for k in ("sh", "os", "sd", "voc", "net")) and cells[IDS.index("shared-read")] == "ON", repr(cells))
    p.typed("u", idle=1.0)
    arow("G11", "U drops the five: no star left, nothing queued", all(not x.endswith("*") for x in p.rows()[ME][1]) and p.counts()[1].startswith("Nothing queued") and "dropped the 5 queued changes" in st(p.h), repr((p.counts(), st(p.h))))
    p.typed("t", idle=1.0)
    a0 = fg.audit_off()
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    arow("G10c", "R shows ONE command with only OFF words, in the table's order, and asks for no name", "modify.account %s sh-off os-off sd-off voc-off net-off" % ME in T and "so the account name has to be typed" not in T, T[-700:])
    p.typed("r", idle=3.0)
    new = fg.audit_new(a0) or ""
    arow("G10", "the register says no in fields 7, 8, 9, 10 and 15 and shared-read is untouched (blank); one audit line for each word", [field(ME, n) for n in (7, 8, 9, 10, 15)] == ["no"] * 5 and field(ME, 13) == ""
         and all(re.search(r"modify\.account %s account=%s$" % (w, re.escape(ME)), new, re.M) for w in ("sh-off", "os-off", "sd-off", "voc-off", "net-off")), repr(([field(ME, n) for n in (7, 8, 9, 10, 15, 13)], new[-300:])))
    p.typed("t", idle=1.0)
    arow("G10d", "T on an account with nothing on that is off as delivered queues nothing and says so", "has no gate on that is off as delivered" in st(p.h) and p.counts()[1].startswith("Nothing queued"), repr(st(p.h)))


def section_filter(p):
    say("\n--- G12: the filter")
    p.typed("f", idle=1.3)
    shown = [n for n in sorted(NAMES) if n not in (GG, GO)]
    p.shown = shown
    p.r = 0
    p.c = 0
    rows = p.rows()
    c1, _c2 = p.counts()
    arow("G12a", "F once: accounts of persons only", sorted(rows) == sorted(shown) and c1.startswith("accounts of persons: 3 of 5 accounts."), repr((sorted(rows), c1)))
    p.typed("f", idle=1.3)
    rows = p.rows()
    c1, _c2 = p.counts()
    arow("G12b", "F twice: only the accounts with a gate on that reaches beyond SD (zzg2, zzgg)", sorted(rows) == sorted([G2, GG]) and c1.startswith("accounts with a gate on that reaches beyond SD: 2 of 5 accounts."), repr((sorted(rows), c1)))
    p.shown = sorted([G2, GG])
    p.r = 0
    p.c = 0
    p.typed("f", idle=1.3)
    p.shown = sorted(NAMES)
    p.r = 0
    p.c = 0
    arow("G12c", "F a third time: all accounts again", sorted(p.rows()) == sorted(NAMES) and p.counts()[0].startswith("all accounts: 5 of 5"), repr(sorted(p.rows())))


def section_who(p):
    say("\n--- G13: who can reach the operating system, and the sessions")
    W = [p.line(n)[3:67].rstrip() for n in range(32, 38)]
    arow("G13a", "the box lists zzg2 with its gates that reach beyond SD (ssh sh os sd) and zzgg (sd); the sandbox user's account has none now", any(re.match(r"^zzg2\s+ssh sh os sd$", x) for x in W) and any(re.match(r"^zzgg\s+sd$", x) for x in W)
         and not any(x.startswith(ME) for x in W), repr(W))
    p.to(ME, "ssh")
    S = [p.line(n)[72:137].rstrip() for n in range(32, 34)]
    arow("G13b", "no session is in the account under the cursor: the box says so", S[0].startswith("No session is in %s now." % ME), repr(S))
    h2 = H(account=ME)                                         # an ordinary session of the sandbox user's own account
    h2.s.settle(1.5)
    p.key("f5", idle=2.0)
    S = [p.line(n)[72:137].rstrip() for n in range(32, 34)]
    arow("G13c", "a live session in the account: the box lists it by user number, login user and terminal", re.match(r"^user \d+\s+%s\s+\S+" % re.escape(ME), S[0]) is not None, repr(S))
    h2.end()
    p.key("f5", idle=2.0)


def section_mouse(p):
    say("\n--- G14: the mouse and help")
    p.h.click(29 + 6 * IDS.index("voc") + 2, 3 + sorted(NAMES).index(G3))
    p.r = sorted(NAMES).index(G3)
    p.c = IDS.index("voc")
    B = p.boxb()
    arow("G14a", "a click on a cell moves the cursor there: the box describes that account and gate", B[0].startswith(G3 + " (user, suspended)  -  Save VOC [voc]"), repr(B[:2]))
    # this sandbox has no shared account, so the help the page asks for is answered in words (11832); the record itself is sandbox-docs.py's, which loads it
    p.h.click(135, 2)
    T = re.sub(r"[|\s]+", " ", p.text())
    arow("G14b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here)", "Help is not installed here" in T, T[-500:])
    p.key("esc", idle=1.0)
    arow("G14b2", "Esc closes it and the matrix is still there", "Help is not installed here" not in re.sub(r"[|\s]+", " ", p.text()) and "Gates by account" in p.text(), p.text()[-300:])
    p.key("f1", idle=1.2)
    T = re.sub(r"[|\s]+", " ", p.text())
    arow("G14c", "F1 reaches it too", "Help is not installed here" in T, T[-500:])
    p.key("esc", idle=1.0)


def section_refresh(p):
    say("\n--- G15: F5 and the queue")
    p.to(ME, "bp")
    p.key("enter")
    rec = regf(G3)
    rec[11 - 1] = "yes"                          # zzg3's field 11, bp
    g.put(os.path.join(sh.SYS, "accounts", G3), "\n".join(rec[:18]) + "\n")
    p.key("f5", idle=2.0)
    arow("G15", "F5 reads the machine again (zzg3's bp is ON now) and the queued change of another account is still there", p.cell(G3, "bp") == "ON" and p.cell(ME, "bp") == "ON*", repr((p.cell(G3, "bp"), p.cell(ME, "bp"))))
    p.typed("u", idle=0.8)
    rec = regf(G3)
    rec[11 - 1] = "no"
    g.put(os.path.join(sh.SYS, "accounts", G3), "\n".join(rec[:18]) + "\n")


def section_group_account(p):
    say("\n--- G17: sh and os on a group account")
    snap = snapshot()
    p.to(GG, "os")
    p.key("enter")
    arow("G17a", "Enter on os of a group account queues nothing and says why", p.cell(GG, "os") == "off" and "is entered by whoever its Linux group admits" in st(p.h) and snapshot() == snap, repr((p.cell(GG, "os"), st(p.h))))
    p.to(GG, "sd")
    p.key("enter")
    p.typed("r", idle=1.5)
    T = re.sub(r"\s+", " ", p.text())
    arow("G17b", "sd on a group account can be turned off like any register gate (the box shows the OFF command)", "modify.account %s sd-off" % GG in T, T[-500:])
    p.key("esc", idle=1.0)
    p.typed("u", idle=0.8)


def section_home(p):
    """7 Nov 26 S.166 (owner: "make home vs TCL a gate that can be selected on the gates pane on means home display off means tcl"): the home column, read from register field 16
    (ACC$START, blank following the system default), switched with modify.account's start words, the register the evidence."""
    say("\n--- G20: the home gate (ON the home screen, off the command prompt)")
    p.to(ME, "home")
    was = field(ME, 16)
    dflt = home_default()
    arow("G20a", "the home cell of %s follows the system's default while its start field is blank (start.default here gives %s)" % (ME, dflt),
         was == "" and p.cell(ME, "home") == dflt, repr((was, dflt, p.cell(ME, "home"))))
    # The first switch is to the state the default does NOT give, so that the register must change; the second goes back the other way.
    first_word, first_cell, first_field = ("start-menu", "ON", "menu") if dflt == "off" else ("start-terminal", "off", "terminal")
    second_word, second_cell, second_field = ("start-terminal", "off", "terminal") if first_cell == "ON" else ("start-menu", "ON", "menu")
    a1 = fg.audit_off()
    p.key("enter")
    arow("G20b", "Enter queues the other state: the cell says %s*" % first_cell, p.cell(ME, "home") == first_cell + "*", repr(p.cell(ME, "home")))
    p.typed("r", idle=1.5)
    T = p.text()
    arow("G20c", "R shows modify.account NAME %s and asks for no name (where a person starts reaches nothing beyond SD)" % first_word,
         "modify.account %s %s" % (ME, first_word) in T and "so the account name has to be typed" not in T, T[-600:])
    p.typed("r", idle=2.5)
    new = fg.audit_new(a1) or ""
    arow("G20d", "Run: the register's start field is %s, the cell %s, and the audit trail has the verb's line" % (first_field, first_cell),
         field(ME, 16) == first_field and p.cell(ME, "home") == first_cell and re.search(r"modify\.account %s account=%s$" % (first_word, re.escape(ME)), new, re.M) is not None,
         repr((field(ME, 16), p.cell(ME, "home"), new[-200:])))
    p.key("enter")
    p.typed("r", idle=1.5)
    T2 = p.text()
    p.typed("r", idle=2.5)
    arow("G20e", "Enter, R (modify.account NAME %s), Run again: the field is %s and the cell %s" % (second_word, second_field, second_cell),
         "modify.account %s %s" % (ME, second_word) in T2 and field(ME, 16) == second_field and p.cell(ME, "home") == second_cell, repr((field(ME, 16), p.cell(ME, "home"))))
    GG_home = p.cell(GG, "home")
    arow("G20f", "a group account has the gate too (it applies to every kind of account): its cell is the default, %s, not a dash" % dflt, GG_home == dflt, repr(GG_home))


def section_null_and_small():
    say("\n--- G16: the null case, a small window")
    hold = os.path.join(box(), "hold-accounts")
    os.makedirs(hold, exist_ok=True)
    for n in NAMES:
        shutil.move(os.path.join(sh.SYS, "accounts", n), os.path.join(hold, n))
    try:
        p = Page()
        T = p.text()
        arow("G16", "with no account in the register but SDSYS the page says so in words (no empty pass), and a key does not crash it", "No account is shown." in T and "Gates by account" in T, T[-300:])
        p.key("enter")
        p.typed("r", idle=0.8)
        arow("G16b", "Enter and R with no account do nothing and the page is still there", "Gates by account" in p.text(), p.text()[-200:])
        p.quit()
    finally:
        for n in NAMES:
            shutil.move(os.path.join(hold, n), os.path.join(sh.SYS, "accounts", n))
        shutil.rmtree(hold, ignore_errors=True)
    p = Page(cols=100, rows=30)
    T = p.text()
    arow("G17", "a window under 140 by 43 gets no page (the toolkit's one size check)", "Gates by account" not in T and "The cell under the cursor" not in T, T[-300:])
    p.end()


def section_all_on():
    # 1 Nov 26: A (all on) and N (all off), the owner's convenience ("set all on, and then turn some off").  Until then this section held that A queued NOTHING.
    say("\n--- G18: A queues every gate ON and N every gate off, for the cursor's account; both only queue")
    p = open_page()
    snap = snapshot()
    p.to(ME, "ssh")
    before = p.rows()[ME][1]
    p.typed("a", idle=1.2)
    cells = p.rows()[ME][1]
    fixed = [i for i, x in enumerate(before) if x in ("-", "plan")] + [IDS.index("home")]      # S.166: A and N leave where the account starts alone
    arow("G18a", "A: every cell of %s that can change ends ON (ON* where it was off, ON where it was on already), a '-' or 'plan' cell is left alone, at least one was queued, and NOTHING ran (the register, the group file and the helper's calls as before)" % ME,
         all(cells[i] == before[i] for i in fixed) and all(x in ("ON", "ON*") for i, x in enumerate(cells) if i not in fixed) and "ON*" in cells and snapshot() == snap and "R runs them" in st(p.h), repr((before, cells, st(p.h))))
    i_sh = IDS.index("sh")
    p.to(ME, "sh")
    p.key("enter", idle=0.8)
    c2 = p.rows()[ME][1]
    arow("G18b", "Enter on one queued cell takes that one gate back (the owner's 'then turn some off'): sh is %s again and the others stay queued" % before[i_sh], c2[i_sh] == before[i_sh] and c2.count("ON*") == cells.count("ON*") - (1 if cells[i_sh] == "ON*" else 0), repr(c2))
    p.typed("r", idle=1.6)
    T = re.sub(r"\s+", " ", p.text())
    ok_box = ("modify.account %s " % ME) in T and "Run" in T and "Cancel" in T and "so the account name has to be typed" in T
    p.key("esc", idle=1.2)
    arow("G18c", "R shows the ONE command in the box, and a gate that reaches beyond SD still wants the account's name typed; Esc runs nothing", ok_box and snapshot() == snap, T[-600:])
    p.typed("u", idle=1.0)
    p.typed("n", idle=1.2)
    c3 = p.rows()[ME][1]
    arow("G18d", "N: every cell that can change ends off (off* where it was on), '-' and 'plan' left alone; nothing ran", all(c3[i] == before[i] for i in fixed) and all(x in ("off", "off*") for i, x in enumerate(c3) if i not in fixed) and snapshot() == snap, repr(c3))
    p.typed("u", idle=1.0)
    arow("G18e", "U drops it: no star left", all(not x.endswith("*") for x in p.rows()[ME][1]), repr(p.rows()[ME][1]))
    p.quit()


def left(p):
    """Has the page gone?  DISPLAY at the TCL prompt prints its text on a line of its own (the echoed command line starts with the prompt); on the page the keys would be the page's."""
    if "Gates by account" in p.text():                 # 2 Nov 26 review: never type the probe into a page that is still there (its keys would queue gates)
        p.s.settle(1.0)
        if "Gates by account" in p.text():
            return False
    p.typed("display ZZ.LEFT\r", idle=1.5)
    return "Gates by account" not in p.text() and any(l.strip() == "ZZ.LEFT" for l in p.h.lines())


def section_leave():
    say("\n--- G19: leaving the page with changes queued (S.88 P10)")

    def shc(p):
        """the sh cell of the sandbox user's row, or None when the page (and so the row) is gone: a page that left must fail a row, not stop the suite"""
        return p.rows().get(ME, (None, [None] * len(IDS), None))[1][IDS.index("sh")]

    snap = snapshot()
    a0 = fg.audit_off()
    p = open_page()
    p.key("ctrl-q", idle=1.5)
    T = p.text()
    arow("G19a", "nothing queued: Ctrl-Q leaves at once, with no question", "Leave the gate matrix?" not in T and left(p), T[-400:])
    p.end()
    p = open_page()
    p.to(ME, "sh")
    p.key("enter")
    p.key("ctrl-q", idle=1.5)
    T = re.sub(r"[|\s]+", " ", p.text())
    arow("G19b", "a change queued: Ctrl-Q opens the question - its title, the three buttons, the command the queue would be, how much is queued - and nothing has run",
         all(w in T for w in ("Leave the gate matrix?", "Run the changes", "Leave without them", "Cancel", "modify.account %s sh-on" % ME, "1 queued change of 1 account not run yet")) and snapshot() == snap, T[-900:])
    p.key("enter", idle=1.2)
    arow("G19c", "Enter is Cancel: the page is still there, the cell is still ON*, the status line says the changes are still here, nothing ran",
         "Gates by account" in p.text() and "Leave the gate matrix?" not in p.text() and shc(p) == "ON*" and "queued changes are still here" in st(p.h) and snapshot() == snap, repr((shc(p), st(p.h))))
    p.key("f10", idle=1.0)
    p.key("enter", idle=1.5)
    asked = "Leave the gate matrix?" in p.text()
    p.key("esc", idle=1.2)
    arow("G19d", "File > Quit (F10, Enter) asks the same question, and Esc in the box is Cancel: the page and the queue are still there",
         asked and "Gates by account" in p.text() and "Leave the gate matrix?" not in p.text() and shc(p) == "ON*" and snapshot() == snap, repr((asked, shc(p), st(p.h))))
    p.key("esc", idle=1.0)
    asked = "Leave the gate matrix?" in p.text()
    p.key("esc", idle=1.0)
    arow("G19e", "Esc on the page does not leave (the Esc rule opens the menu bar), asks nothing, and a second Esc closes the bar: the page and the queue are still there",
         not asked and "Gates by account" in p.text() and shc(p) == "ON*", repr((asked, shc(p), st(p.h))))
    p.key("ctrl-q", idle=1.5)
    p.typed("l", idle=1.5)
    gone = left(p)
    arow("G19f", "Leave without them (l): the page closes and nothing ran - every register record, the group file and the helper's calls as before, no modify.account line in the audit trail",
         gone and snapshot() == snap and "modify.account" not in (fg.audit_new(a0) or ""), repr((gone, fg.audit_new(a0))))
    p.end()
    p = open_page()
    p.to(ME, "sh")
    p.key("enter")
    p.key("ctrl-q", idle=1.5)
    p.typed("r", idle=1.6)
    T = re.sub(r"[|\s]+", " ", p.text())
    box_ok = "Run this command?" in T and ("modify.account %s sh-on" % ME) in T and "so the account name has to be typed" in T
    p.key("esc", idle=1.5)
    arow("G19g", "Run the changes (r) shows R's own box for the account - its title, the command, the name to be typed; Esc there runs nothing, and the page stays and says the change was not run",
         box_ok and "Gates by account" in p.text() and shc(p) == "ON*" and "not run, so the page stays" in st(p.h) and snapshot() == snap, repr((box_ok, T[-600:], st(p.h))))
    p.key("ctrl-q", idle=1.5)
    p.typed("r", idle=1.6)
    p.typed("r", idle=1.3)
    p.typed(ME + "\r", idle=3.0)
    new = fg.audit_new(a0) or ""
    gone = left(p)
    arow("G19", "Run the changes, Run and the account's name: the register's field 7 says yes (read from the disk), the audit trail has the verb's line, and with nothing left the page closes",
         field(ME, 7) == "yes" and re.search(r"modify\.account sh-on account=%s$" % re.escape(ME), new, re.M) is not None and gone, repr((field(ME, 7), new[-200:], gone)))
    p.end()
    rec = regf(ME)
    rec[7 - 1] = "no"                            # put sh back as the other sections expect it
    g.put(os.path.join(sh.SYS, "accounts", ME), "\n".join(rec[:18]) + "\n")


STOP_AFTER_G5 = False


def main():
    global STOP_AFTER_G5, ONLY
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-gates.py <dir> [--build] [--mutant=%s] [--only=%s]" % ("|".join(MUTANTS), ",".join(SECTIONS)))
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), None)
    if only is not None:
        ONLY = [s.strip() for s in only.split(",") if s.strip()]
        if not ONLY or any(s not in SECTIONS for s in ONLY):
            bail("--only takes section names from: %s" % " ".join(SECTIONS))
    try:
        sh.setup("sandbox-tool-gates.py")
        setup_gates()
        if mutant is not None:
            mutate(mutant)
            compile_page()
            STOP_AFTER_G5 = (mutant == "no-typed-name")
            say("sandbox-tool-gates: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if ONLY is not None:
            say("sandbox-tool-gates: --only %s" % ",".join(ONLY))
        p = section_open()
        if mutant is None:
            if chosen("cell"):
                section_cell(p)
            if chosen("queue"):
                section_queue(p)
        if mutant in (None, "no-typed-name") and chosen("run"):
            section_run_on(p)
        if mutant in (None, "route-both-wrong"):
            if mutant is None and chosen("several"):
                section_several(p)
            if chosen("route"):
                section_route(p)
        if mutant in (None, "needs-not-checked") and chosen("needs"):
            section_needs(p)
        if mutant in (None, "tighten-queues-on") and chosen("tighten"):
            section_tighten(p)
        if mutant is None:
            for nm, fn in (("filter", section_filter), ("who", section_who), ("mouse", section_mouse), ("refresh", section_refresh), ("group", section_group_account), ("home", section_home)):
                if chosen(nm):
                    fn(p)
        p.quit()
        if mutant is None and chosen("small"):
            section_null_and_small()
        if mutant in (None, "all-on-skips-test") and chosen("allon"):
            section_all_on()
        if mutant in (None, "leave-at-once", "leave-default") and chosen("leave"):
            section_leave()
    finally:
        restore_home_fixtures()
        sh.teardown()
    say("\nsandbox-tool-gates: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"G\d+", i).group(0) for i in FAILED_IDS if re.match(r"G\d+", i)})
        ok = want == got
        say("sandbox-tool-gates: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
