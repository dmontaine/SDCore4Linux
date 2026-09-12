#!/usr/bin/env bash
#
# witness-accounts.sh - the PRIVILEGED half of the account family: create an
#                       account, check what it made, delete it, check what it
#                       removed.  PORT_ADOPTION queue 22, ranked item 6; the
#                       intent is the port's verify-createaccount.ps1 and
#                       verify-delaccount.ps1.
#
#   bash   /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/witness-accounts.sh
#   sudo bash /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/witness-accounts.sh --commit
#
# ***IT NEEDS sudo, AND ONLY FOR --commit.***  The dry run changes nothing and
# needs no privilege: run it first, read the commands it prints, then commit.
#
# Exit 0 every check passed, 1 a check failed, 2 it could not run.
#
# ***THIS SCRIPT HAS NEVER BEEN RUN.  WRITTEN 12 Sep 2026 BY A SESSION THAT
# CANNOT sudo*** (`sudo -n` answers "interactive authentication is required"),
# so it is parse-checked and byte-scanned and nothing more.  That is why the
# dry run is the DEFAULT rather than an option: the first thing anybody should
# do with it is read what it intends to do, on a run that cannot do it.
#
# WHY A SCRIPT AND NOT A VERIFIER.  gplbld/verify-accounts.py covers everything
# about accounts that an ordinary user can measure - the register against the
# filesystem and against /etc/passwd, and the verbs refusing a non-root session.
# What it cannot do is CREATE one: measured 12 Sep 2026, `CREATE.ACCOUNT` and
# `DELETE.ACCOUNT` from a plain `sd` session as an ADMINISTRATOR both answer
# 2001 "Command requires administrator privileges" and do nothing.  So the
# other half is one owner-run script, on the model queues 12 and 14 used.
#
# ***WHAT IT DELIBERATELY DOES NOT TEST, AND WHY IT IS NOT AN OVERSIGHT.***
# The SD-CREATED Linux user.  `CREATE.ACCOUNT USER <name>` without NO.QUERY
# creates the Linux user too and PROMPTS for its password, and NO.QUERY without
# an existing user is refused outright (message 10039, which phase 1 witnesses).
# Driving that prompt unattended means putting a password in a script, so the
# SD-made branch - and DELETE.ACCOUNT's matching 10028 "OS User: %1 Deleted" -
# is left for a hand run, and phase 5 prints the exact command for it.
# ***PHASE 3 IS THEREFORE THE BORROWED-USER BRANCH***, which is the port's own
# second case: SD did not make the Linux user, so it must leave it behind and
# say so (10036), and the confirmation must use the SHORTER wording (10085) so
# it never promises what it will not do.
#
# THE PIPED-SESSION RULES ARE THE PROJECT'S, NOT THIS FILE'S:
#   * a blank first line absorbs anything the terminal emits before the prompt;
#   * TERM 200,9999 stops pagination, which down a pipe is a prompt like any
#     other;
#   * every session ends in OFF - an install older than c2b375d busy-loops at
#     end of input without it;
#   * a verb that prompts EATS THE NEXT LINE, so DELETE.ACCOUNT's confirmation
#     is answered on its own line before OFF.  DELACC:257-260 reads it with
#     `input yn`, upcases, and treats Enter as N.
#
set -u

# ***THE SCRIPT NAMES ITSELF BY ABSOLUTE PATH, EVERY VARIABLE EXPANDED.***
# CLAUDE.md's hand-over rule: the re-run command it prints lands in somebody
# else's shell, in some other directory, and a bare or relative $0 breaks
# there.  The dry run printed exactly that fault before this line existed.
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"

SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
REGISTER="$SDSYS/ACCOUNTS"
ACCOUNTS_ROOT=/home/sd/user_accounts

# The throwaway name.  "zz" so it sorts away from anything real and cannot
# collide with a verb; phase 0 refuses if anything of that name already exists.
ACC=zzacct2
ACC_UC=ZZACCT2
ACC_REFUSE=zzacct1          # phase 1 only; nothing is ever created for it
ACC_REFUSE_UC=ZZACCT1

COMMIT=0
LOG=""

PASS=0
FAIL=0
MADE_USER=0
MADE_ACCOUNT=0

usage() {
    sed -n '2,50p' "$0"
    exit 2
}

for arg in "$@"; do
    case "$arg" in
        --commit) COMMIT=1 ;;
        --log=*)  LOG="${arg#--log=}" ;;
        # --name is for a collision, and it is also how the ground-clear guard
        # below is exercised: `--name=don` on a DRY RUN must refuse, because
        # don exists.  That guard is the only thing standing between this
        # script and state it did not create, so it wants a way to be seen
        # working rather than an argument that it does.
        --name=*) ACC="${arg#--name=}" ;;
        -h|--help) usage ;;
        *) echo "witness-accounts: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done

ACC_UC=$(printf '%s' "$ACC" | tr '[:lower:]' '[:upper:]')

if [ -z "$LOG" ]; then
    LOG="/tmp/witness-accounts.$(date +%Y%m%d-%H%M%S).log"
fi
exec > >(tee -a "$LOG") 2>&1

say()  { printf '%s\n' "$*"; }
head2() { say ""; say "=== $* ============================================"; }

# ***EVERY CHECK PRINTS WHAT IT COMPARED, NOT ONLY WHAT IT CONCLUDED.***
ck() {
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        PASS=$((PASS + 1)); say "  [PASS] $name: expected '$want', got '$got'"
    else
        FAIL=$((FAIL + 1)); say "  [FAIL] $name: expected '$want', got '$got'"
    fi
}

# Anchored on a string that appears ONLY on the path being claimed.  A pattern
# carried by the failure output too is not a check.
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

# Drive one sd session.  In a dry run it prints the session and returns empty,
# so every check that reads its output fails loudly rather than passing on ''.
#
# ***ALL NARRATION GOES TO fd 2 AND ONLY SD'S OWN OUTPUT COMES BACK ON fd 1.***
# The first draft said everything on stdout, and `OUT=$(run_sd ...)` then
# captured the narration INTO the text the checks search - including the
# command lines this function echoes.  That is the instrument rule's own
# example: sd echoes each command too, so a check anchored on text that the
# echo also carries is a false positive with a check's name on it, and
# ck_silent was the arm exposed to it.  fd 2 is merged into the same tee by the
# exec above, so the transcript still reaches the log in order.
run_sd() {
    local title="$1"; shift
    say "  --- sd session: $title ---" >&2
    say "      binary : $SD" >&2
    local line
    for line in "$@"; do say "      > $line" >&2; done
    if [ "$COMMIT" -eq 0 ]; then
        say "      (dry run - not executed)" >&2
        printf ''
        return 0
    fi
    local body out
    body=$'\n''TERM 200,9999'
    for line in "$@"; do body="$body"$'\n'"$line"; done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | timeout 120 "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g')
    printf '%s' "$out" | sed -e 's/^/      | /' >&2
    printf '%s' "$out"
}

cleanup() {
    local rc=$?
    if [ "$COMMIT" -eq 1 ] && { [ "$MADE_ACCOUNT" -eq 1 ] || [ "$MADE_USER" -eq 1 ]; }; then
        head2 "CLEANUP - removing whatever is left of $ACC"
        if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$REGISTER/$ACC_UC" ]; then
            say "  the SD account is still registered; removing it"
            printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC"$'\n''Y'$'\n''OFF'$'\n' \
                | timeout 120 "$SD" >/dev/null 2>&1
        fi
        if [ "$MADE_USER" -eq 1 ] && id -u "$ACC" >/dev/null 2>&1; then
            say "  removing the Linux user this script created, and its home"
            userdel -r "$ACC" >/dev/null 2>&1 \
                && say "  userdel -r $ACC: done" \
                || say "  userdel -r $ACC: FAILED - remove it by hand"
        fi
        say "  left behind now: register=$( [ -e "$REGISTER/$ACC_UC" ] && echo yes || echo no )" \
            "dir=$( [ -d "$ACCOUNTS_ROOT/$ACC" ] && echo yes || echo no )" \
            "user=$( id -u "$ACC" >/dev/null 2>&1 && echo yes || echo no )" \
            "group=$( getent group "sdu_$ACC" >/dev/null && echo yes || echo no )"
    fi
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
say "  throwaway  : $ACC (and $ACC_REFUSE, for the refusal only)"
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
    say "  CREATE.ACCOUNT and DELETE.ACCOUNT answer 2001 to any other session;"
    say "  re-run as: sudo bash $SELF --commit"
    exit 2
fi

# ***REFUSE IF ANYTHING OF THE THROWAWAY NAME ALREADY EXISTS.***  Every check
# below describes something this run made.  A survivor from an earlier run
# belongs to that run, and deleting it at the end would be destroying state
# this script did not create.
DIRTY=0
for n in "$ACC" "$ACC_REFUSE"; do
    id -u "$n" >/dev/null 2>&1 && { say "  DIRTY: Linux user $n already exists"; DIRTY=1; }
    getent group "sdu_$n" >/dev/null && { say "  DIRTY: group sdu_$n already exists"; DIRTY=1; }
    [ -d "$ACCOUNTS_ROOT/$n" ] && { say "  DIRTY: $ACCOUNTS_ROOT/$n already exists"; DIRTY=1; }
done
for n in "$ACC_UC" "$ACC_REFUSE_UC"; do
    [ -e "$REGISTER/$n" ] && { say "  DIRTY: register record $n already exists"; DIRTY=1; }
done
if [ "$DIRTY" -eq 1 ]; then
    say "witness-accounts: CANNOT RUN - the ground is not clear (above)."
    say "  Remove those by hand and run again; this script will not touch"
    say "  state it did not create."
    exit 2
fi
say "  ground clear: neither name exists as a user, group, directory or record."

# The before-state, so the after-state means something.
head2 "0b. the state before"
say "  register records : $(ls -1 "$REGISTER" | tr '\n' ' ')"
say "  account dirs     : $(ls -1 "$ACCOUNTS_ROOT" | tr '\n' ' ')"
say "  sdusers members  : $(getent group sdusers | cut -d: -f4)"
say "  sdadmin members  : $(getent group sdadmin | cut -d: -f4)"

# ==========================================================================
head2 "1. NO.QUERY without an existing Linux user is refused (10039)"
say "  CREATEA:281 - creating a Linux user means setting its password, and"
say "  that needs a prompt.  Nothing may be created on this path."

OUT=$(run_sd "CREATE.ACCOUNT USER $ACC_REFUSE NO.QUERY" \
             "CREATE.ACCOUNT USER $ACC_REFUSE NO.QUERY")
if [ "$COMMIT" -eq 1 ]; then
    ck_says "1a refused with 10039's wording" \
            "setting its password needs a prompt" "$OUT"
    # ***AND THE REFUSAL MUST HAVE COST NOTHING.***  A verb that refuses AFTER
    # making the Linux user is the failure this row exists for, and it is the
    # shape CREATEA's own history warns about for the ssh-only branch.
    ck "1b no Linux user was made" "no" \
       "$(id -u "$ACC_REFUSE" >/dev/null 2>&1 && echo yes || echo no)"
    ck "1c no group was made" "no" \
       "$(getent group "sdu_$ACC_REFUSE" >/dev/null && echo yes || echo no)"
    ck "1d no directory was made" "no" \
       "$([ -d "$ACCOUNTS_ROOT/$ACC_REFUSE" ] && echo yes || echo no)"
    ck "1e no register record was made" "no" \
       "$([ -e "$REGISTER/$ACC_REFUSE_UC" ] && echo yes || echo no)"
fi

# ==========================================================================
head2 "2. a borrowed Linux user, then CREATE.ACCOUNT USER ... NO.QUERY"
say "  useradd -m $ACC     (this script's own doing, not SD's)"
if [ "$COMMIT" -eq 1 ]; then
    if useradd -m "$ACC"; then
        MADE_USER=1
        say "  created Linux user $ACC (uid $(id -u "$ACC"))"
    else
        say "witness-accounts: CANNOT RUN - useradd failed; nothing was done."
        exit 2
    fi
fi

OUT=$(run_sd "CREATE.ACCOUNT USER $ACC NO.QUERY" \
             "CREATE.ACCOUNT USER $ACC NO.QUERY")
if [ "$COMMIT" -eq 1 ]; then
    MADE_ACCOUNT=1
    # Two instruments: what SD said, and what is on disk.  Either alone can be
    # satisfied by the wrong thing.
    ck_says "2a it added the user to sdusers" "added to sdusers" "$OUT"
    ck "2b the register record exists" "yes" \
       "$([ -e "$REGISTER/$ACC_UC" ] && echo yes || echo no)"
    ck "2c the account directory exists" "yes" \
       "$([ -d "$ACCOUNTS_ROOT/$ACC" ] && echo yes || echo no)"
    ck "2d the sdu_ group exists" "yes" \
       "$(getent group "sdu_$ACC" >/dev/null && echo yes || echo no)"
    if [ -d "$ACCOUNTS_ROOT/$ACC" ]; then
        # ***THE SETGID BIT IS THE ONE THAT MATTERS.***  Without it a record
        # written into the account lands in the writer's own group and the
        # account's group loses access to it.
        ck "2e the directory is owner:group $ACC:sdu_$ACC, mode 2775" \
           "$ACC sdu_$ACC 2775" \
           "$(stat -c '%U %G %a' "$ACCOUNTS_ROOT/$ACC")"
    fi
    if [ -e "$REGISTER/$ACC_UC" ]; then
        say "  register record, field by field (KEYS.H:264-301):"
        awk '{printf "      %d: %s\n", NR, $0}' "$REGISTER/$ACC_UC"
        ck "2f ACC\$PATH (field 1) names the directory" \
           "$ACCOUNTS_ROOT/$ACC" "$(sed -n '1p' "$REGISTER/$ACC_UC")"
        ck "2g ACC\$GROUP (field 3) names the group" \
           "sdu_$ACC" "$(sed -n '3p' "$REGISTER/$ACC_UC")"
        ck "2h ACC\$TIER (field 5) defaults to STANDARD" \
           "STANDARD" "$(sed -n '5p' "$REGISTER/$ACC_UC")"
        ck "2i field 4 (retired ACC\$USERS) was NOT written" \
           "" "$(sed -n '4p' "$REGISTER/$ACC_UC")"
    fi
    ck "2j a STANDARD account's user is NOT in sdadmin" "no" \
       "$(id -nG "$ACC" 2>/dev/null | tr ' ' '\n' | grep -qx sdadmin && echo yes || echo no)"
fi

# ==========================================================================
head2 "3. DELETE.ACCOUNT leaves a Linux user SD did not create"
say "  DELACC:249-260 - one confirmation, Enter is N, so Y is sent on its own"
say "  line and the OFF after it is not eaten by the prompt."

OUT=$(run_sd "DELETE.ACCOUNT $ACC (answering Y)" "DELETE.ACCOUNT $ACC" "Y")
if [ "$COMMIT" -eq 1 ]; then
    # ***THE DISCRIMINATION IS THE POINT, AND IT IS THE PORT'S.***  10085 is
    # the SHORTER confirmation - account and directory only - and 10084 is the
    # one that also promises the Linux user.  Offering 10084 here would be a
    # promise the verb cannot keep.
    ck_says "3a the confirmation used the SHORTER wording (10085)" \
            "and its directory (y/<n>)?" "$OUT"
    ck_silent "3b it did NOT offer to delete the Linux user (10084)" \
              "its Linux user" "$OUT"
    ck_says "3c the data warning preceded it (10158)" \
            "removes everything the account holds" "$OUT"
    ck_says "3d it said the Linux user is not SD's (10036)" \
            "was not created by SD" "$OUT"
    ck_silent "3e it did NOT claim to delete the Linux user (10028)" \
              "OS User:" "$OUT"

    ck "3f the register record is gone" "no" \
       "$([ -e "$REGISTER/$ACC_UC" ] && echo yes || echo no)"
    ck "3g the account directory is gone" "no" \
       "$([ -d "$ACCOUNTS_ROOT/$ACC" ] && echo yes || echo no)"
    ck "3h the sdu_ group is gone" "no" \
       "$(getent group "sdu_$ACC" >/dev/null && echo yes || echo no)"
    # ***AND THE BORROWED USER IS STILL THERE.***  This is the row the whole
    # phase exists for: the others would all pass if DELETE.ACCOUNT had removed
    # the person's Linux account along with the SD one.
    ck "3i the BORROWED Linux user is still there" "yes" \
       "$(id -u "$ACC" >/dev/null 2>&1 && echo yes || echo no)"
    ck "3j and its home directory survived" "yes" \
       "$([ -d "/home/$ACC" ] && echo yes || echo no)"
    [ -e "$REGISTER/$ACC_UC" ] || MADE_ACCOUNT=0
fi

# ==========================================================================
head2 "4. verdict"
if [ "$COMMIT" -eq 0 ]; then
    say "  DRY RUN - nothing was executed and nothing was checked."
    say "  Re-run with --commit, as root, to make these measurements:"
    say "    sudo bash $SELF --commit"
    say ""
    say "  ***A DRY RUN IS NOT A PASS.*** Exit 2."
    exit 2
fi

say "  passed : $PASS"
say "  failed : $FAIL"
if [ "$((PASS + FAIL))" -eq 0 ]; then
    say "witness-accounts: FAILED - no check ran, so this proves nothing."
    exit 1
fi
if [ "$FAIL" -gt 0 ]; then
    say "witness-accounts: FAILED - $FAIL of $((PASS + FAIL)) checks failed."
    exit 1
fi

head2 "5. what is still owed, and it needs a person at the keyboard"
say "  The SD-CREATED Linux user is untested by this script.  Run it by hand:"
say "      sudo $SD"
say "      CREATE.ACCOUNT USER zzacct3 PROGRAMMER"
say "      (type a throwaway password at the prompt)"
say "      DELETE.ACCOUNT zzacct3"
say "      (answer y)"
say "  Expect the LONGER confirmation (10084, naming the Linux user), and"
say "  10028 \"OS User: zzacct3 Deleted\" where phase 3 got 10036.  That pair"
say "  is the half no unattended run can reach."

say "witness-accounts: PASSED - $PASS of $PASS checks passed."
exit 0
