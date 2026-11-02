#!/usr/bin/env python3
#
# sandbox-tool-entries.py - the master files page (S.96 M1a-M2): TOOL.ENTRIES, the VOC entries, dictionary items and programs of every account by pointer, read only until E10 (E and N edit
# the record in its own account).  A private SD, no install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-entries.py <dir> [--build] [--only=read|edit|delete] [--mutant=NAME]
#
# --only (the owner's rule of 3 Nov 26: anything over five minutes has a section selector): `read` is E0-E9 (one chain on one page), `edit` is E10 (a page of its own; it changes the
# fixture accounts' files, so it runs after `read` when both run), `delete` is E11 (a page of its own, its own records, after `edit`).  The build and the fixtures always run.  A mutant runs only its own group.
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
#   E8   K: the dictionary items, / by id or heading, F across accounts, the > mark of the pointer rule     E9  K again: the programs, built or not
#   E10  (M2, S.96) E and N hand the record to the IDE IN ITS OWN ACCOUNT - the VOC entry as text, a pointer record included, a new VOC entry, an account with every gate off, the
#        dictionary item as the form, a new item - each judged by the account's own file read by a SEPARATE session, SDSYS's VOC holding the page's temporary pointer only while the IDE
#        is open; THE POINTER RULE: an item of a dictionary that lies outside the account (a pointer written ../other/.., a LINK to another account's dictionary, a shipped system
#        dictionary) is refused for E and N with its reason, before a pointer is made, and the audit trail has a 'master edit' line for every edit that reached the IDE and none for a
#        refusal; the programs are refused, N while a find is on is refused; a dictionary directory of the account's own whose SUBFILES are links to another account's is refused by the
#        second test (E10z); a pointer left by a killed session is swept at the next start, and only this user number's (E10y).  The files are read ONCE at the start and ONCE at the
#        end, one separate session per account (snap).  Mutants: no-outside-test, no-subfile-test, pointer-left.
#   E11  (M3, S.96; --only=delete) D deletes the record under the cursor IN ITS OWN ACCOUNT after the confirm box with its id TYPED: a VOC entry, a dictionary item, an entry of an account
#        with every gate off; Cancel and a wrong id delete nothing; a record another LIVE session holds with READU is refused and kept; the POINTER RULE refuses D on an item that lies
#        outside the account (../other, a link, a directory of links) with no box; the programs are refused; one 'master delete' line per delete that worked and none otherwise;
#        SDSYS's VOC holds no zm pointer after.  The files read once at the start and once at the end (snap).  Mutants: no-typed-id, no-lock.
# NOT HELD: SDSYS in the group (a sandbox has no sdsys user: the column can only say no or n/a here), the help text itself (sandbox-docs.py).
import importlib.util
import os
import re
import subprocess
import sys
import threading
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
    "never-built": ("locate downcase(pid) in onames<1> setting op3 then built = 'yes'", "locate downcase(pid) in onames<1> setting op3 then built = '-'", ["E9"], "E9"),
    "text-prefix": ("is.out = (if kernel(K$PATH.IN, apath<ca> : @fm : tp) then 0 else 1)", "is.out = (if tp[1, len(apath<ca>)] = apath<ca> then 0 else 1)", ["E8"], "E8"),
    # M2: the rule's test before any pointer is written, the test of the subfiles of what the pointer opens, the pointer taken away again
    "no-outside-test": ("   if not(kernel(K$PATH.IN, ap.f : @fm : tp)) then\n", "   if 0 then\n", ["E10"], "E10"),
    "no-subfile-test": ("   if in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%0')\n   if in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%1')\n", "", ["E10"], "E10"),
    "pointer-left": ("   execute sent\n   gosub drop.pointer\n", "   execute sent\n", ["E10"], "E10"),
    # M3: the id is not asked for (Run alone deletes), another session's lock is not asked about
    "no-typed-id": ("call $tk_confirm(dsent, dlines, eid, res, cmsg, sysmsg(11953))", "call $tk_confirm(dsent, dlines, '', res, cmsg, sysmsg(11953))", ["E11"], "E11"),
    "no-lock": ("   readu dold from tf, eid locked\n      dlu = status()\n      close tf\n      gosub drop.pointer\n"
                "      msg = eid : ' in ' : dwhere : ' is locked by user ' : dlu : ' (an editor holds it): it is not deleted'\n      return\n   end else\n",
                "   read dold from tf, eid else\n", ["E11"], "E11"),
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
    voc_write("zzeptr", [("ze1", "zeq", ["Q", "ze2", "zecust2"]), ("ze1", "zeesc", ["F", "../ze2/zecust2", "../ze2/zecust2.dic"]),
                         ("ze1", "ze2.bp", ["F", "../ze2/bp"])])      # a PROGRAM file (the name ends .bp) that is another account's: its programs are marked > (M1c)
    voc_write("zzefix", [("ze1", "zzqa", ["PA", "DISPLAY QA1"]), ("ze1", "zzqb", ["V", "CA", "$zzkf"]), ("ze1", "zzonly1", ["X", "text one"]),
                         ("ze2", "zzqa", ["PA", "DISPLAY QA2"]), ("ze2", "zzonly2", ["X", "text two"]), ("ze5", "zzqc", ["PA", "DISPLAY QC"])])
    # M1c: programs.  zpbuilt is compiled in ze1 (its object is in ze1's bp.out), zpsrc is source only; ze2 has zpother, compiled.  The compile is done by an administrator session in the
    # account (LOGTO, then BASIC), so bp.out is what BASIC made, not something this suite wrote.
    for acct, progs in (("ze1", ("zpbuilt", "zpsrc")), ("ze2", ("zpother",))):
        for pid in progs:
            g.put(os.path.join(apath(acct), "bp", pid), "program %s\n   crt '%s ran'\nend\n" % (pid, pid.upper()))
    for acct, pid in (("ze1", "zpbuilt"), ("ze2", "zpother")):
        out = g.adm(["LOGTO %s" % acct, "BASIC bp %s" % pid])
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("the program %s was not compiled in %s:\n%s" % (pid, acct, "\n".join(out[-6:])))
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
        m = re.search(r"(?:VOC|Dictionary items|Programs) of ([^\s,]+)", self.text())       # a filter adds ', matching "..."' to the title
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
    p.key("k", 1.2)                    # the dictionary items, then the programs, then round to the VOC entries
    T = p.text()
    arow("E8f", "K twice more: past the programs, round to the VOC entries of ze2 (the title says 'VOC of ze2'), the filter off", "VOC of ze2" in T and "Dictionary items" not in T and "Programs" not in T, T[:300])
    arow("E8g", "the dictionary of ze1's zecust (%d items) and ze2's zecust2 (%d), the one ze1's pointers reach, have the same number of items after everything the page did (COUNT DICT)" % (nd1, nd2),
         dcount_items("ze1", "zecust") == nd1 and dcount_items("ze2", "zecust2") == nd2 and nd1 >= 4 and nd2 >= 2)


def tree_state(acct):
    """The files of an account's bp and bp.out with their modification times: the evidence that nothing was changed."""
    st = {}
    for sub in ("bp", "bp.out"):
        d = os.path.join(apath(acct), sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                st[sub + "/" + f] = os.stat(os.path.join(d, f)).st_mtime_ns
    return st


def section_e9(p):
    say("\n--- E9: the programs (K, K)")
    before1, before2 = tree_state("ze1"), tree_state("ze2")
    obj1 = os.path.join(apath("ze1"), "bp.out")
    p.key("tab", 0.6)                  # the focus may be in the Entries box after E8: the walk below is in Accounts
    p.walk_to("ze1")
    p.key("k", 1.2)
    p.key("k", 1.2)
    T = p.text()
    arow("E9a", "K twice from the VOC: the box is titled 'Programs of ze1' and the status line says the programs", "Programs of ze1" in T and "the programs" in norm(p.st()), repr((p.st(), T[:400])))
    p.key("/", 1.0)
    p.h.typed("zp\r", idle=1.5)
    T = p.text()
    arow("E9b", "/ zp: ze1's own programs - zpbuilt BUILT (yes), zpsrc source only (-), checked against the disk (the object is in ze1's bp.out for the first and not for the second) - and, "
         "marked > and built (ze1's VOC names no .out file for ze2.bp: the page finds the one beside the program file), zpother of ze2 read through ze1's pointer ze2.bp",
         os.path.isfile(os.path.join(obj1, "zpbuilt")) and not os.path.exists(os.path.join(obj1, "zpsrc"))
         and re.search(r"\bbp zpbuilt yes\b", T) is not None and re.search(r"\bbp zpsrc - ", T) is not None and re.search(r"ze2\.bp > zpother yes\b", T) is not None, T[:900])
    arow("E9c", "...the count line says 3 hold zp, and the means box shows the first lines of the program under the cursor (zpbuilt)",
         re.search(r'\b3 of \d+ programs hold "zp"\.', T) is not None and re.search(r"1 program zpbuilt", T) is not None, T[-900:])
    p.key("esc", 1.2)
    p.key("f", 1.0)
    p.h.typed("zpother\r", idle=2.5)
    T = p.text()
    nacc = len([f for f in os.listdir(os.path.join(sh.SYS, "accounts")) if f != "sdsys"])
    arow("E9d", "F zpother: two hits - ze1's pointer ze2.bp (marked >) and ze2's own bp (no >) - from the %d accounts whose VOC opens" % (nacc - 1),
         re.search(r"ze1 ze2\.bp > zpother yes\b", T) is not None and re.search(r"ze2 bp zpother yes\b", T) is not None and re.search(r"\b2 hits in %d accounts read\." % (nacc - 1), T) is not None, T[:900])
    p.key("esc", 1.2)
    p.key("k", 1.2)
    T = p.text()
    arow("E9e", "K once more: round to the VOC entries of ze1 ('VOC of ze1')", "VOC of ze1" in T and "Programs" not in T, T[:300])
    arow("E9f", "nothing was changed: the files of ze1's and ze2's bp and bp.out, with their modification times, are as they were", tree_state("ze1") == before1 and tree_state("ze2") == before2,
         repr((sorted(set(tree_state("ze1").items()) ^ set(before1.items()))[:3],)))


# The records E10 judges, by account: (kind, file, id).  ONE separate session per account reads them all (the owner's rule of 3 Nov 26: a pass must not cost what it need not; a
# session costs about 8 s, and one per row made E10 several minutes long).
TRACK = {
    "ze1": [("voc", "voc", "zzonly1"), ("voc", "voc", "zeq"), ("voc", "voc", "zznew1"), ("voc", "voc", "zzonly2"), ("dict", "zecust", "zqalias"), ("dict", "zecust", "zqnew1")],
    "ze2": [("voc", "voc", "zzonly1"), ("voc", "voc", "zeq"), ("voc", "voc", "zznew1"), ("voc", "voc", "zzonly2"), ("dict", "zecust2", "zqother"), ("dict", "zecust2", "zqfirst"),
            ("dict", "zecust2", "zqnew1"), ("dict", "zecust2", "zqpoison")],
    "sdsys": [("voc", "voc", "zzonly1"), ("voc", "voc", "zznew1"), ("voc", "voc", "zzonly2")],
}

ER_SRC = "\n".join([
    "program zzerd",
    "   n = dcount(@sentence, ' ')",
    "   for i = 4 to n step 3",
    "      kd = field(@sentence, ' ', i)",
    "      fl = field(@sentence, ' ', i + 1)",
    "      rid = field(@sentence, ' ', i + 2)",
    "      ok = 1",
    "      if kd = 'dict' then",
    "         open 'dict', fl to f else ok = 0",
    "      end else",
    "         open 'voc' to f else ok = 0",
    "      end",
    "      if ok then",
    "         read r from f, rid then",
    "            crt 'ER|' : kd : '|' : fl : '|' : rid : '|' : convert(@fm, '|', r)",
    "         end else",
    "            crt 'ER|' : kd : '|' : fl : '|' : rid : '|NONE'",
    "         end",
    "         close f",
    "      end else",
    "         crt 'ER|' : kd : '|' : fl : '|' : rid : '|NOFILE'",
    "      end",
    "   next i",
    "end", ""])


def snap(track=None):
    """Every record in TRACK (or track) as the account's own file holds it (fields joined by |, NONE when it is not there), read by ONE separate session per account, and SDSYS's zm pointers."""
    out = {}
    for acct, keys in (track or TRACK).items():
        res = g.adm((["LOGTO %s" % acct] if acct != "sdsys" else []) + ["RUN bp zzerd " + " ".join("%s %s %s" % k for k in keys)])
        for ln in res:
            if ln.startswith("ER|"):
                parts = ln.rstrip().split("|", 4)
                if len(parts) == 5:
                    out[(acct, parts[1], parts[2], parts[3])] = parts[4]
        missing = [k for k in keys if (acct,) + k not in out]
        if missing:
            bail("the reader in %s did not answer for %s:\n%s" % (acct, missing, "\n".join(res[-6:])))
    out["zm"] = sys_zm()
    return out


def sys_zm():
    """The ids in SDSYS's VOC that start zm (the page's temporary pointers), read by a SEPARATE administrator session."""
    g.put(os.path.join(sh.SYS, "bp", "zzzm"), "\n".join(["$internal", "   openpath @sdsys:@ds:'voc' to v else crt 'ZM no voc' ; stop", "   select v to 9", "   n = 0", "   loop",
                                                          "      readnext id from 9 else exit", "      if id[1, 2] = 'zm' then", "         crt 'ZMID ' : id", "         n += 1", "      end", "   repeat",
                                                          "   crt 'ZMEND ' : n", "end", ""]))
    out = g.adm(["BASIC bp zzzm", "RUN bp zzzm"], internal=True)
    if not [ln for ln in out if ln.startswith("ZMEND ")]:
        bail("the reader of SDSYS's zm pointers did not answer:\n" + "\n".join(out[-6:]))
    return sorted(ln.split(" ", 1)[1].strip() for ln in out if ln.startswith("ZMID "))


def wait_for(h, pred, secs=12.0):
    """Pump the terminal until pred(text) is true; True when it came."""
    end = time.time() + secs
    while time.time() < end:
        if pred(h.text()):
            return True
        h.s._pump(0.3)
    return pred(h.text())


def ide_up(x):
    """The IDE is on the screen: its menu bar on the first row, or the dictionary item form it opens.  x is the screen's text or the session (wait_for gives the text)."""
    t = x if isinstance(x, str) else x.text()
    first = t.split("\n", 1)[0]
    return ("File" in first and "Search" in first) or ("Type:" in t and "Accept" in t and "Cancel" in t)


def to_page(p):
    """Ctrl-Q leaves the IDE, Enter takes the page back."""
    p.h.typed("\x11", idle=1.5)
    if not wait_for(p.h, lambda t: "Press Enter" in t, 6):
        p.h.typed("n", idle=1.0)
    wait_for(p.h, lambda t: "Press Enter" in t, 6)
    p.h.key("enter", idle=2.0)
    wait_for(p.h, lambda t: "What this means" in t and "Press Enter" not in t, 10)


def ide_open(p, key, ask=None):
    """Press the key (and answer the id box if there is one); True when the IDE came up."""
    p.h.typed(key, idle=1.2)
    if ask is not None:
        p.h.typed(ask + "\r", idle=2.5)
    return wait_for(p.h, ide_up, 12)


def section_e10():
    say("\n--- E10: E and N edit the record in its own account; the pointer rule refuses what lies outside it (S.96 M2)")
    _section_e10_body(fixture_e10())


def fixture_e10():
    """The readers, E10's records as the fixture made them, and the two dictionaries that only the kernel's geometry sees leading out of ze1 (a link, and a directory of links).  E10 and E11
    both start here.  Returns the directory of links."""
    for acct in ("ze1", "ze2"):
        g.put(os.path.join(apath(acct), "bp", "zzerd"), ER_SRC)
        out = g.adm(["LOGTO %s" % acct, "BASIC bp zzerd"])
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("the reader zzerd was not compiled in %s:\n%s" % (acct, "\n".join(out[-6:])))
    g.put(os.path.join(sh.SYS, "bp", "zzerd"), ER_SRC)
    out = g.adm(["BASIC bp zzerd"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the reader zzerd was not compiled in SDSYS:\n" + "\n".join(out[-6:]))
    reset_e10()
    # a LINK: ze1's zelnk.dic IS ze2's zecust2.dic.  Its text starts with ze1's own directory; only the kernel's geometry (realpath) sees where it leads.
    os.symlink(os.path.join(apath("ze2"), "zecust2.dic"), os.path.join(apath("ze1"), "zelnk.dic"))
    # LINKS INSIDE a dictionary (the review of 3 Nov 26, finding 2): ze1's zesub.dic is a real directory of ze1's, so the directory passes the first test; its subfiles are links to
    # ze2's.  Only the test of what the pointer opens, subfiles included, sees it.
    sub = os.path.join(apath("ze1"), "zesub.dic")
    os.makedirs(sub)
    src2 = os.path.join(apath("ze2"), "zecust2.dic")
    for f in os.listdir(src2):
        os.symlink(os.path.join(src2, f), os.path.join(sub, f))
    return sub


def reset_e10():
    """What E10 adds and changes is put back as the fixture made it (at its start, for a REUSED sandbox, and at its end, so that a later `read` run on the same sandbox sees the fixture):
    the records E10 edits, the records it makes, its two extra file pointers and their links."""
    import shutil
    lnk = os.path.join(apath("ze1"), "zelnk.dic")
    if os.path.islink(lnk):
        os.remove(lnk)
    sub = os.path.join(apath("ze1"), "zesub.dic")
    if os.path.isdir(sub) and not os.path.islink(sub):
        shutil.rmtree(sub)            # only links inside: rmtree removes the links, never what they point at
    reset = ["$internal"]
    for i, (acct, f) in enumerate((("ze1", "voc"), ("ze2", "voc"), ("ze1", "zecust.dic"), ("ze2", "zecust2.dic"))):
        reset.append("   openpath '%s/%s' to f%d else crt 'RST no %s %s' ; stop" % (apath(acct), f, i, acct, f))
    reset += ["   write 'X' : @fm : 'text one' on f0, 'zzonly1'", "   write 'Q' : @fm : 'ze2' : @fm : 'zecust2' on f0, 'zeq'", "   delete f0, 'zznew1'", "   delete f0, 'zzonly2'",
              "   delete f0, 'zelnk'", "   delete f0, 'zesub'",
              "   write 'X' : @fm : 'text two' on f1, 'zzonly2'", "   delete f1, 'zzonly1'", "   delete f1, 'zeq'", "   delete f1, 'zznew1'",
              "   write 'D' : @fm : '3' : @fm : '' : @fm : 'Nickname' : @fm : '10L' : @fm : 'S' on f2, 'zqalias'", "   delete f2, 'zqnew1'",
              "   delete f3, 'zqnew1'", "   delete f3, 'zqpoison'",
              "   openpath @sdsys:@ds:'voc' to s else crt 'RST no sdsys voc' ; stop", "   delete s, 'zzonly1'", "   delete s, 'zznew1'", "   delete s, 'zzonly2'",
              "   crt 'RST done'", "end", ""]
    g.put(os.path.join(sh.SYS, "bp", "zzerst"), "\n".join(reset))
    out = g.adm(["BASIC bp zzerst", "RUN bp zzerst"], internal=True)
    if not has(out, r"^RST done$"):
        bail("the E10 fixture records were not put back:\n" + "\n".join(out[-6:]))


def _section_e10_body(sub):
    voc_write("zzelnk", [("ze1", "zelnk", ["F", "zelnk", "zelnk.dic"]), ("ze1", "zesub", ["F", "zesub", "zesub.dic"])])
    B = snap()
    a0 = audit_off()
    p = Page()
    p.walk_to("ze1")
    p.key("tab", 0.6)
    p.key("/", 1.0)
    p.h.typed("zzonly1\r", idle=1.5)
    T = p.text()
    arow("E10a", "control: the entries of ze1 are filtered to zzonly1, the cursor is in Entries, and the files hold what the fixture wrote (ze1's zzonly1 is X / text one, ze2 and SDSYS have none)",
         'matching "zzonly1"' in T and B[("ze1", "voc", "voc", "zzonly1")] == "X|text one" and B[("ze2", "voc", "voc", "zzonly1")] == "NONE" and B[("sdsys", "voc", "voc", "zzonly1")] == "NONE"
         and B[("ze1", "voc", "voc", "zeq")] == "Q|ze2|zecust2", repr((T[:300], B)))

    say("  E on a VOC entry")
    up = ide_open(p, "e")
    T = p.text()
    zm_now = sys_zm()
    arow("E10b", "E on zzonly1 gives the screen to the IDE, which has the record open (its text is on the screen; the page is not), and SDSYS's VOC holds ONE temporary pointer for ze1's VOC while it is open",
         up and "text one" in T and "What this means" not in T and len(zm_now) == len(B["zm"]) + 1 and any(re.match(r"zm\d+\.ze1\.voc$", z) for z in zm_now), repr((up, zm_now, T[:300])))
    p.h.key("down", idle=0.3)
    p.h.key("end", idle=0.3)
    p.h.typed(" edited", idle=0.5)
    p.h.typed("\x13", idle=1.8)                        # Ctrl-S: the IDE's only save key (F2 is the debugger's)
    to_page(p)
    T = p.text()
    arow("E10d", "Ctrl-Q and Enter bring the page back on the same entry and the status line says it came back from the editor",
         "What this means" in T and "zzonly1" in T and "back from the editor" in norm(p.st()), repr(p.st()))

    say("  the POINTER RECORD itself is editable although its target is in another account")
    p.key("/", 1.0)
    p.h.typed("zeq\r", idle=1.5)
    up_q = ide_open(p, "e")
    p.h.key("down", idle=0.3)
    p.h.key("down", idle=0.3)
    p.h.key("end", idle=0.3)
    p.h.typed("x", idle=0.5)
    p.h.typed("\x13", idle=1.8)
    to_page(p)

    say("  N on the VOC")
    p.h.typed("n", idle=1.2)
    T = p.text()
    arow("E10g", "N asks the id first: 'Id of the new VOC entry in ze1'", "Id of the new VOC entry in ze1" in T, T[:400])
    p.h.typed("zznew1\r", idle=2.5)
    up_n = wait_for(p.h, ide_up, 12)
    p.h.typed("X\rmade by n", idle=0.8)
    p.h.typed("\x13", idle=1.8)
    to_page(p)

    say("  an account with every edit gate off")
    p.key("tab", 0.6)
    arrived2 = p.walk_to("ze2")
    p.key("tab", 0.6)
    p.key("/", 1.0)
    p.h.typed("zzonly2\r", idle=1.5)
    up2 = ide_open(p, "e")
    p.h.key("down", idle=0.3)
    p.h.key("end", idle=0.3)
    p.h.typed(" edited", idle=0.5)
    p.h.typed("\x13", idle=1.8)
    to_page(p)

    say("  E and N on the dictionary items")
    p.key("tab", 0.6)
    p.walk_to("ze1")
    p.key("tab", 0.6)
    p.key("k", 1.2)
    p.key("/", 1.0)
    p.h.typed("zqalias\r", idle=1.5)
    up = ide_open(p, "e")
    form = wait_for(p.h, lambda t: "Type:" in t and "Accept" in t and "Cancel" in t, 10)
    arow("E10j", "E on the item zqalias of ze1's zecust opens the dictionary item FORM (the default face of a dictionary item); the page is not on the screen", up and form and "Column Heading:" in p.h.text()
         and "What this means" not in p.h.text(), p.h.text()[:300])
    for _ in range(3):
        p.h.key("tab", idle=0.3)
    p.h.typed("\x15", idle=0.3)
    p.h.typed("Alias name", idle=0.4)
    p.h.key("enter", idle=2.5)
    to_page(p)
    st_k = norm(p.st())
    p.h.typed("n", idle=1.2)
    T = p.text()
    arow("E10l", "N on an item asks for the id and names the file and the account: 'Id of the new item in the dictionary of zecust (ze1)'", "Id of the new item in the dictionary of zecust (ze1)" in T, T[:400])
    p.h.typed("zqnew1\r", idle=2.5)
    up_dn = wait_for(p.h, ide_up, 12)
    form_dn = wait_for(p.h, lambda t: "Type:" in t and "Accept" in t, 10)
    p.h.typed("D", idle=0.4)
    p.h.key("tab", idle=1.8)
    wait_for(p.h, lambda t: "Field #:" in t, 8)
    p.h.typed("3", idle=0.4)
    p.h.key("enter", idle=2.5)
    to_page(p)

    say("  THE POINTER RULE: what lies outside the account is refused, before a pointer is made and with the reason")
    p.key("/", 1.0)
    p.h.typed("zqother\r", idle=1.5)
    T = p.text()
    arow("E10n", "control: ze1's dictionary view lists ze2's item zqother under TWO of ze1's pointers, zeesc (written ../ze2/zecust2.dic) and zelnk (a LINK to ze2's dictionary), both marked >",
         re.search(r"zeesc > zqother D Other", T) is not None and re.search(r"zelnk > zqother D Other", T) is not None, T[:900])
    p.h.typed("e", idle=1.5)
    T = p.text()
    arow("E10o", "E on zeesc zqother (the pointer is written ../ze2/zecust2.dic, which STARTS with ze1's directory as text) is refused with the reason, the page stays, no IDE", not ide_up(p.h) and "What this means" in T
         and "zeesc lies outside ze1" in norm(p.st()) and "edited in the account it lives in" in norm(p.st()), repr(p.st()))
    p.key("down", 0.6)
    p.h.typed("e", idle=1.5)
    T = p.text()
    arow("E10p", "E on zelnk zqother (the dictionary is a LINK to ze2's, its text starts with ze1's directory and only realpath sees where it leads) is refused the same way", not ide_up(p.h) and "What this means" in T
         and "zelnk lies outside ze1" in norm(p.st()), repr(p.st()))
    p.key("down", 0.6)
    p.h.typed("e", idle=2.0)
    T = p.text()
    arow("E10z", "E on zesub zqother (ze1's OWN directory zesub.dic, whose subfiles are LINKS to ze2's: the directory passes the first test) is refused by the test of what the pointer opens, "
         "subfiles included - and the pointer it wrote for that test is taken away again", not ide_up(p.h) and "What this means" in T and "opens a file outside the account" in norm(p.st()), repr(p.st()))
    p.key("up", 0.6)
    p.h.typed("n", idle=1.2)
    p.h.typed("zqpoison\r", idle=2.0)
    T = p.text()
    arow("E10q", "N on the zelnk row asks the id and is refused the same way (what it would have made in ze2's dictionary is judged at the end)", not ide_up(p.h) and "What this means" in T
         and "lies outside ze1" in norm(p.st()), repr(p.st()))
    p.key("esc", 1.2)
    p.key("home", 0.6)
    lines = p.h.lines()
    hi = next((i for i, ln in enumerate(lines) if "Heading" in ln[50:] and "File" in ln[50:]), None)
    top = [w for w in (lines[hi + 1][50:].split() if hi is not None and hi + 1 < len(lines) else []) if w != "|"]     # the box's own border is not a word of the row
    if len(top) >= 2 and top[1] == ">":                # the precondition: the top row is an item of a system dictionary, marked >; E is pressed only then
        p.h.typed("e", idle=1.5)
        T = p.text()
        arow("E10s", "E on the top row of the dictionary view - an item of a SHIPPED system dictionary (the pointer leads to @SDSYS/...) - is refused: it is edited in the SDSYS account", not ide_up(p.h)
             and "What this means" in T and "lies outside ze1" in norm(p.st()), repr((p.st(), top)))
    else:
        arow("E10s", "E on the top row of the dictionary view - an item of a SHIPPED system dictionary - is refused (PRECONDITION NOT MET: the top row is not marked >, so E was not pressed)", False, repr(top))

    say("  the programs, a find, an account that is suspended")
    p.key("k", 1.2)
    p.h.typed("e", idle=1.0)
    arow("E10t", "E on the programs says they are not edited from this page yet (M4)", "not edited from this page yet" in norm(p.st()) and not ide_up(p.h), repr(p.st()))
    p.key("k", 1.2)                                    # round to the VOC
    p.key("f", 1.0)
    p.h.typed("zz\r", idle=2.5)
    p.h.typed("n", idle=1.2)
    arow("E10u", "N while a find is on is refused: 'Esc takes the find off first'", "Esc takes the find off first" in norm(p.st()) and not ide_up(p.h), repr(p.st()))
    p.key("esc", 1.2)
    p.key("tab", 0.6)
    arrived = p.walk_to("ze5")
    p.key("tab", 0.6)
    p.key("/", 1.0)
    p.h.typed("zzqc\r", idle=1.5)
    p.h.typed("e", idle=3.0)
    followed = wait_for(p.h, ide_up, 6)
    said = norm(p.st())
    if followed:
        to_page(p)
    say("  [measured] E on an entry of the SUSPENDED account ze5: %s (status: %s)" % ("the IDE opened" if followed else "refused", said))
    arow("E10v", "whatever SD does for a suspended account, the page ends back on its own screen (its pointer is judged at the end)", arrived and "What this means" in p.text(), repr((arrived, said)))
    p.quit()

    say("  the files, read once at the end by a separate session in each account (the oracle)")
    S = snap()

    def k(a, kd, fl, i):
        return S[(a, kd, fl, i)]

    def kb(a, kd, fl, i):
        return B[(a, kd, fl, i)]
    arow("E10c", "E's save wrote the record into ze1's own VOC: X / text one edited", k("ze1", "voc", "voc", "zzonly1") == "X|text one edited", repr(k("ze1", "voc", "voc", "zzonly1")))
    arow("E10e", "SDSYS's own VOC and ze2's have no zzonly1: the record went to ze1 and nowhere else", k("sdsys", "voc", "voc", "zzonly1") == "NONE" and k("ze2", "voc", "voc", "zzonly1") == "NONE")
    arow("E10f", "zeq (a Q-pointer to ze2's zecust2, marked >) was edited like any record of ze1: Q / ze2 / zecust2 became Q / ze2 / zecust2x; ze2 is as it was (its dictionary items, no zeq in its VOC)",
         up_q and kb("ze1", "voc", "voc", "zeq") == "Q|ze2|zecust2" and k("ze1", "voc", "voc", "zeq") == "Q|ze2|zecust2x" and k("ze2", "dict", "zecust2", "zqother") == kb("ze2", "dict", "zecust2", "zqother")
         and k("ze2", "dict", "zecust2", "zqfirst") == kb("ze2", "dict", "zecust2", "zqfirst") and k("ze2", "voc", "voc", "zeq") == "NONE", repr((up_q, k("ze1", "voc", "voc", "zeq"))))
    arow("E10h", "N made zznew1 in ze1's VOC (X / made by n), and SDSYS's VOC and ze2's do not have it", up_n and k("ze1", "voc", "voc", "zznew1") == "X|made by n"
         and k("sdsys", "voc", "voc", "zznew1") == "NONE" and k("ze2", "voc", "voc", "zznew1") == "NONE", repr((up_n, k("ze1", "voc", "voc", "zznew1"))))
    arow("E10i", "ze2 holds voc-edit, dict-edit and bp-edit OFF: the administrator edited its zzonly2 all the same (X / text two edited), and ze1's VOC and SDSYS's have no zzonly2",
         arrived2 and up2 and k("ze2", "voc", "voc", "zzonly2") == "X|text two edited" and k("ze1", "voc", "voc", "zzonly2") == "NONE" and k("sdsys", "voc", "voc", "zzonly2") == "NONE",
         repr((arrived2, up2, k("ze2", "voc", "voc", "zzonly2"))))
    arow("E10k", "the form's Accept wrote the item into ze1's own zecust dictionary: D / 3 / / Alias name / 10L / S, and the page came back", k("ze1", "dict", "zecust", "zqalias") == "D|3||Alias name|10L|S"
         and "back from the editor" in st_k, repr((k("ze1", "dict", "zecust", "zqalias"), st_k)))
    arow("E10m", "N made the item zqnew1 in ze1's zecust (D / 3 / / / 10L / S) through the form, and ze2's zecust2 does not have it", up_dn and form_dn and k("ze1", "dict", "zecust", "zqnew1") == "D|3|||10L|S"
         and k("ze2", "dict", "zecust2", "zqnew1") == "NONE", repr((up_dn, form_dn, k("ze1", "dict", "zecust", "zqnew1"))))
    arow("E10r", "after the refusals ze2's dictionary is as it was (zqother, zqfirst) and has no zqpoison", k("ze2", "dict", "zecust2", "zqother") == kb("ze2", "dict", "zecust2", "zqother")
         and k("ze2", "dict", "zecust2", "zqfirst") == kb("ze2", "dict", "zecust2", "zqfirst") and k("ze2", "dict", "zecust2", "zqpoison") == "NONE")
    arow("E10x", "SDSYS's VOC holds none of the page's temporary pointers at the end: every one was taken away (after each edit, after each refusal that had written one, and for the suspended account)",
         S["zm"] == B["zm"], repr((B["zm"], S["zm"])))

    say("  the audit trail")
    lines = [ln for ln in audit_new(a0).splitlines() if "master edit" in ln]
    want = [r"master edit account=ze1 kind=voc file=voc id=zzonly1 new=0", r"master edit account=ze1 kind=voc file=voc id=zeq new=0", r"master edit account=ze1 kind=voc file=voc id=zznew1 new=1",
            r"master edit account=ze2 kind=voc file=voc id=zzonly2 new=0", r"master edit account=ze1 kind=dict file=zecust id=zqalias new=0", r"master edit account=ze1 kind=dict file=zecust id=zqnew1 new=1"]
    arow("E10w", "each edit that reached the IDE is one 'master edit' line in the audit trail, in lower case, and a refused one (zeesc, zelnk, zesub, zqpoison, the system dictionary) leaves none",
         all(len([ln for ln in lines if re.search(w, ln)]) == 1 for w in want) and not [ln for ln in lines if re.search(r"zeesc|zelnk|zesub|zqpoison|zqother", ln)]
         and len(lines) == len(want) + (1 if followed else 0), repr(lines[-8:]))

    say("  a pointer left by a session killed inside the IDE is swept at the page's next start (the review of 3 Nov 26, finding 4)")
    g.put(os.path.join(sh.SYS, "bp", "zzstale"), "\n".join(["$internal", "   openpath @sdsys:@ds:'voc' to v else crt 'ST no voc' ; stop", "   for n = 1 to 300",
                                                             "      write 'F' : @fm : '/nonexistent' on v, 'zm' : n : '.zzstale.voc'", "   next n", "   crt 'ST done'", "end", ""]))
    out = g.adm(["BASIC bp zzstale", "RUN bp zzstale"], internal=True)
    if not has(out, r"^ST done$"):
        bail("the stale pointers were not planted:\n" + "\n".join(out[-5:]))
    p2 = Page()
    started = "What this means" in p2.text()
    p2.quit()
    left = [z for z in sys_zm() if z.endswith(".zzstale.voc")]
    arow("E10y", "300 dead pointers planted under zm1. to zm300.: the page's start took away exactly ONE, its own user number's, and left the other 299 (they are other sessions' names)",
         started and len(left) == 299, repr((started, len(left))))
    g.put(os.path.join(sh.SYS, "bp", "zzstale"), "\n".join(["$internal", "   openpath @sdsys:@ds:'voc' to v else crt 'ST no voc' ; stop", "   for n = 1 to 300",
                                                             "      delete v, 'zm' : n : '.zzstale.voc'", "   next n", "   crt 'ST done'", "end", ""]))
    g.adm(["BASIC bp zzstale", "RUN bp zzstale"], internal=True)
    reset_e10()                        # the sandbox as the fixture made it, for a later run on it without --build


# E11's records, by account; planted at its start (written over, so a reused sandbox starts the same) and taken away at its end.
TRACK11 = {
    "ze1": [("voc", "voc", "zzdel1"), ("voc", "voc", "zzdel2"), ("voc", "voc", "zzdel3"), ("dict", "zecust", "zqdel1")],
    "ze2": [("voc", "voc", "zzdel4"), ("dict", "zecust2", "zqother")],
}


def e11_records(plant):
    """Write E11's records into ze1's and ze2's own files (plant) or take them away, by an administrator program in SDSYS."""
    body = ["$internal", "   openpath '%s/voc' to v1 else crt 'DP no voc' ; stop" % apath("ze1"), "   openpath '%s/voc' to v2 else crt 'DP no voc' ; stop" % apath("ze2"),
            "   openpath '%s/zecust.dic' to d1 else crt 'DP no dict' ; stop" % apath("ze1")]
    for fv, rid, rec in (("v1", "zzdel1", "'X' : @fm : 'to go'"), ("v1", "zzdel2", "'X' : @fm : 'kept'"), ("v1", "zzdel3", "'X' : @fm : 'held'"),
                         ("d1", "zqdel1", "'D' : @fm : '1' : @fm : '' : @fm : 'Gone' : @fm : '5L' : @fm : 'S'"), ("v2", "zzdel4", "'X' : @fm : 'gates off'")):
        body.append("   write %s on %s, '%s'" % (rec, fv, rid) if plant else "   delete %s, '%s'" % (fv, rid))
    body += ["   crt 'DP done'", "end", ""]
    g.put(os.path.join(sh.SYS, "bp", "zzdplant"), "\n".join(body))
    out = g.adm(["BASIC bp zzdplant", "RUN bp zzdplant"], internal=True)
    if not has(out, r"^DP done$"):
        bail("E11's records were not %s:\n%s" % ("planted" if plant else "taken away", "\n".join(out[-6:])))


class Holder:
    """A LIVE administrator session that holds ze1's VOC record zzdel3 with READU and waits on INPUT (its input stays open); release() ends it, and the lock with it."""
    def __init__(self):
        g.put(os.path.join(sh.SYS, "bp", "zzhold"), "\n".join(["$internal", "   openpath '%s/voc' to v else crt 'HOLD no voc' ; stop" % apath("ze1"),
                                                                "   readu r from v, 'zzdel3' locked", "      crt 'HOLD locked'", "      stop", "   end else", "      null", "   end",
                                                                "   crt 'HOLD held'", "   input x", "   crt 'HOLD released'", "end", ""]))
        out = g.adm(["BASIC bp zzhold"], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("zzhold was not compiled:\n" + "\n".join(out[-6:]))
        say("    > [admin] [internal] in sys, LIVE: RUN bp zzhold (holds ze1 voc zzdel3 until its input is answered)")
        self.buf = []
        self.p = subprocess.Popen([g.SD, "-internal"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sh.SYS, env=g.env(True))
        threading.Thread(target=self._read, daemon=True).start()
        self.p.stdin.write(b"\nTERM 200,9999\nRUN bp zzhold\n")
        self.p.stdin.flush()
        end = time.time() + 20
        while time.time() < end and "HOLD held" not in self.text():
            time.sleep(0.3)
        self.held = "HOLD held" in self.text()

    def _read(self):
        for chunk in iter(lambda: self.p.stdout.read1(4096), b""):
            self.buf.append(chunk.decode("latin-1", "replace"))

    def text(self):
        return "".join(self.buf)

    def release(self):
        try:
            self.p.stdin.write(b"\nOFF\n")
            self.p.stdin.close()
            self.p.wait(timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()
            self.p.wait()


def d_and_confirm(p, typed):
    """D, Run in the confirm box, then the id typed in the second box; returns the text of the box as it was shown."""
    p.h.typed("d", idle=1.5)
    box = p.text()
    p.h.typed("r", idle=1.2)
    p.h.typed(typed + "\r", idle=2.5)
    return box


def section_e11():
    say("\n--- E11: D deletes the record in its own account after its id is typed; the pointer rule refuses what lies outside it (S.96 M3)")
    fixture_e10()
    # ze1's two pointers to the link and the directory of links, as E10's body makes them (reset_e10 takes them away); without them zeesc is the only row of E11f
    voc_write("zzelnk", [("ze1", "zelnk", ["F", "zelnk", "zelnk.dic"]), ("ze1", "zesub", ["F", "zesub", "zesub.dic"])])
    e11_records(True)
    B = snap(TRACK11)
    a0 = audit_off()
    arow("E11a", "control: the planted records are there (ze1 zzdel1 zzdel2 zzdel3 and the item zqdel1, ze2 zzdel4) and SDSYS holds none of the page's pointers",
         B[("ze1", "voc", "voc", "zzdel1")] == "X|to go" and B[("ze1", "voc", "voc", "zzdel3")] == "X|held" and B[("ze1", "dict", "zecust", "zqdel1")] == "D|1||Gone|5L|S"
         and B[("ze2", "voc", "voc", "zzdel4")] == "X|gates off", repr(B))
    p = Page()
    p.walk_to("ze1")
    p.key("tab", 0.6)
    p.key("/", 1.0)
    p.h.typed("zzdel1\r", idle=1.5)
    box = d_and_confirm(p, "zzdel1")
    arow("E11b", "D on ze1's zzdel1 shows the box 'Delete this record?' naming the record and the account (no editor), and Run with the id typed deletes it: the status line says so",
         "Delete this record?" in box and "delete zzdel1 from the VOC of ze1" in box and "deleted zzdel1 from the VOC of ze1" in norm(p.st()), repr((box[box.find("Delete"):][:400], p.st())))
    p.key("/", 1.0)
    p.h.typed("zzdel2\r", idle=1.5)
    p.h.typed("d", idle=1.5)
    p.key("esc", 1.5)
    st_cancel = norm(p.st())
    box = d_and_confirm(p, "zzdelx")
    st_wrong = norm(p.st())
    arow("E11c", "D on zzdel2: Cancel (Esc) says nothing was run; Run with a wrong id typed (zzdelx) says what was typed is not zzdel2 (the record is judged on the disk at the end)",
         "nothing was run" in st_cancel and "what was typed is not zzdel2" in st_wrong, repr((st_cancel, st_wrong)))

    say("  a record another live session holds")
    hold = Holder()
    try:
        p.key("/", 1.0)
        p.h.typed("zzdel3\r", idle=1.5)
        p.h.typed("d", idle=2.0)
        T = p.text()
        st_lock = norm(p.st())
        boxed = "Delete this record?" in T
        if boxed:
            p.key("esc", 1.5)                          # a page that offers the box anyway: it is cancelled, so the row fails on what it showed and not on a delete
    finally:
        hold.release()
    arow("E11d", "D on zzdel3, which a LIVE session holds with READU, is refused with no box: 'locked by user'", hold.held and not boxed and "is locked by user" in st_lock and "not deleted" in st_lock,
         repr((hold.held, boxed, st_lock, hold.text()[-200:])))

    say("  a dictionary item, and the pointer rule")
    p.key("k", 1.2)
    p.key("/", 1.0)
    p.h.typed("zqdel1\r", idle=1.5)
    box = d_and_confirm(p, "zqdel1")
    arow("E11e", "D on the item zqdel1 of ze1's zecust names the dictionary in the box and deletes it with its id typed", "delete zqdel1 from the dictionary of zecust of ze1" in box
         and "deleted zqdel1 from the dictionary of zecust of ze1" in norm(p.st()), repr((box[box.find("Delete"):][:400], p.st())))
    p.key("/", 1.0)
    p.h.typed("zqother\r", idle=1.5)
    said = []
    for _ in range(3):                                 # zeesc (written ../ze2/..), zelnk (a link), zesub (a directory of links), in that order as in E10
        m = re.search(r"zqother in the dictionary of (\S+) of ze1", p.text())     # the box under the lists names the row under the cursor: the instrument for where D is pressed
        p.h.typed("d", idle=2.0)
        T = p.text()
        said.append((norm(p.st()), "Delete this record?" in T, m.group(1) if m else None))
        if "Delete this record?" in T:
            p.key("esc", 1.5)
        p.key("down", 0.6)
    arow("E11f", "D on ze2's item zqother reached through ze1's pointers is refused with no box, each for its reason: zeesc and zelnk lie outside ze1, zesub opens a file outside the account",
         "zeesc lies outside ze1" in said[0][0] and "zelnk lies outside ze1" in said[1][0] and "opens a file outside the account" in said[2][0] and not any(b for _, b, _ in said)
         and [c for _, _, c in said] == ["zeesc", "zelnk", "zesub"], repr(said))
    p.key("k", 1.2)
    p.h.typed("d", idle=1.0)
    arow("E11g", "D on the programs says they are not deleted from this page yet (M4)", "not deleted from this page yet" in norm(p.st()), repr(p.st()))

    say("  an account with every edit gate off")
    p.key("k", 1.2)                                    # round to the VOC
    p.key("tab", 0.6)
    arrived = p.walk_to("ze2")
    p.key("tab", 0.6)
    p.key("/", 1.0)
    p.h.typed("zzdel4\r", idle=1.5)
    d_and_confirm(p, "zzdel4")
    arow("E11h", "ze2 holds every edit gate off: the administrator's D deletes its zzdel4 all the same", arrived and "deleted zzdel4 from the VOC of ze2" in norm(p.st()), repr((arrived, p.st())))
    p.quit()

    say("  the files, read once at the end by a separate session in each account (the oracle)")
    S = snap(TRACK11)
    arow("E11i", "deleted from the account's own file: ze1's zzdel1, ze1's item zqdel1, ze2's zzdel4", S[("ze1", "voc", "voc", "zzdel1")] == "NONE" and S[("ze1", "dict", "zecust", "zqdel1")] == "NONE"
         and S[("ze2", "voc", "voc", "zzdel4")] == "NONE", repr(S))
    arow("E11j", "kept: zzdel2 (Cancel, then a wrong id), zzdel3 (held by another session) and ze2's zqother (outside ze1, refused three ways), each as planted",
         S[("ze1", "voc", "voc", "zzdel2")] == "X|kept" and S[("ze1", "voc", "voc", "zzdel3")] == "X|held" and S[("ze2", "dict", "zecust2", "zqother")] == B[("ze2", "dict", "zecust2", "zqother")], repr(S))
    arow("E11k", "SDSYS's VOC holds none of the page's pointers at the end: each was given back (after a delete, a Cancel, a wrong id, a lock, a refusal)", S["zm"] == B["zm"], repr((B["zm"], S["zm"])))
    lines = [ln for ln in audit_new(a0).splitlines() if "master " in ln]
    want = ["master delete account=ze1 kind=voc file=voc id=zzdel1", "master delete account=ze1 kind=dict file=zecust id=zqdel1", "master delete account=ze2 kind=voc file=voc id=zzdel4"]
    arow("E11l", "the audit trail: one 'master delete' line for each of the three deletes, in lower case, and nothing else from the page (no 'master edit', nothing for zzdel2, zzdel3 or zqother)",
         all(len([ln for ln in lines if w in ln]) == 1 for w in want) and len(lines) == 3, repr(lines[-6:]))
    e11_records(False)
    reset_e10()                        # the links and E10's records, as section_e10 leaves them


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


GROUPS = ("read", "edit", "delete")       # --only=read: E0-E9 (one chain on one page: each section leaves the page where the next starts); edit: E10; delete: E11 (each a page of its own)
LAST_GROUP = {"E10": "edit", "E11": "delete"}                        # a mutant runs the group of its last section; any other last section is in read


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), None)
    groups = set(only.split(",")) if only else set(GROUPS)
    if (mutant is not None and mutant not in MUTANTS) or groups - set(GROUPS) or not groups:
        bail("usage: sandbox-tool-entries.py <dir> [--build] [--only=%s] [--mutant=%s]" % (",".join(GROUPS), "|".join(MUTANTS)))
    last = MUTANTS[mutant][3] if mutant else "E7"
    if mutant is not None:
        groups = {LAST_GROUP.get(last, "read")}
    say("sandbox-tool-entries: sections %s" % ", ".join(g2 for g2 in GROUPS if g2 in groups))
    try:
        sh.setup("sandbox-tool-entries.py")
        setup_page()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-entries: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if "read" in groups:
            if mutant is None:
                section_e0()
            a0 = audit_off()
            p = section_e1()
            if mutant is None or last in ("E5a", "E7", "E8", "E9"):
                n1, n2 = section_e2(p)
                section_e3(p)
                section_e4(p, n1)
            if mutant is None or last in ("E5a", "E8", "E9"):
                section_e5(p)
            if mutant is None or last in ("E8", "E9"):
                section_e8(p)
            if mutant is None or last == "E9":
                section_e9(p)
            if mutant is None:
                section_e6(n1, n2)
                section_e7(p, a0)
            else:
                p.quit()
        if "edit" in groups:
            section_e10()
        if "delete" in groups:
            section_e11()
    finally:
        sh.teardown()
    say("\nsandbox-tool-entries: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"E\d+", i).group(0) for i in FAILED_IDS})
        ok = want == got
        say("sandbox-tool-entries: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
