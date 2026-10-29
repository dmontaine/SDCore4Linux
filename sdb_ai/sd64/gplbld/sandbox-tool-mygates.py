#!/usr/bin/env python3
#
# sandbox-tool-mygates.py - TOOL.GATES for an ACCOUNT HOLDER: the read-only "what my account may do and why" page ($tool_mygates, S.75 A2, the user audience of plan section 12),
# driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-mygates.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand (every field): zzmg1, every register gate off, and zzmg2, sh, sd, voc and net on, os off and the right to
# read the shared account withdrawn.  An ORDINARY session of each (sd -a<account>, as the sandbox user, not an administrator - the first row proves it) types TOOL.GATES.  The route
# groups are Linux groups, which a sandbox cannot change: $tool_mygates asks '!is_grp_member' for the person's login name, and the sandbox's copy of the page asks a copy of that
# program that reads a SCRATCH group file (the same stand-in as sandbox-tool-gates.py), where the sandbox user is in sdssh and sdfiles.
#
# THE INSTRUMENT.  A row that says "nothing changed" is judged by the DISK: the register records, the scratch group file and the audit file, before and after.
#
#   M1      the holder's page is a different page from the administrator's: the verb TOOL.GATES in an ordinary account draws "What this account may do", not the matrix
#   M2-M3   the sixteen gates in the table's order with the right state for the session: register gates from what the session holds, route gates from the groups
#   M4      the line that says who is signed on, in which account, and how many gates are on
#   M5      the row under the cursor in words: a gate that is off ("You cannot", the word the administrator would use), one that is on ("You can", the withdrawing word), a planned gate
#   M6      THE PAGE CHANGES NOTHING: Enter, R, Space, A, T, U and a click on a row queue and run nothing; every record, the group file and the audit trail are as they were
#   M7      what the session holds is not what the register says now: the register is changed under a running page, F5 keeps what the session holds (the edit gates are read at sign-on);
#           a group change shows at once; a NEW session shows the register
#   M8      the administrator's TOOL.GATES in the same sandbox is the matrix
#   M9      a VOC entry that points at the administrator's page in an ordinary account is refused before anything is drawn
#   M10     the [?] and F1 reach the help box; a window under 140 by 43 gets no page
import importlib.util
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_mygates", "sandbox-home.py")
fg = _load("sandbox_filesgrp_for_mygates", "sandbox-filesgrp.py")
q3 = fg.q3
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = fg.ME
FAILED_IDS = []
A1, A2 = "zzmg1", "zzmg2"


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


MUTANTS = {
    # name: (old text of the sandbox's tool_mygates, new text, the row ids that must fail and no others)
    "sh-and-os-swapped": ("         case gid = 'sh'\n            s = (if kernel(K$SH, -1) then 1 else 0)\n         case gid = 'os'\n            s = (if kernel(K$OS.EXEC, -1) then 1 else 0)",
                          "         case gid = 'sh'\n            s = (if kernel(K$OS.EXEC, -1) then 1 else 0)\n         case gid = 'os'\n            s = (if kernel(K$SH, -1) then 1 else 0)", ["M3"]),
    "route-by-account-name": ("s = (if is_grp_member(@logname, ggrp<k>) then 1 else 0)", "s = (if is_grp_member(@who, ggrp<k>) then 1 else 0)", ["M2", "M3", "M4", "M5", "M7"]),
}


def box():
    return sh.BOX


def st(h):
    return h.line(40)


def groups_text():
    with open(os.path.join(box(), "grp", "group"), "rb") as f:
        return f.read()


def write_groups(ssh=(), files=(), ai=()):
    lines = ["root:x:0:", fg.grp_line("sdusers", 2000, [ME]), fg.grp_line("sdssh", 2010, list(ssh)), fg.grp_line("sdapi", 2011, []), fg.grp_line("sdfiles", 2001, list(files)),
             fg.grp_line("sdfileswrite", 2002, []), fg.grp_line("sdfilesadmin", 2003, []), fg.grp_line("sdaiusers", 2004, list(ai)), fg.grp_line("wheel", 10, [])]
    g.put(os.path.join(box(), "grp", "group"), "\n".join(lines))


def reg_record(name, sh_="no", os_="no", sd="no", voc="no", bp="no", dict_="no", srd="", swr="", net="no"):
    return [os.path.join(box(), "user_accounts", name), "", "sdu_" + ME, "", "", "", sh_, os_, sd, voc, bp, dict_, srd, swr, net, "", "", ""]


def gate_titles():
    """[(id, title, status)] from the sandbox's own gate table, in its order."""
    src = open(os.path.join(sh.SYS, "gpl.bp", "tk_gate_info"), encoding="utf-8", errors="replace").read()
    out = []
    for r in re.findall(r'rows<-1> = "([^"]*)"', src):
        f = r.split("|")
        out.append((f[0], f[1], f[14]))
    return out


def setup_mygates():
    b = box()
    q3.BOX, q3.SYS, q3.SD = b, sh.SYS, os.path.join(sh.SYS, "bin", "sd")
    os.makedirs(os.path.join(b, "grp"), exist_ok=True)
    write_groups(ssh=[ME], files=[ME])
    # the stand-in for !is_grp_member that reads the scratch group file (sandbox-filesgrp.py's copy, under another catalogue name)
    t = open(os.path.join(TREE, "sdsys", "gpl.bp", "is_grp_member"), encoding="utf-8", errors="replace").read()
    if t.count('openpath "/etc" to etc then') != 1 or t.count("$catalog !is_grp_member") != 1 or t.count("function is_grp_member(") != 1:
        bail("the tree's is_grp_member is not in the shape this suite patches")
    t = t.replace('openpath "/etc" to etc then', 'openpath "%s" to etc then' % os.path.join(b, "grp")).replace("$catalog !is_grp_member", "$catalog !zzgm").replace("function is_grp_member(", "function zzgm(")
    g.put(os.path.join(sh.SYS, "gpl.bp", "zzgm"), t)
    out = q3.adm(["BASIC gpl.bp zzgm"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the group lookup stand-in did not compile:\n" + "\n".join(out[-6:]))
    page = open(os.path.join(TREE, "sdsys", "gpl.bp", "tool_mygates"), encoding="utf-8", errors="replace").read()
    old = "deffun is_grp_member(user,group) calling '!is_grp_member'"
    if page.count(old) != 1:
        bail("the tree's tool_mygates has its group lookup %d times, not once" % page.count(old))
    g.put(os.path.join(sh.SYS, "gpl.bp", "tool_mygates"), page.replace(old, "deffun is_grp_member(user,group) calling '!zzgm'"))
    compile_page()
    for a in (A1, A2):
        g.FIXTURES[a] = ("no", "no")
        g.build_account(a)
    g.reg_write(A1, reg_record(A1))
    g.reg_write(A2, reg_record(A2, sh_="yes", os_="no", sd="yes", voc="yes", net="yes", srd="no"))      # sh ON and os off: a swap of the two keys is seen


def compile_page():
    out = q3.adm(["BASIC gpl.bp tool_mygates"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_mygates did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def mutate(name):
    old, new, _kills = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_mygates")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    compile_page()


def page(account, cols=140, rows=43):
    h = H(account=account, cols=cols, rows=rows)
    h.typed("tool.gates\r", idle=3.5)
    return h


def table(h):
    """{gate title: (now, delivered, beyond, when)} from the rows on the screen."""
    out = {}
    for n in range(3, 19):
        l = h.line(n)
        title = l[3:27].strip()
        if title:
            out[title] = (l[27:33].strip(), l[33:47].strip(), l[47:58].strip(), l[58:136].strip())
    return out


def boxb(h):
    return [h.line(n)[3:138].rstrip() for n in range(23, 33)]


def snapshot():
    snap = {a: open(os.path.join(sh.SYS, "accounts", a), "rb").read() for a in (A1, A2)}
    snap["group"] = groups_text()
    try:
        snap["audit"] = os.path.getsize(os.path.join(sh.SYS, "audit"))
    except OSError:
        snap["audit"] = 0
    return snap


def expected(register_on, route_on):
    """{title: now} for the sixteen gates: register_on is the set of register gate ids that are on, route_on the set of route gate ids that are on."""
    out = {}
    for gid, title, status in gate_titles():
        if status != "built":
            out[title] = "plan"
        elif gid in ("ssh", "api", "files", "files-write", "files-admin", "ai"):
            out[title] = "ON" if gid in route_on else "off"
        else:
            out[title] = "ON" if gid in register_on else "off"
    return out


def section_page():
    say("\n--- the holder's page")
    a0 = fg.audit_off()
    h = page(A1)
    T = h.text()
    if "What this account may do" not in T:
        dump(h)
        bail("tool.gates never drew the holder's page in an ordinary account, so no row below can be believed")
    arow("M1", "TOOL.GATES in an ordinary account draws the holder's page (not the matrix), for the audience %s@%s, and it writes no audit line" % (ME, A1),
         "Gates by account" not in T and "The row under the cursor" in T and "Where this comes from" in T and re.search(r"tool\.gates\s+%s@%s" % (re.escape(ME), A1), h.line(0)) is not None
         and "tool start" not in (fg.audit_new(a0) or ""), repr((h.line(0)[100:], fg.audit_new(a0))))
    tb = table(h)
    titles = [t for _g, t, _s in gate_titles()]
    arow("M2", "the sixteen gates, in the table's order, for an account with every register gate off: shared-read ON as delivered, ssh and files ON from the groups, sockets plan",
         list(tb) == titles and {k: v[0] for k, v in tb.items()} == expected({"shared-read"}, {"ssh", "files"}), repr({k: v[0] for k, v in tb.items()}))
    arow("M2b", "each row says how the gate is delivered and whether it reaches beyond SD, from the table", tb[titles[2]][1] == "off" and tb[titles[2]][2] == "yes" and tb[titles[5]][2] == "no" and tb[titles[9]][1] == "on",
         repr((tb[titles[2]], tb[titles[5]], tb[titles[9]])))
    L19 = h.line(19)[3:138].rstrip()
    arow("M4", "the line that says who is signed on, in which account, and how many gates are on for the session", L19.startswith("Signed on as %s in the account %s.  3 of 16 gates are on" % (ME, A1)), repr(L19))
    B = boxb(h)
    arow("M5a", "the first row (ssh, ON for the person): 'ON for you', what it lets you do, what you still can, the withdrawing word, and that it is about you as a person",
         "Remote terminal [ssh]" in B[0] and "ON for you.  You can sign in to SD over ssh" in B[0] and any("modify.account %s none" % A1 in x for x in B) and any("membership of the Linux group sdssh by your login name, %s" % ME in x for x in B), repr(B[:6]))
    h.key("down")
    h.key("down")
    B = boxb(h)
    arow("M5b", "the third row (sh, off): 'off for you', 'You cannot', the giving word, and the sentence that it reaches beyond SD",
         "[sh]" in B[0] and "off for you.  You cannot" in B[0] and any("modify.account %s sh-on" % A1 in x and "reaches beyond SD" in x for x in B), repr(B[:5]))
    for _ in range(3):
        h.key("down")
    B = boxb(h)
    arow("M5c", "the sixth row (voc, off): the sign-on sentence for the edit gates", "[voc]" in B[0] and any("read ONCE when you sign on" in x for x in B), repr(B))
    h.key("end")
    B = boxb(h)
    arow("M5d", "the last row is sockets, planned: 'planned and not built yet', nothing to switch", "planned and not built yet" in B[0] and table(h)["Raw sockets"][0] == "plan" if "Raw sockets" in table(h) else "planned and not built yet" in B[0], repr(B[:2]))
    h.key("ctrl-q", idle=1.2)
    h.end()

    h = page(A2)
    tb = table(h)
    arow("M3", "an account with sh, sd, voc and net on, os off and shared-read withdrawn: exactly those are ON in the session (what the session holds), and the route gates are the same person's",
         {k: v[0] for k, v in tb.items()} == expected({"sh", "sd", "voc", "net"}, {"ssh", "files"}), repr({k: v[0] for k, v in tb.items()}))
    L19 = h.line(19)[3:138].rstrip()
    arow("M4b", "...and the count says 6 of 16", "6 of 16 gates are on" in L19, repr(L19))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_readonly():
    say("\n--- M6: the page changes nothing")
    h = page(A1)
    snap = snapshot()
    for k in ("enter", "right", "left", "tab", "bs"):
        h.key(k, idle=0.5)
    for c in "rtuaq p?":
        h.typed(c, idle=0.5)
        if "Help is not installed" in h.text() or "No help has been written" in h.text():
            h.key("esc", idle=0.8)
    h.key("enter", idle=0.6)
    h.click(40, 5)
    h.click(40, 8)
    h.key("esc", idle=0.8)                      # S.88 F0a: Esc opens the menu bar on this page, and the next Esc closes it again (the drop-down covers the box title)
    h.key("esc", idle=0.8)
    cells = {k: v[0] for k, v in table(h).items()}
    arow("M6", "Enter, the arrows, R, T, U, A, Q, P, space, a click on a row: no record, no group line and no audit line changed, and every gate still says what it said",
         snapshot() == snap and cells == expected({"shared-read"}, {"ssh", "files"}), repr((snapshot() == snap, cells)))
    arow("M6b", "the page still has no command in it that could: it is still on the screen and the status line is the page's own", "What this account may do" in h.text() and st(h).startswith("[My gates]"), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_session():
    say("\n--- M7: what the session holds is not what the register says now")
    h = page(A2)
    rec = g.reg_read(A2)
    rec[10 - 1] = "no"                           # voc
    rec[7 - 1] = "no"                            # sh
    g.put(os.path.join(sh.SYS, "accounts", A2), "\n".join(rec[:18]) + "\n")
    write_groups(ssh=[], files=[ME], ai=[ME])    # the person leaves sdssh and joins sdaiusers
    h.key("f5", idle=2.0)
    tb = {k: v[0] for k, v in table(h).items()}
    titles = {gid: t for gid, t, _s in gate_titles()}
    arow("M7a", "the register says voc and sh are off now, and the open session still holds them (sh and voc ON): the register is not what this page reports", tb[titles["voc"]] == "ON" and tb[titles["sh"]] == "ON", repr((tb[titles["voc"]], tb[titles["sh"]])))
    arow("M7b", "a route group is read from the system each time: after F5 ssh is off and ai is ON", tb[titles["ssh"]] == "off" and tb[titles["ai"]] == "ON", repr((tb[titles["ssh"]], tb[titles["ai"]])))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2)
    tb = {k: v[0] for k, v in table(h).items()}
    arow("M7c", "a NEW session shows the register: voc and sh are off", tb[titles["voc"]] == "off" and tb[titles["sh"]] == "off" and tb[titles["sd"]] == "ON", repr((tb[titles["voc"]], tb[titles["sh"]], tb[titles["sd"]])))
    h.key("ctrl-q", idle=1.2)
    h.end()
    write_groups(ssh=[ME], files=[ME])


def section_other():
    say("\n--- M8-M10: the administrator's page, the bypass, help and a small window")
    h = H(admin=True)
    h.typed("tool.gates\r", idle=3.5)
    T = h.text()
    arow("M8", "the administrator's TOOL.GATES in the same sandbox is the matrix", "Gates by account" in T and "What this account may do" not in T, T[:200])
    h.key("ctrl-q", idle=1.2)
    h.end()
    # a VOC entry of the account that points at the administrator's page: the page refuses before it draws anything
    vocdir = os.path.join(box(), "user_accounts", A1)
    g.put(os.path.join(sh.SYS, "bp", "zzmgvoc"), "\n".join(["$internal", "   openpath '%s/voc' to v else crt 'MGV no voc' ; stop" % vocdir,
                                                           "   write 'V':@fm:'CA':@fm:'$tool_gates' to v, 'mgx'", "   crt 'MGV done'", "end", ""]))
    out = adm("BASIC bp zzmgvoc", "RUN bp zzmgvoc")
    ok = has(out, r"^MGV done$")
    if ok:
        out = g.plain(A1, ["mgx"])
        arow("M9", "a VOC entry in an ordinary account that points at the administrator's page is refused before anything is drawn (the page asks the kernel itself)",
             has(out, r"requires the administrator|administrator") and not has(out, r"Gates by account"), repr(out[-4:]))
    else:
        arow("M9", "the bypass fixture was written", False, repr(out[-4:]))
    h = page(A1)
    arow("M10a", "a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    h.click(135, 2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("M10b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("M10c", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    h.typed("tool.gates\r", idle=3.0)
    T = h.text()
    arow("M10d", "a window under 140 by 43 gets no page", "What this account may do" not in T and "The row under the cursor" not in T, T[-300:])
    h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-mygates.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    try:
        sh.setup("sandbox-tool-mygates.py")
        setup_mygates()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-mygates: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        section_page()
        if mutant is None:
            section_readonly()
        if mutant in (None, "route-by-account-name"):
            section_session()
        if mutant is None:
            section_other()
    finally:
        sh.teardown()
    say("\nsandbox-tool-mygates: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"M\d+", i).group(0) for i in FAILED_IDS if re.match(r"M\d+", i)})
        ok = want == got
        say("sandbox-tool-mygates: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
