#!/usr/bin/env python3
"""test-toolconfig-units.py - the configuration page, TOOL.CONFIG (`gpl.bp/tool_config`), and its table of parameters (`sdsys/config.table`), as invariants read off the source (S.75, administrator
app A6, the view half).  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolconfig-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the page's BASIC and the table as text.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT THE PAGE SHOWS WHAT SD IS RUNNING WITH***: that is
`sandbox-tool-config.py` (a private SD, a hand-made sd.conf, and what CONFIG() and the file say compared with the rows).  What a text check is for: (1) THE TABLE IS HELD TO THE C
SOURCE - every parameter `read_config()` takes is in the table and nothing else is, the range of each is the one `rangecheck()` enforces, each default is the one `read_config()`
sets, a parameter that goes into the shared segment says `restart` and one a session keeps for itself says `session`, and the names the CONFIG function cannot read are the ones the
guide says; an edit to config.c that the table does not follow turns this red.  (2) THE PAGE ONLY LOOKS - it opens the base for the administrator before it reads, runs no command, writes
nothing, opens its two files for reading only and asks the backup helper to GET, never to SET.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
SRC = os.path.join(SD64, "gplsrc")
DOCS07 = "/home/don/Projects/SDCore4LinuxDocs/Administrator/markdown/07-sd-admin-configuration.md"
FILES = {
    "page": os.path.join(GPL, "tool_config"),
    "table": os.path.join(SDSYS, "config.table"),
    "voc": os.path.join(SDSYS, "voc_template", "tool.config"),
    "help": os.path.join(SDSYS, "helptext", "tool.config.page"),
    "configc": os.path.join(SRC, "config.c"),
    "opconfig": os.path.join(SRC, "op_config.c"),
    "doc": DOCS07,
    "hdr_dh": os.path.join(SRC, "dh.h"),
    "hdr_config": os.path.join(SRC, "config.h"),
    "hdr_sddefs": os.path.join(SRC, "sddefs.h"),
    "hdr_sysseg": os.path.join(SRC, "sysseg.h"),
}
NEWVOC = os.path.join(SDSYS, "newvoc", "tool.config")
KINDS = {"int", "bits", "flag", "text", "path", "float", "pair", "triple"}
EFFECTS = {"session", "restart", "now"}
STATUSES = {"live", "inert", "retired", "file"}
# the C field that holds a shared parameter's default, and the key it is
CFG_DEFAULTS = {"cmdstack": "CMDSTACK", "numfiles": "NUMFILES", "numlocks": "NUMLOCKS", "maxidlen": "MAXIDLEN", "lgnwait": "LGNWAIT", "usplit": "USPLIT", "cleanup": "CLEANUP", "max_users": "NUMUSERS"}
KB_KEYS = {"SORTMEM", "OBJMEM"}                    # config.c keeps bytes, the table (and CONFIG) say kilobytes
IGNORED_IN_C = {"APILOGIN", "BACKUPDIR"}           # read_config() accepts them and stores nothing


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    raw["newvoc_has"] = "1" if os.path.exists(NEWVOC) else ""
    return raw


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def block(text, label):
    m = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][a-z.0-9]*:\s*$|^end\s*$", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def table_rows(text):
    rows = []
    for ln in text.split("\n"):
        if ln.strip() == "" or ln.startswith("#"):
            continue
        rows.append(ln.split("|"))
    return rows


def macro(raw, name):
    for k in ("hdr_dh", "hdr_config", "hdr_sddefs", "hdr_sysseg"):
        m = re.search(r"#define\s+" + name + r"\s+(\d+)", raw[k])
        if m:
            return int(m.group(1))
    return None


def parser_keys(configc):
    """{key: destination} for every parameter read_config() takes, destination cfg (the shared segment), pcfg (the session's own) or ignored."""
    m = re.search(r'if \(!strcmp\(section, "SD"\)\) \{(.*?)Unrecognised configuration parameter', configc, re.S)
    body = m.group(1) if m else ""
    hits = list(re.finditer(r'(?:sscanf\(rec, |strncmp\(rec, )"([A-Z0-9]+)=', body))
    out = {}
    for i, h in enumerate(hits):
        chunk = body[h.end(): hits[i + 1].start() if i + 1 < len(hits) else len(body)]
        if re.search(r"(?<!p)cfg->", chunk):
            dest = "cfg"
        elif "pcfg." in chunk:
            dest = "pcfg"
        else:
            dest = "ignored"
        out[h.group(1)] = dest
    return out


def c_ranges(raw):
    out = {}
    for m in re.finditer(r'rangecheck\("([A-Z0-9]+)",\s*[^,]+,\s*([A-Z_0-9]+),\s*([A-Z_0-9]+),\s*errmsg', raw["configc"]):
        lo, hi = m.group(2), m.group(3)
        lo = int(lo) if lo.isdigit() else macro(raw, lo)
        hi = int(hi) if hi.isdigit() else macro(raw, hi)
        out[m.group(1)] = (lo, hi)
    return out


def c_defaults(raw):
    """{key: default as text} where read_config() sets one: pcfg lines that name their key in the comment, the shared ones by field, and the two directories."""
    c = raw["configc"]
    out = {}
    for m in re.finditer(r"pcfg\.\w+\s*=\s*([^;]+);\s*/\*\s*([A-Z0-9]+):", c):
        v, key = m.group(1).strip(), m.group(2)
        if v in ("TRUE", "FALSE"):
            v = "1" if v == "TRUE" else "0"
        elif v == "'\\0'":
            v = ""
        if key in KB_KEYS and v.isdigit():
            v = str(int(v) // 1024)
        out[key] = v
    for m in re.finditer(r"cfg->(\w+)\s*=\s*(\d+);", c):
        if m.group(1) in CFG_DEFAULTS:
            out[CFG_DEFAULTS[m.group(1)]] = m.group(2)
    m = re.search(r"cfg->userpool\s*=\s*(\w+);", c)
    if m:
        out["USERPOOL"] = str(macro(raw, m.group(1)))
    m = re.search(r"cfg->fds_limit\s*=\s*SHRT_MAX;", c)
    if m:
        out["FDS"] = "32767"
    for m in re.finditer(r'strncpy\(pcfg\.(usrdir|grpdir),\s*"([^"]+)"', c):
        out["USRDIR" if m.group(1) == "usrdir" else "GRPDIR"] = m.group(2)
    return out


def readable_names(opconfig):
    return set(re.findall(r'strcmp\(param, "([A-Z0-9]+)"\)', opconfig))


def same_default(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-18 + 1e-9 * abs(float(b))
    except ValueError:
        return False


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    pg = strip_bas(raw["page"])
    trs = table_rows(raw["table"])
    keys = [r[0] for r in trs]
    dest = parser_keys(raw["configc"])
    rng = c_ranges(raw)
    dfl = c_defaults(raw)
    readable = readable_names(raw["opconfig"])
    ck("CF0", "NULL CASE: the page, the table, the VOC entry, the help record, config.c, op_config.c and the guide were found and are not empty, the parser gave more than 40 parameters (a check on nothing would pass)",
       len(pg) > 8000 and len(trs) > 40 and raw["voc"].strip() != "" and len(raw["help"].split("\n")) >= 4 and len(raw["configc"]) > 10000 and len(raw["opconfig"]) > 3000 and raw["doc"].strip() != "" and len(dest) > 40,
       "%d %d %d" % (len(pg), len(trs), len(dest)))
    ck("CF1", "the page is an internal program catalogued as $tool_config, SDSYS's VOC has the verb for it, and the shared VOC (newvoc) has NO tool.config",
       re.search(r"^\$internal\s*\nprogram \$tool_config\s*\n\$catalog \$tool_config\b", pg, re.M) is not None and raw["voc"].split("\n")[:3] == ["V", "CA", "$tool_config"] and raw["newvoc_has"] == "",
       repr((raw["voc"][:30], raw["newvoc_has"])))
    ck("CF2", "THE TABLE IS THE PARSER'S: the keys of config.table are exactly the parameters read_config() takes (%d), each once, in alphabetical order" % len(dest),
       sorted(keys) == keys and len(set(keys)) == len(keys) and set(keys) == set(dest), "table only %s, parser only %s" % (sorted(set(keys) - set(dest)), sorted(set(dest) - set(keys))))
    ck("CF3", "every line has eight fields, a kind, an effect and a status from the fixed lists, a text, no stray vertical bar; the numbers of a range are numbers",
       all(len(r) == 8 and r[1] in KINDS and r[5] in EFFECTS and r[6] in STATUSES and r[7].strip() != "" and all(x == "" or re.fullmatch(r"-?\d+", x) for x in (r[3], r[4])) for r in trs),
       next((r[0] for r in trs if not (len(r) == 8 and r[1] in KINDS and r[5] in EFFECTS and r[6] in STATUSES and r[7].strip() != "")), ""))
    bad = []
    for r in trs:
        want = rng.get(r[0])
        have = (int(r[3]) if r[3] != "" else None, int(r[4]) if r[4] != "" else None)
        if want is None and have != (None, None):
            bad.append((r[0], "range in the table, none in config.c"))
        if want is not None and have != want:
            bad.append((r[0], have, want))
    ck("CF4", "THE RANGES ARE THE PARSER'S: the minimum and maximum of a parameter are the ones rangecheck() enforces (the macros MAX_DH_CACHE_SIZE, MAX_GROUP_SIZE and MAX_ID_LEN read from the headers), and a parameter with no rangecheck has none",
       len(rng) >= 15 and not bad and set(rng) <= set(keys), repr(bad[:3]))
    bad = []
    for r in trs:
        if r[0] in dfl and not same_default(r[2], dfl[r[0]]):
            bad.append((r[0], r[2], dfl[r[0]]))
    ck("CF5", "THE DEFAULTS ARE THE PARSER'S: every default read_config() sets that can be read off the source (%d of them) is the table's, SORTMEM and OBJMEM in kilobytes" % len(dfl), len(dfl) >= 35 and not bad, repr(bad[:4]))
    bad = []
    for r in trs:
        d = dest.get(r[0])
        if d == "cfg" and r[5] != "restart":
            bad.append((r[0], "shared, the table says " + r[5]))
        if d == "pcfg" and r[5] != "session":
            bad.append((r[0], "the session's own, the table says " + r[5]))
    ck("CF6", "THE EFFECT IS THE PARSER'S: a parameter that read_config() puts in the shared segment says restart and one it keeps for the session says session (APILOGIN and BACKUPDIR, which are accepted and stored nowhere, are exempt)", not bad and sum(1 for d in dest.values() if d == "cfg") >= 20, repr(bad[:4]))
    unreadable = sorted(k for k in keys if k not in readable or len(k) > 8)
    ck("CF7", "the parameters CONFIG() cannot read are exactly APILOGIN, BACKUPDIR, SCREENTHEME, SDSYS and TXCHAR (a name over eight characters, or one the function has no branch for); the guide says the same and the table says so for the two the page cannot show",
       unreadable == ["APILOGIN", "BACKUPDIR", "SCREENTHEME", "SDSYS", "TXCHAR"] and "`SCREENTHEME`, `SDSYS`, `APILOGIN`, `BACKUPDIR` and `TXCHAR` cannot be read" in raw["doc"]
       and all("Not readable" in r[7] for r in trs if r[0] in ("SCREENTHEME", "SDSYS")), repr(unreadable))
    inert = sorted(r[0] for r in trs if r[6] == "inert")
    retired = sorted(r[0] for r in trs if r[6] == "retired")
    ck("CF8", "the guide's status table names the same inert parameters (%s) and retired ones (%s) as the table" % (" ".join(inert), " ".join(retired)),
       sorted(re.findall(r"`([A-Z][A-Z0-9]+)`", raw["doc"].split("| `inert` |")[-1].split("\n")[0])) == inert and sorted(re.findall(r"`([A-Z][A-Z0-9]+)`", raw["doc"].split("| `retired` |")[-1].split("\n")[0])) == retired,
       repr((inert, retired)))
    i_open = pg.find("call $tk_open('tool.config', 'admin', ctx, err)")
    i_audit = pg.find("kernel(K$AUDIT, 'tool start app=tool.config')")
    i_first = min([x for x in (pg.find("openseq"), pg.find("config("), pg.find("call !")) if x >= 0] or [10 ** 9])
    ck("CF9", "the page opens the toolkit's base for the ADMINISTRATOR first (a refusal is shown and the program stops), before it reads anything; its one audit line says it started",
       0 < i_open < i_audit < i_first and re.search(r"call \$tk_open\('tool\.config', 'admin', ctx, err\)\s*\n\s*if err # '' then\s*\n\s*display err\s*\n\s*stop\s*\n\s*end", pg) is not None and pg.count("K$AUDIT") == 1,
       "open %s audit %s first read %s" % (i_open, i_audit, i_first))
    ck("CF10", "THE PAGE ONLY LOOKS: no command (no $tk_run, $tk_runx, $tk_confirm, execute, os.execute, perform, chain), no write of any kind (write, writeseq, delete, matwrite, ospath with OS$DELETE or OS$CHOWN), and nothing opened but the table and sd.conf, each 'readonly'",
       not re.search(r"\$tk_run|\$tk_runx|\$tk_confirm|\b(execute|os\.execute|perform|chain|write|writeseq|writeseqf|writev|writeu|delete|deleteseq|matwrite|matwriteu|overwrite|append)\b", pg)
       and not re.search(r"OS\$(DELETE|CHOWN|MKDIR|MKPATH|UNIQUE|CD)", pg) and pg.count("openseq") == 2 and "openseq @sdsys : @ds : 'config.table' readonly to tf then" in pg and "openseq conf.path readonly to cf then" in pg, "")
    ck("CF11", "the backup directory is READ: !acc_os_bakdir is called with 'GET' and never 'SET', and !settings_os is the only other helper (it reports, it changes nothing)",
       pg.count("call !acc_os_bakdir(") == 1 and "call !acc_os_bakdir('GET', bdir, bderr)" in pg and "'SET'" not in pg and sorted(set(re.findall(r"call (![a-z_.]+)\(", pg))) == ["!acc_os_bakdir", "!settings_os"], repr(re.findall(r"call (![a-z_.]+)\(", pg)))
    rt = block(pg, "read.table")
    rf = block(pg, "read.file")
    ck("CF12", "the table is read a line at a time, a blank line and a line beginning # skipped, eight fields split at the vertical bar; sd.conf is read the way read_config() reads it: only the [sd] section, a line beginning # skipped, the key in upper case, split at the FIRST =",
       "if ln = '' or ln[1, 1] = '#' then continue" in rt and all(("field(ln, '|', %d)" % n) in rt for n in range(1, 9)) and "section = upcase(ln[2," in rf and "if section # 'SD' then continue" in rf
       and "e = index(ln, '=', 1)" in rf and "ckey = upcase(ln[1, e - 1])" in rf and "cval = ln[e + 1, len(ln)]" in rf and "if ln = '' or ln[1, 1] = '#' then continue" in rf, rf[:160])
    fa = block(pg, "file.add")
    mr = block(pg, "merge.rows")
    cv = block(pg, "compare.values")
    ck("CF13", "a flag parameter written twice is added up as SD adds it (bits: bitor) and any other keeps the last; the running value is CONFIG(name) and a name it cannot read is said to be unreadable by STATUS(), not by guessing; DEBUG is not compared; "
       "a number is compared as a number, with a tolerance only for the decimal places a float prints",
       "tkind<i> = 'bits'" in fa and "bitor(old.v + 0, cval + 0)" in fa and "pforce<i> = config(tk<i>)" in mr and "if status() # 0 then pforce<i> = '(not readable)'" in mr and "tk<i> # 'DEBUG'" in mr
       and "cmp.diff = (a # b)" in cv and "num(a) and num(b)" in cv and "abs((a + 0) - (b + 0)) > 0.000000000000001" in cv, mr[:200])
    ck("CF14", "a name in the file that the table does not have is added as a row with status unknown, marked as disagreeing, listed at the top and explained as stopping SD and every new session",
       "pstat<n> = 'unknown'" in mr and "pdiff<n> = 1" in mr and "unknown<-1> = fk<j>" in mr and "SD does not know this name. SD will not start, and no new session will, while the file holds it" in mr
       and "NAMES IN THE FILE THAT SD DOES NOT KNOW" in block(pg, "draw.top"), mr[-300:])
    ck("CF15", "a parameter that disagrees is counted, and counted as needing a restart only when its effect is restart; the foot box says which of the two it is (this session and new sessions read the file; SD keeps the old value until it restarts)",
       "if teff<i> = 'restart' then nrestart += 1" in mr and "This parameter takes effect only when SD is next started" in block(pg, "draw.param.detail") and "Sessions started now read the file" in block(pg, "draw.param.detail"), "")
    acts = sorted(set(re.findall(r"call \$tk_keys\('add', keys, '[^']+', '[^']+', '([a-z]+)'", pg)))
    ck("CF16", "the key table has exactly: help, parameters, backups, report, differ, setonly, refresh, quit; the dispatch has P, B, R, D, S, F1/?, F5 and Ctrl-Q",
       acts == sorted(["help", "parameters", "backups", "report", "differ", "setonly", "refresh", "quit"]) and all(("case nm = '%s'" % k) in pg for k in ("p", "b", "r", "d", "s", "f5", "ctrl-q")) and "case nm = 'f1' or nm = '?'" in pg, " ".join(acts))
    ck("CF17", "the page waits for a key with no timeout (nothing here changes by itself) and reads the file, the table and the report again only when it opens, on F5 and when a view that needs them is opened",
       "screen key returning nm" in pg and "timeout" not in pg and pg.count("gosub read.all") == 2 and pg.count("gosub read.report") == 2 and pg.count("gosub read.backup") == 2, "read.all x%d" % pg.count("gosub read.all"))
    ck("CF18", "the page has a [?] and F1, ? and a click show tool.config.page, whose record exists with a title, the configuration page of the administrator guide (which has a section on tool.config) and a body",
       pg.count("'tool.config.page'") == 2 and "call $tk_help('mark', 134, 2, 0, 0)" in pg and "call $tk_help('hit', mev, 134, 2, hit.m)" in pg and raw["help"].split("\n")[0].strip() != "" and raw["help"].split("\n")[1].strip() == "07-sd-admin-configuration"
       and raw["help"].split("\n")[2].strip() != "" and "## The parameters on one screen: `tool.config`" in raw["doc"], "")
    dl = block(pg, "draw.all")
    dp = block(pg, "draw.params")
    dd = block(pg, "draw.param.detail")
    ck("CF19", "the layout fits the 140 by 43 frame: three boxes (rows 1-6, 7-26, 27-39), the top text 128 wide so the [?] is clear, the header at row 8 and 17 rows at y 9-25, the parameter under the cursor in 11 rows at y 28-38",
       "screen box at 1,1 size 138,6" in dl and "screen box at 1,7 size 138,20" in dl and "screen box at 1,27 size 138,13" in dl and "attr 'bold' width 128" in block(pg, "draw.top") and re.search(r"^\s*VP = 17\s*$", pg, re.M) is not None
       and "at 3,8 attr 'header'" in dp and "at 3,8 + r attr rat" in dp and "for r = 1 to 11" in dd and "at 3,27 + r width 134" in dd, "")
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if old not in r[key]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (key, old[:60]))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


def setkey(key, val):
    def f(raw):
        r = dict(raw)
        r[key] = val
        return r
    return f


MUTANTS = [
    ("the table loses a parameter", "CF2", sub("table", "\nYEARBASE|", "\nYEARBASEX|")),
    ("the table gains a name the parser does not take", "CF2", sub("table", "\nAPILOGIN|", "\nAPILOGIN|flag|1|||restart|retired|x.\nZZNEW|int|0|||session|live|x.\nAPILOGINX|")),
    ("the table is not in order", "CF2", sub("table", "\nCLEANUP|", "\nZZCLEANUP|")),
    ("a kind that is not one", "CF3", sub("table", "CLEANUP|int|300", "CLEANUP|integer|300")),
    ("a vertical bar in a text", "CF3", sub("table", "the checks that look for sessions", "the checks | that look for sessions")),
    ("a range moves", "CF4", sub("table", "GRPSIZE|int|4|1|8|", "GRPSIZE|int|4|1|16|")),
    ("a range the parser does not have", "CF4", sub("table", "CMDSTACK|int|99|||restart|", "CMDSTACK|int|99|1|500|restart|")),
    ("a default moves", "CF5", sub("table", "INTPREC|int|11|0|14|", "INTPREC|int|13|0|14|")),
    ("a directory default moves", "CF5", sub("table", "|/home/sd/user_accounts|", "|/home/sd/accounts|")),
    ("SORTMEM is given in bytes", "CF5", sub("table", "SORTMEM|int|4096|", "SORTMEM|int|4194304|")),
    ("a shared parameter says session", "CF6", sub("table", "NUMFILES|int|80|||restart|", "NUMFILES|int|80|||session|")),
    ("a session parameter says restart", "CF6", sub("table", "MAXCALL|int|10000|10|1000000|session|", "MAXCALL|int|10000|10|1000000|restart|")),
    ("the guide names another unreadable parameter", "CF7", sub("doc", "`SCREENTHEME`, `SDSYS`, `APILOGIN`, `BACKUPDIR` and `TXCHAR` cannot be read", "`SCREENTHEME`, `SDSYS`, `APILOGIN` and `BACKUPDIR` cannot be read")),
    ("the table forgets to say a parameter is unreadable", "CF7", sub("table", "Not readable with the CONFIG function.", "")),
    ("a parameter is inert in the table and live in the guide", "CF8", sub("table", "GDI|flag|0|||session|inert|", "GDI|flag|0|||session|live|")),
    ("the page is opened for anyone", "CF9", sub("page", "call $tk_open('tool.config', 'admin', ctx, err)", "call $tk_open('tool.config', '', ctx, err)")),
    ("the page reads before it opens the base", "CF9", sub("page", "   call $tk_open('tool.config', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n", "   x0 = config('GRPSIZE')\n   call $tk_open('tool.config', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n")),
    ("the page runs a command", "CF10", sub("page", "   void kernel(K$AUDIT, 'tool start app=tool.config')\n", "   void kernel(K$AUDIT, 'tool start app=tool.config')\n   execute 'who' capturing xx\n")),
    ("the page writes sd.conf", "CF10", sub("page", "openseq conf.path readonly to cf then", "openseq conf.path to cf then")),
    ("the page deletes a file", "CF10", sub("page", "   keys = ''\n", "   delete tf, 'x'\n   keys = ''\n")),
    ("the page saves the backup directory", "CF11", sub("page", "call !acc_os_bakdir('GET', bdir, bderr)", "call !acc_os_bakdir('SET', bdir, bderr)")),
    ("a comment line is read as a parameter", "CF12", sub("page", "         if ln = '' or ln[1, 1] = '#' then continue\n         tk<-1> = field(ln, '|', 1)", "         if ln = '' then continue\n         tk<-1> = field(ln, '|', 1)")),
    ("every section of the file is read", "CF12", sub("page", "         if section # 'SD' then continue\n", "")),
    ("a key is split at the last =", "CF12", sub("page", "         e = index(ln, '=', 1)\n         if e = 0 then continue", "         e = index(ln, '=', 2)\n         if e = 0 then continue")),
    ("a parameter written twice is not added up", "CF13", sub("page", "      fv<p> = bitor(old.v + 0, cval + 0)", "      fv<p> = cval")),
    ("DEBUG is compared", "CF13", sub("page", " and tk<i> # 'DEBUG' then", " then")),
    ("an unreadable name is guessed", "CF13", sub("page", "      if status() # 0 then pforce<i> = '(not readable)'\n", "")),
    ("an unknown name is not listed", "CF14", sub("page", "         unknown<-1> = fk<j>\n", "")),
    ("an unknown name does not count as a difference", "CF14", sub("page", "pforce<n> = '' ; pfile<n> = fv<j> ; pinfile<n> = 1 ; pdiff<n> = 1", "pforce<n> = '' ; pfile<n> = fv<j> ; pinfile<n> = 1 ; pdiff<n> = 0")),
    ("a session parameter is counted as a restart", "CF15", sub("page", "            if teff<i> = 'restart' then nrestart += 1", "            nrestart += 1")),
    ("a key is added to the table", "CF16", sub("page", "   call $tk_keys('add', keys, 's', 'set', 'setonly', 'Parameters', 1)\n", "   call $tk_keys('add', keys, 's', 'set', 'setonly', 'Parameters', 1)\n   call $tk_keys('add', keys, 'w', 'write', 'write', '', 1)\n")),
    ("the page reads on a timer", "CF17", sub("page", "      screen key returning nm\n", "      screen key timeout 3 returning nm\n")),
    ("the help key names a record that does not exist", "CF18", sub("page", "call $tk_help('box', 'tool.config.page', hm, 0, 0)\n         if hm # '' then msg = hm\n      case nm = 'ctrl-q'", "call $tk_help('box', 'tool.config.nopage', hm, 0, 0)\n         if hm # '' then msg = hm\n      case nm = 'ctrl-q'")),
    ("the help record names no page", "CF18", sub("help", "07-sd-admin-configuration", "")),
    ("the lines box overruns the detail", "CF19", sub("page", "screen box at 1,7 size 138,20 title ttl", "screen box at 1,7 size 138,21 title ttl")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:200]))
        bad += 0 if ok else 1
    return bad


def selftest(raw):
    base = [r[0] for r in checks(raw) if not r[2]]
    if base:
        print("selftest: the unchanged tree fails %s, so a mutant's own failure cannot be told from the tree's; run the plain check first" % base)
        return 1
    holes = 0
    for name, want, mut in MUTANTS:
        try:
            m = mut(raw)
        except KeyError as exc:
            print("  [FAIL] selftest: %s  <- %s" % (name, exc))
            holes += 1
            continue
        failed = sorted({r[0] for r in checks(m) if not r[2]})
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        holes += 0 if hit else 1
    print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main(argv):
    raw = load()
    print("test-toolconfig-units: tree %s" % SDSYS)
    if not raw["page"] or not raw["table"]:
        print("test-toolconfig-units: CANNOT RUN - %s or %s is not there" % (FILES["page"], FILES["table"]))
        return 2
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-toolconfig-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
