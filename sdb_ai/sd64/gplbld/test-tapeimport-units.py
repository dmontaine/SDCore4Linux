#!/usr/bin/env python3
"""test-tapeimport-units.py - S.92 TAPE.IMPORT: the verb, the filler and the reader read as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tapeimport-units.py
  python3 .../test-tapeimport-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed.  Written 30 Oct 26 with the verb.

  A  the verb is the administrator's: that check comes first, the verb is in the SDSYS VOC template and in no other VOC
  B  the verb reads the whole image BEFORE anything is made, asks before it makes, and makes the account only through !create_account as a USER with the fill hook
  C  the filler and the reader never open a file for writing outside what they are meant to make, never execute, compile or catalogue anything from an image
  D  the reader opens the image READONLY and is not $internal (so the OS gate still applies to it)
  E  the messages exist, at most four arguments each, and the numbers are the ones the programs use

***IT READS THE PROGRAMS AS TEXT.*** It cannot say that a refusal happens or a file is written: sandbox-tapeimg.py, sandbox-tapeimport.py and the VM witness do.  The administrator's
refusal in particular cannot be shown in a sandbox, whose sessions are the administrator.

--selftest mutates the source in the ways these rules could plausibly be broken and requires each mutation to be CAUGHT and to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GP = os.path.join(SDSYS, "gpl.bp")
FILES = {"tapeimp": os.path.join(GP, "tapeimp"), "tape_fill": os.path.join(GP, "tape_fill"), "tapeimg": os.path.join(GP, "tapeimg")}
VOCT = os.path.join(SDSYS, "voc_template", "tape.import")
NEWVOC = os.path.join(SDSYS, "newvoc")
MESSAGES = os.path.join(SDSYS, "messages")
USED = list(range(11919, 11930)) + list(range(11938, 11943))


def code_lines(src):
    return [(i, l) for i, l in enumerate(src.splitlines(), 1) if not l.lstrip().startswith("*")]


def first(L, needle, start=0):
    for k in range(start, len(L)):
        if needle in L[k][1]:
            return k
    return None


def check(srcs, voct, newvoc_has, messages):
    rows = []

    def row(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    V, F, R = (code_lines(srcs[k]) for k in ("tapeimp", "tape_fill", "tapeimg"))

    # ---- A
    p_adm = first(V, "if not(kernel(K$ADMINISTRATOR, -1)) then")
    p_parse = first(V, "call @parser(PARSER$RESET")
    p_open = first(V, "call !tapeimg('open', image")
    p_create = first(V, "call !create_account('USER', to.name, settings, err)")
    row("A1 the administrator check is the first thing the verb does, before it parses a word of the sentence",
        None not in (p_adm, p_parse) and p_adm < p_parse and "stop sysmsg(2001)" in V[p_adm + 1][1])
    row("A2 the verb is in voc_template as V, CA, $tapeimp", voct.split("\n")[:3] == ["V", "CA", "$tapeimp"], repr(voct))
    row("A3 it is in no newvoc (so in no account's VOC but SDSYS's)", not newvoc_has)

    # ---- B
    p_next = first(V, "call !tapeimg('next', '', kind, num, aux, id, rec, verdict)")
    p_until = first(V, "until kind = 'E' do")
    p_ask = first(V, "display sysmsg(11927, to.name):")
    p_list = first(V, "if list.only then")
    p_nothing = first(V, "if upcase(trim(yn)) # 'Y' then stop sysmsg(11938)")
    row("B1 the image is opened and read to its end before the account is made, and the verb opens it nowhere else",
        None not in (p_open, p_next, p_until, p_create) and p_open < p_next < p_until < p_create and sum(1 for _, t in V if "call !tapeimg('open'" in t) == 1)
    row("B2 LIST stops before anything is made", None not in (p_list, p_create) and p_list < p_create and any("stop" in V[k][1] for k in range(p_list, p_list + 12)))
    row("B3 the question comes before the account is made, and an input that ends or says anything but Y imports nothing",
        None not in (p_ask, p_nothing, p_create) and p_ask < p_nothing < p_create and "status() = ER$EOF then yn = 'N'" in V[p_nothing - 1][1])
    p_nq = first(V, "if not(no.query) then")
    row("B4 NO.QUERY only skips the question", None not in (p_nq, p_ask) and p_nq < p_ask)
    row("B5 the account is a USER account, made with the fill hook and the image path",
        first(V, "settings<CA$AFTER> = '!tape_fill'") is not None and first(V, "settings<CA$AFTER.ARG> = image") is not None and
        first(V, "settings<CA$AFTER> = '!tape_fill'") < p_create and sum(1 for _, t in V if "!create_account(" in t) == 1)
    row("B6 the settings never ask for a gate: no ssh, api, sh, os.execute, files, ai", not any(re.search(r"CA\$(ROUTE|OS\.|FILES|AI|NET|VOC|BP|DICT|SHARED|ATTACH|REUSE)", t) for _, t in V))
    row("B7 the log is written for a run that reached the filler, whether or not the account was made", first(V, "if tf.src # '' then gosub write.log") is not None)
    row("B8 every log is a NEW record: the id holds the account, the date, the time and the user number",
        first(V, "log.id = to.name : '.' : oconv(date(), 'D4Y')") is not None and "@userno" in V[first(V, "log.id = ")][1])

    # ---- C
    for name, L in (("tape_fill", F), ("tapeimp", V)):
        bad = [t.strip() for _, t in L if re.search(r"\b(openseq|writeseq|writeblk|weofseq|osdelete|osopen)\b", t)]
        row("C %s opens no operating system file itself (the image is the reader's)" % name, not bad, repr(bad[:2]))
    bad = [t.strip() for _, t in F if not t.strip().startswith("$") and re.search(r"\b(execute|os\.execute|perform|basic|catalog|decatalog|run|chain|sh)\b", t)]
    row("C tape_fill executes, compiles, catalogues and runs nothing", not bad, repr(bad[:2]))
    mk = [t.strip() for _, t in F if re.search(r"\bcreate\.file\b", t)]
    row("C tape_fill makes files only below pathname (every create.file names the account's directory or the target built from it)",
        bool(mk) and all(("pathname" in t or "target" in t) for t in mk) and first(F, "target = pathname : @ds : final : '.dic'") is not None and first(F, "target = pathname : @ds : final\n") is None or
        (bool(mk) and all(("pathname" in t or "target" in t) for t in mk)), repr(mk[:3]))
    row("C the filler's log is capped at 10000 lines by default", any(t.strip() == "tf.logcap = 10000" for _, t in F))
    p_reached = first(F, "tf.src = '-'")
    p_fopen = first(F, "call !tapeimg('open', img.arg")
    row("C the filler marks that it was reached BEFORE it opens the image, so that a refused image is logged too (the VM witness found it was not)",
        None not in (p_reached, p_fopen) and p_reached < p_fopen)
    p_fname = first(F, "call !tapeimg('name', base : fm : 'file' : fm : maxid")
    p_fcreate = first(F, "create.file target dynamic on error")
    row("C a file name is judged by the name rule before the first file is created", None not in (p_fname, p_fcreate) and p_fname < p_fcreate)
    p_idrule = first(F, "call !tapeimg('name', id : fm : 'id' : fm : maxid")
    p_write = first(F, "write rec to cur.f, lid")
    row("C a record id is judged by the name rule and lower-cased before it is written", None not in (p_idrule, p_write) and p_idrule < p_write and first(F, "lid = downcase(id)") < p_write)
    row("C a quote in a directory file's id is refused (the helper is given the path single-quoted)", first(F, "nm.isdir<mp> and index(id, \"'\", 1) then why = 'quote'") is not None)
    row("C a binary item is never written", first(F, "if kind = 'O' then") is not None and first(F, "if kind = 'O' then") < first(F, "begin case", first(F, "if kind = 'O' then")))

    # ---- D
    for name, L, src in (("tapeimg", R, srcs["tapeimg"]), ("tape_fill", F, srcs["tape_fill"]), ("tapeimp", V, srcs["tapeimp"])):
        if name != "tapeimp":
            row("D %s is not $internal (the OS gate still applies to what it opens)" % name, not any(t.strip() == "$internal" for _, t in L))
    row("D the reader opens the image READONLY", first(R, "openseq path readonly to f on error") is not None)
    bad = [t.strip() for _, t in R if re.search(r"\b(writeseq|writeblk|weofseq|create\.file|delete|osdelete|execute|os\.execute)\b", t)]
    row("D the reader writes, deletes and executes nothing", not bad, repr(bad[:2]))
    row("D the reader's name rule has the rules of tapegen.py (empty, dot, dotdot, nul, slash, leading-dot, too-long, control, high-byte, unsafe)",
        all(w in srcs["tapeimg"] for w in ("'empty'", "'dot'", "'dotdot'", "'nul'", "'slash'", "'leading-dot'", "'too-long'", "'control'", "'high-byte'", "'unsafe'")))

    # ---- E
    called = set()
    for k in ("tapeimp", "tape_fill"):
        for m in re.finditer(r"sysmsg\((\d+)((?:,[^()]*(?:\([^()]*\))?)*)\)", srcs[k]):
            called.add(int(m.group(1)))
    for m in re.finditer(r"(?:ferr|err) = (\d+)", srcs["tape_fill"] + srcs["tapeimp"]):
        called.add(int(m.group(1)))
    row("E1 every number of the feature is a message file", all(messages.get(n) for n in USED), "missing %s" % [n for n in USED if not messages.get(n)])
    row("E2 no message of the feature has more than four arguments", all(max([int(x) for x in re.findall(r"%(\d)", messages[n])] or [0]) <= 4 for n in USED if messages.get(n)))
    row("E3 every number the programs say is one of the feature's or an old one that exists",
        all(n in USED or os.path.isfile(os.path.join(MESSAGES, str(n))) for n in called), "%s" % sorted(n for n in called if n not in USED and not os.path.isfile(os.path.join(MESSAGES, str(n)))))
    return rows


def load():
    srcs = {k: open(p, encoding="utf-8").read() for k, p in FILES.items()}
    voct = open(VOCT, encoding="utf-8").read() if os.path.isfile(VOCT) else ""
    newvoc_has = os.path.exists(os.path.join(NEWVOC, "tape.import"))
    messages = {}
    for n in USED:
        p = os.path.join(MESSAGES, str(n))
        messages[n] = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    return srcs, voct, newvoc_has, messages


MUTANTS = [
    ("tapeimp", "administrator check after the parse", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001)  ;* Command requires administrator privileges\n   end\n\n   parser = \"!PARSER\"\n   call @parser(PARSER$RESET, 0, @sentence, 0)",
     "   parser = \"!PARSER\"\n   call @parser(PARSER$RESET, 0, @sentence, 0)\n   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001)  ;* Command requires administrator privileges\n   end"),
    ("tapeimp", "the account made before the whole image is read", "   call !create_account('USER', to.name, settings, err)", "   call !create_account('USER', to.name, settings, err)\n   call !tapeimg('open', image, kind, num, aux, id, rec, verdict)"),
    ("tapeimp", "no question", "      display sysmsg(11927, to.name):         ;* Import the image into the NEW user account %1? (Y/N)\n", ""),
    ("tapeimp", "end of input is a yes", "      if yn = '' and status() = ER$EOF then yn = 'N'", "      if yn = '' and status() = ER$EOF then yn = 'Y'"),
    ("tapeimp", "LIST does not stop", "      @system.return.code = 0\n      stop\n   end\n\n* ---------------------------------------------------------------- the checks before anything is made", "      @system.return.code = 0\n   end\n\n* ---------------------------------------------------------------- the checks before anything is made"),
    ("tapeimp", "a group account", "call !create_account('USER', to.name, settings, err)", "call !create_account('GROUP', to.name, settings, err)"),
    ("tapeimp", "a gate switched on", "   settings<CA$AFTER> = '!tape_fill'\n", "   settings<CA$AFTER> = '!tape_fill'\n   settings<CA$ROUTE.SSH> = 1\n"),
    ("tape_fill", "the filler is marked as reached only after the image opened", "   tf.src = '-'           ;* ", "   tf.src = ''            ;* "),
    ("tapeimp", "the log only when it worked", "   if tf.src # '' then gosub write.log", "   if tf.src # '' and ok then gosub write.log"),
    ("tapeimp", "the log record overwritten", "log.id = to.name : '.' : oconv(date(), 'D4Y')", "log.id = to.name : '.' : '1' : oconv(date(), 'D4Y')"),
    ("tapeimp", "the verb opens the image itself", "   call !tapeimg('open', image : @fm : @fm : @fm : @fm : layout, kind, num, aux, id, rec, verdict)\n   if verdict # '' then\n      display sysmsg(11924, verdict, rec)",
     "   openseq image to imgf else null\n   call !tapeimg('open', image : @fm : @fm : @fm : @fm : layout, kind, num, aux, id, rec, verdict)\n   if verdict # '' then\n      display sysmsg(11924, verdict, rec)"),
    ("tape_fill", "an id written before its rule", "   call !tapeimg('name', id : fm : 'id' : fm : maxid, k1, k2, k3, k4, why, v)\n   if why = '' and nm.isdir<mp>",
     "   why = ''\n   if why = '' and nm.isdir<mp>"),
    ("tape_fill", "ids not lower-cased", "   lid = downcase(id)\n   read dup from cur.f, lid then", "   lid = id\n   read dup from cur.f, lid then"),
    ("tape_fill", "no quote rule", "nm.isdir<mp> and index(id, \"'\", 1) then why = 'quote'", "nm.isdir<mp> and index(id, \"\\\\\", 1) then why = 'quote'"),
    ("tape_fill", "binary items written", "   if kind = 'O' then\n      tf.nbin += 1", "   if 0 then\n      tf.nbin += 1"),
    ("tape_fill", "a program is run", "   gosub walk.made\n   return", "   gosub walk.made\n   execute 'RUN BP X'\n   return"),
    ("tape_fill", "the filler is $internal", "subroutine tape_fill(pathname, arg, made, ferr)", "$internal\nsubroutine tape_fill(pathname, arg, made, ferr)"),
    ("tape_fill", "a file made before its name is judged", "   call !tapeimg('name', base : fm : 'file' : fm : maxid, k1, k2, k3, k4, why, v)", "   why = ''\n   call !tapeimg('noop', base, k1, k2, k3, k4, v, v)"),
    ("tape_fill", "the log cap raised", "tf.logcap = 10000", "tf.logcap = 100000000"),
    ("tapeimg", "the image opened for writing", "openseq path readonly to f on error", "openseq path to f on error"),
    ("tapeimg", "the reader is $internal", "subroutine tapeimg(op, arg, kind, num, aux, id, rec, verdict)", "$internal\nsubroutine tapeimg(op, arg, kind, num, aux, id, rec, verdict)"),
    ("tapeimg", "the reader writes", "      case op = 'name'\n         gosub do.name", "      case op = 'name'\n         writeseq 'x' to ti.fu else null\n         gosub do.name"),
    ("tapeimg", "unsafe file names allowed", "'unsafe'", "'unsafe-gone'"),
]


def main(argv):
    srcs, voct, newvoc_has, messages = load()
    rows = check(srcs, voct, newvoc_has, messages)
    bad = [r for r in rows if not r[1]]
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
    print("%d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    if bad:
        return 1
    if "--selftest" not in argv:
        return 0
    live = 0
    for n, (which, name, old, new) in enumerate(MUTANTS):
        if srcs[which].count(old) != 1:
            print("  [BAD ] mutant %d (%s): the old text occurs %d times in %s" % (n, name, srcs[which].count(old), which))
            live += 1
            continue
        m = dict(srcs)
        m[which] = srcs[which].replace(old, new)
        try:
            caught = [r for r in check(m, voct, newvoc_has, messages) if not r[1]]
        except TypeError:       # a line the checks look for is gone: a comparison with nothing, which is a failure of the rule it was for
            caught = [("a line the checks need is missing", False, "")]
        print("  [%s] mutant %2d %-46s %s" % ("KILL" if caught else "LIVE", n, name, ("%d failed, first: %s" % (len(caught), caught[0][0][:60])) if caught else ""))
        if not caught:
            live += 1
    print("%d mutants, %d survived" % (len(MUTANTS), live))
    return 1 if live else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
