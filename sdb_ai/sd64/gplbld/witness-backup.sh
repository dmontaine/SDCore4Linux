#!/usr/bin/env bash
#
# witness-backup.sh - SET.BACKUP.DIRECTORY, BACKUP.ACCOUNT, RESTORE.ACCOUNT and
#                     SETTINGS.REPORT (S.50) on a real install of the full
#                     product: what the owner's hand sheet
#                     ~/pCloudDrive/backupcommands-linux.txt runs, plus the
#                     paths the sheet does not reach (several zips and LATEST,
#                     a bare zip name, NO.QUERY, an account that no longer
#                     exists, another session logged in, and archives that lie).
#
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-backup.sh
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-backup.sh --commit
#
# ***IT NEEDS sudo, AND ONLY FOR --commit.***  Without it the script prints what
# it would do and exits 2: a dry run is not a pass.
#
# Exit 0 every check passed, 1 a check failed (or was not reached), 2 it could
# not run.
#
# WRITTEN 5 Oct 2026, after the owner's Parts 1-4 passed on his own install and
# he said further testing in a VM was fine.  The sheet is written for a person;
# this is the repeatable half, and it is what a reinstall of the full product
# should be run against.
#
# ===========================================================================
# WHAT IT NEEDS AND WHAT IT CHANGES
# ===========================================================================
#   * NO OTHER SD SESSION may be open while it runs: BACKUP.ACCOUNT and
#     RESTORE.ACCOUNT refuse until every other session has gone (13000).  It
#     waits up to 90 s at the start for the machine to be quiet and refuses to
#     run if it is not.  On a test VM whose only login is forced into SD, that
#     means starting it detached (systemd-run) and reading the log afterwards
#     through the hypervisor, never through an SD session - an SD session
#     opened while it runs makes a row refuse and is itself a measurement
#     error.
#   * It makes two throwaway accounts, zzbak1 and zzbak2, through CREATE.ACCOUNT
#     (their Linux users and passwords are SD's own flow; the password is
#     generated per run and printed nowhere), and deletes them at the end.
#   * It saves a backup directory, /var/backups/sdbackups, in /etc/sd.conf, and
#     puts that file back byte for byte at the end.  It REFUSES TO RUN if a
#     backup directory is already saved or that directory exists: it will not
#     touch state it did not make.
#   * RESTORE.ACCOUNT LATEST ALL restores EVERY registered account, including
#     the ones this script did not make.  Those are replaced with what the same
#     run's ALL backup took a moment earlier; their tree signature is measured
#     before and after and must be equal (a restore of an unchanged account is
#     the identity).  A tar of every account directory is taken first and kept.
#
# ===========================================================================
# HOW A ROW IS JUDGED
# ===========================================================================
#   * ANCHORED ON THE SUCCESS WORDING, which the failure paths do not print:
#     the messages are 13008/13009 (backup), 13015/13022/13023/13025 (restore),
#     13040/13044 (the backup directory); each refusal row anchors on its own
#     message (13000, 13005, 13014, 13034, 13047, 13013) and the rows around it
#     check that NOTHING CHANGED.
#   * THE DISK IS THE SECOND INSTRUMENT.  SD says "9 files, 50214 bytes, 9
#     directories"; find says it too, before the backup, and after the restore.
#     SD's own message is never the only evidence that a restore put things back.
#   * A TREE SIGNATURE (sha256 of every file and its name) says "this account
#     did not change" for the rows that claim an account was left alone.  It
#     masks the hashed-file usage counters (see sig(): measured, not assumed),
#     because opening an account's VOC bumps them and a backup of an account
#     or a DELETE.ACCOUNT of another opens it.
#   * A ROW WHOSE PRECONDITION FAILED IS NOT A PASS: it is counted as NOT
#     REACHED, which is a failure.  A phase is gated on what it needs.
#
# WHAT IS NOT HERE: the login hold (13002) - it lasts only while a verb runs, so
# a live session cannot be started inside it; the sandbox run measured it.  A
# Solo archive on the full product (13021) and a manifest/archive count
# disagreement caused by a failing archiver (13007) need an archive made by
# another product or a broken archiver.  Globally catalogued programs (gcat)
# need CATALOG GLOBAL, which the sandbox run measured.
#
set -u
export LC_ALL=C

# The script names itself by absolute path, every variable expanded - the
# re-run command it prints lands in somebody else's shell.
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"

SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
REGISTER="$SDSYS/accounts"
ACCOUNTS_ROOT=/home/sd/user_accounts
SDCONF=/etc/sd.conf
BAK=/var/backups/sdbackups
HOST=$(hostname)
A1=zzbak1
A2=zzbak2

COMMIT=0
LOG=""
WAIT=90

PASS=0
FAIL=0
NOT_REACHED=0
GROUND_CLEAR=0
MADE_A1=0
MADE_A2=0
MADE_BAK=0
CONF_COPY=""
SAFETY_TAR=""
HOLD_PID=""
PW_OS=""

for arg in "$@"; do
    case "$arg" in
        --commit)  COMMIT=1 ;;
        --log=*)   LOG="${arg#--log=}" ;;
        --wait=*)  WAIT="${arg#--wait=}" ;;
        -h|--help) sed -n '2,12p' "$0"; exit 2 ;;
        *) echo "witness-backup: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done

if [ -z "$LOG" ]; then
    LOG="/var/tmp/witness-backup.$(date +%Y%m%d-%H%M%S).log"
fi

say()   { printf '%s\n' "$*"; }
head2() { say ""; say "=== $* ============================================"; }
strip() { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g'; }

if [ "$COMMIT" -eq 0 ]; then
    say "witness-backup: DRY RUN - it changes nothing"
    say "  It would, as root and with no other SD session open:"
    say "    1  save $BAK as the backup directory (SET.BACKUP.DIRECTORY), refusals first"
    say "    2  CREATE.ACCOUNT USER $A1 and $A2, and make one file in each as the account itself"
    say "    3  BACKUP.ACCOUNT one account, two accounts, ALL, TO a directory, and every refusal;"
    say "       LATEST with and without a qualifying zip; an account session held open"
    say "    4  change both accounts, then RESTORE.ACCOUNT by bare name, NO.QUERY, LATEST, LATEST ALL,"
    say "       answering n, with another session open, and from three tampered archives"
    say "    5  DELETE.ACCOUNT $A2 and restore it (CREATED, with a new Linux user)"
    say "    6  SETTINGS.REPORT, on the screen and into the backup directory"
    say "    7  put everything back: accounts, $SDCONF, $BAK"
    say ""
    say "  A DRY RUN IS NOT A PASS.  Exit 2.  To measure:"
    say "    sudo bash $SELF --commit"
    exit 2
fi

exec > >(tee -a "$LOG") 2>&1

# Every check prints what it compared, not only what it concluded.
ck() {
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        PASS=$((PASS + 1)); say "  [PASS] $name: expected '$want', got '$got'"
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: expected '$want', got '$got'"
    fi
}

# Anchored on a string that appears ONLY on the path being claimed.
ck_says() {
    local name="$1" needle="$2" text="$3"
    if printf '%s' "$text" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1)); say "  [PASS] $name: found \"$needle\""
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: did NOT find \"$needle\""
    fi
}

ck_silent() {
    local name="$1" needle="$2" text="$3"
    if printf '%s' "$text" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: found \"$needle\" and must not have"
    else
        PASS=$((PASS + 1)); say "  [PASS] $name: \"$needle\" absent, as required"
    fi
}

# ***A ROW WHOSE PRECONDITION FAILED IS NOT A PASS.***
not_reached() {
    FAIL=$((FAIL + 1)); NOT_REACHED=$((NOT_REACHED + 1))
    say "  [NOT REACHED] $1 - its precondition failed above, so it measured nothing"
}

yesno_user()  { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group() { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_dir()   { [ -d "$1" ] && echo yes || echo no; }
yesno_file()  { [ -e "$1" ] && echo yes || echo no; }

# files, bytes and directories of an account's tree, counted the way the archiver
# counts them (directories exclude the account directory itself).
counts() {
    local d="$ACCOUNTS_ROOT/$1" f b n
    f=$(find "$d" -type f | wc -l)
    b=$(find "$d" -type f -printf '%s\n' | awk '{s += $1} END {print s + 0}')
    n=$(find "$d" -mindepth 1 -type d | wc -l)
    echo "$f $b $n"
}

# A signature of a tree: every file's name and content.  "Did not change" is this staying equal.
#
# ***ONE THING IS MASKED, AND IT WAS MEASURED BEFORE IT WAS MASKED (5 Oct 2026).***  A hashed file's
# primary subfile (%0) carries FILESTATS in its header (dh_stat.h: 24 int32 counters, bytes 80-175 of
# the DH_HEADER - opens, reads, writes, selects ...), and any operation that merely OPENS or SELECTs an
# account's VOC bumps them: BACKUP.ACCOUNT of that account (opens +1, reads +N, selects +1), and
# DELETE.ACCOUNT of ANOTHER account (the same three), each seen as exactly four bytes at 84, 88-89
# and 104 of voc/%0 (cmp -l on the VM).  A signature that counted them called every account "changed"
# by a backup of it.  Only those 96 bytes, only in a file named %0 that starts with the primary-header
# magic 0x209A, are zeroed; every other byte of every file is in.
sig() {
    python3 - "$ACCOUNTS_ROOT/$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]
h = hashlib.sha256()
for dp, dn, fn in os.walk(root):
    dn.sort()
    for f in sorted(fn):
        p = os.path.join(dp, f)
        d = open(p, "rb").read()
        if f == "%0" and d[:2] == b"\x9a\x20" and len(d) >= 176:
            d = d[:80] + b"\0" * 96 + d[176:]
        h.update(os.path.relpath(p, root).encode() + b"\0" + hashlib.sha256(d).digest())
print(h.hexdigest()[:16])
PY
}

# Informational: where each tree stood at a named point, so that a row that finds a change can be
# traced to the step that made it.  Prints, never judges.
note_state() {
    local a line=""
    for a in tester "$A1" "$A2"; do
        [ -d "$ACCOUNTS_ROOT/$a" ] && line="$line $a=$(sig "$a")/voc-raw:$(sha256sum "$ACCOUNTS_ROOT/$a/voc/%0" 2>/dev/null | cut -c1-8)"
    done
    say "  [state @ $1]$line"
}

# The "<acct>: N files, M bytes, D directories" line of a backup or restore, as "N M D".
cnt_from_out() {
    printf '%s\n' "$2" | sed -n "s/^ *$1: \\([0-9]*\\) files, \\([0-9]*\\) bytes, \\([0-9]*\\) directories\$/\\1 \\2 \\3/p" | head -1
}

zip_from_out() {
    printf '%s\n' "$1" | sed -n 's/^Backed up [0-9]* account(s) to \(.*\.zip\)$/\1/p' | head -1
}

# Drive one piped sd session AS SDSYS - a real sdsys LOGIN is the only
# administrator (S.26), so the session runs through the root-only loginuid
# bridge.  NARRATION GOES TO fd 2; only sd's own output comes back on fd 1.
# A line "_PW_" is the throwaway Linux password and is never echoed.
run_sd() {
    local title="$1"; shift
    say "  --- sd session as sdsys: $title ---" >&2
    local line body out
    body=$'\n''TERM 200,9999'
    for line in "$@"; do
        if [ "$line" = "_PW_" ]; then
            say "      > (password answer)" >&2
            body="$body"$'\n'"$PW_OS"
        else
            say "      > $line" >&2
            body="$body"$'\n'"$line"
        fi
    done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | (cd "$SDSYS" && timeout 120 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" 2>&1) | strip)
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

# One piped session as an ordinary account, in its own directory.
run_acct() {
    local who="$1" title="$2"; shift 2
    say "  --- sd session as $who: $title ---" >&2
    local line body out
    body=$'\n''TERM 200,9999'
    for line in "$@"; do
        say "      > $line" >&2
        body="$body"$'\n'"$line"
    done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | (cd "$ACCOUNTS_ROOT/$who" && timeout 60 runuser -u "$who" -- "$SD" 2>&1) | strip)
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

# Keep one account's session open for $2 seconds, in the background.  UP is "yes" only when
# the session was SEEN running - a row that relies on it is not reached otherwise.
UP=no
hold_session() {
    local who="$1" secs="$2" i
    say "  --- holding an sd session open as $who for ${secs}s (background) ---" >&2
    ( printf '\nTERM 200,9999\n'; sleep "$secs"; printf 'OFF\n' ) | ( cd "$ACCOUNTS_ROOT/$who" && exec runuser -u "$who" -- "$SD" >/dev/null 2>&1 ) &
    HOLD_PID=$!
    UP=no
    for i in $(seq 1 20); do
        if pgrep -u "$who" -x sd >/dev/null 2>&1; then UP=yes; break; fi
        sleep 1
    done
    say "      held session seen running: $UP (sd processes of $who: $(pgrep -u "$who" -x sd | tr '\n' ' '))" >&2
}

release_session() {
    [ -n "$HOLD_PID" ] && wait "$HOLD_PID" 2>/dev/null
    HOLD_PID=""
    local i
    for i in $(seq 1 30); do
        pgrep -x sd >/dev/null 2>&1 || return 0
        sleep 1
    done
    say "      (an sd session is still running: $(pgrep -a -x sd | tr '\n' ' '))" >&2
}

# A python helper: what is in a zip, as lines a row can anchor on.
zipfacts() {
    python3 - "$1" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
names = z.namelist()
man = z.read("manifest.txt").decode("ascii", "replace")
kv, accts, cur = {}, {}, None
for line in man.split("\n"):
    line = line.rstrip()
    if line.startswith("[account ") and line.endswith("]"):
        cur = line[9:-1]; accts[cur] = {}
    elif ": " in line or line.endswith(":"):
        k, _, v = line.partition(":")
        (accts[cur] if cur else kv)[k.strip()] = v.strip()
print("format=%s" % kv.get("format"))
print("product=%s" % kv.get("product"))
print("accounts=%s" % kv.get("accounts"))
print("host=%s" % kv.get("host"))
print("sections=%s" % ",".join(sorted(accts)))
for a in sorted(accts):
    print("acct %s %s %s %s" % (a, accts[a].get("files"), accts[a].get("bytes"), accts[a].get("dirs")))
print("sdsys_section=%s" % ("yes" if "sdsys" in accts else "no"))
print("members=%d" % len(names))
print("cred_members=%d" % len([n for n in names if "cred" in n.lower()]))
print("bad_members=%d" % len([n for n in names if n.startswith("/") or ".." in n.split("/")]))
for n in names:
    if n.endswith("/%0"):
        print("has %s" % n)
PY
}

cleanup() {
    local rc=$?
    head2 "CLEANUP - putting back whatever this run changed"
    [ -n "$HOLD_PID" ] && { kill "$HOLD_PID" 2>/dev/null; wait "$HOLD_PID" 2>/dev/null; }
    # Only a REGISTERED account is deleted through SD, so its y cannot reach the ":" prompt.
    local a
    for a in "$A1" "$A2"; do
        if [ -e "$REGISTER/$a" ]; then
            say "  $a is still registered; deleting it through SD (as sdsys)"
            printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $a"$'\n''y'$'\n''OFF'$'\n' \
                | timeout 90 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" >/dev/null 2>&1
        fi
    done
    if [ "$GROUND_CLEAR" -eq 1 ]; then
        for a in "$A1" "$A2"; do
            if id -u "$a" >/dev/null 2>&1; then
                userdel -r "$a" >/dev/null 2>&1 && say "  userdel -r $a: done" || say "  userdel -r $a: FAILED - remove it by hand"
            fi
            # DELETE.ACCOUNT keeps the home by design; this run made it, and its user is gone.
            if ! id -u "$a" >/dev/null 2>&1 && [ -d "/home/$a" ]; then
                rm -rf -- "/home/$a" && say "  removed /home/$a (DELETE.ACCOUNT keeps a home; this run made it)"
            fi
        done
        rm -rf -- /home/sd/zz-escaped /tmp/zz-escaped
        if [ -n "$CONF_COPY" ] && [ -f "$CONF_COPY" ]; then
            if cmp -s "$CONF_COPY" "$SDCONF"; then
                say "  $SDCONF is byte for byte what it was before"
            else
                cp -p "$CONF_COPY" "$SDCONF" && say "  $SDCONF put back from the copy taken at the start (it had changed)"
            fi
            rm -f "$CONF_COPY"
        fi
        if [ "$MADE_BAK" -eq 1 ] && [ -d "$BAK" ]; then
            rm -rf -- "$BAK" && say "  removed $BAK (this run made it)"
        fi
    fi
    say "  left behind: registered=$(ls "$REGISTER" | tr '\n' ' ') account dirs=$(ls "$ACCOUNTS_ROOT" | tr '\n' ' ')"
    say "               $A1 user=$(yesno_user "$A1") home=$(yesno_dir "/home/$A1")  $A2 user=$(yesno_user "$A2") home=$(yesno_dir "/home/$A2")"
    say "               BACKUPDIR line: '$(grep -i '^BACKUPDIR' "$SDCONF" 2>/dev/null)'  $BAK exists: $(yesno_dir "$BAK")"
    # THE CLEANUP IS JUDGED TOO: the verdict above is read before it runs, so a machine left changed
    # would otherwise exit 0.  Compared with what was recorded at the start, not with what is expected.
    if [ "$GROUND_CLEAR" -eq 1 ]; then
        local left=""
        [ "$(ls -1 "$REGISTER" | tr '\n' ' ')" = "$REGISTERED_BEFORE" ] || left="$left register-differs"
        [ "$(ls -1 "$ACCOUNTS_ROOT" | tr '\n' ' ')" = "$ACCDIRS_BEFORE" ] || left="$left account-directories-differ"
        for a in "$A1" "$A2"; do
            [ "$(yesno_user "$a")" = yes ] && left="$left user-$a"
            [ "$(yesno_group "sdu_$a")" = yes ] && left="$left group-sdu_$a"
            [ -d "/home/$a" ] && left="$left home-$a"
        done
        [ -n "$(grep -i '^BACKUPDIR' "$SDCONF" 2>/dev/null)" ] && left="$left BACKUPDIR-still-saved"
        [ -e "$BAK" ] && left="$left $BAK"
        [ -e "$SDSYS/login.hold" ] && left="$left login.hold"
        if [ -n "$left" ]; then
            say "  [FAIL] cleanup incomplete:$left"
            [ "$rc" -eq 0 ] && rc=1
        else
            say "  [PASS] cleanup: register, account directories, users, groups, homes, BACKUPDIR and $BAK are as they were before the run"
        fi
    fi
    [ -n "$SAFETY_TAR" ] && say "  a tar of every account directory from before the run is kept at $SAFETY_TAR"
    say "witness-backup: exit $rc  ($([ "$rc" -eq 0 ] && echo 'every check and the cleanup passed' || echo 'see the [FAIL] lines above'))"
    chmod 644 "$LOG" 2>/dev/null
    exit $rc
}
trap cleanup EXIT

# ==========================================================================
say "witness-backup: COMMIT - it will change this system"
say "  date       : $(date -Is)"
say "  uid        : $(id -u) ($(id -un))"
say "  host       : $HOST"
say "  sd         : $SD ($($SD --version 2>&1 | head -1))"
say "  install    : $(tr '\n' ' ' < "$SDSYS/.sdcore-install" 2>/dev/null | sed 's/# Written by[^.]*\.//' | cut -c1-200)"
say "  accounts   : $ACCOUNTS_ROOT"
say "  backup dir : $BAK"
say "  throwaway  : $A1 $A2"
say "  log        : $LOG"

head2 "0. preconditions and the ground being clear"

for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT" "$SDCONF"; do
    if [ ! -e "$p" ]; then
        say "witness-backup: CANNOT RUN - $p does not exist."
        trap - EXIT; exit 2
    fi
done
if [ "$(id -u)" -ne 0 ]; then
    say "witness-backup: CANNOT RUN - --commit needs root."
    say "  re-run as: sudo bash $SELF --commit"
    trap - EXIT; exit 2
fi
for c in python3 runuser pgrep sha256sum; do
    command -v "$c" >/dev/null 2>&1 || { say "witness-backup: CANNOT RUN - $c is not installed."; trap - EXIT; exit 2; }
done

# A backup and a restore refuse while any other session is open: wait for quiet, or refuse.
n=0
while pgrep -x sd >/dev/null 2>&1 && [ "$n" -lt "$WAIT" ]; do sleep 1; n=$((n + 1)); done
if pgrep -x sd >/dev/null 2>&1; then
    say "witness-backup: CANNOT RUN - SD sessions are still open after ${WAIT}s: $(pgrep -a -x sd | tr '\n' ' ')"
    say "  A backup and a restore refuse while any other session exists; this run would measure that, not the verbs."
    trap - EXIT; exit 2
fi
say "  no other sd session (waited ${n}s)"

DIRTY=0
for a in "$A1" "$A2"; do
    [ "$(yesno_user "$a")" = yes ]  && { say "  DIRTY: Linux user $a already exists"; DIRTY=1; }
    [ "$(yesno_group "sdu_$a")" = yes ] && { say "  DIRTY: group sdu_$a already exists"; DIRTY=1; }
    [ "$(yesno_dir "$ACCOUNTS_ROOT/$a")" = yes ] && { say "  DIRTY: $ACCOUNTS_ROOT/$a already exists"; DIRTY=1; }
    [ "$(yesno_file "$REGISTER/$a")" = yes ] && { say "  DIRTY: register record $a already exists"; DIRTY=1; }
    [ "$(yesno_dir "/home/$a")" = yes ] && { say "  DIRTY: /home/$a already exists"; DIRTY=1; }
done
if grep -qi '^BACKUPDIR' "$SDCONF"; then
    say "  DIRTY: $SDCONF already saves a backup directory: $(grep -i '^BACKUPDIR' "$SDCONF")"; DIRTY=1
fi
[ -e "$BAK" ] && { say "  DIRTY: $BAK already exists"; DIRTY=1; }
[ -e "$SDSYS/login.hold" ] && { say "  DIRTY: a login hold is set ($SDSYS/login.hold)"; DIRTY=1; }
ls -d /home/sd/.sdrestore.* >/dev/null 2>&1 && { say "  DIRTY: a restore staging directory exists: $(ls -d /home/sd/.sdrestore.* | tr '\n' ' ')"; DIRTY=1; }
if [ "$DIRTY" -eq 1 ]; then
    say "witness-backup: CANNOT RUN - the ground is not clear (above)."
    say "  This script will not touch state it did not create."
    trap - EXIT; exit 2
fi
GROUND_CLEAR=1
say "  ground clear: neither throwaway exists, no backup directory is saved, no hold, no staging."

CONF_COPY=$(mktemp /var/tmp/witness-backup.sdconf.XXXXXX)
cp -p "$SDCONF" "$CONF_COPY"
SAFETY_TAR="/var/tmp/witness-backup.accounts-before.$(date +%Y%m%d-%H%M%S).tar"
tar -C "$ACCOUNTS_ROOT" -cpf "$SAFETY_TAR" . 2>/dev/null && chmod 600 "$SAFETY_TAR"
say "  safety tar of every account directory: $SAFETY_TAR ($(stat -c %s "$SAFETY_TAR") bytes)"

REGISTERED_BEFORE=$(ls -1 "$REGISTER" | tr '\n' ' ')
ACCDIRS_BEFORE=$(ls -1 "$ACCOUNTS_ROOT" | tr '\n' ' ')
say "  registered before: $REGISTERED_BEFORE"
say "  account directories before: $ACCDIRS_BEFORE"
PW_OS="Zz9-$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-14)"

# ==========================================================================
head2 "1. SET.BACKUP.DIRECTORY"

OUT=$(run_sd "no directory saved yet" "SET.BACKUP.DIRECTORY")
ck_says "1a it says none is set (13045)" "No backup directory is set." "$OUT"
OUT=$(run_sd "a relative path" "SET.BACKUP.DIRECTORY backups")
ck_says "1b a relative path is refused (13046)" "Give the full path of the backup directory" "$OUT"
ck_silent "1b2 and it was not saved" "Backup directory is now" "$OUT"
ck "1b3 $SDCONF carries no BACKUPDIR" "" "$(grep -i '^BACKUPDIR' "$SDCONF")"
OUT=$(run_sd "a full path, made if missing" "SET.BACKUP.DIRECTORY $BAK")
ck_says "1c it is saved (13040)" "Backup directory is now $BAK" "$OUT"
[ -d "$BAK" ] && MADE_BAK=1
ck "1c2 the directory was made" yes "$(yesno_dir "$BAK")"
ck "1c3 it is sdsys's, mode 700" "sdsys 700" "$(stat -c '%U %a' "$BAK" 2>/dev/null)"
ck "1c4 $SDCONF now carries it" "BACKUPDIR=$BAK" "$(grep -i '^BACKUPDIR' "$SDCONF")"
OUT=$(run_sd "read it back" "SET.BACKUP.DIRECTORY")
ck_says "1d it reads back (13044)" "The backup directory is $BAK" "$OUT"

# ==========================================================================
head2 "2. two throwaway accounts, each with a file made by the account itself"

OUT=$(run_sd "CREATE.ACCOUNT USER $A1" "CREATE.ACCOUNT USER $A1" "_PW_" "_PW_")
ck "2a $A1 is registered" yes "$(yesno_file "$REGISTER/$A1")"
[ -e "$REGISTER/$A1" ] && MADE_A1=1
OUT=$(run_sd "CREATE.ACCOUNT USER $A2" "CREATE.ACCOUNT USER $A2" "_PW_" "_PW_")
ck "2b $A2 is registered" yes "$(yesno_file "$REGISTER/$A2")"
[ -e "$REGISTER/$A2" ] && MADE_A2=1
SETUP_OK=0
if [ "$MADE_A1" -eq 1 ] && [ "$MADE_A2" -eq 1 ]; then SETUP_OK=1; fi
if [ "$SETUP_OK" -eq 1 ]; then
    ck "2c $A1 directory is $A1:sdu_$A1, mode 2775" "$A1 sdu_$A1 2775" "$(stat -c '%U %G %a' "$ACCOUNTS_ROOT/$A1")"
    OUT=$(run_acct "$A1" "CREATE.FILE ZZBASE1" "CREATE.FILE ZZBASE1")
    ck_says "2d $A1 made its file" "Created DATA part as zzbase1" "$OUT"
    OUT=$(run_acct "$A2" "CREATE.FILE ZZBASE2" "CREATE.FILE ZZBASE2")
    ck_says "2e $A2 made its file" "Created DATA part as zzbase2" "$OUT"
    ck "2f the files are on disk" "yes yes" "$(yesno_dir "$ACCOUNTS_ROOT/$A1/zzbase1") $(yesno_dir "$ACCOUNTS_ROOT/$A2/zzbase2")"
else
    not_reached "2c-2f the accounts and their files"
    say "witness-backup: the throwaway accounts were not made; every later phase measures nothing."
fi

# ==========================================================================
head2 "3. BACKUP.ACCOUNT"

if [ "$SETUP_OK" -ne 1 ]; then
    not_reached "3 every backup row"
    BAK_OK=0
else
    C1=$(counts "$A1"); C2=$(counts "$A2")
    say "  measured on disk before the first backup: $A1 = $C1, $A2 = $C2  (files bytes dirs)"
    TESTER_SIG0=$(sig tester 2>/dev/null)
    note_state "3 start"

    # ---- 3a one account
    sleep 1
    OUT=$(run_sd "BACKUP.ACCOUNT $A1" "BACKUP.ACCOUNT $A1")
    Z_A1=$(zip_from_out "$OUT")
    ck_says "3a1 it reports the backup (13008)" "Backed up 1 account(s) to $BAK/SD-$HOST-$A1-" "$OUT"
    ck_silent "3a1b and no refusal" "other session(s) are logged in" "$OUT"
    ck "3a2 the zip's name has the shape SD-<host>-<account>-<stamp>.zip" yes \
       "$(printf '%s' "$Z_A1" | grep -Eq "^$BAK/SD-$HOST-$A1-[0-9]{8}-[0-9]{6}\\.zip\$" && echo yes || echo no)"
    ck "3a3 its counts line is what find measured on disk" "$C1" "$(cnt_from_out "$A1" "$OUT")"
    ck "3a4 the zip is there, sdsys:sdusers" "sdsys sdusers" "$(stat -c '%U %G' "$Z_A1" 2>/dev/null)"
    if [ -f "$Z_A1" ]; then
        FACTS=$(zipfacts "$Z_A1" 2>&1); say "  zip facts:"; printf '%s\n' "$FACTS" | sed -e 's/^/      /'
        ck_says "3a5 manifest: format 1" "format=1" "$FACTS"
        ck_says "3a6 manifest: product linux-full" "product=linux-full" "$FACTS"
        ck_says "3a7 manifest: this host" "host=$HOST" "$FACTS"
        ck_says "3a8 manifest: one account, $A1" "sections=$A1" "$FACTS"
        ck_says "3a9 manifest counts equal the disk's" "acct $A1 $C1" "$FACTS"
        ck_says "3a10 $A1's own file is in the archive" "has accounts/$A1/zzbase1/%0" "$FACTS"
        ck_says "3a11 no credential is in the archive" "cred_members=0" "$FACTS"
        ck_says "3a12 no member escapes the account" "bad_members=0" "$FACTS"
    else
        not_reached "3a5-3a12 the zip's contents"
    fi
    ck "3a13 the login hold is cleared" no "$(yesno_file "$SDSYS/login.hold")"
    note_state "after 3a"

    # ---- 3b LATEST with no qualifying zip
    S2=$(sig "$A2")
    OUT=$(run_sd "LATEST for an account no zip names, no ALL zip yet" "RESTORE.ACCOUNT LATEST $A2")
    ck_says "3b1 nothing found (13047)" "No backup of $A2 made on this computer was found in $BAK." "$OUT"
    ck_silent "3b2 no restore ran" "Restore these accounts" "$OUT"
    ck "3b3 $A2 is unchanged" "$S2" "$(sig "$A2")"
    note_state "after 3b"

    # ---- 3c two accounts in one zip
    sleep 2
    OUT=$(run_sd "BACKUP.ACCOUNT $A1 $A2" "BACKUP.ACCOUNT $A1 $A2")
    Z_BOTH=$(zip_from_out "$OUT")
    ck_says "3c1 two accounts, one zip (13008)" "Backed up 2 account(s) to $BAK/SD-$HOST-$A1-$A2-" "$OUT"
    ck "3c2 a counts line for $A1" "$C1" "$(cnt_from_out "$A1" "$OUT")"
    ck "3c3 a counts line for $A2" "$C2" "$(cnt_from_out "$A2" "$OUT")"

    # ---- 3d one account again, with TO (a one-off directory: here the saved one, by name)
    sleep 2
    OUT=$(run_sd "BACKUP.ACCOUNT $A1 TO $BAK" "BACKUP.ACCOUNT $A1 TO $BAK")
    Z_A1B=$(zip_from_out "$OUT")
    ck_says "3d1 TO an existing directory works" "Backed up 1 account(s) to $BAK/SD-$HOST-$A1-" "$OUT"
    ck "3d2 it is a different file from 3a's" "yes" "$([ -n "$Z_A1B" ] && [ "$Z_A1B" != "$Z_A1" ] && echo yes || echo no)"

    # ---- 3e LATEST picks the NEWEST zip whose name admits the account
    sleep 1
    OUT=$(run_sd "LATEST $A1 (three zips name it), answering n" "RESTORE.ACCOUNT LATEST $A1" "n")
    ck_says "3e1 LATEST $A1 is the newest of the three (13048)" "The most recent backup is $Z_A1B" "$OUT"
    ck_says "3e2 answering n abandons it (13024)" "Restore abandoned. Nothing was changed." "$OUT"
    OUT=$(run_sd "LATEST $A2 (only the two-account zip names it), answering n" "RESTORE.ACCOUNT LATEST $A2" "n")
    ck_says "3e3 LATEST $A2 is the two-account zip (13048)" "The most recent backup is $Z_BOTH" "$OUT"
    note_state "after 3e"

    # ---- 3f ALL: every registered account but sdsys - the two made here and whatever was there
    sleep 2
    OTHER_ACCOUNTS=$(ls -1 "$REGISTER" | grep -v -x -e sdsys | tr '\n' ' ')
    say "  accounts an ALL backup takes now: $OTHER_ACCOUNTS"
    OUT=$(run_sd "BACKUP.ACCOUNT ALL" "BACKUP.ACCOUNT ALL")
    Z_ALL=$(zip_from_out "$OUT")
    NALL=$(printf '%s' "$OTHER_ACCOUNTS" | wc -w)
    ck_says "3f1 every account but sdsys, one zip (13008)" "Backed up $NALL account(s) to $BAK/SD-$HOST-all-" "$OUT"
    for a in $OTHER_ACCOUNTS; do
        ck "3f2 a counts line for $a" "$(counts "$a")" "$(cnt_from_out "$a" "$OUT")"
    done
    if [ -f "$Z_ALL" ]; then
        FACTS=$(zipfacts "$Z_ALL" 2>&1)
        ck_says "3f3 the manifest counts $NALL accounts" "accounts=$NALL" "$FACTS"
        ck_says "3f4 sdsys is not in it" "sdsys_section=no" "$FACTS"
        ck_says "3f5 no credential is in the archive" "cred_members=0" "$FACTS"
    else
        not_reached "3f3-3f5 the ALL zip's contents"
    fi

    note_state "after 3f (ALL)"
    # ---- 3g refusals, and they write nothing
    ZN0=$(ls -1 "$BAK" | wc -l)
    OUT=$(run_sd "the refusals" "BACKUP.ACCOUNT nosuchacct" "BACKUP.ACCOUNT sdsys" "BACKUP.ACCOUNT" "BACKUP.ACCOUNT $A1 TO /nonexistent/dir" "BACKUP.ACCOUNT ALL $A1")
    ck_says "3g1 an unregistered name (13005)" "nosuchacct is not a registered account." "$OUT"
    ck_says "3g2 SDSYS is not backed up (13004)" "SDSYS is not backed up or restored with the accounts." "$OUT"
    ck_says "3g3 no arguments is a syntax error (13006)" "Syntax: BACKUP.ACCOUNT name [name ...] [TO directory]" "$OUT"
    ck_says "3g4 TO a missing directory (13010)" "/nonexistent/dir is not a directory." "$OUT"
    ck "3g5 none of the refusals wrote a zip" "$ZN0" "$(ls -1 "$BAK" | wc -l)"

    # ---- 3h another session logged in
    hold_session "$A1" 25
    if [ "$UP" = yes ]; then
        OUT=$(run_sd "BACKUP.ACCOUNT $A2 with $A1's session open" "BACKUP.ACCOUNT $A2")
        ck_says "3h1 refused: other sessions are logged in (13000)" "other session(s) are logged in. Every other session must log out first:" "$OUT"
        ck_says "3h2 and it names the session (13001)" "$A1, process" "$OUT"
        ck_silent "3h3 no backup was made" "Backed up" "$OUT"
        ck "3h4 no zip was written" "$ZN0" "$(ls -1 "$BAK" | wc -l)"
    else
        not_reached "3h1-3h4 the held session was never seen"
    fi
    release_session
    note_state "after 3h (held session)"
    BAK_OK=1
fi

# ==========================================================================
head2 "4. change both accounts AFTER the backups, so a restore has something to undo"

if [ "${BAK_OK:-0}" -ne 1 ]; then
    not_reached "4 every change row"
    CHANGED=0
else
    OUT=$(run_acct "$A1" "CREATE.FILE ZZLATER1" "CREATE.FILE ZZLATER1")
    ck_says "4a $A1 made another file" "Created DATA part as zzlater1" "$OUT"
    OUT=$(run_acct "$A2" "CREATE.FILE ZZLATER2" "CREATE.FILE ZZLATER2")
    ck_says "4b $A2 made another file" "Created DATA part as zzlater2" "$OUT"
    CHANGED=1
    CH1=$(counts "$A1"); CH2=$(counts "$A2")
    say "  now: $A1 = $CH1, $A2 = $CH2  (they differ from the backup's $C1 / $C2)"
    ck "4c $A1 now differs from its backup" yes "$([ "$CH1" != "$C1" ] && echo yes || echo no)"
    note_state "4 changed"
fi

# ==========================================================================
head2 "5. RESTORE.ACCOUNT"

if [ "${CHANGED:-0}" -ne 1 ]; then
    not_reached "5 every restore row"
else
    S1=$(sig "$A1"); S2=$(sig "$A2")
    BARE_A1=$(basename "$Z_A1"); BARE_BOTH=$(basename "$Z_BOTH")

    # ---- 5a refusals that change nothing
    OUT=$(run_sd "restore, answering n (the default)" "RESTORE.ACCOUNT $BARE_A1 $A1" "n")
    ck_says "5a1 it asks, naming what will be replaced (13022)" "$A1 will be REPLACED. It now holds $(echo "$CH1" | cut -d' ' -f1) files, $(echo "$CH1" | cut -d' ' -f2) bytes." "$OUT"
    ck_says "5a2 it asks once (13015)" "Restore these accounts (y/<n>)?" "$OUT"
    ck_says "5a3 n abandons it (13024)" "Restore abandoned. Nothing was changed." "$OUT"
    ck "5a4 $A1 is unchanged" "$S1" "$(sig "$A1")"
    note_state "after 5a"

    hold_session "$A1" 25
    if [ "$UP" = yes ]; then
        OUT=$(run_sd "restore with $A1's session open" "RESTORE.ACCOUNT $BARE_BOTH $A2 NO.QUERY")
        ck_says "5b1 refused: other sessions are logged in (13000)" "other session(s) are logged in. Every other session must log out first:" "$OUT"
        ck_silent "5b2 nothing was restored" "Restored" "$OUT"
        ck "5b3 $A2 is unchanged" "$S2" "$(sig "$A2")"
    else
        not_reached "5b1-5b3 the held session was never seen"
    fi
    release_session
    # The held session was a login as $A1: it wrote its own session files into $A1's tree, so what $A1
    # holds now is measured again, AFTER it, and is what the rows below compare against.
    S1=$(sig "$A1"); CH1=$(counts "$A1")
    note_state "5b after the held session"

    OUT=$(run_sd "the refusals" "RESTORE.ACCOUNT nosuch.zip $A1" "RESTORE.ACCOUNT $BARE_A1 nosuchacct" "RESTORE.ACCOUNT $BARE_A1 sdsys" "RESTORE.ACCOUNT" "RESTORE.ACCOUNT $BARE_A1 ALL $A1")
    ck_says "5c1 a missing archive, looked for in the saved directory (13034)" "$BAK/nosuch.zip does not exist." "$OUT"
    ck_says "5c2 a name not in the zip (13014)" "nosuchacct is not in this backup." "$OUT"
    ck_says "5c3 sdsys is not in a zip either (13014)" "sdsys is not in this backup." "$OUT"
    ck_says "5c4 no arguments: syntax (13016)" "Syntax: RESTORE.ACCOUNT archive name [name ...] {NO.QUERY}" "$OUT"
    ck "5c5 nothing changed: $A1, $A2" "$S1 $S2" "$(sig "$A1") $(sig "$A2")"

    # ---- 5d the restore of one account, by BARE zip name, answering y
    ZN_BEFORE=$(ls -1 "$BAK" | wc -l)
    OUT=$(run_sd "restore $A1 from a bare zip name, answering y" "RESTORE.ACCOUNT $BARE_A1 $A1" "y")
    ck_says "5d1 it names what is replaced, with what it held (13022)" "$A1 will be REPLACED. It now holds $(echo "$CH1" | cut -d' ' -f1) files, $(echo "$CH1" | cut -d' ' -f2) bytes." "$OUT"
    ck_says "5d2 it reports the account (13009)" "$A1: " "$OUT"
    ck "5d3 its counts line is the BACKUP's (what the zip held)" "$C1" "$(cnt_from_out "$A1" "$OUT")"
    ck_says "5d4 it reports the restore (13025)" "Restored 1 account(s) from $BAK/$BARE_A1" "$OUT"
    ck "5d5 the disk agrees: $A1 holds the backup's counts again" "$C1" "$(counts "$A1")"
    ck "5d6 the file made after the backup is gone" "no" "$(yesno_dir "$ACCOUNTS_ROOT/$A1/zzlater1")"
    ck "5d7 the file made before it is back" "yes" "$(yesno_dir "$ACCOUNTS_ROOT/$A1/zzbase1")"
    ck "5d8 $A1's directory is $A1:sdu_$A1, mode 2775" "$A1 sdu_$A1 2775" "$(stat -c '%U %G %a' "$ACCOUNTS_ROOT/$A1")"
    ck "5d9 and its data is $A1:sdu_$A1 too" "$A1 sdu_$A1" "$(stat -c '%U %G' "$ACCOUNTS_ROOT/$A1/zzbase1/%0")"
    ck "5d10 $A2 was not touched" "$S2" "$(sig "$A2")"
    ck "5d11 no zip was written or lost" "$ZN_BEFORE" "$(ls -1 "$BAK" | wc -l)"
    ck "5d12 no staging directory or hold is left" "no no" "$(ls -d /home/sd/.sdrestore.* >/dev/null 2>&1 && echo yes || echo no) $(yesno_file "$SDSYS/login.hold")"
    S1=$(sig "$A1")
    note_state "after 5d"

    # ---- 5e NO.QUERY, from the two-account zip
    OUT=$(run_sd "restore $A2 from the two-account zip, NO.QUERY" "RESTORE.ACCOUNT $BARE_BOTH $A2 NO.QUERY")
    ck_silent "5e1 it did not ask" "Restore these accounts (y/<n>)?" "$OUT"
    ck_says "5e2 it still names what is replaced (13022)" "$A2 will be REPLACED." "$OUT"
    ck_says "5e3 it reports the restore (13025)" "Restored 1 account(s) from $BAK/$BARE_BOTH" "$OUT"
    ck "5e4 the disk agrees: $A2 holds the backup's counts" "$C2" "$(counts "$A2")"
    ck "5e5 $A2's later file is gone" "no" "$(yesno_dir "$ACCOUNTS_ROOT/$A2/zzlater2")"
    ck "5e6 $A1 was not touched, though it is in the same zip" "$S1" "$(sig "$A1")"
    S2=$(sig "$A2")

    # ---- 5f LATEST, named: the newest zip is the ALL zip
    OUT=$(run_acct "$A1" "CREATE.FILE ZZLATER3" "CREATE.FILE ZZLATER3")
    ck_says "5f0 something to undo" "Created DATA part as zzlater3" "$OUT"
    S1=$(sig "$A1")
    OUT=$(run_sd "LATEST $A1, answering y" "RESTORE.ACCOUNT LATEST $A1" "y")
    ck_says "5f1 LATEST names the newest zip that admits it, the ALL zip (13048)" "The most recent backup is $Z_ALL" "$OUT"
    ck_says "5f2 it restored only $A1 (13025)" "Restored 1 account(s) from $Z_ALL" "$OUT"
    ck "5f3 the later file is gone" "no" "$(yesno_dir "$ACCOUNTS_ROOT/$A1/zzlater3")"
    ck "5f4 $A1 holds the ALL backup's counts" "$C1" "$(counts "$A1")"
    ck "5f5 $A2 was not touched by a restore of $A1 from an ALL zip" "$S2" "$(sig "$A2")"
    ck "5f6 nor was tester" "$TESTER_SIG0" "$(sig tester)"
    note_state "after 5f"

    # ---- 5g LATEST ALL
    OUT=$(run_acct "$A1" "CREATE.FILE ZZLATER4" "CREATE.FILE ZZLATER4")
    OUT=$(run_acct "$A2" "CREATE.FILE ZZLATER5" "CREATE.FILE ZZLATER5")
    OUT=$(run_sd "LATEST ALL, answering y" "RESTORE.ACCOUNT LATEST ALL" "y")
    ck_says "5g1 it names the ALL zip (13048)" "The most recent backup is $Z_ALL" "$OUT"
    for a in $OTHER_ACCOUNTS; do
        ck_says "5g2 it lists $a as replaced (13022)" "$a will be REPLACED." "$OUT"
    done
    ck_says "5g3 it asks once (13015)" "Restore these accounts (y/<n>)?" "$OUT"
    ck_says "5g4 it reports every account (13025)" "Restored $NALL account(s) from $Z_ALL" "$OUT"
    ck "5g5 $A1 is the backup's again" "$C1" "$(counts "$A1")"
    ck "5g6 $A2 is the backup's again" "$C2" "$(counts "$A2")"
    ck "5g7 the later files are gone" "no no" "$(yesno_dir "$ACCOUNTS_ROOT/$A1/zzlater4") $(yesno_dir "$ACCOUNTS_ROOT/$A2/zzlater5")"
    ck "5g8 tester - not made by this run - is replaced by itself: its tree is identical" "$TESTER_SIG0" "$(sig tester)"
    ck "5g9 tester's directory is still its own" "tester" "$(stat -c '%U' "$ACCOUNTS_ROOT/tester")"
    note_state "after 5g"

    # ---- 5h LATEST for a name the newest zip does not hold
    S1=$(sig "$A1"); S2=$(sig "$A2")
    OUT=$(run_sd "LATEST for an account the ALL zip does not hold" "RESTORE.ACCOUNT LATEST nosuchacct")
    ck_says "5h1 an ALL zip qualifies by NAME, so it is chosen (13048)" "The most recent backup is $Z_ALL" "$OUT"
    ck_says "5h2 and its manifest refuses (13014): nothing changed" "nosuchacct is not in this backup." "$OUT"
    ck "5h3 nothing changed" "$S1 $S2" "$(sig "$A1") $(sig "$A2")"

    # ---- 5i archives that lie
    mkdir -p /var/tmp/witness-backup.tamper
    python3 - "$Z_A1" /var/tmp/witness-backup.tamper <<'PY'
import sys, zipfile
src, out = sys.argv[1], sys.argv[2]
def tamper(dst, extra_name, extra_data):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for i in zin.infolist():
            zout.writestr(i, zin.read(i.filename))
        zout.writestr(extra_name, extra_data)
tamper(out + "/tamper-count.zip", "accounts/zzbak1/zz-extra-file", "extra")
tamper(out + "/tamper-dotdot.zip", "accounts/zzbak1/../../zz-escaped", "escaped")
tamper(out + "/tamper-abs.zip", "/tmp/zz-escaped", "escaped")
PY
    cp /var/tmp/witness-backup.tamper/tamper-*.zip "$BAK"/ && chown sdsys:sdusers "$BAK"/tamper-*.zip && chmod 664 "$BAK"/tamper-*.zip
    rm -rf /var/tmp/witness-backup.tamper
    ck "5i0 the three tampered archives are in place" "3" "$(ls -1 "$BAK"/tamper-*.zip 2>/dev/null | wc -l)"
    OUT=$(run_sd "a zip with one more file than its manifest says" "RESTORE.ACCOUNT tamper-count.zip $A1")
    ck_says "5i1 refused against its manifest (13013)" "The archive does not match its manifest: $A1" "$OUT"
    ck_says "5i1b and it says nothing was restored" "Nothing was restored." "$OUT"
    ck_silent "5i1c and it did not ask" "Restore these accounts" "$OUT"
    OUT=$(run_sd "a zip with a .. in an entry's path" "RESTORE.ACCOUNT tamper-dotdot.zip $A1")
    ck_says "5i2 refused while unpacking (11017)" "has an empty, '.' or '..' segment" "$OUT"
    ck_silent "5i2b and it did not ask" "Restore these accounts" "$OUT"
    OUT=$(run_sd "a zip with an absolute path" "RESTORE.ACCOUNT tamper-abs.zip $A1")
    ck_says "5i3 refused while unpacking (11017)" "is an absolute path" "$OUT"
    ck_silent "5i3b and it did not ask" "Restore these accounts" "$OUT"
    ck "5i4 nothing was written outside an account" "no no" "$(yesno_file /home/sd/zz-escaped) $(yesno_file /tmp/zz-escaped)"
    ck "5i5 $A1 and $A2 are unchanged" "$S1 $S2" "$(sig "$A1") $(sig "$A2")"
    ck "5i6 no staging directory or hold is left" "no no" "$(ls -d /home/sd/.sdrestore.* >/dev/null 2>&1 && echo yes || echo no) $(yesno_file "$SDSYS/login.hold")"
    note_state "after 5i"

    # ---- 5j an account that no longer exists
    OUT=$(run_sd "DELETE.ACCOUNT $A2" "DELETE.ACCOUNT $A2" "y")
    ck "5j0 $A2 is gone (register, directory, Linux user)" "no no no" "$(yesno_file "$REGISTER/$A2") $(yesno_dir "$ACCOUNTS_ROOT/$A2") $(yesno_user "$A2")"
    say "  (its home survives a plain delete by design: /home/$A2 exists: $(yesno_dir "/home/$A2"))"
    note_state "after the DELETE.ACCOUNT of $A2"
    if [ ! -e "$REGISTER/$A2" ]; then
        OUT=$(run_sd "restore the deleted $A2 from the ALL zip" "RESTORE.ACCOUNT LATEST $A2" "y" "_PW_" "_PW_")
        ck_says "5j1 it will be CREATED (13023)" "$A2 will be CREATED." "$OUT"
        ck_says "5j2 SD made its Linux user" "User $A2 Created" "$OUT"
        ck_says "5j3 it asked for the Linux password: no credential is in a backup" "New password:" "$OUT"
        ck_says "5j4 it reports the restore (13025)" "Restored 1 account(s) from $Z_ALL" "$OUT"
        ck "5j5 $A2 is registered, has its directory and a Linux user again" "yes yes yes" "$(yesno_file "$REGISTER/$A2") $(yesno_dir "$ACCOUNTS_ROOT/$A2") $(yesno_user "$A2")"
        ck "5j6 its directory is $A2:sdu_$A2, mode 2775" "$A2 sdu_$A2 2775" "$(stat -c '%U %G %a' "$ACCOUNTS_ROOT/$A2" 2>/dev/null)"
        ck "5j7 and holds the backup's counts" "$C2" "$(counts "$A2")"
        ck "5j8 its own file is back" "yes" "$(yesno_dir "$ACCOUNTS_ROOT/$A2/zzbase2")"
        ck "5j9 it is in sdusers" "yes" "$(id -nG "$A2" 2>/dev/null | tr ' ' '\n' | grep -qx sdusers && echo yes || echo no)"
        ck "5j10 $A1 was not touched" "$S1" "$(sig "$A1")"
        note_state "after the restore that created $A2"
    else
        not_reached "5j1-5j10 the account was not deleted, so there is nothing to create"
    fi
fi

# ==========================================================================
head2 "6. SETTINGS.REPORT"

if [ "$SETUP_OK" -ne 1 ]; then
    not_reached "6 the report rows"
else
    OUT=$(run_sd "SETTINGS.REPORT on the screen" "SETTINGS.REPORT")
    ck_says "6a it has a system section" "[system]" "$OUT"
    ck_says "6b it names the product" "product: linux-full" "$OUT"
    ck_says "6c it lists the accounts" "account: $A1" "$OUT"
    ck_says "6d and the saved backup directory" "BACKUPDIR=$BAK" "$OUT"
    ck_silent "6e no private key" "PRIVATE KEY" "$OUT"
    ck "6f no password of this run's" "no" "$(printf '%s' "$OUT" | grep -qF -- "$PW_OS" && echo yes || echo no)"
    ck_silent "6g no raw openssl error in the [api] section (a fresh install made none until 5 Oct 2026)" "Could not open file or uri" "$OUT"
    say "  the report's [api] section as printed (informational):"
    printf '%s\n' "$OUT" | sed -n '/^\[api\]/,/^\[groups\]/p' | sed -e 's/^/      /'
    ZN1=$(ls -1 "$BAK" | wc -l)
    OUT=$(run_sd "SETTINGS.REPORT into the backup directory" "SETTINGS.REPORT $BAK")
    ck_says "6h it writes a file (13029)" "Settings report written to $BAK/" "$OUT"
    ck "6i exactly one file more" "$((ZN1 + 1))" "$(ls -1 "$BAK" | wc -l)"
fi

# ==========================================================================
head2 "7. nothing is left over by the verbs themselves"

ck "7a no login hold" no "$(yesno_file "$SDSYS/login.hold")"
ck "7b no restore staging directory" no "$(ls -d /home/sd/.sdrestore.* >/dev/null 2>&1 && echo yes || echo no)"
ck "7c no sd session is running" "" "$(pgrep -x sd | tr '\n' ' ' | sed 's/ $//')"

# ==========================================================================
head2 "8. verdict"
say "  passed      : $PASS"
say "  failed      : $FAIL"
say "  not reached : $NOT_REACHED   (counted in failed - a row that measured nothing)"

if [ "$((PASS + FAIL))" -eq 0 ]; then
    say "witness-backup: FAILED - no check ran, so this proves nothing."
    exit 1
fi
if [ "$FAIL" -eq 0 ]; then
    say "witness-backup: PASSED - $PASS of $PASS checks passed (the cleanup below is judged on its own, and can still fail the run)."
    exit 0
fi
say "witness-backup: FAILED - $FAIL of $((PASS + FAIL)) checks failed ($NOT_REACHED not reached)."
exit 1
