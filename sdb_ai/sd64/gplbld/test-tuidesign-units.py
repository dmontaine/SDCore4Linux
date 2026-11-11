#!/usr/bin/env python3
"""test-tuidesign-units.py - the TUI design specification (sdb_ai/sd64/tui-design.md, S.88 p7A, 2 Nov 2026) held against the tree, as text.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tuidesign-units.py
    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tuidesign-units.py --selftest [--from=N]     (mutants; the first of this sitting is M_P7A)

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  The document's rows parse and carry one of the four tags; a PLANNED row names a marker that does NOT occur in the code of sdsys/gpl.bp (so the row
must move to BUILT in the commit that builds it; since 3 Nov 26, when K7 and K8 were built, the document may have no PLANNED row at all); a BUILT row names a check that exists; the document cites no private path.  Against the tree: the 140 by 43 floor
(tk.h, the IDE) and the 140 by 42 default of a session with no answer (gplsrc/tio.h) are what the document says; the page table is exactly the tool_* programs, with
their audience; every page on the common rules opens and draws through the toolkit, has the toolkit's menu bar (draw, key and click once each, drawn before the
frame), F1 help, Ctrl-Q, and F6 to the AI line; no page builds a SCREEN MENUBAR of its own and none binds F10 or F11, except the test app; every page that runs a
command with $tk_run asks $tk_confirm, whose default button is Cancel; the retired tool_masters is gone; and each exception is still an exception (an exempt page
that gains what it is exempt from fails, so the row is taken out by somebody reading it).

***IT READS SOURCE AS TEXT AND RUNS NOTHING.***  That a bar opens, a key reaches its case or a theme looks as it says is the sandbox suites' (sandbox-home.py, the page
suites); the document's evidence column names them and says which are written and not run.

EXEMPTIONS (the document's section 7, which this list must equal for the tool_* programs):
  tool_keys   E1  no menu bar, no Esc rule, no F1: it shows every key before acting on any (owner's answer 18, 29 Oct 2026)
  tool_tktest E2  the registry's throw-away test app: its own SCREEN MENUBAR, F2, F6, F10, F11
  tool_home   E6  the AI line is $tk_ai itself (not $tk_aipage); Ctrl-Q signs out; it follows every other rule
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
GPL = os.path.join(SD64, "sdsys", "gpl.bp")
MSG = os.path.join(SD64, "sdsys", "messages")
DOC = os.path.join(SD64, "tui-design.md")
TAGS = ("BUILT", "PLANNED", "DROPPED", "EXCEPTION", "OPEN")   # OPEN (2 Nov 26 review): put to the owner, not decided - F2's 140x42 default was wrongly called his ruling
EXEMPT = {"tool_keys": "E1", "tool_tktest": "E2", "tool_home": "E6"}
IDE_MENUS = (11225, 11226, 11227, 11228, 11229, 11230, 11654, 14004, 14019)      # 14004: the Tools menu (S.75 DV10, 3 Nov 26); 14019 the Edit menu (S.180, 8 Nov 26)
PRIVATE = (".claude", "/home/", "PROJECT_STATUS", "Opus_TUI", "pCloud", "sdcore-mail")


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def strip_bas(src):
    """BASIC with full-line comments and ;* tails removed (a ;* inside quotes is kept)"""
    out = []
    for line in src.split("\n"):
        if line.lstrip().startswith("*") or line.lstrip().startswith("!"):
            out.append("")
            continue
        q, cut = "", -1
        for i, ch in enumerate(line):
            if q:
                if ch == q:
                    q = ""
            elif ch in "'\"":
                q = ch
            elif line.startswith(";*", i):
                cut = i
                break
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def load():
    s = {"doc": read(DOC), "tk.h": read(os.path.join(GPL, "tk.h")), "tio.h": read(os.path.join(SD64, "gplsrc", "tio.h")), "ide": read(os.path.join(GPL, "ide")),
         "tk_confirm": read(os.path.join(GPL, "tk_confirm")), "sl.h": read(os.path.join(GPL, "sl.h")), "sd.conf": read(os.path.join(SD64, "sd.conf"))}
    s["pages"] = {n: read(os.path.join(GPL, n)) for n in sorted(os.listdir(GPL)) if n.startswith("tool_")}
    s["code"] = "\n".join(strip_bas(read(os.path.join(GPL, n))) for n in sorted(os.listdir(GPL)) if os.path.isfile(os.path.join(GPL, n)))
    s["checks"] = set(os.listdir(HERE))
    for n in IDE_MENUS:
        s["msg:%d" % n] = read(os.path.join(MSG, str(n)))
    return s


def rows_of(doc):
    """the rule rows of the document: (id, rule, tag, evidence) for every table row whose first cell is an id like F1, K7, D2"""
    out = []
    for line in doc.split("\n"):
        m = re.match(r"^\|\s*([A-Z]\d+)\s*\|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if m.group(1).startswith("E"):
            out.append((m.group(1), " ".join(cells[:-1]), cells[-1], ""))       # an exception row: app | what | why | tag
        elif len(cells) >= 3:
            out.append((m.group(1), cells[0], cells[1], cells[2]))
    return out


def page_table(doc):
    """{program: (verb, audience, rules)} from the section 5 table"""
    out = {}
    for line in doc.split("\n"):
        m = re.match(r"^\|\s*`(tool_\w+)`\s*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$", line)
        if m:
            out[m.group(1)] = (m.group(2).strip(), m.group(3).strip(), m.group(4).strip())
    return out


def exception_apps(doc):
    """{program: id} for the section 7 rows whose app is a tool_* program"""
    out = {}
    for line in doc.split("\n"):
        m = re.match(r"^\|\s*(E\d+)\s*\|\s*`(tool_\w+)`", line)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    doc = s["doc"]
    rr = rows_of(doc)
    ids = [r[0] for r in rr]
    badtag = [r[0] for r in rr if r[2] not in TAGS]
    ck("D0 the document's rule rows parse (more than 20 of them, every id once) and each carries one of BUILT, PLANNED, DROPPED, EXCEPTION, OPEN",
       len(rr) > 20 and len(ids) == len(set(ids)) and not badtag, "rows %d, tags not known: %r, ids twice: %r" % (len(rr), badtag, sorted({i for i in ids if ids.count(i) > 1})))
    planned = [r for r in rr if r[2] == "PLANNED"]
    pbad = []
    for r in planned:
        m = re.search(r"marker:\s*`([^`]+)`", r[3])
        if not m:
            pbad.append("%s names no marker" % r[0])
        elif m.group(1) in s["code"]:
            pbad.append("%s: the marker %s is in the code now - the row must move to BUILT" % (r[0], m.group(1)))
    ck("D1 every PLANNED row names a marker, and no marker occurs in the code of sdsys/gpl.bp (comments left out)", not pbad, "; ".join(pbad))      # 3 Nov 26: none may be left (K7, K8 built)
    ebad = []
    for r in rr:
        if r[2] == "BUILT":
            named = re.findall(r"((?:test|sandbox)-[\w-]+\.(?:py|sh))", r[3])
            if not named:
                ebad.append("%s names no check" % r[0])
            ebad += ["%s: %s does not exist" % (r[0], n) for n in named if n not in s["checks"]]
    ck("D2 every BUILT row names at least one check, and every check it names is in gplbld", not ebad, "; ".join(ebad))
    priv = [p for p in PRIVATE if p in doc]
    ck("D3 the document cites no private path or record (it is in the public tree)", not priv, repr(priv))

    tk = s["tk.h"]
    ck("T1 the floor is 140 by 43: tk.h TK.MINW 140 and TK.MINH 43, the IDE's LAYW = 140 and LAYH = 43, and the document says so",
       re.search(r"\$define TK\.MINW\s+140\b", tk) and re.search(r"\$define TK\.MINH\s+43\b", tk) and re.search(r"^\s*LAYW = 140\b", s["ide"], re.M)
       and re.search(r"^\s*LAYH = 43\b", s["ide"], re.M) and "`TK.MINW 140`, `TK.MINH 43`" in doc and "`LAYH = 43`" in doc, "")
    ck("T8 a session with no size answer gets 140 by 43 (gplsrc/tio.h DEFAULT_WIDTH 140, DEFAULT_DEPTH 43; the owner, 2 Nov 26: 'Change to 43'), as the document's row F2 says",
       re.search(r"#define DEFAULT_WIDTH\s+140\b", s["tio.h"]) and re.search(r"#define DEFAULT_DEPTH\s+43\b", s["tio.h"]) and "`DEFAULT_WIDTH 140`, `DEFAULT_DEPTH 43`" in doc, "")

    pt = page_table(doc)
    pages = s["pages"]
    ck("T2a the page table is exactly the tool_* programs of gpl.bp (a new page adds its row, a removed one takes it out)", set(pt) == set(pages),
       "only in the document: %r; only in gpl.bp: %r" % (sorted(set(pt) - set(pages)), sorted(set(pages) - set(pt))))
    obad = []
    for p, src in pages.items():
        code = strip_bas(src)
        m = re.search(r"call \$tk_open\('[^']*', ('admin'|''|\w+), ctx, err\)", code)
        if not m or "call $tk_frame(" not in code:
            obad.append("%s: no $tk_open or no $tk_frame" % p)
            continue
        aud = pt.get(p, ("", "", ""))[1]
        if (aud == "administrator") != (m.group(1) == "'admin'"):
            obad.append("%s: the table says %s, $tk_open asks %s" % (p, aud, m.group(1)))
    ck("T2 every page opens through $tk_open and draws $tk_frame, and an administrator page (by the table) is the one that asks $tk_open for 'admin'", not obad, "; ".join(obad))

    common = [p for p in pages if p not in ("tool_keys", "tool_tktest")]
    mbad = []
    for p in common:
        code = strip_bas(pages[p])
        for hook in ("draw", "key", "click"):
            n = len(re.findall(r"call \$tk_menubar\('%s'," % hook, code))
            # 11 Nov 26: tool_ai draws the bar a second time in box.resized (S.209: a resize while its own box is open draws the page, the bar and the foot
            #   behind the box); a draw answers nothing.  The same allowance as test-tk-keys-units.py's draws table; every other page and hook is held to one.
            if n != ({"tool_ai": 2}.get(p, 1) if hook == "draw" else 1):
                mbad.append("%s: %d calls of $tk_menubar '%s'" % (p, n, hook))
        if code.find("call $tk_menubar('draw'") > code.find("call $tk_frame("):
            mbad.append("%s: the bar is drawn after the frame" % p)
    own = [p for p in pages if re.search(r"(?i)\bscreen menubar\b", strip_bas(pages[p])) and p != "tool_tktest"]
    fkeys = [p for p in pages if re.search(r"\$tk_keys\('add', \w+, 'f1[01]'", strip_bas(pages[p])) and p != "tool_tktest"]
    ck("T3 every page on the common rules has the toolkit's bar - $tk_menubar draw, key and click once each, the bar drawn before the frame - no page but the test app builds a "
       "SCREEN MENUBAR of its own, and none binds F10 or F11", not mbad and not own and not fkeys, "; ".join(mbad) + " own bar: %r, F10/F11 rows: %r" % (own, fkeys))
    hbad = []
    for p in common:
        code = strip_bas(pages[p])
        if "call $tk_keys('add', keys, 'f1', 'help', 'help', '', 1)" not in code or "call $tk_help('box', " not in code:
            hbad.append("%s: no F1 help row or no $tk_help 'box'" % p)
        quit_act = "signout" if p == "tool_home" else "quit"
        if not re.search(r"call \$tk_keys\('add', keys, 'ctrl-q', '[^']*', '%s', '', 1\)" % quit_act, code):
            hbad.append("%s: Ctrl-Q is not %s" % (p, quit_act))
    ck("T4 every page on the common rules has F1 help (a key row and $tk_help 'box') and Ctrl-Q (quit; the home screen's is sign out, E6)", not hbad, "; ".join(hbad))
    abad = []
    for p in common:
        code = strip_bas(pages[p])
        if p == "tool_home":
            if not ("call $tk_ai('init', ctx, '', '')" in code and "call $tk_keys('add', keys, 'f6', 'ai', 'ai', '', 1)" in code
                    and re.search(r"case nm = 'f6' or nm = 'shift-f6'\n\s*if ctx<TK\.C\.AI> then\n\s*gosub ai\.focus\.on", code)):
                abad.append("tool_home: no F6 row or case to its AI line")
            continue
        # 8 Nov 26 (S.176): F6 is the box key of every page and the AI line one stop of its ring ($tk_aipage 'ring')
        ring = re.search(r"(?:case|if) nm = 'f6' or nm = 'shift-f6' or nm = 'act:ai'(?: then)?\n(?:[^\n]*\n){0,4}?\s*(?:call \$tk_aipage\('ring'|gosub box\.ring)", code)
        if "call $tk_aipage('init'" not in code or not ring:
            abad.append("%s: no $tk_aipage 'init' or no F6 / Shift-F6 case that goes round the ring" % p)
    ck("T5 F6 reaches the AI line on every page on the common rules: $tk_aipage 'init' and one case for F6, Shift-F6 and the menu's act:ai that goes round the ring of boxes and the line (the home screen: its own F6 row and case, $tk_ai, E6)", not abad, "; ".join(abad))
    cbad = [p for p in pages if "call $tk_run(" in strip_bas(pages[p]) and "call $tk_confirm(" not in strip_bas(pages[p])]
    ck("T6 the confirm box's default is Cancel (buttons '&Run,&Cancel' default 2) and every page that runs a command with $tk_run asks $tk_confirm",
       ("buttons '&Run,&Cancel' default 2" in strip_bas(s["tk_confirm"])
        or ("bl = '&Run,&Cancel'" in strip_bas(s["tk_confirm"]) and "nb = dcount(bl, ',')" in strip_bas(s["tk_confirm"])
            and "buttons bl default nb" in strip_bas(s["tk_confirm"])))      # 2 Nov 26 (S.88 P10): the buttons may be given; the default is the LAST (Cancel)
       and not cbad, repr(cbad))
    ck("T7 DROPPED D1: the master-file copies page tool_masters is not in gpl.bp", "tool_masters" not in pages, "")

    ex = exception_apps(doc)
    xbad = []
    if ex != EXEMPT:
        xbad.append("the document's exceptions %r are not this check's %r" % (ex, EXEMPT))
    for p, e in EXEMPT.items():
        if pt.get(p, ("", "", ""))[2] != e:
            xbad.append("%s: the page table's rules are %r, not %s" % (p, pt.get(p, ("", "", ""))[2], e))
    for p in pages:
        if p not in EXEMPT and pt.get(p, ("", "", ""))[2] != "all":
            xbad.append("%s: not exempt, but the table says %r" % (p, pt.get(p, ("", "", ""))[2]))
    kcode = strip_bas(pages.get("tool_keys", ""))
    if "$tk_menubar(" in kcode or "$tk_help(" in kcode:
        xbad.append("tool_keys has a menu bar or F1 now: E1 no longer holds - take the exception out")
    hcode = strip_bas(pages.get("tool_home", ""))
    if "$tk_aipage(" in hcode:
        xbad.append("tool_home calls $tk_aipage now: E6's AI half no longer holds")
    ck("T9 the exceptions are the document's section 7 and the page table's Rules column alike, every other page is 'all', and each exception still holds (an exempt page that gains the rule fails)",
       not xbad, "; ".join(xbad))
    titles = [s["msg:%d" % n].split("|")[0].replace("&", "").strip() for n in IDE_MENUS]
    ck("T10 the IDE's menus (messages 11225-11230, 11654, 14004, 14019) are File Go Search Build View Help, AI, Tools and Edit, as E5 says (Edit is put after File, Tools and AI before Help; S.180, 8 Nov 26)",
       titles == ["File", "Go", "Search", "Build", "View", "Help", "AI", "Tools", "Edit"] and "File, Edit, Go, Search, Build, View, Tools, AI, Help" in doc
       and "if j = 11230 and not(alone) then\n         m = change(sysmsg(14004), '|', @vm)" in s["ide"]
       and "if j = 11226 then\n         m = change(sysmsg(14019), '|', @vm)" in s["ide"], repr(titles))
    codes = re.search(r"\$define SL\.CODES\s+'([^']+)'", s["sl.h"])
    ck("T11 the theme: SL.CODES holds the role letters f U V W X Y, the shipped sd.conf says SCREENTHEME=paper (S.172), and the document says the same (T1, T2)",
       codes and all(c in codes.group(1) for c in "fUVWXY") and re.search(r"^SCREENTHEME=paper\s*$", s["sd.conf"], re.M)
       and "error `f`, warning `U`, success `V`, readonly `W`, busy `X`, focus `Y`" in doc and "(shipped `paper`" in doc, "")
    return rows


M_P7A = 0
MUTANTS = [
    # (what, the text to change, old, new, the check that must go red)
    ("a row with no tag", "doc", "| BUILT | test-tk-keys-units.py |", "| DONE | test-tk-keys-units.py |", "D0"),      # 3 Nov 26: F6's evidence grew, K1's row is the anchor
    # 3 Nov 26: K7 and K8 are BUILT, so no PLANNED row is left to break; a planned row is ADDED whose feature is already in the code ('palette' is, in $tk_menubar), or with no marker
    ("a PLANNED feature is built and the row is not moved", "doc", "| K9 | F11 is bound by no page.",
     "| K10 | A palette of every action. | PLANNED | marker: `'palette'` |\n| K9 | F11 is bound by no page.", "D1"),
    ("a PLANNED row names no marker", "doc", "| K9 | F11 is bound by no page.", "| K10 | A palette of every action. | PLANNED | the palette |\n| K9 | F11 is bound by no page.", "D1"),
    ("K7 goes back to PLANNED while the finder is built", "doc", "with its key, typing narrows the list, Enter chooses. It answers exactly as the bar does (the action's key, replayed through the page's own case); an entry that cannot be used now says why in a box and is never answered. No page binds F2 (a page that did would win in its pane). | BUILT | test-tk-keys-units.py (finder, reserved), sandbox-tool-query.py q14 |",
     "with its key, typing narrows the list, Enter chooses. | PLANNED | marker: `$sl_palette(menus` |", "D1"),
    ("a BUILT row cites a check that does not exist", "doc", "| BUILT | test-tk-keys-units.py |", "| BUILT | test-tk-keyz-units.py |", "D2"),
    ("the document cites a private path", "doc", "Written 2 Nov 2026 (S.88 step p7A)", "Written 2 Nov 2026 (S.88 step p7A, .claude/plan-tui-opus.txt)", "D3"),
    ("the floor becomes 42 rows", "tk.h", "$define TK.MINH        43", "$define TK.MINH        42", "T1"),
    ("the document says the default depth is 42 again", "doc", "`DEFAULT_WIDTH 140`, `DEFAULT_DEPTH 43`", "`DEFAULT_WIDTH 140`, `DEFAULT_DEPTH 42`", "T8"),
    ("a page left out of the table", "doc", "| `tool_voc` | tool.voc | everyone | all |\n", "", "T2a"),
    ("an administrator page opened for everyone", "pages:tool_audit", "call $tk_open('tool.audit', 'admin', ctx, err)", "call $tk_open('tool.audit', '', ctx, err)", "T2"),
    ("a page draws its bar after the frame", "pages:tool_mygates", "      call $tk_menubar('draw', ctx, keys, 'My gates', '', '', mr)",
     "      call $tk_frame(ctx, keys, 'My gates', msg)\n      call $tk_menubar('draw', ctx, keys, 'My gates', '', '', mr)", "T3"),
    ("the home screen builds a SCREEN MENUBAR again", "pages:tool_home", "   ctx<TK.C.BAR> = ''", "   screen menubar menus row 0 draw else null", "T3"),
    ("a page binds F10", "pages:tool_files", "   call $tk_keys('add', keys, 'f1', 'help', 'help', '', 1)\n", "   call $tk_keys('add', keys, 'f1', 'help', 'help', '', 1)\n   call $tk_keys('add', keys, 'f10', 'menu', 'menu', '', 1)\n", "T3"),
    ("a page loses its F1 row", "pages:tool_catalog", "   call $tk_keys('add', keys, 'f1', 'help', 'help', '', 1)\n", "", "T4"),
    ("a page quits on Ctrl-X", "pages:tool_sessions", "call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)", "call $tk_keys('add', keys, 'ctrl-x', 'quit', 'quit', '', 1)", "T4"),
    ("a page's F6 does not open the AI line", "pages:tool_voc", "      case nm = 'f6' or nm = 'shift-f6' or nm = 'act:ai'\n", "      case nm = 'f16'\n", "T5"),
    ("a page's F6 opens the line instead of going round the boxes", "pages:tool_sessions", "call $tk_aipage('ring', ctx, keys, pane, nm : @fm : 2, ap)", "call $tk_aipage('open', ctx, keys, pane, '', ap)", "T5"),
    ("the home screen's F6 opens a line that is not there", "pages:tool_home", "      case nm = 'f6' or nm = 'shift-f6'\n         if ctx<TK.C.AI> then", "      case nm = 'f6' or nm = 'shift-f6'\n         if 1 then", "T5"),
    ("the confirm box defaults to Run", "tk_confirm", "buttons bl default nb", "buttons bl default 1", "T6"),   # 2 Nov 26: the buttons are a variable since S.88 P10
    ("tool_masters comes back", "pages:tool_masters", None, "* TOOL_MASTERS\n   call $tk_open('tool.masters', 'admin', ctx, err)\n", "T7"),
    ("tool.keys gains a menu bar while it is still listed as exempt", "pages:tool_keys", "   call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)\n",
     "   call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)\n   call $tk_menubar('draw', ctx, keys, '', '', '', mr)\n", "T9"),
    ("a page is marked exempt in the table only", "doc", "| `tool_jobs` | tool.jobs | administrator | all |", "| `tool_jobs` | tool.jobs | administrator | E1 |", "T9"),
    ("the IDE loses its Edit menu in the document", "doc", "File, Edit, Go, Search, Build, View, Tools, AI, Help", "File, Go, Search, Build, View, Tools, AI, Help (there is no Edit menu)", "T10"),
    ("the shipped theme is blue again", "sd.conf", "SCREENTHEME=paper", "SCREENTHEME=blue", "T11"),
]


def apply(s, key, old, new):
    t = dict(s)
    if key.startswith("pages:"):
        p = key[6:]
        t["pages"] = dict(s["pages"])
        if old is None:
            if p in t["pages"]:
                return None
            t["pages"][p] = new
        else:
            if t["pages"].get(p, "").count(old) != 1:
                return None
            t["pages"][p] = t["pages"][p].replace(old, new)
        t["code"] = s["code"] + "\n" + strip_bas(t["pages"][p])
        return t
    if s[key].count(old) != 1:
        return None
    t[key] = s[key].replace(old, new)
    return t


def selftest(first):
    s = load()
    base = [n for n, ok, _ in checks(s) if not ok]
    if base:
        print("REFUSING - the unmutated tree already fails: %s" % ", ".join(base))
        return 1
    holes = 0
    for i, (what, key, old, new, want) in enumerate(MUTANTS):
        if i < first:
            continue
        t = apply(s, key, old, new)
        if t is None:
            print("  [CANNOT] #%d %s: the text to change is not found exactly once in %s" % (i, what, key))
            holes += 1
            continue
        red = [n.split()[0] for n, ok, _ in checks(t) if not ok]
        if want in red:
            print("  [killed] #%d %s  <- %s" % (i, what, ", ".join(red)))
        else:
            print("  [MISSED] #%d %s (wanted %s red, got %s)" % (i, what, want, red or "none"))
            holes += 1
    print("selftest: %d mutants from #%d (M_P7A = %d), %d not caught" % (len(MUTANTS) - first, first, M_P7A, holes))
    return 1 if holes else 0


def main():
    for path in (DOC, os.path.join(GPL, "tk.h"), os.path.join(SD64, "gplsrc", "tio.h")):
        if not os.path.exists(path):
            print("test-tuidesign-units: CANNOT RUN - %s is not there" % path)
            return 2
    if "--selftest" in sys.argv:
        first = 0
        for a in sys.argv:
            if a.startswith("--from="):
                first = int(a[len("--from="):])
        return selftest(first)
    rows = checks(load())
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("\n        " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-tuidesign-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
