#!/usr/bin/env python3
#
# sandbox-tool-accounts.py - the accounts page, TOOL.ACCOUNTS, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A3; plan .claude/plan-fullscreen-toolkit.md section 5).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-accounts.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session opens TOOL.ACCOUNTS on a 140 by 43 terminal.  Register records are made by hand (a user account, a suspended one, a group account, an other
# account) beside the sandbox's own fixture accounts, and the REAL modify.account runs for suspend and unsuspend.
#
# WHAT A SANDBOX CANNOT DO.  Creating and deleting an account make and remove Linux users and groups (sd-elevate, root), and a person is added to a group the same way, so no row
# here shows an account created, deleted or a person added: those are the witness on a real install (the Debian 13 Clone VM).  What the rows do show: the page lists the register as the
# disk has it; every guard refuses before a box; every box is what the page says it is and Cancel runs nothing; the sentence the page builds is the one the verb receives; the typed-name
# box for a delete wants the account's own name and a wrong word runs nothing; the real suspend and unsuspend change the register's field and the audit trail.
#
#   AA0  an ordinary account has no tool.accounts; a VOC entry that points at the program gets the page's own refusal
#   AA1  the page opens: one audit line; the counts, the order, the kind, the state and the gates that are on of every account are the register's (a Python reader of the records)
#   AA2  a second session is signed on in an account: the page counts it as LISTU does and names it
#   AA3  the box at the foot shows the account under the cursor: path, kind and the gates
#   AA4  S: the box shows the sentence, Esc runs nothing, Run changes the register's field 5 on the disk and the audit trail, and the page shows it; S again lifts it
#   AA5  A and R: refused on an account that is not a group account; a bad user name is refused; a good one shows 'modify.account <group> add|delete <user>' and Esc runs nothing
#   AA6  C: a bad kind, a bad name, a name that exists and a bad door or path are refused in words; each kind shows its own sentence in a box and Esc makes nothing
#   AA7  X: the sentence (with remove.home when asked), the typed-name box, a wrong word runs nothing and the account is still registered
#   AA8  the mouse, F1, a small window, an input that ends
# NOT HELD: an account made or removed, a person added to a group, the terminal handed to a verb (the VM), the help text itself (sandbox-docs.py).
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


sh = _load("sandbox_home_for_toolaccounts", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
LAST_LISTU = []
MUTANT = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ACC = "zzhd"
OTHER = "zzhm"
WRITER = """   open 'voc' to v else
      crt 'ZZAW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$tool_accounts' to v, 'ztacc' on error
      crt 'ZZAW refused ':status()
      stop
   end
   crt 'ZZAW written'
end
"""

MUTANTS = {
    # name: (old text of the sandbox's tool_accounts, new text, the row ids that must fail and no others, the last section run)
    "suspend-wrong-word": ("      sent = 'modify.account ' : anm<ci> : ' unsuspended'\n", "      sent = 'modify.account ' : anm<ci> : ' suspended'\n", ["AA4"], "AA4"),
    "person-any-kind": ("   if akind<ci> # 'GROUP' then\n      msg = anm<ci> : ' is not a group account", "   if 0 then\n      msg = anm<ci> : ' is not a group account", ["AA5"], "AA5"),
    "delete-untyped": ("   typed = anm<ci>\n", "   typed = ''\n", ["AA7"], "AA7"),
}

GATE_ORDER = ["sh", "os", "sd", "voc", "bp", "dict", "net", "shared-read", "shared-write"]
GATE_FIELD = {"sh": 7, "os": 8, "sd": 9, "voc": 10, "bp": 11, "dict": 12, "net": 15, "shared-read": 13, "shared-write": 14}

# a user account, a suspended one, a group account and an other account, beside the sandbox's fixture accounts: path, group, suspended, sh os sd voc bp dict, shared-read shared-write net
HAND = {
    "zzaa": ("user", "sdu_zzaa", "", ["yes", "yes", "no", "no", "no", "yes"], ["", "", ""]),
    "zzab": ("user", "sdu_zzab", "SUSPENDED", ["no", "no", "no", "yes", "yes", "yes"], ["no", "yes", "yes"]),
    "zzgrp": ("group", "sdg_zzgrp", "", ["no", "no", "no", "yes", "no", "no"], ["", "", ""]),
    "zzoth": ("other", None, "", ["yes", "no", "yes", "no", "no", "no"], ["", "", ""]),
}


def sys_accounts():
    return os.path.join(sh.SYS, "accounts")


def register_ids():
    return sorted(n for n in os.listdir(sys_accounts()) if n != "sdsys")


def make_hand_accounts():
    for name, (kind, grp, susp, gates, rest) in HAND.items():
        path = os.path.join(sh.BOX, "group_accounts" if kind == "group" else "user_accounts", name)
        os.makedirs(path, exist_ok=True)
        fields = [path, "hand-made %s account" % kind, grp if grp else g.GROUP, "", susp, ""] + gates + rest + [""]
        g.reg_write(name, fields)


def read_fields(name):
    return g.reg_read(name)


def kind_of(fields):
    grp = fields[2] if len(fields) > 2 else ""
    return "USER" if grp.startswith("sdu_") else ("GROUP" if grp.startswith("sdg_") else "OTHER")


def gates_on(fields):
    out = []
    for gid in GATE_ORDER:
        idx = GATE_FIELD[gid]
        raw = fields[idx - 1].strip().upper() if len(fields) >= idx else ""
        if gid == "shared-read":
            if raw != "NO":
                out.append(gid)
        elif raw == "YES":
            out.append(gid)
    return out


def listu_counts():
    """The sessions signed on in each account, as a separate administrator session's LISTU shows them."""
    global LAST_LISTU
    counts = {}
    LAST_LISTU = g.adm(["LISTU"])
    for ln in LAST_LISTU:
        if re.match(r"^\*?\s*\d+\s+\d+\s", ln):
            m = re.search(r",\s*(\S+)\s*$", ln)
            if m:
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def audit_lines():
    try:
        return [ln for ln in open(os.path.join(sh.SYS, "audit"), "rb").read().decode("latin-1").split("\n") if ln != ""]
    except OSError:
        return []


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def st(h):
    return h.line(40)


def setup_pages():
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_accounts"), os.path.join(sh.SYS, "gpl.bp", "tool_accounts"))
    out = g.adm(["BASIC gpl.bp tool_accounts"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_accounts did not compile in the sandbox:\n" + "\n".join(out[-8:]))
    with open(os.path.join(sh.SYS, "audit"), "ab"):                 # a session appends to the audit file and never makes it
        pass
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzaw"), WRITER)
    make_hand_accounts()


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_accounts")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_accounts"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    """A session on tool.accounts on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.accounts\r", idle=4.0)

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

    def visible(self):
        out = {}
        for y in range(9, 26):
            t = self.line(y)[3:137]
            name = t[2:22].strip()
            if name:
                out[name] = {"mark": t[0:2].strip(), "kind": t[22:29].strip(), "state": t[29:40].strip(), "gates": t[40:81].strip(), "sess": t[81:91].strip()}
        return out

    def collect(self):
        self.key("home", 0.6)
        seen = dict(self.visible())
        for _ in range(8):
            before = len(seen)
            self.key("pgdn", 0.6)
            seen.update(self.visible())
            if len(seen) == before:
                break
        self.key("home", 0.6)
        return seen

    def detail(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(28, 39)))

    def to(self, name):
        self.key("home", 0.5)
        for _ in range(60):
            if self.line(28)[3:3 + len(name) + 1].startswith(name + " "):
                return True
            self.key("down", 0.3)
        return False

    def ask(self, text, existing=""):
        self.h.typed("\x7f" * len(existing) + text + "\r", idle=1.0)

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def box_open(p):
    T = norm(p.text())
    return "Cancel" in T and "Run" in T


def check_rows(seen, sess=None):
    """The differential: every registered account but SDSYS has a row whose kind, state and gates are the register's."""
    bad = []
    ids = register_ids()
    if sorted(seen) != ids:
        bad.append(("names", sorted(seen), ids))
    for name in ids:
        if name not in seen:
            continue
        f = read_fields(name)
        s = seen[name]
        want = (kind_of(f).lower(), "SUSPENDED" if f[4].strip().upper() == "SUSPENDED" else "active", " ".join(gates_on(f)) or "(none)")
        if (s["kind"], s["state"], s["gates"]) != want:
            bad.append((name, (s["kind"], s["state"], s["gates"]), want))
        if sess is not None and s["sess"] != str(sess.get(name, 0)):
            bad.append((name, "sessions", s["sess"], sess.get(name, 0)))
    return not bad, "%d rows seen; first differences %s" % (len(seen), bad[:3])


# ------------------------------------------------------------------------------------------------------------------------------- the sections

def section_aa0():
    say("\n--- AA0: an ordinary account")
    out = g.plain(ACC, ["tool.accounts"])
    T = norm(" ".join(out))
    arow("AA0a", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)", "Every account" not in T and "The account under the cursor" not in T and len(out) > 0, T[:300])
    out = g.plain(ACC, ["BASIC bp zzaw", "RUN bp zzaw"])
    wrote = has(out, r"^ZZAW written$")
    out = g.plain(ACC, ["ztacc"])
    T = norm(" ".join(out))
    arow("AA0b", "a VOC entry an ordinary account made for the program gets the page's own refusal (message 11800), not 'not a command', and no page", wrote and "is for the administrator only" in T and "The account under the cursor" not in T, repr((wrote, T[:300])))


def section_aa1():
    say("\n--- AA1: the page opens")
    a0 = len(audit_lines())
    p = Page()
    if "The account under the cursor" not in p.text():
        dump(p.h)
        bail("tool.accounts never drew its page, so no row below can be believed")
    mine = [ln for ln in audit_lines()[a0:] if " tool " in ln]
    arow("AA1a", "opening the page wrote one audit line, 'tool start app=tool.accounts', and no other 'tool' line", len(mine) == 1 and mine[0].endswith("tool start app=tool.accounts"), repr(mine))
    ids = register_ids()
    kinds = [kind_of(read_fields(n)) for n in ids]
    susp = sum(1 for n in ids if read_fields(n)[4].strip().upper() == "SUSPENDED")
    top = p.top()
    want = "%d accounts: %d user, %d group, %d other.   Suspended: %d." % (len(ids), kinds.count("USER"), kinds.count("GROUP"), kinds.count("OTHER"), susp)
    arow("AA1b", "the top counts the accounts, by kind, and the suspended ones, as the register has them: '%s'" % want, norm(want) in top, top[:200])
    seen = p.collect()
    ok, detail = check_rows(seen, listu_counts())
    arow("AA1c", "every registered account but SDSYS has a row, in name order, whose kind, state, gates that are on and sessions are the register's and LISTU's (a Python reader of the records)", ok and list(seen) == ids, detail)
    arow("AA1d", "SDSYS is not listed", "sdsys" not in seen, repr(list(seen)))
    return p


def section_aa2(p):
    say("\n--- AA2: a session is signed on in an account")
    other = H(account=OTHER)
    try:
        p.key("f5", 2.0)
        counts = listu_counts()
        seen = p.collect()
        ok, detail = check_rows(seen, counts)
        total = sum(counts.values()) - 1                                  # the LISTU session that counted them is not one the page saw
        arow("AA2a", "the page counts the sessions per account as LISTU does (%s has %d) and says how many are signed on in the top box (%d)" % (OTHER, counts.get(OTHER, 0), total),
             ok and counts.get(OTHER, 0) >= 1 and ("Sessions signed on now: %d" % total) in p.top(), detail + " | " + p.top()[:200] + " | LISTU " + repr(LAST_LISTU[-4:]))
        arow("AA2b", "the box at the foot for that account names the session", p.to(OTHER) and "Signed on in it: user" in p.detail(), p.detail()[-200:])
    finally:
        other.end()
    time.sleep(2.0)


def section_aa3(p):
    say("\n--- AA3: the account under the cursor")
    ok = p.to("zzgrp")
    d = p.detail()
    f = read_fields("zzgrp")
    arow("AA3a", "the box for the group account names it, says group, shows its path as the register has it and the gates that are on", ok and "zzgrp group active path: " + f[0] in d and ("Gates that are on: " + " ".join(gates_on(f))) in d, d[:300])
    p.to("zzab")
    d = p.detail()
    arow("AA3b", "the box for the suspended account says SUSPENDED", "zzab user SUSPENDED" in d, d[:200])


def section_aa4(p):
    say("\n--- AA4: suspend and lift")
    p.to("zzaa")
    a0 = len(audit_lines())
    f0 = read_fields("zzaa")
    p.key("s", 1.5)
    T = norm(p.text())
    arow("AA4a", "S shows 'modify.account zzaa suspended' and what it does in a box", box_open(p) and "modify.account zzaa suspended" in T and "LOGIN, ssh and the API refuse it" in T, T[-500:])
    p.key("esc", 1.2)
    arow("AA4b", "Esc runs nothing: the register's field 5 is as it was and the audit trail has no modify.account line", "nothing was run" in st(p) and read_fields("zzaa")[4] == f0[4] and not [ln for ln in audit_lines()[a0:] if "modify.account" in ln], st(p))
    p.key("s", 1.5)
    p.h.typed("r", idle=6.0)
    f1 = read_fields("zzaa")
    new = [ln for ln in audit_lines()[a0:] if "modify.account" in ln and "zzaa" in ln]
    seen = p.visible()
    arow("AA4c", "Run: the register's field 5 on the disk is SUSPENDED, the audit trail has the verb's line, the page shows SUSPENDED for the account and counts it", f1[4].strip().upper() == "SUSPENDED" and len(new) >= 1
         and seen.get("zzaa", {}).get("state") == "SUSPENDED" and "modify.account zzaa suspended ran (status" in st(p), repr((f1[4], new[-1:], seen.get("zzaa"), st(p))))
    p.to("zzaa")
    p.key("s", 1.5)
    T = norm(p.text())
    arow("AA4d", "S on a suspended account shows 'modify.account zzaa unsuspended'", box_open(p) and "modify.account zzaa unsuspended" in T, T[-400:])
    p.h.typed("r", idle=6.0)
    f2 = read_fields("zzaa")
    arow("AA4e", "Run: the suspension is lifted on the disk and the page shows the account active", f2[4].strip() == "" and p.visible().get("zzaa", {}).get("state") == "active", repr((f2[4], p.visible().get("zzaa"), st(p))))


def section_aa5(p):
    say("\n--- AA5: the people of a group account")
    a0 = len(audit_lines())
    p.to("zzaa")
    p.key("a", 1.2)
    arow("AA5a", "A on a user account is refused in words and asks nothing", "is not a group account" in st(p) and "Linux user to add" not in p.text(), st(p))
    p.to("zzgrp")
    p.key("a", 1.2)
    p.ask("Bad/User!")
    arow("AA5b", "A on the group account asks for a user, and a name with a slash and a mark is refused in words before any box", "a user name has only a-z, 0-9, dot, dash and underscore" in st(p) and not box_open(p), st(p))
    p.key("a", 1.2)
    p.ask("zzperson")
    T = norm(p.text())
    arow("AA5c", "a good name shows 'modify.account zzgrp add zzperson' in a box", box_open(p) and "modify.account zzgrp add zzperson" in T and "joins the Linux group of zzgrp" in T, T[-400:])
    p.key("esc", 1.0)
    p.key("r", 1.2)
    p.ask("zzperson")
    T = norm(p.text())
    arow("AA5d", "R shows 'modify.account zzgrp delete zzperson' in a box", box_open(p) and "modify.account zzgrp delete zzperson" in T and "leaves the Linux group of zzgrp" in T, T[-400:])
    p.key("esc", 1.0)
    arow("AA5e", "nothing was run: the audit trail has no modify.account line", not [ln for ln in audit_lines()[a0:] if "modify.account" in ln], "")


def section_aa6(p):
    say("\n--- AA6: create")
    a0 = len(audit_lines())
    before = register_ids()
    p.key("c", 1.2)
    p.ask("banana", "user")
    arow("AA6a", "a kind that is not user, group or other is refused in words", "the kind is user, group or other" in st(p) and not box_open(p), st(p))
    p.key("c", 1.2)
    p.ask("group", "user")
    p.ask("Bad Name")
    arow("AA6b", "a name with a capital and a space is refused in words", "an account name has only a-z, 0-9, dot, dash and underscore" in st(p) and not box_open(p), st(p))
    p.key("c", 1.2)
    p.ask("group", "user")
    p.ask("zzaa")
    arow("AA6c", "a name that is an account already is refused in words", "zzaa is already an account" in st(p) and not box_open(p), st(p))
    p.key("c", 1.2)
    p.ask("group", "user")
    p.ask("zznewg")
    T = norm(p.text())
    arow("AA6d", "kind group shows 'create.account group zznewg no.query' in a box", box_open(p) and "create.account group zznewg no.query" in T and "no Linux user of its own" in T, T[-400:])
    p.key("esc", 1.0)
    p.key("c", 1.2)
    p.ask("user", "user")
    p.ask("zznewu")
    p.ask("maybe", "none")
    arow("AA6e", "kind user with a door word that is not none, ssh, api or both is refused in words", "the doors are none, ssh, api or both" in st(p) and not box_open(p), st(p))
    p.key("c", 1.2)
    p.ask("user", "user")
    p.ask("zznewu")
    p.ask("both", "none")
    T = norm(p.text())
    arow("AA6f", "kind user shows 'create.account user zznewu both' in a box that says the terminal is given to the verb for the password", box_open(p) and "create.account user zznewu both" in T and "asks for the password of the new person" in T, T[-500:])
    p.key("esc", 1.0)
    p.key("c", 1.2)
    p.ask("other", "user")
    p.ask("zznewo")
    p.ask("relative/dir")
    arow("AA6g", "kind other with a relative path is refused in words", "give an absolute path with no space in it" in st(p) and not box_open(p), st(p))
    p.key("c", 1.2)
    p.ask("other", "user")
    p.ask("zznewo")
    p.ask("/tmp")
    T = norm(p.text())
    arow("AA6h", "kind other with an absolute path shows 'create.account other zznewo /tmp no.query' in a box", box_open(p) and "create.account other zznewo /tmp no.query" in T, T[-400:])
    p.key("esc", 1.0)
    arow("AA6i", "nothing was made: the register holds the accounts it held and the audit trail has no create.account line", register_ids() == before and not [ln for ln in audit_lines()[a0:] if "create.account" in ln], repr(register_ids()))


def section_aa7(p):
    say("\n--- AA7: delete")
    a0 = len(audit_lines())
    before = register_ids()
    p.to("zzaa")
    p.key("x", 1.2)
    p.ask("n", "n")
    T = norm(p.text())
    arow("AA7a", "X on a user account asks about the home directory (default n) and then shows 'delete.account zzaa' in a box that says there is no taking it back", box_open(p) and "delete.account zzaa" in T and "remove.home" not in T and "no taking this back" in T, T[-500:])
    p.key("esc", 1.0)
    p.key("x", 1.2)
    p.ask("y", "n")
    T = norm(p.text())
    arow("AA7b", "answering y adds remove.home to the sentence", box_open(p) and "delete.account zzaa remove.home" in T, T[-400:])
    p.h.typed("r", idle=1.5)
    p.h.typed("nope\r", idle=1.5)
    arow("AA7c", "Run asks for the account's own name; a wrong word runs nothing: the status line says so, zzaa is still registered, and the page is still the page", "zzaa" in register_ids() and "The account under the cursor" in p.text() and not [ln for ln in audit_lines()[a0:] if "delete.account" in ln], st(p))
    p.to("zzgrp")
    p.key("x", 1.2)
    T = norm(p.text())
    arow("AA7d", "X on the group account goes straight to the box: 'delete.account zzgrp', no question about a home directory", box_open(p) and "delete.account zzgrp" in T and "Also remove the home directory" not in T, T[-400:])
    p.key("esc", 1.0)
    arow("AA7e", "no account was removed", register_ids() == before, repr(register_ids()))


def section_aa8(p):
    say("\n--- AA8: the mouse, F1, a small window, an input that ends")
    p.key("home", 0.6)
    names = list(p.visible())
    p.h.click(20, 11)
    arow("AA8a", "a click on the third row puts the cursor there: the box at the foot names that account", p.line(28)[3:3 + len(names[2]) + 1].startswith(names[2] + " "), repr((names[:3], p.line(28)[3:60])))
    p.h.click(135, 2)
    T = norm(p.text())
    arow("AA8b", "a click on the [?] reaches the help box ($tk_help says help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("AA8c", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.accounts\r", idle=3.0)
    T = h.text()
    arow("AA8d", "a window under 140 by 43 gets no page (the toolkit's one size check)", "The account under the cursor" not in T and "Every account" not in T, T[-300:])
    h.end()
    env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(sh.BOX, "aa8-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.accounts\n")
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
    with open(os.path.join(sh.BOX, "aa8-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("AA8e", "a page whose input ends ends by itself within 20 seconds; the output shows it did start (the null case)", ended and "The account under the cursor" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-accounts.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    global MUTANT
    MUTANT = mutant
    last = MUTANTS[mutant][3] if mutant else "AA8"
    order = ["AA2", "AA3", "AA4", "AA5", "AA6", "AA7", "AA8"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    p = None
    try:
        sh.setup("sandbox-tool-accounts.py")
        setup_pages()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-accounts: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_aa0()
        p = section_aa1()
        if mutant is None:
            section_aa2(p)
            section_aa3(p)
        if run("AA4"):
            section_aa4(p)
        if run("AA5"):
            section_aa5(p)
        if mutant is None:
            section_aa6(p)
        if run("AA7"):
            section_aa7(p)
        if mutant is None:
            section_aa8(p)
        else:
            p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-accounts: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"AA\d+", i).group(0) for i in FAILED_IDS if re.match(r"AA\d+", i)})
        ok = want == got
        say("sandbox-tool-accounts: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
