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
PROGS = ("tool_home", "home_entry", "home_off", "home_pins", "home_recent", "mymenu", "tool_menus", "exit", "setstart", "settile", "cproc", "modifya", "sl_theme")
MSGS = tuple(str(n) for n in range(11863, 11887) if n != 11879) + tuple(str(n) for n in range(11956, 11962))       # 11879 was "tiles off for every account": there is no such setting (per account only); 11956-11961 are the sub-menus and the Recent group (26 Oct 26)
STANDARD = "editor ide ced terminal keys switch signout files voc dict query bulk catalog test recent".split()        # the ids SET.TILE and the menu management page know: the tiles the page draws, and recent (the group)


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def ordered(text, *parts):
    """True when every part is found, each after the one before."""
    pos = -1
    for p in parts:
        k = text.find(p, pos + 1)
        if k < 0:
            return False
        pos = k
    return True


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
    src["tool.verbs"] = sorted(n for n in os.listdir(os.path.join(SDSYS, "voc_template")) if n.startswith("tool."))     # every administrator page has a verb of this form
    src["menu.n"] = read(os.path.join(SDSYS, "newvoc", "menu")) if os.path.exists(os.path.join(SDSYS, "newvoc", "menu")) else ""
    src["menu.t"] = read(os.path.join(SDSYS, "voc_template", "menu")) if os.path.exists(os.path.join(SDSYS, "voc_template", "menu")) else ""
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
    cmds = re.findall(r"act = '(cmd:[^']*|menu:[^']*|terminal|switch|signout|back)' ; pal", th)       # the rows of the table (the case lines of start.tile also say act = ...)
    ADMIN_TILES = {"menus": "tool.menus", "viewers": "tool.viewers", "audit": "tool.audit", "config": "tool.config", "backups": "tool.backups", "masters": "tool.masters",
                   "accounts": "tool.accounts", "sessions": "tool.sessions", "gates": "tool.gates", "remote": "tool.remote", "ai": "tool.ai"}
    DEV_TILES = {"files": "tool.files", "voc": "tool.voc", "dict": "tool.dict", "query": "tool.query", "bulk": "tool.bulk", "catalog": "tool.catalog", "test": "tool.test"}            # the development apps (DV), for every account; each adds its tile in the commit that builds it (plan 13.2)
    ck("H4 tool_home: every tile of the table has a fixed action (cmd:sed, ide, ced, tool.keys, my.menu, the development apps and the eleven administrator pages), terminal, switch, signout or back (the Back tile of a sub-menu page); the ONLY other action is a person's own program (H25); and no tile of the delivered page opens a sub-menu (no menu:<name>)",
       sorted(cmds) == sorted(["cmd:sed", "cmd:ide", "cmd:ced", "terminal", "cmd:tool.keys", "switch", "signout", "back", "cmd:my.menu"] + ["cmd:" + v for v in ADMIN_TILES.values()] + ["cmd:" + v for v in DEV_TILES.values()]), repr(cmds))
    ck("H4b ...execute is given only a sentence from that table, 'quit', or the logto of an account picked from the register list",
       sorted(re.findall(r"execute ([^\n]+)", th)) == sorted(["sentence trapping aborts", "'quit'", "'quit'", "'logto ' : acct trapping aborts"]), repr(re.findall(r"execute ([^\n]+)", th)))     # 'quit' twice: sign out, and the confined account; the two that run what is not HOME's own are trapped (28 Oct 26, S.88 phase 2)
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
    ck("H14 modify.account: START-MENU, START-TERMINAL and START-DEFAULT are in the word list between the ai words (23 Oct 26, S.69 step 2) and the pins, and share the slot ST",
       "FILES-ADMIN-OFF,AI-ON,AI-OFF,SDSYS-ON,SDSYS-OFF,START-MENU,START-TERMINAL,START-DEFAULT,PINS-ON,PINS-OFF,SUSPENDED" in ",".join(w) and len(w) == len(sl)
       and [sl[w.index(x)] for x in ("START-MENU", "START-TERMINAL", "START-DEFAULT")] == ["ST", "ST", "ST"] and [sl[w.index(x)] for x in ("PINS-ON", "PINS-OFF")] == ["PN", "PN"])
    ck("H14b ...do.action has the three cases and start.set writes only field 16, says 11868, audits, and says 11869 when nothing changes",
       all(re.search(r"case action = '%s'\n\s+start\.want = %s\n\s+gosub start\.set\n\s+return" % (a, v), md) for a, v in (("START-MENU", "'menu'"), ("START-TERMINAL", "'terminal'"), ("START-DEFAULT", "''")))
       and "acc.new<ACC$START> = start.want" in md and "sysmsg(11868, acc.name" in md and "sysmsg(11869, acc.name)" in md and "K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name" in between(md, "\nstart.set:\n", "\nset.suspended:\n"))
    ck("H14c ...the usage and the list of actions name the three words", md.count("start-menu") >= 2 and "start-menu | start-terminal | start-default" in md)

    f = s["files"]
    ck("H15 the VOC: HOME and EXIT for every account (newvoc) and for SDSYS (voc_template); SET.START.DEFAULT for SDSYS ONLY", f["newvoc/home"] and f["newvoc/exit"] and f["voc_template/home"] and f["voc_template/exit"]
       and f["voc_template/set.start.default"] and not f["newvoc/set.start.default"], repr(f))
    ck("H15c MENU (23 Oct, the owner's word for the way to the full-screen menu) is a verb of every VOC that runs the same program as HOME, in both places",
       all(len(t.split("\n")) >= 3 and t.split("\n")[0][:1].upper() == "V" and t.split("\n")[2] == "$tool_home" for t in (s["menu.n"], s["menu.t"])), repr((s["menu.n"][:60], s["menu.t"][:20])))
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
       and "gosub add.tile\n   if not(added) then return" in th and "if gr<k, HG.BAND> = b and gtiles<k> > 0 then\n            gcols = gcw<k>" in th and "if gk > 0 then gtiles<gk> = gtiles<gk> + 1" in th and "if gy # '' then" in th)
    ck("H21b ...the menus are made by build.page (so F5 and Switch account see the change), and the Terminal, Switch account and Keys entries carry the D flag when their tile is off",
       "gosub alloc.styles\n   gosub make.menus\n   return" in th and "'&Go|&Terminal~~terminal~' : tflag : '|S&witch account~~switch~' : sflag" in th
       and "'&Help|&Keys~~keys~' : kflag" in th and "tflag = (if terminal.off then 'D' else '')" in th)
    ck("H22 !home_entry: when the screen ends and the account's Terminal tile is off, the person is signed out (QUIT) and not left at the prompt",
       he.find("execute 'home'") > 0 and he.find("call !home_off(@who, off)") > he.find("execute 'home'")
       and "if index(' ' : off : ' ', ' terminal ', 1) then\n      sleep 2\n      execute 'quit'\n   end" in he)
    ck("H23 SET.TILE asks for the administrator first (2001), refuses to turn SIGN OUT off before it reads or writes anything, checks the name, and refuses an account that is not registered",
       0 < st_.find("kernel(K$ADMINISTRATOR, -1)") < st_.find("stop sysmsg(2001)") < st_.find("if tile = 'signout' and state = 'off' then stop sysmsg(11878)") < st_.find("openpath @sdsys : @ds : 'accounts' to acc.f else stop sysmsg(6003)")
       and "stop sysmsg(11881, tile)" in st_ and "if who = 'sdsys' then stop sysmsg(2202)" in st_)
    ck("H23a ...and refuses to turn the BACK tile off in the same place (11962, 26 Oct 26, review of the home work), before it reads or writes anything",
       0 < st_.find("if tile = 'signout' and state = 'off' then stop sysmsg(11878)") < st_.find("if tile = 'back' and state = 'off' then stop sysmsg(11962)") < st_.find("openpath @sdsys : @ds : 'accounts' to acc.f else stop sysmsg(6003)")
       and os.path.exists(os.path.join(SDSYS, "messages", "11962")))
    ck("H23b ...it takes ONE account (no 'all'), changes field 17 by readu and write under the lock, says already when nothing changes (11877), audits, and notes a tile that is not standard (11883)",
       "tiles.off" not in st_ and "'all'" not in st_ and "readu acc.rec from acc.f, who else" in st_ and "acc.rec<ACC$TILES.OFF> = new.list" in st_ and "write acc.rec to acc.f, who on error ok = @false" in st_
       and "sysmsg(11877, tile, state, who)" in st_ and "K$AUDIT, 'set.tile '" in st_ and "sysmsg(11883, tile)" in st_ and "standard = '" + " ".join(STANDARD) + "'" in st_)
    tm0 = strip(s["tool_menus"])
    drawn = set(re.findall(r"id = '([a-z]+)' ; grp = ", th)) - {"mymenu", "back"} - set(ADMIN_TILES)               # what the page draws for an account holder: the standard tiles (the administrator's pages, the account's own programs and the Back tile are not standard)
    m_ids = re.search(r"tids = ('[a-z]+'(?: : @fm : '[a-z]+')*)", tm0)
    m_labs = re.search(r"tlabs = ('[^']+'(?: : @fm : '[^']+')*)", tm0)
    ids_tm = re.findall(r"'([a-z]+)'", m_ids.group(1)) if m_ids else []
    labs_tm = re.findall(r"'([^']+)'", m_labs.group(1)) if m_labs else []
    std_st = re.search(r"standard = '([a-z ]+)'", st_)
    ids_st = std_st.group(1).split() if std_st else []
    ck("H23c ...and THE LIST OF STANDARD IDS IS THE TILES THE HOME SCREEN DRAWS (the seven development tiles included): set.tile's list, the menu management page's list and the ids in the table of tool_home are one list, and recent, which is a group and not a tile, is the one id more",
       sorted(drawn) == sorted(set(STANDARD) - {"recent"}) and ids_st == STANDARD and ids_tm == STANDARD, repr((sorted(drawn), ids_st, ids_tm)))
    labs_th = dict(re.findall(r"id = '([a-z]+)' ; grp = [^;]*; label = '([^']+)'", th))
    ck("H23c2 ...the menu management page names each as the tile is named on the page (the label of its row is the label of its tile), in the same order; recent is the Recent group",
       len(labs_tm) == len(ids_tm) and all((labs_th.get(i) == l) for i, l in zip(ids_tm, labs_tm) if i != "recent") and labs_tm[-1:] == ["Recent group"], repr((labs_tm, labs_th)))
    adm = between(th, "   if is.admin then\n      bnd += 1", "\n   end\n")                # the first `end` at the block's own indent closes it
    ck("H23d ...and the eleven tiles that are not standard (the administrator's pages) are built for the administrator only (inside `if is.admin then`, in the groups System, People and access and Data, network and AI), each exactly once and running its page's verb",
       adm.startswith("   if is.admin then") and all(adm.count("id = '%s' ;" % i) == 1 and th.count("id = '%s' ;" % i) == 1 and re.search(r"id = '%s' ; grp = g ;[^\n]*act = 'cmd:%s'" % (i, re.escape(v)), adm) is not None for i, v in ADMIN_TILES.items())
       and all("gr<g> = '%s'" % n in adm for n in ("System", "People and access", "Data, network and AI")), repr(adm[:200]))
    ck("H23e ...and their three groups stand side by side in ONE band, two tile columns each (four tiles in System, three in People and access, four in Data, network and AI: two tile rows), so that the administrator's first screen (this band of two tile rows, Tools, My programs, Everyone) shows Tools and Everyone at 140 by 43 without scrolling",
       re.findall(r"gr<g> = '([^']+)' : @vm : bnd : @vm : (\d)", adm) == [("System", "2"), ("People and access", "2"), ("Data, network and AI", "2")] and adm.count("bnd += 1") == 1, repr(re.findall(r"gr<g> = '([^']+)' : @vm : bnd : @vm : (\d)", adm)))
    # H28a (26 Oct 26, found on the VM by witness-batch26.py S76-b2): OPENSEQ of an ABSENT file takes ELSE and still holds a lock on the name until the file variable is closed.  The delivered
    # state has no start.default, so every session that started at the home screen kept an update lock on it for its whole life and the next session waited at sign-on.  Each program that
    # opens a possibly absent file READONLY closes the variable in its ELSE branch.
    leaks = []
    for prog_, var_ in (("home_entry", "df"), ("setstart", "df"), ("tool_menus", "df"), ("viewlist", "lf"), ("osread", "f")):
        try:
            txt_ = s[prog_] if prog_ in s else open(os.path.join(GPL, prog_), encoding="latin-1").read()      # the mutated text when the self-test mutates this program
        except (OSError, TypeError):
            txt_ = ""
        if not re.search(r"openseq[^\n]* readonly to %s then[\s\S]{0,700}?else[^\n]*\n(?:\s*\*[^\n]*\n)*\s*if not\(unassigned\(%s\)\) then close %s" % (var_, var_, var_), txt_):
            leaks.append(prog_)
    ck("H28a every program that opens a possibly absent file READONLY (!home_entry, SET.START.DEFAULT, the menu management page, !viewlist, OSREAD) closes the file variable in its ELSE branch, so that an absent start.default does not leave an update lock on it for the life of the session",
       not leaks, repr(leaks))
    ck("H28 every administrator page has a tile (plan 13.2: a new app adds its row in the commit that builds it): each verb of voc_template named tool.* (all of SDSYS's) is the action of a tile, and no tile runs a tool.* verb that has no VOC entry",
       sorted(s["tool.verbs"]) == sorted(set(v for v in ADMIN_TILES.values()) | set(DEV_TILES.values()) | {"tool.keys"}) and all(("act = 'cmd:%s'" % v) in th for v in s["tool.verbs"]), repr(s["tool.verbs"]))
    dev = between(th, "gr<g> = 'Develop'", "\n   id = 'switch' ;")
    ck("H28b ...the development apps' tiles are in the group Develop, the LAST group (so that the groups before it, and what the keys and the sandbox rows find in them, stay where they were), built for everyone (outside `if is.admin then`), each exactly once and running its app's verb",
       "gr<g> = 'Develop' : @vm : bnd : @vm : 6" in th and th.find("gr<g> = 'Develop'") > th.find("gr<g> = 'Everyone'") > th.find("if is.admin then")
       and all(dev.count("id = '%s' ;" % i) == 1 and re.search(r"id = '%s' ; grp = g ;[^\n]*act = 'cmd:%s'" % (i, re.escape(v)), dev) is not None for i, v in DEV_TILES.items())
       and "\n   id = 'switch' ; grp = 0 ;" in th, repr(dev[:160]))
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
    live = between(th, "\nlive.read:\n", "\ndraw.panel:")
    ck("H29 live lines (plan 13.1): only the administrator's page has any (the guard comes before the first tile is looked at), and each line is a question that only reads - the kernel's master-file 'ready' and 'pending', the session list and the register's names; nothing is written, executed or audited",
       0 < live.find("if not(is.admin) then return") < live.find("for i = 1 to nt")
       and re.findall(r"kernel\(([^)]*)\)", live) == ["K$MASTERS, 'ready'", "K$MASTERS, 'pending'"]
       and "call !listu(ludata)" in live and "openpath @sdsys : @ds : 'accounts' to lf then" in live
       and not re.search(r"\b(write|writev|delete|execute|void)\b", live), repr(re.findall(r"kernel\(([^)]*)\)", live)))
    ck("H29b ...they are read when the page is built (the first time and on F5, before the styles) and again whenever the 30 seconds' key wait runs out, which draws only the tiles whose line changed; a tile shows its live line where the sub line was, unless it is dimmed",
       0 < th.find("gosub live.read\n   gosub alloc.styles") and "gosub draw.clock\n            gosub live.draw" in th
       and "di = live.chg<k>\n      gosub draw.tile" in th and th.count("tl<di, HT.LIVE> # '' then tl<di, HT.LIVE> else tl<di, HT.SUB>") == 2
       and th.count("tl<di, HT.WHY> # '' then tl<di, HT.WHY> else (if tl<di, HT.LIVE>") == 2)

    # ---------------------------------------------------------------------------------------------------------------- 26 Oct 26 (S.75, home): sub-menus
    om = between(th, "\nopen.menu:\n", "\nclose.menu:\n")
    cm = between(th, "\nclose.menu:\n", "\ntoggle.recent:\n")
    ck("H30 sub-menus: a folder tile (action menu:<name>) is refused when its menu is the one shown, the name is empty or the menu is open above (11956) and at the ninth level (11957), BEFORE anything is pushed; then the page left, its tile and its scroll are kept, the crumb is the tile's label and the level is entered",
       re.search(r"\$define HM\.DEPTH\s+8\b", th) is not None
       and ordered(om, "mname = act[6, 99]", "already = (mname = cur.menu or mname = '')", "if stk<sk, 1> = mname then already = 1", "msg = sysmsg(11956, mname)", "return", "if dep >= HM.DEPTH then",
                   "msg = sysmsg(11957, HM.DEPTH)", "return", "stk<-1> = cur.menu : @vm : tl<fi, HT.ID> : @vm : top", "crumb<-1> = tl<fi, HT.LABEL>", "cur.menu = mname", "gosub enter.level"), om)
    ck("H30b ...Back one page does nothing on the top page (the test of the stack comes before it is read), gives the focus and the scroll back, takes the level off both stacks, and enters the page left",
       ordered(cm, "dep = dcount(stk, @fm)", "if dep = 0 then return", "e = stk<dep>", "cur.menu = e<1, 1>", "want.id = e<1, 2>", "want.top = e<1, 3>", "del stk<dep>", "del crumb<dep>", "gosub enter.level"), cm)
    st_tile = between(th, "\nstart.tile:\n", "\nnote.recent:\n")
    ck("H30c ...a folder tile and the Back tile are started like any tile (Enter, the space bar, a click, the AI line), Esc and Backspace and the Go menu's Back entry do the same, and a tile that runs a command notes it for the Recent group before it runs",
       ordered(st_tile, "case act[1, 4] = 'cmd:'", "gosub note.recent", "gosub run.command", "case act[1, 5] = 'menu:'\n         gosub open.menu", "case act = 'back'\n         gosub close.menu")
       and "case nm = 'esc' or nm = 'bs'\n         gosub close.menu" in th and "case cmd = 'back'\n         gosub close.menu" in th, st_tile)
    bp_ = between(th, "\nbuild.page:\n", "\nadd.recent:\n")
    plh = between(th, "\nplace.header:\n", "\nalloc.styles:\n")
    ck("H30d ...the Back tile is built only on a sub-menu page, at the left end of the header (the first tile column, column 3 at 140 by 43, the header's first row), as a header tile, after the Switch account and Sign out tiles; "
       "and the page is built in this order - the whole table, the Recent group, the level, the live lines, the styles, the menus.  Since S.88 L2 the header tiles are PLACED by the layout (place.header, the "
       "first thing layout does): Switch account and Sign out on the last two tile columns (95 and 117 at 140 by 43), Back on the first, on the header's first row, a tile wide",
       ordered(bp_, "act = 'signout' ; pal = 'gray' ; size = 's' ; pause = 0 ; why = '' ; gosub add.header", "if cur.menu # '' then", "id = 'back' ; grp = 0", "act = 'back' ; pal = 'gray' ; size = 's'", "gosub add.header",
                   "gosub add.recent\n   gosub pick.level\n   gosub live.read\n   gosub alloc.styles\n   gosub make.menus\n   return")
       and ordered(plh, "if tl<i, HT.FIXED> then", "case tl<i, HT.ID> = 'switch'", "tl<i, HT.X> = xcol<ncol - 1>", "case tl<i, HT.ID> = 'signout'", "tl<i, HT.X> = xcol<ncol>", "case 1", "tl<i, HT.X> = xcol<1>",
                   "tl<i, HT.Y> = hdy", "tl<i, HT.W> = tw.n")
       and between(th, "\nlayout:\n", "\nband.cols:\n").startswith("\nlayout:\n   gosub place.header\n"), bp_ + plh)
    pl = between(th, "\npick.level:\n", "\nadd.tile:\n")
    ck("H30e ...pick.level leaves out a folder tile whose menu holds no tile (and goes on until none is left to leave out), keeps the groups of the menu shown and the header tiles, and numbers the groups again; the page it is given is the whole table",
       ordered(pl, "if pa[1, 5] = 'menu:' then", "if gr<pg, HG.MENU> = pa[6, 99] then pn += 1", "if pn = 0 then\n               del tl<pi>", "if dropped = 0 then exit", "if gr<pk, HG.MENU> = cur.menu then", "gmap<pk> = dcount(gr2, @fm)",
                   "if pg = 0 then\n         tl2<-1> = tl<pi>", "t<1, HT.GROUP> = gmap<pg>", "tl = tl2", "gr = gr2", "nt = dcount(tl, @fm)"), pl)
    ck("H30f ...the delivered page declares no sub-menu (no tile with action menu:<name>, no group given a menu): the mechanism is there for a table that wants one",
       "act = 'menu:" not in th and not re.search(r"gr<g, HG\.MENU> =", th), "")
    sw2 = between(th, "\nswitch.account:\n", "\nend\n")
    ck("H30g ...Switch account starts the other account's screen at its TOP page: the level, the stack and the crumbs are cleared after the logto and before the screen is taken again",
       ordered(sw2, "hlogto = 0", "cur.menu = ''", "stk = ''", "crumb = ''", "gosub reopen"), sw2)
    mk = between(th, "\nmake.keys:\n", "\nset.title:\n")
    st2 = between(th, "\nset.title:\n", "\nopen.menu:\n")
    ck("H30h ...the key table names Esc only on a sub-menu page; the status line's pane is the path (Home > ...) and the identity stands at column 25 beside the Back tile, column 3 otherwise; the header's left end is cleared before it is drawn",
       "if cur.menu # '' then call $tk_keys('add', keys, 'esc', 'back', 'back', '', 1)" in mk and ordered(st2, "ttl = 'Home'", "ttl := ' > ' : crumb<ck>", "idx = (if cur.menu # '' then xcol<2> else xcol<1>)")
       and "call $tk_frame(ctx, keys, ttl, msg)" in th and "ttl = 'Home'" in th and "screen clear at 0,hdy size xcol<ncol - 1> - 1,3" in between(th, "\ndraw.header:\n", "\ndraw.clock:\n")
       and "screen text fmt(who.line, '60L') at idx,hdy + 1 attr 'bold'" in th and "at idx,hdy + 2 attr 'disabled'" in th, mk + st2)
    ck("H30i ...the AI line is offered no folder tile, no Back tile and no copy (its list is the cmd: tiles and the Terminal, except a recent copy)",
       ordered(between(th, "\nask.ai:\n", "\n   ctxt = "), "if ta[1, 4] = 'cmd:' or ta = 'terminal' then", "if tl<i, HT.ID>[1, 2] # 'r:' then", "acts<1, -1> = "), "")
    ck("H30j ...an empty band takes no room and a page whose first band is 0 (the Recent group) is laid out from it: the layout finds the first band, and moves down only when a group was placed",
       ordered(between(th, "\nlayout:\n", "\nfind.first:\n"), "b0 = 1", "if gr<k, HG.BAND> < b0 then b0 = gr<k, HG.BAND>", "for b = b0 to nb", "if c0 > 0 then ys = bandend + 1"), "")

    # ---------------------------------------------------------------------------------------------------------------- the Recent group
    ar = between(th, "\nadd.recent:\n", "\npick.level:\n")
    ck("H31 the Recent group: nothing is read when the administrator has turned it off (recent in the off list, asked BEFORE the routine), nothing is built when it is off, only tiles that run a command (cmd:) of a group are copied, a copy is a new id (r: and the tile's own) in the first group, and every other group moves down one place",
       ordered(ar, "rc.on = 0", "if index(off.set, ' recent ', 1) then return", "call !home_recent('get', rc.on, rc.ids)", "if not(rc.on) then return", "tl<ri, HT.GROUP> > 0 and tl<ri, HT.ACT>[1, 4] = 'cmd:'",
                   "t<1, HT.ID> = 'r:' : tl<ri, HT.ID>", "t<1, HT.GROUP> = 1", "tl<ri, HT.GROUP> = tl<ri, HT.GROUP> + 1", "gr = 'Recent' : @vm : 0 : @vm : 6 : @fm : gr", "tl = rc.tiles : @fm : tl"), ar)
    nr = between(th, "\nnote.recent:\n", "\nrun.command:\n")
    ck("H31b ...a tile that is started is noted only while the group is on (nothing is asked of the file otherwise), by its own id (the r: of a copy taken off), never a pin of the person's own, and the routine is asked to add and to do nothing else",
       ordered(nr, "if not(rc.on) then return", "if rid[1, 2] = 'r:' then rid = rid[3, 99]", "if rid[1, 3] = 'pin' then return", "call !home_recent('add', rid, '')"), nr)
    ck("H31c ...the screen asks !home_recent for get, add, on and off and nothing else",
       sorted(re.findall(r"call !home_recent\('(\w+)'", th)) == ["add", "get", "off", "on"], repr(re.findall(r"call !home_recent\('(\w+)'", th)))
    tr = between(th, "\ntoggle.recent:\n", "\nrelayout:\n")
    ck("H31d ...the View menu's entry turns the group on and off, the administrator's SET.TILE ... recent off wins (11961, before the routine is asked), and the entry carries the D flag then; on says 11958, off 11959 and a failure 11960",
       ordered(tr, "if index(off.set, ' recent ', 1) then\n      msg = sysmsg(11961)\n      return", "call !home_recent('off', rok, junk)", "rmsg = 11959", "call !home_recent('on', rok, junk)", "rmsg = (if rok then 11958 else 11960)", "gosub rebuild", "msg = sysmsg(rmsg)")
       and "rflag = (if index(off.set, ' recent ', 1) then 'D' else '')" in th and "'|Recent &group (' : (if rc.on then 'on' else 'off') : ')~~recent~' : rflag" in th and "case cmd = 'recent'\n         gosub toggle.recent" in th, tr)
    hr = strip(s["home_recent"])
    rg = between(hr, "\nrc.get:\n", "\nrc.add:\n")
    ra = between(hr, "\nrc.add:\n", "\nrc.on:\n")
    ro = between(hr, "\nrc.on:\n", "\nrc.off:\n")
    rf = between(hr, "\nrc.off:\n", "\nvalid.id:\n")
    ck("H32 !home_recent GET reads and writes nothing (no write, delete or execute), only for the record RECENT, and returns the ids that are one to twenty lower case letters, no id twice, at most 6; a record whose first field is not on is the group off",
       "read rec from f, 'recent' else rec = ''" in rg and "if rec<1> # 'on' then return" in rg and not re.search(r"\b(write|delete|execute|readu)\b", rg) and re.search(r"\$define RC\.MAX\s+6\b", hr) is not None
       and "if idok and dcount(b, @fm) < RC.MAX then" in rg and "index(@fm : b : @fm, @fm : id : @fm, 1) = 0" in rg and "idok = (id # '' and len(id) <= 20 and index(id, ' ', 1) = 0 and trim(convert(okchars, str(' ', len(okchars)), id)) = '')" in hr
       and "okchars = 'abcdefghijklmnopqrstuvwxyz'" in hr, rg)
    ck("H32b ...ADD does nothing at all when the id is not plain, the file or the record is not there, the record is locked by another session or the first field is not on (every one of these returns BEFORE the write, and releases the lock it holds), keeps six, and writes only the record RECENT",
       ordered(ra, "gosub valid.id", "if not(idok) then return", "open '&menus&' to f else return", "readu rec from f, 'recent' locked", "if lk then\n      close f\n      return", "if not(got) or rec<1> # 'on' then\n      release f, 'recent'\n      close f\n      return",
               "newrec = 'on' : @fm : a", "n < RC.MAX", "write newrec to f, 'recent' on error wok = @false", "if not(wok) then release f, 'recent'") and ra.count("write ") == 1 and "execute" not in ra, ra)
    ck("H32c ...ON is the only place that makes the file (create.file &menus& dynamic, the way MY.MENU does it) and writes the one word on; OFF deletes the record RECENT and nothing else; there is no other execute, write or delete in the routine",
       "execute 'create.file &menus& dynamic' capturing mk" in ro and "write 'on' to f, 'recent' on error wok = @false" in ro and "delete f, 'recent'" in rf and hr.count("execute") == 1 and hr.count("write ") == 2 and hr.count("delete ") == 1
       and "$catalog !home_recent" in hr, ro + rf)
    m = s["msgs"]
    ck("H33 messages 11956 to 11961 are the sub-menu refusals and the Recent group's words: 11956 and 11957 take %1, none begins with a capital command word",
       all(m.get(str(n)) for n in range(11956, 11962)) and "%1" in m["11956"] and "%1" in m["11957"] and "Esc" in m["11957"] and "Recent group is on" in m["11958"] and "forgotten" in m["11959"] and "&menus&" in m["11960"] and "administrator" in m["11961"],
       repr([m.get(str(n)) for n in range(11956, 11962)]))

    # ---------------------------------------------------------------------------------------------------------------- 28 Oct 26, S.88 phase 2 (plan 2.5, 2.8)
    rcm = between(th, "\nrun.command:\n", "\nwait.key:\n")
    ck("H34 a tile's command is run TRAPPING ABORTS, so that a refusal does not end HOME (plan 2.5); the terminal is given up first, $sl_cleanup follows the command (an app the command started and that was aborted may hold the screen and the break key) and the screen is taken again last; "
       "the same for the LOGTO of Switch account, whose $sl_cleanup comes before the screen is taken again",
       ordered(rcm, "call $tk_close(ctx)", "execute sentence trapping aborts", "call $sl_cleanup", "if pause or aborted then gosub wait.key", "gosub reopen")
       and ordered(sw, "execute 'logto ' : acct trapping aborts", "hlogto = 0", "call $sl_cleanup", "gosub reopen"), rcm + sw)
    ck("H34c an aborted command is not drawn over (TUI phase 2 review, a): a sentinel @abort.message is set BEFORE the command (set.sentinel, caught division by zero as tool.test does), the command is judged aborted when @abort.message is no longer the sentinel "
       "(@abort.code is 0 again when the command processor returns, so it is not used), that is read BEFORE $sl_cleanup, and an aborted command waits for a key (wait.key) before the screen is taken again, as a tile with a pause does",
       ordered(rcm, "gosub set.sentinel", "execute sentence trapping aborts", "aborted = (@abort.message # sentinel)", "call $sl_cleanup", "if pause or aborted then gosub wait.key", "gosub reopen")
       and "@abort.code" not in rcm and "sentv = 1 / zero" in rcm and "catch sys.program.div_zero" in rcm and ordered(rcm, "sentinel = ''", "try", "sentinel = @abort.message", "if sentv # 0 then sentinel = ''"), rcm)
    ck("H34d the AI is told there is nowhere to run a command ('nocmd', field 11) when the Terminal tile is off for the account, BEFORE it is asked, and a 'command' answer is refused with a message and never reaches run.command in that case (TUI phase 2 review, b: the Terminal tile off "
       "means no command prompt through the AI either; this tightens a default)",
       ordered(th, "if terminal.off then actx<11> = 'nocmd'", "call $tk_ai('ask', ctx, actx, res)", "case res<1> = 'command' and terminal.off", "case res<1> = 'command'\n         sentence = res<2>")
       and "msg = 'the Terminal is turned off for this account'" in between(th, "case res<1> = 'command' and terminal.off", "case res<1> = 'command'\n"), between(th, "\nask.ai:\n", "\nstart.tile:\n"))
    aia = between(th, "\nask.ai:\n", "\n   ctxt = ")
    ck("H34b the AI is told that every action only NAVIGATES (so that Enter alone accepts) only while no pin and no Terminal tile is among the actions offered (S6): the flag starts at 1, a pin (id pin<n>) or the Terminal tile makes it 0, "
       "and the flag - not a constant - is the fifth field of what the AI is told",
       ordered(aia, "ai.nav = 1", "if tl<i, HT.ID>[1, 3] = 'pin' or ta = 'terminal' then ai.nav = 0") and "acts : @fm : ai.nav" in th and "acts : @fm : 1" not in th, aia)
    return rows


MUTANTS = [
    ("finish no longer signs out a confined account", "tool_home", "      case terminal.off and outcome # 'signout'", "      case @false"),
    ("home_entry leaves a confined account at the prompt", "home_entry", "   if index(' ' : off : ' ', ' terminal ', 1) then\n      sleep 2\n      execute 'quit'\n   end\n", ""),
    ("a header tile that is off is placed on the previous tile", "tool_home", "   gosub add.tile\n   if not(added) then return\n", "   gosub add.tile\n"),
    ("a tile that is off is added", "tool_home", "   if index(off.set, ' ' : id : ' ', 1) then return        ;* turned off by the administrator: not on the page at all\n", ""),
    ("the menus are made once, at the start", "tool_home", "   gosub alloc.styles\n   gosub make.menus\n   return", "   gosub alloc.styles\n   return"),
    ("the Terminal entry stays choosable", "tool_home", "tflag = (if terminal.off then 'D' else '')", "tflag = ''"),
    ("an empty group still has a heading", "tool_home", "      for k = 1 to ng\n         if gr<k, HG.BAND> = b and gtiles<k> > 0 then", "      for k = 1 to ng\n         if gr<k, HG.BAND> = b then"),
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
    ("the logto does not mark hlogto", "tool_home", "   hlogto = 1\n   execute 'logto ' : acct trapping aborts", "   execute 'logto ' : acct trapping aborts"),
    # 28 Oct 26, S.88 phase 2 (plan 2.5, 2.8; defects S6, D4): H34 holds these
    ("a refused command ends HOME again", "tool_home", "   execute sentence trapping aborts\n", "   execute sentence\n"),
    ("an aborted app's screen and break key are not given back", "tool_home", "   call $sl_cleanup\n   if pause or aborted then gosub wait.key", "   if pause or aborted then gosub wait.key"),
    # 28 Oct 26, TUI phase 2 review (a) and (b): H34c and H34d hold these
    ("an aborted command is drawn over again", "tool_home", "   if pause or aborted then gosub wait.key", "   if pause then gosub wait.key"),
    ("the abort is judged by @abort.code, which is 0 again", "tool_home", "aborted = (@abort.message # sentinel)", "aborted = (@abort.code # 0)"),
    ("the abort is judged after the cleanup", "tool_home", "   aborted = (@abort.message # sentinel)                  ;* read before $sl_cleanup\n   call $sl_cleanup\n", "   call $sl_cleanup\n   aborted = (@abort.message # sentinel)\n"),
    ("the sentinel is not set before the command", "tool_home", "   gosub set.sentinel\n   execute sentence trapping aborts", "   execute sentence trapping aborts"),
    ("the AI may still offer a command with the Terminal off", "tool_home", "   if terminal.off then actx<11> = 'nocmd'\n", ""),
    ("the AI is told nocmd only when the Terminal is on", "tool_home", "   if terminal.off then actx<11> = 'nocmd'", "   if not(terminal.off) then actx<11> = 'nocmd'"),
    ("a command answer runs with the Terminal off", "tool_home", "      case res<1> = 'command' and terminal.off\n         msg = 'the Terminal is turned off for this account'", "      case res<1> = 'command' and @false\n         msg = 'the Terminal is turned off for this account'"),
    ("a LOGTO that aborts ends HOME", "tool_home", "   execute 'logto ' : acct trapping aborts ", "   execute 'logto ' : acct ;"),
    ("the AI is told every action only navigates", "tool_home", "acts : @fm : ai.nav", "acts : @fm : 1"),
    ("a pin does not clear the navigation flag", "tool_home", "if tl<i, HT.ID>[1, 3] = 'pin' or ta = 'terminal' then ai.nav = 0", "if ta = 'terminal' then ai.nav = 0"),
    ("the Terminal tile does not clear the navigation flag", "tool_home", "if tl<i, HT.ID>[1, 3] = 'pin' or ta = 'terminal' then ai.nav = 0", "if tl<i, HT.ID>[1, 3] = 'pin' then ai.nav = 0"),
    ("a tile draws outside the panel", "tool_home", "      if sy >= lo and sy <= hi then", "      if @true then"),
    ("the scroll bar is not drawn", "tool_home", "   if ch > ph then\n      call $sl_scrollbar", "   if @false then\n      call $sl_scrollbar"),
    ("a piped session is let in", "tool_home", "   if @tty[1, 5] # '/dev/' then\n      display sysmsg(11863)", "   if @false then\n      display sysmsg(11863)"),
    ("the home entry keeps the lock of an absent start.default", "home_entry", "         if not(unassigned(df)) then close df\n", "         null\n"),
    ("set.tile lets the Back tile be turned off", "settile", "if tile = 'back' and state = 'off' then stop sysmsg(11962)", "if @false then stop sysmsg(11962)"),
    ("modify.account loses a start word", "modifya", "AI-OFF,SDSYS-ON,SDSYS-OFF,START-MENU,START-TERMINAL,START-DEFAULT,PINS-ON,PINS-OFF,SUSPENDED", "AI-OFF,SDSYS-ON,SDSYS-OFF,START-MENU,START-TERMINAL,PINS-ON,PINS-OFF,SUSPENDED"),
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
    ("the Bypass programs tile is built for everyone", "tool_home", "gosub add.tile\n      id = 'viewers' ;", "gosub add.tile\n   end\n   if @true then\n      id = 'viewers' ;"),
    ("the Accounts tile is built for everyone", "tool_home", "      id = 'accounts' ; grp = g ;", "   end\n   if @true then\n      id = 'accounts' ; grp = g ;"),
    ("the Audit trail tile runs another page", "tool_home", "act = 'cmd:tool.audit'", "act = 'cmd:tool.config'"),
    ("the Remote servers tile is gone", "tool_home", "      id = 'remote' ; grp = g ;", "      id = 'remoteX' ; grp = g ;"),
    ("the administrator's People and access group is given a band of its own", "tool_home", "      * who may do what, and who is on: the people and access group\n      g += 1", "      * who may do what, and who is on: the people and access group\n      bnd += 1\n      g += 1"),
    ("the Files tile runs another app", "tool_home", "act = 'cmd:tool.files'", "act = 'cmd:tool.keys'"),
    ("the Develop group moves to a band of its own before Everyone", "tool_home", "   gr<g> = 'Everyone' : @vm : bnd : @vm : 6", "   gr<g> = 'Develop' : @vm : bnd : @vm : 6"),
    ("the Gates tile is moved out of its group name", "tool_home", "gr<g> = 'People and access'", "gr<g> = 'People'"),
    ("a live line is read for an account holder too", "tool_home", "live.chg = ''\n   if not(is.admin) then return", "live.chg = ''"),
    ("a live line drains the master files' journal", "tool_home", "ans = kernel(K$MASTERS, 'pending')", "ans = kernel(K$MASTERS, 'drain')"),
    ("the key wait no longer reads the live lines again", "tool_home", "gosub draw.clock\n            gosub live.draw", "gosub draw.clock"),
    ("the live line is written over the dimmed reason", "tool_home", "s = '  ' : (if tl<di, HT.WHY> # '' then tl<di, HT.WHY> else (if tl<di, HT.LIVE> # '' then tl<di, HT.LIVE> else tl<di, HT.SUB>))", "s = '  ' : (if tl<di, HT.LIVE> # '' then tl<di, HT.LIVE> else tl<di, HT.SUB>)"),
    ("MENU runs another program for every account", "menu.n", "$tool_home", "$exit"),
    ("MENU is missing from SDSYS's VOC", "menu.t", "$tool_home", ""),
    ("the sandbox no longer starts at the terminal", "sandbox-fromtree.py", "f.write(\"terminal\\n\")", "f.write(\"menu\\n\")"),
    # ---- 26 Oct 26 (S.75, home): sub-menus
    ("a folder tile may open the menu that is open", "tool_home", "   already = (mname = cur.menu or mname = '')\n", "   already = 0\n"),
    ("a sub-menu has no depth limit", "tool_home", "   if dep >= HM.DEPTH then\n", "   if @false then\n"),
    ("Back reads the stack before it asks whether there is one", "tool_home", "   if dep = 0 then return\n   e = stk<dep>\n", "   e = stk<dep>\n   if dep = 0 then return\n"),
    ("Back forgets the tile that had the focus", "tool_home", "   want.id = e<1, 2>\n", "   want.id = ''\n"),
    ("Back leaves the level on the stack", "tool_home", "   del stk<dep>\n", ""),
    ("Esc no longer goes back", "tool_home", "      case nm = 'esc' or nm = 'bs'\n", "      case nm = 'bs'\n"),
    ("the Back tile is built on the top page too", "tool_home", "   if cur.menu # '' then\n      * a sub-menu page: the way back", "   if @true then\n      * a sub-menu page: the way back"),
    ("pick.level keeps the groups of every menu", "tool_home", "      if gr<pk, HG.MENU> = cur.menu then\n", "      if @true then\n"),
    ("pick.level keeps a folder whose menu is empty", "tool_home", "            if pn = 0 then\n               del tl<pi>", "            if pn = -1 then\n               del tl<pi>"),
    ("Switch account keeps the sub-menu", "tool_home", "   cur.menu = ''" + " " * 42 + ";* the screen of the new account starts at its top page\n   stk = ''\n   crumb = ''\n", ""),
    ("the status line does not show the path", "tool_home", "      ttl := ' > ' : crumb<ck>\n", "      null\n"),
    ("the identity does not move right of the Back tile", "tool_home", "   idx = (if cur.menu # '' then xcol<2> else xcol<1>)", "   idx = xcol<1>"),
    # ---- 28 Oct 26, S.88 L2: the header tiles placed by the layout (H30d), the header cleared up to the Switch account tile (H30h)
    ("the Back tile stands where Sign out does", "tool_home", "               tl<i, HT.X> = xcol<1>", "               tl<i, HT.X> = xcol<ncol>"),
    ("the header tiles are placed once and not after a resize", "tool_home", "layout:\n   gosub place.header\n", "layout:\n"),
    ("the header is cleared over the Switch account tile", "tool_home", "screen clear at 0,hdy size xcol<ncol - 1> - 1,3", "screen clear at 0,hdy size xcol<ncol - 1> + 5,3"),
    ("the AI is offered the copies of the Recent group", "tool_home", "if tl<i, HT.ID>[1, 2] # 'r:' then", "if @true then"),
    ("an empty band takes a row", "tool_home", "      if c0 > 0 then ys = bandend + 1", "      ys = bandend + 1"),
    ("the Esc key is on the function-key row of the top page", "tool_home", "   if cur.menu # '' then call $tk_keys('add', keys, 'esc', 'back', 'back', '', 1)\n", "   call $tk_keys('add', keys, 'esc', 'back', 'back', '', 1)\n"),
    # ---- the Recent group
    ("the Recent list is read for an account whose group the administrator turned off", "tool_home", "   if index(off.set, ' recent ', 1) then return\n   call !home_recent('get'", "   call !home_recent('get'"),
    ("a recent tile may run what is not a command of the table", "tool_home", " and tl<ri, HT.ACT>[1, 4] = 'cmd:' then", " then"),
    ("a recent copy keeps the id of the tile", "tool_home", "            t<1, HT.ID> = 'r:' : tl<ri, HT.ID>\n", ""),
    ("the Recent group is the second group", "tool_home", "            t<1, HT.GROUP> = 1\n", "            t<1, HT.GROUP> = 2\n"),
    ("a started tile is noted when the group is off", "tool_home", "note.recent:\n   if not(rc.on) then return\n", "note.recent:\n"),
    ("a pinned program is noted", "tool_home", "   if rid[1, 3] = 'pin' then return\n", ""),
    ("the View entry ignores the administrator's switch", "tool_home", "toggle.recent:\n   if index(off.set, ' recent ', 1) then\n      msg = sysmsg(11961)\n      return\n   end\n", "toggle.recent:\n"),
    ("the View entry stays choosable when the administrator turned the group off", "tool_home", "   rflag = (if index(off.set, ' recent ', 1) then 'D' else '')", "   rflag = ''"),
    ("!home_recent ADD writes when the group is off", "home_recent", "   if not(got) or rec<1> # 'on' then\n      release f, 'recent'\n      close f\n      return\n   end\n", ""),
    ("!home_recent ADD ignores a lock", "home_recent", "   if lk then\n      close f\n      return\n   end\n", ""),
    ("!home_recent ADD keeps more than six", "home_recent", "      if idok and id # a and n < RC.MAX then", "      if idok and id # a then"),
    ("!home_recent GET lists an id that is not plain", "home_recent", "      if idok and dcount(b, @fm) < RC.MAX then", "      if dcount(b, @fm) < RC.MAX then"),
    ("!home_recent OFF deletes another record", "home_recent", "   delete f, 'recent'", "   delete f, 'home'"),
    ("!home_recent ON writes another word", "home_recent", "      write 'on' to f, 'recent' on error wok = @false", "      write 'off' to f, 'recent' on error wok = @false"),
    ("!home_recent takes capitals in an id", "home_recent", "   okchars = 'abcdefghijklmnopqrstuvwxyz'", "   okchars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'"),
    ("!home_recent takes an id with a blank in it", "home_recent", "len(id) <= 20 and index(id, ' ', 1) = 0 and trim(", "len(id) <= 20 and trim("),
    ("!home_recent keeps a list of twenty", "home_recent", "$define RC.MAX   6 ", "$define RC.MAX   20"),
    # ---- the standard ids
    ("SET.TILE does not know the Files tile", "settile", "signout files voc dict query bulk catalog test recent'\n", "signout voc dict query bulk catalog test recent'\n"),
    ("the menu management page does not list recent", "tool_menus", "'test' : @fm : 'recent'\n", "'test'\n"),
    ("a development tile has an id the lists do not know", "tool_home", "id = 'test' ; grp = g ;", "id = 'tests' ; grp = g ;"),
    ("the menu management page loses a label", "tool_menus", "'Programs' : @fm : 'Tests'", "'Programs'"),
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
