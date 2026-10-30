#!/usr/bin/env python3
"""test-vocremoved-units.py - the VOC deletion list (S.87), as invariants.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-vocremoved-units.py
  python3 .../test-vocremoved-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.

WHAT THIS IS AND IS NOT.  The DATA half reads sdsys/voc_removed (the shipped list) against sdsys/newvoc and sdsys/voc_template and, when git and the
release tag v1.1-3 are there, against what that release shipped:
  L1 every record of the list is well formed;
  L2 no id on the list is still shipped (a record cannot be both in NEWVOC and on the list);
  L3 every record the tree has stopped shipping since v1.1-3 IS on the list (the invariant that makes the list complete: a removal that forgets its
     list record leaves the record in every old account for ever);
  L4 each signature (type and the VOC fields 2 and 3) is the one the record had at v1.1-3 (a typo would make the update keep a record it should remove).
The TEXT half reads gpl.bp/login, vocrmchk, lstvocrm, rstvoc, the VOC records of the two verbs, the messages and the two shell scripts, and says that the
chain is written and in the right order: the removal runs after the add / change loop and before newvoc.mods; the shipped record is compared first and
nothing a person made is deleted; a copy is saved and checked BEFORE a record is deleted; every removal is audited; the verbs are administrator-only, the
listing cannot write, the restore never overwrites; the saved copies survive a keep cycle.  It cannot run an update: sandbox-vocremoved.py does that.
--selftest breaks each fact in turn and requires the check to say so.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
# regress.sh --snapshot runs this in a copy that has no .git and exports SDREGRESS_REPO, the live repository (stage 2 of 29 Oct 26 skipped L3 / L4 and counted a pass)
GITREPO = os.environ.get("SDREGRESS_REPO") or REPO
SDSYS = os.path.join(REPO, "sdb_ai", "sd64", "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
TAG = "v1.1-3"


def slurp(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def read_tree():
    t = {"list": {}, "newvoc": set(), "template": set()}
    for name in sorted(os.listdir(os.path.join(SDSYS, "voc_removed"))):
        t["list"][name] = slurp(os.path.join(SDSYS, "voc_removed", name))
    t["newvoc"] = set(os.listdir(os.path.join(SDSYS, "newvoc")))
    t["template"] = set(os.listdir(os.path.join(SDSYS, "voc_template")))
    for k in ("login", "vocrmchk", "lstvocrm", "rstvoc"):
        t[k] = slurp(os.path.join(GPL, k))
    t["verb_list"] = slurp(os.path.join(SDSYS, "voc_template", "list.voc.removed"))
    t["verb_restore"] = slurp(os.path.join(SDSYS, "voc_template", "restore.voc"))
    t["msgs"] = {n: slurp(os.path.join(SDSYS, "messages", str(n))) for n in range(11900, 11919)
                 if os.path.exists(os.path.join(SDSYS, "messages", str(n)))}
    t["delete"] = slurp(os.path.join(REPO, "deletesdcore.sh"))
    t["install"] = slurp(os.path.join(REPO, "installsdcore.sh"))
    return t


def git_tag_files(d):
    """{file name: text} of sdsys/<d> at the release tag, or None when git or the tag is not there."""
    base = "sdb_ai/sd64/sdsys/%s" % d
    r = subprocess.run(["git", "-C", GITREPO, "ls-tree", "--name-only", TAG + ":" + base], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        return None
    out = {}
    for n in r.stdout.split("\n"):
        if not n:
            continue
        s = subprocess.run(["git", "-C", GITREPO, "show", "%s:%s/%s" % (TAG, base, n)], capture_output=True, text=True, errors="replace")
        out[n] = s.stdout
    return out


def fields(rec):
    f = rec.split("\n")
    if f and f[-1] == "":
        f.pop()
    return f


def rtype(rec):
    f = fields(rec)
    first = f[0] if f else ""
    t = first[:1].upper()
    if t == "P":
        t = first[:2].upper()
    return t


def block(text, start, stop, frm=0):
    """The text from the first `start` at or after frm to the next `stop` after it; '' when either is missing."""
    a = text.find(start, frm)
    if a < 0:
        return ""
    b = text.find(stop, a + len(start))
    return text[a:b] if b >= 0 else ""


def checks(t, old_newvoc=None, old_template=None):
    res = []

    def ck(name, ok, detail=""):
        res.append((name, bool(ok), detail))

    lst = t["list"]
    # ---- the data
    bad = []
    for name, rec in lst.items():
        f = fields(rec)
        ok = len(f) >= 5 and re.fullmatch(r"[A-Z]{1,2}", f[0] or "") is not None and re.fullmatch(r"\d+\.\d+-\d+", f[3] or "") is not None and f[4].strip() != ""
        if ok and f[0] == "K" and not re.fullmatch(r"\d+", f[1] or ""):
            ok = False
        if not ok:
            bad.append(name)
    ck("L1 every record of the list has a type, the VOC fields 2 and 3 (or nothing), the release and the use-instead line (a keyword has its number)",
       lst and not bad, "malformed: %r" % bad)
    both = sorted(set(lst) & (t["newvoc"] | t["template"]))
    ck("L2 no id on the list is still shipped in NEWVOC or VOC_TEMPLATE", lst and not both, "both: %r" % both)

    if old_newvoc is None:
        old_newvoc = git_tag_files("newvoc")
        old_template = git_tag_files("voc_template")
    if old_newvoc is None or old_template is None:
        print("  [SKIP] L3 / L4: git or the tag %s is not here, so the list is not compared with what that release shipped" % TAG)
        if os.environ.get("SDREGRESS_REPO"):              # under regress.sh a skip is not a pass
            ck("L3", "git and the tag %s are here (regress.sh exports SDREGRESS_REPO: the comparison must run)" % TAG, False, "git_tag_files gave None for %s" % GITREPO)
    else:
        gone = sorted((set(old_newvoc) - t["newvoc"]) | (set(old_template) - t["template"]))
        miss = [g for g in gone if g not in lst]
        ck("L3 every record gone from NEWVOC or VOC_TEMPLATE since %s is on the list (%d are)" % (TAG, len(gone)), not miss, "not on the list: %r" % miss)
        wrong = []
        for name, rec in lst.items():
            was = old_newvoc.get(name, old_template.get(name))
            if was is None:
                continue
            f, wf = fields(rec), fields(was)
            if rtype(was) != f[0]:
                wrong.append((name, "type", f[0], rtype(was)))
            elif f[1] != "" and (len(wf) < 2 or wf[1] != f[1]):
                wrong.append((name, "field 2", f[1], wf[1] if len(wf) > 1 else None))
            elif f[2] != "" and (len(wf) < 3 or wf[2] != f[2]):
                wrong.append((name, "field 3", f[2], wf[2] if len(wf) > 2 else None))
        ck("L4 each signature is what the record was at %s" % TAG, not wrong, "differs: %r" % wrong)

    # ---- login
    lg = t["login"]
    loop_end = lg.find("   close sdsys.file")
    den = lg.find("if upd.denied then return", loop_end)
    step = lg.find("   gosub remove.listed.voc", den)
    mods = lg.find("openpath @sdsys:@ds:\"newvoc.mods\"")
    ck("P1 login removes the listed records after the add / change loop and BEFORE newvoc.mods", 0 <= loop_end < den < step < mods,
       "loop end %d, denied %d, step %d, newvoc.mods %d" % (loop_end, den, step, mods))
    rt = lg.find("remove.listed.voc:\n")
    body = lg[rt:lg.find("\nend\n", rt)] if rt >= 0 else ""
    chk = body.find("call !vocrmchk(")
    dele = body.find("delete update.voc.f, rm.id")
    save = body.find("write rm.copy to rm.sv, rm.key on error")
    ck("P2 the shipped record is compared (!vocrmchk) before anything is deleted", 0 <= chk < dele, "check %d, delete %d" % (chk, dele))
    ck("P3 a copy is written before the record is deleted", 0 <= save < dele, "save %d, delete %d" % (save, dele))
    ck("P4 the delete happens only when the copy was saved", "if rm.saved.ok then" in body[:dele] and body.rfind("if rm.saved.ok then", 0, dele) > save >= 0)
    ck("P5 the delete is `on error`, and a refused one ends the account's update (upd.denied)", "delete update.voc.f, rm.id on error rm.deleted = @false" in body and "upd.denied = 1" in body[dele:])
    keep = block(body, "case rm.verdict = 'differs'", "case 1")
    ck("P6 a record that differs, or is locked, is kept: no delete in those cases", keep != "" and "delete" not in keep, keep[:60])
    aud = body.find("kernel(K$AUDIT, 'voc update account=")
    ck("P7 every update that removed or kept something is audited, after the removal", dele < aud, "delete %d, audit %d" % (dele, aud))
    ck("P8 the audit line is written in lower case words", "'voc update account='" in body and " removed=" in body and " differs=" in body and " locked=" in body)
    w1 = lg.find("upd.account = downcase(@who)")
    w2 = lg.find("upd.account = downcase(acc.name)")
    g1 = lg.find("gosub update.voc", w1)
    g2 = lg.find("gosub update.voc", w2)
    ck("P9 both callers of update.voc name the account before they call it", 0 <= w1 < g1 and 0 <= w2 < g2, "w1 %d g1 %d w2 %d g2 %d" % (w1, g1, w2, g2))
    # ---- vocrmchk
    vc = t["vocrmchk"]
    a, b, c = vc.find("case not(same)"), vc.find("[LOCKED]"), vc.find("case 1\n         verdict = 'delete'")
    ck("V1 !vocrmchk decides 'differs' before it looks at [locked], and 'delete' last", 0 <= a < b < c)
    ck("V2 a locked VERB is 'overruled' (the rule of the VOC update), a locked other record 'locked'", "verdict = if rtype = 'V' then 'overruled' else 'locked'" in vc)
    ck("V3 the type and fields 2 and 3 of the signature are all compared", "same = (rtype = upcase(sig<1>))" in vc and "(rec<2> = sig<2>)" in vc and "(rec<3> = sig<3>)" in vc)
    ck("V4 a record that is not there is 'absent'", "verdict = 'absent'" in vc.split("rtype =")[0])
    # ---- the verbs
    ls, rs = t["lstvocrm"], t["rstvoc"]
    for nm, src in (("lstvocrm", ls), ("rstvoc", rs)):
        admin = src.find("kernel(K$ADMINISTRATOR, -1)")
        first_open = min([x for x in (src.find("openpath"), src.find("!parser")) if x >= 0] or [10 ** 9])
        ck("A1 %s is $internal, catalogued, and asks for the administrator before it opens or parses anything" % nm,
           "$internal" in src and "$catalog $" in src and 0 <= admin < first_open, "admin %d, first %d" % (admin, first_open))
    code_ls = "\n".join(l for l in ls.split("\n") if not l.startswith("*"))
    ck("A2 list.voc.removed cannot change anything: no write, delete, writev or clear in it", not re.search(r"(?m)^\s*(write|writev|delete|clearfile)\b", code_ls))
    ck("A3 restore.voc puts back only a record the account does not hold now, writes `on error`, and audits", "if old # '' then" in rs and "write rec to vf, id on error" in rs and
       "kernel(K$AUDIT, 'voc restore account='" in rs)
    ck("A4 restore.voc takes the NEWEST saved copy of an id", "if at > newest.at<p> then" in rs)
    ck("A5 the two verbs are VOC records of voc_template (SDSYS), V CA with their program, and NOT of newvoc",
       t["verb_list"] == "V\nCA\n$lstvocrm\n" and t["verb_restore"] == "V\nCA\n$rstvoc\n" and "list.voc.removed" not in t["newvoc"] and "restore.voc" not in t["newvoc"]
       and "list.voc.removed" in t["template"] and "restore.voc" in t["template"])
    # ---- messages
    need = {11900: 2, 11901: 2, 11902: 2, 11903: 2, 11904: 1, 11905: 1, 11912: 1, 11913: 1, 11915: 2, 11916: 2, 11917: 2, 11918: 2}
    badm = [n for n, k in need.items() if n not in t["msgs"] or not all("%%%d" % i in t["msgs"][n] for i in range(1, k + 1))]
    ck("M1 messages 11900-11918 exist and hold the substitutions the programs pass", not badm and len(t["msgs"]) == 19, "bad: %r, found %d" % (badm, len(t["msgs"])))
    # ---- the scripts
    d, i = t["delete"], t["install"]
    save = d.find('"$sdsysdir/voc_removed.saved" "$acct_path/"')
    rmsys = d.find('sudo rm -fr "$sdsysdir"')
    ck("S1 deletesdcore.sh saves voc_removed.saved to the account path before it removes the sdsys directory, and not on a DELETE cycle",
       0 <= save < rmsys and '"$keep_accts" != "DELETE"' in d[max(0, save - 200):save], "save %d, rm %d" % (save, rmsys))
    back = i.find('sudo mv "/home/sd/voc_removed.saved" "$sdsysdir/"')
    pass1 = i.find('echo "Bootstrap pass 1."')
    walk = i.find("sudo bin/sd UPDATE.ACCOUNTS ALL")
    own = i.find('sudo chown -R sdsys:sdusers "$sdsysdir/voc_removed.saved"', walk)
    ck("S2 installsdcore.sh puts the saved copies back before bootstrap pass 1, owned by sdsys", 0 <= back < pass1 and 'chown -R sdsys:sdusers "$sdsysdir/voc_removed.saved"' in i[back:back + 200])
    ck("S3 ... and gives the copies the walk saved (it runs as root) to sdsys right after the walk", 0 <= walk < own < walk + 600, "walk %d, chown %d" % (walk, own))
    return res


def selftest():
    t = read_tree()
    base = checks(t)
    bad = [n for n, ok, _ in base if not ok]
    if bad:
        print("selftest: the real tree already fails: %s" % bad)
        return False
    import copy

    def mut(fn):
        c = copy.deepcopy(t)
        fn(c)
        return c

    def rep(key, old, new, count=1):
        def f(c):
            assert old in c[key], (key, old)
            c[key] = c[key].replace(old, new, count)
        return f

    def listrec(name, old, new):
        def f(c):
            c["list"][name] = c["list"][name].replace(old, new, 1)
        return f

    def addid(name):
        def f(c):
            c["newvoc"].add(name)
        return f

    def dropid(name):
        def f(c):
            del c["list"][name]
        return f

    lg_after = "   gosub remove.listed.voc\n   if upd.denied then return\n"

    def late(c):
        assert lg_after in c["login"]
        c["login"] = c["login"].replace(lg_after, "", 1)
        c["login"] = c["login"].replace("      close mods.f\n   end\n", "      close mods.f\n   end\n   gosub remove.listed.voc\n", 1)

    mutants = [
        ("list: a keyword with no number", mut(listrec("margin", "K\n42\n", "K\n\n")), "L1"),
        ("list: an id that is still shipped", mut(addid("margin")), "L2"),
        ("list: a record forgotten", mut(dropid("supp")), "L3"),
        ("list: a signature with the wrong number", mut(listrec("supp", "K\n81\n", "K\n82\n")), "L4"),
        ("login: the step runs after newvoc.mods", mut(late), "P1"),
        ("login: no !vocrmchk", mut(rep("login", "call !vocrmchk(rm.sig, old.rec, rm.verdict)", "rm.verdict = 'delete'")), "P2"),
        ("login: no copy before the delete", mut(rep("login", "write rm.copy to rm.sv, rm.key on error rm.saved.ok = @false", "null")), "P3"),
        ("login: deletes without a copy", mut(rep("login", "            if rm.saved.ok then\n               rm.deleted", "            if @true then\n               rm.deleted")), "P4"),
        ("login: a differing record is deleted", mut(rep("login", "rm.ids.differs<-1> = rm.id\n", "rm.ids.differs<-1> = rm.id\n            delete update.voc.f, rm.id\n")), "P6"),
        ("login: no audit", mut(rep("login", "kernel(K$AUDIT, 'voc update account='", "kernel(K$XXX, 'voc update account='")), "P7"),
        ("login: an upper-case audit word", mut(rep("login", "'voc update account='", "'VOC update account='")), "P8"),
        ("login: the walk does not name the account", mut(rep("login", "upd.account = downcase(acc.name)", "upd.account = ''")), "P9"),
        ("vocrmchk: locked looked at before differs", mut(rep("vocrmchk", "case not(same)", "case index(upcase(rec<1>), '[LOCKED]', 1)\n         verdict = 'locked'\n      case not(same)")), "V1"),
        ("vocrmchk: a locked verb is kept", mut(rep("vocrmchk", "verdict = if rtype = 'V' then 'overruled' else 'locked'", "verdict = 'locked'")), "V2"),
        ("vocrmchk: field 2 not compared", mut(rep("vocrmchk", "(rec<2> = sig<2>)", "@true")), "V3"),
        ("lstvocrm: no administrator check", mut(rep("lstvocrm", "kernel(K$ADMINISTRATOR, -1)", "@true")), "A1"),
        ("lstvocrm: it deletes", mut(rep("lstvocrm", "      display line\n", "      display line\n      delete vf, id\n")), "A2"),
        ("rstvoc: overwrites", mut(rep("rstvoc", "if old # '' then", "if @false then")), "A3"),
        ("rstvoc: not audited", mut(rep("rstvoc", "kernel(K$AUDIT, 'voc restore account='", "kernel(K$XXX, 'voc restore account='")), "A3"),
        ("rstvoc: the oldest copy wins", mut(rep("rstvoc", "if at > newest.at<p> then", "if at < newest.at<p> then")), "A4"),
        ("verb: restore.voc in newvoc too", mut(lambda c: c["newvoc"].add("restore.voc")), "A5"),
        ("message 11900 without its list", mut(lambda c: c["msgs"].__setitem__(11900, "removed\n")), "M1"),
        ("delete: no save", mut(rep("delete", '"$sdsysdir/voc_removed.saved" "$acct_path/"', "x")), "S1"),
        ("install: no restore", mut(rep("install", 'sudo mv "/home/sd/voc_removed.saved" "$sdsysdir/"', "true")), "S2"),
        ("install: no chown after the walk", mut(rep("install", 'sudo chown -R sdsys:sdusers "$sdsysdir/voc_removed.saved"\n', "true\n", 2)), "S3"),
    ]
    ok = True
    for name, c, want in mutants:
        res = checks(c)
        failed = [n.split()[0] for n, passed, _ in res if not passed]
        caught = want in failed
        print("  [%s] selftest: %s%s" % ("PASS" if caught else "FAIL", name, "" if caught else " (NOT CAUGHT; failed: %s)" % failed))
        ok = ok and caught
    return ok


def main():
    for p in (os.path.join(SDSYS, "voc_removed"), os.path.join(GPL, "vocrmchk"), os.path.join(GPL, "lstvocrm"), os.path.join(GPL, "rstvoc")):
        if not os.path.exists(p):
            print("test-vocremoved-units: CANNOT RUN - %s missing" % p)
            return 2
    if "--selftest" in sys.argv:
        return 0 if selftest() else 1
    res = checks(read_tree())
    failed = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        failed += 0 if ok else 1
    print("\ntest-vocremoved-units: %d passed, %d failed" % (len(res) - failed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
