#!/usr/bin/env python3
#
# sandbox-home.py - the home screen and where an account starts (S.75, plan .claude/plan-fullscreen-toolkit.md section 13: H1 the screen, H2 the start), on a pseudo-terminal.
# No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-home.py <dir> [--build] [--only=base,u9,leave,cut]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could
# not run.  ORDINARY sessions are `sd -a<account>` in a fixture account, made with sandbox-gates.py's own functions (the suite stops with exit 2 if its first ordinary session is
# not shown to be one); the administrator's session is SDTEST_ADMIN=1 in the sdsys directory.
#
# START-HISTORY:
# 22 Oct 26 dm  New (S.75, H1 and H2).
# 2 Nov 26 dm   S.88 U9: section u9 (the toolkit's menu bar and type-to-find, rows U9a-U9p) and --only=base,u9 (base: every row before it); the foot row's expected keys follow the table
#               (F10 left the row, / find joined it).  u9 WRITTEN AND RUN ONCE with --only=u9; base NOT rerun.
# 3 Nov 26 dm   S.149: section leave (--only=leave, rows S149a-l): Ctrl-Q on a screen typed at the prompt goes back to the prompt, Ctrl-X signs out there, and a session's own screen keeps Ctrl-Q as Sign out.
# 8 Nov 26 dm   S.172: section cut (--only=cut): in paper and night, at 140 by 43, 172 by 43 and 200 by 50, the administrator's page and zzhm's: no caption ends in the cut mark
#               and the long captions are whole (the owner on sdtest: "The boxes are cutting off the text").
# 28 Oct 26 dm  S.85: setup() runs sandbox-tk-base.py's sudo_null_case() before anything else: every suite built on this setup (the page suites and docs) runs with the stub `sudo` first in PATH,
#               and stops (exit 2) if a child shell or an SD session finds another.  WRITTEN, NOT RUN when added (the owner's rule of 28 Oct).
# END-HISTORY
#
# WHAT IS HELD.  The sandbox starts at the terminal (sandbox-fromtree.py writes start.default = terminal, because every pty suite types at the prompt); this suite changes that for its
# own rows.  The screen is read from the emulator (termscreen.py): the page of an ordinary account and of the administrator, the focus (a reverse-video cell), the keys, a click, the
# tiles that start commands and the screen coming back after them, the Terminal tile and EXIT, sign out, Switch account, where a session starts (the account's own setting, the system
# default, a LOGTO typed at the prompt), a window too small and a piped session (neither is ever handed to the screen), MODIFY.ACCOUNT's three words and SET.START.DEFAULT.  The scroll
# rows run on the sandbox's COPY of tool_home with thirty extra tiles in its table: the shipped page is too short to scroll.  NOT HELD: a dimmed tile (no tile of this page needs a gate),
# CREATE.ACCOUNT's words (not built), a real login over ssh, a UTF-8 border, the page of a window bigger than 140 by 43.
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

spec = importlib.util.spec_from_file_location("sandbox_gates_for_home", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
spec2 = importlib.util.spec_from_file_location("tkb", os.path.join(HERE, "sandbox-tk-base.py"))
tkb = importlib.util.module_from_spec(spec2)
sys.modules["tkb"] = tkb
spec2.loader.exec_module(tkb)
say, row, bail, TOOL = tkb.say, tkb.row, tkb.bail, tkb.TOOL

E = "\x1b"
# the keys of terminfo's linux entry: every account's LOGIN paragraph (newvoc/login) says TERM LINUX, and it runs before the home screen starts, whatever TERM the terminal had
KEYS = {"up": E + "[A", "down": E + "[B", "right": E + "[C", "left": E + "[D", "home": E + "[1~", "end": E + "[4~", "pgup": E + "[5~", "pgdn": E + "[6~", "tab": "\t",
        "btab": E + "[Z", "f2": E + "[[B", "f3": E + "[[C", "f4": E + "[[D", "f5": E + "[[E", "f6": E + "[17~", "f10": E + "[21~", "enter": "\r", "esc": E, "ctrl-q": "\x11", "ctrl-x": "\x18", "bs": "\x7f",
        "alt-x": E + "x", "alt-t": E + "t"}     # S.179, 8 Nov 26: Sign out (after HOME at the prompt) and the Terminal are Alt-X and Alt-T
# a cell inside each tile, on the row of its label, found by the layout of the first screen (13.10): the Tools group at the top, Everyone under it, the header tiles
TILE = {"Editor": (10, 5), "IDE": (10, 27), "Terminal": (17, 5), "Keys": (17, 51), "Files": (24, 5), "Vocabulary": (24, 27), "Dictionary": (24, 51), "Queries": (24, 73), "Bulk update": (24, 97), "Programs": (24, 119), "Tests": (30, 5), "Switch account": (2, 100), "Sign out": (2, 122)}
BOX = SYS = None
THEBOX = None


class H:
    """One session on a pseudo-terminal."""

    def __init__(self, account=None, admin=False, cols=140, rows=43, term="xterm", settle=2.0):
        env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM=term, LC_ALL="C", LANG="C")
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_TTY", None)
        if admin:
            env["SDTEST_ADMIN"] = "1"
        else:
            env.pop("SDTEST_ADMIN", None)
        argv = [os.path.join(SYS, "bin", "sd")] + (["-a" + account] if account else [])
        cwd = SYS if admin else os.path.join(BOX, "user_accounts", account)
        self.s = PtySession(argv, cwd, env, cols, rows)
        self.cols, self.rows = cols, rows
        self.s.settle(settle)

    def lines(self):
        return self.s.screen.lines()

    def line(self, r):
        L = self.lines()
        return L[r].rstrip() if r < len(L) else ""

    def text(self):
        return "\n".join(l.rstrip() for l in self.lines())

    def key(self, name, idle=0.45):
        self.s.type(KEYS[name], idle=idle)

    def typed(self, s, idle=0.8):
        self.s.type(s, idle=idle)

    def click(self, col, rw, idle=0.9):
        self.s.type("%s[<0;%d;%dM%s[<0;%d;%dm" % (E, col + 1, rw + 1, E, col + 1, rw + 1), idle=idle)

    def wheel(self, up, col=60, rw=20, idle=0.6):
        self.s.type("%s[<%d;%d;%dM" % (E, 64 if up else 65, col + 1, rw + 1), idle=idle)

    def style(self, r, c):
        return self.s.screen.style(r, c)

    def focus(self):
        return [n for n, (r, c) in TILE.items() if "r" in self.style(r, c)[2]]

    def prompt(self):
        return any(l.startswith(":") for l in self.lines())

    def home(self):
        T = self.text()
        return "Everyone" in T and "Terminal" in T and "Sign out" in T

    def alive(self):
        self.s._pump(0.3)
        return not self.s.exited

    def end(self):
        self.s.finish()


def dump(h, n=60):
    say("\n".join("%2d|%s" % (i, l.rstrip()[:140]) for i, l in enumerate(h.lines()) if l.strip())[:n * 150])


def reg(name, start=""):
    path = os.path.join(BOX, "user_accounts", name)
    g.reg_write(name, [path, "", g.GROUP, "", "", "", "no", "no", "no", "yes", "yes", "yes", "", "", "", start])


def adm(*cmds):
    return g.adm(list(cmds), internal=True)


def has(lines, pat):
    return any(re.search(pat, ln) for ln in lines)


def default_file():
    return os.path.join(SYS, "start.default")


def file_word():
    """The word in start.default, or None when the file is absent (the delivered state)."""
    try:
        with open(default_file()) as f:
            return f.read().strip()
    except OSError:
        return None


def tiles_file():
    """The words in the system's tiles.off (empty string when the file is empty), or None when it is absent."""
    try:
        with open(os.path.join(SYS, "tiles.off")) as f:
            return f.read().strip()
    except OSError:
        return None


def set_default(word):
    """The system default as the sandbox's own start: 'terminal', 'menu' (written through the verb) or None (the file absent: the delivered state)."""
    if word is None:
        if os.path.exists(default_file()):
            os.remove(default_file())
        return
    out = adm("set.start.default " + word)
    return out


def setup(name):
    """Build (with --build), start and prepare the sandbox and make the fixture accounts; the first row proves an ordinary session is ordinary.  The caller wraps it in try / finally teardown()."""
    global BOX, SYS, THEBOX
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-home.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    say("sandbox-home: sandbox %s" % BOX)
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-home: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYS, "bin", "sd")):
        bail("%s holds no built sandbox" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    g.BOX, g.SYS, g.SD = BOX, SYS, os.path.join(SYS, "bin", "sd")
    tkb.sudo_null_case(BOX)       # S.85: the host's sudo is not reachable from any session below (the stub is first in PATH; a suite that cannot show it stops here)
    g.prepare()
    for a in ("zzhd", "zzhm", "zzht", "zzhs", "zzhv"):
        g.FIXTURES[a] = ("no", "no")
        g.build_account(a)
    reg("zzhd", "")
    reg("zzhm", "menu")
    reg("zzht", "terminal")
    reg("zzhv", "menu")
    # zzhv has no LOGIN paragraph, so its terminal stays what the pty says (TERM=vt100 below: no colour); the others say TERM LINUX
    g.put(os.path.join(SYS, "bp", "zzdel"), "\n".join(["$internal", "   openpath '%s/voc' to v else crt 'ZZDEL no voc' ; stop" % os.path.join(BOX, "user_accounts", "zzhv"),
                                                      "   delete v, 'login'", "   crt 'ZZDEL done'", "end", ""]))
    o = adm("BASIC bp zzdel", "RUN bp zzdel")
    if not has(o, r"^ZZDEL done$"):
        bail("the LOGIN paragraph of zzhv was not removed:\n" + "\n".join(o[-5:]))
    g.reg_write("zzhs", [os.path.join(BOX, "user_accounts", "zzhs"), "", g.GROUP, "", "SUSPENDED", "", "no", "no", "no", "yes", "yes", "yes", "", "", "", "menu"])
    flags = g.flags(g.plain("zzhd", ["zzkf"]))
    say("    (the fixture session: %r)" % (flags,))
    if flags is None or flags[0] != "0":
        bail("the first ordinary session is not shown to be one (admin=%r), so no row below can be believed" % (flags,))
    row("SETUP: an ordinary session in a fixture account is not an administrator (admin=0), and the sandbox starts at the terminal (start.default says terminal)",
        flags[0] == "0" and file_word() == "terminal", repr(flags))


def teardown():
    if SYS and os.path.isdir(SYS):
        set_default("terminal")
    if BOX:
        subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)


def summary(name):
    say("\n%s: %d passed, %d failed" % (name, tkb.passed, tkb.failed))
    sys.exit(0 if tkb.failed == 0 and tkb.passed > 0 else 1)


SECTIONS = ("base", "u9", "leave", "cut")


def only():
    """The sections asked for with --only=NAME[,NAME] (base: every row before 2 Nov 26; u9: the toolkit's menu bar and type-to-find); all of them without it"""
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            want = [w for w in a[len("--only="):].split(",") if w]
            bad = [w for w in want if w not in SECTIONS]
            if bad or not want:
                bail("--only takes %s, not %r" % (",".join(SECTIONS), a))
            return set(want)
    return set(SECTIONS)


def u9_rows():
    """2 Nov 26 (S.88 U9): the home screen on the toolkit's menu bar ($tk_menubar, made from the key table) and type-to-find through $tk_pickrec 'list'.  An ordinary account (zzhm, its
    own word is menu) at 140 by 43; every row reads the emulated screen.  The AI is not on in a sandbox, so its rows are the 'off' half only."""
    say("\n--- U9: the toolkit's menu bar, the keys in the menus, type-to-find")
    h = H("zzhm")
    if not h.home():
        dump(h)
        bail("the home screen never drew for zzhm, so no U9 row can be believed")
    row("U9a the function-key row is the key table's: Enter start  F1 help  F5 refresh  ^Q sign out  / find - F10 is the bar's and not on the row, and the keys that are only in the menus are not on it",
        h.line(42) == "Enter start  F1 help  F5 refresh  ^Q sign out  / find", repr(h.line(42)))
    row("U9b row 0 is the bar made by $tk_menubar: File Go View AI Help at the left, 'home  don@zzhm' at the right (the frame wrote it after the bar)",
        h.line(0).startswith(" File  Go  View  AI  Help") and h.line(0).endswith("home  don@zzhm"), repr(h.line(0)))
    h.key("f10", idle=0.8)
    drop = " ".join(h.line(r) for r in range(1, 8))
    row("U9c F10 opens File: Sign out with the key the table gives it (^Q)", "Sign out" in drop and "^Q" in drop, repr(drop[:200]))
    h.key("right", idle=0.6)
    drop = " ".join(h.line(r) for r in range(1, 9))
    row("U9d ...Right: Go, whose entries show their keys from the table: Back, Terminal Alt-T (S.179: Ctrl-T is the theme on every page), Switch account ^W, Find a tile /",
        all(w in drop for w in ("Back", "Terminal", "Alt-T", "Switch account", "^W", "Find a tile")), repr(drop[:300]))
    h.key("right", idle=0.5)
    h.key("right", idle=0.5)
    h.key("right", idle=0.6)
    drop = " ".join(h.line(r) for r in range(1, 8))
    row("U9e ...Right three times: Help, with Help on this page (F1) and Keys (^K)", "Help on this page" in drop and "F1" in drop and "Keys" in drop and "^K" in drop, repr(drop[:300]))
    h.key("esc", idle=0.7)
    row("U9f Esc closes the menu and the page is whole again", h.home() and "Sign out" not in h.line(1) and h.focus() == ["Editor"], repr((h.line(1)[:60], h.focus())))
    h.key("esc", idle=0.8)
    drop = " ".join(h.line(r) for r in range(1, 8))
    row("U9g Esc on the top page opens the bar (the Esc rule: File's Sign out drops down)", "Sign out" in drop and h.alive(), repr(drop[:200]))
    h.key("esc", idle=0.7)
    row("U9h ...and Esc again closes it: the page is whole, the session alive", h.home() and "Sign out" not in h.line(1) and h.alive(), repr(h.line(1)[:60]))
    h.key("f6", idle=0.6)
    row("U9i F6 with the AI not on for the account changes nothing and says so on the status line", "the AI is not on for this account" in h.line(40) and h.focus() == ["Editor"], repr(h.line(40)))
    h.typed("/", idle=1.0)
    T = h.text()
    row("U9j / opens the pick window of the page's tiles, titled Find a tile, with its filter line ('filter:' and 'n of m', the window's own words)",
        "Find a tile" in T and "filter:" in T and re.search(r"\d+ of \d+", T) is not None, T[-400:])
    h.typed("voc", idle=1.0)
    h.key("enter", idle=1.0)
    T = h.text()
    row("U9k ...typing narrows it (voc) and Enter MOVES the focus to the tile (Vocabulary) without starting it: the window is gone, the page whole, the status line says Enter starts it",
        h.focus() == ["Vocabulary"] and "Find a tile" not in T and h.home() and "Vocabulary: Enter starts it" in h.line(40), repr((h.focus(), h.line(40))))
    h.typed("/", idle=1.0)
    h.typed("ter", idle=0.8)
    h.key("esc", idle=1.0)
    T = h.text()
    row("U9l ...Esc in the window leaves the focus where it was (Vocabulary) and the page whole", h.focus() == ["Vocabulary"] and "Find a tile" not in T and h.home(), repr(h.focus()))
    h.click(7, 0, idle=1.0)
    drop = " ".join(h.line(r) for r in range(1, 8))
    row("U9m a click on Go on row 0 opens Go", "Terminal" in drop and "Find a tile" in drop, repr(drop[:300]))
    h.typed("f", idle=1.2)
    T = h.text()
    row("U9n ...its letter f chooses Find a tile, and the bar's answer runs the page's own case for / : the pick window opens (its filter line, which no menu has)",
        "Find a tile" in T and "filter:" in T and re.search(r"\d+ of \d+", T) is not None, T[-400:])
    h.key("esc", idle=1.0)
    h.typed("\x0b", idle=2.5)
    T = h.text()
    row("U9o Ctrl-K (Help > Keys) lists the keys of this page in a box, as on every page (S.179: it started tool.keys; the Keys tile still does), Ctrl-T the theme among them",
        "Keys of this page" in T and re.search(r"\^T\s+Theme", T) is not None and h.line(0).endswith("home  don@zzhm"),     # the list writes keys as the key row does (^T)
        "\n".join(l.strip() for l in T.splitlines() if "|" in l and l.strip("| -+"))[:600])
    h.key("esc", idle=1.0)
    row("U9p ...and Esc closes the box: the home screen is whole with the same tile selected (Vocabulary)", h.home() and "Keys of this page" not in h.text() and h.focus() == ["Vocabulary"], repr((h.line(0)[-30:], h.focus())))
    h.end()


def leave_rows():
    """3 Nov 26 (S.149; owner: "make ctrl+q leave for the prompt when you typed home"): zzht starts at the prompt, so HOME typed there is a visit and Ctrl-Q goes back to the prompt; zzhm is
    started by the account's own setting, which is the session's own screen, and keeps Ctrl-Q as Sign out.  EXIT after the Terminal tile makes a typed screen the session's own again."""
    say("\n--- Ctrl-Q on a screen typed at the prompt (S.149)")
    h = H("zzht")
    h.typed("home\r", idle=1.5)
    row("S149a the key row of a screen typed at the prompt says ^Q prompt, where a session's own screen says ^Q sign out", h.home() and h.line(42) == "Enter start  F1 help  F5 refresh  ^Q prompt  / find", repr(h.line(42)))
    h.key("ctrl-q", idle=1.3)
    row("S149b Ctrl-Q goes back to the prompt it was typed at: no question, no tiles, the session is alive", h.prompt() and not h.home() and "Sign out of SD?" not in h.text() and h.alive(), h.text()[-300:])
    h.typed("who.am.i\r", idle=1.2)
    row("S149c ...and it is the ordinary prompt of the same account (WHO.AM.I answers zzht)", re.search(r"Account\s*:\s*zzht", h.text()) is not None, h.text()[-300:])
    h.typed("exit\r", idle=2.0)
    row("S149d ...and EXIT there ends the session as QUIT does: leaving did not set the flag that brings the screen back", not h.alive(), h.text()[-200:])
    h.end()
    h = H("zzht")
    h.typed("home\r", idle=1.5)
    h.key("f10", idle=0.8)
    drop = " ".join(h.line(r) for r in range(1, 8))
    row("S149e F10 opens File: Back to the prompt with ^Q, and Sign out with Alt-X (S.179)", "Back to the prompt" in drop and "Sign out" in drop and "^Q" in drop and "Alt-X" in drop, repr(drop[:220]))
    h.key("esc", idle=0.6)
    h.key("alt-x", idle=0.9)
    row("S149f Alt-X asks 'Sign out of SD?' with Sign out and Cancel (Cancel is the default)", "Sign out of SD?" in h.text() and "Cancel" in h.text(), h.text()[-300:])
    h.key("enter", idle=0.8)
    row("S149g Enter takes Cancel: the box closes, the screen is whole and the session is alive", h.home() and "Sign out of SD?" not in h.text() and h.alive(), "")
    h.key("alt-x", idle=0.9)
    h.typed("s", idle=2.0)
    row("S149h the letter S takes Sign out: the session ends", not h.alive(), h.text()[-200:])
    h.end()
    h = H("zzht")
    h.typed("home\r", idle=1.5)
    h.key("down")
    h.key("enter", idle=1.5)
    h.typed("exit\r", idle=1.8)
    row("S149i a screen that EXIT brought back after the Terminal tile is the session's own again: its row says ^Q sign out", h.home() and h.line(42) == "Enter start  F1 help  F5 refresh  ^Q sign out  / find", repr(h.line(42)))
    h.key("ctrl-q", idle=0.9)
    row("S149j ...and Ctrl-Q asks 'Sign out of SD?' there", "Sign out of SD?" in h.text() and h.alive(), h.text()[-200:])
    h.end()
    h = H("zzhm")
    h.key("alt-x", idle=0.9)
    row("S149k a session's own screen (zzhm) has no Alt-X (S.179; it was Ctrl-X): nothing is asked and the screen is whole", h.home() and "Sign out of SD?" not in h.text() and h.alive(), h.text()[-200:])
    h.key("ctrl-q", idle=0.9)
    row("S149l ...and its Ctrl-Q still asks 'Sign out of SD?'", "Sign out of SD?" in h.text(), h.text()[-200:])
    h.end()


CUT = re.compile(r"[A-Za-z]\.(?=[ |+]|$)")      # a word ended by the cut mark: the screen library ends a text that did not fit with '.'


def cut_rows():
    """8 Nov 26 (S.172, the owner on sdtest: "The boxes are cutting off the text"): in the themes paper and night every tile is BOXED, and a caption that filled the tile ran past it,
    so the screen cut the row and ended it in '.' ("Switch accou.", "programs and file.").  For both themes, at 140 by 43 and two wider windows, the administrator's page and an
    ordinary account's (zzhm): no word on the page above the hint row ends in the cut mark, every boxed tile row still ends in its right bar, and the long captions are whole.
    The theme is written to the sandbox's sd.conf for this section only; the bar's colours are the evidence that the theme was in force (the null case)."""
    say("\n--- cut: no tile or button caption is cut in the boxed themes (paper, night)")
    conf = os.path.join(BOX, "sd.conf")
    with open(conf) as fh:
        original = fh.read()
    base = re.sub(r"(?m)^SCREENTHEME=.*\n?", "", original)
    bar = {"paper": (7, 0), "night": (0, 7)}             # ANSI numbers of the menu bar: paper light grey on black, night black on light grey
    whole = {"admin": ["Switch account", "Sign out", "Sessions and locks", "who may do what", "test your keyboard"],
             "zzhm": ["programs and files", "verbs and pointers", "edit many records", "compile, catalog", "run, judge tests", "test your keyboard"]}
    try:
        for theme in ("paper", "night"):
            with open(conf, "w") as fh:
                fh.write(base.rstrip("\n") + "\nSCREENTHEME=%s\n" % theme)
            for cols, rows_ in ((140, 43), (172, 43), (200, 50)):
                for who in ("admin", "zzhm"):
                    if who == "admin":
                        h = H(admin=True, cols=cols, rows=rows_)
                        h.typed("home\r", idle=2.5)
                    else:
                        h = H("zzhm", cols=cols, rows=rows_)
                    L = h.lines()
                    tag = "CUT %s %dx%d %s" % (theme, cols, rows_, who)
                    if not h.home():
                        row(tag + ": the home screen is up", False, "\n".join(l.rstrip() for l in L if l.strip())[-600:])
                        h.end()
                        continue
                    gap = re.search(r"\S  ", L[0])                 # a blank cell of the bar between two menu names: the bar's own style, not a mnemonic's
                    st = h.style(0, gap.start() + 1) if gap else (None, None, "")
                    hint = next((i for i, l in enumerate(L) if "arrows move" in l), len(L) - 3)
                    cuts = ["%d: %s" % (i, m.group(0)) for i in range(1, hint) for m in CUT.finditer(L[i])]
                    T = h.text()
                    missing = [w for w in whole[who] if w not in T]
                    row(tag + ": the theme is in force (the menu bar's colours), so the tiles are boxed", st[:2] == bar[theme], repr(st))
                    row(tag + ": no word above the hint row ends in the cut mark", not cuts, repr(cuts[:6]))
                    row(tag + ": the long captions are whole (%s)" % ", ".join(whole[who]), not missing, repr(missing))
                    if cuts or missing:
                        dump(h)
                    h.end()
    finally:
        with open(conf, "w") as fh:
            fh.write(original)


def main():
    want = only()
    try:
        setup("sandbox-home.py")
        if "cut" in want:
            cut_rows()
        if "u9" in want:
            u9_rows()
        if "leave" in want:
            leave_rows()
        if "base" not in want:
            teardown()
            summary("sandbox-home")

        say("\n--- where a session starts: the system default, the account's own word, a piped session")
        set_default(None)
        h = H("zzhd")
        ok = h.home()
        if not ok:
            dump(h)
        row("the delivered default is menu: with no start.default file an account with no word of its own (zzhd) is given the home screen on a terminal", ok, "")
        h.end()
        h = H("zzhd")
        T = h.text()
        row("...it is the ORDINARY page: the group is 'My tools' (not 'Tools'), the identity row says 'don @ zzhd' and the right end of row 0 names the audience don@zzhd",
            "My tools" in T and "don @ zzhd" in T and "home  don@zzhd" in h.line(0), repr((h.line(0)[-30:], h.line(2)[:30])))
        h.end()
        pipe = g.plain("zzhd", ["who.am.i"])
        row("a PIPED session of the same account (menu by default) is not given the screen: its command runs (Account : zzhd) and no tile is drawn",
            has(pipe, r"Account\s*:\s*zzhd") and not has(pipe, r"My tools|Everyone"), repr(pipe[:6]))
        out = adm("set.start.default terminal")
        row("SET.START.DEFAULT terminal (administrator): says so (11871), and the file holds the word",
            has(out, r"Accounts with no start setting of their own start at: terminal") and file_word() == "terminal", repr(out[:3]))
        h = H("zzhd")
        row("with the default at terminal the account with no word of its own (zzhd) starts at the prompt: a ':' on the screen and no tile", h.prompt() and not h.home(), "")
        h.end()
        h = H("zzhm")
        row("zzhm has its own word (menu) and overrides the default (terminal): it starts in the home screen", h.home(), "")
        h.end()
        set_default("menu")
        h = H("zzht")
        row("zzht has its own word (terminal) and overrides the default (menu): it starts at the prompt", h.prompt() and not h.home(), "")
        h.end()
        out = adm("set.start.default menu")
        row("the same default again says it is already that and changes nothing (11873)", has(out, r"already menu; nothing changed"), repr(out[:3]))
        out = adm("set.start.default")
        row("without a word it says what it is now (11871: menu)", has(out, r"start at: menu"), repr(out[:3]))
        out = adm("set.start.default maybe")
        row("a word that is neither is the usage (11870) and changes nothing", has(out, r"set\.start\.default \{menu \| terminal\}") and file_word() == "menu", repr(out[:3]))
        out = g.plain("zzhd", ["set.start.default terminal"])
        row("an ordinary account cannot run it: the verb is not in its VOC, and the file is unchanged", has(out, r"not in your VOC") and file_word() == "menu", repr(out[:3]))
        pipe = g.plain("zzhd", ["home"])
        row("HOME in a piped session says it needs a terminal (11863) and does not read the input as keys", has(pipe, r"home needs a terminal"), repr(pipe[:4]))

        say("\n--- MODIFY.ACCOUNT's three words (field 16 of the register record)")
        out = adm("modify.account zzhd start-menu")
        field16 = g.reg_read("zzhd")[15] if len(g.reg_read("zzhd")) > 15 else ""
        row("start-menu: 'Account zzhd starts at: menu' (11868), and field 16 of the register record is menu on the disk", has(out, r"Account zzhd starts at: menu") and field16 == "menu", repr((out[:3], field16)))
        out = adm("modify.account zzhd start-menu")
        row("the same word again: 'zzhd already starts that way; nothing changed' (11869)", has(out, r"zzhd already starts that way; nothing changed"), repr(out[:3]))
        out = adm("modify.account zzhd start-terminal")
        field16 = g.reg_read("zzhd")[15]
        row("start-terminal: field 16 is terminal", has(out, r"starts at: terminal") and field16 == "terminal", repr((out[:3], field16)))
        out = adm("modify.account zzhd start-default")
        field16 = g.reg_read("zzhd")[15] if len(g.reg_read("zzhd")) > 15 else ""
        row("start-default: the account follows the system default again - field 16 is empty on the disk", has(out, r"starts at: system default") and field16 == "", repr((out[:3], field16)))
        out = adm("modify.account zzhd start-menu start-terminal")
        row("start-menu with start-terminal in one command is refused before anything changes (11791: the same access to different states)",
            has(out, r"start-menu and start-terminal set the same access to different states") and g.reg_read("zzhd")[15] == "", repr(out[:3]))
        out = adm("modify.account zzhd start-menu voc-off")
        row("start-menu with another word is carried out whole and ends with the summary line (11793)", has(out, r"2 actions carried out") and g.reg_read("zzhd")[15] == "menu", repr(out[:5]))
        adm("modify.account zzhd start-default")
        out = adm("modify.account zzhd start-nowhere")
        row("a word that is not an action is still refused, as typed (11790)", has(out, r"start-nowhere is not a modify.account action"), repr(out[:3]))
        out = adm("modify.account")
        row("the usage names the three words", has(out, r"start-menu \| start-terminal \| start-default"), repr(out[:14]))

        say("\n--- the page, the focus, the keys")
        set_default("menu")
        h = H("zzhm")
        T = h.text()
        if not h.home():
            dump(h)
            bail("the home screen never drew for zzhm, so no row below can be believed")
        row("the ordinary page: group 'My tools' with Editor and IDE (the Record editor tile is gone, S.88 g-P1); group 'Everyone' with Terminal and Keys; Switch account and Sign out in the header",
            all(w in T for w in ("My tools", "Editor", "IDE", "Everyone", "Terminal", "Keys", "Switch account", "Sign out")), "")
        row("the identity (row 2) and the date and time (row 3): 'don @ zzhm' and a line like 'Thursday 22 Oct 2026  -  18:52'",
            h.line(2).strip().startswith("don @ zzhm") and re.match(r"^\s+[A-Z][a-z]+day \d{1,2} [A-Z][a-z]{2} \d{4}  -  \d\d:\d\d", h.line(3)) is not None, repr((h.line(2)[:40], h.line(3)[:50])))
        row("the foot: the hint line (row 39), the status line [Home] (row 40), the border (row 41), the function keys (row 42: Enter start, F1 help, F5 refresh, ^Q sign out, / find; F10 left the row with S.88 U9, 2 Nov 26)",
            "arrows move" in h.line(39) and h.line(40).startswith("[Home]") and set(h.line(41)) == {"-"} and h.line(42) == "Enter start  F1 help  F5 refresh  ^Q sign out  / find", repr((h.line(39)[:30], h.line(40), h.line(42))))
        row("row 0: the menu bar File Go View AI Help at the left, 'home  don@zzhm' at the right", h.line(0).startswith(" File  Go  View  AI  Help") and h.line(0).endswith("home  don@zzhm"), repr(h.line(0)))
        row("the focus starts on the first tile of the page (Editor): one tile in reverse video", h.focus() == ["Editor"], repr(h.focus()))
        # Vocabulary (24,27) is the only tile in IDE's columns below it, so Down from IDE goes to it (a tile that shares columns comes before one that does not: Terminal is narrower than two columns)
        seq = [("right", "IDE"), ("left", "Editor"), ("right", "IDE"), ("down", "Vocabulary"), ("up", "IDE"), ("left", "Editor"), ("down", "Terminal"), ("right", "Keys"), ("left", "Terminal"), ("up", "Editor"), ("down", "Terminal"), ("home", "Editor"), ("end", "Tests"),
               ("home", "Editor"), ("tab", "IDE"), ("btab", "Editor"), ("btab", "Sign out"), ("tab", "Editor")]
        bad = []
        for k, want in seq:
            h.key(k)
            if h.focus() != [want]:
                bad.append("%s -> %r (wanted %s)" % (k, h.focus(), want))
        row("the arrow keys move to the nearest tile in that direction (a tile that shares rows or columns first), Home and End go to the first and last, Tab and Back-tab go in reading order",
            not bad, "; ".join(bad))
        h.key("up")
        row("up from the first row goes to the header: Switch account has the focus", h.focus() == ["Switch account"], repr(h.focus()))
        h.key("pgdn")
        row("Page Down from a header tile does nothing (it has no group)", h.focus() == ["Switch account"], repr(h.focus()))
        h.key("home")
        h.key("pgdn")
        row("Page Down from the first group goes to the first tile of the next one (Terminal); Page Up goes back (Editor)", h.focus() == ["Terminal"], repr(h.focus()))
        h.key("pgup")
        row("...Page Up: Editor", h.focus() == ["Editor"], repr(h.focus()))
        h.typed("k", idle=0.45)
        row("a letter jumps to the next tile whose label begins with it: k - Keys", h.focus() == ["Keys"], repr(h.focus()))
        h.typed("i", idle=0.45)
        row("...i - IDE (the search goes round past the last tile; before S.88 g-P1 this was r - Record editor, and the F5 row below then showed the focus coming back to Editor)", h.focus() == ["IDE"], repr(h.focus()))
        before = h.text()
        h.key("f5", idle=0.8)
        row("F5 builds the page again: the page is the same and the status line says so", h.home() and "page built again" in h.line(40) and h.focus() == ["Editor"], repr((h.line(40), h.focus())))
        h.key("f10", idle=0.8)
        T = h.text()
        row("F10 opens the menu bar: File's drop-down shows Sign out with ^Q", "Sign out" in h.line(1) and "^Q" in h.line(1), repr(h.line(1)))
        h.key("esc", idle=0.6)
        row("Esc closes the menu and the page is whole again", h.home() and "Sign out" not in h.line(1), repr(h.line(1)))
        h.end()

        say("\n--- the administrator's page")
        h = H(admin=True)
        h.typed("home\r", idle=2.5)                     # S.168: the administrator starts at the prompt always; HOME opens the page
        T = h.text()
        row("the administrator's home screen, opened with HOME at the prompt (S.168): group 'Tools' (not 'My tools'), the identity 'administrator', the right end of row 0 'home  administrator'",
            h.home() and "Tools" in T and "My tools" not in T and h.line(2).strip().startswith("administrator") and h.line(0).endswith("home  administrator"), repr((h.line(0)[-24:], h.line(2)[:30])))
        adm_labels = ["Menu management", "Bypass programs", "Audit trail", "Configuration", "Backups", "Master files", "Accounts", "Sessions and locks", "Gates", "Remote servers", "AI"]
        row("the administrator's first screen has a tile for each of the eleven administrator pages, in the groups System, People and access and Data, network and AI, and Tools and Everyone are on it too (no scrolling)",
            all(l in T for l in adm_labels) and all(t in T for t in ("System", "People and access", "Data, network and AI", "Tools", "Everyone", "My programs", "Editor", "Terminal")), repr([l for l in adm_labels if l not in T]))
        nacc = len([a for a in os.listdir(os.path.join(SYS, "accounts")) if a != "sdsys"])
        row("the live lines: Accounts says how many accounts there are (%d on the disk, SDSYS not counted), Sessions and locks how many are signed on (the one session); each in place of the tile's static line.  Master files (tool.entries since S.96 M6, 2 Nov 26) has no live line and shows its static line, every account" % nacc,
            ("%d accounts" % nacc) in T and "1 signed on" in T and "every account" in T and "not set up" not in T and "create and manage" not in T and "who is on" not in T and "shared copies" not in T, repr(re.findall(r"\d+ accounts|\d+ signed on|every account|not set up|nothing pending", T)))
        h2 = H(admin=True)
        h.key("f5", idle=2.0)
        row("a second administrator session signs on and F5 reads the lines again: Sessions and locks now says 2 signed, 2 sdsys (S.76: SDSYS on a terminal in two places is said on the tile; with one it says 1 signed on)",
            h.home() and "2 signed, 2 sdsys" in h.text() and "2 signed on" not in h.text(), repr(re.findall(r"\d+ signed[^ ]* ?(?:on|\d+ sdsys)", h.text())))
        h2.end()
        # The lines are read again each time the key wait runs out (30 seconds without a key).  PtySession._pump(wait) returns as soon as the FIRST byte is ready, not after `wait`
        # seconds (the page's clock redraw at a tick ends it at once), so the wait is a deadline: up to 100 seconds, which holds three readings, until the tile says 1 signed on.
        seen = []
        t_end = time.time() + 100.0
        while time.time() < t_end and "1 signed on" not in h.text():
            h.s._pump(0.5)
        seen.append(re.findall(r"\d+ signed on", h.text()))
        row("the key wait runs out (30 seconds) and the lines are read without a key: the second session has gone, the tile says 1 signed on again, and the page is still whole",
            h.home() and "1 signed on" in h.text() and "2 signed on" not in h.text() and "signed, " not in h.text(),
            repr((seen, "second session exited=%s killed=%s" % (h2.s.exited, getattr(h2.s, "killed", None)), [l for l in adm("LISTU") if "sdsys" in l])))
        h.end()
        h = H(admin=True)
        h.typed("home\r", idle=2.5)                     # S.168
        h.typed("s", idle=0.4)
        h.key("enter", idle=2.5)
        T = h.text()
        row("a tile starts its page: S moves to Sessions and locks, Enter opens tool.sessions (its boxes 'Locks' and 'The row under the cursor', not the home screen)",
            "The row under the cursor" in T and "Locks" in T and not h.home(), T[:200])
        h.typed("\x11", idle=1.5)
        row("...Ctrl-Q ends the page and the home screen is drawn again", h.home(), h.text()[:200])
        h.end()

        say("\n--- no colour: a vt100")
        h = H("zzhv", term="vt100")
        T = h.text()
        row("on a terminal with no colour every tile is boxed: the corners and the lines are on the screen (LC_ALL=C: + - |), and the focused tile (Editor) is in reverse video",
            h.home() and "+-------------------+" in T and "| [=]" in T and "r" in h.style(10, 5)[2], repr((h.line(7)[:30], h.style(10, 5))))      # one space inside the bar since S.172
        h.end()

        say("\n--- the tiles start commands, and the screen comes back")
        h = H("zzhm")
        h.key("down")
        h.key("enter", idle=1.5)
        T = h.text()
        row("Terminal (Enter): the screen is given back - a banner 'Terminal - type exit to return to the home screen' and the ordinary prompt, no tile", "Terminal - type exit to return to the home screen" in T and h.prompt() and not h.home(), T[:200])
        h.typed("who.am.i\r", idle=1.2)
        row("...the prompt is the ordinary command processor, in the account the screen was in: WHO.AM.I answers Account : zzhm", re.search(r"Account\s*:\s*zzhm", h.text()) is not None, h.text()[-300:])
        h.typed("exit\r", idle=1.8)
        row("EXIT comes back to the home screen", h.home(), h.text()[-300:])
        h.key("down")
        h.key("enter", idle=1.5)
        h.typed("exit\r", idle=1.8)
        row("...and again: the flag stays set for the rest of the session", h.home(), h.text()[-300:])
        h.key("home")
        h.key("enter", idle=2.0)
        T = h.text()
        row("Editor (Enter): runs sed - the screen is closed and SED asks 'File name?' at the prompt", "File name?" in T and not h.home(), T[-200:])
        h.typed("\r", idle=1.5)
        row("an empty answer ends SED and the home screen is drawn again", h.home(), h.text()[-300:])
        h.key("right")
        h.key("enter", idle=2.5)
        T = h.text()
        row("IDE (Enter): the IDE takes the terminal (its menu bar is on the screen) and not the home screen", "File" in h.line(0) and "Go" in h.line(0) and "Switch account" not in T, repr(h.line(0)[:60]))
        h.typed("\x11", idle=1.2)
        row("Ctrl-Q ends the IDE and the home screen is drawn again, with the IDE tile still the one selected (not the first tile)", h.home() and h.focus() == ["IDE"], repr((h.home(), h.focus())))
        h.typed("k", idle=0.4)                                  # a letter goes to the next tile whose label begins with it (End is the last tile, which is a Develop tile now)
        h.key("enter", idle=1.8)
        row("Keys (K, Enter): tool.keys is on the screen", "Last keys" in h.text(), h.text()[:200])
        h.typed("\x11", idle=1.2)
        row("...Ctrl-Q ends it and the home screen is drawn again", h.home(), h.text()[-200:])
        row("the page has a group 'Develop' under Everyone with the tile Files (the development tools of every account)", "Develop" in h.text() and "Files" in h.text() and h.text().find("Develop") > h.text().find("Everyone"), h.text()[-600:])
        h.typed("f", idle=0.4)
        h.key("enter", idle=2.5)
        T = h.text()
        row("Files (F, Enter): tool.files is on the screen (its box 'The file under the cursor'), not the home screen", "The file under the cursor" in T and not h.home(), T[:200])
        h.typed("\x11", idle=1.5)
        row("...Ctrl-Q ends it and the home screen is drawn again", h.home(), h.text()[-200:])
        h.typed("v", idle=0.4)
        h.key("enter", idle=2.5)
        T = h.text()
        row("Vocabulary (V, Enter): tool.voc is on the screen (its box 'The entry under the cursor'), not the home screen", "The entry under the cursor" in T and not h.home(), T[:200])
        h.typed("\x11", idle=1.5)
        row("...Ctrl-Q ends it and the home screen is drawn again", h.home(), h.text()[-200:])
        h.end()

        say("\n--- sign out")
        h = H("zzhm")
        h.key("ctrl-q", idle=0.8)
        T = h.text()
        row("Ctrl-Q asks 'Sign out of SD?' with two buttons, Sign out and Cancel", "Sign out of SD?" in T and "Sign out" in T and "Cancel" in T, T[-400:])
        h.key("enter", idle=0.8)
        row("Enter takes the default button, Cancel: the box closes, the home screen is whole and the session is alive", h.home() and "Sign out of SD?" not in h.text() and h.alive(), "")
        h.key("ctrl-q", idle=0.8)
        h.typed("s", idle=2.0)
        row("the letter S takes Sign out: the session ends", not h.alive(), h.text()[-200:])
        h.end()
        h = H("zzhm")
        h.key("btab")
        h.key("enter", idle=0.8)
        row("the Sign out tile (reached with Back-tab) asks the same question", "Sign out of SD?" in h.text(), "")
        h.key("esc", idle=0.5)
        row("Esc is Cancel", "Sign out of SD?" not in h.text() and h.alive(), "")
        h.end()

        say("\n--- EXIT where the home screen was not used")
        h = H("zzht")
        row("zzht starts at the prompt", h.prompt() and not h.home(), h.text()[-200:])
        h.typed("exit\r", idle=2.0)
        row("EXIT at a prompt that never came from the home screen ends the session, as QUIT does", not h.alive(), h.text()[-200:])
        h.end()
        h = H("zzht")
        h.typed("home\r", idle=1.5)
        row("HOME typed at the prompt opens the screen (an account that starts at the terminal can still have it)", h.home(), h.text()[-200:])
        h.key("down")
        h.key("enter", idle=1.5)
        row("its Terminal tile gives the prompt back", h.prompt() and not h.home(), "")
        h.end()


        say("\n--- the mouse")
        h = H("zzhm")
        h.click(TILE["IDE"][1], TILE["IDE"][0], idle=2.5)
        row("a click on the IDE tile starts the IDE", "File" in h.line(0) and "Switch account" not in h.text(), repr(h.line(0)[:50]))
        h.typed("\x11", idle=1.2)
        h.click(TILE["Sign out"][1], TILE["Sign out"][0])
        row("a click on the Sign out tile (in the header) asks 'Sign out of SD?'", "Sign out of SD?" in h.text(), "")
        h.key("esc", idle=0.5)
        h.click(1, 0)
        row("a click on the menu bar opens the menu under it (File)", "Sign out" in h.line(1), repr(h.line(1)))
        h.key("esc", idle=0.5)
        fb = h.focus()
        h.wheel(False)
        row("the wheel on a page that fits changes nothing: the page is whole and the focus has not moved", h.home() and h.focus() == fb and h.line(6).strip().startswith("My tools"), repr((fb, h.focus())))
        h.end()

        say("\n--- Switch account")
        h = H("zzhm")
        h.key("up")
        h.key("enter", idle=1.0)
        T = h.text()
        row("Switch account: a pick list of the accounts this person may enter - zzhd, zzhm and zzht, no suspended account (zzhs) and not sdsys", all(a in T for a in ("zzhd", "zzhm", "zzht")) and "zzhs" not in T and "sdsys" not in T, T[-500:])
        h.key("down")
        h.key("down")
        h.key("enter", idle=2.5)
        row("choosing zzht shows THAT account's home screen: the identity row says 'don @ zzht'", h.home() and h.line(2).strip().startswith("don @ zzht"), repr(h.line(2)))
        h.key("down")
        h.key("enter", idle=1.5)
        h.typed("who.am.i\r", idle=1.2)
        row("...and the process is in that account (the Terminal tile's WHO.AM.I says Account : zzht)", re.search(r"Account\s*:\s*zzht", h.text()) is not None, h.text()[-300:])
        h.end()
        h = H("zzhm")
        h.key("up")
        h.key("enter", idle=1.0)
        h.key("down")
        h.key("enter", idle=2.5)
        row("choosing the account the person is in says so and changes nothing", h.home() and h.line(2).strip().startswith("don @ zzhm") and "already in zzhm" in h.line(40), repr((h.line(2)[:30], h.line(40))))
        h.end()

        say("\n--- a LOGTO typed at the prompt")
        set_default("terminal")
        h = H("zzht")
        h.typed("logto zzhm\r", idle=2.5)
        row("LOGTO into an account that starts in the menu (zzhm) shows its home screen", h.home() and h.line(2).strip().startswith("don @ zzhm"), h.text()[-300:])
        h.key("down")
        h.key("enter", idle=1.5)
        h.typed("logto zzht\r", idle=2.0)
        row("LOGTO into an account that starts at the terminal (zzht) leaves the prompt", h.prompt() and not h.home(), h.text()[-300:])
        h.end()

        say("\n--- a window that is too small")
        set_default("menu")
        h = H("zzhm", cols=100, rows=30)
        h.s._pump(3.5)                                  # home_entry sleeps 2 s after the message before it signs out
        T = h.text()
        # 7 Nov 26 S.164 (owner: "Yes, always sign out"): the prompt is no longer the way out of a screen that could not open.  zzhm's Terminal tile is ON,
        #   which is the case that used to give the prompt; with it off the session was signed out already.
        row("S164a a 100 by 30 window on a start-menu account is not handed to the screen: no tile is drawn, the library's size message and 14015 are shown",
            not h.home() and re.search(r"140", T) is not None and "which could not open, so the session is signed out" in T, T[-400:])
        row("S164b ...and the session is SIGNED OUT, not left at the prompt, although the account's Terminal tile is on", not h.alive(), T[-300:])
        h.end()
        # 7 Nov 26 S.168 (owner: "sdsys should start at the prompt always", after S.167's "Exempt sdsys"): the administrator never starts at the home screen, so at the
        #   same small window there is no screen to refuse - no size message, no 14015 - and at a full-size window it starts at the prompt too (the system default is menu here).
        h = H(None, admin=True, cols=100, rows=30)
        h.s._pump(3.5)
        T = h.text()
        row("S168a the administrator at 100 by 30, the system default menu: no home screen was tried (no size message), no 14015, the prompt, and the session alive",
            "needs a window of at least" not in T and "which could not open, so the session is signed out" not in T and h.prompt() and h.alive(), T[-400:])
        h.typed("who.am.i\r", idle=1.2)
        row("S168b ...and the prompt works (WHO.AM.I answers)", "Account" in h.text(), h.text()[-300:])
        h.end()
        h = H(None, admin=True)
        T = h.text()
        row("S168c the administrator at 140 by 43, the system default menu: the prompt, not the home screen", not h.home() and h.prompt() and h.alive(), T[-300:])
        h.typed("home\r", idle=2.5)
        row("S168d ...and HOME typed there opens the home screen", h.home(), h.text()[-300:])
        h.end()

        say("\n--- the panel scrolls (the sandbox's copy of tool_home with thirty extra tiles in the table)")
        src = open(os.path.join(SYS, "gpl.bp", "tool_home"), encoding="latin-1").read()
        marker = "   gosub add.recent\n   gosub pick.level\n"          # 29 Oct 26: the end of the tile table (the old marker, hx = 95, went with the layout service)
        extra = ("   for fz = 1 to 30\n"
                 "      id = 'zz' : fz ; grp = 1 ; label = 'Filler ' : fz ; glyph = '...' ; sub = 'filler' ; act = 'cmd:who.am.i' ; pal = pal.tools ; size = 'n' ; pause = 1 ; why = '' ; gosub add.tile\n"
                 "   next fz\n")
        if src.count(marker) != 1:
            bail("tool_home has not the one place the scroll rows add their tiles at")
        with open(os.path.join(SYS, "gpl.bp", "tool_home"), "w", encoding="latin-1") as f:
            f.write(src.replace(marker, extra + marker))
        o = adm("BASIC gpl.bp tool_home")
        row("SETUP: the copy with thirty more tiles compiles", has(o, r"Compiled 1 program\(s\) with no errors"), repr(o[-3:]))
        h = H("zzhm")
        T = h.text()
        col = [h.line(r)[139:140] for r in range(5, 39)]
        row("a page taller than the panel has a scroll bar in the last column (rows 5 to 38): an arrow at each end and a thumb at the top", col[0] != " " and any(c in "#|" for c in col) and "".join(col).count("#") >= 1 and col.index([c for c in col if c == "#"][0]) < 6,
            repr("".join(col)))
        row("the header, the hint line and the frame are not part of the panel: they are there", "don @ zzhm" in h.line(2) and "arrows move" in h.line(39) and h.line(40).startswith("[Home]"), "")
        row("at the top the first group's heading 'My tools' is on row 6 and the first tiles under it", h.line(6).strip().startswith("My tools") and "Editor" in h.line(10), repr((h.line(6)[:30], h.line(10)[:30])))
        bar0 = "".join(h.line(r)[139:140] for r in range(5, 39))
        h.key("end")
        T = h.text()
        row("End goes to the last tile of the table (Filler 30) and the panel scrolls to it: Filler 30 is on the screen and the heading 'My tools' is not on row 6 any more", "Filler 30" in T and not h.line(6).strip().startswith("My tools"), h.text()[-600:])
        bar1 = "".join(h.line(r)[139:140] for r in range(5, 39))
        row("...the thumb moved down the bar", bar1.find("#") > bar0.find("#") >= 0, repr((bar0, bar1)))
        row("...the header and the foot are untouched by the scroll", "don @ zzhm" in h.line(2) and "arrows move" in h.line(39) and h.line(40).startswith("[Home]") and h.line(42).startswith("Enter start"), "")
        row("...and the focused tile is the one in view (reverse video somewhere in the panel)", any("r" in h.style(r, c)[2] for r in range(6, 38) for c in (5, 27, 51, 73, 97, 119)), "")
        h.key("home")
        row("Home scrolls back: 'My tools' on row 6 and Editor in reverse video", h.line(6).strip().startswith("My tools") and h.focus() == ["Editor"], repr((h.line(6)[:20], h.focus())))
        h.wheel(False)
        h.wheel(False)
        row("the wheel turned down scrolls the panel (six rows): the heading is gone from row 6", not h.line(6).strip().startswith("My tools"), h.line(6))
        h.wheel(True)
        h.wheel(True)
        row("...and up brings it back", h.line(6).strip().startswith("My tools"), h.line(6))
        h.key("end")
        h.key("pgdn", idle=1.0)
        T = h.text()
        bar2 = "".join(h.line(r)[139:140] for r in range(5, 39))
        term_focus = [r for r in range(6, 38) if h.line(r)[5:13].strip() == "Terminal" and "r" in h.style(r, 5)[2]]        # the page is scrolled, so the fixed cells of TILE do not apply
        row("Page Down from the last of the first group goes to the first tile of the next (Terminal): the panel scrolls to its heading 'Everyone' and the thumb is near the bottom of the bar",
            len(term_focus) == 1 and "Everyone" in T and bar2.rfind("#") > len(bar2) - 14, repr((term_focus, bar2)))       # the Develop group is two rows tall now, so the thumb is in the lower part of the bar, not at its foot
        h.key("home")
        for _ in range(5):
            h.key("down", idle=0.3)
        row("moving down through the rows keeps the focused tile in view (it never leaves the panel)", any("r" in h.style(r, c)[2] for r in range(6, 38) for c in (5, 27, 51, 73, 97, 119)), "")
        h.key("enter", idle=1.8)
        row("a tile that prints (pause) shows its output (WHO.AM.I: the Account line) and asks for Enter (11865); the home screen is not there yet",
            re.search(r"Account\s*:\s*zzhm", h.text()) is not None and re.search(r"Press Enter to return\s*$", h.text(), re.M) is not None and not h.home(), h.text()[-300:])
        h.typed("\r", idle=1.8)
        T = h.text()
        row("...Enter brings the screen back as it was left: the header and a filler tile are there, the question is gone, and the filler tile is still the one selected (the page keeps its scroll, so the heading 'My tools' may be off the top)",
            "Switch account" in T and "Filler" in T and "Press Enter to return" not in T and any("r" in h.style(r, c)[2] for r in range(6, 38) for c in (5, 27, 51, 73, 97, 119)), T[-300:])
        # 7 Nov 26 S.164 (owner: "if the window is shrunk the default is to show only a portion of the home screen and lock user input until it is the right size, not log the person out"):
        #   the window made too small while a tile's command is running is held in the size lock when the screen comes back, and the session is NOT signed out.
        h.key("enter", idle=1.8)
        row("S164c SETUP: the filler tile runs again and asks for Enter", re.search(r"Press Enter to return\s*$", h.text(), re.M) is not None, h.text()[-200:])
        h.s.resize(100, 30, idle=0.8)
        h.typed("\r", idle=2.5)
        T = h.text()
        row("S164c the window made 100 by 30 during the command: the screen comes back behind the size lock (its warning, which names Ctrl-Q), no tile, and NOT the sign-out message",
            "Ctrl-Q" in T and "140 by 43" in T and not h.home() and "which could not open, so the session is signed out" not in T, T[-400:])
        row("S164d ...and the session is still there, not signed out", h.alive(), "")
        h.typed("x", idle=0.8)
        row("S164e a key in the lock is ignored: the warning is still there and the session alive", "Ctrl-Q" in h.text() and h.alive() and not h.home(), h.text()[-200:])
        h.s.resize(140, 43, idle=0.8)
        page = lambda: "Switch account" in h.line(2) and h.line(40).startswith("[Home]")     # the scrolled page: "Everyone" may be off the panel
        for _ in range(8):                              # the lock looks at the window about once a second
            h.s._pump(1.0)
            if page():
                break
        drawn_alone = page()
        say("    (S164f: the page drew by itself after the resize: %s)" % drawn_alone)
        # S.165: it does not - the page stays blank until a key (F5 draws it whole).  A repaint in the reopen and on the next resize did not help (7 Nov), so the
        #   row asks what S.164 promises (the lock lets go, the session lives, a key brings the page) and S.165 holds the blank page.
        if not drawn_alone:
            h.key("f5", idle=1.5)
        ok = page() and h.alive()
        if not ok:
            dump(h, 45)
        row("S164f the window made 140 by 43 again: the lock lets go and the session is at its home screen", ok, repr(h.text()[-300:]))
        h.end()
    finally:
        teardown()
    summary("sandbox-home")


if __name__ == "__main__":
    main()
