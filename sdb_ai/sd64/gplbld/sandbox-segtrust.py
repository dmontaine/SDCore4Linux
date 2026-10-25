#!/usr/bin/env python3
#
# sandbox-segtrust.py - W.11 F9 (security-model evaluation, 24 Oct 2026): what another process writes into the shared segment does not decide what a
#                       session loads, runs or is allowed.  A private SD, no install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-segtrust.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run (including every null case: the segment is not there, an offset does not point where it should, a write did not land).
#
# START-HISTORY:
# 24 Oct 26 dm  New.  Plan: .claude/plan-f9-segment-trust.md.  Evidence: the program below plays the member of sdusers who has a shell - it attaches the
#               sandbox's own segment with shmat and writes - and then fresh and running ordinary sessions are asked what they use.
# END-HISTORY
#
# WHAT IT DOES.  Struct offsets come from a small C program compiled against this tree's own headers (so they cannot drift).  The program attaches the segment
# (SysV key 0x53434C91 + 0x20 * keyset, the sandbox's) and:
#   P  changes the privilege bits and the gates word in a RUNNING ordinary session's user table entry; the session then reports (ZZKF, ZZKG) and tries SH
#   A1 writes a decoy directory over sysdir      A2 breaks the first object of the p-code copy      A3 writes decoys over the process-configuration template
#      and starts FRESH ordinary sessions, which must use the configuration file, bin/pcode and the registered grants instead
#   A4 edits sd.conf: a legitimate change reaches a new session (documented behaviour change) and a bad line refuses it WITHOUT taking SD down
# Every write is read back (the null case), and every change is put back before the next section.  The roles are the same user: a sandbox has no second
# user; what the sandbox cannot say is that a user outside sdusers cannot attach - that is the segment's mode, sandbox-shmmode.py.
# NOT HELD: a root-run process (sd -stop, sd -cleanup, the API first stage) reading the segment - a sandbox is not root; test-segtrust-units.py reads the
# source for it.  The lock, file and user tables stay writable by design (plan, section 1).

import ctypes
import getpass
import importlib.util
import os
import re
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
USER = getpass.getuser()


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g = _load("sandbox_gates_for_segtrust", "sandbox-gates.py")
say, row, bail = g.say, g.row, g.bail

OFFS_C = r'''
#include <stddef.h>
#include <stdio.h>
#include "sd.h"
#include "config.h"
#define P(n, v) printf("%s %zu\n", n, (size_t)(v))
int main(void) {
  P("sysdir", offsetof(SYSSEG, sysdir));
  P("pcode_offset", offsetof(SYSSEG, pcode_offset));
  P("pcode_len", offsetof(SYSSEG, pcode_len));
  P("pcfg_offset", offsetof(SYSSEG, pcfg_offset));
  P("user_table", offsetof(SYSSEG, user_table));
  P("user_entry_size", offsetof(SYSSEG, user_entry_size));
  P("max_users", offsetof(SYSSEG, max_users));
  P("u_uid", offsetof(USER_ENTRY, uid));
  P("u_pid", offsetof(USER_ENTRY, pid));
  P("u_flags", offsetof(USER_ENTRY, flags));
  P("u_gates", offsetof(USER_ENTRY, gates));
  P("p_usrdir", offsetof(struct PCFG, usrdir));
  P("p_sh", offsetof(struct PCFG, sh));
  P("USR_ADMIN", USR_ADMIN);
  P("USR_SH", USR_SH);
  P("USR_OS_EXEC", USR_OS_EXEC);
  P("USR_SD_ACCOUNTS", USR_SD_ACCOUNTS);
  P("UG_ALL", UG_VOC_EDIT | UG_BP_EDIT | UG_DICT_EDIT | UG_NET | UG_SHARED_READ | UG_SHARED_WRITE);
  return 0;
}
'''

O = {}          # offsets and constants
SEG = None      # the attached segment
BOX = SYS = SD = None


def box_offsets():
    c = os.path.join(BOX, "segtrust-offs.c")
    exe = os.path.join(BOX, "segtrust-offs")
    with open(c, "w") as f:
        f.write(OFFS_C)
    r = subprocess.run(["gcc", "-std=gnu17", "-DLINUX", "-D_FILE_OFFSET_BITS=64", "-DGPL", "-I", os.path.join(TREE, "gplsrc"), "-o", exe, c],
                       capture_output=True, text=True)
    if r.returncode != 0:
        bail("the offsets program did not compile (gcc is needed):\n" + (r.stdout + r.stderr)[-600:])
    out = subprocess.run([exe], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        k, v = ln.split()
        O[k] = int(v)
    say("  offsets from this tree's headers: " + " ".join("%s=%d" % (k, O[k]) for k in sorted(O)))


class Seg:
    """the member of sdusers with a shell: attaches the sandbox's segment read-write and reads and writes it"""

    def __init__(self, key):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.shmget.argtypes = [ctypes.c_int, ctypes.c_size_t, ctypes.c_int]
        libc.shmat.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        libc.shmat.restype = ctypes.c_void_p
        shmid = libc.shmget(key, 0, 0)
        if shmid < 0:
            bail("the sandbox's segment (key 0x%X) is not there (errno %d)" % (key, ctypes.get_errno()))
        addr = libc.shmat(shmid, None, 0)
        if addr is None or addr == ctypes.c_void_p(-1).value:
            bail("shmat of the sandbox's segment failed (errno %d)" % ctypes.get_errno())
        self.addr = addr
        self.key = key

    def read(self, off, n):
        return ctypes.string_at(self.addr + off, n)

    def write(self, off, data):
        ctypes.memmove(self.addr + off, data, len(data))

    def i16(self, off):
        return struct.unpack("<h", self.read(off, 2))[0]

    def u16(self, off):
        return struct.unpack("<H", self.read(off, 2))[0]

    def i32(self, off):
        return struct.unpack("<i", self.read(off, 4))[0]

    def cstr(self, off, maxn=300):
        raw = self.read(off, maxn)
        return raw.split(b"\0", 1)[0].decode("latin-1")

    def put_cstr(self, off, text, room):
        data = text.encode("latin-1") + b"\0"
        if len(data) > room:
            bail("%r does not fit in %d bytes" % (text, room))
        self.write(off, data)

    def entry_of(self, pid):
        """the offset of the user table entry whose pid is this one, or None"""
        table = self.i32(O["user_table"])
        size = self.i16(O["user_entry_size"])
        for i in range(self.i16(O["max_users"])):
            off = table + i * size
            if self.i16(off + O["u_uid"]) != 0 and self.i32(off + O["u_pid"]) == pid:
                return off
        return None


class Live:
    """an ORDINARY session (no SDTEST_ADMIN) in an account, on a pipe kept open"""

    def __init__(self, acct):
        env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"))
        for k in ("SDTEST_ADMIN", "SSH_CONNECTION", "SSH_TTY"):
            env.pop(k, None)
        self.out = os.path.join(BOX, "segtrust-live-%s.out" % acct)
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([SD, "-a" + acct], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT,
                                  cwd=os.path.join(BOX, "user_accounts", acct), env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\n")
        self.p.stdin.flush()
        say("    > live ordinary session in %s: pid %d" % (acct, self.p.pid))

    def text(self):
        self.fh.flush()
        with open(self.out, errors="replace") as f:
            return ANSI.sub("", f.read()).replace("\r", "")

    def send(self, cmd):
        say("    > live: " + cmd)
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def ask(self, cmd, pattern, seconds=40):
        """send a command; return the first match of the pattern in what the session printed AFTER it, or None"""
        start = len(self.text())
        say("    > live: " + cmd)
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()
        end = time.time() + seconds
        while time.time() < end:
            m = re.search(pattern, self.text()[start:], re.M)
            if m:
                return m
            if self.p.poll() is not None:
                break
            time.sleep(0.3)
        return None

    def close(self):
        if self.p.poll() is None:
            try:
                self.p.stdin.write("OFF\n")
                self.p.stdin.flush()
                self.p.wait(timeout=15)
            except Exception:
                self.p.kill()
                self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


def probes():
    """internal programs that print what the kernel answers, catalogued in gpl.bp, and a VOC entry for each in the fixture accounts"""
    g.put(os.path.join(SYS, "gpl.bp", "zzkg"), "\n".join([
        "$internal", "program zzkg", "$catalog $zzkg", "$include keys.h", "$include int$keys.h",
        "   crt 'KGATES voc=':kernel(K$VOC.EDIT,-1):' bp=':kernel(K$BP.EDIT,-1):' dict=':kernel(K$DICT.EDIT,-1):' net=':kernel(K$NET,-1):"
        "' sr=':kernel(K$SHARED.READ,-1):' sw=':kernel(K$SHARED.WRITE,-1):' sdacc=':kernel(K$SD.ACCOUNTS,-1)", "end", ""]))
    g.put(os.path.join(SYS, "gpl.bp", "zzsd"), "\n".join([
        "$internal", "program zzsd", "$catalog $zzsd", "   crt 'SDIR=':@sdsys:'='", "end", ""]))
    g.put(os.path.join(SYS, "gpl.bp", "zzcfg"), "\n".join([
        "$internal", "program zzcfg", "$catalog $zzcfg",
        "   crt 'CFG usrdir=':config('USRDIR'):' lptrwide=':config('LPTRWIDE'):' sh=[':config('SH'):']'", "end", ""]))
    out = g.adm(["BASIC gpl.bp zzkg zzsd zzcfg"], internal=True)
    if not g.has(out, r"^Compiled 3 program\(s\) with no errors"):
        bail("the probes did not compile:\n" + "\n".join(out[-10:]))
    for acct in ("zzoff", "zzon"):
        path = os.path.join(BOX, "user_accounts", acct)
        g.put(os.path.join(SYS, "bp", "zzfix2"), "\n".join([
            "$internal", "   openpath '%s/voc' to v else crt 'FIX2 open voc failed' ; stop" % path,
            "   write 'V':@fm:'CA':@fm:'$zzkg' to v, 'zzkg'", "   write 'V':@fm:'CA':@fm:'$zzsd' to v, 'zzsd'",
            "   write 'V':@fm:'CA':@fm:'$zzcfg' to v, 'zzcfg'", "   crt 'FIX2 done ':'%s'" % acct, "end", ""]))
        out = g.adm(["BASIC bp zzfix2", "RUN bp zzfix2"], internal=True)
        if not g.has(out, r"^FIX2 done " + acct + "$"):
            bail("the probes were not added to %s's VOC:\n%s" % (acct, "\n".join(out[-6:])))


def gates_line(lines):
    for ln in lines:
        if ln.startswith("KGATES "):
            return ln
    return None


def one(lines, prefix):
    for ln in lines:
        if ln.startswith(prefix):
            return ln
    return None


def conf_path():
    return os.path.join(BOX, "sd.conf")


def main():
    global BOX, SYS, SD, SEG
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-segtrust.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    g.BOX, g.SYS, g.SD = BOX, SYS, SD
    keyset = int(os.environ.get("SDBOX_KEYSET", "0"))
    key = 0x53434C91 + 0x20 * keyset
    say("sandbox-segtrust: sandbox %s, keyset %d, segment key 0x%X, tree %s" % (BOX, keyset, key, TREE))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-segtrust: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation ---------------------------------------------------------------------------------------------")
    g.prepare()
    for name in ("zzoff", "zzon"):
        g.build_account(name)
    probes()
    box_offsets()
    SEG = Seg(key)
    lives = []
    try:
        run_rows(lives)
    finally:
        for lv in lives:
            lv.close()
    say("")
    say("sandbox-segtrust: %d passed, %d failed" % (g.passed, g.failed))
    sys.exit(1 if g.failed else 0)


def run_rows(lives):
    sysdir_off = O["sysdir"]
    room = 4096 - 1
    real_sys = SEG.cstr(sysdir_off)

    say("\n--- 0. controls: the attacker really is looking at the right bytes -----------------------------------------------")
    row("0a: the segment's sysdir is the sandbox's directory", real_sys == SYS, "segment says %r, the sandbox is %r" % (real_sys, SYS))
    if real_sys != SYS:
        bail("sysdir is not where the offsets say: every row below would write into the wrong bytes")
    pcode_at = SEG.i32(O["pcode_offset"])
    pcode_len = SEG.i32(O["pcode_len"])
    with open(os.path.join(SYS, "bin", "pcode"), "rb") as f:
        pfile = f.read()
    row("0b: the segment's p-code copy is the file bin/pcode (%d bytes)" % len(pfile), pcode_len == len(pfile) and SEG.read(pcode_at, 64) == pfile[:64] and
        SEG.read(pcode_at + pcode_len - 64, 64) == pfile[-64:], "segment length %d, file length %d" % (pcode_len, len(pfile)))
    pcfg_at = SEG.i32(O["pcfg_offset"])
    usr_real = os.path.join(BOX, "user_accounts")
    row("0c: the segment's configuration template carries the sandbox's USRDIR", SEG.cstr(pcfg_at + O["p_usrdir"]) == usr_real,
        "template says %r" % SEG.cstr(pcfg_at + O["p_usrdir"]))
    if not (pcode_len == len(pfile) and SEG.cstr(pcfg_at + O["p_usrdir"]) == usr_real):
        bail("the p-code or the template is not where the offsets say")

    live = Live("zzoff")
    lives.append(live)
    m = live.ask("ZZKF", r"^KFLAGS admin=(\d) sh=(\d) osx=(\d) user=(\S+)$")
    row("0d: the running ordinary session is not an administrator and holds no grant (admin=0 sh=0 osx=0)", m is not None and m.groups()[:3] == ("0", "0", "0"),
        "ZZKF answered %r" % (m.group(0) if m else None))
    if m is None or m.groups()[:3] != ("0", "0", "0"):
        bail("the running session is not an ordinary one: every privilege row below would mean nothing")
    base_gates = live.ask("ZZKG", r"^KGATES .*$")
    row("0e: the session answers ZZKG (its gates as the register loaded them)", base_gates is not None, "")
    entry = SEG.entry_of(live.p.pid)
    row("0f: its user table entry is found by its pid", entry is not None, "pid %d" % live.p.pid)
    if entry is None or base_gates is None:
        bail("the session's user table entry (or its gates) cannot be read: the privilege rows below would write nothing")
    flags_at, gates_at = entry + O["u_flags"], entry + O["u_gates"]
    flags0, gates0 = SEG.u16(flags_at), SEG.u16(gates_at)
    say("    entry at %d: flags 0x%04X gates 0x%04X before" % (entry, flags0, gates0))

    say("\n--- P. a writer changes a RUNNING session's privilege bits and gates ----------------------------------------------")
    bits = O["USR_ADMIN"] | O["USR_SH"] | O["USR_OS_EXEC"] | O["USR_SD_ACCOUNTS"]
    try:
        SEG.write(flags_at, struct.pack("<H", flags0 | bits))
        SEG.write(gates_at, struct.pack("<H", gates0 | O["UG_ALL"]))
        f1, g1 = SEG.u16(flags_at), SEG.u16(gates_at)
        say("    entry after the write: flags 0x%04X gates 0x%04X" % (f1, g1))
        if f1 & bits != bits or g1 & O["UG_ALL"] != O["UG_ALL"]:
            bail("the write to the user table entry did not land")
        m = live.ask("ZZKF", r"^KFLAGS admin=(\d) sh=(\d) osx=(\d) user=(\S+)$")
        row("P1: the session still says admin=0 sh=0 osx=0 (the segment says 1 1 1)", m is not None and m.groups()[:3] == ("0", "0", "0"),
            "ZZKF answered %r" % (m.group(0) if m else None))
        gl = live.ask("ZZKG", r"^KGATES .*$")
        row("P2: and its gates are the ones the register loaded (the segment's word has every gate on)", gl is not None and gl.group(0) == base_gates.group(0),
            "before %r, after %r" % (base_gates.group(0), gl.group(0) if gl else None))
        sent = os.path.join(BOX, "user_accounts", "zzoff", "p.sentinel")
        if os.path.exists(sent):
            os.remove(sent)
        live.send("SH touch " + sent)
        barrier = live.ask("ZZKF", r"^KFLAGS admin=(\d) sh=(\d) osx=(\d) user=(\S+)$")      # answered only after SH has been dealt with
        refused = "is not permitted to use the operating system shell" in live.text()
        row("P3: SH is still refused: the command did not run (the file is the evidence) and the refusal was printed",
            barrier is not None and not os.path.exists(sent) and refused,
            "barrier answered=%s sentinel exists=%s refusal printed=%s" % (barrier is not None, os.path.exists(sent), refused))
    finally:
        SEG.write(flags_at, struct.pack("<H", flags0))
        SEG.write(gates_at, struct.pack("<H", gates0))
    row("P4: the entry is put back as it was", SEG.u16(flags_at) == flags0 and SEG.u16(gates_at) == gates0, "")
    on = g.plain("zzon", ["ZZKF"])
    f = g.flags(on)
    row("P5: control - a fresh session in zzon (register: SH yes, OS.EXECUTE yes) holds both grants: the loaders still set them", f is not None and f[1] == "1" and f[2] == "1" and f[0] == "0",
        "KFLAGS %r" % (f,))

    say("\n--- A1. the system directory in the segment is changed to a decoy -------------------------------------------------")
    decoy = os.path.join(BOX, "decoy-sysdir")
    shutil.rmtree(decoy, ignore_errors=True)
    os.makedirs(decoy)
    try:
        SEG.put_cstr(sysdir_off, decoy, room)
        row("A1a: (null case) the write landed: the segment now names the decoy", SEG.cstr(sysdir_off) == decoy, SEG.cstr(sysdir_off))
        out = g.plain("zzoff", ["ZZSD"])
        l = one(out, "SDIR=")
        row("A1b: a fresh session's SDSYS is still the real directory", l == "SDIR=" + SYS + "=", "ZZSD answered %r; output tail %r" % (l, out[-3:]))
        kids = sorted(os.listdir(decoy))
        row("A1c: and nothing was written under the decoy (no audit line, no errlog)", kids == [], "found %r" % kids)
    finally:
        SEG.put_cstr(sysdir_off, SYS, room)
    row("A1d: the segment is put back", SEG.cstr(sysdir_off) == SYS, "")
    shutil.rmtree(decoy, ignore_errors=True)

    say("\n--- A2. the first object of the p-code copy in the segment is broken -----------------------------------------------")
    orig = SEG.read(pcode_at, 8)
    try:
        SEG.write(pcode_at, bytes(b ^ 0xFF for b in orig[:4]) + orig[4:])
        row("A2a: (null case) the write landed", SEG.read(pcode_at, 4) != orig[:4], "")
        out = g.plain("zzoff", ["ZZKF"])
        f = g.flags(out)
        row("A2b: a fresh session still starts and runs (it runs the file's p-code, not the segment's)", f is not None and f[0] == "0", "output tail %r" % (out[-3:],))
    finally:
        SEG.write(pcode_at, orig)
    row("A2c: the p-code copy is put back", SEG.read(pcode_at, 8) == orig, "")

    say("\n--- A3. the configuration template in the segment is changed (USRDIR, SH) -------------------------------------------")
    usr0, sh0 = SEG.cstr(pcfg_at + O["p_usrdir"]), SEG.cstr(pcfg_at + O["p_sh"])
    try:
        SEG.put_cstr(pcfg_at + O["p_usrdir"], "/nonexistent/decoy-users", 256)
        SEG.put_cstr(pcfg_at + O["p_sh"], "/nonexistent/decoy-shell", 128)
        row("A3a: (null case) the write landed", SEG.cstr(pcfg_at + O["p_usrdir"]) == "/nonexistent/decoy-users", "")
        out = g.plain("zzoff", ["ZZCFG"])
        l = one(out, "CFG ")
        want = "CFG usrdir=%s lptrwide=80 sh=[]" % usr_real
        row("A3b: a fresh session's USRDIR and SH come from sd.conf, not the template", l == want, "ZZCFG answered %r, wanted %r" % (l, want))
    finally:
        SEG.put_cstr(pcfg_at + O["p_usrdir"], usr0, 256)
        SEG.put_cstr(pcfg_at + O["p_sh"], sh0, 128)
    row("A3c: the template is put back", SEG.cstr(pcfg_at + O["p_usrdir"]) == usr0 and SEG.cstr(pcfg_at + O["p_sh"]) == sh0, "")

    say("\n--- A4. sd.conf is read by each new session: an edit reaches it, and a bad line refuses it without stopping SD -------")
    with open(conf_path()) as f:
        conf0 = f.read()
    try:
        with open(conf_path(), "w") as f:
            f.write(conf0 + "LPTRWIDE=111\n")
        out = g.plain("zzoff", ["ZZCFG"])
        l = one(out, "CFG ")
        row("A4a: [documented change] a legitimate edit of sd.conf reaches a session started after it (LPTRWIDE 80 -> 111)",
            l == "CFG usrdir=%s lptrwide=111 sh=[]" % usr_real, "ZZCFG answered %r" % (l,))
        with open(conf_path(), "w") as f:
            f.write(conf0 + "ZZBOGUS=1\n")
        out = g.plain("zzoff", ["ZZCFG"])
        row("A4b: a bad line in sd.conf refuses a new session with the starter's wording and no program ran",
            g.has(out, r"Unrecognised configuration parameter 'ZZBOGUS=1'") and one(out, "CFG ") is None, "output %r" % (out[-3:],))
        alive = live.ask("ZZKF", r"^KFLAGS admin=(\d) sh=(\d) osx=(\d) user=(\S+)$", 30)
        row("A4c: the refusal did not take SD down: the running session still answers", alive is not None, "")
    finally:
        with open(conf_path(), "w") as f:
            f.write(conf0)
    out = g.plain("zzoff", ["ZZCFG"])
    l = one(out, "CFG ")
    row("A4d: with the file as it was a new session starts again", l == "CFG usrdir=%s lptrwide=80 sh=[]" % usr_real, "ZZCFG answered %r" % (l,))
    row("A4e: the segment is still the sandbox's (sysdir)", SEG.cstr(sysdir_off) == SYS, "")


if __name__ == "__main__":
    main()
