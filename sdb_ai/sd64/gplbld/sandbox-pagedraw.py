#!/usr/bin/env python3
#
# sandbox-pagedraw.py - what a full-screen page of the toolkit WRITES to the terminal for each action, and that what the terminal then shows is what a full repaint
#                       would show (S.113, owner 3 Nov 2026: "All pages").  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-pagedraw.py <dir> [--build] [--only=files,query,home,admin,user] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Without --build <dir> must already be
# built, which is how the suite is run against the tree BEFORE the change to show that its rows can fail.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  With --mutant=NAME
# one change is made to the SANDBOX'S OWN COPY of a library program, which is compiled there, and exit 0 means the rows that had to fail failed and no others (MUTANTS below); the copy
# is put back and compiled again at the end.
#
# START-HISTORY:
# 3 Nov 26 dm  New (S.113, track F).  Sections files, query, home, admin, user; the build, the fixtures and the setup always run.
# END-HISTORY
#
# WHAT IS HELD.  Every page is driven on a pseudo-terminal at 140 by 43 with TERM xterm and LC_ALL=C (the conditions track E measured on 3 Nov: tool.files wrote about 14.7 KB for every
# Down, Up and PgDn, 14.6-14.9 KB for F5 and 23.1 KB for the first open).  For each action the suite counts the BYTES the page wrote and the CELLS of text in them, and holds:
#   - a cursor key in a list (Down, Up) writes under 2 KB, PgDn under 6 KB, Tab or a move between tiles under 2 KB;
#   - F5 and Ctrl-L are still a FULL draw (4,000 cells or more, in every row that holds text but three at most; Ctrl-L must also clear the whole screen once).  Not a
#     byte floor: a repaint after this change leaves blank rows out and is about 7.6 KB where the old full redraw was 14.7 KB;
#   - an idle page writes next to nothing (under 200 bytes in two seconds);
#   - THE SCREEN IS NEVER LEFT STALE: after the action the emulated screen (text and style of every cell) is kept, Ctrl-L is pressed, which makes the library clear the terminal and write
#     its whole picture again from its shadow, and the screen must be the same.  The status line (the row 3 above the bottom) is left out of the comparison, because a page takes the
#     message off it on the next key; every other row and every cell is compared.  THE NULL CASE IS REFUSED: a comparison where Ctrl-L did not clear the screen is a FAIL ("no repaint"),
#     never a pass, so the rows are red on a tree where Ctrl-L does nothing.
#   - a box opened and closed (F1's help box, the menu bar's menu), a resize to 160 by 45 and back, F5 and Ctrl-L leave a correct screen by the same comparison;
#   - a user's own SCREEN program (not the toolkit) that PRINTs over its screen gets what it always got: SCREEN TEXT writes what it is told.
#
# THE INSTRUMENT.  Bytes are counted from the pty's raw stream between the key and the moment the page has written nothing for a second (track E's method); cells as
# sandbox-idedraw.py counts them (a cursor position, then the printable text after it).  The screen is termscreen.py's.  Each row prints the numbers it judged.  NOT HELD HERE: a real
# terminal's reflow on a resize (the emulator cuts and pads, as an xterm does with a full-screen program), the mouse, a UTF-8 border.
#
# SECTIONS.  files: tool.files in account zzfl1 (sandbox-tool-files.py's fixture and 26 more files, so that the list scrolls), with the box, the menu, F5, Ctrl-L, idle and the resizes.
# query: tool.query in the same account.  home: the home screen.  admin: tool.accounts as the administrator.  user: a user's SCREEN program that PRINTs over its own text.
import importlib.util
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tf = _load("sandbox_tool_files_for_pagedraw", "sandbox-tool-files.py")
sh = tf.sh
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
A1 = tf.A1

# xterm's keys (every session below types TERM xterm before the page starts, whatever its LOGIN paragraph said)
K = {"down": "\x1bOB", "up": "\x1bOA", "right": "\x1bOC", "left": "\x1bOD", "pgdn": "\x1b[6~", "tab": "\t", "f1": "\x1bOP", "f5": "\x1b[15~", "f6": "\x1b[17~", "f10": "\x1b[21~",
     "esc": "\x1b", "ctrl-l": "\x0c", "ctrl-q": "\x11"}

SECTIONS = ("files", "query", "home", "admin", "user")
FAILED_IDS = []
SCREEN = [None]
CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")

# name: (library program, old text, new text, the row ids that must fail and no others, the sections that run)
MUTANTS = {
    # the sync reset on a resize: the kept picture is made the new size and the terminal is still believed to show it (it shows the old layout)
    "resize-keeps-sync": ("sl_scr", "      ctx<SL.S.SYNC> = 0 ; ss.lost = 1           ;* MUTANT-POINT resize\n", "",
                          ["F12"], ["files"]),
    # every write keeps the terminal's picture: without it a row written once in one style and then back in the other is left out
    "diff-no-term": ("sl_put", "   gosub keep.term                                    ;* MUTANT-POINT term\n", "",
                     ["F4c"], ["files"]),
}
# A mutant is KILLED when every row it names failed.  Other rows it made fail are listed, not judged: a picture of the terminal that is wrong fails rows in ways that depend on the page.


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


def written(raw):
    """[(row, column, cells)] - every run of text the bytes write, with the place of its first cell (sandbox-idedraw.py's count)."""
    s = raw.decode("latin-1")
    out = []
    r = c = 0
    pos = 0
    for m in CSI.finditer(s):
        txt = re.sub(r"[\x00-\x1f]", "", s[pos:m.start()])
        if txt:
            out.append((r, c, len(txt)))
            c += len(txt)
        pos = m.end()
        if m.group(2) == "H":
            p = m.group(1).split(";")
            r = int(p[0] or 1) - 1
            c = int(p[1] or 1) - 1 if len(p) > 1 else 0
    txt = re.sub(r"[\x00-\x1f]", "", s[pos:])
    if txt:
        out.append((r, c, len(txt)))
    return out


def wait_idle(h, idle=1.0, limit=20.0):
    end = time.time() + limit
    while time.time() < end:
        if not h.s._pump(idle):
            return


def act(h, key, n=1):
    """Press the key (n times, the page settling after each); returns (bytes, cells, rows touched) of the LAST press."""
    res = None
    for _ in range(n):
        m = len(h.s.raw)
        h.s.type(K[key] if key in K else key, settle=False)
        wait_idle(h)
        raw = bytes(h.s.raw[m:])
        runs = written(raw)
        res = (len(raw), sum(x[2] for x in runs), len(set(x[0] for x in runs)))
    return res


def snap(h):
    sc = h.s.screen
    return [("".join(sc.grid[r]), tuple(sc.rev[r])) for r in range(sc.rows)]


def consistent(h, rid, what):
    """THE STALE-CELL ROW.  The screen as the page left it is kept; Ctrl-L makes the library clear the terminal and write its whole picture again; the two must agree in every cell
    of every row but the status line.  A Ctrl-L that did not clear the screen is refused (no repaint, nothing compared)."""
    before = snap(h)
    c0 = h.s.screen.clears
    m = len(h.s.raw)
    h.s.type(K["ctrl-l"], settle=False)
    wait_idle(h)
    nbytes = len(h.s.raw) - m
    cleared = h.s.screen.clears - c0
    after = snap(h)
    ystat = h.s.screen.rows - 3
    diff = []
    for r in range(min(len(before), len(after))):
        if r == ystat:
            continue
        if before[r] != after[r]:
            cols = [c for c in range(len(before[r][0])) if before[r][0][c] != after[r][0][c] or before[r][1][c] != after[r][1][c]]
            diff.append((r, cols[0] if cols else -1, len(cols), before[r][0].rstrip()[:60], after[r][0].rstrip()[:60]))
    if cleared < 1:
        arow(rid, "%s: NO REPAINT - Ctrl-L wrote %d bytes and did not clear the screen, so nothing could be compared (the null case is a failure)" % (what, nbytes), False,
             "clears %d" % cleared)
        return
    arow(rid, "%s: the screen is the same as a full repaint from the library's picture (Ctrl-L cleared it %d time(s), wrote %d bytes; %d rows of %d compared, the status line "
         "row %d left out; rows that differ: %d)" % (what, cleared, nbytes, len(before) - 1, len(before), ystat, len(diff)), not diff and len(before) == len(after),
         repr(diff[:4]))


def start(h, cmd, idle=3.5):
    h.typed("TERM xterm\r", idle=0.8)
    h.typed("TERM %d,%d\r" % (h.cols, h.rows), idle=0.8)
    m = len(h.s.raw)
    h.s.type(cmd + "\r", settle=False)
    wait_idle(h, 1.5)
    return len(h.s.raw) - m


def leave(h):
    h.s.type(K["ctrl-q"], settle=False)
    wait_idle(h, 0.8, 6)
    h.s.type("OFF\r", settle=False)
    wait_idle(h, 0.5, 4)
    h.end()


def small(rid, what, res, limit):
    b, c, nr = res
    arow(rid, "%s writes %d bytes, %d cells in %d rows: under %d bytes" % (what, b, c, nr, limit), b < limit and b > 0, repr(res))


def textrows(h):
    return sum(1 for l in h.lines() if l.strip())


def full(rid, what, res, h):
    b, c, nr = res
    tr = textrows(h)
    arow(rid, "%s is still a full draw: %d bytes, %d cells in %d rows, the screen has %d rows of text (4000 cells or more, in all of those rows but 3 at most)" % (what, b, c, nr, tr),
         c >= 4000 and nr >= tr - 3, repr((res, tr)))


# ------------------------------------------------------------------------------------------------- sections

def section_files():
    say("\n--- files: tool.files in %s (the fixture and 26 more files), 140 by 43, TERM xterm" % A1)
    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    first = start(h, "tool.files")
    T = h.text()
    if "The file under the cursor" not in T:
        dump(h)
        bail("tool.files did not draw (no 'The file under the cursor' on the screen): no row below could be believed")
    say("    (first open: %d bytes; track E measured 23,094 on the tree before)" % first)
    arow("F1", "the first open writes %d bytes: no more than the tree before (23,100)" % first, 0 < first <= 23100, repr(first))
    small("F2", "Down (the cursor in the list)", act(h, "down"), 2048)
    small("F3", "Down again, the third time", act(h, "down", 2), 2048)
    small("F4", "Up (the row it left is highlighted again)", act(h, "up"), 2048)
    consistent(h, "F4c", "after Down three times and Up")
    small("F5", "PgDn (every row of the list changes)", act(h, "pgdn"), 6000)
    consistent(h, "F5c", "after PgDn")
    act(h, "f1")
    opened = "Close" in h.text() or "OK" in h.text() or "Help" in h.text()
    b = act(h, "esc")
    say("    (F1's box: opened %s; Esc closed it writing %d bytes)" % (opened, b[0]))
    consistent(h, "F6", "after F1's help box was opened and closed (the box put back what was under it)")
    act(h, "f10")
    b = act(h, "esc")
    say("    (F10's menu closed with Esc, %d bytes)" % b[0])
    consistent(h, "F7", "after the menu bar's menu was opened and closed")
    full("F8", "F5 (read the files again)", act(h, "f5"), h)
    consistent(h, "F8c", "after F5")
    c0 = h.s.screen.clears
    res = act(h, "ctrl-l")
    tr = textrows(h)
    arow("F9", "Ctrl-L is a full draw that clears the screen first: %d bytes, %d cells in %d rows (the screen has %d rows of text), %d clear(s)" % (res[0], res[1], res[2], tr, h.s.screen.clears - c0),
         res[1] >= 4000 and res[2] >= tr - 3 and h.s.screen.clears - c0 >= 1, repr(res))
    m = len(h.s.raw)
    h.s._pump(2.0)
    time.sleep(0.1)
    h.s._pump(0.1)
    idle = len(h.s.raw) - m
    arow("F10", "an idle page writes next to nothing: %d bytes in about two seconds (under 200)" % idle, idle < 200, repr(idle))
    small("F11", "Down after F5 and Ctrl-L", act(h, "down"), 2048)
    m = len(h.s.raw)
    h.s.resize(160, 45, idle=1.0)
    wait_idle(h)
    say("    (resized to 160 by 45: %d bytes)" % (len(h.s.raw) - m))
    consistent(h, "F12", "after the window was made 160 by 45")
    m = len(h.s.raw)
    h.s.resize(140, 43, idle=1.0)
    wait_idle(h)
    say("    (resized back to 140 by 43: %d bytes)" % (len(h.s.raw) - m))
    consistent(h, "F13", "after the window was made 140 by 43 again")
    small("F14", "Down after the resizes", act(h, "down"), 2048)
    consistent(h, "F14c", "after Down at the end")
    leave(h)


def section_query():
    say("\n--- query: tool.query in %s, 140 by 43, TERM xterm" % A1)
    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    first = start(h, "tool.query")
    if "zzfa" not in h.text():
        dump(h)
        bail("tool.query did not draw its list of files (no zzfa on the screen)")
    say("    (first open: %d bytes)" % first)
    small("Q1", "Down in the list of files", act(h, "down"), 2048)
    consistent(h, "Q1c", "after Down")
    small("Q2", "F6 (the focus to the next box; S.176: Tab no longer moves it)", act(h, "f6"), 2048)
    consistent(h, "Q2c", "after F6")
    full("Q3", "F5", act(h, "f5"), h)
    consistent(h, "Q3c", "after F5")
    leave(h)


def section_home():
    say("\n--- home: the home screen in %s, 140 by 43, TERM xterm" % A1)
    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    first = start(h, "home")
    if not h.home():
        dump(h)
        bail("the home screen did not draw")
    say("    (first open: %d bytes)" % first)
    small("H1", "Right (the focus to the next tile)", act(h, "right"), 2048)
    consistent(h, "H1c", "after Right")
    small("H2", "Down (the focus a row of tiles down)", act(h, "down"), 2048)
    consistent(h, "H2c", "after Down")
    full("H3", "F5", act(h, "f5"), h)
    consistent(h, "H3c", "after F5")
    leave(h)


def section_admin():
    say("\n--- admin: tool.accounts as the administrator, 140 by 43, TERM xterm")
    h = H(admin=True, cols=140, rows=43)
    SCREEN[0] = h
    first = start(h, "tool.accounts")
    if A1 not in h.text():
        dump(h)
        bail("tool.accounts did not draw its list (no %s on the screen)" % A1)
    say("    (first open: %d bytes)" % first)
    small("A1", "Down in the list of accounts", act(h, "down"), 2048)
    small("A2", "Down again", act(h, "down"), 2048)
    consistent(h, "A2c", "after Down twice")
    full("A3", "F5", act(h, "f5"), h)
    consistent(h, "A3c", "after F5")
    leave(h)


USERPROG = "\n".join([
    "   screen open clear else crt 'NOTERM' ; stop",
    "   screen text 'AAAA' at 0,5",
    "   crt @(0, 5) : 'XXXX' :",
    "   screen text 'AAAA' at 0,5",
    "   screen text 'READY' at 0,7",
    "   screen key returning k",
    "   screen close",
    "end", ""])


def section_user():
    say("\n--- user: a user's own SCREEN program (not the toolkit) PRINTs over its text and draws the same text again")
    g.put(os.path.join(tf.acct_dir(A1), "bp", "zzpd"), USERPROG)
    out = g.plain(A1, ["BASIC bp zzpd"])
    if not has(out, r"Compiled 1 program"):
        bail("the user's program did not compile:\n" + "\n".join(out[-6:]))
    h = H(account=A1, cols=140, rows=43)
    SCREEN[0] = h
    start(h, "RUN bp zzpd")
    L = h.lines()
    arow("U1", "SCREEN TEXT after the program's own PRINT writes what it is told: row 5 shows AAAA, not XXXX (%r)" % L[5][:8], "READY" in L[7] and L[5][:4] == "AAAA", repr(L[5][:20]))
    h.s.type("\r", settle=False)
    wait_idle(h, 0.8, 5)
    h.s.type("OFF\r", settle=False)
    wait_idle(h, 0.5, 4)
    h.end()


# ------------------------------------------------------------------------------------------------- mutants

ORIG = {}


def compile_lib(prog):
    out = adm("BASIC gpl.bp " + prog)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("%s did not compile in the sandbox:\n%s" % (prog, "\n".join(out[-8:])))


def mutate(name):
    prog, old, new = MUTANTS[name][:3]
    path = os.path.join(sh.SYS, "gpl.bp", prog)
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times in the sandbox's %s, not once" % (name, src.count(old), prog))
    ORIG[prog] = src
    g.put(path, src.replace(old, new))
    compile_lib(prog)
    say("    (mutant %s: the sandbox's %s changed and compiled)" % (name, prog))


def unmutate():
    for prog, src in ORIG.items():
        g.put(os.path.join(sh.SYS, "gpl.bp", prog), src)
        compile_lib(prog)
        say("    (the sandbox's %s put back and compiled)" % prog)


def main():
    mut = None
    want = set(SECTIONS)
    for a in sys.argv[1:]:
        if a.startswith("--mutant="):
            mut = a[len("--mutant="):]
            if mut not in MUTANTS:
                bail("no mutant %r (there are %s)" % (mut, ", ".join(sorted(MUTANTS))))
        if a.startswith("--only="):
            want = set(w for w in a[len("--only="):].split(",") if w)
            bad = want - set(SECTIONS)
            if bad or not want:
                bail("--only takes %s, not %r" % (",".join(SECTIONS), a))
    if mut and not any(a.startswith("--only=") for a in sys.argv[1:]):
        want = set(MUTANTS[mut][4])
    say("sandbox-pagedraw: argv %r; keyset %s; sections %s; mutant %s" % (sys.argv[1:], os.environ.get("SDBOX_KEYSET", "0"), ",".join(s for s in SECTIONS if s in want), mut))
    try:
        sh.setup("sandbox-pagedraw")
        tf.setup_files()
        extra = ["CREATE.FILE zzm%02d" % i for i in range(1, 27)]
        o = g.plain(A1, extra)
        made = sum(1 for ln in o if "created" in ln.lower())
        say("    (the 26 extra files: %d 'created' lines)" % made)
        if made < 26:
            bail("the 26 extra files of %s were not all made:\n%s" % (A1, "\n".join(o[-6:])))
        if mut:
            mutate(mut)
        for name in SECTIONS:
            if name in want:
                globals()["section_" + name]()
    finally:
        try:
            if ORIG:
                unmutate()
        finally:
            sh.teardown()
    say("\nsandbox-pagedraw: %d passed, %d failed%s" % (sh.tkb.passed, sh.tkb.failed, (" (failed: %s)" % " ".join(FAILED_IDS)) if FAILED_IDS else ""))
    if mut:
        kills = set(MUTANTS[mut][3])
        got = set(FAILED_IDS)
        missed = sorted(kills - got)
        extra = sorted(got - kills)
        say("MUTANT %s: must fail %s; failed %s; not failed %s; failed beyond them %s -> %s" % (mut, sorted(kills), sorted(got), missed, extra, "KILLED" if not missed else "NOT KILLED"))
        sys.exit(0 if not missed else 1)
    sys.exit(0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1)


if __name__ == "__main__":
    main()
