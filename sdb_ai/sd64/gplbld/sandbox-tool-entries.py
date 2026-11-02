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
    "find-one": ("   for a = 1 to an\n      openpath apath<a>:@ds:'voc' to vf then", "   for a = 1 to 1\n      openpath apath<a>:@ds:'voc' to vf then", ["E5"], "E5a"),
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
    voc_write("zzefix", [("ze1", "zzqa", ["PA", "DISPLAY QA1"]), ("ze1", "zzqb", ["V", "CA", "$zzkf"]), ("ze1", "zzonly1", ["X", "text one"]),
                         ("ze2", "zzqa", ["PA", "DISPLAY QA2"]), ("ze2", "zzonly2", ["X", "text two"]), ("ze5", "zzqc", ["PA", "DISPLAY QC"])])


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
        m = re.search(r"VOC of (\S+)", self.text())
        return m.group(1) if m else None

    def walk_to(self, name, n=40):
        """Down until the Entries box is titled with the account, then Up if Down did not reach it (the focus is the Accounts box)."""
        for direction in ("down", "up"):
            for _ in range(n):
                if self.on() == name:
                    return True
                before = self.on()
                self.key(direction, 0.5)               # 0.3 s was once not enough for the page to redraw (one run of the find-one mutant, E3 only)
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
    arow("E3", "%s: the Entries box says its VOC cannot be opened from here, with its path" % BAD, "VOC cannot be opened from here" in T and apath(BAD)[-12:] in T, T[:600])


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
        if mutant is None or last in ("E5a", "E7"):
            n1, n2 = section_e2(p)
            section_e3(p)
            section_e4(p, n1)
        if mutant is None or last == "E5a":
            section_e5(p)
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
