#!/usr/bin/env python3
#
# sandbox-ai-pages.py - the AI line on a PAGE of the toolkit ($tk_aipage; S.97 stage 1), pilot pages tool.voc and tool.files, driven on a pseudo-terminal as an ORDINARY session on a private
# SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ai-pages.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of a program and exit 0 means the rows that had to fail failed and no others (MUTANTS below).
#
# WHAT RUNS.  Everything sandbox-ai-line.py runs - the real helper (gplbld/sd-ai, served by ai-runner.py: the person who runs this suite is "in the AI group", which is the gate), the fake
# provider (gplbld/fakemodel.py, which LOGS every request and answers in the toolkit's JSON form when the last line of the prompt carries a marker such as [[act_refresh]]) and an ordinary
# fixture account (zzhd) - and this file loads that one and uses its helpers.  The program under test is tool.voc, then tool.files, typed at the prompt on a 140 by 43 pty.
#
# THE INSTRUMENT.  "Nothing was sent" is judged by the FAKE's request log and the audit file, not by what the screen said; "the page did it" by the page's own status message; the
# layout by the rows of the emulated screen.  Every row that needs a request counts one arriving at the fake first.
#
#   P0a-P0e  the AI is OFF for the account (the gate off): the page is what it always was - the detail box's border is on row 39, the list has 16 rows and its foot is on row 19, no key
#            F6 on the key row, no AI title in the menu bar, F6 does nothing; tool.files the same
#   P1a-P1e  the AI is ON: the line is on row 39 with the dim hint that says F6, the key row has F6, the menu bar has AI between View and Help, the list is ONE row shorter (15 entries, foot
#            on row 18) and the detail box starts on row 22 and ends on row 38; the page's own keys still work; tool.files the same
#   P2a-P2d  F6 gives the line the focus (the status line says how to use it), what is typed is in the line, Esc gives the focus back and keeps the text, a click on the line gives it the focus
#   P3a-P3c  Enter shows everything that will leave the machine, the actions the page OFFERS (type, state, filter, refresh) and NOT the ones it does not (edit, delete, quit, help); Cancel is the
#            default and nothing is sent
#   P4a-P4b  Send: ONE request at the fake with the typed request as the last line and ONE audit line from the kernel
#   P5a-P5d  an action the AI names is carried out by the PAGE'S OWN KEY once the person chooses Accept (Enter alone, it only navigates): refresh says it read the VOC again, type changes the
#            type shown; delete, which the page has but did not offer, is ignored and said so (11649) and no box appears; the page is whole again after the popup
#   P6a-P6b  tool.files: a proposal of refresh is carried out by that page's own key
#   P7a-P7f  (S.97 stage 2, 1 Nov 26) the AI off: tool.catalog, tool.gates (the holder's page), tool.dict, tool.test, tool.query and tool.bulk have no AI row, no F6 and no AI title
#   P8x1-x3  the AI on, each of those six: the line, F6 and AI in the bar; the preview offers the page's navigation actions and NOT one that does something (compile, help, delete,
#            run, run, apply); Cancel sends nothing
#   P9x1-x3  (group B and stage 3) the administrator's eleven pages in an administrator's session with the AI on: the line, F6, AI in the bar; the preview offers the page's
#            navigation and NOT the one action that changes something (delete, export, restore, edit, queue, syncall, ssh, logout, change, key, change); Cancel sends nothing.
#            my.menu is not here (it needs pins-on); test-aipage-units AP11t/AP12t hold its wiring as text
# NOT HELD: the IDE hand-over (E on an entry) and the line after it, a window other than 140 by 43, Esc during the wait, a command from the model (none is run: nocmd), a destructive action.
import importlib.util
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


al = _load("sandbox_ailine_for_pages", "sandbox-ai-line.py")
sh, g, q3 = al.sh, al.g, al.q3
say, bail, has, dump, adm, H = al.say, al.bail, al.has, al.dump, al.adm, al.H
KEY, MODEL = al.KEY, al.MODEL
ACCT = al.ACCT
FAILED_IDS = []
SCREEN = [None]
PROGS = ("tk_ai", "tk_aipage", "tk_frame", "tk_keys", "tk_layout", "tool_voc", "tool_files",
         "tool_catalog", "tool_mygates", "tool_dict", "tool_test", "tool_query", "tool_bulk",     # 1 Nov 26: the pages of S.97 stage 2
         "tool_accounts", "tool_audit", "tool_backups", "tool_config", "tool_gates", "tool_masters", "tool_remote", "tool_sessions", "tool_viewers", "tool_ai",
         "tool_menus", "mymenu")                                                                  # group B and stage 3

# 1 Nov 26 (S.97 stage 2): the pages that got the line in stage 2, each with the ids it offers the model and one id it has and must NOT offer (an action that does
# something).  Sections P7 (the AI off) and P8 (the AI on, the preview and Cancel) run each of them.
MORE = (("tool.catalog", ["filter", "refresh"], "compile"),
        ("tool.gates", ["refresh"], "help"),                  # in an ordinary account tool.gates is the holder's page (tool_mygates)
        ("tool.dict", ["filter", "refresh"], "delete"),       # it starts in the Files pane: the Items and Indices views are offered from the panes that have them
        ("tool.test", ["filter", "refresh", "runspane"], "run"),
        ("tool.query", ["filter", "reread"], "run"),
        ("tool.bulk", ["switch", "refresh"], "apply"))
FILES = ("gpl.bp/tk.h",) + tuple("gpl.bp/" + n for n in PROGS) + ("messages/11943", "messages/11944")

MUTANTS = {
    # name: (program of the sandbox, old text, new text, the row ids that must fail and no others)
    # the row is taken whether or not a page asked: a page with the AI off is one row shorter
    "row-always": ("tk_layout", "ctx<TK.C.YSTAT> - TK.YBODY - (if ctx<TK.C.AIROW> then 1 else 0)", "ctx<TK.C.YSTAT> - TK.YBODY - 1", ["P0a", "P0b", "P0d"]),
    # every action of the table is offered to the model, not only the ones the page opted in
    "offers-all": ("tk_keys", "            if keys<i, TK.K.AI> = 1 and fa # '' and index(seen,", "            if fa # '' and index(seen,", ["P3a"]),
}


def arow(rid, name, ok, detail=""):
    sh.row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


def sync_and_compile(mutant):
    for rel in FILES:
        shutil.copyfile(os.path.join(TREE, "sdsys", rel), os.path.join(sh.SYS, rel))
    if mutant is not None:
        prog, old, new, _kills = MUTANTS[mutant]
        path = os.path.join(sh.SYS, "gpl.bp", prog)
        src = open(path, encoding="utf-8", errors="replace").read()
        if src.count(old) != 1:
            bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
        g.put(path, src.replace(old, new))
        say("sandbox-ai-pages: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][3])))
    for n in PROGS:
        out = q3.adm(["BASIC gpl.bp " + n], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (n, "\n".join(out[-8:])))


def page(prog):
    h = H(ACCT)
    SCREEN[0] = h
    h.typed(prog + "\r", idle=3.5)
    return h


def requests():
    return al.requests()


def msg(n, *args):
    return al.msg(n, *args)


def corner(h, r):
    """a box's bottom border starts the row: the emulated terminal draws it with + (no UTF-8 in this session), a UTF-8 terminal with a corner"""
    return h.line(r)[1:2] in ("└", "+")


def whole(h, title):
    return title in h.text() and "File" in h.line(0)


def ask(h, text):
    """F6, the request typed, Enter: the preview."""
    h.key("f6", idle=0.8)
    h.typed(text, idle=0.6)
    h.key("enter", idle=1.5)


def sec_off():
    say("\n--- P0: the AI is off for the account (the gate): the pages are what they were")
    al.configure()
    al.start_runner("zz-no-such-gate-group")
    h = page("tool.voc")
    if "The entry under the cursor" not in h.text():
        dump(h)
        bail("tool.voc never drew its page in an ordinary account, so no row below can be believed")
    T = h.text()
    arow("P0a", "tool.voc, AI off: row 39 is the detail box's border (no AI row), no F6 on the key row, no AI title in the menu bar",
         corner(h, 39) and "AI>" not in T and "F6" not in h.line(42) and not re.search(r"\bAI\b", h.line(0)[:60]), repr((h.line(39)[:30], h.line(42)[:100], h.line(0)[:50])))
    arow("P0b", "...the list pane is the size it always was: its foot is on row 19 and the detail box starts on row 23",
         "entries," in h.line(19) and "The entry under the cursor" in h.line(23), repr((h.line(19)[:50], h.line(23)[:50])))
    h.key("f6", idle=1.0)
    arow("P0c", "...F6 does nothing: the status line does not say how to use the line, the page is whole", msg(11638) not in h.line(40) and whole(h, "The entry under the cursor"), repr(h.line(40)[:90]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    h = page("tool.files")
    T = h.text()
    arow("P0d", "tool.files, AI off: row 39 is the detail box's border, no AI row, no F6 on the key row, no AI title", corner(h, 39) and "AI>" not in T and "F6" not in h.line(42)
         and not re.search(r"\bAI\b", h.line(0)[:60]), repr((h.line(39)[:30], h.line(42)[:100], h.line(0)[:50])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_on():
    say("\n--- P1: the AI is on: the line, the key, the menu and the layout")
    al.configure()
    al.start_runner()
    h = page("tool.voc")
    arow("P1a", "tool.voc, AI on: the AI row is on row 39 with the dim hint that says F6", h.line(39).lstrip().startswith("AI>") and msg(11943) in h.line(39), repr(h.line(39)[:90]))
    arow("P1b", "...the key row has F6 and the menu bar has AI between View and Help", "F6 ask ai" in h.line(42) and re.search(r"File\s+Entry\s+View\s+AI\s+Help", h.line(0)) is not None,
         repr((h.line(42)[:110], h.line(0)[:50])))
    arow("P1c", "...the list pane is ONE row shorter (its foot on row 18) and the detail box is on rows 22 to 38, the AI row under it",
         "entries," in h.line(18) and "The entry under the cursor" in h.line(22) and corner(h, 21) and corner(h, 38), repr((h.line(18)[:40], h.line(21)[:6], h.line(22)[:40], h.line(38)[:6])))
    h.typed("t", idle=1.0)
    arow("P1d", "...the page's own keys work with the line there: T changes the type shown and the page says so", "verbs" in h.line(40), repr(h.line(40)[:90]))
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.5)
    h.end()
    h = page("tool.files")
    arow("P1e", "tool.files, AI on: the AI row on row 39, F6 on the key row, AI in the menu bar, the detail box ends on row 38 and the list is above it",
         h.line(39).lstrip().startswith("AI>") and "F6 ask ai" in h.line(42) and re.search(r"File\s+\S+\s+View\s+AI\s+Help|AI\s+Help", h.line(0)) is not None and corner(h, 38), repr((h.line(39)[:50], h.line(42)[:110], h.line(0)[:60])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_focus():
    say("\n--- P2: the focus")
    h = page("tool.voc")
    h.key("f6", idle=0.8)
    arow("P2a", "F6 gives the line the focus: the status line says how to use it and the label is bold", msg(11638) in h.line(40), repr(h.line(40)[:90]))
    h.typed("abc", idle=0.6)
    arow("P2b", "what is typed is in the line and the page's keys did not take it (the type shown did not change)", "abc" in h.line(39) and "verbs" not in h.line(40), repr((h.line(39)[:40], h.line(40)[:60])))
    h.key("esc", idle=0.8)
    arow("P2c", "Esc gives the focus back to the page and keeps the text; the status line no longer says how to use the line", "abc" in h.line(39) and msg(11638) not in h.line(40) and "File" in h.line(0), repr((h.line(39)[:40], h.line(40)[:60])))
    h.click(40, 39, idle=1.0)
    arow("P2d", "a click on the line gives it the focus", msg(11638) in h.line(40), repr(h.line(40)[:90]))
    h.key("esc", idle=0.8)
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_preview():
    say("\n--- P3: the preview and Cancel")
    fm = al.STATE["fm"]
    h = page("tool.voc")
    n0, a0 = len(fm.log), al.audit_off()
    ask(h, "read it again [[act_refresh]]")
    T = h.text()
    arow("P3a", "Enter shows the preview: the page's actions - type, state, filter, refresh - and NOT edit, delete, quit, help or the AI itself; the page says what it is; nothing has been sent",
         "  type:Type shown" in T and "  state:State shown" in T and "  filter:Filter by name" in T and "  refresh:Refresh" in T and "  edit:" not in T and "  delete:" not in T
         and "  quit:" not in T and "  help:" not in T and "  ai:" not in T and "the page tool.voc of the SD database system" in T and "read it again [[act_refresh]]" in T and len(fm.log) == n0, T[-1100:])
    arow("P3b", "...with Send and Cancel", "Send" in T and "Cancel" in T, T[-500:])
    h.key("enter", idle=1.5)
    arow("P3c", "Enter on the default button is Cancel: nothing was sent (the fake's log and the audit file agree), the status line says so and the page is whole",
         len(fm.log) == n0 and not al.req_lines(al.audit_new(a0)) and msg(11630) in h.line(40) and whole(h, "The entry under the cursor"), repr((len(fm.log) - n0, h.line(40)[:80])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_send():
    say("\n--- P4 and P5: Send, and what the page does with the answer")
    fm = al.STATE["fm"]
    h = page("tool.voc")
    n0, a0 = len(fm.log), al.audit_off()
    ask(h, "read it again [[act_refresh]]")
    h.typed("s", idle=4.0)
    rq = requests()
    last = rq[-1] if len(rq) > n0 else (None, {}, None)
    body = last[2] or {}
    prompt = body["messages"][-1]["content"] if body.get("messages") else ""
    arow("P4a", "Send: ONE request at the fake, with the key and the model; the prompt lists the offered actions and ends with the typed request",
         len(fm.log) == n0 + 1 and last[1].get("x-api-key") == KEY and body.get("model") == MODEL and "  refresh:Refresh" in prompt and "  delete:" not in prompt
         and prompt.endswith("Request: read it again [[act_refresh]]"), repr((len(fm.log) - n0, prompt[-120:])))
    rl = al.req_lines(al.audit_new(a0))
    arow("P4b", "ONE audit line from the kernel before the request: the account, the program (tk_ai); neither the request nor the key is in the audit trail",
         len(rl) == 1 and re.search(r"ai request account=%s program=tk_ai bytes\.out=\d+$" % ACCT, rl[0]) is not None and "read it again" not in al.audit_new(a0) and KEY not in al.audit_new(a0), repr(rl))
    T = h.text()
    arow("P5a", "the answer is a popup: what the AI said and the proposal with Accept and Reject; nothing has been done yet", "Reading the page again." in T and msg(11647, "Refresh") in T and "Accept" in T
         and "Reject" in T and "read the VOC again" not in h.line(40), T[-800:])
    h.key("enter", idle=3.0)
    arow("P5b", "Enter alone accepts (it only navigates): the page's own F5 ran - its status line says it read the VOC again - and the page is whole, the AI row under it",
         "read the VOC again" in h.line(40) and whole(h, "The entry under the cursor") and h.line(39).lstrip().startswith("AI>") and "entries," in h.line(18), repr((h.line(40)[:80], h.line(39)[:50])))
    ask(h, "show only the verbs [[act_type]]")
    h.typed("s", idle=4.0)
    h.key("enter", idle=2.5)
    arow("P5c", "a proposal of type is carried out by the page's own T key: the type shown changes and the status line says so", "verbs" in h.line(40), repr(h.line(40)[:90]))
    h.key("esc", idle=1.0)
    ask(h, "delete it [[act_delete]]")
    h.typed("s", idle=4.0)
    T = h.text()
    arow("P5d", "delete is a key of the page but was not offered: the proposal is ignored and said so (11649), only a Close button, and no box of the page's own appeared",
         msg(11649, "delete") in T and "Close" in T and "Accept" not in T, T[-700:])
    h.key("enter", idle=1.5)
    arow("P5e", "...Close returns to the page, whole, and the entry is there", whole(h, "The entry under the cursor") and "$acc" in h.text(), repr(h.line(40)[:80]))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_files():
    say("\n--- P6: tool.files")
    h = page("tool.files")
    ask(h, "read it again [[act_refresh]]")
    T = h.text()
    arow("P6a", "tool.files offers filter and refresh and not delete, clear or new", "  refresh:Refresh" in T and "  filter:Filter the names" in T and "  delete:" not in T and "  clear:" not in T and "  new:" not in T, T[-900:])
    h.typed("s", idle=4.0)
    h.key("enter", idle=3.0)
    arow("P6b", "a proposal of refresh is carried out by the page's own F5: it read the files again", "read the files again" in h.line(40), repr(h.line(40)[:90]))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_more_off():
    """P7: with the AI off (the runner sec_off started, with no such gate group) each stage 2 page draws no AI row, no F6 and no AI title.  Runs straight after sec_off."""
    say("\n--- P7: the AI is off: the stage 2 pages are what they were")
    for i, (verb, _offers, _not) in enumerate(MORE):
        h = page(verb)
        drawn = "File" in h.line(0) and "Help" in h.line(0)
        arow("P7" + "abcdef"[i], "%s, AI off: the page is drawn, no AI row on row 39, no F6 on the key row, no AI title in the menu bar" % verb,
             drawn and not h.line(39).lstrip().startswith("AI>") and "F6 ask ai" not in h.line(42) and re.search(r"\bAI\b", h.line(0)) is None,
             repr((h.line(0)[:70], h.line(39)[:40], h.line(42)[:100])))
        h.key("ctrl-q", idle=1.5)
        h.end()


def sec_more_on():
    """P8: with the AI on each stage 2 page has the line, F6 and the AI title; the preview lists exactly the actions it offers and not one it has that does something; Cancel sends
    nothing (the fake's log is the evidence)."""
    say("\n--- P8: the AI is on: the stage 2 pages - the line, the key, the menu, the preview and Cancel")
    fm = al.STATE["fm"]
    for i, (verb, offers, notoff) in enumerate(MORE):
        L = "abcdef"[i]
        h = page(verb)
        arow("P8" + L + "1", "%s, AI on: the AI row on row 39, F6 ask ai on the key row and AI in the menu bar" % verb,
             h.line(39).lstrip().startswith("AI>") and "F6 ask ai" in h.line(42) and re.search(r"\bAI\s+Help", h.line(0)) is not None,
             repr((h.line(0)[:80], h.line(39)[:50], h.line(42)[:110])))
        n0 = len(fm.log)
        ask(h, "what can I do here [[act_refresh]]")
        T = h.text()
        arow("P8" + L + "2", "%s: the preview offers %s and NOT %s, and nothing has been sent" % (verb, ", ".join(offers), notoff),
             all(("  %s:" % o) in T for o in offers) and ("  %s:" % notoff) not in T and "  ai:" not in T and ("the page %s of the SD database system" % verb) in T and len(fm.log) == n0,
             T[-900:])
        h.key("enter", idle=1.5)
        arow("P8" + L + "3", "%s: Enter on the default button is Cancel: nothing was sent and the page is drawn again" % verb,
             len(fm.log) == n0 and msg(11630) in h.line(40) and "File" in h.line(0), repr((len(fm.log) - n0, h.line(40)[:80])))
        h.key("ctrl-q", idle=1.5)
        h.end()


ADMIN_MORE = (("tool.accounts", ["refresh"], "delete"),
              ("tool.audit", ["filter", "clear", "goto", "follow", "refresh"], "export"),
              ("tool.backups", ["refresh"], "restore"),
              ("tool.config", ["parameters", "refresh"], "edit"),
              ("tool.gates", ["filter", "refresh"], "queue"),
              ("tool.masters", ["journal", "refresh"], "syncall"),
              ("tool.remote", ["doors", "routes", "refresh"], "ssh"),
              ("tool.sessions", ["switch", "output", "refresh"], "logout"),
              ("tool.viewers", ["pane", "output", "refresh"], "change"),
              ("tool.ai", ["pane", "refresh"], "key"),
              ("tool.menus", ["pane", "refresh"], "change"))


def dialog_text(h):
    """The text inside the Ask the AI dialog, rows joined, white space taken out.  The dialog sits over the page, so a screen row carries the page's own text (its [?] and [-]
    marks, a border) beyond the dialog's edge, and a long line is cut inside a word at that edge and goes on in the next row: only the columns between the dialog's own corners
    are read, found from the title row.  An empty string when no dialog is on the screen."""
    top = next((r for r in range(43) if "- Ask the AI" in h.line(r)), None)
    if top is None:
        return ""
    row = h.line(top)
    left = row.index("- Ask the AI") - 1
    right = row.index("+", left + 1)
    out = ""
    for r in range(top + 1, 43):
        line = h.line(r)
        if line[left:left + 1] == "+":            # the dialog's bottom corner
            break
        out += line[left + 1:right]
    return re.sub(r"\s+", "", out)


def sec_admin_pages():
    """P9 (S.97 stage 2 group B and stage 3, 1 Nov 26): the administrator's pages, in an administrator's session with the AI on - the line, F6 and the AI title; the preview offers
    the page's navigation and NOT the one action of each that changes something (the owner's default: nothing that changes an account, a gate, a session, a door, a setting or a
    backup); Cancel sends nothing.  The pages with the AI off are their own suites' business (they run without it and pin the layout)."""
    say("\n--- P9: the administrator's pages, the AI on: the line, the key, the menu, the preview and Cancel")
    fm = al.STATE["fm"]
    sh.set_default("terminal")
    for i, (verb, offers, notoff) in enumerate(ADMIN_MORE):
        L = "abcdefghijk"[i]
        h = H(None, admin=True)
        SCREEN[0] = h
        h.typed(verb + "\r", idle=3.5)
        # (tool.ai's key row was full before the line came - it is cut at "F5 r" - so F6 cannot show there; a FULL row is accepted, said in the row's name)
        kr = h.line(42).rstrip()
        arow("P9" + L + "1", "%s (administrator, AI on): the AI row on row 39, AI in the menu bar, and F6 ask ai on the key row (or the row is full to the edge)" % verb,
             h.line(39).lstrip().startswith("AI>") and ("F6 ask ai" in kr or len(kr) >= 138) and re.search(r"\bAI\s+Help", h.line(0)) is not None,
             repr((h.line(0)[:80], h.line(39)[:50], kr[:110], len(kr))))
        n0 = len(fm.log)
        ask(h, "what can I do here [[act_refresh]]")
        T = h.text()
        flat = dialog_text(h)                     # the preview is a box: a sentence wraps across its rows and a long line is cut inside a word at the box's edge
        arow("P9" + L + "2", "%s: the preview offers %s and NOT %s, says the person is the administrator, and nothing has been sent" % (verb, ", ".join(offers), notoff),
             all(("  %s:" % o) in T for o in offers) and ("  %s:" % notoff) not in T and "  ai:" not in T and ("thepage%softheSDdatabasesystem" % verb) in flat
             and "Thepersonistheadministrator." in flat and len(fm.log) == n0, T[-900:])
        h.key("enter", idle=1.5)
        arow("P9" + L + "3", "%s: Enter on the default button is Cancel: nothing was sent and the page is drawn again" % verb,
             len(fm.log) == n0 and msg(11630) in h.line(40) and "File" in h.line(0), repr((len(fm.log) - n0, h.line(40)[:80])))
        h.key("ctrl-q", idle=1.5)
        h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-ai-pages.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    try:
        sh.setup("sandbox-ai-pages.py")
        al.setup_ai(None)
        sync_and_compile(mutant)
        sec_off()
        if mutant is None:
            sec_more_off()
            sec_on()
            sec_focus()
            sec_preview()
            sec_send()
            sec_files()
            sec_more_on()
            sec_admin_pages()
        elif mutant == "offers-all":
            sec_on()
            sec_preview()
    finally:
        al.stop_runner()
        sh.teardown()
    say("\nsandbox-ai-pages: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][3]))
        got = sorted({re.match(r"P\d+[a-z]", i).group(0) for i in FAILED_IDS if re.match(r"P\d+[a-z]", i)})
        ok = want == got
        say("sandbox-ai-pages: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
