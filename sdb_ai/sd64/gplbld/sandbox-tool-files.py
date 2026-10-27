#!/usr/bin/env python3
#
# sandbox-tool-files.py - TOOL.FILES, the files of the account on one screen ($tool_files, S.75 DV1), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-files.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand: zzfl1 with the edit gates (voc, bp, dict) ON and zzfl2 with them OFF.  In zzfl1, files made by an
# ordinary session: zzfa (a dynamic file of five records), zzfb (a dynamic file of four records with an index AMT), zzfd (a directory file) and &zzq& (a name the page does not give
# to a command).  An ORDINARY session (sd -a<account>, as the sandbox user, not an administrator) types TOOL.FILES.
#
# THE INSTRUMENT.  Every outcome is read from the DISK or from SD, not from what the page said: whether a file's directory exists, how many records a separate session counts in it,
# and the page's own list is compared with both.  A row that says "nothing was made / cleared / deleted" is judged by the same.
#
#   F1      the page draws for an ordinary account, for its audience; the list holds the fixture files in name order with the right kind, records, indices
#   F2      the file under the cursor in words (path, records, indices); the filter; the gates line for an account with the edit gates on and one with them off
#   F3      the reports: A (analyze.file), I (list.index: the index AMT), T (list.triggers) - the terminal is handed to the verb (they print through the print unit, which
#           EXECUTE ... CAPTURING does not catch), "Press Enter" waits, Enter brings the page back with the cursor where it was
#   F4      N makes a file: Cancel is the default (nothing made), Run makes it (the directory is on the disk, the row is in the list), a name with a capital is refused
#   F5      C clears: the wrong name typed clears nothing; the right name empties the file (a separate session counts 0) and the row says so
#   F6      D deletes: Cancel is the default; the typed name deletes the file (gone from the disk and the list)
#   F7      a name the page does not give to a command (&zzq&): C and D are refused with the reason and the file is intact
#   F8      an account with the edit gates off: N still makes a file (a new pointer is not held back), C on the program file bp is the verb's own refusal and the record in it stays
#   F9      F1 and the [?] reach the help box; a window under 140 by 43 gets no page
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_files", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zzfl1", "zzfl2"
ME = os.environ.get("USER") or os.getlogin()


SCREEN = [None]      # the pty session of the section running: a failed row prints what it was looking at


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


MUTANTS = {
    # name: (old text of the sandbox's tool_files, new text, the row ids that must fail and no others)
    "clear-no-typed-name": ("call $tk_confirm(sent, lines, fn, res, cmsg)\n   if res # 'run' then\n      msg = cmsg\n      return\n   end\n   gosub run.sent\n   gosub read.all\n   gosub draw.all\n   return\n\ndo.delete:",
                            "call $tk_confirm(sent, lines, '', res, cmsg)\n   if res # 'run' then\n      msg = cmsg\n      return\n   end\n   gosub run.sent\n   gosub read.all\n   gosub draw.all\n   return\n\ndo.delete:", ["F5"]),
    "analyse-clears": ("         sent = 'analyze.file ' : shown<ci>", "         sent = 'clear.file ' : shown<ci>", ["F3"]),
}


def box():
    return sh.BOX


def acct_dir(a):
    return os.path.join(box(), "user_accounts", a)


def reg_record(name, edit):
    e = "yes" if edit else "no"
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", e, e, e, "", "", "no", "", "", ""]


def compile_page():
    out = adm("BASIC gpl.bp tool_files")
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_files did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def mutate(name):
    old, new, _kills = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_files")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    compile_page()


def count_records(account, fname):
    """how many records a SEPARATE ordinary session counts in the file: the evidence for clear"""
    g.put(os.path.join(acct_dir(account), "bp", "zzfcnt"), "\n".join([
        "   open '%s' to f else crt 'CNT[nofile]' ; stop" % fname,
        "   select f to 9",
        "   n = 0",
        "   loop",
        "      readnext id from 9 else exit",
        "      n += 1",
        "   repeat",
        "   crt 'CNT[':n:']'", "end", ""]))
    out = g.plain(account, ["BASIC bp zzfcnt", "RUN bp zzfcnt"])
    for ln in out:
        m = re.match(r"^CNT\[(.*)\]$", ln.strip())
        if m:
            return m.group(1)
    return None


def setup_files():
    q = sh.g
    for a, edit in ((A1, True), (A2, False)):
        q.FIXTURES[a] = ("no", "no")
        q.build_account(a)
        q.reg_write(a, reg_record(a, edit))
    compile_page()
    q.put(os.path.join(acct_dir(A1), "bp", "zzfw"), "\n".join([
        "   open 'zzfa' to f else crt 'ZZFW no zzfa' ; stop",
        "   for i = 1 to 5",
        "      write 'record ':i on f, 'r':i",
        "   next i",
        "   open 'DICT zzfb' to d else crt 'ZZFW no dict' ; stop",
        "   write 'D':@fm:'1':@fm:'':@fm:'Amt':@fm:'10R':@fm:'S' on d, 'AMT'",
        "   open 'zzfb' to f2 else crt 'ZZFW no zzfb' ; stop",
        "   write '10' on f2, 'a'",
        "   write '20' on f2, 'b'",
        "   write '30' on f2, 'c'",
        "   write '5' on f2, 'd'",
        "   crt 'ZZFW done'", "end", ""]))
    out = q.plain(A1, ["CREATE.FILE zzfa", "CREATE.FILE zzfb", "CREATE.FILE zzfd directory", "CREATE.FILE &zzq&", "BASIC bp zzfw", "RUN bp zzfw", "CREATE.INDEX zzfb AMT", "BUILD.INDEX zzfb AMT"])
    if not has(out, r"^ZZFW done$"):
        bail("the fixture files were not made:\n" + "\n".join(out[-12:]))
    n = count_records(A1, "zzfa")
    if n != "5":
        bail("the fixture file zzfa holds %s records, not 5" % n)
    if count_records(A1, "zzfb") != "4":
        bail("the fixture file zzfb does not hold 4 records")


def page(account, cols=140, rows=43):
    h = H(account=account, cols=cols, rows=rows)
    SCREEN[0] = h
    h.typed("tool.files\r", idle=3.5)
    return h


def table(h):
    """{name: (kind, records, modulus, bytes, idx, trigger, case, dict, open)} from the rows of the first box."""
    out = {}
    order = []
    for n in range(3, 19):
        l = h.line(n)
        name = l[3:33].strip()
        if name:
            order.append(name)
            out[name] = (l[33:44].strip(), l[44:54].strip(), l[56:64].strip(), l[66:78].strip(), l[80:84].strip(), l[86:95].strip(), l[95:101].strip(), l[101:106].strip(), l[106:112].strip())
    return out, order


def lower(h):
    return [h.line(n)[3:138].rstrip() for n in range(24, 39)]


def st(h):
    return h.line(40)


def on_disk(account, fname):
    return os.path.exists(os.path.join(acct_dir(account), fname))


def filt(h, text):
    h.typed("/", idle=0.8)
    h.typed(text + "\r", idle=1.0)


def until(h, pred, secs=20.0):
    """a verb that the page runs prints nothing while it runs, so a wait for idle output is not a wait for the page: pump the pty until the screen satisfies pred"""
    for _ in range(int(secs / 0.5)):
        if pred(h.text()):
            return True
        h.s._pump(0.5)
    return pred(h.text())


def section_list():
    say("\n--- F1 and F2: the list, the file under the cursor, the filter, the gates")
    h = page(A1)
    T = h.text()
    if "The file under the cursor" not in T:
        dump(h)
        bail("tool.files never drew its page in an ordinary account, so no row below can be believed")
    tb, order = table(h)
    arow("F1", "the page draws for an ordinary account, for the audience %s@%s (the right end of row 0), and writes no audit line of its own" % (ME, A1),
         re.search(r"tool\.files\s+%s@%s" % (re.escape(ME), A1), h.line(0)) is not None and "Files in %s" % A1 in T, repr(h.line(0)[100:]))
    arow("F1b", "the fixture files are in the list, in name order, as the right kind: zzfa and zzfb dynamic, zzfd a directory, &zzq& dynamic",
         all(n in tb for n in ("zzfa", "zzfb", "zzfd", "&zzq&")) and order == sorted(order) and tb["zzfa"][0] == "dynamic" and tb["zzfb"][0] == "dynamic" and tb["zzfd"][0] == "directory" and tb["&zzq&"][0] == "dynamic", repr((order, tb.get("zzfd"))))
    arow("F1c", "...zzfa says 5 records and no index, zzfb says 4 records and one index, both have a dictionary and ids that ignore case ('any')",
         tb["zzfa"][1] == "5" and tb["zzfa"][4] == "0" and tb["zzfb"][1] == "4" and tb["zzfb"][4] == "1" and tb["zzfa"][7] == "yes" and tb["zzfb"][7] == "yes" and tb["zzfa"][6] == "any", repr((tb["zzfa"], tb["zzfb"])))
    filt(h, "zzfa")
    tb, order = table(h)
    B = lower(h)
    arow("F2", "the filter / keeps the names that hold the text: only zzfa is left, and the box under the list describes it - its path in this account, about 5 records, no indices, no trigger",
         order == ["zzfa"] and "zzfa  -  a dynamic file at" in B[0] and (acct_dir(A1) + "/zzfa") in B[0] and any("About 5 records" in x for x in B) and any("No indices" in x for x in B) and any("No trigger" in x for x in B), repr((order, B[:4])))
    h.key("esc", idle=1.0)
    tb, order = table(h)
    arow("F2b", "Esc clears the filter: every file is back", "zzfb" in order and "zzfd" in order and len(order) >= 4, repr(order))
    filt(h, "zzfb")
    B = lower(h)
    arow("F2c", "zzfb's box names its index: 'Indices: AMT'", any("Indices: AMT" in x for x in B), repr(B[:6]))
    h.key("esc", idle=1.0)
    L = h.line(19)[3:138]
    arow("F2d", "the gates line, asked of the kernel, for an account with the edit gates ON", "voc-edit on" in L and "dict-edit on" in L and "bp-edit on" in L, repr(L))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2)
    L = h.line(19)[3:138]
    arow("F2e", "...and for an account with them OFF: all three say off", "voc-edit off" in L and "dict-edit off" in L and "bp-edit off" in L, repr(L))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_reports():
    say("\n--- F3: the reports")
    h = page(A1)
    filt(h, "zzfb")
    h.typed("i", idle=1.0)
    until(h, lambda t: "Press Enter" in t)
    T = h.text()
    arow("F3a", "I on zzfb hands the terminal to list.index: its printout names the index AMT, the page's boxes are gone and the verb waits for Enter", "AMT" in T and "Press Enter" in T and "The file under the cursor" not in T, T[-600:])
    h.key("enter", idle=1.5)
    until(h, lambda t: "The file under the cursor" in t)
    tb, order = table(h)
    arow("F3b", "Enter brings the page back: the files are read again, the cursor is still on zzfb (the filter is kept) and the status line says it is back from list.index zzfb", "The file under the cursor" in h.text() and order == ["zzfb"] and "back from list.index zzfb" in st(h), repr((order, st(h))))
    h.typed("t", idle=1.0)
    until(h, lambda t: "Press Enter" in t)
    T = h.text()
    arow("F3c", "T on zzfb hands the terminal to list.triggers: the page's boxes are gone and the verb waits for Enter; Enter brings the page back", "Press Enter" in T and "The file under the cursor" not in T, T[-600:])
    h.key("enter", idle=1.5)
    until(h, lambda t: "The file under the cursor" in t)
    arow("F3c2", "...and the status line says it is back from list.triggers zzfb", "back from list.triggers zzfb" in st(h), repr(st(h)))
    filt(h, "zzfa")
    h.typed("a", idle=1.0)
    until(h, lambda t: "Press Enter" in t)
    T = h.text()
    arow("F3d", "A on zzfa hands the terminal to analyze.file: the page's boxes are gone, the verb waits for Enter, and the file still holds its 5 records after", "Press Enter" in T and "The file under the cursor" not in T and count_records(A1, "zzfa") == "5", T[-600:])
    h.key("enter", idle=1.5)
    until(h, lambda t: "The file under the cursor" in t)
    arow("F3e", "...Enter brings the page back, from analyze.file zzfa", "back from analyze.file zzfa" in st(h), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_new():
    say("\n--- F4: N makes a file")
    h = page(A1)
    h.typed("n", idle=1.0)
    h.typed("zzfn\r", idle=1.0)
    h.typed("d", idle=1.5)
    T = h.text()
    arow("F4a", "N asks for a name, then dynamic or directory, then shows the exact command in a box with Run and Cancel, and says what it does", "create.file zzfn" in re.sub(r"[|\s]+", " ", T) and "Run" in T and "Cancel" in T, T[-500:])
    h.key("enter", idle=1.5)
    tb, order = table(h)
    arow("F4b", "Enter is Cancel: nothing is made - no directory on the disk, no row in the list", not on_disk(A1, "zzfn") and "zzfn" not in order, repr((on_disk(A1, "zzfn"), order)))
    h.typed("n", idle=1.0)
    h.typed("zzfn\r", idle=1.0)
    h.typed("d", idle=1.5)
    h.typed("r", idle=3.0)
    tb, order = table(h)
    arow("F4c", "Run makes the file: the directory is on the disk, the page lists it as a dynamic file of 0 records with the cursor on it", on_disk(A1, "zzfn") and tb.get("zzfn", ("",))[0] == "dynamic" and tb["zzfn"][1] in ("0", ""), repr((on_disk(A1, "zzfn"), tb.get("zzfn"))))
    h.typed("n", idle=1.0)
    h.typed("ZZBig\r", idle=1.5)
    arow("F4d", "a name with a capital is refused before any box (the page gives a command only letters a-z, digits, dot, dash and underscore)", "letters a-z" in st(h) and not on_disk(A1, "ZZBig") and not on_disk(A1, "zzbig"), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_clear():
    say("\n--- F5: C clears")
    h = page(A1)
    filt(h, "zzfa")
    h.typed("c", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("wrong\r", idle=2.0)
    arow("F5a", "C, Run, and the wrong name typed: nothing is cleared (a separate session still counts 5 records) and the status line says which name was asked for", count_records(A1, "zzfa") == "5" and "zzfa" in st(h), repr((count_records(A1, "zzfa"), st(h))))
    h.typed("c", idle=1.2)
    h.key("enter", idle=1.5)
    arow("F5b", "C and Enter (Cancel is the default): nothing is cleared", count_records(A1, "zzfa") == "5", repr(count_records(A1, "zzfa")))
    h.typed("c", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("zzfa\r", idle=3.0)
    tb, order = table(h)
    arow("F5", "C, Run, and the right name typed: clear.file ran - a separate session counts 0 records, the file is still there, and the page's row says 0", count_records(A1, "zzfa") == "0" and on_disk(A1, "zzfa") and tb["zzfa"][1] in ("0", ""), repr((count_records(A1, "zzfa"), tb.get("zzfa"))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_delete():
    say("\n--- F6: D deletes")
    h = page(A1)
    filt(h, "zzfn")
    h.typed("d", idle=1.2)
    h.key("enter", idle=1.5)
    arow("F6a", "D and Enter (Cancel is the default): the file is still on the disk and in the list", on_disk(A1, "zzfn") and "zzfn" in table(h)[1], repr((on_disk(A1, "zzfn"), table(h)[1])))
    h.typed("d", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("zzfn\r", idle=3.0)
    h.key("esc", idle=1.0)
    tb, order = table(h)
    arow("F6", "D, Run and the right name: the file's directory is gone from the disk and the list no longer has it", not on_disk(A1, "zzfn") and "zzfn" not in order, repr((on_disk(A1, "zzfn"), order)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_odd():
    say("\n--- F7: a name the page does not give to a command")
    h = page(A1)
    filt(h, "zzq")
    tb, order = table(h)
    h.typed("c", idle=1.5)
    S1 = st(h)
    h.typed("d", idle=1.5)
    S2 = st(h)
    arow("F7", "&zzq& is listed; C and D say the name has a character the page does not give to a command and show the verb to type, and no box opens; the file is intact",
         order == ["&zzq&"] and "does not give to a command" in S1 and "clear.file" in S1 and "delete.file" in S2 and on_disk(A1, "&zzq&") and "Run" not in h.text(), repr((order, S1, S2)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def boxtext(h):
    """the words inside the confirm box on the screen, one line, its wrapped lines joined (the page behind the box is left out: it shows through at the sides); the whole screen when there is no box"""
    rows = [h.line(n) for n in range(43)]
    top = next((n for n, l in enumerate(rows) if "Run this command?" in l), None)
    if top is None:
        return re.sub(r"[|\s]+", " ", h.text())
    s0, s1 = rows[top].index("+"), rows[top].rindex("+")
    inner = []
    for n in range(top + 1, 43):
        if rows[n][s0:s0 + 1] == "+":
            break
        inner.append(rows[n][s0 + 1:s1])
    return re.sub(r"[|\s]+", " ", " ".join(inner))


def section_refused():
    say("\n--- F8: an account whose edit gates are off")
    sentinel = os.path.join(acct_dir(A2), "bp", "zzsent")
    g.put(sentinel, "a record in the program file\n")
    h = page(A2)
    h.typed("n", idle=1.0)
    h.typed("zzfx\r", idle=1.0)
    h.typed("d", idle=1.5)
    T = boxtext(h)
    arow("F8a", "the box for N does not claim a gate stops it (making a new file is not held back by the edit gates) and says so", "Making a new file is not held back by the edit gates" in T and "expect a refusal" not in T, T[-500:])
    h.typed("r", idle=3.0)
    until(h, lambda t: "zzfx" in "\n".join(table(h)[1]))
    tb, order = table(h)
    arow("F8", "Run: the file IS made for an account with every edit gate off - the disk has it and the list shows it (what the Administrator's guide says: a new pointer is a side effect, not held)", on_disk(A2, "zzfx") and "zzfx" in order, repr((on_disk(A2, "zzfx"), order)))
    filt(h, "bp")
    tb, order = table(h)
    h.typed("c", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("bp\r", idle=1.0)
    until(h, lambda t: st(h).strip() != "" and "nothing was run" not in st(h))
    S = st(h)
    arow("F8b", "C on the PROGRAM file bp, Run, the name typed: the verb refuses (bp-edit is off for the account) and says so on the status line, and the record in the file is still on the disk",
         "bp" in order and os.path.exists(sentinel) and S.strip() != "", repr((order, S, os.path.exists(sentinel))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_other():
    say("\n--- F9: help and a small window")
    h = page(A1)
    arow("F9a", "a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    h.click(135, 2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("F9b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("F9c", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    h.typed("tool.files\r", idle=3.0)
    T = h.text()
    arow("F9d", "a window under 140 by 43 gets no page", "The file under the cursor" not in T and "Files in" not in T, T[-300:])
    h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-files.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    try:
        sh.setup("sandbox-tool-files.py")
        setup_files()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-files: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_list()
        if mutant in (None, "analyse-clears"):
            section_reports()
        if mutant is None:
            section_new()
        if mutant in (None, "clear-no-typed-name"):
            section_clear()
        if mutant is None:
            section_delete()
            section_odd()
            section_refused()
            section_other()
    finally:
        sh.teardown()
    say("\nsandbox-tool-files: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"F\d+", i).group(0) for i in FAILED_IDS if re.match(r"F\d+", i)})
        ok = want == got
        say("sandbox-tool-files: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
