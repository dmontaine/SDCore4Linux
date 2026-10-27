#!/usr/bin/env python3
"""test-help-units.py - the context help and the [?] button (S.75, plan .claude/plan-fullscreen-toolkit.md section 14.5), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-help-units.py
  python3 .../test-help-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  $tk_help looks a key up only after testing its characters, only in the file context.help of the shared account (found with !shared_ref asked QUIETLY, opened by
path and only read), and runs nothing but pdf <name> through $tk_run; the [?] button answers a left press on its three cells and nothing else; LOAD.HELP asks for the
administrator before it reads anything, writes only records of that one file, makes only that file and goes back to the account it began in; the shipped text under helptext has
a title, a document that exists in the documentation checkout, and is used by a program; every key a page asks for has a record; the wrapping loop lives in $tk_wrap.

***IT READS THE SOURCE AS TEXT AND DOES NOT RUN BASIC.***  That the box shows the text, F1 and a click open it, and LOAD.HELP fills the file is sandbox-help.py.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
HELP = os.path.join(SDSYS, "helptext")
DOCS = "/home/don/Projects/SDCore4LinuxDocs"                    # the documentation checkout: an absolute path, as test-pack-units.py has it
PROGS = ("tk_help", "loadhelp", "tool_menus", "tool_viewers", "tk_wrap", "tk_confirm")
MSGS = tuple(str(n) for n in list(range(11830, 11833)) + list(range(11835, 11842)))       # 11833, 11834 and 11842 are free


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def load():
    src = {n: read(os.path.join(GPL, n)) for n in PROGS}
    src["tool_ai"] = read(os.path.join(GPL, "tool_ai"))     # 23 Oct 26, S.69 step 2: the AI page asks for tool.ai.providers and tool.ai.accounts
    src["tool_gates"] = read(os.path.join(GPL, "tool_gates"))     # 24 Oct 26, S.75 A2: the gate matrix asks for tool.gates.matrix
    src["tool_mygates"] = read(os.path.join(GPL, "tool_mygates"))     # 24 Oct 26, S.75 A2: the holder's page asks for tool.gates.mine
    src["tool_sessions"] = read(os.path.join(GPL, "tool_sessions"))   # 24 Oct 26, S.75 A4: the sessions and locks page asks for tool.sessions.page
    src["tool_masters"] = read(os.path.join(GPL, "tool_masters"))     # 24 Oct 26, S.75 A7: the master files page asks for tool.masters.page
    src["tool_audit"] = read(os.path.join(GPL, "tool_audit"))         # 25 Oct 26, S.75 A5: the audit trail page asks for tool.audit.page
    src["tool_config"] = read(os.path.join(GPL, "tool_config"))       # 25 Oct 26, S.75 A6: the configuration page asks for tool.config.page
    src["tool_backups"] = read(os.path.join(GPL, "tool_backups"))     # 25 Oct 26, S.75 A8: the backups page asks for tool.backups.page
    src["tool_accounts"] = read(os.path.join(GPL, "tool_accounts"))   # 25 Oct 26, S.75 A3: the accounts page asks for tool.accounts.page
    src["tool_remote"] = read(os.path.join(GPL, "tool_remote"))       # 25 Oct 26, S.75 A9: the remote access page asks for tool.remote.page
    src["tool_files"] = read(os.path.join(GPL, "tool_files"))         # 26 Oct 26, S.75 DV1: the files page asks for tool.files.page
    src["tool_voc"] = read(os.path.join(GPL, "tool_voc"))             # 26 Oct 26, S.75 DV3: the VOC page asks for tool.voc.page
    for app in ("dict", "query", "bulk", "catalog", "test"):
        src["tool_" + app] = read(os.path.join(GPL, "tool_" + app))   # 26 Oct 26, S.75 DV2, DV4-DV7: each page asks for its tool.<app>.page
    src["msgs"] = {n: (read(os.path.join(SDSYS, "messages", n)) if os.path.exists(os.path.join(SDSYS, "messages", n)) else None) for n in MSGS}
    for name in sorted(os.listdir(HELP)):
        src["ht." + name] = read(os.path.join(HELP, name))
    return src


def arg_counts(text, name):
    """The number of arguments of each `call <name>(...)` in TEXT: top-level commas + 1, quotes and brackets respected.  A call with the wrong number stops with
    'Argument count mismatch' at run time and no other free check sees it (found 23 Oct 26: three calls of $tk_help had three arguments, not five)."""
    out = []
    for m in re.finditer(r"call\s+" + re.escape(name) + r"\(", text):
        i, depth, n, q = m.end(), 1, 1, ""
        while i < len(text) and depth:
            c = text[i]
            if q:
                q = "" if c == q else q
            elif c in "'\"":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "," and depth == 1:
                n += 1
            i += 1
        out.append(n)
    return out


def docs_pages():
    pages = set()
    for d in ("User", "Administrator", "GettingStarted"):
        p = os.path.join(DOCS, d, "markdown")
        if os.path.isdir(p):
            pages |= {f[:-3] for f in os.listdir(p) if f.endswith(".md")}
    return pages


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    th, lh, tm, tv, tw, tc = (strip(s[n]) for n in PROGS)
    hts = {k[3:]: v for k, v in s.items() if k.startswith("ht.")}

    ck("P0 the sources were found (the null case: nothing to compare passes every row)", len(th) > 1500 and len(lh) > 2000 and len(tm) > 8000 and len(tv) > 6000 and len(tw) > 300 and len(hts) >= 12, repr((len(th), len(lh), len(tm), len(tv), len(tw), len(hts))))

    i_chars = th.find("if index('abcdefghijklmnopqrstuvwxyz0123456789._-', k[ci, 1], 1) = 0 then ok = 0")
    i_ref = th.find("ans = shared_ref('context.help', 2, @true)")
    i_open = th.find("openpath ans<1> to hf then")
    ck("P1 $tk_help tests the characters of a key (a-z 0-9 . _ -, 1 to 80) BEFORE it asks where the file is, and asks QUIETLY (so SDSYS and an account whose shared.read was withdrawn are answered)",
       0 < i_chars < i_ref < i_open and "len(k) >= 1 and len(k) <= 80" in th, repr((i_chars, i_ref, i_open)))
    ck("P2 ...it only reads: one OPENPATH, no OPENSEQ, WRITE, DELETE or EXECUTE; the caller supplies a key and never a path",
       th.count("openpath") == 1 and not re.search(r"\b(openseq|writeseq|write|delete|clearfile|execute|os\.execute)\b", th) and "pdf " in th, "")
    ck("P3 ...the document it offers is a lower case name from field 2 of the record, and the ONE command it runs is pdf <name> through $tk_run, only when a document is named and the button was chosen",
       "doc = downcase(trim(rec<2>))" in th and th.count("call $tk_run(") == 1 and "call $tk_run('pdf', 'pdf ' : doc, out, st, err)" in th and "if doc # '' and bn = 1 then" in th)
    ck("P4 ...the box has a Close button the Enter key chooses (the Documentation button is the other, never the default), and a session with no terminal gets nothing",
       "btn = '&Documentation,&Close'\n      dflt = 2" in th and "btn = '&Close'\n      dflt = 1" in th and "if system(25) then return" in th)
    ck("P5 ...the [?] button answers a LEFT PRESS on its three cells and nothing else",
       "if a<1> = 'press' and a<2> = 1 and a<4> = c and a<3> >= b and a<3> <= b + 2 then d = 1" in th and "screen text '[?]' at a,b attr 'bold'" in th)
    ck("P6 ...a missing file and a missing record are answered in words (11832, 11831 and the title 11830), not with an error",
       "sysmsg(11830)" in th and "sysmsg(11831, k[1, 60])" in th and "sysmsg(11832)" in th and "have.file" in th)

    i_adm = lh.find("kernel(K$ADMINISTRATOR, -1)")
    i_dir = lh.find("entries = dir(src)")
    i_lt = lh.find("execute 'logto shared' capturing lt")
    ck("P7 LOAD.HELP asks for the administrator before it reads the directory, and enters the shared account only after that",
       0 < i_adm < i_dir < i_lt and "stop sysmsg(2001)" in lh[i_adm:i_adm + 120], repr((i_adm, i_dir, i_lt)))
    execs = re.findall(r"execute\s+('[^']*'(?:\s*:\s*\w+)?)", lh)
    ck("P8 ...the only commands it runs are LOGTO shared, LOGTO back to the account it began in (on every way out), and CREATE.FILE context.help DYNAMIC",
       sorted(set(execs)) == sorted(["'logto shared'", "'logto ' : origin", "'create.file context.help dynamic'"]) and lh.count("execute 'logto ' : origin") >= 3, repr(execs))
    ck("P9 ...a file is a record only if its name is a key (the same characters as $tk_help, the first a letter or digit) and it has a title; the record id is the file name; the only write is that record",
       "keychars = 'abcdefghijklmnopqrstuvwxyz0123456789._-'" in lh and "index('abcdefghijklmnopqrstuvwxyz0123456789', name[1, 1], 1) > 0" in lh and "if rec<1> = '' then" in lh
       and lh.count("write ") == 1 and "write rec to hf, name on error wok = @false" in lh and "if old = rec then" in lh
       and "   if not(ok) then\n      display sysmsg(11840, name, 'not a key')" in lh)
    ck("P10 ...records the administrator added under other ids are kept (the count is made, nothing is deleted)", not re.search(r"\b(delete|clearfile|del)\b", lh.replace("delete.", "")) and "n.kept" in lh)

    # the shipped text
    pages = docs_pages()
    bad_title = [k for k, v in hts.items() if not v.split("\n")[0].strip() or len(v.split("\n")[0]) > 60]
    bad_doc = [k for k, v in hts.items() if v.split("\n")[1:2] and v.split("\n")[1].strip() and not re.fullmatch(r"[a-z0-9._-]+", v.split("\n")[1].strip())]
    bad_name = [k for k in hts if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", k)]
    bad_body = [k for k, v in hts.items() if len([ln for ln in v.split("\n")[2:] if ln.strip()]) < 1 or len(v.split("\n")) > 14 or "\t" in v or any(len(ln) > 1200 for ln in v.split("\n"))]
    ck("P11 every shipped help file has a key for a name, a title of 1 to 60 characters, a document that is blank or a plain name, and one to twelve paragraphs",
       not bad_title and not bad_doc and not bad_name and not bad_body, repr((bad_title, bad_doc, bad_name, bad_body)))
    missing_docs = [k for k, v in hts.items() if len(v.split("\n")) > 1 and v.split("\n")[1].strip() and v.split("\n")[1].strip() not in pages]
    ck("P12 ...and the document each names is a page of the documentation checkout (%s, %d pages; a missing checkout fails this row, it is not skipped)" % (DOCS, len(pages)),
       len(pages) > 50 and not missing_docs, repr(missing_docs))

    # keys asked for by the pages
    tids = re.search(r"tids = ('[a-z]+'(?: : @fm : '[a-z]+')*)", tm)
    tile_ids = re.findall(r"'([a-z]+)'", tids.group(1)) if tids else []
    asked = set(re.findall(r"'(tool\.(?:menus|viewers|ai|gates|sessions|masters|audit|config|backups|accounts|remote|files|voc|dict|query|bulk|catalog|test)\.[a-z-]+)'", tm + "\n" + tv + "\n" + strip(s["tool_ai"]) + "\n" + strip(s["tool_gates"]) + "\n" + strip(s["tool_mygates"]) + "\n" + strip(s["tool_sessions"]) + "\n" + strip(s["tool_masters"]) + "\n" + strip(s["tool_audit"]) + "\n" + strip(s["tool_config"]) + "\n" + strip(s["tool_backups"]) + "\n" + strip(s["tool_accounts"]) + "\n" + strip(s["tool_remote"]) + "\n" + strip(s["tool_files"]) + "\n" + strip(s["tool_voc"]) + "".join("\n" + strip(s["tool_" + a]) for a in ("dict", "query", "bulk", "catalog", "test"))))
    if "'tool.menus.tile.' : tids<si - 2>" in tm:
        asked |= {"tool.menus.tile." + t for t in tile_ids}
    ck("P13 every key a page asks for has a shipped record (%d keys)" % len(asked), len(asked) >= 13 and not (asked - set(hts)), repr(sorted(asked - set(hts))))
    ck("P14 ...and every shipped record is asked for by a page (so text does not rot)", not (set(hts) - asked), repr(sorted(set(hts) - asked)))

    # the pages
    ck("P15 tool.menus: a [?] on each row of the Menu box (inside the row loop, which runs over nmenu rows: where the account starts, its own programs and a row for each standard tile - 17 since 26 Oct 26), one at the system default and one at the Accounts list",
       "call $tk_help('mark', 134, 1 + r, 0, 0)" in tm and "call $tk_help('mark', 66, 32, 0, 0)" in tm and "call $tk_help('mark', 66, 2, 0, 0)" in tm and "width 59\n      call $tk_help('mark'" in tm
       and "nmenu = 2 + dcount(tids, @fm)" in tm and "   for r = 1 to nmenu\n      begin case" in tm and "if pane = 2 and si < nmenu then" in tm)
    ck("P16 ...F1 and ? show the help of the selected row (the key by pane and row), and a left press on a [?] selects its row, then shows it; the loop variable of the click is not the drawing routines'",
       "case nm = 'f1' or nm = '?'" in tm and "call $tk_help('box', hk, hm, 0, 0)" in tm and "call $tk_help('hit', mev, 134, 1 + hr, hit.now)" in tm and "for hr = 1 to nmenu" in tm
       and "call $tk_help('hit', mev, 66, 32, hit.default)" in tm and "call $tk_help('hit', mev, 66, 2, hit.accounts)" in tm and "hk = 'tool.menus.tile.' : tids<si - 2>" in tm)
    ck("P17 tool.viewers: a [?] on each box, F1 and ? and a click show their help, and the page runs only set.viewer",
       "call $tk_help('mark', 66, 2, 0, 0)" in tv and "call $tk_help('mark', 134, 2, 0, 0)" in tv and "case nm = 'f1' or nm = '?'" in tv and "call $tk_help('hit', mev, 66, 2, hit.allowed)" in tv
       and "call $tk_help('hit', mev, 134, 2, hit.found)" in tv and "allow = 'set.viewer'" in tv and "tool.viewers.allowed" in tv and "tool.viewers.found" in tv)

    tg = strip(s["tool_gates"])
    ck("P17b tool.gates: a [?] at the end of the matrix box, F1 and ? and a click show its help, and the page runs only modify.account",
       "call $tk_help('mark', 134, 2, 0, 0)" in tg and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.matrix', hm, 0, 0)" in tg and "call $tk_help('hit', mev, 134, 2, hit.m)" in tg
       and "allow = 'modify.account'" in tg and tg.count("allow = ") == 1 and "tool.gates.matrix" in hts and "call $tk_wrap(lines<wi>, 134, pieces)" in tg and "rest[cut" not in tg)

    tmg = strip(s["tool_mygates"])
    ck("P17c tool.gates for an account holder: a [?] at the end of the first box, F1 and ? and a click show its help, it runs no command, and it wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in tmg and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.mine', hm, 0, 0)" in tmg and "call $tk_help('hit', mev, 134, 2, hit.m)" in tmg
       and "$tk_run" not in tmg and "tool.gates.mine" in hts and "call $tk_wrap(lines<wi>, 134, pieces)" in tmg and "rest[cut" not in tmg)

    tsn = strip(s["tool_sessions"])
    ck("P17d tool.sessions: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only logout, unlock and inhibit.login, and it wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in tsn and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.sessions.page', hm, 0, 0)" in tsn and "call $tk_help('hit', mev, 134, 2, hit.m)" in tsn
       and "allow = 'logout unlock inhibit.login'" in tsn and tsn.count("allow = ") == 1 and "tool.sessions.page" in hts and "call $tk_wrap(lines<wi>, 134, pieces)" in tsn and "rest[cut" not in tsn)

    tma = strip(s["tool_masters"])
    ck("P17e tool.masters: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only sync.masters, and it wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in tma and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.masters.page', hm, 0, 0)" in tma and "call $tk_help('hit', mev, 134, 2, hit.m)" in tma
       and "allow = 'sync.masters'" in tma and tma.count("allow = ") == 1 and "tool.masters.page" in hts and "call $tk_wrap(lines<wi>, 134, pieces)" in tma and "rest[cut" not in tma)

    tau = strip(s["tool_audit"])
    ck("P17f tool.audit: a [?] at the end of the first box, F1 and ? and a click show its help, it runs no command (no allow list, no $tk_run), and it wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in tau and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.audit.page', hm, 0, 0)" in tau and "call $tk_help('hit', mev, 134, 2, hit.m)" in tau
       and "allow = " not in tau and "$tk_run" not in tau and "tool.audit.page" in hts and "call $tk_wrap(cline, 134, pieces)" in tau and "rest[cut" not in tau)

    tcf = strip(s["tool_config"])
    ck("P17g tool.config: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only set.config (one allow list, since 26 Oct 26, S.75 A6) through $tk_run behind the confirm box, and it wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in tcf and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.config.page', hm, 0, 0)" in tcf and "call $tk_help('hit', mev, 134, 2, hit.m)" in tcf
       and "allow = 'set.config'" in tcf and tcf.count("allow = ") == 1 and "call $tk_run(allow, sent, out, stat, err)" in tcf and "call $tk_confirm(sent, el, typed, res, cmsg)" in tcf
       and "tool.config.page" in hts and "call $tk_wrap(ptext<i>, 134, pieces)" in tcf and "rest[cut" not in tcf)

    tbk = strip(s["tool_backups"])
    ck("P17h tool.backups: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only backup.account, restore.account and set.backup.directory (through $tk_runx), and the box is $tk_confirm's",
       "call $tk_help('mark', 134, 2, 0, 0)" in tbk and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.backups.page', hm, 0, 0)" in tbk and "call $tk_help('hit', mev, 134, 2, hit.m)" in tbk
       and "allow = 'backup.account restore.account set.backup.directory'" in tbk and tbk.count("allow = ") == 1 and "tool.backups.page" in hts and "call $tk_confirm(sent, el, typed, res, cmsg)" in tbk and "call $tk_runx(allow, sent, out, stat, err)" in tbk)

    tac = strip(s["tool_accounts"])
    ck("P17i tool.accounts: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only modify.account and create.account through the routines (the terminal-hand-over verbs are the box's), and wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in tac and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.accounts.page', hm, 0, 0)" in tac and "call $tk_help('hit', mev, 134, 2, hit.m)" in tac
       and "allow = 'modify.account create.account'" in tac and tac.count("allow = ") == 1 and "tool.accounts.page" in hts and "call $tk_confirm(sent, el, typed, res, cmsg)" in tac and "call $tk_wrap(ln.s, 134, pieces)" in tac and "rest[cut" not in tac)

    trm = strip(s["tool_remote"])
    ck("P17j tool.remote: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only remote.api, remote.ssh and delete.server through the routine (set.server is the verb's on the terminal), and wraps with $tk_wrap",
       "call $tk_help('mark', 134, 2, 0, 0)" in trm and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.remote.page', hm, 0, 0)" in trm and "call $tk_help('hit', mev, 134, 2, hit.m)" in trm
       and "allow = 'remote.api remote.ssh delete.server'" in trm and trm.count("allow = ") == 1 and "tool.remote.page" in hts and "call $tk_confirm(sent, el, typed, res, cmsg)" in trm and "call $tk_wrap(lines<i>, 134, pieces)" in trm and "rest[cut" not in trm)

    tfl = strip(s["tool_files"])
    ck("P17k tool.files: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only create.file, clear.file and delete.file through $tk_run and hands the terminal to analyze.file, list.index and list.triggers only, and Clear and Delete ask for the file's name typed",
       "call $tk_help('mark', 134, 2, 0, 0)" in tfl and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.files.page', hm, 0, 0)" in tfl and "call $tk_help('hit', mev, 134, 2, hit.m)" in tfl
       and "   allow = 'create.file clear.file delete.file'" in tfl and "show.allow = 'analyze.file list.index list.triggers'" in tfl and tfl.count("allow = ") == 2 and "tool.files.page" in hts
       and tfl.count("call $tk_confirm(sent, lines, fn, res, cmsg)") == 2 and "call $tk_confirm(sent, lines, '', res, cmsg)" in tfl and "call $tk_run(allow, sent, out, stat, rerr)" in tfl)

    tvc = strip(s["tool_voc"])
    ck("P17l tool.voc: a [?] at the end of the first box, F1 and ? and a click show its help, it runs only delete through $tk_run after a box that asks the entry's id typed, and hands the terminal to nothing but sed voc <id> of an id that passed the character check",
       "call $tk_help('mark', 134, 2, 0, 0)" in tvc and "call $tk_help('box', 'tool.voc.page', hm, 0, 0)" in tvc and "call $tk_help('hit', mev, 134, 2, hit.m)" in tvc
       and "   allow = 'delete'" in tvc and tvc.count("allow = ") == 1 and "tool.voc.page" in hts and tvc.count("call $tk_confirm(sent, lines, vid, res, cmsg)") == 1
       and "call $tk_run(allow, sent, out, stat, rerr)" in tvc and tvc.count("execute sent") == 1 and "sent = 'sed voc ' : vid" in tvc, "")

    tdi, tqy, tbl, tcg, tts = (strip(s["tool_" + a]) for a in ("dict", "query", "bulk", "catalog", "test"))
    ck("P17m tool.dict: a [?], F1 and ? and a click show its help (tool.dict.page); it runs delete, compile.dict, make.index, build.index and delete.index through $tk_run, hands the terminal to sed and list.index only, and has the one execute statement of that hand-over",
       "call $tk_help('mark', 134, 2, 0, 0)" in tdi and tdi.count("call $tk_help('box', 'tool.dict.page', hm, 0, 0)") == 2 and "call $tk_help('hit', mev, 134, 2, hit.m)" in tdi and "tool.dict.page" in hts
       and "   allow = 'delete compile.dict make.index build.index delete.index'" in tdi and "show.allow = 'sed list.index'" in tdi and tdi.count("allow = ") == 2 and tdi.count("execute sent") == 1 and "call $tk_run(allow, sent, out, stat, rerr)" in tdi, "")
    ck("P17n tool.query: a [?] in each of its three views, F1 and ? and a click show its help (tool.query.page); it does not use $tk_run (a query value needs the double quote $tk_run refuses) and has exactly two execute statements, the query after check.sentence and the make of its own file",
       tqy.count("call $tk_help('mark', hx, hy, 0, 0)") == 3 and tqy.count("call $tk_help('box', 'tool.query.page', hm, 0, 0)") == 2 and "call $tk_help('hit', mev, hx, hy, hit.m)" in tqy and "tool.query.page" in hts
       and "$tk_run" not in tqy and tqy.count("execute run.s trapping aborts capturing out") == 1 and tqy.count("execute qsent trapping aborts capturing mk") == 1 and len(re.findall(r"^\s*execute\b", tqy, re.M)) == 2, "")
    ck("P17o tool.bulk: a [?], F1 and ? and a click show its help (tool.bulk.page); it does not use $tk_run and has exactly two execute statements, the select of its own words and the make of its undo file",
       "call $tk_help('mark', 134, 2, 0, 0)" in tbl and tbl.count("call $tk_help('box', 'tool.bulk.page', hm, 0, 0)") == 2 and "call $tk_help('hit', mev, 134, 2, hit.m)" in tbl and "tool.bulk.page" in hts
       and "$tk_run" not in tbl and len(re.findall(r"^\s*execute\b", tbl, re.M)) == 2 and "execute ssent trapping aborts capturing sout rtnlist slv" in tbl and "execute MKUNDO trapping aborts capturing mkout" in tbl, "")
    ck("P17p tool.catalog: a [?], F1 and ? and a click show its help (tool.catalog.page); it runs only basic, catalog, decatalog and delete.catalog through $tk_run and has no execute statement",
       "call $tk_help('mark', 134, 2, 0, 0)" in tcg and tcg.count("call $tk_help('box', 'tool.catalog.page', hm, 0, 0)") == 2 and "call $tk_help('hit', mev, 134, 2, hit.m)" in tcg and "tool.catalog.page" in hts
       and "   allow = 'basic catalog decatalog delete.catalog'" in tcg and tcg.count("allow = ") == 1 and "call $tk_run(allow, sent, out, stat, rerr)" in tcg and not re.search(r"^\s*execute\b", tcg, re.M), "")
    ck("P17q tool.test: a [?], F1 and ? and a click show its help (tool.test.page); it runs only run and basic through $tk_run and has no execute statement",
       "call $tk_help('mark', 134, 2, 0, 0)" in tts and tts.count("call $tk_help('box', 'tool.test.page', hm, 0, 0)") == 3 and "call $tk_help('hit', mev, 134, 2, hit.m)" in tts and "tool.test.page" in hts
       and "   allow = 'run basic'" in tts and tts.count("allow = ") == 1 and tts.count("call $tk_run(allow, sent, out, stat, rerr)") == 2 and not re.search(r"^\s*execute\b", tts, re.M), "")

    # one wrapping loop
    ck("P18 the wrapping loop is $tk_wrap and nowhere else: $tk_confirm, tool.menus and tool.viewers call it and none has the loop (a SCREEN TEXT longer than its width is cut, not wrapped)",
       "rest[cut, 1] # ' '" in tw and "call $tk_wrap(sentence, wrapw, pieces)" in tc and "call $tk_wrap(lines<wi>, 63, pieces)" in tm and "call $tk_wrap(lines<wi>, 134, pieces)" in tv
       and "rest[cut" not in tc and "rest[cut" not in tm and "rest[cut" not in tv and "wl[wp" not in tm)
    ck("P18b $tk_confirm wraps the lines of the explanation like the sentence, an empty line stays empty, and does not append them raw (the box CUTS a long line at its edge: the tail of the ai gate's 150-character sentence never showed, 24 Oct 26)",
       "call $tk_wrap(lines<li>, wrapw, pieces)" in tc and "for li = 1 to dcount(lines, @fm)" in tc and "if lines<li> = '' then" in tc and "body := @fm : lines" not in tc)

    every =th + "\n" + lh + "\n" + tm + "\n" + tv + "\n" + tw + "\n" + tc + "\n" + tg + "\n" + tmg + "\n" + tsn + "\n" + tma + "\n" + tau + "\n" + tcf + "\n" + tbk + "\n" + tac + "\n" + trm + "\n" + tfl + "\n" + tvc + "\n" + tdi + "\n" + tqy + "\n" + tbl + "\n" + tcg + "\n" + tts
    want ={"$tk_help": (5,), "$tk_wrap": (3,), "!viewlist": (4,), "$tk_run": (5,), "$tk_confirm": (5, 6)}       # $tk_confirm is VAR.ARGS since 26 Oct 26 (faults): a sixth argument, the title, may be left out
    wrong = {k: [n for n in arg_counts(every, k) if n not in v] for k, v in want.items()}
    seen = {k: len(arg_counts(every, k)) for k in want}
    ck("P20 every call of $tk_help (5 arguments), $tk_wrap (3), !viewlist (4), $tk_run (5) and $tk_confirm (5, or 6 with a title) has the number of arguments the subroutine takes (the null case: each is called at least once)",
       not any(wrong.values()) and seen["$tk_help"] >= 12 and seen["$tk_wrap"] >= 3 and seen["!viewlist"] >= 3 and seen["$tk_run"] >= 2 and seen["$tk_confirm"] >= 2, repr((wrong, seen)))

    m = s["msgs"]
    ck("P19 messages 11830 to 11832 and 11835 to 11841 exist, each one line, none with a capital command word",
       all(m[n] and m[n].count("\n") == 1 for n in MSGS) and "load.help" in (m["11832"] or "") and "context.help" in (m["11831"] or ""), repr([n for n in MSGS if not m[n] or m[n].count("\n") != 1]))
    return rows


MUTANTS = [
    ("tk_help looks up a key before testing its characters", "tk_help", "      for ci = 1 to len(k)\n         if index('abcdefghijklmnopqrstuvwxyz0123456789._-', k[ci, 1], 1) = 0 then ok = 0\n      next ci\n", ""),
    ("tk_help allows a longer key", "tk_help", "len(k) >= 1 and len(k) <= 80", "len(k) >= 1"),
    ("tk_help asks the gates (not quiet)", "tk_help", "shared_ref('context.help', 2, @true)", "shared_ref('context.help', 2, @false)"),
    ("tk_help opens another file than the one found", "tk_help", "openpath ans<1> to hf then", "openpath 'context.help' to hf then"),
    ("tk_help writes", "tk_help", "            read rec from hf, k else rec = ''\n", "            read rec from hf, k else rec = ''\n            write rec to hf, k\n"),
    ("tk_help takes the document name as it is", "tk_help", "doc = downcase(trim(rec<2>))", "doc = rec<2>"),
    ("the Documentation button is the default", "tk_help", "      btn = '&Documentation,&Close'\n      dflt = 2", "      btn = '&Documentation,&Close'\n      dflt = 1"),
    ("the box runs a command of the record", "tk_help", "call $tk_run('pdf', 'pdf ' : doc, out, st, err)", "call $tk_run('pdf', doc, out, st, err)"),
    ("the box runs pdf with no button", "tk_help", "if doc # '' and bn = 1 then", "if doc # '' then"),
    ("a click anywhere on the row counts", "tk_help", "a<4> = c and a<3> >= b and a<3> <= b + 2", "a<4> = c"),
    ("a release counts as a press", "tk_help", "if a<1> = 'press' and a<2> = 1 and", "if a<2> = 1 and"),
    ("a session with no terminal is shown a box", "tk_help", "   if system(25) then return\n   gosub lookup", "   gosub lookup"),
    ("a missing record is an error", "tk_help", "      lines = (if have.file or not(ok) then sysmsg(11831, k[1, 60]) else sysmsg(11832))", "      lines = ''"),
    ("LOAD.HELP does not ask for the administrator", "loadhelp", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("LOAD.HELP enters another account", "loadhelp", "execute 'logto shared' capturing lt", "execute 'logto sdsys' capturing lt"),
    ("LOAD.HELP stays in the shared account", "loadhelp", "   execute 'logto ' : origin capturing lt\n   void kernel(K$AUDIT,", "   void kernel(K$AUDIT,"),
    ("LOAD.HELP runs another command", "loadhelp", "execute 'create.file context.help dynamic' capturing mk", "execute 'create.file context.help dynamic' capturing mk\n      execute 'sh' capturing mk"),
    ("LOAD.HELP loads a file whose name is not a key", "loadhelp", "   if not(ok) then\n      display sysmsg(11840, name, 'not a key')", "   if @false then\n      display sysmsg(11840, name, 'not a key')"),
    ("LOAD.HELP loads a record with no title", "loadhelp", "   if rec<1> = '' then\n", "   if @false then\n"),
    ("LOAD.HELP writes every time", "loadhelp", "      if old = rec then\n         n.same += 1\n         return\n      end\n", ""),
    ("LOAD.HELP writes another record", "loadhelp", "write rec to hf, name on error wok = @false", "write rec to hf, 'x' on error wok = @false"),
    ("LOAD.HELP deletes the administrator's records", "loadhelp", "      locate rid in shipped<1> setting p else n.kept += 1", "      locate rid in shipped<1> setting p else delete hf, rid"),
    ("tool.menus loses a [?] on the Menu rows", "tool_menus", "      call $tk_help('mark', 134, 1 + r, 0, 0)", "      null"),
    ("tool.menus calls $tk_help with too few arguments (a runtime stop in SD BASIC)", "tool_menus", "call $tk_help('mark', 66, 32, 0, 0)", "call $tk_help('mark', 66, 32)"),
    ("tool.viewers calls $tk_help with too few arguments", "tool_viewers", "hm, 0, 0)", "hm)"),
    ("tool.viewers calls $tk_wrap with too many arguments", "tool_viewers", "call $tk_wrap(lines<wi>, 134, pieces)", "call $tk_wrap(lines<wi>, 134, pieces, 0)"),
    ("tool.menus loses F1", "tool_menus", "      case nm = 'f1' or nm = '?'\n         gosub help.here\n", ""),
    ("tool.menus loses the click", "tool_menus", "call $tk_help('hit', mev, 134, 1 + hr, hit.now)", "hit.now = 0"),
    ("tool.menus uses the drawing loop variable for the click", "tool_menus", "for hr = 1 to nmenu", "for r = 1 to nmenu"),
    ("tool.menus draws a [?] for only nine rows (26 Oct 26: the Menu box has a row for each standard tile)", "tool_menus", "   for r = 1 to nmenu\n      begin case", "   for r = 1 to 9\n      begin case"),
    ("tool.menus asks for a tile's help with the wrong index", "tool_menus", "hk = 'tool.menus.tile.' : tids<si - 2>", "hk = 'tool.menus.tile.' : tids<si>"),
    ("tool.menus has its own wrapping loop again", "tool_menus", "call $tk_wrap(lines<wi>, 63, pieces)", "rest[cut"),
    ("$tk_confirm has its own wrapping loop again", "tk_confirm", "call $tk_wrap(sentence, wrapw, pieces)", "rest[cut"),
    ("$tk_confirm appends the explanation lines unwrapped again", "tk_confirm", "            call $tk_wrap(lines<li>, wrapw, pieces)\n            for p = 1 to dcount(pieces, @fm)\n               body<-1> = pieces<p>\n            next p", "            body<-1> = lines<li>"),
    ("$tk_confirm wraps the explanation at a width the box cuts", "tk_confirm", "call $tk_wrap(lines<li>, wrapw, pieces)", "call $tk_wrap(lines<li>, 200, pieces)"),
    ("$tk_wrap cuts a word at the wrong place", "tk_wrap", "rest[cut, 1] # ' '", "rest[cut, 1] # 'x'"),
    ("tool.viewers can run another command", "tool_viewers", "allow = 'set.viewer'", "allow = 'set.viewer sh'"),
    ("tool.viewers loses a [?]", "tool_viewers", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.gates loses its [?]", "tool_gates", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.masters loses its [?]", "tool_masters", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.masters calls $tk_help with too few arguments", "tool_masters", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.masters.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.masters.page', hm)"),
    ("tool.masters can run another command", "tool_masters", "allow = 'sync.masters'", "allow = 'sync.masters sh'"),
    ("tool.audit loses its [?]", "tool_audit", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.audit calls $tk_help with too few arguments", "tool_audit", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.audit.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.audit.page', hm)"),
    ("tool.audit gains a command to run", "tool_audit", "   keys = ''\n", "   allow = 'sync.masters'\n   keys = ''\n"),
    ("tool.config loses its [?]", "tool_config", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.config calls $tk_help with too few arguments", "tool_config", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.config.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.config.page', hm)"),
    ("tool.config can run another command", "tool_config", "allow = 'set.config'", "allow = 'set.config sh'"),
    ("tool.backups loses its [?]", "tool_backups", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.backups calls $tk_help with too few arguments", "tool_backups", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.backups.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.backups.page', hm)"),
    ("tool.backups can run another command", "tool_backups", "allow = 'backup.account restore.account set.backup.directory'", "allow = 'backup.account restore.account set.backup.directory sh'"),
    ("tool.accounts loses its [?]", "tool_accounts", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.accounts calls $tk_help with too few arguments", "tool_accounts", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.accounts.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.accounts.page', hm)"),
    ("tool.accounts can run another command", "tool_accounts", "allow = 'modify.account create.account'", "allow = 'modify.account create.account sh'"),
    ("tool.files loses its [?]", "tool_files", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.files can run another command", "tool_files", "   allow = 'create.file clear.file delete.file'", "   allow = 'create.file clear.file delete.file sh'"),
    ("tool.files can hand the terminal to another command", "tool_files", "show.allow = 'analyze.file list.index list.triggers'", "show.allow = 'analyze.file list.index list.triggers sh'"),
    ("tool.dict loses its [?]", "tool_dict", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.dict can run another command", "tool_dict", "   allow = 'delete compile.dict make.index build.index delete.index'", "   allow = 'delete compile.dict make.index build.index delete.index sh'"),
    ("tool.dict can hand the terminal to another command", "tool_dict", "show.allow = 'sed list.index'", "show.allow = 'sed list.index sh'"),
    ("tool.bulk loses its [?]", "tool_bulk", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.catalog can run another command", "tool_catalog", "   allow = 'basic catalog decatalog delete.catalog'", "   allow = 'basic catalog decatalog delete.catalog sh'"),
    ("tool.catalog loses its [?]", "tool_catalog", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.test can run another command", "tool_test", "   allow = 'run basic'", "   allow = 'run basic sh'"),
    ("tool.test loses its [?]", "tool_test", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.voc loses its [?]", "tool_voc", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.voc can run another command", "tool_voc", "   allow = 'delete'", "   allow = 'delete sh'"),
    ("tool.voc deletes without asking for the id", "tool_voc", "   call $tk_confirm(sent, lines, vid, res, cmsg)", "   call $tk_confirm(sent, lines, '', res, cmsg)"),
    ("tool.files deletes without asking for the name", "tool_files", "   sent = 'delete.file ' : fn : ' no.query'\n   lines = 'Deletes the file ' : fn : ', its dictionary and its VOC entry.  Nothing can bring them back; a backup can.'\n   call $tk_confirm(sent, lines, fn, res, cmsg)",
     "   sent = 'delete.file ' : fn : ' no.query'\n   lines = 'Deletes the file ' : fn : ', its dictionary and its VOC entry.  Nothing can bring them back; a backup can.'\n   call $tk_confirm(sent, lines, '', res, cmsg)"),
    ("tool.remote loses its [?]", "tool_remote", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.remote calls $tk_help with too few arguments", "tool_remote", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.remote.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.remote.page', hm)"),
    ("tool.remote can run another command", "tool_remote", "allow = 'remote.api remote.ssh delete.server'", "allow = 'remote.api remote.ssh delete.server sh'"),
    ("tool.sessions loses its [?]", "tool_sessions", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.sessions calls $tk_help with too few arguments", "tool_sessions", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.sessions.page', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.sessions.page', hm)"),
    ("tool.sessions can run another command", "tool_sessions", "allow = 'logout unlock inhibit.login'", "allow = 'logout unlock inhibit.login sh'"),
    ("tool.gates calls $tk_help with too few arguments", "tool_gates", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.matrix', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.matrix', hm)"),
    ("tool.gates loses the click", "tool_gates", "call $tk_help('hit', mev, 134, 2, hit.m)", "hit.m = 0"),
    ("tool.gates can run another command", "tool_gates", "allow = 'modify.account'", "allow = 'modify.account sh'"),
    ("tool.gates has its own wrapping loop again", "tool_gates", "call $tk_wrap(lines<wi>, 134, pieces)", "rest[cut"),
    ("the holder's gate page loses its [?]", "tool_mygates", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("the holder's gate page calls $tk_help with too few arguments", "tool_mygates", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.mine', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.mine', hm)"),
    ("the holder's gate page loses the click", "tool_mygates", "call $tk_help('hit', mev, 134, 2, hit.m)", "hit.m = 0"),
    ("the holder's gate page runs a command", "tool_mygates", "         msg = 'asked the system again'", "         call $tk_run(allow, sent, out, stat, err)\n         msg = 'asked the system again'"),
    ("a help record names a page that is not there", "ht.tool.menus.pins", "01-accounts-and-security", "no-such-page"),
    ("a help record has no title", "ht.tool.menus.pins", "Programs of the account's own\n", "\n"),
    ("a help record has a tab in it", "ht.tool.menus.default", "Applies to every account", "\tApplies to every account"),
    ("a help record's document name has a slash", "ht.tool.menus.pins", "01-accounts-and-security", "../accounts"),
]


def selftest():
    s = load()
    base = [n for n, ok, _ in checks(s) if not ok]
    if base:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base), file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: the unmutated source passes; each mutation must be CAUGHT and match its text once ---")
    for name, which, old, new in MUTANTS:
        if s[which].count(old) != 1:
            print("  [FAIL] %s: the text to mutate matches %d times in %s, not once" % (name, s[which].count(old), which))
            holes += 1
            continue
        s2 = dict(s)
        s2[which] = s[which].replace(old, new)
        caught = [n for n, ok, _ in checks(s2) if not ok]
        if caught:
            print("  [pass] %s: caught by %s" % (name, ", ".join(caught[:3])))
        else:
            print("  [FAIL] %s: NOT CAUGHT by any check" % name)
            holes += 1
    print("self-test: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if not os.path.isdir(HELP):
        print("test-help-units: no helptext directory at %s" % HELP, file=sys.stderr)
        sys.exit(2)
    s = load()
    rows = checks(s)
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-help-units: %d checks, %d failed" % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
