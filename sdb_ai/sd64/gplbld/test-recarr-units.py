#!/usr/bin/env python3
# test-recarr-units.py - the one-editor plan, stage 1 (26 Oct 2026): a record as a nested array and back ($recarr), CED's data mode (ced_edit, ftype 2) and the IDE's hand-over of a
# record to it (F12, do.fields), read off the source as text.  The behaviour is sandbox-recarr.py's (3,000-record round trip, the CED screen and the IDE on a pseudo-terminal); this holds
# the ORDER and the SHAPE it depends on and that a runtime row cannot see:
#   - $recarr puts marks back from the array's shape by hand (never by assigning to <f, v, s>, which would lose an empty value or a trailing mark), and refuses a number, a boolean, a
#     null, a collection or a fourth level instead of guessing;
#   - CED's save asks $recarr for the record BEFORE it writes anything, the types on offer are string and array with an array never below the second level, and a paste is asked of
#     $recarr (data.fits) before it is accepted;
#   - the IDE gives CED NO file and NO record id (so CED writes nothing and takes no lock), hands the screen over and back around the call, puts what comes back into the tab's text
#     before the screen is rebuilt, and never writes, reads with a lock or deletes in do.fields: the IDE's own save has the S.64 gate;
#   - F12 and the Go menu entry reach do.fields, the entry's mnemonic is not another entry's, and the help and the messages are there.
# FREE CHECK: no install, no sd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-recarr-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-recarr-units.py --selftest
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BP = os.environ.get("BPDIR", os.path.normpath(os.path.join(HERE, "..", "sdsys", "gpl.bp")))
MSG = os.environ.get("MSGDIR", os.path.normpath(os.path.join(HERE, "..", "sdsys", "messages")))


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def load():
    d = {n: read(os.path.join(BP, n)) for n in ("recarr", "ced_edit", "ide")}
    for n in ("11226", "11215", "11988", "11989", "11990", "11991", "11992"):
        d["m" + n] = read(os.path.join(MSG, n))
    return d


def section(text, label):
    """The lines of the BASIC label `label:` (at column 0) up to the next label or the program's end; None if there is no such label."""
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.rstrip() == label + ":":
            out = []
            for l2 in lines[i + 1:]:
                if re.match(r"^[A-Za-z][\w.]*:\s*$", l2) or re.match(r"^end\s*$", l2):
                    break
                out.append(l2)
            return out
    return None


def code(lines):
    """Statements only: whole-line comments and trailing ;* comments dropped, blanks dropped."""
    out = []
    for l in lines or []:
        s = re.sub(r";\*.*$", "", l).rstrip()
        if s.strip() and not s.lstrip().startswith("*"):
            out.append(s.strip())
    return out


def first(lines, pat):
    for i, l in enumerate(lines):
        if re.search(pat, l):
            return i
    return None


def ordered(lines, pats):
    idx = [first(lines, p) for p in pats]
    return None not in idx and idx == sorted(idx) and len(set(idx)) == len(idx)


def checks(p):
    rows = []

    def row(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    # ---- R: $recarr ------------------------------------------------------------------------------------------------------------------------------------------------
    r = p["recarr"]
    row("R1 recarr is an internal subroutine with the cataloged name $recarr and the arguments (op, a, b, ok)",
        re.search(r"^\$internal\s*$", r, re.M) and re.search(r"^subroutine recarr\(op, a, b, ok\)\s*$", r, re.M) and re.search(r"^\$catalog \$recarr\s*$", r, re.M))
    to = code(section(r, "to.array"))
    row("R2 to.array: a field is an array only when it holds a value mark or a subvalue mark, a value only when it holds a subvalue mark (the canonical form)",
        first(to, r"if index\(f\.t, @vm, 1\) or index\(f\.t, @sm, 1\) then") is not None and first(to, r"if index\(v\.t, @sm, 1\) then") is not None, "\n".join(to[:8]))
    fr = code(section(r, "from.array"))
    row("R3 from.array puts the marks in by hand (b := @fm / @vm / @sm) and never by assigning to a dynamic array element, which would lose an empty value or a trailing mark",
        all(first(fr, pat) is not None for pat in (r"b := @fm\b", r"b := @vm\b", r"b := @sm\b")) and first(fr, r"\bb<") is None, "\n".join(fr[:10]))
    row("R4 from.array refuses (ok = 0) a top that is not an array, a field that is neither string nor array, a value that is neither and a subvalue that is not a string - four places - and clears b",
        sum(1 for l in fr if re.search(r"\bok = 0\b", l)) >= 4 and first(fr, r"if not\(ok\) then b = ''") is not None, "ok = 0 x %d" % sum(1 for l in fr if "ok = 0" in l))

    # ---- R5-R8: the token form (26 Oct 26) ------------------------------------------------------------------------------------------------------------------------
    row("R5 the ops 'totext' and 'fromtext' are dispatched",
        re.search(r"case op = 'totext'\s*\n\s*gosub to\.text", r) is not None and re.search(r"case op = 'fromtext'\s*\n\s*gosub from\.text", r) is not None)
    tt = code(section(r, "to.text"))
    row("R6 to.text reads every line back BEFORE it accepts it, and refuses (ok = 0, b = the field's number) a field that does not come back as it was",
        ordered(tt, [r"gosub field\.to\.text", r"gosub field\.from\.text", r"if r\.line # f\.t then", r"^b = f\.i$", r"^ok = 0$", r"^return$", r"t\.all := t\.line", r"^b = t\.all$"]), "\n".join(tt))
    ft = code(section(r, "field.to.text"))
    row("R7 field.to.text writes the tokens in lower case (@vm @sm @tm), joins the pieces by a colon and leaves an empty text out",
        all(first(ft, pat) is not None for pat in (r"tok = '@vm'", r"tok = '@sm'", r"tok = '@tm'", r"t\.line := ':'", r"if seg # '' then", r"if rest # '' then")), "\n".join(ft[:14]))
    ff = code(section(r, "field.from.text"))
    row("R8 field.from.text reads any case (downcase), needs the token at the start of the line or after a colon AND at the end or before a colon, and takes the colon after a token as its separator",
        ordered(ff, [r"lc = downcase\(ln\)", r"pre\.ok = \(q = p\)", r"pre\.ok = \(lc\[q - 1, 1\] = ':'\)", r"post\.ok = \(q \+ 3 > n\.l\)", r"post\.ok = \(lc\[q \+ 3, 1\] = ':'\)",
                  r"if pre\.ok and post\.ok then", r"if lc\[p, 1\] = ':' then p \+= 1"]),
        "\n".join(ff))

    # ---- C: CED's data mode ----------------------------------------------------------------------------------------------------------------------------------------
    c = p["ced_edit"]
    row("C1 CED: an editor called with ftype 2 on something that is not an array returns at once (a record is an array of fields)",
        re.search(r"if ftype = 2 and kind # 'array' then return", c) is not None)
    sv = code(section(c, "save.record"))
    row("C2 save.record: ftype 2 asks $recarr for the record text BEFORE anything is written, and a refusal sets save.ok false with message 11988 and returns",
        ordered(sv, [r"if ftype = 2 then", r"call \$recarr\('from', c, rec\.text, rec\.ok\)", r"if not\(rec\.ok\) then", r"message\.text = sysmsg\(11988\)", r"save\.ok = @false", r"^return$", r"\bwriteu\b"]),
        "\n".join(sv[:14]))
    row("C3 save.record: the text written in data mode is the one $recarr made (rec.text), not the JSON",
        first(sv, r"if ftype = 2 then text = rec\.text else text = jbuild\(c\)") is not None)
    dt = code(section(c, "data.types"))
    row("C4 data.types: a string may become a list only where n.path < 2, a list becomes a string only when empty or one string",
        first(dt, r"if n\.path < 2 then ct\.allowed<-1> = 'array'") is not None and first(dt, r"if inmat\(x\) = 0 then") is not None
        and first(dt, r"if jtype\(x\{1\}\) = 'string' then ct\.allowed<-1> = 'string'") is not None, "\n".join(dt))
    ie = code(section(c, "insert.element"))
    k = first(ie, r"if ftype = 2 then")
    ie = ie[k:] if k is not None else []
    row("C5 insert.element: in data mode the types on offer are string, and array where n.path < 2 - not number, boolean, null or collection",
        ordered(ie, [r"if ftype = 2 then", r"^ct\.allowed = 'string'$", r"if n\.path < 2 then ct\.allowed<-1> = 'array'", r"^end else$", r"ct\.allowed = 'string' : @fm : 'number'"]), "\n".join(ie[:8]))
    ct = code(section(c, "change.type"))
    row("C6 change.type: the data mode's case is the first of the type cases (before the generic string case)",
        ordered(ct, [r"^case ftype = 2$", r"^gosub data\.types$", r"^case et = 'string'$"]))
    ap = code(section(c, "apply.type"))
    row("C7 apply.type: data mode makes its element (a list of one, or the one string) and returns before the generic cases",
        ordered(ap, [r"^if ftype = 2 then", r"v\{1\} = x", r"^cur\{nm\} = v$", r"^return$", r"^begin case$"]), "\n".join(ap[:14]))
    pe = code(section(c, "paste.element"))
    k = first(pe, r"if ftype = 2 then")
    pe = pe[k:] if k is not None else []
    row("C8 paste.element: in data mode the pasted element is asked of data.fits first, and a refusal says 11988 and returns before any position is asked or anything is inserted",
        ordered(pe, [r"if ftype = 2 then", r"gosub data\.fits", r"if not\(fits\) then", r"message\.text = sysmsg\(11988\)", r"^return$", r"gosub new\.position", r"ins v as cur\{np\}"]), "\n".join(pe[:20]))
    df = code(section(c, "data.fits"))
    row("C9 data.fits: the element is put inside as many arrays as the container is deep (n.path + 1) and $recarr decides",
        ordered(df, [r"for fit\.j = 0 to n\.path", r"fit\.a\{1\} = fit\.w", r"next fit\.j", r"call \$recarr\('from', fit\.w, fit\.t, fits\)"]), "\n".join(df))

    # ---- I: the IDE ------------------------------------------------------------------------------------------------------------------------------------------------
    i = p["ide"]
    dk = code(section(i, "do.key"))
    row("I1 do.key: F12 is the command 'fields'", ordered(dk, [r"case edata = 'f12'", r"cmd = 'fields'"]), "\n".join(dk[-12:]))
    rc = code(section(i, "run.cmd"))
    row("I2 run.cmd: the command 'fields' runs do.fields", ordered(rc, [r"case cmd = 'fields'", r"gosub do\.fields"]))
    df = code(section(i, "do.fields"))
    row("I3 do.fields: with no record open it says so (11218) and goes no further", ordered(df, [r"if nbuf = 0 then", r"msg = sysmsg\(11218\)", r"^return$", r"call \$recarr\('to'"]), "\n".join(df[:8]))
    row("I4 do.fields: the order - the record to an array, the screen left, CED called, the array back to text, the tab's text set, the screen taken again",
        ordered(df, [r"call \$recarr\('to'", r"gosub leave\.screen", r"call \$cedit\(", r"call \$recarr\('from'", r"bx\{k\} = fd\.new", r"gosub retake\.quiet"]), "\n".join(df))
    row("I5 do.fields gives CED NO file and NO record id (null, null) and the data mode (2): CED writes nothing and takes no lock",
        first(df, r"call \$cedit\(fd\.arr, '', '', 2, ") is not None)
    row("I6 do.fields itself does not write, read with a lock or delete, or run a command: the IDE's save (edit.check, the overwrite question) is the only writer",
        not any(re.search(r"\b(write|writeu|writev|readu|readv|delete|deleteu|execute|open)\b", l) for l in df), "\n".join(l for l in df if re.search(r"\b(write|writeu|readu|delete|execute|open)\b", l)))
    row("I7 do.fields changes the tab only when what came back differs (11989), else says it is as it was (11990)",
        ordered(df, [r"if fd\.new # fd\.was then", r"bx\{k\} = fd\.new", r"sysmsg\(11989,", r"end else", r"sysmsg\(11990,"]))

    # ---- I8-I12: the token form and the language in the IDE (26 Oct 26) ----------------------------------------------------------------------------------------------
    sf = code(section(i, "syntax.for"))
    row("I8 syntax.for asks $sl_syntax 'detect' with the file, the record id and the first line, as SED does - no suffix rule of its own",
        first(sf, r"call \$sl_syntax\('detect', sy\.file, sy\.id, sy\.first, '', syn\)") is not None and first(sf, r"suffix") is None, "\n".join(sf))
    sc = code(section(i, "stash.current"))
    row("I9 stash.current turns the editor's tokens back into marks only for a tab in token mode (bx m), and BEFORE the text is put in the tab's record",
        ordered(sc, [r"k = 'm' : u", r"if bx\{k\} then", r"call \$recarr\('fromtext', txt, tb\.raw, tb\.ok\)", r"txt = tb\.raw", r"k = 't' : u", r"bx\{k\} = txt"]), "\n".join(sc))
    td = code(section(i, "tab.display"))
    k0 = first(td, r"if not\(tb\.ok\) then")
    row("I10 tab.display shows tokens only for a tab in token mode and falls back to the record as it is (with message 11992) when 'totext' refuses",
        ordered(td, [r"k = 'm' : tb\.u", r"if bx\{k\} then", r"call \$recarr\('totext', tb\.raw, tb\.disp, tb\.ok\)", r"if not\(tb\.ok\) then"])
        and k0 is not None and ordered(td[k0:], [r"bx\{k\} = 0", r"msg = sysmsg\(11992, tb\.disp\)", r"tb\.disp = tb\.raw"]), "\n".join(td))
    sm = code(section(i, "set.token.mode"))
    row("I11 set.token.mode: a tab is in token mode (bx m = 1) only when the record holds a mark AND 'totext' accepts it; a record it refuses says why (11992)",
        ordered(sm, [r"bx\{k\} = 0", r"index\(tm\.raw, @vm, 1\) or index\(tm\.raw, @sm, 1\) or index\(tm\.raw, @tm, 1\)", r"call \$recarr\('totext', tm\.raw, tm\.disp, tm\.ok\)", r"if tm\.ok then", r"bx\{k\} = 1", r"msg = sysmsg\(11991\)", r"msg = sysmsg\(11992, tm\.disp\)"]), "\n".join(sm))
    orc = code(section(i, "open.record"))
    dsd = code(section(i, "do.sed"))
    dfl = code(section(i, "do.fields"))
    nf = code(section(i, "new.form"))
    lc_ = code(section(i, "load.current"))
    row("I12 the mode is set wherever the real record comes from (open.record, the return from SED, the return from CED) and the editor's text is made by tab.display (new.form, load.current)",
        ordered(orc, [r"bx\{k\} = rec", r"gosub set\.token\.mode", r"gosub load\.current"]) and ordered(dsd, [r"bx\{k\} = disk", r"gosub set\.token\.mode"]) and ordered(dfl, [r"bx\{k\} = fd\.new", r"gosub set\.token\.mode", r"msg = sysmsg\(11989"])
        and ordered(nf, [r"gosub tab\.display", r"ed\.text = tb\.disp"]) and ordered(lc_, [r"gosub tab\.display", r"mw\{'value'\} = tb\.disp"]))

    # ---- M: the menu, the help, the messages ----------------------------------------------------------------------------------------------------------------------
    m = p["m11226"].strip("\n")
    entries = m.split("|")[1:]
    labels = [e.split("~")[0] for e in entries]
    mn = [re.search(r"&(.)", lab).group(1).lower() for lab in labels if re.search(r"&(.)", lab)]
    row("M1 the Go menu has the entry 'Edit as fields~F12~fields' last, after the SED entry", len(entries) >= 2 and entries[-1].endswith("~F12~fields") and entries[-2].endswith("~sed"), repr(entries[-2:]))
    row("M2 every entry of the Go menu has a mnemonic and no two share one", len(mn) == len(entries) and len(set(mn)) == len(mn), repr(mn))
    row("M3 the IDE's help names F12 and the tokens", "F12" in p["m11215"] and "fields" in p["m11215"] and ":@vm: :@sm: :@tm:" in p["m11215"])
    row("M5 messages 11991 and 11992 are there: 11991 names the three tokens in lower case, 11992 takes the field number (%1)",
        "@vm, @sm and @tm" in p["m11991"] and "%1" in p["m11992"] and "field" in p["m11992"], repr((p["m11991"], p["m11992"])))
    row("M4 messages 11988, 11989 and 11990 are there; 11989 and 11990 take the file and the record id (%1 %2)",
        p["m11988"].startswith("A record holds only text") and "%1 %2" in p["m11989"] and "%1 %2" in p["m11990"])
    return rows


def run():
    rows = checks(load())
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        bad += 0 if ok else 1
    print("test-recarr-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad or not rows else 0


def selftest():
    progs = load()
    if not all(ok for _, ok, _ in checks(progs)):
        print("  [FAIL] the real sources do not pass")
        return 1
    print("  [ok] the real sources pass")
    caught = missed = 0

    def mutant(name, key, old, new, prefix):
        nonlocal caught, missed
        p = dict(progs)
        if old not in p[key]:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        p[key] = p[key].replace(old, new, 1)
        failing = [n for n, ok, _ in checks(p) if not ok]
        if failing and all(n.startswith(prefix) for n in failing):
            print("  [caught] %s (%s)" % (name, ", ".join(n.split()[0] for n in failing)))
            caught += 1
        else:
            print("  [MISSED] %s: failing rows %s" % (name, failing))
            missed += 1

    mutant("a field of subvalues only is a string", "recarr", "index(f.t, @vm, 1) or index(f.t, @sm, 1)", "index(f.t, @vm, 1)", "R2")
    mutant("the value mark is not put back", "recarr", "if v.i > 1 then b := @vm", "if v.i > 1 then b := @fm", "R3")
    mutant("a subvalue that is not a string is let through", "recarr", "if jtype(s.e) = 'string' then b := s.e else ok = 0", "b := s.e", "R4")
    mutant("save.record does not ask $recarr", "ced_edit", "call $recarr('from', c, rec.text, rec.ok)", "rec.ok = 1", "C2")
    mutant("the JSON is written in data mode", "ced_edit", "if ftype = 2 then text = rec.text else text = jbuild(c)", "text = jbuild(c)", "C3")
    mutant("a list may be a subvalue", "ced_edit", "if n.path < 2 then ct.allowed<-1> = 'array'\n      case et = 'array'", "if n.path < 3 then ct.allowed<-1> = 'array'\n      case et = 'array'", "C4")
    mutant("insert offers numbers in data mode", "ced_edit", "      ct.allowed = 'string'\n      if n.path < 2", "      ct.allowed = 'string' : @fm : 'number'\n      if n.path < 2", "C5")
    mutant("a paste is not asked of data.fits", "ced_edit", "      gosub data.fits\n      if not(fits) then", "      fits = 1\n      if not(fits) then", "C8")
    mutant("do.fields gives CED the record's file and id", "ide", "call $cedit(fd.arr, '', '', 2,", "call $cedit(fd.arr, fv, fd.id, 2,", "I")
    mutant("do.fields writes the record itself", "ide", "if fd.ok then fd.new = fd.text", "if fd.ok then fd.new = fd.text ; write fd.new on fv, fd.id", "I6")
    mutant("do.fields does not take the screen again", "ide", "   gosub retake.quiet\n   return\n\n* The window changed size", "   return\n\n* The window changed size", "I4")
    mutant("F12 runs SED", "ide", "cmd = 'fields'                  ;* the record as fields", "cmd = 'sed'                  ;* the record as fields", "I1")
    # 26 Oct 26: the token form's mutants
    mutant("totext does not read back what it made", "recarr", "if r.line # f.t then", "if r.line # r.line then", "R6")
    mutant("a token is read in lower case only", "recarr", "lc = downcase(ln)", "lc = ln", "R8")
    mutant("a token need not end the line or be followed by a colon", "recarr", "if pre.ok and post.ok then", "if pre.ok then", "R8")
    mutant("the colon after a token is kept as text", "recarr", "if lc[p, 1] = ':' then p += 1", "if lc[p, 1] = '!' then p += 1", "R8")
    mutant("an empty text is written between two tokens", "recarr", "      if seg # '' then\n         if need.sep", "      if 1 then\n         if need.sep", "R7")
    mutant("the IDE's language is the suffix again", "ide", "call $sl_syntax('detect', sy.file, sy.id, sy.first, '', syn)", "syn = '' ; suffix = 'c'", "I8")
    mutant("every tab is converted on the way back", "ide", "      if bx{k} then\n         call $recarr('fromtext'", "      if 1 then\n         call $recarr('fromtext'", "I9")
    mutant("a record that totext refuses is put in token mode", "ide", "      if tm.ok then\n         bx{k} = 1", "      if 1 then\n         bx{k} = 1", "I11")
    mutant("open.record leaves the mode unset", "ide", "   tm.u = uid\n   tm.raw = rec\n   gosub set.token.mode\n", "", "I12")
    mutant("11992 has no field number", "m11992", "field %1 holds", "a field holds", "M5")
    mutant("the menu entry is gone", "m11226", "|Edit as f&ields~F12~fields", "", "M1")
    mutant("the menu entry takes SED's mnemonic", "m11226", "Edit as f&ields~F12~fields", "&Edit as fields~F12~fields", "M2")
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
