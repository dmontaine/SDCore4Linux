#!/usr/bin/env python3
"""test-sedkeyrow-units.py - SED's key row (S.99, look only): every action it names has a key in the default layout.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sedkeyrow-units.py
  python3 .../test-sedkeyrow-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.  Written 1 Nov 26.

THE RULE (owner, 1 Nov 2026: "all panes need to share the same look and feel if possible", "Yes, look only"; the floor to
140 by 43 on Opus's review): SED is laid out for 140 by 43 and its last row is a key row in the toolkit pages' style.  The
row names about ten actions (kr.defs, beside the menu definitions) and asks SED's own table for each one's key when the row
is made (make.key.row through key.table and fmt.key), so a rebound key shows and an action with no key drops off.  An
action listed in kr.defs that the DEFAULT layout does not bind would never appear for anybody: that is what this refuses.

***WHAT THIS IS AND IS NOT.***  It reads sdsys/gpl.bp/sed as text.  It cannot say the row is drawn, in which colour, or
that a rebound key shows: those are sandbox-sed-menu.py's rows (section "S.99").  It holds: SED.ROWS is 43 and the key row
is the row below the status line; every kr.defs action up to LAST.BINDABLE.ACTION has a non-empty key.rec line in
set.default.bindings; F.MENU (not bindable) is given F10 by add.menu.key and fmt.key names that sequence F10 before the
rule that hides unnamed ESC [ sequences; make.key.row reads the table through key.table, whose loop variables are its own
(kb.*), not the s i n z j that get.key.bindings' callers and the drawing code use; paint.key.line is called by
update.screen.  --selftest mutates the source and requires each mutant to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SED = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp", "sed"))


def label_body(lines, label):
    """The code lines of a label, comments dropped: from the label to the next label in column 0, or None."""
    start = next((i for i, l in enumerate(lines) if l.startswith(label + ":")), None)
    if start is None:
        return None
    out = []
    for l in lines[start + 1:]:
        if re.match(r"^[A-Za-z][\w.]*:\s*$", l):
            break
        if l.lstrip().startswith("*"):
            continue
        out.append(l)
    return out


def checks(src):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    lines = src.splitlines()
    eq = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*equate\s+(F\.[\w.]+|LAST\.BINDABLE\.ACTION)\s+to\s+(\d+)", src, re.M)}
    ck("the action numbers are read (F.SAVE.RECORD, F.MENU, LAST.BINDABLE.ACTION)", all(k in eq for k in ("F.SAVE.RECORD", "F.MENU", "LAST.BINDABLE.ACTION")),
       sorted(eq)[:5])
    if "LAST.BINDABLE.ACTION" not in eq:
        return out
    last = eq["LAST.BINDABLE.ACTION"]

    m = re.search(r"^\s*equate\s+SED\.ROWS\s+to\s+(\d+)", src, re.M)
    ck("SED.ROWS is 43 (140 by 43, owner 1 Nov 26)", m is not None and m.group(1) == "43", m.group(0).strip() if m else "no SED.ROWS")
    ck("three rows below the text: displayed.lines = screen.lines - 3", re.search(r"^\s*displayed\.lines\s*=\s*screen\.lines\s*-\s*3\b", src, re.M) is not None)
    ck("the key row is the row below the status line", re.search(r"^\s*status\.line\s*=\s*displayed\.lines\s*\+\s*1\b", src, re.M) is not None
       and re.search(r"^\s*key\.line\s*=\s*displayed\.lines\s*\+\s*2\b", src, re.M) is not None)

    # kr.defs: the actions the row names, in order
    defs = re.findall(r"^\s*kr\.defs<-1>\s*=\s*(F\.[\w.]+)\s*:\s*@vm\s*:\s*'([^']*)'", src, re.M)
    ck("kr.defs names some actions (refuses the empty list)", len(defs) >= 5, "%d" % len(defs))
    ck("every kr.defs action is an action SED knows", all(a in eq for a, _ in defs), [a for a, _ in defs if a not in eq])
    ck("kr.defs names F.MENU", any(a == "F.MENU" for a, _ in defs))
    ck("no action is named twice", len({a for a, _ in defs}) == len(defs))

    # set.default.bindings: action 1 is `key.rec = ...`, each `key.rec<-1> = ...` is the next action, up to the gosub
    sdb = label_body(lines, "set.default.bindings")
    ck("set.default.bindings is there", sdb is not None)
    if sdb is not None:
        vals = []
        for l in sdb:
            if re.match(r"\s*gosub\s+load\.key\.bindings", l):
                break
            mm = re.match(r"\s*key\.rec(<-1>)?\s*=\s*(.*?)\s*(;\*.*)?$", l)
            if mm:
                vals.append(mm.group(2))
        ck("set.default.bindings has a key.rec line for every bindable action (%d)" % last, len(vals) == last, "%d lines" % len(vals))
        unbound = []
        for a, word in defs:
            n = eq.get(a, 0)
            if n and n <= last:
                v = vals[n - 1] if n - 1 < len(vals) else ""
                if v.strip() in ("", "''", '""'):
                    unbound.append("%s (%s)" % (a, word))
        ck("every kr.defs action up to LAST.BINDABLE.ACTION is bound in the default layout", unbound == [], unbound)

    amk = label_body(lines, "add.menu.key")
    ck("add.menu.key gives F.MENU the sequence F10 sends (ESC [21~)", amk is not None and "'[21~'" in "\n".join(amk) and "F.MENU" in "\n".join(amk))
    fk = label_body(lines, "fmt.key")
    if fk is None:
        ck("fmt.key is there", False)
    else:
        t = "\n".join(fk)
        f10 = t.find("'[21~' ; ks.out = 'F10'")
        hide = t.find("ks[1, 2] = char(27) : '['")
        ck("fmt.key names ESC [21~ F10, before the rule that hides unnamed ESC [ sequences", f10 >= 0 and hide >= 0 and f10 < hide, (f10, hide))

    mkr = label_body(lines, "make.key.row")
    ck("make.key.row is there", mkr is not None)
    if mkr is not None:
        t = "\n".join(mkr)
        ck("make.key.row reads the table through key.table, not get.key.bindings", "gosub key.table" in t and "get.key.bindings" not in t)
        ck("make.key.row asks fmt.key for the words of a key", "gosub fmt.key" in t)
        ck("make.key.row leaves an action with no named key off the row", re.search(r"if kr\.show # '' then kr\.text :=", t) is not None)
    kt = label_body(lines, "key.table")
    ck("key.table is there", kt is not None)
    if kt is not None:
        t = "\n".join(kt)
        assigned = set(re.findall(r"^\s*(?:for\s+)?([a-z][\w.]*)\s*(?:<[^>]*>)?\s*=", t, re.M))
        ck("key.table assigns only kb.* variables", assigned and all(v.startswith("kb.") for v in assigned), sorted(assigned))
    gkb = label_body(lines, "get.key.bindings")
    ck("get.key.bindings gives s the table key.table made", gkb is not None and "gosub key.table" in "\n".join(gkb) and re.search(r"^\s*s\s*=\s*kb\.s\s*$", "\n".join(gkb), re.M))

    us = label_body(lines, "update.screen")
    ck("update.screen paints the key row", us is not None and "gosub paint.key.line" in "\n".join(us))
    pat = label_body(lines, "paint.app.tag")
    t = "\n".join(pat or [])
    ck("paint.app.tag gives $sl_put a COPY of ap.tag: $sl_put cuts its text argument, which is passed by reference (a narrow window emptied ap.tag, 1 Nov 26)",
       pat is not None and re.search(r"\$sl_put\([^)]*,\s*ap\.tag\s*,", t) is None and re.search(r"^\s*(\w[\w.]*)\s*=\s*ap\.tag\s*$", t, re.M) is not None, t)
    lkb = label_body(lines, "load.key.bindings")
    ck("load.key.bindings marks the row to be made again", lkb is not None and re.search(r"^\s*kr\.dirty\s*=\s*@true", "\n".join(lkb), re.M))
    return out


def mutants(src):
    res = []
    res.append(("the floor back to 42", src.replace("   equate SED.ROWS to 43\n", "   equate SED.ROWS to 42\n", 1)))
    res.append(("save unbound in the default layout", src.replace("   key.rec<-1> = '@S'               ;* F.SAVE.RECORD\n",
                                                                 "   key.rec<-1> = ''               ;* F.SAVE.RECORD\n", 1)))
    res.append(("an action no default key has is listed", src.replace("   kr.defs<-1> = F.REDO : @vm : 'redo'\n",
                                                                     "   kr.defs<-1> = F.REDO : @vm : 'redo'\n   kr.defs<-1> = F.GOTO.BUFFER : @vm : 'buffer'\n", 1)))
    res.append(("F10 not named", src.replace("      case ks = char(27) : '[21~' ; ks.out = 'F10' ; return\n", "", 1)))
    res.append(("key.table loops on i", src.replace("   for kb.i = 1 to 255\n", "   for i = 1 to 255\n", 1)))
    res.append(("make.key.row calls get.key.bindings", src.replace("   kr.dirty = @false\n   gosub key.table\n", "   kr.dirty = @false\n   gosub get.key.bindings\n", 1)))
    res.append(("the key row is not painted", src.replace("   gosub paint.key.line ", "   * gosub paint.key.line ", 1)))
    res.append(("an unbound action stays on the row", src.replace("      if kr.show # '' then kr.text :=", "      kr.text :=", 1)))
    res.append(("the tag itself is handed to $sl_put", src.replace("   at.text = ap.tag\n   call $sl_put(scr, screen.width - len(ap.tag), 0, at.text, 'a')\n",
                                                                "   call $sl_put(scr, screen.width - len(ap.tag), 0, ap.tag, 'a')\n", 1)))
    res.append(("the row is never made again", src.replace("load.key.bindings:\n   kr.dirty = @true", "load.key.bindings:\n   kr.dirty = @false", 1)))
    return res


def main():
    if not os.path.isfile(SED):
        print("test-sedkeyrow-units: CANNOT RUN - no sed at %s" % SED)
        return 2
    src = open(SED).read()
    if "--selftest" in sys.argv:
        base = checks(src)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated source already fails:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(src)
        for name, msrc in ms:
            if msrc == src:
                print("  [NOT APPLIED] %s" % name)
                bad += 1
                continue
            caught = [n for n, ok, _ in checks(msrc) if not ok]
            if caught:
                print("  [caught] %s  (%d check(s) failed)" % (name, len(caught)))
            else:
                print("  [MISSED] %s" % name)
                bad += 1
        print("test-sedkeyrow-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0
    print("sed : %s" % SED)
    res = checks(src)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail) + ")"))
        fails += 0 if ok else 1
    print("test-sedkeyrow-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
