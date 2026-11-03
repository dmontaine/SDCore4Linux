#!/usr/bin/env bash
#
# witness-sdnet-s73.sh - S.73 items 1 and 2 on a REAL install, ONE machine (3 Nov 2026, track G).  WRITTEN, NOT RUN: bash -n only.
#
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-s73.sh [--only=A,H] [--client ACCOUNT]
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-s73.sh --selftest        (no sudo, no sd: the shared helpers on known texts)
#
# ***NEEDS sudo*** from the owner's login (SUDO_USER names the person; --client is that person's SD account, default the same name).  It RESTARTS sd.service twice (every SD
# session on the machine ends): once with NETFILES=2, NETREPLY=3 and NETWAIT=2 in /etc/sd.conf, and at the end with /etc/sd.conf put back byte for byte.  Run it on a test VM.
#
#   A  ITEM 1 - an os-off account over a real API login with NETFILES=2.  Request 29 (the SDNet open of 'account;file', which no client library sends: scram-probe.py --open-sdnet
#      speaks it over TLS with a SCRAM login) names a VOC F-pointer of the account that leads OUTSIDE its directory.  apisrvr refuses it: server_error not 0, STATUS() 3035, and
#      the audit line 'api refused request=29 reason=os gate off user=zzs73 account=zzs73 path=<the path>'.  Controls: an F-pointer INSIDE the account opens; after OS-ON the
#      outside one opens; NETFILES=0 (as delivered) is not tested here (sandbox-req29.py has it).
#   H  ITEM 2 - a server that hangs after the handshake, at the hello and mid-record, timed with NETWAIT=2 / NETREPLY=3 (witness-sdnet-hang.py serves netfake.py's servers on
#      127.0.0.1).  H1 silent at the hello: SET.SERVER ... connect gives 11445 "The TLS handshake with 127.0.0.1:<p> did not complete" about NETWAIT seconds after the control;
#      H2 half a record for the Ack: SET.NETLOGIN gives "No acknowledgement from 127.0.0.1:<p> at the start of the session" about NETREPLY seconds after it; H3 half a record
#      for the reply to client-first: "No reply from 127.0.0.1:<p> during the login".  The control is the same session against a closed port (refused at once), so the session's own
#      cost is taken off; every time is printed.  The sandbox figures were 2.0, 3.0 and 3.0 s (sandbox-netfile.py section timeout).
#
# WHAT IT CHANGES (and puts back): /etc/sd.conf (saved first, put back byte for byte, owner and mode, SD restarted); the account zzs73 with its Linux user (made, deleted);
# /var/tmp/witness-s73-out (a directory file outside every account, made and removed); the client account's register record (saved, put back: NET-ON for SET.NETLOGIN); the
# server definition zzhang (made, deleted).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-s73-<time>.<random>.log.
#
set -u
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
HERE=$(dirname "$SELF")
# shellcheck source=witness-sdnet-lib.sh
. "$HERE/witness-sdnet-lib.sh" || { echo "CANNOT RUN: no witness-sdnet-lib.sh beside $SELF"; exit 2; }
if [ "${1:-}" = "--selftest" ]; then wl_selftest; exit $?; fi
wl_logged "$SELF" witness-sdnet-s73 "$@"
shift

ONLY="A,H"; CLIENT=""
for x in "$@"; do
  case $x in
    --only=*) ONLY=${x#--only=} ;;
    --client=*) CLIENT=${x#--client=} ;;
    *) need "unknown argument '$x'" ;;
  esac
done
want() { case ",$ONLY," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }
[ -n "$CLIENT" ] || CLIENT=$SUDO_USER
ACC=zzs73
SRV=zzhang
OUTDIR=/var/tmp/witness-s73-out
CONF=/etc/sd.conf
SPROBE="$HERE/scram-probe.py"
HANG="$HERE/witness-sdnet-hang.py"
STAMP=$(date +%Y%m%dT%H%M%S)
ST=$WL_TMP/witness-sdnet-s73-$STAMP.d
say "witness-sdnet-s73.sh $STAMP  sections $ONLY"
say "  script  : $SELF"
say "  sudo    : $SUDO_USER   machine: $(hostname 2>/dev/null)   account: $ACC   client account: $CLIENT"
say "  install : $(wl_commit_stamp)"
[ -x "$WL_SD" ] || need "$WL_SD is not installed"
for f in "$SPROBE" "$HANG" "$HERE/netfake.py"; do [ -f "$f" ] || need "no $f beside this script"; done
grep -q -- '--open-sdnet' "$SPROBE" || need "$SPROBE has no --open-sdnet (it is older than 3 Nov 2026)"
grep -q 'reason=os gate off' "$WL_SDSYS/gpl.bp/apisrvr" 2>/dev/null || need "the installed apisrvr has no 'reason=os gate off' (older than S.73, 20 Oct 2026)"
command -v openssl >/dev/null 2>&1 || need "openssl is not installed"
DIRTY=0
[ -e "$WL_SDSYS/accounts/$ACC" ] && { say "  DIRTY: register record $ACC exists"; DIRTY=1; }
id -u "$ACC" >/dev/null 2>&1 && { say "  DIRTY: Linux user $ACC exists"; DIRTY=1; }
[ -e "$OUTDIR" ] || [ -L "$OUTDIR" ] && { say "  DIRTY: $OUTDIR exists"; DIRTY=1; }
[ "$DIRTY" -eq 0 ] || need "the ground is not clear (above): this script will not touch state it did not create"
CUSER=$(wl_account_user "$CLIENT")
[ -n "$CUSER" ] || need "the register record of account '$CLIENT' is not a user account: give --client=ACCOUNT"
wl_mkdir_new "$ST" 700

# ------------------------------------------------------------------------------------------------ the configuration, saved and put back
CONF_SUM=$(sha256sum -- "$CONF" | cut -d' ' -f1); CONF_ATTR=$(stat -c '%U:%G %a' -- "$CONF")
cp -p -- "$CONF" "$ST/sd.conf.saved" || need "cannot save $CONF"
REG_SUM=$(sha256sum -- "$WL_SDSYS/accounts/$CLIENT" | cut -d' ' -f1)
cp -p -- "$WL_SDSYS/accounts/$CLIENT" "$ST/register-$CLIENT" || need "cannot save the register record of $CLIENT"
MADE_ACC=0; MADE_SRV=0; HANG_PID=""; CLEANED=0
PWO=$(wl_newpw); PWS=$(wl_newpw); WL_SECRETS=("$PWO" "$PWS")

restart_sd() {   # $1 why
  say "  restarting sd.service: $1"
  systemctl restart sd.service 2>&1 | sed -e 's/^/      | /'
  local i; for i in $(seq 1 30); do systemctl is-active --quiet sd.service && break; sleep 1; done
  say "      sd.service: $(systemctl is-active sd.service)"
}
cleanup() {
  local rc=$?
  [ "$CLEANED" -eq 0 ] || return 0
  CLEANED=1; trap - EXIT
  say ""; say "== Z. putting back =="
  [ -n "$HANG_PID" ] && kill "$HANG_PID" 2>/dev/null
  [ "$MADE_SRV" -eq 1 ] && wl_sd_admin "delete.server $SRV" "DELETE.SERVER $SRV" >/dev/null
  if [ "$MADE_ACC" -eq 1 ]; then
    wl_sd_admin "delete.account $ACC" "DELETE.ACCOUNT $ACC" "y" >/dev/null
    id -u "$ACC" >/dev/null 2>&1 && userdel -r "$ACC" >/dev/null 2>&1
    [ -d "/home/$ACC" ] && rm -rf -- "/home/$ACC"
  fi
  rm -rf -- "$OUTDIR"
  cp -p -- "$ST/register-$CLIENT" "$WL_SDSYS/accounts/$CLIENT"
  expect_eq "Z1 the register record of $CLIENT is back" "$(sha256sum -- "$WL_SDSYS/accounts/$CLIENT" | cut -d' ' -f1)" "$REG_SUM"
  cp -p -- "$ST/sd.conf.saved" "$CONF"
  expect_eq "Z2 $CONF is back byte for byte, with its owner and mode" "$(sha256sum -- "$CONF" | cut -d' ' -f1) $(stat -c '%U:%G %a' -- "$CONF")" "$CONF_SUM $CONF_ATTR"
  restart_sd "the configuration as it was"
  left=""; [ -e "$WL_SDSYS/accounts/$ACC" ] && left="$left register"; id -u "$ACC" >/dev/null 2>&1 && left="$left user"; [ -e "$OUTDIR" ] && left="$left outdir"
  [ -z "$left" ] && pass "Z3 nothing of $ACC is left" || fail "Z3 left behind:$left"
  rm -rf -- "$ST"
  wl_summary; local s=$?
  [ "$rc" -ne 0 ] && exit "$rc"
  exit "$s"
}
trap cleanup EXIT

say ""; say "== 0. NETFILES=2, NETREPLY=3, NETWAIT=2 in $CONF, SD restarted =="
grep -v -E '^(NETFILES|NETREPLY|NETWAIT)=' "$ST/sd.conf.saved" > "$ST/sd.conf.new"
printf '%s\n' "NETFILES=2" "NETREPLY=3" "NETWAIT=2" >> "$ST/sd.conf.new"
cat "$ST/sd.conf.new" > "$CONF"
say "  $CONF now:"; sed -e 's/^/      | /' "$CONF"
restart_sd "the three values"
OUT=$(wl_sd_admin "the running values" "CONFIG")
expect_re "S0 the running NETFILES is 2" "$OUT" 'NETFILES[^0-9]*2([^0-9]|$)'
expect_re "S0 the running NETREPLY is 3" "$OUT" 'NETREPLY[^0-9]*3([^0-9]|$)'
expect_re "S0 the running NETWAIT is 2" "$OUT" 'NETWAIT[^0-9]*2([^0-9]|$)'

say ""; say "== the account $ACC (os-off as made, the API route, voc.edit for its pointers, NET on) =="
MADE_ACC=1
OUT=$(wl_sd_admin "create.account $ACC" "CREATE.ACCOUNT USER $ACC BOTH VOC-ON" "$PWO" "$PWO")
[ -e "$WL_SDSYS/accounts/$ACC" ] && pass "S1 the register record exists" || { fail "S1 no register record for $ACC"; exit 1; }
OUT=$(wl_sd_admin "modify.password $ACC" "MODIFY.PASSWORD $ACC" "$PWS" "$PWS")
expect_has "S1 'Password accepted.'" "$OUT" "Password accepted."
OUT=$(wl_sd_admin "net-on" "MODIFY.ACCOUNT $ACC NET-ON")
F8=$(sed -n '8p' "$WL_SDSYS/accounts/$ACC" | tr 'A-Z' 'a-z')
case $F8 in ''|no) pass "S1 os.execute is off (register field 8 is '$F8')" ;; *) fail "S1 os.execute is not off: register field 8 is '$F8'" ;; esac
ADIR=$(wl_account_path "$ACC")
mkdir -m 755 -- "$OUTDIR" && printf 'outside' > "$OUTDIR/r1" && chmod 644 "$OUTDIR/r1" || need "cannot make $OUTDIR"
OUT=$(wl_sd_user "$ACC" "the pointers" "CREATE.FILE zzin DIRECTORY" "ED VOC zzout" "I F" "I $OUTDIR" "FI" "CT VOC zzout")
expect_re "S2 the VOC pointer zzout leads outside the account ($OUTDIR)" "$OUT" "$OUTDIR"
[ -d "$ADIR/zzin" ] && pass "S2 zzin is a directory file inside the account ($ADIR/zzin)" || fail "S2 no $ADIR/zzin"
r29() {   # $1 title, then ACCOUNT;FILE targets
  local t=$1; shift; local a=() x
  for x in "$@"; do a+=(--open-sdnet "$x"); done
  say "  --- scram-probe as $ACC: $t ---" >&2
  say "      > sudo -u $SUDO_USER python3 $SPROBE --user $ACC --account $ACC ${a[*]}" >&2
  SD_SCRAM_PASSWORD="$PWS" timeout 60 sudo -u "$SUDO_USER" --preserve-env=SD_SCRAM_PASSWORD python3 "$SPROBE" --user "$ACC" --account "$ACC" "${a[@]}" 2>&1 | wl_mask | tee /dev/stderr
}

if want A; then
  say ""; say "== A. S.73 item 1: request 29 for a pointer that leads out of an os-off account =="
  OFF=$(wl_audit_offset)
  OUT=$(r29 "inside (the control) and outside" "$ACC;zzin" "$ACC;zzout")
  AUD=$(wl_audit_since "$OFF")
  say "  audit since:"; printf '%s\n' "$AUD" | grep -a 'api ' | cut -c1-220 | sed -e 's/^/      | /'
  expect_has "A0 the SCRAM login succeeded (the server's signature verified)" "$OUT" "SCRAM: server signature VERIFIED"
  expect_re "A1 the control: zzin, inside the account, OPENS" "$OUT" "^open-sdnet $ACC;zzin: OPENED"
  expect_re "A2 THE ROW: zzout, outside, is REFUSED with STATUS() 3035" "$OUT" "^open-sdnet $ACC;zzout: REFUSED server_error [1-9][0-9]* status 3035"
  expect_has "A3 and the audit says so, with the path" "$AUD" "api refused request=29 reason=os gate off user=$ACC account=$ACC path=$OUTDIR"
  OUT=$(wl_sd_admin "os-on" "MODIFY.ACCOUNT $ACC OS-ON")
  OUT=$(r29 "outside, with os-on (the control)" "$ACC;zzout")
  expect_re "A4 the control: with os-on the same pointer OPENS" "$OUT" "^open-sdnet $ACC;zzout: OPENED"
  OUT=$(wl_sd_admin "os-off" "MODIFY.ACCOUNT $ACC OS-OFF")
fi

if want H; then
  say ""; say "== H. S.73 item 2: servers that hang (NETWAIT=2, NETREPLY=3) =="
  OUT=$(wl_sd_admin "net-on for $CLIENT" "MODIFY.ACCOUNT $CLIENT NET-ON")
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout "$ST/hang.key" -out "$ST/hang.crt" -days 2 -subj /CN=127.0.0.1 >/dev/null 2>&1 \
    || need "openssl could not make the throw-away certificate"
  chmod 644 "$ST/hang.key" "$ST/hang.crt"; chmod 711 "$ST"
  PIN=$(openssl x509 -in "$ST/hang.crt" -pubkey -noout | openssl pkey -pubin -outform DER | openssl dgst -sha256 | grep -o -E '[0-9a-f]{64}$')
  say "  the throw-away server key's pin: $PIN"
  start_hang() {   # $1 mode -> HANG_PID, HPORT
    rm -f "$ST/hang.port"
    ( sleep 600 | sudo -u "$SUDO_USER" python3 "$HANG" "$@" "$ST/hang.port.tmp" > "$ST/hang-$1.out" 2>&1 ) &
    HANG_PID=$!
    local i; for i in $(seq 1 40); do [ -s "$ST/hang-$1.out" ] && grep -q '^PORT ' "$ST/hang-$1.out" && break; sleep 0.25; done
    HPORT=$(sed -n 's/^PORT //p' "$ST/hang-$1.out" | head -1)
    say "  witness-sdnet-hang.py $1 on 127.0.0.1:${HPORT:-<none>}"
  }
  stop_hang() { pkill -f "witness-sdnet-hang.py $1" 2>/dev/null; sleep 1; HANG_PID=""; say "  what the hanging server saw:"; sed -e 's/^/      | /' "$ST/hang-$1.out"; }
  timed() {   # runs the rest as a command; prints the seconds on the last line
    local t0 t1 out; t0=$(date +%s.%N); out=$("$@"); t1=$(date +%s.%N)
    printf '%s\nSECONDS %s\n' "$out" "$(echo "$t1 - $t0" | bc)"
  }
  secs() { printf '%s\n' "$1" | sed -n 's/^SECONDS //p' | tail -1; }
  within() { awk -v x="$1" -v lo="$2" -v hi="$3" 'BEGIN { exit !(x >= lo && x <= hi) }'; }
  command -v bc >/dev/null 2>&1 || need "bc is not installed (the timings)"

  # the control: a closed port (127.0.0.1:1), refused at once
  C=$(timed wl_sd_admin "control: set.server to a closed port" "SET.SERVER $SRV 127.0.0.1 1 $ACC connect" "n")
  CT=$(secs "$C"); say "  [timing] the control session took $CT s"

  start_hang silent
  [ -n "${HPORT:-}" ] || need "the silent listener did not start (its output: $(cat "$ST/hang-silent.out"))"
  O=$(timed wl_sd_admin "H1 set.server ... connect to the silent listener" "SET.SERVER $SRV 127.0.0.1 $HPORT $ACC connect" "n")
  T=$(secs "$O"); W=$(echo "$T - $CT" | bc); say "  [timing] H1 took $T s, $W s more than the control"
  expect_has "H1 THE ROW: the handshake is given up on in 11445's words" "$O" "$(wl_msg 11445 127.0.0.1 "$HPORT" | cut -c1-60)"
  within "$W" 1.0 4.5 && pass "H1 bounded by NETWAIT=2: $W s over the control (1.0 to 4.5; the old fixed bound was 15)" || fail "H1 $W s over the control is not 1.0 to 4.5"
  stop_hang silent

  for mode in ack first; do
    start_hang "$mode" "$ST/hang.crt" "$ST/hang.key"
    [ -n "${HPORT:-}" ] || { fail "H-$mode the half-record server did not start: $(cat "$ST/hang-$mode.out")"; continue; }
    MADE_SRV=1
    O=$(wl_sd_admin "define $SRV with the throw-away pin" "SET.SERVER $SRV 127.0.0.1 $HPORT $ACC $PIN ACCOUNTS $CLIENT NO.QUERY" "LIST.SERVERS")
    expect_re "H-$mode the definition holds the throw-away pin" "$O" "^$SRV +127\.0\.0\.1:$HPORT +$ACC"
    O=$(timed wl_sd_user "$CUSER" "set.netlogin $SRV against the half-record server ($mode)" "SET.NETLOGIN $SRV" "$ACC" "$PWS")
    T=$(secs "$O"); W=$(echo "$T - $CT" | bc); say "  [timing] $mode took $T s, $W s more than the control"
    if [ "$mode" = ack ]; then
      expect_has "H2 THE ROW: half a record for the Ack is given up on" "$O" "No acknowledgement from 127.0.0.1:$HPORT at the start of the session"
    else
      expect_has "H3 THE ROW: half a record for the reply to client-first is given up on" "$O" "No reply from 127.0.0.1:$HPORT during the login"
    fi
    within "$W" 1.5 5.5 && pass "H-$mode bounded by NETREPLY=3: $W s over the control (1.5 to 5.5; the server holds the connection 60)" || fail "H-$mode $W s over the control is not 1.5 to 5.5"
    expect_lacks "H-$mode and no login was stored" "$O" "$(wl_msg 11477 "$SRV" "$ACC")"
    stop_hang "$mode"
    wl_sd_admin "delete.server $SRV" "DELETE.SERVER $SRV" >/dev/null; MADE_SRV=0
  done
fi
cleanup
