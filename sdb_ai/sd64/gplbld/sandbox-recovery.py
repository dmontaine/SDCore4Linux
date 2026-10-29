#!/usr/bin/env python3
#
# sandbox-recovery.py - the editors' recovery copy (S.88, plan 2.9, defect D2; the owner's answer to Q2 of 28 Oct 2026: "Build it, ship it off").  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-recovery.py <dir> [--build] [--strict]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row
# that counts passed, 1 a row failed, 2 it could not run.  Every row is phase 2 of the plan (tuirows.py): PENDING until phase 2 is in LANDED, --strict counts it.
#
# START-HISTORY:
# 28 Oct 26 dm  New with the recovery copy.  WRITTEN, NOT RUN (the owner's testing rule of 28 Oct: one complete run after all the full-screen phases).
# 28 Oct 26 dm  Section R, the TUI phase 2 review's findings: R1 two untitled copies both opened are both kept, R2 a copy the tab does not own is kept, the person told
#               (11778), and the tab writes its own once that copy is gone, R3 an emptied untitled tab taken away by New record drops its copy.  WRITTEN, NOT RUN.
# END-HISTORY
#
# WHAT RUNS.  ORDINARY sessions of fixture accounts (made as sandbox-gates.py makes them; their LOGIN paragraph says TERM LINUX, so the keys are the linux forms) on a
# PSEUDO-TERMINAL at 140 by 43, each running the IDE on a record of the account's own bp.  A hang-up is the master side closed, as closing a terminal window does
# (sandbox-ide-fresh.py's hangup_timed).  EVERY OUTCOME IS READ FROM THE DISK: the account directory walked for a file holding the text typed, the $recovery
# directory's mode and owner by lstat, the record's bytes before and after.  Nothing the IDE says is taken as evidence of a copy.
#
# THE ONE CHANGE TO THE SANDBOX'S PROGRAMS.  !edit_recovery writes a copy only in a USER account for its own person: the register group must be sdu_<the Linux
# user>.  A sandbox cannot make that group (it needs root), and LOGIN refuses an account whose group the user is not in, so the fixture accounts carry the
# sandbox user's own group.  Section G FIRST runs the SHIPPED rule against such an account with the switch on (no copy may appear: the rule refuses it); then the
# sandbox's copy of edit_recovery is changed in exactly one line - 'sdu_' : rc.user becomes the fixture group - and recompiled, and the change is printed.
# What that line decides in a real install (a real sdu_ group) is the VM's to show.
#
#   G    the shipped identity rule: an account whose group is not sdu_<user> gets no copy even with the switch on (and no $recovery directory)
#   A    the switch OFF (blank field, as delivered): typing, a pause, a hang-up leave no $recovery directory and no file anywhere in the account holding the text
#   C1   the switch ON: after a pause and a hang-up, $recovery is a real directory of the user's, mode 0700; it holds one copy, mode 0600, with the text; the record is unchanged
#   C1b  ...the copy exists while the IDE still runs (the quiet second, which is what saves the text from an abort the program cannot catch)
#   C2   the record opened again asks first; Enter (Use the copy) puts the text in the editor, changed, the disk unchanged; Ctrl-S writes it and the copy goes
#   C3   Delete the copy: the copy goes and the editor shows the record as it is on the disk
#   C4   Cancel: the record is not opened and the copy stays
#   C5   Close (Ctrl-W) with Discard: the copy goes and the record is unchanged
#   C6   an untitled buffer: a copy after a hang-up, offered by the next bare IDE, Open puts its text in a tab
#   C7   a copy that is not whole (its length does not match) is never offered
#   C8   $recovery replaced by a LINK to a directory of the user's: nothing is written through it (the target stays empty)
#   C9   $recovery made group- and world-readable: no copy is written in it
#   C10  the switch turned off in the register: a new hang-up leaves no new copy
#   R1   two untitled copies, both answered Open: both stay on the disk (a second Open wrote the empty startup buffer over the first tab, and a tick deleted its copy)
#   R2   a copy the tab does not own under the name its first save gave it: kept, the person told (11778); once it is gone the tab writes its own within 10 s
#   R3   an untitled tab opened from a copy, emptied, then replaced by New record (the switch off, so no tick): its copy goes
#
# NOT HERE: a group account refused by MODIFY.ACCOUNT / CREATE.ACCOUNT (11771) - test-recovery-units.py reads that off the source, and CREATE.ACCOUNT makes Linux
# users; the abort path itself (no BASIC runs after an abort: C1b is the row for it); a full disk.

import hashlib
import importlib.util
import os
import stat
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tuirows import Rows  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fr = _load("sandbox_ide_fresh_for_recovery", "sandbox-ide-fresh.py")
sh, g, say, bail = fr.sh, fr.g, fr.say, fr.bail
R = Rows("recovery")
PH = 2                                   # the plan's phase whose change makes these rows pass
E = "\x1b"
L_DOWN = E + "[B"
RET, ESC = "\r", E
CTRL_S, CTRL_W = "\x13", "\x17"
RUN = "%05d" % (os.getpid() % 100000)
ACC_G, ACC_OFF, ACC_ON = "zzrcg", "zzrc0", "zzrc1"
SHIPPED_RULE = "   if downcase(trim(arec<ACC$GROUP>)) # 'sdu_' : rc.user then return\n"


def rid(tag):
    return "zzrc%s%s" % (tag, RUN[-3:])


def acct(a):
    return fr.acct_dir(a)


def rdir(a):
    return os.path.join(acct(a), "$recovery")


def recbp(a, r):
    return os.path.join(acct(a), "bp", r)


def slot(fname, r):
    """the copy's file name as !edit_recovery makes it: 'c' and the SHA-256, in hex, of the file name, a field mark (char 254) and the record id"""
    return "c" + hashlib.sha256((fname + "\xfe" + r).encode("latin-1")).hexdigest()


def holders(a, text):
    """every file under the account directory (links not followed) that holds text"""
    out = []
    for base, dirs, files in os.walk(acct(a), followlinks=False):
        for n in files:
            p = os.path.join(base, n)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and st.st_size < 2000000:
                t = fr.readf(p)
                if t is not None and text in t:
                    out.append(p)
    return out


def lmode(p):
    try:
        st = os.lstat(p)
    except OSError:
        return None
    return st


def register(a, recovery):
    """the fixture's register record: the sandbox user's group, the edit gates on (so Ctrl-S may write bp), field 19 as given"""
    g.reg_write(a, [acct(a), "", g.GROUP, "", "", "", "no", "no", "no", "yes", "yes", "yes", "", "", "no", "", "", "", recovery])
    say("    (register %s: field 19 = %r, group %s)" % (a, recovery, g.GROUP))


def ide(label, a, args):
    return fr.ordinary(label, a, "IDE " + args)


def type_pause_hangup(s, text, pause=2.5):
    s.type(text, wait=pause, show=repr(text) + " then %.1f s of quiet" % pause)
    changed = " *" in s.status()
    el, went = s.hangup_timed()
    time.sleep(1.0)
    say("    [%s] hung up: gone after %.2f s (went=%r); the status before was %r" % (s.label, el, went, s.status()[:80]))
    return changed


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------
def setup():
    sh.setup("sandbox-recovery.py")
    if sh.tkb.failed:
        bail("the setup row failed: an ordinary session is not shown to be one, so no row below can be believed")
    for a in (ACC_G, ACC_OFF, ACC_ON):
        g.FIXTURES[a] = ("no", "no")
        g.build_account(a)
        os.makedirs(os.path.join(acct(a), "bp"), exist_ok=True)
    register(ACC_G, "yes")
    register(ACC_OFF, "")
    register(ACC_ON, "yes")
    fl = g.flags(g.plain(ACC_ON, ["zzkf"]))
    say("    (%s pipe session flags admin, sh, osx, user: %r)" % (ACC_ON, fl))
    if fl is None or fl[0] != "0":
        bail("%s is not shown to be an ordinary account (flags %r)" % (ACC_ON, fl))
    R.row("SETUP control: an ordinary fixture session is not an administrator", True, "")


def patch_rule():
    """the sandbox's own edit_recovery, the identity line pointed at the fixture group (the only change), recompiled as the administrator"""
    p = os.path.join(sh.SYS, "gpl.bp", "edit_recovery")
    with open(p, encoding="latin-1") as f:
        src = f.read()
    if src.count(SHIPPED_RULE) != 1:
        bail("the sandbox's edit_recovery does not hold the identity line once (%d)" % src.count(SHIPPED_RULE))
    new = "   if downcase(trim(arec<ACC$GROUP>)) # '%s' then return\n" % g.GROUP.lower()
    with open(p, "w", encoding="latin-1") as f:
        f.write(src.replace(SHIPPED_RULE, new))
    say("    PATCH (the one change): %r -> %r in %s" % (SHIPPED_RULE.strip(), new.strip(), p))
    out = g.adm(["BASIC gpl.bp edit_recovery"], internal=True)
    if not g.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the patched edit_recovery did not compile:\n" + "\n".join(out[-6:]))


# ---- G: the shipped identity rule -------------------------------------------------------------------------------------------------------------------------------
def section_rule():
    say("\n--- G: the shipped rule (the group is not sdu_<user>) ---------------------------------------------------------------")
    r = rid("g")
    fr.mk(recbp(ACC_G, r), "kept\n")
    s = ide("G", ACC_G, "bp " + r)
    changed = type_pause_hangup(s, "GRULEMARK")
    R.row("G control: the buffer was changed before the hang-up", changed, "", phase=PH)
    R.row("G1 the switch is on but the account's group is not sdu_<user>: no $recovery directory is made", lmode(rdir(ACC_G)) is None, repr(lmode(rdir(ACC_G))), phase=PH)
    R.row("G2 ...and no file in the account holds the text", not holders(ACC_G, "GRULEMARK"), repr(holders(ACC_G, "GRULEMARK")), phase=PH)


# ---- A: the switch off -------------------------------------------------------------------------------------------------------------------------------------------
def section_off():
    say("\n--- A: the switch off, as delivered ---------------------------------------------------------------------------------")
    r = rid("a")
    fr.mk(recbp(ACC_OFF, r), "kept\n")
    s = ide("A", ACC_OFF, "bp " + r)
    changed = type_pause_hangup(s, "OFFMARK")
    R.row("A control: the buffer was changed before the hang-up", changed, "", phase=PH)
    R.row("A1 with the switch off no $recovery directory is made", lmode(rdir(ACC_OFF)) is None, "", phase=PH)
    R.row("A2 ...no file anywhere in the account holds the text", not holders(ACC_OFF, "OFFMARK"), repr(holders(ACC_OFF, "OFFMARK")), phase=PH)
    R.row("A3 ...and the record is as it was", fr.readf(recbp(ACC_OFF, r)) == "kept\n", fr.disk(recbp(ACC_OFF, r)), phase=PH)


# ---- C: the switch on --------------------------------------------------------------------------------------------------------------------------------------------
def section_on():
    say("\n--- C: the switch on --------------------------------------------------------------------------------------------------")
    d = rdir(ACC_ON)
    r1 = rid("c1")
    fr.mk(recbp(ACC_ON, r1), "kept\n")
    s = ide("C1", ACC_ON, "bp " + r1)
    s.type("ONMARK1", wait=2.5, show="'ONMARK1' then 2.5 s of quiet")
    live = holders(ACC_ON, "ONMARK1")
    R.row("C1b a copy holding the text exists while the IDE still runs (after a second of quiet), so an abort, which no program can catch, does not lose it",
          s.alive() and any(p.startswith(d + os.sep) for p in live), repr(live), phase=PH)
    el, went = s.hangup_timed()
    time.sleep(1.0)
    st = lmode(d)
    R.row("C1 $recovery is a real directory (not a link), owned by the session's user, mode 0700 (no group or other bits)",
          st is not None and stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and (st.st_mode & 0o077) == 0 and (st.st_mode & 0o700) == 0o700,
          "mode %s uid %s" % (oct(st.st_mode) if st else None, st.st_uid if st else None), phase=PH)
    names = sorted(os.listdir(d)) if st is not None and stat.S_ISDIR(st.st_mode) else []
    cp = os.path.join(d, slot("bp", r1))
    cst = lmode(cp)
    txt = fr.readf(cp) or ""
    say("    $recovery holds %r; the copy %s: %r" % (names, os.path.basename(cp), txt[:160]))
    R.row("C1c ...it holds the one copy, named for bp and the record, a regular file of the user's, mode 0600",
          names == [slot("bp", r1)] and cst is not None and stat.S_ISREG(cst.st_mode) and cst.st_uid == os.getuid() and (cst.st_mode & 0o777) == 0o600,
          "names %r mode %s" % (names, oct(cst.st_mode) if cst else None), phase=PH)
    R.row("C1d ...the copy begins with its magic line and holds the account, the file, the record and the text typed",
          txt.startswith("sd-recovery 1\xfe" + ACC_ON + "\xfebp\xfe" + r1 + "\xfe") and "ONMARK1" in txt, repr(txt[:80]), phase=PH)
    R.row("C1e ...and the record on disk is as it was", fr.readf(recbp(ACC_ON, r1)) == "kept\n", fr.disk(recbp(ACC_ON, r1)), phase=PH)

    # C2: Use the copy, then Ctrl-S
    s = ide("C2", ACC_ON, "bp " + r1)
    asked = "A recovery copy of bp " + r1 in s.text()
    s.show("the question", rows=range(10, 34))
    s.type(RET, wait=1.5, show="RET (Use the copy, the default)")
    R.row("C2 opening the record again asks first, naming the file and the record", asked, "", phase=PH)
    R.row("C2b Enter (Use the copy) puts the copy's text in the editor, marked changed, and the record on disk is still as it was",
          "ONMARK1" in s.editor() and " *" in s.status() and fr.readf(recbp(ACC_ON, r1)) == "kept\n", "status %r disk %s" % (s.status()[:60], fr.disk(recbp(ACC_ON, r1))), phase=PH)
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    on_disk = fr.readf(recbp(ACC_ON, r1)) or ""
    R.row("C2c Ctrl-S writes the text to the record and the copy goes", "ONMARK1" in on_disk and lmode(cp) is None, "disk %r copy %r" % (on_disk[:40], lmode(cp)), phase=PH)
    s.end()

    # C3: Delete the copy
    r3 = rid("c3")
    fr.mk(recbp(ACC_ON, r3), "kept3\n")
    type_pause_hangup(ide("C3a", ACC_ON, "bp " + r3), "DELMARK")
    cp3 = os.path.join(d, slot("bp", r3))
    had = lmode(cp3) is not None
    s = ide("C3", ACC_ON, "bp " + r3)
    s.type(L_DOWN + RET, wait=1.5, show="Down RET (Delete the copy)")
    R.row("C3 Delete the copy: the copy that was there is gone, the editor shows the record as it is on the disk, unchanged",
          had and lmode(cp3) is None and "kept3" in s.editor() and "DELMARK" not in s.editor() and " *" not in s.status(), "had %r editor %r" % (had, s.editor()[:60]), phase=PH)
    s.end()

    # C4: Cancel
    r4 = rid("c4")
    fr.mk(recbp(ACC_ON, r4), "kept4\n")
    type_pause_hangup(ide("C4a", ACC_ON, "bp " + r4), "CANMARK")
    cp4 = os.path.join(d, slot("bp", r4))
    s = ide("C4", ACC_ON, "bp " + r4)
    s.type(L_DOWN + L_DOWN + RET, wait=1.5, show="Down Down RET (Cancel)")
    R.row("C4 Cancel: the record is not opened (neither its text nor the copy's is in the editor) and the copy stays",
          "kept4" not in s.editor() and "CANMARK" not in s.editor() and lmode(cp4) is not None, "editor %r" % s.editor()[:60], phase=PH)
    s.end()

    # C5: Close with Discard
    r5 = rid("c5")
    fr.mk(recbp(ACC_ON, r5), "kept5\n")
    s = ide("C5", ACC_ON, "bp " + r5)
    s.type("DISCMARK", wait=2.5, show="'DISCMARK' then 2.5 s of quiet")
    cp5 = os.path.join(d, slot("bp", r5))
    had = lmode(cp5) is not None
    s.type(CTRL_W, wait=1.5, show="Ctrl-W")
    asked = "has changes" in s.text()
    s.type(L_DOWN + RET, wait=1.5, show="Down RET (Discard)")
    R.row("C5 Close with Discard: the copy written during the session goes, and the record is unchanged",
          had and asked and lmode(cp5) is None and fr.readf(recbp(ACC_ON, r5)) == "kept5\n", "had %r asked %r" % (had, asked), phase=PH)
    s.end()

    # C6: an untitled buffer
    before = set(os.listdir(d))
    s = ide("C6a", ACC_ON, "")
    type_pause_hangup(s, "UNTMARK")
    new = [n for n in os.listdir(d) if n not in before and "UNTMARK" in (fr.readf(os.path.join(d, n)) or "")]
    R.row("C6 an untitled buffer's text is kept after a hang-up, in a copy with no file name", len(new) == 1 and "\xfe\xfe" in (fr.readf(os.path.join(d, new[0])) or "")[:200] if new else False,
          repr(new), phase=PH)
    s = ide("C6", ACC_ON, "")
    asked = "untitled buffer was kept" in s.text()
    s.type(RET, wait=1.5, show="RET (Open)")
    R.row("C6b the next bare IDE offers it, and Open puts its text in a tab", asked and "UNTMARK" in s.editor(), "asked %r" % asked, phase=PH)
    s.end()

    # C7: a copy that is not whole
    r7 = rid("c7")
    fr.mk(recbp(ACC_ON, r7), "kept7\n")
    body = "FORGED"
    bad = "\xfe".join(["sd-recovery 1", ACC_ON, "bp", r7, "20000", "0", str(len(body) + 5), hashlib.sha256(body.encode()).hexdigest(), body])
    p7 = os.path.join(d, slot("bp", r7))
    with open(p7, "w", encoding="latin-1") as f:
        f.write(bad)
    os.chmod(p7, 0o600)
    s = ide("C7", ACC_ON, "bp " + r7)
    R.row("C7 a copy whose length does not match is never offered (no question; the record opens as it is)",
          "A recovery copy of" not in s.text() and "kept7" in s.editor(), "", phase=PH)
    s.end()

    # C10: the switch turned off between sessions
    register(ACC_ON, "no")
    r10 = rid("c10")
    fr.mk(recbp(ACC_ON, r10), "kept10\n")
    type_pause_hangup(ide("C10", ACC_ON, "bp " + r10), "OFFAGAIN")
    R.row("C10 RECOVERY-OFF in the register: a new hang-up leaves no new copy", not holders(ACC_ON, "OFFAGAIN"), repr(holders(ACC_ON, "OFFAGAIN")), phase=PH)
    register(ACC_ON, "yes")


# ---- R: the TUI phase 2 review's findings (28 Oct 26; WRITTEN, NOT RUN) ------------------------------------------------------------------------------------------
def copy_fields(p):
    t = fr.readf(p) or ""
    return t.split("\xfe", 8)


def drop_untitled(d):
    """the untitled copies (no file name) left by earlier rows go, so that a bare IDE below asks only about this section's own"""
    gone = []
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        f = copy_fields(os.path.join(d, n))
        if len(f) == 9 and f[0] == "sd-recovery 1" and f[2] == "":
            os.remove(os.path.join(d, n))
            gone.append(n)
    say("    (untitled copies removed before the section: %r)" % gone)


def untitled_holding(d, text):
    return [n for n in (sorted(os.listdir(d)) if os.path.isdir(d) else []) if copy_fields(os.path.join(d, n))[2:3] == [""] and text in (fr.readf(os.path.join(d, n)) or "")]


def plant(d, fname, r, body):
    """a whole, private copy as another session of the same person would leave it (the format !edit_recovery writes)"""
    p = os.path.join(d, slot(fname, r))
    rec = "\xfe".join(["sd-recovery 1", ACC_ON, fname, r, "20000", "0", str(len(body)), hashlib.sha256(body.encode("latin-1")).hexdigest(), body])
    with open(p, "w", encoding="latin-1") as f:
        f.write(rec)
    os.chmod(p, 0o600)
    return p


def section_review():
    say("\n--- R: the review's findings: two untitled copies, a copy the tab does not own, an emptied untitled tab -------------")
    d = rdir(ACC_ON)
    DEL_KEY, CTRL_A = E + "[3~", "\x01"
    F10 = E + "[21~"

    # R1: two untitled copies, both answered Open.  Before the fix the second Open wrote the empty startup buffer over the first tab and the next tick deleted its copy.
    drop_untitled(d)
    type_pause_hangup(ide("R1a", ACC_ON, ""), "TWOMARKA")
    s = ide("R1b", ACC_ON, "")
    asked_a = "untitled buffer was kept" in s.text()
    s.type(L_DOWN + L_DOWN + RET, wait=1.5, show="Down Down RET (Later)")
    type_pause_hangup(s, "TWOMARKB")
    have = (untitled_holding(d, "TWOMARKA"), untitled_holding(d, "TWOMARKB"))
    R.row("R1 control: two untitled copies are on the disk, one holding each text (the second session was asked about the first and answered Later)",
          asked_a and len(have[0]) == 1 and len(have[1]) == 1, "asked %r copies %r" % (asked_a, have), phase=PH)
    s = ide("R1", ACC_ON, "")
    q1 = "untitled buffer was kept" in s.text()
    s.type(RET, wait=1.5, show="RET (Open, the first)")
    q2 = "untitled buffer was kept" in s.text()
    s.type(RET, wait=2.5, show="RET (Open, the second) then 2.5 s of quiet (a tick)")
    s.show("after two Opens", rows=[0, 1, 2, 3, 42])
    live = (untitled_holding(d, "TWOMARKA"), untitled_holding(d, "TWOMARKB"))
    R.row("R1b both questions were asked, and after two Opens and a quiet second BOTH copies are still on the disk holding their texts (the first Open's was deleted before)",
          q1 and q2 and len(live[0]) == 1 and len(live[1]) == 1, "asked %r %r copies %r" % (q1, q2, live), phase=PH)
    s.hangup_timed()
    time.sleep(1.0)
    after = (untitled_holding(d, "TWOMARKA"), untitled_holding(d, "TWOMARKB"))
    R.row("R1c ...and after a hang-up both are still there: neither text was lost", len(after[0]) == 1 and len(after[1]) == 1, repr(after), phase=PH)

    # R2: a copy the tab does not own (another session's) under the name the tab takes at its first save; the tab says so, writes nothing over it, and protects itself
    #     again once that copy is gone.  Before the fix it never wrote a copy again.
    drop_untitled(d)
    r2 = rid("r2")
    foreign = plant(d, "bp", r2, "FOREIGNTXT")
    s = ide("R2", ACC_ON, "")
    s.type("MINE12", wait=1.2, show="'MINE12'")
    s.type(CTRL_S, wait=1.5, show="Ctrl-S (the first save of the untitled buffer: the name form)")
    s.type(r2 + RET, wait=2.0, show=repr(r2) + " RET")
    saved = fr.readf(recbp(ACC_ON, r2))
    s.type("MORE", wait=2.5, show="'MORE' then 2.5 s of quiet")
    told = "gets no recovery copy" in s.text()
    kept = "FOREIGNTXT" in (fr.readf(foreign) or "") and "MORE" not in (fr.readf(foreign) or "")
    R.row("R2 control: the first save named the buffer bp %s and wrote it" % r2, saved is not None and "MINE12" in saved, fr.disk(recbp(ACC_ON, r2)), phase=PH)
    R.row("R2b the copy the tab did not write is kept as it was, and the person is told the tab has none (11778)", kept and told, "kept %r told %r" % (kept, told), phase=PH)
    os.remove(foreign)
    say("    (the other copy removed, as the other session's save would)")
    s.wait(12.5)
    mine = fr.readf(foreign) or ""
    R.row("R2c once that copy is gone the tab writes its own within RC.LOOK (10) seconds: a copy at bp %s holds the changed text" % r2,
          s.alive() and "MORE" in mine and "MINE12" in mine and "FOREIGNTXT" not in mine, repr(mine[:120]), phase=PH)
    s.end()

    # R3: an untitled tab whose text the person deleted, taken away by New record, drops its copy.  The switch is OFF in this session, so no tick can drop it (as
    #     after RECOVERY-OFF); before the fix the copy stayed and was offered again at the next bare IDE with the deleted text.
    drop_untitled(d)
    type_pause_hangup(ide("R3a", ACC_ON, ""), "EMPTYME")
    register(ACC_ON, "no")
    s = ide("R3", ACC_ON, "")
    s.type(RET, wait=1.5, show="RET (Open)")
    s.type(CTRL_A + DEL_KEY, wait=1.5, show="Ctrl-A Del (the whole text deleted)")
    emptied = "EMPTYME" not in s.editor()
    still = len(untitled_holding(d, "EMPTYME")) == 1
    R.row("R3 control: the copy was opened, its text deleted in the editor, and the copy is still on the disk (the switch is off: no tick drops it)", emptied and still,
          "emptied %r still %r" % (emptied, still), phase=PH)
    r3 = rid("r3")
    s.type(F10, wait=1.0, show="F10")
    s.type(RET, wait=1.5, show="RET (File, New record)")
    s.type(r3 + RET, wait=2.0, show=repr(r3) + " RET")
    gone = not untitled_holding(d, "EMPTYME")
    R.row("R3b New record takes the empty untitled tab's place and its copy goes with it", gone and s.in_ide(), "copies %r" % untitled_holding(d, "EMPTYME"), phase=PH)
    s.end()
    register(ACC_ON, "yes")


# ---- C8, C9: the directory is not the user's private one --------------------------------------------------------------------------------------------------------
def section_dir():
    say("\n--- C8 / C9: a directory that is not private --------------------------------------------------------------------------")
    d = rdir(ACC_ON)
    target = os.path.join(sh.BOX, "zzrc-target")
    os.makedirs(target, exist_ok=True)
    os.chmod(target, 0o700)
    keep = d + ".was"
    os.rename(d, keep)
    os.symlink(target, d)
    r8 = rid("c8")
    fr.mk(recbp(ACC_ON, r8), "kept8\n")
    type_pause_hangup(ide("C8", ACC_ON, "bp " + r8), "LINKMARK")
    R.row("C8 $recovery is a LINK to a private directory of the user's: nothing is written through it (the target stays empty) and the link is left as it was",
          os.listdir(target) == [] and os.path.islink(d) and not holders(ACC_ON, "LINKMARK"), repr(os.listdir(target)), phase=PH)
    os.unlink(d)
    os.rename(keep, d)
    os.chmod(d, 0o755)
    r9 = rid("c9")
    fr.mk(recbp(ACC_ON, r9), "kept9\n")
    type_pause_hangup(ide("C9", ACC_ON, "bp " + r9), "OPENMARK")
    R.row("C9 $recovery readable by group and others (0755): no copy is written in it", not holders(ACC_ON, "OPENMARK"), repr(holders(ACC_ON, "OPENMARK")), phase=PH)
    os.chmod(d, 0o700)


def main():
    try:
        setup()
        section_rule()
        patch_rule()
        section_off()
        section_on()
        section_review()
        section_dir()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
