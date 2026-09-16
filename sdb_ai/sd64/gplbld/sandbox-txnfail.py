#!/usr/bin/env python3
#
# sandbox-txnfail.py - P.6: the step-2 fixes that only an INDUCED FAILURE can
#                      exercise (A1, A3, A5, A6), run in a private sandbox SD,
#                      each against a mutant build that reverts it.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/sandbox-txnfail.py --dir <empty scratch dir>
#   python3 .../sandbox-txnfail.py --dir <dir> --keep      leave the sandbox built
#
# NO SUDO, AND NEVER THE LIVE SYSTEM.  Exit 0 every decisive row passed on the
# fixed build AND went red on its mutant; 1 a row failed or a mutant did not go
# red; 2 it could not run (or refused to).
#
# ===========================================================================
# WHY A SANDBOX
# ===========================================================================
# Every one of these needs a commit, a truncate or an index write to FAIL part
# way, and the record says what that looks like on the live system when a fix
# is wrong: a stranded lock that survives OFF (queue 27) and the 11 Sep wedge.
# PROJECT_STATUS P.6: "sandbox work, not DON work".  The sandbox is the 11 Sep
# recipe made repeatable:
#   - a copy of this sd64 tree with SD_SHM_KEY/SD_SEM_KEY moved to 0x716d0901/
#     0902 (live is 0301/0302) and check_admin() stubbed - IN THE COPY ONLY;
#   - a copy of /usr/local/sdsys (minus $cred and audit, which are root-only)
#     with the sandbox binaries in its bin;
#   - a private sd.conf named by SD_CONFIG (inipath.c);
#   - a copy of the invoking user's own account, registered in the copy.
# The live segment is printed before and after and must not change.
#
# ===========================================================================
# WHAT EACH ROW MEASURES (the fix, and what its mutant does instead)
# ===========================================================================
# A6  WEOFSEQ on /dev/null (ftruncate EINVAL) must take ON ERROR with 3010;
#     OPENSEQ ... OVERWRITE on a read-only regular file must too, and leave the
#     file as it was.  A device cannot reach the OVERWRITE truncate
#     (op_seqio.c: SQ_NOTFL skips the special modes), which is why that half
#     uses a read-only file.  Mutant: both "succeed", the old content stays.
# L1  after that failed OVERWRITE, the NEXT session sees no record lock - the
#     op_openseq cleanup fix of 14 Sep 2026, found by this script's first run.
# A3  a transaction that deletes a directory-file record from a directory made
#     mode 555 must fail its COMMIT out loud.  Mutant (bare remove()): COMMIT
#     returns status 0 and the record is still there.
# A1  that same commit wrote two DH records first; the failure must put both
#     back (errlog: "3 record(s) restored").  Mutant (no replay_undo): the two
#     NEW values stay - a half-applied commit.
# A5  an I-type index with 245-byte keys over tiny records, grown under
#     RLIMIT_FSIZE with SIGXFSZ ignored: every write whose index node cannot
#     be allocated must be REPORTED (8506, from get_ak_node), and afterwards the
#     index must hold exactly the records whose writes were not reported as
#     failed, with no wrong entries, and keep working.  MUTANT (grow check
#     removed): WHERE THE LIMIT FALLS DECIDES HOW IT SHOWS.  Measured by hand at
#     32768 it gave the fix's counts with another status (8006); at 33792, this
#     script's first full run, it reported 204 failures while 239 records were
#     missing from the index, lost 16 of 40 later writes after the limit was
#     lifted, and never finished 41..600.  So A5.R asks for ANY of: index loss
#     beyond the reported failures, loss after the limit is lifted, or a hang.
#     The free-node READ-failure path (the double allocation the fix's comment
#     describes) needs a transient read error nothing here can induce, and is
#     stated as unexercised.
#
# ***A1's LOCK HALF IS NOT SCORED***: after the failed commit no locks remain on
# the fixed build AND on its mutant, so this probe cannot see it.  Printed.
#
# THE SANDBOX'S sdlnxd IS KILLED AFTER -start (by executable path): its
# periodic check would run "sd -cleanup" mid-run.

import argparse
import getpass
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
LIVE_SYS = "/usr/local/sdsys"
LIVE_KEYS = ("0x716d0301", "0x716d0302")
BOX_KEYS = ("0x716d0901", "0x716d0902")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

PASS = FAIL = 0


def say(s=""):
    print(s)
    sys.stdout.flush()


def die(msg):
    """Could not run, or refused to: exit 2.  SystemExit still runs the
    teardown in main()'s finally block."""
    say(msg)
    sys.exit(2)


def ck(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    say("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, (": " + detail) if detail else ""))


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ipcs_keys():
    out = sh(["ipcs", "-m", "-s"]).stdout
    return sorted(set(re.findall(r"0x716d0[0-9]0[12]", out)))


def replace_once(path, old, new, label):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    n = text.count(old)
    if n != 1:
        die("sandbox-txnfail: CANNOT RUN - %s: expected exactly one match in %s, found %d"
                         % (label, path, n))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new))
    say("    patched %s (%s)" % (os.path.relpath(path, os.path.dirname(os.path.dirname(path))), label))


# ---------------------------------------------------------------------------
# The patches.  Each must match exactly once, or the run refuses: a patch that
# matched nothing would build a "mutant" identical to the fix and every red
# control would silently pass.

SANDBOX_PATCHES = [
    ("gplsrc/sddefs.h", "#define SD_SHM_KEY 0x716d0301", "#define SD_SHM_KEY 0x716d0901", "sandbox shm key"),
    ("gplsrc/sddefs.h", "#define SD_SEM_KEY 0x716d0302", "#define SD_SEM_KEY 0x716d0902", "sandbox sem key"),
    ("gplsrc/sd.c",
     '  if (geteuid() != 0) {\n    fprintf(stderr, "Command requires administrator privileges\\n");\n    exit(1);\n  }\n',
     '  fprintf(stderr, "sd: SANDBOX BUILD - check_admin stubbed\\n");\n',
     "check_admin stub"),
]

MUTANT_A = [  # A6 both sites, A1, A5
    ("gplsrc/op_seqio.c",
     "  if (chsize64(fu, sq_file->posn) != 0) {\n    process.status = -ER_IOE;\n    process.os_error = OSError;\n  }\n",
     "  chsize64(fu, sq_file->posn);  /* MUTANT A6 weofseq */\n", "mutant A6 WEOFSEQ"),
    ("gplsrc/op_seqio.c",
     "        if (chsize64(fu, sq_file->posn)) {\n          process.status = -ER_IOE;\n          process.os_error = OSError;\n          goto exit_op_openseq;\n        }\n",
     "        chsize64(fu, sq_file->posn);  /* MUTANT A6 overwrite */\n", "mutant A6 OVERWRITE"),
    ("gplsrc/txn.c",
     "  replay_undo();\n\n  if (commit_txn_id != 0) {\n    unlock_txn(commit_txn_id);\n    commit_txn_id = 0;\n  }\n",
     "  /* MUTANT A1 */\n", "mutant A1 undo+locks"),
    ("gplsrc/dh_ak.c",
     "    if (chsize64(dh_file->sf[subfile].fu, file_bytes + DH_AK_NODE_SIZE)) {\n      dh_err = DHE_AK_WRITE_ERROR;\n      new_node_num = 0;\n      goto exit_get_ak_node;\n    }\n",
     "    chsize64(dh_file->sf[subfile].fu, file_bytes + DH_AK_NODE_SIZE);  /* MUTANT A5 */\n", "mutant A5 grow"),
]

MUTANT_B = [  # A3 alone: with A3 reverted the commit never fails, so A1 cannot share it
    ("gplsrc/txn.c",
     "              if (remove(path) < 0) {\n                process.os_error = errno;\n                if (process.os_error != ENOENT) {\n                  process.status = -ER_PERM;\n                  log_permissions_error(fvar);\n                  k_error(sysmsg(1423));\n                  goto exit_op_txncmt;\n                }\n              }\n",
     "              remove(path);  /* MUTANT A3 */\n", "mutant A3 remove"),
]

# ---------------------------------------------------------------------------
# The BASIC probes, written into the sandbox account's bp.

PROBES = {
"zza6": r"""* ZZA6 - A6: WEOFSEQ and OPENSEQ OVERWRITE must report a failed truncate.
path = @path:'/zza6.dat'
openseq path to c then null else null
writeblk 'ABCDE' to c else crt 'CONTROL writeblk failed'
closeseq c
openseq path to c else crt 'CONTROL reopen failed'
readblk x from c, 2 else null
weofseq c on error
   crt 'CONTROL ON ERROR status=':status()
end
crt 'CONTROL weofseq status=':status()
closeseq c
d = '?'
openseq path to c then
   readblk d from c, 100 else d = ''
   closeseq c
end else null
crt 'CONTROL content=':d
openseq '/dev/null' to n else crt 'DEVICE openseq ELSE status=':status()
writeblk 'XYZ' to n else null
weofseq n on error
   crt 'DEVICE ON ERROR status=':status()
   goto done
end
crt 'DEVICE weofseq returned without error, status=':status()
done:
closeseq n
ropath = @path:'/zza6ro.dat'
openseq ropath overwrite to o on error
   crt 'OVERWRITE ON ERROR status=':status()
   goto done2
end then
   crt 'OVERWRITE opened without error, status=':status()
   closeseq o
end else
   crt 'OVERWRITE ELSE status=':status()
end
done2:
openseq path overwrite to c then
   closeseq c
end else crt 'CONTROL overwrite ELSE status=':status()
d = '?'
openseq path to c then
   readblk d from c, 100 else d = ''
   closeseq c
end else null
crt 'CONTROL after overwrite len=':len(d)
crt 'ZZA6 END'
end
""",
"zza1s": r"""* ZZA1S - the BEFORE values, outside any transaction.
open 'zza1h' to h else stop 'ZZA1S cannot open zza1h'
open 'zza1d' to d else stop 'ZZA1S cannot open zza1d'
write 'OLDK1' to h, 'k1'
write 'OLDK2' to h, 'k2'
write 'OLDR1' to d, 'r1'
crt 'ZZA1S wrote k1=OLDK1 k2=OLDK2 r1=OLDR1'
end
""",
"zza1t": r"""* ZZA1T - two DH writes, then a directory-file delete the driver made impossible.
open 'zza1h' to h else stop 'ZZA1T cannot open zza1h'
open 'zza1d' to d else stop 'ZZA1T cannot open zza1d'
crt 'ZZA1T.BEGIN'
begin transaction
   readu x from h, 'k1' else x = ''
   write 'NEWK1' to h, 'k1'
   readu x from h, 'k2' else x = ''
   write 'NEWK2' to h, 'k2'
   readu x from d, 'r1' else x = ''
   delete d, 'r1'
   commit
end transaction
crt 'ZZA1T.COMMIT.RETURNED status=':status()
end
""",
"zza1r": r"""* ZZA1R - what is on file now.
open 'zza1h' to h else stop 'ZZA1R cannot open zza1h'
open 'zza1d' to d else stop 'ZZA1R cannot open zza1d'
read k1 from h, 'k1' else k1 = '(missing)'
read k2 from h, 'k2' else k2 = '(missing)'
read r1 from d, 'r1' else r1 = '(missing)'
crt 'ZZA1R k1=':k1:' k2=':k2:' r1=':r1
end
""",
"zza5d": r"""* ZZA5D - an I-type index key of 245 bytes (MAX_KEY_LEN is 255).
open 'dict', 'zza5' to dd else stop 'ZZA5D cannot open dict zza5'
write 'I':@fm:"STR('K',240):@ID":@fm:'':@fm:'LKEY':@fm:'250L':@fm:'S' to dd, 'lkey'
crt 'ZZA5D wrote dict zza5 lkey'
end
""",
"zza5w": r"""* ZZA5W lo hi - write records lo..hi, each checked.
lo = field(trim(@sentence), ' ', 2) + 0
hi = field(trim(@sentence), ' ', 3) + 0
open 'zza5' to f else stop 'ZZA5W cannot open zza5'
ok = 0 ; bad = 0 ; first.bad = ''
for i = lo to hi
   failed = @false
   write 'D' to f, i on error
      failed = @true
      bad += 1
      if first.bad = '' then first.bad = status()
   end
   if not(failed) then ok += 1
next i
crt 'ZZA5W lo=':lo:' hi=':hi:' ok=':ok:' failed=':bad:' first.status=':first.bad
end
""",
"zza5v": r"""* ZZA5V - every record on file must be found by its index key, exactly.
open 'zza5' to f else stop 'ZZA5V cannot open zza5'
select f to 1
ids = '' ; n.data = 0
loop
   readnext id from 1 else exit
   n.data += 1
   ids<-1> = id
repeat
miss = 0 ; wrong = 0
for i = 1 to n.data
   id = ids<i>
   selectindex 'lkey', str('K', 240):id from f to 2
   got = ''
   loop
      readnext g from 2 else exit
      got<-1> = g
   repeat
   if got = '' then
      miss += 1
   end else
      if got # id then wrong += 1
   end
next i
crt 'ZZA5V data.records=':n.data:' index.missing=':miss:' index.wrong=':wrong
end
""",
}


class Box:
    def __init__(self, root, user):
        self.root = root
        self.sys = os.path.join(root, "sys")
        self.acct = os.path.join(root, "accounts", "box")
        self.conf = os.path.join(root, "sd.conf")
        self.user = user

    def env(self):
        e = dict(os.environ)
        e["SD_CONFIG"] = self.conf
        return e

    def session(self, binary, lines, limit=None, timeout=120):
        body = "\nTERM 200,9999\n" + "".join(l + "\n" for l in lines) + "OFF\n"
        cmd = [binary]
        if limit:
            cmd = [sys.executable, "-c",
                   "import os,resource,signal,sys; signal.signal(signal.SIGXFSZ, signal.SIG_IGN); "
                   "resource.setrlimit(resource.RLIMIT_FSIZE, (%d, %d)); os.execv(sys.argv[1], sys.argv[1:])"
                   % (limit, limit), binary]
        say("    > %s%s: %s" % (os.path.relpath(binary, self.root),
                               (" (RLIMIT_FSIZE=%d, SIGXFSZ ignored)" % limit) if limit else "",
                               " | ".join(lines)))
        try:
            p = subprocess.run(cmd, input=body, capture_output=True, text=True, cwd=self.acct,
                               env=self.env(), timeout=timeout)
        except subprocess.TimeoutExpired:
            say("      | TIMEOUT after %d s - the session was killed" % timeout)
            self.kill_daemons()
            return "TIMEOUT"
        out = ANSI.sub("", p.stdout + p.stderr)
        for l in out.splitlines():
            if re.match(r"^(ZZA|CONTROL|DEVICE|OVERWRITE|[0-9A-F]{8}:|There are|User |\s+\d+\s+\d+ )", l):
                say("      | " + l)
        return out

    def start(self):
        binary = os.path.join(self.sys, "bin", "sd")
        with open(os.path.join(self.root, "start.log"), "w") as log:
            subprocess.run([binary, "-start"], stdout=log, stderr=log, env=self.env())
        time.sleep(1)
        self.kill_daemons()

    def stop(self):
        binary = os.path.join(self.sys, "bin", "sd")
        with open(os.path.join(self.root, "stop.log"), "w") as log:
            subprocess.run([binary, "-stop"], stdout=log, stderr=log, env=self.env())
        self.kill_daemons()

    def kill_daemons(self):
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                exe = os.readlink("/proc/%s/exe" % pid)
            except OSError:
                continue
            if exe.startswith(self.root + os.sep):
                os.kill(int(pid), signal.SIGTERM)
                say("    killed sandbox process %s (%s)" % (pid, os.path.basename(exe)))


def build(tree_dir, patches):
    say("  build %s" % tree_dir)
    shutil.copytree(SD64, tree_dir, ignore=shutil.ignore_patterns("bin", "gplobj", "terminfo", "__pycache__"))
    os.makedirs(os.path.join(tree_dir, "bin"))
    os.makedirs(os.path.join(tree_dir, "gplobj"))
    for rel, old, new, label in patches:
        replace_once(os.path.join(tree_dir, rel), old, new, label)
    p = sh(["make"], cwd=tree_dir)
    if p.returncode != 0 or not os.path.exists(os.path.join(tree_dir, "bin", "sd")):
        say(p.stdout[-2000:] + p.stderr[-2000:])
        die("sandbox-txnfail: CANNOT RUN - make failed in %s" % tree_dir)
    say("    make exit 0, bin/sd built")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="an EMPTY or absent scratch directory")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    user = getpass.getuser()
    live_acct = os.path.join("/home/sd/user_accounts", user)

    say("sandbox-txnfail")
    say("  tree        : %s" % SD64)
    say("  sandbox     : %s" % root)
    say("  user        : %s (uid %d)" % (user, os.getuid()))
    say("  account copy: %s" % live_acct)
    before = ipcs_keys()
    say("  IPC keys before: %s" % " ".join(before))
    if os.getuid() == 0:
        die("sandbox-txnfail: REFUSED - run it as an ordinary user; root would reach the live system's files.")
    if any(k in before for k in BOX_KEYS):
        die("sandbox-txnfail: REFUSED - sandbox keys %s already exist; tear the old sandbox down first." % " ".join(BOX_KEYS))
    if os.path.exists(root) and os.listdir(root):
        die("sandbox-txnfail: REFUSED - %s is not empty." % root)
    if not os.path.isdir(live_acct) or not os.path.isdir(LIVE_SYS):
        die("sandbox-txnfail: CANNOT RUN - %s or %s is missing." % (live_acct, LIVE_SYS))
    os.makedirs(root, exist_ok=True)

    box = Box(root, user)
    try:
        say("\n=== 1. build: the sandbox tree and two mutants")
        build(os.path.join(root, "fixed"), SANDBOX_PATCHES)
        build(os.path.join(root, "mutA"), SANDBOX_PATCHES + MUTANT_A)
        build(os.path.join(root, "mutB"), SANDBOX_PATCHES + MUTANT_B)

        say("\n=== 2. the sandbox system and account")
        shutil.copytree(LIVE_SYS, box.sys, ignore=shutil.ignore_patterns("$cred", "audit", "dumps"))
        os.makedirs(os.path.join(box.sys, "$cred"))
        os.makedirs(os.path.join(box.sys, "dumps"))
        open(os.path.join(box.sys, "audit"), "w").close()
        for b in ("sd", "sdlnxd"):
            shutil.copy2(os.path.join(root, "fixed", "bin", b), os.path.join(box.sys, "bin", b))
        shutil.copytree(live_acct, box.acct, ignore=shutil.ignore_patterns("stacks"))
        reg = os.path.join(box.sys, "accounts")
        for r in os.listdir(reg):
            os.remove(os.path.join(reg, r))
        with open(os.path.join(reg, user), "w") as f:
            f.write("%s\n\nsdu_%s\n\nPROGRAMMER" % (box.acct, user))
        with open(os.path.join(reg, "sdsys"), "w") as f:
            f.write("%s\n\nsdsys" % box.sys)
        with open(box.conf, "w") as f:
            f.write("[sd]\nSDSYS=%s\nGRPSIZE=2\nNUMUSERS=20\nSORTMEM=4096\nERRLOG=50\nUSRDIR=%s\nGRPDIR=%s\nDUMPDIR=%s\n"
                    % (box.sys, os.path.dirname(box.acct), os.path.join(root, "groups"), os.path.join(box.sys, "dumps")))
        say("    sys, account 'box' (registered as %s), sd.conf written" % user)
        box.start()
        after = ipcs_keys()
        say("  IPC keys after start: %s" % " ".join(after))
        ck("S0 the sandbox has its own keys and the live keys are untouched",
           all(k in after for k in BOX_KEYS) and all((k in after) == (k in before) for k in LIVE_KEYS))

        fixed = os.path.join(box.sys, "bin", "sd")
        mutA = os.path.join(root, "mutA", "bin", "sd")
        mutB = os.path.join(root, "mutB", "bin", "sd")
        bp = os.path.join(box.acct, "bp")
        for name, src in PROBES.items():
            with open(os.path.join(bp, name), "w") as f:
                f.write(src)
        out = box.session(fixed, ["CREATE.FILE zza1d DIRECTORY", "CREATE.FILE zza1h", "CREATE.FILE zza5",
                                  "BASIC BP " + " ".join(n.upper() for n in PROBES)]
                          + ["CATALOG BP %s LOCAL" % n for n in PROBES])
        ck("S1 every probe compiled", "Compiled %d program(s) with no errors" % len(PROBES) in out)

        # ---- A6 and L1 -------------------------------------------------------
        say("\n=== 3. A6 (and L1): a failed truncate is reported, and leaves no lock")
        ro = os.path.join(box.acct, "zza6ro.dat")
        results = {}
        for label, binary in (("fixed", fixed), ("mutant", mutA)):
            box.stop(); box.start()
            with open(ro, "w") as f:
                f.write("OLDCONTENT")
            os.chmod(ro, 0o444)
            out = box.session(binary, ["ZZA6"])
            os.chmod(ro, 0o644)
            with open(ro) as f:
                kept = f.read()
            locks = box.session(fixed, ["LIST.READU"])
            results[label] = (out, kept, locks)
        out, kept, locks = results["fixed"]
        ck("A6.0 control: a regular file truncates (content AB)", "CONTROL content=AB" in out)
        ck("A6.1 WEOFSEQ on /dev/null takes ON ERROR with 3010", "DEVICE ON ERROR status=3010" in out)
        ck("A6.2 OVERWRITE of a read-only file takes ON ERROR with 3010", "OVERWRITE ON ERROR status=3010" in out)
        ck("A6.3 and the read-only file is unchanged", kept == "OLDCONTENT", repr(kept))
        ck("L1 the next session holds no stranded lock", "There are no active file, read or update locks" in locks)
        out, kept, locks = results["mutant"]
        ck("A6.1R RED: the mutant's WEOFSEQ reports nothing", "DEVICE weofseq returned without error" in out)
        ck("A6.2R RED: the mutant's OVERWRITE 'opens' and truncates nothing", "OVERWRITE opened without error" in out and kept == "OLDCONTENT")

        # ---- A3 and A1 -------------------------------------------------------
        say("\n=== 4. A3 and A1: a commit that fails part way says so and puts back what it wrote")
        d = os.path.join(box.acct, "zza1d")
        errlog = os.path.join(box.sys, "errlog")

        def txn_run(binary):
            os.chmod(d, 0o755)
            box.session(fixed, ["ZZA1S"])
            n0 = os.path.getsize(errlog) if os.path.exists(errlog) else 0
            os.chmod(d, 0o555)
            say("    zza1d is now mode %o" % (os.stat(d).st_mode & 0o7777))
            out = box.session(binary, ["ZZA1T", "LIST.READU"])
            os.chmod(d, 0o755)
            back = box.session(fixed, ["ZZA1R"])
            with open(errlog, errors="replace") as f:
                f.seek(n0)
                new = f.read()
            for l in new.splitlines():
                if l.strip():
                    say("      errlog| " + l.strip())
            return out, back, new

        out, back, new = txn_run(fixed)
        ck("A3.1 the commit fails out loud", "Delete error in transaction commit" in out and "ZZA1T.COMMIT.RETURNED" not in out)
        ck("A1.1 both DH writes are put back", "ZZA1R k1=OLDK1 k2=OLDK2 r1=OLDR1" in back)
        ck("A1.2 errlog names the undo", "3 record(s) restored" in new)
        say("    A1 lock half (NOT SCORED): LIST.READU after the failure said: %s"
            % ("no locks" if "There are no active" in out else "locks listed"))
        out, back, new = txn_run(mutA)
        ck("A1.1R RED: without the undo the commit is left half applied", "ZZA1R k1=NEWK1 k2=NEWK2 r1=OLDR1" in back)
        say("    A1 lock half on the mutant (NOT SCORED): %s" % ("no locks" if "There are no active" in out else "locks listed"))
        out, back, new = txn_run(mutB)
        ck("A3.1R RED: with a bare remove() the commit returns 0", "ZZA1T.COMMIT.RETURNED status=0" in out)
        ck("A3.2R RED: and the 'deleted' record is still there", "r1=OLDR1" in back)

        # ---- A5 --------------------------------------------------------------
        say("\n=== 5. A5: index node allocation failing under RLIMIT_FSIZE")
        box.session(fixed, ["ZZA5D", "CREATE.INDEX zza5 lkey", "ZZA5W 1 40", "BUILD.INDEX zza5 lkey"])
        base = box.session(fixed, ["ZZA5V"])
        ck("A5.0 baseline: 40 records, index exact", "ZZA5V data.records=40 index.missing=0 index.wrong=0" in base)
        snap = os.path.join(root, "zza5.base")
        shutil.copytree(os.path.join(box.acct, "zza5"), snap)
        ak = os.path.join(box.acct, "zza5", "%2")
        limit = os.path.getsize(ak) + 2 * 4096
        vocmax = max(os.path.getsize(os.path.join(box.acct, "voc", x)) for x in os.listdir(os.path.join(box.acct, "voc")))
        limit = max(limit, vocmax + 4096)
        say("    index subfile %%2 = %d bytes; largest voc subfile %d; limit %d" % (os.path.getsize(ak), vocmax, limit))
        found = {}
        for label, binary in (("fixed", fixed), ("mutant", mutA)):
            shutil.rmtree(os.path.join(box.acct, "zza5"))
            shutil.copytree(snap, os.path.join(box.acct, "zza5"))
            w = box.session(binary, ["ZZA5W 41 300"], limit=limit)
            v1 = box.session(fixed, ["ZZA5V"])
            w2 = box.session(fixed, ["ZZA5W 601 640"])
            v2 = box.session(fixed, ["ZZA5V"])
            m = re.search(r"ok=(\d+) failed=(\d+) first.status=(\d*)", w)
            found[label] = (m.groups() if m else None, v1, w2, v2)
        g, v1, w2, v2 = found["fixed"]
        ck("A5.1 writes past the limit were REPORTED, with 8506 (get_ak_node)", g is not None and int(g[1]) > 0 and g[2] == "8506", str(g))
        if g:
            ck("A5.2 the index misses exactly the reported failures, no wrong entries",
               ("index.missing=%s index.wrong=0" % g[1]) in v1)
            ck("A5.3 and keeps working: 40 more writes, still exact apart from those",
               "ok=40 failed=0" in w2 and ("index.missing=%s index.wrong=0" % g[1]) in v2)
        gm, mv1, mw2, mv2 = found["mutant"]
        say("    mutant reported %s; status %s where the fix gives 8506" % (str(gm), gm[2] if gm else "?"))
        # The first run of this script found the mutant did not finish 41..600
        # inside 120 s where the fix did at once.  Measured again here, bounded.
        hung = {}
        for label, binary in (("fixed", fixed), ("mutant", mutA)):
            shutil.rmtree(os.path.join(box.acct, "zza5"))
            shutil.copytree(snap, os.path.join(box.acct, "zza5"))
            t0 = time.time()
            w = box.session(binary, ["ZZA5W 41 600"], limit=limit, timeout=60)
            hung[label] = (w == "TIMEOUT")
            say("    %s, 41..600 under the limit: %s in %.1f s"
                % (label, "TIMEOUT" if hung[label] else "finished", time.time() - t0))
        ck("A5.4 the fix finishes 41..600 under the limit", not hung["fixed"])
        # RED, IN EITHER OF ITS TWO FORMS.  At some limits the mutant's
        # unchecked grow shows only as a different status; at others it loses
        # index entries it reported as written, keeps losing them after the
        # limit is lifted, or never finishes.  The first measured run (32768)
        # showed none of it and the next (33792) showed all three, so one of
        # them is required, not a particular one.
        silent = False
        if gm:
            mm = re.search(r"index.missing=(\d+)", mv1)
            silent = bool(mm) and int(mm.group(1)) != int(gm[1])
        mm2 = re.search(r"index.missing=(\d+)", mv2)
        mm1 = re.search(r"index.missing=(\d+)", mv1)
        drift = bool(mm1 and mm2) and int(mm2.group(1)) != int(mm1.group(1))
        say("    mutant: silent index loss=%s, loss after the limit lifted=%s, hang=%s" % (silent, drift, hung["mutant"]))
        ck("A5.R RED: without the grow check the index is damaged or the write never finishes",
           silent or drift or hung["mutant"])
        say("    A5 UNEXERCISED: the free-node read-failure path (the double-allocation damage) needs a transient read error.")
    finally:
        say("\n=== teardown")
        try:
            box.stop()
        except Exception as e:
            say("    stop: %s" % e)
        left = ipcs_keys()
        for k, flag in zip(BOX_KEYS, ("-M", "-S")):
            if k in left:
                sh(["ipcrm", flag, k])
                say("    ipcrm %s %s" % (flag, k))
        final = ipcs_keys()
        say("  IPC keys after teardown: %s" % " ".join(final))
        ck("T0 no sandbox key is left and the live keys are as they were",
           not any(k in final for k in BOX_KEYS) and all((k in final) == (k in before) for k in LIVE_KEYS))
        if not a.keep:
            for dirpath, dirnames, files in os.walk(root):
                for n in dirnames + files:
                    try:
                        os.chmod(os.path.join(dirpath, n), 0o755)
                    except OSError:
                        pass
            shutil.rmtree(root, ignore_errors=True)
            say("  removed %s" % root)

    say("\n  passed: %d   failed: %d" % (PASS, FAIL))
    if PASS == 0:
        say("sandbox-txnfail: FAILED - no row ran.")
        return 1
    if FAIL:
        say("sandbox-txnfail: FAILED - %d row(s)." % FAIL)
        return 1
    say("sandbox-txnfail: PASSED - every decisive row passed on the fix and went red on its mutant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
