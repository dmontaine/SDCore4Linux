"""solo_swap.py - run SD Core for Linux Solo's programs inside a FULL-product sandbox (LSOLO 43).

Solo has no sandbox tool of its own: sandbox-fromtree.py patches the full product's IPC keys, installer and cproc, and a
scratch Solo would share the installed Solo's shared-memory key (LSOLO 40, memory two-solo-trees-share-one-key).  What can
be measured honestly is a SOLO PROGRAM running on the FULL kernel: for everything these witnesses read (the case of names,
the NOCASE flag of a new file, a rebuild by path) the C is the same code in both products, so the full sandbox's kernel is
the kernel under test and Solo's own BASIC is what is swapped in.  Each witness that takes --solo calls swap() right after
it starts the sandbox, and says so.

swap() copies the named records of Solo's sdsys over the sandbox's, compiles them with the sandbox's own compiler, and
refuses (the caller bails with exit 2, "could not run") unless the compiler printed "Compiled N program(s) with no
errors" with N the number swapped.
"""

import os
import re
import shutil
import subprocess

SOLO_SDSYS = "/home/don/Projects/SDCore4LinuxSolo/sdb_ai/sd64/sdsys"
SOLO_GPLBLD = "/home/don/Projects/SDCore4LinuxSolo/sdb_ai/sd64/gplbld"


def swap(box, programs=(), messages=(), dictdir=False):
    """Returns (ok, text).  programs are gpl.bp record names, messages are message numbers; dictdir also replaces the
    sandbox's gplbld/FILES_DICTS with Solo's (the shipped dictionaries the bootstrap's pass 3 reads)."""
    sysd = os.path.join(box, "sys")
    for name in programs:
        src = os.path.join(SOLO_SDSYS, "gpl.bp", name)
        if not os.path.isfile(src):
            return False, "Solo has no gpl.bp/%s" % name
        shutil.copyfile(src, os.path.join(sysd, "gpl.bp", name))
    for n in messages:
        src = os.path.join(SOLO_SDSYS, "messages", str(n))
        if not os.path.isfile(src):
            return False, "Solo has no message %s" % n
        shutil.copyfile(src, os.path.join(sysd, "messages", str(n)))
    if dictdir:
        dst = os.path.join(sysd, "gplbld", "FILES_DICTS")
        if not os.path.isdir(dst):
            return False, "the sandbox has no gplbld/FILES_DICTS"
        shutil.rmtree(dst)
        shutil.copytree(os.path.join(SOLO_GPLBLD, "FILES_DICTS"), dst)
    if programs:
        r = subprocess.run([os.path.join(sysd, "bin", "sd"), "-internal", "BASIC", "gpl.bp"] + list(programs), cwd=sysd,
                           env=dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf")), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace", timeout=600)
        want = r"(?m)^Compiled %d program\(s\) with no errors" % len(programs)
        if re.search(want, r.stdout) is None:
            return False, "Solo's programs did not compile in the sandbox:\n" + r.stdout[-800:]
    return True, "swapped %d program(s), %d message(s)%s" % (len(programs), len(messages), ", FILES_DICTS" if dictdir else "")
