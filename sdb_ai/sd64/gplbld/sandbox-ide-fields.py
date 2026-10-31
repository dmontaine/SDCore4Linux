#!/usr/bin/env python3
#
# sandbox-ide-fields.py - the IDE's fields PANE (CED in the IDE, stage 2b, 30 Oct 2026) on a pseudo-terminal.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-fields.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.  The IDE runs at 140 by 43 (the owner's size for every full-screen feature), SDBOX_KEYSET as the other suites.
#
# START-HISTORY:
# 30 Oct 26 dm  Written with stage 2b, from Opus's FV1-FV15 (.claude/opus-decisions-30oct.md, Part B item 3) and the falsifiers of the review's risk list.  WRITTEN, NOT RUN.
# 31 Oct 26 dm  Section G (stage 4): Ctrl-T on the empty top level asks collection or array (G3 of the old CED) and the ids on the command line (G4).  The AI line in the fields view has no
#               row here (it needs an answering model: the free check test-fieldspane-units F2 holds its wiring).
# END-HISTORY
#
# WHAT IT PROVES.  F12 shows the tab's record as fields in the editor's rectangle of the IDE's own form, and the TAB'S TEXT IS THE RECORD: each change the pane makes is in the tab's text
# at once (the status line and the path line mark the tab changed, the disk is as it was), Ctrl-S is the IDE's save and writes what the pane shows, and F12 shows the text again.  The
# falsifiers: a tab switch with the pane on and Ctrl-S after it must still save the pane's edit (a stash from the hidden text area would write the old text over it); the commands that
# work on the text refuse while the pane is up (11998, "This works on the text of the record"); a JSON record is edited as the tree it is and saved as JSON; Left, Backspace and Esc go up;
# Q does not leave; Ctrl-T asks the type; F6 moves the focus round the panes with the table as the editor's pane; leaving gives the text area the new text as one undo step.
# Fixtures: bp records (a program file: no token form), made by a BASIC program the suite compiles and runs, and read back by a probe on the disk.

import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sb = _load("sandbox_ide_for_fields", "sandbox-ide.py")        # the IDE's pseudo-terminal driver (Ide) and its key names
rc = _load("sandbox_recarr_for_fields", "sandbox-recarr.py")  # the rectangle readers: elements, path_of, dirty_of, EDX

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = "%05d" % (os.getpid() % 100000)
F12, INS, CTRL_U = "\x1b[24~", "\x1b[2~", "\x15"
CTRL_C, CTRL_T, CTRL_Z, CTRL_L = "\x03", "\x14", "\x1a", "\x0c"
BACKSPACE = "\x7f"
passed = failed = 0


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-ide-fields: CANNOT RUN - " + msg)
    sys.exit(2)


FIX = """   open 'bp' to f else stop 'no bp'
   write 'Acme':@fm:'red':@vm:'dark':@sm:'green':@vm:'blue':@fm:'x' on f, 'zzfa%(r)s'
   write 'one':@fm:'two':@vm:'three' on f, 'zzfb%(r)s'
   write 'Acme':@fm:'red':@vm:'dark':@sm:'green':@vm:'blue':@fm:'x' on f, 'zzfc%(r)s'
   write 'Acme':@fm:'red':@vm:'dark':@sm:'green':@vm:'blue':@fm:'x' on f, 'zzfd%(r)s'
   write '{"a":1,"b":[true,null],"c":"x"}' on f, 'zzfj%(r)s'
   write '{}' on f, 'zzfe%(r)s'
   crt 'FIXTURE DONE'
end
"""

PROBE = """   open 'bp' to f else stop 'no bp'
   ids = 'a':@fm:'b':@fm:'c':@fm:'d'
   for i = 1 to 4
      read r from f, 'zzf' : ids<i> : '%(r)s' else r = '<absent>'
      crt 'REC':i:'[':convert(@fm:@vm:@sm:@tm, '^|~#', r):']'
   next i
   read r from f, 'zzfj%(r)s' else r = '<absent>'
   crt 'JLINES[':dcount(r, @fm):']'
   c = jparse(convert(@fm, char(10), r))
   crt 'JSTATUS[':status():']'
   crt 'JA[':c{'a'}:']'
   b = c{'b'}
   crt 'JBN[':inmat(b):']'
   crt 'JC[':c{'c'}:']'
   read r from f, 'zzfe%(r)s' else r = '<absent>'
   crt 'EMPTYREC[':r:']'
   crt 'END'
end
"""


def tag(out, name):
    m = re.search(r"(?m)^%s\[(.*)\]\s*$" % name, out)
    return None if m is None else m.group(1)


def jrows(L):
    """[(name, type, value)] of the pane for a JSON object: the rows between the header and the path line, names being keys."""
    out = []
    started = False
    for l in L:
        seg = rc._fcell(l)
        if not started:
            started = seg.lstrip().startswith("Name") and "Type" in seg and "Value" in seg
            continue
        if seg.lstrip().startswith("Path:"):
            break
        m = re.match(r"^\s*(\S+)\s+(string|number|boolean|null|collection|array)\s*(.*?)\s*$", seg)
        if m:
            out.append(m.groups())
    return out


def editor_rows(L):
    """The text area's rows (the rectangle under the tab strip down to the row above the messages bar), the border and the scroll bar cut off."""
    return [rc._fcell(l) for l in L[3:30]]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-ide-fields.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-ide-fields: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-fields: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    fix, probe = "zzffix" + RUN, "zzfprobe" + RUN
    ra, rb, rc_, rd, rj = ("zzf%s%s" % (c, RUN) for c in "abcdj")
    for nm, body in ((fix, FIX), (probe, PROBE)):
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body % {"r": RUN})
    out = sb.sess(box, "BASIC bp %s" % fix, "BASIC bp %s" % probe, "RUN bp %s" % fix)
    row("setup: the fixture and the probe compile and the records were written",
        len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == 2 and "FIXTURE DONE" in out, out[-400:])
    if "FIXTURE DONE" not in out:
        bail("the fixture was not made:\n" + out[-600:])

    def disk():
        o = sb.sess(box, "RUN bp %s" % probe)
        return {k: tag(o, k) for k in ("REC1", "REC2", "REC3", "REC4", "JLINES", "JSTATUS", "JA", "JBN", "JC", "EMPTYREC")}

    d0 = disk()
    row("control: the probe reads the records as written", d0["REC1"] == "Acme^red|dark~green|blue^x" and d0["REC2"] == "one^two|three" and d0["JA"] == "1" and d0["JBN"] == "2" and d0["JC"] == "x",
        repr(d0))

    # ---- P: the pane on a record: the view, the dive, an edit that is in the tab and not on the disk, Esc, Ctrl-S = the IDE's save, F12 back ----------------------------------------------------
    say("\n--- P: F12 shows the fields as a pane; the tab's text is the record; Ctrl-S is the IDE's save; F12 shows the text ---------------------")
    e = sb.Ide(box, "IDE bp %s" % ra)
    e.quiet()
    L = e.keys(F12)
    el = rc.elements(L)
    row("P1 F12 shows the record as fields in the editor's rectangle, with the tree, the tab strip and the messages pane still on the screen, the path / and the tab not changed",
        rc.path_of(L) == "/" and [(x[1], x[2], x[3]) for x in el] == [("1", "string", "Acme"), ("2", "array", "[3]"), ("3", "string", "x")] and "accounts" in L[2] and ("[%s]" % ra) in L[2]
        and any("Messages" in l[rc.EDX:] for l in L) and rc.dirty_of(L) is False and "red" not in "\n".join(editor_rows(L)), "%r %r" % (rc.path_of(L), el))
    st = e.status()
    row("P2 the status line names the pane as the editor and says the pane's keys (Return open, Esc up, Ctrl-T type, Ctrl-S save, F12 text)",
        st.startswith("[Editor]") and "Ctrl-T type" in st and "Ctrl-S save" in st and "F12 text" in st, st)
    L = e.keys(sb.DOWN, sb.RET)
    el = rc.elements(L)
    row("P3 Down and Return dive into field 2: the path is /2 and the rows are string red, array [2], string blue",
        rc.path_of(L) == "/2" and [(x[1], x[2], x[3]) for x in el] == [("1", "string", "red"), ("2", "array", "[2]"), ("3", "string", "blue")], "%r %r" % (rc.path_of(L), el))
    e.keys(sb.RET)
    L = e.keys(CTRL_U, "lemon", sb.RET)
    by = {x[1]: (x[2], x[3]) for x in rc.elements(L)}
    e.quiet()
    st = e.status()
    row("P4 an edit shows in the table (lemon), the path line and the IDE's status line mark the tab changed, and the disk is as it was",
        by.get("1") == ("string", "lemon") and rc.dirty_of(L) is True and re.search(r"bp %s \*" % ra, st) is not None and disk()["REC1"] == d0["REC1"], "%r %r %r" % (by, rc.dirty_of(L), st))
    L = e.keys(sb.ESC)
    row("P5 Esc goes up a level: back at /, with the three fields", rc.path_of(L) == "/" and len(rc.elements(L)) == 3, repr(rc.path_of(L)))
    e.keys(sb.CTRL_S)
    L = e.lines()
    st = e.status()
    d = disk()
    row("P6 Ctrl-S is the IDE's save: Saved on the status line, the star gone from the status line and the path line, and the record on the disk is Acme^lemon|dark~green|blue^x (the subvalue mark in place)",
        ("Saved bp %s" % ra) in st and re.search(r"bp %s \*" % ra, st) is None and rc.dirty_of(L) is False and d["REC1"] == "Acme^lemon|dark~green|blue^x", "%r %r" % (st, d["REC1"]))
    e.keys(F12)
    e.quiet()
    t = "\n".join(editor_rows(e.lines()))
    row("P7 F12 shows the text again: the pane is gone, the record as saved (lemon) is in the text area, and nothing is marked changed",
        rc.path_of(e.lines()) is None and "lemon" in t and re.search(r"bp %s \*" % ra, e.status()) is None, e.status() + "\n" + t[:300])
    e.end()

    # ---- Q: the keys of the pane ----------------------------------------------------------------------------------------------------------------------------------------------------------------
    say("\n--- Q: Left and Backspace go up, Q does not leave, Ctrl-T asks the type, F6 goes round the panes with the table as the editor ---------")
    e = sb.Ide(box, "IDE bp %s" % rb)
    e.quiet()
    e.keys(F12)
    L = e.keys(sb.DOWN, sb.RET)
    p1 = rc.path_of(L)
    L = e.keys(sb.LEFT)
    p2 = rc.path_of(L)
    L = e.keys(sb.DOWN, sb.RET)
    p3 = rc.path_of(L)                                 # Down on the last row must stay in the table (stay), so that this Return dives again
    L = e.keys(BACKSPACE)
    row("Q1 Left and Backspace each go up a level (the engine's Esc), and Down on the last row keeps the focus in the table: /2, /, /2 again, /",
        p1 == "/2" and p2 == "/" and p3 == "/2" and rc.path_of(L) == "/" and e.status().startswith("[Editor]"), "%r %r %r %r %r" % (p1, p2, p3, rc.path_of(L), e.status()[:30]))
    L = e.keys("Q")
    row("Q2 the engine's Q does not leave the pane: it is still up at /, with no question and the tab not changed", rc.path_of(L) == "/" and rc.dirty_of(L) is False and len(rc.elements(L)) == 2,
        "%r dirty=%r rows=%r status=%r" % (rc.path_of(L), rc.dirty_of(L), rc.elements(L), e.status()))
    L = e.keys(sb.UP)                                  # Up and Down are the table's: the selection is on field 2 (the array) after the dives above; field 1 is the string
    L = e.keys(CTRL_T)
    ch = rc.menu_choices(L)
    row("Q3 Ctrl-T on a string asks the type (the engine's F4; F4 is the IDE's next problem): a menu is drawn over the table, offering the other type, array (a field in a record is a string or an array)", "1=array" in ch, repr(ch))
    L = e.keys(sb.ESC)
    row("Q4 Esc leaves the menu: the pane is as it was and the tab is not changed", rc.path_of(L) == "/" and rc.dirty_of(L) is False, repr(rc.path_of(L)))
    L = e.keys(sb.F6)
    st1 = e.status()
    e.keys(sb.F6, sb.F6, sb.F6)
    st4 = e.status()
    L = e.keys(sb.DOWN, sb.RET)
    row("Q5 F6 goes round the panes: from the table to the messages pane and, after three more, back to the table, which is the editor pane ([Editor]) and still works (Return dives)",
        st1.startswith("[Messages]") and st4.startswith("[Editor]") and rc.path_of(L) in ("/1", "/2"), "%r %r %r" % (st1[:20], st4[:20], rc.path_of(L)))
    e.keys(F12)
    e.end()

    # ---- R: the commands that work on the text are refused while the pane is up --------------------------------------------------------------------------------------------------------------
    say("\n--- R: Replace, Go to line and the include are refused while the pane is up (11998), and change nothing -------------------------------")
    e = sb.Ide(box, "IDE bp %s" % rc_)
    e.quiet()
    e.keys(F12)
    for key, name in ((sb.CTRL_R, "Ctrl-R (Replace)"), (CTRL_L, "Ctrl-L (Go to line)")):
        L = e.keys(key)
        e.quiet()
        st = e.status()
        row("R1 %s says it works on the text of the record and asks nothing: no form on the screen, the pane is still up and the tab is not changed" % name,
            "works on the text of the record" in st and rc.path_of(L) == "/" and "Replace" not in "\n".join(L[10:30]) and rc.dirty_of(L) is False, st)
    e.keys(F12)
    e.end()

    # ---- T: tabs: the falsifier of a stash from the hidden text area -------------------------------------------------------------------------------------------------------------------------
    say("\n--- T: tab switches with the pane on keep each tab's own view, and Ctrl-S after them still saves the pane's edit -------------------------")
    e = sb.Ide(box, "IDE bp %s" % rd)
    e.quiet()
    e.keys(F12, sb.DOWN, sb.RET)
    e.keys(sb.RET)
    e.keys(CTRL_U, "lemon", sb.RET)
    e.keys(sb.CTRL_O)
    e.keys(rb, sb.RET)
    e.quiet()
    L = e.lines()
    t = "\n".join(editor_rows(L))
    row("T1 a second record opens in a tab of its own as TEXT (no pane, the text 'two' in the text area) while the first tab keeps its pane",
        ("[%s]" % rb) in L[2] and ("%s" % rd) in L[2] and rc.path_of(L) is None and "two" in t, L[2] + "\n" + t[:300])
    e.keys(sb.CTRL_PGUP)
    e.quiet()
    L = e.lines()
    by = {x[1]: x[3] for x in rc.elements(L)}
    row("T2 back on the first tab the pane is there at /2 with the edit (lemon) and the tab marked changed: the view, the path and the text are the tab's own",
        rc.path_of(L) == "/2" and by.get("1") == "lemon" and rc.dirty_of(L) is True, "%r %r" % (rc.path_of(L), by))
    e.keys(sb.CTRL_PGDN)
    e.keys("zz")
    e.quiet()
    e.keys(sb.CTRL_PGUP)
    e.quiet()
    L = e.lines()
    by = {x[1]: x[3] for x in rc.elements(L)}
    row("T3 typing in the other tab's text area changes nothing in the pane's tab: still /2 and lemon", rc.path_of(L) == "/2" and by.get("1") == "lemon", "%r %r" % (rc.path_of(L), by))
    e.keys(sb.CTRL_S)
    d = disk()
    row("T4 THE FALSIFIER: Ctrl-S after the switches saves the pane's edit - the record is Acme^lemon|dark~green|blue^x, not the old text a stash from the hidden text area would write",
        d["REC4"] == "Acme^lemon|dark~green|blue^x", repr(d["REC4"]))
    row("T5 ... and the other record, edited with zz and not saved, is as it was on the disk", d["REC2"] == d0["REC2"], repr(d["REC2"]))
    e.keys(F12)
    e.keys(sb.CTRL_PGDN)
    e.keys(sb.CTRL_W)
    e.keys("n")
    e.end()

    # ---- J: a JSON record is edited as the tree it is and saved as JSON ---------------------------------------------------------------------------------------------------------------------
    say("\n--- J: a JSON record in an ordinary file is edited as a tree and saved as JSON ---------------------------------------------------------")
    e = sb.Ide(box, "IDE bp %s" % rj)
    e.quiet()
    L = e.keys(F12)
    jr = jrows(L)
    row("J1 F12 on a JSON object shows its keys as rows: a number 1, b array [2], c string x", [(n, t_) for n, t_, v in jr] == [("a", "number"), ("b", "array"), ("c", "string")] and jr[0][2] == "1" and rc.path_of(L) == "/",
        repr(jr))
    e.keys(sb.RET)
    L = e.keys(CTRL_U, "2", sb.RET)
    jr = jrows(L)
    row("J2 a number is edited in place: a is 2 and the tab is marked changed; the disk is as it was", jr and jr[0][2] == "2" and rc.dirty_of(L) is True and disk()["JA"] == "1", repr(jr))
    e.keys(sb.CTRL_S)
    d = disk()
    row("J3 Ctrl-S saves JSON that parses (status 0) with a = 2, b still an array of two and c = x, laid out on several lines (the tree's pretty form)",
        d["JSTATUS"] == "0" and d["JA"] == "2" and d["JBN"] == "2" and d["JC"] == "x" and int(d["JLINES"] or 0) > 1, repr(d))
    e.keys(F12)
    e.end()

    # ---- U: the whole fields session is ONE undo step in the text area ---------------------------------------------------------------------------------------------------------------------
    say("\n--- U: Ctrl-Z in the text area takes the whole fields session back in one step --------------------------------------------------------")
    e = sb.Ide(box, "IDE bp %s" % rc_)
    e.quiet()
    e.keys(F12, sb.DOWN, sb.RET)
    e.keys(sb.RET)
    e.keys(CTRL_U, "plum", sb.RET)
    e.keys(sb.DOWN, sb.DOWN, sb.RET)
    e.keys(CTRL_U, "navy", sb.RET)
    e.keys(F12)
    e.quiet()
    t = "\n".join(editor_rows(e.lines()))
    row("U1 after two edits in the pane F12 shows both in the text (plum and navy) and says the record is changed, save it", "plum" in t and "navy" in t and "is changed, save it to keep it" in e.status(), e.status() + "\n" + t[:300])
    e.keys(CTRL_Z)
    e.quiet()
    t = "\n".join(editor_rows(e.lines()))
    row("U2 ONE Ctrl-Z brings back the record as it was (red, blue), and the tab is not marked changed again", "plum" not in t and "navy" not in t and "red" in t and re.search(r"bp %s \*" % rc_, e.status()) is None,
        e.status() + "\n" + t[:300])
    e.end()

    # ---- G: stage 4 (31 Oct 26): Ctrl-T on the empty top level (G3) and several ids on the command line (G4) ---------------------------------------------------------------------------
    say("\n--- G: Ctrl-T on an empty record asks collection or array; IDE file id id opens a tab each; IDE file * lists the file -----------------")
    re_ = "zzfe" + RUN
    e = sb.Ide(box, "IDE bp %s" % re_)
    e.quiet()
    L = e.keys(F12)
    row("G1 F12 on the JSON record {} shows the pane at / with no field in it and the tab not changed", rc.path_of(L) == "/" and len(rc.elements(L)) == 0 and rc.dirty_of(L) is False,
        "%r %r" % (rc.path_of(L), rc.elements(L)))
    L = e.keys(CTRL_T)
    row("G2 Ctrl-T on the empty top level asks 'collection or array' (the old CED's question: C = collection, A = array, Esc = cancel), not the 'cannot be changed' message",
        "A = array" in "\n".join(L) and "cannot be changed" not in e.status(), e.status())
    L = e.keys(sb.ESC)
    row("G3 Esc leaves it as it was: the tab is not changed", rc.path_of(L) == "/" and rc.dirty_of(L) is False, repr(rc.dirty_of(L)))
    e.keys(CTRL_T)
    L = e.keys("a")
    row("G4 A makes the record an array: the tab is changed and the disk is still {}", rc.dirty_of(L) is True and disk()["EMPTYREC"] == "{}", "%r %r" % (rc.dirty_of(L), disk()["EMPTYREC"]))
    e.keys(sb.CTRL_S)
    row("G5 Ctrl-S writes [] - the empty array", disk()["EMPTYREC"] == "[]", repr(disk()["EMPTYREC"]))
    e.keys(F12)
    e.end()
    e = sb.Ide(box, "IDE bp %s %s" % (ra, rb))
    e.quiet()
    L = e.lines()
    st = e.status()
    row("G6 IDE bp id1 id2 opens a tab for each record named (both names on the tab strip) and says how many are listed and open", ("[%s]" % ra) in L[2] and ("[%s]" % rb) in L[2] or (ra in L[2] and rb in L[2]),
        L[2] + " | " + st)
    row("G7 ... in the words of message 11919, not the select list's", "record(s) are listed below; the first 2 are open in tabs" in st, st)
    e.end()
    e = sb.Ide(box, "IDE bp *")
    e.quiet()
    st = e.status()
    row("G8 IDE bp * lists the records of the file and opens the first ten in tabs", "record(s) are listed below; the first 10 are open in tabs" in st, st)
    e.end()

    say("\nsandbox-ide-fields: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
