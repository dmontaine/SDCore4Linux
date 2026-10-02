#!/usr/bin/env bash
#
# witness-bakdir-install.sh - what only a root run on a real install shows, for the
#                             full product (2 Oct 2026; S.53 and S.54 in PROJECT_STATUS).
#
#   S.54  the command names: /usr/local/bin/sd is a link to the installed sd, and there is
#         NO sd-full (the 1 Oct ruling dropped it).
#   S.53  SET.BACKUP.DIRECTORY through the real privileged helper (sd-elevate, as root):
#         no argument shows; a relative path is refused (13046); a place root may not
#         make in is refused and nothing is made; a missing directory below
#         /var/backups is made by root, owned by sdsys, mode 0700, with the
#         directories on the way 0755 root; sd.conf gets ONE BACKUPDIR= line and
#         every other line is unchanged, with its owner and mode; an existing
#         directory is saved as it is; /etc/sd-backup-roots widens the places (a
#         control first: refused without it) and is IGNORED when others may write it.
#
# NOT COVERED: BACKUP.ACCOUNT / RESTORE.ACCOUNT end to end (needs a throwaway
# account and no other session), Solo.
#
# PREREQUISITE: the full product installed by installsdcore.sh from the CURRENT main
# (run the installer first, as the owner, no sudo; it asks questions).  This script
# does not install and does not uninstall.
#
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-bakdir-install.sh
#
# ***NEEDS sudo.***  Run it from the owner's login (SUDO_USER must name a person, not root).
# It CHANGES REAL STATE and puts it back: /etc/sd.conf (backed up, restored byte for byte),
# /etc/sd-backup-roots (backed up if present, otherwise removed), and the scratch
# directories /var/backups/zzwitness, /var/tmp/zzwitness-existing and
# /var/tmp/zzwitness-root, which it removes.  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.  The log is /var/tmp/witness-bakdir-install-<time>.log, handed back
# to the owner.
#
# AN INSTRUMENT SHOWS WHAT IT DID: every sd session prints its input lines and its
# output; a session that prints nothing FAILS (the null case); a PASS needs the success
# wording AND the on-disk state, and a refusal row also needs the success wording to be
# absent.
#
set -u

SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
CONF=/etc/sd.conf
ROOTS=/etc/sd-backup-roots
ELEVATE=/usr/local/sbin/sd-elevate
BAKTOP=/var/backups/zzwitness
EXIST=/var/tmp/zzwitness-existing
ROOTDIR=/var/tmp/zzwitness-root
PASS=0
FAIL=0
STAMP=$(date +%Y%m%dT%H%M%S)
LOG=/var/tmp/witness-bakdir-install-$STAMP.log
WORK=""                      # made after the preconditions, so a refusal leaves nothing behind
CONF_SAVE=""
ROOTS_SAVE=""
HAD_ROOTS=0
STARTED=0

say() { printf '%s\n' "$*"; }
strip() { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g'; }
pass() { PASS=$((PASS+1)); say "  PASS  $1"; }
fail() { FAIL=$((FAIL+1)); say "  FAIL  $1"; }
need() { say "CANNOT RUN: $1"; exit 2; }

# expect_has "name" "$OUT" "wording"   - PASS only when the wording is in the output
expect_has()   { if printf '%s' "$2" | grep -q -F -- "$3"; then pass "$1"; else fail "$1 - wanted: $3"; fi; }
# expect_lacks "name" "$OUT" "wording" - PASS only when it is not
expect_lacks() { if printf '%s' "$2" | grep -q -F -- "$3"; then fail "$1 - must not contain: $3"; else pass "$1"; fi; }
# expect_eq "name" "got" "want"
expect_eq()    { if [ "$2" = "$3" ]; then pass "$1 ($2)"; else fail "$1 - got '$2', wanted '$3'"; fi; }

# sdsys SESSION_TITLE line... - one piped sd session as the administrator, ending in OFF
sdsys() {
  local title=$1; shift
  local body line out
  say "  --- sd session as sdsys: $title ---" >&2
  body=$'\n''TERM 200,9999'
  for line in "$@"; do say "      > $line" >&2; body="$body"$'\n'"$line"; done
  body="$body"$'\n''OFF'$'\n'
  out=$(cd "$SDSYS" && printf '%s' "$body" | timeout 60 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" 2>&1 | strip)
  printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
  if [ -z "$out" ]; then say "      (the session printed NOTHING - the null case)" >&2; fi
  printf '%s' "$out"
}

cleanup() {
  [ "$STARTED" -eq 1 ] || { rm -rf -- "$WORK"; return; }
  say ""
  say "== putting state back =="
  if [ -f "$CONF_SAVE" ]; then
    cp -p -- "$CONF_SAVE" "$CONF" && say "  restored $CONF"
    if cmp -s -- "$CONF_SAVE" "$CONF"; then say "  $CONF reads back identical to the backup"; else say "  *** $CONF DIFFERS from the backup: $CONF_SAVE kept"; WORK_KEEP=1; fi
  fi
  if [ "$HAD_ROOTS" -eq 1 ]; then cp -p -- "$ROOTS_SAVE" "$ROOTS" && say "  restored $ROOTS"; else rm -f -- "$ROOTS" && say "  removed $ROOTS (it was not there before)"; fi
  rm -rf -- "$BAKTOP" "$EXIST" "$ROOTDIR"
  say "  removed $BAKTOP $EXIST $ROOTDIR"
  [ "${WORK_KEEP:-0}" -eq 1 ] || rm -rf -- "$WORK"
  [ -f "$LOG" ] && chown "${SUDO_USER:-root}" "$LOG" 2>/dev/null
}

# ------------------------------------------------------------------ preconditions
if [ "${1:-}" != "--logged" ]; then
  [ "$(id -u)" -eq 0 ] || need "run it with sudo: sudo bash $SELF"
  [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ] || need "SUDO_USER must name a person (run it with sudo from the owner's login)"
  exec bash -c 'bash "$0" --logged 2>&1 | tee "$1"; exit ${PIPESTATUS[0]}' "$SELF" "$LOG"
fi
[ "$(id -u)" -eq 0 ] || need "not root"

say "witness-bakdir-install.sh  $STAMP"
say "  script  : $SELF"
say "  sd      : $SD"
say "  user    : ${SUDO_USER:-?} (sudo)   log: $LOG"
[ -x "$SD" ]       || need "$SD is not installed - run installsdcore.sh first"
[ -f "$CONF" ]     || need "$CONF is missing"
[ -x "$ELEVATE" ]  || need "$ELEVATE is not installed"
id sdsys >/dev/null 2>&1 || need "no sdsys user"
for d in "$BAKTOP" "$EXIST" "$ROOTDIR"; do [ ! -e "$d" ] || need "$d exists already (a scratch path of this script); remove it"; done
say "  version : $(timeout 20 "$SD" --version 2>&1 | head -1)"

WORK=$(mktemp -d /var/tmp/witness-bakdir-work.XXXXXX) || need "cannot make a work directory in /var/tmp"
CONF_SAVE=$WORK/sd.conf.saved
ROOTS_SAVE=$WORK/sd-backup-roots.saved
cp -p -- "$CONF" "$CONF_SAVE"
if [ -e "$ROOTS" ]; then cp -p -- "$ROOTS" "$ROOTS_SAVE"; HAD_ROOTS=1; fi
STARTED=1
trap cleanup EXIT
say "  backed up $CONF (sha256 $(sha256sum "$CONF" | cut -c1-16)...)  roots file present: $HAD_ROOTS"
CONF_META_BEFORE=$(stat -c '%U:%G %a' -- "$CONF")
say "  $CONF is $CONF_META_BEFORE; BACKUPDIR lines before: $(grep -c -E '^BACKUPDIR=' "$CONF")"

# ------------------------------------------------------------------ S.54 command names
say ""
say "== S.54: the command names =="
if [ -L /usr/local/bin/sd ]; then expect_eq "/usr/local/bin/sd is a link to the installed sd" "$(readlink -f /usr/local/bin/sd)" "$(readlink -f "$SD")"; else fail "/usr/local/bin/sd is not a link"; fi
if [ ! -e /usr/local/bin/sd-full ] && [ ! -L /usr/local/bin/sd-full ]; then pass "no /usr/local/bin/sd-full (dropped 1 Oct)"; else fail "/usr/local/bin/sd-full exists"; fi
AC=$(cd "$(dirname "$SELF")" && sudo -u "$SUDO_USER" python3 ./assert-current.py 2>&1; echo "rc=$?")
printf '%s\n' "$AC" | sed -e 's/^/      | /'
case "$(printf '%s' "$AC" | tail -1)" in rc=0) pass "assert-current: the install is current";; *) fail "assert-current did not exit 0 (stale, or cannot tell): the install may not be this commit";; esac

# ------------------------------------------------------------------ S.53
say ""
say "== S.53: SET.BACKUP.DIRECTORY on a real install =="
BEFORE_N=$(grep -c -E '^BACKUPDIR=' "$CONF")

OUT=$(sdsys "no argument" "SET.BACKUP.DIRECTORY")
if [ "$BEFORE_N" -eq 0 ]; then expect_has "B1 no argument, none saved" "$OUT" "No backup directory is set."; else expect_has "B1 no argument shows the saved directory" "$OUT" "The backup directory is"; fi

SUM0=$(sha256sum "$CONF" | cut -d' ' -f1)
OUT=$(sdsys "a relative path" "SET.BACKUP.DIRECTORY zzwitness/relative")
expect_has   "B2 relative path refused (13046)" "$OUT" "Give the full path of the backup directory"
expect_lacks "B2 ...and not saved" "$OUT" "Backup directory is now"
expect_eq    "B2 sd.conf unchanged" "$(sha256sum "$CONF" | cut -d' ' -f1)" "$SUM0"

OUT=$(sdsys "a place root may not make in" "SET.BACKUP.DIRECTORY /etc/zz-witness-bak")
expect_has   "B3 refused, the places named" "$OUT" "is not below a place where root may make a backup directory"
expect_lacks "B3 ...and not saved" "$OUT" "Backup directory is now"
if [ ! -e /etc/zz-witness-bak ]; then pass "B3 nothing was made at /etc/zz-witness-bak"; else fail "B3 /etc/zz-witness-bak exists"; rm -rf /etc/zz-witness-bak; fi
expect_eq    "B3 sd.conf unchanged" "$(sha256sum "$CONF" | cut -d' ' -f1)" "$SUM0"

OUT=$(sdsys "root makes a directory below /var/backups" "SET.BACKUP.DIRECTORY $BAKTOP/a/b" "SET.BACKUP.DIRECTORY")
expect_has "B4 success wording" "$OUT" "Backup directory is now $BAKTOP/a/b"
expect_lacks "B4 no failure wording" "$OUT" "Cannot create the backup directory"
SDG=$(id -gn sdsys)
expect_eq "B4 the directory is sdsys's, mode 0700" "$(stat -c '%U:%G %a' -- "$BAKTOP/a/b" 2>/dev/null)" "sdsys:$SDG 700"
expect_eq "B4 the directory on the way ($BAKTOP/a) is root's, 0755" "$(stat -c '%U:%G %a' -- "$BAKTOP/a" 2>/dev/null)" "root:root 755"
expect_eq "B4 no probe file left behind" "$(ls -A -- "$BAKTOP/a/b" 2>/dev/null | wc -l)" "0"
expect_eq "B4 exactly one BACKUPDIR line, and it is ours" "$(grep -E '^BACKUPDIR=' "$CONF")" "BACKUPDIR=$BAKTOP/a/b"
expect_eq "B4 sd.conf owner and mode unchanged" "$(stat -c '%U:%G %a' -- "$CONF")" "$CONF_META_BEFORE"
OTHERS_BEFORE=$(grep -v -E '^BACKUPDIR=' "$CONF_SAVE" | sha256sum | cut -d' ' -f1)
OTHERS_AFTER=$(grep -v -E '^BACKUPDIR=' "$CONF" | sha256sum | cut -d' ' -f1)
expect_eq "B4 every other sd.conf line is unchanged" "$OTHERS_AFTER" "$OTHERS_BEFORE"
expect_has "B5 no argument now shows the saved directory" "$OUT" "The backup directory is $BAKTOP/a/b"

mkdir -m 0700 "$EXIST" && chown sdsys:"$SDG" "$EXIST"
EXIST_META=$(stat -c '%U:%G %a' -- "$EXIST")
OUT=$(sdsys "an existing directory" "SET.BACKUP.DIRECTORY $EXIST")
expect_has "B6 success wording" "$OUT" "Backup directory is now $EXIST"
expect_eq "B6 the directory is used as it is (owner and mode)" "$(stat -c '%U:%G %a' -- "$EXIST")" "$EXIST_META"
expect_eq "B6 saved" "$(grep -E '^BACKUPDIR=' "$CONF")" "BACKUPDIR=$EXIST"

# /etc/sd-backup-roots: a control first, then the file, then a file others may write
mkdir -m 0755 "$ROOTDIR"; chown root:root "$ROOTDIR"
rm -f -- "$ROOTS"
OUT=$(sdsys "CONTROL: below a root-owned directory, no roots file" "SET.BACKUP.DIRECTORY $ROOTDIR/x")
expect_has   "B7a control refused without the roots file" "$OUT" "is not below a place where root may make a backup directory"
expect_lacks "B7a ...and not saved" "$OUT" "Backup directory is now"
[ ! -e "$ROOTDIR/x" ] && pass "B7a nothing made" || fail "B7a $ROOTDIR/x exists"

printf '# witness\n%s\n' "$ROOTDIR" > "$ROOTS"; chown root:root "$ROOTS"; chmod 0644 "$ROOTS"
OUT=$(sdsys "the same, with $ROOTS listing $ROOTDIR (root:root 0644)" "SET.BACKUP.DIRECTORY $ROOTDIR/x")
expect_has "B7b success wording" "$OUT" "Backup directory is now $ROOTDIR/x"
expect_eq  "B7b made for sdsys, mode 0700" "$(stat -c '%U:%G %a' -- "$ROOTDIR/x" 2>/dev/null)" "sdsys:$SDG 700"

chmod 0666 "$ROOTS"
OUT=$(sdsys "the roots file writable by others (0666): must be ignored" "SET.BACKUP.DIRECTORY $ROOTDIR/y")
expect_lacks "B7c not saved" "$OUT" "Backup directory is now"
[ ! -e "$ROOTDIR/y" ] && pass "B7c nothing made" || fail "B7c $ROOTDIR/y exists"
chmod 0644 "$ROOTS"

say ""
say "== result: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
