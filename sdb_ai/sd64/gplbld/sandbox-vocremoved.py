#!/usr/bin/env python3
#
# sandbox-vocremoved.py - S.87, the VOC deletion list: the VOC update removes from an account's VOC the records that SD no longer ships,
#                         only the record SD shipped, after saving a copy, with an audit line; LIST.VOC.REMOVED and RESTORE.VOC.
#                         Through ORDINARY and administrator sessions on a private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-vocremoved.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every
# row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a machine: stop it afterwards with
# sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 27 Oct 26 dm  Written for the VOC deletion list (S.87).
# END-HISTORY
#
# THE INSTRUMENT.  Every outcome is read from the DISK: the VOC of each fixture account (a BASIC program reads the records back), the
# saved copies in sdsys/voc_removed.saved (matched by their CONTENT, not their file names), the audit file.  The accounts are made by
# sandbox-gates.py's own functions (prepare, build_account) so that their sessions are ORDINARY, and stale records are planted into
# their VOCs by an administrator program:
#   zzvra  the main account (the single-account update, UPDATE.ACCOUNTS from inside it)
#   zzvrb  the same plants, updated by the administrator's UPDATE.ACCOUNTS ALL; listed first without changing anything
#   zzvrc  the control: none of the listed names, nothing must be written, saved or audited
#   zzvrd  the same plants and a VOC the session may not write
# The plants: margin, stats, col.spcs and the symbol id `><` (the list's file %G%L; `<>`, file %L%G, is a different record and still shipped) exactly as SD shipped them (removed); supp with [locked] (kept); calculate
# with another keyword number and only as a paragraph (kept, not the shipped record); zzgone2 and zzgone, two V records that this suite
# adds to the sandbox's own copy of the list, the second marked [locked] (a locked verb is removed all the same).
# A control precedes every kind of removal: the planted record is read back present BEFORE the update, so "absent after" is a removal
# and not a plant that never happened.

import getpass
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
USER = getpass.getuser()
passed = failed = 0
BOX = SYS = SD = g = None

# id -> VOC record fields (a field mark between them)
PLANTS = {
    "margin": ["K", "42"],
    "stats": ["K", "116"],
    "col.spcs": ["K", "62"],
    "><": ["K", "26"],
    "zzgone2": ["V", "CA", "$zzkf"],
    "zzgone": ["V [locked]", "CA", "$zzkf"],
    "supp": ["K [locked]", "81"],
    "calculate": ["K", "99"],
    "only": ["PA", "display kept"],
}
REMOVED = ["margin", "stats", "col.spcs", "><", "zzgone2", "zzgone"]
SCRATCH_LIST = {"zzgone": "V\nCA\n\n1.2-0\ntest entry\n", "zzgone2": "V\nCA\n\n1.2-0\ntest entry\n"}
ALL_IDS = list(PLANTS) + ["evaluate"]          # evaluate is on the list and in no fixture VOC: absent throughout


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-vocremoved: CANNOT RUN - " + msg)
    sys.exit(2)


def load_gates():
    spec = importlib.util.spec_from_file_location("sandbox_gates_for_vocremoved", os.path.join(HERE, "sandbox-gates.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.BOX, m.SYS, m.SD = BOX, SYS, SD
    return m


def acct_path(name):
    return os.path.join(BOX, "user_accounts", name)


def bas(s):
    return "'" + s + "'"


def plant(name, ids):
    """Write the planted records into the account's VOC (an administrator program), and say so."""
    lines = ["$internal", "   openpath %s to v else" % bas(acct_path(name) + "/voc"), "      crt 'PL open failed'", "      stop", "   end"]
    for i in ids:
        lines.append("   write %s to v, %s" % (":@fm:".join(bas(f) for f in PLANTS[i]), bas(i)))
    lines += ["   crt 'PL done'", "end", ""]
    g.put(os.path.join(SYS, "bp", "zzvrp"), "\n".join(lines))
    out = g.adm(["BASIC bp zzvrp", "RUN bp zzvrp"], internal=True)
    if not g.has(out, r"^PL done$"):
        bail("planting into %s failed:\n%s" % (name, "\n".join(out[-6:])))


def readback(name, ids=ALL_IDS):
    """{id: (state, field1, field2)} read from the account's VOC on the disk."""
    lines = ["$internal", "   openpath %s to v else" % bas(acct_path(name) + "/voc"), "      crt 'VR open failed'", "      stop", "   end",
             "   ids = " + ":@fm:".join(bas(i) for i in ids), "   for i = 1 to dcount(ids, @fm)", "      id = ids<i>",
             "      read r from v, id then crt 'VR ':id:' present ':r<1>:'|':r<2> else crt 'VR ':id:' absent'", "   next i", "end", ""]
    g.put(os.path.join(SYS, "bp", "zzvrr"), "\n".join(lines))
    out = g.adm(["BASIC bp zzvrr", "RUN bp zzvrr"], internal=True)
    res = {}
    for ln in out:
        m = re.match(r"^VR (\S+) (present|absent)(?: (.*)\|(.*))?$", ln)
        if m:
            res[m.group(1)] = (m.group(2), m.group(3), m.group(4))
    if len(res) != len(ids):
        bail("the read-back of %s returned %d of %d records:\n%s" % (name, len(res), len(ids), "\n".join(out[-8:])))
    return res


def saved_copies():
    """[(account, id, fields)] of every copy in sdsys/voc_removed.saved, read by content."""
    d = os.path.join(SYS, "voc_removed.saved")
    res = []
    for n in sorted(os.listdir(d)):
        if n == "README":
            continue
        with open(os.path.join(d, n), encoding="latin-1") as f:
            t = f.read().split("\n")
        res.append((t[0], t[1], t))
    return res


def audit_lines(off):
    new = ""
    try:
        with open(os.path.join(SYS, "audit"), "rb") as f:
            f.seek(off)
            new = f.read().decode("utf-8", errors="replace")
    except OSError:
        pass
    return [ln for ln in new.split("\n") if ln.strip()]


def audit_off():
    p = os.path.join(SYS, "audit")
    if not os.path.exists(p):
        open(p, "ab").close()
    return os.path.getsize(p)


def segment(out, name):
    """The lines of an UPDATE.ACCOUNTS ALL run that belong to one account: from its `Updating <path>/<name>/voc` line (so the list is empty only when
    the walk never reached the account) up to the next `Updating`."""
    seg, on = [], False
    for ln in out:
        if re.search(r"Updating ", ln):
            on = re.search(r"Updating .*/%s/voc" % re.escape(name), ln) is not None
        if on:
            seg.append(ln)
    return seg


def main():
    global BOX, SYS, SD, g
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-vocremoved.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    say("sandbox-vocremoved: sandbox  %s" % BOX)
    say("sandbox-vocremoved: tree     %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-vocremoved: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    g = load_gates()

    say("\n--- preparation: ordinary fixture accounts, the sandbox's own copy of the list, the planted records ----------------")
    for d in ("voc_removed", "voc_removed.saved"):
        if not os.path.isdir(os.path.join(SYS, d)):
            bail("the sandbox has no sdsys/%s: the tree under test does not ship the list" % d)
    shipped = sorted(os.listdir(os.path.join(SYS, "voc_removed")))
    for k, v in SCRATCH_LIST.items():
        g.put(os.path.join(SYS, "voc_removed", k), v)
    listed = sorted(os.listdir(os.path.join(SYS, "voc_removed")))
    sd_dir = os.path.join(SYS, "voc_removed.saved")
    for n in os.listdir(sd_dir):                               # copies left by an earlier run of this suite on the same sandbox
        if n != "README":
            os.unlink(os.path.join(sd_dir, n))
    g.prepare()
    for name in ("zzvra", "zzvrb", "zzvrc", "zzvrd"):
        g.FIXTURES[name] = ("no", "no")
        g.build_account(name)
    for name in ("zzvra", "zzvrb", "zzvrd"):
        plant(name, list(PLANTS))
    say("  [done] 4 accounts, %d records on the list (%d shipped, %d of this suite's)" % (len(listed), len(shipped), len(listed) - len(shipped)))

    f = g.flags(g.plain("zzvra", ["ZZKF"]))
    row("0a: a session in zzvra is not an administrator (admin=0) - the control that the update below is an ordinary account's own",
        f is not None and f[0] == "0", repr(f))
    if f is None or f[0] != "0":
        bail("the plain session is an administrator: every row below would be meaningless")
    pre = readback("zzvra")
    row("0b: before any update every planted record is on the disk, in its planted form, and evaluate (on the list, in no VOC) is absent",
        all(pre[i][0] == "present" and pre[i][1] == PLANTS[i][0] and pre[i][2] == (PLANTS[i][1] if len(PLANTS[i]) > 1 else "") for i in PLANTS)
        and pre["evaluate"][0] == "absent", repr(pre))

    # --- L. the listing --------------------------------------------------------------------------------------------
    say("\n--- L. LIST.VOC.REMOVED: the list, and what an update would do in one account, changing nothing -------------------")
    out = g.adm(["LIST.VOC.REMOVED"])
    row("L1: without an account it prints the header with the count of the whole list and a line for each shipped id",
        g.has(out, r"^%d VOC record\(s\) that SD no longer ships:" % len(listed)) and g.has(out, r"^margin\s+1\.2-0\s+left\.margin")
        and g.has(out, r"^supp\s+1\.2-0\s+hdr\.sup"), "\n".join(out[:6]))
    before = readback("zzvrb")
    out = g.adm(["LIST.VOC.REMOVED zzvrb"])
    row("L2: with an account each plant is judged as the update would judge it: removed, removed (a locked verb), kept (not the shipped record), kept (locked), absent",
        g.has(out, r"^margin .*\[would be removed\]") and g.has(out, r"^zzgone .*\[would be removed \(a locked verb\)\]")
        and g.has(out, r"^calculate .*\[kept: not the shipped record\]") and g.has(out, r"^only .*\[kept: not the shipped record\]")
        and g.has(out, r"^supp .*\[kept: locked\]") and g.has(out, r"^evaluate .*\[absent\]"), "\n".join(out))
    row("L3: it changed nothing: the VOC is as planted", readback("zzvrb") == before)
    out = g.adm(["LIST.VOC.REMOVED nosuchacct"])
    row("L4: an account that is not registered is refused in words (11912)", g.has(out, r"^Account nosuchacct is not registered\."), "\n".join(out))
    out = g.plain("zzvra", ["LIST.VOC.REMOVED"])
    row("L5: an ordinary account has no such verb", not g.has(out, r"VOC record\(s\) that SD no longer ships") and g.has(out, r"is not in your VOC"),
        "\n".join(out))

    # --- U. one walk of the administrator's UPDATE.ACCOUNTS ALL over the four accounts (zzvrd's VOC made read only for it) -----
    # (UPDATE.ACCOUNTS without ALL is not a verb of an ordinary account, and SDSYS's own run is the SDSYS account's: the walk is the real path.)
    say("\n--- U. UPDATE.ACCOUNTS ALL (mode 4), the account zzvra --------------------------------------------------------------")
    cb = readback("zzvrc")
    a0 = audit_off()
    s0 = len(saved_copies())
    vd = os.path.join(acct_path("zzvrd"), "voc")
    subprocess.run(["chmod", "-R", "a-w", vd], check=True)
    try:
        walk_out = g.adm(["UPDATE.ACCOUNTS ALL"])
    finally:
        subprocess.run(["chmod", "-R", "u+w", vd], check=True)
    row("U0: the walk ran and reported the accounts it updated (3 updated, 1 left as it was) - the control that the rows below are about the walk",
        g.has(walk_out, r"account\(s\) had their VOC updated") and g.has(walk_out, r"1 account\(s\) were left as they were"), "\n".join(walk_out[-8:]))
    out = segment(walk_out, "zzvra")
    row("U0b: the walk's output for zzvra was found (a segment that begins `Updating .../zzvra/voc`)", out != [], "\n".join(walk_out[:12]))
    post = readback("zzvra")
    dd = readback("zzvrd")                    # what the walk left in the account it could not write
    au1 = audit_lines(a0)                     # and what it audited and saved, before any second walk
    sv1 = saved_copies()
    row("U1: the records SD shipped are gone from the disk (margin, stats, col.spcs, >< and the unlocked verb)",
        all(post[i][0] == "absent" for i in ("margin", "stats", "col.spcs", "><", "zzgone2")), repr({i: post[i][0] for i in REMOVED}))
    row("U2: a locked verb is removed all the same (zzgone)", post["zzgone"][0] == "absent", repr(post["zzgone"]))
    row("U3: a locked record that is not a verb stays, whole (supp keeps its [locked] and its number)",
        post["supp"] == ("present", "K [locked]", "81"), repr(post["supp"]))
    row("U4: a record that is not the one SD shipped stays, whole (calculate with number 99, only as a paragraph)",
        post["calculate"] == ("present", "K", "99") and post["only"] == ("present", "PA", "display kept"), repr((post["calculate"], post["only"])))
    row("U5: it says what it did: removed 6, one locked verb, kept 2 (not the shipped record), kept 1 (locked), with the names",
        g.has(out, r"6 VOC record\(s\) removed, because SD no longer ships them: .*margin") and g.has(out, r"1 locked verb\(s\) were removed all the same.*zzgone")
        and g.has(out, r"2 VOC record\(s\) kept although SD no longer ships the name, because the record is not the one SD shipped: .*(calculate.*only|only.*calculate)")
        and g.has(out, r"1 VOC record\(s\) kept although SD no longer ships them, because they are marked \[locked\]: supp"), "\n".join(out))
    copies = [c for c in saved_copies() if c[0] == "zzvra"]
    ids_saved = sorted(c[1] for c in copies)
    row("U6: a copy of each of the 6 removed records was saved, under the account's name and the record's id, and no copy of a kept one",
        ids_saved == sorted(REMOVED), repr(ids_saved))
    mg = [c for c in copies if c[1] == "margin"]
    row("U7: the saved copy holds the record as it was: field 1 the account, 2 the id, a date and a time, who ran it, then the record (K, 42)",
        len(mg) == 1 and mg[0][2][5:7] == ["K", "42"] and re.fullmatch(r"\d+", mg[0][2][2]) is not None and re.fullmatch(r"\d+", mg[0][2][3]) is not None
        and mg[0][2][4] != "", repr(mg[:1]))
    zg = [c for c in copies if c[1] == "zzgone"]
    row("U7b: the locked verb's copy keeps the mark: its field 1 is `V [locked]`", len(zg) == 1 and zg[0][2][5] == "V [locked]", repr(zg))
    al = audit_lines(a0)
    vu = [ln for ln in al if "voc update account=zzvra " in ln]
    row("U8: one audit line, in lower case words: voc update account=zzvra removed=6 differs=2 locked=1 ids=...",
        len(vu) == 1 and re.search(r"voc update account=zzvra removed=6 differs=2 locked=1 ids=\S*margin", vu[0]) is not None
        and not re.search(r"VOC|REMOVED|ACCOUNT=", vu[0]), repr(vu))
    a1, s1 = audit_off(), len(saved_copies())
    n1 = len([c for c in saved_copies() if c[0] == "zzvra"])
    walk2 = g.adm(["UPDATE.ACCOUNTS ALL"])                     # the lock on zzvrd is gone: this walk updates it too
    out = segment(walk2, "zzvra")
    row("U9: a second walk removes nothing from zzvra and saves nothing (the VOC is as the first left it, no removal line, no new copy)",
        out != [] and readback("zzvra") == post and len([c for c in saved_copies() if c[0] == "zzvra"]) == n1 and not g.has(out, r"VOC record\(s\) removed")
        and not g.has(out, r"locked verb"), "\n".join(out))
    vu2 = [ln for ln in audit_lines(a1) if "voc update account=zzvra" in ln]
    row("U9b: ... and the audit line, which is written while something is kept, says removed=0", len(vu2) == 1 and "removed=0 differs=2 locked=1" in vu2[0], repr(vu2))

    # --- C. the control ---------------------------------------------------------------------------------------------
    say("\n--- C. an account with none of the listed names -----------------------------------------------------------------")
    out = segment(walk_out, "zzvrc")
    row("C1: the same walk left zzvrc as it was, saved nothing for it, audited nothing for it, and said nothing about the list",
        out != [] and readback("zzvrc") == cb and not [c for c in sv1 if c[0] == "zzvrc"] and not [ln for ln in au1 if "voc update account=zzvrc" in ln]
        and not g.has(out, r"VOC record\(s\)") and not g.has(out, r"locked verb"), "\n".join(out))

    # --- W. the second account of the same walk -----------------------------------------------------------------------
    say("\n--- W. the same walk, the account zzvrb ---------------------------------------------------------------------------------")
    wb = readback("zzvrb")
    row("W1: zzvrb: the same records gone and the same kept as in zzvra", {i: wb[i] for i in PLANTS} == {i: post[i] for i in PLANTS}, repr(wb))
    cp = sorted(c[1] for c in sv1 if c[0] == "zzvrb")
    row("W2: its copies carry the register name (zzvrb), not the administrator's; none was saved twice", cp == sorted(REMOVED), repr(cp))
    vu = [ln for ln in au1 if "voc update account=zzvrb" in ln]
    row("W3: and its audit line names it", len(vu) == 1 and "removed=6 differs=2 locked=1" in vu[0], repr(vu))
    row("W5: zzvra gained no second set of copies from the second walk", sorted(c[1] for c in saved_copies() if c[0] == "zzvra") == sorted(REMOVED))

    # --- D. a VOC that cannot be written (the walk of section U had it read only) ----------------------------------------
    say("\n--- D. a VOC the session may not write -------------------------------------------------------------------------------")
    out = segment(walk_out, "zzvrd")
    row("D1: nothing was removed from it (every planted record is still there)", all(dd[i][0] == "present" for i in PLANTS), repr({i: dd[i][0] for i in PLANTS}))
    row("D2: the walk says it could not write it (11983) and does not say it removed anything",
        out != [] and g.has(out, r"this session cannot write the VOC of that account") and not g.has(out, r"VOC record\(s\) removed"), "\n".join(out))
    row("D3: and no audit line says it removed anything", not [ln for ln in au1 if "voc update account=zzvrd" in ln and "removed=0" not in ln], repr([ln for ln in au1 if "zzvrd" in ln]))
    dd2 = readback("zzvrd")
    row("D4: once it can be written again the next walk updates it like the others (the same records gone, the same kept)",
        {i: dd2[i] for i in PLANTS} == {i: post[i] for i in PLANTS}, repr(dd2))

    # --- R. putting a record back ----------------------------------------------------------------------------------------
    say("\n--- R. RESTORE.VOC --------------------------------------------------------------------------------------------------")
    a0 = audit_off()
    out = g.adm(["RESTORE.VOC zzvra margin"])
    rb = readback("zzvra")
    row("R1: a removed record is put back as it was (K, 42), and the verb says so",
        rb["margin"] == ("present", "K", "42") and g.has(out, r"^Put back margin in the VOC of zzvra\."), "\n".join(out) + repr(rb["margin"]))
    row("R2: the audit trail has the line: voc restore account=zzvra id=margin", [ln for ln in audit_lines(a0) if re.search(r"voc restore account=zzvra id=margin\b", ln)] != [], repr(audit_lines(a0)))
    out = g.adm(["RESTORE.VOC zzvra margin"])
    row("R3: a second restore does not overwrite (11918) and the record is as it was", g.has(out, r"^The VOC of zzvra already holds a record margin: it was not overwritten\.")
        and readback("zzvra")["margin"] == ("present", "K", "42"), "\n".join(out))
    out = g.adm(["RESTORE.VOC zzvra evaluate"])
    row("R4: an id with no saved copy is said so (11916) and nothing is written", g.has(out, r"^No saved copy of evaluate for account zzvra\.")
        and readback("zzvra")["evaluate"][0] == "absent", "\n".join(out))
    out = g.adm(["RESTORE.VOC zzvra all"])
    rb = readback("zzvra")
    row("R5: `all` puts back every other removed record (stats, col.spcs, ><, both verbs); supp, calculate and only are as they were",
        all(rb[i][0] == "present" for i in REMOVED) and rb["zzgone"][1] == "V [locked]" and rb["supp"] == post["supp"] and rb["calculate"] == post["calculate"],
        "\n".join(out) + repr({i: rb[i] for i in REMOVED}))
    out = g.adm(["RESTORE.VOC nosuchacct all"])
    row("R6: an account that is not registered is refused (11912)", g.has(out, r"^Account nosuchacct is not registered\."), "\n".join(out))
    out = g.adm(["RESTORE.VOC"])
    row("R7: no arguments prints the format (11914)", g.has(out, r"^Format: restore\.voc account id \| restore\.voc account all"), "\n".join(out))
    pre2 = readback("zzvrb")
    out = g.plain("zzvrb", ["RESTORE.VOC zzvrb margin"])
    row("R8: an ordinary account has no such verb, and nothing was put back", not g.has(out, r"^Put back") and readback("zzvrb") == pre2, "\n".join(out))
    time.sleep(1.5)       # a saved copy's key ends in the second, and this whole suite runs inside one: a second removal of the same record in the same second would overwrite the first copy
    out = g.adm(["UPDATE.ACCOUNTS ALL"])
    row("R9: after a restore the next update removes the record again (the list, not the restore, has the last word), with a new copy",
        readback("zzvra")["margin"][0] == "absent" and len([c for c in saved_copies() if c[0] == "zzvra" and c[1] == "margin"]) >= 2, "\n".join(out[-5:]))

    say("\nsandbox-vocremoved: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
