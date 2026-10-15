#!/usr/bin/env python3
#
# test-clientheaders-units.py - the client library's language headers all declare the functions the library has, with the
# parameters it has.  Read off the source.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-clientheaders-units.py [--selftest] [--lib <dir with sdclilib.so>]
#
# No sudo, no install, no sd.  Exit 0 every check held, 1 one did not, 2 it could not run.  --selftest plants faults in a copy
# of the headers (a function taken out of each language, a parameter added, a function the library does not have, a library
# function with no header entry) and expects each to be caught.
#
# START-HISTORY:
# 15 Oct 26 dm  Written when the QMClient work (SDRevision, SDGetVar, SDSystem, SDIndices, SDTrans, SDRTrans, SDTxn,
#               SDEvaluate, SDEvalConv, SDIConv, SDOConv, SDIConvs, SDOConvs) was found to have reached the C, Basic and
#               PureBasic headers only; the owner's Gambas 3, Free Pascal and Python definitions were added to syscom the same
#               day.  Six files now say the same thing in six languages, and nothing but this check ties them together.
# END-HISTORY
#
# THE AUTHORITY is gplsrc/sdclilib.h, which this check holds against the DLLEntry functions of gplsrc/sdclilib.c.  Each of
# the six headers under sdsys/syscom is then compared with it:
#     sdclilib.h       the C header                       every function but the two package functions
#     sdclient.bas     the Basic (VB) header              the same, but not SDCallx, SDGetArg, SDDebug and SDFree (the VB DLL has none)
#     sdclient.pb      PureBasic                          every function but the two package functions and SDFree, which its
#                                                         procedures call themselves (SDCall and SDCallx are SDCall0 to
#                                                         SDCall20 and SDCallx0 to SDCallx20)
#     sdclient.module  Gambas 3                           the same
#     sdclilibbind.pas Free Pascal: types, variables and the loader's Sym() calls all name the same functions
#     sdclient.py      Python (ctypes)                    the same, with argtypes and restype for each
# SDEnterPackage and SDExitPackage are not declared in any header: the owner ruled licensed packages out (15 Oct 2026) and the
# server answers them as unsupported.  The parameter COUNT of each function is compared too (SDCall and SDCallx take a list
# without end and are left out), with the two the Gambas header gives one more parameter, an ErrNo the library ignores.
# If bin/sdclilib.so is newer than gplsrc/sdclilib.c the Python header is also loaded against it and must bind every function.

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)

LIB_DIR = None
NO_PACKAGES = {"SDEnterPackage", "SDExitPackage"}
NOT_IN_VB = {"SDCallx", "SDGetArg", "SDDebug", "SDFree"}      # the VB DLL hands back strings VB owns
NOT_IN_PB = {"SDFree"}                                          # sdclient.pb frees what the library returns itself
VARARGS = {"SDCall", "SDCallx"}
GAMBAS_EXTRA = {"SDReadList": 1, "SDReadNext": 1}
FILES = ["gplsrc/sdclilib.h", "gplsrc/sdclilib.c", "sdsys/syscom/sdclilib.h", "sdsys/syscom/sdclient.bas", "sdsys/syscom/sdclient.pb",
         "sdsys/syscom/sdclient.module", "sdsys/syscom/sdclilibbind.pas", "sdsys/syscom/sdclient.py"]


def top_count(params):
    """Number of top-level, comma separated items."""
    params = params.strip()
    if params in ("", "void"):
        return 0
    depth = n = 0
    for ch in params:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            n += 1
    return n + 1


def read(tree, rel):
    with open(os.path.join(tree, rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_c(text, prefix):
    out = {}
    for m in re.finditer(r"^%s\s+[^;(\n]*?\b(SD\w+)\s*\(([^)]*)\)\s*;" % prefix, text, re.M):
        out[m.group(1)] = top_count(m.group(2))
    return out


def parse_pascal(text):
    types = {}
    for m in re.finditer(r"T(SD\w+)Fn = (?:function|procedure)\s*(?:\(([^)]*)\))?[^;]*;", text, re.S):
        params = m.group(2) or ""
        n = 0
        for grp in params.split(";"):
            if ":" in grp:
                n += len([x for x in grp.split(":")[0].split(",") if x.strip()])
        types[m.group(1)] = n
    variables = set(re.findall(r"^  (SD\w+): T\1Fn;", text, re.M))
    syms = set(re.findall(r"T(SD\w+)Fn\(Sym\('(SD\w+)'\)\)", text))
    sym_ok = {a for a, b in syms if a == b}
    return types, variables, sym_ok


def parse_python(text):
    names = set(re.findall(r"^(SD\w+) = _lib\.\1\s*$", text, re.M))
    argc = {}
    for m in re.finditer(r"^(SD\w+)\.argtypes = \[(.*)\]\s*$", text, re.M):
        argc[m.group(1)] = top_count(m.group(2))
    rest = set(re.findall(r"^(SD\w+)\.restype = ", text, re.M))
    return names, argc, rest


def run_checks(tree):
    """Returns a list of (name, ok, detail)."""
    res = []

    def row(name, ok, detail=""):
        res.append((name, bool(ok), detail))

    def same(name, got, want, what):
        miss, extra = sorted(want - got), sorted(got - want)
        row(name, not miss and not extra, "%s missing: %s; not in the library: %s" % (what, miss, extra) if (miss or extra) else "")

    h = parse_c(read(tree, "gplsrc/sdclilib.h"), "SD_API")
    c = set(re.findall(r"DLLEntry\s+(SD\w+)\s*\(", read(tree, "gplsrc/sdclilib.c")))
    row("0 the authority has functions (not an empty parse)", len(h) > 40, "%d parsed from gplsrc/sdclilib.h" % len(h))
    same("1 gplsrc/sdclilib.h declares every function gplsrc/sdclilib.c defines with DLLEntry, and no other", set(h), c, "header")
    want = set(h) - NO_PACKAGES

    sh = parse_c(read(tree, "sdsys/syscom/sdclilib.h"), "DLLEntry")
    same("2 syscom/sdclilib.h (C)", set(sh), want, "names")
    bad = sorted(n for n in sh if n in h and n not in VARARGS and sh[n] != h[n])
    row("2 ... and each takes the number of parameters the library's header gives it", not bad,
        "differs: %s" % [(n, sh[n], h[n]) for n in bad])

    bas = set(re.findall(r"^Declare (?:Sub|Function) (SD\w+) Lib ", read(tree, "sdsys/syscom/sdclient.bas"), re.M))
    same("3 syscom/sdclient.bas (Basic, the VB DLL)", bas, want - NOT_IN_VB, "names")

    pbt = read(tree, "sdsys/syscom/sdclient.pb")
    pbd, pbc = {}, {}
    for m in re.finditer(r"^Declare(?:\.\w)? (SD\w+?)(\d*)\(([^)]*)\)", pbt, re.M):
        if m.group(1) in VARARGS and m.group(2) != "":
            pbc.setdefault(m.group(1), set()).add(int(m.group(2)))
        else:
            pbd[m.group(1) + m.group(2)] = top_count(m.group(3))
    pbp = set(re.findall(r"^Procedure(?:\.\w)? (SD\w+)\(", pbt, re.M))
    pbnames = set(pbd) | set(pbc)
    same("4 syscom/sdclient.pb (PureBasic) Declare lines", pbnames, want - NOT_IN_PB, "names")
    row("4 ... SDCall and SDCallx are each declared for 0 to 20 arguments", all(pbc.get(v) == set(range(21)) for v in VARARGS),
        {v: sorted(pbc.get(v, [])) for v in VARARGS})
    procs = {re.sub(r"^(SDCallx?)\d+$", r"\1", n) for n in pbp}
    same("4 ... every Declare has its Procedure and every Procedure its Declare", procs, pbnames, "procedures")
    bad = sorted(n for n in pbd if n in h and pbd[n] != h[n])
    row("4 ... each takes the number of parameters the library's header gives it", not bad, "differs: %s" % [(n, pbd[n], h[n]) for n in bad])

    gb = {}
    for m in re.finditer(r"^(?:Private )?Extern (SD\w+)\((.*)\)(?: As \w+)?\s*$", read(tree, "sdsys/syscom/sdclient.module"), re.M):
        gb[m.group(1)] = top_count(m.group(2))
    same("5 syscom/sdclient.module (Gambas 3)", set(gb), want, "names")
    bad = sorted(n for n in gb if n in h and n not in VARARGS and gb[n] != h[n] + GAMBAS_EXTRA.get(n, 0))
    row("5 ... and each takes the number of parameters the library has (SDReadList and SDReadNext carry an ErrNo it ignores)",
        not bad, "differs: %s" % [(n, gb[n], h[n]) for n in bad])

    types, variables, syms = parse_pascal(read(tree, "sdsys/syscom/sdclilibbind.pas"))
    same("6 syscom/sdclilibbind.pas (Free Pascal) types", set(types), want, "names")
    same("6 ... the pointer variables", variables, want, "names")
    same("6 ... the loader binds each one by the library's own name (Sym)", syms, want, "names")
    bad = sorted(n for n in types if n in h and n not in VARARGS and types[n] != h[n])
    row("6 ... each takes the number of parameters the library's header gives it", not bad, "differs: %s" % [(n, types[n], h[n]) for n in bad])

    names, argc, rest = parse_python(read(tree, "sdsys/syscom/sdclient.py"))
    same("7 syscom/sdclient.py (Python)", names, want, "names")
    same("7 ... each has its argtypes", set(argc), want, "names")
    same("7 ... and its restype", rest, want, "names")
    bad = sorted(n for n in argc if n in h and n not in VARARGS and argc[n] != h[n])
    row("7 ... each takes the number of parameters the library's header gives it", not bad, "differs: %s" % [(n, argc[n], h[n]) for n in bad])

    # the two C headers must at least be C
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc:
        for rel in ("gplsrc/sdclilib.h", "sdsys/syscom/sdclilib.h"):
            r = subprocess.run([cc, "-fsyntax-only", "-x", "c", os.path.join(tree, rel)], capture_output=True, text=True)
            row("8 %s is valid C" % rel, r.returncode == 0, r.stderr[:300])
    else:
        row("8 the C headers are valid C (no C compiler here: not run)", True, "skipped")

    # the Python header against a library built from this source
    lib = os.path.join(LIB_DIR or os.path.join(tree, "bin"), "sdclilib.so")
    src = os.path.join(tree, "gplsrc", "sdclilib.c")
    if os.path.isfile(lib) and os.path.isfile(src) and (LIB_DIR or os.path.getmtime(lib) >= os.path.getmtime(src)):
        code = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('c', sys.argv[1]); m = importlib.util.module_from_spec(s);"
                "s.loader.exec_module(m); print('BOUND', len([n for n in dir(m) if n.startswith('SD') and not n.endswith('_type')"
                " and hasattr(getattr(m, n), 'argtypes')]))")
        r = subprocess.run([sys.executable, "-I", "-B", "-c", code, os.path.join(tree, "sdsys/syscom/sdclient.py")], cwd=os.path.dirname(lib),
                           capture_output=True, text=True)
        m = re.search(r"BOUND (\d+)", r.stdout)
        row("9 sdclient.py loads against the built bin/sdclilib.so and binds every function in the header",
            m is not None and int(m.group(1)) == len(want), (r.stdout + r.stderr)[-300:])
    else:
        row("9 (bin/sdclilib.so is missing or older than gplsrc/sdclilib.c: the Python header was not loaded against it)", True, "skipped")
    return res


def report(res):
    failed = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "   <- " + detail))
        failed += (not ok)
    return failed


def mutate_copy(tree, edits):
    """A copy of the files this check reads, each edit being (file, old, new) that must match exactly once."""
    d = tempfile.mkdtemp(prefix="clienthdr-")
    for rel in FILES:
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        shutil.copy(os.path.join(tree, rel), os.path.join(d, rel))
    for rel, old, new in edits:
        p = os.path.join(d, rel)
        t = open(p, encoding="utf-8").read()
        if t.count(old) != 1:
            shutil.rmtree(d)
            raise SystemExit("selftest: %r appears %d times in %s" % (old, t.count(old), rel))
        open(p, "w", encoding="utf-8").write(t.replace(old, new))
    return d


def selftest():
    cases = [
        ("a function taken out of the C header", [("sdsys/syscom/sdclilib.h", "DLLEntry char * SDRevision(void);\n", "")], "2 "),
        ("a parameter added to a function in the C header", [("sdsys/syscom/sdclilib.h", "SDTxn(int mode)", "SDTxn(int mode, int extra)")], "2 "),
        ("a function taken out of the Basic header", [("sdsys/syscom/sdclient.bas", "Declare Function SDRevision Lib \"SDClient.dll\" () As String\n", "")], "3 "),
        ("a Procedure taken out of the PureBasic header", [("sdsys/syscom/sdclient.pb", "Procedure.s SDRevision()", "Procedure.s SDRevisionX()")], "4 "),
        ("SDCallx19 taken out of PureBasic", [("sdsys/syscom/sdclient.pb", "Declare SDCallx19(", "Declare SDCallxZ(")], "4 "),
        ("a parameter taken out of a Gambas function", [("sdsys/syscom/sdclient.module", "Extern SDTxn(Mode As Integer)", "Extern SDTxn()")], "5 "),
        ("a function the library has not, in Gambas", [("sdsys/syscom/sdclient.module", "Extern SDTxn(Mode As Integer)",
                                                     "Extern SDTxn(Mode As Integer)\nExtern SDBogus(Mode As Integer)")], "5 "),
        ("the loader forgets a function in Pascal", [("sdsys/syscom/sdclilibbind.pas", "  SDTxn := TSDTxnFn(Sym('SDTxn'));\n", "")], "6 "),
        ("a Pascal type of the wrong arity", [("sdsys/syscom/sdclilibbind.pas", "TSDTxnFn = procedure(Mode: LongInt); cdecl;",
                                              "TSDTxnFn = procedure(Mode, Two: LongInt); cdecl;")], "6 "),
        ("a Python binding taken out", [("sdsys/syscom/sdclient.py", "SDRevision = _lib.SDRevision\n", "")], "7 "),
        ("a Python restype taken out", [("sdsys/syscom/sdclient.py", "SDTxn.restype = None\n", "")], "7 "),
        ("a function added to the library and not to the headers", [("gplsrc/sdclilib.c", "SDRevision(void) {", "SDRevision(void) {}\nvoid DLLEntry SDNewThing(void) {")], "1 "),
    ]
    ok_all = True
    print("selftest: the unmutated copy first (it must pass)")
    d = mutate_copy(SD64, [])
    try:
        res = run_checks(d)
    finally:
        shutil.rmtree(d)
    f = [r for r in res if not r[1]]
    print("  [%s] control: %d rows, %d failing" % ("PASS" if not f else "FAIL", len(res), len(f)))
    ok_all &= not f
    for name, edits, want in cases:
        d = mutate_copy(SD64, edits)
        try:
            res = run_checks(d)
        finally:
            shutil.rmtree(d)
        hit = [r for r in res if not r[1] and r[0].startswith(want)]
        print("  [%s] %s: %s" % ("PASS" if hit else "FAIL", name, "caught by row %s" % hit[0][0][:2] if hit else "NOT CAUGHT"))
        ok_all &= bool(hit)
    return 0 if ok_all else 1


def main():
    global LIB_DIR
    if "--lib" in sys.argv:
        LIB_DIR = os.path.abspath(sys.argv[sys.argv.index("--lib") + 1])    # a sandbox's sys/bin, say, whatever its age
    if "--selftest" in sys.argv:
        return selftest()
    for rel in FILES:
        if not os.path.isfile(os.path.join(SD64, rel)):
            print("test-clientheaders-units: %s is missing" % rel)
            return 2
    print("test-clientheaders-units: tree %s" % SD64)
    failed = report(run_checks(SD64))
    print("\ntest-clientheaders-units: %s" % ("every check held" if not failed else "%d failed" % failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
