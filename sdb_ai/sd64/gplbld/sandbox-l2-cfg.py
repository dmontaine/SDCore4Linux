#!/usr/bin/env python3
#
# sandbox-l2-cfg.py - TOOL.CONFIG, TOOL.REMOTE, TOOL.BACKUPS, TOOL.AI and TOOL.MENUS on the layout service ($tk_layout, S.88 stage L2), driven on a PSEUDO-TERMINAL on a private SD.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-l2-cfg.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT, under /tmp).  Exit 0 no row failed, 1 a
# row failed, 2 it could not run.  The administrator's session is SDTEST_ADMIN=1 in the sandbox's sdsys directory (sandbox-home.py's setup; fixture accounts exist, so the menu page's
# Accounts list has rows).
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 L2, the group of tool.config, tool.remote, tool.backups, tool.ai and tool.menus).  WRITTEN, NOT RUN (the owner's rule of 28 Oct: one complete run when the
#               full-screen stages are done).  Its expected rectangles are the MODEL's (test-tklayout-units.py) laid out from the declaration read off each page's own source, and the
#               model was checked against the real $tk_layout once by hand in L1; test-l2-cfg-units.py holds the declarations to the boxes the pages drew before the service.
# END-HISTORY
#
# THE INSTRUMENT.  A page is opened on a pty of the size named, after `TERM xterm` and `TERM cols,rows` (the way sandbox-tk-resize.py does it).  What is judged is the screen of an
# emulator of that size: a page started at the size (S), or a page resized to it, in which case a FRESH emulator of the new size is fed only the bytes the program wrote after the
# resize (plan 7.4: the emulator keeps the cells it had, so a row never reads them).  A box is found by its four corner cells (not a space, not a letter or digit).  Every session prints
# its argv, TERM, size and the keys it is sent.  Each group opens with a CONTROL that passes on the tree as it was (the page is up at 140 by 43, its footer on rows 40-42); when it fails
# the rows below it fail as NULL CASE.
#
#   S0 / B   at 140 by 43 the page is up and drawn EXACTLY as before: every box has the corners of the box the page drew at commit 10380d19 (test-l2-cfg-units.OLD), and the texts the
#            page puts at fixed places are at those places (the anchors below, read from the page's source at that commit)
#   G        started at 180 by 55 the boxes are the model's rectangles for the declaration (the stretching pane takes the extra rows, the width goes to every pane), the [?] is five
#            columns in from the right end of its pane, the footer is on rows 52-54 with a border 180 wide, and text that was cut or wrapped at 134 is now wider
#   Rz       started at 140 by 43 and resized to 180 by 55 the program WRITES the same page (a fresh emulator is fed only the bytes after the resize); resized on to 150 by 45 it follows
#            the shrink: the rectangles are the model's again
#   K        at 180 by 55 the keys still reach the page (Down moves a selection) and a click on the last row of a table puts the cursor there (the hit test is counted from the new rectangle)
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from termscreen import Screen  # noqa: E402
from tuirows import Rows  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_l2cfg", "sandbox-home.py")             # setup / teardown: the sandbox, its fixture accounts
tl = _load("test_tklayout_model_for_l2cfg", "test-tklayout-units.py")   # the model of $tk_layout's equations
lc = _load("test_l2_cfg_for_l2cfg", "test-l2-cfg-units.py")         # the declarations read off the pages, and the boxes they drew before the service
R = Rows("l2-cfg")
M = tl.Model()
BOX = SYS = None
E = "\x1b"
DOWN = E + "[B"
CTRL_Q = "\x11"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# page -> (the command, the pane the table of rows is in or None, the pane ids in the declaration's order)
PAGES = {
    "tool_config": "tool.config",
    "tool_remote": "tool.remote",
    "tool_backups": "tool.backups",
    "tool_ai": "tool.ai",
    "tool_menus": "tool.menus",
}

# The texts the pages put at fixed places, by window size: (text, x, y) is "this text starts at column x of row y" (0-based, as SCREEN TEXT counts); ("~text", y) is "this text is
# somewhere on row y".  At 140 by 43 they are the places of the page as it was (its `screen text ... at x,y` lines at commit 10380d19); at 180 by 55 they are the places the model's rectangles give.
ANCH = {
    "tool_config": {
        (140, 43): [("File: ", 3, 2), ("P parameters", 3, 5), ("[?]", 134, 2), ("Parameter", 5, 8)],
        (180, 55): [("File: ", 3, 2), ("P parameters", 3, 5), ("[?]", 174, 2), ("Parameter", 5, 8)],
    },
    "tool_remote": {
        (140, 43): [("API: ", 3, 2), ("ssh: ", 3, 3), ("1 doors   2 routes", 3, 5), ("[?]", 134, 2), ("What the machine says", 3, 8), ("ON listens on port 4247", 3, 28)],
        (180, 55): [("API: ", 3, 2), ("ssh: ", 3, 3), ("1 doors   2 routes", 3, 5), ("[?]", 174, 2), ("What the machine says", 3, 8), ("ON listens on port 4247", 3, 40)],
    },
    "tool_backups": {
        (140, 43): [("A backup and a restore both run only when every other session", 3, 4), ("B backs every account up", 3, 5), ("[?]", 134, 2), ("Made", 3, 8), ("~director", 28)],
        (180, 55): [("A backup and a restore both run only when every other session", 3, 4), ("B backs every account up", 3, 5), ("[?]", 174, 2), ("Made", 3, 8), ("~director", 40)],
    },
    "tool_ai": {
        (140, 43): [("Provider", 7, 2), ("[?]", 134, 2), ("Account", 3, 24), ("[?]", 134, 24), ("~account", 31), ("One provider and one model serve every account", 3, 34)],
        (180, 55): [("Provider", 7, 2), ("[?]", 174, 2), ("Account", 3, 24), ("[?]", 174, 24), ("~account", 43), ("One provider and one model serve every account", 3, 46)],
    },
    "tool_menus": {
        (140, 43): [("Account", 3, 2), ("[?]", 66, 2), ("Starts in", 74, 2), ("[?]", 134, 2), ("An account with no setting of its own starts in the", 3, 32), ("[?]", 66, 32),
                    ("Arrows move, Tab changes pane", 3, 37)],
        (180, 55): [("Account", 3, 2), ("[?]", 86, 2), ("Starts in", 94, 2), ("[?]", 174, 2), ("An account with no setting of its own starts in the", 3, 44), ("[?]", 86, 44),
                    ("Arrows move, Tab changes pane", 3, 49)],
    },
}
# A text that the page cut at 134 columns (or wrapped at 134) and shows whole (or on the row above) when the box is wider: (row at 140 by 43, row at 180 by 55, the text, where it must be)
WIDE = {
    "tool_config": ("the hint on row 4 is 155 characters: cut at 134 it loses its end, at 180 by 55 it is whole", 4, 4, "disagree.", "row"),
    "tool_remote": ("the first line of the doors view is 170 characters: wrapped at 134 its last sentence is on the next row, at 180 by 55 (a text 174 wide) it is on the first", 28, 40, "OFF opens no API socket at all.", "row"),
}
# the pages with a table whose last row a click can reach: (pane id of the table, the first row of the table below its border = pane y + 2, header rows, keys that make it the table in view)
CLICK = {"tool_config": ("list", 1), "tool_menus": ("menu", 1)}


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-l2-cfg: CANNOT RUN - " + msg)
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

    def click(self, col, rw, idle=0.9):
        self.send("%s[<0;%d;%dM%s[<0;%d;%dm" % (E, col + 1, rw + 1, E, col + 1, rw + 1), idle)

    def mark(self):
        return len(self.s.raw)

    def resize(self, cols, rows, secs=2.0):
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
        return f

    def screen(self):
        return self.s.screen

    def end(self):
        if not self.s.exited:
            self.s.type(CTRL_Q, idle=0.8)
        self.s.finish(limit=2.0)
        say("   [%s] finished: exited=%s killed=%s" % (self.label, self.s.exited, getattr(self.s, "killed", False)))


def launch(label, cmd, cols, rows):
    """The administrator's session of the sandbox (SDTEST_ADMIN=1, cwd the sdsys directory); TERM xterm; the window size given as the answer to TERM; the command typed."""
    env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C", SDTEST_ADMIN="1")
    for k in ("SSH_CONNECTION", "SSH_TTY", "LINES", "COLUMNS"):
        env.pop(k, None)
    argv = [os.path.join(SYS, "bin", "sd")]
    say("== %s: argv=%r cwd=%s TERM=xterm LC_ALL=C SD_CONFIG=%s SDBOX_KEYSET=%s pty=%dx%d command=%r" % (label, argv, SYS, env["SD_CONFIG"], env.get("SDBOX_KEYSET"), cols, rows, cmd))
    w = Win(label, PtySession(argv, SYS, env, cols, rows), cols, rows)
    w.s.settle(1.0)
    w.send("TERM xterm\r", 0.4)
    w.send("TERM %d,%d\r" % (cols, rows), 0.4)
    w.send(cmd + "\r", 1.5)
    w.pump(3.0)
    return w


# ------------------------------------------------------------------------------------------------------------------------ what a screen shows
def line_of(scr, y):
    L = scr.lines()
    return L[y].rstrip() if 0 <= y < len(L) else ""


def corners_ok(scr, rect):
    """the four corner cells of the box are drawn: not a space, not a letter or a digit"""
    x, y, w, h = rect
    for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        L = scr.lines()
        row = L[cy] if 0 <= cy < len(L) else ""
        ch = row[cx] if 0 <= cx < len(row) else " "
        if ch == " " or ch.isalnum():
            return False
    return True


def bad_corners(scr, rects):
    return [r for r in rects if not corners_ok(scr, r)]


def anchors_bad(scr, anchors):
    bad = []
    for a in anchors:
        if a[0].startswith("~"):
            if a[0][1:] not in line_of(scr, a[1]):
                bad.append("%r not on row %d (%r)" % (a[0][1:], a[1], line_of(scr, a[1])[:60]))
        else:
            t, x, y = a
            if line_of(scr, y)[x:x + len(t)] != t:
                bad.append("%r not at %d,%d (%r)" % (t, x, y, line_of(scr, y)[x:x + len(t) + 10]))
    return bad


def foot_bad(scr, cols, rows):
    """the status line '[Pane] ...' on row rows-3, the border on rows-2 (cols wide), the function keys on the last row"""
    st, bd, ky = line_of(scr, rows - 3), line_of(scr, rows - 2), line_of(scr, rows - 1)
    bad = []
    if not st.startswith("["):
        bad.append("status row %d: %r" % (rows - 3, st[:30]))
    if len(bd) != cols or re.search(r"[A-Za-z0-9]", bd):
        bad.append("border row %d is %d wide: %r" % (rows - 2, len(bd), bd[:20]))
    if "^Q" not in ky:
        bad.append("key row %d: %r" % (rows - 1, ky[:30]))
    return bad


def expected(page, cols, rows, floor=(140, 43)):
    """the model's rectangles for the page's declaration (read off the tree's source) in a layout of cols by rows: the pane ids and the rectangles (x, y, w, h), in the order declared"""
    with open(os.path.join(TREE, "sdsys", "gpl.bp", page), encoding="latin-1") as f:
        decl = lc.parse_decl(lc.strip_bas(f.read()))
    fr = M.frame(cols, rows, floor[0], floor[1])
    rects, _ = M.layout(decl, fr)
    return [d["id"] for d in decl], [r[:4] for r in rects]


def judge(rid, page, cols, rows, scr, ctrl, nbytes=None):
    """the geometry rows for one screen of one page at one size: the boxes, the anchors (at 140 by 43 and 180 by 55), the footer"""
    cmd = PAGES[page]
    ids, rects = expected(page, cols, rows)
    if (cols, rows) == (140, 43):
        old = dict(lc.OLD[page])
        want = [old[i] for i in ids]
        assert sorted(want) == sorted(rects)
    else:
        want = rects
    bad = bad_corners(scr, want)
    ok_box = not bad
    ok_foot = not foot_bad(scr, cols, rows)
    anc = ANCH[page].get((cols, rows))
    ab = anchors_bad(scr, anc) if anc else []
    sfx = "" if nbytes is None else "; bytes written: %d" % nbytes
    if not ctrl:
        R.row("%s %s at %dx%d NULL CASE: the control of this group failed, the rows say nothing" % (rid, cmd, cols, rows), False, "", phase=None)
        return
    R.row("%s %s at %dx%d every box is drawn where %s: %d boxes %r" % (rid, cmd, cols, rows, "the page drew it before the service" if (cols, rows) == (140, 43) else "the model puts it", len(want), want),
          ok_box, "corners missing: %r%s" % (bad, sfx), phase=None)
    R.row("%s2 %s at %dx%d the footer is on rows %d-%d (status line, border %d wide, keys)" % (rid, cmd, cols, rows, rows - 3, rows - 1, cols), ok_foot, "; ".join(foot_bad(scr, cols, rows)) + sfx, phase=None)
    if anc is not None:
        R.row("%s3 %s at %dx%d the texts are where %s (%d anchors)" % (rid, cmd, cols, rows, "the page put them before the service" if (cols, rows) == (140, 43) else "the rectangles put them", len(anc)),
              not ab, "; ".join(ab)[:400] + sfx, phase=None)


# ------------------------------------------------------------------------------------------------------------------------ the groups
def sec_at_140():
    say("\n--- S0 / B: at 140 by 43 each page is drawn exactly as before the layout service")
    for page, cmd in PAGES.items():
        w = launch("B-" + page, cmd, 140, 43)
        scr = w.screen()
        up = not foot_bad(scr, 140, 43) and ANCH[page][(140, 43)][0][0].lstrip("~") in "\n".join(scr.lines())
        ctrl = R.row("S0 %s at 140x43 the page is up (its footer on rows 40-42 and its first text on the screen)" % cmd, up, "\n".join(l[:100] for l in scr.lines()[:6]), phase=None)
        judge("B", page, 140, 43, scr, ctrl)
        if page in WIDE:
            what, row140, row180, text, _ = WIDE[page]
            R.row("B4 %s at 140x43 %s: %r is NOT yet on row %d" % (cmd, what, text, row140), text not in line_of(scr, row140), line_of(scr, row140)[:140], phase=None) if ctrl else None
        w.end()


def sec_started_big():
    say("\n--- G: each page started at 180 by 55 uses the whole window")
    for page, cmd in PAGES.items():
        w = launch("G-" + page, cmd, 180, 55)
        scr = w.screen()
        up = not foot_bad(scr, 180, 55)
        ctrl = R.row("G0 %s started at 180x55 it drew its page (footer on rows 52-54, a border 180 wide)" % cmd, up, "\n".join(l[:100] for l in scr.lines()[:6]), phase=None)
        judge("G", page, 180, 55, scr, ctrl)
        if page in WIDE and ctrl:
            what, row140, row180, text, _ = WIDE[page]
            R.row("G4 %s at 180x55 %s: %r is on row %d" % (cmd, what, text, row180), text in line_of(scr, row180), line_of(scr, row180)[:178], phase=None)
        # the rightmost column the page uses and the lowest row: the corners of the last box are at column 178 and the foot of the body
        ids, rects = expected(page, 180, 55)
        right = max(r[0] + r[2] for r in rects) - 1
        low = max(r[1] + r[3] for r in rects) - 1
        L = scr.lines()
        R.row("G5 %s at 180x55 the content reaches column %d and row %d (the body ends at column 178 and row 51 less the page's own spare rows)" % (cmd, right, low),
              right == 178 and any(len(l) > 170 for l in L[:52]) and line_of(scr, low).strip() != "", "right edge %d, lowest row %d: %r" % (right, low, line_of(scr, low)[:60]), phase=None) if ctrl else None
        w.end()


def sec_resized():
    say("\n--- Rz: each page resized 140x43 -> 180x55 -> 150x45 follows the window (judged on the bytes written after each resize)")
    for page, cmd in PAGES.items():
        w = launch("Rz-" + page, cmd, 140, 43)
        scr = w.screen()
        ctrl = R.row("Rz0 %s at 140x43 before the resize the page is up" % cmd, not foot_bad(scr, 140, 43), "", phase=None)
        off = w.resize(180, 55, 2.5)
        fr = w.fresh(off)
        judge("Rz", page, 180, 55, fr, ctrl, nbytes=len(w.s.raw) - off)
        if page in WIDE and ctrl:
            what, row140, row180, text, _ = WIDE[page]
            R.row("Rz4 %s resized to 180x55 %s: %r is on row %d" % (cmd, what, text, row180), text in line_of(fr, row180), line_of(fr, row180)[:178], phase=None)
        off = w.resize(150, 45, 2.5)
        fr = w.fresh(off)
        ids, rects = expected(page, 150, 45)
        bad = bad_corners(fr, rects)
        R.row("Rz5 %s resized on to 150x45 (above the floor) every box is the model's: %r" % (cmd, rects), ctrl and not bad and not foot_bad(fr, 150, 45), "corners missing: %r; %s" % (bad, "; ".join(foot_bad(fr, 150, 45))), phase=None)
        off = w.resize(140, 43, 2.5)
        fr = w.fresh(off)
        old = dict(lc.OLD[page])
        ids, rects = expected(page, 140, 43)
        bad = bad_corners(fr, [old[i] for i in ids])
        R.row("Rz6 %s back at 140x43 it is the page of today again: %d boxes" % (cmd, len(ids)), ctrl and not bad and not foot_bad(fr, 140, 43), "corners missing: %r" % (bad,), phase=None)
        w.end()


def sec_keys():
    say("\n--- K: at 180 by 55 the keys reach the page and a click is counted from the new rectangle")
    for page, cmd in PAGES.items():
        w = launch("K-" + page, cmd, 180, 55)
        scr = w.screen()
        ctrl = R.row("K0 %s at 180x55 the page is up" % cmd, not foot_bad(scr, 180, 55), "", phase=None)
        if page in ("tool_config", "tool_ai", "tool_menus"):
            before = [r for r in range(scr.rows) if scr.reverse(r)]
            w.send(DOWN, 0.6)
            w.send(DOWN, 0.6)
            w.pump(0.8)
            after = [r for r in range(scr.rows) if scr.reverse(r)]
            R.row("K1 %s at 180x55 Down twice changes the reverse-video rows (the keys reach the page)" % cmd, ctrl and before != after, "before %r after %r" % (before[-4:], after[-4:]), phase=None)
        elif page == "tool_remote":
            w.send("3", 1.2)
            w.pump(0.8)
            R.row("K1 %s at 180x55 the key 3 shows the servers view (the status line names it)" % cmd, ctrl and "[Servers]" in line_of(scr, 52), line_of(scr, 52)[:60], phase=None)
        else:
            w.send(E + "[15~", 1.2)                         # F5 as the xterm terminfo entry names it (the session said TERM xterm)
            w.pump(0.8)
            R.row("K1 %s at 180x55 F5 reads the directory again (the status line says so)" % cmd, ctrl and "read again" in line_of(scr, 52), line_of(scr, 52)[:60], phase=None)
        if page in CLICK:
            pid, first = CLICK[page]
            ids, rects = expected(page, 180, 55)
            r = rects[ids.index(pid)]
            # config: the table is the list pane, its rows are 2.. below the pane's top; the last visible row is the pane's height - 2 rows down (VP = h - 3, the header on y + 1)
            # menus: the Menu box has 17 rows from the pane's y + 1; its last standard row is row 17
            if page == "tool_config":
                y = r[1] + 1 + (r[3] - 3)
                x = r[0] + 7
            else:
                y = r[1] + 17
                x = r[0] + 10
            w.click(x, y)
            w.pump(0.6)
            rev = scr.reverse(y)
            R.row("K2 %s at 180x55 a click at column %d, row %d (the last row of the table in the new rectangle) highlights that row" % (cmd, x, y), ctrl and rev != "", "reverse text on row %d: %r" % (y, rev[:60]), phase=None)
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ main
def main():
    global BOX, SYS
    try:
        sh.setup("sandbox-l2-cfg.py")
        BOX, SYS = sh.BOX, sh.SYS
        say("sandbox-l2-cfg: sandbox %s, keyset %s" % (BOX, os.environ.get("SDBOX_KEYSET")))
        sec_at_140()
        sec_started_big()
        sec_resized()
        sec_keys()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
