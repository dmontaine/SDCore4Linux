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
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-accounts.sh
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-accounts.sh --commit
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
#   1b  (8 Oct 26) A password SD refuses, answered n at the retry, unwinds the
#       Linux user it just made: 10086, user and home gone, nothing registered.
#       Needs the build with S.62's create_account change on the install.
#   2a  A pre-existing Linux user WITHOUT ADOPT is refused (10038) and nothing
#       is made.  ADOPT is now install-only (the teardown, S.26: a root
#       session is refused outright, and -internal is root-only), so the
#       borrowed-user route cannot exist on a delivered machine - 2a is the
#       control that says so, and this script no longer drives an ADOPT.
#   2b  CREATE.ACCOUNT USER <name>, SD's whole flow: it creates the Linux
#       user itself and asks for that user's password (answered from a pipe,
#       thrown away, never printed).  Checked: a plain account - three
#       register fields, no tier, no suspension, in sdusers only.
#   2d  (18 Oct 26, S.66) The shared-account words on the account 2b made:
#       MODIFY.ACCOUNT shared-read-off / -on and shared-write-on / -off, each
#       with its report (11515) and its register field (13 and 14), "already"
#       (10080) on a repeat, the BLANK-MEANS-ON rule (a blank field 13 is read
#       ON, so shared-read-on says "already" and shared-read-off WRITES the no),
#       the other fields untouched, and the audit lines in lower case.
#   2e  (18 Oct 26, S.66) The shared account on a REAL install: the register
#       record, the directory's owner, group and mode (sdsys:sdusers 2775, files
#       664), sdg_shared holding root and sdsys only, DELETE.ACCOUNT shared
#       refused (11517), CREATE.ACCOUNT GROUP shared and USER shared refused
#       (11516) with no Linux user made, and LOGTO shared refused for an
#       ordinary user (the audit line says reason=not granted).
#   ***2d AND 2e WERE WRITTEN, NOT RUN: they need sudo and an install that has
#   the S.66 build, and the agent that wrote them could run neither.***
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
GROUND_CLEAR=0

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
    # runs as root under --commit); a bare "sudo -u sdsys sd" is refused (10195).
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
        # 19 Sep 26 - THE HOME IS THIS RUN'S TO TAKE (the ground check refuses a
        #   home that was there before), once its user is gone: DELETE.ACCOUNT
        #   keeps it by design, so every run used to leave one.  witness-absence's
        #   rule: only when the USER is gone, whose home it otherwise still is.
        #   And only after the ground was found clear: this trap also runs when
        #   the ground check refuses, and that home is then someone else's.
        if [ "$GROUND_CLEAR" -eq 1 ] && ! id "$n" >/dev/null 2>&1 && [ -d "/home/$n" ]; then
            rm -rf -- "/home/$n" && say "  removed /home/$n (DELETE.ACCOUNT keeps a home; this run made it)"
        fi
        say "  left behind for $n: register=$(yesno_file "$REGISTER/$uc")" \
            "dir=$(yesno_dir "$ACCOUNTS_ROOT/$n") user=$(yesno_user "$n")" \
            "group=$(yesno_group "sdu_$n") home=$(yesno_dir "/home/$n") marker=$(yesno_file "$SDSYS/\$attach.$n")"
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
    # 19 Sep 26 - AND THE HOME.  The fifth cycle's run left /home/zzacct2 (a
    #   plain DELETE.ACCOUNT keeps the home by design) and this check did not
    #   look, so the sixth cycle's useradd adopted a home another uid owned and
    #   its userdel -r then refused - the run died in section 2.
    [ "$(yesno_dir "/home/$n")" = yes ] && { say "  DIRTY: /home/$n already exists"; DIRTY=1; }
done
if [ "$DIRTY" -eq 1 ]; then
    say "witness-accounts: CANNOT RUN - the ground is not clear (above)."
    say "  This script will not touch state it did not create."
    exit 2
fi
GROUND_CLEAR=1
say "  ground clear: neither name exists as user, group, directory, home, record or marker."

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
head2 "1b. a refused password unwinds the Linux user (8 Oct 26; the Windows owner rule of 21 Aug 26) - 10086"

# CREATE.ACCOUNT USER makes the Linux user, then asks for its password.  Three
# entries the password rule refuses ("weak", under 8 characters), then "n" at
# the retry prompt: SD must remove the user it just made (userdel-home, then
# userdel) and say "Nothing was created".  Before 8 Oct it carried on and made
# the account around a user with no password.
# ***THE NULL CASE IS NAMED, NOT ASSUMED.***  "The user is gone" is also true of
# a user that was never made, so the row that proves the user existed first is
# the one that reads SD's own "User <name> Created" (10007), and every row after
# it counts as NOT REACHED without it.  The retry answer is read, not trusted:
# 10008's prompt must be on screen before the "n" can have meant anything.
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC_REFUSE, three refused passwords, then n" \
             "CREATE.ACCOUNT USER $ACC_REFUSE" "weak" "weak" "weak" "n")
if [ "$COMMIT" -eq 1 ]; then
    if printf '%s' "$OUT" | grep -qF -- "User $ACC_REFUSE Created"; then
        ck_says "1b0 the Linux user WAS made first (10007), so its absence below is an unwind" "User $ACC_REFUSE Created" "$OUT"
        ck_says "1b1 the password was refused and a retry was offered (10008)" "password not set, Retry" "$OUT"
        ck_says "1b2 SD said nothing was created (10086)" "An account must have a password. Nothing was created." "$OUT"
        ck_silent "1b3 and did not say the removal failed (10130)" "could not be removed again" "$OUT"
        ck "1b4 the Linux user is gone"        no "$(yesno_user "$ACC_REFUSE")"
        ck "1b5 its home went with it"         no "$(yesno_dir "/home/$ACC_REFUSE")"
        ck "1b6 no sdu_ group was made"        no "$(yesno_group "sdu_$ACC_REFUSE")"
        ck "1b7 no account directory was made" no "$(yesno_dir "$ACCOUNTS_ROOT/$ACC_REFUSE")"
        ck "1b8 no register record was made"   no "$(yesno_file "$REGISTER/$ACC_REFUSE_UC")"
    else
        for r in "1b1 the password was refused and a retry was offered (10008)" \
                 "1b2 SD said nothing was created (10086)" \
                 "1b3 and did not say the removal failed (10130)" \
                 "1b4 the Linux user is gone" "1b5 its home went with it" \
                 "1b6 no sdu_ group was made" "1b7 no account directory was made" \
                 "1b8 no register record was made"; do
            not_reached "$r"
        done
        ck "1b0 the Linux user WAS made first (10007), so its absence below is an unwind" yes no
    fi
    # Whatever happened, this run does not leave the user behind.
    if [ "$(yesno_user "$ACC_REFUSE")" = yes ]; then
        userdel -r "$ACC_REFUSE" >/dev/null 2>&1 \
            && say "  1b cleanup: userdel -r $ACC_REFUSE (SD did not remove it)" \
            || say "  1b cleanup: userdel -r $ACC_REFUSE FAILED - remove it by hand"
    fi
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
PW_OS="Zz9-$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-14)"
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
        # 13 Oct 26 - S.63: THE OS-ACCESS GATES ARE BACK AND A NEW ACCOUNT STARTS WITH BOTH
        #   OFF.  Fields 7/8 (ACC$SH / ACC$OS.EXEC) hold 'no', written by create_account, so
        #   a decision can be told from a record nobody completed; and the account is in
        #   neither route group (the ssh / API default is off too).  The same facts are said
        #   aloud: 10102 for the gates, 10079 for the routes.  M2d / M5a of witness-absence.sh
        #   read the same record from a second account; this row is the one that reads it
        #   from the account the DELETE phase then removes.
        ck "A3c fields 7/8 (ACC\$SH / ACC\$OS.EXEC) are no / no: a new account has neither gate" "no no" \
           "$(sed -n '7p' "$REGISTER/$ACC_UC") $(sed -n '8p' "$REGISTER/$ACC_UC")"
        ck_says "A3d CREATE.ACCOUNT reported both gates off (10102)" "Account $ACC has SH no, OS.EXECUTE no" "$OUT"
        ck_says "A3e and no remote access (10079)" "$ACC has no remote access: not ssh, not the API" "$OUT"
        ck "A3f and the machine agrees: in neither sdssh nor sdapi" "no no" \
           "$(in_group "$ACC" sdssh) $(in_group "$ACC" sdapi)"
        # 17 Oct 26 - S.64: the three edit gates are written the same way, 'no' unless a word asked for them
        #   (fields 10/11/12 = ACC$VOC.EDIT / ACC$BP.EDIT / ACC$DICT.EDIT), and the command says so aloud (11409).
        ck "A3g fields 10-12 (VOC.EDIT / BP.EDIT / DICT.EDIT) are no / no / no: a new account has none of the three" "no no no" \
           "$(sed -n '10p' "$REGISTER/$ACC_UC") $(sed -n '11p' "$REGISTER/$ACC_UC") $(sed -n '12p' "$REGISTER/$ACC_UC")"
        ck_says "A3h CREATE.ACCOUNT reported the three edit gates off (11409)" "Account $ACC has VOC.EDIT no, BP.EDIT no, DICT.EDIT no" "$OUT"
        # 18 Oct 26 - S.66: the two shared-account gates are written explicitly for a USER account, read 'yes' (the delivered
        #   default is ON, and a decided state is told from a blank) and write 'no', and the command says so aloud (11515).
        ck "A3i fields 13-14 (SHARED.READ / SHARED.WRITE) are yes / no: a new account can read the shared account's files and cannot write them" "yes no" \
           "$(sed -n '13p' "$REGISTER/$ACC_UC") $(sed -n '14p' "$REGISTER/$ACC_UC")"
        ck_says "A3j CREATE.ACCOUNT reported both (11515)" "Account $ACC has shared.read yes, shared.write no" "$OUT"
    else
        not_reached "A2 field 5 blank"
        not_reached "A3 field 4 not written"
        not_reached "A3b field 6 not written"
        not_reached "A3c fields 7/8 are no / no"
        not_reached "A3d both gates off said"
        not_reached "A3e no remote access said"
        not_reached "A3f in neither route group"
        not_reached "A3g fields 10-12 are no / no / no"
        not_reached "A3h the three edit gates off said"
        not_reached "A3i fields 13-14 are yes / no"
        not_reached "A3j both shared gates said (11515)"
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
    # 4 Oct 26 - A7c IS REVERSED, as witness-absence.sh's M7b was on 20 Sep: S.29 has the
    # installer create sdapi (and sdssh) before any account, so "does not exist" measured a
    # decision that had been taken back and failed on every fresh install since.
    ck "A7c the sdapi group EXISTS (S.29: membership is the API route)" yes "$(yesno_group sdapi)"
fi

# ==========================================================================
head2 "2d. MODIFY.ACCOUNT shared-read-on|off, shared-write-on|off on that account (S.66) - WRITTEN, NOT RUN"

# The register field a row reads is the DISK, not what the verb said; the verb's report is the second instrument.  The same
# gating as phase 3: no registered account, no rows (they would measure nothing).
set_field() {   # set_field FILE N VALUE - one line of a register record replaced in place (root, so the file's owner and mode stay)
    local f="$1" n="$2" v="$3"
    awk -v n="$n" -v v="$v" 'NR == n { print v; next } { print }' "$f" > "$f.tmp.$$" && cat "$f.tmp.$$" > "$f"
    rm -f "$f.tmp.$$"
}
reg_rest() { sed -n '1,12p;15,99p' "$REGISTER/$ACC_UC" | md5sum | cut -d' ' -f1; }   # every field but 13 and 14
AUD="$SDSYS/audit"

if [ "$COMMIT" -eq 1 ] && [ "$CREATED" -ne 1 ]; then
    for r in "M1 shared-read-off" "M2 repeat says already" "M3 shared-read-on" "M4 shared-write-on" "M5 repeat says already" \
             "M6 shared-write-off" "M7 blank field: read-on says already" "M8 blank field: read-off writes no" "M9 other fields untouched" "M10 audit lines lower case"; do
        not_reached "$r"
    done
else
    REST0=""; AUD0=0
    if [ "$COMMIT" -eq 1 ]; then
        REST0=$(reg_rest); AUD0=$(wc -l < "$AUD" 2>/dev/null || echo 0)
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-read-off" "MODIFY.ACCOUNT $ACC shared-read-off")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M1 reported both states (11515)" "Account $ACC has shared.read no, shared.write no" "$OUT"
        ck "M1b field 13 is no, field 14 is no" "no no" "$(sed -n '13p' "$REGISTER/$ACC_UC") $(sed -n '14p' "$REGISTER/$ACC_UC")"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-read-off, again" "MODIFY.ACCOUNT $ACC shared-read-off")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M2 a repeat says it already had that access (10080)" "$ACC already had that access; nothing changed" "$OUT"
        ck "M2b and field 13 is still no" no "$(sed -n '13p' "$REGISTER/$ACC_UC")"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-read-on" "MODIFY.ACCOUNT $ACC shared-read-on")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M3 reported both states" "Account $ACC has shared.read yes, shared.write no" "$OUT"
        ck "M3b field 13 is yes (a decided state, not blank)" yes "$(sed -n '13p' "$REGISTER/$ACC_UC")"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-write-on" "MODIFY.ACCOUNT $ACC shared-write-on")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M4 reported both states" "Account $ACC has shared.read yes, shared.write yes" "$OUT"
        ck "M4b field 14 is yes" yes "$(sed -n '14p' "$REGISTER/$ACC_UC")"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-write-on, again" "MODIFY.ACCOUNT $ACC shared-write-on")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M5 a repeat says it already had that access (10080)" "$ACC already had that access; nothing changed" "$OUT"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-write-off" "MODIFY.ACCOUNT $ACC shared-write-off")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M6 reported both states" "Account $ACC has shared.read yes, shared.write no" "$OUT"
        ck "M6b field 14 is no" no "$(sed -n '14p' "$REGISTER/$ACC_UC")"
    fi
    # THE BLANK-MEANS-ON ROWS.  A blank field 13 is read ON, so shared-read-on has nothing to do, and shared-read-off MUST write
    # the no: if os.was were "= yes" the gate could never be withdrawn from an account whose field is blank.
    if [ "$COMMIT" -eq 1 ]; then
        set_field "$REGISTER/$ACC_UC" 13 ""
        ck "M7 precondition: field 13 is blank now (the null case of the two rows below)" "" "$(sed -n '13p' "$REGISTER/$ACC_UC")"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-read-on on a BLANK field 13" "MODIFY.ACCOUNT $ACC shared-read-on")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "M7 blank means ON, so shared-read-on says it already had that access (10080)" "$ACC already had that access; nothing changed" "$OUT"
        ck "M7b and field 13 was not written" "" "$(sed -n '13p' "$REGISTER/$ACC_UC")"
    fi
    OUT=$(run_sd "MODIFY.ACCOUNT $ACC shared-read-off on a BLANK field 13" "MODIFY.ACCOUNT $ACC shared-read-off")
    if [ "$COMMIT" -eq 1 ]; then
        ck_silent "M8 shared-read-off on a blank field does NOT say it already had that access" "already had that access" "$OUT"
        ck_says "M8b it reported shared.read no" "Account $ACC has shared.read no" "$OUT"
        ck "M8c and WROTE the no into field 13" no "$(sed -n '13p' "$REGISTER/$ACC_UC")"
        ck "M9 no other field of the record changed through the whole sequence (fields 1-12 and 15 up)" "$REST0" "$(reg_rest)"
        NEWAUD=$(tail -n +"$((AUD0 + 1))" "$AUD" 2>/dev/null)
        printf '%s\n' "$NEWAUD" | grep -F 'modify.account' | sed -e 's/^/      | /'
        ck_says "M10 the audit trail names the words in lower case" "modify.account shared-read-off account=$ACC" "$NEWAUD"
        ck_silent "M10b and none of them in upper case" "SHARED-READ-OFF" "$NEWAUD"
    fi
fi

# ==========================================================================
head2 "2e. the shared account on this install (S.66) - WRITTEN, NOT RUN: the installer made it; SD refuses what must be refused"

SHARED_REG="$REGISTER/shared"
SHARED_DIR=/home/sd/group_accounts/shared
SHARED_OK=0
if [ "$COMMIT" -eq 1 ]; then
    if [ -e "$SHARED_REG" ] && [ -d "$SHARED_DIR" ]; then
        SHARED_OK=1
        say "  the shared account's register record:"
        awk '{printf "      %d: %s\n", NR, $0}' "$SHARED_REG"
    else
        say "  THERE IS NO SHARED ACCOUNT on this install (register $(yesno_file "$SHARED_REG"), directory $(yesno_dir "$SHARED_DIR")):"
        say "  this install predates S.66, or its creation failed; the rows below count as NOT REACHED."
    fi
fi
if [ "$COMMIT" -eq 1 ] && [ "$SHARED_OK" -ne 1 ]; then
    for r in "S1 the register says where the account is and its group" "S2 the directory is sdsys:sdusers 2775" "S3 every file in it is 664" \
             "S4 sdg_shared holds root and sdsys only" "S5 DELETE.ACCOUNT shared is refused" "S6 CREATE.ACCOUNT GROUP shared is refused" \
             "S7 CREATE.ACCOUNT USER shared is refused and makes no Linux user" "S8 LOGTO shared is refused for an ordinary user"; do
        not_reached "$r"
    done
else
    if [ "$COMMIT" -eq 1 ]; then
        ck "S1 line 1 of the register record is the directory, line 3 the group" "$SHARED_DIR sdg_shared" "$(sed -n '1p' "$SHARED_REG") $(sed -n '3p' "$SHARED_REG")"
        ck "S2 the directory is sdsys:sdusers, mode 2775 (every SD user's own process can read the files through the kernel)" "sdsys sdusers 2775" \
           "$(stat -c '%U %G %a' "$SHARED_DIR")"
        BAD=$(find "$SHARED_DIR" -type f ! -perm 664 2>/dev/null | head -3 | tr '\n' ' ')
        ck "S3 no file in it has a mode other than 664 (these do: ${BAD:-none})" "" "$BAD"
        ck "S4 sdg_shared holds root and sdsys and nobody else (only SDSYS can sign on to the account: withdrawing shared.read is a real wall)" "root,sdsys" \
           "$(getent group sdg_shared | cut -d: -f4 | tr ',' '\n' | sort | paste -sd, -)"
    fi
    REGSUM=""
    [ "$COMMIT" -eq 1 ] && REGSUM=$(md5sum < "$SHARED_REG")
    OUT=$(run_sd "DELETE.ACCOUNT shared (no confirmation is asked: the refusal comes first)" "DELETE.ACCOUNT shared")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "S5 refused with 11517's words" "The shared account cannot be deleted" "$OUT"
        ck "S5b the register record is as it was" "$REGSUM" "$(md5sum < "$SHARED_REG")"
        ck "S5c and the directory is still there" yes "$(yesno_dir "$SHARED_DIR")"
    fi
    OUT=$(run_sd "CREATE.ACCOUNT GROUP shared, with no marker" "CREATE.ACCOUNT GROUP shared")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "S6 refused with 11516's words" "reserved for the shared account" "$OUT"
        ck "S6b the register record is as it was" "$REGSUM" "$(md5sum < "$SHARED_REG")"
        ck "S6c and sdg_shared still holds root and sdsys only" "root,sdsys" "$(getent group sdg_shared | cut -d: -f4 | tr ',' '\n' | sort | paste -sd, -)"
    fi
    # The ground first: a Linux user or group that is already called shared would make S7b measure nothing.
    SHUSER_BEFORE=no
    if [ "$COMMIT" -eq 1 ]; then
        SHUSER_BEFORE=$(yesno_user shared)
        [ "$SHUSER_BEFORE" = yes ] && say "  a Linux user named shared EXISTS before S7: S7b and S7c are NOT REACHED (they could not tell a refusal from that user)"
    fi
    OUT=$(run_sd "CREATE.ACCOUNT USER shared" "CREATE.ACCOUNT USER shared")
    if [ "$COMMIT" -eq 1 ]; then
        ck_says "S7 refused with 11516's words" "reserved for the shared account" "$OUT"
        if [ "$SHUSER_BEFORE" = no ] && [ "$(yesno_group sdu_shared)" = no ]; then
            ck "S7b NO Linux user named shared was made (the refusal comes before any user or group is)" no "$(yesno_user shared)"
            ck "S7c and no group sdu_shared" no "$(yesno_group sdu_shared)"
        else
            not_reached "S7b no Linux user named shared was made"
            not_reached "S7c no group sdu_shared"
        fi
        # whatever SD did, this run does not leave a user it made
        if [ "$SHUSER_BEFORE" = no ] && [ "$(yesno_user shared)" = yes ]; then
            userdel -r shared >/dev/null 2>&1 && say "  S7 cleanup: userdel -r shared (SD should have refused first)" || say "  S7 cleanup: userdel -r shared FAILED - remove it by hand"
        fi
    fi
    # An ORDINARY session: the account created in 2c, running as its own Linux user.  Entering shared needs membership of sdg_shared.
    if [ "$COMMIT" -eq 1 ] && [ "$CREATED" -eq 1 ]; then
        say "  --- sd session as $ACC (an ordinary user): LOGTO shared ---"
        AUD1=$(wc -l < "$AUD" 2>/dev/null || echo 0)
        OUT=$(printf '\nTERM 200,9999\nLOGTO shared\nOFF\n' | timeout 90 sudo -u "$ACC" "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g')
        printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
        NEWAUD=$(tail -n +"$((AUD1 + 1))" "$AUD" 2>/dev/null)
        ck_says "S8 refused with 10003's words" "User not allowed in requested account" "$OUT"
        ck_says "S8b and audited as not granted" "logto refused account=shared reason=not granted" "$NEWAUD"
    elif [ "$COMMIT" -eq 1 ]; then
        not_reached "S8 LOGTO shared is refused for an ordinary user (no ordinary account was made in 2c)"
    fi
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
