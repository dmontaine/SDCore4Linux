#!/usr/bin/env bash
#
# witness-release-run.sh - three witnesses that need a throwaway account, in
#                          one owner-run pass on one install:
#     S.9   LOGIN's $release prompt (5026) takes N on Enter and at end of input
#     Q.28  RUN of a runfile path over 128 characters says so (10918)
#     S.2   a root session LOGTOs an account whose group is newer than it
#     Q.22  logtoaccess: a root session keeps its access across LOGTOs (2b)
#     S.10  RUN folds the program name (3b)
#     W.2   Enter at 2050 means N; W.3  6133 cancels on Enter or C (5b)
#     S.4   OS.EXECUTE runs at ADMINISTRATOR, 10054 at PROGRAMMER (6)
#     S.3   Y at the release prompt keeps STANDARD's omit list out (7)
#     Q.13  MODIFY.ACCOUNT ADD/DELETE and ELEVATION REFUSED reach the audit
#           trail (8); a second throwaway, zzrel2, is made and removed
#     S.12  10043's claim: a session open during a GRANT enters the account
#           but cannot write in it, against a fresh session's write (10)
#     S.6   a plain-sd administrator reaches SH; LOGTO reloads the grants (11)
#     S.5   the 10 Sep parity audit's witness list (12, 15); a third throwaway,
#           zzrel3, carries SD's "SD account" stamp and is deleted by SD
#     Q.17  MODIFY.PASSWORD's administrator arm, checked in /etc/shadow (13)
#     Q.12  ssh into a SUSPENDED account is refused, after a control (14);
#           a throwaway ssh key is installed for zzrel1 only
#     ALSO TOUCHES REAL STATE: section 12 runs UPDATE.ACCOUNTS ALL, which
#     updates every account's VOC as each install does.
#
#   bash      /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/witness-release-run.sh
#   sudo bash /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/witness-release-run.sh --commit
#
# ***NEEDS sudo, ONLY FOR --commit.***  The dry run changes nothing.
# Exit 0 every check passed, 1 a check failed (or was not reached), 2 it could
# not run.  The log goes to /var/tmp, which survives a reboot (the 14 Sep
# witness-tierchange log in /tmp did not).
#
# ===========================================================================
# THE THROWAWAY, AND WHY NOT don
# ===========================================================================
# don is the owner's login and never a fixture.  This makes Linux user zzrel1,
# ADOPTs it as an SD account the way witness-tierchange.sh does (a marker + the
# one-shot `sd -internal create-account USER <name> ADOPT no.query`, no password
# prompt), and removes both at the end, whatever happened.
#
# ===========================================================================
# WHAT EACH PART MEASURES
# ===========================================================================
# S.2  This script's own process started BEFORE sdu_zzrel1 existed, so its
#      supplementary groups lack it - exactly the stale case.  Every root sd it
#      starts inherits that list, and the S.2 fix (sdext_eguid.c, initgroups
#      before the euid drop) must refresh it.  The script PRINTS its own group
#      list and the new group's gid, and if the group is somehow already in the
#      list the S.2 rows are NOT REACHED rather than passed.
#
# S.9  As zzrel1: BASIC compiles two tiny programs from bp (a directory file, so
#      the source is written straight to disk).  ZZREL sets $release field 2 to
#      L0.9-9; ZZSHOW prints it.  Then three sign-ons:
#        (a) a blank first line - that line is the prompt's answer.  Enter must
#            mean N: the session goes on to WHO, and "Please answer Y or N"
#            (5027) never appears.  Before the fix a blank re-asked, and the next
#            line (TERM) re-asked again.
#        (b) </dev/null - end of input at the prompt.  Must finish, not spin.
#        (c) RUN BP ZZSHOW - field 2 must STILL be L0.9-9, so N changed nothing.
#      Success wording: the NEW prompt text "(y/<n>)?", so a run against an
#      install without the message change fails rather than passing on 5025.
#
# Q.28 As zzrel1: ZZSHOW's object copied into a DEEP directory, reached through
#      a VOC F-pointer zzdeep.out written by a third program (ZZVOC), so that
#      the run path exceeds 128 characters with a short record name, then RUN
#      ZZDEEP zzshow.  Must print 10918's words; "Invalid runfile pathname"
#      (1135, the old message), "Message not found" (10918 not installed) or
#      "not found" (the lookup never reached the length check) fail it.
#      ***NOT A LONG RECORD NAME, AND THE 13:07 RUN SHOWED WHY:*** MAXIDLEN
#      defaults to 63 (config.c:139) and valid_id (op_dio3.c) rejects a longer
#      id, so a 100-character name answered "Program ... not found" before RUN
#      ever measured the path.  With a 63-character id, a 32-character account
#      name and /home/sd/user_accounts, a bp.out path tops out at 126 - so the
#      limit is only reachable through a deeper data file, as here.
#
# THE PIPED-SESSION RULES ARE THE PROJECT'S: a blank first line, TERM 200,9999,
# every session ends in OFF, every sd has a timeout.
#
set -u

SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"

SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
REGISTER="$SDSYS/accounts"
ACCOUNTS_ROOT=/home/sd/user_accounts

ACC=zzrel1
COMMIT=0
LOG=""
FAKE_REL="L0.9-9"

PASS=0
FAIL=0
NOT_REACHED=0
MADE_USER=0
MADE_ACCOUNT=0
# Section 8 (Q.13) needs a SECOND account to grant to - don is never a fixture.
ACC2=zzrel2
MADE_USER2=0
MADE_ACCOUNT2=0
# Section 12 (S.5) needs an account whose Linux user carries SD's "SD account"
# stamp, to reach DELETE.ACCOUNT's SD-created branch and REMOVE.HOME.
ACC3=zzrel3
MADE_USER3=0
MADE_ACCOUNT3=0
SSHDIR=""

usage() { sed -n '2,16p' "$0"; exit 2; }

for arg in "$@"; do
    case "$arg" in
        --commit) COMMIT=1 ;;
        --log=*)  LOG="${arg#--log=}" ;;
        -h|--help) usage ;;
        *) echo "witness-release-run: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done

MARKER="$SDSYS/\$adopt.$ACC"
ADIR="$ACCOUNTS_ROOT/$ACC"
[ -n "$LOG" ] || LOG="/var/tmp/witness-release-run.$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

say()   { printf '%s\n' "$*"; }
head2() { say ""; say "=== $* ============================================"; }

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
not_reached() {
    FAIL=$((FAIL + 1)); NOT_REACHED=$((NOT_REACHED + 1))
    say "  [NOT REACHED] $1 - a precondition failed above, so it measured nothing"
}

yesno_user()  { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group() { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_dir()   { [ -d "$1" ] && echo yes || echo no; }
yesno_file()  { [ -e "$1" ] && echo yes || echo no; }

strip() { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g'; }

# A piped session.  $1 who ("root" or the account), $2 title, then commands.
# Narration to fd 2; sd's own output on fd 1; SD_RC holds the exit (124 = timeout).
SD_RC=0
# FIRST_LINE is the session's first stdin line - blank by the project's rule,
# which is also what answers a sign-on prompt.  Set it to Y for one call to
# answer a prompt yes (section 7), and it is reset to blank after every call.
FIRST_LINE=""
run_sd() {
    local who="$1" title="$2"; shift 2
    say "  --- sd session as $who: $title ---" >&2
    [ -n "$FIRST_LINE" ] && say "      (first line: '$FIRST_LINE')" >&2
    local line
    for line in "$@"; do say "      > $line" >&2; done
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; SD_RC=0; FIRST_LINE=""; return 0; fi
    local body out
    body="$FIRST_LINE"$'\n''TERM 200,9999'
    FIRST_LINE=""
    for line in "$@"; do body="$body"$'\n'"$line"; done
    body="$body"$'\n''OFF'$'\n'
    if [ "$who" = root ]; then
        out=$(cd "$SDSYS" && printf '%s' "$body" | timeout 60 "$SD" 2>&1; echo "rc=${PIPESTATUS[1]}")
    elif [ "${who#root:}" != "$who" ]; then
        # root:<person> - a root session whose SUDO_USER names <person>, which
        # is who CPROC's grant.administrator asks about (K$REAL.USER).
        out=$(cd "$SDSYS" && printf '%s' "$body" | SUDO_USER="${who#root:}" timeout 60 "$SD" 2>&1; echo "rc=${PIPESTATUS[1]}")
    else
        out=$(cd "$ADIR" && printf '%s' "$body" | timeout 60 runuser -u "$who" -- "$SD" 2>&1; echo "rc=${PIPESTATUS[1]}")
    fi
    SD_RC=$(printf '%s' "$out" | tail -1 | sed -n 's/^rc=//p')
    out=$(printf '%s' "$out" | sed '$d' | strip)
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    say "      (exit $SD_RC)" >&2
    printf '%s' "$out"
}

# A sign-on as the account with stdin at END OF INPUT from the start.
run_sd_eof() {
    say "  --- sd session as $ACC: stdin </dev/null (end of input at once) ---" >&2
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; SD_RC=0; return 0; fi
    local out
    out=$(cd "$ADIR" && timeout 30 runuser -u "$ACC" -- "$SD" </dev/null 2>&1; echo "rc=$?")
    SD_RC=$(printf '%s' "$out" | tail -1 | sed -n 's/^rc=//p')
    out=$(printf '%s' "$out" | sed '$d' | strip)
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    say "      (exit $SD_RC)" >&2
    printf '%s' "$out"
}

run_oneshot() {   # the installer's ADOPT form
    say "  --- sd one-shot, cwd $SDSYS, </dev/null, timeout 25 s ---" >&2
    say "      > $SD $*" >&2
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; return 0; fi
    local out
    out=$(cd "$SDSYS" && timeout 25 "$SD" "$@" </dev/null 2>&1 | strip)
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

# userdel refuses (exit 8) while the user owns a process, and an ssh login
# (section 14) leaves a systemd --user manager behind for some seconds after
# the session ends.  The 14:38 run printed only "FAILED" with the exit code
# and message thrown away, and zzrel1 was left.  So wait, then say why.
del_user() {   # $1 user, $2 suffix for the report line
    local u="$1" tag="${2:-}" n=0 err urc
    while pgrep -u "$u" >/dev/null 2>&1 && [ "$n" -lt 20 ]; do sleep 1; n=$((n + 1)); done
    pgrep -u "$u" >/dev/null 2>&1 && say "  $u still owns processes after ${n}s: $(pgrep -a -u "$u" | tr '\n' ';')"
    err=$(userdel -r "$u" 2>&1); urc=$?
    if [ "$urc" -eq 0 ]; then
        say "  userdel -r $u: done$tag (waited ${n}s)${err:+ - $err}"
    else
        say "  userdel -r $u: FAILED$tag, exit $urc (8 = still owns a process) - ${err:-no message} - remove it by hand"
    fi
}

cleanup() {
    local rc=$?
    [ "$COMMIT" -eq 1 ] || exit $rc
    head2 "CLEANUP - removing whatever this run made"
    [ -e "$MARKER" ] && { rm -f "$MARKER"; say "  removed a leftover ADOPT marker"; }
    [ -e "$SDSYS/\$adopt.$ACC2" ] && { rm -f "$SDSYS/\$adopt.$ACC2"; say "  removed a leftover ADOPT marker for $ACC2"; }
    if [ "$MADE_ACCOUNT2" -eq 1 ] && [ -e "$REGISTER/$ACC2" ]; then
        say "  deleting the SD account $ACC2 through SD"
        printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC2"$'\n''Y'$'\n''OFF'$'\n' \
            | (cd "$SDSYS" && timeout 90 "$SD") >/dev/null 2>&1
    fi
    if [ "$MADE_USER2" -eq 1 ] && id -u "$ACC2" >/dev/null 2>&1; then
        del_user "$ACC2"
    fi
    say "  left behind ($ACC2): register=$(yesno_file "$REGISTER/$ACC2")" \
        "dir=$(yesno_dir "$ACCOUNTS_ROOT/$ACC2") user=$(yesno_user "$ACC2")" \
        "group=$(yesno_group "sdu_$ACC2")"
    if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$REGISTER/$ACC" ]; then
        say "  deleting the SD account through SD"
        printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC"$'\n''Y'$'\n''OFF'$'\n' \
            | (cd "$SDSYS" && timeout 90 "$SD") >/dev/null 2>&1
    fi
    if [ "$MADE_USER" -eq 1 ] && id -u "$ACC" >/dev/null 2>&1; then
        del_user "$ACC"
    fi
    say "  left behind: register=$(yesno_file "$REGISTER/$ACC")" \
        "dir=$(yesno_dir "$ADIR") user=$(yesno_user "$ACC")" \
        "group=$(yesno_group "sdu_$ACC") marker=$(yesno_file "$MARKER")"
    # Section 12's zzrel3 is normally deleted by the section itself (that is
    # the thing measured); this is the fallback if it stopped part-way.
    [ -e "$SDSYS/\$adopt.$ACC3" ] && rm -f "$SDSYS/\$adopt.$ACC3"
    if [ "$MADE_ACCOUNT3" -eq 1 ] && [ -e "$REGISTER/$ACC3" ]; then
        say "  deleting the SD account $ACC3 through SD (fallback)"
        printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC3"$'\n''Y'$'\n''OFF'$'\n' \
            | (cd "$SDSYS" && timeout 90 "$SD") >/dev/null 2>&1
    fi
    if [ "$MADE_USER3" -eq 1 ] && id -u "$ACC3" >/dev/null 2>&1; then
        del_user "$ACC3" " (fallback)"
    fi
    if [ "$MADE_USER3" -eq 1 ]; then
        say "  left behind ($ACC3): register=$(yesno_file "$REGISTER/$ACC3")" \
            "dir=$(yesno_dir "$ACCOUNTS_ROOT/$ACC3") user=$(yesno_user "$ACC3")" \
            "group=$(yesno_group "sdu_$ACC3") home=$(yesno_dir "/home/$ACC3")"
    fi
    [ -n "$SSHDIR" ] && [ -d "$SSHDIR" ] && { rm -rf "$SSHDIR"; say "  removed the witness ssh key ($SSHDIR)"; }
    say "  log: $LOG"
    exit $rc
}
trap cleanup EXIT

# ==========================================================================
say "witness-release-run: $( [ "$COMMIT" -eq 1 ] && echo 'COMMIT - it will change this system' || echo 'DRY RUN - it changes nothing' )"
say "  date       : $(date -Is)"
say "  uid        : $(id -u) ($(id -un))"
say "  sd         : $SD"
say "  install    : $(sed -n 's/^commit=//p' "$SDSYS/.sdcore-install" 2>/dev/null) $(sed -n 's/^installed=//p' "$SDSYS/.sdcore-install" 2>/dev/null)"
say "  account    : $ACC  ($ADIR)"
say "  log        : $LOG"

head2 "0. preconditions and the ground being clear"
for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT"; do
    [ -e "$p" ] || { say "witness-release-run: CANNOT RUN - $p does not exist."; exit 2; }
done
command -v runuser >/dev/null || { say "witness-release-run: CANNOT RUN - runuser not found."; exit 2; }
if [ "$COMMIT" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
    say "witness-release-run: CANNOT RUN - --commit needs root."
    say "  re-run as: sudo bash $SELF --commit"
    exit 2
fi
DIRTY=0
[ "$(yesno_user "$ACC")" = yes ]  && { say "  DIRTY: Linux user $ACC exists"; DIRTY=1; }
[ "$(yesno_group "sdu_$ACC")" = yes ] && { say "  DIRTY: group sdu_$ACC exists"; DIRTY=1; }
[ "$(yesno_dir "$ADIR")" = yes ] && { say "  DIRTY: $ADIR exists"; DIRTY=1; }
[ "$(yesno_file "$REGISTER/$ACC")" = yes ] && { say "  DIRTY: register record $ACC exists"; DIRTY=1; }
[ "$(yesno_file "$MARKER")" = yes ] && { say "  DIRTY: an ADOPT marker for $ACC exists"; DIRTY=1; }
[ "$(yesno_user "$ACC2")" = yes ]  && { say "  DIRTY: Linux user $ACC2 exists"; DIRTY=1; }
[ "$(yesno_group "sdu_$ACC2")" = yes ] && { say "  DIRTY: group sdu_$ACC2 exists"; DIRTY=1; }
[ "$(yesno_dir "$ACCOUNTS_ROOT/$ACC2")" = yes ] && { say "  DIRTY: $ACCOUNTS_ROOT/$ACC2 exists"; DIRTY=1; }
[ "$(yesno_file "$REGISTER/$ACC2")" = yes ] && { say "  DIRTY: register record $ACC2 exists"; DIRTY=1; }
[ "$(yesno_user "$ACC3")" = yes ]  && { say "  DIRTY: Linux user $ACC3 exists"; DIRTY=1; }
[ "$(yesno_group "sdu_$ACC3")" = yes ] && { say "  DIRTY: group sdu_$ACC3 exists"; DIRTY=1; }
[ "$(yesno_dir "$ACCOUNTS_ROOT/$ACC3")" = yes ] && { say "  DIRTY: $ACCOUNTS_ROOT/$ACC3 exists"; DIRTY=1; }
[ "$(yesno_file "$REGISTER/$ACC3")" = yes ] && { say "  DIRTY: register record $ACC3 exists"; DIRTY=1; }
[ "$(yesno_dir "/home/$ACC3")" = yes ] && { say "  DIRTY: /home/$ACC3 exists"; DIRTY=1; }
if [ "$DIRTY" -eq 1 ]; then
    say "witness-release-run: CANNOT RUN - the ground is not clear (above)."
    say "  This script will not touch state it did not create."
    exit 2
fi
say "  ground clear: $ACC exists as no user, group, directory, record or marker."
STAMP=$(sed -n '2p' "$SDSYS/voc_template/\$release" 2>/dev/null)
say "  voc_template \$release field 2 (what a new account gets): '$STAMP'"
[ "$STAMP" != "$FAKE_REL" ] || { say "witness-release-run: CANNOT RUN - the install is already at $FAKE_REL, so nothing would differ."; exit 2; }
# THE SCRIPT'S OWN GROUPS - the S.2 input.  Printed before the group exists.
say "  this process's groups (before): $(id -G)"

# ==========================================================================
head2 "1. adopt $ACC (no password prompt)"
say "  useradd -m $ACC"
if [ "$COMMIT" -eq 1 ]; then
    if useradd -m "$ACC"; then MADE_USER=1; say "  created Linux user $ACC (uid $(id -u "$ACC"))"
    else say "witness-release-run: CANNOT RUN - useradd failed; nothing else attempted."; exit 2; fi
fi
say "  touch $MARKER"
[ "$COMMIT" -eq 1 ] && touch "$MARKER"
run_oneshot -internal create-account USER "$ACC" ADOPT no.query >/dev/null
[ "$COMMIT" -eq 1 ] && rm -f "$MARKER"

ADOPTED=0
if [ "$COMMIT" -eq 1 ]; then
    ck "A1 the register record exists (the gate for the rest)" yes "$(yesno_file "$REGISTER/$ACC")"
    ck "A2 the account directory exists" yes "$(yesno_dir "$ADIR")"
    ck "A3 its bp directory exists" yes "$(yesno_dir "$ADIR/bp")"
    if [ -e "$REGISTER/$ACC" ] && [ -d "$ADIR/bp" ]; then ADOPTED=1; MADE_ACCOUNT=1; fi
    [ -e "$REGISTER/$ACC" ] && MADE_ACCOUNT=1
fi

# ==========================================================================
head2 "2. S.2 - a root session LOGTOs $ACC, whose group is newer than this process"
GID_NEW=$(getent group "sdu_$ACC" | cut -d: -f3)
say "  sdu_$ACC gid: '${GID_NEW:-none}'; this process's groups: $(id -G)"
if [ "$COMMIT" -eq 1 ]; then
    if [ "$ADOPTED" -ne 1 ] || [ -z "$GID_NEW" ]; then
        not_reached "S2.a LOGTO $ACC entered it"; not_reached "S2.b no Error 3001"
    elif id -G | tr ' ' '\n' | grep -qx "$GID_NEW"; then
        say "  this process ALREADY holds sdu_$ACC, so this is not the stale case."
        not_reached "S2.a LOGTO $ACC entered it (stale groups)"; not_reached "S2.b no Error 3001 (stale groups)"
    else
        say "  this process does NOT hold sdu_$ACC - the stale case the fix is for."
        OUT=$(run_sd root "LOGTO $ACC, WHO" "LOGTO $ACC" "WHO")
        if printf '%s' "$OUT" | grep -qE "^[[:space:]]*[0-9]+[[:space:]]+$ACC([[:space:]]|$)"; then
            ck "S2.a WHO reports the session in $ACC" yes yes
        else
            ck "S2.a WHO reports the session in $ACC" yes no
        fi
        ck_absent "S2.b no Error 3001" "Error 3001" "$OUT"
    fi
fi

# ==========================================================================
# THE PORT'S verify-logtoaccess (its PRE_RELEASE 91), AS IT TRANSFERS.  The port
# lost K$ADMINISTRATOR on the first LOGTO, so the SECOND was refused; ***ONE
# SUCCESSFUL LOGTO DOES NOT TELL THE FIX FROM THE DEFECT*** - hence arrivals
# are COUNTED.  Here USR_ADMIN is set once (cproc grant.administrator) and
# nothing clears it, so this is expected to hold - measured, not assumed.  The
# port's other half (an administrator signed in as themselves enters any
# account) does not transfer: a plain session lacks the account's sdu_ group,
# so the filesystem would refuse the VOC even if SD admitted it.
head2 "2b. logtoaccess - a root session keeps its access across LOGTOs"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "L1 two arrivals in $ACC" "L2 one arrival in sdsys" "L3 no refusal" "LC.1 control refused" "LC.2 control stayed"; do
        not_reached "$r"; done
else
    OUT=$(run_sd root "LOGTO $ACC, LOGTO sdsys, LOGTO $ACC" \
          "LOGTO $ACC" "WHO" "LOGTO sdsys" "WHO" "LOGTO $ACC" "WHO")
    if [ "$COMMIT" -eq 1 ]; then
        ck "L1 WHO reported $ACC twice (both LOGTOs into it arrived)" 2 \
           "$(printf '%s' "$OUT" | grep -cE "^[[:space:]]*[0-9]+[[:space:]]+$ACC([[:space:]]|$)")"
        ck "L2 WHO reported sdsys once, between them" 1 \
           "$(printf '%s' "$OUT" | grep -cE "^[[:space:]]*[0-9]+[[:space:]]+sdsys([[:space:]]|$)")"
        ck_absent "L3a no 10003" "User not allowed in requested account" "$OUT"
        ck_absent "L3b no SDSYS gate refusal" "restricted to privileged users" "$OUT"
    fi
    # THE CONTROL: without it L1-L3 cannot tell "the administrator keeps its
    # access" from "the gate is open to everybody".
    OUT=$(run_sd "$ACC" "control: LOGTO sdsys as $ACC in plain sd" "LOGTO sdsys" "WHO")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "LC.1 control: plain $ACC is refused SDSYS" "restricted to privileged users" "$OUT"
        if printf '%s' "$OUT" | grep -qE "^[[:space:]]*[0-9]+[[:space:]]+$ACC([[:space:]]|$)"; then
            ck "LC.2 control: and stayed in $ACC" yes yes
        else
            ck "LC.2 control: and stayed in $ACC" yes no
        fi
    fi
fi

# ==========================================================================
head2 "3. setup as $ACC - compile ZZREL (sets \$release field 2) and ZZSHOW (prints it)"
SRC_REL='open "voc" to f else stop "ZZREL: cannot open voc"
read r from f, "$release" else stop "ZZREL: no $release record"
r<2> = "'"$FAKE_REL"'"
write r to f, "$release"
crt "ZZREL wrote field 2 = ":r<2>
end'
SRC_SHOW='open "voc" to f else stop "ZZSHOW: cannot open voc"
read r from f, "$release" else stop "ZZSHOW: no $release record"
crt "ZZSHOW field 2 = ":r<2>
end'
# Section 6 (S.4): runs an OS command, then says so.  10054 aborts it first
# when the account may not use OS.EXECUTE.
SRC_OS='os.execute "true"
crt "ZZOS ran OS.EXECUTE"
end'
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -eq 1 ]; then
    printf '%s\n' "$SRC_REL"  > "$ADIR/bp/zzrel"
    printf '%s\n' "$SRC_SHOW" > "$ADIR/bp/zzshow"
    printf '%s\n' "$SRC_OS"   > "$ADIR/bp/zzos"
    chown "$ACC:$(id -gn "$ACC")" "$ADIR/bp/zzrel" "$ADIR/bp/zzshow" "$ADIR/bp/zzos"
    say "  wrote $ADIR/bp/zzrel, zzshow and zzos"
fi
# ***THE SETUP RUNS THE PROGRAMS BY THEIR EXACT, LOWER-CASE NAMES.***  The
# 14 Sep 12:55 run typed RUN BP ZZREL and RUN answered "Program BP.OUT ZZREL
# not found" - BASIC had folded the name to zzrel and RUN did not fold it back.
# That was a real defect (fixed in cproc int.run the same day), but it left
# every S.9 and Q.28 row NOT REACHED.  So the fold is now its own row, F1, and
# nothing else depends on it.
SETUP_OK=0
if [ "$COMMIT" -eq 0 ] || [ "$ADOPTED" -eq 1 ]; then
    OUT=$(run_sd "$ACC" "compile both, set field 2, show it" \
          "BASIC BP ZZREL" "BASIC BP ZZSHOW" "BASIC BP ZZOS" "RUN BP zzrel" "RUN BP zzshow")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "B1 ZZREL wrote the fake release" "ZZREL wrote field 2 = $FAKE_REL" "$OUT"
        ck_says "B2 ZZSHOW reads it back" "ZZSHOW field 2 = $FAKE_REL" "$OUT"
        printf '%s' "$OUT" | grep -qF "ZZSHOW field 2 = $FAKE_REL" && SETUP_OK=1
    fi
else
    not_reached "B1 ZZREL wrote the fake release"; not_reached "B2 ZZSHOW reads it back"
fi

head2 "3b. the RUN fold - RUN BP ZZSHOW, typed in upper case, finds bp.out/zzshow"
if [ "$COMMIT" -eq 1 ] && [ "$SETUP_OK" -ne 1 ]; then
    not_reached "F1 RUN BP ZZSHOW ran the program"; not_reached "F2 no 5073"
else
    OUT=$(run_sd "$ACC" "RUN BP ZZSHOW (upper case)" "RUN BP ZZSHOW")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says  "F1 RUN BP ZZSHOW ran the program" "ZZSHOW field 2 = " "$OUT"
        ck_absent "F2 no 'Program ... not found' (5073)" "not found" "$OUT"
    fi
fi

# ==========================================================================
head2 "4. S.9 - sign-on with \$release at $FAKE_REL"
if [ "$COMMIT" -eq 1 ] && [ "$SETUP_OK" -ne 1 ]; then
    for r in "S9a.1 new prompt text" "S9a.2 no 5027" "S9a.3 went on to WHO" "S9a.4 finished" \
             "S9b.1 prompt shown once" "S9b.2 finished at EOF" "S9c.1 field 2 unchanged"; do
        not_reached "$r"; done
else
    say "  (a) a blank first line answers the prompt"
    OUT=$(run_sd "$ACC" "blank line at the prompt, then WHO" "WHO")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says  "S9a.1 the prompt says its default" "Update VOC to new release (y/<n>)?" "$OUT"
        ck_absent "S9a.2 Enter was not refused (no 5027)" "Please answer Y or N" "$OUT"
        if printf '%s' "$OUT" | grep -qE "^[[:space:]]*[0-9]+[[:space:]]+$ACC([[:space:]]|$)"; then
            ck "S9a.3 the session went on to WHO" yes yes
        else
            ck "S9a.3 the session went on to WHO" yes no
        fi
        ck "S9a.4 it finished (not a timeout)" no "$( [ "$SD_RC" = 124 ] && echo yes || echo no )"
    fi
    say "  (b) end of input at the prompt"
    OUT=$(run_sd_eof)
    if [ "$COMMIT" -eq 1 ]; then
        ck "S9b.1 the prompt was shown exactly once" 1 "$(printf '%s' "$OUT" | grep -oF 'Update VOC to new release' | wc -l)"
        ck "S9b.2 it finished at end of input (not a timeout)" no "$( [ "$SD_RC" = 124 ] && echo yes || echo no )"
    fi
    say "  (c) N changed nothing"
    OUT=$(run_sd "$ACC" "RUN BP zzshow" "RUN BP zzshow")
    [ "$COMMIT" -eq 1 ] && ck_says "S9c.1 field 2 is still $FAKE_REL" "ZZSHOW field 2 = $FAKE_REL" "$OUT"
fi

# ==========================================================================
head2 "5. Q.28 - RUN of a runfile path over 128 characters"
DEEPDIR="$ADIR/zzdeep/$(printf 'd%.0s' $(seq 1 60))/$(printf 'e%.0s' $(seq 1 60))"
LPATH="$DEEPDIR/zzshow"
say "  data file   : VOC zzdeep.out -> $DEEPDIR"
say "  record name : zzshow (6 characters, under MAXIDLEN)"
say "  run path    : ${#LPATH} characters (limit 128)"
SRC_VOC='open "voc" to f else stop "ZZVOC: cannot open voc"
r = "F" : @fm : "'"$DEEPDIR"'"
write r to f, "zzdeep.out"
crt "ZZVOC wrote zzdeep.out"
end'
if [ "$COMMIT" -eq 1 ] && { [ "$SETUP_OK" -ne 1 ] || [ ! -f "$ADIR/bp.out/zzshow" ]; }; then
    for r in "Q0 the pointer was written" "Q1 10918's words" "Q2 not 1135" "Q3 10918 is installed" "Q4 the lookup reached the length check"; do
        not_reached "$r"; done
else
    if [ "$COMMIT" -eq 1 ]; then
        mkdir -p "$DEEPDIR" && cp "$ADIR/bp.out/zzshow" "$LPATH"
        chown -R "$ACC:$(id -gn "$ACC")" "$ADIR/zzdeep"
        printf '%s\n' "$SRC_VOC" > "$ADIR/bp/zzvoc"
        chown "$ACC:$(id -gn "$ACC")" "$ADIR/bp/zzvoc"
        say "  object at that path: $(yesno_file "$LPATH")"
    fi
    OUT=$(run_sd "$ACC" "write the pointer, then RUN ZZDEEP zzshow" \
          "BASIC BP ZZVOC" "RUN BP zzvoc" "RUN ZZDEEP zzshow")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says  "Q0 the VOC pointer was written" "ZZVOC wrote zzdeep.out" "$OUT"
        ck_says  "Q1 RUN names the limit (10918)" "Runfile pathname is longer than 128 characters" "$OUT"
        ck_absent "Q2 not the old 1135 message" "Invalid runfile pathname" "$OUT"
        ck_absent "Q3 10918 is installed" "Message not found" "$OUT"
        ck_absent "Q4 the lookup reached the length check (no 'not found')" "not found" "$OUT"
    fi
fi

# ==========================================================================

# ==========================================================================
# W.2 and W.3 - the port's rulings of 13 Sep 26 (its RELEASE_1.1_FIXES 33),
# adopted 14 Sep; the port's verify-promptenter legs 7 and 8, re-expressed.
# BEFORE THE TIER MOVES: STANDARD's omit list takes CREATE.FILE and
# DELETE.FILE, so this runs while zzrel1 is still ADMINISTRATOR.
#   2050 via SSELECT VOC SAMPLE 1 + CT VOC (CT only displays): Enter must
#        display nothing and let WHO run; the Y control must display it.
#   6133 via a two-component multifile: Enter and C must delete nothing and
#        leave both components and the dictionary on disk; the N control
#        must still delete the dictionary only (N then Y, in case 6140 asks).
head2 "5b. W.2 / W.3 - Enter at 2050 means N; 6133 cancels on Enter or C"
MF=zzpromptm
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "P1 2050 prompt" "P2 Enter showed nothing" "P3 WHO ran" "P4 Y control" "M0 multifile built" "M1 Enter cancels" "M2 C cancels" "M3 N control"; do not_reached "$r"; done
else
    OUT=$(run_sd "$ACC" "2050 answered with ENTER, then WHO" "SSELECT VOC SAMPLE 1" "CT VOC" "" "WHO")
    if [ "$COMMIT" -eq 1 ]; then
        ID7=$(printf '%s' "$OUT" | grep -o "First item '[^']*'" | head -1 | sed "s/First item '//; s/'$//")
        say "  first item of the list: '${ID7:-none}'"
        ck_says "P1 2050 was reached, showing (y/<n>)" "Use active select list (First item '$ID7') (y/<n>)?" "$OUT"
        if [ -n "$ID7" ] && printf '%s' "$OUT" | grep -qE "^VOC $ID7[[:space:]]*$"; then
            ck "P2 Enter displayed nothing (no 'VOC $ID7' record)" no yes
        else
            ck "P2 Enter displayed nothing (no 'VOC $ID7' record)" no no
        fi
        if printf '%s' "$OUT" | grep -qE "^[[:space:]]*[0-9]+[[:space:]]+$ACC([[:space:]]|$)"; then
            ck "P3 the session went on to WHO" yes yes
        else
            ck "P3 the session went on to WHO" yes no
        fi
    fi
    OUT=$(run_sd "$ACC" "control: 2050 answered Y" "SSELECT VOC SAMPLE 1" "CT VOC" "Y")
    if [ "$COMMIT" -eq 1 ]; then
        if [ -n "$ID7" ] && printf '%s' "$OUT" | grep -qE "^VOC $ID7[[:space:]]*$"; then
            ck "P4 control: Y displays 'VOC $ID7'" yes yes
        else
            ck "P4 control: Y displays 'VOC $ID7'" yes no
        fi
    fi

    OUT=$(run_sd "$ACC" "make the multifile $MF (components c1, c2)" \
          "CREATE.FILE $MF,c1" "CREATE.FILE $MF,c2" "CT VOC $MF")
    MF_OK=0
    if [ "$COMMIT" -eq 1 ]; then
        say "  on disk: $(ls -d "$ADIR/$MF"/* "$ADIR/$MF.dic" 2>&1 | tr '\n' ' ')"
        [ -d "$ADIR/$MF/c1" ] && [ -d "$ADIR/$MF/c2" ] && [ -e "$ADIR/$MF.dic" ] && MF_OK=1
        ck "M0 $MF has components c1, c2 and a dictionary on disk" 1 "$MF_OK"
    fi
    for ANS in "" "C"; do
        LABEL=$([ -z "$ANS" ] && echo ENTER || echo C)
        if [ "$COMMIT" -eq 1 ] && [ "$MF_OK" -ne 1 ]; then
            not_reached "M $LABEL cancels"; continue
        fi
        OUT=$(run_sd "$ACC" "DELETE.FILE $MF answered with $LABEL, then WHO" "DELETE.FILE $MF" "$ANS" "WHO")
        if [ "$COMMIT" -eq 1 ]; then
            ck_says  "M.$LABEL.1 6133 reached, showing (y/n/<c>)" "C cancel (y/n/<c>)?" "$OUT"
            ck_absent "M.$LABEL.2 no DATA portion deleted" "DATA portion '" "$OUT"
            ck_absent "M.$LABEL.3 no DICT portion deleted" "DICT portion '" "$OUT"
            ck "M.$LABEL.4 c1, c2 and the dictionary survive on disk" 1 \
               "$( [ -d "$ADIR/$MF/c1" ] && [ -d "$ADIR/$MF/c2" ] && [ -e "$ADIR/$MF.dic" ] && echo 1 || echo 0)"
            if printf '%s' "$OUT" | grep -qE "^[[:space:]]*[0-9]+[[:space:]]+$ACC([[:space:]]|$)"; then
                ck "M.$LABEL.5 the session went on to WHO" yes yes
            else
                ck "M.$LABEL.5 the session went on to WHO" yes no
            fi
        fi
    done
    if [ "$COMMIT" -eq 1 ] && [ "$MF_OK" -ne 1 ]; then
        not_reached "M3 N control"
    else
        OUT=$(run_sd "$ACC" "control: DELETE.FILE $MF answered N (then Y, if 6140 asks)" "DELETE.FILE $MF" "N" "Y")
        if [ "$COMMIT" -eq 1 ]; then
            ck_says "M3.a control: N deleted the dictionary" "DICT portion '" "$OUT"
            ck "M3.b control: the dictionary is gone and c1 remains" 1 \
               "$( [ ! -e "$ADIR/$MF.dic" ] && [ -d "$ADIR/$MF/c1" ] && echo 1 || echo 0)"
        fi
    fi
fi

# ==========================================================================
# S.4 - PRE_RELEASE 23's OS.EXECUTE gate (10054) on a PROGRAMMER account.  It
# was witnessed on STANDARD pete on 10 Sep, which could compile only because
# the per-tier VOC was not built yet; a STANDARD account has no BASIC now, so
# the witness it is owed is PROGRAMMER.  THE CONTROL COMES FIRST: at
# ADMINISTRATOR (in sdadmin) ZZOS must RUN, or the refusal after the move
# could be ZZOS failing for any reason at all.
head2 "6. S.4 - OS.EXECUTE runs at ADMINISTRATOR, then 10054 at PROGRAMMER"
if [ "$COMMIT" -eq 1 ] && { [ "$SETUP_OK" -ne 1 ] || [ ! -f "$ADIR/bp.out/zzos" ]; }; then
    for r in "O1 control ran" "O2 moved to PROGRAMMER" "O3 10054" "O4 did not run"; do not_reached "$r"; done
else
    OUT=$(run_sd "$ACC" "control: RUN BP zzos at ADMINISTRATOR" "RUN BP zzos")
    [ "$COMMIT" -eq 1 ] && ck_says "O1 control: ZZOS ran at ADMINISTRATOR" "ZZOS ran OS.EXECUTE" "$OUT"
    OUT=$(run_sd root "MODIFY.ACCOUNT $ACC PROGRAMMER" "MODIFY.ACCOUNT $ACC PROGRAMMER")
    [ "$COMMIT" -eq 1 ] && ck_says "O2 MODIFY.ACCOUNT reported the move (10109)" "is now PROGRAMMER" "$OUT"
    OUT=$(run_sd "$ACC" "RUN BP zzos at PROGRAMMER" "RUN BP zzos")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says  "O3 refused in 10054's words" "$ACC is not permitted to use OS.EXECUTE" "$OUT"
        ck_absent "O4 and the command did not run" "ZZOS ran OS.EXECUTE" "$OUT"
    fi
fi

# ==========================================================================
# S.3 - LOGIN update.voc's STANDARD filter.  MODIFY.ACCOUNT to STANDARD strips
# the omit list (basic, run...); then a sign-on answers Y to the $release
# prompt, which runs update.voc.  WITHOUT THE FILTER update.voc would copy
# basic and run straight back from newvoc.  So: after Y, basic and run are
# still absent, list (which STANDARD keeps) is present - the control that the
# reads work - and the next sign-on no longer asks, so Y really updated.
head2 "7. S.3 - Y at the release prompt on a STANDARD account keeps the omit list out"
if [ "$COMMIT" -eq 1 ] && [ "$SETUP_OK" -ne 1 ]; then
    for r in "U1 moved to STANDARD" "U2 basic absent before" "U3 prompt answered" "U4 basic still absent" "U5 run still absent" "U6 list present" "U7 no prompt after"; do not_reached "$r"; done
else
    OUT=$(run_sd root "MODIFY.ACCOUNT $ACC STANDARD" "MODIFY.ACCOUNT $ACC STANDARD")
    [ "$COMMIT" -eq 1 ] && ck_says "U1 MODIFY.ACCOUNT reported the move (10109)" "is now STANDARD" "$OUT"
    OUT=$(run_sd "$ACC" "before: CT VOC basic (blank answers the prompt N)" "CT VOC basic")
    [ "$COMMIT" -eq 1 ] && ck_says "U2 before: basic is absent" "Record 'basic' not found" "$OUT"
    # run_sd runs inside $( ), a subshell, so its own reset cannot reach here:
    # clear FIRST_LINE in THIS shell straight after, or every later session
    # would answer Y too.
    FIRST_LINE="Y"
    OUT=$(run_sd "$ACC" "answer Y, then CT VOC basic, run, list" "CT VOC basic" "CT VOC run" "CT VOC list")
    FIRST_LINE=""
    if [ "$COMMIT" -eq 1 ]; then
        ck_says  "U3 the prompt was there to answer" "Update VOC to new release (y/<n>)?" "$OUT"
        ck_says  "U4 THE ROW: basic is still absent after update.voc" "Record 'basic' not found" "$OUT"
        ck_says  "U5 THE ROW: run is still absent after update.voc" "Record 'run' not found" "$OUT"
        if printf '%s' "$OUT" | grep -qE '^VOC list[[:space:]]*$'; then
            ck "U6 control: list (kept by STANDARD) is present" yes yes
        else
            ck "U6 control: list (kept by STANDARD) is present" yes no
        fi
        ck "U6b it finished (not a timeout)" no "$( [ "$SD_RC" = 124 ] && echo yes || echo no )"
    fi
    OUT=$(run_sd "$ACC" "after: a plain sign-on" "WHO")
    [ "$COMMIT" -eq 1 ] && ck_absent "U7 Y updated the release: no prompt on the next sign-on" "Your VOC is at release level" "$OUT"
fi

# ==========================================================================
# Q.13 - THREE AUDIT RECORD TYPES THE TRAIL HAD NEVER HELD.  Measured 14 Sep:
# the trail on 984be50 (back to the 13 Sep 19:11 full install) held only
# ELEVATION GRANTED, LOGIN, LOGTO, LOGTO REFUSED and MODIFY.ACCOUNT TIER.
# The writers exist (modifya:246 ADD, :275 DELETE; cproc grant.administrator
# ELEVATION REFUSED), so each is driven once and the NEW lines of the trail
# are read - by line count, before and after, so an old record cannot pass.
# zzrel1 is STANDARD by now, so the refused elevation names a person who is
# not a registered administrator (10902).
head2 "8. Q.13 - ADD, DELETE and ELEVATION REFUSED reach the audit trail"
AUD="$SDSYS/audit"
if [ "$COMMIT" -eq 1 ] && { [ "$ADOPTED" -ne 1 ] || [ ! -f "$AUD" ]; }; then
    for r in "T1 zzrel2 adopted" "T2 ADD said" "T3 DELETE said" "T4 elevation refused" "T5 ADD record" "T6 DELETE record" "T7 REFUSED record"; do not_reached "$r"; done
else
    N0=0
    [ "$COMMIT" -eq 1 ] && N0=$(wc -l < "$AUD")
    say "  audit trail before: $N0 lines ($AUD)"
    say "  useradd -m $ACC2; ADOPT $ACC2"
    if [ "$COMMIT" -eq 1 ]; then
        if useradd -m "$ACC2"; then MADE_USER2=1; fi
        touch "$SDSYS/\$adopt.$ACC2"
    fi
    run_oneshot -internal create-account USER "$ACC2" ADOPT no.query >/dev/null
    [ "$COMMIT" -eq 1 ] && rm -f "$SDSYS/\$adopt.$ACC2"
    [ "$COMMIT" -eq 1 ] && [ -e "$REGISTER/$ACC2" ] && MADE_ACCOUNT2=1
    [ "$COMMIT" -eq 1 ] && ck "T1 $ACC2 adopted (register record)" yes "$(yesno_file "$REGISTER/$ACC2")"
    OUT=$(run_sd root "MODIFY.ACCOUNT $ACC ADD $ACC2, then DELETE" \
          "MODIFY.ACCOUNT $ACC ADD $ACC2" "MODIFY.ACCOUNT $ACC DELETE $ACC2")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "T2 ADD said so (10018)" "$ACC2 added to group sdu_$ACC" "$OUT"
        ck_says "T3 DELETE said so (10021)" "$ACC2 removed from group sdu_$ACC" "$OUT"
    fi
    OUT=$(run_sd "root:$ACC" "a root session whose SUDO_USER is $ACC (not an administrator)" "WHO")
    [ "$COMMIT" -eq 1 ] && ck_says "T4 elevation refused, in 10902's words" "$ACC is not a registered SD administrator" "$OUT"
    if [ "$COMMIT" -eq 1 ]; then
        NEW=$(tail -n +"$((N0 + 1))" "$AUD")
        say "  audit trail after: $(wc -l < "$AUD") lines; the new records naming $ACC:"
        printf '%s\n' "$NEW" | grep -F "$ACC" | sed -e 's/^/      | /'
        ck_says "T5 the ADD record is new in the trail" "MODIFY.ACCOUNT ADD account=$ACC to=$ACC2" "$NEW"
        ck_says "T6 the DELETE record is new in the trail" "MODIFY.ACCOUNT DELETE account=$ACC from=$ACC2" "$NEW"
        ck_says "T7 the ELEVATION REFUSED record is new, naming $ACC" "sudo=$ACC" "$(printf '%s\n' "$NEW" | grep -F 'ELEVATION REFUSED reason=not a registered administrator')"
    fi
fi

# ==========================================================================
# Sections 10-15 - the remaining owner witnesses, folded in 14 Sep 2026.
# who_in <account> <text>: WHO printed "<n> <account>" (with or without "from").
who_in() { printf '%s' "$2" | grep -qE "^[[:space:]]*[0-9]+[[:space:]]+$1([[:space:]]|$)"; }
ck_who() { if who_in "$2" "$3"; then ck "$1" yes yes; else ck "$1" yes no; fi; }
ck_line() { if printf '%s' "$3" | grep -qxF -- "$2"; then ck "$1" yes yes; else ck "$1" yes no; fi; }
ck_noline() { if printf '%s' "$3" | grep -qxF -- "$2"; then ck "$1" no yes; else ck "$1" no no; fi; }
ctx() { say "  [CONTEXT] $*"; }
GID1=$(getent group "sdu_$ACC" | cut -d: -f3)
A2DIR="$ACCOUNTS_ROOT/$ACC2"

# ==========================================================================
# S.12 - MESSAGE 10043's CLAIM.  A person with a session open at the moment of
# a GRANT is admitted by SD at once, but the session keeps the Linux groups it
# started with.  The 14:38 run on f2251e6 measured that such a session ENTERS
# (the message then said "refused by the filesystem").  From source it enters
# READ-ONLY: dh_open asks access() and opens a file it cannot write read-only
# (dh_open.c:118), the fvar takes FV_RDONLY (op_dio1.c:793), and COPY refuses
# a read-only target with 1431 before copying (copy:212).  So the stale session
# COPYs a VOC record and must be refused, with nothing on disk; the CONTROL, a
# session started after the grant, makes the same COPY and it must land - or
# the refusal could be COPY failing for any reason.
# zzrel1 is STANDARD since section 7, and STANDARD has no COPY (and no RUN,
# which section 11 needs - the 14:38 run lost H3 to that), so it moves to
# PROGRAMMER first.  VOC ids are lower case since plan M: the record is who.
# This is a plain session, so the S.2 initgroups refresh (root only) does not
# apply.  The live process's own group list is printed from /proc.
head2 "10. S.12 - a session open during GRANT enters read-only (message 10043)"
if [ "$COMMIT" -eq 1 ] && { [ "$ADOPTED" -ne 1 ] || [ "$MADE_ACCOUNT2" -ne 1 ]; }; then
    for r in "V0 PROGRAMMER" "G0 not yet granted" "G1 10043" "G2 stale groups" "G3 SD admitted" "G4 entered" "G6 write refused" "G6a no copy" "G6b nothing on disk" "G5 fresh session enters" "G7 control copied" "G7b control on disk"; do not_reached "$r"; done
else
    OUT=$(run_sd root "MODIFY.ACCOUNT $ACC PROGRAMMER (STANDARD has no COPY or RUN)" "MODIFY.ACCOUNT $ACC PROGRAMMER")
    [ "$COMMIT" -eq 1 ] && ck_says "V0 $ACC is now PROGRAMMER" "is now PROGRAMMER" "$OUT"
    say "  $ACC2 in sdu_$ACC before: $(id -nG "$ACC2" 2>/dev/null | tr ' ' '\n' | grep -cx "sdu_$ACC")"
    say "  --- sd session as $ACC2, STARTED BEFORE THE GRANT: WHO; (sleep 5); LOGTO $ACC; WHO; COPY FROM VOC who,zzstale ---"
    STALE_OUT=""
    if [ "$COMMIT" -eq 1 ]; then
        ck "G0 $ACC2 is not in sdu_$ACC before the grant" 0 "$(id -nG "$ACC2" | tr ' ' '\n' | grep -cx "sdu_$ACC")"
        STALEF=$(mktemp)
        ( cd "$A2DIR" && { printf '\nTERM 200,9999\nWHO\n'; sleep 5; printf 'LOGTO %s\nWHO\nCOPY FROM VOC who,zzstale\nOFF\n' "$ACC"; } \
            | timeout 60 runuser -u "$ACC2" -- "$SD" >"$STALEF" 2>&1 ) &
        BG=$!
        sleep 2
    fi
    OUT=$(run_sd root "GRANT $ACC TO $ACC2 (while that session sleeps)" "GRANT $ACC TO $ACC2")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "G1 GRANT printed 10043" "$ACC2 must log out of Linux and back in" "$OUT"
        SPID=$(pgrep -u "$ACC2" -x sd | head -1)
        SGRP=$(grep '^Groups:' "/proc/$SPID/status" 2>/dev/null)
        say "  the sleeping session: pid ${SPID:-none}, $SGRP (sdu_$ACC is gid $GID1)"
        if [ -n "$SPID" ] && [ -n "$SGRP" ] && ! printf '%s' "$SGRP" | tr ' \t' '\n\n' | grep -qx "$GID1"; then
            ck "G2 the open session's process lacks sdu_$ACC" yes yes
        else
            ck "G2 the open session's process lacks sdu_$ACC" yes no
        fi
        wait "$BG"
        STALE_OUT=$(strip < "$STALEF"); rm -f "$STALEF"
        printf '%s\n' "$STALE_OUT" | sed -e 's/^/      | /'
        ck_absent "G3 SD admitted the LOGTO (no 10003)" "User not allowed in requested account" "$STALE_OUT"
        ck_who "G4 the stale session entered $ACC" "$ACC" "$STALE_OUT"
        printf '%s' "$STALE_OUT" | grep -q 'Error 3001' && ctx "G4 it printed Error 3001"
        ck_says "G6 its COPY was refused, the VOC read-only (1431)" "File is read-only" "$STALE_OUT"
        ck_absent "G6a and COPY did not report a copy (6189)" "record(s) copied" "$STALE_OUT"
        ck "G6b zzstale is on disk in neither account's VOC" 0 "$(cat "$ADIR"/voc/%* "$A2DIR"/voc/%* 2>/dev/null | grep -a -c zzstale)"
    fi
    OUT=$(run_sd "$ACC2" "control: a session started AFTER the grant" "LOGTO $ACC" "WHO" "COPY FROM VOC who,zzctl")
    if [ "$COMMIT" -eq 1 ]; then
        ck_who "G5 control: a fresh session enters $ACC" "$ACC" "$OUT"
        ck_says "G7 control: the same COPY writes (6189)" "1 record(s) copied." "$OUT"
        ck "G7b control: zzctl is on disk in $ACC's VOC" yes "$( [ "$(cat "$ADIR"/voc/%* 2>/dev/null | grep -a -c zzctl)" -gt 0 ] && echo yes || echo no )"
    fi
fi

# ==========================================================================
# S.6 - A PLAIN-sd ADMINISTRATOR REACHES THE OS, AND A LOGTO RELOADS IT.
# zzrel2 is ADMINISTRATOR and in sdadmin, in plain sd (no USR_ADMIN), so SH runs
# only because LOGIN loaded K$SH from the tier.  After LOGTO into zzrel1
# (PROGRAMMER since section 10, no OS-ON) the grants reload from zzrel1's
# record: zzrel1's own compiled OS.EXECUTE program must then be refused naming
# zzrel2 (10054 prints process.username, op_sh.c:158).  SH itself is not in a
# PROGRAMMER VOC, which is why the second half uses OS.EXECUTE.  H3b names the
# 14:38 miss: zzrel1 was still STANDARD, so RUN was not in its VOC.
head2 "11. S.6 - plain-sd administrator: SH runs; after LOGTO a non-admin account, OS.EXECUTE is refused"
if [ "$COMMIT" -eq 1 ] && { [ "$ADOPTED" -ne 1 ] || [ "$MADE_ACCOUNT2" -ne 1 ] || [ ! -f "$ADIR/bp.out/zzos" ]; }; then
    for r in "H1 SH ran" "H2 in zzrel1" "H3 10054" "H3b RUN found" "H4 did not run"; do not_reached "$r"; done
else
    OUT=$(run_sd "$ACC2" "SH in its own account, then LOGTO $ACC and RUN BP zzos" \
          "SH echo zzsh-ran" "LOGTO $ACC" "WHO" "RUN BP zzos")
    if [ "$COMMIT" -eq 1 ]; then
        ck_line "H1 plain-sd ADMINISTRATOR: SH ran (output line zzsh-ran)" "zzsh-ran" "$OUT"
        ck_absent "H1b and was not refused 10053" "is not permitted to use the operating system shell" "$OUT"
        ck_who "H2 the session is in $ACC" "$ACC" "$OUT"
        ck_says "H3 after LOGTO, OS.EXECUTE refused in 10054's words" "$ACC2 is not permitted to use OS.EXECUTE" "$OUT"
        ck_absent "H3b RUN was in $ACC's VOC (the 14:38 miss)" "is not in your VOC" "$OUT"
        ck_absent "H4 and the program did not run" "ZZOS ran OS.EXECUTE" "$OUT"
    fi
fi

# ==========================================================================
# S.5 - THE 10 Sep PARITY AUDIT'S WITNESS LIST.  zzrel1, PROGRAMMER since
# section 10 (V0), must lack the admin verbs zzrel2 holds; UPDATE.ACCOUNTS refuses a stray word
# and ALL updates every account without asking (THIS TOUCHES REAL ACCOUNTS'
# VOCs, exactly as every install does); a new account's LISTF has descriptions;
# CREATE.ACCOUNT ... SH-ON reports 10102 (reached through ADOPT, since a
# password prompt cannot be piped); DELETE.ACCOUNT of a user carrying SD's
# stamp asks ONE question naming the user and home, then removes both.
# zzrel3's stamp is written by this script (useradd -c "SD account"), exactly
# what sd-elevate useradd writes - the delete branch keys on the stamp alone.
head2 "12. S.5 - the parity audit's witness list"
if [ "$COMMIT" -eq 1 ] && { [ "$ADOPTED" -ne 1 ] || [ "$MADE_ACCOUNT2" -ne 1 ]; }; then
    for r in "V1-3 PROGRAMMER lacks" "V4-6 ADMINISTRATOR has" "V7 listf" "V8 10173" "V9 10170" "V10 10171" "D1 10102" "D2 one question" "D3 home named" "D4 user gone" "D5 home gone" "D6 register gone"; do not_reached "$r"; done
else
    OUT=$(run_sd "$ACC" "PROGRAMMER: CT VOC sh, config, listu; LISTF" "CT VOC sh" "CT VOC config" "CT VOC listu" "LISTF")
    if [ "$COMMIT" -eq 1 ]; then
        for v in sh config listu; do ck_says "V1 PROGRAMMER lacks $v" "Record '$v' not found" "$OUT"; done
        ck_says "V7 a new account's LISTF shows descriptions" "File for BASIC programs" "$OUT"
    fi
    OUT=$(run_sd "$ACC2" "ADMINISTRATOR: CT VOC sh, config, listu" "CT VOC sh" "CT VOC config" "CT VOC listu")
    if [ "$COMMIT" -eq 1 ]; then
        for v in sh config listu; do ck_line "V4 ADMINISTRATOR has $v" "VOC $v" "$OUT"; done
    fi
    OUT=$(run_sd root "UPDATE.ACCOUNTS FOO, then UPDATE.ACCOUNTS ALL" "UPDATE.ACCOUNTS FOO" "UPDATE.ACCOUNTS ALL")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "V8 UPDATE.ACCOUNTS FOO refused (10173)" "does not take" "$OUT"
        ck_says "V9 ALL says what it will do (10170)" "Every registered account will have its VOC updated" "$OUT"
        ck_says "V10 and reports a count (10171)" "account(s) had their VOC updated" "$OUT"
        ck "V10b it finished (not a timeout)" no "$( [ "$SD_RC" = 124 ] && echo yes || echo no )"
    fi

    say "  useradd -m -c \"SD account\" $ACC3; ADOPT $ACC3 PROGRAMMER SH-ON"
    if [ "$COMMIT" -eq 1 ]; then
        useradd -m -c "SD account" "$ACC3" && MADE_USER3=1
        touch "$SDSYS/\$adopt.$ACC3"
    fi
    OUT=$(run_oneshot -internal create-account USER "$ACC3" PROGRAMMER SH-ON ADOPT no.query)
    if [ "$COMMIT" -eq 1 ]; then
        rm -f "$SDSYS/\$adopt.$ACC3"
        [ -e "$REGISTER/$ACC3" ] && MADE_ACCOUNT3=1
        ck_says "D1 CREATE.ACCOUNT ... SH-ON reported 10102" "Account $ACC3 has SH" "$OUT"
        say "  before delete: user=$(yesno_user "$ACC3") home=$(yesno_dir "/home/$ACC3") register=$(yesno_file "$REGISTER/$ACC3") gecos='$(getent passwd "$ACC3" | cut -d: -f5)'"
    fi
    OUT=$(run_sd root "DELETE.ACCOUNT $ACC3 REMOVE.HOME, answered Y" "DELETE.ACCOUNT $ACC3 REMOVE.HOME" "Y")
    if [ "$COMMIT" -eq 1 ]; then
        ck "D2 exactly ONE confirmation was asked" 1 "$(printf '%s' "$OUT" | grep -o '(y/<n>)?' | wc -l)"
        ck_says "D3 it named the Linux user and the home (10905)" "its Linux user $ACC3 and the home directory /home/$ACC3" "$OUT"
        ck_says "D3b and reported the home removed (10907)" "Home directory /home/$ACC3 removed" "$OUT"
        ck "D4 the Linux user is gone" no "$(yesno_user "$ACC3")"
        ck "D5 the home directory is gone" no "$(yesno_dir "/home/$ACC3")"
        ck "D6 the register record is gone" no "$(yesno_file "$REGISTER/$ACC3")"
        [ "$(yesno_user "$ACC3")" = no ] && MADE_USER3=0
        [ "$(yesno_file "$REGISTER/$ACC3")" = no ] && MADE_ACCOUNT3=0
    fi
fi

# ==========================================================================
# Q.17 - MODIFY.PASSWORD's ADMINISTRATOR ARM.  A root session sets zzrel1's
# password through sd-elevate passwd; passwd has no terminal, so it reads the
# new password twice from the session's own input (SD reads stdin a byte at a
# time, linuxio.c:447, so the lines are still there).  The password is random,
# NEVER PRINTED, and dies with the account.  The instrument is the shadow
# entry's hash prefix before and after, not SD's message alone.
head2 "13. Q.17 - MODIFY.PASSWORD under sudo sd sets another account's password"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "W1 10914" "W2 no 10915" "W3 shadow changed"; do not_reached "$r"; done
else
    PW="Zq7$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 16)x9"
    SH_BEFORE=$(getent shadow "$ACC" 2>/dev/null | cut -d: -f2)
    say "  shadow hash prefix before: '$(printf '%s' "$SH_BEFORE" | cut -c1-3)'"
    say "  --- sd session as root: MODIFY.PASSWORD $ACC, then the new password twice (not shown) ---"
    OUT=""
    if [ "$COMMIT" -eq 1 ]; then
        OUT=$(cd "$SDSYS" && printf '\nTERM 200,9999\nMODIFY.PASSWORD %s\n%s\n%s\nOFF\n' "$ACC" "$PW" "$PW" \
              | timeout 60 "$SD" 2>&1 | strip)
        printf '%s\n' "$OUT" | sed -e "s/$PW/********/g" -e 's/^/      | /'
        SH_AFTER=$(getent shadow "$ACC" 2>/dev/null | cut -d: -f2)
        say "  shadow hash prefix after : '$(printf '%s' "$SH_AFTER" | cut -c1-3)'"
        ck_says "W1 MODIFY.PASSWORD reported the change (10914)" "The password for $ACC was changed" "$OUT"
        ck_absent "W2 and not 10915" "was NOT changed" "$OUT"
        if [ -n "$SH_AFTER" ] && [ "$SH_AFTER" != "$SH_BEFORE" ] && [ "${SH_AFTER:0:1}" = '$' ]; then
            ck "W3 the shadow entry changed to a real hash" yes yes
        else
            ck "W3 the shadow entry changed to a real hash" yes no
        fi
    fi
    PW=""
fi

# ==========================================================================
# Q.12 - THE ssh DOOR TO A SUSPENDED ACCOUNT.  sshd_config's "Match Group
# sdusers,!sdadmin / ForceCommand sd" sends zzrel1 (PROGRAMMER, not sdadmin)
# straight into sd.  A throwaway key is installed for zzrel1 only.  CONTROL
# FIRST: before the suspend, ssh must land in sd and WHO name zzrel1 - without
# it a refusal after could be ssh failing for any reason.  The API door is not
# measured here (task table W.4).
head2 "14. Q.12 - ssh into a SUSPENDED account is refused (10107)"
ssh_ready() {
    command -v ssh >/dev/null && command -v ssh-keygen >/dev/null || return 1
    systemctl is-active --quiet ssh 2>/dev/null || systemctl is-active --quiet sshd 2>/dev/null
}
if [ "$COMMIT" -eq 1 ] && { [ "$ADOPTED" -ne 1 ] || ! ssh_ready; }; then
    say "  ssh, ssh-keygen or an active sshd is missing"
    for r in "X1 control landed in sd" "X2 suspended" "X3 10107" "X4 no WHO"; do not_reached "$r"; done
else
    SSH_OPTS=(-F /dev/null -o BatchMode=yes -o PasswordAuthentication=no -o IdentitiesOnly=yes
              -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o LogLevel=ERROR)
    ssh_sd() {   # $1 title; stdin body is fixed: blank, TERM, WHO, OFF
        say "  --- ssh $ACC@127.0.0.1 (ForceCommand sd): $1 ---" >&2
        [ "$COMMIT" -eq 1 ] || { say "      (dry run - not executed)" >&2; return 0; }
        local out
        out=$(printf '\nTERM 200,9999\nWHO\nOFF\n' | timeout 45 ssh "${SSH_OPTS[@]}" -i "$SSHDIR/key" "$ACC@127.0.0.1" 2>&1 | strip)
        printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
        printf '%s' "$out"
    }
    if [ "$COMMIT" -eq 1 ]; then
        SSHDIR=$(mktemp -d)
        ssh-keygen -q -t ed25519 -N '' -C witness-release-run -f "$SSHDIR/key"
        UHOME=$(getent passwd "$ACC" | cut -d: -f6)
        install -d -m 700 -o "$ACC" -g "$(id -gn "$ACC")" "$UHOME/.ssh"
        install -m 600 -o "$ACC" -g "$(id -gn "$ACC")" "$SSHDIR/key.pub" "$UHOME/.ssh/authorized_keys"
        say "  key installed in $UHOME/.ssh/authorized_keys (removed with the user)"
    fi
    OUT=$(ssh_sd "control, before the suspend")
    [ "$COMMIT" -eq 1 ] && ck_who "X1 control: ssh landed in sd and WHO names $ACC" "$ACC" "$OUT"
    OUT=$(run_sd root "MODIFY.ACCOUNT $ACC SUSPENDED" "MODIFY.ACCOUNT $ACC SUSPENDED")
    [ "$COMMIT" -eq 1 ] && ck_says "X2 MODIFY.ACCOUNT reported the suspend (10109)" "is now SUSPENDED" "$OUT"
    OUT=$(ssh_sd "after the suspend")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "X3 refused in 10107's words" "Account $ACC is suspended" "$OUT"
        if who_in "$ACC" "$OUT"; then ck "X4 and never reached a command (no WHO)" no yes; else ck "X4 and never reached a command (no WHO)" no no; fi
    fi
    OUT=$(run_sd root "restore: MODIFY.ACCOUNT $ACC PROGRAMMER" "MODIFY.ACCOUNT $ACC PROGRAMMER")
    [ "$COMMIT" -eq 1 ] && ck_says "X5 the suspension was lifted" "is now PROGRAMMER" "$OUT"
fi

# ==========================================================================
# S.5, the other half - DELETE.ACCOUNT of an account whose Linux user SD did not
# create (zzrel1, plain useradd, no stamp): one shorter question (10085), the
# account goes, the Linux user is KEPT and stripped of SD's groups (10036).
head2 "15. S.5 - DELETE.ACCOUNT of a borrowed user keeps the user (10085, 10036)"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "K1 one question" "K2 10085" "K3 10036" "K4 register gone" "K5 user kept" "K6 groups stripped"; do not_reached "$r"; done
else
    OUT=$(run_sd root "DELETE.ACCOUNT $ACC, answered Y" "DELETE.ACCOUNT $ACC" "Y")
    if [ "$COMMIT" -eq 1 ]; then
        ck "K1 exactly ONE confirmation was asked" 1 "$(printf '%s' "$OUT" | grep -o '(y/<n>)?' | wc -l)"
        ck_says "K2 the shorter question (10085)" "Delete account $ACC and its directory (y/<n>)?" "$OUT"
        ck_says "K3 the Linux user left in place (10036)" "Linux user $ACC was not created by SD" "$OUT"
        ck "K4 the register record is gone" no "$(yesno_file "$REGISTER/$ACC")"
        ck "K5 the Linux user is kept" yes "$(yesno_user "$ACC")"
        ck "K6 and holds no SD group" 0 "$(id -nG "$ACC" 2>/dev/null | tr ' ' '\n' | grep -cE '^(sdusers|sdadmin|sdu_)')"
        [ "$(yesno_file "$REGISTER/$ACC")" = no ] && MADE_ACCOUNT=0
    fi
fi

head2 "16. verdict"
if [ "$COMMIT" -eq 0 ]; then
    say "  DRY RUN - nothing was executed and nothing was checked."
    say "  Re-run with --commit, as root:"
    say "    sudo bash $SELF --commit"
    say "  A DRY RUN IS NOT A PASS.  Exit 2."
    exit 2
fi
say "  passed      : $PASS"
say "  failed      : $FAIL"
say "  not reached : $NOT_REACHED   (counted in failed)"
if [ "$((PASS + FAIL))" -eq 0 ]; then
    say "witness-release-run: FAILED - no check ran, so this proves nothing."
    exit 1
fi
if [ "$FAIL" -gt 0 ]; then
    say "witness-release-run: FAILED - $FAIL of $((PASS + FAIL)) checks failed."
    exit 1
fi
say "witness-release-run: PASSED - $PASS of $PASS checks passed."
exit 0
