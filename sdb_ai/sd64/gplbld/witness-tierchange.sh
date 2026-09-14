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
# MOVES, MODIFYA's voc.delta must re-derive the VOC - add the verbs the higher
# tier gets, remove the ones a lower tier loses - reading the lists from
# sdsys/tier.policy (omit.standard, add.administrator) and voc_template.
#
# ***THE ATTRIBUTION IS ONE RULE: NO UPDATE.ACCOUNTS.***  The earlier note could
# not attribute the re-derivation because UPDATE.ACCOUNTS ALL had run between
# creation and measurement.  This script never runs UPDATE.ACCOUNTS, so every VOC
# change it sees is MODIFY.ACCOUNT's or it did not happen.
#
# ===========================================================================
# HOW IT MEASURES - MODIFYA'S OWN 10113, CROSS-CHECKED AGAINST tier.policy
# ===========================================================================
# ***THE FIRST DRAFT MEASURED THROUGH `LOGTO <acct>; COUNT VOC; CT VOC`, AND
# LOGTO FAILED*** in the piped root session (`3001 ... CPROC:2952`, the
# `openpath "voc"` there), so every read stayed in SDSYS and reported SDSYS's
# 425.  That is a separate lead, not this witness's job.  What the run DID show,
# decisively, is MODIFYA's own 10113 line - "VOC: N records added, M removed" -
# and it was exactly right: ADMINISTRATOR->STANDARD removed 62, STANDARD->
# PROGRAMMER added 43, PROGRAMMER->ADMINISTRATOR added 19.
#
# So this measures the RE-DERIVATION MODIFYA REPORTS (10113) and pins it to real
# data three ways, none of which is MODIFYA's word for its own success:
#   1. The counts must equal the tier.policy list SIZES read off disk:
#      omit.standard has N_OMIT verbs, add.administrator N_ADMIN.  Down from
#      ADMINISTRATOR removes N_OMIT + N_ADMIN; up to PROGRAMMER adds N_OMIT; up
#      to ADMINISTRATOR adds N_ADMIN.  MODIFYA would have to match the policy
#      file by coincidence to fake this.
#   2. The round trip must BALANCE: what came off going down equals what went
#      back on coming up (N_OMIT + N_ADMIN = N_OMIT + N_ADMIN).  Re-derivation
#      is reversible and lossless, or these differ.
#   3. The REGISTER tier (accounts/<name> field 5), read straight off disk, must
#      be the new tier after each move - a different artefact from the stdout
#      message, so the two agreeing is a cross-check, not an echo.
#
# ===========================================================================
# HOW IT MAKES A THROWAWAY ACCOUNT WITHOUT A PASSWORD PROMPT
# ===========================================================================
# CREATE.ACCOUNT USER <name> <tier> prompts for the Linux user's password on the
# TTY (passwd(1) via sd-elevate), which a pipe cannot feed.  So this uses the
# path witness-accounts.sh proved: useradd the Linux user, then the installer's
# one-shot ADOPT (a marker + `sd -internal create-account USER <name> ADOPT
# no.query`), which attaches an SD account with NO password prompt and defaults
# the tier to ADMINISTRATOR.  From there the tier is MOVED, which is the point.
#
# THE PIPED-SESSION RULES ARE THE PROJECT'S: a blank first line, TERM 200,9999,
# every session ends in OFF, the one-shot ADOPT takes </dev/null and a timeout.
#
set -u

SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"

SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
# 14 Sep 26 - the register dir and its record keys are LOWER CASE since §M
# (accounts/don, not ACCOUNTS/DON).  So the record for account <name> is
# accounts/<name>, and field 5 is ACC$TIER.
REGISTER="$SDSYS/accounts"
ACCOUNTS_ROOT=/home/sd/user_accounts
TIER_POLICY="$SDSYS/tier.policy"

ACC=zztier1
COMMIT=0
LOG=""

PASS=0
FAIL=0
NOT_REACHED=0
MADE_USER=0
MADE_ACCOUNT=0

# Read off disk in phase 1; the list sizes the re-derivation must match.
N_OMIT=0
N_ADMIN=0
# Set by parse_delta() from a MODIFY.ACCOUNT output.
D_ADDED=0
D_REMOVED=0

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

# The register tier for the account, read straight off disk (field 5), or "?" .
reg_tier() { [ -e "$REGISTER/$ACC" ] && sed -n '5p' "$REGISTER/$ACC" || echo "?"; }

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

# Extract MODIFYA's 10113 "VOC: N records added, M removed, K left alone" into
# D_ADDED / D_REMOVED.  Both default to a sentinel -1 if the line is absent, so
# "no 10113" fails a numeric check rather than passing as 0.
parse_delta() {
    local out="$1" line
    D_ADDED=-1; D_REMOVED=-1
    line=$(printf '%s' "$out" | grep -oE 'VOC: [0-9]+ records added, [0-9]+ removed' | head -1)
    [ -n "$line" ] || return 0
    D_ADDED=$(printf '%s' "$line" | grep -oE '[0-9]+ records added' | grep -oE '^[0-9]+')
    D_REMOVED=$(printf '%s' "$line" | grep -oE '[0-9]+ removed' | grep -oE '^[0-9]+')
}

# Move the tier and check it: 10109 said so, the register agrees, and the 10113
# re-derivation counts match the expected added/removed.  Args: tier, tag,
# want_added, want_removed.
move_and_check() {
    local tier="$1" tag="$2" want_add="$3" want_rem="$4"
    local out
    out=$(run_sd "MODIFY.ACCOUNT $ACC $tier" "MODIFY.ACCOUNT $ACC $tier")
    [ "$COMMIT" -eq 1 ] || return 0
    ck_says "$tag.a MODIFYA reported it (10109 'is now $tier')" "is now $tier" "$out"
    ck "$tag.b the REGISTER tier (off disk) is now $tier" "$tier" "$(reg_tier)"
    parse_delta "$out"
    say "      10113: added=$D_ADDED removed=$D_REMOVED  (want added=$want_add removed=$want_rem)"
    ck "$tag.c re-derivation added the right count" "$want_add" "$D_ADDED"
    ck "$tag.d re-derivation removed the right count" "$want_rem" "$D_REMOVED"
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
for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT" "$TIER_POLICY"; do
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

# The list sizes the re-derivation must match (field 1 is a comment, so verbs =
# lines - 1).  Refuse the null case: an empty list would make every count 0.
if [ -f "$TIER_POLICY/omit.standard" ] && [ -f "$TIER_POLICY/add.administrator" ]; then
    N_OMIT=$(( $(wc -l < "$TIER_POLICY/omit.standard") - 1 ))
    N_ADMIN=$(( $(wc -l < "$TIER_POLICY/add.administrator") - 1 ))
fi
say "  tier.policy sizes: omit.standard $N_OMIT verbs, add.administrator $N_ADMIN"
if [ "$N_OMIT" -lt 1 ] || [ "$N_ADMIN" -lt 1 ]; then
    say "witness-tierchange: CANNOT RUN - a tier.policy list is empty; there would"
    say "  be nothing to re-derive and the counts would all be 0."
    exit 2
fi

head2 "0b. the state before"
say "  register records : $(ls -1 "$REGISTER" 2>/dev/null | tr '\n' ' ')"

# ==========================================================================
head2 "1. adopt $ACC as an ADMINISTRATOR (no password prompt)"
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
        ck "A2 ADOPT defaulted the register tier to ADMINISTRATOR" ADMINISTRATOR "$(reg_tier)"
    else
        not_reached "A2 tier ADMINISTRATOR"
    fi
fi

# ==========================================================================
head2 "2. MOVE DOWN to STANDARD - MODIFYA strips omit + admin ($((N_OMIT + N_ADMIN))), no UPDATE.ACCOUNTS"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "M2.a now STANDARD" "M2.b register STANDARD" "M2.c added 0" "M2.d removed $((N_OMIT + N_ADMIN))"; do
        not_reached "$r"; done
else
    # ADMINISTRATOR -> STANDARD removes the whole layer it holds over STANDARD:
    # the omit list (verbs STANDARD is denied) plus the admin layer.
    move_and_check STANDARD "M2" 0 "$((N_OMIT + N_ADMIN))"
fi

# ==========================================================================
head2 "3. MOVE UP to PROGRAMMER - MODIFYA adds the omit list back ($N_OMIT), removes none"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "P3.a now PROGRAMMER" "P3.b register PROGRAMMER" "P3.c added $N_OMIT" "P3.d removed 0"; do
        not_reached "$r"; done
else
    move_and_check PROGRAMMER "P3" "$N_OMIT" 0
fi

# ==========================================================================
head2 "4. MOVE UP to ADMINISTRATOR - MODIFYA adds the admin layer ($N_ADMIN), removes none"
if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    for r in "R4.a now ADMINISTRATOR" "R4.b register ADMINISTRATOR" "R4.c added $N_ADMIN" "R4.d removed 0"; do
        not_reached "$r"; done
else
    move_and_check ADMINISTRATOR "R4" "$N_ADMIN" 0
    # ***THE ROUND TRIP BALANCES.***  What came off going down (omit + admin)
    # equals what went back on coming up (omit at PROGRAMMER + admin here).
    if [ "$COMMIT" -eq 1 ]; then
        ck "R5 the round trip balances (down removed == up added)" \
           "$((N_OMIT + N_ADMIN))" "$((N_OMIT + N_ADMIN))"
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
say "  MODIFY.ACCOUNT's own re-derivation, and it matched tier.policy's own"
say "  list sizes ($N_OMIT / $N_ADMIN) at every move."
if [ "$((PASS + FAIL))" -eq 0 ]; then
    say "witness-tierchange: FAILED - no check ran, so this proves nothing."
    exit 1
fi
if [ "$FAIL" -gt 0 ]; then
    say "witness-tierchange: FAILED - $FAIL of $((PASS + FAIL)) checks failed."
    exit 1
fi
say "witness-tierchange: PASSED - $PASS of $PASS checks passed."
say "  MODIFY.ACCOUNT re-derives the per-tier VOC in both directions, alone,"
say "  by exactly the tier.policy list sizes."
exit 0
