#!/usr/bin/env python3
#
# sandbox-home2.py - the home screen's leftovers (S.75, "home" sitting of 26 Oct 26): SUB-MENUS with a Back tile, the RECENT group, create.account taking the start and pins words, and the
# standard tile ids - on a pseudo-terminal.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-home2.py <dir> [--build] [--only=C,D,B,A] [--mutant=NAME|all]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row failed, 2
# it could not run.  It uses sandbox-home.py's setup (the same fixture accounts, ordinary sessions through sandbox-gates.py, the sandbox starting at the terminal) and its session class.
# With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the programs, the section that holds the rows for it is run, and exit 0 means the rows that had to fail failed and no
# others (MUTANTS); --mutant=all does that for each in one run.  A built sandbox may be run again without --build: the programs are put back from the tree first.
#
# START-HISTORY:
# 26 Oct 26 dm  New (S.75, home).
# END-HISTORY
#
#   C  SUB-MENUS.  The delivered page has no folder tile, so the rows run on the sandbox's COPY of tool_home with one declared (the Develop group becomes the menu develop, a tile Develop in
#      Everyone opens it) and a chain of nine menus: the page and its path on the status line, the Back tile, Esc and Backspace and the menu and a click, the focus given back, a menu that is
#      open above refused (11956), the ninth level refused (11957), Switch account starting at the top page, and a tile started in a sub-menu coming back as a Recent tile
#   D  THE STANDARD TILE IDS.  SET.TILE accepts all fourteen ids without the "not standard" note, and with all of them off the page draws nothing but Sign out (the ids are the tiles it draws)
#   B  CREATE.ACCOUNT's START-MENU, START-TERMINAL and PINS-ON, on an OTHER account (a sandbox cannot make Linux users: GROUP and USER need root and are for the VM witness): the register
#      fields, the lines said, the audit line, two start words refused with nothing made, words that restate the delivered state refused, and !create_account called with a start word that is
#      neither (nothing made).  sudo is a stand-in first in PATH whose log is read
#   A  THE RECENT GROUP, in the account's own file &menus& (record RECENT): off as delivered and nothing written; on from the View menu; the tiles started, newest first, six at most; a record
#      edited by hand (junk, duplicates, an id the page does not offer); the group off again forgets the list and writes nothing; the administrator's SET.TILE ... recent off wins; the person's own
#      programs are not kept; an account whose VOC may not be changed
#
# THE INSTRUMENT.  Every outcome of A is read from the DISK: the record is read by a program of the administrator's (zzrc), which opens the account's file by its real path.  Nothing in A is
# judged by what the screen said alone.  NOT HELD: GROUP and USER accounts made with the words (witness-accounts.sh), the real sd-elevate, a real login over ssh.
import importlib.util
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
GPLBP = os.path.join(TREE, "sdsys", "gpl.bp")
sys.path.insert(0, HERE)

spec = importlib.util.spec_from_file_location("sandbox_home_for_home2", os.path.join(HERE, "sandbox-home.py"))
sh = importlib.util.module_from_spec(spec)
sys.modules["sandbox_home_for_home2"] = sh
spec.loader.exec_module(sh)
say, bail, has, dump, adm, H, g = sh.say, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g

COLS = (3, 25, 49, 71, 95, 117)          # the x of the six tile columns
RES = {}                                 # row id -> passed
MUT = False                              # the mutant mode: rows are tallied by id and not counted as failures


def R(rid, name, ok, detail=""):
    RES[rid] = bool(ok)
    if MUT:
        say("    [%s] %s" % ("ok" if ok else "FAILED", rid))
    else:
        sh.row("%s %s" % (rid, name), ok, detail)


# ------------------------------------------------------------------------------------------------------------------------------- the sandbox's own copies of the programs

def sb_gpl(name):
    return os.path.join(sh.SYS, "gpl.bp", name)


def read_file(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def write_file(path, text):
    with open(path, "w", encoding="latin-1") as f:
        f.write(text)


def compile_programs(*names):
    out = adm("BASIC gpl.bp " + " ".join(names))
    if not has(out, r"Compiled %d program\(s\) with no errors" % len(names)):
        bail("%s did not compile in the sandbox:\n%s" % (" ".join(names), "\n".join(out[-8:])))


def restore(*names):
    """The tree's own text of each program back into the sandbox, and compiled."""
    for n in names:
        write_file(sb_gpl(n), read_file(os.path.join(GPLBP, n)))
    compile_programs(*names)


def patch(name, old, new):
    """One change in the sandbox's copy; old is text that must be found exactly once, or re:<pattern> (a regular expression that must match exactly once)."""
    src = read_file(sb_gpl(name))
    if old.startswith("re:"):
        out, n = re.subn(old[3:], lambda m: new, src)
    else:
        n = src.count(old)
        out = src.replace(old, new)
    if n != 1:
        bail("the text to change in %s is found %d times, not once: %r" % (name, n, old[:70]))
    write_file(sb_gpl(name), out)


# ------------------------------------------------------------------------------------------------------------------------------- the account's file &menus&, read and written from outside

ARGS = None


def acct_dir(a):
    return os.path.join(sh.BOX, "user_accounts", a)


def menus_dir(a):
    """The real path of the account's file &menus& on the disk, or None when it is not there."""
    try:
        names = [n for n in os.listdir(acct_dir(a)) if "menus" in n]
    except OSError:
        return None
    return os.path.join(acct_dir(a), names[0]) if names else None


def setup_programs():
    global ARGS
    ARGS = os.path.join(sh.BOX, "rwarg.txt")
    g.put(os.path.join(sh.SYS, "bp", "zzrc"), "\n".join([
        "$internal", "   openseq '%s' readonly to d else crt 'RC noarg' ; stop" % ARGS, "   readseq path from d else crt 'RC noarg' ; stop", "   readseq rname from d else crt 'RC noarg' ; stop", "   closeseq d",
        "   if path = '' then crt 'RC nofile' ; stop", "   openpath path to f else crt 'RC nofile' ; stop",
        "   read r from f, rname then", "      crt 'RC rec=' : change(r, @fm, '/')", "   end else", "      crt 'RC norec'", "   end", "end", ""]))
    g.put(os.path.join(sh.SYS, "bp", "zzrw"), "\n".join([
        "$internal", "   openseq '%s' readonly to d else crt 'RW noarg' ; stop" % ARGS, "   readseq path from d else crt 'RW noarg' ; stop", "   readseq rname from d else crt 'RW noarg' ; stop",
        "   rec = ''", "   loop", "      readseq line from d else exit", "      rec<-1> = change(change(line, '~', @vm), '_', ' ')", "   repeat", "   closeseq d",
        "   openpath path to f else crt 'RW nofile' ; stop", "   write rec to f, rname", "   crt 'RW done'", "end", ""]))
    out = adm("BASIC bp zzrc zzrw")
    if not has(out, r"Compiled 2 program\(s\) with no errors"):
        bail("the reader and writer programs did not compile:\n" + "\n".join(out[-8:]))


def rc_read(a, rname="recent"):
    """What the record is on the disk: 'nofile', 'norec' or its fields joined with /."""
    g.put(ARGS, "%s\n%s\n" % (menus_dir(a) or "", rname))
    out = adm("RUN bp zzrc")
    for ln in out:
        m = re.match(r"^RC (nofile|norec|noarg|rec=(.*))$", ln)
        if m:
            return m.group(2) if m.group(2) is not None else m.group(1)
    bail("the reader printed no RC line:\n" + "\n".join(out[-6:]))


def rc_write(a, rname, fields):
    """Write a record by hand into the account's file &menus& (fields: a list; ~ is a value mark and _ a blank)."""
    g.put(ARGS, "%s\n%s\n%s\n" % (menus_dir(a), rname, "\n".join(fields)))
    out = adm("RUN bp zzrw")
    if not has(out, r"^RW done$"):
        bail("the writer did not write %s of %s:\n%s" % (rname, a, "\n".join(out[-6:])))


def fresh(a, start="menu", edit="yes"):
    """The fixture account made again (its file &menus& gone) and its register record rewritten."""
    g.FIXTURES.setdefault(a, ("no", "no"))
    g.build_account(a)
    g.reg_write(a, [acct_dir(a), "", g.GROUP, "", "", "", "no", "no", "no", edit, edit, edit, "", "", "", start])


# ------------------------------------------------------------------------------------------------------------------------------- reading the screen

def label_at(h, r, c):
    """The text of the label row of the tile whose column is c."""
    return h.line(r)[c + 2:c + 22].strip()


def focus_label(h):
    """The label of the tile that is in reverse video (a tile of the panel, not a header tile)."""
    for r in range(6, 39):
        L = h.line(r)
        for c in COLS:
            if len(L) > c + 2 and L[c + 2].isalpha() and "r" in h.style(r, c + 2)[2]:
                return L[c + 2:c + 22].strip()
    return None


def heading_row(h, name):
    for r in range(5, 39):
        if re.search(r"(^|\s)%s(\s|$)" % re.escape(name), h.line(r)):
            return r
    return None


def is_top(h):
    return "Sign out" in h.text() and h.line(40).startswith("[Home]")


def go_top(h):
    """Back to the top page by the Back tile (Esc is under test and must not be what puts a row right): at most ten clicks."""
    for _ in range(10):
        if is_top(h):
            return
        h.click(8, 2, idle=1.0)


def norm(h):
    """The top page with the folder tile Develop selected: the start of the next row, whatever the last one did."""
    go_top(h)
    h.typed("d", idle=0.45)


def view_menu(h):
    """F10, then Right twice: the View menu's drop-down is open."""
    h.key("f10", idle=0.8)
    h.key("right", idle=0.5)
    h.key("right", idle=0.6)


def turn_group(h):
    view_menu(h)
    h.typed("g", idle=1.3)


def run_tile(h, letter, wait=2.0):
    """A letter to the tile, Enter to start it, Ctrl-Q to leave what it opened.  The page comes back."""
    h.typed(letter, idle=0.45)
    h.key("enter", idle=wait)
    h.typed("\x11", idle=1.6)


def tile_labels(h, row=10):
    return [label_at(h, row, c) for c in COLS]


# ------------------------------------------------------------------------------------------------------------------------------- C  sub-menus

FOLDERS = ("   id = 'develop' ; grp = g ; label = 'Develop' ; glyph = '[+]' ; sub = 'seven tools' ; act = 'menu:develop' ; pal = 'gray' ; size = 'n' ; pause = 0 ; why = '' ; gosub add.tile\n"
           "   id = 'chain' ; grp = g ; label = 'Chain' ; glyph = '[+]' ; sub = 'eight deep' ; act = 'menu:chain1' ; pal = 'gray' ; size = 'n' ; pause = 0 ; why = '' ; gosub add.tile\n")
DEVELOP_OLD = "   bnd += 1\n   g += 1\n   gr<g> = 'Develop' : @vm : bnd : @vm : 6\n"
DEVELOP_NEW = "   bnd += 1\n   g += 1\n   gr<g> = 'Develop' : @vm : bnd : @vm : 6\n   gr<g, HG.MENU> = 'develop'\n   gr<g, HG.BAND> = 1\n"
CHAIN = ("   id = 'again' ; grp = g ; label = 'Again' ; glyph = '(o)' ; sub = 'opens itself' ; act = 'menu:develop' ; pal = 'gray' ; size = 'n' ; pause = 0 ; why = '' ; gosub add.tile\n"
         "   for fz = 1 to 9\n"
         "      g += 1\n"
         "      gr<g> = 'Level ' : fz : @vm : 1 : @vm : 6\n"
         "      gr<g, HG.MENU> = 'chain' : fz\n"
         "      if fz < 9 then\n"
         "         id = 'down' : fz ; grp = g ; label = 'Down ' : fz ; glyph = 'v  ' ; sub = 'level ' : fz ; act = 'menu:chain' : (fz + 1) ; pal = 'gray' ; size = 'n' ; pause = 0 ; why = '' ; gosub add.tile\n"
         "      end else\n"
         "         id = 'leaf' ; grp = g ; label = 'Leaf' ; glyph = '.  ' ; sub = 'level 9' ; act = 'cmd:who.am.i' ; pal = 'gray' ; size = 'n' ; pause = 1 ; why = '' ; gosub add.tile\n"
         "      end\n"
         "   next fz\n")
HX_MARK = "   hx = 95 ; hy = 1\n"


def declare_folders():
    """The sandbox's copy of tool_home with a sub-menu declared (see the header): the Develop group is the menu develop, its folder is in Everyone, and a chain of nine menus."""
    patch("tool_home", DEVELOP_OLD, FOLDERS + DEVELOP_NEW)
    patch("tool_home", HX_MARK, CHAIN + HX_MARK)
    compile_programs("tool_home")


def c_sub():
    a = "zzhm"
    fresh(a)
    declare_folders()
    h = H(a)
    T = h.text()
    R("C1", "the top page: the folder tile Develop is in the group Everyone, the seven tools are NOT on it, and no tile of the page is lost (Editor, IDE, Record editor, Terminal, Keys, Chain)",
      is_top(h) and "Develop" in h.line(17) and not any(w in T for w in ("Files", "Vocabulary", "Dictionary", "Queries", "Bulk update", "Programs", "Tests")) and all(w in T for w in ("Editor", "IDE", "Record editor", "Terminal", "Keys", "Chain")),
      repr((h.line(17)[:110], h.line(40))))
    R("C1b", "...and it has no Back tile (the header's left end is the identity)", "Back" not in h.line(2)[:24] and h.line(2).strip().startswith("don @ zzhm"), repr(h.line(2)[:40]))
    h.typed("d", idle=0.45)
    R("C1c", "a letter jumps to the folder tile like any other (D: Develop has the focus)", focus_label(h) == "Develop", repr(focus_label(h)))
    h.key("enter", idle=1.2)
    T = h.text()
    R("C2", "Enter opens the sub-menu as a page of its own: the status line shows the path [Home > Develop], the seven tools are on it (and Terminal is not), the first one has the focus",
      h.line(40).startswith("[Home > Develop]") and all(w in T for w in ("Files", "Vocabulary", "Dictionary", "Queries", "Bulk update", "Programs", "Tests")) and "Terminal" not in T and focus_label(h) == "Files",
      repr((h.line(40), focus_label(h))))
    R("C2b", "...the Back tile is at the left of the header and the identity has moved right of it; Switch account and Sign out are still there",
      "Back" in h.line(2)[3:24] and h.line(2)[25:].strip().startswith("don @ zzhm") and "Switch account" in T and "Sign out" in T, repr(h.line(2)[:60]))
    R("C2c", "...and the function-key row names Esc (Enter start  Esc back  F5 refresh  F10 menu  ^Q sign out)", h.line(42) == "Enter start  Esc back  F5 refresh  F10 menu  ^Q sign out", repr(h.line(42)))
    h.key("enter", idle=2.5)
    started = "The file under the cursor" in h.text()
    h.typed("\x11", idle=1.6)
    R("C3", "a tile of the sub-menu starts its page (Files: tool.files), and Ctrl-Q brings back the sub-menu with the status path and the same tile selected",
      started and h.line(40).startswith("[Home > Develop]") and focus_label(h) == "Files", repr((started, h.line(40), focus_label(h))))
    h.key("right", idle=0.4)
    h.key("esc", idle=1.2)
    R("C_ESC", "Esc goes back one page: the top page, the status line [Home], the identity at the left again and no Back tile", is_top(h) and h.line(2).strip().startswith("don @ zzhm") and "Back" not in h.line(2)[:24],
      repr((h.line(40), h.line(2)[:40])))
    R("C_FOCUS", "...with the folder tile (Develop) selected as it was left, not the first tile of the page", focus_label(h) == "Develop", repr(focus_label(h)))
    norm(h)
    h.key("enter", idle=1.2)
    h.key("bs", idle=1.2)
    R("C_BS", "Backspace goes back one page too, with the folder tile selected", is_top(h) and focus_label(h) == "Develop", repr((h.line(40), focus_label(h))))
    norm(h)
    h.key("enter", idle=1.2)
    h.click(8, 2, idle=1.4)
    R("C_BACKTILE", "a click on the Back tile goes back one page", is_top(h), repr(h.line(40)))
    h.click(73, 17, idle=1.4)
    R("C_CLICK", "a click on the folder tile opens the sub-menu", h.line(40).startswith("[Home > Develop]"), repr(h.line(40)))
    h.key("f10", idle=0.8)
    h.key("right", idle=0.5)
    h.typed("b", idle=1.2)
    R("C_MENU", "the Go menu's Back entry goes back one page", is_top(h), repr(h.line(40)))
    h.key("f10", idle=0.8)
    h.key("right", idle=0.5)
    h.typed("b", idle=0.8)
    h.key("esc", idle=0.6)
    R("C_MENU_TOP", "on the top page the same entry cannot be chosen (its letter does nothing); Esc closes the menu and the page is whole", is_top(h) and h.alive(), repr(h.line(40)))
    h.key("esc", idle=0.8)
    R("C_ESC_TOP", "Esc on the top page does nothing: the page is whole, the session is alive", is_top(h) and h.alive(), repr(h.line(40)))
    norm(h)
    h.key("enter", idle=1.2)
    h.typed("a", idle=0.45)
    h.key("enter", idle=1.0)
    R("C_CYCLE", "a folder tile that opens the menu already open is refused (11956) and the page stays where it is",
      "develop is already open above this page" in h.line(40) and h.line(40).startswith("[Home > Develop]"), repr(h.line(40)))
    norm(h)
    h.typed("c", idle=0.45)
    h.key("enter", idle=1.0)
    for _ in range(7):
        h.key("enter", idle=0.9)
    path = "[Home > Chain > " + " > ".join("Down %d" % n for n in range(1, 8)) + "]"
    got = h.line(40)
    h.key("enter", idle=1.0)
    R("C_PATH", "Chain, then seven folder tiles of the chain: the path on the status line is Home > Chain > Down 1 ... Down 7 (eight pages deep)", got.startswith(path), repr(got))
    R("C_DEPTH", "the ninth page is refused (11957): the message is on the status line and the page is still the eighth", "Pages can be opened 8 deep at most" in h.line(40) and h.line(40).startswith(path), repr(h.line(40)))
    for _ in range(8):
        h.key("esc", idle=0.7)
    R("C_UNWIND", "Esc eight times is back at the top page with the Chain tile selected", is_top(h) and focus_label(h) == "Chain", repr((h.line(40), focus_label(h))))
    norm(h)
    h.key("enter", idle=1.2)
    h.click(100, 2, idle=1.2)
    h.key("enter", idle=2.5)
    R("C_SWITCH", "Switch account from a sub-menu page shows the other account's TOP page (status line [Home], no Back tile, the other identity)",
      h.line(40).startswith("[Home]") and "Back" not in h.line(2)[:24] and h.line(2).strip().startswith("don @ zzhd"), repr((h.line(40), h.line(2)[:40])))
    h.end()
    if MUT:
        return                      # the mutants' rows end here: the Recent rows below take a minute and no mutant is about them (mutate() puts the programs back)
    # a tile started inside a sub-menu is offered by the Recent group of the top page, and the copy starts the same tool
    fresh(a)
    h = H(a)
    turn_group(h)
    h.typed("d", idle=0.45)
    h.key("enter", idle=1.2)
    h.key("enter", idle=2.5)
    h.typed("\x11", idle=1.6)
    go_top(h)
    R("C_RECENT", "a tile started in a sub-menu is kept by the Recent group (the record says files) and the top page shows its copy first, under the heading Recent",
      rc_read(a) == "on/files" and heading_row(h, "Recent") == 6 and label_at(h, 10, 3) == "Files" and is_top(h), repr((rc_read(a), heading_row(h, "Recent"), tile_labels(h))))
    h.key("home", idle=0.5)
    h.key("enter", idle=2.5)
    R("C_RECENT2", "...and Enter on the copy starts tool.files from the top page", "The file under the cursor" in h.text(), repr(h.text()[:120]))
    h.typed("\x11", idle=1.6)
    h.end()
    restore("tool_home")


# ------------------------------------------------------------------------------------------------------------------------------- D  the standard ids

STANDARD = "editor ide ced terminal keys switch signout files voc dict query bulk catalog test recent".split()
LABELS = ("Editor", "IDE", "Record editor", "Terminal", "Keys", "Switch account", "Files", "Vocabulary", "Dictionary", "Queries", "Bulk update", "Programs", "Tests")


def d_ids():
    a = "zzhm"
    fresh(a)
    offs = [t for t in STANDARD if t != "signout"]
    out = adm(*(["set.tile %s %s off" % (a, t) for t in offs] + ["set.tile %s zzcustom off" % a]))
    nonstd = [ln for ln in out if "is not a standard tile" in ln]
    R("D1", "SET.TILE takes all fourteen standard ids (the seven development tiles and recent among them) with 'is now off' and no 'not a standard tile' note; an id that is not one still gets the note",
      len([ln for ln in out if re.search(r"^Tile \S+ is now off for zzhm$", ln)]) == 15 and len(nonstd) == 1 and "zzcustom" in nonstd[0], repr(out[-6:]))
    r = g.reg_read(a)
    f17 = r[16] if len(r) > 16 else ""
    R("D1b", "...and field 17 of the register record holds the fourteen ids", sorted(f17.split()) == sorted(offs + ["zzcustom"]), repr(f17))
    h = H(a)
    T = h.text()
    R("D2", "with every standard id off (all but Sign out, which cannot be) the page draws nothing but Sign out: no tile of the page is outside the standard ids, and no group heading is left",
      "Sign out" in T and not any(w in T for w in LABELS) and not any(w in T for w in ("My tools", "Everyone", "Develop", "Recent")), repr(T[:300]))
    h.end()
    out = adm("set.tile %s signout off" % a)
    R("D3", "Sign out is a standard id and cannot be turned off (11878)", has(out, r"Sign out cannot be turned off"), repr(out[:3]))


# ------------------------------------------------------------------------------------------------------------------------------- B  create.account

SHIM = "#!/bin/sh\necho \"sudo $*\" >> %s\nexit 0\n"
LOGP = None


def run_create(cmds, internal=False):
    """A session of the administrator with a sudo stand-in first in PATH: nothing here runs as root, and the stand-in's log says what the verb asked for."""
    global LOGP
    shim_dir = os.path.join(sh.BOX, "shimbin")
    os.makedirs(shim_dir, exist_ok=True)
    LOGP = os.path.join(shim_dir, "sudo.log")
    g.put(os.path.join(shim_dir, "sudo"), SHIM % LOGP)
    os.chmod(os.path.join(shim_dir, "sudo"), 0o755)
    env = g.env(True)
    env["PATH"] = shim_dir + ":" + env.get("PATH", "")
    argv = [g.SD] + (["-internal"] if internal else [])
    say("    > [admin] [PATH has the sudo stand-in]%s: %s" % (" [internal]" if internal else "", " | ".join(cmds)))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run(argv, input=body, cwd=sh.SYS, env=env, capture_output=True, text=True, errors="replace", timeout=300)
    out = g.ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip() for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


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
        return ""
    try:
        with open(os.path.join(sh.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def reg_field(a, n):
    try:
        r = g.reg_read(a)
    except OSError:
        return None
    return r[n - 1] if len(r) >= n else ""


def b_create():
    p = lambda n: os.path.join(sh.BOX, "user_accounts", n)
    for n in ["zzco%d" % k for k in range(1, 10)]:         # a rerun on the same sandbox: the accounts an earlier run made are put away first, or 'already exists' would answer for them
        if os.path.exists(os.path.join(sh.SYS, "accounts", n)):
            os.remove(os.path.join(sh.SYS, "accounts", n))
        if os.path.isdir(p(n)):
            shutil.rmtree(p(n))
    out = run_create(["create.account"])
    R("B0", "the usage names the words: start-menu | start-terminal and pins-on", has(out, r"start-menu \| start-terminal\} \{pins-on\}") and has(out, r"unless pins-on is typed"), repr(out[:6]))
    a0 = audit_off()
    out = run_create(["create.account other zzco1 %s start-menu pins-on no.query" % p("zzco1")])
    new = audit_new(a0)
    R("B1", "start-menu pins-on: 'Account zzco1 starts at: menu' (11868) and 'may add its own programs to the home screen: yes' (11885) are said",
      has(out, r"Account zzco1 starts at: menu") and has(out, r"Account zzco1 may add its own programs to the home screen: yes"), repr(out[-8:]))
    R("B1b", "...the register record on the disk: field 16 is menu and field 18 is yes", reg_field("zzco1", 16) == "menu" and reg_field("zzco1", 18) == "yes", repr((reg_field("zzco1", 16), reg_field("zzco1", 18))))
    R("B1c", "...and the audit line is create.account account=zzco1 type=other gates=pins-on start=menu (lower case)", "create.account account=zzco1 type=other gates=pins-on start=menu" in new, repr(new[-200:]))
    log = open(LOGP).read() if LOGP and os.path.exists(LOGP) else ""
    R("B1d", "...the sudo stand-in was what the verb called (its log has a chown-account line for the new directory), so nothing ran as root", "chown-account" in log and p("zzco1") in log, repr(log[-200:]))
    a0 = audit_off()
    out = run_create(["create.account other zzco2 %s start-terminal no.query" % p("zzco2")])
    new = audit_new(a0)
    R("B2", "start-terminal alone: field 16 is terminal, field 18 is empty (pins stay off), and the audit line says gates=none start=terminal",
      reg_field("zzco2", 16) == "terminal" and reg_field("zzco2", 18) == "" and "create.account account=zzco2 type=other gates=none start=terminal" in new
      and has(out, r"Account zzco2 starts at: terminal") and not has(out, r"may add its own programs"), repr((reg_field("zzco2", 16), reg_field("zzco2", 18), new[-120:])))
    a0 = audit_off()
    out = run_create(["create.account other zzco3 %s no.query" % p("zzco3")])
    new = audit_new(a0)
    R("B3", "neither word: fields 16 and 18 are empty (the account follows the system default, pins off), nothing is said about them, and the audit line is the old one with no start= tail",
      reg_field("zzco3", 16) == "" and reg_field("zzco3", 18) == "" and not has(out, r"starts at") and not has(out, r"home screen") and "create.account account=zzco3 type=other gates=none" in new and "start=" not in new,
      repr((reg_field("zzco3", 16), out[-4:], new[-120:])))
    a0 = audit_off()
    out = run_create(["create.account other zzco4 %s pins-on no.query" % p("zzco4")])
    new = audit_new(a0)
    R("B3b", "pins-on alone: field 18 is yes, field 16 empty, audit gates=pins-on and no start=", reg_field("zzco4", 18) == "yes" and reg_field("zzco4", 16) == "" and "gates=pins-on" in new and "start=" not in new, repr((reg_field("zzco4", 18), new[-120:])))
    a0 = audit_off()
    out = run_create(["create.account other zzco5 %s start-menu start-terminal no.query" % p("zzco5")])
    new = audit_new(a0)
    R("B4", "start-menu with start-terminal is refused (11791) BEFORE anything is made: no register record, no directory, no audit line",
      has(out, r"start-menu and start-terminal set the same access to different states") and reg_field("zzco5", 16) is None and not os.path.exists(p("zzco5")) and "zzco5" not in new, repr((out[-3:], os.path.exists(p("zzco5")), new[-100:])))
    out = run_create(["create.account other zzco5 %s start-default no.query" % p("zzco5"), "create.account other zzco5 %s pins-off no.query" % p("zzco5")])
    R("B5", "start-default and pins-off restate the delivered state and are not accepted here ('Unexpected token'), and nothing is made",
      len([ln for ln in out if "Unexpected token (start-default)" in ln]) == 1 and len([ln for ln in out if "Unexpected token (pins-off)" in ln]) == 1 and reg_field("zzco5", 16) is None and not os.path.exists(p("zzco5")), repr(out[-4:]))
    g.put(os.path.join(sh.SYS, "bp", "zzcab"), "\n".join([
        "$internal", "$include createacc.h",
        "   settings = '' ; settings<CA$START> = 'bogus' ; settings<CA$PATH> = '%s'" % p("zzco6"),
        "   call !create_account('OTHER', 'zzco6', settings, err)",
        "   crt 'CAB1 err=' : change(err, @vm, '/')",
        "   settings = '' ; settings<CA$START> = 'MENU' ; settings<CA$PATH> = '%s'" % p("zzco7"),
        "   call !create_account('OTHER', 'zzco7', settings, err)",
        "   crt 'CAB2 err=' : change(err, @vm, '/')",
        "   settings = '' ; settings<CA$START> = 'terminal' ; settings<CA$PINS> = 1 ; settings<CA$PATH> = '%s' ; settings<CA$NO.QUERY> = 1" % p("zzco8"),
        "   call !create_account('OTHER', 'zzco8', settings, err)",
        "   crt 'CAB3 err=[' : err : ']'",
        "   settings = '' ; settings<CA$PINS> = 'yes' ; settings<CA$PATH> = '%s' ; settings<CA$NO.QUERY> = 1" % p("zzco9"),
        "   call !create_account('OTHER', 'zzco9', settings, err)",
        "   crt 'CAB4 err=[' : err : ']'",
        "end", ""]))
    out = run_create(["BASIC bp zzcab", "RUN bp zzcab"], internal=True)
    R("B_BOGUS", "!create_account called with a start word that is neither (bogus, MENU) refuses it with 2018 and makes NOTHING: no register record, no directory",
      has(out, r"^CAB1 err=2018/bogus$") and has(out, r"^CAB2 err=2018/MENU$") and reg_field("zzco6", 16) is None and reg_field("zzco7", 16) is None and not os.path.exists(p("zzco6")) and not os.path.exists(p("zzco7")), repr(out[-8:]))
    R("B6", "...called with terminal and CA$PINS = 1 it makes the account (field 16 terminal, 18 yes); CA$PINS = 'yes' is not exactly 1 and leaves pins off",
      has(out, r"^CAB3 err=\[\]$") and reg_field("zzco8", 16) == "terminal" and reg_field("zzco8", 18) == "yes" and has(out, r"^CAB4 err=\[\]$") and reg_field("zzco9", 18) == "",
      repr((out[-4:], reg_field("zzco8", 16), reg_field("zzco8", 18), reg_field("zzco9", 18))))


# ------------------------------------------------------------------------------------------------------------------------------- A  the Recent group

def a_basic():
    a = "zzhm"
    fresh(a)
    h = H(a)
    T = h.text()
    R("A1", "as delivered the group is OFF: no Recent heading on the page and no file &menus& in the account", is_top(h) and "Recent" not in T and menus_dir(a) is None, repr((menus_dir(a), h.line(6)[:40])))
    view_menu(h)
    R("A2", "the View menu offers 'Recent group (off)'", "Recent group (off)" in h.text(), repr(h.text()[:400]))
    h.typed("g", idle=1.3)
    R("A3", "choosing it turns the group on (11958 on the status line); the file &menus& is made in the person's own account and the record RECENT is the one word on",
      "The Recent group is on" in h.line(40) and menus_dir(a) is not None and rc_read(a) == "on", repr((h.line(40), menus_dir(a), rc_read(a))))
    run_tile(h, "k")
    R("A4", "Keys started: the group is the first on the page (heading Recent on row 6, the tile Keys first) and the record is on/keys; the page is whole",
      is_top(h) and heading_row(h, "Recent") == 6 and label_at(h, 10, 3) == "Keys" and rc_read(a) == "on/keys", repr((heading_row(h, "Recent"), tile_labels(h), rc_read(a))))
    h.typed("e", idle=0.45)
    h.key("enter", idle=2.0)
    h.typed("\r", idle=1.6)
    run_tile(h, "i", wait=2.5)
    R("A5", "Editor, then the IDE: newest first - IDE, Editor, Keys - on the page and in the record",
      rc_read(a) == "on/ide/editor/keys" and tile_labels(h)[:3] == ["IDE", "Editor", "Keys"] and is_top(h), repr((rc_read(a), tile_labels(h))))
    h.key("home", idle=0.5)
    R("A6", "Home goes to the first tile of the page, the first Recent tile (IDE)", focus_label(h) == "IDE" and h.line(10)[5:8] == "IDE", repr(focus_label(h)))
    h.key("enter", idle=2.5)
    opened = "File" in h.line(0) and "Switch account" not in h.text()
    h.typed("\x11", idle=1.6)
    R("A7", "Enter on the Recent copy starts the same tool (the IDE) and Ctrl-Q brings the page back; the order is unchanged (it was already first)",
      opened and is_top(h) and rc_read(a) == "on/ide/editor/keys" and focus_label(h) == "IDE", repr((opened, rc_read(a), focus_label(h))))
    h.key("right", idle=0.4)
    h.key("right", idle=0.4)
    h.key("enter", idle=2.0)
    opened = "Last keys" in h.text()
    h.typed("\x11", idle=1.6)
    R("A8", "the third Recent tile (Keys) starts tool.keys and moves to the front: the record is on/keys/ide/editor and so is the page",
      opened and rc_read(a) == "on/keys/ide/editor" and tile_labels(h)[:3] == ["Keys", "IDE", "Editor"], repr((opened, rc_read(a), tile_labels(h))))
    h.end()


def a_validate():
    a = "zzhm"
    fresh(a)
    h = H(a)
    turn_group(h)
    h.end()
    rc_write(a, "recent", ["on", "nosuch", "keys", "KEYS", "ide", "bad_id", "files", "files", "voc", "dict", "query", "bulk"])
    R("A9", "the record is written by hand: the program that wrote it is the evidence (on/nosuch/keys/KEYS/ide/bad id/files/files/voc/dict/query/bulk)",
      rc_read(a) == "on/nosuch/keys/KEYS/ide/bad id/files/files/voc/dict/query/bulk", repr(rc_read(a)))
    h = H(a)
    labs = tile_labels(h)
    R("A10", "a record edited by hand cannot make the page offer what it does not: the id the page has no tile for (nosuch), the capitals, the id with a blank and the second files are left out, and the six that count are the first six valid ids - the page shows Keys, IDE, Files, Vocabulary, Dictionary",
      is_top(h) and labs[:5] == ["Keys", "IDE", "Files", "Vocabulary", "Dictionary"] and labs[5] == "" and "Queries" not in h.line(10), repr(labs))
    h.end()


def a_off():
    a = "zzhm"
    fresh(a)
    h = H(a)
    turn_group(h)
    run_tile(h, "k")
    before = rc_read(a)
    turn_group(h)
    R("A_OFF", "choosing it again turns the group off (11959): the record is deleted - the list is forgotten - and the page has no Recent heading; the file &menus& stays",
      before == "on/keys" and "The Recent group is off" in h.line(40) and rc_read(a) == "norec" and heading_row(h, "Recent") is None and menus_dir(a) is not None, repr((before, h.line(40), rc_read(a))))
    run_tile(h, "k")
    R("A_OFFW", "NOTHING IS WRITTEN WHEN THE GROUP IS OFF: with the file there, starting Keys again leaves the record absent",
      rc_read(a) == "norec" and heading_row(h, "Recent") is None and is_top(h), repr((rc_read(a), h.line(40))))
    h.end()


def a_admin():
    a = "zzhm"
    fresh(a)
    h = H(a)
    turn_group(h)
    h.end()
    rc_write(a, "recent", ["on", "keys", "ide"])
    out = adm("set.tile %s recent off" % a)
    R("A_ADM", "the administrator turns the group off for the account with SET.TILE (recent is a standard id: no 'not a standard tile' note); the person's record is not touched",
      has(out, r"Tile recent is now off for zzhm") and not has(out, r"not a standard tile") and rc_read(a) == "on/keys/ide", repr((out[:3], rc_read(a))))
    h = H(a)
    R("A_ADM_GROUP", "...the account's page has no Recent group although the person's record says on and holds Keys and IDE", is_top(h) and heading_row(h, "Recent") is None and label_at(h, 10, 3) != "Keys", repr((tile_labels(h), rc_read(a))))
    view_menu(h)
    shown = "Recent group" in h.text()
    h.typed("g", idle=1.0)
    same = rc_read(a) == "on/keys/ide"
    h.key("esc", idle=0.6)
    R("A_ADM_MENU", "...and its View entry cannot be chosen: the letter does nothing and the record is as it was", shown and same and "Recent group is" not in h.line(40), repr((shown, rc_read(a), h.line(40))))
    run_tile(h, "i", wait=2.5)
    R("A_ADM_WRITE", "...starting a tile writes nothing: starting the IDE leaves the record on/keys/ide (the IDE is not first)", rc_read(a) == "on/keys/ide", repr(rc_read(a)))
    h.end()
    adm("set.tile %s recent on" % a)
    h = H(a)
    R("A_ADM_BACK", "turned on again by the administrator, the group is back with what the person had kept (Keys, IDE)", heading_row(h, "Recent") == 6 and tile_labels(h)[:2] == ["Keys", "IDE"], repr(tile_labels(h)))
    h.end()


def a_pins():
    a = "zzhm"
    fresh(a)
    h = H(a)
    turn_group(h)
    run_tile(h, "k")
    h.end()
    adm("modify.account %s pins-on" % a)
    rc_write(a, "home", ["Orders~~who.am.i~y"])
    h = H(a)
    h.typed("o", idle=0.45)
    h.key("enter", idle=2.0)
    shown = re.search(r"Account\s*:\s*zzhm", h.text()) is not None
    h.typed("\r", idle=2.0)
    R("A_PINS", "a program of the person's own (a pinned command) is not kept by the group: it runs, the page comes back, and the record is still on/keys", shown and is_top(h) and rc_read(a) == "on/keys", repr((shown, rc_read(a))))
    h.end()
    adm("modify.account %s pins-off" % a)


def a_nofile():
    a = "zzhg"
    fresh(a, edit="no")
    h = H(a)
    turn_group(h)
    st = h.line(40)
    rc = rc_read(a)
    on = "The Recent group is on" in st and rc == "on"
    say("    (informational: with the edit gates off, turning the group on %s)" % ("WORKED" if on else "was REFUSED, 11960"))
    h.end()
    # 26 Oct 26 (review of the home work): the failure path made to HAPPEN.  A plain file named &menus& stands where create.file would make the directory file, so the file cannot be made and the
    # page must say so (11960) and leave no record; the plain file is untouched.  (The row above passed whichever way the edit gates went, so it could not fail.)
    b = "zzhf"
    fresh(b)
    p = os.path.join(acct_dir(b), "&menus&")
    write_file(p, "planted\n")
    h = H(b)
    turn_group(h)
    st = h.line(40)
    rc = rc_read(b)
    h.end()
    kept = os.path.isfile(p) and read_file(p) == "planted\n"
    os.unlink(p)
    R("A_NOFILE", "the file &menus& cannot be made (a plain file of that name is in the account's directory): turning the group on says so (11960 'could not be turned on'), no record exists (the reader finds no file) and the plain file is untouched",
      "could not be turned on" in st and rc == "nofile" and kept, repr((st, rc, kept)))


def a_adminrec():
    """26 Oct 26 (review of the home work): the Recent group for the ADMINISTRATOR, whose top page is three groups side by side in one band: with the group on and one tile started the
    page grows by the Recent band and must stay whole - the heading on row 6, the started tile first, the page still the top page - and turning the group off puts it back."""
    sh.set_default("menu")                              # the administrator starts where the system default says; sandbox-home.py sets it the same way before its administrator rows
    h = H(admin=True)
    page0 = [l[:70] for l in h.lines()[:14]]            # kept for the detail of a failure: what the administrator's top page looked like before anything was done
    turn_group(h)
    st_on = h.line(40)
    first = focus_label(h)
    h.key("enter", idle=2.5)
    h.typed("\x11", idle=1.8)
    top = is_top(h)
    hr = heading_row(h, "Recent")
    lab = label_at(h, 10, 3)
    turn_group(h)
    st_off = h.line(40)
    gone = heading_row(h, "Recent") is None and is_top(h)
    h.end()
    R("A_ADMREC", "as SDSYS: the group turns on (11958), the tile started (the one in focus: %s) comes back as the first Recent tile under a Recent heading on row 6, the page is still the top page, and turning the group off (11959) takes the heading away" % first,
      "The Recent group is on" in st_on and bool(first) and top and hr == 6 and lab == first and "The Recent group is off" in st_off and gone, repr((st_on, first, top, hr, lab, st_off, gone, page0)))


# ------------------------------------------------------------------------------------------------------------------------------- the mutants: name -> (section, [(program, old, new)], the rows that must fail)

SWITCH_RESET = r"re:   cur\.menu = ''[ ]+;\* the screen of the new account starts at its top page\n   stk = ''\n   crumb = ''\n"
MUTANTS = {
    "recent-writes-when-off": ("a_off", [("tool_home", "   if not(rc.on) then return\n   rid = tl<fi, HT.ID>", "   rid = tl<fi, HT.ID>"),
                                          ("home_recent", "   if not(got) or rec<1> # 'on' then\n      release f, 'recent'\n      close f\n      return\n   end\n", "")], ["A_OFFW"]),
    "admin-off-ignored": ("a_admin", [("tool_home", "   if index(off.set, ' recent ', 1) then return\n   call !home_recent('get', rc.on, rc.ids)", "   call !home_recent('get', rc.on, rc.ids)")],
                         ["A_ADM_BACK", "A_ADM_GROUP", "A_ADM_WRITE"]),      # A_ADM_BACK reads the record the mutant's write (A_ADM_WRITE) has changed: three rows about one fault
    "esc-ignored": ("c_sub", [("tool_home", "      case nm = 'esc' or nm = 'bs'\n", "      case nm = 'esc-ignored'\n")], ["C_ESC", "C_FOCUS", "C_BS", "C_UNWIND"]),
    "depth-unlimited": ("c_sub", [("tool_home", "$define HM.DEPTH   8 ", "$define HM.DEPTH   99")], ["C_DEPTH", "C_UNWIND"]),
    "cycle-allowed": ("c_sub", [("tool_home", "   already = (mname = cur.menu or mname = '')\n", "   already = 0\n")], ["C_CYCLE"]),
    "back-forgets-focus": ("c_sub", [("tool_home", "   want.id = e<1, 2>\n", "   want.id = ''\n")], ["C_FOCUS", "C_BS", "C_UNWIND"]),
    "switch-keeps-level": ("c_sub", [("tool_home", SWITCH_RESET, "")], ["C_SWITCH"]),
    "create-start-unchecked": ("b_create", [("create_account", "   if start.want # '' and start.want # 'menu' and start.want # 'terminal' then\n", "   if @false then\n")], ["B_BOGUS"]),
}
SECTIONS = {"c_sub": c_sub, "d_ids": d_ids, "b_create": b_create, "a_basic": a_basic, "a_validate": a_validate, "a_off": a_off, "a_admin": a_admin, "a_pins": a_pins, "a_nofile": a_nofile, "a_adminrec": a_adminrec}
PROGRAMS = ("tool_home", "home_recent", "create_account")


def mutate(name):
    """One mutant: the change in the sandbox's own copy, the section run, the copy put back.  Returns (the ids that failed, the ids that had to)."""
    global MUT
    section, edits, expect = MUTANTS[name]
    progs = sorted({e[0] for e in edits})
    for prog, old, new in edits:
        patch(prog, old, new)
    compile_programs(*progs)
    RES.clear()
    MUT = True
    say("sandbox-home2: MUTANT %s: the rows that must fail, and nothing else: %s" % (name, ", ".join(expect)))
    try:
        SECTIONS[section]()
    finally:
        MUT = False
        restore(*progs)
    return sorted(k for k, v in RES.items() if not v), sorted(expect)


def main():
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), "")
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant != "all" and mutant not in MUTANTS:
        bail("usage: sandbox-home2.py <dir> [--build] [--only=C,D,B,A] [--mutant=%s|all]" % "|".join(sorted(MUTANTS)))
    try:
        sh.setup("sandbox-home2.py")
        setup_programs()
        restore(*PROGRAMS)
        if mutant is not None:
            todo = sorted(MUTANTS) if mutant == "all" else [mutant]
            bad = 0
            for m in todo:
                failed, expect = mutate(m)
                ok = failed == expect
                bad += 0 if ok else 1
                say("sandbox-home2: MUTANT %s: rows that failed %s, rows that had to %s -> %s" % (m, failed, expect, "KILLED by exactly its rows" if ok else "NOT as required"))
            say("\nsandbox-home2: %d mutants, %d not killed by exactly their own rows" % (len(todo), bad))
            sh.teardown()
            sys.exit(1 if bad else 0)
        want = only.split(",") if only else ["C", "D", "B", "A"]
        if "C" in want:
            say("\n--- C  sub-menus (on the sandbox's copy of tool_home with a folder declared)")
            c_sub()
        if "D" in want:
            say("\n--- D  the standard tile ids")
            d_ids()
        if "B" in want:
            say("\n--- B  create.account's start-menu, start-terminal and pins-on (an OTHER account; sudo is a stand-in)")
            b_create()
        if "A" in want:
            say("\n--- A  the Recent group")
            for fn in (a_basic, a_validate, a_off, a_admin, a_pins, a_nofile, a_adminrec):
                fn()
    except BaseException as e:
        if isinstance(e, SystemExit) and e.code in (0, 1):
            raise                   # the end of a run that ran (the sandbox is stopped; the programs were put back by the section that changed them)
        if sh.SYS and os.path.isdir(sh.SYS) and os.path.exists(sb_gpl("tool_home")):
            try:
                restore(*PROGRAMS)
            except SystemExit:
                pass
        raise
    sh.teardown()
    sh.summary("sandbox-home2")


if __name__ == "__main__":
    main()
