#!/usr/bin/env python3
#
# sandbox-docs.py - the shared account's documentation (S.75, plan .claude/plan-fullscreen-toolkit.md section 14): the context help file and its [?] buttons, docs.install and
# the menu verb, on a private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-docs.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  It uses sandbox-home.py's setup (the same fixture accounts, ORDINARY sessions through sandbox-gates.py, the sandbox starting at the terminal) and its session class.
#
# START-HISTORY:
# 23 Oct 26 dm  New (S.75, plan section 14).
# 3 Nov 26 dm   tool.gates.matrix's words: "drops" (U drops them) for "everything", which left the record with its sentence "There is no key that
#               queues everything ON" when A and N were added (427cfa0d, 1 Nov); the click and F1 rows failed on a correct record.
# 9 Nov 26 (S.187): the pdf verb, set.viewer and the Bypass programs page (tool.viewers) were REMOVED from Core (owner: pdf only works at the machine's own display).  Their
#               sections went with them: pdf (the list, every refusal, the viewer started, the audit line), set.viewer, and tool.viewers.  docs.install's "...and PDF lists it"
#               row now reads the pdf directory.  The help box has no Documentation button: the F1 row looks for Close and NO Documentation button, and the row that pressed
#               it now holds that the box's last line names the PDF (message 14046) and that 'd' starts nothing.  The administrator's System group row names Audit trail.
#               NOT RUN since (the owner's rule for this sitting: free checks only).
# END-HISTORY
#
# THE SHARED ACCOUNT HERE.  The sandbox cannot make Linux groups, so shared is a hand-made register record  <path>\n...\nsdg_shared, the directory <sandbox>/group_accounts/shared with a
# VOC made from NEWVOC, and a pdf directory with fixture documents.  LOAD.HELP enters the shared account, which the administrator may do only if the sandbox user is in its register
# group, so the group is set to the user's own for that one command and put back to sdg_shared (the delivered one) before any other row.
#
# THE FIXTURE DOCUMENTS.  Each is given an old modification time (OLD); the help box's rows hold that nothing touched them (the box opens no document since S.187).
#
# WHAT IS HELD.  The store: nothing before LOAD.HELP, the records equal the shipped files, a second run changes nothing, a changed file is written and an added record is kept, bad
# names are skipped; $tk_help for SDSYS, for an ordinary account and for one whose shared.read is withdrawn, with a key that is not a key.  DOCS.INSTALL.  The pages: [?] on every
# row, F1, ?, a click, the one Close button and the last line naming the PDF (14046).  MENU opens the home screen; the administrator's page has the tiles of the System group.
# NOT HELD: the installer's blocks (test-install-docs.sh and a real install), the group modes of the files LOAD.HELP makes (one OS user here).
import importlib.util
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sandbox_home_for_docs", os.path.join(HERE, "sandbox-home.py"))
sh = importlib.util.module_from_spec(spec)
sys.modules["sandbox_home_for_docs"] = sh
spec.loader.exec_module(sh)
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
OLD = 1000000000                                  # the modification time given to a fixture document: a viewer that touches it moves it
HELPSRC = os.path.join(HERE, os.pardir, "sdsys", "helptext")
DOCS = {"administrator-01-accounts-and-security.pdf": b"%PDF-1.4\naccounts\n", "guide-one.pdf": b"%PDF-1.4\none\n", "guide-two.pdf": b"%PDF-1.4\ntwo\n", "Upper.pdf": b"%PDF-1.4\nupper\n",
        "notes.txt": b"not a pdf\n"}


def S():
    return os.path.join(sh.BOX, "group_accounts", "shared")


def pdfp(name):
    return os.path.join(S(), "pdf", name)


def mtime(name):
    """Modification time of a fixture document, named as the pdf verb names it (without .pdf)."""
    return int(os.path.getmtime(pdfp(name if name.endswith(".pdf") else name + ".pdf")))


def reset_times():
    for n in DOCS:
        os.utime(pdfp(n), (OLD, OLD))


def touched(name, wait=6.0):
    end = time.time() + wait
    while time.time() < end:
        if mtime(name) > OLD + 1000:
            return True
        time.sleep(0.2)
    return False


def untouched(name, wait=2.0):
    time.sleep(wait)
    return mtime(name) == OLD


def shared_reg(group):
    g.put(os.path.join(sh.SYS, "accounts", "shared"), "\n".join([S(), "The shared account", group, "", ""]) + "\n")


def viewers_file():
    p = os.path.join(sh.SYS, "viewers")
    try:
        with open(p) as f:
            return f.read()
    except OSError:
        return None


def audit_tail(off):
    try:
        with open(os.path.join(sh.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def audit_size():
    """The size of the audit file now; an absent file is made empty first, because the kernel writes audit lines only to a file that is there (sandbox-shared.py's audit_off)."""
    path = os.path.join(sh.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return 0


def expected_help():
    """What LOAD.HELP must have written: id -> (title, doc, number of paragraphs), from the shipped files."""
    out = {}
    for n in sorted(os.listdir(HELPSRC)):
        with open(os.path.join(HELPSRC, n), encoding="latin-1") as f:
            lines = f.read().rstrip("\n").split("\n")
        out[n] = (lines[0].rstrip(), lines[1].strip() if len(lines) > 1 else "", len(lines) - 2)
    return out


PROBES = {
    "hlook": ["$internal", "program hlook", "$catalog $hlook",
              "   key = field(trim(@sentence), ' ', 2)",
              "   call $tk_help('text', key, t, l, d)",
              "   crt 'HT=' : t",
              "   crt 'HD=' : d",
              "   for i = 1 to dcount(l, @fm)",
              "      crt 'HL=' : l<i>",
              "   next i", "end", ""],
    "hids": ["$internal", "program hids", "$catalog $hids",
             "   openpath '%s/context.help' to f else crt 'HIDS no file' ; stop",
             "   select f to 11", "   n = 0", "   loop", "      readnext id from 11 else exit",
             "      read r from f, id then",
             "         crt 'ID=' : id : '|' : r<1> : '|' : r<2> : '|' : (dcount(r, @fm) - 2)",
             "         n += 1", "      end", "   repeat", "   crt 'N=' : n", "end", ""],
    "hadd": ["$internal", "program hadd", "$catalog $hadd",
             "   openpath '%s/context.help' to f else crt 'HADD no file' ; stop",
             "   write 'Site note' : @fm : '' : @fm : 'kept by the administrator' to f, 'site.note'",
             "   crt 'HADD done'", "end", ""],
}


def make_probes():
    for nm, src in PROBES.items():
        text = "\n".join(src)
        if "%s" in text:
            text = text % S()
        g.put(os.path.join(sh.SYS, "gpl.bp", nm), text)
    out = adm("BASIC gpl.bp hlook hids hadd")
    if not has(out, r"^Compiled 3 program\(s\) with no errors"):
        bail("the probes did not compile:\n" + "\n".join(out[-8:]))


def make_shared():
    """Idempotent: a rerun on a sandbox that was already used (no --build) starts from nothing again."""
    for stale in (S(), os.path.join(sh.SYS, "viewers"), os.path.join(sh.BOX, "docsrc")):
        if os.path.isdir(stale):
            shutil.rmtree(stale)
        elif os.path.exists(stale):
            os.remove(stale)
    os.makedirs(os.path.join(S(), "pdf"), exist_ok=True)
    shared_reg("sdg_shared")
    accts = ":@fm:".join("'" + a + "'" for a in ("zzhd", "zzhm", "zzht", "zzhv"))
    g.put(os.path.join(sh.SYS, "bp", "dcfix"), "\n".join([
        "$internal",
        "   s = '%s'" % S(),
        "   create.file s:'/voc' dynamic on error crt 'DCFIX create voc failed' ; stop",
        "   openpath s:'/voc' to v else crt 'DCFIX open voc failed' ; stop",
        "   openpath '%s/newvoc' to nv else crt 'DCFIX no newvoc' ; stop" % sh.SYS,
        "   select nv to 11",
        "   loop",
        "      readnext id from 11 else exit",
        "      read rec from nv, id then write rec to v, id",
        "   repeat",
        "   close nv",
        "   write 'X' to v, '$command.stack'",
        "   close v",
        "   for each a in " + accts,
        "      openpath '%s/user_accounts/':a:'/voc' to av else crt 'DCFIX no voc ':a ; stop" % sh.BOX,
        "      write 'V':@fm:'CA':@fm:'$hlook' to av, 'hlook'",
        "      close av",
        "   next a",
        "   openpath '%s/voc' to sv else crt 'DCFIX no sys voc' ; stop" % sh.SYS,
        "   write 'V':@fm:'CA':@fm:'$hlook' to sv, 'hlook'",
        "   write 'V':@fm:'CA':@fm:'$hids' to sv, 'hids'",
        "   write 'V':@fm:'CA':@fm:'$hadd' to sv, 'hadd'",
        "   close sv",
        "   crt 'DCFIX done'",
        "end", ""]))
    out = adm("BASIC bp dcfix", "RUN bp dcfix")
    if not has(out, r"^DCFIX done$"):
        bail("the shared account was not built:\n" + "\n".join(out[-8:]))
    for n, data in DOCS.items():
        with open(pdfp(n), "wb") as f:
            f.write(data)
    os.symlink("/etc/hostname", pdfp("linked.pdf"))
    os.makedirs(pdfp("adir.pdf"), exist_ok=True)
    reset_times()


def load_help():
    """LOAD.HELP needs the administrator to be able to enter the shared account: the register group is the sandbox user's own for this one command."""
    shared_reg(g.GROUP)
    out = adm("load.help")
    shared_reg("sdg_shared")
    return out


def counts(out):
    """(new, changed, already current, kept) from LOAD.HELP's summary line, or None."""
    for l in out:
        m = re.match(r"^Context help in the shared account: (\d+) new, (\d+) changed, (\d+) already current, (\d+) added by the administrator and kept$", l)
        if m:
            return tuple(int(x) for x in m.groups())
    return None


def hlook(acct, key):
    out = g.adm(["hlook " + key], internal=True) if acct is None else g.plain(acct, ["hlook " + key])
    t = [l[3:] for l in out if l.startswith("HT=")]
    d = [l[3:] for l in out if l.startswith("HD=")]
    ls = [l[3:] for l in out if l.startswith("HL=")]
    return (t[0] if t else None), (d[0] if d else None), ls, out


def hids():
    out = adm("hids")
    recs = {}
    for l in out:
        m = re.match(r"^ID=([^|]*)\|([^|]*)\|([^|]*)\|(\d+)$", l)
        if m:
            recs[m.group(1)] = (m.group(2), m.group(3), int(m.group(4)))
    n = [int(l[2:]) for l in out if re.match(r"^N=\d+$", l)]
    return recs, (n[0] if n else None), out


def open_page(verb, admin=True):
    h = H(admin=True)
    h.typed(verb + "\r", idle=2.5)
    return h


def main():
    try:
        sh.setup("sandbox-docs.py")
        make_probes()
        make_shared()
        say("\n--- the store: the file context.help of the shared account (LOAD.HELP, $tk_help)")
        t, d, ls, out = hlook(None, "tool.menus.pins")
        row("before LOAD.HELP there is no file: $tk_help answers in words (11830 and 11832), for the administrator", t == "No help has been written for this yet" and any("Help is not installed here" in l for l in ls), repr(out[-4:]))
        out = g.plain("zzhd", ["load.help"])
        row("an ordinary account cannot run LOAD.HELP: the verb is not in its VOC", has(out, r"not in your VOC"), repr(out[:3]))
        expect = expected_help()
        out = load_help()
        n = len(expect)
        row("LOAD.HELP says it wrote every shipped file as new: %d new, 0 changed, 0 already current, 0 kept" % n, counts(out) == (n, 0, 0, 0), repr(out[-4:]))
        row("...and the file context.help is on the disk, in the shared account's directory", os.path.exists(os.path.join(S(), "context.help")), repr(os.listdir(S())))
        recs, cnt, out = hids()
        row("the records ARE the shipped files: the same ids, and each one's title, document and number of paragraphs", recs == expect and cnt == n, repr((sorted(set(expect) ^ set(recs)), cnt, out[-3:])))
        out = load_help()
        row("a second LOAD.HELP changes nothing: 0 new, 0 changed, %d already current" % n, counts(out) == (0, 0, n, 0), repr(out[-4:]))

        pins = os.path.join(sh.SYS, "helptext", "tool.menus.pins")
        with open(pins, encoding="latin-1") as f:
            src = f.read()
        with open(pins, "w", encoding="latin-1") as f:
            f.write(src.replace("Programs of the account's own", "Own programs (edited)", 1))
        out = load_help()
        t, d, ls, o2 = hlook(None, "tool.menus.pins")
        row("a changed shipped file is written (0 new, 1 changed, %d already current) and the title read back is the new one" % (n - 1), counts(out) == (0, 1, n - 1, 0) and t == "Own programs (edited)", repr((out[-2:], t)))
        with open(pins, "w", encoding="latin-1") as f:
            f.write(src)
        load_help()

        out = adm("hadd")
        out = load_help()
        t, d, ls, o2 = hlook(None, "site.note")
        row("a record the administrator added under an id that is not shipped is KEPT (1 kept, nothing else changed) and still read back", counts(out) == (0, 0, n, 1) and t == "Site note", repr((out[-2:], t, ls)))

        for bad, text in (("Bad_Name", "A title\n\ntext\n"), ("no.title", "\n\ntext\n"), (".hidden", "A title\n\ntext\n")):
            with open(os.path.join(sh.SYS, "helptext", bad), "w") as f:
                f.write(text)
        out = load_help()
        recs, cnt, o2 = hids()
        row("a file whose name is not a key (a capital, an underscore, a leading dot) or that has no title is SKIPPED and named, and is not in the file",
            has(out, r"^Skipped Bad_Name in the help text directory: not a key$") and has(out, r"^Skipped \.hidden in the help text directory: not a key$")
            and has(out, r"^Skipped no\.title in the help text directory: has no title$") and not ({"Bad_Name", "bad_name", ".hidden", "no.title"} & set(recs)), repr(out[-5:]))
        for bad in ("Bad_Name", "no.title", ".hidden"):
            os.remove(os.path.join(sh.SYS, "helptext", bad))

        t, d, ls, out = hlook("zzhd", "tool.menus.pins")
        row("an ORDINARY account reads it: the title, the document (administrator-01-accounts-and-security: the book, then the page, S.228) and the paragraphs of the shipped file", t == "Programs of the account's own" and d == "administrator-01-accounts-and-security" and len(ls) == 3 and ls[0].startswith("Off as delivered."), repr((t, d, ls[:1])))
        sh.g.reg_write("zzhd", [os.path.join(sh.BOX, "user_accounts", "zzhd"), "", g.GROUP, "", "", "", "no", "no", "no", "yes", "yes", "yes", "no", "", "", ""])
        t, d, ls, out = hlook("zzhd", "tool.menus.starts-in")
        row("...and so does an account whose shared.read is withdrawn (field 13 = no): the help is the product's documentation, not data", t == "Where an account starts" and len(ls) == 3, repr((t, out[-3:])))
        sh.reg("zzhd", "")
        t, d, ls, out = hlook("zzhd", "Tool.Menus.Pins")
        row("a key is folded to lower case", t == "Programs of the account's own", repr(t))
        t, d, ls, out = hlook("zzhd", "tool.menus.nothing")
        row("a key with no record: the title 11830 and the line 11831 naming the key, not an error", t == "No help has been written for this yet" and any("has no record tool.menus.nothing" in l for l in ls), repr((t, ls)))
        t, d, ls, out = hlook("zzhd", "../etc/passwd")
        row("a key that is not a key (a slash) is not looked up at all: the same words, and no text of any file", t == "No help has been written for this yet" and not any("root:" in l for l in ls) and any("has no record" in l for l in ls), repr((t, ls)))

        # 9 Nov 26 (S.187): the pdf and set.viewer sections went with the verbs (see START-HISTORY)


        # ------------------------------------------------------------------------------------------------ docs.install
        say("\n--- docs.install")
        src = os.path.join(sh.BOX, "docsrc")
        os.makedirs(src, exist_ok=True)
        for n, data in (("good-one.pdf", b"%PDF-1.5\ngood\n"), ("fake.pdf", b"just text\n"), ("Bad.pdf", b"%PDF-1.4\nbad\n"), ("text.txt", b"%PDF-1.4\n")):
            with open(os.path.join(src, n), "wb") as f:
                f.write(data)
        out = g.plain("zzhd", ["docs.install " + src])
        row("an ordinary account cannot run DOCS.INSTALL: not in its VOC", has(out, r"not in your VOC"), repr(out[:3]))
        out = adm("docs.install " + src)
        dest = pdfp("good-one.pdf")
        row("DOCS.INSTALL copies the one good file and names the two it skipped (a capital in the name; no %PDF- at the start); a .txt is not looked at",
            has(out, r"^Copied 1 document\(s\) into the shared account; skipped 2$") and has(out, r"^Skipped Bad\.pdf: the name is not lower case") and has(out, r"^Skipped fake\.pdf: it does not start with %PDF-$"), repr(out[-4:]))
        row("...the copy is on the disk, the same bytes, mode 0644; the others are not there", os.path.exists(dest) and open(dest, "rb").read() == b"%PDF-1.5\ngood\n" and (os.stat(dest).st_mode & 0o777) == 0o644
            and not os.path.exists(pdfp("fake.pdf")) and not os.path.exists(pdfp("Bad.pdf")) and not os.path.exists(pdfp("text.txt")), repr(sorted(os.listdir(os.path.join(S(), "pdf")))))
        row("...and it is a regular file of the pdf directory, beside the fixture documents (the pdf verb that listed them is gone, S.187)",
            os.path.isfile(dest) and not os.path.islink(dest) and "administrator-01-accounts-and-security.pdf" in os.listdir(os.path.join(S(), "pdf")), repr(sorted(os.listdir(os.path.join(S(), "pdf")))))
        out = adm("docs.install /tmp/../etc")
        row("a path with .. in it is refused (11721) and nothing is read", has(out, r"^The directory /tmp/\.\./etc cannot be read, or is not a plain path"), repr(out[-3:]))
        out = adm("docs.install /nonexistent-directory-for-docs")
        row("a directory that is not there is refused (11721)", has(out, r"^The directory /nonexistent-directory-for-docs cannot be read"), repr(out[-3:]))

        # --------------------------------------------------------------------------------- the pages: [?], F1 and the box
        say("\n--- tool.menus: the [?] buttons and the help box")
        reset_times()
        h = open_page("tool.menus")
        T = h.text()
        if "What this means" not in T:
            dump(h)
            bail("tool.menus never drew its page, so no row below can be believed")
        marks = [h.line(r)[134:137] for r in range(2, 11)]
        row("a [?] at the end of each of the nine rows of the Menu box (columns 134 to 136)", marks == ["[?]"] * 9, repr(marks))
        row("...one at the system default and one at the Accounts list", h.line(32)[66:69] == "[?]" and h.line(2)[66:69] == "[?]", repr((h.line(32)[60:72], h.line(2)[60:72])))
        row("the function-key row says F1 help", "F1 help" in h.line(42), repr(h.line(42)))
        h.key("f1", idle=1.2)
        T = h.text()
        row("F1 in the Accounts box shows the help: the title, its first paragraph, the button Close and NO Documentation button (S.187)",
            "The accounts list" in T and "Every registered account except SDSYS" in T and "Documentation" not in T and "Close" in T, T[-700:])
        h.key("esc", idle=0.8)
        T = h.text()
        row("Esc closes it: the box is gone and the page is as it was", "The accounts list" not in T and "What this means" in T and "Accounts" in T, T[-300:])
        h.key("f6", idle=0.6)                       # S.176: F6 is the box key of every page
        h.typed("?", idle=1.2)
        T = h.text()
        row("'?' on the first row of the Menu box (where the account starts) shows that setting's help", "Where an account starts" in T and "start-menu, start-terminal or start-default" in T, T[-500:])
        h.key("esc", idle=0.8)
        h.key("down", idle=0.5)
        h.key("f1", idle=1.2)
        T = h.text()
        row("F1 on the next row (programs of its own) shows that one", "Programs of the account's own" in T and "Off as delivered." in T, T[-500:])
        h.key("esc", idle=0.8)
        for _ in range(3):                                   # 4 before the Record editor tile went (S.88 g-P1): editor, ide, terminal
            h.key("down", idle=0.4)
        h.key("f1", idle=1.2)
        T = h.text()
        row("F1 on the Terminal row says what turning it off does, including that it is a wall only for the prompt the home screen gives",
            "The Terminal tile" in T and "OFF" in T and "wall only for the prompt" in T, T[-700:])
        h.key("esc", idle=0.8)
        h.click(135, 4, idle=1.4)
        T = h.text()
        row("a click on the [?] of the third row (the Editor tile) shows its help", "The Editor tile" in T and "Starts sed" in T, T[-500:])
        h.key("esc", idle=0.8)
        row("...and selected that row (reverse video on the row), so the box answers the row that was clicked", "r" in h.style(4, 75)[2], repr(h.style(4, 75)))
        h.click(67, 32, idle=1.4)
        T = h.text()
        row("a click on the [?] of the system default shows its help", "Where an account with no setting starts" in T, T[-500:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.2)
        reset_times()
        h.key("enter", idle=1.4)
        row("Enter in the box chooses Close, the default: the box closes and no program was started", "Where an account with no setting starts" not in h.text() and untouched("administrator-01-accounts-and-security", 1.5), h.text()[-300:])
        h.key("f1", idle=1.2)
        T = h.text()
        row("the box's last line names the document the record names (message 14046: administrator-01-accounts-and-security.pdf, in the pdf directory of the shared account)",
            "administrator-01-accounts-and-security.pdf" in T and "pdf directory" in T, T[-700:])
        h.typed("d", idle=2.0)
        row("...and 'd' (the old Documentation button's letter) starts nothing: no document was touched and no 'Opened' on the status line",
            untouched("administrator-01-accounts-and-security", 1.5) and "Opened" not in h.line(40), repr(h.line(40)))
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        reset_times()

        # 9 Nov 26 (S.187): the tool.viewers section (the Bypass programs page) went with the page

        # ----------------------------------------------------------------------------------------------- tool.gates (24 Oct 26, S.75 A2): only its help is the docs suite's; the page is sandbox-tool-gates.py's
        say("\n--- tool.gates: the gate matrix's help")
        h = open_page("tool.gates")
        T = h.text()
        if "Gates by account" not in T:
            dump(h)
            bail("tool.gates never drew its page, so no row below can be believed")
        row("a [?] at the end of the matrix box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())                     # the box wraps its text and draws its border between the lines
        words = ("queues", "drops", "modify.account", "Cancel", "files-write")          # single words: the box wraps its text, and a phrase cut at a line end has the rest of that screen row between its halves
        row("a click on the [?] shows the record of tool.gates.matrix: its title and words of its three paragraphs", "The gate matrix" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "The gate matrix" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # ----------------------------------------------------------------------------------------------- tool.sessions (24 Oct 26, S.75 A4): only its help is the docs suite's; the page is sandbox-tool-sessions.py's
        say("\n--- tool.sessions: the sessions and locks page's help")
        h = open_page("tool.sessions")
        T = h.text()
        if "The row under the cursor" not in T:
            dump(h)
            bail("tool.sessions never drew its page, so no row below can be believed")
        row("a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words = ("logout", "unlock", "inhibit.login", "Cancel", "audit")         # single words: the box wraps its text
        row("a click on the [?] shows the record of tool.sessions.page: its title and words of its three paragraphs", "Sessions and locks" in T and all(w in T for w in words) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "Sessions and locks" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # tool.masters' help rows (24 Oct 26, S.75 A7) went with the page on 2 Nov 26 (S.96 M6: the master-file copies of S.67 are retired).
        # ----------------------------------------------------------------------------------------------- tool.audit (25 Oct 26, S.75 A5): only its help is the docs suite's; the page is sandbox-tool-audit.py's
        say("\n--- tool.audit: the audit trail page's help")
        h = open_page("tool.audit")
        T = h.text()
        if "The line under the cursor" not in T:
            dump(h)
            bail("tool.audit never drew its page, so no row below can be believed")
        row("a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words = ("blocks", "filters", "follows", "HOLD")         # single words: the box wraps its text
        row("a click on the [?] shows the record of tool.audit.page: its title and words of its three paragraphs", "The audit trail" in T and all(w in T for w in words) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "The audit trail" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # ----------------------------------------------------------------------------------------------- tool.config (25 Oct 26, S.75 A6): only its help is the docs suite's; the page is sandbox-tool-config.py's
        say("\n--- tool.config: the configuration page's help")
        h = open_page("tool.config")
        T = h.text()
        if "The parameter under the cursor" not in T:
            dump(h)
            bail("tool.config never drew its page, so no row below can be believed")
        row("a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words = ("parameter", "disagree", "restart", "backup")         # single words: the box wraps its text
        row("a click on the [?] shows the record of tool.config.page: its title and words of its three paragraphs", "The configuration" in T and all(w in T for w in words) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "The configuration" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # ----------------------------------------------------------------------------------------------- tool.backups (25 Oct 26, S.75 A8): only its help is the docs suite's; the page is sandbox-tool-backups.py's
        say("\n--- tool.backups: the backups page's help")
        h = open_page("tool.backups")
        T = h.text()
        if "The archive under the cursor" not in T:
            dump(h)
            bail("tool.backups never drew its page, so no row below can be believed")
        row("a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words = ("archives", "manifest", "RESTORE", "root")         # single words: the box wraps its text
        row("a click on the [?] shows the record of tool.backups.page: its title and words of its three paragraphs", "Backups and restores" in T and all(w in T for w in words) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "Backups and restores" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # ----------------------------------------------------------------------------------------------- tool.accounts (25 Oct 26, S.75 A3): only its help is the docs suite's; the page is sandbox-tool-accounts.py's
        say("\n--- tool.accounts: the accounts page's help")
        h = open_page("tool.accounts")
        T = h.text()
        if "The account under the cursor" not in T:
            dump(h)
            bail("tool.accounts never drew its page, so no row below can be believed")
        row("a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words = ("suspends", "gates", "password", "Cancel")         # single words: the box wraps its text
        row("a click on the [?] shows the record of tool.accounts.page: its title and words of its three paragraphs", "The accounts" in T and all(w in T for w in words) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "The accounts" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # ----------------------------------------------------------------------------------------------- tool.remote (25 Oct 26, S.75 A9): only its help is the docs suite's; the page is sandbox-tool-remote.py's
        say("\n--- tool.remote: the remote access page's help")
        h = open_page("tool.remote")
        T = h.text()
        if "About this view" not in T:
            dump(h)
            bail("tool.remote never drew its page, so no row below can be believed")
        row("a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words = ("doors", "OPEN", "servers", "Cancel")         # single words: the box wraps its text
        row("a click on the [?] shows the record of tool.remote.page: its title and words of its three paragraphs", "Remote access" in T and all(w in T for w in words) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", "Remote access" in T and all(w in T for w in words), T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()
        # the same verb in an ORDINARY account is the holder's read-only page (sandbox-tool-mygates.py's); its help is this suite's
        h = H("zzhd")
        h.typed("tool.gates\r", idle=3.5)
        T = h.text()
        if "What this account may do" not in T:
            dump(h)
            bail("tool.gates never drew the holder's page in an ordinary account, so no row below can be believed")
        row("in an ordinary account tool.gates is the holder's page (not the matrix), with a [?] at the end of its first box", "Gates by account" not in T and h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
        h.click(135, 2, idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        words2 = ("What this account may do", "nothing", "gate", "sign", "administrator")
        row("a click on the [?] shows the record of tool.gates.mine: its title and words of its two paragraphs", all(w in T for w in words2) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("f1", idle=1.4)
        T = re.sub(r"[|\s]+", " ", h.text())
        row("F1 shows the same record", all(w in T for w in words2) and "Help is not installed" not in T, T[-700:])
        h.key("esc", idle=0.8)
        h.key("ctrl-q", idle=1.5)
        h.end()

        # -------------------------------------------------------------------------------------- menu, and the tiles
        say("\n--- menu and the home screen's tiles")
        h = H("zzhd")
        row("(control) the account starts at the prompt in this sandbox", h.prompt() and not h.home(), h.text()[-200:])
        h.typed("menu\r", idle=2.5)
        row("MENU at the prompt opens the full-screen menu: the home screen, with its Terminal and Sign out tiles", h.home(), h.text()[-300:])
        h.key("ctrl-q", idle=1.0)
        h.key("enter", idle=0.5)
        h.end()
        h = H(admin=True)
        h.typed("menu\r", idle=2.5)
        T = h.text()
        row("MENU in the administrator's session opens the administrator's page, whose System group has Menu management and Audit trail (Bypass programs is gone, S.187)",
            "Menu management" in T and "Audit trail" in T and "Bypass programs" not in T and "administrator" in T, T[:600])   # stale-ok: checks the tile is gone
        h.end()
        h = H("zzhd")
        h.typed("home\r", idle=2.5)
        T = h.text()
        row("an account holder's page has neither of those tiles", h.home() and "Audit trail" not in T and "Menu management" not in T, T[:400])
        h.end()
    finally:
        sh.teardown()
    sh.summary("sandbox-docs")


if __name__ == "__main__":
    main()
