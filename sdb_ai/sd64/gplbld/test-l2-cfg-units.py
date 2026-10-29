#!/usr/bin/env python3
"""test-l2-cfg-units.py - the layout of five toolkit pages, TOOL.CONFIG, TOOL.REMOTE, TOOL.BACKUPS, TOOL.AI and TOOL.MENUS, on the layout service (S.88 stage L2).  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-l2-cfg-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  ***IT RUNS NO SD, SO IT CANNOT SAY THAT A BOX IS DRAWN WHERE THE RECTANGLE SAYS***: that is `sandbox-l2-cfg.py` (a private SD, a pseudo-terminal, the
screen read back).  What it holds is the geometry the pages DECLARE, worked out by the MODEL of `$tk_layout` that `test-tklayout-units.py` keeps (imported, not copied):

  N  the null case: all five pages, their declarations and the model were found.
  G  the declaration is READ OFF EACH PAGE'S SOURCE (the `d<n> = ...` lines of `lay.declare`, not a copy of them here).  At 140 by 43 it is valid and gives EXACTLY the rectangles of the
     boxes the page drew before it used the service (OLD below, which is also held against the page as it was at commit 10380d19 when git can show it); at 180 by 55, 200 by 60 and
     500 by 300 every pane is inside the body, no two overlap, the columns fill the body's width, the rows left empty at the foot are the rows the page left empty at 140 by 43, and the
     panes that stretch take the growth: config, remote and backups give the extra rows to their list (worked values below), the AI page to its Accounts box, the menu page to its
     Accounts box and What this means; and the width goes to every pane.
  D  the numbers the page counts from its rectangles (`lay.get`: the text width, the rows of a table, the places of the [?] buttons) are read off the source and worked out from the same
     rectangles: at 140 by 43 they are the constants the pages have always used (134, 17 rows, 11 rows, 134 for the [?] ...) and at every size the rows and the borders add up to the pane.
  T  the text: each page declares after $tk_open (and again after a $tk_close and $tk_open), asks for each pane's rectangle, makes the layout again on the key resize before it draws,
     draws every box and tests every mouse position from the rectangles, and keeps no number of the 140 by 43 layout (134, 138, 136, 137, 17) outside the declaration.

--selftest breaks each invariant in the way an edit plausibly would and requires the named check to notice; a mutant that nothing catches is a failure of the self-test.

START-HISTORY:
28 Oct 26 dm  New (S.88 L2, the group of TOOL.CONFIG, TOOL.REMOTE, TOOL.BACKUPS, TOOL.AI and TOOL.MENUS).
END-HISTORY
"""

import importlib.util
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OLD_COMMIT = "10380d19"          # the last commit whose pages drew literal boxes

# TK.P.* in the order of tk.h: the values of one field of a declaration
ATTRS = ["id", "band", "col", "h", "w", "gap", "vkind", "vwt", "hkind", "hwt", "minh", "minw", "prio"]

# The boxes each page drew before the service, by pane id: x, y, w, h (read from the source at OLD_COMMIT, held against git below).  Order is the order of the page's `screen box` lines.
OLD = {
    "tool_config": [("top", (1, 1, 138, 6)), ("list", (1, 7, 138, 20)), ("detail", (1, 27, 138, 13))],
    "tool_remote": [("top", (1, 1, 138, 6)), ("list", (1, 7, 138, 20)), ("detail", (1, 27, 138, 13))],
    "tool_backups": [("top", (1, 1, 138, 6)), ("list", (1, 7, 138, 20)), ("detail", (1, 27, 138, 13))],
    "tool_ai": [("providers", (1, 1, 138, 9)), ("row", (1, 10, 138, 13)), ("accounts", (1, 23, 138, 10)), ("effect", (1, 33, 138, 6))],
    "tool_menus": [("accounts", (1, 1, 70, 30)), ("menu", (72, 1, 67, 21)), ("what", (72, 22, 67, 17)), ("default", (1, 31, 70, 5)), ("help", (1, 36, 70, 3))],
}
# The rows the page leaves empty at the foot of the body at 140 by 43 (the body is 39 rows): they stay empty at every size.
SPARE = {"tool_config": 0, "tool_remote": 0, "tool_backups": 0, "tool_ai": 1, "tool_menus": 1}
# What the pages count from their rectangles at 140 by 43: the constants they used to have.
DERIVED = {
    "tool_config": {"tw": 134, "VP": 17, "DV": 11, "mk.x": 134, "mk.y": 2},
    "tool_remote": {"tw": 134, "VR": 17, "DV": 11, "mk.x": 134, "mk.y": 2},
    "tool_backups": {"tw": 134, "VA": 17, "DV": 11, "mk.x": 134, "mk.y": 2},
    "tool_ai": {"tw": 134, "VISA": 6, "DV": 11, "EV": 4, "mk.px": 134, "mk.py": 2, "mk.ax": 134, "mk.ay": 24},
    "tool_menus": {"aw": 66, "mw": 63, "ww": 63, "dw": 66, "hw": 66, "VIS": 26, "WV": 15, "mk.acx": 66, "mk.acy": 2, "mk.mx": 134, "mk.dx": 66, "mk.dy": 32},
}
# derived name -> (pane id, function of the pane's x, y, w, h): a number of rows (or columns) is the pane's height (width) less a fixed number, a place is a corner of its pane
RT = lambda r: r[0] + r[2] - 5      # the [?] button: five columns in from the right edge
RW = lambda r: r[1] + 1             # ... on the first row inside the border
HH = lambda k: (lambda r: r[3] - k)
WW = lambda k: (lambda r: r[2] - k)
FITS = {
    "tool_config": {"VP": ("list", HH(3)), "DV": ("detail", HH(2)), "tw": ("list", WW(4)), "mk.x": ("top", RT), "mk.y": ("top", RW)},
    "tool_remote": {"VR": ("list", HH(3)), "DV": ("detail", HH(2)), "tw": ("list", WW(4)), "mk.x": ("top", RT), "mk.y": ("top", RW)},
    "tool_backups": {"VA": ("list", HH(3)), "DV": ("detail", HH(2)), "tw": ("list", WW(4)), "mk.x": ("top", RT), "mk.y": ("top", RW)},
    "tool_ai": {"VISA": ("accounts", HH(4)), "DV": ("row", HH(2)), "EV": ("effect", HH(2)), "tw": ("providers", WW(4)), "mk.px": ("providers", RT), "mk.py": ("providers", RW),
                "mk.ax": ("accounts", RT), "mk.ay": ("accounts", RW)},
    "tool_menus": {"VIS": ("accounts", HH(4)), "WV": ("what", HH(2)), "aw": ("accounts", WW(4)), "mw": ("menu", WW(4)), "ww": ("what", WW(4)), "dw": ("default", WW(4)), "hw": ("help", WW(4)),
                   "mk.acx": ("accounts", RT), "mk.acy": ("accounts", RW), "mk.mx": ("menu", RT), "mk.dx": ("default", RT), "mk.dy": ("default", RW)},
}
# What each page must give the extra rows to, and the worked rectangles at 180 by 55 (body 178 by 51 at 1,1).
GROW = {
    "tool_config": {"top": (1, 1, 178, 6), "list": (1, 7, 178, 32), "detail": (1, 39, 178, 13)},
    "tool_remote": {"top": (1, 1, 178, 6), "list": (1, 7, 178, 32), "detail": (1, 39, 178, 13)},
    "tool_backups": {"top": (1, 1, 178, 6), "list": (1, 7, 178, 32), "detail": (1, 39, 178, 13)},
    "tool_ai": {"providers": (1, 1, 178, 9), "row": (1, 10, 178, 13), "accounts": (1, 23, 178, 22), "effect": (1, 45, 178, 6)},
    "tool_menus": {"accounts": (1, 1, 90, 42), "default": (1, 43, 90, 5), "help": (1, 48, 90, 3), "menu": (92, 1, 87, 21), "what": (92, 22, 87, 29)},
}
SIZES = [(140, 43), (141, 44), (150, 45), (180, 55), (200, 60), (233, 71), (500, 300)]
PAGES = ["tool_config", "tool_remote", "tool_backups", "tool_ai", "tool_menus"]

# What the source of each page must contain (comments removed, runs of white space as written): the hit tests and drawing are counted from the rectangles
PINS = {
    "tool_config": ["call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get", "gosub lay.declare", "screen box at top.x,top.y size top.w,top.h", "screen box at lst.x,lst.y size lst.w,lst.h",
                    "screen box at det.x,det.y size det.w,det.h", "call $tk_help('mark', mk.x, mk.y, 0, 0)", "call $tk_help('hit', mev, mk.x, mk.y, hit.m)",
                    "if mx >= tx and mx <= tx + tw - 1 and my >= lst.y + 2 and my <= lst.y + 1 + VP then", "ci = ta + my - (lst.y + 1)", "rtop = dcount(repl, @fm) - (VP - 1)",
                    "if rtop + VP - 1 < dcount(repl, @fm) then rtop += 1", "call $tk_wrap(ptext<i>, tw, pieces)", "room = (tw - 6) - 6 - len(cnt.txt)"],
    "tool_remote": ["call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get", "gosub lay.declare", "screen box at top.x,top.y size top.w,top.h", "screen box at lst.x,lst.y size lst.w,lst.h",
                    "screen box at det.x,det.y size det.w,det.h", "call $tk_help('mark', mk.x, mk.y, 0, 0)", "call $tk_help('hit', mev, mk.x, mk.y, hit.m)",
                    "if mx >= tx and mx <= tx + tw - 1 and my >= lst.y + 2 and my <= lst.y + 1 + VR then", "ci = ta + my - (lst.y + 1)", "call $tk_wrap(lines<i>, tw, pieces)", "if n <= DV then"],
    "tool_backups": ["call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get", "gosub lay.declare", "screen box at top.x,top.y size top.w,top.h", "screen box at lst.x,lst.y size lst.w,lst.h",
                     "screen box at det.x,det.y size det.w,det.h", "call $tk_help('mark', mk.x, mk.y, 0, 0)", "call $tk_help('hit', mev, mk.x, mk.y, hit.m)",
                     "if mx >= tx and mx <= tx + tw - 1 and my >= lst.y + 2 and my <= lst.y + 1 + VA then", "ci = ta + my - (lst.y + 1)", "if dcount(lines, @fm) > DV then", "na - (DV - 3)"],
    "tool_ai": ["call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get", "screen box at pr.x,pr.y size pr.w,pr.h", "screen box at dt.x,dt.y size dt.w,dt.h", "screen box at ac.x,ac.y size ac.w,ac.h",
                "screen box at ef.x,ef.y size ef.w,ef.h", "call $tk_help('mark', mk.px, mk.py, 0, 0)", "call $tk_help('mark', mk.ax, mk.ay, 0, 0)", "call $tk_help('hit', mev, mk.px, mk.py, hit.prov)",
                "call $tk_help('hit', mev, mk.ax, mk.ay, hit.acc)", "case mx >= pr.x + 1 and mx <= pr.x + pr.w - 2 and my >= pr.y + 2 and my <= pr.y + 5", "pi = my - (pr.y + 1)",
                "case mx >= ac.x + 1 and mx <= ac.x + ac.w - 2 and my >= ac.y + 2 and my <= ac.y + 1 + VISA", "if ta + my - (ac.y + 1) <= an then ci = ta + my - (ac.y + 1)",
                "call $tk_wrap(lines<wi>, tw, pieces)", "for r = 1 to DV", "for r = 1 to EV", "at tx,pr.y + pr.h - 2 attr 'bold' width tw", "at tx,ac.y + ac.h - 2 attr 'bold' width tw", "mk.py = pr.y + 1", "mk.ay = ac.y + 1"],
    "tool_menus": ["call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get", "screen box at acl.x,acl.y size acl.w,acl.h", "screen box at mnu.x,mnu.y size mnu.w,mnu.h", "screen box at wat.x,wat.y size wat.w,wat.h",
                   "screen box at dfl.x,dfl.y size dfl.w,dfl.h", "screen box at hlp.x,hlp.y size hlp.w,hlp.h", "call $tk_help('mark', mk.acx, mk.acy, 0, 0)", "call $tk_help('mark', mk.mx, mnu.y + r, 0, 0)",
                   "call $tk_help('mark', mk.dx, mk.dy, 0, 0)", "call $tk_help('hit', mev, mk.mx, mnu.y + hr, hit.now)", "call $tk_help('hit', mev, mk.dx, mk.dy, hit.default)", "call $tk_help('hit', mev, mk.acx, mk.acy, hit.accounts)",
                   "case mx >= acl.x + 1 and mx <= acl.x + acl.w - 2 and my >= acl.y + 2 and my <= acl.y + 1 + VIS", "k = top + my - (acl.y + 1)",
                   "case mx >= mnu.x + 1 and mx <= mnu.x + mnu.w - 1 and my >= mnu.y + 1 and my <= mnu.y + nmenu", "si = my - mnu.y",
                   "case mx >= dfl.x + 1 and mx <= dfl.x + dfl.w - 2 and my >= dfl.y + 1 and my <= dfl.y + 3", "call $tk_wrap(lines<wi>, ww, pieces)", "for r = 1 to WV",
                   "tfw = aw - 48", "if len(tf) > tfw then tf = tf[1, tfw - 1] : '+'"],
}
# The pages that give the terminal away and take the screen again: the new context holds no panes
REOPEN = {"tool_remote", "tool_ai"}


def load_model():
    path = os.path.join(HERE, "test-tklayout-units.py")
    spec = importlib.util.spec_from_file_location("tklayout_units", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_pages():
    raw = {}
    for n in PAGES:
        try:
            with open(os.path.join(GPL, n), encoding="latin-1") as f:
                raw[n] = f.read()
        except OSError:
            raw[n] = ""
    return raw


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append((line if cut < 0 else line[:cut]).rstrip())
    return "\n".join(out)


def block(text, label):
    m = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][a-z.0-9]*:\s*$|^end\s*$", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def parse_decl(code):
    """the page's declaration: a list of attribute dicts, from the `d<n> = ...` lines of lay.declare"""
    out = []
    for m in re.finditer(r"^\s*d<(\d+)>\s*=\s*(.*)$", block(code, "lay.declare"), re.M):
        vals = []
        for tok in m.group(2).split(" : @vm : "):
            tok = tok.strip()
            if len(tok) >= 2 and tok[0] == "'" and tok[-1] == "'":
                vals.append(tok[1:-1])
            elif tok == "":
                vals.append("")
            else:
                vals.append(int(tok) if re.fullmatch(r"\d+", tok) else tok)
        vals += [""] * (len(ATTRS) - len(vals))
        a = {k: (v if v != "" else None) for k, v in zip(ATTRS, vals)}
        out.append(a)
    return out


def pane_vars(code):
    """prefix -> pane id, from the pairs `lay.id = 'ID'` ... `PRE.x = lay.x` of lay.get"""
    lg = block(code, "lay.get")
    pairs = {}
    cur = None
    for line in lg.split("\n"):
        m = re.match(r"\s*lay\.id = '([a-z]+)'", line)
        if m:
            cur = m.group(1)
        m = re.match(r"\s*([a-z]+)\.x = lay\.x ;", line)
        if m and cur:
            pairs[m.group(1)] = cur
    return pairs


def derived_values(code, rects):
    """the numbers lay.get works out from the rectangles (rects: id -> (x, y, w, h)), evaluated from the page's own lines"""
    env = {}
    for pre, pid in pane_vars(code).items():
        r = rects.get(pid)
        if r:
            env.update({pre + ".x": r[0], pre + ".y": r[1], pre + ".w": r[2], pre + ".h": r[3]})
    got = {}
    for line in block(code, "lay.get").split("\n"):
        m = re.match(r"\s+([A-Za-z][A-Za-z.]*) = ([A-Za-z0-9.+\-*() ]+?)\s*$", line)
        if not m or m.group(1).startswith("lay.") or "ctx<" in line:
            continue
        name, expr = m.group(1), m.group(2)
        if re.search(r"\.(x|y|w|h) = ", line) and ";" in line:
            continue
        py = re.sub(r"[A-Za-z][A-Za-z.]*", lambda t: str(env[t.group(0)]) if t.group(0) in env else t.group(0), expr)
        if not re.fullmatch(r"[0-9+\-*() ]+", py):
            continue
        env[name] = eval(py)
        got[name] = env[name]
    return got


def overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def old_boxes_from_git(page):
    """the page's literal boxes at OLD_COMMIT, or None when git cannot show them"""
    try:
        out = subprocess.run(["git", "-C", REPO, "show", "%s:sdb_ai/sd64/sdsys/gpl.bp/%s" % (OLD_COMMIT, page)], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    src = out.stdout.decode("latin-1")
    return [tuple(int(v) for v in m.groups()) for m in re.finditer(r"screen box at (\d+),(\d+) size (\d+),(\d+)", strip_bas(src))]


def checks(raw, M, git_boxes=None):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    code = {n: strip_bas(raw[n]) for n in PAGES}
    decl = {n: parse_decl(code[n]) for n in PAGES}
    ck("N0", "NULL CASE: all five pages were read, each has a lay.declare of at least three panes and a lay.get, and the model (test-tklayout-units.py) is the one with a layout()",
       all(len(raw[n]) > 5000 and len(decl[n]) >= 3 and block(code[n], "lay.get") for n in PAGES) and hasattr(M, "Model") and hasattr(M.Model, "layout"),
       " ".join("%s:%d" % (n, len(decl[n])) for n in PAGES))

    if not rows[-1][2]:
        return rows                                     # nothing to measure: the null case already failed
    fr0 = M.Model().frame(140, 43)
    model = M.Model()
    bad = []
    for n in PAGES:
        v = model.validate(decl[n])
        rects, mode = model.layout(decl[n], fr0)
        got = [(d["id"], r[:4]) for d, r in zip(decl[n], rects)]
        want = OLD[n]
        if v is not None or mode != "full" or not all(r[4] for r in rects) or sorted(got) != sorted(want):
            bad.append("%s: valid %r mode %s got %r want %r" % (n, v, mode, got, want))
    ck("G1", "AT 140 BY 43 EACH PAGE'S DECLARATION (read off its lay.declare) IS VALID AND GIVES EXACTLY THE BOXES THE PAGE DREW BEFORE THE SERVICE: %s" % ", ".join("%s %d" % (n, len(OLD[n])) for n in PAGES), not bad, "; ".join(bad)[:700])

    if git_boxes is None:
        ck("G1b", "SKIPPED (git cannot show %s): the table of old boxes is held against the page as it was" % OLD_COMMIT, True, "")
    else:
        bad = []
        for n in PAGES:
            gb = git_boxes.get(n)
            if gb != [b for _, b in OLD[n]]:
                bad.append("%s: git %r table %r" % (n, gb, [b for _, b in OLD[n]]))
        ck("G1b", "the table of old boxes is the pages' own literal `screen box` lines at commit %s, in the order drawn" % OLD_COMMIT, not bad, "; ".join(bad)[:500])

    bad = []
    for n in PAGES:
        rects0, _ = model.layout(decl[n], fr0)
        for (ww, hh) in SIZES[1:]:
            fr = model.frame(ww, hh)
            rects, mode = model.layout(decl[n], fr)
            if mode != "full" or not all(r[4] for r in rects):
                bad.append("%s %dx%d mode %s" % (n, ww, hh, mode))
                continue
            for a, b0 in zip(rects, rects0):
                if a[2] < b0[2] or a[3] < b0[3]:
                    bad.append("%s %dx%d %r smaller than at 140x43 %r" % (n, ww, hh, a, b0))
                if a[0] < fr["XBODY"] or a[1] < fr["YBODY"] or a[0] + a[2] > fr["XBODY"] + fr["BODYW"] or a[1] + a[3] > fr["YBODY"] + fr["BODYH"]:
                    bad.append("%s %dx%d %r outside the body" % (n, ww, hh, a))
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    if overlaps(rects[i], rects[j]):
                        bad.append("%s %dx%d %r overlaps %r" % (n, ww, hh, rects[i], rects[j]))
            right = max(r[0] + r[2] for r in rects)
            foot = max(r[1] + r[3] for r in rects)
            if right != fr["XBODY"] + fr["BODYW"]:
                bad.append("%s %dx%d the panes end at column %d, the body at %d" % (n, ww, hh, right - 1, fr["XBODY"] + fr["BODYW"] - 1))
            if foot != fr["YBODY"] + fr["BODYH"] - SPARE[n]:
                bad.append("%s %dx%d the panes end at row %d, the body less the %d spare row(s) at %d" % (n, ww, hh, foot - 1, SPARE[n], fr["YBODY"] + fr["BODYH"] - SPARE[n] - 1))
    ck("G2", "LARGER (%s): every pane at least its 140-by-43 size, inside the body, no two overlapping, the panes fill the body's width and end where the page ended (the foot row(s) it left empty at 140 by 43 stay empty)"
       % ", ".join("%dx%d" % s for s in SIZES[1:]), not bad, "; ".join(bad)[:700])

    bad = []
    fr = model.frame(180, 55)
    for n in PAGES:
        rects, _ = model.layout(decl[n], fr)
        got = {d["id"]: r[:4] for d, r in zip(decl[n], rects)}
        if got != GROW[n]:
            bad.append("%s: got %r want %r" % (n, got, GROW[n]))
    ck("G3", "WORKED VALUES at 180 by 55 (body 178 by 51): the list takes the 12 extra rows on config, remote and backups (1,7 178x32); the Accounts box takes them on the AI page (1,23 178x22); "
             "on the menu page Accounts (1,1 90x42) and What this means (92,22 87x29) take them and the two columns share the 40 extra columns", not bad, "; ".join(bad)[:800])

    bad = []
    for n in PAGES:
        for (ww, hh) in SIZES:
            fr = model.frame(ww, hh)
            rects, _ = model.layout(decl[n], fr)
            rr = {d["id"]: r[:4] for d, r in zip(decl[n], rects)}
            dv = derived_values(code[n], rr)
            if (ww, hh) == (140, 43):
                want = DERIVED[n]
                if {k: dv.get(k) for k in want} != want:
                    bad.append("%s 140x43: got %r want %r" % (n, {k: dv.get(k) for k in want}, want))
            for name, (pid, fn) in FITS[n].items():
                if dv.get(name) != fn(rr[pid]):
                    bad.append("%s %dx%d %s = %r, its pane %s gives %d" % (n, ww, hh, name, dv.get(name), pid, fn(rr[pid])))
    ck("D", "THE NUMBERS A PAGE COUNTS FROM ITS RECTANGLES (read off lay.get and worked out): at 140 by 43 the constants it always had (a text line 134 wide, 17 list rows, 11 detail rows, the [?] at 134,2 ...), "
            "and at every size (%d) each count is its pane's height or width less the borders and margin, and each [?] is five columns in from its pane's right edge on its first row" % len(SIZES), not bad, "; ".join(bad)[:800])

    bad = []
    for n in PAGES:
        c = code[n]
        for pin in PINS[n]:
            if pin not in c:
                bad.append("%s: %r" % (n, pin[:70]))
        if "call $tk_layout('declare', ctx, d, lay.err)" not in block(c, "lay.declare"):
            bad.append("%s: lay.declare does not declare" % n)
        opens = c.count("call $tk_open(")
        calls = c.count("gosub lay.declare")
        if calls != opens:
            bad.append("%s: %d $tk_open(s) but %d 'gosub lay.declare'" % (n, opens, calls))
        if n in REOPEN and opens != 2:
            bad.append("%s: expected a reopen" % n)
        first_open = c.find("call $tk_open(")
        first_decl = c.find("gosub lay.declare")
        first_read = c.find("gosub read.all")
        if not (0 <= first_open < first_decl < first_read):
            bad.append("%s: the first declaration is not between $tk_open and the first read" % n)
        if "lay.err" in c.replace("call $tk_layout('declare', ctx, d, lay.err)", ""):
            bad.append("%s: lay.err is used elsewhere" % n)
        lit = re.search(r"\b(134|138|136|137|17)\b", re.sub(r"(?m)^   d<\d> = .*$", "", c))
        if lit:
            bad.append("%s: the literal %s outside the declaration" % (n, lit.group(1)))
        if re.search(r"screen box at \d", c):
            bad.append("%s: a screen box at a literal place" % n)
        rz = c.find("case nm = 'resize'")
        if rz < 0 or not (rz < c.find("call $tk_layout('refresh'") < c.find("gosub lay.get", rz) < c.find("ctx<TK.C.GEN> = gen", rz) < c.find("gosub draw.all", rz)):
            bad.append("%s: the resize does not refresh, take the rectangles, raise the generation and draw, in that order" % n)
    ck("T", "THE TEXT: each page declares after every $tk_open (before it reads), declares only a valid declaration through lay.err it never reads, draws and tests the mouse from the rectangles (%d pins), "
            "keeps no number of the 140-by-43 layout outside its declaration, and on the key resize refreshes, takes the rectangles, raises the generation and draws, in that order; %s take the screen again"
       % (sum(len(v) for v in PINS.values()), " and ".join(sorted(REOPEN))), not bad, "; ".join(bad)[:900])
    return rows


def sub(page, old, new):
    def mut(raw):
        if old not in raw[page]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (page, old[:80]))
        out = dict(raw)
        out[page] = raw[page].replace(old, new, 1)
        return out
    return mut


MUTANTS = [
    ("config: the list is a row taller", "G1", sub("tool_config", "d<2> = 'list' : @vm : 2 : @vm : 1 : @vm : 20 :", "d<2> = 'list' : @vm : 2 : @vm : 1 : @vm : 21 :")),
    ("config: the detail is a row shorter", "G1", sub("tool_config", "@vm : 3 : @vm : 1 : @vm : 13 : @vm : 138", "@vm : 3 : @vm : 1 : @vm : 12 : @vm : 138")),
    ("config: the list no longer stretches", "G3", sub("tool_config", "@vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch' : @vm : 1\n   d<3>", "@vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch' : @vm : 1\n   d<3>")),
    ("config: the detail stretches too, taking half of the extra rows", "G3", sub("tool_config", "@vm : 13 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'", "@vm : 13 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'")),
    ("config: the rows of the list are a constant again", "D", sub("tool_config", "VP = lst.h - 3", "VP = 17")),
    ("config: the [?] is at a literal column", "D", sub("tool_config", "mk.x = top.x + top.w - 5", "mk.x = 134")),
    ("config: the text is a literal width", "D", sub("tool_config", "tw = lst.w - 4", "tw = 134")),
    ("config: the resize no longer asks the layout", "T", sub("tool_config", "            call $tk_layout('refresh', ctx, '', lay.chg)\n", "")),
    ("config: a box at a literal place", "T", sub("tool_config", "screen box at lst.x,lst.y size lst.w,lst.h title ttl", "screen box at 1,7 size 138,20 title ttl")),
    ("config: the page is never declared", "T", sub("tool_config", "   gosub lay.declare                                            ;* the panes;", "   null                                                         ;* the panes;")),
    ("remote: the list no longer stretches", "G3", sub("tool_remote", "@vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch' : @vm : 1\n   d<3>", "@vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch' : @vm : 1\n   d<3>")),
    ("remote: the top box is on the wrong band", "G1", sub("tool_remote", "d<1> = 'top' : @vm : 1 :", "d<1> = 'top' : @vm : 3 :")),
    ("remote: the panes are not declared again after the terminal came back", "T", sub("tool_remote", "   gosub lay.declare                                           ;* the new context holds no panes", "   null                                                        ;* the new context holds no panes")),
    ("remote: a click is tested at a literal column", "T", sub("tool_remote", "if mx >= tx and mx <= tx + tw - 1 and my >= lst.y + 2", "if mx >= 3 and mx <= tx + tw - 1 and my >= lst.y + 2")),
    ("remote: the explanation wraps at a literal width", "T", sub("tool_remote", "call $tk_wrap(lines<i>, tw, pieces)", "call $tk_wrap(lines<i>, 134, pieces)")),
    ("backups: the detail is a column too wide", "G1", sub("tool_backups", "@vm : 3 : @vm : 1 : @vm : 13 : @vm : 138", "@vm : 3 : @vm : 1 : @vm : 13 : @vm : 139")),
    ("backups: the 'more accounts' line counts from a literal again", "T", sub("tool_backups", "na - (DV - 3)", "na - 8")),
    ("backups: the rows of the list are the pane's height less four", "D", sub("tool_backups", "VA = lst.h - 3", "VA = lst.h - 4")),
    ("ai: the Accounts box no longer stretches", "G3", sub("tool_ai", "@vm : 10 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'", "@vm : 10 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'")),
    ("ai: the detail takes the extra rows instead", "G3", sub("tool_ai", "@vm : 13 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'", "@vm : 13 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'")),
    ("ai: the Accounts box is below the explanation", "G1", sub("tool_ai", "d<3> = 'accounts' : @vm : 3 :", "d<3> = 'accounts' : @vm : 5 :")),
    ("ai: the account rows are the pane's height less three", "D", sub("tool_ai", "VISA = ac.h - 4", "VISA = ac.h - 3")),
    ("ai: the account [?] is at a literal row (the same row at every size, since nothing above it grows: the text pins it)", "T", sub("tool_ai", "mk.ay = ac.y + 1", "mk.ay = 24")),
    ("ai: the panes are not declared again after the key prompt", "T", sub("tool_ai", "   gosub lay.declare                                           ;* the new context holds no panes", "   null                                                        ;* the new context holds no panes")),
    ("ai: a click on an account row is tested at a literal row", "T", sub("tool_ai", "my >= ac.y + 2 and my <= ac.y + 1 + VISA", "my >= 25 and my <= ac.y + 1 + VISA")),
    ("menus: the right column is not a column away", "G1", sub("tool_menus", "d<4> = 'menu' : @vm : 1 : @vm : 2 : @vm : 21 : @vm : 67 : @vm : 1 :", "d<4> = 'menu' : @vm : 1 : @vm : 2 : @vm : 21 : @vm : 67 : @vm : 0 :")),
    ("menus: What this means no longer stretches", "G3", sub("tool_menus", "@vm : 17 : @vm : 67 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'", "@vm : 17 : @vm : 67 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'")),
    ("menus: the Menu box takes the extra rows as well", "G3", sub("tool_menus", "@vm : 21 : @vm : 67 : @vm : 1 : @vm : '' : @vm : '' : @vm : 'stretch'", "@vm : 21 : @vm : 67 : @vm : 1 : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'")),
    ("menus: the Help box is a row taller", "G1", sub("tool_menus", "d<3> = 'help' : @vm : 1 : @vm : 1 : @vm : 3 :", "d<3> = 'help' : @vm : 1 : @vm : 1 : @vm : 4 :")),
    ("menus: the account rows are a constant again", "D", sub("tool_menus", "VIS = acl.h - 4", "VIS = 26")),
    ("menus: the Tiles off cut is a literal again", "T", sub("tool_menus", "if len(tf) > tfw then tf = tf[1, tfw - 1] : '+'", "if len(tf) > 18 then tf = tf[1, 17] : '+'")),
    ("menus: a click in the Menu box is tested at a literal column", "T", sub("tool_menus", "case mx >= mnu.x + 1 and mx <= mnu.x + mnu.w - 1", "case mx >= 73 and mx <= mnu.x + mnu.w - 1")),
    ("menus: the explanation wraps at a literal width", "T", sub("tool_menus", "call $tk_wrap(lines<wi>, ww, pieces)", "call $tk_wrap(lines<wi>, 63, pieces)")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:300]))
        bad += 0 if ok else 1
    return bad


def selftest(raw, M, git_boxes):
    base = [r[0] for r in checks(raw, M, git_boxes) if not r[2]]
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
        failed = sorted({r[0] for r in checks(m, M, git_boxes) if not r[2]})
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        holes += 0 if hit else 1
    # controls: a page that is not there, and a declaration with no pane, must fail the null case (the check does not pass because it did nothing)
    ctl = dict(raw)
    ctl["tool_ai"] = ""
    c1 = "N0" in {r[0] for r in checks(ctl, M, git_boxes) if not r[2]}
    ctl = dict(raw)
    ctl["tool_menus"] = re.sub(r"(?m)^   d<\d> = .*$", "", raw["tool_menus"])
    c2 = "N0" in {r[0] for r in checks(ctl, M, git_boxes) if not r[2]}
    for nm, ok in (("control: a missing page fails N0", c1), ("control: a page with no declaration fails N0", c2)):
        print("  [%s] selftest: %s" % ("PASS" if ok else "FAIL", nm))
        holes += 0 if ok else 1
    print("selftest: %d mutants and 2 controls, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main(argv):
    raw = read_pages()
    print("test-l2-cfg-units: tree %s" % SDSYS)
    if not all(raw.values()):
        print("test-l2-cfg-units: CANNOT RUN - a page is not there: %s" % ", ".join(n for n in PAGES if not raw[n]))
        return 2
    M = load_model()
    git_boxes = {}
    for n in PAGES:
        b = old_boxes_from_git(n)
        if b is None:
            git_boxes = None
            break
        git_boxes[n] = b
    if git_boxes is None:
        print("test-l2-cfg-units: git cannot show commit %s here: the table of old boxes is not held against it (row G1b says so)" % OLD_COMMIT)
    rows = checks(raw, M, git_boxes)
    bad = report(rows)
    print("\ntest-l2-cfg-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw, M, git_boxes) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
