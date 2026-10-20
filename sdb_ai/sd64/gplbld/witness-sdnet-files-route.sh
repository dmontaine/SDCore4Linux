#!/usr/bin/env bash
#
# witness-sdnet-files-route.sh - SDNet on a real install talking to itself: the whole files-only route and the write group, on the CURRENT build.
#                                (K6b, 19 Oct 2026; the S.65 finish.  Ports the private steps w1-w9 and w21a-w21d of
#                                .claude/vmtools/sdnet-witness-steps/round3, which ran on the Debian 13 Clone VM on 18 Oct, and adds what the S.65 finish changed.)
#
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-files-route.sh [--client ACCOUNT] [--remote NAME] [--port N]
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-files-route.sh --selftest        (no sudo, no sd: the helpers on known texts)
#
# ***NEEDS sudo.***  Run it from the owner's login (SUDO_USER must name a person, not root).  It CHANGES REAL STATE on the install and puts it back:
#   * MAKES an SD account REMOTE (default zzwrem) with its Linux user, and DELETES them at the end (DELETE.ACCOUNT, then userdel -r and its home);
#   * DEFINES a server zzloop, the client's stored login for it and two VOC pointers in the client account, and removes all three;
#   * TURNS ON the NET, VOC and BP gates of the client account (default: the account of SUDO_USER) and puts its register record back byte for byte from a copy it
#     takes first (the copy is kept under /var/tmp/witness-sdnet-files-route-<time>/ and the script says so);
#   * writes ten small programs zzwn* into the client's bp, and removes them.
# It refuses to start when anything it would make already exists.  It does not install and does not uninstall, and it never touches the VM's other installs.
#
# WHY IT EXISTS.  The 18 Oct VM runs (round 2 on 5315c65, round 3 on c42aa13) were made before the S.65 finish.  Since then these changed and have been proved only in
# sandboxes and against a fake server (gplbld/netfake.py): the text of a refused change (message 11521, K1), "Account X has files yes" (K2, message 11482), the
# audit reason "not a member of sdapi or sdfiles" (K3), MODIFY.ACCOUNT files-off / files-on and the orphan (K4a: witness-sdnet-writegroup.sh), the NETWAIT / NETREPLY waits
# (K8d) and the oversize-reply refusal (K8c).  This script runs the lot against the REAL server over the real loopback TLS channel.
#
# PREREQUISITE: an install made from a tree that has the S.65 finish (the script CHECKS the installed texts), the API server listening on the port, the client account
# a user account of its own (the installing user's).  Install first, as the owner, no sudo (installsdcore-dev.sh asks questions).
#
# WHAT IT DOES, in order.  Each row needs the success wording AND the state of the real thing (groups, audit, server file); a session that prints nothing fails its rows.
#   P   premises: the install has the S.65 finish, the ground is clear, the client is a user account
#   S   set-up: CREATE.ACCOUNT, MODIFY.PASSWORD, seed two files, THE KEY (set.server ... connect shows the hash; sd-elevate tls-key and the docs' openssl pipeline give the
#       SAME hash - the "not confirmed" line of 12-sdnet.md), the definition, the stored login, the gates, the VOC pointers
#   R   read: COUNT / LIST / SORT through the pointer, a read, a dictionary open
#   A   files-on only (no write group): every change or lock is refused BY THE SERVER; the text a person sees is K1's; the audit lines; the file did not change; the
#       probe (the C client library through ctypes) sends 7-10, 16-19 and 30 directly
#   M   the definition says READ: the client refuses a write before it is sent (11501); a WRONG PIN: nothing reaches the server (11455, no new login line)
#   B   files-write-on: the same programs now work, the server file changed, two sessions see each other's lock, the audit says write=on and has no refusal
#   C   files-write-off, files-off (K3: the login is refused with the new reason), files-on (K2), the manifest key route.files.write at each step
#   Z   put back: the register record is identical to the copy, nothing the script made is left
# NOT COVERED HERE (other scripts): the orphan and the order of the two group changes (witness-sdnet-writegroup.sh), the requests no files-only login may make, TLS 1.2,
# backup and restore (witness-sdnet-gaps.sh), the installer and uninstaller (witness-sdnet-groups.sh), two machines (witness-sdnet-two-machines.sh), MUSTLOCK (not scripted: see
# the S.65 row).  The private steps w13-w20 (LOGTO, lost connection, CLEARFILE, a transaction, edit gates by name, the negative gates, the restore) are NOT ported: run them
# from .claude/vmtools once they use one MODIFY.ACCOUNT word per command (w3 does not).
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-files-route-<time>.<six random characters>.log, handed back to the owner.
# Changed 19 Oct 26 (finish 2, the verifier's findings): the backup directory is made with wl_mkdir_new, and the audit offset is the physical line count (wl_audit_offset).
#
set -u
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
HERE=$(dirname "$SELF")
# shellcheck source=witness-sdnet-lib.sh
. "$HERE/witness-sdnet-lib.sh" || { echo "CANNOT RUN: no witness-sdnet-lib.sh beside $SELF"; exit 2; }

if [ "${1:-}" = "--selftest" ]; then wl_selftest; exit $?; fi
wl_logged "$SELF" witness-sdnet-files-route "$@"
shift                                   # the "--logged" the re-exec added

CLIENT=""; REMOTE=zzwrem; PORT=4247
while [ $# -gt 0 ]; do
  case $1 in
    --client) [ $# -ge 2 ] || need "--client needs an account name"; CLIENT=$2; shift 2 ;;
    --remote) [ $# -ge 2 ] || need "--remote needs a name"; REMOTE=$2; shift 2 ;;
    --port)   [ $# -ge 2 ] || need "--port needs a number"; PORT=$2; shift 2 ;;
    *) need "unknown argument '$1'" ;;
  esac
done
[ -n "$CLIENT" ] || CLIENT=$SUDO_USER
SRV=zzloop; HOST=127.0.0.1
case $REMOTE in *[!a-z0-9]*|'') need "--remote must be lower case letters and digits" ;; esac
case $PORT in *[!0-9]*|'') need "--port must be a number" ;; esac

STAMP=$(date +%Y%m%dT%H%M%S)
BK=$WL_TMP/witness-sdnet-files-route-$STAMP.d
PWO=$(wl_newpw); PWS=$(wl_newpw)
WL_SECRETS=("$PWO" "$PWS")

say "witness-sdnet-files-route.sh  $STAMP"
say "  script  : $SELF"
say "  sudo    : $SUDO_USER (the owner)   client account: $CLIENT   remote account to make: $REMOTE   server name to define: $SRV   $HOST:$PORT"
say "  install : $(wl_commit_stamp)"
say "  sd      : $WL_SD   $(timeout 20 "$WL_SD" --version 2>&1 | head -1)"
say "  working : $BK   (the copy of the client's register record, the password file and the backups live here)"

# ------------------------------------------------------------------ the things this run may have made (set BEFORE the command that makes them)
MADE_USER=0; MADE_ACCOUNT=0; MADE_SERVER=0; MADE_NETLOGIN=0; MADE_VOC=0; MADE_PROGS=0; GROUND_CLEAR=0; REG_SAVED=0; CLEANED=0
PROGS="zzwnmk zzwnrd zzwn1 zzwn2 zzwn3 zzwn4 zzwnla zzwnlb zzwncl"

cleanup() {
  local rc=$? p
  [ "$CLEANED" -eq 0 ] || return 0
  CLEANED=1
  trap - EXIT
  say ""
  say "== Z. putting back what this run made =="
  if [ "$GROUND_CLEAR" -eq 1 ]; then
    if [ "$MADE_VOC" -eq 1 ]; then wl_sd_user "$CUSER" "remove the two VOC pointers" "RUN bp zzwncl" >/dev/null; fi
    if [ "$MADE_NETLOGIN" -eq 1 ]; then wl_sd_user "$CUSER" "delete.netlogin $SRV" "DELETE.NETLOGIN $SRV" >/dev/null; fi
    if [ "$MADE_SERVER" -eq 1 ]; then wl_sd_admin "delete.server $SRV" "DELETE.SERVER $SRV" >/dev/null; fi
    if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$WL_SDSYS/accounts/$REMOTE" ]; then
      wl_sd_admin "delete.account $REMOTE" "DELETE.ACCOUNT $REMOTE" "y" >/dev/null
    fi
    if [ "$MADE_USER" -eq 1 ] && id -u "$REMOTE" >/dev/null 2>&1; then
      userdel -r "$REMOTE" >/dev/null 2>&1 && say "  userdel -r $REMOTE: done" || say "  userdel -r $REMOTE: FAILED - remove it by hand"
    fi
    # the home is this run's to take once its user is gone (DELETE.ACCOUNT keeps a home by design), and only after the ground was found clear
    if [ "$MADE_USER" -eq 1 ] && ! id -u "$REMOTE" >/dev/null 2>&1 && [ -d "/home/$REMOTE" ]; then
      rm -rf -- "/home/$REMOTE" && say "  removed /home/$REMOTE (DELETE.ACCOUNT keeps a home; this run made it)"
    fi
    if [ "$MADE_PROGS" -eq 1 ] && [ -n "${CDIR:-}" ] && [ -d "$CDIR/bp" ]; then
      for p in $PROGS; do rm -f -- "$CDIR/bp/$p" "$CDIR/bp.out/$p"; done
      say "  removed the programs $PROGS from $CDIR/bp (and their objects from bp.out)"
    fi
    if [ "$REG_SAVED" -eq 1 ]; then
      cp -p -- "$BK/register-$CLIENT" "$WL_SDSYS/accounts/$CLIENT" && say "  the register record of $CLIENT put back from $BK/register-$CLIENT"
      if cmp -s -- "$BK/register-$CLIENT" "$WL_SDSYS/accounts/$CLIENT"; then pass "Z1 the register record of $CLIENT is identical to the copy taken before the run"
      else fail "Z1 the register record of $CLIENT differs from the copy taken before the run (the copy is in $BK)"; fi
    fi
    rm -f -- "$BK/pw" 2>/dev/null
    local left=""
    [ -e "$WL_SDSYS/accounts/$REMOTE" ] && left="$left register"
    id -u "$REMOTE" >/dev/null 2>&1 && left="$left user"
    wl_group_exists "sdu_$REMOTE" && left="$left group"
    [ -d "/home/$REMOTE" ] && left="$left home"
    [ -d "/home/sd/user_accounts/$REMOTE" ] && left="$left account-dir"
    if [ -z "$left" ]; then pass "Z2 nothing of $REMOTE is left (register, user, group, home, account directory)"; else fail "Z2 left behind for $REMOTE:$left - remove by hand"; fi
    wl_in_group "$REMOTE" sdfiles && fail "Z3 $REMOTE is still listed in sdfiles" || pass "Z3 $REMOTE is not in sdfiles"
    wl_in_group "$REMOTE" sdfileswrite && fail "Z4 $REMOTE is still listed in sdfileswrite" || pass "Z4 $REMOTE is not in sdfileswrite"
  else
    say "  (the ground was never found clear, so nothing was made and nothing is touched)"
  fi
  wl_summary
  local s=$?
  if [ "$rc" -ne 0 ]; then exit "$rc"; fi
  exit "$s"
}
trap cleanup EXIT

# ------------------------------------------------------------------ P. premises
[ -x "$WL_SD" ] || need "$WL_SD is not installed - run the installer first"
for g in sdfiles sdfileswrite sdusers; do wl_group_exists "$g" || need "no Linux group $g on this machine (install from a tree that makes it)"; done
command -v ss >/dev/null 2>&1 || need "ss is not installed"
ss -ltn 2>/dev/null | grep -q -E "[:.]$PORT[[:space:]]" || need "nothing is listening on port $PORT (is the API server running on this install?)"
[ -r "$WL_SDSYS/messages/11521" ] || need "no $WL_SDSYS/messages/11521"
grep -q 'cannot change or lock files here' "$WL_SDSYS/messages/11521" 2>/dev/null || need "the installed message 11521 is not the K1 text: this install predates the S.65 finish (19 Oct 2026); install a newer Dev"
grep -q 'has files %2' "$WL_SDSYS/messages/11482" 2>/dev/null || need "the installed message 11482 is not 'Account %1 has files %2' (K2)"
grep -q 'not a member of sdapi or sdfiles' "$WL_SDSYS/gpl.bp/apisrvr" 2>/dev/null || need "the installed apisrvr has no 'not a member of sdapi or sdfiles' (K3)"
grep -q 'change.files.group' "$WL_SDSYS/gpl.bp/modifya" 2>/dev/null || need "the installed modifya has no change.files.group (K4a)"
grep -q 'NETREPLY' "$WL_SDSYS/gpl.bp/config" 2>/dev/null || need "the installed config verb does not list NETREPLY (K8d)"
[ -x "$WL_ELEVATE" ] || need "$WL_ELEVATE is not installed"
CUSER=$(wl_account_user "$CLIENT")
[ -n "$CUSER" ] || need "the register record of account '$CLIENT' is not a user account (field 3 is not sdu_<user>): give --client ACCOUNT"
id "$CUSER" >/dev/null 2>&1 || need "no Linux user '$CUSER'"
CDIR=$(wl_account_path "$CLIENT")
[ -n "$CDIR" ] && [ -d "$CDIR/bp" ] || need "the client account's directory '$CDIR' has no bp file"
say "  client  : account $CLIENT, Linux user $CUSER, directory $CDIR"

# the ground: nothing of the names this run makes may exist, so that it never touches state it did not create
DIRTY=0
[ -e "$WL_SDSYS/accounts/$REMOTE" ] && { say "  DIRTY: register record $REMOTE exists"; DIRTY=1; }
id -u "$REMOTE" >/dev/null 2>&1 && { say "  DIRTY: Linux user $REMOTE exists"; DIRTY=1; }
wl_group_exists "sdu_$REMOTE" && { say "  DIRTY: group sdu_$REMOTE exists"; DIRTY=1; }
[ -d "/home/$REMOTE" ] && { say "  DIRTY: /home/$REMOTE exists"; DIRTY=1; }
[ -d "/home/sd/user_accounts/$REMOTE" ] && { say "  DIRTY: /home/sd/user_accounts/$REMOTE exists"; DIRTY=1; }
[ -r "$WL_AUDIT" ] || need "the audit file $WL_AUDIT cannot be read"
OUT=$(wl_sd_admin "list.servers (is $SRV free?)" "LIST.SERVERS")
[ -n "$OUT" ] || need "LIST.SERVERS printed nothing: an sd session as sdsys does not work here (is sd.service running?)"
if printf '%s\n' "$OUT" | grep -a -q -E "^$SRV[[:space:]]"; then say "  DIRTY: a server named $SRV is already defined"; DIRTY=1; fi
for p in $PROGS; do [ -e "$CDIR/bp/$p" ] && { say "  DIRTY: $CDIR/bp/$p exists"; DIRTY=1; }; done
[ "$DIRTY" -eq 0 ] || need "the ground is not clear (above): this script will not touch state it did not create"
GROUND_CLEAR=1
say "  ground clear: none of $REMOTE, $SRV, the programs exists"

wl_mkdir_new "$BK" 755
cp -p -- "$WL_SDSYS/accounts/$CLIENT" "$BK/register-$CLIENT" || need "cannot copy the register record of $CLIENT"
REG_SAVED=1
REG_SUM=$(sha256sum "$BK/register-$CLIENT" | cut -d' ' -f1)
say "  saved   : the register record of $CLIENT, sha256 $REG_SUM"
install -m 755 "$HERE/witness-sdnet-probe.py" "$BK/probe.py" || need "cannot copy witness-sdnet-probe.py beside this script"
: > "$BK/pw" && chown "$CUSER" "$BK/pw" && chmod 600 "$BK/pw" || need "cannot make the password file"
printf '%s\n' "$PWS" > "$BK/pw"

TXT_WRITE_REFUSED=$(wl_msg 11521 16)
[ -n "$TXT_WRITE_REFUSED" ] || need "message 11521 cannot be read"

# ------------------------------------------------------------------ small helpers
count_re() { local n; n=$(printf '%s\n' "$1" | grep -a -c -E -- "$2"); printf '%s' "${n:-0}"; }
prog() { sudo -u "$CUSER" tee "$CDIR/bp/$1" >/dev/null; }
srvids() { wl_sd_user "$REMOTE" "list the ids of $1 on the server" "LIST $1 @ID" | grep -a -o -E '^[a-z][a-z0-9-]*' | grep -a -x -E 'p[0-9]|n[0-9]|p[0-9]-w[u]?|lk1|c[0-9]' | sort -u | tr '\n' ' '; }
reseed() { wl_sd_user "$REMOTE" "reseed zzwgf" "CLEAR.FILE zzwgf" "ED zzwgf p1" "I one" "FI" "ED zzwgf p2" "I two" "FI" "ED zzwgf p3" "I three" "FI" "ED zzwgf lk1" "I lock me" "FI" >/dev/null; }
logins() { grep -a -c 'api login route=sdfiles' "$WL_AUDIT" 2>/dev/null || true; }
defs() {   # defs PIN MODE   (re)define the server $SRV with the typed pin; prints the LIST.SERVERS line
  wl_sd_admin "set.server $SRV (pin typed, mode $2)" "SET.SERVER $SRV $HOST $PORT $REMOTE $1 $2 ACCOUNTS $CLIENT NO.QUERY" "LIST.SERVERS"
}
have_line() { printf '%s\n' "$1" | grep -a -q -E -- "$2"; }

# ================================================================== S. set-up
say ""; say "== S1. CREATE.ACCOUNT USER $REMOTE with the files route and the edit gates it needs =="
MADE_USER=1; MADE_ACCOUNT=1
OUT=$(wl_sd_admin "create.account $REMOTE" "CREATE.ACCOUNT USER $REMOTE FILES-ON VOC-ON BP-ON" "$PWO" "$PWO")
[ -e "$WL_SDSYS/accounts/$REMOTE" ] && pass "S1 the register record exists" || fail "S1 no register record for $REMOTE (the create did not happen: every later row is void)"
id -u "$REMOTE" >/dev/null 2>&1 && pass "S1 the Linux user exists" || fail "S1 no Linux user $REMOTE"
expect_eq "S1 the real groups: sdfiles only, no write group" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=0"
wl_in_group "$REMOTE" sdusers && pass "S1 the user is in sdusers" || fail "S1 the user is not in sdusers"
wl_in_group "$REMOTE" sdapi && fail "S1 the user IS in sdapi: a files-only login must not have the whole API" || pass "S1 the user is NOT in sdapi (the API gate is off): the files route is the only one"
[ -e "$WL_SDSYS/accounts/$REMOTE" ] || need "no account was made: nothing after this can mean anything"

say ""; say "== S2. MODIFY.PASSWORD (the password the SDNet login will use) =="
OUT=$(wl_sd_admin "modify.password $REMOTE" "MODIFY.PASSWORD $REMOTE" "$PWS" "$PWS")
expect_has "S2 'Password accepted.'" "$OUT" "Password accepted."
expect_lacks "S2 and not 'Password not changed.'" "$OUT" "Password not changed."
expect_lacks "S2 and not 'Unable to set password'" "$OUT" "Unable to set password"

say ""; say "== S3. the two server files: zzcust (3 customers, a dictionary) and zzwgf (p1 p2 p3 lk1) =="
OUT=$(wl_sd_user "$REMOTE" "seed zzcust and zzwgf" \
  "CREATE.FILE zzcust DYNAMIC" "ED zzcust c1" "I Smith" "I 100" "FI" "ED zzcust c2" "I Jones" "I 50" "FI" "ED zzcust c3" "I Brown" "I 75" "FI" \
  "ED DICT zzcust name" "I D" "I 1" "I Name" "I 15L" "I S" "FI" "ED DICT zzcust bal" "I D" "I 2" "I Balance" "I 10R" "I S" "FI" "COUNT zzcust" \
  "CREATE.FILE zzwgf DYNAMIC" "CLEAR.FILE zzwgf" "ED zzwgf p1" "I one" "FI" "ED zzwgf p2" "I two" "FI" "ED zzwgf p3" "I three" "FI" "ED zzwgf lk1" "I lock me" "FI" "COUNT zzwgf")
expect_re "S3 zzcust holds 3 records" "$OUT" '^3 record\(s\) counted'
expect_re "S3 zzwgf holds 4 records" "$OUT" '^4 record\(s\) counted'
SEEDED_IDS=$(srvids zzwgf)
expect_eq "S3 the ids of zzwgf on the server" "$SEEDED_IDS" "lk1 p1 p2 p3 "

say ""; say "== S4. THE KEY: set.server ... connect, answered n; the same hash from sd-elevate tls-key and from the openssl pipeline =="
MADE_SERVER=1
OUT=$(wl_sd_admin "set.server $SRV ... connect, answering n" "SET.SERVER $SRV $HOST $PORT $REMOTE connect READ ACCOUNTS $CLIENT" "n")
expect_has "S4 'Connected to ... (a TLS handshake only: nothing was sent)'" "$OUT" "$(wl_msg 11440 "$HOST" "$PORT")"
expect_has "S4 'The key was not trusted.  Nothing was written'" "$OUT" "$(wl_msg 11443 "$SRV")"
HASH_CONNECT=$(printf '%s\n' "$OUT" | grep -a -E '^[0-9a-f]{64}$' | head -1)
expect_re "S4 the hash is 64 lower case hex digits, alone on its line" "$HASH_CONNECT" '^[0-9a-f]{64}$'
OUT=$(wl_sd_admin "list.servers (answering n wrote nothing)" "LIST.SERVERS")
if [ -z "$OUT" ]; then fail "S4 LIST.SERVERS printed nothing (the null case)"
elif printf '%s\n' "$OUT" | grep -a -q -E "^$SRV[[:space:]]"; then fail "S4 the definition was written although the key was not trusted"
else pass "S4 nothing was written: $SRV is not in LIST.SERVERS"; fi
TLSKEY=$("$WL_ELEVATE" tls-key 2>&1 | tee /dev/stderr | sed -n 's/^public key sha256: //p')
expect_eq "S4 sd-elevate tls-key gives the hash the connection showed" "$TLSKEY" "$HASH_CONNECT"
if command -v openssl >/dev/null 2>&1 && [ -r "$WL_TLS_PEM" ]; then
  OSSL=$(sh -c 'openssl x509 -pubkey -noout -in "$1" | openssl pkey -pubin -outform DER | openssl dgst -sha256' sh "$WL_TLS_PEM" 2>&1 | tee /dev/stderr | grep -o -E '[0-9a-f]{64}$' | head -1)
  expect_eq "S4 the openssl pipeline of 12-sdnet.md gives the same hash" "$OSSL" "$HASH_CONNECT"
else
  say "  SKIPPED  S4 the openssl pipeline: openssl or $WL_TLS_PEM is not here (not counted as a pass)"
fi

say ""; say "== S5. the definition, WRITE mode, trusting that key =="
MADE_SERVER=1
OUT=$(wl_sd_admin "set.server $SRV ... connect, answering y" "SET.SERVER $SRV $HOST $PORT $REMOTE connect WRITE ACCOUNTS $CLIENT NO.QUERY" "y" "LIST.SERVERS")
expect_has "S5 'Server $SRV ($HOST:$PORT) is defined'" "$OUT" "$(wl_msg 11424 "$SRV" "$HOST" "$PORT")"
PIN=$HASH_CONNECT
SHORT=$(printf '%s' "$PIN" | cut -c1-16)
expect_re "S5 LIST.SERVERS shows the server, write mode, the cut pin, the client account" "$OUT" "^$SRV +$HOST:$PORT +$REMOTE/write +$SHORT\.\.\. +$CLIENT *\$"

say ""; say "== S6. the client account: NET, VOC and BP gates, one word per command =="
for w in NET-ON VOC-ON BP-ON; do
  OUT=$(wl_sd_admin "modify.account $CLIENT $w" "MODIFY.ACCOUNT $CLIENT $w")
  expect_lacks "S6 $w was not refused as a second action (11714)" "$OUT" "does one action at a time"
done

say ""; say "== S7. the client programs (written into $CDIR/bp, compiled) =="
MADE_PROGS=1
prog zzwnmk <<'EOP'
   open 'voc' to v else crt 'NO VOC' ; stop
   write 'N':@fm:'zzloop':@fm:'zzcust' to v, 'zzrc' on error crt 'VOC WRITE REFUSED zzrc st=':status() ; stop
   write 'N':@fm:'zzloop':@fm:'zzwgf' to v, 'zzrw' on error crt 'VOC WRITE REFUSED zzrw st=':status() ; stop
   names = 'zzrc':@fm:'zzrw'
   for i = 1 to 2
      nm = names<i>
      read r from v, nm then crt 'pointer ':nm:' = [':change(r, @fm, ' / '):']' else crt 'pointer ':nm:' MISSING'
   next i
   crt 'zzwnmk done'
end
EOP
prog zzwnrd <<'EOP'
   open 'zzrc' to f else crt 'OPEN FAILED st=':status() ; stop
   crt 'data open ok'
   read r from f, 'c1' then crt 'c1=[':change(r, @fm, '/'):']' else crt 'READ ELSE st=':status()
   open 'DICT', 'zzrc' to d on error crt 'DICT OPEN ERROR st=':status() ; stop else crt 'DICT OPEN ELSE st=':status() ; stop
   crt 'dict open ok'
end
EOP
# zzwn1: every kind of change or lock, each ON ERROR, with the branch and STATUS() printed; two controls that are plain reads
prog zzwn1 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   crt 'X0 opened zzrw'
   oc = 'then' ; r = '' ; read r from f, 'p1' on error oc = 'error' else oc = 'else'
   crt 'X1 READ p1 (control) branch=':oc:' STATUS()=':status():' record=[':r:']'
   oc = 'then' ; write 'viaremote' to f, 'n1' on error oc = 'error'
   crt 'X2 WRITE n1 branch=':oc:' STATUS()=':status()
   oc = 'then' ; writeu 'viaremoteu' to f, 'n2' on error oc = 'error'
   crt 'X3 WRITEU n2 branch=':oc:' STATUS()=':status()
   oc = 'then' ; delete f, 'p2' on error oc = 'error'
   crt 'X4 DELETE p2 branch=':oc:' STATUS()=':status()
   oc = 'then' ; readu r from f, 'p3' on error oc = 'error' locked oc = 'locked' else oc = 'else'
   crt 'X5 READU p3 branch=':oc:' STATUS()=':status()
   oc = 'then' ; recordlocku f, 'p3' on error oc = 'error' locked oc = 'locked'
   crt 'X6 RECORDLOCKU p3 branch=':oc:' STATUS()=':status()
   oc = 'then' ; readvu v from f, 'p3', 1 on error oc = 'error' locked oc = 'locked' else oc = 'else'
   crt 'X7 READVU p3 branch=':oc:' STATUS()=':status()
   oc = 'then' ; readv v from f, 'p3', 1 on error oc = 'error' else oc = 'else'
   crt 'X8 READV p3 (control, no lock) branch=':oc:' STATUS()=':status():' value=[':v:']'
   oc = 'then' ; clearfile f on error oc = 'error'
   crt 'X9 CLEARFILE branch=':oc:' STATUS()=':status()
   release
   close f
   crt 'XZ done'
end
EOP
# zzwn2: one WRITE with no ON ERROR clause - the text a person sees
prog zzwn2 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   write 'viaremote' to f, 'n3'
   crt 'W9 REACHED (the write was not refused)'
end
EOP
# zzwn3: the same changes when the login may write
prog zzwn3 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then' ; write 'viaremote' to f, 'n1' on error oc = 'error'
   crt 'Y1 WRITE n1 branch=':oc:' STATUS()=':status()
   oc = 'then' ; writeu 'viaremoteu' to f, 'n2' on error oc = 'error'
   crt 'Y2 WRITEU n2 branch=':oc:' STATUS()=':status()
   oc = 'then' ; delete f, 'p2' on error oc = 'error'
   crt 'Y3 DELETE p2 branch=':oc:' STATUS()=':status()
   oc = 'then' ; readu r from f, 'p3' on error oc = 'error' locked oc = 'locked' else oc = 'else'
   crt 'Y4 READU p3 branch=':oc:' STATUS()=':status():' record=[':r:']'
   oc = 'then' ; recordlocku f, 'p1' on error oc = 'error' locked oc = 'locked'
   crt 'Y5 RECORDLOCKU p1 branch=':oc:' STATUS()=':status()
   oc = 'then' ; readvu v from f, 'p1', 1 on error oc = 'error' locked oc = 'locked' else oc = 'else'
   crt 'Y6 READVU p1 branch=':oc:' STATUS()=':status():' value=[':v:']'
   release
   crt 'YZ done'
end
EOP
prog zzwn4 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then' ; clearfile f on error oc = 'error'
   crt 'Y7 CLEARFILE branch=':oc:' STATUS()=':status()
   close f
end
EOP
# zzwnla / zzwnlb: two sessions and one lock.  The holder keeps lk1 for 12 seconds; B takes it with the LOCKED clause, then waits for it with a plain READU
prog zzwnla <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   readu r from f, 'lk1' on error crt 'READU ERROR st=':status() ; stop else crt 'READU ELSE' ; stop
   crt 'A ':oconv(time(), 'MTS'):' holds lk1 (remote)'
   sleep 12
   release f, 'lk1'
   crt 'A ':oconv(time(), 'MTS'):' released lk1'
   close f
end
EOP
prog zzwnlb <<'EOP'
   fid = downcase(field(trim(@sentence), ' ', 4))
   if fid = '' then crt 'NO RECORD ID GIVEN' ; stop
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then'
   readu r from f, fid on error oc = 'error' locked oc = 'locked' else oc = 'else'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' B1 READU ':fid:' LOCKED-clause branch=':oc:' STATUS()=':st:' record=[':change(r, @fm, '/'):']'
   oc = 'then'
   recordlocku f, fid on error oc = 'error' locked oc = 'locked'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' B3 RECORDLOCKU ':fid:' LOCKED-clause branch=':oc:' STATUS()=':st
   t1 = time()
   oc = 'then' ; r = ''
   readu r from f, fid on error oc = 'error' else oc = 'else'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' B2 plain READU ':fid:' returned branch=':oc:' STATUS()=':st:' record=[':change(r, @fm, '/'):'] waited ':(time() - t1):' s'
   release f, fid
   close f
end
EOP
prog zzwncl <<'EOP'
   open 'voc' to v else crt 'NO VOC' ; stop
   delete v, 'zzrc'
   delete v, 'zzrw'
   crt 'zzwncl done'
end
EOP
OUT=$(wl_sd_user "$CUSER" "compile the nine programs" \
  "BASIC bp zzwnmk" "BASIC bp zzwnrd" "BASIC bp zzwn1" "BASIC bp zzwn2" "BASIC bp zzwn3" "BASIC bp zzwn4" "BASIC bp zzwnla" "BASIC bp zzwnlb" "BASIC bp zzwncl")
expect_eq "S7 nine programs compiled with '0 error(s)'" "$(count_re "$OUT" '^0 error\(s\)')" 9

say ""; say "== S8. the client's stored login (set.netlogin) and the two VOC pointers =="
OUT=$(wl_sd_user "$CUSER" "set.netlogin $SRV" "SET.NETLOGIN $SRV" "$REMOTE" "$PWS")
MADE_NETLOGIN=1
expect_has "S8 'Your login on server $SRV as $REMOTE is stored.  The password is not stored'" "$OUT" "$(wl_msg 11477 "$SRV" "$REMOTE")"
MADE_VOC=1
OUT=$(wl_sd_user "$CUSER" "run zzwnmk (VOC pointers)" "RUN bp zzwnmk")
expect_has "S8 the pointer zzrc reads back as N / $SRV / zzcust" "$OUT" "pointer zzrc = [N / $SRV / zzcust]"
expect_has "S8 the pointer zzrw reads back as N / $SRV / zzwgf" "$OUT" "pointer zzrw = [N / $SRV / zzwgf]"
expect_has "S8 the program ran to its end" "$OUT" "zzwnmk done"
expect_lacks "S8 no VOC write was refused" "$OUT" "VOC WRITE REFUSED"

say ""; say "== S9. the two waits are listed by CONFIG (K8d) =="
OUT=$(wl_sd_admin "config" "CONFIG")
expect_re "S9 CONFIG lists NETWAIT in seconds (the default is 5)" "$OUT" '^NETWAIT +[1-9][0-9]* seconds'
expect_re "S9 CONFIG lists NETREPLY in seconds (the default is 30)" "$OUT" '^NETREPLY +[1-9][0-9]* seconds'

# ================================================================== R. read
say ""; say "== R. read through the pointer =="
AUD0=$(wl_audit_offset); L0=$(logins)
OUT=$(wl_sd_user "$CUSER" "queries through zzrc" "COUNT zzrc" "LIST zzrc name" "SORT zzrc BY name" "RUN bp zzwnrd")
expect_re "R1 COUNT counts the 3 records on the server" "$OUT" '^3 record\(s\) counted'
expect_re "R2 LIST lists 3 records" "$OUT" '^3 record\(s\) listed'
expect_has "R2 LIST shows Smith" "$OUT" "Smith"
wl_before "R3 SORT BY name puts c3 (Brown) before c2 (Jones)" "$OUT" "c3" "c2"
wl_before "R3 and c2 (Jones) before c1 (Smith)" "$OUT" "c2" "c1"
expect_has "R4 the data file opens" "$OUT" "data open ok"
expect_has "R4 a record reads (c1 holds Smith and 100)" "$OUT" "c1=[Smith/100]"
expect_has "R4 the dictionary opens" "$OUT" "dict open ok"
sleep 2
AUD=$(wl_audit_since "$AUD0")
expect_re "R5 the server's audit trail has a files-only login for $REMOTE (write=off)" "$AUD" "api login route=sdfiles write=off user=$REMOTE"
expect_lacks "R5 and no refusal: reading needs sdfiles alone" "$AUD" "api refused"
[ "$(logins)" -gt "$L0" ] && pass "R5 the number of login lines grew ($L0 -> $(logins))" || fail "R5 the number of login lines did not grow ($L0 -> $(logins)): the session never reached the server"

# ================================================================== A. files-on only
say ""; say "== A. files-on, no write group: every change or lock is refused by the SERVER =="
expect_eq "A0 the real groups: sdfiles only" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=0"
B_IDS=$(srvids zzwgf); AUD0=$(wl_audit_offset)
expect_eq "A0 the server file holds lk1 p1 p2 p3 before the runs" "$B_IDS" "lk1 p1 p2 p3 "
OUT1=$(wl_sd_user "$CUSER" "run zzwn1" "RUN bp zzwn1")
OUT2=$(wl_sd_user "$CUSER" "run zzwn2 (a write with no ON ERROR)" "RUN bp zzwn2")
POUT=$(sudo -u "$CUSER" python3 "$BK/probe.py" files "$HOST" "$PORT" "$REMOTE" "$BK/pw" "$REMOTE" zzwgf p1 2>&1 | tee /dev/stderr)
sleep 2
AUD=$(wl_audit_since "$AUD0")
F_IDS=$(srvids zzwgf)
say "  audit lines added by phase A:"; printf '%s\n' "$AUD" | grep -a -E 'api|netfile' | cut -c1-200 | sed -e 's/^/      | /'
expect_has "A1 NULL CASE: run 1 opened the remote file" "$OUT1" "X0 opened zzrw"
expect_has "A1 NULL CASE: run 1 reached its end" "$OUT1" "XZ done"
expect_has "A1 NULL CASE: the probe connected, opened and finished" "$POUT" "P DONE"
expect_re "A2 control X1: a READ works through the files-only login (record 'one')" "$OUT1" '^X1 READ p1 \(control\) branch=then STATUS\(\)=0 record=\[one\]'
expect_re "A2 control X8: a READV without a lock works" "$OUT1" '^X8 READV p3 .*branch=then STATUS\(\)=0 value=\[three\]'
for x in "X2 WRITE n1" "X3 WRITEU n2" "X4 DELETE p2" "X5 READU p3" "X6 RECORDLOCKU p3" "X7 READVU p3" "X9 CLEARFILE"; do
  expect_re "A3 $x refused: the ON ERROR branch, STATUS() 7000" "$OUT1" "^$x branch=error STATUS\(\)=7000"
done
expect_has "A4 K1: the person sees the server's own reason ($TXT_WRITE_REFUSED)" "$OUT2" "$(wl_msg 11500 "$SRV" write "$TXT_WRITE_REFUSED")"
expect_lacks "A4 K1: not the old 'status 0' text" "$OUT2" "answered write with an error: status"
expect_lacks "A4 and the program did not go on after the refused write" "$OUT2" "W9 REACHED"
for n in 7 8 9 10 16 17 18 19 30; do
  expect_has "A5 probe: request $n refused with the 11521 text" "$POUT" "$(wl_msg 11521 $n)"
done
expect_lacks "A5 probe: not the 11480 wording ('This login is for files only')" "$POUT" "This login is for files only"
expect_lacks "A5 probe control: request 6 (read) was not refused" "$POUT" "(request 6)"
expect_lacks "A5 probe control: request 15 (release) was not refused" "$POUT" "(request 15)"
for n in 16 17 18 30 31; do
  expect_has "A6 server audit: api refused request=$n route=sdfiles write=off user=$REMOTE (from the netfile run)" "$AUD" "api refused request=$n route=sdfiles write=off user=$REMOTE"
done
for n in 7 8 9 10 19; do
  expect_has "A6 server audit: api refused request=$n (only the probe sends it)" "$AUD" "api refused request=$n route=sdfiles write=off user=$REMOTE"
done
expect_lacks "A6 server audit: no write=on line in this phase" "$AUD" "write=on"
expect_lacks "A6 server audit: request 6 and 15 are never refused" "$AUD" "api refused request=6 "
expect_lacks "A6 server audit: ... nor 15" "$AUD" "api refused request=15 "
[ "$(count_re "$AUD" "api login route=sdfiles write=off user=$REMOTE")" -ge 3 ] && pass "A6 server audit: at least three logins say write=off (two netfile runs and the probe)" || fail "A6 fewer than three 'api login route=sdfiles write=off' lines"
if printf '%s\n' "$AUD" | grep -a -q -E '^[0-9: -]+ user=[A-Za-z0-9_-]+( sudo=[A-Za-z0-9_-]+)? uid=[0-9]+ pid=[0-9]+ (api|netfile) '; then
  if printf '%s\n' "$AUD" | grep -a -q -E '^[0-9: -]+ user=[A-Za-z0-9_-]+( sudo=[A-Za-z0-9_-]+)? uid=[0-9]+ pid=[0-9]+ (api|netfile) [^=]*[A-Z]'; then fail "A6 server audit: an upper-case letter in an event word"; else pass "A6 server audit: the event words of the api and netfile lines are lower case"; fi
else fail "A6 server audit: no api or netfile line to judge (the null case)"; fi
expect_eq "A7 the server file did not change (still lk1 p1 p2 p3: no n1 n2 n3, no probe write)" "$F_IDS" "$B_IDS"

# ================================================================== M. mode and pin
say ""; say "== M. the definition says READ; then a wrong pin =="
OUT=$(defs "$PIN" READ)
expect_re "M0 the definition now says read" "$OUT" "^$SRV +$HOST:$PORT +$REMOTE/read +"
AUD0=$(wl_audit_offset)
OUT=$(wl_sd_user "$CUSER" "run zzwn2 under READ" "RUN bp zzwn2")
sleep 2; AUD=$(wl_audit_since "$AUD0")
expect_has "M1 the client refused the write before sending it (11501)" "$OUT" "$(wl_msg 11501 "$SRV" write)"
expect_lacks "M1 the program did not go on" "$OUT" "W9 REACHED"
expect_lacks "M1 nothing was refused by the server (no api refused line): the client never sent the write" "$AUD" "api refused"
BAD=$(printf 'f%.0s' $(seq 1 64))
OUT=$(defs "$BAD" WRITE)
expect_re "M2 the definition holds the wrong pin (ffff...)" "$OUT" "^$SRV +$HOST:$PORT +$REMOTE/write +ffffffffffffffff\.\.\. "
L0=$(logins); AUD0=$(wl_audit_offset)
OUT=$(wl_sd_user "$CUSER" "run zzwnrd under the WRONG pin" "RUN bp zzwnrd")
sleep 2; AUD=$(wl_audit_since "$AUD0")
expect_has "M2 the stored login is refused because the key differs (11455)" "$OUT" "$(wl_msg 11455 "$SRV")"
expect_lacks "M2 the program did not reach the data" "$OUT" "data open ok"
expect_eq "M2 the server saw no new login: nothing was sent (login lines $L0 before)" "$(logins)" "$L0"
expect_lacks "M2 and no refusal on the server either" "$AUD" "api refused"
OUT=$(defs "$PIN" WRITE)
expect_re "M3 the right pin is back (mode write)" "$OUT" "^$SRV +$HOST:$PORT +$REMOTE/write +$SHORT\.\.\. +$CLIENT *\$"

# ================================================================== B. files-write-on
say ""; say "== B. MODIFY.ACCOUNT $REMOTE FILES-WRITE-ON =="
OUT=$(wl_sd_admin "files-write-on" "MODIFY.ACCOUNT $REMOTE FILES-WRITE-ON")
expect_has "B1 the line says files-write yes" "$OUT" "$(wl_msg 11522 "$REMOTE" yes)"
expect_eq "B1 the real groups: both" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=1"
reseed
B_IDS=$(srvids zzwgf); AUD0=$(wl_audit_offset)
expect_eq "B2 reseeded: the server file holds lk1 p1 p2 p3" "$B_IDS" "lk1 p1 p2 p3 "
OUT3=$(wl_sd_user "$CUSER" "run zzwn3" "RUN bp zzwn3")
MID_IDS=$(srvids zzwgf)
N1=$(wl_sd_user "$REMOTE" "CT zzwgf n1" "CT zzwgf n1"); N2=$(wl_sd_user "$REMOTE" "CT zzwgf n2" "CT zzwgf n2")
POUT=$(sudo -u "$CUSER" python3 "$BK/probe.py" files "$HOST" "$PORT" "$REMOTE" "$BK/pw" "$REMOTE" zzwgf p3 2>&1 | tee /dev/stderr)
PRB_IDS=$(srvids zzwgf)
OUT4=$(wl_sd_user "$CUSER" "run zzwn4 (clearfile)" "RUN bp zzwn4")
CLR_CNT=$(wl_sd_user "$REMOTE" "COUNT zzwgf after the clear" "COUNT zzwgf")
sleep 2; AUD=$(wl_audit_since "$AUD0")
say "  audit lines added by phase B:"; printf '%s\n' "$AUD" | grep -a -E 'api|netfile' | cut -c1-200 | sed -e 's/^/      | /'
expect_has "B3 NULL CASE: zzwn3 ran to its end" "$OUT3" "YZ done"
expect_has "B3 NULL CASE: zzwn4 printed its line" "$OUT4" "Y7 CLEARFILE"
expect_has "B3 NULL CASE: the probe finished" "$POUT" "P DONE"
for y in "Y1 WRITE n1" "Y2 WRITEU n2" "Y3 DELETE p2" "Y5 RECORDLOCKU p1"; do
  expect_re "B4 $y now succeeds" "$OUT3" "^$y branch=then STATUS\(\)=0"
done
expect_re "B4 Y4 READU p3 now succeeds and reads 'three'" "$OUT3" '^Y4 READU p3 branch=then STATUS\(\)=0 record=\[three\]'
expect_re "B4 Y6 READVU p1 now succeeds (value 'one')" "$OUT3" '^Y6 READVU p1 branch=then STATUS\(\)=0 value=\[one\]'
expect_eq "B5 SERVER evidence: after zzwn3 the file holds lk1 n1 n2 p1 p3 and NOT p2" "$MID_IDS" "lk1 n1 n2 p1 p3 "
expect_re "B5 n1 holds 'viaremote'" "$N1" '^1: viaremote *$'
expect_re "B5 n2 holds 'viaremoteu'" "$N2" '^1: viaremoteu *$'
for n in 7 8 9 10 16 17 18 19 30; do expect_lacks "B6 probe: request $n is no longer refused" "$POUT" "(request $n)"; done
case " $PRB_IDS " in *" p3-w "*) pass "B7 SERVER evidence: the probe's SDWrite made p3-w" ;; *) fail "B7 p3-w is not on the server (got: $PRB_IDS)" ;; esac
case " $PRB_IDS " in *" p3-wu "*) pass "B7 SERVER evidence: the probe's SDWriteu made p3-wu" ;; *) fail "B7 p3-wu is not on the server (got: $PRB_IDS)" ;; esac
case " $PRB_IDS " in *" p3 "*) fail "B7 p3 is still on the server: the probe's deletes did nothing" ;; *) pass "B7 SERVER evidence: the probe's deletes removed p3" ;; esac
expect_re "B8 Y7 CLEARFILE now succeeds" "$OUT4" '^Y7 CLEARFILE branch=then STATUS\(\)=0'
expect_re "B8 SERVER evidence: the file holds 0 records afterwards (COUNT as the server's own user)" "$CLR_CNT" '^0 record\(s\) counted'
[ "$(count_re "$AUD" "api login route=sdfiles write=on user=$REMOTE")" -ge 3 ] && pass "B9 audit: at least three logins say write=on" || fail "B9 audit: fewer than three 'api login route=sdfiles write=on' lines"
expect_lacks "B9 audit: NO api refused line in phase B" "$AUD" "api refused"
expect_lacks "B9 audit: no write=off login in phase B" "$AUD" "route=sdfiles write=off"
expect_has "B9 audit: the client's own lines for the write, the delete and the clear" "$AUD" "netfile write server=$SRV file=zzwgf"
expect_has "B9 audit: ... delete" "$AUD" "netfile delete server=$SRV file=zzwgf"
expect_has "B9 audit: ... clear" "$AUD" "netfile clear server=$SRV file=zzwgf"

say ""; say "== B10. two sessions, one lock: A holds lk1 on the server for 12 s; B takes it with LOCKED, then waits =="
reseed
HO="$BK/lock-holder.out"; BO="$BK/lock-b.out"
( cd / && printf '\nTERM 200,9999\nRUN bp zzwnla\nOFF\n' | timeout 100 sudo -u "$CUSER" "$WL_SD" 2>&1 | strip > "$HO" ) &
HP=$!
sleep 4
( cd / && printf '\nTERM 200,9999\nRUN bp zzwnlb lk1\nOFF\n' | timeout 100 sudo -u "$CUSER" "$WL_SD" 2>&1 | strip > "$BO" ) &
BP=$!
sleep 3
LK=$(wl_sd_admin "list.readu while A holds the lock" "LIST.READU" | grep -a -i -E 'lk1' | head -1)
HUN=$(printf '%s' "$LK" | awk '{print $1}')
wait "$HP" "$BP"
say "  holder session:"; grep -a -E '^A ' "$HO" | cut -c1-120 | sed -e 's/^/      | /'
say "  session B:"; grep -a -E '^B |FAILED|ERROR' "$BO" | cut -c1-200 | sed -e 's/^/      | /'
say "  the server's lock table row for lk1: [$(printf '%s' "$LK" | tr -s ' ' | cut -c1-90)]   holder user number: [$HUN]"
HOT=$(cat "$HO" 2>/dev/null); BOT=$(cat "$BO" 2>/dev/null)
expect_has "B10 NULL CASE: the holder held the lock" "$HOT" "holds lk1 (remote)"
expect_re "B10 B1 took the LOCKED branch (not then, else or error) and read nothing" "$BOT" 'B1 READU lk1 LOCKED-clause branch=locked STATUS\(\)=[0-9-]+ record=\[\]'
[ -n "$HUN" ] && expect_re "B10 B1's STATUS() is the holder's user number in the server's lock table ($HUN)" "$BOT" "B1 READU lk1 LOCKED-clause branch=locked STATUS\(\)=$HUN record" || fail "B10 the lock table showed no holder for lk1 (the null case): the user number cannot be compared"
[ -n "$HUN" ] && expect_re "B10 B3 RECORDLOCKU also took the LOCKED branch with the same holder" "$BOT" "B3 RECORDLOCKU lk1 LOCKED-clause branch=locked STATUS\(\)=$HUN" || fail "B10 B3 cannot be compared (no holder)"
expect_re "B10 B2 plain READU waited for the release (3 s or more) and then got the record" "$BOT" 'B2 plain READU lk1 returned branch=then STATUS\(\)=0 record=\[lock me\] waited ([3-9]|1[0-9]) s'

# ================================================================== C. taking the group away again
say ""; say "== C. files-write-off, files-off, files-on - and the manifest key at each step =="
reseed
B_IDS=$(srvids zzwgf)
expect_eq "C0 reseeded: the server file holds lk1 p1 p2 p3" "$B_IDS" "lk1 p1 p2 p3 "
R_ON=$(wl_backup_routes "$REMOTE" "$BK/bak1")
expect_re "C1 manifest while write is on: route.files: 1 route.files.write: 1" "$R_ON" "\[account $REMOTE\] route\.files: 1 route\.files\.write: 1"

OUT=$(wl_sd_admin "files-write-off" "MODIFY.ACCOUNT $REMOTE FILES-WRITE-OFF")
expect_has "C2 the line says files-write no" "$OUT" "$(wl_msg 11522 "$REMOTE" no)"
expect_eq "C2 the real groups: sdfiles kept, write gone" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=0"
OUT2=$(wl_sd_user "$CUSER" "run zzwn2 after files-write-off" "RUN bp zzwn2")
POUT=$(sudo -u "$CUSER" python3 "$BK/probe.py" files "$HOST" "$PORT" "$REMOTE" "$BK/pw" "$REMOTE" zzwgf p1 2>&1 | tee /dev/stderr)
expect_has "C2 a netfile write is refused again with the 11521 text" "$OUT2" "$TXT_WRITE_REFUSED"
expect_has "C2 a direct write (16) is refused again" "$POUT" "$(wl_msg 11521 16)"
expect_has "C2 NULL CASE: the probe connected and opened before it was refused" "$POUT" "P OPEN ok"
expect_eq "C2 the server file is unchanged by the refused tries" "$(srvids zzwgf)" "$B_IDS"
R_OFF=$(wl_backup_routes "$REMOTE" "$BK/bak2")
expect_re "C2 manifest after files-write-off: route.files: 1 route.files.write: 0" "$R_OFF" "\[account $REMOTE\] route\.files: 1 route\.files\.write: 0"

OUT=$(wl_sd_admin "files-write-on again, then files-off" "MODIFY.ACCOUNT $REMOTE FILES-WRITE-ON" "MODIFY.ACCOUNT $REMOTE FILES-OFF")
expect_has "C3 files-write-on put the group back" "$OUT" "$(wl_msg 11522 "$REMOTE" yes)"
expect_has "C3 files-off says the write group is out ..." "$OUT" "$(wl_msg 11522 "$REMOTE" no)"
expect_has "C3 ... and that the files route is out" "$OUT" "$(wl_msg 11482 "$REMOTE" no)"
wl_before "C3 the write group is reported out BEFORE sdfiles" "$OUT" "$(wl_msg 11522 "$REMOTE" no)" "$(wl_msg 11482 "$REMOTE" no)"
expect_eq "C3 the real groups: neither" "$(wl_state "$REMOTE")" "sdfiles=0 sdfileswrite=0"
AUD0=$(wl_audit_offset)
OUT3=$(wl_sd_user "$CUSER" "run zzwnrd after files-off" "RUN bp zzwnrd")
POUT=$(sudo -u "$CUSER" python3 "$BK/probe.py" files "$HOST" "$PORT" "$REMOTE" "$BK/pw" "$REMOTE" zzwgf p1 2>&1 | tee /dev/stderr)
sleep 2; AUD=$(wl_audit_since "$AUD0")
expect_has "C3 the netfile open is refused ($REMOTE is not permitted to use the API, 10073)" "$OUT3" "$(wl_msg 10073 "$REMOTE")"
expect_has "C3 the direct login is refused: the probe could not connect" "$POUT" "P CONNECT FAILED"
expect_has "C3 K3: the server's audit says why (api refused user=$REMOTE reason=not a member of sdapi or sdfiles)" "$AUD" "api refused user=$REMOTE reason=not a member of sdapi or sdfiles"
R_NO=$(wl_backup_routes "$REMOTE" "$BK/bak3")
expect_re "C3 manifest after files-off: route.files: 0 route.files.write: 0" "$R_NO" "\[account $REMOTE\] route\.files: 0 route\.files\.write: 0"

OUT=$(wl_sd_admin "files-on" "MODIFY.ACCOUNT $REMOTE FILES-ON")
expect_has "C4 K2: 'Account $REMOTE has files yes'" "$OUT" "$(wl_msg 11482 "$REMOTE" yes)"
expect_eq "C4 files-on gave sdfiles back and did NOT give the write group back" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=0"
OUT2=$(wl_sd_user "$CUSER" "run zzwn2 after files-on" "RUN bp zzwn2")
expect_has "C4 a netfile write is refused again" "$OUT2" "$TXT_WRITE_REFUSED"
R_BACK=$(wl_backup_routes "$REMOTE" "$BK/bak4")
expect_re "C4 manifest after files-on: route.files: 1 route.files.write: 0" "$R_BACK" "\[account $REMOTE\] route\.files: 1 route\.files\.write: 0"

# ================================================================== the end: cleanup() makes the Z rows and the summary
say ""
say "== the rows above are complete; putting back (Z rows follow) =="
cleanup
