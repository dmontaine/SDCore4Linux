#!/usr/bin/env bash
#
# witness-accounts.sh - the PRIVILEGED half of the account family: create a
#                       throwaway SD account (Linux user and all, as
#                       CREATE.ACCOUNT does it), then DELETE.ACCOUNT it, and
#                       measure both branches against the teardown model.
#                       PORT_ADOPTION queue 22, ranked item 6; the intent is
#                       the port's verify-createaccount.ps1 and
#                       verify-delaccount.ps1.
#
#   bash      /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-accounts.sh
#   sudo bash /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-accounts.sh --commit
#
# ***IT NEEDS sudo, AND ONLY FOR --commit.***  The dry run changes nothing and
# needs no privilege: run it first, read what it intends, then commit.
#
# Exit 0 every check passed, 1 a check failed (or was not reached), 2 it could
# not run.
#
# ===========================================================================
# WHAT THE FIRST VERSION GOT WRONG, 12 Sep 2026 17:57 - KEPT, BECAUSE THE
# REASON IS THE LESSON
# ===========================================================================
# The first --commit run scored "13 passed, 7 failed", and BOTH NUMBERS WERE
# WRONG ABOUT WHAT THEY MEANT.
#
#   * THE 7 FAILURES WERE ONE BAD PREMISE, AND IT WAS THIS SCRIPT'S.  Phase 2
#     created a Linux user with useradd and then ran
#     "CREATE.ACCOUNT USER zzacct2 NO.QUERY", expecting an account.  SD
#     refused it with 10038 - "SD accounts create their own Linux user" - and
#     SD was RIGHT: since 11 Sep (CREATEA:21-27) a pre-existing Linux user is
#     refused rather than silently taken over, and ADOPT is the one sanctioned
#     exception.  The premise came from a 10 Sep recipe in PROJECT_STATUS that
#     predates that change.  ***THE CHANGE WAS DOCUMENTED IN THE FILE BEING
#     SCRIPTED AGAINST, AND IN PROJECT_STATUS'S OWN QUEUE 15 WITNESS, AND
#     NEITHER WAS READ FIRST.***
#   * ***8 OF THE 13 PASSES WERE THE NULL CASE.***  Nothing was created, so
#     "the register record is gone", "the directory is gone", "the Linux user
#     survives" and "it did not offer to delete the Linux user" were all true
#     of an account that never existed.  Only phase 1's five rows measured
#     anything.  THE FIX IS NEVER THE ONE-LINE CAUSE: the premise was the
#     cause, but what would have caught it is GATING - a phase whose
#     precondition was not established must not run, and its rows must count
#     as NOT REACHED, which is a failure.  Every phase below is gated.
#   * AND THE UNGATED PHASE LEAKED ITS ANSWER.  DELETE.ACCOUNT refused an
#     unregistered name without asking anything, so the "Y" meant for its
#     confirmation reached the ":" prompt as a command - "Y is not in your
#     VOC".  Harmless because Y is not a verb; the shape is not harmless.
#     Phase 3 now runs only against a registered account, and row D6 checks
#     that the Y was consumed by the confirmation.
#
# ===========================================================================
# WHAT IT MEASURES NOW (18 Sep 26, AFTER THE TEARDOWN)
# ===========================================================================
#   1   NO.QUERY without a Linux user is refused (10039): SD accounts create
#       their own Linux user, and creating one means setting its password.
#   2a  A pre-existing Linux user WITHOUT ADOPT is refused (10038) and nothing
#       is made.  ADOPT is now install-only (the teardown, S.26: a root
#       session is refused outright, and -internal is root-only), so the
#       borrowed-user route cannot exist on a delivered machine - 2a is the
#       control that says so, and this script no longer drives an ADOPT.
#   2b  CREATE.ACCOUNT USER <name>, SD's whole flow: it creates the Linux
#       user itself and asks for that user's password (answered from a pipe,
#       thrown away, never printed).  Checked: a plain account - three
#       register fields, no tier, no suspension, in sdusers only.
#   3   DELETE.ACCOUNT on the account SD created: the SD-created branch -
#       the LONGER confirmation (10084, naming the Linux user), the data
#       warning (10158), and 10028 "OS User: <name> Deleted".  The Linux
#       user and its home go with it.
#
# THE SESSIONS RUN AS SDSYS, THE ONE ADMINISTRATOR (S.26): a local session
# running as the sdsys OS user is the only thing CPROC grants, and the only
# thing CREATE.ACCOUNT and DELETE.ACCOUNT accept.
#
# NOT HERE, BY RULING: the borrowed-user branch.  It was the ADOPT flow, and
# the teardown closed it - witness-absence.sh says the closing.
#
# THE PIPED-SESSION RULES ARE THE PROJECT'S:
#   * a blank first line absorbs anything emitted before the first prompt;
#   * TERM 200,9999 stops pagination;
#   * every session ends in OFF;
#   * a verb that prompts EATS THE NEXT LINE - and a prompt that never appears
#     leaves its answer for the ":" prompt (the 12 Sep 17:57 run);
#   * password answers are never echoed into the log: run_sd prints
#     "(password answer)" in their place.
#   * OBSERVED 12 Sep 17:57: with a terminal attached, sd writes its command
#     echo straight to the TTY, so ":TERM 200,9999" appears unprefixed on
#     screen and is NOT in the captured text.  Nothing below anchors on echo
#     text.
#
set -u

# The script names itself by absolute path, every variable expanded - the
# re-run command it prints lands in somebody else's shell.
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"

SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
REGISTER="$SDSYS/accounts"           # 13 Sep 26: lower case on disk (plan M3 D1)
ACCOUNTS_ROOT=/home/sd/user_accounts

ACC=zzacct2                 # adopted in phase 2, deleted in phase 3
ACC_REFUSE=zzacct1          # phase 1 only; nothing is ever created for it

COMMIT=0
LOG=""

PASS=0
FAIL=0
NOT_REACHED=0
MADE_USER=0
MADE_ACCOUNT=0

usage() {
    sed -n '2,20p' "$0"
    exit 2
}

for arg in "$@"; do
    case "$arg" in
        --commit) COMMIT=1 ;;
        --log=*)  LOG="${arg#--log=}" ;;
        # --name exists for a collision, and so the ground-clear guard can be
        # SEEN working: --name=don on a dry run must refuse.
        --name=*) ACC="${arg#--name=}" ;;
        -h|--help) usage ;;
        *) echo "witness-accounts: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done

ACC=$(printf '%s' "$ACC" | tr '[:upper:]' '[:lower:]')
# The REGISTER KEY for each name.  _UC once meant upper case; since 13 Sep 2026
# account names are stored lower case, so the key is the name as it already is.
ACC_UC=$(printf '%s' "$ACC" | tr '[:upper:]' '[:lower:]')
ACC_REFUSE_UC=$(printf '%s' "$ACC_REFUSE" | tr '[:upper:]' '[:lower:]')
# CREATEA:208 - the marker names the account it authorises, DOWNCASED.
MARKER="$SDSYS/\$attach.$ACC"

if [ -z "$LOG" ]; then
    LOG="/tmp/witness-accounts.$(date +%Y%m%d-%H%M%S).log"
fi
exec > >(tee -a "$LOG") 2>&1

say()   { printf '%s\n' "$*"; }
head2() { say ""; say "=== $* ============================================"; }

# Every check prints what it compared, not only what it concluded.
ck() {
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        PASS=$((PASS + 1)); say "  [PASS] $name: expected '$want', got '$got'"
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: expected '$want', got '$got'"
    fi
}

# Anchored on a string that appears ONLY on the path being claimed.
ck_says() {
    local name="$1" needle="$2" text="$3"
    if printf '%s' "$text" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1)); say "  [PASS] $name: found \"$needle\""
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: did NOT find \"$needle\""
    fi
}

ck_silent() {
    local name="$1" needle="$2" text="$3"
    if printf '%s' "$text" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: found \"$needle\" and must not have"
    else
        PASS=$((PASS + 1)); say "  [PASS] $name: \"$needle\" absent, as required"
    fi
}

# ***A ROW WHOSE PRECONDITION FAILED IS NOT A PASS.***  The 17:57 run is why.
not_reached() {
    FAIL=$((FAIL + 1)); NOT_REACHED=$((NOT_REACHED + 1))
    say "  [NOT REACHED] $1 - its precondition failed above, so it measured nothing"
}

yesno_user()   { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group()  { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_dir()    { [ -d "$1" ] && echo yes || echo no; }
yesno_file()   { [ -e "$1" ] && echo yes || echo no; }
in_group()     { id -nG "$1" 2>/dev/null | tr ' ' '\n' | grep -qx "$2" && echo yes || echo no; }

# Drive one piped sd session, running AS SDSYS - the administrator (S.26).
# ALL NARRATION GOES TO fd 2 and only sd's own output comes back on fd 1, so
# `OUT=$(run_sd ...)` never captures this function's echo of the commands into
# the text the checks search.  A line that is a password answer is printed as
# "(password answer)" rather than echoed.
run_sd() {
    local title="$1"; shift
    say "  --- sd session as sdsys: $title ---" >&2
    local line
    for line in "$@"; do
        case "$line" in
            _PW_) say "      > (password answer)" >&2 ;;
            *)    say "      > $line" >&2 ;;
        esac
    done
    if [ "$COMMIT" -eq 0 ]; then
        say "      (dry run - not executed)" >&2
        return 0
    fi
    local body out
    body=$'\n''TERM 200,9999'
    for line in "$@"; do
        if [ "$line" = "_PW_" ]; then
            body="$body"$'\n'"$PW_OS"
        else
            body="$body"$'\n'"$line"
        fi
    done
    body="$body"$'\n''OFF'$'\n'
    # 18 Sep 26 dm, NIGHT - S.26 corrected: only a real sdsys LOGIN administers,
    # so the session runs through the root-only loginuid bridge (the witness
    # runs as root under --commit); a bare "sudo -u sdsys sd" is refused (10181).
    out=$(printf '%s' "$body" | timeout 90 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g')
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

cleanup() {
    local rc=$?
    [ "$COMMIT" -eq 1 ] || exit $rc
    head2 "CLEANUP - removing whatever this run made"
    # ***THE MARKER GOES WHATEVER HAPPENED.***  A marker left behind is an
    # open ADOPT door for that name - the state CREATEA:173-186 exists to
    # prevent.  Removed unconditionally, and its presence is reported.
    if [ -e "$MARKER" ]; then
        rm -f "$MARKER"
        say "  marker $MARKER WAS STILL PRESENT - removed (ATTACH did not consume it)"
    fi
    # Only a REGISTERED account is deleted through SD, so the Y cannot leak.
    if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$REGISTER/$ACC_UC" ]; then
        say "  $ACC_UC is still registered; deleting it through SD (as sdsys)"
        printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC"$'\n''y'$'\n''OFF'$'\n' \
            | timeout 90 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" >/dev/null 2>&1
    fi
    if [ "$MADE_USER" -eq 1 ] && id -u "$ACC" >/dev/null 2>&1; then
        userdel -r "$ACC" >/dev/null 2>&1 \
            && say "  userdel -r $ACC: done" \
            || say "  userdel -r $ACC: FAILED - remove it by hand"
    fi
    for n in "$ACC" "$ACC_REFUSE"; do
        local uc
        uc=$(printf '%s' "$n" | tr '[:upper:]' '[:lower:]')   # register key, lower since 13 Sep
        say "  left behind for $n: register=$(yesno_file "$REGISTER/$uc")" \
            "dir=$(yesno_dir "$ACCOUNTS_ROOT/$n") user=$(yesno_user "$n")" \
            "group=$(yesno_group "sdu_$n") marker=$(yesno_file "$SDSYS/\$attach.$n")"
    done
    exit $rc
}
trap cleanup EXIT

# ==========================================================================
say "witness-accounts: $( [ "$COMMIT" -eq 1 ] && echo 'COMMIT - it will change this system' || echo 'DRY RUN - it changes nothing' )"
say "  date       : $(date -Is)"
say "  uid        : $(id -u) ($(id -un))"
say "  sd         : $SD"
say "  register   : $REGISTER"
say "  accounts   : $ACCOUNTS_ROOT"
say "  account    : $ACC   (a leftover ATTACH marker for it would refuse: $MARKER)"
say "  refused    : $ACC_REFUSE"
say "  log        : $LOG"

head2 "0. preconditions and the ground being clear"

for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT"; do
    if [ ! -e "$p" ]; then
        say "witness-accounts: CANNOT RUN - $p does not exist."
        exit 2
    fi
done

if [ "$COMMIT" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
    say "witness-accounts: CANNOT RUN - --commit needs root."
    say "  re-run as: sudo bash $SELF --commit"
    exit 2
fi

# Refuse if anything of either name already exists - including a MARKER, which
# would mean this run's ADOPT row could pass on an earlier run's door.
DIRTY=0
for n in "$ACC" "$ACC_REFUSE"; do
    uc=$(printf '%s' "$n" | tr '[:upper:]' '[:lower:]')   # register key, lower since 13 Sep
    [ "$(yesno_user "$n")" = yes ] && { say "  DIRTY: Linux user $n already exists"; DIRTY=1; }
    [ "$(yesno_group "sdu_$n")" = yes ] && { say "  DIRTY: group sdu_$n already exists"; DIRTY=1; }
    [ "$(yesno_dir "$ACCOUNTS_ROOT/$n")" = yes ] && { say "  DIRTY: $ACCOUNTS_ROOT/$n already exists"; DIRTY=1; }
    [ "$(yesno_file "$REGISTER/$uc")" = yes ] && { say "  DIRTY: register record $uc already exists"; DIRTY=1; }
    [ "$(yesno_file "$SDSYS/\$attach.$n")" = yes ] && { say "  DIRTY: an ATTACH marker for $n already exists"; DIRTY=1; }
done
if [ "$DIRTY" -eq 1 ]; then
    say "witness-accounts: CANNOT RUN - the ground is not clear (above)."
    say "  This script will not touch state it did not create."
    exit 2
fi
say "  ground clear: neither name exists as user, group, directory, record or marker."

head2 "0b. the state before"
say "  register records : $(ls -1 "$REGISTER" | tr '\n' ' ')"
say "  account dirs     : $(ls -1 "$ACCOUNTS_ROOT" | tr '\n' ' ')"
say "  sdusers members  : $(getent group sdusers | cut -d: -f4)"

# ==========================================================================
head2 "1. NO.QUERY without an existing Linux user is refused (10039) - re-witness"

# 18 Sep 26 dm - THE API KEYWORD IS GONE (S.28), so the pre-teardown "NONE"
# that this row used to carry would now itself be the refusal - the row asks
# NO.QUERY alone and meets 10039, the answer it witnesses.
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC_REFUSE NO.QUERY" \
             "CREATE.ACCOUNT USER $ACC_REFUSE NO.QUERY")
if [ "$COMMIT" -eq 1 ]; then
    ck_says "1a refused with 10039's wording" "setting its password needs a prompt" "$OUT"
    ck "1b no Linux user was made"      no "$(yesno_user "$ACC_REFUSE")"
    ck "1c no group was made"           no "$(yesno_group "sdu_$ACC_REFUSE")"
    ck "1d no directory was made"       no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC_REFUSE")"
    ck "1e no register record was made" no "$(yesno_file "$REGISTER/$ACC_REFUSE_UC")"
fi

# ==========================================================================
head2 "2. a borrowed Linux user is refused, and that is now the whole story"
say "  useradd -m $ACC     (this script's own doing, not SD's)"
USER_OK=0
if [ "$COMMIT" -eq 1 ]; then
    if useradd -m "$ACC"; then
        MADE_USER=1; USER_OK=1
        say "  created Linux user $ACC (uid $(id -u "$ACC")), GECOS '$(getent passwd "$ACC" | cut -d: -f5)'"
    else
        say "witness-accounts: CANNOT RUN - useradd failed; nothing else was attempted."
        exit 2
    fi
fi

say ""
say "  2a. THE CONTROL: a pre-existing Linux user is refused (10038)."
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC NO.QUERY" \
             "CREATE.ACCOUNT USER $ACC NO.QUERY")
if [ "$COMMIT" -eq 1 ]; then
    ck_says "2a1 refused with 10038's wording" "SD accounts create their own Linux user" "$OUT"
    ck "2a2 no register record was made" no "$(yesno_file "$REGISTER/$ACC_UC")"
    ck "2a3 no directory was made"       no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC")"
    ck "2a4 no sdu_ group was made"      no "$(yesno_group "sdu_$ACC")"
fi

say ""
say "  2b. THE TEARDOWN'S DOOR (S.26): there is no ATTACH on a delivered machine."
say "  ATTACH needs -internal, -internal needs root (check_admin), and a root"
say "  session is refused outright by CPROC.  The borrowed-user route is closed;"
say "  witness-absence.sh says the same about the machinery."
say "  This script removes the borrowed user again and makes the account SD's"
say "  own way instead."
if [ "$COMMIT" -eq 1 ]; then
    if userdel -r "$ACC"; then
        MADE_USER=0
        say "  userdel -r $ACC: the borrowed user is gone; SD will create its own"
    else
        say "witness-accounts: CANNOT RUN - userdel failed; the ground is no longer clear."
        exit 2
    fi
fi

say ""
say "  2c. CREATE.ACCOUNT USER $ACC - SD's whole flow, as sdsys."
# A throwaway Linux password, generated per run and printed nowhere: CREATEA
# asks for one because it is creating the Linux user, and the account dies in
# phase 3.  passwd(1) gets it through the piped session's stdin (the _PW_
# placeholders below), exactly as MODIFY.PASSWORD answers travel.
PW_OS="zz$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-14)"
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC (answering the Linux password)" \
             "CREATE.ACCOUNT USER $ACC" "_PW_" "_PW_")
PW_OS=""
CREATED=0
if [ "$COMMIT" -eq 1 ]; then
    # ***A1 IS THE GATE FOR EVERYTHING IN PHASE 3.***
    ck "A1 the register record exists (the gate for phase 3)" yes "$(yesno_file "$REGISTER/$ACC_UC")"
    if [ -e "$REGISTER/$ACC_UC" ]; then
        CREATED=1; MADE_ACCOUNT=1
        say "  register record, field by field:"
        awk '{printf "      %d: %s\n", NR, $0}' "$REGISTER/$ACC_UC"
        # 18 Sep 26 (W.7/S.25): field 5 is the suspension flag, blank for a
        # new account; field 6 is the retired prior-tier slot, never written.
        ck "A2 field 5 (ACC\$SUSPENDED) is blank - no tier" "" "$(sed -n '5p' "$REGISTER/$ACC_UC")"
        ck "A3 field 4 (retired ACC\$USERS) was not written" "" "$(sed -n '4p' "$REGISTER/$ACC_UC")"
        ck "A3b field 6 (retired ACC\$PRIOR.TIER) was not written" "" "$(sed -n '6p' "$REGISTER/$ACC_UC")"
    else
        not_reached "A2 field 5 blank"
        not_reached "A3 field 4 not written"
        not_reached "A3b field 6 not written"
    fi
    if [ -d "$ACCOUNTS_ROOT/$ACC" ]; then
        ck "A4 directory is $ACC:sdu_$ACC, mode 2775" "$ACC sdu_$ACC 2775" \
           "$(stat -c '%U %G %a' "$ACCOUNTS_ROOT/$ACC")"
    else
        ck "A4 the account directory exists" yes no
    fi
    ck "A5 the sdu_ group exists" yes "$(yesno_group "sdu_$ACC")"
    ck "A5b SD created the Linux user" yes "$(yesno_user "$ACC")"
    # Two instruments: what SD said, and what /etc/group says.
    ck_says "A6 SD reported the sdusers membership (10013)" "added to sdusers" "$OUT"
    ck "A6b and $ACC is in sdusers" yes "$(in_group "$ACC" sdusers)"
    # 18 Sep 26 (S.26/S.28): no administrator grant, no API route.
    ck_silent "A7 SD claimed no administrator grant (10032 gone)" "is now an SD administrator" "$OUT"
    ck "A7b the sdadmin group does not exist" no "$(yesno_group sdadmin)"
    ck "A7c the sdapi group does not exist"    no "$(yesno_group sdapi)"
fi

# ==========================================================================
head2 "3. DELETE.ACCOUNT on the account SD created - the branch this run can now reach"

if [ "$COMMIT" -eq 1 ] && [ "$CREATED" -ne 1 ]; then
    say "  PHASE 3 IS GATED ON A1 AND A1 FAILED: there is no registered account to"
    say "  delete, so running it would score passes on an account that never existed"
    say "  and send its y to the ':' prompt."
    for r in "D1 10084" "D2 not 10085" "D3 10158" "D4 10028" "D5 not 10036" \
             "D6 y consumed" "D7 register gone" "D8 dir gone" "D9 sdu_ gone" \
             "D10 user gone" "D11 home gone"; do
        not_reached "$r"
    done
else
    # The BEFORE of every "gone" row, so none of them can pass on something
    # that was never there.
    if [ "$COMMIT" -eq 1 ]; then
        say "  before: register=$(yesno_file "$REGISTER/$ACC_UC") dir=$(yesno_dir "$ACCOUNTS_ROOT/$ACC")" \
            "group=$(yesno_group "sdu_$ACC") user=$(yesno_user "$ACC") home=$(yesno_dir "/home/$ACC")" \
            "sdusers=$(in_group "$ACC" sdusers)"
    fi
    OUT=$(run_sd "DELETE.ACCOUNT $ACC (answering y)" "DELETE.ACCOUNT $ACC" "y")
    if [ "$COMMIT" -eq 1 ]; then
        # 10084 is the LONGER confirmation: the verb may delete the Linux user
        # because SD created it, and it says so.
        ck_says   "D1 the confirmation named the Linux user (10084)" "its Linux user" "$OUT"
        ck_silent "D2 it did NOT use the SHORTER wording (10085)" "and its directory (y/<n>)?" "$OUT"
        ck_says   "D3 the data warning preceded it (10158)" "removes everything the account holds" "$OUT"
        ck_says   "D4 it claimed the Linux user's deletion (10028)" "OS User:" "$OUT"
        ck_silent "D5 it did NOT say the user was not SD's (10036)" "was not created by SD" "$OUT"
        ck_silent "D6 the y was consumed by the confirmation, not the ':' prompt" "y is not in your VOC" "$OUT"
        ck "D7 the register record is gone"   no "$(yesno_file "$REGISTER/$ACC_UC")"
        ck "D8 the account directory is gone" no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC")"
        ck "D9 the sdu_ group is gone"        no "$(yesno_group "sdu_$ACC")"
        # ***THE SD-CREATED BRANCH'S POINT***: the Linux user SD made is SD's
        # to take away.  THE HOME IS NOT: it goes only with REMOVE.HOME
        # (delacc's own description, the owner's 10 Sep 2026 ruling - on Linux
        # the home holds the person's own files and ssh keys).  The first real
        # run's D11 asked for the home to be gone while running the PLAIN
        # delete, which was the row's error, not the product's; the row now
        # asserts the designed outcome and names the other path.
        ck "D10 the SD-created Linux user is gone" no "$(yesno_user "$ACC")"
        ck "D11 and its home SURVIVES a plain delete (REMOVE.HOME is the other path)" \
           yes "$(yesno_dir "/home/$ACC")"
        [ -e "$REGISTER/$ACC_UC" ] || MADE_ACCOUNT=0
    fi
fi

# ==========================================================================
head2 "4. verdict"
if [ "$COMMIT" -eq 0 ]; then
    say "  DRY RUN - nothing was executed and nothing was checked."
    say "  Re-run with --commit, as root, to make these measurements:"
    say "    sudo bash $SELF --commit"
    say ""
    say "  A DRY RUN IS NOT A PASS.  Exit 2."
    exit 2
fi

say "  passed      : $PASS"
say "  failed      : $FAIL"
say "  not reached : $NOT_REACHED   (counted in failed - a row that measured nothing)"

if [ "$((PASS + FAIL))" -eq 0 ]; then
    say "witness-accounts: FAILED - no check ran, so this proves nothing."
    exit 1
fi

if [ "$FAIL" -eq 0 ]; then
    say "witness-accounts: PASSED - $PASS of $PASS checks passed."
    exit 0
fi
say "witness-accounts: FAILED - $FAIL of $((PASS + FAIL)) checks failed" \
    "($NOT_REACHED not reached)."
exit 1
