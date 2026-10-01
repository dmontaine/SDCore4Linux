#!/usr/bin/env python3
# Scratch experiment: build a sandbox SD system from the TREE (no install),
# replaying installsdai.sh's assembly and bootstrap passes as an ordinary user.
import getpass, importlib.util, os, shutil, subprocess, sys

SD64 = "/home/don/Projects/SDCore4Linux/sdb_ai/sd64"
spec = importlib.util.spec_from_file_location("sbx", os.path.join(SD64, "gplbld", "sandbox-txnfail.py"))
sbx = importlib.util.module_from_spec(spec); spec.loader.exec_module(sbx)

root = os.path.abspath(sys.argv[1])
step = sys.argv[2] if len(sys.argv) > 2 else "all"
tree = os.path.join(root, "tree")
sysd = os.path.join(root, "sys")
conf = os.path.join(root, "sd.conf")
env = dict(os.environ, SD_CONFIG=conf)

def run(cmd, cwd=None, inp=None, timeout=900):
    print(">", " ".join(cmd), "(cwd %s)" % cwd); sys.stdout.flush()
    p = subprocess.run(cmd, cwd=cwd, env=env, input=inp, capture_output=True, text=True, timeout=timeout)
    out = sbx.ANSI.sub("", p.stdout + p.stderr)
    print(out[-3000:]); print("exit", p.returncode); sys.stdout.flush()
    return p.returncode, out

if step in ("all", "build"):
    os.makedirs(root, exist_ok=True)
    sbx.build(tree, sbx.SANDBOX_PATCHES + [
        ("gplbld/pcode_bld.py", "SDSYS = '/usr/local/sdsys'", "SDSYS = %r" % sysd, "pcode_bld sdsys")])

UID = os.getuid()
USER = getpass.getuser()
CPROC_PATCHES = [
    ("sdsys/gpl.bp/cproc",
     "      if system(27) = 0 then           ;* entered as root?\n",
     "$ifdef IS_INSTALL\n      if system(27) = %d then\n$else\n      if system(27) = 0 then           ;* entered as root?\n$endif\n" % UID,
     "sandbox: install arm grants the sandbox uid"),
    ("sdsys/gpl.bp/cproc",
     "if downcase(kernel(K$USERNAME, 0)) = 'sdsys' and",
     "if downcase(kernel(K$USERNAME, 0)) = '%s' and" % USER,
     "sandbox: the sandbox user plays sdsys"),
    ("sdsys/gpl.bp/cproc",
     "if kernel(K$LOGIN.UID, 'sdsys') = 1 then",
     "if 1 then",
     "sandbox: no sdsys login uid"),
    ("sdsys/gpl.bp/bbproc",
     "if system(27) # 0 then",
     "if system(27) # %d then" % UID,
     "sandbox: bootstrap accepts the sandbox uid"),
    ("sdsys/gpl.bp/login",
     "if  not(is_grp_member(lgn.id,'sdusers')) then",
     "if @false then",
     "sandbox: no sdusers group"),
    ("sdsys/gpl.bp/write_install_dicts",
     "IF SYSTEM(27) # 0 THEN",
     "IF SYSTEM(27) # %d THEN" % UID,
     "sandbox: pass 3 accepts the sandbox uid"),
]

if step in ("all", "assemble"):
    for rel, old, new, label in CPROC_PATCHES:
        sbx.replace_once(os.path.join(tree, rel), old, new, label)
    shutil.copytree(os.path.join(tree, "sdsys"), sysd)
    open(os.path.join(sysd, "gcat", "$CPROC"), "w").close()
    open(os.path.join(sysd, "errlog"), "w").close()
    for d in ("bin", "gplsrc", "gplobj", "terminfo"):
        if os.path.isdir(os.path.join(tree, d)):
            shutil.copytree(os.path.join(tree, d), os.path.join(sysd, d), dirs_exist_ok=True)
    os.makedirs(os.path.join(sysd, "gplbld"), exist_ok=True)
    shutil.copytree(os.path.join(tree, "gplbld", "FILES_DICTS"), os.path.join(sysd, "gplbld", "FILES_DICTS"))
    for src in ("bbproc", "bcomp", "pathtkn"):
        run(["python3", "gplbld/bbcmp.py", sysd, "gpl.bp/" + src, "gpl.bp.out/" + src], cwd=tree)
    run(["python3", "gplbld/pcode_bld.py"], cwd=tree)
    for f in ("Makefile", "gpl.src", "terminfo.src"):
        shutil.copy2(os.path.join(tree, f), sysd)
    shutil.copytree(os.path.join(tree, "gplbld", "microcfg"), os.path.join(sysd, "microcfg"))
    for d in ("dumps", "$cred", "batch.jobs"):
        os.makedirs(os.path.join(sysd, d), exist_ok=True)
    with open(os.path.join(sysd, "accounts", "sdsys"), "w") as f:
        f.write("%s\n\nsdsys\n" % sysd)
    os.makedirs(os.path.join(root, "user_accounts"), exist_ok=True)
    os.makedirs(os.path.join(root, "group_accounts"), exist_ok=True)
    with open(conf, "w") as f:
        f.write("[sd]\nSDSYS=%s\nGRPSIZE=2\nNUMUSERS=20\nSORTMEM=4096\nERRLOG=50\nUSRDIR=%s\nGRPDIR=%s\nDUMPDIR=%s\n"
                % (sysd, os.path.join(root, "user_accounts"), os.path.join(root, "group_accounts"),
                   os.path.join(sysd, "dumps")))

if step == "sess":
    # sbx_fromtree.py <root> sess <cwd> <command> [<command> ...]
    sd = os.path.join(sysd, "bin", "sd")
    cwd = sys.argv[3]
    body = "\nTERM 200,9999\n" + "".join(l + "\n" for l in sys.argv[4:]) + "OFF\n"
    p = subprocess.run([sd], input=body, cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
    print(sbx.ANSI.sub("", p.stdout + p.stderr)); print("exit", p.returncode)

if step == "start":
    box = sbx.Box(root, getpass.getuser()); box.sys = sysd; box.conf = conf
    box.start()

if step == "stop":
    box = sbx.Box(root, getpass.getuser()); box.sys = sysd; box.conf = conf
    box.stop()

if step in ("all", "boot"):
    sd = os.path.join(sysd, "bin", "sd")
    box = sbx.Box(root, getpass.getuser()); box.sys = sysd; box.conf = conf
    box.start()
    run([sd, "-i"], cwd=sysd)
    run([sd, "-internal", "SECOND.COMPILE"], cwd=sysd)
    run([sd, "RUN", "gpl.bp", "write_install_dicts", "NO.PAGE"], cwd=sysd)
    run([sd, "THIRD.COMPILE"], cwd=sysd)
    box.stop()
