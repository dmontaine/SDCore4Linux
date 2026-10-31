#!/usr/bin/env python3
"""test-createhook-units.py - S.92: the fill hook of create_account (CA$AFTER), as invariants.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-createhook-units.py
  python3 .../test-createhook-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed.  Written 30 Oct 26 with the hook (owner: "Yes, add the hook").

  A  the two settings positions (45, 46) are in createacc.h and used nowhere else
  B  the hook is refused BEFORE anything is made: only '!tape_fill', only a USER or GROUP account, no ATTACH, no reused user, not the shared account (11919)
  C  the call is made once, inside make.account, after the last thing it makes and BEFORE the VOC is handed over
  D  the paths the filler returns are checked (inside the new directory, no quote, no dot-dot) BEFORE the first is handed over, and a bad one is a refusal (11922)
  E  a refusal removes what THIS call made, in the order directory, Linux user (USER only), group; the register record is written after both places, so a refused fill leaves none
  F  the messages 11919 to 11922 exist

***IT READS create_account AS TEXT AND DOES NOT RUN BASIC.*** It cannot say that a directory is removed or that a file is handed over: a sandbox cannot make Linux users, so the runtime
rows are the VM witness of the verb that uses the hook.  A green run is evidence that nothing has deleted or reordered the code, nothing more.

--selftest mutates the source in the ways the hook could plausibly be broken and requires each mutation to be CAUGHT and to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
CA = os.path.join(SDSYS, "gpl.bp", "create_account")
HEADER = os.path.join(SDSYS, "syscom", "createacc.h")
MESSAGES = os.path.join(SDSYS, "messages")

ALLOW = "after.name # '!tape_fill'"
REFUSE_ARGS = "(acc.type # 'USER' and acc.type # 'GROUP') or settings<CA$ATTACH> = 1 or reuse.sd.user or acc.shared"
CALL = "call @after.name(pathname, after.arg, made, ferr)"
PREFIX = "set.owner.path[1, len(pathname) + 1] # pathname : @ds"
QUOTE = 'index(set.owner.path, "\'", 1)'
DOTDOT = "index(set.owner.path, @ds : '..' : @ds, 1)"
DOTDOT_END = "set.owner.path[len(set.owner.path) - 2, 3] = @ds : '..'"
VOC_HAND = "set.owner.path = pathname:@ds:'voc'"
RMTREE = 'os.execute "sudo /usr/local/sbin/sd-elevate rmtree-account \'" : pathname : "\'"'
UDHOME = 'os.execute "sudo /usr/local/sbin/sd-elevate userdel-home " : acc.uname'
GROUPDEL = 'os.execute "sudo /usr/local/sbin/sd-elevate groupdel " : group_name'


def code_lines(src):
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("*"):
            continue
        out.append((i, line))
    return out


def first(lines, needle, start=0):
    for k in range(start, len(lines)):
        if needle in lines[k][1]:
            return k
    return None


def n_of(lines, needle):
    return sum(1 for _, t in lines if needle in t)


def check(src, header, messages):
    rows = []

    def row(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    L = code_lines(src)

    # ---- A
    row("A1 CA$AFTER is 45 and CA$AFTER.ARG is 46 in createacc.h",
        re.search(r"(?m)^\$define CA\$AFTER\s+45\b", header) is not None and re.search(r"(?m)^\$define CA\$AFTER\.ARG\s+46\b", header) is not None)
    nums = re.findall(r"(?m)^\$define CA\$\S+\s+(\d+)\b", header)
    row("A2 no position of the settings is used twice", len(nums) == len(set(nums)), "duplicates: %r" % sorted(set(n for n in nums if nums.count(n) > 1)))

    # ---- B
    p_allow = first(L, ALLOW)
    p_make = first(L, "create.file pathname directory on error")
    p_group = first(L, "gosub create.group")
    p_user = first(L, "if not(create_user(acc.uname)) then")
    row("B1 the only name accepted is !tape_fill", p_allow is not None and n_of(L, ALLOW) == 1 and re.findall(r"'![a-z_.]+'", L[p_allow][1]) == ["'!tape_fill'"]
        and " and after.name" not in L[p_allow][1] and src.count("!tape_fill") >= 2)
    row("B2 the refusal also asks type, ATTACH, a reused user and the shared account", p_allow is not None and REFUSE_ARGS in L[p_allow][1])
    row("B3 the refusal says 11919 and returns", p_allow is not None and "err = 11919" in L[p_allow + 3][1] + L[p_allow + 2][1] and "return" in L[p_allow + 3][1] + L[p_allow + 4][1])
    row("B4 it comes before the account directory, the groups and the Linux user are made",
        None not in (p_allow, p_make, p_group, p_user) and p_allow < p_make and p_allow < p_group and p_allow < p_user)

    # ---- C
    p_call = first(L, CALL)
    p_run = first(L, "gosub run.after")
    p_makeacc = first(L, "make.account:")
    p_voc = first(L, VOC_HAND, p_makeacc or 0)
    p_cat = first(L, "Unable to create private catalogue directory")
    row("C1 the filler is called once", n_of(L, CALL) == 1)
    row("C2 it is run from make.account, after the private catalogue directory and before the VOC is handed over",
        None not in (p_run, p_voc, p_cat, p_makeacc) and p_makeacc < p_cat < p_run < p_voc)
    row("C3 a refusal returns from make.account at once", p_run is not None and "if err # '' then return" in L[p_run + 1][1])
    row("C4 only when the hook was asked for", p_run is not None and "if after.name # '' then" in L[p_run - 1][1])

    # ---- D
    p_ra = first(L, "run.after:")
    p_loop = first(L, "for i.made = 1 to n.made", p_ra or 0)
    p_bad = first(L, "err = 11922", p_ra or 0)
    p_hand = first(L, "gosub set.owner", p_loop or 0)
    p_pref = first(L, PREFIX, p_ra or 0)
    row("D1 the check names the new directory, a quote and a dot-dot component (inside and at the end)",
        p_pref is not None and all(x in L[p_pref][1] for x in (QUOTE, DOTDOT, DOTDOT_END)))
    row("D2 it is made for each path BEFORE that path is handed over", None not in (p_loop, p_pref, p_bad, p_hand) and p_loop < p_pref < p_bad < p_hand)
    row("D3 a bad path is a refusal that removes the account (11922, after.failed)",
        p_bad is not None and "after.failed = @true" in L[p_bad + 1][1] + L[p_bad + 2][1] and "return" in L[p_bad + 2][1] + L[p_bad + 3][1])
    row("D4 a refusal of the filler is an error of the account too, with after.failed",
        p_call is not None and "err = ferr" in L[p_call + 3][1] + L[p_call + 4][1] and "after.failed = @true" in L[p_call + 4][1] + L[p_call + 5][1])
    p_unw_label = first(L, "unwind.new:")
    row("D5 run.after hands over in one place only, and that place is after the check",
        None not in (p_ra, p_unw_label) and sum(1 for k in range(p_ra, p_unw_label) if "gosub set.owner" in L[k][1]) == 1)

    # ---- E
    p_main = first(L, "gosub make.account")
    p_unw = first(L, "gosub unwind.new")
    p_exit = first(L, "goto exit.create", p_main or 0)
    p_reg = first(L, "write acc.rec to acc.f, acc.name")
    row("E1 after make.account a failed fill is unwound before the routine ends",
        None not in (p_main, p_unw, p_exit) and p_main < p_unw < p_exit and "if after.failed then gosub unwind.new" in L[p_unw][1])
    row("E2 the register record is written after that, so a refused fill leaves none", None not in (p_unw, p_reg) and p_unw < p_reg)
    p_u = first(L, "unwind.new:")
    p_rm = first(L, RMTREE, p_u or 0)
    p_ud = first(L, UDHOME, p_u or 0)
    p_gd = first(L, GROUPDEL, p_u or 0)
    p_ok = first(L, "crt sysmsg(11920, acc.name)", p_u or 0)
    p_no = first(L, "crt sysmsg(11921, acc.name, unwind.stat)", p_u or 0)
    row("E3 it removes the directory, then the Linux user and its home, then the group", None not in (p_u, p_rm, p_ud, p_gd) and p_u < p_rm < p_ud < p_gd)
    row("E4 the user is removed for a USER account only, and the group only when this call made one",
        p_ud is not None and "if acc.type = 'USER' then" in L[p_ud - 1][1] and p_gd is not None and "if group_name # '' then" in L[p_gd - 1][1])
    row("E5 it says 11920 when all went and 11921 with the step when not", None not in (p_ok, p_no) and p_ok < p_no and "if unwind.stat = 0 then" in L[p_ok - 1][1])
    row("E6 nothing in the unwind removes by a shell command of its own", p_u is not None and not any(re.search(r"\brm\b|\bdelete\b", L[k][1]) for k in range(p_u, (p_ok or p_u) + 1)))
    row("E7 the removal is single-quoted for the helper and the helper's refusal of anything but an account directory still holds",
        p_rm is not None and "rmtree-account '" in L[p_rm][1])

    # ---- F
    for n, needle in ((11919, "only for a new user or group account"), (11920, "removed again"), (11921, "removing it again also failed"), (11922, "not inside the new account")):
        txt = messages.get(n, "")
        row("F %d exists and says what it should" % n, needle in txt, repr(txt)[:80])
    return rows


MUTANTS = [
    ("allow-list widened", ALLOW, "after.name # '!tape_fill' and after.name # '!other'"),
    ("type check out", "(acc.type # 'USER' and acc.type # 'GROUP') or ", ""),
    ("ATTACH allowed", " or settings<CA$ATTACH> = 1", ""),
    ("reused user allowed", " or reuse.sd.user or acc.shared", " or acc.shared"),
    ("shared allowed", "or reuse.sd.user or acc.shared then", "or reuse.sd.user then"),
    ("hook run after the VOC handover", "   if after.name # '' then\n      gosub run.after\n      if err # '' then return\n   end\n\n   set.owner.path = pathname:@ds:'voc'\n   gosub set.owner",
     "   set.owner.path = pathname:@ds:'voc'\n   gosub set.owner\n   if after.name # '' then\n      gosub run.after\n      if err # '' then return\n   end"),
    ("call twice", "   call @after.name(pathname, after.arg, made, ferr)\n", "   call @after.name(pathname, after.arg, made, ferr)\n   call @after.name(pathname, after.arg, made, ferr)\n"),
    ("prefix check out", "set.owner.path[1, len(pathname) + 1] # pathname : @ds or ", ""),
    ("quote check out", " or index(set.owner.path, \"'\", 1)", ""),
    ("dot-dot check out", " or index(set.owner.path, @ds : '..' : @ds, 1)", ""),
    ("bad path not a failure", "         err = 11922:@vm:set.owner.path[1, 120] ;* The fill step named a path that is not inside the new account\n         after.failed = @true\n",
     "         err = 11922:@vm:set.owner.path[1, 120] ;* The fill step named a path that is not inside the new account\n"),
    ("filler refusal not unwound", "      err = ferr\n      after.failed = @true\n", "      err = ferr\n"),
    ("no unwind in the main flow", "      if after.failed then gosub unwind.new\n", ""),
    ("directory not removed", "   os.execute \"sudo /usr/local/sbin/sd-elevate rmtree-account '\" : pathname : \"'\"\n", ""),
    ("user removed for every type", "   if acc.type = 'USER' then\n      os.execute \"sudo /usr/local/sbin/sd-elevate userdel-home \"", "   if 1 then\n      os.execute \"sudo /usr/local/sbin/sd-elevate userdel-home \""),
    ("group removed without a group", "   if group_name # '' then\n      os.execute \"sudo /usr/local/sbin/sd-elevate groupdel \"", "   if 1 then\n      os.execute \"sudo /usr/local/sbin/sd-elevate groupdel \""),
    ("success always said", "   if unwind.stat = 0 then\n      crt sysmsg(11920", "   if 1 then\n      crt sysmsg(11920"),
]


def load():
    src = open(CA, encoding="utf-8").read()
    header = open(HEADER, encoding="utf-8").read()
    messages = {}
    for n in (11919, 11920, 11921, 11922):
        p = os.path.join(MESSAGES, str(n))
        messages[n] = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    return src, header, messages


def main(argv):
    src, header, messages = load()
    rows = check(src, header, messages)
    bad = [r for r in rows if not r[1]]
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
    print("%d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    if bad:
        return 1
    if "--selftest" not in argv:
        return 0
    live = 0
    for n, (name, old, new) in enumerate(MUTANTS):
        if src.count(old) != 1:
            print("  [BAD ] mutant %d (%s): the old text occurs %d times" % (n, name, src.count(old)))
            live += 1
            continue
        mrows = check(src.replace(old, new), header, messages)
        caught = [r for r in mrows if not r[1]]
        print("  [%s] mutant %2d %-40s %s" % ("KILL" if caught else "LIVE", n, name, ("%d failed, first: %s" % (len(caught), caught[0][0][:60])) if caught else ""))
        if not caught:
            live += 1
    print("%d mutants, %d survived" % (len(MUTANTS), live))
    return 1 if live else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
