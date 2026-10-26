#!/usr/bin/env python3
"""test-confset-elevate-units.py - sd-elevate's conf-set (S.75 A6, the write half of tool.config): the root helper that changes ONE tuning parameter of /etc/sd.conf.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-confset-elevate-units.py
    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-confset-elevate-units.py --selftest

No sudo, no install, no sd.  It CUTS the functions between "# BEGIN confset_functions" and "# END confset_functions" out of sd-elevate and runs them with bash on scratch files, playing root
itself, exactly as test-bakdir-elevate-units.py does for bakdir-set; and it drives the real script with --dry-run for the verb's argument rules.  ***IT CANNOT SAY THAT ROOT WRITES
/etc/sd.conf***: the file's real owner, the sudoers line and the sudo call are the VM witness's rows (the lead's list), not this check's.

WHAT IS HELD.  (1) THE LIST IS THE PARSER'S AND NARROWER: the helper knows by name exactly the parameters config.c's read_config() takes (writable + known-but-fixed), the writable ones are
the ones config.c range-checks, with the range rangecheck() enforces, and the table's 'write', range and effect columns say the same as the helper; a pinned list of doors, paths, commands,
logs and throttles can never become writable without this turning red.  (2) EVERY REFUSAL has its own wording and changes nothing: no name, a name with a case change, an unknown name, a
known fixed name, no value, a value with a newline, a space, a quote, a sign, a point, a leading zero, too many digits, below the minimum and above the maximum of every writable parameter;
the boundaries are accepted.  (3) THE WRITE: the line goes inside an [sd] section (the only place config.c reads), the old line is replaced where it is and a stale second one dropped,
nothing else changes, the file is renamed into place from a temp file (a reader of the old file still sees the old text), its mode and (through chown --reference) its owner are kept, the
file as it was is kept as sd.conf.bak, an unchanged value writes nothing, a symlink or a NUL byte or no [sd] section is refused, a write that did not land is caught by the read-back, and a
failed copy leaves no temp file.  (4) THE CALLER: sudo's SUDO_USER must be sdsys when it is set.  (5) THE VERB'S ARGUMENTS (the real script, --dry-run) and its place in the script:
the names are checked before need_root, the caller after it, the write last; the file is /etc/sd.conf and nothing moves it; sudoers gives conf-set to nobody new.

Every check prints what it used and what it saw.  --selftest breaks the helper 40 ways (and the script text 8) and requires a named check to go red for each one.
Exit 0 every check passed, 1 a check failed, 2 it could not measure.
"""

import contextlib
import difflib
import importlib.util
import io
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ELEVATE = os.path.join(HERE, "sd-elevate")
SUDOERS = os.path.join(HERE, "sdcore.sudoers")
BEGIN = "# BEGIN confset_functions"
END = "# END confset_functions"

WRITABLE = ["CLEANUP", "DHCACHE", "GRPSIZE", "LGNWAIT", "LPTRHIGH", "LPTRWIDE", "MAXCALL", "MAXRLOCK", "NETREPLY", "NETWAIT", "NUMLOCKS", "RECCACHE", "SORTMRG", "USPLIT"]
# parameters that must NEVER be writable here: the doors and their settings, every path and command, the logs, dumps and diagnostics, the security throttle, and the sizing/combining
# parameters config.c does not check or checks against each other.  A name moved out of config.c's fixed set into the list turns CS4 red.
NEVER = ["NETFILES", "SDCLIENT", "PORTMAP", "FILERULE", "FIXUSERS", "PHANTOMS", "USERPOOL", "SDSYS", "DUMPDIR", "GRPDIR", "USRDIR", "SH", "SH1", "STARTUP", "TEMPDIR", "SORTWORK", "SPOOLER",
         "TERMINFO", "BACKUPDIR", "JNLDIR", "ERRLOG", "DEBUG", "PDUMP", "DEADLOCK", "PWDELAY", "CMDSTACK", "FDS", "NUMFILES", "NUMUSERS", "OBJECTS", "OBJMEM", "SORTMEM", "MAXIDLEN",
         "APILOGIN", "CREATUSR", "SCREENTHEME"]

T_FUNC = r'''t() { local out rc; out=$( (confset_check "$2" "$3") 2>&1 ); rc=$?; printf 'CASE\t%s\t%d\t%s\n' "$1" "$rc" "${out//$'\n'/ }"; }'''

BASE = "# SD configuration\n[sd]\nSDSYS=/usr/local/sdsys\nGRPSIZE=4\nNUMUSERS=20\n\n# the dumps\nDUMPDIR=/usr/local/sdsys/dumps\n# a trailing comment\n\n"


def load_module(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def cut_code(text):
    lines = text.split("\n")
    b = [i for i, l in enumerate(lines) if l.strip() == BEGIN]
    e = [i for i, l in enumerate(lines) if l.strip() == END]
    if len(b) != 1 or len(e) != 1 or b[0] >= e[0]:
        print("REFUSED: sd-elevate must hold exactly one '%s' and one '%s' line, in that order (found %d and %d)" % (BEGIN, END, len(b), len(e)), file=sys.stderr)
        sys.exit(2)
    return "\n".join(lines[b[0] + 1:e[0]])


def stat_of(path, field):
    """One field of os.stat(path), None when the path is not there (a mutant may leave no .bak, and the check must go red rather than crash)."""
    try:
        return getattr(os.stat(path), field)
    except OSError:
        return None


def model_read(text, kinds):
    """config.c's reader as a model: only the [sd] section, a line beginning # or empty skipped, KEY=value, an int key needs a number after the =.
    Returns ({key: last value}, [lines SD would refuse as unrecognised])."""
    sect, vals, bad = "", {}, []
    for ln in text.split("\n"):
        if ln == "" or ln[0] == "#":
            continue
        if ln[0] == "[":
            sect = ln[1:].split("]")[0][:32].upper()
            continue
        if sect != "SD":
            continue
        m = re.match(r"([A-Z0-9]+)=(.*)$", ln, re.S)
        if not m or m.group(1) not in kinds:
            bad.append(ln)
            continue
        if kinds[m.group(1)] in ("int", "flag", "bits") and not re.match(r"\s*[+-]?\d+", m.group(2)):
            bad.append(ln)
            continue
        vals[m.group(1)] = m.group(2)
    return vals, bad


class Suite:
    def __init__(self, code, script_text, raw, tc):
        self.code = code
        self.script_text = script_text
        self.raw = raw
        self.tc = tc
        self.checks = 0
        self.failed = 0
        self.failed_ids = []
        self.quiet = False
        self.tmp = None
        self.script_path = ELEVATE
        self.sudoers_path = SUDOERS

    def check(self, cid, name, ok, saw):
        self.checks += 1
        if not ok:
            self.failed += 1
            self.failed_ids.append(cid)
        if not self.quiet or not ok:
            saw = repr(saw) if not isinstance(saw, str) else saw
            print("  [%s] %s %s | saw: %s" % ("PASS" if ok else "FAIL", cid, name, saw[:260]))

    def bash(self, call, env=None):
        script = 'set -uo pipefail\ndie() { printf "REFUSED - %%s\\n" "$1" >&2; exit 2; }\n%s\n%s\n' % (self.code, call)
        e = dict(os.environ)
        e.pop("SUDO_USER", None)
        if env:
            e.update(env)
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env=e)

    def put(self, text, mode=0o644, name="sd.conf"):
        p = os.path.join(self.tmp, name)
        for stale in (p, p + ".bak"):
            if os.path.lexists(stale):
                os.unlink(stale)
        with open(p, "w", newline="") as fh:
            fh.write(text)
        os.chmod(p, mode)
        return p

    def left(self):
        return sorted(n for n in os.listdir(self.tmp) if n.startswith("sd.conf.") and n != "sd.conf.bak")

    def setk(self, f, k, v, pre=""):
        """check and write, as the verb's arm does; prints CHANGED=n when it got that far"""
        return self.bash('%s\nconfset_check %s %s && conf_set %s %s %s && printf "CHANGED=%%s\\n" "$CS_CHANGED"' % (pre, shlex.quote(k), shlex.quote(v), shlex.quote(f), shlex.quote(k), shlex.quote(v)))

    # ----------------------------------------------------------------------------------------------------------------------------------------- the list
    def suite_list(self):
        raw, tc = self.raw, self.tc
        dest = tc.parser_keys(raw["configc"])
        rng = tc.c_ranges(raw)
        trs = tc.table_rows(raw["table"])
        keys = sorted(dest)
        decoys = ["ZZNEW", "CLEANUPX", "XCLEANUP", "SD"]
        r = self.bash('for k in %s; do if confset_limits "$k"; then echo "$k W $CS_MIN $CS_MAX $CS_EFFECT"; elif confset_fixed "$k"; then echo "$k F"; else echo "$k U"; fi; done; echo "LIST=$CS_WRITABLE"'
                      % " ".join(keys + decoys))
        cls, helper = {}, {}
        listvar = ""
        for ln in r.stdout.split("\n"):
            p = ln.split(" ")
            if ln.startswith("LIST="):
                listvar = ln[5:]
            elif len(p) >= 2:
                cls[p[0]] = p[1]
                if p[1] == "W":
                    helper[p[0]] = (int(p[2]), int(p[3]), p[4])
        writable = sorted(k for k, c in cls.items() if c == "W")
        fixed = sorted(k for k, c in cls.items() if c == "F")
        self.check("CS0", "NULL CASE: the helper's functions were cut, config.c gave more than 40 parameters, the table 63 rows, the classifier answered for all %d names" % (len(keys) + len(decoys)),
                   len(dest) > 40 and len(trs) == 63 and len(cls) == len(keys) + len(decoys) and r.returncode == 0 and len(writable) > 0, "%d %d %d exit %d %r" % (len(dest), len(trs), len(cls), r.returncode, r.stderr[:100]))
        self.check("CS1", "THE HELPER KNOWS THE PARSER'S NAMES AND NO OTHERS: writable + fixed are exactly the %d parameters read_config() takes, none is both, and a lookalike (ZZNEW, CLEANUPX, XCLEANUP, SD) is unknown"
                   % len(keys), sorted(writable + fixed) == keys and not (set(writable) & set(fixed)) and all(cls[d] == "U" for d in decoys),
                   "only helper %s, only parser %s, decoys %s" % (sorted(set(writable + fixed) - set(keys)), sorted(set(keys) - set(writable + fixed)), [cls[d] for d in decoys]))
        self.check("CS1b", "the writable names are exactly the %d the owner was shown, and CS_WRITABLE (the list the page's text quotes) says the same" % len(WRITABLE),
                   writable == WRITABLE and sorted(listvar.split(" ")) == WRITABLE, "%s | %s" % (writable, listvar))
        bad = []
        for k in writable:
            if k not in rng:
                bad.append((k, "config.c has no rangecheck for it"))
            elif rng[k] != (helper[k][0], helper[k][1]):
                bad.append((k, "helper", helper[k][:2], "config.c", rng[k]))
        self.check("CS2", "ONLY A PARAMETER CONFIG.C RANGE-CHECKS IS WRITABLE, WITH ITS RANGE: every writable name has a rangecheck() in read_config() and the helper's minimum and maximum are that rangecheck's (the macros read from the headers)",
                   not bad and len(rng) >= 15, repr(bad[:4]))
        bad = []
        by_key = {r_[0]: r_ for r_ in trs}
        for k in keys:
            row = by_key.get(k)
            if row is None or len(row) != 10:
                bad.append((k, "no ten-field table row"))
                continue
            want = "yes" if k in writable else "no"
            if row[8] != want:
                bad.append((k, "table write=" + row[8], "helper " + want))
            if k in helper:
                lo, hi, eff = helper[k]
                if (row[3], row[4]) != (str(lo), str(hi)):
                    bad.append((k, "range", (row[3], row[4]), (lo, hi)))
                if row[5] != eff:
                    bad.append((k, "effect table", row[5], "helper", eff))
                if row[6] != "live" or row[9] != "":
                    bad.append((k, "a writable row must be live with no reason"))
            elif not (row[9] and len(row[9]) <= 100 and "|" not in row[9] and row[9].strip() == row[9]):
                bad.append((k, "a fixed row needs a reason of 1 to 100 characters", len(row[9])))
        self.check("CS3", "THE TABLE SAYS WHAT THE HELPER DOES: the 'write' column is yes exactly for the helper's writable names, their range and effect are the helper's, a writable row is live and has no reason, a fixed one has one of at most 100 characters",
                   not bad, repr(bad[:4]))
        self.check("CS4", "NOTHING THAT IS A DOOR, A PATH OR COMMAND, A LOG OR DIAGNOSTIC, A THROTTLE OR A SIZE CONFIG.C DOES NOT CHECK IS WRITABLE: the %d names the owner's rule excludes are all fixed, none unknown" % len(NEVER),
                   all(cls.get(k) == "F" for k in NEVER), repr([(k, cls.get(k)) for k in NEVER if cls.get(k) != "F"]))
        return writable, helper

    # ----------------------------------------------------------------------------------------------------------------------------------------- refusals
    def suite_refusals(self, writable, helper):
        cases = []   # (id, key, value, wording the refusal must carry; None = accepted)
        add = lambda i, k, v, w: cases.append((i, k, v, w))
        add("R1 no name", "", "5", "no parameter name")
        add("R2 lower case", "cleanup", "600", "capital letter or a digit")
        add("R3 a case change", "Cleanup", "600", "capital letter or a digit")
        add("R4 a space in the name", "CLEAN UP", "600", "capital letter or a digit")
        add("R5 a newline in the name", "CLEANUP\nSDSYS", "600", "capital letter or a digit")
        add("R6 a quote in the name", "CLEANUP'", "600", "capital letter or a digit")
        add("R7 a dollar sign in the name", "$HOME", "600", "capital letter or a digit")
        add("R8 a name over 12 characters", "CLEANUPCLEANUP", "600", "longer than any parameter")
        add("R9 an unknown name", "ZZNEW", "1", "is not a parameter SD knows")
        add("R9b a name that only starts like one", "CLEANUPX", "40", "is not a parameter SD knows")
        add("R9c a name that begins with a digit", "9CLEANUP", "40", "capital letter or a digit")
        for k in ("NETFILES", "SDCLIENT", "SDSYS", "PORTMAP", "DUMPDIR", "SH", "STARTUP", "ERRLOG", "PWDELAY", "USERPOOL", "BACKUPDIR", "APILOGIN"):
            add("R10 the fixed name %s" % k, k, "1", "SD knows, and conf-set does not change it")
        add("R11 no value", "CLEANUP", "", "no value was given")
        add("R12 a newline in the value (a second line for sd.conf)", "CLEANUP", "600\nSDSYS=/etc", "digits only")
        add("R12b a trailing newline", "CLEANUP", "600\n", "digits only")
        add("R13 a space in the value", "CLEANUP", "6 0", "digits only")
        add("R14 a quote in the value", "CLEANUP", "6'0", "digits only")
        add("R15 a minus sign", "CLEANUP", "-60", "digits only")
        add("R16 a plus sign", "CLEANUP", "+60", "digits only")
        add("R17 a decimal point", "CLEANUP", "60.5", "digits only")
        add("R18 a hexadecimal number", "CLEANUP", "0x40", "digits only")
        add("R19 words", "CLEANUP", "sixty", "digits only")
        add("R20 a comment mark", "CLEANUP", "60#", "digits only")
        add("R21 a leading zero", "CLEANUP", "0040", "must not start with a zero")
        add("R22 eight digits", "CLEANUP", "12345678", "more than 7 digits")
        add("R22b eight digits that start with zeros", "CLEANUP", "00000040", "more than 7 digits")
        add("R23 a command substitution", "CLEANUP", "$(id)", "digits only")
        for k in writable:
            lo, hi, _ = helper[k]
            add("A1 %s at its minimum %d" % (k, lo), k, str(lo), None)
            add("A1 %s at its maximum %d" % (k, hi), k, str(hi), None)
            add("A1 %s in the middle" % k, k, str((lo + hi) // 2), None)
            if lo >= 1:
                add("R24 %s below its minimum" % k, k, str(lo - 1), "outside the range %d to %d" % (lo, hi))
            add("R25 %s above its maximum" % k, k, str(hi + 1), "outside the range %d to %d" % (lo, hi))
        lines = [T_FUNC]
        for n, (i, k, v, w) in enumerate(cases):
            lines.append("t %d %s %s" % (n, shlex.quote(k), shlex.quote(v)))
        r = self.bash("\n".join(lines))
        got = {}
        for ln in r.stdout.split("\n"):
            if ln.startswith("CASE\t"):
                p = ln.split("\t", 3)
                got[int(p[1])] = (int(p[2]), p[3] if len(p) > 3 else "")
        families = ["no parameter name", "capital letter or a digit", "longer than any parameter", "is not a parameter SD knows", "SD knows, and conf-set does not change it", "no value was given", "digits only",
                    "more than 7 digits", "must not start with a zero", "outside the range"]
        bad, mixed, used = [], [], set()
        for n, (i, k, v, w) in enumerate(cases):
            rc, msg = got.get(n, (None, "no answer"))
            if w is None:
                if rc != 0:
                    bad.append((i, "refused:", msg[:80]))
                continue
            if rc != 2 or w not in msg:
                bad.append((i, "wanted exit 2 and %r" % w, "exit %s: %s" % (rc, msg[:90])))
            fam = "outside the range" if w.startswith("outside the range") else w
            used.add(fam)
            present = {f for f in families if f in msg}
            if present != {fam}:
                mixed.append((i, sorted(present)))
        self.check("CS5", "EVERY REFUSAL IS A REFUSAL (%d cases: no name, case change, space, newline, quote, dollar, long, unknown, 12 fixed names, no value, newline/space/quote/sign/point/hex/words/comment/substitution in the value, leading zero, 8 digits, below the minimum and above the maximum of every writable parameter), exit 2 with its wording, and every boundary is accepted"
                   % len(cases), len(got) == len(cases) and not bad and r.returncode == 0, "%d of %d answered; first differences %s" % (len(got), len(cases), bad[:3]))
        self.check("CS5b", "EACH REFUSAL HAS ITS OWN WORDING: %d different sentences are used and no refusal carries another rule's sentence (the person is told which rule refused)" % len(families),
                   used == set(families) and not mixed, "used %d, mixed %s" % (len(used), mixed[:3]))
        # a refusal never echoes the offending text before it has passed (a control character in a name or value must not reach the terminal)
        r = self.bash('( confset_check "$(printf \'CLEAN\\033UP\')" 5 ) 2>&1; echo "rc=$?"')
        self.check("CS5c", "a name with an ESC in it is refused without being echoed", "\x1b" not in r.stdout and "rc=2" in r.stdout, repr(r.stdout[:160]))

    # ----------------------------------------------------------------------------------------------------------------------------------------- the write
    def suite_write(self, writable, helper):
        tmp = self.tmp
        # W1 added inside [sd], after the last line that sets something, before the comments that follow it
        f = self.put(BASE)
        r = self.setk(f, "CLEANUP", "600")
        want = BASE.replace("DUMPDIR=/usr/local/sdsys/dumps\n", "DUMPDIR=/usr/local/sdsys/dumps\nCLEANUP=600\n")
        got = open(f).read()
        self.check("W1", "a key the file lacks is ADDED inside [sd], after the last line that sets something and before the comment and blank lines after it; nothing else changes",
                   r.returncode == 0 and "CHANGED=1" in r.stdout and got == want, "exit %d %r" % (r.returncode, got[-120:]))
        # W2 replaced in place
        f = self.put("[sd]\nSDSYS=/x\nCLEANUP=40\nGRPSIZE=4\n# end\n")
        r = self.setk(f, "CLEANUP", "600")
        got = open(f).read()
        self.check("W2", "a key the file has is REPLACED WHERE IT IS (same place, one line), the lines around it byte for byte", r.returncode == 0 and got == "[sd]\nSDSYS=/x\nCLEANUP=600\nGRPSIZE=4\n# end\n", repr(got))
        # W3 duplicates
        f = self.put("[sd]\nCLEANUP=40\nSDSYS=/x\nCLEANUP=50\n[other]\nCLEANUP=70\n[SD]\nCLEANUP=80\n")
        r = self.setk(f, "CLEANUP", "600")
        got = open(f).read()
        self.check("W3", "a second CLEANUP line in an [sd] section is dropped (config.c keeps the last, so a stale one would win) and one in ANOTHER section is left alone",
                   r.returncode == 0 and got == "[sd]\nCLEANUP=600\nSDSYS=/x\n[other]\nCLEANUP=70\n[SD]\n", repr(got))
        # W4 only in another section
        f = self.put("[sd]\nSDSYS=/x\n[other]\nCLEANUP=70\n")
        r = self.setk(f, "CLEANUP", "600")
        got = open(f).read()
        self.check("W4", "a line in another section does not count: the key is ADDED to [sd] (appended at the end of the file it would be ignored) and the other section is untouched",
                   r.returncode == 0 and got == "[sd]\nSDSYS=/x\nCLEANUP=600\n[other]\nCLEANUP=70\n", repr(got))
        # W5 lookalikes
        look = "[sd]\n# CLEANUP=5\nCLEANUPX=1\nXCLEANUP=1\n  CLEANUP=5\nCLEANUP =7\ncleanup=9\n"
        f = self.put(look)
        r = self.setk(f, "CLEANUP", "600")
        got = open(f).read()
        self.check("W5", "a comment, CLEANUPX=, XCLEANUP=, an indented CLEANUP=, 'CLEANUP =' and cleanup= are NOT the key and are all kept; the line is added after them", r.returncode == 0 and got == look + "CLEANUP=600\n", repr(got))
        # W6 no newline at the end
        f = self.put("[sd]\nSDSYS=/x")
        r = self.setk(f, "GRPSIZE", "6")
        got = open(f).read()
        self.check("W6", "a last line without a newline is kept and the new line starts on its own line", r.returncode == 0 and got == "[sd]\nSDSYS=/x\nGRPSIZE=6\n", repr(got))
        # W7 nowhere to put it
        for name, text in (("no [sd] section", "[other]\nX=1\n"), ("an empty file", ""), ("a header that is not sd", "[ sd ]\nSDSYS=/x\n"), ("[sdx]", "[sdx]\nSDSYS=/x\n")):
            f = self.put(text)
            r = self.setk(f, "CLEANUP", "600")
            self.check("W7", "%s: refused, the file unchanged, no .bak and no temp file" % name,
                       r.returncode == 2 and "no [sd] section" in r.stderr and open(f).read() == text and not os.path.exists(f + ".bak") and not self.left(), "exit %d %s %r" % (r.returncode, r.stderr.strip()[:80], open(f).read()))
        # W8 header forms config.c accepts
        for name, hdr in (("[SD]", "[SD]"), ("[sd]xyz after the bracket", "[sd]xyz"), ("[sd with no closing bracket", "[sd"), ("[Sd]", "[Sd]")):
            f = self.put(hdr + "\nSDSYS=/x\n")
            r = self.setk(f, "CLEANUP", "600")
            self.check("W8", "the header %s is the [sd] section for config.c, so the line goes there" % name, r.returncode == 0 and open(f).read() == hdr + "\nSDSYS=/x\nCLEANUP=600\n", repr(open(f).read()))
        # W9 two sections
        f = self.put("[sd]\nSDSYS=/x\n[other]\nB=1\n[sd]\nGRPSIZE=4\n\n")
        r = self.setk(f, "CLEANUP", "600")
        self.check("W9", "with two [sd] sections the line is added to the LAST one", r.returncode == 0 and open(f).read() == "[sd]\nSDSYS=/x\n[other]\nB=1\n[sd]\nGRPSIZE=4\nCLEANUP=600\n\n", repr(open(f).read()))
        # W10 the .bak
        f = self.put(BASE)
        self.setk(f, "CLEANUP", "600")
        one = open(f).read()
        bak1 = open(f + ".bak").read() if os.path.exists(f + ".bak") else None
        self.setk(f, "CLEANUP", "700")
        two = open(f).read()
        bak2 = open(f + ".bak").read() if os.path.exists(f + ".bak") else None
        ino, mt = os.stat(f).st_ino, os.stat(f).st_mtime_ns
        bmt = stat_of(f + ".bak", "st_mtime_ns")
        r = self.setk(f, "CLEANUP", "700")
        same = open(f).read() == two and os.path.exists(f + ".bak") and open(f + ".bak").read() == one and os.stat(f).st_ino == ino and os.stat(f).st_mtime_ns == mt and stat_of(f + ".bak", "st_mtime_ns") == bmt
        self.check("W10", "THE FILE AS IT WAS IS KEPT AS sd.conf.bak, ONE GENERATION: after the first change .bak is the original, after the second it is the first change's result; a third that changes nothing writes nothing (same file, same .bak, CHANGED=0)",
                   bak1 == BASE and bak2 == one and two != one and same and "CHANGED=0" in r.stdout, "bak1 ok %s, bak2 ok %s, unchanged %s, %s" % (bak1 == BASE, bak2 == one, same, r.stdout.strip()))
        # W11 mode and owner
        for mode in (0o644, 0o600, 0o640):
            f = self.put(BASE, mode)
            log = os.path.join(tmp, "chown.log")
            if os.path.exists(log):
                os.unlink(log)
            r = self.setk(f, "CLEANUP", "600", pre='LOGF=%s\nchown() { printf "%%s\\n" "$*" >> "$LOGF"; command chown "$@"; }' % shlex.quote(log))
            m = stat.S_IMODE(os.stat(f).st_mode)
            bm = stat_of(f + ".bak", "st_mode")
            bm = None if bm is None else stat.S_IMODE(bm)
            calls = open(log).read().strip().split("\n") if os.path.exists(log) else []
            ok_owner = len(calls) == 1 and calls[0].startswith("--reference=%s -- %s." % (f, f))
            self.check("W11", "mode %s is kept on the file and the .bak, and the new file is given the old one's owner (chown --reference=<file> on the temp file, once)" % oct(mode),
                       r.returncode == 0 and m == mode and bm == mode and ok_owner, "exit %d mode %s bak %s chown %r" % (r.returncode, oct(m), "none" if bm is None else oct(bm), calls))
        # W12 temp then rename
        f = self.put(BASE)
        before = os.stat(f).st_ino
        with open(f) as old:
            r = self.setk(f, "CLEANUP", "600")
            still = old.read()
        after = os.stat(f).st_ino
        self.check("W12", "THE WRITE IS A RENAME: the file has a new inode, a reader that had the old file open still sees the old text (an in-place rewrite would change it under the reader), and no temp file is left",
                   r.returncode == 0 and after != before and still == BASE and not self.left(), "inode %d -> %d, reader saw %r, left %s" % (before, after, still[:40], self.left()))
        # W13 refusals about the file
        real = self.put(BASE, name="real.conf")
        link = os.path.join(tmp, "link.conf")
        if os.path.lexists(link):
            os.unlink(link)
        os.symlink(real, link)
        r = self.setk(link, "CLEANUP", "600")
        self.check("W13", "a symlink for the file is refused and its target is untouched", r.returncode == 2 and "not a regular file" in r.stderr and open(real).read() == BASE and not os.path.exists(real + ".bak"), "exit %d %s" % (r.returncode, r.stderr.strip()[:80]))
        r = self.setk(os.path.join(tmp, "absent.conf"), "CLEANUP", "600")
        self.check("W13b", "a missing file is refused and none is made", r.returncode == 2 and not os.path.exists(os.path.join(tmp, "absent.conf")), "exit %d %s" % (r.returncode, r.stderr.strip()[:80]))
        f = self.put(BASE)
        target = self.put("elsewhere\n", name="elsewhere")
        os.symlink(target, f + ".bak")
        r = self.setk(f, "CLEANUP", "600")
        self.check("W13c", "a symlink where the .bak goes is refused: the file is unchanged and the link's target is not overwritten", r.returncode == 2 and "is not a regular file" in r.stderr and open(f).read() == BASE and open(target).read() == "elsewhere\n", "exit %d %s" % (r.returncode, r.stderr.strip()[:80]))
        os.unlink(f + ".bak")
        f = self.put(BASE)
        with open(f, "wb") as fh:
            fh.write(b"[sd]\nSDSYS=/x\n\x00junk\n")
        r = self.setk(f, "CLEANUP", "600")
        self.check("W13d", "a file with a NUL byte in it is refused unchanged (bash would drop the byte)", r.returncode == 2 and "NUL byte" in r.stderr and open(f, "rb").read() == b"[sd]\nSDSYS=/x\n\x00junk\n" and not self.left(), "exit %d %s" % (r.returncode, r.stderr.strip()[:80]))
        # W14 CRLF
        f = self.put("[sd]\r\nSDSYS=/x\r\nCLEANUP=40\r\nGRPSIZE=4\r\n")
        r = self.setk(f, "CLEANUP", "600")
        self.check("W14", "in a file with CRLF line ends every line but the key's is kept byte for byte (the key's new line ends in a plain newline)", r.returncode == 0 and open(f, newline="").read() == "[sd]\r\nSDSYS=/x\r\nCLEANUP=600\nGRPSIZE=4\r\n", repr(open(f, newline="").read()))
        # W15 all fourteen on one realistic file: one line changes at a time, and an independent model of config.c reads every value back
        kinds = {r_[0]: r_[1] for r_ in self.tc.table_rows(self.raw["table"])}
        f = self.put(BASE)
        text = BASE
        ok_each, detail = True, []
        want_vals = {}
        for k in writable:
            lo, hi, _ = helper[k]
            v = str(hi)
            r = self.setk(f, k, v)
            new = open(f).read()
            ops = [o for o in difflib.SequenceMatcher(None, text.split("\n"), new.split("\n")).get_opcodes() if o[0] != "equal"]
            one = len(ops) == 1 and ((ops[0][0] == "insert" and ops[0][4] - ops[0][3] == 1) or (ops[0][0] == "replace" and ops[0][2] - ops[0][1] == 1 and ops[0][4] - ops[0][3] == 1))
            if r.returncode != 0 or not one:
                ok_each = False
                detail.append((k, r.returncode, ops))
            text = new
            want_vals[k] = v
        vals, bad = model_read(text, kinds)
        base_vals, _ = model_read(BASE, kinds)
        self.check("W15", "all %d writable parameters changed one after another on one file: each change adds or replaces exactly one line, and a model of config.c's reader then finds every value, finds nothing unrecognised and finds the file's own other lines unchanged" % len(writable),
                   ok_each and all(vals.get(k) == v for k, v in want_vals.items()) and not bad and all(vals.get(k) == v for k, v in base_vals.items() if k not in want_vals), "%s %s %s" % (detail[:2], bad[:2], {k: vals.get(k) for k in list(want_vals)[:3]}))
        # W16 a change to a parameter the file already has keeps the line count and every other line
        for k in writable[:5]:
            lo, hi, _ = helper[k]
            v2 = str(lo)
            before = text.split("\n")
            r = self.setk(f, k, v2)
            after = open(f).read().split("\n")
            ops = [o for o in difflib.SequenceMatcher(None, before, after).get_opcodes() if o[0] != "equal"]
            self.check("W16", "%s changed again: one line replaced in place (%s), the line count the same" % (k, v2), r.returncode == 0 and len(before) == len(after) and (len(ops) == 1 and ops[0][0] == "replace" or before == after), "%d %d %s" % (len(before), len(after), ops))
            text = "\n".join(after)
        # W17 the caller
        f = self.put(BASE)
        for who, want in ((None, 0), ("sdsys", 0), ("don", 2), ("root", 2), ("sdsys2", 2), ("sd", 2)):
            env = {} if who is None else {"SUDO_USER": who}
            r = self.bash("confset_caller", env=env)
            self.check("W17", "SUDO_USER %s: %s" % ("unset" if who is None else who, "accepted" if want == 0 else "refused"), r.returncode == want and (want == 0 or "sdsys" in r.stderr), "exit %d %s" % (r.returncode, r.stderr.strip()[:80]))
        # W18 a write that did not land is caught by the read-back; a failed copy leaves no temp file and the file untouched
        f = self.put(BASE)
        r = self.setk(f, "CLEANUP", "600", pre="mv() { return 0; }")
        self.check("W18", "a rename that reports success and does nothing is caught by the read-back (exit 2, 'does not read back')", r.returncode == 2 and "does not read back" in r.stderr and open(f).read() == BASE, "exit %d %s" % (r.returncode, r.stderr.strip()[:90]))
        for name in os.listdir(tmp):
            if name.startswith("sd.conf.") and name != "sd.conf.bak":
                os.unlink(os.path.join(tmp, name))
        f = self.put(BASE)
        if os.path.exists(f + ".bak"):
            os.unlink(f + ".bak")
        r = self.setk(f, "CLEANUP", "600", pre="cp() { return 1; }")
        self.check("W19", "a failed copy of the old file (no .bak could be made) stops the write: exit 2, the file unchanged and NO temp file left", r.returncode == 2 and "writing" in r.stderr and open(f).read() == BASE and not self.left(), "exit %d %s left %s" % (r.returncode, r.stderr.strip()[:80], self.left()))

    # ----------------------------------------------------------------------------------------------------------------------------------------- the verb
    def suite_verb(self):
        text = self.script_text
        run = lambda *a: subprocess.run(["bash", self.script_path, "--dry-run", "conf-set"] + list(a), capture_output=True, text=True, timeout=60)
        r = run("CLEANUP", "600")
        self.check("V1", "the real script, --dry-run, CLEANUP 600: exit 0, it prints the command it would run, and does NOT print the success line (' is now ')",
                   r.returncode == 0 and r.stdout.strip() == "sd-elevate: set CLEANUP=600 in /etc/sd.conf" and " is now " not in r.stdout + r.stderr, "exit %d %r %r" % (r.returncode, r.stdout, r.stderr[:80]))
        for name, args, want in (("no argument", [], "exactly two arguments"), ("one argument", ["CLEANUP"], "exactly two arguments"), ("a third argument", ["CLEANUP", "600", "7"], "exactly two arguments"),
                                 ("an empty name", ["", "600"], "no parameter name"), ("an empty value", ["CLEANUP", ""], "no value was given"), ("a fixed name", ["NETFILES", "1"], "conf-set does not change it"),
                                 ("an unknown name", ["ZZNEW", "1"], "is not a parameter SD knows"), ("a value out of range", ["CLEANUP", "29"], "outside the range 30 to 3600"),
                                 ("a lower-case name", ["cleanup", "600"], "capital letter or a digit")):
            r = run(*args)
            self.check("V2", "the real script, --dry-run, %s: exit 2 'REFUSED' and the wording %r, and no success line" % (name, want), r.returncode == 2 and "REFUSED - " in r.stderr and want in r.stderr and " is now " not in r.stdout + r.stderr,
                       "exit %d %r %r" % (r.returncode, r.stdout[:60], r.stderr.strip()[:100]))
        arm = text[text.find("  conf-set)"):]
        arm = arm[:arm.find("\n    ;;") + 8] if arm else ""
        order = [arm.find(s) for s in ("confset_check \"$1\" \"$2\"", "need_root", "confset_caller", "conf_set \"$SD_CONF\" \"$1\" \"$2\"", "printf '%s: %s is now %s in")]
        self.check("V3", "THE ORDER IN THE VERB: the arguments counted, then the names and value checked, the dry run stops, then need_root, then the caller, then the write, then the success line (which only a completed write prints)",
                   arm != "" and all(x > 0 for x in order) and order == sorted(order) and arm.find("[[ $DRY -eq 1 ]] && exit 0") > arm.find("confset_check") and arm.find("[[ $DRY -eq 1 ]] && exit 0") < arm.find("need_root")
                   and arm.find("[[ $# -eq 2 ]] || die") < arm.find("confset_check"), repr(order))
        self.check("V4", "THE FILE IS /etc/sd.conf AND NOTHING A CALLER PASSES MOVES IT: SD_CONF is a plain assignment, the verb takes no file argument, and its conf_set call names $SD_CONF",
                   re.search(r"^SD_CONF=/etc/sd\.conf\s*$", text, re.M) is not None and "SD_CONF=${" not in text and 'conf_set "$SD_CONF" "$1" "$2"' in arm, "")
        sud = open(self.sudoers_path, encoding="utf-8").read()
        sdusers = [l for l in sud.split("\n") if l.startswith("%sdusers")]
        sdsys = [l for l in sud.split("\n") if l.startswith("sdsys")]
        self.check("V5", "NO NEW GRANT: sudoers still gives sdsys the helper and %sdusers four exact argument lists, none of them conf-set (so only sdsys, or root, can reach the verb)",
                   len(sdusers) == 1 and "conf-set" not in sdusers[0] and sdusers[0].count("/usr/local/sbin/sd-elevate ") == 4 and len(sdsys) == 1 and "conf-set" not in sdsys[0], repr((sdusers, sdsys)))
        self.check("V6", "the usage text and the history block name conf-set, and the success line is the only line that says ' is now <value> in ' for it", "conf-set <PARAMETER> <whole number>" in text and "26 Oct 26 dm S.75 A6" in text
                   and arm.count("is now") == 2 and text.count("is now %s in %s%s; takes effect") == 1, "")
        self.check("V7", "the verb logs to syslog like bakdir-set (logger -t sd-elevate 'conf-set: ...'), after the write and before the success line", arm.find("logger -t sd-elevate \"conf-set: ") > arm.find("conf_set \"$SD_CONF\"") and arm.find("logger -t sd-elevate") < arm.find("printf '%s: %s is now"), "")
        # V8 (26 Oct 26, the review of A6): the NON-dry-run arm run for real.  A scratch copy of the whole script has its file constant pointed at a scratch sd.conf and its root test
        # removed (this free check is not root, and the sandbox's shim prints its own success line); nothing else is changed.  The verb must write, keep the .bak and print the
        # success line the sd.conf verb anchors on.  What it still cannot show: the real root, sudo, the owner of /etc/sd.conf.
        f = self.put(BASE)
        if os.path.exists(f + ".bak"):
            os.unlink(f + ".bak")
        run_text = text.replace("SD_CONF=/etc/sd.conf\n", "SD_CONF=%s\n" % f, 1)
        run_text = run_text.replace('  [[ ${EUID:-$(id -u)} -eq 0 ]] || die "must run as root (it is invoked through sudo); use --dry-run to validate"\n', "  :\n", 1)
        os.makedirs(os.path.join(self.tmp, "runcopy"), exist_ok=True)
        rp = os.path.join(self.tmp, "runcopy", "sd-elevate")      # the success line starts with the script's own name
        with open(rp, "w", encoding="utf-8") as fh:
            fh.write(run_text)
        env = {k: v for k, v in os.environ.items() if k != "SUDO_USER"}
        r = subprocess.run(["bash", rp, "conf-set", "CLEANUP", "600"], capture_output=True, text=True, timeout=60, env=env)
        last = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
        wrote = open(f).read() if os.path.exists(f) else ""
        bak = open(f + ".bak").read() if os.path.exists(f + ".bak") else None
        self.check("V8", "the real non-dry-run arm on a scratch copy: exit 0, the success line starts 'sd-elevate: CLEANUP is now 600 in <file>' and ends with 'takes effect: ...', the file has exactly one CLEANUP=600 line "
                   "and every other line as it was, and the .bak is the file as it was",
                   r.returncode == 0 and last.startswith("sd-elevate: CLEANUP is now 600 in %s" % f) and "; takes effect: " in last and wrote.count("CLEANUP=600\n") == 1
                   and bak == BASE and [l for l in wrote.split("\n") if l != "CLEANUP=600"] == BASE.split("\n"),
                   "exit %d last %r stderr %r file %r bak %r" % (r.returncode, last[:90], r.stderr.strip()[:90], wrote[-80:], (bak or "")[:20]))
        # V9: the uninstaller takes the generation the helper keeps away with the file
        dsh = os.path.join(HERE, "..", "..", "..", "deletesdcore.sh")
        dtext = open(dsh, encoding="utf-8").read() if os.path.exists(dsh) else ""
        i1 = dtext.find("sudo rm -f /etc/sd.conf\n")
        i2 = dtext.find("sudo rm -f /etc/sd.conf.bak\n")
        self.check("V9", "deletesdcore.sh removes /etc/sd.conf.bak (the generation conf-set keeps) with /etc/sd.conf, on the path where the configuration is saved to /home/sd and on the path where it is deleted",
                   i1 > 0 and i2 > i1 and dtext.count("sudo rm -f /etc/sd.conf.bak") == 1 and dtext.find("conf_deleted=no") < i1, "%d %d" % (i1, i2))

    def run(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.tmp = os.path.realpath(tmp)
            writable, helper = self.suite_list()
            self.suite_refusals(writable, helper)
            self.suite_write(writable, helper)
            self.suite_verb()


def mutants_of(code, script):
    """(name, kind, old, new, the check that must go red): kind 'code' edits the cut functions, 'script' the whole script text."""
    M = []
    c = lambda name, old, new, want: M.append((name, "code", old, new, want))
    s = lambda name, old, new, want: M.append((name, "script", old, new, want))
    # the list
    c("the list gains NETFILES, a door", "    NUMLOCKS) CS_MIN=1;  CS_MAX=32767;   CS_EFFECT=restart ;;\n", "    NUMLOCKS) CS_MIN=1;  CS_MAX=32767;   CS_EFFECT=restart ;;\n    NETFILES) CS_MIN=0;  CS_MAX=3;       CS_EFFECT=restart ;;\n", "CS1b")
    c("the list gains SDCLIENT, a door", "    SORTMRG)  CS_MIN=2;  CS_MAX=10;      CS_EFFECT=session ;;\n", "    SORTMRG)  CS_MIN=2;  CS_MAX=10;      CS_EFFECT=session ;;\n    SDCLIENT) CS_MIN=0;  CS_MAX=3;       CS_EFFECT=session ;;\n", "CS4")
    c("the list gains PWDELAY, the security throttle (with config.c's own range)", "    NETWAIT)  CS_MIN=1;  CS_MAX=3600;    CS_EFFECT=session ;;\n", "    NETWAIT)  CS_MIN=1;  CS_MAX=3600;    CS_EFFECT=session ;;\n    PWDELAY)  CS_MIN=0;  CS_MAX=3600;    CS_EFFECT=session ;;\n", "CS4")
    c("the security throttle PWDELAY is forgotten (it would read as unknown)", "|PDUMP|PHANTOMS|PORTMAP|PWDELAY|RINGWAIT|", "|PDUMP|PHANTOMS|PORTMAP|RINGWAIT|", "CS1")
    c("a fixed name is forgotten (it would read as unknown)", "|GDI|GRPDIR|INTPREC|", "|GDI|INTPREC|", "CS1")
    c("a writable name loses its limits", "    DHCACHE)  CS_MIN=0;  CS_MAX=1024;    CS_EFFECT=session ;;\n", "", "CS1")
    c("CS_WRITABLE drifts from the limits", 'CS_WRITABLE="CLEANUP DHCACHE ', 'CS_WRITABLE="CLEANUP ', "CS1b")
    c("a range moves up", "CLEANUP)  CS_MIN=30; CS_MAX=3600; ", "CLEANUP)  CS_MIN=30; CS_MAX=36000;", "CS2")
    c("a minimum moves down", "NETWAIT)  CS_MIN=1;  CS_MAX=3600;", "NETWAIT)  CS_MIN=0;  CS_MAX=3600;", "CS2")
    c("GRPSIZE is allowed past config.c's MAX_GROUP_SIZE", "GRPSIZE)  CS_MIN=1;  CS_MAX=8; ", "GRPSIZE)  CS_MIN=1;  CS_MAX=16;", "CS2")
    c("an effect is wrong", "GRPSIZE)  CS_MIN=1;  CS_MAX=8;       CS_EFFECT=session", "GRPSIZE)  CS_MIN=1;  CS_MAX=8;       CS_EFFECT=restart", "CS3")
    # the checks
    c("a lower-case name is let through the character test", "[[ $k =~ ^[A-Z][A-Z0-9]*$ ]]", "[[ $k =~ ^[A-Za-z][A-Za-z0-9]*$ ]]", "CS5")
    c("the character test is gone", '  [[ $k =~ ^[A-Z][A-Z0-9]*$ ]] || die "the parameter name holds a character that is not a capital letter or a digit: sd.conf spells a parameter in capitals (CLEANUP, not cleanup) and SD does not start when it meets a name it does not know"\n', "", "CS5")
    c("the name length limit is gone", '  [[ ${#k} -le 12 ]] || die "the parameter name is longer than any parameter SD has"\n', "", "CS5")
    c("a fixed name is called unknown", "    if confset_fixed \"$k\"; then", "    if false; then", "CS5")
    c("an empty name is not noticed", '  [[ -n $k ]] || die "no parameter name was given"\n', "", "CS5")
    c("an empty value is not noticed", '  [[ -n $v ]] || die "no value was given for $k"\n', "", "CS5")
    c("a sign is let through", "[[ $v =~ ^[0-9]+$ ]]", "[[ $v =~ ^[-+]?[0-9]+$ ]]", "CS5")
    c("the end of the value is not anchored (a newline and a second line pass)", "[[ $v =~ ^[0-9]+$ ]]", "[[ $v =~ ^[0-9]+ ]]", "CS5")
    c("the digit count limit is gone", '  [[ ${#v} -le 7 ]] || die "the value has more than 7 digits"\n', "", "CS5")
    c("a leading zero is let through", '  [[ $v == 0 || $v != 0* ]] || die "the value must not start with a zero"\n', "", "CS5")
    c("the minimum is exclusive", "10#$v >= CS_MIN", "10#$v > CS_MIN", "CS5")
    c("the maximum is exclusive", "10#$v <= CS_MAX", "10#$v < CS_MAX", "CS5")
    c("the range test is gone", '  (( 10#$v >= CS_MIN && 10#$v <= CS_MAX )) || die "$v is outside the range $CS_MIN to $CS_MAX that SD accepts for $k"\n', "", "CS5")
    c("the offending name is echoed before it has passed", 'die "the parameter name holds a character that is not a capital letter', 'die "the parameter name $k holds a character that is not a capital letter', "CS5c")
    # the write
    c("the line is appended at the end of the file, not in [sd]", "    if (( CS_FIRST < 0 && i == CS_AFTER )); then out+=(\"$k=$v\"); fi\n", "    if (( CS_FIRST < 0 && i == CS_N - 1 )); then out+=(\"$k=$v\"); fi\n", "W4")
    c("the section name is compared in lower case only", "      name=${name^^}\n", "", "W8")
    c("a later duplicate is kept", '    elif [[ $CS_DROPS == *" $i "* ]]; then\n      :\n', '    elif false; then\n      :\n', "W3")
    c("a line of another section counts", "    (( insd )) || continue\n    CS_AFTER=$i\n", "    CS_AFTER=$i\n", "W4")
    c("the mode is not kept", "&& chmod --reference=\"$f\" -- \"$tmp\" \\\n", "\\\n", "W11")
    c("the owner is not kept", "chown --reference=\"$f\" -- \"$tmp\" && chmod --reference", "chmod --reference", "W11")
    c("no .bak is made", "    && cp -p -- \"$f\" \"$bak\" \\\n", "\\\n", "W10")
    c("the .bak is made from the new file", "    && cp -p -- \"$f\" \"$bak\" \\\n    && mv -f -- \"$tmp\" \"$f\" \\\n", "    && mv -f -- \"$tmp\" \"$f\" \\\n    && cp -p -- \"$f\" \"$bak\" \\\n", "W10")
    c("the file is rewritten in place", "    && mv -f -- \"$tmp\" \"$f\" \\\n", "    && cat -- \"$tmp\" > \"$f\" \\\n", "W12")
    c("an unchanged value is written again", "  if cmp -s -- \"$tmp\" \"$f\"; then\n    rm -f -- \"$tmp\"\n    return 0\n  fi\n", "", "W10")
    c("the read-back is gone", "  [[ $CS_COUNT -eq 1 && $CS_N -eq ${#out[@]} && ${CS_L[CS_FIRST]} == \"$k=$v\" ]] || die \"$f does not read back as written (the file as it was is $bak)\"\n  for (( i = 0; i < CS_N; i++ )); do\n    [[ ${CS_L[i]} == \"${out[i]}\" ]] || die \"$f does not read back as written (the file as it was is $bak)\"\n  done\n", "", "W18")
    c("a symlink for the file is followed", "  [[ -f $f && ! -L $f ]] || die \"$f is not a regular file\"\n  if", "  [[ -f $f ]] || die \"$f is not a regular file\"\n  if", "W13")
    c("a symlink for the .bak is followed", "    [[ -f $bak && ! -L $bak ]] || die \"$bak is not a regular file\"\n", "    :\n", "W13c")
    c("a NUL byte is not looked for", "  tr -d '\\000' < \"$f\" | cmp -s -- - \"$f\" || die \"$f holds a NUL byte, so it is not rewritten\"\n", "", "W13d")
    c("a file with no [sd] section is accepted", "  (( CS_AFTER >= 0 )) || die \"$f has no [sd] section, so there is nowhere to put $k\"\n", "", "W7")
    c("the temp file is left when the write fails", "    || { rm -f -- \"$tmp\"; die \"writing $f failed\"; }\n  confset_scan", "    || { die \"writing $f failed\"; }\n  confset_scan", "W19")
    c("any caller is accepted", "  [[ -z ${SUDO_USER:-} || ${SUDO_USER:-} == sdsys ]] || die", "  true || die", "W17")
    c("a caller that begins with sdsys is accepted", "${SUDO_USER:-} == sdsys ]]", "${SUDO_USER:-} == sdsys* ]]", "W17")
    # the script
    s("the verb does not count its arguments", '    [[ $# -eq 2 ]] || die "conf-set takes exactly two arguments', '    true || die "conf-set takes exactly two arguments', "V2")
    s("the verb writes before it asks who the caller is", "    need_root\n    confset_caller\n    conf_set \"$SD_CONF\" \"$1\" \"$2\"", "    need_root\n    conf_set \"$SD_CONF\" \"$1\" \"$2\"\n    confset_caller", "V3")
    s("the verb forgets to check the names", "    confset_check \"$1\" \"$2\"\n    printf '%s: set %s=%s in %s\\n'", "    printf '%s: set %s=%s in %s\\n'", "V2")
    s("the dry run writes", "    [[ $DRY -eq 1 ]] && exit 0\n    need_root\n    confset_caller", "    need_root\n    confset_caller", "V3")
    s("the file can be moved from the environment", "SD_CONF=/etc/sd.conf\n", "SD_CONF=${SD_CONF:-/etc/sd.conf}\n", "V4")
    s("sudoers is widened to the users group", "%sdusers ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate cred-own query,", "%sdusers ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate conf-set, /usr/local/sbin/sd-elevate cred-own query,", "V5")
    s("the success line is printed before the write", "    conf_set \"$SD_CONF\" \"$1\" \"$2\"\n    cs_note=''", "    printf '%s: %s is now %s in %s%s; takes effect: %s\\n' \"$PROG\" \"$1\" \"$2\" \"$SD_CONF\" '' \"$CS_EFFECT\"\n    conf_set \"$SD_CONF\" \"$1\" \"$2\"\n    cs_note=''", "V3")
    s("the syslog line is gone", "    logger -t sd-elevate \"conf-set: $1 is now $2 in $SD_CONF$cs_note\" 2>/dev/null || true\n", "", "V7")
    # 26 Oct 26 (the review of A6): the arm run for real (V8)
    s("the arm hands the write the value for the name", "    need_root\n    confset_caller\n    conf_set \"$SD_CONF\" \"$1\" \"$2\"\n    cs_note=''", "    need_root\n    confset_caller\n    conf_set \"$SD_CONF\" \"$2\" \"$1\"\n    cs_note=''", "V8")
    s("the success line is not the one the verb anchors on", "    printf '%s: %s is now %s in %s%s; takes effect: %s\\n' \"$PROG\" \"$1\" \"$2\" \"$SD_CONF\" \"$cs_note\" \"$CS_EFFECT\"", "    printf '%s: %s set to %s in %s%s; takes effect: %s\\n' \"$PROG\" \"$1\" \"$2\" \"$SD_CONF\" \"$cs_note\" \"$CS_EFFECT\"", "V8")
    return M


def selftest(code, script, raw, tc, only_from=0):
    M = mutants_of(code, script)
    bad = 0
    for n, (name, kind, old, new, want) in enumerate(M):
        if n < only_from:
            continue
        on_sudoers = kind == "script" and name.startswith("sudoers")
        base_text = code if kind == "code" else (open(SUDOERS, encoding="utf-8").read() if on_sudoers else script)
        if base_text.count(old) != 1:
            print("REFUSED: mutant '%s' could not be applied (the text appears %d times)" % (name, base_text.count(old)), file=sys.stderr)
            return 2
        mutated = base_text.replace(old, new)
        with tempfile.TemporaryDirectory() as d:
            sc = Suite(code, script, raw, tc)
            sc.quiet = True
            if kind == "code":
                sc.code = mutated
            elif on_sudoers:
                sc.sudoers_path = os.path.join(d, "sdcore.sudoers")
                with open(sc.sudoers_path, "w") as fh:
                    fh.write(mutated)
            else:
                p = os.path.join(d, "sd-elevate")
                with open(p, "w") as fh:
                    fh.write(mutated)
                sc.script_path = p
                sc.script_text = mutated
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    sc.run()
            except Exception as exc:        # a mutant may break a later scenario outright; the checks that ran before it still count
                print("    (the suite stopped on mutant %d: %s: %s)" % (n, type(exc).__name__, exc))
        hit = want in sc.failed_ids
        print("  mutant %2d '%s': %s (must fail %s; failed %s)" % (n, name, "CAUGHT" if hit else "NOT CAUGHT", want, " ".join(sorted(set(sc.failed_ids))) or "none"))
        bad += 0 if hit else 1
    print("selftest: %d mutants, %d not caught" % (len(M) - only_from, bad))
    return 0 if bad == 0 else 1


def main(argv):
    with open(ELEVATE, encoding="utf-8") as f:
        script = f.read()
    code = cut_code(script)
    tc = load_module("toolconfig_units_for_confset", "test-toolconfig-units.py")
    raw = tc.load()
    print("test-confset-elevate-units inputs:")
    print("  sd-elevate : %s  (%d lines between '%s' and '%s')" % (ELEVATE, len(code.split("\n")), BEGIN, END))
    print("  config.c   : %s" % tc.FILES["configc"])
    print("  table      : %s" % tc.FILES["table"])
    print("  bash       : %s" % subprocess.run(["bash", "--version"], capture_output=True, text=True).stdout.split("\n")[0])
    if "confset_check" not in code or "conf_set" not in code or not raw["configc"] or not raw["table"]:
        print("REFUSED: the cut code or config.c or the table is missing; nothing could be measured", file=sys.stderr)
        return 2
    if os.geteuid() == 0:
        print("REFUSED: run it as an ordinary user (it plays root itself)", file=sys.stderr)
        return 2
    if "--selftest" in argv:
        n = 0
        for a in argv:
            if a.startswith("--from="):
                n = int(a.split("=", 1)[1])
        return selftest(code, script, raw, tc, n)
    if [a for a in argv if a not in ("--selftest",)]:
        print("usage: %s [--selftest [--from=N]]" % sys.argv[0], file=sys.stderr)
        return 2
    s = Suite(code, script, raw, tc)
    s.run()
    print("\ntest-confset-elevate-units: %d passed, %d failed" % (s.checks - s.failed, s.failed))
    if s.checks == 0:
        print("REFUSED: no check ran", file=sys.stderr)
        return 2
    return 0 if s.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
