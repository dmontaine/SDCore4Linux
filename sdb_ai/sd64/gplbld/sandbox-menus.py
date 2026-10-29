#!/usr/bin/env python3
#
# sandbox-menus.py - the administrator's control of the home screen: SET.TILE and the menu management page tool.menus (S.75, plan .claude/plan-fullscreen-toolkit.md section 13), on a
# pseudo-terminal.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-menus.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  It uses sandbox-home.py's setup (the same fixture accounts, ordinary sessions through sandbox-gates.py, the sandbox starting at the terminal) and its session class.
#
# START-HISTORY:
# 22 Oct 26 dm  New (S.75: tiles off per account, the Terminal tile off as a wall, tool.menus).
# END-HISTORY
#
# WHAT IS HELD.  SET.TILE (one account at a time; no setting for every account; Sign out refused; names and accounts checked; an ordinary account cannot run it), the home screen
# leaving a tile out and closing up the page, the Terminal tile off keeping an account that starts in the menu from the prompt (a window too small ends the session) and not touching
# one that starts at the prompt, and tool.menus: the page, the selection, the command shown in a box with Run / Cancel, the typed account name for the Terminal tile, the answer of the
# command on the status line, the register read again, the start setting and the system default, and the tile on the administrator's own home screen only.  NOT HELD: a mouse click
# on the page, the page in a window bigger than 140 by 43, tiles defined in page records (not built).
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sandbox_home_for_menus", os.path.join(HERE, "sandbox-home.py"))
sh = importlib.util.module_from_spec(spec)
sys.modules["sandbox_home_for_menus"] = sh
spec.loader.exec_module(sh)
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
file_word, tiles_file, set_default = sh.file_word, sh.tiles_file, sh.set_default


def main():
    try:
        sh.setup("sandbox-menus.py")
        say("\n--- tiles the administrator turns off (SET.TILE)")
        set_default("menu")
        out = adm("set.tile")
        row("SET.TILE alone says every tile is on", has(out, r"^Every tile is on$"), repr(out[:3]))
        out = adm("set.tile zzhm editor off")
        f17 = g.reg_read("zzhm")[16] if len(g.reg_read("zzhm")) > 16 else ""
        row("set.tile zzhm editor off: 'Tile editor is now off for zzhm' (11875), and field 17 of zzhm's register record is editor on the disk; no list for every account is made",
            has(out, r"Tile editor is now off for zzhm") and f17 == "editor" and tiles_file() is None, repr((out[:3], f17, tiles_file())))
        h = H("zzhm")
        T = h.text()
        row("the Editor tile is gone from zzhm's page, the IDE tile has taken its place at the first position, and the page is still the whole page",
            h.home() and "Editor" not in T and "Terminal" in T and "IDE" in h.line(10)[3:12] and "My tools" in T, h.line(10)[:60])
        h.end()
        h = H("zzhd")
        row("...and zzhd, which has nothing turned off, still has the Editor tile: tiles are on as delivered and are turned off one account at a time", h.home() and "Editor" in h.text() and "IDE" in h.text(), "")
        h.end()
        out = adm("set.tile zzhm editor off")
        row("the same again says it was already off and changes nothing (11877)", has(out, r"Tile editor was already off for zzhm; nothing changed"), repr(out[:3]))
        out = adm("set.tile zzhd ide off")
        f17 = g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else ""
        row("set.tile zzhd ide off: field 17 of zzhd's register record is ide on the disk", has(out, r"Tile ide is now off for zzhd") and f17 == "ide", repr((out[:3], f17)))
        h = H("zzhd")
        T = h.text()
        h2 = H("zzhm")
        T2 = h2.text()
        row("...zzhd's page lacks the IDE tile and keeps the Editor; zzhm's lacks the Editor and keeps the IDE: one account's switch does not reach another",
            h.home() and "IDE" not in T and "Editor" in T and "Terminal" in T and h2.home() and "IDE" in T2 and "Editor" not in T2, "")
        h.end()
        h2.end()
        out = adm("set.tile zzhd ide on")
        f17 = g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else ""
        row("set.tile zzhd ide on: the field is empty again", has(out, r"Tile ide is now on for zzhd") and f17 == "", repr((out[:3], f17)))
        out = adm("set.tile zzhd signout off")
        row("SIGN OUT cannot be turned off: refused (11878) and nothing is written",
            has(out, r"Sign out cannot be turned off") and (g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else "") == "", repr(out[:3]))
        out = adm("set.tile nobody ide off")
        row("an account that is not in the register is refused (Account name is invalid)", has(out, r"Account name is invalid"), repr(out[:3]))
        out = adm("set.tile all ide off")
        row("there is no 'all': the word is taken for an account name and refused, and no file for every account is made", has(out, r"Account name is invalid") and tiles_file() is None, repr((out[:3], tiles_file())))
        out = adm("set.tile zzhd Bad_Name off")
        row("a tile name with a capital or an underscore is refused (11881)", has(out, r"is not a tile name"), repr(out[:3]))
        out = adm("set.tile zzhd ide maybe")
        row("a state that is not on or off is the usage (11874)", has(out, r"set\.tile account tile \{on \| off\}"), repr(out[:3]))
        out = adm("set.tile zzhd zzcustom off")
        row("a tile that is not a standard one is accepted and said not to be (11883): it applies to a tile of that name in a page record", has(out, r"Tile zzcustom is now off for zzhd") and has(out, r"zzcustom is not a standard tile"), repr(out[:4]))
        adm("set.tile zzhd zzcustom on")
        out = g.plain("zzhd", ["set.tile zzhd ide off"])
        row("an ordinary account cannot run it: the verb is not in its VOC", has(out, r"not in your VOC"), repr(out[:3]))
        adm("set.tile zzhm switch off")
        adm("set.tile zzhm terminal off")
        out = adm("set.tile")
        row("SET.TILE alone lists them, one line for each account that has any ('Tiles off for zzhm: editor switch terminal')", has(out, r"Tiles off for zzhm: editor switch terminal"), repr(out[:4]))
        h = H("zzhm")
        T = h.text()
        row("zzhm with Switch account and Terminal off: neither is on the page (header and group), Keys is still there, and the group 'Everyone' has no empty place for them",
            "Switch account" not in T and "Terminal" not in T and "Keys" in T and "Sign out" in T and "Everyone" in T, T[-300:])
        h.key("f10", idle=0.8)
        h.key("right", idle=0.6)
        h.typed("t", idle=1.0)
        row("...the Go menu's Terminal entry cannot be chosen (its letter does nothing): the person is not given the prompt, and the session is alive",
            h.alive() and not h.prompt(), h.text()[-200:])
        h.key("esc", idle=0.5)
        row("...Esc closes the menu and the page is still there", h.alive() and "Sign out" in h.text() and not h.prompt(), "")
        h.end()
        h = H("zzhm", cols=100, rows=30, settle=4.5)
        row("THE TERMINAL TILE OFF IS A WALL for an account that starts in the menu: a window too small to take the screen does not leave zzhm at the prompt - the size message is shown and the session ends",
            not h.alive() and re.search(r"140", h.text()) is not None and not h.prompt(), h.text()[-300:])
        h.end()
        h = H("zzhd", cols=100, rows=30)
        row("an account that has the Terminal tile (zzhd) is left at the prompt in the same window, as before", h.alive() and h.prompt(), h.text()[-200:])
        h.end()
        adm("set.tile zzht terminal off")
        h = H("zzht")
        row("an account that STARTS at the prompt (zzht) keeps it whatever tiles are off: the wall is for the prompt the screen gives", h.alive() and h.prompt() and not h.home(), h.text()[-200:])
        h.end()
        adm("set.tile zzht terminal on")
        adm("set.tile zzhm switch on")
        adm("set.tile zzhm terminal on")
        adm("set.tile zzhm editor on")
        out = adm("set.tile")
        row("everything turned on again: SET.TILE alone says every tile is on and the account fields are empty",
            has(out, r"^Every tile is on$") and (g.reg_read("zzhm")[16] if len(g.reg_read("zzhm")) > 16 else "") == "", repr(out[:3]))
        h = H("zzhm")
        row("...and zzhm's page is whole again (Editor and Terminal and Switch account)", h.home() and "Editor" in h.text() and "Switch account" in h.text(), "")
        h.end()

        say("\n--- menu management (tool.menus): the administrator's page for the tiles and where an account starts")
        set_default("terminal")
        out = g.plain("zzhd", ["tool.menus"])
        row("an ordinary account cannot reach it: tool.menus is in SDSYS's VOC only", has(out, r"not in your VOC"), repr(out[:3]))
        h = H(admin=True)
        h.typed("tool.menus\r", idle=2.5)
        T = h.text()
        if "What this means" not in T:
            dump(h)
            bail("tool.menus never drew its page, so no row below can be believed")
        row("the page: boxes Accounts, Menu, What this means, System default and Help; the function keys 'F1 help  Enter change  Tab pane  F5 refresh  ^Q quit'",
            all(w in T for w in ("Accounts", "Menu", "What this means", "System default", "Help")) and h.line(42).startswith("F1 help  Enter change  Tab pane  F5 refresh  ^Q quit"), repr(h.line(42)))        # (the bar adds "Esc menu" at the end, 29 Oct 26)
        row("the accounts, in order, without SDSYS: zzhd zzhm zzhs zzht zzhv (zzhs is marked suspended), each with where it starts (own word, or 'default (terminal)')",
            all(re.search(p, h.line(r)) for p, r in ((r"zzhd\s+OTHER\s+default \(terminal\)", 3), (r"zzhm\s+OTHER\s+menu", 4), (r"zzhs\s+OTHER \(s\)\s+menu", 5), (r"zzht\s+OTHER\s+terminal", 6), (r"zzhv\s+OTHER\s+menu", 7)))
            and "sdsys" not in T.replace("administrator", ""), repr([h.line(r)[:60] for r in range(2, 9)]))
        row("the first account is selected (reverse video on its row) and the Menu box is for it: 'Starts in' and the fourteen standard ids (the six tiles of the account, the seven development tiles and the Recent group), all on ([x])",
            "r" in h.style(3, 5)[2] and "Starts in" in h.line(2)[72:] and len(re.findall(r"\[x\] [A-Z]", T)) == 14, repr((h.style(3, 5), h.line(2)[72:100], len(re.findall(r"\[x\] [A-Z]", T)))))
        h.key("down")
        row("Down selects the next account (zzhm): its row is in reverse video and zzhd's is not", "r" in h.style(4, 5)[2] and "r" not in h.style(3, 5)[2], repr((h.style(3, 5), h.style(4, 5))))
        h.key("up")
        h.key("tab")
        row("Tab goes to the Menu pane: the status line says [Menu] and the 'Starts in' row is selected", h.line(40).startswith("[Menu]") and "r" in h.style(2, 75)[2], repr((h.line(40), h.style(2, 75))))
        h.key("down")
        h.key("down")
        h.key("down")
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter on the IDE row shows the command in a box with its effect and Run / Cancel: 'set.tile zzhd ide off' and 'this will run:'",
            "set.tile zzhd ide off" in T and "this will run" in T and "Run" in T and "Cancel" in T and "left off zzhd's home screen" in T, T[-500:])
        h.key("esc", idle=0.8)
        f17 = g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else ""
        row("Esc is Cancel: nothing ran - field 17 of zzhd's register record is still empty - and the status line says so", f17 == "" and "nothing was run" in h.line(40), repr((f17, h.line(40))))
        h.key("enter", idle=1.0)
        h.typed("r", idle=2.0)
        f17 = g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else ""
        row("Enter and the letter R run it: field 17 is ide on the disk, and the line under the page is the command's own answer 'Tile ide is now off for zzhd'",
            f17 == "ide" and "Tile ide is now off for zzhd" in h.line(40), repr((f17, h.line(40))))
        T = h.text()
        row("the page is read from the register again: zzhd's row lists 'ide' under Tiles off and the IDE row of the Menu box is [ ]",
            re.search(r"zzhd\s+OTHER\s+default \(terminal\)\s+no\s+ide", h.line(3)) is not None and re.search(r"\[ \] IDE", T) is not None and len(re.findall(r"\[x\] [A-Z]", T)) == 13, repr((h.line(3)[:80], len(re.findall(r"\[x\] [A-Z]", T)))))
        h.key("down")                               # one Down from the IDE row to Terminal (two before S.88 g-P1: the Record editor row lay between them)
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter on the Terminal row says plainly what it does - the prompt is removed for an account that starts in the screen - and will ask for the account's name",
            "set.tile zzhd terminal off" in T and "never given the command prompt" in T, T[-600:])
        h.typed("r", idle=1.0)
        row("...Run asks for the name to be typed before anything runs", "zzhd" in h.text() and re.search(r"[Tt]ype", h.text()) is not None, h.text()[-400:])
        h.typed("nope\r", idle=1.5)
        f17 = g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else ""
        row("a name that is not the account's runs nothing: field 17 is still ide, and the status line says what was typed is not zzhd", f17 == "ide" and "not zzhd" in h.line(40), repr((f17, h.line(40))))
        h.key("enter", idle=1.0)
        h.typed("r", idle=1.0)
        h.typed("zzhd\r", idle=2.0)
        f17 = g.reg_read("zzhd")[16] if len(g.reg_read("zzhd")) > 16 else ""
        row("the right name runs it: field 17 is 'ide terminal' and the command's own answer is under the page", f17 == "ide terminal" and "Tile terminal is now off for zzhd" in h.line(40), repr((f17, h.line(40))))
        T = h.text()
        row("What this means, for an account that starts in the screen (zzhd follows the default, terminal) with the Terminal tile off: it starts at the prompt, so it keeps the prompt",
            "zzhd starts in the command prompt" in T and "has the prompt" in T, T[-700:])
        h.key("down", idle=0.4)
        h.key("down", idle=0.4)
        h.key("down", idle=0.4)
        h.key("enter", idle=0.8)
        row("the Sign out row cannot be changed: the status line says it cannot be turned off, and no box was opened", "Sign out cannot be turned off" in h.line(40) and "this will run" not in h.text(), repr(h.line(40)))
        for _ in range(6):                          # 7 before S.88 g-P1 (Sign out is the eighth row now, own programs the second)
            h.key("up", idle=0.3)
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter on the 'May add own programs' row shows 'modify.account zzhd pins-on' and says what it allows: a command the person could type, no access added",
            "modify.account zzhd pins-on" in T and "its own programs" in T and "adds no access" in T, T[-600:])
        h.typed("r", idle=2.0)
        f18 = g.reg_read("zzhd")[17] if len(g.reg_read("zzhd")) > 17 else ""
        row("Run: field 18 is yes on the disk, the answer is 'Account zzhd may add its own programs to the home screen: yes', and the list shows Own yes",
            f18 == "yes" and "may add its own programs to the home screen: yes" in h.line(40) and re.search(r"zzhd\s+OTHER\s+default \(terminal\)\s+yes", h.line(3)) is not None, repr((f18, h.line(40), h.line(3)[:70])))
        h.key("enter", idle=1.0)
        h.typed("r", idle=2.0)
        f18 = g.reg_read("zzhd")[17] if len(g.reg_read("zzhd")) > 17 else ""
        row("Enter again turns it off (pins-off): field 18 is no", f18 == "no" and "may add its own programs to the home screen: no" in h.line(40), repr((f18, h.line(40))))
        h.key("up", idle=0.3)
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter on the 'Starts in' row offers three choices: menu, terminal, the system default (terminal)", "menu (the home screen)" in T and "terminal (the command prompt)" in T and "the system default (terminal)" in T, T[-500:])
        h.key("down")
        h.key("enter", idle=1.0)
        row("...the second choice, terminal, shows 'modify.account zzhd start-terminal' in the box", "modify.account zzhd start-terminal" in h.text(), h.text()[-300:])
        h.typed("r", idle=2.0)
        f16 = g.reg_read("zzhd")[15]
        row("Run: field 16 is terminal on the disk and the answer is 'Account zzhd starts at: terminal'", f16 == "terminal" and "Account zzhd starts at: terminal" in h.line(40), repr((f16, h.line(40))))
        row("...the list shows it as zzhd's own word", re.search(r"zzhd\s+OTHER\s+terminal\s+no\s+ide terminal", h.line(3)) is not None, h.line(3)[:80])
        h.key("tab")
        h.key("enter", idle=1.0)
        T = h.text()
        row("the Default pane: Enter offers menu and terminal", "Where an account with no setting of its own starts" in T and "menu (the home screen)" in T, T[-400:])
        h.key("enter", idle=1.0)
        row("...menu is 'set.start.default menu' with its effect", "set.start.default menu" in h.text() and "will start in the home screen" in h.text(), h.text()[-400:])
        h.typed("r", idle=2.0)
        row("Run: the file start.default says menu, the answer is under the page, and the System default box says home screen (menu)",
            file_word() == "menu" and "start at: menu" in h.line(40) and "home screen (menu)" in h.text(), repr((file_word(), h.line(40))))
        row("...zzht, with its own word terminal, is not changed; zzhv (own menu) neither: the page lists both as they were",
            re.search(r"zzht\s+OTHER\s+terminal", h.line(6)) is not None and re.search(r"zzhv\s+OTHER\s+menu", h.line(7)) is not None, repr((h.line(6)[:50], h.line(7)[:50])))
        h.key("f5", idle=1.0)
        row("F5 reads the register again", "read the register again" in h.line(40), repr(h.line(40)))
        # 26 Oct 26 (S.75, home): the seven development tiles and the Recent group have rows of their own
        h.key("tab", idle=0.5)
        h.key("tab", idle=0.5)
        T = h.text()
        row("the Menu box has a row for each standard id - Files, Vocabulary, Dictionary, Queries, Bulk update, Programs, Tests and the Recent group after the six it had (S.88 g-P1 took the Record editor row away): 16 rows, the last on row 17 with its [?]; the explanation starts under the box (row 22) and the key hints are one line under the system default (row 37)",
            all(re.search(p, T) for p in (r"\[x\] Files\s+files", r"\[x\] Vocabulary\s+voc", r"\[x\] Dictionary\s+dict", r"\[x\] Queries\s+query", r"\[x\] Bulk update\s+bulk", r"\[x\] Programs\s+catalog", r"\[x\] Tests\s+test", r"\[x\] Recent group\s+recent"))
            and h.line(17)[134:137] == "[?]" and "Recent group" in h.line(17) and "What this means" in h.line(22) and "Help" in h.line(36) and "Arrows move" in h.line(37), repr((h.line(17)[72:140], h.line(22)[:30], h.line(36)[:30])))
        for _ in range(8):                          # 9 before S.88 g-P1: the Files row is the ninth row now (starts in, own programs, editor, ide, terminal, keys, switch, signout, files)
            h.key("down", idle=0.3)
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter on the Files row shows the command and its effect: 'set.tile zzhd files off', and the Files tile left off zzhd's home screen", "set.tile zzhd files off" in T and "The Files tile will be left off zzhd's home screen" in T, T[-500:])
        h.key("esc", idle=0.8)
        for _ in range(7):
            h.key("down", idle=0.3)
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter on the Recent group row (the last) shows 'set.tile zzhd recent off' and says the group will not be on the home screen and the person cannot turn it on", "set.tile zzhd recent off" in T and "The Recent group will not be on zzhd's home screen" in T and "cannot turn it on" in T, T[-500:])
        h.typed("r", idle=2.0)
        r = g.reg_read("zzhd")
        f17 = r[16] if len(r) > 16 else ""
        row("Run: field 17 is 'ide terminal recent', the answer is 'Tile recent is now off for zzhd' (recent is standard: no note), and the row reads [ ] Recent group",
            f17 == "ide terminal recent" and "Tile recent is now off for zzhd" in h.line(40) and re.search(r"\[ \] Recent group", h.text()) is not None and "not a standard tile" not in h.text(), repr((f17, h.line(40))))
        h.key("enter", idle=1.0)
        T = h.text()
        row("Enter again offers to turn it on: 'set.tile zzhd recent on' and says the person may turn it on in the View menu", "set.tile zzhd recent on" in T and "View menu" in T, T[-400:])
        h.typed("r", idle=2.0)
        r = g.reg_read("zzhd")
        row("Run: field 17 is 'ide terminal' again", (r[16] if len(r) > 16 else "") == "ide terminal" and re.search(r"\[x\] Recent group", h.text()) is not None, repr(h.line(40)))
        h.key("ctrl-q", idle=1.5)
        row("Ctrl-Q leaves the page and the prompt is there (the administrator's session)", h.prompt() and "What this means" not in h.text(), h.text()[-200:])
        h.end()

        say("\n--- a person's own programs on the home screen (MY.MENU), when the administrator allows it")
        out = g.plain("zzht", ["my.menu"])
        row("delivered off: MY.MENU in an account the administrator has not allowed (zzht) says so (11886) and draws nothing",
            has(out, r"has not allowed this account to add its own programs") and not has(out, r"My programs"), repr(out[:3]))
        out = adm("modify.account zzhm pins-on pins-off")
        row("pins-on with pins-off in one command is refused before anything changes (11791)", has(out, r"pins-on and pins-off set the same access to different states"), repr(out[:3]))
        out = adm("modify.account zzhm pins-on")
        f18 = g.reg_read("zzhm")[17] if len(g.reg_read("zzhm")) > 17 else ""
        row("modify.account zzhm pins-on: 'Account zzhm may add its own programs to the home screen: yes' (11885), field 18 is yes", has(out, r"Account zzhm may add its own programs to the home screen: yes") and f18 == "yes", repr((out[:3], f18)))
        out = adm("modify.account zzhm pins-on")
        row("the same word again says it already had that access (10080)", has(out, r"already had that access"), repr(out[:3]))
        h = H("zzhm")
        T = h.text()
        row("zzhm's home screen now has a group 'My programs' with one tile, 'Add a program' (change this list); the standard tiles are all still there",
            h.home() and "My programs" in T and "Add a program" in T and "change this list" in T and "Editor" in T and "IDE" in T, T[:400])
        h.typed("a", idle=0.5)
        h.key("enter", idle=2.0)
        T = h.text()
        row("Enter on it starts MY.MENU: the page 'My programs' with the empty-list line, and the keys Ctrl-N add, Enter change, Del remove, U up, D down",
            "You have not added a program yet" in T and h.line(42).startswith("^N add  ^Q quit"), repr(h.line(42)))
        h.typed("\x0e", idle=0.8)                      # Ctrl-N (it was F2; owner answer 20, 29 Oct 26)
        # S.88: one form (label, command, glyph, wait): Tab between the entries, Return in an entry presses Save; the wait entry starts as y
        h.typed("Orders\twho.am.i\r", idle=1.2)
        T = h.text()
        row("Ctrl-N shows the form with the label, the command, the glyph and whether to wait; the item is in the list (Orders, who.am.i, waits yes) and the line under the page says 'added Orders'",
            re.search(r"Orders\s+>>>\s+who\.am\.i\s+yes", T) is not None and "added Orders" in h.line(40), T[-500:])
        rec = g.plain("zzhm", ["CT &menus& home"])
        row("...and it is in the person's own file: the record HOME of &menus& holds Orders and who.am.i", has(rec, r"Orders") and has(rec, r"who\.am\.i"), repr(rec[:6]))
        h.typed("\x0e", idle=0.8)
        h.typed("Alpha\tdate\t\t", idle=0.8)           # label, command, glyph left empty, now in the wait entry (it starts as y)
        h.key("bs", idle=0.3)
        h.typed("n\r", idle=1.2)
        h.typed("u", idle=1.0)                         # U moves it up (it was F4)
        L3, L4 = h.line(3), h.line(4)
        row("a second item (Alpha, date, no wait) goes to the end; F4 moves the selected item up and the selection follows it: Alpha is the first row, Orders the second",
            L3.lstrip(" |").startswith("Alpha") and L4.lstrip(" |").startswith("Orders") and "r" in h.style(3, 5)[2], repr((L3[:50], L4[:50])))
        h.typed("d", idle=1.0)                         # D moves it down (it was F6)
        row("D moves it down again: Orders first, Alpha second", h.line(3).lstrip(" |").startswith("Orders") and h.line(4).lstrip(" |").startswith("Alpha"), repr((h.line(3)[:40], h.line(4)[:40])))
        h.key("down", idle=0.4)
        h.typed("\x1b[3~", idle=1.0)                   # Del removes it (it was F3)
        row("Del asks 'Remove Alpha from your home screen?' with Remove and Cancel", "Remove Alpha from your home screen?" in h.text() and "Cancel" in h.text(), h.text()[-300:])
        h.key("esc", idle=0.8)
        row("Esc is Cancel: Alpha is still in the list", "Alpha" in h.text() and "nothing was removed" in h.line(40), repr(h.line(40)))
        h.typed("\x1b[3~", idle=1.0)
        h.typed("r", idle=1.2)
        row("Del and R remove it: only Orders is left, and the line says 'removed'", "Alpha" not in h.text() and "Orders" in h.text() and "removed" in h.line(40), repr(h.line(40)))
        h.key("ctrl-q", idle=2.0)
        T = h.text()
        row("Ctrl-Q returns to the home screen, rebuilt: the group 'My programs' now has the tile Orders (command who.am.i) after 'Add a program'", h.home() and "Orders" in T and "who.am.i" in T and "Alpha" not in T, T[:500])
        h.typed("o", idle=0.5)
        h.key("enter", idle=2.0)
        T = h.text()
        row("Enter on Orders runs who.am.i exactly as typed at the prompt (Account : zzhm), then asks for Enter (the item says wait)", re.search(r"Account\s*:\s*zzhm", T) is not None and re.search(r"Press Enter to return\s*$", T, re.M) is not None, T[-300:])
        h.typed("\r", idle=2.0)
        row("...and the home screen comes back with the tile still selected", h.home() and "Orders" in h.text(), h.text()[:200])
        h.end()
        adm("modify.account zzhm pins-off")
        h = H("zzhm")
        T = h.text()
        row("pins-off: the group 'My programs' and its tiles are gone from the home screen, though the person's file still holds the item",
            h.home() and "My programs" not in T and "Orders" not in T and has(g.plain("zzhm", ["CT &menus& home"]), r"Orders"), T[:300])
        h.end()
        out = g.plain("zzhm", ["my.menu"])
        row("...and MY.MENU refuses again (11886)", has(out, r"has not allowed this account to add its own programs"), repr(out[:3]))
        adm("set.tile zzhd ide on")
        adm("set.tile zzhd terminal on")
        adm("modify.account zzhd start-default")
        set_default("menu")
        h = H(admin=True)
        T = h.text()
        h2 = H("zzhm")
        T2 = h2.text()
        row("the administrator's home screen has the tile Menu management, in its own group System, and the account holder's page has none",
            h.home() and "Menu management" in T and "System" in T and h2.home() and "Menu management" not in T2 and "System" not in T2, T[:300])
        h2.end()
        h.key("enter", idle=2.5)
        row("Enter on it (it is the first tile) opens the page", "What this means" in h.text(), h.text()[-200:])
        h.key("ctrl-q", idle=1.5)
        row("Ctrl-Q returns to the home screen with the Menu management tile still selected", h.home() and "r" in h.style(10, 5)[2], repr(h.style(10, 5)))
        h.end()
    finally:
        sh.teardown()
    sh.summary("sandbox-menus")


if __name__ == "__main__":
    main()
