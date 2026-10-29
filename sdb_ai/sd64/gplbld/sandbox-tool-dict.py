#!/usr/bin/env python3
#
# sandbox-tool-dict.py - TOOL.DICT, the dictionary of a file on one screen ($tool_dict, S.75 DV2), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-dict.py <dir> [--build] [--sections=a,b] [--mutants | --mutant=NAME]
#   (--sections= runs some sections only, of: files items new refused try compile edit delete odd indices other; the fixtures are always made)
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutants every runtime mutant is made in turn on the SANDBOX'S OWN COPY of the page (never on the tree) and run through the section its rows are in;
# exit 0 means each was killed by exactly its own rows (MUTANTS).  --mutant=NAME does one.  The sandbox's copy of the page is taken from the tree at the start of every run.
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand: zzdc1 with dict-edit ON and zzdc2 with dict-edit OFF (voc-edit and bp-edit are ON in both, so the fixtures
# can be built and a program compiled).  Each is built the same way while dict-edit is on, and zzdc2 is then switched off: files `cust` (a dictionary of every kind of item the page shows -
# D, A, I compiled and not compiled, a multivalued one with an association, X text, a conversion, an id with a capital - and two records), `ixf` (four items, one index defined and not
# built, one made in capitals) and `nodic` (a VOC entry for a file with no dictionary).  An ORDINARY session (sd -a<account>, as the sandbox user, not an administrator) types TOOL.DICT.
#
# THE INSTRUMENT.  Every outcome is read from the DISK or from SD, not from what the page said: the record of an item is read by a separate ordinary session (bp/zzdrd: the first ten
# fields and whether the object code is there), the indices by a separate session's LIST.INDEX, and what the page lists is compared with both.  A row that says "nothing was written /
# deleted / built" is judged by the same.
#
#   D1   the files: the chooser lists the account's files with their dictionaries; Enter opens one; a file with no dictionary is said so; a file named after the verb is opened (lower
#        or upper case), anything the page cannot give to a command or that is not a file is said politely and the chooser is shown; the input ending ends the page (no spin)
#   D2   the items: types, fields, headings, formats in id order; the item under the cursor in words for each kind; the filter; the gate line for dict-edit on and off; a click
#   D3   N makes an item in the account with dict-edit ON: each wrong answer is refused and asked again; Cancel is the default; Run writes the record (D, D multivalued, A, I - the
#        exact fields, read from the disk)
#   D4   N in the account with dict-edit OFF: the box says the write will be refused, Run is met by the kernel's own words and NO record appears  [mutant no-edit-check]
#   D5   T tries an item on a record: D, A, I, multivalued, a conversion and format; a missing record, an item not compiled, an item that holds no value
#   D6   C compiles an I item: only A S I; Cancel is the default; Run puts the object code in the record (disk), and T then works; compiling is not held back by dict-edit
#   D7   E hands the terminal to the IDE on the item ('ide dict file id', S.88 stage C; it was SED - re-pointed 28 Oct 26, NOT RUN) and the page comes back; a change saved by the IDE is on the disk (dict-edit ON) and is refused and not on the disk (OFF)
#   D8   D deletes: Cancel is the default; the wrong id typed deletes nothing; the right id deletes (disk); with dict-edit OFF the verb's own refusal and the item stays  [mutant delete-no-typed-name]
#   D9   an id with a capital, a file with a dollar in its name: listed and described, and E, D and C are refused with the verb to type; the file is untouched
#   D10  the indices: the pane lists them with built / not built; N picks an item and CREATE.INDEX defines it and BUILD.INDEX builds it (Cancel is the default; one that has an index is refused); B builds one;
#        D deletes one after its name is typed and leaves the others; L hands the terminal to LIST.INDEX; an index made in capitals is built and deleted by its lower-case name  [mutant delete-index-all]
#   D11  F1 and the [?] reach the help box; Tab and I and Esc move between the panes; F goes back to the files; F5 reads again; a window under 140 by 43 gets no page
import importlib.util
import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_dict", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zzdc1", "zzdc2"
ME = os.environ.get("USER") or os.getlogin()
PAGE = "tool_dict"
SRC = os.path.join(TREE, "sdsys", "gpl.bp", PAGE)

SCREEN = [None]      # the pty session of the section running: a failed row prints what it was looking at


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


WRITE_WALL = ("   if not(kernel(K$EDIT.OK, dpath)) then\n      msg = edit_msg(kernel(K$EDIT.KIND, dpath))\n      close dv\n      return\n   end\n   read old from dv, nid then")

MUTANTS = {
    # name: (old text of the sandbox's page, new text, the base row ids that must fail and no others, the section that runs)
    "no-edit-check": (WRITE_WALL, "   read old from dv, nid then", ["D4"], "refused"),
    "delete-no-typed-name": ("call $tk_confirm(sent, lines, iid, res, cmsg)", "call $tk_confirm(sent, lines, '', res, cmsg)", ["D8"], "delete"),
    "delete-index-all": ("sent = 'delete.index ' : fn : ' ' : xn", "sent = 'delete.index ' : fn : ' all'", ["D10"], "indices"),
    "keyword-wall-open": ("if upcase(kwr<1>[1, 1]) = 'K' then okname = @false", "if 0 then okname = @false", ["D9"], "odd"),
}


def box():
    return sh.BOX


def acct_dir(a):
    return os.path.join(box(), "user_accounts", a)


def reg_record(name, dict_on):
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", "yes", "yes", "yes" if dict_on else "no", "", "", "no", "", "", ""]


def compile_page():
    """the page of THIS TREE is put into the sandbox's gpl.bp and compiled there"""
    with open(SRC, encoding="latin-1") as f:
        g.put(os.path.join(sh.SYS, "gpl.bp", PAGE), f.read())
    out = adm("BASIC gpl.bp " + PAGE)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("%s did not compile in the sandbox:\n%s" % (PAGE, "\n".join(out[-8:])))


def mutate(name):
    old, new, _kills, _sec = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", PAGE)
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = adm("BASIC gpl.bp " + PAGE)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant %s did not compile:\n%s" % (name, "\n".join(out[-8:])))


# ------------------------------------------------------------------------------------------------------------------------------ the fixtures and the evidence

def fixture_program(a):
    path = acct_dir(a)
    L = []

    def w(dictname, itemid, *fields):
        L.append("   write " + ":@fm:".join("'%s'" % f for f in fields) + " on %s, '%s'" % (dictname, itemid))
    L += ["   open 'DICT cust' to d else crt 'ZZDF no dict cust' ; stop", "   open 'cust' to f else crt 'ZZDF no cust' ; stop",
          "   open 'DICT ixf' to d2 else crt 'ZZDF no dict ixf' ; stop", "   open 'ixf' to f2 else crt 'ZZDF no ixf' ; stop",
          "   open 'VOC' to v else crt 'ZZDF no voc' ; stop"]
    w("d", "name", "D", "1", "", "Name", "20L", "S")
    w("d", "city", "A", "2", "City", "", "", "", "", "", "L", "12")
    w("d", "amt", "D", "3", "", "Amt", "10R", "S")
    w("d", "dbl", "I", "AMT * 2", "", "Double", "10R", "S")
    L.append("   write 'D':@fm:'4':@fm:'':@fm:'Tags':@fm:'10L':@fm:'M':@fm:'LINE' on d, 'tags'")
    w("d", "note", "X", "some text")
    w("d", "dt", "D", "5", "D2/", "When", "10L", "S")
    w("d", "uncomp", "I", "AMT + 1", "", "Plus", "8R", "S")
    w("d", "UpCase", "D", "1", "", "Up", "10L", "S")
    w("d", "ed1", "X", "edit me")
    w("d", "del1", "X", "delete me")
    L.append("   write 'Smith':@fm:'Oslo':@fm:'12.5':@fm:'a':@vm:'b':@vm:'c':@fm:'1' on f, 'c1'")
    L.append("   write 'Jones':@fm:'Rome':@fm:'7' on f, 'c2'")
    w("d2", "f1", "D", "1", "", "First", "10L", "S")
    w("d2", "f2", "D", "2", "", "Second", "8R", "S")
    w("d2", "f3", "X", "text")
    w("d2", "upname", "D", "1", "", "Up", "10L", "S")
    L.append("   write 'x':@fm:'5' on f2, 'i1'")
    L.append("   write 'y':@fm:'10' on f2, 'i2'")
    L.append("   write 'F':@fm:'%s/cust' on v, 'nodic'" % path)
    L += ["   crt 'ZZDF done'", "end", ""]
    return "\n".join(L)


READER = "\n".join([
    "   fl = field(trim(@sentence), ' ', 4)",
    "   it = field(trim(@sentence), ' ', 5)",
    "   open 'DICT', fl to d else crt 'DRD[nodict]' ; stop",
    "   if it = '*' then",
    "      select d to 9",
    "      s = ''",
    "      loop",
    "         readnext id from 9 else exit",
    "         s := (if s = '' then '' else '|') : id",
    "      repeat",
    "      crt 'DRDIDS[' : s : ']'",
    "      stop",
    "   end",
    "   read r from d, it then",
    "      n = dcount(r, @fm)",
    "      if n > 10 then n = 10",
    "      s = ''",
    "      for k = 1 to n",
    "         s := (if k = 1 then '' else '|') : r<k>",
    "      next k",
    "      crt 'DRD[' : s : ']'",
    "      crt 'DRDOBJ[' : (if r<16> # '' then 1 else 0) : ']'",
    "   end else",
    "      crt 'DRD[absent]'",
    "   end",
    "end", ""])


def build_acct(a, dict_final):
    q = sh.g
    q.FIXTURES[a] = ("no", "no")
    q.build_account(a)
    q.reg_write(a, reg_record(a, True))
    q.put(os.path.join(acct_dir(a), "bp", "zzdfix"), fixture_program(a))
    q.put(os.path.join(acct_dir(a), "bp", "zzdrd"), READER)
    out = q.plain(a, ["CREATE.FILE cust", "CREATE.FILE ixf", "BASIC bp zzdfix zzdrd", "RUN bp zzdfix", "COMPILE.DICT cust dbl", "CREATE.INDEX ixf f1", "CREATE.INDEX ixf UPNAME", "BUILD.INDEX ixf UPNAME"])
    if not has(out, r"^ZZDF done$"):
        bail("the fixture files of %s were not made:\n%s" % (a, "\n".join(out[-14:])))
    if not has(out, r"Added index for UPNAME") or not has(out, r"Added index for f1"):
        bail("the fixture indices of %s were not made:\n%s" % (a, "\n".join(out[-14:])))
    q.reg_write(a, reg_record(a, dict_final))


def setup_files():
    build_acct(A1, True)
    build_acct(A2, False)
    compile_page()
    a1 = ids(A1, "cust")
    if a1 is None or sorted(a1) != sorted(["@id", "name", "city", "amt", "dbl", "tags", "note", "dt", "uncomp", "UpCase", "ed1", "del1"]):
        bail("the fixture dictionary of cust in %s holds %r" % (A1, a1))
    d = item(A1, "cust", "dbl")
    if d is None or d[1] != 1:
        bail("the fixture item dbl is not compiled: %r" % (d,))


def item(account, fl, it):
    """the item as the DISK has it, read by a SEPARATE ordinary session: (its first ten fields as a list, 1 when the record holds object code), or None when the record is absent"""
    out = g.plain(account, ["RUN bp zzdrd %s %s" % (fl, it)])
    rec = obj = None
    for ln in out:
        m = re.match(r"^DRD\[(.*)\]$", ln.strip())
        if m:
            rec = m.group(1)
        m = re.match(r"^DRDOBJ\[(\d)\]$", ln.strip())
        if m:
            obj = int(m.group(1))
    if rec is None:
        raise RuntimeError("zzdrd printed no DRD line for %s %s:\n%s" % (fl, it, "\n".join(out[-6:])))
    if rec in ("absent", "nodict"):
        return None
    return rec.split("|"), obj


def ids(account, fl):
    out = g.plain(account, ["RUN bp zzdrd %s *" % fl])
    for ln in out:
        m = re.match(r"^DRDIDS\[(.*)\]$", ln.strip())
        if m:
            return m.group(1).split("|") if m.group(1) else []
    return None


def idx_state(account, fl):
    """the indices of the file as a SEPARATE session's LIST.INDEX says: {lower-case name: Y or N}"""
    out = g.plain(account, ["LIST.INDEX %s ALL" % fl])
    res = {}
    for ln in out:
        m = re.match(r"^(\S+)\s+([YN])\s+[A-Z]\s+(Yes|No)\s+", ln.strip())
        if m:
            res[m.group(1).lower()] = m.group(2)
    return res


# ------------------------------------------------------------------------------------------------------------------------------ the pseudo-terminal

def page(account, arg="", cols=140, rows=43):
    h = H(account=account, cols=cols, rows=rows)
    SCREEN[0] = h
    h.typed("tool.dict%s\r" % ((" " + arg) if arg else ""), idle=3.5)
    return h


def until(h, pred, secs=20.0):
    """a verb that the page runs prints nothing while it runs, so a wait for idle output is not a wait for the page: pump the pty until the screen satisfies pred"""
    for _ in range(int(secs / 0.5)):
        if pred(h.text()):
            return True
        h.s._pump(0.5)
    return pred(h.text())


def flat(h):
    return re.sub(r"[|\s]+", " ", h.text())


def rawflat(h):
    """the screen with runs of blanks made one, the bars kept (a value printed between bars is looked for with its bars)"""
    return re.sub(r" +", " ", h.text())


def st(h):
    return h.line(40)


def ftable(h):
    """{name: (kind, dictionary, items, indices)} from the rows of the files pane"""
    out, order = {}, []
    for n in range(3, 19):
        l = h.line(n)
        name = l[3:33].strip()
        if name:
            order.append(name)
            out[name] = (l[33:45].strip(), l[45:57].strip(), l[57:65].strip(), l[65:74].strip())
    return out, order


def itable(h):
    """{id: (type, field, heading, format, conversion, s/m, association, expression)} from the rows of the items pane"""
    out, order = {}, []
    for n in range(3, 19):
        l = h.line(n)
        name = l[3:29].strip()
        if name:
            order.append(name)
            out[name] = (l[29:34].strip(), l[34:43].strip(), l[43:65].strip(), l[65:73].strip(), l[73:85].strip(), l[85:89].strip(), l[89:101].strip(), l[101:135].strip())
    return out, order


def xtable(h):
    """{name: (built, type, nulls, s/m, fmt, case, field)} from the rows of the indices pane"""
    out, order = {}, []
    for n in range(3, 19):
        l = h.line(n)
        name = l[3:27].strip()
        if name:
            order.append(name)
            out[name] = (l[27:33].strip(), l[33:38].strip(), l[38:44].strip(), l[44:49].strip(), l[49:54].strip(), l[54:60].strip(), l[60:134].strip())
    return out, order


def lower(h):
    return [h.line(n)[3:138].rstrip() for n in range(24, 39)]


def lowtxt(h):
    return " ".join(x.strip() for x in lower(h))


def filt(h, text):
    h.typed("/", idle=0.8)
    h.typed(text + "\r", idle=1.0)


def goto(h, it):
    """the cursor on the item `it`: the filter keeps the ids that hold it and the cursor goes down to it"""
    filt(h, it)
    tb, order = itable(h)
    for _ in range(order.index(it) if it in order else 0):
        h.key("down", idle=0.4)


def boxtext(h):
    """the words inside the confirm box on the screen, one line (the page behind the box shows through at its sides and is left out); the whole screen when there is no box"""
    rows = [h.line(n) for n in range(43)]
    top = next((n for n, l in enumerate(rows) if re.search(r"Run this command\?|Write this record\?", l)), None)      # 26 Oct 26 (faults): N's box is titled by what it does
    if top is None:
        return re.sub(r"[|\s]+", " ", h.text())
    s0, s1 = rows[top].index("+"), rows[top].rindex("+")
    inner = []
    for n in range(top + 1, 43):
        if rows[n][s0:s0 + 1] == "+":
            break
        inner.append(rows[n][s0 + 1:s1])
    return re.sub(r"[|\s]+", " ", " ".join(inner))


def new_item_d(h, nid, loc, head, just, width, conv, sm, assoc=""):
    """N, the id, Data, and every answer: an answer that is the default is accepted with Enter, any other is typed over it (Ctrl-U empties the entry first)"""
    h.typed("n", idle=1.0)
    h.typed(nid + "\r", idle=1.0)
    h.typed("d", idle=1.2)
    h.typed(loc + "\r", idle=0.8)
    h.typed(head + "\r", idle=0.8)
    h.typed(("\x15" + just if just != "L" else "") + "\r", idle=0.8)
    h.typed(("\x15" + width if width != "10" else "") + "\r", idle=0.8)
    h.typed(conv + "\r", idle=0.8)
    h.typed(("\x15" + sm if sm != "S" else "") + "\r", idle=1.2)
    if sm == "M":
        h.typed(assoc + "\r", idle=1.2)


def pipe_end(account, lines, deadline=10.0):
    """the page in a session whose input is a pipe that is then closed: it must end by itself, without using the CPU for as long as it is let run.  (ended, wall, cpu, output)"""
    env = dict(os.environ, SD_CONFIG=os.path.join(box(), "sd.conf"))
    env.pop("SDTEST_ADMIN", None)
    outf = os.path.join(box(), "dict-eof.out")
    body = "TERM 140,43\n" + "".join(l + "\n" for l in lines)
    say("    > pipe session of %s: %r then the pipe is closed" % (account, body))
    with open(outf, "wb") as fo:
        p = subprocess.Popen([g.SD, "-a" + account], cwd=acct_dir(account), env=env, stdin=subprocess.PIPE, stdout=fo, stderr=subprocess.STDOUT)
        p.stdin.write(body.encode())
        p.stdin.close()
        t0 = time.time()
        ended = True
        while True:
            wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
            if wpid:
                break
            if time.time() - t0 > deadline:
                ended = False
                os.kill(p.pid, signal.SIGHUP)
                t1 = time.time()
                while time.time() - t1 < 3.0:
                    wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
                    if wpid:
                        break
                    time.sleep(0.05)
                else:
                    os.kill(p.pid, signal.SIGKILL)
                    _w, _status, ru = os.wait4(p.pid, 0)
                break
            time.sleep(0.05)
        p.returncode = 0
    wall = time.time() - t0
    with open(outf, "rb") as fi:
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", fi.read().decode("latin-1"))
    return ended, wall, ru.ru_utime + ru.ru_stime, text


# ------------------------------------------------------------------------------------------------------------------------------ the sections

def section_files():
    say("\n--- D1: the files, and a file named after the verb")
    h = page(A1)
    T = h.text()
    if "The file under the cursor" not in T:
        dump(h)
        bail("tool.dict never drew its page in an ordinary account, so no row below can be believed")
    tb, order = ftable(h)
    arow("D1", "the page draws for an ordinary account in the files pane, for the audience %s@%s (the right end of row 0), titled with the account, and the status line names the pane [Files]" % (ME, A1),
         re.search(r"tool\.dict\s+%s@%s" % (re.escape(ME), A1), h.line(0)) is not None and "Files of %s" % A1 in T and st(h).startswith("[Files]"), repr((h.line(0)[100:], st(h)[:30])))
    cust_ids = ids(A1, "cust")
    arow("D1b", "cust, ixf and nodic are listed in name order: cust and ixf with a dictionary (cust holds the %d items the disk says), nodic with none" % len(cust_ids or []),
         all(n in tb for n in ("cust", "ixf", "nodic")) and order == sorted(order) and tb["cust"][1] == "yes" and tb["cust"][2] == str(len(cust_ids or [])) and tb["ixf"][1] == "yes"
         and tb["ixf"][2] == str(len(ids(A1, "ixf") or [])) and tb["nodic"][1] == "none" and tb["nodic"][2] == "", repr((tb.get("cust"), tb.get("ixf"), tb.get("nodic"))))
    arow("D1c", "the indices column: ixf has 2 (one defined, one made in capitals), cust has 0", tb["ixf"][3] == "2" and tb["cust"][3] == "0", repr((tb["ixf"], tb["cust"])))
    filt(h, "nodic")
    h.key("enter", idle=1.5)
    arow("D1d", "Enter on nodic (no dictionary) stays in the files pane and says there is nothing to show", st(h).startswith("[Files]") and "nodic has no dictionary" in st(h), repr(st(h)))
    h.key("esc", idle=1.0)
    filt(h, "cust")
    h.key("enter", idle=2.0)
    tb, order = itable(h)
    arow("D1e", "Enter on cust opens its dictionary: the items pane, titled with the file, the items in id order as the disk has them",
         "Dictionary of cust" in h.text() and st(h).startswith("[Items]") and sorted(order) == sorted(cust_ids or []) and "@id" in order, repr((order, cust_ids)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1, "cust")
    arow("D1f", "a file named after the verb is opened at once: tool.dict cust shows the items pane", "Dictionary of cust" in h.text() and st(h).startswith("[Items]") and "dbl" in itable(h)[1], repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1, "CUST")
    arow("D1g", "...in capitals too (the name is put in lower case)", "Dictionary of cust" in h.text() and st(h).startswith("[Items]"), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1, "nosuch")
    arow("D1h", "a name that is not one of the account's files is said politely and the files pane is shown", "Files of %s" % A1 in h.text() and "nosuch is not a file in this account" in st(h), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1, "cu$t")
    arow("D1i", "a name with a character the page does not give to a command is said politely and the files pane is shown", "Files of %s" % A1 in h.text() and "a file name is made of a-z" in st(h), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A1, "nodic")
    arow("D1j", "a file with no dictionary named after the verb: the files pane and the reason", "Files of %s" % A1 in h.text() and "nodic has no dictionary" in st(h), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    ended, wall, cpu, text = pipe_end(A1, ["tool.dict cust"])
    arow("D1k", "the input ending ends the page by itself (wall %.1f s, cpu %.1f s) after it drew its first screen" % (wall, cpu), ended and cpu < 2.0 and "Dictionary of cust" in text, repr((ended, wall, cpu, text[-200:])))


def section_items():
    say("\n--- D2: the items, the item under the cursor, the filter, the gate")
    h = page(A1, "cust")
    tb, order = itable(h)
    arow("D2", "the items of cust as the disk has them: types D A I X, the field, heading, format; dbl shows computed and its expression, tags is multivalued with its association, dt has its conversion",
         tb["amt"][:4] == ("D", "3", "Amt", "10R") and tb["name"][:4] == ("D", "1", "Name", "20L") and tb["city"][:4] == ("A", "2", "City", "12L") and tb["dbl"][:4] == ("I", "computed", "Double", "10R") and tb["dbl"][7] == "AMT * 2"
         and tb["tags"][5:7] == ("M", "LINE") and tb["note"][0] == "X" and tb["note"][7] == "some text" and tb["dt"][4] == "D2/" and tb["@id"][:2] == ("D", "0"), repr(tb))
    arow("D2b", "the gate line says dict-edit on for this account", "Your gate:  dict-edit on" in h.line(19), repr(h.line(19)[:80]))
    goto(h, "amt")
    B = lowtxt(h)
    arow("D2c", "amt in words: a data field, field 3 of each record, heading Amt, 10 wide right-justified, no conversion, single valued, and the record as the disk has it",
         "amt - a data field (D)" in B.replace("  ", " ") and "Shows field 3 of each record." in B and 'Column heading "Amt".' in B and "Printed 10 characters wide, right-justified." in B and "No conversion" in B and "Single valued." in B
         and "Record: 1=D 2=3 3=- 4=Amt 5=10R 6=S" in B, B[:300])
    h.key("esc", idle=1.0)
    goto(h, "dbl")
    B = lowtxt(h)
    arow("D2d", "dbl in words: a computed field, its expression, and that it is compiled", "a computed field (I-type)" in B and "AMT * 2" in B and "Compiled: the query processor runs the compiled form." in B, B[:300])
    h.key("esc", idle=1.0)
    goto(h, "uncomp")
    B = lowtxt(h)
    arow("D2e", "uncomp in words: not compiled yet, and C compiles it", "Not compiled yet: C compiles it" in B and "AMT + 1" in B, B[:300])
    h.key("esc", idle=1.0)
    goto(h, "tags")
    B = lowtxt(h)
    arow("D2f", "tags in words: multivalued, in the association LINE", "Multivalued: the field holds several values." in B and "Association LINE" in B, B[:300])
    h.key("esc", idle=1.0)
    goto(h, "city")
    B = lowtxt(h)
    arow("D2g", "city in words: an A-type field in the Pick layout, field 2, heading City, 12 wide left-justified", "an A-type field, the Pick layout (A)" in B and "Shows field 2 of each record." in B and 'Column heading "City".' in B and "12 characters wide, left-justified" in B, B[:300])
    h.key("esc", idle=1.0)
    goto(h, "dt")
    B = lowtxt(h)
    arow("D2h", "dt in words: converted for display with D2/, a date", "Converted for display with D2/ (a date)." in B, B[:300])
    h.key("esc", idle=1.0)
    goto(h, "note")
    B = lowtxt(h)
    arow("D2i", "note in words: text, not a field a query reads", "text (X)" in B and "A query does not read it as a field." in B, B[:300])
    h.key("esc", idle=1.0)
    filt(h, "amt")
    tb, order = itable(h)
    arow("D2j", "the filter keeps the ids that hold the text: only amt holds 'amt', and the summary says so", order == ["amt"] and '1 with "amt" in the id' in h.line(19), repr((order, h.line(19)[:80])))
    h.key("esc", idle=1.0)
    tb, order = itable(h)
    arow("D2k", "Esc clears the filter: every item is back", len(order) >= 12 and "dbl" in order, repr(order))
    h.click(10, 5, idle=1.0)
    third = itable(h)[1][2]
    arow("D2l", "a click on the third row (%s) puts the cursor there: the box under the list describes it" % third, lowtxt(h).replace("  ", " ").startswith(third + " - "), lowtxt(h)[:200])
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2, "cust")
    arow("D2m", "the gate line for an account with dict-edit OFF says off", "Your gate:  dict-edit off" in h.line(19), repr(h.line(19)[:80]))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_new():
    say("\n--- D3: N makes an item in an account with dict-edit ON")
    h = page(A1, "cust")
    h.typed("n", idle=1.0)
    h.typed("amt\r", idle=1.2)
    arow("D3", "an id that is taken is refused and asked again (the question stays, with the reason in its prompt)", "that id is taken" in h.text(), flat(h)[-300:])
    h.key("esc", idle=1.2)
    arow("D3b", "Esc leaves the question: nothing is written", "nothing written" in st(h), repr(st(h)))
    h.typed("n", idle=1.0)
    h.typed("UPCASE\r", idle=1.2)
    arow("D3b2", "an id that exists in ANOTHER CASE is taken too (UPCASE against the item UpCase): no id can exist in two casings", "that id is taken" in h.text(), flat(h)[-300:])
    h.key("esc", idle=1.2)
    h.typed("n", idle=1.0)
    h.typed("Bad$\r", idle=1.2)
    arow("D3c", "an id with a dollar is refused (a-z, 0-9, dot, dash, underscore)", "a-z, 0-9, dot, dash, underscore" in h.text(), flat(h)[-300:])
    h.key("esc", idle=1.2)
    h.typed("n", idle=1.0)
    h.typed("zzd\r", idle=1.0)
    h.typed("d", idle=1.2)
    h.typed("x\r", idle=1.2)
    t1 = "a whole number from 0 to 9999" in h.text()
    h.typed("\x15" + "10000\r", idle=1.2)
    t2 = "a whole number from 0 to 9999" in h.text()
    h.typed("\x15" + "7\r", idle=1.0)
    h.typed("Zed\r", idle=1.0)
    h.typed("\x15q\r", idle=1.2)
    t3 = "L, R or T" in h.text()
    h.typed("\x15r\r", idle=1.0)
    h.typed("\x15" + "0\r", idle=1.2)
    t4 = "a whole number from 1 to 200" in h.text()
    h.typed("\x15" + "12\r", idle=1.0)
    h.typed("XYZ\r", idle=1.2)
    t5 = "SD does not know this conversion" in h.text()
    h.typed("\x15D2/\r", idle=1.0)
    h.typed("\x15z\r", idle=1.2)
    t6 = "S or M" in h.text()
    h.typed("\x15s\r", idle=1.5)
    arow("D3d", "every wrong answer is refused with its reason and asked again: a letter or 10000 for the field number, Q for the justification, 0 for the width, XYZ for the conversion, Z for single or multi",
         t1 and t2 and t3 and t4 and t5 and t6, repr((t1, t2, t3, t4, t5, t6)))
    bt = boxtext(h)
    arow("D3e", "the box shows the command line and the WHOLE record field by field (type D, field 7, conversion D2/, heading Zed, format 12R, S), and that nothing else changes",
         "write the item zzd in the dictionary of cust" in bt and "1 type D" in bt and "2 field number 7" in bt and "3 conversion D2/" in bt and "4 heading Zed" in bt and "5 format 12R" in bt and "6 single/multi S" in bt
         and "Nothing else changes" in bt and "expected to be refused" not in bt, bt[:600])
    h.key("enter", idle=1.5)
    arow("D3f", "Enter is Cancel: nothing is written - the disk has no item zzd and the status says nothing was run", item(A1, "cust", "zzd") is None and "nothing was run" in st(h), repr((item(A1, "cust", "zzd"), st(h))))
    new_item_d(h, "zzd", "7", "Zed", "R", "12", "D2/", "S")
    h.typed("r", idle=2.5)
    d = item(A1, "cust", "zzd")
    tb, order = itable(h)
    arow("D3g", "Run: the record is on the DISK exactly (D, 7, D2/, Zed, 12R, S), the list has it with the cursor on it, and the status says it was written",
         d is not None and d[0] == ["D", "7", "D2/", "Zed", "12R", "S"] and tb.get("zzd", ("",))[:5] == ("D", "7", "Zed", "12R", "D2/") and "wrote the item zzd" in st(h), repr((d, tb.get("zzd"), st(h))))
    arow("D3h", "...and it is described: field 7, heading Zed, 12 wide right-justified, converted with D2/", "Shows field 7 of each record." in lowtxt(h) and "12 characters wide, right-justified" in lowtxt(h), lowtxt(h)[:200])
    new_item_d(h, "zze", "4", "T2", "L", "10", "", "M", "LINE")
    arow("D3i", "a multivalued item asks for its association; the box shows it as field 7", "7 association LINE" in boxtext(h) and "6 single/multi M" in boxtext(h), boxtext(h)[:500])
    h.typed("r", idle=2.5)
    d = item(A1, "cust", "zze")
    arow("D3j", "Run: the multivalued item is on the disk (D, 4, '', T2, 10L, M, LINE)", d is not None and d[0] == ["D", "4", "", "T2", "10L", "M", "LINE"], repr(d))
    # an A-type item: location, heading, association, conversion, correlative, justification, width
    h.typed("n", idle=1.0)
    h.typed("newa\r", idle=1.0)
    h.typed("a", idle=1.2)
    h.typed("2\r", idle=0.8)
    h.typed("Cty\r", idle=0.8)
    h.typed("CTY\r", idle=0.8)
    h.typed("\r", idle=0.8)
    h.typed("\r", idle=0.8)
    h.typed("\x15r\r", idle=0.8)
    h.typed("\x15" + "14\r", idle=1.5)
    bt = boxtext(h)
    arow("D3k", "an A-type item: the box lists it in the Pick layout (3 heading, 4 association, 9 justification, 10 width)", "1 type A" in bt and "3 heading Cty" in bt and "4 association CTY" in bt and "9 justification R" in bt and "10 width 14" in bt, bt[:600])
    h.typed("r", idle=2.5)
    d = item(A1, "cust", "newa")
    arow("D3l", "Run: the A item is on the disk with the Pick layout (A, 2, Cty, CTY, -, -, -, -, R, 14)", d is not None and d[0] == ["A", "2", "Cty", "CTY", "", "", "", "", "R", "14"], repr(d))
    # an I-type item: the expression
    h.typed("n", idle=1.0)
    h.typed("newi\r", idle=1.0)
    h.typed("i", idle=1.2)
    h.typed("AMT + 5\r", idle=1.0)
    h.typed("Plus5\r", idle=0.8)
    h.typed("\x15r\r", idle=0.8)
    h.typed("\x15" + "8\r", idle=0.8)
    h.typed("\r", idle=0.8)
    h.typed("\r", idle=1.5)
    bt = boxtext(h)
    arow("D3m", "an I item: the box shows the expression as field 2 and says it is not compiled yet", "2 expression AMT + 5" in bt and "4 heading Plus5" in bt and "5 format 8R" in bt and "It is not compiled yet" in bt, bt[:600])
    h.typed("r", idle=2.5)
    d = item(A1, "cust", "newi")
    arow("D3n", "Run: the I item is on the disk (I, AMT + 5, '', Plus5, 8R, S) with no object code yet", d is not None and d[0] == ["I", "AMT + 5", "", "Plus5", "8R", "S"] and d[1] == 0, repr(d))
    # an id typed with capitals is made in lower case
    h.typed("n", idle=1.0)
    h.typed("ZzCap\r", idle=1.0)
    h.typed("d", idle=1.2)
    for k in range(6):
        h.typed("2\r" if k == 0 else "\r", idle=(0.8 if k < 5 else 1.5))
    bt = boxtext(h)
    h.typed("r", idle=2.5)
    d = item(A1, "cust", "zzcap")
    arow("D3p", "an id typed with capitals (ZzCap) is made in lower case: the box names zzcap and the disk has the record zzcap (D, 2, '', '', 10L, S)", "write the item zzcap in the dictionary of cust" in bt and d is not None and d[0] == ["D", "2", "", "", "10L", "S"], repr((bt[:200], d)))
    # nothing else changed: the other items are as they were
    arow("D3o", "the items that were there are as they were (amt and dbl read from the disk)", item(A1, "cust", "amt")[0] == ["D", "3", "", "Amt", "10R", "S"] and item(A1, "cust", "dbl")[0][:2] == ["I", "AMT * 2"], repr((item(A1, "cust", "amt"), item(A1, "cust", "dbl"))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_refused():
    say("\n--- D4: N in an account with dict-edit OFF")
    before = ids(A2, "cust")
    h = page(A2, "cust")
    new_item_d(h, "refus1", "7", "Nope", "L", "10", "", "S")
    bt = boxtext(h)
    arow("D4", "the box says the write is expected to be refused, with the kernel's own reason (dict.edit, modify.account <account> dict-on)", "expected to be refused" in bt and "dict.edit" in bt and "dict-on" in bt, bt[:700])
    h.typed("r", idle=2.5)
    arow("D4b", "Run: the status line carries the kernel's own refusal (a dictionary can only be changed by an account that has dict.edit)", "A dictionary can only be changed by an account that has dict.edit" in st(h), repr(st(h)))
    after = ids(A2, "cust")
    arow("D4c", "...and NO record appears: refus1 is not on the disk, and the dictionary holds the same items as before", item(A2, "cust", "refus1") is None and after == before, repr((item(A2, "cust", "refus1"), before, after)))
    tb, order = itable(h)
    arow("D4d", "...and the list does not show it", "refus1" not in order, repr(order))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_try():
    say("\n--- D5: T tries an item on a record")
    before = sorted(ids(A1, "cust") or [])
    h = page(A1, "cust")
    for it, rid, want, kind in (("amt", "c1", ["The value:", " 12.5", "As a query prints it (format 10R), between bars:", "| 12.5|"], "D"),
                                ("dbl", "c1", ["The value:", " 25", "As a query prints it (format 10R), between bars:", "| 25|"], "I"),
                                ("city", "c2", ["The value:", "Rome"], "A"),
                                ("tags", "c1", ["The value (3 values, between bars):", "a | b | c"], "D")):
        goto(h, it)
        h.typed("t", idle=1.2)
        h.typed("\x15" + rid + "\r", idle=2.0)
        bt = rawflat(h)
        arow("D5" + {"amt": "", "dbl": "b", "city": "c", "tags": "d"}[it], "T on %s (%s) with the record %s shows %s" % (it, kind, rid, " / ".join(want)), all(w in bt for w in want) and "Try an item" in bt, bt[-600:])
        h.key("enter", idle=1.0)
        h.key("esc", idle=1.0)
    goto(h, "dt")
    h.typed("t", idle=1.2)
    h.typed("\x15c1\r", idle=2.0)
    bt = rawflat(h)
    arow("D5e", "T on dt (conversion D2/, format 10L) with c1 shows the stored value 1 and, as a query prints it, 01/01/68 in a column of 10", "The value:" in bt and " 1 " in bt and "As a query prints it (converted with D2/) (format 10L), between bars:" in bt and "|01/01/68 |" in bt, bt[-600:])
    h.key("enter", idle=1.0)
    h.key("esc", idle=1.0)
    goto(h, "amt")
    h.typed("t", idle=1.2)
    h.typed("\x15" + "nosuchrec\r", idle=1.5)
    arow("D5f", "a record that is not in the file is said so on the status line and nothing is shown", "there is no record nosuchrec in cust" in st(h) and "Try an item" not in h.text(), repr(st(h)))
    h.key("esc", idle=1.0)
    goto(h, "uncomp")
    h.typed("t", idle=1.5)
    arow("D5g", "an I item that has not been compiled is refused BEFORE a record is asked for, and C is named", "uncomp has not been compiled yet: C compiles it" in st(h) and "Try an item" not in h.text(), repr(st(h)))
    h.key("esc", idle=1.0)
    goto(h, "note")
    h.typed("t", idle=1.5)
    arow("D5h", "an item that holds no value (text X) is refused with its type", "only D, A, S and I items give a value for a record; note is of type X" in st(h), repr(st(h)))
    h.key("esc", idle=1.0)
    goto(h, "UpCase")
    h.typed("t", idle=1.2)
    h.typed("\x15c1\r", idle=2.0)
    arow("D5i", "an id the page does not give to a command (UpCase) can still be tried: T runs nothing", "The value:" in flat(h) and "Smith" in flat(h), flat(h)[-400:])
    h.key("enter", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    arow("D5j", "T wrote nothing: the dictionary holds the same items as before the section, and amt and dbl are as they were", sorted(ids(A1, "cust") or []) == before and item(A1, "cust", "amt")[0] == ["D", "3", "", "Amt", "10R", "S"]
         and item(A1, "cust", "dbl")[0][:2] == ["I", "AMT * 2"], repr((before, ids(A1, "cust"))))


def section_compile():
    say("\n--- D6: C compiles an item")
    h = page(A1, "cust")
    goto(h, "amt")
    h.typed("c", idle=1.5)
    arow("D6", "C on a D item is refused with its type before any box", "only A, S and I items are compiled; amt is of type D" in st(h) and "Run this command?" not in h.text(), repr(st(h)))
    h.key("esc", idle=1.0)
    goto(h, "uncomp")
    h.typed("c", idle=1.5)
    bt = boxtext(h)
    arow("D6b", "C on uncomp shows the exact command in a box", "compile.dict cust uncomp" in bt and "Run" in h.text() and "Cancel" in h.text(), bt[:400])
    h.key("enter", idle=1.5)
    d = item(A1, "cust", "uncomp")
    arow("D6c", "Enter is Cancel: the record has no object code on the disk", d is not None and d[1] == 0 and "nothing was run" in st(h), repr((d, st(h))))
    h.typed("c", idle=1.5)
    h.typed("r", idle=3.0)
    until(h, lambda t: "Compiling uncomp" in st(h))
    d = item(A1, "cust", "uncomp")
    arow("D6d", "Run: compile.dict ran - the record on the DISK now holds the object code, the fields are as they were, and the status shows the verb's words", d is not None and d[1] == 1 and d[0][:2] == ["I", "AMT + 1"] and "Compiling uncomp" in st(h), repr((d, st(h))))
    B = lowtxt(h)
    arow("D6e", "the item under the cursor now says it is compiled", "Compiled: the query processor runs the compiled form." in B, B[:300])
    h.typed("t", idle=1.2)
    h.typed("\x15c1\r", idle=2.0)
    arow("D6f", "T works on it now: AMT + 1 on c1 is 13.5", "The value:" in flat(h) and "13.5" in flat(h), flat(h)[-300:])
    h.key("enter", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    d2 = item(A2, "cust", "uncomp")
    h = page(A2, "cust")
    goto(h, "uncomp")
    h.typed("c", idle=1.5)
    h.typed("r", idle=3.0)
    until(h, lambda t: "Compiling uncomp" in st(h))
    d3 = item(A2, "cust", "uncomp")
    arow("D6g", "in the account with dict-edit OFF compiling is not held back (the object code is a side effect of an ordinary command): the record on the disk gets its object code", d2 is not None and d2[1] == 0 and d3 is not None and d3[1] == 1 and "Compiling uncomp" in st(h), repr((d2, d3, st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def ide_edit(h, expect_saved):
    """E on the item under the cursor (the IDE, 'ide dict file id'), a Q typed at the head of the record, Ctrl-S, then - when the save was refused - Enter to dismiss the box that says why,
    Ctrl-Q (and Discard, DOWN and Enter, to every 'has changes' question), Enter to come back"""
    h.typed("e", idle=2.0)
    until(h, lambda t: "File" in h.line(0) and "Search" in h.line(0) and "dict cust" in t)
    h.typed("Q", idle=0.8)
    h.typed("\x13", idle=1.5)
    IDESCREEN = h.text()
    if not expect_saved:
        h.key("enter", idle=1.0)
    h.typed("\x11", idle=1.5)
    n = 0
    while "has changes" in h.text() and n < 6:
        h.key("down", idle=0.5)
        h.key("enter", idle=1.0)
        n += 1
    until(h, lambda t: "Press Enter" in t or "Dictionary of" in t, 10)
    h.key("enter", idle=2.0)
    until(h, lambda t: "Dictionary of" in t, 10)
    return IDESCREEN


def section_edit():
    say("\n--- D7: E hands the terminal to the IDE")
    h = page(A1, "cust")
    goto(h, "note")
    h.typed("e", idle=2.0)
    until(h, lambda t: "File" in h.line(0) and "Search" in h.line(0) and "dict cust note" in t)
    T = h.text()
    arow("D7", "E on note hands the screen to the IDE: the IDE's menu bar is on row 0, the record dict cust note is the one open (its fields X and 'some text' are on the screen) and the page's boxes are gone",
         "File" in h.line(0) and "Search" in h.line(0) and "dict cust note" in T and "some text" in T and "The item under the cursor" not in T, T[:300])
    h.typed("\x11", idle=1.5)
    until(h, lambda t: "Press Enter" in t or "Dictionary of" in t, 10)
    h.key("enter", idle=2.0)
    until(h, lambda t: "Dictionary of" in t, 10)
    arow("D7b", "Ctrl-Q leaves the IDE, Enter brings the page back, the cursor is on note again and the status line says it came back from ide dict cust note", "back from ide dict cust note" in st(h) and "note" in itable(h)[1] and "text (X)" in lowtxt(h), repr((st(h), lowtxt(h)[:80])))
    h.key("esc", idle=1.0)
    goto(h, "ed1")
    ide_edit(h, True)
    d = item(A1, "cust", "ed1")
    tb, order = itable(h)
    arow("D7c", "with dict-edit ON the IDE saves: the record on the DISK is now QX / 'edit me' and the page, back from the IDE, lists ed1 as an item of type Q", d is not None and d[0] == ["QX", "edit me"] and tb.get("ed1", ("",))[0] == "Q", repr((d, tb.get("ed1"))))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2, "cust")
    goto(h, "ed1")
    ide_edit(h, False)
    d = item(A2, "cust", "ed1")
    arow("D7d", "with dict-edit OFF the IDE's save is refused by the kernel: the record on the DISK is as it was (X / 'edit me')", d is not None and d[0] == ["X", "edit me"], repr(d))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_delete():
    say("\n--- D8: D deletes an item")
    h = page(A1, "cust")
    goto(h, "del1")
    h.typed("d", idle=1.5)
    bt = boxtext(h)
    arow("D8", "D shows the exact command (delete dict cust del1) in a box and what it does", "delete dict cust del1" in bt and "Deletes the item del1 from the dictionary of cust" in bt and "Run" in h.text() and "Cancel" in h.text(), bt[:500])
    h.key("enter", idle=1.5)
    arow("D8b", "Enter is Cancel: the item is still on the disk and in the list", item(A1, "cust", "del1") is not None and "del1" in itable(h)[1], repr((item(A1, "cust", "del1"), itable(h)[1])))
    h.typed("d", idle=1.5)
    h.typed("r", idle=1.5)
    h.typed("nope\r", idle=2.0)
    arow("D8c", "Run and the WRONG id typed: nothing is deleted (the item is on the disk) and the status says what was asked for", item(A1, "cust", "del1") is not None and "del1" in st(h), repr((item(A1, "cust", "del1"), st(h))))
    h.typed("d", idle=1.5)
    h.typed("r", idle=1.5)
    h.typed("del1\r", idle=3.0)
    arow("D8d", "Run and the right id typed: delete dict ran - the record is gone from the DISK, the list no longer has it and the other items stay", item(A1, "cust", "del1") is None and "del1" not in itable(h)[1]
         and item(A1, "cust", "note") is not None and "1 record(s) deleted" in st(h), repr((item(A1, "cust", "del1"), st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2, "cust")
    goto(h, "del1")
    h.typed("d", idle=1.5)
    bt = boxtext(h)
    h.typed("r", idle=1.5)
    h.typed("del1\r", idle=3.0)
    arow("D8e", "with dict-edit OFF the box says the delete is expected to be refused, the verb's own refusal is on the status line and the item is still on the disk", "The delete is expected to be refused" in bt
         and "A dictionary can only be changed by an account that has dict.edit" in st(h) and item(A2, "cust", "del1") is not None, repr((bt[:200], st(h), item(A2, "cust", "del1"))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_odd():
    say("\n--- D9: names the page does not give to a command")
    h = page(A1, "cust")
    goto(h, "UpCase")
    tb, order = itable(h)
    arow("D9", "an item with a capital in its id is listed (UpCase) and described", "UpCase" in tb and lowtxt(h).replace("  ", " ").startswith("UpCase - a data field"), repr((tb.get("UpCase"), lowtxt(h)[:80])))
    h.typed("e", idle=1.5)
    s1 = st(h)
    h.typed("d", idle=1.5)
    s2 = st(h)
    arow("D9b", "E and D on it say the id is not given to a command by the page (a character it does not pass, or an SD keyword) and show the verb to type; no box and no IDE open, and the item is untouched",
         "is not given to a command by the page" in s1 and "ide dict cust UpCase" in s1 and "is not given to a command by the page" in s2 and "delete dict cust UpCase" in s2 and "Run this command?" not in h.text() and item(A1, "cust", "UpCase") is not None, repr((s1, s2)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    # a word the VOC holds as a keyword is never given to a verb as an item id: DELETE DICT cust ALL would ask to delete every item
    bp = os.path.join(acct_dir(A1), "bp")
    g.put(os.path.join(bp, "zzkw"), "\n".join(["   open 'DICT cust' to d else crt 'ZZKW no dict' ; stop",
                                               "   write 'X':@fm:'a keyword as an item id' on d, 'all'", "   write 'X':@fm:'another' on d, 'no.query'", "   crt 'ZZKW done'", "end", ""]))
    g.put(os.path.join(bp, "zzkwd"), "\n".join(["   open 'DICT cust' to d else crt 'ZZKWD no dict' ; stop",
                                                "   delete d, 'all'", "   delete d, 'no.query'", "   crt 'ZZKWD done'", "end", ""]))
    out = g.plain(A1, ["BASIC bp zzkw zzkwd", "RUN bp zzkw"])
    if not has(out, r"^ZZKW done$"):
        bail("the keyword-named items were not made:\n" + "\n".join(out[-6:]))
    before = (item(A1, "cust", "all"), item(A1, "cust", "no.query"))
    h = page(A1, "cust")
    ks = []
    for kid in ("all", "no.query"):
        goto(h, kid)
        h.typed("e", idle=1.5)
        ks.append(st(h))
        h.typed("d", idle=1.5)
        ks.append(st(h))
        if "Run this command?" in h.text():
            h.key("enter", idle=1.5)                                   # a page that offered the box (a mutant): Cancel
    arow("D9e", "items called ALL and NO.QUERY (SD keywords) are listed, but E and D on them say the id is not given to a command by the page and show the verb to type; no box, no IDE, and both items are still on the disk",
         before[0] is not None and before[1] is not None and all("is not given to a command by the page" in s for s in ks) and "delete dict cust all" in ks[1] and "ide dict cust no.query" in ks[2]
         and item(A1, "cust", "all") is not None and item(A1, "cust", "no.query") is not None, repr(ks))
    h.key("ctrl-q", idle=1.2)
    h.end()
    out = g.plain(A1, ["RUN bp zzkwd"])
    if not has(out, r"^ZZKWD done$"):
        bail("the keyword-named items were not taken away again:\n" + "\n".join(out[-6:]))
    h = page(A1)
    filt(h, "$map")
    h.key("enter", idle=2.0)
    arow("D9c", "a file whose name has a dollar ($map) opens (the page only reads it)", "Dictionary of $map" in h.text(), repr(st(h)))
    tb, order = itable(h)
    plain = [x for x in order if re.fullmatch(r"[a-z0-9._-]+", x)]
    first = plain[0] if plain else ""
    if first:
        goto(h, first)
    h.typed("e", idle=1.5)
    s1 = st(h)
    h.typed("d", idle=1.5)
    s2 = st(h)
    arow("D9d", "...and E and D on an item with a plain id (%s) say the FILE name is not given to a command by the page (a character it does not pass, or an SD keyword), with the verb to type" % first,
         first != "" and "this file name is not given to a command by the page (a character it does not pass, or an SD keyword)" in s1 and "ide dict $map %s" % first in s1 and "this file name is not given to a command by the page" in s2 and "delete dict $map %s" % first in s2
         and "Run this command?" not in h.text(), repr((first, s1, s2)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_indices():
    say("\n--- D10: the indices")
    h = page(A1, "ixf")
    h.typed("i", idle=1.5)
    tb, order = xtable(h)
    arow("D10", "I shows the indices pane of ixf: f1 (defined, NOT built) and UPNAME (built), as a separate session's list.index says (f1 N, upname Y)",
         st(h).startswith("[Indices]") and "Indices of ixf" in h.text() and tb.get("f1", ("",))[0] == "no" and tb.get("UPNAME", ("",))[0] == "yes" and idx_state(A1, "ixf") == {"f1": "N", "upname": "Y"}, repr((tb, idx_state(A1, "ixf"))))
    B = lowtxt(h)
    arow("D10b", "the index under the cursor is described: f1 is defined but not built and finds nothing until B builds it", "defined but NOT BUILT" in B and "It is on field 1 of each record." in B, B[:300])
    h.typed("n", idle=1.5)
    h.key("enter", idle=1.5)
    arow("D10c", "N offers the items to index in a list; the first one (f1) already has an index and is refused", "already has an index" in st(h) and idx_state(A1, "ixf") == {"f1": "N", "upname": "Y"}, repr(st(h)))
    h.typed("n", idle=1.5)
    h.key("down", idle=0.5)
    h.key("enter", idle=1.5)
    bt = boxtext(h)
    arow("D10d", "N then Down and Enter picks f2 and shows the exact command (create.index ixf f2) in a box that says build.index follows and that an index that is not built finds nothing", "create.index ixf f2" in bt and "build.index ixf f2" in bt and "An index that is not built finds nothing." in bt and "Run" in h.text(), bt[:500])
    h.key("enter", idle=1.5)
    arow("D10e", "Enter is Cancel: no index is made (a separate session's list.index has the same two)", idx_state(A1, "ixf") == {"f1": "N", "upname": "Y"} and "f2" not in xtable(h)[1], repr((idx_state(A1, "ixf"), xtable(h)[1])))
    h.typed("n", idle=1.5)
    h.key("down", idle=0.5)
    h.key("enter", idle=1.5)
    h.typed("r", idle=3.0)
    until(h, lambda t: "Populating index" in st(h) or "Cannot" in st(h))
    state = idx_state(A1, "ixf")
    tb, order = xtable(h)
    arow("D10f", "Run: create.index and then build.index ran - a separate session's list.index has f2 BUILT (Y) and the others as they were, the pane lists it as built with the last verb's words on the status line",
         state == {"f1": "N", "upname": "Y", "f2": "Y"} and tb.get("f2", ("",))[0] == "yes" and "Populating index" in st(h), repr((state, tb.get("f2"), st(h))))
    # B on f1
    h.key("home", idle=0.6)
    h.typed("b", idle=1.5)
    bt = boxtext(h)
    h.key("enter", idle=1.5)
    arow("D10g", "B shows build.index ixf f1 in a box; Enter is Cancel and f1 stays NOT built", "build.index ixf f1" in bt and idx_state(A1, "ixf").get("f1") == "N", repr((bt[:300], idx_state(A1, "ixf"))))
    h.typed("b", idle=1.5)
    h.typed("r", idle=3.0)
    until(h, lambda t: "Populating index" in st(h) or "Cannot" in st(h))
    arow("D10h", "Run: build.index ran - f1 is BUILT now on the disk's word (list.index Y) and in the pane", idx_state(A1, "ixf").get("f1") == "Y" and xtable(h)[0].get("f1", ("",))[0] == "yes", repr((idx_state(A1, "ixf"), xtable(h)[0].get("f1"), st(h))))
    # L
    h.typed("l", idle=1.0)
    until(h, lambda t: "Press Enter" in t)
    T = h.text()
    arow("D10i", "L hands the terminal to list.index: its printout (the details of the index) is on the screen, the page's boxes are gone and the verb waits for Enter", "Alternate key" in T and "Press Enter" in T and "The index under the cursor" not in T, T[-500:])
    h.key("enter", idle=1.5)
    until(h, lambda t: "The index under the cursor" in t)
    arow("D10j", "Enter brings the page back, in the indices pane, and the status says it is back from list.index ixf f1 detail", st(h).startswith("[Indices]") and "back from list.index ixf f1 detail" in st(h), repr(st(h)))
    tb, order = xtable(h)
    ordered = list(order)
    # an index made in capitals (UPNAME) is built by its lower-case name
    if "UPNAME" in ordered:
        for _ in range(ordered.index("UPNAME")):
            h.key("down", idle=0.5)
        h.typed("b", idle=1.5)
        bt = boxtext(h)
        h.typed("r", idle=3.0)
        until(h, lambda t: "Populating index" in st(h) or "Cannot" in st(h))
        arow("D10k", "an index made in capitals (UPNAME) is built by its lower-case name: the box shows build.index ixf upname and the verb's words are on the status line", "build.index ixf upname" in bt and "Populating index" in st(h) and idx_state(A1, "ixf").get("upname") == "Y",
             repr((bt[:200], idx_state(A1, "ixf"), st(h))))
    else:
        arow("D10k", "the index UPNAME is in the pane", False, repr(ordered))
    # D on f2: the wrong name, then the right name; ONLY that index goes
    tb, order = xtable(h)
    if "f2" in order:
        h.key("home", idle=0.6)
        for _ in range(order.index("f2")):
            h.key("down", idle=0.5)
        h.typed("d", idle=1.5)
        bt = boxtext(h)
        h.typed("r", idle=1.2)
        h.typed("nope\r", idle=2.0)
        arow("D10l", "D on f2 shows delete.index ixf f2; Run and the WRONG name typed deletes nothing (the three indices are as a separate session's list.index says)", "delete.index ixf f2" in bt and idx_state(A1, "ixf") == {"f1": "Y", "upname": "Y", "f2": "Y"}, repr((bt[:300], idx_state(A1, "ixf"))))
        h.typed("d", idle=1.5)
        h.typed("r", idle=1.2)
        h.typed("f2\r", idle=3.0)
        arow("D10m", "Run and the right name typed: ONLY f2 is deleted - f1 and upname stay, as a separate session's list.index says - and the pane no longer lists f2", idx_state(A1, "ixf") == {"f1": "Y", "upname": "Y"} and "f2" not in xtable(h)[1], repr((idx_state(A1, "ixf"), xtable(h)[1])))
    else:
        arow("D10l", "the index f2 is in the pane", False, repr(order))
    # D on UPNAME by its lower-case name typed
    tb, order = xtable(h)
    if "UPNAME" in order:
        h.key("home", idle=0.6)
        for _ in range(order.index("UPNAME")):
            h.key("down", idle=0.5)
        h.typed("d", idle=1.5)
        h.typed("r", idle=1.2)
        h.typed("upname\r", idle=3.0)
        arow("D10n", "an index made in capitals is deleted by its lower-case name typed (delete.index ixf upname): only f1 is left", idx_state(A1, "ixf") == {"f1": "Y"}, repr((idx_state(A1, "ixf"), st(h))))
    else:
        arow("D10n", "the index UPNAME is still in the pane", False, repr(order))
    h.key("esc", idle=1.2)
    arow("D10o", "Esc in the indices pane goes back to the items pane", st(h).startswith("[Items]") and "Dictionary of ixf" in h.text(), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    # the indices are not held back by dict-edit: in the account with it OFF create.index and build.index still make one
    h = page(A2, "ixf")
    h.typed("i", idle=1.5)
    before = idx_state(A2, "ixf")
    h.typed("n", idle=1.5)
    h.key("down", idle=0.5)
    h.key("enter", idle=1.5)
    bt = boxtext(h)
    h.typed("r", idle=3.0)
    until(h, lambda t: "Populating index" in st(h) or "Cannot" in st(h))
    after = idx_state(A2, "ixf")
    arow("D10p", "with dict-edit OFF the indices are not held back: N, Down, Enter, Run builds f2 (create.index ixf f2, then build.index; a separate session's list.index has it, Y)", "create.index ixf f2" in bt and before == {"f1": "N", "upname": "Y"} and after.get("f2") == "Y", repr((bt[:200], before, after, st(h))))
    h.key("home", idle=0.6)
    h.typed("b", idle=1.5)
    h.typed("r", idle=3.0)
    until(h, lambda t: "Populating index" in st(h) or "Cannot" in st(h))
    arow("D10q", "...B builds f1 there too (a separate session's list.index has f1 built, Y)", idx_state(A2, "ixf").get("f1") == "Y", repr((idx_state(A2, "ixf"), st(h))))
    h.key("end", idle=0.6)
    h.typed("d", idle=1.5)
    h.typed("r", idle=1.2)
    h.typed("f2\r", idle=3.0)
    arow("D10r", "...and D deletes f2 (its name typed): f1 and upname stay", idx_state(A2, "ixf") == {"f1": "Y", "upname": "Y"}, repr((idx_state(A2, "ixf"), st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_other():
    say("\n--- D11: help, panes, files, F5, a small window")
    h = page(A1, "cust")
    arow("D11", "a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    h.click(135, 2, idle=1.5)
    arow("D11b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in flat(h), flat(h)[-300:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.5)
    arow("D11c", "F1 reaches it too", "Help is not installed here" in flat(h), flat(h)[-300:])
    h.key("esc", idle=1.0)
    h.key("tab", idle=1.5)
    arow("D11d", "Tab moves from the items to the indices pane", st(h).startswith("[Indices]"), repr(st(h)))
    h.key("tab", idle=1.5)
    arow("D11e", "...and Tab again moves back", st(h).startswith("[Items]"), repr(st(h)))
    # F5 reads again: an item another session added appears (the filter keeps the list short enough to see it)
    filt(h, "zzout")
    g.put(os.path.join(acct_dir(A1), "bp", "zzdadd"), "\n".join(["   open 'DICT cust' to d else stop", "   write 'X':@fm:'outside' on d, 'zzout'", "   crt 'ADD done'", "end", ""]))
    g.plain(A1, ["BASIC bp zzdadd", "RUN bp zzdadd"])
    before = "zzout" in itable(h)[1]
    h.key("f5", idle=2.0)
    arow("D11f", "F5 reads the dictionary again: an item another session added is listed (not before)", not before and "zzout" in itable(h)[1] and "read again" in st(h), repr((before, itable(h)[1], st(h))))
    h.key("esc", idle=1.0)
    h.typed("f", idle=1.5)
    tb, order = ftable(h)
    arow("D11g", "F goes back to the files pane, with the cursor kept", st(h).startswith("[Files]") and "Files of %s" % A1 in h.text() and "cust" in order, repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    h.typed("tool.dict cust\r", idle=3.0)
    T = h.text()
    arow("D11h", "a window under 140 by 43 gets no page", "The item under the cursor" not in T and "Dictionary of" not in T, T[-300:])
    h.end()


def run_sections(names):
    for n in names:
        {"files": section_files, "items": section_items, "new": section_new, "refused": section_refused, "try": section_try, "compile": section_compile,
         "edit": section_edit, "delete": section_delete, "odd": section_odd, "indices": section_indices, "other": section_other}[n]()


ALL = ["files", "items", "new", "refused", "try", "compile", "edit", "delete", "odd", "indices", "other"]


def main():
    mutants = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")]
    if "--mutants" in sys.argv:
        mutants = list(MUTANTS)
    for m in mutants:
        if m not in MUTANTS:
            bail("usage: sandbox-tool-dict.py <dir> [--build] [--mutants | --mutant=%s]" % "|".join(MUTANTS))
    results = []
    only = [a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--sections=")]
    only = only[0] if only else ALL
    for s in only:
        if s not in ALL:
            bail("--sections= takes some of %s" % ",".join(ALL))
    try:
        sh.setup("sandbox-tool-dict.py")
        setup_files()
        if not mutants:
            run_sections(only)
        else:
            for m in mutants:
                if m != mutants[0]:
                    setup_files()                       # fresh accounts and the page from the tree
                FAILED_IDS[:] = []
                mutate(m)
                want = sorted(set(MUTANTS[m][2]))
                say("sandbox-tool-dict: MUTANT %s: the rows that must fail, and nothing else: %s (section %s)" % (m, ", ".join(want), MUTANTS[m][3]))
                run_sections([MUTANTS[m][3]])
                got = sorted({re.match(r"D\d+", i).group(0) for i in FAILED_IDS if re.match(r"D\d+", i)})
                ok = want == got
                say("sandbox-tool-dict: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (m, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
                results.append(ok)
    finally:
        sh.teardown()
    if mutants:
        say("\nsandbox-tool-dict: %d mutants run, %d killed by exactly their own rows" % (len(results), sum(1 for r in results if r)))
        return 0 if results and all(results) else 1
    say("\nsandbox-tool-dict: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
