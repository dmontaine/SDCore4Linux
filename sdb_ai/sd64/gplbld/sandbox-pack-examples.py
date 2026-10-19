#!/usr/bin/env python3
#
# sandbox-pack-examples.py - the generated knowledge pack (agent-pack/pack) against a RUNNING SD.  S.69 row 1b.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-pack-examples.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree (it must be
# empty or absent).  SDBOX_KEYSET=n picks the keys.  Exit 0 every row passed, 1 one failed, 2 it could not run.  Stop the sandbox with
# sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 19 Oct 26 dm  Written for S.69 row 1b (evaluation 5A.2b, "the example runner"): gplbld/test-pack-units.py proves the pack equals a
#               build from the SOURCES; this proves the sources are what a built SD actually holds.  The pack is read AS COMMITTED,
#               not regenerated, so a stale pack and a drifted SD are both findings.
# END-HISTORY
#
# WHAT IT RUNS.  The sandbox's SDSYS account is built from sdsys/voc_template, and its dictionaries are written by write_install_dicts
# from gplbld/FILES_DICTS.  The pack quotes both.  For each:
#   1. VERBS     every tcl: verb chunk says how the verb dispatches (type, mode, target).  A BASIC program reads the VOC record of the
#                running SD and compares.  A verb the pack names that the VOC does not hold is a row.
#   2. VOC ENTRIES  every voc:entry chunk quotes a shipped S, PA, PH, Q, F, R or X record verbatim; the program compares it with the
#                record in the running SDSYS VOC.
#   3. DICTIONARY ITEMS  every dict:item chunk quotes a shipped item; the program opens the installed dictionary and compares.
#   4. PRINTED SYNTAX  create.account and modify.account, typed with no arguments, print their syntax; the sys:syntax:accounts chunk
#                quotes it.
# The expected records are written into a scratch DIRECTORY file (gzpack) with the bytes the pack quotes, so the program compares
# what SD holds with what the pack says, and prints OK or DIFF for each.  A RUN THAT COMPARED NOTHING FAILS: each group must have
# compared as many records as the pack has chunks of that kind, and every id the program was given must have an answer line.

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
PACK = os.environ.get("SDPACK_DIR") or os.path.join(SD64, "agent-pack", "pack")      # SDPACK_DIR: a mutated copy, for the selftest
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0


def say(s=""):
    print(s)
    sys.stdout.flush()


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-pack-examples: CANNOT RUN - " + msg)
    sys.exit(2)


CHUNK = re.compile(r"(?m)^### (\S+)\n> (.*)\n")


def load_pack():
    chunks = {}
    for root, _d, names in os.walk(PACK):
        for n in sorted(names):
            if not n.endswith(".md"):
                continue
            text = open(os.path.join(root, n), encoding="utf-8").read()
            heads = list(CHUNK.finditer(text))
            for i, m in enumerate(heads):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
                chunks[m.group(1)] = text[m.end():end].strip()
    return chunks


def fence_body(body):
    """The text inside the first fenced block of a chunk body, or None."""
    m = re.search(r"(?s)^(`{3,})\n(.*?)\n\1$", body, re.M)
    return m.group(2) if m else None


def all_fences(body):
    return [m.group(2) for m in re.finditer(r"(?s)^(`{3,})\n(.*?)\n\1$", body, re.M)]


def unclean(s):
    """The pack writes bytes 128 and up and control characters as \\xNN; this gives them back."""
    return re.sub(r"\\x([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), s)


PROGRAM = r"""program gzpackcheck
   * reads each record of the scratch directory file gzpack and compares it with what the running SD holds
   open 'gzpack' to ex else stop 'GZPACK no gzpack file'
   open 'voc' to voc else stop 'GZPACK no voc'
   select ex to 1
   nv = 0 ; nd = 0 ; nbad = 0
   loop
      readnext id from 1 else exit
      read exp from ex, id else continue
      kind = field(id, '^', 1)
      name = field(id, '^', 2, 99)
      begin case
         case kind = 'verb'
            read act from voc, name else crt 'MISSING ' : id ; continue
            nv += 1
            t = act<1>[1,1]
            if t = 'K' then d = act<4> ; g = act<5> else d = act<2> ; g = act<3>
            got = t : @fm : upcase(d) : @fm : g
            gosub compare
         case kind = 'voc'
            read act from voc, name else crt 'MISSING ' : id ; continue
            nv += 1
            got = act
            gosub compare
         case kind = 'dict'
            dname = field(name, '^', 1)
            item = field(name, '^', 2, 99)
            openpath @sdsys : @ds : dname to dd else crt 'MISSING ' : id : ' (no dictionary ' : dname : ')' ; continue
            read act from dd, item else crt 'MISSING ' : id ; continue
            nd += 1
            * an I-type is compiled when the dictionaries are written: field 15 is the compile stamp and the object code follows it.
            * They differ with every build, so the comparison is of fields 1 to 14, which is the item as a person wrote it.
            got = '' ; want = ''
            for k = 1 to 14
               got<k> = act<k>
               want<k> = exp<k>
            next k
            exp = want
            gosub compare
      end case
   repeat
   crt 'GZPACK DONE verbs-and-voc=' : nv : ' dict=' : nd : ' different=' : nbad
   stop
compare:
   * trailing empty fields are not part of a record
   e1 = exp ; g1 = got
   loop while e1[1] = @fm do e1 = e1[1, len(e1) - 1] repeat
   loop while g1[1] = @fm do g1 = g1[1, len(g1) - 1] repeat
   if e1 = g1 then
      crt 'OK ' : id
   end else
      crt 'DIFF ' : id
      crt '   pack: ' : change(e1, @fm, '|')
      crt '   SD:   ' : change(g1, @fm, '|')
      nbad += 1
   end
   return
end
"""


def sess(box, cmds, timeout=600):
    conf = os.path.join(box, "sd.conf")
    env = dict(os.environ, SD_CONFIG=conf)
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    env["SDTEST_ADMIN"] = "1"
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd")], input=body, cwd=os.path.join(box, "user_accounts"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=timeout)
    return ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-pack-examples.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-pack-examples: sandbox %s" % box)
    say("sandbox-pack-examples: pack    %s" % PACK)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-pack-examples: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    if not os.path.isdir(PACK):
        bail("there is no pack at %s" % PACK)
    chunks = load_pack()

    # what to compare
    expected = {}        # record id in gzpack -> raw text
    n_verb = n_voc = n_dict = 0
    for cid, body in chunks.items():
        if cid.startswith("tcl:"):
            m = re.search(r"- dispatch `([A-Z]+)`(?: (\S+))?:", body)
            kind = re.search(r"- VOC record `[^`]+`: (type V|a keyword that is also a verb)", body)
            if not m or not kind:
                continue
            typ = "V" if kind.group(1) == "type V" else "K"
            expected["verb^" + cid[4:]] = "%s\n%s\n%s" % (typ, m.group(1), m.group(2) or "")
            n_verb += 1
        elif cid.startswith("voc:entry:"):
            fences = all_fences(body)                       # one block when the layers agree, else newvoc's and then voc_template's
            if fences:
                expected["voc^" + cid[len("voc:entry:"):]] = unclean(fences[-1])      # SDSYS's VOC is built from voc_template
                n_voc += 1
        elif cid.startswith("dict:item:"):
            raw = fence_body(body)
            dname, item = cid[len("dict:item:"):].split(":", 1)
            if raw is not None:
                expected["dict^%s^%s" % (dname, item)] = unclean(raw)
                n_dict += 1
    say("sandbox-pack-examples: the pack gives %d verbs, %d shipped VOC records and %d shipped dictionary items to compare" % (n_verb, n_voc, n_dict))
    row("the pack has something to compare (>= 90 verbs, >= 20 VOC records, >= 40 dictionary items)", n_verb >= 90 and n_voc >= 20 and n_dict >= 40,
        "%d / %d / %d" % (n_verb, n_voc, n_dict))

    # the scratch directory file, written with the bytes the pack quotes
    sess(box, ["DELETE.FILE gzpack NO.QUERY", "CREATE.FILE gzpack DIRECTORY"], timeout=120)
    gz = os.path.join(sysd, "gzpack")
    if not os.path.isdir(gz):
        bail("CREATE.FILE gzpack DIRECTORY made no directory at %s" % gz)
    for rid, text in expected.items():
        with open(os.path.join(gz, rid), "wb") as f:
            f.write(text.encode("latin-1", "replace"))
    with open(os.path.join(sysd, "bp", "gzpackcheck"), "w") as f:
        f.write(PROGRAM)
    say("sandbox-pack-examples: wrote %d expected records to %s and the program bp/gzpackcheck" % (len(expected), gz))
    out = sess(box, ["BASIC bp gzpackcheck", "RUN bp gzpackcheck", "DELETE.FILE gzpack NO.QUERY"])
    lines = [l.strip() for l in out.splitlines()]
    if not any(l == "Compiled 1 program(s) with no errors" for l in lines):
        bail("the comparison program did not compile:\n" + "\n".join(lines[:12]))
    ok_ids = {l[3:] for l in lines if l.startswith("OK ")}
    if "--show" in sys.argv:          # what differed, field marks shown as |
        say("\n".join(l for l in out.splitlines() if l.startswith(("DIFF", "   pack:", "   SD:", "MISSING"))))
    diff = [l[5:] for l in lines if l.startswith("DIFF ")]
    missing = [l[8:] for l in lines if l.startswith("MISSING ")]
    done = next((l for l in lines if l.startswith("GZPACK DONE")), None)
    say("sandbox-pack-examples: %s" % (done or "the program printed no GZPACK DONE line"))

    def group(prefix, label, want_n):
        ids = [i for i in expected if i.startswith(prefix)]
        got = [i for i in ids if i in ok_ids]
        bad = [i for i in ids if i in diff]
        gone = [i for i in ids if any(i in m for m in missing)]
        row("%s: the running SD holds what the pack says (%d of %d compared equal)" % (label, len(got), want_n),
            want_n > 0 and len(got) == want_n and not bad and not gone,
            "different: %s; missing: %s" % (bad[:4], gone[:4]))

    group("verb^", "VERBS (type, dispatch mode and target of every tcl: verb chunk, in SDSYS's VOC)", n_verb)
    group("voc^", "VOC RECORDS (every voc:entry chunk against the record in SDSYS's VOC)", n_voc)
    group("dict^", "DICTIONARY ITEMS (every dict:item chunk against the installed dictionaries)", n_dict)

    # the syntax the two account verbs print
    syn = chunks.get("sys:syntax:accounts")
    fences = all_fences(syn) if syn else []
    if len(fences) != 2:
        row("sys:syntax:accounts quotes the two printed syntaxes", False, "found %d fenced blocks" % len(fences))
    else:
        for verb, quoted in (("create.account", fences[0]), ("modify.account", fences[1])):
            printed = [l.rstrip() for l in sess(box, [verb], timeout=120).splitlines() if l.strip() and not l.startswith(":")]
            want = [l.rstrip() for l in unclean(quoted).splitlines() if l.strip()]
            row("%s typed alone prints the %d lines the pack quotes" % (verb, len(want)), printed[:len(want)] == want and len(want) > 0,
                "printed %r, pack %r" % (printed[:3], want[:3]))

    shutil.rmtree(gz, ignore_errors=True)
    for p in (os.path.join(sysd, "bp", "gzpackcheck"), os.path.join(sysd, "bp.out", "gzpackcheck")):
        if os.path.exists(p):
            os.remove(p)
    say("\nsandbox-pack-examples: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 and passed > 0 else 1)


if __name__ == "__main__":
    main()
