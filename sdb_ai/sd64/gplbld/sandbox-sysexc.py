#!/usr/bin/env python3
#
# sandbox-sysexc.py - 17 Oct 2026, QM4 Fixes 354 and 513: run time errors as SYS.* exceptions, exception GROUPS, the
#                     rollback of a transaction begun inside a TRY clause, and SYS.PROGRAM.NO_PDEBUG.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sysexc.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree
# (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 17 Oct 26 dm  Written.  Triggers were found on a sandbox built from the tree before the change, by running each program
#               with no TRY and reading the message it aborted with; the message number each stands for is in the label.
# END-HISTORY
#
# Each case is (label, subs, body, wanted).  subs = {name: source} are catalogued subroutines (lower case names) made
# first; the body is compiled as program zzsxNN and the value it leaves in x is printed between brackets.  A row passes
# only if x is what is wanted AND the session printed no abort line (a message "00000123: ... at line N of ..."): a
# caught error must leave the terminal alone.  The rows after the cases are special: errors with nothing to catch them,
# the EXECUTE barrier, the phantom debugger.

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ABORT_LINE = re.compile(r"(?m)^[0-9A-F]{8}: ")
passed = failed = 0

OPEN_F = "open 'zzsxf' to f else stop 'nofile'"
DIV0 = "y = 1 / zz"  # zz is set to 0 by ZERO

SUB_DIV = "subroutine zzsxd(r)\n   zz = 0\n   r = 1 / zz\nreturn\nend\n"
SUB_DEEP = "subroutine zzsxe(r)\n   call zzsxd(r)\n   crt 'NOT REACHED zzsxe'\nreturn\nend\n"
SUB_QUIET = "subroutine zzsxq(r)\n   r = 'quiet'\nreturn\nend\n"
SUB_ONE = "subroutine zzsx1(a)\n   crt 'NOT REACHED zzsx1'\nreturn\nend\n"
ALLSUBS = {"zzsxd": SUB_DIV, "zzsxe": SUB_DEEP, "zzsxq": SUB_QUIET, "zzsx1": SUB_ONE}


def catches(trigger, name, pre="", post="", extra=""):
    """A TRY around one trigger that must be caught under the full name; x is @EXCEPTION."""
    return (("%s\n" % pre if pre else "") + "try\n   %s\n   x = 'NOT CAUGHT'\ncatch %s\n   x = @exception\n%send" %
            (trigger, name, extra)) + ("\n" + post if post else "")


# 1. each kind of error, thrown under its SYS name (label: the message the abort printed on the unchanged build)
NAMES = [
    ("1105 an unassigned variable", "y = unas1 + 1", "SYS.PROGRAM.DATATYPE.UNASSIGNED", "", ""),
    ("1104 a non-numeric value", "a = 'abc'\n   y = a + 1", "SYS.PROGRAM.DATATYPE.NOT_NUMERIC", "", ""),
    ("1108 divide by zero", "zz = 0\n   y = 1 / zz", "SYS.PROGRAM.DIV_ZERO", "", ""),
    ("1100 matrix subscript out of range", "m(7) = 1", "SYS.PROGRAM.INVALID_MATRIX_INDEX", "dim m(3)", ""),
    ("1118 select list number out of range", "readlist l from 99 else null", "SYS.SELECT.INVALID_LIST_NO", "", ""),
    ("1133 GOSUBs nested too deeply", "gosub deep", "SYS.PROGRAM.LIMIT.GOSUB_DEPTH", "",
     "goto fin\ndeep: gosub deep\nreturn\nfin: null"),
    ("1134 a subroutine that is not catalogued", "nm = 'zznosuchsub'\n   call @nm()", "SYS.PROGRAM.NOT_FOUND", "", ""),
    ("1130 an illegal call name", "nm = 'Bad Name!'\n   call @nm()", "SYS.PROGRAM.INVALID_CALL_NAME", "", ""),
    ("1005 a CALL with the wrong number of arguments", "call zzsx1(1, 2)", "SYS.PROGRAM.INVALID_ARGCT", "", ""),
    ("11121 a collection operation on a string", "q = 'abc'\n   y = q{'x'}", "SYS.PROGRAM.DATATYPE.NOT_COLLECTION", "", ""),
    ("11122 an empty collection element name", "c = jparse(\"{'a':1}\")\n   y = c{''}", "SYS.PROGRAM.INVALID_NAME", "", ""),
    ("11398 SORTADD on something that is not a sort variable", "sortadd 'abc', 'k'", "SYS.PROGRAM.DATATYPE.NOT_SORT", "", ""),
    ("10004 a string over the maximum size", "y = str('x', 2000000000)", "SYS.PROGRAM.INVALID_DATA_SIZE", "", ""),
    ("1600 an illegal TRIM mode", "y = trim('abc', '', 'X')", "SYS.PROGRAM.RANGE", "", ""),
    ("1138 a socket function on a string", "y = 'abc'\n   y = read.socket(y, 10, 0, 0)", "SYS.PROGRAM.DATATYPE.NOT_SOCKET", "", ""),
    ("1115 an invalid print unit", "print on 999 'x'", "SYS.PRINTER.INVALID_UNIT", "", ""),
    ("1119 CLEARFILE inside a transaction", "begin transaction\n      clearfile f\n   end transaction",
     "SYS.PROGRAM.INVALID_IN_TXN", OPEN_F, ""),
    ("1418 WEOFSEQ on a file that is not a sequential file", "weofseq g", "SYS.FILESYS.INVALID_FILE_TYPE",
     "open 'VOC' to g else stop 'novoc'", ""),
    ("1413 SELECT of something that is not a file", "openseq 'zzsxf.dat' to g2 else null\n   select g2", "SYS.FILESYS.INVALID_FILE_TYPE", "", ""),
    ("10151 a WRITE in a transaction with no lock on the record", "begin transaction\n      write 'one' to f, 'nolock'\n   end transaction",
     "SYS.FILESYS.LOCK_REQUIRED", OPEN_F, ""),
]

CASES = []
for label, trigger, name, pre, post in NAMES:
    CASES.append(("%s is thrown as %s" % (label, name), ALLSUBS, catches(trigger, name, pre, post), name))

# 2. groups of exceptions: a handler takes its own name and everything below it, whole components only
ZERO = "zz = 0"
CASES += [
    ("a handler for SYS.PROGRAM takes SYS.PROGRAM.DIV_ZERO (a group)", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch sys.program\n   x = 'group ':@exception\nend", "group SYS.PROGRAM.DIV_ZERO"),
    ("a handler for SYS takes every system exception", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch sys\n   x = 'sys ':@exception\nend", "sys SYS.PROGRAM.DIV_ZERO"),
    ("a handler for another group, SYS.LOCKS, does not: the outer SYS.PROGRAM one does", {},
     ZERO + "\ntry\n   try\n      " + DIV0 + "\n   catch sys.locks\n      x = 'inner'\n   end\ncatch sys.program\n   x = 'outer'\nend", "outer"),
    ("a handler is whole components: SYS.PROG does not take SYS.PROGRAM.DIV_ZERO", {},
     ZERO + "\ntry\n   try\n      " + DIV0 + "\n   catch sys.prog\n      x = 'inner'\n   end\ncatch sys$any\n   x = 'outer'\nend", "outer"),
    ("the first clause that covers the name is the one used: the specific name written first", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch sys.program.div_zero\n   x = 'specific'\ncatch sys.program\n   x = 'group'\nend", "specific"),
    ("...and the group written first", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch sys.program\n   x = 'group'\ncatch sys.program.div_zero\n   x = 'specific'\nend", "group"),
    ("exception names are not case sensitive, system ones included", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch Sys.Program.Div_Zero\n   x = 'caught'\nend", "caught"),
    ("SYS$ANY takes a system exception, @EXCEPTION is its real name", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch sys$any\n   x = 'any ':@exception\nend", "any SYS.PROGRAM.DIV_ZERO"),
    ("SYS$UNHANDLED takes one nobody names", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch other.thing\n   x = 'other'\ncatch sys$unhandled\n   x = 'unhandled ':@exception\nend",
     "unhandled SYS.PROGRAM.DIV_ZERO"),
    ("a user group: CATCH account takes THROW account.invalid.closed", {},
     "try\n   throw 'account.invalid.closed'\ncatch account\n   x = @exception\nend", "account.invalid.closed"),
    ("a user group: CATCH account.invalid takes THROW account.invalid.closed", {},
     "try\n   throw 'Account.Invalid.Closed'\ncatch account.invalid\n   x = @exception\nend", "Account.Invalid.Closed"),
    ("a user group does not work upward: CATCH account.invalid does not take THROW account", {},
     "try\n   try\n      throw 'account'\n   catch account.invalid\n      x = 'inner'\n   end\ncatch account\n   x = 'outer'\nend", "outer"),
    ("a user group is whole components: CATCH acc does not take THROW account.x", {},
     "try\n   try\n      throw 'account.x'\n   catch acc\n      x = 'inner'\n   end\ncatch sys$any\n   x = 'outer'\nend", "outer"),
    ("CAUGHT sees a group handler: account covers account.invalid.closed, account.invalid does not cover account", {},
     "try\n   x = caught('account.invalid.closed'):caught('account.invalid'):caught('accountant')\ncatch account\n   null\nend", "110"),
    ("CAUGHT of a system name sees a group handler", {},
     "try\n   x = caught('SYS.PROGRAM.DIV_ZERO'):caught('sys.locks.deadlock')\ncatch sys.program\n   null\nend", "10"),
    ("CAUGHT with modes 1 counts SYS$ANY for a system name", {},
     "try\n   x = caught('SYS.PROGRAM.DIV_ZERO'):caught('SYS.PROGRAM.DIV_ZERO', 1)\ncatch sys$any\n   null\nend", "01"),
]

# 3. what the exception carries
CASES += [
    ("@EXCEPTION.DATA is the abort message: the same as @ABORT.MESSAGE, with the address, text and place", {},
     ZERO + "\ntry\n   " + DIV0 + "\ncatch sys.program.div_zero\n   d = @exception.data\n"
     "   x = (d = @abort.message):'/':(index(d, 'Divide by zero error', 1) > 0):'/':(index(d, ' at line ', 1) > 0)\nend", "1/1/1"),
    ("@EXCEPTION.ORIGIN names the line of the failing statement, the one the message names", {},
     ZERO + "\ntry\n   " + DIV0 + "\n   x = 'NOT CAUGHT'\ncatch sys.program.div_zero\n   ln = field(@exception.origin, @fm, 2)\n"
     "   x = ln:'/':(index(@exception.data, ' at line ':ln:' of ', 1) > 0)\nend", "4/1"),
    ("SAVING.STACK works for a system exception: the innermost program is the subroutine that divided", {"zzsxd": SUB_DIV},
     "try\n   call zzsxd(r)\ncatch sys.program.div_zero saving.stack\n   p1 = field(field(@exception.stack, @fm, 1), @vm, 1)\n"
     "   x = field(p1, '/', dcount(p1, '/'))\nend", "zzsxd"),
]

# 4. the flow after an exception
CASES += [
    ("an error two CALL levels down is caught in the caller, which carries on", ALLSUBS,
     "try\n   call zzsxe(r)\n   x = 'NOT REACHED'\ncatch sys.program.div_zero\n   x = 'caught'\nend\nx := ' then continues'", "caught then continues"),
    ("a subroutine can be CALLed after the unwind", ALLSUBS,
     "try\n   call zzsxe(r)\ncatch sys.program.div_zero\n   null\nend\ncall zzsxq(r2)\nx = r2", "quiet"),
    ("after a GOSUB overflow the GOSUB stack is back: a GOSUB and RETURN work", {},
     "try\n   gosub deep\ncatch sys.program.limit.gosub_depth\n   x = 'caught'\nend\ngosub ok\ngoto fin\ndeep: gosub deep\nreturn\nok: x := ' ok'\nreturn\nfin: null",
     "caught ok"),
    ("an error half way through an expression with string temporaries; strings and loops still work after", {},
     ZERO + "\ns = 'abc'\ntry\n   x = s : 'def' : (1 / zz) : 'ghi'\ncatch sys.program.div_zero\n   x = 'caught'\nend\n"
     "for i = 1 to 3\n   x := i\nnext i\nx := '/':s", "caught123/abc"),
    ("an error inside a FOR loop inside the TRY; a new FOR loop works after", {},
     ZERO + "\ntry\n   for i = 1 to 5\n      if i = 3 then y = 1 / zz\n   next i\ncatch sys.program.div_zero\n   x = 'caught at ':i\nend\n"
     "for j = 1 to 2\n   x := j\nnext j", "caught at 312"),
    ("200 caught errors in a loop leave no handler behind (the limit is 64)", {},
     ZERO + "\ncnt = 0\nfor i = 1 to 200\n   try\n      " + DIV0 + "\n   catch sys.program.div_zero\n      cnt += 1\n   end\nnext i\nx = cnt", "200"),
]

# 5. transactions: the one begun inside the TRY clause goes, the one before it stays
TXN_USER = ("zz = 0\n" + OPEN_F + "\ntry\n   begin transaction\n      readu q from f, 'rA' else null\n      write 'one' to f, 'rA'\n"
            "      %s\n   end transaction\ncatch %s\n   x = 'caught'\nend\n"
            "read q from f, 'rA' then x := ' present' else x := ' absent'\nx := ' depth ':system(1008)")
CASES += [
    ("THROW out of a transaction begun in the TRY clause: the write is rolled back, the depth is 0", {},
     TXN_USER % ("throw 'oops'", "oops"), "caught absent depth 0"),
    ("a system exception does the same", {},
     TXN_USER.replace("'rA'", "'rB'") % (DIV0, "sys.program.div_zero"), "caught absent depth 0"),
    ("a transaction begun before the TRY survives: the inner one is rolled back, the outer one commits", {},
     "zz = 0\n" + OPEN_F + "\nbegin transaction\n   readu q from f, 'rC' else null\n   write 'two' to f, 'rC'\n   try\n"
     "      begin transaction\n         readu q from f, 'rD' else null\n         write 'three' to f, 'rD'\n         " + DIV0 + "\n"
     "      end transaction\n   catch sys.program.div_zero\n      x = 'caught depth ':system(1008)\n   end\n   commit\nend transaction\n"
     "read q from f, 'rC' then x := ' rC present' else x := ' rC absent'\nread q from f, 'rD' then x := ' rD present' else x := ' rD absent'\n"
     "x := ' depth ':system(1008)", "caught depth 1 rC present rD absent depth 0"),
]

LOCKLIMIT = ("CONFIG MAXRLOCK 2", "CONFIG MAXRLOCK 0")


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
    say("sandbox-sysexc: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=900)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def has(out, pat):
    return re.search(pat, out, re.M) is not None


MARK = "# --- sandbox-sysexc below ---"


def tool(box, *args, **kw):
    return subprocess.run([sys.executable, TOOL, box] + list(args), capture_output=True, text=True, errors="replace",
                          timeout=kw.pop("timeout", 900), **kw)


def started(box):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-status"], capture_output=True, text=True,
                       errors="replace", env=env, timeout=60)
    return re.search(r"(?m)^Started\s+20\d\d-", p.stdout + p.stderr) is not None


def restart(box, *extra):
    """Stop the sandbox, put `extra` lines in sd.conf below the marker, start it, and say whether SD is running."""
    conf = os.path.join(box, "sd.conf")
    tool(box, "stop", timeout=120)
    with open(conf) as f:
        base = f.read().split(MARK)[0].rstrip("\n") + "\n"
    with open(conf, "w") as f:
        f.write(base + ((MARK + "\n" + "".join(l + "\n" for l in extra)) if extra else ""))
    tool(box, "start", timeout=180)
    ok = started(box)
    say("  -- sd.conf %s: SD %s" % (("+ " + " ".join(extra)) if extra else "as built", "started" if ok else "NOT STARTED"))
    return ok


def source(i, body):
    """The probe program: line 1 is x = '', the body's lines follow from line 2."""
    lines = "".join("   %s\n" % ln for ln in body.split("\n") if ln)
    return "   x = ''\n" + lines + "   crt 'C%02d[':x:']'\nend\n" % i


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sysexc.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    bp = os.path.join(sysd, "bp")
    say("sandbox-sysexc: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sysexc: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    catalogued = []
    try:
        out = sess(box, "CREATE.FILE zzsxf")
        if not has(out, r"(?i)created"):
            say("  [note] CREATE.FILE zzsxf: %s" % out[-200:].replace("\n", " | "))
        for nm, text in ALLSUBS.items():
            p = os.path.join(bp, nm)
            write(p, text)
            made.append(p)
            out = sess(box, "BASIC bp %s" % nm, "CATALOG bp %s" % nm)
            if not has(out, r"(?i)compiled 1 program"):
                say("  [note] %s: %s" % (nm, out[-200:].replace("\n", " | ")))
            catalogued.append(nm)

        say("\n--- the exceptions, the groups, what they carry, the flow ----------------------------------")
        for i, (label, subs, body, want) in enumerate(CASES):
            for nm, text in subs.items():
                if nm not in catalogued:
                    p = os.path.join(bp, nm)
                    write(p, text)
                    made.append(p)
                    sess(box, "BASIC bp %s" % nm, "CATALOG bp %s" % nm)
                    catalogued.append(nm)
            prog = "zzsx%02d" % i
            p = os.path.join(bp, prog)
            write(p, source(i, body))
            made.append(p)
            out = sess(box, "BASIC bp %s" % prog, "RUN bp %s" % prog)
            m = re.search(r"(?m)^C%02d\[(.*)\]\s*$" % i, out)
            got = m.group(1) if m else None
            row("%s: wanted %r" % (label, want), got == want and not ABORT_LINE.search(out),
                ("got %r" % got) if m and not ABORT_LINE.search(out) else out[-300:].replace("\n", " | "))

        say("\n--- the lock limit (MAXRLOCK is set for the one program and put back) --------------------------")
        prog = "zzsxlk"
        p = os.path.join(bp, prog)
        write(p, "   x = ''\n   execute 'CONFIG MAXRLOCK 2' capturing j\n   open 'VOC' to f else stop 'novoc'\n   try\n"
                 "      recordlocku f, 'a'\n      recordlocku f, 'b'\n      recordlocku f, 'c'\n      x = 'NOT CAUGHT'\n"
                 "   catch sys.locks.limit\n      x = @exception\n   end\n   execute 'CONFIG MAXRLOCK 0' capturing j\n"
                 "   crt 'LK[':x:']'\nend\n")
        made.append(p)
        out = sess(box, "BASIC bp %s" % prog, "RUN bp %s" % prog)
        sess(box, "CONFIG MAXRLOCK 0")
        row("11162 the record lock limit is thrown as SYS.LOCKS.LIMIT", has(out, r"(?m)^LK\[SYS\.LOCKS\.LIMIT\]\s*$") and not ABORT_LINE.search(out),
            out[-300:].replace("\n", " | "))

        say("\n--- a deadlock (DEADLOCK=1; two phantoms, each holding a record and asking for the other's) ---------")
        # A holds a and after 3 s asks for b; B holds b and after 5 s asks for a, so B's request closes the circle and is the
        # one refused.  B catches it and ends, which frees b for A.
        da, db, dp = (os.path.join(bp, n) for n in ("zzsxda", "zzsxdb", "zzsxdp"))
        made.extend([da, db, dp])
        write(da, "   open 'zzsxdl' to f else stop 'nofile'\n   readu r from f, 'a' else null\n   sleep 3\n"
                  "   readu r from f, 'b' else null\n   write 'got-b' to f, 'dlA'\nend\n")
        write(db, "   open 'zzsxdl' to f else stop 'nofile'\n   readu r from f, 'b' else null\n   sleep 5\n   try\n"
                  "      readu r from f, 'a' else null\n      write 'NOT CAUGHT' to f, 'dlB'\n   catch sys.locks.deadlock\n"
                  "      write 'caught:':@exception:'/':(index(@exception.data, 'Deadlock detected', 1) > 0) to f, 'dlB'\n   end\nend\n")
        write(dp, "   x = ''\n   execute 'DELETE.FILE zzsxdl' capturing j\n   execute 'CREATE.FILE zzsxdl' capturing j\n"
                  "   open 'zzsxdl' to f else stop 'nofile'\n   execute 'PHANTOM NO.MSG RUN bp zzsxda' capturing o\n   sleep 1\n"
                  "   execute 'PHANTOM NO.MSG RUN bp zzsxdb' capturing o\n   for w = 1 to 40\n      read q from f, 'dlA' then exit\n"
                  "      sleep 1\n   next w\n   sleep 1\n   for each id in 'dlA':@fm:'dlB'\n"
                  "      read q from f, id then x := id:'=':q:'|' else x := id:' absent|'\n   next id\n   crt 'DL[':x:']'\n"
                  "   execute 'DELETE.FILE zzsxdl' capturing j\nend\n")
        if not restart(box, "DEADLOCK=1"):
            row("SD restarts with DEADLOCK=1", False, "it did not start")
        else:
            out = sess(box, "BASIC bp zzsxda", "BASIC bp zzsxdb", "BASIC bp zzsxdp", "RUN bp zzsxdp")
            m = re.search(r"(?m)^DL\[(.*)\]\s*$", out)
            got = m.group(1) if m else None
            row("1114 the deadlock is thrown as SYS.LOCKS.DEADLOCK in the process refused, which carries on; the other gets its lock",
                got == "dlA=got-b|dlB=caught:SYS.LOCKS.DEADLOCK/1|", ("got %r" % got) if m else out[-300:].replace("\n", " | "))
        restart(box)   # DEADLOCK is back to its default for what follows

        say("\n--- nothing to catch it: the error aborts as it always did -----------------------------------------")
        write(p, "   zz = 0\n   x = ''\n   y = 1 / zz\n   crt 'SURVIVED[':x:']'\nend\n")
        out = sess(box, "BASIC bp %s" % prog, "RUN bp %s" % prog)
        row("CONTROL: with no TRY, divide by zero aborts and says so", has(out, r"(?m)^[0-9A-F]{8}: Divide by zero error at line 3 of ") and not has(out, "SURVIVED"),
            out[-250:].replace("\n", " | "))
        write(p, "   zz = 0\n   x = ''\n   try\n      y = 1 / zz\n   catch other.name\n      x = 'WRONGLY CAUGHT'\n   end\n   crt 'SURVIVED[':x:']'\nend\n")
        out = sess(box, "BASIC bp %s" % prog, "RUN bp %s" % prog)
        row("a TRY whose handlers do not name it lets the error abort, with the same message",
            has(out, r"(?m)^[0-9A-F]{8}: Divide by zero error at line 4 of ") and not has(out, "SURVIVED|WRONGLY"), out[-250:].replace("\n", " | "))
        write(p, "   zz = 0\n   x = ''\n   try\n      y = 1 / zz\n   catch sys.locks\n      x = 'WRONGLY CAUGHT'\n   end\n   crt 'SURVIVED[':x:']'\nend\n")
        out = sess(box, "BASIC bp %s" % prog, "RUN bp %s" % prog)
        row("a handler for another SYS group does not catch it either",
            has(out, r"(?m)^[0-9A-F]{8}: Divide by zero error at line 4 of ") and not has(out, "SURVIVED|WRONGLY"), out[-250:].replace("\n", " | "))
        write(p, "   x = ''\n   try\n      y = unas1 + 1\n   catch sys.program.div_zero\n      x = 'WRONGLY CAUGHT'\n   end\n   crt 'SURVIVED[':x:']'\nend\n")
        out = sess(box, "BASIC bp %s" % prog, "RUN bp %s" % prog)
        row("a handler for DIV_ZERO does not take an unassigned variable",
            has(out, r"(?m)^[0-9A-F]{8}: Unassigned variable UNAS1 at line 3 of ") and not has(out, "SURVIVED|WRONGLY"), out[-250:].replace("\n", " | "))

        # a program run by EXECUTE is a barrier: an error in there is not caught by a TRY around the EXECUTE
        inner = os.path.join(bp, "zzsxin")
        write(inner, "   zz = 0\n   y = 1 / zz\nend\n")
        made.append(inner)
        write(p, "   x = ''\n   try\n      execute 'RUN bp zzsxin'\n      x = 'after execute'\n   catch sys$any\n      crt 'WRONGLY_CAUGHT'\n   end\n   crt 'BARRIER[':x:']'\nend\n")
        out = sess(box, "BASIC bp zzsxin", "BASIC bp %s" % prog, "RUN bp %s" % prog)
        row("an error inside an EXECUTEd program is not caught by a TRY around the EXECUTE",
            has(out, r"(?m)^[0-9A-F]{8}: Divide by zero error") and not has(out, "WRONGLY_CAUGHT"), out[-300:].replace("\n", " | "))

        say("\n--- 513 the phantom debugger (no PDEBUG is waiting) -----------------------------------------------")
        ph = os.path.join(bp, "zzsxph")
        made.append(ph)
        # variants: the handler named, a group handler, SYS$ANY, no handler
        variants = [
            ("a handler for SYS.PROGRAM.NO_PDEBUG", "catch sys.program.no_pdebug", "caught:SYS.PROGRAM.NO_PDEBUG/Phantom debugger not active", True),
            ("a handler for the group SYS.PROGRAM", "catch sys.program", "caught:SYS.PROGRAM.NO_PDEBUG/Phantom debugger not active", True),
            ("a SYS$ANY handler", "catch sys$any", "caught:SYS.PROGRAM.NO_PDEBUG/Phantom debugger not active", True),
            ("CONTROL: a handler for something else", "catch other.name", None, False),
        ]
        for vlabel, catch, want, goes_on in variants:
            write(ph, "   open 'zzsxf' to f else stop 'nofile'\n"
                      "   write 'started' to f, 'ph1'\n   try\n      debug\n      write 'no throw' to f, 'ph2'\n   %s\n"
                      "      write 'caught:':@exception:'/':@exception.data to f, 'ph2'\n   end\n   write 'finished' to f, 'ph3'\nend\n" % catch)
            # the parent clears the records first (a stale ph3 from the last variant would end its wait at once), then waits
            # up to 40 s for ph3; where the phantom is expected to end at DEBUG there is no ph3, so it waits 8 s
            write(p, "   x = ''\n   open 'zzsxf' to f else stop 'nofile'\n   delete f, 'ph1'\n   delete f, 'ph2'\n   delete f, 'ph3'\n"
                     "   execute 'PHANTOM NO.MSG RUN bp zzsxph' capturing o\n"
                     "   for w = 1 to %d\n      read q from f, 'ph3' then exit\n      sleep 1\n   next w\n"
                     "   sleep 1\n   for each id in 'ph1':@fm:'ph2':@fm:'ph3'\n"
                     "      read q from f, id then x := id:'=':q:'|' else x := id:' absent|'\n   next id\n   crt 'PH[':x:']'\nend\n"
                     % (40 if goes_on else 8))
            out = sess(box, "BASIC bp zzsxph DEBUGGING", "BASIC bp %s" % prog, "RUN bp %s" % prog)
            m = re.search(r"(?m)^PH\[(.*)\]\s*$", out)
            got = m.group(1) if m else None
            if goes_on:
                wanted = "ph1=started|ph2=%s|ph3=finished|" % want
            else:
                wanted = "ph1=started|ph2 absent|ph3 absent|"
            row("513 %s: the phantom %s" % (vlabel, "gets SYS.PROGRAM.NO_PDEBUG and carries on" if goes_on else "ends, as it always did"),
                got == wanted, ("got %r" % got) if m else out[-300:].replace("\n", " | "))
    finally:
        sess(box, *["DELETE.CATALOG %s" % nm for nm in catalogued])
        sess(box, "DELETE.FILE zzsxf")
        for p in made:
            if os.path.exists(p):
                os.remove(p)
        if os.path.isdir(os.path.join(sysd, "bp.out")):
            for f in os.listdir(os.path.join(sysd, "bp.out")):
                if f.startswith("zzsx"):
                    os.remove(os.path.join(sysd, "bp.out", f))

    say("\nsandbox-sysexc: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


main()
