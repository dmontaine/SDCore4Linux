#!/usr/bin/env python3
#
# sandbox-nocase.py - no two record ids can differ only by case.  RELEASE_1.1 5 D2 (PAL-1), the Linux
# form of the Windows port's verify-twins.ps1.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-nocase.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree, no sudo, its own IPC
# keys: never the live system).  With --build the sandbox is built first from THIS tree; <dir> must
# then be empty or absent.  Without it <dir> must already be built, which is how the same script is
# run against an OLD build to prove it can fail.  Fixture names are unique to the run.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run (setup is not what the rows assume).
#
# WHAT IT MEASURES.  The kernel makes every hashed file it creates case insensitive (gplsrc/op_dio1.c),
# so a second spelling of an id IS the first record and a twin cannot be written, and a rebuild that
# would keep only one of a pair is refused:
#   A. a fresh file is NOCASE            - CREATE.FILE, then COPY the same record in as jack and as JACK:
#                                          ONE record, stored jack.  A2 reads the flag itself on the
#                                          data part, the dictionary part and the account's VOC.
#   B. CASE is refused for a normal user - 10176, printed a line at a time (no raw field marks), no file.
#   C. an OLD case-sensitive file with a twin is refused by CONFIGURE.FILE - the fixture is built only
#      by sd -internal (the one way to make a CASE file): jack and JACK, 2 records; CONFIGURE.FILE NO.CASE
#      answers 10177 naming both and leaves the file case sensitive with BOTH records.
#   D. the control - a single-spelling case-sensitive file converts, keeps its record, and is NOCASE.
#   E. the kernel's own guard, under the verbs: a BASIC create.file statement asking for KEEPCASE (4)
#      from an ordinary session still makes a NOCASE file, because the opcode honours it in internal
#      mode only.  Rows A-D cannot see this: CREATE.FILE refuses CASE before it reaches the kernel.
#
# THE INSTRUMENT.  It prints the commands it sent and what came back.  The flag is READ (fileinfo
# FL$NOCASE in a probe program), not inferred from a count, and every row that expects a fixture checks the
# fixture first and bails with 2 rather than passing over nothing.

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
N, C, K, X, E, P = ("zztwn" + RUN, "zztwc" + RUN, "zztwk" + RUN, "zzx" + RUN, "zztwe" + RUN, "zzncp" + RUN)
passed = failed = 0
# --solo: run SD Core for Linux Solo's createf and configf (and messages 10176 and 10177) inside this full-product
# sandbox.  The kernel is the full product's, the same C for everything these rows measure (op_create_dh); Solo
# has no sandbox tool of its own (LSOLO 40).  The rows are unchanged.
SOLO = "--solo" in sys.argv
SOLO_SDSYS = "/home/don/Projects/SDCore4LinuxSolo/sdb_ai/sd64/sdsys"


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
    say("sandbox-nocase: CANNOT RUN - " + msg)
    sys.exit(2)


def show(out):
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit "):
            say("      | " + line.rstrip()[:130])


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = out.split(":TERM 200,9999", 1)[-1]
    show(out)
    return out


def isess(box, *cmds):
    """The same, in internal mode (sd -internal): the only way to build a case-sensitive file."""
    say("    > [sd -internal] " + " | ".join(cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"),
                       env=env, capture_output=True, text=True, errors="replace", timeout=300)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\[[0-9;]*[A-Za-z]", "", out.split(":TERM 200,9999", 1)[-1])
    show(out)
    return out


def counted(text):
    m = re.search(r"(?m)^(\d+) record\(s\) (listed|counted)", text)
    return int(m.group(1)) if m else -1


def has_row(text, ident):
    """A LIST row for exactly this id, case sensitive: the id at the start of a line, then 2+ spaces or end."""
    return re.search(r"(?m)^" + re.escape(ident) + r"(\s{2,}|\s*$)", text) is not None


def flags(text):
    """{file: (data, dict)} from the probe's 'NC <file> data=<n> dict=<n>' lines; '-' when it would not open."""
    return {m.group(1): (m.group(2), m.group(3))
            for m in re.finditer(r"(?m)^NC (\S+) data=(\S+) dict=(\S+)\s*$", text)}


def write(path, lines):
    with open(path, "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("ascii"))


def on_disk(box, name):
    return os.path.exists(os.path.join(box, "sys", name)) or os.path.exists(os.path.join(box, "user_accounts", name))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-nocase.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-nocase: sandbox  %s" % box)
    say("sandbox-nocase: tree     %s" % os.path.dirname(HERE))
    say("sandbox-nocase: files    %s (fresh) %s (CASE, twin) %s (CASE, single) %s (CASE refused) %s (KEEPCASE statement)"
        % (N, C, K, X, E))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-nocase: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    if SOLO:
        say("sandbox-nocase: SOLO MODE - Solo's createf, configf and messages 10176, 10177 replace the full product's in this sandbox")
        for rel in ("gpl.bp/createf", "gpl.bp/configf", "messages/10176", "messages/10177"):
            src = os.path.join(SOLO_SDSYS, rel)
            if not os.path.isfile(src):
                bail("Solo has no %s" % src)
            shutil.copyfile(src, os.path.join(sysd, rel))
        r = subprocess.run([os.path.join(sysd, "bin", "sd"), "-internal", "BASIC", "gpl.bp", "createf", "configf"], cwd=sysd,
                           env=dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf")), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace", timeout=300)
        if len(re.findall(r"(?m)^Compiled 2 program\(s\) with no errors", r.stdout)) != 1:
            bail("Solo's createf and configf did not compile in the sandbox:\n" + r.stdout[-600:])

    # The probe reads the flag itself.  create.file ... flags 4 is the KEEPCASE request, written as the number
    # because int$keys.h (FL$FLAGS.KEEPCASE) is not for an ordinary program.
    write(os.path.join(sysd, "bp", P), [
        "$include keys.h",
        "   open 'VOC' to v then crt 'NC voc data=':fileinfo(v, FL$NOCASE):' dict=-' else crt 'NC voc data=- dict=-'",
        "   names = '%s':@fm:'%s':@fm:'%s':@fm:'%s'" % (N, C, K, E),
        "   for i = 1 to 4",
        "      nm = names<i>",
        "      d = '-' ; g = '-'",
        "      open nm to f then d = fileinfo(f, FL$NOCASE) else openpath nm to f then d = fileinfo(f, FL$NOCASE)",
        "      open 'DICT', nm to f2 then g = fileinfo(f2, FL$NOCASE)",
        "      crt 'NC ':nm:' data=':d:' dict=':g",
        "   next i",
        "end"])
    write(os.path.join(sysd, "bp", P + "k"), [
        "   create.file '%s' dynamic flags 4 on error crt 'KEEPCASE create failed' ; stop" % E,
        "   crt 'KEEPCASE statement made %s'" % E,
        "end"])

    def cleanup(probes=False):
        sess(box, *["DELETE.FILE %s FORCE" % n for n in (N, C, K, X, E)])
        for n in (N, C, K, X, E):
            for suffix in ("", ".dic"):
                for d in ("sys", "user_accounts"):
                    p = os.path.join(box, d, n + suffix)
                    # a hashed file is a directory here, and a create.file STATEMENT's file is in no VOC,
                    # so DELETE.FILE never sees it; the names carry the run's number, inside the sandbox
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                        say("    swept directory %s/%s" % (d, n + suffix))
                    elif os.path.isfile(p):
                        os.remove(p)
                        say("    swept %s/%s" % (d, n + suffix))
        if probes:
            for rec in (P, P + "k"):
                for d in ("bp", "bp.out"):
                    p = os.path.join(sysd, d, rec)
                    if os.path.exists(p):
                        os.remove(p)

    try:
        say("\n--- sweep leftovers, compile the probes ---------------------------------------")
        cleanup()
        out = sess(box, "BASIC bp %s" % P, "BASIC bp %sk" % P)
        clean = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: both probe programs compiled with no errors", clean == 2, "clean compiles: %d of 2" % clean)
        if clean != 2:
            bail("the probes did not compile - nothing below would read a flag")

        # --- A. a fresh file is NOCASE ----------------------------------------------------
        say("\n--- A. a fresh file folds: jack then JACK is ONE record -------------------------")
        out = sess(box, "CREATE.FILE " + N,
                   "COPY FROM VOC TO %s who,jack OVERWRITING" % N, "COPY FROM VOC TO %s who,JACK OVERWRITING" % N,
                   "COUNT " + N, "LIST %s @ID" % N, "RUN bp " + P)
        row("setup: the fixture file exists on disk", on_disk(box, N), "no file %s" % N)
        if not on_disk(box, N):
            bail("CREATE.FILE made no file - nothing below would measure the fold")
        row("A: a fresh file folds - writing jack then JACK leaves ONE record", counted(out) == 1, "COUNT said %d" % counted(out))
        row("A: the surviving id is the first spelling, jack (not JACK)", has_row(out, "jack") and not has_row(out, "JACK"),
            "jack=%s JACK=%s" % (has_row(out, "jack"), has_row(out, "JACK")))
        fl = flags(out)
        say("    flags read: " + "  ".join("%s=%s" % (k, v) for k, v in sorted(fl.items())) + "  voc=%s" % (
            re.search(r"(?m)^NC voc data=(\S+)", out).group(1) if re.search(r"(?m)^NC voc data=(\S+)", out) else "?"))
        row("A2: the data part reads NOCASE (flag 1)", fl.get(N, ("?", "?"))[0] == "1", repr(fl.get(N)))
        row("A2: the dictionary part reads NOCASE (flag 1)", fl.get(N, ("?", "?"))[1] == "1", repr(fl.get(N)))
        m = re.search(r"(?m)^NC voc data=(\S+)", out)
        row("A2: the account's VOC reads NOCASE (flag 1)", bool(m) and m.group(1) == "1", "voc flag %s" % (m.group(1) if m else "not printed"))

        # --- B. CASE is refused outside internal mode --------------------------------------
        say("\n--- B. CREATE.FILE ... CASE is refused for a normal session ------------------")
        out = sess(box, "CREATE.FILE %s CASE" % X)
        row("B: CREATE.FILE ... CASE answers 10176", "Record ids are case insensitive in every file, so CASE is not accepted." in out,
            "no 10176 text")
        row("B: the refusal carries no raw field mark (printed a line at a time)", "�" not in out and "\xfe" not in out,
            "a field mark reached the screen")
        row("B: and no file was created", not on_disk(box, X), "file %s exists" % X)

        # --- C. an OLD case-sensitive file with a twin ------------------------------------
        say("\n--- C. a case-sensitive file holding jack and JACK: CONFIGURE.FILE refuses -------")
        out = isess(box, "CREATE.FILE %s CASE" % C,
                    "COPY FROM VOC TO %s who,jack OVERWRITING" % C, "COPY FROM VOC TO %s who,JACK OVERWRITING" % C, "COUNT " + C)
        row("C-setup: sd -internal built a case-sensitive file", on_disk(box, C), "no file %s" % C)
        row("C-setup: it holds both jack and JACK (2 records)", counted(out) == 2, "COUNT said %d" % counted(out))
        out = sess(box, "RUN bp " + P)
        fl = flags(out)
        row("C-setup: the probe reads it as case SENSITIVE (flag 0) - KEEPCASE worked in internal mode",
            fl.get(C, ("?", "?"))[0] == "0", repr(fl.get(C)))
        if counted(out) != 2 and not on_disk(box, C):
            bail("the twin fixture was not built")
        out = sess(box, "CONFIGURE.FILE %s NO.CASE" % C)
        refused = "differ only by case" in out
        row("C: CONFIGURE.FILE NO.CASE refuses the twinned file (10177, 'differ only by case')", refused, "no 10177 text")
        row("C: the refusal names BOTH spellings", ("'jack'" in out and "'JACK'" in out), "ids not both named")
        row("C: the refusal carries no raw field mark", "�" not in out and "\xfe" not in out, "a field mark reached the screen")
        out = sess(box, "COUNT " + C, "RUN bp " + P)
        row("C: the file is LEFT AS IT WAS - both records survive, nothing lost", counted(out) == 2, "COUNT said %d" % counted(out))
        row("C: and it is still case sensitive (flag 0)", flags(out).get(C, ("?", "?"))[0] == "0", repr(flags(out).get(C)))

        # --- D. control: a single-spelling case-sensitive file converts ---------------------
        say("\n--- D. control: a case-sensitive file with only jack converts to NOCASE --------")
        out = isess(box, "CREATE.FILE %s CASE" % K, "COPY FROM VOC TO %s who,jack OVERWRITING" % K, "COUNT " + K)
        row("D-setup: the single-record CASE file exists with 1 record", on_disk(box, K) and counted(out) == 1,
            "exists=%s count=%d" % (on_disk(box, K), counted(out)))
        out = sess(box, "RUN bp " + P)
        row("D-setup: the probe reads it as case SENSITIVE (flag 0)", flags(out).get(K, ("?", "?"))[0] == "0", repr(flags(out).get(K)))
        out = sess(box, "CONFIGURE.FILE %s NO.CASE" % K, "COUNT " + K, "RUN bp " + P)
        row("D: it converted, and the 10177 refusal did not appear", "differ only by case" not in out, "refused a clean file")
        row("D: the record survived the rebuild (1 record)", counted(out) == 1, "COUNT said %d" % counted(out))
        row("D: and it now reads NOCASE (flag 1)", flags(out).get(K, ("?", "?"))[0] == "1", repr(flags(out).get(K)))

        # --- E. the kernel guard, under the verbs ------------------------------------------
        say("\n--- E. a create.file STATEMENT asking for KEEPCASE, from an ordinary session -----")
        out = sess(box, "RUN bp %sk" % P)
        row("E-setup: the statement ran and made the file", ("KEEPCASE statement made %s" % E) in out and on_disk(box, E),
            "no 'KEEPCASE statement made' line, or no file")
        out = sess(box, "RUN bp " + P)
        row("E: the kernel made it NOCASE anyway (flag 1): KEEPCASE is honoured in internal mode only",
            flags(out).get(E, ("?", "?"))[0] == "1", repr(flags(out).get(E)))
    finally:
        say("\n--- cleanup ------------------------------------------------------------------")
        cleanup(probes=True)
        left = [n for n in (N, C, K, X, E) if on_disk(box, n)]
        row("cleanup: no fixture file is left in sys or user_accounts", not left, " ".join(left))

    say("\nsandbox-nocase: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
