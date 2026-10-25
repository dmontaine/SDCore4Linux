#!/usr/bin/env python3
# test-auditjournal-units.py - W.11 F4, option B (24 Oct 2026, the owner: "b then c"): every audit record is ALSO sent to the system journal, whose daemon
# stamps the sender's real uid and pid, which the sender cannot choose.  FREE CHECK, text only (comments removed), no install, no sudo, no sd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-auditjournal-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-auditjournal-units.py --selftest      (mutants)
#
#   J1  k_error.c includes <syslog.h>
#   J2  audit_message() makes exactly one syslog() call: facility LOG_AUTHPRIV, level LOG_NOTICE, the format "sd-audit %s" (the record is an ARGUMENT, never the format)
#   J3  it is made AFTER EndExclusive(ERRLOG_SEM): a stalled syslog socket must not hold the semaphore every session's audit and error logging waits on
#   J4  it is made whether or not the file could be opened or written (the copy is the point when the file is not available), guarded only by "bytes > 0"
#   J5  the record's trailing newline is removed first, and the text is the SAME buffer the file got (one record, two places)
# NOT SAID HERE: that the journal holds the record with the right _UID and _PID - that is sandbox-auditjournal.py.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "gplsrc"))
F = os.environ.get("AJ_KERROR", os.path.join(SRC, "k_error.c"))
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def code(path):
    s = open(path, encoding="latin-1").read()
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def func(src, head):
    m = re.search(re.escape(head) + r"[^;{]*\{.*?\n\}", src, re.S)
    return m.group(0) if m else ""


def run():
    k = code(F)
    row("J1 k_error.c includes <syslog.h>", "#include <syslog.h>" in k)
    am = func(k, "void audit_message(char* msg)")
    row("J0 audit_message() is found", bool(am))
    calls = re.findall(r"\bsyslog\s*\(([^;]*)\);", am)
    row("J2 audit_message() makes exactly one syslog() call: LOG_AUTHPRIV | LOG_NOTICE, the format \"sd-audit %s\", the record as an argument",
        len(calls) == 1 and re.fullmatch(r'\s*LOG_AUTHPRIV\s*\|\s*LOG_NOTICE\s*,\s*"sd-audit %s"\s*,\s*buff\s*', calls[0]) is not None, "calls: %r" % (calls,))
    i_end, i_sys = am.find("EndExclusive(ERRLOG_SEM);"), am.find("syslog(")
    row("J3 the syslog() call comes after EndExclusive(ERRLOG_SEM), not while the semaphore is held", 0 <= i_end < i_sys, "EndExclusive at %d, syslog at %d" % (i_end, i_sys))
    tail = am[i_end:] if i_end >= 0 else ""
    row("J4 and it is made whether or not the file was written: guarded only by 'bytes > 0', outside the open/write branch",
        re.search(r"EndExclusive\(ERRLOG_SEM\);\s*if \(bytes > 0\) \{\s*buff\[bytes - 1\] = '\\0';\s*syslog\(", tail) is not None, tail[:200])
    row("J5 the trailing newline is removed before the record goes to the journal", "buff[bytes - 1] = '\\0';" in tail)
    i_write, i_nul = am.find("write(fd, buff, bytes)"), am.find("buff[bytes - 1] = '\\0';")
    row("J5b and the file got the record WITH its newline first (the file write precedes the cut)", 0 <= i_write < i_nul, "write at %d, cut at %d" % (i_write, i_nul))
    print("test-auditjournal-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


MUTANTS = [
    ("no-syslog-call", '  syslog(LOG_AUTHPRIV | LOG_NOTICE, "sd-audit %s", buff);\n', ""),
    ("wrong-facility", "syslog(LOG_AUTHPRIV | LOG_NOTICE,", "syslog(LOG_LOCAL1 | LOG_NOTICE,"),
    ("record-as-format", 'syslog(LOG_AUTHPRIV | LOG_NOTICE, "sd-audit %s", buff);', "syslog(LOG_AUTHPRIV | LOG_NOTICE, buff);"),
    ("no-prefix", '"sd-audit %s"', '"%s"'),
    ("inside-the-semaphore", "  EndExclusive(ERRLOG_SEM);\n\n  if (bytes > 0) {", "  if (bytes > 0) {"),
    ("only-when-file-written", "      if (write(fd, buff, bytes) != bytes) {\n        /* silent - see the banner */\n      }\n      close(fd);",
     "      if (write(fd, buff, bytes) == bytes) {\n        syslog(LOG_AUTHPRIV | LOG_NOTICE, \"sd-audit %s\", buff);\n      }\n      close(fd);"),
    ("newline-kept", "    buff[bytes - 1] = '\\0';\n", ""),
    ("include-gone", "#include <syslog.h>\n", ""),
]


def selftest():
    import shutil
    t = tempfile.mkdtemp()
    caught = missed = 0
    real = open(F, encoding="latin-1").read()
    print("selftest: the real file first (must pass), then mutants (each must not)")
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] the real file does not pass:\n" + r.stdout[-600:])
        return 1
    print("  [ok] the real file passes")
    for name, old, new in MUTANTS:
        if old not in real:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            continue
        f = os.path.join(t, name + ".c")
        open(f, "w", encoding="latin-1").write(real.replace(old, new, 1))
        env = dict(os.environ, AJ_KERROR=f)
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print("  [caught] %s (exit %d)" % (name, r.returncode))
            caught += 1
        else:
            print("  [MISSED] %s: the check still passed" % name)
            missed += 1
    shutil.rmtree(t, ignore_errors=True)
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 and caught > 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
