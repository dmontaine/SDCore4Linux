#!/usr/bin/env python3
#
# sandbox-tool-config.py - the configuration page, TOOL.CONFIG, driven on a PSEUDO-TERMINAL on a private SD (S.75, administrator app A6, the view half; plan
# .claude/plan-fullscreen-toolkit.md section 5).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-config.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
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
# NOT HELD: a real install's /etc/sd.conf (owner root, mode 644), the help text itself (sandbox-docs.py).
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

MUTANTS = {
    # name: (old text of the sandbox's tool_config, new text, the row ids that must fail and no others, the last section run)
    "bits-not-added": ("      fv<p> = bitor(old.v + 0, cval + 0)\n", "      fv<p> = cval\n", ["C3"], "C3"),
    "diff-ignored": ("   cmp.diff = (a # b)\n", "   cmp.diff = 0\n   a = b\n", ["C2"], "C2"),
    "unknown-not-listed": ("         unknown<-1> = fk<j>\n", "", ["C4"], "C4"),
}

# ------------------------------------------------------------------------------------------------------------------------------- the table and the file, read by Python


def table():
    rows = []
    for ln in open(os.path.join(TREE, "sdsys", "config.table"), encoding="latin-1").read().split("\n"):
        if ln.strip() == "" or ln.startswith("#"):
            continue
        f = ln.split("|")
        rows.append({"key": f[0], "kind": f[1], "default": f[2], "min": f[3], "max": f[4], "effect": f[5], "status": f[6], "text": f[7]})
    return rows


def conf_path():
    return os.path.join(sh.BOX, "sd.conf")


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


def st(h):
    return h.line(40)


def audit_lines():
    try:
        return [ln for ln in open(os.path.join(sh.SYS, "audit"), "rb").read().decode("latin-1").split("\n") if ln != ""]
    except OSError:
        return []


def setup_pages():
    for prog in ("tool_config",):
        shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", prog), os.path.join(sh.SYS, "gpl.bp", prog))
        out = g.adm(["BASIC gpl.bp " + prog], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (prog, "\n".join(out[-8:])))
    shutil.copyfile(os.path.join(TREE, "sdsys", "config.table"), os.path.join(sh.SYS, "config.table"))
    with open(os.path.join(sh.SYS, "audit"), "ab"):                 # a session appends to the audit file and never makes it: without one the page's audit line goes nowhere
        pass
    g.put(os.path.join(sh.SYS, "bp", "zzcf"), probe_program([r["key"] for r in table()]))
    out = g.adm(["BASIC bp zzcf"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the probe did not compile:\n" + "\n".join(out[-8:]))
    g.put(os.path.join(g.BOX, "user_accounts", ACC, "bp", "zzcw"), WRITER)


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
                out[name] = {"mark": t[0:2].strip(), "force": t[14:37].strip(), "file": t[37:60].strip(), "default": t[60:80].strip(), "effect": t[80:93].strip(), "status": t[93:].strip().rstrip("|").strip()}
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
        got = (s["force"], s["file"], s["default"], s["effect"], s["status"], s["mark"])
        want = (want_force, want_file, want_def, r["effect"], r["status"], mark)
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
         len(forced) == len(rows) and sorted(k for k, v in forced.items() if v is None) == ["APILOGIN", "BACKUPDIR", "SCREENTHEME", "SDSYS", "TXCHAR"], repr(sorted(k for k, v in forced.items() if v is None)))
    p = Page()
    if "The parameter under the cursor" not in p.text():
        dump(p.h)
        bail("tool.config never drew its page, so no row below can be believed")
    mine = [ln for ln in audit_lines()[a0:] if " tool " in ln]
    arow("C1b", "opening the page wrote one audit line, 'tool start app=tool.config', and no other 'tool' line", len(mine) == 1 and mine[0].endswith("tool start app=tool.config"), repr(mine))
    filev = file_values(read_conf(), kinds)
    top = p.top()
    arow("C1c", "the top box names the file as SD_CONFIG gives it, how many parameters it sets (%d), and says none differs and no restart is needed" % len(filev),
         ("File: " + conf_path()) in top and ("Parameters in it: %d" % len(filev)) in top and "Differ from what SD is running with: 0" in top and "Need a restart: 0" in top and "Names in the file that SD does not know: none" in top, top[:300])
    seen = p.collect()
    ok, detail = check_rows(seen, rows, forced, filev, kinds)
    arow("C1d", "every parameter of the table has a row: the running value, the file's value, the default, when it takes effect and the status are the probe's, the Python reader's and the table's, and no row is marked *", ok and not any(s["mark"] for s in seen.values()), detail)
    arow("C1e", "the rows come in alphabetical order, the first APILOGIN and the last YEARBASE", list(seen)[0] == "APILOGIN" and list(seen)[-1] == "YEARBASE" and list(seen) == sorted(seen), repr(list(seen)[:3]))
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
    own = [ln for ln in audit_lines() if " tool " in ln and "app=tool.config" in ln]
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


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-config.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    global MUTANT
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
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-config: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        rows = table()
        kinds = {r["key"]: r["kind"] for r in rows}
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
        else:
            p.quit()
    finally:
        if orig is not None:
            try:
                write_conf(orig)
            except OSError:
                pass
        sh.teardown()
    say("\nsandbox-tool-config: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"C\d+", i).group(0) for i in FAILED_IDS if re.match(r"C\d+", i)})
        ok = want == got
        say("sandbox-tool-config: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
