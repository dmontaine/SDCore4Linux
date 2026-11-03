#!/usr/bin/env python3
#
# sandbox-tool-entries.py - the master files page (S.96 M1a-M2): TOOL.ENTRIES, the VOC entries, dictionary items and programs of every account by pointer, read only until E10 (E and N edit
# the record in its own account).  A private SD, no install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-entries.py <dir> [--build] [--only=read,edit,delete,programs,debug,global] [--mutant=NAME]
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
#   E12  (M4, S.96; --only=programs) the programs: C compiles the program under the cursor IN ITS OWN ACCOUNT through run.in (the object in ze1's bp.out, none in SDSYS or the global
#        catalogue), a syntax error shown and no object; E opens it in the IDE through a pointer, whose F8 compiles and F9 catalogues through run.in in ze1 (no zm...out made in
#        SDSYS; ze1's private catalogue), F5 and F7 refused; N makes a program; the pointer rule: ze2's zpother through ze1's ze2.bp refused for E and C, a record that is a LINK
#        to ze2's file refused, a LINK that leads nowhere refused for N (the kernel's resolve_name, 2 Nov 26: red on the tree before, the IDE opened it as a new record), and nothing of ze2 changed; the audit lines.  The disk is the oracle (a program is a file).
#        Mutants: ide-compiles-here, no-record-test.  setup_page copies and compiles the tree's ide too.
#        M6a (2 Nov 26): D on a program deletes it AND its compiled program in ze1's bp.out after its id is typed, its private catalogue entry LEFT (E12m, E12s); a program file of
#        ze1 whose .out file beside it is a LINK to ze2's bp.out is refused with no box (E12q: the pointer rule for the object), ze2's program through ze2.bp too (E12r).
#   E13  (M5, S.96; --only=debug) B on a program gives the terminal to the debugger IN ze1 through run.in (its key row, stopped at the first statement, the object compiled in ze1's
#        bp.out and none in SDSYS's), Q and the pause bring the page back; the IDE's F7 on a tab the page opened does the same and the IDE comes back; run.in's audit lines
#        and 'master debug'.  E13e (M6a): the editor's breakpoints handed to the debugger run through run.in - a CLICK in the IDE's gutter marks a line (the harness has no
#        Shift-F7 for the console terminal type), F7 stops ON it in ze1, and the mark comes back.
#        Mutants: page-debug-here, ide-debug-here.
#   E14  (S.97 / S.96, 3 Nov 26; --only=global) G, the global change of every row shown, and U, its undo: a find across accounts; ONE preview box per account with its count, first ids
#        and refusals (a phrase has no heading; ze2's item through ze1's pointer and ze6's item that ONLY ze1's pointer reaches are refused by the pointer rule); Cancel writes nothing;
#        Run writes each record in its own account (the disk is the oracle), one undo record per write and none for a refused or failed row; U puts back what is still as the run
#        left it and LEAVES a record edited since; a second U is not offered; the VOC kind with a record a LIVE session holds (refused, the next account done all the same); the
#        programs replaced in the source and compiled again in each account by run.in (objects newer), a read-only source failed with no undo record, U compiling again; the audit lines.
#        Mutants: global-no-rule, global-stops, undo-no-digest, undo-after-write.
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

GC_RULE = ("   gin = kernel(K$PATH.IN, ap.f : @fm : tp)\n   rt = ''\n   if gin then\n      openpath tp to gf else\n         gfwhy = 'the file cannot be opened (' : tp : ')'\n"
           "         return\n      end\n      gfopen = 1\n      rp = fileinfo(gf, FL$PATH)\n      rt = fileinfo(gf, FL$TYPE)\n      gin = kernel(K$PATH.IN, ap.f : @fm : rp)\n"
           "      if gkd # 3 then\n         if gin then gin = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%0')\n         if gin then gin = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%1')\n"
           "      end\n   end\n")                    # gc.file's pointer rule for G and U, as tool_entries has it (the global-no-rule mutant answers each question "inside")

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
    # M4: the IDE compiles a tab of the pointer HERE (BASIC in SDSYS) instead of through run.in; the test of the program's own file is lost
    "ide-compiles-here": ("   if in.ptr # '' and c.file = in.ptr then\n", "   if 0 then\n", ["E12"], "E12"),
    "no-record-test": ("   if isprog and in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : eid)", "   in.ok = in.ok", ["E12"], "E12"),
    # M5: the page's B and the IDE's F7 run the debugger here in SDSYS instead of through run.in in the account
    "page-debug-here": ("   dbsent = 'run.in ' : ea : ' debug ' : efl : ' ' : eid", "   dbsent = 'debug ' : efl : ' ' : eid", ["E13"], "E13"),
    "ide-debug-here": ("execute 'run.in ' : in.acct : ' debug ' : in.file : ' ' : c.id trapping aborts", "execute 'debug ' : in.file : ' ' : c.id trapping aborts", ["E13"], "E13"),
    # G and U (3 Nov 26): the pointer rule of a global change lost; the run stops at the first account with a refusal; U puts back a record changed since the run; the record as
    # it was is kept AFTER the write (so a write that failed leaves an undo record for a record never changed)
    # global-no-rule: EVERY question of the rule answered "inside" (the path, what was opened, its two subfiles).  Its first two forms survived, each for a good reason: the
    # refusal's IF alone taken away left an unopened file to fail the type test, and the path and FL$PATH alone left the subfiles' test to refuse it (3 Nov 26)
    "global-no-rule": (GC_RULE, GC_RULE.replace("kernel(K$PATH.IN, ap.f : @fm : tp)", "1").replace("kernel(K$PATH.IN, ap.f : @fm : rp)", "1")
                       .replace("kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%0')", "1").replace("kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%1')", "1"), ["E14"], "E14"),
    "global-stops": ("         if gk > 0 and gw then gosub gc.audit\n", "         if gk > 0 and gw then gosub gc.audit\n         if gk > 0 and gnr<gk> + gnf<gk> > 0 then exit\n", ["E14"], "E14"),
    "undo-no-digest": ("         case ('S' : digest(cur, 0, 'MD5')) # ('S' : uemd)\n", "         case 0\n", ["E14"], "E14"),
    "undo-after-write": ("   gun += 1\n   write ea : @fm : gkw : @fm : (if efl = '' then 'voc' else efl) : @fm : eid : @fm : digest(gnew, 0, 'MD5') : @fm : grec on uf, gun on error\n"
                         "      gun -= 1\n      release gf, eid\n      grs = 'failed'\n      grw = 'the undo file could not be written (status ' : status() : ')'\n      return\n   end\n"
                         "   writeu gnew on gf, eid on error\n      grs = 'failed'\n      grw = 'the file refused the write (status ' : status() : ')'\n"
                         "      delete uf, gun                                            ;* the old record of a write that did not happen is not kept\n      gun -= 1\n   end\n",
                         "   writeu gnew on gf, eid on error\n      grs = 'failed'\n      grw = 'the file refused the write (status ' : status() : ')'\n   end\n"
                         "   gun += 1\n   write ea : @fm : gkw : @fm : (if efl = '' then 'voc' else efl) : @fm : eid : @fm : digest(gnew, 0, 'MD5') : @fm : grec on uf, gun on error\n"
                         "      gun -= 1\n   end\n", ["E14"], "E14"),
}
MUTANT_PROG = {"ide-compiles-here": "ide", "ide-debug-here": "ide"}          # the program a mutant changes, when it is not the page; setup_page copies both from the tree first, so a mutant does not outlive its run
KEY_F5, KEY_F7, KEY_F8, KEY_F9 = "\x1b[[E", "\x1b[18~", "\x1b[19~", "\x1b[20~"     # the console's codes (the sandbox's terminal is linux, as sh.KEYS)


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
    import shutil
    for prog in ("tool_entries", "ide"):              # M4: the IDE's half too, so a reused sandbox runs the tree's and an IDE mutant does not outlive its run
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
    prog = MUTANT_PROG.get(name, "tool_entries")
    path = os.path.join(sh.SYS, "gpl.bp", prog)
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp %s" % prog], internal=True)
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
    # the path on lines of its own, WRAPPED at the box's width (2 Nov 26: under regress.sh's long sandbox directory it was cut at the edge, the account's name lost):
    # the wrapped text is joined back from the column the label starts in to the box's right border, line by line, until a blank line
    wrapped = ""
    L = p.h.lines()
    for i, ln in enumerate(L):
        x0 = ln.find("Its path in the register: ")
        if x0 >= 0:
            for ln2 in L[i:i + 6]:
                rb = ln2.find("|", x0)
                seg = (ln2[x0:rb] if rb > x0 else ln2[x0:]).rstrip()
                if not seg:
                    break
                wrapped += seg if not wrapped else seg.strip()
            break
    ok3 = "VOC cannot be opened from here." in T and ("Its path in the register: " + apath(BAD)) in wrapped
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
    p.h.typed("c", idle=1.0)
    arow("E10t", "C in the dictionary view says C compiles a program and K shows them (M4: E on the programs is E12's)", "C compiles a program" in norm(p.st()) and not ide_up(p.h), repr(p.st()))
    p.key("k", 1.2)
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
    """A LIVE administrator session that holds ze1's VOC record rid (zzdel3 for E11, zgvheld for E14) with READU and waits on INPUT (its input stays open); release() ends it, and the lock with it."""
    def __init__(self, rid="zzdel3"):
        g.put(os.path.join(sh.SYS, "bp", "zzhold"), "\n".join(["$internal", "   openpath '%s/voc' to v else crt 'HOLD no voc' ; stop" % apath("ze1"),
                                                                "   readu r from v, '%s' locked" % rid, "      crt 'HOLD locked'", "      stop", "   end else", "      null", "   end",
                                                                "   crt 'HOLD held'", "   input x", "   crt 'HOLD released'", "end", ""]))
        out = g.adm(["BASIC bp zzhold"], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("zzhold was not compiled:\n" + "\n".join(out[-6:]))
        say("    > [admin] [internal] in sys, LIVE: RUN bp zzhold (holds ze1 voc %s until its input is answered)" % rid)
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
    p.key("k", 1.2)                                    # to the programs (E11g, "programs are not deleted yet", went with M6a: D of a program is E12m-E12s)

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


def zw_fixture():
    """E12's programs in ze1's bp, written as files (a directory file's records ARE files), their objects and catalogue entries taken away, and two links: zwlink to ze2's
    zpother (a file outside ze1) and zwdang to a name in ze2's bp that does not exist (a link that leads nowhere).  Written over each time, so a reused sandbox starts the same."""
    bp1, bp2 = os.path.join(apath("ze1"), "bp"), os.path.join(apath("ze2"), "bp")
    srcs = {"zwedit": "program zwedit\n   crt 'ZW one'\nend\n", "zwbad": "program zwbad\n   crt 'ZW bad'\n   x = (1 +\nend\n"}     # an ERROR, not a warning (a missing END only warns and compiles)
    for pid, text in srcs.items():
        g.put(os.path.join(bp1, pid), text)
    for d, pid in ((os.path.join(apath("ze1"), "bp.out"), "zwedit"), (os.path.join(apath("ze1"), "bp.out"), "zwbad"), (bp1, "zwnew"), (os.path.join(apath("ze1"), "bp.out"), "zwnew")):
        if os.path.lexists(os.path.join(d, pid)):
            os.remove(os.path.join(d, pid))
    for nm in ("zwlink", "zwdang"):
        if os.path.lexists(os.path.join(bp1, nm)):
            os.remove(os.path.join(bp1, nm))
    os.symlink(os.path.join(bp2, "zpother"), os.path.join(bp1, "zwlink"))
    os.symlink(os.path.join(bp2, "zwnowhere"), os.path.join(bp1, "zwdang"))
    if os.path.lexists(os.path.join(bp2, "zwnowhere")):
        os.remove(os.path.join(bp2, "zwnowhere"))
    # M6a: zwdel, compiled and catalogued IN ze1 by an administrator session (its object in ze1's bp.out, a private catalogue entry), for D; and zeob.bp, a program file of ze1
    # whose .out file BESIDE it is a LINK to ze2's bp.out, holding zwob, whose object of the same name is planted in ze2's bp.out (the pointer rule for the compiled program)
    g.put(os.path.join(bp1, "zwdel"), "program zwdel\n   crt 'ZW del'\nend\n")
    cat1 = os.path.join(apath("ze1"), "cat")
    if os.path.isdir(cat1):
        for f in os.listdir(cat1):
            if f.lower().startswith("zwdel"):
                os.remove(os.path.join(cat1, f))
    out = g.adm(["LOGTO ze1", "BASIC bp zwdel", "CATALOG bp zwdel"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("zwdel was not compiled in ze1:\n" + "\n".join(out[-6:]))
    zeob = os.path.join(apath("ze1"), "zeob.bp")
    os.makedirs(zeob, exist_ok=True)
    g.put(os.path.join(zeob, "zwob"), "program zwob\n   crt 'ZW ob'\nend\n")
    if os.path.lexists(zeob + ".out"):
        os.remove(zeob + ".out")
    os.symlink(os.path.join(apath("ze2"), "bp.out"), zeob + ".out")
    g.put(os.path.join(apath("ze2"), "bp.out", "zwob"), "PLANTED: not an object, and not ze1's to delete\n")
    voc_write("zzeob", [("ze1", "zeob.bp", ["F", "zeob.bp"])])


def zw_unfixture():
    """What zw_fixture made for M6a and the read section must not meet on a reused sandbox: zeob.bp, its link, its VOC entry, ze2's planted zwob, zwdel's catalogue entry."""
    zeob = os.path.join(apath("ze1"), "zeob.bp")
    for p_ in (zeob + ".out", os.path.join(zeob, "zwob"), os.path.join(apath("ze2"), "bp.out", "zwob")):
        if os.path.lexists(p_):
            os.remove(p_)
    if os.path.isdir(zeob) and not os.path.islink(zeob):
        import shutil
        shutil.rmtree(zeob)
    cat1 = os.path.join(apath("ze1"), "cat")
    if os.path.isdir(cat1):
        for f in os.listdir(cat1):
            if f.lower().startswith("zwdel"):
                os.remove(os.path.join(cat1, f))
    g.put(os.path.join(sh.SYS, "bp", "zzeobx"), "\n".join(["$internal", "   openpath '%s/voc' to v else crt 'OBX no voc' ; stop" % apath("ze1"),
                                                           "   delete v, 'zeob.bp'", "   crt 'OBX done'", "end", ""]))
    out = g.adm(["BASIC bp zzeobx", "RUN bp zzeobx"], internal=True)
    if not has(out, r"^OBX done$"):
        bail("ze1's zeob.bp VOC entry was not taken away:\n" + "\n".join(out[-6:]))


def zw_read(acct, *parts):
    p = os.path.join(apath(acct), *parts)
    if not os.path.exists(p):
        return None
    with open(p, encoding="latin-1") as f:
        return f.read()


def zw_mtime(path):
    return os.stat(path).st_mtime_ns if os.path.exists(path) else None


def in_cat(d, name):
    return os.path.isdir(d) and any(f.lower().startswith(name) for f in os.listdir(d))


def section_e12():
    say("\n--- E12: the programs - E and N in the IDE in their own account, C and the IDE's compile and catalogue through run.in, the pointer rule (S.96 M4)")
    zw_fixture()
    obj1, obj2 = os.path.join(apath("ze1"), "bp.out"), os.path.join(apath("ze2"), "bp.out")
    other_m0 = zw_mtime(os.path.join(obj2, "zpother"))
    other_s0 = zw_read("ze2", "bp", "zpother")
    zm0 = sys_zm()
    sys_out0 = sorted(f for f in os.listdir(sh.SYS) if f.startswith("zm"))     # what SDSYS's directory already holds (a reused sandbox may keep an earlier mutant's leftovers)
    a0 = audit_off()
    p = Page()
    p.walk_to("ze1")
    p.key("tab", 0.6)
    p.key("k", 1.2)
    p.key("k", 1.2)
    p.key("/", 1.0)
    p.h.typed("zw\r", idle=1.5)
    T = p.text()
    arow("E12a", "control: the programs of ze1 filtered to zw - zwbad and zwedit are listed, not built (-), and neither has an object on the disk",
         re.search(r"\bbp zwbad - ", T) is not None and re.search(r"\bbp zwedit - ", T) is not None and not os.path.exists(os.path.join(obj1, "zwedit")), T[:700])

    say("  C compiles in the account, through run.in")
    p.key("/", 1.0)
    p.h.typed("zwedit\r", idle=1.5)
    p.h.typed("c", idle=6.0)
    box = p.text()
    p.key("enter", 2.0)
    st_c = norm(p.st())
    m_c = zw_mtime(os.path.join(obj1, "zwedit"))
    arow("E12b", "C on zwedit: the box 'Compile zwedit in ze1' shows the compiler's success line, the status line says it was compiled in ze1, and the object is in ze1's bp.out - not in "
         "SDSYS's bp.out and not in the global catalogue",
         "Compile zwedit in ze1" in box and "Compiled 1 program(s) with no errors" in box and "compiled zwedit in ze1" in st_c and m_c is not None
         and not os.path.exists(os.path.join(sh.SYS, "bp.out", "zwedit")) and not in_cat(os.path.join(sh.SYS, "gcat"), "zwedit"), repr((box[box.find("Compile"):][:300], st_c, m_c)))
    p.key("/", 1.0)
    p.h.typed("zwbad\r", idle=1.5)
    p.h.typed("c", idle=6.0)
    box = p.text()
    p.key("enter", 2.0)
    st_b = norm(p.st())
    arow("E12c", "C on zwbad (a syntax error): the box shows the compiler's words without its success line, the status line says it did not compile, and there is no object",
         "Compile zwbad in ze1" in box and "Compiled 1 program(s) with no errors" not in box and "did not compile" in st_b and not os.path.exists(os.path.join(obj1, "zwbad")),
         repr((box[box.find("Compile"):][:300], st_b)))

    say("  E: the IDE in the account; its F8, F9, F5 and F7")
    p.key("/", 1.0)
    p.h.typed("zwedit\r", idle=1.5)
    up = ide_open(p, "e")
    T = p.h.text()
    zm_open = sys_zm()
    arow("E12d", "E on zwedit gives the screen to the IDE with the program open, and SDSYS's VOC holds one temporary pointer to ze1's bp while it is open",
         up and "ZW one" in T and len(zm_open) == len(zm0) + 1 and any(re.match(r"zm\d+\.ze1\.bp$", z) for z in zm_open), repr((up, zm_open, T[:300])))
    p.h.key("down", idle=0.3)
    p.h.key("end", idle=0.3)
    p.h.typed(" : ' two'", idle=0.5)
    p.h.typed("\x13", idle=1.8)
    time.sleep(1.1)                                    # the object's time must be able to move
    p.h.typed(KEY_F8, idle=6.0)
    st8 = p.h.text()
    m_8 = zw_mtime(os.path.join(obj1, "zwedit"))
    sys_out = sorted(f for f in os.listdir(sh.SYS) if f.startswith("zm"))
    arow("E12e", "the IDE's F8 on that tab compiled IN ze1 through run.in: the IDE says compiled with no errors, ze1's object is newer, and SDSYS's directory gained no zm...out file or "
         "directory (BASIC was not run on the pointer here)", "with no errors" in st8 and m_8 is not None and m_c is not None and m_8 > m_c and sys_out == sys_out0,
         repr((m_c, m_8, sys_out0, sys_out, st8[-400:])))
    p.h.typed(KEY_F9, idle=7.0)
    st9 = p.h.text()
    arow("E12f", "F9 (compile and catalogue) catalogues through run.in in ze1: the IDE says Catalogued, ze1's private catalogue has zwedit and the global catalogue does not",
         "Catalogued" in st9 and in_cat(os.path.join(apath("ze1"), "cat"), "zwedit") and not in_cat(os.path.join(sh.SYS, "gcat"), "zwedit"), st9[-400:])
    p.h.typed(KEY_F5, idle=2.0)
    st5 = p.h.text()
    arow("E12g", "F5 (run) on that tab is refused in words, and the IDE is still on the screen (F7, debug, is E13's: M5)", "is not run from here" in st5 and ide_up(p.h), st5[-300:])
    to_page(p)
    src_now = zw_read("ze1", "bp", "zwedit")
    arow("E12h", "the edit was written into ze1's own bp (the disk), and the page came back saying so", src_now is not None and "' two'" in src_now
         and "back from the editor: the list shows the programs" in norm(p.st()), repr((src_now, p.st())))

    say("  N: a new program in the same file")
    p.h.typed("n", idle=1.2)
    T = p.text()
    asked = "Id of the new program in bp (ze1)" in T
    p.h.typed("zwnew\r", idle=2.5)
    up_n = wait_for(p.h, ide_up, 12)
    p.h.typed("program zwnew\rcrt 'ZW new'\rend", idle=0.8)
    p.h.typed("\x13", idle=1.8)
    to_page(p)
    arow("E12i", "N asks 'Id of the new program in bp (ze1)', the IDE opens it, and the saved program is in ze1's bp on the disk", asked and up_n and "ZW new" in (zw_read("ze1", "bp", "zwnew") or ""),
         repr((asked, up_n, zw_read("ze1", "bp", "zwnew"))))

    say("  THE POINTER RULE for programs: refused before anything is written or compiled")
    p.key("/", 1.0)
    p.h.typed("zpother\r", idle=1.5)
    rows = norm(p.text())
    p.h.typed("e", idle=1.5)
    st_e = norm(p.st())
    up_e = ide_up(p.h)
    p.h.typed("c", idle=2.5)
    st_c2 = norm(p.st())
    arow("E12j", "control: ze1's pointer ze2.bp lists ze2's zpother marked >; E and C on it are each refused with 'lies outside ze1', no editor, no box",
         re.search(r"ze2\.bp > zpother", rows) is not None and "lies outside ze1" in st_e and not up_e and "lies outside ze1" in st_c2 and "Compile zpother" not in norm(p.text()),
         repr((st_e, st_c2)))
    p.key("/", 1.0)
    p.h.typed("zwlink\r", idle=1.5)
    p.h.typed("e", idle=1.5)
    st_l = norm(p.st())
    up_l = ide_up(p.h)
    p.h.typed("c", idle=2.5)
    st_l2 = norm(p.st())
    arow("E12k", "zwlink, ze1's own bp record that is a LINK to ze2's zpother: E and C are refused by the test of the program's own file ('opens a file outside the account')",
         "opens a file outside the account" in st_l and not up_l and "opens a file outside the account" in st_l2, repr((st_l, st_l2)))
    p.key("/", 1.0)
    p.h.typed("zw\r", idle=1.5)
    p.h.typed("n", idle=1.2)
    p.h.typed("zwdang\r", idle=2.5)
    st_d = norm(p.st())
    up_d = ide_up(p.h)
    if up_d:
        to_page(p)
    arow("E12l", "N with the id zwdang, a LINK in ze1's bp that leads to a name in ze2's bp that does not exist, is refused by the kernel's test of the program's own file "
         "('opens a file outside the account': op_sh.c's resolve_name no longer takes such a link for a new name), no editor",
         "opens a file outside the account" in st_d and not up_d, repr((st_d, up_d)))

    say("  D on a program (M6a): with its compiled program; the pointer rule for the .out file")
    del_src0 = zw_read("ze1", "bp", "zwdel")
    del_obj0 = os.path.exists(os.path.join(obj1, "zwdel"))
    del_cat0 = in_cat(os.path.join(apath("ze1"), "cat"), "zwdel")
    p.key("/", 1.0)
    p.h.typed("zwdel\r", idle=1.5)
    box = d_and_confirm(p, "zwdel")
    st_del = norm(p.st())
    arow("E12m", "D on zwdel (built and catalogued in ze1): the box names the program in ze1's bp and its compiled program, and says a catalogue entry is left; Run with the id typed "
         "deletes both: the status line says so", "delete zwdel from the program file bp of ze1" in box and "compiled program zwdel" in box and "catalogue entry" in box
         and "deleted zwdel from the program file bp of ze1 and its compiled program" in st_del, repr((box[box.find("delete zwdel"):][:500], st_del)))
    p.key("/", 1.0)
    p.h.typed("zwob\r", idle=1.5)
    rows_ob = p.text()
    p.h.typed("d", idle=2.0)
    T = p.text()
    st_ob = norm(p.st())
    boxed_ob = "Delete this record?" in T
    if boxed_ob:
        p.key("esc", 1.5)                              # a page that offers the box anyway: cancelled, so the row fails on what it showed and not on a delete
    arow("E12q", "D on zwob of ze1's own zeob.bp, whose .out file BESIDE it is a LINK to ze2's bp.out, is refused with no box: the compiled programs 'lie outside ze1' (the pointer rule "
         "for the object; the program file itself is ze1's and not marked >)", re.search(r"zeob\.bp zwob ", rows_ob) is not None and "lie outside ze1" in st_ob and not boxed_ob,
         repr((st_ob, boxed_ob, rows_ob[:400])))
    p.key("/", 1.0)
    p.h.typed("zpother\r", idle=1.5)
    p.h.typed("d", idle=2.0)
    T = p.text()
    st_po = norm(p.st())
    boxed_po = "Delete this record?" in T
    if boxed_po:
        p.key("esc", 1.5)
    arow("E12r", "D on ze2's zpother through ze1's pointer ze2.bp (marked >) is refused with no box: the program file 'lies outside ze1'", "lies outside ze1" in st_po and not boxed_po,
         repr((st_po, boxed_po)))
    p.quit()
    arow("E12s", "the disk: zwdel's source and its object in ze1's bp.out are gone (both there before), its private catalogue entry is LEFT (the account's); zwob's source in ze1 and the "
         "file of that name in ze2's bp.out are as they were",
         del_src0 is not None and del_obj0 and zw_read("ze1", "bp", "zwdel") is None and not os.path.exists(os.path.join(obj1, "zwdel"))
         and del_cat0 and in_cat(os.path.join(apath("ze1"), "cat"), "zwdel")
         and zw_read("ze1", "zeob.bp", "zwob") is not None and (zw_read("ze2", "bp.out", "zwob") or "").startswith("PLANTED"),
         repr((del_src0 is not None, del_obj0, del_cat0, zw_read("ze1", "bp", "zwdel"), os.path.exists(os.path.join(obj1, "zwdel")), in_cat(os.path.join(apath("ze1"), "cat"), "zwdel"))))

    say("  the disk and the audit trail at the end")
    arow("E12n", "nothing of ze2 changed: zpother's source and object are as they were, and nothing was made at the end of zwdang's link",
         zw_read("ze2", "bp", "zpother") == other_s0 and zw_mtime(os.path.join(obj2, "zpother")) == other_m0 and not os.path.lexists(os.path.join(apath("ze2"), "bp", "zwnowhere")),
         repr((zw_mtime(os.path.join(obj2, "zpother")), other_m0)))
    arow("E12o", "SDSYS's VOC holds none of the page's pointers at the end", sys_zm() == zm0, repr((zm0, sys_zm())))
    lines = [ln for ln in audit_new(a0).splitlines() if "master " in ln]
    want = ["master compile account=ze1 file=bp id=zwedit result=ok", "master compile account=ze1 file=bp id=zwbad result=failed",
            "master edit account=ze1 kind=bp file=bp id=zwedit new=0", "master edit account=ze1 kind=bp file=bp id=zwnew new=1",
            "master delete account=ze1 kind=bp file=bp id=zwdel object=deleted"]
    runin = [ln for ln in audit_new(a0).splitlines() if "run.in begin account=ze1" in ln]
    arow("E12p", "the audit trail: one line each for the two compiles, the two edits and zwdel's delete (object=deleted), none for zpother, zwob, zwlink or zwdang, and run.in's own begin lines for the page's two "
         "compiles and the IDE's F8 and F9 (at least four)", all(len([ln for ln in lines if w in ln]) == 1 for w in want) and len(lines) == 5 and len(runin) >= 4,
         repr((lines[-6:], len(runin))))
    for nm in ("zwlink", "zwdang"):
        os.remove(os.path.join(apath("ze1"), "bp", nm))     # the read section lists ze1's programs: it must not meet them
    zw_unfixture()


DBG_KEYS = "F1 help  F2 abort  F3 stop  F4 screen  F5 run  F7 step  F8 line  ^F7 parent  ^F8 program"      # the debugger's key row (sandbox-idebrk.py)


def in_debugger(h):
    return any(ln.rstrip() == DBG_KEYS for ln in h.lines()[-4:])


def dbg_arrows(h):
    """the source lines the debugger marks > (the line about to run), from its source pane (rows 1 to 32, before the Autos pane at column 92)"""
    out = []
    for ln in h.lines()[1:33]:
        m = re.match(r"^>\s*(\d+): ", ln[:91])
        if m:
            out.append(int(m.group(1)))
    return out


IDE_MARKCOL = 29                   # the IDE's gutter: its first cell is the breakpoint mark (sandbox-idebrk.py MARKCOL; the editor's border is column 28)


def ide_marks(h, count):
    """the lines 1..count the IDE's gutter marks with * (the editor shows line 1 on row 3)"""
    L = h.lines()
    return [n for n in range(1, count + 1) if len(L[2 + n]) > IDE_MARKCOL and L[2 + n][IDE_MARKCOL] == "*"]


def dbg_mark(L, n):
    """the debugger's mark of source line n (column 0 of its row in the source pane: > about to run, * a breakpoint), as sandbox-idebrk.py dmark"""
    for ln in L[1:33]:
        if re.match(r"^[ *>]\s*%d: " % n, ln[:91]):
            return ln[0]
    return None


def section_e13():
    say("\n--- E13: debugging a program IN ITS OWN ACCOUNT, from the page (B) and from the IDE (F7), through run.in (S.96 M5)")
    bp1, obj1 = os.path.join(apath("ze1"), "bp"), os.path.join(apath("ze1"), "bp.out")
    g.put(os.path.join(bp1, "zwdbg"), "program zwdbg\n   crt 'DBG one'\n   x = 1\n   crt 'DBG two'\nend\n")
    if os.path.lexists(os.path.join(obj1, "zwdbg")):
        os.remove(os.path.join(obj1, "zwdbg"))
    zm0 = sys_zm()
    a0 = audit_off()
    p = Page()
    p.walk_to("ze1")
    p.key("tab", 0.6)
    p.key("k", 1.2)
    p.key("k", 1.2)
    p.key("/", 1.0)
    p.h.typed("zwdbg\r", idle=1.5)
    p.h.typed("b", idle=1.0)
    came = wait_for(p.h, lambda t: in_debugger(p.h), 20)
    arr = dbg_arrows(p.h)
    scr = p.h.text()
    arow("E13a", "B on zwdbg gives the terminal to the debugger (its key row is on the screen), stopped at the first statement (line 2 marked >), with the program's object compiled "
         "IN ze1 (ze1's bp.out) and none in SDSYS's bp.out", came and arr == [2] and os.path.exists(os.path.join(obj1, "zwdbg")) and not os.path.exists(os.path.join(sh.SYS, "bp.out", "zwdbg")),
         repr((came, arr, scr[-500:])))
    p.h.typed("q\r", idle=2.0)
    paused = wait_for(p.h, lambda t: "Press Enter to return" in t, 10)
    p.h.key("enter", idle=2.5)
    wait_for(p.h, lambda t: "What this means" in t, 10)
    arow("E13b", "Q in the debugger ends it, run.in brings the session back, the page pauses ('Press Enter to return') and comes back on its own screen saying where it was",
         paused and "back from the debugger: zwdbg was debugged in ze1" in norm(p.st()), repr((paused, p.st())))

    say("  the IDE's F7 on a tab the page opened")
    up = ide_open(p, "e")
    p.h.typed(KEY_F7, idle=1.0)
    came2 = wait_for(p.h, lambda t: in_debugger(p.h), 20)
    arr2 = dbg_arrows(p.h)
    p.h.typed("q\r", idle=2.0)
    paused2 = wait_for(p.h, lambda t: "Press Return to go back to the IDE" in t, 10)
    p.h.key("enter", idle=2.5)
    back2 = wait_for(p.h, ide_up, 10)
    arow("E13c", "E opens zwdbg in the IDE; its F7 gives the terminal to the debugger IN ze1 (through run.in), stopped at line 2; Q, the IDE's pause, and the IDE is back",
         up and came2 and arr2 == [2] and paused2 and back2, repr((up, came2, arr2, paused2, back2)))

    say("  the editor's breakpoints handed to the debugger run through run.in (M6a): a click in the gutter, F7")
    p.h.click(IDE_MARKCOL, 3 + 4 - 1)                  # line 4, crt 'DBG two' (the editor shows line 1 on row 3)
    m_before = ide_marks(p.h, 6)
    p.h.typed(KEY_F7, idle=1.0)
    came3 = wait_for(p.h, lambda t: in_debugger(p.h), 20)
    L3 = p.h.lines()
    star3, arr3 = dbg_mark(L3, 4), dbg_arrows(p.h)
    p.h.typed("q\r", idle=2.0)
    paused3 = wait_for(p.h, lambda t: "Press Return to go back to the IDE" in t, 10)
    p.h.key("enter", idle=2.5)
    back3 = wait_for(p.h, ide_up, 10)
    m_after = ide_marks(p.h, 6)
    arow("E13e", "a click in the IDE's gutter marks line 4 of zwdbg; F7 runs it IN ze1 through run.in and the debugger stops ON line 4 (marked *, no line marked >: it ran on from the "
         "first statement, so it was handed the mark); Q, the pause, the IDE is back and line 4 is still marked (the debugger's list came back)",
         m_before == [4] and came3 and star3 == "*" and arr3 == [] and paused3 and back3 and m_after == [4],
         repr((m_before, came3, star3, arr3, paused3, back3, m_after, "\n".join(L3[:8]))))
    to_page(p)
    p.quit()
    lines = audit_new(a0).splitlines()
    begins = [ln for ln in lines if re.search(r"run\.in begin account=ze1 command=debug bp zwdbg\b", ln)]
    mdbg = [ln for ln in lines if "master debug account=ze1 file=bp id=zwdbg" in ln]
    arow("E13d", "the audit trail: run.in began 'debug bp zwdbg' in ze1 three times (the page's B and the IDE's F7 twice), the page wrote one 'master debug' line, and SDSYS's VOC holds none of "
         "the page's pointers at the end", len(begins) == 3 and len(mdbg) == 1 and sys_zm() == zm0, repr((len(begins), mdbg, sys_zm())))


ZG_DICT = [("zgf1", "D", "1", "Old Head"), ("zgf2", "I", "@ID", "Old Head"), ("zgf4", "D", "1", "Old Head"), ("zgf5", "D", "1", "Old Head")]
ZG_SRC = "program %s\n   crt 'ZG old'\nend\n"


def zg_paths():
    """label -> (the file's path, the record id): what E14 judges on the disk."""
    return {"zgf1": (os.path.join(apath("ze1"), "zecust.dic"), "zgf1"), "zgf2": (os.path.join(apath("ze1"), "zecust.dic"), "zgf2"),
            "zgf3": (os.path.join(apath("ze1"), "zecust.dic"), "zgf3"), "zgf4": (os.path.join(apath("ze2"), "zecust2.dic"), "zgf4"),
            "zgf5": (os.path.join(apath(BAD), "zgout.dic"), "zgf5"),
            "zgv1": (os.path.join(apath("ze1"), "voc"), "zgv1"), "zgvheld": (os.path.join(apath("ze1"), "voc"), "zgvheld"), "zgv2": (os.path.join(apath("ze2"), "voc"), "zgv2")}


def zg_fixture():
    """E14's records, written over each time (a reused sandbox starts the same): dictionary items in ze1's zecust (zgf1 D, zgf2 I, zgf3 a phrase, which has no heading), in ze2's
    zecust2 (zgf4, also seen from ze1 through its pointer zeesc, written ../ze2/..) and in a dictionary in ze6's directory (zgf5, which only ze1's pointer zgout reaches: ze6 has no VOC,
    so nothing but the pointer rule keeps it unchanged); VOC entries zgv1, zgvheld (ze1) and zgv2 (ze2); programs zgp1 and zgpro (ze1, zgpro READ ONLY on the disk so that its write
    fails) and zgp2 (ze2, also seen from ze1 through ze2.bp), each compiled in its account.  The undo file of an earlier run is emptied."""
    import shutil
    out_dic = os.path.join(apath(BAD), "zgout.dic")
    if os.path.isdir(out_dic):
        shutil.rmtree(out_dic)
    shutil.copytree(os.path.join(apath("ze2"), "zecust2.dic"), out_dic)       # a hashed file of its own, cleared below
    body = ["$internal", "   openpath '%s/zecust.dic' to d1 else crt 'ZG no d1' ; stop" % apath("ze1"), "   openpath '%s/zecust2.dic' to d2 else crt 'ZG no d2' ; stop" % apath("ze2"),
            "   openpath '%s' to d5 else crt 'ZG no d5' ; stop" % out_dic, "   clearfile d5",
            "   openpath '%s/voc' to v1 else crt 'ZG no v1' ; stop" % apath("ze1"), "   openpath '%s/voc' to v2 else crt 'ZG no v2' ; stop" % apath("ze2")]
    for iid, ity, f2, head in ZG_DICT:
        fv = {"zgf1": "d1", "zgf2": "d1", "zgf4": "d2", "zgf5": "d5"}[iid]
        body.append("   write '%s':@fm:'%s':@fm:'':@fm:'%s':@fm:'10L':@fm:'S' on %s, '%s'" % (ity, f2, head, fv, iid))
    body += ["   write 'PH':@fm:'ZGF1 ZGF2' on d1, 'zgf3'",
             "   write 'F':@fm:'../ze6/zgout':@fm:'../ze6/zgout.dic' on v1, 'zgout'",
             "   write 'X':@fm:'old text' on v1, 'zgv1'", "   write 'X':@fm:'old text' on v1, 'zgvheld'", "   write 'X':@fm:'old text' on v2, 'zgv2'",
             "   open '&entries.undo&' to u then clearfile u",
             "   crt 'ZG done'", "end", ""]
    g.put(os.path.join(sh.SYS, "bp", "zzgfix"), "\n".join(body))
    out = g.adm(["BASIC bp zzgfix", "RUN bp zzgfix"], internal=True)
    if not has(out, r"^ZG done$"):
        bail("E14's records were not written:\n" + "\n".join(out[-8:]))
    for acct, pids in (("ze1", ("zgp1", "zgpro")), ("ze2", ("zgp2",))):
        for pid in pids:
            path = os.path.join(apath(acct), "bp", pid)
            if os.path.exists(path):
                os.chmod(path, 0o644)
            g.put(path, ZG_SRC % pid)
        out = g.adm(["LOGTO %s" % acct] + ["BASIC bp %s" % pid for pid in pids])
        if len([ln for ln in out if re.match(r"^Compiled 1 program\(s\) with no errors", ln)]) != len(pids):
            bail("E14's programs were not compiled in %s:\n%s" % (acct, "\n".join(out[-8:])))
    os.chmod(os.path.join(apath("ze1"), "bp", "zgpro"), 0o444)                 # its WRITE fails (SD writes a directory file's record in place: SAFEDIR is off)


def zg_read(labels=None):
    """The records E14 judges, read by ONE separate administrator session by their paths (fields joined by |, NONE when not there), and the undo file's records (UN|account|id)."""
    paths = zg_paths()
    labels = labels or sorted(paths)
    files = sorted({paths[l][0] for l in labels})
    body = ["$internal"]
    for i, f in enumerate(files):
        body.append("   openpath '%s' to f%d else crt 'ZGR no %s' ; stop" % (f, i, f))
    for l in labels:
        body.append("   read r from f%d, '%s' then crt 'ZGR|%s|' : convert(@fm, '|', r) else crt 'ZGR|%s|NONE'" % (files.index(paths[l][0]), paths[l][1], l, l))
    body += ["   open '&entries.undo&' to u then", "      select u to 9", "      loop", "         readnext uid from 9 else exit", "         if uid # 'last' then",
             "            read ur from u, uid then crt 'UN|' : ur<1> : '|' : ur<4> : '|' : ur<5>", "         end", "      repeat", "   end", "   crt 'ZGR end'", "end", ""]
    g.put(os.path.join(sh.SYS, "bp", "zzgrd"), "\n".join(body))
    out = g.adm(["BASIC bp zzgrd", "RUN bp zzgrd"], internal=True)
    if not has(out, r"^ZGR end$"):
        bail("E14's reader did not answer:\n" + "\n".join(out[-8:]))
    res = {}
    for ln in out:
        if ln.startswith("ZGR|"):
            _, l, rest = ln.rstrip().split("|", 2)
            res[l] = rest
    res["undo"] = sorted(ln.rstrip()[3:] for ln in out if ln.startswith("UN|"))
    return res


def zg_src(acct, pid):
    with open(os.path.join(apath(acct), "bp", pid)) as f:
        return f.read()


def zg_obj(acct, pid):
    p = os.path.join(apath(acct), "bp.out", pid)
    return os.stat(p).st_mtime_ns if os.path.exists(p) else None


def zg_global(p, answers, wait=15.0):
    """G, then the answers to its prompts; returns the preview box's text (or the status line when no box came)."""
    p.h.typed("g", idle=1.2)
    for a in answers:
        p.h.typed(a + "\r", idle=1.2)
    wait_for(p.h, lambda t: "Update these records?" in t, wait)
    return p.text()


def zg_run(p, title, wait=40.0):
    """Run in the box on the screen (and in the box that makes the undo file, if it comes); returns the summary box's text, which is then closed."""
    p.h.typed("r", idle=2.0)
    if "create.file &entries.undo&" in p.text():
        p.h.typed("r", idle=3.0)
    wait_for(p.h, lambda t: title in t, wait)
    T = p.text()
    p.key("enter", 2.0)
    return T


def section_e14():
    say("\n--- E14: G, the global change of every row shown, in all accounts, and U, its undo (S.97 / S.96, 3 Nov 26)")
    zg_fixture()
    B = zg_read()
    o1, o2 = zg_obj("ze1", "zgp1"), zg_obj("ze2", "zgp2")
    a0 = audit_off()
    arow("E14a", "control: the fixture's records are on the disk (zgf1 zgf2 zgf4 zgf5 with the heading Old Head, zgf3 a phrase, the VOC entries old text), the programs compiled, no undo record",
         all(B[l].split("|")[3] == "Old Head" for l in ("zgf1", "zgf2", "zgf4", "zgf5")) and B["zgf3"].startswith("PH|") and all(B[l] == "X|old text" for l in ("zgv1", "zgvheld", "zgv2"))
         and o1 and o2 and B["undo"] == [], repr(B))
    p = Page()
    p.key("k", 1.2)                                            # the dictionary items
    p.key("f", 1.0)
    p.h.typed("zgf\r", idle=2.5)
    box = norm(zg_global(p, ["heading", "s", "New Head"]))
    p.key("esc", 1.5)
    st_cancel = norm(p.st())
    arow("E14b", "G on the find 'zgf' (every account), heading set to New Head: ONE box titled 'Update these records?' lists ze1 with 2 to change (zecust zgf1, zecust zgf2) and 3 refused "
         "(the phrase has no heading; ze2's zgf4 through zeesc and ze6's zgf5 through zgout lie outside ze1: the pointer rule) and ze2 with 1 to change; Esc cancels",
         "Update these records?" in box and "ze1: 2 to change (zecust zgf1 zecust zgf2)" in box and "3 refused" in box and "ze2: 1 to change (zecust2 zgf4)" in box
         and "zecust zgf3: it has no" in box and "heading (not a D, I, E or L item)" in box and "nothing was run" in st_cancel,      # the box wraps after "no" (first run, 3 Nov 26)
         repr((box[box.find("Update"):][:1500], st_cancel)))
    C = zg_read()
    arow("E14c", "Cancel wrote nothing: every record as the fixture made it", all(C[l] == B[l] for l in zg_paths()) and C["undo"] == [], repr(C))
    zg_global(p, ["heading", "s", "New Head"])
    summ = norm(zg_run(p, "Global change:"))
    D = zg_read()
    arow("E14d", "Run: zgf1 and zgf2 (ze1) and zgf4 (ze2, in its own account) have the heading New Head; zgf3 (no heading) and ze6's zgf5 (reached only through ze1's pointer) are UNCHANGED "
         "on the disk; the summary says ze1 2 changed 3 refused, ze2 1 changed",
         all(D[l].split("|")[3] == "New Head" for l in ("zgf1", "zgf2", "zgf4")) and D["zgf3"] == B["zgf3"] and D["zgf5"] == B["zgf5"]
         and "ze1: 2 changed, 3 refused, 0 failed" in summ and "ze2: 1 changed, 0 refused, 0 failed" in summ, repr((D, summ[:900])))
    arow("E14e", "the undo file holds one record for each record written - ze1 zgf1, ze1 zgf2, ze2 zgf4 - each with the digest of what was written, and none for a refused row",
         sorted(u.rsplit("|", 1)[0] for u in D["undo"]) == ["ze1|zgf1", "ze1|zgf2", "ze2|zgf4"] and all(len(u.rsplit("|", 1)[1]) == 32 for u in D["undo"]), repr(D["undo"]))
    # a record edited between the run and the undo: it must be LEFT, never overwritten
    g.put(os.path.join(sh.SYS, "bp", "zzgedit"), "\n".join(["$internal", "   openpath '%s/zecust.dic' to d else crt 'ZGE no' ; stop" % apath("ze1"),
                                                            "   read r from d, 'zgf2' else r = ''", "   r<4> = 'Edited Since'", "   write r on d, 'zgf2'", "   crt 'ZGE done'", "end", ""]))
    out = g.adm(["BASIC bp zzgedit", "RUN bp zzgedit"], internal=True)
    if not has(out, r"^ZGE done$"):
        bail("zgf2 was not edited:\n" + "\n".join(out[-6:]))
    p.h.typed("u", idle=1.5)
    ubox = norm(p.text())
    usum = norm(zg_run(p, "Undo of the global change"))
    p.h.typed("u", idle=1.5)
    st_again = norm(p.st())
    U = zg_read()
    arow("E14f", "U (the box 'Put these records back?') puts back zgf1 and zgf4 as the fixture made them; zgf2, edited since the run, is LEFT as edited and counted; the disk is the oracle",
         "Put these records back?" in ubox and U["zgf1"] == B["zgf1"] and U["zgf4"] == B["zgf4"] and U["zgf2"].split("|")[3] == "Edited Since"
         and "2 put back, 1 left (changed since the run)" in usum, repr((U, usum[:600])))
    arow("E14g", "a second U is not offered: it says the change has been put back already, and nothing moves", "put back already" in st_again and zg_read(["zgf2"])["zgf2"] == U["zgf2"],
         repr(st_again))

    say("  the VOC kind: a field replaced, a record another live session holds")
    p.key("k", 1.2)
    p.key("k", 1.2)                                            # round to the VOC
    hold = Holder("zgvheld")
    try:
        p.key("f", 1.0)
        p.h.typed("zgv\r", idle=2.5)
        zg_global(p, ["2", "r", "old", "new"])
        vsum = norm(zg_run(p, "Global change:"))
    finally:
        hold.release()
    V = zg_read()
    arow("E14h", "field 2 of the VOC entries: ze1's zgv1 and ze2's zgv2 say new text; zgvheld, which a LIVE session holds with READU, is refused and unchanged, and ze2 is done "
         "all the same (a refusal in one account does not stop the others)",
         hold.held and V["zgv1"] == "X|new text" and V["zgv2"] == "X|new text" and V["zgvheld"] == "X|old text"
         and "ze1: 1 changed, 1 refused" in vsum and "another session holds it" in vsum and "ze2: 1 changed, 0 refused" in vsum, repr((hold.held, V, vsum[:600])))

    say("  the programs: a text replaced in the source, compiled again in each account by run.in")
    p.key("k", 1.2)
    p.key("k", 1.2)                                            # VOC -> dictionary items -> programs
    p.key("f", 1.0)
    p.h.typed("zgp\r", idle=2.5)
    pbox = norm(zg_global(p, ["ZG old", "ZG new"]))
    psum = norm(zg_run(p, "Global change:", wait=60.0))
    P = zg_read([])
    q1, q2 = zg_obj("ze1", "zgp1"), zg_obj("ze2", "zgp2")
    arow("E14i", "the box: ze1 has zgp1 and zgpro to change and ze2's zgp2 through ze2.bp refused (the pointer rule); ze2 has its own zgp2 to change",
         "ze1: 2 to change (bp zgp1 bp zgpro)" in pbox and "1 refused" in pbox and "ze2: 1 to change (bp zgp2)" in pbox, repr(pbox[pbox.find("Update"):][:1200]))
    arow("E14j", "Run: zgp1 (ze1) and zgp2 (ze2) say ZG new on the disk and each is compiled again IN ITS ACCOUNT (its object in that account's bp.out is newer); zgpro, whose file refuses "
         "the write, is failed and unchanged, and ze2 is done all the same; the undo file holds zgp1 and zgp2 and NOTHING for zgpro (the old record is kept BEFORE the write and dropped when the write fails)",
         "ZG new" in zg_src("ze1", "zgp1") and "ZG new" in zg_src("ze2", "zgp2") and "ZG old" in zg_src("ze1", "zgpro") and q1 and q2 and q1 > o1 and q2 > o2
         and "ze1: 1 changed, 1 refused, 1 failed" in psum and "ze2: 1 changed, 0 refused, 0 failed" in psum
         and sorted(u.rsplit("|", 1)[0] for u in P["undo"]) == ["ze1|zgp1", "ze2|zgp2"], repr((psum[:700], P["undo"], q1, o1, q2, o2)))
    p.h.typed("u", idle=1.5)
    zg_run(p, "Undo of the global change", wait=60.0)
    r1, r2 = zg_obj("ze1", "zgp1"), zg_obj("ze2", "zgp2")
    arow("E14k", "U puts the two programs back (ZG old on the disk) and compiles each again in its account (its object newer than after the run)",
         "ZG old" in zg_src("ze1", "zgp1") and "ZG old" in zg_src("ze2", "zgp2") and r1 and r2 and r1 > q1 and r2 > q2, repr((r1, q1, r2, q2)))
    p.quit()
    lines = [ln for ln in audit_new(a0).splitlines() if re.search(r"master global|entries undo", ln)]
    want = [("master global account=ze1 kind=dict changed=2 refused=3 failed=0", 1), ("master global account=ze2 kind=dict changed=1 refused=0 failed=0", 1),
            ("entries undo account=ze1 records=1", 2), ("entries undo account=ze2 records=1", 2),            # the dictionary items' undo and the programs'
            ("master global account=ze1 kind=voc changed=1 refused=1 failed=0", 1), ("master global account=ze2 kind=voc changed=1 refused=0 failed=0", 1),
            ("master global account=ze1 kind=bp changed=1 refused=1 failed=1", 1), ("master global account=ze2 kind=bp changed=1 refused=0 failed=0", 1)]
    arow("E14l", "the audit trail: one 'master global' line per account per run and one 'entries undo' line per account per undo, lower case, and none for the Cancel",
         all(len([ln for ln in lines if w in ln]) == n for w, n in want) and len(lines) == 10, repr(lines))
    os.chmod(os.path.join(apath("ze1"), "bp", "zgpro"), 0o644)


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


GROUPS = ("read", "edit", "delete", "programs", "debug", "global")       # --only=read: E0-E9 (one chain on one page); edit: E10; delete: E11; programs: E12; debug: E13; global: E14 (each a page of its own)
LAST_GROUP = {"E10": "edit", "E11": "delete", "E12": "programs", "E13": "debug", "E14": "global"}       # a mutant runs the group of its last section; any other last section is in read


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
        if "programs" in groups:
            section_e12()
        if "debug" in groups:
            section_e13()
        if "global" in groups:
            section_e14()
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
