#!/usr/bin/env bash
#
# witness-sdnet-gaps.sh - the SDNet proofs that no earlier real-install run made.  (K6c, 19 Oct 2026; the S.65 finish.)
#
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-gaps.sh [--account NAME] [--port N]
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-gaps.sh --selftest        (no sudo, no sd: the helpers on known texts)
#
# ***NEEDS sudo.***  Run it from the owner's login (SUDO_USER must name a person, not root).  It CHANGES REAL STATE and puts it back:
#   * MAKES an SD account NAME (default zzwgap) with its Linux user, takes its write group on and off, BACKS IT UP twice, DELETES it and RESTORES it from each backup,
#     and at the end DELETES it again (DELETE.ACCOUNT, then userdel -r and its home).  It refuses to start when anything it would make already exists.
#   * writes its backups under /var/tmp/witness-sdnet-gaps-<time>.d and leaves them there for the owner to look at.
# It does not install and does not uninstall.  (The installer and the uninstaller are witness-sdnet-groups.sh.)
#
# WHAT IT PROVES, and why nothing earlier did (the S.65 row, K6c, 19 Oct 2026):
#   T   TLS 1.2 is REFUSED by the API port and TLS 1.3 completes (openssl s_client).  The docs say TLS 1.3 only; the unit tests read the source and the relay test uses
#       a local server, so the real listener had not been asked.
#   W   the wire probe as a FILES-ONLY login (sdfiles, not sdapi) sends the requests the allow table refuses whether or not the write group is on - 20 call, 21 execute,
#       22 respond, 23 end command, 54 transaction, 61 open sequential file, and a SECOND 3 (SDLogto) - and every one is refused with message 11480 and the audit line
#       "api refused request=N route=sdfiles write=<off|on>"; a read still works.  Run twice: files-on alone, then files-write-on.  (Request 29 has no function in the client
#       library: gplbld/sandbox-req29.py sends it on the wire, and this script does not.)
#   A   verify-auditwords.py over the REAL audit file, judged from the moment this script started: every event word the run wrote is lower case.
#   R   BACKUP.ACCOUNT then DELETE.ACCOUNT then RESTORE.ACCOUNT of an account with the write group off and then on: the manifest says route.files.write 0 / 1, and the
#       restored Linux user is in exactly the groups the manifest said (sdfiles=1 sdfileswrite=0 / sdfiles=1 sdfileswrite=1).  The 18 Oct restore run (w20) was made before the
#       manifest key existed.
#   Z   put back: nothing of the account is left.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-gaps-<time>.log, handed back to the owner.
#
set -u
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
HERE=$(dirname "$SELF")
# shellcheck source=witness-sdnet-lib.sh
. "$HERE/witness-sdnet-lib.sh" || { echo "CANNOT RUN: no witness-sdnet-lib.sh beside $SELF"; exit 2; }

if [ "${1:-}" = "--selftest" ]; then wl_selftest; exit $?; fi
wl_logged "$SELF" witness-sdnet-gaps "$@"
shift                                   # the "--logged" the re-exec added

ACC=zzwgap; PORT=4247
while [ $# -gt 0 ]; do
  case $1 in
    --account) [ $# -ge 2 ] || need "--account needs a name"; ACC=$2; shift 2 ;;
    --port)    [ $# -ge 2 ] || need "--port needs a number"; PORT=$2; shift 2 ;;
    *) need "unknown argument '$1'" ;;
  esac
done
HOST=127.0.0.1
case $ACC in *[!a-z0-9]*|'') need "--account must be lower case letters and digits" ;; esac
case $PORT in *[!0-9]*|'') need "--port must be a number" ;; esac

STAMP=$(date +%Y%m%dT%H%M%S)
START_TS=$(date '+%Y-%m-%d %H:%M:%S')
BK=$WL_TMP/witness-sdnet-gaps-$STAMP.d
PWO=$(wl_newpw); PWS=$(wl_newpw); PWR=$(wl_newpw)
WL_SECRETS=("$PWO" "$PWS" "$PWR")

say "witness-sdnet-gaps.sh  $STAMP   (audit judged from $START_TS)"
say "  script  : $SELF"
say "  sudo    : $SUDO_USER (the owner)   account to make: $ACC   $HOST:$PORT"
say "  install : $(wl_commit_stamp)"
say "  sd      : $WL_SD   $(timeout 20 "$WL_SD" --version 2>&1 | head -1)"
say "  working : $BK   (the backups stay here)"

MADE_USER=0; MADE_ACCOUNT=0; GROUND_CLEAR=0; CLEANED=0

cleanup() {
  local rc=$?
  [ "$CLEANED" -eq 0 ] || return 0
  CLEANED=1
  trap - EXIT
  say ""
  say "== Z. putting back what this run made =="
  if [ "$GROUND_CLEAR" -eq 1 ]; then
    if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$WL_SDSYS/accounts/$ACC" ]; then
      wl_sd_admin "delete.account $ACC" "DELETE.ACCOUNT $ACC" "y" >/dev/null
    fi
    if [ "$MADE_USER" -eq 1 ] && id -u "$ACC" >/dev/null 2>&1; then
      userdel -r "$ACC" >/dev/null 2>&1 && say "  userdel -r $ACC: done" || say "  userdel -r $ACC: FAILED - remove it by hand"
    fi
    if [ "$MADE_USER" -eq 1 ] && ! id -u "$ACC" >/dev/null 2>&1 && [ -d "/home/$ACC" ]; then
      rm -rf -- "/home/$ACC" && say "  removed /home/$ACC (DELETE.ACCOUNT keeps a home; this run made it)"
    fi
    rm -f -- "$BK/pw" 2>/dev/null
    local left=""
    [ -e "$WL_SDSYS/accounts/$ACC" ] && left="$left register"
    id -u "$ACC" >/dev/null 2>&1 && left="$left user"
    wl_group_exists "sdu_$ACC" && left="$left group"
    [ -d "/home/$ACC" ] && left="$left home"
    [ -d "/home/sd/user_accounts/$ACC" ] && left="$left account-dir"
    if [ -z "$left" ]; then pass "Z1 nothing of $ACC is left (register, user, group, home, account directory)"; else fail "Z1 left behind for $ACC:$left - remove by hand"; fi
    wl_in_group "$ACC" sdfiles && fail "Z2 $ACC is still listed in sdfiles" || pass "Z2 $ACC is not in sdfiles"
    wl_in_group "$ACC" sdfileswrite && fail "Z3 $ACC is still listed in sdfileswrite" || pass "Z3 $ACC is not in sdfileswrite"
  else
    say "  (the ground was never found clear, so nothing was made and nothing is touched)"
  fi
  wl_summary
  local s=$?
  if [ "$rc" -ne 0 ]; then exit "$rc"; fi
  exit "$s"
}
trap cleanup EXIT

# ------------------------------------------------------------------ premises
[ -x "$WL_SD" ] || need "$WL_SD is not installed - run the installer first"
for g in sdfiles sdfileswrite sdusers; do wl_group_exists "$g" || need "no Linux group $g on this machine (install from a tree that makes it)"; done
command -v ss >/dev/null 2>&1 || need "ss is not installed"
command -v openssl >/dev/null 2>&1 || need "openssl is not installed (the TLS rows need its s_client)"
command -v python3 >/dev/null 2>&1 || need "python3 is not installed"
ss -ltn 2>/dev/null | grep -q -E "[:.]$PORT[[:space:]]" || need "nothing is listening on port $PORT (is the API server running on this install?)"
grep -q 'cannot change or lock files here' "$WL_SDSYS/messages/11521" 2>/dev/null || need "the installed message 11521 is not the K1 text: this install predates the S.65 finish (19 Oct 2026)"
grep -q 'route.files.write' "$WL_SDSYS/gpl.bp/restorea" 2>/dev/null || need "the installed restorea has no route.files.write: this install predates the write group"
[ -r "$WL_AUDIT" ] || need "the audit file $WL_AUDIT cannot be read"
[ -r "$HERE/verify-auditwords.py" ] || need "no verify-auditwords.py beside this script"
DIRTY=0
[ -e "$WL_SDSYS/accounts/$ACC" ] && { say "  DIRTY: register record $ACC exists"; DIRTY=1; }
id -u "$ACC" >/dev/null 2>&1 && { say "  DIRTY: Linux user $ACC exists"; DIRTY=1; }
wl_group_exists "sdu_$ACC" && { say "  DIRTY: group sdu_$ACC exists"; DIRTY=1; }
[ -d "/home/$ACC" ] && { say "  DIRTY: /home/$ACC exists"; DIRTY=1; }
[ -d "/home/sd/user_accounts/$ACC" ] && { say "  DIRTY: /home/sd/user_accounts/$ACC exists"; DIRTY=1; }
OUT=$(wl_sd_admin "list.servers (does an sd session as sdsys work?)" "LIST.SERVERS")
[ -n "$OUT" ] || need "LIST.SERVERS printed nothing: an sd session as sdsys does not work here (is sd.service running?)"
[ "$DIRTY" -eq 0 ] || need "the ground is not clear (above): this script will not touch state it did not create"
GROUND_CLEAR=1
say "  ground clear: none of $ACC exists"

mkdir -p -- "$BK" && chmod 755 "$BK" || need "cannot make $BK"
install -m 755 "$HERE/witness-sdnet-probe.py" "$BK/probe.py" || need "cannot copy witness-sdnet-probe.py beside this script"

# ================================================================== T. TLS
say ""; say "== T. the API port: TLS 1.2 refused, TLS 1.3 completes =="
T12=$(echo | timeout 20 openssl s_client -connect "$HOST:$PORT" -tls1_2 2>&1 | tee /dev/stderr)
T13=$(echo | timeout 20 openssl s_client -connect "$HOST:$PORT" -tls1_3 2>&1 | tee /dev/stderr)
expect_re "T1 TLS 1.2 is refused (a protocol, handshake or no-ciphers alert, and no negotiated cipher)" "$T12" 'alert protocol version|handshake failure|no protocols available|wrong version number|Cipher *(is|:) *\(NONE\)'
expect_lacks "T1 and no TLS 1.2 session was set up" "$T12" "Protocol  : TLSv1.2"
expect_re "T2 TLS 1.3 completes (the protocol line names it)" "$T13" 'Protocol *: *TLSv1\.3|New, TLSv1\.3'
expect_lacks "T2 and it was not refused" "$T13" "alert protocol version"

# ================================================================== the fixture account
say ""; say "== S. the fixture: account $ACC with the files route and a file =="
MADE_USER=1; MADE_ACCOUNT=1
OUT=$(wl_sd_admin "create.account $ACC" "CREATE.ACCOUNT USER $ACC FILES-ON" "$PWO" "$PWO")
[ -e "$WL_SDSYS/accounts/$ACC" ] && pass "S1 the register record exists" || fail "S1 no register record for $ACC"
id -u "$ACC" >/dev/null 2>&1 && pass "S1 the Linux user exists" || fail "S1 no Linux user $ACC"
[ -e "$WL_SDSYS/accounts/$ACC" ] || need "no account was made: nothing after this can mean anything"
expect_eq "S1 the real groups: sdfiles only" "$(wl_state "$ACC")" "sdfiles=1 sdfileswrite=0"
wl_in_group "$ACC" sdapi && fail "S1 $ACC IS in sdapi: it must be a files-only login" || pass "S1 $ACC is NOT in sdapi (a files-only login)"
OUT=$(wl_sd_admin "modify.password $ACC" "MODIFY.PASSWORD $ACC" "$PWS" "$PWS")
expect_has "S2 'Password accepted.'" "$OUT" "Password accepted."
OUT=$(wl_sd_user "$ACC" "make zzgfile" "CREATE.FILE zzgfile DYNAMIC" "ED zzgfile g1" "I one" "FI" "COUNT zzgfile")
expect_re "S3 zzgfile holds 1 record" "$OUT" '^1 record\(s\) counted'
: > "$BK/pw" && chown "$ACC" "$BK/pw" && chmod 600 "$BK/pw" || need "cannot make the password file"
printf '%s\n' "$PWS" > "$BK/pw"

# probe_run TAG WRITEWORD   run the gaps probe as the files-only login; check its text and the server's audit
probe_run() {
  local tag=$1 w=$2 aud0 aud pout n
  aud0=$(wl_audit_offset)
  pout=$(sudo -u "$ACC" python3 "$BK/probe.py" gaps "$HOST" "$PORT" "$ACC" "$BK/pw" "$ACC" zzgfile g1 2>&1 | tee /dev/stderr)
  sleep 2
  aud=$(wl_audit_since "$aud0")
  say "  audit lines added by the $tag probe:"; printf '%s\n' "$aud" | grep -a -E 'api' | cut -c1-200 | sed -e 's/^/      | /'
  expect_has "$tag NULL CASE: the probe connected, opened the file and finished" "$pout" "P DONE"
  expect_has "$tag the login is a files-only login with write=$w" "$aud" "api login route=sdfiles write=$w user=$ACC"
  for n in 20 21 22 23 54 61 3; do
    expect_has "$tag request $n: the person sees the 11480 text" "$pout" "$(wl_msg 11480 $n)"
    expect_has "$tag request $n: the server audit says api refused request=$n route=sdfiles write=$w user=$ACC" "$aud" "api refused request=$n route=sdfiles write=$w user=$ACC"
  done
  expect_eq "$tag the second 3 is the ONE refused 3 (the first, the account entry after login, was allowed)" "$(count_re "$aud" "api refused request=3 route=sdfiles")" 1
  expect_re "$tag control: a read is still allowed after all those refusals" "$pout" '^P 6 SDRead \(control, still allowed\) +status=0 ret=True'
  expect_lacks "$tag control: request 6 was never refused" "$aud" "api refused request=6 "
  expect_lacks "$tag no 11521 text (those are for the requests the write group governs, not for these)" "$pout" "files-write-on (request"
}
count_re() { local n; n=$(printf '%s\n' "$1" | grep -a -c -E -- "$2"); printf '%s' "${n:-0}"; }

# ================================================================== W. the requests no files-only login may make
say ""; say "== W1. files-on alone: 20 21 22 23 54 61 and a second 3 are refused =="
probe_run W1 off
say ""; say "== take a backup now (write group OFF), then turn it on =="
R_OFF=$(wl_backup_routes "$ACC" "$BK/bak-off")
expect_re "W2 manifest, write group off: route.files: 1 route.files.write: 0" "$R_OFF" "\[account $ACC\] route\.files: 1 route\.files\.write: 0"
OUT=$(wl_sd_admin "files-write-on" "MODIFY.ACCOUNT $ACC FILES-WRITE-ON")
expect_has "W2 the line says files-write yes" "$OUT" "$(wl_msg 11522 "$ACC" yes)"
expect_eq "W2 the real groups: both" "$(wl_state "$ACC")" "sdfiles=1 sdfileswrite=1"
say ""; say "== W3. files-write-on: the SAME requests are refused just the same =="
probe_run W3 on
R_ON=$(wl_backup_routes "$ACC" "$BK/bak-on")
expect_re "W4 manifest, write group on: route.files: 1 route.files.write: 1" "$R_ON" "\[account $ACC\] route\.files: 1 route\.files\.write: 1"

# ================================================================== A. audit words
say ""; say "== A. verify-auditwords.py over the real audit file, from $START_TS =="
AW=$(python3 "$HERE/verify-auditwords.py" --file "$WL_AUDIT" --since "$START_TS" 2>&1); AWRC=$?     # not "| tee": a pipe inside $( ) would give the status of tee
printf '%s\n' "$AW" >&2
expect_eq "A1 verify-auditwords exits 0 (every event word this run wrote is lower case)" "$AWRC" "0"
expect_re "A1 it judged records (a reader that judges nothing proves nothing)" "$AW" '[1-9][0-9]* judged'
expect_re "A1 its control saw a login record" "$AW" 'control: [1-9][0-9]* judged "login" record'
expect_lacks "A1 and it did not say NOTHING MEASURED" "$AW" "NOTHING MEASURED"

# ================================================================== R. backup, delete, restore
say ""; say "== R. delete $ACC and restore it from each backup =="
zip_of() { ls "$1"/*.zip 2>/dev/null | head -1; }
ZIP_OFF=$(zip_of "$BK/bak-off"); ZIP_ON=$(zip_of "$BK/bak-on")
[ -n "$ZIP_OFF" ] && [ -n "$ZIP_ON" ] || need "a backup archive is missing (above): restore cannot be tried"
say "  archives: write-off $ZIP_OFF   write-on $ZIP_ON"

restore_from() {   # restore_from TAG ZIP WANT_STATE
  local tag=$1 zip=$2 want=$3 out
  out=$(wl_sd_admin "delete.account $ACC (before restoring from the $tag archive)" "DELETE.ACCOUNT $ACC" "y")
  [ -e "$WL_SDSYS/accounts/$ACC" ] && fail "$tag the account is still registered after DELETE.ACCOUNT: the restore would replace, not create" || pass "$tag the account is gone (register)"
  id -u "$ACC" >/dev/null 2>&1 && fail "$tag the Linux user is still there after DELETE.ACCOUNT" || pass "$tag the Linux user is gone"
  wl_in_group "$ACC" sdfiles && fail "$tag the user is still listed in sdfiles" || pass "$tag the user is not listed in sdfiles"
  wl_in_group "$ACC" sdfileswrite && fail "$tag the user is still listed in sdfileswrite" || pass "$tag the user is not listed in sdfileswrite"
  out=$(wl_sd_admin "restore.account from the $tag archive" "RESTORE.ACCOUNT $zip $ACC NO.QUERY" "$PWR" "$PWR")
  [ -e "$WL_SDSYS/accounts/$ACC" ] && pass "$tag the register record is back" || fail "$tag no register record after RESTORE.ACCOUNT"
  id -u "$ACC" >/dev/null 2>&1 && pass "$tag the Linux user is back" || fail "$tag no Linux user after RESTORE.ACCOUNT"
  expect_eq "$tag THE REAL GROUPS: the restored user is in exactly what the manifest said" "$(wl_state "$ACC")" "$want"
  wl_in_group "$ACC" sdusers && pass "$tag the restored user is in sdusers" || fail "$tag the restored user is not in sdusers"
  expect_re "$tag the restore reports itself (13025: Restored 1 account(s) from ...)" "$out" '^Restored 1 account\(s\) from '
  expect_lacks "$tag the restore did not stop on a mismatch (13013)" "$out" "Nothing was restored."
}
restore_from R1-write-off "$ZIP_OFF" "sdfiles=1 sdfileswrite=0"
OUT=$(wl_sd_user "$ACC" "the restored data (as the restored user)" "COUNT zzgfile")
expect_re "R1 the restored account holds zzgfile with its record" "$OUT" '^1 record\(s\) counted'
restore_from R2-write-on "$ZIP_ON" "sdfiles=1 sdfileswrite=1"
OUT=$(wl_sd_user "$ACC" "the restored data (as the restored user)" "COUNT zzgfile")
expect_re "R2 the restored account holds zzgfile with its record" "$OUT" '^1 record\(s\) counted'
R_AGAIN=$(wl_backup_routes "$ACC" "$BK/bak-again")
expect_re "R3 a new backup of the restored account says the same: route.files: 1 route.files.write: 1" "$R_AGAIN" "\[account $ACC\] route\.files: 1 route\.files\.write: 1"

say ""
say "== the rows above are complete; putting back (Z rows follow) =="
cleanup
