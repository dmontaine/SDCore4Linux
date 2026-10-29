#!/usr/bin/env python3
#
# sandbox-l2-files.py - five toolkit pages on the layout service (S.88 L2, ~/Documents/Audits/TUI/Opus_TUI_Plan.txt section 12): tool.files, tool.catalog, tool.test, tool.bulk and
# tool.query at 140 by 43 (the same page as before L2), at 180 by 55 and 200 by 60 (the boxes grown, the lists longer), and across a resize, on a PSEUDO-TERMINAL.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-l2-files.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT, under /tmp).  Exit 0 no row
# failed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 L2, the pages tool_files, tool_catalog, tool_test, tool_bulk, tool_query).  WRITTEN, NOT RUN (the owner's rule: one complete run when the full-screen
#               phases are done).  Its expected rectangles come from the declarations in the pages' own source, laid out by the model in test-l2-files-units.py (over
#               test-tklayout-units.py's model of $tk_layout).
# END-HISTORY
#
# THE ROWS.
#   S   THE SAME PAGE AT 140 BY 43.  Each page as it was before L2 (the source at OLD_COMMIT, read with git show) is compiled into the sandbox's gpl.bp and drawn on a 140 by 43 pty;
#       then the tree's page is compiled back and drawn the same way.  Every cell of the two screens - text and look (colour, reverse, bold) - must be equal.  A control first: the
#       old page is up (its own title is on the screen), else the S row of that page fails as a null case.
#   G   THE PAGE GROWS.  Started at 180 by 55 and at 200 by 60: the four corners of every pane the page's declaration gives for that size are corner glyphs on the screen, the
#       panes reach the last column and the last row of the body, the status line, the border and the keys are the last three rows, and the lists show as many rows as the
#       list pane has (28 file rows of 30 files at 180 by 55 where 16 were shown at 140 by 43).
#   R   A RESIZE.  Started at 140 by 43, grown to 180 by 55: a FRESH emulator fed only the bytes written after the resize shows the corners of the 180 by 55 panes; shrunk back it
#       shows those of the 140 by 43 panes.
#   K   THE MOUSE ON THE NEW RECTANGLE.  tool.files at 180 by 55: a click on the 20th file row (row 22, a row past the 16 rows the list has at 140 by 43) puts the cursor there.
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


sh = _load("sandbox_home_for_l2files", "sandbox-home.py")             # setup / teardown / adm: the sandbox and the administrator's internal session
L2 = _load("test_l2_files_for_sandbox", "test-l2-files-units.py")      # the pages' declarations over the model of $tk_layout
R = Rows("l2-files")
BOX = SYS = UA = None
E = "\x1b"
CTRL_Q = "\x11"
OLD_COMMIT = "10380d19"                                               # the last commit before L2 moved these pages onto the layout service
REPO = os.environ.get("SDREGRESS_REPO") or os.path.normpath(os.path.join(HERE, "..", "..", ".."))        # regress.sh --snapshot sets it: the copy has no .git
GPLREL = "sdb_ai/sd64/sdsys/gpl.bp/"
CORNERS = set("+") | set("┌┐└┘┬┴├┤┼╔╗╚╝")                                # LC_ALL=C draws +, - and | (UNVERIFIED: this suite has not been run)
# page -> (the verb, a text the old page shows, the view of the declaration, what the list pane holds: (a text on every list row, the id of the list pane, the rows it has at 140 by 43))
PAGES = {
    "tool_files": ("tool.files", "Files in ", 0, ("zzl", "list", 16)),
    "tool_catalog": ("tool.catalog", "Programs in ", 0, ("zzlp", "list", 16)),
    "tool_test": ("tool.test", "Tests in ", 0, ("test.l2", "list", 16)),
    "tool_bulk": ("tool.bulk", "Which records", 0, None),
    "tool_query": ("tool.query", "The sentence", 0, ("zzl", "files", 16)),
}


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-l2-files: CANNOT RUN - " + msg)
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

    def lines(self):
        return [l.rstrip() for l in self.s.screen.lines()]

    def end(self):
        self.s.finish(limit=2.0)                       # hung up: it releases whatever it holds
        say("   [%s] finished: exited=%s" % (self.label, self.s.exited))


def launch(label, cmd, cols, rows):
    """the administrator's session in the sandbox's SDSYS (SDTEST_ADMIN=1); TERM xterm; the verb typed"""
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
    w.pump(2.5)
    return w


def sess(*cmds):
    return "\n".join(sh.adm(*cmds))


# ------------------------------------------------------------------------------------------------------------------------ the fixture
def fixture():
    prog = r"""   open 'bp' to bpf else stop 'no bp'
   for i = 1 to 40
      s =(if i < 10 then '0' else '') : i
      execute 'CREATE.FILE zzl' : s capturing j
      open 'zzl' : s to f then
         for k = 1 to 3
            write 'a' : i : @fm : 'b' : k on f, 'r' : k
         next k
      end
      write '* l2 probe program ' : i : @fm : 'crt "x"' on bpf, 'zzlp' : s
      write '* l2 probe test ' : i : @fm : 'crt "1 passed, 0 failed"' on bpf, 'test.l2.' : s
   next i
   crt 'FIXTURE DONE'
end
"""
    with open(os.path.join(SYS, "bp", "zzl2fx"), "w") as fh:
        fh.write(prog)
    out = sess("BASIC bp zzl2fx", "RUN bp zzl2fx")
    if "FIXTURE DONE" not in out:
        bail("the fixture was not made:\n" + out[-600:])
    chk = sess("COUNT bp WITH @ID LIKE \"zzlp...\"", "COUNT zzl40")
    say(chk[-300:])


# ------------------------------------------------------------------------------------------------------------------------ the old pages and the new
def old_source(page):
    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s%s" % (OLD_COMMIT, GPLREL, page)], capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or ("program $%s" % page) not in r.stdout:
        bail("git show %s:%s%s did not give the page before L2: %s" % (OLD_COMMIT, GPLREL, page, r.stderr.strip()[:200]))
    if "$tk_layout" in r.stdout:
        bail("the page %s at %s already uses the layout service: it is not the page before L2" % (page, OLD_COMMIT))
    return r.stdout


def compile_page(page, text, what):
    with open(os.path.join(SYS, "gpl.bp", page), "w", encoding="latin-1") as f:
        f.write(text)
    out = sh.adm("BASIC gpl.bp " + page)
    ok = sh.has(out, r"^Compiled 1 program\(s\) with no errors")
    say("   compiled the %s %s: %s" % (what, page, "ok" if ok else "FAILED\n" + "\n".join(out[-8:])))
    return ok


def snapshot(w):
    """every cell as (character, look), digits masked"""
    scr = w.s.screen
    L = scr.lines()
    out = []
    for r in range(w.rows):
        line = re.sub(r"\d", "#", (L[r] if r < len(L) else "").ljust(w.cols))
        out.append([(line[c], scr.style(r, c)) for c in range(w.cols)])
    return out


def differences(a, b):
    d = []
    for r in range(min(len(a), len(b))):
        for c in range(min(len(a[r]), len(b[r]))):
            if a[r][c] != b[r][c]:
                d.append((r, c, a[r][c], b[r][c]))
    return d


# ------------------------------------------------------------------------------------------------------------------------ what the model says
def panes(page, view, W, H):
    """id -> (x, y, w, h) of the panes of the page's declaration `view` laid out at W by H, from the page's own source"""
    src = open(os.path.join(HERE, "..", "sdsys", "gpl.bp", page), encoding="latin-1").read()
    decl = L2.declarations(src)[view]
    r, _ = L2.rects_at(decl, W, H)
    return {a["id"]: tuple(t[:4]) for a, t in zip(decl, r)}


def corners_ok(lines, pn):
    """the four corners of every pane are corner glyphs; the list of the ones that are not"""
    bad = []
    for pid, (x, y, w, h) in pn.items():
        for (cy, cx) in ((y, x), (y, x + w - 1), (y + h - 1, x), (y + h - 1, x + w - 1)):
            ch = lines[cy][cx] if cy < len(lines) and cx < len(lines[cy]) else " "
            if ch not in CORNERS:
                bad.append((pid, cy, cx, ch))
    return bad


def foot_ok(lines, cols, rows):
    L = [l.rstrip() for l in lines] + [""] * rows
    st, bd, ky = L[rows - 3], L[rows - 2], L[rows - 1]
    return st.startswith("[") and len(bd) >= cols - 1 and not re.search(r"[A-Za-z0-9]", bd) and ky.strip() != "", "status %r border %d keys %r" % (st[:30], len(bd), ky[:30])


def filled(lines, pn, pid):
    """how many interior rows of pane pid hold any text between its side lines"""
    x, y, w, h = pn[pid]
    return sum(1 for r in range(y + 1, y + h - 1) if r < len(lines) and lines[r][x + 1:x + w - 1].strip())


def listed(lines, pn, key, pid):
    """how many rows inside pane pid hold the text key"""
    x, y, w, h = pn[pid]
    return sum(1 for r in range(y + 1, y + h - 1) if r < len(lines) and key in lines[r][x:x + w])


# ------------------------------------------------------------------------------------------------------------------------ S: the same page at 140 by 43
def sec_same():
    say("\n--- S: at 140 by 43 each page is the page before L2, cell for cell")
    new_text = {p: open(os.path.join(HERE, "..", "sdsys", "gpl.bp", p), encoding="latin-1").read() for p in PAGES}
    olds = {}
    for p, (cmd, mark, _v, _l) in PAGES.items():
        if not compile_page(p, old_source(p), "OLD (%s)" % OLD_COMMIT):
            bail("the old page %s did not compile in this sandbox" % p)
        w = launch("S-old-" + p, cmd, 140, 43)
        t = "\n".join(w.s.screen.lines())
        ok = mark in t and "^Q" in t
        R.row("S0 control: the OLD %s is up at 140x43 (%r and the ^Q key)" % (cmd, mark), ok, t[:200])
        olds[p] = snapshot(w) if ok else None
        w.end()
    for p, (cmd, mark, _v, _l) in PAGES.items():
        if not compile_page(p, new_text[p], "tree's"):
            bail("the tree's %s did not compile in this sandbox" % p)
        w = launch("S-new-" + p, cmd, 140, 43)
        new = snapshot(w)
        old = olds[p]
        d = differences(old, new) if old else ["null case: the old page was not up"]
        R.row("S1 %s at 140x43 is the old page in every cell, text and look" % cmd, old is not None and not d, "%d differences, first %r" % (len(d), d[:5]))
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ G: grown
def sec_grow():
    say("\n--- G: started at 180 by 55 and at 200 by 60")
    for (W, H) in ((180, 55), (200, 60)):
        for p, (cmd, mark, view, lst) in PAGES.items():
            w = launch("G%d-%s" % (W, p), cmd, W, H)
            L = w.lines()
            up = mark in "\n".join(L)
            R.row("G0 control: %s is up at %dx%d (%r on the screen)" % (cmd, W, H, mark), up, "\n".join(L[:6]))
            if not up:
                w.end()
                continue
            pn = panes(p, view, W, H)
            bad = corners_ok(L, pn)
            R.row("G1 %s at %dx%d every pane of the declaration has its four corners on the screen (%d panes)" % (cmd, W, H, len(pn)), not bad, "not corners: %r" % bad[:6])
            right = max(x + w_ - 1 for (x, y, w_, h) in pn.values())
            bottom = max(y + h - 1 for (x, y, w_, h) in pn.values())
            R.row("G2 %s at %dx%d the panes reach column %d and row %d, the last of the body (the window is %d wide and the status line is row %d)" % (cmd, W, H, W - 2, H - 4, W, H - 3),
                  right == W - 2 and bottom == H - 4, "right %d bottom %d" % (right, bottom))
            fo, fd = foot_ok(L, W, H)
            R.row("G3 %s at %dx%d the status line, the border and the keys are the last three rows" % (cmd, W, H), fo, fd)
            if lst:
                key, pid, at140 = lst
                x, y, w_, h = pn[pid]
                got = filled(L, pn, pid)
                R.row("G4 %s at %dx%d the %s pane (%d rows high) is full of text: at least %d of its %d interior rows hold some, where it held %d at 140x43; %d fixture rows carry %r" %
                      (cmd, W, H, pid, h, h - 3, h - 2, at140 + 3, listed(L, pn, key, pid), key), got >= h - 3 and got > at140 + 3, "interior rows with text: %d" % got)
            w.end()


# ------------------------------------------------------------------------------------------------------------------------ R: grown and shrunk
def sec_resize():
    say("\n--- R: started at 140 by 43, grown to 180 by 55, shrunk back")
    for p, (cmd, mark, view, lst) in PAGES.items():
        w = launch("R-" + p, cmd, 140, 43)
        c = mark in "\n".join(w.lines())
        R.row("R0 control: %s is up at 140x43" % cmd, c, "")
        off = w.resize(180, 55)
        fr = w.fresh(off)
        bad = corners_ok([l.rstrip() for l in fr.lines()], panes(p, view, 180, 55))
        R.row("R1 %s resized to 180x55: the bytes written after the resize give the corners of the 180 by 55 panes" % cmd, c and not bad, "not corners: %r" % bad[:6])
        off = w.resize(140, 43)
        fr = w.fresh(off)
        bad = corners_ok([l.rstrip() for l in fr.lines()], panes(p, view, 140, 43))
        R.row("R2 %s shrunk back to 140x43: the corners of the 140 by 43 panes" % cmd, c and not bad, "not corners: %r" % bad[:6])
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ K: the mouse
def sec_mouse():
    say("\n--- K: tool.files at 180 by 55, a click on a row the list did not have at 140 by 43")
    w = launch("K", "tool.files", 180, 55)
    pn = panes("tool_files", 0, 180, 55)
    x, y, w_, h = pn["list"]
    scr = w.s.screen

    def rev(r):
        return "r" in scr.style(r, x + 4)[2]
    first, row20 = y + 2, y + 21                      # item 1 is on row y + 2, item 20 on row y + 21 (the header is on y + 1): row 22 at 180 by 55
    c0 = rev(first) and not rev(row20)
    R.row("K0 control: the first file has the cursor (reverse video on row %d) and row %d has not" % (first, row20), c0, "")
    w.click(x + 4, row20)
    R.row("K1 a click on row %d (the 20th file; the list had 16 rows at 140x43) puts the cursor there" % row20, c0 and rev(row20) and not rev(first), "")
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ main
def main():
    global BOX, SYS, UA
    try:
        sh.setup("sandbox-l2-files.py")
        BOX, SYS = sh.BOX, sh.SYS
        UA = os.path.join(BOX, "user_accounts")
        say("sandbox-l2-files: sandbox %s, keyset %s" % (BOX, os.environ.get("SDBOX_KEYSET")))
        fixture()
        sec_same()
        sec_grow()
        sec_resize()
        sec_mouse()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
