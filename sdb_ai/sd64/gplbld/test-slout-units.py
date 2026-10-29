#!/usr/bin/env python3
"""test-slout-units.py - the output pane widget $sl_out (S.88 phase 3.10, widget A), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-slout-units.py
  python3 .../test-slout-units.py --selftest

No sudo, no install, no sd, no compiler.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  The program is $internal and catalogued under its own name; it draws ONLY through $sl_put (no display, no screen
statement, no @() positioning); it is MEMORY ONLY (no file, no operating system verb, no EXECUTE, no printer); every CALL it makes has the
number of arguments the subroutine takes (a wrong count fails only at run time); entries go in newest first, the oldest are dropped
past 500 and counted in a last row; an entry is cleaned (CR, tab, the four marks) BEFORE it is kept; the text of an entry is cut off by
position, so a text holding a field mark survives; entries are wrapped at DRAW time with $tk_wrap (the rows cached by width and
history version); each kind has a text prefix; poll reads only waiting keys (KEYREADY before $sl_key), counts what it throws away
and answers Esc; progress is drawn at once; Esc and every unknown key are 'unhandled' and the pane never closes itself; a closed
pane or a phantom draws nothing; every message it cites exists, with its text, in the block 11179 and 11181-11185; and the
regress map names it ahead of the coarse sl_* rule.

***IT READS THE SOURCE AS TEXT AND DOES NOT RUN BASIC.***  That a refusal is whole on the screen at width 60, that the scroll keys move
the rows and that the progress line shows while a page is blocked is the suite tk-widgets.  A green run here is evidence that
nothing has deleted or reordered the code that makes those rows true.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and each mutation to
match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
MSGDIR = os.path.join(SDSYS, "messages")
MSGS = {"11179": "Output", "11181": "nothing to show yet", "11182": "Esc cancels", "11183": "%1 earlier lines dropped", "11184": "ok", "11185": "!!"}
ARGS = {"$sl_put": 5, "$tk_wrap": 3, "$sl_attr": 2, "$sl_scrollbar": 5, "$sl_progress": 5, "$sl_key": 2}          # the argument counts of the subroutines called
LABELS = ["geom", "geom.rows", "scrub", "add.entry", "set.progress", "poll.keys", "click", "handle.key", "clamp.top", "get.rows", "build.rows", "paint", "paint.prog"]


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def squeeze(t):
    return re.sub(r"\s+", " ", t).strip()


def nostr(t):
    """String literals taken out, so a word inside a quote (the 'open' of a collection key) is not read as a statement."""
    return re.sub(r"'[^']*'", "''", t)


def ordered(text, *parts):
    pos = -1
    for p in parts:
        k = text.find(p, pos + 1)
        if k < 0:
            return False
        pos = k
    return True


def body(c, label):
    """The text of one internal subroutine of the squeezed code, up to the next label."""
    i = c.find(" " + label + ": ")
    if i < 0:
        return ""
    rest = LABELS[LABELS.index(label) + 1:]
    j = len(c)
    for n in rest:
        k = c.find(" " + n + ": ", i + 1)
        if k >= 0:
            j = min(j, k)
    return c[i:j]


def call_counts(code):
    """[(name, argument count)] for every CALL $name(...) in the code."""
    res = []
    for m in re.finditer(r"\bcall\s+(\$[a-z_.]+)\s*\(", code):
        i = m.end()
        depth = 1
        n = 1
        q = None
        while i < len(code) and depth > 0:
            ch = code[i]
            if q:
                if ch == q:
                    q = None
            elif ch in "'\"":
                q = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 1:
                n += 1
            i += 1
        res.append((m.group(1), n))
    return res


def load():
    s = {"sl_out": read(os.path.join(GPL, "sl_out")),
         "regress-map": read(os.path.join(HERE, "regress-map.txt"))}
    s["msgs"] = {n: (read(os.path.join(MSGDIR, n)) if os.path.exists(os.path.join(MSGDIR, n)) else None) for n in MSGS}
    return s


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    raw = s["sl_out"]
    code = strip(raw)
    c = squeeze(code)
    cn = nostr(c)

    ck("S0 the source was found (the null case: nothing to read passes every row)", len(code) > 4000 and all(m is not None for m in s["msgs"].values()),
       "code %d bytes, messages %s" % (len(code), ",".join(n for n, m in s["msgs"].items() if m is None)))
    ck("S1 internal, catalogued under its own name, the widget contract", "$internal subroutine sl_out(op, w, scr, key, ret) $catalog $sl_out $include sl.h" in c and raw.count("$catalog $sl_out") == 1)

    # ---- draws only through $sl_put; memory only
    bad = [w for w in re.findall(r"\b(display|print|crt|screen|execute|perform|shell|open|openseq|openpath|openpu|write|writev|writet|writeseq|writeblk|weofseq|readseq|readblk|"
                                 r"osopen|osread|oswrite|osdelete|ospath|setptr|setpu|printer|dir|delete|deleteseq|readu|readv|input|inputat|hush|sh)\b", cn)]
    ck("S2 MEMORY ONLY: no file, operating system verb, execute or printer word in the code", not bad, ", ".join(sorted(set(bad))))
    ck("S3 it draws only through $sl_put: no display, no screen statement, no @() positioning", "@(" not in code and not re.search(r"\b(display|crt|print|screen)\b", cn)
       and len(re.findall(r"call \$sl_put\(", c)) >= 3)
    ck("S3b the only system() it asks is the phantom test", set(re.findall(r"system\((\d+)\)", c)) == {"25"} and c.count("system(25)") >= 3)

    # ---- every call has the right number of arguments
    cc = call_counts(code)
    wrong = [(n, k) for n, k in cc if n in ARGS and ARGS[n] != k]
    unknown = sorted(set(n for n, _ in cc) - set(ARGS))
    ck("S4 every CALL has the argument count of its subroutine (a wrong count stops only at run time)", cc and not wrong and not unknown,
       "wrong %s unknown %s" % (wrong, unknown))
    ck("S4b the calls it makes are exactly $sl_put $tk_wrap $sl_attr $sl_scrollbar $sl_progress $sl_key", set(n for n, _ in cc) == set(ARGS))

    # ---- the history
    add = body(c, "add.entry")
    ck("S5 an entry goes IN FRONT of the older ones (newest first)", "ents = kind : @sm : txt : @vm : ents" in add)
    ck("S5b a new entry puts the view back at the newest", "w{'top'} = 1" in add)
    ck("S6 the cap is 500 and the OLDEST entry (the last value) is the one dropped, counted in earlier",
       "$define OUT.CAP 500 " in c and ordered(add, "n = dcount(ents, @vm)", "loop while n > OUT.CAP do", "del ents<1, n>", "n -= 1", "w{'earlier'} = w{'earlier'} + 1", "repeat"))
    ck("S6b the dropped entries show as one last row with message 11183", ordered(body(c, "build.rows"), "next bi", "if w{'earlier'} + 0 > 0 then rows<-1> =", "sysmsg(11183, w{'earlier'} + 0)"))
    ck("S7 the entry is cleaned BEFORE it is kept", ordered(add, "gosub scrub", "w{'entries'} = ents"))
    sc = body(c, "scrub")
    ck("S7a a return is removed", "txt = change(txt, char(13), '')" in sc)
    ck("S7b a tab becomes blanks up to the next stop of eight", ordered(sc, "index(txt, char(9), 1)", "loop while tp > 0 do", "space(8 - mod(tp - 1, 8))", "repeat"))
    ck("S7c the four marks are shown as ^ ] | [ and none is kept", "txt = convert(@fm : @vm : @sm : @tm, '^]|[', txt)" in sc)
    ck("S7d the text is cut off by position, so a text holding a field mark survives", "kind = field(key, @fm, 1)" in add and "txt = key[len(kind) + 2, 999999]" in add and "key<2>" not in add)
    ck("S7e an unknown kind is out; the kinds are ok refuse info out", "if kind # 'ok' and kind # 'refuse' and kind # 'info' then kind = 'out'" in add)
    ck("S7f the progress text is cleaned too, and a line feed in it is a blank", ordered(body(c, "set.progress"), "gosub scrub", "txt = change(txt, char(10), ' ')"))
    ck("S7g an empty text is kept as a blank (it would wrap to no row and the entry would vanish)", "if txt = '' then txt = ' '" in add)

    # ---- wrapped at draw
    br = body(c, "build.rows")
    gr = body(c, "get.rows")
    ck("S8 each line is wrapped with $tk_wrap at draw time, and the width leaves the scroll bar and the lead", "call $tk_wrap(field(txt, char(10), li), ww, pcs)" in br and "ww = ow - 4" in gr)
    ck("S8b the wrapped rows are kept by width AND history version, and every change of the history bumps the version",
       "ck = ww : '/' : w{'ver'}" in gr and ordered(gr, "if w{'ckey'} = ck then", "rows = w{'rowcache'}", "gosub build.rows", "w{'rowcache'} = rows", "w{'ckey'} = ck")
       and "w{'ver'} = w{'ver'} + 1" in add and "w{'ver'} = w{'ver'} + 1" in c.split("case op = 'clear'")[1].split("end case")[0] and ordered(c, "case op = 'init'", "w{'ver'} = w{'ver'} + 1", "case op = 'draw'"))
    ck("S9 each kind has a text lead: ok and !! from messages 11184 and 11185, blanks for the rest; a refusal is in the bold style",
       "lead.ok = (sysmsg(11184) : ' ')[1, 2] : ' '" in br and "lead.bad = (sysmsg(11185) : ' ')[1, 2] : ' '" in br and       # squeeze() has made the blank runs one blank
 "lead1 = lead.bad" in br and "lead1 = lead.ok" in br
       and "if rw[1, 1] = 'r' then code = bd" in body(c, "paint") and "call $sl_attr('bold', bd)" in body(c, "paint"))
    ck("S9b only the first row of an entry carries the lead; the others are indented three", "if li = 1 and pj = 1 then lead = lead1" in br and "lead = ' '" in br and "lead1 = ' '" in br)
    pa = body(c, "paint")
    ck("S9c a scroll bar is drawn only when the rows do not fit, from $sl_scrollbar", "bar = (nrows > bh)" in pa and "if bar then call $sl_scrollbar(bh, top, nrows, bh, sbc)" in pa)
    ck("S9d an empty history says so with message 11181", "sysmsg(11181)" in pa and "nrows = 0 and r = 0" in pa)

    # ---- poll
    pk = body(c, "poll.keys")
    ck("S10 poll: a phantom answers 0 first; KEYREADY is tested BEFORE $sl_key; the loop is bounded", ordered(pk, "ret = 0", "if system(25) then return", "loop while keyready() and cnt < 50 do", "call $sl_key(1, pk)", "repeat"))
    ck("S10b poll: Esc is the answer, any other key is thrown away and counted in dropped, the end of the input ends the loop",
       ordered(pk, "if pk = '' then exit", "if pk = 'esc' then", "ret = 1", "end else", "w{'dropped'} = w{'dropped'} + 1", "end"))

    # ---- progress
    sp = body(c, "set.progress")
    ck("S11 progress is drawn AT ONCE: only its line when there was one, the whole pane when it appears", "if had then gosub paint.prog else gosub paint" in sp)
    ck("S11b progress is a percent from 0 to 100, from n of total, or n alone", ordered(sp, "pv = pn", "if pt > 0 then pv = int(pn * 100 / pt)", "if pv < 0 then pv = 0", "if pv > 100 then pv = 100"))
    ck("S11c a null key takes the line away and repaints", ordered(sp, "if key = '' then", "w{'prog'} = ''", "gosub geom.rows", "gosub paint", "return"))
    pp = body(c, "paint.prog")
    ck("S11d the bar is $sl_progress's own, on the last row; the title tells 'Esc cancels' while a line is on",
       "call $sl_progress('draw', pw, scr, '', pr)" in pp and "py = w{'ay'} + oh - 1" in pp and "if prog # '' then hint = sysmsg(11182) : ' '" in pa)

    # ---- keys: the page decides
    hk = body(c, "handle.key")
    ck("S12 the pane scrolls with up down pgup pgdn home end and answers every other key, Esc included, 'unhandled'",
       all(("case key = '%s'" % k) in hk for k in ("up", "down", "pgup", "pgdn", "home", "end")) and "case key = 'esc'" not in hk and ordered(hk, "case 1", "ret = 'unhandled' : @fm : key", "return", "end case"))
    ck("S12b a closed pane answers every key 'unhandled'", ordered(hk, "if not(isopen) then", "ret = 'unhandled' : @fm : key", "return", "end"))
    ck("S12c THE PANE NEVER CLOSES ITSELF: open is set to 0 in the 'close' op only", c.count("w{'open'} = 0") == 1 and ordered(c, "case op = 'close'", "w{'open'} = 0", "case op = 'open'"))
    ck("S12d the wheel scrolls three rows, a press is taken, a closed pane takes nothing", ordered(body(c, "click"), "ret = 'unhandled'", "if not(isopen) then return", "ret = 'handled'", "if key<1> = 'wheel' then", "top -= 3", "top += 3"))
    ck("S12e the top is kept inside the rows", ordered(body(c, "clamp.top"), "maxtop = nrows - bh + 1", "if maxtop < 1 then maxtop = 1", "if top > maxtop then top = maxtop", "if top < 1 then top = 1", "w{'top'} = top"))

    # ---- nothing drawn when it should not be
    ck("S13 a phantom and a closed pane draw nothing (paint and paint.prog both begin with the two tests)",
       pa.startswith(" paint: if system(25) then return if not(isopen) then return") and pp.startswith(" paint.prog: if system(25) then return if not(isopen) then return"))
    ck("S13b the size is never below 24 by 3", ordered(body(c, "geom"), "if ow < 24 then ow = 24", "if oh < 3 then oh = 3"))
    ck("S13c the init op keeps the history (a resize calls it again) and opens the pane", ordered(c, "case op = 'init'", "w{'open'} = 1", "case op = 'draw'") and "w{'entries'} = ''" not in c.split("case op = 'clear'")[0])

    # ---- the messages
    cited = set(re.findall(r"sysmsg\((\d+)", c))
    ck("S14 the messages it cites are exactly 11179 and 11181-11185", cited == set(MSGS), "cites %s" % sorted(cited))
    ck("S14b each message file has its text (one line, under 60 characters)",
       all(s["msgs"][n] is not None and s["msgs"][n].rstrip("\n") == t and len(t) < 60 for n, t in MSGS.items()),
       ",".join(n for n, t in MSGS.items() if s["msgs"][n] is None or s["msgs"][n].rstrip("\n") != t))
    ck("S14c none of them is in the Windows block 12000-12999, none is 11180", all(11000 <= int(n) < 12000 and n != "11180" for n in MSGS))

    # ---- the regress map
    mp = s["regress-map"]
    ml = [ln.split(":")[0].strip() for ln in mp.split("\n") if ln.strip() and not ln.lstrip().startswith("#")]
    def at(p):
        return ml.index(p) if p in ml else -1
    ck("S15 the map names sl_out before the coarse sl_* rule, and the suite tk-widgets",
       at("sdsys/gpl.bp/sl_out") >= 0 and at("sdsys/gpl.bp/sl_out") < at("sdsys/gpl.bp/sl_*") and re.search(r"^sdsys/gpl\.bp/sl_out\s*:\s*tk-widgets\s*$", mp, re.M) is not None)
    ck("S15b the map names the messages before the 117* rule",
       0 <= at("sdsys/messages/11179") < at("sdsys/messages/117*") and 0 <= at("sdsys/messages/1118[1-5]") < at("sdsys/messages/117*"))
    return rows


def M(name, which, old, new):
    return (name, which, old, new)


MUTANTS = [
    M("the newest entry goes last", "sl_out", "ents = kind : @sm : txt : @vm : ents", "ents = ents : @vm : kind : @sm : txt"),
    M("the cap is 5000", "sl_out", "$define OUT.CAP 500 ", "$define OUT.CAP 5000 "),
    M("the cap drops the newest", "sl_out", "del ents<1, n>", "del ents<1, 1>"),
    M("the dropped entries are not counted", "sl_out", "      w{'earlier'} = w{'earlier'} + 1\n", ""),
    M("the dropped row is never shown", "sl_out", "   if w{'earlier'} + 0 > 0 then rows<-1> = 'i' : '   ' : sysmsg(11183, w{'earlier'} + 0)\n", ""),
    M("an entry is kept without cleaning", "sl_out", "   gosub scrub\n   if txt = '' then txt = ' '", "   if txt = '' then txt = ' '"),
    M("a return is kept", "sl_out", "txt = change(txt, char(13), '')", "txt = txt"),
    M("a tab is kept", "sl_out", "loop while tp > 0 do", "loop while 0 do"),
    M("the marks are kept", "sl_out", "txt = convert(@fm : @vm : @sm : @tm, '^]|[', txt)", "txt = txt"),
    M("the text is read as a field", "sl_out", "txt = key[len(kind) + 2, 999999]", "txt = key<2>"),
    M("the text is not wrapped", "sl_out", "call $tk_wrap(field(txt, char(10), li), ww, pcs)", "pcs = field(txt, char(10), li)"),
    M("the wrap is wider than the pane", "sl_out", "ww = ow - 4 ", "ww = ow + 4 "),
    M("the cache ignores the history", "sl_out", "ck = ww : '/' : w{'ver'}", "ck = ww"),
    M("an add does not bump the version", "sl_out", "   w{'entries'} = ents\n   w{'ver'} = w{'ver'} + 1\n", "   w{'entries'} = ents\n"),
    M("clear does not bump the version", "sl_out", "         w{'ver'} = w{'ver'} + 1\n   end case", "   end case"),
    M("a refusal has no lead", "sl_out", "lead1 = lead.bad", "lead1 = '   '"),
    M("a refusal is not bold", "sl_out", "if rw[1, 1] = 'r' then code = bd", "if 0 then code = bd"),
    M("poll reads without asking KEYREADY", "sl_out", "loop while keyready() and cnt < 50 do", "loop while cnt < 50 do"),
    M("poll has no bound", "sl_out", "loop while keyready() and cnt < 50 do", "loop while keyready() do"),
    M("poll does not count what it throws away", "sl_out", "         w{'dropped'} = w{'dropped'} + 1\n", "         cnt += 0\n"),
    M("poll asks a phantom for a key", "sl_out", "   ret = 0\n   if system(25) then return\n   cnt = 0", "   ret = 0\n   cnt = 0"),
    M("the pane takes Esc", "sl_out", "      case key = 'home'\n         top = 1", "      case key = 'esc'\n         ret = 'done'\n      case key = 'home'\n         top = 1"),
    M("a key closes the pane", "sl_out", "      case key = 'down'\n         top += 1", "      case key = 'down'\n         w{'open'} = 0\n         top += 1"),
    M("a closed pane is drawn", "sl_out", "paint:\n   if system(25) then return\n   if not(isopen) then return\n", "paint:\n   if system(25) then return\n"),
    M("a phantom is drawn to", "sl_out", "paint:\n   if system(25) then return\n", "paint:\n"),
    M("the progress line is not drawn at once", "sl_out", "   if had then gosub paint.prog else gosub paint\n", ""),
    M("the progress is not kept to 100", "sl_out", "   if pv > 100 then pv = 100\n", ""),
    M("a null progress key does not clear", "sl_out", "      w{'prog'} = ''\n      gosub geom.rows\n      gosub paint\n      return", "      return"),
    M("the title is displayed", "sl_out", "   call $sl_put(scr, w{'ax'} + 0, w{'ay'} + 0, line, code)\n   * the rows", "   display line\n   * the rows"),
    M("the history is written to a file", "sl_out", "   w{'entries'} = ents\n   w{'ver'}", "   write ents to ofile, 'out.log'\n   w{'entries'} = ents\n   w{'ver'}"),
    M("$sl_progress is called with four arguments", "sl_out", "call $sl_progress('draw', pw, scr, '', pr)", "call $sl_progress('draw', pw, scr, '')"),
    M("$sl_put is called with four arguments", "sl_out", "call $sl_put(scr, w{'ax'} + 0, w{'ay'} + 1 + r, line, code)", "call $sl_put(scr, w{'ax'} + 0, w{'ay'} + 1 + r, line)"),
    M("the dropped row cites another message", "sl_out", "sysmsg(11183, w{'earlier'} + 0)", "sysmsg(11180, w{'earlier'} + 0)"),
    M("it is not $internal", "sl_out", "$internal\nsubroutine sl_out", "subroutine sl_out"),
    M("it is catalogued under another name", "sl_out", "$catalog $sl_out", "$catalog $sl_outx"),
    M("the size has no floor", "sl_out", "   if ow < 24 then ow = 24\n", ""),
    M("the map does not name sl_out", "regress-map", "sdsys/gpl.bp/sl_out          : tk-widgets\n", ""),
    M("the map does not name the message 11179", "regress-map", "sdsys/messages/11179         : tk-widgets\n", ""),
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
    try:
        s = load()
    except OSError as e:
        print("cannot read the sources: %s" % e, file=sys.stderr)
        sys.exit(2)
    rows = checks(s)
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-slout-units: %d checks, %d failed" % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
