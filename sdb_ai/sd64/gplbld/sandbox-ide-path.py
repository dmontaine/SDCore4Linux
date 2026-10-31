#!/usr/bin/env python3
#
# sandbox-ide-path.py - operating system files in the IDE (the editor merge's stage E; ~/Documents/Audits/TUI/Opus_TUI_Plan.txt section 11).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-path.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every
# row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 28 Oct 26 dm  New with stage E.  WRITTEN, NOT RUN (the owner's rule for the full-screen phases: one complete run at the end).  The free check that holds the same properties
#               as text is test-idepath-units.py.  EXPECT FIRST-RUN FAULTS IN THE SUITE: the keys that answer the overwrite question (Left, Return), the exact words of a box, and
#               whether a refused open leaves the editor focused are guesses from the other IDE suites.
# 29 Oct 26 dm  Row C6 (review R8): Write a copy is File's fifth entry (DOWN * 4, as sandbox-ide-kinds.py NA7); DOWN * 7 wrapped round to New record, and the row passed on the word "copy".
# 30 Oct 26 dm  S.88 stage E2 (a file of the operating system is MADE by New, Save as, the first save of an untitled buffer, Write a copy and Export; the tree has an
#               'Operating system files' node; Import takes path:/full/name): sections S1 (the scratch directory, the records and the probes), M (make), X (the kernel's
#               exclusive create seen through the IDE), T (the tree's node) and I (import), and rows G5 to G10 in G.  WRITTEN, NOT RUN: EXPECT FIRST-RUN FAULTS IN THE SUITE -
#               the number of Down presses to a menu entry (File: Save as 3, Write a copy 4; Search: Import 7, Export 8, as sandbox-ide-edit.py), the words of a message on the
#               status line, whether the focus is in the editor after a form closes, the cursor row the tree helper reads, and a tab's label for a path (`os name`, as O1).
#               The kernel's half of the exclusive create is sandbox-oq2.py rows 485b-d; the free check is test-idepath-units.py.
# END-HISTORY
#
# WHAT RUNS.  The IDE on a PSEUDO-TERMINAL at 140 by 43 (sandbox-ide.py's Ide) in the sandbox user's own account, opening FILES OF THE OPERATING SYSTEM (`ide path:/full/name`)
# that this script writes beforehand from Python.  EVERY VERDICT IS READ FROM THE DISK BY PYTHON (the bytes of the file, and its inode, mode, owner and link count before and
# after), never from what the IDE said.  The gate rows (section G) come LAST: they need sandbox-gates.py's prepare(), which makes the sandbox user an ordinary user, and
# build ordinary fixture accounts with the OS gate off and on.
#
#   S0   setup and controls: the fixture files were written and read back exactly; the sentinel outside the account is there
#   O    open, edit, save: LF; CR LF (kept); no final newline (none added); a CR in a LF file (kept as data); a tab; an empty file; a cut that shortens the file (no tail left); inode,
#        mode, owner and link count unchanged by a save, and a hard link sees the new bytes
#   R    refused: NUL; bytes 254 and 255; over 2 MB; a directory; a FIFO (and the IDE is not hung); a file that is not there; a relative path; a .. component; bytes 128 to 247
#        (opens read-only, nothing changes); a file mode 0444 (opens read-only, nothing changes)
#   L    a second session cannot open a file the first holds; after the first closes it can
#   C    the file changed on disk between the open and the save: the overwrite question (Cancel is the default; Cancel leaves the other bytes; Overwrite writes ours); a
#        same-size change in place (C4, the reviewer's finding 2b); a file renamed over the one the tab holds (C5, finding 2a); Write a copy is there as the way out (C6)
#   N    what does not apply: Ctrl-E (SED) and F8 (compile) on such a tab say so and change nothing; no recovery copy was written for it
#   S1   (30 Oct 26) the scratch directory /tmp/zs<run> (a fifo, a socket, a directory with a control character in its name, a dangling link ...), a data file of records and
#        the probe programs; the null case: the suite stops, exit 2, when a fixture is not what it must be
#   M    make: New with path:<name> makes an EMPTY file and opens it; Save as of a record writes the text, gives the lock back and turns the tab into a path tab (a later
#        Ctrl-S writes in place); the first save of an untitled buffer; Write a copy and Export keep no tab and no lock; the mode is 0666 minus the umask (two umasks, and a
#        plain OPENSEQ CREATING as the control); a name that exists with content, a dangling link, a missing directory, a directory, a FIFO, a record with value marks, a file
#        open in another tab: each is refused with the disk as it was and the tab, the record and its lock as they were; an existing EMPTY file is filled
#   X    the exclusive create through the IDE's other makers (Write a copy, Export, the first save of an untitled buffer) onto a dangling link and a file with content
#   T    the tree's 'Operating system files' node: Return lists '/', directories first and sorted, a FIFO / socket / control-character name not listed (and counted), Return
#        again closes everything under it, a file node opens a tab, a file made in a listed directory appears
#   I    import: path:<file> not open anywhere (text inserted, no lock left), a file a tab holds (the tab's unsaved text), a NUL, bytes 128 to 247, a directory
#   G    an ordinary account: OS gate off - a file inside the account opens and saves, a file outside it and a link that leads out are refused (the bytes untouched);
#        OS gate on - the outside file opens and saves; (30 Oct 26, G5-G10) the name form refuses an outside name and stays open, no OS node in the tree, a file made inside
#        the account, an os-on account makes an outside file and lists '/', an edit-gated place (below a program file the account may not change) is refused, Import of an
#        outside file is refused

import importlib.util
import os
import re
import shutil
import socket
import stat
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


sb = _load("sandbox_ide_for_path", "sandbox-ide.py")                     # Ide (the pty driver) and the key names
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = "%05d" % (os.getpid() % 100000)
F10, RIGHT, LEFT, DOWN, RET, ESC = sb.F10, sb.RIGHT, sb.LEFT, sb.DOWN, sb.RET, sb.ESC
CTRL_Q, CTRL_S, CTRL_W = sb.CTRL_Q, sb.CTRL_S, sb.CTRL_W
CTRL_K, CTRL_E, F8 = "\x0b", "\x05", "\x1b[19~"
TAB, CTRL_U, CTRL_N, CTRL_O, UP, END, ALT_PGUP = sb.TAB, sb.CTRL_U, sb.CTRL_N, sb.CTRL_O, sb.UP, sb.END, sb.ALT_PGUP
CTRL_G = "\x07"                                                  # sets the mark in the editor (sandbox-ide-edit.py)
GOTO_TREE = sb.GOTO_TREE
passed = failed = 0
BOX = SYSD = ACC = None
LIVES = []


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
    say("sandbox-ide-path: CANNOT RUN - " + msg)
    teardown()
    sys.exit(2)


# the files: name -> (bytes, mode).  All are in the account directory (the pty's working directory), which is ACC; OUT is outside it, in the box.
FILES = {
    "lf": (b"alpha\nbeta\ngamma\n", 0o640),
    "crlf": (b"one\r\ntwo\r\n", 0o640),
    "nofinal": (b"x\ny", 0o640),
    "mixed": (b"a\r\nb\nc\r\n", 0o640),
    "tab": (b"a\tb\n", 0o640),
    "empty": (b"", 0o640),
    "nul": (b"ab\x00cd\n", 0o640),
    "marks": (b"ab\xfe\xffcd\n", 0o640),
    "high": (b"caf\xc3\xa9\n", 0o640),
    "ro": (b"read only\n", 0o444),
    "big": (b"x" * 2097153, 0o640),
    "cut": (b"alpha\nbeta\ngamma\n", 0o640),
    "chg": (b"first\nsecond\n", 0o640),
    "ren": (b"one\ntwo\n", 0o640),
    "same": (b"abcd\n", 0o640),
    "lock": (b"held\n", 0o640),
}


# The IDE's status line is the tab's name, the position and then the message, in 140 columns, and the messages of rows O2 and N1 repeat the file's full path: under the
#   regression's directory (/tmp/sdregress.XXXXXX/sbx-ide-path/user_accounts/...) the words the rows look for are cut off the right edge.  Those fixtures (SHORT_KEYS)
#   therefore live in a short directory of their own, which the sandbox user (the administrator, in SDSYS) may open, and which teardown() removes.
SHORT = "/tmp/zq%s" % RUN
SHORT_KEYS = ("crlf", "tab")


def fpath(key):
    if key in SHORT_KEYS:
        return os.path.join(SHORT, "%s.txt" % key)
    return os.path.join(ACC, "zzp%s-%s.txt" % (RUN, key))


def rd(p):
    """the bytes of a plain file; None for anything else (a read of a FIFO with no writer would wait for ever) or a file that is not there"""
    try:
        if not stat.S_ISREG(os.stat(p).st_mode):
            return None
        with open(p, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def ident(p):
    try:
        s = os.stat(p)
    except OSError:
        return None
    return (s.st_ino, stat.S_IMODE(s.st_mode), s.st_uid, s.st_nlink)


def make_files():
    os.makedirs(SHORT, exist_ok=True)
    for key, (data, mode) in FILES.items():
        p = fpath(key)
        if os.path.exists(p):
            os.chmod(p, 0o644)
            os.remove(p)
        with open(p, "wb") as fh:
            fh.write(data)
        os.chmod(p, mode)
    twin = fpath("lf") + ".twin"
    if os.path.exists(twin):
        os.remove(twin)
    os.link(fpath("lf"), twin)                                   # a second name for the same file: a save must keep both
    d = os.path.join(ACC, "zzp%s-dir" % RUN)
    os.makedirs(d, exist_ok=True)
    fifo = os.path.join(ACC, "zzp%s-fifo" % RUN)
    if os.path.exists(fifo):
        os.remove(fifo)
    os.mkfifo(fifo)
    out = os.path.join(BOX, "zzp%s-out.txt" % RUN)
    with open(out, "wb") as fh:
        fh.write(b"outside\n")


def tab_row(e):
    L = e.lines()
    return L[2] if len(L) > 2 else ""


def editor_text(e):
    return "\n".join(l[28:] for l in e.lines()[3:39])


def in_ide(e):
    return not e.s.exited and "IDE: " in "\n".join(e.lines()[:3])


def says(e, *words):
    """(hit, status line): one of the words is on the status line or in a refusal box.  Since 30 Oct 26 (S.88 9g) the long refusals 11737, 11739 and 11762 are in a box, which stays up until a
    key closes it, so a box is closed here with Return and the next step starts clean."""
    st, t = e.status(), e.text()
    hit = any(w in st or w in t for w in words)
    if "[ OK ]" in t:                                                 # the box has its button on the screen; the status line may still hold the last case's message, so it cannot tell
        hit = any(w in t for w in words)
        e.keys(RET)
        e.quiet()
    return hit, st


def done(e):
    """Leave the IDE the way a person does (Ctrl-Q, Discard to every question), so that it gives its locks back, then log off"""
    if in_ide(e):
        e.keys(CTRL_Q)
        n = 0
        while "has changes" in e.text() and n < 6:
            e.keys(DOWN, RET)
            n += 1
        time.sleep(0.5)
    e.end()


def open_edit_save(key, typed="ZZ", cmd_path=None):
    """open the file in the IDE, type, Ctrl-S; returns (Ide, status after the open, status after the save)"""
    e = sb.Ide(BOX, "IDE path:%s" % (cmd_path or fpath(key)))
    e.quiet()
    st1 = e.status()
    e.keys(typed)
    e.keys(CTRL_S)
    e.quiet()
    return e, st1, e.status()


# ---- S0 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_setup():
    say("\n--- S0: the fixture files and the instruments' controls ---------------------------------------------------------------")
    make_files()
    bad = {k: rd(fpath(k)) for k, (d, m) in FILES.items() if rd(fpath(k)) != d}
    row("S0 control: every fixture file reads back exactly as written (a probe that reads nothing would pass every later row)", not bad, repr(list(bad)))
    row("S0 control: the hard link shares the inode (so 'a save keeps the link' below means something)", ident(fpath("lf"))[0] == ident(fpath("lf") + ".twin")[0]
        and ident(fpath("lf"))[3] == 2, repr((ident(fpath("lf")), ident(fpath("lf") + ".twin"))))
    out = os.path.join(BOX, "zzp%s-out.txt" % RUN)
    row("S0 control: the outside file is outside the account directory and holds its sentinel text", not out.startswith(ACC + os.sep) and rd(out) == b"outside\n", repr((out, rd(out))))


# ---- O ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_open_save():
    say("\n--- O: open, edit, save ---------------------------------------------------------------------------------------------------------")
    before = ident(fpath("lf"))
    e, st1, st2 = open_edit_save("lf")
    row("O1 `ide path:<file>` opens it: the tab says os <name>, the status line names the path, the editor shows the three lines", ("os " + os.path.basename(fpath("lf"))) in tab_row(e)
        and fpath("lf") in st1 and "alpha" in editor_text(e) and "gamma" in editor_text(e), "%r | %r" % (tab_row(e)[:90], st1[:140]))
    row("O1b typed ZZ and Ctrl-S: the disk holds ZZalpha, beta, gamma, each line end and the final one kept; the status line says Saved", rd(fpath("lf")) == b"ZZalpha\nbeta\ngamma\n"
        and "Saved" in st2, repr((rd(fpath("lf")), st2[:120])))
    row("O1c the SAME file was written: inode, mode, owner and link count are as before, and the hard link name sees the new bytes",
        ident(fpath("lf")) == before and rd(fpath("lf") + ".twin") == b"ZZalpha\nbeta\ngamma\n", repr((before, ident(fpath("lf")))))
    done(e)

    e, st1, st2 = open_edit_save("crlf")
    row("O2 a CR LF file: opened with the message that every line ends CR LF; saved, its line ends are still CR LF", "CR LF" in st1 and rd(fpath("crlf")) == b"ZZone\r\ntwo\r\n", repr((st1[:100], rd(fpath("crlf")))))
    done(e)
    e, st1, st2 = open_edit_save("nofinal")
    row("O3 a file without a final newline gets none added", rd(fpath("nofinal")) == b"ZZx\ny", repr(rd(fpath("nofinal"))))
    done(e)
    e, st1, st2 = open_edit_save("mixed")
    row("O4 a file where only SOME lines end CR LF is not taken as CR LF: the CRs stay in the lines and come back byte for byte", rd(fpath("mixed")) == b"ZZa\r\nb\nc\r\n", repr(rd(fpath("mixed"))))
    done(e)
    e, st1, st2 = open_edit_save("tab")
    row("O5 a tab character is kept as a tab", rd(fpath("tab")) == b"ZZa\tb\n", repr(rd(fpath("tab"))))
    done(e)
    e, st1, st2 = open_edit_save("empty", typed="hi")
    row("O6 an empty file opens, takes text, and is written with no newline added", rd(fpath("empty")) == b"hi", repr(rd(fpath("empty"))))
    done(e)
    e = sb.Ide(BOX, "IDE path:%s" % fpath("cut"))
    e.quiet()
    e.keys(CTRL_K, CTRL_K)                                           # the whole-line cut, twice: alpha and beta go
    e.keys(CTRL_S)
    e.quiet()
    row("O7 a save that makes the file SHORTER leaves no tail of the old text behind", rd(fpath("cut")) == b"gamma\n", repr(rd(fpath("cut"))))
    done(e)


# ---- R ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def refused(key, words, label, path=None):
    p = path or fpath(key)
    before = rd(p)
    e = sb.Ide(BOX, "IDE path:%s" % p)
    e.quiet()
    st = e.status()
    row("%s is refused: the status line says %r, no os tab is made, the IDE is still up and the file is as it was" % (label, words),
        words in st and "os " + os.path.basename(p) not in tab_row(e) and in_ide(e) and rd(p) == before, "%r | %r" % (st[:160], tab_row(e)[:80]))
    done(e)


def section_refused():
    say("\n--- R: refused, and read-only -----------------------------------------------------------------------------------------------")
    refused("nul", "NUL byte", "R1 a file with a NUL")
    refused("marks", "NUL byte", "R2 a file with the bytes 254 and 255")
    refused("big", "larger than 2 MB", "R3 a file of 2 MB and one byte")
    refused(None, "not a plain file", "R4 a directory", path=os.path.join(ACC, "zzp%s-dir" % RUN))
    refused(None, "not a plain file", "R5 a FIFO (and the IDE is not hung: it answered within the quiet second)", path=os.path.join(ACC, "zzp%s-fifo" % RUN))
    refused(None, "There is no operating system file", "R6 a name with no file", path=os.path.join(ACC, "zzp%s-absent.txt" % RUN))
    e = sb.Ide(BOX, "IDE path:zzp%s-lf.txt" % RUN)
    e.quiet()
    row("R7 a relative path is refused (the full path is the rule)", "full path" in e.status(), e.status()[:160])
    done(e)
    e = sb.Ide(BOX, "IDE path:%s/zzp%s-dir/../zzp%s-chg.txt" % (ACC, RUN, RUN))
    e.quiet()
    row("R8 a path with a .. component is refused", "full path" in e.status() and "os " not in tab_row(e), e.status()[:160])
    done(e)

    before = rd(fpath("high"))
    e = sb.Ide(BOX, "IDE path:%s" % fpath("high"))
    e.quiet()
    st = e.status()
    e.keys("ZZ")
    e.keys(CTRL_S)
    e.quiet()
    row("R9 a file holding bytes 128 to 247 opens READ-ONLY: the status line says so, typing changes nothing, Ctrl-S is refused in a box, the disk keeps every byte",
        "read-only" in st and rd(fpath("high")) == before and "ZZ" not in editor_text(e) and "outside ASCII" in e.text(), "%r | %r" % (st[:120], e.text()[-300:]))
    done(e)

    before = rd(fpath("ro"))
    e = sb.Ide(BOX, "IDE path:%s" % fpath("ro"))
    e.quiet()
    st = e.status()
    e.keys("ZZ")
    e.keys(CTRL_S)
    e.quiet()
    row("R10 a file the session may not write (mode 0444) opens READ-ONLY with the message, typing changes nothing and Ctrl-S is refused; the disk is as it was",
        "read-only" in st and rd(fpath("ro")) == before and "ZZ" not in editor_text(e), "%r | %r" % (st[:140], e.text()[-300:]))
    done(e)


# ---- L ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_lock():
    say("\n--- L: the file's SD lock ---------------------------------------------------------------------------------------------------")
    e1 = sb.Ide(BOX, "IDE path:%s" % fpath("lock"))
    e1.quiet()
    e2 = sb.Ide(BOX, "IDE path:%s" % fpath("lock"))
    e2.quiet()
    row("L1 while one session has the file open, a second cannot open it: 'in use by another session', no tab", "in use by another session" in e2.status() and "os " not in tab_row(e2), e2.status()[:160])
    done(e2)
    done(e1)
    e3 = sb.Ide(BOX, "IDE path:%s" % fpath("lock"))
    e3.quiet()
    row("L2 once the first session has closed it, the file opens (the lock went with the tab)", ("os " + os.path.basename(fpath("lock"))) in tab_row(e3), tab_row(e3)[:90])
    done(e3)


# ---- C ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_changed():
    say("\n--- C: the file changed on disk between the open and the save ----------------------------------------------------------------")
    e = sb.Ide(BOX, "IDE path:%s" % fpath("chg"))
    e.quiet()
    with open(fpath("chg"), "ab") as fh:
        fh.write(b"third\n")
    e.keys("ZZ")
    e.keys(CTRL_S)
    box = e.text()
    row("C1 saving a file that changed on disk asks the overwrite question (Overwrite, Cancel)", "changed by someone else" in box and "Overwrite" in box and "Cancel" in box, box[-300:])
    e.keys(RET)                                                      # Cancel is the default
    row("C2 Cancel (the default) leaves the other writer's bytes on the disk", rd(fpath("chg")) == b"first\nsecond\nthird\n", repr(rd(fpath("chg"))))
    e.keys(CTRL_S)
    e.keys(LEFT, RET)                                                # Overwrite
    e.quiet()
    row("C3 Overwrite writes our text over it, whole", rd(fpath("chg")) == b"ZZfirst\nsecond\n", repr(rd(fpath("chg"))))
    done(e)

    # review of 28 Oct 26, finding 2b: a change of the SAME SIZE, written in place by another program (same inode), in a file small enough for one block buffer - the second look used to
    #   read the buffer and see the old text
    e = sb.Ide(BOX, "IDE path:%s" % fpath("same"))
    e.quiet()
    with open(fpath("same"), "r+b") as fh:
        fh.write(b"wxyz\n")
    e.keys("ZZ")
    e.keys(CTRL_S)
    box = e.text()
    row("C4 a same-size change made in place by another program is seen (the overwrite question), where the buffer once hid it", "changed by someone else" in box, box[-300:])
    e.keys(RET)
    row("C4b Cancel leaves the other program's bytes", rd(fpath("same")) == b"wxyz\n", repr(rd(fpath("same"))))
    done(e)

    # finding 2a: another program writes a new file and renames it over this one (vim, sed -i, git): the tab holds the old, unlinked inode
    e = sb.Ide(BOX, "IDE path:%s" % fpath("ren"))
    e.quiet()
    new = fpath("ren") + ".new"
    with open(new, "wb") as fh:
        fh.write(b"replaced\n")
    os.replace(new, fpath("ren"))
    e.keys("ZZ")
    e.keys(CTRL_S)
    box = e.text()
    row("C5 a file renamed over the one the tab holds is refused ('renamed over it'), not saved into the old inode", "renamed over it" in box and rd(fpath("ren")) == b"replaced\n", "%r | %r" % (box[-300:], rd(fpath("ren"))))
    e.keys(RET)
    e.keys(F10, DOWN * 4, RET)                                          # File / Write a copy: the fifth entry (DOWN * 7 wrapped round the seven entries to New record: review R8, 29 Oct 26; sandbox-ide-kinds.py NA7 uses DOWN * 4)
    t6 = e.text()
    row("C6 Write a copy is offered for such a tab (the way out): the name form opens (its own words, not the word 'copy' anywhere on the screen)", "Name of the" in t6 or "File:" in t6, t6[-300:])
    e.keys(ESC)
    done(e)


# ---- N ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_notfor():
    say("\n--- N: what does not apply to such a tab ---------------------------------------------------------------------------------")
    rcdir = os.path.expanduser("~/.local/state/sd")
    before = sorted(os.listdir(rcdir)) if os.path.isdir(rcdir) else None
    e = sb.Ide(BOX, "IDE path:%s" % fpath("tab"))
    e.quiet()
    e.keys("Q")
    e.keys(CTRL_E)
    e.quiet()
    hit, st = says(e, "operating system file")                      # a box since 30 Oct 26 (9g)
    row("N1 Ctrl-E (SED) says it is an operating system file and the IDE stays up with the tab", hit and in_ide(e), st[:160])
    e.keys(F8)
    e.quiet()
    hit, st = says(e, "operating system file")
    row("N2 F8 (compile) says the same and does not save the text", hit and rd(fpath("tab")) == b"ZZa\tb\n", repr((st[:100], rd(fpath("tab")))))
    time.sleep(2.5)
    after = sorted(os.listdir(rcdir)) if os.path.isdir(rcdir) else None
    row("N3 no recovery copy was written for the changed tab (the store in the home is as it was)", before == after, repr((before, after)))
    done(e)


# ---- the scratch directory, the records, the probes and the helpers of sections S1 to I (30 Oct 26, stage E2) -------------------------------------------------------------
# The scratch directory is under /dev/shm when that is a writable directory (/tmp otherwise): the TREE rows reach it by opening '/', then each directory above it, and a listing
#   keeps at most 1000 entries in the order DIR() gives them, so a parent with hundreds of entries (a busy /tmp) could drop it.  S1 stops the suite when the parent holds more than 900.
SHM = "/dev/shm" if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK) else "/tmp"
SCR = "%s/zs%s" % (SHM, RUN)
DF = "zzpf" + RUN                      # a data file of records, made by the fixture
UID = os.getuid()
SCR_MADE = False

FIX ="""   execute 'CREATE.FILE %(df)s' capturing j
   open '%(df)s' to d else stop 'PFIX no data file'
   write 'alpha':@fm:'beta':@fm:'gamma' on d, 'rec1'
   write 'two-a':@fm:'two-b' on d, 'rec2'
   write 'three-a':@fm:'three-b' on d, 'rec3'
   write 'four-a':@fm:'four-b' on d, 'rec4'
   write 'five-a':@fm:'five-b' on d, 'rec5'
   write 'six-a':@fm:'six-b' on d, 'rec6'
   write 'Don':@vm:'Henry':@fm:'x' on d, 'recmark'
   crt 'PFIX done'
end
"""
PROBE = """   open '%(df)s' to d else stop 'PPROBE no data file'
   ids = 'rec1':@fm:'rec2':@fm:'rec3':@fm:'rec4':@fm:'rec5':@fm:'rec6':@fm:'recmark'
   for i = 1 to 7
      read r from d, ids<i> then crt 'PREC ':ids<i>:' [':convert(@fm:@vm:@sm, '^|~', r):']' else crt 'PREC ':ids<i>:' <absent>'
   next i
   crt 'PPROBE END'
end
"""
# another session asks for the lock of a record of the data file: LOCKED and the holder, or GOT (and lets it go at once)
LOCKP = """   id = field(@sentence, ' ', 4)
   open '%(df)s' to d else stop 'PLK no data file'
   readu x from d, id locked
      crt 'PLK LOCKED ':status()
      stop
   end then null else null
   crt 'PLK GOT'
   release d, id
end
"""
# another session asks for the SD lock of an operating system file by OPENSEQ (the clauses end the statement: the LOCKED flag is tested after it, as !ide_osfile does)
OSP = """   id = field(@sentence, ' ', 4)
   lk = 0
   openseq id to f on error
      crt 'POS ERROR ':status()
      stop
   end locked
      lk = 1
   end then
      null
   end else
      crt 'POS ELSE ':status()
      stop
   end
   if lk then
      crt 'POS LOCKED'
   end else
      crt 'POS GOT'
      close f
   end
end
"""
# a plain OPENSEQ ... CREATING of a name: the file the kernel makes with no IDE in between (the control for the mode of a file the IDE makes)
MKP = """   id = field(@sentence, ' ', 4)
   openseq id creating to f on error
      crt 'PMK ERROR ':status()
      stop
   end then
      null
   end else
      crt 'PMK ELSE ':status()
      stop
   end
   close f
   crt 'PMK MADE'
end
"""
WANT_RECS = {"rec1": "[alpha^beta^gamma]", "rec2": "[two-a^two-b]", "rec3": "[three-a^three-b]", "rec4": "[four-a^four-b]", "rec5": "[five-a^five-b]", "rec6": "[six-a^six-b]",
             "recmark": "[Don|Henry^x]"}


def scr(*parts):
    return os.path.join(SCR, *parts)


def full_ident(p):
    """lstat of the NAME (a link is not followed): inode, mode, owner, links, size, modification time in ns; None when there is nothing there"""
    try:
        s = os.lstat(p)
    except OSError:
        return None
    return (s.st_ino, stat.S_IMODE(s.st_mode), s.st_uid, s.st_nlink, s.st_size, s.st_mtime_ns)


def put_file(p, data, mode=0o644):
    if os.path.lexists(p):
        os.remove(p)
    with open(p, "wb") as fh:
        fh.write(data)
    os.chmod(p, mode)


def with_umask(mask, fn):
    old = os.umask(mask)
    try:
        return fn()
    finally:
        os.umask(old)


def put_prog(name, text):
    with open(os.path.join(SYSD, "bp", name), "w") as fh:
        fh.write(text % {"df": DF})


def need(name, ok, detail=""):
    """a fixture row: when it fails the suite stops (exit 2) - what follows would judge nothing"""
    row(name, ok, detail)
    if not ok:
        bail("a fixture is not what it must be: " + name)


def recs():
    """every record of the data file as the disk has it, id -> '[text]' (^ for a field mark, | for a value mark)"""
    o = sb.sess(BOX, "RUN bp zzppr" + RUN)
    if "PPROBE END" not in o:
        say("    (the record probe did not reach its end: %r)" % o[-300:])
    return dict(re.findall(r"(?m)^PREC (\S+) (.*?)\s*$", o))


def rec_lock(rid):
    """'GOT' or 'LOCKED <user>' from ANOTHER session asking for the record's lock; 'NO ANSWER' when the probe said neither (a string, so that a row's startswith() fails the row and does not stop the suite)"""
    o = sb.sess(BOX, "RUN bp zzplk%s %s" % (RUN, rid))
    m = re.search(r"(?m)^PLK (GOT|LOCKED -?\d+)\s*$", o)
    return m.group(1) if m else "NO ANSWER"


def os_lock(path):
    """'GOT', 'LOCKED', 'ELSE n' or 'ERROR n' from ANOTHER session's OPENSEQ of the file; 'NO ANSWER' when the probe said none of them"""
    o = sb.sess(BOX, "RUN bp zzpos%s %s" % (RUN, path))
    m = re.search(r"(?m)^POS (GOT|LOCKED|ELSE -?\d+|ERROR -?\d+)\s*$", o)
    return m.group(1) if m else "NO ANSWER"


def mode_of(p):
    try:
        return stat.S_IMODE(os.lstat(p).st_mode)
    except OSError:
        return None


def ed_lines(e):
    """the editor's lines without the line numbers (the editor runs from column 29 to the scroll bar at 138)"""
    return [re.sub(r"^\s*\d+ ", "", l[29:138]).rstrip() for l in e.lines()[3:39]]


def name_to(e, path):
    """the name form is open and the focus is on its record entry: Tab to the file entry, clear it, type path:<path>, Return (the form takes path:/full/name in any mode)"""
    e.keys(TAB, CTRL_U, "path:" + path, RET)
    e.quiet()


def menu(e, n_right, n_down):
    """F10, Right n_right times (File is the first menu, Search the third), Down n_down times, Return"""
    e.keys(F10, RIGHT * n_right, DOWN * n_down, RET)
    e.quiet()


def do_new(e, path):
    e.keys(CTRL_N)
    name_to(e, path)


def do_saveas(e, path):
    e.keys(F10, DOWN * 3, RET)                                  # File: New record, Open record, Save, Save as
    name_to(e, path)


def do_copy(e, path):
    e.keys(F10, DOWN * 4, RET)                                  # ... Write a copy
    name_to(e, path)


def do_export(e, path):
    menu(e, 2, 8)                                               # Search: Find, Replace, List, Query replace, Find options, Upcase, Downcase, Import, Export
    name_to(e, path)


def export_sel(e, path):
    e.keys(CTRL_G)                                              # the mark at line 1 column 1 ...
    e.keys(RIGHT * 5)                                           # ... the cursor at column 6: "alpha" is selected
    do_export(e, path)


def do_import(e, path):
    menu(e, 2, 7)
    name_to(e, path)


# the tree's rows are 3 to 38, its first 28 columns; a node is a marker (+ or -, or a blank for a leaf) at column (depth - 1) * 2 and its label two columns on
def tree_lines(e):
    return [l[:27] for l in e.lines()[3:39]]                          # 30 Oct 26: not column 27, where a long listing draws the scroll bar (# | v ^) and a label would carry it


def label_of(seg):
    return re.sub(r"^[\s+\-|]+", "", seg).strip()                       # 30 Oct 26: column 0 of a row is the frame's border '|' at 140 by 43; the first run never matched a label


def tree_row_of(e, label):
    for i, seg in enumerate(tree_lines(e)):
        if label_of(seg) == label:
            return i + 3
    return None


def cur_label(e):
    r = e.s.screen.r
    if 3 <= r <= 38:
        return label_of(tree_lines(e)[r - 3])
    return None


TG_TRACE = []                                                    # (row of the label, row of the cursor) at each step of the last tree_goto: what a failed row shows


def tree_goto(e, label, tries=60):
    """Move the tree's cursor to the node with that label (the cursor is drawn on the current node): by the Up and Down keys when it is on the screen, by the node's first letter
    (the tree jumps to the next node that starts with it) and Page Down when it is not.  True when the cursor is on it"""
    TG_TRACE[:] = []
    for _ in range(tries):
        r = tree_row_of(e, label)
        cur = e.s.screen.r
        TG_TRACE.append((r, cur))
        if r is not None:
            if r == cur:
                return True
            e.keys((DOWN if r > cur else UP) * min(abs(r - cur), 10))
        else:
            e.keys(label[0])
            if tree_row_of(e, label) is None:
                e.keys(sb.HOME, label[0])                                # 30 Oct 26: the letter jump only looks DOWN the tree; a node above the view (the root, after a long listing) is reached from the top
                if tree_row_of(e, label) is None:
                    e.keys(sb.PGDN)
        e.quiet()
    return False


def tree_chain(e, labels):
    """go to each label in turn and press Return on it (open the directory, list it); False at the first that cannot be reached"""
    for lab in labels:
        if not tree_goto(e, lab):
            return False
        e.keys(RET)
        e.quiet()
    return True


# ---- S1 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_scratch():
    say("\n--- S1: the scratch directory, the records, the probes and their controls ----------------------------------------------------")
    parent = os.path.dirname(SCR)
    need("S1 control: the scratch directory's parent %s is not crowded (a listing keeps 1000 entries: fewer than 900 here)" % parent, len(os.listdir(parent)) < 900, str(len(os.listdir(parent))))
    if os.path.lexists(SCR):
        bail("%s is there already (left by a run with this number)" % SCR)
    os.makedirs(SCR)
    global SCR_MADE
    SCR_MADE = True                                              # teardown removes the scratch directory only when THIS run made it
    for d in (scr("prog.bp"), scr("t"), scr("t", "d1"), scr("t", "d2"), os.path.join(os.fsencode(SCR), b"t", b"dctl\x01x"), scr("i-dir")):
        os.makedirs(d)
    # the files are made in the REVERSE of their sorted order, so that a listing in the order of creation could not pass for a sorted one
    put_file(scr("t", "f3.txt"), b"f3\n")
    put_file(scr("t", "f2.txt"), b"f2\n")
    put_file(scr("t", "f1.txt"), b"f1 line one\nf1 line two\n")
    put_file(scr("t", "d1", "inner.txt"), b"inner\n")
    os.mkfifo(scr("t", "pfifo"))
    sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sk.bind(scr("t", "psock"))
    sk.close()
    put_file(scr("src1.txt"), b"s1\ns2\n")
    put_file(scr("i-a.txt"), b"imp-a\nimp-b\n")
    put_file(scr("i-held.txt"), b"x1\nx2\n")
    put_file(scr("i-nul.bin"), b"ab\x00cd\n")
    put_file(scr("i-high.txt"), "café\n".encode("utf-8"))
    names = sorted(os.listdir(scr("t")))
    need("S1 control: the tree fixture holds what the T rows expect (d1, d2, a name with a control character, f1 to f3, a FIFO and a socket) - on the disk",
         names == sorted(["d1", "d2", "dctl\x01x", "f1.txt", "f2.txt", "f3.txt", "pfifo", "psock"]) and stat.S_ISFIFO(os.lstat(scr("t", "pfifo")).st_mode)
         and stat.S_ISSOCK(os.lstat(scr("t", "psock")).st_mode), repr(names))
    for n, t in (("zzppf", FIX), ("zzppr", PROBE), ("zzplk", LOCKP), ("zzpos", OSP), ("zzpmk", MKP)):
        put_prog(n + RUN, t)
    o = sb.sess(BOX, "BASIC bp zzppf%s zzppr%s zzplk%s zzpos%s zzpmk%s" % ((RUN,) * 5), "RUN bp zzppf" + RUN)
    need("S1 setup: the fixture and the four probes compile and the fixture ran to its end", re.search(r"(?m)^Compiled 5 program\(s\) with no errors", o) is not None and "PFIX done" in o, o[-600:])
    d = recs()
    need("S1 control: the record probe reads every record as the fixture wrote it", d == WANT_RECS, repr(d))
    need("S1 control: the lock probe GETS a record nobody holds (so LOCKED below is a lock, not a broken probe)", rec_lock("rec1") == "GOT", repr(rec_lock("rec1")))
    need("S1 control: the file-lock probe GETS a file nobody holds", os_lock(scr("src1.txt")) == "GOT", repr(os_lock(scr("src1.txt"))))
    q = scr("ctl-made.txt")
    o = sb.sess(BOX, "RUN bp zzpmk%s %s" % (RUN, q))
    need("S1 control: the plain-CREATING probe makes an empty regular file (the mode control of M2)", "PMK MADE" in o and rd(q) == b"" and full_ident(q)[2] == UID, o[-300:])
    os.remove(q)


# ---- M ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def tab_unchanged(e, rid, base):
    """the tab is still the record's (and no operating system tab was made), the editor shows the same text, and another session is still refused the record's lock"""
    return ("[%s]" % rid) in tab_row(e) and "os " not in tab_row(e) and ed_lines(e) == base and rec_lock(rid).startswith("LOCKED")


def try_names(e, op, cases, who, rid=None, base=None):
    """Try each bad name in turn with op (do_saveas or do_new).  After each: the message says why; the disk is as it was; and, with a record open, the tab, the editor and the record's
    lock are as they were; without one, no operating system tab was made"""
    for label, path, anchor, check in cases:
        op(e, path)
        hit, st = says(e, anchor)
        row("%s onto %s is refused: the message says %r" % (who, label, anchor), hit, repr(st[:160]))
        row("%s ...%s: the disk is as it was" % (who, label), check(), "")
        if rid:
            row("%s ...%s: the tab is still the record's, the editor shows the same text and the record's lock is still held" % (who, label), tab_unchanged(e, rid, base),
                "%r | %r" % (tab_row(e)[:100], rec_lock(rid)))
        else:
            row("%s ...%s: no operating system tab was made" % (who, label), "os " + os.path.basename(path) not in tab_row(e), tab_row(e)[:100])


def section_make():
    say("\n--- M: New, Save as, the first save, Write a copy and Export make a file of the operating system ----------------------------")
    before = recs()

    # ---- M1 New -----------------------------------------------------------------------------------------------------------------------------------------------------------
    p = scr("new1.txt")
    e = sb.Ide(BOX, "IDE")
    e.quiet()
    do_new(e, p)
    i1 = full_ident(p)
    row("M1 New with path:<name> makes an EMPTY plain file (disk: size 0, one link, ours) and opens it in a tab of its own: the strip says os new1.txt",
        i1 is not None and i1[4] == 0 and i1[3] == 1 and i1[2] == UID and stat.S_ISREG(os.lstat(p).st_mode) and "os new1.txt" in tab_row(e), "%r | %r" % (i1, tab_row(e)[:100]))
    row("M1b the status line says it was saved and names the file", "Saved" in e.status() and p in e.status(), e.status()[:160])
    row("M1c the new tab holds the file's SD lock (another session is told LOCKED)", os_lock(p) == "LOCKED", repr(os_lock(p)))
    e.keys("hi")
    e.keys(CTRL_S)
    e.quiet()
    i2 = full_ident(p)
    row("M1d typed hi and Ctrl-S: the file holds hi (no line end added to an empty file), written in place: same inode, mode, owner and one link",
        rd(p) == b"hi" and i1 is not None and i2 is not None and i2[:4] == i1[:4], repr((rd(p), i1, i2)))
    done(e)
    row("M1e once the tab is closed the lock is gone", os_lock(p) == "GOT", repr(os_lock(p)))

    # ---- M2 the mode of a file the IDE makes -----------------------------------------------------------------------------------------------------------------------------
    cur = os.umask(0)
    os.umask(cur)
    for n, mask in enumerate([cur] if cur == 0o077 else [cur, 0o077]):
        p, q = scr("mode%d.txt" % n), scr("modectl%d.txt" % n)
        e = with_umask(mask, lambda: sb.Ide(BOX, "IDE"))        # the session inherits the umask it is started under
        e.quiet()
        do_new(e, p)
        o = with_umask(mask, lambda: sb.sess(BOX, "RUN bp zzpmk%s %s" % (RUN, q)))
        row("M2 (umask %03o): the file New made has the mode a plain OPENSEQ ... CREATING makes under the same umask (here %s)" % (mask, oct(mode_of(q)) if mode_of(q) is not None else None),
            mode_of(p) is not None and mode_of(p) == mode_of(q) and "PMK MADE" in o, repr((mode_of(p), mode_of(q), o[-200:])))
        # First run, 30 Oct 26: the expectation "0666 minus the shell's umask" was red (664 under 077): SD sets the umask of its own process (UMASK, per account), so the shell's is not what
        #   shapes the mode.  What holds under any umask: read and write for the owner, nothing beyond 0666 (no execute, no setuid, setgid or sticky bit); the exact mode is M2's comparison with a plain OPENSEQ.
        row("M2b (umask %03o): ...and it is a plain file mode: read and write for the owner, no execute and no special bit" % mask,
            mode_of(p) is not None and (mode_of(p) & 0o600) == 0o600 and (mode_of(p) & ~0o666) == 0, oct(mode_of(p)) if mode_of(p) is not None else "none")
        done(e)

    # ---- M3 Save as of a record ------------------------------------------------------------------------------------------------------------------------------------------
    p = scr("sa1.txt")
    e = sb.Ide(BOX, "IDE %s rec1" % DF)
    e.quiet()
    row("M3 CONTROL: the open record's tab holds its lock (another session is told LOCKED) and the editor shows the record",
        rec_lock("rec1").startswith("LOCKED") and "alpha" in ed_lines(e)[0], repr(ed_lines(e)[:3]))
    do_saveas(e, p)
    i1 = full_ident(p)
    row("M3a Save as to path:<name> writes exactly the text of the record: alpha, beta, gamma, LF line ends and a final line end; a plain file, one link, ours",
        rd(p) == b"alpha\nbeta\ngamma\n" and i1 is not None and i1[3] == 1 and i1[2] == UID and stat.S_ISREG(os.lstat(p).st_mode), "%r | %r" % (rd(p), i1))
    row("M3b ...the record on the disk is as it was", recs() == before, "")
    row("M3c ...the record's lock was given back (another session gets it) and the file's is held", rec_lock("rec1") == "GOT" and os_lock(p) == "LOCKED", "%r %r" % (rec_lock("rec1"), os_lock(p)))
    row("M3d ...the tab is now the file's: the strip says os sa1.txt and no longer [rec1]", "os sa1.txt" in tab_row(e) and "[rec1]" not in tab_row(e), tab_row(e)[:100])
    e.keys("ZZ")
    e.keys(CTRL_S)
    e.quiet()
    i2 = full_ident(p)
    row("M3e a later Ctrl-S writes the file in place: ZZ in front, same inode, mode, owner and links", rd(p) == b"ZZalpha\nbeta\ngamma\n" and i1 is not None and i2 is not None and i2[:4] == i1[:4], "%r | %r %r" % (rd(p), i1, i2))
    row("M3f ...and asks for no name (Ctrl-S on a path tab is a plain save)", "Name of the new record" not in e.text(), e.text()[-200:])
    done(e)

    # ---- M4 the first save of an untitled buffer -------------------------------------------------------------------------------------------------------------------------
    p = scr("untitled1.txt")
    e = sb.Ide(BOX, "IDE")
    e.quiet()
    e.keys("untitled text")
    e.keys(CTRL_S)
    row("M4 CONTROL: Ctrl-S on an untitled buffer asks for a name (the form)", "Name of the new record" in e.text(), e.text()[-200:])
    name_to(e, p)
    i1 = full_ident(p)
    row("M4a the file holds the buffer's text with a final line end, and the buffer is now a path tab (os untitled1.txt)",
        rd(p) == b"untitled text\n" and "os untitled1.txt" in tab_row(e), "%r | %r" % (rd(p), tab_row(e)[:100]))
    e.keys("Q")
    e.keys(CTRL_S)
    e.quiet()
    i2 = full_ident(p)
    # (First run, 30 Oct 26: the Q went where the cursor was, at the end of the line typed, and not in front - the cursor is kept across the conversion.)
    row("M4b a later Ctrl-S asks no name and writes in place: Q at the cursor (the end of the typed line), same inode", rd(p) == b"untitled textQ\n" and "Name of the new record" not in e.text() and i1 is not None and i2 is not None and i2[:4] == i1[:4],
        "%r | %r %r" % (rd(p), i1, i2))
    done(e)

    # ---- M5 Write a copy, M6 Export: no tab, no lock ---------------------------------------------------------------------------------------------------------------------
    p = scr("wc1.txt")
    e = sb.Ide(BOX, "IDE %s rec2" % DF)
    e.quiet()
    base = ed_lines(e)
    do_copy(e, p)
    row("M5a Write a copy to path:<name> writes the record's text (two-a, two-b, a final line end) to a new plain file", rd(p) == b"two-a\ntwo-b\n" and full_ident(p)[3] == 1, repr(rd(p)))
    row("M5b ...it keeps no tab (the strip is still [rec2], no os wc1.txt), the record's lock is still held, and the file's lock was given back",
        tab_unchanged(e, "rec2", base) and os_lock(p) == "GOT" and "os wc1.txt" not in tab_row(e), "%r | %r" % (tab_row(e)[:100], os_lock(p)))
    row("M5c ...and the record on the disk is as it was", recs() == before, "")
    done(e)
    p = scr("ex1.txt")
    e = sb.Ide(BOX, "IDE %s rec1" % DF)
    e.quiet()
    base = ed_lines(e)
    export_sel(e, p)
    row("M6a Export of the selection (alpha) to path:<name> writes alpha and a final line end to a new file", rd(p) == b"alpha\n" and full_ident(p)[3] == 1, repr(rd(p)))
    row("M6b ...no tab, no file lock, the record's tab and lock as they were", tab_unchanged(e, "rec1", base) and os_lock(p) == "GOT", "%r | %r" % (tab_row(e)[:100], os_lock(p)))
    done(e)
    src = scr("src1.txt")
    p = scr("wc2.txt")
    e = sb.Ide(BOX, "IDE path:%s" % src)
    e.quiet()
    do_copy(e, p)
    row("M7 Write a copy of a PATH tab to another path: the new file holds s1, s2 and a final line end, the source file is as it was, the tab is still the source's",
        rd(p) == b"s1\ns2\n" and rd(src) == b"s1\ns2\n" and "os src1.txt" in tab_row(e) and "os wc2.txt" not in tab_row(e) and os_lock(p) == "GOT", "%r | %r | %r" % (rd(p), rd(src), tab_row(e)[:100]))
    done(e)

    # ---- M8 a bad name is refused, and nothing else changes --------------------------------------------------------------------------------------------------------------
    full = scr("full.txt")
    put_file(full, b"keep\n", 0o640)
    dang, dang_t = scr("dang.lnk"), scr("dang.tgt")
    os.symlink(dang_t, dang)
    nopar = scr("nodir", "x.txt")
    isdir, fifo = scr("isdir"), scr("isfifo")
    os.makedirs(isdir)
    os.mkfifo(fifo)
    empty_b = scr("empty-b.txt")
    put_file(empty_b, b"", 0o600)
    st_full, st_dang, st_fifo, st_empty = full_ident(full), full_ident(dang), full_ident(fifo), full_ident(empty_b)
    need("M8 control: the refusal fixtures are what they must be (a file with content, a link to nothing, a FIFO, an empty file, no 'nodir')",
         rd(full) == b"keep\n" and os.path.islink(dang) and not os.path.lexists(dang_t) and stat.S_ISFIFO(os.lstat(fifo).st_mode) and rd(empty_b) == b"" and not os.path.lexists(scr("nodir")),
         repr((st_full, st_dang)))
    cases = [
        ("a file with content", full, "there already", lambda: full_ident(full) == st_full and rd(full) == b"keep\n"),
        ("a link to nothing (the target must not be made)", dang, "there already", lambda: not os.path.lexists(dang_t) and full_ident(dang) == st_dang and os.readlink(dang) == dang_t),
        ("a directory that is not there (it must not be made)", nopar, "directory is not there", lambda: not os.path.lexists(scr("nodir"))),
        ("a directory", isdir, "not a plain file", lambda: os.path.isdir(isdir) and not os.path.islink(isdir) and os.listdir(isdir) == []),
        ("a FIFO", fifo, "not a plain file", lambda: full_ident(fifo) == st_fifo and stat.S_ISFIFO(os.lstat(fifo).st_mode)),
    ]
    e = sb.Ide(BOX, "IDE %s rec3" % DF)
    e.quiet()
    base = ed_lines(e)
    row("M8 CONTROL: the record rec3 is open, its lock is held and the editor shows three-a", rec_lock("rec3").startswith("LOCKED") and base[0].startswith("three-a"), repr(base[:2]))
    try_names(e, do_saveas, cases, "M8 Save as", rid="rec3", base=base)
    row("M8z the record on the disk is as it was after every refusal", recs() == before, "")
    p = scr("sa3.txt")
    do_saveas(e, p)
    row("M8y CONTROL: after the refusals the same tab can still be saved as a free name: the file holds the record's text, the record's lock is given back",
        rd(p) == b"three-a\nthree-b\n" and "os sa3.txt" in tab_row(e) and rec_lock("rec3") == "GOT", "%r | %r | %r" % (rd(p), tab_row(e)[:100], rec_lock("rec3")))
    done(e)
    e = sb.Ide(BOX, "IDE")
    e.quiet()
    try_names(e, do_new, cases, "M8 New")
    p = scr("new8.txt")
    do_new(e, p)
    row("M8x CONTROL: after the refusals New still makes a free name (an empty file, os new8.txt in the strip)", rd(p) == b"" and "os new8.txt" in tab_row(e), "%r | %r" % (rd(p), tab_row(e)[:100]))
    done(e)

    # ---- M9 text that is not text for a file: a record with value marks -------------------------------------------------------------------------------------------------
    e = sb.Ide(BOX, "IDE %s recmark" % DF)
    e.quiet()
    base = ed_lines(e)
    do_saveas(e, empty_b)
    st, box = e.status(), e.text()
    row("M9 Save as of a record holding a value mark (recmark: Don|Henry^x) is refused before any file is touched: the message says a NUL or a byte from 248 to 255",
        "holds a NUL or a byte" in st or "holds a NUL or a byte" in box, repr(st[:160]))
    row("M9b ...the empty file at that name is untouched (same inode, mode, size 0 and modification time)", full_ident(empty_b) == st_empty and rd(empty_b) == b"", repr((full_ident(empty_b), st_empty)))
    row("M9c ...and the tab, the editor and the record's lock are as they were", tab_unchanged(e, "recmark", base), "%r | %r" % (tab_row(e)[:100], rec_lock("recmark")))
    p = scr("nomarks.txt")
    do_saveas(e, p)
    row("M9d ...and a free name is refused too, with NO file made", not os.path.lexists(p), "")
    done(e)

    # ---- M10 an existing EMPTY file is filled, and is the same file afterwards -------------------------------------------------------------------------------------------
    fe = scr("empty-fill.txt")
    put_file(fe, b"", 0o600)
    ie = full_ident(fe)
    e = sb.Ide(BOX, "IDE %s rec4" % DF)
    e.quiet()
    do_saveas(e, fe)
    i2 = full_ident(fe)
    row("M10 Save as onto an existing EMPTY file fills it: the file holds four-a, four-b and a final line end, and it is the same file (inode, mode 0600, owner, one link)",
        rd(fe) == b"four-a\nfour-b\n" and ie is not None and i2 is not None and i2[:4] == ie[:4] and "os empty-fill.txt" in tab_row(e), "%r | %r %r" % (rd(fe), ie, i2))
    done(e)

    # ---- M11 the administrator is not refused by an edit gate (the control for G9) ---------------------------------------------------------------------------------------
    p = scr("prog.bp", "admin-ok.txt")
    e = sb.Ide(BOX, "IDE")
    e.quiet()
    do_new(e, p)
    row("M11 CONTROL: the administrator makes a file below a directory called prog.bp (the edit gates do not bind SDSYS; G9 shows an ordinary account refused there)", rd(p) == b"", repr(rd(p)))
    done(e)

    # ---- M12 a file open in another tab is not made again ----------------------------------------------------------------------------------------------------------------------
    ox = scr("open-x.txt")
    put_file(ox, b"open x\n")
    ix = full_ident(ox)
    e = sb.Ide(BOX, "IDE %s rec4" % DF)
    e.quiet()
    e.keys(CTRL_O)
    name_to(e, ox)                                               # opens the file in a tab of its own (the Open form takes path:/full/name)
    e.keys(ALT_PGUP)                                             # back to the record's tab
    e.quiet()
    base = ed_lines(e)
    do_saveas(e, ox)
    st, box = e.status(), e.text()
    row("M12 Save as onto a file that is open in ANOTHER tab is refused: 'open in another tab'", "open in another tab" in st or "open in another tab" in box, repr(st[:160]))
    row("M12b ...the file is as it was, and both tabs are still there (the record's and os open-x.txt), the record's lock still held",
        full_ident(ox) == ix and rd(ox) == b"open x\n" and "[rec4]" in tab_row(e) and "os open-x.txt" in tab_row(e) and rec_lock("rec4").startswith("LOCKED"), "%r | %r" % (tab_row(e)[:120], rec_lock("rec4")))
    do_new(e, ox)
    row("M12c New onto it is refused the same way and makes no third tab", ("open in another tab" in e.status() or "open in another tab" in e.text()) and tab_row(e).count("os open-x.txt") == 1 and full_ident(ox) == ix, tab_row(e)[:120])
    done(e)


# ---- X ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_excl():
    say("\n--- X: the exclusive create through the other makers (the kernel's own rows are sandbox-oq2.py 485b-d) ------------------------")
    before = recs()
    dang, tgt = scr("dx.lnk"), scr("dx.tgt")
    os.symlink(tgt, dang)
    keep = scr("dx-keep.txt")
    put_file(keep, b"keep two\n")
    st_dang, st_keep = full_ident(dang), full_ident(keep)
    need("X0 control: a link to nothing and a file with content are there, the target is not", os.path.islink(dang) and not os.path.lexists(tgt) and rd(keep) == b"keep two\n")
    e = sb.Ide(BOX, "IDE %s rec1" % DF)
    e.quiet()
    base = ed_lines(e)
    for who, op in (("Write a copy", do_copy),):
        for label, path, ok in (("a link to nothing", dang, lambda: not os.path.lexists(tgt) and full_ident(dang) == st_dang and os.readlink(dang) == tgt),
                                ("a file with content", keep, lambda: full_ident(keep) == st_keep and rd(keep) == b"keep two\n")):
            op(e, path)
            hit, st = says(e, "there already")
            row("X1 %s onto %s is refused ('there already')" % (who, label), hit, repr(st[:160]))
            row("X1b ...the disk is as it was (the link's target is NOT made)", ok(), "")
            row("X1c ...and the tab, the editor and the record's lock are as they were", tab_unchanged(e, "rec1", base), tab_row(e)[:100])
    done(e)
    for label, path, ok in (("a link to nothing", dang, lambda: not os.path.lexists(tgt) and full_ident(dang) == st_dang and os.readlink(dang) == tgt),
                            ("a file with content", keep, lambda: full_ident(keep) == st_keep and rd(keep) == b"keep two\n")):
        e = sb.Ide(BOX, "IDE %s rec1" % DF)
        e.quiet()
        base = ed_lines(e)
        export_sel(e, path)
        hit, st = says(e, "there already")
        row("X2 Export onto %s is refused ('there already')" % label, hit, repr(st[:160]))
        row("X2b ...the disk is as it was", ok(), "")
        row("X2c ...the record's tab and lock are as they were", tab_unchanged(e, "rec1", base), tab_row(e)[:100])
        done(e)
    # the first save of an untitled buffer onto a link to nothing: the buffer stays untitled with its text, and a free name then works
    e = sb.Ide(BOX, "IDE")
    e.quiet()
    e.keys("scrap")
    e.keys(CTRL_S)
    name_to(e, dang)
    hit, st = says(e, "there already")
    row("X3 the first save of an untitled buffer onto a link to nothing is refused ('there already'), the target is not made", hit
        and not os.path.lexists(tgt) and full_ident(dang) == st_dang, repr(st[:160]))
    row("X3b ...the buffer is still untitled and still holds scrap (no os tab)", "os " not in tab_row(e) and "scrap" in "\n".join(ed_lines(e)), tab_row(e)[:100])
    p = scr("scrap.txt")
    e.keys(CTRL_S)
    name_to(e, p)
    row("X3c CONTROL: Ctrl-S again and a free name: the file holds scrap and a final line end", rd(p) == b"scrap\n", repr(rd(p)))
    done(e)
    row("X4 the record on the disk is as it was after every refusal", recs() == before, "")


# ---- T ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_tree():
    say("\n--- T: the tree's 'Operating system files' node ---------------------------------------------------------------------------------")
    chain = [d + "/" for d in SCR.split("/")[1:-1]]              # e.g. dev/ shm/ : the directories above the scratch directory
    zs = os.path.basename(SCR) + "/"
    e = sb.Ide(BOX, "IDE")
    e.quiet()
    e.keys(*GOTO_TREE)
    e.quiet()
    row("T0 CONTROL: the tree has the focus (the status line says [Files])", e.status().startswith("[Files]"), e.status()[:100])
    found = tree_goto(e, "Operating system files")
    scr_ = e.s.screen                                                     # 30 Oct 26: the first run failed here with the node in plain sight; show where the cursor is and how the rows are drawn
    row("T1 the administrator's tree has the node 'Operating system files', after the account's own files", found,
        "steps (label row, cursor row) %r\ncursor (row, col, visible) %r\nattrs of the tree's rows 3-%d:\n%s\n%s" % (TG_TRACE[:12], (scr_.r, scr_.c, scr_.cursor_visible), 3 + len(tree_lines(e)) - 1,
                                                                                  "\n".join("%2d %s %s" % (r, scr_.attrs(r)[:28], scr_.lines()[r][:28]) for r in range(3, 17)), "\n".join(tree_lines(e))))
    if not found:
        done(e)
        return
    row("T1b closed, it lists nothing: no %s node yet" % chain[0], tree_row_of(e, chain[0]) is None, "")
    e.keys(RET)
    e.quiet()
    row("T2 Return on it lists '/': %s is a node of its own, and it is a directory (a trailing slash)" % chain[0], tree_goto(e, chain[0]), "\n".join(tree_lines(e)))
    ok = tree_chain(e, chain + [zs])
    row("T2b Return on each directory down to the scratch directory lists it", ok and tree_goto(e, "t/") and tree_goto(e, "prog.bp/"), "\n".join(tree_lines(e)))
    if not ok:
        done(e)
        return
    tree_goto(e, "t/")
    e.keys(RET)
    e.quiet()
    shown = e.text()
    row("T3 listing t/ says that one entry is not shown (the name with a control character)", re.search(r"1 entries of %s are not shown" % re.escape(scr("t")), shown) is not None, shown[-300:])
    labels = []
    for _ in range(5):
        e.keys(DOWN)
        labels.append(cur_label(e))
    row("T3b the entries come directories first and sorted, then the files sorted: d1/ d2/ f1.txt f2.txt f3.txt (made in the reverse order)",
        labels == ["d1/", "d2/", "f1.txt", "f2.txt", "f3.txt"], repr(labels))
    e.keys(DOWN)
    nxt = cur_label(e)
    row("T3c the FIFO, the socket and the name with a control character are not nodes: the entry after f3.txt is not pfifo or psock, and no dctl node is among the five",
        nxt not in ("pfifo", "psock") and not any(l and l.startswith("dctl") for l in labels), repr((nxt, labels)))
    # directories open and close with Return, and Return on a directory closes everything under it
    tree_goto(e, "d1/")
    e.keys(RET)
    e.quiet()
    row("T4 Return on d1/ lists its file: inner.txt is a node under it", tree_goto(e, "inner.txt"), "\n".join(tree_lines(e)))
    tree_goto(e, "t/")
    e.keys(RET)
    e.quiet()
    row("T4b Return on t/ closes it and everything listed under it: no d1/, f1.txt or inner.txt left, and t/ itself stays",
        tree_row_of(e, "t/") is not None and all(tree_row_of(e, x) is None for x in ("d1/", "d2/", "f1.txt", "inner.txt")), "\n".join(tree_lines(e)))
    put_file(scr("t", "f4.txt"), b"f4\n")
    e.keys(RET)
    e.quiet()
    row("T4c Return on t/ again lists it afresh: f4.txt (made meanwhile) is there, and d1/ is closed again (inner.txt is not)", tree_goto(e, "f4.txt") and tree_row_of(e, "inner.txt") is None, "\n".join(tree_lines(e)))
    # a file node opens a tab
    before = rd(scr("t", "f1.txt"))
    tree_goto(e, "f1.txt")
    e.keys(RET)
    e.quiet()
    row("T5 Return on f1.txt opens it in a tab of its own: the strip says os f1.txt, the editor shows its lines, the focus is the editor, the file is as it was",
        "os f1.txt" in tab_row(e) and "f1 line one" in "\n".join(ed_lines(e)) and e.status().startswith("[Editor]") and rd(scr("t", "f1.txt")) == before, "%r | %r" % (tab_row(e)[:100], e.status()[:80]))
    e.keys(*GOTO_TREE)
    e.quiet()
    e.keys(RET)
    e.quiet()
    row("T5b Return on the same node again goes to the tab it is in: still ONE os f1.txt tab", tab_row(e).count("os f1.txt") == 1, tab_row(e)[:120])
    # a file made in a directory the tree lists appears in it
    p = scr("t", "f9.txt")
    do_new(e, p)
    e.keys(*GOTO_TREE)
    e.quiet()
    row("T6 a file made by New in a listed directory appears in the tree at once (f9.txt), and its tab is open (os f9.txt)", tree_goto(e, "f9.txt") and "os f9.txt" in tab_row(e), "\n".join(tree_lines(e)))
    # the root closes everything
    tree_goto(e, "Operating system files")
    e.keys(RET)
    e.quiet()
    row("T7 Return on 'Operating system files' closes the lot: none of %s, t/, f1.txt is a node" % chain[0],
        tree_row_of(e, "Operating system files") is not None and all(tree_row_of(e, x) is None for x in (chain[0], "t/", "f1.txt")), "\n".join(tree_lines(e)))
    e.keys(RET)
    e.quiet()
    row("T7b Return again lists only '/' afresh: %s is back and t/ is not (what was open was forgotten)" % chain[0], tree_goto(e, chain[0]) and tree_row_of(e, "t/") is None, "\n".join(tree_lines(e)))
    done(e)


# ---- I ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_import():
    say("\n--- I: Search / Import a record here takes path:/full/name ----------------------------------------------------------------------")
    ia, held, nulf, highf, dirf = scr("i-a.txt"), scr("i-held.txt"), scr("i-nul.bin"), scr("i-high.txt"), scr("i-dir")
    before = recs()
    ida = full_ident(ia)
    e = sb.Ide(BOX, "IDE %s rec5" % DF)
    e.quiet()
    row("I0 CONTROL: the record rec5 is open (five-a, five-b)", ed_lines(e)[:2] == ["five-a", "five-b"], repr(ed_lines(e)[:3]))
    e.keys(END)
    do_import(e, ia)
    l1 = ed_lines(e)
    row("I1 Import of path:<a file open nowhere> puts its lines in at the cursor (the end of line 1): five-aimp-a, imp-b, five-b", l1[:3] == ["five-aimp-a", "imp-b", "five-b"], repr(l1[:4]))
    row("I1b ...the status line counts the lines ('inserted at the cursor')", "inserted at the cursor" in e.status(), e.status()[:160])
    row("I1c ...the file is as it was and NO lock was left on it (another session gets it), the record on the disk is as it was and its lock is still held",
        full_ident(ia) == ida and rd(ia) == b"imp-a\nimp-b\n" and os_lock(ia) == "GOT" and recs() == before and rec_lock("rec5").startswith("LOCKED"), "%r %r" % (os_lock(ia), rec_lock("rec5")))
    for label, path, anchor in (("a file with a NUL", nulf, "NUL byte"), ("a file with characters outside ASCII", highf, "Cannot be imported into the text"), ("a directory", dirf, "not a plain file"),
                                ("a name with no file", scr("i-none.txt"), "There is no operating system file")):
        do_import(e, path)
        row("I2 Import of %s is refused: the message says %r" % (label, anchor), anchor in e.status() or anchor in e.text(), repr(e.status()[:160]))
        row("I2b ...nothing was inserted (the editor is as it was after I1) and no lock is left on it", ed_lines(e) == l1 and (os_lock(path) == "GOT" if os.path.isfile(path) else True), repr((os_lock(path) if os.path.isfile(path) else "-", ed_lines(e)[:3])))
    row("I2c the NUL file is as it was", rd(nulf) == b"ab\x00cd\n", repr(rd(nulf)))
    done(e)
    # a file that a tab of this IDE holds is imported from the TAB's text (opening it again would give away the lock the tab keeps)
    e = sb.Ide(BOX, "IDE %s rec6" % DF)
    e.quiet()
    e.keys(CTRL_O)
    name_to(e, held)                                             # opens i-held.txt in a tab of its own, the editor has the focus
    e.keys("UNSAVED")                                            # typed at the start of its first line, not saved
    e.keys(ALT_PGUP)                                             # back to the record's tab
    e.quiet()
    row("I3 CONTROL: the file's tab holds its lock (LOCKED) and the record's tab is current (six-a)", os_lock(held) == "LOCKED" and ed_lines(e)[0] == "six-a", "%r %r" % (os_lock(held), ed_lines(e)[:2]))
    do_import(e, held)
    l2 = ed_lines(e)
    row("I3a Import of a file a tab holds takes the TAB's text: UNSAVEDx1 (the unsaved line) and x2 are in the editor, though the file on the disk says x1", "UNSAVEDx1" in "\n".join(l2) and "x2" in "\n".join(l2) and rd(held) == b"x1\nx2\n", repr((l2[:4], rd(held))))
    row("I3b ...the tab's lock survived (still LOCKED), the file is as it was, and the record on the disk is as it was", os_lock(held) == "LOCKED" and rd(held) == b"x1\nx2\n" and recs() == before, repr(os_lock(held)))
    done(e)


# ---- G ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_gate():
    say("\n--- G: the OS gate in an ordinary account (the helper is not $internal: the kernel asks) ------------------------------------")
    g = _load("sandbox_gates_for_path", "sandbox-gates.py")
    g.BOX, g.SYS, g.SD = BOX, SYSD, os.path.join(SYSD, "bin", "sd")
    g.prepare()
    out = os.path.join(BOX, "zzp%s-out.txt" % RUN)
    host_before = rd("/etc/hostname")

    def pty(acct, path, cmd, keys, close=()):
        """one ordinary session: the commands, the keys, the screen as it is after them; then the keys of CLOSE (30 Oct 26: Esc, to close a form the rows above left open), then the way out"""
        env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
        env.pop("SDTEST_ADMIN", None)
        env.pop("SSH_CONNECTION", None)
        say("    > pty %s: %s | keys %r" % (acct, cmd, keys))
        s = PtySession([g.SD, "-a" + acct], path, env, 140, 43)
        s.settle(2.0)
        s.type("TERM xterm\r")
        s.type("TERM 140,43\r")
        s.type(cmd + "\r", idle=1.5)
        for k in keys:
            s.type(k, idle=0.8)
        text = "\n".join(l for l in s.screen.lines() if l.strip())
        for k in close:
            s.type(k, idle=0.6)
        for k in (CTRL_Q, DOWN, RET):
            s.type(k, idle=0.6)
        s.type("\rOFF\r", idle=0.5)
        s.finish()
        return text

    for acct, osx in (("zzpg1", "no"), ("zzpg2", "yes")):
        g.FIXTURES[acct] = ("no", osx)
        path = g.build_account(acct)
        g.reg_write(acct, [path, "", g.GROUP, "", "", "", "no", osx, "no", "yes", "yes", "no"])
        fl = g.flags(g.plain(acct, ["zzkf"]))
        row("G0 control: a session in %s (os %s) is an ordinary one (admin=0)" % (acct, osx), fl is not None and fl[0] == "0", repr(fl))
        inside = os.path.join(path, "inside.txt")
        if osx == "no":
            t = pty(acct, path, "IDE path:%s" % inside, ["ZZ", CTRL_S])
            row("G1 OS gate OFF: a file INSIDE the account opens and saves", rd(inside) == b"ZZan ordinary file in the account\n", repr((rd(inside), t[-300:])))
            t = pty(acct, path, "IDE path:%s" % out, ["ZZ", CTRL_S])
            row("G2 OS gate OFF: a file OUTSIDE the account is refused (has no OS access) and its bytes are untouched", "has no OS access" in t and rd(out) == b"outside\n", repr((rd(out), t[-300:])))
            t = pty(acct, path, "IDE path:%s" % os.path.join(path, "link.txt"), ["ZZ", CTRL_S])
            row("G3 OS gate OFF: a link inside the account that leads OUT of it is refused, and what it leads to (/etc/hostname) is untouched",
                "has no OS access" in t and rd("/etc/hostname") == host_before, repr((t[-300:], rd("/etc/hostname"))))
        else:
            t = pty(acct, path, "IDE path:%s" % out, ["ZZ", CTRL_S])
            row("G4 OS gate ON: the file outside the account opens and saves", rd(out) == b"ZZoutside\n", repr((rd(out), t[-300:])))

    # ---- G5 to G10 (30 Oct 26, stage E2): making files, the tree and Import in ordinary accounts.  zzpg1 has the OS gate OFF, zzpg2 ON, zzpg3 ON with bp.edit OFF.  The files made are
    #      judged on the disk; the screen is read only for the words (has no OS access, bp.edit) and for the form still being open.
    p1, p2 = os.path.join(BOX, "user_accounts", "zzpg1"), os.path.join(BOX, "user_accounts", "zzpg2")
    g.FIXTURES["zzpg3"] = ("no", "yes")
    p3 = g.build_account("zzpg3")
    g.reg_write("zzpg3", [p3, "", g.GROUP, "", "", "", "no", "yes", "no", "yes", "no", "no"])          # fields 10 to 12: voc.edit yes, bp.edit NO, dict.edit no
    fl = g.flags(g.plain("zzpg3", ["zzkf"]))
    row("G0 control: a session in zzpg3 (os yes, bp.edit no) is an ordinary one (admin=0)", fl is not None and fl[0] == "0", repr(fl))
    out2 = os.path.join(BOX, "zzp%s-out2.txt" % RUN)
    with open(out2, "wb") as fh:
        fh.write(b"outside two\n")
    newout = os.path.join(BOX, "zzp%s-newout.txt" % RUN)
    inner = os.path.join(p1, "zzpnew.txt")
    t = pty("zzpg1", p1, "IDE", [CTRL_N, TAB, CTRL_U, "path:" + newout, RET], close=[ESC])
    row("G5 OS gate OFF: New with path:<a name outside the account> is refused IN THE FORM (has no OS access), the form is still open, and no file was made",
        "has no OS access" in t and "Name of the new record" in t and not os.path.lexists(newout), repr((os.path.lexists(newout), t[-300:])))
    t = pty("zzpg1", p1, "IDE", [CTRL_N, TAB, CTRL_U, "path:" + inner, RET])
    ii = full_ident(inner)
    row("G6 CONTROL, OS gate OFF: a name INSIDE the account is made: an empty plain file, ours, one link", ii is not None and ii[4] == 0 and ii[2] == UID and ii[3] == 1, repr((ii, t[-300:])))
    t1 = pty("zzpg1", p1, "IDE", [])
    t2 = pty("zzpg2", p2, "IDE", [])
    row("G7 the tree has NO 'Operating system files' node for the account without OS access (and the IDE is up: the control)", "IDE: " in t1 and "Operating system files" not in t1, t1[-300:])
    row("G7b ...and has it when the account has OS access", "IDE: " in t2 and "Operating system files" in t2, t2[-300:])
    t3 = pty("zzpg2", p2, "IDE", list(GOTO_TREE) + ["O", RET])
    row("G7c OS gate ON: Return on the node lists '/' (a root directory such as etc/, usr/ or var/ is there)", re.search(r"\b(etc|usr|var|dev)/", t3) is not None, t3[-400:])
    t = pty("zzpg2", p2, "IDE", [CTRL_N, TAB, CTRL_U, "path:" + newout, RET])
    io_ = full_ident(newout)
    row("G8 OS gate ON: New with path:<a name outside the account> makes it: an empty plain file, ours", io_ is not None and io_[4] == 0 and io_[2] == UID, repr((io_, t[-300:])))
    # 30 Oct 26: the edit gate looks at the components BELOW THE ACCOUNT'S OWN DIRECTORY only (op_sh.c edit_os_path_refusal: an account that holds OS.EXECUTE - the register's
    # os field - is "the whole machine ... not covered"), so the first version of this row, a directory called prog.bp OUTSIDE the account, was made by design.  The program file
    # that the account may not change is its own bp; the control is the same account's other place.
    gated, free = os.path.join(p3, "bp", "gated.txt"), os.path.join(p3, "ord-ok.txt")
    t = pty("zzpg3", p3, "IDE", [CTRL_N, TAB, CTRL_U, "path:" + gated, RET], close=[ESC])
    row("G9 OS gate ON but bp.edit OFF: New below the account's own bp (a program file) is refused IN THE FORM with the edit gate's words (bp.edit), the form stays open, no file made",
        "bp.edit" in t and "Name of the new record" in t and not os.path.lexists(gated), repr((os.path.lexists(gated), t[-300:])))
    t = pty("zzpg3", p3, "IDE", [CTRL_N, TAB, CTRL_U, "path:" + free, RET])
    row("G9b CONTROL: the same account makes a file that is not below a program file", rd(free) == b"", repr((rd(free), t[-300:])))
    t = pty("zzpg1", p1, "IDE", [F10, RIGHT, RIGHT, DOWN * 7, RET, TAB, CTRL_U, "path:" + out2, RET])
    row("G10 OS gate OFF: Import of a file outside the account is refused (has no OS access), nothing is inserted, and the file is untouched",
        "has no OS access" in t and "outside two" not in t and rd(out2) == b"outside two\n", repr((rd(out2), t[-300:])))


def teardown():
    for key in SHORT_KEYS:                                       # the two files this run made in SHORT, and then the directory if nothing else is in it
        try:
            os.remove(fpath(key))
        except OSError:
            pass
    try:
        os.rmdir(SHORT)
    except OSError:
        pass
    # the scratch directory of S1 to I: exactly the one this run named (its path holds the run's number), never a link, and only under /dev/shm or /tmp
    if SCR_MADE and re.fullmatch(r"/(dev/shm|tmp)/zs\d{5}", SCR) and os.path.isdir(SCR) and not os.path.islink(SCR):
        shutil.rmtree(SCR, ignore_errors=True)
    if BOX:
        subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)


ONLY = [a[len("--only="):].split(",") for a in sys.argv[1:] if a.startswith("--only=")]


def wanted(name):
    """--only=tree,import,gate runs those sections after S0 and S1 (which always run: the fixtures and the controls); no --only runs them all"""
    return not ONLY or name in ONLY[0]


def main():
    global BOX, SYSD, ACC
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        say("usage: sandbox-ide-path.py <dir> [--build] [--only=open_save,refused,lock,changed,notfor,make,excl,tree,import,gate]")
        sys.exit(2)
    if ONLY and not set(ONLY[0]) <= {"open_save", "refused", "lock", "changed", "notfor", "make", "excl", "tree", "import", "gate"}:
        say("sandbox-ide-path: --only names a section that is not there: %s" % ",".join(ONLY[0]))
        sys.exit(2)
    BOX = os.path.abspath(args[0])
    SYSD = os.path.join(BOX, "sys")
    ACC = os.path.join(BOX, "user_accounts")
    say("sandbox-ide-path: sandbox %s  tree %s  run %s  SDBOX_KEYSET=%s" % (BOX, os.path.dirname(HERE), RUN, os.environ.get("SDBOX_KEYSET")))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-path: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYSD, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        section_setup()
        for name, fn in (("open_save", section_open_save), ("refused", section_refused), ("lock", section_lock), ("changed", section_changed), ("notfor", section_notfor)):
            if wanted(name):
                fn()
        section_scratch()              # S1: stops the suite (exit 2) when the scratch directory or a probe is not what it must be
        for name, fn in (("make", section_make), ("excl", section_excl), ("tree", section_tree), ("import", section_import),
                         ("gate", section_gate)):          # gate last: prepare() makes the sandbox user ordinary unless SDTEST_ADMIN is set
            if wanted(name):
                fn()
    finally:
        teardown()
    say("\nsandbox-ide-path: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        say("sandbox-ide-path: CANNOT RUN - no row ran (a broken test, not a pass)")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
