#!/usr/bin/env python3
"""test-modifya-multi-units.py - MODIFY.ACCOUNT with more than one action in one command (owner, 19 Oct 2026), as invariants read off modifya.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-modifya-multi-units.py
  python3 .../test-modifya-multi-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

THE RULE IT HOLDS.  A command of several actions is carried out WHOLE or not at all as far as its words go: validate.actions reads every word
first and refuses (stop) on an unknown word (11790), on two different words of one slot (11791: sh-on and sh-off, ssh and api; files-off with
files-write-on) and on add or delete among other words (11714), changing nothing; run.actions then does the words in the order of one list
whatever order they were typed, each through do.action, re-reading the account first, and ends with 11793 or 11794.  Silence about half of a
command, the fault of 18 Oct 2026, stays impossible.

THREE LISTS MUST AGREE and nothing but this check ties them: the word list of validate.actions (which is also the order of execution), the case
lines of do.action, and the words of the usage text.  A word added to one and not to another would be accepted and then ignored, or refused.

***IT READS modifya AS TEXT AND DOES NOT RUN BASIC.***  That the words are done, in the order, with the summary, is sandbox-gates.py section G
(rows "G: multi - ...").  A green run here is evidence that nothing has deleted or reordered the code that makes those rows true.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and each mutation to match its
text exactly once: an injection that changed nothing is not a test.

26 Oct 26, F6 (S.67 stage 2, alternative C): SDSYS-ON and SDSYS-OFF (M14 to M14c: the words, the slot SY they share with nothing else, set.sdsys's order and its three
helper commands, the read back; M15, M15b: messages 11977 to 11980) with their own mutants (F6_MUTANTS, first number M_F6), and `--selftest --from=N`, which runs the
mutants from number N on, so that a sitting that changes the F6 words does not pay for the others.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
MD = os.path.join(SDSYS, "gpl.bp", "modifya")
GPL = os.path.join(SDSYS, "gpl.bp")
MESSAGES = os.path.join(SDSYS, "messages")
NEW = ("11714", "11790", "11791", "11793", "11794")
NEW_F6 = ("11977", "11978", "11979", "11980")      # 26 Oct 26, F6: the lines set.sdsys prints


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else text[i:]


def in_order(text, *parts):
    """True when every part occurs in text, each after the one before; a part that is missing is False (a mutant may have taken it out)."""
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def checks(src, msgs):
    c = strip(src)
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    m_words = re.search(r"word\.arr = convert\(',', @fm, '([^']*)'\)", c)
    m_slots = re.search(r"slot\.arr = convert\(',', @fm, '([^']*)'\)", c)
    words = m_words.group(1).split(",") if m_words else []
    slots = m_slots.group(1).split(",") if m_slots else []
    do_action = between(c, "\ndo.action:\n", "\nadd.delete.arm:\n")
    case_words = re.findall(r"case action = '([A-Z.-]+)'", do_action)
    usage = between(c, "\nshow.usage:\n", "\n   return\n")
    usage_words = []
    for m in re.finditer(r"modify\.account <account> ([^']*)'", usage):
        for w in m.group(1).split("|"):
            w = w.strip()
            if w and "<" not in w and " " not in w:
                usage_words.append(w.upper())
    usage_words = [w for w in usage_words if w not in ("ADD", "DELETE")]

    ck("M0 the word list, the slot list, the case lines and the usage were all found (the null case: nothing to compare passes every row)",
       len(words) > 20 and len(slots) > 20 and len(case_words) > 20 and len(usage_words) > 20,
       "words %d slots %d cases %d usage %d" % (len(words), len(slots), len(case_words), len(usage_words)))
    ck("M1 the word list of validate.actions, the case lines of do.action and the words of the usage are ONE set",
       set(words) == set(case_words) == set(usage_words) and len(words) == len(set(words)),
       "list-only %s, case-only %s, usage-only %s" % (sorted(set(words) - set(case_words)), sorted(set(case_words) - set(words)),
                                                       sorted(set(usage_words) - set(words))))
    pairs_ok = len(words) == len(slots)
    for w, s in zip(words, slots):
        base = re.sub(r"-(ON|OFF)$", "", w)
        mate = [x for x, t in zip(words, slots) if re.sub(r"-(ON|OFF)$", "", x) == base and x != w]
        for x in mate:
            if slots[words.index(x)] != s:
                pairs_ok = False
    ck("M2 the slot list has a slot for every word, the ON and OFF of one gate share one, and the four route words share one",
       pairs_ok and len({s for w, s in zip(words, slots) if w in ("SSH", "API", "BOTH", "NONE")}) == 1, "slots %s" % slots)
    by_slot = {}
    for w, s in zip(words, slots):
        gate = "SUSPEND" if w in ("SUSPENDED", "UNSUSPENDED") else re.sub(r"-(ON|OFF)$", "", w)   # the two suspension words are one gate
        if w.startswith("START-"):
            gate = "START"                                                                        # 22 Oct 26: start-menu, start-terminal and start-default are one setting (slot ST)
        by_slot.setdefault(s, set()).add(gate if s != "R" else "R")
    set_ai = between(c, "\nset.ai:\n", "\nset.sdsys:\n")      # 26 Oct 26, F6: set.sdsys sits between set.ai and os.set
    ck("M13 AI-ON and AI-OFF (23 Oct 26, S.69 step 2): do.action sets ai.want true or false and calls set.ai; set.ai refuses a group account first, reads the group three-valued, answers 'already' before it "
       "looks for the Linux group (10024), changes the group through change.files.group (which reads it back) and prints 11606 from that read back, after the audit line",
       re.search(r"case action = 'AI-ON'\s*\n\s*ai\.want = @true\s*\n\s*gosub set\.ai\s*\n\s*return", do_action) is not None
       and re.search(r"case action = 'AI-OFF'\s*\n\s*ai\.want = @false\s*\n\s*gosub set\.ai\s*\n\s*return", do_action) is not None
       and set_ai != "" and in_order(set_ai, "if group.name[1,4] # 'sdu_' then", "has.ai = is_grp_member(files.user, 'sdaiusers')", "if has.ai = ai.want then", "ai.found = is_group('sdaiusers')",
                                    "cg.group = 'sdaiusers'", "gosub change.files.group", "kernel(K$AUDIT, 'modify.account ' : downcase(action)", "sysmsg(11606, acc.name, if cg.now then 'yes' else 'no')")
       and "os.execute" not in set_ai, "")
    ck("M2b ...and two different gates never share a slot (a shared slot would call sh-on with os-on a conflict)",
       all(len(v) == 1 for v in by_slot.values()), "%s" % {k: sorted(v) for k, v in by_slot.items() if len(v) > 1})
    # ---- 26 Oct 26, F6 (S.67 stage 2, alternative C): SDSYS-ON and SDSYS-OFF, the sdsys user in or out of a user account's group
    set_sd = between(c, "\nset.sdsys:\n", "\nos.set:\n")
    ck("M14 SDSYS-ON and SDSYS-OFF: do.action sets sdsys.want true or false and calls set.sdsys; the two words are in the list one after the other, share a slot (SY) that no other word has, and "
       "conflict only with each other",
       re.search(r"case action = 'SDSYS-ON'\s*\n\s*sdsys\.want = @true\s*\n\s*gosub set\.sdsys\s*\n\s*return", do_action) is not None
       and re.search(r"case action = 'SDSYS-OFF'\s*\n\s*sdsys\.want = @false\s*\n\s*gosub set\.sdsys\s*\n\s*return", do_action) is not None
       and "SDSYS-ON" in words and "SDSYS-OFF" in words and words.index("SDSYS-OFF") == words.index("SDSYS-ON") + 1
       and len(slots) == len(words) and slots[words.index("SDSYS-ON")] == slots[words.index("SDSYS-OFF")] == "SY" and slots.count("SY") == 2,
       "words %s slots %s" % (words, slots))
    ck("M14a set.sdsys: a group or other account is refused first (11979), then the group name is checked (valid_os_name), then the membership is read three-valued (is_grp_member and status()); "
       "SDSYS-OFF for an account that is not in the group says 'already' (10080) and changes nothing; the join comes before group-write, which runs for an account already switched on too",
       set_sd != "" and in_order(set_sd, "if group.name[1,4] # 'sdu_' then", "sysmsg(11979, acc.name)", "if not(valid_os_name(sdsys.group)) then", "has.sdsys = is_grp_member('sdsys', sdsys.group)",
                                 "sdsys.stat = status()", "if not(sdsys.want) and not(has.sdsys) then", "sysmsg(10080, acc.name)", "if sdsys.want then", "if not(has.sdsys) then",
                                 "sd-elevate sdsys-join ", "if sdsys.stat = 0 then gosub sdsys.group.write", "sd-elevate sdsys-leave ")
       and set_sd.count("sd-elevate sdsys-join ") == 1 and set_sd.count("sd-elevate sdsys-leave ") == 1 and set_sd.count("sd-elevate group-write ") == 1, "")
    ck("M14b ...the state is READ BACK from /etc/group after the change and a read back that does not show the wanted state is a failure (11980), never a success; the success path audits once "
       "(modify.account <word> account=<name>, lower case) and then prints 11977 or 11978",
       in_order(set_sd, "sdsys.now = is_grp_member('sdsys', sdsys.group)", "sdsys.stat = status()", "if sdsys.stat = 0 and sdsys.now # sdsys.want then sdsys.stat = 2", "if sdsys.stat # 0 then",
                "crt sysmsg(11980, acc.name, sdsys.step, sdsys.stat)", "return", "kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)", "crt sysmsg(11977, acc.name)",
                "crt sysmsg(11978, acc.name)") and set_sd.count("kernel(K$AUDIT") == 2
       # 26 Oct 26 (review of F6): a sdsys-on that put the user in the group and then failed is audited as incomplete, once, before the failure is said
       and in_order(set_sd, "if sdsys.joined then void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' incomplete account=' : acc.name)", "crt sysmsg(11980, acc.name, sdsys.step, sdsys.stat)")
       and "if sdsys.stat = 0 then sdsys.joined = @true" in set_sd, "")
    ck("M14c ...the user put in or out of the group is written in the helper's verb and never typed here: the only commands are sdsys-join GROUP, sdsys-leave GROUP and group-write PATH (quoted, and not run "
       "for a path with a quote in it), where GROUP is the account's own sdu_ group; no addgroup, delgroup, usermod or gpasswd and no register write",
       set_sd != "" and set_sd.count("os.execute") == 3 and not re.search(r"addgroup|delgroup|usermod|gpasswd", set_sd) and not re.search(r"(?m)^\s*(write|readu|delete)\s", set_sd)
       and 'os.execute "sudo /usr/local/sbin/sd-elevate sdsys-join " : sdsys.group' in set_sd and 'os.execute "sudo /usr/local/sbin/sd-elevate sdsys-leave " : sdsys.group' in set_sd
       and "index(sdsys.path, \"'\", 1)" in set_sd and "sd-elevate group-write '\" : sdsys.path : \"'\"" in set_sd, "")
    ck("M3 the order of execution (the word list): the routes first, files-on before files-write-on before files-admin-on, the suspension last",
       words[:4] == ["SSH", "API", "BOTH", "NONE"] and words and words[-2:] == ["SUSPENDED", "UNSUSPENDED"]
       and "FILES-ON" in words and "FILES-WRITE-ON" in words and "FILES-ADMIN-ON" in words
       and words.index("FILES-ON") < words.index("FILES-WRITE-ON") < words.index("FILES-ADMIN-ON"), "list %s" % words)

    g = c.find("if (action # 'ADD') and (action # 'DELETE') then")
    v = c.find("gosub validate.actions")
    r = c.find("gosub run.actions")
    t = c.find("goto add.delete.arm")
    ck("M4 the main flow: the guard (not ADD or DELETE), then validate, then run, then stop, then the goto that skips do.action for ADD / DELETE",
       0 <= g < v < r < t and c.count("gosub validate.actions") == 1 and c.count("gosub run.actions") == 1
       and "stop" in c[r:t] and c.count("goto add.delete.arm") == 1 and c.count("\nadd.delete.arm:\n") == 1,
       "guard %s validate %s run %s goto %s" % (g, v, r, t))

    val = between(c, "\nvalidate.actions:\n", "\nrun.actions:\n")
    stops = [m.start() for m in re.finditer(r"stop sysmsg\(", val)]
    ck("M5 validate.actions refuses with stop: ADD / DELETE 11714, an unknown word 11790, a conflict 11791 (four ways: a slot, files-off with files-write-on, and files-admin-on with files-off or files-write-off)",
       "stop sysmsg(11714, typed.list<i>)" in val and "stop sysmsg(11790, typed.list<i>)" in val
       and "stop sysmsg(11791, downcase(actions<i>), downcase(actions<j>))" in val and "stop sysmsg(11791, 'files-off', 'files-write-on')" in val
       and "stop sysmsg(11791, 'files-off', 'files-admin-on')" in val and "stop sysmsg(11791, 'files-write-off', 'files-admin-on')" in val
       and len(stops) == 6)
    ck("M5b ...each refusal sets the failure code first, and the add / delete test comes before the word lookup, which comes before the conflict test",
       all(val[max(0, s - 60):s].count("@system.return.code = -ER$ARGS") == 1 for s in stops)
       and 0 < val.find("(w = 'ADD')") < val.find("locate w in word.arr<1>") < val.find("if slot.arr<pi> = slot.arr<pj> then"))
    ck("M5c ...and it CHANGES NOTHING: no gosub, no write, no readu, no os.execute and no audit line in it",
       val != "" and not re.search(r"\bgosub\b|\bwrite\b|\breadu\b|os\.execute|K\$AUDIT", re.sub(r"'[^']*'", "''", val)))
    ck("M5d ...the conflict test compares DIFFERENT words only (the same word twice is one action)", "if actions<i> # actions<j> then" in val)

    run = between(c, "\nrun.actions:\n", "\nstart.set:\n")      # 22 Oct 26: start.set (S.75) sits between run.actions and set.suspended
    ck("M6 run.actions builds its list from word.arr (the fixed order), re-reads the account and clears the code before each action",
       "if want.at<p> then run.list<-1> = word.arr<p>" in run and 0 < run.find("read acc.rec from acc.f, acc.name else null")
       < run.find("@system.return.code = 0") < run.find("gosub do.action"))
    ck("M6b ...a failure leaves the rest to be tried, the summary only for more than one action: 11793 when none failed, else 11794",
       "if n.run > 1 then" in run and re.search(r"if undone\.list = '' then\s+crt sysmsg\(11793, acc\.name, n\.run,", run)
       and "crt sysmsg(11794, acc.name, done.said, change(undone.list, @fm, ', '))" in run
       and run.find("if n.run > 1 then") < run.find("11793") < run.find("11794"))
    ck("M6c ...the code after the run is 0 only when every action was carried out",
       re.search(r"if undone\.list = '' then\s+@system\.return\.code = 0\s+end else\s+@system\.return\.code = -ER\$FAILED\s+end\s+return\s*$", run.rstrip() + "\n") is not None)

    ck("M7 do.action has no stop (a stop would end the run after the first word), every case ends in return, and a word nobody knows is a failure (11790)",
       do_action != "" and not re.search(r"\bstop\b", do_action) and do_action.count("return") >= len(case_words)
       and "case 1\n         @system.return.code = -ER$ARGS\n         crt sysmsg(11790, downcase(action))" in do_action
       and do_action.rstrip().endswith("return"))
    add_arm = c[c.find("\nadd.delete.arm:\n"):]
    ck("M8 ADD and DELETE are as they were: a word after the user name is refused with 11714, and no other path reads extra.word",
       add_arm.count("stop sysmsg(11714, extra.word)") == 1 and c.count("extra.word") == 2, "extra.word lines: %d" % c.count("extra.word"))
    ck("M9 the usage says that several actions may be given together, with an example",
       "may be given together in one command" in usage and "modify.account <account> sh-on os-on voc-on bp-on" in usage)

    texts = {}
    for n in NEW:
        texts[n] = msgs.get(n)
    ck("M10 the five messages exist, end in a newline, and carry their words and their %n",
       all(texts[n] is not None and texts[n].endswith("\n") for n in NEW)
       and texts["11714"] is not None and "add and delete" in texts["11714"] and "%1" in texts["11714"] and "nothing was changed" in texts["11714"]
       and texts["11790"] is not None and "%1" in texts["11790"] and "modify.account" in texts["11790"] and "nothing was changed" in texts["11790"]
       and texts["11791"] is not None and "%1" in texts["11791"] and "%2" in texts["11791"] and "nothing was changed" in texts["11791"]
       and texts["11793"] is not None and all(x in texts["11793"] for x in ("%1", "%2", "%3", "carried out"))
       and texts["11794"] is not None and all(x in texts["11794"] for x in ("%1", "%2", "%3", "NOT every action")),
       "%s" % {n: (texts[n] or "MISSING")[:50] for n in NEW})
    ck("M10b ...no command word in them is in capitals (the lower-case rule)",
       all(texts[n] is not None and "MODIFY.ACCOUNT" not in texts[n] for n in NEW))
    cited = {}
    for fn in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, fn)
        if fn == "modifya" or not os.path.isfile(p):
            continue
        try:
            body = open(p, encoding="latin-1").read()
        except OSError:
            continue
        for n in ("11790", "11791", "11793", "11794"):
            if "sysmsg(%s" % n in body and not (n == "11791" and fn == "createa"):       # 26 Oct 26 (S.75, home): CREATE.ACCOUNT refuses START-MENU with START-TERMINAL in the words MODIFY.ACCOUNT uses (the same message, "same messages where they exist")
                cited.setdefault(n, []).append(fn)
    ck("M10c ...and 11790, 11791, 11793 and 11794 are cited by modifya alone (no other program has taken the number), except that createa says 11791 for two start words", not cited, "%s" % cited)
    # ---- 26 Oct 26, F6: the four lines of set.sdsys
    f6 = {n: msgs.get(n) for n in NEW_F6}
    ck("M15 messages 11977 to 11980 (F6) exist, end in a newline, are one line each and carry their %n: 11977 and 11978 say master edits are on or off and name the sdsys user (11977 also says to sign "
       "on again), 11979 says it is not a user account and that nothing was changed, 11980 has the account, the step that failed and the status",
       all(f6[n] is not None and f6[n].endswith("\n") and f6[n].count("\n") == 1 and "%1" in f6[n] for n in NEW_F6)
       and "master edits are on" in (f6["11977"] or "") and "sdsys" in (f6["11977"] or "") and "Sign on again" in (f6["11977"] or "")
       and "master edits are off" in (f6["11978"] or "") and "sdsys" in (f6["11978"] or "")
       and "is not a user account" in (f6["11979"] or "") and "Nothing was changed" in (f6["11979"] or "")
       and all(x in (f6["11980"] or "") for x in ("%1", "%2", "%3")),
       "%s" % {n: (f6[n] or "MISSING")[:50] for n in NEW_F6})
    ck("M15b ...no command word in them is in capitals, and the numbers are cited by modifya alone", all(f6[n] is not None and "MODIFY.ACCOUNT" not in f6[n] for n in NEW_F6)
       and all(("sysmsg(%s" % n) in strip(src) for n in NEW_F6) and not any(
           ("sysmsg(%s" % n) in open(os.path.join(GPL, fn), encoding="latin-1").read() for n in NEW_F6 for fn in os.listdir(GPL) if fn != "modifya" and os.path.isfile(os.path.join(GPL, fn))),
       "")
    return rows


def load(path=MD):
    with open(path, encoding="latin-1") as f:
        src = f.read()
    msgs = {}
    for n in NEW + NEW_F6:
        p = os.path.join(MESSAGES, n)
        if os.path.isfile(p):
            with open(p, encoding="latin-1") as f:
                msgs[n] = f.read()
    return src, msgs


def report(rows, quiet=False):
    bad = 0
    for name, ok, detail in rows:
        if not ok:
            bad += 1
        if not quiet or not ok:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
    return bad


MUTANTS = [
    ("validate.actions is never called", "      gosub validate.actions\n", ""),
    ("run.actions is called before validate.actions", "      gosub validate.actions\n      gosub run.actions\n", "      gosub run.actions\n      gosub validate.actions\n"),
    ("a word is missing from the word list", ",NET-OFF,SHARED-READ-ON,", ",SHARED-READ-ON,"),
    ("the usage forgets a word", "voc-on | voc-off | bp-on | bp-off | dict-on | dict-off", "voc-on | voc-off | bp-on | dict-on | dict-off"),
    ("sh-on and os-on share a slot", "'R,R,R,R,SH,SH,OS,OS,", "'R,R,R,R,SH,SH,SH,SH,"),
    ("files-write-on runs before files-on", "FILES-ON,FILES-OFF,FILES-WRITE-ON,FILES-WRITE-OFF,FILES-ADMIN-ON", "FILES-WRITE-ON,FILES-WRITE-OFF,FILES-ON,FILES-OFF,FILES-ADMIN-ON"),
    ("files-admin-on runs before files-write-on (21 Oct 26, S.73 item 3)", "FILES-WRITE-ON,FILES-WRITE-OFF,FILES-ADMIN-ON,FILES-ADMIN-OFF,AI-ON", "FILES-ADMIN-ON,FILES-ADMIN-OFF,FILES-WRITE-ON,FILES-WRITE-OFF,AI-ON"),
    ("the suspension runs first", "PINS-OFF,SUSPENDED,UNSUSPENDED'", "PINS-OFF,UNSUSPENDED,SUSPENDED'"),
    ("the start and pins words run after the suspension (22 Oct 26, S.75)", "SDSYS-OFF,START-MENU,START-TERMINAL,START-DEFAULT,PINS-ON,PINS-OFF,SUSPENDED,UNSUSPENDED'", "SDSYS-OFF,SUSPENDED,UNSUSPENDED,START-MENU,START-TERMINAL,START-DEFAULT,PINS-ON,PINS-OFF'"),
    ("the pins words share the start slot (22 Oct 26, S.75)", "SY,SY,ST,ST,ST,PN,PN,S,S')", "SY,SY,ST,ST,ST,ST,ST,S,S')"),
    # 23 Oct 26, S.69 step 2: the AI words
    ("ai-on is missing from the word list (23 Oct 26, S.69 step 2)", ",FILES-ADMIN-OFF,AI-ON,AI-OFF,SDSYS-ON", ",FILES-ADMIN-OFF,AI-OFF,SDSYS-ON"),
    ("the ai words share the files-admin slot (23 Oct 26, S.69 step 2)", "FA,FA,AI,AI,SY", "FA,FA,FA,FA,SY"),
    ("the usage forgets the ai words (23 Oct 26, S.69 step 2)", "   crt '                 modify.account <account> ai-on | ai-off'\n", ""),
    ("set.ai says yes without reading the group back (23 Oct 26, S.69 step 2)", "crt sysmsg(11606, acc.name, if cg.now then 'yes' else 'no')", "crt sysmsg(11606, acc.name, if ai.want then 'yes' else 'no')"),
    ("set.ai does not refuse a group account (23 Oct 26, S.69 step 2)", "set.ai:\n   if group.name[1,4] # 'sdu_' then", "set.ai:\n   if @false then"),
    ("set.ai changes the group without sd-elevate's reading back (23 Oct 26, S.69 step 2)", "   cg.group = 'sdaiusers'\n   cg.want = ai.want\n   gosub change.files.group\n", "   cg.group = 'sdaiusers'\n   cg.want = ai.want\n   cg.now = ai.want\n"),
    ("a case of do.action ends in stop", "         gosub os.set\n         return\n      case action = 'SH-OFF'", "         gosub os.set\n         stop\n      case action = 'SH-OFF'"),
    ("the account is not read again before each action", "      read acc.rec from acc.f, acc.name else null\n", ""),
    ("the code is not cleared before each action", "      @system.return.code = 0\n      gosub do.action\n", "      gosub do.action\n"),
    ("the summary is printed for one action too", "   if n.run > 1 then\n", "   if @true then\n"),
    ("the summary always says every action was carried out", "      if undone.list = '' then\n         crt sysmsg(11793", "      if @true then\n         crt sysmsg(11793"),
    ("a failed run ends with code 0", "   end else\n      @system.return.code = -ER$FAILED\n   end\n   return\n", "   end else\n      @system.return.code = 0\n   end\n   return\n"),
    ("an unknown word is not refused", "         stop sysmsg(11790, typed.list<i>)", "         null"),
    ("the slot conflict is not tested", "            if slot.arr<pi> = slot.arr<pj> then", "            if @false then"),
    ("files-off with files-write-on is not refused", "         stop sysmsg(11791, 'files-off', 'files-write-on')", "         null"),
    ("files-off with files-admin-on is not refused (21 Oct 26, S.73 item 3)", "         stop sysmsg(11791, 'files-off', 'files-admin-on')", "         null"),
    ("files-write-off with files-admin-on is not refused (21 Oct 26, S.73 item 3)", "         stop sysmsg(11791, 'files-write-off', 'files-admin-on')", "         null"),
    ("add or delete among other words is accepted", "      if (w = 'ADD') or (w = 'DELETE') then", "      if @false then"),
    ("validate.actions does an action", "   n.words = dcount(actions, @fm)\n   pos.of = ''\n", "   n.words = dcount(actions, @fm)\n   gosub set.suspended\n   pos.of = ''\n"),
    ("the same word twice is a conflict", "         if actions<i> # actions<j> then", "         if @true then"),
    ("DELETE is no longer kept for the old arm", "if (action # 'ADD') and (action # 'DELETE') then\n      actions = action", "if (action # 'ADD') then\n      actions = action"),
    ("the goto that skips do.action for ADD is gone", "   goto add.delete.arm\n", ""),
    ("the 18 Oct refusal of a second word is back", "   typed.first = action\n   action = upcase(action)\n", "   typed.first = action\n   action = upcase(action)\n   call @parser(PARSER$GET.TOKEN, token.type, extra.word, keyword)\n   if token.type # PARSER$END then stop sysmsg(11714, extra.word)\n"),
    ("the usage no longer says several actions may be given", "may be given together in one command", "may be given one at a time"),
]
MSG_MUTANTS = [
    ("message 11793 loses its list", "11793", "%3", "(none)"),
    ("message 11794 does not say NOT", "11794", "NOT every action was carried out", "every action was carried out"),
    ("message 11714 says the old thing", "11714", "add and delete take a user name and stand alone", "modify.account does one action at a time"),
    ("message 11791 loses its second word", "11791", "%2", "that"),
    ("message 11790 has a capital command", "11790", "is not a modify.account action", "is not a MODIFY.ACCOUNT action"),
]


# ---- 26 Oct 26, F6 (S.67 stage 2, alternative C): the mutants of SDSYS-ON and SDSYS-OFF.  M_F6 is the number of the first, for `--selftest --from=N`, so that a sitting that
# ---- changes only these runs only these.  Each is (name, kind, message number or None, old, new): kind "src" mutates modifya, kind "msg" mutates one message.
M_F6 = len(MUTANTS) + len(MSG_MUTANTS)
_SDS = "set.sdsys:\n   sdsys.stat = 0 ; sdsys.step = '' ; sdsys.path = '' ; sdsys.now = @false ; has.sdsys = @false ; sdsys.joined = @false\n"
F6_MUTANTS = [
    ("sdsys-on is missing from the word list", "src", None, ",AI-ON,AI-OFF,SDSYS-ON,SDSYS-OFF,START-MENU", ",AI-ON,AI-OFF,SDSYS-OFF,START-MENU"),
    ("the sdsys words share the ai slot", "src", None, "AI,AI,SY,SY,ST", "AI,AI,AI,AI,ST"),
    ("the sdsys words share the slot of the SD.ACCOUNTS gate", "src", None, "AI,AI,SY,SY,ST", "AI,AI,SD,SD,ST"),
    ("the usage forgets the sdsys words", "src", None, "   crt '                 modify.account <account> sdsys-on | sdsys-off'\n", ""),
    ("set.sdsys does not refuse a group account", "src", None, _SDS + "   if group.name[1,4] # 'sdu_' then", _SDS + "   if @false then"),
    ("set.sdsys does not read the membership", "src", None, "   has.sdsys = is_grp_member('sdsys', sdsys.group)\n", "   has.sdsys = @true\n"),
    ("sdsys-off runs the helper for an account that is not in the group", "src", None, "   if not(sdsys.want) and not(has.sdsys) then\n", "   if @false then\n"),
    ("sdsys-on does not run group-write", "src", None, "      if sdsys.stat = 0 then gosub sdsys.group.write\n", ""),
    ("the state is not read back", "src", None, "      if sdsys.stat = 0 and sdsys.now # sdsys.want then sdsys.stat = 2\n", ""),
    ("a failed step is not said", "src", None, "      crt sysmsg(11980, acc.name, sdsys.step, sdsys.stat)  ;* Account %1: %2 failed, status %3\n", ""),
    ("the success is not audited", "src", None, "   void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   if sdsys.want then crt sysmsg(11977", "   if sdsys.want then crt sysmsg(11977"),
    ("the two lines are swapped", "src", None, "if sdsys.want then crt sysmsg(11977, acc.name) else crt sysmsg(11978, acc.name)", "if sdsys.want then crt sysmsg(11978, acc.name) else crt sysmsg(11977, acc.name)"),
    ("the user put in the group is the one typed", "src", None, '"sudo /usr/local/sbin/sd-elevate sdsys-join " : sdsys.group', '"sudo /usr/local/sbin/sd-elevate addgroup " : @logname : " " : sdsys.group'),
    ("sdsys-off is a delgroup", "src", None, '"sudo /usr/local/sbin/sd-elevate sdsys-leave " : sdsys.group', '"sudo /usr/local/sbin/sd-elevate delgroup sdsys " : sdsys.group'),
    ("a path with a quote in it is handed to the shell", "src", None, "or index(sdsys.path, \"'\", 1) then", "then"),
    ("the register is written", "src", None, "   if sdsys.want then crt sysmsg(11977", "   write acc.rec to acc.f, acc.name\n   if sdsys.want then crt sysmsg(11977"),
    ("a sdsys-on that joined and then failed leaves no audit line", "src", None, "      if sdsys.joined then void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' incomplete account=' : acc.name)\n", ""),
    ("message 11977 forgets to say sign on again", "msg", "11977", "Sign on again as SDSYS", "Remember it"),
    ("message 11978 says on", "msg", "11978", "master edits are off", "master edits are on"),
    ("message 11979 forgets that nothing was changed", "msg", "11979", " Nothing was changed", ""),
    ("message 11980 loses the status", "msg", "11980", "status %3", "status"),
    ("message 11980 has a capital command", "msg", "11980", "failed, status", "failed, MODIFY.ACCOUNT status"),
]


def selftest():
    src, msgs = load()
    base = [n for n, ok, _ in checks(src, msgs) if not ok]
    if base:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base), file=sys.stderr)
        return 2
    start = 0
    for a in sys.argv[1:]:
        if a.startswith("--from="):
            start = int(a.split("=", 1)[1])
    holes = 0
    ran = 0
    print("--- self-test: the unmutated source passes; each mutation must be CAUGHT and match its text once%s ---" % ("" if start == 0 else " (from mutant %d: M_F6 is %d)" % (start, M_F6)))
    seq = ([(name, "src", None, old, new) for name, old, new in MUTANTS] + [(name, "msg", n, old, new) for name, n, old, new in MSG_MUTANTS] + F6_MUTANTS)
    for i, (name, kind, n, old, new) in enumerate(seq):
        if i < start:
            continue
        ran += 1
        if kind == "src":
            if src.count(old) != 1:
                print("  [FAIL] %s: the text to mutate matches %d times, not once (this test no longer understands the source)" % (name, src.count(old)))
                holes += 1
                continue
            caught = [x for x, ok, _ in checks(src.replace(old, new), msgs) if not ok]
        else:
            if msgs.get(n, "").count(old) != 1:
                print("  [FAIL] %s: message %s text matches %d times, not once" % (name, n, msgs.get(n, "").count(old)))
                holes += 1
                continue
            m2 = dict(msgs)
            m2[n] = msgs[n].replace(old, new)
            caught = [x for x, ok, _ in checks(src, m2) if not ok]
        if caught:
            print("  [pass] %s: caught by %s" % (name, ", ".join(caught[:3])))
        else:
            print("  [FAIL] %s: NOT CAUGHT by any check" % name)
            holes += 1
    if ran == 0:
        print("REFUSING - no mutant ran (--from is past the end: %d mutants)" % len(seq), file=sys.stderr)
        return 2
    print("\n%d of %d mutants caught, %d missed" % (ran - holes, ran, holes))
    return 1 if holes else 0


def main():
    if not os.path.isfile(MD):
        print("test-modifya-multi-units: CANNOT RUN - %s is not readable" % MD, file=sys.stderr)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    src, msgs = load()
    print("test-modifya-multi-units: %s" % MD)
    rows = checks(src, msgs)
    bad = report(rows)
    print("\ntest-modifya-multi-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
