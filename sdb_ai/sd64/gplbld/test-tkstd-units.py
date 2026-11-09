#!/usr/bin/env python3
"""test-tkstd-units.py - the keys every full-screen program has the same, and the theme kept for the person (8 Nov 26, S.179).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tkstd-units.py
  python3 .../test-tkstd-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.

THE OWNER, 8 Nov 2026: "The commands need to be consistent across all pages ... the theme switching capability should be available on every
page using the same methodology and should appear in the menu under view"; the theme kept "Inside SD (tighter)"; F5 refresh everywhere, run on F9.

WHAT IT HOLDS (gpl.bp read as text, comments removed):
  S1  $tk_std 'keys' adds Ctrl-T (theme) and Ctrl-K (keys), both off the function-key row, and View > Theme and Help > Keys.
  S2  $tk_std 'theme' is $tk_theme with the library's repaint (own 1); 'keylist' asks the registry's keylist and shows it in a box.
  S3  $tk_theme takes $sl_theme's next, sets it as the program's choice, and keeps it for the person ($sl_theme 'save').
  S4  every program that calls $tk_std('keys' handles Ctrl-T through $tk_std('theme' and Ctrl-K through $tk_std('keylist' (by the key or the action).
  S5  the pages expected to use it do (the 20 tool pages, the home screen, MY.MENU).
  S6  only sl_theme reads CONFIG('SCREENTHEME') to choose a theme (the config verb only prints it): everything else asks $sl_theme 'site'.
  S7  $sl_theme 'site' and 'save' keep the choice as the record theme.<login name> of &menus& in the session's account, and nothing outside it.
  S8  SED: Ctrl-T and Ctrl-K are bound in action.list only when free (a layout's or person's own binding wins); kill line Esc K, toggle Esc T,
      go to Esc G only, refresh F5 and Ctrl-L, compile and run F9; View (Theme, Refresh screen) and Help (Keys in use) menus.
  S9  the debugger: F5 refresh, F9 run, Ctrl-T theme, Ctrl-K keys, Ctrl-L redraw, Esc K / Esc T line editing, Esc alone or F10 the menu bar
      (Run, View, Help) whose function-key items go back to the command loop as the key.
  S10 the IDE: F5 and Ctrl-L refresh, F9 run, Shift-F9 catalog, Alt-G go to, Ctrl-T theme, Ctrl-K keys; the editor passes Ctrl-T and Ctrl-K.
It cannot say a key does what it says on a screen: the suites (sandbox-sed-menu, sandbox-ide, sandbox-dbgui, the pages' own) are that.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BP = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp"))
PAGES = ["tool_accounts", "tool_ai", "tool_audit", "tool_backups", "tool_bulk", "tool_catalog", "tool_config", "tool_dict", "tool_entries",
         "tool_files", "tool_gates", "tool_jobs", "tool_menus", "tool_mygates", "tool_query", "tool_remote", "tool_sessions", "tool_test",
         "tool_viewers", "tool_voc", "tool_home", "mymenu"]


def load():
    src = {}
    for f in os.listdir(BP):
        p = os.path.join(BP, f)
        if os.path.isfile(p):
            with open(p, encoding="latin-1") as fh:
                src[f] = fh.read()
    return src


def code(text):
    out = []
    for ln in text.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s;\*.*$", "", ln).rstrip())
    return "\n".join(out)


def flat(s):
    return re.sub(r"\s+", " ", s)


def block(text, label):
    m = re.search(r"^" + re.escape(label) + r":\n(.*?)\n[ \t]*return[ \t]*$", text, re.S | re.M)
    return m.group(1) if m else ""


def checks(src):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    c = {k: code(v) for k, v in src.items()}
    std = flat(c.get("tk_std", ""))
    ck("S1 $tk_std 'keys' adds Ctrl-T theme and Ctrl-K keys, each taken off the function-key row, and View > Theme and Help > Keys",
       "call $tk_keys('add', keys, 'ctrl-t', 'theme', 'theme', '', 1) keys<dcount(keys, @fm), TK.K.ROW> = 0" in std
       and "call $tk_keys('add', keys, 'ctrl-k', 'keys', 'keys', '', 1) keys<dcount(keys, @fm), TK.K.ROW> = 0" in std
       and "call $tk_keys('menu', keys, 'theme', '&View', '&Theme', '', '')" in std and "call $tk_keys('menu', keys, 'keys', '&Help', '&Keys', '', '')" in std, std[:200])
    ck("S2 $tk_std 'theme' is $tk_theme with the library's repaint; 'keylist' shows the registry's keylist for the pane in a box",
       "case op = 'theme' call $tk_theme(1, chg, tmsg) ret = chg : @fm : tmsg" in std
       and "call $tk_keys('keylist', keys, pane, kl, '', '', '')" in std and "call $sl_msgbox('run', hw, scr, '', hb)" in std)
    tth = flat(c.get("tk_theme", ""))
    ck("S3 $tk_theme: the library's next, set as the program's choice, kept for the person; nothing when the terminal has no colour",
       "call $sl_theme('next', now, '', '', '', want) if want = now then" in tth and "call $sl_theme('set', want, 'asked', '', '', setr)" in tth
       and "call $sl_theme('save', now, '', '', '', kept)" in tth and tth.find("('set', want") < tth.find("('save', now"), tth[:200])
    bad = []
    users = [k for k, v in c.items() if "$tk_std('keys'" in v and k != "tk_std"]
    for p in users:
        v = c[p]
        th = re.search(r"case (?:[a-z][\w.]* = 'ctrl-t'|act = 'theme')[^\n]*\n\s*call \$tk_std\('theme'", v)        # 9 Nov 26 (S.181): any key variable (!CED()'s is c.key)
        kl = re.search(r"case (?:[a-z][\w.]* = 'ctrl-k'|act = 'keys')[^\n]*\n\s*call \$tk_std\('keylist'", v)
        if not (th and kl):
            bad.append(p)
    ck("S4 every program that adds the shared keys handles Ctrl-T through $tk_std('theme' and Ctrl-K through $tk_std('keylist'", users and not bad, "%d users, wrong: %s" % (len(users), bad))
    missing = [p for p in PAGES if p not in users]
    ck("S5 the 20 tool pages, the home screen and MY.MENU add the shared keys", not missing, missing)
    readers = sorted(k for k, v in c.items() if "config('SCREENTHEME')" in v.replace('"', "'") and k not in ("sl_theme", "config"))
    ck("S6 only sl_theme reads CONFIG('SCREENTHEME') to choose a theme; every other program asks $sl_theme 'site'", not readers, readers)
    slt = c.get("sl_theme", "")
    rid = flat(block(slt, "theme.record.id")).strip()
    st = flat(block(slt, "site.theme"))
    sv = flat(block(slt, "save.theme"))
    ck("S7 the person's theme is the record theme.<login name> of &menus& in the session's account; site reads it before SCREENTHEME, save writes a NAME only",
       rid == "st.id = 'theme.' : downcase(@logname)" and "open '&menus&' to st.f then" in st and st.find("&menus&") < st.find("SCREENTHEME")
       and "locate sv.name in thorder<1> setting sv.i else return" in sv and "write sv.name to sv.f, st.id on error" in sv
       and "openseq" not in slt.lower() and "openpath" not in slt.lower() and "oswrite" not in slt.lower(), (rid, st[:120]))
    sed = c.get("sed", "")
    fsed = flat(sed)
    ck("S8 SED: Ctrl-T and Ctrl-K bound only when free; kill line Esc K, toggle Esc T, go to Esc G, refresh F5 and Ctrl-L, run F9; View and Help menus with Theme, Refresh, Keys",
       "if seq(action.list[20, 1]) = 0 then action.list[20, 1] = char(F.THEME)" in fsed and "if seq(action.list[11, 1]) = 0 then action.list[11, 1] = char(F.KEYS)" in fsed
       and "key.rec<-1> = '@[K'" in sed and "key.rec<-1> = '@[T'" in sed and "key.rec<-1> = '@[G'" in sed
       and "key.rec<-1> = '@[[15~':@VM:'@[[[E':@VM:'@L'" in sed and "key.rec<-1> = '@[[20~'" in sed
       and "bar.titles := @fm : '&View' : @fm : '&Help'" in sed and "ml = '&Theme' ; ma = F.THEME ; gosub add.item" in sed
       and "ml = '&Keys in use' ; ma = F.KEYS ; gosub add.item" in sed and "if action = F.THEME then gosub do.theme" in fsed
       and "call $tk_theme(0, thm.chg, thm.msg)" in sed)
    dbg = c.get("debug", "")
    fdbg = flat(dbg)
    ck("S9 the debugger: F5 refresh, F9 run, Ctrl-T theme, Ctrl-K keys, Ctrl-L redraw, Esc K / Esc T, Esc or F10 the menu bar (Run View Help)",
       "case n = K$F5 and full.screen gosub relayout" in fdbg and "case n = K$F9 gosub dbg.breakpoint(BRK$RUN, 0)" in fdbg
       and "case n = 20 and full.screen gosub dbg.theme" in fdbg and "case n = 11 gosub dbg.keys" in fdbg and "case n = 12 and full.screen gosub relayout" in fdbg
       and "case upcase(dk.c) = 'K'" in dbg and "case upcase(dk.c) = 'T'" in dbg and "case n = 27 or n = K$F10" in dbg
       and "dm.m = '&Run'" in dbg and "dm.m = '&View'" in dbg and "dm.m = '&Help'" in dbg and "call $tk_theme(0, dt.chg, dt.msg)" in dbg
       and "case dm.code = 'f9' ; dm.cmd = char(K$F9)" in dbg)
    ide = c.get("ide", "")
    fide = flat(ide)
    ck("S10 the IDE: F5 and Ctrl-L refresh, F9 run, Shift-F9 catalog, Alt-G go to, Ctrl-T theme, Ctrl-K keys; the editor passes Ctrl-T and Ctrl-K; the Theme command is $tk_theme",
       "case edata = 'f5' or edata = 'ctrl-l' cmd = 'refresh'" in fide and "case edata = 'f9' cmd = 'run'" in fide and "case edata = 'shift-f9' cmd = 'catalog'" in fide
       and "case edata = 'alt-g' cmd = 'goto'" in fide and "case edata = 'ctrl-t' cmd = 'theme'" in fide and "case edata = 'ctrl-k' cmd = 'keys'" in fide
       and "mw{'passkeys'} = 'ctrl-e' : @vm : 'ctrl-t' : @vm : 'ctrl-k'" in ide and "case cmd = 'theme' call $tk_theme(1, th.chg, th.msg)" in fide
       and "case cmd = 'keys' call $tk_std('keylist'" in fide)

    # S.180 (the owner: "all features available on a page need to appear somewhere on the menus"): a registry page's every keyed action is on a menu;
    # the keys that only move within a box (and Esc, which opens the bar or goes back) are not actions of their own
    nav = {"up", "down", "left", "right", "home", "end", "pgup", "pgdn", "tab", "shift-tab", "bs", "esc"}
    gaps = []
    for p, v in sorted(c.items()):
        if p in ("tk_std", "tk_aipage", "tool_tktest", "tk_keys") or "$tk_keys('menu'" not in v:
            continue
        adds = re.findall(r"\$tk_keys\('add',\s*\w+(?:\.\w+)?,\s*'([^']*)',\s*'[^']*',\s*'([^']*)'", v)
        menued = set(re.findall(r"\$tk_keys\('menu',\s*\w+(?:\.\w+)?,\s*'([^']*)'", v))
        if "$tk_std('keys'" in v:
            menued |= {"theme", "keys"}
        for key, act in adds:
            if key in nav or act in ("menu", "back", "cancel") or act in menued:
                continue
            gaps.append("%s:%s=%s" % (p, key, act))
    ck("S11 every keyed action of a registry page is on its menus (the keys that only move, and Esc, aside)", not gaps, gaps)
    mm = {}
    for n in (11225, 11226, 11227, 11228, 11229, 11230, 14004, 14019):
        mp = os.path.join(os.path.dirname(BP), "messages", str(n))
        if os.path.exists(mp):
            mm[n] = open(mp, encoding="latin-1").read()
    mcmds = set(re.findall(r"~[^~|]*~([a-z.0-9]+)", "|".join(mm.values())))
    dkey = block(ide, "do.key")
    kcmds = set(re.findall(r"cmd = '([a-z.0-9]+)'", dkey)) - {"menu"}
    ck("S12 every command the IDE's keys run is on one of its menus (14019 the Edit menu among them)", kcmds and kcmds <= mcmds and 14019 in mm, sorted(kcmds - mcmds))
    # S13 SED: every action the default layout gives a key is on a menu, the moves within the text, Return, Tab, Backspace and Cancel (Ctrl-G) aside
    rsed = src.get("sed", "")                     # the raw text: each key.rec line names its action in its ;* comment
    db = rsed[rsed.index("set.default.bindings:"):rsed.index("set.emacs.bindings:")] if "set.emacs.bindings:" in rsed else ""
    keyed = [n for v, n in re.findall(r"key\.rec<-1> = ([^;\n]*);\*\s*(F\.[A-Z.]+)", db) if v.strip() not in ("''", "")]
    mb = sed[sed.index("build.menu.defs:"):] if "build.menu.defs:" in sed else ""
    inm = set(re.findall(r"ma = (F\.[A-Z.]+)", mb))
    moves = {"F.HOME", "F.END", "F.LEFT", "F.RIGHT", "F.UP", "F.DOWN", "F.BACKSPACE", "F.TAB", "F.NEWLINE", "F.CANCEL"}
    sgaps = sorted(set(keyed) - inm - moves)
    ck("S13 SED: every action the default layout gives a key is on a menu (the moves, Return, Tab, Backspace and Cancel aside)", keyed and not sgaps, sgaps)
    return out


def mutants(src):
    def m(name, f, old, new):
        s = dict(src)
        s[f] = src[f].replace(old, new, 1)
        return (name, s, s[f] != src[f])
    return [
        m("the theme row stays on the key row", "tk_std", "call $tk_keys('add', keys, 'ctrl-t', 'theme', 'theme', '', 1)\n         keys<dcount(keys, @fm), TK.K.ROW> = 0",
          "call $tk_keys('add', keys, 'ctrl-t', 'theme', 'theme', '', 1)"),
        m("no View > Theme", "tk_std", "call $tk_keys('menu', keys, 'theme', '&View', '&Theme', '', '')", "null"),
        m("the theme is not repainted", "tk_std", "call $tk_theme(1, chg, tmsg)", "call $tk_theme(0, chg, tmsg)"),
        m("the theme is not kept", "tk_theme", "call $sl_theme('save', now, '', '', '', kept)", "kept = 1"),
        m("a page's Ctrl-T does its own thing", "tool_voc", "call $tk_std('theme', ctx, keys, '', std.r)", "call $sl_theme('next', '', '', '', '', std.r)"),
        m("a page lacks the shared keys", "tool_audit", "call $tk_std('keys', ctx, keys, '', '')", "null"),
        m("a program reads SCREENTHEME itself", "spview", "call $sl_theme('site', '', '', '', '', site.theme)", "site.theme = downcase(trim(config('SCREENTHEME')))"),
        m("the theme is kept per account, not per person", "sl_theme", "st.id = 'theme.' : downcase(@logname)", "st.id = 'theme'"),
        m("SED takes Ctrl-T whatever is bound", "sed", "if seq(action.list[20, 1]) = 0 then action.list[20, 1] = char(F.THEME)", "action.list[20, 1] = char(F.THEME)"),
        m("SED's kill line keeps Ctrl-K", "sed", "key.rec<-1> = '@[K'", "key.rec<-1> = '@K'"),
        m("SED runs on F5 again", "sed", "key.rec<-1> = '@[[20~'", "key.rec<-1> = '@[[15~'"),
        m("the debugger runs on F5 again", "debug", "case n = K$F9             ;* Free run", "case n = K$F5             ;* Free run"),
        m("the debugger has no View menu", "debug", "dm.m = '&View'", "dm.m = '&Vue'"),
        m("the IDE's F5 runs again", "ide", "case edata = 'f5' or edata = 'ctrl-l'\n         cmd = 'refresh'", "case edata = 'f5' or edata = 'ctrl-l'\n         cmd = 'run'"),
        m("the IDE's editor keeps Ctrl-T", "ide", "mw{'passkeys'} = 'ctrl-e' : @vm : 'ctrl-t' : @vm : 'ctrl-k'", "mw{'passkeys'} = 'ctrl-e' : @vm : 'ctrl-k'"),
        m("S11: a page's box key is on no menu", "tool_dict", "call $tk_keys('menu', keys, 'nextpane', '&View', '&Next box', '', '')", "null"),
        m("S12: an IDE key runs a command no menu has", "ide", "case edata = 'f4'\n         cmd = 'nexterr'", "case edata = 'f4'\n         cmd = 'nexterrx'"),
        m("S13: a SED keyed action is on no menu", "sed", "   ml = 'Insert a control character, &quoted' ; ma = F.QUOTE.CHAR ; gosub add.item\n", ""),
    ]


def main():
    if not os.path.isdir(BP):
        print("test-tkstd-units: CANNOT RUN - no %s" % BP)
        return 2
    src = load()
    for need in ("tk_std", "tk_theme", "sl_theme", "sed", "debug", "ide"):
        if need not in src:
            print("test-tkstd-units: CANNOT RUN - no %s in %s" % (need, BP))
            return 2
    if "--selftest" in sys.argv:
        base = checks(src)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the real files already fail:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        missed = 0
        ms = mutants(src)
        for name, s, applied in ms:
            if not applied:
                print("  [NOT APPLIED] %s" % name)
                missed += 1
                continue
            caught = [n for n, ok, _ in checks(s) if not ok]
            print("  [%s] %s" % ("caught" if caught else "MISSED", name))
            missed += 0 if caught else 1
        print("test-tkstd-units --selftest: %d mutant(s), %d not caught" % (len(ms), missed))
        return 1 if missed else 0
    print("gpl.bp : %s" % BP)
    res = checks(src)
    fails = 0
    for n, ok, d in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", n, "" if ok or d == "" else "  <- " + str(d)[:300]))
        fails += 0 if ok else 1
    print("test-tkstd-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
