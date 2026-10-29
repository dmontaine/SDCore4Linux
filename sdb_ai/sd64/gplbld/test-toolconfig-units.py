#!/usr/bin/env python3
"""test-toolconfig-units.py - the configuration page, TOOL.CONFIG (`gpl.bp/tool_config`), and its table of parameters (`sdsys/config.table`), as invariants read off the source (S.75, administrator
app A6, the view half and, since 26 Oct 26, the write half: the page's E key and the verb SET.CONFIG).  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolconfig-units.py [--selftest]
    SD_DOCS_CHECKOUT=/some/docs/clone python3 .../test-toolconfig-units.py     (the documentation repository to read; the default is /home/don/Projects/SDCore4LinuxDocs)

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the page's BASIC and the table as text.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT THE PAGE SHOWS WHAT SD IS RUNNING WITH***: that is
`sandbox-tool-config.py` (a private SD, a hand-made sd.conf, and what CONFIG() and the file say compared with the rows).  What a text check is for: (1) THE TABLE IS HELD TO THE C
SOURCE - every parameter `read_config()` takes is in the table and nothing else is, the range of each is the one `rangecheck()` enforces, each default is the one `read_config()`
sets, a parameter that goes into the shared segment says `restart` and one a session keeps for itself says `session`, and the names the CONFIG function cannot read are the ones the
guide says; an edit to config.c that the table does not follow turns this red.  (2) THE PAGE LOOKS, AND ITS ONE WAY OF CHANGING ANYTHING IS SET.CONFIG - it opens the base for the administrator
before it reads, writes nothing itself, opens its two files for reading only, asks the backup helper to GET, never to SET, and runs one command, set.config, only in the order ask -> validate
-> box -> run -> read again (CF20 to CF24).  (3) THE VERB SET.CONFIG (`gpl.bp/setconfig`) asks for the administrator first, checks its two words before anything runs, runs only the helper's
conf-set with them, judges success by the helper's own line, writes one lower-case audit line and has its messages and its VOC entry in the right places (CF25).  (4) THE TABLE'S 'write'
COLUMN, the guide's two tables and the help text say the same thing (CF20, CF26, CF27); the helper's side of it is `test-confset-elevate-units.py`.

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
DOCS07 = os.path.join(os.environ.get("SD_DOCS_CHECKOUT", "/home/don/Projects/SDCore4LinuxDocs"), "Administrator", "markdown", "07-sd-admin-configuration.md")
FILES = {
    "page": os.path.join(GPL, "tool_config"),
    "table": os.path.join(SDSYS, "config.table"),
    "voc": os.path.join(SDSYS, "voc_template", "tool.config"),
    "verb": os.path.join(GPL, "setconfig"),
    "vocverb": os.path.join(SDSYS, "voc_template", "set.config"),
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
STATUSES = {"live", "file"}   # 27 Oct 26, S.87: 'inert' and 'retired' went with the eleven parameters that had them
# the C field that holds a shared parameter's default, and the key it is
CFG_DEFAULTS = {"cmdstack": "CMDSTACK", "numfiles": "NUMFILES", "numlocks": "NUMLOCKS", "maxidlen": "MAXIDLEN", "lgnwait": "LGNWAIT", "usplit": "USPLIT", "cleanup": "CLEANUP", "max_users": "NUMUSERS"}
KB_KEYS = {"SORTMEM", "OBJMEM"}                    # config.c keeps bytes, the table (and CONFIG) say kilobytes
IGNORED_IN_C = {"BACKUPDIR"}                       # read_config() accepts it and stores nothing
# the 14 tuning parameters the table marks write=yes (26 Oct 26); test-confset-elevate-units.py holds the helper's list to the same names
WRITABLE = ["CLEANUP", "DHCACHE", "GRPSIZE", "LGNWAIT", "LPTRHIGH", "LPTRWIDE", "MAXCALL", "MAXRLOCK", "NETREPLY", "NETWAIT", "NUMLOCKS", "RECCACHE", "SORTMRG", "USPLIT"]


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    raw["newvoc_has"] = "1" if os.path.exists(NEWVOC) else ""
    raw["newvoc_verb_has"] = "1" if os.path.exists(os.path.join(SDSYS, "newvoc", "set.config")) else ""
    raw["msgs"] = {}
    for n in range(11931, 11946):
        try:
            with open(os.path.join(SDSYS, "messages", str(n)), encoding="latin-1") as f:
                raw["msgs"][n] = f.read()
        except OSError:
            pass
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
    good3 = lambda r: (len(r) == 10 and r[1] in KINDS and r[5] in EFFECTS and r[6] in STATUSES and r[7].strip() != "" and all(x == "" or re.fullmatch(r"-?\d+", x) for x in (r[3], r[4]))
                       and r[8] in ("yes", "no") and ((r[8] == "yes" and r[9] == "") or (r[8] == "no" and 1 <= len(r[9]) <= 100 and r[9] == r[9].strip())))
    ck("CF3", "every line has ten fields, a kind, an effect and a status from the fixed lists, a text, no stray vertical bar; the numbers of a range are numbers; 'write' is yes with no reason or no with a reason of 1 to 100 characters",
       all(good3(r) for r in trs), next((r[0] for r in trs if not good3(r)), ""))
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
    ck("CF5", "THE DEFAULTS ARE THE PARSER'S: every default read_config() sets that can be read off the source (%d of them) is the table's, SORTMEM and OBJMEM in kilobytes" % len(dfl), len(dfl) >= 30 and not bad, repr(bad[:4]))
    bad = []
    for r in trs:
        d = dest.get(r[0])
        if d == "cfg" and r[5] != "restart":
            bad.append((r[0], "shared, the table says " + r[5]))
        if d == "pcfg" and r[5] != "session":
            bad.append((r[0], "the session's own, the table says " + r[5]))
    ck("CF6", "THE EFFECT IS THE PARSER'S: a parameter that read_config() puts in the shared segment says restart and one it keeps for the session says session (BACKUPDIR, which is accepted and stored nowhere, is exempt)", not bad and sum(1 for d in dest.values() if d == "cfg") >= 15, repr(bad[:4]))   # 20 before the 27 Oct 26 removals (S.87)
    # 29 Oct 26 (S.88 3.7a): CONFIG() takes a name of up to 16 characters, so SCREENTHEME (11) is readable; BACKUPDIR and SDSYS have no branch
    unreadable = sorted(k for k in keys if k not in readable or len(k) > 16)
    ck("CF7", "the parameters CONFIG() cannot read are exactly BACKUPDIR and SDSYS (a name over sixteen characters, or one the function has no branch for), SCREENTHEME being readable since the buffer went from 8 to 16 (the setter's is not touched); the guide says the same and the table says so for SDSYS and no longer for SCREENTHEME",
       unreadable == ["BACKUPDIR", "SDSYS"] and "`SDSYS` and `BACKUPDIR` cannot be read" in raw["doc"]
       and "char param[16 + 1];" in raw["opconfig"] and "k_get_c_string(descr, param, 16) < 1" in raw["opconfig"]
       and all("Not readable" in r[7] for r in trs if r[0] == "SDSYS") and all("Not readable" not in r[7] for r in trs if r[0] == "SCREENTHEME"), repr(unreadable))
    used_status = sorted({r[6] for r in trs})
    doc_status = sorted(re.findall(r"^\| `([a-z]+)` \|", raw["doc"].split("| Status | Meaning |")[-1].split("\n\n")[0], re.M))
    ck("CF8", "the guide's status table has a row for each status the table uses (%s) and for `unknown`, and none for the two that went with the eleven removed parameters (`inert`, `retired`)" % " ".join(used_status),
       doc_status == sorted(used_status + ["unknown"]) and "inert" not in doc_status and "retired" not in doc_status,
       repr((used_status, doc_status)))
    i_open = pg.find("call $tk_open('tool.config', 'admin', ctx, err)")
    i_audit = pg.find("kernel(K$AUDIT, 'tool start app=tool.config')")
    i_first = min([x for x in (pg.find("openseq"), pg.find("config("), pg.find("call !")) if x >= 0] or [10 ** 9])
    ck("CF9", "the page opens the toolkit's base for the ADMINISTRATOR first (a refusal is shown and the program stops), before it reads anything; its one audit line says it started",
       0 < i_open < i_audit < i_first and re.search(r"call \$tk_open\('tool\.config', 'admin', ctx, err\)\s*\n\s*if err # '' then\s*\n\s*display err\s*\n\s*stop\s*\n\s*end", pg) is not None and pg.count("K$AUDIT") == 1,
       "open %s audit %s first read %s" % (i_open, i_audit, i_first))
    ck("CF10", "THE PAGE'S ONE WAY OF CHANGING ANYTHING IS set.config: one $tk_run behind one $tk_confirm, one allow list that is exactly 'set.config', and no $tk_runx, execute, os.execute, perform or chain; no write of any kind (write, writeseq, delete, matwrite, ospath with OS$DELETE or OS$CHOWN), and nothing opened but the table and sd.conf, each 'readonly'",
       pg.count("call $tk_run(") == 1 and pg.count("call $tk_confirm(") == 1 and pg.count("allow = ") == 1 and "allow = 'set.config'" in pg
       and not re.search(r"\$tk_runx|\b(execute|os\.execute|perform|chain|write|writeseq|writeseqf|writev|writeu|delete|deleteseq|matwrite|matwriteu|overwrite|append)\b", pg)
       and not re.search(r"OS\$(DELETE|CHOWN|MKDIR|MKPATH|UNIQUE|CD)", pg) and pg.count("openseq") == 2 and "openseq @sdsys : @ds : 'config.table' readonly to tf then" in pg and "openseq conf.path readonly to cf then" in pg, "")
    ck("CF11", "the backup directory is READ: !acc_os_bakdir is called with 'GET' and never 'SET', and !settings_os is the only other helper (it reports, it changes nothing)",
       pg.count("call !acc_os_bakdir(") == 1 and "call !acc_os_bakdir('GET', bdir, bderr)" in pg and "'SET'" not in pg and sorted(set(re.findall(r"call (![a-z_.]+)\(", pg))) == ["!acc_os_bakdir", "!settings_os"], repr(re.findall(r"call (![a-z_.]+)\(", pg)))
    rt = block(pg, "read.table")
    rf = block(pg, "read.file")
    ck("CF12", "the table is read a line at a time, a blank line and a line beginning # skipped, eight fields split at the vertical bar; sd.conf is read the way read_config() reads it: only the [sd] section, a line beginning # skipped, the key in upper case, split at the FIRST =",
       "if ln = '' or ln[1, 1] = '#' then continue" in rt and all(("field(ln, '|', %d)" % n) in rt for n in range(1, 9)) and "section = upcase(ln[2," in rf and "if section # 'SD' then continue" in rf
       and "e = index(ln, '=', 1)" in rf and "ckey = upcase(ln[1, e - 1])" in rf and "cval = ln[e + 1, len(ln)]" in rf and "if ln = '' or ln[1, 1] = '#' then continue" in rf, rf[:160])
    ck("CF12b", "THE TABLE IS READ BY INDEX: every column of every line is assigned with its line number (nl), never appended with <-1> - an append to a still-empty array adds nothing, so the minimum and maximum (blank for the first rows) slid up and E checked a value against another parameter's range",
       "<-1>" not in rt and "nl += 1" in rt and all(("%s<nl> = field(ln, '|', %d)" % (a, n)) in rt for n, a in enumerate(("tk", "tkind", "tdef", "tmin", "tmax", "teff", "tstat", "ttext", "twrite", "twhy"), 1)), rt[:80])
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
    ck("CF16", "the key table has exactly: help, parameters, backups, report, differ, setonly, edit, refresh, quit; the dispatch has P, B, R, D, S, E, F1/?, F5 and Ctrl-Q, and E is a key of the parameters pane only",
       acts == sorted(["help", "parameters", "backups", "report", "differ", "setonly", "edit", "refresh", "quit"]) and all(("case nm = '%s'" % k) in pg for k in ("p", "b", "r", "d", "s", "e", "f5", "ctrl-q")) and "case nm = 'f1' or nm = '?'" in pg
       and "call $tk_keys('add', keys, 'e', 'change', 'edit', 'Parameters', 1)" in pg, " ".join(acts))
    ck("CF17", "the page waits for a key with no timeout (nothing here changes by itself) and reads the file, the table and the report again only when it opens, on F5, when a view that needs them is opened and after a command it ran",
       "screen key returning nm" in pg and "timeout" not in pg and pg.count("gosub read.all") == 3 and pg.count("gosub read.report") == 2 and pg.count("gosub read.backup") == 2, "read.all x%d" % pg.count("gosub read.all"))
    ck("CF18", "the page has a [?] and F1, ? and a click show tool.config.page, whose record exists with a title, the configuration page of the administrator guide (which has a section on tool.config) and a body",
       pg.count("'tool.config.page'") == 2 and "call $tk_help('mark', mk.x, mk.y, 0, 0)" in pg and "call $tk_help('hit', mev, mk.x, mk.y, hit.m)" in pg and raw["help"].split("\n")[0].strip() != "" and raw["help"].split("\n")[1].strip() == "07-sd-admin-configuration"
       and raw["help"].split("\n")[2].strip() != "" and "## The parameters on one screen: `tool.config`" in raw["doc"], "")
    dl = block(pg, "draw.all")
    dp = block(pg, "draw.params")
    dd = block(pg, "draw.param.detail")
    ld = block(pg, "lay.declare")
    lg = block(pg, "lay.get")
    ck("CF19", "the layout is the service's (S.88 L2): three panes declared at the 140 by 43 sizes (rows 1-6, 7-26, 27-39: 138 by 6, 138 by 20 stretching, 138 by 13), the boxes drawn at the panes' rectangles, the top text 6 narrower than the box's text so the [?] is clear, "
             "the header on the row under the list's border, the rows counted from the pane (VP = list height - 3, 17 at 140 by 43; DV = detail height - 2, 11) and every text as wide as the box's text (tw = width - 4, 134)",
       "'top' : @vm : 1 : @vm : 1 : @vm : 6 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'" in ld and "'list' : @vm : 2 : @vm : 1 : @vm : 20 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch'" in ld
       and "'detail' : @vm : 3 : @vm : 1 : @vm : 13 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'" in ld and "call $tk_layout('declare', ctx, d, lay.err)" in ld
       and "screen box at top.x,top.y size top.w,top.h" in dl and "screen box at lst.x,lst.y size lst.w,lst.h" in dl and "screen box at det.x,det.y size det.w,det.h" in dl
       and "VP = lst.h - 3" in lg and "DV = det.h - 2" in lg and "tw = lst.w - 4" in lg and "mk.x = top.x + top.w - 5" in lg and "mk.y = top.y + 1" in lg
       and "attr 'bold' width tw - 6" in block(pg, "draw.top") and "at tx,lst.y + 1 attr 'header'" in dp and "at tx,lst.y + 1 + r attr rat width tw" in dp and "for r = 1 to DV" in dd and "at tx,det.y + r width tw" in dd
       and "call $tk_layout('refresh', ctx, '', lay.chg)\n            gosub lay.get" in pg and re.search(r"\b(134|138|136|17)\b", re.sub(r"(?m)^   d<\d> = .*$", "", pg)) is None, "")
    # ----------------------------------------------------------------------------------------------------------- the write half (26 Oct 26)
    yes_keys = sorted(r[0] for r in trs if len(r) > 8 and r[8] == "yes")
    rtb = block(pg, "read.table")
    ck("CF20", "THE TABLE'S WRITE COLUMN: exactly the 14 parameters of the helper's list are 'yes' (%s), every one is live, range-checked by config.c and has a range in the table; the page reads fields 9 and 10 of each line and a row of the page carries them (pwrite, pwhy)" % " ".join(WRITABLE),
       yes_keys == WRITABLE and all(r[6] == "live" and r[0] in rng and r[3] != "" and r[4] != "" for r in trs if len(r) > 8 and r[8] == "yes") and "twrite<nl> = field(ln, '|', 9)" in rtb and "twhy<nl> = field(ln, '|', 10)" in rtb
       and "pwrite<i> = twrite<i>" in mr and "pwhy<i> = twhy<i>" in mr and "pmin<i> = tmin<i>" in mr and "pmax<i> = tmax<i>" in mr, " ".join(yes_keys))
    cp = block(pg, "change.param")
    marks = ["screen ask qq width 12 value '' title tt returning nv then got = 1 else got = 0", "ok = (len(nv) <= 7)", "if index('0123456789', nv[q, 1], 1) = 0 then ok = @false", "if ok then ok = (('S' : nv) = 'S0' or nv[1, 1] # '0')",
             "if ok then ok = ((nv + 0) >= (pmin<i> + 0) and (nv + 0) <= (pmax<i> + 0))", "sent = 'set.config ' : downcase(k) : ' ' : nv", "call $tk_confirm(sent, el, typed, res, cmsg)", "if res # 'run' then",
             "call $tk_run(allow, sent, out, stat, err)", "gosub read.all", "if stat = 0 and ('S' : trim(now.f)) = ('S' : nv) then"]
    at = [cp.find(m) for m in marks]
    between = cp[at[7]:at[8]] if all(x >= 0 for x in at) else "?"
    ck("CF21", "THE ORDER OF A CHANGE: ask for the value -> check its length, its digits, its leading zero and its range -> build the sentence from the table's name and the checked digits -> the box -> (Cancel returns) -> $tk_run -> read the file and SD again -> say what changed judged by the file, "
       "with nothing between the box's answer and the run",
       all(x >= 0 for x in at) and at == sorted(at) and "typed = ''" in cp and "call $tk_wrap" not in between and "gosub" not in between and "call " not in between and "if err # '' then\n      msg = err\n      return" in cp and "k.eff = peff<i>" in cp, repr(at))
    ef = block(pg, "explain.fixed")
    ed = block(pg, "edit.param")
    ck("CF22", "A PARAMETER THAT CANNOT BE CHANGED ONLY EXPLAINS: explain.fixed shows the table's reason, the file SD reads and the line KEY=<value> and when it would take effect, in a box with one button, and has no command, no box that runs, no gosub and no write",
       "pwhy<i>" in ef and "conf.path" in ef and "'=<value> in the [sd] section of '" in ef and "buttons '&Close'" in ef and not re.search(r"\$tk_(run|runx|confirm)|\b(execute|gosub|write|writeseq|openseq|delete)\b", ef) and "peff<i> = 'restart'" in ef and "peff<i> = 'session'" in ef
       and "pstat<i> = 'unknown'" in ef, ef[:120])
    ck("CF23", "E IS DECIDED BY THE TABLE, ON THE PARAMETERS VIEW ONLY: edit.param returns unless view is 1, takes a row's pwrite = 'yes' to change.param and anything else to explain.fixed; a name SD does not know is marked 'no'",
       ed.find("if view # 1 then") >= 0 and ed.find("if view # 1 then") < ed.find("i = pshow<ci>") and "if pwrite<i> = 'yes' then\n      gosub change.param\n   end else\n      gosub explain.fixed\n   end" in ed and "pwrite<n> = 'no'" in mr, ed[:160])
    ck("CF24", "THE PAGE CHECKS THE VALUE ITSELF, so most mistakes never reach the helper: at most 7 characters, digits only, no leading zero ('S0' compare, because two numeric-looking strings compare as numbers), and the table's minimum and maximum; a refusal changes nothing and says the range",
       "ok = (len(nv) <= 7)" in cp and "index('0123456789', nv[q, 1], 1) = 0" in cp and "('S' : nv) = 'S0'" in cp and "(nv + 0) >= (pmin<i> + 0)" in cp and "(nv + 0) <= (pmax<i> + 0)" in cp
       and "' takes a whole number from ' : pmin<i> : ' to ' : pmax<i> : ', digits only; nothing was changed'" in cp, "")
    hd = pg[pg.find("hp = "):pg.find("hp = ") + 260]
    ck("CF24b", "THE ROW AND THE FOOT SAY WHICH ROWS CAN CHANGE: a Change column (e or by hand), and the box at the foot says 'E changes it here' with the range or 'Not changed from this page' with the reason",
       "fmt('Status', '9L') : 'Change'" in hd and "(if pwrite<i> = 'yes' then 'e' else 'by hand')" in dp and "E changes it here: a whole number from " in dd and "'Not changed from this page: ' : pwhy<i>" in dd, "")
    vb = strip_bas(raw["verb"])
    used = sorted({int(x) for x in re.findall(r"sysmsg\((\d+)", vb)})
    adm = vb.find("if not(kernel(K$ADMINISTRATOR, -1)) then")
    seq = [adm, vb.find("if dcount(words, ' ') # 3 then stop sysmsg(11931)"), vb.find("pname = upcase(field(words, ' ', 2))"), vb.find("if index(good, pname[i, 1], 1) = 0 then ok = @false"),
           vb.find("if index('0123456789', pval[i, 1], 1) = 0 then ok = @false"), vb.find("os.execute ACCOS$ELEVATE : \" conf-set '\" : pname : \"' '\" : pval : \"' 2>&1\" capturing out"),
           vb.find("anchor = 'sd-elevate: ' : pname : ' is now ' : pval : ' in '"), vb.find("if stat # 0 or not(done) then")]
    ck("CF25", "THE VERB set.config: an internal program catalogued as $setconfig that asks for the administrator FIRST, wants exactly three words, makes the name capitals, checks the name's letters and the value's digits BEFORE the one os.execute, which is the helper's conf-set with those two words and nothing else; "
       "success is the helper's own line ('sd-elevate: NAME is now N in ') and a bad status or a missing line is a refusal",
       re.search(r"^\$internal\s*\nprogram set\.config\s*\n\$catalog \$setconfig\b", vb, re.M) is not None and all(x >= 0 for x in seq) and seq == sorted(seq) and vb.count("os.execute") == 1 and not re.search(r"\b(execute|perform|chain)\b", vb.replace("os.execute", ""))
       and "len(pname) <= 12" in vb and "len(pval) <= 7" in vb and "$include accos.h" in vb and "ACCOS$ELEVATE : \" conf-set '\"" in vb, repr(seq))
    ck("CF25b", "THE VERB'S AUDIT AND WORDS: one audit statement, in one subroutine called on the refusal and on the success, lower case, with the name, the number and the status (no other field); every message it shows exists in the range 11931 to 11937, its VOC entry is in SDSYS's VOC and in no other, and the shared VOC has none",
       vb.count("K$AUDIT") == 1 and "void kernel(K$AUDIT, 'set.config key=' : downcase(pname) : ' value=' : pval : ' status=' : st)" in vb and vb.count("gosub write.audit") == 2 and "st = 'refused'" in vb and "st = 'ok'" in vb
       and used == [2001, 11931, 11932, 11933, 11934, 11935, 11936, 11937] and all(n in raw["msgs"] and raw["msgs"][n].strip() != "" and raw["msgs"][n].count("\n") == 1 for n in range(11931, 11938))
       and raw["vocverb"].split("\n")[:3] == ["V", "CA", "$setconfig"] and raw["newvoc_verb_has"] == "", repr((used, sorted(raw["msgs"]))))
    doc = raw["doc"]
    sect = doc[doc.find("### Changing a parameter from SD"):] if "### Changing a parameter from SD" in doc else ""
    sect = sect.split("\n## ")[0]                      # the guide has other two-column tables of parameter names (the inert ones): only this section's are the write column
    d_can = re.findall(r"^\| `([A-Z0-9]+)` \| (\d+) to (\d+) \| (session|restart|now) \|$", sect, re.M)
    d_no = dict(re.findall(r"^\| `([A-Z0-9]+)` \| ([^|]+) \|$", sect, re.M))
    t_can = [(r[0], r[3], r[4], r[5]) for r in trs if len(r) > 8 and r[8] == "yes"]
    t_no = {r[0]: r[9] for r in trs if len(r) > 8 and r[8] == "no"}
    ck("CF26", "THE GUIDE'S TWO TABLES ARE THE TABLE: the 14 parameters with their range and effect, and the other 36 with the same sentence the page shows; the guide also names set.config, the .bak, the audit line and the E key",
       d_can == t_can and len(t_can) == 14 and {k: v.strip() for k, v in d_no.items()} == {k: v.strip() for k, v in t_no.items()} and len(t_no) == 36
       and all(s in doc for s in ("set.config cleanup 600", "/etc/sd.conf.bak", "set.config key=cleanup value=600 status=ok", "the `E` key of `tool.config`", "`Change`")), "can %s, no %d of %d" % (d_can[:2], len(d_no), len(t_no)))
    hp = raw["help"]
    ck("CF27", "THE HELP RECORD says what E does (it names set.config, the .bak, the fourteen parameters and the by-hand line) and no longer says the page only looks",
       "E changes the parameter under the cursor" in hp and "set.config" in hp and "sd.conf.bak" in hp and "Only 14 tuning parameters" in hp and "by hand" in hp and "The page only looks" not in hp, "")
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
    ("the table gains a name the parser does not take", "CF2", sub("table", "\nBACKUPDIR|", "\nZZNEW|int|0|||session|live|x.\nBACKUPDIR|")),
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
    ("the guide names another unreadable parameter", "CF7", sub("doc", "`SDSYS` and `BACKUPDIR` cannot be read", "`SDSYS` cannot be read")),
    ("the table forgets to say a parameter is unreadable", "CF7", sub("table", "Not readable with the CONFIG function.", "")),
    ("the table says SCREENTHEME is not readable again", "CF7", sub("table", "terminal with no colour shows mono whatever this says.", "terminal with no colour shows mono whatever this says. Not readable with the CONFIG function.")),
    ("CONFIG()'s name buffer is eight again", "CF7", sub("opconfig", "char param[16 + 1];", "char param[8 + 1];")),
    ("CONFIG()'s name limit is eight again", "CF7", sub("opconfig", "k_get_c_string(descr, param, 16) < 1", "k_get_c_string(descr, param, 8) < 1")),
    ("a parameter is marked inert again", "CF3", sub("table", "CLEANUP|int|300|30|3600|restart|live|", "CLEANUP|int|300|30|3600|restart|inert|")),
    ("the guide's status table keeps a row for a status nothing has", "CF8", sub("doc", "| `file` |", "| `inert` | nothing acts on it |\n| `file` |")),
    ("the page is opened for anyone", "CF9", sub("page", "call $tk_open('tool.config', 'admin', ctx, err)", "call $tk_open('tool.config', '', ctx, err)")),
    ("the page reads before it opens the base", "CF9", sub("page", "   call $tk_open('tool.config', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n", "   x0 = config('GRPSIZE')\n   call $tk_open('tool.config', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop\n   end\n")),
    ("the page runs a command", "CF10", sub("page", "   void kernel(K$AUDIT, 'tool start app=tool.config')\n", "   void kernel(K$AUDIT, 'tool start app=tool.config')\n   execute 'who' capturing xx\n")),
    ("the page writes sd.conf", "CF10", sub("page", "openseq conf.path readonly to cf then", "openseq conf.path to cf then")),
    ("the page deletes a file", "CF10", sub("page", "   keys = ''\n", "   delete tf, 'x'\n   keys = ''\n")),
    ("the page saves the backup directory", "CF11", sub("page", "call !acc_os_bakdir('GET', bdir, bderr)", "call !acc_os_bakdir('SET', bdir, bderr)")),
    ("a comment line is read as a parameter", "CF12", sub("page", "         if ln = '' or ln[1, 1] = '#' then continue\n*        BY INDEX", "         if ln = '' then continue\n*        BY INDEX")),
    ("the table's minimum is appended with <-1> again (a leading empty value slides the column up)", "CF12b", sub("page", "         tmin<nl> = field(ln, '|', 4)\n", "         tmin<-1> = field(ln, '|', 4)\n")),
    ("the table's maximum is appended with <-1> again", "CF12b", sub("page", "         tmax<nl> = field(ln, '|', 5)\n", "         tmax<-1> = field(ln, '|', 5)\n")),
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
    ("the lines box overruns the detail", "CF19", sub("page", "d<2> = 'list' : @vm : 2 : @vm : 1 : @vm : 20 :", "d<2> = 'list' : @vm : 2 : @vm : 1 : @vm : 21 :")),
    ("the page draws a box at a literal place again", "CF19", sub("page", "screen box at lst.x,lst.y size lst.w,lst.h title ttl", "screen box at 1,7 size 138,20 title ttl")),
    ("the resize no longer asks the layout again", "CF19", sub("page", "            call $tk_layout('refresh', ctx, '', lay.chg)\n", "")),
    # ---- the write half (26 Oct 26): the page's flow, the table's write column, the verb, the guide and the help record
    ("the page can run another command", "CF10", sub("page", "allow = 'set.config'", "allow = 'set.config sh'")),
    ("the page runs through $tk_runx", "CF10", sub("page", "call $tk_run(allow, sent, out, stat, err)", "call $tk_runx(allow, sent, out, stat, err)")),
    ("the page runs the sentence itself as well", "CF10", sub("page", "   call $tk_run(allow, sent, out, stat, err)\n", "   call $tk_run(allow, sent, out, stat, err)\n   execute sent capturing out\n")),
    ("the box is skipped", "CF21", sub("page", "   call $tk_confirm(sent, el, typed, res, cmsg)\n   if res # 'run' then", "   res = 'run'\n   if res # 'run' then")),
    ("the digits of the value are not checked", "CF24", sub("page", "      if index('0123456789', nv[q, 1], 1) = 0 then ok = @false\n", "")),
    ("a leading zero is let through", "CF24", sub("page", "   if ok then ok = (('S' : nv) = 'S0' or nv[1, 1] # '0')\n", "")),
    ("the range of the table is not checked", "CF24", sub("page", "   if ok then ok = ((nv + 0) >= (pmin<i> + 0) and (nv + 0) <= (pmax<i> + 0))\n", "")),
    ("the length of the value is not limited", "CF24", sub("page", "ok = (len(nv) <= 7)", "ok = 1")),
    ("the command is built with the name as the table spells it", "CF21", sub("page", "sent = 'set.config ' : downcase(k) : ' ' : nv", "sent = 'set.config ' : k : ' ' : nv")),
    ("the page does not read again after the command", "CF21", sub("page", "   call $tk_run(allow, sent, out, stat, err)\n   gosub read.all\n   gosub draw.all\n", "   call $tk_run(allow, sent, out, stat, err)\n   gosub draw.all\n")),
    ("success is claimed on the verb's status alone", "CF21", sub("page", "if stat = 0 and ('S' : trim(now.f)) = ('S' : nv) then", "if stat = 0 then")),
    ("a parameter that cannot be changed is edited", "CF23", sub("page", "   if pwrite<i> = 'yes' then\n      gosub change.param", "   if pwrite<i> # 'zz' then\n      gosub change.param")),
    ("E works in every view", "CF23", sub("page", "   if view # 1 then\n      msg = 'E changes a parameter: press P for the parameters first'\n      return\n   end\n", "")),
    ("a name SD does not know is writable", "CF23", sub("page", "pwrite<n> = 'no'", "pwrite<n> = 'yes'")),
    ("explaining a parameter runs something", "CF22", sub("page", "   screen msgbox body title 'Not changed here'", "   call $tk_run(allow, 'set.config sdsys 1', xo, xs, xe)\n   screen msgbox body title 'Not changed here'")),
    ("the explanation loses the line to add by hand", "CF22", sub("page", "'=<value> in the [sd] section of '", "' in the sd section of '")),
    ("the Change column is gone", "CF24b", sub("page", "fmt('Status', '9L') : 'Change'", "fmt('Status', '9L')")),
    ("the page forgets to read the table's write column", "CF20", sub("page", "         twrite<nl> = field(ln, '|', 9)\n", "")),
    ("a door becomes writable in the table", "CF20", sub("table", "|no|A door: bit 2 gates API request 29, a remote open of an account.", "|yes|")),
    ("a writable parameter becomes fixed in the table", "CF20", sub("table", "restart|live|How many record locks may be held across all sessions.|yes|", "restart|live|How many record locks may be held across all sessions.|no|Sizes a table.")),
    ("a reason is missing", "CF3", sub("table", "|no|A directory: set.backup.directory saves it, with its own checks of the path.\nCLEANUP", "|no|\nCLEANUP")),
    ("a reason runs past 100 characters", "CF3", sub("table", "|no|A diagnostic: 2 makes SD write a file of the locks involved; set it by hand while you hunt one.", "|no|A diagnostic: 2 makes SD write a file of the locks involved; set it by hand while you hunt one. " + "x" * 60)),
    ("a writable parameter carries a reason", "CF3", sub("table", "and clear them from the user table.|yes|\n", "and clear them from the user table.|yes|a reason\n")),
    ("the verb does not ask for the administrator", "CF25", sub("verb", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", "")),
    ("the verb does not check the characters of the name", "CF25", sub("verb", "      if index(good, pname[i, 1], 1) = 0 then ok = @false\n", "")),
    ("the verb does not check the characters of the value", "CF25", sub("verb", "      if index('0123456789', pval[i, 1], 1) = 0 then ok = @false\n", "")),
    ("the verb runs the words the person typed", "CF25", sub("verb", "os.execute ACCOS$ELEVATE : \" conf-set '\" : pname : \"' '\" : pval : \"' 2>&1\" capturing out", "os.execute ACCOS$ELEVATE : ' ' : words capturing out")),
    ("the verb trusts the status alone", "CF25", sub("verb", "if stat # 0 or not(done) then", "if stat # 0 then")),
    ("the verb writes a second audit line", "CF25b", sub("verb", "   st = 'ok'\n   gosub write.audit\n", "   st = 'ok'\n   gosub write.audit\n   void kernel(K$AUDIT, 'set.config done')\n")),
    ("the audit line is upper case", "CF25b", sub("verb", "'set.config key='", "'SET.CONFIG key='")),
    ("a refusal writes no audit line", "CF25b", sub("verb", "      st = 'refused'\n      gosub write.audit\n", "      st = 'refused'\n")),
    ("the verb is in every account's VOC", "CF25b", setkey("newvoc_verb_has", "1")),
    ("a message of the verb is missing", "CF25b", lambda raw: dict(raw, msgs={n: t for n, t in raw["msgs"].items() if n != 11934})),
    ("the guide's reason differs from the table's", "CF26", sub("doc", "| A diagnostic: 2 makes SD write a file of the locks involved; set it by hand while you hunt one. |", "| A diagnostic. |")),
    ("the guide's range differs from the table's", "CF26", sub("doc", "| `CLEANUP` | 30 to 3600 | restart |", "| `CLEANUP` | 30 to 36000 | restart |")),
    ("the guide forgets a parameter's row", "CF26", sub("doc", "| `YEARBASE` | Changes how every program reads a two-digit year; config.c checks no range. |\n", "")),
    ("the help still says the page only looks", "CF27", sub("help", "Only 14 tuning parameters", "The page only looks. Only 14 tuning parameters")),
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
