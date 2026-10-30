#!/usr/bin/env python3
#
# sandbox-tool-masters.py - the master files page, TOOL.MASTERS, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A7; plan .claude/plan-fullscreen-toolkit.md section 5).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-masters.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN, the person who runs this suite) opens TOOL.MASTERS on a 140 by 43 terminal.  The page runs the REAL sync.masters.
#
# THE INSTRUMENT.  The page is judged against SD, not against itself: for every account the number of differences the page shows is compared with the number the verb CHECK.MASTERS
# prints for it (run by a separate administrator session AFTER the page has read, since the verb applies the journal and a page that did not would then differ), and what a sync did is
# read from the disk (the master files and the journal exist or not), from CHECK.MASTERS and from the audit file.
#
#   M0   an ordinary account has no tool.masters
#   M1   the master files are not set up: the page says so in the verb's words, lists no account, refuses Y, and P shows the journal's box; opening it writes one audit line
#   M2   S sets them up: the box says what it does, Esc runs nothing (no files on the disk), Run makes the files, the journal and the audit line, and the page then shows every account
#        with the number of differences CHECK.MASTERS gives for it
#   M3   an account made after the set-up (no master copies yet): the page and the verb agree on its differences, all of the kind missing; Y shows sync.masters NAME and that the flags are
#        not cleared, Esc runs nothing, Run makes it match
#   M4   a VOC record written by an ordinary session sits in the journal: P shows the journal's lines and the count; F5 applies them and the page shows no difference for it, as the verb
#   M5   an account that is no longer registered: its copies are listed as not registered, Y is refused in words, S removes them
#   M6   the mouse, F5, F1; a window under 140 by 43 gets no page; the page ends when its input ends
# NOT HELD: the stale and resync flags (a sandbox cannot make a journal write fail or overflow), a real install, the help text itself (sandbox-docs.py).
import getpass
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_toolmasters", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
MUTANT = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
NEWACC = "zmnew"
JOURNAL_ACC = "zzhd"

# an ordinary session writes a record in its own account's VOC: the file-change hook journals it
WRITER = """   open 'voc' to v else
      crt 'ZZJW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$zzjw' to v, 'zzjw1' on error
      crt 'ZZJW refused ':status()
      stop
   end
   crt 'ZZJW written'
end
"""

MUTANTS = {
    # name: (old text of the sandbox's tool_masters, new text, the row ids that must fail and no others, the last section run)
    "sync-wrong-account": ("   sent = 'sync.masters ' : anm<ci>\n", "   sent = 'sync.masters ' : anm<na>\n", ["M3"], "M3"),       # the LAST account: zmnew sorts first, so anm<1> would have been the right account
    "no-drain": ("      void kernel(K$MASTERS, 'drain')", "      void kernel(K$MASTERS, 'ready')", ["M4"], "M4"),
    "orphan-offered": ("   if aorph<ci> = 1 then\n      msg = anm<ci> : ' is not a registered account: S removes its master copies'\n      return\n   end\n", "", ["M5"], "M5"),
}


def arow(rid, name, ok, detail=""):
    """A row with an id (M3 ...): the mutant mode compares the ids that failed with the ids that had to."""
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def box():
    return sh.BOX


def st(h):
    return h.line(40)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def audit_off():
    path = os.path.join(sh.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    if off is None:
        return None
    try:
        with open(os.path.join(sh.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def files_exist():
    """(the master files, the journal) as they are on the disk."""
    return (all(os.path.isdir(os.path.join(sh.SYS, d)) or os.path.exists(os.path.join(sh.SYS, d)) for d in ("voc_master", "dict_master", "master_state")),
            os.path.exists(os.path.join(sh.SYS, "$master.journal")))


def verb_check():
    """CHECK.MASTERS as a separate administrator session prints it: ({account: n}, [rows], the lines).  The verb applies the journal first."""
    out = g.adm(["CHECK.MASTERS"])
    counts = {}
    kinds = {}
    for ln in out:
        m = re.match(r"^(missing|differs|extra|nonwritable|norights|toolong|unreadable): (\S+) (.*)$", ln)
        if m:
            counts[m.group(2)] = counts.get(m.group(2), 0) + 1
            kinds.setdefault(m.group(2), set()).add(m.group(1))
    return counts, kinds, out


def registered():
    return sorted(os.listdir(os.path.join(sh.SYS, "accounts")))


def setup_masters_page():
    shutil_copy = __import__("shutil").copyfile
    shutil_copy(os.path.join(TREE, "sdsys", "gpl.bp", "tool_masters"), os.path.join(sh.SYS, "gpl.bp", "tool_masters"))
    out = g.adm(["BASIC gpl.bp tool_masters"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_masters did not compile in the sandbox:\n" + "\n".join(out[-8:]))
    # the writer is an ORDINARY program compiled into the account that runs it
    g.put(os.path.join(g.BOX, "user_accounts", JOURNAL_ACC, "bp", "zzjw"), WRITER)
    out = g.plain(JOURNAL_ACC, ["BASIC bp zzjw"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the writer program did not compile in %s:\n%s" % (JOURNAL_ACC, "\n".join(out[-6:])))


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_masters")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_masters"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    """A session on tool.masters on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.masters\r", idle=3.5)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.6):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def typed(self, s, idle=0.9):
        self.h.typed(s, idle=idle)

    def idle(self, seconds):
        self.h.s.settle(seconds)

    def top(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(2, 7)))

    def visible(self):
        out = {}
        for n in range(11, 22):
            ln = self.line(n)
            name = ln[3:29].strip()
            if name:
                out[name] = (ln[29:61].strip(), ln[61:].strip().rstrip("|").strip())
        return out

    def collect(self):
        """Every account the list shows, scrolling with Page Down from the top."""
        self.key("home", 0.5)
        seen = dict(self.visible())
        for _ in range(8):
            before = len(seen)
            self.key("pgdn", 0.6)
            seen.update(self.visible())
            if len(seen) == before:
                break
        self.key("home", 0.5)
        return seen

    def diffs_box(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(25, 30)))

    def words(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(31, 38)))

    def under_cursor(self):
        m = re.match(r"(\S+) has \d+ difference", self.words()) or re.match(r"Every master copy of (\S+) matches", self.words()) or re.match(r"(\S+) is not a registered account", self.words())
        return m.group(1) if m else None

    def to_account(self, name):
        self.key("home", 0.5)
        for _ in range(60):
            if self.under_cursor() == name:
                return True
            self.key("down", 0.35)
        return False

    def end(self):
        self.h.end()

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def count_of(state):
    if state == "in sync":
        return 0
    m = re.match(r"(\d+) difference", state) or re.match(r"not registered: (\d+) to remove", state)
    return int(m.group(1)) if m else None


def page_counts(p):
    seen = p.collect()
    return {n: count_of(s) for n, (s, _f) in seen.items()}, seen


def agree(p, label):
    """The differential row: the page's number for every account equals CHECK.MASTERS's; returns (ok, detail)."""
    pc, seen = page_counts(p)
    vc, kinds, out = verb_check()
    want = {n: vc.get(n, 0) for n in set(list(pc) + list(vc))}
    got = {n: (pc.get(n) if pc.get(n) is not None else None) for n in want}
    summ = next((ln for ln in out if ln.startswith("Checked ")), "")
    return got == want and all(v is not None for v in pc.values()), "%s: page %s, verb %s, %s" % (label, {k: v for k, v in pc.items() if v}, {k: v for k, v in vc.items()}, summ)


def section_m0():
    say("\n--- M0: an ordinary account has no tool.masters")
    out = g.plain("zzhd", ["tool.masters"])
    T = norm(" ".join(out))
    arow("M0", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)", "Master files" not in T and "Accounts" not in T and len(out) > 0, T[:300])


def section_m1():
    say("\n--- M1: the master files are not set up")
    on, oj = files_exist()
    if on or oj:
        bail("the sandbox already has master files (%s %s), so the not-set-up rows cannot be run" % (on, oj))
    verb = g.adm(["CHECK.MASTERS"])
    a0 = audit_off()
    p = Page()
    T = p.text()
    if "Master files" not in T:
        dump(p.h)
        bail("tool.masters never drew its page, so no row below can be believed")
    new = audit_new(a0) or ""
    arow("M1a", "opening the page writes one audit line, 'tool start app=tool.masters', and no other", len(re.findall(r"tool start app=tool\.masters$", new, re.M)) == 1 and "sync.masters" not in new, repr(new[-200:]))
    top = p.top()
    arow("M1b", "the page says the master files have not been set up, in the verb's own words (message 11564), and lists no account",
         "The master files have not been set up on this system" in top and has(verb, r"have not been set up on this system") and not p.visible(), repr((top[:200], p.visible())))
    p.key("y", 1.0)
    arow("M1c", "Y is refused in words, and no box opens", "the master files are not set up: S sets them up" in st(p.h) and "Cancel" not in p.text(), st(p.h))
    p.key("p", 1.0)
    arow("M1d", "P changes the lower box to the journal's, and back", "The journal: lines not yet applied" in p.text(), p.text()[-300:])
    p.key("p", 1.0)
    arow("M1e", "... and back to the account box", "The account under the cursor" in p.text() and "The journal: lines not yet applied" not in p.text(), "")
    return p


def section_m2(p):
    say("\n--- M2: S sets the files up")
    a0 = audit_off()
    p.key("s", 1.5)
    T = norm(p.text())
    arow("M2a", "S shows the command and, because the files are not set up, says what it sets up", "sync.masters" in T and "are set up in the SDSYS account" in T and "master copy of every registered account" in T, T[-600:])
    p.key("esc", 1.2)
    on, oj = files_exist()
    arow("M2b", "Esc runs nothing: no master file and no journal on the disk, no audit line", "nothing was run" in st(p.h) and not on and not oj and "sync.masters" not in (audit_new(a0) or ""), repr((st(p.h), on, oj, audit_new(a0))))
    p.typed("s", idle=1.3)
    p.typed("r", idle=6.0)
    new = audit_new(a0) or ""
    on, oj = files_exist()
    arow("M2c", "Run: the master files and the journal are on the disk, the audit trail has the verb's line, and the page says it ran", on and oj and re.search(r"sync\.masters account=\*$", new, re.M) is not None and "sync.masters ran (status 0)" in st(p.h),
         repr((on, oj, new[-200:], st(p.h))))
    top = p.top()
    arow("M2d", "the page now says the master files are set up and lists accounts", "The master files are set up." in top and len(p.visible()) > 0, repr((top[:200], p.visible())))
    ok, detail = agree(p, "after the first sync")
    arow("M2e", "for every account the page shows the number of differences CHECK.MASTERS prints (a differential: the verb is run after the page has read)", ok, detail)
    summ = re.search(r"Checked (\d+) account\(s\): (\d+) difference\(s\)", p.top())
    arow("M2f", "the page's own count line equals the number of registered accounts", summ is not None and int(summ.group(1)) == len(registered()), repr((summ.group(0) if summ else None, len(registered()))))
    return p


def section_m3(p):
    say("\n--- M3: an account made after the set-up")
    g.FIXTURES[NEWACC] = ("no", "no")
    g.build_account(NEWACC)                        # made and registered, after the set-up: no master copies yet
    p.key("f5", 6.0)
    ok, detail = agree(p, "the new account")
    pc, seen = page_counts(p)
    vc, vk, _o = verb_check()
    arow("M3a", "the page and the verb agree, and the new account has many differences of which some are the kind missing", ok and pc.get(NEWACC, 0) > 50 and "missing" in vk.get(NEWACC, set()), repr((pc.get(NEWACC), seen.get(NEWACC), vk.get(NEWACC), detail[:300])))
    arow("M3b", "the account under the cursor: its differences are listed in the box below and the plain words say what missing means",
         p.to_account(NEWACC) and p.diffs_box() != "" and "the account has a record the master copy lacks" in p.words(), repr((p.under_cursor(), p.diffs_box()[:150], p.words()[:300])))
    a0 = audit_off()
    p.key("y", 1.5)
    T = norm(p.text())
    arow("M3c", "Y shows 'sync.masters %s' and says the stale and resync flags are not cleared" % NEWACC, ("sync.masters %s" % NEWACC) in T and "NOT cleared by this" in T, T[-500:])
    p.key("esc", 1.2)
    vc, _k, _o = verb_check()
    arow("M3d", "Esc runs nothing: the account still has its differences and the audit trail has no sync line", "nothing was run" in st(p.h) and vc.get(NEWACC, 0) > 50 and "sync.masters" not in (audit_new(a0) or ""), repr((st(p.h), vc.get(NEWACC))))
    p.typed("y", idle=1.3)
    p.typed("r", idle=4.0)
    new = audit_new(a0) or ""
    vc, _k, out = verb_check()
    arow("M3e", "Run: the verb finds no difference for the account, the audit trail has 'sync.masters account=%s', and the page lists it as in sync" % NEWACC,
         vc.get(NEWACC, 0) == 0 and ("sync.masters account=%s" % NEWACC) in new and page_counts(p)[0].get(NEWACC) == 0, repr((vc.get(NEWACC), new[-200:], st(p.h))))
    ok, detail = agree(p, "after syncing the new account")
    arow("M3f", "the page and the verb still agree for every account", ok, detail)


def section_m4(p):
    say("\n--- M4: a record in the journal")
    a0 = audit_off()
    out = g.plain(JOURNAL_ACC, ["RUN bp zzjw"])
    pend = g.adm(["LIST.MASTER.PENDING"])
    m = re.search(r"holds (\d+) byte\(s\) and (\d+) line\(s\)", " ".join(pend))
    arow("M4a", "an ordinary session wrote a VOC record and the journal holds its line (LIST.MASTER.PENDING)", has(out, r"^ZZJW written$") and m is not None and int(m.group(2)) >= 1, repr((out[-2:], pend[:4])))
    p.key("p", 1.5)
    top = p.top()
    jl = norm(" ".join(p.line(n)[3:137] for n in range(25, 30)))
    arow("M4b", "P shows the journal's box with a line in it, and the count the verb gave", "The journal: lines not yet applied" in p.text() and re.search(r"holds \d+ byte\(s\) and %s line\(s\)" % (m.group(2) if m else "?"), top) is not None
         and jl != "" and "Nothing is waiting" not in jl, repr((top[:200], jl[:200])))
    p.key("p", 1.0)
    p.key("f5", 6.0)
    arow("M4c", "F5 applies the journal: the page says nothing is waiting", "Nothing is waiting in the journal" in p.top(), p.top()[:200])
    ok, detail = agree(p, "after the journal was applied")
    arow("M4d", "the page and the verb agree for every account: the journalled record is not shown as a difference", ok, detail)


def section_m5(p):
    say("\n--- M5: an account that is no longer registered")
    os.remove(os.path.join(sh.SYS, "accounts", NEWACC))
    p.key("f5", 6.0)
    pc, seen = page_counts(p)
    vc, kinds, out = verb_check()
    arow("M5a", "its copies are listed as not registered, with the number the verb gives, of the kind extra", NEWACC in seen and seen[NEWACC][0].startswith("not registered:") and pc.get(NEWACC) == vc.get(NEWACC, -1) and pc.get(NEWACC, 0) > 50 and kinds.get(NEWACC) == {"extra"},
         repr((seen.get(NEWACC), pc.get(NEWACC), vc.get(NEWACC), kinds.get(NEWACC))))
    p.to_account(NEWACC)
    arow("M5b", "the plain words say it is not registered and that S removes the copies", "is not a registered account" in p.words() and "S removes them" in p.words(), p.words()[:200])
    a0 = audit_off()
    p.key("y", 1.2)
    T = norm(p.text())
    arow("M5c", "Y on it is refused in words and no box opens", "is not a registered account: S removes its master copies" in st(p.h) and "taken out" not in T and "sync.masters" not in (audit_new(a0) or ""), repr(st(p.h)))
    p.key("s", 1.5)
    T = norm(p.text())
    arow("M5d", "S shows 'sync.masters' and that it makes the copies of EVERY registered account match and removes those of accounts that are not registered (single words: the box wraps its text)",
         "sync.masters" in T and "EVERY" in T and "removed" in T and "Cancel" in T, T[-500:])
    p.typed("r", idle=6.0)
    vc, kinds, out = verb_check()
    seen = p.collect()
    new = audit_new(a0) or ""
    arow("M5e", "Run: the verb finds no copy of the account, the page no longer lists it, and the audit trail has 'sync.masters account=*'", vc.get(NEWACC, 0) == 0 and NEWACC not in seen and re.search(r"sync\.masters account=\*$", new, re.M) is not None, repr((vc.get(NEWACC), NEWACC in seen, new[-160:])))


def section_m6(p):
    say("\n--- M6: the mouse, F5, F1; a small window; an input that ends")
    seen = p.visible()
    names = list(seen)
    p.h.click(20, 11 + 1)
    arow("M6a", "a click on the second row puts the cursor there", p.under_cursor() == names[1], repr((p.under_cursor(), names[:3])))
    p.key("f5", 5.0)
    arow("M6b", "F5 checks again and says so", "checked again" in st(p.h), st(p.h))
    p.h.click(135, 2)
    T = norm(p.text())
    arow("M6c", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("M6d", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.masters\r", idle=3.0)
    T = h.text()
    arow("M6e", "a window under 140 by 43 gets no page (the toolkit's one size check)", "The account under the cursor" not in T and "Master files" not in T, T[-300:])
    h.end()
    env = dict(os.environ, SD_CONFIG=os.path.join(box(), "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(box(), "m6-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.masters\n")
    pr.stdin.flush()
    time.sleep(4)
    pr.stdin.close()
    try:
        pr.wait(timeout=20)
        ended = True
    except subprocess.TimeoutExpired:
        ended = False
        pr.kill()
        pr.wait()
    fh.close()
    with open(os.path.join(box(), "m6-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("M6f", "a page whose input ends ends by itself within 20 seconds; the output shows it did start (the null case)", ended and "The account under the cursor" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-masters.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    global MUTANT
    MUTANT = mutant
    last = MUTANTS[mutant][3] if mutant else "M6"
    order = ["M3", "M4", "M5", "M6"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    p = None
    try:
        sh.setup("sandbox-tool-masters.py")
        setup_masters_page()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-masters: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_m0()
        p = section_m1()
        p = section_m2(p)
        if run("M3"):
            section_m3(p)
        if run("M4"):
            section_m4(p)
        if run("M5"):
            section_m5(p)
        if mutant is None:
            section_m6(p)
        else:
            p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-masters: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"M\d+", i).group(0) for i in FAILED_IDS if re.match(r"M\d+", i)})
        ok = want == got
        say("sandbox-tool-masters: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
