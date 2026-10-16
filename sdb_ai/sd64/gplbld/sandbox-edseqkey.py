#!/usr/bin/env python3
#
# sandbox-edseqkey.py - ED and SED take CREATING.SEQKEY in the place of a record id.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-edseqkey.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent); without it <dir> must already be built, which is how the same script is run against an OLD tree to prove
# it can fail.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Stop the sandbox afterwards with
# sandbox-fromtree.py <dir> stop (SDBOX_KEYSET=n the same as for the build).
#
# START-HISTORY:
# 15 Oct 26 dm  Written with the CREATING.SEQKEY option of ED and SED (openQM 4: "Use of CREATING.SEQKEY instead of a
#               record id automatically generates the next sequential key for the file"), gpl.bp/seqkey.
# END-HISTORY
#
# HOW IT DRIVES THE EDITORS.  ED, the line editor, is driven through a pipe, one command to a line, as sandbox-collfile.py
# does.  SED is driven on a PSEUDO-TERMINAL (ptydrive.py) at 120 by 36, its one size, and its screen is read from the
# emulator in termscreen.py.  What each editor DID is read from the disk afterwards by a BASIC probe (the counter, from
# FILEINFO(f, 1031), and every record of the data part, the dictionary part, a directory file and a collection file), not
# from what the editor printed; what the editor printed is read for the id it showed and for the words of a refusal.
# Each row that changes something has a control row before it: the counter and the records as they were.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
H = "zzsqh" + RUN                  # a hashed file
D = "zzsqd" + RUN                  # a directory file
C = "zzsqc" + RUN                  # a data collection file (a hashed file as well)
R = "zzsqr" + RUN                  # a VOC entry for H with the letter R in field 6: the same file, opened read-only
FIX, PRB = "zzsqfx" + RUN, "zzsqpr" + RUN
passed = failed = 0

ESC, RET = "\x1b", "\r"
CTRL = lambda ch: chr(ord(ch.upper()) - 64)         # noqa: E731

REFUSED = "creating.seqkey cannot give it a record id"     # message 11352
READONLY = "File is read-only"                              # message 1431


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
    say("sandbox-edseqkey: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, one line to a command.  The output is shown (not the echoes) and returned."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = out.split(":TERM 200,9999", 1)[-1]
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit "):
            say("      | " + line.rstrip()[:140])
    return out


class Term:
    """One run of a command on a pseudo-terminal: type to it, read its screen."""

    def __init__(self, box, cmd, cols=120, rows=36):          # SED is 120 by 36 always, and refuses a smaller window
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.0)

    def keys(self, *chunks, idle=0.5):
        for chunk in chunks:
            self.s.type(chunk, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def text(self):
        return "\n".join(l.rstrip() for l in self.lines() if l.strip())

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


# What the disk holds.  The probe prints LAST <label> <FILEINFO 1031> and REC <label> <id> <text, lines joined by |> for
# each of: H's data part (H), H's dictionary (HD), the directory file (D) and the collection file (C).
PROBE = """$include keys.h
   names = '%(h)s' : @fm : 'DICT %(h)s' : @fm : '%(d)s' : @fm : '%(c)s'
   labs = 'H' : @fm : 'HD' : @fm : 'D' : @fm : 'C'
   for k = 1 to 4
      open names<k> to f then
         crt 'LAST ' : labs<k> : ' [' : fileinfo(f, FL$SEQ.KEY) : ']'
         select f to 9
         readlist ids from 9 else ids = ''
         for i = 1 to dcount(ids, @fm)
            id = ids<i>
            read r from f, id then
               if jtype(r) = 'string' then t = convert(@fm, '|', r) else t = jbuild(r)
               crt 'REC ' : labs<k> : ' ' : id : ' [' : t : ']'
            end
         next i
      end else
         crt 'LAST ' : labs<k> : ' <not open>'
      end
   next k
   crt 'PROBE DONE'
end
"""

FIXTURE = """   execute 'DELETE.FILE %(h)s' capturing j0
   execute 'DELETE.FILE %(d)s' capturing j1
   execute 'DELETE.FILE %(c)s' capturing j2
   execute 'CREATE.FILE %(h)s' capturing j3
   execute 'CREATE.FILE %(d)s DIRECTORY' capturing j4
   execute 'CREATE.FILE %(c)s COLLECTION' capturing j5
   open 'voc' to v else stop 'no voc'
   read e from v, '%(h)s' else stop 'no voc entry'
   e<6> = 'R'
   write e on v, '%(r)s'
   crt 'FIXTURE DONE'
end
"""


def state(box):
    """({label: counter text or None}, {(label, id): text}) as the disk holds them now."""
    out = sess(box, "RUN bp %s" % PRB)
    if "PROBE DONE" not in out:
        bail("the probe did not finish:\n" + out[-600:])
    last = {m.group(1): m.group(2) for m in re.finditer(r"(?m)^LAST (\S+) \[?([^\]\r\n]*)\]?\s*$", out)}
    recs = {(m.group(1), m.group(2)): m.group(3) for m in re.finditer(r"(?m)^REC (\S+) (\S+) \[(.*)\]\s*$", out)}
    return last, recs


def ids_of(recs, lab):
    return sorted(i for (l, i) in recs if l == lab)


def shown_id(out, name):
    """The id ED showed as the record's name: the line that is the file name and the id."""
    m = re.search(r"(?m)^%s (\S+)\s*$" % re.escape(name), out)
    return m.group(1) if m else None


def sed_id(e, name):
    """The id SED shows on its file line, by the file name."""
    m = re.search(re.escape(name) + r" (\S+)", "\n".join(e.lines()))
    return m.group(1) if m else None


def part_ed(box):
    say("\n--- ED: CREATING.SEQKEY takes the next id and edits a new record under it ----------------------------")
    last, recs = state(box)
    row("control: the fixture is as made: the counter of H reads 0 and H, its dictionary's records and D hold nothing of ours",
        last.get("H") == "0" and ids_of(recs, "H") == [] and ids_of(recs, "D") == [] and ids_of(recs, "C") == [],
        repr(last) + " " + repr(sorted(recs)))

    out = sess(box, "ED %s CREATING.SEQKEY" % H, "I first", "FI")
    last, recs = state(box)
    row("ED H CREATING.SEQKEY shows the id it took, 1, as it shows any record id, and says it is a new record",
        shown_id(out, H) == "1" and "New record" in out, "shown %r" % shown_id(out, H))
    row("...and FI files the record under 1 (the data on disk), with the text typed",
        recs.get(("H", "1")) == "first", repr(recs.get(("H", "1"))))
    row("...a record called CREATING.SEQKEY was NOT made (the old behaviour), and the counter reads 1",
        ("H", "CREATING.SEQKEY") not in recs and last.get("H") == "1", repr(ids_of(recs, "H")) + " " + repr(last))

    out = sess(box, "ED %s CREATING.SEQKEY" % H, "I second", "FI")
    last, recs = state(box)
    row("a second edit takes 2: shown 2, filed 2, and record 1 is as it was",
        shown_id(out, H) == "2" and recs.get(("H", "2")) == "second" and recs.get(("H", "1")) == "first" and last.get("H") == "2",
        "shown %r %r %r" % (shown_id(out, H), recs.get(("H", "2")), last.get("H")))

    out = sess(box, "ED %s creating.seqkey" % H, "I third", "FI")
    last, recs = state(box)
    row("the word is taken in lower case too: 3",
        shown_id(out, H) == "3" and recs.get(("H", "3")) == "third", "shown %r %r" % (shown_id(out, H), recs.get(("H", "3"))))

    say("\n--- ED: the id is taken when the edit starts, so a record never filed leaves a gap ------------------")
    out = sess(box, "ED %s CREATING.SEQKEY" % H, "Q")
    last, recs = state(box)
    row("quit without filing: the editor showed 4, nothing was filed under 4, and the counter reads 4",
        shown_id(out, H) == "4" and ("H", "4") not in recs and last.get("H") == "4",
        "shown %r, counter %r, ids %r" % (shown_id(out, H), last.get("H"), ids_of(recs, "H")))
    out = sess(box, "ED %s CREATING.SEQKEY" % H, "I after the gap", "FI")
    last, recs = state(box)
    row("the next edit takes 5: 4 is not given out twice",
        shown_id(out, H) == "5" and recs.get(("H", "5")) == "after the gap" and ("H", "4") not in recs,
        "shown %r %r" % (shown_id(out, H), recs.get(("H", "5"))))

    say("\n--- ED: at the Record name? prompt, twice on a line, with NO.QUERY, EDIT -----------------------------")
    out = sess(box, "ED %s" % H, "creating.seqkey", "I via the prompt", "FI", "")
    last, recs = state(box)
    row("typed at the Record name? prompt it takes the next id: 6",
        recs.get(("H", "6")) == "via the prompt" and last.get("H") == "6", repr(recs.get(("H", "6"))) + " " + repr(last.get("H")))

    out = sess(box, "ED %s CREATING.SEQKEY CREATING.SEQKEY" % H, "I seven", "FI", "I eight", "FI")
    last, recs = state(box)
    row("two on one command line take two ids, each as its edit begins: 7 and 8",
        recs.get(("H", "7")) == "seven" and recs.get(("H", "8")) == "eight" and last.get("H") == "8",
        repr(recs.get(("H", "7"))) + " " + repr(recs.get(("H", "8"))) + " " + repr(last.get("H")))

    out = sess(box, "ED %s CREATING.SEQKEY NO.QUERY" % H, "I nine", "FI")
    last, recs = state(box)
    row("NO.QUERY after it is accepted as it always was: 9",
        recs.get(("H", "9")) == "nine" and last.get("H") == "9", repr(recs.get(("H", "9"))) + " " + repr(last.get("H")))

    out = sess(box, "EDIT %s CREATING.SEQKEY" % H, "I ten", "FI")
    last, recs = state(box)
    row("EDIT, the synonym, takes it too: 10",
        recs.get(("H", "10")) == "ten" and last.get("H") == "10", repr(recs.get(("H", "10"))) + " " + repr(last.get("H")))

    say("\n--- ED: an ordinary record id is as it was; CREATING.SEQKEY in quotes is a record id ----------------")
    before = last.get("H")
    out = sess(box, "ED %s abc" % H, "I plain", "FI")
    last, recs = state(box)
    row("an ordinary id is edited under that id, and the counter does not move",
        shown_id(out, H) == "abc" and recs.get(("H", "abc")) == "plain" and last.get("H") == before,
        "shown %r, counter %r (was %r)" % (shown_id(out, H), last.get("H"), before))
    out = sess(box, 'ED %s "CREATING.SEQKEY"' % H, "I the literal", "FI")
    last, recs = state(box)
    row("CREATING.SEQKEY in quotes is the record of that name, and the counter does not move",
        shown_id(out, H) == "CREATING.SEQKEY" and recs.get(("H", "CREATING.SEQKEY")) == "the literal" and last.get("H") == before,
        "shown %r, counter %r (was %r)" % (shown_id(out, H), last.get("H"), before))

    say("\n--- ED: a select list is as it was --------------------------------------------------------------------")
    out = sess(box, 'SELECT %s WITH @ID = "abc"' % H, "ED %s NO.QUERY" % H, "Q")
    last, recs = state(box)
    row("an active select list with NO.QUERY edits the listed record, abc, and takes no id",
        shown_id(out, H) == "abc" and last.get("H") == before, "shown %r, counter %r" % (shown_id(out, H), last.get("H")))

    say("\n--- ED: an id that names a record already there is passed over (the editor is asked for a new one) ---")
    sess(box, "ED %s 11" % H, "I eleven by hand", "FI", "ED %s 12" % H, "I twelve by hand", "FI")
    last, recs = state(box)
    row("control: records 11 and 12 were written by hand, and the counter still reads 10",
        recs.get(("H", "11")) == "eleven by hand" and recs.get(("H", "12")) == "twelve by hand" and last.get("H") == "10",
        repr(last.get("H")))
    out = sess(box, "ED %s CREATING.SEQKEY" % H, "I thirteen", "FI")
    last, recs = state(box)
    row("the next CREATING.SEQKEY would be 11, which is there: the editor shows 13, files 13, and leaves 11 and 12 alone",
        shown_id(out, H) == "13" and recs.get(("H", "13")) == "thirteen" and recs.get(("H", "11")) == "eleven by hand"
        and recs.get(("H", "12")) == "twelve by hand" and last.get("H") == "13",
        "shown %r, counter %r, 11 %r, 12 %r" % (shown_id(out, H), last.get("H"), recs.get(("H", "11")), recs.get(("H", "12"))))

    say("\n--- ED: CONFIGURE.FILE NEXT, the dictionary, a collection file -----------------------------------------")
    sess(box, "CONFIGURE.FILE %s NEXT 100" % H)
    out = sess(box, "ED %s CREATING.SEQKEY" % H, "I hundred", "FI")
    last, recs = state(box)
    row("after CONFIGURE.FILE NEXT 100 the editor takes 100",
        shown_id(out, H) == "100" and recs.get(("H", "100")) == "hundred" and last.get("H") == "100",
        "shown %r, counter %r" % (shown_id(out, H), last.get("H")))

    dcount0 = last.get("HD")
    out = sess(box, "ED DICT %s CREATING.SEQKEY" % H, "I xdict item", "FI")
    last, recs = state(box)
    row("DICT: the dictionary has its own counter: the item is filed in the dictionary under the next id there",
        any(l == "HD" and t == "xdict item" for (l, i), t in recs.items()) and ("H", "xdict item") not in recs,
        repr(sorted(k for k in recs if k[0] == "HD")) + " " + repr(last))
    hd_ids = [i for (l, i), t in recs.items() if l == "HD" and t == "xdict item"]
    row("...and the data part's counter did not move (100), the dictionary's reads the id it was given",
        last.get("H") == "100" and hd_ids != [] and last.get("HD") == hd_ids[0], repr(last) + " " + repr(hd_ids) + " was " + repr(dcount0))

    out = sess(box, "ED %s CREATING.SEQKEY" % C, "I {", 'I "a": 1', "I }", "FI")
    last, recs = state(box)
    row("a data collection file is a hashed file: record 1 holds the JSON typed, the counter reads 1",
        shown_id(out, C) == "1" and recs.get(("C", "1")) == '{"a":1}' and last.get("C") == "1",
        "shown %r, record %r, counter %r" % (shown_id(out, C), recs.get(("C", "1")), last.get("C")))

    say("\n--- ED: a file that cannot give an id is refused, and nothing is edited -------------------------------")
    last0, recs0 = state(box)
    out = sess(box, "ED %s CREATING.SEQKEY" % D)
    last, recs = state(box)
    row("a directory file: the refusal is printed (message 11352)", REFUSED in out, out[-300:])
    row("...no record was edited (no New record line, no id shown) and none was made in the directory",
        "New record" not in out and shown_id(out, D) is None and ids_of(recs, "D") == [] and ("D", "CREATING.SEQKEY") not in recs,
        repr(ids_of(recs, "D")))
    out = sess(box, "ED %s abc" % D, "I in a directory", "FI")
    last, recs = state(box)
    row("control: an ordinary id in the directory file is edited as ever",
        recs.get(("D", "abc")) == "in a directory", repr(recs.get(("D", "abc"))))

    out = sess(box, "ED %s CREATING.SEQKEY" % R)
    last, recs = state(box)
    row("a read-only file: the refusal is printed (message 1431)", READONLY in out and "New record" not in out, out[-300:])
    row("...and the counter of H, the same file, did not move (it reads 100)", last.get("H") == "100", repr(last.get("H")))
    out = sess(box, "ED %s abc CREATING.SEQKEY" % D)
    last, recs = state(box)
    row("on a command line with an ordinary id first, the refusal comes before any record is edited",
        REFUSED in out and "New record" not in out and "abc" not in "\n".join(l for l in out.splitlines() if l.startswith(D)),
        out[-300:])


def part_sed(box):
    say("\n--- SED: CREATING.SEQKEY on the command line ----------------------------------------------------------")
    last, recs = state(box)
    n = int(last.get("H")) + 1                            # the id it should take
    literal0 = recs.get(("H", "CREATING.SEQKEY"))         # the ED part made the record of that name (in quotes) on purpose
    e = Term(box, "SED %s CREATING.SEQKEY" % H)
    shown = sed_id(e, H)
    row("SED H CREATING.SEQKEY shows the next id, %d, on its file line, as it shows any record id" % n, shown == str(n),
        "shown %r\n%s" % (shown, e.text()[-500:]))
    e.keys("typed in sed")
    e.keys(CTRL("s"))
    e.keys(CTRL("q"))
    e.end()
    last, recs = state(box)
    row("...Ctrl-S files it under %d (the disk), the counter reads %d, and no record called CREATING.SEQKEY was made" % (n, n),
        recs.get(("H", str(n))) == "typed in sed" and last.get("H") == str(n) and recs.get(("H", "CREATING.SEQKEY")) == literal0,
        "%r %r" % (recs.get(("H", str(n))), last.get("H")))

    say("\n--- SED: quit without saving leaves the id taken --------------------------------------------------------")
    e = Term(box, "SED %s creating.seqkey" % H)
    shown = sed_id(e, H)
    row("the word in lower case: it shows %d" % (n + 1), shown == str(n + 1), "shown %r\n%s" % (shown, e.text()[-300:]))
    e.keys(CTRL("q"))
    e.end()
    last, recs = state(box)
    row("quit with no change: nothing filed under %d and the counter reads %d" % (n + 1, n + 1),
        ("H", str(n + 1)) not in recs and last.get("H") == str(n + 1), "%r %r" % (ids_of(recs, "H")[-3:], last.get("H")))

    say("\n--- SED: at the Record name? prompt --------------------------------------------------------------------")
    e = Term(box, "SED %s" % H)
    e.keys("creating.seqkey", RET, idle=1.0)
    shown = sed_id(e, H)
    row("typed at the prompt it takes the next id: %d" % (n + 2), shown == str(n + 2), "shown %r\n%s" % (shown, e.text()[-300:]))
    e.keys("from the prompt")
    e.keys(CTRL("s"))
    e.keys(CTRL("q"))
    e.end()
    last, recs = state(box)
    row("...and it is filed under %d" % (n + 2), recs.get(("H", str(n + 2))) == "from the prompt" and last.get("H") == str(n + 2),
        "%r %r" % (recs.get(("H", str(n + 2))), last.get("H")))

    say("\n--- SED: DICT, an ordinary id, the id in quotes ---------------------------------------------------------")
    e = Term(box, "SED DICT %s CREATING.SEQKEY" % H)
    dn = sed_id(e, H)
    e.keys("xsed dict item")
    e.keys(CTRL("s"))
    e.keys(CTRL("q"))
    e.end()
    last, recs = state(box)
    row("DICT: SED showed an id of the dictionary's counter, and the item was filed in the dictionary under it",
        dn is not None and recs.get(("HD", dn)) == "xsed dict item" and last.get("HD") == dn and last.get("H") == str(n + 2),
        "shown %r, dict record %r, counters %r" % (dn, recs.get(("HD", dn)), last))

    before = last.get("H")
    e = Term(box, "SED %s abc" % H)
    shown = sed_id(e, H)
    e.keys(CTRL("q"))
    e.end()
    last, recs = state(box)
    row("an ordinary id opens that record, and the counter does not move", shown == "abc" and last.get("H") == before,
        "shown %r, counter %r (was %r)" % (shown, last.get("H"), before))
    e = Term(box, 'SED %s "CREATING.SEQKEY"' % H)
    shown = sed_id(e, H)
    e.keys(CTRL("q"))
    e.end()
    last, recs = state(box)
    row("CREATING.SEQKEY in quotes opens the record of that name, and the counter does not move",
        shown == "CREATING.SEQKEY" and last.get("H") == before, "shown %r, counter %r (was %r)" % (shown, last.get("H"), before))

    say("\n--- SED: a file that cannot give an id is refused, and nothing is edited -------------------------------")
    e = Term(box, "SED %s CREATING.SEQKEY" % D)
    t = e.text()
    row("a directory file: SED prints the refusal (11352) and does not draw the editor", REFUSED in t and "Ctrl" not in t and "File " not in t.split(REFUSED)[0][-200:],
        t[-500:])
    e.end()
    e = Term(box, "SED %s CREATING.SEQKEY" % R)
    t = e.text()
    row("a read-only file: SED prints the refusal (1431)", READONLY in t, t[-500:])
    e.end()
    last2, recs2 = state(box)
    row("...and no record was made in the directory, and the counter of H did not move",
        ids_of(recs2, "D") == ids_of(recs, "D") and last2.get("H") == before, repr(last2.get("H")) + " was " + repr(before))

    say("\n--- SED: at the prompt, a file that cannot give an id is said so and asks again --------------------------")
    e = Term(box, "SED %s" % D)
    e.keys("creating.seqkey", RET, idle=1.0)
    t = e.text()
    row("the refusal is printed at the prompt, and the prompt comes back", REFUSED in t and t.rstrip().endswith("Record name?"),
        t[-400:])
    e.end()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-edseqkey.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-edseqkey: sandbox %s" % box)
    say("sandbox-edseqkey: tree    %s" % os.path.dirname(HERE))
    say("sandbox-edseqkey: files   %s (hashed) %s (directory) %s (collection) %s (read-only entry)" % (H, D, C, R))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-edseqkey: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    names = {"h": H, "d": D, "c": C, "r": R}
    progs = {FIX: FIXTURE % names, PRB: PROBE % names}
    for nm, body in progs.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(box, *(["BASIC bp %s" % n for n in progs] + ["RUN bp %s" % FIX]))
        row("setup: the programs compiled and the fixture was made",
            len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == len(progs) and "FIXTURE DONE" in out, out[-900:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-800:])
        only = [a for a in sys.argv if a.startswith("--only=")]
        if not only or only[0] == "--only=ed":
            part_ed(box)
        if not only or only[0] == "--only=sed":
            part_sed(box)
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        sess(box, "DELETE.FILE %s" % H, "DELETE.FILE %s" % D, "DELETE.FILE %s" % C, "DELETE VOC %s" % R)
        for nm in progs:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-edseqkey: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
