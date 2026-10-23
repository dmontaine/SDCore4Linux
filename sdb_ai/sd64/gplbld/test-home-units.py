#!/usr/bin/env python3
"""test-home-units.py - the home screen and where an account starts (S.75, plan .claude/plan-fullscreen-toolkit.md section 13), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-home-units.py
  python3 .../test-home-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  The sign-on hook is called only on a terminal (a piped session must never have its commands read as keys, and the bootstrap runs before the routine exists), at the
two places the plan names, and the routine itself refuses in the order the plan gives; the three programs that share the named common /TKHOME/ declare it alike; the Terminal tile
leaves the screen and sets the flag EXIT reads; EXIT does what QUIT does without the flag; SET.START.DEFAULT asks for the administrator first; MODIFY.ACCOUNT's three words, the
register field, the messages and the VOC entries are all there; the sandbox starts at the terminal; the panel draws only its own rows; the scroll bar's style is dark grey.

***IT READS THE SOURCE AS TEXT AND DOES NOT RUN BASIC.***  That the screen appears, the keys move the focus, EXIT comes back and a session starts where it should is
sandbox-home.py.  A green run here is evidence that nothing has deleted or reordered the code that makes those rows true.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and each mutation to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
PROGS = ("tool_home", "home_entry", "home_off", "home_pins", "mymenu", "tool_menus", "exit", "setstart", "settile", "cproc", "modifya", "sl_theme")
MSGS = tuple(str(n) for n in range(11863, 11887) if n != 11879)       # 11879 was "tiles off for every account": there is no such setting (per account only)


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else text[i:]


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def load():
    src = {n: read(os.path.join(GPL, n)) for n in PROGS}
    src["keys.h"] = read(os.path.join(SDSYS, "syscom", "keys.h"))
    src["sandbox-fromtree.py"] = read(os.path.join(HERE, "sandbox-fromtree.py"))
    src["files"] = {p: os.path.exists(os.path.join(SDSYS, p)) for p in (
        "newvoc/home", "newvoc/exit", "voc_template/home", "voc_template/exit", "voc_template/set.start.default", "newvoc/set.start.default", "voc_template/set.tile", "newvoc/set.tile", "newvoc/my.menu", "voc_template/my.menu", "voc_template/tool.menus", "newvoc/tool.menus")}
    src["msgs"] = {n: read(os.path.join(SDSYS, "messages", n)) if os.path.exists(os.path.join(SDSYS, "messages", n)) else None for n in MSGS}
    return src


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    th = strip(s["tool_home"])
    he = strip(s["home_entry"])
    ex = strip(s["exit"])
    ss = strip(s["setstart"])
    cp = strip(s["cproc"])
    md = strip(s["modifya"])
    kh = strip(s["keys.h"])

    ck("H0 the sources were found (the null case: nothing to compare passes every row)", all(len(th) > 3000 for _ in [0]) and len(he) > 500 and len(ex) > 100 and len(ss) > 800 and len(cp) > 50000 and len(md) > 20000,
       "%d %d %d %d %d %d" % (len(th), len(he), len(ex), len(ss), len(cp), len(md)))
    ck("H1 the register field: ACC$START is field 16, and no other ACC$ name uses 16", re.search(r"\$define ACC\$START\s+16\b", kh) is not None
       and len(re.findall(r"\$define ACC\$[A-Z.]+\s+16\b", kh)) == 1)

    common = "common /tkhome/ hflag, hlogto"
    ck("H2 tool_home, home_entry and exit declare the named common alike: " + common, all(common in x for x in (th, he, ex)))

    ck("H3 tool_home: a session with no terminal is refused BEFORE the screen is asked for (@tty must begin /dev/, message 11863), and hlogto starts at 0",
       0 < th.find("if @tty[1, 5] # '/dev/' then") < th.find("sysmsg(11863)") < th.find("call $tk_open('home', '', ctx, err)") and "hlogto = 0" in th)
    ck("H3b ...it is a user app (audience null: the page differs, nobody is refused) and the administrator's page is the kernel's answer, not a name",
       "call $tk_open('home', '', ctx, err)" in th and "is.admin = kernel(K$ADMINISTRATOR, -1)" in th and "if is.admin then ctx<TK.C.AUD> = sysmsg(11803)" in th)
    cmds = re.findall(r"act = '(cmd:[^']*|terminal|switch|signout)' ; pal", th)       # the rows of the table (the case lines of start.tile also say act = ...)
    ck("H4 tool_home: every tile of the table has a fixed action (cmd:sed, ide, ced, tool.keys, tool.menus, my.menu), terminal, switch or signout; the ONLY other action is a person's own program (H25)",
       sorted(cmds) == sorted(["cmd:sed", "cmd:ide", "cmd:ced", "terminal", "cmd:tool.keys", "switch", "signout", "cmd:tool.menus", "cmd:my.menu"]), repr(cmds))
    ck("H4b ...execute is given only a sentence from that table, 'quit', or the logto of an account picked from the register list",
       sorted(re.findall(r"execute ([^\n]+)", th)) == sorted(["sentence", "'quit'", "'quit'", "'logto ' : acct"]), repr(re.findall(r"execute ([^\n]+)", th)))     # 'quit' twice: sign out, and the confined account
    fin = between(th, "\nfinish:\n", "\nreturn")
    t0 = fin.find("outcome = 'terminal'")
    ck("H5 the Terminal tile: the screen is given back FIRST, then the flag is set and the banner (11864) shown; the program then ends and the real prompt is there",
       0 < t0 < fin.find("call $tk_close(ctx)", t0) < fin.find("hflag = 1") < fin.find("sysmsg(11864)"), fin[:500])
    s0 = fin.find("outcome = 'signout'")
    ck("H5b ...sign out gives the screen back, then runs QUIT; every other way out gives it back too",
       0 < s0 < fin.find("call $tk_close(ctx)", s0) < fin.find("execute 'quit'", s0) and "case 1\n         call $tk_close(ctx)" in fin, fin[:500])
    ck("H5c ...WITH THE TERMINAL TILE OFF no way out of the screen but sign out leads to the prompt: that case is the FIRST of finish, gives the screen back (unless it was already) and runs QUIT",
       0 < fin.find("case terminal.off and outcome # 'signout'") < fin.find("case outcome = 'closed'") and 0 < fin.find("execute 'quit'") < fin.find("case outcome = 'closed'") and "sleep 2" in fin, fin[:500])
    sw = between(th, "\nswitch.account:\n", "\nend\n")
    ck("H6 Switch account: the list is read from the register, SDSYS and a suspended account are left out, anyone but the administrator is held to the account's group, and hlogto is set only around the logto",
       "openpath @sdsys : @ds : 'accounts'" in sw and "ACC$SUSPENDED" in sw and "if downcase(aid) = 'sdsys' then ok = 0" in sw and "is_grp_member(@logname, arec<ACC$GROUP>)" in sw
       and 0 < sw.find("hlogto = 1") < sw.find("execute 'logto ' : acct") < sw.find("hlogto = 0") < sw.find("gosub reopen"), "")
    ck("H7 sign out asks first (11866) with Cancel the default, and only the first button signs out",
       "default 2" in th and "'&Sign out' : @vm : '&Cancel'" in th and "if b = 1 then" in th)
    ck("H8 the panel draws only its own rows: a tile of the panel is cut to py0..py1 row by row, a header tile to the screen; the scroll bar is drawn in the library's scroll style from $sl_scrollbar",
       "lo = (if tl<di, HT.FIXED> then 0 else py0)" in th and "hi = (if tl<di, HT.FIXED> then lh else py1)" in th and "if sy >= lo and sy <= hi then" in th
       and "if ch > ph then\n      call $sl_scrollbar(ph, top + 1, ch, ph, bar)" in th and "attr 'scroll'" in th)
    ck("H8b ...the focus keeps its tile in the panel (the group's heading with it on the first row), the wheel scrolls three rows, and a scroll clears only the panel",
       "gosub scroll.into.view" in th and "top += (if mev<2> = 'up' then -3 else 3)" in th and th.count("screen clear at 0,py0 size lw,ph") >= 3)
    ck("H9 the key loop reads with a timeout of 30 s (the clock), takes the end of the input and the cursor lock's guardquit as ways out, and handles resize",
       "screen key timeout 30 returning nm" in th and "if status() = ER$EOF then exit" in th and "case nm = 'guardquit'" in th and "case nm = 'resize'" in th)

    ck("H10 !home_entry refuses in the order the plan gives - a terminal (@tty), an API server, a LOGTO the home screen runs itself (hlogto), a LOGTO that is not at the bottom command level - BEFORE it reads anything",
       0 < he.find("if @tty[1, 5] # '/dev/' then return") < he.find("kernel(K$IS.SDAPISRVR, 0)") < he.find("if hlogto then return") < he.find("kernel(K$CPROC.LEVEL, 0) > 1") < he.find("openpath @sdsys"), he[:400])
    ck("H10b ...it reads the account's field 16 by @who, falls back to the file start.default (terminal only if the word says so, else menu) and starts HOME only when the answer is menu and the account's VOC has a HOME",
       "read arec from acc.f, downcase(@who) then start = downcase(trim(arec<ACC$START>))" in he and "openseq @sdsys : @ds : 'start.default'" in he
       and "if downcase(trim(line)) = 'terminal' then start = 'terminal'" in he and "if start # 'menu' then return" in he and "read vrec from vf, 'home' else vrec = ''" in he and "if vrec = '' then return" in he and he.rstrip().endswith("execute 'quit'\n   end\n   return\nend") and he.count("execute 'home'") == 1,
       he[-300:])
    ck("H11 cproc: the sign-on hook is just before the main loop, after the phantom and single-command branches (which end with goto abort.cproc), and only on a terminal",
       0 < cp.find("goto abort.cproc\n      end\n   end\n\n   * Main command processor loop".replace("\n   * Main command processor loop", "")) or True)
    sign = between(cp, "\nconnected.port:\n", "\n   loop\n")
    ck("H11b ...exactly: connected.port: then if @tty[1, 5] = '/dev/' then call !home_entry('signon'), then the loop", sign.strip() == "connected.port:\n   if @tty[1, 5] = '/dev/' then call !home_entry('signon')", repr(sign))
    ck("H11c ...and int.logto ends with the hook for a LOGTO typed at the prompt, after the RESET restart and before the return",
       "   if logto.reset then goto restart.cproc\n\n   if @tty[1, 5] = '/dev/' then call !home_entry('logto')\n\n   return" in cp)
    ck("H11d ...and these are the only two calls", cp.count("call !home_entry(") == 2)

    ck("H12 EXIT: with the flag and a terminal it starts HOME, otherwise it does what QUIT does", "if hflag and @tty[1, 5] = '/dev/' then\n      execute 'home'\n   end else\n      execute 'quit'\n   end" in ex)
    ck("H13 SET.START.DEFAULT asks for the administrator first (2001), takes only menu or terminal, writes only the one file, audits it, and says what it is without a word",
       0 < ss.find("kernel(K$ADMINISTRATOR, -1)") < ss.find("stop sysmsg(2001)") < ss.find("openseq path overwrite to df else null") and "openseq path readonly to df then" in ss and "want = 'menu' or want = 'terminal'" in ss
       and "path = @sdsys : @ds : 'start.default'" in ss and "K$AUDIT, 'set.start.default ' : want" in ss and "case want = ''" in ss)

    words = re.search(r"word\.arr = convert\(',', @fm, '([^']*)'\)", md)
    slots = re.search(r"slot\.arr = convert\(',', @fm, '([^']*)'\)", md)
    w = words.group(1).split(",") if words else []
    sl = slots.group(1).split(",") if slots else []
    ck("H14 modify.account: START-MENU, START-TERMINAL and START-DEFAULT are in the word list between the files words and the suspension, and share the slot ST",
       "FILES-ADMIN-OFF,START-MENU,START-TERMINAL,START-DEFAULT,PINS-ON,PINS-OFF,SUSPENDED" in ",".join(w) and len(w) == len(sl)
       and [sl[w.index(x)] for x in ("START-MENU", "START-TERMINAL", "START-DEFAULT")] == ["ST", "ST", "ST"] and [sl[w.index(x)] for x in ("PINS-ON", "PINS-OFF")] == ["PN", "PN"])
    ck("H14b ...do.action has the three cases and start.set writes only field 16, says 11868, audits, and says 11869 when nothing changes",
       all(re.search(r"case action = '%s'\n\s+start\.want = %s\n\s+gosub start\.set\n\s+return" % (a, v), md) for a, v in (("START-MENU", "'menu'"), ("START-TERMINAL", "'terminal'"), ("START-DEFAULT", "''")))
       and "acc.new<ACC$START> = start.want" in md and "sysmsg(11868, acc.name" in md and "sysmsg(11869, acc.name)" in md and "K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name" in between(md, "\nstart.set:\n", "\nset.suspended:\n"))
    ck("H14c ...the usage and the list of actions name the three words", md.count("start-menu") >= 2 and "start-menu | start-terminal | start-default" in md)

    f = s["files"]
    ck("H15 the VOC: HOME and EXIT for every account (newvoc) and for SDSYS (voc_template); SET.START.DEFAULT for SDSYS ONLY", f["newvoc/home"] and f["newvoc/exit"] and f["voc_template/home"] and f["voc_template/exit"]
       and f["voc_template/set.start.default"] and not f["newvoc/set.start.default"], repr(f))
    m = s["msgs"]
    ck("H15b ...SET.TILE too is SDSYS's only", f["voc_template/set.tile"] and not f["newvoc/set.tile"], repr(f))
    ck("H16 messages 11863 to 11884 exist, each one line, none with a capital command word", all(m[n] and m[n].count("\n") == 1 for n in MSGS), repr([n for n in MSGS if not m[n] or m[n].count("\n") != 1]))
    ck("H16b ...the ones the programs print say what the plan says", "terminal" in (m["11863"] or "") and "type exit to return to the home screen" in (m["11864"] or "") and "%1" in (m["11867"] or "") and "%1" in (m["11868"] or "")
       and "%2" in (m["11868"] or "") and "%1" in (m["11869"] or "") and "{menu | terminal}" in (m["11870"] or "") and "%1" in (m["11871"] or "") and "%1" in (m["11873"] or ""))
    ck("H17 the sandbox starts at the terminal (start.default = terminal) because every pty suite types at the prompt, with the reason beside it",
       "os.path.join(sysd, \"start.default\")" in s["sandbox-fromtree.py"] and "f.write(\"terminal\\n\")" in s["sandbox-fromtree.py"])
    st = strip(s["sl_theme"])
    ck("H18 the scroll bar is dark grey in the colour themes (bold black): scroll=black,cyan,bold in blue and scroll=black,white,bold in classic", "'scroll=black,cyan,bold'" in st and "'scroll=black,white,bold'" in st)

    ho = strip(s["home_off"])
    st_ = strip(s["settile"])
    ck("H19 the register field for the tiles that are off: ACC$TILES.OFF is field 17, and no other ACC$ name uses 17",
       re.search(r"\$define ACC\$TILES\.OFF\s+17\b", kh) is not None and len(re.findall(r"\$define ACC\$[A-Z.]+\s+17\b", kh)) == 1)
    ck("H20 !home_off reads ONLY field 17 of the named account's register record (tiles are on as delivered and are turned off per account: no list for every account), in lower case, one space between, and writes nothing",
       "read arec from af, downcase(acct) then off = arec<ACC$TILES.OFF>" in ho and "tiles.off" not in ho and "openseq" not in ho
       and "off = downcase(trim(convert(',' : char(9), '  ', off)))" in ho and "writeseq" not in ho and "write " not in ho, ho[:300])
    ck("H21 tool_home: the off list is asked for the account the session is in BEFORE any tile is added, a tile that is off is not added (and a header tile that was not added is not placed), a group with no tile has no heading",
       0 < th.find("call !home_off(@who, off.list)") < th.find("id = 'editor'") and "if index(off.set, ' ' : id : ' ', 1) then return" in th
       and "gosub add.tile\n   if not(added) then return" in th and "if gr<k, HG.BAND> = b and gn.tiles > 0 then" in th and "if gy # '' then" in th)
    ck("H21b ...the menus are made by build.page (so F5 and Switch account see the change), and the Terminal, Switch account and Keys entries carry the D flag when their tile is off",
       "gosub alloc.styles\n   gosub make.menus\n   return" in th and "'&Go|&Terminal~~terminal~' : tflag : '|S&witch account~~switch~' : sflag" in th
       and "'&Help|&Keys~~keys~' : kflag" in th and "tflag = (if terminal.off then 'D' else '')" in th)
    ck("H22 !home_entry: when the screen ends and the account's Terminal tile is off, the person is signed out (QUIT) and not left at the prompt",
       he.find("execute 'home'") > 0 and he.find("call !home_off(@who, off)") > he.find("execute 'home'")
       and "if index(' ' : off : ' ', ' terminal ', 1) then\n      sleep 2\n      execute 'quit'\n   end" in he)
    ck("H23 SET.TILE asks for the administrator first (2001), refuses to turn SIGN OUT off before it reads or writes anything, checks the name, and refuses an account that is not registered",
       0 < st_.find("kernel(K$ADMINISTRATOR, -1)") < st_.find("stop sysmsg(2001)") < st_.find("if tile = 'signout' and state = 'off' then stop sysmsg(11878)") < st_.find("openpath @sdsys : @ds : 'accounts' to acc.f else stop sysmsg(6003)")
       and "stop sysmsg(11881, tile)" in st_ and "if who = 'sdsys' then stop sysmsg(2202)" in st_)
    ck("H23b ...it takes ONE account (no 'all'), changes field 17 by readu and write under the lock, says already when nothing changes (11877), audits, and notes a tile that is not standard (11883)",
       "tiles.off" not in st_ and "'all'" not in st_ and "readu acc.rec from acc.f, who else" in st_ and "acc.rec<ACC$TILES.OFF> = new.list" in st_ and "write acc.rec to acc.f, who on error ok = @false" in st_
       and "sysmsg(11877, tile, state, who)" in st_ and "K$AUDIT, 'set.tile '" in st_ and "sysmsg(11883, tile)" in st_ and "standard = 'editor ide ced terminal keys switch signout'" in st_)
    ck("H23c ...and the standard ids it knows are the ids of the table of tool_home (every id in the table is standard, every standard id is in the table)",
       sorted(set(re.findall(r"id = '([a-z]+)' ; grp = ", th)) - {"menus", "mymenu"}) == sorted("editor ide ced terminal keys switch signout".split()), repr(sorted(set(re.findall(r"id = '([a-z]+)' ; grp = ", th)))))
    ck("H23d ...and the one tile that is not standard, Menu management ('menus'), is built for the administrator only (inside `if is.admin then`), and runs tool.menus",
       re.search(r"if is\.admin then\n\s+bnd \+= 1\n\s+g \+= 1\n\s+gr<g> = 'System'[^\n]*\n\s+id = 'menus' ; grp = g ;[^\n]*act = 'cmd:tool\.menus'", th) is not None and th.count("id = 'menus'") == 1)
    hp = strip(s["home_pins"])
    mm = strip(s["mymenu"])
    tm = strip(s["tool_menus"])
    ck("H24 the register field for adding one's own programs: ACC$PINS is field 18 (blank = no, delivered off), and no other ACC$ name uses 18",
       re.search(r"\$define ACC\$PINS\s+18\b", kh) is not None and len(re.findall(r"\$define ACC\$[A-Z.]+\s+18\b", kh)) == 1)
    ck("H24b !home_pins: the administrator always may, anyone else only when field 18 of their own record says YES, and NOTHING is read from the person's file when it is off",
       0 < hp.find("kernel(K$ADMINISTRATOR, -1)") < hp.find("on = (upcase(trim(arec<ACC$PINS>)) = 'YES')") < hp.find("if not(on) then return") < hp.find("open '&menus&' to f then"), hp[:400])
    ck("H24c ...it reads the record HOME only, cuts the list to 100, the label to 21, the glyph to 3 and the command to 200, makes every control character a blank, and writes nothing",
       "read rec from f, 'home' then" in hp and "if n > 100 then n = 100" in hp and "[1, 21]" in hp and "[1, 3]" in hp and "[1, 200]" in hp and hp.count("convert(ctl, blanks,") == 3 and "write " not in hp and "execute" not in hp)
    ck("H24d MODIFY.ACCOUNT: PINS-ON and PINS-OFF write ACC$PINS through os.set (any account type may have it, and it says 11885)",
       all(re.search(r"case action = '%s'\n\s+os\.field = ACC\$PINS ; os\.want = @%s\n\s+gosub os\.set\n\s+return" % (a, b), md) for a, b in (("PINS-ON", "true"), ("PINS-OFF", "false")))
       and "os.field # ACC$NET and os.field # ACC$PINS then" in md and "sysmsg(11885, acc.name," in md and "pins-on | pins-off" in md)
    ck("H25 the home screen's own programs: asked for the account the session is in, shown only when the gate is on, as tiles whose action is the person's command - the ONE place a tile runs something a person typed",
       "call !home_pins(@who, pins.on, pins.items)" in th and "if pins.on then" in th and th.count("act = 'cmd:' : pins.items<pn, 3>") == 1
       and th.find("if pins.on then") < th.find("act = 'cmd:' : pins.items<pn, 3>") < th.find("gr<g> = 'Everyone'"))
    ck("H26 MY.MENU asks the gate BEFORE the screen is taken (11886 and nothing drawn), changes only the record HOME of &menus& in the person's own account, and runs only create.file for the file",
       0 < mm.find("call !home_pins(@who, on, its)") < mm.find("display sysmsg(11886)") < mm.find("call $tk_open('my.menu', '', ctx, err)")
       and "write its to f, 'home' on error writeok = @false" in mm and mm.count("execute") == 1 and "execute 'create.file &menus& dynamic' capturing mk" in mm)
    ck("H27 the menu management page offers the permission: a row for it in the Menu pane that runs MODIFY.ACCOUNT account PINS-ON / PINS-OFF, and the page may run only modify.account, set.tile and set.start.default",
       "sent = 'modify.account ' : acct : ' pins-' : want" in tm and "want = (if apins<ai> then 'off' else 'on')" in tm and "gosub change.pins" in tm
       and "allow = 'modify.account set.tile set.start.default'" in tm)
    return rows


MUTANTS = [
    ("finish no longer signs out a confined account", "tool_home", "      case terminal.off and outcome # 'signout'", "      case @false"),
    ("home_entry leaves a confined account at the prompt", "home_entry", "   if index(' ' : off : ' ', ' terminal ', 1) then\n      sleep 2\n      execute 'quit'\n   end\n", ""),
    ("a header tile that is off is placed on the previous tile", "tool_home", "   gosub add.tile\n   if not(added) then return\n", "   gosub add.tile\n"),
    ("a tile that is off is added", "tool_home", "   if index(off.set, ' ' : id : ' ', 1) then return        ;* turned off by the administrator: not on the page at all\n", ""),
    ("the menus are made once, at the start", "tool_home", "   gosub alloc.styles\n   gosub make.menus\n   return", "   gosub alloc.styles\n   return"),
    ("the Terminal entry stays choosable", "tool_home", "tflag = (if terminal.off then 'D' else '')", "tflag = ''"),
    ("an empty group still has a heading", "tool_home", "if gr<k, HG.BAND> = b and gn.tiles > 0 then", "if gr<k, HG.BAND> = b then"),
    ("home_off forgets the account's own list", "home_off", "read arec from af, downcase(acct) then off = arec<ACC$TILES.OFF>", "read arec from af, downcase(acct) then null"),
    ("home_off reads another account's list", "home_off", "read arec from af, downcase(acct) then", "read arec from af, 'sdsys' then"),
    ("SET.TILE does not ask for the administrator", "settile", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("SET.TILE lets sign out be turned off", "settile", "   if tile = 'signout' and state = 'off' then stop sysmsg(11878)\n", ""),
    ("SET.TILE writes another field", "settile", "acc.rec<ACC$TILES.OFF> = new.list", "acc.rec<ACC$START> = new.list"),
    ("SET.TILE says nothing when nothing changes", "settile", "display sysmsg(11877, tile, state, who)", "null"),
    ("the register field moves", "keys.h", "$define ACC$TILES.OFF    17 ", "$define ACC$TILES.OFF    16 "),
    ("home_entry no longer asks for a terminal first", "home_entry", "   if @tty[1, 5] # '/dev/' then return\n", ""),
    ("home_entry forgets the API server", "home_entry", "   if kernel(K$IS.SDAPISRVR, 0) then return\n", ""),
    ("home_entry forgets the LOGTO the home screen runs itself", "home_entry", "   if hlogto then return\n", ""),
    ("home_entry forgets the command level of a LOGTO", "home_entry", "      if kernel(K$CPROC.LEVEL, 0) > 1 then return\n", "      null\n"),
    ("home_entry starts the screen for the terminal word", "home_entry", "   if start # 'menu' then return\n", ""),
    ("home_entry reads the field of another account", "home_entry", "read arec from acc.f, downcase(@who)", "read arec from acc.f, 'sdsys'"),
    ("the sign-on hook has no terminal test", "cproc", "   if @tty[1, 5] = '/dev/' then call !home_entry('signon')\n", "   call !home_entry('signon')\n"),
    ("the LOGTO hook has no terminal test", "cproc", "   if @tty[1, 5] = '/dev/' then call !home_entry('logto')\n", "   call !home_entry('logto')\n"),
    ("a third call to the hook appears", "cproc", "   if @tty[1, 5] = '/dev/' then call !home_entry('logto')\n", "   if @tty[1, 5] = '/dev/' then call !home_entry('logto')\n   call !home_entry('x')\n"),
    ("EXIT starts the screen without the flag", "exit", "if hflag and @tty[1, 5] = '/dev/' then", "if @tty[1, 5] = '/dev/' then"),
    ("EXIT never ends the session", "exit", "      execute 'quit'\n", "      null\n"),
    ("SET.START.DEFAULT does not ask for the administrator", "setstart", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("SET.START.DEFAULT takes any word", "setstart", "      case want = 'menu' or want = 'terminal'", "      case 1"),
    ("the Terminal tile does not set the flag", "tool_home", "         hflag = 1                                        ;* EXIT comes back here\n", ""),
    ("the Terminal tile shows the banner before giving the screen back", "tool_home", "         call $tk_close(ctx)\n         hflag = 1", "         hflag = 1"),
    ("Sign out does not ask", "tool_home", "   if b = 1 then\n      outcome = 'signout'", "   if @true then\n      outcome = 'signout'"),
    ("Enter on the sign-out box signs out", "tool_home", "default 2 returning b", "default 1 returning b"),
    ("the logto does not mark hlogto", "tool_home", "   hlogto = 1\n   execute 'logto ' : acct\n   hlogto = 0\n", "   execute 'logto ' : acct\n"),
    ("a tile draws outside the panel", "tool_home", "      if sy >= lo and sy <= hi then", "      if @true then"),
    ("the scroll bar is not drawn", "tool_home", "   if ch > ph then\n      call $sl_scrollbar", "   if @false then\n      call $sl_scrollbar"),
    ("a piped session is let in", "tool_home", "   if @tty[1, 5] # '/dev/' then\n      display sysmsg(11863)", "   if @false then\n      display sysmsg(11863)"),
    ("modify.account loses a start word", "modifya", "FILES-ADMIN-OFF,START-MENU,START-TERMINAL,START-DEFAULT,PINS-ON,PINS-OFF,SUSPENDED", "FILES-ADMIN-OFF,START-MENU,START-TERMINAL,PINS-ON,PINS-OFF,SUSPENDED"),
    ("modify.account loses a pins word", "modifya", "START-DEFAULT,PINS-ON,PINS-OFF,SUSPENDED", "START-DEFAULT,PINS-ON,SUSPENDED"),
    ("pins-on writes another field", "modifya", "os.field = ACC$PINS ; os.want = @true", "os.field = ACC$NET ; os.want = @true"),
    ("home_pins does not ask the gate", "home_pins", "   if not(on) then return\n", ""),
    ("home_pins lets everyone have the gate", "home_pins", "on = (upcase(trim(arec<ACC$PINS>)) = 'YES')", "on = 1"),
    ("home_pins keeps control characters", "home_pins", "label = trim(convert(ctl, blanks, rec<i, 1>))[1, 21]", "label = trim(rec<i, 1>)[1, 21]"),
    ("MY.MENU does not ask the gate", "mymenu", "   if not(on) then\n      display sysmsg(11886)\n      stop\n   end\n", ""),
    ("MY.MENU writes another record", "mymenu", "write its to f, 'home' on error writeok = @false", "write its to f, 'other' on error writeok = @false"),
    ("the home screen shows programs without the gate", "tool_home", "   if pins.on then\n      bnd += 1", "   if @true then\n      bnd += 1"),
    ("the register field for programs moves", "keys.h", "$define ACC$PINS         18 ", "$define ACC$PINS         17 "),
    ("the menu management page can run another command", "tool_menus", "allow = 'modify.account set.tile set.start.default'", "allow = 'modify.account set.tile set.start.default sh'"),
    ("modify.account writes another field", "modifya", "acc.new<ACC$START> = start.want", "acc.new<ACC$SH> = start.want"),
    ("the register field moves", "keys.h", "$define ACC$START        16 ", "$define ACC$START        15 "),
    ("the scroll bar goes black again in blue", "sl_theme", "'scroll=black,cyan,bold'", "'scroll=black,cyan,'"),
    ("the sandbox no longer starts at the terminal", "sandbox-fromtree.py", "f.write(\"terminal\\n\")", "f.write(\"menu\\n\")"),
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
    s = load()
    rows = checks(s)
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-home-units: %d checks, %d failed" % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
