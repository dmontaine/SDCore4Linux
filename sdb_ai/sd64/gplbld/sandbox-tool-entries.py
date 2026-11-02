#!/usr/bin/env python3
#
# sandbox-tool-entries.py - the master files page, first stage (S.96 M1a): TOOL.ENTRIES, the VOC entries of every account by pointer, read only.  A private SD, no install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-entries.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# THE INSTRUMENT.  What the page shows is judged against things it does not read itself: the register records this suite WROTE (the gates, the group, the suspension), the VOC
# records an administrator program wrote into each account's VOC file, and COUNT VOC run in the account by a separate administrator session (the number of entries).  The null
# case of every "not shown" row is the same row where the thing IS shown.
#
#   E0   an ordinary account has no tool.entries
#   E1   the page opens, writes one 'tool start' audit line, lists the accounts with their gates, whether the sdsys user is in the group, and suspension
#   E2   the entries of the account under the cursor are its own VOC (a record written only there), the count is COUNT VOC's, and another account shows its own
#   E3   an account whose VOC cannot be opened says so
#   E4   / keeps the entries holding a part of the id; Esc takes it off
#   E5   F finds an id in the VOC of every account; Enter on a hit goes to that entry in its account
#   E6   the page READ ONLY: no VOC changed, the audit trail holds the start line and nothing else
#   E7   F1 and the [?]; a window under 140 by 43 gets no page; Ctrl-Q leaves
# NOT HELD: SDSYS in the group (a sandbox has no sdsys user: the column can only say no or n/a here), the help text itself (sandbox-docs.py).
import importlib.util
import os
import re
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


sh = _load("sandbox_home_for_toolentries", "sandbox-home.py")
say, row, bail, has, dump, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
FAILED_IDS = []

# the fixture accounts: name -> (voc-edit, bp-edit, dict-edit, group, suspended); the page shows the gates as v d b
ACCOUNTS = {
    "ze1": ("yes", "yes", "yes", None, ""),
    "ze2": ("no", "no", "no", None, ""),
    "ze3": ("yes", "yes", "no", None, ""),
    "ze4": ("yes", "yes", "yes", "", ""),               # no group in the register
    "ze5": ("no", "no", "no", None, "SUSPENDED"),
}
BAD = "ze6"                                              # registered, its directory holds no VOC

MUTANTS = {
    # name: (old text of the sandbox's tool_entries, new text, the row ids that must fail and no others, the last section run)
    "gates": ("gset := (if upcase(trim(arec<ACC$DICT.EDIT>)) = 'YES' then 'd' else '-')", "gset := (if upcase(trim(arec<ACC$BP.EDIT>)) = 'YES' then 'd' else '-')", ["E1"], "E1"),
    "find-one": ("   for a = 1 to an\n      ca = a\n", "   for a = 1 to 1\n      ca = a\n", ["E5"], "E5a"),
    "heading": (" or index(upcase(dhead), upcase(pat), 1) > 0)", ")", ["E8"], "E8"),
    "text-prefix": ("is.out = (if kernel(K$PATH.IN, apath<ca> : @fm : tp) then 0 else 1)", "is.out = (if tp[1, len(apath<ca>)] = apath<ca> then 0 else 1)", ["E8"], "E8"),
}


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def audit_off():
    path = os.path.join(sh.SYS, "audit")
    if not os.path.exists(path):
        open(path, "ab").close()
    return os.path.getsize(path)


def audit_new(off):
    with open(os.path.join(sh.SYS, "audit"), "rb") as f:
        f.seek(off)
        return f.read().decode("utf-8", errors="replace")


def apath(name):
    return os.path.join(g.BOX, "user_accounts", name)


def voc_write(prog, items):
    """An administrator's program in SDSYS bp that writes records into the VOC FILES of fixture accounts: items = [(account, id, [field, ...])]; it must print FIX done."""
    lines = ["$internal"]
    for i, acct in enumerate(sorted({a for a, _, _ in items})):
        lines.append("   openpath '%s/voc' to v%d else crt 'FIX no voc %s' ; stop" % (apath(acct), i, acct))
    for acct, rid, fields in items:
        n = sorted({a for a, _, _ in items}).index(acct)
        lines.append("   write %s to v%d, '%s'" % (" : @fm : ".join("'%s'" % f for f in fields), n, rid))
    lines += ["   crt 'FIX done'", "end", ""]
    g.put(os.path.join(sh.SYS, "bp", prog), "\n".join(lines))
    out = g.adm(["BASIC bp %s" % prog, "RUN bp %s" % prog], internal=True)
    if not has(out, r"^FIX done$"):
        bail("%s did not run:\n%s" % (prog, "\n".join(out[-6:])))


def count_voc(acct):
    """The number of entries of the account's VOC, counted by a SEPARATE administrator session in the account (the oracle for the page's count)."""
    out = g.adm(["LOGTO %s" % acct, "COUNT VOC"])
    for ln in out:
        m = re.search(r"\b(\d+) record", ln)
        if m:
            return int(m.group(1))
    bail("COUNT VOC in %s printed no count:\n%s" % (acct, "\n".join(out[-4:])))


def setup_page():
    prog = "tool_entries"
    import shutil
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", prog), os.path.join(sh.SYS, "gpl.bp", prog))
    out = g.adm(["BASIC gpl.bp %s" % prog], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("%s did not compile in the sandbox:\n%s" % (prog, "\n".join(out[-8:])))
    # the VOC record that makes the verb (SDSYS's VOC only: voc_template)
    g.put(os.path.join(sh.SYS, "bp", "zzevoc"), "\n".join(["$internal", "   openpath @sdsys:@ds:'voc' to v else crt 'EVOC no voc' ; stop",
                                                          "   write 'V':@fm:'CA':@fm:'$tool_entries' to v, 'tool.entries'", "   crt 'EVOC done'", "end", ""]))
    out = g.adm(["BASIC bp zzevoc", "RUN bp zzevoc"], internal=True)
    if not has(out, r"^EVOC done$"):
        bail("the tool.entries VOC record was not made:\n" + "\n".join(out[-5:]))
    for name, (voc, bp, dct, grp, susp) in ACCOUNTS.items():
        g.FIXTURES[name] = ("no", "no")
        g.build_account(name)
        group = g.GROUP if grp is None else grp
        g.reg_write(name, [apath(name), "", group, "", susp, "", "no", "no", "", voc, bp, dct])
    os.makedirs(apath(BAD), exist_ok=True)
    g.reg_write(BAD, [apath(BAD), "", g.GROUP, "", "", "", "no", "no", "", "no", "no", "no"])
    # THE OWNER'S RULE (3 Nov 26): a pointer whose target lies outside the account is marked >.  zeq is a Q-pointer to another account; zeesc is a file pointer written as ../ze2/zecust2, which
    # STARTS with ze1's own directory as text and lives in ze2's (the kernel's geometry resolves .. and sees it; a text prefix does not).
    voc_write("zzeptr", [("ze1", "zeq", ["Q", "ze2", "zecust2"]), ("ze1", "zeesc", ["F", "../ze2/zecust2", "../ze2/zecust2.dic"])])
    voc_write("zzefix", [("ze1", "zzqa", ["PA", "DISPLAY QA1"]), ("ze1", "zzqb", ["V", "CA", "$zzkf"]), ("ze1", "zzonly1", ["X", "text one"]),
                         ("ze2", "zzqa", ["PA", "DISPLAY QA2"]), ("ze2", "zzonly2", ["X", "text two"]), ("ze5", "zzqc", ["PA", "DISPLAY QC"])])
    # M1b: a data file with a dictionary in two accounts, made by an administrator session in the account (CREATE.FILE makes the pointer, the data and the dictionary) and a program
    # that writes the items.  zqalias has a heading that its id does not hold; zqfirst is in both accounts under the same heading.
    for acct, fname, items in (("ze1", "zecust", [("zqfirst", "D", "1", "First Name"), ("zqgiven", "D", "2", "Given Name"), ("zqalias", "D", "3", "Nickname"), ("zqdbl", "I", "@ID * 2", "Double")]),
                               ("ze2", "zecust2", [("zqfirst", "D", "1", "First Name"), ("zqother", "D", "2", "Other")])):
        body = ["program zzed", "   open 'dict', '%s' to d else crt 'ED no dict' ; stop" % fname]
        for iid, ity, f2, head in items:
            body.append("   write '%s':@fm:'%s':@fm:'':@fm:'%s':@fm:'10L':@fm:'S' on d, '%s'" % (ity, f2, head, iid))
        body += ["   crt 'ED done'", "end"]
        g.put(os.path.join(apath(acct), "bp", "zzed"), "\n".join(body) + "\n")
        out = g.adm(["LOGTO %s" % acct, "CREATE.FILE %s DYNAMIC" % fname, "BASIC bp zzed", "RUN bp zzed"])
        if not has(out, r"^ED done$"):
            bail("the dictionary of %s in %s was not made:\n%s" % (fname, acct, "\n".join(out[-8:])))


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_entries")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_entries"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.entries\r", idle=3.5)

    def text(self):
        return norm(self.h.text())

    def key(self, name, idle=0.6):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def st(self):
        return self.h.line(40)

    def on(self):
        """The account the Entries box is titled with."""
        m = re.search(r"(?:VOC|Dictionary items) of (\S+)", self.text())
        return m.group(1) if m else None

    def walk_to(self, name, n=40):
        """Down until the Entries box is titled with the account, then Up if Down did not reach it (the focus is the Accounts box)."""
        for direction in ("down", "up"):
            for _ in range(n):
                if self.on() == name:
                    return True
                before = self.on()
                self.key(direction, 0.5)
                if self.on() == before:
                    # the screen may simply not be drawn yet (E3 failed in three of four mutant runs and in no plain run: the walk gave up at the first key whose redraw was late);
                    # let the pty settle up to a second before believing the cursor did not move
                    for _ in range(3):
                        self.h.alive()
                        if self.on() != before:
                            break
                    if self.on() == before:
                        break
        return self.on() == name

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def section_e0():
    say("\n--- E0: an ordinary account has no tool.entries")
    out = g.plain("zzhd", ["tool.entries"])
    T = norm(" ".join(out))
    arow("E0", "an ordinary session is told it is not a command, and no page appears", "Accounts" not in T and "not in your VOC" in T, T[:300])


def section_e1():
    say("\n--- E1: the page and its accounts")
    a0 = audit_off()
    p = Page()
    T = p.text()
    if "Accounts" not in T or "What this means" not in T:
        dump(p.h)
        bail("tool.entries never drew its page, so no row below can be believed")
    new = audit_new(a0)
    arow("E1a", "opening the page writes 'tool start app=tool.entries' once", len(re.findall(r"tool start app=tool\.entries$", new, re.M)) == 1, repr(new[-200:]))
    # the accounts are listed in name order; the list shows ten rows, so walk to each to see it
    seen = {}
    for name in list(ACCOUNTS) + [BAD]:
        p.walk_to(name)
        # the row of the Accounts box: name, three gate characters, the sdsys word, and 'suspended' or nothing (the third word keeps the Entries box's title, 'VOC of ze1 -----', out of it)
        m = re.search(r"(?<![\w-])%s ([vdb-]{3}) (no|yes|n/a)\b( suspended)?" % name, p.text())
        seen[name] = m.groups() if m else None
    arow("E1b", "the gates are shown as v d b or a dash: ze1 vdb, ze2 ---, ze3 v-b (dict-edit off), ze4 vdb, ze5 ---",
         [seen[n][0] if seen[n] else None for n in ("ze1", "ze2", "ze3", "ze4", "ze5")] == ["vdb", "---", "v-b", "vdb", "---"], repr(seen))
    arow("E1c", "the sdsys column: no for an account with a group the sdsys user is not in, n/a for one with no group in the register (ze4)",
         seen["ze1"] and seen["ze1"][1] == "no" and seen["ze4"] and seen["ze4"][1] == "n/a" and seen["ze5"] and seen["ze5"][1] == "no", repr(seen))
    arow("E1d", "only the suspended account says so (ze5) - and the others do not (the control)", bool(seen["ze5"] and seen["ze5"][2]) and not any(seen[n] and seen[n][2] for n in ("ze1", "ze2", "ze3", "ze4")), repr(seen))
    return p


def section_e2(p):
    say("\n--- E2: the entries are the account's own VOC")
    n1 = count_voc("ze1")
    n2 = count_voc("ze2")
    p.walk_to("ze1")
    p.key("tab", 0.6)
    p.key("end", 0.8)                  # the box shows ten rows: the zz entries sort last
    T = p.text()
    arow("E2a", "ze1: the entry only ze1 has (zzqa, a paragraph pointing at DISPLAY QA1) is listed with its type and what it does", re.search(r"zzqa PA DISPLAY QA1", T) is not None, T[:900])
    p.key("tab", 0.6)
    arow("E2b", "ze1: the count line is COUNT VOC's number (%d), all of them read" % n1, re.search(r"\b%d of %d entries\." % (n1, n1), T) is not None, repr((n1, T[-500:])))
    p.walk_to("ze2")
    p.key("tab", 0.6)
    p.key("end", 0.8)
    T = p.text()
    arow("E2c", "ze2: its own zzqa (DISPLAY QA2) is listed and ze1's zzqb is not", re.search(r"zzqa PA DISPLAY QA2", T) is not None and "zzqb" not in T and "DISPLAY QA1" not in T, T[:900])
    p.key("tab", 0.6)
    arow("E2d", "ze2: the count line is COUNT VOC's number (%d)" % n2, re.search(r"\b%d of %d entries\." % (n2, n2), T) is not None, repr((n2, T[-500:])))
    return n1, n2


def section_e3(p):
    say("\n--- E3: a VOC that cannot be opened")
    p.walk_to(BAD)
    T = p.text()
    ok3 = "VOC cannot be opened from here." in T and ("Its path in the register: " + apath(BAD)) in T       # the path on a line of its own, whole (it was cut at the box edge on a long one)
    arow("E3", "%s: the Entries box says its VOC cannot be opened from here, with its path" % BAD, ok3, T[:600])
    if not ok3:
        dump(p.h)


def section_e4(p, n1):
    say("\n--- E4: / and Esc")
    p.walk_to("ze1")
    p.key("tab", 0.8)
    p.key("/", 1.0)
    p.h.typed("zzq\r", idle=1.2)
    T = p.text()
    arow("E4a", "/ zzq keeps zzqa and zzqb of ze1 and nothing else (the title and the count line say so)",
         re.search(r"zzqa PA", T) and re.search(r"zzqb V", T) and "zzonly1" not in T and re.search(r'\b2 of %d entries hold "zzq"\.' % n1, T) is not None, T[:700])
    p.key("esc", 1.2)
    T = p.text()
    arow("E4b", "Esc takes the filter off: every entry is back, and the menu bar did not open", re.search(r"\b%d of %d entries\." % (n1, n1), T) is not None and "zzonly1" in T, T[-500:])


def section_e5(p):
    say("\n--- E5: F finds an id in every account")
    nacc = len([f for f in os.listdir(os.path.join(sh.SYS, "accounts")) if f != "sdsys"])
    p.key("f", 1.0)
    p.h.typed("zzq\r", idle=2.0)
    T = p.text()
    arow("E5a", "F zzq: four hits - ze1 zzqa, ze1 zzqb, ze2 zzqa and ze5 zzqc - from every VOC that opens (%d of the %d accounts)" % (nacc - 1, nacc),
         all(re.search(r"%s %s \S+" % (a, i), T) for a, i in (("ze1", "zzqa"), ("ze1", "zzqb"), ("ze2", "zzqa"), ("ze5", "zzqc")))
         and re.search(r"\b4 hits in %d VOCs read\." % (nacc - 1), T) is not None, T[:900])
    # the second hit of ze2 is the third row; Enter goes to it
    p.key("down", 0.4)
    p.key("down", 0.4)
    p.key("enter", 1.5)
    T = p.text()
    arow("E5b", "Enter on the hit 'ze2 zzqa' goes to that entry in ze2: the Entries box is titled 'VOC of ze2', the find is off, the status line names the entry",
         p.on() == "ze2" and "zzqa in ze2" in norm(p.st()) and "Ids with" not in T, repr((p.on(), p.st())))


def dcount_items(acct, fname):
    """The number of items of a file's dictionary, counted by a SEPARATE administrator session in the account."""
    out = g.adm(["LOGTO %s" % acct, "COUNT DICT %s" % fname])
    for ln in out:
        m = re.search(r"\b(\d+) record", ln)
        if m:
            return int(m.group(1))
    bail("COUNT DICT %s in %s printed no count:\n%s" % (fname, acct, "\n".join(out[-4:])))


def section_e8(p):
    say("\n--- E8: the dictionary items (K)")
    nd1 = dcount_items("ze1", "zecust")
    nd2 = dcount_items("ze2", "zecust2")
    # THE OWNER'S RULE (3 Nov 26): no pointer may lead the master to edit something in one account from another.  A pointer whose target lies OUTSIDE the account is marked > (the pointer
    # record is the account's; its target is not).  The control of each row is the pointer that stays inside.
    p.key("f", 1.0)
    p.h.typed("$map\r", idle=2.5)
    T = p.text()
    arow("E8s1", "F $map (VOC kind): ze1's pointer $map, which leads to @SDSYS/$map, is marked >", re.search(r"ze1 \$map > F data @SDSYS/\$map", T) is not None, T[:900])
    p.key("esc", 1.2)
    p.key("f", 1.0)
    p.h.typed("zecust\r", idle=2.5)
    T = p.text()
    arow("E8s2", "F zecust: ze1's own pointer zecust (data zecust, dict zecust.dic, both in the account) has no > - the control of E8s1", re.search(r"ze1 zecust F data zecust", T) is not None, T[:900])
    p.key("esc", 1.2)
    p.key("f", 1.0)
    p.h.typed("zeq\r", idle=2.5)
    T = p.text()
    arow("E8o1", "F zeq: ze1's Q-pointer to a file in ANOTHER ACCOUNT (ze2) is marked >", re.search(r"ze1 zeq > Q file zecust2 in the account ze2", T) is not None, T[:900])
    p.key("esc", 1.2)
    p.key("f", 1.0)
    p.h.typed("zeesc\r", idle=2.5)
    T = p.text()
    arow("E8o2", "F zeesc: ze1's file pointer ../ze2/zecust2 - which STARTS with ze1's own directory as text and lives in ze2's - is marked > (the kernel's geometry resolves the ..)",
         re.search(r"ze1 zeesc > F data \.\./ze2/zecust2", T) is not None, T[:900])
    p.key("esc", 1.2)
    p.key("tab", 0.6)                  # the focus is in the Entries box after the find: the walk below is in Accounts
    p.walk_to("ze1")
    p.key("k", 1.2)
    T = p.text()
    arow("E8s3", "K, from the top: the items of the dictionaries outside the account ($map, dict.dict, newvoc, voc: the shipped pointers lead to @SDSYS/...) are marked >", re.search(r"(?:\$map|dict\.dict|newvoc|voc) > \S+", T) is not None, T[:900])
    arow("E8a", "K shows the dictionary items of the account: the box is titled 'Dictionary items of ze1' and the status line says so",
         "Dictionary items of ze1" in T and "the dictionary items" in norm(p.st()), repr((p.st(), T[:500])))
    p.key("/", 1.0)
    p.h.typed("zq\r", idle=1.5)
    T = p.text()
    arow("E8b", "/ zq: the four items of ze1's own zecust - zqfirst D First Name, zqgiven D Given Name, zqalias D Nickname, zqdbl I Double - none marked >, and none of ze2's under that file",
         all(re.search(r"zecust %s %s %s" % (i, t, h), T) for i, t, h in (("zqfirst", "D", "First Name"), ("zqgiven", "D", "Given Name"), ("zqalias", "D", "Nickname"), ("zqdbl", "I", "Double")))
         and re.search(r"zecust zqother", T) is None
         and "could not be opened" not in T, T[:900])      # the shipped file pointers name @SDSYS/voc.dic and the like: their tokens are expanded, so every dictionary opens
    arow("E8o3", "...and the items that ze1's pointer zeesc (../ze2/zecust2) reaches in ze2's dictionary are listed under zeesc, marked >: they are read, and ze2's, not ze1's",
         re.search(r"zeesc > zqother D Other", T) is not None and re.search(r"zeesc > zqfirst D First Name", T) is not None, T[:900])
    p.key("/", 1.0)
    p.h.typed("nickn\r", idle=1.5)
    T = p.text()
    arow("E8c", "/ nickn: matched by the HEADING, not the id (zqalias holds no 'nickn'): only zqalias, and the count line says 1 hold it",
         re.search(r"zecust zqalias D Nickname", T) is not None and "zqfirst" not in T and re.search(r'\b1 of \d+ items hold "nickn"\.', T) is not None, T[:700])
    p.key("esc", 1.2)
    p.key("f", 1.0)
    p.h.typed("first name\r", idle=2.5)
    T = p.text()
    nacc = len([f for f in os.listdir(os.path.join(sh.SYS, "accounts")) if f != "sdsys"])
    arow("E8d", "F 'first name': three hits - ze1's own zecust zqfirst, ze1's zeesc zqfirst (ze2's item, read through the pointer, marked >) and ze2's own zecust2 zqfirst - found by the heading, "
         "from every account whose VOC opens (%d of %d)" % (nacc - 1, nacc),
         re.search(r"ze1 zecust zqfirst D First Name", T) is not None and re.search(r"ze1 zeesc > zqfirst D First Name", T) is not None and re.search(r"ze2 zecust2 zqfirst D First Name", T) is not None
         and re.search(r"\b3 hits in %d accounts read\." % (nacc - 1), T) is not None, T[:900])
    p.key("down", 0.5)
    p.key("down", 0.5)
    p.key("enter", 1.5)
    T = p.text()
    arow("E8e", "Enter on the hit 'ze2 zecust2 zqfirst' goes to it: 'Dictionary items of ze2', the find off, the item shown field by field (First Name, 10L)",
         p.on() == "ze2" and "Dictionary items of ze2" in T and "zqfirst in ze2" in norm(p.st()) and "First Name" in T and "Ids with" not in T and "Dictionary items with" not in T, repr((p.on(), p.st())))
    p.key("k", 1.2)
    T = p.text()
    arow("E8f", "K again: back to the VOC entries of ze2 (the title says 'VOC of ze2'), the filter off", "VOC of ze2" in T and "Dictionary items" not in T, T[:300])
    arow("E8g", "the dictionary of ze1's zecust (%d items) and ze2's zecust2 (%d), the one ze1's pointers reach, have the same number of items after everything the page did (COUNT DICT)" % (nd1, nd2),
         dcount_items("ze1", "zecust") == nd1 and dcount_items("ze2", "zecust2") == nd2 and nd1 >= 4 and nd2 >= 2)


def section_e6(n1, n2):
    say("\n--- E6: the page reads and writes nothing")
    arow("E6a", "the VOC of ze1 and of ze2 have the same number of entries after everything the page did", count_voc("ze1") == n1 and count_voc("ze2") == n2, repr((n1, n2)))


def section_e7(p, a0):
    say("\n--- E7: help, audit, a small window, Ctrl-Q")
    new = audit_new(a0)
    lines = [ln for ln in new.splitlines() if ln.strip()]
    arow("E7a", "the audit trail holds the start line of the page and nothing else from it (no run, no write, no record change)",
         len([ln for ln in lines if "tool start app=tool.entries" in ln]) == 1 and not [ln for ln in lines if re.search(r"tool run|run\.in|modify|create|delete", ln)], repr(lines[-6:]))
    p.key("f1", 1.2)
    arow("E7b", "F1 reaches the help box (a sandbox has no shared account: help is not installed here)", "Help is not installed here" in p.text(), p.text()[-300:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.entries\r", idle=3.0)
    T = norm(h.text())
    arow("E7c", "a window under 140 by 43 gets no page", "What this means" not in T, T[-300:])
    h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-entries.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    last = MUTANTS[mutant][3] if mutant else "E7"
    try:
        sh.setup("sandbox-tool-entries.py")
        setup_page()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-entries: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_e0()
        a0 = audit_off()
        p = section_e1()
        if mutant is None or last in ("E5a", "E7", "E8"):
            n1, n2 = section_e2(p)
            section_e3(p)
            section_e4(p, n1)
        if mutant is None or last in ("E5a", "E8"):
            section_e5(p)
        if mutant is None or last == "E8":
            section_e8(p)
        if mutant is None:
            section_e6(n1, n2)
            section_e7(p, a0)
        else:
            p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-entries: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"E\d", i).group(0) for i in FAILED_IDS})
        ok = want == got
        say("sandbox-tool-entries: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
