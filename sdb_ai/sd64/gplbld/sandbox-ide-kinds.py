#!/usr/bin/env python3
#
# sandbox-ide-kinds.py - the IDE's record kinds and locks (the editor merge, stage B; ~/Documents/Audits/TUI/Opus_TUI_Plan.txt section 11).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-kinds.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every
# row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 28 Oct 26 dm  New with stage B.  WRITTEN, NOT RUN (the owner's rule for the full-screen phases: one complete run at the end).  The free check that holds the
#               same properties as text is test-idekinds-units.py; the token rows of sandbox-recarr.py (E0, E, F) were moved to a data file with it.
# 28 Oct 26 dm  Section NA (the owner's approval of 28 Oct): a record holding bytes 128 to 247 opens read-only, typing changes nothing, Ctrl-S, Replace, Edit as
#               fields, Save as and Write a copy are refused in a box before anything is asked, the disk keeps every byte, and a record whose only high bytes
#               are SD's marks is NOT read-only (control).  The fixture gains r5; S0 does not read it.  WRITTEN, NOT RUN.  The AI edit's refusal is held as
#               text only (test-idekinds-units.py K32): this suite has no fake provider.
# END-HISTORY
#
# WHAT RUNS.  The IDE on a PSEUDO-TERMINAL at 140 by 42 (sandbox-ide.py's Ide, in the sandbox user's own account, as sandbox-recarr.py drives it), and pipe
# sessions in the same account for the fixtures and to read the disk back.  EVERY VERDICT ON A RECORD IS READ FROM THE DISK by a probe program (zzkprobe), never
# from what the IDE said; a lock is judged by ANOTHER SESSION asking for it (zzklk: READU ... LOCKED prints the holder, or it got the lock).  A record is held by a
# LIVE pipe session (zzkhold) that takes the lock and waits for a line on its input, so that it can be let go cleanly (a killed session keeps its locks until a
# cleanup).  The gate rows (section G) come LAST: they need sandbox-gates.py's prepare(), which makes the sandbox user an ordinary user unless SDTEST_ADMIN is set.
#
#   S0   setup and controls: the fixture and the probes compile; the probe reads every record as written; the lock probe GETS a free record (so LOCKED means something)
#   D    a dictionary item: `ide dict file id` opens it (dict on the status line and the tab), its edit is saved to the DICTIONARY (the data part untouched); the
#        tree shows a (dictionary) node under the file, whose items appear only after Return on it
#   V    a VOC record: `ide voc id` opens it in the token form (a value mark shows as :@vm:) and saves it
#   B    a big data file (5,000 records): `ide file` lists it within a time bound and says that only the first 2,000 are listed; a small file says nothing (control)
#   L    locks: a record another session holds opens read-only (the status line names the user), typing changes nothing and Ctrl-S is refused with the disk
#        unchanged; once let go it opens writable and saves; while a tab holds it another session cannot lock it, and after a save too (WRITEU kept it); Ctrl-W,
#        Ctrl-Q and a hang-up each give it back
#   M    a missing id: `ide file newid` opens a NEW tab (status New record ...), nothing is on the disk until Ctrl-S, and a discard leaves nothing
#   T    token mode by kind: a data record with no marks takes :@vm: typed into it as a mark; a PROGRAM (bp) that holds a value mark is never shown with :@vm:
#   Q    CREATING.SEQKEY: `ide file creating.seqkey` opens the file's next sequential id as a new record, and the save writes it there
#   SL   an active select list: SELECT then `ide file` opens the listed records in tabs and lists them
#   I    Go / Open the include: on a $include line it opens the include record in a tab; on another line it says so and opens nothing
#   C    a collection file's record is refused with a message and the IDE stays up (a plain READ of one would abort it)
#   G    the gate: in an ordinary account whose dict edit gate is off, `ide dict ...` and Ctrl-S are refused with the dict.edit message and the item is unchanged;
#        control, the same account's data record saves

import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sb = _load("sandbox_ide_for_kinds", "sandbox-ide.py")                     # Ide (the pty driver), sess (a pipe session), the key names
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F10, RIGHT, DOWN, RET, ESC, END = sb.F10, sb.RIGHT, sb.DOWN, sb.RET, sb.ESC, sb.END
CTRL_Q, CTRL_S, CTRL_W = sb.CTRL_Q, sb.CTRL_S, sb.CTRL_W
GO_INCLUDE = 7                       # Down presses from Go to line to Open the include: Go to line, Next error, Next tab, Previous tab, Files and records, Next pane, Previous pane
passed = failed = 0
BOX = SYSD = None
LIVES = []

DF = "zzkd" + RUN                    # a data file with a dictionary
BIG = "zzkbig" + RUN                 # 5,000 records
COL = "zzkcol" + RUN                 # a collection file
VOCID = "zzkv" + RUN
SRC, INC, HDR = "zzksrc" + RUN, "zzkinc" + RUN, "zzkhdr" + RUN
NEW1, NEW2 = "zzknew1" + RUN, "zzknew2" + RUN


def say(s=""):
    print(s)
    sys.stdout.flush()


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))
    return ok


def bail(msg):
    say("sandbox-ide-kinds: CANNOT RUN - " + msg)
    teardown()
    sys.exit(2)


FIX = """   execute 'CREATE.FILE %(df)s' capturing j
   execute 'CREATE.FILE %(big)s' capturing j
   execute 'CREATE.FILE %(col)s COLLECTION' capturing j
   open '%(df)s' to d else stop 'KFIX no data file'
   open 'DICT', '%(df)s' to dd else stop 'KFIX no dictionary'
   write 'Don':@vm:'Henry':@fm:'x' on d, 'r1'
   write 'plain text' on d, 'r2'
   write 'locked one' on d, 'r3'
   write 'tab one' on d, 'r4'
   write 'D':@fm:'1':@fm:'':@fm:'Name':@fm:'20L':@fm:'S' on dd, 'name'
   write 'caf':char(233):@fm:'na':char(195):char(169):'ve' on d, 'r5'
   open '%(big)s' to b else stop 'KFIX no big file'
   for i = 1 to 5000
      write 'big ':i on b, 'b':i
   next i
   open '%(col)s' to cf else stop 'KFIX no collection file'
   c = collection()
   c{'a'} = 1
   write c on cf, 'c1'
   open 'bp' to p else stop 'KFIX no bp'
   write 'x = 1':@vm:'2':@fm:'end' on p, '%(src)s'
   write '$include %(hdr)s':@fm:'crt ZZK':@fm:'end' on p, '%(inc)s'
   write 'equ ZZK to 1' on p, '%(hdr)s'
   open 'voc' to v else stop 'KFIX no voc'
   write 'X':@fm:'a':@vm:'b' on v, '%(voc)s'
   crt 'KFIX done'
end
"""
# every record a row judges, with ^ for a field mark, | for a value mark and ~ for a subvalue mark
PROBE = """   open '%(df)s' to d else stop 'KPROBE no data file'
   open 'DICT', '%(df)s' to dd else stop 'KPROBE no dictionary'
   open 'voc' to v else stop 'KPROBE no voc'
   ids = 'r1':@fm:'r2':@fm:'r3':@fm:'r4':@fm:'%(n1)s':@fm:'%(n2)s':@fm:'1'
   for i = 1 to 7
      read r from d, ids<i> then crt 'KREC ':ids<i>:' [':convert(@fm:@vm:@sm, '^|~', r):']' else crt 'KREC ':ids<i>:' <absent>'
   next i
   read r from dd, 'name' then crt 'KREC dict.name [':convert(@fm:@vm:@sm, '^|~', r):']' else crt 'KREC dict.name <absent>'
   read r from d, 'name' then crt 'KREC data.name [':r:']' else crt 'KREC data.name <absent>'
   read r from v, '%(voc)s' then crt 'KREC voc [':convert(@fm:@vm:@sm, '^|~', r):']' else crt 'KREC voc <absent>'
   crt 'KPROBE END'
end
"""
# another session asks for the lock of a record of the data file: LOCKED and the holder, or GOT (and lets it go at once)
LOCKP = """   id = field(@sentence, ' ', 4)
   open '%(df)s' to d else stop 'KLK no data file'
   readu x from d, id locked
      crt 'KLK LOCKED ':status()
      stop
   end then null else null
   crt 'KLK GOT'
   release d, id
end
"""
# a live session that holds the lock of r3 until it reads a line
HOLD = """   open '%(df)s' to d else stop 'KHOLD no data file'
   readu x from d, 'r3' else null
   crt 'KHOLD holding ':@userno
   input go
   release d, 'r3'
   crt 'KHOLD done'
end
"""


# 28 Oct 26: r5 as hex bytes (a latin-1 e-acute and a UTF-8 one), and whether a copy was written anywhere
NAPROBE = """   open '%(df)s' to d else stop 'KNA no data file'
   read r from d, 'r5' then crt 'KNA r5 ':oconv(r, 'MX0C') else crt 'KNA r5 <absent>'
   read r from d, 'zzknacopy' then crt 'KNA copy present' else crt 'KNA copy absent'
   crt 'KNA END'
end
"""
R5_HEX = "636166E9FE6E61C3A97665"           # caf e9 | FM | na c3 a9 ve


def put(name, text):
    with open(os.path.join(SYSD, "bp", name), "w") as fh:
        fh.write(text % SUBS)


SUBS = {"df": DF, "big": BIG, "col": COL, "src": SRC, "inc": INC, "hdr": HDR, "voc": VOCID, "n1": NEW1, "n2": NEW2}


def disk():
    o = sb.sess(BOX, "RUN bp zzkprobe" + RUN)
    d = dict(re.findall(r"(?m)^KREC (\S+) (.*?)\s*$", o))
    if "KPROBE END" not in o:
        say("    (the probe did not reach its end: %r)" % o[-300:])
    return d


def lock_of(rid):
    """'GOT', 'LOCKED <user>' or None, from another session asking for the record's lock"""
    o = sb.sess(BOX, "RUN bp zzklk%s %s" % (RUN, rid))
    m = re.search(r"(?m)^KLK (GOT|LOCKED \d+)\s*$", o)
    return m.group(1) if m else None


class Live:
    """A session on a pipe kept open, holding r3 until a line is written to it."""

    def __init__(self):
        env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"))
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_TTY", None)
        self.out = os.path.join(BOX, "kinds-live-%s.out" % RUN)
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([os.path.join(SYSD, "bin", "sd")], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT,
                                  cwd=os.path.join(BOX, "user_accounts"), env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\nRUN bp zzkhold%s\n" % RUN)
        self.p.stdin.flush()
        say("    > live holder: pid %d, RUN bp zzkhold%s (cwd %s)" % (self.p.pid, RUN, os.path.join(BOX, "user_accounts")))
        LIVES.append(self)

    def text(self):
        self.fh.flush()
        with open(self.out, errors="replace") as f:
            return ANSI.sub("", f.read())

    def user(self, secs=15.0):
        end = time.time() + secs
        while time.time() < end:
            m = re.search(r"KHOLD holding (\d+)", self.text())
            if m:
                return m.group(1)
            time.sleep(0.5)
        return None

    def let_go(self):
        try:
            self.p.stdin.write("go\nOFF\n")
            self.p.stdin.flush()
        except OSError:
            pass
        try:
            self.p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.kill()
        return "KHOLD done" in self.text()

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


def tab_row(e):
    L = e.lines()
    return L[2] if len(L) > 2 else ""


def tree_text(e):
    return "\n".join(l[:28] for l in e.lines()[3:39])          # rows 3 to 38: row 39 is the form's bottom border since the IDE's foot (28 Oct 26, 140 by 43)


def editor_text(e):
    return "\n".join(l[28:] for l in e.lines()[3:39])


def quit_discard(e):
    """Ctrl-Q, and Discard to every 'has changes' question"""
    e.keys(CTRL_Q)
    n = 0
    while "has changes" in e.text() and n < 6:
        e.keys(DOWN, RET)
        n += 1


def in_ide(e):
    return not e.s.exited and "IDE: " in "\n".join(e.lines()[:3])


def done(e):
    """Leave the IDE the way a person does (Ctrl-Q, Discard), so that it gives its locks back, then log off.  A session that is killed keeps its locks until a
    cleanup, which would make every later lock row lie"""
    if in_ide(e):
        quit_discard(e)
        time.sleep(0.5)
    e.end()


# ---- S0 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_setup():
    say("\n--- S0: the fixture, the probes, and the instruments' controls ----------------------------------------------------------")
    put("zzkfix" + RUN, FIX)
    put("zzkprobe" + RUN, PROBE)
    put("zzklk" + RUN, LOCKP)
    put("zzkhold" + RUN, HOLD)
    o = sb.sess(BOX, "BASIC bp zzkfix%s zzkprobe%s zzklk%s zzkhold%s" % (RUN, RUN, RUN, RUN), "RUN bp zzkfix" + RUN)
    ok = re.search(r"(?m)^Compiled 4 program\(s\) with no errors", o) is not None and "KFIX done" in o
    row("S0 setup: the fixture and the three probes compile and the fixture ran to its end", ok, o[-600:])
    if not ok:
        bail("the fixture was not made")
    d = disk()
    want = {"r1": "[Don|Henry^x]", "r2": "[plain text]", "r3": "[locked one]", "r4": "[tab one]", NEW1: "<absent>", NEW2: "<absent>", "1": "<absent>",
            "dict.name": "[D^1^^Name^20L^S]", "data.name": "<absent>", "voc": "[X^a|b]"}
    bad = {k: (d.get(k), v) for k, v in want.items() if d.get(k) != v}
    row("S0 control: the probe reads every record as the fixture wrote it", not bad, repr(bad))
    row("S0 control: the lock probe GETS a record nobody holds (so a LOCKED below is a lock, not a broken probe)", lock_of("r1") == "GOT", repr(lock_of("r1")))


# ---- D: a dictionary item -----------------------------------------------------------------------------------------------------------------------------------------------
def section_dict():
    say("\n--- D: a dictionary item ------------------------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE DICT %s name" % DF)
    e.quiet()
    st, tabs, ed = e.status(), tab_row(e), editor_text(e)
    row("D1 `ide dict file id` opens the dictionary item: the status line says dict %s name, the tab says dict name, the editor shows its fields (Name, 20L)" % DF,
        ("dict %s name" % DF) in st and "dict name" in tabs and "Name" in ed and "20L" in ed, "%r | %r | %r" % (st, tabs[:80], ed[:200]))
    row("D1b the tree has the file's (dictionary) node opened, with the item name under it", "(dictionary)" in tree_text(e) and "name" in tree_text(e), tree_text(e)[:600])
    e.keys("ZZ")
    e.keys(CTRL_S)
    e.quiet()
    d = disk()
    row("D2 typed ZZ and Ctrl-S: the DICTIONARY item is ZZD^1^^Name^20L^S on the disk and the data part has no record name",
        d.get("dict.name") == "[ZZD^1^^Name^20L^S]" and d.get("data.name") == "<absent>", repr((d.get("dict.name"), d.get("data.name"), e.status())))
    done(e)

    e = sb.Ide(BOX, "IDE %s" % DF)
    e.quiet()
    t0 = tree_text(e)
    row("D3 `ide file` shows a (dictionary) node under the file, and the dictionary's items are NOT listed before it is opened (name is not in the tree)",
        "(dictionary)" in t0 and not re.search(r"(?m)^\s*\S?\s*name\s*$", t0), t0[:600])
    e.keys(DOWN)                                      # from the file to its first node, the dictionary
    e.keys(RET)
    e.quiet()
    t1 = tree_text(e)
    row("D4 Return on the (dictionary) node lists its item name", "name" in t1 and "(dictionary)" in t1, t1[:600])
    done(e)


# ---- V: a VOC record ----------------------------------------------------------------------------------------------------------------------------------------------------
def section_voc():
    say("\n--- V: a VOC record ------------------------------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE VOC %s" % VOCID)
    e.quiet()
    ed = editor_text(e)
    row("V1 `ide voc id` opens the VOC record and shows its value mark as :@vm: (a VOC record is shown in the token form by its kind)", "a:@vm:b" in ed, ed[:300])
    e.keys(DOWN, END, ":@vm:c")
    e.keys(CTRL_S)
    e.quiet()
    d = disk()
    row("V2 :@vm:c typed at the end of field 2 and Ctrl-S: the VOC record is X^a|b|c", d.get("voc") == "[X^a|b|c]", repr((d.get("voc"), e.status())))
    done(e)


# ---- B: the bound on a big file -------------------------------------------------------------------------------------------------------------------------------------------
def section_big():
    say("\n--- B: a big data file is listed up to 2,000 records, without reading it whole first ------------------------------------------")
    t = time.time()
    e = sb.Ide(BOX, "IDE %s" % BIG)
    seen = None
    while time.time() - t < 30:
        e.s.settle(0.5)
        if "Only the first 2000 records" in e.status():
            seen = time.time() - t
            break
    st = e.status()
    row("B1 `ide` on a file of 5,000 records draws its page and says that only the first 2,000 records are listed, within 30 seconds (%s s)" % (
        "%.1f" % seen if seen is not None else "never"), seen is not None and "IDE: " in "\n".join(e.lines()[:3]), st)
    rows_listed = len([l for l in tree_text(e).split("\n") if re.search(r"\bb\d+\b", l)])
    row("B2 the tree lists records of the file (%d rows of b<n> in the pane)" % rows_listed, rows_listed >= 10, tree_text(e)[:400])
    done(e)
    e = sb.Ide(BOX, "IDE %s" % DF)
    e.quiet()
    row("B3 control: a small file is listed with no such message", "Only the first" not in e.status() and "r1" in tree_text(e), e.status())
    done(e)


# ---- L: locks -----------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_locks():
    say("\n--- L: a record open in a tab is locked; one another session holds opens read-only ---------------------------------------")
    h = Live()
    hu = h.user()
    row("L0 control: the live holder took the lock of r3 (it says its user number, and the lock probe sees r3 LOCKED by it)",
        hu is not None and lock_of("r3") == "LOCKED %s" % hu, "holder %r probe %r" % (hu, lock_of("r3")))
    e = sb.Ide(BOX, "IDE %s r3" % DF)
    e.quiet()
    st = e.status()
    row("L1 the record opens READ-ONLY: the status line names the user who holds its lock", hu is not None and ("read-only: user %s" % hu) in st, st)
    e.keys("ZZ")
    e.quiet()
    ed = editor_text(e)
    row("L2 typing does not change the text of a read-only tab (no ZZ in the editor, the tab not marked changed)", "ZZlocked" not in ed and ("%s r3 *" % DF) not in e.status(),
        ed[:200] + " | " + e.status())
    e.keys(CTRL_S)
    t = e.text()
    row("L3 Ctrl-S on it is refused in a box that says why (read-only here, the holder's user), and the disk is as it was",
        "is read-only here" in t and disk().get("r3") == "[locked one]", t[-500:])
    e.keys(RET)
    done(e)
    row("L4 control: the holder let go cleanly", h.let_go(), h.text()[-200:])
    row("L4b ...and the lock probe now GETS r3", lock_of("r3") == "GOT", repr(lock_of("r3")))

    e = sb.Ide(BOX, "IDE %s r3" % DF)
    e.quiet()
    st = e.status()
    row("L5 with nobody holding it the record opens writable (no read-only on the status line)", "read-only" not in st and ("%s r3" % DF) in st, st)
    lk = lock_of("r3")
    row("L6 while the tab is open ANOTHER SESSION CANNOT LOCK the record (LOCKED)", lk is not None and lk.startswith("LOCKED"), repr(lk))
    e.keys("ZZ")
    e.keys(CTRL_S)
    e.quiet()
    row("L7 Ctrl-S saves it (ZZlocked one on the disk)", disk().get("r3") == "[ZZlocked one]", repr((disk().get("r3"), e.status())))
    lk = lock_of("r3")
    row("L8 after the save the tab STILL holds the lock (WRITEU: another session still gets LOCKED)", lk is not None and lk.startswith("LOCKED"), repr(lk))
    e.keys(CTRL_W)
    e.quiet()
    row("L9 Ctrl-W closes the tab and gives the lock back (the probe GETS r3)", lock_of("r3") == "GOT", repr(lock_of("r3")))
    done(e)

    e = sb.Ide(BOX, "IDE %s r4" % DF)
    e.quiet()
    lk = lock_of("r4")
    e.keys(CTRL_Q)
    e.quiet()
    row("L10 Ctrl-Q (no changes) ends the IDE and gives the lock back (LOCKED while open: %r; GOT after)" % lk, lk is not None and lk.startswith("LOCKED")
        and lock_of("r4") == "GOT", repr(lock_of("r4")))
    done(e)

    e = sb.Ide(BOX, "IDE %s r4" % DF)
    e.quiet()
    lk = lock_of("r4")
    try:
        os.close(e.s.fd)                            # a hang-up, as closing a terminal window does
    except OSError:
        pass
    e.s.fd = -1
    gone = e.s._reap(8.0)
    if not gone:
        try:
            os.kill(e.s.pid, 9)
        except OSError:
            pass
        e.s._reap(5.0)
    e.s.exited = True
    row("L11 a hang-up ends the IDE and gives the lock back (LOCKED while open: %r; GOT after; the process went by itself: %r)" % (lk, gone),
        lk is not None and lk.startswith("LOCKED") and gone and lock_of("r4") == "GOT", repr(lock_of("r4")))


# ---- NA: a record holding bytes 128 to 247 is read-only (28 Oct 26, approved by the owner; WRITTEN, NOT RUN) ---------------------------------------------------------
def na_disk():
    o = sb.sess(BOX, "RUN bp zzknap" + RUN)
    m = re.search(r"(?m)^KNA r5 (\S+)\s*$", o)
    c = re.search(r"(?m)^KNA copy (present|absent)\s*$", o)
    if "KNA END" not in o:
        say("    (the NA probe did not reach its end: %r)" % o[-300:])
    return (m.group(1).upper() if m else None), (c.group(1) if c else None)


def box_says(e, words):
    """the refusal box is on the screen with these words; Return closes it"""
    t = e.text()
    seen = words in t
    if seen:
        e.keys(RET)
        e.quiet()
    return seen, t


def section_nonascii():
    say("\n--- NA: a record with characters outside ASCII opens read-only, and every way of changing or copying it is refused in a box ----")
    F12 = "\x1b[24~"
    CTRL_R = sb.CTRL_R
    put("zzknap" + RUN, NAPROBE)
    o = sb.sess(BOX, "BASIC bp zzknap" + RUN)
    hx, cp = na_disk()
    row("NA0 control: the NA probe compiled and r5 holds a latin-1 e-acute (E9), a field mark and a UTF-8 one (C3 A9): %r" % hx,
        re.search(r"(?m)^Compiled 1 program\(s\) with no errors", o) is not None and hx == R5_HEX and cp == "absent", repr((hx, cp)) + o[-200:])
    e = sb.Ide(BOX, "IDE %s r5" % DF)
    e.quiet()
    st = e.status()
    row("NA1 it opens read-only: the status line says [read-only: characters outside ASCII]", "[read-only: characters outside ASCII]" in st, st)
    e.keys("ZZ")
    e.quiet()
    row("NA2 typing changes nothing (no ZZ in the editor, the tab not marked changed)", "ZZ" not in editor_text(e) and ("%s r5 *" % DF) not in e.status(),
        editor_text(e)[:120] + " | " + e.status())
    refusal = "holds characters outside ASCII"
    for key, label, name in ((CTRL_S, "Ctrl-S", "NA3"), (CTRL_R, "Ctrl-R (Replace)", "NA4"), (F12, "F12 (Edit as fields)", "NA5"),
                             ((F10, DOWN * 3, RET), "File, Save as", "NA6"), ((F10, DOWN * 4, RET), "File, Write a copy", "NA7")):
        e.keys(*(key if isinstance(key, tuple) else (key,)))
        e.quiet()
        seen, t = box_says(e, refusal)
        named = "Name of the" in t or "File:" in t
        row("%s %s is refused in a box that says why, before anything is asked (no name form, no question)" % (name, label), seen and not named, t[-500:])
    row("NA8 the disk is as it was, byte for byte (nothing was decoded, encoded or normalised), and no copy was written", na_disk() == (R5_HEX, "absent"), repr(na_disk()))
    done(e)
    e = sb.Ide(BOX, "IDE %s r1" % DF)
    e.quiet()
    e.keys(END, "Q")
    e.quiet()
    row("NA9 control: a record whose only bytes above 127 are SD's marks (r1, a value mark) is NOT read-only: no tag, and typing changes it",
        "outside ASCII" not in e.status() and " *" in e.status(), e.status())
    done(e)
    row("NA10 ...and after leaving both, r5 is still byte for byte what the fixture wrote", na_disk()[0] == R5_HEX, repr(na_disk()))


# ---- M: a missing id ----------------------------------------------------------------------------------------------------------------------------------------------------
def section_missing():
    say("\n--- M: a record that is not there opens as a new one --------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE %s %s" % (DF, NEW1))
    e.quiet()
    st = e.status()
    row("M1 `ide file newid` opens a NEW tab: the status line says New record %s in %s, the tab is [%s], and nothing is on the disk" % (NEW1, DF, NEW1),
        ("New record %s in %s" % (NEW1, DF)) in st and ("[%s]" % NEW1) in tab_row(e) and disk().get(NEW1) == "<absent>", st)
    row("M1b ...and while it is open another session cannot make it (the tab holds the lock for its creation)", (lock_of(NEW1) or "").startswith("LOCKED"), repr(lock_of(NEW1)))
    e.keys("fresh")
    e.keys(CTRL_S)
    e.quiet()
    row("M2 typed fresh and Ctrl-S: the record is on the disk", disk().get(NEW1) == "[fresh]", repr((disk().get(NEW1), e.status())))
    done(e)
    e = sb.Ide(BOX, "IDE %s %s" % (DF, NEW2))
    e.quiet()
    e.keys("temp")
    quit_discard(e)
    done(e)
    row("M3 a new record typed in and discarded leaves nothing on the disk, and no lock", disk().get(NEW2) == "<absent>" and lock_of(NEW2) == "GOT", repr(disk().get(NEW2)))


# ---- T: the token form by kind --------------------------------------------------------------------------------------------------------------------------------------------
def section_tokens():
    say("\n--- T: the token form follows the kind ----------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE %s r2" % DF)
    e.quiet()
    e.keys(END, ":@vm:Z")
    e.keys(CTRL_S)
    e.quiet()
    row("T1 a DATA record with no marks: :@vm:Z typed at the end of its line is saved as a value mark (plain text|Z)", disk().get("r2") == "[plain text|Z]",
        repr((disk().get("r2"), e.status())))
    done(e)
    e = sb.Ide(BOX, "IDE bp %s" % SRC)
    e.quiet()
    ed, st = editor_text(e), e.status()
    row("T2 a PROGRAM (bp) that holds a value mark is never shown in the token form: no :@vm: in the editor and no 'Marks are shown' on the status line",
        ":@vm:" not in ed and "Marks are shown" not in st and ("bp %s" % SRC) in st, st + " | " + ed[:200])
    done(e)
    e = sb.Ide(BOX, "IDE %s r1" % DF)
    e.quiet()
    row("T3 control: the DATA record that holds a value mark is shown as Don:@vm:Henry", "Don:@vm:Henry" in editor_text(e), editor_text(e)[:200])
    done(e)


# ---- Q: CREATING.SEQKEY -------------------------------------------------------------------------------------------------------------------------------------------------------
def section_seqkey():
    say("\n--- Q: CREATING.SEQKEY ------------------------------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE %s CREATING.SEQKEY" % DF)
    e.quiet()
    st = e.status()
    row("Q1 `ide file creating.seqkey` opens the file's next sequential id (1) as a new record", ("New record 1 in %s" % DF) in st and "[1]" in tab_row(e), st)
    e.keys("seqrec")
    e.keys(CTRL_S)
    e.quiet()
    row("Q2 Ctrl-S writes it as record 1", disk().get("1") == "[seqrec]", repr((disk().get("1"), e.status())))
    done(e)


# ---- SL: a select list ---------------------------------------------------------------------------------------------------------------------------------------------------------
def section_select():
    say("\n--- SL: an active select list at the start ------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "SELECT %s WITH @ID = \"r1\" \"r2\"" % DF)
    e.keys("IDE %s\r" % DF)
    e.quiet()
    st, tabs = e.status(), tab_row(e)
    row("SL1 SELECT then `ide file` opens the listed records in tabs ([r1] and [r2]) and says so", "[r1]" in tabs and "[r2]" in tabs and "of the select list" in st,
        "%r | %r" % (st, tabs[:100]))
    quit_discard(e)
    done(e)


# ---- I: the include --------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_include():
    say("\n--- I: Go / Open the include ------------------------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE bp %s" % INC)
    e.quiet()
    e.keys(F10, RIGHT, DOWN * GO_INCLUDE, RET)
    e.quiet()
    tabs, ed = tab_row(e), editor_text(e)
    row("I1 on the line $include %s, Go / Open the include opens that record in a tab of its own" % HDR, ("[%s]" % HDR) in tabs and "equ ZZK" in ed, "%r | %r" % (tabs[:100], ed[:120]))
    done(e)
    e = sb.Ide(BOX, "IDE bp %s" % INC)
    e.quiet()
    e.keys(DOWN)
    e.keys(F10, RIGHT, DOWN * GO_INCLUDE, RET)
    e.quiet()
    row("I2 on a line that is not a $include line it says so and opens nothing", "not a $include line" in e.status() and ("[%s]" % HDR) not in tab_row(e), e.status())
    done(e)


# ---- C: a collection file ---------------------------------------------------------------------------------------------------------------------------------------------------
def section_collection():
    say("\n--- C: a collection file's record is refused --------------------------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE %s c1" % COL)
    e.quiet()
    row("C1 a collection file's record is refused with a message (the IDE does not edit collections yet) and the IDE is still up",
        "collection file" in e.status() and "IDE: " in "\n".join(e.lines()[:3]), e.status())
    done(e)


# ---- G: the dict edit gate ------------------------------------------------------------------------------------------------------------------------------------------------------
def section_gate():
    say("\n--- G: the dict edit gate in an ordinary account (the IDE is $internal: it is the only guard) ------------------------------")
    g = _load("sandbox_gates_for_kinds", "sandbox-gates.py")
    g.BOX, g.SYS, g.SD = BOX, SYSD, os.path.join(SYSD, "bin", "sd")
    g.prepare()
    acct = "zzkg"
    g.FIXTURES[acct] = ("no", "no")
    path = g.build_account(acct)
    fixer = "\n".join([
        "$internal",
        "   acct = '%s'" % path,
        "   openpath acct:'/voc' to v else crt 'KGFIX no voc' ; stop",
        "   create.file acct:'/zzkgd' dynamic on error crt 'KGFIX create' ; stop",
        "   create.file acct:'/zzkgd.dic' dynamic on error crt 'KGFIX create dict' ; stop",
        "   write 'F':@fm:'zzkgd':@fm:'zzkgd.dic' to v, 'zzkgd'",
        "   openpath acct:'/zzkgd.dic' to dd else crt 'KGFIX open dict' ; stop",
        "   write 'D':@fm:'1' to dd, 'name'",
        "   openpath acct:'/zzkgd' to d else crt 'KGFIX open data' ; stop",
        "   write 'data' to d, 'k1'",
        "   crt 'KGFIX done'",
        "end", ""])
    g.put(os.path.join(SYSD, "bp", "zzkgfix"), fixer)
    out = g.adm(["BASIC bp zzkgfix", "RUN bp zzkgfix"], internal=True)
    if not g.has(out, r"^KGFIX done$"):
        row("G0 setup: the ordinary account's data file and dictionary were made", False, "\n".join(out[-6:]))
        return
    # voc and bp edit on, DICT EDIT OFF (fields 10 to 12)
    g.reg_write(acct, [path, "", g.GROUP, "", "", "", "no", "no", "no", "yes", "yes", "no"])
    fl = g.flags(g.plain(acct, ["zzkf"]))
    row("G0 control: a session in %s is an ordinary one (admin=0)" % acct, fl is not None and fl[0] == "0", repr(fl))
    reader = "\n".join(["$internal", "   openpath '%s/zzkgd.dic' to dd else stop" % path, "   openpath '%s/zzkgd' to d else stop" % path,
                        "   read r from dd, 'name' else r = '<absent>'", "   crt 'KG dict [':convert(@fm, '^', r):']'",
                        "   read r from d, 'k1' else r = '<absent>'", "   crt 'KG data [':convert(@fm, '^', r):']'", "end", ""])
    g.put(os.path.join(SYSD, "bp", "zzkgread"), reader)

    def read_back():
        o = g.adm(["BASIC bp zzkgread", "RUN bp zzkgread"], internal=True)
        return dict(re.findall(r"(?m)^KG (\w+) (.*?)\s*$", "\n".join(o)))

    def pty(cmd, keys):
        env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
        env.pop("SDTEST_ADMIN", None)
        env.pop("SSH_CONNECTION", None)
        say("    > pty %s: %s | keys %r" % (acct, cmd, keys))
        s = PtySession([g.SD, "-a" + acct], path, env, 140, 43)        # 140 by 43: the IDE's floor since its window lock (28 Oct 26)
        s.settle(2.0)
        s.type("TERM xterm\r")
        s.type("TERM 140,43\r")
        s.type(cmd + "\r", idle=1.5)
        for k in keys:
            s.type(k, idle=0.8)
        text = "\n".join(l for l in s.screen.lines() if l.strip())
        for k in (RET, CTRL_Q, DOWN, RET):
            s.type(k, idle=0.6)
        s.type("\rOFF\r", idle=0.5)
        s.finish()
        return text

    t1 = pty("IDE DICT zzkgd name", ["ZZ", CTRL_S])
    r = read_back()
    row("G1 dict edit OFF: the IDE refuses to save the dictionary item, says why (dict.edit) and the item is as it was",
        "A dictionary can only be changed by an account that has dict.edit" in t1 and r.get("dict") == "[D^1]", "%r | %r" % (r, t1[-400:]))
    t2 = pty("IDE zzkgd k1", ["ZZ", CTRL_S])
    r = read_back()
    row("G2 control: the same account saves a record of the data part (ZZdata)", r.get("data") == "[ZZdata]", "%r | %r" % (r, t2[-300:]))


def teardown():
    for h in LIVES:
        h.kill()
    if BOX:
        subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)


def main():
    global BOX, SYSD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        say("usage: sandbox-ide-kinds.py <dir> [--build]")
        sys.exit(2)
    BOX = os.path.abspath(args[0])
    SYSD = os.path.join(BOX, "sys")
    say("sandbox-ide-kinds: sandbox %s  tree %s  run %s  SDBOX_KEYSET=%s" % (BOX, os.path.dirname(HERE), RUN, os.environ.get("SDBOX_KEYSET")))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-kinds: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYSD, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        section_setup()
        section_dict()
        section_voc()
        section_big()
        section_locks()
        section_nonascii()
        section_missing()
        section_tokens()
        section_seqkey()
        section_select()
        section_include()
        section_collection()
        section_gate()                 # last: prepare() makes the sandbox user ordinary unless SDTEST_ADMIN is set
    finally:
        teardown()
    say("\nsandbox-ide-kinds: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        say("sandbox-ide-kinds: CANNOT RUN - no row ran (a broken test, not a pass)")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
