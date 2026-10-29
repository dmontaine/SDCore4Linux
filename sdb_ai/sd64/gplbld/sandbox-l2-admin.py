#!/usr/bin/env python3
#
# sandbox-l2-admin.py - the five dense administrator pages on the layout service (S.88 stage L2): TOOL.GATES, TOOL.SESSIONS, TOOL.MASTERS, TOOL.AUDIT and TOOL.ACCOUNTS drawn at 140 by 43,
# grown to 180 by 55 while they run, and started at 200 by 60, on a PSEUDO-TERMINAL.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-l2-admin.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.  WRITTEN 28 Oct 26 AND NOT YET RUN (the owner's rule for the L2 sitting: no sandbox runs; the free check test-l2-admin-units.py is the evidence so far).
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 L2, the administrator pages).
# END-HISTORY
#
# THE INSTRUMENT.  The expected rectangles are not typed here: they are the declaration each page makes, read out of the page's own `declare.layout` by test-l2-admin-units.py and laid out by that
# file's model of $tk_layout (a copy of its equations).  So a row says "the screen shows the boxes the model says the declaration gives", and the model is held to the pages' old literal boxes
# by the free check.  Every box is judged on the SCREEN: its title on the top border inside the box, its left and right edges non-blank on every row, its bottom border non-blank along the whole
# width.  Texts that the page places from its rectangles (the headings, the counts, the hints, the [?] button) are looked for at the place the declaration puts them, and at 140 by 43 that place is
# also compared with the literal the page used before L2 (a mistake in the table cannot hide there).  After a resize the program's own bytes are fed to a FRESH emulator of the new size
# (the emulator keeps the cells it had), as sandbox-tk-resize.py does.  Every session prints its argv, TERM, window size and the keys it is sent.  Every group opens with a CONTROL (the page is
# up at 140 by 43: its first title is on the screen and the footer is on rows 41-43); when it fails the rows that depend on it fail as NULL CASE.
#
#   G1   at 140 by 43 the page is drawn exactly as before: every box where the old page put it, every text where the old page put it (no growth at the reference)
#   G2   grown to 180 by 55 while running: the boxes are where the declaration puts them (the content reaches column 178 and row 51), the texts follow their boxes, the footer is on rows 53-55
#   G3   started at 200 by 60: the same (the content reaches column 198 and row 56)
# NOT HELD: the lists with more data than the sandbox has (a table that shows more rows needs more rows in it: the row counts are the free check's), keys and the mouse (the page's own suites).
import importlib.util
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from termscreen import Screen  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_l2admin", "sandbox-home.py")
l2 = _load("test_l2_admin_for_sandbox", "test-l2-admin-units.py")
say = sh.say
M = l2.load_model().Model()
CTRL_Q = "\x11"

# Texts a page places from its rectangles: (pane id, ('t', k) the k-th row from the top of the pane or ('b', k) the k-th from the bottom, dx the columns from the pane's left edge or ('r', k) the
# k-th from its right edge, a regular expression the text must start with, the (row, column) it was at 140 by 43 before L2).
ANCH = {
    "tool_gates": [("matrix", ("t", 1), 2, r"Account\s+Kind", (2, 3)), ("matrix", ("t", 1), ("r", 5), r"\[\?\]", (2, 134)), ("matrix", ("b", 3), 2, r"all accounts: ", (17, 3)),
                   ("matrix", ("b", 2), 2, r"Nothing queued for ", (18, 3)), ("cell", ("t", 1), 2, r"\S+ \(\w+.*\)  -  ", (21, 3))],
    "tool_sessions": [("sessions", ("t", 1), 2, r"\s*User\s+Pid\s+Logged in\s+Kind\s+Login user\s+Account\s+Where from\s+State", (2, 3)), ("sessions", ("t", 1), ("r", 5), r"\[\?\]", (2, 134)),
                      ("sessions", ("b", 2), 2, r"\d+ sessions: ", (14, 3)), ("locks", ("t", 1), 2, r"User\s+File\s+Path\s+Type\s+Record id\s+Since\s+Holder", (17, 3)),
                      ("row", ("b", 2), 2, r"L asks the selected session to end\.", (38, 3))],
    "tool_masters": [("master", ("t", 1), 2, r"\S", (2, 3)), ("master", ("t", 1), ("r", 5), r"\[\?\]", (2, 134)), ("accounts", ("t", 1), 2, r"Account\s+State\s+First difference", (10, 3)),
                     ("accounts", ("b", 2), 2, r"(Nothing to compare yet\.|\d+ accounts? listed\.)", (22, 3)), ("detail", ("b", 2), 2, r"S syncs every account\.", (38, 3))],
    "tool_audit": [("trail", ("t", 1), 2, r"File: ", (2, 3)), ("trail", ("t", 2), 2, r"From: ", (3, 3)), ("trail", ("t", 3), 2, r"Event: ", (4, 3)), ("trail", ("t", 4), 2, r"F filters", (5, 3)),
                   ("trail", ("t", 1), ("r", 5), r"\[\?\]", (2, 134)), ("lines", ("t", 1), 2, r"Time\s+User\s+Event\s+Details", (8, 3))],
    "tool_accounts": [("counts", ("t", 1), 2, r"\d+ accounts?: ", (2, 3)), ("counts", ("t", 2), 2, r"SDSYS, the administrator", (3, 3)), ("counts", ("t", 3), 2, r"C creates an account\.", (4, 3)),
                      ("counts", ("t", 4), 2, r"A adds a person", (5, 3)), ("counts", ("t", 1), ("r", 5), r"\[\?\]", (2, 134)),
                      ("list", ("t", 1), 2, r"\s+Account\s+Kind\s+State\s+Gates that are on\s+Signed on\s+Description", (8, 3))],
}


def bail(msg):
    say("sandbox-l2-admin: CANNOT RUN - " + msg)
    sys.exit(2)


# ------------------------------------------------------------------------------------------------------------------------ a session on a pty
class Win:
    def __init__(self, label, s, cols, rows):
        self.label, self.s, self.cols, self.rows = label, s, cols, rows

    def pump(self, secs):
        """a deadline loop: _pump returns at the FIRST byte, so a wait of N seconds is made here"""
        end = time.time() + secs
        while time.time() < end and not self.s.exited:
            self.s._pump(min(0.2, max(0.01, end - time.time())))
        self.s.settle(0.4)

    def send(self, data, idle=0.6):
        say("   [%s] keys %r" % (self.label, data))
        self.s.type(data, idle=idle)

    def mark(self):
        return len(self.s.raw)

    def resize(self, cols, rows, secs=2.5):
        """the window is resized (TIOCSWINSZ and SIGWINCH); returns the offset of the bytes the program writes in answer"""
        off = self.mark()
        say("   [%s] resize pty %dx%d -> %dx%d (wait %.1f s)" % (self.label, self.cols, self.rows, cols, rows, secs))
        self.s.resize(cols, rows, idle=0.05)
        self.cols, self.rows = cols, rows
        self.pump(secs)
        return off

    def fresh(self, off):
        """a FRESH emulator of the current size fed only the bytes written since `off`: what the program drew for this size"""
        f = Screen(self.cols, self.rows)
        f.feed(self.s.raw[off:].decode("latin-1"))
        return [l.rstrip() for l in f.lines()]

    def lines(self):
        return [l.rstrip() for l in self.s.screen.lines()]

    def end(self):
        if not self.s.exited:
            self.s.type(CTRL_Q, idle=0.8)
        self.s.finish(limit=2.0)
        say("   [%s] finished: exited=%s killed=%s" % (self.label, self.s.exited, getattr(self.s, "killed", False)))


def launch(label, cmd, cols, rows):
    """The administrator's session of the sandbox (SDTEST_ADMIN, cwd the sandbox's SDSYS); TERM xterm; the command typed."""
    env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C", SDTEST_ADMIN="1")
    for k in ("SSH_CONNECTION", "SSH_TTY", "LINES", "COLUMNS"):
        env.pop(k, None)
    argv = [os.path.join(sh.SYS, "bin", "sd")]
    say("== %s: argv=%r cwd=%s TERM=xterm LC_ALL=C SD_CONFIG=%s SDBOX_KEYSET=%s pty=%dx%d command=%r" % (label, argv, sh.SYS, env["SD_CONFIG"], env.get("SDBOX_KEYSET"), cols, rows, cmd))
    w = Win(label, PtySession(argv, sh.SYS, env, cols, rows), cols, rows)
    w.s.settle(1.0)
    w.send("TERM xterm\r", 0.4)
    w.send("TERM %d,%d\r" % (cols, rows), 0.4)
    w.send(cmd + "\r", 1.5)
    w.pump(2.5)
    return w


# ------------------------------------------------------------------------------------------------------------------------ what a screen shows
def ch(lines, r, c):
    return lines[r][c] if 0 <= r < len(lines) and 0 <= c < len(lines[r]) else " "


def boxes_ok(lines, rects, titles):
    """each box on the screen: the title on the top border inside the box, the left and right edges non-blank on every row, the bottom border non-blank along the whole width"""
    bad = []
    for (x, y, w, h, shown), title in zip(rects, titles):
        top = lines[y] if y < len(lines) else ""
        i = top.find(title)
        if i < x + 1 or i + len(title) > x + w:
            bad.append("%r not on the top border of %r (found at column %d)" % (title, (x, y, w, h), i))
        for r in range(y, y + h):
            if ch(lines, r, x) == " " or ch(lines, r, x + w - 1) == " ":
                bad.append("%r: an edge is blank on row %d (left %r right %r)" % (title, r, ch(lines, r, x), ch(lines, r, x + w - 1)))
                break
        for c in range(x, x + w):
            if ch(lines, y + h - 1, c) == " ":
                bad.append("%r: the bottom border is blank at column %d of row %d" % (title, c, y + h - 1))
                break
    return not bad, "; ".join(bad)[:700]


def anchors_ok(lines, page, rects, ids, at140):
    bad = []
    for pid, (kind, k), dx, pat, old in ANCH[page]:
        x, y, w, h, _ = rects[ids.index(pid)]
        r = y + k if kind == "t" else y + h - k
        c = x + dx if isinstance(dx, int) else x + w - dx[1]
        if at140 and (r, c) != old:
            bad.append("%s: the place %r is not the old %r" % (pid, (r, c), old))
        line = lines[r] if r < len(lines) else ""
        if not re.match(r"\s?(?:" + pat + ")", line[c:]):                 # 29 Oct 26: the locks heading begins with the blank of its right-aligned 'User' (fmt 5R)
            bad.append("%s: %r not at row %d column %d (there: %r)" % (pid, pat, r, c, line[c:c + 40]))
    return not bad, "; ".join(bad)[:700]


def foot_ok(lines, cols, rows):
    """the status line '[Pane] ...' on row rows-3, the border (one line character) on rows-2, the function keys with ^Q on the last"""
    L = list(lines) + [""] * rows
    st, bd, ky = L[rows - 3], L[rows - 2], L[rows - 1]
    bd_w = len(bd) if bd and not re.search(r"[A-Za-z0-9]", bd) else 0
    return st.startswith("[") and "^Q" in ky and bd_w == cols, "status %r border %d wide keys %r" % (st[:30], bd_w, ky[:30])


def row(rid, name, ok, detail="", ctrl=True):
    """One result.  `ctrl` False means the control of the group failed: the page was not reached, so the row cannot be believed either way (NULL CASE)."""
    if not ctrl:
        sh.row("%s %s" % (rid, name), False, "NULL CASE: the control of this group failed, the rows below it say nothing. " + detail)
        return False
    sh.row("%s %s" % (rid, name), ok, "" if ok else detail)
    return ok


# ------------------------------------------------------------------------------------------------------------------------ one page
def sec_page(page):
    cmd = page.replace("_", ".", 1)
    with open(os.path.join(l2.GPL, page), encoding="latin-1") as f:
        decl = l2.parse_decl(l2.strip_bas(f.read()))
    if not decl:
        bail("%s: no declaration could be read from the page" % page)
    ids = [a["id"] for a in decl]
    titles = [t for (_, t, _) in l2.REF[page]]
    say("\n--- %s: G1 at 140x43, G2 grown to 180x55, G3 started at 200x60" % cmd)

    def rects_at(W, H):
        rects, mode = M.layout(decl, M.frame(W, H))
        return rects

    # G1
    w = launch("G1-" + cmd, cmd, 140, 43)
    lines = w.lines()
    f0 = foot_ok(lines, 140, 43)
    ctrl = row("G1c", "%s at 140x43 is up: its first title %r is on the screen and the footer is on rows 41-43" % (cmd, titles[0]), titles[0] in "\n".join(lines) and f0[0],
               "%s; screen rows: %r" % (f0[1], [l[:50] for l in lines if l.strip()][:4]))
    r140 = rects_at(140, 43)
    ok, det = boxes_ok(lines, r140, titles)
    row("G1a", "%s at 140x43 every box is where the old page drew it (REF of the free check) and no more: %s" % (cmd, [tuple(r[:4]) for r in r140]), ok and [tuple(r[:4]) for r in r140] == [t[2] for t in l2.REF[page]], det, ctrl)
    ok, det = anchors_ok(lines, page, r140, ids, True)
    row("G1b", "%s at 140x43 the headings, counts, hints and the [?] are at the rows and columns the old page used" % cmd, ok, det, ctrl)

    # G2: the window grows while the page runs
    off = w.resize(180, 55, 3.0)
    fr = w.fresh(off)
    r180 = rects_at(180, 55)
    ok, det = boxes_ok(fr, r180, titles)
    row("G2a", "%s grown to 180x55: the program writes the boxes where the declaration puts them %s (content to column 178 and row 51)" % (cmd, [tuple(r[:4]) for r in r180]), ok, det, ctrl)
    ok, det = anchors_ok(fr, page, r180, ids, False)
    row("G2b", "%s grown to 180x55: the headings, counts, hints and the [?] follow their boxes" % cmd, ok, det, ctrl)
    ok, det = foot_ok(fr, 180, 55)
    row("G2c", "%s grown to 180x55: the footer is written on rows 53-55 with a border 180 wide" % cmd, ok, det, ctrl)
    last = max(r180, key=lambda r: r[1] + r[3])
    right = max(r180, key=lambda r: r[0] + r[2])
    row("G2d", "%s grown to 180x55: the lowest box ends on row 51 and the widest reaches column 178 (nothing is left in the top left 140 by 43)" % cmd,
        last[1] + last[3] - 1 == 51 and right[0] + right[2] - 1 == 178 and ch(fr, 51, 1) != " " and ch(fr, 1, 178) != " " and ch(fr, 51, 178) != " ",
        "lowest ends %d, widest reaches %d; corners %r %r %r" % (last[1] + last[3] - 1, right[0] + right[2] - 1, ch(fr, 51, 1), ch(fr, 1, 178), ch(fr, 51, 178)), ctrl)
    w.end()

    # G3: started big
    w = launch("G3-" + cmd, cmd, 200, 60)
    lines = w.lines()
    r200 = rects_at(200, 60)
    c3 = row("G3c", "%s started at 200x60 is up: its first title is on the screen" % cmd, titles[0] in "\n".join(lines), "screen rows: %r" % ([l[:50] for l in lines if l.strip()][:4]))
    ok, det = boxes_ok(lines, r200, titles)
    row("G3a", "%s started at 200x60: every box where the declaration puts it %s (content to column 198 and row 56)" % (cmd, [tuple(r[:4]) for r in r200]), ok, det, c3)
    ok, det = anchors_ok(lines, page, r200, ids, False)
    row("G3b", "%s started at 200x60: the headings, counts, hints and the [?] follow their boxes" % cmd, ok, det, c3)
    ok, det = foot_ok(lines, 200, 60)
    row("G3c2", "%s started at 200x60: the footer is on rows 58-60 with a border 200 wide" % cmd, ok, det, c3)
    w.end()


def main():
    try:
        sh.setup("sandbox-l2-admin.py")
        for page in l2.PAGE_NAMES:
            sec_page(page)
    finally:
        sh.teardown()
    sh.summary("sandbox-l2-admin")


if __name__ == "__main__":
    main()
