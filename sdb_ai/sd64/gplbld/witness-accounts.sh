#!/usr/bin/env bash
#
# witness-accounts.sh - the PRIVILEGED half of the account family: ADOPT a
#                       throwaway Linux user the way the installer does, then
#                       DELETE.ACCOUNT it, and measure what survives.
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
# WHAT IT MEASURES NOW
# ===========================================================================
#   1   NO.QUERY without a Linux user is refused (10039).  RE-WITNESS: the
#       11 Sep witness-adopt.sh already covered it; this is the same path on
#       the current install.
#   2a  A pre-existing Linux user WITHOUT ADOPT is refused (10038) and nothing
#       is made.  Re-witness too - and it is the CONTROL for 2b: the same user,
#       refused without the marker and accepted with it.
#   2b  ADOPT, with the installer's own invocation (installsdai.sh:903-906):
#       marker, "sd -internal create-account USER <name> ADOPT no.query",
#       marker removed.  Re-witness of 11 Sep, and here it is chiefly the
#       PRECONDITION for phase 3.  One row is new: A8, that ADOPT leaves the
#       Linux user's GECOS UNSTAMPED - the property that stops DELETE.ACCOUNT
#       from ever deleting a login SD did not create (the adopted admin's own -
#       "don" here is the transitory human; SDSYS is the constant user).
#   3   DELETE.ACCOUNT on that adopted account.  ***NEVER WITNESSED BY
#       ANYTHING***: the borrowed-user branch - the SHORTER confirmation
#       (10085), the data warning (10158), "not created by SD" (10036), and
#       the Linux user and its home surviving.
#   3k  ***PRE_RELEASE 28 (SEV A), NOW FIXED IN SOURCE - THESE MUST PASS.***
#       The survivor was in sdusers and - as an ADMINISTRATOR - in sdadmin, and
#       sdadmin grants passwordless sd-elevate (sdcore.sudoers).  sd-elevate
#       passwd retargets any SD user who is also a Linux sudoer - the admin who
#       "becomes SDSYS" to run administrative commands - so a leftover member
#       reaches root; the ssh force-command exemption comes with it.  DELACC's
#       10036 branch now removes the survivor from sdadmin then sdusers, the
#       shape MODIFYA:616 / GRANTA:307 use.  D12/D13 assert the survivor holds
#       NEITHER: ***A PASS IS THE FIX; A FAIL MEANS PRE_RELEASE 28 IS NOT ON
#       THE INSTALL UNDER TEST.***  On Linux this is safe and unambiguous:
#       sdusers and sdadmin are SD's own groups, so every membership was SD's
#       to remove and none predates SD.  (The port cannot reason that way: its
#       admin group is BUILTIN\Administrators.)
#
# NOT HERE: the SD-CREATED Linux user.  CREATE.ACCOUNT USER <new> without
# NO.QUERY prompts for a password, which an unattended run cannot answer
# without a password in a script.  Phase 5 prints the hand recipe.
#
# THE PIPED-SESSION RULES ARE THE PROJECT'S:
#   * a blank first line absorbs anything emitted before the first prompt;
#   * TERM 200,9999 stops pagination;
#   * every session ends in OFF;
#   * a verb that prompts EATS THE NEXT LINE - and a prompt that never appears
#     leaves its answer for the ":" prompt (the 17:57 run);
#   * the one-shot ADOPT call takes </dev/null and a 25 s timeout.  The first
#     ADOPT witness FROZE on that call with the terminal attached to stdin, and
#     the cause was never found; this is the immunisation that let it pass.
#   * OBSERVED 17:57: with a terminal attached, sd writes its command echo
#     straight to the TTY, so ":TERM 200,9999" appears unprefixed on screen and
#     is NOT in the captured text.  Nothing below anchors on echo text.
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
MARKER="$SDSYS/\$adopt.$ACC"

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

# Drive one piped sd session.  ALL NARRATION GOES TO fd 2 and only sd's own
# output comes back on fd 1, so `OUT=$(run_sd ...)` never captures this
# function's echo of the commands into the text the checks search.
run_sd() {
    local title="$1"; shift
    say "  --- sd session: $title ---" >&2
    local line
    for line in "$@"; do say "      > $line" >&2; done
    if [ "$COMMIT" -eq 0 ]; then
        say "      (dry run - not executed)" >&2
        return 0
    fi
    local body out
    body=$'\n''TERM 200,9999'
    for line in "$@"; do body="$body"$'\n'"$line"; done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | timeout 60 "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g')
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

# The installer's one-shot form, from the system directory, with the freeze
# immunisation the first ADOPT witness needed.
run_oneshot() {
    say "  --- sd one-shot, cwd $SDSYS, stdin </dev/null, timeout 25 s ---" >&2
    say "      > $SD $*" >&2
    if [ "$COMMIT" -eq 0 ]; then
        say "      (dry run - not executed)" >&2
        return 0
    fi
    local out rc
    # pipefail INSIDE the substitution: PIPESTATUS read after `out=$(a | b)`
    # describes the assignment, whose status is sed's, so it would report
    # "exit 0" for a timeout.  With pipefail the substitution returns sd's own
    # status (or timeout's 124), and $? carries it out.
    out=$(cd "$SDSYS" && set -o pipefail && \
          timeout 25 "$SD" "$@" </dev/null 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g')
    rc=$?
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    say "      (exit $rc)" >&2
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
        say "  marker $MARKER WAS STILL PRESENT - removed (ADOPT did not consume it)"
    fi
    # Only a REGISTERED account is deleted through SD, so the Y cannot leak.
    if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$REGISTER/$ACC_UC" ]; then
        say "  $ACC_UC is still registered; deleting it through SD"
        printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC"$'\n''Y'$'\n''OFF'$'\n' \
            | timeout 60 "$SD" >/dev/null 2>&1
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
            "group=$(yesno_group "sdu_$n") marker=$(yesno_file "$SDSYS/\$adopt.$n")"
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
say "  adopted    : $ACC   (marker $MARKER)"
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
    [ "$(yesno_file "$SDSYS/\$adopt.$n")" = yes ] && { say "  DIRTY: an ADOPT marker for $n already exists"; DIRTY=1; }
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
say "  sdadmin members  : $(getent group sdadmin | cut -d: -f4)"

# ==========================================================================
head2 "1. NO.QUERY without an existing Linux user is refused (10039) - re-witness"

# 14 Sep 26 dm - NONE: since S.16 a non-administrator USER account must say API
# or NONE (10082), and that is checked first; without it this row would meet
# 10082 and never reach the 10039 it witnesses.
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC_REFUSE NONE NO.QUERY" \
             "CREATE.ACCOUNT USER $ACC_REFUSE NONE NO.QUERY")
if [ "$COMMIT" -eq 1 ]; then
    ck_says "1a refused with 10039's wording" "setting its password needs a prompt" "$OUT"
    ck "1b no Linux user was made"      no "$(yesno_user "$ACC_REFUSE")"
    ck "1c no group was made"           no "$(yesno_group "sdu_$ACC_REFUSE")"
    ck "1d no directory was made"       no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC_REFUSE")"
    ck "1e no register record was made" no "$(yesno_file "$REGISTER/$ACC_REFUSE_UC")"
fi

# ==========================================================================
head2 "2. a borrowed Linux user: refused without ADOPT, adopted with it"
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
say "  2a. THE CONTROL: the same user WITHOUT the marker must be refused (10038)."
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC NONE NO.QUERY (no marker)" \
             "CREATE.ACCOUNT USER $ACC NONE NO.QUERY")
if [ "$COMMIT" -eq 1 ]; then
    ck_says "2a1 refused with 10038's wording" "SD accounts create their own Linux user" "$OUT"
    ck "2a2 no register record was made" no "$(yesno_file "$REGISTER/$ACC_UC")"
    ck "2a3 no directory was made"       no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC")"
    ck "2a4 no sdu_ group was made"      no "$(yesno_group "sdu_$ACC")"
fi

say ""
say "  2b. ADOPT, exactly as installsdai.sh:903-906 does it."
say "  touch $MARKER"
[ "$COMMIT" -eq 1 ] && touch "$MARKER"
OUT=$(run_oneshot -internal create-account USER "$ACC" ADOPT no.query)
say "  rm -f $MARKER   (the installer removes it whatever happens; so does this)"
MARKER_AFTER_VERB=no
if [ "$COMMIT" -eq 1 ]; then
    MARKER_AFTER_VERB=$(yesno_file "$MARKER")
    rm -f "$MARKER"
fi

ADOPTED=0
if [ "$COMMIT" -eq 1 ]; then
    # ***A1 IS THE GATE FOR EVERYTHING IN PHASE 3.***
    ck "A1 the register record exists (the gate for phase 3)" yes "$(yesno_file "$REGISTER/$ACC_UC")"
    if [ -e "$REGISTER/$ACC_UC" ]; then
        ADOPTED=1; MADE_ACCOUNT=1
        say "  register record, field by field (KEYS.H:264-301):"
        awk '{printf "      %d: %s\n", NR, $0}' "$REGISTER/$ACC_UC"
        ck "A2 ACC\$TIER (field 5) is ADMINISTRATOR - ADOPT's default" \
           ADMINISTRATOR "$(sed -n '5p' "$REGISTER/$ACC_UC")"
        ck "A3 field 4 (retired ACC\$USERS) was not written" "" "$(sed -n '4p' "$REGISTER/$ACC_UC")"
    else
        not_reached "A2 tier ADMINISTRATOR"
        not_reached "A3 field 4 not written"
    fi
    if [ -d "$ACCOUNTS_ROOT/$ACC" ]; then
        ck "A4 directory is $ACC:sdu_$ACC, mode 2775" "$ACC sdu_$ACC 2775" \
           "$(stat -c '%U %G %a' "$ACCOUNTS_ROOT/$ACC")"
    else
        ck "A4 the account directory exists" yes no
    fi
    ck "A5 the sdu_ group exists" yes "$(yesno_group "sdu_$ACC")"
    # Two instruments: what SD said, and what /etc/group says.
    ck_says "A6 SD reported the sdusers membership (10013)" "added to sdusers" "$OUT"
    ck "A6b and $ACC is in sdusers" yes "$(in_group "$ACC" sdusers)"
    ck_says "A7 SD reported the administrator grant (10032)" "is now an SD administrator" "$OUT"
    ck "A7b and $ACC is in sdadmin" yes "$(in_group "$ACC" sdadmin)"
    # ***THE MARKER IS CONSUMED BY THE VERB, NOT BY THE rm AFTER IT.***  Read
    # between the two, which is the only moment the difference is visible.
    ck "A8 the verb CONSUMED the marker (absent before this script's rm)" no "$MARKER_AFTER_VERB"
    # ***A9: ADOPT DOES NOT STAMP.***  If it wrote "SD account" into GECOS,
    # DELETE.ACCOUNT would delete an adopted person's Linux login - for the
    # installer's account, the owner's own.
    ck "A9 ADOPT left the GECOS unstamped" no \
       "$( [ "$(getent passwd "$ACC" | cut -d: -f5)" = "SD account" ] && echo yes || echo no )"
fi

# ==========================================================================
head2 "3. DELETE.ACCOUNT on the adopted account - the branch nothing has reached"

if [ "$COMMIT" -eq 1 ] && [ "$ADOPTED" -ne 1 ]; then
    say "  PHASE 3 IS GATED ON A1 AND A1 FAILED: there is no registered account to"
    say "  delete, so running it would score passes on an account that never existed"
    say "  and send its Y to the ':' prompt - the 17:57 run did both."
    for r in "D1 10085" "D2 not 10084" "D3 10158" "D4 10036" "D5 not 10028" \
             "D6 Y consumed" "D7 register gone" "D8 dir gone" "D9 sdu_ gone" \
             "D10 user survives" "D11 home survives" "D12 not in sdadmin" \
             "D13 not in sdusers"; do
        not_reached "$r"
    done
else
    # The BEFORE of every "gone" and "survives" row, so none of them can pass
    # on something that was never there.
    if [ "$COMMIT" -eq 1 ]; then
        say "  before: register=$(yesno_file "$REGISTER/$ACC_UC") dir=$(yesno_dir "$ACCOUNTS_ROOT/$ACC")" \
            "group=$(yesno_group "sdu_$ACC") user=$(yesno_user "$ACC") home=$(yesno_dir "/home/$ACC")" \
            "sdusers=$(in_group "$ACC" sdusers) sdadmin=$(in_group "$ACC" sdadmin)"
    fi
    OUT=$(run_sd "DELETE.ACCOUNT $ACC (answering Y)" "DELETE.ACCOUNT $ACC" "Y")
    if [ "$COMMIT" -eq 1 ]; then
        # 10085 is the SHORTER confirmation; 10084 also promises the Linux user,
        # a promise the verb cannot keep for a user SD did not create.
        ck_says   "D1 the confirmation used the SHORTER wording (10085)" "and its directory (y/<n>)?" "$OUT"
        ck_silent "D2 it did NOT offer to delete the Linux user (10084)"  "its Linux user"            "$OUT"
        ck_says   "D3 the data warning preceded it (10158)" "removes everything the account holds" "$OUT"
        ck_says   "D4 it said the Linux user is not SD's (10036)" "was not created by SD" "$OUT"
        ck_silent "D5 it did NOT claim to delete the Linux user (10028)" "OS User:" "$OUT"
        ck_silent "D6 the Y was consumed by the confirmation, not the ':' prompt" "Y is not in your VOC" "$OUT"
        ck "D7 the register record is gone"   no "$(yesno_file "$REGISTER/$ACC_UC")"
        ck "D8 the account directory is gone" no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC")"
        ck "D9 the sdu_ group is gone"        no "$(yesno_group "sdu_$ACC")"
        # ***D10 IS WHAT THE BRANCH EXISTS FOR*** - the others would all pass
        # if DELETE.ACCOUNT had taken the person's Linux login with it.
        ck "D10 the BORROWED Linux user is still there" yes "$(yesno_user "$ACC")"
        ck "D11 and its home directory survived"        yes "$(yesno_dir "/home/$ACC")"
        [ -e "$REGISTER/$ACC_UC" ] || MADE_ACCOUNT=0

        say ""
        say "  3k. PRE_RELEASE 28: a true deletion strips the SD groups too."
        say "  sdadmin grants passwordless sd-elevate (sdcore.sudoers), and"
        say "  sd-elevate passwd retargets any SD user who is also a Linux"
        say "  sudoer - the admin who 'becomes SDSYS' - so a leftover member"
        say "  reaches root.  DELACC's 10036 branch now removes the survivor"
        say "  from sdadmin then sdusers (MODIFYA:616 / GRANTA:307 shape); both"
        say "  are SD's own groups, so every membership was SD's to remove."
        say "  ***THESE MUST PASS ON A FIXED INSTALL. A FAIL MEANS PRE_RELEASE"
        say "  28 IS NOT INSTALLED ON THE TREE UNDER TEST (reinstall, re-run).***"
        say "  after : sdusers=$(in_group "$ACC" sdusers) sdadmin=$(in_group "$ACC" sdadmin)" \
            "groups='$(id -nG "$ACC" 2>/dev/null)'"
        ck "D12 the survivor no longer holds sdadmin" no "$(in_group "$ACC" sdadmin)"
        ck "D13 the survivor no longer holds sdusers" no "$(in_group "$ACC" sdusers)"
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

head2 "5. still owed: the SD-CREATED Linux user, by hand"
say "  As SDSYS (a human admin becomes SDSYS to run this):"
say "  sudo $SD"
say "  CREATE.ACCOUNT USER zzacct3 PROGRAMMER NONE (type a throwaway password)"
say "  DELETE.ACCOUNT zzacct3                      (answer y)"
say "  Expect the LONGER confirmation (10084, naming the Linux user), and"
say "  10028 \"OS User: zzacct3 Deleted\" where phase 3 got 10036."

if [ "$FAIL" -eq 0 ]; then
    say "witness-accounts: PASSED - $PASS of $PASS checks passed."
    exit 0
fi
# ***IF THE ONLY FAILURES ARE D12/D13, THE INSTALL PREDATES THE PRE_RELEASE 28
# FIX*** - the finding is real and present, and the fix is in source at DELACC's
# 10036 branch.  Reinstall (SDSYS recompiles GPL.BP) and re-run; they must pass.
d_fail=0
for r in D12 D13; do
    grep -qE "^\s*\[FAIL\] $r " "$LOG" && d_fail=$((d_fail + 1))
done
if [ "$FAIL" -eq "$d_fail" ] && [ "$d_fail" -gt 0 ]; then
    say "witness-accounts: FAILED - PRE_RELEASE 28 is NOT installed on the tree under"
    say "  test: the deleted account's Linux user still holds SD's groups (D12/D13)."
    say "  Everything else passed ($PASS).  The fix is in source (DELACC 10036 branch);"
    say "  reinstall so SDSYS recompiles it, then re-run - D12/D13 must then pass."
    exit 1
fi
say "witness-accounts: FAILED - $FAIL of $((PASS + FAIL)) checks failed" \
    "($NOT_REACHED not reached)."
exit 1
