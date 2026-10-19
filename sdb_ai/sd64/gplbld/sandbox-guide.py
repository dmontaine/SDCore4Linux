#!/usr/bin/env python3
#
# sandbox-guide.py - the SD BASIC dialect guide (agent-pack/guide/sd-basic-guide.md) COMPILED AND RUN on a private SD.  S.69 row 1.
#                    No install, no sudo, no model.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-guide.py <dir> [--build] [--guide FILE] [--match REGEX]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree (it must be
# empty or absent).  Exit 0 every block held, 1 one did not, 2 it could not run.  SDBOX_KEYSET=n picks the pair of shared memory keys;
# stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.  --match REGEX runs only the blocks under headings that match (for
# writing the guide: a setup block under another heading is not run, so the later blocks may fail for want of it).
#
# START-HISTORY:
# 19 Oct 26 dm  Written FIRST, for the guide of S.69 row 1: a guide that tells an agent how SD BASIC behaves is only worth having if
#               every sentence in it was seen to hold.  Run red on a guide that did not exist, then on a trial guide with wrong rows.
# END-HISTORY
#
# THE BLOCKS (fenced, the language word first).  Nothing else in the guide is checked by this suite; prose that makes a claim carries a
# block, or the word [unverified] (counted and listed at the end).
#   ```basic frag run        statements; the suite wraps them in a program, compiles it, runs it and compares the NEXT ```output block
#   ```basic run id=NAME     a whole program, saved as bp/NAME; with `catalog` it is also catalogued (a subroutine other blocks call)
#   ```basic                 compiled only (a subroutine, or a program that needs a terminal): must say "Compiled 1 program(s) with no errors"
#   ```basic fail            must NOT compile: the NEXT ```error block names a line of what the compiler (or the gate) says
#   ```basic warn            must compile with 0 errors and WARN: the NEXT ```warning block names a line of the warning
#   ```notinsd               lines  name | statements | note  - each is wrapped in a program, and must fail to compile ("SD does not have X")
#   ```tcl run               TCL commands; the NEXT ```output block is what they print
#   ```tcl setup             TCL commands whose output is not compared (they must not print an error wording)
#   ```output / ```error     the expected text
# A block with  as=ACCOUNT  runs in an ORDINARY account, not as the administrator: gdoff (every gate off, as CREATE.ACCOUNT delivers it)
# or gdbp (bp-on only: it can compile).  The sandbox user plays SDSYS, which passes every gate, so those sessions need the preparation
# sandbox-gates.py makes (CPROC recompiled without the install arm; elevation only when SDTEST_ADMIN=1), and the suite refuses to go on
# if its first ordinary row does not prove the session is NOT an administrator.  The sandbox user's name is shown as <user>.
#
# A COMPILE counts only on the wording the compiler prints when it worked, "Compiled 1 program(s) with no errors", and only with no
# WARNING line (a variable that is never assigned is a warning at 0 errors and a program that fails when the line is reached).
# A RUN counts when its lines equal the output block's after trailing blanks are taken off and "at line N of /path" is made "at line N".
#
# THE NULL CASE.  A guide with too few run blocks, fail blocks or notinsd rows is refused (exit 1), and so is a block whose output block
# is missing; a session that printed none of the markers the suite asked for is exit 2.

import argparse
import getpass
import importlib.util
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
GUIDE = os.path.join(SD64, "agent-pack", "guide", "sd-basic-guide.md")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
USER = getpass.getuser()
passed = failed = 0
MIN_RUN, MIN_FAIL, MIN_NOTINSD = 20, 2, 20

# the ordinary accounts a block may name: register fields 7 to 12 (sh, os.execute, sd.accounts, voc.edit, bp.edit, dict.edit)
ORDINARY = {
    "gdoff": ["no", "no", "no", "no", "no", "no"],
    "gdbp": ["no", "no", "no", "no", "yes", "no"],
}


def say(s=""):
    print(s)
    sys.stdout.flush()


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-guide: CANNOT RUN - " + msg)
    sys.exit(2)


# ------------------------------------------------------------------------------------------------------ the guide

class Block:
    def __init__(self, lang, flags, text, line, heading):
        self.lang, self.flags, self.text, self.line, self.heading = lang, flags, text, line, heading
        self.partner = None            # the output / error / warning block that follows
        self.partner2 = None           # for a `warn run` block: the ```output block after the ```warning one
        self.name = None               # the bp record this block is saved as
        self.marker = None
        self.acct = None               # None = the administrator's session; else the ordinary account


def parse_guide(path):
    """The fenced blocks of the guide, each with the heading it sits under and its starting line."""
    blocks = []
    heading = ""
    cur = None
    for n, ln in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        if cur is None:
            m = re.match(r"^(#{1,4})\s+(.*\S)", ln)
            if m:
                heading = m.group(2)
            m = re.match(r"^```(\w+)\s*(.*)$", ln)
            if m:
                cur = Block(m.group(1), m.group(2).split(), [], n, heading)
        elif ln.startswith("```"):
            cur.text = "\n".join(cur.text)
            blocks.append(cur)
            cur = None
        else:
            cur.text.append(ln)
    if cur is not None:
        bail("%s: the block at line %d is never closed" % (path, cur.line))
    # pair every run / fail / tcl-run block with the output or error block that follows it before the next code block
    last = None
    for b in blocks:
        if b.lang in ("output", "error", "warning"):
            if last is not None and last.partner is None:
                last.partner = b
                if "warn" in last.flags and "run" in last.flags:
                    continue                       # a program that warns AND is run has a second partner: its ```output
            elif last is not None and last.partner2 is None and b.lang == "output" and "warn" in last.flags and "run" in last.flags:
                last.partner2 = b
            last = None
        elif b.lang in ("basic", "tcl", "notinsd"):
            last = b if ({"run", "fail", "warn"} & set(b.flags)) else None
            b.acct = flag(b, "as")
    return blocks


def flag(b, key):
    for f in b.flags:
        if f.startswith(key + "="):
            return f.split("=", 1)[1]
    return None


# ------------------------------------------------------------------------------------------------------ the sessions

def sd_session(box, cmds, timeout=420, account=None):
    """Run sd on a pipe with the commands.  With no account the sandbox user plays SDSYS (SDTEST_ADMIN=1 says so where the box has been
    prepared); with one, it is `sd -aACCOUNT` in that account's directory and the session is ordinary.  A hung session is hung up
    (SIGHUP) before it is killed, because a killed session keeps its slot in the user table."""
    conf = os.path.join(box, "sd.conf")
    env = dict(os.environ, SD_CONFIG=conf)
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    if account:
        env.pop("SDTEST_ADMIN", None)
    else:
        env["SDTEST_ADMIN"] = "1"
    argv = [os.path.join(box, "sys", "bin", "sd")] + (["-a" + account] if account else [])
    cwd = os.path.join(box, "user_accounts", account) if account else os.path.join(box, "user_accounts")
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, env=env, text=True, errors="replace")
    try:
        out, _ = p.communicate(body, timeout=timeout)
        hung = False
    except subprocess.TimeoutExpired:
        hung = True
        p.send_signal(signal.SIGHUP)
        try:
            out, _ = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            out, _ = p.communicate()
    out = ANSI.sub("", out or "")
    return out.split(":TERM 200,9999", 1)[-1], hung


def segments(out):
    """{marker: lines} - what SD printed after each @@@marker line DISPLAYed by the suite, echoed commands (":...") left out."""
    parts = re.split(r"(?m)^@@@(\S+)\s*$", out)
    got = {}
    for i in range(1, len(parts) - 1, 2):
        got[parts[i]] = [l.rstrip() for l in parts[i + 1].split("\n") if not l.startswith(":") and not l.startswith("exit ")]
    return got


def trim_blank(lines):
    lines = list(lines)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def norm_run(lines, squeeze=False):
    """at line N of /path -> at line N; the sandbox user's name (a whole word) -> <user>; the 8 hex digits that open a run time error
    (they differ between two runs of the same fault) -> <addr>; the "Page 1" that ends the first line of a report -> nothing; trailing
    blanks and edge blank lines off.  squeeze=True (the output of TCL verbs, which put blank lines between their answers) drops every
    blank line."""
    out = []
    for l in lines:
        l = re.sub(r"( at line \d+) of \S+", r"\1", l)
        l = re.sub(r"^[0-9A-F]{8}: ", "<addr>: ", l)
        l = re.sub(r"\b%s\b" % re.escape(USER), "<user>", l)
        l = re.sub(r"\s+Page \d+$", "", l)
        if squeeze and not l.strip():
            continue
        out.append(l.rstrip())
    return trim_blank(out)


def compile_verdict(lines):
    """(compiled clean?, the error lines, the warning lines, the error count) read off what BASIC printed."""
    text = "\n".join(lines)
    nerr = re.search(r"(?m)^(\d+) error\(s\)\s*$", text)
    errs = [l.strip() for l in lines if re.match(r"^\s*\d+: ", l)]
    warns = [l.strip() for l in lines if l.strip().startswith("WARNING:")]
    good = re.search(r"(?m)^Compiled 1 program\(s\) with no errors\s*$", text) is not None and nerr is not None and nerr.group(1) == "0"
    bad_words = [w for w in ("Unable to load", "not found", "Unrecognised statement", "Compiled 1 program(s) with errors") if w in text]
    return good and not bad_words, errs, warns, (int(nerr.group(1)) if nerr else None)


# ------------------------------------------------------------------------------------------------------ the ordinary accounts

def prepare_ordinary(box, accounts):
    """Make the sandbox able to run ORDINARY sessions and build the fixture accounts, through sandbox-gates.py's own functions."""
    spec = importlib.util.spec_from_file_location("sandbox_gates_for_guide", os.path.join(HERE, "sandbox-gates.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    g.BOX = box
    g.SYS = os.path.join(box, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    g.prepare()
    for acct in accounts:
        g.FIXTURES[acct] = ("no", "no")
        g.build_account(acct)
        path = os.path.join(box, "user_accounts", acct)
        sh, osx, sdacc, voc, bp, dic = ORDINARY[acct]
        g.reg_write(acct, [path, "", g.GROUP, "", "", "", sh, osx, sdacc, voc, bp, dic])
    return g


# ------------------------------------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--guide", default=GUIDE)
    ap.add_argument("--match", default=None)
    ap.add_argument("--mutant", default=None, choices=["open-gates"],
                    help="selftest: open-gates builds the ordinary accounts with every gate ON, so the guide's refusal blocks must go red")
    a = ap.parse_args()
    if a.mutant == "open-gates":
        for k in ORDINARY:
            ORDINARY[k] = ["yes"] * 6
    box = os.path.abspath(a.dir)
    guide = a.guide
    match = re.compile(a.match, re.I) if a.match else None
    sysd = os.path.join(box, "sys")
    say("sandbox-guide: sandbox %s" % box)
    say("sandbox-guide: guide   %s" % guide)
    say("sandbox-guide: tree    %s" % SD64)
    say("sandbox-guide: user    %s (plays SDSYS in the administrator's lane; shown as <user>)" % USER)
    if not os.path.isfile(guide):
        say("sandbox-guide: there is no guide at %s" % guide)
        sys.exit(1)
    if a.build:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-guide: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    blocks = parse_guide(guide)
    # a mark is  [unverified]  as plain text; the bold form is how the guide's introduction names the mark
    unverified = sum(len(re.findall(r"(?<!\*\*)\[unverified\](?!\*\*)", b)) for b in [open(guide, encoding="utf-8").read()])
    code = [b for b in blocks if b.lang in ("basic", "tcl", "notinsd")]
    if match:
        code = [b for b in code if match.search(b.heading)]
    n_run = sum(1 for b in code if b.lang == "basic" and "run" in b.flags)
    n_fail = sum(1 for b in code if b.lang == "basic" and "fail" in b.flags)
    n_not = sum(len([l for l in b.text.split("\n") if l.strip()]) for b in code if b.lang == "notinsd")
    n_ord = sum(1 for b in code if b.acct)
    say("sandbox-guide: %d blocks: %d basic run, %d basic fail, %d notinsd rows, %d compile-only, %d tcl, %d in an ordinary account; %d [unverified] marks" % (
        len(code), n_run, n_fail, n_not, sum(1 for b in code if b.lang == "basic" and not ({"run", "fail"} & set(b.flags))),
        sum(1 for b in code if b.lang == "tcl"), n_ord, unverified))
    if not match:
        row("the guide is not empty: at least %d run blocks, %d fail blocks, %d notinsd rows" % (MIN_RUN, MIN_FAIL, MIN_NOTINSD),
            n_run >= MIN_RUN and n_fail >= MIN_FAIL and n_not >= MIN_NOTINSD, "%d / %d / %d" % (n_run, n_fail, n_not))
    accts = sorted({b.acct for b in code if b.acct})
    for acct in accts:
        if acct not in ORDINARY:
            bail("a block names the account %r; the suite knows %s" % (acct, sorted(ORDINARY)))

    # cleanup of an earlier run: the files this guide creates are removed first (a create.file on an existing file would not say so)
    created = []
    for b in code:
        if b.lang == "tcl" and not b.acct:
            created += re.findall(r"(?mi)^\s*create\.file\s+(?:dict\s+)?(\S+)", b.text)
    if accts:
        say("sandbox-guide: preparing the sandbox for ordinary sessions (CPROC without the install arm) and the accounts %s" % ", ".join(accts))
        prepare_ordinary(box, accts)
    if created:
        sd_session(box, ["DELETE.FILE %s NO.QUERY" % f for f in sorted(set(created))], timeout=120)

    # the commands, in document order, with a marker before each block; one session for the administrator, one for each ordinary account
    lanes = {}                                # account (None = administrator) -> commands
    names = []                                # (directory, record) to remove afterwards
    seq = 0

    def bpdir(acct):
        return os.path.join(box, "user_accounts", acct, "bp") if acct else os.path.join(sysd, "bp")

    for b in code:
        seq += 1
        b.marker = "B%03d" % seq
        cmds = lanes.setdefault(b.acct, [])
        if b.lang == "basic":
            nm = flag(b, "id") or ("gz%03d" % seq)
            b.name = nm
            src = b.text
            if "frag" in b.flags:
                src = "program %s\n%s\nend\n" % (nm, b.text)
            elif not src.endswith("\n"):
                src += "\n"
            with open(os.path.join(bpdir(b.acct), nm), "w", encoding="ascii", errors="replace") as f:
                f.write(src)
            names.append((b.acct, nm))
            cmds += ["DISPLAY @@@%sC" % b.marker, "BASIC bp %s" % nm]
            if "catalog" in b.flags:
                cmds.append("CATALOG bp %s" % nm)
            if "run" in b.flags:
                cmds += ["DISPLAY @@@%sR" % b.marker, "RUN bp %s" % nm]
        elif b.lang == "tcl":
            cmds.append("DISPLAY @@@%sR" % b.marker)
            cmds += [l for l in b.text.split("\n") if l.strip()]
        elif b.lang == "notinsd":
            for k, ln in enumerate([l for l in b.text.split("\n") if l.strip()]):
                parts = [p.strip() for p in ln.split("|")]
                if len(parts) < 2:
                    continue
                nm = "gn%03d%02d" % (seq, k)
                with open(os.path.join(bpdir(b.acct), nm), "w", encoding="ascii", errors="replace") as f:
                    f.write("program %s\n%s\nend\n" % (nm, parts[1].replace(";", "\n")))
                names.append((b.acct, nm))
                cmds += ["DISPLAY @@@%sN%02d" % (b.marker, k), "BASIC bp %s" % nm]

    seg = {}
    for acct in sorted(lanes, key=lambda x: (x is not None, x or "")):
        cmds = lanes[acct]
        say("sandbox-guide: running %d commands in one %s session" % (len(cmds), ("ordinary (" + acct + ")") if acct else "administrator's"))
        t0 = time.time()
        out, hung = sd_session(box, cmds, timeout=900, account=acct)
        say("sandbox-guide: the session took %.0f s%s" % (time.time() - t0, " AND HAD TO BE HUNG UP" if hung else ""))
        s = segments(out)
        if not s:
            bail("the session printed none of the markers (first lines: %r)" % out[:300].splitlines()[:4])
        seg.update(s)
        row("the %s session ended by itself" % (("ordinary " + acct) if acct else "administrator's"), not hung, "it was still running at the timeout")
        if acct:
            # the null case of an ordinary session: it must not be the administrator in disguise
            probe = sd_session(box, ["WHO.AM.I"], timeout=120, account=acct)[0]
            m = re.search(r"Admin\?\s*:\s*(\w+)", probe)
            row("the ordinary session %s is NOT an administrator (WHO.AM.I says Admin? %s)" % (acct, m.group(1) if m else "-"), bool(m) and m.group(1) == "No",
                "the session is privileged or WHO.AM.I printed nothing: %s" % probe[:200])
            if not (m and m.group(1) == "No"):
                bail("an ordinary session came out privileged; its refusals prove nothing")

    for b in code:
        where = "line %d (%s)%s" % (b.line, b.heading[:48], (" [as " + b.acct + "]") if b.acct else "")
        if b.lang == "basic":
            comp = seg.get(b.marker + "C")
            if comp is None:
                row("%s: basic: no output was printed for this block" % where, False, "marker %sC missing - an earlier block hung the session?" % b.marker)
                continue
            ok, errs, warns, nerr = compile_verdict(comp)
            if "warn" in b.flags:
                # compiles (0 errors) but the compiler warns: the NEXT ```warning block names a line of the warning
                want = b.partner.text.strip().split("\n")[0].strip() if b.partner is not None else None
                hit = want is not None and any(want in w for w in warns)
                row("%s: basic warn: compiled with 0 errors and warned %r (%s)" % (where, want, "; ".join(warns[:2]) or "no warning"),
                    b.partner is not None and nerr == 0 and hit, "compiler said: %s" % "; ".join(comp[:6]))
                if "run" in b.flags:               # and what the program then does, which is the point of showing a warning
                    if b.partner2 is None:
                        row("%s: basic warn run %s has an output block after the warning block" % (where, b.name), False, "none")
                    else:
                        got = norm_run(seg.get(b.marker + "R", []))
                        want2 = norm_run(b.partner2.text.split("\n"))
                        row("%s: basic warn run %s then printed what the guide says (%d lines)" % (where, b.name, len(want2)), got == want2 and len(want2) > 0,
                            "wanted %r, got %r" % (want2[:8], got[:8]))
                continue
            if "fail" in b.flags:
                want = b.partner.text.strip().split("\n")[0].strip() if b.partner is not None else None
                hit = want is not None and any(want in l for l in comp)
                shown = (errs or [l for l in comp if l.strip()] or ["no output"])[0]
                row("%s: basic fail: refused with %r (%s)" % (where, want, shown), b.partner is not None and not ok and hit,
                    "compiler said: %s" % "; ".join(comp[:6]) if not hit else "it compiled clean")
                continue
            row("%s: basic %s compiles clean%s" % (where, b.name, "" if not warns else " (WARNINGS)"), ok and not warns,
                "; ".join((errs + warns + comp)[:5]))
            if "run" in b.flags:
                if b.partner is None or b.partner.lang != "output":
                    row("%s: basic run %s has an output block after it" % (where, b.name), False, "none")
                    continue
                got = norm_run(seg.get(b.marker + "R", []))
                want = norm_run(b.partner.text.split("\n"))
                row("%s: basic run %s printed what the guide says (%d lines)" % (where, b.name, len(want)), got == want and len(want) > 0 or got == want == [],
                    "wanted %r, got %r" % (want[:8], got[:8]))
        elif b.lang == "tcl":
            got = norm_run(seg.get(b.marker + "R", []), squeeze=True)
            if "run" in b.flags:
                if b.partner is None or b.partner.lang != "output":
                    row("%s: tcl run has an output block after it" % where, False, "none")
                    continue
                want = norm_run(b.partner.text.split("\n"), squeeze=True)
                row("%s: tcl run printed what the guide says (%d lines)" % (where, len(want)), got == want and len(want) > 0, "wanted %r, got %r" % (want[:8], got[:8]))
            else:
                bad = [l for l in got if re.search(r"(?i)\b(not found|syntax error|unable|cannot|refused|error)\b", l)]
                row("%s: tcl setup ran without an error wording" % where, not bad, "; ".join(bad[:3]))
        elif b.lang == "notinsd":
            for k, ln in enumerate([l for l in b.text.split("\n") if l.strip()]):
                parts = [p.strip() for p in ln.split("|")]
                comp = seg.get("%sN%02d" % (b.marker, k))
                if comp is None:
                    row("%s: notinsd %s: nothing was printed" % (where, parts[0]), False, "marker missing")
                    continue
                ok, errs, warns, nerr = compile_verdict(comp)
                row("%s: SD does not have %s: it does not compile (%s)" % (where, parts[0], (errs or ["no error line"])[0]),
                    not ok and (nerr or 0) > 0 and len(errs) > 0, "it compiled clean - the guide is out of date: %s" % " ".join(comp[:3]) if ok else "; ".join(comp[:4]))

    # remove what this run made (the sandbox is disposable, but a second run on it must start from the same state)
    for acct, nm in names:
        for d in ("bp", "bp.out"):
            p = os.path.join(box, "user_accounts", acct, d, nm) if acct else os.path.join(sysd, d, nm)
            if os.path.exists(p):
                os.remove(p)
    if created:
        sd_session(box, ["DELETE.FILE %s NO.QUERY" % f for f in sorted(set(created))], timeout=120)
    witnessed = len(re.findall(r"\[witnessed:", open(guide, encoding="utf-8").read()))
    if unverified:
        say("sandbox-guide: %d [unverified] marks in the guide - claims with no probe behind them" % unverified)
    if witnessed:
        say("sandbox-guide: %d [witnessed: ...] marks - claims whose probe is in another suite, named in the mark, not run here" % witnessed)
    say("\nsandbox-guide: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 and passed > 0 else 1)


if __name__ == "__main__":
    main()
