#!/usr/bin/env bash
#
# witness-sdnet-two-machines.sh - SDNet between TWO real machines.  (K6e, 19 Oct 2026; the S.65 finish.)  Run it on both: the server first, then the client, then the server again.
#
#   SERVER   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-two-machines.sh --role server-setup [--account NAME] [--port N]
#   CLIENT   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-two-machines.sh --role client --host ADDRESS --server-hash HEX64 [--server-epoch N] [--pwfile FILE] [--account NAME] [--port N] [--client ACCOUNT]
#   SERVER   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-two-machines.sh --role server-check
#   SERVER   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-two-machines.sh --role server-teardown
#   either   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-two-machines.sh --selftest        (no sudo, no sd: the helpers on known texts)
# (On the second machine the path is wherever that machine's checkout is; the script names itself by absolute path in every command it prints, so copy those.)
#
# ***NEEDS sudo*** on both machines, from the owner's login (SUDO_USER must name a person).  BOTH machines need a full SD Core for Linux install of the CURRENT build (the plan's
# candidates are the Debian 13, Fedora 44 and Ubuntu 26 VMs; the Solo VMs are not Core), on a host-only or internal network, set up from VMs that are STOPPED (the
# systemd-run recipe in the memory file; never run VBoxManage from the app shell with no VM running).  Linux Solo with Linux Solo is a separate, later witness.
#
# WHAT ONLY TWO MACHINES ADD (every earlier real-install run was ONE machine talking to itself on 127.0.0.1:4247 - the S.65 row, K6e):
#   * a TCP login between hosts, through whatever sits between them (a firewall, a NAT: C1 says whether the port is reachable at all);
#   * TWO DIFFERENT PINS: the hash the client's connection sees equals the one the server printed, and a definition with the wrong pin is refused by the client's own
#     dial before anything is sent (11471);
#   * the SCRAM login with its channel binding across a real network (the loopback runs showed the positive case only; netfake.py does not check the binding, so the
#     NEGATIVE case - a client talking to a machine that is not the one pinned - is shown by the wrong-pin row, not by the binding);
#   * two clocks: both epochs are printed and the skew is shown.  It is information, not a verdict: SD pins a key, it does not check a certificate's dates.
#
# WHAT EACH ROLE CHANGES (and puts back):
#   server-setup    MAKES the SD account NAME (default zzwtwo) with its Linux user, the files route AND the write group, and a file zzwfile of three records; writes the account's
#                   password to /var/tmp/witness-sdnet-two-machines.pw (mode 0600, yours) for you to carry to the client by scp - the script never prints it.
#   client          DEFINES the server zzremote, the client's stored login and one VOC pointer, turns on the client account's NET, VOC and BP gates (it saves the register
#                   record first) and writes three programs zzwt* into the client's bp.  At the end it takes ALL of that away and puts the register record back.
#   server-check    reads what the client did to the server (the record the client wrote, the audit lines) - read only.
#   server-teardown DELETES the account (DELETE.ACCOUNT, userdel -r, its home) and the password file.
# It does not install and does not uninstall.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-two-machines-<time>.<six random characters>.log on each machine.
# Changed 19 Oct 26 (finish 2, the verifier's findings): the password file is created exclusively and a planted link is DIRTY; the state and backup directories are made with wl_mkdir_new (no
# directory that somebody else made first in /var/tmp is used); row Z1 compares the restored register record with its checksum, owner and mode worked out BEFORE the copy was taken.
#
set -u
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
HERE=$(dirname "$SELF")
# shellcheck source=witness-sdnet-lib.sh
. "$HERE/witness-sdnet-lib.sh" || { echo "CANNOT RUN: no witness-sdnet-lib.sh beside $SELF"; exit 2; }

if [ "${1:-}" = "--selftest" ]; then wl_selftest; exit $?; fi
wl_logged "$SELF" witness-sdnet-two-machines "$@"
shift                                   # the "--logged" the re-exec added

ROLE=""; ACC=zzwtwo; PORT=4247; HOST=""; SHASH=""; SEPOCH=""; PWFILE=$WL_TMP/witness-sdnet-two-machines.pw; CLIENT=""
while [ $# -gt 0 ]; do
  case $1 in
    --role)         [ $# -ge 2 ] || need "--role needs a value"; ROLE=$2; shift 2 ;;
    --account)      [ $# -ge 2 ] || need "--account needs a name"; ACC=$2; shift 2 ;;
    --port)         [ $# -ge 2 ] || need "--port needs a number"; PORT=$2; shift 2 ;;
    --host)         [ $# -ge 2 ] || need "--host needs an address"; HOST=$2; shift 2 ;;
    --server-hash)  [ $# -ge 2 ] || need "--server-hash needs the 64 hex digits the server printed"; SHASH=$2; shift 2 ;;
    --server-epoch) [ $# -ge 2 ] || need "--server-epoch needs a number"; SEPOCH=$2; shift 2 ;;
    --pwfile)       [ $# -ge 2 ] || need "--pwfile needs a file"; PWFILE=$2; shift 2 ;;
    --client)       [ $# -ge 2 ] || need "--client needs an account"; CLIENT=$2; shift 2 ;;
    *) need "unknown argument '$1'" ;;
  esac
done
case $ACC in *[!a-z0-9]*|'') need "--account must be lower case letters and digits" ;; esac
case $PORT in *[!0-9]*|'') need "--port must be a number" ;; esac
case $ROLE in server-setup|client|server-check|server-teardown) ;; *) need "--role server-setup | client | server-check | server-teardown" ;; esac

STAMP=$(date +%Y%m%dT%H%M%S)
SRV=zzremote
STATE_DIR=$WL_TMP/witness-sdnet-two-machines.d
SERVER_STATE=$STATE_DIR/server.state
say "witness-sdnet-two-machines.sh --role $ROLE  $STAMP"
say "  script  : $SELF"
say "  sudo    : $SUDO_USER (the owner)   machine: $(hostname 2>/dev/null)   account: $ACC   port: $PORT"
say "  install : $(wl_commit_stamp)"
say "  sd      : $WL_SD   $(timeout 20 "$WL_SD" --version 2>&1 | head -1)"

CLEANED=0
[ -x "$WL_SD" ] || need "$WL_SD is not installed - run the installer first"
count_re() { local n; n=$(printf '%s\n' "$1" | grep -a -c -E -- "$2"); printf '%s' "${n:-0}"; }

# ====================================================================================================== SERVER SETUP
if [ "$ROLE" = server-setup ]; then
  for g in sdfiles sdfileswrite sdusers; do wl_group_exists "$g" || need "no Linux group $g on this machine (install from a tree that makes it)"; done
  command -v ss >/dev/null 2>&1 || need "ss is not installed"
  grep -q 'cannot change or lock files here' "$WL_SDSYS/messages/11521" 2>/dev/null || need "the installed message 11521 is not the K1 text: this install predates the S.65 finish (19 Oct 2026)"
  [ -x "$WL_ELEVATE" ] || need "$WL_ELEVATE is not installed"
  [ -r "$WL_AUDIT" ] || need "the audit file $WL_AUDIT cannot be read"
  DIRTY=0
  [ -e "$WL_SDSYS/accounts/$ACC" ] && { say "  DIRTY: register record $ACC exists"; DIRTY=1; }
  id -u "$ACC" >/dev/null 2>&1 && { say "  DIRTY: Linux user $ACC exists"; DIRTY=1; }
  wl_group_exists "sdu_$ACC" && { say "  DIRTY: group sdu_$ACC exists"; DIRTY=1; }
  [ -d "/home/$ACC" ] && { say "  DIRTY: /home/$ACC exists"; DIRTY=1; }
  [ -d "/home/sd/user_accounts/$ACC" ] && { say "  DIRTY: /home/sd/user_accounts/$ACC exists"; DIRTY=1; }
  [ -e "$STATE_DIR" ] || [ -L "$STATE_DIR" ] && { say "  DIRTY: $STATE_DIR exists (a previous run: run --role server-teardown first)"; DIRTY=1; }
  [ -e "$PWFILE" ] || [ -L "$PWFILE" ] && { say "  DIRTY: $PWFILE exists (a previous run, or somebody else's file: remove it, or give --pwfile another name)"; DIRTY=1; }
  [ "$DIRTY" -eq 0 ] || need "the ground is not clear (above): this script will not touch state it did not create"
  OUT=$(wl_sd_admin "list.servers (does an sd session as sdsys work?)" "LIST.SERVERS")
  [ -n "$OUT" ] || need "LIST.SERVERS printed nothing: an sd session as sdsys does not work here (is sd.service running?)"
  wl_mkdir_new "$STATE_DIR" 700
  printf 'account=%s\nstarted=%s\naudit_offset=%s\n' "$ACC" "$(date '+%Y-%m-%d %H:%M:%S')" "$(wl_audit_offset)" > "$SERVER_STATE"
  PWO=$(wl_newpw); PWS=$(wl_newpw); WL_SECRETS=("$PWO" "$PWS")

  say ""; say "== SS1. the listener: the client must be able to reach it =="
  LISTEN=$(ss -ltnH "sport = :$PORT" 2>/dev/null | tee /dev/stderr)
  [ -n "$LISTEN" ] && pass "SS1 something is listening on port $PORT" || fail "SS1 nothing is listening on port $PORT (is the API server on?)"
  if printf '%s\n' "$LISTEN" | grep -q -E '(^|[[:space:]])(0\.0\.0\.0|\*|\[::\]|::):'"$PORT"; then pass "SS1 it is bound to every address (a client on another machine can reach it)"
  else fail "SS1 it is not bound to every address (the line above): a client on another machine cannot reach it"; fi

  say ""; say "== SS2. the account, with the files route and the write group =="
  OUT=$(wl_sd_admin "create.account $ACC" "CREATE.ACCOUNT USER $ACC FILES-ON" "$PWO" "$PWO")
  [ -e "$WL_SDSYS/accounts/$ACC" ] && pass "SS2 the register record exists" || fail "SS2 no register record for $ACC"
  id -u "$ACC" >/dev/null 2>&1 && pass "SS2 the Linux user exists" || fail "SS2 no Linux user $ACC"
  [ -e "$WL_SDSYS/accounts/$ACC" ] || { wl_summary; exit 2; }
  OUT=$(wl_sd_admin "modify.password $ACC" "MODIFY.PASSWORD $ACC" "$PWS" "$PWS")
  expect_has "SS2 'Password accepted.'" "$OUT" "Password accepted."
  OUT=$(wl_sd_admin "files-write-on" "MODIFY.ACCOUNT $ACC FILES-WRITE-ON")
  expect_has "SS2 the line says files-write yes" "$OUT" "$(wl_msg 11522 "$ACC" yes)"
  expect_eq "SS2 the real groups: both" "$(wl_state "$ACC")" "sdfiles=1 sdfileswrite=1"
  OUT=$(wl_sd_user "$ACC" "seed zzwfile" "CREATE.FILE zzwfile DYNAMIC" "ED zzwfile t1" "I Smith" "I 100" "FI" "ED zzwfile t2" "I Jones" "I 50" "FI" "ED zzwfile t3" "I Brown" "I 75" "FI" "COUNT zzwfile")
  expect_re "SS2 zzwfile holds 3 records" "$OUT" '^3 record\(s\) counted'

  say ""; say "== SS3. the password file for the client =="
  # created EXCLUSIVELY (set -C: O_EXCL, which refuses a file that is there and a link, even a dangling one) in a directory every user can write into, by a script that runs as root and
  # chowns it: a link planted at this predictable name would otherwise have had its target overwritten and handed to the owner (verifier finding of 19 Oct 2026)
  ( umask 077; set -C; : > "$PWFILE" ) && chown "$SUDO_USER" "$PWFILE" && chmod 600 "$PWFILE" && printf '%s\n' "$PWS" > "$PWFILE" || need "cannot create $PWFILE (it is there already, or the directory is not writable)"
  pass "SS3 the password is in $PWFILE (mode 0600, owner $SUDO_USER): copy it to the client machine, same path, mode 0600, with scp from your login. It is not printed here."

  say ""; say "== SS4. THE FACTS THE CLIENT NEEDS (type them, or read them off this screen: the hash must come to the client by a way that does not use the network under test) =="
  TLSKEY=$("$WL_ELEVATE" tls-key 2>&1 | tee /dev/stderr | sed -n 's/^public key sha256: //p')
  expect_re "SS4 the public key hash is 64 lower case hex digits" "$TLSKEY" '^[0-9a-f]{64}$'
  say "      server hash : $TLSKEY"
  say "      server epoch: $(date -u +%s)   ($(date -u '+%Y-%m-%d %H:%M:%S') UTC)"
  say "      addresses   : $(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | tr '\n' ' ')"
  say "      host name   : $(hostname 2>/dev/null)"
  command -v ufw >/dev/null 2>&1 && say "      ufw         : $(ufw status 2>&1 | head -3 | tr '\n' ' ')"
  command -v nft >/dev/null 2>&1 && say "      nft         : $(nft list ruleset 2>&1 | head -3 | tr '\n' ' ')"
  say ""
  say "  NEXT, on the CLIENT machine (the account '$ACC' is the server's; --client is the account there that will use it, default the owner's):"
  say "      sudo bash $SELF --role client --host <ADDRESS above> --server-hash $TLSKEY --server-epoch <epoch above>"
  say "  then, here:  sudo bash $SELF --role server-check      and at the very end:  sudo bash $SELF --role server-teardown"
  wl_summary; exit $?
fi

# ====================================================================================================== SERVER CHECK
if [ "$ROLE" = server-check ]; then
  [ -r "$SERVER_STATE" ] || need "no $SERVER_STATE: run --role server-setup first"
  ACC=$(sed -n 's/^account=//p' "$SERVER_STATE"); OFF=$(sed -n 's/^audit_offset=//p' "$SERVER_STATE"); STARTED=$(sed -n 's/^started=//p' "$SERVER_STATE")
  [ -n "$ACC" ] && [ -n "$OFF" ] || need "$SERVER_STATE is half written"
  say "  account $ACC, state saved $STARTED, audit offset $OFF"
  AUD=$(wl_audit_since "$OFF")
  say "  audit lines since the setup (api):"; printf '%s\n' "$AUD" | grep -a -E 'api' | cut -c1-200 | sed -e 's/^/      | /'
  expect_re "SC1 the server's audit trail has a files-only login of $ACC with write=on (the client's login arrived)" "$AUD" "api login route=sdfiles write=on user=$ACC"
  expect_lacks "SC2 and no refusal of a request (the client asked only for what the account may do)" "$AUD" "api refused request="
  OUT=$(wl_sd_user "$ACC" "the records the client left" "CT zzwfile t4" "CT zzwfile t1")
  expect_re "SC3 the record t4 the CLIENT wrote is here, with its text (a write that came over the network)" "$OUT" '^1: from the client *$'
  expect_re "SC3 the record t1 is as it was" "$OUT" '^1: Smith *$'
  SOCK=$(ss -tnH state established "sport = :$PORT" 2>/dev/null | wc -l)
  expect_eq "SC4 no connection to port $PORT is left open by the client's run" "$SOCK" "0"
  AW=$(python3 "$HERE/verify-auditwords.py" --file "$WL_AUDIT" --since "$STARTED" 2>&1); AWRC=$?     # not "| tee": a pipe inside $( ) would give the status of tee
  printf '%s\n' "$AW" >&2
  expect_eq "SC5 verify-auditwords exits 0 over the records since the setup" "$AWRC" "0"
  wl_summary; exit $?
fi

# ====================================================================================================== SERVER TEARDOWN
if [ "$ROLE" = server-teardown ]; then
  [ -r "$SERVER_STATE" ] || need "no $SERVER_STATE: nothing of a --role server-setup run is recorded here (nothing to take away)"
  ACC=$(sed -n 's/^account=//p' "$SERVER_STATE")
  [ -n "$ACC" ] || need "$SERVER_STATE has no account"
  say "  taking away the account $ACC that --role server-setup made"
  if [ -e "$WL_SDSYS/accounts/$ACC" ]; then wl_sd_admin "delete.account $ACC" "DELETE.ACCOUNT $ACC" "y" >/dev/null; fi
  if id -u "$ACC" >/dev/null 2>&1; then userdel -r "$ACC" >/dev/null 2>&1 && say "  userdel -r $ACC: done" || say "  userdel -r $ACC: FAILED - remove it by hand"; fi
  if ! id -u "$ACC" >/dev/null 2>&1 && [ -d "/home/$ACC" ]; then rm -rf -- "/home/$ACC" && say "  removed /home/$ACC (DELETE.ACCOUNT keeps a home; setup made it)"; fi
  rm -f -- "$PWFILE"
  left=""
  [ -e "$WL_SDSYS/accounts/$ACC" ] && left="$left register"
  id -u "$ACC" >/dev/null 2>&1 && left="$left user"
  wl_group_exists "sdu_$ACC" && left="$left group"
  [ -d "/home/$ACC" ] && left="$left home"
  [ -d "/home/sd/user_accounts/$ACC" ] && left="$left account-dir"
  [ -e "$PWFILE" ] && left="$left pwfile"
  if [ -z "$left" ]; then pass "ST1 nothing of $ACC is left (register, user, group, home, account directory, password file)"; else fail "ST1 left behind for $ACC:$left - remove by hand"; fi
  wl_in_group "$ACC" sdfiles && fail "ST2 $ACC is still listed in sdfiles" || pass "ST2 $ACC is not in sdfiles"
  wl_in_group "$ACC" sdfileswrite && fail "ST3 $ACC is still listed in sdfileswrite" || pass "ST3 $ACC is not in sdfileswrite"
  rm -rf -- "$STATE_DIR"
  wl_summary; exit $?
fi

# ====================================================================================================== CLIENT
[ -n "$HOST" ] || need "--host ADDRESS is needed (the address the server's setup printed)"
case $HOST in *[!A-Za-z0-9.:-]*) need "--host must be an address or a name" ;; esac
case $SHASH in [0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;; *) need "--server-hash needs the 64 lower case hex digits the server printed" ;; esac
[ "${#SHASH}" -eq 64 ] || need "--server-hash must be exactly 64 hex digits"
case $SHASH in *[!0-9a-f]*) need "--server-hash must be lower case hex" ;; esac
[ -n "$CLIENT" ] || CLIENT=$SUDO_USER
[ -r "$PWFILE" ] || need "no $PWFILE: copy the password file from the server (scp, from your login, mode 0600, same path) - see the setup's SS3"
PWS=$(head -1 "$PWFILE"); [ -n "$PWS" ] || need "$PWFILE is empty"
WL_SECRETS=("$PWS")
command -v openssl >/dev/null 2>&1 || need "openssl is not installed (the TLS rows need its s_client)"
grep -q 'cannot change or lock files here' "$WL_SDSYS/messages/11521" 2>/dev/null || need "the installed message 11521 is not the K1 text: this install predates the S.65 finish (19 Oct 2026)"
CUSER=$(wl_account_user "$CLIENT")
[ -n "$CUSER" ] || need "the register record of account '$CLIENT' is not a user account: give --client ACCOUNT"
id "$CUSER" >/dev/null 2>&1 || need "no Linux user '$CUSER'"
CDIR=$(wl_account_path "$CLIENT")
[ -n "$CDIR" ] && [ -d "$CDIR/bp" ] || need "the client account's directory '$CDIR' has no bp file"
OUT=$(wl_sd_admin "list.servers (is $SRV free?)" "LIST.SERVERS")
[ -n "$OUT" ] || need "LIST.SERVERS printed nothing: an sd session as sdsys does not work here (is sd.service running?)"
printf '%s\n' "$OUT" | grep -a -q -E "^$SRV[[:space:]]" && need "a server named $SRV is already defined: this script will not touch state it did not create"
PROGS="zzwtmk zzwtrw zzwtcl"
for p in $PROGS; do [ -e "$CDIR/bp/$p" ] && need "$CDIR/bp/$p exists: this script will not touch state it did not create"; done
BK=$WL_TMP/witness-sdnet-two-machines-$STAMP.d
wl_mkdir_new "$BK" 755
# What the restore at the end is judged against is worked out from the LIVE record BEFORE the copy is taken (its checksum, its owner and group and its mode), not from the copy: a row that
# compared the copy with the file it had just been copied onto could only fail if cp failed (verifier finding of 19 Oct 2026).
REG_SUM=$(sha256sum -- "$WL_SDSYS/accounts/$CLIENT" | cut -d' ' -f1)
REG_ATTR=$(stat -c '%U:%G %a' -- "$WL_SDSYS/accounts/$CLIENT")
cp -p -- "$WL_SDSYS/accounts/$CLIENT" "$BK/register-$CLIENT" || need "cannot copy the register record of $CLIENT"
[ -n "$REG_SUM" ] && [ "$(sha256sum -- "$BK/register-$CLIENT" | cut -d' ' -f1)" = "$REG_SUM" ] || need "the saved copy of the register record of $CLIENT is not the record it was taken from"
REG_SAVED=1; MADE_SERVER=0; MADE_NETLOGIN=0; MADE_VOC=0; MADE_PROGS=0
say "  client  : account $CLIENT, Linux user $CUSER, directory $CDIR; the register record is saved in $BK"
say "  server  : $HOST:$PORT   account $ACC   pin to find: ${SHASH:0:16}..."

cleanup() {
  local rc=$? p
  [ "$CLEANED" -eq 0 ] || return 0
  CLEANED=1
  trap - EXIT
  say ""; say "== Z. putting back what this run made on the client =="
  if [ "$MADE_VOC" -eq 1 ]; then wl_sd_user "$CUSER" "remove the VOC pointer" "RUN bp zzwtcl" >/dev/null; fi
  if [ "$MADE_NETLOGIN" -eq 1 ]; then wl_sd_user "$CUSER" "delete.netlogin $SRV" "DELETE.NETLOGIN $SRV" >/dev/null; fi
  if [ "$MADE_SERVER" -eq 1 ]; then wl_sd_admin "delete.server $SRV" "DELETE.SERVER $SRV" >/dev/null; fi
  if [ "$MADE_PROGS" -eq 1 ]; then for p in $PROGS; do rm -f -- "$CDIR/bp/$p" "$CDIR/bp.out/$p"; done; say "  removed the programs $PROGS"; fi
  if [ "$REG_SAVED" -eq 1 ]; then
    if [ "$(sha256sum -- "$WL_SDSYS/accounts/$CLIENT" | cut -d' ' -f1)" = "$REG_SUM" ]; then say "  (the register record of $CLIENT was not changed by the run: nothing to put back)"
    else say "  (the run changed the register record of $CLIENT - the gate words of C4 - and the saved copy is put back)"; fi
    cp -p -- "$BK/register-$CLIENT" "$WL_SDSYS/accounts/$CLIENT"
    expect_eq "Z1 the register record of $CLIENT is back as it was before the run: its checksum, then its owner, group and mode (worked out from the live record before the copy was taken)" \
      "$(sha256sum -- "$WL_SDSYS/accounts/$CLIENT" | cut -d' ' -f1) $(stat -c '%U:%G %a' -- "$WL_SDSYS/accounts/$CLIENT")" "$REG_SUM $REG_ATTR"
  fi
  OUT=$(wl_sd_admin "list.servers (is $SRV gone?)" "LIST.SERVERS")
  if [ -z "$OUT" ]; then fail "Z2 LIST.SERVERS printed nothing (the null case)"
  elif printf '%s\n' "$OUT" | grep -a -q -E "^$SRV[[:space:]]"; then fail "Z2 the definition $SRV is still there"; else pass "Z2 the definition $SRV is gone"; fi
  wl_summary
  local s=$?
  if [ "$rc" -ne 0 ]; then exit "$rc"; fi
  exit "$s"
}
trap cleanup EXIT

say ""; say "== C1. the port is reachable from here =="
if timeout 8 bash -c "exec 3<>/dev/tcp/$HOST/$PORT" 2>/dev/null; then pass "C1 a TCP connection to $HOST:$PORT opens (nothing in between refuses it)"
else fail "C1 a TCP connection to $HOST:$PORT does NOT open: a firewall, a wrong address, or a server bound to loopback only. The rows below cannot pass"; fi

say ""; say "== C2. TLS between the two: 1.3 completes, 1.2 refused, and the key is the one the server printed =="
T13=$(echo | timeout 20 openssl s_client -connect "$HOST:$PORT" -tls1_3 2>&1 | tee /dev/stderr)
T12=$(echo | timeout 20 openssl s_client -connect "$HOST:$PORT" -tls1_2 2>&1 | tee /dev/stderr)
expect_re "C2 TLS 1.3 completes with the other machine" "$T13" 'Protocol *: *TLSv1\.3|New, TLSv1\.3'
expect_re "C2 TLS 1.2 is refused by the other machine" "$T12" 'alert protocol version|handshake failure|no protocols available|wrong version number|Cipher *(is|:) *\(NONE\)'
OSSL=$(echo | timeout 20 openssl s_client -connect "$HOST:$PORT" -tls1_3 2>/dev/null | openssl x509 -pubkey -noout 2>/dev/null | openssl pkey -pubin -outform DER 2>/dev/null | openssl dgst -sha256 2>/dev/null | grep -o -E '[0-9a-f]{64}$' | head -1)
expect_eq "C2 the key hash worked out HERE from what the server presented equals the hash typed from the server's screen" "$OSSL" "$SHASH"

say ""; say "== C3. set.server ... connect: the hash SD shows is the same, and answering n writes nothing =="
MADE_SERVER=1
OUT=$(wl_sd_admin "set.server $SRV ... connect, answering n" "SET.SERVER $SRV $HOST $PORT $ACC connect WRITE ACCOUNTS $CLIENT" "n")
expect_has "C3 'Connected to $HOST:$PORT (a TLS handshake only: nothing was sent)'" "$OUT" "$(wl_msg 11440 "$HOST" "$PORT")"
SHOWN=$(printf '%s\n' "$OUT" | grep -a -E '^[0-9a-f]{64}$' | head -1)
expect_eq "C3 the hash SD shows equals the hash from the server's screen (two different machines, one key)" "$SHOWN" "$SHASH"
expect_has "C3 'The key was not trusted.  Nothing was written'" "$OUT" "$(wl_msg 11443 "$SRV")"

say ""; say "== C4. the client account's gates (one word per command) =="
for w in NET-ON VOC-ON BP-ON; do
  OUT=$(wl_sd_admin "modify.account $CLIENT $w" "MODIFY.ACCOUNT $CLIENT $w")
  expect_lacks "C4 $w was not refused as a second action (11714)" "$OUT" "does one action at a time"
done

say ""; say "== C5. a definition with the WRONG pin: the dial itself is refused before anything is sent =="
BAD=$(printf 'f%.0s' $(seq 1 64))
OUT=$(wl_sd_admin "set.server $SRV with the wrong pin" "SET.SERVER $SRV $HOST $PORT $ACC $BAD WRITE ACCOUNTS $CLIENT NO.QUERY" "LIST.SERVERS")
expect_re "C5 the definition holds the wrong pin" "$OUT" "^$SRV +$HOST:$PORT +$ACC/write +ffffffffffffffff\.\.\. "
MADE_NETLOGIN=1
OUT=$(wl_sd_user "$CUSER" "set.netlogin $SRV against the wrong pin" "SET.NETLOGIN $SRV" "$ACC" "$PWS")
expect_has "C5 the key the other machine presents is not the pinned key (11471): nothing was sent and nothing was stored" "$OUT" "$(wl_msg 11471 "$HOST" "$PORT" "$SRV")"
expect_lacks "C5 and no login was stored" "$OUT" "$(wl_msg 11477 "$SRV" "$ACC")"

say ""; say "== C6. the right pin: the SCRAM login with its channel binding across the network =="
OUT=$(wl_sd_admin "set.server $SRV with the right pin" "SET.SERVER $SRV $HOST $PORT $ACC $SHASH WRITE ACCOUNTS $CLIENT NO.QUERY" "LIST.SERVERS")
expect_re "C6 the definition holds the right pin" "$OUT" "^$SRV +$HOST:$PORT +$ACC/write +${SHASH:0:16}\.\.\. +$CLIENT *\$"
OUT=$(wl_sd_user "$CUSER" "set.netlogin $SRV" "SET.NETLOGIN $SRV" "$ACC" "$PWS")
expect_has "C6 'Your login on server $SRV as $ACC is stored' - the other machine verified the password and proved it knew it too" "$OUT" "$(wl_msg 11477 "$SRV" "$ACC")"

say ""; say "== C7. programs: a pointer, a read, a write and a read back =="
MADE_PROGS=1
sudo -u "$CUSER" tee "$CDIR/bp/zzwtmk" >/dev/null <<'EOP'
   open 'voc' to v else crt 'NO VOC' ; stop
   write 'N':@fm:'zzremote':@fm:'zzwfile' to v, 'zzrt' on error crt 'VOC WRITE REFUSED st=':status() ; stop
   read r from v, 'zzrt' then crt 'pointer zzrt = [':change(r, @fm, ' / '):']' else crt 'pointer zzrt MISSING'
   crt 'zzwtmk done'
end
EOP
sudo -u "$CUSER" tee "$CDIR/bp/zzwtrw" >/dev/null <<'EOP'
   open 'zzrt' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then' ; r = '' ; read r from f, 't1' on error oc = 'error' else oc = 'else'
   crt 'T1 READ t1 branch=':oc:' STATUS()=':status():' record=[':change(r, @fm, '/'):']'
   oc = 'then' ; write 'from the client' to f, 't4' on error oc = 'error'
   crt 'T2 WRITE t4 branch=':oc:' STATUS()=':status()
   oc = 'then' ; r = '' ; read r from f, 't4' on error oc = 'error' else oc = 'else'
   crt 'T3 READ t4 branch=':oc:' STATUS()=':status():' record=[':r:']'
   close f
   crt 'TZ done'
end
EOP
sudo -u "$CUSER" tee "$CDIR/bp/zzwtcl" >/dev/null <<'EOP'
   open 'voc' to v else crt 'NO VOC' ; stop
   delete v, 'zzrt'
   crt 'zzwtcl done'
end
EOP
OUT=$(wl_sd_user "$CUSER" "compile the three programs" "BASIC bp zzwtmk" "BASIC bp zzwtrw" "BASIC bp zzwtcl")
expect_eq "C7 three programs compiled with '0 error(s)'" "$(count_re "$OUT" '^0 error\(s\)')" 3
MADE_VOC=1
OUT=$(wl_sd_user "$CUSER" "run zzwtmk (the VOC pointer)" "RUN bp zzwtmk")
expect_has "C7 the pointer reads back as N / $SRV / zzwfile" "$OUT" "pointer zzrt = [N / $SRV / zzwfile]"
OUT=$(wl_sd_user "$CUSER" "queries and the read/write program through the pointer" "COUNT zzrt" "LIST zzrt" "RUN bp zzwtrw")
expect_re "C7 COUNT counts the 3 records on the OTHER machine" "$OUT" '^3 record\(s\) counted'
expect_has "C7 LIST shows a name that lives only on the other machine (Smith)" "$OUT" "Smith"
expect_re "C7 T1: a READ works (record 'Smith/100')" "$OUT" '^T1 READ t1 branch=then STATUS\(\)=0 record=\[Smith/100\]'
expect_re "C7 T2: the WRITE succeeded over the network (the server's write group is on)" "$OUT" '^T2 WRITE t4 branch=then STATUS\(\)=0'
expect_re "C7 T3: the record reads back as written" "$OUT" '^T3 READ t4 branch=then STATUS\(\)=0 record=\[from the client\]'
expect_has "C7 the program ran to its end" "$OUT" "TZ done"

say ""; say "== C8. two clocks (information, not a verdict: SD pins a key, it does not check certificate dates) =="
LOCAL_EPOCH=$(date -u +%s)
say "      this machine: $LOCAL_EPOCH ($(date -u '+%Y-%m-%d %H:%M:%S') UTC)"
if [ -n "$SEPOCH" ]; then
  case $SEPOCH in *[!0-9]*) fail "C8 --server-epoch is not a number" ;; *) say "      the server's, from its setup: $SEPOCH   (the setup ran earlier, so this machine is expected to read LATER; difference $((LOCAL_EPOCH - SEPOCH)) s)"; pass "C8 both epochs are on record in the log" ;; esac
else
  say "      (no --server-epoch given: the skew is not shown)"
fi

say ""
say "== the rows above are complete; putting back (Z rows follow) =="
say "  NEXT, on the server: sudo bash $SELF --role server-check"
cleanup
