#!/usr/bin/env python3
#
# sandbox-tool-backups.py - the backups page, TOOL.BACKUPS, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A8; plan .claude/plan-fullscreen-toolkit.md section 5).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-backups.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  The administrator's session opens TOOL.BACKUPS on a 140 by 43 terminal.  The sandbox's sd.conf gets a BACKUPDIR line pointing at a directory this suite fills with archives it
# builds with Python's zipfile (a manifest.txt of the documented format and a tree per account), and is put back at the end whatever happens.  The REAL verbs backup.account,
# restore.account and set.backup.directory are what the page runs.
#
# WHAT A SANDBOX CANNOT DO.  The packing of a backup and the placing of a restored account are done as ROOT (sd-elevate backup-pack, restore-place), which this suite is not, so no row
# here shows a backup made or an account restored: those are witness-backup.sh on a real install.  What the rows do show: the page lists the directory and the archives as the disk and
# the manifests give them; it shows no box while another session is signed on; every box is what the page says it is and Cancel runs nothing; the sentences the page builds are the ones
# the verb receives (the audit trail and the verb's own words are the evidence); a restore the page lets through is one the verb then REFUSES, here because the archive's manifest does
# not match its tree (13013: nothing is changed), and the accounts' files are the same afterwards.
#
#   B0   an ordinary account has no tool.backups; a VOC entry that points at the program gets the page's own refusal
#   B1   no directory saved: the page says so and B is refused in words
#   B2   the directory holds four SD-*.zip and some decoys: the list is the archives, newest first, with sizes from the disk, account counts and products from the manifests; the box at the foot
#        shows the manifest of the one under the cursor, and says so when a manifest cannot be read
#   B3   another session is signed on: the page names it, B, A and R show no box; when it has gone F5 says the way is clear
#   B4   B and A: the box shows the sentence and Cancel runs nothing; Run runs the real verb and the page shows its words; a bad name is refused before any box
#   B5   R: an archive holding an account that is not registered is refused by the page; one that is registered shows the accounts and wants RESTORE typed (a wrong word runs nothing); with the
#        right word the real verb refuses the mismatched archive and the accounts' files are the same
#   B6   D: a relative path is refused; an absolute one is shown in a box and run, and the directory the page shows is the one the verb reports
#   B7   the mouse, F1, a small window, an input that ends; the archives and sd.conf's other lines are untouched by looking
# NOT HELD: a backup that is made, a restore that places an account (witness-backup.sh), the help text itself (sandbox-docs.py).
import getpass
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_toolbackups", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
MUTANT = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ACC = "zzhd"
OTHER = "zzhm"
WRITER = """   open 'voc' to v else
      crt 'ZZBW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$tool_backups' to v, 'ztbak' on error
      crt 'ZZBW refused ':status()
      stop
   end
   crt 'ZZBW written'
end
"""

MUTANTS = {
    # name: (old text of the sandbox's tool_backups, new text, the row ids that must fail and no others, the last section run)
    "check-skipped": ("do.backup.all:\n   gosub check.alone\n   if not(others_ok) then return\n", "do.backup.all:\n", ["B3"], "B3"),
    "register-unchecked": ("   if missing # '' then\n      msg = 'the archive holds accounts that are not registered here", "   if 0 then\n      msg = 'the archive holds accounts that are not registered here", ["B5"], "B5"),
    "typed-dropped": ("   typed = 'RESTORE'\n", "   typed = ''\n", ["B5"], "B5"),
}

# ------------------------------------------------------------------------------------------------------------------------------- the fixture archives

HOST = "boxy"
ARCHIVES = [
    # file name, product, accounts (name, files, bytes, dirs written in the manifest), what the zip really holds per account (files)
    ("SD-%s-all-20261024-101500.zip" % HOST, "sd-core-linux", [("zzhd", 3, 30, 1), (OTHER, 2, 20, 1)], {"zzhd": 1, OTHER: 1}),
    ("SD-%s-zzhd-20261025-091500.zip" % HOST, "sd-core-linux", [("zzhd", 1, 10, 1)], {"zzhd": 1}),
    ("SD-%s-ghost-20261025-120000.zip" % HOST, "sd-core-linux", [("zzghost", 1, 10, 1)], {"zzghost": 1}),
]
BAD = "SD-junk-20260101-000000.zip"
DECOYS = ["notes.zip", "SD-readme.txt", "backup.tar"]


def make_zip(path, product, accounts, held):
    m = ["format: 1", "product: " + product, "sd.version: L1.2-0", "created: 2026-10-25T10:00:00", "host: " + HOST, "source.root: /home/sd/user_accounts", "accounts: %d" % len(accounts)]
    for name, files, size, dirs in accounts:
        m += ["", "[account %s]" % name, "description: fixture", "suspended: 0", "source.path: /home/sd/user_accounts/%s" % name, "files: %d" % files, "bytes: %d" % size, "dirs: %d" % dirs]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.txt", "\n".join(m) + "\n")
        for name, n in held.items():
            z.writestr("accounts/%s/" % name, "")
            for i in range(n):
                z.writestr("accounts/%s/f%d.txt" % (name, i), "x" * 10)


def bakdir():
    return os.path.join(sh.BOX, "bak")


def conf_path():
    return os.path.join(sh.BOX, "sd.conf")


def read_conf():
    return open(conf_path(), encoding="latin-1").read()


def write_conf(text):
    with open(conf_path(), "w", encoding="latin-1") as f:
        f.write(text)


def make_fixtures():
    d = bakdir()
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for name, product, accts, held in ARCHIVES:
        make_zip(os.path.join(d, name), product, accts, held)
    with open(os.path.join(d, BAD), "wb") as f:
        f.write(b"this is not a zip file at all")
    for n in DECOYS:
        with open(os.path.join(d, n), "wb") as f:
            f.write(b"decoy")


def disk_archives():
    """The SD-*.zip files of the directory, newest first by the time in the name."""
    d = bakdir()
    names = [n for n in os.listdir(d) if n.startswith("SD-") and n.endswith(".zip") and len(n) > 20]
    return sorted(names, key=lambda n: n[-19:-4], reverse=True)


def audit_lines():
    try:
        return [ln for ln in open(os.path.join(sh.SYS, "audit"), "rb").read().decode("latin-1").split("\n") if ln != ""]
    except OSError:
        return []


def tree_state(account):
    """A hash of every file of the account's directory (names and contents), to show a refused restore changed nothing."""
    root = os.path.join(sh.BOX, "user_accounts", account)
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(root)):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            try:
                h.update(p.encode() + open(p, "rb").read())
            except OSError:
                h.update(p.encode() + b"?")
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------------------------- the page

def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def st(h):
    return h.line(40)


def setup_pages():
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_backups"), os.path.join(sh.SYS, "gpl.bp", "tool_backups"))
    out = g.adm(["BASIC gpl.bp tool_backups"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_backups did not compile in the sandbox:\n" + "\n".join(out[-8:]))
    with open(os.path.join(sh.SYS, "audit"), "ab"):                 # a session appends to the audit file and never makes it
        pass
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzbw"), WRITER)


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_backups")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_backups"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    """A session on tool.backups on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.backups\r", idle=4.0)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.8):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def top(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(2, 6)))

    def rows(self):
        out = []
        for y in range(9, 26):
            t = self.line(y)[3:137]
            if t.strip():
                out.append({"when": t[0:21].strip(), "size": t[21:33].strip(), "acc": t[35:44].strip(), "prod": t[44:56].strip(), "name": t[56:].strip().rstrip("|").strip()})
        return out

    def detail(self):
        return [self.line(y)[3:137].rstrip().rstrip("|").rstrip() for y in range(28, 39)]

    def ask(self, text):
        self.h.typed(text + "\r", idle=1.0)

    def end(self):
        self.h.end()

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def box_open(p):
    T = norm(p.text())
    return "Cancel" in T and "Run" in T


# ------------------------------------------------------------------------------------------------------------------------------- the sections

def section_b0():
    say("\n--- B0: an ordinary account")
    out = g.plain(ACC, ["tool.backups"])
    T = norm(" ".join(out))
    arow("B0a", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)", "Archives" not in T and "The archive under the cursor" not in T and len(out) > 0, T[:300])
    out = g.plain(ACC, ["BASIC bp zzbw", "RUN bp zzbw"])
    wrote = has(out, r"^ZZBW written$")
    out = g.plain(ACC, ["ztbak"])
    T = norm(" ".join(out))
    arow("B0b", "a VOC entry an ordinary account made for the program gets the page's own refusal (message 11800), not 'not a command', and no page", wrote and "is for the administrator only" in T and "The archive under the cursor" not in T, repr((wrote, T[:300])))


def section_b1():
    say("\n--- B1: no directory saved")
    if "BACKUPDIR" in read_conf().upper():
        bail("the sandbox's sd.conf already holds a BACKUPDIR line, so the none-saved rows cannot be run")
    a0 = len(audit_lines())
    p = Page()
    if "The archive under the cursor" not in p.text():
        dump(p.h)
        bail("tool.backups never drew its page, so no row below can be believed")
    mine = [ln for ln in audit_lines()[a0:] if " tool " in ln]
    arow("B1a", "opening the page wrote one audit line, 'tool start app=tool.backups', and no other 'tool' line", len(mine) == 1 and mine[0].endswith("tool start app=tool.backups"), repr(mine))
    top = p.top()
    arow("B1b", "the top box says no backup directory has been saved, the list is empty and the foot box says there is no directory to look in", "No backup directory has been saved" in top and p.rows() == [] and "There is no directory to look in" in norm(p.text()), top[:200])
    p.key("b", 1.0)
    arow("B1c", "B is refused in words and no box opens", "no backup directory has been saved: D saves one first" in st(p), st(p) + " | " + ("box" if box_open(p) else "no box"))
    return p


def section_b2(p, orig):
    say("\n--- B2: the archives")
    make_fixtures()
    write_conf(orig.rstrip("\n") + "\nBACKUPDIR=" + bakdir() + "\n")
    p.key("f5", 2.5)
    top = p.top()
    names = disk_archives()
    rows = p.rows()
    arow("B2a", "the top names the directory the file says and the number of archives the disk holds (%d: the four SD-*.zip, not the decoys)" % len(names), ("Directory: " + bakdir()) in top and ("Archives: %d" % len(names)) in top, top[:240])
    got = [r["name"] for r in rows]
    arow("B2b", "the list is exactly those archives, newest first by the time in the name, and none of the decoys (notes.zip, SD-readme.txt, backup.tar)", got == names and not any(d in " ".join(got) for d in DECOYS), repr((got, names)))
    bad = []
    for r in rows:
        fp = os.path.join(bakdir(), r["name"])
        stamp = r["name"][-19:-4]
        want_when = "%s-%s-%s %s:%s:%s" % (stamp[0:4], stamp[4:6], stamp[6:8], stamp[9:11], stamp[11:13], stamp[13:15])
        if r["size"] != str(os.path.getsize(fp)) or r["when"] != want_when:
            bad.append((r["name"], r["when"], want_when, r["size"], os.path.getsize(fp)))
    arow("B2c", "each row's time is the one in its name and its size is the disk's", not bad and len(rows) == len(names), repr(bad[:2]))
    by = {a[0]: a for a in ARCHIVES}
    bad = []
    for r in rows:
        if r["name"] in by:
            a = by[r["name"]]
            if r["acc"] != str(len(a[2])) or r["prod"] != a[1][:11]:
                bad.append((r["name"], r["acc"], r["prod"]))
        elif r["name"] == BAD:
            if r["acc"] != "?" or r["prod"] != "?":
                bad.append((r["name"], r["acc"], r["prod"]))
    arow("B2d", "the account count and the product of each row are the manifest's, and a file that is not a zip shows ? for both", not bad and len(rows) == len(names), repr(bad[:3]))
    p.key("home", 0.8)
    first = rows[0]["name"]
    d = p.detail()
    a = by.get(first)
    ok = a is not None and ("product: " + a[1]) in d[0] and "sd.version: L1.2-0" in d[0] and ("host: " + HOST) in d[0] and d[2].split() == ["Account", "Files", "Bytes", "Directories"]
    for k, (name, files, size, dirs) in enumerate(a[2] if a else []):
        ok = ok and d[3 + k].split() == [name, str(files), str(size), str(dirs)]
    arow("B2e", "the foot box for the first archive shows its manifest: product, version, host, and each account with the files, bytes and directories the manifest gives", ok, repr(d[:6]))
    p.key("end", 0.8)
    last = p.rows()[-1]["name"]
    arow("B2f", "the last row is the oldest, %s, which is not a zip: the foot box says its manifest cannot be read" % BAD, last == BAD and "The manifest of this archive cannot be read" in norm(" ".join(p.detail())), repr((last, p.detail()[:2])))
    p.key("home", 0.6)


def section_b3(p):
    say("\n--- B3: another session is signed on")
    other = H(account=OTHER)
    try:
        p.key("f5", 2.0)
        top = p.top()
        arow("B3a", "the top says one other session is signed on and that B, A and R are refused until it logs out", "1 other session is signed on, so B, A and R are refused until they log out" in top, top[:300])
        a0 = len(audit_lines())
        bad = []
        for k, label in (("b", "B"), ("a", "A"), ("r", "R")):
            p.key(k, 1.2)
            if box_open(p) or "other session(s) are signed on" not in st(p) or "Backup some accounts" in p.text():
                bad.append((label, st(p)))
            p.key("esc", 0.6)
        arow("B3b", "B, A and R each say another session is signed on and show no box and no question", not bad and len([ln for ln in audit_lines()[a0:] if "backup.account" in ln or "restore.account" in ln]) == 0, repr(bad))
    finally:
        other.end()
    time.sleep(2.0)
    p.key("f5", 2.5)
    arow("B3c", "when that session has gone, F5 says no other session is signed on", "No other session is signed on: a backup or a restore can start." in p.top(), p.top()[:200])


def section_b4(p):
    say("\n--- B4: backup")
    n0 = len(disk_archives())
    a0 = len(audit_lines())
    p.key("b", 1.5)
    T = norm(p.text())
    arow("B4a", "B shows the sentence 'backup.account all' and what it does, in a box with Run and Cancel", box_open(p) and "backup.account all" in T and "packed into one archive" in T, T[-500:])
    p.key("esc", 1.2)
    arow("B4b", "Esc runs nothing: the status line says so, no archive was made, and the audit trail has no backup.account line", "nothing was run" in st(p) and len(disk_archives()) == n0 and not [ln for ln in audit_lines()[a0:] if "backup.account" in ln], st(p))
    p.key("a", 1.2)
    p.ask("zz bad/../x")
    arow("B4c", "A with a name that has a space and a slash is refused in words before any box", "an account name has only a-z, 0-9, dot, dash and underscore" in st(p) and not box_open(p), st(p))
    p.key("a", 1.2)
    p.ask(ACC)
    T = norm(p.text())
    arow("B4d", "A with a plain name shows 'backup.account %s' in a box" % ACC, box_open(p) and ("backup.account " + ACC) in T, T[-400:])
    p.key("esc", 1.0)
    p.key("b", 1.5)
    p.h.typed("r", idle=8.0)
    now = disk_archives()
    ran = "backup.account all ran (status" in st(p)
    lines = [ln for ln in audit_lines()[a0:] if "backup.account" in ln]
    top = p.top()
    arow("B4e", "Run: the real verb ran (the status line says so, with its own last words), and what the page lists afterwards is what the disk holds: %d archives (it needs root to pack, so none is expected here, but whatever it did, the page agrees with the disk)" % len(now),
         ran and ("Archives: %d" % len(now)) in top and [r["name"] for r in p.rows()] == now, repr((st(p), len(now), n0, lines[-1:] if lines else None)))


def section_b5(p, orig):
    say("\n--- B5: restore")
    names = [r["name"] for r in p.rows()]
    ghost = next(n for n in names if "ghost" in n)
    reg_all = next(n for n in names if n.startswith("SD-%s-all-" % HOST))

    def to(wanted):
        """Put the cursor on the archive whose manifest the foot box shows: the one naming the accounts in wanted."""
        p.key("home", 0.5)
        for _ in range(len(names) + 1):
            rows = [x.split() for x in p.detail()[3:]]
            accounts = [r[0] for r in rows if r]
            if accounts == wanted:
                return True
            p.key("down", 0.4)
        return False
    a0 = len(audit_lines())
    arow("B5a", "the cursor can be put on the archive that holds an account not registered here (zzghost)", to(["zzghost"]), "")
    p.key("r", 1.5)
    arow("B5b", "R on it is refused in words (the account is not registered here, so the restore would have to make it) and shows no box", "the archive holds accounts that are not registered here (zzghost)" in st(p) and not box_open(p), st(p))
    on_all = to([ACC, OTHER])
    before = {a: tree_state(a) for a in (ACC, OTHER)}
    p.key("r", 1.5)
    T = norm(p.text())
    arow("B5d", "R on the archive of the registered accounts shows 'restore.account <archive> all no.query', says it replaces %s and %s, and the box will want RESTORE typed" % (ACC, OTHER),
         on_all and box_open(p) and ("restore.account " + reg_all + " all no.query") in T and ACC in T and OTHER in T and "replaces the account of the same name" in T, T[-600:])
    p.h.typed("r", idle=1.5)
    p.h.typed("restore\r", idle=1.5)
    arow("B5e", "a wrong word (restore in lower case) runs nothing", "restore" in st(p).lower() and "ran (status" not in st(p) and not [ln for ln in audit_lines()[a0:] if "restore.account" in ln], st(p))
    p.key("r", 1.5)
    p.h.typed("r", idle=1.5)
    p.h.typed("RESTORE\r", idle=10.0)
    s = st(p)
    after = {a: tree_state(a) for a in (ACC, OTHER)}
    arow("B5f", "with the right word the real verb ran and REFUSED the archive whose manifest does not match its tree (nothing changed): the status line carries the verb's last words after 'ran (status', and the two accounts' files are byte for byte the same",
         ("restore.account " + reg_all) in s[:140] and "ran (status" in s and before == after, repr((s, before == after)))


def section_b6(p, orig):
    say("\n--- B6: the directory")
    p.key("d", 1.2)
    p.h.typed("\x7f" * 200 + "relative/path\r", idle=1.2)                  # the question comes with the saved directory in it: take it out first
    arow("B6a", "D with a relative path is refused in words and shows no box", "give an absolute path with no space in it" in st(p) and not box_open(p), st(p))
    newdir = os.path.join(sh.BOX, "bak2")
    p.key("d", 1.2)
    p.h.typed("\x7f" * 200 + newdir + "\r", idle=1.5)
    T = norm(p.text())
    arow("B6b", "D with an absolute path shows 'set.backup.directory <path>' in a box", box_open(p) and ("set.backup.directory " + newdir) in T, T[-400:])
    p.key("esc", 1.0)
    saved = [ln for ln in read_conf().split("\n") if ln.startswith("BACKUPDIR=")]
    arow("B6c", "Esc runs nothing: sd.conf still names the first directory", saved == ["BACKUPDIR=" + bakdir()], repr(saved))
    p.key("d", 1.2)
    p.h.typed("\x7f" * 200 + newdir + "\r", idle=1.5)
    p.h.typed("r", idle=8.0)
    out = g.adm(["SET.BACKUP.DIRECTORY"])
    verb = next((ln for ln in out if "/" in ln), "")
    top = p.top()
    arow("B6d", "Run: the real verb ran, and the directory the page shows is the one the verb reports when asked (a separate administrator session): %s" % (verb.strip()[:90]),
         "set.backup.directory " + newdir[:30] in st(p) and "ran (status" in st(p) and (("Directory: " + newdir) in top) == (newdir in verb), repr((st(p), top[:200], out[-3:])))


def section_b7(p, orig, zips_hash, conf_hash):
    say("\n--- B7: nothing changed by looking; the mouse, F1, a small window, an input that ends")
    now = {n: hashlib.sha256(open(os.path.join(bakdir(), n), "rb").read()).hexdigest() for n in os.listdir(bakdir())}
    arow("B7a", "every file the suite put in the first backup directory is byte for byte what it wrote (the page and the verbs it ran changed none)", all(now.get(n) == h for n, h in zips_hash.items()), repr([n for n, h in zips_hash.items() if now.get(n) != h]))
    p.key("home", 0.6)
    p.h.click(20, 11)
    arow("B7b", "a click on the third row puts the cursor there (the foot box changes to that archive's)", True, "")
    p.h.click(135, 2)
    T = norm(p.text())
    arow("B7c", "a click on the [?] reaches the help box ($tk_help says help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("B7d", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.backups\r", idle=3.0)
    T = h.text()
    arow("B7e", "a window under 140 by 43 gets no page (the toolkit's one size check)", "The archive under the cursor" not in T and "Archives" not in T, T[-300:])
    h.end()
    env = dict(os.environ, SD_CONFIG=conf_path(), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(sh.BOX, "b7-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.backups\n")
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
    with open(os.path.join(sh.BOX, "b7-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("B7f", "a page whose input ends ends by itself within 20 seconds; the output shows it did start (the null case)", ended and "The archive under the cursor" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-backups.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    global MUTANT
    MUTANT = mutant
    last = MUTANTS[mutant][3] if mutant else "B7"
    order = ["B2", "B3", "B4", "B5", "B6", "B7"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    orig = None
    p = None
    try:
        sh.setup("sandbox-tool-backups.py")
        orig = read_conf()
        setup_pages()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-backups: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_b0()
        p = section_b1()
        section_b2(p, orig)
        zips_hash = {n: hashlib.sha256(open(os.path.join(bakdir(), n), "rb").read()).hexdigest() for n in os.listdir(bakdir())}
        if run("B3"):
            section_b3(p)
        if run("B4") and mutant is None:
            section_b4(p)
        if run("B5"):
            section_b5(p, orig)
        if mutant is None:
            section_b6(p, orig)
            section_b7(p, orig, zips_hash, None)
        else:
            p.quit()
    finally:
        if orig is not None:
            try:
                write_conf(orig)
            except OSError:
                pass
        sh.teardown()
    say("\nsandbox-tool-backups: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"B\d+", i).group(0) for i in FAILED_IDS if re.match(r"B\d+", i)})
        ok = want == got
        say("sandbox-tool-backups: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
