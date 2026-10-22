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
#   * writes twenty-one small programs zzwn* into the client's bp, and removes them.
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
#   A   files-on only (no write group): every change or lock is refused BY THE SERVER - FILELOCK and FILEUNLOCK (requests 32 and 33, S.72) and RECORDLOCKED() (34, S.72b: the
#       holder's user number is not for a login that cannot lock) included; the text a person sees is K1's; the audit lines; the file did not change; the probe (the C client
#       library through ctypes) sends 7-10, 16-19, 30 and 34 directly (the library has NO call for 32 and 33: those two are sent by the netfile programs)
#   M   the definition says READ: the client refuses a write, FILELOCK, FILEUNLOCK and (S.72b) RECORDLOCKED() before they are sent (11501); a WRONG PIN: nothing reaches the
#       server (11455, no new login line)
#   B   files-write-on: the same programs now work, the server file changed, RECORDLOCKED() is served (the same zzwnrl that was refused in A), two sessions see each other's lock - a record lock (B10) and a
#       FILE lock (B11) - the life of a file lock on the real server read from its own LIST.READU (B12: CLOSE, a program that ends holding it, RELEASE), a transaction (B13: FILELOCK refused there,
#       RECORDLOCKED() served, also with a file lock held), the audit says write=on and has no refusal
#   D   (S.73 item 3, 21 Oct 26 - WRITTEN AND SYNTAX-CHECKED, NOT RUN) the administration group: with the write group alone a WRITE ... CREATING.SEQKEY (68) takes ON ERROR 7000, FCONTROL (71)
#       stops the program, ANALYSE.FILE and CREATE.FILE ... SERVER (70) are refused (message 11500 with the 11524 text) and the audit says admin=off; MODIFY.ACCOUNT FILES-ADMIN-ON; the same
#       statements and verbs now work and the SERVER's files are the evidence (the record under the id the counter gave, an index made and enabled, a file made and deleted); the audit has the
#       'api admin request=70 op=...' lines and no refusal; FILES-ADMIN-OFF takes only that group and 68 is refused again
#   C   files-write-off, files-off (K3: the login is refused with the new reason), files-on (K2), the manifest key route.files.write at each step
#   Z   put back: the register record is identical to the copy, nothing the script made is left
# NOT COVERED HERE (other scripts): the orphan and the order of the two group changes (witness-sdnet-writegroup.sh), the requests no files-only login may make, TLS 1.2,
# backup and restore (witness-sdnet-gaps.sh), the installer and uninstaller (witness-sdnet-groups.sh), two machines (witness-sdnet-two-machines.sh), MUSTLOCK (not scripted: it is
# a setting only an internal program can make - pconfig('MUSTLOCK', 1) - and MUSTLOCK=1 in sd.conf would change the whole install; sandbox-netfile.py holds its rows against the fake server.
# S.72b: the request 34 behind a MUSTLOCK write is refused to a write-mode handle whose login has no write group (the write then ends with 7000 / message 11500 "(request 34)" instead of
# 3023); that row is NOT witnessed here).  The private steps w13-w20 (LOGTO, lost connection, CLEARFILE, a transaction, edit gates by name, the negative gates, the restore) are NOT ported: run them
# from .claude/vmtools once they use one MODIFY.ACCOUNT word per command (w3 does not).
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-files-route-<time>.<six random characters>.log, handed back to the owner.
# Changed 19 Oct 26 (finish 2, the verifier's findings): the backup directory is made with wl_mkdir_new, and the audit offset is the physical line count (wl_audit_offset).
# Changed 20 Oct 26 (S.72, QMNet parity tiers A and B): FILELOCK, FILEUNLOCK and RECORDLOCKED() on a remote file.  The rows are in A (zzwn1 X10-X11 - X12 went in S.72b -, zzwn5, zzwn6), M (zzwn5-7), B (zzwn3 Y8-Y12,
# B11 zzwnfa/zzwnfb, B12 zzwnfl/zzwnfd/zzwnfe, B13 zzwn8/zzwn9) and C (zzwn5, zzwn6).  The server's own lock table is read through LIST.READU AS THE ADMINISTRATOR (the verb is not in an ordinary
# account's VOC: the first run on the VM found out that a client program cannot run it): polled for the two-session row (B11), and by a SAMPLER session that runs beside the programs of B12 and is
# tied to them by clock time (see state_fx).  A file lock shows there as type FX with an EMPTY id; fxrows / fxsamples join the path pieces (the verb cuts a path at 31 characters).
# Changed 20 Oct 26 (S.72b, the owner's decision: RECORDLOCKED() of a remote file is write-governed).  Request 34 is in the change set of !apifilesok, so a files-only login WITHOUT the write
# group is refused by the SERVER (message 11500 with the 11521 text "(request 34)", and the audit line `api refused request=34 ...`); a READ definition stops the statement in the CLIENT (11501
# `recordlocked`, nothing sent); with the group and a write definition it is served, inside BEGIN TRANSACTION too.  RECORDLOCKED() has no ON ERROR clause, so it cannot sit in zzwn1's list
# of branches: it has its own program, zzwnrl (A4, M1, B4, C2), and zzwnrt (B13 V1-V3: the transaction with a file lock held, so that a served answer is not 0).  zzwn1's X12 and zzwn7's R3
# are gone (they were rows that expected RECORDLOCKED() to be served to a login without the group and under READ).  The probe sends 34 (A5, B6, C2) after an update lock on ID-rl.
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
PROGS="zzwnmk zzwnrd zzwn1 zzwn2 zzwn3 zzwn4 zzwn5 zzwn6 zzwn7 zzwn8 zzwn9 zzwnrl zzwnrt zzwnla zzwnlb zzwnfa zzwnfb zzwnfl zzwnfd zzwnfe zzwnad zzwncl"

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
    wl_in_group "$REMOTE" sdfilesadmin && fail "Z5 $REMOTE is still listed in sdfilesadmin" || pass "Z5 $REMOTE is not in sdfilesadmin"
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
for g in sdfiles sdfileswrite sdfilesadmin sdusers; do wl_group_exists "$g" || need "no Linux group $g on this machine (install from a tree that makes it)"; done
[ -r "$WL_SDSYS/messages/11524" ] || need "no $WL_SDSYS/messages/11524: this install predates S.73 item 3 (the administration group, 21 Oct 2026); install a newer Dev"
grep -q 'files.admin' "$WL_SDSYS/gpl.bp/apisrvr" 2>/dev/null || need "the installed apisrvr has no files.admin: this install predates S.73 item 3 (21 Oct 2026); install a newer Dev"
command -v ss >/dev/null 2>&1 || need "ss is not installed"
ss -ltn 2>/dev/null | grep -q -E "[:.]$PORT[[:space:]]" || need "nothing is listening on port $PORT (is the API server running on this install?)"
[ -r "$WL_SDSYS/messages/11521" ] || need "no $WL_SDSYS/messages/11521"
grep -q 'cannot change or lock files here' "$WL_SDSYS/messages/11521" 2>/dev/null || need "the installed message 11521 is not the K1 text: this install predates the S.65 finish (19 Oct 2026); install a newer Dev"
grep -q 'has files %2' "$WL_SDSYS/messages/11482" 2>/dev/null || need "the installed message 11482 is not 'Account %1 has files %2' (K2)"
grep -q 'not a member of sdapi or sdfiles' "$WL_SDSYS/gpl.bp/apisrvr" 2>/dev/null || need "the installed apisrvr has no 'not a member of sdapi or sdfiles' (K3)"
grep -q 'change.files.group' "$WL_SDSYS/gpl.bp/modifya" 2>/dev/null || need "the installed modifya has no change.files.group (K4a)"
grep -q 'NETREPLY' "$WL_SDSYS/gpl.bp/config" 2>/dev/null || need "the installed config verb does not list NETREPLY (K8d)"
grep -q 'act.fileunlock' "$WL_SDSYS/gpl.bp/netfile" 2>/dev/null || need "the installed netfile handler has no act.fileunlock: this install predates S.72 (FILELOCK, FILEUNLOCK and RECORDLOCKED() on a remote file, 20 Oct 2026); install a newer Dev"
grep -q 'S.72b: request 34 (recordlocked) joins the change set' "$WL_SDSYS/gpl.bp/apifilesok" 2>/dev/null || need "the installed !apifilesok does not have request 34 in its change set: this install predates S.72b (RECORDLOCKED() of a remote file is write-governed, 20 Oct 2026); install a newer Dev"
grep -q 'S.72b: act.recordlocked refuses a handle whose mode is not write' "$WL_SDSYS/gpl.bp/netfile" 2>/dev/null || need "the installed netfile handler does not refuse RECORDLOCKED() of a read-mode handle: this install predates S.72b (20 Oct 2026); install a newer Dev"
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
# fxrows TEXT FILE   the FILE locks (type FX or SX, and no id) that a LIST.READU text shows on the file FILE, one a line: "<user> <type> <path>".  LIST.READU cuts a path into pieces of 31
# characters (fmt T) and prints the rest on the lines below the row, so the pieces are joined before the file is looked for (as a path component: a dynamic file may show its directory
# or a part of it).  A record lock row has an id and is not a file lock; the verb's other rows end the one before.  20 Oct 26 (S.72): the type and the empty id were measured on the real server.
fxrows() {
  printf '%s\n' "$1" | awk -v want="$2" '
    function flush() { if (type != "" && index(path "/", "/" want "/") > 0) print user, type, path; type = "" }
    $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && NF == 4 && ($4 == "FX" || $4 == "SX") { flush(); user = $1; path = $3; type = $4; cont = 1; next }
    cont && substr($0, 1, 10) == "          " && substr($0, 11, 1) ~ /[^ ]/ { path = path $1; next }
    { flush(); cont = 0 }
    END { flush() }'
}
# fxsamples TEXT FILE   TEXT is the output of a session that ran  TIME / LIST.READU  over and over.  One line for each LIST.READU in it:  "<second of the day> <file locks on FILE> <their owners, comma
# separated, or -> <answered>".  The second is the one the TIME verb printed just before; ANSWERED is 1 when the sample holds the verb's own header or its message 6450 ("no active locks") and 0
# when it holds neither (the verb did not run: "LIST.READU is not in your VOC" was what an ordinary account got on the first VM run) - a sample that did not answer is no evidence of anything.
fxsamples() {
  printf '%s\n' "$1" | awk -v want="$2" -v none="$(wl_msg 6450)" '
    function finish() { if (type != "" && index(path "/", "/" want "/") > 0) { n++; u = (u == "" ? user : u "," user) } type = "" }
    function flush() { finish(); if (have) print sec, n, (u == "" ? "-" : u), ans; have = 0 }
    $0 ~ /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9] [0-9][0-9] [A-Za-z]+ [0-9][0-9][0-9][0-9]$/ { flush(); split($1, a, ":"); sec = a[1] * 3600 + a[2] * 60 + a[3]; have = 1; n = 0; u = ""; ans = 0; cont = 0; next }
    !have { next }
    $0 ~ /^User +File +Path/ { ans = 1; next }
    none != "" && index($0, none) == 1 { ans = 1; next }
    $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && NF == 4 && ($4 == "FX" || $4 == "SX") { finish(); user = $1; path = $3; type = $4; cont = 1; next }
    cont && substr($0, 1, 10) == "          " && substr($0, 11, 1) ~ /[^ ]/ { path = path $1; next }
    { finish(); cont = 0 }
    END { flush() }'
}
# evsec OUT TAG   the second of the day at which a program printed its line "TAG hh:mm:ss ...", or nothing
evsec() { printf '%s\n' "$1" | awk -v t="$2" '$1 == t && $2 ~ /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$/ { split($2, a, ":"); print a[1] * 3600 + a[2] * 60 + a[3]; exit }'; }
# state_fx NAME OUT TAG WANT SAMPLES FILE   the program printed TAG right after an action and then slept 5 seconds, so every sample taken 1 to 3 seconds after that second was taken in that state:
# each of them must answer and show exactly WANT file locks on FILE; a window with no sample in it, or a sample that did not answer, FAILS (the null cases).  The samples it used are printed.
state_fx() {
  local name=$1 out=$2 tag=$3 want=$4 samples=$5 file=$6 p w n bad
  p=$(evsec "$out" "$tag")
  if [ -z "$p" ]; then fail "$name - the program printed no line $tag with a time (the null case)"; return; fi
  w=$(fxsamples "$samples" "$file" | awk -v p="$p" '{ d = ($1 - p + 86400) % 86400; if (d >= 1 && d <= 3) print }')
  n=$(count_re "$w" '.')
  say "      $tag at second $p: samples 1-3 s later (second, file locks on $file, owners, answered): [$(printf '%s' "$w" | tr '\n' ';')]"
  if [ "$n" -lt 1 ]; then fail "$name - no LIST.READU sample was taken 1 to 3 seconds after $tag (the null case: the row would mean nothing)"; return; fi
  bad=$(printf '%s\n' "$w" | awk -v want="$want" '$4 != 1 || $2 != want' | head -1)
  if [ -z "$bad" ]; then pass "$name ($n sample(s), each answered and each with $want file lock(s) on $file)"; else fail "$name - a sample is [$bad] (second, file locks, owners, answered), wanted answered with $want file lock(s)"; fi
}

# ================================================================== S. set-up
say ""; say "== S1. CREATE.ACCOUNT USER $REMOTE with the files route and the edit gates it needs =="
MADE_USER=1; MADE_ACCOUNT=1
# 19 Oct 26: DICT-ON added.  The seeding below runs ED DICT on the account's files, which SD refuses without dict.edit ("A dictionary can only be changed by an account that has
# dict.edit"); the first real run (sdsrv, merged Dev) left ED open on that refusal, every later line was taken as ED input and 74 rows failed.  The 18 Oct private step had all four words.
OUT=$(wl_sd_admin "create.account $REMOTE" "CREATE.ACCOUNT USER $REMOTE FILES-ON VOC-ON BP-ON DICT-ON" "$PWO" "$PWO")
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
# zzwn1: every kind of change or lock, each ON ERROR, with the branch and STATUS() printed; two controls that are plain reads.  (S.72b: RECORDLOCKED() is not here - it has no ON ERROR clause,
# so its refusal would end the program before XZ; it has its own program, zzwnrl, below.  The X12 row of S.72 expected it to be served to this login, which is what S.72b took away.)
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
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   crt 'X10 FILELOCK branch=':oc:' STATUS()=':status()
   oc = 'then' ; fileunlock f on error oc = 'error'
   crt 'X11 FILEUNLOCK branch=':oc:' STATUS()=':status()
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
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   crt 'Y8 FILELOCK branch=':oc:' STATUS()=':status()
   x = recordlocked(f, 'p1')
   crt 'Y9 RECORDLOCKED p1 (we hold the file lock) x=':x:' STATUS()=':status()
   oc = 'then' ; fileunlock f on error oc = 'error'
   crt 'Y10 FILEUNLOCK branch=':oc:' STATUS()=':status()
   x = recordlocked(f, 'p1')
   crt 'Y11 RECORDLOCKED p1 (given back) x=':x:' STATUS()=':status()
   oc = 'then' ; fileunlock f on error oc = 'error'
   crt 'Y12 FILEUNLOCK again (nobody holds it) branch=':oc:' STATUS()=':status()
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
# S.72.  zzwn5 / zzwn6: one FILELOCK / FILEUNLOCK with NO ON ERROR clause - the text a person sees when it is refused (and the line that must not appear)
prog zzwn5 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   filelock f
   crt 'L9 REACHED (the file lock was not refused)'
end
EOP
prog zzwn6 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   fileunlock f
   crt 'U9 REACHED (the file unlock was not refused)'
end
EOP
# zzwn7: the two lock statements that have an ON ERROR clause, under a definition that says READ (phase M).  A FILELOCK or FILEUNLOCK is refused by the client (11501) and nothing is sent.
# (S.72b: the R3 row, RECORDLOCKED() "a read, served", is gone: the statement is refused under READ too, and it has no ON ERROR clause, so it ends the program - it has its own, zzwnrl.)
prog zzwn7 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   crt 'R1 FILELOCK branch=':oc:' STATUS()=':status()
   oc = 'then' ; fileunlock f on error oc = 'error'
   crt 'R2 FILEUNLOCK branch=':oc:' STATUS()=':status()
   close f
   crt 'RZ done'
end
EOP
# S.72b.  zzwnrl: one RECORDLOCKED() of p1 and nothing else.  The function has no ON ERROR clause, so a refusal ends the program with the message: the person sees it and Q9 is not reached.
# Run in A (the server refuses request 34: no write group), M (the client refuses: the definition says READ), B (served: x=0, nothing is locked) and C (refused again after files-write-off).
prog zzwnrl <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   crt 'Q0 opened zzrw'
   x = recordlocked(f, 'p1')
   crt 'Q9 REACHED (RECORDLOCKED() was not refused) x=':x:' STATUS()=':status()
end
EOP
# S.72b.  zzwnrt: RECORDLOCKED() INSIDE BEGIN TRANSACTION.  The session takes a FILE lock first (a lock cannot be taken inside a transaction: 11510), so a served answer is 3 with our user
# number and not the 0 that "nothing is held" also gives.  Only in B (it needs the write group for the FILELOCK).  The unlock comes after the transaction.
prog zzwnrt <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   crt 'V1 FILELOCK before the transaction branch=':oc:' STATUS()=':status()
   begin transaction
   x = recordlocked(f, 'p1')
   crt 'V2 RECORDLOCKED p1 inside the transaction (we hold the file lock) x=':x:' STATUS()=':status()
   rollback
   end transaction
   oc = 'then' ; fileunlock f on error oc = 'error'
   crt 'V3 FILEUNLOCK after the transaction branch=':oc:' STATUS()=':status()
   close f
   crt 'VZ done'
end
EOP
# zzwn8 / zzwn9: the same inside BEGIN TRANSACTION (the client refuses a lock there: 11510, STATUS() 1010; RECORDLOCKED() is a read and is served).  The RECORDLOCKED() after the refused
# FILELOCK says 0, not 3: the file lock was not taken
prog zzwn8 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   begin transaction
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   crt 'T1 FILELOCK in a transaction branch=':oc:' STATUS()=':status()
   oc = 'then' ; fileunlock f on error oc = 'error'
   crt 'T2 FILEUNLOCK in a transaction branch=':oc:' STATUS()=':status()
   x = recordlocked(f, 'p1')
   crt 'T3 RECORDLOCKED p1 in a transaction x=':x:' STATUS()=':status()
   rollback
   end transaction
   close f
   crt 'TZ done'
end
EOP
prog zzwn9 <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   begin transaction
   filelock f
   crt 'T9 REACHED (the file lock was not refused)'
   rollback
   end transaction
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
   x = recordlocked(f, fid)
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' B4 RECORDLOCKED ':fid:' (another user holds the update lock) x=':x:' STATUS()=':st
   t1 = time()
   oc = 'then' ; r = ''
   readu r from f, fid on error oc = 'error' else oc = 'else'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' B2 plain READU ':fid:' returned branch=':oc:' STATUS()=':st:' record=[':change(r, @fm, '/'):'] waited ':(time() - t1):' s'
   release f, fid
   close f
end
EOP
# S.72, two sessions and one FILE lock (B11).  zzwnfa holds the file lock for 12 seconds.  zzwnfb: F1 FILELOCK with a LOCKED clause takes that branch, STATUS() the holder's user number on the
# server; F2 READU of p1 is kept out too (a file lock keeps every record lock out); F3 RECORDLOCKED() says -3 with the same number; F4 FILEUNLOCK of a lock that is not ours leaves 3011 and the
# lock where it is; F5 a plain FILELOCK waits for the holder (3 s or more) and gets the lock; F6 RECORDLOCKED() says 3 with OUR number; it keeps the lock 8 seconds so that the administrator's
# LIST.READU can show it; F7 FILEUNLOCK leaves 0; F8 RECORDLOCKED() says 0.
prog zzwnfa <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then'
   filelock f on error oc = 'error' locked oc = 'locked'
   if oc # 'then' then crt 'FILELOCK branch=':oc:' STATUS()=':status() ; stop
   crt 'A ':oconv(time(), 'MTS'):' holds the file lock (remote)'
   sleep 12
   oc = 'then'
   fileunlock f on error oc = 'error'
   crt 'A ':oconv(time(), 'MTS'):' gave the file lock back, branch=':oc:' STATUS()=':status()
   close f
end
EOP
prog zzwnfb <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   r = ''
   oc = 'then'
   filelock f on error oc = 'error' locked oc = 'locked'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F1 FILELOCK LOCKED-clause branch=':oc:' STATUS()=':st
   oc = 'then'
   readu r from f, 'p1' on error oc = 'error' locked oc = 'locked' else oc = 'else'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F2 READU p1 LOCKED-clause branch=':oc:' STATUS()=':st:' record=[':change(r, @fm, '/'):']'
   x = recordlocked(f, 'p1')
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F3 RECORDLOCKED p1 (the other user holds the file lock) x=':x:' STATUS()=':st
   oc = 'then'
   fileunlock f on error oc = 'error'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F4 FILEUNLOCK of the other user lock branch=':oc:' STATUS()=':st
   t1 = time()
   oc = 'then'
   filelock f on error oc = 'error'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F5 plain FILELOCK returned branch=':oc:' STATUS()=':st:' waited ':(time() - t1):' s'
   x = recordlocked(f, 'p1')
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F6 RECORDLOCKED p1 (we hold the file lock) x=':x:' STATUS()=':st
   sleep 8
   oc = 'then'
   fileunlock f on error oc = 'error'
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F7 FILEUNLOCK branch=':oc:' STATUS()=':st
   x = recordlocked(f, 'p1')
   st = status()
   crt 'B ':oconv(time(), 'MTS'):' F8 RECORDLOCKED p1 (given back) x=':x:' STATUS()=':st
   close f
end
EOP
# S.72, the life of a file lock on the real server (B12).  The client account has NO LIST.READU in its VOC (an administrator verb: run 1 of this script on the VM, 20 Oct 26, found "LIST.READU is
# not in your VOC" where it had expected the table - and its rows for "no file lock" passed on that message), so a program cannot read the lock table itself.  The table is read by an administrator
# SAMPLER that runs beside the programs (TIME, LIST.READU, SLEEP 1, over and over), and every state is tied to the sampler by CLOCK TIME: a program prints "<tag> hh:mm:ss ..." right after each
# action and then sleeps 5 seconds, so the samples taken 1 to 3 seconds after that print were taken in that state.  state_fx does the arithmetic and refuses a window with no sample in it.
# zzwnfl: L0 nothing locked; L1 FILELOCK; L2 RECORDLOCKED() 3 with our number; CLOSE of the locking variable, then a SECOND variable on the same file: L3 RECORDLOCKED() 0 and no lock in the
# table; L4 FILELOCK through the second variable; RELEASE g: L5 0 and no lock; L6 FILELOCK again; a bare RELEASE: L7 0 and no lock.
prog zzwnfl <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   crt 'L0 ':oconv(time(), 'MTS'):' nothing is locked yet'
   sleep 5
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   st = status()
   crt 'L1 ':oconv(time(), 'MTS'):' FILELOCK branch=':oc:' STATUS()=':st
   x = recordlocked(f, 'p1')
   st = status()
   crt 'L2 ':oconv(time(), 'MTS'):' RECORDLOCKED p1 x=':x:' STATUS()=':st
   sleep 5
   close f
   open 'zzrw' to g else crt 'OPEN 2 FAILED st=':status() ; stop
   x = recordlocked(g, 'p1')
   st = status()
   crt 'L3 ':oconv(time(), 'MTS'):' after CLOSE of the locking variable, a second variable: RECORDLOCKED p1 x=':x:' STATUS()=':st
   sleep 5
   oc = 'then' ; filelock g on error oc = 'error' locked oc = 'locked'
   st = status()
   crt 'L4 ':oconv(time(), 'MTS'):' FILELOCK through the second variable branch=':oc:' STATUS()=':st
   sleep 5
   release g
   x = recordlocked(g, 'p1')
   st = status()
   crt 'L5 ':oconv(time(), 'MTS'):' after RELEASE g: RECORDLOCKED p1 x=':x:' STATUS()=':st
   sleep 5
   oc = 'then' ; filelock g on error oc = 'error' locked oc = 'locked'
   st = status()
   crt 'L6 ':oconv(time(), 'MTS'):' FILELOCK again branch=':oc:' STATUS()=':st
   sleep 5
   release
   x = recordlocked(g, 'p1')
   st = status()
   crt 'L7 ':oconv(time(), 'MTS'):' after a bare RELEASE: RECORDLOCKED p1 x=':x:' STATUS()=':st
   sleep 5
   close g
   crt 'LZ ':oconv(time(), 'MTS'):' done'
end
EOP
# zzwnfd and zzwnfe, RUN one after the other in ONE session: zzwnfd takes the file lock (D1: held while it sleeps) and ENDS without CLOSE and without FILEUNLOCK; the NEXT command, zzwnfe (E1: the
# session is still open), asks RECORDLOCKED() through a new variable after five seconds (E2): the lock went with the variable at the prompt, and the sampler shows no file lock during E1.
prog zzwnfd <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   oc = 'then' ; filelock f on error oc = 'error' locked oc = 'locked'
   st = status()
   crt 'D1 ':oconv(time(), 'MTS'):' FILELOCK branch=':oc:' STATUS()=':st
   sleep 5
   crt 'DZ ':oconv(time(), 'MTS'):' ends WITHOUT CLOSE and WITHOUT FILEUNLOCK'
end
EOP
prog zzwnfe <<'EOP'
   crt 'E1 ':oconv(time(), 'MTS'):' the next command begins'
   sleep 5
   open 'zzrw' to g else crt 'OPEN FAILED st=':status() ; stop
   x = recordlocked(g, 'p1')
   st = status()
   crt 'E2 ':oconv(time(), 'MTS'):' the next command, a new file variable: RECORDLOCKED p1 x=':x:' STATUS()=':st
   close g
   crt 'EZ ':oconv(time(), 'MTS'):' done'
end
EOP
# zzwnad (S.73 item 3, phase D): the two statements of the administration set that have an ON ERROR form and the one that has not.  D1 WRITE ... CREATING.SEQKEY takes ON ERROR; D2 and D3 are
# FCONTROL (no ON ERROR clause: a refusal ends the program there, so D9 is reached only when everything before it was served).  The id the server gave is printed so that the server's file can be
# read for it.
prog zzwnad <<'EOP'
   open 'zzrw' to f else crt 'OPEN FAILED st=':status() ; stop
   crt 'D0 opened zzrw'
   oc = 'then' ; id = '' ; write 'seqrec' to f creating.seqkey id on error oc = 'error'
   crt 'D1 WRITE CREATING.SEQKEY branch=':oc:' STATUS()=':status():' id=[':id:']'
   x = fcontrol(f, 6, 'abc')
   crt 'D2 FCONTROL valid.id abc x=[':x:']'
   x = fcontrol(f, 3)
   crt 'D3 FCONTROL get.seq.key x=[':x:']'
   crt 'D9 REACHED'
end
EOP
prog zzwncl <<'EOP'
   open 'voc' to v else crt 'NO VOC' ; stop
   delete v, 'zzrc'
   delete v, 'zzrw'
   delete v, 'zzwnew'
   crt 'zzwncl done'
end
EOP
OUT=$(wl_sd_user "$CUSER" "compile the twenty-two programs" \
  "BASIC bp zzwnmk" "BASIC bp zzwnrd" "BASIC bp zzwn1" "BASIC bp zzwn2" "BASIC bp zzwn3" "BASIC bp zzwn4" "BASIC bp zzwn5" "BASIC bp zzwn6" "BASIC bp zzwn7" "BASIC bp zzwn8" "BASIC bp zzwn9" \
  "BASIC bp zzwnrl" "BASIC bp zzwnrt" "BASIC bp zzwnla" "BASIC bp zzwnlb" "BASIC bp zzwnfa" "BASIC bp zzwnfb" "BASIC bp zzwnfl" "BASIC bp zzwnfd" "BASIC bp zzwnfe" "BASIC bp zzwnad" "BASIC bp zzwncl")
expect_eq "S7 twenty-two programs compiled with '0 error(s)'" "$(count_re "$OUT" '^0 error\(s\)')" 22

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
expect_re "R5 the server's audit trail has a files-only login for $REMOTE (write=off)" "$AUD" "api login route=sdfiles write=off admin=off user=$REMOTE"
expect_lacks "R5 and no refusal: reading needs sdfiles alone" "$AUD" "api refused"
[ "$(logins)" -gt "$L0" ] && pass "R5 the number of login lines grew ($L0 -> $(logins))" || fail "R5 the number of login lines did not grow ($L0 -> $(logins)): the session never reached the server"

# ================================================================== A. files-on only
say ""; say "== A. files-on, no write group: every change or lock is refused by the SERVER =="
expect_eq "A0 the real groups: sdfiles only" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=0"
B_IDS=$(srvids zzwgf); AUD0=$(wl_audit_offset)
expect_eq "A0 the server file holds lk1 p1 p2 p3 before the runs" "$B_IDS" "lk1 p1 p2 p3 "
OUT1=$(wl_sd_user "$CUSER" "run zzwn1" "RUN bp zzwn1")
OUT2=$(wl_sd_user "$CUSER" "run zzwn2 (a write with no ON ERROR)" "RUN bp zzwn2")
OUT5=$(wl_sd_user "$CUSER" "run zzwn5 (a FILELOCK with no ON ERROR)" "RUN bp zzwn5")
OUT6=$(wl_sd_user "$CUSER" "run zzwn6 (a FILEUNLOCK with no ON ERROR)" "RUN bp zzwn6")
# S.72b: zzwnrl on its own, between two audit offsets of its own, so that the server's audit of ITS request 34 can be counted apart from the probe's
AUDK0=$(wl_audit_offset)
OUTK=$(wl_sd_user "$CUSER" "run zzwnrl (a RECORDLOCKED(): request 34, no ON ERROR clause)" "RUN bp zzwnrl")
sleep 2; AUDK=$(wl_audit_since "$AUDK0")
POUT=$(sudo -u "$CUSER" python3 "$BK/probe.py" files "$HOST" "$PORT" "$REMOTE" "$BK/pw" "$REMOTE" zzwgf p1 2>&1 | tee /dev/stderr)
sleep 2
AUD=$(wl_audit_since "$AUD0")
F_IDS=$(srvids zzwgf)
say "  audit lines added by phase A:"; printf '%s\n' "$AUD" | grep -a -E 'api|netfile' | cut -c1-200 | sed -e 's/^/      | /'
expect_has "A1 NULL CASE: run 1 opened the remote file" "$OUT1" "X0 opened zzrw"
expect_has "A1 NULL CASE: run 1 reached its end" "$OUT1" "XZ done"
expect_has "A1 NULL CASE: the probe connected, opened and finished" "$POUT" "P DONE"
expect_has "A1 NULL CASE: zzwnrl opened the remote file (so the refusal below is the statement's, not the open's)" "$OUTK" "Q0 opened zzrw"
expect_re "A2 control X1: a READ works through the files-only login (record 'one')" "$OUT1" '^X1 READ p1 \(control\) branch=then STATUS\(\)=0 record=\[one\]'
expect_re "A2 control X8: a READV without a lock works" "$OUT1" '^X8 READV p3 .*branch=then STATUS\(\)=0 value=\[three\]'
# (S.72b: the X12 control, "RECORDLOCKED() is a read, served", is gone: request 34 is a change-set request now, see A4 / A6 below)
for x in "X2 WRITE n1" "X3 WRITEU n2" "X4 DELETE p2" "X5 READU p3" "X6 RECORDLOCKU p3" "X7 READVU p3" "X9 CLEARFILE" "X10 FILELOCK" "X11 FILEUNLOCK"; do
  expect_re "A3 $x refused: the ON ERROR branch, STATUS() 7000" "$OUT1" "^$x branch=error STATUS\(\)=7000"
done
expect_has "A4 K1: the person sees the server's own reason ($TXT_WRITE_REFUSED)" "$OUT2" "$(wl_msg 11500 "$SRV" write "$TXT_WRITE_REFUSED")"
expect_lacks "A4 K1: not the old 'status 0' text" "$OUT2" "answered write with an error: status"
expect_lacks "A4 and the program did not go on after the refused write" "$OUT2" "W9 REACHED"
expect_has "A4 S.72: a FILELOCK with no ON ERROR clause: the person sees the server's reason, with the request number 32" "$OUT5" "$(wl_msg 11500 "$SRV" filelock "$(wl_msg 11521 32)")"
expect_lacks "A4 S.72: ... and the program did not go on after the refused FILELOCK" "$OUT5" "L9 REACHED"
expect_has "A4 S.72: a FILEUNLOCK with no ON ERROR clause: the server's reason, with the request number 33" "$OUT6" "$(wl_msg 11500 "$SRV" fileunlock "$(wl_msg 11521 33)")"
expect_lacks "A4 S.72: ... and the program did not go on after the refused FILEUNLOCK" "$OUT6" "U9 REACHED"
expect_has "A4 S.72b: a RECORDLOCKED() (no ON ERROR clause exists for it): the person sees the server's reason, with the request number 34" "$OUTK" "$(wl_msg 11500 "$SRV" recordlocked "$(wl_msg 11521 34)")"
expect_lacks "A4 S.72b: ... and the program did not go on after the refused RECORDLOCKED() (the line after it was not reached)" "$OUTK" "Q9 REACHED"
# (the probe sends 7-10, 16-19, 30 and 34.  It cannot send 32 and 33: the client library has no call for them - the netfile programs above are what sends them, and the audit rows below count them)
for n in 7 8 9 10 16 17 18 19 30 34; do
  expect_has "A5 probe: request $n refused with the 11521 text" "$POUT" "$(wl_msg 11521 $n)"
done
expect_re "A5 probe NULL CASE (S.72b): the 34 call was made - its line is in the output, after the update lock on p1-rl, and the library's answer is 0" "$POUT" '^P 34 SDRecordlocked +status=-?[0-9]+ id=p1-rl ret=0 error='
expect_lacks "A5 probe: not the 11480 wording ('This login is for files only')" "$POUT" "This login is for files only"
expect_lacks "A5 probe control: request 6 (read) was not refused" "$POUT" "(request 6)"
expect_lacks "A5 probe control: request 15 (release) was not refused" "$POUT" "(request 15)"
for n in 16 17 18 30 31; do
  expect_has "A6 server audit: api refused request=$n route=sdfiles write=off admin=off user=$REMOTE (from the netfile run)" "$AUD" "api refused request=$n route=sdfiles write=off admin=off user=$REMOTE"
done
for n in 7 8 9 10 19; do
  expect_has "A6 server audit: api refused request=$n (only the probe sends it)" "$AUD" "api refused request=$n route=sdfiles write=off admin=off user=$REMOTE"
done
# S.72: 32 and 33 were each sent twice (zzwn1 and zzwn5; zzwn1 and zzwn6) and refused once each time: a refusal is not asked for again
expect_eq "A6 server audit S.72: request 32 (FILELOCK) refused exactly twice - zzwn1 and zzwn5, each asked once" "$(count_re "$AUD" "api refused request=32 route=sdfiles write=off admin=off user=$REMOTE")" 2
expect_eq "A6 server audit S.72: request 33 (FILEUNLOCK) refused exactly twice - zzwn1 and zzwn6" "$(count_re "$AUD" "api refused request=33 route=sdfiles write=off admin=off user=$REMOTE")" 2
expect_eq "A6 client audit S.72: the FILELOCK attempts are audited before the request, once for each handle (zzwn1, zzwn5): netfile filelock server=$SRV file=zzwgf" "$(count_re "$AUD" "netfile filelock server=$SRV file=zzwgf")" 2
expect_lacks "A6 server audit: no write=on line in this phase" "$AUD" "write=on"
expect_lacks "A6 server audit: request 6 and 15 are never refused" "$AUD" "api refused request=6 "
expect_lacks "A6 server audit: ... nor 15" "$AUD" "api refused request=15 "
# S.72b: request 34 is refused like 32 and 33.  Once for zzwnrl run on its own (its own audit window, AUDK), and twice in the whole phase: zzwnrl and the probe
expect_eq "A6 server audit S.72b: request 34 (RECORDLOCKED()) refused exactly once in the audit lines of zzwnrl's run alone" "$(count_re "$AUDK" "api refused request=34 route=sdfiles write=off admin=off user=$REMOTE")" 1
expect_eq "A6 server audit S.72b: request 34 refused exactly twice in the whole phase - zzwnrl and the probe" "$(count_re "$AUD" "api refused request=34 route=sdfiles write=off admin=off user=$REMOTE")" 2
[ "$(count_re "$AUD" "api login route=sdfiles write=off admin=off user=$REMOTE")" -ge 3 ] && pass "A6 server audit: at least three logins say write=off (two netfile runs and the probe)" || fail "A6 fewer than three 'api login route=sdfiles write=off' lines"
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
OUT5=$(wl_sd_user "$CUSER" "run zzwn5 under READ (a FILELOCK with no ON ERROR)" "RUN bp zzwn5")
OUT6=$(wl_sd_user "$CUSER" "run zzwn6 under READ (a FILEUNLOCK with no ON ERROR)" "RUN bp zzwn6")
OUT7=$(wl_sd_user "$CUSER" "run zzwn7 under READ (FILELOCK and FILEUNLOCK with ON ERROR, branch and STATUS() printed)" "RUN bp zzwn7")
OUTK=$(wl_sd_user "$CUSER" "run zzwnrl under READ (a RECORDLOCKED(): refused by the client, S.72b)" "RUN bp zzwnrl")
sleep 2; AUD=$(wl_audit_since "$AUD0")
expect_has "M1 the client refused the write before sending it (11501)" "$OUT" "$(wl_msg 11501 "$SRV" write)"
expect_lacks "M1 the program did not go on" "$OUT" "W9 REACHED"
expect_has "M1 S.72: the client refused a FILELOCK before sending it (11501 filelock)" "$OUT5" "$(wl_msg 11501 "$SRV" filelock)"
expect_lacks "M1 S.72: ... and the program did not go on" "$OUT5" "L9 REACHED"
expect_has "M1 S.72: the client refused a FILEUNLOCK before sending it (11501 fileunlock)" "$OUT6" "$(wl_msg 11501 "$SRV" fileunlock)"
expect_lacks "M1 S.72: ... and the program did not go on" "$OUT6" "U9 REACHED"
expect_re "M1 S.72: FILELOCK ON ERROR under READ takes the error branch, STATUS() 7000" "$OUT7" '^R1 FILELOCK branch=error STATUS\(\)=7000'
expect_re "M1 S.72: FILEUNLOCK ON ERROR under READ takes the error branch, STATUS() 7000" "$OUT7" '^R2 FILEUNLOCK branch=error STATUS\(\)=7000'
expect_has "M1 S.72: ... zzwn7 reached its end" "$OUT7" "RZ done"
# S.72b: RECORDLOCKED() under READ was SERVED (the R3 row) and is refused now, by the client, before anything is sent.  The login of this phase has NO write group, so a request 34 that had been sent
# would have been refused and audited ("api refused request=34", as A6 showed for the same login): the absence of that line, and of every api refused line, is the evidence that nothing reached the server
expect_has "M1 NULL CASE: zzwnrl opened the remote file under READ (the open works; the statement is what is refused)" "$OUTK" "Q0 opened zzrw"
expect_has "M1 S.72b: the client refused a RECORDLOCKED() before sending it (11501 recordlocked)" "$OUTK" "$(wl_msg 11501 "$SRV" recordlocked)"
expect_lacks "M1 S.72b: ... and the program did not go on" "$OUTK" "Q9 REACHED"
expect_lacks "M1 S.72b: ... and what the person saw is NOT the server's reason (11500 / request 34): the request was not sent" "$OUTK" "$(wl_msg 11521 34)"
expect_lacks "M1 nothing was refused by the server (no api refused line): the client never sent the write, the FILELOCK, the FILEUNLOCK or the RECORDLOCKED()" "$AUD" "api refused"
expect_lacks "M1 S.72b: ... in particular no 'api refused request=34' line (a files-only login without the group is refused 34 by the server whenever it is sent: A6)" "$AUD" "api refused request=34 "
expect_lacks "M1 S.72: and the handler was never asked for a file lock (no netfile filelock audit line)" "$AUD" "netfile filelock"
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
OUTK=$(wl_sd_user "$CUSER" "run zzwnrl (the RECORDLOCKED() that was refused in A, M and C: served now, S.72b)" "RUN bp zzwnrl")
OUT4=$(wl_sd_user "$CUSER" "run zzwn4 (clearfile)" "RUN bp zzwn4")
CLR_CNT=$(wl_sd_user "$REMOTE" "COUNT zzwgf after the clear" "COUNT zzwgf")
sleep 2; AUD=$(wl_audit_since "$AUD0")
say "  audit lines added by phase B:"; printf '%s\n' "$AUD" | grep -a -E 'api|netfile' | cut -c1-200 | sed -e 's/^/      | /'
expect_has "B3 NULL CASE: zzwn3 ran to its end" "$OUT3" "YZ done"
expect_has "B3 NULL CASE: zzwn4 printed its line" "$OUT4" "Y7 CLEARFILE"
expect_has "B3 NULL CASE: the probe finished" "$POUT" "P DONE"
expect_has "B3 NULL CASE: zzwnrl opened the remote file" "$OUTK" "Q0 opened zzrw"
for y in "Y1 WRITE n1" "Y2 WRITEU n2" "Y3 DELETE p2" "Y5 RECORDLOCKU p1"; do
  expect_re "B4 $y now succeeds" "$OUT3" "^$y branch=then STATUS\(\)=0"
done
expect_re "B4 Y4 READU p3 now succeeds and reads 'three'" "$OUT3" '^Y4 READU p3 branch=then STATUS\(\)=0 record=\[three\]'
expect_re "B4 Y6 READVU p1 now succeeds (value 'one')" "$OUT3" '^Y6 READVU p1 branch=then STATUS\(\)=0 value=\[one\]'
expect_re "B4 Y8 S.72: FILELOCK now succeeds" "$OUT3" '^Y8 FILELOCK branch=then STATUS\(\)=0( |$)'
expect_re "B4 Y9 S.72: RECORDLOCKED() says 3 (this session holds the file lock) and STATUS() is a user number on the server" "$OUT3" '^Y9 RECORDLOCKED p1 \(we hold the file lock\) x=3 STATUS\(\)=[1-9][0-9]*( |$)'
expect_re "B4 Y10 S.72: FILEUNLOCK of our own lock leaves STATUS() 0" "$OUT3" '^Y10 FILEUNLOCK branch=then STATUS\(\)=0( |$)'
expect_re "B4 Y11 S.72: RECORDLOCKED() says 0 once the lock is given back, with STATUS() 0" "$OUT3" '^Y11 RECORDLOCKED p1 \(given back\) x=0 STATUS\(\)=0( |$)'
expect_re "B4 Y12 S.72: a second FILEUNLOCK (nobody holds it) leaves STATUS() 3012 (ER\$NLK) and is not an error" "$OUT3" '^Y12 FILEUNLOCK again \(nobody holds it\) branch=then STATUS\(\)=3012( |$)'
expect_re "B4 S.72b: the zzwnrl that was refused in A (and is again in M and C) is SERVED with the write group and a write definition: the line after the statement is reached, x=0 (nothing is locked) and STATUS() 0" "$OUTK" '^Q9 REACHED \(RECORDLOCKED\(\) was not refused\) x=0 STATUS\(\)=0( |$)'
expect_eq "B5 SERVER evidence: after zzwn3 the file holds lk1 n1 n2 p1 p3 and NOT p2" "$MID_IDS" "lk1 n1 n2 p1 p3 "
expect_re "B5 n1 holds 'viaremote'" "$N1" '^1: viaremote *$'
expect_re "B5 n2 holds 'viaremoteu'" "$N2" '^1: viaremoteu *$'
# (32 and 33 are not in this list: the client library has no call to send them; zzwn3's Y8-Y12 above and B11-B13 below are what sends them to a login that may write)
for n in 7 8 9 10 16 17 18 19 30 34; do expect_lacks "B6 probe: request $n is no longer refused" "$POUT" "(request $n)"; done
# S.72b.  The library answers 0 for a refusal AND for "not locked", so "no refusal text" alone could be a call that was never made.  The probe took an UPDATE lock on p3-rl a moment before: a request 34
# that the server answered says 2 (this session holds an update lock), and nothing else can.  The A5 row for the same call is the refusal.
expect_re "B6 probe S.72b: 34 SDRecordlocked is SERVED: it answers 2 (this session holds the update lock it took on p3-rl) - a refused or an unsent call would show 0" "$POUT" '^P 34 SDRecordlocked +status=-?[0-9]+ id=p3-rl ret=2 error='
case " $PRB_IDS " in *" p3-w "*) pass "B7 SERVER evidence: the probe's SDWrite made p3-w" ;; *) fail "B7 p3-w is not on the server (got: $PRB_IDS)" ;; esac
case " $PRB_IDS " in *" p3-wu "*) pass "B7 SERVER evidence: the probe's SDWriteu made p3-wu" ;; *) fail "B7 p3-wu is not on the server (got: $PRB_IDS)" ;; esac
case " $PRB_IDS " in *" p3 "*) fail "B7 p3 is still on the server: the probe's deletes did nothing" ;; *) pass "B7 SERVER evidence: the probe's deletes removed p3" ;; esac
expect_re "B8 Y7 CLEARFILE now succeeds" "$OUT4" '^Y7 CLEARFILE branch=then STATUS\(\)=0'
expect_re "B8 SERVER evidence: the file holds 0 records afterwards (COUNT as the server's own user)" "$CLR_CNT" '^0 record\(s\) counted'
[ "$(count_re "$AUD" "api login route=sdfiles write=on admin=off user=$REMOTE")" -ge 3 ] && pass "B9 audit: at least three logins say write=on" || fail "B9 audit: fewer than three 'api login route=sdfiles write=on' lines"
expect_lacks "B9 audit: NO api refused line in phase B" "$AUD" "api refused"
expect_lacks "B9 audit: no write=off login in phase B" "$AUD" "route=sdfiles write=off"
expect_has "B9 audit: the client's own lines for the write, the delete and the clear" "$AUD" "netfile write server=$SRV file=zzwgf"
expect_has "B9 audit: ... delete" "$AUD" "netfile delete server=$SRV file=zzwgf"
expect_has "B9 audit: ... clear" "$AUD" "netfile clear server=$SRV file=zzwgf"
expect_eq "B9 audit S.72: ONE 'netfile filelock server=$SRV file=zzwgf' line for the run (zzwn3 locked and unlocked through one handle; no id, no record)" "$(count_re "$AUD" "netfile filelock server=$SRV file=zzwgf")" 1

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
[ -n "$HUN" ] && expect_re "B10 B4 S.72: RECORDLOCKED() sees the other user's update lock: -2 and the holder's user number in the server's lock table" "$BOT" "B4 RECORDLOCKED lk1 \(another user holds the update lock\) x=-2 STATUS\(\)=$HUN( |\$)" || fail "B10 B4 cannot be compared (no holder)"
expect_re "B10 B2 plain READU waited for the release (3 s or more) and then got the record" "$BOT" 'B2 plain READU lk1 returned branch=then STATUS\(\)=0 record=\[lock me\] waited ([3-9]|1[0-9]) s'

say ""; say "== B11. two sessions, one FILE lock (S.72): A holds it on the server for 12 s; B is told (LOCKED), is kept out of a record, waits, gets it, gives it back =="
reseed
AUD0=$(wl_audit_offset)
HO="$BK/filelock-holder.out"; BO="$BK/filelock-b.out"
( cd / && printf '\nTERM 200,9999\nRUN bp zzwnfa\nOFF\n' | timeout 100 sudo -u "$CUSER" "$WL_SD" 2>&1 | strip > "$HO" ) &
HP=$!
sleep 4
( cd / && printf '\nTERM 200,9999\nRUN bp zzwnfb\nOFF\n' | timeout 100 sudo -u "$CUSER" "$WL_SD" 2>&1 | strip > "$BO" ) &
BP=$!
sleep 3
LR1=$(wl_sd_admin "list.readu while A holds the file lock" "LIST.READU")
FX1=$(fxrows "$LR1" zzwgf)
HUN=$(printf '%s\n' "$FX1" | awk 'NR == 1 {print $1}')
BUN=""
if [ -n "$HUN" ]; then            # B gets the lock when A lets go and keeps it 8 s: look for a file lock held by somebody else than A
  for k in 1 2 3 4 5 6 7 8 9 10; do
    sleep 1
    LR2=$(wl_sd_admin "list.readu: does B hold the file lock yet? (try $k)" "LIST.READU")
    BUN=$(fxrows "$LR2" zzwgf | awk -v h="$HUN" '$1 != h {print $1; exit}')
    [ -n "$BUN" ] && break
  done
fi
wait "$HP" "$BP"
LR3=$(wl_sd_admin "list.readu after both programs ended" "LIST.READU")
FX3=$(fxrows "$LR3" zzwgf)
sleep 2; AUD=$(wl_audit_since "$AUD0")
HOT=$(cat "$HO" 2>/dev/null); BOT=$(cat "$BO" 2>/dev/null)
say "  holder session:"; grep -a -E '^A |FAILED|ERROR' "$HO" | cut -c1-160 | sed -e 's/^/      | /'
say "  session B:"; grep -a -E '^B |FAILED|ERROR' "$BO" | cut -c1-200 | sed -e 's/^/      | /'
say "  the server's file locks on zzwgf (the FX rows of LIST.READU): while A held it [$(printf '%s' "$FX1" | tr '\n' '|' | cut -c1-150)] holder user number [$HUN]; while B held it, B's number [$BUN]; after both ended [$(printf '%s' "$FX3" | tr '\n' '|' | cut -c1-150)]"
expect_has "B11 NULL CASE: the holder held the file lock" "$HOT" "holds the file lock (remote)"
expect_eq "B11 SERVER evidence: while A held it, LIST.READU as the administrator shows ONE file lock on zzwgf (type FX, no id)" "$(count_re "$FX1" '^[0-9]+ FX ')" 1
if [ -n "$HUN" ]; then
  expect_re "B11 F1 took the LOCKED branch (not then, else or error); STATUS() is the holder's user number in the server's lock table ($HUN)" "$BOT" "F1 FILELOCK LOCKED-clause branch=locked STATUS\(\)=$HUN( |\$)"
  expect_re "B11 F2 READU p1 was kept out by the file lock: the LOCKED branch with the same holder, nothing read" "$BOT" "F2 READU p1 LOCKED-clause branch=locked STATUS\(\)=$HUN record=\[\]"
  expect_re "B11 F3 RECORDLOCKED() sees the other user's FILE lock: -3 and the holder's user number" "$BOT" "F3 RECORDLOCKED p1 \(the other user holds the file lock\) x=-3 STATUS\(\)=$HUN( |\$)"
else
  fail "B11 the lock table showed no file lock held by A (the null case): F1, F2 and F3 cannot be compared"
fi
expect_re "B11 F4 FILEUNLOCK of a lock that is not ours is no error and leaves STATUS() 3011 (ER\$LCK); the lock stayed A's, as F5's wait shows" "$BOT" 'F4 FILEUNLOCK of the other user lock branch=then STATUS\(\)=3011( |$)'
expect_re "B11 F5 a plain FILELOCK waited for the release (3 s or more) and then got the lock" "$BOT" 'F5 plain FILELOCK returned branch=then STATUS\(\)=0 waited ([3-9]|1[0-9]) s'
if [ -n "$BUN" ]; then
  pass "B11 SERVER evidence: once A let go, LIST.READU shows the file lock held by ANOTHER user number ($BUN; A's was $HUN)"
  expect_re "B11 F6 RECORDLOCKED() says 3 (this session holds the file lock) and STATUS() is OUR user number as the server's table shows it ($BUN)" "$BOT" "F6 RECORDLOCKED p1 \(we hold the file lock\) x=3 STATUS\(\)=$BUN( |\$)"
else
  fail "B11 the lock table never showed the file lock held by a user other than A (the null case): B's number cannot be compared"
fi
expect_re "B11 F7 FILEUNLOCK of our own lock leaves STATUS() 0" "$BOT" 'F7 FILEUNLOCK branch=then STATUS\(\)=0( |$)'
expect_re "B11 F8 RECORDLOCKED() says 0 once the lock is given back, STATUS() 0" "$BOT" 'F8 RECORDLOCKED p1 \(given back\) x=0 STATUS\(\)=0( |$)'
expect_re "B11 the holder gave its lock back at the end of its sleep: FILEUNLOCK left STATUS() 0" "$HOT" 'A [0-9:]+ gave the file lock back, branch=then STATUS\(\)=0( |$)'
{ have_line "$LR3" '^User +File +Path' || have_line "$LR3" "^$(wl_msg 6450)"; } && pass "B11 NULL CASE: LIST.READU answered after both programs ended" || fail "B11 NULL CASE: LIST.READU printed nothing useful after both programs ended (the rows below mean nothing)"
expect_eq "B11 SERVER evidence: after both programs ended, LIST.READU shows NO file lock on zzwgf" "$(count_re "$FX3" '.')" 0
expect_eq "B11 audit S.72: exactly TWO 'netfile filelock server=$SRV file=zzwgf' lines - A's handle and B's - though B asked for the lock many times while it waited (once for a handle)" "$(count_re "$AUD" "netfile filelock server=$SRV file=zzwgf")" 2
expect_lacks "B11 audit: no api refused line" "$AUD" "api refused"

say ""; say "== B12. the life of a file lock on the real server, read from its own LIST.READU by an administrator sampler beside the programs (S.72): CLOSE, RELEASE f, a bare RELEASE, a program that ends holding it =="
reseed
SMP="$BK/lock-sampler.out"
SBODY=$'\n''TERM 200,9999'; for k in $(seq 1 75); do SBODY="$SBODY"$'\nTIME\nLIST.READU\nSLEEP 1'; done; SBODY="$SBODY"$'\nOFF\n'
say "  the sampler (an sd session as sdsys: TIME, LIST.READU, SLEEP 1, 75 times; it ends by itself about 80 seconds after it starts; its whole output is $SMP) starts first"
( cd "$WL_SDSYS" && printf '%s' "$SBODY" | timeout 200 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$WL_SD" 2>&1 | strip > "$SMP" ) &
SP=$!
sleep 3
LF=$(wl_sd_user "$CUSER" "run zzwnfl (FILELOCK, CLOSE, RELEASE f, a bare RELEASE: a state every 5 seconds, each printed with its time)" "RUN bp zzwnfl")
LD=$(wl_sd_user "$CUSER" "run zzwnfd and then zzwnfe in ONE session (a program that ends holding the file lock; the next command)" "RUN bp zzwnfd" "RUN bp zzwnfe")
wait "$SP"
SAMP=$(cat "$SMP" 2>/dev/null)
SAMPLES=$(fxsamples "$SAMP" zzwgf)
say "  the sampler took $(count_re "$SAMPLES" '.') samples, $(count_re "$SAMPLES" ' 1$') of them answered; the first three (second, file locks on zzwgf, owners, answered): [$(printf '%s' "$SAMPLES" | head -3 | tr '\n' ';')]"
[ "$(count_re "$SAMPLES" '.')" -ge 40 ] && [ "$(count_re "$SAMPLES" ' 1$')" = "$(count_re "$SAMPLES" '.')" ] && pass "B12 NULL CASE: the sampler's LIST.READU ran and ANSWERED every time ($(count_re "$SAMPLES" '.') samples; an answer is the verb's own header or its 'no active locks' message)" \
  || fail "B12 NULL CASE: the sampler took $(count_re "$SAMPLES" '.') samples and $(count_re "$SAMPLES" ' 1$') answered (at least 40, all answered, are needed): the rows below mean nothing"
expect_re "B12 NULL CASE: zzwnfl ran to its end" "$LF" '^LZ [0-9:]+ done'
state_fx "B12 L0 SERVER evidence: before the program locked anything, NO file lock on zzwgf" "$LF" L0 0 "$SAMP" zzwgf
expect_re "B12 L1 FILELOCK succeeds" "$LF" '^L1 [0-9:]+ FILELOCK branch=then STATUS\(\)=0( |$)'
state_fx "B12 L1 SERVER evidence: after FILELOCK, ONE file lock on zzwgf (type FX, no id) in LIST.READU" "$LF" L1 1 "$SAMP" zzwgf
P1=$(evsec "$LF" L1); OWN=$(printf '%s\n' "$SAMPLES" | awk -v p="${P1:-0}" '{ d = ($1 - p + 86400) % 86400; if (d >= 1 && d <= 3 && $2 == 1) { print $3; exit } }')
[ -n "$OWN" ] && expect_re "B12 L2 RECORDLOCKED() says 3 and STATUS() is the owner the table shows ($OWN)" "$LF" "^L2 [0-9:]+ RECORDLOCKED p1 x=3 STATUS\(\)=$OWN( |\$)" || fail "B12 L2 cannot be compared with the table (no owner was seen in it)"
expect_re "B12 (a) L3 CLOSE of the locking variable released the lock: RECORDLOCKED() through a second variable says 0 (not 3)" "$LF" '^L3 [0-9:]+ after CLOSE of the locking variable, a second variable: RECORDLOCKED p1 x=0 STATUS\(\)=[0-9]+( |$)'
state_fx "B12 (a) L3 SERVER evidence: after the CLOSE, NO file lock on zzwgf in LIST.READU" "$LF" L3 0 "$SAMP" zzwgf
expect_re "B12 L4 FILELOCK through the second variable succeeds" "$LF" '^L4 [0-9:]+ FILELOCK through the second variable branch=then STATUS\(\)=0( |$)'
state_fx "B12 L4 SERVER evidence: ONE file lock on zzwgf again" "$LF" L4 1 "$SAMP" zzwgf
expect_re "B12 (c) L5 RELEASE g (the file form) gave the lock back: RECORDLOCKED() says 0 (not 3)" "$LF" '^L5 [0-9:]+ after RELEASE g: RECORDLOCKED p1 x=0 STATUS\(\)=[0-9]+( |$)'
state_fx "B12 (c) L5 SERVER evidence: after RELEASE g, NO file lock on zzwgf in LIST.READU" "$LF" L5 0 "$SAMP" zzwgf
expect_re "B12 L6 FILELOCK again succeeds" "$LF" '^L6 [0-9:]+ FILELOCK again branch=then STATUS\(\)=0( |$)'
state_fx "B12 L6 SERVER evidence: ONE file lock on zzwgf again" "$LF" L6 1 "$SAMP" zzwgf
expect_re "B12 (c) L7 a bare RELEASE gave the lock back: RECORDLOCKED() says 0 (not 3)" "$LF" '^L7 [0-9:]+ after a bare RELEASE: RECORDLOCKED p1 x=0 STATUS\(\)=[0-9]+( |$)'
state_fx "B12 (c) L7 SERVER evidence: after the bare RELEASE, NO file lock on zzwgf in LIST.READU" "$LF" L7 0 "$SAMP" zzwgf
expect_re "B12 NULL CASE: zzwnfd ended as designed (no CLOSE, no FILEUNLOCK)" "$LD" '^DZ [0-9:]+ ends WITHOUT CLOSE and WITHOUT FILEUNLOCK'
expect_re "B12 NULL CASE: the next command, zzwnfe, ran to its end in the same session" "$LD" '^EZ [0-9:]+ done'
expect_re "B12 (b) D1 zzwnfd's FILELOCK succeeds" "$LD" '^D1 [0-9:]+ FILELOCK branch=then STATUS\(\)=0( |$)'
state_fx "B12 (b) D1 SERVER evidence: while zzwnfd slept, ONE file lock on zzwgf in LIST.READU" "$LD" D1 1 "$SAMP" zzwgf
state_fx "B12 (b) E1 SERVER evidence: in the NEXT command of the same session (still open), NO file lock on zzwgf in LIST.READU - the lock went with the variable at the prompt" "$LD" E1 0 "$SAMP" zzwgf
expect_re "B12 (b) E2 the next command's RECORDLOCKED() through a new variable says 0 (not 3)" "$LD" '^E2 [0-9:]+ the next command, a new file variable: RECORDLOCKED p1 x=0 STATUS\(\)=[0-9]+( |$)'

say ""; say "== B13. a transaction (S.72, S.72b): FILELOCK and FILEUNLOCK are refused there (11510, STATUS() 1010) and send nothing; RECORDLOCKED() changes nothing and is SERVED there - with the write group and a write definition, as everywhere (S.72b: the client's test for it is the read-mode one alone) =="
AUD0=$(wl_audit_offset)
OUT8=$(wl_sd_user "$CUSER" "run zzwn8 (FILELOCK, FILEUNLOCK and RECORDLOCKED inside BEGIN TRANSACTION)" "RUN bp zzwn8")
OUT9=$(wl_sd_user "$CUSER" "run zzwn9 (a FILELOCK with no ON ERROR inside BEGIN TRANSACTION)" "RUN bp zzwn9")
sleep 2; AUD=$(wl_audit_since "$AUD0")
expect_has "B13 NULL CASE: zzwn8 ran to its end" "$OUT8" "TZ done"
expect_re "B13 T1 FILELOCK inside the transaction takes the ON ERROR branch, STATUS() 1010" "$OUT8" '^T1 FILELOCK in a transaction branch=error STATUS\(\)=1010( |$)'
expect_re "B13 T2 FILEUNLOCK inside the transaction takes the ON ERROR branch, STATUS() 1010" "$OUT8" '^T2 FILEUNLOCK in a transaction branch=error STATUS\(\)=1010( |$)'
expect_re "B13 T3 RECORDLOCKED() inside the transaction is served: x=0 (not 3: the refused FILELOCK took no lock) - the program went on to TZ, so the statement did not stop it (S.72b)" "$OUT8" '^T3 RECORDLOCKED p1 in a transaction x=0 STATUS\(\)=[0-9]+( |$)'
expect_has "B13 zzwn9: with no ON ERROR the person sees message 11510 naming the server and filelock" "$OUT9" "$(wl_msg 11510 "$SRV" filelock)"
expect_lacks "B13 zzwn9: ... and the program did not go on" "$OUT9" "T9 REACHED"
expect_lacks "B13 nothing was refused by the server (no api refused line): the client never sent the FILELOCKs, and the RECORDLOCKED() it did send was served (S.72b)" "$AUD" "api refused"
expect_lacks "B13 the handler was never asked for a lock (no netfile filelock audit line)" "$AUD" "netfile filelock"
# S.72b.  T3's 0 is also what "nothing is held" gives, and a stub that answered 0 inside a transaction would pass it.  zzwnrt takes a FILE lock BEFORE BEGIN TRANSACTION (a lock cannot be taken inside one),
# asks inside, and gives the lock back after: a served answer is 3 with our user number.  Its own audit window: its FILELOCK is one 'netfile filelock' line, which the rows above must not see.
AUDT0=$(wl_audit_offset)
OUTT=$(wl_sd_user "$CUSER" "run zzwnrt (FILELOCK, then BEGIN TRANSACTION and RECORDLOCKED() inside it, then FILEUNLOCK)" "RUN bp zzwnrt")
sleep 2; AUDT=$(wl_audit_since "$AUDT0")
expect_has "B13 NULL CASE: zzwnrt ran to its end" "$OUTT" "VZ done"
expect_re "B13 V1 the FILELOCK before the transaction succeeds (the lock is held when the transaction begins)" "$OUTT" '^V1 FILELOCK before the transaction branch=then STATUS\(\)=0( |$)'
expect_re "B13 V2 S.72b: RECORDLOCKED() INSIDE the transaction is served and sees our file lock: x=3 and STATUS() a user number on the server (a refusal would have ended the program; a stub answering 0 would show x=0)" "$OUTT" '^V2 RECORDLOCKED p1 inside the transaction \(we hold the file lock\) x=3 STATUS\(\)=[1-9][0-9]*( |$)'
expect_re "B13 V3 FILEUNLOCK after the transaction leaves STATUS() 0 (the lock was still ours, so the transaction did not take it away)" "$OUTT" '^V3 FILEUNLOCK after the transaction branch=then STATUS\(\)=0( |$)'
expect_eq "B13 audit S.72b: exactly ONE 'netfile filelock' line for zzwnrt (the FILELOCK before the transaction; the RECORDLOCKED() inside it writes none)" "$(count_re "$AUDT" "netfile filelock server=$SRV file=zzwgf")" 1
expect_lacks "B13 audit S.72b: no api refused line for zzwnrt (the RECORDLOCKED() inside the transaction reached the server and was served)" "$AUDT" "api refused"

# ================================================================== D. the administration group (S.73 item 3, 21 Oct 2026)
say ""; say "== D. files-admin-on (S.73 item 3): requests 68 to 71 are refused to a login with the write group alone, served with files-admin-on, refused again after files-admin-off =="
reseed
D_IDS0=$(srvids zzwgf)
expect_eq "D0 reseeded: the server file holds lk1 p1 p2 p3" "$D_IDS0" "lk1 p1 p2 p3 "
expect_eq "D0 the real groups: sdfiles and sdfileswrite" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=1"
wl_in_group "$REMOTE" sdfilesadmin && fail "D0 $REMOTE is in sdfilesadmin before files-admin-on (a new account has it off)" || pass "D0 $REMOTE is not in sdfilesadmin"

# D1. the write group alone: a WRITE ... CREATING.SEQKEY (68) takes ON ERROR with STATUS() 7000, FCONTROL (71) stops the program, ANALYSE.FILE and CREATE.FILE ... SERVER (70) are refused, and the server
# audits each refusal with admin=off.  Nothing is changed on the server.
AUDD0=$(wl_audit_offset)
OUTD=$(wl_sd_user "$CUSER" "run zzwnad WITHOUT the administration group" "RUN bp zzwnad")
OUTV=$(wl_sd_user "$CUSER" "ANALYSE.FILE and CREATE.FILE ... SERVER WITHOUT the administration group" "ANALYSE.FILE zzrw" "CREATE.FILE zzwnew SERVER $SRV")
NF1=$(wl_sd_user "$REMOTE" "COUNT zzwnew (must not be there)" "COUNT zzwnew")
sleep 2; AUDD=$(wl_audit_since "$AUDD0")
say "  audit lines added by phase D1:"; printf '%s\n' "$AUDD" | grep -a -E 'api|netfile' | cut -c1-200 | sed -e 's/^/      | /'
expect_has "D1 NULL CASE: zzwnad opened the remote file" "$OUTD" "D0 opened zzrw"
expect_re "D1 WRITE ... CREATING.SEQKEY is refused: ON ERROR, STATUS() 7000 and no id" "$OUTD" '^D1 WRITE CREATING.SEQKEY branch=error STATUS\(\)=7000 id=\[\]'
expect_has "D1 FCONTROL stops the program with the server's refusal in the client's words (message 11500 with 11524, request 71)" "$OUTD" "$(wl_msg 11500 "$SRV" fcontrol "$(wl_msg 11524 71)")"
expect_lacks "D1 ... D9 is not reached" "$OUTD" "D9 REACHED"
expect_has "D1 ANALYSE.FILE is refused with the server's words (request 70)" "$OUTV" "$(wl_msg 11500 "$SRV" analyse.file "$(wl_msg 11524 70)")"
expect_has "D1 CREATE.FILE ... SERVER is refused with the server's words (request 70)" "$OUTV" "$(wl_msg 11500 "$SRV" create.file "$(wl_msg 11524 70)")"
expect_eq "D1 SERVER evidence: the file is unchanged by the refused tries" "$(srvids zzwgf)" "$D_IDS0"
expect_lacks "D1 SERVER evidence: zzwnew was not created on the server" "$NF1" "record(s) counted"
expect_eq "D1 audit: requests 68, 71 and 70 (twice) refused, each with write=on admin=off" "$(count_re "$AUDD" "api refused request=(68|70|71) route=sdfiles write=on admin=off user=$REMOTE")" 4

# D2. files-admin-on: the word, the real groups, the manifest
OUT=$(wl_sd_admin "files-admin-on" "MODIFY.ACCOUNT $REMOTE FILES-ADMIN-ON")
expect_has "D2 the line says files-admin yes" "$OUT" "$(wl_msg 11525 "$REMOTE" yes)"
expect_eq "D2 the real groups: sdfiles and sdfileswrite kept" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=1"
wl_in_group "$REMOTE" sdfilesadmin && pass "D2 $REMOTE is in sdfilesadmin" || fail "D2 $REMOTE is not in sdfilesadmin"
R_AD=$(wl_backup_routes "$REMOTE" "$BK/bak0")
expect_re "D2 manifest while administration is on: route.files: 1 route.files.write: 1 route.files.admin: 1" "$R_AD" "\[account $REMOTE\] route\.files: 1 route\.files\.write: 1 route\.files\.admin: 1"

# D3. with the group: the same programs and verbs are served, and the server's own files are the evidence
AUDD0=$(wl_audit_offset)
OUTD=$(wl_sd_user "$CUSER" "run zzwnad WITH the administration group" "RUN bp zzwnad")
D_ID=$(printf '%s\n' "$OUTD" | sed -n 's/^D1 .* id=\[\([0-9][0-9]*\)\].*$/\1/p' | head -1)
OUTV=$(wl_sd_user "$CUSER" "the verbs WITH the administration group" "ANALYSE.FILE zzrw" "CREATE.INDEX zzrc name" "BUILD.INDEX zzrc name" "CREATE.FILE zzwnew SERVER $SRV" "COUNT zzwnew" "DELETE.FILE zzwnew NO.QUERY")
IDX=$(wl_sd_user "$REMOTE" "LIST.INDEX zzcust" "LIST.INDEX zzcust")
SEQ=$(wl_sd_user "$REMOTE" "CT zzwgf ${D_ID:-0}" "CT zzwgf ${D_ID:-0}")
GONE=$(wl_sd_user "$REMOTE" "COUNT zzwnew after the delete" "COUNT zzwnew")
sleep 2; AUDD=$(wl_audit_since "$AUDD0")
say "  audit lines added by phase D3:"; printf '%s\n' "$AUDD" | grep -a -E 'api|netfile' | cut -c1-200 | sed -e 's/^/      | /'
expect_has "D3 NULL CASE: zzwnad opened the remote file and ran to its end" "$OUTD" "D9 REACHED"
expect_re "D3 WRITE ... CREATING.SEQKEY is served: THEN, STATUS() 0 and an id" "$OUTD" '^D1 WRITE CREATING.SEQKEY branch=then STATUS\(\)=0 id=\[[0-9]+\]'
[ -n "$D_ID" ] && pass "D3 the id the server's counter gave is $D_ID" || fail "D3 no id came back from the WRITE ... CREATING.SEQKEY"
expect_has "D3 SERVER evidence: the record under that id holds 'seqrec'" "$SEQ" "seqrec"
expect_re "D3 FCONTROL(f, valid.id, 'abc') answers 1" "$OUTD" '^D2 FCONTROL valid.id abc x=\[1\]'
expect_re "D3 FCONTROL(f, get.seq.key) answers a number" "$OUTD" '^D3 FCONTROL get.seq.key x=\[[0-9]+\]'
expect_re "D3 ANALYSE.FILE printed the server's report of zzwgf" "$OUTV" 'zzwgf'
expect_re "D3 SERVER evidence: CREATE.INDEX and BUILD.INDEX made the index NAME of zzcust and enabled it (LIST.INDEX as the server's own user)" "$IDX" '^[Nn][Aa][Mm][Ee] +Y'
expect_has "D3 CREATE.FILE ... SERVER said the file was made and the pointer written" "$OUTV" "$(wl_msg 11533 zzwnew "$SRV" zzwnew)"
expect_re "D3 the new pointer works: COUNT zzwnew through it counted 0 records" "$OUTV" '^0 record\(s\) counted'
expect_has "D3 DELETE.FILE said the file and the pointer are gone" "$OUTV" "$(wl_msg 11532 zzwnew "$SRV" zzwnew)"
expect_lacks "D3 SERVER evidence: zzwnew is gone from the server" "$GONE" "record(s) counted"
for v in "analyse.file file=zzwgf" "create.index file=zzcust" "build.index file=zzcust" "create.file file=zzwnew" "delete.file file=zzwnew"; do
  expect_has "D3 audit: api admin request=70 op=$v user=$REMOTE" "$AUDD" "api admin request=70 op=${v% *} ${v#* } user=$REMOTE"
done
expect_has "D3 audit: the client's own line for the verb" "$AUDD" "netfile admin server=$SRV file=zzwgf op=analyse.file"
expect_lacks "D3 audit: NO api refused line in phase D3" "$AUDD" "api refused"
[ "$(count_re "$AUDD" "api login route=sdfiles write=on admin=on user=$REMOTE")" -ge 3 ] && pass "D3 audit: the logins say write=on admin=on" || fail "D3 audit: fewer than three 'api login route=sdfiles write=on admin=on' lines"

# D4. files-admin-off: only the administration group goes, and the requests are refused again
OUT=$(wl_sd_admin "files-admin-off" "MODIFY.ACCOUNT $REMOTE FILES-ADMIN-OFF")
expect_has "D4 the line says files-admin no" "$OUT" "$(wl_msg 11525 "$REMOTE" no)"
expect_eq "D4 the real groups: sdfiles and sdfileswrite kept" "$(wl_state "$REMOTE")" "sdfiles=1 sdfileswrite=1"
wl_in_group "$REMOTE" sdfilesadmin && fail "D4 $REMOTE is still in sdfilesadmin" || pass "D4 $REMOTE is not in sdfilesadmin"
OUTD=$(wl_sd_user "$CUSER" "run zzwnad after files-admin-off" "RUN bp zzwnad")
expect_has "D4 NULL CASE: zzwnad opened the remote file" "$OUTD" "D0 opened zzrw"
expect_re "D4 WRITE ... CREATING.SEQKEY is refused again" "$OUTD" '^D1 WRITE CREATING.SEQKEY branch=error STATUS\(\)=7000 id=\[\]'

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
OUT5=$(wl_sd_user "$CUSER" "run zzwn5 after files-write-off (a FILELOCK)" "RUN bp zzwn5")
OUT6=$(wl_sd_user "$CUSER" "run zzwn6 after files-write-off (a FILEUNLOCK)" "RUN bp zzwn6")
AUDK0=$(wl_audit_offset)
OUTK=$(wl_sd_user "$CUSER" "run zzwnrl after files-write-off (a RECORDLOCKED(): request 34)" "RUN bp zzwnrl")
sleep 2; AUDK=$(wl_audit_since "$AUDK0")
expect_has "C2 a netfile write is refused again with the 11521 text" "$OUT2" "$TXT_WRITE_REFUSED"
expect_has "C2 S.72: a FILELOCK is refused again with the 11521 text (request 32), and the program does not go on" "$OUT5" "$(wl_msg 11500 "$SRV" filelock "$(wl_msg 11521 32)")"
expect_lacks "C2 S.72: ... L9 is not reached" "$OUT5" "L9 REACHED"
expect_has "C2 S.72: a FILEUNLOCK is refused again with the 11521 text (request 33), and the program does not go on" "$OUT6" "$(wl_msg 11500 "$SRV" fileunlock "$(wl_msg 11521 33)")"
expect_lacks "C2 S.72: ... U9 is not reached" "$OUT6" "U9 REACHED"
expect_has "C2 NULL CASE: zzwnrl opened the remote file (the same program that B served)" "$OUTK" "Q0 opened zzrw"
expect_has "C2 S.72b: a RECORDLOCKED() is refused again with the 11521 text (request 34), and the program does not go on" "$OUTK" "$(wl_msg 11500 "$SRV" recordlocked "$(wl_msg 11521 34)")"
expect_lacks "C2 S.72b: ... Q9 is not reached" "$OUTK" "Q9 REACHED"
expect_eq "C2 S.72b: server audit: request 34 refused exactly once in the audit lines of that run" "$(count_re "$AUDK" "api refused request=34 route=sdfiles write=off admin=off user=$REMOTE")" 1
expect_has "C2 a direct write (16) is refused again" "$POUT" "$(wl_msg 11521 16)"
expect_has "C2 S.72b: a direct request 34 (the probe's SDRecordlocked) is refused again" "$POUT" "$(wl_msg 11521 34)"
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
OUTK=$(wl_sd_user "$CUSER" "run zzwnrl after files-on (a RECORDLOCKED())" "RUN bp zzwnrl")
expect_has "C4 a netfile write is refused again" "$OUT2" "$TXT_WRITE_REFUSED"
expect_has "C4 NULL CASE: zzwnrl opened the remote file" "$OUTK" "Q0 opened zzrw"
expect_has "C4 S.72b: a RECORDLOCKED() is refused again with the 11521 text (request 34): files-on gave sdfiles back and not the write group" "$OUTK" "$(wl_msg 11500 "$SRV" recordlocked "$(wl_msg 11521 34)")"
expect_lacks "C4 S.72b: ... Q9 is not reached" "$OUTK" "Q9 REACHED"
R_BACK=$(wl_backup_routes "$REMOTE" "$BK/bak4")
expect_re "C4 manifest after files-on: route.files: 1 route.files.write: 0" "$R_BACK" "\[account $REMOTE\] route\.files: 1 route\.files\.write: 0"

# ================================================================== the end: cleanup() makes the Z rows and the summary
say ""
say "== the rows above are complete; putting back (Z rows follow) =="
cleanup
