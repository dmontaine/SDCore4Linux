#!/usr/bin/env python3
"""test-runin-units.py - RUN.IN, the administrator's account-scoped run, as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-runin-units.py
  python3 .../test-runin-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.  Written 3 Nov 26 for S.96 (owner, 2 Nov 2026: mechanism C, reserved for
sdsys, a fixed command list).

***WHAT THIS IS AND WHAT IT IS NOT.*** It reads sdsys/gpl.bp/cproc (int.runin, revert.account, load.account.switches, the abort branch and the /runin/ common), the
VOC record and the messages as TEXT.  IT CANNOT SAY THE VERB REFUSES ANYBODY OR THAT THE SESSION COMES BACK: that is sandbox-runin.py.  What it holds is the order the
design depends on, which a hand edit can break unnoticed:

  the administrator is asked FIRST; the command is rebuilt from checked words and is never the typed text; the list is exactly six commands; every word is a plain word before
  the register is read; what is needed to come back is kept BEFORE anything changes and the flag is set before the first change; the account's LOGIN is not run; the way back clears
  the flag first and puts the six switches back in the order they were kept; and the abort branch puts the session back before it does anything else - because LOGTO SDSYS is
  refused for everybody, an administrator who is not put back stays in the account for the rest of the session.

11 Nov 26 dm, S.213 (R37-R49): the command word and the option words are compared with the shipped VOC before anything is kept (A); the command runs with the administrator flag
off, SH and OS.EXECUTE off whatever the record says and one edit gate on, and revert.account puts the gates back first and the flag last (B); BCOMP refuses $execute, and an
include file or dictionary outside the account, while ri.active is set (C).  bcomp is read as well.  --selftest --from=s213 runs that sitting's mutants on.
Second part, the same day (R50, R51): LOGTO is refused during a run before it changes anything, and _voc_ref refuses a Q-pointer into any account but the run's
(by its register name) before check.q.hop.  _voc_ref is read as well.  --selftest --from=s213b runs that part's 10 mutants only.

***AND THE CHECKS ARE THEMSELVES CHECKED.*** --selftest makes the changes that would plausibly break the verb and requires each to be CAUGHT.
"""

import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
CPROC = os.path.join(SD64, "sdsys", "gpl.bp", "cproc")
VOCREC = os.path.join(SD64, "sdsys", "voc_template", "run.in")
NEWVOC = os.path.join(SD64, "sdsys", "newvoc")
MESSAGES = os.path.join(SD64, "sdsys", "messages")
SOLO_MESSAGES = "/home/don/Projects/SDCore4LinuxSolo/sdb_ai/sd64/sdsys/messages"
REGRESS = os.path.join(HERE, "regress.sh")
RMAP = os.path.join(HERE, "regress-map.txt")

COMMANDS = ["basic", "catalog", "decatalog", "delete.catalog", "debug", "compile.dict"]
SWITCHES = ["K$SH", "K$OS.EXEC", "K$SD.ACCOUNTS", "K$NET", "K$SHARED.READ", "K$SHARED.WRITE"]
NEW_MESSAGES = [11447, 11448, 11449, 11176, 11177, 11178, 11241, 11242]
BASIC = os.path.join(SD64, "sdsys", "gpl.bp", "basic")
PARSERH = os.path.join(SD64, "sdsys", "syscom", "parser.h")
KW_NEWVOC = os.path.join(SD64, "sdsys", "newvoc", "no.catalog")
KW_TEMPLATE = os.path.join(SD64, "sdsys", "voc_template", "no.catalog")
KW_NUMBER = 239
NOCATALOG_MESSAGE = 11245
OPARRAY = os.path.join(SD64, "gplsrc", "op_array.c")      # 2 Nov 26: op_common keeps $ / _ named commons to internal programs (R26b)
BCOMP = os.path.join(SD64, "sdsys", "gpl.bp", "bcomp")    # 11 Nov 26, S.213: $execute and files outside the account are refused in a compile RUN.IN started (R46-R48)
S213_MESSAGES = [14070, 14071, 14072, 14073]
VOCREF = os.path.join(SD64, "sdsys", "gpl.bp", "_voc_ref")    # 11 Nov 26, S.213 second part: no Q-pointer out of the run's account (R51)


def code(src):
    """[(line number, stripped code line)] with full-line comments dropped."""
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s and not s.startswith("*") and not s.startswith("!"):
            out.append((i, s))
    return out


def section(lines, start, end):
    """The code lines from the one that starts with `start` up to (not including) the one that starts with `end`."""
    a = next((n for n, s in lines if s.startswith(start)), None)
    if a is None:
        return []
    b = next((n for n, s in lines if n > a and s.startswith(end)), None)
    return [(n, s) for n, s in lines if n >= a and (b is None or n < b)]


def first(sec, needle, after=0):
    return next((n for n, s in sec if n > after and needle in s), None)


def last(sec, needle):
    hits = [n for n, s in sec if needle in s]
    return hits[-1] if hits else None


def count(sec, needle):
    return sum(1 for n, s in sec if needle in s)


def checks(src, voc_text, newvoc_names, extra=None):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    lines = code(src)
    run = section(lines, "int.runin:", "ri.plain.word:")
    plain = section(lines, "ri.plain.word:", "revert.account:")      # comments are dropped, so the banner between the two labels is not in the way
    rev = section(lines, "revert.account:", "int.if:")
    lsw = section(lines, "load.account.switches:", "int.runin:")
    logto = section(lines, "int.logto:", "load.account.switches:")
    a_n = next((n for n, s in lines if s == "abort.code = n"), None)
    b_n = next((n for n, s in lines if n and a_n and n > a_n and s == "begin case"), None)
    net = [(n, s) for n, s in lines if a_n and b_n and a_n < n < b_n]

    # ---- the VOC record and the verb list -------------------------------------------------------------------------------
    ck("R1 the VOC record is V / IN / 42, in SDSYS's template only (no newvoc record: an ordinary account has no verb)",
       voc_text == "V\nIN\n42\n" and "run.in" not in newvoc_names, "record %r, newvoc has it: %s" % (voc_text, "run.in" in newvoc_names))
    m = re.search(r"on voc\.rec<3> gosub(.*?)\n\s*case dispatch\.mode = \"OS\"", src, re.S)
    labels = []
    if m:
        for part in m.group(1).splitlines():
            t = re.sub(r";\*.*", "", part).strip().rstrip(",").split()
            if t:
                labels.append(t[0])
    ck("R2 int.runin is the 42nd internal verb, after int.logmsg (41)", len(labels) == 42 and labels[40] == "int.logmsg" and labels[41] == "int.runin",
       "%d labels, 41st %s, 42nd %s" % (len(labels), labels[40] if len(labels) > 40 else None, labels[41] if len(labels) > 41 else None))
    ck("R3 int.logto still is the 17th (the numbers of the others did not move)", len(labels) > 16 and labels[16] == "int.logto")

    # ---- the order inside int.runin -------------------------------------------------------------------------------------
    A = {
        "admin": first(run, "if not(kernel(K$ADMINISTRATOR, -1)) then"),
        "nest": first(run, "if ri.active then"),
        "parser": first(run, "call @parser(PARSER$GET.REST"),
        "loop": first(run, "for ri.w = 1 to ri.nwords"),
        "nocat": first(run, "if ri.cmd = 'basic' then ri.sentence := ' no.catalog'"),
        "bad": first(run, "if ri.bad # '' then"),
        "plain": first(run, "gosub ri.plain.word"),
        "sdsys": first(run, "if ri.acct = 'sdsys' then"),
        "register": first(run, "openpath @sdsys:@ds:'accounts' to acc.f"),
        "save_path": first(run, "ri.path = ospath('', os$cwd)"),
        "save_sw": first(run, "ri.sw = kernel(K$SH, -1)"),
        "active": first(run, "ri.active = 1"),
        "begin": first(run, "'run.in begin account='"),
        "cd": first(run, "if not(ospath(acc.rec, OS$CD)) then"),
        "switches": first(run, "gosub load.account.switches"),
        "filechk": first(run, "if ri.n.names = 2 then"),
        "proc": first(run, "gosub proc.sentence"),
        "revert": last(run, "gosub revert.account"),
        "end": last(run, "'run.in end account=' : ri.acct)"),
    }
    order = ["admin", "nest", "parser", "loop", "nocat", "sdsys", "register", "save_path", "save_sw", "active", "begin", "cd", "switches", "filechk", "proc", "revert", "end"]
    missing = [k for k in order if A[k] is None]
    ck("R4 every anchor of int.runin is there", not missing, "missing " + ", ".join(missing))
    ck("R5 the order: administrator first, then the nest test, the words, the register, THEN what is kept to come back, THEN the flag, THEN the first change",
       not missing and all(A[order[i]] < A[order[i + 1]] for i in range(len(order) - 1)),
       " ".join("%s=%s" % (k, A[k]) for k in order))
    ck("R6 the plain-word check runs inside the word loop, before the register is read",
       A["loop"] is not None and A["plain"] is not None and A["register"] is not None and A["loop"] < A["plain"] < A["register"])
    cds = [n for n, s in run if "OS$CD" in s]
    ck("R7 nothing changes the directory before the flag is set (every OS$CD in the verb is after ri.active = 1)",
       A["active"] is not None and cds and all(n > A["active"] for n in cds), "cd lines %s active %s" % (cds, A["active"]))

    # ---- the list, the sentence and the words ---------------------------------------------------------------------------
    cases = re.findall(r"case ri\.cmd = '([^']+)'", "\n".join(s for n, s in run))
    ck("R8 the commands are exactly basic, catalog, decatalog, delete.catalog, debug and compile.dict", sorted(cases) == sorted(COMMANDS), "found %s" % cases)
    assigns = [s for n, s in run if re.match(r"new\.sentence\s*=", s)]
    ck("R9 the only sentence the verb runs is the one built from checked words (new.sentence = ri.sentence, once)", assigns == ["new.sentence = ri.sentence"], "%s" % assigns)
    sent = re.findall(r"(ri\.sentence\s*:?=[^\n]*)", "\n".join(s for n, s in run))
    ck("R10 ri.sentence starts as the command word and grows only by checked words", sent == ["ri.sentence = ri.cmd", "ri.sentence := ' ' : ri.word", "ri.sentence := ' no.catalog'"], "%s" % sent)
    ck("R11 the verb never executes text (no execute, no ri.rest as a sentence, one proc.sentence)",
       not any(re.match(r"execute\b", s) for n, s in run) and count(run, "gosub proc.sentence") == 1 and not any("sentence" in s and "ri.rest" in s for n, s in run if re.match(r"new\.sentence", s)))
    ck("R12 the account's LOGIN and ON.LOGTO are NOT run, and no group test stands in for the administrator test",
       not any(re.search(r"LOGIN|ON\.LOGTO|is_grp_member", s) for n, s in run), "")
    opts = [o for o in re.findall(r"ri\.opts = '([^']*)'", "\n".join(s for n, s in run)) if o]
    ck("R13 the options are debugging and no.query for basic, local and no.query for catalog, local for delete.catalog, and none else",
       sorted(opts) == sorted(["debugging no.query", "local no.query", "local"]), "found %s" % opts)
    kw = re.search(r"ri\.kwords = '([^']*)'", "\n".join(s for n, s in run))
    kwords = set(kw.group(1).split()) if kw else set()
    ck("R14 the keyword list holds every option word and the words the verbs read as options", {"local", "global", "pcode", "no.query", "no.catalog", "debugging"} <= kwords, "%s" % sorted(kwords))
    ptxt = "\n".join(s for n, s in plain)
    ck("R15 a plain word: a letter or digit first, then a-z 0-9 . _ - only, at most 64, and not a keyword",
       "index('abcdefghijklmnopqrstuvwxyz0123456789', ri.word[1, 1], 1)" in ptxt and "index('abcdefghijklmnopqrstuvwxyz0123456789._-', ri.word[ri.i, 1], 1)" in ptxt
       and "len(ri.word) > 64" in ptxt and "ri.kwords" in ptxt)
    ck("R16 the account is checked as a word and refused when it is sdsys, and the register record gives the path (never the typed text)",
       "acc.rec = parse.pathname.tokens(acc.record<ACC$PATH>)" in "\n".join(s for n, s in run) and "if acc.record<ACC$PATH> = '' then" in "\n".join(s for n, s in run))

    # ---- the way back ---------------------------------------------------------------------------------------------------
    ck("R17 revert.account clears the flag FIRST (a failure below it must not run it twice)", bool(rev) and rev[0][1] == "revert.account:" and rev[1][1] == "ri.active = 0",
       "%s" % (rev[:2],))
    rtxt = "\n".join(s for n, s in rev)
    all_r = re.findall(r"void kernel\((K\$[A-Z.]+),\s+ri\.sw<(\d+)>\)", rtxt)
    order_r = [(k, i) for k, i in all_r if k in SWITCHES]
    ck("R18 it restores the six switches from ri.sw in the order they were kept", [k for k, i in order_r] == SWITCHES and [i for k, i in order_r] == list("123456"), "%s" % order_r)
    kept = re.findall(r"kernel\((K\$[A-Z.]+), -1\)", next((s for n, s in run if s.startswith("ri.sw = ")), ""))
    ck("R19 ... and that is the order int.runin kept them in", kept == SWITCHES, "%s" % kept)
    loaded = re.findall(r"void kernel\((K\$[A-Z.]+),", "\n".join(s for n, s in lsw))
    ck("R20 load.account.switches sets the same six, once, in the same order", loaded == SWITCHES, "%s" % loaded)
    ck("R21 the way back is fatal when it cannot get back (return to abort.cproc twice) and puts the name, the VOC, the catalogue and the object cache back",
       count(rev, "return to abort.cproc") == 2 and "void kernel(K$SET.ACCOUNT, who)" in rtxt and "voc = new.voc ; new.voc = 0" in rtxt and "gosub find.private.catalogue" in rtxt
       and "kernel(K$INVALIDATE.OBJECT, 0)" in rtxt and "account.path = ri.account.path" in rtxt and "who = ri.who" in rtxt)
    ltxt = "\n".join(s for n, s in logto)
    ck("R22 int.logto uses load.account.switches (once) and no longer carries the six statements itself",
       ltxt.count("gosub load.account.switches") == 1 and not re.search(r"void kernel\(K\$(SH|OS\.EXEC|SD\.ACCOUNTS|NET|SHARED\.READ|SHARED\.WRITE),", ltxt))

    # ---- the safety net -------------------------------------------------------------------------------------------------
    ntxt = "\n".join(s for n, s in net)
    ck("R23 the abort branch puts the session back BEFORE the case on the abort cause (the block sits between 'abort.code = n' and 'begin case')",
       bool(net) and "if ri.active then" in ntxt and "gosub revert.account" in ntxt, "%d lines between" % len(net))
    ck("R24 ... says so (11242 with the account) and audits it as run.in revert ... reason=abort",
       "display sysmsg(11242, ri.account)" in ntxt and "'run.in revert account=' : ri.account : ' reason=abort'" in ntxt)
    ck("R25 the test is the flag and nothing else, and it comes before the first 'case' of the branch",
       a_n is not None and b_n is not None and next((n for n, s in lines if n > a_n and s.startswith("case ")), 10 ** 9) > b_n)
    commons = [s for n, s in lines if re.match(r"common /\$?runin/", s)]
    ck("R26 the common /$runin/ is declared once, ri.active first, with everything the way back needs - and its name starts with $ (2 Nov 26: a plain /runin/ "
       "could be declared by any program, which then set ri.sw and ABORTed into revert.account with every gate on)",
       len(commons) == 1 and re.match(r"common /\$runin/ ri\.active,", commons[0]) and all(v in commons[0] for v in ("ri.path", "ri.account.path", "ri.who", "ri.sw", "ri.account")),
       "%s" % commons)
    opa = (extra or {}).get("op_array.c", "")
    body = opa[opa.find("void op_common()"):opa.find("void op_delcom()")]
    chk = body.find("k_error(sysmsg(11598))")
    ck("R26b the kernel refuses a $ or _ named common to a program that is not internal (op_common, message 11598), before the block is looked up or made",
       chk > 0 and re.search(r"\(\*block_name == '\$'\)\s*\|\|\s*\(\*block_name == '_'\)", body[:chk]) is not None and "!(process.program.flags & HDR_INTERNAL)" in body[:chk]
       and chk < body.find("process.named_common") and os.path.exists(os.path.join(MESSAGES, "11598")), "check at %d" % chk)

    # ---- audit and messages ---------------------------------------------------------------------------------------------
    audits = re.findall(r"K\$AUDIT, '([^']*)'", "\n".join(s for n, s in run + rev + net))
    bad = [a for a in audits if not a.startswith("run.in ") and not a.startswith("logto revert account=") or re.search(r"[A-Z]", a.split("=")[0])]
    ck("R27 every audit line the verb writes starts with run.in (or LOGTO's own revert line) and has no capital before its first =", audits and not bad, "%s" % bad)
    cited = sorted(set(int(x) for x in re.findall(r"sysmsg\((\d+)", "\n".join(s for n, s in run + rev + net))))
    absent = [n for n in cited if not os.path.isfile(os.path.join(MESSAGES, str(n)))]
    ck("R28 every message the verb cites is a file", cited and not absent, "cited %s, absent %s" % (cited, absent))
    ck("R29 the eight new messages exist and are cited", all(os.path.isfile(os.path.join(MESSAGES, str(n))) for n in NEW_MESSAGES) and all(n in cited for n in NEW_MESSAGES if n != 11242) and 11242 in cited,
       "cited %s" % cited)
    if os.path.isdir(SOLO_MESSAGES):
        clash = [n for n in NEW_MESSAGES if os.path.exists(os.path.join(SOLO_MESSAGES, str(n)))]
        ck("R30 none of the eight numbers (nor 11245) is used in Solo (a later carry cannot collide)", not clash and not os.path.exists(os.path.join(SOLO_MESSAGES, str(NOCATALOG_MESSAGE))), "in Solo: %s" % clash)

    # ---- the NO.CATALOG option (owner, 3 Nov 26: "compile option"): run.in basic always gives it, basic honours it at the one place the catalogue step runs ----------
    ck("R33 no option list lets a person give no.catalog (it is added by the verb, after the typed words are checked, and only to basic)",
       not any("no.catalog" in o for o in opts) and A["nocat"] is not None and A["bad"] is not None and A["loop"] < A["bad"] < A["nocat"] < A["register"],
       "loop %s bad %s nocat %s register %s" % (A["loop"], A["bad"], A["nocat"], A["register"]))
    if extra is not None:
        bl = code(extra["basic"])
        btxt = "\n".join(s for n, s in bl)
        init = first(bl, "no.catalog = @false")
        case_ = first(bl, "case keyword = KW$NO.CATALOG")
        setit = first(bl, "no.catalog = @true", case_ or 0)
        skip = first(bl, "if catalogue.name # '' and no.catalog then")
        msg = first(bl, "display sysmsg(11245, record.name)", skip or 0)
        els = first(bl, "end else if catalogue.name # '' then", msg or 0)
        exe = first(bl, "execute cat.cmd", els or 0)
        ck("R34 basic reads the option (KW$NO.CATALOG sets no.catalog, which starts false) and the catalogue step is run only in the branch where it is not set: the skip, its message, THEN the old test, "
           "and the one 'execute cat.cmd' after them",
           all(x is not None for x in (init, case_, setit, skip, msg, els, exe)) and init < case_ < setit < skip < msg < els < exe and btxt.count("execute cat.cmd") == 1,
           "init %s case %s set %s skip %s msg %s else %s exec %s" % (init, case_, setit, skip, msg, els, exe))
        ph = [(m.group(1), m.group(2)) for m in re.finditer(r"^\$define\s+(KW\$[A-Z.]+)\s+(\d+)", extra["parser.h"], re.M)]
        knums = [n for k, n in ph if k == "KW$NO.CATALOG"]
        ck("R35 the keyword is the same number in parser.h, in the newvoc record (K description, then the number) and in the template record (K, the number), and no other KW$ has it",
           knums == [str(KW_NUMBER)] and sum(1 for k, n in ph if n == str(KW_NUMBER)) == 1
           and extra["kw.newvoc"].split("\n")[:2][1:] == [str(KW_NUMBER)] and extra["kw.newvoc"].upper().startswith("K")
           and extra["kw.template"] == "K\n%d\n" % KW_NUMBER, "parser.h %s" % knums)
        mp = os.path.join(MESSAGES, str(NOCATALOG_MESSAGE))
        mt = open(mp, encoding="utf-8").read() if os.path.isfile(mp) else ""
        ck("R36 message 11245 exists, takes the program name and names the option", "%1" in mt and "no.catalog" in mt, repr(mt))

    # ---- 11 Nov 26, S.213: SD's own words (A), not the administrator (B), no command at compile time (C) -------------------------------------------------
    own = section(lines, "ri.own.words:", "ri.narrow:")
    nar = section(lines, "ri.narrow:", "ri.plain.word:")
    otxt = "\n".join(s for n, s in own)
    runtxt = "\n".join(s for n, s in run)
    ow = first(run, "gosub ri.own.words")
    ow_ref = first(run, "display sysmsg(14070, ri.bad[1, 40], ri.acct)", ow or 0)
    ow_aud = first(run, "'run.in refused account=' : ri.acct : ' word=' : ri.bad[1, 40] : ' reason=' : ri.why", ow or 0)
    ow_ret = first(run, "return", ow_aud or 0)
    ck("R37 (A) the words are asked after the register is read and BEFORE anything is kept or changed; a failure says so (14070, the word and the account), is audited "
       "with word= and reason=, and returns before the flag is set",
       None not in (ow, ow_ref, ow_aud, ow_ret, A["register"], A["save_path"], A["active"]) and A["register"] < ow < ow_ref < ow_aud < ow_ret < A["save_path"] < A["active"]
       and count(run, "gosub ri.own.words") == 1, "own %s refuse %s audit %s return %s save %s" % (ow, ow_ref, ow_aud, ow_ret, A["save_path"]))
    ck("R38 (A) ri.own.words reads the SHIPPED record (NEWVOC of the system directory) and the ACCOUNT's VOC by the register's path, for the command word and every word after "
       "the names, and compares the type letter and every field after the first; a file it cannot open and a record that is missing are refusals",
       "openpath @sdsys:@ds:'newvoc' to ri.nv.f then ri.nv.open = @true" in otxt and "openpath acc.rec:@ds:'voc' to ri.av.f then ri.av.open = @true" in otxt
       and "if (ri.w = 1 or ri.w > 1 + ri.n.names) and ri.bad = '' then" in otxt and "ri.word = field(ri.sentence, ' ', ri.w)" in otxt
       and "read ri.own from ri.nv.f, ri.word else ri.own = ''" in otxt and "read ri.vrec from ri.av.f, ri.word else ri.vrec = ''" in otxt
       and "case upcase(ri.vrec[1, 1]) # upcase(ri.own[1, 1])" in otxt and "case field(ri.vrec, @fm, 2, 9999) # field(ri.own, @fm, 2, 9999)" in otxt
       and "case ri.own = ''" in otxt and "case ri.vrec = ''" in otxt and "case not(ri.nv.open)" in otxt and "case not(ri.av.open)" in otxt
       and otxt.count("ri.bad = ri.") == 6 and not re.search(r"\bexecute\b|proc\.sentence|write ", otxt), "")
    kept = next((n for n, s in run if s.startswith("ri.sw<7> = kernel(K$VOC.EDIT, -1) ; ri.sw<8> = kernel(K$BP.EDIT, -1) ; ri.sw<9> = kernel(K$DICT.EDIT, -1)")), None)
    kept10 = next((n for n, s in run if s.startswith("ri.sw<10> = kernel(K$ADMINISTRATOR, -1)")), None)
    ck("R39 (B) the three edit gates and the administrator flag are kept in ri.sw<7> to ri.sw<10>, after the six and before the flag ri.active is set",
       None not in (kept, kept10, A["save_sw"], A["active"]) and A["save_sw"] < kept < kept10 < A["active"], "kept %s %s" % (kept, kept10))
    ntxt2 = [s for n, s in nar]
    ck("R40 (B) ri.narrow is exactly: voc-edit off, bp-edit on for basic / catalog / decatalog / delete.catalog only, dict-edit on for compile.dict only, SH off, OS.EXECUTE off, "
       "and the administrator flag off LAST",
       ntxt2 == ["ri.narrow:", "void kernel(K$VOC.EDIT,  0)",
                 "void kernel(K$BP.EDIT,   (ri.cmd = 'basic') or (ri.cmd = 'catalog') or (ri.cmd = 'decatalog') or (ri.cmd = 'delete.catalog'))",
                 "void kernel(K$DICT.EDIT, (ri.cmd = 'compile.dict'))", "void kernel(K$SH, 0)", "void kernel(K$OS.EXEC, 0)", "void kernel(K$ADMINISTRATOR, 0)", "return"], "%s" % ntxt2)
    idx = {n: i for i, (n, s) in enumerate(run)}
    nr = first(run, "gosub ri.narrow")
    ck("R41 (B) the flag is dropped once, on the line before the command runs (gosub ri.narrow, then gosub proc.sentence), after the account's switches were loaded",
       nr is not None and count(run, "gosub ri.narrow") == 1 and A["proc"] is not None and idx[A["proc"]] == idx[nr] + 1 and A["switches"] < nr,
       "narrow %s proc %s" % (nr, A["proc"]))
    ck("R42 (B) nothing in the verb turns the flag ON, and nothing else in CPROC turns it off: (K$ADMINISTRATOR, 0) is in ri.narrow alone, and the only other setting of it "
       "outside the sign-on block is revert.account's",
       src.count("kernel(K$ADMINISTRATOR, 0)") == 1 and "kernel(K$ADMINISTRATOR, 1)" not in runtxt and "kernel(K$ADMINISTRATOR, 1)" not in rtxt
       and src.count("kernel(K$ADMINISTRATOR, ri.sw<10>)") == 1, "")
    sh_l = next((s for n, s in lsw if s.startswith("void kernel(K$SH,")), "")
    os_l = next((s for n, s in lsw if s.startswith("void kernel(K$OS.EXEC,")), "")
    ck("R43 (B) load.account.switches never turns SH or OS.EXECUTE on while a run is in progress (not(ri.active) and ...), so the account's record is not what decides - for RUN.IN's "
       "own load and for a LOGTO executed inside the run",
       sh_l == "void kernel(K$SH,      not(ri.active) and (upcase(trim(acc.record<ACC$SH>)) = 'YES'))"
       and os_l == "void kernel(K$OS.EXEC, not(ri.active) and (upcase(trim(acc.record<ACC$OS.EXEC>)) = 'YES'))", "%r / %r" % (sh_l, os_l))
    rv = [s for n, s in rev]
    cd_i = next((i for i, s in enumerate(rv) if "OS$CD" in s), None)
    adm_i = next((i for i, s in enumerate(rv) if s.startswith("void kernel(K$ADMINISTRATOR, ri.sw<10>)")), None)
    last_sw = max([i for i, s in enumerate(rv) if re.match(r"void kernel\(K\$[A-Z.]+,\s+ri\.sw<\d+>\)", s)] or [-1])
    ck("R44 (B) the way back fails closed: the three edit gates go back right after the flag ri.active is cleared and before anything that can fail (the first OS$CD); the "
       "administrator flag is restored from ri.sw<10>, after the six switches, and is the LAST switch set",
       rv[2:5] == ["void kernel(K$VOC.EDIT,  ri.sw<7>)", "void kernel(K$BP.EDIT,   ri.sw<8>)", "void kernel(K$DICT.EDIT, ri.sw<9>)"] and cd_i is not None and cd_i > 4
       and adm_i is not None and adm_i == last_sw and adm_i > next((i for i, s in enumerate(rv) if "K$SHARED.WRITE" in s), 10 ** 9), "%s" % rv[:6])
    netl = [s for n, s in net]
    ni = netl.index("if ri.active then") if "if ri.active then" in netl else -1
    ck("R45 (B) the abort branch calls revert.account FIRST inside its test of the flag (nothing runs between), so an aborted command gets the same way back",
       ni >= 0 and len(netl) > ni + 1 and netl[ni + 1] == "gosub revert.account", "%s" % netl[ni:ni + 2])
    if extra is not None and "bcomp" in extra:
        bsrc = extra["bcomp"]
        bc = code(bsrc)
        bcom = [s for n, s in bc if re.match(r"common /\$?runin/", s)]
        ck("R46 (C) BCOMP declares the /$runin/ common exactly as CPROC does (the same names in the same order)", len(bcom) == 1 and commons == bcom, "%s / %s" % (commons, bcom))
        e_case = first(bc, 'case u.token.string = "EXECUTE"')
        e_next = first(bc, 'case u.token.string = "EXPLIST"', e_case or 0)
        ex = [s for n, s in bc if e_case and e_next and e_case < n < e_next]
        tail = ex[-6:]
        ck("R47 (C) the $execute directive: under ri.active it is a compile error (14071, gosub error) and the one 'execute token.string' of the compiler is in the ELSE of that test",
           tail == ["if ri.active then", "err.msg = sysmsg(14071) ;* $execute is refused in a compile started by run.in: it would run a command from the administrator's session",
                    "gosub error", "end else", "execute token.string", "end"] and sum(1 for n, s in bc if s.startswith("execute token.string")) == 1, "%s" % tail)
        outs = section(bc, "ri.outside:", "get.token:")
        ck("R48 (C) an include file, the $dict dictionary and a FILE statement's dictionary are each asked of ri.outside (three calls), which refuses - only under ri.active - a "
           "file that the kernel says is neither inside the account (@path) nor SD's SYSCOM",
           sum(1 for n, s in bc if s == "gosub ri.outside") == 3
           and [s for n, s in outs][:6] == ["ri.outside:", "ri.out = @false", "if ri.active then", "if not(kernel(K$PATH.IN, @path : @fm : ri.chk.path)) then",
                                             "if not(kernel(K$PATH.IN, @sdsys : @ds : 'syscom' : @fm : ri.chk.path : @ds : 'x')) then ri.out = @true", "end"]
           and bsrc.count("sysmsg(14072,") == 3 and "to dict.f" not in "\n".join(s for n, s in bc if s.startswith("open ")), "%s" % [s for n, s in outs][:6])
    # ---- 11 Nov 26, S.213 second part: no LOGTO during a run, and no Q-pointer out of the run's account --------------------------------------------------
    lg_tok = first(logto, "call @parser(PARSER$GET.TOKEN, token.type, new.account, keyword)")
    lg_act = first(logto, "if ri.active then")
    lg_msg = first(logto, "display sysmsg(14073, ri.account)")
    lg_aud = first(logto, "'run.in refused account=' : ri.account : ' target=' : downcase(new.account)[1, 40] : ' reason=logto'")
    lg_ret = first(logto, "return", lg_aud or 0)
    lg_sys = first(logto, 'if (downcase(new.account) = "sdsys") then')
    lg_first = min([n for n, s in logto if re.search(r"OS\$CD|K\$AUDIT, 'logto |gosub proc\.sentence|gosub load\.account\.switches|voc = new\.voc|K\$SET\.ACCOUNT", s)] or [10 ** 9])
    ck("R50 LOGTO is refused while a run is in progress: right after the account name is read and BEFORE the sdsys test, ON.LOGTO, any directory change, switch, "
       "VOC or audit line of LOGTO's own; it says so (14073 with the run's account), audits run.in refused ... reason=logto, and returns",
       None not in (lg_tok, lg_act, lg_msg, lg_aud, lg_ret, lg_sys) and lg_tok < lg_act < lg_msg < lg_aud < lg_ret < lg_sys < lg_first,
       "token %s active %s msg %s audit %s return %s sdsys %s first change %s" % (lg_tok, lg_act, lg_msg, lg_aud, lg_ret, lg_sys, lg_first))
    if extra is not None and "_voc_ref" in extra:
        vsrc = extra["_voc_ref"]
        vc = code(vsrc)
        vcom = [s for n, s in vc if re.match(r"common /\$?runin/", s)]
        q_reg = first(vc, "q.registered = @true")
        q_act = first(vc, "if ri.active then", q_reg or 0)
        q_test = first(vc, "if not(q.registered and downcase(q.named) = ri.account) then", q_act or 0)
        q_perm = first(vc, "set.status ER$PERM", q_test or 0)
        q_hop = first(vc, "gosub check.q.hop")
        q_open = first(vc, "openpath qpath:@ds:'voc' to qvoc else")
        ck("R51 _voc_ref declares /$runin/ as CPROC does, and in the Q branch, after the register is read and BEFORE check.q.hop and the target VOC is opened, "
           "refuses (ER$PERM) during a run any pointer whose account is not the run's account by its register name - whoever the session is",
           len(vcom) == 1 and vcom == commons and None not in (q_reg, q_act, q_test, q_perm, q_hop, q_open) and q_reg < q_act < q_test < q_perm < q_hop < q_open
           and not any("vr.admin" in s for n, s in vc if q_act <= n <= q_perm),
           "common %s register %s active %s test %s perm %s hop %s open %s" % (vcom, q_reg, q_act, q_test, q_perm, q_hop, q_open))
    texts = {}
    for num in S213_MESSAGES:
        mp = os.path.join(MESSAGES, str(num))
        texts[num] = (extra or {}).get("msg%d" % num)          # the self-test hands a changed text in
        if texts[num] is None:
            texts[num] = open(mp, encoding="utf-8").read() if os.path.isfile(mp) else ""
    ck("R49 the four messages exist: 14070 takes the word and the account and says the entry is not SD's own, 14071 names $execute and run.in, 14072 names run.in and syscom, "
       "14073 names logto and run.in and takes the account; none is used in Solo",
       "%1" in texts[14070] and "%2" in texts[14070] and "not SD's own entry in the VOC" in texts[14070] and "$execute" in texts[14071] and "run.in" in texts[14071]
       and "%1" in texts[14072] and "run.in" in texts[14072] and "syscom" in texts[14072]
       and texts[14073].startswith("logto ") and "run.in" in texts[14073] and "%1" in texts[14073]
       and not any(os.path.exists(os.path.join(SOLO_MESSAGES, str(n))) for n in S213_MESSAGES), "%r" % texts)
    return out


def sandbox_mutants_still_match(src, extra):
    """sandbox-runin.py edits the sandbox's copy of cproc or of basic at text that must occur exactly once."""
    spec = importlib.util.spec_from_file_location("sbr", os.path.join(HERE, "sandbox-runin.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    texts = {"cproc": src, "basic": extra["basic"], "bcomp": extra["bcomp"], "_voc_ref": extra["_voc_ref"]}
    bad = [k for k, (f, old, new) in mod.MUTANTS.items() if f not in texts or texts[f].count(old) != 1]
    return [("R31 each --mutant of sandbox-runin.py still matches its program (cproc or basic) exactly once (%s)" % ", ".join(mod.MUTANTS), not bad, "stale: %s" % bad)]   # (name, ok, detail)


def registered():
    with open(REGRESS) as f:
        text = f.read()
    with open(RMAP) as f:
        rmap = f.read()
    suites = re.search(r'^ALL_SUITES="([^"]*)"', text, re.M)
    return [("R32 the suite is registered: ALL_SUITES, and the cproc rule and the file's own rules of regress-map.txt",
             bool(suites) and "runin" in suites.group(1).split() and re.search(r"^sdsys/gpl\.bp/cproc\s*:.*\brunin\b", rmap, re.M) is not None
             and re.search(r"^sdsys/voc_template/run\.in\s*:\s*runin", rmap, re.M) is not None and re.search(r"^gplbld/sandbox-runin\.py\s*:\s*@self", rmap, re.M) is not None, "")]


def load():
    with open(CPROC, encoding="utf-8", errors="replace") as f:
        src = f.read()
    with open(VOCREC, encoding="utf-8") as f:
        voc = f.read()
    names = set(os.listdir(NEWVOC)) if os.path.isdir(NEWVOC) else set()
    extra = {}
    for key, path in (("basic", BASIC), ("parser.h", PARSERH), ("kw.newvoc", KW_NEWVOC), ("kw.template", KW_TEMPLATE), ("op_array.c", OPARRAY), ("bcomp", BCOMP), ("_voc_ref", VOCREF)):
        with open(path, encoding="utf-8", errors="replace") as f:
            extra[key] = f.read()
    for num in S213_MESSAGES:
        mp = os.path.join(MESSAGES, str(num))
        if os.path.isfile(mp):
            with open(mp, encoding="utf-8") as f:
                extra["msg%d" % num] = f.read()
    return src, voc, names, extra


def run_checks(src, voc, names, extra):
    return checks(src, voc, names, extra) + sandbox_mutants_still_match(src, extra) + registered()


# Each mutant: (name, kind, old, new).  kind "cproc" edits the source text, "voc" the record text.
MUTANTS = [
    ("admin test off", "cproc", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      display sysmsg(2001)   ;* Command requires administrator privileges\n      void kernel(K$AUDIT, 'run.in refused reason=not the administrator')",
     "   if 0 then\n      display sysmsg(2001)   ;* Command requires administrator privileges\n      void kernel(K$AUDIT, 'run.in refused reason=not the administrator')"),
    ("nest test off", "cproc", "   if ri.active then\n      display sysmsg(11178)", "   if 0 then\n      display sysmsg(11178)"),
    ("a seventh command: sh", "cproc", "      case ri.cmd = 'debug'\n         ri.n.names = 2\n", "      case ri.cmd = 'sh'\n         ri.n.names = 1\n      case ri.cmd = 'debug'\n         ri.n.names = 2\n"),
    ("the typed text is run", "cproc", "      new.sentence = ri.sentence\n", "      new.sentence = ri.rest\n"),
    ("the flag is not cleared first", "cproc", "revert.account:\n   ri.active = 0\n", "revert.account:\n"),
    ("the switches are restored in another order", "cproc", "   void kernel(K$SH,          ri.sw<1>)\n", "   void kernel(K$SH,          ri.sw<2>)\n"),
    ("the safety net is off", "cproc", "         if ri.active then\n            gosub revert.account\n            display sysmsg(11242, ri.account)",
     "         if 0 then\n            gosub revert.account\n            display sysmsg(11242, ri.account)"),
    ("the flag is never set", "cproc", "   ri.active = 1\n   void kernel(K$AUDIT, 'run.in begin", "   ri.active = 0\n   void kernel(K$AUDIT, 'run.in begin"),
    ("the account's LOGIN is run", "cproc", "      new.sentence = ri.sentence\n", "      new.sentence = 'LOGIN'\n      gosub proc.sentence\n      new.sentence = ri.sentence\n"),
    ("a slash is a plain character", "cproc", "'abcdefghijklmnopqrstuvwxyz0123456789._-', ri.word[ri.i, 1], 1)", "'abcdefghijklmnopqrstuvwxyz0123456789._-/', ri.word[ri.i, 1], 1)"),
    ("sdsys is not refused", "cproc", "   if ri.acct = 'sdsys' then\n", "   if 0 then\n"),
    ("one switch is not restored", "cproc", "   void kernel(K$SD.ACCOUNTS, ri.sw<3>)\n", ""),
    ("LOGTO no longer loads through the routine", "cproc", "   gosub load.account.switches   ;* the account-scoped switches, from the new account's own register record",
     "   null   ;* the account-scoped switches, from the new account's own register record"),
    ("the verb is in the ordinary VOC too", "newvoc", None, None),
    ("the record says 43", "voc", "V\nIN\n42\n", "V\nIN\n43\n"),
    ("the check of a file in the account is dropped", "cproc", "   if ri.n.names = 2 then\n      ri.file = field(ri.rest, ' ', 3)", "   if 0 then\n      ri.file = field(ri.rest, ' ', 3)"),
    ("the word loop does not check the plain word", "cproc", "            gosub ri.plain.word\n", "            ri.ok = @true\n"),
    ("the directory is entered before the flag", "cproc", "   ri.active = 1\n   void kernel(K$AUDIT, 'run.in begin account=' : ri.acct : ' command=' : ri.sentence)\n",
     "   void kernel(K$AUDIT, 'run.in begin account=' : ri.acct : ' command=' : ri.sentence)\n   if ospath(acc.rec, OS$CD) then null\n   ri.active = 1\n"),
    ("no message after an abort", "cproc", "            display sysmsg(11242, ri.account)   ;* run.in: the command did not finish; the session is back in account %1\n", ""),
    # 3 Nov 26: the NO.CATALOG option
    ("run.in basic does not give no.catalog", "cproc", "   if ri.cmd = 'basic' then ri.sentence := ' no.catalog'\n", ""),
    ("no.catalog is given to every command", "cproc", "if ri.cmd = 'basic' then ri.sentence := ' no.catalog'", "ri.sentence := ' no.catalog'"),
    ("a person may give no.catalog", "cproc", "ri.n.names = 2 ; ri.opts = 'debugging no.query'", "ri.n.names = 2 ; ri.opts = 'debugging no.query no.catalog'"),
    ("no.catalog may be a name", "cproc", "ri.kwords = 'local global pcode no.query no.catalog noxref", "ri.kwords = 'local global pcode no.query noxref"),
    ("basic ignores the option", "basic", "      if catalogue.name # '' and no.catalog then\n", "      if 0 then\n"),
    ("basic catalogues after the skip as well", "basic", "      end else if catalogue.name # '' then\n", "      end\n      if catalogue.name # '' then\n"),
    ("basic never sets the flag", "basic", "            no.catalog = @true    ;* 3 Nov 26 dm  (S.96)", "            null"),
    ("the template record has another number", "kw.template", "K\n239\n", "K\n240\n"),
    ("the newvoc record has another number", "kw.newvoc", "\n239\n", "\n241\n"),
    ("parser.h has another number", "parser.h", "KW$NO.CATALOG     239", "KW$NO.CATALOG     240"),
    # 2 Nov 26: the forged-abort defect (probe-runin-forge.py on a real install)
    ("the common is a plain name again", "cproc", "   common /$runin/ ri.active,", "   common /runin/ ri.active,"),
    ("the kernel lets any program join a $ common", "op_array.c", "      !(process.program.flags & HDR_INTERNAL))\n    k_error(sysmsg(11598));", "      0)\n    k_error(sysmsg(11598));"),
    ("the kernel guards only $, not _", "op_array.c", "((*block_name == '$') || (*block_name == '_'))", "(*block_name == '$')"),
]

# 11 Nov 26, S.213.  --selftest --from=N runs the mutants from index N on; M_S213 is this sitting's first.
M_S213 = len(MUTANTS)
MUTANTS += [
    ("the words are not compared with the shipped VOC", "cproc", "   gosub ri.own.words\n   if ri.bad # '' then\n", "   ri.bad = ''\n   if ri.bad # '' then\n"),
    ("the words are asked after the flag is set", "cproc", "   gosub ri.own.words\n   if ri.bad # '' then\n      display sysmsg(14070, ri.bad[1, 40], ri.acct)",
     "   ri.active = 1\n   gosub ri.own.words\n   if ri.bad # '' then\n      display sysmsg(14070, ri.bad[1, 40], ri.acct)"),
    ("only the command word is compared, not the options", "cproc", "            if (ri.w = 1 or ri.w > 1 + ri.n.names) and ri.bad = '' then", "            if (ri.w = 1) and ri.bad = '' then"),
    ("only the type letter is compared", "cproc", "                  case field(ri.vrec, @fm, 2, 9999) # field(ri.own, @fm, 2, 9999)\n", "                  case 0\n"),
    ("a missing record passes", "cproc", "                  case ri.vrec = ''\n                     ri.bad = ri.word ; ri.why = 'no entry in the voc of the account'\n", ""),
    ("the refusal of a word is not audited", "cproc", "      void kernel(K$AUDIT, 'run.in refused account=' : ri.acct : ' word=' : ri.bad[1, 40] : ' reason=' : ri.why)\n", ""),
    ("the command keeps the administrator flag", "cproc", "   void kernel(K$OS.EXEC, 0)\n   void kernel(K$ADMINISTRATOR, 0)\n   return\n", "   void kernel(K$OS.EXEC, 0)\n   return\n"),
    ("the flag is never dropped (no call)", "cproc", "      gosub ri.narrow            ;* 11 Nov 26, S.213: not the administrator from here to revert.account\n", ""),
    ("the flag is dropped after the command", "cproc", "      gosub ri.narrow            ;* 11 Nov 26, S.213: not the administrator from here to revert.account\n      gosub proc.sentence\n",
     "      gosub proc.sentence\n      gosub ri.narrow\n"),
    ("debug is given bp-edit", "cproc", "(ri.cmd = 'decatalog') or (ri.cmd = 'delete.catalog'))", "(ri.cmd = 'decatalog') or (ri.cmd = 'delete.catalog') or (ri.cmd = 'debug'))"),
    ("every command is given voc-edit", "cproc", "   void kernel(K$VOC.EDIT,  0)\n", "   void kernel(K$VOC.EDIT,  1)\n"),
    ("SH follows the account's record during a run", "cproc", "   void kernel(K$SH,      not(ri.active) and (upcase(trim(acc.record<ACC$SH>)) = 'YES'))", "   void kernel(K$SH,      (upcase(trim(acc.record<ACC$SH>)) = 'YES'))"),
    ("OS.EXECUTE follows the account's record during a run", "cproc", "   void kernel(K$OS.EXEC, not(ri.active) and (upcase(trim(acc.record<ACC$OS.EXEC>)) = 'YES'))",
     "   void kernel(K$OS.EXEC, (upcase(trim(acc.record<ACC$OS.EXEC>)) = 'YES'))"),
    ("revert does not restore the flag", "cproc", "   void kernel(K$ADMINISTRATOR, ri.sw<10>)   ;* 11 Nov 26, S.213: LAST - see the note above\n", ""),
    ("revert restores the flag first", "cproc", "revert.account:\n   ri.active = 0\n", "revert.account:\n   ri.active = 0\n   void kernel(K$ADMINISTRATOR, 1)\n"),
    ("revert leaves the account's edit gate on", "cproc", "   void kernel(K$BP.EDIT,   ri.sw<8>)\n", ""),
    ("the gates are restored after the directory change", "cproc",
     "   void kernel(K$VOC.EDIT,  ri.sw<7>)\n   void kernel(K$BP.EDIT,   ri.sw<8>)\n   void kernel(K$DICT.EDIT, ri.sw<9>)\n   if not(ospath(ri.path, OS$CD)) then\n      display sysmsg(5162)   ;* Fatal error : Cannot return to previous account\n      return to abort.cproc\n   end\n",
     "   if not(ospath(ri.path, OS$CD)) then\n      display sysmsg(5162)   ;* Fatal error : Cannot return to previous account\n      return to abort.cproc\n   end\n   void kernel(K$VOC.EDIT,  ri.sw<7>)\n   void kernel(K$BP.EDIT,   ri.sw<8>)\n   void kernel(K$DICT.EDIT, ri.sw<9>)\n"),
    ("the flag is not kept", "cproc", "   ri.sw<10> = kernel(K$ADMINISTRATOR, -1)", "   ri.sw<10> = 1 ;* kernel(K$ADMINISTRATOR, -1)"),
    ("the abort branch does something before revert", "cproc", "         if ri.active then\n            gosub revert.account\n            display sysmsg(11242, ri.account)",
     "         if ri.active then\n            void kernel(K$ADMINISTRATOR, 1)\n            gosub revert.account\n            display sysmsg(11242, ri.account)"),
    ("bcomp runs $execute under run.in", "bcomp", "         if ri.active then\n            err.msg = sysmsg(14071)", "         if 0 then\n            err.msg = sysmsg(14071)"),
    ("bcomp runs $execute and then reports", "bcomp", "            gosub error\n         end else\n            execute token.string\n         end\n", "            gosub error\n         end\n         execute token.string\n"),
    ("bcomp's common differs from cproc's", "bcomp", "   common /$runin/ ri.active, ri.path, ri.account.path, ri.who, ri.sw, ri.account\n", "   common /$runin/ ri.active\n"),
    ("an include file is not asked", "bcomp", "   ri.chk.path = fileinfo(incl.file, FL$PATH)\n   gosub ri.outside\n", "   ri.out = @false\n"),
    ("ri.outside refuses nothing", "bcomp", "then ri.out = @true\n", "then ri.out = @false\n"),
    ("message 14070 does not name the account", "msg14070", " of account %2", ""),
]

# 11 Nov 26, S.213 second part.  --selftest --from=s213b runs these only.
M_S213B = len(MUTANTS)
MUTANTS += [
    ("LOGTO is not refused during a run", "cproc", "   if ri.active then\n      display sysmsg(14073, ri.account)", "   if 0 then\n      display sysmsg(14073, ri.account)"),
    ("the LOGTO refusal is not audited", "cproc", "      void kernel(K$AUDIT, 'run.in refused account=' : ri.account : ' target=' : downcase(new.account)[1, 40] : ' reason=logto')\n", ""),
    ("the LOGTO refusal goes on into LOGTO", "cproc", "      display sysmsg(14073, ri.account) ;* logto is refused while run.in is running a command in account %1\n      void kernel(K$AUDIT, 'run.in refused account=' : ri.account : ' target=' : downcase(new.account)[1, 40] : ' reason=logto')\n      unwinding = 2\n      return\n",
     "      display sysmsg(14073, ri.account) ;* logto is refused while run.in is running a command in account %1\n      void kernel(K$AUDIT, 'run.in refused account=' : ri.account : ' target=' : downcase(new.account)[1, 40] : ' reason=logto')\n      unwinding = 2\n"),
    ("the LOGTO refusal comes after the sdsys test", "cproc",
     "   if ri.active then\n      display sysmsg(14073, ri.account)", "   if (downcase(new.account) = \"sdsys\") then null\n   if ri.active then\n      display sysmsg(14073, ri.account)"),
    ("_voc_ref follows any Q-pointer during a run", "_voc_ref", "                  if not(q.registered and downcase(q.named) = ri.account) then", "                  if 0 then"),
    ("_voc_ref accepts an unregistered path during a run", "_voc_ref", "                  if not(q.registered and downcase(q.named) = ri.account) then",
     "                  if q.registered and downcase(q.named) # ri.account then"),
    ("_voc_ref asks only for a non-administrator", "_voc_ref", "               if ri.active then\n                  if not(q.registered", "               if ri.active and not(vr.admin) then\n                  if not(q.registered"),
    ("_voc_ref asks after check.q.hop", "_voc_ref",
     "               if ri.active then\n                  if not(q.registered and downcase(q.named) = ri.account) then\n                     set.status ER$PERM\n                     return\n                  end\n               end\n\n* 13 Oct 26 dm - second sitting: only into an account the user could LOGTO (see the note at the top).\n               if not(vr.admin) then\n                  gosub check.q.hop\n                  if not(q.ok) then\n                     set.status ER$PERM\n                     return\n                  end\n               end\n",
     "\n* 13 Oct 26 dm - second sitting: only into an account the user could LOGTO (see the note at the top).\n               if not(vr.admin) then\n                  gosub check.q.hop\n                  if not(q.ok) then\n                     set.status ER$PERM\n                     return\n                  end\n               end\n               if ri.active then\n                  if not(q.registered and downcase(q.named) = ri.account) then\n                     set.status ER$PERM\n                     return\n                  end\n               end\n"),
    ("_voc_ref's common differs from cproc's", "_voc_ref", "   common /$runin/ ri.active, ri.path, ri.account.path, ri.who, ri.sw, ri.account\n", "   common /$runin/ ri.active, ri.account\n"),
    ("message 14073 does not name logto", "msg14073", "logto is refused", "it is refused"),
]


def selftest():
    src, voc, names, extra = load()
    base = run_checks(src, voc, names, extra)
    if any(not ok for _, ok, _ in base):
        print("selftest: the unmutated source already fails; fix that first")
        return 1
    missed = 0
    start = 0
    for a in sys.argv[1:]:
        if a.startswith("--from="):
            start = {"--from=s213": M_S213, "--from=s213b": M_S213B}.get(a) or int(a.split("=", 1)[1])
    if start:
        print("selftest: mutants from index %d on (%d of %d)" % (start, len(MUTANTS) - start, len(MUTANTS)))
    for name, kind, old, new in MUTANTS[start:]:
        s, v, nm, ex = src, voc, set(names), dict(extra)
        if kind == "cproc":
            if s.count(old) != 1:
                print("  [CANNOT] %-60s the text does not occur exactly once (%d)" % (name, s.count(old)))
                missed += 1
                continue
            s = s.replace(old, new)
        elif kind == "voc":
            v = v.replace(old, new)
        elif kind == "newvoc":
            nm.add("run.in")
        elif kind in ex:
            if ex[kind].count(old) != 1:
                print("  [CANNOT] %-60s the text does not occur exactly once (%d)" % (name, ex[kind].count(old)))
                missed += 1
                continue
            ex[kind] = ex[kind].replace(old, new)
        res = run_checks(s, v, nm, ex)
        caught = [n for n, ok, _ in res if not ok]
        if caught:
            print("  [caught] %-60s by %s" % (name, ", ".join(c.split()[0] for c in caught[:4])))
        else:
            print("  [MISSED] %-60s" % name)
            missed += 1
    print("selftest: %d mutants, %d missed or not applied" % (len(MUTANTS), missed))
    return 0 if missed == 0 else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        src, voc, names, extra = load()
    except OSError as e:
        print("cannot read the source: %s" % e)
        return 2
    res = run_checks(src, voc, names, extra)
    failed = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        failed += 0 if ok else 1
    print("test-runin-units: %d checks, %d failed" % (len(res), failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
