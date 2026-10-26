#!/usr/bin/env python3
#
# sandbox-tool-catalog.py - TOOL.CATALOG, the programs of the account on one screen ($tool_catalog, S.75 DV6), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-catalog.py <dir> [--build] [--mutant=NAME|all]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  The suite copies the tree's page, VOC entries and nothing else into the sandbox before it compiles the page, so a built sandbox can be reused after an edit.
# With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others; --mutant=all does every mutant in turn (MUTANTS).
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand: zzcg1 with the edit gates (voc, bp, dict) ON and zzcg2 with them OFF.  In zzcg1, in the program file bp:
# zzcur (compiled, private copy of the same compile), zzolder (private copy of an EARLIER compile), zzloc (compiled, a local entry), zzboth (private copy and local entry), zzstale (compiled, the
# object file made older than the source), zznew (never compiled), zznloc (compiled, not catalogued), zzsub (a subroutine), zzglob (compiled, and an entry of that name in SDSYS's gcat), zzbad
# (a source with an error), zzinc.h (an include record), zz$odd (a name the page does not give to a command), local (a name the verbs read as an option); in the program file util.bp: zzutil;
# and two entries no program record accounts for: zzorph (private) and zzlorph (a local pointer to an object that is not there).  An ORDINARY session (sd -a<account>, as the sandbox user,
# not an administrator) types TOOL.CATALOG.  In zzcg2 (all gates off): zzoff2 (not compiled), zzoff (compiled), zzoffc (a private entry), zzoffl (a local entry and its object).
#
# THE INSTRUMENT.  Every outcome is read from the DISK or from SD, not from what the page said: whether an object or a catalogue record is a file in the account's directory, what a VOC record
# holds (read by an administrator session), what a SEPARATE ordinary session prints when it types the call name, and the page's own list is compared with the disk.  A row that says "nothing
# was done" is judged by the same.
#
#   C1      the page draws for an ordinary account, for its audience; the list holds the fixture programs in file and name order with the right kind, compile time, object size, state and
#           catalogues; the list agrees with the disk for every program record; the entries no program accounts for are rows of their own
#   C2      the program under the cursor in words (paths, STALE, an earlier compile, local and global lines, a subroutine's arguments); the gates line for edit gates on and off
#   C3      B compiles: Cancel is the default (nothing compiled), a source with an error shows the compiler's lines in a report box and leaves no object, a good one is compiled
#   C4      C catalogues privately: Cancel is the default, Run makes the entry and a SEPARATE session runs the program by its call name; a program not compiled and a record that is not a
#           program are refused before any box; an entry of the same name in the global catalogue is named in the box and the name is asked, a wrong name does nothing
#   C5      L catalogues locally (a VOC entry that points at the object; a separate session runs it); over a private copy the box names it and asks for the name
#   C6      D takes an entry out: the wrong name does nothing, the right name removes the entry and leaves the compiled program; with both a private and a local entry the page asks which
#   C7      X takes a local entry out AND deletes the compiled program: the wrong name does nothing, Cancel is the default, the right name removes both
#   C8      names the page does not give to a command ($odd), an option word of the verbs (local) and an include record are refused with the reason and no box opens
#   C9      B on a stale program makes it current
#   C10     an account with the edit gates off: the gate line says off, the box warns, and the verbs' own refusal is the status line; nothing is made, removed or compiled
#   C11     option catalogue.local on in the session: C and a private D are refused with the reason and nothing changes
#   C12     the filter and Esc, the second program file (util.bp), F1 and the [?], and a window under 140 by 43
import importlib.util
import os
import re
import shutil
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


sh = _load("sandbox_home_for_catalog", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zzcg1", "zzcg2"
ME = os.environ.get("USER") or os.getlogin()
SCREEN = [None]      # the pty session of the section running: a failed row prints what it was looking at


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


MUTANTS = {
    # name: (old text of the sandbox's tool_catalog, new text, the row ids that must fail and no others, the sections that run)
    "decat-no-typed-name": ("call $tk_confirm(sent, lines, lid, res, cmsg)", "call $tk_confirm(sent, lines, '', res, cmsg)", ["C7"], ["decat"]),
    "delcat-always-local": ("sent = 'delete.catalog ' : cname : (if which = 2 then ' local' else '')", "sent = 'delete.catalog ' : cname : ' local'", ["C6"], ["del"]),
    "no-page-name-check": ("   fn = pfile\n   gosub check.name\n   ok1 = okname\n   fn = pname\n   gosub check.name\n", "   ok1 = @true\n   okname = @true\n", ["C8"], ["names"]),
    "cat-no-typed-name": ("typed.name = (if others # '' then pname else '')", "typed.name = ''", ["C5"], ["catothers"]),
    "dup-by-path": ("locate sname in locid<1> setting lq else lq = 0", "lq = 0", ["C13"], ["dup"]),
    "decat-outside-open": ("   if rtype<mk> # 'p' and (rpath<mk> = '' or not(kernel(K$PATH.OK, rpath<mk>))) then", "   if 0 then", ["C13"], ["dup"]),
    "stale-inverted": ("mstate = (if msm + 0 > mom + 0 then 'stale' else 'current')", "mstate = (if msm + 0 < mom + 0 then 'stale' else 'current')", ["C1", "C2", "C9"], ["list", "stale"]),
}


def box():
    return sh.BOX


def acct_dir(a):
    return os.path.join(box(), "user_accounts", a)


def reg_record(name, edit):
    e = "yes" if edit else "no"
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", e, e, e, "", "", "no", "", "", ""]


def sync_tree():
    """the tree's page and VOC entries into the sandbox (a built sandbox is reused after an edit); the page is compiled by compile_page()"""
    for sub, name in (("gpl.bp", "tool_catalog"), ("newvoc", "tool.catalog"), ("voc_template", "tool.catalog")):
        shutil.copyfile(os.path.join(TREE, "sdsys", sub, name), os.path.join(sh.SYS, sub, name))


def compile_page():
    out = adm("BASIC gpl.bp tool_catalog")
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_catalog did not compile in the sandbox:\n" + "\n".join(out[-10:]))
    if has(out, r"is not assigned a value"):
        bail("tool_catalog compiled with a warning that a variable is not assigned a value:\n" + "\n".join(out[-10:]))


def mutate(name):
    old, new = MUTANTS[name][0], MUTANTS[name][1]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_catalog")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    compile_page()


# ---------------------------------------------------------------------------------------------------------------------------------- evidence

def obj_path(a, f, n):
    return os.path.join(acct_dir(a), f + ".out", n)


def has_obj(a, n, f="bp"):
    return os.path.exists(obj_path(a, f, n))


def cat_path(a, n):
    return os.path.join(acct_dir(a), "cat", n)


def has_cat(a, n):
    return os.path.exists(cat_path(a, n))


def gcat_has(n):
    return os.path.exists(os.path.join(sh.SYS, "gcat", n))


def vocq(account, ids):
    """{id: (type, second field, third field)} or None, read from the account's VOC by an ADMINISTRATOR session (the account's own session is what the page runs in)"""
    src = ["$internal", "   openpath '%s/voc' to v else crt 'VQ no voc' ; stop" % acct_dir(account)]
    for i in ids:
        src += ["   read r from v, '%s' then crt 'VQ[%s|':r<1>:'|':r<2>:'|':r<3>:']' else crt 'VQ[%s|none]'" % (i, i, i)]
    src += ["end", ""]
    g.put(os.path.join(sh.SYS, "bp", "zzvq"), "\n".join(src))
    out = adm("BASIC bp zzvq", "RUN bp zzvq")
    res = {}
    for ln in out:
        m = re.match(r"^VQ\[([^|]*)\|(.*)\]$", ln.strip())
        if m:
            res[m.group(1)] = None if m.group(2) == "none" else tuple((m.group(2).split("|") + ["", "", ""])[:3])
    return res


def mkloc(account, ident, path):
    """a local catalogue entry (V / CS / object path) written into the account's VOC by an administrator session"""
    g.put(os.path.join(sh.SYS, "bp", "zzmkloc"), "\n".join([
        "$internal", "   openpath '%s/voc' to v else crt 'MKLOC no voc' ; stop" % acct_dir(account),
        "   write 'V':@fm:'CS':@fm:'%s' on v, '%s'" % (path, ident), "   crt 'MKLOC done'", "end", ""]))
    out = adm("BASIC bp zzmkloc", "RUN bp zzmkloc")
    if not has(out, r"^MKLOC done$"):
        bail("the local entry %s was not made in %s:\n%s" % (ident, account, "\n".join(out[-6:])))


def runs(account, name, expect):
    """a SEPARATE ordinary session types the call name: does it print what the program prints"""
    return has(g.plain(account, [name]), r"^" + re.escape(expect) + r"$")


# ---------------------------------------------------------------------------------------------------------------------------------- fixtures

SRC = {
    "zzcur": "   crt 'ZZCUR OK'\nend\n",
    "zzolder": "   crt 'ZZOLDER OK'\nend\n",
    "zzloc": "   crt 'ZZLOC OK'\nend\n",
    "zzboth": "   crt 'ZZBOTH OK'\nend\n",
    "zzstale": "   crt 'ZZSTALE OK'\nend\n",
    "zznew": "   crt 'ZZNEW OK'\nend\n",
    "zznloc": "   crt 'ZZNLOC OK'\nend\n",
    "zzsub": "subroutine zzsub(a, b)\n   b = a\n   return\nend\n",
    "zzglob": "   crt 'ZZGLOB OK'\nend\n",
    "zzbad": "   for i = 1 to\nend\n",
    "zzinc.h": "$define ZZINC 1\n",
    "zz$odd": "   crt 'ZZODD OK'\nend\n",
    "local": "   crt 'LOCAL OK'\nend\n",
}
SRC2 = {
    "zzoff": "   crt 'ZZOFF OK'\nend\n",
    "zzoff2": "   crt 'ZZOFF2 OK'\nend\n",
    "zzoffc": "   crt 'ZZOFFC OK'\nend\n",
    "zzoffl": "   crt 'ZZOFFL OK'\nend\n",
}


def setup_catalog():
    q = sh.g
    sync_tree()
    compile_page()
    for a in (A1, A2):
        q.FIXTURES[a] = ("no", "no")
        q.build_account(a)
        q.reg_write(a, reg_record(a, True))                     # the gates are on while the fixtures are made; A2's are switched off at the end
    d1, d2 = acct_dir(A1), acct_dir(A2)
    for n, t in SRC.items():
        q.put(os.path.join(d1, "bp", n), t)
    for n, t in SRC2.items():
        q.put(os.path.join(d2, "bp", n), t)
    out = q.plain(A1, ["CREATE.FILE util.bp DIRECTORY"])
    if not os.path.isdir(os.path.join(d1, "util.bp")):
        bail("the program file util.bp was not made:\n" + "\n".join(out[-6:]))
    q.put(os.path.join(d1, "util.bp", "zzutil"), "   crt 'ZZUTIL OK'\nend\n")
    say("    (the compiler's lines for the source with an error, for the log)")
    bad = q.plain(A1, ["BASIC bp zzbad"])
    for ln in bad[-6:]:
        say("      | " + ln)
    out = q.plain(A1, ["BASIC bp zzcur zzolder zzloc zzboth zzstale zznloc zzsub zzglob", "BASIC util.bp zzutil"])
    if not has(out, r"^Compiled 8 program\(s\) with no errors"):
        bail("the fixture programs were not compiled:\n" + "\n".join(out[-12:]))
    out = q.plain(A1, ["CATALOG bp zzcur", "CATALOG bp zzolder", "CATALOG bp zzloc LOCAL"])
    if not (has(out, r"zzcur added to private catalogue") and has(out, r"zzolder added to private catalogue") and has(out, r"zzloc added to local catalogue")):
        bail("the fixture entries were not catalogued:\n" + "\n".join(out[-8:]))
    time.sleep(1.4)                                              # the object header holds seconds: a second compile must be a different second
    out = q.plain(A1, ["BASIC bp zzolder"])
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("zzolder was not compiled again:\n" + "\n".join(out[-6:]))
    past = time.time() - 7200
    os.utime(obj_path(A1, "bp", "zzstale"), (past, past))       # the object is older than its source: STALE
    shutil.copyfile(obj_path(A1, "bp", "zzboth"), cat_path(A1, "zzboth"))
    mkloc(A1, "zzboth", obj_path(A1, "bp", "zzboth"))
    shutil.copyfile(obj_path(A1, "bp", "zzcur"), cat_path(A1, "zzorph"))
    mkloc(A1, "zzlorph", obj_path(A1, "bp", "zzgone"))
    g.put(os.path.join(sh.SYS, "bp", "zzglob"), SRC["zzglob"])
    out = adm("BASIC bp zzglob", "CATALOG bp zzglob GLOBAL")
    if not (has(out, r"^Compiled 1 program\(s\) with no errors") and gcat_has("zzglob")):
        bail("zzglob was not catalogued globally:\n" + "\n".join(out[-8:]))
    out = q.plain(A2, ["BASIC bp zzoff zzoffc zzoffl", "CATALOG bp zzoffc", "CATALOG bp zzoffl LOCAL"])
    if not (has(out, r"^Compiled 3 program\(s\) with no errors") and has_cat(A2, "zzoffc")):
        bail("the fixtures of %s were not made:\n%s" % (A2, "\n".join(out[-10:])))
    q.reg_write(A2, reg_record(A2, False))
    # the fixture is what the rows below assume: stated, so that a row cannot pass on a fixture that is not there
    ok = (has_obj(A1, "zzcur") and has_cat(A1, "zzcur") and has_cat(A1, "zzolder") and has_cat(A1, "zzboth") and has_cat(A1, "zzorph") and not has_obj(A1, "zznew") and not has_obj(A1, "zzbad")
          and os.path.exists(obj_path(A1, "util.bp", "zzutil")) and os.path.getmtime(obj_path(A1, "bp", "zzstale")) < os.path.getmtime(os.path.join(d1, "bp", "zzstale")))
    v = vocq(A1, ["zzloc", "zzboth", "zzlorph", "zznloc"])
    ok = ok and v.get("zzloc") and v["zzloc"][:2] == ("V", "CS") and v.get("zzboth") and v.get("zzlorph") and v.get("zznloc") is None
    if not ok:
        bail("the fixture is not what the rows assume: %r" % (v,))


# ---------------------------------------------------------------------------------------------------------------------------------- the screen

def page(account, cols=140, rows=43):
    h = H(account=account, cols=cols, rows=rows)
    SCREEN[0] = h
    h.typed("tool.catalog\r", idle=3.5)
    return h


def table(h):
    """{file/name: {kind, comp, obj, state, cat}} and the order, from the 16 rows of the first box"""
    out = {}
    order = []
    for n in range(3, 19):
        l = h.line(n)
        name = l[18:48].strip()
        if name:
            key = l[3:17].strip() + "/" + name
            order.append(key)
            out[key] = {"kind": l[48:60].strip(), "comp": l[60:78].strip(), "obj": l[79:87].strip(), "state": l[89:97].strip(), "cat": l[97:137].strip()}
    return out, order


def table_all(h):
    """the list from its top and from its end (more than 16 rows): the rows in order, once each"""
    h.key("home", idle=0.6)
    t1, o1 = table(h)
    h.key("end", idle=0.8)
    t2, o2 = table(h)
    h.key("home", idle=0.6)
    order = list(o1) + [k for k in o2 if k not in o1]
    t1.update(t2)
    return t1, order


def lower(h):
    return [h.line(n)[3:138].rstrip() for n in range(24, 39)]


def st(h):
    return h.line(40)


def norm(T):
    return re.sub(r"[|\s]+", " ", T)


def boxtext(h):
    """the words inside the confirm box on the screen, one line, its wrapped lines joined (the page behind the box is left out: it shows through at the sides); the whole screen when there is no box"""
    rows = [h.line(n) for n in range(43)]
    top = next((n for n, l in enumerate(rows) if "Run this command?" in l), None)
    if top is None:
        return norm(h.text())
    s0, s1 = rows[top].index("+"), rows[top].rindex("+")
    inner = []
    for n in range(top + 1, 43):
        if rows[n][s0:s0 + 1] == "+":
            break
        inner.append(rows[n][s0 + 1:s1])
    return norm(" ".join(inner))


def filt(h, text):
    h.typed("/", idle=0.8)
    h.typed(text + "\r", idle=1.0)


def until(h, pred, secs=25.0):
    """a verb that the page runs prints nothing while it runs, so a wait for idle output is not a wait for the page: pump the pty until the screen satisfies pred"""
    for _ in range(int(secs / 0.5)):
        if pred(h.text()):
            return True
        h.s._pump(0.5)
    return pred(h.text())


def back(h):
    return until(h, lambda t: "The program under the cursor" in t and "Run this command?" not in t)


def run_with_name(h, key, name, wait=None):
    """key, Run, the name typed"""
    h.typed(key, idle=1.3)
    h.typed("r", idle=1.2)
    h.typed(name + "\r", idle=2.5)
    if wait:
        until(h, wait, 15.0)


# ---------------------------------------------------------------------------------------------------------------------------------- sections

def section_list():
    say("\n--- C1 and C2: the list, the program under the cursor, the filter, the gates")
    h = page(A1)
    T = h.text()
    if "The program under the cursor" not in T:
        dump(h)
        bail("tool.catalog never drew its page in an ordinary account, so no row below can be believed")
    tb, order = table_all(h)
    arow("C1", "the page draws for an ordinary account, for the audience %s@%s (the right end of row 0), titled with the account" % (ME, A1),
         re.search(r"tool\.catalog\s+%s@%s" % (re.escape(ME), A1), h.line(0)) is not None and "Programs in %s" % A1 in T, repr(h.line(0)[100:]))
    want = ["bp/local", "bp/zz$odd", "bp/zzbad", "bp/zzboth", "bp/zzcur", "bp/zzglob", "bp/zzinc.h", "bp/zzloc", "bp/zznew", "bp/zznloc", "bp/zzolder", "bp/zzstale", "bp/zzsub", "util.bp/zzutil",
            "(private)/zzorph", "(local)/zzlorph"]
    arow("C1b", "the list is every program record of both program files in file and name order, then the private entry and the local entry no program accounts for", order == want, repr(order))
    g_ = lambda k, f: tb.get(k, {}).get(f)
    arow("C1c", "kinds: zzcur a program, zzsub a subroutine, zzinc.h an include, zz$odd and zznew and zzbad not compiled (-); the orphan private copy is a program; a state: zzcur current, zzstale STALE, zznew -",
         g_("bp/zzcur", "kind") == "program" and g_("bp/zzsub", "kind") == "subroutine" and g_("bp/zzinc.h", "kind") == "include" and g_("bp/zz$odd", "kind") == "-" and g_("bp/zznew", "kind") == "-"
         and g_("bp/zzbad", "kind") == "-" and g_("(private)/zzorph", "kind") == "program" and g_("bp/zzcur", "state") == "current" and g_("bp/zzstale", "state") == "stale"
         and g_("bp/zznew", "state") == "-" and g_("bp/zznew", "comp") == "" and g_("bp/zznew", "obj") == "", repr((tb.get("bp/zzcur"), tb.get("bp/zzstale"), tb.get("bp/zznew"), tb.get("bp/zzsub"))))
    arow("C1d", "where each is catalogued: zzcur private, zzolder private (older), zzloc local, zzboth private and local, zzglob global, zznew none; the orphans are private and local",
         g_("bp/zzcur", "cat") == "private" and g_("bp/zzolder", "cat") == "private (older)" and g_("bp/zzloc", "cat") == "local" and g_("bp/zzboth", "cat") == "private, local"
         and g_("bp/zzglob", "cat") == "global" and g_("bp/zznew", "cat") == "" and g_("(private)/zzorph", "cat") == "private" and g_("(local)/zzlorph", "cat") == "local",
         repr({k: tb[k]["cat"] for k in tb}))
    ok = True
    bad = []
    for k, v in tb.items():
        f, n = k.split("/", 1)
        if f in ("bp", "util.bp"):
            if bool(v["comp"]) != has_obj(A1, n, f) and v["kind"] not in ("include",):
                ok = False
                bad.append((k, "object", v["comp"], has_obj(A1, n, f)))
            if f == "bp" and (v["cat"].startswith("private")) != has_cat(A1, n):
                ok = False
                bad.append((k, "cat", v["cat"], has_cat(A1, n)))
    arow("C1e", "the list agrees with the disk for every program record: it says compiled exactly when the object is a file in <file>.out, and private exactly when it is a record of the cat file", ok, repr(bad))
    # the second page of the same facts: the box under the list
    filt(h, "zzstale")
    B = lower(h)
    J = "\n".join(B)
    arow("C2", "the cursor on zzstale: its box names the source and the object by path, says STALE, and says B compiles it again",
         "bp / zzstale" in B[0] and (acct_dir(A1) + "/bp/zzstale") in J and (acct_dir(A1) + "/bp.out/zzstale") in J and "STALE" in J and "B compiles it again" in J, repr(B[:6]))
    h.key("esc", idle=1.0)
    filt(h, "zzolder")
    J = "\n".join(lower(h))
    arow("C2b", "zzolder: the private copy is from an earlier compile and C catalogues the current one", "from an earlier compile" in J and "C catalogues the current one" in J, J[:500])
    h.key("esc", idle=1.0)
    filt(h, "zzboth")
    J = "\n".join(lower(h))
    arow("C2c", "zzboth: private yes (the same compile), local yes (zzboth points at the compiled program), global none", "the same compile as the compiled program" in J and "yes, zzboth points at the compiled program" in J, J[:600])
    h.key("esc", idle=1.0)
    filt(h, "zzglob")
    J = "\n".join(lower(h))
    arow("C2d", "zzglob: an entry of that name exists in SDSYS's gcat and the page says it cannot tell whether it is this program", "an entry of that name exists" in J and "cannot tell whether it is this program" in J, J[:600])
    h.key("esc", idle=1.0)
    filt(h, "zzsub")
    J = "\n".join(lower(h))
    arow("C2e", "zzsub: a subroutine with 2 arguments", "a subroutine with 2 arguments" in J, J[:300])
    h.key("esc", idle=1.0)
    filt(h, "zzlorph")
    J = "\n".join(lower(h))
    arow("C2f", "the local entry nothing accounts for: it points at an object that is not there, and the page says so", "points at" in J and "the object it points at is not there" in J, J[:600])
    h.key("esc", idle=1.0)
    L = h.line(19)[3:138]
    arow("C2g", "the gate line, asked of the kernel, for an account with the edit gates ON", "bp-edit on" in L and "4 private and 3 local catalogue entries" in L, repr(L))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2)
    L = h.line(19)[3:138]
    arow("C2h", "...and for an account with them OFF it says off", "bp-edit off" in L, repr(L))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_basic():
    say("\n--- C3: B compiles")
    h = page(A1)
    filt(h, "zzbad")
    h.typed("b", idle=1.5)
    T = boxtext(h)
    arow("C3a", "B shows the exact command in a box with Run and Cancel and says what it does and what no.query is for",
         "basic bp zzbad no.query" in T and "Run" in T and "Cancel" in T and "no.query keeps the compiler from asking a question" in T, T[-500:])
    h.key("enter", idle=1.5)
    arow("C3b", "Enter is Cancel: nothing is compiled (no object on the disk) and the page is back", not has_obj(A1, "zzbad") and "Run this command?" not in h.text() and "The program under the cursor" in h.text(), st(h))
    h.typed("b", idle=1.3)
    h.typed("r", idle=1.0)
    until(h, lambda t: "error(s)" in t)
    T = norm(h.text())
    arow("C3c", "Run on the source with an error: the report box shows the compiler's lines (an error count, the program named as having errors) and no object was written",
         "error(s)" in T and "errors in" in T and not has_obj(A1, "zzbad"), T[-600:])
    h.key("enter", idle=1.5)
    back(h)
    tb, order = table(h)
    arow("C3d", "...Close brings the page back; the row is still not compiled and the status line says it did not compile", tb.get("bp/zzbad", {}).get("comp") == "" and "did not compile" in st(h), repr((tb.get("bp/zzbad"), st(h))))
    h.key("esc", idle=1.0)
    filt(h, "zznew")
    arow("C3e", "precondition: zznew has no object", not has_obj(A1, "zznew"), "")
    h.typed("b", idle=1.3)
    h.typed("r", idle=1.0)
    until(h, lambda t: "Compiled 1 program(s) with no errors" in t)
    T = norm(h.text())
    arow("C3f", "Run on a good source: the report box says Compiled 1 program(s) with no errors and the object is a file in bp.out", "Compiled 1 program(s) with no errors" in T and has_obj(A1, "zznew"), T[-500:])
    h.key("enter", idle=1.5)
    back(h)
    tb, order = table(h)
    r = tb.get("bp/zznew", {})
    arow("C3g", "...the row now says program, compiled, an object size and current, and the status line says it compiled with no errors",
         r.get("kind") == "program" and r.get("comp") != "" and r.get("obj", "").isdigit() and r.get("state") == "current" and "compiled with no errors" in st(h), repr((r, st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_cat():
    say("\n--- C4: C catalogues privately")
    h = page(A1)
    filt(h, "zznew")
    h.typed("c", idle=1.5)
    T = boxtext(h)
    arow("C4a", "C shows the exact command, says it copies the compiled program into the private catalogue, and asks for no typed name (nothing else is taken out)",
         "catalog bp zznew no.query" in T and "private catalogue" in T and "Run" in T and "That is why the name is asked for" not in T, T[-500:])
    h.key("enter", idle=1.5)
    arow("C4b", "Enter is Cancel: nothing is catalogued (no record in the cat file)", not has_cat(A1, "zznew"), st(h))
    h.typed("c", idle=1.3)
    h.typed("r", idle=1.0)
    until(h, lambda t: has_cat(A1, "zznew"), 15.0)
    h.s._pump(1.5)
    tb, order = table(h)
    arow("C4c", "Run: the entry is a record of the cat file, the row says private, the status line says it was added, and a SEPARATE session that types zznew runs the program",
         has_cat(A1, "zznew") and tb.get("bp/zznew", {}).get("cat") == "private" and "added to private catalogue" in st(h) and runs(A1, "zznew", "ZZNEW OK"), repr((tb.get("bp/zznew"), st(h))))
    h.key("esc", idle=1.0)
    filt(h, "zzbad")
    h.typed("c", idle=1.5)
    arow("C4d", "C on a source that was never compiled is refused before any box, with the reason", "is not compiled yet" in st(h) and "Run this command?" not in h.text(), st(h))
    h.key("esc", idle=1.0)
    filt(h, "zzinc.h")
    h.typed("c", idle=1.5)
    arow("C4e", "C on an include record is refused before any box", "not compiled by itself" in st(h) and "Run this command?" not in h.text(), st(h))
    h.key("esc", idle=1.0)
    filt(h, "zzglob")
    h.typed("c", idle=1.5)
    T = boxtext(h)
    arow("C4f", "C on zzglob: the box names the global entry that no.query would take out of the other catalogue and says that is why the name is asked for",
         "catalog bp zzglob no.query" in T and "the global entry zzglob" in T and "That is why the name is asked for" in T, T[-700:])
    h.typed("r", idle=1.3)
    h.typed("wrong\r", idle=2.0)
    arow("C4g", "...the wrong name typed does nothing: the global entry is still there and no private copy was made", gcat_has("zzglob") and not has_cat(A1, "zzglob"), st(h))
    h.typed("c", idle=1.3)
    h.key("enter", idle=1.5)
    arow("C4h", "...and Cancel does nothing either", gcat_has("zzglob") and not has_cat(A1, "zzglob"), st(h))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_catothers():
    say("\n--- C5: L catalogues locally; the name is asked when another entry would go")
    h = page(A1)
    filt(h, "zznloc")
    h.typed("l", idle=1.5)
    T = boxtext(h)
    arow("C5a", "L shows catalog bp zznloc local no.query, says it makes a VOC entry that points at the compiled program, and asks for no name", "catalog bp zznloc local no.query" in T and "VOC entry" in T
         and "That is why the name is asked for" not in T, T[-500:])
    h.typed("r", idle=1.0)
    until(h, lambda t: "added to local catalogue" in st(h), 15.0)
    v = vocq(A1, ["zznloc"]).get("zznloc")
    arow("C5b", "Run: the VOC holds zznloc as V / CS pointing at the object in bp.out, the status line says it was added, and a SEPARATE session that types zznloc runs the program",
         v is not None and v[:2] == ("V", "CS") and v[2].endswith("/bp.out/zznloc") and "added to local catalogue" in st(h) and runs(A1, "zznloc", "ZZNLOC OK"), repr((v, st(h))))
    h.key("esc", idle=1.0)
    filt(h, "zzolder")
    h.typed("l", idle=1.5)
    T = boxtext(h)
    arow("C5c", "L on zzolder, which has a private copy: the box says no.query takes the private copy out without asking, and that is why the name is asked for",
         "catalog bp zzolder local no.query" in T and "the private copy of zzolder" in T and "That is why the name is asked for" in T, T[-700:])
    h.typed("r", idle=1.3)
    h.typed("wrong\r", idle=2.0)
    v = vocq(A1, ["zzolder"]).get("zzolder")
    arow("C5", "...the wrong name typed does nothing: the private copy is still a record of the cat file and the VOC has no zzolder", has_cat(A1, "zzolder") and v is None, repr((has_cat(A1, "zzolder"), v, st(h))))
    run_with_name(h, "l", "zzolder", lambda t: not has_cat(A1, "zzolder"))
    h.s._pump(1.0)
    v = vocq(A1, ["zzolder"]).get("zzolder")
    arow("C5d", "...the right name typed: the VOC has the local entry, the private copy is gone from the disk, and the compiled program stays", v is not None and v[:2] == ("V", "CS") and not has_cat(A1, "zzolder") and has_obj(A1, "zzolder"), repr((v, st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_del():
    say("\n--- C6: D takes an entry out of the catalogue")
    h = page(A1)
    filt(h, "zzcur")
    h.typed("d", idle=1.5)
    T = boxtext(h)
    arow("C6a", "D on a program with a private copy only: the box shows delete.catalog zzcur and says the compiled program stays", "delete.catalog zzcur" in T and "private catalogue" in T and "stays" in T, T[-500:])
    h.typed("r", idle=1.3)
    h.typed("wrong\r", idle=2.0)
    arow("C6b", "...the wrong name typed does nothing: the private copy is still a record of the cat file", has_cat(A1, "zzcur"), st(h))
    run_with_name(h, "d", "zzcur", lambda t: not has_cat(A1, "zzcur"))
    h.s._pump(1.0)
    tb, order = table(h)
    arow("C6c", "...the right name typed: the private copy is gone, the compiled program is still in bp.out, and the row no longer says private", not has_cat(A1, "zzcur") and has_obj(A1, "zzcur") and tb.get("bp/zzcur", {}).get("cat") == "", repr((tb.get("bp/zzcur"), st(h))))
    h.key("esc", idle=1.0)
    filt(h, "zzboth")
    h.typed("d", idle=1.5)
    T = norm(h.text())
    arow("C6d", "D on zzboth (a private copy and a local entry): the page asks which entry", "Which entry of zzboth" in T and "Private" in T and "Local" in T, T[-400:])
    h.typed("p", idle=1.5)
    T = boxtext(h)
    arow("C6e", "...Private: the box shows delete.catalog zzboth (no local word)", "delete.catalog zzboth" in T and "delete.catalog zzboth local" not in T, T[-400:])
    h.typed("r", idle=1.3)
    h.typed("zzboth\r", idle=3.0)
    until(h, lambda t: not has_cat(A1, "zzboth"), 10.0)
    v = vocq(A1, ["zzboth"]).get("zzboth")
    arow("C6f", "...the right name typed: the private copy is gone and the local entry is still in the VOC", not has_cat(A1, "zzboth") and v is not None and v[:2] == ("V", "CS"), repr((has_cat(A1, "zzboth"), v, st(h))))
    h.typed("d", idle=1.5)
    T = boxtext(h)
    arow("C6g", "D again: only the local entry is left, so there is no question; the box shows delete.catalog zzboth local", "Which entry" not in T and "delete.catalog zzboth local" in T, T[-400:])
    h.key("enter", idle=1.5)
    v = vocq(A1, ["zzboth"]).get("zzboth")
    arow("C6h", "...Enter is Cancel: the local entry is still in the VOC", v is not None and v[:2] == ("V", "CS"), repr(v))
    h.key("esc", idle=1.0)
    filt(h, "zzorph")
    h.typed("d", idle=1.5)
    T = boxtext(h)
    arow("C6i", "D on the private entry no program accounts for: delete.catalog zzorph", "delete.catalog zzorph" in T, T[-400:])
    h.typed("r", idle=1.3)
    h.typed("zzorph\r", idle=3.0)
    until(h, lambda t: not has_cat(A1, "zzorph"), 10.0)
    tb, order = table(h)
    arow("C6j", "...the right name typed: the record is gone from the cat file and the row is gone from the list", not has_cat(A1, "zzorph") and "(private)/zzorph" not in order, repr((has_cat(A1, "zzorph"), order, st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_decat():
    say("\n--- C7: X takes a local entry out and deletes the compiled program")
    h = page(A1)
    filt(h, "zzloc")
    h.typed("x", idle=1.5)
    T = boxtext(h)
    arow("C7a", "X on zzloc: the box shows decatalog zzloc and says it deletes the compiled program too, naming its path", "decatalog zzloc" in T and "AND deletes the compiled program" in T and "/bp.out/zzloc" in T, T[-600:])
    h.typed("r", idle=1.3)
    h.typed("wrong\r", idle=2.0)
    v = vocq(A1, ["zzloc"]).get("zzloc")
    arow("C7b", "...the wrong name typed does nothing: the VOC entry and the compiled program are both still there", v is not None and v[:2] == ("V", "CS") and has_obj(A1, "zzloc"), repr((v, st(h))))
    h.typed("x", idle=1.5)
    h.key("enter", idle=1.5)
    v = vocq(A1, ["zzloc"]).get("zzloc")
    arow("C7c", "X and Enter (Cancel is the default): nothing is removed", v is not None and has_obj(A1, "zzloc"), repr(v))
    run_with_name(h, "x", "zzloc", lambda t: not has_obj(A1, "zzloc"))
    h.s._pump(1.0)
    v = vocq(A1, ["zzloc"]).get("zzloc")
    tb, order = table(h)
    arow("C7", "the right name typed: the VOC entry is gone AND the compiled program is gone from bp.out, the source stays, and the row says not compiled and not catalogued",
         v is None and not has_obj(A1, "zzloc") and os.path.exists(os.path.join(acct_dir(A1), "bp", "zzloc")) and tb.get("bp/zzloc", {}).get("comp") == "" and tb.get("bp/zzloc", {}).get("cat") == "",
         repr((v, tb.get("bp/zzloc"), st(h))))
    h.key("esc", idle=1.0)
    filt(h, "zzsub")
    h.typed("x", idle=1.5)
    arow("C7d", "X on a program with no local entry says so and opens no box", "no local catalogue entry" in st(h) and "Run this command?" not in h.text(), st(h))
    h.key("esc", idle=1.0)
    filt(h, "zzlorph")
    h.typed("x", idle=1.5)
    T = boxtext(h)
    arow("C7e", "X on the local entry whose object is not there: the box shows decatalog zzlorph", "decatalog zzlorph" in T, T[-400:])
    h.typed("r", idle=1.3)
    h.typed("zzlorph\r", idle=3.0)
    until(h, lambda t: "(local)/zzlorph" not in table(h)[1], 10.0)
    v = vocq(A1, ["zzlorph"]).get("zzlorph")
    arow("C7f", "...the right name typed: the VOC entry is gone (the verb says it cannot delete the object, which was never there) and the row is gone from the list", v is None and "(local)/zzlorph" not in table(h)[1], repr((v, st(h))))
    h.key("ctrl-q", idle=1.2)
    h.end()


A3 = "zzcl3"


def section_dup():
    say("\n--- C13: an entry of the same name that points at another program, an entry that leads outside the account, and Enter is Cancel for B on a source that would compile (their own account)")
    q = sh.g
    q.FIXTURES[A3] = ("no", "no")
    q.build_account(A3)
    q.reg_write(A3, reg_record(A3, True))
    d3 = acct_dir(A3)
    out = q.plain(A3, ["CREATE.FILE util.bp DIRECTORY"])
    if not os.path.isdir(os.path.join(d3, "util.bp")):
        bail("the program file util.bp was not made in %s:\n%s" % (A3, "\n".join(out[-6:])))
    q.put(os.path.join(d3, "bp", "zzdup"), "   crt 'ZZDUP BP'\nend\n")
    q.put(os.path.join(d3, "util.bp", "zzdup"), "   crt 'ZZDUP UTIL'\nend\n")
    q.put(os.path.join(d3, "bp", "zzcancel"), "   crt 'ZZCANCEL OK'\nend\n")
    out = q.plain(A3, ["BASIC bp zzdup", "BASIC util.bp zzdup"])
    if not (has_obj(A3, "zzdup") and os.path.exists(obj_path(A3, "util.bp", "zzdup"))):
        bail("the two zzdup programs were not compiled in %s:\n%s" % (A3, "\n".join(out[-8:])))
    mkloc(A3, "zzdup", obj_path(A3, "util.bp", "zzdup"))             # the local entry called zzdup points at util.bp's program, not bp's
    victim = os.path.join(box(), "zzvictim")
    q.put(victim, "a file outside every account\n")
    mkloc(A3, "zzoutl", victim)
    h = page(A3)
    filt(h, "zzdup")
    tb, order = table(h)
    h.typed("c", idle=1.5)
    T = boxtext(h)
    arow("C13a", "C on bp/zzdup, when the local entry called zzdup points at util.bp's program: the box says so (the local entry zzdup, it points at another program) and asks for the name, because the verb would take it out by name",
         order[:1] == ["bp/zzdup"] and "catalog bp zzdup no.query" in T and "the local entry zzdup (it points at another program)" in T and "That is why the name is asked for" in T, repr((order, T[-600:])))
    h.typed("r", idle=1.3)
    h.typed("wrong\r", idle=2.0)
    v = vocq(A3, ["zzdup"]).get("zzdup")
    arow("C13b", "...the wrong name typed does nothing: the local entry is still there, still pointing at util.bp's program, and there is no private copy", v is not None and v[:2] == ("V", "CS") and v[2].endswith("/util.bp.out/zzdup") and not has_cat(A3, "zzdup"), repr((v, has_cat(A3, "zzdup"), st(h))))
    h.key("esc", idle=1.0)
    filt(h, "zzoutl")
    h.typed("x", idle=1.5)
    arow("C13c", "X on a local entry whose pointer leads outside the account (the OS gate is off): the page says so and shows the command to type, opens no box, and the file the entry points at is still there",
         "leads outside this account" in st(h) and "type decatalog zzoutl" in st(h) and "Run this command?" not in h.text() and os.path.exists(victim), repr((st(h), os.path.exists(victim))))
    h.key("esc", idle=1.0)
    filt(h, "zzcancel")
    h.typed("b", idle=1.5)
    T = boxtext(h)
    h.key("enter", idle=2.0)
    arow("C13d", "B on a source that WOULD compile (zzcancel): the box shows basic bp zzcancel, and Enter is Cancel - no object code was made and no compiler line is on the screen",
         "basic bp zzcancel" in T and not has_obj(A3, "zzcancel") and "error(s)" not in h.text() and "Compiled 1 program" not in h.text(), repr((T[-300:], has_obj(A3, "zzcancel"))))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_names():
    say("\n--- C8: names the page does not give to a command")
    h = page(A1)
    filt(h, "zz$odd")
    h.typed("b", idle=1.5)
    S1 = st(h)
    B1 = "Run this command?" in h.text()
    if B1:
        h.key("esc", idle=1.0)
    h.typed("c", idle=1.5)
    S2 = st(h)
    B2 = "Run this command?" in h.text()
    if B2:
        h.key("esc", idle=1.0)
    arow("C8", "zz$odd is listed; B and C say the name has a character the page does not give to a command and show the verb to type, and no box opens",
         "does not give to a command" in S1 and "basic bp zz$odd" in S1 and "catalog bp zz$odd" in S2 and not B1 and not B2, repr((S1, S2, B1, B2)))
    h.key("esc", idle=1.0)
    filt(h, "local")
    h.typed("b", idle=1.5)
    S3 = st(h)
    arow("C8b", "a record called local is a word the verbs read as an option: B says so and opens no box", "read as an option" in S3 and "Run this command?" not in h.text(), S3)
    h.key("esc", idle=1.0)
    filt(h, "zzinc.h")
    h.typed("b", idle=1.5)
    arow("C8c", "an include record is not compiled by itself: B says so and opens no box", "not compiled by itself" in st(h) and "Run this command?" not in h.text(), st(h))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_stale():
    say("\n--- C9: B on a stale program")
    h = page(A1)
    filt(h, "zzstale")
    before = (h.line(3)[89:97].strip(), os.path.getmtime(obj_path(A1, "bp", "zzstale")) < os.path.getmtime(os.path.join(acct_dir(A1), "bp", "zzstale")))
    h.typed("b", idle=1.3)
    h.typed("r", idle=1.0)
    until(h, lambda t: "Compiled 1 program(s) with no errors" in t)
    h.key("enter", idle=1.5)
    back(h)
    h.s._pump(1.0)
    tb, order = table(h)
    r = tb.get("bp/zzstale", {})
    newer = os.path.getmtime(obj_path(A1, "bp", "zzstale")) >= os.path.getmtime(os.path.join(acct_dir(A1), "bp", "zzstale"))
    arow("C9", "zzstale was STALE (the disk agrees: its object file is older than its source); after B the object file is the newer and the row says current", before == ("stale", True) and newer and r.get("state") == "current",
         repr((before, newer, r)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_off():
    say("\n--- C10: an account whose edit gates are off")
    h = page(A2)
    L = h.line(19)[3:138]
    arow("C10", "the gate line says bp-edit off", "bp-edit off" in L, repr(L))
    filt(h, "zzoff2")
    h.typed("b", idle=1.5)
    T = boxtext(h)
    arow("C10a", "B on a source: the box warns that the bp-edit gate is off and the verb will refuse", "basic bp zzoff2 no.query" in T and "Your bp-edit gate is off" in T, T[-500:])
    h.typed("r", idle=1.0)
    until(h, lambda t: "bp.edit" in st(h) or "bp-edit" in st(h), 15.0)
    arow("C10b", "Run: the verb's own refusal is the status line (an account that has bp.edit), no report box opens, and no object was written", "bp.edit" in st(h) and "Run this command?" not in h.text() and not has_obj(A2, "zzoff2"), repr(st(h)))
    h.key("esc", idle=1.0)
    filt(h, "zzoff")
    # the filter holds zzoff, zzoff2, zzoffc, zzoffl: the cursor is on the first row, zzoff
    h.typed("c", idle=1.5)
    h.typed("r", idle=1.0)
    until(h, lambda t: "bp.edit" in st(h), 15.0)
    arow("C10c", "C on the compiled zzoff: the verb refuses and no record was made in the cat file", "bp.edit" in st(h) and not has_cat(A2, "zzoff"), repr(st(h)))
    h.key("esc", idle=1.0)
    filt(h, "zzoffc")
    run_with_name(h, "d", "zzoffc", lambda t: "bp.edit" in st(h))
    arow("C10d", "D on the private entry zzoffc, the name typed: the verb refuses and the entry is still a record of the cat file", "bp.edit" in st(h) and has_cat(A2, "zzoffc"), repr(st(h)))
    h.key("esc", idle=1.0)
    filt(h, "zzoffl")
    run_with_name(h, "x", "zzoffl", lambda t: "bp.edit" in st(h))
    v = vocq(A2, ["zzoffl"]).get("zzoffl")
    arow("C10e", "X on the local entry zzoffl, the name typed: the verb refuses and both the VOC entry and the compiled program are still there", "bp.edit" in st(h) and v is not None and has_obj(A2, "zzoffl"), repr((st(h), v)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_option():
    say("\n--- C11: option catalogue.local")
    h = H(account=A1)
    SCREEN[0] = h
    h.typed("option catalogue.local\r", idle=1.2)
    h.typed("tool.catalog\r", idle=3.5)
    L = h.line(19)[3:138]
    arow("C11", "the summary says option catalogue.local is on", "option catalogue.local is on" in L, repr(L))
    filt(h, "zzsub")
    h.typed("c", idle=1.5)
    arow("C11a", "C is refused with the reason before any box, and nothing is catalogued (no record in the cat file, no VOC entry)",
         "option catalogue.local is on" in st(h) and "Run this command?" not in h.text() and not has_cat(A1, "zzsub") and vocq(A1, ["zzsub"]).get("zzsub") is None, st(h))
    h.key("esc", idle=1.0)
    filt(h, "zznew")
    h.typed("d", idle=1.5)
    arow("C11b", "D on a private entry is refused with the reason and the entry is still a record of the cat file", "option catalogue.local is on" in st(h) and has_cat(A1, "zznew"), st(h))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_other():
    say("\n--- C12: the filter, the second program file, help and a small window")
    h = page(A1)
    filt(h, "util")
    tb, order = table(h)
    arow("C12", "the filter keeps the rows whose program or file name holds the text: only util.bp / zzutil is left; Esc brings every row back", order == ["util.bp/zzutil"] and (h.key("esc", idle=1.0) or True) and len(table(h)[1]) >= 10, repr(order))
    filt(h, "zzutil")
    h.typed("c", idle=1.5)
    T = boxtext(h)
    arow("C12b", "C on a program of util.bp gives the file name to the verb: catalog util.bp zzutil no.query", "catalog util.bp zzutil no.query" in T, T[-500:])
    h.typed("r", idle=1.0)
    until(h, lambda t: has_cat(A1, "zzutil"), 15.0)
    arow("C12c", "...Run: the entry is a record of the cat file and a SEPARATE session that types zzutil runs the program", has_cat(A1, "zzutil") and runs(A1, "zzutil", "ZZUTIL OK"), st(h))
    h.key("esc", idle=1.0)
    h.key("esc", idle=1.0)
    filt(h, "zznloc")
    before = table(h)[0].get("bp/zznloc", {}).get("cat")
    out = g.plain(A1, ["DELETE.CATALOG zznloc LOCAL"])
    h.key("f5", idle=2.0)
    after = table(h)[0].get("bp/zznloc", {}).get("cat")
    arow("C12h", "F5 reads everything again: zznloc was local, a SEPARATE session took the entry out, and after F5 the row says it is catalogued nowhere",
         before == "local" and has(out, r"zznloc deleted from the local catalogue") and after == "", repr((before, after, out[-2:])))
    h.key("esc", idle=1.0)
    arow("C12d", "a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    h.click(135, 2)
    T = norm(h.text())
    arow("C12e", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.2)
    T = norm(h.text())
    arow("C12f", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    h.typed("tool.catalog\r", idle=3.0)
    T = h.text()
    arow("C12g", "a window under 140 by 43 gets no page", "The program under the cursor" not in T and "Programs in" not in T, T[-300:])
    h.end()


SECTIONS = [("list", section_list), ("basic", section_basic), ("cat", section_cat), ("catothers", section_catothers), ("del", section_del), ("decat", section_decat),
            ("dup", section_dup), ("names", section_names), ("stale", section_stale), ("off", section_off), ("option", section_option), ("other", section_other)]


def run_sections(names):
    for n, f in SECTIONS:
        if names is None or n in names:
            f()


def one_mutant(name):
    del FAILED_IDS[:]
    setup_catalog()
    mutate(name)
    want = sorted(set(MUTANTS[name][2]))
    say("sandbox-tool-catalog: MUTANT %s: the rows that must fail, and nothing else: %s" % (name, ", ".join(want)))
    run_sections(MUTANTS[name][3])
    got = sorted({re.match(r"C\d+", i).group(0) for i in FAILED_IDS if re.match(r"C\d+", i)})
    ok = want == got
    say("sandbox-tool-catalog: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (name, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
    return ok


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant != "all" and mutant not in MUTANTS:
        bail("usage: sandbox-tool-catalog.py <dir> [--build] [--mutant=%s|all]" % "|".join(MUTANTS))
    rc = 0
    try:
        sh.setup("sandbox-tool-catalog.py")
        if mutant is None:
            setup_catalog()
            run_sections(None)
        else:
            results = [one_mutant(m) for m in (MUTANTS if mutant == "all" else [mutant])]
            rc = 0 if all(results) else 1
    finally:
        sh.teardown()
    say("\nsandbox-tool-catalog: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        return rc
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
