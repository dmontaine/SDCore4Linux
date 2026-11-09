#!/usr/bin/env python3
#
# sandbox-runin.py - S.96, RUN.IN: the administrator runs ONE command from a fixed list in a registered account and is ALWAYS back.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-runin.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (SHORT path under /tmp).  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every
# row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist per keyset: stop it afterwards with sandbox-fromtree.py <dir> stop (this script stops it).
#
# START-HISTORY:
# 3 Nov 26 dm   Written for S.96 (owner, 2 Nov 2026: mechanism C, reserved for sdsys, a fixed command list).  The probes of that day (scratchpad probe_s96.py) showed
#               what the suite has to hold: the administrator's LOGTO into a locked-out account works, compile and catalogue work inside it, and after an ABORT the
#               session stays there for good (LOGTO sdsys is refused) - so the rows that matter most are the ones after an abort.
# END-HISTORY
#
# THE INSTRUMENT.  It uses sandbox-gates.py's helpers: the sandbox user plays SDSYS (SDTEST_ADMIN=1 makes a session an administrator; a session without it is an ordinary one).
# EVERY ROW THAT RUNS RUN.IN IS ONE SESSION that goes on to ask where it is: WHERE is a catalogued probe in SDSYS's VOC that prints the account name, @path and the six
# account-scoped switches, and SH pwd prints the working directory.  A row passes on RUN.IN's own words AND on that picture being equal to the BASELINE taken in a session
# that never ran RUN.IN.  The baseline is refused if it is not there (exit 2): without it every "back" row would compare nothing with nothing.  The evidence of what a command
# did is on the disk (the object file, the catalogue entry) or is the command's own success wording; a pattern that the failure also prints is not used.
#
# --mutant=NAME  makes one change to the SANDBOX's copy of cproc (or of basic) before it is compiled, and the rows that hold that part must go red:
#   no-safety-net  the abort branch no longer puts the session back          no-admin-check  the verb no longer asks for the administrator
#   no-logto-switches  LOGTO no longer loads the account's switches (F1 and F2)
#   no-nocatalog  run.in basic no longer gives NO.CATALOG                      basic-ignores-option  basic catalogues although NO.CATALOG is given (G1 and G2)

import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("sg", os.path.join(HERE, "sandbox-gates.py"))
sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg)

passed = failed = 0
BOX = SYS = None

# name: (the program of gpl.bp it edits, the text, what replaces it); the text must occur in that program exactly once
MUTANTS = {
    "no-safety-net": ("cproc", "         if ri.active then\n            gosub revert.account\n            display sysmsg(11242, ri.account)",
                      "         if 0 then\n            gosub revert.account\n            display sysmsg(11242, ri.account)"),
    "no-logto-switches": ("cproc", "   gosub load.account.switches   ;* the account-scoped switches, from the new account's own register record",
                          "   null   ;* the account-scoped switches, from the new account's own register record"),
    "no-nocatalog": ("cproc", "   if ri.cmd = 'basic' then ri.sentence := ' no.catalog'\n", ""),
    "basic-ignores-option": ("basic", "      if catalogue.name # '' and no.catalog then\n", "      if 0 then\n"),
    "no-admin-check": ("cproc", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      display sysmsg(2001)   ;* Command requires administrator privileges\n      void kernel(K$AUDIT, 'run.in refused reason=not the administrator')",
                       "   if 0 then\n      display sysmsg(2001)   ;* Command requires administrator privileges\n      void kernel(K$AUDIT, 'run.in refused reason=not the administrator')"),
}


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
    say("sandbox-runin: CANNOT RUN - " + msg)
    try:
        subprocess.run([sys.executable, sg.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    except Exception:
        pass
    sys.exit(2)


def put(path, lines):
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")


AUDIT_START = 0          # lines of the audit file that were there before this run: a rerun on a used sandbox must not count them


def audit_lines():
    p = os.path.join(SYS, "audit")
    with open(p, errors="replace") as f:
        return [ln.rstrip() for ln in f][AUDIT_START:]


def audit_has(pat):
    return [ln for ln in audit_lines() if re.search(pat, ln)]


def adm_t(cmds, timeout=90):
    """sandbox-gates.adm with a limit: a session that has not ended in `timeout` seconds is killed and says so in its output (a debugger that is still waiting for a key when the input has
    ended spins at 100% CPU; the first version of this suite waited 300 s for one).  Prints the real input as sg.sd does."""
    sg.say("    > [admin]  in sys: " + " | ".join(cmds))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen([sg.SD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=SYS, env=sg.env(True), text=True, errors="replace")
    note = ""
    try:
        out, _ = p.communicate(body, timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        note = "\nSUITE-TIMEOUT: the session was still running after %d s and was killed\n" % timeout
    out = sg.ANSI.sub("", out + note).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip() for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


def run(cmds, label=None):
    """One administrator session in SDSYS's directory: the commands, then ZZWHERE and SH pwd.  Returns (lines, where-lines, pwd)."""
    out = adm_t(list(cmds) + ["ZZWHERE", "SH pwd"])
    where = [ln for ln in out if ln.startswith("WHERE ")]
    pwd = out[-1] if out else ""
    return out, where, pwd


def main():
    global BOX, SYS
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-runin.py <dir> [--build] [--mutant=NAME]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    sg.BOX, sg.SYS, sg.SD = BOX, SYS, os.path.join(SYS, "bin", "sd")
    mutant = None
    for a in sys.argv[1:]:
        if a.startswith("--mutant="):
            mutant = a.split("=", 1)[1]
            if mutant not in MUTANTS:
                bail("unknown mutant %r (known: %s)" % (mutant, ", ".join(MUTANTS)))
    say("sandbox-runin: sandbox %s" % BOX)
    say("sandbox-runin: tree    %s" % os.path.dirname(HERE))
    say("sandbox-runin: user %s plays SDSYS; mutant: %s" % (sg.USER, mutant or "none"))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, sg.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-runin: built, bootstrap passed")
    elif not os.path.isfile(sg.SD):
        bail("%s holds no built sandbox (use --build)" % BOX)
    subprocess.run([sys.executable, sg.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # the sandbox's own cproc, with the one change of the mutant; prepare() then compiles it
    if mutant:
        prog, old, new = MUTANTS[mutant]
        path = os.path.join(SYS, "gpl.bp", prog)
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        if text.count(old) != 1:
            bail("the mutant %s does not match %s exactly once (%d)" % (mutant, prog, text.count(old)))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))
        if prog != "cproc":          # the build compiled the unmutated program: compile this one again (cproc is compiled by prepare())
            out = sg.adm(["BASIC gpl.bp " + prog], internal=True)
            if not sg.has(out, r"^Compiled 1 program\(s\) with no errors"):
                bail("the mutated %s did not compile:\n%s" % (prog, "\n".join(out[-8:])))

    say("\n--- preparation: an ordinary-session CPROC, the fixture accounts, the probes -------------------------------------")
    sg.EDIT_DEFAULT = None                    # the edit gates are blank = off: the accounts are locked out of their own files
    sg.prepare()
    accts = {}
    sg.EXTRA_FIXTURES["zzopt"] = ("no", "no")          # a third account, whose bp file holds a $BASIC.OPTIONS that asks for GLOBAL cataloguing (section G)
    for name in ("zzoff", "zzon", "zzopt"):
        accts[name] = sg.build_account(name)
    open(os.path.join(SYS, "audit"), "a").close()          # the kernel appends to the audit file and never creates it
    global AUDIT_START
    AUDIT_START = len(audit_lines())                       # (zero here: AUDIT_START is still 0) everything already in the file is not this run's

    # WHERE: a catalogued probe in SDSYS's VOC.  It prints everything RUN.IN has to give back.
    put(os.path.join(SYS, "gpl.bp", "zzwhere"), [
        "$internal", "program zzwhere", "$catalog $zzwhere", "$include keys.h", "$include int$keys.h",
        "   crt 'WHERE who=':@who:' path=':@path:' admin=':kernel(K$ADMINISTRATOR,-1):' sh=':kernel(K$SH,-1):' os=':kernel(K$OS.EXEC,-1):"
        "' sdacc=':kernel(K$SD.ACCOUNTS,-1):' net=':kernel(K$NET,-1):' shr=':kernel(K$SHARED.READ,-1):' shw=':kernel(K$SHARED.WRITE,-1)",
        "end"])
    # the VOC records: SDSYS gets WHERE; zzoff gets a hand-made RUN.IN (control A3: an ordinary account that writes the verb into its own VOC)
    put(os.path.join(SYS, "bp", "zzvoc"), [
        "$internal",
        "   openpath @sdsys:@ds:'voc' to v else crt 'VOC no sdsys voc' ; stop",
        "   write 'V':@fm:'CA':@fm:'$zzwhere' to v, 'zzwhere'",
        "   openpath '%s/voc' to v2 else crt 'VOC no zzoff voc' ; stop" % accts["zzoff"],
        "   write 'V':@fm:'IN':@fm:'42' to v2, 'run.in'",
        "   crt 'VOC done'", "end"])
    out = sg.adm(["BASIC gpl.bp zzwhere", "BASIC bp zzvoc", "RUN bp zzvoc"], internal=True)
    if not sg.has(out, r"^VOC done$") or not sg.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the WHERE probe or the VOC records were not made:\n" + "\n".join(out[-8:]))

    # the programs the commands work on, in each account's bp; and a data file with an I-type in zzoff
    for name in ("zzoff", "zzon"):
        put(os.path.join(accts[name], "bp", "zzprog"), ["program zzprog", "   crt 'ZZPROG ran: who=':@who:' path=':@path", "end"])
    put(os.path.join(accts["zzoff"], "bp", "zzabort"), ["program zzabort", "   crt 'ZZABORT ran: who=':@who",
                                                         "   abort 'zzabort aborting'", "end"])
    put(os.path.join(accts["zzoff"], "bp", "zznest"), ["program zznest", "   execute 'run.in zzoff basic bp zzprog'",
                                                        "   crt 'ZZNEST ended: who=':@who", "end"])
    put(os.path.join(accts["zzoff"], "bp", "zzmk"), ["program zzmk", "   open 'dict', 'cust' to d else crt 'MK no dict' ; stop",
                                                      "   write 'I':@fm:'@ID * 2':@fm:'':@fm:'Double':@fm:'10R':@fm:'S' on d, 'dbl'", "   crt 'MK done'", "end"])
    # section G's sources: a $CATALOG GLOBAL directive IN the program (zzoff), and none in the program but a CATALOG GLOBAL line in the $BASIC.OPTIONS record of the account's bp file (zzopt)
    put(os.path.join(accts["zzoff"], "bp", "zzglob"), ["program zzglob", "$catalog global no.query", "   crt 'ZZGLOB ran'", "end"])
    put(os.path.join(accts["zzopt"], "bp", "zzop"), ["program zzop", "   crt 'ZZOP ran'", "end"])
    put(os.path.join(accts["zzopt"], "bp", "$BASIC.OPTIONS"), ["X", "CATALOG GLOBAL NO.QUERY"])
    out = sg.adm(["LOGTO zzoff", "CREATE.FILE cust DYNAMIC", "BASIC bp zzmk", "RUN bp zzmk", "BASIC bp zzabort DEBUGGING", "BASIC bp zznest DEBUGGING"])
    if not sg.has(out, r"^MK done$"):
        bail("the fixture file cust was not made in zzoff:\n" + "\n".join(out[-10:]))
    sg.say("  [done] zzoff: cust with an I-type; the programs zzprog zzabort zznest (the last two compiled by the setup, not by RUN.IN)")

    # ------------------------------------------------------------------------------------------------------------------
    say("\n--- 0. the baseline: a session that never runs RUN.IN ------------------------------------------------------------")
    out, base_where, base_pwd = run(["WHO"])
    if len(base_where) != 1 or not re.match(r"^WHERE who=sdsys path=\S+ admin=1 ", base_where[0]) or base_pwd != SYS:
        bail("the baseline is not the administrator in SDSYS's directory: %r pwd %r\n%s" % (base_where, base_pwd, "\n".join(out[-6:])))
    say("  baseline: %s   pwd %s" % (base_where[0], base_pwd))
    row("0a: the baseline is the administrator, in sdsys, in its own directory", True)

    def back(where, pwd, name):
        row(name + " - and the session is back: WHERE and the working directory equal the baseline",
            where == base_where and pwd == base_pwd, "WHERE %r pwd %r" % (where, pwd))

    # --- A. controls: who may have the verb ---------------------------------------------------------------------------
    say("\n--- A. the verb is the administrator's -------------------------------------------------------------------------------")
    out = sg.plain("zzon", ["RUN.IN zzoff basic bp zzprog"])
    row("A1: an ordinary account has no RUN.IN (it is only in SDSYS's VOC)", sg.has(out, r"RUN\.IN is not in your VOC"), "output %r" % (out,))
    out = sg.plain("zzoff", ["RUN.IN zzon basic bp zzprog", "WHO"])
    row("A2: an ordinary session that wrote the verb into its own VOC is refused by the verb (administrator privileges), and stays in zzoff",
        sg.has(out, r"requires administrator privileges") and sg.has(out, r"\bzzoff\b") and not sg.has(out, r"Compiled"), "output %r" % (out,))
    row("A2b: ... and no run.in begin line was written for it", not audit_has(r"run\.in begin account=zzon"))

    # --- B. refusals: nothing changes ---------------------------------------------------------------------------------
    say("\n--- B. what the verb refuses: the words are checked before anything changes ----------------------------------------")
    out, w, p = run(["RUN.IN"])
    row("B1: no arguments says how the verb is used", sg.has(out, r"^run\.in account command name"), "output %r" % (out,))
    back(w, p, "B1")
    out, w, p = run(["RUN.IN zzoff basic bp"])
    row("B2: too few names says how the verb is used", sg.has(out, r"^run\.in account command name"), "output %r" % (out,))
    for word in ("sh", "logto", "delete", "list", "create.file", "execute", "run"):
        out, w, p = run(["RUN.IN zzoff %s bp zzprog" % word])
        row("B3-%s: the command %s is not on the list" % (word, word), sg.has(out, r"is not a command run\.in runs") and w == base_where, "output %r" % (out,))
    out, w, p = run(["RUN.IN sdsys basic bp zzprog"])
    row("B4: the administrator's own account is refused", sg.has(out, r"works in the other accounts") and not sg.has(out, r"Compiled"), "output %r" % (out,))
    back(w, p, "B4")
    out, w, p = run(["RUN.IN zzghost basic bp zzprog"])
    row("B5: an account with no register record is refused", sg.has(out, r"zzghost is not a registered account") and not sg.has(out, r"Compiled"), "output %r" % (out,))
    back(w, p, "B5")
    for acct in ("..", "../zzoff", "/tmp/x", "zz/off", ".zzoff"):
        out, w, p = run(["RUN.IN %s basic bp zzprog" % acct])
        row("B6-account %r: a path, a dot name or a slash is not an account name" % acct,
            sg.has(out, r"cannot be given to a command by run\.in") and not sg.has(out, r"Compiled") and w == base_where, "output %r" % (out,))
    for nm in ("a'b", 'a"b', "a$b", "-x", ".x", "local", "no.query", "no.catalog", "debugging", "a:b", "a|b", "a`b"):
        out, w, p = run(["RUN.IN zzoff basic bp %s" % nm])
        row("B6-name %r: not a name the verb gives to a command" % nm,
            sg.has(out, r"cannot be given to a command by run\.in") and not sg.has(out, r"Compiled") and w == base_where, "output %r" % (out,))
    for cmd in ("basic bp zzprog local", "catalog bp zzprog debugging", "basic bp zzprog debugging debugging", "decatalog zzprog local", "debug bp zzprog no.query",
                "basic bp zzprog global", "basic bp zzprog no.catalog", "catalog bp zzprog no.catalog"):
        out, w, p = run(["RUN.IN zzoff " + cmd])
        row("B7 %r: an option the command does not take, or one given twice" % cmd,
            sg.has(out, r"(is not an option run\.in gives to|cannot be given to a command by run\.in)") and not sg.has(out, r"Compiled") and w == base_where, "output %r" % (out,))
    out, w, p = run(["RUN.IN zzoff basic nofile zzprog"])
    row("B8: the file must be a file in the ACCOUNT's VOC", sg.has(out, r"nofile is not a file in account zzoff") and not sg.has(out, r"Compiled"), "output %r" % (out,))
    back(w, p, "B8 (the check is made inside the account)")

    # --- C. each command works inside the account ---------------------------------------------------------------------
    say("\n--- C. each command on the list, in the account, with the disk as the evidence ---------------------------------")
    objdir = os.path.join(accts["zzoff"], "bp.out")
    catdir = os.path.join(accts["zzoff"], "cat")
    row("C0: before: no object and no catalogue entry for zzprog in zzoff",
        not os.path.exists(os.path.join(objdir, "zzprog")) and not os.path.exists(os.path.join(catdir, "zzprog")))
    out, w, p = run(["RUN.IN zzoff basic bp zzprog"])
    row("C1: basic compiles the program in zzoff (its own success wording; the object file is in zzoff's bp.out)",
        sg.has(out, r"^Compiled 1 program\(s\) with no errors") and os.path.isfile(os.path.join(objdir, "zzprog")) and not sg.has(out, r"catalog directive was not run"), "output %r" % (out,))
    back(w, p, "C1")
    os.remove(os.path.join(objdir, "zzprog"))
    out, w, p = run(["RUN.IN zzoff basic bp zzprog debugging no.query"])
    row("C2: basic with debugging and no.query", sg.has(out, r"^Compiled 1 program\(s\) with no errors") and os.path.isfile(os.path.join(objdir, "zzprog")), "output %r" % (out,))
    back(w, p, "C2")
    out, w, p = run(["RUN.IN zzoff catalog bp zzprog"])
    row("C3: catalog puts the program in zzoff's PRIVATE catalogue (the message, and the file in zzoff/cat)",
        sg.has(out, r"^zzprog added to private catalog") and os.path.isfile(os.path.join(catdir, "zzprog")), "output %r" % (out,))
    back(w, p, "C3")
    existed = os.path.isfile(os.path.join(catdir, "zzprog"))
    out, w, p = run(["RUN.IN zzoff delete.catalog zzprog"])
    row("C4: delete.catalog takes the entry out (the file in zzoff/cat was there before and is gone)", existed and not os.path.exists(os.path.join(catdir, "zzprog")), "existed %s, output %r" % (existed, out))
    back(w, p, "C4")
    out, w, p = run(["RUN.IN zzoff basic bp zzprog", "RUN.IN zzoff catalog bp zzprog"])
    row("C5: two commands in one session both ran (the object and the catalogue entry are on the disk; the second run.in was not refused as nested)",
        os.path.isfile(os.path.join(objdir, "zzprog")) and os.path.isfile(os.path.join(catdir, "zzprog")) and not sg.has(out, r"already running"), "output %r" % (out,))
    back(w, p, "C5")
    # the private entry of C5 first: CATALOG asks "Program is also in private catalogue. Remove (y/<n>)?" otherwise, and the question takes the next input line
    out, w, p = run(["RUN.IN zzoff delete.catalog zzprog", "RUN.IN zzoff catalog bp zzprog local no.query"])
    row("C5b: catalog with local makes a LOCAL catalogue entry in zzoff (its own wording)", sg.has(out, r"^zzprog added to local catalog"), "output %r" % (out,))
    back(w, p, "C5b")
    out, w, p = run(["RUN.IN zzoff decatalog zzprog", "RUN.IN zzoff decatalog zzprog"])
    say("    (decatalog twice printed: %r)" % (out,))
    row("C5c: decatalog takes the local entry out: the first run does not say it is absent, the second does (so the first removed it)",
        len([ln for ln in out if "is not in the local catalog" in ln]) == 1 and not sg.has(out, r"already running"), "output %r" % (out,))
    back(w, p, "C5c")
    out, w, p = run(["RUN.IN zzoff basic bp zzprog debugging", "RUN.IN zzoff debug bp zzprog", "R"])
    row("C6: debug runs the program UNDER THE DEBUGGER, INSIDE zzoff (its output names the account and its directory)",
        sg.has(out, r"^ZZPROG ran: who=zzoff path=" + re.escape(accts["zzoff"]) + r"$"), "output %r" % (out,))
    back(w, p, "C6")
    out, w, p = run(["RUN.IN zzoff compile.dict cust dbl"])
    say("    (compile.dict printed: %r)" % (out,))
    row("C7: compile.dict ran in zzoff on an I-type of cust (its own line, Compiling dbl; nothing refused it)",
        sg.has(out, r"^Compiling dbl$") and not sg.has(out, r"(is not a file|is not a command|cannot be given|not found|not in your VOC|rror)"), "output %r" % (out,))
    back(w, p, "C7")
    out, w, p = run(["RUN.IN zzon basic bp zzprog"])
    row("C8: an account with SH and OS.EXECUTE on (zzon): compiles, and the SIX switches come back to SDSYS's own values (WHERE equals the baseline)",
        sg.has(out, r"^Compiled 1 program\(s\) with no errors") and os.path.isfile(os.path.join(accts["zzon"], "bp.out", "zzprog")), "output %r" % (out,))
    back(w, p, "C8")

    # --- D. back, whatever happens ------------------------------------------------------------------------------------
    say("\n--- D. the way back after an ABORT, a quit and a nested call: the reason the verb is built as it is -------------")
    out, w, p = run(["RUN.IN zzoff debug bp zzabort", "R"])
    row("D1: the program aborts INSIDE zzoff (its own line is printed)", sg.has(out, r"^ZZABORT ran: who=zzoff") and sg.has(out, r"zzabort aborting"), "output %r" % (out,))
    row("D1b: the safety net says so (the session is back in account zzoff)", sg.has(out, r"the command did not finish; the session is back in account zzoff"), "output %r" % (out,))
    back(w, p, "D1c: after the abort")
    out, w, p = run(["RUN.IN zzoff debug bp zzprog", "Q"])
    row("D2: the debugger's Q (quit) did not run the program on", not sg.has(out, r"^ZZPROG ran"), "output %r" % (out,))
    back(w, p, "D2: after Q")
    # the debugger stops again on the line after an EXECUTE (measured 3 Nov 26), so the program needs a second R to finish
    out, w, p = run(["RUN.IN zzoff debug bp zznest", "R", "R"])
    row("D3: a program in the account that calls RUN.IN is refused (it does not nest), and the program goes on to its last line",
        sg.has(out, r"run\.in is already running a command") and sg.has(out, r"^ZZNEST ended: who=zzoff") and not sg.has(out, r"SUITE-TIMEOUT"), "output %r" % (out,))
    back(w, p, "D3")
    out, w, p = run(["RUN.IN zzoff debug bp zzabort", "R", "RUN.IN zzon basic bp zzprog"])
    row("D4: after an aborted run a NEW run.in works (the flag was cleared)", sg.has(out, r"^Compiled 1 program\(s\) with no errors"), "output %r" % (out,))
    back(w, p, "D4")

    # --- G. BASIC through run.in is given NO.CATALOG ---------------------------------------------------------------------
    say("\n--- G. BASIC through run.in compiles WITHOUT cataloguing: a directive in an account's code cannot put it in a catalogue ----")
    gcat = os.path.join(SYS, "gcat")

    def in_gcat(nm):
        return os.path.isdir(gcat) and any(nm in f.lower() for f in os.listdir(gcat))

    def compiled(o):
        return sg.has(o, r"^Compiled 1 program\(s\) with no errors")

    row("G0: before: zzglob and zzop are in no catalogue (the global one, or zzoff's private one)",
        not in_gcat("zzglob") and not in_gcat("zzop") and not os.path.exists(os.path.join(catdir, "zzglob")), "gcat %r" % (sorted(os.listdir(gcat)) if os.path.isdir(gcat) else None,))
    out, w, p = run(["RUN.IN zzoff basic bp zzglob"])
    row("G1: a '$catalog global' directive in the SOURCE: the program compiles, the compile says the directive was not run, and nothing is catalogued (not globally, not privately)",
        compiled(out) and sg.has(out, r"^zzglob compiled; its catalog directive was not run \(no\.catalog\)") and os.path.isfile(os.path.join(objdir, "zzglob"))
        and not in_gcat("zzglob") and not os.path.exists(os.path.join(catdir, "zzglob")), "output %r" % (out,))
    back(w, p, "G1")
    out, w, p = run(["RUN.IN zzopt basic bp zzop"])
    row("G2: a 'CATALOG GLOBAL' line in the $BASIC.OPTIONS record of the account's bp file (no directive in the program at all): the same",
        compiled(out) and sg.has(out, r"^zzop compiled; its catalog directive was not run \(no\.catalog\)") and not in_gcat("zzop"), "output %r" % (out,))
    back(w, p, "G2")
    # THE CONTROLS: the same two sources compiled by a plain BASIC after a LOGTO DO reach the global catalogue, so the rows above could have failed
    out = sg.adm(["LOGTO zzoff", "BASIC bp zzglob"])
    row("G3 (control): the source of G1 compiled by a plain BASIC is put in the GLOBAL catalogue", compiled(out) and in_gcat("zzglob"), "output %r, gcat %r" % (out, sorted(os.listdir(gcat)) if os.path.isdir(gcat) else None))
    out = sg.adm(["LOGTO zzopt", "BASIC bp zzop"])
    row("G4 (control): the source of G2 compiled by a plain BASIC is put in the GLOBAL catalogue", compiled(out) and in_gcat("zzop"), "output %r" % (out,))

    # --- F. LOGTO itself: its switch loading is the routine RUN.IN shares ------------------------------------------------
    say("\n--- F. LOGTO still loads the account's switches (they are one routine now, shared with RUN.IN) ----------------------")
    out = sg.adm(["LOGTO zzon", "ZZKF"])
    f = sg.flags(out)
    row("F1: LOGTO zzon (SH and OS.EXECUTE on in its register record): the administrator flag stays and SH and OS.EXECUTE are on", f is not None and f[:3] == ("1", "1", "1"), "KFLAGS %r" % (f,))
    out = sg.adm(["LOGTO zzoff", "ZZKF"])
    f = sg.flags(out)
    row("F2: LOGTO zzoff (both off): the administrator flag stays and SH and OS.EXECUTE are off - the second load replaced the first", f is not None and f[:3] == ("1", "0", "0"), "KFLAGS %r" % (f,))

    # --- E. the audit trail --------------------------------------------------------------------------------------------
    say("\n--- E. audit lines ---------------------------------------------------------------------------------------------------")
    begins = audit_has(r"\brun\.in begin account=")
    ends = audit_has(r"\brun\.in end account=")
    reverts = audit_has(r"\brun\.in revert account=zzoff reason=abort")
    say("    audit: %d begin, %d end, %d revert-after-abort, %d refused" % (len(begins), len(ends), len(reverts), len(audit_has(r"\brun\.in refused"))))
    row("E1: a begin line names the account and the command built from the checked words",
        bool(audit_has(r"run\.in begin account=zzoff command=basic bp zzprog no\.catalog$")), "begin lines %r" % (begins[:3],))
    row("E2: every begin has its end or its revert (nothing is left open)", len(begins) > 0 and len(begins) == len(ends) + len(reverts), "%d / %d / %d" % (len(begins), len(ends), len(reverts)))
    row("E3: the abort wrote a revert line", len(reverts) >= 2, "revert lines %r" % (reverts,))
    row("E4: the refusals were written (command not on the list, not registered, the administrator account, a word the command does not take, nested)",
        all(audit_has(p) for p in (r"run\.in refused account=zzoff reason=command not on the list", r"run\.in refused account=zzghost reason=not registered",
                                    r"run\.in refused account=sdsys reason=the administrator account", r"run\.in refused account=zzoff reason=a word the command does not take",
                                    r"run\.in refused reason=nested")))

    subprocess.run([sys.executable, sg.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-runin: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
