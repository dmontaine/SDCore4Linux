#!/usr/bin/env python3
#
# sandbox-stmt-q3.py - QM4 gaps, the 15 Oct 26 second sitting: DIGEST() (Q-13), SET.TIMEZONE and the TIMEZONE parameter
#                      (Q-3, Q-19), KEEP.SELECT (Q-2), FIND.FILE, FIND.PROGRAM and COMMAND.LOGGING (Q-8), the USPLIT
#                      parameter (Q-19) and SYSTEM(20) (Q-18).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-stmt-q3.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 15 Oct 26 dm  Written for QM4 gaps bundles Q-13 (DIGEST), Q-3 / Q-19 (SET.TIMEZONE, TIMEZONE) and Q-2 (KEEP.SELECT).
# END-HISTORY
#
# THE INSTRUMENT.  Sessions are real: bin/sd with a pipe on stdin, ordinary ones in a fixture account (no -internal,
# SDTEST_ADMIN unset: CPROC is patched as sandbox-inhibit-q8.py and sandbox-gates.py patch it, so that the sandbox user is
# the administrator only when asked) and an administrator one for the rows that need it.  The EXPECTED values are not typed
# in by hand where a program can say them: Python's hashlib digests the file the probe made, and zoneinfo converts the
# epoch value in the zone, so a wrong answer in SD cannot agree with them by construction.
#
#   A  DIGEST: the published test vectors of every mode, lower case mode, MD5() as the control, what it refuses (MD4 and
#      unknown modes, a missing file, a directory, a file outside the account), the file case against hashlib for a small
#      and a 3 MB file, the administrator reading the file the account cannot, 2000 calls in a loop
#   B  SET.TIMEZONE / CONFIG TIMEZONE: the epoch functions in two zones against zoneinfo, MVEPOCH as the inverse, DATE() and
#      TIME() not moved, a refused name leaves the setting, the null string goes back, the CONFIG verb sets it
#   C  KEEP.SELECT: with OPTION CLEAR.SELECT a program that leaves list 0 active has it cleared at the end of its command;
#      with KEEP.SELECT it is left; without CLEAR.SELECT it is left either way; the flag belongs to one command
#   E  FIND.FILE and FIND.PROGRAM against FILEINFO and !PROG_INFO, which read the same things by another road
#   F  COMMAND.LOGGING: the file's mode, owner and lines, the origins, a link left in its place, TEMPDIR
#   G  ANALYSE.INDEX against the figures of a file whose index values are known, and against LIST.INDEX
#   H  SET.MODE: the permission bits on the disk (stat), every way of naming records, the modes it refuses, a record that
#      is a link, a file that is not a directory file
#   I  MATWRITECSV: the lines the statement writes, read back from the disk, and the ELSE of a file opened read only
#   D  USPLIT=1 (sd.conf, the sandbox is restarted): the user number an interactive session and a phantom get, with the
#      plain rotation as the control; SYSTEM(20), the count of print jobs passed to the spooler (SPOOLER=true, so nothing
#      is printed), and that it is the system's count

import datetime
import getpass
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import zoneinfo

os.environ["TZ"] = "Asia/Kathmandu"          # +05:45: a conversion done in UTC or in a whole-hour zone is wrong by a visible amount

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
USER = getpass.getuser()
GROUP = subprocess.run(["id", "-gn"], capture_output=True, text=True).stdout.strip()
passed = failed = 0
BOX = SYS = SD = None


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
    say("sandbox-stmt-q3: CANNOT RUN - " + msg)
    sys.exit(2)


def env(admin):
    e = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"))
    e.pop("SSH_CONNECTION", None)
    e.pop("SSH_TTY", None)
    if admin:
        e["SDTEST_ADMIN"] = "1"
    else:
        e.pop("SDTEST_ADMIN", None)
    return e


def sd(cwd, cmds, admin=False, internal=False, account=None):
    """Run sd with the commands on stdin; return the lines it printed after the TERM line, echoed commands removed.
    Prints the real inputs: the working directory, the flags and the commands."""
    argv = [SD] + (["-internal"] if internal else []) + (["-a" + account] if account else [])
    say("    > %s%s%s in %s: %s" % ("[admin] " if admin else "", "[internal] " if internal else "",
                                    ("-a" + account + " ") if account else "", os.path.relpath(cwd, BOX), " | ".join(cmds)))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run(argv, input=body, cwd=cwd, env=env(admin), capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip() for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


def plain(acct, cmds):
    return sd(os.path.join(BOX, "user_accounts", acct), cmds, account=acct)


def adm(cmds, internal=False):
    return sd(SYS, cmds, admin=True, internal=internal)


MARK = "# --- sandbox-stmt-q3 below ---"
lives = []


class Live:
    """An administrator's session on a pipe kept open (hold=True), in the SDSYS account."""

    def __init__(self, tag, cmds, admin=True, hold=False):
        self.out = os.path.join(BOX, "live-%s.out" % tag)
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([SD], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=SYS, env=env(admin), text=True)
        self.p.stdin.write("\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + ("" if hold else "OFF\n"))
        self.p.stdin.flush()
        say("    > live %s [admin]: %s" % (tag, " | ".join(cmds)))
        lives.append(self)

    def text(self):
        self.fh.flush()
        return ANSI.sub("", open(self.out, errors="replace").read())

    def wait_for(self, pattern, seconds=30):
        end = time.time() + seconds
        while time.time() < end:
            if re.search(pattern, self.text()):
                return True
            time.sleep(0.3)
        return False

    def wait(self, seconds):
        try:
            self.p.wait(timeout=seconds)
            return True
        except subprocess.TimeoutExpired:
            return False

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


def restart(*extra):
    """Stop the sandbox, put `extra` lines in sd.conf below the marker (none: the file as built), start it, say whether SD runs."""
    conf = os.path.join(BOX, "sd.conf")
    subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    with open(conf) as f:
        base = f.read().split(MARK)[0].rstrip("\n") + "\n"
    with open(conf, "w") as f:
        f.write(base + ((MARK + "\n" + "".join(l + "\n" for l in extra)) if extra else ""))
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=180)
    p = subprocess.run([SD, "-status"], capture_output=True, text=True, errors="replace", env=env(False), timeout=60)
    ok = re.search(r"(?m)^Started\s+20\d\d-", p.stdout + p.stderr) is not None
    say("  -- sd.conf %s: SD %s" % (("+ " + " ".join(extra)) if extra else "as built", "started" if ok else "NOT STARTED"))
    return ok


def has(lines, pattern):
    return any(re.search(pattern, ln) for ln in lines)


def put(path, text):
    with open(path, "w", encoding="ascii") as f:
        f.write(text)


def tag(lines, name):
    """The text inside NAME[...] on lines that start with it (every one, in order)."""
    out = []
    for ln in lines:
        m = re.match(r"^%s\[(.*)\]\s*$" % re.escape(name), ln)
        if m:
            out.append(m.group(1))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The probes: the same user programs in the fixture account's bp and in SDSYS's.

MODES = ["MD5", "SHA1", "SHA256", "SHA384", "SHA512"]

USER_PROGS = {
    # A: the published vectors for "abc" in each mode, the empty string, a lower case mode, a string with marks against MD5()
    "zzdg1": ("   modes = 'MD5':@fm:'SHA1':@fm:'SHA256':@fm:'SHA384':@fm:'SHA512'\n"
              "   for i = 1 to 5\n      crt 'V':i:'[':digest('abc', @false, modes<i>):'][':status():']'\n   next i\n"
              "   crt 'E[':digest('', @false, 'MD5'):']'\n"
              "   crt 'L[':digest('abc', @false, 'sha256'):']'\n"
              "   crt 'M[':digest('x':@vm:'y':@fm:'z':@sm:'w', @false, 'MD5'):'][':md5('x':@vm:'y':@fm:'z':@sm:'w'):']'\n"
              "   crt 'B4[':digest('abc', @false, 'MD4'):'][':status():']'\n"
              "   crt 'B5[':digest('abc', @false, 'ROT13'):'][':status():']'\n"
              "   crt 'B6[':digest('abc', @false, ''):'][':status():']'\n"
              # a null result with status 0 must not be possible: a good call right after a bad one clears STATUS
              "   crt 'AFTER[':digest('abc', @false, 'MD5'):'][':status():']'\n"
              "   n = 0\n   for i = 1 to 2000\n      if digest(i, @false, 'MD5') # '' then n += 1\n   next i\n"
              "   crt 'LOOP[':n:']'\n   crt 'D1DONE'\nend\n"),
    # the file case: the pathname is the fourth word of the command
    "zzdgf": ("   path = field(@sentence, ' ', 4)\n"
              "   modes = 'MD5':@fm:'SHA1':@fm:'SHA256':@fm:'SHA384':@fm:'SHA512'\n"
              "   for i = 1 to 5\n      crt 'F':i:'[':digest(path, @true, modes<i>):'][':status():']'\n   next i\n"
              "   crt 'FDONE'\nend\n"),
    # B: the epoch functions in the zone in force, and what SET.TIMEZONE refuses
    "zztz": ("   e = 1234567890\n"
             "   crt 'Z0[':config('TIMEZONE'):']'\n"
             "   crt 'A[':mvdate(e):'][':mvtime(e):'][':mvepoch(mvdate(e), mvtime(e)):']'\n"
             "   set.timezone 'America/Los_Angeles'\n"
             "   st = status()\n"
             "   crt 'ST1[':st:']'\n"
             "   crt 'Z1[':config('TIMEZONE'):']'\n"
             "   crt 'B[':mvdate(e):'][':mvtime(e):'][':mvepoch(mvdate(e), mvtime(e)):']'\n"
             "   crt 'BD[':mvdate.time(e):'][':mvepoch(mvdate.time(e)):']'\n"
             "   t1 = time()\n   set.timezone 'Pacific/Wake'\n   t2 = time()\n"
             "   crt 'CLOCK[':(abs(t2 - t1) < 5):']'\n"
             "   crt 'C[':mvdate(e):'][':mvtime(e):']'\n"
             "   set.timezone 'GMT'\n   crt 'G[':mvdate(e):'][':mvtime(e):'][':config('TIMEZONE'):']'\n"
             "   bad = 'Mars/Olympus':@fm:'../../etc/passwd':@fm:'/etc/passwd':@fm:':/etc/passwd':@fm:'UTC+3':@fm:'America/../Asia/Tokyo'\n"
             "   bad := @fm:'Asia/Tokyo ':@fm:'EST5EDT,M3.2.0,M11.1.0'\n"
             "   for i = 1 to dcount(bad, @fm)\n"
             "      set.timezone bad<i>\n"
             "      st = status()                    ;* before CONFIG(), which sets STATUS() itself\n"
             "      crt 'BAD':i:'[':config('TIMEZONE'):'][':st:']'\n"
             "   next i\n"
             "   set.timezone 'Europe/London'\n   st = status()\n   crt 'OLD[':config('TIMEZONE'):'][':st:']'\n"
             "   set.timezone ''\n   crt 'RESET[':config('TIMEZONE'):'][':mvdate(e):'][':mvtime(e):']'\n"
             "   crt 'TZDONE'\nend\n"),
    "zztzc": ("   e = 1234567890\n   crt 'TC[':config('TIMEZONE'):'][':mvdate(e):'][':mvtime(e):']'\nend\n"),
    # D: USPLIT and SYSTEM(20).  zzun: the number this session has, NUMUSERS and USPLIT; zzphl: start a phantom and say the user
    # number IT had (it writes @USERNO to a record in bp); zzspl: two print jobs to the spooler, SYSTEM(20) before and after each
    "zzun": "   crt 'UNO[':@userno:'][':config('NUMUSERS'):'][':config('USPLIT'):']'\nend\n",
    "zzphd": "   open 'bp' to f else stop\n   write @userno to f, 'zzphun'\nend\n",
    "zzphl": ("   open 'bp' to f else stop 'no bp'\n   delete f, 'zzphun'\n"
              "   execute 'PHANTOM NO.MSG RUN bp zzphd' capturing j\n"
              "   t = 0\n   loop\n      read r from f, 'zzphun' then exit\n      t += 1\n   until t >= 150\n      nap 100\n   repeat\n"
              "   crt 'PHUNO[':r:']'\nend\n"),
    "zzspl": ("   a = system(20)\n   execute 'SETPTR 0,80,60,0,1' capturing j\n   printer on\n   print 'hello'\n   printer close\n"
              "   b = system(20)\n   crt 'JOBS[':a:'][':b:']'\n   crt 'END'\nend\n"),
    # E: FIND.FILE and FIND.PROGRAM.  zzfi: what FILEINFO says of a file and its dictionary (the oracle for FIND.FILE); zzfps: a
    # subroutine of two arguments to catalogue; zzfpi: what !PROG_INFO (older, used by other verbs) reads from its object
    "zzfi": ("   open 'zzefdyn' to f else stop 'no f'\n"
             "   crt 'FI[':fileinfo(f, 7):'][':fileinfo(f, 5):'][':fileinfo(f, 2):'][':fileinfo(f, 1008):']'\n"
             "   open 'DICT', 'zzefdyn' to d else stop 'no d'\n   crt 'FD[':fileinfo(d, 2):']'\nend\n"),
    "zzfps": "subroutine zzfps(a, b)\n   a = b\n   return\nend\n",
    "zzfpi": ("   call !prog_info(@path:@ds:'cat', 'zzfps', pn, sz, tm, dt, err)\n"
              "   crt 'PI[':dt:'][':tm:'][':sz:'][':err:']'\nend\n"),
    # F: COMMAND.LOGGING.  zzin is a program to run as a command; zzex runs a command from inside a program (origin Exec);
    # zzmkpa makes a paragraph in the VOC
    "zzin": "   crt 'IN[':@who:']'\nend\n",
    "zzex": "   execute 'DATE'\nend\n",
    "zzmkpa": "   write 'PA':@fm:'TIME':@fm:'DATE' to @voc, 'zzpara'\nend\n",
    # G: ANALYSE.INDEX.  zzaisu fills file zzaix: ten records, the city Paris five times, Rome three, Oslo and Lima once
    "zzaisu": ("   open 'zzaix' to f else stop 'no file'\n   open 'DICT zzaix' to d else stop 'no dict'\n"
               "   write 'D':@fm:'1':@fm:'':@fm:'City':@fm:'12L':@fm:'S' on d, 'CITY'\n"
               "   cities = 'Paris':@fm:'Paris':@fm:'Paris':@fm:'Paris':@fm:'Paris':@fm:'Rome':@fm:'Rome':@fm:'Rome':@fm:'Oslo':@fm:'Lima'\n"
               "   for i = 1 to 10\n      write cities<i> on f, 'r':i\n   next i\nend\n"),
    # H: SET.MODE.  zzsmmk fills the directory file zzsmdir with three records
    "zzsmmk": ("   open 'zzsmdir' to f else stop 'no file'\n   write 'one' on f, 'a'\n   write 'two' on f, 'b'\n"
               "   write 'three' on f, 'c'\nend\n"),
    # I: MATWRITECSV.  Three matrices written as lines to one sequential file, then the file opened read only for the ELSE path
    "zzmwc": ("   dim m(2,2)\n   dim v(3)\n   dim w(1)\n"
              "   m(1,1) = 'a' ; m(1,2) = 'b,c' ; m(2,1) = 'say \"hi\"' ; m(2,2) = ''\n"
              "   v(1) = 1 ; v(2) = 22 ; v(3) = 'x y'\n   w(1) = ''\n"
              "   openseq 'zzmwc.csv' to f else create f else stop 'no create'\n   weofseq f\n"
              "   matwritecsv m to f then crt 'M1[1]' else crt 'M1[0]'\n"
              "   matwritecsv v on f then crt 'M2[1]' else crt 'M2[0]'\n"
              "   matwritecsv w to f then crt 'M3[1]' else crt 'M3[0]'\n"
              "   closeseq f\n"
              "   openseq 'zzmwc.csv' readonly to g else stop 'no readonly open'\n"
              "   matwritecsv v to g then crt 'M4[1]' else crt 'M4[0]'\n"
              "   closeseq g\n   crt 'MWCDONE'\nend\n"),
    # C: KEEP.SELECT.  zzmk makes list 0 (a, b, c); zzp1 takes one id; zzp2 takes one and says KEEP.SELECT; zzdr drains list 0
    "zzmk": "   formlist 'a':@fm:'b':@fm:'c' to 0\nend\n",
    "zzp1": "   readnext x from 0 else x = 'NONE'\n   crt 'P1[':x:']'\nend\n",
    "zzp2": "   readnext x from 0 else x = 'NONE'\n   crt 'P2[':x:']'\n   keep.select\nend\n",
    "zzdr": ("   ids = ''\n   loop\n      readnext id from 0 else exit\n      ids<-1> = id\n   repeat\n"
             "   crt 'LEFT[':change(ids, @fm, ','):']'\nend\n"),
}


def prepare():
    """A CPROC that is not the install build, so the sandbox user is the administrator only when SDTEST_ADMIN=1."""
    path = os.path.join(SYS, "gpl.bp", "cproc")
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    old = "if downcase(kernel(K$USERNAME, 0)) = '%s' and env('SSH_CONNECTION') = ''" % USER
    new = "if downcase(kernel(K$USERNAME, 0)) = '%s' and env('SDTEST_ADMIN') = '1' and env('SSH_CONNECTION') = ''" % USER
    if "SDTEST_ADMIN" not in text:
        if text.count(old) != 1:
            bail("the sandbox CPROC does not have the one elevation test this suite patches (%d matches)" % text.count(old))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))
    put(os.path.join(SYS, "gpl.bp", "define_install.h"), "*comment out * $define IS_INSTALL\n")
    out = adm(["BASIC gpl.bp cproc"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("CPROC did not recompile in the sandbox:\n" + "\n".join(out[-8:]))


def build_account(name):
    path = os.path.join(BOX, "user_accounts", name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(os.path.join(path, "sub"))
    put(os.path.join(SYS, "bp", "zzfix"), "\n".join([
        "$internal",
        "   acct = '%s'" % path,
        "   create.file acct:'/voc' dynamic on error crt 'FIX create voc failed' ; stop",
        "   openpath acct:'/voc' to v else crt 'FIX open voc failed' ; stop",
        "   openpath '%s/newvoc' to nv else crt 'FIX no newvoc' ; stop" % SYS,
        "   select nv to 11",
        "   loop",
        "      readnext id from 11 else exit",
        "      read rec from nv, id then write rec to v, id",
        "   repeat",
        "   write 'X' to v, '$command.stack'",
        "   create.file acct:'/bp' directory on error crt 'FIX bp failed' ; stop",
        "   write 'F':@fm:'bp' to v, 'bp'",
        "   create.file acct:'/cat' directory on error crt 'FIX cat failed' ; stop",
        "   crt 'FIX done ':'%s'" % name,
        "end", ""]))
    out = adm(["BASIC bp zzfix", "RUN bp zzfix"], internal=True)
    if not has(out, r"^FIX done " + name + "$"):
        bail("the fixture account %s was not built:\n%s" % (name, "\n".join(out[-6:])))
    put(os.path.join(SYS, "accounts", name), "\n".join([path, "", GROUP, "", "", "", "", ""]) + "\n")
    for nm, text in USER_PROGS.items():
        put(os.path.join(path, "bp", nm), text)
    out = plain(name, ["BASIC bp " + " ".join(USER_PROGS)])
    if not has(out, r"^Compiled %d program\(s\) with no errors" % len(USER_PROGS)):
        bail("the user probes did not compile in %s:\n%s" % (name, "\n".join(out[-8:])))
    return path


def mvdate_time(epoch, zone):
    """The internal date and the seconds since midnight of an epoch value in a zone, from zoneinfo."""
    dt = datetime.datetime.fromtimestamp(epoch, zoneinfo.ZoneInfo(zone))
    days = (dt.date() - datetime.date(1967, 12, 31)).days
    secs = dt.hour * 3600 + dt.minute * 60 + dt.second
    return days, secs


def main():
    global BOX, SYS, SD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-stmt-q3.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    say("sandbox-stmt-q3: sandbox  %s" % BOX)
    say("sandbox-stmt-q3: user %s, group %s, TZ %s" % (USER, GROUP, os.environ["TZ"]))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-stmt-q3: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, one fixture account, the probes -------------------------")
    prepare()
    acct = build_account("zzaa")
    for nm, text in USER_PROGS.items():
        put(os.path.join(SYS, "bp", nm), text)
    out = adm(["BASIC bp " + " ".join(USER_PROGS)])
    if not has(out, r"^Compiled %d program\(s\) with no errors" % len(USER_PROGS)):
        bail("the probes did not compile in the SDSYS account:\n" + "\n".join(out[-8:]))
    say("  [done] account zzaa, the probes in it and in SDSYS")

    # the files whose digests are asked for: inside the account (small, 3 MB, a directory) and one outside it
    small = os.path.join(acct, "zzdg.dat")
    big = os.path.join(acct, "zzdgbig.dat")
    outside = os.path.join(BOX, "zzoutside.dat")
    with open(small, "wb") as f:
        f.write(b"abc\n\xfe\xfd\x00binary \xff\n")
    with open(big, "wb") as f:
        f.write(bytes((i * 7 + 3) & 0xFF for i in range(3 * 1024 * 1024 + 17)))
    with open(outside, "wb") as f:
        f.write(b"outside the account, readable by the administrator only\n")
    os.makedirs(os.path.join(acct, "zzdgdir"), exist_ok=True)

    try:
        # -------------------------------------------------------------------------------------------------------------
        say("\n--- A. DIGEST() -------------------------------------------------------------------------------------------")
        out = plain("zzaa", ["RUN bp zzdg1"])
        vec = {
            "MD5": "900150983cd24fb0d6963f7d28e17f72",
            "SHA1": "a9993e364706816aba3e25717850c26c9cd0d89d",
            "SHA256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "SHA384": "cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7",
            "SHA512": ("ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd45"
                       "4d4423643ce80e2a9ac94fa54ca49f"),
        }
        for i, mode in enumerate(MODES, 1):
            row("A1: DIGEST('abc', false, '%s') is the published vector (and STATUS() is 0)" % mode,
                tag(out, "V%d" % i) == ["%s][0" % vec[mode]], repr(tag(out, "V%d" % i)))
        row("A1: the empty string's MD5 (d41d8cd9...)", tag(out, "E") == ["d41d8cd98f00b204e9800998ecf8427e"], repr(tag(out, "E")))
        row("A1: the mode in lower case is the same mode", tag(out, "L") == [vec["SHA256"]], repr(tag(out, "L")))
        mm = tag(out, "M")
        row("A1: CONTROL: a string with field, value and subvalue marks: DIGEST MD5 equals MD5()",
            len(mm) == 1 and re.match(r"^[0-9a-f]{32}\]\[[0-9a-f]{32}$", mm[0]) is not None and mm[0].split("][")[0] == mm[0].split("][")[1],
            repr(mm))
        row("A2: MD4 is refused: a null string and STATUS() 1", tag(out, "B4") == ["][1"], repr(tag(out, "B4")))
        row("A2: an unknown mode is refused the same way", tag(out, "B5") == ["][1"], repr(tag(out, "B5")))
        row("A2: so is a null mode", tag(out, "B6") == ["][1"], repr(tag(out, "B6")))
        row("A2: a good call after the bad ones gives the digest and STATUS() 0 again", tag(out, "AFTER") == ["%s][0" % vec["MD5"]],
            repr(tag(out, "AFTER")))
        row("A3: 2000 calls in a loop all answer (the stack stays in step), and the program ends", tag(out, "LOOP") == ["2000"] and
            has(out, r"^D1DONE$"), repr(out[-4:]))

        # the file case, against hashlib on the bytes Python wrote
        def want(path, mode):
            h = hashlib.new(mode.lower())
            with open(path, "rb") as f:
                h.update(f.read())
            return h.hexdigest()

        out = plain("zzaa", ["RUN bp zzdgf zzdg.dat"])
        row("A4: a file in the account, every mode, equals hashlib's digest of the bytes (binary content, marks and a null)",
            all(tag(out, "F%d" % i) == ["%s][0" % want(small, m)] for i, m in enumerate(MODES, 1)),
            repr([tag(out, "F%d" % i) for i in range(1, 6)]))
        out = plain("zzaa", ["RUN bp zzdgf zzdgbig.dat"])
        row("A4: a 3 MB file (read in blocks), every mode, equals hashlib's",
            all(tag(out, "F%d" % i) == ["%s][0" % want(big, m)] for i, m in enumerate(MODES, 1)),
            repr([tag(out, "F%d" % i) for i in range(1, 6)])[:300])
        out = plain("zzaa", ["RUN bp zzdgf zzmissing.dat"])
        row("A5: a file that is not there: a null string and STATUS() 3003 (file not found)", tag(out, "F3") == ["][3003"], repr(tag(out, "F3")))
        out = plain("zzaa", ["RUN bp zzdgf zzdgdir"])
        row("A5: a directory is not a file: a null string and STATUS() 1008 (action failed)", tag(out, "F3") == ["][1008"], repr(tag(out, "F3")))
        out = plain("zzaa", ["RUN bp zzdgf " + outside])
        row("A6: a file OUTSIDE the account, for an account without the OS gate: a null string and STATUS() 3035 (permissions), "
            "and no digest of it appears anywhere in the output",
            tag(out, "F3") == ["][3035"] and want(outside, "SHA256") not in "\n".join(out), repr(tag(out, "F3")))
        out = plain("zzaa", ["RUN bp zzdgf ../../../../../../etc/hostname"])
        row("A6: ... and a path that climbs out of it with .. is refused the same way", tag(out, "F3") == ["][3035"], repr(tag(out, "F3")))
        link = os.path.join(acct, "zzdglink")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(outside, link)
        out = plain("zzaa", ["RUN bp zzdgf zzdglink"])
        row("A6: ... and a symbolic link inside the account that points out of it (the gate resolves it)", tag(out, "F3") == ["][3035"],
            repr(tag(out, "F3")))
        os.remove(link)
        out = adm(["RUN bp zzdgf " + outside])
        row("A7: CONTROL: the administrator (the gate is open) gets the digests of the same file, equal to hashlib's",
            all(tag(out, "F%d" % i) == ["%s][0" % want(outside, m)] for i, m in enumerate(MODES, 1)),
            repr([tag(out, "F%d" % i) for i in range(1, 6)]))

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- B. SET.TIMEZONE and the TIMEZONE parameter --------------------------------------------------------------")
        e = 1234567890
        out = plain("zzaa", ["RUN bp zztz"])
        kd, ks = mvdate_time(e, "Asia/Kathmandu")
        ld, ls = mvdate_time(e, "America/Los_Angeles")
        wd, ws = mvdate_time(e, "Pacific/Wake")
        gd, gs = mvdate_time(e, "GMT")
        row("B1: with nothing set, CONFIG('TIMEZONE') is the process's own TZ (the session runs with TZ=Asia/Kathmandu)",
            tag(out, "Z0") == ["Asia/Kathmandu"], repr(tag(out, "Z0")))
        row("B1: ... and MVDATE / MVTIME of %d are Kathmandu's (%d, %d) and MVEPOCH is the inverse" % (e, kd, ks),
            tag(out, "A") == ["%d][%d][%d" % (kd, ks, e)], repr(tag(out, "A")))
        row("B2: SET.TIMEZONE 'America/Los_Angeles': CONFIG says so and STATUS() is 0",
            tag(out, "Z1") == ["America/Los_Angeles"] and tag(out, "ST1") == ["0"], repr(tag(out, "Z1")) + repr(tag(out, "ST1")))
        row("B2: ... the epoch functions answer in that zone: (%d, %d) against zoneinfo, and MVEPOCH gives the epoch value back" % (ld, ls),
            tag(out, "B") == ["%d][%d][%d" % (ld, ls, e)], repr(tag(out, "B")))
        row("B2: ... MVDATE.TIME is that zone's and MVEPOCH of it is the epoch value again",
            tag(out, "BD") == ["%d_%d][%d" % (ld, ls, e)], repr(tag(out, "BD")))
        row("B3: DATE() and TIME() are NOT moved by it: the clock read either side of a SET.TIMEZONE agrees",
            tag(out, "CLOCK") == ["1"], repr(tag(out, "CLOCK")))
        row("B4: a second zone replaces the first: Pacific/Wake (%d, %d)" % (wd, ws), tag(out, "C") == ["%d][%d" % (wd, ws)], repr(tag(out, "C")))
        row("B4: ... and GMT (%d, %d), which is not a file of the zoneinfo directory on every machine, is always accepted" % (gd, gs),
            tag(out, "G") == ["%d][%d][GMT" % (gd, gs)], repr(tag(out, "G")))
        bads = {1: "Mars/Olympus", 2: "../../etc/passwd", 3: "/etc/passwd", 4: ":/etc/passwd", 5: "UTC+3",
                6: "America/../Asia/Tokyo", 7: "Asia/Tokyo (trailing space)", 8: "a POSIX rule string"}
        for i, nm in bads.items():
            row("B5: %r is refused: STATUS() 2, and the zone is still GMT" % nm, tag(out, "BAD%d" % i) == ["GMT][2"], repr(tag(out, "BAD%d" % i)))
        row("B6: a name that is a real zoneinfo file (Europe/London) is taken after the refusals, STATUS() 0",
            tag(out, "OLD") == ["Europe/London][0"], repr(tag(out, "OLD")))
        row("B7: the null string goes back to the process's own zone: CONFIG says Asia/Kathmandu and the epoch functions are Kathmandu's",
            tag(out, "RESET") == ["Asia/Kathmandu][%d][%d" % (kd, ks)], repr(tag(out, "RESET")))
        row("B8: the program ends (the statement leaves the stack in step)", has(out, r"^TZDONE$"), repr(out[-3:]))

        # the CONFIG verb is the administrator's (NEWVOC does not carry it), so these three run in the SDSYS account
        out = adm(["CONFIG TIMEZONE Asia/Tokyo", "RUN bp zztzc"])
        td, ts = mvdate_time(e, "Asia/Tokyo")
        row("B9: CONFIG TIMEZONE Asia/Tokyo sets it for the session (the epoch functions are Tokyo's: %d, %d)" % (td, ts),
            tag(out, "TC") == ["Asia/Tokyo][%d][%d" % (td, ts)], repr(tag(out, "TC")) + repr(out[-4:]))
        out = adm(["CONFIG TIMEZONE Mars/Olympus"])
        row("B9: ... and the CONFIG verb refuses a zone the machine does not have (Invalid value for this parameter)",
            has(out, r"Invalid value for this parameter"), repr(out[-3:]))
        out = adm(["RUN bp zztzc"])
        row("B10: the setting belongs to the session: the next session is back in its own zone",
            tag(out, "TC") == ["Asia/Kathmandu][%d][%d" % (kd, ks)], repr(tag(out, "TC")))
        out = adm(["CONFIG"])
        row("B11: the CONFIG listing shows the TIMEZONE line", has(out, r"^TIMEZONE\s+Asia/Kathmandu$"), repr([l for l in out if "TIME" in l]))

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- C. KEEP.SELECT -------------------------------------------------------------------------------------------")
        out = plain("zzaa", ["RUN bp zzmk", "RUN bp zzp1", "RUN bp zzdr"])
        row("C0: CONTROL: with no OPTION, a program that takes one id and ends leaves the rest: list 0 holds b, c",
            tag(out, "P1") == ["a"] and tag(out, "LEFT") == ["b,c"], repr(out[-5:]))
        out = plain("zzaa", ["OPTION CLEAR.SELECT", "RUN bp zzmk", "RUN bp zzp1", "RUN bp zzdr"])
        row("C1: THE ROW: with OPTION CLEAR.SELECT the same program's command ends with list 0 cleared", tag(out, "P1") == ["a"] and
            tag(out, "LEFT") == [""], repr(out[-5:]))
        out = plain("zzaa", ["OPTION CLEAR.SELECT", "RUN bp zzmk", "RUN bp zzp2", "RUN bp zzdr"])
        row("C2: ... and when the program says KEEP.SELECT the list is left: b, c", tag(out, "P2") == ["a"] and
            tag(out, "LEFT") == ["b,c"], repr(out[-5:]))
        out = plain("zzaa", ["RUN bp zzmk", "RUN bp zzp2", "RUN bp zzdr"])
        row("C3: without CLEAR.SELECT, KEEP.SELECT does nothing the list was not already doing: b, c", tag(out, "LEFT") == ["b,c"], repr(out[-5:]))
        out = plain("zzaa", ["OPTION CLEAR.SELECT", "RUN bp zzmk", "RUN bp zzp2", "RUN bp zzp1", "RUN bp zzdr"])
        row("C4: the flag belongs to one command: a KEEP.SELECT in one command does not protect the list from the next "
            "(b is taken by the second program, which does not keep it, and c is cleared)",
            tag(out, "P2") == ["a"] and tag(out, "P1") == ["b"] and tag(out, "LEFT") == [""], repr(out[-6:]))
        out = plain("zzaa", ["OPTION CLEAR.SELECT", "RUN bp zzmk", "RUN bp zzdr"])
        row("C5: CONTROL: a list the command made itself is kept by CLEAR.SELECT, as ever (a, b, c)", tag(out, "LEFT") == ["a,b,c"], repr(out[-4:]))

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- E. FIND.FILE and FIND.PROGRAM -----------------------------------------------------------------------------")
        out = plain("zzaa", ["CREATE.FILE zzefdyn", "RUN bp zzfi", "FIND.FILE zzefdyn"])
        fi = tag(out, "FI")
        m = re.match(r"^(\d+)\]\[(\d+)\]\[(.*)\]\[([01])$", fi[0]) if len(fi) == 1 else None
        row("E0: setup: a dynamic file made and FILEINFO read for it (the oracle)", m is not None, repr(fi))
        if m:
            grp, mod, path, nocase = m.groups()
            row("E1: FIND.FILE of a dynamic file: 'Dynamic hashed file, group size %s, modulus %s' (FILEINFO's own numbers)" % (grp, mod),
                has(out, r"^Dynamic hashed file, group size %s, modulus %s$" % (grp, mod)), repr(out[-6:]))
            row("E1: ... and 'Pathname: %s'" % path, has(out, r"^Pathname: %s$" % re.escape(path)), repr(out[-6:]))
            row("E2: ... 'File uses case insensitive record ids' is shown exactly when FILEINFO says it is (%s)" % nocase,
                has(out, r"^File uses case insensitive record ids$") == (nocase == "1"), repr(out[-6:]))
        dpath = tag(out, "FD")
        out = plain("zzaa", ["FIND.FILE DICT zzefdyn"])
        row("E3: FIND.FILE DICT reports the dictionary: its pathname is FILEINFO's for the dictionary (%s)" % dpath,
            len(dpath) == 1 and has(out, r"^Pathname: %s$" % re.escape(dpath[0])), repr(out[-5:]))
        out = plain("zzaa", ["FIND.FILE bp"])
        row("E4: a directory file: 'Directory file' and its pathname", has(out, r"^Directory file$") and has(out, r"^Pathname: .*/bp$"), repr(out[-5:]))
        out = plain("zzaa", ["FIND.FILE zznosuchfile"])
        row("E5: a name that is not in the VOC is said so", has(out, r"zznosuchfile is not defined in your VOC"), repr(out[-3:]))
        out = plain("zzaa", ["FIND.FILE"])
        row("E5: no name at all is refused (Invalid file name)", has(out, r"^Invalid file name"), repr(out[-3:]))
        out = plain("zzaa", ["FIND.FILE zzefdyn zzextra"])
        row("E5: a word too many is refused (Unexpected token)", has(out, r"Unexpected token \(zzextra\)"), repr(out[-3:]))
        plain("zzaa", ["DELETE.FILE zzefdyn"])

        out = plain("zzaa", ["BASIC bp zzfps", "CATALOG bp zzfps", "FIND.PROGRAM zzfps", "RUN bp zzfpi"])
        pi = tag(out, "PI")
        # PI[date][time][size][err] comes back as "date][time][size][" from tag(): err is null
        mp = re.match(r"^([^\]]+)\]\[([^\]]+)\]\[(\d+)\]\[$", pi[0]) if len(pi) == 1 else None
        row("E6: setup: the subroutine is catalogued and !PROG_INFO reads its date, time and object size (the oracle)",
            mp is not None, repr(pi) + repr(out[-8:]))
        row("E6: FIND.PROGRAM of it: 'Program is in the private catalogue', 'Subroutine with 2 arguments'",
            has(out, r"^Program is in the private catalogue$") and has(out, r"^\s+Subroutine with 2 arguments$"), repr(out[-8:]))
        if mp:
            dt, tm, size = mp.groups()
            # !PROG_INFO gives the time as 12 hour "08:56pm"; FIND.PROGRAM gives hours, minutes and seconds on a 24 hour clock
            t24 = None
            mt = re.match(r"^(\d\d):(\d\d)([ap]m)$", tm)
            if mt:
                hh = int(mt.group(1)) % 12 + (12 if mt.group(3) == "pm" else 0)
                t24 = "%02d:%s" % (hh, mt.group(2))
            row("E6: ... 'Compiled %s %s:ss' (the date and the time !PROG_INFO reads from the same bytes: %s)" % (dt, t24, tm),
                t24 is not None and has(out, r"^\s+Compiled %s %s:\d\d$" % (re.escape(dt), re.escape(t24))), repr(out[-8:]))
            out = plain("zzaa", ["FIND.PROGRAM zzfps DETAIL"])
            row("E7: DETAIL gives the object code size !PROG_INFO reads (%s bytes)" % size,
                has(out, r"^\s+Object code %s bytes$" % size), repr(out[-6:]))
        # CATALOG ... LOCAL asks whether to remove the private entry: N keeps it, and the next line is the FIND.PROGRAM
        out = plain("zzaa", ["CATALOG bp zzfps LOCAL", "N", "FIND.PROGRAM zzfps"])
        places = [l for l in out if l.startswith("Program is in the ")]
        row("E8: catalogued locally as well, it is shown twice, in the order a program is loaded: local, then private",
            places == ["Program is in the local catalogue", "Program is in the private catalogue"], repr(places) + repr(out[-8:]))
        out = plain("zzaa", ["FIND.PROGRAM !acc_hold", "FIND.PROGRAM !ftype"])
        row("E9: a global program: !acc_hold is in the global catalogue and has three arguments",
            has(out, r"^Program is in the global catalogue$") and has(out, r"^\s+Subroutine with 3 arguments$"), repr(out[-8:]))
        row("E9: ... and !ftype is a function of one argument", has(out, r"^\s+Function with 1 arguments$"), repr(out[-8:]))
        out = plain("zzaa", ["FIND.PROGRAM !acc_hold DETAIL"])
        row("E9: DETAIL shows the flags: !acc_hold is an internal program", has(out, r"^\s+Flags: .*internal"), repr(out[-8:]))
        out = plain("zzaa", ["FIND.PROGRAM zznosuchprog"])
        row("E10: a name that is catalogued nowhere is said so (zznosuchprog is not catalogued)", has(out, r"^zznosuchprog is not catalogued$"), repr(out[-3:]))

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- I. MATWRITECSV -------------------------------------------------------------------------------------------")
        csvf = os.path.join(acct, "zzmwc.csv")
        if os.path.exists(csvf):
            os.remove(csvf)
        out = plain("zzaa", ["RUN bp zzmwc"])
        row("I1: the three writes take THEN, and the program ends", tag(out, "M1") == ["1"] and tag(out, "M2") == ["1"] and tag(out, "M3") == ["1"]
            and has(out, r"^MWCDONE$"), repr(out[-6:]))
        try:
            with open(csvf, errors="replace") as f:
                lines = f.read().split("\n")
        except OSError:
            lines = []
        row("I2: a 2 x 2 matrix is ONE line, elements in row order, a value with the delimiter or a quote quoted as CSV is, a null last "
            "element left empty: a,\"b,c\",\"say \"\"hi\"\"\",", len(lines) >= 1 and lines[0] == 'a,"b,c","say ""hi""",', repr(lines[:4]))
        row("I3: a vector of three is the next line: 1,22,x y", len(lines) >= 2 and lines[1] == "1,22,x y", repr(lines[:4]))
        row("I4: a matrix of one null element is a blank line (and the file ends with a line feed)", len(lines) >= 3 and lines[2] == "" and len(lines) == 4
            and lines[3] == "", repr(lines))
        row("I5: a file opened READONLY takes ELSE, and what was in the file is untouched", tag(out, "M4") == ["0"] and len(lines) == 4, repr(tag(out, "M4")))
        if os.path.exists(csvf):
            os.remove(csvf)

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- H. SET.MODE ----------------------------------------------------------------------------------------------")
        smdir = os.path.join(acct, "zzsmdir")

        def modes():
            r = {}
            for n in ("a", "b", "c"):
                try:
                    r[n] = os.stat(os.path.join(smdir, n)).st_mode & 0o777
                except OSError:
                    r[n] = None
            return r

        def set_os(on):
            """The account's register record with the OS.EXECUTE gate (field 8) off or on, as MODIFY.ACCOUNT os-on writes it."""
            put(os.path.join(SYS, "accounts", "zzaa"),
                "\n".join([acct, "", GROUP, "", "", "", "", "YES" if on else ""]) + "\n")

        out = plain("zzaa", ["CREATE.FILE zzsmdir DIRECTORY", "RUN bp zzsmmk"])
        before = modes()
        row("H0: setup: a directory file with three records (their modes before are the umask's: %s)" % {k: oct(v) if v is not None else None for k, v in before.items()},
            all(v is not None for v in before.values()) and all(v != 0o640 for v in before.values()), repr(out[-3:]))
        out = plain("zzaa", ["SET.MODE zzsmdir a 640"])
        row("H0: the verb changes OS permission bits, so it is behind the account's OS gate: an account with the gate off is refused "
            "(and nothing changes), and the administrator is not",
            has(out, r"needs the account's operating system access") and modes() == before, repr(out[-3:]) + repr(modes()))
        set_os(True)                  # SDSYS turned os-on for the account: the rows below are that account's
        out = plain("zzaa", ["SET.MODE zzsmdir a 640"])
        now = modes()
        row("H1: SET.MODE zzsmdir a 640: '1 record(s) set to mode 640', and record a is 0640 on the disk, b and c untouched",
            has(out, r"^1 record\(s\) set to mode 640$") and now["a"] == 0o640 and now["b"] == before["b"] and now["c"] == before["c"],
            repr(out[-3:]) + repr({k: oct(v) for k, v in now.items()}))
        out = plain("zzaa", ["SET.MODE zzsmdir ALL 600"])
        now = modes()
        row("H2: ALL: three records, all 0600", has(out, r"^3 record\(s\) set to mode 600$") and set(now.values()) == {0o600}, repr(out[-3:]) + repr(now))
        out = plain("zzaa", ["SET.MODE zzsmdir b c 664"])
        now = modes()
        row("H3: two ids on the line: b and c are 0664 and a stays 0600", has(out, r"^2 record\(s\) set to mode 664$") and now == {"a": 0o600, "b": 0o664, "c": 0o664},
            repr(out[-3:]) + repr(now))
        out = plain("zzaa", ["SELECT zzsmdir", "SET.MODE zzsmdir NO.QUERY 644"])
        now = modes()
        row("H4: no ids, an active select list and NO.QUERY: the list's three records are 0644",
            has(out, r"^3 record\(s\) set to mode 644$") and set(now.values()) == {0o644}, repr(out[-4:]) + repr(now))
        out = plain("zzaa", ["SELECT zzsmdir", "SET.MODE zzsmdir 640", "N"])
        now = modes()
        row("H5: CONTROL: the same without NO.QUERY asks (Use active select list), and N changes nothing",
            has(out, r"Use active select list") and set(now.values()) == {0o644}, repr(out[-4:]) + repr(now))
        for bad in ("649", "7777", "64", "rwx", "0o640"):
            out = plain("zzaa", ["SET.MODE zzsmdir a " + bad])
            row("H6: the mode %r is refused (three octal digits) and nothing changes" % bad,
                has(out, r"The mode must be three octal digits") and modes()["a"] == 0o644, repr(out[-3:]))
        out = plain("zzaa", ["SET.MODE zzsmdir zzno 600"])
        row("H7: a record that is not there is said so and nothing is counted", has(out, r"Record 'zzno' not found") and has(out, r"^0 record\(s\) set to mode 600$"),
            repr(out[-3:]))
        victim = os.path.join(BOX, "zzsmvictim.txt")
        with open(victim, "w") as f:
            f.write("not a record\n")
        os.chmod(victim, 0o644)
        link = os.path.join(smdir, "zzlnk")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(victim, link)
        out = plain("zzaa", ["SET.MODE zzsmdir zzlnk 600"])
        row("H8: a record that is a symbolic link is not followed: the file it points at keeps its mode (0644), and it is reported",
            (os.stat(victim).st_mode & 0o777) == 0o644 and not has(out, r"^1 record\(s\) set to mode 600$"), repr(out[-3:]) + oct(os.stat(victim).st_mode & 0o777))
        os.remove(link)
        out = plain("zzaa", ["CREATE.FILE zzsmdyn", "SET.MODE zzsmdyn a 600"])
        row("H9: a file that is not a directory file is refused (A directory file is required)", has(out, r"A directory file is required"), repr(out[-3:]))
        out = plain("zzaa", ["SET.MODE zzsmdir a 600 junk"])
        row("H10: CONTROL of the parse: a record named junk is looked for as a record, not taken for the mode (the last word is the mode)",
            has(out, r"The mode must be three octal digits"), repr(out[-3:]))
        plain("zzaa", ["DELETE.FILE zzsmdir", "DELETE.FILE zzsmdyn"])
        set_os(False)                 # the gate back off for the rows after this one
        try:
            os.remove(victim)
        except OSError:
            pass

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- G. ANALYSE.INDEX -----------------------------------------------------------------------------------------")
        out = plain("zzaa", ["CREATE.FILE zzaix", "ANALYSE.INDEX zzaix", "RUN bp zzaisu", "CREATE.INDEX zzaix CITY", "BUILD.INDEX zzaix CITY",
                             "ANALYSE.INDEX zzaix"])
        row("G1: a file with no index says so (File has no indices)", has(out, r"^File has no indices$"), repr(out[:6]))
        row("G2: with the file name alone: the heading, and a line for the index: 4 indexed values, at most 5 records for one",
            has(out, r"^Analysis of the indices of file zzaix$") and has(out, r"^CITY\s+4\s+5$"), repr(out[-6:]))
        out = plain("zzaa", ["ANALYSE.INDEX zzaix CITY", "LIST.INDEX zzaix CITY STATISTICS"])
        want = re.compile(r"^\s+10\s+4\s+1\s+2\.5\s+5$")
        figs = [l for l in out if want.match(l)]
        row("G3: a named index shows the totals - 10 index entries, 4 values, least 1, average 2.5, most 5 - and LIST.INDEX, which reads "
            "the same figures by its own loop, shows the same line", len(figs) == 2, repr(out[-14:]))
        row("G3: ... and the spread of the values over the number of records they hold: 1 record (2 values), 2 to 3 (1), 4 to 7 (1)",
            has(out, r"^\s+1\s+2$") and has(out, r"^\s+2 to 3\s+1$") and has(out, r"^\s+4 to 7\s+1$"), repr(out[-14:]))
        out = plain("zzaa", ["ANALYSE.INDEX zzaix CITY DETAIL"])
        row("G4: DETAIL lists every indexed value with its number of records: Paris 5, Rome 3, Oslo 1, Lima 1",
            all(has(out, r"^\s+%d  %s$" % (n, v)) for n, v in ((5, "Paris"), (3, "Rome"), (1, "Oslo"), (1, "Lima"))), repr(out[-12:]))
        out = plain("zzaa", ["ANALYSE.INDEX zzaix city NO.PAGE"])
        row("G5: the index name is taken in any case, and NO.PAGE is accepted", has(out, r"^\s+10\s+4\s+1\s+2\.5\s+5$"), repr(out[-6:]))
        out = plain("zzaa", ["ANALYSE.INDEX zzaix NOSUCH"])
        row("G6: an index the file does not have is refused (Unrecognised index name (NOSUCH))", has(out, r"Unrecognised index name \(NOSUCH\)"), repr(out[-3:]))
        out = plain("zzaa", ["ANALYSE.INDEX zznosuchfile"])
        row("G6: a file that is not there is refused (File not found)", has(out, r"File not found"), repr(out[-3:]))
        out = plain("zzaa", ["ANALYSE.INDEX"])
        row("G6: no file name is refused (File name required)", has(out, r"File name required"), repr(out[-3:]))
        plain("zzaa", ["DELETE.FILE zzaix"])

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- F. COMMAND.LOGGING ---------------------------------------------------------------------------------------")

        def logs():
            return sorted(f for f in os.listdir(acct) if re.match(r"^clog\.\d+\.log$", f))

        for f in logs():
            os.remove(os.path.join(acct, f))
        out = plain("zzaa", ["COMMAND.LOGGING"])
        row("F1: with nothing done it says 'Command logging is off' and makes no file", has(out, r"^Command logging is off$") and logs() == [], repr(out[-3:]))
        out = plain("zzaa", ["COMMAND.LOGGING ON", "DATE", "RUN bp zzin", "COMMAND.LOGGING", "COMMAND.LOGGING OFF", "TIME"])
        m = re.search(r"(?m)^Command logging is on: (.*clog\.(\d+)\.log)$", "\n".join(out))
        row("F2: ON says 'Command logging is on: <pathname>' (clog.<user number>.log in the account directory)",
            m is not None and os.path.dirname(m.group(1)) == os.path.realpath(acct), repr(out[:6]))
        row("F2: ... the file exists, and it is mode 0600 and the sandbox user's", len(logs()) == 1 and
            (os.stat(os.path.join(acct, logs()[0])).st_mode & 0o777) == 0o600 and os.stat(os.path.join(acct, logs()[0])).st_uid == os.getuid(),
            repr(logs()))
        rows_ = []
        if logs():
            with open(os.path.join(acct, logs()[0]), errors="replace") as f:
                rows_ = [ln.rstrip("\n").split("\t") for ln in f.read().splitlines()]
        got = [(r[3], r[4]) for r in rows_ if len(r) == 5]
        row("F3: the commands after ON are in it, in order, with their origin: DATE, RUN bp zzin, COMMAND.LOGGING, COMMAND.LOGGING OFF "
            "(User); the ON itself and the TIME after OFF are not",
            got == [("User", "DATE"), ("User", "RUN bp zzin"), ("User", "COMMAND.LOGGING"), ("User", "COMMAND.LOGGING OFF")], repr(got))
        row("F3: ... each line is epoch, user number, login name, origin, command: the epoch is within five minutes of now, the user "
            "number is this session's, the name is %s" % USER,
            len(rows_) == 4 and all(len(r) == 5 and r[0].isdigit() and abs(int(r[0]) - time.time()) < 300 and r[1] == m.group(2) and r[2] == USER
                                    for r in rows_) if m else False, repr(rows_[:2]))
        # nested commands: EXECUTE from a program, and a paragraph
        for f in logs():
            os.remove(os.path.join(acct, f))
        out = plain("zzaa", ["RUN bp zzmkpa", "COMMAND.LOGGING ON", "RUN bp zzex", "zzpara"])
        rows_ = []
        if logs():
            with open(os.path.join(acct, logs()[0]), errors="replace") as f:
                rows_ = [ln.rstrip("\n").split("\t") for ln in f.read().splitlines()]
        got = [(r[3], r[4]) for r in rows_ if len(r) == 5]
        row("F4: a command a program runs with EXECUTE is Exec, a paragraph and its lines are User then PA (and the OFF that "
            "ends the session, which this one never turned logging off for, is the last line)",
            got == [("User", "RUN bp zzex"), ("Exec", "DATE"), ("User", "zzpara"), ("PA", "TIME"), ("PA", "DATE"), ("User", "OFF")],
            repr(got))
        out = plain("zzaa", ["COMMAND.LOGGING"])
        row("F5: a new session starts with it off (logging is the session's own), and the earlier session's file is not added to",
            has(out, r"^Command logging is off$"), repr(out[-3:]))
        out = plain("zzaa", ["COMMAND.LOGGING MAYBE"])
        row("F6: a word that is not ON or OFF is refused (Unexpected token (MAYBE))", has(out, r"Unexpected token \(MAYBE\)"), repr(out[-3:]))
        # a link left where the log would be made is not written through
        victim = os.path.join(BOX, "zzvictim.txt")
        with open(victim, "w") as f:
            f.write("not for the log\n")
        for f in logs():
            os.remove(os.path.join(acct, f))
        planted = []
        for n in range(1, 1100):   # user numbers rotate up to USERPOOL (1023 by default): every one the session could get
            p = os.path.join(acct, "clog.%d.log" % n)
            os.symlink(victim, p)
            planted.append(p)
        out = plain("zzaa", ["COMMAND.LOGGING ON", "DATE", "COMMAND.LOGGING"])
        with open(victim) as f:
            vtext = f.read()
        row("F7: a symbolic link in the log's place is refused (The command log could not be started), and what it points at is "
            "not written to", has(out, r"^The command log could not be started$") and vtext == "not for the log\n", repr(out[-4:]) + repr(vtext))
        for p in planted:
            os.remove(p)

        # -------------------------------------------------------------------------------------------------------------
        say("\n--- D. USPLIT and SYSTEM(20) ---------------------------------------------------------------------------------")
        out = adm(["RUN bp zzun", "RUN bp zzphl"])
        un = tag(out, "UNO")
        nusers = int(un[0].split("][")[1]) if un and re.match(r"^\d+\]\[\d+\]\[\d+$", un[0]) else None
        row("D1: CONTROL: the sandbox's own sd.conf has no USPLIT: CONFIG('USPLIT') is 0 and NUMUSERS is a number (%s)" % nusers,
            nusers is not None and un[0].endswith("][0"), repr(un))
        ph0 = tag(out, "PHUNO")
        row("D1: CONTROL: ... and the phantom is NOT given the highest user number (the plain rotation took a low one)",
            len(ph0) == 1 and ph0[0].isdigit() and nusers is not None and int(ph0[0]) != nusers, repr(ph0) + " NUMUSERS " + str(nusers))

        tmpdir = os.path.join(BOX, "zztmp")
        os.makedirs(tmpdir, exist_ok=True)
        if not restart("USPLIT=1", "SPOOLER=true", "TEMPDIR=" + tmpdir):
            row("D2: SD starts with USPLIT=1", False, "did not start")
        else:
            out = plain("zzaa", ["COMMAND.LOGGING ON", "DATE", "COMMAND.LOGGING OFF"])
            tl = [f for f in os.listdir(tmpdir) if re.match(r"^clog\.\d+\.log$", f)]
            row("F8: with TEMPDIR in sd.conf the command log is STILL made in the account directory (TEMPDIR is a directory anyone "
                "can write to), and nothing is made in TEMPDIR",
                tl == [] and has(out, r"^Command logging is on: %s/clog\.\d+\.log$" % re.escape(os.path.realpath(acct))),
                repr(tl) + repr(out[:4]))
            out = adm(["RUN bp zzun", "RUN bp zzphl"])
            un = tag(out, "UNO")
            ph1 = tag(out, "PHUNO")
            row("D2: USPLIT=1: CONFIG('USPLIT') is 1", len(un) == 1 and un[0].endswith("][1"), repr(un))
            row("D2: ... an interactive session takes the LOWEST free user number (1)", len(un) == 1 and un[0].split("][")[0] == "1", repr(un))
            row("D2: ... and a phantom takes the HIGHEST (NUMUSERS = %s)" % nusers,
                len(ph1) == 1 and nusers is not None and ph1[0] == str(nusers), repr(ph1))
            h = Live("usp", ["RUN bp zzun"], admin=True, hold=True)
            h.wait_for(r"(?m)^UNO\[", 20)
            out = adm(["RUN bp zzun"])
            un2 = tag(out, "UNO")
            row("D3: a second interactive session, with the first still there, takes the next lowest (2)",
                len(un2) == 1 and un2[0].split("][")[0] == "2", repr(un2))
            h.p.stdin.write("OFF\n")
            h.p.stdin.flush()
            h.wait(30)

            out = adm(["RUN bp zzspl"])
            j1 = tag(out, "JOBS")
            row("D4: SYSTEM(20) counts the print job passed to the spooler: a, then a + 1", len(j1) == 1 and re.match(r"^\d+\]\[\d+$", j1[0]) and
                int(j1[0].split("][")[1]) == int(j1[0].split("][")[0]) + 1, repr(j1))
            out = adm(["RUN bp zzspl"])
            j2 = tag(out, "JOBS")
            row("D4: ... and it is the system's, not the session's: a second session starts at the first one's total",
                len(j1) == 1 and len(j2) == 1 and j2[0].split("][")[0] == j1[0].split("][")[1]
                and int(j2[0].split("][")[1]) == int(j2[0].split("][")[0]) + 1, repr(j1) + repr(j2))
    finally:
        for lv in lives:
            lv.kill()
        restart()
        for d in ("bp", "bp.out"):
            for nm in list(USER_PROGS) + ["zzfix", "zzphun"]:
                p = os.path.join(SYS, d, nm)
                if os.path.exists(p):
                    os.remove(p)
        try:
            os.remove(outside)
        except OSError:
            pass

    say("\nsandbox-stmt-q3: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
