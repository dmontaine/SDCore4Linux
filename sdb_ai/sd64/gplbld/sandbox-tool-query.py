#!/usr/bin/env python3
#
# sandbox-tool-query.py - TOOL.QUERY, the query and report builder ($tool_query, S.75 DV4), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-query.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# START-HISTORY:
# 25 Oct 26 dm  New (S.75, DV4).
# END-HISTORY
#
# WHAT RUNS.  Two fixture accounts, zzqa and zzqb, each with the files zq (eight records and a dictionary with a column of every kind and four names the page must not put in a sentence),
# zqe (empty), zbig (2,100 records), zesc (two records whose values hold an escape sequence and a byte above 127), zdel (to be deleted under the page), zdir (a directory file) and &zbad&
# (a name the page does not give to a command).  zzqa also has the file &queries& with 100 records: five hostile or odd ones (evil1 to evil5) and 95 good ones.  The fixtures are BUILT
# with the three edit gates on (a program has to be compiled to put the data in) and then the register is written again with EVERY GATE OFF: every session below is an ORDINARY session
# (sd -a<account>, not an administrator) of an account whose gates are at their delivered default.
#
# THE INSTRUMENT.  Every outcome is read from the DISK or from SD, not from what the page said: the sentence the page ran is run again in a SEPARATE session and the page's results box must
# hold every line that session printed; a record the page saved is read back by a program in the account; a file the page made or a command an injection would have run is looked for on
# the disk (zzinj1 to zzinj5 are directories an injected create.file would make; /tmp/zzq-leak-<pid>.txt is what an injected TO would write).
#
#   Q1      the page draws for an ordinary account with every gate off; the files are listed in name order with their kind; a name the page does not give to a command is refused
#   Q2      the dictionary: @id first, the items in order, the four names the page will not put in a sentence are refused with a reason
#   Q3      the main job: columns, two conditions joined by or, two sort levels, run, and the results equal what a separate session prints for the same sentence
#   Q4      break.on and total, id.sup, det.sup, heading, footing, no.page, sample: the sentence and the results
#   Q5      count and sum, and a sum with no column
#   Q6      INJECTION through E: thirteen attacks are refused, with the reason, and nothing they would have done is on the disk; a plain edit is run; a box change writes the sentence again
#   Q7      INJECTION through a condition value: a double quote, a single quote, a backslash, a backquote, a semicolon are refused and the row stays empty; a value with a space is run
#   Q8      save and load: the file &queries& is made after a box, a record is written after a box, loaded back, replaced only with its name typed, deleted only with its name typed
#   Q9      hostile saved records: what does not pass is dropped and counted, a bad record and a bad file are refused, an edited sentence is kept only if it passes; the cap of 100
#   Q10     the results box: 2,000 lines kept and the number said, scrolling, escape sequences taken out, the empty file, the file that went away, a waiting select list
#   Q11     help, a small window, the file given after the verb, the mouse, a piped session
#   Q12     delete from the saved list needs the name typed
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


sh = _load("sandbox_home_for_query", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zzqa", "zzqb"
ME = os.environ.get("USER") or os.getlogin()
LEAK = "/tmp/zzq-leak-%d.txt" % os.getpid()

SCREEN = [None]      # the pty session of the section running: a failed row prints what it was looking at

PAGE_FILES = ("gpl.bp/tool_query", "newvoc/tool.query", "voc_template/tool.query", "helptext/tool.query.page")


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


MUTANTS = {
    # name: (old text of the sandbox's tool_query, new text, the row ids that must fail and no others, the sections that run)
    "edit-unchecked": ("   chk.s = trimf(trimb(es))\n   gosub check.sentence\n   if chk.err # '' then\n      msg = 'not accepted: ' : chk.err\n      return\n   end\n   sent = chk.out",
                       "   sent = trimf(trimb(es))",
                       ["Q6a", "Q6b", "Q6c", "Q6d", "Q6e", "Q6f", "Q6g", "Q6h", "Q6i", "Q6j", "Q6k", "Q6l", "Q6m"], ["q6"]),
    "load-unchecked": ("   gosub validate.panes\n   gosub gen.sentence\n   * a sentence that was edited",
                       "   gosub gen.sentence\n   * a sentence that was edited",
                       ["Q9b", "Q9c", "Q9d", "Q9g2"], ["q9"]),
    "delete-no-typed-name": ("   call $tk_confirm(dsent, lines, lname, res, cmsg, sysmsg(11953))", "   call $tk_confirm(dsent, lines, '', res, cmsg, sysmsg(11953))", ["Q12b", "Q12c"], ["q12"]),      # 26 Oct 26: the sixth argument (the box title) since the faults batch
}


def box():
    return sh.BOX


def acct_dir(a):
    return os.path.join(box(), "user_accounts", a)


def reg_record(name, edit):
    e = "yes" if edit else "no"
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", e, e, e, "", "", "no", "", "", ""]


def sync_page():
    """The page's files go into the sandbox (a build from this tree has them already; a sandbox built before the page existed does not)."""
    for rel in PAGE_FILES:
        src = os.path.join(TREE, "sdsys", rel)
        dst = os.path.join(sh.SYS, rel)
        if not os.path.isfile(src):
            bail("%s is not in the tree" % src)
        if os.path.isdir(os.path.dirname(dst)):
            shutil.copyfile(src, dst)


def compile_page():
    out = adm("BASIC gpl.bp tool_query")
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_query did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def mutate(name):
    old, new, _kills, _sections = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_query")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    compile_page()


POPULATE = "\n".join([
    "   open 'DICT zq' to d else crt 'ZZQW no dict zq' ; stop",
    "   write 'D':@fm:'1':@fm:'':@fm:'Name':@fm:'10L':@fm:'S' on d, 'name'",
    "   write 'D':@fm:'2':@fm:'':@fm:'Qty':@fm:'5R':@fm:'S' on d, 'qty'",
    "   write 'D':@fm:'3':@fm:'MD2':@fm:'Price':@fm:'8R':@fm:'S' on d, 'price'",
    "   write 'D':@fm:'4':@fm:'':@fm:'Region':@fm:'8L':@fm:'S' on d, 'region'",
    "   write 'A':@fm:'4':@fm:'Reg A':@fm:'':@fm:'':@fm:'':@fm:'':@fm:'':@fm:'L':@fm:'8' on d, 'rega'",
    "   write 'PH':@fm:'name qty' on d, 'phr'",
    "   write 'D':@fm:'1':@fm:'':@fm:'Lp':@fm:'6L':@fm:'S' on d, 'lptr'",
    "   write 'D':@fm:'1':@fm:'':@fm:'Wt':@fm:'6L':@fm:'S' on d, 'wait'",
    "   write 'D':@fm:'1':@fm:'':@fm:'Dollar':@fm:'6L':@fm:'S' on d, 'x$y'",
    "   write 'D':@fm:'1':@fm:'':@fm:'Qd':@fm:'6L':@fm:'S' on d, '$qd'",
    "   open 'zq' to f else crt 'ZZQW no zq' ; stop",
    "   write 'Ann':@fm:'3':@fm:'150':@fm:'east' on f, 'r1'",
    "   write 'Bob':@fm:'5':@fm:'325':@fm:'west' on f, 'r2'",
    "   write 'Cy':@fm:'2':@fm:'1000':@fm:'east' on f, 'r3'",
    "   write 'Dee':@fm:'8':@fm:'475':@fm:'north' on f, 'r4'",
    "   write 'Eve Jones':@fm:'1':@fm:'99':@fm:'east' on f, 'r5'",
    "   write 'Fay':@fm:'12':@fm:'50':@fm:'west' on f, 'r6'",
    "   write 'Gus':@fm:'0':@fm:'':@fm:'' on f, 'r7'",
    "   write 'Hal':@fm:'7':@fm:'700':@fm:'north' on f, 'r8'",
    "   open 'DICT zbig' to d2 else crt 'ZZQW no dict zbig' ; stop",
    "   write 'D':@fm:'1':@fm:'':@fm:'Nm':@fm:'12L':@fm:'S' on d2, 'nm'",
    "   open 'zbig' to f2 else crt 'ZZQW no zbig' ; stop",
    "   for i = 1 to 2100",
    "      write 'row ':i on f2, 'b':i",
    "   next i",
    "   open 'DICT zesc' to d3 else crt 'ZZQW no dict zesc' ; stop",
    "   write 'D':@fm:'1':@fm:'':@fm:'Nm':@fm:'20L':@fm:'S' on d3, 'nm'",
    "   open 'zesc' to f3 else crt 'ZZQW no zesc' ; stop",
    "   write 'Esc':char(27):'[31mred' on f3, 'e1'",
    "   write 'hi':char(200):'ok' on f3, 'e2'",
    "   crt 'ZZQW done'", "end", ""])

# the file of saved queries, with hostile and odd records among good ones (zzqa only)
PLANT = "\n".join([
    "   execute 'create.file &queries& dynamic' capturing mk",
    "   open '&queries&' to f else crt 'ZZPL no queries' ; stop",
    "   dq = char(34) ; sq = char(39) ; semi = char(59)",
    "   r = 'query1':@fm:'zq':@fm:'list'",
    "   r<4> = 'name':@vm:'x':semi:'sh':@vm:'lptr':@vm:'nosuchitem'",
    "   r<6> = '':@vm:'and'",
    "   r<7> = 'qty':@vm:'lptr'",
    "   r<8> = '>':@vm:'to'",
    "   r<9> = '4':@vm:'a':dq:' ':semi:' create.file zzinj4 ':dq",
    "   r<10> = 'name':@vm:'x y'",
    "   r<11> = 'd':@vm:'a'",
    "   r<12> = 'Big':sq:'Head'",
    "   r<13> = 'Foot':semi:'er'",
    "   r<14> = 1 ; r<15> = 0 ; r<16> = 0 ; r<17> = '3x' ; r<18> = 0 ; r<19> = 'list zq name'",
    "   write r on f, 'evil1'",
    "   r = 'query1':@fm:'nosuchfile':@fm:'list'",
    "   write r on f, 'evil2'",
    "   r = 'query1':@fm:'zq':@fm:'list':@fm:'name'",
    "   r<18> = 1 ; r<19> = 'list zq name ':semi:' create.file zzinj5'",
    "   write r on f, 'evil3'",
    "   r = 'junk':@fm:'zq':@fm:'list'",
    "   write r on f, 'evil4'",
    "   r = 'query1':@fm:'zq':@fm:'list':@fm:'name':@vm:'qty'",
    "   r<18> = 1 ; r<19> = 'list zq name qty vertically'",
    "   write r on f, 'evil5'",
    "   for i = 1 to 95",
    "      r = 'query1':@fm:'zq':@fm:'list':@fm:'name'",
    "      r<19> = 'list zq name'",
    "      write r on f, 'fill':right('0':i, 2)",
    "   next i",
    "   crt 'ZZPL done'", "end", ""])

READER = "\n".join([
    "   id = field(@sentence, ' ', dcount(@sentence, ' '))",
    "   open '&queries&' to f else crt 'RD[nofile]' ; stop",
    "   read r from f, id else crt 'RD[norecord]' ; stop",
    "   crt 'RD[':convert(@fm, '|', convert(@vm, '~', r)):']'",
    "end", ""])

COUNTER = "\n".join([
    "   open '&queries&' to f else crt 'QN[nofile]' ; stop",
    "   select f to 9",
    "   n = 0",
    "   loop",
    "      readnext x from 9 else exit",
    "      n += 1",
    "   repeat",
    "   crt 'QN[':n:']'",
    "end", ""])


def make_account(a, plant):
    q = g
    q.FIXTURES[a] = ("no", "no")
    q.build_account(a)
    q.reg_write(a, reg_record(a, True))                    # the edit gates are ON while the fixture is built: a program has to be compiled to put the data in
    bp = os.path.join(acct_dir(a), "bp")
    q.put(os.path.join(bp, "zzqw"), POPULATE)
    q.put(os.path.join(bp, "zzrd"), READER)
    q.put(os.path.join(bp, "zzcnt"), COUNTER)
    cmds = ["CREATE.FILE zq", "CREATE.FILE zqe", "CREATE.FILE zbig", "CREATE.FILE zesc", "CREATE.FILE zdel", "CREATE.FILE zdir directory", "CREATE.FILE &zbad&",
            "BASIC bp zzqw zzrd zzcnt", "RUN bp zzqw"]
    if plant:
        q.put(os.path.join(bp, "zzpl"), PLANT)
        cmds += ["BASIC bp zzpl", "RUN bp zzpl"]
    out = q.plain(a, cmds)
    if not has(out, r"^ZZQW done$"):
        bail("the fixture files of %s were not made:\n%s" % (a, "\n".join(out[-14:])))
    if plant and not has(out, r"^ZZPL done$"):
        bail("the saved queries of %s were not planted:\n%s" % (a, "\n".join(out[-14:])))
    if not has(out, r"Compiled 3 program"):
        bail("the helper programs of %s did not compile:\n%s" % (a, "\n".join(out[-14:])))
    q.reg_write(a, reg_record(a, False))                   # ... and now EVERY gate is off
    reg = g.reg_read(a)
    if [x.strip() for x in reg[9:12]] != ["no", "no", "no"]:
        bail("the register of %s still has an edit gate on: %r" % (a, reg[9:12]))


def setup_query():
    sync_page()
    compile_page()
    make_account(A1, True)
    make_account(A2, False)


# ------------------------------------------------------------------------------------------------- reading the page

def page(account, arg="", pre=()):
    h = H(account=account, cols=140, rows=43)
    SCREEN[0] = h
    for c in pre:
        h.typed(c + "\r", idle=1.5)
    h.typed("tool.query%s\r" % ((" " + arg) if arg else ""), idle=3.5)
    return h


def st(h):
    return h.line(40)


def sentence(h):
    """the sentence in the box at the foot: its rows joined"""
    rows = [h.line(n)[3:137].strip() for n in range(32, 37)]
    return re.sub(r"\s+", " ", " ".join(r for r in rows if r)).strip()


def state_line(h):
    return h.line(37)[3:137].strip()


def files_rows(h):
    out = {}
    order = []
    for n in range(2, 18):
        l = h.line(n)
        name = l[3:23].strip()
        if name:
            order.append(name)
            out[name] = (l[2:3], l[24:28].strip())
    return out, order


def cols_rows(h):
    """[(nr, flag, item, type, heading)] of the Columns box"""
    out = []
    for n in range(3, 19):
        l = h.line(n)
        item = l[35:57].strip()
        if item:
            out.append((l[30:32].strip(), l[33:35].strip(), item, l[57:62].strip(), l[62:72].strip()))
    return out


def cond_row(h, i):
    l = h.line(2 + i)
    return (l[78:83].strip(), l[83:106].strip(), l[106:114].strip(), l[114:136].strip())


def sort_row(h, i):
    l = h.line(21 + i)
    return (l[9:20].strip(), l[20:46].strip())


def norm_screen(h):
    return re.sub(r"[|\s]+", " ", h.text())


def results_rows(h):
    return [h.line(n)[3:137].rstrip() for n in range(6, 39)]


def key(h, name, n=1, idle=0.4):
    for _ in range(n):
        h.key(name, idle=idle)


def tp(h, s, idle=0.7):
    h.typed(s, idle=idle)


def until(h, pred, secs=25.0):
    """a verb that the page runs prints nothing while it runs, so a wait for idle output is not a wait for the page: pump the pty until the screen satisfies pred"""
    for _ in range(int(secs / 0.5)):
        if pred(h.text()):
            return True
        h.s._pump(0.5)
    return pred(h.text())


def choose(h, name):
    """/ name Enter in the File box, then Enter chooses the first file that holds the text; the Columns box has the focus afterwards"""
    for _ in range(5):
        if "[*] File" in h.text():
            break
        h.key("btab", idle=0.7)
    tp(h, "/", 0.9)
    tp(h, name + "\r", 1.0)
    h.key("enter", idle=1.4)


def mark(h, pos, n=1):
    """the Columns box has the focus: the item at position pos (1 is @id) gets its mark"""
    key(h, "home", idle=0.3)
    key(h, "down", pos - 1, idle=0.25)
    tp(h, " ", 0.5)


ZQ_ITEMS = ["@id", "lptr", "name", "price", "qty", "rega", "region", "wait", "x$y"]
POS = {n: i + 1 for i, n in enumerate(ZQ_ITEMS)}
USABLE = ["@id", "name", "price", "qty", "rega", "region"]           # what the pick list offers for a condition
SORT_PICK = ["(none)"] + USABLE


def cond_set(h, row_no, item, op_index, value):
    """the Conditions box has the focus: the row gets its item (by place in the pick list), operator (by place in the table) and value"""
    key(h, "home", idle=0.3)
    key(h, "down", row_no - 1, idle=0.3)
    h.key("enter", idle=1.0)
    key(h, "down", USABLE.index(item), idle=0.25)
    h.key("enter", idle=1.0)
    key(h, "down", op_index, idle=0.25)
    h.key("enter", idle=1.0)
    tp(h, value + "\r", 1.2)


def verb_lines(account, sent):
    """what a SEPARATE ordinary session prints for the sentence: every line but the one that echoes the sentence with its page number"""
    out = g.plain(account, [sent])
    return [re.sub(r"\s+", " ", l.strip()) for l in out if l.strip() and "Page 1" not in l]


def same_as_verb(h, account, sent, minimum=2, scroll=False):
    """every line a separate session prints for the sentence is in the Results box (with scroll, in some screen of it, from the first line to the last)"""
    want = verb_lines(account, sent)
    got = norm_screen(h)
    if scroll:
        parts = [got]
        key(h, "home", 1, idle=0.8)
        parts.append(norm_screen(h))
        for _ in range(60):
            m = re.search(r"Showing (\d+) to (\d+)", h.line(5))
            k = re.search(r"the first (\d+) are kept", h.line(5))
            n = re.search(r"(\d+) lines", h.line(5))
            keep = int(k.group(1)) if k else (int(n.group(1)) if n else 0)
            if not m or int(m.group(2)) >= keep:
                break
            key(h, "pgdn", 1, idle=0.8)
            parts.append(norm_screen(h))
        got = " ".join(parts)
    missing = [l for l in want if l not in got]
    return len(want) >= minimum and not missing, "missing %r of %d lines" % (missing[:4], len(want))


def boxtext(h):
    """the words inside the confirm box on the screen, one line, its wrapped lines joined; the whole screen when there is no box"""
    rows = [h.line(n) for n in range(43)]
    top = next((n for n, l in enumerate(rows) if re.search(r"Run this command\?|Write this record\?|Delete this record\?", l)), None)      # 26 Oct 26 (faults): save and delete are titled by what they do
    if top is None:
        return re.sub(r"[|\s]+", " ", h.text())
    s0, s1 = rows[top].index("+"), rows[top].rindex("+")
    inner = []
    for n in range(top + 1, 43):
        if rows[n][s0:s0 + 1] == "+":
            break
        inner.append(rows[n][s0 + 1:s1])
    return re.sub(r"[|\s]+", " ", " ".join(inner))


def edit_sentence(h, text):
    """E: the ask box holds the sentence; it is wiped and the text typed"""
    tp(h, "e", 1.0)
    tp(h, "\x7f" * 80, 0.6)
    tp(h, text + "\r", 1.3)


def in_pages(h, name_pat):
    return re.search(name_pat, h.text()) is not None


def on_disk(account, name):
    return os.path.exists(os.path.join(acct_dir(account), name))


def read_rec(account, rid):
    out = g.plain(account, ["RUN bp zzrd " + rid])
    for l in out:
        m = re.match(r"^RD\[(.*)\]$", l.strip())
        if m:
            return m.group(1)
    return None


def count_q(account):
    out = g.plain(account, ["RUN bp zzcnt"])
    for l in out:
        m = re.match(r"^QN\[(.*)\]$", l.strip())
        if m:
            return m.group(1)
    return None


# ------------------------------------------------------------------------------------------------- the sections

def section_q1():
    say("\n--- Q1: the page for an ordinary account with every gate off, and the files")
    reg = g.reg_read(A1)
    h = page(A1)
    T = h.text()
    if "The sentence" not in T:
        dump(h)
        bail("tool.query never drew its page in an ordinary account, so no row below can be believed")
    arow("Q1", "the page draws for an ordinary account whose three edit gates are off (register fields 10-12 read %r), for the audience %s@%s at the right end of row 0, in its five boxes and the sentence box" % (reg[9:12], ME, A1),
         re.search(r"tool\.query\s+%s@%s" % (re.escape(ME), A1), h.line(0)) is not None and all(t in T for t in ("File", "Columns", "Conditions", "Sort", "Options", "The sentence")) and [x.strip() for x in reg[9:12]] == ["no", "no", "no"],
         repr(h.line(0)[100:]))
    tb, order = files_rows(h)
    arow("Q1b", "the files are listed in name order with their kind: zq, zqe, zbig, zesc, zdel dynamic and zdir a directory file; &zbad& is listed too",
         all(n in tb for n in ("zq", "zqe", "zbig", "zesc", "zdel", "zdir", "&zbad&")) and order == sorted(order) and tb["zq"][1] == "dyn" and tb["zdir"][1] == "dir" and tb["&zbad&"][1] == "dyn", repr((order, tb.get("zdir"))))
    arow("Q1c", "before a file is chosen the sentence box says so and R runs nothing", "Choose a file first" in sentence(h) and (tp(h, "r", 1.0) is None) and "Choose a file first" in st(h) + sentence(h), repr((sentence(h), st(h))))
    arow("Q1d", "the [?] button is at the end of the Conditions box's header row", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    # &zbad& is listed, but the page does not give it to a command
    tp(h, "/", 0.9)
    tp(h, "zbad\r", 1.0)
    h.key("enter", idle=1.2)
    arow("Q1e", "Enter on &zbad& (a name the page does not give to a command) chooses nothing: the status line says why and the sentence box still asks for a file",
         "does not give to a command" in st(h) and "Choose a file first" in sentence(h), repr((st(h), sentence(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q2():
    say("\n--- Q2: the dictionary")
    h = page(A1)
    choose(h, "zq")
    tb, order = files_rows(h)
    arow("Q2", "Enter chooses the file: the Columns box takes the focus, the file is marked in the File box and the sentence box holds list zq", "[*] Columns" in h.text() and tb.get("zq", ("",))[0] == "*" and sentence(h) == "list zq", repr((sentence(h), tb.get("zq"))))
    cr = cols_rows(h)
    arow("Q2b", "the Columns box lists @id first and then the dictionary in name order, with the type of each (D, and A for rega); a phrase (phr) and a record that starts with a dollar are not listed",
         [c[2] for c in cr] == ZQ_ITEMS and dict((c[2], c[3]) for c in cr)["rega"] == "A" and dict((c[2], c[3]) for c in cr)["name"] == "D" and "phr" not in [c[2] for c in cr] and "$qd" not in [c[2] for c in cr], repr(cr))
    arow("Q2c", "the status line counts the items: 9 in the dictionary of zq", "zq: 9 items in its dictionary" in st(h), repr(st(h)))
    refused = {}
    for item in ("lptr", "wait", "x$y"):
        mark(h, POS[item])
        refused[item] = st(h)
    cr = cols_rows(h)
    arow("Q2d", "Space on lptr (a word that sends output to a printer), wait (a keyword of the VOC) and x$y (a character the page does not use) marks nothing and says why; the sentence is still list zq",
         all("does not put this name in a sentence" in s for s in refused.values()) and all(c[0] == "" for c in cr) and sentence(h) == "list zq", repr(refused))
    mark(h, POS["name"])
    mark(h, POS["qty"])
    mark(h, POS["region"])
    cr = cols_rows(h)
    arow("Q2e", "Space marks name, qty and region: the marks are numbered in the order they were made and the sentence lists them in that order", [(c[0], c[2]) for c in cr if c[0]] == [("1", "name"), ("2", "qty"), ("3", "region")] and sentence(h) == "list zq name qty region", repr((cr, sentence(h))))
    mark(h, POS["qty"])
    arow("Q2f", "Space on a marked column takes the mark off and the later marks move up: name 1, region 2", [(c[0], c[2]) for c in cr if c[0]] and [(c[0], c[2]) for c in cols_rows(h) if c[0]] == [("1", "name"), ("2", "region")] and sentence(h) == "list zq name region", repr((cols_rows(h), sentence(h))))
    tp(h, "x", 0.8)
    arow("Q2g", "X takes every mark off", all(c[0] == "" for c in cols_rows(h)) and sentence(h) == "list zq", repr(sentence(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q3():
    say("\n--- Q3: the main job - columns, conditions, sorts, run, and the results against a separate session")
    h = page(A1)
    choose(h, "zq")
    mark(h, POS["name"])
    mark(h, POS["qty"])
    mark(h, POS["region"])
    arow("Q3a", "three columns marked: the sentence is list zq name qty region", sentence(h) == "list zq name qty region", repr(sentence(h)))
    h.key("tab", idle=0.7)
    cond_set(h, 1, "qty", 3, "4")
    c1 = cond_row(h, 1)
    arow("Q3b", "Conditions row 1 (qty > 4) is shown and the sentence has its with clause before the columns",
         c1[1] == "qty" and c1[2] == ">" and c1[3] == '"4"' and sentence(h) == 'list zq with qty > "4" name qty region', repr((c1, sentence(h))))
    cond_set(h, 2, "region", 0, "west")
    arow("Q3c", "row 2 (region = west) joins row 1 with and", cond_row(h, 2)[0] == "and" and sentence(h) == 'list zq with qty > "4" and with region = "west" name qty region', repr((cond_row(h, 2), sentence(h))))
    tp(h, "j", 0.8)
    arow("Q3d", "J turns the join of the row under the cursor to or", cond_row(h, 2)[0] == "or" and sentence(h) == 'list zq with qty > "4" or with region = "west" name qty region', repr((cond_row(h, 2), sentence(h))))
    h.key("tab", idle=0.7)
    key(h, "home", idle=0.3)
    h.key("enter", idle=1.0)
    key(h, "down", SORT_PICK.index("region"), idle=0.25)
    h.key("enter", idle=1.0)
    key(h, "down", 1)
    h.key("enter", idle=1.0)
    key(h, "down", SORT_PICK.index("qty"), idle=0.25)
    h.key("enter", idle=1.0)
    tp(h, " ", 0.8)
    s1, s2 = sort_row(h, 1), sort_row(h, 2)
    want = 'sort zq with qty > "4" or with region = "west" by region by.dsnd qty name qty region'
    arow("Q3e", "two sort levels (region ascending, qty turned over with Space): the verb becomes sort and the sentence has by region by.dsnd qty", s1 == ("by", "region") and s2 == ("by.dsnd", "qty") and sentence(h) == want, repr((s1, s2, sentence(h))))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    ok, why = same_as_verb(h, A1, want)
    arow("Q3f", "R shows the output in the Results box and every line a SEPARATE session prints for the same sentence is in it (4 records: Bob, Dee, Fay and Hal)", ok and "Ran: sort zq" in norm_screen(h), why)
    arow("Q3g", "the box says how many lines and where the view is", re.search(r"\d+ lines\.\s+Showing 1 to \d+", h.text()) is not None, h.line(5))
    h.key("esc", idle=1.2)
    arow("Q3h", "Esc goes back to the boxes and the sentence is as it was", "The sentence" in h.text() and sentence(h) == want, sentence(h))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q4():
    say("\n--- Q4: break.on, total and the options")
    h = page(A1)
    choose(h, "zq")
    mark(h, POS["region"])
    mark(h, POS["qty"])
    tp(h, "b", 0.6)      # the cursor is on qty: B breaks on it; take that off and put it on region
    tp(h, "b", 0.6)
    key(h, "home", idle=0.3)
    key(h, "down", POS["region"] - 1, idle=0.25)
    tp(h, "b", 0.6)
    key(h, "home", idle=0.3)
    key(h, "down", POS["qty"] - 1, idle=0.25)
    tp(h, "t", 0.6)
    cr = {c[2]: c[1] for c in cols_rows(h)}
    arow("Q4", "B marks region as a break column and T marks qty as a total column; the flags show in the Columns box and the sentence has break.on region total qty", cr["region"] == "B" and cr["qty"] == "T" and sentence(h) == "list zq break.on region total qty", repr((cr, sentence(h))))
    tp(h, "b", 0.6)
    tp(h, "b", 0.6)
    arow("Q4b", "B on a column that is marked T makes it B, and B again takes it off", {c[2]: c[1] for c in cols_rows(h)}["qty"] == "", repr(cols_rows(h)))
    tp(h, "t", 0.6)
    h.key("tab", idle=0.6)
    h.key("tab", idle=0.6)
    key(h, "home", idle=0.3)
    h.key("enter", idle=1.0)
    key(h, "down", SORT_PICK.index("region"), idle=0.25)
    h.key("enter", idle=1.0)
    arow("Q4c", "the sort level on region makes the verb sort: sort zq by region break.on region total qty", sentence(h) == "sort zq by region break.on region total qty", sentence(h))
    h.key("tab", idle=0.7)
    key(h, "home", idle=0.3)
    key(h, "down", 3, idle=0.25)       # row 4: id.sup
    tp(h, " ", 0.7)
    key(h, "down", 1)
    tp(h, " ", 0.7)                    # row 5: det.sup
    key(h, "down", 1)
    tp(h, " ", 0.7)                    # row 6: no.page
    key(h, "down", 1)
    h.key("enter", idle=1.0)           # row 7: sample
    tp(h, "5\r", 1.2)
    key(h, "home", idle=0.3)
    key(h, "down", 1)
    h.key("enter", idle=1.0)           # row 2: heading
    tp(h, "My report\r", 1.2)
    key(h, "down", 1)
    h.key("enter", idle=1.0)           # row 3: footing
    tp(h, "The end\r", 1.2)
    want = 'sort zq by region break.on region total qty id.sup det.sup heading "My report" footing "The end" no.page sample 5'
    arow("Q4d", "the options set id.sup, det.sup, a heading, a footing, no.page and a sample of 5: the sentence has them in the order the page builds, and the Options box shows the three switches as [x]",
         sentence(h) == want and sum(1 for n in range(24, 27) if "[x]" in h.line(n)) == 3, repr((sentence(h), [h.line(n)[48:100] for n in range(21, 28)])))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    ok, why = same_as_verb(h, A1, want)
    arow("Q4e", "R: the results hold every line a separate session prints for it (the heading, the totals, the footing and the sample note)", ok and "My report" in norm_screen(h) and "The end" in norm_screen(h), why)
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q5():
    say("\n--- Q5: count and sum")
    h = page(A1)
    choose(h, "zq")
    mark(h, POS["qty"])
    h.key("tab", idle=0.6)
    h.key("tab", idle=0.6)
    h.key("tab", idle=0.6)
    key(h, "home", idle=0.3)
    h.key("enter", idle=1.0)
    arow("Q5", "Report: Enter on the first Options row changes list to count: the sentence is count zq (the columns are not used)", sentence(h) == "count zq", sentence(h))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) counted" in t)
    ok, why = same_as_verb(h, A1, "count zq", 1)
    arow("Q5b", "R: the results say what a separate session says: 8 record(s) counted", ok and "8 record(s) counted" in norm_screen(h), why)
    h.key("esc", idle=1.2)
    h.key("enter", idle=1.0)
    arow("Q5c", "Enter again changes count to sum: the sentence is sum zq qty", sentence(h) == "sum zq qty", sentence(h))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) summed" in t)
    ok, why = same_as_verb(h, A1, "sum zq qty", 2)
    arow("Q5d", "R: the total of qty is what a separate session prints (38, over 8 records)", ok and "38" in norm_screen(h), why)
    h.key("esc", idle=1.2)
    h.key("btab", idle=0.8)
    h.key("btab", idle=0.8)
    h.key("btab", idle=0.8)
    tp(h, "x", 0.8)
    h.key("tab", idle=0.6)
    h.key("tab", idle=0.6)
    h.key("tab", idle=0.6)
    arow("Q5e", "a sum with no column makes no sentence: the box says what to do, and R says there is nothing to run",
         "A sum needs at least one column" in sentence(h) and (tp(h, "r", 1.0) is None) and "A sum needs at least one column" in st(h), repr((sentence(h), st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


ATTACKS = [
    # id, the text typed in the E box, a word the refusal must contain
    ("Q6a", "list zq name ; create.file zzinj1", "semicolon"),
    ("Q6b", "list zq name to %s" % LEAK, "sends the output somewhere else"),
    ("Q6c", "list zq name lptr", "sends the output somewhere else"),
    ("Q6d", "LIST zq NAME CSV AS zzinj3 r1", "sends the output somewhere else"),
    ("Q6e", 'list zq with name = "x" ; sh', "semicolon"),
    ("Q6f", 'list zq with name = "a;b" name', "semicolon"),
    ("Q6g", "list zq with name = 'x' name", "semicolon"),
    ("Q6h", "select zq", "first word must be"),
    ("Q6i", "list voc name", "the file must be"),
    ("Q6j", "list zq name create.file zzinj4", "is not a word the page knows"),
    ("Q6k", "list zq name saving zzl", "sends the output somewhere else"),
    ("Q6l", 'list zq with name = "unclosed name', "quote is not closed"),
    ("Q6m", "sh", "first word must be"),
]


def section_q6():
    say("\n--- Q6: INJECTION through E - the attacks are refused, and nothing they would have done is on the disk")
    h = page(A1)
    choose(h, "zq")
    mark(h, POS["name"])
    base = sentence(h)
    for rid, text, why in ATTACKS:
        edit_sentence(h, text)
        s = st(h)
        arow(rid, "E with  %s  is refused (the status line says why: %s) and the sentence is still %s" % (text[:44], why, base),
             "not accepted" in s and why in s and sentence(h) == base and "Edited by hand" not in state_line(h), repr((s, sentence(h))))
        tp(h, "r", 1.8)                                 # whatever the page holds is run: a defence in depth - the run checks again
        if "Ran:" in h.text():
            h.key("esc", idle=1.0)
    gone = [n for n in ("zzinj1", "zzinj2", "zzinj3", "zzinj4") if on_disk(A1, n)]
    arow("Q6n", "after all thirteen attacks and a run after each, nothing an injected command would have made is on the disk (no zzinj directory, no file from TO)", not gone and not os.path.exists(LEAK) and "The sentence" in h.text(), repr(gone))
    edit_sentence(h, "list zq name qty vertically")
    arow("Q6o", "a plain edit that uses words the page knows is accepted: the state line says it was edited by hand and the sentence is the text typed", sentence(h) == "list zq name qty vertically" and "Edited by hand" in state_line(h), repr((sentence(h), state_line(h))))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    ok, why = same_as_verb(h, A1, "list zq name qty vertically", 4, scroll=True)
    arow("Q6p", "the edited sentence runs and its results are what a separate session prints (the vertical form: one value to a line)", ok and "Name" in norm_screen(h), why)
    h.key("esc", idle=1.2)
    key(h, "home", idle=0.3)
    key(h, "down", POS["region"] - 1, idle=0.25)
    tp(h, " ", 0.9)
    arow("Q6q", "a change in a box writes the sentence again from the boxes: the hand edit is given up, and the status line says so", sentence(h) == "list zq name region" and "Edited by hand" not in state_line(h) and "written again from the boxes" in st(h), repr((sentence(h), st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


VALUE_ATTACKS = [
    ("Q7a", 'a"b', "quote"),
    ("Q7b", "a'b", "quote"),
    ("Q7c", "a\\b", "backslash"),
    ("Q7d", "a`b", "backquote"),
    ("Q7e", "a;b", "semicolon"),
]


def section_q7():
    say("\n--- Q7: INJECTION through a condition value")
    h = page(A1)
    choose(h, "zq")
    mark(h, POS["name"])
    h.key("tab", idle=0.7)
    for rid, val, why in VALUE_ATTACKS:
        cond_set(h, 1, "name", 0, val)
        arow(rid, "the value  %s  is refused ('not accepted', %s): the row stays empty and the sentence is still list zq name" % (val, why),
             "not accepted" in st(h) and why in st(h) and cond_row(h, 1)[1] == "" and sentence(h) == "list zq name", repr((st(h), cond_row(h, 1), sentence(h))))
    cond_set(h, 1, "name", 0, "Eve Jones")
    arow("Q7f", "a value with a space is accepted and quoted: with name = \"Eve Jones\"", sentence(h) == 'list zq with name = "Eve Jones" name', sentence(h))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    ok, why = same_as_verb(h, A1, 'list zq with name = "Eve Jones" name', 2)
    arow("Q7g", "run: the results are what a separate session prints (one record, Eve Jones)", ok and "Eve Jones" in norm_screen(h) and "1 record(s) listed" in norm_screen(h), why)
    h.key("esc", idle=1.2)
    tp(h, "d", 0.8)
    arow("Q7h", "D clears the row: it is empty again and the sentence is list zq name", cond_row(h, 1)[1] == "" and sentence(h) == "list zq name", repr((cond_row(h, 1), sentence(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q8():
    say("\n--- Q8: save and load (an account that has no &queries& file yet)")
    h = page(A2)
    choose(h, "zq")
    mark(h, POS["name"])
    mark(h, POS["qty"])
    h.key("tab", idle=0.7)
    cond_set(h, 1, "qty", 3, "4")
    h.key("tab", idle=0.7)
    key(h, "home", idle=0.3)
    h.key("enter", idle=1.0)
    key(h, "down", SORT_PICK.index("name"), idle=0.25)
    h.key("enter", idle=1.0)
    h.key("tab", idle=0.7)
    key(h, "home", idle=0.3)
    key(h, "down", 1)
    h.key("enter", idle=1.0)
    tp(h, "Saved head\r", 1.2)
    want = 'sort zq with qty > "4" by name name qty heading "Saved head"'
    arow("Q8", "the query to save is built (condition, sort, columns, heading): %s" % want, sentence(h) == want, sentence(h))
    arow("Q8a", "the account has no &queries& file and no record yet", not on_disk(A2, "&queries&") and read_rec(A2, "q1") == "nofile", repr((on_disk(A2, "&queries&"), read_rec(A2, "q1"))))
    tp(h, "s", 1.0)
    tp(h, "q1\r", 1.5)
    T = boxtext(h)
    arow("Q8b", "S asks for a name, then shows the box for the file: the exact command create.file &queries& dynamic, with Run and Cancel", "create.file &queries& dynamic" in T and "Run" in T and "Cancel" in T, T[-400:])
    h.key("enter", idle=1.5)
    arow("Q8c", "Enter is Cancel: the file was not made and nothing was saved", not on_disk(A2, "&queries&") and "nothing was run" in st(h), repr((on_disk(A2, "&queries&"), st(h))))
    tp(h, "s", 1.0)
    tp(h, "q1\r", 1.5)
    tp(h, "r", 2.5)
    T = boxtext(h)
    arow("Q8d", "Run makes the file (a directory on the disk) and the second box follows: it names the record, says it is not a command and that only that record is written",
         on_disk(A2, "&queries&") and "write q1 to &queries&" in T and "not a command" in T, T[-500:])
    h.key("enter", idle=1.5)
    arow("Q8e", "Enter is Cancel again: the file is there but no record was written", on_disk(A2, "&queries&") and read_rec(A2, "q1") == "norecord", repr(read_rec(A2, "q1")))
    tp(h, "s", 1.0)
    tp(h, "q1\r", 1.5)
    tp(h, "r", 2.0)
    rec = read_rec(A2, "q1") or ""
    f = rec.split("|")
    arow("Q8f", "Run writes the record: a program in the account reads it back - query1, the file zq, the kind list, the columns name~qty, the condition qty > 4, the sort name, the heading and the sentence",
         len(f) >= 19 and f[0] == "query1" and f[1] == "zq" and f[2] == "list" and f[3] == "name~qty" and f[6].startswith("qty") and f[7].startswith(">") and f[8].startswith("4") and f[9].startswith("name") and f[11] == "Saved head" and f[18] == want, repr(rec))
    arow("Q8g", "the status line says it was saved", "saved q1" in st(h), st(h))
    choose(h, "zq")
    arow("Q8h", "choosing the file again starts a new query: the sentence is list zq", sentence(h) == "list zq", sentence(h))
    tp(h, "l", 1.5)
    arow("Q8i", "L lists the saved queries: q1, its file and kind", re.search(r"q1\s+zq\s+list", h.text()) is not None and "Saved queries" in h.text(), h.text()[:600])
    h.key("enter", idle=1.5)
    arow("Q8j", "Enter loads it: the boxes and the sentence are as they were saved, and the status line says loaded q1", sentence(h) == want and "loaded q1" in st(h) and cond_row(h, 1)[1] == "qty" and sort_row(h, 1) == ("by", "name"), repr((sentence(h), st(h))))
    tp(h, "r", 1.0)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    ok, why = same_as_verb(h, A2, want, 3)
    arow("Q8k", "the loaded query runs and its results are what a separate session prints for the saved sentence", ok, why)
    h.key("esc", idle=1.2)
    key(h, "home", idle=0.3)
    key(h, "down", POS["region"] - 1, idle=0.25)
    tp(h, " ", 0.9)
    tp(h, "s", 1.0)
    tp(h, "q1\r", 1.5)
    T = boxtext(h)
    arow("Q8l", "saving over a name that exists shows the box with the old record's file and asks for the name typed", "Replaces the saved query q1" in T, T[-400:])
    tp(h, "r", 1.2)
    tp(h, "wrong\r", 1.5)
    rec = read_rec(A2, "q1") or ""
    arow("Q8m", "a wrong name typed replaces nothing: the record still has the two columns name~qty", rec.split("|")[3:4] == ["name~qty"] and "nothing was run" in st(h), repr((rec, st(h))))
    tp(h, "s", 1.0)
    tp(h, "q1\r", 1.5)
    tp(h, "r", 1.2)
    tp(h, "q1\r", 2.0)
    rec = read_rec(A2, "q1") or ""
    arow("Q8n", "the name typed replaces the record: it now has the columns name~qty~region", rec.split("|")[3:4] == ["name~qty~region"] and "saved q1" in st(h), repr((rec, st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q9():
    say("\n--- Q9: hostile saved records (zzqa), the cap of 100")
    h = page(A1)
    choose(h, "zq")
    arow("Q9", "the account has 100 saved queries: five odd ones and 95 good ones", count_q(A1) == "100", count_q(A1))
    tp(h, "l", 1.5)
    T = h.text()
    arow("Q9a", "L lists them in name order: evil1 to evil5 first, then fill01", all(n in T for n in ("evil1", "evil2", "evil3", "evil4", "evil5", "fill01")) and T.find("evil1") < T.find("evil5") < T.find("fill01"), T[:500])
    h.key("enter", idle=1.8)
    s1 = sentence(h)
    want1 = 'sort zq with qty > "4" by.dsnd name name id.sup'
    arow("Q9b", "evil1 (a hostile column, a hostile condition, a hostile sort, a heading with a quote, a footing with a semicolon, a sample of 3x) is loaded with ONLY the parts that pass: %s" % want1, s1 == want1, repr((s1, st(h))))
    arow("Q9c", "...and the status line counts what was dropped: 8 parts", st(h).endswith("loaded evil1: 8 part(s) did not pass the checks and were dropped") or "loaded evil1: 8 part(s) did not pass the checks and were dropped" in st(h), repr(st(h)))
    arow("Q9d", "...and nothing in the record ran: no zzinj4 directory, the Conditions box holds only row 1", not on_disk(A1, "zzinj4") and cond_row(h, 2)[1] == "" and cond_row(h, 1)[1] == "qty", repr((cond_row(h, 1), cond_row(h, 2))))
    tp(h, "l", 1.5)
    key(h, "down", 1)
    h.key("enter", idle=1.5)
    arow("Q9e", "evil2 names a file that is not one of the account's files: nothing is loaded and the status line says so", "is not one of your files with a dictionary: nothing was loaded" in st(h), repr(st(h)))
    key(h, "down", 2)
    h.key("enter", idle=1.5)
    arow("Q9f", "evil4 does not say it is a query: refused", "evil4 is not a query this page saved" in st(h), repr(st(h)))
    h.key("home", idle=0.4)
    key(h, "down", 2)
    h.key("enter", idle=1.8)
    arow("Q9g", "evil3 holds good boxes and an edited sentence with a semicolon: the boxes load, the sentence is dropped (1 part) and rebuilt from the boxes; the state line does not say edited, and no zzinj5 directory was made",
         sentence(h) == "list zq name" and "Edited by hand" not in state_line(h) and "1 part(s) did not pass" in st(h) and not on_disk(A1, "zzinj5"), repr((sentence(h), st(h), state_line(h))))
    tp(h, "l", 1.5)
    key(h, "down", 4)
    h.key("enter", idle=1.8)
    arow("Q9g1", "evil5 holds an edited sentence that passes the check: it is kept, and the state line says edited by hand", sentence(h) == "list zq name qty vertically" and "Edited by hand" in state_line(h), repr((sentence(h), state_line(h))))
    arow("Q9g2", "...and nothing was dropped: the status line says only loaded evil5", st(h).strip().endswith("loaded evil5") and "did not pass" not in st(h), repr(st(h)))
    tp(h, "s", 1.0)
    tp(h, "extra\r", 1.5)
    arow("Q9h", "S with 100 saved queries already: refused before any box, with the reason", "holds 100 at most" in st(h) and not re.search(r"Run this command|Write this record", h.text()) and count_q(A1) == "100", repr((st(h), count_q(A1))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q10():
    say("\n--- Q10: the results box")
    h = page(A1)
    choose(h, "zbig")
    tp(h, "r", 1.5)
    until(h, lambda t: "Ran:" in t and "are kept" in t, 40.0)
    info = h.line(5)
    m = re.search(r"(\d+) lines, the first 2000 are kept\.\s+Showing 1 to 33", info)
    arow("Q10", "zbig has 2100 records: the box says how many lines there were and that the first 2000 are kept (the number is over 2100: the verb's own headings, repeated at each page, and its count)", m is not None and 2100 < int(m.group(1)) < 2400 and g.plain(A1, ["COUNT zbig"])[-1].strip().startswith("2100 record(s) counted"), repr(info))
    h.key("end", idle=1.2)
    m = re.search(r"Showing (\d+) to 2000", h.line(5))
    last = [r for r in results_rows(h) if r.strip()]
    arow("Q10b", "End shows the last of the 2000 lines (Showing 1968 to 2000) and the rows are record ids of zbig", m is not None and m.group(1) == "1968" and last and re.match(r"^\s*b\d+\s*$", last[-1]) is not None, repr((h.line(5), last[-2:])))
    key(h, "pgup", 1)
    m = re.search(r"Showing (\d+) to (\d+)", h.line(5))
    arow("Q10c", "PgUp moves a page back: Showing 1935 to 1967", m is not None and (m.group(1), m.group(2)) == ("1935", "1967"), h.line(5))
    key(h, "home", 1)
    arow("Q10d", "Home goes back to the first line", re.search(r"Showing 1 to 33", h.line(5)) is not None, h.line(5))
    key(h, "right", 1)
    shifted = "from column 21" in h.line(5)
    key(h, "left", 1)
    arow("Q10d2", "Right moves the view 20 columns to the side (the info line says from column 21) and Left moves it back", shifted and "from column" not in h.line(5), h.line(5))
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()
    # escape sequences and a byte above 127 in the data
    h = page(A1)
    choose(h, "zesc")
    mark(h, 2)
    tp(h, "r", 1.5)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    T = h.text()
    lines = h.lines()
    er = next((i for i, l in enumerate(lines) if "Escred" in l), None)
    same_style = er is not None and h.style(er, lines[er].index("Escred")) == h.style(er, lines[er].index("Escred") + 3)
    arow("Q10e", "zesc holds a value with an escape sequence (ESC [ 31 m) and one with a byte above 127: the box shows Escred and hi.ok, no part of the sequence, and the cell after the sequence is NOT coloured (the terminal never saw it)",
         "Escred" in T and "hi.ok" in T and "[31m" not in T and same_style, repr(([r for r in results_rows(h) if r.strip()][:6], er)))
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()
    # the empty file
    h = page(A1)
    choose(h, "zqe")
    tp(h, "r", 1.5)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    ok, why = same_as_verb(h, A1, "list zqe", 1)
    arow("Q10f", "an empty file: the results say what a separate session says (0 record(s) listed)", ok and "0 record(s) listed" in norm_screen(h), why)
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()
    # a file that goes away under the page
    h = page(A1)
    choose(h, "zdel")
    g.plain(A1, ["DELETE.FILE zdel NO.QUERY"])
    gone = not on_disk(A1, "zdel")
    tp(h, "r", 1.5)
    until(h, lambda t: "Ran:" in t)
    want = verb_lines(A1, "list zdel")
    got = norm_screen(h)
    arow("Q10g", "the file is deleted by another session after it was chosen: the verb's own words are shown in the box (the page checked the sentence, not the file)", gone and want and all(l in got for l in want), repr((gone, want)))
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()
    # a select list that is waiting
    h = page(A1, "zq", pre=('SELECT zq WITH qty > "4"',))
    tp(h, "r", 1.5)
    until(h, lambda t: "Ran:" in t and "record(s) listed" in t)
    arow("Q10h", "a select list was waiting: the query used it (4 records, not 8) and the box says so", "4 record(s) listed" in norm_screen(h) and "A select list was active" in norm_screen(h), repr(h.line(5)))
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_q11():
    say("\n--- Q11: help, a small window, the file after the verb, the mouse, a piped session")
    h = page(A1, "zq")
    tb, order = files_rows(h)
    arow("Q11", "tool.query zq opens the file directly: it is marked in the File box, the Columns box has the focus and the sentence is list zq", tb.get("zq", ("",))[0] == "*" and "[*] Columns" in h.text() and sentence(h) == "list zq", repr((sentence(h), tb.get("zq"))))
    h.click(135, 2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("Q11b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("Q11c", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    h.key("esc", idle=1.0)
    mark(h, POS["name"])
    h.key("f5", idle=2.0)
    arow("Q11c2", "F5 reads the files and the dictionary again: the status line says so, and the column mark and the sentence (list zq name) are kept", "read the files and the dictionary again" in st(h) and sentence(h) == "list zq name" and [(c[0], c[2]) for c in cols_rows(h) if c[0]] == [("1", "name")], repr((st(h), sentence(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1, "nosuchfile")
    arow("Q11d", "tool.query with a name that is not one of the files: the page opens, chooses nothing and says so", "is not one of your files that have a dictionary" in st(h) and "Choose a file first" in sentence(h), repr((st(h), sentence(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1)
    tb, order = files_rows(h)
    third = order[2]
    h.click(10, 4)                                  # the third row of the File box
    h.key("enter", idle=1.4)
    tb2, order2 = files_rows(h)
    ok_third = tb2.get(third, ("",))[0] == "*" or (third == "&zbad&" and "does not give to a command" in st(h))
    arow("Q11e", "the mouse: a click on the third row of the File box moves the cursor there, and Enter chooses that file (%s)" % third, ok_third, repr((third, st(h), order[:4])))
    h.click(80, 4)
    arow("Q11f", "a click inside the Conditions box gives it the focus", "[*] Conditions" in h.text(), h.text()[:300])
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    SCREEN[0] = h
    h.typed("tool.query\r", idle=3.0)
    T = h.text()
    arow("Q11g", "a window under 140 by 43 gets no page", "The sentence" not in T and "Conditions" not in T, T[-300:])
    h.end()
    # NOT HELD: a PIPED session that types tool.query (and tool.keys, which is committed) never ends - it hangs without a word; that is the base's ($tk_open), see the report


def section_q12():
    say("\n--- Q12: delete from the saved list needs the name typed")
    h = page(A1)
    choose(h, "zq")
    arow("Q12", "fill01 is a saved query before the delete", read_rec(A1, "fill01") is not None and read_rec(A1, "fill01").startswith("query1"), repr(read_rec(A1, "fill01")))
    tp(h, "l", 1.5)
    key(h, "down", 5)                               # evil1 .. evil5, then fill01
    tp(h, "x", 1.5)
    T = boxtext(h)
    arow("Q12a", "X shows the box: delete fill01 from &queries&, not a command, with Run and Cancel", "delete fill01 from &queries&" in T and "not a command" in T, T[-400:])
    tp(h, "r", 1.2)
    tp(h, "wrong\r", 1.8)
    rec = read_rec(A1, "fill01")
    arow("Q12b", "a wrong name typed deletes nothing: fill01 is still in the file", rec is not None and rec.startswith("query1"), repr(rec))
    if "Saved queries" not in h.text():
        tp(h, "l", 1.5)
        key(h, "down", 5)
    tp(h, "x", 1.5)
    tp(h, "r", 1.2)
    tp(h, "fill01\r", 2.0)
    arow("Q12c", "the right name typed deletes it: the record is gone and 99 remain; the others are untouched (fill02 and evil1 are still there)",
         read_rec(A1, "fill01") == "norecord" and count_q(A1) == "99" and (read_rec(A1, "fill02") or "").startswith("query1") and (read_rec(A1, "evil1") or "").startswith("query1"), repr((read_rec(A1, "fill01"), count_q(A1))))
    h.key("ctrl-q", idle=1.2)
    h.end()


SECTIONS = [("q1", section_q1), ("q2", section_q2), ("q3", section_q3), ("q4", section_q4), ("q5", section_q5), ("q6", section_q6), ("q7", section_q7), ("q8", section_q8),
            ("q9", section_q9), ("q10", section_q10), ("q11", section_q11), ("q12", section_q12)]


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-query.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    try:
        sh.setup("sandbox-tool-query.py")
        setup_query()
        run = [s for s, _f in SECTIONS]
        if mutant is not None:
            mutate(mutant)
            run = MUTANTS[mutant][3]
            say("sandbox-tool-query: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        for sid, fn in SECTIONS:
            if sid in run:
                fn()
        if os.path.exists(LEAK):
            os.remove(LEAK)
    finally:
        sh.teardown()
    say("\nsandbox-tool-query: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted(set(FAILED_IDS))
        ok = want == got
        say("sandbox-tool-query: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
