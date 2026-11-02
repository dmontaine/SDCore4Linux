#!/usr/bin/env python3
"""test-focusmarks-units.py - the toolkit pages' focus marks (S.99, look only): [*] on the box with the focus, [-] on the others.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-focusmarks-units.py
  python3 .../test-focusmarks-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.  Written 1 Nov 26.

THE RULE (owner, 19 Oct 2026, for the IDE: "a small visual indicator in the top right corner of each pane to indicate that it is
active, [-] for off, [*] for on"; carried to the pages on 1 Nov 2026 under "all panes need to share the same look and feel"):
a page that has more than one box the focus can be in names those boxes in ctx<TK.C.FOCI> - the layout pane's id and the name the
page gives $tk_frame for it - and $tk_frame draws the marks over each box's top border.  A page whose id is not one of its own
layout panes, or whose name is not one it ever passes to $tk_frame, gets no mark or a wrong one, and nothing on the screen says so:
that is what this refuses, page by page.

***WHAT THIS IS AND IS NOT.***  It reads the programs as text.  It cannot say a mark is drawn where the box is, or moves with the
focus: those are sandbox-tool-sessions.py rows S8c1 and S8c2.  --selftest mutates the sources and requires each mutant caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GP = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp"))
PAGES = ["tool_sessions", "tool_menus", "tool_ai", "tool_viewers", "tool_bulk", "tool_query", "tool_test", "tool_jobs"]


def code(src):
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("*"))


def page_checks(name, src, ck):
    c = code(src)
    m = re.search(r"^\s*ctx<TK\.C\.FOCI>\s*=\s*(.+?)(?:\s*;\*.*)?$", c, re.M)
    ck("%s: names its focus boxes (ctx<TK.C.FOCI> = ...)" % name, m is not None)
    if not m:
        return
    pairs = re.findall(r"'([^']*)'\s*:\s*@sm\s*:\s*'([^']*)'", m.group(1))
    ck("%s: two or more boxes named, each an id and a name" % name, len(pairs) >= 2 and len(pairs) == m.group(1).count("@sm"), pairs)
    ids = set(re.findall(r"^\s*\w+<\d+>\s*=\s*'([a-z0-9]+)'\s*:\s*@vm", c, re.M))
    bad = [i for i, _ in pairs if i not in ids]
    ck("%s: every id is a pane of the page's own layout declaration" % name, ids and not bad, "not declared: %s; declared %s" % (bad, sorted(ids)))
    # the names the page gives $tk_frame: its pane list, or the literal names it sets
    given = set()
    for lst in re.findall(r"^\s*(?:pnames|panes)\s*=\s*(.+)$", c, re.M):
        given |= set(re.findall(r"'([^']*)'", lst))
    given |= set(re.findall(r"^\s*(?:pn|cur\.pane|pane)\s*=\s*'([^']*)'", c, re.M))
    given |= set(re.findall(r"tk_frame\(ctx,\s*keys,\s*'([^']*)'", c))
    badn = [n for _, n in pairs if n not in given]
    ck("%s: every name is one the page gives $tk_frame" % name, not badn, "never given: %s; given %s" % (badn, sorted(given)))
    decl = [mm.start() for mm in re.finditer(r"\$tk_layout\('declare'", c)]
    ck("%s: the names are set before the page's first layout declaration" % name, decl and m.start() < decl[0], (m.start(), decl[:1]))


def frame_checks(tk_h, tk_frame, ck):
    slots = re.findall(r"^\$define\s+TK\.C\.\w+\s+(\d+)", tk_h, re.M)
    m = re.search(r"^\$define\s+TK\.C\.FOCI\s+(\d+)", tk_h, re.M)
    ck("tk.h: TK.C.FOCI is defined, on a slot no other TK.C name has", m is not None and slots.count(m.group(1)) == 1, m.group(0) if m else None)
    c = code(tk_frame)
    ck("tk_frame: reads ctx<TK.C.FOCI> and the layout's rectangles", "ctx<TK.C.FOCI>" in c and "ctx<TK.C.RECTS, pk>" in c)
    ck("tk_frame: no marks for fewer than two boxes, or when the pane with the focus is none of them",
       re.search(r"if mk\.n < 2 or not\(mk\.any\) then mk = ''", c) is not None)
    ck("tk_frame: a collapsed box (shown 0) has no mark", re.search(r"if rc<1, 1, 5> and", c) is not None)
    ck("tk_frame: a mark is judged against the library's shadow and written only where the shadow does not show it",
       "$sl_scr('get', mk.scr)" in c and re.search(r"mk\.scr<SL\.S\.SHADOW, my \+ 1>\[mx \+ 1, 3\] # mk<1, mj, 3>", c) is not None)
    ck("tk_frame: marks that went have the border put back", "str(mk.hc, 3)" in c and "$sl_line('h', 0, mk.hc)" in c)
    ck("tk_frame: the marks' cache is its own common block, /tkframe/ unchanged",
       re.search(r"common /tkmarks/ last\.marks", c) is not None
       and re.search(r"common /tkframe/ last\.stat, last\.keys, last\.bord, last\.top, last\.gen, last\.geo\s*$", c, re.M) is not None)


def checks(srcs):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    for p in PAGES:
        page_checks(p, srcs[p], ck)
    frame_checks(srcs["tk.h"], srcs["tk_frame"], ck)
    return out


def mutants(srcs):
    res = []

    def mut(name, f, old, new):
        s = dict(srcs)
        s[f] = srcs[f].replace(old, new, 1)
        res.append((name, s, s[f] == srcs[f]))

    mut("sessions: an id that is not a layout pane", "tool_sessions", "'locks' : @sm : 'Locks'", "'lock' : @sm : 'Locks'")
    mut("bulk: a name the page never gives", "tool_bulk", "'what' : @sm : 'Operations'", "'what' : @sm : 'Operation'")
    mut("ai: only one box named", "tool_ai", "'providers' : @sm : 'Provider' : @vm : 'accounts' : @sm : 'Accounts'", "'providers' : @sm : 'Provider'")
    mut("test: the names set after the declaration", "tool_test",
        "   ctx<TK.C.FOCI> = 'list' : @sm : 'Tests' : @vm : 'detail' : @sm : 'Output'        ;* S.99: the boxes that take the focus (Output scrolls in the lower box), for $tk_frame's [*] / [-]\n   call $tk_layout('declare', ctx, d, perr)",
        "   call $tk_layout('declare', ctx, d, perr)\n   ctx<TK.C.FOCI> = 'list' : @sm : 'Tests' : @vm : 'detail' : @sm : 'Output'")
    mut("tk.h: the slot is the AI row's", "tk.h", "$define TK.C.FOCI      29", "$define TK.C.FOCI      28")
    mut("tk_frame: marks for a single box", "tk_frame", "if mk.n < 2 or not(mk.any) then mk = ''", "if mk.n < 1 then mk = ''")
    mut("tk_frame: written every time, not against the shadow", "tk_frame",
        "if mk.scr<SL.S.SHADOW, my + 1>[mx + 1, 3] # mk<1, mj, 3> then mk.out", "mk.out")
    mut("tk_frame: a collapsed box marked", "tk_frame", "if rc<1, 1, 5> and rc<1, 1, 3> >= 10 then", "if rc<1, 1, 3> >= 10 then")
    return res


def load():
    srcs = {}
    for p in PAGES + ["tk.h", "tk_frame"]:
        path = os.path.join(GP, p)
        if not os.path.isfile(path):
            return None, path
        srcs[p] = open(path, encoding="utf-8", errors="replace").read()
    return srcs, None


def main():
    srcs, missing = load()
    if srcs is None:
        print("test-focusmarks-units: CANNOT RUN - no %s" % missing)
        return 2
    if "--selftest" in sys.argv:
        base = checks(srcs)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated sources already fail:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(srcs)
        for name, s, same in ms:
            if same:
                print("  [NOT APPLIED] %s" % name)
                bad += 1
                continue
            caught = [n for n, ok, _ in checks(s) if not ok]
            print("  [%s] %s%s" % ("caught" if caught else "MISSED", name, "  (%d check(s) failed)" % len(caught) if caught else ""))
            bad += 0 if caught else 1
        print("test-focusmarks-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0
    print("gpl.bp : %s" % GP)
    res = checks(srcs)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail) + ")"))
        fails += 0 if ok else 1
    print("test-focusmarks-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
