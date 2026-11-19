#!/usr/bin/env python3
"""sandbox-examples.py - the example programs: LOAD.EXAMPLES gives an account its own examples.bp, compiled, and an ordinary account uses it.

    SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-examples.py <dir> [--build] [--only=load,self,reach,run,remove]

19 Nov 2026 (the owner: "wouldnt it be easier to just have the user load the examples rather than do it for every account.  most accounts will not
need the examples"; of bp.edit, "respect the gate"): nothing loads every account; the administrator's no-name form is SDSYS alone, a list loads the
accounts named, and a person loads their own with bp.edit (section self).

No install, no sudo; <dir> a SHORT path under /tmp.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  (17 Nov 2026; the owner: "there should be
a examples.bp file available to all users that contains those programs and a set of training programs typical for a Computer Science 101 course", then, asked
how every account reaches it, "A copy in every account" - the shared account serves no program file and an outside F-pointer meets the OS gate.)

The fixture accounts are sandbox-home.py's (zzhd zzhm zzht zzhv in service, zzhs SUSPENDED).  Sections (load and its rows always run first):
  load   LOAD.EXAMPLES as the administrator: with no name SDSYS alone and no other account; a list zzhd zzhm zzht zzhs loads the three in service
         and not the suspended one; the counts, every record equal to its shipped file, every program compiled (its object in examples.bp.out), a
         second run changes and compiles nothing, a program the administrator added is kept and a shipped one changed by hand is put back,
         LOAD.EXAMPLES NAME does that account only
  self   the person loads their own (zzhv): refused (11408) with bp.edit off and nothing made, naming an account refused (2001), with bp.edit on
         their own account only, compiled, and a program runs
  reach  an ORDINARY fixture account (zzhd): its VOC holds examples.bp as its own file, COUNT counts the programs, RUN examples.bp NAME runs one where
         it is, COPY to its own bp, BASIC and RUN give the same; it cannot write into examples.bp (bp.edit off as delivered)
  remove REMOVE.EXAMPLES with a list, with an unregistered name; the administrator's own program kept with its file; LOAD.EXAMPLES with a list;
         the person's own (2001 naming another, 11408 without bp.edit, their account only with it); the administrator's no-name form SDSYS alone
  run    every training program, run from the ordinary account, against an answer this suite works out in Python (fizzbuzz, the primes, the
         gcds, the sorts, the searches...), lines compared with runs of spaces made one; cs03 and cs21 with input on the pipe; cs20 makes and removes
         its file in zzhd; cs22 depends on today, so only its shape is held
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sandbox_docs_for_examples", os.path.join(HERE, "sandbox-docs.py"))
dm = importlib.util.module_from_spec(spec)
sys.modules["sandbox_docs_for_examples"] = dm
spec.loader.exec_module(dm)
sh, g = dm.sh, dm.g
say, row, bail, has, adm = sh.say, sh.row, sh.bail, sh.has, sh.adm

SRC = os.path.join(HERE, os.pardir, "sdsys", "examples")
ONLY = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--only=")), None)


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def shipped():
    return sorted(n for n in os.listdir(SRC) if os.path.isfile(os.path.join(SRC, n)))


INSERVICE = ("zzhd", "zzhm", "zzht", "zzhv")
LISTED = ("zzhd", "zzhm", "zzht")                   # 19 Nov 26: the accounts the administrator's list loads; zzhv is left to its person (self)


def adir(acct):
    return sh.SYS if acct == "sdsys" else os.path.join(sh.BOX, "user_accounts", acct)


def xbp(name="", acct="zzhd"):
    return os.path.join(adir(acct), "examples.bp", name)


def load(acct=""):
    return adm(("load.examples " + acct).strip())


def counts(out):
    """(accounts, new, changed, same) and (compiled, tried, kept), or None"""
    a = b = None
    for l in out:
        m = re.match(r"^Example programs in examples\.bp of (\d+) account\(s\): (\d+) new, (\d+) changed, (\d+) the same$", l)
        if m:
            a = tuple(int(x) for x in m.groups())
        m = re.match(r"^Compiled (\d+) of the (\d+) that were new, changed or not yet compiled; programs added by the administrator, kept: (\d+)$", l)
        if m:
            b = tuple(int(x) for x in m.groups())
    return a, b


def contains(out, want):
    """want (lines) appears in out as consecutive lines, runs of spaces made one and blank lines left out of both"""
    o = [norm(l) for l in out if l.strip()]
    w = [norm(l) for l in want if l.strip()]
    for i in range(len(o) - len(w) + 1):
        if o[i:i + len(w)] == w:
            return True
    return False


def user(cmds):
    return g.plain("zzhd", cmds)


# ------------------------------------------------------------------------------------------------- the answers, worked out here

def fizzbuzz():
    return ["FizzBuzz" if n % 15 == 0 else "Fizz" if n % 3 == 0 else "Buzz" if n % 5 == 0 else str(n) for n in range(1, 31)]


def primes(limit=100):
    return [n for n in range(2, limit + 1) if all(n % d for d in range(2, int(n ** 0.5) + 1))]


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def bubble(vals):
    a = list(vals)
    passes = 0
    while True:
        swapped = False
        for i in range(len(a) - 1):
            if a[i] > a[i + 1]:
                a[i], a[i + 1] = a[i + 1], a[i]
                swapped = True
        passes += 1
        if not swapped:
            break
    return a, passes


def binary_looks(lst, want):
    lo, hi, looks = 1, len(lst), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        looks += 1
        if lst[mid - 1] == want:
            return mid, looks
        if lst[mid - 1] < want:
            lo = mid + 1
        else:
            hi = mid - 1
    return 0, looks


def expected():
    e = {}
    e["cs01.hello"] = ["Hello, world!", "This is SD BASIC.", "One plus one is 2"]
    e["cs02.variables"] = ["apples + pears = 12", "2 + 3 * 4 = 14", "(2 + 3) * 4 = 20", "17 / 5 = 3.4", "int(17 / 5) = 3", "mod(17, 5) = 2", "2 ** 10 = 1024",
                           "Ada was born in 1815, 211 years ago.", "count = 2"]
    e["cs04.decisions"] = ["score 95: grade A, passed", "score 83: grade B, passed", "score 71: grade C, passed", "score 64: grade D, passed", "score 40: grade F, not passed"]
    e["cs05.loops"] = ["the sum of 1 to 100 is 5050", "countdown: 10 9 8 7 6 5 4 3 2 1 go", "1000 halves below 1 after 10 steps", "the digits of 98765 add up to 35"]
    e["cs06.fizzbuzz"] = fizzbuzz()
    head = "    |" + "".join("%4d" % c for c in range(1, 10))
    e["cs07.tables"] = [head, "-" * len(head)] + [str(r) + " | " + " ".join(str(r * c) for c in range(1, 10)) for r in range(1, 10)]
    e["cs08.temperature"] = ["Celsius Fahrenheit"] + ["%d %.1f" % (c, c * 9 / 5 + 32) for c in range(-20, 41, 10)]
    e["cs09.subroutines"] = ["== areas ==", "square 4 by 4: area 16", "rectangle 3 by 7: area 21", "counting 1", "counting 2", "counting 3",
                             "after count.to, i is still: the main program's i"]
    fact = 1
    fl = []
    for n in range(0, 11):
        fact = fact * n if n > 1 else 1 if n <= 1 else fact
        f = 1
        for k in range(2, n + 1):
            f *= k
        fl.append("%d! = %d" % (n, f))
    fib = [0, 1]
    while len(fib) < 15:
        fib.append(fib[-1] + fib[-2])
    e["cs10.recursion"] = fl + ["", "the first 15 Fibonacci numbers, by a loop:", " ".join(str(x) for x in fib[:15])]
    marks = [72, 85, 91, 66, 78, 95, 59, 88]
    e["cs11.arrays"] = ["marks: " + ",".join(str(m) for m in marks), "total: %d" % sum(marks), "average: %.2f" % (sum(marks) / 8), "highest: %d" % max(marks), "lowest: %d" % min(marks)]
    e["cs12.dynamic.arrays"] = ["name: Grace Hopper", "languages: 3", "1: COBOL", "2: FLOW-MATIC", "3: A-0", "born: 1906", "now: COBOL, FLOW-MATIC, A-0, MATH-MATIC",
                                "inserted: B-0, COBOL, FLOW-MATIC, A-0, MATH-MATIC", "deleted 2: B-0, FLOW-MATIC, A-0, MATH-MATIC", "fields: 3"]
    s = "The quick brown fox"
    pal = []
    for w in ("level", "kayak", "basic", "A man a plan a canal Panama"):
        t = w.replace(" ", "").lower()
        pal.append(w + (" is a palindrome" if t == t[::-1] else " is not a palindrome"))
    e["cs13.strings"] = ["text: " + s, "length: %d" % len(s), "upper case: " + s.upper(), "lower case: " + s.lower(), "first 9: " + s[:9], "last 3: " + s[-3:],
                         "word 3: brown", "brown is at: %d" % (s.index("brown") + 1), "words: 4", "backwards: " + s[::-1]] + pal
    text = "the cat sat on the mat and the dog sat on the log".split()
    words = sorted(set(text))
    e["cs14.words"] = ["%d words, %d different:" % (len(text), len(words))] + ["%s %d" % (w, text.count(w)) for w in words]
    p = primes()
    e["cs15.primes"] = ["the %d primes up to 100:" % len(p), " ".join(str(x) for x in p)]
    e["cs16.gcd"] = ["gcd(%d, %d) = %d lcm = %d" % (a, b, gcd(a, b), a * b // gcd(a, b)) for a, b in ((48, 18), (1071, 462), (17, 5), (100, 75))]
    vals = [64, 25, 12, 22, 11, 90, 3, 47, 58, 36]
    srt, passes = bubble(vals)
    e["cs17.sorting"] = ["bubble sort: %s (%d passes)" % (" ".join(str(x) for x in srt), passes), "insertion sort: " + " ".join(str(x) for x in sorted(vals))]
    lst = [i * 3 for i in range(1, 1001)]
    lines = []
    for want in (3, 1500, 2997, 1001):
        pl = lst.index(want) + 1 if want in lst else 0
        ll = pl if pl else 1000
        pb, lb = binary_looks(lst, want)
        lines.append("%d linear: %s %d looks binary: %s %d looks" % (want, "at %d" % pl if pl else "absent", ll, "at %d" % pb if pb else "absent", lb))
    e["cs18.searching"] = lines
    e["cs19.stack.queue"] = ["stack holds 4 items"] + ["pop plate %d" % i for i in (4, 3, 2, 1)] + ["queue holds 4 items"] + ["serve customer %d" % i for i in (1, 2, 3, 4)]
    bal, rows = 0, []
    for kind, amt in (("deposit", 10000), ("withdraw", 2550), ("withdraw", 9000), ("deposit", 1999), ("withdraw", 4000)):
        note = ""
        if kind == "deposit":
            bal += amt
        elif amt <= bal:
            bal -= amt
        else:
            note = "refused: not enough money"
        rows.append(("%s %.2f %.2f %s" % (kind, amt / 100, bal / 100, note)).strip())
    e["cs23.bank"] = ["transaction amount balance note"] + rows + ["closing balance: %.2f" % (bal / 100)]
    e["cs20.files"] = ["wrote 3 records", "p2 is Alan, born 1912", "there is no p9", "p1: Ada (1815)", "p2: Alan (1912)", "p3: Grace Hopper (1906)", "p1 is deleted",
                       "the file cs20.data is removed again"]
    return e


# ------------------------------------------------------------------------------------------------- sections

def section_load():
    # 19 Nov 26 (the owner: "have the user load the examples rather than do it for every account"; "respect the gate"): the administrator's
    # LOAD.EXAMPLES with no name is SDSYS alone (the account the session is in); the accounts are loaded by naming them, or by their person (self)
    say("\n--- load: LOAD.EXAMPLES as the administrator - no name is SDSYS alone, a list loads the accounts named")
    names = shipped()
    n = len(names)
    row("L0 the shipped directory holds the five TUI programs and the training programs (the null case: there is something to load)",
        all(x in names for x in ("hello", "menus", "notes", "browse", "stock")) and len([x for x in names if x.startswith("cs")]) >= 20, repr(names))
    row("L0b no account has an examples.bp before LOAD.EXAMPLES (the null case of what follows)", not any(os.path.exists(xbp("", a)) for a in INSERVICE + ("zzhs", "sdsys")))
    out = load()
    row("L1 the administrator with no name: SDSYS alone, every program new and compiled", counts(out) == ((1, n, 0, 0), (n, n, 0)) and os.path.isdir(xbp("", "sdsys")),
        repr((counts(out), out[-6:])))
    row("L1b no other account was given an examples.bp (no form loads the whole register)", not any(os.path.exists(xbp("", a)) for a in INSERVICE + ("zzhs",)))
    out = load(" ".join(LISTED + ("zzhs",)))
    row("L1c the administrator's list %s zzhs: the three in service loaded, every program new and compiled; zzhs, SUSPENDED, is not entered (14123) "
        "and has no examples.bp" % " ".join(LISTED),
        counts(out) == ((3, 3 * n, 0, 0), (3 * n, 3 * n, 0)) and has(out, r"Could not enter the account zzhs") and not os.path.exists(xbp("", "zzhs")),
        repr((counts(out), out[-6:])))
    every = LISTED + ("sdsys",)
    bad = []
    for a in every:
        for x in names:
            want = [l.rstrip() for l in open(os.path.join(SRC, x), encoding="latin-1").read().rstrip("\n").split("\n")]
            try:
                got = open(xbp(x, a), encoding="latin-1").read().rstrip("\n").split("\n")
            except OSError:
                got = None
            if got != want:
                bad.append(a + " " + x)
    row("L2 every loaded account's examples.bp holds every shipped file, line for line", not bad, repr(bad[:6]))
    missing = [a + " " + x for a in every for x in names if not os.path.isfile(os.path.join(adir(a), "examples.bp.out", x))]
    row("L3 every program has its object in each loaded account's examples.bp.out", not missing, repr(missing[:6]))
    out = load(" ".join(LISTED))
    row("L4 a second run of the list changes nothing and compiles nothing", counts(out) == ((3, 0, 0, 3 * n), (0, 0, 0)), repr(counts(out)))
    g.put(xbp("zzmine"), "* zzmine - the administrator's own\n   crt 'mine'\nend\n")
    g.put(xbp("cs01.hello"), "* changed by hand\n   crt 'not the shipped program'\nend\n")
    out = load("zzhd")
    row("L5 LOAD.EXAMPLES zzhd: that account only; the administrator's program kept, a shipped one changed by hand put back and compiled again",
        counts(out) == ((1, 0, 1, n - 1), (1, 1, 1)) and "not the shipped program" not in open(xbp("cs01.hello")).read() and os.path.exists(xbp("zzmine")), repr(counts(out)))
    os.remove(xbp("zzmine"))
    out = load("zznone")
    row("L5b an account that is not registered is said (14122) and nothing is made", has(out, r"No account is registered as zznone"), repr(out[-3:]))


def bp_edit(acct, on):
    """field 11 of the account's register record (bp.edit), yes or no; read by the next session's sign-on"""
    rec = g.reg_read(acct)
    while rec and rec[-1] == "":
        rec.pop()
    rec += [""] * (12 - len(rec))
    rec[10] = "yes" if on else "no"
    g.reg_write(acct, rec)


def section_self():
    # 19 Nov 26: THE PERSON LOADS THEIR OWN.  zzhv, an ordinary fixture account in service, has no examples.bp yet (load did not name it)
    say("\n--- self: an ordinary account loads its own examples (zzhv), only with bp.edit")
    n = len(shipped())
    BP_REFUSED = r"Programs can only be compiled or cataloged by an account that has bp\.edit"
    bp_edit("zzhv", False)
    out = g.plain("zzhv", ["load.examples"])
    row("S1 with bp.edit OFF, as delivered, LOAD.EXAMPLES in the person's own account is refused in BASIC's words (11408) and nothing is made",
        has(out, BP_REFUSED) and not os.path.exists(xbp("", "zzhv")), repr(out[-4:]))
    out = g.plain("zzhv", ["load.examples zzht"])
    row("S2 naming an account is the administrator's: refused (2001), whatever bp.edit says", has(out, r"Command requires administrator privileges"), repr(out[-4:]))
    bp_edit("zzhv", True)
    out = g.plain("zzhv", ["load.examples"])
    row("S3 with bp.edit ON the person's LOAD.EXAMPLES loads their own account only: every program new and compiled, the objects there",
        counts(out) == ((1, n, 0, 0), (n, n, 0)) and all(os.path.isfile(os.path.join(adir("zzhv"), "examples.bp.out", x)) for x in shipped()), repr((counts(out), out[-6:])))
    out = g.plain("zzhv", ["RUN examples.bp cs01.hello"])
    row("S4 and runs one where it is", contains(out, ["Hello, world!", "This is SD BASIC.", "One plus one is 2"]), repr(out[-5:]))


def section_reach():
    say("\n--- reach: an ordinary account and its own examples.bp")
    out = user(["CT VOC examples.bp", "COUNT examples.bp"])
    row("R0 the account's VOC holds examples.bp as its own file (an F entry naming examples.bp, not a path outside the account)",
        any(re.match(r"^\s*0*1:?\s+F\b", l) or l.strip() == "F" for l in out) and not any("/" in l and "examples.bp" in l and "user_accounts/zzhd" not in l for l in out), repr(out[-8:]))
    n = len(shipped())
    row("R1 COUNT examples.bp counts the shipped programs", has(out, r"^%d record\(s\) counted" % n), repr(out[-4:]))
    out = user(["RUN examples.bp cs06.fizzbuzz"])
    row("R2 RUN examples.bp cs06.fizzbuzz runs the program where it is", contains(out, fizzbuzz()), repr(out[-12:]))
    out = user(["COPY FROM examples.bp TO bp cs06.fizzbuzz", "BASIC bp cs06.fizzbuzz", "RUN bp cs06.fizzbuzz"])
    row("R3 COPY FROM examples.bp TO bp, BASIC and RUN in the account's own bp: the same output", has(out, r"Compiled 1 program\(s\) with no errors") and contains(out, fizzbuzz())
        and os.path.exists(os.path.join(sh.BOX, "user_accounts", "zzhd", "bp", "cs06.fizzbuzz")), repr(out[-12:]))
    # R4: the fixture accounts are made with bp.edit ON (sandbox-home.py); as delivered it is OFF.  The control first, then field 11 set to no.
    g.put(os.path.join(adir("zzhd"), "bp", "zzother"), "* zzother\n   crt 'other'\nend\n")
    rec = g.reg_read("zzhd")
    while rec and rec[-1] == "":
        rec.pop()
    rec += [""] * (12 - len(rec))
    row("R4a (the control) with bp.edit ON, as the fixture is made, COPY into examples.bp writes the record",
        rec[10].strip().lower() == "yes" and has(user(["COPY FROM bp TO examples.bp zzother"]), r"1 record\(s\) copied") and os.path.exists(xbp("zzother")), repr(rec[10]))
    if os.path.exists(xbp("zzother")):
        os.remove(xbp("zzother"))
    rec[10] = "no"
    g.reg_write("zzhd", rec)
    out = user(["COPY FROM bp TO examples.bp zzother"])
    row("R4 with bp.edit OFF, as delivered, the account cannot write into its examples.bp: refused, and no record made", not os.path.exists(xbp("zzother")), repr(out[-4:]))
    out = user(["RUN examples.bp cs01.hello"])
    row("R4b and with bp.edit OFF it still RUNS a program where it is (as delivered, a person can run every example)", contains(out, ["Hello, world!", "This is SD BASIC.", "One plus one is 2"]), repr(out[-5:]))
    rec[10] = "yes"
    g.reg_write("zzhd", rec)


def section_run():
    say("\n--- run: every training program, from the ordinary account, against its answer")
    exp = expected()
    for name in sorted(exp):
        out = user(["RUN examples.bp " + name])
        row("X %s" % name, contains(out, exp[name]), repr([l for l in out if l.strip()][-14:]))
    out = g.plain("zzhd", ["RUN examples.bp cs03.input", "Grace", "37"])
    row("X cs03.input (input on the pipe: Grace, 37)", any("Hello, Grace. In ten years you will be 47." == norm(l) for l in out), repr(out[-6:]))
    out = g.plain("zzhd", ["RUN examples.bp cs21.guess 42"] + [str(x) for x in range(1, 101)])
    row("X cs21.guess (seed 42, guesses 1 to 100: it is found, and every guess before it was too low)",
        any(re.search(r"You got it in \d+ tries!", l) for l in out) and not any("Too high." in l for l in out), repr([l for l in out if "got it" in l or "Too" in l][-3:]))
    out = user(["RUN examples.bp cs22.dates"])
    import datetime
    moon = (datetime.date(1969, 7, 20) - datetime.date(1967, 12, 31)).days          # SD's day 0 is 31 December 1967
    row("X cs22.dates (today's date: the shape only; the Moon landing is day %d)" % moon, any(re.match(r"^today is day number \d+$", norm(l)) for l in out)
        and any(("the Moon landing was day %d," % moon) in l for l in out), repr(out[-8:]))
    row("X cs20.files left no file behind in zzhd", not os.path.exists(os.path.join(sh.BOX, "user_accounts", "zzhd", "cs20.data")))


def rcounts(out):
    """(accounts, programs, files) and (accounts with none, kept) of REMOVE.EXAMPLES's two lines, or None"""
    a = b = None
    for l in out:
        m = re.match(r"^Example programs removed from (\d+) account\(s\): (\d+) programs, (\d+) files examples\.bp deleted \(nothing else was in them\)$", l)
        if m:
            a = tuple(int(x) for x in m.groups())
        m = re.match(r"^Accounts that had no examples\.bp: (\d+); programs added by the administrator, kept: (\d+)$", l)
        if m:
            b = tuple(int(x) for x in m.groups())
    return a, b


def section_remove():
    say("\n--- remove: REMOVE.EXAMPLES, and both verbs with a list of accounts (runs after run, on what load and self left)")
    names = shipped()
    n = len(names)
    out = adm("remove.examples zzhd zzhm")
    row("M1 REMOVE.EXAMPLES zzhd zzhm (a list): each loses its n programs and its examples.bp, none was left behind",
        rcounts(out) == ((2, 2 * n, 2), (0, 0)), repr((rcounts(out), out[-5:])))
    row("M1b zzhd and zzhm have neither examples.bp nor examples.bp.out on the disk; zzht, not named, still has both",
        not any(os.path.exists(os.path.join(adir(a), x)) for a in ("zzhd", "zzhm") for x in ("examples.bp", "examples.bp.out"))
        and os.path.isdir(os.path.join(adir("zzht"), "examples.bp")) and os.path.isdir(os.path.join(adir("zzht"), "examples.bp.out")))
    g.put(xbp("zzmine", "zzht"), "* zzmine - the administrator's own\n   crt 'mine'\nend\n")
    out = adm("remove.examples zzht zznone zzhm")
    row("M2 a program the administrator added is KEPT with the file; an unregistered name is said (14130) and the others go on; an account with no examples.bp is counted",
        rcounts(out) == ((1, n, 0), (1, 1)) and has(out, r"No account is registered as zznone, so no example programs were removed there"), repr((rcounts(out), out[-6:])))
    row("M2b in zzht the shipped programs and their objects are gone, zzmine is still there",
        os.path.exists(xbp("zzmine", "zzht")) and not any(os.path.exists(xbp(x, "zzht")) or os.path.exists(os.path.join(adir("zzht"), "examples.bp.out", x)) for x in names))
    out = load("zzhd zzhm zzht")
    row("M3 LOAD.EXAMPLES zzhd zzhm zzht (a list): all three given every program again, compiled, the added one kept",
        counts(out) == ((3, 3 * n, 0, 0), (3 * n, 3 * n, 1)) and all(os.path.isfile(os.path.join(adir(a), "examples.bp.out", x)) for a in ("zzhd", "zzhm", "zzht") for x in names), repr((counts(out), out[-4:])))
    out = g.plain("zzhv", ["remove.examples zzhd"])
    row("M4 an ordinary account may not name an account (2001), and zzhd keeps its examples", has(out, r"Command requires administrator privileges")
        and os.path.isdir(xbp("", "zzhd")), repr(out[-4:]))
    bp_edit("zzhv", False)
    out = g.plain("zzhv", ["remove.examples"])
    row("M4b with bp.edit OFF the person's own REMOVE.EXAMPLES is refused (11408) and the examples stay", has(out, r"Programs can only be compiled or cataloged by an account that has bp\.edit")
        and os.path.isdir(xbp("", "zzhv")), repr(out[-4:]))
    bp_edit("zzhv", True)
    out = g.plain("zzhv", ["remove.examples"])
    row("M4c with bp.edit ON it removes them from the person's own account only", rcounts(out) == ((1, n, 1), (0, 0)) and not os.path.exists(xbp("", "zzhv"))
        and os.path.isdir(xbp("", "zzhd")), repr((rcounts(out), out[-5:])))
    out = adm("remove.examples")
    row("M5 the administrator's REMOVE.EXAMPLES with no name: SDSYS alone; the accounts keep theirs",
        rcounts(out) == ((1, n, 1), (0, 0)) and not os.path.exists(xbp("", "sdsys")) and os.path.isdir(xbp("", "zzhd")) and os.path.exists(xbp("zzmine", "zzht")), repr((rcounts(out), out[-5:])))


def main():
    try:
        sh.setup("sandbox-examples.py")
        section_load()
        if ONLY is None or "self" in ONLY or "remove" in ONLY:
            section_self()
        if ONLY is None or "reach" in ONLY:
            section_reach()
        if ONLY is None or "run" in ONLY:
            section_run()
        if ONLY is None or "remove" in ONLY:
            section_remove()
    finally:
        sh.teardown()
    sh.summary("sandbox-examples")                  # prints "N passed, M failed" and exits 0 only when every row passed and one did


if __name__ == "__main__":
    sys.exit(main())
