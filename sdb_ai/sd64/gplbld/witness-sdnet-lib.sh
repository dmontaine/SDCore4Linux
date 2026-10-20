#!/usr/bin/env bash
#
# witness-sdnet-lib.sh - the helpers that the witness-sdnet-*.sh scripts share.  SOURCED, NEVER RUN.  (19 Oct 26, the S.65 finish.)
#
#   . "$(dirname "$0")/witness-sdnet-lib.sh"
#
# What it holds: say / pass / fail / need, the three expect_* comparisons, the sessions (one piped sd session as SDSYS through the loginuid bridge, one as an ordinary user),
# the Linux group readers, the audit-trail offset and reader, the install's commit stamp, the log re-exec (every byte a script prints also goes to a log), and a
# selftest of its own comparisons (wl_selftest).  It does not elevate anything itself: a script that sources it is started with sudo and says so.
# Changed 19 Oct 26 (finish 2, the verifier's findings): wl_audit_offset prints ONE number and counts the physical lines wl_audit_since starts from; wl_mkdir_new and wl_state_dir (nothing in the
# shared /var/tmp is made "if missing" by a command that follows a link); the log is made by mktemp.
#
# AN INSTRUMENT SHOWS WHAT IT DID.  Every session prints the lines it was given and the text it got back; a session that prints NOTHING says so and the row that needed
# it FAILS (the null case); a PASS needs the success wording AND the state (the group, the file, the audit line) and a refusal row needs the success wording to be absent.
# The script's exit status is 0 only when every row passed and at least one row ran.
#
WL_PASS=0
WL_FAIL=0
WL_SD=${WL_SD:-/usr/local/sdsys/bin/sd}
WL_SDSYS=${WL_SDSYS:-/usr/local/sdsys}
WL_AUDIT=${WL_AUDIT:-/usr/local/sdsys/audit}
WL_ELEVATE=${WL_ELEVATE:-/usr/local/sbin/sd-elevate}
WL_TLS_PEM=${WL_TLS_PEM:-/etc/sd-tls/api.pem}
WL_TMP=${WL_TMP:-/var/tmp}
# The six WL_* paths above may be moved by the environment ONLY so that test-witness-sdnet-units.py can run a script against a model of the install; a real run leaves them alone.

say() { printf '%s\n' "$*"; }
strip() { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g'; }
pass() { WL_PASS=$((WL_PASS+1)); say "  PASS  $1"; }
fail() { WL_FAIL=$((WL_FAIL+1)); say "  FAIL  $1"; }
need() { say "CANNOT RUN: $1"; exit 2; }

# expect_has "name" "$OUT" "wording"    PASS only when the wording is in the text (fixed string).  An EMPTY text is a failure, not a "no match".
expect_has() {
  if [ -z "$3" ]; then fail "$1 - the wording to look for is EMPTY (a message that could not be read? an empty wording is in every text)"; return; fi
  if [ -z "$2" ]; then fail "$1 - the text to look in is EMPTY (the null case): wanted: $3"; return; fi
  if grep -q -F -- "$3" <<<"$2"; then pass "$1"; else fail "$1 - wanted: $3"; fi     # a here-string, not `printf | grep -q`: grep -q leaves at the first match and the printf then died with "Broken pipe" noise in the log
}
# expect_lacks "name" "$OUT" "wording"  PASS only when the text is not empty and the wording is not in it
expect_lacks() {
  if [ -z "$3" ]; then fail "$1 - the wording that must be absent is EMPTY (a message that could not be read? an empty wording is in every text)"; return; fi
  if [ -z "$2" ]; then fail "$1 - the text to look in is EMPTY (the null case), so its absence proves nothing: $3"; return; fi
  if grep -q -F -- "$3" <<<"$2"; then fail "$1 - must not contain: $3"; else pass "$1"; fi
}
# expect_re "name" "$OUT" "regex"       PASS only when the (extended, case sensitive) regex matches a line of a text that is not empty
expect_re() {
  if [ -z "$3" ]; then fail "$1 - the pattern is EMPTY (it matches every line)"; return; fi
  if [ -z "$2" ]; then fail "$1 - the text to look in is EMPTY (the null case): wanted /$3/"; return; fi
  if grep -q -a -E -- "$3" <<<"$2"; then pass "$1"; else fail "$1 - wanted /$3/"; fi
}
# expect_eq "name" "got" "want"
expect_eq() { if [ "$2" = "$3" ]; then pass "$1 ($2)"; else fail "$1 - got '$2', wanted '$3'"; fi; }

wl_summary() {
  say ""
  say "== $WL_PASS passed, $WL_FAIL failed =="
  if [ "$WL_FAIL" -gt 0 ]; then return 1; fi
  if [ "$WL_PASS" -eq 0 ]; then say "  (no row ran: that is not a pass)"; return 2; fi
  return 0
}

# THE SCRIPTS RUN AS ROOT AND KEEP THEIR FILES IN /var/tmp, WHICH EVERY USER CAN WRITE INTO, UNDER NAMES ANYONE CAN WORK OUT (a time stamp to the second, a fixed word).  So nothing is made
# there "if it is missing" by a command that follows a link or accepts a directory somebody else made first (a planted link at $WL_TMP/witness-sdnet-two-machines.pw would have had its
# target overwritten and chowned to the owner; a directory made beforehand by another user would have been written into as root).  (Verifier finding of 19 Oct 2026.)
# wl_mkdir_new PATH MODE   make PATH, which must not exist (mkdir refuses an existing name, a link included), with exactly MODE; CANNOT RUN when it cannot.
wl_mkdir_new() { mkdir -m "$2" -- "$1" 2>/dev/null || need "cannot make $1 (it is there already, or its directory is not writable): remove it first"; }
# wl_state_dir PATH   a directory a script keeps its state in BETWEEN runs: made 0755 when it is not there; when it is, it must be a real directory (not a link) that root owns and that
# nobody else can write into; CANNOT RUN otherwise.
wl_state_dir() {
  if [ -L "$1" ]; then need "$1 is a symbolic link: this script will not use it"; fi
  if [ -e "$1" ]; then
    [ -d "$1" ] && [ "$(stat -c '%u' -- "$1")" = "$EUID" ] && [ "$(( 0$(stat -c '%a' -- "$1") & 022 ))" = 0 ] \
      || need "$1 exists and is not a directory that only the user running this script (uid $EUID, root on a real run) can write into: remove it, or leave it if it is yours from an earlier run"
    return 0
  fi
  mkdir -m 755 -- "$1" 2>/dev/null || need "cannot make $1"
}

# wl_logged SELF LOGPREFIX ARGS...   Called first by a script that needs sudo: checks root and SUDO_USER, then re-runs itself with every byte also going to the log.
# A script calls it as   wl_logged "$SELF" witness-sdnet-x "$@"   and then continues as the logged copy when "--logged" is its first argument.
# The log is made by mktemp (a new file, mode 0600, a random tail: witness-sdnet-x-<time>.<6 characters>.log) and handed to the owner when the run ends.
wl_logged() {
  local self=$1 prefix=$2; shift 2
  if [ "${1:-}" != "--logged" ]; then
    [ "$(id -u)" -eq 0 ] || need "run it with sudo: sudo bash $self"
    [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ] || need "SUDO_USER must name a person (run it with sudo from the owner's login, not from a root shell)"
    WL_LOG=$(mktemp "$WL_TMP/$prefix-$(date +%Y%m%dT%H%M%S).XXXXXX.log") || need "cannot make a log file in $WL_TMP"
    exec bash -c 'bash "$0" --logged "${@:2}" 2>&1 | tee "$1"; rc=${PIPESTATUS[0]}; chown "${SUDO_USER:-root}" "$1" 2>/dev/null; exit $rc' "$self" "$WL_LOG" "$@"
  fi
  [ "$(id -u)" -eq 0 ] || need "not root"
}

# wl_commit_stamp   prints the commit and the date the install says it is.
wl_commit_stamp() {
  local f=$WL_SDSYS/.sdcore-install
  [ -r "$f" ] || { say "(no $f)"; return 1; }
  grep -E '^(commit|branch|installed)=' "$f" | tr '\n' ' '
}

# WL_SECRETS is an array of strings (passwords) that are never printed: every echoed input line and every text a session returns has each of them replaced by ********.
WL_SECRETS=()
wl_mask() {
  local s esc txt
  txt=$(cat)
  for s in "${WL_SECRETS[@]+"${WL_SECRETS[@]}"}"; do
    [ -n "$s" ] || continue
    esc=$(printf '%s' "$s" | sed -e 's/[][\/.*^$]/\\&/g')
    txt=$(printf '%s' "$txt" | sed -e "s/$esc/********/g")
  done
  printf '%s' "$txt"
}

# wl_sd_admin TITLE LINE...    one piped sd session as SDSYS (the loginuid bridge), ending in OFF.  The lines and the text are printed to stderr as they happen; the text is the
# function's output.  A session that printed nothing says so (the null case).
wl_sd_admin() {
  local title=$1; shift
  local body line out
  say "  --- sd session as sdsys: $title ---" >&2
  body=$'\n''TERM 200,9999'
  for line in "$@"; do printf '%s\n' "      > $line" | wl_mask >&2; echo >&2; body="$body"$'\n'"$line"; done
  body="$body"$'\n''OFF'$'\n'
  out=$(cd "$WL_SDSYS" && printf '%s' "$body" | timeout 120 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$WL_SD" 2>&1 | strip | wl_mask)
  printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
  if [ -z "$out" ]; then say "      (the session printed NOTHING - the null case)" >&2; fi
  printf '%s' "$out"
}

# wl_sd_user USER TITLE LINE...   one piped sd session as the ordinary Linux user USER, in the root of the file system (so that it enters the user's own account), ending in OFF.
wl_sd_user() {
  local who=$1 title=$2; shift 2
  local body line out
  say "  --- sd session as $who: $title ---" >&2
  body=$'\n''TERM 200,9999'
  for line in "$@"; do printf '%s\n' "      > $line" | wl_mask >&2; echo >&2; body="$body"$'\n'"$line"; done
  body="$body"$'\n''OFF'$'\n'
  out=$(cd / && printf '%s' "$body" | timeout 180 sudo -u "$who" "$WL_SD" 2>&1 | strip | wl_mask)
  printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
  if [ -z "$out" ]; then say "      (the session printed NOTHING - the null case)" >&2; fi
  printf '%s' "$out"
}

# wl_members GROUP      the member list of a Linux group, from the group file (supplementary members only), comma separated; empty when there are none or no such group.
wl_members() { getent group "$1" 2>/dev/null | cut -d: -f4; }
# wl_group_exists GROUP
wl_group_exists() { getent group "$1" >/dev/null 2>&1; }
# wl_in_group USER GROUP   true when USER is a supplementary member of GROUP.
wl_in_group() { printf ',%s,' "$(wl_members "$2")" | grep -q -F ",$1,"; }
# wl_state USER   "sdfiles=<0|1> sdfileswrite=<0|1>"
wl_state() {
  local a=0 b=0
  wl_in_group "$1" sdfiles && a=1
  wl_in_group "$1" sdfileswrite && b=1
  printf 'sdfiles=%s sdfileswrite=%s' "$a" "$b"
}
# wl_set_state USER FILES WRITE    put USER in exactly the wanted state of the two groups, as root, with gpasswd (this script's own doing, not SD's), and say so.
wl_set_state() {
  local u=$1 f=$2 w=$3
  if [ "$f" = 1 ]; then wl_in_group "$u" sdfiles || gpasswd -a "$u" sdfiles >/dev/null; else wl_in_group "$u" sdfiles && gpasswd -d "$u" sdfiles >/dev/null; fi
  if [ "$w" = 1 ]; then wl_in_group "$u" sdfileswrite || gpasswd -a "$u" sdfileswrite >/dev/null; else wl_in_group "$u" sdfileswrite && gpasswd -d "$u" sdfileswrite >/dev/null; fi
  say "      (this script set $u to $(wl_state "$u") with gpasswd)" >&2
  return 0
}

# wl_audit_offset   the number of lines the audit trail has now (root reads it): ONE number, 0 for an empty or missing file.    wl_audit_since OFFSET   the lines added since.
# Both count PHYSICAL lines (wc -l and tail -n +N count newlines), so an offset taken here and used there always agree - it counted the non-empty lines before, which differ from the
# physical ones as soon as the trail holds a blank line, and `grep -c ... || echo 0` printed "0" twice for an empty file (grep prints 0 AND exits 1).
wl_audit_offset() { local n; n=$({ wc -l < "$WL_AUDIT"; } 2>/dev/null); printf '%s\n' "$(( ${n:-0} + 0 ))"; }
wl_audit_since() { tail -n +$(( $1 + 1 )) "$WL_AUDIT" 2>/dev/null; }

# wl_api_pids   the pids of the API server processes (sd -n -q) running now, one a line.   wl_api_left "BEFORE"   those of them that are not in BEFORE (a list of pids, one a line).
# 20 Oct 26.  A client that completes the TLS handshake and closes at once leaves its server process in a poll loop at 100% of a processor about half the time (S.71, measured on the VM),
# and BACKUP.ACCOUNT then refuses with "1 other session(s) are logged in", which showed in a witness only as an empty manifest.  These name the process instead.  READ-ONLY: nothing is ended
# here; a witness that ended the process would erase the evidence it exists to give.
wl_api_pids() { pgrep -x sd -a 2>/dev/null | grep -F -- ' -n -q' | awk '{print $1}' | sort -n; }
wl_api_left() { local p; for p in $(wl_api_pids); do printf '%s\n' "$1" | grep -q -x -F -- "$p" || printf '%s\n' "$p"; done; }

# wl_account_user ACCOUNT    the Linux user an SD account's register record names (field 3 is sdu_<user>); empty when the record is not a user account.
wl_account_user() {
  local g
  g=$(sed -n '3p' "$WL_SDSYS/accounts/$1" 2>/dev/null)
  case $g in sdu_*) printf '%s' "${g#sdu_}" ;; *) printf '' ;; esac
}

# wl_account_path ACCOUNT    the directory an SD account's register record names (field 1); empty when there is no such record.
wl_account_path() { sed -n '1p' "$WL_SDSYS/accounts/$1" 2>/dev/null; }

# wl_sed_esc TEXT   TEXT made safe to sit in the replacement half of a sed s/// command.
wl_sed_esc() { printf '%s' "$1" | sed -e 's/[&/\\]/\\&/g'; }
# wl_msg N [A1 [A2 [A3]]]   the text of message N as the INSTALL has it (first line of $WL_SDSYS/messages/N) with %1 %2 %3 replaced.  Empty when there is no such message,
# so a row that needs the text fails on the empty wording instead of passing on "".
wl_msg() {
  local f="$WL_SDSYS/messages/$1"
  [ -r "$f" ] || return 0
  sed -n '1p' "$f" | sed -e "s/%1/$(wl_sed_esc "${2:-}")/g" -e "s/%2/$(wl_sed_esc "${3:-}")/g" -e "s/%3/$(wl_sed_esc "${4:-}")/g" | tr -d '\n'
}
# wl_line_of OUT TEXT   the number of the first line of OUT that is exactly TEXT (trailing blanks aside), or 0.  TEXT goes in through the environment, not -v, so a backslash in it stays one.
wl_line_of() {
  local n
  n=$(printf '%s\n' "$1" | WL_LINE_T="$2" awk '{ s = $0; sub(/[ \t]+$/, "", s); if (s == ENVIRON["WL_LINE_T"]) { print NR; exit } }')
  printf '%s' "${n:-0}"
}
# wl_before NAME OUT FIRST SECOND   PASS only when both lines are in OUT and FIRST is above SECOND.
wl_before() {
  local a b
  a=$(wl_line_of "$2" "$3"); b=$(wl_line_of "$2" "$4")
  if [ "$a" -gt 0 ] && [ "$b" -gt "$a" ]; then pass "$1: '$3' (line $a) comes before '$4' (line $b)"; else fail "$1: wanted '$3' above '$4', got lines $a and $b (0 = not there)"; fi
}
# wl_newpw   a fresh password of the shape SD's rule accepts (capital, small letter, digit, symbol, 26 characters).  The caller adds it to WL_SECRETS at once.
wl_newpw() { printf 'Cr9-%sq4' "$(head -c 60 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20)"; }
# wl_zip_member ZIP MEMBER   the text of one member of a zip, on stdout; empty when it cannot be read.
wl_zip_member() {
  if command -v unzip >/dev/null 2>&1; then unzip -p "$1" "$2" 2>/dev/null
  else python3 -c 'import sys, zipfile; sys.stdout.write(zipfile.ZipFile(sys.argv[1]).read(sys.argv[2]).decode("utf-8", "replace"))' "$1" "$2" 2>/dev/null; fi
}
# wl_backup_routes ACCOUNT DIR   BACKUP.ACCOUNT of ACCOUNT into DIR (made here, open to every user, because the session runs as sdsys; DIR must be under /var/tmp/witness-sdnet-)
# and prints the route lines of its manifest on one line, such as  "[account x] route.files: 1 route.files.write: 0 ".  Empty when no archive or no manifest came out.
wl_backup_routes() {
  local acc=$1 d=$2 z
  case $d in "$WL_TMP"/witness-sdnet-*) ;; *) say "      (wl_backup_routes refuses $d: it must be under $WL_TMP/witness-sdnet-)" >&2; return 1 ;; esac
  rm -rf -- "$d"; wl_mkdir_new "$d" 777
  wl_sd_admin "backup.account $acc" "BACKUP.ACCOUNT $acc TO $d" >&2
  z=$(ls "$d"/*.zip 2>/dev/null | head -1)
  [ -n "$z" ] || return 0
  wl_zip_member "$z" manifest.txt | grep -a -E '^(\[account|route\.files)' | tr '\n' ' '
}

# wl_selftest   the comparisons of this file on texts whose answer is known.  No sudo, no sd.  Prints PASS/FAIL rows and returns wl_summary's status.
wl_selftest() {
  WL_PASS=0; WL_FAIL=0
  local saved_pass saved_fail t
  say "wl_selftest: the helpers on known texts (each is shown a text it must accept and one it must refuse; a helper that answers wrong prints SELFTEST-WRONG)"
  t=$'Account fred has files yes\nAccount fred has files-write no'
  # each case: the helper must answer as written; the wrapper turns the expected FAIL into a PASS of the helper
  chk() { local want=$1 label=$2; shift 2; local b_p=$WL_PASS b_f=$WL_FAIL; "$@" >/dev/null; if [ "$want" = pass ] && [ $WL_PASS -gt $b_p ]; then :; elif [ "$want" = fail ] && [ $WL_FAIL -gt $b_f ]; then :; else echo "SELFTEST-WRONG: $label"; SELF_BAD=1; fi; WL_PASS=$b_p; WL_FAIL=$b_f; }
  SELF_BAD=0
  chk fail "expect_has with an EMPTY wording is a failure"   expect_has x "$t" ""
  chk fail "expect_lacks with an EMPTY wording is a failure" expect_lacks x "$t" ""
  chk fail "expect_re with an EMPTY pattern is a failure"    expect_re x "$t" ""
  chk pass "expect_has finds a line"                         expect_has x "$t" "has files yes"
  chk fail "expect_has misses a line that is not there"      expect_has x "$t" "has files no"
  chk fail "expect_has on EMPTY text is a failure"           expect_has x "" "anything"
  chk pass "expect_lacks passes when the wording is absent"  expect_lacks x "$t" "FILES"
  chk fail "expect_lacks fails when it is present"           expect_lacks x "$t" "files-write no"
  chk fail "expect_lacks on EMPTY text is a failure"         expect_lacks x "" "FILES"
  chk pass "expect_re matches"                               expect_re x "$t" '^Account [a-z]+ has files (yes|no)$'
  chk fail "expect_re does not match files-write"            expect_re x "$t" '^Account [a-z]+ has files (maybe)$'
  chk pass "expect_eq equal"                                 expect_eq x "a" "a"
  chk fail "expect_eq unequal"                               expect_eq x "a" "b"
  chk fail "expect_eq unequal only after the third character" expect_eq x "abcd" "abce"
  local t2=$'A line\nB line\nC line'
  chk pass "wl_before: the first above the second"            wl_before x "$t2" "A line" "B line"
  chk fail "wl_before: the second above the first"            wl_before x "$t2" "B line" "A line"
  chk fail "wl_before: a line that is not there"              wl_before x "$t2" "A line" "Z line"
  chk fail "wl_before: on EMPTY text"                         wl_before x "" "A line" "B line"
  [ "$(wl_line_of "$t2" "B line")" = 2 ] && [ "$(wl_line_of "$t2" "B")" = 0 ] && [ "$(wl_line_of "" "B line")" = 0 ] || { echo "SELFTEST-WRONG: wl_line_of"; SELF_BAD=1; }
  [[ $(wl_newpw) =~ ^Cr9-[A-Za-z0-9]{20}q4$ ]] && [ "$(wl_newpw)" != "$(wl_newpw)" ] || { echo "SELFTEST-WRONG: wl_newpw"; SELF_BAD=1; }
  # wl_summary's three answers: 0 only when a row ran and none failed, 1 when one failed, 2 when no row ran (that is not a pass)
  ( WL_PASS=2; WL_FAIL=0; wl_summary >/dev/null; [ $? -eq 0 ] ) && ( WL_PASS=2; WL_FAIL=1; wl_summary >/dev/null; [ $? -eq 1 ] ) && ( WL_PASS=0; WL_FAIL=0; wl_summary >/dev/null; [ $? -eq 2 ] ) \
    || { echo "SELFTEST-WRONG: wl_summary"; SELF_BAD=1; }
  local saved_sdsys=$WL_SDSYS tmp
  tmp=$(mktemp -d /tmp/wl-selftest.XXXXXX) && mkdir -p "$tmp/messages" "$tmp/accounts" || { echo "SELFTEST-WRONG: no scratch directory"; SELF_BAD=1; tmp=; }
  if [ -n "$tmp" ]; then
    printf 'Account %%1 has files %%2\nsecond line\n' > "$tmp/messages/11482"
    printf '/home/sd/user_accounts/ann\nx\nsdu_ann\n' > "$tmp/accounts/ann"
    WL_SDSYS=$tmp
    [ "$(wl_msg 11482 ann yes)" = "Account ann has files yes" ] || { echo "SELFTEST-WRONG: wl_msg"; SELF_BAD=1; }
    [ "$(wl_msg 11482 'a/b&c' no)" = "Account a/b&c has files no" ] || { echo "SELFTEST-WRONG: wl_msg with a slash and an ampersand"; SELF_BAD=1; }
    [ -z "$(wl_msg 99999 a b)" ] || { echo "SELFTEST-WRONG: wl_msg of a message that is not there is not empty"; SELF_BAD=1; }
    [ "$(wl_account_path ann)" = "/home/sd/user_accounts/ann" ] && [ "$(wl_account_user ann)" = ann ] && [ -z "$(wl_account_path nobody)" ] \
      || { echo "SELFTEST-WRONG: wl_account_path / wl_account_user"; SELF_BAD=1; }
    WL_SDSYS=$saved_sdsys
    # wl_audit_offset: ONE number whatever the file holds (an empty file printed two lines "0" before), counted in the physical lines wl_audit_since starts from
    local saved_audit=$WL_AUDIT
    WL_AUDIT=$tmp/audit
    : > "$WL_AUDIT"
    [ "$(wl_audit_offset)" = 0 ] && [ "$(wl_audit_offset | wc -l)" = 1 ] || { echo "SELFTEST-WRONG: wl_audit_offset of an EMPTY file is not the one line 0"; SELF_BAD=1; }
    printf 'one\n\ntwo\n' > "$WL_AUDIT"
    [ "$(wl_audit_offset)" = 3 ] && [ "$(wl_audit_since 2)" = "two" ] && [ -z "$(wl_audit_since 3)" ] && [ "$(wl_audit_since 0 | wc -l)" = 3 ] \
      || { echo "SELFTEST-WRONG: wl_audit_offset / wl_audit_since disagree about a trail with a blank line"; SELF_BAD=1; }
    WL_AUDIT=$tmp/no-such-file
    [ "$(wl_audit_offset)" = 0 ] && [ "$(wl_audit_offset | wc -l)" = 1 ] || { echo "SELFTEST-WRONG: wl_audit_offset of a MISSING file is not the one line 0"; SELF_BAD=1; }
    WL_AUDIT=$saved_audit
    # wl_mkdir_new / wl_state_dir (a directory somebody else made first, a link, a file): each is run in a subshell because a refusal is `need`, which exits
    ( wl_mkdir_new "$tmp/new" 750 ) >/dev/null 2>&1 && [ "$(stat -c %a "$tmp/new")" = 750 ] || { echo "SELFTEST-WRONG: wl_mkdir_new did not make a new directory with the mode asked"; SELF_BAD=1; }
    ( wl_mkdir_new "$tmp/new" 750 ) >/dev/null 2>&1 && { echo "SELFTEST-WRONG: wl_mkdir_new accepted a name that is there"; SELF_BAD=1; }
    ln -s "$tmp/new" "$tmp/lnk"
    ( wl_mkdir_new "$tmp/lnk" 750 ) >/dev/null 2>&1 && { echo "SELFTEST-WRONG: wl_mkdir_new accepted a link"; SELF_BAD=1; }
    ( wl_state_dir "$tmp/st" ) >/dev/null 2>&1 && [ "$(stat -c %a "$tmp/st")" = 755 ] || { echo "SELFTEST-WRONG: wl_state_dir did not make a missing directory 755"; SELF_BAD=1; }
    ( wl_state_dir "$tmp/st" ) >/dev/null 2>&1 || { echo "SELFTEST-WRONG: wl_state_dir refused its own directory"; SELF_BAD=1; }
    ln -s "$tmp/st" "$tmp/stlnk"
    ( wl_state_dir "$tmp/stlnk" ) >/dev/null 2>&1 && { echo "SELFTEST-WRONG: wl_state_dir accepted a link"; SELF_BAD=1; }
    chmod 775 "$tmp/st"
    ( wl_state_dir "$tmp/st" ) >/dev/null 2>&1 && { echo "SELFTEST-WRONG: wl_state_dir accepted a directory that the group can write into"; SELF_BAD=1; }
    chmod 755 "$tmp/st"
    : > "$tmp/afile"
    ( wl_state_dir "$tmp/afile" ) >/dev/null 2>&1 && { echo "SELFTEST-WRONG: wl_state_dir accepted a file"; SELF_BAD=1; }
    rm -rf -- "$tmp"
  fi
  # wl_in_group on a canned group: use a private function that stands in for the group file
  wl_members() { case $1 in sdfiles) printf 'ann,bob' ;; sdfileswrite) printf 'bob' ;; esac; }
  wl_in_group ann sdfiles && wl_in_group bob sdfiles && ! wl_in_group cy sdfiles && ! wl_in_group an sdfiles && ! wl_in_group ann sdfileswrite && wl_in_group bob sdfileswrite \
    || { echo "SELFTEST-WRONG: wl_in_group"; SELF_BAD=1; }
  [ "$(wl_state bob)" = "sdfiles=1 sdfileswrite=1" ] && [ "$(wl_state ann)" = "sdfiles=1 sdfileswrite=0" ] && [ "$(wl_state cy)" = "sdfiles=0 sdfileswrite=0" ] \
    || { echo "SELFTEST-WRONG: wl_state"; SELF_BAD=1; }
  local old_secrets=("${WL_SECRETS[@]+"${WL_SECRETS[@]}"}")
  WL_SECRETS=('pa/ss.1' 'Zz9x')
  [ "$(printf 'user pa/ss.1 and Zz9x, and pa/ss.1 again, not paXss.1' | wl_mask)" = "user ******** and ********, and ******** again, not paXss.1" ] || { echo "SELFTEST-WRONG: wl_mask"; SELF_BAD=1; }
  WL_SECRETS=()
  [ "$(printf 'nothing to hide' | wl_mask)" = "nothing to hide" ] || { echo "SELFTEST-WRONG: wl_mask with no secret"; SELF_BAD=1; }
  WL_SECRETS=("${old_secrets[@]+"${old_secrets[@]}"}")
  if [ "$SELF_BAD" -eq 0 ]; then WL_PASS=1; WL_FAIL=0; say "  PASS  every helper answered as written on the known texts"; else WL_PASS=0; WL_FAIL=1; say "  FAIL  a helper answered wrong (see SELFTEST-WRONG above)"; fi
  wl_summary
}
