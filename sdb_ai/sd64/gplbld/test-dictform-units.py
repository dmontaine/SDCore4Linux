#!/usr/bin/env python3
"""test-dictform-units.py - S.90 stage 2: the dictionary item form (gpl.bp/dict_form) and the IDE's hook for it (do.dform, /form, the Go menu entry), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-dictform-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-dictform-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
31 Oct 26 dm  New with the form (plan .claude/plan-s90-dict-form.md).
END-HISTORY

WHAT IT HOLDS.  $dict_form is the screen over !dict_item: it opens nothing, writes nothing and makes no record of its own (every record comes from the engine's 'build'); it
checks a row as the focus leaves it and every row again before it ends with a record; it ends with save, text, cancel or cannot and nothing else; an item the engine cannot parse
is `cannot` BEFORE any form is made; a change of type collects what was typed before the form is made again; Esc asks only when something changed.  The IDE's do.dform refuses a
tab that is not a dictionary item and a read-only tab, keeps the editor's text first (stash.current), calls the form once, redraws, puts the record in the tab as the token form
and writes it with the IDE's own save only for `save`; `/form` is taken off the sentence before any id is read from it; the Go menu has the entry, with no key.

***IT READS THE SOURCE AS TEXT.***  That the form shows what the engine says and the IDE saves what the form built is sandbox-dictform.py (the IDE on a pseudo-terminal).
--selftest requires each mutation to match its text exactly once and to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.join(HERE, os.pardir, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
FILES = {"form": os.path.join(GPL, "dict_form"), "ide": os.path.join(GPL, "ide"), "go": os.path.join(SDSYS, "messages", "11226"),
         "m1": os.path.join(SDSYS, "messages", "11949"), "m2": os.path.join(SDSYS, "messages", "11950")}


def strip(src):
    """the code without comment lines and trailing ;* comments"""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def between(text, start, end):
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]


def checks(src, others):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    form, ide = strip(src["form"]), strip(src["ide"])
    ck("F0 NULL CASE: the reader sees the form (over 5 KB of code) and the IDE (over 100 KB)", len(form) > 5000 and len(ide) > 100000, repr((len(form), len(ide))))
    ck("F1 the form is $internal, `subroutine dict_form(rec, title, newrec, res)`, catalogued as $dict_form, and no other program takes the name",
       form.lstrip().startswith("$internal") and re.search(r"^subroutine dict_form\(rec, title, newrec, res\)$", form, re.M) is not None and "$catalog $dict_form" in form
       and not any(re.search(r"^\$catalog\s+\$dict_form\b", strip(t), re.M | re.I) for t in others.values()), "")
    bad = re.findall(r"\b(openseq|openpath|open|write|writev|writeu|delete|execute|perform|chain|kernel|oscopy|osopen)\b", form, re.I)
    ck("F2 it opens nothing, writes nothing and runs nothing", not bad, repr(bad[:5]))
    ck("F3 every record comes from the engine: the form calls !dict_item for types, parse, layout, check and build, and never assigns a field of a record",
       all(("call !dict_item('%s'" % o) in form for o in ("types", "parse", "layout", "check", "build")) and re.search(r"\b(newrec|nr|rec)<", form) is None, "")
    ck("F4 an item the engine will not parse ends as `cannot` with the reason in words, BEFORE any form is made",
       ordered(form, "if pd # '' then", "res = 'cannot'", "newrec = ", "return", "loop\n      gosub make.form") and form.count("res = 'cannot'") == 1, "")
    ck("F5 the form ends with save, text, cancel or cannot and nothing else",
       sorted(set(re.findall(r"res = '(\w+)'", form))) == ["cancel", "cannot"] and "res = bt" in form and "bt = ev<2>" in form
       and "if bt = 'save' or bt = 'text' then" in form, "")
    ck("F6 Save and Edit as text end the form only when `build` accepted every row; otherwise the row is named in the err line and takes the focus",
       ordered(form, "on.button:", "call !dict_item('build', vals, rec, nr, be)", "if be = '' then", "newrec = nr", "res = bt", "act = 'done'", "else", "screen set f, 'err' text '! ' : be<2>", "screen focus f, be<1> else null"), "")
    ck("F7 a row is checked as the focus leaves it (check, then the err line; a good value is put back in its normal form)",
       ordered(form, "on.focus:", "lfk = ev<3>", "call !dict_item('check', ty, lfk, cv, ce)", "screen set f, lfk value cv", "screen set f, 'err' text '! '"), "")
    ck("F8 a change of type collects what was typed BEFORE it makes the form again, and only when the type is another one",
       ordered(form, "case ev<1> = 'change' and ev<2> = 'type'", "if types<tn> # ty then", "gosub collect", "vals{'type'} = types<tn>", "act = 'type'"), "")
    ck("F9 Esc or Cancel asks only when something was changed (the built record is not the old one, or the rows fail), and Keep editing leaves the form on the screen",
       ordered(form, "ask.discard:", "gosub collect", "call !dict_item('build', vals, rec, nr, be)", "if be = '' and nr = rec then", "res = 'cancel'", "screen msgbox", "if bq = 1 then", "res = 'cancel'"), "")
    ck("F10 the form is 140 by 43, a text row is a memo, every other row an entry with its own width and longest text, Save is the default button and Cancel the cancel button",
       "size 140,43" in form and "screen memo f, key" in form and "screen entry f, key at 26,y width ew value vals{key} maxlen em" in form
       and "screen button f, 'save', '&Save' at 26,38 default" in form and "screen button f, 'cancel', '&Cancel' at 62,38 cancel" in form, "")

    d = between(ide, "\ndo.dform:", "\nfields.enter:")
    ck("I1 do.dform refuses an empty editor, a tab that is not a dictionary item (11949) and a read-only tab, and keeps the editor's text first",
       ordered(d, "if nbuf = 0 then", "if bx{k} # 'dict' then", "msg = sysmsg(11949)", "gosub ro.check", "if not(ro.ok) then", "gosub stash.current", "df.rec = bx{k}"), "")
    ck("I2 it calls the form once, redraws, says why an item stays text (11950), and for save or text puts the record in the tab as the token form",
       d.count("call $dict_form(") == 1 and ordered(d, "call $dict_form(df.rec", "gosub redraw", "df.res = 'cannot'", "sysmsg(11950, ", "df.res = 'save' or df.res = 'text'",
                                                    "bx{k} = df.new", "gosub set.token.mode", "gosub load.current"), "")
    ck("I3 only `save` is written, by the IDE's own save, AFTER the text is in the tab; `text` and `cancel` write nothing",
       ordered(d, "gosub load.current", "if df.res = 'save' then", "gosub save.one") and d.count("gosub save.one") == 1 and d.count("save.current") == 0, "")
    ck("I4 the command dform is a case of run.cmd and the Go menu ends with the entry, which has no key", "case cmd = 'dform'" in ide and "gosub do.dform" in ide
       and src["go"].strip().endswith("|Dictionary item as for&m~~dform"), repr(src["go"][-60:]))
    ck("I5 the start word /form is taken off the sentence before any id is read, and the sentence is read once",
       ordered(ide, "sent.in = @sentence", "form0 = @true", "sent.in = trimb(sent.in[1, len(trimb(sent.in)) - 5])", "fn0 = field(sent.in, ' ', 2)") and ide.count("@sentence") == 1, repr(ide.count("@sentence")))
    ck("I6 IDE DICT file item /form opens the form after the record is open and before the main loop",
       ordered(ide, "gosub rc.untitled", "if form0 and nbuf > 0 then", "gosub redraw", "gosub do.dform", "menu.click = ''"), "")
    ck("I7 message 11949 says the tab is not a dictionary item; 11950 takes the item and the reason",
       "dictionary item" in src["m1"] and "%1" in src["m2"] and "%2" in src["m2"], "")
    return rows


def load():
    src = {}
    for k, p in FILES.items():
        with open(p, encoding="latin-1") as f:
            src[k] = f.read()
    others = {}
    for n in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, n)
        if n != "dict_form" and os.path.isfile(p):
            with open(p, encoding="latin-1") as f:
                others[n] = f.read()
    return src, others


def report(rows):
    bad = 0
    for name, ok, detail in rows:
        bad += 0 if ok else 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
    return bad


# (file key, name, old, new): each must match its file's text once and be caught
MUTANTS = [
    ("form", "the form writes a record", "   res = 'cancel'\n   newrec = rec\n", "   res = 'cancel'\n   newrec = rec\n   write rec to df, 'x'\n"),
    ("form", "the form assembles a record itself", "         newrec = nr\n         res = bt", "         newrec<2> = nr\n         res = bt"),
    ("form", "an item it cannot parse is shown anyway", "         res = 'cannot'\n         begin case", "         res = 'cancel'\n         begin case"),
    ("form", "Save does not ask the engine", "      call !dict_item('build', vals, rec, nr, be)\n      if be = '' then\n         newrec = nr", "      be = ''\n      nr = rec\n      if be = '' then\n         newrec = nr"),
    ("form", "a bad row does not take the focus", "         screen focus f, be<1> else null", "         null"),
    ("form", "a row is not checked as the focus leaves it", "         call !dict_item('check', ty, lfk, cv, ce)", "         ce = ''"),
    ("form", "a change of type forgets what was typed", "                     gosub collect\n                     vals{'type'} = types<tn>", "                     vals{'type'} = types<tn>"),
    ("form", "Esc always asks", "   if be = '' and nr = rec then", "   if 0 then"),
    ("form", "the form is smaller than the layout", "size 140,43", "size 100,30"),
    ("form", "Cancel is not the cancel button", "'&Cancel' at 62,38 cancel", "'&Cancel' at 62,38"),
    ("ide", "do.dform takes a tab that is not a dictionary item", "   if bx{k} # 'dict' then\n      msg = sysmsg(11949)", "   if 0 then\n      msg = sysmsg(11949)"),
    ("ide", "do.dform changes a read-only tab", "   gosub ro.check                       ;* a read-only tab (another session holds the record, bytes outside ASCII) is not changed", "   ro.ok = 1"),
    ("ide", "do.dform reads the tab before the editor's text is kept", "   gosub stash.current\n   df.u = bu<cb>", "   df.u = bu<cb>"),
    ("ide", "do.dform does not redraw", "   last.status = char(1)\n   gosub redraw\n   begin case\n      case df.res = 'cannot'", "   last.status = char(1)\n   begin case\n      case df.res = 'cannot'"),
    ("ide", "Edit as text writes the record too", "         if df.res = 'save' then\n            sv.i = cb", "         if df.res = 'save' or df.res = 'text' then\n            sv.i = cb"),
    ("ide", "the command is not a case of run.cmd", "      case cmd = 'dform'\n         gosub do.dform ", "      case cmd = 'dformx'\n         gosub do.dform "),
    ("ide", "/form is left on the sentence", "         sent.in = trimb(sent.in[1, len(trimb(sent.in)) - 5])", "         null"),
    ("ide", "the start form runs after the main loop begins", "   if form0 and nbuf > 0 then\n      gosub redraw ", "   if 0 then\n      gosub redraw "),
    ("go", "the menu entry has a key", "|Dictionary item as for&m~~dform", "|Dictionary item as for&m~F11~dform"),
]


def selftest():
    src, others = load()
    if any(not ok for _, ok, _ in checks(src, others)):
        print("REFUSING - the unmutated source already fails", file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: each mutation must be CAUGHT and match its text once ---")
    for fk, name, old, new in MUTANTS:
        n = src[fk].count(old)
        if n != 1:
            print("  [FAIL] %s: the text matches %d times in %s, not once" % (name, n, fk))
            holes += 1
            continue
        mut = dict(src)
        mut[fk] = src[fk].replace(old, new)
        caught = [x.split(" ")[0] for x, ok, _ in checks(mut, others) if not ok]
        print("  [%s] %s%s" % ("pass" if caught else "FAIL", name, ": caught by " + ", ".join(caught[:3]) if caught else ": NOT CAUGHT"))
        holes += 0 if caught else 1
    o2 = dict(others)
    o2["zz_clash"] = "$internal\nsubroutine zz_clash\n$catalog $dict_form\nend\n"
    caught = [x.split(" ")[0] for x, ok, _ in checks(src, o2) if not ok]
    print("  [%s] another program takes the catalogue name%s" % ("pass" if caught else "FAIL", ": caught by " + ", ".join(caught) if caught else ": NOT CAUGHT"))
    holes += 0 if caught else 1
    total = len(MUTANTS) + 1
    print("\n%d of %d mutants caught, %d missed" % (total - holes, total, holes))
    return 1 if holes else 0


def main():
    missing = [p for p in FILES.values() if not os.path.isfile(p)]
    if missing:
        print("test-dictform-units: CANNOT RUN - not readable: %s" % missing, file=sys.stderr)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    src, others = load()
    rows = checks(src, others)
    bad = report(rows)
    print("\nNOT MEASURED HERE: that the form shows what the engine says and the IDE saves what the form built.  That is sandbox-dictform.py.")
    print("test-dictform-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
