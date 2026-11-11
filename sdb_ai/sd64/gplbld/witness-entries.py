#!/usr/bin/env python3
#
# witness-entries.py - TOOL.ENTRIES (S.96, the master files by pointer) on a REAL install: M7 of .claude/plan-s96-master-pages.md.  The half that
# sandbox-tool-entries.py cannot show, because a sandbox is never the sdsys OS user: SDSYS's page writes, compiles and debugs in the installing user's
# account as the REAL sdsys user through the REAL groups (S.103: sdsys is in every user account's group), the account itself being locked out of its own
# VOC by its delivered edit gate; and the pointer rule refusing SDSYS's own syscom, which the sdsys user could really write.
#
#   python3 witness-entries.py            (on the VM, as the installing user, with ptydrive.py and termscreen.py beside this file; sudo needs no password there)
#
# SDSYS is entered as witness-toolgates.py does it (the audit loginuid set to sdsys's uid, then sudo -u sdsys sd), 140 by 43, TERM xterm, no SSH_* variables.
# Every outcome is read from the system, not from the page: the account's files on the disk (content, owner, group), an ordinary session of the user, the
# audit trail.  The fixture is written as root at the start and every file it made is taken away at the end (said so), whatever happened.  2 Nov 2026.
# Prints PASS / FAIL lines and a verdict; exit 0 only when every row passed.
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptydrive import PtySession  # noqa: E402

SDSYS_DIR = "/usr/local/sdsys"
SD = SDSYS_DIR + "/bin/sd"
ME = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
ACCT = "/home/sd/user_accounts/" + ME
# 11 Nov 26: the debugger's key row since S.179 / S.186 (F2 find, F5 refresh, F9 run, F10 menu), the same string sandbox-tool-entries.py holds.  The old one
#   (F2 abort, F5 run) made W8 the one red row of the VM run of this day, although the debugger was entered and left (the status line and the audit line say so).
DBG_KEYS = "F1 help  F2 find  F3 stop  F4 screen  F5 refresh  F7 step  F8 line  F9 run  F10 menu  ^F7 parent  ^F8 program"
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if isinstance(ok, str):
        ok, detail = False, "INSTRUMENT FAULT: a text verdict\n" + str(detail)
    if ok:
        passed += 1
        print("PASS  " + name, flush=True)
    else:
        failed += 1
        print("FAIL  " + name, flush=True)
    for ln in str(detail).split("\n")[:(10 if ok else 50)]:
        if ln.strip():
            print("        | " + ln[:220], flush=True)


def sh(cmd):
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, encoding="latin-1").stdout     # an object file is binary


def disk(rel):
    """The record or file as the disk holds it (None when absent), read with sudo."""
    p = os.path.join(ACCT, rel)
    if sh("sudo test -e '%s' && echo y" % p).strip() != "y":
        return None
    return sh("sudo cat '%s'" % p)


def owner(rel):
    return sh("sudo stat -c '%%U:%%G %%a' '%s' 2>&1" % os.path.join(ACCT, rel)).strip()


def mtime(path):
    return sh("sudo stat -c %%Y '%s' 2>/dev/null" % path).strip()


def audit_count():
    return int(sh("sudo wc -l < %s/audit" % SDSYS_DIR).strip() or "0")


def audit_since(n):
    return sh("sudo tail -n +%d %s/audit" % (n + 1, SDSYS_DIR))


def sdsys_cmds(body):
    """TCL lines run as SDSYS on a pipe (sdnet-wlib.sh's sd_as)."""
    inner = 'printf "%s\\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"'
    r = subprocess.run(["sudo", "sh", "-c", inner, "sd-run", SD], input=("\nTERM 200,9999\n%s\nOFF\n" % body).encode(), cwd=SDSYS_DIR, capture_output=True, timeout=180)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", r.stdout.decode("latin1")).replace("\r", "")


def me_cmds(body):
    """TCL lines run by the installing user in an ordinary session of its own account."""
    r = subprocess.run([SD], input=("\nTERM 200,9999\n%s\nOFF\n" % body).encode(), cwd=ACCT, capture_output=True, timeout=120)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", r.stdout.decode("latin1")).replace("\r", "")


def put_as_account(rel, text):
    """Write a record of a DIRECTORY file of the account (bp) as root, owned like the account's own voc directory (user, group), mode 664."""
    p = os.path.join(ACCT, rel)
    subprocess.run(["sudo", "tee", p], input=text.encode(), capture_output=True)
    sh("sudo chown --reference='%s/voc' '%s'; sudo chmod 664 '%s'" % (ACCT, p, p))


# The account's VOC is a HASHED file (voc/%0, voc/%1): its records are not files.  Run 1-3 of 2 Nov read voc/<id> as a file - an instrument fault that made W1 pass
# for the wrong reason and planted the fixture's pointers as stray files.  The VOC is now read by the account's own session (CT) and written by an SDSYS program.
IO_PROG = """program zzm7io
   s = trim(@sentence)
   op = field(s, ' ', 4) ; pth = field(s, ' ', 5) ; id = field(s, ' ', 6) ; txt = field(s, ' ', 7, 99)
   openpath pth to f else crt 'ZZIO NOOPEN' ; stop
   if op = 'w' then
      convert '^' to @fm in txt
      write txt to f, id
      crt 'ZZIO WROTE ' : id
   end else
      delete f, id
      crt 'ZZIO DELETED ' : id
   end
end
"""


def io_setup():
    p = SDSYS_DIR + "/bp/zzm7io"
    subprocess.run(["sudo", "tee", p], input=IO_PROG.encode(), capture_output=True)
    sh("sudo chown sdsys:sdusers '%s'" % p)
    out = sdsys_cmds("BASIC bp zzm7io")
    return "Compiled 1 program(s) with no errors" in out, out


def voc_put(rid, fields):
    out = sdsys_cmds("RUN bp zzm7io w %s/voc %s %s" % (ACCT, rid, "^".join(fields)))
    return ("ZZIO WROTE " + rid) in out


def voc_del(rid):
    sdsys_cmds("RUN bp zzm7io d %s/voc %s" % (ACCT, rid))


def voc_read(rid):
    """The VOC record as the account's own session sees it (CT), or None when CT says it is not there."""
    out = me_cmds("CT VOC " + rid)
    body = out.split("CT VOC " + rid, 1)[-1]
    if re.search(r"not found|not on file", body, re.I) or not re.search(r"^\s*\d+:", body, re.M):
        return None
    return body


env = dict(os.environ, TERM="xterm", LC_ALL="C", LANG="C")
for k in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"):
    env.pop(k, None)
ARGV = ["/usr/bin/sudo", "/bin/sh", "-c", 'printf "%s\\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"', "sd-run", SD]
S = {"s": None}


def text():
    return "\n".join(l.rstrip() for l in S["s"].screen.lines())


def norm(t=None):
    return re.sub(r"[|\s]+", " ", text() if t is None else t)


def st():
    L = S["s"].screen.lines()
    return norm(L[40] if len(L) > 40 else "")


def typed(x, idle=0.9):
    S["s"].type(x, idle=idle)


def wait_for(pred, secs=15.0):
    end = time.time() + secs
    while time.time() < end:
        if pred(text()):
            return True
        S["s"].settle(0.3, limit=1.0)
    return pred(text())


def on():
    m = re.search(r"(?:VOC|Dictionary items|Programs) of ([^\s,]+)", norm())
    return m.group(1) if m else None


def walk_to(name):
    for direction in ("\x1b[B", "\x1b[A"):
        for _ in range(40):
            if on() == name:
                return True
            before = on()
            typed(direction, 0.5)
            if on() == before:
                S["s"].settle(0.5, limit=2.0)
                if on() == before:
                    break
    return on() == name


def filt(word):
    # 11 Nov 26: the filter is the Entries box's; in the Accounts box "/" looks for an account.  The page comes back from the editor with the keyboard in the
    #   Accounts box (its status line starts [Accounts]), so F6 first, and the status line is read again before anything is typed.
    for _ in range(3):
        if st().startswith("[Entries]"):
            break
        typed("\x1b[17~", 0.6)
    if not st().startswith("[Entries]"):
        print("        | filt(%r): the keyboard is not in the Entries box after F6 (status line %r); the row that follows cannot be believed" % (word, st()))
    typed("/", 1.0)
    typed(word + "\r", 1.5)


def ide_up(t):
    first = t.split("\n", 1)[0]
    return "File" in first and "Search" in first


def to_page():
    typed("\x11", 1.5)
    if not wait_for(lambda t: "Press Enter" in t, 6):
        typed("n", 1.0)
    wait_for(lambda t: "Press Enter" in t, 6)
    typed("\r", 2.0)
    wait_for(lambda t: "What this means" in t and "Press Enter" not in t, 10)


VOC_MADE = ["zm7new", "zm7own", "zsys.bp"]
FIX = {"bp_voc": False, "bpout_voc": False, "bp_dir": False}


def fixture():
    ok, out = io_setup()
    if not ok:
        return "the SDSYS helper zzm7io did not compile:\n" + out[-600:]
    FIX["bp_voc"] = voc_read("bp") is None                       # what the fixture adds, so that the cleanup takes away only that
    FIX["bpout_voc"] = voc_read("bp.out") is None
    FIX["bp_dir"] = sh("sudo test -d '%s/bp' && echo y" % ACCT).strip() != "y"
    if FIX["bp_dir"]:
        sh("sudo install -d -o $(sudo stat -c %%U '%s/voc') -g $(sudo stat -c %%G '%s/voc') -m 2775 '%s/bp'" % (ACCT, ACCT, ACCT))
    put_as_account("bp/zm7prog", "program zm7prog\n   crt 'M7 RAN IN ' : @who\nend\n")
    put_as_account("bp/zm7dbg", "program zm7dbg\n   crt 'DBG one'\n   x = 1\nend\n")
    sh("sudo rm -f '%s/bp.out/zm7prog' '%s/bp.out/zm7dbg'" % (ACCT, ACCT))
    for rid in ("zm7new", "zm7own"):
        voc_del(rid)
    if (FIX["bp_voc"] and not voc_put("bp", ["F", "bp"])) or not voc_put("zsys.bp", ["F", "@SDSYS/syscom"]):
        return "the fixture's VOC pointers bp / zsys.bp were not written"
    return ""


def cleanup():
    for rid in VOC_MADE + (["bp"] if FIX["bp_voc"] else []) + (["bp.out"] if FIX["bpout_voc"] else []):
        voc_del(rid)
    sh("sudo rm -f '%s/bp/zm7prog' '%s/bp/zm7dbg' '%s/bp.out/zm7prog' '%s/bp.out/zm7dbg'" % ((ACCT,) * 4))
    if FIX["bp_dir"]:
        sh("sudo rmdir '%s/bp' 2>/dev/null" % ACCT)
    if FIX["bpout_voc"]:
        sh("sudo rmdir '%s/bp.out' 2>/dev/null" % ACCT)
    sh("sudo rm -f %s/bp/zzm7io %s/bp.out/zzm7io" % (SDSYS_DIR, SDSYS_DIR))
    left = [r for r in VOC_MADE if voc_read(r) is not None] + [f for f in ("bp/zm7prog", "bp.out/zm7prog", "bp/zm7dbg") if sh("sudo test -e '%s/%s' && echo y" % (ACCT, f)).strip() == "y"]
    print("witness-entries: cleanup - the fixture's records and files still present: %s" % (left or "none"))


def main():
    print("witness-entries: user %s, account %s, SD %s, %s" % (ME, ACCT, SD, time.strftime("%F %T")))
    if not os.path.exists(SD) or sh("sudo test -d '%s/voc' && echo y" % ACCT).strip() != "y":
        print("witness-entries: CANNOT RUN - no SD at %s or no account directory %s" % (SD, ACCT))
        return 2
    grp = sh("sudo stat -c %%G '%s/voc'" % ACCT).strip()
    mem = sh("getent group %s" % grp).strip()
    reg = sh("sudo cat %s/accounts/%s" % (SDSYS_DIR, ME)).split("\n")
    row("W0 the delivered state: the account's voc belongs to group %s, which lists the sdsys user (S.103), and the account's voc gate (register field 10) is not yes" % grp,
        "sdsys" in mem.split(":")[-1].split(",") and reg[9].strip().lower() != "yes", "group: %s\nregister 1-12: %r" % (mem, reg[:12]))
    m_ctl, n_ctl = voc_read("menu"), voc_read("zm7none")
    row("W0b control of the reader: CT VOC in the user's own session finds the shipped entry menu and not zm7none", m_ctl is not None and n_ctl is None, repr((m_ctl, n_ctl)))
    bad = fixture()
    if bad:
        row("the fixture", False, bad)
        return finish(1)
    a0 = audit_count()
    gpl_m0 = mtime(SDSYS_DIR + "/syscom/keys.h")        # S.198: an install has no gpl.bp any more; syscom is the directory of SDSYS's own that stays

    # ---- the account is locked out of its own VOC (the gate), the disk unchanged
    out = me_cmds("ED VOC zm7own\nI\nX\nmine\n\nFI")
    row("W1 the user's own ordinary session cannot write its VOC: ED's FI says 'The VOC can only be changed by an account that has voc.edit' and there is no zm7own on the disk",
        "can only be changed by an account that has voc.edit" in out and voc_read("zm7own") is None, out[-600:])

    # ---- SDSYS's page
    S["old_default"] = sh("sudo cat %s/start.default 2>/dev/null" % SDSYS_DIR).strip()
    sdsys_cmds("set.start.default terminal")
    S["s"] = PtySession(ARGV, SDSYS_DIR, env, 140, 43)
    S["s"].settle(3.0)
    typed("tool.entries\r", 4.0)
    up = wait_for(lambda t: "What this means" in t, 15)
    got = up and walk_to(ME)
    row("W2 SDSYS's tool.entries draws on a real terminal and lists the user's account", got, text()[-800:])
    if not got:
        return finish(1)
    # 11 Nov 26: F6 goes to the Entries box.  This was Tab, which has moved no box since S.176 (8 Nov); with the keyboard left in the Accounts box the first
    #   real-install run (the Debian VM, b91adbee) passed W3 (N needs no box) and then filtered and pressed E on the wrong list: W4 to W10 red for the witness's own key.
    typed("\x1b[17~", 0.6)
    row("W2b F6 put the keyboard in the Entries box (the status line names it)", "[Entries]" in st(), repr(st()))

    # ---- N: a VOC entry written by the administrator in the locked-out account
    typed("n", 1.2)
    asked = "Id of the new VOC entry in %s" % ME in norm()
    typed("zm7new\r", 2.5)
    up_n = wait_for(ide_up, 12)
    typed("X\rmade by sdsys", 0.8)
    typed("\x13", 2.5)
    ide_after = text()
    to_page()
    rec = voc_read("zm7new")
    row("W3 N asks the id, the IDE opens, Ctrl-S writes zm7new INTO the user's VOC (read back by the account's own CT; the account cannot write it itself: W1)",
        asked and up_n and rec is not None and "made by sdsys" in rec and re.search(r"^\s*0*1:\s*X\s*$", rec, re.M) is not None, repr((asked, up_n, rec, st())) + "\nthe IDE after Ctrl-S:\n" + ide_after)

    # ---- E: change it
    filt("zm7new")
    after_filter = text()                              # 11 Nov 26: kept for the row's detail - the first real-install run failed here and its output did not show the list E was pressed on
    typed("e", 1.2)
    up_e = wait_for(ide_up, 12)
    if not up_e:
        print("        | W4: E did not open the IDE.  The page after the filter, before E:\n" + "\n".join("        |   " + l for l in after_filter.split("\n")[:22]))
        print("        | ...and after E:\n" + "\n".join("        |   " + l for l in text().split("\n")[:22]))
    typed("\x1b[B", 0.3)
    typed("\x1b[F", 0.3)
    typed(" and edited", 0.5)
    typed("\x13", 1.8)
    to_page()
    rec = voc_read("zm7new") or ""
    row("W4 E opens zm7new in the IDE and the change is on the disk; the page says it came back from the editor",
        up_e and "made by sdsys and edited" in rec and "back from the editor" in st(), repr((up_e, rec, st())))

    # ---- the pointer rule against SDSYS's own syscom (S.198: an install has no gpl.bp)
    typed("k", 1.2)
    typed("k", 1.2)
    filt("keys.h")
    rows = norm()
    typed("e", 1.5)
    st_e, up_x = st(), ide_up(text())
    typed("c", 2.5)
    st_c = st()
    row("W5 the pointer zsys.bp (to @SDSYS/syscom) lists keys.h marked >; E and C on it are refused with 'lies outside %s', no editor, no compile; syscom/keys.h unchanged" % ME,
        re.search(r"zsys\.bp > keys\.h\b", rows) is not None and "lies outside " + ME in st_e and not up_x and "lies outside " + ME in st_c
        and mtime(SDSYS_DIR + "/syscom/keys.h") == gpl_m0, repr((st_e, st_c, gpl_m0)) + "\n" + text())
    if up_x:
        to_page()

    # ---- C: compile in the account, and the user then runs it
    filt("zm7prog")
    typed("c", 7.0)
    box = norm()
    typed("\r", 2.0)
    st_k = st()
    obj = owner("bp.out/zm7prog")
    row("W6 C compiles zm7prog IN the user's account through run.in: the compiler's success line, the status line, the object in the account's bp.out (%s), none in SDSYS's" % obj,
        "Compiled 1 program(s) with no errors" in box and "compiled zm7prog in %s" % ME in st_k and disk("bp.out/zm7prog") is not None
        and sh("sudo test -e %s/bp.out/zm7prog && echo y" % SDSYS_DIR).strip() != "y", repr((box[box.find("Compile"):][:300], st_k, obj)))
    out = me_cmds("RUN bp zm7prog")
    row("W7 the user's own ordinary session runs the object the administrator compiled (it can read it): 'M7 RAN IN %s'" % ME, ("M7 RAN IN " + ME) in out, out[-400:])

    # ---- B: debug in the account
    filt("zm7dbg")
    typed("b", 1.0)
    came = wait_for(lambda t: any(ln.rstrip() == DBG_KEYS for ln in S["s"].screen.lines()[-4:]), 25)
    scr = text()
    typed("q\r", 2.0)
    paused = wait_for(lambda t: "Press Enter to return" in t, 10)
    typed("\r", 2.5)
    wait_for(lambda t: "What this means" in t, 10)
    row("W8 B gives the terminal to the debugger IN the account (its key row; the object in the account's bp.out), Q and Enter bring the page back",
        came and disk("bp.out/zm7dbg") is not None and paused and "back from the debugger: zm7dbg was debugged in " + ME in st(), repr((came, paused, st(), scr[-400:])))

    # ---- D: delete the VOC entry after its id is typed
    typed("k", 1.2)
    filt("zm7new")
    typed("d", 1.5)
    dbox = norm()
    typed("r", 1.2)
    typed("zm7new\r", 2.5)
    row("W9 D on zm7new (there before: W4): the box names the record and the account, Run with the id typed deletes it - the account's own CT no longer finds it",
        "Delete this record?" in dbox and voc_read("zm7new") is None and "deleted zm7new from" in st(), repr((dbox[dbox.find("Delete"):][:300], st())))

    typed("\x11", 1.5)
    typed("OFF\r", 1.5)
    a = audit_since(a0)
    want = {"master edit (N)": r"master edit account=%s kind=voc file=\S* ?id=zm7new new=1" % ME, "master edit (E)": r"master edit account=%s kind=voc file=\S* ?id=zm7new new=0" % ME,
            "master compile": r"master compile account=%s file=bp id=zm7prog result=ok" % ME, "master debug": r"master debug account=%s file=bp id=zm7dbg" % ME,
            "master delete": r"master delete account=%s kind=voc file=\S* ?id=zm7new" % ME, "run.in": r"run\.in begin account=%s command=basic bp zm7prog" % ME}
    lost = [k for k, rx in want.items() if not re.search(rx, a)]
    row("W10 the audit trail has the page's lines for N, E, C, B, D and run.in's own begin line (lower case)", not lost, "missing: %s\n%s" % (lost, "\n".join(ln for ln in a.splitlines() if "master" in ln or "run.in" in ln)[-1500:]))
    return finish(0)


def finish(rc):
    try:
        if S["s"] is not None:
            S["s"].finish()
    except Exception:
        pass
    old = S.get("old_default")
    if old is not None:
        sdsys_cmds("set.start.default %s" % old if old else "set.start.default menu")
        if not old:
            sh("sudo rm -f %s/start.default" % SDSYS_DIR)
    cleanup()
    print("witness-entries: %d passed, %d failed -> %s" % (passed, failed, "PASSED" if failed == 0 and passed > 0 and rc == 0 else "FAILED"))
    return 0 if failed == 0 and passed > 0 and rc == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("witness-entries: STOPPED by %r" % e)
        sys.exit(finish(1))
