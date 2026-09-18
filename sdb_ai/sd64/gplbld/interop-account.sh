#!/usr/bin/env bash
#
# interop-account.sh - a throwaway SD account for the TLS interop run between
#                      SD Core for Linux and SD Core for Windows.
#
#   bash      /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/interop-account.sh
#   sudo bash /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/interop-account.sh --create
#   sudo bash /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/interop-account.sh --remove
#
# No argument is a dry run: it prints the plan and changes nothing.
# --create asks for two passwords at the terminal, hidden: the Linux password
# for the throwaway account (CREATE.ACCOUNT prompts for it when it creates the
# Linux user) and the SD password for the API.  Neither is ever on a command
# line, in the log or in the mailbox; hand the SD password to the Windows side
# yourself.
# Exit 0 every check passed, 1 a check failed, 2 it could not run.
# The log goes to /var/tmp/interop-account.<date>.log.
#
# WHY (owner, 15 Sep 2026, "do it"): RELEASE_1.1 41's last witness points a
# Windows client at this machine's API.  It needs an ordinary account with the
# API and an SD password.  18 Sep 26, the teardown (S.28): the API is open to
# every account except SDSYS, so the account is an ordinary one - no tier, no
# sdapi join.  Test accounts are disposable, and --remove takes this one away
# again.
#
# --create follows the new administrator route (18 Sep 26, S.26): everything
# that needs rights runs as the sdsys OS user, the one administrator, on a
# local session.
#   A  CREATE.ACCOUNT USER zzinterop, which creates the Linux user itself (the
#      owner's rule) and asks for its password.  The register record must
#      exist; field 5 (the suspension flag) must be blank - a plain account.
#   T  THE ABSENCE HALF: zzinterop is in sdusers, and the legacy sdadmin and
#      sdapi groups do not exist.
#   P  MODIFY.PASSWORD zzinterop.  "Password set for account zzinterop", and
#      the $cred record is on disk.
#   L  THE PROOF THE ACCOUNT IS USABLE: scram-probe logs in over 127.0.0.1 and
#      over this machine's LAN address.  Each login must show TLS 1.3, a
#      verified server signature, the account entered and WHO naming
#      zzinterop, with no refusal.  The LAN login must not carry 10174's
#      refusal (that door is SDSYS's now).  That row is the one a Windows
#      client depends on.
#
# --remove: DELETE.ACCOUNT through SD, then userdel -r.  It removes a leftover
# $cred record, then checks nothing of the account is left.

set -u

SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
REGISTER="$SDSYS/accounts"
ACCOUNTS_ROOT=/home/sd/user_accounts
ACC=zzinterop
ADIR="$ACCOUNTS_ROOT/$ACC"
CRED="$SDSYS/\$cred/$ACC"
SPROBE="$(dirname "$SELF")/scram-probe.py"
REFUSED_10174="SDSYS may be reached through the API only from this machine"

MODE=dry
[ $# -le 1 ] || { echo "interop-account: one argument at most" >&2; exit 2; }
case "${1:-}" in
    "")        MODE=dry ;;
    --create)  MODE=create ;;
    --remove)  MODE=remove ;;
    -h|--help) sed -n '2,16p' "$0"; exit 2 ;;
    *) echo "interop-account: unknown argument '$1'" >&2; exit 2 ;;
esac

LOG="/var/tmp/interop-account.$(date +%Y%m%d-%H%M%S).log"
[ "$MODE" = dry ] || exec > >(tee -a "$LOG") 2>&1

PASS=0
FAIL=0
PW=""
PW2=""
LW=""
LW2=""

say() { printf '%s\n' "$*"; }
ck() {
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        PASS=$((PASS + 1)); say "  [PASS] $name: expected '$want', got '$got'"
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: expected '$want', got '$got'"
    fi
}
ck_says() {
    local name="$1" needle="$2" text="$3"
    if printf '%s' "$text" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1)); say "  [PASS] $name: found \"$needle\""
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: did NOT find \"$needle\""
    fi
}
ck_absent() {
    local name="$1" needle="$2" text="$3"
    if printf '%s' "$text" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: FOUND \"$needle\""
    else
        PASS=$((PASS + 1)); say "  [PASS] $name: absent \"$needle\""
    fi
}

yesno_user()  { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group() { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_dir()   { [ -d "$1" ] && echo yes || echo no; }
yesno_file()  { [ -e "$1" ] && echo yes || echo no; }
in_group()    { id -nG "$ACC" 2>/dev/null | tr ' ' '\n' | grep -qx "$1" && echo yes || echo no; }
strip()       { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g'; }

state() {
    say "  state: user=$(yesno_user "$ACC") group=$(yesno_group "sdu_$ACC") dir=$(yesno_dir "$ADIR")" \
        "register=$(yesno_file "$REGISTER/$ACC") cred=$(yesno_file "$CRED")" \
        "sdadmin_group=$(yesno_group sdadmin) sdapi_group=$(yesno_group sdapi)"
}

# 18 Sep 26 (S.26): THE ADMINISTRATOR SESSION - the sdsys OS user, local.
# CPROC grants it K$ADMINISTRATOR (no ssh env, uid 999) and LOGIN puts it in
# the sdsys account.  A root session would be refused outright (10176).
sd_sdsys() {
    local title="$1" body line out; shift
    say "  --- sd session as sdsys: $title ---" >&2
    body=$'\n''TERM 200,9999'
    for line in "$@"; do say "      > $line" >&2; body="$body"$'\n'"$line"; done
    body="$body"$'\n''OFF'$'\n'
    out=$(cd "$SDSYS" && printf '%s' "$body" | sudo -u sdsys timeout 90 "$SD" 2>&1 | strip)
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

# userdel refuses (exit 8) while the user owns a process, so wait, then say why.
del_user() {
    local n=0 err urc
    while pgrep -u "$ACC" >/dev/null 2>&1 && [ "$n" -lt 20 ]; do sleep 1; n=$((n + 1)); done
    err=$(userdel -r "$ACC" 2>&1); urc=$?
    if [ "$urc" -eq 0 ]; then
        say "  userdel -r $ACC: done (waited ${n}s)${err:+ - $err}"
    else
        say "  userdel -r $ACC: FAILED, exit $urc (8 = still owns a process) - ${err:-no message}"
    fi
}

verdict() {
    PW=""; PW2=""; LW=""; LW2=""
    say ""
    say "=== verdict ============================================"
    say "  passed: $PASS   failed: $FAIL"
    state
    if [ "$PASS" -eq 0 ]; then
        say "interop-account: FAILED - nothing passed, so nothing was measured."
        exit 1
    fi
    if [ "$FAIL" -ne 0 ]; then
        say "interop-account: FAILED - $FAIL check(s) failed (above)."
        [ "$MODE" = create ] && say "  Take it away with: sudo bash $SELF --remove"
        exit 1
    fi
    if [ "$MODE" = create ]; then
        say "interop-account: READY - $ACC logs in to the SD API over TLS 1.3 from 127.0.0.1 and from $LANIP."
        say "  For the Windows side: host $LANIP, port 4243, user and account $ACC,"
        say "  and the SD password you typed - give it directly, not through the mailbox."
        say "  Remove it after the run: sudo bash $SELF --remove"
    else
        say "interop-account: REMOVED - nothing of $ACC is left."
    fi
    exit 0
}

LANIP=$(ip -4 -o addr show scope global 2>/dev/null | awk 'NR==1 { split($4, a, "/"); print a[1] }')

say "interop-account: $MODE"
say "  date     : $(date -Is)"
say "  uid      : $(id -u) ($(id -un))"
say "  sd       : $SD"
say "  install  : $(sed -n 's/^commit=//p' "$SDSYS/.sdcore-install" 2>/dev/null) $(sed -n 's/^installed=//p' "$SDSYS/.sdcore-install" 2>/dev/null)"
say "  account  : $ACC ($ADIR)"
say "  LAN      : ${LANIP:-none found}"
say "  probe    : $SPROBE"
[ "$MODE" = dry ] || say "  log      : $LOG"

for p in "$SD" "$REGISTER" "$ACCOUNTS_ROOT" "$SPROBE"; do
    [ -e "$p" ] || { say "interop-account: CANNOT RUN - $p does not exist."; exit 2; }
done

if [ "$MODE" = dry ]; then
    state
    say "  DRY RUN - the plan, nothing executed:"
    say "    --create: CREATE.ACCOUNT USER $ACC (asks for its Linux password);"
    say "              MODIFY.PASSWORD $ACC (SD password asked at the terminal);"
    say "              scram-probe --host 127.0.0.1 and --host ${LANIP:-<LAN address>} --user $ACC --account $ACC WHO"
    say "              Every SD step runs as the sdsys OS user (S.26)."
    say "    --remove: DELETE.ACCOUNT $ACC; userdel -r $ACC; a leftover \$cred/$ACC"
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    say "interop-account: CANNOT RUN - --$MODE needs root (it becomes sdsys for the SD steps). Re-run as: sudo bash $SELF --$MODE"
    exit 2
fi

if [ "$MODE" = remove ]; then
    state
    if [ ! -e "$REGISTER/$ACC" ] && [ "$(yesno_user "$ACC")" = no ] && [ ! -e "$CRED" ]; then
        say "interop-account: CANNOT RUN - nothing of $ACC exists, so there is nothing to remove."
        exit 2
    fi
    if [ -e "$REGISTER/$ACC" ]; then
        OUT=$(sd_sdsys "DELETE.ACCOUNT $ACC, answering Y" "DELETE.ACCOUNT $ACC" "Y")
    fi
    [ "$(yesno_user "$ACC")" = yes ] && del_user
    [ -e "$CRED" ] && { rm -f "$CRED"; say "  removed a leftover \$cred/$ACC"; }
    ck "R1 no register record" no "$(yesno_file "$REGISTER/$ACC")"
    ck "R2 no account directory" no "$(yesno_dir "$ADIR")"
    ck "R3 no Linux user" no "$(yesno_user "$ACC")"
    ck "R4 no sdu_$ACC group" no "$(yesno_group "sdu_$ACC")"
    ck "R5 no \$cred record" no "$(yesno_file "$CRED")"
    verdict
fi

# ---------------------------------------------------------------- --create
state
DIRTY=0
[ "$(yesno_user "$ACC")" = yes ]          && { say "  DIRTY: Linux user $ACC exists"; DIRTY=1; }
[ "$(yesno_group "sdu_$ACC")" = yes ]     && { say "  DIRTY: group sdu_$ACC exists"; DIRTY=1; }
[ "$(yesno_dir "$ADIR")" = yes ]          && { say "  DIRTY: $ADIR exists"; DIRTY=1; }
[ "$(yesno_file "$REGISTER/$ACC")" = yes ] && { say "  DIRTY: register record $ACC exists"; DIRTY=1; }
[ "$(yesno_file "$CRED")" = yes ]         && { say "  DIRTY: \$cred/$ACC exists"; DIRTY=1; }
if [ "$DIRTY" -eq 1 ]; then
    say "interop-account: CANNOT RUN - the ground is not clear. Run: sudo bash $SELF --remove"
    exit 2
fi
if [ -z "$LANIP" ]; then
    say "interop-account: CANNOT RUN - no LAN address, so the row a Windows client depends on could not be measured."
    exit 2
fi
if [ ! -r /dev/tty ]; then
    say "interop-account: CANNOT RUN - no terminal to ask for the passwords on."
    exit 2
fi

# The Linux password CREATE.ACCOUNT will prompt for (hidden, twice inside SD).
read -r -s -p "Linux password for the throwaway account $ACC (not shown, 12 characters or more): " LW </dev/tty; echo
read -r -s -p "The same again: " LW2 </dev/tty; echo
if [ "$LW" != "$LW2" ]; then
    say "interop-account: CANNOT RUN - the two entries differ; nothing was changed."
    exit 2
fi
if [ "${#LW}" -lt 12 ]; then
    say "interop-account: CANNOT RUN - the password is under 12 characters; nothing was changed."
    exit 2
fi
case "$LW" in
    *[[:space:]]*) say "interop-account: CANNOT RUN - the password contains a space or tab; nothing was changed."; exit 2 ;;
esac
# The SD password for the API.
read -r -s -p "SD password for $ACC (not shown, 12 characters or more): " PW </dev/tty; echo
read -r -s -p "The same again: " PW2 </dev/tty; echo
if [ "$PW" != "$PW2" ]; then
    say "interop-account: CANNOT RUN - the two entries differ; nothing was changed."
    exit 2
fi
if [ "${#PW}" -lt 12 ]; then
    say "interop-account: CANNOT RUN - the password is under 12 characters; nothing was changed."
    exit 2
fi
case "$PW" in
    *[[:space:]]*) say "interop-account: CANNOT RUN - the password contains a space or tab; nothing was changed."; exit 2 ;;
esac
say "  passwords : ${#LW} and ${#PW} characters (not shown)"

say ""
say "=== A. create $ACC ============================================"
say "  --- sd session as sdsys: CREATE.ACCOUNT USER $ACC, then the Linux"
say "      password twice (SET_PASSWD prompts inside SD, hidden) ---"
OUT=$(cd "$SDSYS" && printf '\nTERM 200,9999\nCREATE.ACCOUNT USER %s\n%s\n%s\nOFF\n' "$ACC" "$LW" "$LW" \
      | sudo -u sdsys timeout 90 "$SD" 2>&1 | strip)
printf '%s\n' "$OUT" | grep -vF -- "$LW" | sed -e 's/^/      | /'
ck "A1 the register record exists" yes "$(yesno_file "$REGISTER/$ACC")"
ck "A2 the account directory exists" yes "$(yesno_dir "$ADIR")"
ck "A3 the Linux user exists" yes "$(yesno_user "$ACC")"
if [ ! -e "$REGISTER/$ACC" ]; then
    say "  STOPPING - no register record, so nothing further can be measured."
    verdict
fi

say ""
say "=== T. a plain account ============================================"
ck "T1 register field 5 (the suspension flag) is blank" "" \
   "$(sed -n '5p' "$REGISTER/$ACC" 2>/dev/null)"
ck "T2 $ACC is in sdusers" yes "$(in_group sdusers)"
ck "T3 the sdadmin group does not exist" no "$(yesno_group sdadmin)"
ck "T4 the sdapi group does not exist" no "$(yesno_group sdapi)"

say ""
say "=== P. the SD password ============================================"
say "  --- sd session as sdsys: MODIFY.PASSWORD $ACC, the password twice (not shown) ---"
OUT=$(cd "$SDSYS" && printf '\nTERM 200,9999\nMODIFY.PASSWORD %s\n%s\n%s\nOFF\n' "$ACC" "$PW" "$PW" \
      | sudo -u sdsys timeout 120 "$SD" 2>&1 | strip)
printf '%s\n' "$OUT" | grep -vF -- "$PW" | sed -e 's/^/      | /'
ck_says "P1 MODIFY.PASSWORD reported it set" "Password set for account $ACC" "$OUT"
ck_absent "P1b and not a failure" "Unable to set password" "$OUT"
ck "P2 the \$cred record is on disk" yes "$(yesno_file "$CRED")"

say ""
say "=== L. logins over TLS, from this machine and from its LAN address ============================================"
for host in 127.0.0.1 "$LANIP"; do
    say "  --- scram-probe over $host as $ACC, WHO ---"
    say "      > SD_SCRAM_PASSWORD=(not shown) python3 $SPROBE --host $host --user $ACC --account $ACC WHO"
    OUT=$(SD_SCRAM_PASSWORD="$PW" timeout 90 python3 "$SPROBE" --host "$host" --user "$ACC" --account "$ACC" WHO 2>&1)
    printf '%s\n' "$OUT" | sed -e 's/^/      | /'
    ck_says "L1 $host: TLS 1.3" "tls      : TLSv1.3" "$OUT"
    ck_says "L2 $host: server signature verified" "SCRAM: server signature VERIFIED" "$OUT"
    ck_says "L3 $host: account entered" "account $ACC: entered" "$OUT"
    ck "L4 $host: WHO names $ACC" yes "$(printf '%s\n' "$OUT" | grep -Eq "^\| +[0-9]+ $ACC\$" && echo yes || echo no)"
    ck_absent "L5 $host: not refused" "SCRAM: login REFUSED" "$OUT"
    ck_absent "L6 $host: no SDSYS-only refusal (10174)" "$REFUSED_10174" "$OUT"
done

verdict
