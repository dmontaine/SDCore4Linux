#!/usr/bin/env bash
#
# witness-masters.sh - what only a ROOT run on a real install (or the VM) shows about MASTER TO ACCOUNT (S.67 stage 2, D7; owner 17 Oct 2026, warned) AS CHANGED BY F6
#                      (alternative C, 26 Oct 2026; the core direction: high security is delivered and the administrator loosens it later): the sdsys
#                      operating-system user is in NO user account's group as delivered; `modify.account <name> sdsys-on` puts it there (and sdsys-off takes it
#                      out); the modes of the VOC and dictionaries; an SDSYS edit reaching a user's VOC at once WHEN IT IS ON and refused (11976) when it is off;
#                      the refusal when the SDSYS session is older than the membership; the installer's one-time ruling for the accounts that had it.
#                      ***WRITTEN 26 Oct 26 AND NOT YET RUN.***  Its first run on the VM decides every expectation that says "first real run" below.
#
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-masters.sh               (a dry run: says what it would do, changes nothing)
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-masters.sh --commit      (does it)
#
# ***sudo IS NEEDED, AND ONLY FOR --commit.***  Run it from the owner's login (SUDO_USER must name a person).  The dry run needs no privilege.
# Exit 0 every row passed, 1 a row failed or was not reached, 2 it could not run.  The log is /tmp/witness-masters.<time>.log.
#
# WHY IT EXISTS.  The sandbox suite (sandbox-masters.py) has ONE operating-system user, so it cannot show who OWNS a file, which GROUP a session is in,
# or root changing files that belong to ANOTHER user.  Those are this script's.  What it adds to the sandbox's rows is exactly that and nothing else:
#
#   1  sdsys-join and sdsys-leave as the sdsys user through sudo (the way SD calls them): the sdsys user is put in the group of a throwaway user and in no
#      other, and taken out of it again (a group that does not list it is left alone); the refused calls (sdusers, a group account's group, root, sdsys itself)
#      leave /etc/group and /etc/gshadow byte for byte as they were; each of the two leaves a line in the system log (logger -t sd-elevate).
#   2  group-write as root on a tree that holds what the unit test cannot make: a file owned by ANOTHER user, a file of another group, a link to a file
#      and a link to a directory (/etc), a data file's directory.  Only the account's own are changed; /etc and /etc/hostname keep their modes; a second
#      run changes nothing; an account whose directory belongs to another group (the shared account's shape) is refused; it too leaves a line in the log.
#   3  CREATE.ACCOUNT USER <name> - SD's whole flow, and the DELIVERED SETTING: sdsys is NOT in the new group; an SDSYS save of a master record is REFUSED
#      (11976) and the VOC is unchanged; a dictionary made under a closed umask is NOT given group bits (C2); CHECK.MASTERS counts the account as off and lists
#      neither nonwritable nor norights for it.  Then `MODIFY.ACCOUNT <name> SDSYS-ON`: sdsys is in the group, the VOC is owner:group of the account with group
#      rwx (setgid on the directory) and rw on its subfiles, an SDSYS session saves a master record (ED on voc_master) and an ordinary session of the user finds
#      the record in its VOC AT ONCE; the audit lines (the edit and the modify.account) are in /usr/local/sdsys/audit; the file keeps its owner and group
#      (written in place); a dictionary made under a closed umask now IS given its group bits.
#   4  A SESSION OF SDSYS THAT BEGAN BEFORE THE MEMBERSHIP: a long-lived SDSYS session is started, a second account is made (off: the session's save is
#      refused with 11976), then switched on by ANOTHER session; the first session's next save is REFUSED with the stale-session message (11586) and changes
#      nothing; CHECK.MASTERS in it says norights stale-session; a NEW session saves.
#   5  The administrator's act and the installer's ruling: the account's modes are broken and CHECK.MASTERS says nonwritable, with the hint (11982); a second
#      SDSYS-ON repairs them and says so; the installer's own sdsys_groups_ruling (and its question), cut out of installsdcore.sh and run with the real sudo and
#      the real sd-elevate on the throwaway groups only, takes the sdsys user out with the answer n, leaves it with y, writes its marker, and with the marker
#      present does nothing, so a later SDSYS-ON stands; SDSYS-OFF takes it out again; a group account is refused (11979).  5.3: what is NOT lost when an
#      account is off (CREATE.ACCOUNT, SYNC.MASTERS, CHECK.MASTERS, LOGTO and a read, DELETE.ACCOUNT) and the one thing that is (a write by SDSYS inside the account).
#   5.4 The honest rows (the owner is to be told they pass): as the sdsys login the files root runs are the sdsys user's own (R-A), and sd-elevate would still
#      accept `sdsys-join` and a `chown-account sdsys sdusers` on the throwaway account (R-C, dry runs).  They PASS when the weaknesses are there: switching a
#      membership off removes the silent route into an account, it does not make a stolen sdsys login unable to reach it.
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
ck_nonempty() {   # ck_nonempty name text   - 26 Oct 26 (review of F6): the companion of every ck_silent on a SESSION's output: a session that printed nothing at all proves nothing
    local n; n=$(printf '%s' "$2" | tr -d '[:space:]' | wc -c)
    if [ "$n" -gt 20 ]; then PASS=$((PASS + 1)); say "  [PASS] $1: the session printed $n characters, so the silent row before it saw a real session"
    else FAIL=$((FAIL + 1)); say "  [FAIL] $1: the session printed $n characters: the silent row before it measured nothing"; fi
}
not_reached() { FAIL=$((FAIL + 1)); NOT_REACHED=$((NOT_REACHED + 1)); say "  [NOT REACHED] $1 - its precondition failed above, so it measured nothing"; }
yesno_user()  { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group() { getent group "$1" >/dev/null && echo yes || echo no; }
yesno_path()  { [ -e "$1" ] && echo yes || echo no; }
members_of()  { getent group "$1" | cut -d: -f4; }
has_member()  { case ",$(members_of "$1")," in *",$2,"*) echo yes ;; *) echo no ;; esac; }
modes_of()    { stat -c '%U:%G %a' -- "$1" 2>/dev/null || echo "(absent)"; }
sha_of()      { cat /etc/group /etc/gshadow 2>/dev/null | sha256sum | cut -d' ' -f1; }
sd_log()      { journalctl -t sd-elevate --no-pager -o cat -n 400 2>/dev/null || grep -h 'sd-elevate' /var/log/syslog /var/log/messages 2>/dev/null | tail -n 400; }   # what the helper wrote with logger -t sd-elevate

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
        # ONLY a record this run made (MADE_A1 / MADE_A2, set after the ground was found clear and the record was seen to appear).  A record that was there before is not ours: a run that
        # stopped at "CANNOT RUN - the ground is not clear" made nothing, and used to delete the very account it had refused to touch.
        MADE=$([ "$a" = "$A1" ] && echo "$MADE_A1" || echo "$MADE_A2")
        if [ "$MADE" -eq 1 ] && [ -e "$REGISTER/$a" ]; then
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
say "  sd   : $SD   helper: $ELEVATE   installer (for sdsys_groups_ruling): $INSTALLER"
say "  log  : $LOG"

head2 "0. preconditions and the ground being clear"
for p in "$SD" "$SDSYS" "$REGISTER" "$ACCOUNTS_ROOT" "$ELEVATE" "$AUDIT" "$SDSYS/voc_master" "$SDSYS/dict_master" "$SDSYS/master_state" "$INSTALLER"; do
    [ -e "$p" ] || { say "witness-masters: CANNOT RUN - $p does not exist (install a build with S.67 stage 2 first)"; exit 2; }
done
grep -q 'sdsys-join' "$ELEVATE" && grep -q 'sdsys-leave' "$ELEVATE" && grep -q 'group-write' "$ELEVATE" || { say "witness-masters: CANNOT RUN - the installed sd-elevate lacks sdsys-join, sdsys-leave or group-write (an install of an earlier build)"; exit 2; }
grep -q -i 'sdsys-on' "$SDSYS/gpl.bp/modifya" 2>/dev/null || { say "witness-masters: CANNOT RUN - the installed modify.account has no sdsys-on (an install of an earlier build)"; exit 2; }
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
head2 "1. sdsys-join and sdsys-leave, as the sdsys user through sudo (the way SD calls them)"
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
    # 26 Oct 26, F6: the other half.  sdsys is a member of sdu_$VU at this point (1b).
    OUT=$(as_sdsys_elevate sdsys-leave "sdu_$VU")
    ck_says "1h sdsys-leave sdu_$VU ran (exit 0)" "EXIT=0" "$OUT"
    ck_says "1h' ...and printed the command it ran: gpasswd -d sdsys, and no usermod" "gpasswd -d sdsys sdu_$VU" "$OUT"
    ck "1i sdsys is no longer a member of sdu_$VU, and ONLY that membership went: sdsys is still in sdusers" "no yes" "$(has_member "sdu_$VU" sdsys) $(has_member sdusers sdsys)"
    OUT=$(as_sdsys_elevate sdsys-leave "sdu_$VU")
    ck_says "1j run again: the group does not list sdsys, so it is left alone (exit 0, 'sdsys is not in')" "sdsys is not in sdu_$VU" "$OUT"
    ck_silent "1j' ...and no gpasswd command was run" "gpasswd -d" "$OUT"
    H1=$(sha_of)
    for g in sdusers sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdg_shared sdu_root sdu_sdsys sudo; do
        OUT=$(as_sdsys_elevate sdsys-leave "$g")
        ck_silent "1k sdsys-leave $g is refused (no gpasswd command printed)" "gpasswd -d" "$OUT"
        ck_silent "1k' ...and the exit status is not 0" "EXIT=0" "$OUT"
    done
    ck "1l after every refused call /etc/group and /etc/gshadow are byte for byte as before, and sdsys is still in sdusers" "$H1 yes" "$(sha_of) $(has_member sdusers sdsys)"
    LOGTXT=$(sd_log)
    ck_says "1m the system log has sd-elevate's line for the join (logger -t sd-elevate)" "sdsys-join: the user sdsys is now in sdu_$VU" "$LOGTXT"
    ck_says "1n ...and for the leave" "sdsys-leave: the user sdsys is no longer in sdu_$VU" "$LOGTXT"
    ck "1o ...the leave that had nothing to change (1j) wrote no line of its own: the line is there once" "1" "$(printf '%s\n' "$LOGTXT" | grep -cF "sdsys-leave: the user sdsys is no longer in sdu_$VU")"
else
    say "  (dry run: would useradd $VU and groupadd sdu_$VU through the helper, run sdsys-join and sdsys-leave as the sdsys user, try nine refusals of each, and read the system log)"
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
    ck_says "2i' the system log has group-write's line (logger -t sd-elevate; it was written by each run that succeeded)" "group-write: the VOC and dictionaries of $T are group-writable for sdu_$VU" "$(sd_log)"
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
head2 "3. CREATE.ACCOUNT USER $A1 - SD's whole flow, the delivered setting (off), then SDSYS-ON and an SDSYS edit that reaches the user's VOC at once"
OUT=$(run_sd "CREATE.ACCOUNT USER $A1 (answering the Linux password)" "CREATE.ACCOUNT USER $A1" "_PW_" "_PW_")
CREATED1=0
if [ "$COMMIT" -eq 1 ]; then
    ck "3a (the gate) the register record exists" "yes" "$(yesno_path "$REGISTER/$A1")"
    if [ -e "$REGISTER/$A1" ]; then CREATED1=1; MADE_A1=1; fi
fi
if [ "$COMMIT" -eq 1 ] && [ "$CREATED1" -eq 1 ]; then
    # 26 Oct 26, F6: the delivered setting.  CREATE.ACCOUNT made the group with root and the user only.
    ck "3b sdsys is NOT a member of sdu_$A1 (F6: the group was made with root and the user; the join of 19 Oct is gone) and the group lists exactly root and $A1" "no root,$A1" "$(has_member "sdu_$A1" sdsys) $(members_of "sdu_$A1")"
    V="$ACCOUNTS_ROOT/$A1/voc"
    ck "3c the VOC belongs to the account's user and group" "$A1:sdu_$A1 $A1:sdu_$A1" "$(modes_of "$V" | cut -d' ' -f1) $(modes_of "$V/%0" | cut -d' ' -f1)"
    # first real run decides: with C2 nothing forces the group bits now, so these are what the session's umask 002 made (775 / 664)
    ck "3d ...with group rwx on the directory and group rw on %0 and %1 (the sign-on umask 002 gives it; nothing forces it while the account is off)" "7 6 6" "$(( ($(stat -c '%a' "$V") / 10) % 10 )) $(( ($(stat -c '%a' "$V/%0") / 10) % 10 )) $(( ($(stat -c '%a' "$V/%1") / 10) % 10 ))"
    OUT=$(run_sd "SDSYS saves a master record while the account is OFF: ED voc_master $A1*zzoff" "ED voc_master $A1*zzoff" "I" "X" "written while off" "" "FI" "EX" "Y")
    ck_says "3d1 the save is REFUSED and says why (11976: sdsys is not in the group of the account)" "sdsys is not in the group of $A1" "$OUT"
    ck_says "3d2 ...and names the verb that switches it on" "modify.account $A1 sdsys-on" "$OUT"
    OUT2=$(run_user "$A1" "the user looks for the record" "CT VOC zzoff")
    ck_silent "3d3 ...and the account's VOC has no such record: nothing was changed" "written while off" "$OUT2"
    ck_nonempty "3d3a ...(the user's session ran and answered)" "$OUT2"
    OUT3=$(run_sd "CHECK.MASTERS $A1 (the account is off)" "CHECK.MASTERS $A1")
    ck_says "3d4 CHECK.MASTERS counts the accounts that are off, in a line of its own (11981)" "Master edits are switched off for" "$OUT3"
    ck_silent "3d5 ...and lists no file of $A1 as nonwritable" "nonwritable: $A1" "$OUT3"
    ck_silent "3d5' ...nor as norights" "norights: $A1" "$OUT3"
    OUT4=$(run_user "$A1" "UMASK 077, then CREATE.FILE zzoffd (a dictionary made under a closed umask while the account is off)" "UMASK 077" "CREATE.FILE zzoffd DYNAMIC")
    DMO="$(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzoffd.dic" 2>/dev/null) $(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzoffd.dic/%0" 2>/dev/null)"
    # first real run decides the exact modes: a directory made under 077 inside a setgid directory is 2700, its %0 is 600
    ck "3d6 (C2) a dictionary made under UMASK 077 while the account is off is NOT given group bits (2700, 600)" "2700 600" "$DMO"
    # the administrator's act
    A0=$(wc -l < "$AUDIT")
    OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-ON" "MODIFY.ACCOUNT $A1 SDSYS-ON")
    ck_says "3d7 MODIFY.ACCOUNT SDSYS-ON says master edits are on, and to sign on again as SDSYS" "Account $A1: master edits are on" "$OUT"
    ck_says "3d7' ...and tells a running session it does not have it" "a session already running does not have it" "$OUT"
    ck "3d8 sdsys is a member of sdu_$A1 now (put in by sd-elevate sdsys-join, by the administrator's act)" "yes" "$(has_member "sdu_$A1" sdsys)"
    ck "3d9 ...the VOC is group rwx / rw (sd-elevate group-write ran too)" "2775 664 664" "$(stat -c '%a' "$V") $(stat -c '%a' "$V/%0") $(stat -c '%a' "$V/%1")"
    OUT=$(run_sd "SDSYS saves a master record: ED voc_master $A1*zzwitness" "ED voc_master $A1*zzwitness" "I" "X" "saved by sdsys from the master" "" "FI")
    sleep 1
    OUT2=$(run_user "$A1" "the user reads the record in its own VOC" "CT VOC zzwitness")
    ck_says "3e the user's own session finds the record in ITS VOC at once" "saved by sdsys from the master" "$OUT2"
    NEWAUD=$(tail -n +"$((A0 + 1))" "$AUDIT")
    ck_says "3f the audit trail has the line (lower case, account, file, id)" "master edit account=$A1 file=voc id=zzwitness" "$NEWAUD"
    ck_says "3f' ...and the administrator's act (lower case: the word sdsys-on is vocabulary of the audit trail)" "modify.account sdsys-on account=$A1" "$NEWAUD"
    ck "3g the file kept its owner and group: written in place by sdsys, not replaced" "$A1:sdu_$A1" "$(modes_of "$V/%0" | cut -d' ' -f1)"
    OUT3=$(run_sd "CHECK.MASTERS $A1" "CHECK.MASTERS $A1")
    ck_says "3h CHECK.MASTERS finds nothing to say about the account" "Every master copy matches its account" "$OUT3"
    ck_silent "3i ...and lists no file as nonwritable or norights" "nonwritable:" "$OUT3"
    # a user in an ORDINARY umask-077 session makes a dictionary: SD gives its group the write bit
    OUT4=$(run_user "$A1" "UMASK 077, then CREATE.FILE zzfile (a dictionary made under a closed umask)" "UMASK 077" "CREATE.FILE zzfile DYNAMIC")
    DM="$(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzfile.dic" 2>/dev/null) $(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzfile.dic/%0" 2>/dev/null) $(stat -c '%a' "$ACCOUNTS_ROOT/$A1/zzfile" 2>/dev/null)"
    # 19 Oct 26: the expected data directory is 2700, not 700: the account's directory is setgid, a directory made under it inherits the bit (the first real run said 2700),
    # and what the row is about - no GROUP read, write or search bit - holds either way.
    ck "3j the dictionary made under UMASK 077 has its GROUP bits (2770, 660) now that the account is ON (C2) and the data file's directory next to it does not (2700: owner only, with the setgid bit it inherits)" "2770 660 2700" "$DM"
elif [ "$COMMIT" -eq 1 ]; then
    for r in "3b sdsys not in the group" "3c owner and group" "3d modes" "3d1 off: refused" "3d4 off count" "3d6 off: modes not forced" "3d7 sdsys-on" "3d8 membership" "3e the edit reaches the VOC" "3f audit line" "3g owner kept" "3h check" "3i no norights" "3j dictionary modes"; do not_reached "$r"; done
fi

# ==========================================================================
head2 "4. an SDSYS session that began BEFORE the membership: refused while the account is off (11976), refused as stale once ANOTHER session switched it on (11586)"
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
    ck "4b the register record of $A2 exists, and sdsys is NOT in sdu_$A2 by /etc/group (F6: delivered off)" "yes no" "$(yesno_path "$REGISTER/$A2") $(has_member "sdu_$A2" sdsys)"
    if [ "$MADE_A2" -eq 1 ]; then
        : > "$WORK/stale.mark"
        # 26 Oct 26, F6: first the account is OFF.  The long-lived session's save is refused with 11976, whatever its groups.
        printf '%s\n' "ED voc_master $A2*zzoff" "I" "X" "written while off" "" "FI" "EX" "Y" >&3
        sleep 6
        OFF_TEXT=$(sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g' "$OUT_STALE")
        printf '%s\n' "$OFF_TEXT" | sed -e 's/^/      | /' >&2
        ck_says "4b1 the OLD session's save while the account is off is refused, and says why (11976)" "sdsys is not in the group of $A2" "$OFF_TEXT"
        OUT5=$(run_user "$A2" "the user looks for the record written while off" "CT VOC zzoff")
        ck_silent "4b2 ...and the account's VOC has no such record" "written while off" "$OUT5"
        ck_nonempty "4b2a ...(the user's session ran and answered)" "$OUT5"
        # now ANOTHER session switches it on: the old session's groups were fixed when it started, so it is STALE
        OUT=$(run_sd "MODIFY.ACCOUNT $A2 SDSYS-ON (another session, while the first is still open)" "MODIFY.ACCOUNT $A2 SDSYS-ON")
        ck "4b3 sdsys is in sdu_$A2 by /etc/group now" "yes" "$(has_member "sdu_$A2" sdsys)"
        # 19 Oct 26: after the refused FI the editor is STILL OPEN with the record changed (the first real run typed CHECK.MASTERS into ED: "Invalid string delimiter").
        # EX asks "Record changed - OK to quit?" and Y answers it; only then is the next line a TCL command.
        printf '%s\n' "ED voc_master $A2*zzstale" "I" "X" "written by the old session" "" "FI" "EX" "Y" "CHECK.MASTERS $A2" >&3
        sleep 8
        STALE_TEXT=$(sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g' "$OUT_STALE")
        printf '%s\n' "$STALE_TEXT" | sed -e 's/^/      | /' >&2
        # 19 Oct 26: message 11586 says "joined group" (the verifier round reworded it); the script still had the first draft's "was put in group".
        ck_says "4c the OLD session's save is refused and says why (11586: this session began before sdsys joined the group)" "this session began before sdsys joined group sdu_$A2" "$STALE_TEXT"
        OUT5=$(run_user "$A2" "the user looks for the record" "CT VOC zzstale")
        ck_silent "4d ...and the account's VOC has no such record: nothing was changed" "written by the old session" "$OUT5"
        ck_nonempty "4d1 ...(the user's session ran and answered)" "$OUT5"
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
head2 "5. a broken mode is repaired by a second SDSYS-ON; the installer's ruling; SDSYS-OFF; what is not lost when an account is off; the honest rows"
if [ "$COMMIT" -eq 1 ] && [ "$CREATED1" -eq 1 ]; then
    A="$ACCOUNTS_ROOT/$A1"
    # break the modes as an old install would have them: no group write on the VOC and the dictionary.  The account is ON (section 3), so CHECK.MASTERS says so.
    chmod 0755 "$A/voc" "$A/zzfile.dic" 2>/dev/null; chmod 0644 "$A/voc/%0" "$A/voc/%1" "$A/zzfile.dic/%0" "$A/zzfile.dic/%1" 2>/dev/null
    # 19 Oct 26: chmod 0755 on a setgid directory keeps the setgid bit (GNU chmod), so stat says 2755 (the first real run), as 5f below says 2775 after the repair.
    ck "5a (control) broken: sdsys is in sdu_$A1 (it is on), and the VOC is 755 (setgid kept: 2755) / 644" "yes 2755 644" "$(has_member "sdu_$A1" sdsys) $(stat -c '%a' "$A/voc") $(stat -c '%a' "$A/voc/%0")"
    OUT=$(run_sd "CHECK.MASTERS $A1 (a fresh session: the account is on and its modes are broken)" "CHECK.MASTERS $A1")
    ck_says "5b CHECK.MASTERS lists the VOC as nonwritable" "nonwritable: $A1 voc" "$OUT"
    ck_says "5c ...and the dictionary" "nonwritable: $A1 dict zzfile" "$OUT"
    ck_says "5d ...and says what it means, and which verb puts it right (11982)" "modify.account <account> sdsys-on puts it right" "$OUT"
    OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-ON (a second time: it repairs the modes and changes nothing else)" "MODIFY.ACCOUNT $A1 SDSYS-ON")
    ck_says "5e the second SDSYS-ON says master edits are on" "Account $A1: master edits are on" "$OUT"
    ck "5f ...and the VOC is group rwx / rw again, sdsys still in the group" "yes 2775 664" "$(has_member "sdu_$A1" sdsys) $(stat -c '%a' "$A/voc") $(stat -c '%a' "$A/voc/%0")"
    OUT3=$(run_sd "CHECK.MASTERS $A1 (a NEW session)" "CHECK.MASTERS $A1")
    ck_says "5g CHECK.MASTERS is clean again" "Every master copy matches its account" "$OUT3"
    ck_silent "5g' ...and lists no file of $A1 as nonwritable" "nonwritable: $A1" "$OUT3"

    # ---- the installer's ruling, on the throwaway groups ONLY: the question and the act are cut out of the installer and run with the real sudo and the real sd-elevate;
    # ---- `getent group` (the listing) is narrowed to the groups this run made so that no real account is touched, and the marker is a scratch file, not /home/sd's.
    RULING_ASK=$(awk '/^# SDSYSGROUPS-ASK-BEGIN$/{f=1;next} /^# SDSYSGROUPS-ASK-END$/{f=0} f{print}' "$INSTALLER" | sed -e "s#/home/sd/#$WORK/ruling/#g")
    RULING_FN=$(awk '/^sdsys_groups_ruling\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INSTALLER")
    RULING_MARKER="$WORK/ruling/\$groups.ruled"
    mkdir -p "$WORK/ruling"
    ruling_run() {   # ruling_run ANSWER  - the installer's question (the answer on its input) and then its act, as root, on sdu_zwm1 and sdu_zwm2 only
        printf '%s\n' "$1" | RULING_ASK="$RULING_ASK" RULING_FN="$RULING_FN" MARKER="$RULING_MARKER" bash -c '
            set -euo pipefail
            IFS=$'"'"'\n\t'"'"'
            RED=; NC=
            getent() { if [ "${1:-}" = group ] && [ -z "${2:-}" ]; then command getent group | grep -E "^sdu_(zwm1|zwm2|zwmv):" || true; else command getent "$@"; fi; }
            eval "$RULING_ASK"
            eval "$RULING_FN"
            sdsys_groups_ruling "$MARKER" "$sdsys_keep"
            echo "KEEP=$sdsys_keep"' 2>&1
    }
    if [ -z "$RULING_ASK" ] || [ -z "$RULING_FN" ]; then
        for r in 5h 5i 5j 5k 5l 5m 5n; do not_reached "$r (the installer's SDSYSGROUPS-ASK block or sdsys_groups_ruling not found in $INSTALLER)"; done
    else
        REAL_MARKER_BEFORE=$(yesno_path "/home/sd/\$groups.ruled")
        OUT=$(ruling_run n)
        printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
        ck_says "5h the question was reached and the answer n read (the account(s) with the sdsys user in the group were counted)" "KEEP=n" "$OUT"
        ck_says "5i the act took the sdsys user out of the group of $A1" "the sdsys user is no longer in the group sdu_$A1" "$OUT"
        OTHERS_OK=yes
        [ "$(has_member sdusers sdsys)" = yes ] || OTHERS_OK=no
        if [ -d /home/sd/group_accounts/shared ] && [ "$(has_member sdg_shared sdsys)" != yes ]; then OTHERS_OK=no; fi
        ck "5j ...really: /etc/group no longer lists sdsys in sdu_$A1 (nor in sdu_$A2 where it was switched on); sdusers and the shared account's group still do" "no no yes" "$(has_member "sdu_$A1" sdsys) $(has_member "sdu_$A2" sdsys) $OTHERS_OK"
        ck "5k the scratch marker was written: sdsys:sdusers 644; the REAL marker in /home/sd is as it was (this run did not touch it)" "sdsys:sdusers 644 $REAL_MARKER_BEFORE" "$(stat -c '%U:%G %a' "$RULING_MARKER" 2>/dev/null) $(yesno_path "/home/sd/\$groups.ruled")"
        # the administrator switches it on afterwards; the next install, with the marker there, must leave it alone
        OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-ON (after the ruling)" "MODIFY.ACCOUNT $A1 SDSYS-ON")
        ck "5l after the ruling an administrator's SDSYS-ON puts the user in the group of $A1 again" "yes" "$(has_member "sdu_$A1" sdsys)"
        OUT=$(ruling_run n)
        printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
        ck_says "5m an install again, answer n, marker present: nothing is asked and it says the ruling was made earlier" "ruled on at an earlier install" "$OUT"
        ck "5n ...and the administrator's SDSYS-ON STANDS: sdsys is still in the group of $A1" "yes" "$(has_member "sdu_$A1" sdsys)"
        rm -f -- "$RULING_MARKER"
        OUT=$(ruling_run y)
        printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
        ck_says "5o with the answer y (marker absent again) the sdsys user is kept in the group: the question read y" "KEEP=y" "$OUT"
        ck "5p ...and nothing changed: sdsys is still in the group of $A1, and the marker was written" "yes yes" "$(has_member "sdu_$A1" sdsys) $(yesno_path "$RULING_MARKER")"
    fi

    # ---- SDSYS-OFF, the refusal for a group account, and 5.3 what is not lost when an account is off
    A0=$(wc -l < "$AUDIT")
    OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-OFF" "MODIFY.ACCOUNT $A1 SDSYS-OFF")
    ck_says "5q SDSYS-OFF says master edits are off" "Account $A1: master edits are off" "$OUT"
    ck "5r ...and sdsys is out of sdu_$A1 (and still in sdusers)" "no yes" "$(has_member "sdu_$A1" sdsys) $(has_member sdusers sdsys)"
    ck_says "5s the audit trail has the line (lower case)" "modify.account sdsys-off account=$A1" "$(tail -n +"$((A0 + 1))" "$AUDIT")"
    OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-OFF (again)" "MODIFY.ACCOUNT $A1 SDSYS-OFF")
    ck_says "5t run again it says it already had that access and changes nothing" "already had that access" "$OUT"
    OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-ON SDSYS-OFF (the two words conflict with each other, and with nothing else)" "MODIFY.ACCOUNT $A1 SDSYS-ON SDSYS-OFF")
    ck_says "5u both words in one command are refused (11791: they set the same access to different states)" "sdsys-on and sdsys-off set the same access" "$OUT"
    ck "5u' ...and nothing was changed" "no" "$(has_member "sdu_$A1" sdsys)"
    if [ -d /home/sd/group_accounts/shared ]; then
        H2=$(sha_of)
        OUT=$(run_sd "MODIFY.ACCOUNT shared SDSYS-ON (a group account)" "MODIFY.ACCOUNT shared SDSYS-ON")
        ck_says "5v a group account is refused (11979)" "is not a user account" "$OUT"
        ck "5v' ...and /etc/group and /etc/gshadow are byte for byte as before" "$H2" "$(sha_of)"
    else
        say "  (no shared account here: 5v is left out - it needs a group account)"
    fi
    # 5.3: the account is OFF now.  Everything an administrator does that does not write INTO the account still works.
    OUT=$(run_sd "SYNC.MASTERS $A1 (the account is off)" "SYNC.MASTERS $A1")
    OUT3=$(run_sd "CHECK.MASTERS $A1 (the account is off)" "CHECK.MASTERS $A1")
    ck_says "5.3a SYNC.MASTERS and CHECK.MASTERS of an account that is off work: the copies match" "Every master copy matches its account" "$OUT3"
    ck_says "5.3b ...and the off account is counted, not listed as a difference" "Master edits are switched off for" "$OUT3"
    OUT=$(run_sd "LOGTO $A1, then a READ in the account, then a WRITE (CREATE.FILE zzcollat)" "LOGTO $A1" "CT VOC LOGTO" "CREATE.FILE zzcollat DYNAMIC")
    ck_silent "5.3c LOGTO into an account that is off and a read of its VOC raise no 'not a member' or 'not authorized' complaint (first real run decides the wording)" "not authorized" "$OUT"
    ck_nonempty "5.3c1 ...(the SDSYS session ran, entered the account and answered)" "$OUT"
    # A FALSIFICATION ROW (design fact 1, read from the modes and never measured): if this file appears, SDSYS could write inside an account without being in its group
    ck "5.3d (falsification) the WRITE inside the account by SDSYS is the one thing that is lost: zzcollat was NOT made while the account is off" "no" "$(yesno_path "$A/zzcollat")"
    OUT=$(run_sd "MODIFY.ACCOUNT $A1 SDSYS-ON (a new session follows, so that its groups include the account's)" "MODIFY.ACCOUNT $A1 SDSYS-ON")
    OUT=$(run_sd "LOGTO $A1 and CREATE.FILE zzcollat (the account is on)" "LOGTO $A1" "CREATE.FILE zzcollat DYNAMIC")
    ck "5.3e ...and with the account on (a new session) it is made" "yes" "$(yesno_path "$A/zzcollat")"
    if [ "$MADE_A2" -eq 1 ] && [ -e "$REGISTER/$A2" ]; then
        OUT=$(run_sd "DELETE.ACCOUNT $A2 (the account is off after the ruling)" "DELETE.ACCOUNT $A2" "y")
        ck "5.3f DELETE.ACCOUNT of an account that is off works: the register record is gone" "no" "$(yesno_path "$REGISTER/$A2")"
    else
        not_reached "5.3f DELETE.ACCOUNT of an account that is off (no $A2 from section 4)"
    fi

    # ---- 5.4 the honest rows.  They PASS when the weaknesses of design section 0 are there; they are not claims about SD, they are measurements the owner was promised.
    ck "R-A1 the files root runs are the sdsys user's own: bin/sd and bin/sdlnxd belong to sdsys (a stolen sdsys login can replace them; root runs them at the next start)" "sdsys sdsys" "$(stat -c %U "$SDSYS/bin/sd") $(stat -c %U "$SDSYS/bin/sdlnxd")"
    ck "R-A2 ...and neither unit that starts them names a User= (they run as root)" "0" "$(systemctl cat sd.service sd-lnxd.service 2>/dev/null | grep -c '^User=')"
    ck "R-A2a ...(both units were really read: at least two ExecStart= lines came back, so the 0 above is not an empty read)" "yes" "$([ "$(systemctl cat sd.service sd-lnxd.service 2>/dev/null | grep -c '^ExecStart=')" -ge 2 ] && echo yes || echo no)"
    OUT=$(as_sdsys_elevate --dry-run sdsys-join "sdu_$A1")
    ck_says "R-C1 the sdsys login may still run sd-elevate sdsys-join for an account (a dry run): the switch is not a wall" "usermod -aG sdu_$A1 -- sdsys" "$OUT"
    OUT=$(as_sdsys_elevate --dry-run chown-account sdsys sdusers "$A/voc/%0")
    ck_says "R-C2 ...and chown-account sdsys sdusers on a throwaway account's VOC file (a dry run) is accepted too" "chown -- sdsys:sdusers" "$OUT"
    ck_says "R-C2' ...exit 0" "EXIT=0" "$OUT"
elif [ "$COMMIT" -eq 1 ]; then
    for r in 5a 5b 5c 5d 5e 5f 5g 5h 5i 5j 5k 5l 5m 5n 5o 5p 5q 5r 5s 5t 5u 5.3a 5.3b 5.3c 5.3d 5.3e 5.3f R-A1 R-A2 R-C1 R-C2; do not_reached "$r (no account from section 3)"; done
else
    say "  (dry run: would break the modes of $A1, repair them with a second SDSYS-ON, run the installer's question and sdsys_groups_ruling with the real helper on the throwaway groups only (answers n and y, marker present and absent), try SDSYS-OFF and a group account, do what an administrator does with an account that is off, and measure the weaknesses R-A and R-C)"
fi

# ==========================================================================
head2 "6. the master files are the sdsys user's alone (verifier F1, 19 Oct 26): no group bit, no other bit, and a user who IS in sdusers cannot open them"
if [ "$COMMIT" -eq 1 ]; then
    # the owner, group and mode of what the install made (the sandbox has one user, so only here can the owner and the group be seen)
    LIST=""
    for f in voc_master dict_master master_state; do
        for p in "$SDSYS/$f" "$SDSYS/$f/%0" "$SDSYS/$f/%1" "$SDSYS/$f.dic" "$SDSYS/$f.dic/%0" "$SDSYS/$f.dic/%1"; do
            say "      $(stat -c '%U:%G %a  %n' -- "$p" 2>&1)"
            LIST="$LIST$(stat -c '%U %a' -- "$p" 2>/dev/null)
"
        done
    done
    OWNERS=$(printf '%s' "$LIST" | awk 'NF{print $1}' | sort -u | tr '\n' ' ')
    ck "6a master files: owner, group and mode - every one of the 18 paths is owned by sdsys" "sdsys " "$OWNERS"
    DIRS=$(printf '%s' "$LIST" | awk 'NF{print $2}' | sort | uniq -c | awk '{printf "%s x%s ", $2, $1}')
    ck "6b ...the six directories are 700 and the twelve subfiles 600" "600 x12 700 x6 " "$DIRS"
    LOOSE=0
    while read -r own mode; do [ -n "$mode" ] && [ $((8#$mode & 8#077)) -ne 0 ] && LOOSE=$((LOOSE + 1)); done <<< "$LIST"
    ck "6c ...and not one of them has a group or other bit set (no group or other bit: the group SDSYS runs in is sdusers, which every SD user is in)" "0" "$LOOSE"
    ck "6d the journal is sdsys:sdusers 620 (every SD user's session appends to it, nobody but sdsys reads it)" "sdsys:sdusers 620" "$(stat -c '%U:%G %a' -- "$SDSYS/\$master.journal" 2>&1)"
    if [ "$MADE_A1" -eq 1 ] && [ "$(has_member sdusers "$A1")" = yes ]; then
        R1=$(sudo -u "$A1" sh -c 'cat "$1" >/dev/null 2>&1 && echo OPENED || echo DENIED' sh "$SDSYS/voc_master/%0")
        R2=$(sudo -u "$A1" sh -c 'ls "$1" >/dev/null 2>&1 && echo LISTED || echo DENIED' sh "$SDSYS/voc_master")
        R3=$(sudo -u "$A1" sh -c 'cat "$1" >/dev/null 2>&1 && echo OPENED || echo DENIED' sh "$SDSYS/dict_master.dic/%0")
        ck "6e $A1 is in sdusers, which every SD user is: it cannot read voc_master's subfile, list its directory or read dict_master's dictionary (the group these files used to have gave it all three)" \
           "DENIED DENIED DENIED" "$R1 $R2 $R3"
    else
        not_reached "6e a member of sdusers cannot open the master files (needs $A1 from section 3 in sdusers)"
    fi
else
    say "  (dry run: would stat the 18 paths of the three master files, their dictionaries and subfiles and the journal, require sdsys as the owner, 700 / 600 and no group or other bit, and try to open them as a member of sdusers)"
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
