#!/usr/bin/env python3
"""test-tk-keys-units.py - the toolkit's action registry ($tk_keys, tk.h's key table) held as TEXT (S.88 phase 3.9, steps S0 to S2).

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tk-keys-units.py [--s0] [--selftest [--from=N]]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the BASIC of the 24 programs that build a key table (`call $tk_keys('add', ...)`), parses all of their
rows, and holds the rules a hand edit breaks unnoticed: seven arguments at every call, no key bound to two actions in one pane, one label and one key
per action, quit on Ctrl-Q and help on F1, a handler in the page's source for every key it registers, the keys the plan reserves (F2, F6, F10, F11)
and the mnemonics of the IDE's menus.  Part B (below the marker lines in this file) holds the registry's own operations in `tk_keys` and `tk_fkeys`,
and the owner's answer 25 of 29 Oct 26: ***an action reachable through the registry (a menu entry, the palette, the key list) runs through the SAME
handler as its key*** - the registry holds no code path that runs an action; it returns the action's code and the page's own handler does the rest.

***IT RUNS NOTHING.***  It cannot say that a handler's own gate (K$PATH.OK, K$EDIT.OK, the administrator test) refuses anybody, that a menu bar is
drawn, or that a key press reaches the handler: those are the sandbox suites (`sandbox-tk-base.py` rows on tool_tktest).  A text check can only
say that there is exactly one place where an action's code is turned into work, and that the registry has no other.

--s0      run part A only (step S0 of the plan: the check alone, on a tree whose tk_keys has not changed).
--selftest breaks each rule in the way an edit plausibly would and requires a check to notice; a mutant nothing catches is a failure.
          --from=N runs the mutants from number N on (the first of part B is printed as M_P39B).

THE EXCEPTIONS LEDGER.  Each entry is a defect that is true of the tree today and is the Phase 5 work list.  An entry that stops being true makes
the check FAIL ("the ledger names X, which no longer fires: remove it"), so the ledger can only shrink by someone reading it.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
MSG = os.path.join(SDSYS, "messages")

EXPECT_PROGRAMS = 24
EXPECT_ADD_ROWS = 245             # the 232 rows of the tree before 29 Oct 26, the two rows of tool_tktest's pilot (S2), the Esc row of tool_mygates and the Ctrl-O and Esc rows of tool_viewers (30 Oct 26, the F0a pilots of $tk_menubar)
KNOWN_OPS_S0 = {"add", "name", "action"}

# an action that has two keys on purpose (the second is for a terminal that keeps the first for itself)
TWO_KEYS = {}
RESERVED = ("f2", "f6", "f10", "f11")
# the action a reserved key may stand for (plan 5.2 / K8: F2 find an action, F6 the next pane, F10 the menu is NOT a page key, F11 gone)
RESERVED_OK = {"f2": {"palette", "find"}, "f6": {"nextpane"}}
MYMENU_MOVED = ("f2", "f3", "f4", "f6")

LEDGER = {
    "reserved": {
        "tool_files:f11": "F11 filter: F11 is the terminal emulator's full-screen key (plan 5.2); Phase 5 moves the filter",
        "tool_voc:f11": "F11 filter (as tool_files)",
        "tool_dict:f11": "F11 filter (as tool_files)",
        "tool_catalog:f11": "F11 filter (as tool_files)",
        "tool_test:f11": "F11 filter (as tool_files)",
        "tool_tktest:f11": "the throw-away test app's pick-a-file key; it goes with the app",
        "tool_tktest:f6": "the throw-away test app's table refresh; it goes with the app",
        "tool_tktest:f10": "the throw-away test app's multi-pick key; it goes with the app",
        "mymenu:f2": "mymenu add (F2 is find an action); Phase 5 moves it (owner answer 20: Ctrl-N)",
        "mymenu:f3": "mymenu F3 (Phase 5)",
        "mymenu:f4": "mymenu F4 (Phase 5)",
        "mymenu:f6": "mymenu F6 down (F6 is the next pane); Phase 5 moves it",
        "tool_home:f10": "tool_home binds F10 for its menu without Esc first (K8)",
    },
    "mnemonic": {
        "11225:file:c": "File menu: 'Write a &copy' and '&Close record' are both C, so Close record cannot be reached by its letter (d2a fixes the message)",
        "11228:build:c": "Build menu: '&Compile' and 'Compile and &catalogue' are both C (d2a fixes the message)",
    },
    "handler": {
        "ide:esc/menu": "the IDE's Esc is handled where the form is read (the menu bar), not in do.key",
        "tool_remote:2/": "tool_remote's digit keys 2 to 4 choose a pane by number (a computed test, not a literal case)",
        "tool_remote:3/": "(as 2)",
        "tool_remote:4/": "(as 2)",
    },
    "conflict": {},
    "quitkey": {
        "tool_home:ctrl-q is signout": "the home screen leaves by signing out; Ctrl-Q is its quit",
        "tool_home:has no quit": "(as above)",
    },
    "helpkey": {
        "mymenu:has no help": "mymenu registers no F1 (Phase 5 converts it)",
        "tool_home:has no help": "the home screen's help is the Help menu's Keys entry",
        "tool_keys:has no help": "tool.keys is exempt (owner answer 18: it is the page that shows keys)",
    },
    "twokeys": {
        "tool_query:option": "an option list chooses with Enter or the space bar (the table of two-key actions)",
    },
}

IDE_MENU_MESSAGES = (11225, 11226, 11227, 11228, 11229, 11230, 11654)


# ---------------------------------------------------------------------------------------------------------------------- reading

def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = cut_comment(line)
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def cut_comment(line):
    """the index of a ';*' that is outside quotes, or -1"""
    q = ""
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = ""
        elif ch in "'\"":
            q = ch
        elif ch == ";" and line[i + 1:i + 2] == "*":
            return i
    return -1


def load():
    raw = {}
    for f in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, f)
        if os.path.isfile(p):
            with open(p, "r", encoding="latin-1") as fh:
                raw[f] = fh.read()
    for n in IDE_MENU_MESSAGES:
        with open(os.path.join(MSG, str(n)), "r", encoding="latin-1") as fh:
            raw["msg:%d" % n] = fh.read()
    for n in range(11186, 11190):
        p = os.path.join(MSG, str(n))
        if os.path.exists(p):
            with open(p, "r", encoding="latin-1") as fh:
                raw["msg:%d" % n] = fh.read()
    return raw


def split_top(s, sep):
    """split on sep outside quotes and brackets"""
    parts, depth, q, cur = [], 0, "", ""
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = ""
        elif ch in "'\"":
            q = ch
            cur += ch
        elif ch in "([" or (sep == "," and ch == "<"):
            depth += 1
            cur += ch
        elif ch in ")]" or (sep == "," and ch == ">"):
            depth -= 1
            cur += ch
        elif ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts]


CALL = re.compile(r"call \$tk_keys\((.*)\)\s*$")


def calls_in(code):
    """[(line number, op, [args], text)] for every `call $tk_keys(` of a stripped program"""
    out = []
    for no, line in enumerate(code.split("\n"), 1):
        m = CALL.search(line)
        if m and "call $tk_keys(" in line:
            args = split_top(m.group(1), ",")
            out.append((no, args[0].strip("'") if args else "", args, line))
    return out


def literal(arg):
    """('lit', text) for a quoted string or a ':' chain of quoted strings and @sm / @fm / @vm; ('var', name) for a name; ('expr', text) otherwise"""
    arg = arg.strip()
    parts = split_top(arg, ":")
    text = ""
    for p in parts:
        if len(p) >= 2 and p[0] == p[-1] and p[0] in "'\"":
            text += p[1:-1]
        elif p in ("@sm", "@fm", "@vm"):
            text += "|"
        else:
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9.]*", arg):
                return ("var", arg)
            return ("expr", arg)
    return ("lit", text)


def rows_of(raw):
    """every 'add' row: dict(prog, line, key, label, act, panes (frozenset, empty = every pane), on ('on', 'off', 'cond'), problems)"""
    rows = []
    for prog in sorted(raw):
        if prog.startswith("msg:"):
            continue
        code = strip_bas(raw[prog])
        for no, op, args, line in calls_in(code):
            if op != "add":
                continue
            r = {"prog": prog, "line": no, "bad": [], "nargs": len(args), "args": args}
            if len(args) == 7:
                kind = {}
                for name, i in (("key", 2), ("label", 3), ("act", 4)):
                    k, v = literal(args[i])
                    if k != "lit":
                        r["bad"].append("%s is %s, not a quoted text" % (name, k))
                    r[name] = v
                k, v = literal(args[5])
                if k == "var":
                    m = None
                    for mm in re.finditer(r"^\s*%s\s*=\s*(.*)$" % re.escape(v), code, re.M):
                        m = mm
                    if m is None:
                        r["bad"].append("panes variable %s is not assigned in the program" % v)
                        v = ""
                    else:
                        k2, v2 = literal(m.group(1))
                        if k2 != "lit":
                            r["bad"].append("panes variable %s is not a text" % v)
                            v2 = ""
                        v = v2
                elif k == "expr":
                    r["bad"].append("panes is an expression")
                    v = ""
                r["panes"] = frozenset(x for x in re.split(r"[|]", v) if x)
                on = args[6].strip()
                r["on"] = "off" if on == "0" else ("on" if on in ("1", "''") else "cond")
                if on.startswith("(if ") and on.endswith(")"):
                    r["on"] = "cond"
                elif r["on"] == "on" and on not in ("1", "''"):
                    r["bad"].append("on is %s" % on)
            rows.append(r)
    return rows


# ---------------------------------------------------------------------------------------------------------------------- part A

def run_a(raw, rows):
    """{check name: [problem strings]}"""
    res = {}
    progs = sorted({r["prog"] for r in rows})
    ops_ok = KNOWN_OPS_S0
    tk = strip_bas(raw.get("tk_keys", ""))
    implemented = set(re.findall(r"case op = '([a-z]+)'", tk))
    if not implemented:
        implemented = ops_ok
    res["parse"] = []
    if len(progs) != EXPECT_PROGRAMS:
        res["parse"].append("%d programs build a key table, expected %d (%s)" % (len(progs), EXPECT_PROGRAMS, " ".join(progs)))
    if len(rows) != EXPECT_ADD_ROWS:
        res["parse"].append("%d 'add' rows found, expected %d" % (len(rows), EXPECT_ADD_ROWS))
    for r in rows:
        if r["nargs"] != 7:
            res["parse"].append("%s:%d add has %d arguments" % (r["prog"], r["line"], r["nargs"]))
        for b in r["bad"]:
            res["parse"].append("%s:%d %s" % (r["prog"], r["line"], b))
    res["args"] = []
    for prog in sorted(raw):
        if prog.startswith("msg:"):
            continue
        for no, op, args, line in calls_in(strip_bas(raw[prog])):
            if len(args) != 7:
                res["args"].append("%s:%d $tk_keys has %d arguments, not 7" % (prog, no, len(args)))
            if op not in implemented:
                res["args"].append("%s:%d $tk_keys op '%s' is not one tk_keys implements" % (prog, no, op))
    good = [r for r in rows if r["nargs"] == 7 and not r["bad"]]
    # (key, pane) bound to two actions
    res["conflict"] = []
    byprog = {}
    for r in good:
        byprog.setdefault(r["prog"], []).append(r)
    for prog, rs in byprog.items():
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a["key"] and a["key"] == b["key"] and a["act"] != b["act"] and "off" not in (a["on"], b["on"]):
                    if not a["panes"] or not b["panes"] or (a["panes"] & b["panes"]):
                        res["conflict"].append("%s:%s" % (prog, a["key"]))
    # one act, one label; one act, one key
    res["label"] = []
    res["twokeys"] = []
    for prog, rs in byprog.items():
        labels, keys = {}, {}
        for r in rs:
            labels.setdefault(r["act"], set()).add(r["label"])
            if r["key"]:
                keys.setdefault(r["act"], set()).add(r["key"])
        for act, ls in labels.items():
            if len(ls) > 1:
                res["label"].append("%s:%s has the labels %s" % (prog, act, sorted(ls)))
        for act, ks in keys.items():
            if len(ks) > 1 and ks != TWO_KEYS.get((prog, act)):
                res["twokeys"].append("%s:%s has the keys %s" % (prog, act, sorted(ks)))
    # quit is ctrl-q, help is f1
    res["quitkey"], res["helpkey"] = [], []
    for prog, rs in byprog.items():
        for r in rs:
            if r["act"] == "quit" and r["key"] != "ctrl-q":
                res["quitkey"].append("%s:quit is on %s" % (prog, r["key"]))
            if r["act"] == "help" and r["key"] != "f1":
                res["helpkey"].append("%s:help is on %s" % (prog, r["key"]))
            if r["key"] == "ctrl-q" and r["act"] != "quit":
                res["quitkey"].append("%s:ctrl-q is %s" % (prog, r["act"]))
            if r["key"] == "f1" and r["act"] != "help":
                res["helpkey"].append("%s:f1 is %s" % (prog, r["act"]))
        if not any(r["act"] == "quit" for r in rs):
            res["quitkey"].append("%s:has no quit" % prog)
        if not any(r["act"] == "help" for r in rs):
            res["helpkey"].append("%s:has no help" % prog)
    # a handler in the page's source for every registered key
    res["handler"] = []
    for prog, rs in byprog.items():
        body = "\n".join(l for l in strip_bas(raw[prog]).split("\n") if "$tk_keys('add'" not in l)
        for r in rs:
            if not r["key"] or r["on"] == "off":          # a menu-only action has no key; a row switched off needs no handler
                continue
            hit =(re.search(r"\bact\s*=\s*'%s'" % re.escape(r["act"]), body) is not None
                   or (r["key"] == "esc" and r["act"] == "menu" and "$tk_menubar('key'" in body)           # the bar takes Esc itself ($tk_menubar 'key': the Esc rule), whatever the page's own case says
                   or re.search(r"=\s*'%s'" % re.escape(r["key"]), body) is not None
                   or re.search(r"\bcase\b[^\n]*'%s'" % re.escape(r["key"]), body) is not None)
            if not hit:
                res["handler"].append("%s:%s/%s" % (prog, r["key"], r["act"]))
    # reserved keys
    res["reserved"] = []
    for prog, rs in byprog.items():
        for r in rs:
            if r["key"] in RESERVED and r["act"] not in RESERVED_OK.get(r["key"], set()):
                res["reserved"].append("%s:%s" % (prog, r["key"]))
            if prog == "mymenu" and r["key"] in MYMENU_MOVED:      # owner answer 20: mymenu's own keys give way to Ctrl-N, Del and u / d in Phase 5
                res["reserved"].append("%s:%s" % (prog, r["key"]))
    res["reserved"] = sorted(set(res["reserved"]))
    # the IDE's menus: one & in every entry, the mnemonics of a menu and of the titles all different
    res["mnemonic"] = []
    titles = {}
    for n in IDE_MENU_MESSAGES:
        text = raw.get("msg:%d" % n, "").rstrip("\n")
        items = text.split("|")
        title = items[0]
        if title.count("&") != 1:
            res["mnemonic"].append("%d:%s:title has %d marks" % (n, title, title.count("&")))
            continue
        t = re.search(r"&(.)", title).group(1).lower()
        if t in titles:
            res["mnemonic"].append("%d:%s:%s title letter %s is also %s's" % (n, title.replace("&", "").lower(), t, t, titles[t]))
        titles[t] = title.replace("&", "")
        seen = {}
        for it in items[1:]:
            label = it.split("~")[0]
            if label.count("&") != 1:
                res["mnemonic"].append("%d:%s:entry '%s' has %d marks" % (n, title.replace("&", "").lower(), label, label.count("&")))
                continue
            c = re.search(r"&(.)", label).group(1).lower()
            if c in seen:
                res["mnemonic"].append("%d:%s:%s" % (n, title.replace("&", "").lower(), c))
            seen[c] = label
    return res


def judge(res, ledger_on=True):
    """[(name, passed, detail)] - a problem in the ledger is allowed, a ledger entry that no longer fires is a failure"""
    out = []
    for name in sorted(res):
        probs = res[name]
        led = LEDGER.get(name, {}) if ledger_on else {}
        new = [p for p in probs if not any(p.startswith(k) for k in led)]
        stale = [k for k in led if not any(p.startswith(k) for p in probs)]
        detail = []
        if new:
            detail.append("NEW: " + "; ".join(new[:6]) + (" ..." if len(new) > 6 else ""))
        if stale:
            detail.append("the ledger names %s, which no longer fires: remove it" % ", ".join(stale))
        out.append((name, not detail, " | ".join(detail)))
    return out


A_TEXT = {
    "parse": "all 232 'add' rows of the 24 programs parse (key, label and action quoted, panes a text or a variable assigned in the program, on a number or an (if) expression)",
    "args": "every $tk_keys call has seven arguments and an op tk_keys implements",
    "conflict": "no key is bound to two actions in one pane (a null pane list overlaps every pane; a row switched off is out)",
    "label": "one action has one label in a page",
    "twokeys": "one action has one key in a page, except the table of two-key actions",
    "quitkey": "quit is Ctrl-Q and nothing else is, in every page",
    "helpkey": "help is F1 and nothing else is, in every page",
    "handler": "every key a page registers is acted on in that page's source (an act = 'x' case or the key's literal in a case)",
    "reserved": "the keys the plan reserves (F2 find an action, F6 next pane, F10, F11) are bound only to those actions - the rest is the ledger",
    "mnemonic": "the IDE's menus: one & in every entry, no letter twice in a menu or among the titles - the rest is the ledger",
}


# ---------------------------------------------------------------------------------------------------------------------- part B
# ---- PART B BEGINS (the registry's operations, fkeys, the messages, and the owner's answer 25) ----
def norm(text):
    return re.sub(r"\s+", " ", text)


REGISTRY_OPS = {"add", "name", "action", "menu", "why", "menus", "keyof", "keylist"}
# what a program that only lists and names actions must never contain: it would be a second way to run one
NO_RUN_WORDS = ("execute", "perform", "chain", "screen", "display", "print", "crt", "open", "openseq", "write", "writeseq", "writev", "delete", "kernel(", "@sentence",
                "stop", "abort", "call $", "call(", "input", "read")


def run_b(raw):
    res = {}
    tkh = norm(strip_bas(raw.get("tk.h", "")))
    tk = norm(strip_bas(raw.get("tk_keys", "")))
    fk = norm(strip_bas(raw.get("tk_fkeys", "")))
    app = strip_bas(raw.get("tool_tktest", ""))
    appn = norm(app)
    # the table's values: the first five did not move
    want = [("KEY", 1), ("LABEL", 2), ("ACT", 3), ("PANES", 4), ("ON", 5), ("MENU", 6), ("ENTRY", 7), ("WHY", 8), ("ROW", 9)]
    res["tablevalues"] = ["TK.K.%s is not %d" % (n, v) for n, v in want if re.search(r"\$define TK\.K\.%s +%d\b" % (n, v), tkh) is None]
    res["tablevalues"] += ["TK.K.%s is defined more than once" % n for n, v in want if len(re.findall(r"\$define TK\.K\.%s\b" % n, tkh)) != 1]
    # the subroutine: seven arguments, the ops, the 'add' line as the pages have always had it
    res["ops"] = []
    if "subroutine tk_keys(op, keys, a, b, c, d, e)" not in tk:
        res["ops"].append("tk_keys does not take seven arguments (op, keys, a, b, c, d, e)")
    got = set(re.findall(r"case op = '([a-z]+)'", tk))
    if got != REGISTRY_OPS:
        res["ops"].append("tk_keys implements %s, the registry has %s" % (sorted(got), sorted(REGISTRY_OPS)))
    if "case op = 'add' keys<-1> = a : @vm : b : @vm : c : @vm : d : @vm : e" not in tk:
        res["ops"].append("'add' no longer writes the five values of the page tables")
    # action: an empty key matches nothing, a switched off action or one with a reason is not returned
    res["action"] = []
    m = re.search(r"case op = 'action' (.*?) case op = 'menu'", tk)
    ab = m.group(1) if m else ""
    for what, text in (("the empty-key guard (a # '')", "if a # '' and keys<i, TK.K.KEY> = a"), ("the ON test", "keys<i, TK.K.ON> # '0'"),
                       ("the WHY skip", "keys<i, TK.K.WHY> = '' then"), ("the pane test", "index(@sm : panes : @sm, @sm : pane : @sm, 1)")):
        if text not in ab:
            res["action"].append("'action' lacks " + what)
    # why: takes the action out of use AND states the reason; gives back only an action that had one
    res["why"] = []
    m = re.search(r"case op = 'why' (.*?) case op = 'menus'", tk)
    wb = m.group(1) if m else ""
    if not re.search(r"if b # '' then keys<i, TK\.K\.ON> = 0 keys<i, TK\.K\.WHY> = b end else if keys<i, TK\.K\.WHY> # '' then keys<i, TK\.K\.WHY> = '' keys<i, TK\.K\.ON> = ''", wb):
        res["why"].append("'why' does not set ON 0 with the reason, or gives back an action that had none")
    # menus: the flag D, the shown key derived, the entries from the table
    res["menus"] = []
    m = re.search(r"case op = 'menus' (.*?) case op = 'keyof'", tk)
    mb = m.group(1) if m else ""
    m = re.search(r" act\.state: (.*?) return key\.name:", tk)
    st = m.group(1) if m else ""
    for what, text in (("the flag D from the action's state", "fl = (if ia then '' else 'D')"), ("the shown key derived (ik)", "ent = keys<i, TK.K.ENTRY> : @sm : ik : @sm : fa : @sm : fl"),
                       ("one entry an action", "if index(seen, @fm : fa : @fm, 1) = 0 then")):
        if text not in mb:
            res["menus"].append("'menus' lacks " + what)
    for what, text in (("enabled means ON # '0' and no reason", "if keys<j, TK.K.ON> # '0' and keys<j, TK.K.WHY> = '' then ia = 1"),
                       ("the pane scope", "if panes = '' or index(@sm : panes : @sm, @sm : pane : @sm, 1) then isc = 1")):
        if text not in st:
            res["menus"].append("act.state lacks " + what)
    # keyof returns the first ENABLED binding's key for the pane
    res["keyof"] = []
    m = re.search(r"case op = 'keyof' (.*?) case op = 'keylist'", tk)
    kb = m.group(1) if m else ""
    if "gosub act.state c = ikf" not in kb or "if ikf = '' then ikf = kj" not in st:
        res["keyof"].append("'keyof' does not return the first enabled binding's key")
    # the names
    res["name"] = []
    for what, text in (("PgUp", "kt = 'PgUp'"), ("PgDn", "kt = 'PgDn'"), ("Shift-", "pre = 'Shift-'"), ("Alt-", "pre = 'Alt-'"), ("^", "pre = '^'")):
        if text not in tk:
            res["name"].append("'name' lacks " + what)
    # the function-key row leaves out a row with no key and a row whose ROW is 0
    res["fkeys"] = []
    if "keys<i, TK.K.ROW> # '0'" not in fk:
        res["fkeys"].append("tk_fkeys does not skip ROW = 0")
    if "keys<i, TK.K.KEY> # ''" not in fk:
        res["fkeys"].append("tk_fkeys does not skip an empty key")
    # the messages 11186 to 11189
    res["messages"] = []
    for n in (11186, 11187, 11188, 11189):
        t = raw.get("msg:%d" % n)
        if t is None:
            res["messages"].append("message %d is missing" % n)
        elif not t.endswith("\n") or t.count("\n") != 1 or not t.strip():
            res["messages"].append("message %d is not one line" % n)
    if (raw.get("msg:11188") or "").count("%1") != 1:
        res["messages"].append("11188 must hold %1 once (the reason)")
    cited = {}
    for prog in raw:
        if not prog.startswith("msg:"):
            for x in re.findall(r"sysmsg\((111(?:8[6-9]))", strip_bas(raw[prog])):
                cited.setdefault(prog, set()).add(int(x))
    if cited.get("tk_keys") != {11188} or cited.get("tool_tktest") != {11189}:
        res["messages"].append("only tk_keys cites 11188 and only tool_tktest cites 11189 (got %s)" % {k: sorted(v) for k, v in cited.items()})
    # ***OWNER ANSWER 25: the registry runs nothing.***  It lists and names actions and returns an action id; the page's own handler is the only place an id becomes work.
    res["norun"] = []
    for name, src in (("tk_keys", strip_bas(raw.get("tk_keys", ""))), ("tk_fkeys", strip_bas(raw.get("tk_fkeys", "")))):
        for w in NO_RUN_WORDS:
            pat = re.escape(w) if not w[0].isalpha() or not w[-1].isalpha() else r"\b%s\b" % re.escape(w)
            # tk_fkeys calls $tk_keys 'name' and nothing else
            for mm in re.finditer(pat, src):
                line = src[src.rfind("\n", 0, mm.start()) + 1:src.find("\n", mm.end())]
                if name == "tk_fkeys" and w == "call $" and "call $tk_keys('name'" in line:
                    continue
                res["norun"].append("%s contains '%s': %s" % (name, w, line.strip()[:60]))
    targets = set(re.findall(r"gosub ([a-z.]+)", tk))
    if not targets <= {"act.state", "key.name"}:
        res["norun"].append("tk_keys gosubs %s, not only act.state and key.name" % sorted(targets - {"act.state", "key.name"}))
    # a page that puts actions in a menu runs a menu answer through the page's one case on the action id
    res["samehandler"] = []
    menus_users = []
    facade_users = []
    for prog in sorted(raw):
        if prog.startswith("msg:"):
            continue
        code = strip_bas(raw[prog])
        acts = [args[2].strip().strip("'") for no, op, args, line in calls_in(code) if op == "menu" and len(args) == 7]
        if not acts:
            continue
        menus_users.append(prog)
        if "$tk_menubar(" in code:
            # 30 Oct 26 (S.88 F0a): a page on the toolkit's bar.  The bar returns the KEY of the chosen action (field 4 of its answer is the name to dispatch on) and the page's own case on that
            # key does what it does for the key itself: ONE handler per action, the key's, with the registry running nothing.  So: every menu action has a key, the page asks the bar for a key
            # once and for a click once, takes each answer as `nm = mr<4>` once, and draws the bar before the frame.
            facade_users.append(prog)
            keyed = {args[4].strip().strip("'") for no, op, args, line in calls_in(code) if op == "add" and len(args) == 7 and args[2].strip().strip("'") != ""}
            for act in sorted(set(acts)):
                if act not in keyed:
                    res["samehandler"].append("%s: the menu action '%s' has no key, so the bar has nothing to replay through the page's case; a keyless action needs its row read" % (prog, act))
            for hook, want in (("'draw'", 1), ("'key'", 1), ("'click'", 1)):
                n = len(re.findall(r"call \$tk_menubar\(%s," % hook, code))
                if n != want:
                    res["samehandler"].append("%s: %d calls of $tk_menubar %s, expected %d" % (prog, n, hook, want))
            n = len(re.findall(r"\bnm = \w+<4>", code))
            if n != 2:
                res["samehandler"].append("%s: the bar's answer reaches nm %d times, expected 2 (the key hook and the click hook)" % (prog, n))
            if re.search(r"\bmr<[123]>", code) and not re.search(r"\bmr<1>\s*#\s*''", code):
                res["samehandler"].append("%s: the bar's answer is read for something other than the name to dispatch on" % prog)
            if code.find("call $tk_menubar('draw'") > code.find("call $tk_frame("):
                res["samehandler"].append("%s: the bar is not drawn before the frame" % prog)
            continue
        for act in sorted(set(acts)):
            lines = [l for l in code.split("\n") if re.match(r"\s*case\b", l) and re.search(r"\bact\s*=\s*'%s'" % re.escape(act), l)]
            if len(lines) != 1:
                res["samehandler"].append("%s: the action '%s' has %d 'case act' handlers, not one" % (prog, act, len(lines)))
        mcs = re.findall(r"screen menubar [^\n]*returning (\w+)", code)
        if len(mcs) != 1:
            res["samehandler"].append("%s: %d menu bars that return an answer, not one" % (prog, len(mcs)))
            continue
        mc = mcs[0]
        uses = re.findall(r"\b%s\b" % re.escape(mc), code)
        if len(uses) != 2 or not re.search(r"^\s*act = %s\s*$" % re.escape(mc), code, re.M):
            res["samehandler"].append("%s: the menu answer %s is used %d times; it must be used once, as `act = %s`" % (prog, mc, len(uses), mc))
        first_case = re.search(r"^\s*begin case\s*\n\s*case act = ", code, re.M)
        ans = code.find("act = " + mc)
        if not first_case or ans < 0 or ans > first_case.start():
            res["samehandler"].append("%s: the menu answer does not reach `act` before the program's case on act" % prog)
        if "call $tk_keys('action', keys, k, pane, act, '', '')" not in code or code.find("act = " + mc) < code.find("call $tk_keys('action'"):
            res["samehandler"].append("%s: ACT is not set from the key table before the menu answer replaces it" % prog)
    if [p for p in menus_users if p not in facade_users] != ["tool_tktest"]:
        res["samehandler"].append("the programs that call $tk_keys 'menu' are %s; the registry's own pilot is tool_tktest, the pages on $tk_menubar are held by the rules above, and any other needs its row read" % menus_users)
    # mnemonics of the registry's own menus: one & in every entry, unique in a menu and among the titles
    res["regmenu"] = []
    for prog in sorted(raw):
        if prog.startswith("msg:"):
            continue
        menus = {}
        for no, op, args, line in calls_in(strip_bas(raw[prog])):
            if op == "menu" and len(args) == 7:
                k, title = literal(args[3])
                k2, entry = literal(args[4])
                if k != "lit" or k2 != "lit":
                    res["regmenu"].append("%s:%d title or entry is not a quoted text" % (prog, no))
                    continue
                menus.setdefault(title, []).append(entry)
        letters = {}
        for title, entries in menus.items():
            if title.count("&") != 1:
                res["regmenu"].append("%s: title '%s' has %d marks" % (prog, title, title.count("&")))
                continue
            t = re.search(r"&(.)", title).group(1).lower()
            if t in letters:
                res["regmenu"].append("%s: title letter %s is used twice" % (prog, t))
            letters[t] = 1
            seen = set()
            for en in entries:
                if en.count("&") != 1:
                    res["regmenu"].append("%s: entry '%s' has %d marks" % (prog, en, en.count("&")))
                    continue
                c = re.search(r"&(.)", en).group(1).lower()
                if c in seen:
                    res["regmenu"].append("%s: menu %s uses the letter %s twice" % (prog, title, c))
                seen.add(c)
    # the pilot in tool_tktest
    res["pilot"] = []
    for what, text in (("only with the word menubar", "pilot = (if index(' ' : @sentence : ' ', ' menubar ', 1) then 1 else 0)"),
                       ("Esc is on no function-key row", "keys<nk, TK.K.ROW> = 0"),
                       ("Save as has no key", "call $tk_keys('add', keys, '', 'save as', 'saveas', 'A' : @sm : 'B', 1)"),
                       ("Save as has a reason from message 11189", "call $tk_keys('why', keys, 'saveas', sysmsg(11189), '', '', '')"),
                       ("the bar is made by 'menus' for the focused pane", "call $tk_keys('menus', keys, '', menus, pane, '', '')"),
                       ("the bar is drawn on row 0", "screen menubar menus row 0 draw else null")):
        if text not in appn:
            res["pilot"].append("tool_tktest lacks: " + what)
    return res


B_TEXT = {
    "tablevalues": "tk.h: the key table's nine values, the first five where they were (MENU 6, ENTRY 7, WHY 8, ROW 9 are new)",
    "ops": "tk_keys keeps seven arguments and the five-value 'add'; it implements add, name, action, menu, why, menus, keyof, keylist and no other op",
    "action": "'action': an empty key matches nothing, a switched-off action or one with a reason is not returned, the pane is tested",
    "why": "'why' takes the action out of use together with the reason, and gives back only an action that had one",
    "menus": "'menus': the flag D comes from the action's state (switched off, a reason, or a pane that does not use it); the shown key is derived; one entry an action",
    "keyof": "'keyof' returns the key of the first enabled binding for the pane",
    "name": "'name' knows PgUp, PgDn, ^, Shift- and Alt-",
    "fkeys": "tk_fkeys leaves a key-less row and a ROW = 0 row off the function-key row",
    "messages": "messages 11186 to 11189 exist, are one line each, 11188 holds %1; only tk_keys cites 11188 and only tool_tktest 11189",
    "norun": "OWNER ANSWER 25: tk_keys and tk_fkeys contain no word that runs, opens, writes, calls or stops anything (and gosub only act.state and key.name): the registry cannot run an action",
    "samehandler": "OWNER ANSWER 25: in a page that puts actions in a menu, every such action has exactly one `case act` handler and the menu answer is used only as `act = answer`, before that case",
    "regmenu": "the registry's own menus: one & in every title and entry, no letter twice in a menu or among the titles",
    "pilot": "tool_tktest's pilot: only with the word menubar, Esc off the key row, Save as with no key and a reason, the bar made by 'menus' and drawn on row 0",
}
# ---- PART B ENDS ----

# ---------------------------------------------------------------------------------------------------------------------- the run

def run(raw, s0=False):
    rows = rows_of(raw)
    res = run_a(raw, rows)
    texts = dict(A_TEXT)
    if not s0:
        res.update(run_b(raw))
        texts.update(B_TEXT)
    return judge(res), texts, rows


M = []         # (file, text to change, replacement, what it breaks, the check that must go red)
M_A = len(M)


def mut(fname, old, new, what, expect):
    M.append((fname, old, new, what, expect))


mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)", "call $tk_keys('add', keys, 'ctrl-x', 'quit', 'quit', '', 1)", "quit moved off Ctrl-Q", "quitkey")
mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-l', 'clear', 'clear', '', 1)", "call $tk_keys('add', keys, 'ctrl-r', 'clear', 'clear', '', 1)", "two actions on Ctrl-R", "conflict")
mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-t', 'theme', 'theme', '', 1)", "call $tk_keys('add', keys, 'ctrl-t', 'theme', 'raw', '', 1)", "one action with two labels and two keys", "label")
mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)", "call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', 1)", "a call with six arguments", "args")
mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-t', 'theme', 'theme', '', 1)", "call $tk_keys('add', keys, 'ctrl-9', 'theme', 'zzact', '', 1)", "a key whose action has no handler in the page", "handler")
mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-l', 'clear', 'clear', '', 1)", "call $tk_keys('add', keys, 'f11', 'clear', 'clear', '', 1)", "a new F11 binding outside the ledger", "reserved")
mut("tool_keys", "call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)", "call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)\n   call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)", "a row more than the table has", "parse")
mut("msg:11654", "&Ask about this record", "&Explain about this record", "a duplicate mnemonic in the AI menu", "mnemonic")
mut("msg:11654", "&Ask about this record", "Ask about this record", "an entry with no mnemonic", "mnemonic")
mut("tool_home", "call $tk_keys('add', keys, 'f10', 'menu', 'menu', '', 1)", "call $tk_keys('add', keys, 'f9', 'menu', 'menu', '', 1)","tool_home's F10 moved: the ledger entry no longer fires", "reserved")

# ---- PART B MUTANTS BEGIN ----
M_P39B = len(M)
mut("tk_keys", "if a # '' and keys<i, TK.K.KEY> = a", "if keys<i, TK.K.KEY> = a", "an empty key matches the first empty-key row", "action")
mut("tk_keys", "and keys<i, TK.K.ON> # '0' and keys<i, TK.K.WHY> = '' then", "and keys<i, TK.K.ON> # '0' then", "'action' returns an action that has a reason", "action")
mut("tk_keys", "keys<i, TK.K.ON> = 0\n", "keys<i, TK.K.ON> = 1\n", "'why' leaves the action in use", "why")
mut("tk_keys", "fl = (if ia then '' else 'D')", "fl = ''", "no entry is ever disabled", "menus")
mut("tk_keys", "if keys<j, TK.K.ON> # '0' and keys<j, TK.K.WHY> = '' then", "if keys<j, TK.K.ON> # '0' then", "a reason does not disable the entry", "menus")
mut("tk_keys", "if ikf = '' then ikf = kj", "ikf = kj", "keyof returns the last binding, not the first enabled one", "keyof")
mut("tk_keys", "kt = 'PgDn'", "kt = 'Pgdn'", "PgDn is written Pgdn", "name")
mut("tk_keys", "keys<-1> = a : @vm : b : @vm : c : @vm : d : @vm : e", "keys<-1> = a : @vm : b : @vm : c : @vm : d", "'add' drops the ON value", "ops")
mut("tk_keys", "      case op = 'keyof'\n", "      case op = 'keyof'\n         execute c\n", "the registry executes a sentence", "norun")
mut("tk_keys", "      case op = 'keyof'\n", "      case op = 'keyof'\n         call $tk_run('x', 's', o, st, er)\n", "the registry runs a command through $tk_run", "norun")
mut("tk_keys", "      case op = 'keyof'\n", "      case op = 'keyof'\n         screen text 'x' at 0,0\n", "the registry writes to the screen", "norun")
mut("tk_keys", "         c = ikf\n", "         c = ikf\n         gosub run.it\n", "the registry gosubs a routine of its own that is not one of the two", "norun")
mut("tk_fkeys", "keys<i, TK.K.ROW> # '0' and ", "", "ROW = 0 stays on the key row", "fkeys")
mut("tk_fkeys", " and keys<i, TK.K.KEY> # ''", "", "a key-less row is on the key row", "fkeys")
mut("tool_tktest", "            act = mc\n", "            msg = mc\n", "a menu answer is handled by code of its own, not the case on act", "samehandler")
mut("tool_tktest", "            msg = 'sorted'", "            msg = 'sorted'\n         case act = 'sort'\n            msg = 'again'", "a second handler for the action the menu offers", "samehandler")
mut("tool_tktest", "      call $tk_keys('why', keys, 'saveas', sysmsg(11189), '', '', '')\n", "", "Save as has no reason: the pilot's null case is gone", "pilot")
mut("tool_tktest", "'refresh', '&Actions', '&Refresh'", "'refresh', '&Actions', '&Seek'", "two entries with the letter S (Seek, Sort)", "regmenu")
mut("tool_tktest", "'refresh', '&Actions', '&Refresh'", "'refresh', '&Actions', '&Sample'", "two entries with the letter S", "regmenu")
mut("msg:11188", "%1", "reason", "message 11188 loses its substitution", "messages")
mut("tk.h", "$define TK.K.ROW       9", "$define TK.K.ROW       8", "ROW takes WHY's place", "tablevalues")
# 30 Oct 26 (S.88 F0a pilot): tool_mygates on $tk_menubar - the first of these is marker M_F0A for --from=
M_F0A = len(M)
mut("tool_mygates", "   call $tk_keys('menu', keys, 'refresh', '&View', '&Refresh', '', '')\n", "   call $tk_keys('menu', keys, 'refresh', '&View', '&Refresh', '', '')\n   call $tk_keys('menu', keys, 'saveas', '&File', 'Save &as', '', '')\n", "a menu action with no key on a bar page", "samehandler")
mut("tool_mygates", "      if mr<1> # '' then nm = mr<4>\n", "", "the bar's answer is not taken in the loop", "samehandler")
mut("tool_mygates", "      nm = mr<4>\n      gosub on.key\n", "      nm = mr<2>\n      gosub on.key\n", "a click on the bar is dispatched on the action id, not the name", "samehandler")
mut("tool_mygates", "      call $tk_menubar('draw', ctx, keys, 'My gates', '', '', mr)", "      call $tk_frame(ctx, keys, 'My gates', msg)\n      call $tk_menubar('draw', ctx, keys, 'My gates', '', '', mr)", "the bar is drawn after the frame", "samehandler")
mut("tool_mygates", "      if nm # '' then call $tk_menubar('key', ctx, keys, 'My gates', nm, 0, mr)", "      if nm # '' then mr = ''", "the Esc row has no bar to take it", "handler")
# ---- PART B MUTANTS END ----


def selftest(frm, s0):
    try:
        raw = load()
    except (OSError, IOError) as e:
        print("CANNOT RUN: %s" % e)
        return 2
    base, _, _ = run(raw, s0)
    if any(not ok for _, ok, _ in base):
        print("selftest: the real files already fail a check")
        return 1
    killed, missed = 0, []
    for i, (fname, old, new, what, expect) in enumerate(M):
        if i < frm:
            continue
        if s0 and i >= M_P39B:
            continue
        if fname not in raw:
            print("  [CANNOT] %s: no such file %s" % (what, fname))
            return 2
        if raw[fname].count(old) != 1:
            print("  [CANNOT] %s: the text to change is found %d times in %s, not once" % (what, raw[fname].count(old), fname))
            return 2
        m = dict(raw)
        m[fname] = raw[fname].replace(old, new)
        res, _, _ = run(m, s0)
        red = [n for n, ok, _ in res if not ok]
        if expect in red:
            killed += 1
            print("  [killed] #%d %s  <- %s" % (i, what, ", ".join(red)))
        else:
            missed.append(what)
            print("  [MISSED] #%d %s (wanted %s red, got %s)" % (i, what, expect, red or "none"))
    print("selftest: %d mutants run, %d killed, %d missed (M_P39B = %d)" % (killed + len(missed), killed, len(missed), M_P39B))
    return 0 if not missed and killed else 1


def main():
    s0 = "--s0" in sys.argv
    if "--selftest" in sys.argv:
        frm = 0
        for a in sys.argv:
            if a.startswith("--from="):
                frm = int(a[7:])
        return selftest(frm, s0)
    try:
        raw = load()
    except (OSError, IOError) as e:
        print("CANNOT RUN: %s" % e)
        return 2
    res, texts, rows = run(raw, s0)
    bad = 0
    print("test-tk-keys-units: read %d 'add' rows of %d programs%s" % (len(rows), len({r['prog'] for r in rows}), " (part A only: --s0)" if s0 else ""))
    for name, ok, detail in res:
        print("  [%s] %s: %s%s" % ("ok" if ok else "FAIL", name, texts.get(name, ""), ("\n        " + detail) if detail else ""))
        bad += 0 if ok else 1
    print("test-tk-keys-units: %d passed, %d failed" % (len(res) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
