#!/usr/bin/env python3
# test-themeroles-units.py - S.88 3.7a (29 Oct 2026): the role styles, the theme list and the delivered SCREENTHEME.  FREE CHECK, text only (comments removed), no install, no sudo, no sd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-themeroles-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-themeroles-units.py --selftest      (mutants)
#
#   R1  SL.CODES: 51 different letters, the five roles UVWXY after the scroll bar (B) and before the sixteen user styles, Z the only letter left; the old list is nowhere in gpl.bp
#   R2  $sl_theme names the styles in the order of the codes: the roles are warning success readonly busy focus, error is code f, the user styles still come last
#   R3  every theme gives every role a look: mono (flags only, no dim, six looks different from each other and from plain), classic and blue (both colours), dark and light (a colour and flags)
#   R9  (8 Nov 26, S.172) paper and night: every style has both colours, the body / bar / selection / mnemonic / header pairs are the readable ones (black or dark blue on
#       light grey, white or yellow on black), the menu bar the inverse of the page with its letter underlined and no red on it, nothing on the light grey bold, the four
#       raw styles in the theme's own colours
#   R4  'list' answers blue classic dark light mono night paper; 'next' takes the next one this terminal can show, wraps, and answers mono alone when there is no colour or no terminal
#   R5  tool.keys has no list of its own and asks the library for the next theme
#   R6  CONFIG() reads a name of up to 16 characters (the setter's buffer is not touched) and SCREEN OPEN asks for SCREENTHEME, refusals ignored
#   R7  the shipped sd.conf has SCREENTHEME=paper once, in [sd], and the table row no longer says it cannot be read
#   R8  (2 Nov 26, S.88 p3.7b) the IDE has no list of its own: it starts in SCREENTHEME (paper when blank), falls back to paper then to what the library kept, cycles with
#       $sl_theme('next') and puts the theme on again when it takes the screen back.  That it OPENS in the site's theme on a screen is sandbox-ide-resize.py section theme.
# NOT SAID HERE: that a role is drawn as it says, that a program compiled against the new list works, or that CONFIG() answers - that is sandbox-themeroles.py, and it has not been run.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
BP = os.path.join(SD64, "sdsys", "gpl.bp")
F = {"sl.h": os.path.join(BP, "sl.h"), "sl_theme": os.path.join(BP, "sl_theme"), "tool_keys": os.path.join(BP, "tool_keys"), "sl_sgr": os.path.join(BP, "sl_sgr"), "ide": os.path.join(BP, "ide"),
     "tk_theme": os.path.join(BP, "tk_theme"),
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
             "light": theme_case(th, "light", "nm = 'blue'"), "blue": theme_case(th, "blue", "nm = 'paper'"),
             "paper": theme_case(th, "paper", "nm = 'night'"), "night": theme_case(th, "night", "1")}
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
    hl = [mono.get(s, ("", "", ()))[2] for s in ("highlight", "bar")]
    row("R3 mono: focus does not look like highlight or the bar (9 Nov 26, S.186: it was plain reverse, so the focused box looked like the selected row)",
        mflags.get("focus") not in hl and all(hl), repr((mflags.get("focus"), hl)))
    row("R3 classic, blue, paper and night: a role has both colours, as a style replaces the whole attribute set",
        all(looks[t][r][0] and looks[t][r][1] for t in ("classic", "blue", "paper", "night") for r in ROLES),
        repr({t: {r: looks[t][r] for r in ROLES} for t in ("classic", "blue", "paper", "night")}))
    row("R3 dark and light: a colour and at least one flag, no background (the terminal's own)",
        all(looks[t][r][0] and looks[t][r][1] == "" and looks[t][r][2] for t in ("dark", "light") for r in ROLES), repr({t: {r: looks[t][r] for r in ROLES} for t in ("dark", "light")}))
    row("R3 the colour themes keep error white on red, bold (the syntax colour)", all(looks[t]["error"] == ("white", "red", ("bold",)) for t in ("classic", "dark", "light", "blue", "paper", "night")))

    # R9 (8 Nov 26, S.172): paper and night are the readable themes the owner asked for ("black or dark blue on light grey or white or yellow on black")
    bg_of = {"paper": "white", "night": "black"}
    allpairs = {r for t in ("paper", "night") for r in looks[t]}
    row("R9 paper and night: every style they define has BOTH colours (a foreground alone would show the terminal's background in a light or black window)",
        all(looks[t][s][0] and looks[t][s][1] for t in ("paper", "night") for s in looks[t]),
        repr({t: [s for s in looks[t] if not (looks[t][s][0] and looks[t][s][1])] for t in ("paper", "night")}))
    readable = {("black", "white"), ("blue", "white"), ("white", "black"), ("brown", "black")}
    body = ["desktop", "window", "text", "pane", "field", "bar", "barsel", "highlight", "hotkey", "hotkey.bar", "header", "tab"]
    row("R9 ... the body, the bar, the selection, the mnemonic letters and the headers are one of the readable pairs (black or dark blue on light grey, white or yellow on black)",
        all(s in looks[t] and looks[t][s][:2] in readable for t in ("paper", "night") for s in body),
        repr({t: {s: looks[t].get(s) for s in body if s not in looks[t] or looks[t][s][:2] not in readable} for t in ("paper", "night")}))
    row("R9 ... the menu bar is the inverse of the page (paper light grey on black, night black on light grey), its letter underlined on the bar's background, no red on it",
        all(looks[t]["bar"][:2] == (looks[t]["window"][1], looks[t]["window"][0]) and "underline" in looks[t]["hotkey.bar"][2]
            and looks[t]["hotkey.bar"][1] == looks[t]["bar"][1] and looks[t]["barsel"][1] == looks[t]["bar"][0]
            and "red" not in looks[t]["hotkey.bar"][:2] and "red" not in looks[t]["barsel"][:2] for t in ("paper", "night")),
        repr({t: (looks[t].get("bar"), looks[t].get("hotkey.bar"), looks[t].get("barsel")) for t in ("paper", "night")}))
    row("R9 ... nothing on the light grey is bold (most terminals make bold text bright, and bright black or blue on light grey is pale: the first capture)",
        all("bold" not in looks[t][s][2] for t in ("paper", "night") for s in looks[t] if looks[t][s][1] == "white"),
        repr({t: [s for s in looks[t] if looks[t][s][1] == "white" and "bold" in looks[t][s][2]] for t in ("paper", "night")}))
    row("R9 ... the four raw styles take the theme's two colours (a page's list in normal is not in the terminal's own colours), reverse still reverse",
        all(looks[t][s][:2] == looks[t]["window"][:2] for t in ("paper", "night") for s in ("normal", "reverse", "underline", "both"))
        and all(looks[t]["reverse"][2] == ("reverse",) and looks[t]["underline"][2] == ("underline",) for t in ("paper", "night")),
        repr({t: {s: looks[t].get(s) for s in ("normal", "reverse", "underline", "both")} for t in ("paper", "night")}))
    row("R9 ... the window, the text and the desktop are on the theme's own background (light grey for paper, black for night)",
        all(looks[t][s][1] == bg_of[t] for t in ("paper", "night") for s in ("window", "text", "desktop", "pane")) and len(allpairs) > 20)

    fl = flat(th)
    row("R4 'list' answers blue classic dark light mono night paper, in that order, from one place",
        "thorder = 'blue' : @fm : 'classic' : @fm : 'dark' : @fm : 'light' : @fm : 'mono' : @fm : 'night' : @fm : 'paper'" in fl and fl.count("thorder = '") == 1 and "case op = 'list' gosub theme.order ret = thorder" in fl)
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
    # 8 Nov 26 (S.179): tool.keys takes the theme the way every page does - $tk_std 'theme', which asks $tk_theme (the library's next, kept for the person)
    row("R5 ... and takes the next theme the way every page does ($tk_std 'theme'), showing its message",
        "case act = 'theme' call $tk_std('theme', ctx, keys, '', std.r) msg = std.r<2>" in ftk)
    tth = flat(bas("tk_theme"))
    row("R5 ... $tk_theme takes $sl_theme's next, says so when there is none but mono, sets it as the program's choice and keeps it for the person",
        "call $sl_theme('next', now, '', '', '', want) if want = now then msg =" in tth and "call $sl_theme('set', want, 'asked', '', '', setr)" in tth
        and "call $sl_theme('save', now, '', '', '', kept)" in tth, tth[:300])

    ide = bas("ide")
    fide = flat(ide)
    first_apply = ide.find("gosub apply.theme")
    head = flat(ide[:first_apply]) if first_apply > 0 else ""
    ap = flat(label_block(ide, "apply.theme") or "").strip()
    m = re.search(r"case cmd = 'theme'\n(.*?)\n\s*end case", ide, re.S)
    tc = flat(m.group(1)).strip() if m else ""
    row("R8 the IDE has no list of themes of its own (2 Nov 26, S.88 p3.7b)", not re.search(r"\bthemes\s*=", ide) and "theme.n" not in ide and "themes<" not in ide)
    row("R8 ... it starts in the person's or the site's theme: th.want is $sl_theme 'site' (8 Nov 26, S.179), paper when blank, before the first apply.theme",
        "call $sl_theme('site', '', '', '', '', th.want) if th.want = '' then th.want = 'paper'" in head, head[-300:])
    row("R8 ... apply.theme asks for th.want, falls back to paper, and keeps in th.want the theme in force",
        ap.startswith("screen theme th.want returning th else if th.want # 'paper' then screen theme 'paper' returning th else null end call $sl_theme('name', '', '', '', '', th.want) end"), ap)
    row("R8 ... the Theme command takes the next theme the way every page does ($tk_theme, kept for the person) and keeps it in th.want",
        tc.startswith("call $tk_theme(1, th.chg, th.msg) call $sl_theme('name', '', '', '', '', th.want)"), tc)
    row("R8 ... and the screen taken back puts th.want on again (retake.quiet)", "gosub open.screen gosub apply.theme" in flat(label_block(ide, "retake.quiet") or ""))

    oc = ccode("opconfig")
    cfg = oc[:oc.find("op_pconfig")] if "op_pconfig" in oc else oc
    row("R6 CONFIG() has a 16 character name buffer and limit, and no 8 left in it", "char param[16 + 1];" in cfg and "k_get_c_string(descr, param, 16) < 1" in cfg and "k_get_c_string(descr, param, 8)" not in cfg)
    row("R6 ... the setter's buffer and limit are not touched", "char param[8 + 1];" in oc and "k_get_c_string(descr, param, 8) < 1" in oc, "")
    row("R6 ... SCREENTHEME has its branch", 'strcmp(param, "SCREENTHEME")' in cfg and "k_put_c_string(pcfg.screentheme, &result)" in cfg)
    # 8 Nov 26 (S.179): the default is the person's own theme (the record theme.<login name> of &menus&), else SCREENTHEME - site.theme says both
    row("R6 SCREEN OPEN's default asks site.theme, only when the program has not asked, and a refusal is not an error",
        "if not(th.asked) then gosub site.theme dn = st.name if dn # '' and dn # downcase(th.name) then a = dn gosub set.theme end end" in fl)
    st = flat(label_block(th, "site.theme") or "")
    row("R6 ... site.theme takes the person's record theme.<login name> of &menus& when it names a theme, else CONFIG('SCREENTHEME')",
        "open '&menus&' to st.f then" in st and "locate st.want in thorder<1> setting st.i then st.name = st.want" in st
        and "if st.name = '' then st.name = downcase(trim(config('SCREENTHEME')))" in st, st[:300])
    tid = flat(label_block(th, "theme.record.id") or "")
    row("R6 ... the record is per login name, in the session's own account (nothing outside it is read or written)",
        "st.id = 'theme.' : downcase(@logname)" in tid and "openpath" not in th.lower() and "openseq" not in th.lower(), tid)

    conf = raw("sd.conf")
    sec = None
    n_sd = n_all = 0
    for ln in conf.split("\n"):
        if ln.startswith("["):
            sec = ln.strip().lower()
        if ln.strip() == "SCREENTHEME=paper":
            n_all += 1
            n_sd += 1 if sec == "[sd]" else 0
    row("R7 the shipped sd.conf has SCREENTHEME=paper once, in [sd]", n_sd == 1 and n_all == 1 and len(re.findall(r"^SCREENTHEME=", conf, re.M)) == 1, "in [sd] %d, all %d" % (n_sd, n_all))
    tr = [ln for ln in raw("table").split("\n") if ln.startswith("SCREENTHEME|")]
    row("R7 the table has one SCREENTHEME row, which says blank is mono and that the shipped file sets paper, and no longer says it cannot be read",
        len(tr) == 1 and "Not readable" not in tr[0] and "Blank means mono" in tr[0] and "sets paper" in tr[0], repr(tr))
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
    mutant("the default theme is not asked of the configuration", "sl_theme", "if st.name = '' then st.name = downcase(trim(config('SCREENTHEME')))", "if st.name = '' then st.name = ''")
    mutant("the person's own theme is not read (S.179)", "sl_theme", "locate st.want in thorder<1> setting st.i then st.name = st.want", "st.i = 0")
    mutant("the person's theme is kept per account, not per person (S.179)", "sl_theme", "st.id = 'theme.' : downcase(@logname)", "st.id = 'theme'")
    mutant("SCREEN OPEN's default goes back to SCREENTHEME alone (S.179)", "sl_theme", "gosub site.theme\n            dn = st.name", "dn = downcase(trim(config('SCREENTHEME')))")
    mutant("tool.keys keeps its own list", "tool_keys", "   snames = 'normal'", "   themes = 'mono' : @fm : 'classic' : @fm : 'blue'\n   snames = 'normal'")
    mutant("tool.keys does not take the theme the pages' way", "tool_keys", "call $tk_std('theme', ctx, keys, '', std.r)", "std.r = ''")
    mutant("$tk_theme does not keep the theme for the person", "tk_theme", "call $sl_theme('save', now, '', '', '', kept)", "kept = 1")
    mutant("$tk_theme cycles nothing", "tk_theme", "call $sl_theme('next', now, '', '', '', want)", "want = now")
    mutant("the IDE starts in paper whatever the person or the site says", "ide", "   call $sl_theme('site', '', '', '', '', th.want)", "   th.want = ''")
    mutant("the IDE keeps a list of its own", "ide", "   if th.want = '' then th.want = 'paper'\n", "   if th.want = '' then th.want = 'paper'\n   themes = 'blue' : @fm : 'mono'\n")
    mutant("the IDE's theme command cycles nothing", "ide", "call $tk_theme(1, th.chg, th.msg)", "th.chg = 0")
    mutant("the IDE has no fallback to paper", "ide", "         screen theme 'paper' returning th else null\n", "")
    mutant("the IDE falls back to blue again", "ide", "   if th.want = '' then th.want = 'paper'\n", "   if th.want = '' then th.want = 'blue'\n")
    mutant("paper's menu bar back to black on cyan", "sl_theme", "         spec<-1> = 'bar=white,black,'", "         spec<-1> = 'bar=black,cyan,'")
    mutant("paper's menus the page's colours (no edge)", "sl_theme", "         spec<-1> = 'bar=white,black,'", "         spec<-1> = 'bar=black,white,'")
    mutant("paper's bar letter red again", "sl_theme", "         spec<-1> = 'hotkey.bar=brown,black,bold underline'", "         spec<-1> = 'hotkey.bar=red,black,'")
    mutant("paper's header bold again", "sl_theme", "         spec<-1> = 'header=black,white,underline'", "         spec<-1> = 'header=black,white,bold underline'")
    mutant("paper's normal is the terminal's own", "sl_theme", "         spec<-1> = 'normal=black,white,'\n", "")
    mutant("night's reverse loses reverse", "sl_theme", "         spec<-1> = 'reverse=white,black,reverse'", "         spec<-1> = 'reverse=white,black,'")
    mutant("night's text has no background", "sl_theme", "         spec<-1> = 'text=white,black,'\n         spec<-1> = 'header=brown,black,bold underline'", "         spec<-1> = 'text=white,,'\n         spec<-1> = 'header=brown,black,bold underline'")
    mutant("paper's syntax comment loses its background", "sl_theme", "   spec<-1> = 'comment=magenta,white,'", "   spec<-1> = 'comment=magenta,,'")
    mutant("night is not in the list", "sl_theme", " : @fm : 'night' : @fm : 'paper'", " : @fm : 'paper'")
    mutant("mono's focus back to plain reverse (highlight's look)", "sl_theme", "'focus=,,reverse bold underline'", "'focus=,,reverse'")
    mutant("paper gives no roles", "sl_theme", "         spec<-1> = 'focus=white,blue,bold underline'\n         gosub syntax.paper", "         gosub syntax.paper")
    mutant("CONFIG() buffer back to eight", "opconfig", "char param[16 + 1];", "char param[8 + 1];")
    mutant("CONFIG() limit back to eight", "opconfig", "k_get_c_string(descr, param, 16) < 1", "k_get_c_string(descr, param, 8) < 1")
    mutant("the setter widened", "opconfig", "  char param[8 + 1];\n", "  char param[16 + 1];\n")
    mutant("SCREENTHEME has no branch", "opconfig", 'strcmp(param, "SCREENTHEME")', 'strcmp(param, "SCREENTHEMX")')
    mutant("the shipped sd.conf has no theme", "sd.conf", "SCREENTHEME=paper\n", "")
    mutant("the shipped sd.conf says blue again", "sd.conf", "SCREENTHEME=paper", "SCREENTHEME=blue")
    mutant("the table says unreadable again", "table", "whatever this says.|no|", "whatever this says. Not readable with the CONFIG function.|no|")
    shutil.rmtree(t, ignore_errors=True)
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
