#!/usr/bin/env python3
"""test-examples-units.py - the example programs (examples.bp in every account, 17 Nov 2026) as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-examples-units.py [--selftest]

The owner, 17 Nov 2026: "there should be a examples.bp file available to all users that contains those programs and a set of training programs typical
for a Computer Science 101 course"; asked how every account reaches it, "A copy in every account".  What it holds:
  X1  THE GUIDE AND THE FILES ARE ONE TEXT: each of the five TUI programs (hello, menus, notes, browse, stock) is byte for byte the first code block of its
      chapter of the SD Text User Interface - Programmer's Guide in the docs checkout /home/don/Projects/SDCore4LinuxDocs (exit 2 when it is missing)
  X2  every shipped file has a name LOAD.EXAMPLES takes, begins "* <name> -", and each training program (cs..) is "program <name>" ... "end"
  X3  no shipped program writes a doubled quote inside a string (SD BASIC has no '' escape: test-sqescape-units.py's rule, for gpl.bp)
  X4  LOAD.EXAMPLES asks for the administrator before it reads anything, skips a SUSPENDED account, makes examples.bp a DIRECTORY file, judges each
      compile on the compiler's own success line, goes back to the account it began in, and writes one audit line
  X5  create.account runs load.examples for the account it made, after its audit line
  X6  the installer's EXAMPLES block is there once, after SHARED-CONTENT and before SOURCE-GONE, runs load.examples internally and warns on failure
  X7  load.examples is the administrator's verb: in voc_template, not in newvoc; the messages it cites exist
  X8, X9  LOAD.EXAMPLES and REMOVE.EXAMPLES take a LIST of accounts (owner, 17 Nov 2026), an unregistered name said and skipped
  X10, X11  REMOVE.EXAMPLES, the companion: only the shipped names deleted with their objects, the file only when nothing is left, back to the account it
      began in, one audit line; its VOC record in voc_template only and its messages exist
It cannot say a program runs or what it prints: that is sandbox-examples.py.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sqescape_for_examples", os.path.join(HERE, "test-sqescape-units.py"))
SQ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SQ)                         # its rule (doubled, COMMENT_LINE) is the one gpl.bp is held to; main() is not run
SD64 = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(SD64, "..", ".."))
SDSYS = os.path.join(SD64, "sdsys")
EX = os.path.join(SDSYS, "examples")
GUIDE = "/home/don/Projects/SDCore4LinuxDocs/TUIGuide/markdown"
PAGES = [("hello", "02-a-bare-page"), ("menus", "03-menus-and-the-finder"), ("notes", "04-a-form-and-a-confirm-box"),
         ("browse", "05-panes-and-pickers"), ("stock", "05b-a-form-in-the-body")]


def rd(p):
    try:
        with open(p, encoding="latin-1") as f:
            return f.read()
    except OSError:
        return None


def load():
    raw = {"load": rd(os.path.join(SDSYS, "gpl.bp", "loadexamples")), "createa": rd(os.path.join(SDSYS, "gpl.bp", "createa")),
           "inst": rd(os.path.join(ROOT, "installsdcore.sh")), "vt": rd(os.path.join(SDSYS, "voc_template", "load.examples")),
           "nv": rd(os.path.join(SDSYS, "newvoc", "load.examples")),
           "rm": rd(os.path.join(SDSYS, "gpl.bp", "removeexamples")), "vtr": rd(os.path.join(SDSYS, "voc_template", "remove.examples")),
           "nvr": rd(os.path.join(SDSYS, "newvoc", "remove.examples"))}
    raw["files"] = {n: rd(os.path.join(EX, n)) for n in sorted(os.listdir(EX))} if os.path.isdir(EX) else {}
    raw["guide"] = {n: rd(os.path.join(GUIDE, p + ".md")) for n, p in PAGES}
    return raw


def code(src):
    return "\n".join(re.sub(r"\s*;\*.*$", "", l) for l in (src or "").split("\n") if not re.match(r"^\s*\*", l))


def first_block(md, name):
    blocks, cur, inside = [], [], False
    for ln in (md or "").split("\n"):
        if ln.startswith("```"):
            if inside:
                blocks.append(cur)
                cur = []
            inside = not inside
            continue
        if inside:
            cur.append(ln)
    b = next((b for b in blocks if b and b[0].startswith("* %s -" % name)), None)
    return None if b is None else "\n".join(b) + "\n"


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    files = raw["files"]
    bad = [n for n, _ in PAGES if files.get(n) is None or first_block(raw["guide"][n], n) != files.get(n)]
    ck("X1", "each of the five TUI programs is byte for byte its chapter's first code block in the guide", not bad, repr(bad))
    badname = [n for n in files if not re.match(r"^[a-z][a-z0-9._-]{0,79}$", n)]
    badhead = [n for n, t in files.items() if not (t or "").startswith("* %s -" % n)]
    badcs = [n for n, t in files.items() if n.startswith("cs") and not (re.search(r"^program %s\s*$" % re.escape(n), t or "", re.M) and (t or "").rstrip().endswith("end"))]
    ck("X2", "%d shipped files: every name is a key, every file begins '* <name> -', every training program is program <name> ... end" % len(files),
       len(files) >= 25 and not badname and not badhead and not badcs and len([n for n in files if n.startswith("cs")]) >= 20, repr((badname, badhead, badcs)))
    dq = [n for n, t in files.items() for l in (t or "").split("\n") if not SQ.COMMENT_LINE.match(l) and SQ.doubled(l)]     # test-sqescape-units.py's own reading
    ck("X3", "no shipped program writes a doubled quote inside a string ('it''s' is two strings in SD BASIC)", not dq, repr(dq))
    ld = code(raw["load"])
    ck("X4", "LOAD.EXAMPLES: the administrator first, a SUSPENDED account skipped, examples.bp a DIRECTORY file, the compile judged on its success line, back to "
             "the account it began in, one audit line",
       raw["load"] is not None and 0 <= ld.find("if not(kernel(K$ADMINISTRATOR, -1)) then") < ld.find("dir(src)")
       and "if upcase(trim(arec<ACC$SUSPENDED>)) = 'SUSPENDED' then continue" in ld and "execute 'create.file examples.bp directory' trapping aborts" in ld
       and "if index(out, 'Compiled 1 program(s) with no errors', 1) then" in ld and "execute 'logto ' : origin trapping aborts capturing lt" in ld and ld.count("kernel(K$AUDIT") == 1
       # 18 Nov 26: every EXECUTE traps aborts - a create.file the session may not make aborts (8207), and an untrapped abort left the
       # administrator in the account (the owner found it through create.account)
       and len(re.findall(r"\bexecute\b", ld)) == len(re.findall(r"\bexecute\b[^\n]*\btrapping aborts\b", ld)))
    ca = code(raw["createa"])
    i_aud = ca.find("void kernel(K$AUDIT, 'create.account account='")
    i_ld = ca.find("execute 'load.examples ' : downcase(acc.name) trapping aborts\n")
    ck("X5", "create.account runs load.examples for the account it made, after its audit line, trapping aborts and NOT capturing (S.270: capturing "
             "around a trapped abort crashed the process), goes back to the account it began in, and says 14185 when its return code is not 0", 0 < i_aud < i_ld
       and 0 < i_ld < ca.find("if downcase(@who) # ex.origin then execute 'logto ' : ex.origin trapping aborts") and "if ex.code # 0 then crt sysmsg(14185" in ca
       and not re.search(r"execute 'load\.examples[^\n]*capturing", ca))
    inst = raw["inst"] or ""
    b = inst.find("# EXAMPLES-BEGIN")
    blk = inst[b:inst.find("# EXAMPLES-END")] if b >= 0 else ""
    ck("X6", "the installer's EXAMPLES block: once, after SHARED-CONTENT and before SOURCE-GONE, load.examples run internally, a WARNING when it says no account",
       inst.count("# EXAMPLES-BEGIN") == 1 and inst.find("# SHARED-CONTENT-END") < b < inst.find("# SOURCE-GONE-BEGIN") and "sudo bin/sd -internal load.examples < /dev/null" in blk
       and "WARNING: the example programs were not put into the accounts." in blk and "exit" not in blk)
    cited = set(re.findall(r"sysmsg\((\d+)", ld))
    gone = sorted(n for n in cited if not os.path.exists(os.path.join(SDSYS, "messages", n)))
    ck("X7", "load.examples is in voc_template (V CA $loadexamples) and not in newvoc; the %d messages it cites exist" % len(cited),
       (raw["vt"] or "").split("\n")[:3] == ["V", "CA", "$loadexamples"] and raw["nv"] is None and cited and not gone, repr(gone))
    # THE LIST (owner, 17 Nov 2026: "both load.examples and remove.examples should take a list of accounts") and the companion verb
    rm = code(raw["rm"])
    for who, t in (("LOAD.EXAMPLES", ld), ("REMOVE.EXAMPLES", rm)):
        ck("X8" if who[0] == "L" else "X9", "%s takes a LIST of accounts: each word after the verb, each once, an unregistered name said and skipped, the others go on" % who,
           t and "for w = 2 to dcount(want, ' ')" in t and t.count("locate aid in accts<1> by 'AL' setting ap else ins aid before accts<ap>") == 2     # the list and the register
           and "stop sysmsg(14122, want)" not in t and "n.bad += 1\n            continue" in t)
    ck("X10", "REMOVE.EXAMPLES: the administrator first, only the SHIPPED names deleted (each read first), the compiled object with its program, examples.bp and its .out "
              "deleted only when nothing is left (left = 0) and judged on a reopen, back to the account it began in, one audit line, a SUSPENDED account skipped",
       raw["rm"] is not None and 0 <= rm.find("if not(kernel(K$ADMINISTRATOR, -1)) then") < rm.find("dir(src)")
       and "read old from xf, names<p> then" in rm and "delete xf, names<p> on error dok = @false" in rm and "delete of, names<p> on error dok = @false" in rm
       and 0 < rm.find("if left = 0 then") < rm.find("execute 'delete.file examples.bp' trapping aborts capturing out") < rm.find("execute 'delete.file examples.bp.out' trapping aborts capturing out")
       and "select xf to 12" in rm and rm.count("delete.file") == 2 and "execute 'logto ' : origin trapping aborts capturing lt" in rm and rm.count("kernel(K$AUDIT") == 1
       and len(re.findall(r"\bexecute\b", rm)) == len(re.findall(r"\bexecute\b[^\n]*\btrapping aborts\b", rm))
       and "if upcase(trim(arec<ACC$SUSPENDED>)) = 'SUSPENDED' then continue" in rm and "delete xf" in rm and "clear.file" not in rm and "select" in rm)
    cited_r = set(re.findall(r"sysmsg\((\d+)", rm))
    gone_r = sorted(n for n in cited_r if not os.path.exists(os.path.join(SDSYS, "messages", n)))
    ck("X11", "remove.examples is in voc_template (V CA $removeexamples) and not in newvoc; the %d messages it cites exist" % len(cited_r),
       (raw["vtr"] or "").split("\n")[:3] == ["V", "CA", "$removeexamples"] and raw["nvr"] is None and cited_r and not gone_r, repr(gone_r))
    return rows


def sub(key, old, new):
    def f(raw):
        if raw.get(key) is None or old not in raw[key]:
            return None
        r = dict(raw)
        r[key] = raw[key].replace(old, new, 1)
        return r
    return f


def subfile(name, old, new):
    def f(raw):
        t = raw["files"].get(name)
        if t is None or old not in t:
            return None
        r = dict(raw)
        r["files"] = dict(raw["files"])
        r["files"][name] = t.replace(old, new, 1)
        return r
    return f


MUTANTS = [
    ("a TUI program drifts from the guide", "X1", subfile("hello", "Ctrl-Q", "Ctrl-X")),
    ("a training program loses its program line", "X2", subfile("cs06.fizzbuzz", "program cs06.fizzbuzz", "program fizz")),
    ("a doubled quote in a string", "X3", subfile("cs09.subroutines", "\"the main program's i\"", "'the main program''s i'")),
    ("load.examples does not ask for the administrator", "X4", sub("load", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001)", "   if 0 then\n      stop sysmsg(2001)")),
    ("a suspended account is entered", "X4", sub("load", "if upcase(trim(arec<ACC$SUSPENDED>)) = 'SUSPENDED' then continue", "null")),
    ("the compile is not judged", "X4", sub("load", "if index(out, 'Compiled 1 program(s) with no errors', 1) then", "if 1 then")),
    ("create.account does not load the examples", "X5", sub("createa", "   execute 'load.examples ' : downcase(acc.name) trapping aborts\n", "   null\n")),
    ("create.account does not go back where it began", "X5", sub("createa", "   if downcase(@who) # ex.origin then execute 'logto ' : ex.origin trapping aborts\n", "")),
    ("create.account captures load.examples again (S.270 crash)", "X5", sub("createa", "   execute 'load.examples ' : downcase(acc.name) trapping aborts\n",
                                                                           "   execute 'load.examples ' : downcase(acc.name) trapping aborts capturing ex.out\n")),
    ("load.examples' create.file aborts out of the verb", "X4", sub("load", "execute 'create.file examples.bp directory' trapping aborts capturing mk", "execute 'create.file examples.bp directory' capturing mk")),
    ("the installer block does not warn", "X6", sub("inst", "    echo \"WARNING: the example programs were not put into the accounts.\"\n", "")),
    ("the installer block runs load.examples as root's session, not internally", "X6", sub("inst", "sudo bin/sd -internal load.examples < /dev/null", "sudo bin/sd load.examples < /dev/null")),
    ("load.examples is given to every account", "X7", lambda raw: dict(raw, nv="V\nCA\n$loadexamples\n")),
    ("load.examples takes one account again", "X8", sub("load", "for w = 2 to dcount(want, ' ')", "for w = 2 to 2")),
    ("load.examples stops at an unregistered name", "X8", sub("load", "            display sysmsg(14122, aid)                           ;* No account is registered as %1 ...\n            n.bad += 1\n            continue",
                                                              "            stop sysmsg(14122, want)")),
    ("remove.examples takes one account only", "X9", sub("rm", "for w = 2 to dcount(want, ' ')", "for w = 2 to 2")),
    ("remove.examples lists a name twice", "X9", sub("rm", "locate aid in accts<1> by 'AL' setting ap else ins aid before accts<ap>\n      next w",
                                                     "ins aid before accts<1>\n      next w")),
    ("remove.examples does not ask for the administrator", "X10", sub("rm", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001)", "   if 0 then\n      stop sysmsg(2001)")),
    ("remove.examples deletes a program the system does not ship (clears the file)", "X10", sub("rm", "   for p = 1 to dcount(names, @fm)\n      read old from xf, names<p> then",
                                                                                                "   execute 'clear.file examples.bp' capturing out\n   for p = 1 to dcount(names, @fm)\n      read old from xf, names<p> then")),
    ("remove.examples deletes the file although programs are left", "X10", sub("rm", "   if left = 0 then", "   if 1 then")),
    ("remove.examples keeps the compiled object", "X10", sub("rm", "delete of, names<p> on error dok = @false", "dok = @true")),
    ("remove.examples is not judged on a reopen", "X10", sub("rm", "      open 'examples.bp' to xf then\n         close xf\n         display sysmsg(14129, acct : ' examples.bp', 'the file could not be deleted')",
                                                             "      open 'examples.bp' to xf then\n         close xf\n         display sysmsg(14129, acct : ' examples.bp', 'the file could not be deleted')\n         execute 'delete.file examples.bp' capturing out")),
    ("remove.examples does not go back to the account it began in", "X10", sub("rm", "execute 'logto ' : origin trapping aborts capturing lt", "null")),
    ("remove.examples is given to every account", "X11", lambda raw: dict(raw, nvr="V\nCA\n$removeexamples\n")),
]


def main(argv):
    raw = load()
    if not all(raw["guide"].values()):
        print("test-examples-units: CANNOT RUN - the docs checkout %s is missing or incomplete" % GUIDE)
        return 2
    if not raw["files"]:
        print("test-examples-units: CANNOT RUN - no %s" % EX)
        return 2
    if "--selftest" in argv:
        if any(not ok for _, _, ok, _ in checks(raw)):
            print("REFUSING - the unmutated source already fails")
            return 1
        missed = 0
        for name, tag, f in MUTANTS:
            m = f(raw)
            failed = [i for i, _, ok, _ in checks(m)] if m is None else [i for i, _, ok, _ in checks(m) if not ok]
            if m is None or tag not in failed:
                print("  [MISSED] %s" % name)
                missed += 1
            else:
                print("  [pass] %s: caught by %s" % (name, tag))
        print("self-test: %d mutants, %d not caught" % (len(MUTANTS), missed))
        return 1 if missed else 0
    rows = checks(raw)
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok else "   <- " + str(detail)[:300]))
        bad += 0 if ok else 1
    print("test-examples-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
