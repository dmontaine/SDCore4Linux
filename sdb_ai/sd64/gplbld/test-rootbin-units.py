#!/usr/bin/env python3
# test-rootbin-units.py - W.11 F11 (security-model evaluation, 26 Oct 2026): root executes files that the sdsys user owns.  sd.service, sd-lnxd.service and
# sdclient@.service run bin/sd and bin/sdlnxd as root, sd-elevate's akpath-set runs bin/sdidx as root and every session reads bin/pcode; the installer's
# "chown -R sdsys:sdusers" made all of them the sdsys user's, so whoever held that login could have root run its code at the next start.  The installer's ROOTBIN
# block makes bin root's (and immutable).  FREE CHECK: no install, no sudo, no sd; the sources are read as text.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-rootbin-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-rootbin-units.py --selftest      (mutants of the installer, the remover, the units, the helpers, the kernel and the Makefile)
#
# WHAT IT COMPUTES.  THE SET OF FILES ROOT RUNS OR LOADS FROM THE SYSTEM DIRECTORY is read from the sources, not listed here:
#   units      every Exec* line (ExecStart, ExecStartPre, ExecStartPost, ExecStop, ExecStopPost, ExecReload, ExecCondition) of every .service and .socket in
#              usr/lib/systemd/system whose unit has no User= (or User=root); a path under /usr/local/sdsys must be bin/<one name>
#   helpers    every /usr/local/sdsys/bin/<name> (also as $SD_SYS_ROOT_REAL, $SD_SYS_ROOT or $sdsysdir) in sd-elevate, sd-accarchive, ssh-forcecommand.sh, reconcile-accounts.sh,
#              sd-ai and sd-ai-ctl, which are root-owned programs that root runs
#   kernel     every "%s/bin/<name>" or "%s%cbin%c<name>" in sysseg.c (starts sdlnxd and the start-up process), sdlnxd.c (execs sd -cleanup), op_kernel.c (a phantom) and sd.c
#              (reads bin/pcode), comments taken out
#   installer  every ${sdsysdir}/bin/<name> in installsdcore.sh and deletesdcore.sh (they run sd as root)
# and compares the union with rootbin_files in the ROOTBIN block: they must be EQUAL, so a new root-run file cannot be forgotten and a name that nothing runs is not kept.
#
# CHECKS (the first word of each row is its id; --selftest names the id each mutant must fail)
#   U1  every unit's Exec* path under /usr/local/sdsys is bin/<name>; a unit that is not root's has none under it at all
#   U2  every path a unit runs OUTSIDE /usr/local/sdsys is installed by the installer with -o root -g root; the same for the sudoers drop-in's commands (and none of them is under the system directory)
#   L1  root loads no library from the tree: the Makefile has no rpath/RUNPATH/$ORIGIN, the units set no LD_LIBRARY_PATH/LD_PRELOAD/Environment, the installer adds no ld.so path, and dlopen is
#       called only in op_ccall.c (CCALL, a per-account gate)
#   B1  ONE ROOTBIN block, its markers in order, and rootbin="$sdsysdir/bin"
#   B2  its place: after the recursive chown to sdsys, the pcode build, the pack copy, the stamp and EVERY bootstrap or compile command that writes under the tree (the last of them is
#       printed), and before the passwords.  (The stamp is written at the top of the install, before the bootstrap passes, so the block cannot come before it and after the compiles.)
#   B3  after the block nothing writes under bin or re-owns the system directory
#   B4  rootbin_files equals the computed set
#   B5  the block's commands: chown only -R root:root on bin, chmod only -R go-w, chattr only -i/+i on bin, no sdsys/sdusers, no numeric mode
#   B6  its guards, in order: a link or a missing bin is refused before anything is changed; entries that are not plain files are refused before the chown; the attribute is lifted before
#       the chown and set after the chmod; the verdict reads lsattr and the success line needs the owner/mode check, the missing-file check and the attribute
#   B7  the closing summary: rootbin_sealed starts 0, is set to 1 once on the success path only, and the summary after the block says NOT sealed when it is not 1
#   D1  deletesdcore.sh lifts the attribute (chattr -i on bin) once, after the services are stopped and before the removal of the system directory, and sets no attribute itself
#   D2  the upgrade path is unchanged: an upgrade is a delete (accounts kept) and a fresh install, so the installer still refuses to run over an install and copies bin and chowns
#       before the block; the block never meets a bin it sealed earlier
#   D3  the drop-in grants sdsys nothing but the helper (the helper is outside the tree)
# B2 and B3 know a bootstrap, compile or write by its COMMAND SHAPE (the anchors in B2, the verbs and the bin path in B3): a later install step of another shape, say
# `sudo python3 x.py "$sdsysdir"` after the block, would pass unseen.  B4 is the strong check; B2 and B3 are a tripwire.
# WHAT IT CANNOT SAY: who owns what on a real machine, whether chattr +i holds on that file system, whether sdsys can still rename bin: witness-f11.py on a real install.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(SD64, "..", ".."))
SYSDIR = "/usr/local/sdsys"
passed = failed = 0


def env(name, default):
    return os.environ.get(name, default)


INST = env("INSTALLER", os.path.join(ROOT, "installsdcore.sh"))
DELETER = env("DELETER", os.path.join(ROOT, "deletesdcore.sh"))
UNITDIR = env("UNITDIR", os.path.join(SD64, "usr", "lib", "systemd", "system"))
HELPERDIR = env("HELPER_DIR", HERE)
GPLSRC = env("GPLSRC", os.path.join(SD64, "gplsrc"))
SYSSEG_C = env("SYSSEG_C", os.path.join(SD64, "gplsrc", "sysseg.c"))
SDLNXD_C = env("SDLNXD_C", os.path.join(SD64, "gplsrc", "sdlnxd.c"))
OPKERNEL_C = env("OPKERNEL_C", os.path.join(SD64, "gplsrc", "op_kernel.c"))
SD_C = env("SD_C", os.path.join(SD64, "gplsrc", "sd.c"))
MAKEFILE = env("MAKEFILE", os.path.join(SD64, "Makefile"))
HELPERS = ["sd-elevate", "sd-accarchive", "ssh-forcecommand.sh", "reconcile-accounts.sh", "sd-ai", "sd-ai-ctl"]
SUDOERS = "sdcore.sudoers"


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def read(p):
    return open(p, encoding="latin-1").read()


def strip_c_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def code_lines(text):
    """(index, line) of every line that is not a whole-line shell comment"""
    return [(i, l) for i, l in enumerate(text.split("\n")) if not l.lstrip().startswith("#")]


# ---- what the units run -------------------------------------------------------------------------------------------------------------------------------------
EXEC_KEYS = ("ExecStart", "ExecStartPre", "ExecStartPost", "ExecStop", "ExecStopPost", "ExecReload", "ExecCondition")


def parse_units(unitdir):
    units = {}
    for fn in sorted(os.listdir(unitdir)):
        if not fn.endswith((".service", ".socket")):
            continue
        u = {"user": None, "exec": [], "env": [], "text": ""}
        text = read(os.path.join(unitdir, fn))
        u["text"] = text
        for line in text.split("\n"):
            s = line.strip()
            if not s or s[0] in "#;[":
                continue
            k, _, v = s.partition("=")
            k = k.strip()
            v = v.strip()
            if k == "User":
                u["user"] = v
            elif k in EXEC_KEYS and v:
                path = v.lstrip("-@+!:").split()
                if path:
                    u["exec"].append((k, path[0]))
            elif k in ("Environment", "EnvironmentFile", "PassEnvironment", "UnsetEnvironment"):
                u["env"].append(s)
        units[fn] = u
    return units


def root_run(u):
    return u["user"] in (None, "", "root")


def bin_names_in(text, comments="shell"):
    """names after <sysdir>/bin/ in the text, with the spellings the sources use for the system directory"""
    pat = re.compile(r"(?:/usr/local/sdsys|\$\{?SD_SYS_ROOT(?:_REAL)?\}?|\$\{?SDSYS\}?|\$\{?sdsysdir\}?)/bin/([A-Za-z0-9_.-]+)")
    names = set()
    if comments == "shell":
        for _, l in code_lines(text):
            names.update(pat.findall(l))
    else:
        names.update(pat.findall(text))
    return names


def compute(units):
    """the root-run set {name: [sources]} and the faults found on the way"""
    found = {}
    faults = []

    def add(name, src):
        found.setdefault(name, []).append(src)

    for fn, u in units.items():
        for key, path in u["exec"]:
            if path.startswith(SYSDIR + "/"):
                rest = path[len(SYSDIR) + 1:]
                m = re.fullmatch(r"bin/([A-Za-z0-9_.-]+)", rest)
                if not m:
                    faults.append("%s %s=%s is under the system directory but not bin/<name>" % (fn, key, path))
                elif not root_run(u):
                    faults.append("%s runs as %s but %s=%s is under the system directory" % (fn, u["user"], key, path))
                else:
                    add(m.group(1), "%s %s" % (fn, key))
    for h in HELPERS:
        p = os.path.join(HELPERDIR, h)
        if os.path.exists(p):
            for n in bin_names_in(read(p)):
                add(n, h)
    for label, p in (("sysseg.c", SYSSEG_C), ("sdlnxd.c", SDLNXD_C), ("op_kernel.c", OPKERNEL_C), ("sd.c", SD_C)):
        t = strip_c_comments(read(p))
        for n in re.findall(r'"%s/bin/([A-Za-z0-9_.-]+)"', t) + re.findall(r'"%s%cbin%c([A-Za-z0-9_.-]+)"', t):
            add(n, label)
    for label, p in (("installsdcore.sh", INST), ("deletesdcore.sh", DELETER)):
        for n in bin_names_in(read(p)):
            add(n, label)
    return found, faults


def block_of(inst):
    ms = re.findall(r"^# ROOTBIN-BEGIN\n(.*?)^# ROOTBIN-END$", inst, re.S | re.M)
    return ms


def install_dests(inst):
    """destinations of 'install -o root -g root -m NNNN src dest' lines"""
    dests = set()
    for _, l in code_lines(inst):
        m = re.search(r"\binstall\s+-o root -g root -m 0?\d+\s+(\S+)\s+(\S+)", l)
        if m:
            dests.add(m.group(2).strip("'\""))
    return dests


def run():
    inst = read(INST)
    deleter = read(DELETER)
    units = parse_units(UNITDIR)
    found, faults = compute(units)
    root_units = sorted(f for f, u in units.items() if root_run(u))
    if not units or not root_units or "sd" not in found or "sdlnxd" not in found:
        print("test-rootbin-units: CANNOT RUN - the units or the sources did not yield the root-run set (units %s, set %s)" % (sorted(units), sorted(found)))
        return 2
    print("units     : %s (root-run: %s)" % (", ".join(sorted(units)), ", ".join(root_units)))
    print("root-run  : " + "; ".join("bin/%s <- %s" % (n, ", ".join(sorted(set(s)))) for n, s in sorted(found.items())))

    # ---- U1 -----------------------------------------------------------------------------------------------------------------------------------------------
    row("U1 every Exec* path of every unit under %s is bin/<name> (and none of a unit that is not root's)" % SYSDIR, not faults, "; ".join(faults))

    # ---- U2 -----------------------------------------------------------------------------------------------------------------------------------------------
    dests = install_dests(inst)
    outside = []
    for fn, u in units.items():
        for key, path in u["exec"]:
            if not path.startswith(SYSDIR + "/"):
                outside.append((fn, path))
    missing = [p for fn, p in outside if p not in dests]
    row("U2 every path a unit runs outside the system directory (%s) is installed with -o root -g root by the installer"
        % ", ".join(sorted(set(p for _, p in outside))), bool(outside) and not missing, "not installed root:root: %s" % missing if missing else "no unit path outside the tree was found")
    sud = read(os.path.join(HELPERDIR, SUDOERS))
    cmds = []
    for l in sud.split("\n"):
        if l.lstrip().startswith("#") or "NOPASSWD:" not in l:
            continue
        for c in l.split("NOPASSWD:", 1)[1].split(","):
            cmds.append(c.strip().split()[0])
    bad = [c for c in cmds if c.startswith(SYSDIR) or c not in dests]
    row("U2 and every command the sudoers drop-in names is outside the system directory and installed -o root -g root (%s)" % ", ".join(sorted(set(cmds))), bool(cmds) and not bad, "bad: %s" % bad)

    # ---- L1 -----------------------------------------------------------------------------------------------------------------------------------------------
    mk = read(MAKEFILE)
    mkbad = [l.strip() for _, l in code_lines(mk) if re.search(r"rpath|RUNPATH|RUN_PATH|\$ORIGIN|-Wl,-R\b|LD_RUN_PATH", l)]
    envbad = [fn for fn, u in units.items() if u["env"] or re.search(r"LD_LIBRARY_PATH|LD_PRELOAD", u["text"])]
    ldbad = [l.strip() for _, l in code_lines(inst) if re.search(r"ld\.so\.conf|ldconfig|LD_LIBRARY_PATH|LD_PRELOAD", l)]
    dl = []
    for fn in sorted(os.listdir(GPLSRC)):
        if fn.endswith((".c", ".h")):
            if re.search(r"\bdlopen\s*\(", strip_c_comments(read(os.path.join(GPLSRC, fn)))):
                dl.append(fn)
    row("L1 root loads no library from the tree: no rpath in the Makefile %s, no library variable in a unit %s, no ld.so path in the installer %s, dlopen only in op_ccall.c (found in %s)"
        % (mkbad or "", envbad or "", ldbad or "", dl), not mkbad and not envbad and not ldbad and dl == ["op_ccall.c"], "")

    # ---- B1 -----------------------------------------------------------------------------------------------------------------------------------------------
    blocks = block_of(inst)
    nb = len(re.findall(r"^# ROOTBIN-BEGIN$", inst, re.M))
    ne = len(re.findall(r"^# ROOTBIN-END$", inst, re.M))
    row("B1 ONE ROOTBIN block (begin markers %d, end markers %d) and it sets rootbin=\"$sdsysdir/bin\"" % (nb, ne),
        nb == 1 and ne == 1 and len(blocks) == 1 and 'rootbin="$sdsysdir/bin"' in blocks[0], "")
    if len(blocks) != 1:
        print("test-rootbin-units: %d passed, %d failed" % (passed, failed))
        return 1
    block = blocks[0]

    # ---- B2 -----------------------------------------------------------------------------------------------------------------------------------------------
    lines = inst.split("\n")
    bi = lines.index("# ROOTBIN-BEGIN")
    ei = lines.index("# ROOTBIN-END")

    def first(pred):
        for i, l in code_lines(inst):
            if pred(l):
                return i
        return None

    chown_main = first(lambda l: l.strip() == 'sudo chown -R sdsys:sdusers "$sdsysdir"')
    pcode_i = first(lambda l: "gplbld/pcode_bld.py" in l)
    stamp_i = first(lambda l: 'sudo tee "$sdsysdir/.sdcore-install"' in l)
    pack_end = lines.index("# AGENTPACK-END") if "# AGENTPACK-END" in lines else None
    pw_i = first(lambda l: l.strip() == 'echo "PASSWORDS."')
    anchor_re = re.compile(r'-internal|THIRD\.COMPILE|SECOND\.COMPILE|write_install_dicts|bin/sd"? -i\b|UPDATE\.ACCOUNTS|sdtic')
    anchors = [i for i, l in code_lines(inst) if "sudo" in l and anchor_re.search(l) and not l.lstrip().startswith(("echo", "printf"))]
    anchors += [i for i, l in code_lines(inst) if l.strip() == "fix_gcat_modes"]
    last_anchor = max(anchors) if anchors else None
    before = [("the recursive chown to sdsys", chown_main), ("the pcode build", pcode_i), ("the stamp", stamp_i), ("the pack copy", pack_end)]
    nope = [n for n, i in before if i is None or i > bi]
    row("B2 the block (line %d) is after %s, and after the last bootstrap or compile command (line %s: %s), and before the passwords (line %s)"
        % (bi + 1, ", ".join("%s (%s)" % (n, (i + 1) if i is not None else "?") for n, i in before), (last_anchor + 1) if last_anchor is not None else "?",
           lines[last_anchor].strip()[:60] if last_anchor is not None else "none", (pw_i + 1) if pw_i is not None else "?"),
        not nope and last_anchor is not None and last_anchor < bi and pw_i is not None and bi < pw_i and len(anchors) >= 8,
        "wrong place: %s; anchors found %d, last %s; passwords %s" % (nope, len(anchors), last_anchor, pw_i))

    # ---- B3 -----------------------------------------------------------------------------------------------------------------------------------------------
    mut_re = re.compile(r"\b(cp|mv|rm|install|tee|touch|ln|chown|chmod|chattr|dd|truncate|rsync|mkdir)\b")
    bin_re = re.compile(r"(\$\{?sdsysdir\}?|/usr/local/sdsys)/bin\b")
    redir_re = re.compile(r">>?\s*\"?(\$\{?sdsysdir\}?|/usr/local/sdsys)/bin")
    root_re = re.compile(r"\b(chown|chmod|chattr)\b[^#\n]*\"\$\{?sdsysdir\}?\"")
    late = []
    for i, l in code_lines(inst):
        if i <= ei:
            continue
        if (bin_re.search(l) and mut_re.search(l)) or redir_re.search(l) or root_re.search(l):
            late.append("%d: %s" % (i + 1, l.strip()[:80]))
    row("B3 after the block nothing writes under bin or re-owns the system directory (%d lines checked)" % len([1 for i, _ in code_lines(inst) if i > ei]), not late, "; ".join(late))

    # ---- B4 -----------------------------------------------------------------------------------------------------------------------------------------------
    m = re.search(r"^rootbin_files=\(([^)]*)\)$", block, re.M)
    listed = set(m.group(1).split()) if m else None
    computed = set(found)
    row("B4 rootbin_files %s equals the computed root-run set %s" % (sorted(listed) if listed is not None else "(none)", sorted(computed)), listed == computed,
        "only in the block: %s; only computed: %s" % (sorted((listed or set()) - computed), sorted(computed - (listed or set()))))

    # ---- B5 -----------------------------------------------------------------------------------------------------------------------------------------------
    cmd = [l for _, l in code_lines(block) if not l.lstrip().startswith(("echo", "printf"))]
    chmods = [l.strip() for l in cmd if re.search(r"\bchmod\b", l)]
    chowns = [l.strip() for l in cmd if re.search(r"\bchown\b", l)]
    chattrs = [l.strip() for l in cmd if re.search(r"\bchattr\b", l)]
    names = [l.strip() for l in cmd if re.search(r"\b(sdsys|sdusers)\b", l.replace("$sdsysdir", ""))]
    ok5 = (chmods == ['sudo chmod -R go-w "$rootbin"'] and chowns == ['sudo chown -R root:root "$rootbin"']
           and sorted(chattrs) == ['if sudo chattr +i "$rootbin" 2>/dev/null; then', 'sudo chattr -i "$rootbin" 2>/dev/null || true'] and not names)
    row("B5 the block's commands are 'chown -R root:root', 'chmod -R go-w' and 'chattr -i/+i', all on bin, and none names sdsys or sdusers", ok5,
        "chmod %s; chown %s; chattr %s; names %s" % (chmods, chowns, chattrs, names))

    # ---- B6 -----------------------------------------------------------------------------------------------------------------------------------------------
    bl = block.split("\n")

    def at(pred):
        for i, l in enumerate(bl):
            if not l.lstrip().startswith("#") and pred(l):
                return i
        return None

    i_link = at(lambda l: l.strip() == 'if [ -L "$rootbin" ] || [ ! -d "$rootbin" ]; then')
    i_odd = at(lambda l: "sudo find \"$rootbin\" -mindepth 1 \\! -type f" in l)
    i_refuse = at(lambda l: l.strip() == 'if [ -n "$rootbin_odd" ]; then')
    i_lift = at(lambda l: l.strip() == 'sudo chattr -i "$rootbin" 2>/dev/null || true')
    i_chown = at(lambda l: l.strip() == 'sudo chown -R root:root "$rootbin"')
    i_chmod = at(lambda l: l.strip() == 'sudo chmod -R go-w "$rootbin"')
    i_set = at(lambda l: l.strip() == 'if sudo chattr +i "$rootbin" 2>/dev/null; then')
    i_ls = at(lambda l: "sudo lsattr -d \"$rootbin\"" in l)
    i_miss = at(lambda l: '[ -f "$rootbin/$f" ] || rootbin_miss=' in l)
    i_bad = at(lambda l: l.strip().startswith("rootbin_bad=$(sudo stat -c '%U:%G %A %n' \"$rootbin\" \"$rootbin\"/*"))
    i_ok = at(lambda l: l.strip() == 'if [ -z "$rootbin_bad" ] && [ -z "$rootbin_miss" ] && [ "$rootbin_imm" = yes ]; then')
    idx = [i_link, i_odd, i_refuse, i_lift, i_chown, i_chmod, i_set, i_ls, i_miss, i_bad, i_ok]
    inorder = all(x is not None for x in idx) and idx == sorted(idx)
    row("B6 the guards are all there and in this order: link/absent test, find of non-plain entries, the refusal, chattr -i, chown, chmod, chattr +i, lsattr, missing-file test, owner/mode check, success test",
        inorder, "lines in the block: %s" % idx)
    row("B6 and the attribute counts only when lsattr shows it (case *i*), the success line is printed only on that path and every other path says NOT",
        'case "$rootbin_flags" in *i*) rootbin_imm=yes ;; esac' in block and block.count("Root-run files are root's") == 1 and "NOT sealed" in block and "NOT all sealed" in block, "")

    # ---- B7 -----------------------------------------------------------------------------------------------------------------------------------------------
    i_flag0 = at(lambda l: l.strip() == "rootbin_sealed=0")
    i_flag1 = at(lambda l: l.strip() == "rootbin_sealed=1")
    seal_sets = [l for _, l in code_lines(block) if re.match(r"\s*rootbin_sealed=", l)]
    summ = [i for i, l in code_lines(inst) if i > ei and l.strip() == 'if [ "${rootbin_sealed:-0}" -ne 1 ]; then']
    summ_text = "\n".join(lines[summ[0]:summ[0] + 6]) if summ else ""
    row("B7 the closing summary repeats the warning when the block did not seal: rootbin_sealed starts 0 (line %s), is set to 1 once, on the success path only (%s, after the success test %s), "
        "and the summary after the block (line %s) prints NOT sealed when it is not 1" % (i_flag0, i_flag1, i_ok, summ and summ[0] + 1),
        i_flag0 is not None and i_flag1 is not None and i_ok is not None and i_ok < i_flag1 and len(seal_sets) == 2 and bl[i_flag1 - 1].lstrip().startswith("echo \"Root-run files are root's")
        and len(summ) == 1 and "NOT sealed" in summ_text,
        "sets %s; summary %s" % (seal_sets, summ))

    # ---- D1 -----------------------------------------------------------------------------------------------------------------------------------------------
    dl_ = deleter.split("\n")

    def dat(pred):
        return [i for i, l in code_lines(deleter) if pred(l)]

    lifts = dat(lambda l: l.strip() == 'sudo chattr -i "$sdsysdir/bin" 2>/dev/null || true')
    rms = dat(lambda l: l.strip() == 'sudo rm -fr "$sdsysdir"')
    stops = dat(lambda l: l.strip().startswith("sudo systemctl stop sd.service"))
    sets = dat(lambda l: re.search(r"chattr\s+\+", l) is not None)
    binmods = dat(lambda l: re.search(r"\b(chown|chmod)\b[^#\n]*\$sdsysdir/bin", l) is not None)
    row("D1 deletesdcore.sh lifts the attribute once (line %s), after the services are stopped (%s) and before the system directory is removed (%s), and sets none itself"
        % (lifts and lifts[0] + 1, stops and stops[0] + 1, rms and rms[0] + 1),
        len(lifts) == 1 and len(rms) == 1 and stops and stops[0] < lifts[0] < rms[0] and not sets and not binmods, "lifts %s, removals %s, stops %s, sets %s, bin modes %s" % (lifts, rms, stops, sets, binmods))

    # ---- D2 -----------------------------------------------------------------------------------------------------------------------------------------------
    guard = first(lambda l: l.strip() == 'if [ -f  "/usr/local/sdsys/bin/sd" ]; then')
    cp_bin = first(lambda l: l.strip() == 'sudo cp -R bin "$sdsysdir"')
    first_change = first(lambda l: "git clone --branch" in l or "sudo groupadd" in l)
    row("D2 the installer still refuses to run over an install (line %s) before it clones or creates anything (%s), copies bin (%s) and chowns (%s) before the block (%d)"
        % (guard and guard + 1, first_change and first_change + 1, cp_bin and cp_bin + 1, chown_main and chown_main + 1, bi + 1),
        guard is not None and first_change is not None and guard < first_change and cp_bin is not None and cp_bin < bi and chown_main is not None and chown_main < bi,
        "guard %s, first change %s, cp -R bin %s" % (guard, first_change, cp_bin))

    # ---- D3 -----------------------------------------------------------------------------------------------------------------------------------------------
    sdsys_lines = [l for l in sud.split("\n") if l.startswith("sdsys ") and "NOPASSWD" in l]
    row("D3 the drop-in gives the sdsys user one command, the helper outside the tree (%s)" % [l.strip() for l in sdsys_lines],
        len(sdsys_lines) == 1 and sdsys_lines[0].strip().endswith("NOPASSWD: /usr/local/sbin/sd-elevate"), "")

    print("test-rootbin-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


# ======================================================================================================================================================================
def selftest():
    import shutil
    t = tempfile.mkdtemp()
    caught = missed = 0
    me = os.path.abspath(__file__)
    real = {"inst": read(INST), "del": read(DELETER), "make": read(MAKEFILE), "sysseg": read(SYSSEG_C), "sd": read(SD_C), "sdlnxd": read(SDLNXD_C), "opk": read(OPKERNEL_C)}
    seq = [0]

    def prep_dir(kind):
        """a copy of the units (kind 'u') or of the helper files (kind 'h') to change"""
        seq[0] += 1
        d = os.path.join(t, "d%d" % seq[0])
        os.makedirs(d)
        if kind == "u":
            for fn in os.listdir(UNITDIR):
                shutil.copy(os.path.join(UNITDIR, fn), d)
        else:
            for fn in HELPERS + [SUDOERS]:
                shutil.copy(os.path.join(HELPERDIR, fn), d)
        return d

    def run_with(extra):
        e = dict(os.environ)
        e.update(extra)
        r = subprocess.run([sys.executable, me], env=e, capture_output=True, text=True)
        return r

    def verdict(name, expect, r):
        nonlocal caught, missed
        failing = [l.strip() for l in r.stdout.split("\n") if l.strip().startswith("[FAIL]")]
        if r.returncode != 0 and any(re.match(r"\[FAIL\] %s\b" % re.escape(expect), l) for l in failing):
            print("  [caught] %s by %s" % (name, expect))
            caught += 1
        elif r.returncode != 0:
            print("  [MISSED] %s: it failed, but not on %s: %s" % (name, expect, [l[:50] for l in failing] or r.stdout[-200:]))
            missed += 1
        else:
            print("  [MISSED] %s: the check still passed" % name)
            missed += 1

    def file_mutant(name, expect, which, old, new, envname):
        nonlocal missed
        src = real[which]
        if old not in src:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        f = os.path.join(t, "%s.txt" % name)
        open(f, "w", encoding="latin-1").write(src.replace(old, new, 1))
        verdict(name, expect, run_with({envname: f}))

    def text_mutant(name, expect, which, fn, envname):
        """fn(src) -> new src, or None when it did not apply"""
        nonlocal missed
        new = fn(real[which])
        if new is None or new == real[which]:
            print("  [MISSED] %s: the mutation changed nothing" % name)
            missed += 1
            return
        f = os.path.join(t, "%s.txt" % name)
        open(f, "w", encoding="latin-1").write(new)
        verdict(name, expect, run_with({envname: f}))

    def dir_mutant(name, expect, kind, fname, old, new, envname, count=1):
        nonlocal missed
        d = prep_dir(kind)
        p = os.path.join(d, fname)
        s = read(p)
        if old not in s:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        open(p, "w", encoding="latin-1").write(s.replace(old, new, count))
        verdict(name, expect, run_with({envname: d}))

    def inst(name, expect, old, new):
        file_mutant(name, expect, "inst", old, new, "INSTALLER")

    def move_block(src, anchor, after):
        m = re.search(r"^# ROOTBIN-BEGIN\n.*?^# ROOTBIN-END\n", src, re.S | re.M)
        if not m or anchor not in src:
            return None
        blk = m.group(0)
        s = src.replace(blk, "", 1)
        i = s.index(anchor)
        i += len(anchor) if after else 1       # every anchor starts and ends with a newline: the block goes on a line of its own
        return s[:i] + blk + s[i:]

    print("selftest: the real files first (must pass), then mutants (each must fail on the named check)")
    r = run_with({})
    if r.returncode != 0:
        print("  [FAIL] the real files do not pass:\n" + r.stdout[-900:])
        return 1
    print("  [ok] the real files pass")

    # the block's place
    text_mutant("block-before-bootstrap", "B2", "inst", lambda s: move_block(s, '\necho "Bootstrap pass 1."\n', False), "INSTALLER")
    text_mutant("block-before-chown", "B2", "inst", lambda s: move_block(s, '\nsudo chown -R sdsys:sdusers "$sdsysdir"\n', False), "INSTALLER")
    text_mutant("block-after-passwords", "B2", "inst", lambda s: move_block(s, '\necho "PASSWORDS."\n', True), "INSTALLER")
    text_mutant("block-before-last-compile", "B2", "inst", lambda s: move_block(s, '\nfix_gcat_modes\n#\necho\necho Compiling terminfo database\n', False), "INSTALLER")
    inst("block-marker-gone", "B1", "# ROOTBIN-BEGIN", "# rootbin-begin")
    text_mutant("block-twice", "B1", "inst", lambda s: s.replace("# ROOTBIN-END\n", "# ROOTBIN-END\n# ROOTBIN-BEGIN\n:\n# ROOTBIN-END\n", 1), "INSTALLER")
    inst("rootbin-elsewhere", "B1", 'rootbin="$sdsysdir/bin"', 'rootbin="$sdsysdir/bin/"')
    # the list
    inst("list-lost-sdidx", "B4", "rootbin_files=(sd sdlnxd sdidx pcode)", "rootbin_files=(sd sdlnxd pcode)")
    inst("list-lost-pcode", "B4", "rootbin_files=(sd sdlnxd sdidx pcode)", "rootbin_files=(sd sdlnxd sdidx)")
    inst("list-extra-sdfix", "B4", "rootbin_files=(sd sdlnxd sdidx pcode)", "rootbin_files=(sd sdlnxd sdidx pcode sdfix)")
    dir_mutant("unit-new-daemon", "B4", "u", "sd-lnxd.service", "ExecStart=/usr/local/sdsys/bin/sdlnxd", "ExecStart=/usr/local/sdsys/bin/sdnewd", "UNITDIR")
    dir_mutant("unit-new-prestart", "B4", "u", "sd.service", "ExecStart=/usr/local/sdsys/bin/sd -start -nodaemon", "ExecStartPre=/usr/local/sdsys/bin/sdprep\nExecStart=/usr/local/sdsys/bin/sd -start -nodaemon", "UNITDIR")
    dir_mutant("unit-prefixed-exec", "B4", "u", "sd.service", "ExecStop=/usr/local/sdsys/bin/sd -stop", "ExecStop=-/usr/local/sdsys/bin/sdstopper -stop", "UNITDIR")
    dir_mutant("socket-runs-a-file", "B4", "u", "sdclient.socket", "[Socket]\n", "[Socket]\nExecStartPost=/usr/local/sdsys/bin/sdpost\n", "UNITDIR")
    dir_mutant("elevate-runs-sdfix", "B4", "h", "sd-elevate", '    "$SD_SYS_ROOT_REAL/bin/sdidx" -p "$1" "$2" || die', '    "$SD_SYS_ROOT_REAL/bin/sdfix" -q "$1"\n    "$SD_SYS_ROOT_REAL/bin/sdidx" -p "$1" "$2" || die', "HELPER_DIR")
    dir_mutant("elevate-loses-sdidx", "B4", "h", "sd-elevate", "$SD_SYS_ROOT_REAL/bin/sdidx", "$SD_SYS_ROOT_REAL/bin/sd", "HELPER_DIR", count=-1)
    dir_mutant("helper-runs-sdconv", "B4", "h", "reconcile-accounts.sh", "SDSYS=/usr/local/sdsys\n", "SDSYS=/usr/local/sdsys\n/usr/local/sdsys/bin/sdconv --help\n", "HELPER_DIR")
    file_mutant("kernel-new-daemon-name", "B4", "sysseg", '"%s/bin/sdlnxd"', '"%s/bin/sdlnxd2"', "SYSSEG_C")
    file_mutant("kernel-no-pcode", "B4", "sd", '"%s%cbin%cpcode"', '"%s%cbin%cpcodx"', "SD_C")
    file_mutant("kernel-new-exec", "B4", "opk", '"%s/bin/sd"', '"%s/bin/sdphantom"', "OPKERNEL_C")
    # the units and the sudoers
    dir_mutant("unit-under-sysdir-not-bin", "U1", "u", "sd-lnxd.service", "ExecStart=/usr/local/sdsys/bin/sdlnxd", "ExecStart=/usr/local/sdsys/gplbld/sdlnxd", "UNITDIR")
    dir_mutant("unit-nonroot-under-sysdir", "U1", "u", "sd-ai@.service", "ExecStart=/usr/local/lib/sd-ai/sd-ai", "ExecStart=/usr/local/sdsys/bin/sd-ai", "UNITDIR")
    dir_mutant("unit-runs-uninstalled-file", "U2", "u", "sd.service", "ExecStartPre=-/usr/local/sbin/sd-reconcile-accounts --sweep", "ExecStartPre=-/usr/local/sbin/sd-zz-new --sweep", "UNITDIR")
    dir_mutant("sudoers-names-a-file-in-the-tree", "U2", "h", SUDOERS, "sdsys ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate", "sdsys ALL=(root) NOPASSWD: /usr/local/sdsys/bin/sdfix", "HELPER_DIR")
    dir_mutant("sudoers-second-line-for-sdsys", "D3", "h", SUDOERS, "sdsys ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate\n", "sdsys ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate\nsdsys ALL=(root) NOPASSWD: /usr/local/sbin/sd-accarchive\n", "HELPER_DIR")
    # the block's commands and guards
    inst("block-chowns-sdsys", "B5", 'sudo chown -R root:root "$rootbin"\n    sudo chmod', 'sudo chown -R sdsys:sdusers "$rootbin"\n    sudo chmod')
    inst("block-group-write", "B5", 'sudo chmod -R go-w "$rootbin"', 'sudo chmod -R g+w "$rootbin"')
    inst("block-numeric-775", "B5", 'sudo chmod -R go-w "$rootbin"', 'sudo chmod -R 775 "$rootbin"')
    inst("block-extra-chmod", "B5", 'sudo chmod -R go-w "$rootbin"\n', 'sudo chmod -R go-w "$rootbin"\n    sudo chmod 666 "$rootbin/pcode"\n')
    inst("block-chown-not-recursive", "B5", 'sudo chown -R root:root "$rootbin"', 'sudo chown root:root "$rootbin"')
    inst("immutable-lifted-not-set", "B5", 'if sudo chattr +i "$rootbin" 2>/dev/null; then', 'if sudo chattr -i "$rootbin" 2>/dev/null; then')
    inst("link-test-gone", "B6", 'if [ -L "$rootbin" ] || [ ! -d "$rootbin" ]; then', 'if [ ! -d "$rootbin" ]; then')
    inst("odd-find-gone", "B6", 'sudo find "$rootbin" -mindepth 1 \\! -type f 2>/dev/null', 'sudo find "$rootbin" -mindepth 1 -name zz-none 2>/dev/null')
    inst("lift-after-chown", "B6", '    sudo chattr -i "$rootbin" 2>/dev/null || true\n    sudo chown -R root:root "$rootbin"\n', '    sudo chown -R root:root "$rootbin"\n    sudo chattr -i "$rootbin" 2>/dev/null || true\n')
    inst("flag-read-from-exit-status", "B6", 'case "$rootbin_flags" in *i*) rootbin_imm=yes ;; esac', 'rootbin_imm=yes')
    inst("success-ignores-attribute", "B6", ' && [ "$rootbin_imm" = yes ]; then', '; then')
    inst("success-ignores-owner-check", "B6", 'if [ -z "$rootbin_bad" ] && [ -z "$rootbin_miss" ]', 'if [ -z "$rootbin_miss" ]')
    # the closing summary (26 Oct 26, review of F11)
    inst("sealed-flag-never-set", "B7", '        rootbin_sealed=1\n', '')
    inst("sealed-flag-set-at-start", "B7", 'rootbin_sealed=0\n', 'rootbin_sealed=1\n')
    inst("summary-gone", "B7", 'if [ "${rootbin_sealed:-0}" -ne 1 ]; then', 'if false; then')
    inst("summary-silent", "B7", 'echo "WARNING: the files root runs ($sdsysdir/bin) were NOT sealed;', 'echo "WARNING: the files root runs ($sdsysdir/bin) were not looked at;')
    # after the block
    inst("write-after-block", "B3", 'echo "PASSWORDS."\n', 'sudo cp /tmp/x "$sdsysdir/bin/sdnew"\necho "PASSWORDS."\n')
    inst("rechown-after-block", "B3", 'echo "PASSWORDS."\n', 'sudo chown -R sdsys:sdusers "$sdsysdir"\necho "PASSWORDS."\n')
    inst("chmod-bin-after-block", "B3", 'echo "PASSWORDS."\n', 'sudo chmod 775 "$sdsysdir/bin"\necho "PASSWORDS."\n')
    inst("redirect-into-bin-after-block", "B3", 'echo "PASSWORDS."\n', 'echo x >> "$sdsysdir/bin/pcode"\necho "PASSWORDS."\n')
    # the remover and the upgrade path
    file_mutant("deleter-no-lift", "D1", "del", 'sudo chattr -i "$sdsysdir/bin" 2>/dev/null || true\n', "", "DELETER")
    file_mutant("deleter-lift-after-removal", "D1", "del", 'sudo chattr -i "$sdsysdir/bin" 2>/dev/null || true\n\n# remove the /usr/sdsys directory\nsudo rm -fr "$sdsysdir"',
                '# remove the /usr/sdsys directory\nsudo rm -fr "$sdsysdir"\nsudo chattr -i "$sdsysdir/bin" 2>/dev/null || true', "DELETER")
    file_mutant("deleter-sets-attribute", "D1", "del", 'sudo chattr -i "$sdsysdir/bin" 2>/dev/null || true\n', 'sudo chattr -i "$sdsysdir/bin" 2>/dev/null || true\nsudo chattr +i "$sdsysdir/gcat" 2>/dev/null || true\n', "DELETER")
    inst("installer-no-refusal", "D2", 'if [ -f  "/usr/local/sdsys/bin/sd" ]; then', 'if [ -f  "/usr/local/sdsys/bin/sdx" ]; then')
    inst("installer-no-bin-copy", "D2", 'sudo cp -R bin "$sdsysdir"\n', 'sudo cp -R binx "$sdsysdir"\n')
    # libraries
    file_mutant("makefile-rpath", "L1", "make", "L_FLAGS    := ", "L_FLAGS    := -Wl,-rpath,/usr/local/sdsys/bin ", "MAKEFILE")
    dir_mutant("unit-ld-library-path", "L1", "u", "sd-lnxd.service", "Restart=on-failure\n", "Restart=on-failure\nEnvironment=LD_LIBRARY_PATH=/usr/local/sdsys/bin\n", "UNITDIR")
    inst("installer-adds-ld-path", "L1", 'echo "PASSWORDS."\n', 'echo /usr/local/sdsys/bin | sudo tee /etc/ld.so.conf.d/sd.conf\necho "PASSWORDS."\n')
    gdir = os.path.join(t, "gplsrc-dl")
    os.makedirs(gdir)
    shutil.copy(os.path.join(GPLSRC, "op_ccall.c"), gdir)
    open(os.path.join(gdir, "zz_loader.c"), "w").write("void f(void) { dlopen(\"/usr/local/sdsys/bin/x.so\", 0); }\n")
    verdict("dlopen-in-another-file", "L1", run_with({"GPLSRC": gdir}))
    shutil.rmtree(t, ignore_errors=True)
    total = caught + missed
    print("selftest: %d of %d mutants caught, %d missed" % (caught, total, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
