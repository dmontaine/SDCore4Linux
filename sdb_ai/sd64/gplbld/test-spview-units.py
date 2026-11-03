#!/usr/bin/env python3
"""test-spview-units.py - SP.VIEW's record view in the full-screen pages' look (S.99, 2 Nov 26), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-spview-units.py
  python3 .../test-spview-units.py --selftest [--from=N]

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.  Written 2 Nov 26.

WHAT THIS HOLDS.  `sdsys/gpl.bp/spview` (the program behind the sp.view verb) lays the record view out in ONE routine, set.look: on a
terminal whose size the kernel can read and that can address a cell (look.able), and on a window of at least 140 by 43 (a bigger one is
used whole), the pages' look - the bar on row 0 with "sp.view  user@account" at its right, the record from row 1, the prompt line, the
status line, the border and the key row at the bottom; otherwise the layout it always had (@CRTHIGH, @CRTWIDE), which is NOT refused.
The key row is made from a key table by $tk_keys and $tk_fkeys, and every key on it is one the command loop acts on.  The theme is the
site's (SCREENTHEME) while a record is shown and is given back when it is left.  The old layout's display statements are unchanged.  The
app name is given to $sl_put as a copy ($sl_put cuts the text it is given: SED's tag was emptied that way, 1 Nov 26).
2 Nov 26, V23-V25: the end of the input leaves SP.VIEW and its pick list (!PICK, `sdsys/gpl.bp/pick`, also read here) - a null key that
is not a timeout - and the spool form's INPUTs return on ER$EOF; it rang the bell for ever.  The runtime rows are sandbox-eofkeys.py's.

***WHAT THIS IS NOT.***  It cannot say the screen is right: that is sandbox-spview.py (a pseudo-terminal, the cells' colours, every old
key, a resize).  --selftest mutates the source and requires each mutant to be caught; --from=N runs the mutants from number N on.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPL = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp"))
SPVIEW = os.path.join(GPL, "spview")
PICK = os.path.join(GPL, "pick")          # 2 Nov 26: !PICK, SP.VIEW's pick list (V25)
PICK_SRC = None

# each key of the key row and what in the command loop acts on it: a K$ name in map.keys, or the letter of a case c = line
ROW_KEYS = {"pgdn": "K$PAGE.DOWN", "pgup": "K$PAGE.UP", "home": "K$HOME", "end": "K$END", "left": "K$LEFT", "right": "K$RIGHT",
            "s": "'S'", "x": "'X'", "q": "'Q'"}

# the old layout's statements, which a small window and a session with no terminal still get exactly
OLD_LINES = [
    "display @(0, info.line) : @(-13) : fmt(info.text, info.fmt) :",
    "display @(0,prompt.line) : fmt(data.prompt, info.fmt) : @(-14) :",
    "display @(0,prompt.line) : @(-13) : fmt(prompt.text, info.fmt) : @(-14) :",
    "display @(0,i-1) : @(-4) :",
    "display s[pan,@crtwide] :",
]


def code(src):
    """The lines with full-line comments dropped and a trailing ;* comment cut: a rule that exists only in a comment is no rule."""
    out = []
    for line in src.splitlines():
        if line.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s;\*.*$", "", line).rstrip())
    return "\n".join(out)


def routine(text, name):
    """The body of the label `name:` up to the next label at column 0 (None if there is no such label)"""
    m = re.search(r"(?m)^%s:[^\n]*\n(.*?)(?=^[A-Za-z][\w.]*:|\Z)" % re.escape(name), text, re.S)
    return m.group(1) if m else None


def at(text, s):
    return text.find(s) if text else -1


def checks(src):
    c = code(src)
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    sl = routine(c, "set.look") or ""
    si = routine(c, "show.item") or ""
    sd = routine(c, "show.data.page") or ""
    pf = routine(c, "paint.frame") or ""
    gk = routine(c, "get.key") or ""
    ti = routine(c, "theme.in") or ""
    to = routine(c, "theme.out") or ""
    sn = routine(c, "say.note") or ""
    mk = routine(c, "map.keys") or ""

    ck("V1 look.able is a terminal the kernel can size (K$WINSIZE not null) that can address a cell (cup)",
       "look.able = (kernel(K$WINSIZE, '') # '' and terminfo('cup') # '')" in c)
    ck("V2 set.look gives the pages' look only when look.able and the window ($sl_window) is at least LAY.WIDTH by LAY.DEPTH, 140 by 43",
       "call $sl_window(win.w, win.h)" in sl and "look = (look.able and win.w >= LAY.WIDTH and win.h >= LAY.DEPTH)" in sl
       and re.search(r"(?m)^\$define LAY\.WIDTH\s+140\b", c) and re.search(r"(?m)^\$define LAY\.DEPTH\s+43\b", c))
    ck("V3 the look uses the whole window and its rows: bar 0, lines from 1 (lay.h - 5 of them), prompt lay.h - 4, status lay.h - 3, border lay.h - 2, keys lay.h - 1",
       all(s in sl for s in ("lay.w = win.w", "lay.h = win.h", "view.w = lay.w", "data.row = 1", "data.lines.per.page = lay.h - 5",
                             "prompt.line = lay.h - 4", "info.line = lay.h - 3", "border.line = lay.h - 2", "key.line = lay.h - 1")))
    ck("V4 a smaller window, or no terminal, gets the old layout (not a refusal): @CRTWIDE, lines from row 0, @CRTHIGH - 4 of them, status and prompt at the foot",
       all(s in sl for s in ("view.w = @crtwide", "data.row = 0", "data.lines.per.page = @crthigh - 4", "prompt.line = @crthigh - 1",
                             "info.line = @crthigh - 2")) and "$sl_need" not in c and "$sl_guard" not in c)
    ck("V5 the old layout's display statements are there unchanged (the status line, the prompt, the lines)",
       all(s in c for s in OLD_LINES), [s for s in OLD_LINES if s not in c])
    ck("V6 show.item lays out (set.look) after the record is read and before the first page, and the theme is taken only on a terminal",
       0 <= at(si, "read rec from data.f, item.name") < at(si, "if look.able then gosub theme.in") < at(si, "gosub set.look") < at(si, "gosub show.data.page"))
    ck("V7 the theme is given back when the record is left: theme.out after the command loop of show.item",
       "if themed or look then gosub theme.out" in si and at(si, "repeat") < at(si, "gosub theme.out"))
    ck("V8 theme.in keeps a theme in force unless it is mono; then SCREENTHEME of sd.conf, else classic; theme.out sets the old one back, else mono, and clears plain",
       "call $sl_theme('name', '', '', '', '', old.theme)" in ti and "config('SCREENTHEME')" in ti
       and "if old.theme = '' or old.theme = 'mono' then" in ti and "call $sl_theme('set', 'classic', '', '', '', th.r)" in ti
       and "call $sl_theme('set', old.theme, '', '', '', th.r)" in to and "call $sl_theme('set', 'mono', '', '', '', th.r)" in to
       and "call $sl_sgr('n', sq)" in to and "look = @false" in to)
    ck("V9 the styles are the theme's roles: the bar, the prompt and the key row 'a' (bar), the record 't' (text), the status line the reverse role",
       "bar.attr = 'a'" in ti and "text.attr = 't'" in ti and "call $sl_theme('code', 'reverse', '', '', '', rev.attr)" in ti)
    ck("V10 the bar: the file and the record at the left and 'sp.view  user@account' at the right end of row 0, the tag given as a copy",
       "pf.app = 'sp.view  ' : @logname : '@' : @who : ' '" in pf and "pf.w = lay.w - len(pf.app)" in pf
       and "call $sl_put(scr, pf.w, 0, pf.app[1, len(pf.app)], bar.attr)" in pf and "call $sl_put(scr, 0, 0," in pf
       and "call $sl_put(scr, pf.w, 0, pf.app, " not in pf)
    adds = re.findall(r"call \$tk_keys\('add', kr\.keys, '([^']*)', '([^']*)', '([^']*)', '', ''\)", pf)
    keys = [a[0] for a in adds]
    ck("V11 the key row is made by $tk_fkeys from a table of $tk_keys rows, as wide as the window, and drawn on the key line in the bar style",
       len(adds) >= 5 and "kr.ctx<TK.C.W> = lay.w" in pf and "call $tk_fkeys(kr.ctx, kr.keys, '', key.row)" in pf
       and "call $sl_put(scr, 0, key.line, key.row, bar.attr)" in pf and at(pf, "kr.keys = ''") < at(pf, "$tk_keys('add'"), keys)
    missing = []
    for k in keys:
        want = ROW_KEYS.get(k)
        if want is None:
            missing.append(k + " (not a key this check knows)")
        elif want.startswith("K$"):
            if not re.search(r"case n = %s\s*;" % re.escape(want), mk):
                missing.append(k)
        elif ("case c = %s" % want) not in si and ("case (c = %s" % want) not in si:
            missing.append(k)
    ck("V12 every key on the row is one the command loop acts on (map.keys, or a case c = line of show.item), and the row has them all",
       not missing and sorted(keys) == sorted(ROW_KEYS), (missing, keys))
    ck("V13 the border is a line across the window on border.line",
       "call $sl_line('h', 0, pf.hc)" in pf and "call $sl_put(scr, 0, border.line, str(pf.hc, lay.w), text.attr)" in pf)
    ck("V14 show.data.page draws the frame and the lines through $sl_put in the look, from data.row, cut and padded to the window, and keeps the old loop otherwise",
       0 <= at(sd, "if look then") < at(sd, "gosub paint.frame") < at(sd, "call $sl_put(scr, 0, data.row + i - 1,") < at(sd, "display @(0,i-1) : @(-4) :")
       and "s = s[pan, view.w]" in sd and "if len(s) >= pan + view.w then more.right = @true" in sd)
    ck("V15 the status and prompt lines of the command loop go through $sl_put in the look and through the old displays otherwise",
       0 <= at(si, "if look then") < at(si, "call $sl_put(scr, 0, info.line,") < at(si, "rev.attr)") < at(si, "call $sl_put(scr, 0, prompt.line,")
       < at(si, "display @(0, info.line) : @(-13)"))
    ck("V16 a page across moves by the window's width less 20 (view.w), not by @CRTWIDE",
       "pan += view.w - 20" in si and "pan -= view.w - 20" in si and "@crtwide - 20" not in c)
    ck("V17 the command loop waits through get.key, and draws the page again when the window changed",
       "gosub get.key" in si and "if k.relaid then" in si and "c = upcase(keycode())" not in si
       and at(si, "if k.relaid then") < at(si, "gosub show.data.page\n         continue") < at(si, "c = upcase(c)"))
    ck("V18 get.key: a plain keycode() with no terminal; on one, keycode(1) and $sl_window once a second, set.look when the size changed",
       0 <= at(gk, "if not(look.able) then") < at(gk, "c = keycode()") < at(gk, "c = keycode(1)") < at(gk, "until c # '' or k.st # ER$TIMEOUT")
       < at(gk, "if win.w # last.w or win.h # last.h then") < at(gk, "gosub set.look") < at(gk, "k.relaid = @true"))
    ck("V19 the prompts of Q and X go through say.prompt / say.note: $sl_put in the look, the old reverse display otherwise",
       "call $sl_put(scr, 0, prompt.line, fmt(prompt.text[1, lay.w], lay.w : 'L'), bar.attr)" in sn
       and "display @(0,prompt.line) : @(-13) : fmt(prompt.text, info.fmt) : @(-14) :" in sn
       and c.count("display @(0,prompt.line) : @(-13) : fmt(prompt.text, info.fmt) : @(-14) :") == 1
       and c.count("gosub say.note") >= 4 and c.count("gosub say.prompt") >= 2)
    ck("V20 SP.VIEW is no toolkit page: it never calls the one-app routines ($tk_open, $tk_close, $tk_frame, $tk_menubar, $tk_help)",
       not re.search(r"\$tk_(open|close|frame|menubar|help)\b", c))
    ck("V21 the library's context is the program's own copy, with no clip (set.look), and every $sl_put draws on it",
       "call $sl_scr('get', scr)" in sl and "scr<SL.S.CLIP> = ''" in sl and "$sl_scr('put'" not in c
       and all(m.startswith("call $sl_put(scr,") for m in re.findall(r"call \$sl_put\([^,]*,", c)))
    di = routine(c, "delete.item") or ""
    ck("V22 X still asks the edit gate first (S.64): delete.item asks kernel(K$EDIT.OK) of the open file's path, says the refusal through "
       "say.note and returns, all before the question (say.prompt) and the lock (readvu)",
       0 <= at(di, "edit.p = fileinfo(data.f, FL$PATH)") < at(di, "if not(kernel(K$EDIT.OK, edit.p)) then")
       < at(di, "prompt.text = edit_msg(edit.kind)") < at(di, "gosub say.note") < at(di, "return")
       < at(di, "prompt.text = sysmsg(11105, item.name, file.name)") < at(di, "gosub say.prompt") < at(di, "readvu dummy from data.f"))
    # 2 Nov 26 (PROJECT_STATUS (95) follow-up 7): the end of the input leaves SP.VIEW; it rang the bell for ever at full CPU.
    ck("V23 the end of the input: get.key sets input.ended on a null key with no terminal (no timeout asked) and after the timeout loop on one; "
       "show.item leaves its loop before anything else looks at the key, and the pick list loop stops",
       re.search(r"c = keycode\(\)\n\s*if c = '' then input\.ended = @true\n\s*return", gk)
       and 0 <= at(gk, "until c # '' or k.st # ER$TIMEOUT") < at(gk, "repeat\n   if c = '' then input.ended = @true")
       and 0 <= at(si, "gosub get.key") < at(si, "if input.ended then exit") < at(si, "if k.relaid then")
       and re.search(r"gosub show\.item\n\s*if input\.ended then exit", c)
       and "input.ended = @false" in c)
    sp = routine(c, "spool.item") or ""
    ck("V24 the spool form's three INPUTs return when STATUS() is ER$EOF, before their value is used (an ended input used to loop there for ever)",
       len(re.findall(r"input @\([^)]*\) : (lptr|s|yn), \d_:\n\s*if status\(\) = ER\$EOF then return", sp)) == 3)
    pk = code(PICK_SRC) if PICK_SRC is not None else ""
    ck("V25 !PICK, SP.VIEW's pick list, ends with a null item on a null key (the end of the input), before map.keys",
       re.search(r"c = upcase\(keycode\(\)\)\n\s*if c = '' then\n\s*item = ''\n[^\n]*\n\s*exit\n\s*end\n\s*gosub map\.keys", pk))
    return out


def mutants(src):
    res = []

    def sub(label, old, new, count=1):
        if src.count(old) != count:
            res.append((label, None))
        else:
            res.append((label, src.replace(old, new)))

    sub("the look on any window (no size test)", "look = (look.able and win.w >= LAY.WIDTH and win.h >= LAY.DEPTH)", "look = look.able")
    sub("the look on a pipe as well", "look.able = (kernel(K$WINSIZE, '') # '' and terminfo('cup') # '')", "look.able = @true")
    sub("laid out for 140 by 42", "$define LAY.DEPTH     43", "$define LAY.DEPTH     42")
    sub("the key row on the status line's row", "key.line = lay.h - 1", "key.line = lay.h - 3")
    sub("the record from row 0 under the bar", "      data.row = 1\n", "      data.row = 0\n")
    sub("a small window refused", "   look = (look.able and win.w >= LAY.WIDTH",
        "   call $sl_need('sp.view', LAY.WIDTH, LAY.DEPTH, need.msg, '')\n   look = (look.able and win.w >= LAY.WIDTH")
    sub("the old status line lost", "         display @(0, info.line) : @(-13) : fmt(info.text, info.fmt) :\n", "")
    sub("the theme never given back", "   if themed or look then gosub theme.out", "   null")
    sub("the site theme ignored", "      site.theme = downcase(trim(config('SCREENTHEME')))", "      site.theme = ''")
    sub("a program's theme replaced", "   if old.theme = '' or old.theme = 'mono' then", "   if 1 then")
    sub("the app tag passed by reference", "call $sl_put(scr, pf.w, 0, pf.app[1, len(pf.app)], bar.attr)", "call $sl_put(scr, pf.w, 0, pf.app, bar.attr)")
    sub("no user@account at the right", "pf.app = 'sp.view  ' : @logname : '@' : @who : ' '", "pf.app = 'sp.view '")
    sub("a key on the row the loop ignores", "   call $tk_keys('add', kr.keys, 'q', 'quit', 'quit', '', '')",
        "   call $tk_keys('add', kr.keys, 'q', 'quit', 'quit', '', '')\n   call $tk_keys('add', kr.keys, 'f9', 'print', 'print', '', '')")
    sub("a key the loop acts on left off the row", "   call $tk_keys('add', kr.keys, 'x', 'delete', 'delete', '', '')\n", "")
    sub("the key row drawn as text", "call $sl_put(scr, 0, key.line, key.row, bar.attr)", "call $sl_put(scr, 0, key.line, key.row, text.attr)")
    sub("the status line in the bar style", "fmt(info.text[1, lay.w], lay.w : 'L'), rev.attr)", "fmt(info.text[1, lay.w], lay.w : 'L'), bar.attr)")
    sub("the pan by @CRTWIDE again", "            pan += view.w - 20", "            pan += @crtwide - 20")
    sub("no redraw on a resize", "      if k.relaid then", "      if 0 then")
    sub("get.key never looks at the window", "      if win.w # last.w or win.h # last.h then", "      if 0 then")
    sub("the Q prompt drawn the old way in the look", "            prompt.text = sysmsg(7136) ;* Press return to quit, any other key to continue\n            gosub say.prompt",
        "            prompt.text = sysmsg(7136) ;* Press return to quit, any other key to continue\n            display @(0,prompt.line) : @(-13) : fmt(prompt.text, info.fmt) : @(-14) :")
    sub("a toolkit app opened", "   kr.ctx = ''\n", "   kr.ctx = ''\n   call $tk_open('sp.view', '', kr.ctx, kr.err)\n")
    sub("the lines not cut to the window", "            s = s[pan, view.w]\n", "")
    sub("X deletes without asking the edit gate", "   if not(kernel(K$EDIT.OK, edit.p)) then", "   if 0 then")      # 2 Nov 26: V22
    # 2 Nov 26: the end of the input (V23 - V25)
    sub("no terminal: the null key not taken for the end", "      c = keycode()\n      if c = '' then input.ended = @true\n", "      c = keycode()\n")
    sub("a terminal: the null key after the loop not taken for the end", "   repeat\n   if c = '' then input.ended = @true", "   repeat\n   if 0 then input.ended = @true")
    sub("show.item does not leave on the end", "      if input.ended then exit             ;*", "      if 0 then exit             ;*")
    sub("the pick list loop goes on after the end", "         if input.ended then exit          ;*", "         if 0 then exit          ;*")
    sub("an ended input loops at Ok to print", "         if status() = ER$EOF then return      ;* 2 Nov 26: the input has ended; leave the form (it used to ask again for ever)", "         null ;* 2 Nov 26: the input has ended; leave the form (it used to ask again for ever)")
    if PICK_SRC is not None:
        old = "      if c = '' then                 ;* 2 Nov 26"
        res.append(("!PICK rings on at the end of the input", ("pick", PICK_SRC.replace(old, "      if 0 then                 ;* 2 Nov 26"))
                    if PICK_SRC.count(old) == 1 else None))
    return res


def main():
    if not os.path.isfile(SPVIEW):
        print("test-spview-units: CANNOT RUN - no %s" % SPVIEW)
        return 2
    src = open(SPVIEW, errors="replace").read()
    global PICK_SRC
    if not os.path.isfile(PICK):
        print("test-spview-units: CANNOT RUN - no %s" % PICK)
        return 2
    PICK_SRC = open(PICK, errors="replace").read()
    if "--selftest" in sys.argv:
        frm = 1
        for a in sys.argv[1:]:
            if a.startswith("--from="):
                frm = int(a.split("=", 1)[1])
        base = checks(src)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated source already fails:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(src)
        run = 0
        for k, (name, msrc) in enumerate(ms, 1):
            if k < frm:
                continue
            run += 1
            if msrc is None:
                print("  [NOT APPLIED] %d %s" % (k, name))
                bad += 1
                continue
            if isinstance(msrc, tuple):           # a mutant of !PICK: the spview source as it is, PICK_SRC mutated for this one
                keep, PICK_SRC = PICK_SRC, msrc[1]
                caught = [n for n, ok, _ in checks(src) if not ok]
                PICK_SRC = keep
            else:
                caught = [n for n, ok, _ in checks(msrc) if not ok]
            if caught:
                print("  [caught] %d %s  (%s)" % (k, name, caught[0][:40]))
            else:
                print("  [MISSED] %d %s" % (k, name))
                bad += 1
        if run == 0:
            print("selftest: CANNOT RUN - no mutant from %d (there are %d)" % (frm, len(ms)))
            return 2
        print("test-spview-units --selftest: %d mutant(s) run, %d not caught" % (run, bad))
        return 1 if bad else 0
    print("spview  : %s" % SPVIEW)
    res = checks(src)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail).replace("\n", " | ")[:200] + ")"))
        fails += 0 if ok else 1
    if not res:
        print("test-spview-units: no check ran - a broken test, not a pass")
        return 2
    print("test-spview-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
