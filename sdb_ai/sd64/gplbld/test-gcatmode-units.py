#!/usr/bin/env python3
# test-gcatmode-units.py - W.11 F2 (security-model evaluation, 24 Oct 2026): a global catalogue object that others or the group sdusers can write is
# not trusted.  FREE CHECK: no install, no sudo, no sd; the installer function is RUN in bash on scratch files, the kernel check is read as text.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-gcatmode-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-gcatmode-units.py --selftest      (mutants of the installer and of object.c)
#
# WHAT IT CHECKS
#   I1  fix_gcat_modes is defined between GCAT-MODE-BEGIN and -END; run in bash (sudo a function that skips chown) on a scratch gcat it clears group and
#       other write from 0664, 0666 and 0775 files, leaves a 0755 file alone, and exits 0
#   I2  it is called straight after the CPROC compile (before the next sd run), and again after the final stop of SD
#   K1  object.c: gcat_object_writable() fails closed when fstat fails, refuses S_IWOTH, refuses S_IWGRP when the file's group is sdusers
#   K2  load_object() applies it to an object with OBJ_GLOBAL, before it reads the header, closes the file and takes message 11930
#   M1  message 11930 exists, names %1, and is in the Linux block (11000-11999, not one of Solo's 11900-11914 or 11920-11925)
# WHAT IT CANNOT SAY: that the kernel refuses a writable object when it runs - that is sandbox-gcatmode.py.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
INST = os.environ.get("INSTALLER", os.path.join(ROOT, "installsdcore.sh"))
OBJC = os.environ.get("OBJECTC", os.path.join(ROOT, "sdb_ai", "sd64", "gplsrc", "object.c"))
MSGDIR = os.path.join(ROOT, "sdb_ai", "sd64", "sdsys", "messages")
passed = failed = 0


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
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def run():
    inst = read(INST)
    m = re.search(r"^# GCAT-MODE-BEGIN\n(.*?)^# GCAT-MODE-END", inst, re.S | re.M)
    if not m:
        print("test-gcatmode-units: CANNOT RUN - no GCAT-MODE block in the installer")
        return 2
    func = m.group(1)
    # I1: run the function
    with tempfile.TemporaryDirectory() as t:
        g = os.path.join(t, "gcat")
        os.makedirs(g)
        want = {"a664": 0o664, "a666": 0o666, "a775": 0o775, "ok755": 0o755, "ok644": 0o644}
        for n, md in want.items():
            p = os.path.join(g, n)
            open(p, "w").write("x")
            os.chmod(p, md)
        script = ("set -euo pipefail\nIFS=$'\\n\\t'\nsdsysdir='%s'\n"
                  "sudo() { if [ \"$1\" = chown ]; then return 0; fi; \"$@\"; }\n%s\nfix_gcat_modes\necho DONE\n") % (t, func)
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        modes = {n: os.stat(os.path.join(g, n)).st_mode & 0o777 for n in want}
        row("I1 the function exits 0 under the installer's set and IFS", r.returncode == 0 and "DONE" in r.stdout, r.stderr.strip()[:200])
        row("I1 group and other write cleared from 0664, 0666 and 0775",
            all(modes[n] & 0o022 == 0 for n in ("a664", "a666", "a775")), str(modes))
        row("I1 a 0755 and a 0644 file are left as they were", modes["ok755"] == 0o755 and modes["ok644"] == 0o644, str(modes))
        row("I1 the group and other read and execute bits are kept", modes["a775"] == 0o755 and modes["a664"] == 0o644, str(modes))
    # I2: order
    lines = inst.split("\n")
    comp = [i for i, l in enumerate(lines) if "sudo bin/sd -internal BASIC gpl.bp cproc" in l]
    calls = [i for i, l in enumerate(lines) if l.strip() == "fix_gcat_modes"]
    if not comp:
        row("I2 the CPROC compile is found", False, "no compile line")
    else:
        c0 = comp[0]
        after = [i for i in calls if i > c0]
        nxt_sd = [i for i, l in enumerate(lines) if i > c0 and re.search(r"\b(sudo )?(\"\$\{?sdsysdir\}?/bin/sd\"|bin/sd)\b", l) and not l.strip().startswith("#")]
        first_call_ok = bool(after) and after[0] < (nxt_sd[0] if nxt_sd else 10 ** 9) and after[0] - c0 <= 8
        row("I2 fix_gcat_modes is called straight after the CPROC compile", first_call_ok,
            "compile at %d, calls after it %s" % (c0 + 1, [i + 1 for i in after]))
        stops = [i for i, l in enumerate(lines) if l.strip() == "sd_install_start || true"]
        late = stops and any(i > stops[0] and i - stops[0] <= 6 for i in calls)
        row("I2 and again after the last start and stop of SD", bool(late), "start at %s, calls %s" % ([i + 1 for i in stops], [i + 1 for i in calls]))
    # K1, K2
    obj = strip_c_comments(read(OBJC))
    fm = re.search(r"Private bool gcat_object_writable\(OSFILE fd\) \{(.*?)\n\}", obj, re.S)
    if not fm:
        row("K1 gcat_object_writable() is defined", False, "not found in object.c")
        body = ""
    else:
        body = fm.group(1)
        row("K1 it fails closed when fstat fails", bool(re.search(r"fstat\(fd, &st\) != 0\)\s*return TRUE", body)))
        row("K1 it refuses a file others can write", bool(re.search(r"st\.st_mode & S_IWOTH\)\s*return TRUE", body)))
        row("K1 it refuses a file the group sdusers can write",
            bool(re.search(r"st\.st_mode & S_IWGRP\) && \(sdusers_gid != \(gid_t\)-1\) && \(st\.st_gid == sdusers_gid\)\)\s*return TRUE", body))
            and 'getgrnam("sdusers")' in body)
    lo = re.search(r"found:\n(.*?)Read\(obj_fu, \(char\*\)\(&obj_header\)", obj, re.S)
    guard = lo.group(1) if lo else ""
    row("K2 load_object() applies it to OBJ_GLOBAL before reading the header",
        bool(re.search(r"\(flags & OBJ_GLOBAL\) && gcat_object_writable\(obj_fu\)", guard)))
    row("K2 it closes the file and reports message 11930", "CloseFile(obj_fu)" in guard and "sysmsg(11930)" in guard.replace(" ", ""))
    row("K2 and it is an error whether or not the caller asked for no abort (never a NULL return)", "return NULL" not in guard and "abort_on_error" not in guard)
    # M1
    p = os.path.join(MSGDIR, "11930")
    txt = read(p) if os.path.exists(p) else ""
    row("M1 message 11930 exists and takes the name with %s (a C-level message: %1 is for BASIC)", "%s" in txt and "%1" not in txt and len(txt.strip()) > 20, txt.strip()[:80])
    row("M1 11930 is in the Linux block and not one of Solo's numbers", 11000 <= 11930 < 12000 and not (11900 <= 11930 <= 11914 or 11920 <= 11930 <= 11925))
    print("test-gcatmode-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


def selftest():
    import shutil
    t = tempfile.mkdtemp()
    caught = missed = 0
    reali = read(INST)
    realo = read(OBJC)

    def mutant(name, which, old, new):
        nonlocal caught, missed
        src = reali if which == "i" else realo
        if old not in src:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        f = os.path.join(t, name + (".sh" if which == "i" else ".c"))
        open(f, "w", encoding="latin-1").write(src.replace(old, new, 1))
        env = dict(os.environ)
        env["INSTALLER" if which == "i" else "OBJECTC"] = f
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print("  [caught] %s (exit %d)" % (name, r.returncode))
            caught += 1
        else:
            print("  [MISSED] %s: the check still passed" % name)
            missed += 1

    print("selftest: the real files first (must pass), then mutants (each must not)")
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] the real files do not pass:\n" + r.stdout[-600:])
        return 1
    print("  [ok] the real files pass")
    mutant("installer-no-find", "i", '    sudo find "$sdsysdir/gcat" -type f -perm /022 -exec chmod go-w {} +\n', "    true\n")
    mutant("installer-adds-write", "i", "-exec chmod go-w {} +", "-exec chmod go+w {} +")
    mutant("installer-only-group", "i", "-perm /022 -exec chmod go-w", "-perm /020 -exec chmod g-w")
    mutant("installer-no-call-after-compile", "i", "fi\nfix_gcat_modes\n#", "fi\n#")
    mutant("installer-no-final-call", "i", "sd_install_stop\nfix_gcat_modes\n#", "sd_install_stop\n#")
    mutant("kernel-fstat-fails-open", "o", "return TRUE; /* cannot tell: fail closed */", "return FALSE;")
    mutant("kernel-ignores-other-write", "o", "if (st.st_mode & S_IWOTH)\n    return TRUE;", "if (0)\n    return TRUE;")
    mutant("kernel-ignores-group-write", "o", "(st.st_mode & S_IWGRP) &&", "(0) &&")
    mutant("kernel-any-group", "o", " && (st.st_gid == sdusers_gid)", "")
    mutant("kernel-not-applied-to-global", "o", "if ((flags & OBJ_GLOBAL) && gcat_object_writable(obj_fu))", "if (0 && gcat_object_writable(obj_fu))")
    mutant("kernel-applied-to-all", "o", "if ((flags & OBJ_GLOBAL) && gcat_object_writable(obj_fu))", "if (gcat_object_writable(obj_fu))")
    mutant("kernel-no-close", "o", "    CloseFile(obj_fu);\n    /* Always an error", "    /* Always an error")
    mutant("kernel-returns-null", "o", "    k_error(sysmsg(11930), name);\n  }", "    if (abort_on_error)\n      k_error(sysmsg(11930), name);\n    else\n      return NULL;\n  }")
    mutant("kernel-wrong-message", "o", "sysmsg(11930)", "sysmsg(1128)")
    shutil.rmtree(t, ignore_errors=True)
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
