#!/usr/bin/env python3
"""test-tkbase-units.py - the toolkit's shared base, slice 1 (TK-0.1: the frame, the key table and the function-key row), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tkbase-units.py
  python3 .../test-tkbase-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 22 Oct 2026 (S.75, plan .claude/plan-fullscreen-toolkit.md sections 2.1, 2.2, 2.12).

WHAT IT HOLDS: the order of what `$tk_open` does (a phantom has no terminal; the size is asked of the library's one check, 140 by 43 by the owner's ruling of 20 Oct; the audience
is tested BEFORE the screen is opened and before any data is read; only then the screen is taken, with the cursor lock) and that every failure returns instead of going on; that
`$tk_close` gives back the break setting and the screen; that the frame is drawn from the layout and writes the status line only when its text changed; that the function-key row
shows only the keys the focused pane uses, from the app's one key table; that no raw escape sequence is written (the library's styles and line characters only); that the
throw-away test app ends when its input ends; and that every program is internal, catalogued under its own name, and cites only messages of the toolkit's block that exist.

***IT READS SOURCE AS TEXT AND RUNS NOTHING***: that the frame appears where it should and the keys do what the labels say is `sandbox-tk-base.py`'s job, on a pseudo-terminal.

--selftest runs every check on the real files and then on a copy with one deliberate fault at a time: each must make a check fail.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
BP = os.path.join(SDSYS, "gpl.bp")
NAMES = ["tk.h", "tk_open", "tk_close", "tk_frame", "tk_fkeys", "tk_keys", "tk_gate_info", "tk_run", "tk_gates", "tool_tktest"]
PROGRAMS = [n for n in NAMES if n != "tk.h"]


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def squeeze(t):
    return re.sub(r"\s+", " ", t).strip()


def ordered(text, *needles):
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def checks(raw):
    code = {n: strip_bas(raw[n]) for n in NAMES}
    sq = {n: squeeze(code[n]) for n in NAMES}
    out = []

    def add(i, what, ok, detail=""):
        out.append((i, what, bool(ok), detail))

    add("T0", "NULL CASE: every file of the base was found and none is trivially short (a check on nothing would pass)", all(len(raw[n]) > 300 for n in NAMES),
        ", ".join("%s %d" % (n, len(raw[n])) for n in NAMES))
    h = raw["tk.h"]
    add("T1", "tk.h fixes the minimum at 140 by 43 and names the chrome rows", re.search(r"\$define TK\.MINW\s+140\b", h) is not None and re.search(r"\$define TK\.MINH\s+43\b", h) is not None
        and "TK.C.YSTAT" in h and "TK.C.YBORD" in h and "TK.C.YKEYS" in h, "")
    op = sq["tk_open"]
    add("T2", "ORDER in $tk_open: a phantom is turned away, then the size is asked, then the audience, and only then the screen is taken, then the cursor lock",
        ordered(op, "system(25)", "call $sl_need(", "K$ADMINISTRATOR", "screen open", "call $sl_guardmode("), "")
    add("T3", "the size asked is TK.MINW by TK.MINH (never a number typed in the program) and so is the cursor lock's",
        "call $sl_need(app, TK.MINW, TK.MINH," in op and "call $sl_guardmode(app, TK.MINW, TK.MINH)" in op and not re.search(r"\b(140|42|43)\b", op), "")
    before = op.split("screen open", 1)[0]
    add("T4", "EVERY REFUSAL RETURNS before the screen is opened: the phantom, the size and the audience each set err and return",
        before.count("return") >= 3 and "err = " in before, "returns before screen open: %d" % before.count("return"))
    add("T5", "the audience test is asked of the kernel (K$ADMINISTRATOR, -1) and only for the administrator audience, before any data is read",
        re.search(r"audience = 'admin' then if not\(kernel\(K\$ADMINISTRATOR, -1\)\)", op) is not None, "")
    add("T6", "the break setting is saved before it is changed, and the screen is opened with line drawing only when the terminal says UTF-8",
        ordered(op, "pterm(PT$BREAK, -1)", "pterm(PT$BREAK, @false)", "screen open") and "screen open clear lines" in op and "UTF-8" in op, "")
    cl = sq["tk_close"]
    add("T7", "$tk_close gives the screen back, then the break setting it saved, then the break key", ordered(cl, "screen close", "pterm(PT$BREAK,", "break on"), "")
    fr = sq["tk_frame"]
    add("T8", "$tk_frame writes the status line in reverse video, only when its text changed since it was last written, and keeps the cursor where the widget left it",
        "attr 'reverse'" in fr and "if t = last.stat then" in fr and "call $sl_curat('get'" in fr and re.search(r"attr 'reverse' call \$sl_curat\('back'", fr) is not None, "")
    add("T9", "$tk_frame draws the border with the library's own line character ($sl_line 'h') and the function keys from $tk_fkeys, on rows the layout gives (never a literal row number)",
        "call $sl_line('h'," in fr and "call $tk_fkeys(" in fr and not re.search(r"\bat \d+,\d+\b", fr) and "TK.C.YKEYS" in fr and "TK.C.YBORD" in fr and "TK.C.YSTAT" in fr
        and "if ft # last.keys then" in fr and "if b # last.bord then" in fr
        and re.search(r"at 0,ybord call \$sl_curat\('back'", fr) is not None and re.search(r"at 0,ykeys attr 'bar' call \$sl_curat\('back'", fr) is not None, "")
    fk = sq["tk_fkeys"]
    add("T10", "the function-key row shows a key only if it is enabled and the focused pane uses it (a null pane list means every pane), in the order of the key table",
        "TK.K.PANES" in fk and "TK.K.ON" in fk and ("pane" in fk) and re.search(r"index\(@sm : .* : @sm, @sm : pane : @sm, 1\)", fk) is not None, "")
    ky = sq["tk_keys"]
    add("T11", "the key table has an add, a name and an action operation, and an action is looked up by key AND pane",
        all(("op = '%s'" % o) in ky for o in ("add", "name", "action")) and "TK.K.ACT" in ky and "pane" in ky, "")
    anycode = "\n".join(code[n] for n in PROGRAMS)
    add("T12", "no program writes a raw escape sequence or a cursor code: the library's styles and line characters only",
        "char(27)" not in anycode.lower() and "@(-" not in anycode and "\\x1b" not in anycode and "crt @(" not in anycode, "")
    app = sq["tool_tktest"]
    add("T13", "the test app's key loop treats the end of input as the end of the app (status() = ER$EOF is tested, never taken for an empty key) and leaves on the cursor lock's own way out",
        "ER$EOF" in app and "guardquit" in app and "call $tk_close(" in app, "")
    add("T14", "every program is internal and catalogued under its own name, and they are all different",
        all(re.search(r"^\$internal\b", raw[n], re.M) for n in PROGRAMS) and len({re.search(r"^\$catalog (\S+)", raw[n], re.M).group(1) for n in PROGRAMS if re.search(r"^\$catalog (\S+)", raw[n], re.M)}) == len(PROGRAMS)
        and all(re.search(r"^\$catalog \$%s\b" % n, raw[n], re.M) for n in PROGRAMS), "")
    cited = set()
    for n in PROGRAMS:
        cited |= set(int(x) for x in re.findall(r"sysmsg\((\d+)", code[n]))
    have = {int(f) for f in os.listdir(os.path.join(SDSYS, "messages")) if f.isdigit()}
    add("T15", "the messages the base cites (%s) are all in the toolkit's block 11800 to 11849 and all exist" % sorted(cited), bool(cited) and all(11800 <= m <= 11849 and m in have for m in cited), sorted(m for m in cited if m not in have))
    rn = sq["tk_run"]
    add("T16", "ORDER in $tk_run: an empty sentence, a too long one, a first word outside the tool's list and a bad character are each refused (and return) BEFORE the one EXECUTE",
        ordered(rn, "sysmsg(11804)", "sysmsg(11807)", "if not(ok.verb) then err = sysmsg(11805, verb)", "if index(good, w[j, 1], 1) = 0 then err = sysmsg(11806, w)",
                "execute s trapping aborts capturing out")
        and all(re.search(r"err = sysmsg\(%d[^)]*\) return" % m, rn) for m in (11804, 11805, 11806, 11807)), "")
    add("T17", "$tk_run runs only the sentence it checked (s), traps aborts, hands back the return code, and writes no audit line and no screen text",
        rn.count("execute ") == 1 and "execute sentence" not in rn and "status = @system.return.code" in rn and "K$AUDIT" not in rn and not re.search(r"\b(crt|display|print|screen)\b", rn), "")
    add("T18", "$tk_run allows exactly a-z, 0-9, dot, dash and underscore in a word, and the first word is compared whole against the tool's list, in lower case as typed",
        "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-'" in rn and "field(allow, ' ', i) = verb and verb # ''" in rn, "")
    gi = sq["tk_gate_info"]
    gi_code = re.sub(r'rows<-1> = "[^"]*"', "rows<-1> = ROW", gi)          # the rows are prose: the words of a sentence are not statements
    add("T19", "$tk_gate_info answers a list and one gate at a time from its rows, writes nothing and changes no state",
        "id = 'list' then" in gi and "convert('|', @fm, rows<i>)" in gi and gi_code.count("rows<-1> = ROW") >= 10
        and not re.search(r"\b(crt|display|print|screen|write|writev|kernel|execute)\b", gi_code), "")
    tg = sq["tk_gates"]
    add("T20", "ORDER in $tk_gates: the administrator is asked of the kernel (and refused with 11800) BEFORE the name is looked at, before the register is opened and before it is read; each refusal returns",
        ordered(tg, "if not(kernel(K$ADMINISTRATOR, -1)) then err = sysmsg(11800, 'tk_gates') return", "sysmsg(11808, name) return", "if index(good, name[j, 1], 1) = 0 then err = sysmsg(11808, name) return",
                "openpath @sdsys:@ds:'accounts' to acc.f else err = sysmsg(11809) return", "read rec from acc.f, name else", "call $tk_gate_info('list', ids)"), "")
    add("T21", "$tk_gates only READS the register (no write, delete, lock or command), closes it on both paths, and puts nothing on the screen",
        not re.search(r"\b(write|writev|writeu|writet|delete|readu|execute|crt|display|print|screen|os\.execute)\b", re.sub(r"'[^']*'", "''", tg)) and tg.count("close acc.f") == 2, "")
    add("T22", "$tk_gates: a gate with its default on (shared-read) is on unless the field says no, every other register gate only if it says yes, and a route gate on an account with no person is 'na' (never a membership test of nobody)",
        "if gi<TK.G.DEFAULT> = 'on' then state = (if raw # 'NO' then 1 else 0) end else state = (if raw = 'YES' then 1 else 0) end" in tg
        and "if atype = 'USER' then state = (if is_grp_member(user, gi<TK.G.GROUP>) then 1 else 0) end else state = 'na' end" in tg, "")
    return out


def load():
    raw = {}
    for n in NAMES:
        p = os.path.join(BP, n)
        if not os.path.isfile(p):
            raise FileNotFoundError(p)
        with open(p, encoding="latin-1") as f:
            raw[n] = f.read()
    return raw


def run(raw, quiet=False):
    rows = checks(raw)
    bad = [r for r in rows if not r[2]]
    if not quiet:
        for i, what, ok, detail in rows:
            print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, ("   <- " + str(detail)) if (detail and not ok) else ""))
    return rows, bad


MUT = [
    ("tk_open", "the audience is tested after the screen is taken", "audience = 'admin' then", "audience = 'admin' and 0 then"),
    ("tk_open", "a refusal does not return", "err = sysmsg(11801, app)\n      return", "err = sysmsg(11801, app)"),
    ("tk_open", "the size is typed into the program", "call $sl_need(app, TK.MINW, TK.MINH,", "call $sl_need(app, 140, 42,"),
    ("tk_open", "the cursor lock is not asked for", "call $sl_guardmode(app, TK.MINW, TK.MINH)", "null"),
    ("tk_open", "the break setting is changed before it is saved", "saved.trap = pterm(PT$BREAK, -1)", "saved.trap = 1"),
    ("tk_close", "the break setting is not given back", "void pterm(PT$BREAK, ctx<TK.C.TRAP>)", "null"),
    ("tk_frame", "the status line is written every time", "if t = last.stat then", "if 0 then"),
    ("tk_frame", "the status line moves the cursor", "screen text t at 0,ystat attr 'reverse'\n      call $sl_curat('back', keep.cur)", "screen text t at 0,ystat attr 'reverse'"),
    ("tk_frame", "the function keys are redrawn on every call", "if ft # last.keys then", "if 1 then"),
    ("tk_frame", "the status line is not reverse video", "screen text t at 0,ystat attr 'reverse'", "screen text t at 0,ystat"),
    ("tk_frame", "the border is a typed character", "call $sl_line('h', 0, hc)", "hc = '-'"),
    ("tk_fkeys", "a key is shown on every pane", "index(@sm : panes : @sm, @sm : pane : @sm, 1)", "1"),
    ("tk_keys", "an action is looked up by key alone", "op = 'action'", "op = 'actionx'"),
    ("tool_tktest", "end of input is taken for an empty key", "ER$EOF", "ER$XXX"),
    ("tk_open", "an escape sequence is written", "screen open clear lines", "crt char(27) : '[2J' ; screen open clear lines"),
    ("tk_run", "the tool's list is not asked", "if not(ok.verb) then", "if 0 then"),
    ("tk_run", "the characters of a word are not checked", "if index(good, w[j, 1], 1) = 0 then", "if 0 then"),
    ("tk_run", "the raw sentence is run, not the checked one", "execute s trapping aborts capturing out", "execute sentence trapping aborts capturing out"),
    ("tk_run", "aborts are not trapped", "execute s trapping aborts capturing out", "execute s capturing out"),
    ("tk_run", "a refused sentence does not return", "err = sysmsg(11805, verb)\n      return", "err = sysmsg(11805, verb)"),
    ("tk_run", "an extra character is allowed (the semicolon)", "0123456789._-'", "0123456789._-;'"),
    ("tk_run", "the first word is matched as a prefix", "field(allow, ' ', i) = verb and verb # ''", "field(allow, ' ', i)[1, len(verb)] = verb"),
    ("tk_gates", "the administrator is not asked", "if not(kernel(K$ADMINISTRATOR, -1)) then", "if 0 then"),
    ("tk_gates", "the administrator refusal does not return", "err = sysmsg(11800, 'tk_gates')\n      return", "err = sysmsg(11800, 'tk_gates')"),
    ("tk_gates", "the name is not checked", "if index(good, name[j, 1], 1) = 0 then", "if 0 then"),
    ("tk_gates", "a missing account leaves the register open", "      close acc.f\n      err = sysmsg(11808, name)", "      err = sysmsg(11808, name)"),
    ("tk_gates", "shared-read needs the word yes like the rest", "state = (if raw # 'NO' then 1 else 0)", "state = (if raw = 'YES' then 1 else 0)"),
    ("tk_gates", "every gate is on unless the field says no", "state = (if raw = 'YES' then 1 else 0)\n            end", "state = (if raw # 'NO' then 1 else 0)\n            end"),
    ("tk_gates", "a route is looked up for an account with no person", "if atype = 'USER' then", "if 1 then"),
    ("tk_gates", "the register is written", "   close acc.f\n\n   grp = rec<ACC$GROUP>", "   close acc.f\n   write rec to acc.f, name\n\n   grp = rec<ACC$GROUP>"),
    ("tk_gate_info", "the table is written to the screen","   if id = 'list' then", "   crt 'x'\n   if id = 'list' then"),
]


def selftest():
    try:
        raw = load()
    except FileNotFoundError as e:
        print("CANNOT RUN: %s is not there" % e)
        return 2
    rows, bad = run(raw)
    if bad:
        print("selftest: the real files already fail %d check(s)" % len(bad))
        return 1
    killed, missed = 0, []
    for fname, what, old, new in MUT:
        if raw[fname].count(old) != 1:
            print("  [CANNOT] %s: the text to change is found %d times in %s, not once" % (what, raw[fname].count(old), fname))
            return 2
        m = dict(raw)
        m[fname] = raw[fname].replace(old, new)
        rows_m, bad_m = run(m, quiet=True)
        if bad_m:
            killed += 1
            print("  [killed] %s  <- %s" % (what, ", ".join(r[0] for r in bad_m)))
        else:
            missed.append(what)
            print("  [MISSED] %s" % what)
    print("selftest: %d mutants, %d killed, %d missed" % (len(MUT), killed, len(missed)))
    return 0 if not missed else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        raw = load()
    except FileNotFoundError as e:
        print("CANNOT RUN: %s is not there" % e)
        return 2
    rows, bad = run(raw)
    print("test-tkbase-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
