#!/usr/bin/env python3
# test-themeroles-units.py - S.88 3.7a (29 Oct 2026): the role styles, the theme list and the delivered SCREENTHEME.  FREE CHECK, text only (comments removed), no install, no sudo, no sd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-themeroles-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-themeroles-units.py --selftest      (mutants)
#
#   R1  SL.CODES: 51 different letters, the five roles UVWXY after the scroll bar (B) and before the sixteen user styles, Z the only letter left; the old list is nowhere in gpl.bp
#   R2  $sl_theme names the styles in the order of the codes: the roles are warning success readonly busy focus, error is code f, the user styles still come last
#   R3  every theme gives every role a look: mono (flags only, no dim, six looks different from each other and from plain), classic and blue (both colours), dark and light (a colour and flags)
#   R4  'list' answers blue classic dark light mono; 'next' takes the next one this terminal can show, wraps, and answers mono alone when there is no colour or no terminal
#   R5  tool.keys has no list of its own and asks the library for the next theme
#   R6  CONFIG() reads a name of up to 16 characters (the setter's buffer is not touched) and SCREEN OPEN asks for SCREENTHEME, refusals ignored
#   R7  the shipped sd.conf has SCREENTHEME=blue once, in [sd], and the table row no longer says it cannot be read
# NOT SAID HERE: that a role is drawn as it says, that a program compiled against the new list works, or that CONFIG() answers - that is sandbox-themeroles.py, and it has not been run.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
BP = os.path.join(SD64, "sdsys", "gpl.bp")
F = {"sl.h": os.path.join(BP, "sl.h"), "sl_theme": os.path.join(BP, "sl_theme"), "tool_keys": os.path.join(BP, "tool_keys"), "sl_sgr": os.path.join(BP, "sl_sgr"),
     "opconfig": os.path.join(SD64, "gplsrc", "op_config.c"), "sd.conf": os.path.join(SD64, "sd.conf"), "table": os.path.join(SD64, "sdsys", "config.table")}
for k in F:
    F[k] = os.environ.get("TR_" + re.sub(r"\W", "_", k).upper(), F[k])
passed = failed = 0
ROLES = ["warning", "success", "readonly", "busy", "focus"]
EXPECT_CODES = "nruxbwhasjkedytgcqovplzfimGPTBUVWXYACDEFHIJKLMNOQRS"


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def raw(key):
    return open(F[key], encoding="latin-1").read()


def bas(key):
    """BASIC with its comment lines and ;* tails removed"""
    out = []
    for ln in raw(key).split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        ln = re.sub(r"\s;\*.*$", "", ln)
        out.append(ln.rstrip())
    return "\n".join(out)


def ccode(key):
    s = raw(key)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def flat(s):
    return re.sub(r"\s+", " ", s)


def label_block(src, label):
    """the lines of a label: from 'label:' to its 'return'"""
    m = re.search(r"^" + re.escape(label) + r":\n(.*?)\n[ \t]*return[ \t]*$", src, re.S | re.M)
    return m.group(1) if m else ""


def specs(block):
    """'name=fg,bg,flags' strings of a block of BASIC -> {name: (fg, bg, flags)}"""
    out = {}
    for m in re.finditer(r"spec<-1> = '([a-z.]+)=([a-z]*),([a-z]*),([a-z +]*)'", block):
        out[m.group(1)] = (m.group(2), m.group(3), tuple(sorted(m.group(4).split())))
    return out


def theme_case(th, name, nxt):
    m = re.search(r"case nm = '" + name + r"'\n(.*?)\n\s*case " + nxt, th, re.S)
    return m.group(1) if m else ""


def theme_looks(th):
    """the style definitions each theme ends with: its own case plus the subroutines it gosubs"""
    cases = {"mono": theme_case(th, "mono", "nm = 'classic'"), "classic": theme_case(th, "classic", "nm = 'dark'"), "dark": theme_case(th, "dark", "nm = 'light'"),
             "light": theme_case(th, "light", "nm = 'blue'"), "blue": theme_case(th, "blue", "1")}
    out = {}
    for name, body in cases.items():
        d = specs(body)
        for g in re.findall(r"gosub ([a-z.]+)", body):
            d.update(specs(label_block(th, g)))
        out[name] = d
    return out


def run():
    sh = raw("sl.h")
    m = re.search(r"\$define SL\.CODES\s+'([^']+)'", sh)
    codes = m.group(1) if m else ""
    row("R1 SL.CODES is the 51 letters in the one order (the roles UVWXY between B and the user styles)", codes == EXPECT_CODES, codes)
    row("R1 ... all different, Z unused, and the last sixteen are still the user styles", len(set(codes)) == 51 and "Z" not in codes and codes.endswith("ACDEFHIJKLMNOQRS"))
    old = "nruxbwhasjkedytgcqovplzfimGPTBACDEFHIJKLMNOQRS"
    stale = [n for n in os.listdir(BP) if os.path.isfile(os.path.join(BP, n)) and old in open(os.path.join(BP, n), encoding="latin-1").read()]
    row("R1 the old list of 46 is in no program of gpl.bp", not stale, repr(stale))
    row("R1 $sl_sgr still compares the theme's codes with SL.CODES (a program on the old list falls back to mono, not to wrong colours)", "th.codes = SL.CODES" in bas("sl_sgr"))

    th = bas("sl_theme")
    names = []
    for ln in th.split("\n"):
        if ln.strip().startswith("th.names ") or ln.strip().startswith("th.names:="):
            names += re.findall(r"'([a-z.]+)'", ln)
    names = [n for n in names if n != "user"] + ["user%d" % i for i in range(1, 17)]
    pair = dict(zip(names, codes))
    row("R2 $sl_theme names 51 styles", len(names) == 51, str(len(names)))
    row("R2 ... the roles are codes U V W X Y in the order warning success readonly busy focus", [pair.get(r) for r in ROLES] == list("UVWXY"), repr([pair.get(r) for r in ROLES]))
    row("R2 ... error is f, scroll is B, and user1 to user16 are the last sixteen", pair.get("error") == "f" and pair.get("scroll") == "B" and pair.get("user1") == "A" and pair.get("user16") == "S")
    row("R2 ... the user styles are still found as len(th.codes) - 15, in all three places", th.count("len(th.codes) - 15") == 3, str(th.count("len(th.codes) - 15")))

    looks = theme_looks(th)
    row("R3 every theme gives every role and error a definition", all(all(r in looks[t] for r in ROLES + ["error"]) for t in looks),
        repr({t: [r for r in ROLES + ["error"] if r not in looks[t]] for t in looks}))
    mono = looks["mono"]
    mflags = {r: mono[r][2] for r in ROLES + ["error"] if r in mono}
    row("R3 mono: flags only, no colour", all(mono[r][0] == "" and mono[r][1] == "" for r in mflags), repr(mono))
    row("R3 mono: no dim (SD's xterm entry has none)", all("dim" not in f for f in mflags.values()), repr(mflags))
    row("R3 mono: the six roles look different from one another and from plain", len(set(mflags.values())) == 6 and () not in mflags.values() and len(mflags) == 6, repr(mflags))
    row("R3 classic and blue: a role has both colours, as a style replaces the whole attribute set",
        all(looks[t][r][0] and looks[t][r][1] for t in ("classic", "blue") for r in ROLES), repr({t: {r: looks[t][r] for r in ROLES} for t in ("classic", "blue")}))
    row("R3 dark and light: a colour and at least one flag, no background (the terminal's own)",
        all(looks[t][r][0] and looks[t][r][1] == "" and looks[t][r][2] for t in ("dark", "light") for r in ROLES), repr({t: {r: looks[t][r] for r in ROLES} for t in ("dark", "light")}))
    row("R3 the colour themes keep error white on red, bold (the syntax colour)", all(looks[t]["error"] == ("white", "red", ("bold",)) for t in ("classic", "dark", "light", "blue")))

    fl = flat(th)
    row("R4 'list' answers blue classic dark light mono, in that order, from one place",
        "thorder = 'blue' : @fm : 'classic' : @fm : 'dark' : @fm : 'light' : @fm : 'mono'" in fl and fl.count("thorder = '") == 1 and "case op = 'list' gosub theme.order ret = thorder" in fl)
    nt = flat(label_block(th, "next.theme")).strip()
    i_col = nt.find("system(25)")
    i_37 = nt.find("@(-37, 7) = ''")
    i_38 = nt.find("@(-38, 0) = ''")
    i_ret = nt.find("ret = thorder<nxpos>")
    row("R4 'next' starts from mono as the answer, tests for a terminal with no colour (system(25), setf, setb) before it picks anything, and returns at once if so",
        nt.startswith("gosub theme.order ret = 'mono'") and 0 < i_col < i_ret and 0 < i_37 < i_ret and 0 < i_38 < i_ret and "if nxok = 0 then return" in nt and nt.find("if nxok = 0 then return") < i_ret, nt[:300])
    row("R4 'next' starts at the theme asked about, else the one in force, else mono; a name it does not know starts the list again; it wraps",
        "nxcur = downcase(trim(a)) if nxcur = '' then nxcur = th.name if nxcur = '' then nxcur = 'mono'" in nt and "end else nxpos = 0 end" in nt
        and "nxpos = nxpos + 1 if nxpos > dcount(thorder, @fm) then nxpos = 1 ret = thorder<nxpos>" in nt and "locate nxcur in thorder<1> setting nxi" in nt)
    row("R4 the op is in the case list ('next' calls next.theme) and it writes nothing", "case op = 'next' gosub next.theme" in fl and not re.search(r"\b(write|delete|execute|openseq|kernel)\b", nt))

    tk = bas("tool_keys")
    ftk = flat(tk)
    row("R5 tool.keys has no list of themes of its own", not re.search(r"\bthemes\s*=", tk) and "locate thn in themes" not in tk and "'mono' : @fm : 'classic' : @fm : 'blue'" not in tk)
    row("R5 ... and takes the next theme from $sl_theme, saying so when there is none but mono",
        "call $sl_theme('next', thn, '', '', '', thx) if thx = thn then msg = 'this terminal cannot show colour: no theme but mono'" in ftk and "screen theme thx returning thn else" in ftk)

    oc = ccode("opconfig")
    cfg = oc[:oc.find("op_pconfig")] if "op_pconfig" in oc else oc
    row("R6 CONFIG() has a 16 character name buffer and limit, and no 8 left in it", "char param[16 + 1];" in cfg and "k_get_c_string(descr, param, 16) < 1" in cfg and "k_get_c_string(descr, param, 8)" not in cfg)
    row("R6 ... the setter's buffer and limit are not touched", "char param[8 + 1];" in oc and "k_get_c_string(descr, param, 8) < 1" in oc, "")
    row("R6 ... SCREENTHEME has its branch", 'strcmp(param, "SCREENTHEME")' in cfg and "k_put_c_string(pcfg.screentheme, &result)" in cfg)
    row("R6 SCREEN OPEN's default asks CONFIG('SCREENTHEME'), only when the program has not asked, and a refusal is not an error",
        "if not(th.asked) then dn = downcase(trim(config('SCREENTHEME'))) if dn # '' and dn # downcase(th.name) then a = dn gosub set.theme end end" in fl)

    conf = raw("sd.conf")
    sec = None
    n_sd = n_all = 0
    for ln in conf.split("\n"):
        if ln.startswith("["):
            sec = ln.strip().lower()
        if ln.strip() == "SCREENTHEME=blue":
            n_all += 1
            n_sd += 1 if sec == "[sd]" else 0
    row("R7 the shipped sd.conf has SCREENTHEME=blue once, in [sd]", n_sd == 1 and n_all == 1 and len(re.findall(r"^SCREENTHEME=", conf, re.M)) == 1, "in [sd] %d, all %d" % (n_sd, n_all))
    tr = [ln for ln in raw("table").split("\n") if ln.startswith("SCREENTHEME|")]
    row("R7 the table has one SCREENTHEME row, which says blank is mono and that the shipped file sets blue, and no longer says it cannot be read",
        len(tr) == 1 and "Not readable" not in tr[0] and "Blank means mono" in tr[0] and "sets blue" in tr[0], repr(tr))
    print("test-themeroles-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


def selftest():
    import shutil
    t = tempfile.mkdtemp()
    caught = missed = 0
    real = {k: open(v, encoding="latin-1").read() for k, v in F.items()}

    def mutant(name, which, old, new):
        nonlocal caught, missed
        if old not in real[which]:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        f = os.path.join(t, name.replace(" ", "_"))
        open(f, "w", encoding="latin-1").write(real[which].replace(old, new, 1))
        env = dict(os.environ)
        env["TR_" + re.sub(r"\W", "_", which).upper()] = f
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
        print("  [FAIL] the real files do not pass:\n" + r.stdout[-900:])
        return 1
    print("  [ok] the real files pass")
    mutant("roles after the user styles", "sl.h", "GPTBUVWXYACDEFHIJKLMNOQRS", "GPTBACDEFHIJKLMNOQRSUVWXY")
    mutant("a role code is a user code", "sl.h", "GPTBUVWXYACD", "GPTBUVWXACD")
    mutant("a role is not named", "sl_theme", "th.names := @fm : 'busy' : @fm : 'focus'", "th.names := @fm : 'busy'")
    mutant("roles named in another order", "sl_theme", "'warning' : @fm : 'success'", "'success' : @fm : 'warning'")
    mutant("mono warning uses dim", "sl_theme", "spec<-1> = 'warning=,,bold underline'", "spec<-1> = 'warning=,,dim'")
    mutant("two mono roles look the same", "sl_theme", "spec<-1> = 'readonly=,,underline'", "spec<-1> = 'readonly=,,bold'")
    mutant("mono has no look for error", "sl_theme", "   spec<-1> = 'error=,,reverse bold'\n", "")
    mutant("mono is not given the roles", "sl_theme", "         gosub roles.mono\n", "")
    mutant("blue readonly has no background", "sl_theme", "spec<-1> = 'readonly=cyan,black,'", "spec<-1> = 'readonly=cyan,,'")
    mutant("classic is given no roles", "sl_theme", "         spec<-1> = 'focus=white,cyan,bold'\n         gosub syntax.dark\n      case nm = 'dark'", "         gosub syntax.dark\n      case nm = 'dark'")
    mutant("dark roles lose their flags", "sl_theme", "spec<-1> = 'success=green,,bold'\n   spec<-1> = 'readonly=cyan,,underline'", "spec<-1> = 'success=green,,bold'\n   spec<-1> = 'readonly=cyan,,'")
    mutant("light is not given the roles", "sl_theme", "         gosub syntax.light\n         gosub roles.light\n", "         gosub syntax.light\n")
    mutant("the list changes order", "sl_theme", "thorder = 'blue' : @fm : 'classic'", "thorder = 'classic' : @fm : 'blue'")
    mutant("next forgets the colourless terminal", "sl_theme", "   if system(25) then nxok = 0\n", "")
    mutant("next forgets setf and setb", "sl_theme", "      if @(-37, 7) = '' or @(-38, 0) = '' then nxok = 0\n", "")
    mutant("next does not wrap", "sl_theme", "if nxpos > dcount(thorder, @fm) then nxpos = 1", "if nxpos > dcount(thorder, @fm) then nxpos = 0")
    mutant("next starts from the first theme always", "sl_theme", "nxcur = downcase(trim(a))", "nxcur = 'zz'")
    mutant("the user styles are found by a fixed number", "sl_theme", "ufirst = len(th.codes) - 15                     ;* the user styles", "ufirst = 31                     ;* the user styles")
    mutant("the default theme is not asked of the configuration", "sl_theme", "dn = downcase(trim(config('SCREENTHEME')))", "dn = ''")
    mutant("tool.keys keeps its own list", "tool_keys", "   snames = 'normal'", "   themes = 'mono' : @fm : 'classic' : @fm : 'blue'\n   snames = 'normal'")
    mutant("tool.keys does not ask the library", "tool_keys", "call $sl_theme('next', thn, '', '', '', thx)", "thx = thn")
    mutant("CONFIG() buffer back to eight", "opconfig", "char param[16 + 1];", "char param[8 + 1];")
    mutant("CONFIG() limit back to eight", "opconfig", "k_get_c_string(descr, param, 16) < 1", "k_get_c_string(descr, param, 8) < 1")
    mutant("the setter widened", "opconfig", "  char param[8 + 1];\n", "  char param[16 + 1];\n")
    mutant("SCREENTHEME has no branch", "opconfig", 'strcmp(param, "SCREENTHEME")', 'strcmp(param, "SCREENTHEMX")')
    mutant("the shipped sd.conf has no theme", "sd.conf", "SCREENTHEME=blue\n", "")
    mutant("the shipped sd.conf says mono", "sd.conf", "SCREENTHEME=blue", "SCREENTHEME=mono")
    mutant("the table says unreadable again", "table", "whatever this says.|no|", "whatever this says. Not readable with the CONFIG function.|no|")
    shutil.rmtree(t, ignore_errors=True)
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
