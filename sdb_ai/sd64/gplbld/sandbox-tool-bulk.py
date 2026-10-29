#!/usr/bin/env python3
#
# sandbox-tool-bulk.py - TOOL.BULK, the bulk update of the records of one data file ($tool_bulk, S.75 DV5), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-bulk.py <dir> [--build] [--only=b1,b2,...] [--mutant=NAME[,NAME...]|all]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  --only runs some sections (b1 b2 b3 b4 b7 b8 b9 b10; b4 holds B4 to B6).  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and
# exit 0 means the rows that had to fail failed and no others (MUTANTS); --mutant=all does that for every mutant in turn (the page is put back and compiled again between them).
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand: zzbl1 with the edit gates (voc, bp, dict) ON and zzbl2 with them OFF.  In each, a dynamic file `cust`
# with a dictionary (name 1, city 2, amt 3, status 4) and seven records (c1 to c7: three in Paris, one in paris, one whose amt is text, one whose amt is empty), a second file `ordr`, a file `zzgone`
# that B2 deletes from another session,
# a sentinel file `zzsent`, a directory file `ddir`, a VOC pointer `custdic` at the dictionary directory `cust.dic`, the program file `bp`, and in zzbl1 the saved list `lp` (c1 c3 c1:
# a name twice).  An ORDINARY session (sd -a<account>, as the sandbox user, not an administrator) types TOOL.BULK.
#
# THE INSTRUMENT.  Every outcome is read from the DISK or from SD, not from what the page said: the records of a file are read back by a SEPARATE ordinary session (zzdump) and compared
# with the records they should be; the number of records a selection takes is asked of a separate session's SELECT; the data files under cust are compared by size and modification time
# before and after a dry run (not the header %0, which any session that opens the file touches); the audit file is read from the offset it had before the run; a lock is held by a
# second live session.  The page's own words are compared with those.
#
#   B1   the page draws; F: a data file is taken, and bp, bp.out, the VOC, a dictionary, a directory file, a missing file and a bad name are refused up front, by name and by kind,
#        in the page's words - and, in an account with the edit gates OFF, in the KERNEL'S words; after all of that nothing on the disk moved
#   B2   the records: conditions (the count is the count of a separate SELECT), E, a pattern, ALL and ANY, an injection in a value runs nothing and adds nothing, at most four, X,
#        every record, a saved list (a name twice is taken once), a file that another session deleted (the select's own words, not a count)
#   B3   the operations: what is refused (a non-number, attribute 0, 1000, a copy onto itself), a D item picked by name, the closed set
#   B4   the DRY RUN writes nothing (records and modification times) and says how many it selected, would change, would leave, could not work out; an edit makes it stale
#   B5   APPLY: the undo file is made through a box, Cancel is the default everywhere, the wrong name changes nothing, the right name changes exactly the records the dry run named,
#        one audit line, the undo records hold the old records, the dry run is spent
#   B6   UNDO: Cancel changes nothing, a record changed since is left alone, the others come back, the header says undone
#   B7   every operation of the closed set on seven records, and the undo that brings the old records back byte for byte
#   B8   a record another session holds locked is skipped and counted
#   B9   a record that changed after the dry run is skipped and counted
#   B10  help, a window under 140 by 43, another file clears the selection and the operations
import importlib.util
import os
import re
import shutil
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


sh = _load("sandbox_home_for_bulk", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zzbl1", "zzbl2"
A3 = "zzbl3"                                                           # voc-edit ON, bp-edit and dict-edit OFF (B11)
ME =os.environ.get("USER") or os.getlogin()
SCREEN = [None]      # the pty session of the section running: a failed row prints what it was looking at
PAGES = []
LAST = [None]        # in a mutant run: the section stops after the row with this id
HOLDERS = []

ITEMS = ["@id", "amt", "city", "name", "status"]                   # the order of the item pick list for cust (zzgone has the first only)
OPS = ["eq", "ne", "lt", "le", "gt", "ge", "like", "unlike"]
KINDS = ["set", "null", "append", "prepend", "replace", "add", "upper", "lower", "copy"]
ORIG = {
    "c1": ["Alice", "Paris", "10", "open"],
    "c2": ["Bob", "London", "20", "open"],
    "c3": ["Carol", "Paris", "5", "closed"],
    "c4": ["Dave", "Rome", "100", "open"],
    "c5": ["Eve", "paris", "7", "open"],
    "c6": ["Frank", "Paris", "abc", "open"],
    "c7": ["Gina", "Oslo", "", "new"],
}


class StopSection(Exception):
    pass


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])
    if LAST[0] == rid:
        raise StopSection()


def box():
    return sh.BOX


def acct_dir(a):
    return os.path.join(box(), "user_accounts", a)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def reg_record(name, edit):
    e = "yes" if edit else "no"
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", e, e, e, "", "", "no", "", "", ""]


# ------------------------------------------------------------------------------------------------- the sandbox's copy of the page

SRC = os.path.join(TREE, "sdsys", "gpl.bp", "tool_bulk")


def install_sources():
    """a sandbox built before the page existed has no copy of it, its VOC entry or its help record: put the tree's in (a sandbox built from this tree already has them)"""
    for rel in (("gpl.bp", "tool_bulk"), ("newvoc", "tool.bulk"), ("helptext", "tool.bulk.page")):
        shutil.copyfile(os.path.join(TREE, "sdsys", rel[0], rel[1]), os.path.join(sh.SYS, rel[0], rel[1]))


def compile_page():
    out = adm("BASIC gpl.bp tool_bulk")
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_bulk did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def sandbox_page():
    return os.path.join(sh.SYS, "gpl.bp", "tool_bulk")


# ------------------------------------------------------------------------------------------------- the fixtures

SEED = """
   open 'DICT cust' to d else crt 'ZZSEED no dict' ; stop
   write 'D':@fm:'1':@fm:'':@fm:'Name':@fm:'15L':@fm:'S' on d, 'name'
   write 'D':@fm:'2':@fm:'':@fm:'City':@fm:'15L':@fm:'S' on d, 'city'
   write 'D':@fm:'3':@fm:'':@fm:'Amt':@fm:'10R':@fm:'S' on d, 'amt'
   write 'D':@fm:'4':@fm:'':@fm:'Status':@fm:'10L':@fm:'S' on d, 'status'
   open 'cust' to f else crt 'ZZSEED no cust' ; stop
   clearfile f
   write 'Alice':@fm:'Paris':@fm:'10':@fm:'open' on f, 'c1'
   write 'Bob':@fm:'London':@fm:'20':@fm:'open' on f, 'c2'
   write 'Carol':@fm:'Paris':@fm:'5':@fm:'closed' on f, 'c3'
   write 'Dave':@fm:'Rome':@fm:'100':@fm:'open' on f, 'c4'
   write 'Eve':@fm:'paris':@fm:'7':@fm:'open' on f, 'c5'
   write 'Frank':@fm:'Paris':@fm:'abc':@fm:'open' on f, 'c6'
   write 'Gina':@fm:'Oslo':@fm:'':@fm:'new' on f, 'c7'
   open 'zzsent' to s else crt 'ZZSEED no zzsent' ; stop
   write 'sentinel' on s, 's1'
   open 'ordr' to o else crt 'ZZSEED no ordr' ; stop
   write 'Widget':@fm:'3' on o, 'o1'
   open '$savedlists' to sl else crt 'ZZSEED no savedlists' ; stop
   formlist 'c1':@fm:'c3':@fm:'c1' to 4
   savelist 'lp' from 4 else crt 'ZZSEED save failed' ; stop
   open 'voc' to v else crt 'ZZSEED no voc' ; stop
   write 'F':@fm:'cust.dic' on v, 'custdic'
   crt 'ZZSEED done'
end
"""

DUMP = """
   fname = downcase(field(@sentence, ' ', 4))
   what = downcase(field(@sentence, ' ', 5))
   if what = 'dict' then
      open 'DICT', fname to f else crt 'DUMP[nofile]' ; stop
   end else
      open fname to f else crt 'DUMP[nofile]' ; stop
   end
   select f to 9
   n = 0
   loop
      readnext id from 9 else exit
      read r from f, id then
         n += 1
         crt 'REC ' : id : ' ' : change(change(change(r, @fm, '|'), @vm, ']'), @sm, '/')
      end
   repeat
   crt 'DUMP[' : n : ']'
end
"""

WRITE = """
   fname = downcase(field(@sentence, ' ', 4))
   id = downcase(field(@sentence, ' ', 5))
   attr = field(@sentence, ' ', 6)
   val = field(@sentence, ' ', 7)
   open fname to f else crt 'ZZWR no file' ; stop
   readu r from f, id else crt 'ZZWR no record' ; stop
   r<attr> = val
   write r on f, id
   crt 'ZZWR done'
end
"""

HOLD = """
   open 'cust' to f else crt 'ZZHOLD nofile' ; stop
   readu r from f, 'c2' locked
      crt 'ZZHOLD locked' ; stop
   end then
      crt 'ZZHOLD holding'
   end else
      crt 'ZZHOLD gone' ; stop
   end
   sleep 300
end
"""

PLANT = """
   target = downcase(field(@sentence, ' ', 4))
   open 'VOC' to v else crt 'ZZPL no voc' ; stop
   read r from v, target else crt 'ZZPL no entry ' : target ; stop
   write r on v, '&bulk.undo&'
   crt 'ZZPL done'
end
"""

def setup_fixtures():
    q = sh.g
    for a in (A1, A2, A3):
        q.FIXTURES[a] = ("no", "no")
        q.build_account(a)
        q.reg_write(a, reg_record(a, True))                      # the gates stay ON while the fixtures are made; zzbl2's go off at the end, and zzbl3's bp-edit and dict-edit
        bp = os.path.join(acct_dir(a), "bp")
        q.put(os.path.join(bp, "zzplant"), PLANT)
        q.put(os.path.join(bp, "zzseed"), SEED)
        q.put(os.path.join(bp, "zzdump"), DUMP)
        q.put(os.path.join(bp, "zzwr"), WRITE)
        q.put(os.path.join(bp, "zzhold"), HOLD)
        q.put(os.path.join(bp, "zzsent"), "a record in the program file\n")
        out = q.plain(a, ["CREATE.FILE cust", "CREATE.FILE ordr", "CREATE.FILE zzsent", "CREATE.FILE zzgone", "CREATE.FILE ddir DIRECTORY", "CREATE.FILE $savedlists", "BASIC bp zzseed zzdump zzwr zzhold zzplant", "RUN bp zzseed"])
        if not has(out, r"^ZZSEED done$"):
            bail("the fixture files of %s were not made:\n%s" % (a, "\n".join(out[-12:])))
        if not has(out, r"^Compiled 5 program\(s\) with no errors"):
            bail("the fixture programs of %s did not compile:\n%s" % (a, "\n".join(out[-12:])))
    q.reg_write(A2, reg_record(A2, False))                       # now the gates of zzbl2 are OFF
    r3 = reg_record(A3, True)
    r3[10] = "no"                                                # zzbl3: voc-edit stays ON (it can point a VOC name anywhere), bp-edit and dict-edit go OFF
    r3[11] = "no"
    q.reg_write(A3, r3)
    d = dump_file(A1, "cust")
    if d != ORIG:
        bail("the fixture file cust is not what it should be: %r" % d)
    if dump_file(A1, "cust", "dict").get("amt", [""])[0] != "D":
        bail("the fixture dictionary of cust is not there")


def parse_dump(out):
    recs = {}
    done = None
    for ln in out:
        m = re.match(r"^REC (\S+) ?(.*)$", ln.rstrip())
        if m:
            recs[m.group(1)] = m.group(2).split("|")
        m = re.match(r"^DUMP\[(.*)\]$", ln.strip())
        if m:
            done = m.group(1)
    if done is None or done == "nofile":
        return None
    return recs


def dump_file(account, fname, what=""):
    """every record of a file as a SEPARATE ordinary session reads it: {id: [fields]}, or None when the file cannot be opened"""
    out = g.plain(account, ["RUN bp zzdump " + fname + (" " + what if what else "")])
    return parse_dump(out)


def write_field(account, fname, rid, attr, val):
    out = g.plain(account, ["RUN bp zzwr %s %s %s %s" % (fname, rid, attr, val)])
    if not has(out, r"^ZZWR done$"):
        bail("a separate session could not write %s %s:\n%s" % (fname, rid, "\n".join(out[-5:])))


def reseed(account=A1, undo=None):
    """the fixture records and dictionary back as they were; undo=True makes sure &bulk.undo& exists, undo=False that it does not"""
    out = g.plain(account, ["RUN bp zzseed"])
    if not has(out, r"^ZZSEED done$"):
        bail("the fixtures were not seeded again:\n" + "\n".join(out[-6:]))
    if undo is False and os.path.isdir(os.path.join(acct_dir(account), "&bulk.undo&")):
        g.plain(account, ["DELETE.FILE &bulk.undo& NO.QUERY"])
        if os.path.exists(os.path.join(acct_dir(account), "&bulk.undo&")):
            bail("the undo file could not be taken away")
    if undo is True and not os.path.isdir(os.path.join(acct_dir(account), "&bulk.undo&")):
        g.plain(account, ["CREATE.FILE &bulk.undo&"])
        if not os.path.isdir(os.path.join(acct_dir(account), "&bulk.undo&")):
            bail("the undo file could not be made")


def sep_count(account, sentence):
    """how many records a SEPARATE session's SELECT takes"""
    out = g.plain(account, [sentence])
    for ln in out:
        m = re.match(r"^(\d+) record\(s\) selected to list 0$", ln.strip())
        if m:
            return int(m.group(1))
    return None


def tree_state(path):
    """{relative path: (size, mtime in ns)} of every data file below path: a dry run must not move any of them.  The header %0 is left out: a session that opens a dynamic
    file touches it (seen on the sandbox, 25 Oct 26: the modification time of %0 moved through read-only sessions while that of the data group file %1 stood still until a write)"""
    st = {}
    for root, _dirs, files in os.walk(path):
        for f in files:
            if f == "%0":
                continue
            p = os.path.join(root, f)
            try:
                s = os.stat(p)
                st[os.path.relpath(p, path)] = (s.st_size, s.st_mtime_ns)
            except OSError:
                pass
    return st


def audit_off():
    path = os.path.join(sh.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    if off is None:
        return None
    try:
        with open(os.path.join(sh.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


class Holder:
    """a second LIVE ordinary session that holds the update lock on cust c2 until it is logged out"""

    def __init__(self, account):
        env = dict(os.environ, SD_CONFIG=os.path.join(box(), "sd.conf"))
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_TTY", None)
        env.pop("SDTEST_ADMIN", None)
        self.out = os.path.join(box(), "holder-%d.out" % len(HOLDERS))
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd"), "-a" + account], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=acct_dir(account), env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\nRUN bp zzhold\n")
        self.p.stdin.flush()
        say("    > holder: pid %d, %s: RUN bp zzhold" % (self.p.pid, account))
        HOLDERS.append(self)

    def text(self):
        self.fh.flush()
        with open(self.out, errors="replace") as f:
            return f.read()

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


def release_holders():
    for hd in HOLDERS:
        hd.kill()
    HOLDERS[:] = []
    try:
        g.adm(["LOGOUT ALL"])
    except Exception:
        pass


# ------------------------------------------------------------------------------------------------- the page on a pseudo-terminal

class Page:
    def __init__(self, account, cols=140, rows=43):
        self.h = H(account=account, cols=cols, rows=rows)
        SCREEN[0] = self.h
        PAGES.append(self)
        self.h.typed("tool.bulk\r", idle=3.5)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def st(self):
        return self.h.line(40)

    def keysrow(self):
        return self.h.line(42)

    def pane(self):
        m = re.match(r"\[(\w+)\]", self.st().strip())
        return m.group(1) if m else ""

    def key(self, name, idle=0.6):
        self.h.key(name, idle=idle)

    def typed(self, s, idle=0.9):
        self.h.typed(s, idle=idle)

    def click(self, col, rw, idle=1.0):
        self.h.click(col, rw, idle=idle)

    def until(self, pred, secs=20.0):
        """a page that runs a loop prints nothing while it runs, so a wait for idle output is not a wait for the page: pump the pty until the screen satisfies pred"""
        for _ in range(int(secs / 0.5)):
            if pred(self.h.text()):
                return True
            self.h.s._pump(0.5)
        return pred(self.h.text())

    def downs(self, n):
        for _ in range(n):
            self.key("down", 0.25)

    def focus(self, pane):
        for _ in range(4):
            if self.pane() == pane:
                return
            self.key("tab", 0.7)

    def choose_file(self, name):
        self.typed("f", idle=1.5)
        self.key("enter", idle=1.0)                                # the first line: type a file name
        self.typed(name + "\r", idle=2.0)

    def add_cond(self, item, op, value, wait=2.5):
        self.focus("Selection")
        self.typed("n", idle=1.2)
        self.downs(ITEMS.index(item))
        self.key("enter", idle=1.0)
        self.downs(OPS.index(op))
        self.key("enter", idle=1.0)
        self.typed(value + "\r", idle=wait)

    def add_op(self, kind, attr, a1=None, a2=None, src=None):
        self.focus("Operations")
        self.typed("n", idle=1.2)
        self.downs(KINDS.index(kind))
        self.key("enter", idle=1.0)
        self.key("enter", idle=1.0)                                # the first line: type an attribute number
        self.typed(str(attr) + "\r", idle=1.0)
        if kind == "copy":
            self.key("enter", idle=1.0)
            self.typed(str(src) + "\r", idle=1.2)
            return
        if kind == "replace":                                      # S.88: one form, the two texts joined by Tab, Return presses Use
            self.typed(a1 + "\t" + a2 + "\r", idle=1.2)
            self.h.s.settle(0.6)
            return
        for t in (a1, a2):
            if t is not None:
                self.typed(t + "\r", idle=1.0)
        self.h.s.settle(0.6)

    def cond_rows(self):
        return [norm(self.line(n)[3:137]).strip() for n in range(8, 12)]

    def op_rows(self):
        return [norm(self.line(n)[3:137]).strip() for n in range(16, 26)]

    def count_line(self):
        return norm(self.line(12)[3:137]).strip()

    def result(self, n):
        return norm(self.line(n)[3:137]).strip()

    def preview(self):
        return [norm(self.line(n)[3:137]).strip() for n in range(32, 39)]

    def boxtext(self):
        """the words inside the confirm box on the screen, one line (the page behind the box is left out); the whole screen when there is no box"""
        rows = [self.line(n) for n in range(43)]
        top = next((n for n, l in enumerate(rows) if re.search(r"Run this command\?|Update these records\?|Put these records back\?", l)), None)      # 26 Oct 26 (faults): the update's and the undo's boxes are titled by what they do
        if top is None:
            return norm(self.text())
        s0, s1 = rows[top].index("+"), rows[top].rindex("+")
        inner = []
        for n in range(top + 1, 43):
            if rows[n][s0:s0 + 1] == "+":
                break
            inner.append(rows[n][s0 + 1:s1])
        return norm(" ".join(inner))

    def quit(self):
        self.key("ctrl-q", idle=1.2)
        self.end()

    def end(self):
        try:
            self.h.end()
        except Exception:
            pass
        if self in PAGES:
            PAGES.remove(self)


def close_pages():
    for p in list(PAGES):
        p.end()
    SCREEN[0] = None


def section(fn):
    """a section stops quietly when a mutant run has reached the row it was written to be caught by"""
    def run(*a, **k):
        try:
            return fn(*a, **k)
        except StopSection:
            return None
        finally:
            close_pages()
            release_holders()
    run.__name__ = fn.__name__
    return run


def scenario_paris(p, six=False):
    """cust, city equal to Paris (c1 c3 c6), three operations: append -ok to attribute 1, add 5 (or 6) to attribute 3, replace open with ready in attribute 4"""
    p.choose_file("cust")
    p.add_cond("city", "eq", "Paris")
    p.add_op("append", 1, "-ok")
    p.add_op("add", 3, "6" if six else "5")
    p.add_op("replace", 4, "open", "ready")


EXP_PARIS_6 = {"c1": ["Alice-ok", "Paris", "16", "ready"], "c3": ["Carol-ok", "Paris", "11", "closed"]}


def expect(changes, base=None):
    d = {k: list(v) for k, v in (base or ORIG).items()}
    d.update({k: list(v) for k, v in changes.items()})
    return d


# ------------------------------------------------------------------------------------------------- B1: the file

@section
def section_b1():
    say("\n--- B1: the page draws; the file; what is refused up front, in the page's words and in the kernel's")
    reseed(A1)                                                        # a mutant run that stopped early in another section leaves its records as that section left them
    before = dump_file(A1, "cust")
    before_dict = dump_file(A1, "cust", "dict")
    p = Page(A1)
    T = p.text()
    if "Which records" not in T:
        dump(p.h)
        bail("tool.bulk never drew its page in an ordinary account, so no row below can be believed")
    arow("B1", "the page draws for an ordinary account, for the audience %s@%s (the right end of row 0): four boxes, a [?], no file chosen" % (ME, A1),
         re.search(r"tool\.bulk\s+%s@%s" % (re.escape(ME), A1), p.line(0)) is not None and all(t in T for t in ("File", "Which records", "What to do to them", "Result", "No file chosen")) and p.line(2)[134:137] == "[?]", repr(p.line(0)[100:]))
    arow("B1b", "the gates line, asked of the kernel, for an account with the edit gates ON", "voc-edit on" in p.line(3) and "dict-edit on" in p.line(3) and "bp-edit on" in p.line(3), repr(p.line(3)[:100]))
    k0 = p.keysrow()
    p.typed("r", idle=1.0)
    arow("B1c", "R before anything is chosen says to choose the file first, and A is not on the function-key row", "choose the file first" in p.st() and "A apply" not in k0, repr((p.st(), k0)))
    refusals = [
        ("B1d", "bp", "this page updates data files only: a program file is not one", "the program file bp"),
        ("B1d2", "bp.out", "a program file is not one", "the object directory bp.out"),
        ("B1d3", "voc", "this page updates data files only: the VOC is not one", "the VOC"),
        ("B1d4", "custdic", "this page updates data files only: a dictionary is not one", "a dictionary (the VOC pointer custdic leads to cust.dic)"),
        ("B1d5", "ddir", "this page updates dynamic data files only: ddir is a directory file", "a directory file"),
        ("B1d6", "nosuchfile", "this account cannot open nosuchfile", "a file that is not there"),
        ("B1d7", "x;y", "a file name of letters a-z, digits, dot, dash and underscore only", "a name with a semicolon"),
    ]
    for rid, name, words, what in refusals:
        p.choose_file(name)
        arow(rid, "F, a typed name, %s: refused up front in the page's words (%s) and no file is chosen" % (what, words), words in p.st() and "No file chosen" in p.line(2), repr((p.st(), p.line(2)[:60])))
    after = dump_file(A1, "cust")
    arow("B1e", "after every refusal nothing on the disk moved: cust and its dictionary are as they were, the program file's record and the sentinel file are still there",
         after == before == ORIG and dump_file(A1, "cust", "dict") == before_dict and os.path.exists(os.path.join(acct_dir(A1), "bp", "zzsent")) and (dump_file(A1, "zzsent") or {}).get("s1") == ["sentinel"], repr(after))
    p.choose_file("CUST")
    arow("B1f", "a data file is taken (a capital is folded as SD folds it): the File box names cust, its kind, about 7 records and the dictionary",
         "File: cust" in p.line(2) and "dynamic file, about 7 records, with a dictionary" in p.line(2) and "cust" in p.st(), repr((p.line(2)[:100], p.st())))
    p.quit()
    # an account whose edit gates are OFF: the kernel's own words
    q = Page(A2)
    arow("B1g", "the gates line for an account with the edit gates OFF: all three say off", "voc-edit off" in q.line(3) and "dict-edit off" in q.line(3) and "bp-edit off" in q.line(3), repr(q.line(3)[:100]))
    for rid, name, words in (("B1h", "bp", "bp.edit"), ("B1h2", "voc", "voc.edit"), ("B1h3", "custdic", "dict.edit")):
        q.choose_file(name)
        arow(rid, "in an account with the edit gates OFF, %s is refused in the KERNEL'S words (they name %s) - not in the page's" % (name, words),
             words in q.st() and "can only be changed by an account that has" in q.st() and "this page updates" not in q.st() and "No file chosen" in q.line(2), repr(q.st()))
    q.choose_file("cust")
    arow("B1i", "...and a plain data file is not held back by the edit gates: cust is taken", "File: cust" in q.line(2), repr(q.line(2)[:80]))
    q.quit()


# ------------------------------------------------------------------------------------------------- B2: which records

@section
def section_b2():
    say("\n--- B2: which records: the count is a separate SELECT's, E, ALL and ANY, injection, at most four, X, every record, a saved list, a file that is gone")
    reseed(A1)
    p = Page(A1)
    p.choose_file("cust")
    p.add_cond("city", "eq", "Paris")
    n1 = sep_count(A1, 'select cust with city eq "Paris"')
    arow("B2a", "city equal to Paris: the conditions list shows it and the count line is the count of a separate session's SELECT (%s)" % n1,
         n1 == 3 and p.cond_rows()[0] == '1 city equal to "Paris"' and p.count_line() == "Selected: 3 records.", repr((p.cond_rows(), p.count_line(), n1)))
    p.focus("Selection")
    p.typed("e", idle=1.2)
    p.key("enter", idle=1.0)                                           # the item starts where it was: city
    p.key("enter", idle=1.0)                                           # the operator starts where it was: equal to
    p.typed("\x15London\r", idle=2.5)                                  # the value starts as it was (Paris): cleared and typed again
    nl = sep_count(A1, 'select cust with city eq "London"')
    arow("B2a2", "E on the condition: the questions start from what it was and the value is changed to London; the count (%s) is the separate SELECT's - only Bob" % nl,
         nl == 1 and p.cond_rows()[0] == '1 city equal to "London"' and p.count_line() == "Selected: 1 record.", repr((p.cond_rows(), p.count_line(), nl)))
    p.typed("e", idle=1.2)
    p.key("enter", idle=1.0)
    p.key("enter", idle=1.0)
    p.typed("\x15Paris\r", idle=2.5)
    p.add_cond("name", "like", "A0X")
    n1b = sep_count(A1, 'select cust with city eq "Paris" and with name like "A0X"')
    arow("B2b", "a pattern condition (name matches the pattern A0X): the count (%s) is the separate SELECT's - only Alice" % n1b, n1b == 1 and p.cond_rows()[1] == '2 name matches the pattern "A0X"' and p.count_line() == "Selected: 1 record.", repr((p.cond_rows(), p.count_line(), n1b)))
    p.focus("Selection")
    p.key("end", 0.5)
    p.typed("x", idle=2.0)
    arow("B2b2", "...and X takes it out again: one condition, 3 records", p.cond_rows()[1] == "" and p.count_line() == "Selected: 3 records.", repr((p.cond_rows(), p.count_line())))
    # injection: nothing is added, nothing is run
    p.add_cond("name", "eq", 'x" or with name ne "', wait=1.5)
    arow("B2c", "a value with a double quote (x\" or with name ne \") is refused with the reason before any command is built: still one condition, the count line is the same",
         "only letters" in p.st() and p.cond_rows()[1] == "" and p.count_line() == "Selected: 3 records.", repr((p.st(), p.cond_rows(), p.count_line())))
    p.add_cond("name", "eq", 'x"; delete.file zzsent no.query; "', wait=1.5)
    arow("B2c2", "an attempt to run delete.file through a value is refused the same way, and the sentinel file is still there with its record",
         "only letters" in p.st() and p.cond_rows()[1] == "" and (dump_file(A1, "zzsent") or {}).get("s1") == ["sentinel"], repr((p.st(), p.cond_rows())))
    p.add_cond("name", "eq", "a;b", wait=1.5)
    arow("B2c3", "a semicolon, a dollar and a backquote in a value are refused as well", "only letters" in p.st() and p.cond_rows()[1] == "", repr(p.st()))
    p.add_cond("name", "eq", "a$b`c", wait=1.5)
    arow("B2c4", "...a dollar and a backquote too", "only letters" in p.st() and p.cond_rows()[1] == "" and (dump_file(A1, "cust") == ORIG), repr(p.st()))
    p.add_cond("status", "eq", "open")
    n2 = sep_count(A1, 'select cust with city eq "Paris" and with status eq "open"')
    arow("B2d", "a second condition, status equal to open, ALL of them: the count (%s) is the separate SELECT's" % n2, n2 == 2 and p.cond_rows()[1] == '2 status equal to "open"' and p.count_line() == "Selected: 2 records.", repr((p.cond_rows(), p.count_line(), n2)))
    p.typed("j", idle=2.0)
    n3 = sep_count(A1, 'select cust with city eq "Paris" or with status eq "open"')
    arow("B2e", "J switches to ANY of them: the count (%s) is the separate SELECT's with OR" % n3, n3 == 6 and p.count_line() == "Selected: 6 records." and "ANY" in p.line(6), repr((p.count_line(), n3, p.line(6)[:60])))
    p.typed("j", idle=1.5)
    p.add_cond("amt", "gt", "1")
    p.add_cond("name", "ne", "Zed")
    arow("B2f", "four conditions are in the list", all(r != "" for r in p.cond_rows()) and p.cond_rows()[3].startswith("4 name not equal to"), repr(p.cond_rows()))
    p.focus("Selection")
    p.typed("n", idle=1.5)
    arow("B2g", "a fifth condition is refused before any question is asked: at most 4", "at most 4 conditions" in p.st(), repr(p.st()))
    p.focus("Selection")
    p.key("end", 0.5)
    p.typed("x", idle=2.0)
    p.typed("x", idle=2.0)
    arow("B2h", "X takes the condition under the cursor out (twice): two conditions are left and the count line is recounted", p.cond_rows()[2] == "" and p.cond_rows()[3] == "" and p.cond_rows()[1] != "" and p.count_line().startswith("Selected:"), repr((p.cond_rows(), p.count_line())))
    p.typed("m", idle=1.2)
    p.downs(2)
    p.key("enter", idle=2.0)
    arow("B2i", "M, every record: the count is the count of the file (a separate session counts 7)", p.count_line() == "Selected: 7 records." and sep_count(A1, "select cust") == 7, repr(p.count_line()))
    p.typed("l", idle=1.2)
    p.key("enter", idle=2.0)
    ds = dump_file(A1, "$savedlists") or {}
    arow("B2j", "L, the saved list lp (it holds c1 c3 c1: a name twice): it is taken once, so 2 records", ds.get("lp") == ["c1", "c3", "c1"] and p.count_line() == "Selected: 2 records." and "saved list lp" in p.line(6), repr((ds.get("lp"), p.count_line(), p.line(6)[:60])))
    p.typed("m", idle=1.2)
    p.key("enter", idle=1.5)
    # a select that fails: the file is deleted by another session after it was chosen.  (A deleted DICTIONARY ITEM does not do it: the query processor of a running session keeps the
    # dictionary of a file it has used - seen here, run 2 and 4 - so the item is still accepted and the select takes 0 records.)
    p.choose_file("zzgone")
    p.add_cond("@id", "eq", "x")
    arow("B2k", "another file, zzgone, one condition on @id: the count is 0 records (a file that is there and matches nothing)", p.count_line() == "Selected: 0 records.", repr(p.count_line()))
    g.plain(A1, ["DELETE.FILE zzgone NO.QUERY"])
    p.add_cond("@id", "ne", "y")
    arow("B2l", "the file is deleted by another session; the next count meets the select's own words ('File not found'), not a count and not a 0, and the rows say what they said",
         p.count_line() == "Cannot select: File not found" and not os.path.exists(os.path.join(acct_dir(A1), "zzgone")), repr(p.count_line()))
    g.plain(A1, ["CREATE.FILE zzgone"])
    p.quit()
    reseed(A1)


# ------------------------------------------------------------------------------------------------- B3: the operations

@section
def section_b3():
    say("\n--- B3: the operations: what is refused, a D item picked by name, the closed set")
    p = Page(A1)
    p.choose_file("cust")
    p.add_op("add", 3, "abc")
    arow("B3a", "Add with a text that is not a number is refused and nothing is added", "not a number" in p.st() and p.op_rows()[0] == "", repr((p.st(), p.op_rows()[:2])))
    p.add_op("set", 0, None)
    arow("B3b", "attribute 0 is refused (it is the record id)", "whole number from 1 to 999" in p.st() and p.op_rows()[0] == "", repr(p.st()))
    p.add_op("set", 1000, None)
    arow("B3c", "attribute 1000 is refused", "whole number from 1 to 999" in p.st() and p.op_rows()[0] == "", repr(p.st()))
    p.add_op("copy", 2, src=2)
    arow("B3d", "Copy of an attribute onto itself is refused", "onto itself" in p.st() and p.op_rows()[0] == "", repr(p.st()))
    p.focus("Operations")
    p.typed("n", idle=1.2)
    p.key("enter", idle=1.0)                                           # set to a constant
    p.downs(4)                                                         # the pick list: (type a number), amt, city, name, status
    p.key("enter", idle=1.0)
    p.typed("q\r", idle=1.5)
    arow("B3e", "a D item picked by name from the dictionary: Set on 'status' shows attribute 4 (status) and its text", p.op_rows()[0].startswith('1 set to a constant attribute 4 (status) "q"'), repr(p.op_rows()[:2]))
    p.add_op("upper", 1)
    p.add_op("lower", 2)
    p.add_op("prepend", 4, "P-")
    p.add_op("replace", 4, "a", "b")
    p.add_op("add", 3, "-1.5")
    p.add_op("copy", 5, src=1)
    p.add_op("null", 6)
    rows = p.op_rows()
    arow("B3f", "the closed set is all there: set, upper case, lower case, prepend, replace, add, copy, null (with a negative decimal) - and the list is in the order they were added",
         [r.split(" ")[1] for r in rows[:8]] == ["set", "upper", "lower", "prepend", "replace", "add", "copy", "set"] and rows[5].endswith("-1.5") and rows[6].endswith("attribute 1") and rows[7].startswith("8 set to null"), repr(rows[:9]))
    p.focus("Operations")
    p.key("home", 0.5)
    p.typed("x", idle=1.2)
    arow("B3g", "X in the Operations list takes the operation under the cursor out", p.op_rows()[0].startswith("1 upper case") and p.op_rows()[7] == "", repr(p.op_rows()[:8]))
    p.quit()


# ------------------------------------------------------------------------------------------------- B4 to B6: the dry run, the apply, the undo

@section
def section_b4_b6():
    say("\n--- B4 to B6: the dry run writes nothing; apply; undo")
    reseed(A1, undo=False)
    p = Page(A1)
    scenario_paris(p)
    rows = p.op_rows()
    arow("B4", "the scenario is on the screen: city equal to Paris, three operations (append -ok to 1, add 5 to 3, replace open with ready in 4)",
         p.cond_rows()[0] == '1 city equal to "Paris"' and p.count_line() == "Selected: 3 records." and rows[0].startswith('1 append text attribute 1 "-ok"') and rows[1].startswith("2 add a number attribute 3 5")
         and rows[2].startswith('3 replace text attribute 4 "open" with "ready"'), repr((p.cond_rows()[0], p.count_line(), rows[:3])))
    k0 = p.keysrow()
    p.typed("a", idle=1.2)
    arow("B4a", "A is not on the function-key row before a dry run, and pressing it is refused with the reason and writes nothing", "A apply" not in k0 and "dry run of exactly these settings first" in p.st() and dump_file(A1, "cust") == ORIG, repr((k0, p.st())))
    ts = tree_state(os.path.join(acct_dir(A1), "cust"))
    p.typed("r", idle=2.5)
    p.until(lambda t: "Dry run of cust" in t)
    r28 = p.result(28)
    arow("B4b", "R: the dry run says 3 selected, 2 would change, 0 would stay as they are, 1 cannot be worked out (c6: its amt is text), 0 not found",
         r28 == "Dry run of cust: 3 selected, 2 would change, 0 would stay as they are, 1 cannot be worked out, 0 not found." and "the first that cannot be worked out is c6" in p.st(), repr((r28, p.st())))
    pv = " ".join(p.preview())
    arow("B4b2", "...and shows before and after of the two records that would change - c1 and c3 - and A is on the function-key row now",
         re.search(r"c1 a1 \[Alice\] -> \[Alice-ok\] a3 \[10\] -> \[15\] a4 \[open\] -> \[ready\]", pv) is not None and re.search(r"c3 a1 \[Carol\] -> \[Carol-ok\] a3 \[5\] -> \[10\]", pv) is not None
         and "c6" not in pv and "A apply" in p.keysrow(), repr((pv, p.keysrow())))
    arow("B4c", "THE DRY RUN WRITES NOTHING: a separate session reads every record of cust as it was, and no file under cust has a new size or modification time",
         dump_file(A1, "cust") == ORIG and tree_state(os.path.join(acct_dir(A1), "cust")) == ts, repr(dump_file(A1, "cust")))
    # an edit makes the dry run stale
    p.focus("Operations")
    p.key("home", 0.5)
    p.key("down", 0.5)
    p.typed("e", idle=1.2)
    p.key("enter", idle=1.0)                                           # the kind: add a number, as it is
    p.key("enter", idle=1.0)                                           # the attribute: type a number
    p.typed("\x15" + "3\r", idle=1.0)                                  # attribute 3 again (the ask starts with the old value)
    p.typed("\x15" + "6\r", idle=1.5)                                  # 6, not 5
    arow("B4d", "an edit (add 6 instead of 5) makes the dry run stale: the Result box says there is no dry run of these settings and A leaves the function-key row",
         p.op_rows()[1].startswith("2 add a number attribute 3 6") and p.result(28).startswith("No dry run of these settings yet") and "A apply" not in p.keysrow(), repr((p.op_rows()[1], p.result(28), p.keysrow())))
    p.typed("a", idle=1.2)
    arow("B4d2", "A after the edit is refused with the reason and writes nothing: the old dry run is not used for new settings", "dry run of exactly these settings first" in p.st() and dump_file(A1, "cust") == ORIG, repr((p.st(), dump_file(A1, "cust"))))
    p.typed("r", idle=2.5)
    p.until(lambda t: "Dry run of cust" in t)
    arow("B4e", "a new dry run of the new settings: it shows add 6 (c1 10 -> 16, c3 5 -> 11)", re.search(r"c1 a1 \[Alice\] -> \[Alice-ok\] a3 \[10\] -> \[16\]", " ".join(p.preview())) is not None and "A apply" in p.keysrow(), repr(p.preview()))
    # apply: the undo file is made through a box, Cancel is the default
    p.typed("a", idle=1.5)
    T = p.boxtext()
    arow("B5", "A, the undo file does not exist: a box shows the exact command create.file &bulk.undo& with Run and Cancel, and nothing is made yet", "create.file &bulk.undo&" in T and "Run" in T and "Cancel" in T and not os.path.exists(os.path.join(acct_dir(A1), "&bulk.undo&")), T[-400:])
    p.key("enter", idle=1.5)
    arow("B5a", "Enter is Cancel: no undo file is made, nothing is applied, and the page says so", not os.path.exists(os.path.join(acct_dir(A1), "&bulk.undo&")) and "nothing was applied" in p.st() and dump_file(A1, "cust") == ORIG, repr(p.st()))
    p.typed("a", idle=1.5)
    p.typed("r", idle=2.5)
    T = p.boxtext()
    arow("B5b", "A, Run: the undo file is made (a directory on the disk), and the apply's own box follows - it names the file, the three operations in words and the number of records, and says where the old records go",
         os.path.isdir(os.path.join(acct_dir(A1), "&bulk.undo&")) and "bulk update cust: 3 operations on 2 records" in T and 'append text on attribute 1: "-ok"' in T and "add a number on attribute 3: 6" in T
         and 'replace text on attribute 4: "open" with "ready"' in T and "&bulk.undo&" in T and "audit" in T, T[-600:])
    p.key("enter", idle=1.5)
    arow("B5c", "Enter is Cancel again: nothing is applied", dump_file(A1, "cust") == ORIG and "nothing was run" in p.st(), repr((p.st(), dump_file(A1, "cust"))))
    p.typed("a", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("wrong\r", idle=2.0)
    arow("B5d", "A, Run, and the WRONG file name typed: nothing is applied (a separate session reads every record as it was) and the page says which name was asked for",
         dump_file(A1, "cust") == ORIG and "cust" in p.st() and "nothing was run" in p.st(), repr((p.st(), dump_file(A1, "cust"))))
    off = audit_off()
    p.typed("a", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Applied to cust" in t)
    exp = expect(EXP_PARIS_6)
    got = dump_file(A1, "cust")
    arow("B5e", "A, Run, the right name: EXACTLY the two records the dry run named are changed (c1 and c3, as the preview said) and the other five - c6 whose amt is text included - are byte for byte as they were", got == exp, repr(got))
    a29 = p.result(29)
    arow("B5f", "the Result box says: 2 to change, 2 changed, 0 skipped (locked), 0 skipped (not as read), 0 errors", a29.startswith("Applied to cust: 2 to change, 2 changed, 0 skipped (locked by another session), 0 skipped (not as the dry run read them), 0 errors."), repr(a29))
    au = audit_new(off)
    arow("B5g", "the audit trail has ONE line from the run: bulk update file=cust records=2 (no data)", au is not None and len(re.findall(r"bulk update file=cust records=2\b", au)) == 1 and "bulk update" in au and au.count("bulk update") == 1, repr(au[-300:] if au else au))
    ud = dump_file(A1, "&bulk.undo&") or {}
    hdr = ud.get("last", [])
    arow("B5h", "the undo file holds the header (cust, 2 records, done) and one record for each changed record: its id, a digest, and the record as it was",
         len(hdr) == 6 and hdr[0] == "bulk-undo" and hdr[1] == "cust" and hdr[4] == "2" and hdr[5] == "done" and sorted(k for k in ud if k != "last") == ["1", "2"]
         and {ud["1"][0]: ud["1"][2:], ud["2"][0]: ud["2"][2:]} == {"c1": ORIG["c1"], "c3": ORIG["c3"]} and all(re.match(r"^[0-9a-f]{32}$", ud[k][1]) for k in ("1", "2")), repr(ud))
    k0 = p.keysrow()
    p.typed("a", idle=1.2)
    arow("B5i", "the dry run is spent: A leaves the function-key row, U joins it, and A pressed again writes nothing more", "A apply" not in k0 and "U undo" in k0 and dump_file(A1, "cust") == exp and "dry run of exactly these settings first" in p.st(), repr((k0, p.st())))
    # undo: a record changed since is left alone
    write_field(A1, "cust", "c3", 3, "99")
    mid = dump_file(A1, "cust")
    p.typed("u", idle=1.5)
    T = p.boxtext()
    arow("B6", "U: a box shows 'bulk undo cust: 2 records' with Run and Cancel", "bulk undo cust: 2 records" in T and "Run" in T and "Cancel" in T, T[-400:])
    p.key("enter", idle=1.5)
    arow("B6a", "Enter is Cancel: nothing is put back", dump_file(A1, "cust") == mid and mid["c3"][2] == "99", repr(dump_file(A1, "cust")))
    p.typed("u", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Undo of the last run" in t)
    got = dump_file(A1, "cust")
    exp2 = expect({"c3": ["Carol-ok", "Paris", "99", "closed"]})
    arow("B6b", "U, Run, the name: c1 is put back exactly as it was; c3, which another session changed since the run (amt 99), is LEFT ALONE; nothing else moved", got == exp2, repr(got))
    a29 = p.result(29)
    arow("B6c", "the Result box says: 1 put back, 1 left (changed since), 0 gone, 0 locked, 0 errors", a29.startswith("Undo of the last run on cust: 1 put back, 1 left (changed since), 0 left (gone), 0 skipped (locked), 0 errors."), repr(a29))
    ud = dump_file(A1, "&bulk.undo&") or {}
    k0 = p.keysrow()
    p.typed("u", idle=1.2)
    arow("B6d", "the header says undone, U leaves the function-key row and a second U is refused", ud.get("last", [""] * 6)[5] == "undone" and "U undo" not in k0 and "put back already" in p.st(), repr((ud.get("last"), k0, p.st())))
    p.quit()
    reseed(A1)


# ------------------------------------------------------------------------------------------------- B7: every operation, and the undo that brings the old records back

@section
def section_b7():
    say("\n--- B7: every operation of the closed set on seven records; the undo brings the old records back byte for byte")
    reseed(A1, undo=True)
    p = Page(A1)
    p.choose_file("cust")
    p.typed("m", idle=1.2)
    p.downs(2)
    p.key("enter", idle=2.0)
    p.add_op("upper", 1)
    p.add_op("lower", 2)
    p.add_op("prepend", 4, "ZZ-")
    p.add_op("replace", 4, "Z", "y")
    p.add_op("set", 5, "new")
    p.add_op("copy", 6, src=1)
    p.add_op("add", 3, "-2.5")
    p.typed("r", idle=3.0)
    p.until(lambda t: "Dry run of cust" in t)
    arow("B7", "every record, seven operations: the dry run says 7 selected, 5 would change, 2 cannot be worked out (c6: text in amt, c7: nothing in amt), and the disk is as it was",
         p.result(28).startswith("Dry run of cust: 7 selected, 5 would change, 0 would stay as they are, 2 cannot be worked out, 0 not found.") and dump_file(A1, "cust") == ORIG, repr((p.result(28), p.op_rows()[:7])))
    p.typed("a", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Applied to cust" in t)
    exp = expect({
        "c1": ["ALICE", "paris", "7.5", "yy-open", "new", "ALICE"],
        "c2": ["BOB", "london", "17.5", "yy-open", "new", "BOB"],
        "c3": ["CAROL", "paris", "2.5", "yy-closed", "new", "CAROL"],
        "c4": ["DAVE", "rome", "97.5", "yy-open", "new", "DAVE"],
        "c5": ["EVE", "paris", "4.5", "yy-open", "new", "EVE"],
    })
    got = dump_file(A1, "cust")
    arow("B7a", "applied: upper, lower, prepend, replace, set past the end of the record, copy and add -2.5 did exactly what the table says to the five records that could be worked out; c6 and c7 are untouched, every attribute of them",
         got == exp, repr(got))
    p.typed("u", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Undo of the last run" in t)
    got = dump_file(A1, "cust")
    arow("B7b", "U: all five records are back exactly as they were - the fields past the old end of the record included", got == ORIG and p.result(29).startswith("Undo of the last run on cust: 5 put back, 0 left (changed since)"), repr((got, p.result(29))))
    # replace with nothing, and null
    p.focus("Selection")
    p.typed("m", idle=1.2)
    p.key("enter", idle=1.5)
    p.add_cond("status", "eq", "new")
    p.focus("Operations")
    while p.op_rows()[0] != "":
        p.key("home", 0.4)
        p.typed("x", idle=0.8)
    p.add_op("replace", 4, "ew", "")
    p.add_op("null", 2)
    p.typed("r", idle=2.5)
    p.until(lambda t: "Dry run of cust" in t)
    arow("B7c", "status equal to new, replace 'ew' with nothing in 4 and null in 2: the dry run says 1 selected and 1 would change", p.result(28).startswith("Dry run of cust: 1 selected, 1 would change"), repr(p.result(28)))
    p.typed("a", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Applied to cust" in t)
    got = dump_file(A1, "cust")
    arow("B7d", "c7 is Gina, nothing, nothing, n: 'new' lost its 'ew' (replace with nothing) and the city is null - and no other record moved", got == expect({"c7": ["Gina", "", "", "n"]}), repr(got))
    p.quit()
    reseed(A1)


# ------------------------------------------------------------------------------------------------- B8: a record another session holds locked

@section
def section_b8():
    say("\n--- B8: a record another session holds locked is skipped and counted")
    reseed(A1, undo=True)
    hd = Holder(A1)
    for _ in range(40):
        if "ZZHOLD holding" in hd.text():
            break
        time.sleep(0.5)
    if "ZZHOLD holding" not in hd.text():
        bail("the second session did not take its lock on c2:\n" + hd.text()[-300:])
    p = Page(A1)
    p.choose_file("cust")
    p.typed("m", idle=1.2)
    p.downs(2)
    p.key("enter", idle=2.0)
    p.add_op("set", 4, "x")
    p.typed("r", idle=3.0)
    p.until(lambda t: "Dry run of cust" in t)
    arow("B8", "every record, set attribute 4 to x: the dry run (it takes no lock) says 7 selected, 7 would change", p.result(28).startswith("Dry run of cust: 7 selected, 7 would change"), repr(p.result(28)))
    off = audit_off()
    p.typed("a", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Applied to cust" in t, 30)
    got = dump_file(A1, "cust")
    exp = {k: list(v) for k, v in ORIG.items()}
    for k in exp:
        if k != "c2":
            exp[k][3] = "x"
    arow("B8a", "the record the other session holds (c2) is NOT written - a separate session reads it as it was - and the six others are", got == exp, repr(got))
    arow("B8b", "the Result box counts it: 7 to change, 6 changed, 1 skipped (locked by another session), 0 not as read, 0 errors", p.result(29).startswith("Applied to cust: 7 to change, 6 changed, 1 skipped (locked by another session), 0 skipped (not as the dry run read them), 0 errors."), repr(p.result(29)))
    au = audit_new(off)
    arow("B8c", "and the audit line says how many were written: records=6", au is not None and re.search(r"bulk update file=cust records=6\b", au) is not None, repr(au[-200:] if au else au))
    p.quit()
    release_holders()
    reseed(A1)


# ------------------------------------------------------------------------------------------------- B9: a record that changed after the dry run

@section
def section_b9():
    say("\n--- B9: a record that changed after the dry run is skipped and counted")
    reseed(A1, undo=True)
    p = Page(A1)
    p.choose_file("cust")
    p.add_cond("city", "eq", "Paris")
    p.add_op("set", 4, "z")
    p.typed("r", idle=2.5)
    p.until(lambda t: "Dry run of cust" in t)
    arow("B9", "city equal to Paris, set attribute 4 to z: the dry run says 3 selected, 3 would change", p.result(28).startswith("Dry run of cust: 3 selected, 3 would change"), repr(p.result(28)))
    write_field(A1, "cust", "c3", 3, "77")
    mid = dump_file(A1, "cust")
    p.typed("a", idle=1.5)
    p.typed("r", idle=1.5)
    p.typed("cust\r", idle=1.0)
    p.until(lambda t: "Applied to cust" in t)
    got = dump_file(A1, "cust")
    exp = expect({"c1": ["Alice", "Paris", "10", "z"], "c3": ["Carol", "Paris", "77", "closed"], "c6": ["Frank", "Paris", "abc", "z"]})
    arow("B9a", "c3 was changed by another session after the dry run: it is NOT written (it keeps amt 77 and status closed); c1 and c6 are", got == exp and mid["c3"][2] == "77", repr(got))
    arow("B9b", "the Result box counts it: 3 to change, 2 changed, 0 locked, 1 skipped (not as the dry run read them), 0 errors", p.result(29).startswith("Applied to cust: 3 to change, 2 changed, 0 skipped (locked by another session), 1 skipped (not as the dry run read them), 0 errors."), repr(p.result(29)))
    p.quit()
    reseed(A1)


# ------------------------------------------------------------------------------------------------- B10: help, a small window, another file

@section
def section_b10():
    say("\n--- B10: help, a window under 140 by 43, another file clears the selection and the operations")
    p = Page(A1)
    p.click(135, 2)
    T = norm(p.text())
    arow("B10", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    p.key("esc", idle=1.0)
    p.key("f1", idle=1.2)
    T = norm(p.text())
    arow("B10a", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    p.key("esc", idle=1.0)
    p.choose_file("cust")
    p.add_cond("city", "eq", "Paris")
    p.add_op("upper", 1)
    p.choose_file("ordr")
    arow("B10b", "another file (ordr): the conditions, the operations and the dry run of cust are gone, the count line starts again", "File: ordr" in p.line(2) and all(r == "" for r in p.cond_rows()) and all(r == "" for r in p.op_rows()) and p.count_line() == "No condition yet: N adds one.",
         repr((p.line(2)[:60], p.cond_rows(), p.op_rows()[:2], p.count_line())))
    p.quit()
    h = H(account=A1, cols=100, rows=30)
    SCREEN[0] = h
    h.typed("tool.bulk\r", idle=3.0)
    T = h.text()
    arow("B10c", "a window under 140 by 43 gets no page", "Which records" not in T and "What to do to them" not in T, T[-300:])
    h.end()


# ------------------------------------------------------------------------------------------------- B11: the undo file is the account's own

@section
def section_b11():
    say("\n--- B11: the undo file is used only if it is this account's own &bulk.undo& (voc-edit ON, bp-edit and dict-edit OFF: the VOC name pointed at bp, then at the dictionary of cust)")
    bpdir = os.path.join(acct_dir(A3), "bp")

    def press_a():
        p = Page(A3)
        p.choose_file("cust")
        p.typed("m", idle=1.2)
        p.downs(2)
        p.key("enter", idle=2.0)
        p.add_op("append", 1, "-x")
        p.typed("r", idle=3.0)
        p.until(lambda t: "Dry run of cust" in t)
        p.typed("a", idle=2.0)
        T = norm(p.text())
        if re.search(r"Run this command|Update these records|Put these records back", T):                                   # only a page that did not refuse (a mutant) has a box: answer it, so that the evidence is the disk
            p.typed("r", idle=1.5)
            p.typed("cust\r", idle=1.0)
            p.until(lambda t: "Applied to cust" in t or "cannot be written" in t, 25)
        p.quit()
        return T

    out = g.plain(A3, ["RUN bp zzplant bp"])
    if not has(out, r"^ZZPL done$"):
        bail("the pointer &bulk.undo& -> bp was not planted in %s:\n%s" % (A3, "\n".join(out[-6:])))
    before = sorted(os.listdir(bpdir))
    cust = dump_file(A3, "cust")
    T = press_a()
    arow("B11a", "A with &bulk.undo& pointing at bp: the page refuses (bp is not a dynamic file of this account), says nothing was applied, and shows no box",
         ("is not a dynamic file of this account" in T or "does not stand in this account's own directory" in T) and "nothing was applied" in T and not re.search(r"Run this command|Update these records|Put these records back", T), T[-500:])
    after = sorted(os.listdir(bpdir))
    arow("B11b", "...and bp is as it was - the same programs, no record 'last' written into it, nothing cleared - and no record of cust changed",
         after == before and "last" not in after and dump_file(A3, "cust") == cust, repr((sorted(set(after) ^ set(before)), cust == dump_file(A3, "cust"))))
    g.plain(A3, ["DELETE VOC &bulk.undo&"])
    # the dictionary of cust is a dynamic file in the account's own directory, but not the undo file: only the path question refuses it
    ddict = dump_file(A3, "cust", "dict")
    out = g.plain(A3, ["RUN bp zzplant custdic"])
    if not has(out, r"^ZZPL done$"):
        bail("the pointer &bulk.undo& -> the dictionary of cust was not planted in %s:\n%s" % (A3, "\n".join(out[-6:])))
    T = press_a()
    arow("B11c", "A with &bulk.undo& pointing at the dictionary of cust (a dynamic file, dict-edit OFF): the page refuses - the name does not stand in this account's own directory - says nothing was applied, and shows no box",
         "does not stand in this account's own directory" in T and "nothing was applied" in T and not re.search(r"Run this command|Update these records|Put these records back", T), T[-500:])
    arow("B11d", "...and the dictionary of cust is exactly as it was (no record 'last', nothing cleared) and no record of cust changed",
         dump_file(A3, "cust", "dict") == ddict and "last" not in (dump_file(A3, "cust", "dict") or {}) and dump_file(A3, "cust") == cust, repr((ddict == dump_file(A3, "cust", "dict"), cust == dump_file(A3, "cust"))))
    g.plain(A3, ["DELETE VOC &bulk.undo&"])


# ------------------------------------------------------------------------------------------------- the mutants

# name: (the changes to the sandbox's copy of the page [(old, new) each found exactly once], the rows that must fail and no others, the row after which the section stops, the section)
MUTANTS = {
    "stale-dry-run-accepted": ([("   gosub drop.dry\n   gosub draw.all\n   return\n\n* X in the Operations list", "   gosub draw.all\n   return\n\n* X in the Operations list"),
                                ("   if not(dr.valid) or dr.fp # fp then\n", "   if 0 then\n")], ["B4a", "B4d", "B4d2"], "B4d2", "b4"),       # B4a too: with no dry run at all the gate is gone
    "apply-asks-no-name": ([("call $tk_confirm(sent, lines, bf, res, cmsg, sysmsg(11954))", "call $tk_confirm(sent, lines, '', res, cmsg, sysmsg(11954))")], ["B5d"], "B5d", "b4"),      # 26 Oct 26: the sixth argument (the box title) since the faults batch
    "dry-run-writes": ([("                  dr.md5 := digest(rec, 0, 'MD5')\n", "                  dr.md5 := digest(rec, 0, 'MD5')\n                  write newrec on fv, id\n")], ["B4c"], "B4c", "b4"),
    "no-undo-records": ([("               write id : @fm : digest(newrec, 0, 'MD5') : @fm : rec on uf, n.written on error\n", "               n.err += 0\n               write 'x' on uf, 'never' on error\n")], ["B5h"], "B5h", "b4"),
    "undo-ignores-changed-since": ([("         case digest(cur, 0, 'MD5') # uemd\n", "         case 0\n")], ["B6b", "B6c"], "B6c", "b4"),
    "apply-ignores-moved": ([("         case digest(rec, 0, 'MD5') # emd\n", "         case 0\n")], ["B9a", "B9b"], "B9b", "b9"),
    "lock-counted-as-moved": ([("n.lock += 1", "n.moved += 1")], ["B8b"], "B8c", "b8"),
    "audit-counts-todo": ([("void kernel(K$AUDIT, 'bulk update file=' : bf : ' records=' : n.written)", "void kernel(K$AUDIT, 'bulk update file=' : bf : ' records=' : n.todo)")], ["B8c"], "B8c", "b8"),
    "kernel-words-dropped": ([("      case not(ceo)\n", "      case 0\n")], ["B1h", "B1h2", "B1h3"], "B1h3", "b1"),
    "undo-file-unchecked": ([("   open UNDOF to uf then\n      gosub check.undo\n      if uck then\n         uok = 1\n      end else\n         close uf\n         msg = ucw : ': nothing was applied'\n      end\n      return\n   end", "   open UNDOF to uf then\n      uok = 1\n      return\n   end"),
                             ("   gosub check.undo\n   if not(uck) then\n      close fv\n      close uf\n      msg = ucw : ': nothing was applied'\n      return\n   end\n   clearfile uf", "   clearfile uf")], ["B11a", "B11b"], "B11b", "b11"),
    "quote-allows-double-quote": ([("0123456789 .,:+-_/@()%*'\n", "0123456789 .,:+-_/@()%*\"'\n")], ["B2c"], "B2c", "b2"),
}
SECTIONS = {"b1": section_b1, "b2": section_b2, "b4": section_b4_b6, "b8": section_b8, "b9": section_b9, "b11": section_b11}


def mutate(name):
    changes = MUTANTS[name][0]
    src = open(SRC, encoding="utf-8", errors="replace").read()
    for old, new in changes:
        if src.count(old) != 1:
            bail("mutant %s: the text to change is found %d times, not once: %r" % (name, src.count(old), old[:80]))
        src = src.replace(old, new)
    g.put(sandbox_page(), src)
    compile_page()


def unmutate():
    shutil.copyfile(SRC, sandbox_page())
    compile_page()


def run_mutant(name):
    changes, kills, last, sec = MUTANTS[name]
    FAILED_IDS[:] = []
    mutate(name)
    say("\nsandbox-tool-bulk: MUTANT %s: the rows that must fail, and nothing else: %s" % (name, ", ".join(kills)))
    LAST[0] = last
    try:
        SECTIONS[sec]()
    finally:
        LAST[0] = None
        unmutate()
    want = sorted(set(kills))
    got = sorted(set(FAILED_IDS))
    ok = want == got
    say("sandbox-tool-bulk: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (name, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
    return ok


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant != "all" and not all(m in MUTANTS for m in mutant.split(",")):
        bail("usage: sandbox-tool-bulk.py <dir> [--build] [--mutant=%s|all] (names may be joined with commas)" % "|".join(MUTANTS))
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), None)
    verdicts = {}
    try:
        sh.setup("sandbox-tool-bulk.py")
        install_sources()
        compile_page()
        setup_fixtures()
        if mutant is None:
            plan = [("b1", section_b1), ("b2", section_b2), ("b3", section_b3), ("b4", section_b4_b6), ("b7", section_b7), ("b8", section_b8), ("b9", section_b9), ("b10", section_b10), ("b11", section_b11)]
            for key, fn in plan:
                if only is None or key in only.split(","):
                    fn()
        else:
            for name in (list(MUTANTS) if mutant == "all" else mutant.split(",")):
                verdicts[name] = run_mutant(name)
    finally:
        close_pages()
        release_holders()
        sh.teardown()
    say("\nsandbox-tool-bulk: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        for n, ok in verdicts.items():
            say("sandbox-tool-bulk: mutant %-30s %s" % (n, "killed by its own rows" if ok else "NOT AS EXPECTED"))
        return 0 if verdicts and all(verdicts.values()) else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
