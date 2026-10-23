#!/usr/bin/env python3
"""test-pdf-units.py - the pdf verb and the programs allowed to bypass OS.EXECUTE (S.75, plan .claude/plan-fullscreen-toolkit.md section 14.6 and 14.7), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pdf-units.py
  python3 .../test-pdf-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  PDF starts a program outside SD for an account whose OS.EXECUTE switch is off, so it is held to be narrow: the document name is tested before a path is built, the file
is a lower case regular file of the shared account's pdf directory, the program is the first on the administrator's list that passes the test AGAIN now, the display is asked
before anything is started, the command line is built from those two checked parts and nothing else, and one audit line is written.  !VIEWLIST's test is held to every condition the
plan names (an absolute path of plain characters, not under a place users can write, a regular file owned by root with no setuid or sticky bit, not writable by group or others,
executable by everyone) and its list is made mode 0644.  SET.VIEWER and DOCS.INSTALL ask for the administrator first and only SDSYS's VOC has them, LOAD.HELP and the Bypass programs
page. The installer's question defaults to No and allows nothing itself; its content block makes the pdf directory mode 755 so that no SD user can add a document.

***IT READS THE SOURCE AS TEXT AND DOES NOT RUN BASIC OR THE INSTALLER.***  That PDF starts a program, refuses what it should and writes its audit line is sandbox-pdf.py; the installer
blocks run under their own shell options in test-install-docs.sh.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
INSTALLER = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir, "installsdcore.sh"))
PROGS = ("pdf", "viewlist", "setviewer", "docsinst", "tool_viewers")
MSGS = tuple(str(n) for n in list(range(11720, 11725)) + list(range(11843, 11850)) + [11887, 11888] + list(range(11890, 11900)))       # 11889 is free
VOC_BOTH = ("pdf",)
VOC_SDSYS_ONLY = ("set.viewer", "tool.viewers", "docs.install", "load.help")


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else text[i:]


def arg_counts(text, name):
    """The number of arguments of each `call <name>(...)` in TEXT: top-level commas + 1, quotes and brackets respected.  A call with the wrong number stops with 'Argument count mismatch'
    at run time, and no other free check sees it."""
    out = []
    for m in re.finditer(r"call\s+" + re.escape(name) + r"\(", text):
        i, depth, n, q = m.end(), 1, 1, ""
        while i < len(text) and depth:
            c = text[i]
            if q:
                q = "" if c == q else q
            elif c in "'\"":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "," and depth == 1:
                n += 1
            i += 1
        out.append(n)
    return out


def load():
    src = {n: read(os.path.join(GPL, n)) for n in PROGS}
    src["installer"] = read(INSTALLER)
    src["msgs"] = {n: (read(os.path.join(SDSYS, "messages", n)) if os.path.exists(os.path.join(SDSYS, "messages", n)) else None) for n in MSGS}
    src["voc"] = {("newvoc/" + n): os.path.exists(os.path.join(SDSYS, "newvoc", n)) for n in VOC_BOTH + VOC_SDSYS_ONLY}
    src["voc"].update({("voc_template/" + n): os.path.exists(os.path.join(SDSYS, "voc_template", n)) for n in VOC_BOTH + VOC_SDSYS_ONLY})
    return src


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    pd, vl, sv, di, tv = (strip(s[n]) for n in PROGS)
    ins = s["installer"]

    ck("D0 the sources were found (the null case: nothing to compare passes every row)", len(pd) > 2000 and len(vl) > 2500 and len(sv) > 2000 and len(di) > 2000 and len(tv) > 6000 and len(ins) > 50000,
       repr((len(pd), len(vl), len(sv), len(di), len(tv), len(ins))))

    # PDF
    ck("D1 PDF is $internal and does NOT ask the account's OS switches (it is the bypass; the administrator's list is the control), and runs exactly two commands: stat of the document and the viewer",
       "$internal\nprogram pdf" in pd and "K$OS.EXEC" not in pd and "K$PATH.OK" not in pd and pd.count("os.execute") == 2, repr(pd.count("os.execute")))
    i_chars = pd.find("if trim(convert('abcdefghijklmnopqrstuvwxyz0123456789._-', space(39), name)) # '' then ok = 0")
    i_file = pd.find("docfile = pdfdir : @ds : name : '.pdf'")
    i_stat = pd.find("os.execute \"find '\" : pdfdir : \"' -maxdepth 1 -type f -name '*.pdf' -print\" capturing found")
    i_view = pd.find("call !viewlist('get', 'pdf', paths, 0)")
    i_disp = pd.find("if env('DISPLAY') = '' and env('WAYLAND_DISPLAY') = '' then stop sysmsg(11847)")
    i_run = pd.find("os.execute \"nohup '\"")
    i_aud = pd.find("void kernel(K$AUDIT, 'pdf open file=' : name : ' viewer=' : viewer)")
    ck("D2 the order: the documents are the regular files found in the pdf directory, THEN the characters of the name, then the path of the document, then the viewer, then the display, then the program is started, then the audit line",
       0 < i_stat < i_chars < i_file < i_view < i_disp < i_run < i_aud, repr((i_stat, i_chars, i_file, i_view, i_disp, i_run, i_aud)))
    ck("D3 the name: 1 to 80 characters, not starting with a dot, a-z 0-9 . _ - only; a trailing .pdf is taken off; it must be one of the documents the directory lists",
       "ok = (len(name) >= 1 and len(name) <= 80 and name[1, 1] # '.')" in pd and "if name[len(name) - 3, 4] = '.pdf' then name = name[1, len(name) - 4]" in pd and "locate name in docs<1> setting dp else stop sysmsg(11845, name)" in pd)
    ck("D4 the documents: REGULAR files (find -type f, so a link or a directory is not one) with a lower case name ending .pdf, in the pdf directory of the shared account; the path of that account is tested for plain characters",
       "nm = downcase(nm) and nm[len(nm) - 3, 4] = '.pdf' and nm[1, 1] # '.'" in pd and "pdfdir = spath : @ds : 'pdf'" in pd and "-maxdepth 1 -type f" in pd
       and "space(66), spath)) # '' then" in pd)
    ck("D5 the viewer is the first on the list that passes the test now; none on the list is 11846, one that fails is 11849",
       "call !viewlist('check', paths<i>, why, 0)" in pd and "if why = '' then viewer = paths<i>" in pd and "if paths = '' then stop sysmsg(11846)" in pd and "stop sysmsg(11849, paths<1>, why)" in pd)
    ck("D6 the command line is built from the viewer and the document only, quoted, in the background, with no input and no output of SD's",
       "os.execute \"nohup '\" : viewer : \"' '\" : docfile : \"' </dev/null >/dev/null 2>&1 &\" capturing out" in pd)
    ck("D7 the list shows the documents sorted, and says how many (11887)", "by 'AL'" in pd and "sysmsg(11887, dcount(listed, @fm))" in pd)

    # !VIEWLIST
    ck("D8 !viewlist 'check' makes every test the plan names: an absolute path, plain characters, no .., not under /tmp /var/tmp /dev /home /run /proc /sys /mnt /media, the file exists, is owned by root, is a regular file, has no setuid / setgid / sticky bit, is not writable by group or others, is executable by everyone",
       all(w in vl for w in ("p[1, 1] # '/' or len(p) < 2 or len(p) > 200", "index(p, '..', 1) > 0", "stat -L -c '%u %a %F'", "if own # '0' then", "kind[1, 7] # 'regular'", "mode[1, lm - 3] + 0 # 0",
                             "bitand(gb, 2) or bitand(ob, 2)", "not(bitand(ob, 1))"))
       and all(r in vl for r in ("'/tmp/'", "'/var/tmp/'", "'/dev/'", "'/home/'", "'/run/'", "'/proc/'", "'/sys/'", "'/mnt/'", "'/media/'")))
    ck("D9 ...the list is empty as delivered (an absent file reads as nothing: OPENSEQ READONLY), 'put' keeps the other purposes' lines, and the file is made mode 0644 after it is written",
       "openseq lfile readonly to lf then" in vl and "if pur<i> # a then" in vl and "chmod 0644 '" in vl and "openseq lfile overwrite to lf else null" in vl)

    # SET.VIEWER
    i_adm = sv.find("kernel(K$ADMINISTRATOR, -1)")
    i_words = sv.find("words = trim(@sentence)")
    ck("D10 SET.VIEWER asks for the administrator before it reads its words; only the purpose pdf; a program is added only after !viewlist's test, removed without one; the audit line names the program",
       0 < i_adm < i_words and "if purpose # 'pdf' then stop sysmsg(11897" in sv and "call !viewlist('check', path, why, 0)" in sv and sv.find("call !viewlist('check', path, why, 0)") < sv.find("paths<-1> = path")
       and "void kernel(K$AUDIT, 'set.viewer ' : action : ' purpose=' : purpose : ' program=' : path)" in sv and "del paths<p>" in sv)
    ck("D11 ...a bare name is looked for by !viewlist 'find' (/usr/bin, /usr/local/bin, /bin), nothing is added when it is not found (11899), and a program already there is not added twice (11893)",
       "call !viewlist('find', arg, path, 0)" in sv and "if path = '' then stop sysmsg(11899" in sv and "stop sysmsg(11893, path, purpose)" in sv)

    # DOCS.INSTALL
    j_adm = di.find("kernel(K$ADMINISTRATOR, -1)")
    j_words = di.find("words = trim(@sentence)")
    ck("D12 DOCS.INSTALL asks for the administrator first; the directory is a plain absolute path; the destination is the pdf directory of the shared account and is never made here; no sub-directory is read",
       0 < j_adm < j_words and "src[1, 1] # @ds or len(src) > 200 or trim(convert(okc, space(len(okc)), src)) # '' or index(src, '..', 1) > 0" in di and "dest = spath : @ds : 'pdf'" in di
       and "mkdir" not in di and "if entries<i, 2> # 'F' then continue" in di)
    ck("D13 ...a file is copied only if its name is lower case letters, digits and . _ - ending in .pdf and not starting with a dot, and the file starts with %PDF- ; cp is given quoted checked parts after --, the copy is mode 0644, and what is not there afterwards counts as skipped",
       "nm = downcase(nm)" in di and "if magic[1, 5] # '%PDF-' then" in di and di.find("if magic[1, 5] # '%PDF-' then") < di.find("os.execute \"cp -f -- '\"") and "chmod 0644 '" in di and "not(ospath(dest : @ds : nm, OS$EXISTS))" in di)

    # the Bypass programs page
    ck("D14 tool.viewers runs only set.viewer, shows the command and its effect before it runs (Run / Cancel), asks for the program's name to be typed before ALLOWING one, and offers a reader only from the fixed list of names",
       "allow = 'set.viewer'" in tv and 0 < tv.find("call $tk_confirm(sent, el, typed, res, cmsg)") < tv.find("call $tk_run(allow, sent, out, st, err)") and "typed = pname" in tv and tv.count("call $tk_run(") == 1
       and "cnames = 'evince'" in tv and "call !viewlist('find', cnames<i>, pth, 0)" in tv and "if not(on.now) and pwhy # '' then" in tv)

    # the entries
    v = s["voc"]
    ck("D15 the VOC: PDF for every account (newvoc) and SDSYS (voc_template); SET.VIEWER, TOOL.VIEWERS, DOCS.INSTALL and LOAD.HELP for SDSYS ONLY",
       v["newvoc/pdf"] and v["voc_template/pdf"] and all(v["voc_template/" + n] and not v["newvoc/" + n] for n in VOC_SDSYS_ONLY), repr(v))
    m = s["msgs"]
    ck("D16 messages 11720 to 11724, 11843 to 11849, 11887, 11888 and 11890 to 11899 exist, each one line", all(m[n] and m[n].count("\n") == 1 for n in MSGS), repr([n for n in MSGS if not m[n] or m[n].count("\n") != 1]))

    counts = arg_counts(pd + "\n" + sv + "\n" + tv, "!viewlist")
    ck("D19 every call of !viewlist has its four arguments (the subroutine takes four; a call with fewer stops with 'Argument count mismatch'), and there are calls to count (the null case)",
       len(counts) >= 8 and all(n == 4 for n in counts), repr(counts))

    # the installer
    ask = between(ins, "# VIEWER-ASK-BEGIN", "# VIEWER-ASK-END")
    cont = between(ins, "# SHARED-CONTENT-BEGIN", "# SHARED-CONTENT-END")
    ck("D17 the installer asks about a reader up front: No unless y or yes, only when a known reader is installed and the list has no pdf line yet, and allows nothing itself",
       "allow_viewer=n" in ask and "if ! grep -qs '^pdf ' \"${sdsysdir}/viewers\"; then" in ask and "case $yn_viewer in [yY]|[yY][eE][sS] ) allow_viewer=y;; esac" in ask and "set.viewer" not in ask
       and ins.find("# GATES-ASK-END") < ins.find("# VIEWER-ASK-BEGIN") < ins.find("printf \"%b\\n\" \"$NC\"", ins.find("# VIEWER-ASK-END")), repr(len(ask)))
    ck("D18 ...and then, in the content block (after the shared account is made): the pdf directory is owner sdsys, group sdusers, mode 755; load.help runs with input from /dev/null and cannot stop the install; set.viewer runs only after a y; the result is judged on the list",
       ins.find("# SHARED-CREATE-END") < ins.find("# SHARED-CONTENT-BEGIN") < ins.find("# 11 Sep 26  AN UPGRADE BRINGS EVERY ACCOUNT'S VOC FORWARD")
       and 'sudo mkdir -p "${shared_dir}/pdf"' in cont and 'sudo chown sdsys:sdusers "${shared_dir}/pdf"' in cont and 'sudo chmod 755 "${shared_dir}/pdf"' in cont
       and "sudo bin/sd -internal load.help < /dev/null || true" in cont and 'if [ "$allow_viewer" = y ] && [ -n "$allow_viewer_name" ]; then' in cont
       and 'sudo bin/sd -internal set.viewer add pdf "$allow_viewer_name" < /dev/null || true' in cont and "if sudo grep -qs '^pdf ' \"${sdsysdir}/viewers\"; then" in cont)
    return rows


MUTANTS = [
    ("PDF checks the account's OS switch", "pdf", "   @system.return.code = -ER$ARGS\n\n   words = trim(@sentence)", "   @system.return.code = -ER$ARGS\n   if not(kernel(K$OS.EXEC, -1)) then stop\n\n   words = trim(@sentence)"),
    ("PDF takes a name with any character", "pdf", "      if trim(convert('abcdefghijklmnopqrstuvwxyz0123456789._-', space(39), name)) # '' then ok = 0\n", ""),
    ("PDF allows a name that begins with a dot", "pdf", "ok = (len(name) >= 1 and len(name) <= 80 and name[1, 1] # '.')", "ok = (len(name) >= 1 and len(name) <= 80)"),
    ("PDF lists links and directories", "pdf", " -maxdepth 1 -type f ", " -maxdepth 1 "),
    ("PDF lists upper case file names", "pdf", "      if nm = downcase(nm) and nm[len(nm) - 3, 4] = '.pdf'", "      if nm[len(nm) - 3, 4] = '.pdf'"),
    ("PDF lists sub-directories", "pdf", " -maxdepth 1 -type f ", " -type f "),
    ("SET.VIEWER calls !viewlist with three arguments", "setviewer", "call !viewlist('put', purpose, paths, wrote)", "call !viewlist('put', purpose, paths)"),
    ("PDF asks for no list", "pdf", "   call !viewlist('get', 'pdf', paths, 0)\n   viewer = ''", "   paths = '/usr/bin/xdg-open'\n   viewer = ''"),
    ("PDF does not test the program again", "pdf", "         call !viewlist('check', paths<i>, why, 0)\n         if why = '' then viewer = paths<i>", "         viewer = paths<i>"),
    ("PDF starts a program with no viewer on the list", "pdf", "      if paths = '' then stop sysmsg(11846)                       ;* No viewer has been allowed\n", ""),
    ("PDF does not ask for a display", "pdf", "   if env('DISPLAY') = '' and env('WAYLAND_DISPLAY') = '' then stop sysmsg(11847)\n", ""),
    ("PDF starts the program in the foreground", "pdf", "</dev/null >/dev/null 2>&1 &\"", "\""),
    ("PDF writes no audit line", "pdf", "   void kernel(K$AUDIT, 'pdf open file=' : name : ' viewer=' : viewer)\n", ""),
    ("PDF runs a third command", "pdf", "   @system.return.code = 0\n   void kernel(K$AUDIT, 'pdf open", "   os.execute 'id' capturing idout\n   @system.return.code = 0\n   void kernel(K$AUDIT, 'pdf open"),
    ("PDF does not test the shared path", "pdf", "space(66), spath)) # '' then", "space(66), spath)) # 'x' then"),
    ("viewlist accepts a relative path", "viewlist", "p[1, 1] # '/' or len(p) < 2 or len(p) > 200", "len(p) < 2 or len(p) > 200"),
    ("viewlist accepts .. in a path", "viewlist", "      case index(p, '..', 1) > 0\n", "      case @false\n"),
    ("viewlist accepts a program under /home", "viewlist", " : @fm : '/home/' : @fm : ", " : @fm : "),
    ("viewlist accepts a program owned by someone else", "viewlist", "   if own # '0' then", "   if @false then"),
    ("viewlist accepts a link or a directory", "viewlist", "      if kind[1, 7] # 'regular' then", "      if @false then"),
    ("viewlist accepts a setuid program", "viewlist", "         if lm > 3 and mode[1, lm - 3] + 0 # 0 then", "         if @false then"),
    ("viewlist accepts a program group can write", "viewlist", "               case bitand(gb, 2) or bitand(ob, 2)", "               case bitand(ob, 2)"),
    ("viewlist accepts a program others cannot run", "viewlist", "               case not(bitand(ob, 1))", "               case @false"),
    ("viewlist's list is left writable", "viewlist", "   if c then os.execute \"chmod 0644 '\" : lfile : \"'\" capturing mo\n", ""),
    ("viewlist's put drops the other purposes", "viewlist", "            if pur<i> # a then", "            if @true then"),
    ("viewlist's list is created when it is only read", "viewlist", "openseq lfile readonly to lf then", "openseq lfile to lf then"),
    ("SET.VIEWER does not ask for the administrator", "setviewer", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("SET.VIEWER adds without the test", "setviewer", "      call !viewlist('check', path, why, 0)\n      if why # '' then stop sysmsg(11849, path, why)             ;* The viewer %1 cannot be used: %2\n", ""),
    ("SET.VIEWER takes another purpose", "setviewer", "   if purpose # 'pdf' then stop sysmsg(11897, purpose[1, 40])", "   if @false then stop sysmsg(11897, purpose[1, 40])"),
    ("SET.VIEWER writes no audit line", "setviewer", "   void kernel(K$AUDIT, 'set.viewer ' : action : ' purpose=' : purpose : ' program=' : path)\n", ""),
    ("DOCS.INSTALL does not ask for the administrator", "docsinst", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("DOCS.INSTALL copies a file that is not a PDF", "docsinst", "   if magic[1, 5] # '%PDF-' then", "   if @false then"),
    ("DOCS.INSTALL copies a name with a capital", "docsinst", " and nm = downcase(nm))", ")"),
    ("DOCS.INSTALL makes the directory", "docsinst", "   dest = spath : @ds : 'pdf'\n", "   dest = spath : @ds : 'pdf'\n   os.execute \"mkdir -p '\" : dest : \"'\" capturing mo\n"),
    ("DOCS.INSTALL reads a path with .. in it", "docsinst", " or index(src, '..', 1) > 0", ""),
    ("the Bypass programs page runs another command", "tool_viewers", "allow = 'set.viewer'", "allow = 'set.viewer sh'"),
    ("the Bypass programs page does not ask for the name before allowing", "tool_viewers", "      typed = pname\n", ""),
    ("the Bypass programs page runs without the confirm box", "tool_viewers", "   call $tk_confirm(sent, el, typed, res, cmsg)\n   if res = 'run' then", "   res = 'run'\n   if res = 'run' then"),
    ("the Bypass programs page offers a reader not on the list of names", "tool_viewers", "call !viewlist('find', cnames<i>, pth, 0)", "call !viewlist('find', cnames<i> : 'x', pth, 0)"),
    ("the installer asks even when a reader is already allowed", "installer", "if ! grep -qs '^pdf ' \"${sdsysdir}/viewers\"; then", "if true; then"),
    ("the installer's answer defaults to yes", "installer", "allow_viewer=n\nallow_viewer_name=\"\"", "allow_viewer=y\nallow_viewer_name=\"\""),
    ("the installer allows a reader with no question", "installer", "# VIEWER-ASK-END", "set.viewer\n# VIEWER-ASK-END"),
    ("the installer's pdf directory is writable by the group", "installer", 'sudo chmod 755 "${shared_dir}/pdf"', 'sudo chmod 775 "${shared_dir}/pdf"'),
    ("the installer allows the reader without a y", "installer", 'if [ "$allow_viewer" = y ] && [ -n "$allow_viewer_name" ]; then', 'if [ -n "$allow_viewer_name" ]; then'),
    ("load.help can stop the install", "installer", "sudo bin/sd -internal load.help < /dev/null || true", "sudo bin/sd -internal load.help < /dev/null"),
]


def selftest():
    s = load()
    base = [n for n, ok, _ in checks(s) if not ok]
    if base:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base), file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: the unmutated source passes; each mutation must be CAUGHT and match its text once ---")
    for name, which, old, new in MUTANTS:
        if s[which].count(old) != 1:
            print("  [FAIL] %s: the text to mutate matches %d times in %s, not once" % (name, s[which].count(old), which))
            holes += 1
            continue
        s2 = dict(s)
        s2[which] = s[which].replace(old, new)
        caught = [n for n, ok, _ in checks(s2) if not ok]
        if caught:
            print("  [pass] %s: caught by %s" % (name, ", ".join(caught[:3])))
        else:
            print("  [FAIL] %s: NOT CAUGHT by any check" % name)
            holes += 1
    print("self-test: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    s = load()
    rows = checks(s)
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-pdf-units: %d checks, %d failed" % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
