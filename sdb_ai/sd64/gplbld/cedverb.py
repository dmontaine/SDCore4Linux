#!/usr/bin/env python3
# cedverb.py - gives a sandbox the `ced` verb again, for the suites that drive the CED program by typing it.
#
# 29 Oct 26, S.88 g-P1 (owner answer 16 of 29 Oct): the `ced` verb was retired - sdsys/voc_template/ced and sdsys/newvoc/ced are gone and
# sdsys/voc_removed/ced removes the record from an account that has it.  gpl.bp/ced stays in the tree as an UNSHIPPED TEST DRIVER and `$ced` stays
# in the global catalogue, so the suites that type CED need only the VOC record, written here as the administrator after the sandbox is built
# (the idiom of sandbox-tk-base.py's zztkvoc).  Nothing here is part of a shipped system.
#
#   import cedverb; cedverb.install(box)                 # the sandbox's SDSYS account; returns True when the record was written
#   cedverb.install(box, account)                          # a fixture account's own VOC (an ordinary session in it, `sd -a<account>`)
#
# It does what the null case demands: it prints what it ran, and it FAILS (returns False, says why) when the success line is absent; a caller
# that gets False must stop with exit 2, not carry on to a run that can only be red.
#
# The record is written into the VOC of the account the sandbox's own sessions sign on to (the SDSYS account of the sandbox).  A fixture account
# made by sandbox-gates.py has its own VOC from newvoc, which does not hold `ced`; the one suite that types CED in a fixture account
# (sandbox-ai-apps.py) names the account.

import os
import re
import subprocess

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PROG = "zzcedverb"
DONE = "CEDVERB done"


def _sess(box, *cmds):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd"), "-internal"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=os.path.join(box, "sys"), env=env)
    try:
        out, _ = p.communicate(body.encode("latin-1"), timeout=300)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        return ""
    return ANSI.sub("", out.decode("latin-1", "replace")).split(":TERM 200,9999", 1)[-1]


def install(box, account=None):
    """Write the VOC record `ced` (V / CA / $ced) into the VOC of the sandbox's SDSYS account, or of the fixture account `account` (its voc file is opened
    by pathname, as sandbox-home.py's zzdel does); True only when the program printed its success line and no refusal."""
    path = os.path.join(box, "sys", "bp", PROG)
    opener = "open 'VOC' to v else" if not account else "openpath '%s' to v else" % os.path.join(box, "user_accounts", account, "voc")
    with open(path, "w", encoding="latin-1") as f:
        f.write("$internal\n   " + opener + " crt 'CEDVERB no voc' ; stop\n   write 'V':@fm:'CA':@fm:'$ced' to v, 'ced'\n"
                "   read r from v, 'ced' else crt 'CEDVERB not written' ; stop\n   if r<3> # '$ced' then crt 'CEDVERB wrong record' ; stop\n   crt '" + DONE + "'\nend\n")
    out = _sess(box, "BASIC bp " + PROG, "RUN bp " + PROG)
    ok = re.search(r"^" + DONE + r"\s*$", out, re.M) is not None and "CEDVERB no voc" not in out and "CEDVERB not written" not in out \
        and "CEDVERB wrong record" not in out
    print("cedverb: the VOC record ced (V / CA / $ced) %s in the VOC of %s" % ("written" if ok else "NOT WRITTEN", account or "the sandbox's SDSYS account (" + box + ")"))
    if not ok:
        print("cedverb: output was:\n" + out[-600:])
    return ok
