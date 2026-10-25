#!/usr/bin/env python3
#
# sandbox-shmmode.py - W.11 F1 (security-model evaluation, 24 Oct 2026): a running SD makes its shared memory segment and its semaphores 0660 and gives
# them to the group sdusers.  No install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-shmmode.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row
# passed, 1 a row failed, 2 it could not run (including: the sandbox's segment is not there, the null case).  The group rows need the group sdusers.
#
# START-HISTORY:
# 24 Oct 26 dm  New.  sysseg.c create_shared_segment(), sdsem.c get_semaphores().
# END-HISTORY
#
# THE EVIDENCE is /proc/sysvipc/shm and /proc/sysvipc/sem: the numeric mode and group of the sandbox's own keys (0x53434C91 / 0x53434C92 plus 0x20 for
# each keyset), read while the sandbox runs.  NOT SAID HERE: that a user who is not in the group cannot attach (this suite has no second user and no
# sudo); the mode and group are what the kernel decides that on.  The daemon sdlnxd runs only on an install, so its change is test-shmmode-units.py's.

import grp
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-shmmode: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def ipc(kind, key):
    """the row of /proc/sysvipc/<kind> for this key: {'perms': octal int, 'gid': n, 'cgid': n, 'uid': n}"""
    with open("/proc/sysvipc/" + kind) as fh:
        lines = fh.read().split("\n")
    head = lines[0].split()
    for ln in lines[1:]:
        f = ln.split()
        if f and int(f[head.index("key")]) == key:
            return {"perms": int(f[head.index("perms")], 8), "gid": int(f[head.index("gid")]), "cgid": int(f[head.index("cgid")]),
                    "uid": int(f[head.index("uid")])}
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-shmmode.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    keyset = int(os.environ.get("SDBOX_KEYSET", "0"))
    shm_key = 0x53434C91 + 0x20 * keyset
    sem_key = 0x53434C92 + 0x20 * keyset
    say("sandbox-shmmode: sandbox %s, keyset %d, keys 0x%X / 0x%X" % (box, keyset, shm_key, sem_key))
    try:
        sdusers = grp.getgrnam("sdusers").gr_gid
    except KeyError:
        sdusers = None
        say("  note: there is no group sdusers on this machine, so the group rows are skipped")
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-shmmode: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    shm = ipc("shm", shm_key)
    sem = ipc("sem", sem_key)
    if shm is None or sem is None:
        bail("the sandbox's segment or semaphores (keys 0x%X / 0x%X) are not there: %s" % (shm_key, sem_key, (shm, sem)))
    say("  segment %s, semaphores %s" % ({k: (oct(v) if k == "perms" else v) for k, v in shm.items()},
                                         {k: (oct(v) if k == "perms" else v) for k, v in sem.items()}))

    say("\n--- the segment ------------------------------------------------------------------------------------------")
    row("the segment is mode 0660 (it was 0666)", shm["perms"] & 0o777 == 0o660, oct(shm["perms"]))
    row("no access for others: the other bits are 0", shm["perms"] & 0o007 == 0, oct(shm["perms"]))
    if sdusers is not None:
        row("its group is sdusers", shm["gid"] == sdusers, "gid %d, sdusers is %d" % (shm["gid"], sdusers))
    say("\n--- the semaphores ---------------------------------------------------------------------------------------")
    row("the semaphores are mode 0660 (they were 0666)", sem["perms"] & 0o777 == 0o660, oct(sem["perms"]))
    row("no access for others: the other bits are 0", sem["perms"] & 0o007 == 0, oct(sem["perms"]))
    if sdusers is not None:
        row("their group is sdusers", sem["gid"] == sdusers, "gid %d, sdusers is %d" % (sem["gid"], sdusers))

    say("\n--- a session of the same user still works ---------------------------------------------------------------")
    out = sess(box, "WHO")
    row("CONTROL: a new session attaches the segment and runs WHO", re.search(r"\bWHO\b", out) is not None and "Error" not in out and len(out.strip()) > 10,
        out[-300:])
    after = ipc("shm", shm_key)
    row("and the session left the mode and group as they were", after is not None and after["perms"] == shm["perms"] and after["gid"] == shm["gid"], str(after))

    say("")
    say("sandbox-shmmode: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
