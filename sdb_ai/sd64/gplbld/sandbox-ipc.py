#!/usr/bin/env python3
#
# sandbox-ipc.py - W.11 F10 (security-model evaluation, 24 Oct 2026): what a phantom takes from the file $ipc.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ipc.py <dir> [--build] [--mutants]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.  --mutants then breaks the sandbox's OWN copy of CPROC, PHANTOM and !IPC_SEAL eight ways, one at a time, runs the rows
# each break must turn red, and puts the programs back.
#
# START-HISTORY:
# 26 Oct 26 dm  New.  PHANTOM seals the records it leaves in $ipc (Xn, Dn, Ln) with a secret it hands the new process in its environment; CPROC runs, stacks or
#               sets nothing from them unless the seal checks (gpl.bp/phantom, cproc read.phantom.cargo, ipc_seal; op_kernel.c K_PHANTOM_NONCE).
# END-HISTORY
#
# WHAT THIS CAN AND CANNOT SAY.  The sandbox has ONE operating-system user.  The records a stranger could write are therefore simulated: a probe
# (gpl.bp/zzfake) plays PHANTOM, starts a real phantom, and writes the records itself - once as PHANTOM would (the control), then each time with one thing wrong:
# a command changed after it was sealed, a seal made with a secret the phantom was not given, no seal at all, a DATA record or a log file name the parent never
# passed, option flags changed, a record for a phantom started with no secret, no Xn record, and one phantom's valid record copied to another.  The phantom's own
# answer is read from the DISK (the record its command writes into the file zzout), from the audit trail, and from the message it sends its parent.  That the
# environment of a process can be read only by the same operating-system user is the operating system's rule and is NOT tested here: it needs a second user (the VM).
#
#   A  the legitimate flows are as before: PHANTOM runs its command; DATA, LOG and an inherited option arrive; the secret is not left in the phantom's
#      environment and is not in the parent's; the profiler's display (it reads $ipc) still works; no refusal was audited
#   B  the control (a probe that does what PHANTOM does) runs the command; each wrong record does NOT, is refused with its own message and audit line, and the
#      three records are taken out of $ipc whether or not they passed

import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
_spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(q3)
say, has, tag, put = q3.say, q3.has, q3.tag, q3.put

passed = failed = 0
RES = {}
QUIET = False
REFUSAL = r"not from the process that started it, nothing was run"
NORMAL = r"Normal termination"

# programs an ordinary account can compile and run (also put in SDSYS's bp: the phantoms run there)
ORDINARY = {
    # what a phantom's command writes: one record per phantom user number and tag, in the file zzout
    "zzmark": ("   tag = field(@sentence, ' ', 4)\n   open 'zzout' to f else stop 'no zzout'\n"
               "   write 'ran' to f, 'U':@userno:'.':tag\nend\n"),
    # what a CHANGED command would write: a different record, so that a forged command is told from the honest one
    "zzmarkx": ("   tag = field(@sentence, ' ', 4)\n   open 'zzout' to f else stop 'no zzout'\n"
                "   write 'ran' to f, 'F':@userno:'.':tag\nend\n"),
    "zzdata": ("   tag = field(@sentence, ' ', 4)\n   open 'zzout' to f else stop 'no zzout'\n   input a\n   input b\n"
               "   write a:'/':b to f, 'I':@userno:'.':tag\nend\n"),
    "zzshow": ("   open 'zzout' to f else stop 'no zzout'\n   select f to 9\n   loop\n      readnext id from 9 else exit\n"
               "      read r from f, id else r = ''\n      crt 'REC[':id:'][':convert(@fm:@vm, '|^', r):']'\n   repeat\n   crt 'SHOWDONE'\nend\n"),
    "zzclr": "   open 'zzout' to f else stop 'no zzout'\n   clearfile f\n   crt 'CLRDONE'\nend\n",
    # a program for the profiler to watch (the profiler keeps its table in $ipc)
    "zzprfm": ("   open 'zzprf' to f else crt 'PRF open failed' ; stop\n   write 'a' to f, 'k1'\n   read r from f, 'k1' else null\n"
               "   read r from f, 'k1' else null\n   delete f, 'k1'\n   crt 'PRFDONE'\nend\n"),
}

# $internal programs, in SDSYS's gpl.bp (a program that starts a phantom, or asks the kernel, must be internal)
INTERNAL = {
    "zzopt": ("$internal\n$include int$keys.h\n   tag = field(@sentence, ' ', 4)\n   open 'zzout' to f else stop 'no zzout'\n"
              "   write option(OPT.INHERIT.OWNERSHIP) to f, 'O':@userno:'.':tag\nend\n"),
    "zzenv": ("$internal\n$include int$keys.h\n   tag = field(@sentence, ' ', 4)\n   open 'zzout' to f else stop 'no zzout'\n"
              "   write len(env('SD_PHANTOM_NONCE')):'/':len(kernel(K$PHANTOM.NONCE, 'G')) to f, 'E':@userno:'.':tag\nend\n"),
    # RUN gpl.bp zzstart <mode> <the PHANTOM command>: the verb itself, from a session that is not a phantom
    "zzstart": ("$internal\n$include int$keys.h\n   mode = field(@sentence, ' ', 4)\n   ph = field(@sentence, ' ', 5, 99999)\n"
                "   if mode = 'data' then\n      data 'alpha'\n      data 'beta'\n   end\n"
                "   if mode = 'optonly' then execute 'OPTION INHERIT.OWNERSHIP' capturing j\n"
                "   execute ph capturing j\n   crt 'UID[':@system.return.code:']'\n"
                "   crt 'PARENT[':len(env('SD_PHANTOM_NONCE')):'][':len(kernel(K$PHANTOM.NONCE, 'G')):']'\nend\n"),
    # RUN gpl.bp zzfake <variant>: does what the PHANTOM verb does, writing the records itself.  'ok' is exactly what PHANTOM writes; the others have one thing wrong
    "zzfake": ("$internal\n$include syscom.h\n$include keys.h\n$include int$keys.h\n$include err.h\n"
               "deffun ipc_seal(sl.mode, sl.key, sl.seal, sl.opts, sl.cmd, sl.data, sl.log) calling '!ipc_seal'\n"
               "   variant = field(@sentence, ' ', 4)\n"
               "   good.cmd = 'RUN bp zzmark ' : variant\n   bad.cmd = 'RUN bp zzmarkx ' : variant\n"
               "   secret = SDEXT('24', @TRUE, SD_RANDBYTES)\n   stranger = SDEXT('24', @TRUE, SD_RANDBYTES)\n"
               "   stage = @true\n   use.key = secret\n   w.cmd = good.cmd\n   w.opts = ''\n   w.d = ''\n   w.l = ''\n   no.seal = @false\n   skip.x = @false\n"
               "   n.exp = 1\n"
               "   begin case\n"
               "      case variant = 'ok'\n         null\n"
               "      case variant = 'cmdalt'\n         w.cmd = bad.cmd\n"
               "      case variant = 'badkey'\n         use.key = stranger\n"
               "      case variant = 'noseal'\n         no.seal = @true\n"
               "      case variant = 'dadd'\n         w.d = 'FORGED1':@fm:'FORGED2'\n"
               "      case variant = 'ladd'\n         w.l = 'zzlogdir'\n"
               "      case variant = 'optalt'\n         w.opts = str('1', 100)\n"
               "      case variant = 'nox'\n         skip.x = @true\n         w.d = 'FORGED1'\n"
               "      case variant = 'nostage'\n         stage = @false\n"
               "      case variant = 'replay'\n         n.exp = 2\n"
               "      case 1\n         crt 'FAKE bad variant ':variant\n         stop\n"
               "   end case\n"
               "   seal = ipc_seal('make', use.key, '', '', good.cmd, '', '')\n"
               "   uid2 = 0\n   saw = -1\n"
               "   filelock ipc.f\n"
               "   if stage then void kernel(K$PHANTOM.NONCE, 'S':secret)\n"
               "   uid = phantom()\n"
               "   if uid = 0 then\n      fileunlock ipc.f\n      crt 'FAKE no phantom'\n      stop\n   end\n"
               "   if variant = 'replay' then\n"
               "      rec1 = seal:@fm:'':@fm:good.cmd\n      write rec1 to ipc.f, 'X':uid\n"
               "      void kernel(K$PHANTOM.NONCE, 'S':stranger)\n      uid2 = phantom()\n"
               "      if uid2 # 0 then write rec1 to ipc.f, 'X':uid2\n"
               "      saw = len(rec1)\n"
               "   end else\n"
               "      if not(skip.x) then\n"
               "         if no.seal then\n            write w.opts:@fm:w.cmd to ipc.f, 'X':uid\n"
               "         end else\n            write seal:@fm:w.opts:@fm:w.cmd to ipc.f, 'X':uid\n         end\n"
               "         read back from ipc.f, 'X':uid then saw = len(back) else saw = -1\n"
               "      end\n"
               "      if w.d # '' then write w.d to ipc.f, 'D':uid\n"
               "      if w.l # '' then write w.l to ipc.f, 'L':uid\n"
               "   end\n"
               "   fileunlock ipc.f\n"
               "   crt 'FAKE[':variant:'][':uid:'][':uid2:'][':saw:']'\n"
               "   m = ''\n"
               "   for t = 1 to 200\n      read m from ipc.f, 'M':@userno else m = ''\n      if dcount(m, @fm) >= n.exp then exit\n      nap 200\n   next t\n"
               "   crt 'MSG[':convert(@fm, '|', m):']'\n   delete ipc.f, 'M':@userno\n"
               "   remain = ''\n   for u = 1 to 2\n      id = if u = 1 then uid else uid2\n      if id # 0 then\n"
               "         read z from ipc.f, 'X':id then remain := 'X':id:' '\n         read z from ipc.f, 'D':id then remain := 'D':id:' '\n"
               "         read z from ipc.f, 'L':id then remain := 'L':id:' '\n      end\n   next u\n"
               "   crt 'LEFT[':remain:']'\nend\n"),
}


def row(rid, name, ok, detail=""):
    global passed, failed
    RES[rid] = bool(ok)
    if QUIET:
        return
    if ok:
        passed += 1
        say("  [PASS] %s %s" % (rid, name))
    else:
        failed += 1
        say("  [FAIL] %s %s%s" % (rid, name, ("   <- " + detail) if detail else ""))


def audit_off():
    """Size of the sandbox's audit file.  SD APPENDS to <sys>/audit and never creates it, so without one every audit line is dropped: it is made, empty, when it is missing."""
    path = os.path.join(q3.SYS, "audit")
    if not os.path.exists(path):
        open(path, "ab").close()
    return os.path.getsize(path)


def audit_new(off):
    try:
        with open(os.path.join(q3.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def records():
    """The records of zzout read by a session of its own; None when the session did not get to its end (a row that needs it then FAILS)."""
    out = q3.adm(["RUN bp zzshow"])
    if not has(out, r"^SHOWDONE$"):
        return None
    d = {}
    for t in tag(out, "REC"):
        m = re.match(r"^(.*?)\]\[(.*)$", t)
        if m:
            d[m.group(1)] = m.group(2)
    return d


WAIT = 40       # seconds a row waits for a phantom's record; the mutant runs wait less


def wait_rec(rid, seconds=None):
    end = time.time() + (seconds or WAIT)
    d = None
    while time.time() < end:
        d = records()
        if d is not None and rid in d:
            return d[rid]
        time.sleep(0.5)
    return None


def start(mode, command):
    """The PHANTOM verb from a session that is not a phantom; (user number or None, output)."""
    out = q3.adm(["RUN gpl.bp zzstart %s %s" % (mode, command)], internal=True)
    u = (tag(out, "UID") or [""])[0]
    return (u if u.isdigit() and int(u) > 0 else None), out


def fake(variant):
    """One run of the probe.  Returns what it printed, the records of zzout and what the audit trail gained."""
    q3.adm(["RUN bp zzclr"])
    a0 = audit_off()
    out = q3.adm(["RUN gpl.bp zzfake " + variant], internal=True)
    recs = records()
    new = audit_new(a0) or ""
    parts = (tag(out, "FAKE") or [""])[0].split("][")
    r = {"out": out, "recs": recs, "audit": new, "variant": variant}
    if len(parts) == 4 and parts[0] == variant and parts[1].isdigit():
        r.update(uid=parts[1], uid2=parts[2], saw=int(parts[3]) if re.match(r"^-?\d+$", parts[3]) else None)
    else:
        r.update(uid=None, uid2="0", saw=None)
    r["msg"] = (tag(out, "MSG") or [None])[0]
    r["left"] = (tag(out, "LEFT") or [None])[0]
    return r


def refused_audit(audit, uid):
    return re.search(r"phantom refused phantom=%s reason=start-up records not from the process that started it" % re.escape(str(uid)), audit) is not None


def rows_variant(v, expect_saw=True):
    """The rows of one wrong record (all but 'ok' and 'replay'): nothing it asked for ran, it was refused with its own message and audit line, nothing is left in $ipc."""
    r = fake(v)
    u, recs = r["uid"], r["recs"]
    detail = repr((r["out"][-5:], recs))
    row(v + ".0", "%s: the probe started a phantom and the instrument can see (%s)" % (v, "the record it wrote read back" if expect_saw else "no Xn record written"),
        u is not None and recs is not None and (r["saw"] is not None and (r["saw"] > 0) == expect_saw), detail)
    row(v + ".a", "%s: NOTHING ran - neither the honest command's record nor the changed command's is on the disk" % v,
        u is not None and recs is not None and not any(k.startswith(("U%s." % u, "F%s." % u)) for k in recs) and not any(k.startswith(("U", "F")) and k.endswith("." + v) for k in recs), detail)
    row(v + ".b", "%s: the phantom told its parent the records were refused (and did not say it ended normally)" % v,
        r["msg"] is not None and re.search(REFUSAL, r["msg"]) is not None and not re.search(NORMAL, r["msg"]), repr(r["msg"]))
    row(v + ".c", "%s: the audit trail has 'phantom refused' for that phantom" % v, u is not None and refused_audit(r["audit"], u), repr(r["audit"][-200:]))
    row(v + ".d", "%s: the Xn, Dn and Ln records are no longer in $ipc" % v, r["left"] == "", repr(r["left"]))
    return r


def rows_control():
    r = fake("ok")
    u, recs = r["uid"], r["recs"]
    detail = repr((r["out"][-5:], recs))
    row("ok.0", "CONTROL: the probe started a phantom and wrote the records as PHANTOM does (it read its Xn record back)", u is not None and r["saw"] is not None and r["saw"] > 0, detail)
    row("ok.a", "CONTROL: the command in the honest record ran - its record is on the disk", u is not None and recs is not None and recs.get("U%s.ok" % u) == "ran", detail)
    row("ok.b", "CONTROL: the phantom ended normally and said so to its parent", r["msg"] is not None and re.search(NORMAL, r["msg"]) is not None and not re.search(REFUSAL, r["msg"]), repr(r["msg"]))
    row("ok.c", "CONTROL: nothing was audited as refused for it", u is not None and not refused_audit(r["audit"], u) and "phantom refused" not in r["audit"], repr(r["audit"][-200:]))
    row("ok.d", "CONTROL: the three records are no longer in $ipc", r["left"] == "", repr(r["left"]))
    return r


def rows_replay():
    r = fake("replay")
    u1, u2, recs = r["uid"], r["uid2"], r["recs"]
    detail = repr((r["out"][-5:], recs))
    row("replay.0", "replay: two phantoms started, the first one's sealed record copied to the second", u1 is not None and u2 not in (None, "0") and u1 != u2 and r["saw"] is not None and r["saw"] > 0, detail)
    row("replay.a", "replay: the first phantom ran its command, the second did NOT (it has a secret of its own)",
        recs is not None and recs.get("U%s.replay" % u1) == "ran" and ("U%s.replay" % u2) not in recs, detail)
    row("replay.b", "replay: one of the two messages to the parent is the refusal and one is a normal ending",
        r["msg"] is not None and len(re.findall(REFUSAL, r["msg"])) == 1 and len(re.findall(NORMAL, r["msg"])) == 1, repr(r["msg"]))
    row("replay.c", "replay: the audit trail refuses the second phantom and not the first",
        refused_audit(r["audit"], u2) and not refused_audit(r["audit"], u1), repr(r["audit"][-300:]))
    return r


def rows_legit(only=None):
    def want(k):
        return only is None or k in only
    a0 = audit_off()
    if want("A1"):
        u, out = start("plain", "PHANTOM NO.MSG RUN bp zzmark A1")
        got = wait_rec("U%s.A1" % u) if u else None
        row("A1", "PHANTOM runs its command in a new process: the record the command wrote is on the disk (user %s)" % u, got == "ran", repr(out[-4:]))
    if want("A2"):
        u, out = start("data", "PHANTOM NO.MSG DATA RUN bp zzdata A2")
        got = wait_rec("I%s.A2" % u) if u else None
        row("A2", "PHANTOM DATA: the phantom read the two lines the parent queued (alpha, beta)", got == "alpha/beta", repr((got, out[-4:])))
    if want("A3"):
        q3.adm(["CREATE.FILE zzlogdir DIRECTORY"])
        t0 = time.time() - 2
        u, out = start("plain", "PHANTOM NO.MSG LOG zzlogdir RUN bp zzmark A3")
        got = wait_rec("U%s.A3" % u) if u else None
        found = []
        for _ in range(40):
            d_ = os.path.join(q3.SYS, "zzlogdir")
            found = [n for n in os.listdir(d_) if n.lower().startswith("ph%s_" % u) and os.path.getmtime(os.path.join(d_, n)) >= t0] if u else []
            if found:
                break
            time.sleep(0.5)
        row("A3", "PHANTOM LOG: the phantom ran and its COMO log is a file of the directory file zzlogdir (%s)" % found, got == "ran" and len(found) == 1, repr(out[-4:]))
    if want("A4"):
        # 27 Oct 26, S.87 batch 16: OPTION INHERIT is gone, so A4a ("the phantom has the option the parent set") is gone; A4b stays as the rule itself.
        u, out = start("optonly", "PHANTOM NO.MSG RUN gpl.bp zzopt A4b")
        got = wait_rec("O%s.A4b" % u) if u else None
        row("A4b", "a phantom starts with every option off: the parent's INHERIT.OWNERSHIP does not reach it", got == "0", repr((got, out[-4:])))
    if want("A5"):
        u, out = start("plain", "PHANTOM NO.MSG RUN gpl.bp zzenv A5")
        got = wait_rec("E%s.A5" % u) if u else None
        row("A5a", "the phantom was given a secret (32 characters, K$PHANTOM.NONCE 'G') and it is NOT left in its environment", got == "0/32", repr((got, out[-4:])))
        row("A5b", "the starting session holds no SD_PHANTOM_NONCE in its environment and is not given a secret ('G' is null for a session that is not a phantom)",
            has(out, r"^PARENT\[0\]\[0\]$"), repr(out[-4:]))
    if want("A7"):
        new = audit_new(a0) or ""
        row("A7", "no start-up record was refused in all of the above (the audit trail has no 'phantom refused')", "phantom refused" not in new, repr(new[-300:]))


def rows_profiler():
    out = q3.plain("zzaa", ["CREATE.FILE zzprf DYNAMIC", "PROFILER ON", "RUN bp zzprfm", "PROFILER OFF", "PROFILER DISPLAY", "Q"])
    m = next((re.match(r"^Profiler off for user (\d+): (\d+) events in (\d+) entries$", l) for l in out if l.startswith("Profiler off for user")), None)
    row("A6a", "the profiler (it keeps its table in $ipc) stopped and reported events", m is not None and int(m.group(2)) > 0 and int(m.group(3)) > 0, repr(out[:12]))
    types = [re.sub(r"^\s*\d+\s+\d+\s+", "", l).strip() for l in out if re.match(r"^\s*\d+\s+\d+\s+[A-Z]+\s*$", l)]
    row("A6b", "PROFILER DISPLAY lists the event types of what it recorded (Event types: %s)" % types,
        has(out, r"^Event types$") and "READ" in types and "WRITE" in types and "OPEN" in types, repr(out[-14:]))


# ----- the mutants (the sandbox's own copies of three programs) -------------------------------------------------------------------------------------------------
# (name, program, [(old, new)], what to run, the rows that must turn red)
MUTANTS = [
    ("cproc-never-refuses", "cproc", [("if not(ipc_seal('check',", "if 0 and not(ipc_seal('check',")],
     {"v": ["cmdalt", "badkey", "dadd", "ladd", "optalt", "nostage", "noseal"], "replay": True},
     ["cmdalt.a", "badkey.a", "dadd.a", "ladd.a", "optalt.a", "nostage.a", "replay.a", "noseal.b"]),
    ("seal-constant-key", "ipc_seal", [("mac = SDEXT(nonce : @FM : signed,", "mac = SDEXT('QUJDREVGR0hJSktMTU5PUFFSU1RVVldY' : @FM : signed,")],
     {"v": ["badkey", "cmdalt"], "replay": True}, ["badkey.a", "replay.a"]),
    ("seal-ignores-data", "ipc_seal", [("oconv(dq, 'MX0C')", "''")], {"v": ["dadd"]}, ["dadd.a"]),
    ("seal-ignores-options", "ipc_seal", [("oconv(opt, 'MX0C')", "''")], {"v": ["optalt"]}, ["optalt.a"]),
    ("seal-ignores-logfile", "ipc_seal", [("oconv(logf, 'MX0C')", "''")], {"v": ["ladd"]}, ["ladd.a"]),
    ("phantom-gives-no-secret", "phantom", [("if kernel(K$PHANTOM.NONCE, 'S':nonce) # 1 then", "if 0 then")], {"legit": ["A1", "A2", "A5"]}, ["A1", "A2", "A5a"]),
    ("no-record-is-accepted", "cproc", [("   if ph.rec = '' then\n      ph.refused = @true\n   end else", "   if ph.rec = '' then\n      null\n   end else")],
     {"v": ["nox"]}, ["nox.b"]),
    ("refusal-runs-the-command", "cproc", [("      phantom.command = ''\n      ph.data = ''\n      ph.log.file = ''\n   end\n\n   return",
                                            "      ph.data = ''\n      ph.log.file = ''\n   end\n\n   return"),
                                           ("            goto terminate.phantom\n         end\n\n         * The option flags", "         end\n\n         * The option flags")],
     {"v": ["cmdalt", "badkey", "dadd"], "replay": True}, ["cmdalt.a", "badkey.a", "dadd.a", "replay.a"]),
]


def run_mutants():
    global QUIET, WAIT
    WAIT = 12
    say("\n--- the mutants: the sandbox's own copies of CPROC, PHANTOM and !IPC_SEAL broken one at a time ---------------------------------")
    caught = 0
    for name, prog, edits, what, red in MUTANTS:
        path = os.path.join(q3.SYS, "gpl.bp", prog)
        with open(path, encoding="utf-8", errors="replace") as f:
            real = f.read()
        text = real
        ok = True
        for old, new in edits:
            if text.count(old) != 1:
                say("  [MISSED] %s: the text to change is in %s %d times, not once" % (name, prog, text.count(old)))
                ok = False
                break
            text = text.replace(old, new, 1)
        if not ok:
            continue
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            out = q3.adm(["BASIC gpl.bp " + prog], internal=True)
            if not has(out, r"^Compiled 1 program\(s\) with no errors"):
                say("  [MISSED] %s: the broken %s did not compile: %s" % (name, prog, out[-3:]))
                continue
            RES.clear()
            QUIET = True
            if "legit" in what:
                rows_legit(only=what["legit"])
            for v in what.get("v", []):
                rows_variant(v, expect_saw=(v != "nox"))
            if what.get("replay"):
                rows_replay()
            QUIET = False
            went_red = [k for k in red if RES.get(k) is False]
            green_missing = [k for k in red if k not in RES]
            if len(went_red) == len(red) and not green_missing:
                caught += 1
                say("  [caught] %s: red %s" % (name, ", ".join(went_red)))
            else:
                say("  [MISSED] %s: wanted red %s, red was %s, never ran %s" % (name, red, sorted(k for k, v in RES.items() if not v), green_missing))
        finally:
            QUIET = False
            with open(path, "w", encoding="utf-8") as f:
                f.write(real)
            out = q3.adm(["BASIC gpl.bp " + prog], internal=True)
            if not has(out, r"^Compiled 1 program\(s\) with no errors"):
                say("  !! %s was NOT put back: %s" % (prog, out[-3:]))
                RES["restore"] = False
    say("mutants: %d of %d caught" % (caught, len(MUTANTS)))
    return caught == len(MUTANTS)


def main():
    global passed, failed
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-ipc.py <dir> [--build] [--mutants]")
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    q3.USER_PROGS = ORDINARY
    BOX, SYS = q3.BOX, q3.SYS
    say("sandbox-ipc: sandbox  %s" % BOX)
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            q3.bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ipc: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, the probes, one fixture account ----------------------------------------")
    q3.prepare()
    q3.build_account("zzaa")
    for nm, text in ORDINARY.items():
        put(os.path.join(SYS, "bp", nm), text)
    for nm, text in INTERNAL.items():
        put(os.path.join(SYS, "gpl.bp", nm), text)
    out = q3.adm(["BASIC bp " + " ".join(ORDINARY)])
    if not has(out, r"^Compiled %d program\(s\) with no errors" % len(ORDINARY)):
        q3.bail("the probes did not compile in the SDSYS account:\n" + "\n".join(out[-8:]))
    out = q3.adm(["BASIC gpl.bp " + " ".join(INTERNAL)], internal=True)
    if not has(out, r"^Compiled %d program\(s\) with no errors" % len(INTERNAL)):
        q3.bail("the internal probes did not compile:\n" + "\n".join(out[-8:]))
    out = q3.adm(["CREATE.FILE zzout DYNAMIC"])
    out = q3.adm(["RUN bp zzclr"])
    if not has(out, r"^CLRDONE$"):
        q3.bail("zzout could not be made or cleared:\n" + "\n".join(out[-6:]))
    say("  [done] the file zzout, the probes, the account zzaa")

    mut_ok = True
    try:
        say("\n--- A. the legitimate flows are as before -------------------------------------------------------------------------------------")
        rows_legit()
        rows_profiler()
        say("\n--- B. records that are not the ones PHANTOM sealed are not acted on ----------------------------------------------------------")
        rows_control()
        for v in ["cmdalt", "badkey", "noseal", "dadd", "ladd", "optalt", "nostage", "nox"]:
            rows_variant(v, expect_saw=(v != "nox"))
        rows_replay()
        if "--mutants" in sys.argv:
            mut_ok = run_mutants()
    finally:
        for lv_ in q3.lives:
            lv_.kill()
        for nm in ORDINARY:
            for d in ("bp", "bp.out"):
                p = os.path.join(SYS, d, nm)
                if os.path.exists(p):
                    os.remove(p)
        for nm in INTERNAL:
            for d in ("gpl.bp", "gpl.bp.out"):
                p = os.path.join(SYS, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-ipc: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        q3.bail("no row ran - a broken test, not a pass")
    return 1 if (failed or not mut_ok) else 0


if __name__ == "__main__":
    sys.exit(main())
