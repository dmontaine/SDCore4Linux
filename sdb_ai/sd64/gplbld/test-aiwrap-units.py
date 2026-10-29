#!/usr/bin/env python3
# test-aiwrap-units.py - what the AI proposes is SHOWN whole, not cut at the box (S.88 phase 2, S5; 28 Oct 2026), read off the source of tk_ai as text, and a MODEL of the row cutting run over
# random lines.  The behaviour is sandbox-ai-ide.py's rows I14a and I14b (a 230 character new line must show 230 characters; WRITTEN, not run) and the mutant cut-not-wrapped; this holds the
# SHAPE a runtime row cannot see:
#   - no line of the preview, the diff or the command is cut with a substring at the box width any more (the old `[1, wrapw - 2]` and `[1, wrapw - 6]`): every one goes through wrap.exact,
#     which cuts a line into rows of EXACTLY the width, no character lost and none added, and the rows are shown as they come;
#   - the diff counts its ROWS towards the 30 it will show (a proposal that does not fit is not offered: message 11659), for the old lines and the new ones;
#   - the command is wrapped from the same variable that is run (pcmd), and the action line with its label and argument is wrapped by $tk_wrap;
#   - the text Accept applies (the edit list's new text) is the text the diff was built from: the same variable, split at the same line feeds.
# AND a model in Python of wrap.exact over 3,000 random lines: the rows joined are the line, none is wider than the width, the count is the ceiling of the length over the width (one row for
# an empty line), and a diff built from them shows every character of a new text the edit applies.
# FREE CHECK: no install, no sd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aiwrap-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aiwrap-units.py --selftest
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BP = os.environ.get("BPDIR", os.path.normpath(os.path.join(HERE, "..", "sdsys", "gpl.bp")))


def read(name):
    with open(os.path.join(BP, name), encoding="latin-1") as f:
        return f.read()


def code(text):
    out = []
    for l in text.split("\n"):
        s = re.sub(r";\*.*$", "", l).rstrip()
        if s.strip() and not s.lstrip().startswith("*"):
            out.append(s.strip())
    return "\n".join(out)


def section(text, label):
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.rstrip() == label + ":":
            out = []
            for l2 in lines[i + 1:]:
                if re.match(r"^[A-Za-z][\w.]*:\s*$", l2) or re.match(r"^end\s*$", l2):
                    break
                out.append(l2)
            return "\n".join(out)
    return ""


def ordered(text, *parts):
    pos = 0
    for p in parts:
        i = text.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def wrap_exact(text, w, p1, p2):
    """The model of wrap.exact: rows of at most w characters, the first behind p1, the others behind p2; an empty text is the one row p1."""
    if text == "":
        return [p1]
    return [(p1 if k == 0 else p2) + text[k:k + w] for k in range(0, len(text), w)]


def checks(src):
    ai = src["tk_ai"]
    c = code(ai)
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    ck("W1 no substring cut at the box is left in tk_ai (`[1, wrapw - n]`): the preview, the diff and the command are not cut", not re.search(r"\[1, wrapw - \d+\]", c), "; ".join(re.findall(r".*\[1, wrapw - \d+\].*", c))[:200])
    we = code(section(ai, "wrap.exact"))
    ck("W2 wrap.exact cuts the text into rows of exactly wr.w characters, the first behind wr.p1 and the rest behind wr.p2, and an empty text is the one row wr.p1",
       ordered(we, "wr.out = ''", "wr.len = len(wr.text)", "if wr.len = 0 then", "wr.out = wr.p1", "return", "for wr.k = 1 to wr.len step wr.w",
               "wr.out<-1> = (if wr.k = 1 then wr.p1 else wr.p2) : wr.text[wr.k, wr.w]", "next wr.k", "return"), we)
    ask = code(section(ai, "run.ask"))
    pv = ask.split("body<-1> = sysmsg(11641, n.acts, len(alist))")[1].split("body<-1> = sysmsg(11643, len(req))")[0] if "body<-1> = sysmsg(11641, n.acts, len(alist))" in ask else ""
    ck("W3 the preview: the page's actions, the page's text, the text being worked on and the selection are each put through wrap.exact (4 uses), at the box width less the two blanks of the indent",
       pv.count("gosub wrap.exact") == 4 and "wr.w = wrapw - 2" in pv and "wr.text = acts<1, i>" in pv and "wr.text = field(ptext, nl, p)" in pv and "wr.text = field(tbm, nl, p)" in pv
       and "wr.text = field(selm, nl, p)" in pv, pv[:300])
    ed = code(section(ai, "read.edits"))
    ck("W4 the diff: every old line and every new line goes through wrap.exact at the box width less six, behind the sign and a hanging indent, and the rows are appended as they come",
       ordered(ed, "wr.w = wrapw - 6", "wr.p1 = '- ' ; wr.p2 = '  '", "wr.text = field(eo, nl, j)", "gosub wrap.exact", "diff.lines<-1> = wr.out", "wr.p1 = '+ ' ; wr.p2 = '  '",
               "wr.text = field(en, nl, j)", "gosub wrap.exact", "diff.lines<-1> = wr.out"), ed[-700:])
    ck("W5 the diff counts its ROWS: the old lines and the new ones each add the rows of the wrapped line to dl, and more than 30 is not offered (11659)",
       ed.count("dl += dcount(wr.out, @fm)") == 2 and ordered(ed, "dl += dcount(wr.out, @fm)", "dl += dcount(wr.out, @fm)", "if dl > 30 then", "sysmsg(11659, dl)", "return", "pk = 'edit'"), ed[-500:])
    ck("W6 what Accept applies is what was shown: the edit list takes the new text from enew<k> and the diff shows the same variable (en = enew<k>, split at the same line feeds)",
       ordered(ed, "en = enew<k>", "wr.text = field(en, nl, j)") and "ed.list<1, -1> = ep : @sm : elen<k> : @sm : en" in ed, "")
    cm = ask.split("case pk = 'command'")[1].split("case 1")[0] if "case pk = 'command'" in ask else ""
    ck("W7 the command is shown whole: wrapped from pcmd (the string the answer returns and the person runs) at the box width less four, before the Run and Cancel buttons are named",
       ordered(cm, "body<-1> = sysmsg(11648)", "wr.w = wrapw - 4", "wr.text = pcmd", "gosub wrap.exact", "body<-1> = wr.out", "btn = '&Run,&Cancel'")
       and "(if pk = 'edit' then ed.list else pcmd)" in ask, cm[:300])
    ac = ask.split("case pk = 'action'")[1].split("case pk = 'command'")[0] if "case pk = 'action'" in ask else ""
    ck("W8 the action line (the label and the argument) is wrapped by $tk_wrap, not left to the box", "call $tk_wrap(sysmsg(11647, plabel" in ac and "body<-1> = pieces" in ac, ac[:300])
    ck("W9 the answer's own words are still wrapped by $tk_wrap (say), as they were", "call $tk_wrap(say, wrapw, pieces)" in ask, "")
    # the model
    rng = random.Random(20261028)
    bad = 0
    for _ in range(3000):
        w = rng.randint(14, 94)
        t = "".join(rng.choice("abc ZZé_") for _ in range(rng.choice([0, 1, w - 1, w, w + 1, 2 * w, rng.randint(0, 400)])))
        r = wrap_exact(t, w, "- ", "  ")
        body = [x[2:] for x in r]
        if "".join(body) != t or any(len(x) > w for x in body) or len(r) != max(1, -(-len(t) // w)):
            bad += 1
    ck("Y1 model: 3,000 random lines and widths - the rows joined are the line, none is wider than the width, and the number of rows is the ceiling of the length over the width (one for an empty line) (%d bad)" % bad,
       bad == 0, "")
    new = "Z" * 230
    shown = wrap_exact(new, 94, "+ ", "  ")
    ck("Y2 model: the 230 character line of sandbox-ai-ide.py's I14a is shown in 3 rows holding 230 characters in all (the old code showed the first 94)",
       len(shown) == 3 and sum(x.count("Z") for x in shown) == 230 and new[:94].count("Z") == 94, repr([len(x) for x in shown]))
    return rows


def load():
    return {"tk_ai": read("tk_ai")}


def run():
    rows = checks(load())
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail[:300]))
        bad += 0 if ok else 1
    print("test-aiwrap-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad or not rows else 0


def selftest():
    src = load()
    if not all(ok for _, ok, _ in checks(src)):
        print("  [FAIL] the real source does not pass")
        return 1
    print("  [ok] the real source passes")
    caught = missed = 0

    def mutant(name, old, new):
        nonlocal caught, missed
        s = dict(src)
        if s["tk_ai"].count(old) != 1:
            print("  [MISSED] %s: the text to change is found %d times" % (name, s["tk_ai"].count(old)))
            missed += 1
            return
        s["tk_ai"] = s["tk_ai"].replace(old, new, 1)
        failing = [n for n, ok, _ in checks(s) if not ok]
        if failing:
            print("  [caught] %s (%s)" % (name, ", ".join(f.split()[0] for f in failing)))
            caught += 1
        else:
            print("  [MISSED] %s" % name)
            missed += 1

    mutant("rows of the first chunk only", "   for wr.k = 1 to wr.len step wr.w\n", "   for wr.k = 1 to 1 step wr.w\n")
    mutant("a chunk one short", "wr.text[wr.k, wr.w]", "wr.text[wr.k, wr.w - 1]")
    mutant("an empty line shows nothing", "      wr.out = wr.p1\n      return\n", "      return\n")
    mutant("old lines cut again", "         wr.text = field(eo, nl, j)\n         gosub wrap.exact\n         diff.lines<-1> = wr.out\n",
           "         diff.lines<-1> = '- ' : field(eo, nl, j)[1, wrapw - 6]\n")
    mutant("new lines cut again", "            wr.text = field(en, nl, j)\n            gosub wrap.exact\n            diff.lines<-1> = wr.out\n",
           "            diff.lines<-1> = '+ ' : field(en, nl, j)[1, wrapw - 6]\n")
    mutant("rows of the new lines not counted", "            diff.lines<-1> = wr.out\n            dl += dcount(wr.out, @fm)\n         next j\n", "            diff.lines<-1> = wr.out\n            dl += 1\n         next j\n")
    mutant("rows of the old lines not counted", "         diff.lines<-1> = wr.out\n         dl += dcount(wr.out, @fm)\n      next j\n", "         diff.lines<-1> = wr.out\n         dl += 1\n      next j\n")
    mutant("limit of rows lifted", "   if dl > 30 then", "   if dl > 3000 then")
    mutant("command cut again", "         wr.text = pcmd\n         gosub wrap.exact\n         body<-1> = wr.out\n", "         body<-1> = '  ' : pcmd[1, wrapw - 4]\n")
    mutant("command wrapped at the wrong width", "         wr.w = wrapw - 4\n", "         wr.w = wrapw + 40\n")
    mutant("action line not wrapped", "         call $tk_wrap(sysmsg(11647, plabel : (if parg # '' then ' (' : parg : ')' else '')), wrapw, pieces)      ;* (S5) a label and an argument can be wider than the box: wrapped, not cut\n         body<-1> = pieces\n",
           "         body<-1> = sysmsg(11647, plabel : (if parg # '' then ' (' : parg : ')' else ''))\n")
    mutant("preview lines cut again", "         wr.text = field(ptext, nl, p)\n         gosub wrap.exact\n         body<-1> = wr.out\n", "         body<-1> = '  ' : field(ptext, nl, p)[1, wrapw - 2]\n")
    mutant("accept applies another text", "      ed.list<1, -1> = ep : @sm : elen<k> : @sm : en", "      ed.list<1, -1> = ep : @sm : elen<k> : @sm : tb.raw")
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
