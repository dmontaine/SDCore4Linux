#!/usr/bin/env bash
#
# witness-tierchange.sh - does MODIFY.ACCOUNT RE-DERIVE an account's VOC on a
#                         tier move, by ITSELF, with no UPDATE.ACCOUNTS?
#                         The last open item of §L1 (per-tier VOC).
#
#   bash      /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/witness-tierchange.sh
#   sudo bash /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/witness-tierchange.sh --commit
#
# ***NEEDS sudo, ONLY FOR --commit.***  The dry run changes nothing and needs no
# privilege: run it first, read what it intends, then commit.
#
# Exit 0 every check passed, 1 a check failed (or was not reached), 2 it could
# not run.
#
# ===========================================================================
# WHAT IT WITNESSES, AND WHY IT IS THE LAST §L1 ITEM
# ===========================================================================
# CREATE.ACCOUNT builds a tier's VOC at creation, and LOGIN's update.voc rebuilds
# it on an upgrade.  The THIRD path is MODIFY.ACCOUNT: when an account's tier
# MOVES, MODIFYA's voc.delta must re-derive the VOC to match - add the verbs the
# higher tier gets, remove the ones a lower tier loses - reading the lists from
# sdsys/tier.policy (omit.standard, add.administrator) and voc_template.
#
# ***THE ATTRIBUTION IS THE WHOLE POINT, AND IT IS ONE RULE: NO UPDATE.ACCOUNTS.***
# PROJECT_STATUS's earlier note could not attribute the re-derivation because
# UPDATE.ACCOUNTS ALL had run for every account between creation and the
# measurement - so an account holding its tier's layer proved only that SOMETHING
# built it, not that MODIFY.ACCOUNT did.  This script never runs UPDATE.ACCOUNTS.
# Every VOC change it measures happened inside a single MODIFY.ACCOUNT, so the
# change is MODIFY.ACCOUNT's or it did not happen.
#
# ===========================================================================
# HOW IT MAKES A THROWAWAY ACCOUNT WITHOUT A PASSWORD PROMPT
# ===========================================================================
# CREATE.ACCOUNT USER <name> <tier> prompts for the Linux user's password on the
# TTY (passwd(1) via sd-elevate), which a pipe cannot feed.  So this uses the
# same path witness-accounts.sh proved: useradd the Linux user, then the
# installer's one-shot ADOPT (a marker + `sd -internal create-account USER <name>
# ADOPT no.query`), which attaches an SD account to the existing user with NO
# password prompt and defaults the tier to ADMINISTRATOR.  From there the tier is
# MOVED, which is what this witnesses.  The account is deleted and the Linux user
# removed at the end.
#
# ===========================================================================
# WHAT IT MEASURES, AND WHY RELATIONSHIPS NOT LITERALS
# ===========================================================================
# The account VOC is a HASHED file (the records are inside %0/%1, not one file
# each), so it is read through a session: LOGTO <name>, COUNT VOC, and CT VOC of
# specific verbs.  From the SDSYS session `sudo sd` lands in, LOGTO reaches the
# account and MODIFY.ACCOUNT runs.
#
# The per-tier counts DRIFT (they were 368/410/~420 on 10 Sep and have moved
# since - MODIFY.PASSWORD added, the tier lists left newvoc), so this asserts
# RELATIONSHIPS, not the numbers: STANDARD < PROGRAMMER < ADMINISTRATOR, and the
# round trip returns to the start.  The verbs it checks are exact, though:
#   omit-list verbs (STANDARD is denied, PROGRAMMER/ADMINISTRATOR get):
#       basic  catalog  ed  run
#   admin-layer verbs (only ADMINISTRATOR gets):
#       create.account  grant  modify.account
# So a STANDARD account must LACK all seven; PROGRAMMER must HAVE the four omit
# verbs and LACK the three admin ones; ADMINISTRATOR must HAVE all seven.  And
# MODIFYA's own 10109 ("Account %1 is now %2") and 10113 ("VOC: %1 records added,
# %2 removed, %3 left alone") are anchored on the move itself.
#
# THE PIPED-SESSION RULES ARE THE PROJECT'S: a blank first line, TERM 200,9999,
# every session ends in OFF, the one-shot ADOPT takes </dev/null and a timeout.
#
set -u

SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"

SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
# 14 Sep 26 - the register dir and its record keys are LOWER CASE since §M
# (accounts/don, not ACCOUNTS/DON): account names were lower-cased with
# everything else.  So the record for account <name> is accounts/<name>.
REGISTER="$SDSYS/accounts"
ACCOUNTS_ROOT=/home/sd/user_accounts

ACC=zztier1
COMMIT=0
LOG=""

PASS=0
FAIL=0
NOT_REACHED=0
MADE_USER=0
MADE_ACCOUNT=0

# The verbs whose presence tells the tier apart.
OMIT_VERBS="basic catalog ed run"          # STANDARD lacks; PROG/ADMIN have
ADMIN_VERBS="create.account grant modify.account"   # only ADMINISTRATOR has

# Set by measure(): the account's COUNT VOC and the list of the checked verbs
# that are PRESENT, for the tier just measured.
M_COUNT=0
M_PRESENT=""
COUNT_ADMIN=0
COUNT_STD=0
COUNT_PROG=0

usage() { sed -n '2,20p' "$0"; exit 2; }

for arg in "$@"; do
    case "$arg" in
        --commit) COMMIT=1 ;;
        --log=*)  LOG="${arg#--log=}" ;;
        --name=*) ACC="${arg#--name=}" ;;
        -h|--help) usage ;;
        *) echo "witness-tierchange: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done

ACC=$(printf '%s' "$ACC" | tr '[:upper:]' '[:lower:]')
MARKER="$SDSYS/\$adopt.$ACC"

[ -n "$LOG" ] || LOG="/tmp/witness-tierchange.$(date +%Y%m%d-%H%M%S).log"
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

ck_gt() {   # name, a, b : pass if integer a > b
    local name="$1" a="$2" b="$3"
    if [ "$a" -gt "$b" ] 2>/dev/null; then
        PASS=$((PASS + 1)); say "  [PASS] $name: $a > $b"
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: expected $a > $b"
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

not_reached() {
    FAIL=$((FAIL + 1)); NOT_REACHED=$((NOT_REACHED + 1))
    say "  [NOT REACHED] $1 - a precondition failed above, so it measured nothing"
}

yesno_user()  { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group() { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_dir()   { [ -d "$1" ] && echo yes || echo no; }
yesno_file()  { [ -e "$1" ] && echo yes || echo no; }

# One piped SDSYS session.  Narration to fd 2; only sd's own output on fd 1.
run_sd() {
    local title="$1"; shift
    say "  --- sd session (SDSYS): $title ---" >&2
    local line
    for line in "$@"; do say "      > $line" >&2; done
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; return 0; fi
    local body out
    body=$'\n''TERM 200,9999'
    for line in "$@"; do body="$body"$'\n'"$line"; done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | timeout 90 "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g')
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

run_oneshot() {   # the installer's ADOPT form
    say "  --- sd one-shot, cwd $SDSYS, </dev/null, timeout 25 s ---" >&2
    say "      > $SD $*" >&2
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; return 0; fi
    local out
    out=$(cd "$SDSYS" && set -o pipefail && \
          timeout 25 "$SD" "$@" </dev/null 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g')
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

# Measure the account's VOC AT ITS CURRENT TIER: COUNT VOC and which of the
# checked verbs are present.  Sets M_COUNT and M_PRESENT.  Reads through LOGTO
# from the SDSYS session; a real record read on the positive path, "not found"
# on the negative, so presence is never guessed.
measure() {
    local label="$1"
    M_COUNT=0; M_PRESENT=""
    local cmds=("LOGTO $ACC" "COUNT VOC")
    local v
    for v in $OMIT_VERBS $ADMIN_VERBS; do cmds+=("CT VOC $v"); done
    local out
    out=$(run_sd "measure $ACC ($label)" "${cmds[@]}")
    [ "$COMMIT" -eq 1 ] || return 0
    M_COUNT=$(printf '%s' "$out" | grep -oE '[0-9]+ record\(s\) counted' | head -1 | grep -oE '^[0-9]+')
    [ -n "$M_COUNT" ] || M_COUNT=0
    # A verb is PRESENT when CT VOC printed its record (a line "VOC <verb>"),
    # ABSENT when it printed "Record '<verb>' not found".  Anchored on the
    # positive wording, and the negative refused if it appears for a present one.
    for v in $OMIT_VERBS $ADMIN_VERBS; do
        if printf '%s' "$out" | grep -qE "^VOC $v$" && \
           ! printf '%s' "$out" | grep -qF "Record '$v' not found"; then
            M_PRESENT="$M_PRESENT $v"
        fi
    done
    M_PRESENT="${M_PRESENT# }"
    say "      $label: COUNT VOC $M_COUNT; present of the 7 checked: [$M_PRESENT]"
}

has() { case " $M_PRESENT " in *" $1 "*) echo yes ;; *) echo no ;; esac; }

# Assert the checked-verb pattern for a tier.  want_omit/want_admin are yes/no.
check_verbs() {
    local tier="$1" want_omit="$2" want_admin="$3" v
    for v in $OMIT_VERBS;  do ck "$tier has omit-verb $v"   "$want_omit"  "$(has "$v")"; done
    for v in $ADMIN_VERBS; do ck "$tier has admin-verb $v"  "$want_admin" "$(has "$v")"; done
}

# Move the tier, anchoring on MODIFYA's own 10109 + 10113.  Returns the output.
move_tier() {
    local tier="$1"
    run_sd "MODIFY.ACCOUNT $ACC $tier" "MODIFY.ACCOUNT $ACC $tier"
}

cleanup() {
    local rc=$?
    [ "$COMMIT" -eq 1 ] || exit $rc
    head2 "CLEANUP - removing whatever this run made"
    [ -e "$MARKER" ] && { rm -f "$MARKER"; say "  removed a leftover ADOPT marker"; }
    if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$REGISTER/$ACC" ]; then
        say "  deleting the SD account through SD"
        printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC"$'\n''Y'$'\n''OFF'$'\n' \
            | timeout 90 "$SD" >/dev/null 2>&1
    fi
    if [ "$MADE_USER" -eq 1 ] && id -u "$ACC" >/dev/null 2>&1; then
        userdel -r "$ACC" >/dev/null 2>&1 && say "  userdel -r $ACC: done" \
            || say "  userdel -r $ACC: FAILED - remove it by hand"
    fi
    say "  left behind: register=$(yesno_file "$REGISTER/$ACC")" \
        "dir=$(yesno_dir "$ACCOUNTS_ROOT/$ACC") user=$(yesno_user "$ACC")" \
        "group=$(yesno_group "sdu_$ACC") marker=$(yesno_file "$MARKER")"
    exit $rc
}
trap cleanup EXIT

# ==========================================================================
say "witness-tierchange: $( [ "$COMMIT" -eq 1 ] && echo 'COMMIT - it will change this system' || echo 'DRY RUN - it changes nothing' )"
say "  date       : $(date -Is)"
say "  uid        : $(id -u) ($(id -un))"
say "  sd         : $SD"
say "  account    : $ACC  (adopted ADMINISTRATOR, then moved)"
say "  marker     : $MARKER"
say "  log        : $LOG"
say "  NEVER RUNS UPDATE.ACCOUNTS - that is the whole of the attribution."

head2 "0. preconditions and the ground being clear"
for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT"; do
    [ -e "$p" ] || { say "witness-tierchange: CANNOT RUN - $p does not exist."; exit 2; }
done
if [ "$COMMIT" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
    say "witness-tierchange: CANNOT RUN - --commit needs root."
    say "  re-run as: sudo bash $SELF --commit"
    exit 2
fi
DIRTY=0
[ "$(yesno_user "$ACC")" = yes ]  && { say "  DIRTY: Linux user $ACC exists"; DIRTY=1; }
[ "$(yesno_group "sdu_$ACC")" = yes ] && { say "  DIRTY: group sdu_$ACC exists"; DIRTY=1; }
[ "$(yesno_dir "$ACCOUNTS_ROOT/$ACC")" = yes ] && { say "  DIRTY: $ACCOUNTS_ROOT/$ACC exists"; DIRTY=1; }
[ "$(yesno_file "$REGISTER/$ACC")" = yes ] && { say "  DIRTY: register record $ACC exists"; DIRTY=1; }
[ "$(yesno_file "$MARKER")" = yes ] && { say "  DIRTY: an ADOPT marker for $ACC exists"; DIRTY=1; }
if [ "$DIRTY" -eq 1 ]; then
    say "witness-tierchange: CANNOT RUN - the ground is not clear (above)."
    say "  This script will not touch state it did not create."
    exit 2
fi
say "  ground clear: $ACC exists as no user, group, directory, record or marker."

head2 "0b. the state before"
say "  register records : $(ls -1 "$REGISTER" 2>/dev/null | tr '\n' ' ')"

# ==========================================================================
head2 "1. adopt $ACC as an ADMINISTRATOR (no password prompt), and measure it"
say "  useradd -m $ACC"
if [ "$COMMIT" -eq 1 ]; then
    if useradd -m "$ACC"; then MADE_USER=1; say "  created Linux user $ACC (uid $(id -u "$ACC"))"
    else say "witness-tierchange: CANNOT RUN - useradd failed; nothing else attempted."; exit 2; fi
fi
say "  touch $MARKER  (the installer's one-shot ADOPT gate)"
[ "$COMMIT" -eq 1 ] && touch "$MARKER"
OUT=$(run_oneshot -internal create-account USER "$ACC" ADOPT no.query)
[ "$COMMIT" -eq 1 ] && rm -f "$MARKER"

ADOPTED=0
if [ "$COMMIT" -eq 1 ]; then
    ck "A1 the register record exists (the gate for the rest)" yes "$(yesno_file "$REGISTER/$ACC")"
    if [ -e "$REGISTER/$ACC" ]; then
        ADOPTED=1; MADE_ACCOUNT=1
        ck "A2 ADOPT defaulted the tier to ADMINISTRATOR" ADMINISTRATOR "$(sed -n '5p' "$REGISTER/$ACC")"
    else
        not_reached "A2 tier ADMINISTRATOR"
    fi
fi

if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -eq 1 ]; then
    measure "ADMINISTRATOR (as adopted)"
    COUNT_ADMIN=$M_COUNT
    check_verbs "ADMINISTRATOR" yes yes
    ck "A3 COUNT VOC is non-zero (the measurement reached the VOC)" yes \
       "$( [ "$COUNT_ADMIN" -gt 0 ] 2>/dev/null && echo yes || echo no )"
fi

# ==========================================================================
head2 "2. MOVE DOWN to STANDARD - MODIFYA must strip the layer, no UPDATE.ACCOUNTS"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "M1 now STANDARD" "M2 10113 re-derivation" "S count < admin" \
             "S lacks omit verbs" "S lacks admin verbs"; do not_reached "$r"; done
else
    OUT=$(move_tier STANDARD)
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M1 MODIFYA reported the move (10109 'is now STANDARD')" "is now STANDARD" "$OUT"
        # ***10113 IS THE RE-DERIVATION, REPORTED BY MODIFYA ITSELF.***  Going
        # down from ADMINISTRATOR removes records; "0 removed" would mean it did
        # nothing while claiming a move.
        ck_says "M2 MODIFYA re-derived the VOC (10113 'VOC: ... records ...')" "VOC:" "$OUT"
        ck_says "M3 and it removed records on the way down" "removed" "$OUT"
        measure "STANDARD (after MODIFY.ACCOUNT down)"
        COUNT_STD=$M_COUNT
        ck_gt "S1 STANDARD count is LESS than ADMINISTRATOR" "$COUNT_ADMIN" "$COUNT_STD"
        check_verbs "STANDARD" no no
    fi
fi

# ==========================================================================
head2 "3. MOVE UP to PROGRAMMER - the omit verbs return, the admin ones do not"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "P1 now PROGRAMMER" "P3 count > std" "P PROGRAMMER verbs"; do not_reached "$r"; done
else
    OUT=$(move_tier PROGRAMMER)
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "P1 MODIFYA reported the move (10109 'is now PROGRAMMER')" "is now PROGRAMMER" "$OUT"
        ck_says "P2 and it added records on the way up" "added" "$OUT"
        measure "PROGRAMMER (after MODIFY.ACCOUNT up)"
        COUNT_PROG=$M_COUNT
        ck_gt "P3 PROGRAMMER count is MORE than STANDARD" "$COUNT_PROG" "$COUNT_STD"
        ck_gt "P4 and still LESS than ADMINISTRATOR" "$COUNT_ADMIN" "$COUNT_PROG"
        check_verbs "PROGRAMMER" yes no
    fi
fi

# ==========================================================================
head2 "4. MOVE UP to ADMINISTRATOR - the round trip returns the whole layer"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "R1 now ADMINISTRATOR" "R2 round trip count"; do not_reached "$r"; done
else
    OUT=$(move_tier ADMINISTRATOR)
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "R1 MODIFYA reported the move (10109 'is now ADMINISTRATOR')" "is now ADMINISTRATOR" "$OUT"
        measure "ADMINISTRATOR (after the round trip)"
        check_verbs "ADMINISTRATOR" yes yes
        # ***THE ROUND TRIP.***  Back at the start tier, the count is the start
        # count again - re-derivation is reversible and complete, not lossy.
        ck "R2 the round trip returned COUNT VOC to the ADMINISTRATOR value" \
           "$COUNT_ADMIN" "$M_COUNT"
    fi
fi

# ==========================================================================
head2 "5. verdict"
if [ "$COMMIT" -eq 0 ]; then
    say "  DRY RUN - nothing was executed and nothing was checked."
    say "  Re-run with --commit, as root:"
    say "    sudo bash $SELF --commit"
    say ""
    say "  A DRY RUN IS NOT A PASS.  Exit 2."
    exit 2
fi
say "  passed      : $PASS"
say "  failed      : $FAIL"
say "  not reached : $NOT_REACHED   (counted in failed)"
say "  UPDATE.ACCOUNTS was NEVER run, so every VOC change above is"
say "  MODIFY.ACCOUNT's own re-derivation."
if [ "$((PASS + FAIL))" -eq 0 ]; then
    say "witness-tierchange: FAILED - no check ran, so this proves nothing."
    exit 1
fi
if [ "$FAIL" -gt 0 ]; then
    say "witness-tierchange: FAILED - $FAIL of $((PASS + FAIL)) checks failed."
    exit 1
fi
say "witness-tierchange: PASSED - $PASS of $PASS checks passed."
say "  MODIFY.ACCOUNT re-derives the per-tier VOC in both directions, alone."
exit 0
