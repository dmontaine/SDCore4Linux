#!/usr/bin/env python3
"""test-pdbgstore-units.py - W.11 F10b: the phantom debugger's conversation is kept in the user's private directory, not in $ipc; read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pdbgstore-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pdbgstore-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
31 Oct 26 dm  New with F10b (Opus's decision of 30 Oct: seal the debugger's conversation by moving it out of $ipc into <home>/.local/state/sd/pdebug).
END-HISTORY

WHAT IT HOLDS.  PDEBUG (the user's session), the DEBUG subroutine it calls and PDBG (in the phantom being debugged) leave each other messages - D.n, DR.n and the
START record DR.account!logname.  They used to be records of $ipc, a file every SD user's process can write, so a user with an operating-system shell could answer a
debugger that was not theirs.  They are now records of a directory file, <home>/.local/state/sd/pdebug, opened by !pdbg_store: the home is the password database's
for the user the process runs as (SDEXT SD_USER_HOME, never $HOME, never root), each directory from the home down is trusted only when it is a real directory of that
user's that nobody else can write (made under umask 077 when missing), and the store itself must be owner-only (SD_FILE_PRIVATE, mode 0700).  A PDEBUG and a phantom
reach each other only as the SAME operating-system user.  The store outlives an SD restart, which $ipc did not: PDEBUG clears the records of its own user number before
it starts, and PDBG removes and does not answer a START record whose PDEBUG has gone (kernel(K$USERS, n) is empty).

***IT READS THE SOURCE AS TEXT.***  That a conversation still works end to end is sandbox-oq2.py row 251; that a record forged in $ipc is not answered is the
sandbox-sysexc.py row of 31 Oct; that another operating-system user cannot reach the directory needs a second user: the VM.  --selftest requires each mutation to
match its text exactly once and to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.join(HERE, os.pardir, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
FILES = {n: os.path.join(GPL, n) for n in ("debug", "debug.h", "pdbg", "pdebug", "pdbg_store")}
MSG = 11948


def strip(src):
    """the code without comment lines and trailing ;* comments"""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def between(text, start, end):
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]


def checks(src, msgs, others):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    code = {k: strip(v) for k, v in src.items()}
    dbg, pdbg, pdebug, store, hdr = code["debug"], code["pdbg"], code["pdebug"], code["pdbg_store"], code["debug.h"]
    ck("P0 NULL CASE: the reader sees the five sources (debug over 50 KB, the others not empty)",
       len(dbg) > 50000 and len(pdbg) > 1500 and len(pdebug) > 1500 and len(store) > 800 and len(hdr) > 1000,
       repr([len(code[k]) for k in code]))

    named = [k for k in ("debug", "pdbg", "pdebug") if re.search(r"ipc\.f|\$ipc|\bipc_seal\b", code[k], re.I)]
    ck("P1a debug, pdbg and pdebug name neither the file $ipc nor ipc.f nor ipc_seal in code", not named, repr(named))
    uses = {k: len(re.findall(r"\bdbg\.store\b", code[k])) for k in ("debug", "pdbg", "pdebug")}
    ck("P1b every message statement of the three goes to dbg.store: 7 uses in debug (send.message 5, dbg.stop 2), 12 in pdbg, 15 in pdebug", uses == {"debug": 7, "pdbg": 12, "pdebug": 15}, repr(uses))
    stray = []
    seen = 0
    for k in ("pdbg", "pdebug"):
        for ln in code[k].split("\n"):
            m = re.search(r"^\s*(?:readu?\s+[\w.]+\s+from|write\s+.+?\s+to|delete|recordlocku|release)\s+([\w.]+)", ln)
            if m and m.group(1) not in ("dbg.store",):
                stray.append(k + ": " + ln.strip()[:60])
            seen += 1 if m else 0
    ck("P1c every record statement of pdbg and pdebug (readu, read, write, delete, recordlocku, release) names dbg.store and no other file (some 20 of them)",
       not stray and seen >= 18, repr((seen, stray[:3])))

    ck("P2a !pdbg_store is $internal, `subroutine pdbg_store(pf, why)`, catalogued as !pdbg_store",
       store.lstrip().startswith("$internal") and re.search(r"^subroutine pdbg_store\(pf, why\)$", store, re.M) is not None and "$catalog !pdbg_store" in store, "")
    ck("P2b ...and no other program of gpl.bp takes the catalogue name", sum(1 for t in others.values() if re.search(r"^\$catalog\s+!pdbg_store\b", t, re.M | re.I)) == 0
       and len(re.findall(r"^\$catalog", store, re.M)) == 1, "")
    ck("P3a the directory is .local/state/sd/pdebug below the home", "STORE = '.local/state/sd/pdebug'" in store and store.count("STORE = ") == 1, "")
    ck("P3b pf and why are assigned first; root and an empty user are refused; the home is SD_USER_HOME's and never an environment variable",
       ordered(store, "pf = ''", "why = 'user'", "kernel(K$USERNAME, 0)", "if ps.user = '' or ps.user = 'root' then return", "why = 'home'",
               "ps.home = SDEXT('', @FALSE, SD_USER_HOME)", "if ps.home = '' then return")
       and re.search(r"getenv|environment|\$HOME", store, re.I) is None and "'HOME'" not in store, "")
    ck("P3c the directory is made and checked BEFORE it is opened; the file is opened with mark mapping OFF (a message keeps its field marks); `why` is '' only after that",
       ordered(store, "why = 'directory'", "gosub make.dir", "if not(dir.ok) then return", "why = 'open'", "openpath ps.dir to pf else", "mark.mapping pf, off", "why = ''")
       and store.count("why = ''") == 1, "")
    ck("P3d it touches only the store: no OPENSEQ, no execute, no OSPATH other than EXISTS and MKDIR, no os.execute",
       re.search(r"\b(openseq|execute|os\.execute|osopen|oscopy)\b", store, re.I) is None
       and sorted(re.findall(r"ospath\([^,]+,\s*(OS\$\w+)\)", store)) == ["OS$EXISTS", "OS$MKDIR"], "")
    ck("P4a make.dir walks the path from the home down: a directory SD_USER_HOME does not trust that is already there stops it; one it makes is made under umask 63 "
       "(0700) and must be trusted before the next",
       ordered(store, "make.dir:", "md.n = dcount(STORE, '/')", "if SDEXT(md.rel, @FALSE, SD_USER_HOME) # md.path then", "if ospath(md.path, OS$EXISTS) then return",
               "md.um = umask(63)", "ospath(md.path, OS$MKDIR)", "if umask(md.um) then null", "if SDEXT(md.rel, @FALSE, SD_USER_HOME) # md.path then return", "gosub check.dir"), "")
    ck("P4b check.dir asks SD_USER_HOME for the whole path again and SD_FILE_PRIVATE for 'DIR' (owner-only), and the answer is that test alone",
       ordered(store, "check.dir:", "dir.ok = @false", "if SDEXT(STORE, @FALSE, SD_USER_HOME) # ps.dir then return",
               "dir.ok = (SDEXT(ps.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) = '1')")
       and store.count("dir.ok = @true") == 0, "")

    ck("P5a PDEBUG makes the store BEFORE it turns BREAK off and before any record, and stops with 11948 and the reason when it cannot",
       ordered(pdebug, "call !pdbg_store(dbg.store, store.why)", "if store.why # '' then stop sysmsg(11948, store.why)", "break off", "recordlocku dbg.store, start.id"), "")
    ck("P5b PDEBUG removes the records of its own user number (in.id, out.id) before it writes START, and START is written last of those",
       ordered(pdebug, "in.id = 'D.':@userno", "out.id = 'DR.':@userno", "recordlocku dbg.store, in.id", "delete dbg.store, in.id", "recordlocku dbg.store, out.id",
               "delete dbg.store, out.id", "start.id = 'DR.':@who:'!':@logname", "write out.msg to dbg.store, start.id"), "")
    ck("P6a PDBG makes the store before it reads START, and a store it cannot make is `cannot debug` (NO_PDEBUG, or the old stop)",
       ordered(pdbg, "call !pdbg_store(dbg.store, store.why)", "if store.why # '' then goto cannot.debug", "readu in.msg from dbg.store, id else goto cannot.debug"), "")
    ck("P6b PDBG takes START only when it says START, and a PDEBUG that is gone (kernel(K$USERS, n) empty) has its record deleted and is not answered; the answer "
       "(D.n deleted, the conversation) comes after that",
       ordered(pdbg, "if in.msg<1> # 'START' then goto cannot.debug", "debugger.uid = in.msg<2>", "if kernel(K$USERS, debugger.uid) = '' then",
               "delete dbg.store, id", "goto cannot.debug", "end", "delete dbg.store, id", "id = 'D.':debugger.uid", "debug.initialised = @true"), "")
    ck("P6c cannot.debug gives the locks back only when the store was made (a store that could not be made is not a file to release)",
       ordered(pdbg, "cannot.debug:", "if store.why = '' then release dbg.store", "caught('SYS.PROGRAM.NO_PDEBUG', 3)"), "")
    ck("P7 debug.h holds dbg.store once, in the common block /$debug/ shared by PDEBUG and DEBUG", len(re.findall(r"\bdbg\.store\b", between(hdr, "common /$debug/", "$define DE$WATCH"))) == 1, "")
    ck("P8 message %d exists, takes the reason as %%1 and says the phantom debugger cannot start; nothing but PDEBUG asks for it" % MSG,
       "%1" in msgs.get(MSG, "") and "debugger" in msgs.get(MSG, "") and len(re.findall(r"\b%d\b" % MSG, "\n".join(code[k] for k in code))) == 1
       and not any(re.search(r"\b%d\b" % MSG, strip(t)) for n, t in others.items()), repr(msgs.get(MSG)))
    return rows


def load():
    src = {}
    for k, p in FILES.items():
        with open(p, encoding="latin-1") as f:
            src[k] = f.read()
    msgs = {}
    p = os.path.join(SDSYS, "messages", str(MSG))
    if os.path.isfile(p):
        with open(p, encoding="latin-1") as f:
            msgs[MSG] = f.read()
    others = {}
    for n in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, n)
        if n not in FILES and os.path.isfile(p):
            with open(p, encoding="latin-1") as f:
                others[n] = f.read()
    return src, msgs, others


def report(rows):
    bad = 0
    for name, ok, detail in rows:
        bad += 0 if ok else 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
    return bad


# (file, name, old, new): each must match its file's text once and be caught
MUTANTS = [
    # the conversation goes back to $ipc
    ("pdbg", "PDBG reads START from $ipc again", "readu in.msg from dbg.store, id else goto cannot.debug", "readu in.msg from ipc.f, id else goto cannot.debug"),
    ("pdebug", "PDEBUG writes START to $ipc again", "write out.msg to dbg.store, start.id", "write out.msg to ipc.f, start.id"),
    ("debug", "DEBUG sends its message through $ipc again", "   write out.msg to dbg.store, id\n   wake debugger.uid\n\n   id = 'D.':@userno", "   write out.msg to ipc.f, id\n   wake debugger.uid\n\n   id = 'D.':@userno"),
    ("pdbg", "PDBG answers through a second, unnamed file", "      write out.msg to dbg.store, id\n      wake debugger.uid", "      write out.msg to other.f, id\n      wake debugger.uid"),
    # the store
    ("pdbg_store", "root may have a store", "   if ps.user = '' or ps.user = 'root' then return", "   if ps.user = '' then return"),
    ("pdbg_store", "the home is not the trusted one", "   ps.home = SDEXT('', @FALSE, SD_USER_HOME)", "   ps.home = '/tmp'"),
    ("pdbg_store", "the file keeps the mark mapping (a field mark becomes a line end)", "   mark.mapping pf, off\n", ""),
    ("pdbg_store", "the directory is opened without being made", "   gosub make.dir\n   if not(dir.ok) then return\n", ""),
    ("pdbg_store", "the owner-only test is gone", "   dir.ok = (SDEXT(ps.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) = '1')", "   dir.ok = @true"),
    ("pdbg_store", "a directory is made under the process's umask", "         md.um = umask(63)", "         md.um = umask(0)"),
    ("pdbg_store", "a made directory is not tried again", "         if SDEXT(md.rel, @FALSE, SD_USER_HOME) # md.path then return\n      end\n   next md.i", "      end\n   next md.i"),
    ("pdbg_store", "a directory that is there and not trusted is used", "         if ospath(md.path, OS$EXISTS) then return             ;* there, and not to be trusted\n", ""),
    ("pdbg_store", "the store is somewhere else", "STORE = '.local/state/sd/pdebug'", "STORE = '.local/state/sd/pdebug2'"),
    ("pdbg_store", "the store reads the environment", "   ps.user = downcase(trim(kernel(K$USERNAME, 0)))", "   ps.user = downcase(trim(kernel(K$USERNAME, 0)))\n   ps.env = getenv('HOME')"),
    # PDEBUG
    ("pdebug", "PDEBUG makes the store after it turned BREAK off", "   call !pdbg_store(dbg.store, store.why)\n   if store.why # '' then stop sysmsg(11948, store.why)\n\n   break off\n", "   break off\n\n   call !pdbg_store(dbg.store, store.why)\n   if store.why # '' then stop sysmsg(11948, store.why)\n"),
    ("pdebug", "PDEBUG goes on without a store", "   if store.why # '' then stop sysmsg(11948, store.why)\n", ""),
    ("pdebug", "PDEBUG leaves the records of its user number", "   recordlocku dbg.store, in.id\n   delete dbg.store, in.id\n   recordlocku dbg.store, out.id\n   delete dbg.store, out.id\n", ""),
    # PDBG
    ("pdbg", "PDBG answers a START whose PDEBUG has gone", "      if kernel(K$USERS, debugger.uid) = '' then\n         delete dbg.store, id      ;* PDEBUG has gone and left its record: nobody is waiting\n         goto cannot.debug\n      end\n", ""),
    ("pdbg", "PDBG goes on when it has no store", "      if store.why # '' then goto cannot.debug\n", ""),
    ("pdbg", "cannot.debug releases a store that was never made", "   if store.why = '' then release dbg.store      ;* store.why is set by the call above, before any jump here", "   release dbg.store"),
    # the header
    ("debug.h", "the common block has no store", "dbg.store                    ;* 31 Oct 26 (W.11 F10b)", "dbg.store2                   ;* 31 Oct 26 (W.11 F10b)"),
]
MSG_MUTANTS = [("message 11948 is missing", None), ("message 11948 has no reason in it", "The debugger's private directory could not be set up\n")]


def selftest():
    src, msgs, others = load()
    if any(not ok for _, ok, _ in checks(src, msgs, others)):
        print("REFUSING - the unmutated source already fails", file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: each mutation must be CAUGHT and match its text once ---")
    for fk, name, old, new in MUTANTS:
        if src[fk].count(old) != 1:
            print("  [FAIL] %s: the text matches %d times in %s, not once" % (name, src[fk].count(old), fk))
            holes += 1
            continue
        mut = dict(src)
        mut[fk] = src[fk].replace(old, new)
        caught = [n.split(" ")[0] for n, ok, _ in checks(mut, msgs, others) if not ok]
        print("  [%s] %s%s" % ("pass" if caught else "FAIL", name, ": caught by " + ", ".join(caught[:3]) if caught else ": NOT CAUGHT"))
        holes += 0 if caught else 1
    for name, text in MSG_MUTANTS:
        m2 = dict(msgs)
        if text is None:
            m2.pop(MSG, None)
        else:
            m2[MSG] = text
        caught = [n.split(" ")[0] for n, ok, _ in checks(src, m2, others) if not ok]
        print("  [%s] %s%s" % ("pass" if caught else "FAIL", name, ": caught by " + ", ".join(caught) if caught else ": NOT CAUGHT"))
        holes += 0 if caught else 1
    # another program takes the catalogue name
    o2 = dict(others)
    o2["zz_clash"] = "$internal\nsubroutine zz_clash\n$catalog !pdbg_store\nend\n"
    caught = [n.split(" ")[0] for n, ok, _ in checks(src, msgs, o2) if not ok]
    print("  [%s] another program takes the catalogue name%s" % ("pass" if caught else "FAIL", ": caught by " + ", ".join(caught) if caught else ": NOT CAUGHT"))
    holes += 0 if caught else 1
    total = len(MUTANTS) + len(MSG_MUTANTS) + 1
    print("\n%d of %d mutants caught, %d missed" % (total - holes, total, holes))
    return 1 if holes else 0


def main():
    missing = [p for p in FILES.values() if not os.path.isfile(p)]
    if missing:
        print("test-pdbgstore-units: CANNOT RUN - not readable: %s" % missing, file=sys.stderr)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    src, msgs, others = load()
    rows = checks(src, msgs, others)
    bad = report(rows)
    print("\nNOT MEASURED HERE: that a conversation works end to end (sandbox-oq2.py 251), that a record forged in $ipc is ignored (sandbox-sysexc.py), that another operating-system user cannot enter the directory (the VM).")
    print("test-pdbgstore-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
