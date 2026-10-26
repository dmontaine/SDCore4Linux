#!/usr/bin/env python3
#
# sandbox-tk-faults.py - the known faults and loose ends of the toolkit's pages (task faults, 26 Oct 2026).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-faults.py <dir> [--build] [--sections=e,w,t,g,m] [--mutants | --mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT, under /tmp).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutants every runtime mutant is made in turn on the SANDBOX'S OWN COPY of a program (never on the tree), and only the section its rows are in is run; exit 0
# means each was killed by exactly its own rows (MUTANTS).  --mutant=NAME does one.  Every run starts by putting the tree's programs and the tree's messages 11865 and 11951-11955 into the sandbox
# (a message is a plain file there, so a built sandbox does not need a new build for them); the mutants are undone the same way at the start of the next.
#
# THE FIVE THINGS (the lead's task "faults"):
#
#   E  THE END OF THE INPUT.  The status entry said "a session whose standard input is a pipe never ends on any toolkit page".  MEASURED 26 Oct on the tree before: it does end.  Ten pages (eight for
#      any account, tool.sessions and tool.audit for the administrator, which read keys with a timeout) are run on a CLOSED PIPE at 140 by 43: each draws its first screen and ends by itself, in
#      well under the 8 seconds it is given and with next to no CPU.  The rows are the guard that a page which stops testing ER$EOF would fail (mutant eof-spin: tool.files).
#   W  THE WINDOW.  What did hang, for minutes at full CPU and with nothing drawn, is a window of 200 by 9999: the library keeps the screen as one value to a row of ONE array, every row written
#      copies the array, and opening the screen costs the SQUARE of the height (tool.keys, closed pipe: 140 by 400 0.5 s, 140 by 1600 5.6 s, 140 by 3200 21.5 s).  200 by 9999 is what the suites'
#      plain sessions set so that nothing pages, so the first builder to run a page in one met it.  $tk_open now refuses a window above TK.MAXW (500) by TK.MAXH (300) before it takes the screen
#      (message 11951), after it has asked whether the person may run the page at all.  Ten pages are run at 200 by 9999 and must be refused at once, in those words; the limits themselves are tried
#      on both sides, on each dimension; an ordinary account that runs an administrator page at 200 by 9999 is told it is for the administrator only.  (mutants no-size-cap and cap-first;
#      no-size-cap IS the tree before the fix for these rows: every page spins for the 8 seconds it is given, 8.0 s of CPU in 8.0 s)
#   T  THE TITLE of $tk_confirm's box.  A program of the sandbox calls $tk_confirm with five arguments (every old caller), with an empty sixth, and with each of the four titles; the title is read
#      from the pseudo-terminal's screen, and in the box that asks for the name typed as well.  Then the pages: tool.dict N is "Write this record?", tool.query X "Delete this record?", and a
#      command (tool.dict C) is still "Run this command?".  (mutant title-ignored)
#   G  THE DICTIONARY GATE.  tool.dict writes a dictionary item from an $internal program, which the kernel's edit gate does not hold; the page asks for itself (K$EDIT.OK).  An ordinary account
#      WITHOUT dict-edit drives the page through N and Run: the kernel's words are on the status line and the DISK has no record; an account WITH it gets the record.  (mutant dict-no-gate: the page's
#      question is taken out, and the write goes through - which is what shows the page's own question is the wall.)
#   M  MESSAGE 11865.  A page that hands the terminal to a verb (tool.files A) asks "Press Enter to return" and Enter brings back THE PAGE; the text names no screen.  (mutant msg-11865-old)
#
# THE INSTRUMENT.  A pipe session is the sandbox's sd as a child with a PIPE for its input: TERM w,h, the verb, then the pipe is CLOSED (no OFF line), waited for with wait4() so that its own CPU
# comes back, hung up after 8 s if it is still there (SIGHUP; one that ignores it for 3 s is killed and sd -cleanup run).  A row that judges "ended by itself" first checks the page really
# started (the page's name and audience at the right end of row 0, which only $tk_frame writes), so a session that never reached the page cannot pass; wall and CPU are printed in every row.
# Everything else is a pseudo-terminal (the screen is read from the emulator) with the DISK as the evidence (a separate ordinary session reads the record).
#
# START-HISTORY:
# 26 Oct 26 dm  Written (task faults).  Red before the fix, measured on the tree before in this sandbox: tool.keys, tool.files and tool.query on a closed pipe at 200 by 9999 did not draw in 40 s
#               (CPU 40.0 s in 41.1 s wall); at 140 by 43 every page ended in 0.1 s.  60 rows, green on a fresh build; six runtime mutants (--mutants), each killed by exactly its own rows.
# END-HISTORY

import importlib.util
import os
import re
import shutil
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


td = _load("sandbox_tool_dict_for_faults", "sandbox-tool-dict.py")          # the dictionary suite's fixtures (zzdc1 with dict-edit on, zzdc2 off) and its way of driving the page
sh = td.sh
g = td.g
say, bail, has, adm, H = sh.say, sh.bail, sh.has, sh.adm, sh.H
A1, A2, ME = td.A1, td.A2, td.ME
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
FAILED_IDS = []
SCREEN = [None]
DEADLINE = 8.0          # seconds a session may take before it is hung up
CPU_OK = 3.0            # CPU seconds a session that ended by itself may have used
COUNTER = [0]

PROGS = ["tk.h", "tk_open", "tk_confirm", "tool_keys", "tool_files", "tool_voc", "tool_query", "tool_bulk", "tool_catalog", "tool_test", "tool_sessions", "tool_audit"]
MSGS = [11865, 11951, 11952, 11953, 11954, 11955]
PAGES = ["tool.keys", "tool.files", "tool.query", "tool.dict", "tool.voc", "tool.bulk", "tool.catalog", "tool.test"]          # for any account
ADMIN_PAGES = ["tool.sessions", "tool.audit"]                                                                              # for the administrator: they read keys with a timeout


def arow(rid, name, ok, detail=""):
    sh.row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            sh.dump(SCREEN[0])


def uid(prefix):
    """an id of its own for each use (a run, then a mutant's run, writes to the same fixture): lower case letters and digits"""
    COUNTER[0] += 1
    return "%s%d" % (prefix, COUNTER[0])


# ------------------------------------------------------------------------------------------------------------------------------ the tree into the sandbox

def sync_tree():
    """the tree's programs and messages into the sandbox (undoing a mutant), and the programs compiled"""
    for n in PROGS:
        shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", n), os.path.join(sh.SYS, "gpl.bp", n))
    for n in MSGS:
        shutil.copyfile(os.path.join(TREE, "sdsys", "messages", str(n)), os.path.join(sh.SYS, "messages", str(n)))
    comp = [n for n in PROGS if n != "tk.h"] + ["zzcf"]
    with open(os.path.join(sh.SYS, "gpl.bp", "zzcf"), "w") as f:            # the caller of $tk_confirm that T uses (see ZZCF)
        f.write(ZZCF)
    out = adm("BASIC gpl.bp " + " ".join(comp))
    if not has(out, r"^Compiled %d program\(s\) with no errors" % len(comp)):
        bail("the programs of the tree did not compile in the sandbox:\n%s" % "\n".join(out[-12:]))
    td.compile_page()


def mutate_prog(name, old, new):
    """one change to the SANDBOX'S copy of a program, compiled there; the text must be found once"""
    path = os.path.join(sh.SYS, "gpl.bp", name)
    with open(path, encoding="latin-1") as f:
        src = f.read()
    if src.count(old) != 1:
        bail("mutant: the text to change in %s is found %d times, not once:\n%s" % (name, src.count(old), old))
    with open(path, "w", encoding="latin-1") as f:
        f.write(src.replace(old, new))
    out = adm("BASIC gpl.bp " + name)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant of %s did not compile:\n%s" % (name, "\n".join(out[-8:])))


MAXBLK = ("   call $sl_window(win.w, win.h)\n   if win.w > TK.MAXW or win.h > TK.MAXH then\n      err = sysmsg(11951, app, TK.MAXW, TK.MAXH, win.w : ' by ' : win.h)\n      return\n   end\n")


def m_no_size_cap():
    mutate_prog("tk_open", MAXBLK, "")


def m_cap_first():
    """the cap moved in front of the audience check"""
    aud = "   if audience = 'admin' then\n"
    path = os.path.join(sh.SYS, "gpl.bp", "tk_open")
    with open(path, encoding="latin-1") as f:
        src = f.read()
    if src.count(aud) != 1 or src.count(MAXBLK) != 1:
        bail("mutant cap-first: the audience test or the cap is not found once in tk_open")
    src = src.replace(MAXBLK, "", 1).replace(aud, MAXBLK + "\n" + aud, 1)
    with open(path, "w", encoding="latin-1") as f:
        f.write(src)
    out = adm("BASIC gpl.bp tk_open")
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant of tk_open did not compile:\n%s" % "\n".join(out[-8:]))


def m_title_ignored():
    mutate_prog("tk_confirm", "      if boxtitle # '' then ttl = boxtitle\n", "      if 0 then ttl = boxtitle\n")


def m_dict_no_gate():
    mutate_prog("tool_dict", td.WRITE_WALL, "   read old from dv, nid then")


def m_eof_spin():
    mutate_prog("tool_files", "         case nm = ''\n            if status() = ER$EOF then exit\n", "         case nm = ''\n            if 0 then exit\n")


def m_msg_old():
    with open(os.path.join(sh.SYS, "messages", "11865"), "w") as f:
        f.write("Press Enter to return to the home screen\n")


# name: (the change, the base ids that must fail and no others, the section that runs)
MUTANTS = {
    "no-size-cap": (m_no_size_cap, ["W01", "W02", "W03", "W04", "W05", "W06", "W07", "W08", "W09", "W10", "W12", "W13"], "w"),
    "cap-first": (m_cap_first, ["W15"], "w"),
    "title-ignored": (m_title_ignored, ["T03", "T04", "T05", "T06", "T07", "T08", "T10"], "t"),
    "dict-no-gate": (m_dict_no_gate, ["G1", "G1b", "G1c"], "g"),
    "eof-spin": (m_eof_spin, ["E02b"], "e"),
    "msg-11865-old": (m_msg_old, ["M1"], "m"),
}


# ------------------------------------------------------------------------------------------------------------------------------ the pipe session

def pipe_run(label, account, lines, size="140,43", admin=False):
    """the sandbox's sd (-a<account>, or the administrator in the system directory) with TERM <size> and these lines on a pipe that is then CLOSED.  (ended, wall, cpu, text)"""
    env = g.env(admin)
    argv = [g.SD] + ([] if admin else ["-a" + account])
    cwd = g.SYS if admin else os.path.join(g.BOX, "user_accounts", account)
    body = "TERM %s\n" % size + "".join(l + "\n" for l in lines)
    outf = os.path.join(g.BOX, "faults-%s.out" % label)
    killed = False
    say("    > %s%s in %s: %r, then the pipe is closed (deadline %.0f s)" % ("[admin] " if admin else "", " ".join(os.path.basename(a) if a == g.SD else a for a in argv), os.path.relpath(cwd, g.BOX), body, DEADLINE))
    with open(outf, "wb") as fo:
        p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=fo, stderr=subprocess.STDOUT)
        p.stdin.write(body.encode())
        p.stdin.close()
        t0 = time.time()
        ended = True
        wall = None
        while True:
            wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
            if wpid:
                break
            if time.time() - t0 > DEADLINE:
                ended = False
                wall = time.time() - t0                  # the time it was let run, not the time the hang-up took
                os.kill(p.pid, signal.SIGHUP)          # as closing a terminal window does: SD ends and gives its user slot back
                t1 = time.time()
                while time.time() - t1 < 3.0:
                    wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
                    if wpid:
                        break
                    time.sleep(0.05)
                else:
                    os.kill(p.pid, signal.SIGKILL)
                    _w, _status, ru = os.wait4(p.pid, 0)
                    killed = True
                break
            time.sleep(0.05)
        p.returncode = 0
    if wall is None:
        wall = time.time() - t0
    if killed:
        subprocess.run([g.SD, "-cleanup"], cwd=g.SYS, env=env, capture_output=True, timeout=60)
        say("    (the session ignored the hang-up and was killed; sd -cleanup run)")
    size = os.path.getsize(outf)
    with open(outf, "rb") as fi:
        if size > 400000:                     # a page that spins writes megabytes: judge the first and the last of it
            head = fi.read(200000)
            fi.seek(size - 200000)
            raw = head + b"\n[... %d bytes not kept ...]\n" % (size - 400000) + fi.read()
        else:
            raw = fi.read()
    os.remove(outf)
    text = ANSI.sub("", raw.decode("utf-8", "replace"))
    say("    < %d bytes; ended=%s wall %.1f s cpu %.1f s" % (size, ended, wall, ru.ru_utime + ru.ru_stime))
    return ended, wall, ru.ru_utime + ru.ru_stime, text


def marker(page, admin):
    """what only $tk_frame writes: the page's name and the audience at the right end of row 0"""
    return re.escape(page) + (r"\s+administrator" if admin else r"\s+\S+@" + re.escape(A1))


# ------------------------------------------------------------------------------------------------------------------------------ E: the end of the input

def section_e():
    say("\n--- E: a page ends when its input ends (closed pipe, 140 by 43)")
    rows = [(p, False) for p in PAGES] + [(p, True) for p in ADMIN_PAGES]
    for k, (page, admin) in enumerate(rows, 1):
        ended, wall, cpu, text = pipe_run("e%d" % k, A1, [page], admin=admin)
        started = re.search(marker(page, admin), text) is not None
        arow("E%02da" % k, "%s%s: it drew its page (the name and the audience at the right end of row 0)" % (page, " as the administrator" if admin else ""), started, repr(text[-200:]))
        arow("E%02db" % k, "%s: it ended by itself, within %.0f s, using under %.0f s of CPU   [wall %.1f s, cpu %.1f s]" % (page, DEADLINE, CPU_OK, wall, cpu),
             started and ended and cpu < CPU_OK, "ended=%s wall=%.1f cpu=%.1f" % (ended, wall, cpu))


# ------------------------------------------------------------------------------------------------------------------------------ W: the window

def section_w():
    say("\n--- W: a window above 500 by 300 is refused before the screen is taken (200 by 9999 is what the suites' plain sessions set)")
    rows = [(p, False) for p in PAGES] + [(p, True) for p in ADMIN_PAGES]
    for k, (page, admin) in enumerate(rows, 1):
        ended, wall, cpu, text = pipe_run("w%d" % k, A1, [page], size="200,9999", admin=admin)
        want = "%s needs a window of at most 500 columns by 300 lines; this one is 200 by 9999" % page
        arow("W%02d" % k, "%s%s at 200 by 9999: refused at once in the words of 11951, nothing drawn   [wall %.1f s, cpu %.1f s]" % (page, " as the administrator" if admin else "", wall, cpu),
             ended and cpu < CPU_OK and want in text and re.search(marker(page, admin), text) is None, "ended=%s wall=%.1f cpu=%.1f %r" % (ended, wall, cpu, text[-240:]))
    # the limits, each dimension, both sides
    ended, wall, cpu, text = pipe_run("w11", A1, ["tool.keys"], size="500,300")
    arow("W11", "tool.keys at 500 by 300, the largest window, is drawn and ends   [wall %.1f s, cpu %.1f s]" % (wall, cpu),
         ended and cpu < 6.0 and re.search(marker("tool.keys", False), text) is not None and "needs a window" not in text, "ended=%s wall=%.1f cpu=%.1f %r" % (ended, wall, cpu, text[-200:]))
    ended, wall, cpu, text = pipe_run("w12", A1, ["tool.keys"], size="501,300")
    arow("W12", "501 columns by 300 lines is refused, and the message names the size it found", ended and "needs a window of at most 500 columns by 300 lines; this one is 501 by 300" in text
         and re.search(marker("tool.keys", False), text) is None, "ended=%s %r" % (ended, text[-200:]))
    ended, wall, cpu, text = pipe_run("w13", A1, ["tool.keys"], size="500,301")
    arow("W13", "500 columns by 301 lines is refused", ended and "needs a window of at most 500 columns by 300 lines; this one is 500 by 301" in text
         and re.search(marker("tool.keys", False), text) is None, "ended=%s %r" % (ended, text[-200:]))
    ended, wall, cpu, text = pipe_run("w14", A1, ["tool.keys"], size="139,43")
    arow("W14", "the minimum is still asked first: 139 by 43 says 'at least 140 columns by 43 lines' (message 11197), not the new message", ended
         and "needs a window of at least 140 columns by 43 lines; this one is 139 by 43" in text and "at most" not in text, "ended=%s %r" % (ended, text[-200:]))
    ended, wall, cpu, text = pipe_run("w15", A1, ["zzadm"], size="200,9999")
    arow("W15", "the audience is asked BEFORE the size: an ordinary account that runs an administrator page (tool.sessions, under the name zzadm) at 200 by 9999 is told it is for the administrator only, "
                "not that the window is too big   [wall %.1f s]" % wall,
         ended and "tool.sessions is for the administrator only" in text and "needs a window" not in text, "ended=%s %r" % (ended, text[-240:]))


# ------------------------------------------------------------------------------------------------------------------------------ T: the title of the box

# A user program cannot call $tk_confirm (the compiler reads  call $tk_confirm(  as a bracket, and a call by name is "Illegal call name" for a name that starts with a dollar), so the
# caller is an INTERNAL program of the sandbox's own, compiled in its gpl.bp and catalogued as $zzcf; an ordinary account gets it as a verb through a VOC entry (V, CA, $zzcf), as every
# tool.* page is given.  Its next word picks which call it makes.
ZZCF = "\n".join([
    "$internal",
    "program $zzcf",
    "$catalog $zzcf",
    "",
    "   n = field(trim(@sentence), ' ', dcount(trim(@sentence), ' '))",
    "   lines = 'one line of explanation' : @fm : '' : @fm : 'another line'",
    "   res = '' ; msg = ''",
    "   screen open clear else crt 'ZZCF no screen' ; stop",
    "   begin case",
    "      case n = 'old' ; call $tk_confirm('a sentence', lines, '', res, msg)",
    "      case n = 'empty' ; call $tk_confirm('a sentence', lines, '', res, msg, '')",
    "      case n = 'write' ; call $tk_confirm('a sentence', lines, '', res, msg, sysmsg(11952))",
    "      case n = 'delete' ; call $tk_confirm('a sentence', lines, '', res, msg, sysmsg(11953))",
    "      case n = 'update' ; call $tk_confirm('a sentence', lines, '', res, msg, sysmsg(11954))",
    "      case n = 'back' ; call $tk_confirm('a sentence', lines, '', res, msg, sysmsg(11955))",
    "      case n = 'typed' ; call $tk_confirm('a sentence', lines, 'zzname', res, msg, sysmsg(11955))",
    "      case n = 'typedold' ; call $tk_confirm('a sentence', lines, 'zzname', res, msg)",
    "   end case",
    "   screen close",
    "   crt 'ZZCF[' : res : '|' : msg : ']'",
    "end", ""])

ZZPQ = "\n".join([
    "   execute 'create.file &queries& dynamic' capturing mk",
    "   open '&queries&' to f else crt 'ZZPQ no queries' ; stop",
    "   r = 'query1' : @fm : 'cust' : @fm : 'list' : @fm : 'name'",
    "   r<19> = 'list cust name'",
    "   write r on f, 'zzq1'",
    "   open 'VOC' to v else crt 'ZZPQ no voc' ; stop",
    "   write 'V' : @fm : 'CA' : @fm : '$zzcf' on v, 'zzcf'",
    "   write 'V' : @fm : 'CA' : @fm : '$tool_sessions' on v, 'zzadm'",         # an administrator page under another name, in an ordinary account (W15: the audience is asked first)
    "   crt 'ZZPQ done'", "end", ""])


def make_fixtures():
    """a saved query to delete, and the verb zzcf in the ordinary account's VOC"""
    g.put(os.path.join(td.acct_dir(A1), "bp", "zzpq"), ZZPQ)
    out = g.plain(A1, ["BASIC bp zzpq", "RUN bp zzpq"])
    if not has(out, r"Compiled 1 program\(s\) with no errors") or not has(out, r"^ZZPQ done$"):
        bail("the fixture program of %s did not compile or run:\n%s" % (A1, "\n".join(out[-12:])))


def title_rows(h):
    """the lines of the screen that hold a box title: a '+' border row with words in it"""
    return [l for l in h.text().split("\n") if "+" in l and re.search(r"[A-Za-z]{3}", l)]


def has_title(h, title):
    return any(title in l for l in title_rows(h))


def section_t():
    say("\n--- T: the title of $tk_confirm's box")
    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    cases = [("T01", "old", "Run this command?", "a call with FIVE arguments, as every old caller makes it, has the old title"),
             ("T02", "empty", "Run this command?", "an EMPTY sixth argument is the old title too"),
             ("T03", "write", "Write this record?", "message 11952 is the title of a box about a record the page writes"),
             ("T04", "delete", "Delete this record?", "message 11953 is the title of a box about a record the page deletes"),
             ("T05", "update", "Update these records?", "message 11954 is the title of a bulk update's box"),
             ("T06", "back", "Put these records back?", "message 11955 is the title of an undo's box")]
    for rid, variant, want, what in cases:
        h.typed("zzcf %s\r" % variant, idle=2.5)
        others = [t for t in ("Run this command?", "Write this record?", "Delete this record?", "Update these records?", "Put these records back?") if t != want]
        arow(rid, "%s: the box is titled \"%s\" and no other title is on the screen" % (what, want), has_title(h, want) and not any(has_title(h, o) for o in others), repr(title_rows(h)))
        h.key("esc", idle=1.5)
        T = h.text()
        arow(rid + "x", "Esc is Cancel: the program was told 'cancel' and nothing else (the old Run / Cancel contract is kept)", "ZZCF[cancel|" in T, T[-200:])
    h.typed("zzcf typed\r", idle=2.5)
    first = has_title(h, "Put these records back?")
    h.typed("r", idle=2.0)
    arow("T07", "the box that asks for the name typed carries the same title (\"Put these records back?\"), after Run was chosen in the first", first and has_title(h, "Put these records back?")
         and "zzname" in h.text(), repr((first, title_rows(h))))
    h.key("esc", idle=1.5)
    h.typed("zzcf typedold\r", idle=2.5)
    h.typed("r", idle=2.0)
    arow("T07b", "...and without a title it is \"Run this command?\" in both boxes", has_title(h, "Run this command?") and "zzname" in h.text(), repr(title_rows(h)))
    h.key("esc", idle=1.5)
    h.typed("off\r", idle=1.0)
    h.end()

    # the pages
    nid = uid("zzt")
    h = td.page(A1, "cust")
    SCREEN[0] = h
    td.new_item_d(h, nid, "7", "Ttl", "L", "10", "", "S")
    bt = td.boxtext(h)
    arow("T08", "tool.dict N: the box about the record it writes is titled \"Write this record?\" (not \"Run this command?\") and shows the record   [item %s]" % nid,
         has_title(h, "Write this record?") and not has_title(h, "Run this command?") and ("write the item %s in the dictionary of cust" % nid) in bt, repr((title_rows(h), bt[:200])))
    h.key("enter", idle=1.5)
    arow("T08b", "Enter is Cancel: the disk has no item %s" % nid, td.item(A1, "cust", nid) is None and "nothing was run" in td.st(h), repr((td.item(A1, "cust", nid), td.st(h))))
    td.goto(h, "uncomp")
    h.typed("c", idle=1.5)
    arow("T09", "tool.dict C (compile) is a command: its box keeps the title \"Run this command?\"", has_title(h, "Run this command?") and not has_title(h, "Write this record?")
         and "compile.dict cust uncomp" in td.boxtext(h), repr((title_rows(h), td.boxtext(h)[:120])))
    h.key("enter", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()

    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    h.typed("tool.query cust\r", idle=3.5)
    h.typed("l", idle=1.5)
    h.typed("x", idle=1.5)
    arow("T10", "tool.query X (delete a saved query): the box is titled \"Delete this record?\" and says it is not a command", has_title(h, "Delete this record?") and not has_title(h, "Run this command?")
         and "delete zzq1 from &queries&" in td.boxtext(h), repr((title_rows(h), td.boxtext(h)[:160])))
    h.key("esc", idle=1.2)
    h.key("ctrl-q", idle=1.2)
    h.end()


# ------------------------------------------------------------------------------------------------------------------------------ G: the dictionary gate

def section_g():
    say("\n--- G: tool.dict writes a dictionary item only where the kernel would let the session")
    before = td.ids(A2, "cust")
    nid = uid("zzg")
    h = td.page(A2, "cust")
    SCREEN[0] = h
    td.new_item_d(h, nid, "7", "Gate", "L", "10", "", "S")
    h.typed("r", idle=2.5)
    arow("G1", "dict-edit OFF, N and Run: the status line carries the kernel's own refusal (a dictionary can only be changed by an account that has dict.edit)   [item %s]" % nid,
         "A dictionary can only be changed by an account that has dict.edit" in td.st(h) and "wrote the item" not in td.st(h), repr(td.st(h)))
    d = td.item(A2, "cust", nid)
    arow("G1b", "...and the DISK has no record %s in the dictionary of cust (read by a separate session)" % nid, d is None, repr(d))
    after = td.ids(A2, "cust")
    arow("G1c", "...and the dictionary holds exactly the items it held before", after == before, repr((before, after)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    nid = uid("zzg")
    h = td.page(A1, "cust")
    SCREEN[0] = h
    td.new_item_d(h, nid, "7", "Gate", "L", "10", "", "S")
    h.typed("r", idle=2.5)
    d = td.item(A1, "cust", nid)
    arow("G2", "CONTROL, dict-edit ON, the same keys: the record is on the disk (D, 7, '', Gate, 10L, S) and the status line says it was written   [item %s]" % nid,
         d is not None and d[0] == ["D", "7", "", "Gate", "10L", "S"] and "wrote the item %s" % nid in td.st(h), repr((d, td.st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


# ------------------------------------------------------------------------------------------------------------------------------ M: message 11865

def section_m():
    say("\n--- M: \"Press Enter to return\" brings back the page that handed the terminal over")
    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    h.typed("tool.files\r", idle=3.5)
    h.typed("/", idle=0.8)
    h.typed("cust\r", idle=1.0)
    h.typed("a", idle=1.0)
    td.until(h, lambda t: "Press Enter" in t)
    T = h.text()
    arow("M1", "tool.files A hands the terminal to analyse.file and asks 'Press Enter to return' - the words of message 11865, naming no screen",
         re.search(r"^Press Enter to return\s*$", T, re.M) is not None and "home screen" not in T and "The file under the cursor" not in T, T[-300:])
    h.key("enter", idle=1.5)
    td.until(h, lambda t: "The file under the cursor" in t)
    arow("M2", "...Enter brings back THE PAGE (tool.files), with the status line saying it is back from analyse.file cust", "The file under the cursor" in h.text() and "back from analyse.file cust" in td.st(h), repr(td.st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


SECTIONS = {"e": section_e, "w": section_w, "t": section_t, "g": section_g, "m": section_m}
ORDER = ["e", "w", "t", "g", "m"]


def main():
    mutants = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")]
    if "--mutants" in sys.argv:
        mutants = list(MUTANTS)
    for m in mutants:
        if m not in MUTANTS:
            bail("usage: sandbox-tk-faults.py <dir> [--build] [--sections=e,w,t,g,m] [--mutants | --mutant=%s]" % "|".join(MUTANTS))
    only = [a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--sections=")]
    only = only[0] if only else ORDER
    for s in only:
        if s not in SECTIONS:
            bail("--sections= takes some of %s" % ",".join(ORDER))
    results = []
    try:
        sh.setup("sandbox-tk-faults.py")
        td.setup_files()
        sync_tree()
        make_fixtures()
        if not mutants:
            for s in ORDER:
                if s in only:
                    SECTIONS[s]()
        else:
            for m in mutants:
                if m != mutants[0]:
                    sync_tree()
                FAILED_IDS[:] = []
                change, want, sec = MUTANTS[m]
                change()
                say("sandbox-tk-faults: MUTANT %s: the rows that must fail, and nothing else: %s (section %s)" % (m, ", ".join(want), sec))
                SECTIONS[sec]()
                got = sorted(set(FAILED_IDS))
                # a row id may carry a letter ('E02b'): the ids in MUTANTS are exact
                ok = got == sorted(want)
                say("sandbox-tk-faults: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (m, got, sorted(want), "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
                results.append(ok)
            sync_tree()
    finally:
        sh.teardown()
    if mutants:
        say("\nsandbox-tk-faults: %d mutants run, %d killed by exactly their own rows" % (len(results), sum(1 for r in results if r)))
        return 0 if results and all(results) else 1
    say("\nsandbox-tk-faults: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
