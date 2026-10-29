#!/usr/bin/env python3
#
# sandbox-l2-home.py - the home screen on the toolkit's layout service (S.88 L2, ~/Documents/Audits/TUI/Opus_TUI_Plan.txt section 12): the same page at 140 by 43, a tile grid
# that spreads at 180 by 55 and 200 by 60, grown and shrunk, on a PSEUDO-TERMINAL.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-l2-home.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT, under /tmp).  Exit 0 no row
# failed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 L2, the home screen).  WRITTEN, NOT RUN (the owner's rule: one complete run when the full-screen phases are done).  Its expected cells come from
#               the model in test-l2-home-units.py (the page's own columns, band.cols, layout and place.header copied, over test-tklayout-units.py's model of $tk_layout).
# END-HISTORY
#
# THE ROWS.
#   S   THE SAME PAGE AT 140 BY 43.  The page as it was before L2 (tool_home at OLD_COMMIT, read with git show) is compiled into the sandbox's gpl.bp and drawn on a 140 by 43
#       pty, for the administrator and for an ordinary account; then the tree's tool_home is compiled back and drawn the same way.  Every cell of the two screens - text and
#       look (colour, reverse, bold) - must be equal, but for the clock row (row 3) and digits (the live lines count sessions).  A control first: the old page is up (Everyone,
#       Sign out) and its screen is not empty, else every S row fails as a null case.
#   G   THE GRID SPREADS.  Started at 180 by 55 (the administrator) and 200 by 60 (an ordinary account): every tile's label, the header tiles' labels and the hint row stand on the
#       cells the model gives for that size, the status line, the border and the keys are the last three rows, and the right-most tile reaches past column 150.
#   R   A RESIZE.  Started at 140 by 43, grown to 180 by 55: a FRESH emulator fed only the bytes written after the resize (plan 7.4) shows every label on the model's cells for
#       180 by 55 and the footer on rows 53 to 55 (1-based); shrunk back to 140 by 43 it shows the labels of the panel's visible rows on the 140 by 43 cells.
#   K   KEYS AND THE MOUSE ON THE NEW RECTANGLES.  At 180 by 55 a Right arrow moves the focus (the reverse-video label) from the first tile to the second, and a click on the Keys tile
#       at its 180 by 55 cell starts tool.keys (its name on row 0); a click where the Keys tile stood at 140 by 43 that is now another tile does not start tool.keys.
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
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


sh = _load("sandbox_home_for_l2home", "sandbox-home.py")             # setup / teardown / adm / set_default: the sandbox, its fixture accounts and the administrator's internal session
L2 = _load("test_l2_home_for_sandbox", "test-l2-home-units.py")      # the model of the page's grid over the model of $tk_layout
R = Rows("l2-home")
M = L2.TL.Model()
BOX = SYS = UA = None
E = "\x1b"
CTRL_Q = "\x11"
RIGHT = E + "[C"
OLD_COMMIT = "10380d19"                                               # the last commit before L2 moved the home screen onto the layout service
REPO = os.environ.get("SDREGRESS_REPO") or os.path.normpath(os.path.join(HERE, "..", "..", ".."))        # regress.sh --snapshot sets it: the copy has no .git
REL = "sdb_ai/sd64/sdsys/gpl.bp/tool_home"


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-l2-home: CANNOT RUN - " + msg)
    sys.exit(2)


# ------------------------------------------------------------------------------------------------------------------------ a session on a pty
class Win:
    def __init__(self, label, s, cols, rows):
        self.label, self.s, self.cols, self.rows = label, s, cols, rows

    def pump(self, secs):
        """a deadline loop: _pump returns at the FIRST byte, so a wait of N seconds is made here"""
        import time
        end = time.time() + secs
        while time.time() < end and not self.s.exited:
            self.s._pump(min(0.2, max(0.01, end - time.time())))
        self.s.settle(0.4)

    def send(self, data, idle=0.6):
        say("   [%s] keys %r" % (self.label, data))
        self.s.type(data, idle=idle)

    def click(self, col, rw, idle=1.5):
        say("   [%s] click at column %d row %d (0-based)" % (self.label, col, rw))
        self.s.type("%s[<0;%d;%dM%s[<0;%d;%dm" % (E, col + 1, rw + 1, E, col + 1, rw + 1), idle=idle)

    def resize(self, cols, rows, secs=2.0):
        off = len(self.s.raw)
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

    def end(self):
        self.s.finish(limit=2.0)                       # hung up: Ctrl-Q would only open the sign-out box (Cancel is its default)
        say("   [%s] finished: exited=%s" % (self.label, self.s.exited))


def launch(label, cols, rows, account=None):
    """the administrator's session in the sandbox's SDSYS (SDTEST_ADMIN=1), or an ordinary fixture account's (its LOGIN paragraph starts home: start.default is menu); TERM xterm"""
    env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
    for k in ("SSH_CONNECTION", "SSH_TTY", "SDTEST_ADMIN", "LINES", "COLUMNS"):
        env.pop(k, None)
    if not account:
        env["SDTEST_ADMIN"] = "1"
    argv = [os.path.join(SYS, "bin", "sd")] + (["-a" + account] if account else [])
    cwd = os.path.join(UA, account) if account else SYS
    say("== %s: argv=%r cwd=%s TERM=xterm LC_ALL=C SD_CONFIG=%s SDBOX_KEYSET=%s pty=%dx%d" % (label, argv, cwd, env["SD_CONFIG"], env.get("SDBOX_KEYSET"), cols, rows))
    w = Win(label, PtySession(argv, cwd, env, cols, rows), cols, rows)
    w.s.settle(1.0)
    if not account:
        w.send("TERM xterm\r", 0.4)
        w.send("TERM %d,%d\r" % (cols, rows), 0.4)
        w.send("home\r", 1.5)
    w.pump(2.5)
    return w


# ------------------------------------------------------------------------------------------------------------------------ the old page and the new
def compile_home(text, what):
    with open(os.path.join(SYS, "gpl.bp", "tool_home"), "w", encoding="latin-1") as f:
        f.write(text)
    out = sh.adm("BASIC gpl.bp tool_home")
    ok = sh.has(out, r"^Compiled 1 program\(s\) with no errors")
    say("   compiled the %s tool_home: %s" % (what, "ok" if ok else "FAILED\n" + "\n".join(out[-8:])))
    return ok


def old_source():
    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (OLD_COMMIT, REL)], capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or "program $tool_home" not in r.stdout:
        bail("git show %s:%s did not give the page before L2: %s" % (OLD_COMMIT, REL, r.stderr.strip()[:200]))
    if "X.COL" not in r.stdout:
        bail("the page at %s already has no X.COL: it is not the page before L2" % OLD_COMMIT)
    return r.stdout


def snapshot(w):
    """every cell as (character, look), the clock row and digits masked"""
    scr = w.s.screen
    L = scr.lines()
    out = []
    for r in range(w.rows):
        if r == 3:
            out.append(None)
            continue
        line = re.sub(r"\d", "#", (L[r] if r < len(L) else "").ljust(w.cols))
        out.append([(line[c], scr.style(r, c)) for c in range(w.cols)])
    return out


def differences(a, b):
    d = []
    for r in range(min(len(a), len(b))):
        if a[r] is None or b[r] is None:
            continue
        for c in range(min(len(a[r]), len(b[r]))):
            if a[r][c] != b[r][c]:
                d.append((r, c, a[r][c], b[r][c]))
    return d


# ------------------------------------------------------------------------------------------------------------------------ what the model says
def labels():
    """id -> label, read from the tree's build.page"""
    src = open(os.path.join(HERE, "..", "sdsys", "gpl.bp", "tool_home"), encoding="latin-1").read()
    return {m.group(1): m.group(2) for m in re.finditer(r"id = '([a-z]+)' ; grp = [g0] ; label = '([^']*)'", src)}


def expect(W, H, admin):
    """the cells of every tile label (row, column, label, panel row, panel bottom) and of the header labels at W by H, top = 0"""
    raw = L2.load()
    src = L2.code(raw)
    decl, p, groups = L2.declaration(src), L2.params(src), L2.table(src)
    fr = M.frame(W, H)
    rs, _ = M.layout(decl, fr)
    g = dict(zip(["header", "panel", "hint"], rs))
    pnx, py0, pnw, ph, _ = g["panel"]
    nc, tw, xc = L2.columns(pnx, pnw, p)
    gr, tl = L2.page(groups, admin)
    n, _, _ = L2.new_layout(gr, tl, nc, tw, xc)
    lab = labels()
    cells = []
    for i, (x, y, w, h) in n.items():
        top_row = py0 + y                                  # top = 0: panel row y is screen row py0 + y (the BASIC's py0 + ty - top)
        cells.append((tl[i]["id"], top_row, x + 2, lab.get(tl[i]["id"], "?"), py0 + ph - 1))
    hd = L2.header(nc, tw, xc, g["header"][1])
    head = [("switch", hd["switch"][1] + 1, hd["switch"][0] + 7, lab["switch"]), ("signout", hd["signout"][1] + 1, hd["signout"][0] + 7, lab["signout"])]
    return dict(cells=cells, head=head, hint=g["hint"], fr=fr, xc=xc, tw=tw)


def label_at(lines, top_row, col, text, bottom):
    """the label is on the tile's row 3 (colour) or row 2 (plain boxes); a row past the panel's last is not drawn and counts as found"""
    for r, cc in ((top_row + 3, col), (top_row + 2, col + 1)):             # a plain box puts its side line first, so the label is a column further in
        if r > bottom:
            return True
        if r < len(lines) and lines[r][cc:cc + len(text)] == text:
            return True
    return False


def head_at(lines, h):
    """a header tile's label: '  ' glyph '  ' label from the tile's x (colour), one column further in a plain box"""
    r, c, t = h[1], h[2], h[3]
    return r < len(lines) and (lines[r][c:c + len(t)] == t or lines[r][c + 1:c + 1 + len(t)] == t)


def foot_ok(lines, cols, rows):
    L = [l.rstrip() for l in lines] + [""] * rows
    st, bd, ky = L[rows - 3], L[rows - 2], L[rows - 1]
    return st.startswith("[Home]") and len(bd) >= cols - 1 and not re.search(r"[A-Za-z0-9]", bd) and ky.strip() != "", "status %r border %d keys %r" % (st[:30], len(bd), ky[:30])


def grid_rows(tag, lines, ex, rows_, cols_):
    miss = [(c[0], c[1], c[2]) for c in ex["cells"] if not label_at(lines, c[1], c[2], c[3], c[4])]
    R.row("%s1 every tile label on the model's cell at %dx%d (%d tiles)" % (tag, cols_, rows_, len(ex["cells"])), bool(not miss and ex["cells"]), "missing: %r" % miss[:6])
    hm = [h for h in ex["head"] if not head_at(lines, h)]
    R.row("%s2 Switch account and Sign out on the last two tile columns (labels at columns %s)" % (tag, ", ".join(str(h[2]) for h in ex["head"])), not hm, "missing: %r" % hm)
    fo, fd = foot_ok(lines, cols_, rows_)
    R.row("%s3 the status line, the border and the keys are the last three rows of %dx%d" % (tag, cols_, rows_), fo, fd)
    return not miss


# ------------------------------------------------------------------------------------------------------------------------ S: the same page at 140 by 43
def sec_same():
    say("\n--- S: at 140 by 43 the page is the page before L2, cell for cell")
    new_text = open(os.path.join(HERE, "..", "sdsys", "gpl.bp", "tool_home"), encoding="latin-1").read()
    if not compile_home(old_source(), "OLD (%s)" % OLD_COMMIT):
        bail("the old page did not compile in this sandbox")
    olds = {}
    for who, acct in (("administrator", None), ("ordinary", "zzhd")):
        w = launch("S-old-" + who, 140, 43, acct)
        t = "\n".join(w.s.screen.lines())
        ok = "Everyone" in t and "Sign out" in t
        R.row("S0 control: the OLD page is up for the %s at 140x43 (Everyone, Sign out)" % who, ok, t[:200])
        olds[who] = snapshot(w) if ok else None
        w.end()
    if not compile_home(new_text, "tree's"):
        bail("the tree's tool_home did not compile in this sandbox")
    for who, acct in (("administrator", None), ("ordinary", "zzhd")):
        w = launch("S-new-" + who, 140, 43, acct)
        new = snapshot(w)
        old = olds[who]
        d = differences(old, new) if old else ["null case: the old page was not up"]
        R.row("S1 the %s's page at 140x43 is the old page in every cell, text and look (the clock row and digits aside)" % who, old is not None and not d, "%d differences, first %r" % (len(d), d[:5]))
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ G: the grid at 180 by 55 and 200 by 60
def sec_grid():
    say("\n--- G: started at 180 by 55 (administrator) and 200 by 60 (ordinary account)")
    for tag, cols_, rows_, acct in (("G180", 180, 55, None), ("G200", 200, 60, "zzhd")):
        w = launch(tag, cols_, rows_, acct)
        L = [l for l in w.s.screen.lines()]
        ex = expect(cols_, rows_, acct is None)
        grid_rows(tag, L, ex, rows_, cols_)
        hx, hy = ex["hint"][0], ex["hint"][1]
        R.row("%s4 the hint row is row %d (YSTAT - 1) and its text starts at column %d" % (tag, hy, hx + 2), L[hy][hx + 2:hx + 2 + 11] == "arrows move", repr(L[hy][:60]))
        far = max(c[2] for c in ex["cells"])
        sx = ex["head"][-1][2]
        R.row("%s5 the page reaches across the window: the right-most tile label at column %d (past the 140 by 43 grid's 119) and Sign out's at %d (past column 140, where a 140 by 43 "
              "window ends), both on the screen" % (tag, far, sx), far > 119 and sx > 140 and any(label_at(L, c[1], c[2], c[3], c[4]) for c in ex["cells"] if c[2] == far)
              and head_at(L, ex["head"][-1]), "")
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ R: grown and shrunk
def sec_resize():
    say("\n--- R: started at 140 by 43, grown to 180 by 55, shrunk back")
    w = launch("R", 140, 43)
    c = "Everyone" in "\n".join(w.s.screen.lines())
    R.row("R0 control: the administrator's page is up at 140x43", c, "")
    off = w.resize(180, 55)
    fr = w.fresh(off)
    ok = grid_rows("R180", fr.lines(), expect(180, 55, True), 55, 180) if c else False
    off = w.resize(140, 43)
    fr = w.fresh(off)
    ex = expect(140, 43, True)
    miss = [(x[0], x[1], x[2]) for x in ex["cells"] if not label_at(fr.lines(), x[1], x[2], x[3], x[4])]
    R.row("R140 shrunk back to 140x43: the labels of the panel's visible rows are on the 140 by 43 cells (the old X.COL)", c and ok and not miss, "missing: %r" % miss[:6])
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ K: keys and the mouse
def sec_keys():
    say("\n--- K: keys and the mouse on the 180 by 55 rectangles")
    ex = expect(180, 55, True)
    cell = {c[0]: c for c in ex["cells"]}
    w = launch("K", 180, 55)
    first, second = cell["menus"], cell["viewers"]

    def rev(c):
        r = c[1] + 3
        return "r" in w.s.screen.style(r, c[2])[2] or "r" in w.s.screen.style(c[1] + 2, c[2])[2]
    c0 = rev(first) and not rev(second)
    R.row("K0 control: the first tile (Menu management) has the focus at 180x55", c0, "")
    w.send(RIGHT, 0.8)
    R.row("K1 Right moves the focus to Bypass programs, on its 180 by 55 cell (column %d)" % second[2], c0 and rev(second) and not rev(first), "")
    # the click lands near the right end of the Keys tile at 180 by 55, in a column the tile did not reach at 140 by 43 (49 to 69): only a hit test on the NEW rectangles finds it
    old_keys = [c for c in expect(140, 43, True)["cells"] if c[0] == "keys"][0]
    keys = cell["keys"]
    col = keys[2] - 2 + ex["tw"] - 2
    reach = old_keys[2] - 2 + 21 - 1
    w.click(col, keys[1] + 3)
    w.pump(2.0)
    top = w.s.screen.lines()[0] if w.s.screen.lines() else ""
    R.row("K2 a click on the Keys tile at column %d, row %d (inside it at 180 by 55, past where it ended at 140 by 43: %d) starts tool.keys" % (col, keys[1] + 3, reach),
          c0 and col > reach and "tool.keys" in top, repr(top[-40:]))
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ main
def main():
    global BOX, SYS, UA
    try:
        sh.setup("sandbox-l2-home.py")
        BOX, SYS = sh.BOX, sh.SYS
        UA = os.path.join(BOX, "user_accounts")
        say("sandbox-l2-home: sandbox %s, keyset %s" % (BOX, os.environ.get("SDBOX_KEYSET")))
        sh.set_default(None)                                # the delivered default (menu): an ordinary account signs on to the home screen
        sec_same()
        sec_grid()
        sec_resize()
        sec_keys()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
