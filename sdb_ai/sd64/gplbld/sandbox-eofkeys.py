#!/usr/bin/env python3
#
# sandbox-eofkeys.py - SED, the IDE, ED and a user program's SCREEN WAIT end when their input ends.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-eofkeys.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# MUTANTS.  --mutant=NAME takes one change of the ED fix out of the SANDBOX's copy of `ed` (never the tree), compiles it and runs the ED
# rows only, with record ids of their own (the name is added to each), so that several can be run one after another in one sandbox; the
# rows that must FAIL are listed with each (MUTANTS below).  `--mutant=whole` takes all of the fix out: the new ED rows go red and the
# controls stay green, which is the tree before the fix.  The sandbox's `ed` is put back from its own copy of the tree at the start of
# every run.  Mutants are made with `sd -internal` as the sandbox user, who is its administrator.
#
# START-HISTORY:
# 19 Oct 26 dm  Written for the verifier's finding F8 of the 140x42 branch (owner: "fix 100% cpu problem"): a SED or IDE session whose
#               input was a pipe that had ended spun at 100% CPU for as long as it was let run (8.0 s of CPU in 8.3 s, measured on
#               the merged tree before the fix).  Two causes: SED's key loop took the null key of an ended input for "no key yet"
#               and asked again; $sl_form's wait turned the null key into a TIMEOUT event whenever the caller had given a timeout,
#               and the IDE waits a second at a time.
# 19 Oct 26 dm  ED, the classic line editor, added (it spun the same way: `ed zzcpu e5` with the input closed ran 6.1 s of CPU in 6.1 s,
#               printing the `----:` prompt for ever, because its command loop took the '' of an ended INPUT for an empty command).
#               Rows for the command prompt, text typed then the input ending (nothing written, lock given back), the "Record changed
#               - OK to quit?" question, a list of record ids (ED stops at the first), LOAD from an empty record (its start-line
#               prompt cannot be satisfied), the destructive default (FD answered by the end of the input keeps the record), the
#               controls that already ended, and one row on a PSEUDO-TERMINAL: an empty Enter on a real terminal still does not leave.
#               pipe_session keeps only the first and last 100 KB of a big output, since a spinning ED writes tens of megabytes.
#               --mutant=NAME added (nine mutants of the ED change, each killed by its own rows, below).  A session that is still there at
#               the deadline is hung up before it is killed (the first mutant runs killed ~60 sessions and the next ones could not start:
#               "User limit reached").
# END-HISTORY
#
# THE INSTRUMENT.  Each session is the sandbox's `sd` started as a child with a PIPE for its input: the lines, then the pipe is CLOSED, so
# the input ends and there is no OFF line to end the session politely.  The child is waited for with wait4(), so its own user + system CPU
# comes back (not the CPU of everything this script ever started), and it is HUNG UP after 8 s if it is still there (SIGHUP, as closing a
# terminal window does: SD ends and gives its user slot and record locks back; one that ignores that for 3 s is killed and `sd -cleanup`
# is run, since a killed session keeps its row in the user table and a sandbox with ~100 of them answers "User limit reached").  A row that
# judges "ended by itself" first checks that the program really started (a word only that program draws), so a session that never
# got as far as the program cannot pass; the numbers (wall seconds, CPU seconds) are printed in every row.
#
# NOT HERE: that a timeout still happens as a timeout.  A pipe has no timeouts (keyin() reads with no limit when the input is not a
# terminal), so the other direction is `sandbox-screen.py` (the wait that times out: ELSE timeout) and `sandbox-ide.py` (the status line
# follows what is typed, which is the IDE's one-second timeout) on a pseudo-terminal.  ED's one pseudo-terminal row is here, because
# its risk is the other direction: an empty Enter at a real terminal's prompt must still be an empty command, not the end of the input.
# ED rows use a record id of their own each, because a session that is killed keeps the lock on the record it was editing.

import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
DEADLINE = 8.0          # seconds a session may take before it is killed
CPU_OK = 3.0            # CPU seconds a session that ended by itself may have used
KEEP = 100000           # bytes kept from each end of a very big output
TAG = ""                # added to every record id the ED rows use: a mutant run takes ids of its own (a killed session keeps its lock)


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
    say("sandbox-eofkeys: CANNOT RUN - " + msg)
    sys.exit(2)


def pipe_session(box, label, *lines):
    """Run the sandbox's sd with these lines on a pipe that is then closed.  Returns (ended, wall, cpu, text)."""
    sysd = os.path.join(box, "sys")
    sd = os.path.join(sysd, "bin", "sd")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "TERM 140,42\n" + "".join(l + "\n" for l in lines)
    outf = os.path.join(box, "eofkeys-%s.out" % label)
    killed = []
    wall_at_deadline = 0.0
    say("    > %s  (cwd %s, input %s, then the pipe is closed)" % (sd, sysd, repr(body)))
    with open(outf, "wb") as fo:
        p = subprocess.Popen([sd], cwd=sysd, env=env, stdin=subprocess.PIPE, stdout=fo, stderr=subprocess.STDOUT)
        p.stdin.write(body.encode())
        p.stdin.close()
        t0 = time.time()
        while True:
            wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
            if wpid:
                ended = True
                break
            if time.time() - t0 > DEADLINE:
                ended = False
                wall_at_deadline = time.time() - t0
                # HUNG UP first, as closing a terminal window does, so that SD ends cleanly and gives its user slot and its record
                # locks back; a kill leaves both (a sandbox that has had a hundred killed sessions answers "User limit reached")
                os.kill(p.pid, signal.SIGHUP)
                t1 = time.time()
                while time.time() - t1 < 3.0:
                    wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
                    if wpid:
                        break
                    time.sleep(0.05)
                else:
                    os.kill(p.pid, signal.SIGKILL)
                    _w, _status, ru = os.wait4(p.pid, 0)
                    killed.append(p.pid)
                break
            time.sleep(0.05)
        p.returncode = 0                      # (waited for here, not by Popen)
    wall = wall_at_deadline if not ended else time.time() - t0
    cpu = ru.ru_utime + ru.ru_stime
    if killed:
        subprocess.run([sd, "-cleanup"], cwd=sysd, env=env, capture_output=True, timeout=60)
        say("    (the session ignored the hang-up and was killed; sd -cleanup run)")
    size = os.path.getsize(outf)
    with open(outf, "rb") as fi:
        if size > 2 * KEEP:               # a program that spins writes tens of megabytes: judge the first and the last of it
            head = fi.read(KEEP)
            fi.seek(size - KEEP)
            raw = head + b"\n[... %d bytes not kept ...]\n" % (size - 2 * KEEP) + fi.read()
        else:
            raw = fi.read()
    os.remove(outf)
    text = ANSI.sub("", raw.decode("utf-8", "replace"))
    say("    < %d bytes of output" % size)
    return ended, wall, cpu, text


def judge(name, started_re, res):
    """Two rows: the program started (so the next row is about it), and it ended by itself without spinning."""
    ended, wall, cpu, text = res
    started = re.search(started_re, text) is not None
    row("%s: it started (%s)" % (name, started_re), started, repr(text[-300:]))
    row("%s: it ended by itself, within %.0f s, using under %.0f s of CPU   [wall %.1f s, cpu %.1f s]" % (name, DEADLINE, CPU_OK, wall, cpu),
        started and ended and cpu < CPU_OK, "ended=%s wall=%.1f cpu=%.1f" % (ended, wall, cpu))


PROG = (
    "   screen open clear else\n      crt 'OPENFAILED'\n      stop\n   end\n"
    "   screen form title 'Eof' at 10,3 size 30,6 returning f\n"
    "   screen button f, 'ok', '&OK' at 2,4 default\n"
    "   n = 0\n   last = ''\n"
    "   loop\n"
    "      screen wait f timeout 1 returning ev then\n         last = 'event ':ev<1>\n      end else\n         last = ev<1>\n      end\n"
    "      n += 1\n"
    "   until last = 'end' or n >= 2000 do\n   repeat\n"
    "   screen close\n"
    "   crt 'EOFLAST[':last:'] EOFN[':n:']'\n"
    "end\n")

# The records ED is run on: an existing one of three lines for each row that edits it (a changed record must stay as it was; a session
# that was killed keeps the lock on the record it was editing, so a control row never edits a record an earlier row did), one to LOAD
# lines from (esrc1: it is read, not locked) and an empty one for LOAD.  Written by a program, not by ED, so that the thing under
# test does not make its own fixture.
PROGW = (
    "   open 'zzeof' to f else\n      crt 'WOPENFAILED'\n      stop\n   end\n"
    "   rec = 'one':@fm:'two':@fm:'three'\n"
    "   write rec to f, 'ec1%(t)s'\n"
    "   write rec to f, 'eq1%(t)s'\n"
    "   write rec to f, 'efd1%(t)s'\n"
    "   write rec to f, 'eov2%(t)s'\n"
    "   write rec to f, 'esrc1%(t)s'\n"
    "   write rec to f, 'eul1%(t)s'\n"
    "   write '' to f, 'eempty1%(t)s'\n"
    "   crt 'WROTE'\n"
    "end\n")


def rid(base):
    """A record id of the ED rows: the base name and the run's tag (empty except in a mutant run)."""
    return base + TAG


# The changes of the fix to ED, one by one.  Each is (old text, new text) in the sandbox's copy of `ed`, the old text occurring exactly once.
# The rows that must FAIL with it (and no others) are named.
FIX_MAIN = ("            if new.command = '' and status() = ER$EOF then\n", "            if 0 then\n")
FIX_LIST = ("         while more.ids and not(input.ended)\n", "         while more.ids\n")
FIX_NAME = ("         until input.ended      ;* (else the prompt for the next name would be shown once more, to an input that has ended)\n", "")
FIX_LOAD1 = ("            if n = '' and status() = ER$EOF then return\n            if len(n) = 0 then n = 1\n         while not(num(n)) or (n < 1) or (n > n.lines)\n",
             "            if len(n) = 0 then n = 1\n         while not(num(n)) or (n < 1) or (n > n.lines)\n")
FIX_LOAD2 = ("            if i = '' and status() = ER$EOF then return\n            if len(i) = 0 then i = n.lines\n",
             "            if len(i) = 0 then i = n.lines\n")
FIX_UNLOAD1 = ("            if n = '' and status() = ER$EOF then return\n            if len(n) = 0 then n = 1\n         while not(num(n)) or (n < 1) or (n > lines)\n",
               "            if len(n) = 0 then n = 1\n         while not(num(n)) or (n < 1) or (n > lines)\n")
FIX_UNLOAD2 = ("            if i = '' and status() = ER$EOF then return\n            if len(i) = 0 then i = lines\n",
               "            if len(i) = 0 then i = lines\n")
# The wrong fix: any empty line leaves, so that an Enter on a terminal would end ED.
WRONG_EMPTY = ("            if new.command = '' and status() = ER$EOF then\n", "            if new.command = '' then\n")

# name: [changes], rows that must fail
MUTANTS = {
    "nomain": ([FIX_MAIN], "every row that reaches the command prompt: new record, typed text and its lock, changed record and its lock, X, FD, "
                           "the first of three ids, record named at the prompt, LOAD / UNLOAD after their cancel"),
    "nolist": ([FIX_LIST], "three record ids: it stopped at the first"),
    "noname": ([FIX_NAME], "record named at the prompt: asked for a name once"),
    "noload1": ([FIX_LOAD1], "LOAD from an empty record (both its rows: it spins)"),
    "noload2": ([FIX_LOAD2], "LOAD answered at the start-line prompt: nothing is loaded"),
    "nounload1": ([FIX_UNLOAD1], "UNLOAD, the input ends at the start-line prompt: the end-line prompt was not shown"),
    "nounload2": ([FIX_UNLOAD2], "UNLOAD answered at the start-line prompt: nothing was written"),
    "emptyleaves": ([WRONG_EMPTY], "terminal: three empty Enters (ED must still be running)"),
    "whole": ([FIX_MAIN, FIX_LIST, FIX_NAME, FIX_LOAD1, FIX_LOAD2, FIX_UNLOAD1, FIX_UNLOAD2],
              "all the new ED rows; the CONTROL rows and the terminal rows stay green"),
}


def internal(box, *cmds):
    """sd -internal in the sandbox's sys directory (the sandbox user is its administrator): for compiling the mutants."""
    sysd = os.path.join(box, "sys")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    say("    > [internal] " + " | ".join(cmds))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(sysd, "bin", "sd"), "-internal"], input=body, cwd=sysd, env=env, capture_output=True,
                       text=True, errors="replace", timeout=600)
    return ANSI.sub("", p.stdout + p.stderr)


def put_ed(box, changes):
    """Make the sandbox's `ed` the tree's copy of it with these changes (none: as it was built) and compile it, unless it already is that."""
    orig = os.path.join(box, "tree", "sdsys", "gpl.bp", "ed")
    path = os.path.join(box, "sys", "gpl.bp", "ed")
    with open(orig, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    for old, new in changes:
        if text.count(old) != 1:
            bail("a change to ED is in %d places in the sandbox's copy of ed, not 1:\n%s" % (text.count(old), old))
        text = text.replace(old, new)
    with open(path, encoding="utf-8", errors="replace") as fh:
        now = fh.read()
    if now == text:
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    out = internal(box, "BASIC gpl.bp ed")
    if "Compiled 1 program(s) with no errors" not in out:
        bail("ed did not compile after the change:\n" + out[-600:])
    return True


def record_state(box, label, rec):
    """What `ct zzeof <rec>` shows: the record's lines, or "Record 'x' not found"."""
    _e, _w, _c, ct = pipe_session(box, label + "ct", "ct zzeof " + rec)
    return ct


def ed_rows(box, sysd, made):
    R = rid
    say("\n  ED, the classic line editor: INPUT gives '' with STATUS() = ER$EOF when the input has ended")
    with open(os.path.join(sysd, "bp", "zzeofw"), "w") as fh:
        fh.write(PROGW % {"t": TAG})
    made.append("zzeofw")
    _e, _w, _c, text = pipe_session(box, "edsetup", "basic bp zzeofw", "run bp zzeofw")
    row("ED setup: the fixture records were written (ec1, eq1, efd1, eov2, esrc1, eul1 of three lines, eempty1)",
        "Compiled 1 program(s) with no errors" in text and "WROTE" in text and "WOPENFAILED" not in text, repr(text[-300:]))
    _e, _w, _c, text = pipe_session(box, "edsetupct", "ct zzeof " + R("ec1"))
    row("ED setup: ec1 holds one, two, three", all(w in text for w in ("one", "two", "three")), repr(text[-300:]))

    # (A row about what is on the disk afterwards also wants the session to have ENDED: a session that was killed after 8 s has not
    # yet been asked anything, so "the record is as it was" would pass for the wrong reason.)
    say("\n  ED, a new record: the command prompt")
    res = pipe_session(box, "ed1", "ed zzeof " + R("ea"))
    judge("ED, a new record", r"New record", res)

    say("\n  ED, a new record with text typed (INSERT, then the input ends)")
    res = pipe_session(box, "ed2", "ed zzeof " + R("eb"), "i", "hello", "")
    judge("ED with typed text", r"New record", res)
    ct = record_state(box, "ed2", R("eb"))
    row("ED with typed text: the session ended and the text was not written to the record (nobody was there to answer)",
        res[0] and "Record '%s' not found" % R("eb") in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))
    ended, wall, cpu, text = pipe_session(box, "ed2b", "ed zzeof " + R("eb"))
    row("ED with typed text: the record's lock was given back (a second ED opens it as a new record, and ends)",
        ended and "New record" in text and "locked" not in text, "ended=%s %s" % (ended, repr(text[-300:])))

    say("\n  ED, an existing record that is changed (INSERT, then the input ends)")
    res = pipe_session(box, "ed3", "ed zzeof " + R("ec1"), "i", "zzz", "")
    judge("ED on an existing record, changed", r"3 line\(s\)", res)
    ct = record_state(box, "ed3", R("ec1"))
    row("ED on an existing record, changed: the session ended and the record on disk is as it was",
        res[0] and all(w in ct for w in ("one", "two", "three")) and "zzz" not in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))
    ended, wall, cpu, text = pipe_session(box, "ed3b", "ed zzeof " + R("ec1"))
    row("ED on an existing record, changed: the lock was given back (a second ED opens it, and ends)",
        ended and re.search(r"3 line\(s\)", text) is not None and "locked" not in text, "ended=%s %s" % (ended, repr(text[-300:])))

    say("\n  ED, X after a change asks 'OK to quit?' and the end of the input is the answer")
    res = pipe_session(box, "ed4", "ed zzeof " + R("eq1"), "i", "zzz", "", "x")
    judge("ED, X on a changed record", r"Record changed - OK to quit\?", res)
    ct = record_state(box, "ed4", R("eq1"))
    row("ED, X on a changed record: the session ended and the record on disk is as it was",
        res[0] and all(w in ct for w in ("one", "two", "three")) and "zzz" not in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))

    say("\n  ED, FD asks 'Are you sure' and the end of the input is NOT a yes")
    res = pipe_session(box, "ed5", "ed zzeof " + R("efd1"), "fd")
    judge("ED, FD", r"Are you sure you want to delete the entire record", res)
    ct = record_state(box, "ed5", R("efd1"))
    row("ED, FD: the session ended and the record was not deleted (the end of the input answers no)",
        res[0] and all(w in ct for w in ("one", "two", "three")) and "not found" not in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))

    say("\n  ED, SAVE under another name that is in use asks 'Overwrite?' and the end of the input is NOT a yes")
    res = pipe_session(box, "ed5b", "ed zzeof " + R("eov1"), "i", "zzz", "", "save " + R("eov2"))
    judge("ED, SAVE over an existing record", r"Record already exists\. Overwrite", res)
    ct = record_state(box, "ed5b", R("eov2"))
    row("ED, SAVE over an existing record: the session ended and the record was not overwritten",
        res[0] and all(w in ct for w in ("one", "two", "three")) and "zzz" not in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))

    say("\n  ED, three record ids: the first is opened, the input ends, and ED does not go on to the others")
    res = pipe_session(box, "ed6", "ed zzeof %s %s %s" % (R("el1"), R("el2"), R("el3")))
    judge("ED, three record ids", r"(?m)^zzeof " + R("el1"), res)
    ended, wall, cpu, text = res
    # (The header of a record that is opened after the prompt continues the prompt's line, so it is looked for anywhere, not at a line's
    # start; the command line the session echoes holds "zzeof el1 el2 el3", which has neither "zzeof el2" nor "zzeof el3" in it.)
    row("ED, three record ids: it stopped at the first (el2 and el3 were not opened)",
        ended and re.search(r"(?m)^zzeof " + R("el1"), text) is not None and ("zzeof " + R("el2")) not in text and ("zzeof " + R("el3")) not in text,
        "ended=%s %s" % (ended, repr(text[-300:])))

    say("\n  ED, a record named at the 'Record name?' prompt: ED asks for the next name only while there is an input")
    res = pipe_session(box, "ed6b", "ed zzeof", R("enm1"))
    judge("ED, a record named at the prompt", r"New record", res)
    ended, wall, cpu, text = res
    row("ED, a record named at the prompt: it asked for a name once (not again after the input had ended)   [%d times]" % text.count("Record name?"),
        ended and text.count("Record name?") == 1, "ended=%s %s" % (ended, repr(text[-300:])))

    say("\n  ED, LOAD from an empty record: the start-line prompt can never be satisfied, so only the end of the input leaves it")
    res = pipe_session(box, "ed7", "ed zzeof " + R("ef"), "load zzeof " + R("eempty1"))
    judge("ED, LOAD from an empty record", r"Start line number", res)
    row("ED, LOAD from an empty record: cancelled at the first prompt (the end-line prompt was not shown)",
        res[0] and "End line number" not in res[3], "ended=%s %s" % (res[0], repr(res[3][-300:])))

    say("\n  ED, LOAD answered at the start-line prompt, the input ends at the end-line prompt: nothing is loaded")
    res = pipe_session(box, "ed7b", "ed zzeof " + R("ef2"), "load zzeof " + R("esrc1"), "2")
    judge("ED, LOAD, start answered", r"End line number", res)
    row("ED, LOAD, start answered: nothing was loaded (no 'lines loaded' message)",
        res[0] and "lines loaded from" not in res[3], "ended=%s %s" % (res[0], repr(res[3][-300:])))

    say("\n  ED, UNLOAD: the end of the input is not an answer that writes a record (a human's Enter would take the whole record)")
    res = pipe_session(box, "ed8", "ed zzeof " + R("eu1"), "i", "text", "", "unload zzeof " + R("eu2"))
    judge("ED, UNLOAD", r"Start line number", res)
    ct = record_state(box, "ed8", R("eu2"))
    row("ED, UNLOAD: the session ended and nothing was written to the target record",
        res[0] and "Record '%s' not found" % R("eu2") in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))
    row("ED, UNLOAD: cancelled at the first prompt (the end-line prompt was not shown)",
        res[0] and "End line number" not in res[3], "ended=%s %s" % (res[0], repr(res[3][-300:])))

    say("\n  ED, UNLOAD answered at the start-line prompt, the input ends at the end-line prompt: nothing is written")
    res = pipe_session(box, "ed8b", "ed zzeof " + R("eu3"), "i", "text", "", "unload zzeof " + R("eu4"), "1")
    judge("ED, UNLOAD, start answered", r"End line number", res)
    ct = record_state(box, "ed8b", R("eu4"))
    row("ED, UNLOAD, start answered: the session ended and nothing was written to the target record",
        res[0] and "Record '%s' not found" % R("eu4") in ct, "ended=%s %s" % (res[0], repr(ct[-300:])))

    say("\n  CONTROLS: the line-range prompts of LOAD and UNLOAD still take typed answers")
    res = pipe_session(box, "edl", "ed zzeof " + R("ecl1"), "load zzeof " + R("esrc1"), "2", "3", "fi")
    ct = record_state(box, "edl", R("ecl1"))
    row("CONTROL: LOAD of lines 2 to 3 answered at the prompts puts those two lines in the record (filed with FI)",
        res[0] and re.search(r"(?m)^1: two", ct) is not None and re.search(r"(?m)^2: three", ct) is not None and ": one" not in ct,
        "ended=%s %s" % (res[0], repr(ct[-300:])))
    res = pipe_session(box, "edu", "ed zzeof " + R("eul1"), "unload zzeof " + R("ecu1"), "1", "2", "q")
    ct = record_state(box, "edu", R("ecu1"))
    row("CONTROL: UNLOAD of lines 1 to 2 answered at the prompts writes those two lines to the target record",
        res[0] and re.search(r"(?m)^1: one", ct) is not None and re.search(r"(?m)^2: two", ct) is not None and ": three" not in ct,
        "ended=%s %s" % (res[0], repr(ct[-300:])))

    say("\n  CONTROLS: prompts that already ended at the end of the input")
    res = pipe_session(box, "edc1", "ed")
    judge("CONTROL: ED with no file name", r"File name\?", res)
    res = pipe_session(box, "edc2", "ed zzeof")
    judge("CONTROL: ED with no record name", r"Record name\?", res)
    res = pipe_session(box, "edc3", "select zzeof", "ed zzeof")
    judge("CONTROL: ED with an active select list", r"Use active select list", res)

    say("\n  ON A TERMINAL an empty Enter is an empty command: ED stays (the end of the input is not an empty line)")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
    s = PtySession([os.path.join(sysd, "bin", "sd")], sysd, env, 140, 42)
    try:
        s.settle(1.0)
        s.type("TERM xterm\r")
        s.type("TERM 140,42\r")
        s.type("ed zzeof %s\r" % R("pt1"), idle=0.8)
        s.type("\r", idle=0.5)
        s.type("\r", idle=0.5)
        s.type("\r", idle=0.5)
        scr = [l.rstrip() for l in s.screen.lines() if l.strip()]
        say("    screen: " + repr(scr[-6:]))
        prompts = [l for l in scr if l.startswith("----:")]
        row("terminal: after three empty Enters ED is still running and has shown its prompt four times   [%d prompts]" % len(prompts),
            not s.exited and len(prompts) >= 4 and any(l.startswith("New record") for l in scr), repr(scr[-6:]))
        s.type("x\r", idle=0.8)
        scr = [l.rstrip() for l in s.screen.lines() if l.strip()]
        row("terminal: X (nothing changed) leaves ED for the command prompt, and the session is still there",
            not s.exited and scr and scr[-1].startswith(":") and scr[-1].strip() == ":", repr(scr[-4:]))
    finally:
        s.type("OFF\r", idle=0.5)
        s.finish()


def main():
    global TAG
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-eofkeys.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("no mutant %s (%s)" % (mutant, ", ".join(MUTANTS)))
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-eofkeys: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-eofkeys: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # `ed` as the tree has it (a mutant run changes it in the sandbox's copy; the next run puts it back before it starts)
    if mutant is None:
        if put_ed(box, []):
            say("sandbox-eofkeys: the sandbox's ed was put back as the tree has it")
    else:
        changes, rows = MUTANTS[mutant]
        put_ed(box, changes)
        TAG = "_" + mutant
        say("sandbox-eofkeys: MUTANT %s: %d change(s) taken out of the sandbox's ed; ED rows only, record ids tagged %s.\n"
            "  Rows that must FAIL: %s" % (mutant, len(changes), TAG, rows))

    made = []
    try:
        if mutant is not None:
            ended, wall, cpu, text = pipe_session(box, "setup", "create.file zzeof")
            row("setup: the file zzeof was made", "Created DATA part as zzeof" in text and ended, repr(text[-300:]))
            ed_rows(box, sysd, made)
            say("\nsandbox-eofkeys: mutant %s: %d rows passed, %d failed (the failed ones are the rows it breaks)" % (mutant, passed, failed))
            return 0
        with open(os.path.join(sysd, "bp", "zzeofu"), "w") as fh:
            fh.write(PROG)
        made.append("zzeofu")

        ended, wall, cpu, text = pipe_session(box, "setup", "create.file zzeof", "basic bp zzeofu")
        row("setup: the file zzeof was made", "Created DATA part as zzeof" in text and ended, repr(text[-300:]))
        row("setup: the probe program compiles with no errors", "Compiled 1 program(s) with no errors" in text, repr(text[-300:]))

        say("\n  SED, a new record")
        res = pipe_session(box, "sed1", "sed zzeof t1")
        judge("SED", r"File\s+Edit\s+Search\s+Buffer\s+Window\s+Tools", res)

        say("\n  SED, a record with typed text in it (the buffer is changed)")
        res = pipe_session(box, "sed2", "sed zzeof t2", "hello")
        judge("SED with typed text", r"File\s+Edit\s+Search\s+Buffer\s+Window\s+Tools", res)
        _e, _w, _c, text = pipe_session(box, "ct2", "ct zzeof t2")
        row("SED with typed text: the text was not written to the record (nobody was there to answer 'save?')",
            "Record 't2' not found" in text, repr(text[-300:]))
        _e, _w, _c, text = pipe_session(box, "sed2b", "sed zzeof t2")
        row("SED with typed text: the record's lock was given back (a second session opens it as a new record)",
            "New record" in text and "locked" not in text, repr(text[-400:]))

        say("\n  the IDE")
        res = pipe_session(box, "ide1", "ide")
        judge("IDE", r"IDE: sdsys", res)
        res = pipe_session(box, "ide2", "ide zzeof t5")
        judge("IDE with a record named", r"IDE: sdsys", res)

        say("\n  a user program: SCREEN WAIT f TIMEOUT 1 in a loop")
        res = pipe_session(box, "user", "run bp zzeofu")
        ended, wall, cpu, text = res
        m = re.search(r"EOFLAST\[(.*?)\] EOFN\[(\d+)\]", text)
        row("user program: it ran to its end (the line it prints was found)", m is not None, repr(text[-300:]))
        row("user program: the wait answered END, not TIMEOUT, when the input had ended   [last %s, waits %s]" %
            (m.group(1) if m else "?", m.group(2) if m else "?"), m is not None and m.group(1) == "end", repr(m.group(0) if m else None))
        row("user program: ... at once, with little CPU   [wall %.1f s, cpu %.1f s]" % (wall, cpu), ended and cpu < CPU_OK,
            "ended=%s wall=%.1f cpu=%.1f" % (ended, wall, cpu))

        ed_rows(box, sysd, made)

        say("\n  CONTROL: CED already ended at the end of input")
        res = pipe_session(box, "ced", "ced zzeof c1")
        ended, wall, cpu, text = res
        row("CONTROL: CED ended by itself and its screen was drawn (the word array)", ended and cpu < CPU_OK and "array" in text,
            "ended=%s wall=%.1f cpu=%.1f %s" % (ended, wall, cpu, repr(text[-200:])))
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        pipe_session(box, "clean", "delete.file zzeof")

    say("\nsandbox-eofkeys: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
