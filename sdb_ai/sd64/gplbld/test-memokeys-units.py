#!/usr/bin/env python3
# test-memokeys-units.py - the editor's keys of the memo area (S.88 D2, 29 Oct 2026), read off the source of sl_memo and ide as text.  FREE CHECK: no install, no sd.
#   K1  edkeys is an opt-in: sl_memo reads w{'edkeys'} once into ek, every one of the five new cases is guarded by `and ek` (a user program's SCREEN MEMO never gets them), only the
#       IDE sets the flag, and nothing else in gpl.bp does
#   K2  the four movement keys (Ctrl-Home, Ctrl-End, Ctrl-Left, Ctrl-Right) are cases BEFORE `case ro` (a readonly area moves), Ctrl-Del is AFTER it (a readonly area does not delete)
#   K3  Ctrl-Home is line 1 column 1, Ctrl-End the end of the last line; Ctrl-Left / Ctrl-Right are the word code of Ctrl-P / Ctrl-U (blanks, then the word) and cross a line end
#   K4  Ctrl-Del is one undo step of the kind 'delword' (snap.push BEFORE the lines change), deletes the selection if there is one, the blanks and the word at the cursor otherwise,
#       joins the next line at the end of a line, and ends with want = cx and the mark cleared
#   K5  without the flag these keys are not the area's: the final `case 1` answers 'unhandled'
# The behaviour on a screen is sandbox-memokeys.py's (NOT WRITTEN: the first run of the complete test shows whether the terminal sends these keys at all; sandbox-realkeys.py is the
# decoding row).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-memokeys-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-memokeys-units.py --selftest
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BP = os.environ.get("BPDIR", os.path.normpath(os.path.join(HERE, "..", "sdsys", "gpl.bp")))
NEW_KEYS = ("ctrl-home", "ctrl-end", "ctrl-right", "ctrl-left", "ctrl-del")


def read(name):
    with open(os.path.join(BP, name), encoding="latin-1") as f:
        return f.read()


def strip(src):
    out = []
    for l in src.split("\n"):
        if l.lstrip().startswith("*"):
            continue
        out.append(re.sub(r";\*.*$", "", l).rstrip())
    return "\n".join(out)


def case_block(text, key):
    """the lines of `case key = '<key>' and ek` up to the next case line at the same indent"""
    m = re.search(r"(?m)^( *)case key = '%s' and ek\n" % re.escape(key), text)
    if not m:
        return None
    ind = m.group(1)
    rest = text[m.end():]
    n = re.search(r"(?m)^%scase " % ind, rest)
    return rest[:n.start()] if n else rest


def checks(s):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, "", bool(ok), detail))

    memo, ide = strip(s["sl_memo"]), strip(s["ide"])
    others = [os.path.basename(p) for p in glob.glob(os.path.join(BP, "*")) if os.path.basename(p) not in ("sl_memo", "ide")
              and "'edkeys'" in strip(open(p, encoding="latin-1", errors="replace").read())]
    ck("K1 edkeys is an opt-in of the program: read once (ek = w{'edkeys'} + 0), each new case needs `and ek`, only the IDE sets it",
       memo.count("w{'edkeys'}") == 1 and "ek = w{'edkeys'} + 0" in memo and all(("case key = '%s' and ek" % k) in memo for k in NEW_KEYS) and not re.search(r"case key = 'ctrl-(home|end|left|right|del)'\s*\n", memo)
       and ide.count("mw{'edkeys'} = 1") == 1 and not others, repr(others))
    ro = memo.find("      case ro\n")
    pos = {k: memo.find("case key = '%s' and ek" % k) for k in NEW_KEYS}
    ck("K2 the movement keys come before `case ro` and Ctrl-Del after it", ro > 0 and all(0 < pos[k] < ro for k in NEW_KEYS[:4]) and pos["ctrl-del"] > ro, repr((ro, pos)))
    top, end = case_block(memo, "ctrl-home"), case_block(memo, "ctrl-end")
    ck("K3a Ctrl-Home is line 1 column 1 and Ctrl-End the end of the last line", top is not None and "cy = 1" in top and "cx = 1" in top and end is not None and "cy = n" in end and "cx = len(lines<n>) + 1" in end,
       repr((top, end)))
    fwd, back = case_block(memo, "ctrl-right"), case_block(memo, "ctrl-left")
    ck("K3b Ctrl-Right and Ctrl-Left are the blanks-then-word code of Ctrl-U and Ctrl-P, and cross a line end",
       fwd is not None and "while cx <= len(ln) and ln[cx, 1] = ' '" in fwd and "while cx <= len(ln) and ln[cx, 1] # ' '" in fwd and "if cy < n then" in fwd
       and back is not None and "while cx > 1 and ln[cx, 1] = ' '" in back and "while cx > 1 and ln[cx - 1, 1] # ' '" in back and "if cy > 1 then" in back, repr((fwd, back)))
    dw = case_block(memo, "ctrl-del")
    ok = dw is not None
    if ok:
        i = [dw.find(x) for x in ("kind = 'delword'", "gosub snap.push", "if has.sel then", "gosub del.sel", "ce = cx", "lines<cy> = ln[1, cx - 1] : ln[ce, len(ln)]", "del lines<cy + 1>", "want = cx", "my = 0 ; mx = 0")]
        ok = all(x >= 0 for x in i) and i == sorted(i)
    ck("K4 Ctrl-Del is one undo step 'delword' made BEFORE the lines change: the selection, else the blanks and the word, else a join at the end of a line; then want = cx and no mark", ok, repr(dw))
    tail = memo[memo.rfind("      case 1\n"):] if "      case 1\n" in memo else ""
    ck("K5 without the flag the keys fall to `case 1`, which answers unhandled", "ret = 'unhandled' : @fm : key" in tail, tail[:120])
    return rows


def run():
    s = {"sl_memo": read("sl_memo"), "ide": read("ide")}
    bad = 0
    for i, what, ok, detail in checks(s):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok else "   <- " + str(detail)[:300]))
        bad += 0 if ok else 1
    print("\ntest-memokeys-units: %d passed, %d failed" % (len(checks(s)) - bad, bad))
    return 1 if bad else 0


def selftest():
    s0 = {"sl_memo": read("sl_memo"), "ide": read("ide")}
    if any(not ok for _, _, ok, _ in checks(s0)):
        print("selftest: the unchanged tree fails, so a mutant's failure cannot be told from the tree's")
        return 1
    caught = missed = 0

    def mutant(name, prog, old, new):
        nonlocal caught, missed
        s = dict(s0)
        if old not in s[prog]:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        s[prog] = s[prog].replace(old, new, 1)
        failing = [i.split()[0] for i, _, ok, _ in checks(s) if not ok]
        if failing:
            print("  [caught] %s (%s)" % (name, ", ".join(failing)))
            caught += 1
        else:
            print("  [MISSED] %s" % name)
            missed += 1

    mutant("Ctrl-Del is for everyone", "sl_memo", "case key = 'ctrl-del' and ek", "case key = 'ctrl-del'")
    mutant("Ctrl-Home is for everyone", "sl_memo", "case key = 'ctrl-home' and ek", "case key = 'ctrl-home'")
    mutant("the IDE does not set the flag", "ide", "mw{'edkeys'} = 1", "mw{'edkeys'} = 0")
    mutant("the flag is not read", "sl_memo", "ek = w{'edkeys'} + 0", "ek = 1")
    mutant("Ctrl-Del before `case ro`", "sl_memo", "      case ro\n", "      case key = 'zz-never'\n         null\n      case ro\n         ret = 'unhandled' : @fm : key\n      case key = 'ctrl-del' and ek\n         null\n      case key = 'zz-never2'\n")
    mutant("Ctrl-End goes to the first line", "sl_memo", "         cy = n\n         cx = len(lines<n>) + 1\n      case key = 'ctrl-right' and ek", "         cy = 1\n         cx = len(lines<n>) + 1\n      case key = 'ctrl-right' and ek")
    mutant("Ctrl-Right does not cross a line end", "sl_memo", "         ln = lines<cy>\n         if cx > len(ln) then\n            if cy < n then\n               cy += 1\n               cx = 1\n            end\n         end else\n            loop\n            while cx <= len(ln) and ln[cx, 1] = ' '\n               cx += 1\n            repeat\n            loop\n            while cx <= len(ln) and ln[cx, 1] # ' '\n               cx += 1\n            repeat\n         end\n      case key = 'ctrl-left' and ek", "         ln = lines<cy>\n         if cx > len(ln) then\n            null\n         end else\n            loop\n            while cx <= len(ln) and ln[cx, 1] = ' '\n               cx += 1\n            repeat\n            loop\n            while cx <= len(ln) and ln[cx, 1] # ' '\n               cx += 1\n            repeat\n         end\n      case key = 'ctrl-left' and ek")
    mutant("Ctrl-Del is no undo step", "sl_memo", "         kind = 'delword'\n         gosub snap.push\n", "         kind = 'delword'\n")
    mutant("Ctrl-Del leaves the mark", "sl_memo", "               end\n            end\n         end\n         want = cx\n         my = 0 ; mx = 0\n      case key = 'ctrl-k'", "               end\n            end\n         end\n         want = cx\n      case key = 'ctrl-k'")
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
