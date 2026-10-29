#!/usr/bin/env python3
"""test-tkfaults-units.py - the known faults and loose ends of the toolkit's pages (task faults, 26 Oct 2026), as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tkfaults-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads BASIC and message files as text.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT A PAGE ENDS WHEN ITS INPUT ENDS, THAT A WINDOW IS REFUSED OR WHAT A
BOX IS TITLED ON THE SCREEN***: that is `sandbox-tk-faults.py` (a private SD; sessions on a closed pipe and on a pseudo-terminal; the disk and the screen as the evidence).  What a text check
is for here: the ORDER and the ABSENCE that an edit can move without a compile error.

  F1-F3  the largest window a page is given.  The measured fault: a session at 200 by 9999 (what the suites' plain sessions set so that nothing pages) sat at full CPU for minutes opening the
         screen of any toolkit page, because the library keeps the screen as one value to a row of one array (the cost grows with the square of the height).  $tk_open turns the window away
         BEFORE it takes the screen, after the minimum and the audience have been asked (a person who may not run an administrator page is told that at any size); message 11951 says it
         in the shape of 11197.
  F4-F5  $tk_confirm's optional sixth argument (the title): VAR.ARGS, tested through UNASSIGNED before it is used, the default "Run this command?" (11812) for both boxes it shows, and exactly
         the six places that write or delete a record instead of running a command pass one (11952 to 11955); every other call has five arguments, as before.
  F6     message 11865 ("Press Enter to return") is true after the page's own writes and after the home screen's: it names no screen.
  F7-F9  the review's low-severity defects that were plain: tool.query refuses the names . and .. and counts the lines a command printed without the one after its last line break; tool.bulk shows a VOC id
         through the control-character filter; the hints of tool.query and tool.test fit the width they are drawn into (F8); a new item id of tool.dict starts with a letter or a digit (F9).

--selftest breaks each invariant in the way an edit plausibly would and requires the named check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
MSG = os.path.join(SDSYS, "messages")
NAMES = ["tk.h", "tk_open", "tk_confirm", "tool_dict", "tool_query", "tool_bulk", "tool_test"]


def load():
    raw = {}
    for n in NAMES:
        try:
            with open(os.path.join(GPL, n), encoding="latin-1") as f:
                raw[n] = f.read()
        except OSError:
            raw[n] = ""
    for n in (11197, 11812, 11864, 11865, 11951, 11952, 11953, 11954, 11955):
        try:
            with open(os.path.join(MSG, str(n)), encoding="latin-1") as f:
                raw["m%d" % n] = f.read()
        except OSError:
            raw["m%d" % n] = ""
    # every other page of the toolkit: the null case of "no other call has a sixth argument"
    pages = {}
    for f in sorted(os.listdir(GPL)):
        if f.startswith("tool_") and f not in raw:
            with open(os.path.join(GPL, f), encoding="latin-1") as fh:
                pages[f] = fh.read()
    raw["pages"] = pages
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


def squeeze(t):
    return re.sub(r"\s+", " ", t).strip()


def ordered(text, *needles):
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def arg_lists(text, name):
    """for each `call <name>(...)` in TEXT: (the list of its top-level arguments, the label it stands under)"""
    out = []
    for m in re.finditer(r"call\s+" + re.escape(name) + r"\(", text):
        i, depth, cur, args, q = m.end(), 1, "", [], ""
        while i < len(text) and depth:
            c = text[i]
            if q:
                q = "" if c == q else q
                cur += c
            elif c in "'\"":
                q = c
                cur += c
            elif c == "(":
                depth += 1
                cur += c
            elif c == ")":
                depth -= 1
                if depth:
                    cur += c
            elif c == "," and depth == 1:
                args.append(cur.strip())
                cur = ""
            else:
                cur += c
            i += 1
        args.append(cur.strip())
        labs = re.findall(r"^([a-z][a-z.0-9]*):\s*$", text[:m.start()], re.M)
        out.append((args, labs[-1] if labs else ""))
    return out


LIT = re.compile(r"screen text (?:fmt\()?(['\"])((?:(?!\1).)*)\1(?:, *'(\d+)L')?\)? *at [^\n]*?width (\d+)")


def too_long(code):
    """(how many literal `screen text 'text' ... width n` there are, the ones whose text is longer than n)"""
    count, over = 0, []
    for line in code.split("\n"):
        m = LIT.search(line)
        if m:
            count += 1
            if len(m.group(2)) > int(m.group(4)):
                over.append((len(m.group(2)), int(m.group(4)), m.group(2)[:40]))
    return count, over


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    th, op_raw, cf_raw = raw["tk.h"], raw["tk_open"], raw["tk_confirm"]
    op, cf = squeeze(strip_bas(op_raw)), squeeze(strip_bas(cf_raw))
    td, tq, tb = strip_bas(raw["tool_dict"]), strip_bas(raw["tool_query"]), strip_bas(raw["tool_bulk"])
    ck("F0", "NULL CASE: tk.h, $tk_open, $tk_confirm, the three pages and the messages were found and are not trivially short (a check on nothing would pass)",
       len(th) > 1500 and len(op) > 800 and len(cf) > 800 and len(td) > 20000 and len(tq) > 20000 and len(tb) > 20000
       and all(raw["m%d" % n].strip() for n in (11197, 11812, 11864, 11865, 11951, 11952, 11953, 11954, 11955)) and len(raw["pages"]) >= 15,
       "%d %d %d %d %d %d, %d other pages" % (len(th), len(op), len(cf), len(td), len(tq), len(tb), len(raw["pages"])))

    # ---- the largest window
    ck("F1", "tk.h fixes the largest window a page is given: TK.MAXW 500 and TK.MAXH 300, each above the minimum (140 by 43) and defined once",
       re.findall(r"^\$define TK\.MAXW\s+(\d+)\b", th, re.M) == ["500"] and re.findall(r"^\$define TK\.MAXH\s+(\d+)\b", th, re.M) == ["300"]
       and re.search(r"\$define TK\.MINW\s+140\b", th) is not None and re.search(r"\$define TK\.MINH\s+43\b", th) is not None, "")
    ck("F2", "ORDER in $tk_open: a phantom is turned away, the minimum is asked, the audience is asked, THEN the window is asked for its size and the maximum applied, and only then the screen is taken - "
             "a window too big is refused before the screen is taken (taking it is what costs the time) and after the audience (so the administrator-only message is the same at every size)",
       ordered(op, "system(25)", "call $sl_need(", "K$ADMINISTRATOR", "call $sl_window(win.w, win.h)", "TK.MAXW", "TK.MAXH", "screen open", "call $tk_layout('open'"), "")   # 28 Oct 26 (S.88 L1): the lock is armed by $tk_layout 'open'
    ck("F3", "the refusal says message 11951 with the app, TK.MAXW, TK.MAXH and the size found, and RETURNS (it is a test of BOTH dimensions, either one over the limit refuses; no number is typed into the program)",
       re.search(r"if win\.w > TK\.MAXW or win\.h > TK\.MAXH then err = sysmsg\(11951, app, TK\.MAXW, TK\.MAXH, win\.w : ' by ' : win\.h\) return end", op) is not None
       and not re.search(r"\b(500|300|9999)\b", op)
       and raw["m11951"] == "%1 needs a window of at most %2 columns by %3 lines; this one is %4\n"
       and raw["m11197"].replace("at least", "at most") == raw["m11951"], repr(raw["m11951"]))

    # ---- $tk_confirm's title
    ck("F4", "$tk_confirm is VAR.ARGS with a sixth argument that is only ever read after UNASSIGNED() has been tested, in a nested IF (BASIC does not short-circuit): the default is message 11812 and "
             "the one title is given to BOTH boxes the routine shows (the Run / Cancel box and the box that asks for the name typed)",
       "subroutine tk_confirm(sentence, lines, typed, res, msg, boxtitle) var.args" in cf
       and cf.count("boxtitle") == 4 and ordered(cf, "ttl = sysmsg(11812)", "if not(unassigned(boxtitle)) then if boxtitle # '' then ttl = boxtitle end", "screen msgbox body title ttl buttons", "tt = ttl", "screen ask pr width fw title tt")
       and cf.count("sysmsg(11812)") == 1 and "title sysmsg(11812)" not in cf and " and boxtitle" not in cf and " or boxtitle" not in cf, "")
    want = {("tool_dict", "show.new"): ["sysmsg(11952)"], ("tool_query", "do.save"): ["sysmsg(11952)", "sysmsg(11952)"], ("tool_query", "delete.selected"): ["sysmsg(11953)"],
            ("tool_bulk", "do.apply"): ["sysmsg(11954)"], ("tool_bulk", "do.undo"): ["sysmsg(11955)"]}
    got = {}
    bad_count = []
    for page, text in (("tool_dict", td), ("tool_query", tq), ("tool_bulk", tb)):
        for args, lab in arg_lists(text, "$tk_confirm"):
            if len(args) == 6:
                got.setdefault((page, lab), []).append(args[5])
            elif len(args) != 5:
                bad_count.append((page, lab, len(args)))
    for page, text in raw["pages"].items():
        for args, lab in arg_lists(strip_bas(text), "$tk_confirm"):
            if len(args) == 6:
                got.setdefault((page, lab), []).append(args[5])
            elif len(args) != 5:
                bad_count.append((page, lab, len(args)))
    ck("F5", "EXACTLY the places that write or delete a record instead of running a command pass the title - tool.dict N (11952), tool.query S twice (11952) and X (11953), tool.bulk apply (11954) "
             "and undo (11955) - and every other call of $tk_confirm in the toolkit has five arguments, as before (the null case: all the other pages were read)",
       got == want and not bad_count, repr((got, bad_count)))

    # ---- 11865
    ck("F6", "message 11865 is \"Press Enter to return\" and names no screen: the pages that hand the terminal over come back to THEIR page, the home screen to the home screen; message 11864, the "
             "Terminal tile's banner, still names the home screen (it is true there)",
       raw["m11865"] == "Press Enter to return\n" and "home screen" not in raw["m11865"] and "home screen" in raw["m11864"],
       repr(raw["m11865"]))
    ck("F6b", "messages 11952 to 11955 are one line each, in the words the callers' boxes need",
       [raw["m%d" % n] for n in (11952, 11953, 11954, 11955)] == ["Write this record?\n", "Delete this record?\n", "Update these records?\n", "Put these records back?\n"],
       repr([raw["m%d" % n] for n in (11952, 11953, 11954, 11955)]))

    # ---- the review's plain defects
    cn = re.search(r"^check\.name:\n(.*?)^\s+return\n", tq, re.S | re.M)
    cn = cn.group(1) if cn else ""
    ck("F7", "tool.query: check.name refuses the two names of a directory (. and ..); the lines a command printed are counted without the empty one after its last line break; "
             "tool.bulk: a VOC id in the pick list goes through a control-character filter",
       "if fn = '.' or fn = '..' then okname = @false" in cn
       and ordered(squeeze(tq), "execute run.s trapping aborts capturing out", "if out[len(out), 1] = @fm then out = out[1, len(out) - 1]", "rl.n = dcount(out, @fm)")
       and "fl.text<-1> = fmt(convert(fctl, str('.', len(fctl)), cf)[1, 30], '30L')" in squeeze(tb) and "fl.text<-1> = fmt(cf[1, 30]" not in squeeze(tb)
       and ordered(squeeze(tb), "fctl = ''", "for fk0 = 1 to 31", "for fk0 = 127 to 255", "open 'VOC' to vocf then"), "")
    tt = strip_bas(raw["tool_test"])
    ck("F8", "the literal texts of tool.query and tool.test that are drawn with SCREEN TEXT ... WIDTH n fit n (the statement cuts the text at n: three hints of tool.query and the foot hint of tool.test were "
             "cut, the last in the middle of the Ctrl-C then Q instruction); the null case: tool.query has seventeen of them and tool.test one",
       too_long(tq)[0] >= 10 and too_long(tt)[0] >= 1 and not too_long(tq)[1] and not too_long(tt)[1], repr((too_long(tq), too_long(tt))))
    ta = re.search(r"case vk = 'id'\n(.*?)case vk = 'num'", td, re.S)
    ta = squeeze(ta.group(1)) if ta else ""
    ck("F9", "tool.dict: the id of a NEW item must start with a letter or a digit (. .. and a leading dash or dot are read as options or directories by some verbs), asked before the check that the id is taken",
       ordered(ta, "gosub check.word", "starting with a letter or a digit", "if index('abcdefghijklmnopqrstuvwxyz0123456789', askv[1, 1], 1) = 0 then vok = 0", "that id is taken"), ta[:200])
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if old not in r[key]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (key, old[:70]))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


MAXBLK = ("   call $sl_window(win.w, win.h)\n   if win.w > TK.MAXW or win.h > TK.MAXH then\n      err = sysmsg(11951, app, TK.MAXW, TK.MAXH, win.w : ' by ' : win.h)\n      return\n   end\n")


def move_max(raw):
    """the same block, but after the screen is taken and the cursor lock asked for"""
    r = dict(raw)
    t = r["tk_open"]
    lay = "   call $tk_layout('open', ctx, '', lay.chg)\n"          # 28 Oct 26 (S.88 L1): the layout and its cursor lock, after the screen is taken
    if MAXBLK not in t or lay not in t:
        raise KeyError("tk_open: the block to move is not there, so the mutant cannot be made")
    t = t.replace(MAXBLK, "", 1)
    t = t.replace(lay, lay + MAXBLK, 1)
    r["tk_open"] = t
    return r


def move_cap_first(raw):
    """the same block, in front of the audience test"""
    r = dict(raw)
    t = r["tk_open"]
    aud = "   if audience = 'admin' then\n"
    if MAXBLK not in t or t.count(aud) != 1:
        raise KeyError("tk_open: the block or the audience test is not there once, so the mutant cannot be made")
    r["tk_open"] = t.replace(MAXBLK, "", 1).replace(aud, MAXBLK + "\n" + aud, 1)
    return r


MUTANTS = [
    ("the window is not asked for its size before the screen", "F2", sub("tk_open", "   call $sl_window(win.w, win.h)\n", "")),
    ("the maximum is applied after the screen is taken", "F2", move_max),
    ("the maximum is applied before the audience", "F2", move_cap_first),
    ("only the height is limited", "F3", sub("tk_open", "if win.w > TK.MAXW or win.h > TK.MAXH then", "if win.h > TK.MAXH then")),
    ("only the width is limited", "F3", sub("tk_open", "if win.w > TK.MAXW or win.h > TK.MAXH then", "if win.w > TK.MAXW then")),
    ("the refusal does not return", "F3", sub("tk_open", "      err = sysmsg(11951, app, TK.MAXW, TK.MAXH, win.w : ' by ' : win.h)\n      return\n", "      err = sysmsg(11951, app, TK.MAXW, TK.MAXH, win.w : ' by ' : win.h)\n")),
    ("a limit is typed into the program", "F3", sub("tk_open", "if win.w > TK.MAXW or win.h > TK.MAXH then", "if win.w > TK.MAXW or win.h > 300 then")),
    ("the message says at least", "F3", sub("m11951", "at most", "at least")),
    ("the limit is raised in tk.h", "F1", sub("tk.h", "$define TK.MAXH        300", "$define TK.MAXH        9999")),
    ("the limit is lower than the minimum", "F1", sub("tk.h", "$define TK.MAXW        500", "$define TK.MAXW        100")),
    ("$tk_confirm is not VAR.ARGS", "F4", sub("tk_confirm", "boxtitle) var.args", "boxtitle)")),
    ("the title is read without asking whether it is there", "F4", sub("tk_confirm", "   if not(unassigned(boxtitle)) then\n      if boxtitle # '' then ttl = boxtitle\n   end", "   if boxtitle # '' then ttl = boxtitle")),
    ("the unassigned test and the read are one condition", "F4", sub("tk_confirm", "   if not(unassigned(boxtitle)) then\n      if boxtitle # '' then ttl = boxtitle\n   end",
                                                                        "   if not(unassigned(boxtitle)) and boxtitle # '' then\n      ttl = boxtitle\n   end")),
    ("the box that asks for the name has the old title", "F4", sub("tk_confirm", "      tt = ttl\n", "      tt = sysmsg(11812)\n")),
    ("the box has the old title whatever the caller says", "F4", sub("tk_confirm", "screen msgbox body title ttl buttons", "screen msgbox body title sysmsg(11812) buttons")),
    ("tool.dict N has the old title", "F5", sub("tool_dict", "call $tk_confirm(sent, lines, '', res, cmsg, sysmsg(11952))", "call $tk_confirm(sent, lines, '', res, cmsg)")),
    ("tool.dict N says it deletes", "F5", sub("tool_dict", "call $tk_confirm(sent, lines, '', res, cmsg, sysmsg(11952))", "call $tk_confirm(sent, lines, '', res, cmsg, sysmsg(11953))")),
    ("tool.query S (replace) has the old title", "F5", sub("tool_query", "call $tk_confirm(wsent, lines, qname, res, cmsg, sysmsg(11952))", "call $tk_confirm(wsent, lines, qname, res, cmsg)")),
    ("tool.query X has the write title", "F5", sub("tool_query", "call $tk_confirm(dsent, lines, lname, res, cmsg, sysmsg(11953))", "call $tk_confirm(dsent, lines, lname, res, cmsg, sysmsg(11952))")),
    ("tool.bulk apply has the old title", "F5", sub("tool_bulk", "call $tk_confirm(sent, lines, bf, res, cmsg, sysmsg(11954))", "call $tk_confirm(sent, lines, bf, res, cmsg)")),
    ("tool.bulk undo has the apply title", "F5", sub("tool_bulk", "call $tk_confirm(sent, lines, uf.name, res, cmsg, sysmsg(11955))", "call $tk_confirm(sent, lines, uf.name, res, cmsg, sysmsg(11954))")),
    ("a command's box is given a record title", "F5", sub("tool_bulk", "call $tk_confirm(sent, lines, '', res, cmsg)", "call $tk_confirm(sent, lines, '', res, cmsg, sysmsg(11954))")),
    ("a call has four arguments", "F5", sub("tool_dict", "call $tk_confirm(sent, lines, iid, res, cmsg)", "call $tk_confirm(sent, lines, res, cmsg)")),
    ("11865 names the home screen again", "F6", sub("m11865", "return\n", "return to the home screen\n")),
    ("11865 names the page", "F6", sub("m11865", "return\n", "return to the page\n")),
    ("11954 changed", "F6b", sub("m11954", "Update", "Change")),
    ("check.name takes the dots again", "F7", sub("tool_query", "   if fn = '.' or fn = '..' then okname = @false", "")),
    ("the last line break is counted again", "F7", sub("tool_query", "   if out[len(out), 1] = @fm then out = out[1, len(out) - 1]", "")),
    ("the pick list shows a VOC id as it is", "F7", sub("tool_bulk", "fmt(convert(fctl, str('.', len(fctl)), cf)[1, 30], '30L')", "fmt(cf[1, 30], '30L')")),
    ("a hint of tool.query is longer than its width again", "F8", sub("tool_query", "screen text 'Enter picks the item.  Space toggles it.' at 3,27 width 42", "screen text 'Enter picks the item.  Space turns it over, on and off.' at 3,27 width 42")),
    ("the foot hint of tool.test is longer than its line again", "F8", sub("tool_test", "Ctrl-C then Q stops one that does not end.\", '134L') at 3,20 width 134",
                                                                            "Ctrl-C then Q stops a test that does not end: there is no time limit.\", '134L') at 3,20 width 134")),
    ("a new item id may start with a dot", "F9", sub("tool_dict", "            if index('abcdefghijklmnopqrstuvwxyz0123456789', askv[1, 1], 1) = 0 then vok = 0\n", "")),
    ("the reason given for a refused id does not mention the first character", "F9", sub("tool_dict", "etxt = 'a-z, 0-9, dot, dash, underscore only, starting with a letter or a digit, and not an SD keyword'", "etxt = 'a-z, 0-9, dot, dash, underscore only, and not an SD keyword'")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:240]))
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
    print("test-tkfaults-units: tree %s" % os.path.dirname(GPL))
    if not raw["tk_open"] or not raw["tk_confirm"]:
        print("test-tkfaults-units: CANNOT RUN - the base is not there")
        return 2
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-tkfaults-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
