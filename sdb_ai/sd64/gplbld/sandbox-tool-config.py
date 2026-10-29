#!/usr/bin/env python3
#
# sandbox-tool-config.py - the configuration page, TOOL.CONFIG, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A6: the view half and, since 26 Oct 26, the write half; plan
# .claude/plan-fullscreen-toolkit.md section 5).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-config.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# THE WRITE HALF (rows C8 to C13) AND WHAT A SANDBOX CANNOT SHOW.  set.config asks the root helper (sd-elevate conf-set) through sudo.  A sandbox is not root and has no sudo grant, so
# the sandbox's own copy of accos.h points the helper at a SHIM of this suite: it runs the REAL sd-elevate with --dry-run first (every check of the name and the value is the real one) and
# then the REAL conf_set function, cut out of the real sd-elevate, on the sandbox's own sd.conf.  So these rows hold the page, the verb, the real checks and the real rewrite.  ***THEY DO NOT
# HOLD*** that /etc/sd.conf is changed by root (its owner, its mode, the rename in /etc), the sudoers line, need_root, the SUDO_USER check, or the .bak next to /etc/sd.conf: the VM witness's
# rows.  Every outcome is read from the disk (sd.conf, sd.conf.bak, the audit file, the shim's call log) or from a separate administrator session (CONFIG()), never from what the page said.
#
# WHAT RUNS.  The administrator's session opens TOOL.CONFIG on a 140 by 43 terminal.  The sandbox's own sd.conf (SD_CONFIG) is edited by this suite, and put back at the end whatever happens.
#
# THE INSTRUMENT.  The page is judged against SD, not against itself.  WHAT SD IS RUNNING WITH is what a probe program, run by a separate administrator session BEFORE the file is edited,
# prints for CONFIG(key) of every parameter of the table; WHAT A NEW SESSION WILL USE is the same probe run after the edit (a session reads sd.conf itself when it starts: the page's claim
# for a `session` parameter), and what a parameter that sizes the system keeps is what the probe still says (the page's claim for `restart`); WHAT THE FILE SAYS is a Python reader of
# sd.conf written from the documented rules (only the [sd] section, a bits parameter added up, the last of the others).  For every parameter the page's three columns and its * mark are
# compared with those, and the claim that a name SD does not know stops a new session is tried on a real new session.
#
#   C0   an ordinary account has no tool.config; a VOC entry that points at the program gets the page's own refusal
#   C1   the page opens: one audit line; every parameter of the table has a row (alphabetical); for each the running value, the file's value, the default, when it takes effect and the
#        status are the probe's, the Python reader's and the table's; no row is marked *
#   C2   the file is edited under the page (a restart parameter and a session parameter): F5 marks exactly those two, counts them, and says who sees the file's value; a NEW session
#        really sees the session parameter's new value and still runs with the old restart one; D and S filter
#   C3   a flag parameter written three times is added up and a plain one keeps the last, and a new session agrees
#   C4   a name SD does not know: the page lists it, says SD will not start, and a real new session is refused with SD's own words (the file is put right at once)
#   C5   B shows the backup directory (none, one that is there, one that is not); R shows the operating system report without the [sd.conf] section and scrolls
#   C6   the page changed nothing: sd.conf is byte for byte what the suite wrote, and the audit trail holds the page's one start line and no other line of its own
#   C7   the mouse, F1, a small window, an input that ends
#   C8   the Change column (e or by hand) is the table's for every row, and the foot box says E changes it here with the range, or why it is not changed here
#   C9   E on a parameter that is not changed here (a door, the system directory, the throttle, a name SD does not know) shows the reason and the line to add by hand and writes nothing: the file,
#        the helper's call log and the audit trail are as they were
#   C10  E on a writable parameter: the value is checked on the page (nothing typed, Esc, letters, a leading zero, below the minimum, above the maximum, too many digits) and none of them
#        reaches a box, the helper, the file or the audit trail
#   C11  the flow: the box shows the exact command and when it takes effect; Esc runs nothing; Run on a restart parameter (CLEANUP: the line is added inside [sd], the .bak is the file as it was,
#        the helper got exactly conf-set CLEANUP 600, one audit line, the page shows the file's new value and that SD keeps running with the old one) and on a session parameter (GRPSIZE: the line
#        is replaced where it was, a NEW session really sees 6, this one keeps 4); the same value again changes nothing and leaves the .bak alone
#   C12  the real verb: the helper's own refusals (a door, an unknown name, out of range) reach the person in the helper's words and write a refused audit line; a wrong number of words, a bad
#        character in the name or the value never reach the helper; an ordinary account has no verb and one given a VOC entry is refused as not the administrator
#   C13  every line of sd.conf the suite did not ask to change is as it was, and the audit lines of the verb are lower case with key, value and status and nothing else
# NOT HELD: a real install's /etc/sd.conf (owner root, mode 644) and root's write of it (see above), the help text itself (sandbox-docs.py).
import getpass
import hashlib
import importlib.util
import os
import re
import shutil
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


sh = _load("sandbox_home_for_toolconfig", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = getpass.getuser()
FAILED_IDS = []
MUTANT = None
AUDIT_START = 0                       # the number of lines the audit file had when this run began (a rerun on the same sandbox must not count an earlier run's)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ACC = "zzhd"
WRITER = """   open 'voc' to v else
      crt 'ZZCW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$tool_config' to v, 'ztcfg' on error
      crt 'ZZCW refused ':status()
      stop
   end
   crt 'ZZCW written'
end
"""

WRITER2 = """   open 'voc' to v else
      crt 'ZZSW no voc'
      stop
   end
   write 'V':@fm:'CA':@fm:'$setconfig' to v, 'ztset' on error
      crt 'ZZSW refused ':status()
      stop
   end
   crt 'ZZSW written'
end
"""

# the stand-in for `sudo /usr/local/sbin/sd-elevate` in the sandbox's copy of accos.h.  The REAL sd-elevate runs first as a --dry-run (so every refusal is the real one), then, for conf-set,
# the REAL conf_set function cut out of the real sd-elevate, on the sandbox's own sd.conf.  It is not root, and it does not pretend the root-only steps (need_root, the caller check).
SHIM = r'''#!/bin/bash
REAL=%(real)s
CONF=%(conf)s
LOG=%(log)s
printf '%%s\n' "$*" >> "$LOG"
if ! out=$(bash "$REAL" --dry-run "$@" 2>&1); then printf '%%s\n' "$out"; exit 2; fi
[ "${1:-}" = conf-set ] || { echo "sd-elevate (sandbox): checked, pretended: $*"; exit 0; }
set -uo pipefail
eval "$(sed -n '/^# BEGIN confset_functions/,/^# END confset_functions/p' "$REAL")"
die() { printf 'sd-elevate: REFUSED - %%s\n' "$1" >&2; exit 2; }
confset_check "$2" "$3"
conf_set "$CONF" "$2" "$3" || exit 3
note=''
[ "$CS_CHANGED" = 1 ] || note=' (it already was; nothing was written)'
printf 'sd-elevate: %%s is now %%s in %%s%%s; takes effect: %%s\n' "$2" "$3" "$CONF" "$note" "$CS_EFFECT"
'''

MUTANTS = {
    # name: (old text of the sandbox's tool_config, new text, the row ids that must fail and no others, the last section run)
    "bits-not-added": ("      fv<p> = bitor(old.v + 0, cval + 0)\n", "      fv<p> = cval\n", ["C3"], "C3"),
    "diff-ignored": ("   cmp.diff = (a # b)\n", "   cmp.diff = 0\n   a = b\n", ["C2"], "C2"),
    "unknown-not-listed": ("         unknown<-1> = fk<j>\n", "", ["C4"], "C4"),
    # the write half: these two run only the write sections (C8 to C13), and stop at the section named
    "fixed-edited": ("   if pwrite<i> = 'yes' then\n      gosub change.param", "   if pwrite<i> # 'zz' then\n      gosub change.param", ["C9a", "C9b", "C9c"], "C9"),
    "box-skipped": ("   call $tk_confirm(sent, el, typed, res, cmsg)\n   if res # 'run' then", "   res = 'run' ; cmsg = ''\n   if res # 'run' then", ["C11a", "C11b"], "C11"),
}
WRITE_MUTANTS = ("fixed-edited", "box-skipped")

# ------------------------------------------------------------------------------------------------------------------------------- the table and the file, read by Python


def table():
    rows = []
    for ln in open(os.path.join(TREE, "sdsys", "config.table"), encoding="latin-1").read().split("\n"):
        if ln.strip() == "" or ln.startswith("#"):
            continue
        f = ln.split("|")
        rows.append({"key": f[0], "kind": f[1], "default": f[2], "min": f[3], "max": f[4], "effect": f[5], "status": f[6], "text": f[7], "write": f[8], "why": f[9]})
    return rows


def conf_path():
    return os.path.join(sh.BOX, "sd.conf")


def shows_path(top):
    """The top line shows the file whole, or - when the path is too long for the line, as under regress.sh's long scratch
    directory - as '...' and the end of it.  Anything else (another file, a cut that is not the end) is not a pass."""
    m = re.search(r"File: (\S+)", top)
    if not m:
        return False
    shown, path = m.group(1), conf_path()
    return shown == path or (shown.startswith("...") and len(shown) > 3 and path.endswith(shown[3:]))


def read_conf():
    return open(conf_path(), encoding="latin-1").read()


def write_conf(text):
    with open(conf_path(), "w", encoding="latin-1") as f:
        f.write(text)


def file_values(text, kinds):
    """What sd.conf says, by the rules of the guide: only the [sd] section, # lines skipped, the key in upper case, split at the first =, a bits parameter written twice added up, the others keep the last."""
    out = {}
    section = ""
    for ln in text.split("\n"):
        if ln == "" or ln.startswith("#"):
            continue
        if ln.startswith("["):
            section = ln[1:ln.find("]")].upper() if "]" in ln else ln[1:].upper()
            continue
        if section != "SD" or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.upper()
        if k in out and kinds.get(k) == "bits" and re.fullmatch(r"-?\d+", out[k]) and re.fullmatch(r"-?\d+", v):
            out[k] = str(int(out[k]) | int(v))
        else:
            out[k] = v
    return out


def probe_program(keys):
    body = ["   keys = '%s'" % ",".join(keys),
            "   for i = 1 to dcount(keys, ',')",
            "      k = field(keys, ',', i)",
            "      v = config(k)",
            "      crt 'ZZCF ' : k : ' [' : v : '] ' : status()",
            "   next i",
            "end", ""]
    return "\n".join(body)


def run_probe():
    """What a new administrator session says CONFIG() is, for every key of the table: {key: value or None when CONFIG cannot read it}."""
    out = g.adm(["RUN bp zzcf"])
    got = {}
    for ln in out:
        m = re.match(r"^ZZCF (\S+) \[(.*)\] (\d+)$", ln)
        if m:
            got[m.group(1)] = (m.group(2) if m.group(3) == "0" else None)
    return got


def differs(file_v, force_v, key):
    if file_v is None or force_v is None or key == "DEBUG":
        return False
    a, b = file_v.strip(), force_v.strip()
    if a == b:
        return False
    try:
        return abs(float(a) - float(b)) > 1e-15
    except ValueError:
        return True


# ------------------------------------------------------------------------------------------------------------------------------- the page

def arow(rid, name, ok, detail=""):
    """A row with an id (C3 ...): the mutant mode compares the ids that failed with the ids that had to."""
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def sq(t):
    """26 Oct 26: the text with every blank and box border taken out.  A box wraps at its width and cuts a word longer than that (a sandbox directory under /tmp/sdregress.<run>/ is longer than
    the short /tmp/sx0 it was written with), so a path inside a box is compared this way: the characters and their order, not where the lines broke."""
    return re.sub(r"[|\s]+", "", t)


def box_text(p):
    """26 Oct 26: the text of the dialog box on the screen and nothing else.  norm(p.text()) reads the screen row by row across its whole width, so the parameter names of the list to the left of
    the box land INSIDE a sentence the box wraps onto a second row (a sandbox directory under /tmp/sdregress.<run>/ is long enough for the path to wrap; /tmp/sx0 was not).  The box is found from
    the row with its buttons ( [ Close ] or [ Run ] ): on the confirm box that row is the bottom border (+-- [ Run ] [ Cancel ] --+), on the information box it is a row between two side borders
    (|  [ Close ]  |).  The border characters either side of the buttons give the columns; every row above it up to the top border is cut to those columns.  '' when there is no box."""
    L = p.h.lines()
    for r in range(len(L) - 1, -1, -1):
        ln = L[r]
        b = max(ln.find("[ Close ]"), ln.find("[ Run ]"))
        if b < 0:
            continue
        e = ln.find("]", b)
        c0 = max(ln.rfind("+", 0, b), ln.rfind("|", 0, b))
        ends = [x for x in (ln.find("+", e), ln.find("|", e)) if x >= 0]
        if c0 < 0 or not ends:
            continue
        c1 = min(ends)
        rows = [ln[c0 + 1:c1]]
        for q in range(r - 1, -1, -1):
            if len(L[q]) <= c1 or L[q][c0] not in "|+":
                break
            rows.insert(0, L[q][c0 + 1:c1])
            if L[q][c0] == "+":
                break
        return norm(" ".join(rows))
    return ""


def st(h):
    return h.line(40)


def audit_lines():
    try:
        return [ln for ln in open(os.path.join(sh.SYS, "audit"), "rb").read().decode("latin-1").split("\n") if ln != ""]
    except OSError:
        return []


def helper_log():
    return os.path.join(sh.BOX, "elevate-calls.log")


def helper_calls():
    """What the shim was asked, one line per call: the helper's own arguments (conf-set CLEANUP 600)."""
    try:
        return [ln for ln in open(helper_log(), encoding="latin-1").read().split("\n") if ln != ""]
    except OSError:
        return []


def patch_elevate():
    """The sandbox's own accos.h names the shim instead of `sudo /usr/local/sbin/sd-elevate`; setconfig is compiled after it (the define is read at compile time)."""
    shim = os.path.join(sh.BOX, "elevate-shim")
    with open(helper_log(), "w"):
        pass
    with open(shim, "w") as f:
        f.write(SHIM % {"real": os.path.join(HERE, "sd-elevate"), "conf": conf_path(), "log": helper_log()})
    os.chmod(shim, 0o755)
    ah = os.path.join(sh.SYS, "syscom", "accos.h")
    txt = open(ah, encoding="latin-1").read()
    new = "'bash %s'" % shim
    if new not in txt:
        old = "'sudo /usr/local/sbin/sd-elevate'"
        if txt.count(old) != 1:
            bail("the sandbox's accos.h does not hold the one helper command this suite points at the shim (%d matches)" % txt.count(old))
        g.put(ah, txt.replace(old, new))


def setup_pages():
    patch_elevate()
    for prog in ("tool_config", "setconfig"):
        shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", prog), os.path.join(sh.SYS, "gpl.bp", prog))
        out = g.adm(["BASIC gpl.bp " + prog], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (prog, "\n".join(out[-8:])))
    for n in (11931, 11935):                       # the messages are read from the sandbox's own message files, which a fresh build copies
        if not os.path.exists(os.path.join(sh.SYS, "messages", str(n))):
            bail("the sandbox has no message %d: it was built before this change; build a fresh one with --build" % n)
    shutil.copyfile(os.path.join(TREE, "sdsys", "config.table"), os.path.join(sh.SYS, "config.table"))
    with open(os.path.join(sh.SYS, "audit"), "ab"):                 # a session appends to the audit file and never makes it: without one the page's audit line goes nowhere
        pass
    g.put(os.path.join(sh.SYS, "bp", "zzcf"), probe_program([r["key"] for r in table()]))
    out = g.adm(["BASIC bp zzcf"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the probe did not compile:\n" + "\n".join(out[-8:]))
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzcw"), WRITER)
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzsw"), WRITER2)


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_config")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_config"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    """A session on tool.config on a pseudo-terminal."""

    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.config\r", idle=4.0)

    def text(self):
        return self.h.text()

    def line(self, n):
        return self.h.line(n)

    def key(self, name, idle=0.7):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def top(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(2, 6)))

    def visible(self):
        out = {}
        for y in range(9, 26):
            t = self.line(y)[3:137]
            name = t[2:14].strip()
            if name:
                out[name] = {"mark": t[0:2].strip(), "force": t[14:37].strip(), "file": t[37:60].strip(), "default": t[60:80].strip(), "effect": t[80:93].strip(), "status": t[93:102].strip(),
                             "change": t[102:].strip().rstrip("|").strip()}
        return out

    def collect(self):
        """Every row the list shows, scrolling with Page Down from the top."""
        self.key("home", 0.6)
        seen = dict(self.visible())
        for _ in range(12):
            before = len(seen)
            self.key("pgdn", 0.6)
            seen.update(self.visible())
            if len(seen) == before:
                break
        self.key("home", 0.6)
        return seen

    def detail(self):
        return norm(" ".join(self.line(n)[3:137] for n in range(28, 39)))

    def to_key(self, key):
        self.key("home", 0.5)
        for _ in range(90):
            if self.line(28)[3:3 + len(key) + 1].startswith(key + " "):
                return True
            self.key("down", 0.3)
        return False

    def end(self):
        self.h.end()

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def expected_cols(r, forced, filev, kinds):
    """The three columns the page must show for table row r: (running, file, default)."""
    k = r["key"]
    fv = forced.get(k)
    force = "(not readable)" if fv is None else (fv if fv != "" else "(empty)")
    infile = filev.get(k)
    return force[:22], ("-" if infile is None else infile)[:22], (r["default"] if r["default"] != "" else "(none)")[:19]


def check_rows(seen, rows, forced, filev, kinds):
    """The differential: every table row's columns against the probe, the Python reader and the table; the marks against Python's own comparison.  Returns (ok, detail)."""
    bad = []
    for r in rows:
        k = r["key"]
        if k not in seen:
            bad.append((k, "no row"))
            continue
        want_force, want_file, want_def = expected_cols(r, forced, filev, kinds)
        s = seen[k]
        mark = "*" if differs(filev.get(k), forced.get(k), k) else ""
        got = (s["force"], s["file"], s["default"], s["effect"], s["status"], s["mark"], s["change"])
        want = (want_force, want_file, want_def, r["effect"], r["status"], mark, "e" if r["write"] == "yes" else "by hand")
        if got != want:
            bad.append((k, got, want))
    return not bad and len(seen) >= len(rows), "%d rows seen, %d wanted; first differences %s" % (len(seen), len(rows), bad[:3])


# ------------------------------------------------------------------------------------------------------------------------------- the sections

def section_c0():
    say("\n--- C0: an ordinary account")
    out = g.plain(ACC, ["tool.config"])
    T = norm(" ".join(out))
    arow("C0a", "an ordinary account's session is told it is not a command and no page is drawn (SDSYS's VOC alone has the verb)", "Configuration" not in T and "The parameter under the cursor" not in T and len(out) > 0, T[:300])
    out = g.plain(ACC, ["BASIC bp zzcw", "RUN bp zzcw"])
    wrote = has(out, r"^ZZCW written$")
    out = g.plain(ACC, ["ztcfg"])
    T = norm(" ".join(out))
    arow("C0b", "a VOC entry an ordinary account made for the program gets the page's own refusal (message 11800), not 'not a command', and no page", wrote and "is for the administrator only" in T and "The parameter under the cursor" not in T, repr((wrote, T[:300])))


def section_c1(rows, kinds):
    say("\n--- C1: the page opens")
    a0 = len(audit_lines())
    forced = run_probe()
    arow("C1a", "the probe (CONFIG() of every key of the table, in a separate administrator session) answered for them all, and it can read what the page says it cannot not (the null case: the instrument measured)",
         len(forced) == len(rows) and sorted(k for k, v in forced.items() if v is None) == ["BACKUPDIR", "SDSYS"], repr(sorted(k for k, v in forced.items() if v is None)))
    p = Page()
    if "The parameter under the cursor" not in p.text():
        dump(p.h)
        bail("tool.config never drew its page, so no row below can be believed")
    mine = [ln for ln in audit_lines()[a0:] if " tool " in ln]
    arow("C1b", "opening the page wrote one audit line, 'tool start app=tool.config', and no other 'tool' line", len(mine) == 1 and mine[0].endswith("tool start app=tool.config"), repr(mine))
    filev = file_values(read_conf(), kinds)
    top = p.top()
    arow("C1c", "the top box names the file as SD_CONFIG gives it (a path too long for the line shows as '...' and its end, never at the cost of the counts), how many parameters it sets (%d), and says none differs and no restart is needed" % len(filev),
         shows_path(top) and ("Parameters in it: %d" % len(filev)) in top and "Differ from what SD is running with: 0" in top and "Need a restart: 0" in top and "Names in the file that SD does not know: none" in top, top[:300])
    seen = p.collect()
    ok, detail = check_rows(seen, rows, forced, filev, kinds)
    arow("C1d", "every parameter of the table has a row: the running value, the file's value, the default, when it takes effect and the status are the probe's, the Python reader's and the table's, and no row is marked *", ok and not any(s["mark"] for s in seen.values()), detail)
    arow("C1e", "the rows come in alphabetical order, the first BACKUPDIR and the last YEARBASE", list(seen)[0] == "BACKUPDIR" and list(seen)[-1] == "YEARBASE" and list(seen) == sorted(seen), repr(list(seen)[:3]))
    return p, forced


def section_c2(p, rows, kinds, forced_before):
    say("\n--- C2: the file is edited under the page")
    orig = read_conf()
    write_conf(orig.rstrip("\n") + "\nNUMFILES=90\nGRPSIZE=6\n")
    filev = file_values(read_conf(), kinds)
    p.key("f5", 1.5)
    top = p.top()
    seen = p.collect()
    ok, detail = check_rows(seen, rows, forced_before, filev, kinds)
    marked = sorted(k for k, s in seen.items() if s["mark"])
    arow("C2a", "F5 marks exactly NUMFILES and GRPSIZE with *, counts two differences and one restart, and every column is still the probe's (taken before the edit), the reader's and the table's",
         ok and marked == ["GRPSIZE", "NUMFILES"] and "Differ from what SD is running with: 2" in top and "Need a restart: 1" in top, repr((marked, top[:200], detail)))
    p.to_key("NUMFILES")
    d = p.detail()
    nf0, gs0 = forced_before.get("NUMFILES"), forced_before.get("GRPSIZE")
    arow("C2b", "the box at the foot for NUMFILES says it takes effect only when SD is next started and that SD keeps running with %s" % nf0, "takes effect only when SD is next started" in d and ("keeps running with %s." % nf0) in d, d[:300])
    p.to_key("GRPSIZE")
    d = p.detail()
    arow("C2c", "... and for GRPSIZE that sessions started now read the file and this one keeps %s" % gs0, "Sessions started now read the file" in d and ("keep %s." % gs0) in d, d[:300])
    after = run_probe()
    arow("C2d", "THE CLAIM IS TRUE: a new session really runs with GRPSIZE 6 (a session parameter reaches the sessions started after the edit) and the shared NUMFILES is still %s until SD restarts" % nf0,
         after.get("GRPSIZE") == "6" and after.get("NUMFILES") == nf0 and gs0 not in (None, "6") and nf0 not in (None, "90"), repr((after.get("GRPSIZE"), after.get("NUMFILES"), gs0, nf0)))
    p.key("d", 1.0)
    shown = p.visible()
    arow("C2e", "D shows only the two rows where the file and SD disagree", sorted(shown) == ["GRPSIZE", "NUMFILES"] and "only the rows where the file and SD disagree" in st(p.h), repr((sorted(shown), st(p.h))))
    p.key("d", 1.0)
    p.key("s", 1.0)
    shown = p.collect()
    want = sorted(k for k in file_values(read_conf(), kinds))
    arow("C2f", "S shows only the parameters the file sets (the sandbox's own lines and the two added)", sorted(shown) == want, repr((sorted(shown), want)))
    p.key("s", 1.0)
    return orig


def section_c3(p, rows, kinds, forced_before, orig):
    say("\n--- C3: a flag parameter written more than once")
    write_conf(orig.rstrip("\n") + "\nFSYNC=1\nFSYNC=2\nFSYNC=4\nGRPSIZE=5\nGRPSIZE=7\n")
    filev = file_values(read_conf(), kinds)
    p.key("f5", 1.5)
    seen = p.collect()
    after = run_probe()
    arow("C3a", "FSYNC written 1, 2 and 4 is 7 in the page's file column, GRPSIZE written 5 and 7 is 7 (the last), and a new session agrees with both (so SD adds the flags up and keeps the last of a plain one)",
         seen.get("FSYNC", {}).get("file") == "7" and seen.get("GRPSIZE", {}).get("file") == "7" and after.get("FSYNC") == "7" and after.get("GRPSIZE") == "7", repr((seen.get("FSYNC"), seen.get("GRPSIZE"), after.get("FSYNC"), after.get("GRPSIZE"))))
    ok, detail = check_rows(seen, rows, forced_before, filev, kinds)
    arow("C3b", "every column of every row is still the probe's, the reader's and the table's", ok, detail)
    return orig


def section_c4(p, rows, kinds, forced_before, orig):
    say("\n--- C4: a name SD does not know")
    write_conf(orig.rstrip("\n") + "\nZZBAD=1\n")
    p.key("f5", 1.5)
    top = p.top()
    seen = p.collect()
    p.key("end", 0.8)
    arow("C4a", "the top says SD does not know ZZBAD and will not start with it; the last row is ZZBAD with status unknown and a *, and the box at the foot says SD will not start and no new session will",
         "NAMES IN THE FILE THAT SD DOES NOT KNOW (SD will not start with them): ZZBAD" in top and seen.get("ZZBAD", {}).get("status") == "unknown" and seen.get("ZZBAD", {}).get("mark") == "*" and list(seen)[-1] == "ZZBAD"
         and "will not start, and no new session will, while the file holds it" in p.detail(), repr((top[:240], seen.get("ZZBAD"), p.detail()[:160])))
    out = g.plain(ACC, ["WHO"])
    T = norm(" ".join(out))
    arow("C4b", "THE CLAIM IS TRUE: a real new session is refused while the file holds the name, with SD's own words (the null case: some output, and not a sign-on)", len(out) > 0 and "Unrecognised configuration parameter" in T and "ZZBAD" in T, T[:300])
    write_conf(orig)
    p.key("f5", 1.5)
    arow("C4c", "the file put right and F5: the name is gone from the top and from the list, and a new session starts again",
         "Names in the file that SD does not know: none" in p.top() and "ZZBAD" not in p.collect() and has(g.plain(ACC, ["WHO"]), r"\d"), p.top()[:200])


def section_c5(p, rows, kinds, orig):
    say("\n--- C5: the backup directory and the report")
    p.key("b", 1.2)
    T = norm(p.text())
    arow("C5a", "B with no BACKUPDIR line says no backup directory has been saved", "No backup directory has been saved" in T and "Backup directory" in T, T[-500:])
    there = os.path.join(sh.BOX, "bakdir-there")
    os.makedirs(there, exist_ok=True)
    write_conf(orig.rstrip("\n") + "\nBACKUPDIR=" + there + "\n")
    p.key("f5", 1.5)
    T = norm(p.text())
    arow("C5b", "with BACKUPDIR naming a directory that is there, the page shows the path and says it exists", ("BACKUPDIR in " + conf_path()) in T and there in T and "It exists." in T, T[-500:])
    gone = os.path.join(sh.BOX, "bakdir-gone")
    write_conf(orig.rstrip("\n") + "\nBACKUPDIR=" + gone + "\n")
    p.key("f5", 1.5)
    T = norm(p.text())
    arow("C5c", "with one that is not there, it says so", gone in T and "It does not exist now" in T, T[-500:])
    write_conf(orig)
    p.key("r", 5.0)
    T = p.text()
    lines = [p.line(y)[3:137].rstrip() for y in range(9, 26)]
    arow("C5d", "R shows the operating system part of the report: section headings from [ssh] [api] [groups] [service] [sudoers] and not [sd.conf], the line counts, and a footer",
         any(re.match(r"^\[(ssh|api|groups|service|sudoers)\]", ln) for ln in lines) and not any(ln.startswith("[sd.conf]") for ln in lines) and "Lines 1 to" in norm(T), repr(lines[:4]))
    n = int(re.search(r"of (\d+)\.", norm(T)).group(1)) if re.search(r"of (\d+)\.", norm(T)) else 0
    first = lines[0]
    p.key("down", 0.5)
    p.key("down", 0.5)
    lines2 = [p.line(y)[3:137].rstrip() for y in range(9, 26)]
    arow("C5e", "Down scrolls the report (the first line on the screen is the one that was third, when there are more lines than rows)", n <= 17 or lines2[0] == lines[2], repr((n, first, lines2[:2])))
    p.key("p", 1.2)


def section_c6(p, orig, wrote_hash):
    say("\n--- C6: the page changed nothing")
    arow("C6a", "sd.conf is byte for byte what the suite last wrote: the page never touched it", hashlib.sha256(read_conf().encode("latin-1")).hexdigest() == wrote_hash, "")
    own = [ln for ln in audit_lines()[AUDIT_START:] if " tool " in ln and "app=tool.config" in ln]       # the audit file outlives a run: only this run's lines are judged
    arow("C6b", "the audit trail holds one line of the page's own for each time it was opened, and nothing else (no 'tool run', no 'tool export')", len(own) == 1 and all(ln.endswith("tool start app=tool.config") for ln in own), repr(own[-3:]))


def section_c7(p):
    say("\n--- C7: the mouse, F1, a small window, an input that ends")
    p.key("home", 0.6)
    names = list(p.visible())
    p.h.click(20, 11)
    arow("C7a", "a click on the third row puts the cursor there: the box at the foot names that parameter", p.line(28)[3:3 + len(names[2]) + 1].startswith(names[2] + " "), repr((names[:3], p.line(28)[3:60])))
    p.h.click(135, 2)
    T = norm(p.text())
    arow("C7b", "a click on the [?] reaches the help box ($tk_help says help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.key("f1", 1.2)
    T = norm(p.text())
    arow("C7c", "F1 reaches it too", "Help is not installed here" in T, T[-300:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.config\r", idle=3.0)
    T = h.text()
    arow("C7d", "a window under 140 by 43 gets no page (the toolkit's one size check)", "The parameter under the cursor" not in T and "Configuration" not in T, T[-300:])
    h.end()
    env = dict(os.environ, SD_CONFIG=conf_path(), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    fh = open(os.path.join(sh.BOX, "c7-eof.out"), "w")
    t0 = time.time()
    pr = subprocess.Popen([os.path.join(sh.SYS, "bin", "sd")], stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env, text=True)
    pr.stdin.write("\nTERM 200,60\ntool.config\n")
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
    with open(os.path.join(sh.BOX, "c7-eof.out"), errors="replace") as f:
        drawn = ANSI.sub("", f.read())
    arow("C7e", "a page whose input ends ends by itself within 20 seconds; the output shows it did start (the null case)", ended and "The parameter under the cursor" in drawn, "took %.1f s, drawn: %r" % (time.time() - t0, drawn[-200:]))


# ------------------------------------------------------------------------------------------------------------------------------- the write half (C8 to C13)

def sha():
    return hashlib.sha256(read_conf().encode("latin-1")).hexdigest()


def bak_path():
    return conf_path() + ".bak"


def read_bak():
    """The .bak's text, None when there is none (a row must go red then, not stop the suite)."""
    try:
        return open(bak_path(), encoding="latin-1").read()
    except OSError:
        return None


def verb_audit(a0):
    """The audit lines set.config wrote since the file had a0 lines."""
    return [ln for ln in audit_lines()[a0:] if " set.config " in ln or ln.endswith("set.config")]


def box_open(p):
    T = norm(p.text())
    return "Cancel" in T and "Run" in T and "this will run" in T


def ask_open(p):
    return "New value for" in norm(p.text())


def goto(p, names, key):
    """The cursor on the row of KEY: Home, then Page Down (17 rows) and Down by arithmetic on the order of the rows; True when the foot box names it."""
    idx = names.index(key)
    p.key("home", 0.5)
    for _ in range(idx // 17):
        p.key("pgdn", 0.5)
    for _ in range(idx % 17):
        p.key("down", 0.3)
    return p.line(28)[3:3 + len(key) + 1].startswith(key + " ")


def add_after_last_setting(text, line):
    """Where conf_set puts a line the file lacks: after the last line of the [sd] section that sets something (the sandbox's file has the one section)."""
    ls = text.split("\n")
    last = max(i for i, l in enumerate(ls) if l != "" and not l.startswith("#") and not l.startswith("["))
    return "\n".join(ls[:last + 1] + [line] + ls[last + 1:])


def fresh(orig):
    """Every write section begins from the file as the suite found it, no .bak and an empty call log."""
    write_conf(orig)
    if os.path.exists(bak_path()):
        os.remove(bak_path())
    with open(helper_log(), "w"):
        pass


def section_c8(p, by, names):
    say("\n--- C8: which rows the page can change")
    r = by["CLEANUP"]
    ok = goto(p, names, "CLEANUP")
    d = p.detail()
    arow("C8a", "CLEANUP (writable): the foot box gives its own range (range %s to %s, which the table's first rows must not have slid onto), says E changes it here with that range, and does not say it is not changed from this page" % (r["min"], r["max"]),
         ok and ("range %s to %s" % (r["min"], r["max"])) in d and ("E changes it here: a whole number from %s to %s" % (r["min"], r["max"])) in d and "Not changed from this page" not in d, d[:700])
    ok = goto(p, names, "BACKUPDIR")
    d = p.detail()
    arow("C8c", "BACKUPDIR (the table's first row, no range): the foot box shows no range - the minimum and maximum columns are read by index, so a blank at the top does not move the later ranges up onto it", ok and " range " not in d and "Not changed from this page" in d, d[:300])
    r = by["NETFILES"]
    ok = goto(p, names, "NETFILES")
    d = p.detail()
    arow("C8b", "NETFILES (a door): the foot box says Not changed from this page with the table's reason word for word, and does not offer E", ok and ("Not changed from this page: " + r["why"]) in d and "E changes it here" not in d, d[:300])


def section_c9(p, by, names, orig):
    say("\n--- C9: E on a parameter that is not changed here")
    path = conf_path()
    for key in ("NETFILES", "SDSYS", "PWDELAY"):
        why = by[key]["why"]
        h0, c0, a0 = sha(), len(helper_calls()), len(audit_lines())
        ok = goto(p, names, key)
        p.key("e", 1.5)
        T = box_text(p)
        arow("C9a", "E on %s opens a box that says it is not changed from this page, gives the table's reason word for word, and the line %s=<value> to add to the [sd] section of the file SD reads" % (key, key),
             ok and (key + " is not changed from this page.") in T and why in T and sq(key + "=<value> in the [sd] section of " + path) in sq(T) and "Close" in T and not ask_open(p), T[max(0, T.find(key + " is not changed") - 80):][:1100])      # 26 Oct 26: the detail is the box, not the foot of the page
        p.key("enter", 1.2)
        arow("C9b", "closing it leaves nothing open and says nothing was written; sd.conf, the helper's call log, the .bak and the audit trail are as they were (%s)" % key,
             (key + " is not changed from this page; nothing was written") in st(p) and not box_open(p) and not ask_open(p) and sha() == h0 and helper_calls()[c0:] == [] and not os.path.exists(bak_path()) and not verb_audit(a0),
             st(p).strip()[:100])
    write_conf(orig.rstrip("\n") + "\nZZBAD=1\n")
    p.key("f5", 1.8)
    h0, c0 = sha(), len(helper_calls())
    ok = goto(p, names + ["ZZBAD"], "ZZBAD")
    p.key("e", 1.5)
    T = box_text(p)
    arow("C9c", "E on a name SD does not know says so, that SD will not start while the file holds it, and to take the line out of the file by hand; it offers no line to add",
         ok and "ZZBAD is not changed from this page." in T and "SD does not know this name" in T and sq("Take the line out of " + conf_path() + " by hand") in sq(T) and "ZZBAD=<value>" not in T, T[-600:])
    p.key("enter", 1.2)
    arow("C9d", "and it writes nothing: the file is as the suite wrote it and the helper was not asked", sha() == h0 and helper_calls()[c0:] == [], "")
    write_conf(orig)
    p.key("f5", 1.8)


def section_c10(p, by, names, orig, forced):
    say("\n--- C10: a writable parameter: the value is checked on the page")
    r = by["CLEANUP"]
    h0, c0, a0 = sha(), len(helper_calls()), len(audit_lines())
    ok = goto(p, names, "CLEANUP")
    p.key("e", 1.5)
    T = norm(p.text())
    arow("C10a", "E on CLEANUP asks for the new value: the question gives the range %s to %s and says what SD runs with (%s) and that sd.conf says nothing" % (r["min"], r["max"], forced.get("CLEANUP")),
         ok and ask_open(p) and ("a whole number from %s to %s" % (r["min"], r["max"])) in T and ("SD runs with %s" % forced.get("CLEANUP")) in T and "sd.conf says (nothing)" in T, T[-500:])
    p.key("esc", 1.2)
    arow("C10b", "Esc in the question cancels it: the status line says CLEANUP is unchanged and no question or box is left", "cancelled; CLEANUP is unchanged" in st(p) and not ask_open(p) and not box_open(p), st(p).strip()[:100])
    range_msg = "CLEANUP takes a whole number from %s to %s, digits only; nothing was changed" % (r["min"], r["max"])
    empty_msg = "nothing was typed; CLEANUP is unchanged"
    bad = []
    for label, typed, want in (("nothing", "", empty_msg), ("spaces only", "   ", empty_msg), ("letters", "abc", range_msg), ("digits and a letter", "60x", range_msg), ("a leading zero", "0600", range_msg),
                               ("below the minimum", "29", range_msg), ("above the maximum", "3601", range_msg), ("eight digits", "12345678", range_msg), ("a minus sign", "-60", range_msg),
                               ("a decimal point", "60.5", range_msg)):
        p.key("e", 1.2)
        p.h.typed(typed + "\r", idle=1.3)
        s, bx, ak = st(p), box_open(p), ask_open(p)
        if want not in s or bx or ak:
            bad.append((label, s.strip()[:100], "box" if bx else "", "ask" if ak else ""))
        if bx or ak:
            p.key("esc", 1.0)
    arow("C10c", "each of nothing, spaces, letters, digits and a letter, a leading zero, 29, 3601, eight digits, a minus sign and a decimal point is refused on the page in words (the range, or 'nothing was typed') and none reaches a box", not bad, repr(bad[:3]))
    arow("C10d", "none of them reached the helper: its call log is as it was, and so are sd.conf, the .bak and the audit trail", helper_calls()[c0:] == [] and sha() == h0 and not os.path.exists(bak_path()) and not verb_audit(a0),
         repr((helper_calls()[c0:], verb_audit(a0))))


def section_c11(p, by, names, orig, forced, mutant):
    say("\n--- C11: the flow")
    path = conf_path()
    h0, c0, a0 = sha(), len(helper_calls()), len(audit_lines())
    ok = goto(p, names, "CLEANUP")
    p.key("e", 1.3)
    p.h.typed("600\r", idle=1.8)
    T = box_text(p)
    arow("C11a", "typing 600 for CLEANUP shows the box: the exact command 'set.config cleanup 600', that it takes effect when SD is next stopped and started (sd -stop, then sd -start), where the old file is kept, "
         "and that this session reads another file than the one the helper changes",
         ok and box_open(p) and "set.config cleanup 600" in T and "sd -stop, then sd -start" in T and "/etc/sd.conf.bak" in T and sq("This session reads " + path + ", but the root helper changes /etc/sd.conf only.") in sq(T), T[max(0, T.find("this will run") - 150):][:1100])      # 26 Oct 26: the detail is the box, not the foot of the page
    p.key("esc", 1.5)
    arow("C11b", "Esc (Cancel, which is what Enter chooses) runs nothing: sd.conf, the helper's call log, the .bak and the audit trail are as they were, and the status line says nothing was run",
         sha() == h0 and helper_calls()[c0:] == [] and not os.path.exists(bak_path()) and not verb_audit(a0) and "nothing was run" in st(p), repr((st(p).strip()[:60], helper_calls()[c0:])))
    if mutant == "box-skipped":
        return
    # ---- CLEANUP: a restart parameter the file lacks
    p.key("e", 1.3)
    p.h.typed("600\r", idle=1.8)
    p.h.typed("r", idle=5.0)
    s_run = st(p).strip()                          # the status line is cleared by the next key: read it now
    after = read_conf()
    arow("C11c", "Run (CLEANUP 600): the file is the original with CLEANUP=600 added inside [sd] after its last setting and nothing else changed", after == add_after_last_setting(orig, "CLEANUP=600"), repr(after[-160:]))
    bak = read_bak()
    arow("C11d", "the file as it was is kept as sd.conf.bak, byte for byte, with the mode the file has", bak == orig and os.path.exists(bak_path()) and os.stat(bak_path()).st_mode == os.stat(conf_path()).st_mode, repr(bak)[:120])
    calls = helper_calls()[c0:]
    mine = verb_audit(a0)
    arow("C11e", "the helper was asked exactly once, with the name in capitals and the digits as typed: 'conf-set CLEANUP 600'; and exactly ONE audit line was written, 'set.config key=cleanup value=600 status=ok'",
         calls == ["conf-set CLEANUP 600"] and len(mine) == 1 and mine[0].endswith("set.config key=cleanup value=600 status=ok"), repr((calls, mine)))
    goto(p, names, "CLEANUP")
    row_ = p.visible().get("CLEANUP", {})
    top = p.top()
    run_c = forced.get("CLEANUP")
    arow("C11f", "the page read the file and SD again: the status line says CLEANUP in sd.conf went from (nothing) to 600 and SD runs with %s until it is restarted; the row shows 600 in the file, %s running and a *; "
         "the top counts one difference that needs a restart" % (run_c, run_c),
         ("CLEANUP in sd.conf: (nothing) -> 600; SD is running with %s until it is restarted" % run_c) in s_run and row_.get("file") == "600" and row_.get("force") == run_c and row_.get("mark") == "*"
         and "Differ from what SD is running with: 1" in top and "Need a restart: 1" in top, repr((s_run[:120], row_, top[:200])))
    now = run_probe()
    arow("C11g", "THE CLAIM IS TRUE: a new session still runs with CLEANUP %s, because CLEANUP sizes the system (the restart words are not decoration)" % run_c, now.get("CLEANUP") == run_c and run_c not in (None, "600"), repr(now.get("CLEANUP")))
    # ---- GRPSIZE: a session parameter the file has
    before = read_conf()
    if "GRPSIZE=4\n" not in before:
        bail("the sandbox's sd.conf has no GRPSIZE=4 line, so the replace-in-place rows cannot be run")
    bak0 = read_bak()
    c1, a1 = len(helper_calls()), len(audit_lines())
    goto(p, names, "GRPSIZE")
    p.key("e", 1.3)
    p.h.typed("6\r", idle=1.8)
    T = norm(p.text())
    box_ok = box_open(p) and "set.config grpsize 6" in T and "Sessions started after this read the new value" in T
    p.h.typed("r", idle=5.0)
    s_run2 = st(p).strip()
    after2 = read_conf()
    arow("C11h", "GRPSIZE 6: the box says sessions started after this read the new value; after Run the GRPSIZE line is replaced WHERE IT WAS (same place, one line) and every other line is as before",
         box_ok and after2 == before.replace("GRPSIZE=4\n", "GRPSIZE=6\n", 1) and after2 != before, repr((box_ok, after2[-200:])))
    bak2 = read_bak()
    arow("C11i", "the .bak is now the file as it was before THIS change (it holds CLEANUP=600 and GRPSIZE=4): one generation, not an archive", bak2 == before and bak2 != bak0, repr(bak2)[:120])
    goto(p, names, "GRPSIZE")
    run_g = forced.get("GRPSIZE")
    now = run_probe()
    arow("C11j", "THE CLAIM IS TRUE: a NEW session runs with GRPSIZE 6; this page's own session still runs with %s, and the status line says so" % run_g,
         now.get("GRPSIZE") == "6" and run_g == "4" and p.visible().get("GRPSIZE", {}).get("force") == "4"
         and ("GRPSIZE in sd.conf: 4 -> 6; SD is running with 4 (sessions started now use 6)") in s_run2, repr((now.get("GRPSIZE"), run_g, s_run2[:120])))
    calls = helper_calls()[c1:]
    mine = verb_audit(a1)
    arow("C11k", "that was one call to the helper ('conf-set GRPSIZE 6') and one audit line ('set.config key=grpsize value=6 status=ok')", calls == ["conf-set GRPSIZE 6"] and len(mine) == 1 and mine[0].endswith("set.config key=grpsize value=6 status=ok"), repr((calls, mine)))
    # ---- the same value again
    h3, bak3, c2, a2 = sha(), read_bak(), len(helper_calls()), len(audit_lines())
    goto(p, names, "GRPSIZE")
    p.key("e", 1.3)
    p.h.typed("6\r", idle=1.8)
    p.h.typed("r", idle=4.0)
    calls = helper_calls()[c2:]
    arow("C11l", "the same value again: the helper is asked and finds nothing to change, so sd.conf and sd.conf.bak are byte for byte as before (the .bak is not overwritten by an identical file), "
         "and one more audit line says ok", sha() == h3 and bak3 is not None and read_bak() == bak3 and calls == ["conf-set GRPSIZE 6"] and len(verb_audit(a2)) == 1, repr((calls, verb_audit(a2))))


def section_c12(orig):
    say("\n--- C12: the real verb")
    h0, c0, a0 = sha(), len(helper_calls()), len(audit_lines())
    cases = [("a door", "set.config netfiles 1", "SD knows, and conf-set does not change it", "conf-set NETFILES 1", "netfiles", "1"),
             ("the security throttle", "set.config pwdelay 0", "SD knows, and conf-set does not change it", "conf-set PWDELAY 0", "pwdelay", "0"),
             ("a name SD does not know", "set.config zznew 1", "is not a parameter SD knows", "conf-set ZZNEW 1", "zznew", "1"),
             ("below the minimum", "set.config cleanup 29", "outside the range 30 to 3600", "conf-set CLEANUP 29", "cleanup", "29"),
             ("above the maximum", "set.config grpsize 9", "outside the range 1 to 8", "conf-set GRPSIZE 9", "grpsize", "9")]
    bad = []
    for label, cmd, frag, call, key, val in cases:
        out = norm(" ".join(g.adm([cmd])))
        if "sd.conf was not changed:" not in out or frag not in out or " is now " in out:
            bad.append((label, out[:200]))
    arow("C12a", "the helper's own refusals reach the person after 'sd.conf was not changed:' (a door, the throttle, an unknown name, below the minimum, above the maximum)", not bad, repr(bad[:2]))
    calls = helper_calls()[c0:]
    mine = verb_audit(a0)
    arow("C12b", "each reached the helper once (the call log holds the five, the name in capitals), each wrote ONE refused audit line, and sd.conf is as it was",
         calls == [c[3] for c in cases] and len(mine) == 5 and all(m.endswith("status=refused") for m in mine) and [m.split("set.config ", 1)[1] for m in mine] == ["key=%s value=%s status=refused" % (c[4], c[5]) for c in cases] and sha() == h0,
         repr((calls, mine[-2:])))
    c1, a1 = len(helper_calls()), len(audit_lines())
    usage, c_name, c_val = "set.config parameter value", "The parameter name has only letters and digits", "The value is a whole number written with digits only"
    cases2 = [("no words", "set.config", usage), ("one word", "set.config cleanup", usage), ("three words", "set.config cleanup 600 7", usage), ("a dash in the name", "set.config clean-up 5", c_name),
              ("a name of 14 letters", "set.config cleanupcleanup 5", c_name), ("a letter in the value", "set.config cleanup 6x", c_val), ("a decimal point in the value", "set.config cleanup 6.5", c_val),
              ("a value of eight digits", "set.config cleanup 12345678", c_val)]
    bad = []
    for label, cmd, frag in cases2:
        out = norm(" ".join(g.adm([cmd])))
        if frag not in out or "sd.conf was not changed" in out:
            bad.append((label, out[:160]))
    arow("C12c", "a wrong number of words, a dash or 14 letters in the name, a letter or a point or eight digits in the value are answered by the verb itself (the usage line, or which of the two words is wrong)", not bad, repr(bad[:2]))
    arow("C12d", "and none of them reached the helper or the audit trail: no call, no audit line, sd.conf unchanged", helper_calls()[c1:] == [] and not verb_audit(a1) and sha() == h0, repr((helper_calls()[c1:], verb_audit(a1))))
    c2, a2 = len(helper_calls()), len(audit_lines())
    out = norm(" ".join(g.plain(ACC, ["set.config cleanup 600"])))
    out2 = g.plain(ACC, ["BASIC bp zzsw", "RUN bp zzsw"])
    wrote = has(out2, r"^ZZSW written$")
    out3 = norm(" ".join(g.plain(ACC, ["ztset cleanup 600"])))
    arow("C12e", "an ordinary account has no set.config (the session answers, and nothing was changed), and a VOC entry it made for the program gets message 2001, 'Command requires administrator privileges'",
         out != "" and " is now " not in out and wrote and "Command requires administrator privileges" in out3 and " is now " not in out3, repr((out[:100], wrote, out3[:100])))
    arow("C12f", "and neither reached the helper, the audit trail or the file", helper_calls()[c2:] == [] and not verb_audit(a2) and sha() == h0, repr((helper_calls()[c2:], verb_audit(a2))))


def section_c13(orig, audit_base):
    say("\n--- C13: nothing else changed; the audit words")
    final = read_conf()
    want = add_after_last_setting(orig, "CLEANUP=600").replace("GRPSIZE=4\n", "GRPSIZE=6\n", 1)
    arow("C13a", "every line of sd.conf the suite did not ask to change is as it was, in the same order: the file is the original with GRPSIZE=6 and CLEANUP=600 and nothing else", final == want, repr(final[-200:]))
    lines = [ln.split("set.config ", 1)[1] for ln in verb_audit(audit_base)]
    ok_lines = [x for x in lines if x.endswith("status=ok")]
    ref_lines = [x for x in lines if x.endswith("status=refused")]
    shape = all(re.fullmatch(r"key=[a-z0-9]+ value=[0-9]+ status=(ok|refused)", x) for x in lines)
    arow("C13b", "the audit trail holds 8 lines of the verb (3 ok: CLEANUP, GRPSIZE, GRPSIZE again; 5 refused), each exactly 'key=<name> value=<number> status=ok|refused' in lower case, and the words and the name are lower case", len(lines) == 8 and len(ok_lines) == 3 and len(ref_lines) == 5 and shape
         and all(x == x.lower() for x in lines), repr(lines))


def write_sections(rows, orig, forced, mutant):
    by = {r["key"]: r for r in rows}
    names = [r["key"] for r in rows]
    fresh(orig)
    audit_base = len(audit_lines())                # the audit file outlives a run: only the lines of THIS run are counted
    pw = Page()
    if "The parameter under the cursor" not in pw.text():
        dump(pw.h)
        bail("tool.config never drew its page for the write rows")
    section_c8(pw, by, names)
    section_c9(pw, by, names, orig)
    if mutant == "fixed-edited":
        pw.quit()
        return
    section_c10(pw, by, names, orig, forced)
    section_c11(pw, by, names, orig, forced, mutant)
    if mutant == "box-skipped":
        pw.end()
        return
    pw.quit()
    section_c12(orig)
    section_c13(orig, audit_base)


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-config.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    global MUTANT, AUDIT_START
    MUTANT = mutant
    last = MUTANTS[mutant][3] if mutant else "C7"
    order = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]

    def run(s):
        return mutant is None or order.index(s) <= order.index(last)

    orig = None
    p = None
    try:
        sh.setup("sandbox-tool-config.py")
        orig = read_conf()
        setup_pages()
        AUDIT_START = len(audit_lines())
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-config: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        rows = table()
        kinds = {r["key"]: r["kind"] for r in rows}
        if mutant in WRITE_MUTANTS:
            write_sections(rows, orig, run_probe(), mutant)
        else:
            if mutant is None:
                section_c0()
            p, forced = section_c1(rows, kinds)
            if run("C2"):
                section_c2(p, rows, kinds, forced)
            if run("C3"):
                section_c3(p, rows, kinds, forced, orig)
            if run("C4"):
                section_c4(p, rows, kinds, forced, orig)
            if mutant is None:
                section_c5(p, rows, kinds, orig)
                write_conf(orig + "\n# the suite's last line\n")
                wrote = hashlib.sha256(read_conf().encode("latin-1")).hexdigest()
                p.key("f5", 1.5)
                p.key("b", 1.0)
                p.key("p", 1.0)
                p.key("d", 0.8)
                p.key("d", 0.8)
                section_c6(p, orig, wrote)
                section_c7(p)
                write_sections(rows, orig, forced, None)
            else:
                p.quit()
    finally:
        if orig is not None:
            try:
                write_conf(orig)
                if os.path.exists(bak_path()):
                    os.remove(bak_path())
            except OSError:
                pass
        sh.teardown()
    say("\nsandbox-tool-config: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        if mutant in WRITE_MUTANTS:
            got = sorted(set(FAILED_IDS))               # a write mutant is judged by the row ids themselves
        else:
            got = sorted({re.match(r"C\d+", i).group(0) for i in FAILED_IDS if re.match(r"C\d+", i)})
        ok = want == got
        say("sandbox-tool-config: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
