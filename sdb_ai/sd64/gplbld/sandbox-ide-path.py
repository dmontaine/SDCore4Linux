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
#   C    the file changed on disk between the open and the save: the overwrite question (Cancel is the default; Cancel leaves the other bytes; Overwrite writes ours)
#   N    what does not apply: Ctrl-E (SED) and F8 (compile) on such a tab say so and change nothing; no recovery copy was written for it
#   G    an ordinary account: OS gate off - a file inside the account opens and saves, a file outside it and a link that leads out are refused (the bytes untouched);
#        OS gate on - the outside file opens and saves

import importlib.util
import os
import re
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
    "lock": (b"held\n", 0o640),
}


def fpath(key):
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
    row("N1 Ctrl-E (SED) says it is an operating system file and the IDE stays up with the tab", "operating system file" in e.status() and in_ide(e), e.status()[:160])
    e.keys(F8)
    e.quiet()
    row("N2 F8 (compile) says the same and does not save the text", "operating system file" in e.status() and rd(fpath("tab")) == b"ZZa\tb\n", repr((e.status()[:100], rd(fpath("tab")))))
    time.sleep(2.5)
    after = sorted(os.listdir(rcdir)) if os.path.isdir(rcdir) else None
    row("N3 no recovery copy was written for the changed tab (the store in the home is as it was)", before == after, repr((before, after)))
    done(e)


# ---- G ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def section_gate():
    say("\n--- G: the OS gate in an ordinary account (the helper is not $internal: the kernel asks) ------------------------------------")
    g = _load("sandbox_gates_for_path", "sandbox-gates.py")
    g.BOX, g.SYS, g.SD = BOX, SYSD, os.path.join(SYSD, "bin", "sd")
    g.prepare()
    out = os.path.join(BOX, "zzp%s-out.txt" % RUN)
    host_before = rd("/etc/hostname")

    def pty(acct, path, cmd, keys):
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


def teardown():
    if BOX:
        subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)


def main():
    global BOX, SYSD, ACC
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        say("usage: sandbox-ide-path.py <dir> [--build]")
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
        section_open_save()
        section_refused()
        section_lock()
        section_changed()
        section_notfor()
        section_gate()                 # last: prepare() makes the sandbox user ordinary unless SDTEST_ADMIN is set
    finally:
        teardown()
    say("\nsandbox-ide-path: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        say("sandbox-ide-path: CANNOT RUN - no row ran (a broken test, not a pass)")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
