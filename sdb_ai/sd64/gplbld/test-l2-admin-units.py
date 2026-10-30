#!/usr/bin/env python3
"""test-l2-admin-units.py - the five dense administrator pages on the layout service (S.88 stage L2): TOOL.GATES, TOOL.SESSIONS, TOOL.MASTERS, TOOL.AUDIT, TOOL.ACCOUNTS.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-l2-admin-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads each page's BASIC as text, with comments removed, takes the pane DECLARATION out of the page's own `declare.layout`, lays it out with the geometry
model of test-tklayout-units.py (a copy of $tk_layout's equations; that file is shared and not edited here) and holds the result against what the page drew before L2.  ***IT RUNS
NOTHING, SO IT CANNOT SAY THAT A PAGE IS DRAWN IN A BIGGER WINDOW***: that is `sandbox-l2-admin.py`, which opens each page on a pseudo-terminal at 140 by 43, 180 by 55 and 200 by 60 and reads
the boxes off the screen against this file's expected rectangles.  What a text check is for:

  L2-0  NULL CASE: the model loaded, the five pages and their declarations were found.
  L2-1  every declaration is accepted by the model's version of $tk_layout 'declare' (ids, bands, sizes, the reference body).
  L2-2  AT 140 BY 43 THE DECLARATION GIVES EXACTLY THE BOXES THE PAGE DREW BEFORE L2 (REF below, the literal `screen box at x,y size w,h` of each page at the commit before L2), every pane shown,
        mode full; and the declared sizes are those boxes.  L2-2b: while the committed page still holds the literal boxes, REF equals them.
  L2-3  the names the page derives from its rectangles (get.rects: the row counts, the text widths, the first cell's column) and the row and column of every text it draws or tests with the mouse
        are, at 140 by 43, the numbers the page used as literals; the expressions are looked for in the page's own code and evaluated here.
  L2-4  at 150 by 45, 180 by 55, 200 by 60, 233 by 71 and 500 by 300 every pane is shown, at least its 140-by-43 size, inside the body, no two overlap, the panes of a band fill the body's width and
        the bands its height (the cells not covered are the declared gaps), every row and column a text uses stays inside its box, and every row count and text width follows the box it is tied to (a list shows more rows when its box is taller).
  L2-4b worked values at 180 by 55: the rows and columns the window gives are shared by the weights the declarations say (a pin on the stretch weights).
  L2-5  the panes the page asks $tk_layout for are the panes it declared, and every one is drawn as a box.
  L2-6  the page opens the layout once after $tk_open and before its first read; a refused declaration closes the base; the resize key makes the layout again (refresh, rectangles, scroll kept in view,
        generation, redraw, in that order); TOOL.ACCOUNTS declares again after the terminal was handed to a verb (the new $tk_open has no panes).
  L2-7  no number that is really the window's is left in the drawing and mouse code: no 128, 134, 136, 138 or 139, no `at 3,`, no `for r = 1 to <number>`.
  L2-8  the floor each page declares stays 140 by 43: $tk_open is called with its four arguments.

--selftest breaks each invariant in the way an edit plausibly would and requires the named check to notice; a mutant that nothing catches is a failure of the self-test.

START-HISTORY:
28 Oct 26 dm  New (S.88 L2, the administrator pages).
END-HISTORY
"""

import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPL = os.path.normpath(os.path.join(HERE, "..", "sdsys", "gpl.bp"))
PAGE_NAMES = ["tool_gates", "tool_sessions", "tool_masters", "tool_audit", "tool_accounts"]
SIZES = [(150, 45), (180, 55), (200, 60), (233, 71), (500, 300)]

# The boxes each page drew at 140 by 43 before L2 (x, y, w, h), in the order the page declares its panes, with the title the box carries.
REF = {
    "tool_gates": [("matrix", "Gates by account", (1, 1, 138, 19)), ("cell", "The cell under the cursor", (1, 20, 138, 11)),
                   ("reach", "Who can reach the operating system", (1, 31, 68, 9)), ("sessions", "Sessions of the account under the cursor", (70, 31, 69, 9))],
    "tool_sessions": [("sessions", "Sessions", (1, 1, 138, 15)), ("locks", "Locks", (1, 16, 138, 14)), ("row", "The row under the cursor", (1, 30, 138, 10))],
    "tool_masters": [("master", "Master files", (1, 1, 138, 8)), ("accounts", "Accounts", (1, 9, 138, 15)), ("detail", "The account under the cursor", (1, 24, 138, 16))],
    "tool_audit": [("trail", "Audit trail", (1, 1, 138, 6)), ("lines", "Lines", (1, 7, 138, 20)), ("detail", "The line under the cursor", (1, 27, 138, 13))],
    "tool_accounts": [("counts", "Accounts", (1, 1, 138, 6)), ("list", "Every account", (1, 7, 138, 20)), ("detail", "The account under the cursor", (1, 27, 138, 13))],
}
# The prefix the page gives each pane's rectangle (prefix.x .y .w .h)
PREFIX = {
    "tool_gates": {"matrix": "mat", "cell": "cel", "reach": "rea", "sessions": "ses"},
    "tool_sessions": {"sessions": "ssn", "locks": "lck", "row": "rwb"},
    "tool_masters": {"master": "top", "accounts": "acc", "detail": "det"},
    "tool_audit": {"trail": "top", "lines": "lst", "detail": "det"},
    "tool_accounts": {"counts": "top", "list": "lst", "detail": "det"},
}
# What the page derives from its rectangles, at 140 by 43, as the literal it used before: (name, value)
CONSTS = {
    "tool_gates": [("VIS", 14), ("CL", 9), ("RW", 7), ("X0", 29), ("mtw", 134), ("ctw", 134), ("rtw", 64), ("stw", 65)],
    "tool_sessions": [("VS", 11), ("VL", 10), ("VR", 7), ("stw", 134), ("ltw", 134), ("rtw", 134)],
    "tool_masters": [("VA", 11), ("VD", 5), ("VW", 7), ("ttw", 134), ("atw", 134), ("dtw", 134)],
    "tool_audit": [("VL", 17), ("DR", 11), ("ttw", 134), ("ltw", 134), ("dtw", 134)],
    "tool_accounts": [("VA", 17), ("DR", 11), ("ttw", 134), ("ltw", 134), ("dtw", 134)],
}
# The rows and columns the page draws at and tests the mouse against: (expression as the page writes it, pane prefix, axis, the name of the largest r, the literal it was at 140 by 43 with r = 1).
# An axis of n is a number that is not a place (a count or a width).  The place of a row that uses r is held inside the box for r = 1 and for r = the largest.
EXPRS = {
    "tool_gates": [("mat.x + 2", "mat", "x", None, 3), ("mat.y + 1", "mat", "y", None, 2), ("mat.y + 1 + r", "mat", "y", "VIS", 3), ("mat.y + mat.h - 3", "mat", "y", None, 17),
                   ("mat.y + mat.h - 2", "mat", "y", None, 18), ("mat.y + 3", "mat", "y", None, 4), ("mat.x + mat.w - 5", "mat", "x", None, 134), ("mat.y + 2", "mat", "y", None, 3),
                   ("mat.y + 1 + VIS", "mat", "y", None, 16), ("mat.x + mat.w - 3", "mat", "x", None, 136), ("cel.x + 2", "cel", "x", None, 3), ("cel.y + r", "cel", "y", "CL", 21),
                   ("rea.x + 2", "rea", "x", None, 3), ("rea.y + r", "rea", "y", "RW", 32), ("rea.y + RW", "rea", "y", None, 38), ("rea.y + 1", "rea", "y", None, 32),
                   ("ses.x + 2", "ses", "x", None, 72), ("ses.y + r", "ses", "y", "RW", 32), ("ses.y + 1", "ses", "y", None, 32)],
    "tool_sessions": [("ssn.x + 2", "ssn", "x", None, 3), ("ssn.y + 1", "ssn", "y", None, 2), ("ssn.y + 1 + r", "ssn", "y", "VS", 3), ("ssn.y + ssn.h - 2", "ssn", "y", None, 14),
                      ("ssn.x + ssn.w - 5", "ssn", "x", None, 134), ("ssn.y + 2", "ssn", "y", None, 3), ("ssn.y + 1 + VS", "ssn", "y", None, 13), ("ssn.x + ssn.w - 3", "ssn", "x", None, 136),
                      ("lck.x + 2", "lck", "x", None, 3), ("lck.y + 1", "lck", "y", None, 17), ("lck.y + 1 + r", "lck", "y", "VL", 18), ("lck.y + 2", "lck", "y", None, 18),
                      ("lck.y + lck.h - 2", "lck", "y", None, 28), ("lck.y + 1 + VL", "lck", "y", None, 27), ("rwb.x + 2", "rwb", "x", None, 3), ("rwb.y + r", "rwb", "y", "VR", 31),
                      ("rwb.y + rwb.h - 2", "rwb", "y", None, 38)],
    "tool_masters": [("top.x + 2", "top", "x", None, 3), ("top.y + 1", "top", "y", None, 2), ("top.y + 2", "top", "y", None, 3), ("top.y + 3", "top", "y", None, 4), ("top.y + 4", "top", "y", None, 5),
                     ("top.y + 5", "top", "y", None, 6), ("top.y + 6", "top", "y", None, 7), ("top.x + top.w - 5", "top", "x", None, 134), ("acc.x + 2", "acc", "x", None, 3),
                     ("acc.y + 1", "acc", "y", None, 10), ("acc.y + 1 + r", "acc", "y", "VA", 11), ("acc.y + acc.h - 2", "acc", "y", None, 22), ("acc.y + 2", "acc", "y", None, 11),
                     ("acc.y + 1 + VA", "acc", "y", None, 21), ("acc.x + acc.w - 3", "acc", "x", None, 136), ("det.x + 2", "det", "x", None, 3), ("det.y + r", "det", "y", "VD", 25),
                     ("det.y + VD + 1 + r", "det", "y", "VW", 31), ("det.y + det.h - 2", "det", "y", None, 38), ("det.h - 3", "det", "n", None, 13)],
    "tool_audit": [("top.x + 2", "top", "x", None, 3), ("top.y + 1", "top", "y", None, 2), ("top.y + 2", "top", "y", None, 3), ("top.y + 3", "top", "y", None, 4), ("top.y + 4", "top", "y", None, 5),
                   ("top.x + top.w - 5", "top", "x", None, 134), ("ttw - 6", "top", "n", None, 128), ("lst.x + 2", "lst", "x", None, 3), ("lst.y + 1", "lst", "y", None, 8),
                   ("lst.y + 1 + r", "lst", "y", "VL", 9), ("lst.y + 2", "lst", "y", None, 9), ("lst.y + 1 + VL", "lst", "y", None, 25), ("lst.x + lst.w - 3", "lst", "x", None, 136),
                   ("det.x + 2", "det", "x", None, 3), ("det.y + r", "det", "y", "DR", 28), ("det.y + 1", "det", "y", None, 28), ("dtw - 4", "det", "n", None, 130)],
    "tool_accounts": [("top.x + 2", "top", "x", None, 3), ("top.y + 1", "top", "y", None, 2), ("top.y + 2", "top", "y", None, 3), ("top.y + 3", "top", "y", None, 4), ("top.y + 4", "top", "y", None, 5),
                      ("top.x + top.w - 5", "top", "x", None, 134), ("ttw - 6", "top", "n", None, 128), ("lst.x + 2", "lst", "x", None, 3), ("lst.y + 1", "lst", "y", None, 8),
                      ("lst.y + 1 + r", "lst", "y", "VA", 9), ("lst.y + 2", "lst", "y", None, 9), ("lst.y + 1 + VA", "lst", "y", None, 25), ("lst.x + lst.w - 3", "lst", "x", None, 136),
                      ("det.x + 2", "det", "x", None, 3), ("det.y + r", "det", "y", "DR", 28), ("det.y + 1", "det", "y", None, 28), ("dtw", "det", "n", None, 134)],
}
# Worked values at 180 by 55 (body 178 by 51: 40 columns and 12 rows more than the reference): the declared weights, in rectangles
WORKED = {
    "tool_gates": [(1, 1, 178, 27), (1, 28, 178, 11), (1, 39, 88, 13), (90, 39, 89, 13)],
    "tool_sessions": [(1, 1, 178, 21), (1, 22, 178, 20), (1, 42, 178, 10)],
    "tool_masters": [(1, 1, 178, 8), (1, 9, 178, 23), (1, 32, 178, 20)],
    "tool_audit": [(1, 1, 178, 6), (1, 7, 178, 28), (1, 35, 178, 17)],
    "tool_accounts": [(1, 1, 178, 6), (1, 7, 178, 28), (1, 35, 178, 17)],
}
# The names that follow a box: the number of rows or the width of text, tied to the height or the width of a pane (it grows by what the pane grew by)
TIED = {
    "tool_gates": {"VIS": ("mat", "h"), "CL": ("cel", "h"), "RW": ("rea", "h"), "mtw": ("mat", "w"), "ctw": ("cel", "w"), "rtw": ("rea", "w"), "stw": ("ses", "w")},
    "tool_sessions": {"VS": ("ssn", "h"), "VL": ("lck", "h"), "VR": ("rwb", "h"), "stw": ("ssn", "w"), "ltw": ("lck", "w"), "rtw": ("rwb", "w")},
    "tool_masters": {"VA": ("acc", "h"), "VD": ("det", "h"), "ttw": ("top", "w"), "atw": ("acc", "w"), "dtw": ("det", "w")},
    "tool_audit": {"VL": ("lst", "h"), "DR": ("det", "h"), "ttw": ("top", "w"), "ltw": ("lst", "w"), "dtw": ("det", "w")},
    "tool_accounts": {"VA": ("lst", "h"), "DR": ("det", "h"), "ttw": ("top", "w"), "ltw": ("lst", "w"), "dtw": ("det", "w")},
}
BAD_LITERALS = [r"\b128\b", r"\b134\b", r"\b136\b", r"\b138\b", r"\b139\b", r"\bat 3,", r"\bat 72,", r"for r = 1 to \d+\b", r"'134L'", r"'64L'", r"'65L'"]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------- loading
def load_model():
    spec = importlib.util.spec_from_file_location("tklayout_units_for_l2", os.path.join(HERE, "test-tklayout-units.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tklayout_units_for_l2"] = mod
    spec.loader.exec_module(mod)
    return mod


def load():
    raw = {}
    for n in PAGE_NAMES:
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
    """The text of an internal subroutine: from its label to the next label at the start of a line (or to END)."""
    m = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^[A-Za-z][A-Za-z0-9.]*:\s*$|^end\s*$", rest, re.M)
    return rest[:n.start()] if n else rest


def py_expr(e):
    """a BASIC arithmetic expression as Python: prefix.x becomes prefix_x"""
    return re.sub(r"\b([A-Za-z]\w*)\.(\w+)\b", r"\1_\2", e)


def parse_decl(code):
    """The declaration of declare.layout as the model takes it (a dict for each pane), or None"""
    body = block(code, "declare.layout")
    panes = []
    for m in re.finditer(r"^\s*ld<(\d+)> = (.*)$", body, re.M):
        toks = [t.strip() for t in m.group(2).split(" : @vm : ")]
        vals = []
        for t in toks:
            if t.startswith("'") and t.endswith("'"):
                vals.append(t[1:-1])
            elif re.fullmatch(r"-?\d+", t):
                vals.append(int(t))
            else:
                return None
        vals += [""] * (13 - len(vals))
        keys = ["id", "band", "col", "h", "w", "gap", "vkind", "vwt", "hkind", "hwt", "minh", "minw", "prio"]
        a = {k: (None if v == "" else v) for k, v in zip(keys, vals)}
        panes.append(a)
    return panes or None


def rects_of(M, decl, w, h):
    rects, mode = M.layout(decl, M.frame(w, h))
    return rects, mode


def get_rects_env(code, page, decl, rects):
    """The variables get.rects sets, evaluated here from the page's own formulas against the model's rectangles; None when a line cannot be read"""
    ids = [a["id"] for a in decl]
    env = {}
    cur = None
    for ln in block(code, "get.rects").split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r"call \$tk_layout\('pane', ctx, '([a-z]+)', lrc\)$", ln)
        if m:
            cur = m.group(1)
            continue
        if ln == "return":
            continue
        for part in ln.split(" ; "):
            m = re.match(r"([A-Za-z]\w*(?:\.\w+)?) = (.*)$", part.strip())
            if not m:
                return None
            name, expr = m.group(1), m.group(2)
            mm = re.fullmatch(r"lrc<1, (\d)>", expr)
            if mm:
                if cur not in ids:
                    return None
                env[name.replace(".", "_")] = rects[ids.index(cur)][int(mm.group(1)) - 1]
                continue
            try:
                env[name.replace(".", "_")] = eval(py_expr(expr), {}, dict(env))
            except Exception:
                return None
    return env


def ev(expr, env, r=1):
    e = dict(env)
    e["r"] = r
    return eval(py_expr(expr), {}, e)


def head_literals(page):
    """the literal boxes of the page as committed (git HEAD), or None when git cannot say"""
    try:
        r = subprocess.run(["git", "-C", os.environ.get("SDREGRESS_REPO") or HERE, "show", "HEAD:sdb_ai/sd64/sdsys/gpl.bp/" + page], capture_output=True, text=True, errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return [tuple(int(v) for v in m.groups()) for m in re.finditer(r"screen box at (\d+),(\d+) size (\d+),(\d+)", r.stdout)]


def overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------- the checks
def checks(raw, model=None, head=True):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    T = model or load_model()
    M = T.Model()
    code = {n: strip_bas(raw[n]) for n in PAGE_NAMES}
    decl = {n: parse_decl(code[n]) for n in PAGE_NAMES}

    ck("L2-0", "NULL CASE: the model of $tk_layout loaded, the five pages were found with a declaration of 3 or 4 panes each, and the tables here know every page",
       hasattr(T, "Model") and all(len(raw[n]) > 8000 for n in PAGE_NAMES) and all(decl[n] and len(decl[n]) == len(REF[n]) for n in PAGE_NAMES)
       and all(set(PREFIX[n]) == {r[0] for r in REF[n]} for n in PAGE_NAMES),
       " ".join("%s:%s" % (n, len(decl[n]) if decl[n] else None) for n in PAGE_NAMES))
    if not all(decl[n] for n in PAGE_NAMES):
        return rows

    bad = []
    for n in PAGE_NAMES:
        v = M.validate(decl[n])
        if v is not None:
            bad.append("%s: %r" % (n, v))
    ck("L2-1", "every declaration is accepted by $tk_layout's check (ids, bands, columns, sizes, the reference body 138 by 39)", not bad, "; ".join(bad))

    bad = []
    r140 = {}
    for n in PAGE_NAMES:
        rects, mode = rects_of(M, decl[n], 140, 43)
        r140[n] = rects
        want = [r[2] for r in REF[n]]
        got = [tuple(r[:4]) for r in rects]
        ids = [a["id"] for a in decl[n]]
        if got != want or mode != "full" or not all(r[4] for r in rects) or ids != [r[0] for r in REF[n]]:
            bad.append("%s: got %r want %r mode %s ids %r" % (n, got, want, mode, ids))
        sizes = [(a["w"], a["h"]) for a in decl[n]]
        if sizes != [(r[2][2], r[2][3]) for r in REF[n]]:
            bad.append("%s: declared sizes %r are not the boxes" % (n, sizes))
    ck("L2-2", "AT 140 BY 43 EVERY DECLARATION GIVES EXACTLY THE BOXES THE PAGE DREW BEFORE L2 (nothing grows at the reference; every pane shown, mode full), in the same order and with the boxes' own sizes", not bad, "; ".join(bad)[:900])

    msgs = []
    done = 0
    if head:
        for n in PAGE_NAMES:
            lit = head_literals(n)
            if lit:                                   # the committed page still holds the literal boxes: the table must be exactly them
                done += 1
                if lit != [r[2] for r in REF[n]]:
                    msgs.append("%s: HEAD has %r, REF %r" % (n, lit, [r[2] for r in REF[n]]))
    ck("L2-2b", "while the committed page still holds the literal boxes (%d of 5 do), the table REF is exactly those boxes" % done if head else "(not asked)", not msgs, "; ".join(msgs)[:600])

    bad = []
    env140 = {}
    for n in PAGE_NAMES:
        env = get_rects_env(code[n], n, decl[n], r140[n])
        if env is None:
            bad.append("%s: get.rects cannot be read" % n)
            continue
        env140[n] = env
        for name, want in CONSTS[n]:
            if env.get(name) != want:
                bad.append("%s: %s is %r, was %r" % (n, name, env.get(name), want))
        for expr, pref, axis, rname, want in EXPRS[n]:
            if expr not in code[n]:
                bad.append("%s: `%s` is not in the page" % (n, expr))
                continue
            try:
                got = ev(expr, env)
            except Exception as exc:
                bad.append("%s: `%s` cannot be evaluated (%s)" % (n, expr, exc))
                continue
            if got != want:
                bad.append("%s: `%s` is %r at 140x43, was %r" % (n, expr, got, want))
    ck("L2-3", "at 140 by 43 the names the page derives from its rectangles (%s) and every row and column it draws or tests the mouse at are the literals it used before; each expression is looked for in the page and evaluated"
       % ", ".join("%d for %s" % (len(EXPRS[n]), n[5:]) for n in PAGE_NAMES), not bad, "; ".join(bad)[:900])

    bad = []
    for n in PAGE_NAMES:
        if n not in env140:
            continue
        ids = [a["id"] for a in decl[n]]
        for (ww, hh) in SIZES:
            fr = M.frame(ww, hh)
            rects, mode = rects_of(M, decl[n], ww, hh)
            tag = "%s %dx%d" % (n, ww, hh)
            if mode != "full" or not all(r[4] for r in rects):
                bad.append("%s: mode %s, a pane hidden" % (tag, mode))
                continue
            for a, r0 in zip(rects, r140[n]):
                if a[2] < r0[2] or a[3] < r0[3]:
                    bad.append("%s: %r smaller than %r" % (tag, a, r0))
                if a[0] < fr["XBODY"] or a[1] < fr["YBODY"] or a[0] + a[2] > fr["XBODY"] + fr["BODYW"] or a[1] + a[3] > fr["YBODY"] + fr["BODYH"]:
                    bad.append("%s: %r outside the body" % (tag, a))
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    if overlaps(rects[i], rects[j]):
                        bad.append("%s: %r overlaps %r" % (tag, rects[i], rects[j]))
            # the bands fill the body: a band's panes (its columns, with their gaps) fill the width, the bands fill the height, the area not covered is the gaps
            bands = {}
            for a, rc in zip(decl[n], rects):
                bands.setdefault(a["band"], []).append((a, rc))
            hsum = 0
            area_want = 0
            for b, lst in sorted(bands.items()):
                cols = {}
                for a, rc in lst:
                    cols.setdefault(a["col"] or 1, []).append((a, rc))
                used = 0
                bh = 0
                gaps = 0
                for c, cl in sorted(cols.items()):
                    gaps += int(cl[0][0]["gap"] or 0)
                    used += int(cl[0][0]["gap"] or 0) + cl[0][1][2]
                    bh = max(bh, sum(rc[3] for a, rc in cl))
                    if sum(rc[3] for a, rc in cl) != bh and len(cols) == 1:
                        bad.append("%s band %s: column heights differ" % (tag, b))
                if used != fr["BODYW"]:
                    bad.append("%s band %s fills %d of %d columns" % (tag, b, used, fr["BODYW"]))
                hsum += bh
                area_want += (fr["BODYW"] - gaps) * bh
            if hsum != fr["BODYH"]:
                bad.append("%s: the bands fill %d of %d rows" % (tag, hsum, fr["BODYH"]))
            if sum(rc[2] * rc[3] for rc in rects) != area_want:
                bad.append("%s: area %d, wanted %d" % (tag, sum(rc[2] * rc[3] for rc in rects), area_want))
            env = get_rects_env(code[n], n, decl[n], rects)
            if env is None:
                bad.append("%s: get.rects cannot be read" % tag)
                continue
            for expr, pref, axis, rname, want in EXPRS[n]:
                if axis == "n" or expr not in code[n]:
                    continue
                pid = [k for k, v in PREFIX[n].items() if v == pref][0]
                rc = rects[ids.index(pid)]
                lo, hi = (rc[0] + 1, rc[0] + rc[2] - 2) if axis == "x" else (rc[1] + 1, rc[1] + rc[3] - 2)
                for rv in {1, env[rname] if rname else 1}:
                    got = ev(expr, env, rv)
                    if not (lo <= got <= hi):
                        bad.append("%s: `%s` with r=%s is %d, outside %d..%d of %s" % (tag, expr, rv, got, lo, hi, pid))
            # the lists show more rows when the box is taller, and the text widths follow the boxes: every name tied to a pane is its 140-by-43 value plus what the pane grew by
            for name, (pref, dim) in TIED[n].items():
                pid = [k for k, v in PREFIX[n].items() if v == pref][0]
                k = 3 if dim == "w" else 4
                grew = rects[ids.index(pid)][k - 1] - r140[n][ids.index(pid)][k - 1]
                want = dict(CONSTS[n])[name] + grew
                if env.get(name) != want:
                    bad.append("%s: %s is %r, wanted %d (the %s of %s grew by %d)" % (tag, name, env.get(name), want, dim, pid, grew))
    ck("L2-4", "LARGER (%s): every pane shown, at least its 140-by-43 size, inside the body, no two overlapping; the panes of a band fill the body's width, the bands its height, what is not covered is the "
       "declared gaps; every row and column a text uses is inside its box for the first and the last row; every row count and text width tied to a box is its 140-by-43 value plus what the box grew by"
       % ", ".join("%dx%d" % s for s in SIZES), not bad, "; ".join(bad)[:1100])

    bad = []
    for n in PAGE_NAMES:
        rects, mode = rects_of(M, decl[n], 180, 55)
        got = [tuple(r[:4]) for r in rects]
        if got != WORKED[n]:
            bad.append("%s: %r, wanted %r" % (n, got, WORKED[n]))
    ck("L2-4b", "worked values at 180 by 55 (40 columns, 12 rows more): the rows and columns are shared by the declared weights - the matrix 8 rows and the lists under the cell 4, the two lists of sessions 6 each, "
       "the account lists twice what the box under them gets, the two lists under the gate cell 20 columns each", not bad, "; ".join(bad)[:900])

    bad = []
    for n in PAGE_NAMES:
        gr = block(code[n], "get.rects")
        asked = re.findall(r"call \$tk_layout\('pane', ctx, '([a-z]+)', lrc\)", gr)
        ids = [a["id"] for a in decl[n]]
        dl = block(code[n], "draw.all")
        boxes = re.findall(r"screen box at (\w+)\.x,\1\.y size \1\.w,\1\.h", dl)
        if asked != ids:
            bad.append("%s: asks for %r, declares %r" % (n, asked, ids))
        if sorted(boxes) != sorted(PREFIX[n].get(i, "?" + i) for i in ids):
            bad.append("%s: draws the boxes %r" % (n, boxes))
        for pid, pref in PREFIX[n].items():
            if not re.search(r"\b%s\.x = lrc<1, 1> ; %s\.y = lrc<1, 2> ; %s\.w = lrc<1, 3> ; %s\.h = lrc<1, 4>" % ((pref,) * 4), gr):
                bad.append("%s: %s does not take x y w h from the rectangle" % (n, pref))
    ck("L2-5", "the panes each page asks $tk_layout for are the panes it declared, in order, each rectangle is taken whole (x y w h), and every pane is drawn as a box from its rectangle", not bad, "; ".join(bad)[:700])

    bad = []
    for n in PAGE_NAMES:
        c = code[n]
        i_open = c.find("call $tk_open('" + n.replace("_", ".", 1) + "', 'admin', ctx, err)")
        i_decl = c.find("gosub declare.layout")
        i_keys = c.find("keys = ''")
        if not (0 <= i_open < i_decl < i_keys):
            bad.append("%s: the layout is not declared between the open and the first read (%d %d %d)" % (n, i_open, i_decl, i_keys))
        dc = block(c, "declare.layout")
        if not re.search(r"call \$tk_layout\('declare', ctx, ld, perr\)\s*\n\s*if perr # '' then\s*\n\s*call \$tk_close\(ctx\)\s*\n\s*display perr\s*\n\s*stop\s*\n\s*end\s*\n\s*gosub get\.rects", dc):
            bad.append("%s: a refused declaration does not close the base and stop before the rectangles are taken" % n)
        rz = re.search(r"case nm = 'resize'(.*?)case nm = 'mouse'", c, re.S)
        rzt = rz.group(1) if rz else ""
        if not re.search(r"call \$tk_layout\('refresh', ctx, '', lchg\)\s*\n\s*gosub get\.rects\s*\n\s*gosub keep\.in\.view\s*\n\s*gen \+= 1\s*\n\s*ctx<TK\.C\.GEN> = gen\s*\n\s*gosub draw\.all", rzt):
            bad.append("%s: the resize key does not refresh, take the rectangles, keep the rows in view, raise the generation and draw again in that order" % n)
        kv = block(c, "keep.in.view")
        if "if ta" not in kv or "< 0 then ta" not in kv and "< 0 then ta1" not in kv:
            bad.append("%s: keep.in.view does not keep the scroll inside the list" % n)
    ac = code["tool_accounts"]
    if not re.search(r"call \$tk_open\('tool\.accounts', 'admin', ctx, err\)\s*\n\s*if err # '' then\s*\n\s*display err\s*\n\s*done = 1\s*\n\s*return\s*\n\s*end\s*\n\s*gen \+= 1\s*\n\s*ctx<TK\.C\.GEN> = gen\s*\n\s*gosub declare\.layout", ac):
        bad.append("tool_accounts: the layout is not declared again after the terminal was handed to a verb")
    ck("L2-6", "each page opens the layout once between $tk_open and its first read; a refused declaration closes the base and stops; the resize key does refresh, rectangles, scroll kept in view, generation, redraw in that order; "
       "tool.accounts declares again after the terminal was handed to a verb", not bad, "; ".join(bad)[:900])

    bad = []
    for n in PAGE_NAMES:
        c = code[n]
        rest = c.replace(block(c, "declare.layout"), "")
        for pat in BAD_LITERALS:
            for m in re.finditer(pat, rest):
                line = rest[:m.start()].count("\n") + 1
                bad.append("%s line %d (stripped): %r" % (n, line, rest.split("\n")[line - 1].strip()[:70]))
    ck("L2-7", "no number that is really the window's is left outside the declaration: no 128, 134, 136, 138 or 139, no `at 3,`, no `for r = 1 to <number>`, no fixed fmt width of a box", not bad, "; ".join(bad)[:900])

    bad = []
    for n in PAGE_NAMES:
        m = re.search(r"call \$tk_open\('[a-z.]+', 'admin', ctx, err([^)]*)\)", code[n])
        if not m or m.group(1) != "":
            bad.append("%s: %r" % (n, m.group(0) if m else None))
    ck("L2-8", "the floor each page declares stays 140 by 43: $tk_open is called with its four arguments, no floor", not bad, "; ".join(bad))
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if old not in r[key]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (key, old[:60]))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


MUTANTS = [
    ("a pane one row too tall (the gate matrix)", "L2-1", sub("tool_gates", "ld<1> = 'matrix' : @vm : 1 : @vm : 1 : @vm : 19", "ld<1> = 'matrix' : @vm : 1 : @vm : 1 : @vm : 20")),
    ("a pane one row too short (the sessions)", "L2-2", sub("tool_sessions", "ld<1> = 'sessions' : @vm : 1 : @vm : 1 : @vm : 15", "ld<1> = 'sessions' : @vm : 1 : @vm : 1 : @vm : 14")),
    ("the gap between the two lower gate panes is lost", "L2-2", sub("tool_gates", "@vm : 69 : @vm : 1 : @vm : 'stretch'", "@vm : 69 : @vm : '' : @vm : 'stretch'")),
    ("a declaration of another page's id", "L2-2", sub("tool_masters", "ld<1> = 'master' :", "ld<1> = 'masters' :")),
    ("a weight changed (the accounts list of the master files)", "L2-4b", sub("tool_masters", "@vm : 'stretch' : @vm : 2 : @vm : 'stretch' : @vm : 1\n   ld<3>", "@vm : 'stretch' : @vm : 1 : @vm : 'stretch' : @vm : 1\n   ld<3>")),
    ("the sessions list no longer stretches", "L2-4b", sub("tool_sessions", "ld<2> = 'locks' : @vm : 2 : @vm : 1 : @vm : 14 : @vm : 138 : @vm : '' : @vm : 'stretch'", "ld<2> = 'locks' : @vm : 2 : @vm : 1 : @vm : 14 : @vm : 138 : @vm : '' : @vm : ''")),
    ("the account rows counted one short", "L2-3", sub("tool_gates", "VIS = mat.h - 5", "VIS = mat.h - 4")),
    ("the counts line one row too low", "L2-3", sub("tool_gates", "at mat.x + 2,mat.y + mat.h - 3 attr 'bold'", "at mat.x + 2,mat.y + mat.h - 2 attr 'bold'")),
    ("the hint of the row box on the border", "L2-3", sub("tool_sessions", "rwb.y + rwb.h - 2", "rwb.y + rwb.h - 1")),
    ("the first cell's column wrong", "L2-3", sub("tool_gates", "X0 = mat.x + 28", "X0 = mat.x + 29")),
    ("the detail rows counted from the wrong constant", "L2-3", sub("tool_audit", "DR = det.h - 2", "DR = det.h - 1")),
    ("the words of the master page start on the last difference row", "L2-3", sub("tool_masters", "det.y + VD + 1 + r", "det.y + VD + r")),
    ("a text drawn past the box's right edge at a bigger window (a column fixed to the reference)", "L2-4", sub("tool_accounts", "dtw = det.w - 4", "dtw = det.w + 4")),
    ("the list rows of the audit fixed at the reference", "L2-4", sub("tool_audit", "VL = lst.h - 3", "VL = 17")),
    ("a pane is not asked for", "L2-5", sub("tool_masters", "   call $tk_layout('pane', ctx, 'detail', lrc)\n   det.x = lrc<1, 1> ; det.y = lrc<1, 2> ; det.w = lrc<1, 3> ; det.h = lrc<1, 4>\n", "")),
    ("a rectangle taken without its height", "L2-5", sub("tool_audit", "lst.h = lrc<1, 4>", "lst.h = lrc<1, 3>")),
    ("a box is not drawn from its rectangle", "L2-5", sub("tool_gates", "screen box at rea.x,rea.y size rea.w,rea.h", "screen box at 1,31 size rea.w,rea.h")),
    ("the layout is never declared (the sessions)", "L2-6", sub("tool_sessions", "   gosub declare.layout\n\n   keys = ''", "\n   keys = ''")),
    ("the layout is declared before the open (the masters)", "L2-6", sub("tool_masters", "   call $tk_open('tool.masters', 'admin', ctx, err)", "   gosub declare.layout\n   call $tk_open('tool.masters', 'admin', ctx, err)")),
    ("a refused declaration goes on (the gates)", "L2-6", sub("tool_gates", "      call $tk_close(ctx)\n      display perr\n      stop\n", "      null\n")),
    ("the resize key does not refresh (the sessions)", "L2-6", sub("tool_sessions", "            call $tk_layout('refresh', ctx, '', lchg)\n", "")),
    ("the resize key does not take the rectangles (the audit)", "L2-6", sub("tool_audit", "            call $tk_layout('refresh', ctx, '', lchg)\n            gosub get.rects\n", "            call $tk_layout('refresh', ctx, '', lchg)\n")),
    ("the resize key does not keep the rows in view (the accounts)", "L2-6", sub("tool_accounts", "            gosub keep.in.view\n", "")),
    ("the layout is not declared again after a verb had the terminal", "L2-6", sub("tool_accounts", "   gosub declare.layout                                         ;* the new $tk_open has no panes\n", "")),
    ("a literal width is left (the masters)", "L2-7", sub("tool_masters", "at top.x + 2,top.y + 4 width ttw", "at top.x + 2,top.y + 4 width 134")),
    ("a literal row is left (the audit)", "L2-7", sub("tool_audit", "at lst.x + 2,lst.y + 1 attr 'header' width ltw", "at 3,8 attr 'header' width ltw")),
    ("a mouse limit is left (the gates)", "L2-7", sub("tool_gates", "mx <= mat.x + mat.w - 3", "mx <= 136")),
    ("a loop of a fixed number of rows (the sessions)", "L2-7", sub("tool_sessions", "for r = 1 to VR", "for r = 1 to 7")),
    ("the floor is lowered (the audit)", "L2-8", sub("tool_audit", "call $tk_open('tool.audit', 'admin', ctx, err)", "call $tk_open('tool.audit', 'admin', ctx, err, 100, 30)")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:300]))
        bad += 0 if ok else 1
    return bad


def selftest(raw, model):
    base = [r[0] for r in checks(raw, model, head=False) if not r[2]]
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
        failed = sorted({r[0] for r in checks(m, model, head=False) if not r[2]})
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        holes += 0 if hit else 1
    print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main(argv):
    raw = load()
    model = load_model()
    print("test-l2-admin-units: tree %s" % os.path.dirname(GPL))
    if "--selftest" in argv:
        return selftest(raw, model)
    rows = checks(raw, model)
    bad = report(rows)
    print("\ntest-l2-admin-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
