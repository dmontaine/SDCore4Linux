#!/usr/bin/env python3
"""test-toolmasters-units.py - the master files page, TOOL.MASTERS (`gpl.bp/tool_masters`), as invariants read off the source (S.75, administrator app A7).  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolmasters-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the page's BASIC as text, with comments removed.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT A SYNC MAKES A MASTER COPY MATCH***: that is
`sandbox-tool-masters.py` (a private SD, the real sync.masters, the master files and the journal as the evidence).  What a text check is for: the properties that make the page a FRONT END
and not a second way to change the master files - it opens the base for the administrator before it reads, it asks the kernel only READING master-file operations (never sync, syncall,
syncbegin, syncend, drain, init or note), it runs ONE command, sync.masters, through the one place that runs commands and only after the box was answered Run, it builds the sentence from
the account list the kernel gave, it does not read on a timer (a check reads every master file), and it knows the seven kinds of difference the kernel reports - which are mostly ORDER and
ABSENCE, and an edit that moves one still compiles.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
FILES = {
    "page": os.path.join(GPL, "tool_masters"),
    "run": os.path.join(GPL, "tk_run"),
    "voc": os.path.join(SDSYS, "voc_template", "tool.masters"),
    "help": os.path.join(SDSYS, "helptext", "tool.masters.page"),
    "masters_c": os.path.join(SD64, "gplsrc", "masters.c"),
}
NEWVOC = os.path.join(SDSYS, "newvoc", "tool.masters")
MSGDIR = os.path.join(SDSYS, "messages")
SAFE = "abcdefghijklmnopqrstuvwxyz0123456789.-_"
READ_OPS = {"ready", "refusal", "accounts", "drain", "check", "pending", "peek"}       # drain is the first step of CHECK.MASTERS itself: it moves journal lines already written into the master copies
KINDS = {"missing", "differs", "extra", "nonwritable", "norights", "toolong", "unreadable"}


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    raw["newvoc_has"] = "1" if os.path.exists(NEWVOC) else ""
    msgs = {}
    for n in (11564, 11568, 11569, 11571, 11572, 11573, 11574, 11594, 11981):      # 26 Oct 26, F6: 11981, how many accounts have master edits switched off
        try:
            with open(os.path.join(MSGDIR, str(n)), encoding="latin-1") as f:
                msgs[n] = f.read()
        except OSError:
            msgs[n] = ""
    raw["msgs"] = repr(sorted(msgs.items()))
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
    """The text of an internal subroutine: from its label to the next label at the start of a line (or to END)."""
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
    ck("MA0", "NULL CASE: the page, the VOC entry, the help record, tk_run and the kernel source were found and are not empty (a check on nothing would pass)",
       len(pg) > 8000 and raw["voc"].strip() != "" and len(raw["help"].split("\n")) >= 5 and len(raw["run"]) > 500 and len(raw["masters_c"]) > 50000, "%d" % len(pg))
    ck("MA1", "the page is an internal program catalogued as $tool_masters, SDSYS's VOC has it as a verb for that program, and the shared VOC (newvoc) has NO tool.masters",
       re.search(r"^\$internal\s*\nprogram \$tool_masters\s*\n\$catalog \$tool_masters\b", pg, re.M) is not None and raw["voc"].split("\n")[:3] == ["V", "CA", "$tool_masters"] and raw["newvoc_has"] == "",
       repr((raw["voc"][:30], raw["newvoc_has"])))
    i_open = pg.find("call $tk_open('tool.masters', 'admin', ctx, err)")
    i_audit = pg.find("kernel(K$AUDIT, 'tool start app=tool.masters')")
    i_first = pg.find("kernel(K$MASTERS")
    ck("MA2", "it opens the toolkit's base for the ADMINISTRATOR first (a refusal is shown and the program stops), before its first master-file operation; the one audit line says it started",
       0 < i_open < i_audit < i_first and re.search(r"call \$tk_open\('tool\.masters', 'admin', ctx, err\)\s*\n\s*if err # '' then\s*\n\s*display err\s*\n\s*stop\s*\n\s*end", pg) is not None and pg.count("K$AUDIT") == 1,
       "open %s, audit %s, first read %s" % (i_open, i_audit, i_first))
    ops = set(re.findall(r"kernel\(K\$MASTERS, '([a-z]+)'", pg))
    ck("MA3", "the page asks the kernel only the operations CHECK.MASTERS and LIST.MASTER.PENDING use (ready, refusal, accounts, drain, check, pending, peek): never sync, syncall, syncbegin, syncend, init or note",
       ops == READ_OPS and "kernel(K$MASTERS, '" in pg and not re.search(r"kernel\(K\$MASTERS,\s*(?!')\S", pg), repr(sorted(ops)))
    ck("MA4", "it runs ONE command, sync.masters, through $tk_run and nowhere else: one allow list, one call of $tk_run directly after the confirm box and guarded by res = 'run'; no execute, perform, chain, write or delete",
       re.findall(r"\ballow = '([^']*)'", pg) == ["sync.masters"] and pg.count("call $tk_run(allow, sent, out, stat, err)") == 1
       and re.search(r"call \$tk_confirm\(sent, el, notyped, res, cmsg\)\s*\n\s*if res = 'run' then\s*\n\s*call \$tk_run\(allow, sent, out, stat, err\)", pg) is not None
       and not re.search(r"^\s*(?:execute|os\.execute|perform|chain|write[uv]?|delete[uv]?|matwrite[u]?|openseq|openpath|writeseq)\b", pg, re.M))
    ds = block(pg, "do.syncall")
    do = block(pg, "do.syncone")
    ck("MA5", "S sends exactly 'sync.masters' (the box says what it does, and says differently when the files are not set up); Y sends 'sync.masters ' + an account name from the kernel's list, only when the files are set up, "
       "the account is registered (not an orphan) and the name passes plain.word - in that order, before the sentence",
       ds.count("sent = ") == 1 and "sent = 'sync.masters'" in ds and "if ready then" in ds and do.count("sent = ") == 1 and "sent = 'sync.masters ' : anm<ci>" in do
       and 0 < do.find("if not(ready) then") < do.find("if aorph<ci> = 1 then") < do.find("gosub plain.word") < do.find("sent = 'sync.masters '"), do[:200])
    pw = block(pg, "plain.word")
    ck("MA6", "plain.word lets through exactly what $tk_run lets through (a-z, 0-9, dot, dash, underscore) and refuses an empty name",
       ("index('%s', word[pi, 1], 1) = 0" % SAFE) in pw and "plain = (word # '')" in pw and re.search(r"a-z, 0-9, dot, dash and underscore", raw["run"]) is not None, pw[:160])
    ra = block(pg, "read.all")
    ck("MA7", "read.all asks 'ready' first, asks 'accounts', 'drain' and 'check' only when the files are set up, drains BEFORE it checks (as CHECK.MASTERS does) and asks 'pending' AFTER 'check' (so the journal shown is what is left)",
       0 < ra.find("kernel(K$MASTERS, 'ready')") < ra.find("if ready then") < ra.find("kernel(K$MASTERS, 'accounts')") < ra.find("kernel(K$MASTERS, 'drain')") < ra.find("kernel(K$MASTERS, 'check')") < ra.find("gosub read.pending")
       and "kernel(K$MASTERS, 'pending')" in block(pg, "read.pending") and "kernel(K$MASTERS, 'pending')" not in ra and "if ready then gosub read.pending" in pg)
    ck("MA8", "the page waits for a key with no timeout (a check reads every master file and applies the journal; it is not repeated on a timer), and reads again only when it opens, on F5 and after a sync",
       re.search(r"screen key returning nm", pg) is not None and "timeout" not in pg.replace("no timeout", "") and pg.count("gosub read.all") == 3, "read.all called %d times" % pg.count("gosub read.all"))
    acts = sorted(set(re.findall(r"call \$tk_keys\('add', keys, '[^']+', '[^']+', '([a-z]+)'", pg)))
    ck("MA9", "the key table has exactly: help, syncall, syncone, journal, refresh, quit; the dispatch has S, Y and P",
       acts == sorted(["help", "syncall", "syncone", "journal", "refresh", "quit"]) and "case nm = 's'\n         gosub do.syncall" in pg and "case nm = 'y'\n         gosub do.syncone" in pg and "case nm = 'p'" in pg, " ".join(acts))
    cn = block(pg, "confirm.and.run")
    ck("MA10", "after the command the lists are read again and the page is drawn again, and the status line says what the check finds now (every copy matches, n differences remain, or the files are still not set up)",
       re.search(r"call \$tk_run\(allow, sent, out, stat, err\)\s*\n\s*gosub read\.all\s*\n\s*gosub draw\.all", cn) is not None and "every master copy matches its account" in cn and "difference" in cn and "still not set up" in cn)
    ck("MA11", "a row of the check for an account that is not in the kernel's list adds it to the list marked as not registered (aorph = 1), counts its differences, and the list shows it as 'not registered'",
       "aorph<pos> = 1" in block(pg, "count.row") and "acnt<pos> = acnt<pos> + 1" in block(pg, "count.row") and "st.t = 'not registered: ' : acnt<i> : ' to remove'" in block(pg, "account.line") and "aorph<i> = 0" in ra)
    kw = block(pg, "kind.words")
    kinds_page = set(re.findall(r"case kinds<i> = '([a-z]+)'", kw))
    kinds_c = set(re.findall(r'mst_row\(ck, "([a-z]+)"', raw["masters_c"]))
    ck("MA12", "the page explains every kind of difference the kernel reports and no other: %s" % " ".join(sorted(KINDS)), kinds_page == KINDS and kinds_c == KINDS, "page %s, kernel %s" % (sorted(kinds_page), sorted(kinds_c)))
    ck("MA13", "the page has a [?] and F1, ? and a click show tool.masters.page, whose record exists with a title, the master files page of the administrator guide and a body",
       pg.count("'tool.masters.page'") == 2 and "call $tk_help('mark', 134, 2, 0, 0)" in pg and "call $tk_help('hit', mev, 134, 2, hit.m)" in pg
       and raw["help"].split("\n")[0].strip() != "" and raw["help"].split("\n")[1].strip() == "19-the-master-files" and raw["help"].split("\n")[2].strip() != "")
    dl = block(pg, "draw.all")
    dsl = block(pg, "draw.list")
    drw = block(pg, "draw.row")
    ck("MA14", "the layout fits the 140 by 43 frame: three boxes (rows 1-8, 9-23, 24-39), 11 account rows at y 11-21 with the count at 22, 5 difference lines at y 25-29, 7 lines of explanation at y 31-37 and the hint at 38",
       "screen box at 1,1 size 138,8" in dl and "screen box at 1,9 size 138,15" in dl and "screen box at 1,24 size 138,16" in dl and "VA = 11" in pg and "VD = 5" in pg
       and "at 3,10 + r attr rat" in dsl and "at 3,22 attr" in dsl and "for r = 1 to 13" in drw and "at 3,30 + r width 134" in drw and "at 3,38 attr" in drw and "for r = 1 to 7" in drw)
    mm = {int(k): v for k, v in re.findall(r"\((\d+), '([^']*)'\)", raw["msgs"])}
    arity = {}
    for m in re.finditer(r"sysmsg\((\d+)((?:, [^()]+?)*)\)", pg):
        arity[int(m.group(1))] = max(arity.get(int(m.group(1)), 0), len([a for a in m.group(2).split(",") if a.strip()]))
    ok_msgs = bool(arity) and all(mm.get(n, "") != "" and max([int(x) for x in re.findall(r"%(\d)", mm[n])] or [0]) <= a for n, a in arity.items())
    ck("MA15", "every message the page prints exists and the page gives it as many arguments as it has %%n places: %s" % (" ".join(str(n) for n in sorted(arity)),), ok_msgs and set(arity) == {11564, 11568, 11569, 11571, 11572, 11573, 11574, 11594, 11981}, repr(arity))
    # ---- 26 Oct 26, F6 (alternative C): the kernel's check ends with an "off" row, the number of accounts whose master edits are switched off.  It is not a difference: the page keeps it out of the
    # ---- rows, out of the list of accounts and out of every count, and says it in the top box (11981).  nonwritable and norights are worded for an account that is ON, and name the verb.
    ra_ = block(pg, "read.all")
    ds_ = block(pg, "draw.status")
    ck("MA16", "the 'off' row of the check is taken out BEFORE a row is counted for an account (it would be an account called by a number), is kept in noff, which read.all clears; the top box prints 11981 for it, "
       "only when the files are set up and it is above 0; the kernel appends that row and counts the account once (the kernel source says so); nonwritable names modify.account ... sdsys-on",
       0 < ra_.find("noff = 0") and 0 < ra_.find("if rw<1, 1> = 'off' then") < ra_.find("noff = rw<1, 2>") < ra_.find("gosub count.row")
       and "if ready and noff > 0 then s = sysmsg(11981, noff)" in ds_ and ds_.find("sysmsg(11569") < ds_.find("sysmsg(11981, noff)") and 'mst_buf_str(&out, "off");' in raw["masters_c"]
       and "modify.account " in kw and " sdsys-on puts the mode right" in kw)
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
    ("the page is opened for anyone", "MA2", sub("page", "call $tk_open('tool.masters', 'admin', ctx, err)", "call $tk_open('tool.masters', '', ctx, err)")),
    ("the page reads before it opens the base", "MA2", sub("page", "   call $tk_open('tool.masters', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n", "   ans = kernel(K$MASTERS, 'ready')\n   call $tk_open('tool.masters', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n")),
    ("a second audit line", "MA2", sub("page", "   keys = ''\n", "   void kernel(K$AUDIT, 'tool x')\n   keys = ''\n")),
    ("an ordinary account gets the verb", "MA1", setkey("newvoc_has", "1")),
    ("the page syncs by itself", "MA3", sub("page", "      ans = kernel(K$MASTERS, 'check')\n", "      ans = kernel(K$MASTERS, 'syncall')\n      ans = kernel(K$MASTERS, 'check')\n")),
    ("the page sets the master files up itself", "MA3", sub("page", "   ans = kernel(K$MASTERS, 'pending')\n", "   ans = kernel(K$MASTERS, 'init')\n   ans = kernel(K$MASTERS, 'pending')\n")),
    ("P does not ask the journal again", "MA7", sub("page", "         if ready then gosub read.pending ", "         if @false then gosub read.pending ")),
    ("the page does not drain before it checks", "MA7", sub("page", "      void kernel(K$MASTERS, 'drain') ", "      void kernel(K$MASTERS, 'ready') ")),
    ("the page may run another command", "MA4", sub("page", "allow = 'sync.masters'", "allow = 'sync.masters sh'")),
    ("the page runs the command itself", "MA4", sub("page", "      call $tk_run(allow, sent, out, stat, err)\n", "      execute sent capturing out\n")),
    ("the box is skipped", "MA4", sub("page", "   call $tk_confirm(sent, el, notyped, res, cmsg)\n   if res = 'run' then", "   res = 'run'\n   if res = 'run' then")),
    ("the page writes a file", "MA4", sub("page", "   notyped = ''", "   notyped = ''\n   write 'x' to acc.f, 'y'")),
    ("S sends another sentence", "MA5", sub("page", "   sent = 'sync.masters'\n   el = ''", "   sent = 'sync.masters x'\n   el = ''")),
    ("Y syncs an account that is not registered", "MA5", sub("page", "   if aorph<ci> = 1 then\n      msg = anm<ci> : ' is not a registered account: S removes its master copies'\n      return\n   end\n", "")),
    ("Y syncs before the files are set up", "MA5", sub("page", "   if not(ready) then\n      msg = 'the master files are not set up: S sets them up'\n      return\n   end\n", "")),
    ("Y skips the safe-word test", "MA5", sub("page", "   word = anm<ci>\n   gosub plain.word\n   if not(plain) then", "   word = anm<ci>\n   plain = 1\n   if not(plain) then")),
    ("the safe-word test lets a space through", "MA6", sub("page", "abcdefghijklmnopqrstuvwxyz0123456789.-_", "abcdefghijklmnopqrstuvwxyz0123456789.-_ ")),
    ("an empty name is a word", "MA6", sub("page", "plain = (word # '')", "plain = 1")),
    ("the journal is read before the check", "MA7", sub("page", "      ans = kernel(K$MASTERS, 'accounts')", "      ans = kernel(K$MASTERS, 'pending')\n      ans = kernel(K$MASTERS, 'accounts')")),
    ("the check is asked when the files are not set up", "MA7", sub("page", "   if ready then\n      ans = kernel(K$MASTERS, 'accounts')", "   ans = kernel(K$MASTERS, 'check')\n   if ready then\n      ans = kernel(K$MASTERS, 'accounts')")),
    ("the page reads on a timer", "MA8", sub("page", "      screen key returning nm\n", "      screen key timeout 3 returning nm\n")),
    ("a key logs out of nothing but syncs", "MA9", sub("page", "call $tk_keys('add', keys, 'p', 'journal', 'journal', '', 1)", "call $tk_keys('add', keys, 'p', 'journal', 'journal', '', 1)\n   call $tk_keys('add', keys, 'a', 'all', 'all', '', 1)")),
    ("the page shows its old state after a sync", "MA10", sub("page", "      call $tk_run(allow, sent, out, stat, err)\n      gosub read.all\n      gosub draw.all\n", "      call $tk_run(allow, sent, out, stat, err)\n      gosub draw.all\n")),
    ("an account not in the list is not added", "MA11", sub("page", "      aorph<pos> = 1\n", "      aorph<pos> = 0\n")),
    ("a kind of difference is not explained", "MA12", sub("page", "      case kinds<i> = 'toolong'\n", "      case kinds<i> = 'tooshort'\n")),
    ("the help key names a record that does not exist", "MA13", sub("page", "call $tk_help('box', 'tool.masters.page', hm, 0, 0)\n         if hm # '' then msg = hm\n      case nm = 'f5'", "call $tk_help('box', 'tool.masters.nopage', hm, 0, 0)\n         if hm # '' then msg = hm\n      case nm = 'f5'")),
    ("the help record names no page", "MA13", sub("help", "19-the-master-files", "")),
    ("the accounts box overruns the explanation", "MA14", sub("page", "screen box at 1,9 size 138,15 title 'Accounts'", "screen box at 1,9 size 138,16 title 'Accounts'")),
    ("a message is given too few arguments", "MA15", sub("page", "sysmsg(11571, pend.bytes, pend.lines)", "sysmsg(11571, pend.bytes)")),
]
M_F6C = len(MUTANTS)          # 26 Oct 26, F6 (alternative C): the first of its mutants, for `--selftest --from=N`
MUTANTS += [
    ("the off row is counted as an account", "MA16", sub("page", "               if rw<1, 1> = 'off' then\n", "               if @false then\n")),
    ("the top box never says how many accounts are off", "MA16", sub("page", "   if ready and noff > 0 then s = sysmsg(11981, noff)", "   if ready and noff > 0 then s = ''")),
    ("the count is not cleared when the page reads again", "MA16", sub("page", "   nd = 0 ; ncheck = 0 ; noff = 0 ; pend.bytes = 0", "   nd = 0 ; ncheck = 0 ; pend.bytes = 0")),
    ("nonwritable names the retired verb", "MA16", sub("page", " sdsys-on puts the mode right)", " sd-elevate group-write puts the mode right)")),
    ("the off count is given too few arguments", "MA15", sub("page", "sysmsg(11981, noff)", "sysmsg(11981)")),
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
    start = 0
    for a_ in sys.argv[1:]:
        if a_.startswith("--from="):
            start = int(a_.split("=", 1)[1])
    for k_, (name, want, mut) in enumerate(MUTANTS):
        if k_ < start:
            continue
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
    print("test-toolmasters-units: tree %s" % SDSYS)
    if not raw["page"]:
        print("test-toolmasters-units: CANNOT RUN - %s is not there" % FILES["page"])
        return 2
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-toolmasters-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
