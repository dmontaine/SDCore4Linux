#!/usr/bin/env python3
#
# sandbox-dictform.py - S.90 stage 2 (31 Oct 2026): a dictionary item as a full-screen form, in the IDE, driven on a PSEUDO-TERMINAL.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dictform.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 31 Oct 26 dm  New (WRITTEN WITH THE FORM; every row is the first run's).
# END-HISTORY
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN=1, the sdsys account) types IDE DICT zzdf1 item /form on a 140 by 43 terminal, with a file zzdf1 whose dictionary holds six items
# written by an $internal probe (a D item, an I item, an L item, a PH item, an X item, and a D item whose format is not one the form can show).  THE EVIDENCE IS THE DISK: a second
# probe reads the item back (DR[id][record with | between the fields]), before and after, so a row that says "nothing was written" compares two reads.
#
#   DF0   the form opens: the rows of a D item, numbered 1 to 10, with the item's own values
#   DF1   Esc with nothing changed leaves without a question and writes nothing
#   DF2   a heading changed and Return (the Save button) writes the item through the IDE's own save
#   DF3   a field number that is not a number: the err line names the row when the focus leaves it; Save is refused and the form stays; the disk is as it was
#   DF4   Esc after a change asks; Keep editing keeps the form and what was typed; Discard leaves and writes nothing
#   DF5   the Type chosen again makes the form again with the rows of that type and keeps what was typed (D to E to I, the heading stays), and Save writes an I item
#   DF6   a new item opens as a new D item with defaults (width 10, L, S) and writes the item that does not exist yet
#   DF7   an L item has its own three rows, a PH item one text row, an X item a text area (and no Field #)
#   DF8   an item the form cannot show stays text, with the reason said, and nothing is written
#   DF9   /form on a tab that is not a dictionary item says so and shows no form
#   DF10  the Go menu has the entry and it opens the form
#   DF11  Edit as text leaves the form with the text view and writes nothing
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_dictform", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
FILE = "zzdf1"

WRITE_PROBE = r"""$internal
program zzdw
   open 'DICT', 'zzdf1' to d else
      crt 'DW no dict'
      stop
   end
   write 'D' : @fm : '2' : @fm : '' : @fm : 'Name' : @fm : '10L' : @fm : 'S' to d, 'fld'
   write 'I' : @fm : 'AMT * 2' : @fm : '' : @fm : 'Double' : @fm : '8R2' : @fm : 'S' to d, 'calc'
   write 'L' : @fm : 'FIELD(@ID, "-", 1)' : @fm : 'TITLES' to d, 'lnk'
   write 'PH' : @fm : "GRAND.TOTAL 'L'" to d, 'ph1'
   write 'X' : @fm : 'line one' : @fm : 'line two' to d, 'note'
   write 'D' : @fm : '2' : @fm : '' : @fm : 'F' : @fm : 'abc' to d, 'badfmt'
   delete d, 'newone'
   open 'zzdf1' to dd else
      crt 'DW no data'
      stop
   end
   write 'x' to dd, 'rec1'
   crt 'DW done'
end
"""

READ_PROBE = r"""$internal
program zzdr
   id = field(@sentence, ' ', 4)
   open 'DICT', 'zzdf1' to d else
      crt 'DR no dict'
      stop
   end
   read r from d, id then
      crt 'DR[' : id : '][' : convert(@fm, '|', r) : ']'
   end else
      crt 'DR[' : id : '][ABSENT]'
   end
end
"""


def reset():
    out = adm("RUN gpl.bp zzdw")
    if not has(out, r"^DW done$"):
        bail("the fixture items were not written:\n" + "\n".join(out[-5:]))


def disk(item):
    """The item as the dictionary holds it, fields joined by |; None when the probe did not answer (a row that needs it then FAILS)."""
    out = adm("RUN gpl.bp zzdr " + item)
    for ln in out:
        m = re.match(r"^DR\[%s\]\[(.*)\]\s*$" % re.escape(item), ln)
        if m:
            return m.group(1)
    return None


def ide(command, idle=3.2):
    h = H(admin=True)
    h.typed(command + "\r", idle=idle)
    return h


def form_up(h):
    T = h.text()
    return "1. Type:" in T and "Save" in T and "Cancel" in T


def rowline(h, label):
    for ln in h.lines():
        if label in ln:
            return ln.rstrip()
    return ""


def leave(h):
    h.key("ctrl-q", idle=1.2)
    h.typed("n", idle=0.6)
    h.end()


FIXTURE = {"fld": "D|2||Name|10L|S", "calc": "I|AMT * 2||Double|8R2|S", "lnk": "L|FIELD(@ID, \"-\", 1)|TITLES", "ph1": "PH|GRAND.TOTAL 'L'", "note": "X|line one|line two",
           "badfmt": "D|2||F|abc"}


def main():
    try:
        sh.setup("sandbox-dictform.py")
        adm("CREATE.FILE " + FILE)
        g.put(os.path.join(sh.SYS, "gpl.bp", "zzdw"), WRITE_PROBE)
        g.put(os.path.join(sh.SYS, "gpl.bp", "zzdr"), READ_PROBE)
        out = adm("BASIC gpl.bp zzdw zzdr")
        if not has(out, r"^Compiled 2 program\(s\) with no errors"):
            bail("the probes did not compile:\n" + "\n".join(out[-8:]))
        reset()
        for k, v in FIXTURE.items():
            if disk(k) != v:
                bail("the fixture item %s reads back as %r, not %r: the instrument cannot be believed" % (k, disk(k), v))
        say("    (the fixture: six dictionary items, read back from the disk)")
        run_rows()
    finally:
        sh.teardown()
    say("\nsandbox-dictform: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


def run_rows():
    say("\n--- the form of a D item")
    h = ide("ide dict zzdf1 fld /form")
    if not form_up(h):
        dump(h)
        bail("IDE DICT zzdf1 fld /form never drew the form, so no row below can be believed")
    T = h.text()
    want = ["1. Type:", "2. Field #:", "3. Conversion:", "4. Heading:", "5. Width:", "6. Justification:", "7. Decimals:", "8. Single/Multi:", "9. Association:", "10. User:"]
    row("DF0 the form of a D item: ten numbered rows, Save, Edit as text and Cancel", all(w in T for w in want) and "Edit as text" in T and "(new item)" not in T,
        repr([w for w in want if w not in T]))
    row("DF0b the item's own values are in the rows: field 2, heading Name, width 10, justification L, S", re.search(r"2\. Field #:\s+2\b", rowline(h, "2. Field #:")) is not None
        and "Name" in rowline(h, "4. Heading:") and re.search(r"\b10\b", rowline(h, "5. Width:")) is not None and re.search(r"\bL\b", rowline(h, "6. Justification:")) is not None
        and re.search(r"\bS\b", rowline(h, "8. Single/Multi:")) is not None, repr([rowline(h, w) for w in want[:6]]))
    h.key("esc", idle=1.5)
    T = h.text()
    row("DF1 Esc with nothing changed leaves without a question: the IDE is back, the disk is as it was", not form_up(h) and "Leave without saving" not in T and disk("fld") == FIXTURE["fld"],
        repr((T[:120], disk("fld"))))
    leave(h)

    say("\n--- a heading changed and saved")
    reset()
    h = ide("ide dict zzdf1 fld /form")
    for _ in range(3):
        h.key("tab")
    h.typed("\x15", idle=0.3)
    h.typed("Full name", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF2 a heading changed and Return (Save): the item is written by the IDE's save with the new heading and nothing else changed", disk("fld") == "D|2||Full name|10L|S" and not form_up(h),
        repr((disk("fld"), h.text()[-300:])))
    leave(h)

    say("\n--- a field number that is not a number")
    reset()
    h = ide("ide dict zzdf1 fld /form")
    h.key("tab")
    h.typed("\x15", idle=0.3)
    h.typed("abc", idle=0.4)
    h.key("tab", idle=0.8)
    T = h.text()
    row("DF3a leaving the Field # row with abc names the row in the err line", "! Field #: a whole number from 0 to 9999" in T, T[-700:])
    h.key("enter", idle=1.5)
    T = h.text()
    row("DF3b Save is refused: the form is still up with the same message and the disk is as it was", form_up(h) and "a whole number from 0 to 9999" in T and disk("fld") == FIXTURE["fld"],
        repr((form_up(h), disk("fld"))))

    say("\n--- Esc after a change asks")
    h.key("esc", idle=1.2)
    T = h.text()
    row("DF4a Esc after a change asks 'Leave without saving the changes?'", "Leave without saving the changes?" in T, T[-500:])
    h.key("enter", idle=1.0)
    row("DF4b Keep editing (the default) keeps the form and what was typed", form_up(h) and re.search(r"abc", rowline(h, "2. Field #:")) is not None, rowline(h, "2. Field #:"))
    h.key("esc", idle=1.2)
    h.typed("d", idle=1.5)
    row("DF4c Discard leaves the form and writes nothing", not form_up(h) and disk("fld") == FIXTURE["fld"], repr((form_up(h), disk("fld"), h.text()[-200:])))
    leave(h)

    say("\n--- the Type chosen again")
    reset()
    h = ide("ide dict zzdf1 fld /form")
    h.key("right", idle=1.2)
    row("DF5a the Type moved to E: the form has a Path row and no Field # row", "Path:" in h.text() and "Field #:" not in h.text(), h.text()[:600])
    h.key("right", idle=1.2)
    T = h.text()
    row("DF5b ...and to I: an Expression row; the heading typed for the D item is still there", "Expression:" in T and "Name" in rowline(h, "Heading:"), repr(rowline(h, "Heading:")))
    h.key("tab")
    h.typed("F2 * 3", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF5c Save writes an I item: the expression, and the heading, format and S/M the D item had", disk("fld") == "I|F2 * 3||Name|10L|S", repr(disk("fld")))
    leave(h)

    say("\n--- a new item")
    reset()
    h = ide("ide dict zzdf1 newone /form")
    T = h.text()
    row("DF6a a new item: the form says so, is a D item and has the defaults 10, L and S", form_up(h) and "(new item)" in T and re.search(r"\b10\b", rowline(h, "5. Width:")) is not None
        and re.search(r"\bL\b", rowline(h, "6. Justification:")) is not None and re.search(r"\bS\b", rowline(h, "8. Single/Multi:")) is not None, repr((T[:200], rowline(h, "5. Width:"))))
    h.key("tab")
    h.typed("3", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF6b Save writes the item that did not exist: D, field 3, format 10L, S", disk("newone") == "D|3|||10L|S", repr(disk("newone")))
    leave(h)

    say("\n--- the rows of the other types")
    reset()
    h = ide("ide dict zzdf1 lnk /form")
    T = h.text()
    row("DF7a an L item: Id expression, File, File expression and no Field # or Width", form_up(h) and "2. Id expression:" in T and "3. File:" in T and "4. File expression:" in T and "Field #" not in T
        and "Width" not in T and "TITLES" in rowline(h, "3. File:"), T[:700])
    h.key("esc", idle=1.5)
    leave(h)
    h = ide("ide dict zzdf1 ph1 /form")
    T = h.text()
    row("DF7b a PH item: one text row, Phrase, with the phrase in it", form_up(h) and "2. Phrase:" in T and "GRAND.TOTAL" in T and "Field #" not in T, T[:600])
    h.key("esc", idle=1.5)
    leave(h)
    h = ide("ide dict zzdf1 note /form")
    T = h.text()
    row("DF7c an X item: a text area with its two lines", form_up(h) and "2. Text:" in T and "line one" in T and "line two" in T, T[:700])
    h.key("esc", idle=1.5)
    leave(h)

    say("\n--- an item the form cannot show, and a tab that is not an item")
    h = ide("ide dict zzdf1 badfmt /form")
    T = h.text()
    row("DF8 a D item whose format is not a width, L R T or C and decimals stays text: the reason is said, no form, nothing written", not form_up(h) and "cannot show" in T and "format" in T
        and disk("badfmt") == FIXTURE["badfmt"], repr((T[-300:], disk("badfmt"))))
    leave(h)
    h = ide("ide zzdf1 rec1 /form")
    T = h.text()
    row("DF9 /form on a record of the data file says the form is for a dictionary item and shows no form", not form_up(h) and "dictionary form is for a dictionary item" in T, T[-300:])
    leave(h)

    say("\n--- the Go menu, and Edit as text")
    h = ide("ide dict zzdf1 fld")
    row("DF10a without /form the item opens as text: no form", not form_up(h), h.text()[:200])
    h.key("esc", idle=1.0)
    h.key("right", idle=0.8)
    T = h.text()
    row("DF10b the Go menu lists 'Dictionary item as form'", "Dictionary item as form" in T, T[:900])
    h.typed("m", idle=2.0)
    row("DF10c ...and choosing it opens the form", form_up(h) and "2. Field #:" in h.text(), h.text()[:300])
    h.typed("t", idle=1.5)
    row("DF11 Edit as text (the t key, from the Type row) leaves the form with the text view and writes nothing", not form_up(h) and disk("fld") == FIXTURE["fld"], repr((form_up(h), disk("fld"))))
    leave(h)


if __name__ == "__main__":
    sys.exit(main())
