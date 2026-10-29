#!/usr/bin/env python3
"""test-toolbackups-units.py - the backups page, TOOL.BACKUPS (`gpl.bp/tool_backups`), as invariants read off the source (S.75, administrator app A8).  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolbackups-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the page's BASIC as text, with comments removed.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT A BACKUP IS MADE OR AN ACCOUNT RESTORED***: the packing
and the placing are done as root (`sd-elevate backup-pack`, `restore-place`), which a sandbox is not; they are `witness-backup.sh`'s on a real install.  What a text check is for: the properties that make
the page a FRONT END - it opens the base for the administrator before it reads, it runs FOUR commands and no others, only through the one routine and only after the box was answered Run, it
builds every sentence from values it has checked in the order that keeps a bad value out of the command, it will not show a box while another session is signed on (the verbs would refuse), it
refuses a restore that would have to make an account (that asks for a password, which a page cannot type), and it reads an archive's manifest and never unpacks one.  Those are ORDER and ABSENCE, and
an edit that moves one still compiles.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
DOCS = "/home/don/Projects/SDCore4LinuxDocs/Administrator/markdown/01a-account-maintenance.md"
FILES = {
    "page": os.path.join(GPL, "tool_backups"),
    "voc": os.path.join(SDSYS, "voc_template", "tool.backups"),
    "help": os.path.join(SDSYS, "helptext", "tool.backups.page"),
    "runx": os.path.join(GPL, "tk_runx"),
    "doc": DOCS,
}
NEWVOC = os.path.join(SDSYS, "newvoc", "tool.backups")


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    raw["newvoc_has"] = "1" if os.path.exists(NEWVOC) else ""
    return raw


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def block(text, label):
    m = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][a-z.0-9]*:\s*$|^end\s*$", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    pg = strip_bas(raw["page"])
    ck("TB0", "NULL CASE: the page, the VOC entry, the help record, tk_runx and the guide were found and are not empty (a check on nothing would pass)",
       len(pg) > 8000 and raw["voc"].strip() != "" and len(raw["help"].split("\n")) >= 4 and len(raw["runx"]) > 500 and raw["doc"].strip() != "", "%d" % len(pg))
    ck("TB1", "the page is an internal program catalogued as $tool_backups, SDSYS's VOC has the verb for it, and the shared VOC (newvoc) has NO tool.backups",
       re.search(r"^\$internal\s*\nprogram \$tool_backups\s*\n\$catalog \$tool_backups\b", pg, re.M) is not None and raw["voc"].split("\n")[:3] == ["V", "CA", "$tool_backups"] and raw["newvoc_has"] == "",
       repr((raw["voc"][:30], raw["newvoc_has"])))
    i_open = pg.find("call $tk_open('tool.backups', 'admin', ctx, err)")
    i_audit = pg.find("kernel(K$AUDIT, 'tool start app=tool.backups')")
    i_first = min([x for x in (pg.find("call !acc_os_bakdir"), pg.find("call !acc_hold"), pg.find("openpath"), pg.find("gosub read.all")) if x >= 0] or [10 ** 9])
    ck("TB2", "the page opens the toolkit's base for the ADMINISTRATOR first (a refusal is shown and the program stops), before it reads anything; its one audit line says it started",
       0 < i_open < i_audit < i_first and re.search(r"call \$tk_open\('tool\.backups', 'admin', ctx, err\)\s*\n\s*if err # '' then\s*\n\s*display err\s*\n\s*stop\s*\n\s*end", pg) is not None and pg.count("K$AUDIT") == 1,
       "open %s audit %s first %s" % (i_open, i_audit, i_first))
    ck("TB3", "it runs exactly FOUR commands, backup.account, restore.account and set.backup.directory (three first words; backup.account has two sentences), through $tk_runx alone, with the one allow list, "
       "directly after the confirm box and guarded by res = 'run'; no execute, perform, chain, os.execute or $tk_run",
       re.findall(r"\ballow = '([^']*)'", pg) == ["backup.account restore.account set.backup.directory"] and pg.count("call $tk_runx(allow, sent, out, stat, err)") == 1 and "$tk_run(" not in pg
       and re.search(r"call \$tk_confirm\(sent, el, typed, res, cmsg\)\s*\n\s*if res = 'run' then\s*\n\s*call \$tk_runx\(allow, sent, out, stat, err\)", pg) is not None
       and not re.search(r"\b(execute|os\.execute|perform|chain)\b", pg), "")
    ck("TB4", "THE PAGE WRITES NOTHING ITSELF and unpacks nothing: no write, delete, writeseq, openseq, matwrite, no ospath with OS$DELETE or OS$CHOWN, and an archive is only ever asked for its MANIFEST (never CREATE or EXTRACT)",
       not re.search(r"\b(write|writeseq|writeseqf|writev|writeu|delete|deleteseq|openseq|matwrite|matwriteu|overwrite|append)\b", pg) and not re.search(r"OS\$(DELETE|CHOWN|MKDIR|MKPATH|UNIQUE|CD)", pg)
       and set(re.findall(r"call !acc_archive\('([A-Z]+)'", pg)) == {"MANIFEST"} and set(re.findall(r"call !acc_os_bakdir\('([A-Z]+)'", pg)) == {"GET"}
       and set(re.findall(r"call !acc_hold\((\w+\$?\w*)", pg)) == {"ACCBAK$CHECK"}, "")
    ca = block(pg, "check.alone")
    ck("TB5", "WHILE ANOTHER SESSION IS SIGNED ON the page shows no box: B, A and R each run check.alone FIRST (before anything else, even the directory test), and check.alone reads the hold with CHECK only and returns on any other session",
       "call !acc_hold(ACCBAK$CHECK, others, hold.err)" in ca and "others_ok = 0" in ca and "dcount(others, @fm) > 0" in ca
       and all(0 < block(pg, lb).find("gosub check.alone") < block(pg, lb).find("if not(others_ok) then return") < min([x for x in (block(pg, lb).find("sent ="), block(pg, lb).find("screen ask")) if x >= 0] or [10 ** 9])
               for lb in ("do.backup.all", "do.backup.some", "do.restore")), ca[:200])
    ba = block(pg, "do.backup.all")
    bs = block(pg, "do.backup.some")
    ck("TB6", "B sends exactly 'backup.account all' and only when a directory is saved; A asks for the names, checks every name against a-z, 0-9, dot, dash and underscore (up to 20) BEFORE the sentence, and sends 'backup.account ' + the names",
       ba.count("sent = ") == 1 and "sent = 'backup.account all'" in ba and 0 < ba.find("if bdir = '' then") < ba.find("sent = ") and bs.count("sent = ") == 1 and "sent = 'backup.account ' : names.in" in bs
       and "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-'" in bs and "if not(ok) or dcount(names.in, ' ') > 20 then" in bs and 0 < bs.find("index(good, wd[q, 1], 1) = 0") < bs.find("sent = ") and 0 < bs.find("if bdir = '' then") < bs.find("screen ask"), bs[:200])
    rs = block(pg, "do.restore")
    ck("TB7", "R restores only the archive under the cursor, every account it holds, with no.query given because the box has asked; the manifest is read first, the accounts come from its [account lines, every one must be registered "
       "(the register is read, a missing one stops the command with the names) BEFORE the sentence, and the box wants the word RESTORE typed",
       rs.count("sent = ") == 1 and "sent = 'restore.account ' : anm<ci> : ' all no.query'" in rs and "typed = 'RESTORE'" in rs
       and 0 < rs.find("call !acc_archive('MANIFEST'") < rs.find("[account") < rs.find("openpath @sdsys : @ds : 'accounts' to reg.f") < rs.find("if missing # '' then") < rs.find("sent = ") < rs.find("typed = 'RESTORE'")
       and "if index(@fm : regids : @fm, @fm : accts<k> : @fm, 1) = 0 then missing<-1> = accts<k>" in rs and "readnext rid from 9 else exit" in rs, rs[:200])
    ds = block(pg, "do.directory")
    ck("TB8", "D sends 'set.backup.directory ' + a path that is absolute, has no space and is at most 200 characters, tested BEFORE the sentence",
       ds.count("sent = ") == 1 and "sent = 'set.backup.directory ' : nd" in ds and "nd[1, 1] # '/'" in ds and "len(nd) > 200" in ds and "index(nd, ' ', 1) > 0" in ds and 0 < ds.find("nd[1, 1] # '/'") < ds.find("sent = "), ds[:200])
    cr = block(pg, "confirm.and.run")
    ck("TB9", "after a command the directory, the archives and the sessions are read again, the screen is drawn again, and the status line carries the verb's own last line (or the routine's refusal)",
       re.search(r"call \$tk_runx\(allow, sent, out, stat, err\)\s*\n\s*gosub read\.all\s*\n\s*gosub draw\.all", cr) is not None and "lastl = trim(out<k>)" in cr and "msg = err" in cr and "msg = cmsg" in cr, cr[:200])
    ra = block(pg, "read.archives")
    ck("TB10", "the archives are the files whose names begin SD- and end .zip, newest first by the time in the name (the 15 characters before .zip, sorted descending), each with its size and its manifest facts; a manifest that cannot be read is shown as ?",
       "nm[1, 3] = 'SD-' and nm[len(nm) - 3, 4] = '.zip'" in ra and "st = nm[len(nm) - 18, 15]" in ra and "locate st in stamps<1> by 'DL' setting p else null" in ra and "ospath(bdir : @ds : nm, OS$INFO)" in ra
       and "aacc<nark> = '?' ; aprod<nark> = '?'" in ra and "if merr = '' then" in ra, ra[:200])
    acts = sorted(set(re.findall(r"call \$tk_keys\('add', keys, '[^']+', '[^']+', '([a-z]+)'", pg)))
    ck("TB11", "the key table has exactly: help, backupall, backupsome, restore, directory, refresh, quit; the dispatch has B, A, R, D, F1/?, F5 and Ctrl-Q",
       acts == sorted(["help", "backupall", "backupsome", "restore", "directory", "refresh", "quit"]) and all(("case nm = '%s'" % k) in pg for k in ("b", "a", "r", "d", "f5", "ctrl-q")) and "case nm = 'f1' or nm = '?'" in pg, " ".join(acts))
    ck("TB12", "the page waits for a key with no timeout (nothing here changes by itself) and reads again only when it opens, on F5 and after a command",
       "screen key returning nm" in pg and "timeout" not in pg and pg.count("gosub read.all") == 3, "read.all x%d" % pg.count("gosub read.all"))
    ck("TB13", "the page has a [?] and F1, ? and a click show tool.backups.page, whose record exists with a title, the account maintenance page of the administrator guide (which has a section on tool.backups) and a body",
       pg.count("'tool.backups.page'") == 2 and "call $tk_help('mark', mk.x, mk.y, 0, 0)" in pg and "call $tk_help('hit', mev, mk.x, mk.y, hit.m)" in pg and raw["help"].split("\n")[0].strip() != ""
       and raw["help"].split("\n")[1].strip() == "01a-account-maintenance" and raw["help"].split("\n")[2].strip() != "" and "## Backups and restores on one screen: `tool.backups`" in raw["doc"], "")
    dl = block(pg, "draw.all")
    dsl = block(pg, "draw.list")
    dd = block(pg, "draw.detail")
    ld = block(pg, "lay.declare")
    lg = block(pg, "lay.get")
    ck("TB14", "the layout is the service's (S.88 L2): three panes declared at the 140 by 43 sizes (rows 1-6, 7-26, 27-39: 138 by 6, 138 by 20 stretching, 138 by 13), the boxes drawn at the panes' rectangles, the top text 6 narrower than the box's text so the [?] is clear, "
             "the header under the list's border, the rows counted from the pane (VA = list height - 3, 17 at 140 by 43; DV = detail height - 2, 11; the 'more accounts' line on the last of them and counted from them), every text as wide as the box's text (tw = width - 4, 134)",
       "'top' : @vm : 1 : @vm : 1 : @vm : 6 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'" in ld and "'list' : @vm : 2 : @vm : 1 : @vm : 20 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'" in ld
       and "'detail' : @vm : 3 : @vm : 1 : @vm : 13 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'" in ld and "call $tk_layout('declare', ctx, d, lay.err)" in ld
       and "screen box at top.x,top.y size top.w,top.h" in dl and "screen box at lst.x,lst.y size lst.w,lst.h" in dl and "screen box at det.x,det.y size det.w,det.h" in dl
       and "VA = lst.h - 3" in lg and "DV = det.h - 2" in lg and "tw = lst.w - 4" in lg and "mk.x = top.x + top.w - 5" in lg and "mk.y = top.y + 1" in lg
       and "attr 'bold' width tw - 6" in block(pg, "draw.top") and "at tx,lst.y + 1 attr 'header'" in dsl and "at tx,lst.y + 1 + r attr rat width tw" in dsl and "for r = 1 to DV" in dd and "at tx,det.y + r width tw" in dd
       and "if dcount(lines, @fm) > DV then" in dd and "na - (DV - 3)" in dd and "at tx,det.y + DV width tw" in dd
       and "call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get" in pg and re.search(r"\b(134|138|136|17)\b", re.sub(r"(?m)^   d<\d> = .*$", "", pg)) is None, "")
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if old not in r[key]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (key, old[:60]))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


def setkey(key, val):
    def f(raw):
        r = dict(raw)
        r[key] = val
        return r
    return f


MUTANTS = [
    ("the page is opened for anyone", "TB2", sub("page", "call $tk_open('tool.backups', 'admin', ctx, err)", "call $tk_open('tool.backups', '', ctx, err)")),
    ("the page reads before it opens the base", "TB2", sub("page", "   call $tk_open('tool.backups', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n", "   call !acc_os_bakdir('GET', bdir0, bderr0)\n   call $tk_open('tool.backups', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n")),
    ("an ordinary account gets the verb", "TB1", setkey("newvoc_has", "1")),
    ("the page may run another command", "TB3", sub("page", "allow = 'backup.account restore.account set.backup.directory'", "allow = 'backup.account restore.account set.backup.directory delete.account'")),
    ("the page runs a command with the plain routine", "TB3", sub("page", "call $tk_runx(allow, sent, out, stat, err)", "call $tk_run(allow, sent, out, stat, err)")),
    ("the box is skipped", "TB3", sub("page", "   call $tk_confirm(sent, el, typed, res, cmsg)\n   if res = 'run' then", "   res = 'run'\n   if res = 'run' then")),
    ("the page executes a command", "TB3", sub("page", "   void kernel(K$AUDIT, 'tool start app=tool.backups')\n", "   void kernel(K$AUDIT, 'tool start app=tool.backups')\n   execute 'who' capturing xx\n")),
    ("the page unpacks an archive", "TB4", sub("page", "call !acc_archive('MANIFEST', bdir : @ds : anm<ci>, '', mtext, merr)\n   if merr # '' then\n      msg = 'the manifest", "call !acc_archive('EXTRACT', bdir : @ds : anm<ci>, '', mtext, merr)\n   if merr # '' then\n      msg = 'the manifest")),
    ("the page saves the directory itself", "TB4", sub("page", "call !acc_os_bakdir('GET', bdir, bderr)", "call !acc_os_bakdir('SET', bdir, bderr)")),
    ("the page takes the hold", "TB4", sub("page", "call !acc_hold(ACCBAK$CHECK, others, hold.err)\n   if ci > nark", "call !acc_hold(ACCBAK$SET, others, hold.err)\n   if ci > nark")),
    ("the page writes a record", "TB4", sub("page", "   keys = ''\n", "   write 'x' to reg.f, 'y'\n   keys = ''\n")),
    ("check.alone does not refuse", "TB5", sub("page", "      others_ok = 0\n      msg = dcount(others, @fm)", "      msg = dcount(others, @fm)")),
    ("B does not look for other sessions", "TB5", sub("page", "do.backup.all:\n   gosub check.alone\n   if not(others_ok) then return\n", "do.backup.all:\n")),
    ("R looks for other sessions after it reads the manifest", "TB5", sub("page", "do.restore:\n   gosub check.alone\n   if not(others_ok) then return\n", "do.restore:\n")),
    ("B sends another sentence", "TB6", sub("page", "   sent = 'backup.account all'", "   sent = 'backup.account all to /tmp'")),
    ("B runs with no directory saved", "TB6", sub("page", "   if bdir = '' then\n      msg = 'no backup directory has been saved: D saves one first'\n      return\n   end\n   sent = 'backup.account all'", "   sent = 'backup.account all'")),
    ("a name with a slash is allowed", "TB6", sub("page", "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-'", "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-/'")),
    ("any number of names", "TB6", sub("page", "if not(ok) or dcount(names.in, ' ') > 20 then", "if not(ok) then")),
    ("R is run without the word typed", "TB7", sub("page", "   typed = 'RESTORE'\n", "   typed = ''\n")),
    ("R is run without no.query", "TB7", sub("page", "' all no.query'", "' all'")),
    ("R does not check the register", "TB7", sub("page", "   if missing # '' then\n      msg = 'the archive holds accounts that are not registered here", "   if 0 then\n      msg = 'the archive holds accounts that are not registered here")),
    ("R restores the first archive, not the one under the cursor", "TB7", sub("page", "sent = 'restore.account ' : anm<ci> : ' all no.query'", "sent = 'restore.account ' : anm<1> : ' all no.query'")),
    ("D takes a relative path", "TB8", sub("page", "nd[1, 1] # '/' or ", "")),
    ("D allows a space in a path", "TB8", sub("page", " or index(nd, ' ', 1) > 0 then", " then")),
    ("the state is not read again after a command", "TB9", sub("page", "      call $tk_runx(allow, sent, out, stat, err)\n      gosub read.all\n      gosub draw.all\n", "      call $tk_runx(allow, sent, out, stat, err)\n      gosub draw.all\n")),
    ("every zip is an archive", "TB10", sub("page", "if nm[1, 3] = 'SD-' and nm[len(nm) - 3, 4] = '.zip'", "if nm[len(nm) - 3, 4] = '.zip'")),
    ("the archives come oldest first", "TB10", sub("page", "locate st in stamps<1> by 'DL' setting p else null", "locate st in stamps<1> by 'AL' setting p else null")),
    ("a key is added to the table", "TB11", sub("page", "   call $tk_keys('add', keys, 'd', 'directory', 'directory', '', 1)\n", "   call $tk_keys('add', keys, 'd', 'directory', 'directory', '', 1)\n   call $tk_keys('add', keys, 'k', 'kill', 'kill', '', 1)\n")),
    ("the page reads on a timer", "TB12", sub("page", "      screen key returning nm\n", "      screen key timeout 3 returning nm\n")),
    ("the help key names a record that does not exist", "TB13", sub("page", "call $tk_help('box', 'tool.backups.page', hm, 0, 0)\n         if hm # '' then msg = hm\n      case nm = 'ctrl-q'", "call $tk_help('box', 'tool.backups.nopage', hm, 0, 0)\n         if hm # '' then msg = hm\n      case nm = 'ctrl-q'")),
    ("the help record names no page", "TB13", sub("help", "01a-account-maintenance", "")),
    ("the archives box overruns the manifest", "TB14", sub("page", "d<2> = 'list' : @vm : 2 : @vm : 1 : @vm : 20 :", "d<2> = 'list' : @vm : 2 : @vm : 1 : @vm : 21 :")),
    ("the page draws a box at a literal place again", "TB14", sub("page", "screen box at lst.x,lst.y size lst.w,lst.h title 'Archives'", "screen box at 1,7 size 138,20 title 'Archives'")),
    ("the 'more accounts' line counts from a literal again", "TB14", sub("page", "na - (DV - 3)", "na - 8")),
    ("the resize no longer asks the layout again", "TB14", sub("page", "            call $tk_layout('refresh', ctx, '', lay.chg)\n", "")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:200]))
        bad += 0 if ok else 1
    return bad


def selftest(raw):
    base = [r[0] for r in checks(raw) if not r[2]]
    if base:
        print("selftest: the unchanged tree fails %s, so a mutant's own failure cannot be told from the tree's; run the plain check first" % base)
        return 1
    holes = 0
    for name, want, mut in MUTANTS:
        try:
            m = mut(raw)
        except KeyError as exc:
            print("  [FAIL] selftest: %s  <- %s" % (name, exc))
            holes += 1
            continue
        failed = sorted({r[0] for r in checks(m) if not r[2]})
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        holes += 0 if hit else 1
    print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main(argv):
    raw = load()
    print("test-toolbackups-units: tree %s" % SDSYS)
    if not raw["page"]:
        print("test-toolbackups-units: CANNOT RUN - %s is not there" % FILES["page"])
        return 2
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-toolbackups-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
