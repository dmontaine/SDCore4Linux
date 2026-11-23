#!/usr/bin/env bash
#
# witness-localsdsys.sh - S.267 on a REAL install (the Debian 13 VM): SDSYS reached from this computer by the Linux users the administrator lists.
# A sandbox cannot show any of it: it is not root, has no sdsys user, no sudo, no logind ssh session and no setpriv.
#
#   sudo bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/witness-localsdsys.sh --listed USER --unlisted USER --lan ADDRESS \
#        --sdsys-password-file FILE [--commit]
#
# ***NEEDS sudo (root) AND A PERSON AT THE TERMINAL.***  Without --commit it prints every command it would run and runs none.  With --commit it
# changes the two lists (they must be EMPTY when it starts, and are cleared again at the end) and makes ssh logins that the person answers: the
# Linux password of USER at ssh's prompt, and the SD password of sdsys at SD's prompt where a row says so.  The SD password of sdsys for the API
# rows comes from FILE (root only, never on a command line); the ssh rows ask the person to type it.
#
#   --listed USER     an SD user (uid >= 1000, in sdusers) whose Linux password the person knows; it is listed and unlisted by this run
#   --unlisted USER   another such user, never listed
#   --lan ADDRESS     this machine's own non-loopback address (sshd then sees a remote host that is not loopback)
#
# ROWS (each prints the real command, the state before and after, matches the SUCCESS wording and REFUSES on the failure wording)
#   L0  the install: /usr/local/bin/sd-sdsys root:root 0755, the sudoers line, both lists absent
#   L1  empty lists: the listed user's ssh -t <user>@localhost sd-sdsys is refused by the helper (list-empty), no grant is audited
#   L2  empty lists: the listed user's program on the Unix socket signs in as sdsys - refused (10922), the reason carries no why=
#   L3  local.sdsys's helper verb lists the user: root:root 0644, the name in the file
#   L4  the listed user from 127.0.0.1 with the RIGHT SD password of sdsys: the session is the administrator, audited with the user's name
#   L5  the same with a WRONG password: refused, 14175, audited "wrong password"
#   L6  the unlisted user from 127.0.0.1: refused by the helper (not-listed)
#   L7  the listed user over --lan (not loopback): refused by the helper (not-local)
#   L8  su sdsys from this (root's) shell: 10195, audited with why=
#   L9  sudo -u sdsys sd from this shell: 10195, audited with why=
#   L10 the console (the person logs in at the VM's console as the listed user and types sd-sdsys): refused (not-ssh), read from the journal
#   L11 the API list holds the user: its PAM login on the Unix socket signs in as sdsys and is the administrator, audited from=this machine user=
#   L12 the same user by sudo -u from another login: refused (the login is not the listed user's)
#   L13 the unlisted user's PAM login on the Unix socket: refused, why=not-listed
#   L14 the listed user on loopback TCP: refused (SDSYS never over TCP from this machine)
#   L15 both lists cleared: absent again
# Exit 0 every row passed, 1 a row failed or was not reached, 2 it could not run.
#
# START-HISTORY:
# 18 Nov 26 dm  S.267 - written; syntax-checked (bash -n), NOT run.
# 19 Nov 26 dm  first run (Ubuntu 24.04, package dev20261119c, driven by .claude/vmtools/drive-localsdsys.py on the owner's word): 53 of 54; L10's
#               wait read a line already on the terminal, so the console login came after L15 - it now empties the terminal first.
# END-HISTORY

set -u
SELF="$(readlink -f "$0")"
HERE="$(dirname "$SELF")"
SDSYS=/usr/local/sdsys
SD_BIN=$SDSYS/bin/sd
ELEV=/usr/local/sbin/sd-elevate
WRAP=/usr/local/bin/sd-sdsys
AUDIT=$SDSYS/audit
SSH_LIST=/etc/sdcore/sdsys-local-ssh
API_LIST=/etc/sdcore/sdsys-local-api
PROBE_SRC=$HERE/scram-probe.py
PROBE_PUB=/var/tmp/sd-witness-localsdsys-probe.py
COMMIT=0
LISTED="" UNLISTED="" LAN="" PWFILE=""
PASS=0 FAIL=0 NOT_REACHED=0

usage() { echo "usage: $0 --listed USER --unlisted USER --lan ADDRESS --sdsys-password-file FILE [--commit]" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --commit) COMMIT=1; shift ;;
    --listed) [ $# -ge 2 ] || usage; LISTED=$2; shift 2 ;;
    --unlisted) [ $# -ge 2 ] || usage; UNLISTED=$2; shift 2 ;;
    --lan) [ $# -ge 2 ] || usage; LAN=$2; shift 2 ;;
    --sdsys-password-file) [ $# -ge 2 ] || usage; PWFILE=$2; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$LISTED" ] && [ -n "$UNLISTED" ] && [ -n "$LAN" ] && [ -n "$PWFILE" ] || usage

say() { printf '%s\n' "$*"; }
strip() { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g'; }
ck_says()   { if printf '%s' "$3" | grep -qF -- "$2"; then PASS=$((PASS + 1)); say "  [PASS] $1: found \"$2\""; else FAIL=$((FAIL + 1)); say "  [FAIL] $1: did NOT find \"$2\""; fi; }
ck_absent() { if printf '%s' "$3" | grep -qF -- "$2"; then FAIL=$((FAIL + 1)); say "  [FAIL] $1: FOUND \"$2\""; else PASS=$((PASS + 1)); say "  [PASS] $1: absent \"$2\""; fi; }
ck_true()   { if [ "$2" = yes ]; then PASS=$((PASS + 1)); say "  [PASS] $1"; else FAIL=$((FAIL + 1)); say "  [FAIL] $1 ($3)"; fi; }
not_reached() { NOT_REACHED=$((NOT_REACHED + 1)); FAIL=$((FAIL + 1)); say "  [FAIL] $1: NOT REACHED"; }
run_show() { say "      > $*"; }

finish() {
  say ""
  say "witness-localsdsys: $PASS passed, $FAIL failed ($NOT_REACHED not reached)"
  if [ "$COMMIT" -eq 1 ]; then
    rm -f "$PROBE_PUB"
  fi
  [ "$FAIL" -eq 0 ] && [ "$PASS" -gt 0 ] && exit 0
  exit 1
}

say "witness-localsdsys: listed=$LISTED unlisted=$UNLISTED lan=$LAN password-file=$PWFILE commit=$COMMIT"
say "  sd: $SD_BIN  helper: $ELEV  wrapper: $WRAP  audit: $AUDIT  lists: $SSH_LIST $API_LIST"
if [ "$COMMIT" -eq 1 ]; then
  [ "$(id -u)" -eq 0 ] || { say "witness-localsdsys: CANNOT RUN - --commit needs root (sudo bash $SELF ...)"; exit 2; }
  [ -r "$PWFILE" ] && [ "$(stat -c '%u %a' "$PWFILE")" = "0 600" ] || { say "witness-localsdsys: CANNOT RUN - $PWFILE must be root's, mode 600"; exit 2; }
  for u in "$LISTED" "$UNLISTED"; do
    id -u "$u" >/dev/null 2>&1 || { say "witness-localsdsys: CANNOT RUN - no Linux user $u"; exit 2; }
  done
  [ -x "$SD_BIN" ] || { say "witness-localsdsys: CANNOT RUN - SD is not installed ($SD_BIN)"; exit 2; }
  if [ -e "$SSH_LIST" ] || [ -L "$SSH_LIST" ] || [ -e "$API_LIST" ] || [ -L "$API_LIST" ]; then
    say "witness-localsdsys: CANNOT RUN - a list is not empty (it must start as delivered): $(ls -l "$SSH_LIST" "$API_LIST" 2>&1 | tr '\n' ' ')"
    exit 2
  fi
  install -o root -g root -m 0644 "$PROBE_SRC" "$PROBE_PUB" || { say "witness-localsdsys: CANNOT RUN - could not copy scram-probe.py"; exit 2; }
fi
USOCK=$(sed -n 's#^ListenStream=\(/.*\)#\1#p' /usr/lib/systemd/system/sdclient.socket 2>/dev/null | head -1)
say "  the API's Unix socket, from /usr/lib/systemd/system/sdclient.socket: '${USOCK:-none}'"
KH=$(mktemp -d /tmp/witness-localsdsys.XXXXXX)
trap 'rm -rf "$KH"' EXIT
T0=$(date +%s)

audit_mark() { AUD_BEFORE=$(wc -l < "$AUDIT" 2>/dev/null || echo 0); }
audit_new() { tail -n +"$((AUD_BEFORE + 1))" "$AUDIT" 2>/dev/null; }
journal_since() { journalctl -t sd-elevate --since "@$1" -o cat --no-pager 2>/dev/null; }

# An ssh login of $1 to $2 asking for sd-sdsys, kept on a terminal with script(1) (never a pipe: ssh needs the tty for the password prompts).
ssh_try() {   # $1 user, $2 host, $3 what the person types
  local log
  log=$KH/ssh-$RANDOM.log
  say "      > script -q -e -c 'ssh -t -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KH/known_hosts -o PubkeyAuthentication=no $1@$2 sd-sdsys' $log"
  if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)"; SSH_OUT=""; return 0; fi
  say "      THE PERSON TYPES: $3"
  script -q -e -c "ssh -t -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KH/known_hosts -o PubkeyAuthentication=no $1@$2 sd-sdsys" "$log" < /dev/tty > /dev/tty 2>&1
  SSH_OUT=$(strip < "$log")
  printf '%s\n' "$SSH_OUT" | tail -n 25 | sed -e 's/^/      | /'
}

# scram-probe in a PAM login session of $1 (pam_loginuid sets its login uid to $1, as a console login does)
probe_login_as() {   # $1 user, then scram-probe arguments
  say "      > systemd-run --uid=$1 -p PAMName=login --pipe --wait python3 $PROBE_PUB ${*:2}   (password from $PWFILE)"
  if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)"; PROBE_OUT=""; return 0; fi
  PROBE_OUT=$(timeout 90 systemd-run --quiet --uid="$1" -p PAMName=login --pipe --wait --collect -E SD_SCRAM_PASSWORD="$(cat "$PWFILE")" \
      -E HOME="$(getent passwd "$1" | cut -d: -f6)" sh -c 'echo "loginuid=$(cat /proc/self/loginuid)"; exec python3 "$0" "$@"' "$PROBE_PUB" "${@:2}" 2>&1 < /dev/null)
  printf '%s\n' "$PROBE_OUT" | tail -n 20 | sed -e 's/^/      | /'
}
probe_sudo_as() {   # $1 user, then scram-probe arguments: the same probe by sudo -u from THIS login (the login uid stays the person's)
  say "      > sudo -u $1 --preserve-env=SD_SCRAM_PASSWORD python3 $PROBE_PUB ${*:2}"
  if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)"; PROBE_OUT=""; return 0; fi
  PROBE_OUT=$(SD_SCRAM_PASSWORD="$(cat "$PWFILE")" timeout 90 sudo -u "$1" --preserve-env=SD_SCRAM_PASSWORD python3 "$PROBE_PUB" "${@:2}" 2>&1 < /dev/null)
  printf '%s\n' "$PROBE_OUT" | tail -n 20 | sed -e 's/^/      | /'
}
helper_root() {   # the helper's verb as root with no sudo caller (sdsys_local_caller asks SUDO_USER, which sudo gave this witness)
  say "      > env -u SUDO_USER -u SUDO_UID -u SUDO_GID -u SUDO_COMMAND $ELEV $*"
  if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)"; HELPER_OUT=""; return 0; fi
  HELPER_OUT=$(env -u SUDO_USER -u SUDO_UID -u SUDO_GID -u SUDO_COMMAND "$ELEV" "$@" 2>&1)
  printf '%s\n' "$HELPER_OUT" | sed -e 's/^/      | /'
}
state() { say "      state: ssh list: $(cat "$SSH_LIST" 2>/dev/null | tr '\n' ' ' || true)$( [ -e "$SSH_LIST" ] || echo '(absent)')  api list: $(cat "$API_LIST" 2>/dev/null | tr '\n' ' ' || true)$( [ -e "$API_LIST" ] || echo '(absent)')"; }

say ""
say "=== L0 the install ==="
if [ "$COMMIT" -eq 1 ]; then
  ck_true "L0a /usr/local/bin/sd-sdsys is root:root 0755" "$( [ "$(stat -c '%U:%G %a' "$WRAP" 2>/dev/null)" = "root:root 755" ] && echo yes || echo no)" "$(stat -c '%U:%G %a' "$WRAP" 2>&1)"
  SUD=$(cat /etc/sudoers.d/sdcore 2>/dev/null)
  ck_says "L0b the sudoers drop-in names sd-elevate sdsys-session for %sdusers" "/usr/local/sbin/sd-elevate netcred-dir, /usr/local/sbin/sd-elevate sdsys-session" "$SUD"
  ck_absent "L0c and no wildcard after it" "sdsys-session *" "$SUD"
  state
else
  not_reached "L0 (dry run)"
fi

say ""
say "=== L1 empty lists: the listed user's ssh from 127.0.0.1 is refused by the helper ==="
audit_mark; T1=$(date +%s)
ssh_try "$LISTED" 127.0.0.1 "the Linux password of $LISTED (SD must not ask for anything)"
if [ "$COMMIT" -eq 1 ]; then
  ck_says "L1 the helper refused it: list-empty" "sdsys-session: list-empty" "$SSH_OUT"
  ck_absent "L1b SD never asked for the password of sdsys" "SD password of sdsys:" "$SSH_OUT"
  ck_absent "L1c no grant was audited" "elevation granted" "$(audit_new)"
  ck_says "L1d the system log has the refusal" "sdsys-session refused: list-empty" "$(journal_since "$T1")"
else not_reached "L1"; fi

say ""
say "=== L2 empty lists: the listed user's program on the Unix socket, as sdsys ==="
audit_mark
probe_login_as "$LISTED" --unix "$USOCK" --user sdsys --account sdsys WHO
if [ "$COMMIT" -eq 1 ]; then
  ck_says "L2 the login as the listed user" "loginuid=$(id -u "$LISTED")" "$PROBE_OUT"
  ck_says "L2b refused" "SCRAM: login REFUSED" "$PROBE_OUT"
  ck_absent "L2c not verified" "SCRAM: server signature VERIFIED" "$PROBE_OUT"
  NEW=$(audit_new)
  ck_says "L2d audited as today: opened by $LISTED" "reason=sdsys API session opened by $LISTED from" "$NEW"
  ck_absent "L2e with no why= (the list is not in use)" "why=" "$NEW"
else not_reached "L2"; fi

say ""
say "=== L3 the helper lists $LISTED on the ssh list ==="
helper_root sdsys-local ssh add "$LISTED"
if [ "$COMMIT" -eq 1 ]; then
  ck_says "L3 the helper says it added the name" "sdsys local ssh: added $LISTED; listed now: $LISTED" "$HELPER_OUT"
  ck_absent "L3b and did not refuse" "REFUSED" "$HELPER_OUT"
  ck_true "L3c the list is root:root 0644 and holds the name" "$( [ "$(stat -c '%U:%G %a' "$SSH_LIST" 2>/dev/null)" = "root:root 644" ] && [ "$(cat "$SSH_LIST")" = "$LISTED" ] && echo yes || echo no)" "$(ls -l "$SSH_LIST" 2>&1)"
  helper_root sdsys-local ssh add "$UNLISTED-nosuch"
  ck_says "L3d a user that does not exist is refused by name" "there is no Linux user" "$HELPER_OUT"
  state
else not_reached "L3"; fi

say ""
say "=== L4 the listed user from 127.0.0.1 with the RIGHT SD password of sdsys ==="
audit_mark
ssh_try "$LISTED" 127.0.0.1 "the Linux password of $LISTED, then at 'SD password of sdsys:' the RIGHT one, then at the SD prompt: who.am.i  and then: quit"
if [ "$COMMIT" -eq 1 ]; then
  NEW=$(audit_new)
  ck_says "L4 SD asked for the password of sdsys" "SD password of sdsys:" "$SSH_OUT"
  ck_says "L4b the session says it is the administrator, reached from $LISTED's login" "SD administration granted: this session is the sdsys OS user, reached from" "$SSH_OUT"
  ck_says "L4c audited with the user's name" "elevation granted reason=sdsys local ssh user=$LISTED" "$NEW"
  ck_absent "L4d and not refused" "elevation refused" "$NEW"
else not_reached "L4"; fi

say ""
say "=== L5 the same with a WRONG SD password of sdsys ==="
audit_mark
ssh_try "$LISTED" 127.0.0.1 "the Linux password of $LISTED, then at 'SD password of sdsys:' a WRONG one"
if [ "$COMMIT" -eq 1 ]; then
  NEW=$(audit_new)
  ck_says "L5 refused with 14175" "The SD password of sdsys was not right" "$SSH_OUT"
  ck_says "L5b audited as a wrong password" "elevation refused reason=sdsys local ssh wrong password user=$LISTED" "$NEW"
  ck_absent "L5c no grant" "elevation granted" "$NEW"
else not_reached "L5"; fi

say ""
say "=== L6 the UNLISTED user from 127.0.0.1 ==="
audit_mark; T6=$(date +%s)
ssh_try "$UNLISTED" 127.0.0.1 "the Linux password of $UNLISTED"
if [ "$COMMIT" -eq 1 ]; then
  ck_says "L6 the helper refused it: not-listed" "sdsys-session: not-listed" "$SSH_OUT"
  ck_absent "L6b SD never asked for the password of sdsys" "SD password of sdsys:" "$SSH_OUT"
  ck_absent "L6c no grant" "elevation granted" "$(audit_new)"
else not_reached "L6"; fi

say ""
say "=== L7 the listed user over $LAN (not loopback) ==="
audit_mark
ssh_try "$LISTED" "$LAN" "the Linux password of $LISTED"
if [ "$COMMIT" -eq 1 ]; then
  ck_says "L7 the helper refused it: not-local" "sdsys-session: not-local" "$SSH_OUT"
  ck_absent "L7b no grant" "elevation granted" "$(audit_new)"
else not_reached "L7"; fi

say ""
say "=== L8 su sdsys from this shell (its login is $(cat /proc/self/loginuid 2>/dev/null)'s uid) ==="
audit_mark
say "      > su -s /bin/sh sdsys -c '$SD_BIN' < /dev/null"
if [ "$COMMIT" -eq 1 ]; then
  OUT=$(timeout 60 su -s /bin/sh sdsys -c "$SD_BIN" < /dev/null 2>&1 | strip)
  printf '%s\n' "$OUT" | tail -n 8 | sed -e 's/^/      | /'
  NEW=$(audit_new)
  ck_says "L8 10195" "This session runs as sdsys but the machine was not logged in as" "$OUT"
  ck_says "L8b audited with why= (the list is in use)" "elevation refused reason=sdsys session without a sdsys login why=" "$NEW"
  ck_absent "L8c no grant" "elevation granted" "$NEW"
else not_reached "L8"; fi

say ""
say "=== L9 sudo -u sdsys sd from this shell ==="
audit_mark
say "      > sudo -u sdsys $SD_BIN < /dev/null"
if [ "$COMMIT" -eq 1 ]; then
  OUT=$(timeout 60 sudo -u sdsys "$SD_BIN" < /dev/null 2>&1 | strip)
  printf '%s\n' "$OUT" | tail -n 8 | sed -e 's/^/      | /'
  NEW=$(audit_new)
  ck_says "L9 10195" "This session runs as sdsys but the machine was not logged in as" "$OUT"
  ck_says "L9b audited with why=" "elevation refused reason=sdsys session without a sdsys login why=" "$NEW"
  ck_absent "L9c no grant" "elevation granted" "$NEW"
else not_reached "L9"; fi

say ""
say "=== L10 the console ==="
T10=$(date +%s)
say "      THE PERSON: at the VM's own console, log in as $LISTED, type  sd-sdsys  and press Enter, log out, then press Enter here."
if [ "$COMMIT" -eq 1 ]; then
  # 19 Nov 26: throw away what is already waiting on the terminal first - the first run's L10 read a line left over from an earlier ssh row and went
  #   on at once, so the console login came after L15 had cleared the lists and the helper said list-empty, not not-ssh.
  while read -r -t 0.3 _ < /dev/tty; do :; done
  read -r _ < /dev/tty
  J=$(journal_since "$T10")
  printf '%s\n' "$J" | tail -n 5 | sed -e 's/^/      | /'
  ck_says "L10 the helper refused the console session: not-ssh" "sdsys-session refused: not-ssh" "$J"
  ck_absent "L10b and admitted nobody" "sdsys-session: $LISTED admitted" "$J"
else not_reached "L10"; fi

say ""
say "=== L11 the API list holds $LISTED: its program on the Unix socket signs in as sdsys ==="
helper_root sdsys-local api add "$LISTED"
audit_mark
probe_login_as "$LISTED" --unix "$USOCK" --user sdsys --account sdsys WHO
if [ "$COMMIT" -eq 1 ]; then
  NEW=$(audit_new)
  ck_says "L11 the helper listed it" "sdsys local api: added $LISTED" "$HELPER_OUT"
  ck_says "L11b the login as the listed user" "loginuid=$(id -u "$LISTED")" "$PROBE_OUT"
  ck_says "L11c verified" "SCRAM: server signature VERIFIED" "$PROBE_OUT"
  ck_absent "L11d not refused" "SCRAM: login REFUSED" "$PROBE_OUT"
  ck_says "L11e the administrator, audited with the user's name" "elevation granted reason=sdsys api from=this machine user=$LISTED" "$NEW"
else not_reached "L11"; fi

say ""
say "=== L12 the same user by sudo -u from this login ==="
audit_mark
probe_sudo_as "$LISTED" --unix "$USOCK" --user sdsys --account sdsys WHO
if [ "$COMMIT" -eq 1 ]; then
  NEW=$(audit_new)
  ck_says "L12 refused" "SCRAM: login REFUSED" "$PROBE_OUT"
  ck_says "L12b audited: listed, but the login behind it is another's" "(listed by local.sdsys api, but the login behind it is" "$NEW"
  ck_absent "L12c no grant" "elevation granted" "$NEW"
else not_reached "L12"; fi

say ""
say "=== L13 the unlisted user's program on the Unix socket ==="
audit_mark
probe_login_as "$UNLISTED" --unix "$USOCK" --user sdsys --account sdsys WHO
if [ "$COMMIT" -eq 1 ]; then
  NEW=$(audit_new)
  ck_says "L13 refused" "SCRAM: login REFUSED" "$PROBE_OUT"
  ck_says "L13b audited with why=not-listed" "reason=sdsys API session opened by $UNLISTED from" "$NEW"
  ck_says "L13c" "why=not-listed" "$NEW"
  ck_absent "L13d no grant" "elevation granted" "$NEW"
else not_reached "L13"; fi

say ""
say "=== L14 the listed user on loopback TCP ==="
audit_mark
probe_login_as "$LISTED" --host 127.0.0.1 --user sdsys --account sdsys WHO
if [ "$COMMIT" -eq 1 ]; then
  NEW=$(audit_new)
  # refused at the login, or not listened for at all when the API is closed to TCP (remote.api off): either way never verified
  ck_absent "L14 not verified" "SCRAM: server signature VERIFIED" "$PROBE_OUT"
  ck_says "L14a the probe connected as the listed user" "loginuid=$(id -u "$LISTED")" "$PROBE_OUT"
  ck_absent "L14b no grant" "elevation granted" "$NEW"
else not_reached "L14"; fi

say ""
say "=== L15 both lists cleared ==="
helper_root sdsys-local ssh clear
H1=$HELPER_OUT
helper_root sdsys-local api clear
if [ "$COMMIT" -eq 1 ]; then
  ck_says "L15 the ssh list cleared" "sdsys local ssh: cleared, none listed" "$H1"
  ck_says "L15b the api list cleared" "sdsys local api: cleared, none listed" "$HELPER_OUT"
  ck_true "L15c both files are absent" "$( [ ! -e "$SSH_LIST" ] && [ ! -e "$API_LIST" ] && echo yes || echo no)" "$(ls -l "$SSH_LIST" "$API_LIST" 2>&1 | tr '\n' ' ')"
  state
else not_reached "L15"; fi

say "  (started $T0, the journal lines of this run: journalctl -t sd-elevate --since @$T0)"
finish
