#!/usr/bin/env python3
#
# test-ai-units.py - the AI integration read off its source as TEXT (S.69 step 2, plan .claude/plan-ai-step2.md).  Free: no sd, no sudo, no install.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ai-units.py [--selftest [--from=N]]
#
# What a behaviour test cannot say: that a rule is still WRITTEN where it must be.  Each group of the plan adds its rows in the commit that builds it.  Exit 0 every
# row passed, 1 a row failed.   --selftest   each MUTANT (a rule taken out of a copy of the text) must turn a row red; --from=N runs the mutants from number N on.
#
# GROUP A, the helper: it never turns certificate checking off, names no way to (no CERT_NONE, no verify=False, no unverified context, no insecure flag),
# checks the host name, accepts https URLs only, never starts a program (no subprocess, os.system, eval, exec, popen), never prints to stdout (the one reply is
# written by os.write), gives the gate group sdaiusers and asks the gate BEFORE the settings are read, keeps the key out of its one log line, writes no audit lines
# (SD does), lets only sdsys and root change a setting, and the shipped providers table is https only, has exactly the three providers, and leaves model and key out.
# GROUP B, the gate and the settings: the group sdaiusers in the installer, the remover and sd-elevate; the helper, its client and the provider table root-owned and
# outside /usr/local/sdsys; the state directory sdai's own and kept by an upgrade; the two units; ai-on / ai-off in modify.account, create.account, the manifest and the
# restore; the set.ai verb (administrator first, every word checked before a command line is built, the key never an argument and never read by SD, no key and no
# whole URL in the audit trail); the messages.
# GROUP C, the kernel calls and the ai verb: the four keys 160-163 are the same numbers in keys.h and int$keys.h and are dispatched together to k_ai; k_ai refuses a caller
# that is not a $internal program before it looks at the action; the audit line is written once, BEFORE the connection, from the kernel's own state (account, the program's name,
# a length) and never holds the text; the request that can be built is an ask and nothing else; the kernel opens a Unix socket and nothing else; a request has a deadline and a
# size limit and is always closed; the ai verb gives an earlier request up, asks the helper for its status, tests the gate, the model and the key, SHOWS the text, asks, and only
# then starts the request, with the fixed sentence and the person's text and nothing of the account; it only displays the answer; the VOC entries and messages 11623-11634.
# GROUP D, the AI choice page (tool.ai): administrator first; it runs only set.ai (through $tk_runx) and modify.account (through $tk_run), every command shown in the confirm box
# before it runs; the names typed (the provider, the account for a gate ON, custom, ca); every word checked against set.ai's own list before a sentence is built, and that list is
# $tk_runx's; the one direct EXECUTE is the hand-over of the terminal to set.ai key, after the confirm, with a sentence made of a fixed text and a name from the fixed four; the page
# reads no key and starts no request, and reads the helper only through K$AI.STATUS and the accounts only through $tk_gates; VOC and help records; the ai row of the gate table.
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SD64))
BP = os.path.join(SD64, "sdsys", "gpl.bp")
FILES = {
    "helper": os.path.join(HERE, "sd-ai"),
    "ctl": os.path.join(HERE, "sd-ai-ctl"),
    "providers": os.path.join(HERE, "ai-providers"),
    "installer": os.path.join(ROOT, "installsdcore.sh"),
    "remover": os.path.join(ROOT, "deletesdcore.sh"),
    "elevate": os.path.join(HERE, "sd-elevate"),
    "socket": os.path.join(SD64, "usr", "lib", "systemd", "system", "sd-ai.socket"),
    "service": os.path.join(SD64, "usr", "lib", "systemd", "system", "sd-ai@.service"),
    "modifya": os.path.join(BP, "modifya"),
    "createa": os.path.join(BP, "createa"),
    "create_account": os.path.join(BP, "create_account"),
    "acc_os_info": os.path.join(BP, "acc_os_info"),
    "restorea": os.path.join(BP, "restorea"),
    "setai": os.path.join(BP, "setai"),
    "createacc.h": os.path.join(SD64, "sdsys", "syscom", "createacc.h"),
    "voc_template": os.path.join(SD64, "sdsys", "voc_template", "set.ai"),
    "op_ai": os.path.join(SD64, "gplsrc", "op_ai.c"),
    "keys.h": os.path.join(SD64, "gplsrc", "keys.h"),
    "int$keys.h": os.path.join(BP, "int$keys.h"),
    "op_kernel": os.path.join(SD64, "gplsrc", "op_kernel.c"),
    "sd.h": os.path.join(SD64, "gplsrc", "sd.h"),
    "gpl.src": os.path.join(SD64, "gpl.src"),
    "ai": os.path.join(BP, "ai"),
    "voc_ai": os.path.join(SD64, "sdsys", "voc_template", "ai"),
    "newvoc_ai": os.path.join(SD64, "sdsys", "newvoc", "ai"),
    "m11623": os.path.join(SD64, "sdsys", "messages", "11623"),
    "m11625": os.path.join(SD64, "sdsys", "messages", "11625"),
    "tool_ai": os.path.join(BP, "tool_ai"),
    "tk_runx": os.path.join(BP, "tk_runx"),
    "tk_gate_info": os.path.join(BP, "tk_gate_info"),
    "voc_tool_ai": os.path.join(SD64, "sdsys", "voc_template", "tool.ai"),
    "h_prov": os.path.join(SD64, "sdsys", "helptext", "tool.ai.providers"),
    "h_acc": os.path.join(SD64, "sdsys", "helptext", "tool.ai.accounts"),
}
MESSAGES = os.path.join(SD64, "sdsys", "messages")
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def code_only(text):
    """The text with comments and docstrings taken out, so a rule named in a comment does not count as code."""
    text = re.sub(r'"""(?:.|\n)*?"""', '""', text)
    return "\n".join(re.sub(r"(^|\s)#.*$", "", l) for l in text.split("\n"))


def bas(text):
    """A BASIC source without its comment lines and the ;* comments after a statement."""
    out = []
    for l in text.split("\n"):
        if l.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s;\*.*$", "", l))
    return "\n".join(out)


def unit_only(text):
    """A systemd unit without its # comment lines."""
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#")) + "\n"


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j > 0 else text[i:]


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def check_a(t):
    c = code_only(t["helper"])
    row("no way to turn certificate checking off: no CERT_NONE, no verify=False, no _create_unverified_context, no 'insecure' anywhere", not re.search(r"CERT_NONE|verify\s*=\s*False|_create_unverified|insecure", c, re.I), "")
    row("the TLS context checks the host name and requires a certificate (check_hostname = True, CERT_REQUIRED) and is not older than TLS 1.2", "ctx.check_hostname = True" in c and "ctx.verify_mode = ssl.CERT_REQUIRED" in c
        and "minimum_version = ssl.TLSVersion.TLSv1_2" in c, "")
    row("the URL a request goes to must be https: URL_RE starts ^https://, and has no query string and no % escape", 'URL_RE = re.compile(r"^https://' in c and "http://" not in c.replace("https://", "")
        and re.search(r'URL_RE = re\.compile\(r"[^"]*\(/\[A-Za-z0-9\._~/\+,:-\]\{0,500\}\)\?\$"\)', c) is not None, "")
    row("it starts no program and runs no text: no subprocess, os.system, os.popen, eval, exec, pickle", not re.search(r"\bsubprocess\b|os\.system|os\.popen|\beval\(|\bexec\(|\bpickle\b", c), "")
    row("it never prints to stdout (the one reply is written with os.write on the connection)", not re.search(r"\bprint\(|sys\.stdout", c), "")
    row("the gate group is sdaiusers and the administrator user for the settings and for status is sdsys", 'GATE_GROUP = "sdaiusers"' in c and 'ADMIN_USER = "sdsys"' in c, "")
    h = c[c.index("def handle("):c.index("def serve(")]
    row("in handle() the gate is asked BEFORE the settings are read (in_group comes before parse_kv)", h.index("in_group(uid, GATE_GROUP)") < h.index("parse_kv("), "")
    row("in handle() the key is read after the model and before the request is checked, the limits are counted before the call, and the call is last", h.index("selected(conf, table)") < h.index("read_key(")
        < h.index("counters(state, uid, time.time(), limits, count=True)") < h.index("ask(state, conf"), "")
    row("in handle() set, keyset and keyclear reach admin_op only for the administrator: is_admin is asked first, and a caller who is not gets noadmin", ordered(h, 'req["op"] in ("set", "keyset", "keyclear")',
        "not is_admin(uid)", '"code": "noadmin"', "admin_op(state, providers_path, req)") and h.count("admin_op(") == 1, "")
    s = c[c.index("def serve("):c.index("def main(")]
    log = re.search(r'log\("([^"]*)"[^\n]*', s)
    row("the one log line names the uid, the provider, the status and the sizes and no text or key", bool(log) and all(w in log.group(0) for w in ("uid=", "provider=", "status=", "in=", "out="))
        and not re.search(r"prompt|text|key|system", log.group(1)), repr(log.group(0) if log else None))
    row("it writes no audit trail: no 'audit' and no K$AUDIT in the helper (SD writes the line BEFORE it asks)", "audit" not in c.lower(), "")
    row("the key file is read with lstat and must be a private regular file (a link or a file others can read is refused)", "os.lstat(path)" in c and "stat.S_ISREG" in c and "0o077" in c, "")
    row("a redirect is never followed: no http.client redirect handling, no urllib.request, no requests", not re.search(r"urllib\.request|import requests|HTTPRedirectHandler", c) and "redirect, which is not followed" in c, "")
    row("the reply is cut to ASCII by hygiene() before it is returned, and an oversize reply is an error, not a cut", c.index("text, replaced = hygiene(text)") < c.index('"toobig", "the reply is over'), "")
    ad = c[c.index("def admin_op("):c.index("def handle(")]
    row("admin_op checks the whole result before it writes (selected, every limit) and write_key/write_conf replace atomically; a key reply never holds the key", ordered(ad, "selected(new, table)", "int_setting(new, k)", "write_conf(state, new)")
        and "os.replace(tmp, path)" in c and "os.replace(tmp, os.path.join(d, name))" in c and 'return {"t": "ok", "key": "set"}' in ad and 'req.get("key")' in ad and ad.count("key") >= 1
        and not re.search(r'\{[^}]*"echo"', ad), "")
    p = t["providers"]
    secs = re.findall(r"^\[([a-z]+)\]$", p, re.M)
    row("the shipped providers table has exactly anthropic, openai and deepseek", secs == ["anthropic", "openai", "deepseek"], repr(secs))
    urls = re.findall(r"^url=(.*)$", p, re.M)
    row("every shipped URL is https and names a host", len(urls) == 3 and all(re.match(r"^https://[a-z.]+/", u) for u in urls), repr(urls))
    row("the shipped table holds no model and no key (the person supplies both)", not re.search(r"^(model|key)", p, re.M | re.I), "")
    k = code_only(t["ctl"])
    kb = between(k, 'elif cmd == "key" and len(rest) == 1:', "if req is None:")
    row("sd-ai-ctl never takes a key as an argument: in the key branch the key comes from getpass or stdin only (rest holds the provider and nothing else), and it is never printed",
        'key = getpass.getpass("Key for %s (not shown): " % rest[0])' in kb and "key = sys.stdin.readline().rstrip" in kb and "rest[1]" not in kb and "sys.argv" not in kb
        and not re.search(r'print\([^)]*key["\']?\s*\)|print\(.*req\b', k) and 'rest[0] not in PROVIDERS' in k, "")


def check_b(t):
    inst, rem = t["installer"], t["remover"]
    loop = re.search(r"for sd_route_group in ([a-z ]+); do", inst)
    row("the installer makes sdaiusers with the other route groups, in the one loop, and adds nobody to it", bool(loop) and "sdaiusers" in loop.group(1).split() and inst.count("for sd_route_group in") == 1
        and not re.search(r"(usermod|addgroup|gpasswd)[^\n]*sdaiusers", inst), "")
    blk = between(inst, "# AI-BEGIN", "# AI-END")
    row("the installer's AI block puts the helper, its client and the provider table in /usr/local/lib/sd-ai, root-owned, 0755 / 0755 / 0644, and not under /usr/local/sdsys",
        blk != "" and "install -d -o root -g root -m 0755 /usr/local/lib/sd-ai" in blk
        and "sudo install -o root -g root -m 0755 gplbld/sd-ai /usr/local/lib/sd-ai/sd-ai" in blk
        and "sudo install -o root -g root -m 0755 gplbld/sd-ai-ctl /usr/local/lib/sd-ai/sd-ai-ctl" in blk and "sudo install -o root -g root -m 0644 gplbld/ai-providers /usr/local/lib/sd-ai/ai-providers" in blk
        and "/usr/local/sdsys" not in blk, "")
    row("...the state directory is sdai's own: /var/lib/sd-ai 0750, keys and state 0700, made only if the user sdai exists, and nothing is deleted or reset there",
        "install -d -o sdai -g sdai -m 0750 /var/lib/sd-ai" in blk and "install -d -o sdai -g sdai -m 0700 /var/lib/sd-ai/keys /var/lib/sd-ai/state" in blk and "getent passwd sdai" in blk
        and not re.search(r"\brm\b|truncate|mv ", blk), "")
    row("...the two units are installed HERE, outside the 'sd.service not yet installed' copy (an upgrade must get them), root-owned 0644", "install -o root -g root -m 0644 usr/lib/systemd/system/sd-ai.socket" in blk
        and "sd-ai@.service" in blk and "SYSTEMDPATH/sd.service" not in blk, "")
    row("...the block comes after the sdai user is made and after sd-elevate is installed", ordered(inst, "sudo useradd --system --user-group --shell /usr/sbin/nologin --home-dir /var/lib/sd-ai --no-create-home sdai",
        "install -o root -g root -m 0755 gplbld/sd-elevate /usr/local/sbin/sd-elevate", "# AI-BEGIN"), "")
    row("the socket is enabled and restarted where the other services start, only when its unit is there", ordered(inst, "sudo systemctl enable sdclient.socket", "if [ -f /usr/lib/systemd/system/sd-ai.socket ]; then",
        "sudo systemctl enable sd-ai.socket", "sudo systemctl restart sd-ai.socket"), "")
    row("the remover stops and disables the socket, removes both units and /usr/local/lib/sd-ai always, and removes /var/lib/sd-ai only in the branch where the accounts are deleted",
        "systemctl stop sd-ai.socket" in rem and "systemctl disable sd-ai.socket" in rem and '"${systemd_dir}/sd-ai.socket"' in rem and '"${systemd_dir}/sd-ai@.service"' in rem
        and "sudo rm -rf /usr/local/lib/sd-ai" in rem and rem.count("rm -rf /var/lib/sd-ai") == 1
        and ordered(rem, 'if [ "$keep_accts" = "DELETE" ]; then', "rm -rf /var/lib/sd-ai", "else") and rem.index('if [ "$keep_accts" = "DELETE" ]; then') < rem.index("rm -rf /var/lib/sd-ai"), "")
    e = t["elevate"]
    row("sd-elevate whitelists sdaiusers by its exact name (no prefix) and never deletes it", "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers) : ;;" in e
        and re.search(r"case \$1 in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\|sdfileswrite\|sdfilesadmin\|sdaiusers\)\s*\n\s*die", e) is not None and "sdaiusers*" not in e, "")
    so, se = unit_only(t["socket"]), unit_only(t["service"])
    row("the socket unit: /run/sd-ai/sock, group sdusers, mode 0660, one process per connection, a cap on connections", ordered(so, "ListenStream=/run/sd-ai/sock", "SocketGroup=sdusers", "SocketMode=0660", "Accept=true")
        and "MaxConnections=" in so and "SocketMode=066" not in so.replace("SocketMode=0660", "") and "0666" not in so, "")
    row("the service unit: the connection is stdin and stdout, user and group sdai, the root-owned program, nothing writable but /var/lib/sd-ai, no new privileges, no capabilities, no raw or netlink sockets",
        ordered(se, "User=sdai", "Group=sdai", "StandardInput=socket", "StandardOutput=socket", "ExecStart=/usr/local/lib/sd-ai/sd-ai") and "NoNewPrivileges=yes" in se and "ProtectSystem=strict" in se
        and "ReadWritePaths=/var/lib/sd-ai\n" in se and re.search(r"^CapabilityBoundingSet=\s*$", se, re.M) is not None and "AF_PACKET" not in se and "AF_NETLINK" not in se and "PrivateTmp=yes" in se
        and "Environment" not in se and "/usr/local/sdsys" not in se, "")
    h, cr, ca2, ai, rs, hd = (t[k] for k in ("modifya", "createa", "create_account", "acc_os_info", "restorea", "createacc.h"))
    row("createacc.h defines CA$AI as 41, once; create.account's AI-ON sets it and nothing else does; the syntax line and the audit gates= list name it", re.search(r"\$define\s+CA\$AI\s+41\b", hd) is not None
        and len(re.findall(r"\$define\s+\S+\s+41\b", hd)) == 1 and re.search(r"case upcase\(token\) = 'AI-ON'\s*\n\s*settings<CA\$AI> = 1\s*\n", cr) is not None and len(re.findall(r"(?<!if )settings<CA\$AI>\s*=", cr)) == 1
        and "{ai-on} {no.query}" in cr and "if settings<CA$AI> = 1 then gates<-1> = 'ai-on'" in cr, "")
    cab = bas(ca2)
    row("!create_account: ai.want is exactly 1; the group sdaiusers is looked for BEFORE the Linux user is made and joined AFTER, a group or other account is refused as for FILES-ON, and the state line 11606 is read off /etc/group",
        "ai.want = (settings<CA$AI> = 1)" in cab and ordered(cab, "if ai.want then", "files.grp.name = 'sdaiusers'", "gosub check.files.group", "if not(create_user(acc.uname)) then", "if ai.want then", "files.grp.name = 'sdaiusers'",
        "gosub join.files.group") and cab.count("or ai.want then") == 2 and "sysmsg(11606, acc.name, if is_grp_member(acc.uname, 'sdaiusers') then 'yes' else 'no')" in cab, "")
    row("the manifest has route.ai from membership of sdaiusers (USER accounts), RESTORE.ACCOUNT reads it, clears it for each section and hands it on as CA$AI only when it is 1",
        ordered(ai, "'route.files.admin: '", "'route.ai: ':(if is_grp_member(user, 'sdaiusers') then 1 else 0)", "'os.sh: '") and re.search(r"= 'route\.ai'\s*; m\.route\.ai = kv", rs) is not None
        and "m.route.ai = ''" in rs and "if m.route.ai = '1' then settings<CA$AI> = 1" in rs and bas(rs).count("CA$AI") == 1, "")
    sa = bas(t["setai"])
    row("set.ai asks for the administrator FIRST (before any word is read or any command built), then checks every word against the allowed characters, then builds the command", ordered(sa, "kernel(K$ADMINISTRATOR, -1)",
        "stop sysmsg(2001)", "words = trim(@sentence)", "convert(okc, space(len(okc)), w)", "stop sysmsg(11622", "begin case") and sa.count("os.execute") == 2, "")
    safe = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:/@+,-")
    row("set.ai quotes every word it passes to the client in single quotes and allows only letters, digits and . _ : / @ + , - (no quote, space, $, ; or backquote)",
        set(re.search(r"okc = '([^']*)'", sa).group(1)) == safe and sa.count("qargs") >= 8
        and "qargs = \"'provider' '\"" in sa and 'os.execute "\'" : ctl' in sa, "")
    row("set.ai key: the terminal is handed to the client (os.execute, no capturing), the key is never in a variable of SD's, and the result is read back from the client's listing, not assumed",
        ordered(sa, "case sub = 'key' and n.words = 3", "os.execute \"'\" : ctl : \"' 'key' '\" : prov : \"' 2>&1\"", "qargs = \"'show'\"", "gosub run.ctl", "gosub check.key", "if not(key.found) then")
        and not re.search(r"os\.execute[^\n]*'key'[^\n]*capturing", sa) and not re.search(r"\binput\b|readline", sa), "")
    audits = re.findall(r"kernel\(K\$AUDIT, ([^\n]*)\)", sa)
    row("every audit line of set.ai is lower case, has no key (no 'key=' and no variable named key) and names a host, never a whole URL", len(audits) == 9 and all(a.lstrip().startswith("'set.ai ") for a in audits)
        and not any(re.search(r"key=|: key\b|curl\b|cpath\b.*curl", a) for a in audits) and not any("curl" in a for a in audits) and any("host=' : chost" in a for a in audits), repr(audits))
    row("set.ai finds its client at /usr/local/lib/sd-ai/sd-ai-ctl, not in the SD system directory (the program that holds the key is root-owned); SD_AI_CTL overrides it for the tests only",
        "ctl = '/usr/local/lib/sd-ai/sd-ai-ctl'" in sa and "env('SD_AI_CTL')" in sa and "@sdsys" not in sa, "")
    row("set.ai is in SDSYS's VOC only: voc_template has it as a verb for $setai and newvoc has no set.ai", t["voc_template"].split("\n")[:3] == ["V", "CA", "$setai"]
        and not os.path.exists(os.path.join(SD64, "sdsys", "newvoc", "set.ai")), "")
    need = [str(n) for n in range(11606, 11623)]
    bad = []
    for n in need:
        p = os.path.join(MESSAGES, n)
        try:
            tx = open(p, encoding="latin-1").read()
        except OSError:
            bad.append(n + " missing")
            continue
        if not tx.endswith("\n") or tx.count("\n") != 1 or tx.strip() == "":
            bad.append(n + " shape")
    row("messages 11606 to 11622 exist, one line each", not bad, repr(bad))
    row("11606 is 'Account %1 has ai %2' and 11607 to 11609 name the helper, its refusal and the usage in lower case words", open(os.path.join(MESSAGES, "11606")).read() == "Account %1 has ai %2\n"
        and "set.ai {" in open(os.path.join(MESSAGES, "11609")).read() and "sd-ai" not in open(os.path.join(MESSAGES, "11608")).read(), "")


def c_only(text):
    """C source without its comments."""
    text = re.sub(r"/\*(?:.|\n)*?\*/", " ", text)
    return re.sub(r"//[^\n]*", "", text)


def check_c(t):
    o = c_only(t["op_ai"])
    ks = dict(re.findall(r"#define\s+K_AI_([A-Z]+)\s+(\d+)", t["keys.h"]))
    bs = dict(re.findall(r"\$define\s+K\$AI\.([A-Z]+)\s+(\d+)", t["int$keys.h"]))
    want = {"START": "160", "POLL": "161", "CANCEL": "162", "STATUS": "163"}
    row("the four AI kernel keys are 160 to 163, the same numbers in keys.h and in int$keys.h, and no other key of either file uses one of them", ks == want and bs == want
        and len(re.findall(r"#define\s+K_\w+\s+16[0-3]\b", t["keys.h"])) == 4 and len(re.findall(r"\$define\s+K\$\S+\s+16[0-3]\b", t["int$keys.h"])) == 4, repr((ks, bs)))
    kk = c_only(t["op_kernel"])
    row("op_kernel.c sends the four keys together to k_ai(action, descr, &result) and nowhere else; sd.h declares k_ai; gpl.src builds op_ai",
        re.search(r"case K_AI_START:\s*case K_AI_POLL:\s*case K_AI_CANCEL:\s*case K_AI_STATUS:\s*k_ai\(action, descr, &result\);\s*break;", kk) is not None and kk.count("k_ai(") == 1
        and "void k_ai(int action, DESCRIPTOR * descr, DESCRIPTOR * result);" in t["sd.h"] and "\nop_ai\n" in t["gpl.src"], "")
    kf = o[o.index("void k_ai("):]
    row("k_ai refuses a caller that is not a $internal program BEFORE the action is looked at: the flag test comes first, answers ERR internal and returns, and the switch follows",
        ordered(kf, "if (!(process.program.flags & HDR_INTERNAL))", 'ai_answer("ERR", "internal", result)', "return;", "switch (action)"), "")
    st = o[o.index("Private void ai_start("):o.index("Private void ai_poll(")]
    row("ai_start: one request at a time (busy is the first test), the audit line is written BEFORE the connection is made, and once", ordered(st, "if (ai.active)", '"busy"', "audit_message(audit);", "ai_connect()")
        and st.count("audit_message(") == 1, "")
    row("the audit line is 'ai request account=%s program=%s bytes.out=%d' in lower case, from the account, the program's name and a length: the text, the prompt and the system sentence are not arguments of it",
        'snprintf(audit, sizeof(audit), "ai request account=%s program=%s bytes.out=%d", account(), pname, (int)(strlen(system) + strlen(prompt)));' in st, "")
    row("the request that can be built is an ask and nothing else: the JSON op is \"ask\" once, and keyset, keyclear and set appear nowhere in op_ai.c", st.count('\\"op\\":\\"ask\\"') == 1
        and not re.search(r'keyset|keyclear|\\"set\\"', o), "")
    row("the arguments are cut system, maxtokens, prompt: the first mark ends the system sentence, the second the number, and the prompt is the rest (a mark inside it moves no field)",
        ordered(st, "system = arg;", "maxt = p + 1;", "prompt = p + 1;", "maxtokens = atoi(maxt);"), "")
    row("a byte above 127 goes out as ? and a control character is escaped (English only; nothing but plain ASCII is sent)", re.search(r"else if \(c >= 128\) \{\s*out\[pos\+\+\] = '\?';", o) is not None
        and "c < 32 || c == 127" in o, "")
    row("the kernel talks to a Unix socket and nothing else: AF_UNIX only, no AF_INET, no host name lookup, no TLS, no program started", "AF_UNIX" in o
        and not re.search(r"AF_INET|netinet|getaddrinfo|gethostbyname|SSL_|\bsystem\s*\(|popen|\bexec[lv]", o), "")
    row("the socket is /run/sd-ai/sock, or the SD_AI_SOCKET of the session's environment (the tests); nothing else names a path", o.count('"/run/sd-ai/sock"') == 1 and o.count("getenv(") == 1
        and 'getenv("SD_AI_SOCKET")' in o, "")
    pl = o[o.index("Private void ai_poll("):o.index("Private void ai_status(")]
    row("a request ends: a 340 second deadline, a reply of at most 512 KB, and the descriptor is closed by ai_reset on every end (the deadline, a reply too big twice, the answer taken, the helper hanging up)",
        re.search(r"#define AI_DEADLINE 340\s*\n", o) is not None and re.search(r"#define AI_REPLY_MAX 524288\s*\n", o) is not None and pl.count("ai_reset();") >= 5, "")
    v = bas(t["ai"])
    row("ai is an internal program catalogued as $ai", re.search(r"\$internal\s*\nprogram ai\s*\n\$catalog \$ai\b", v) is not None, "")
    row("the order in the verb: an earlier request is given up, the helper's status is read, the text is shown, the person is asked, a no stops it, and ONLY THEN is the request started (START appears once)",
        ordered(v, "kernel(K$AI.CANCEL, 0)", "kernel(K$AI.STATUS, 0)", "display sysmsg(11628", "display question", "input ans", "if ans # 'y' and ans # 'yes' then", "stop sysmsg(11630)", "kernel(K$AI.START")
        and v.count("K$AI.START") == 1 and v.count("input ") == 1, "")
    row("what is sent is the fixed sentence and the person's text and nothing of the account: the sentence is assigned once from a literal, and the START argument is exactly it, the limit and the text",
        len(re.findall(r"^\s*system\.text = '[^']*'\s*$", v, re.M)) == 1 and len(re.findall(r"system\.text\s*=", v)) == 1
        and "reply = kernel(K$AI.START, system.text : @fm : 1024 : @fm : question)" in v, "")
    row("the gate, the model and the key are read from the helper's status BEFORE anything is shown: provider empty, gate false, model empty and key false each stop with their own message",
        ordered(v, "prov = st{'provider'}", "if prov = '' then", "stop sysmsg(11624)", "if not(st{'gate'}) then", "stop sysmsg(11625, @who)", "if model = '' then", "stop sysmsg(11626, prov, 'model')",
                "if not(st{'key'}) then", "stop sysmsg(11626, prov, 'key')", "display sysmsg(11628"), "")
    row("the verb only displays the answer: it starts no program and reads no file (no os.execute, execute, perform, chain, openseq, readseq, writeseq) and takes one answer of the person's",
        not re.search(r"\b(os\.execute|execute|perform|chain|openseq|readseq|writeseq|openpath)\b", v), "")
    row("ai is a verb in SDSYS's VOC and in every account's: voc_template and newvoc both name $ai", t["voc_ai"].split("\n")[:3] == ["V", "CA", "$ai"]
        and t["newvoc_ai"].startswith("Verb") and t["newvoc_ai"].split("\n")[1:3] == ["CA", "$ai"], "")
    bad = []
    for n in range(11623, 11635):
        p = os.path.join(MESSAGES, str(n))
        try:
            tx = open(p, encoding="latin-1").read()
        except OSError:
            bad.append("%d missing" % n)
            continue
        if not tx.endswith("\n") or tx.count("\n") != 1 or tx.strip() == "":
            bad.append("%d shape" % n)
    row("messages 11623 to 11634 exist, one line each", not bad, repr(bad))
    row("11623 tells the person to put text that ends with ? in quotes, and 11625 names the way to allow an account (modify.account %1 ai-on)", "in quotes if it ends with ?" in t["m11623"]
        and "modify.account %1 ai-on" in t["m11625"], "")


def sqz(text):
    return re.sub(r"\s+", " ", text).strip()


def check_d(t):
    v = sqz(bas(t["tool_ai"]))
    row("tool.ai is an internal program catalogued as $tool_ai; it opens the base for the administrator FIRST (and prints and stops on a refusal), writes its one audit line, and only then reads the helper",
        re.search(r"^\$internal\s*\nprogram \$tool_ai\s*\n\$catalog \$tool_ai\b", bas(t["tool_ai"]), re.M) is not None
        and ordered(v, "call $tk_open('tool.ai', 'admin', ctx, err) if err # '' then display err stop end", "kernel(K$AUDIT, 'tool start app=tool.ai')", "gosub read.all", "reply = kernel(K$AI.STATUS, 0)"), "")
    row("it may run SET.AI (through $tk_runx) and MODIFY.ACCOUNT (through $tk_run) and nothing else: each list is assigned once and each routine called once, with its own list",
        v.count("allow.set = 'set.ai'") == 1 and v.count("allow.acc = 'modify.account'") == 1 and v.count("call $tk_runx(allow.set, sent, out, st, err)") == 1 and v.count("call $tk_run(allow.acc, sent, out, st, err)") == 1
        and len(re.findall(r"call \$tk_run", v)) == 2, "")
    row("every command is shown in the confirm box BEFORE it runs: in confirm.and.run the box comes first, a result other than run runs nothing, and both run sites follow it; no other site calls $tk_run or $tk_runx",
        ordered(v, "confirm.and.run: call $tk_confirm(sent, el, typed, res, cmsg) if res = 'run' then if use.x then call $tk_runx(", "call $tk_run(allow.acc", "end else msg = cmsg end return") and v.count("call $tk_confirm(sent, el, typed") == 1, "")
    row("the one direct EXECUTE is the hand-over of the terminal to SET.AI KEY: the name is tested against the fixed four, the sentence is a fixed text and that name, the confirm box comes first and anything but run returns, then the screen is given back",
        len(re.findall(r"\bexecute\b", v)) == 1 and not re.search(r"\b(os\.execute|perform|chain|sh)\b", v)
        and ordered(v, "do.key: p = provs<pi> if index(' anthropic openai deepseek custom ', ' ' : p : ' ', 1) = 0 then return", "sent = 'set.ai key ' : p", "call $tk_confirm(sent, el, '', res, cmsg) if res # 'run' then msg = cmsg return end",
                    "call $tk_close(ctx) execute sent", "gosub reopen"), "")
    row("THE KEY IS NOT HANDLED: the page reads nothing at the terminal but the Enter that ends the hand-over (one INPUT, into a variable called junk), has no hidden or masked entry and no GETPASS, and builds no sentence that holds a key",
        v.count("input ") == 1 and "input junk" in v and not re.search(r"getpass|\bmask\b|keyin|rawkey", v, re.I) and "sent = 'set.ai key ' : p el = ''" in v and "sent = 'set.ai key ' : p : ' clear'" in v
        and len(re.findall(r"sent = 'set\.ai key '", v)) == 2, "")
    row("the page starts no request and reads no secret: no K$AI.START and no K$AI.POLL, the only kernel AI call is K$AI.STATUS, the only file opened is the register (one OPENPATH), and no key file is named",
        "K$AI.START" not in v and "K$AI.POLL" not in v and "K$AI.CANCEL" not in v and v.count("K$AI.STATUS") == 1 and v.count("openpath") == 1 and "@sdsys:@ds:'accounts'" in v
        and not re.search(r"/var/lib|keys/|openseq|readseq", v), "")
    row("the names typed: selecting a provider asks for its name (and deselecting asks for none), turning an account's gate ON asks for the account's name (OFF none), Custom asks for 'custom' and a certificate file for 'ca'",
        "sent = 'set.ai provider none' typed = ''" in v and "sent = 'set.ai provider ' : p typed = p" in v and "end else typed = an.name lpid = sel" in v
        and "sent = 'modify.account ' : an.name : ' ' : (if on.now then 'ai-off' else 'ai-on') el = '' typed = '' if on.now then" in v
        and v.count("typed = 'custom'") == 1 and v.count("typed = 'ca'") == 1, "")
    row("every word that is typed is checked against SET.AI's own list before the sentence is built: the model (1 to 80), the four fields and the address of Custom (https:// first), the certificate file, and a limit's name and digits",
        ordered(v, "do.model:", "vmax = 80 gosub valid.word if not(vw.ok) then", "sent = 'set.ai model '") and ordered(v, "do.custom:", "vmax = 40 ; vw = v1 ; gosub valid.word", "vmax = 300 ; vw = v2 ; gosub valid.word ; if not(vw.ok) or v2[1, 8] # 'https://'",
        "vmax = 40 ; vw = v5 ; gosub valid.word", "vmax = 60 ; vw = v6 ; gosub valid.word", "if bad # '' then", "sent = 'set.ai custom '") and ordered(v, "do.ca:", "vmax = 300 gosub valid.word if not(vw.ok) then", "sent = 'set.ai ca '")
        and ordered(v, "do.limit:", "locate ln in lnames<1> setting lk else", "convert('0123456789', space(10), lv)) # ''", "sent = 'set.ai limit '"), "")
    okc_page = re.search(r"\bokc = '([^']*)'", bas(t["tool_ai"]))
    okc_set = re.search(r"\bokc = '([^']*)'", bas(t["setai"]))
    good_x = re.search(r"\bgood = '([^']*)'", bas(t["tk_runx"]))
    row("the page's list of characters, SET.AI's and $tk_runx's are the same set, with no space, quote, semicolon, dollar, backquote, bar, ampersand, angle bracket or backslash in it",
        bool(okc_page and okc_set and good_x) and set(okc_page.group(1)) == set(okc_set.group(1)) == set(good_x.group(1)) and not (set(okc_page.group(1)) & set(" '\"`;$|&<>\\")), repr((okc_page, okc_set, good_x)))
    row("the accounts are read through $tk_gates and only a USER account is listed; the gate is the 'ai' row of the table; the page opens no record of the register itself",
        "call $tk_gates(names<i>, g, ainfo, gerr) if gerr = '' and ainfo<1> = 'USER' then" in v and "if g<k, 1> = 'ai' then ast<an> = g<k, 2>" in v and not re.search(r"\bread(v|u|vu)?\s+\w[\w.]*\s+from\b", v), "")
    row("tool.ai is in SDSYS's VOC only: voc_template has it as a verb for $tool_ai and newvoc has no tool.ai", t["voc_tool_ai"].split("\n")[:3] == ["V", "CA", "$tool_ai"] and not os.path.exists(os.path.join(SD64, "sdsys", "newvoc", "tool.ai")), "")
    row("the two help records exist (title, documentation page, a paragraph) and the page asks for both by their keys", all(len(t[k].strip().split("\n")) >= 3 and t[k].split("\n")[1] == "20-the-ai-helper" for k in ("h_prov", "h_acc"))
        and "'tool.ai.providers'" in v and "'tool.ai.accounts'" in v, "")
    gi = [ln for ln in re.findall(r'rows<-1> = "([^"]*)"', t["tk_gate_info"]) if ln.startswith("ai|")]
    cols = gi[0].split("|") if len(gi) == 1 else []
    ids = [ln.split("|")[0] for ln in re.findall(r'rows<-1> = "([^"]*)"', t["tk_gate_info"])]
    row("the gate table has one 'ai' row: group sdaiusers, words ai-on and ai-off, off as delivered, reaching beyond SD, built, listed after files-admin and before the planned sockets",
        len(cols) == 15 and cols[2:4] == ["ai-on", "ai-off"] and cols[4] == "group" and cols[6] == "sdaiusers" and cols[9] == "off" and cols[13] == "1" and cols[14] == "built"
        and ids.index("ai") == ids.index("files-admin") + 1 and ids.index("sockets") == ids.index("ai") + 1, repr(gi))


GROUP_A_MUTANTS = [
    ("helper", "certificate check off", "ctx.verify_mode = ssl.CERT_REQUIRED", "ctx.verify_mode = ssl.CERT_NONE"),
    ("helper", "host name check off", "ctx.check_hostname = True", "ctx.check_hostname = False"),
    ("helper", "http accepted", 'URL_RE = re.compile(r"^https://', 'URL_RE = re.compile(r"^https?://'),
    ("helper", "a query string is accepted in a URL", "(/[A-Za-z0-9._~/+,:-]{0,500})?$", "(/[A-Za-z0-9._~/+,:?=&-]{0,500})?$"),
    ("helper", "a program is started", "import urllib.parse\n", "import urllib.parse\nimport subprocess\n"),
    ("helper", "the helper prints", "    serve(0, 1, state, providers, sys.stderr.write)\n", "    print('x')\n    serve(0, 1, state, providers, sys.stderr.write)\n"),
    ("helper", "the gate group is renamed", 'GATE_GROUP = "sdaiusers"', 'GATE_GROUP = "sdusers"'),
    ("helper", "the key is put in the log line", 'log("sd-ai: uid=%s provider=%s status=%s in=%s out=%s\\n" % (uid,', 'log("sd-ai: key=%s uid=%s provider=%s status=%s in=%s out=%s\\n" % (name, uid,'),
    ("helper", "the key file may be a link", "os.lstat(path)", "os.stat(path)"),
    ("helper", "the hygiene runs after the size test", "        text, replaced = hygiene(text)\n        if len(text.encode(\"ascii\"))", "        if len(text.encode(\"ascii\", \"replace\"))"),
    ("helper", "the settings are checked for the administrator after they are done", '        if uid is None or not is_admin(uid):\n            return {"t": "err", "code": "noadmin"', '        if False:\n            return {"t": "err", "code": "noadmin"'),
    ("helper", "keyset echoes the key", 'return {"t": "ok", "key": "set"}', 'return {"t": "ok", "key": "set", "echo": key}'),
    ("helper", "the result of a setting is not checked before it is written", "        selected(new, table)", "        pass  #"),
    ("providers", "an http URL in the table", "url=https://api.openai.com", "url=http://api.openai.com"),
    ("providers", "a model in the table", "[openai]\n", "[openai]\nmodel=gpt\n"),
    ("ctl", "the key is taken from the command line", "key = getpass.getpass(", "key = rest[1] if len(rest) > 1 else getpass.getpass("),
]
GROUP_B_MUTANTS = [
    ("installer", "sdaiusers is not made", "sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers; do", "sdssh sdapi sdfiles sdfileswrite sdfilesadmin; do"),
    ("installer", "nobody is added... but the installer adds the installing user", "    sudo groupadd --system \"$sd_route_group\"\n", "    sudo groupadd --system \"$sd_route_group\"\n    sudo usermod -a -G sdaiusers root\n"),
    ("installer", "the helper is put under the sdsys tree", "gplbld/sd-ai /usr/local/lib/sd-ai/sd-ai", "gplbld/sd-ai /usr/local/sdsys/bin/sd-ai"),
    ("installer", "the helper is not root-owned", "sudo install -o root -g root -m 0755 gplbld/sd-ai /usr/local/lib/sd-ai/sd-ai", "sudo install -o sdsys -g sdusers -m 0755 gplbld/sd-ai /usr/local/lib/sd-ai/sd-ai"),
    ("installer", "the keys directory is open", "-m 0700 /var/lib/sd-ai/keys /var/lib/sd-ai/state", "-m 0755 /var/lib/sd-ai/keys /var/lib/sd-ai/state"),
    ("installer", "the units are installed only on a first install", "  sudo install -o root -g root -m 0644 usr/lib/systemd/system/sd-ai.socket /usr/lib/systemd/system/sd-ai.socket\n",
     "  [ -f \"$SYSTEMDPATH/sd.service\" ] || sudo install -o root -g root -m 0644 usr/lib/systemd/system/sd-ai.socket /usr/lib/systemd/system/sd-ai.socket\n"),
    ("installer", "the socket is never restarted", "    sudo systemctl restart sd-ai.socket || true\n", ""),
    ("remover", "the settings and keys are removed on an upgrade", '    if [ -d /var/lib/sd-ai ]; then\n        sudo rm -rf /var/lib/sd-ai\n        echo "Removed /var/lib/sd-ai (the AI settings and keys)."\n    fi\n', ""),
    ("remover", "the helper directory is left behind", "sudo rm -rf /usr/local/lib/sd-ai\n", ""),
    ("elevate", "sdaiusers dropped from the whitelist", "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers) : ;;", "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin) : ;;"),
    ("socket", "the socket is open to everyone", "SocketMode=0660", "SocketMode=0666"),
    ("socket", "the socket is not one process per connection", "Accept=true", "Accept=false"),
    ("service", "the helper runs as sdsys", "User=sdai", "User=sdsys"),
    ("service", "the helper may gain privileges", "NoNewPrivileges=yes", "NoNewPrivileges=no"),
    ("service", "the helper may write anywhere", "ProtectSystem=strict", "ProtectSystem=no"),
    ("service", "the helper has packet sockets", "AF_UNIX AF_INET AF_INET6", "AF_UNIX AF_INET AF_INET6 AF_PACKET"),
    ("service", "the program is the one in the sdsys tree", "ExecStart=/usr/local/lib/sd-ai/sd-ai", "ExecStart=/usr/local/sdsys/bin/sd-ai"),
    ("createacc.h", "CA$AI shares a number", "$define CA$AI              41", "$define CA$AI              40"),
    ("createa", "ai-on is not a word", "         case upcase(token) = 'AI-ON'\n            settings<CA$AI> = 1\n", ""),
    ("create_account", "the group is joined before the Linux user is made", "      if ai.want then\n         files.grp.name = 'sdaiusers'\n         gosub join.files.group\n         if route.stat # 0 then goto exit.create\n      end\n", ""),
    ("create_account", "a group account may be given the ai gate", "if files.want or files.write.want or files.admin.want or ai.want then      ;* 23 Oct 26, S.69 step 2: and no AI gate to give, for the same reason",
     "if files.want or files.write.want or files.admin.want then"),
    ("acc_os_info", "the manifest has no route.ai", "         info<-1> = 'route.ai: ':(if is_grp_member(user, 'sdaiusers') then 1 else 0)", "         info<-1> = 'route.ai: 0'"),
    ("restorea", "route.ai is not restored", "      if m.route.ai = '1' then settings<CA$AI> = 1\n", ""),
    ("setai", "the administrator is not asked first", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("setai", "the words are not checked", "      if trim(convert(okc, space(len(okc)), w)) # '' then stop sysmsg(11622, w[1, 40])    ;* %1 has a character that is not allowed here\n", ""),
    ("setai", "a semicolon is an allowed character", "0123456789._:/@+,-'", "0123456789._:/@+,-;'"),
    ("setai", "the key is captured by SD", "os.execute \"'\" : ctl : \"' 'key' '\" : prov : \"' 2>&1\"", "os.execute \"'\" : ctl : \"' 'key' '\" : prov : \"' 2>&1\" capturing keyout"),
    ("setai", "the whole URL goes to the audit trail", "' host=' : chost)", "' host=' : curl)"),
    ("setai", "the client is looked for in the SD system directory", "if ctl = '' then ctl = '/usr/local/lib/sd-ai/sd-ai-ctl'", "if ctl = '' then ctl = @sdsys : @ds : 'bin' : @ds : 'sd-ai-ctl'"),
    ("voc_template", "set.ai is a different program", "$setai", "$setviewer"),
]
M_C = len(GROUP_A_MUTANTS) + len(GROUP_B_MUTANTS)         # the first mutant of group C (23 Oct 26): --from=M_C runs only these
GROUP_C_MUTANTS = [
    ("op_ai", "any program may call the kernel keys", "if (!(process.program.flags & HDR_INTERNAL)) {", "if (0) {"),
    ("op_ai", "the audit line is not written", "  audit_message(audit);\n", ""),
    ("op_ai", "a second audit call after the connection", "  ai.fd = ai_connect();\n  if (ai.fd < 0) {\n    free(req);", "  ai.fd = ai_connect();\n  audit_message(audit);\n  if (ai.fd < 0) {\n    free(req);"),
    ("op_ai", "the text goes into the audit line", 'bytes.out=%d", account(), pname, (int)(strlen(system) + strlen(prompt)));', 'bytes.out=%d %s", account(), pname, (int)(strlen(system) + strlen(prompt)), prompt);'),
    ("op_ai", "the kernel includes the network header", "#include <sys/un.h>\n", "#include <sys/un.h>\n#include <netinet/in.h>\n"),
    ("op_ai", "the request is a settings operation", '\\"op\\":\\"ask\\"', '\\"op\\":\\"keyset\\"'),
    ("op_ai", "a byte above 127 is sent as it is", "    } else if (c >= 128) {\n      out[pos++] = '?';", "    } else if (c >= 128) {\n      out[pos++] = (char)c;"),
    ("op_ai", "the deadline is a thousand times longer", "#define AI_DEADLINE 340 /*", "#define AI_DEADLINE 340000 /*"),
    ("op_ai", "the number is read from the prompt", "maxtokens = atoi(maxt);", "maxtokens = atoi(prompt);"),
    ("keys.h", "a key number is moved", "#define K_AI_POLL            161", "#define K_AI_POLL            171"),
    ("int$keys.h", "a key number is moved in BASIC", "$define K$AI.CANCEL       162", "$define K$AI.CANCEL       172"),
    ("op_kernel", "POLL is not dispatched", "    case K_AI_POLL:\n    case K_AI_CANCEL:", "    case K_AI_CANCEL:"),
    ("ai", "the preview answer is not tested", "   if ans # 'y' and ans # 'yes' then", "   if @false then"),
    ("ai", "nobody is asked", "   input ans\n", "   ans = 'y'\n"),
    ("ai", "the account is put into the system sentence", "   system.text = 'You are", "   system.text = @who : 'You are"),
    ("ai", "the account is put into the request", "system.text : @fm : 1024 : @fm : question)", "system.text : @fm : 1024 : @fm : question : @who)"),
    ("ai", "the gate is not read from the status", "   if not(st{'gate'}) then", "   if @false then"),
    ("ai", "the answer is run", "   display sysmsg(11634, j{'in'}", "   os.execute text\n   display sysmsg(11634, j{'in'}"),
    ("newvoc_ai", "ai is a different program for accounts", "$ai", "$pdf"),
    ("m11623", "the usage no longer mentions quotes", "Put the text in quotes if it ends with ?", ""),
]
M_D = M_C + len(GROUP_C_MUTANTS)                           # the first mutant of group D (23 Oct 26)
GROUP_D_MUTANTS = [
    ("tool_ai", "the confirm box is skipped", "   call $tk_confirm(sent, el, typed, res, cmsg)\n   if res = 'run' then\n      if use.x then", "   res = 'run'\n   if res = 'run' then\n      if use.x then"),
    ("tool_ai", "no name is typed to select a provider", "      sent = 'set.ai provider ' : p\n      typed = p\n", "      sent = 'set.ai provider ' : p\n      typed = ''\n"),
    ("tool_ai", "no name is typed to turn a gate on", "      typed = an.name\n      lpid = sel", "      typed = ''\n      lpid = sel"),
    ("tool_ai", "Custom needs no word", "   typed = 'custom'\n", "   typed = ''\n"),
    ("tool_ai", "a certificate file needs no word", "      typed = 'ca'\n", "      typed = ''\n"),
    ("tool_ai", "a semicolon is an allowed character", "0123456789._:/@+,-'", "0123456789._:/@+,-;'"),
    ("tool_ai", "the page may run sh", "allow.set = 'set.ai'", "allow.set = 'set.ai sh'"),
    ("tool_ai", "the key hand-over is not guarded by the fixed four", "   if index(' anthropic openai deepseek custom ', ' ' : p : ' ', 1) = 0 then return\n", ""),
    ("tool_ai", "the key is put in the sentence", "   sent = 'set.ai key ' : p\n   el = ''\n", "   sent = 'set.ai key ' : p : ' ' : kv\n   el = ''\n"),
    ("tool_ai", "the model is not checked", "   vmax = 80\n   gosub valid.word\n", "   vmax = 80\n   vw.ok = 1\n"),
    ("tool_ai", "the page is opened for anyone", "   call $tk_open('tool.ai', 'admin', ctx, err)\n   if err # '' then\n      display err\n      stop", "   call $tk_open('tool.ai', '', ctx, err)\n   if err # '' then\n      display err\n      stop"),
    ("tool_ai", "the page starts a request", "   reply = kernel(K$AI.STATUS, 0)\n   if reply<1> = 'D' then", "   void kernel(K$AI.START, 'x')\n   reply = kernel(K$AI.STATUS, 0)\n   if reply<1> = 'D' then"),
    ("tool_ai", "the page asks for a key itself", "   crt sysmsg(11865) :", "   input kv\n   crt sysmsg(11865) :"),
    ("tool_ai", "an account that is not a person is listed", "if gerr = '' and ainfo<1> = 'USER' then", "if gerr = '' then"),
    ("voc_tool_ai", "tool.ai is another program", "$tool_ai", "$tool_viewers"),
    ("tk_gate_info", "the ai gate is on as delivered", "|ai-on|ai-off|group||sdaiusers||at the next request|off|AI|", "|ai-on|ai-off|group||sdaiusers||at the next request|on|AI|"),
    ("tk_gate_info", "the ai gate is another group", "|group||sdaiusers||at the next request|off|AI|", "|group||sdusers||at the next request|off|AI|"),
    ("h_acc", "the help record points at another page", "20-the-ai-helper", "01-accounts-and-security"),
]


def load():
    t = {}
    for k, p in FILES.items():
        with open(p, encoding="latin-1") as f:
            t[k] = f.read()
    return t


def run_all(t):
    check_a(t)
    check_b(t)
    check_c(t)
    check_d(t)


def selftest(first):
    import contextlib
    import io
    global passed, failed
    base = load()
    bad = 0
    for i, (key, name, old, new) in enumerate(GROUP_A_MUTANTS + GROUP_B_MUTANTS + GROUP_C_MUTANTS + GROUP_D_MUTANTS):
        if i < first:
            continue
        if base[key].count(old) != 1:
            print("  [FAIL] mutant %r: the old text occurs %d times in %s, it must occur once" % (name, base[key].count(old), key))
            bad += 1
            continue
        t = dict(base)
        t[key] = base[key].replace(old, new)
        p0, f0 = passed, failed
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                run_all(t)
            except (ValueError, AttributeError, IndexError):
                failed += 1                     # a rule the mutation broke so far that the text can no longer be read counts as caught
        caught = failed > f0
        passed, failed = p0, f0
        print("  [%s] mutant %d: %s" % ("caught" if caught else "MISSED", i, name))
        bad += not caught
    p0, f0 = passed, failed
    with contextlib.redirect_stdout(io.StringIO()):
        run_all(base)
    ok = failed == f0
    passed, failed = p0, f0
    print("  [%s] control: the unmutated text passes every row" % ("ok" if ok else "FAIL"))
    bad += not ok
    print("\nselftest: %s" % ("all behaved" if bad == 0 else "%d problem(s)" % bad))
    return 0 if bad == 0 else 1


def main():
    if "--selftest" in sys.argv:
        first = 0
        for a in sys.argv:
            if a.startswith("--from="):
                first = int(a[len("--from="):])
        return selftest(first)
    run_all(load())
    print("\ntest-ai-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 and passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
