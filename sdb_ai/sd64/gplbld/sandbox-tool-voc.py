#!/usr/bin/env python3
#
# sandbox-tool-voc.py - TOOL.VOC, the VOC of the account on one screen ($tool_voc, S.75 DV3), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-voc.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand: zzvl1 with the edit gates (voc, bp, dict) ON and zzvl2 with them OFF.  In zzvl1 an ordinary program
# writes VOC entries: a verb zzverb, a paragraph zzpara, a stored sentence zzsent, a file pointer zzfile to a real file, a file pointer zzgone to a file that is not there, a Q-pointer
# zzqbad to an account that is not there, and bell changed from the shipped record.  An ORDINARY session (sd -a<account>, not an administrator) types TOOL.VOC.
#
# THE INSTRUMENT.  Every outcome is read from SD, not from what the page said: a SEPARATE ordinary session runs a program that reads the VOC record, and the page's own list is compared
# with it.  A row that says "nothing was deleted" is judged by the same.
#
#   V1      the page draws for an ordinary account, for its audience; the foot counts the entries the VOC holds (a separate session counts them)
#   V2      the fixture entries are listed with the right type, the right "points at", the right Works and the right state against the shipped VOC (added / changed / same)
#   V3      the entry under the cursor is shown field by field
#   V4      T chooses a type (verbs, files, pointers, paragraphs and sentences), S a state (differ from the shipped VOC, broken pointers), / filters by a part of the id, Esc clears all
#   V5      D deletes: Cancel is the default; the wrong id typed deletes nothing; the right id deletes the record (a separate session reads it) and the list no longer has it
#   V6      E hands the terminal to SED on the entry and the page comes back
#   V7      an account with voc-edit OFF: the box says so, the kernel refuses the delete, the entry is still there
#   V8      F1 and the [?] reach the help box; a window under 140 by 43 gets no page
#   (28 Oct 26)
#   V9      S4 (S.88 phase 2): D on an entry the VOC holds as a KEYWORD (type K: all) is refused by the page - $tk_word - before any box, so "delete voc all" is never offered (its question,
#           "Delete all records in VOC?", would go to output the page captures and a y would empty the VOC); the VOC is read from a separate session, unchanged.  WRITTEN, NOT RUN (28 Oct 26:
#           the owner ruled that no suite runs until all the phases are in).  Runtime mutant: keyword-unchecked (V9).
import importlib.util
import os
import re
import shutil
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


sh = _load("sandbox_home_for_voc", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zzvl1", "zzvl2"
SCREEN = [None]


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


MUTANTS = {
    # name: (old text of the sandbox's tool_voc, new text, the row ids that must fail and no others)
    "delete-no-typed-name": ("call $tk_confirm(sent, lines, vid, res, cmsg)", "call $tk_confirm(sent, lines, '', res, cmsg)", ["V5"]),
    "all-same": ("edif = (if sr = r then 'same' else 'changed')", "edif = 'same'", ["V2", "V4"]),
    "keyword-unchecked": ("   call $tk_word(vid, kwok, kwwhy)\n", "   kwok = 1\n", ["V9"]),           # 28 Oct 26 (S.88 phase 2, S4)
}
MUTANT_SECTIONS = {"delete-no-typed-name": ("delete",), "all-same": ("list", "filters"), "keyword-unchecked": ("keyword",)}


def box():
    return sh.BOX


def acct_dir(a):
    return os.path.join(box(), "user_accounts", a)


def reg_record(name, edit):
    e = "yes" if edit else "no"
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", e, e, e, "", "", "no", "", "", ""]


def sync_tree():
    # 28 Oct 26 (S.88 phase 2, S4): the page calls $tk_word and prints message 11755; a sandbox built before they were written has neither, so the tree's copies go in first (and a mutant of
    # an earlier run is undone).  Not part of compile_page(): a mutant is compiled by it and must keep its change.
    for rel in ("gpl.bp/tool_voc", "gpl.bp/tk_word", "messages/11755", "messages/11806"):
        shutil.copyfile(os.path.join(TREE, "sdsys", rel), os.path.join(sh.SYS, rel))


def compile_page():
    out = adm("BASIC gpl.bp tk_word tool_voc")
    if not has(out, r"^Compiled 2 program\(s\) with no errors"):
        bail("tool_voc and tk_word did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def mutate(name):
    old, new, _kills = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_voc")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    compile_page()


def until(h, pred, secs=20.0):
    """a verb or an editor the page runs prints nothing while it runs: poll the pty until the screen satisfies pred"""
    for _ in range(int(secs / 0.5)):
        if pred(h.text()):
            return True
        h.s._pump(0.5)
    return pred(h.text())


def vocinfo(account, vid):
    """the VOC record of vid as a SEPARATE ordinary session reads it: None when there is none, else the fields"""
    g.put(os.path.join(acct_dir(account), "bp", "zzvx"), "\n".join([
        "   open 'VOC' to v else crt 'VX[novoc]' ; stop",
        "   read r from v, '%s' then" % vid,
        "      crt 'VX[1|':change(r, @fm, '|'):']'",
        "   end else",
        "      crt 'VX[0]'",
        "   end", "end", ""]))
    out = g.plain(account, ["BASIC bp zzvx", "RUN bp zzvx"])
    for ln in out:
        m = re.match(r"^VX\[(.*)\]$", ln.strip())
        if m:
            return None if m.group(1) == "0" else m.group(1)[2:].split("|")
    return "ERROR"


def voccount(account):
    g.put(os.path.join(acct_dir(account), "bp", "zzvn"), "\n".join([
        "   open 'VOC' to v else crt 'VN[novoc]' ; stop",
        "   select v to 9", "   n = 0", "   loop", "      readnext id from 9 else exit", "      n += 1", "   repeat",
        "   crt 'VN[':n:']'", "end", ""]))
    out = g.plain(account, ["BASIC bp zzvn", "RUN bp zzvn"])
    for ln in out:
        m = re.match(r"^VN\[(\d+)\]$", ln.strip())
        if m:
            return int(m.group(1))
    return None


def setup_voc():
    for a, edit in ((A1, True), (A2, False)):
        g.FIXTURES[a] = ("no", "no")
        g.build_account(a)
        g.reg_write(a, reg_record(a, edit))
    sync_tree()
    compile_page()
    g.put(os.path.join(acct_dir(A1), "bp", "zzvw"), "\n".join([
        "   open 'VOC' to v else crt 'VW no voc' ; stop",
        "   write 'V':@fm:'CA':@fm:'zzverbprog' on v, 'zzverb'",
        "   write 'PA':@fm:'display hello':@fm:'display second line' on v, 'zzpara'",
        "   write 'S':@fm:'list voc' on v, 'zzsent'",
        "   write 'F':@fm:'zzfile':@fm:'' on v, 'zzfile'",
        "   write 'F':@fm:'zznosuch':@fm:'zznosuch.dic' on v, 'zzgone'",
        "   write 'Q':@fm:'zznoaccount':@fm:'somefile' on v, 'zzqbad'",
        "   read r from v, 'bell' then",
        "      r<1> = r<1>:' changed in this account'",
        "      write r on v, 'bell'",
        "   end",
        "   crt 'VW done'", "end", ""]))
    out = g.plain(A1, ["CREATE.FILE zzfile", "BASIC bp zzvw", "RUN bp zzvw"])
    if not has(out, r"^VW done$"):
        bail("the fixture VOC entries were not written:\n" + "\n".join(out[-12:]))
    for vid in ("zzverb", "zzpara", "zzsent", "zzfile", "zzgone", "zzqbad", "bell"):
        if vocinfo(A1, vid) in (None, "ERROR"):
            bail("the fixture entry %s is not in the VOC" % vid)


def page(account, cols=140, rows=43):
    h = H(account=account, cols=cols, rows=rows)
    SCREEN[0] = h
    h.typed("tool.voc\r", idle=3.5)
    return h


def table(h):
    """{id: (type, points at, works, state)} and the order, from the rows of the first box."""
    out = {}
    order = []
    for n in range(3, 19):
        l = h.line(n)
        name = l[3:31].strip()
        if name:
            order.append(name)
            out[name] = (l[31:37].strip(), l[37:95].strip(), l[95:102].strip(), l[102:135].strip())
    return out, order


def lower(h):
    return [h.line(n)[3:138].rstrip() for n in range(24, 39)]


def st(h):
    return h.line(40)


def filt(h, text):
    h.typed("/", idle=0.8)
    h.typed(text + "\r", idle=1.0)


def section_list():
    say("\n--- V1 and V2: the list")
    h = page(A1)
    T = h.text()
    if "The entry under the cursor" not in T:
        dump(h)
        bail("tool.voc never drew its page in an ordinary account, so no row below can be believed")
    n = voccount(A1)
    m = re.search(r"(\d+) entries, (\d+) shown", h.line(19))
    arow("V1", "the page draws for an ordinary account (audience %s@%s at the right end of row 0) and the foot counts the entries the VOC holds: %s by a separate session" % (sh.ME if hasattr(sh, "ME") else "?", A1, n),
         re.search(r"tool\.voc\s+\S+@%s" % A1, h.line(0)) is not None and m is not None and int(m.group(1)) == n and int(m.group(2)) == n, repr((h.line(0)[100:], h.line(19)[:80], n)))
    filt(h, "zz")
    tb, order = table(h)
    arow("V2", "the fixture entries are listed in id order with the right type, target and Works: zzverb V, zzpara PA, zzsent S, zzfile F that works, zzgone F that does not, zzqbad Q that does not",
         order == sorted(order) and {"zzverb", "zzpara", "zzsent", "zzfile", "zzgone", "zzqbad"} <= set(order) and set(order) - {"zzverb", "zzpara", "zzsent", "zzfile", "zzgone", "zzqbad"} <= {"zzkf", "zzkp"} and tb["zzverb"][0] == "V" and tb["zzpara"][0] == "PA" and tb["zzsent"][0] == "S" and tb["zzfile"][0] == "F"
         and tb["zzfile"][2] == "yes" and tb["zzgone"][2] == "NO" and tb["zzqbad"][0] == "Q" and tb["zzqbad"][2] == "NO" and "zznosuch" in tb["zzgone"][1] and "zznoaccount" in tb["zzqbad"][1], repr(tb))
    arow("V2b", "...and each is 'added' against the shipped VOC (none of them is in newvoc)", all(tb[k][3] == "added" for k in tb), repr({k: v[3] for k, v in tb.items()}))
    h.key("esc", idle=1.0)
    filt(h, "bell")
    tb, order = table(h)
    arow("V2c", "bell, which the fixture changed, is 'changed'", order == ["bell"] and tb["bell"][3] == "changed", repr(tb))
    h.key("esc", idle=1.0)
    filt(h, "list")
    tb, order = table(h)
    arow("V2d", "an entry nobody touched is 'same' (every entry with list in its id that is not ours)", len(order) > 0 and all(v[3] == "same" for v in tb.values()), repr({k: v[3] for k, v in tb.items()}))
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    say("\n--- V3: the entry under the cursor")
    h = page(A1)
    filt(h, "zzpara")
    B = lower(h)
    arow("V3", "zzpara under the cursor: its id and kind, then each field with its number (1 PA, 2 display hello, 3 display second line) and the sentence that it is not in the shipped VOC",
         "zzpara  -  a paragraph" in B[0] and any(re.match(r"^\s*1\s+PA$", x) for x in B) and any(re.match(r"^\s*2\s+display hello$", x) for x in B) and any(re.match(r"^\s*3\s+display second line$", x) for x in B)
         and any("not in the shipped VOC" in x for x in B), repr(B[:7]))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_filters():
    say("\n--- V4: type, state and name")
    h = page(A1)
    filt(h, "zz")
    h.typed("t", idle=1.0)
    tb, order = table(h)
    arow("V4a", "T once chooses 'verbs': only the V entries, so zzverb is there and zzfile, zzpara and zzsent are not", "zzverb" in order and not (set(order) & {"zzfile", "zzpara", "zzsent", "zzgone", "zzqbad"}), repr(order))
    h.typed("t", idle=1.0)
    tb, order = table(h)
    arow("V4b", "T again: 'files' - zzfile and zzgone, nothing else of ours", set(order) == {"zzfile", "zzgone"}, repr(order))
    h.typed("t", idle=1.0)
    tb, order = table(h)
    arow("V4c", "...'pointers' - the Q-pointer zzqbad", "zzqbad" in order and "zzfile" not in order and "zzverb" not in order, repr(order))
    h.typed("t", idle=1.0)
    tb, order = table(h)
    arow("V4d", "...'paragraphs and sentences' - zzpara and zzsent", set(order) == {"zzpara", "zzsent"}, repr(order))
    h.key("esc", idle=1.0)
    tb, order = table(h)
    arow("V4e", "Esc clears the type, the state and the filter: every entry is listed again", "zzverb" in order or len(order) >= 16, repr(order[:5]))
    h.typed("s", idle=1.0)
    tb, order = table(h)
    arow("V4f", "S once chooses 'differ from the shipped VOC': ours and bell are there and the entries that are the same are not (list is not)", {"zzverb", "zzpara", "bell"} <= set(order) and "list" not in order, repr(order[:12]))
    h.typed("s", idle=1.0)
    tb, order = table(h)
    arow("V4g", "S again: 'broken pointers' - exactly zzgone and zzqbad", order == ["zzgone", "zzqbad"], repr(order))
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_delete():
    say("\n--- V5: D deletes")
    h = page(A1)
    filt(h, "zzsent")
    h.typed("d", idle=1.2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("V5a", "D shows the exact command 'delete voc zzsent' in a box with Run and Cancel and says what it does", "delete voc zzsent" in T and "Run" in T and "Cancel" in T, T[-400:])
    h.key("enter", idle=1.5)
    arow("V5b", "Enter is Cancel: the entry is still in the VOC (read by a separate session) and in the list", vocinfo(A1, "zzsent") is not None and "zzsent" in table(h)[1], repr((vocinfo(A1, "zzsent"), table(h)[1])))
    h.typed("d", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("wrong\r", idle=2.0)
    arow("V5c", "D, Run and the wrong id typed: nothing is deleted and the status line names the id asked for", vocinfo(A1, "zzsent") is not None and "zzsent" in st(h), repr((vocinfo(A1, "zzsent"), st(h))))
    h.typed("d", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("zzsent\r", idle=1.0)
    until(h, lambda t: "zzsent" not in "\n".join(table(h)[1]))
    arow("V5", "D, Run and the right id typed: the record is gone from the VOC (a separate session reads None) and the list no longer has it", vocinfo(A1, "zzsent") is None and "zzsent" not in table(h)[1], repr((vocinfo(A1, "zzsent"), table(h)[1])))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_keyword():
    say("\n--- V9: D on `all`, a VOC keyword (S4): the page refuses; the VOC is unchanged")
    n0 = voccount(A1)
    k0 = vocinfo(A1, "all")
    arow("V9ctl1", "the fixture VOC holds the entry `all` (a keyword: its type letter is K) and a count of its entries is read by a separate session", k0 not in (None, "ERROR") and k0[0][:1].upper() == "K" and n0 is not None, repr((k0, n0)))
    h = page(A1)
    filt(h, "all")
    order = table(h)[1]
    arow("V9ctl2", "the entry `all` is in the filtered list (the cursor can be put on it)", "all" in order, repr(order))
    if "all" not in order:
        h.key("ctrl-q", idle=1.2)
        h.end()
        return
    for _ in range(order.index("all")):
        h.key("down", idle=0.4)
    h.typed("d", idle=1.5)
    T = re.sub(r"[|\s]+", " ", h.text())
    offered = "delete voc all" in T
    if offered:                                                  # the mutant's path: the box is up; Run and the id typed, then the DELETE's question is answered No so the fixture VOC survives
        h.typed("r", idle=1.2)
        h.typed("all\r", idle=2.5)
        h.typed("n\r", idle=2.0)
    n1 = voccount(A1)
    arow("V9", "D on `all` is refused: no box offers 'delete voc all', the status line says the id is a keyword, and the VOC is unchanged (a separate session: `all` is there and the count is %s)" % n0,
         (not offered) and "keyword" in st(h) and vocinfo(A1, "all") not in (None, "ERROR") and n1 == n0, repr((offered, st(h), n1)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_edit():
    say("\n--- V6: E hands the terminal to SED")
    h = page(A1)
    filt(h, "zzpara")
    h.typed("e", idle=1.0)
    until(h, lambda t: "zzpara" in h.line(41) + h.line(40) + h.line(42) or "File" in h.line(0))
    T = h.text()
    arow("V6a", "E on zzpara hands the screen to SED: SED's menu bar is on row 0 and the record zzpara is the one open", "File" in h.line(0) and "Search" in h.line(0) and "voc zzpara" in h.line(40) + h.line(41) and "display hello" in T and "The entry under the cursor" not in T, T[:300])
    h.typed("\x11", idle=1.5)
    until(h, lambda t: "Press Enter" in t or "The entry under the cursor" in t, 10)
    h.key("enter", idle=2.0)
    until(h, lambda t: "The entry under the cursor" in t, 10)
    T = h.text()
    arow("V6", "Ctrl-Q leaves SED, Enter brings the page back, the cursor is on zzpara again and the status line says it came back from SED", "The entry under the cursor" in T and "back from SED" in st(h) and "zzpara" in table(h)[1], repr((st(h), table(h)[1])))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_refused():
    say("\n--- V7: an account whose voc-edit gate is off")
    h = page(A2)
    L = h.line(19)[3:138] + h.line(20)[3:138]
    h.typed("/", idle=0.8)
    h.typed("bell\r", idle=1.0)
    h.typed("d", idle=1.5)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("V7a", "the box for D says voc-edit is off for you and that the delete is expected to be refused", "voc-edit is off for you" in T and "expected to be refused" in T, T[-500:])
    h.typed("r", idle=1.2)
    h.typed("bell\r", idle=1.0)
    until(h, lambda t: st(h).strip() != "" and "nothing was run" not in st(h))
    S = st(h)
    arow("V7", "Run and the id typed: the kernel refuses (voc-edit is off), the verb's own words are on the status line, and bell is still in the VOC (a separate session reads it)",
         vocinfo(A2, "bell") is not None and S.strip() != "" and "voc-edit" in S.lower() or (vocinfo(A2, "bell") is not None and S.strip() != ""), repr((S, vocinfo(A2, "bell"))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_other():
    say("\n--- V8: help and a small window")
    h = page(A1)
    arow("V8a", "a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    h.click(135, 2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("V8b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("V8c", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    h.typed("tool.voc\r", idle=3.0)
    T = h.text()
    arow("V8d", "a window under 140 by 43 gets no page", "The entry under the cursor" not in T and "The VOC of" not in T, T[-300:])
    h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-voc.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    run = (lambda s: mutant is None or s in MUTANT_SECTIONS.get(mutant, ()))
    try:
        sh.setup("sandbox-tool-voc.py")
        setup_voc()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-voc: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if run("list"):
            section_list()
        if run("filters"):
            section_filters()
        if run("delete"):
            section_delete()
        if run("keyword"):
            section_keyword()
        if mutant is None:
            section_edit()
            section_refused()
            section_other()
    finally:
        sh.teardown()
    say("\nsandbox-tool-voc: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"V\d+", i).group(0) for i in FAILED_IDS if re.match(r"V\d+", i)})
        ok = want == got
        say("sandbox-tool-voc: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
