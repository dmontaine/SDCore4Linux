#!/usr/bin/env python3
#
# sandbox-qm4def.py - two defects the QM4 evaluation noticed (18 Oct 2026), each REPRODUCED in a sandbox before it was fixed, through ORDINARY sessions
#                     on a private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-qm4def.py <dir> [--build]
#
#   1. A user conversion code ("U" and a name) in OCONV / ICONV called the catalogued subroutine of that name through _oconv / _iconv, which are
#      $internal: a name beginning with $ (a program only internal code may CALL) was reached by an ordinary program.
#   2. A print unit's SPOOLER string (SETPTR ... SPOOLER, which any program can set) is the start of a shell command handed to system(): an account
#      with SH and OS.EXECUTE off ran "touch ...; true".  Now used only by a session that holds the OS access gate.
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.  The first rows prove the session is NOT an administrator.  Stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 18 Oct 26 dm  Written.  The old code failed rows P1a, P1b and P2a (observed: the internal subroutine printed its line, the marker file was made).
# END-HISTORY
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

MARK = "/tmp/zz_qm4def_spool_marker"
passed = failed = 0


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


def gone():
    if os.path.exists(MARK):
        os.remove(MARK)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        g.bail("usage: sandbox-qm4def.py <dir> [--build]")
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    say("sandbox-qm4def: sandbox %s" % g.BOX)
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            g.bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            g.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-qm4def: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        g.bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: an ordinary account (no SH, no OS.EXECUTE; the edit gates on so it can compile), one with OS.EXECUTE ---")
    g.prepare()
    g.EXTRA_FIXTURES["zzq"] = ("no", "no")
    g.EXTRA_FIXTURES["zzqo"] = ("no", "yes")
    paths = {}
    for acct, osx in (("zzq", "no"), ("zzqo", "yes")):
        p = g.build_account(acct)
        g.reg_write(acct, [p, "", g.GROUP, "", "", "", "no", osx, "", "yes", "yes", "yes", "", ""])
        os.makedirs(os.path.join(p, "$hold"), exist_ok=True)
        paths[acct] = p
    f = g.flags(g.plain("zzq", ["ZZKF"]))
    row("CONTROL: a plain session in zzq is not an administrator and has neither SH nor OS.EXECUTE (admin, sh, os = 0 0 0)", f is not None and f[:3] == ("0", "0", "0"), repr(f))
    if f is None or f[:3] != ("0", "0", "0"):
        g.bail("the plain session is not ordinary: every row below would be meaningless")
    f = g.flags(g.plain("zzqo", ["ZZKF"]))
    row("CONTROL: a plain session in zzqo holds OS.EXECUTE only (admin, sh, os = 0 0 1)", f is not None and f[:3] == ("0", "0", "1"), repr(f))

    # ---- 1. conversion codes -----------------------------------------------------------------------------------------------------------------
    say("\n--- 1. a user conversion code reaches only subroutines an ordinary program may CALL ---")
    g.put(os.path.join(g.SYS, "gpl.bp", "zzqint"), "$internal\nsubroutine zzqint(result, src, state, flag)\n$catalog $zzqint\n   crt 'P1 INTERNAL SUBROUTINE RAN'\n   result = 'viaint'\n   state = 0\n   return\nend\n")
    out = g.adm(["BASIC gpl.bp zzqint"], internal=True)
    row("SETUP: the $internal global subroutine $zzqint compiles and is catalogued", g.has(out, r"^Compiled 1 program\(s\) with no errors") and any("added to global catalogue" in x for x in out), repr(out[-4:]))
    g.put(os.path.join(paths["zzq"], "bp", "zzqconv"), "subroutine zzqconv(result, src, state, flag)\n   result = 'conv:' : src\n   state = 0\n   return\nend\n")
    g.put(os.path.join(paths["zzq"], "bp", "zzqp1"), "\n".join([
        "   x = oconv('abc', 'U$zzqint')", "   crt 'P1 oconv ':x:' status ':status()",
        "   z = iconv('abc', 'U$zzqint')", "   crt 'P1 iconv ':z:' status ':status()",
        "   c = oconv('abc', 'Uzzqconv')", "   crt 'P1 own conversion ':c:' status ':status()", "end", ""]))
    out = g.plain("zzq", ["BASIC bp zzqconv zzqp1", "CATALOG bp zzqconv", "RUN bp zzqp1"])
    ok_c = g.has(out, r"^Compiled 2 program\(s\) with no errors")
    row("SETUP: the user's own conversion subroutine and the probe compile in the ordinary account", ok_c, repr(out[:8]))
    row("P1a: OCONV(x, 'U$zzqint') from an ORDINARY program does not run the internal subroutine", not any("P1 INTERNAL SUBROUTINE RAN" in x for x in out), repr([x for x in out if x.startswith("P1")]))
    row("P1b: ...and says so as it does for a name that is not catalogued (status 2, the source returned)", "P1 oconv abc status 2" in out, repr([x for x in out if x.startswith("P1 oconv")]))
    il = [x for x in out if x.startswith("P1 iconv")]
    row("P1c: ICONV(x, 'U$zzqint') likewise: not run, status 2 (the kernel gives ICONV a null string for a conversion it does not know)", len(il) == 1 and il[0].endswith("status 2") and "viaint" not in il[0], repr(il))
    row("P1d: CONTROL: the user's own catalogued conversion subroutine still works (OCONV(x, 'Uzzqconv'))", "P1 own conversion conv:abc status 0" in out, repr([x for x in out if x.startswith("P1 own")]))

    # ---- 2. the spooler string ---------------------------------------------------------------------------------------------------------------
    say("\n--- 2. a print unit's SPOOLER string is a shell command: only a session with the OS access gate may set the one that is run ---")
    prog = "   print on 4 'hello'\n   printer close on 4\n   crt 'P2 printed and closed'\nend\n"
    cmd = 'SETPTR 4,80,60,0,0,1,SPOOLER "touch %s; true"' % MARK
    for acct, want, why in (("zzq", False, "an ordinary account (SH and OS.EXECUTE off)"), ("zzqo", True, "an account with OS.EXECUTE")):
        g.put(os.path.join(paths[acct], "bp", "zzqp2"), prog)
        gone()
        out = g.plain(acct, [cmd, "y", "BASIC bp zzqp2", "RUN bp zzqp2"])
        printed = any(x == "P2 printed and closed" for x in out)
        made = os.path.exists(MARK)
        row("P2%s: %s sets the spooler to a command and prints: the program ran to its end" % ("a" if acct == "zzq" else "c", why), printed, repr(out[-6:]))
        row("P2%s: ...the command %s run (the marker file %s)" % ("a" if acct == "zzq" else "c", "WAS" if want else "was NOT", "exists" if want else "does not exist"), made == want, "marker exists=%s" % made)
        gone()
    g.put(os.path.join(g.SYS, "bp", "zzqp2"), prog)
    out = g.adm([cmd, "y", "BASIC bp zzqp2", "RUN bp zzqp2"])
    row("P2d: the administrator's spooler string is run (the marker file exists): the gate lets the one who has it through", os.path.exists(MARK), repr(out[-5:]))
    gone()

    say("\n--- summary " + "-" * 100)
    say("sandbox-qm4def: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
