#!/usr/bin/env python3
"""test-witness-sdnet-units.py - are the SDNet witness scripts INSTRUMENTS?  (19 Oct 26, the S.65 finish.)

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-witness-sdnet-units.py            (the free check, about 25 s: static rows, the helpers' mutants, the write-group and groups scripts against their models)
  python3 .../test-witness-sdnet-units.py --selftest      (the same, and the write-group and groups models broken one way at a time: about 100 s)
  python3 .../test-witness-sdnet-units.py --full          (also files-route, gaps and the two-machines roles against their models, each broken one way at a time: about 12 minutes)
  python3 .../test-witness-sdnet-units.py --only=files-route [--selftest]     (one model: writegroup, groups, files-route, gaps or two-machines; --only may be given more than once)

No sudo, no install, no sd, no network.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  REFUSES to run as root: the scripts it exercises do real work when they are
root (the re-exec, the groups), and this check must never be the way a witness script runs on a real machine.

WHAT IS CHECKED, and what is NOT.
  The six witness-sdnet-*.sh scripts and the probe are run by the owner with sudo on a real install; they have never been run on one.  A witness that cannot fail, or that fails for the
  wrong reason, wastes the one session the owner gives it.  So:
  S  static: no BOM, no CR, bash -n, the header says "NEEDS sudo" and gives an absolute command, --selftest passes, a run without sudo says CANNOT RUN and exits 2 before it changes anything,
     every message number a wl_msg call names exists in this tree with enough text for its arguments, every grep the premises make on the installed tree finds its string in THIS tree
     (so a renamed message or program fails here, not on the VM), the probe's python compiles and refuses a missing password file and a missing library;
  L  the helpers (witness-sdnet-lib.sh) with one fault at a time: each must make --selftest fail (an empty text that passes, a substring group match, an order test the wrong way round, a
     mask that masks nothing, a message that is not filled in ...);
  M  the MODEL: the scripts are run with PATH stubs for sudo, id, getent, gpasswd, groupdel, userdel, ss and openssl and a fake `sd` (this file with --fake-sd) that answers the verbs
     they send with the texts the REAL message files give, in the order the real programs print them, and edits a fake group file.  The correct model must give 0 failed rows and no shell
     error; each deliberate fault in the model (the orphan is ignored, the groups change in the wrong order, a write is allowed without the group, TLS 1.2 is accepted, an installer that
     gives the write right away ...) must make exactly the rows built to catch it fail.  THE MODEL IS MY READING OF THE REAL SYSTEM, so a pass says the script and the model agree and the
     script can fail; it does not say the real system does what the model does.  That is the witness's own job, on a machine.

Written 19 Oct 2026.  THE MODEL IS NOT THE SYSTEM: the outputs it prints are copied from the 18 Oct VM logs where there are some and from the message files where there are not.
"""
import fcntl
import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TESTPY = os.path.abspath(__file__)
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS_TREE = os.path.join(SD64, "sdsys")
MSG_DIR = os.path.join(SDSYS_TREE, "messages")

LIB = "witness-sdnet-lib.sh"
SCRIPTS = ["witness-sdnet-writegroup.sh", "witness-sdnet-files-route.sh", "witness-sdnet-gaps.sh", "witness-sdnet-groups.sh", "witness-sdnet-two-machines.sh"]
PROBE = "witness-sdnet-probe.py"
SERVER_HASH = hashlib.sha256(b"the model server's public key").hexdigest()
OTHER_HASH = hashlib.sha256(b"another machine's public key").hexdigest()


# ======================================================================================================================================== THE MODEL
# Everything from here to the line "THE CHECKS" is what the fake commands run.  It is deliberately small and is written from the message files, the 18 Oct VM logs and the sources.

def mutant():
    return os.environ.get("MODEL_MUTANT", "")


def W():
    return os.environ["FAKE_WORLD"]


def msg(n, *a):
    with open(os.path.join(MSG_DIR, str(n)), encoding="utf-8") as f:
        t = f.readline().rstrip("\n")
    for i, x in enumerate(a, 1):
        t = t.replace("%%%d" % i, str(x))
    return t


class Locked:
    """An exclusive lock on the model's state for the time of one verb (the two-session lock test runs two processes at once)."""
    def __enter__(self):
        self.f = open(os.path.join(W(), "state.lock"), "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def st_load():
    with open(os.path.join(W(), "state.json")) as f:
        return json.load(f)


def st_save(st):
    tmp = os.path.join(W(), "state.json.tmp")
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, os.path.join(W(), "state.json"))


def groups_read():
    g = {}
    with open(os.path.join(W(), "groups")) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            n, _x, gid, mem = (line.split(":") + ["", "", "", ""])[:4]
            g[n] = [gid, [m for m in mem.split(",") if m]]
    return g


def groups_write(g):
    with open(os.path.join(W(), "groups"), "w") as f:
        for n, (gid, mem) in g.items():
            f.write("%s:x:%s:%s\n" % (n, gid, ",".join(mem)))


def users_read():
    with open(os.path.join(W(), "users")) as f:
        return [l.strip() for l in f if l.strip()]


def users_write(u):
    with open(os.path.join(W(), "users"), "w") as f:
        f.write("\n".join(u) + "\n")


def in_group(g, user, grp):
    return user in g.get(grp, ["", []])[1]


def grp_add(g, user, grp):
    if grp in g and user not in g[grp][1]:
        g[grp][1].append(user)


def grp_del(g, user, grp):
    if grp in g and user in g[grp][1]:
        g[grp][1].remove(user)


def audit(user, words):
    with open(os.path.join(W(), "sdsys", "audit"), "a") as f:
        f.write("%s user=%s uid=998 pid=%d %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), user, os.getpid(), words))


def reg_path(acc):
    return os.path.join(W(), "sdsys", "accounts", acc)


def reg_write(acc, path, user, gates):
    os.makedirs(os.path.join(W(), "sdsys", "accounts"), exist_ok=True)
    with open(reg_path(acc), "w") as f:
        f.write("%s\nx\nsdu_%s\n%s\n" % (path, user, " ".join(gates)))


def reg_gates(acc):
    try:
        with open(reg_path(acc)) as f:
            return f.read().split("\n")[3].split()
    except (OSError, IndexError):
        return []


def helper_line(cmd):
    return "sd-elevate: " + cmd


# ---- MODIFY.ACCOUNT's files words: the semantics of modifya after K4a (gplbld/sandbox-filesgrp.py runs the real program on a scratch group file)
def modify_files(st, g, acc, word, out):
    user = acc
    has_f = in_group(g, user, "sdfiles")
    has_w = in_group(g, user, "sdfileswrite")
    m = mutant()
    if word == "FILES-ON":
        if has_f and m != "on-ignores-orphan-never":
            if has_w and m == "on-removes-write-when-both":
                grp_del(g, user, "sdfileswrite")
                out.append(helper_line("gpasswd -d %s sdfileswrite" % user))
                out.append(msg(11522, acc, "no"))
                return
            out.append(msg(10080, acc))
            return
        if has_w and m != "on-keeps-orphan-write":
            grp_del(g, user, "sdfileswrite")
            out.append(helper_line("gpasswd -d %s sdfileswrite" % user))
            if m == "no-message-order":
                pass
            else:
                out.append(msg(11522, acc, "no"))
        if m == "no-message-order" and has_w:
            grp_add(g, user, "sdfiles")
            out.append(helper_line("usermod -aG sdfiles -- %s" % user))
            out.append(msg(11482, acc, "yes"))
            out.append(msg(11522, acc, "no"))
            return
        if m == "on-add-first" and has_w:
            pass
        grp_add(g, user, "sdfiles")
        out.append(helper_line("usermod -aG sdfiles -- %s" % user))
        out.append(msg(11482, acc, "yes"))
    elif word == "FILES-OFF":
        nothing = (not has_f and not has_w) or (m == "off-ignores-orphan" and not has_f)
        if nothing:
            out.append(msg(10080, acc))
            return
        if m == "off-sdfiles-first":
            if has_f:
                grp_del(g, user, "sdfiles")
                out.append(helper_line("gpasswd -d %s sdfiles" % user))
                out.append(msg(11482, acc, "no"))
            if has_w:
                grp_del(g, user, "sdfileswrite")
                out.append(helper_line("gpasswd -d %s sdfileswrite" % user))
                out.append(msg(11522, acc, "no"))
            return
        if has_w and m != "off-keeps-write":
            grp_del(g, user, "sdfileswrite")
            out.append(helper_line("gpasswd -d %s sdfileswrite" % user))
            out.append(msg(11522, acc, "no"))
        if has_f:
            grp_del(g, user, "sdfiles")
            out.append(helper_line("gpasswd -d %s sdfiles" % user))
            out.append(msg(11482, acc, "no"))
        elif has_w:
            out.append(msg(11482, acc, "no"))
    elif word == "FILES-WRITE-ON":
        if not has_f and m != "write-on-without-files":
            out.append(msg(11523, acc))
            return
        if has_w:
            out.append(msg(10080, acc))
            return
        grp_add(g, user, "sdfileswrite")
        out.append(helper_line("usermod -aG sdfileswrite -- %s" % user))
        out.append(msg(11522, acc, "yes"))
    elif word == "FILES-WRITE-OFF":
        if not has_w:
            out.append(msg(10080, acc))
            return
        grp_del(g, user, "sdfileswrite")
        out.append(helper_line("gpasswd -d %s sdfileswrite" % user))
        out.append(msg(11522, acc, "no"))
        if m == "write-off-removes-files":
            grp_del(g, user, "sdfiles")
            out.append(helper_line("gpasswd -d %s sdfiles" % user))
            out.append(msg(11482, acc, "no"))


# ---- the remote side of the files-only route (apisrvr + !apifilesok), as the 18 Oct VM logs showed it
CHANGE_REQS = (7, 8, 9, 10, 16, 17, 18, 19, 30, 31, 32, 33)


def remote_login(st, g, ru, pw, route_audit=True):
    """The server's side of a files-only login by user ru.  Returns (status, write) with status 'ok', 'noaccount', 'badpw', 'norole'."""
    acc = st["accounts"].get(ru)
    if acc is None or ru not in users_read():
        audit("sdsys", "api refused user=%s reason=credential" % ru)
        return "badpw", False
    if acc.get("password") != pw:
        audit("sdsys", "api refused user=%s reason=credential" % ru)
        return "badpw", False
    if not (in_group(g, ru, "sdapi") or in_group(g, ru, "sdfiles")):
        reason = "not a member of sdapi or sdfiles"
        if mutant() == "k3-old-reason":
            reason = "not a member of sdapi"
        audit("sdsys", "api refused user=%s reason=%s" % (ru, reason))
        return "norole", False
    write = in_group(g, ru, "sdfiles") and in_group(g, ru, "sdfileswrite") and mutant() != "write-never"
    if mutant() == "write-without-group" and in_group(g, ru, "sdfiles"):
        write = True
    audit("sdsys", "api login route=sdfiles write=%s user=%s" % ("on" if write else "off", ru))
    return "ok", write


def refuse_audit(n, write, ru):
    audit("sdsys", "api refused request=%d route=sdfiles write=%s user=%s" % (n, "on" if write else "off", ru))


def files_of(st, acc):
    return st["files"].setdefault(acc, {})


def vfile(st, acc, name):
    return files_of(st, acc).setdefault(name, {"data": {}, "dict": {}})


# ======================================================================================================================================== THE FAKE sd
def fake_sd(argv):
    if "--version" in argv:
        print("SD Core for Linux (model for test-witness-sdnet-units.py)")
        return 0
    user = os.environ.get("FAKE_SUDO_USER") or getpass.getuser()
    lines = sys.stdin.read().split("\n")
    out = []
    audit(user, "login account=%s" % user)
    i = 0
    try:
        while i < len(lines):
            raw = lines[i]
            i += 1
            cmd = raw.strip()
            if not cmd or cmd.upper().startswith("TERM "):
                continue
            if cmd.upper() == "OFF":
                break
            out.append(":" + cmd)
            with Locked():
                i = dispatch(user, cmd, lines, i, out)
    except Exception as e:  # a bug in the model must be seen, not turned into a pass
        out.append("MODEL ERROR: %s: %s" % (type(e).__name__, e))
    sys.stdout.write("\n".join(out) + "\n")
    return 0


def take(lines, i, n=1):
    got = []
    for _ in range(n):
        if i < len(lines):
            got.append(lines[i])
            i += 1
        else:
            got.append("")
    return got, i


def dispatch(user, cmd, lines, i, out):
    st = st_load()
    g = groups_read()
    parts = cmd.split()
    verb = parts[0].upper()
    admin = (user == "sdsys")
    if verb == "LIST.SERVERS":
        if not st["servers"]:
            out.append(msg(11433))
        for n, d in sorted(st["servers"].items()):
            out.append("%s  %s:%s  %s/%s  %s...  %s" % (n, d["host"], d["port"], d["account"], d["mode"], d["pin"][:16], ",".join(d["accounts"])))
    elif verb == "CREATE.ACCOUNT":
        name = parts[2].lower()
        words = [w.upper() for w in parts[3:]]
        (_pw1, _pw2), i = take(lines, i, 2)
        if name in st["accounts"] or name in users_read():
            out.append("model: the account or user %s exists" % name)
            return i
        us = users_read()
        us.append(name)
        users_write(us)
        g["sdu_" + name] = ["2%03d" % len(g), [name]]
        grp_add(g, name, "sdusers")
        if "FILES-ON" in words:
            grp_add(g, name, "sdfiles")
            if mutant() == "create-gives-api":
                grp_add(g, name, "sdapi")
        st["accounts"][name] = {"password": "", "os_password": _pw1}
        reg_write(name, os.path.join(W(), "home", "user_accounts", name), name, [re.sub(r"-on$", "", w.lower()) for w in words if w != "FILES-ON"])
        os.makedirs(os.path.join(W(), "home", "user_accounts", name), exist_ok=True)
        out.append("Account %s created" % name)
        audit(user, "create.account account=%s" % name)
    elif verb == "MODIFY.PASSWORD":
        name = parts[1].lower()
        (p1, p2), i = take(lines, i, 2)
        if name not in st["accounts"]:
            out.append("Account %s not in register" % name)
        elif p1 != p2:
            out.append("Passwords do not match.")
            out.append("Password not changed.")
        else:
            st["accounts"][name]["password"] = p1
            out.append("Password accepted.")
    elif verb == "MODIFY.ACCOUNT":
        acc = parts[1].lower()
        word = parts[2].upper() if len(parts) > 2 else ""
        if len(parts) > 3:
            out.append(msg(11714, parts[3]))
        elif word.startswith("FILES-"):
            modify_files(st, g, acc, word, out)
            audit(user, "modify.account %s account=%s" % (word.lower(), acc))
        else:
            gates = reg_gates(acc)
            gname = re.sub(r"-(on|off)$", "", word.lower())
            if word.endswith("-OFF"):
                gates = [x for x in gates if x != gname]
            elif gname not in gates:
                gates.append(gname)
            try:
                with open(reg_path(acc)) as f:
                    rl = f.read().split("\n")
                rl[3] = " ".join(gates)
                with open(reg_path(acc), "w") as f:
                    f.write("\n".join(rl))
            except OSError:
                out.append("model: no register record for %s" % acc)
            out.append("Account %s has %s yes" % (acc, gname))
    elif verb == "SET.SERVER":
        name, host, port, acct, pin = parts[1].lower(), parts[2], parts[3], parts[4], parts[5]
        rest = [p.upper() for p in parts[6:]]
        mode = "write" if "WRITE" in rest else "read"
        accounts = []
        if "ACCOUNTS" in rest:
            accounts = parts[6 + rest.index("ACCOUNTS") + 1].split(",")
        no_query = "NO.QUERY" in rest
        replaced = name in st["servers"]
        if pin.lower() == "connect":
            out.append(msg(11440, host, port))
            out.append(SERVER_HASH)
            out.append(msg(11441))
            ans, i = take(lines, i)
            if ans[0].strip().lower().startswith("y"):
                if replaced and not no_query:
                    pass
                st["servers"][name] = {"host": host, "port": port, "account": acct, "pin": SERVER_HASH, "mode": mode, "accounts": accounts}
                out.append(msg(11442) + msg(11425 if replaced else 11424, name, host, port))
            else:
                out.append(msg(11442) + msg(11443, name))
        else:
            if mutant() == "connect-writes":
                pass
            st["servers"][name] = {"host": host, "port": port, "account": acct, "pin": pin.lower(), "mode": mode, "accounts": accounts}
            out.append(msg(11425 if replaced else 11424, name, host, port))
    elif verb == "DELETE.SERVER":
        name = parts[1].lower()
        if name in st["servers"]:
            del st["servers"][name]
            out.append(msg(11431, name))
        else:
            out.append(msg(11430, name))
    elif verb == "SET.NETLOGIN":
        name = parts[1].lower()
        (ru, pw), i = take(lines, i, 2)
        d = st["servers"].get(name)
        out.append(msg(11464, name, d["host"] if d else "?", d["port"] if d else "?"))
        if "net" not in reg_gates(user):
            out.append(msg(11460, user))
        elif d is None:
            out.append(msg(11430, name))
        elif user not in d["accounts"]:
            out.append(msg(11461, user, name))
        elif d["pin"] != SERVER_HASH and mutant() != "wrong-pin-sends":
            out.append(msg(11471, d["host"], d["port"], name))
        else:
            acc = st["accounts"].get(ru)
            if acc is None or acc.get("password") != pw:
                out.append(msg(11474, ""))
            else:
                st["netlogins"]["%s|%s" % (user, name)] = {"ru": ru, "pw": pw, "pin": SERVER_HASH}
                out.append(msg(11477, name, ru))
    elif verb == "DELETE.NETLOGIN":
        name = parts[1].lower()
        if st["netlogins"].pop("%s|%s" % (user, name), None) is not None:
            out.append(msg(11478, name))
        else:
            out.append(msg(11453, name))
    elif verb == "DELETE.ACCOUNT":
        name = parts[1].lower()
        ans, i = take(lines, i)
        if name in st["accounts"] and ans[0].strip().lower().startswith("y"):
            del st["accounts"][name]
            if os.path.exists(reg_path(name)):
                os.remove(reg_path(name))
            us = users_read()
            if name in us:
                us.remove(name)
                users_write(us)
            for grp in list(g):
                grp_del(g, name, grp)
            g.pop("sdu_" + name, None)
            st["files"].pop(name, None)
            out.append("Account %s deleted" % name)
    elif verb == "BACKUP.ACCOUNT":
        name = parts[1].lower()
        d = parts[3]
        os.makedirs(d, exist_ok=True)
        z = os.path.join(d, "%s-%s.zip" % (name, time.strftime("%Y%m%dT%H%M%S")))
        rf = 1 if in_group(g, name, "sdfiles") else 0
        rw = 1 if in_group(g, name, "sdfiles") and in_group(g, name, "sdfileswrite") else 0
        if mutant() == "manifest-no-write-key":
            man = "[account %s]\nroute.files: %d\n" % (name, rf)
        else:
            man = "[account %s]\nroute.files: %d\nroute.files.write: %d\n" % (name, rf, rw)
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("manifest.txt", man)
            zf.writestr("data.json", json.dumps(st["files"].get(name, {})))
        out.append("Backed up 1 account(s) to %s" % z)
    elif verb == "RESTORE.ACCOUNT":
        z, name = parts[1], parts[2].lower()
        (pw1, _pw2), i = take(lines, i, 2)
        with zipfile.ZipFile(z) as zf:
            man = zf.read("manifest.txt").decode()
            data = json.loads(zf.read("data.json").decode())
        rf = re.search(r"route\.files: (\d)", man)
        rw = re.search(r"route\.files\.write: (\d)", man)
        us = users_read()
        if name not in us:
            us.append(name)
            users_write(us)
            g["sdu_" + name] = ["2%03d" % len(g), [name]]
            grp_add(g, name, "sdusers")
            if rf and rf.group(1) == "1":
                grp_add(g, name, "sdfiles")
                if rw and rw.group(1) == "1" and mutant() != "restore-drops-write":
                    grp_add(g, name, "sdfileswrite")
            if mutant() == "restore-gives-write" and rf and rf.group(1) == "1":
                grp_add(g, name, "sdfileswrite")
            out.append("  %s will be CREATED." % name)
        st["accounts"][name] = {"password": pw1, "os_password": pw1}
        st["files"][name] = data
        reg_write(name, os.path.join(W(), "home", "user_accounts", name), name, [])
        out.append("Restored 1 account(s) from %s" % z)
    elif verb == "CONFIG":
        out.append("NETWAIT   5 seconds")
        out.append("NETREPLY  30 seconds")
    elif verb == "LIST.READU":
        out.append("User  Pid  File Id")
        for key, lk in sorted(st.get("locks", {}).items()):
            if lk["until"] > time.time():
                out.append("%4d %5d  %s" % (lk["user"], 4242, key.replace("|", "  ")))
    elif verb in ("CREATE.FILE", "CLEAR.FILE", "COUNT", "LIST", "SORT", "CT", "ED", "BASIC", "RUN", "SHELL"):
        i = data_verbs(st, g, user, verb, parts, lines, i, out)
    else:
        out.append("%s is not in your VOC" % parts[0])
    st_save(st)
    groups_write(g)
    return i


def data_verbs(st, g, user, verb, parts, lines, i, out):
    cdir = os.path.join(W(), "home", "user_accounts", user)
    if verb == "CREATE.FILE":
        vfile(st, user, parts[1].lower())
        out.append("Created DATA part as %s" % parts[1])
    elif verb == "CLEAR.FILE":
        vfile(st, user, parts[1].lower())["data"] = {}
        out.append("File %s cleared" % parts[1])
    elif verb == "ED":
        dct = parts[1].upper() == "DICT"
        fname = (parts[2] if dct else parts[1]).lower()
        rid = parts[3] if dct else parts[2]
        body = []
        while i < len(lines):
            ln = lines[i]
            i += 1
            if ln.strip().upper() == "FI":
                break
            if ln.startswith("I "):
                body.append(ln[2:])
        vf = vfile(st, user, fname)
        (vf["dict"] if dct else vf["data"])[rid] = body
        out.append("Record %s filed" % rid)
    elif verb == "COUNT":
        data, how = resolve(st, g, user, parts[1].lower(), out)
        if data is not None:
            out.append("%d record(s) counted" % len(data))
    elif verb == "LIST":
        data, how = resolve(st, g, user, parts[1].lower(), out)
        if data is not None:
            out.append("%s." % parts[1])
            for rid in sorted(data):
                if len(parts) > 2 and parts[2].lower() == "name":
                    out.append("%-12s %s" % (rid, data[rid][0] if data[rid] else ""))
                else:
                    out.append(rid)
            out.append("")
            out.append("%d record(s) listed" % len(data))
    elif verb == "SORT":
        data, how = resolve(st, g, user, parts[1].lower(), out)
        if data is not None:
            out.append("%s." % parts[1])
            for rid in sorted(data, key=lambda r: (data[r][0] if data[r] else "")):
                out.append(rid)
            out.append("")
            out.append("%d record(s) listed" % len(data))
    elif verb == "CT":
        data, how = resolve(st, g, user, parts[1].lower(), out)
        if data is not None:
            rid = parts[2]
            out.append("%s %s" % (parts[1], rid))
            for k, ln in enumerate(data.get(rid, []), 1):
                out.append("%d: %s" % (k, ln))
    elif verb == "BASIC":
        for name in parts[2:]:
            p = os.path.join(cdir, "bp", name)
            out.append("Compiling bp %s" % name)
            out.append("0 error(s)" if os.path.exists(p) else "Program bp.OUT %s not found" % name)
            out.append("Compiled 1 program(s) with no errors")
    elif verb == "RUN":
        i = run_program(st, g, user, parts, out, i)
    return i


def resolve(st, g, user, name, out):
    """A file name as a person at a session means it: a pointer in the VOC to a remote file (the netfile route) or the user's own file."""
    ptr = st["vocs"].get(user, {}).get(name)
    if ptr is None:
        vf = files_of(st, user).get(name)
        if vf is None:
            out.append("Cannot open file %s" % name)
            return None, "local"
        return vf["data"], "local"
    conn = remote_open(st, g, user, ptr, out)
    if conn is None:
        return None, "remote"
    return conn["vf"]["data"], "remote"


def remote_open(st, g, user, ptr, out, quiet=False):
    """OPEN of an N pointer: the client's checks in the order the docs give, then the server's login.  Returns a connection dict or None (the reason is in out)."""
    server, fname = ptr
    d = st["servers"].get(server)
    if "net" not in reg_gates(user):
        out.append(msg(11460, user))
        return None
    if d is None:
        out.append(msg(11430, server))
        return None
    if user not in d["accounts"]:
        out.append(msg(11461, user, server))
        return None
    nl = st["netlogins"].get("%s|%s" % (user, server))
    if nl is None:
        out.append(msg(11496, server, "no stored login"))
        return None
    if nl["pin"] != d["pin"] and mutant() != "wrong-pin-sends":
        out.append("000000B0: " + msg(11455, server) + " at line 1 of /model/bp.out/prog")
        return None
    status, write = remote_login(st, g, nl["ru"], nl["pw"])
    if status != "ok":
        if status == "norole":
            out.append("000000C1: " + msg(10073, nl["ru"]) + " at line 1 of /model/bp.out/prog")
        else:
            out.append("000000C2: " + msg(11498, server, "credential") + " at line 1 of /model/bp.out/prog")
        return None
    return {"server": server, "ru": nl["ru"], "write": write, "mode": d["mode"], "vf": vfile(st, d["account"], fname), "cuser": user, "fname": fname}


STATUS_REFUSED = 7000


def netfile_change(st, conn, opname, req, ctx):
    """One change or lock through an open remote file.  Returns (branch, status, text) as the program would print them."""
    if conn["mode"] != "write":
        return "error", STATUS_REFUSED, msg(11501, conn["server"], opname)
    if not conn["write"]:
        refuse_audit(req, False, conn["ru"])
        txt = msg(11521, req)
        if mutant() == "k1-old-text":
            txt = "status 0"
        return "error", STATUS_REFUSED, msg(11500, conn["server"], opname, txt)
    word = {"write": "write", "writeu": "write", "delete": "delete", "deleteu": "delete", "clear.file": "clear"}.get(opname)
    if word:                     # the client's own audit line for a change it made (the 18 Oct VM run showed write, delete and clear)
        audit(conn["cuser"], "netfile %s server=%s file=%s" % (word, conn["server"], conn["fname"]))
    return "then", 0, ""


def run_program(st, g, user, parts, out, i):
    prog = parts[2].lower() if len(parts) > 2 else ""
    cdir = os.path.join(W(), "home", "user_accounts", user)
    if not os.path.exists(os.path.join(cdir, "bp", prog)):
        out.append("Program bp.OUT %s not found" % prog)
        return i
    voc = st["vocs"].setdefault(user, {})
    if prog == "zzwnmk":
        if "voc" not in reg_gates(user):
            out.append("VOC WRITE REFUSED zzrc st=3099")
            return i
        voc["zzrc"] = ["zzloop", "zzcust"]
        voc["zzrw"] = ["zzloop", "zzwgf"]
        for nm in ("zzrc", "zzrw"):
            out.append("pointer %s = [N / %s / %s]" % (nm, voc[nm][0], voc[nm][1]))
        out.append("zzwnmk done")
    elif prog == "zzwtmk":
        if "voc" not in reg_gates(user):
            out.append("VOC WRITE REFUSED st=3099")
            return i
        voc["zzrt"] = ["zzremote", "zzwfile"]
        out.append("pointer zzrt = [N / zzremote / zzwfile]")
        out.append("zzwtmk done")
    elif prog in ("zzwncl", "zzwtcl"):
        voc.pop("zzrc", None); voc.pop("zzrw", None); voc.pop("zzrt", None)
        out.append("%s done" % prog)
    elif prog == "zzwnrd":
        conn = remote_open(st, g, user, voc.get("zzrc", ["zzloop", "zzcust"]), out)
        if conn is not None:
            out.append("data open ok")
            c1 = conn["vf"]["data"].get("c1", [])
            out.append("c1=[%s]" % "/".join(c1))
            out.append("dict open ok")
    elif prog in ("zzwn1", "zzwn2", "zzwn3", "zzwn4", "zzwtrw", "zzwnla", "zzwnlb"):
        ptr = voc.get("zzrw") or voc.get("zzrt")
        conn = remote_open(st, g, user, ptr, out) if ptr else None
        if conn is None:
            return i
        vf = conn["vf"]["data"]
        if prog == "zzwn1":
            out.append("X0 opened zzrw")
            out.append("X1 READ p1 (control) branch=then STATUS()=0 record=[%s]" % "/".join(vf.get("p1", [])))
            for label, opname, req, apply in (("X2 WRITE n1", "write", 16, lambda: vf.__setitem__("n1", ["viaremote"])),
                                              ("X3 WRITEU n2", "writeu", 17, lambda: vf.__setitem__("n2", ["viaremoteu"])),
                                              ("X4 DELETE p2", "delete", 18, lambda: vf.pop("p2", None)),
                                              ("X5 READU p3", "lock", 30, lambda: None),
                                              ("X6 RECORDLOCKU p3", "lock", 30, lambda: None),
                                              ("X7 READVU p3", "lock", 30, lambda: None)):
                br, sts, _t = netfile_change(st, conn, opname, req, None)
                if br == "then":
                    apply()
                out.append("%s branch=%s STATUS()=%d" % (label, br, sts))
            out.append("X8 READV p3 (control, no lock) branch=then STATUS()=0 value=[%s]" % (vf.get("p3", [""])[0]))
            br, sts, _t = netfile_change(st, conn, "clear.file", 31, None)
            if br == "then":
                vf.clear()
            out.append("X9 CLEARFILE branch=%s STATUS()=%d" % (br, sts))
            out.append("XZ done")
        elif prog == "zzwn2":
            br, sts, txt = netfile_change(st, conn, "write", 16, None)
            if br == "then":
                vf["n3"] = ["viaremote"]
                out.append("W9 REACHED (the write was not refused)")
            else:
                out.append("000000D9: " + (txt or msg(11501, conn["server"], "write")) + " at line 2 of /model/bp.out/zzwn2")
        elif prog == "zzwn3":
            def step(label, opname, req, apply, show=""):
                br, sts, _t = netfile_change(st, conn, opname, req, None)
                if br == "then":
                    apply()
                out.append("%s branch=%s STATUS()=%d%s" % (label, br, sts, show if br == "then" else ""))
            step("Y1 WRITE n1", "write", 16, lambda: vf.__setitem__("n1", ["viaremote"]))
            step("Y2 WRITEU n2", "writeu", 17, lambda: vf.__setitem__("n2", ["viaremoteu"]))
            step("Y3 DELETE p2", "delete", 18, lambda: vf.pop("p2", None))
            step("Y4 READU p3", "lock", 30, lambda: None, " record=[%s]" % "/".join(vf.get("p3", [])))
            step("Y5 RECORDLOCKU p1", "lock", 30, lambda: None)
            step("Y6 READVU p1", "lock", 30, lambda: None, " value=[%s]" % (vf.get("p1", [""])[0]))
            out.append("YZ done")
        elif prog == "zzwn4":
            br, sts, _t = netfile_change(st, conn, "clear.file", 31, None)
            if br == "then":
                vf.clear()
            out.append("Y7 CLEARFILE branch=%s STATUS()=%d" % (br, sts))
        elif prog == "zzwtrw":
            out.append("T1 READ t1 branch=then STATUS()=0 record=[%s]" % "/".join(vf.get("t1", [])))
            br, sts, _t = netfile_change(st, conn, "write", 16, None)
            if br == "then":
                vf["t4"] = ["from the client"]
            out.append("T2 WRITE t4 branch=%s STATUS()=%d" % (br, sts))
            out.append("T3 READ t4 branch=%s STATUS()=0 record=[%s]" % ("then" if "t4" in vf else "else", "/".join(vf.get("t4", []))))
            out.append("TZ done")
        elif prog == "zzwnla":
            if not conn["write"]:
                out.append("READU ERROR st=7000")
                return i
            key = "%s|%s" % ("zzwgf", "lk1")
            st.setdefault("locks", {})[key] = {"user": 7, "until": time.time() + 9}
            out.append("A %s holds lk1 (remote)" % time.strftime("%H:%M:%S"))
            st_save(st)
            groups_write(g)
            rel = time.time() + 9
            # the verb holds the state lock while it sleeps in the real world? No: it must not. Release the model lock around the sleep.
            LOCK_HOLD.append(rel)
        elif prog == "zzwnlb":
            fid = parts[3].lower() if len(parts) > 3 else "lk1"
            key = "%s|%s" % ("zzwgf", fid)
            lk = st.get("locks", {}).get(key)
            held = lk is not None and lk["until"] > time.time()
            if held:
                out.append("B %s B1 READU %s LOCKED-clause branch=locked STATUS()=%d record=[]" % (time.strftime("%H:%M:%S"), fid, lk["user"]))
                out.append("B %s B3 RECORDLOCKU %s LOCKED-clause branch=locked STATUS()=%d" % (time.strftime("%H:%M:%S"), fid, lk["user"]))
                WAIT_FOR.append((key, time.time(), fid, "/".join(vf.get(fid, []))))
            else:
                out.append("B %s B1 READU %s LOCKED-clause branch=then STATUS()=0 record=[%s]" % (time.strftime("%H:%M:%S"), fid, "/".join(vf.get(fid, []))))
    else:
        out.append("model: no behaviour for program %s" % prog)
    return i


LOCK_HOLD = []
WAIT_FOR = []


def after_verb_sleeps(out):
    """The lock holder sleeps AFTER the verb (outside the state lock); the waiting session polls until the lock is gone."""
    for rel in LOCK_HOLD:
        time.sleep(max(0.0, rel - time.time()))
        with Locked():
            st = st_load()
            st.get("locks", {}).pop("zzwgf|lk1", None)
            st_save(st)
        out.append("A %s released lk1" % time.strftime("%H:%M:%S"))
    for key, t0, fid, rec in WAIT_FOR:
        while True:
            with Locked():
                lk = st_load().get("locks", {}).get(key)
            if lk is None or lk["until"] <= time.time():
                break
            time.sleep(0.25)
        waited = int(time.time() - t0)
        out.append("B %s B2 plain READU %s returned branch=then STATUS()=0 record=[%s] waited %d s" % (time.strftime("%H:%M:%S"), fid, rec, waited))


# ======================================================================================================================================== THE STUBS
def stub(name, argv):
    g = groups_read()
    us = users_read()
    real_user = getpass.getuser()
    if name == "id":
        if argv == ["-u"]:
            print(0)
            return 0
        if len(argv) == 2 and argv[0] == "-u":
            if argv[1] in us or argv[1] in ("sdsys", "root", real_user):
                print(990 if argv[1] == "sdsys" else 1000)
                return 0
            sys.stderr.write("id: '%s': no such user\n" % argv[1])
            return 1
        if len(argv) == 1 and not argv[0].startswith("-"):
            if argv[0] in us or argv[0] in ("sdsys", "root", real_user):
                print("uid=1000(%s) gid=1000(%s) groups=1000(%s)" % (argv[0], argv[0], argv[0]))
                return 0
            return 1
        if len(argv) == 2 and argv[0] == "-nG":
            print(" ".join(n for n, (_g, m) in g.items() if argv[1] in m))
            return 0
        os.execv(real_cmd("id"), ["id"] + argv)
    if name == "getent":
        if argv[:1] == ["group"] and len(argv) == 2:
            if argv[1] in g:
                gid, mem = g[argv[1]]
                print("%s:x:%s:%s" % (argv[1], gid, ",".join(mem)))
                return 0
            return 2
        os.execv(real_cmd("getent"), ["getent"] + argv)
    if name == "gpasswd":
        flag, user, grp = argv[0], argv[1], argv[2]
        if grp not in g:
            return 3
        (grp_add if flag == "-a" else grp_del)(g, user, grp)
        groups_write(g)
        return 0
    if name == "groupdel":
        g.pop(argv[0], None)
        groups_write(g)
        return 0
    if name == "userdel":
        user = [a for a in argv if not a.startswith("-")][0]
        if user in us:
            us.remove(user)
            users_write(us)
        for grp in list(g):
            grp_del(g, user, grp)
        g.pop("sdu_" + user, None)
        groups_write(g)
        return 0
    if name == "sudo":
        env = dict(os.environ)
        args = list(argv)
        while args and args[0].startswith("-"):
            if args[0] == "-u":
                env["FAKE_SUDO_USER"] = args[1]
                args = args[2:]
            else:
                args = args[1:]
        os.execvpe(args[0], args, env)
    if name == "ss":
        text = " ".join(argv)
        if "established" in text:
            if mutant() == "connection-left-open":
                print("ESTAB 0 0 127.0.0.1:4247 127.0.0.1:50000")
            return 0
        if mutant() == "loopback-only":
            line = "LISTEN 0 128 127.0.0.1:4247 0.0.0.0:*"
        else:
            line = "LISTEN 0 128 0.0.0.0:4247 0.0.0.0:*"
        if "-H" in text or "H" in [a.lstrip("-") for a in argv if a.startswith("-")] or any(a.startswith("-") and "H" in a for a in argv):
            print(line)
        else:
            print("State Recv-Q Send-Q Local Address:Port Peer Address:Port")
            print(line)
        return 0
    if name == "openssl":
        return fake_openssl(argv)
    sys.stderr.write("model: no stub for %s\n" % name)
    return 127


def real_cmd(name):
    path = [p for p in os.environ["PATH"].split(":") if p != os.path.join(W(), "bin")]
    return shutil.which(name, path=":".join(path)) or "/usr/bin/" + name


def fake_openssl(argv):
    sub = argv[0] if argv else ""
    if sub == "s_client":
        sys.stdin.read()
        if "-tls1_2" in argv:
            if mutant() == "tls12-accepted":
                print("New, TLSv1.2, Cipher is ECDHE-RSA-AES256-GCM-SHA384\n    Protocol  : TLSv1.2")
            else:
                print("tlsv1 alert protocol version\nCipher    : (NONE)")
            return 0
        print("New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384\n    Protocol  : TLSv1.3")
        return 0
    if sub == "x509":
        sys.stdin.read() if not sys.stdin.isatty() else None
        print("-----BEGIN PUBLIC KEY-----\nMODEL\n-----END PUBLIC KEY-----")
        return 0
    if sub == "pkey":
        sys.stdin.read()
        sys.stdout.write("DER")
        return 0
    if sub == "dgst":
        sys.stdin.read()
        print("SHA2-256(stdin)= " + SERVER_HASH)
        return 0
    return 0


def fake_elevate(argv):
    if argv == ["tls-key"]:
        print("sd-elevate: openssl x509 -noout -pubkey -in %s | openssl pkey -pubin -outform DER | openssl dgst -sha256" % os.environ.get("WL_TLS_PEM", "/etc/sd-tls/api.pem"))
        print("public key sha256: %s" % (OTHER_HASH if mutant() == "tlskey-differs" else SERVER_HASH))
        return 0
    return 2


def fake_probe(argv):
    """witness-sdnet-probe.py against the model: the same P lines, the same abort-event texts."""
    mode, host, port, user, pwfile, account, fname, rid = argv
    pw = open(pwfile).read().strip()
    print("P INPUTS mode=%s host=%s port=%s user=%s account=%s file=%s id=%s (password read from %s, not printed)" % (mode, host, port, user, account, fname, rid, pwfile))
    with Locked():
        st = st_load()
        g = groups_read()
        status, write = remote_login(st, g, user, pw)
        if status != "ok":
            print("P CONNECT FAILED session=0 status=0 error=[]")
            return 2
        print("P CONNECT ok session=1")
        vf = vfile(st, account, fname)["data"]
        print("P OPEN ok fno=1")
        def show(label, extra=""):
            print("P %-30s status=0 %s error=[]" % (label, extra))
        if mode == "files":
            show("6 SDRead (control)", "ret=%s" % (rid in vf))
            seq = [(7, "7 SDReadl", "Read", "wait=0"), (8, "8 SDReadl wait", "Read", "wait=1"), (9, "9 SDReadu", "Read", "wait=0"), (10, "10 SDReadu wait", "Read", "wait=1"),
                   (16, "16 SDWrite", "Write", ""), (17, "17 SDWriteu", "Write", ""), (18, "18 SDDelete", "DELETE", ""), (19, "19 SDDeleteu", "DELETE", ""), (30, "30 SDRecordlock", "RECORDLOCK", "")]
            for n, label, name, extra in seq:
                if not write:
                    refuse_audit(n, False, user)
                    print("%s generated an abort event%s" % (name, msg(11521, n)))
                elif n == 16:
                    vf[rid + "-w"] = ["written by the probe"]
                elif n == 17:
                    vf[rid + "-wu"] = ["written by the probe"]
                elif n in (18, 19):
                    vf.pop(rid, None)
                show(label, extra)
            show("15 SDRelease (control)")
        else:
            for n, label, name in ((20, "20 SDCall", "CALL"), (21, "21 SDExecute", "EXECUTE"), (22, "22 SDRespond", "EXECUTE"), (23, "23 SDEndCommand", "EndCommand"),
                                   (54, "54 SDTxn", "Txn"), (61, "61 SDOpenSeq", "OpenSeq"), (3, "3 SDLogto (the second 3)", "LOGTO")):
                if n == 54 and mutant() == "gaps-54-allowed":
                    show(label)
                    continue
                refuse_audit(n, write, user)
                print("%s generated an abort event%s" % (name, msg(11480, n)))
                show(label)
            show("6 SDRead (control, still allowed)", "ret=%s" % (rid in vf))
        st_save(st)
        groups_write(g)
    print("P DONE")
    return 0


# ======================================================================================================================================== THE CHECKS
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def read(path):
    with open(path, "rb") as f:
        return f.read()


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", **kw)


def strip_comments_sh(text):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in text.split("\n"))


# ---- S. static
def static_checks():
    files = [LIB] + SCRIPTS + [PROBE]
    for f in files:
        p = os.path.join(HERE, f)
        raw = read(p)
        check("S1 %s exists, no BOM, no CR" % f, b"\xef\xbb\xbf" not in raw[:3] and b"\r" not in raw, "BOM or CR found")
        if f.endswith(".sh"):
            r = sh(["bash", "-n", p])
            check("S2 %s passes bash -n" % f, r.returncode == 0, r.stderr[:300])
        else:
            r = sh([sys.executable, "-m", "py_compile", p])
            check("S2 %s compiles" % f, r.returncode == 0, r.stderr[:300])
    for f in SCRIPTS:
        text = read(os.path.join(HERE, f)).decode("utf-8")
        check("S3 %s says ***NEEDS sudo*** and names its command with an absolute path" % f,
              "***NEEDS sudo" in text and "/home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/%s" % f in text, "header")
        check("S3 %s sources the library and runs --selftest before anything else" % f,
              '--selftest' in text and 'wl_selftest' in text and 'wl_logged' in text and text.index("wl_selftest") < text.index("wl_logged"), "order")
        r = sh(["bash", os.path.join(HERE, f), "--selftest"], timeout=120)
        check("S4 %s --selftest exits 0 and says '1 passed, 0 failed'" % f, r.returncode == 0 and "== 1 passed, 0 failed ==" in r.stdout and re.search(r"(?m)^SELFTEST-WRONG:", r.stdout) is None, r.stdout[-300:])
        # a run without sudo refuses BEFORE anything else (the first thing the script does after the selftest branch is wl_logged)
        env = {k: v for k, v in os.environ.items() if not k.startswith("WL_") and not k.startswith("FAKE_")}
        r = sh(["bash", os.path.join(HERE, f)], env=env, timeout=60, input="")
        check("S5 %s run without sudo says CANNOT RUN and exits 2" % f, r.returncode == 2 and "CANNOT RUN" in r.stdout and "sudo" in r.stdout, "rc=%d %s" % (r.returncode, r.stdout[:200]))
    # the probe
    r = sh([sys.executable, os.path.join(HERE, PROBE)])
    check("S6 the probe with no arguments prints its usage and exits 2", r.returncode == 2 and "P USAGE" in r.stdout, r.stdout[:200])
    r = sh([sys.executable, os.path.join(HERE, PROBE), "files", "127.0.0.1", "4247", "u", "/nonexistent/pw", "u", "f", "i"])
    check("S6 the probe with a missing password file says CANNOT RUN and exits 2 (nothing sent)", r.returncode == 2 and "CANNOT RUN" in r.stdout, r.stdout[:200])
    d = tempfile.mkdtemp(prefix="wsu-probe-")
    try:
        with open(os.path.join(d, "pw"), "w") as f:
            f.write("x\n")
        r = sh([sys.executable, os.path.join(HERE, PROBE), "files", "127.0.0.1", "4247", "u", os.path.join(d, "pw"), "u", "f", "i"], env=dict(os.environ, WL_SDSYS=d))
        check("S6 the probe with no client library says CANNOT RUN and exits 2", r.returncode == 2 and "CANNOT RUN" in r.stdout, r.stdout[:200])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # S7: every message a script names exists in this tree and has the text for its arguments; no %n is left over
    for f in SCRIPTS:
        text = read(os.path.join(HERE, f)).decode("utf-8")
        for m in re.finditer(r'wl_msg (\d+)((?: (?:"[^"]*"|\'[^\']*\'|[^\s)"\']+))*)', strip_comments_sh(text)):
            n = m.group(1)
            args = shlex.split(m.group(2)) if m.group(2).strip() else []
            p = os.path.join(MSG_DIR, n)
            if not os.path.exists(p):
                check("S7 %s: message %s exists" % (f, n), False, "no such message file")
                continue
            first = open(p, encoding="utf-8").readline().rstrip("\n")
            need = max([int(x) for x in re.findall(r"%(\d)", first)] + [0])
            check("S7 %s: wl_msg %s is given the %d argument(s) its text has" % (f, n, need), len(args) >= need, "text %r, args %r" % (first[:80], args))
    # S8: the greps the premises make on the installed tree find their string in THIS tree
    for f in SCRIPTS:
        text = read(os.path.join(HERE, f)).decode("utf-8")
        for m in re.finditer(r"""grep -q '([^']+)' "\$WL_SDSYS/([^"]+)\"""", text):
            needle, rel = m.group(1), m.group(2)
            p = os.path.join(SDSYS_TREE, rel)
            ok = os.path.exists(p) and needle in open(p, encoding="utf-8", errors="replace").read()
            check("S8 %s: the premise grep for %r in %s finds it in this tree" % (f, needle, rel), ok, "not found in %s" % p)
    # S9: no script prints a password: every password variable is added to WL_SECRETS and none is echoed
    for f in SCRIPTS:
        text = strip_comments_sh(read(os.path.join(HERE, f)).decode("utf-8"))
        pw_vars = set(re.findall(r"\b(PW[A-Z]*)=\$\(wl_newpw\)", text))
        for v in sorted(pw_vars):
            check("S9 %s: %s is in WL_SECRETS" % (f, v), re.search(r"WL_SECRETS=\([^)]*\"\$%s\"" % v, text) is not None, "not masked")
            check("S9 %s: %s is never printed with say/echo/printf to the log" % (f, v),
                  re.search(r"\b(say|echo)\b[^\n]*\$\{?%s\b" % v, text) is None, "printed")
    # S10: one MODIFY.ACCOUNT word per command in every script
    for f in SCRIPTS:
        text = read(os.path.join(HERE, f)).decode("utf-8")
        bad = [l.strip() for l in text.split("\n") if re.search(r'"MODIFY\.ACCOUNT \$\{?\w+\}? [A-Z.-]+ [A-Z.-]+"', l)]
        check("S10 %s: no MODIFY.ACCOUNT command carries two actions (the Dev build before 18 Oct refuses them with 11714)" % f, not bad, bad[:2])


# ---- L. the helpers with one fault at a time
LIB_MUTANTS = [
    ("expect_has accepts an empty wording", 'if [ -z "$3" ]; then fail "$1 - the wording to look for is EMPTY (a message that could not be read? an empty wording is in every text)"; return; fi\n  if [ -z "$2" ]; then fail "$1 - the text to look in is EMPTY (the null case): wanted: $3"; return; fi', 'if [ -z "$2" ]; then fail "$1 - the text to look in is EMPTY (the null case): wanted: $3"; return; fi'),
    ("expect_lacks passes on an empty text", 'if [ -z "$2" ]; then fail "$1 - the text to look in is EMPTY (the null case), so its absence proves nothing: $3"; return; fi', ''),
    ("expect_re accepts an empty pattern", 'if [ -z "$3" ]; then fail "$1 - the pattern is EMPTY (it matches every line)"; return; fi', ''),
    ("wl_in_group matches a substring", "printf ',%s,' \"$(wl_members \"$2\")\" | grep -q -F \",$1,\"", "wl_members \"$2\" | grep -q -F \"$1\""),
    ("wl_before accepts the wrong order", '[ "$b" -gt "$a" ]', '[ "$b" -ne "$a" ]'),
    ("wl_mask masks nothing", 'txt=$(printf \'%s\' "$txt" | sed -e "s/$esc/********/g")', 'txt=$txt'),
    ("wl_msg does not fill in %2", ' -e "s/%2/$(wl_sed_esc "${3:-}")/g"', ''),
    ("wl_line_of matches a substring", 'if (s == ENVIRON["WL_LINE_T"])', 'if (index(s, ENVIRON["WL_LINE_T"]) > 0)'),
    ("wl_summary passes when no row ran", 'if [ "$WL_PASS" -eq 0 ]; then say "  (no row ran: that is not a pass)"; return 2; fi', ''),
    ("wl_summary passes a failure", 'if [ "$WL_FAIL" -gt 0 ]; then return 1; fi', ''),
    ("wl_state reads sdfileswrite from sdfiles", "wl_in_group \"$1\" sdfileswrite && b=1", "wl_in_group \"$1\" sdfiles && b=1"),
    ("expect_eq compares loosely", 'if [ "$2" = "$3" ]; then pass', 'if [ "${2:0:3}" = "${3:0:3}" ]; then pass'),
]


def lib_mutants():
    src = read(os.path.join(HERE, LIB)).decode("utf-8")
    base = tempfile.mkdtemp(prefix="wsu-lib-")
    try:
        for name, old, new in LIB_MUTANTS:
            if src.count(old) != 1:
                check("L %s: its text occurs once in the library" % name, False, "occurs %d times" % src.count(old))
                continue
            p = os.path.join(base, "lib.sh")
            with open(p, "w") as f:
                f.write(src.replace(old, new))
            r = sh(["bash", "-c", '. "$1"; wl_selftest', "x", p], timeout=120)
            check("L mutant: %s is caught by --selftest" % name, r.returncode != 0, "the selftest still passed:\n" + r.stdout[-200:])
        p = os.path.join(base, "lib.sh")
        with open(p, "w") as f:
            f.write(src)
        r = sh(["bash", "-c", '. "$1"; wl_selftest', "x", p], timeout=120)
        check("L control: the unmutated library passes its own selftest", r.returncode == 0, r.stdout[-200:])
    finally:
        shutil.rmtree(base, ignore_errors=True)


# ---- M. the model
class World:
    def __init__(self, mut=""):
        self.root = tempfile.mkdtemp(prefix="wsu-world-")
        self.mut = mut
        self.user = getpass.getuser()
        r = self.root
        for d in ("bin", "sdsys/accounts", "gplbld", "tmp", "home/user_accounts/%s/bp" % self.user, "etc-tls"):
            os.makedirs(os.path.join(r, d), exist_ok=True)
        for d in ("messages", "gpl.bp"):
            os.symlink(os.path.join(SDSYS_TREE, d), os.path.join(r, "sdsys", d))
        with open(os.path.join(r, "sdsys", ".sdcore-install"), "w") as f:
            f.write("commit=model\nbranch=model\ninstalled=2020-01-01 00:00:00\n")
        open(os.path.join(r, "sdsys", "audit"), "w").close()
        open(os.path.join(r, "etc-tls", "api.pem"), "w").write("MODEL\n")
        with open(os.path.join(r, "groups"), "w") as f:
            for n, gid, mem in (("sdusers", "990", [self.user, "root"]), ("sdssh", "991", []), ("sdapi", "992", []), ("sdfiles", "993", []), ("sdfileswrite", "994", []), ("sdu_" + self.user, "1000", [self.user])):
                f.write("%s:x:%s:%s\n" % (n, gid, ",".join(mem)))
        with open(os.path.join(r, "users"), "w") as f:
            f.write("%s\nroot\n" % self.user)
        json.dump({"accounts": {self.user: {"password": "x", "os_password": "x"}}, "servers": {}, "netlogins": {}, "vocs": {}, "files": {}, "locks": {}},
                  open(os.path.join(r, "state.json"), "w"))
        reg_env = dict(FAKE_WORLD=r)
        os.environ.update(reg_env)
        reg_write(self.user, os.path.join(r, "home", "user_accounts", self.user), self.user, [])
        for name in ("sudo", "id", "getent", "gpasswd", "groupdel", "userdel", "ss", "openssl"):
            self.wrapper(name, '#!/bin/sh\nexec python3 "$FAKE_TESTPY" --stub %s "$@"\n' % name)
        self.wrapper("chown", '#!/bin/sh\nexit 0\n')        # the model's accounts are not operating system users, and this check never runs as root
        self.wrapper("sd", '#!/bin/sh\nexec python3 "$FAKE_TESTPY" --fake-sd "$@"\n')
        self.wrapper("sd-elevate", '#!/bin/sh\nexec python3 "$FAKE_TESTPY" --fake-elevate "$@"\n')
        # the scripts, copied beside a library and a fake probe, exactly as they sit in gplbld
        for f in [LIB] + SCRIPTS + ["verify-auditwords.py"]:
            shutil.copy(os.path.join(HERE, f), os.path.join(r, "gplbld", f))
        with open(os.path.join(r, "gplbld", PROBE), "w") as f:
            f.write('import subprocess, sys, os\nsys.exit(subprocess.call([sys.executable, os.environ["FAKE_TESTPY"], "--fake-probe"] + sys.argv[1:]))\n')

    def wrapper(self, name, text):
        p = os.path.join(self.root, "bin", name)
        with open(p, "w") as f:
            f.write(text)
        os.chmod(p, 0o755)

    def env(self):
        e = dict(os.environ)
        e.update(PATH=os.path.join(self.root, "bin") + ":" + os.environ["PATH"], WL_SD=os.path.join(self.root, "bin", "sd"), WL_SDSYS=os.path.join(self.root, "sdsys"),
                 WL_AUDIT=os.path.join(self.root, "sdsys", "audit"), WL_ELEVATE=os.path.join(self.root, "bin", "sd-elevate"), WL_TLS_PEM=os.path.join(self.root, "etc-tls", "api.pem"), WL_TMP=os.path.join(self.root, "tmp"),
                 SUDO_USER=self.user, FAKE_WORLD=self.root, FAKE_TESTPY=TESTPY, MODEL_MUTANT=self.mut, HOME=self.root)
        e.pop("FAKE_SUDO_USER", None)
        return e

    def run(self, script, *args, timeout=600):
        t0 = time.time()
        r = subprocess.run(["bash", os.path.join(self.root, "gplbld", script), "--logged"] + list(args), capture_output=True, text=True, errors="replace",
                           env=self.env(), timeout=timeout, cwd=self.root, input="")
        r.seconds = time.time() - t0
        return r

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


ROW = re.compile(r"^\s+(PASS|FAIL)\s+(\S+)(.*)$")
SHELL_ERR = re.compile(r"unbound variable|command not found|syntax error|: line \d+: |No such file or directory|MODEL ERROR|model: no ")


def rows_of(text):
    got = {"PASS": [], "FAIL": []}
    for l in text.split("\n"):
        m = ROW.match(l)
        if m:
            got[m.group(1)].append((m.group(2), m.group(3).strip()))
    return got


def model_run(label, script, args, mut, expect_ok, expect_fail_ids=(), min_pass=1, setup=None, extra=None, timeout=600):
    w = World(mut)
    try:
        if setup:
            setup(w)
        r = w.run(script, *args, timeout=timeout)
        out = r.stdout + r.stderr
        rows = rows_of(r.stdout)
        shell = [l for l in out.split("\n") if SHELL_ERR.search(l) and not l.lstrip().startswith(("FAIL", "|", ">", "     ")) and "NOTE" not in l]
        check("M %s: no shell error in the run" % label, not shell, " / ".join(shell[:3]))
        if expect_ok:
            check("M %s: exit 0, %d passed, 0 failed" % (label, len(rows["PASS"])), r.returncode == 0 and not rows["FAIL"] and len(rows["PASS"]) >= min_pass,
                  "rc=%d pass=%d fail=%s\n%s" % (r.returncode, len(rows["PASS"]), rows["FAIL"][:6], r.stdout[-500:]))
        else:
            failed_ids = {i for i, _d in rows["FAIL"]}
            missing = [i for i in expect_fail_ids if not any(f == i or f.startswith(i) for f in failed_ids)]
            check("M %s: exit non-zero and the rows %s fail (%s)" % (label, "/".join(expect_fail_ids), ", ".join(sorted(failed_ids))[:120]),
                  r.returncode != 0 and not missing, "rc=%d missing=%s failed=%s" % (r.returncode, missing, sorted(failed_ids)))
        if extra:
            extra(w, r, rows)
        return r, rows, w
    finally:
        w.close()


def groups_state(w):
    g = {}
    for l in open(os.path.join(w.root, "groups")):
        n, _x, _gid, mem = l.rstrip("\n").split(":")
        g[n] = [m for m in mem.split(",") if m]
    return g


def setup_writegroup(w):
    # the person is the account: a user account of its own, in sdusers, with the register record the script reads
    pass


WG_MUTANTS = [
    # name,                                  model mutation,                expected failing row prefixes
    ("the orphan is ignored by files-off", "off-ignores-orphan", ("W4",)),
    ("files-off takes sdfiles out first", "off-sdfiles-first", ("W3",)),
    ("files-off leaves the write membership", "off-keeps-write", ("W3", "W4")),
    ("files-on leaves the orphan's write membership", "on-keeps-orphan-write", ("W5",)),
    ("files-on takes the write group from someone who has both", "on-removes-write-when-both", ("W6",)),
    ("files-write-on is accepted for a person without files", "write-on-without-files", ("W8",)),
    ("files-write-off takes sdfiles too", "write-off-removes-files", ("W9",)),
    ("the files line is printed before the write line", "no-message-order", ("W5",)),
]


def writegroup_models(selftest):
    r, rows, w = model_run("writegroup, faithful model", "witness-sdnet-writegroup.sh", [], "", True, min_pass=30)
    if selftest:
        for name, m, ids in WG_MUTANTS:
            model_run("writegroup, mutant: %s" % name, "witness-sdnet-writegroup.sh", [], m, False, ids)


# ---- the groups witness against a model of the installer and the remover
def groups_models(selftest):
    def seq(label, mut, steps, expect_ok, ids=()):
        w = World(mut)
        try:
            rcs = []
            for script_args, mutate in steps:
                if mutate:
                    mutate(w)
                r = w.run("witness-sdnet-groups.sh", *script_args)
                rcs.append((script_args[0], r))
            out = "\n".join(r.stdout for _a, r in rcs)
            rows = rows_of(out)
            shell = [l for l in (out + "".join(r.stderr for _a, r in rcs)).split("\n") if SHELL_ERR.search(l) and not l.lstrip().startswith(("FAIL", "|"))]
            check("M groups %s: no shell error" % label, not shell, shell[:3])
            last = rcs[-1][1]
            if expect_ok:
                check("M groups %s: every step exits 0 (%d rows passed)" % (label, len(rows["PASS"])), all(r.returncode == 0 for _a, r in rcs) and not rows["FAIL"] and len(rows["PASS"]) >= 3,
                      "%s fail=%s\n%s" % ([(a, r.returncode) for a, r in rcs], rows["FAIL"][:5], out[-400:]))
            else:
                failed = {i for i, _d in rows["FAIL"]}
                miss = [i for i in ids if not any(f.startswith(i) for f in failed)]
                check("M groups %s: the last step fails on %s (%s)" % (label, "/".join(ids), ",".join(sorted(failed))[:80]), last.returncode != 0 and not miss, "rc=%d failed=%s" % (last.returncode, sorted(failed)))
        finally:
            w.close()

    def add_members(w):
        g = groups_read_world(w)
        g["sdfiles"][1][:] = ["ann", "bob"]
        g["sdssh"][1][:] = ["ann"]
        groups_write_world(w, g)

    def installer(w, give_write=None, drop_file_member=False, skip_create=False, recreate_sdfiles=False):
        g = groups_read_world(w)
        if not skip_create and "sdfileswrite" not in g:
            g["sdfileswrite"] = ["994", []]
        if give_write:
            g["sdfileswrite"][1][:] = list(give_write)
        if drop_file_member:
            g["sdfiles"][1][:] = ["ann"]
        if recreate_sdfiles:
            g["sdfiles"][1][:] = []
        groups_write_world(w, g)

    def remover(w, accounts, leave=()):
        g = groups_read_world(w)
        if accounts == "delete":
            for n in ("sdssh", "sdapi", "sdfiles", "sdfileswrite"):
                if n not in leave:
                    g.pop(n, None)
        groups_write_world(w, g)

    # (v) the installer over an install that has sdfiles and no sdfileswrite
    up = lambda **k: [(["arrange-upgrade"], add_members), (["after-upgrade"], lambda w: installer(w, **k))]
    seq("(v) the installer creates an empty sdfileswrite", "", up(), True)
    seq("(v) the installer answers the gate question y for ann", "", [(["arrange-upgrade"], add_members), (["after-upgrade", "--gates-for", "ann"], lambda w: installer(w, give_write=["ann"]))], True)
    if selftest:
        seq("(v) mutant: the installer makes no sdfileswrite", "", up(skip_create=True), False, ("U2",))
        seq("(v) mutant: the installer puts every sdfiles member in sdfileswrite", "", up(give_write=["ann", "bob"]), False, ("U3", "U4"))
        seq("(v) mutant: the installer drops a member of sdfiles", "", up(drop_file_member=True), False, ("U1",))
        seq("(v) mutant: the installer empties sdfiles", "", up(recreate_sdfiles=True), False, ("U1",))
    # (vii) the remover
    def full(w):
        g = groups_read_world(w)
        g["sdfiles"][1][:] = ["ann"]
        g["sdfileswrite"][1][:] = ["ann"]
        g["sdssh"][1][:] = ["ann"]
        groups_write_world(w, g)
    seq("(vii) a DELETE cycle removes the four groups", "", [(["before-delete"], full), (["after-delete", "--accounts", "delete"], lambda w: remover(w, "delete"))], True)
    seq("(vii) the keep-accounts branch leaves them as they were", "", [(["before-delete"], full), (["after-delete", "--accounts", "keep"], lambda w: remover(w, "keep"))], True)
    if selftest:
        seq("(vii) mutant: a DELETE cycle leaves sdfileswrite", "", [(["before-delete"], full), (["after-delete", "--accounts", "delete"], lambda w: remover(w, "delete", leave=("sdfileswrite",)))], False, ("D1",))
        seq("(vii) mutant: the keep-accounts branch removes the groups", "", [(["before-delete"], full), (["after-delete", "--accounts", "keep"], lambda w: remover(w, "delete"))], False, ("D2",))
        seq("(vii) mutant: nothing existed before, so nothing was measured", "", [(["before-delete"], lambda w: remover(w, "delete")), (["after-delete", "--accounts", "delete"], None)], False, ("D0",))


def groups_read_world(w):
    g = {}
    for l in open(os.path.join(w.root, "groups")):
        n, _x, gid, mem = l.rstrip("\n").split(":")
        g[n] = [gid, [m for m in mem.split(",") if m]]
    return g


def groups_write_world(w, g):
    with open(os.path.join(w.root, "groups"), "w") as f:
        for n, (gid, mem) in g.items():
            f.write("%s:x:%s:%s\n" % (n, gid, ",".join(mem)))


# ---- the three long models
FR_MUTANTS = [
    ("a write is allowed without the write group", "write-without-group", ("A3", "A4", "A5", "A6", "A7")),
    ("the server shows only 'status 0' for a refusal (the old text)", "k1-old-text", ("A4",)),
    ("the audit reason is the old one", "k3-old-reason", ("C3",)),
    ("a wrong pin still reaches the server", "wrong-pin-sends", ("M2",)),
    ("files-off leaves the write group", "off-keeps-write", ("C3",)),
    ("a new account is given the whole API", "create-gives-api", ("S1",)),
    ("the manifest has no write key", "manifest-no-write-key", ("C1", "C2", "C3", "C4")),
    ("sd-elevate tls-key gives another hash", "tlskey-differs", ("S4",)),
]


def files_route_models(selftest):
    model_run("files-route, faithful model", "witness-sdnet-files-route.sh", [], "", True, min_pass=100, timeout=900)
    if selftest:
        for name, m, ids in FR_MUTANTS:
            model_run("files-route, mutant: %s" % name, "witness-sdnet-files-route.sh", [], m, False, ids, timeout=900)


GAPS_MUTANTS = [
    ("request 54 is allowed", "gaps-54-allowed", ("W1", "W3")),
    ("TLS 1.2 is accepted", "tls12-accepted", ("T1",)),
    ("a restore does not give the write group back", "restore-drops-write", ("R2",)),
    ("a restore gives the write group to a write-off archive", "restore-gives-write", ("R1",)),
]


def gaps_models(selftest):
    model_run("gaps, faithful model", "witness-sdnet-gaps.sh", [], "", True, min_pass=60, timeout=900)
    if selftest:
        for name, m, ids in GAPS_MUTANTS:
            model_run("gaps, mutant: %s" % name, "witness-sdnet-gaps.sh", [], m, False, ids, timeout=900)


def two_machines_models(selftest):
    def server_setup(w):
        return w.run("witness-sdnet-two-machines.sh", "--role", "server-setup")

    def client(w):
        return w.run("witness-sdnet-two-machines.sh", "--role", "client", "--host", "127.0.0.1", "--server-hash", SERVER_HASH, "--server-epoch", str(int(time.time())), timeout=600)

    w = World("")
    try:
        pwfile = os.path.join(w.root, "tmp", "witness-sdnet-two-machines.pw")
        r1 = server_setup(w)
        out1 = r1.stdout
        rows1 = rows_of(out1)
        check("M two-machines server-setup: exit 0 and no failed row (%d passed)" % len(rows1["PASS"]), r1.returncode == 0 and not rows1["FAIL"] and len(rows1["PASS"]) >= 10, out1[-600:] + r1.stderr[-300:])
        m = re.search(r"server hash : ([0-9a-f]{64})", out1)
        check("M two-machines server-setup: it prints the hash the client needs", m is not None and m.group(1) == SERVER_HASH, out1[-300:])
        pw = open(pwfile).read() if os.path.exists(pwfile) else ""
        check("M two-machines server-setup: the password is in the file (mode 0600) and not in the log", pw.strip() != "" and pw.strip() not in out1 + r1.stderr and
              oct(os.stat(pwfile).st_mode & 0o777) == "0o600" if pw else False, "password in the log, no file, or the mode is wrong")
        # the client role: the model's client and server are the same world; the client account is the real user's
        r2 = client(w)
        rows2 = rows_of(r2.stdout)
        shell = [l for l in (r2.stdout + r2.stderr).split("\n") if SHELL_ERR.search(l) and not l.lstrip().startswith(("FAIL", "|"))]
        check("M two-machines client: no shell error", not shell, shell[:3])
        check("M two-machines client: exit 0, %d passed, 0 failed" % len(rows2["PASS"]), r2.returncode == 0 and not rows2["FAIL"] and len(rows2["PASS"]) >= 20, "rc=%d fail=%s\n%s" % (r2.returncode, rows2["FAIL"][:5], r2.stdout[-600:]))
        check("M two-machines client: the log does not contain the password", pw.strip() != "" and pw.strip() not in r2.stdout + r2.stderr, "password in the log")
        r3 = w.run("witness-sdnet-two-machines.sh", "--role", "server-check")
        rows3 = rows_of(r3.stdout)
        check("M two-machines server-check: exit 0 and the client's write is on the server (%d passed)" % len(rows3["PASS"]), r3.returncode == 0 and not rows3["FAIL"] and len(rows3["PASS"]) >= 4, r3.stdout[-500:])
        r4 = w.run("witness-sdnet-two-machines.sh", "--role", "server-teardown")
        rows4 = rows_of(r4.stdout)
        check("M two-machines server-teardown: exit 0 and nothing is left (%d passed)" % len(rows4["PASS"]), r4.returncode == 0 and not rows4["FAIL"] and len(rows4["PASS"]) >= 3, r4.stdout[-400:])
        check("M two-machines server-teardown: the password file is gone", not os.path.exists(pwfile), pwfile)
    finally:
        w.close()
    if selftest:
        w = World("loopback-only")
        try:
            r1 = server_setup(w)
            failed = {i for i, _d in rows_of(r1.stdout)["FAIL"]}
            check("M two-machines mutant: the listener is on loopback only - server-setup fails SS1 (%s)" % ",".join(sorted(failed)), r1.returncode != 0 and any(f.startswith("SS1") for f in failed), r1.stdout[-300:])
        finally:
            w.close()
        w = World("wrong-pin-sends")
        try:
            server_setup(w)
            r2 = client(w)
            failed = {i for i, _d in rows_of(r2.stdout)["FAIL"]}
            check("M two-machines mutant: a wrong pin still reaches the server - the client fails C5 (%s)" % ",".join(sorted(failed)), r2.returncode != 0 and any(f.startswith("C5") for f in failed), r2.stdout[-300:])
        finally:
            w.close()


def main():
    argv = sys.argv[1:]
    if argv[:1] == ["--fake-sd"]:
        rc = fake_sd(argv[1:])
        out = []
        after_verb_sleeps(out)
        if out:
            sys.stdout.write("\n".join(out) + "\n")
        return rc
    if argv[:1] == ["--stub"]:
        return stub(argv[1], argv[2:])
    if argv[:1] == ["--fake-elevate"]:
        return fake_elevate(argv[1:])
    if argv[:1] == ["--fake-probe"]:
        return fake_probe(argv[1:])
    if os.geteuid() == 0:
        print("test-witness-sdnet-units: CANNOT RUN as root - the witness scripts do real work as root; run this as an ordinary user")
        return 2
    selftest = "--selftest" in argv or "--full" in argv
    full = "--full" in argv
    for f in [LIB, PROBE] + SCRIPTS:
        if not os.path.exists(os.path.join(HERE, f)):
            print("test-witness-sdnet-units: CANNOT RUN - no %s" % f)
            return 2
    only = [a[len("--only="):] for a in argv if a.startswith("--only=")]
    models = {"writegroup": writegroup_models, "groups": groups_models, "files-route": files_route_models, "gaps": gaps_models, "two-machines": two_machines_models}
    if only:
        for n in only:
            if n not in models:
                print("test-witness-sdnet-units: CANNOT RUN - no model called %s (%s)" % (n, " ".join(models)))
                return 2
            models[n](selftest)
    else:
        static_checks()
        lib_mutants()
        writegroup_models(selftest)
        groups_models(selftest)
        if full:
            files_route_models(selftest)
            gaps_models(selftest)
            two_machines_models(selftest)
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name[:300], "" if ok or not detail else "   <- " + str(detail)[:700]))
    print("\ntest-witness-sdnet-units: %d checks, %d failed%s" % (len(results), len(failed), "" if full else "   (the three long models were not run: use --full)"))
    print("NOT MEASURED HERE: whether the real install does what the model does.  The scripts are run by the owner with sudo on a machine; nothing in this file ran one.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
