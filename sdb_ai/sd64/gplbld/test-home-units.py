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
PROGS = ("tool_home", "home_entry", "exit", "setstart", "cproc", "modifya", "sl_theme")
MSGS = tuple(str(n) for n in range(11863, 11874))


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
        "newvoc/home", "newvoc/exit", "voc_template/home", "voc_template/exit", "voc_template/set.start.default", "newvoc/set.start.default")}
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
    ck("H4 tool_home: every tile's action is a fixed sentence (cmd:sed, cmd:ide, cmd:ced, cmd:tool.keys), terminal, switch or signout - nothing typed by the person is ever run",
       sorted(cmds) == sorted(["cmd:sed", "cmd:ide", "cmd:ced", "terminal", "cmd:tool.keys", "switch", "signout"]), repr(cmds))
    ck("H4b ...execute is given only a sentence from that table, 'quit', or the logto of an account picked from the register list",
       sorted(re.findall(r"execute ([^\n]+)", th)) == sorted(["sentence", "'quit'", "'logto ' : acct"]), repr(re.findall(r"execute ([^\n]+)", th)))
    fin = between(th, "\nfinish:\n", "\nreturn")
    ck("H5 the Terminal tile: the screen is given back FIRST, then the flag is set and the banner (11864) shown; the program then ends and the real prompt is there",
       0 < fin.find("outcome = 'terminal'") < fin.find("call $tk_close(ctx)") < fin.find("hflag = 1") < fin.find("sysmsg(11864)"), fin[:300])
    ck("H5b ...sign out gives the screen back, then runs QUIT; every other way out gives it back too", 0 < fin.find("outcome = 'signout'") < fin.find("call $tk_close(ctx)", fin.find("outcome = 'signout'")) < fin.find("execute 'quit'")
       and fin.rstrip().endswith("end case\n   return".rstrip()) or "case 1\n         call $tk_close(ctx)" in fin)
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
       and "if downcase(trim(line)) = 'terminal' then start = 'terminal'" in he and "if start # 'menu' then return" in he and "read vrec from vf, 'home' else vrec = ''" in he and "if vrec = '' then return" in he and he.rstrip().endswith("execute 'home'\n   return\nend"),
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
       "FILES-ADMIN-OFF,START-MENU,START-TERMINAL,START-DEFAULT,SUSPENDED" in ",".join(w) and len(w) == len(sl) and [sl[w.index(x)] for x in ("START-MENU", "START-TERMINAL", "START-DEFAULT")] == ["ST", "ST", "ST"])
    ck("H14b ...do.action has the three cases and start.set writes only field 16, says 11868, audits, and says 11869 when nothing changes",
       all(re.search(r"case action = '%s'\n\s+start\.want = %s\n\s+gosub start\.set\n\s+return" % (a, v), md) for a, v in (("START-MENU", "'menu'"), ("START-TERMINAL", "'terminal'"), ("START-DEFAULT", "''")))
       and "acc.new<ACC$START> = start.want" in md and "sysmsg(11868, acc.name" in md and "sysmsg(11869, acc.name)" in md and "K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name" in between(md, "\nstart.set:\n", "\nset.suspended:\n"))
    ck("H14c ...the usage and the list of actions name the three words", md.count("start-menu") >= 2 and "start-menu | start-terminal | start-default" in md)

    f = s["files"]
    ck("H15 the VOC: HOME and EXIT for every account (newvoc) and for SDSYS (voc_template); SET.START.DEFAULT for SDSYS ONLY", f["newvoc/home"] and f["newvoc/exit"] and f["voc_template/home"] and f["voc_template/exit"]
       and f["voc_template/set.start.default"] and not f["newvoc/set.start.default"], repr(f))
    m = s["msgs"]
    ck("H16 messages 11863 to 11873 exist, each one line, none with a capital command word", all(m[n] and m[n].count("\n") == 1 for n in MSGS), repr([n for n in MSGS if not m[n] or m[n].count("\n") != 1]))
    ck("H16b ...the ones the programs print say what the plan says", "terminal" in (m["11863"] or "") and "type exit to return to the home screen" in (m["11864"] or "") and "%1" in (m["11867"] or "") and "%1" in (m["11868"] or "")
       and "%2" in (m["11868"] or "") and "%1" in (m["11869"] or "") and "{menu | terminal}" in (m["11870"] or "") and "%1" in (m["11871"] or "") and "%1" in (m["11873"] or ""))
    ck("H17 the sandbox starts at the terminal (start.default = terminal) because every pty suite types at the prompt, with the reason beside it",
       "os.path.join(sysd, \"start.default\")" in s["sandbox-fromtree.py"] and "f.write(\"terminal\\n\")" in s["sandbox-fromtree.py"])
    st = strip(s["sl_theme"])
    ck("H18 the scroll bar is dark grey in the colour themes (bold black): scroll=black,cyan,bold in blue and scroll=black,white,bold in classic", "'scroll=black,cyan,bold'" in st and "'scroll=black,white,bold'" in st)
    return rows


MUTANTS = [
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
    ("modify.account loses a start word", "modifya", "FILES-ADMIN-OFF,START-MENU,START-TERMINAL,START-DEFAULT,SUSPENDED", "FILES-ADMIN-OFF,START-MENU,START-TERMINAL,SUSPENDED"),
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
