#!/usr/bin/env python3
#
# sandbox-dictform.py - S.90 (31 Oct 2026): a dictionary item as a full-screen form, in the IDE, driven on a PSEUDO-TERMINAL.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dictform.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 31 Oct 26 dm  REWRITTEN FOR THE OWNER'S LAYOUT (his message of 31 Oct, after the first build): Type is an entry that is typed and the rows of that type appear once it is entered; the labels
#               are Field #, Conversion Cd, Column Heading and ONE row Len & Just (30 L, 12 R 2); no row is numbered; the buttons are Accept and Cancel and nothing else.  The first build's
#               rows (a radio Type row, numbered rows, Width, Justification and Decimals, Save and Edit as text) are gone with it.
# 31 Oct 26 dm  New (WRITTEN WITH THE FORM; every row is the first run's).
# END-HISTORY
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN=1, the sdsys account) types IDE DICT zzdf1 item /form on a 140 by 43 terminal, with a file zzdf1 whose dictionary holds six items
# written by an $internal probe (a D item, an I item, an L item, a PH item, an X item, and a D item whose format is not one the form can show).  THE EVIDENCE IS THE DISK: a second
# probe reads the item back (DR[id][record with | between the fields]), before and after, so a row that says "nothing was written" compares two reads.
#
#   DF0   the form opens in the owner's layout: Type, Field #, Conversion Cd, Column Heading, Len & Just, Single/Multi, User, with the item's own values, Accept and Cancel, no number on a row
#   DF1   Esc with nothing changed leaves without a question and writes nothing
#   DF2   a column heading changed and Return (the Accept button) writes the item through the IDE's own save
#   DF3   a field number that is not a number: the err line names the row when the focus leaves it; Accept is refused and the form stays; the disk is as it was
#   DF4   Esc after a change asks; Keep editing keeps the form and what was typed; Discard leaves and writes nothing
#   DF5   a Type typed makes the form again with the rows of that type and keeps what was typed (D to E to I, the heading and Len & Just stay), and Accept writes an I item; a type that is not one is refused
#   DF6   a new item shows only the Type until one is typed; D and Tab bring the rows with the defaults 10 L and S; Accept writes the item; Accept with no Type is refused
#   DF7   an L item has its own three rows, a PH item one text row, an X item a text area (and no Field #, no Len & Just); each has Accept and Cancel
#   DF8   an item the form cannot show stays text, with the reason said, and nothing is written
#   DF9   /form on a tab that is not a dictionary item says so and shows no form
#   DF10  the form is the DEFAULT face (no last word opens it; Esc leaves the item as text; an item it cannot show and `/text` open as text; a new item opens as the form); the Go menu has the entry
#   DF11  Cancel (Esc) leaves the form with the item as text and writes nothing
#   DF12  Len & Just: 12 r 2 is written as 12R2; a bad one (30 X) is refused with its own message, at the row and at Accept
import importlib.util
import os
import re
import sys
import time

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
   delete d, 'newtwo'
   delete d, 'newdef'
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
    return "Type:" in T and "Accept" in T and "Cancel" in T


def wait_text(h, needle, secs=10.0):
    """pump the terminal until `needle` is on the screen (a remade form takes longer on a busy machine than any fixed wait): True when it came"""
    end = time.time() + secs
    while time.time() < end:
        if needle in h.text():
            return True
        h.s._pump(0.3)
    return needle in h.text()


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
    say("\n--- the form of a D item, in the owner's layout")
    h = ide("ide dict zzdf1 fld /form")
    if not form_up(h):
        dump(h)
        bail("IDE DICT zzdf1 fld /form never drew the form, so no row below can be believed")
    T = h.text()
    want = ["Type:", "Field #:", "Conversion Cd:", "Column Heading:", "Len & Just:", "Single/Multi:", "User:"]
    gone = ["Width", "Justification", "Decimals", "Edit as text", "Save", "(new item)"]
    row("DF0 the form of a D item: Type, Field #, Conversion Cd, Column Heading, Len & Just, Single/Multi, User, and the buttons Accept and Cancel - nothing of the first build (Width, Justification, Decimals, Save, Edit as text)",
        all(w in T for w in want) and all(w not in T for w in gone), repr(([w for w in want if w not in T], [w for w in gone if w in T])))
    row("DF0a no row is numbered", re.search(r"\b\d+\. [A-Z]", T) is None, T[:400])
    row("DF0b the item's own values are in the rows: Type D, field 2, column heading Name, Len & Just 10 L, Single/Multi S",
        re.search(r"Type:\s+D\b", rowline(h, "Type:")) is not None and re.search(r"Field #:\s+2\b", rowline(h, "Field #:")) is not None and "Name" in rowline(h, "Column Heading:")
        and re.search(r"Len & Just:\s+10 L\b", rowline(h, "Len & Just:")) is not None and re.search(r"Single/Multi:\s+S\b", rowline(h, "Single/Multi:")) is not None,
        repr([rowline(h, w) for w in want[:6]]))
    h.key("esc", idle=1.5)
    T = h.text()
    row("DF1 Esc with nothing changed leaves without a question: the IDE is back, the disk is as it was", not form_up(h) and "Leave without saving" not in T and disk("fld") == FIXTURE["fld"],
        repr((T[:120], disk("fld"))))
    leave(h)

    say("\n--- a column heading changed and accepted")
    reset()
    h = ide("ide dict zzdf1 fld /form")
    for _ in range(3):
        h.key("tab")
    h.typed("\x15", idle=0.3)
    h.typed("Full name", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF2 a column heading changed and Return (Accept): the item is written by the IDE's save with the new heading and nothing else changed", disk("fld") == "D|2||Full name|10L|S" and not form_up(h),
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
    row("DF3b Accept is refused: the form is still up with the same message and the disk is as it was", form_up(h) and "a whole number from 0 to 9999" in T and disk("fld") == FIXTURE["fld"],
        repr((form_up(h), disk("fld"))))

    say("\n--- Esc after a change asks")
    h.key("esc", idle=1.2)
    T = h.text()
    row("DF4a Esc after a change asks 'Leave without saving the changes?'", "Leave without saving the changes?" in T, T[-500:])
    h.key("enter", idle=1.0)
    row("DF4b Keep editing (the default) keeps the form and what was typed", form_up(h) and re.search(r"abc", rowline(h, "Field #:")) is not None, rowline(h, "Field #:"))
    h.key("esc", idle=1.2)
    h.typed("d", idle=1.5)
    row("DF4c Discard leaves the form and writes nothing", not form_up(h) and disk("fld") == FIXTURE["fld"], repr((form_up(h), disk("fld"), h.text()[-200:])))
    leave(h)

    say("\n--- the Type typed")
    reset()
    h = ide("ide dict zzdf1 fld /form")
    h.typed("\x15", idle=0.3)
    h.typed("E", idle=0.4)
    h.key("tab", idle=1.8)
    wait_text(h, "Element Path:")
    T = h.text()
    row("DF5a typing E in the Type entry and Tab makes the rows of an E item: the Type reads E, Element Path, no Field #; the column heading and Len & Just are still there",
        re.search(r"Type:\s+E\b", rowline(h, "Type:")) is not None and "Element Path:" in T and "Field #:" not in T and "Name" in rowline(h, "Column Heading:") and re.search(r"Len & Just:\s+10 L\b", rowline(h, "Len & Just:")) is not None, T[:600])
    h.key("up", idle=0.8)
    h.typed("\x15", idle=0.3)
    h.typed("I", idle=0.4)
    h.key("tab", idle=1.8)
    wait_text(h, "Expression:")
    T = h.text()
    row("DF5b ...and I: an Expression row; the heading typed for the D item is still there", "Expression:" in T and "Element Path" not in T and "Name" in rowline(h, "Column Heading:"), repr(rowline(h, "Column Heading:")))
    h.typed("F2 * 3", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF5c Accept writes an I item: the expression, and the heading, format and S/M the D item had", disk("fld") == "I|F2 * 3||Name|10L|S", repr(disk("fld")))
    leave(h)
    reset()
    h = ide("ide dict zzdf1 fld /form")
    h.typed("\x15", idle=0.3)
    h.typed("Z", idle=0.4)
    h.key("tab", idle=1.2)
    T = h.text()
    row("DF5d a type that is not one is refused where it is typed: the err line says so, the rows are still those of the D item and nothing is written",
        "! Type: D, E, I, L, PH or X" in T and "Field #:" in T and disk("fld") == FIXTURE["fld"], T[-700:])
    h.key("esc", idle=1.5)
    leave(h)

    say("\n--- a new item")
    reset()
    h = ide("ide dict zzdf1 newone /form")
    T = h.text()
    row("DF6a a new item shows the Type and nothing else until a type is entered", form_up(h) and "(new item)" in T and "Field #:" not in T and "Len & Just:" not in T and "Column Heading:" not in T, T[:400])
    h.typed("D", idle=0.4)
    h.key("tab", idle=1.8)
    wait_text(h, "Field #:")
    T = h.text()
    row("DF6b ...typing D and Tab brings the rows of a D item, with the defaults 10 L and S", "Field #:" in T and re.search(r"Len & Just:\s+10 L\b", rowline(h, "Len & Just:")) is not None
        and re.search(r"Single/Multi:\s+S\b", rowline(h, "Single/Multi:")) is not None, T[:500])
    h.typed("3", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF6c Accept writes the item that did not exist: D, field 3, format 10L, S", disk("newone") == "D|3|||10L|S", repr(disk("newone")))
    leave(h)
    h = ide("ide dict zzdf1 newtwo /form")
    h.key("enter", idle=1.5)
    T = h.text()
    row("DF6d Accept with no Type typed is refused and says why; nothing is written", form_up(h) and "! Type: D, E, I, L, PH or X" in T and disk("newtwo") == "ABSENT", repr((form_up(h), T[-400:], disk("newtwo"))))
    h.key("esc", idle=1.5)
    leave(h)

    say("\n--- the rows of the other types")
    reset()
    h = ide("ide dict zzdf1 lnk /form")
    T = h.text()
    row("DF7a an L item: Id Expression, File, File Expression, and no Field # or Len & Just", form_up(h) and "Id Expression:" in T and "File:" in T and "File Expression:" in T and "Field #" not in T
        and "Len & Just" not in T and "TITLES" in rowline(h, "File:"), T[:700])
    h.key("esc", idle=1.5)
    leave(h)
    h = ide("ide dict zzdf1 ph1 /form")
    T = h.text()
    row("DF7b a PH item: one text row, Phrase, with the phrase in it", form_up(h) and "Phrase:" in T and "GRAND.TOTAL" in T and "Field #" not in T, T[:600])
    row("DF7b2 ...with its Accept and Cancel buttons (a text row is a memo with the id `text`: no button may have it)", "Accept" in T and "Cancel" in T and "Edit as text" not in T, T[-900:])
    h.key("esc", idle=1.5)
    leave(h)
    h = ide("ide dict zzdf1 note /form")
    T = h.text()
    row("DF7c an X item: a text area with its two lines", form_up(h) and "Text:" in T and "line one" in T and "line two" in T, T[:700])
    row("DF7c2 ...with its Accept and Cancel buttons", "Accept" in T and "Cancel" in T and "Edit as text" not in T, T[-900:])
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

    say("\n--- the default face, /text, the Go menu, and Cancel")
    reset()
    h = ide("ide dict zzdf1 fld")
    row("DF10a without a last word the item opens as the FORM (the default face): the Type row and the item's own rows", form_up(h) and "Field #:" in h.text() and "(new item)" not in h.text(),
        h.text()[:300])
    h.key("esc", idle=1.5)
    T = h.text()
    row("DF10a2 ...and Esc with nothing changed leaves the item as a text tab: no form, no question, the disk as it was", not form_up(h) and "Leave without saving" not in T and "dict zzdf1 fld" in T and disk("fld") == FIXTURE["fld"],
        repr((T[:200], disk("fld"))))
    leave(h)
    h = ide("ide dict zzdf1 badfmt")
    T = h.text()
    row("DF10a3 an item the form cannot show opens as text by default too, with the reason said: no form, nothing written", not form_up(h) and "cannot show" in T and disk("badfmt") == FIXTURE["badfmt"], repr((T[-300:], disk("badfmt"))))
    leave(h)
    h = ide("ide dict zzdf1 newdef")
    row("DF10a4 a new item opens as the form by default: only the Type (new item), nothing written until it is accepted", form_up(h) and "(new item)" in h.text() and "Field #:" not in h.text() and disk("newdef") == "ABSENT",
        repr((form_up(h), disk("newdef"))))
    h.key("esc", idle=1.5)
    leave(h)
    h = ide("ide dict zzdf1 fld /text")
    T = h.text()
    row("DF10a5 a last word /text opens the item as text: the editor shows its lines (Name, 10L), no form", not form_up(h) and "dict zzdf1 fld" in T and "Name" in T and "10L" in T, T[:300])
    h.key("esc", idle=1.0)
    h.key("right", idle=0.6)                           # Edit (S.180, 8 Nov 26: after File)
    h.key("right", idle=0.8)                           # Go
    T = h.text()
    row("DF10b the Go menu lists 'Dictionary item as form'", "Dictionary item as form" in T, T[:900])
    h.typed("m", idle=2.0)
    row("DF10c ...and choosing it opens the form", form_up(h) and "Field #:" in h.text(), h.text()[:300])
    h.key("esc", idle=1.5)
    row("DF11 Cancel (Esc) leaves the form with the item as text in its tab and writes nothing", not form_up(h) and "dict zzdf1 fld" in h.text() and disk("fld") == FIXTURE["fld"], repr((form_up(h), disk("fld"))))
    leave(h)

    say("\n--- Len & Just")
    reset()
    h = ide("ide dict zzdf1 fld /form")
    for _ in range(4):
        h.key("tab")
    h.typed("\x15", idle=0.3)
    h.typed("12 r 2", idle=0.4)
    h.key("enter", idle=2.5)
    row("DF12a Len & Just typed as `12 r 2` is written as 12R2 and nothing else changed", disk("fld") == "D|2||Name|12R2|S" and not form_up(h), repr((disk("fld"), h.text()[-300:])))
    leave(h)
    reset()
    h = ide("ide dict zzdf1 fld /form")
    for _ in range(4):
        h.key("tab")
    h.typed("\x15", idle=0.3)
    h.typed("30 X", idle=0.4)
    h.key("tab", idle=0.8)
    T = h.text()
    row("DF12b a bad Len & Just (30 X) is named in the err line when the row is left, with what is wanted", "! Len & Just: a width from 1 to 200, then L, R, T or C" in T, T[-700:])
    h.key("enter", idle=1.5)
    T = h.text()
    row("DF12c Accept is refused with the same message, the form stays and the disk is as it was", form_up(h) and "a width from 1 to 200" in T and disk("fld") == FIXTURE["fld"], repr((form_up(h), disk("fld"))))
    h.key("esc", idle=1.5)
    leave(h)


if __name__ == "__main__":
    sys.exit(main())
