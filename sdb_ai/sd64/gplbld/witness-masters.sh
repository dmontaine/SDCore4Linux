#!/usr/bin/env bash
#
# witness-masters.sh - what only a ROOT run on a real install (or the VM) shows about MASTER TO ACCOUNT (S.67 stage 2, D7; owner 17 Oct 2026, warned):
#                      the sdsys operating-system user in the account groups, the modes of the VOC and dictionaries, an SDSYS edit reaching a user's
#                      VOC at once, the refusal when the SDSYS session is older than the group membership, and the upgrade's repair of the modes.
#
#   bash      /home/don/Projects/SDCore4Linux-wt-s67/sdb_ai/sd64/gplbld/witness-masters.sh               (a dry run: says what it would do, changes nothing)
#   sudo bash /home/don/Projects/SDCore4Linux-wt-s67/sdb_ai/sd64/gplbld/witness-masters.sh --commit      (does it)
#
# ***sudo IS NEEDED, AND ONLY FOR --commit.***  Run it from the owner's login (SUDO_USER must name a person).  The dry run needs no privilege.
# Exit 0 every row passed, 1 a row failed or was not reached, 2 it could not run.  The log is /tmp/witness-masters.<time>.log.
#
# WHY IT EXISTS.  The sandbox suite (sandbox-masters.py) has ONE operating-system user, so it cannot show who OWNS a file, which GROUP a session is in,
# or root changing files that belong to ANOTHER user.  Those are this script's.  What it adds to the sandbox's rows is exactly that and nothing else:
#
#   1  sdsys-join as the sdsys user through sudo (the way SD calls it): the sdsys user is put in the group of a throwaway user and in no other; the
#      refused calls (sdusers, a group account's group, root, sdsys itself) leave /etc/group and /etc/gshadow byte for byte as they were.
#   2  group-write as root on a tree that holds what the unit test cannot make: a file owned by ANOTHER user, a file of another group, a link to a file
#      and a link to a directory (/etc), a data file's directory.  Only the account's own are changed; /etc and /etc/hostname keep their modes; a second
#      run changes nothing; an account whose directory belongs to another group (the shared account's shape) is refused.
#   3  CREATE.ACCOUNT USER <name> - SD's whole flow: sdsys is in the new group, the VOC is owner:group of the account with group rwx (setgid on the
#      directory) and rw on its subfiles; an SDSYS session saves a master record (ED on voc_master) and a ordinary session of the user finds the record
#      in its VOC AT ONCE; the audit line is in /usr/local/sdsys/audit; the file keeps its owner and group (written in place).
#   4  A SESSION OF SDSYS THAT BEGAN BEFORE THE ACCOUNT: a long-lived SDSYS session is started, a second account is made, and the first session's save is
#      REFUSED with the stale-session message (11586) and changes nothing; CHECK.MASTERS in it says norights stale-session; a NEW session saves.
#   5  The upgrade's repair: the account's modes are broken and sdsys is taken out of its group; CHECK.MASTERS says nonwritable (and norights
#      not-a-member); the installer's own join_sdsys_groups (cut out of installsdcore.sh, run with the real sudo and the real sd-elevate on a register of
#      one record) puts it right and says so; run again it changes nothing.
#
# NOT COVERED: the installer run as a whole (witness-release-run.sh and a real install are); SDSYS on a machine with a second administrator (there is
# none by design); the API server.  The throwaway names are zwmv, zwm1 and zwm2: the script refuses to run if any exists, and removes what it made.
#
# THE PROJECT'S INSTRUMENT RULES: every session prints its input lines and its output; a session that prints nothing FAILS (the null case); a PASS
# needs the success wording AND the state on the disk; a refusal row needs the success wording ABSENT; a row whose precondition failed is NOT REACHED,
# which is a failure.  Password answers are never echoed into the log.
set -u

SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
SD=/usr/local/sdsys/bin/sd
SDSYS=/usr/local/sdsys
REGISTER="$SDSYS/accounts"
ACCOUNTS_ROOT=/home/sd/user_accounts
ELEVATE=/usr/local/sbin/sd-elevate
AUDIT="$SDSYS/audit"
INSTALLER="$(cd "$(dirname "$0")/../../.." 2>/dev/null && pwd)/installsdcore.sh"
VU=zwmv           # the throwaway user for the verb rows (no SD account)
A1=zwm1           # a throwaway SD account made by CREATE.ACCOUNT
A2=zwm2           # and a second, made while a long-lived SDSYS session is open

COMMIT=0
LOG=""
PASS=0
FAIL=0
NOT_REACHED=0
GROUND_CLEAR=0
MADE_VU=0
MADE_A1=0
MADE_A2=0
WORK=""
FIFO=""
STALE_PID=""

for arg in "$@"; do
    case "$arg" in
        --commit) COMMIT=1 ;;
        --log=*)  LOG="${arg#--log=}" ;;
        -h|--help) sed -n '2,12p' "$0"; exit 2 ;;
        *) echo "witness-masters: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done
[ -n "$LOG" ] || LOG="/tmp/witness-masters.$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

say()   { printf '%s\n' "$*"; }
head2() { say ""; say "=== $* ============================================"; }
ck() {   # ck name want got
    if [ "$2" = "$3" ]; then PASS=$((PASS + 1)); say "  [PASS] $1: expected '$2', got '$3'"
    else FAIL=$((FAIL + 1)); say "  [FAIL] $1: expected '$2', got '$3'"; fi
}
ck_says() {   # ck_says name needle text   - the success wording must be there
    if printf '%s' "$3" | grep -qF -- "$2"; then PASS=$((PASS + 1)); say "  [PASS] $1: found \"$2\""
    else FAIL=$((FAIL + 1)); say "  [FAIL] $1: did NOT find \"$2\""; fi
}
ck_silent() {   # ck_silent name needle text   - and on a refusal row the success wording must be ABSENT
    if printf '%s' "$3" | grep -qF -- "$2"; then FAIL=$((FAIL + 1)); say "  [FAIL] $1: found \"$2\" and must not have"
    else PASS=$((PASS + 1)); say "  [PASS] $1: \"$2\" absent, as required"; fi
}
not_reached() { FAIL=$((FAIL + 1)); NOT_REACHED=$((NOT_REACHED + 1)); say "  [NOT REACHED] $1 - its precondition failed above, so it measured nothing"; }
yesno_user()  { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group() { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_path()  { [ -e "$1" ] && echo yes || echo no; }
members_of()  { getent group "$1" | cut -d: -f4; }
has_member()  { case ",$(members_of "$1")," in *",$2,"*) echo yes ;; *) echo no ;; esac; }
modes_of()    { stat -c '%U:%G %a' -- "$1" 2>/dev/null || echo "(absent)"; }
sha_of()      { cat /etc/group /etc/gshadow 2>/dev/null | sha256sum | cut -d' ' -f1; }

# one piped sd session, AS sdsys (S.26: only a real sdsys LOGIN administers, so the root-only loginuid bridge); narration to fd 2, sd's output to fd 1
run_sd() {
    local title="$1"; shift
    say "  --- sd session as sdsys: $title ---" >&2
    local line body out
    for line in "$@"; do case "$line" in _PW_) say "      > (password answer)" >&2 ;; *) say "      > $line" >&2 ;; esac; done
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; return 0; fi
    body=$'\n''TERM 200,9999'
    for line in "$@"; do if [ "$line" = "_PW_" ]; then body="$body"$'\n'"$PW_OS"; else body="$body"$'\n'"$line"; fi; done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | timeout 120 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g')
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    [ -n "$out" ] || say "      (the session printed NOTHING - the null case)" >&2
    printf '%s' "$out"
}

# one piped sd session as an ORDINARY user (its own Linux user)
run_user() {
    local who="$1" title="$2"; shift 2
    say "  --- sd session as $who (an ordinary user): $title ---" >&2
    local line body out
    for line in "$@"; do say "      > $line" >&2; done
    if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; return 0; fi
    body=$'\n''TERM 200,9999'
    for line in "$@"; do body="$body"$'\n'"$line"; done
    body="$body"$'\n''OFF'$'\n'
    out=$(printf '%s' "$body" | timeout 120 sudo -u "$who" "$SD" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g')
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    [ -n "$out" ] || say "      (the session printed NOTHING - the null case)" >&2
    printf '%s' "$out"
}

# as the sdsys user, through sudo, the way SD calls the helper
as_sdsys_elevate() {
    say "      \$ sudo -u sdsys sudo $ELEVATE $*" >&2
    local out
    out=$(sudo -u sdsys sudo "$ELEVATE" "$@" 2>&1); local rc=$?
    printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
    printf '%s\nEXIT=%d' "$out" "$rc"
}

cleanup() {
    local rc=$?
    [ "$COMMIT" -eq 1 ] || exit $rc
    head2 "CLEANUP - removing whatever this run made"
    if [ -n "$STALE_PID" ] && kill -0 "$STALE_PID" 2>/dev/null; then kill "$STALE_PID" 2>/dev/null; say "  stopped the long-lived SDSYS session ($STALE_PID)"; fi
    exec 3>&- 2>/dev/null
    for a in "$A1" "$A2"; do
        if [ -e "$REGISTER/$a" ]; then
            say "  $a is still registered; deleting it through SD (as sdsys)"
            printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $a"$'\n''y'$'\n''OFF'$'\n' \
                | timeout 90 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD" >/dev/null 2>&1
        fi
    done
    if [ "$GROUND_CLEAR" -eq 1 ]; then
        for u in "$A1" "$A2" "$VU"; do
            if id -u "$u" >/dev/null 2>&1; then userdel -r "$u" >/dev/null 2>&1 && say "  userdel -r $u: done" || say "  userdel -r $u: FAILED - remove it by hand"; fi
            if getent group "sdu_$u" >/dev/null; then groupdel "sdu_$u" >/dev/null 2>&1 && say "  groupdel sdu_$u: done" || say "  groupdel sdu_$u: FAILED - remove it by hand"; fi
            [ -d "/home/$u" ] && ! id -u "$u" >/dev/null 2>&1 && rm -rf -- "/home/$u" && say "  removed /home/$u"
            [ -d "$ACCOUNTS_ROOT/$u" ] && rm -rf -- "$ACCOUNTS_ROOT/$u" && say "  removed $ACCOUNTS_ROOT/$u"
        done
    fi
    [ -n "$WORK" ] && rm -rf -- "$WORK"
    for u in "$A1" "$A2" "$VU"; do
        say "  left behind for $u: user=$(yesno_user "$u") group=$(yesno_group "sdu_$u") dir=$(yesno_path "$ACCOUNTS_ROOT/$u") register=$(yesno_path "$REGISTER/$u")"
    done
    exit $rc
}
trap cleanup EXIT

say "witness-masters: $( [ "$COMMIT" -eq 1 ] && echo 'COMMIT - it will change this system' || echo 'DRY RUN - it changes nothing' )"
say "  date : $(date -Is)   uid: $(id -u) ($(id -un))   sudo user: ${SUDO_USER:-none}"
say "  sd   : $SD   helper: $ELEVATE   installer (for join_sdsys_groups): $INSTALLER"
say "  log  : $LOG"

head2 "0. preconditions and the ground being clear"
for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT" "$ELEVATE" "$AUDIT" "$SDSYS/voc_master" "$SDSYS/dict_master" "$SDSYS/master_state" "$INSTALLER"; do
    [ -e "$p" ] || { say "witness-masters: CANNOT RUN - $p does not exist (install a build with S.67 stage 2 first)"; exit 2; }
done
grep -q 'sdsys-join' "$ELEVATE" && grep -q 'group-write' "$ELEVATE" || { say "witness-masters: CANNOT RUN - the installed sd-elevate lacks sdsys-join or group-write (an install of an earlier build)"; exit 2; }
id -u sdsys >/dev/null 2>&1 || { say "witness-masters: CANNOT RUN - no sdsys user"; exit 2; }
if [ "$COMMIT" -eq 1 ]; then
    [ "$(id -u)" -eq 0 ] || { say "witness-masters: CANNOT RUN - --commit needs root: sudo bash $SELF --commit"; exit 2; }
    [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ] || { say "witness-masters: CANNOT RUN - SUDO_USER must name a person"; exit 2; }
fi
DIRTY=0
for u in "$A1" "$A2" "$VU"; do
    [ "$(yesno_user "$u")" = yes ]  && { say "  DIRTY: Linux user $u already exists"; DIRTY=1; }
    [ "$(yesno_group "sdu_$u")" = yes ] && { say "  DIRTY: group sdu_$u already exists"; DIRTY=1; }
    [ -e "$ACCOUNTS_ROOT/$u" ]       && { say "  DIRTY: $ACCOUNTS_ROOT/$u already exists"; DIRTY=1; }
    [ -e "$REGISTER/$u" ]            && { say "  DIRTY: register record $u already exists"; DIRTY=1; }
    [ -e "/home/$u" ]                && { say "  DIRTY: /home/$u already exists"; DIRTY=1; }
done
[ "$DIRTY" -eq 0 ] || { say "witness-masters: CANNOT RUN - the ground is not clear (above); this script will not touch state it did not create"; exit 2; }
GROUND_CLEAR=1
say "  ground clear: $A1, $A2 and $VU exist as neither user, group, directory, home nor record."
if [ "$COMMIT" -eq 1 ]; then
    WORK=$(mktemp -d /var/tmp/witness-masters-work.XXXXXX) || { say "witness-masters: CANNOT RUN - no work directory"; exit 2; }
    say "  sdsys is in sdusers: $(has_member sdusers sdsys)   master files set up: $(yesno_path "$SDSYS/\$master.journal")"
fi
PW_OS="Zz9-$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-14)"

# ==========================================================================
head2 "1. sdsys-join, as the sdsys user through sudo (the way SD calls it)"
if [ "$COMMIT" -eq 1 ]; then
    "$ELEVATE" useradd "$VU" >/dev/null 2>&1 && "$ELEVATE" groupadd "sdu_$VU" >/dev/null 2>&1
    MADE_VU=1
    ck "1a (control) the throwaway user and its group exist, and sdsys is NOT in the group yet" "yes yes no" "$(yesno_user "$VU") $(yesno_group "sdu_$VU") $(has_member "sdu_$VU" sdsys)"
    OUT=$(as_sdsys_elevate sdsys-join "sdu_$VU")
    ck_says "1b sdsys-join sdu_$VU ran (exit 0)" "EXIT=0" "$OUT"
    ck "1c sdsys is a member of sdu_$VU now" "yes" "$(has_member "sdu_$VU" sdsys)"
    ck "1d ...and ONLY sdsys was added: the group's members are exactly sdsys" "sdsys" "$(members_of "sdu_$VU")"
    ck "1e ...no other group of sdsys changed (sdusers, sdssh, sdapi are as they were: sdsys is still in sdusers)" "yes" "$(has_member sdusers sdsys)"
    H0=$(sha_of)
    for g in sdusers sdssh sdapi sdfiles sdfileswrite sdg_shared sdu_root sdu_sdsys sudo; do
        OUT=$(as_sdsys_elevate sdsys-join "$g")
        ck_silent "1f sdsys-join $g is refused (no success command printed)" "usermod -aG" "$OUT"
        ck_silent "1f' ...and the exit status is not 0" "EXIT=0" "$OUT"
    done
    ck "1g after every refused call /etc/group and /etc/gshadow are byte for byte as before" "$H0" "$(sha_of)"
else
    say "  (dry run: would useradd $VU and groupadd sdu_$VU through the helper, run sdsys-join as the sdsys user, and try nine refusals)"
fi

# ==========================================================================
head2 "2. group-write, as root, on a tree that holds what a unit test cannot make"
if [ "$COMMIT" -eq 1 ] && [ "$MADE_VU" -eq 1 ]; then
    T="$ACCOUNTS_ROOT/$VU"
    mkdir -p "$T/voc" "$T/foo.dic" "$T/data" "$T/report.doc" 2>/dev/null
    for d in voc foo.dic data report.doc; do for f in %0 %1; do : > "$T/$d/$f"; chmod 0644 "$T/$d/$f"; chown "$VU:sdu_$VU" "$T/$d/$f"; done; chmod 0755 "$T/$d"; chown "$VU:sdu_$VU" "$T/$d"; done
    chown "$VU:sdu_$VU" "$T"; chmod 2755 "$T"
    : > "$T/foo.dic/rootfile"; chmod 0644 "$T/foo.dic/rootfile"; chown "root:sdu_$VU" "$T/foo.dic/rootfile"       # another OWNER
    : > "$T/foo.dic/wronggroup"; chmod 0644 "$T/foo.dic/wronggroup"; chown "$VU:sdusers" "$T/foo.dic/wronggroup" # another GROUP
    ln -s /etc/hostname "$T/foo.dic/lnk"                                                                          # a link to a file root could change
    ln -s /etc "$T/evil.dic"                                                                                      # a dictionary that is a link to /etc
    ETC_BEFORE=$(stat -c '%a' /etc); HOST_BEFORE=$(stat -c '%a' /etc/hostname)
    BEFORE="$(for p in voc voc/%0 foo.dic foo.dic/%0 foo.dic/rootfile foo.dic/wronggroup data data/%0 report.doc; do printf '%s=%s ' "$p" "$(stat -c '%a' "$T/$p")"; done)"
    say "  before: $BEFORE etc=$ETC_BEFORE hostname=$HOST_BEFORE"
    OUT=$(as_sdsys_elevate group-write "$T")
    ck_says "2a group-write ran and said what it did" "group-write: 2 directories and 4 file(s) changed" "$OUT"
    ck "2b the VOC and the dictionary directories are group rwx and setgid (2775)" "2775 2775" "$(stat -c '%a' "$T/voc") $(stat -c '%a' "$T/foo.dic")"
    ck "2c ...and their subfiles group rw (664)" "664 664 664 664" "$(stat -c '%a' "$T/voc/%0") $(stat -c '%a' "$T/voc/%1") $(stat -c '%a' "$T/foo.dic/%0") $(stat -c '%a' "$T/foo.dic/%1")"
    ck "2d a file owned by ANOTHER user (root) in the dictionary is left as it was (644)" "644" "$(stat -c '%a' "$T/foo.dic/rootfile")"
    ck "2e a file of ANOTHER group (sdusers) is left as it was (644)" "644" "$(stat -c '%a' "$T/foo.dic/wronggroup")"
    ck "2f a data file's directory and a directory called report.doc are not touched (755 / 755 / 644 / 644)" "755 755 644 644" "$(stat -c '%a' "$T/data") $(stat -c '%a' "$T/report.doc") $(stat -c '%a' "$T/data/%0") $(stat -c '%a' "$T/report.doc/%0")"
    ck "2g /etc and /etc/hostname - what the links point at - keep their modes: root did not follow a link" "$ETC_BEFORE $HOST_BEFORE" "$(stat -c '%a' /etc) $(stat -c '%a' /etc/hostname)"
    ck "2h owners and groups of what was changed are as they were (the verb changes modes only)" "$VU:sdu_$VU $VU:sdu_$VU" "$(modes_of "$T/voc" | cut -d' ' -f1) $(modes_of "$T/foo.dic/%0" | cut -d' ' -f1)"
    OUT=$(as_sdsys_elevate group-write "$T")
    ck_says "2i run again it changes nothing" "group-write: 0 directories and 0 file(s) changed" "$OUT"
    chgrp sdusers "$T"
    MODES1=$(modes_of "$T/voc")
    OUT=$(as_sdsys_elevate group-write "$T")
    ck_says "2j an account directory that belongs to ANOTHER group (the shared account's shape) is refused" "not to the account's own group" "$OUT"
    ck_silent "2k ...and says no success line" "group-write: " "$OUT"
    ck "2l ...and changed nothing" "$MODES1" "$(modes_of "$T/voc")"
    SH="/home/sd/group_accounts/shared"
    if [ -d "$SH" ]; then
        SB="$(find "$SH" -maxdepth 2 \( -name voc -o -name '*.dic' \) -printf '%p %m %u:%g\n' 2>/dev/null | sort | sha256sum | cut -d' ' -f1)"
        OUT=$(as_sdsys_elevate group-write "$SH")
        ck_says "2m the real shared account (group sdusers) is refused by group-write" "REFUSED" "$OUT"
        ck "2n ...and its VOC and dictionaries are as they were" "$SB" "$(find "$SH" -maxdepth 2 \( -name voc -o -name '*.dic' \) -printf '%p %m %u:%g\n' 2>/dev/null | sort | sha256sum | cut -d' ' -f1)"
    else
        say "  (no shared account here: 2m and 2n are left out - they need the real one)"
    fi
    rm -rf -- "$T"
else
    say "  (dry run: would build a tree with a foreign-owner file, a foreign-group file, two links and a data directory, and run group-write as the sdsys user)"
fi

# ==========================================================================
head2 "3. CREATE.ACCOUNT USER $A1 - SD's whole flow - and an SDSYS edit that reaches the user's VOC at once"
OUT=$(run_sd "CREATE.ACCOUNT USER $A1 (answering the Linux password)" "CREATE.ACCOUNT USER $A1" "_PW_" "_PW_")
CREATED1=0
if [ "$COMMIT" -eq 1 ]; then
    ck "3a (the gate) the register record exists" "yes" "$(yesno_path "$REGISTER/$A1")"
    if [ -e "$REGISTER/$A1" ]; then CREATED1=1; MADE_A1=1; fi
fi
if [ "$COMMIT" -eq 1 ] && [ "$CREATED1" -eq 1 ]; then
    ck "3b sdsys is a member of sdu_$A1 (put in by CREATE.ACCOUNT)" "yes" "$(has_member "sdu_$A1" sdsys)"
    V="$ACCOUNTS_ROOT/$A1/voc"
    ck "3c the VOC belongs to the account's user and group" "$A1:sdu_$A1 $A1:sdu_$A1" "$(modes_of "$V" | cut -d' ' -f1) $(modes_of "$V/%0" | cut -d' ' -f1)"
    ck "3d ...with group rwx on the directory and group rw on %0 and %1" "7 6 6" "$(( ($(stat -c '%a' "$V") / 10) % 10 )) $(( ($(stat -c '%a' "$V/%0") / 10) % 10 )) $(( ($(stat -c '%a' "$V/%1") / 10) % 10 ))"
    A0=$(wc -l < "$AUDIT")
    OUT=$(run_sd "SDSYS saves a master record: ED voc_master $A1*zzwitness" "ED voc_master $A1*zzwitness" "I" "X" "saved by sdsys from the master" "" "FI")
    sleep 1
    OUT2=$(run_user "$A1" "the user reads the record in its own VOC" "CT VOC zzwitness")
    ck_says "3e the user's own session finds the record in ITS VOC at once" "saved by sdsys from the master" "$OUT2"
    NEWAUD=$(tail -n +"$((A0 + 1))" "$AUDIT")
    ck_says "3f the audit trail has the line (lower case, account, file, id)" "master edit account=$A1 file=voc id=zzwitness" "$NEWAUD"
    ck "3g the file kept its owner and group: written in place by sdsys, not replaced" "$A1:sdu_$A1" "$(modes_of "$V/%0" | cut -d' ' -f1)"
    OUT3=$(run_sd "CHECK.MASTERS $A1" "CHECK.MASTERS $A1")
    ck_says "3h CHECK.MASTERS finds nothing to say about the account" "Every master copy matches its account" "$OUT3"
    ck_silent "3i ...and lists no file as nonwritable or norights" "nonwritable:" "$OUT3"
    # a user in an ORDINARY umask-077 session makes a dictionary: SD gives its group the write bit
    OUT4=$(run_user "$A1" "UMASK 077, then CREATE.FILE zzfile (a dictionary made under a closed umask)" "UMASK 077" "CREATE.FILE zzfile DYNAMIC")
    DM="$(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzfile.dic" 2>/dev/null) $(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzfile.dic/%0" 2>/dev/null) $(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzfile" 2>/dev/null)"
    ck "3j the dictionary made under UMASK 077 has its GROUP bits (2770, 660) and the data file next to it does not (700)" "2770 660 700" "$DM"
elif [ "$COMMIT" -eq 1 ]; then
    for r in "3b sdsys in the group" "3c owner and group" "3d modes" "3e the edit reaches the VOC" "3f audit line" "3g owner kept" "3h check" "3i no norights" "3j dictionary modes"; do not_reached "$r"; done
fi

# ==========================================================================
head2 "4. an SDSYS session that began BEFORE the account was made cannot write it"
if [ "$COMMIT" -eq 1 ] && [ "$CREATED1" -eq 1 ]; then
    FIFO="$WORK/sdsys.in"
    OUT_STALE="$WORK/stale.out"
    mkfifo "$FIFO"
    exec 3<>"$FIFO"
    # the long-lived SDSYS session: started now, before zwm2 exists, so its supplementary groups are the ones sdsys has TODAY
    sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1" < "$2"' sd-run "$SD" "$FIFO" > "$OUT_STALE" 2>&1 &
    STALE_PID=$!
    printf '\nTERM 200,9999\n' >&3
    sleep 4
    ck "4a (control) the long-lived session is running" "yes" "$(kill -0 "$STALE_PID" 2>/dev/null && echo yes || echo no)"
    say "  --- the account $A2 is made by ANOTHER session ---"
    OUT=$(run_sd "CREATE.ACCOUNT USER $A2 (answering the Linux password)" "CREATE.ACCOUNT USER $A2" "_PW_" "_PW_")
    if [ -e "$REGISTER/$A2" ]; then MADE_A2=1; fi
    ck "4b the register record of $A2 exists, and sdsys is in sdu_$A2 by /etc/group" "yes yes" "$(yesno_path "$REGISTER/$A2") $(has_member "sdu_$A2" sdsys)"
    if [ "$MADE_A2" -eq 1 ]; then
        : > "$WORK/stale.mark"
        printf '%s\n' "ED voc_master $A2*zzstale" "I" "X" "written by the old session" "" "FI" "CHECK.MASTERS $A2" >&3
        sleep 8
        STALE_TEXT=$(sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g' "$OUT_STALE")
        printf '%s\n' "$STALE_TEXT" | sed -e 's/^/      | /' >&2
        ck_says "4c the OLD session's save is refused and says why (11586: this session began before sdsys was put in the group)" "this session began before sdsys was put in group sdu_$A2" "$STALE_TEXT"
        OUT5=$(run_user "$A2" "the user looks for the record" "CT VOC zzstale")
        ck_silent "4d ...and the account's VOC has no such record: nothing was changed" "written by the old session" "$OUT5"
        ck_says "4e CHECK.MASTERS in the old session says norights, with the reason stale-session" "norights: $A2 voc stale-session" "$STALE_TEXT"
        printf '%s\n' "OFF" >&3
        sleep 2
        OUT6=$(run_sd "a NEW session: ED voc_master $A2*zznew" "ED voc_master $A2*zznew" "I" "X" "written by a new session" "" "FI")
        OUT7=$(run_user "$A2" "the user reads the record" "CT VOC zznew")
        ck_says "4f a NEW session of SDSYS (its groups read afresh) saves, and the record is in the user's VOC" "written by a new session" "$OUT7"
    else
        for r in "4c refused with 11586" "4d nothing changed" "4e norights stale-session" "4f a new session saves"; do not_reached "$r"; done
    fi
    exec 3>&-
elif [ "$COMMIT" -eq 1 ]; then
    for r in "4a" "4b" "4c" "4d" "4e" "4f"; do not_reached "$r (no account from section 3)"; done
else
    say "  (dry run: would start a long-lived SDSYS session, make $A2 by another session, and try a save in the first)"
fi

# ==========================================================================
head2 "5. the upgrade repairs the modes and the membership"
if [ "$COMMIT" -eq 1 ] && [ "$CREATED1" -eq 1 ]; then
    A="$ACCOUNTS_ROOT/$A1"
    # break it as an old install would have it: no group write on the VOC and the dictionary, and sdsys out of the group
    chmod 0755 "$A/voc" "$A/zzfile.dic" 2>/dev/null; chmod 0644 "$A/voc/%0" "$A/voc/%1" "$A/zzfile.dic/%0" "$A/zzfile.dic/%1" 2>/dev/null
    gpasswd -d sdsys "sdu_$A1" >/dev/null 2>&1
    ck "5a (control) broken: sdsys is out of sdu_$A1, and the VOC is 755 / 644" "no 755 644" "$(has_member "sdu_$A1" sdsys) $(stat -c '%a' "$A/voc") $(stat -c '%a' "$A/voc/%0")"
    OUT=$(run_sd "CHECK.MASTERS $A1 (a fresh session: sdsys is not in the group any more)" "CHECK.MASTERS $A1")
    ck_says "5b CHECK.MASTERS lists the VOC as nonwritable" "nonwritable: $A1 voc" "$OUT"
    ck_says "5c ...and the dictionary" "nonwritable: $A1 dict zzfile" "$OUT"
    ck_says "5d ...and says what it means (11593)" "cannot be written by SDSYS" "$OUT"
    # the installer's own function, on a register of ONE record, with the real sudo and the real sd-elevate
    mkdir -p "$WORK/reg"
    printf '%s\n\n%s\n' "$A" "sdu_$A1" > "$WORK/reg/$A1"
    FN=$(awk '/^join_sdsys_groups\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INSTALLER")
    if [ -z "$FN" ]; then not_reached "5e the installer's join_sdsys_groups (not found in $INSTALLER)"
    else
        OUT=$(bash -c 'set -euo pipefail; IFS=$'"'"'\n\t'"'"'; RED=; NC=; '"$FN"'; join_sdsys_groups "$1"' witness "$WORK/reg" 2>&1)
        printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
        ck_says "5e the installer's walk says it put sdsys in the group" "sdsys is now in the group sdu_$A1" "$OUT"
        ck_says "5f ...and made the modes right" "$A1: group-write: " "$OUT"
        ck_silent "5g ...with no WARNING" "WARNING" "$OUT"
        ck "5h sdsys is in the group again, and the VOC is group rwx / rw" "yes 2775 664" "$(has_member "sdu_$A1" sdsys) $(stat -c '%a' "$A/voc") $(stat -c '%a' "$A/voc/%0")"
        OUT=$(bash -c 'set -euo pipefail; IFS=$'"'"'\n\t'"'"'; RED=; NC=; '"$FN"'; join_sdsys_groups "$1"' witness "$WORK/reg" 2>&1)
        ck_says "5i run again it finds nothing to do" "it was in 1 already" "$OUT"
        ck_says "5j ...and the modes were right already" "1 were right already" "$OUT"
        OUT3=$(run_sd "CHECK.MASTERS $A1 (a NEW session, in the group)" "CHECK.MASTERS $A1")
        ck_says "5k CHECK.MASTERS is clean again" "Every master copy matches its account" "$OUT3"
    fi
elif [ "$COMMIT" -eq 1 ]; then
    for r in 5a 5b 5c 5d 5e 5f 5g 5h 5i 5j 5k; do not_reached "$r (no account from section 3)"; done
else
    say "  (dry run: would break the modes and the membership of $A1, run the installer's join_sdsys_groups on a one-record register with the real helper, and look)"
fi

# ==========================================================================
head2 "RESULT"
if [ "$COMMIT" -eq 1 ]; then
    say "  passed: $PASS   failed: $FAIL (of which not reached: $NOT_REACHED)"
    say "  log: $LOG"
    [ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER" "$LOG" 2>/dev/null
    [ "$FAIL" -eq 0 ] && exit 0 || exit 1
fi
say "  dry run: nothing was changed.  Run it for real:  sudo bash $SELF --commit"
exit 0
