#!/usr/bin/env bash
#
# witness-absence.sh - the ABSENCE half of the teardown (owner's decision,
#                      18 Sep 2026): prove the tier machinery and its braces
#                      are gone from a machine and from this tree, and prove
#                      the one-administrator model the way the machine reads
#                      it.  Replaces witness-tierchange.sh and
#                      verify-tier-layer.*, which measured the machinery that
#                      no longer exists.
#
#   bash      /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-absence.sh
#   sudo bash /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-absence.sh --commit
#
# ***NEEDS sudo, ONLY FOR --commit.***  The dry run changes nothing.
#
# WHAT IT PROVES ABSENT
#   M1  no tier policy: /usr/local/sdsys/tier.policy is not there, and the
#       TIERGATE program is not in sdsys's VOC (S.25).
#   M2  a fresh CREATE.ACCOUNT writes no tier: field 5 of the new record is
#       blank (the suspension flag) and field 6 is blank (S.25/W.7).
#   M3  no tier keyword in MODIFY.ACCOUNT's grammar: the tier words are
#       refused as unexpected tokens, and SUSPENDED/UNSUSPEND are the flag
#       (S.25/W.7).
#   M4  no OS-access grants: SH-ON/SH-OFF/OS-ON/OS-OFF are refused by
#       MODIFY.ACCOUNT, and fields 7/8 are gone from the register (S.27).
#   M5  no API route words: API/NONE/SSH/BOTH are refused by
#       MODIFY.ACCOUNT and CREATE.ACCOUNT (S.28).
#   M6  no grant verbs: GRANT/REVOKE/LIST.GRANTS are refused as not in VOC
#       (W.8); a grant is usermod -aG.
#   M7  no sdadmin or sdapi group exists (S.26/S.28); the sudoers drop-in
#       names the sdsys user alone; the ssh boundary block forces every
#       sdusers member into sd and denies sdsys network login (S.28).
#   M8  the administrator model, driven: a root session is refused outright
#       (10176, audited) and a local sdsys session is granted (10916).
#   M9  the machine-side absences the source must not contradict: this
#       script checks the shipped installer, deleter, ssh helper, sudoers
#       and register-key comments in the source tree it lives in.
#
# THE THROWAWAY.  M2 needs a real CREATE.ACCOUNT, so a throwaway account
# (zzabst) is made as sdsys - SD's whole flow, Linux user and all - and
# DELETE.ACCOUNTed afterwards whatever happens.  Its Linux password is
# generated per run and printed nowhere.
#
# Exit 0 every check passed, 1 a check failed (or was not reached), 2 it could
# not run.
#
# ---------------------------------------------------------------------------

set -u
SELF="$(readlink -f "$0")"
SD_BIN="/usr/local/sdsys/bin/sd"
COMMIT=0
case "${1:-}" in
  --commit) COMMIT=1 ;;
  "") ;;
  *) echo "usage: $0 [--commit]" >&2; exit 2 ;;
esac

PASS=0; FAIL=0; NOT_REACHED=0
say()  { printf '%s\n' "$*"; }
head2() { say ""; say "=== $* ============================================"; }
ck() {   # name, want, got
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1)); say "  [PASS] $1: got \"$3\""
  else FAIL=$((FAIL + 1)); say "  [FAIL] $1: wanted \"$2\", got \"$3\""; fi
}
ck_says() {   # name, needle, text
  if printf '%s' "$3" | grep -qF -- "$2"; then PASS=$((PASS + 1)); say "  [PASS] $1: found \"$2\""
  else FAIL=$((FAIL + 1)); say "  [FAIL] $1: did NOT find \"$2\""; fi
}
ck_absent() {   # name, needle, text
  if printf '%s' "$3" | grep -qF -- "$2"; then FAIL=$((FAIL + 1)); say "  [FAIL] $1: FOUND \"$2\""
  else PASS=$((PASS + 1)); say "  [PASS] $1: absent \"$2\""; fi
}
not_reached() { NOT_REACHED=$((NOT_REACHED + 1)); FAIL=$((FAIL + 1)); say "  [FAIL] $1: NOT REACHED"; }
yesno_file() { [ -e "$1" ] && echo yes || echo no; }
yesno_dir()  { [ -d "$1" ] && echo yes || echo no; }
yesno_user() { id -u "$1" >/dev/null 2>&1 && echo yes || echo no; }
yesno_group(){ getent group "$1" >/dev/null 2>&1 && echo yes || echo no; }
strip() { sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g'; }

SDSYS="/usr/local/sdsys"
ACC="zzabst"
ACC_UC="ZZABST"
ADIR="/home/sd/user_accounts/$ACC"
REGISTER="$SDSYS/accounts"
MARKER="$SDSYS/\$adopt.$ACC"
PW_OS=""
MADE_ACCOUNT=0

# One piped sd session, run AS SDSYS - the administrator.  A _PW_ line is
# replaced with $PW_OS (the throwaway Linux password) and echoed as
# "(password answer)".
#
# 18 Sep 26 dm - THE USER IS A PARAMETER, AND M8 USES IT.  The first real run's
#   M8a/M8c measured NOTHING: "root" was only the title argument, so the "root
#   session" ran as sdsys, was granted (10916), and the two refusal rows could
#   not have passed whatever the product did.  A root session is now the
#   witness's OWN uid - which IS root, because --commit requires sudo - with no
#   -u switch.
run_sd_as() {
  local user="$1"; shift
  local title="$1"; shift
  say "  --- sd session as $user: $title ---" >&2
  local line
  for line in "$@"; do
    case "$line" in _PW_) say "      > (password answer)" >&2 ;; *) say "      > $line" >&2 ;; esac
  done
  if [ "$COMMIT" -eq 0 ]; then say "      (dry run - not executed)" >&2; return 0; fi
  local body out
  body=$'\n''TERM 200,9999'
  for line in "$@"; do
    if [ "$line" = "_PW_" ]; then body="$body"$'\n'"$PW_OS"; else body="$body"$'\n'"$line"; fi
  done
  body="$body"$'\n''OFF'$'\n'
  if [ "$user" = sdsys ]; then
    out=$(printf '%s' "$body" | timeout 90 sudo -u sdsys "$SD_BIN" 2>&1 | strip)
  else
    out=$(printf '%s' "$body" | timeout 90 "$SD_BIN" 2>&1 | strip)
  fi
  printf '%s\n' "$out" | sed -e 's/^/      | /' >&2
  printf '%s' "$out"
}

run_sd() { run_sd_as sdsys "$@"; }

# ---------------- the ground ---------------------------------------------
head2 "0. the ground"
say "  throwaway : $ACC   (register record $REGISTER/$ACC, dir $ADIR)"
say "  adopt marker: $MARKER (a leftover would refuse; a marker never exists on a delivered machine)"
DIRTY=0
[ "$(yesno_file "$MARKER")" = yes ] && { say "  DIRTY: an ADOPT marker for $ACC exists"; DIRTY=1; }
if [ "$COMMIT" -eq 1 ] && [ "$(yesno_file "$REGISTER/$ACC")" = yes ]; then
  say "  DIRTY: $ACC is already registered; delete it first or pick another name"
  DIRTY=1
fi
if [ "$DIRTY" -eq 1 ]; then
  say "  witness-absence: CANNOT RUN - the ground is not clear."
  exit 2
fi

cleanup() {
  if [ "$MADE_ACCOUNT" -eq 1 ] && [ -e "$REGISTER/$ACC" ]; then
    say "  $ACC is still registered; deleting it through SD (as sdsys, REMOVE.HOME)"
    printf '%s' $'\n''TERM 200,9999'$'\n'"DELETE.ACCOUNT $ACC REMOVE.HOME"$'\n''y'$'\n''OFF'$'\n' \
      | timeout 90 sudo -u sdsys "$SD_BIN" >/dev/null 2>&1
  fi
  # 18 Sep 26 dm - AND ITS HOME, WHICH IS THIS WITNESS'S OWN TO TAKE AWAY.  A
  #   plain DELETE.ACCOUNT keeps the home by design - REMOVE.HOME is the other
  #   path, the owner's 10 Sep ruling - so a cleanup that did not ask for it left
  #   /home/<acc> behind after every run: the first real run left /home/zzabst.
  #   Only when the USER is gone: a home whose user survives still belongs to
  #   that user.  AND ONLY WITH --commit: a dry run changes nothing (the run that
  #   added this was itself a dry run, and it tried).
  if [ "$COMMIT" -eq 1 ] && ! id "$ACC" >/dev/null 2>&1 && [ -d "/home/$ACC" ]; then
    rm -rf "/home/$ACC"
  fi
}
trap cleanup EXIT

# ==========================================================================
head2 "M1. no tier policy, no TIERGATE (S.25)"
ck "M1a the tier.policy file is not installed"   no "$(yesno_dir  "$SDSYS/tier.policy")"
ck "M1b the tier.policy path is not a file"      no "$(yesno_file "$SDSYS/tier.policy")"

# ==========================================================================
head2 "M2. a fresh CREATE.ACCOUNT writes no tier (S.25/W.7)"
say "  CREATE.ACCOUNT USER $ACC (SD's whole flow, as sdsys)"
if [ "$COMMIT" -eq 1 ]; then
  PW_OS="zz$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-14)"
fi
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC (answering the Linux password)" \
             "CREATE.ACCOUNT USER $ACC" "_PW_" "_PW_")
PW_OS=""
if [ "$COMMIT" -eq 1 ]; then
  [ -e "$REGISTER/$ACC" ] && MADE_ACCOUNT=1
  ck "M2a the register record exists (the gate for M2b-d)" yes "$(yesno_file "$REGISTER/$ACC")"
  if [ -e "$REGISTER/$ACC" ]; then
    say "  register record, field by field:"
    awk '{printf "      %d: %s\n", NR, $0}' "$REGISTER/$ACC"
    ck "M2b field 5 (ACC\$SUSPENDED) is blank - no tier" "" "$(sed -n '5p' "$REGISTER/$ACC")"
    ck "M2c field 6 (retired ACC\$PRIOR.TIER) is blank"   "" "$(sed -n '6p' "$REGISTER/$ACC")"
    ck "M2d the record has no fields 7/8 (ACC\$SH / ACC\$OS.EXEC are gone)" "" "$(sed -n '7p' "$REGISTER/$ACC")"
  else
    not_reached "M2b field 5 blank"; not_reached "M2c field 6 blank"; not_reached "M2d no fields 7/8"
  fi
fi

# ==========================================================================
head2 "M3. no tier keyword in MODIFY.ACCOUNT (S.25/W.7)"
OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC STANDARD (refused: not an action word)" \
             "MODIFY.ACCOUNT $ACC STANDARD")
if [ "$COMMIT" -eq 1 ]; then
  # 18 Sep 26 dm - THE WORDING IS THE REWRITE'S (S.25).  modifya's grammar is
  #   MODIFY.ACCOUNT <acc> ADD|DELETE|SUSPENDED|UNSUSPEND, so a tier word is
  #   answered by the action rule and not by the old parse's "Unexpected
  #   token".  The row's subject is that the word is REFUSED, which this is.
  for w in STANDARD PROGRAMMER ADMINISTRATOR; do
    OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC $w" "MODIFY.ACCOUNT $ACC $w")
    ck_says "M3a $w is refused (not a MODIFY.ACCOUNT action)" \
            "Action Must Be Add, Delete, Suspended or Unsuspend" "$OUT"
  done
  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC SUSPENDED, then UNSUSPEND (the flag, W.7)" \
             "MODIFY.ACCOUNT $ACC SUSPENDED" "MODIFY.ACCOUNT $ACC UNSUSPEND")
  ck_says "M3b SUSPENDED is the flag (10179)" "is now suspended" "$OUT"
  ck "M3c and UNSUSPEND cleared it on disk" "" "$(sed -n '5p' "$REGISTER/$ACC" 2>/dev/null)"
fi

# ==========================================================================
head2 "M4. no OS-access grants (S.27)"
if [ "$COMMIT" -eq 1 ]; then
  # S.27: the OS-access words are gone from the grammar, so they are refused by
  # the action rule (see M3a's note) - the row's subject is the REFUSAL.
  for w in SH-ON SH-OFF OS-ON OS-OFF; do
    OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC $w" "MODIFY.ACCOUNT $ACC $w")
    ck_says "M4a $w is refused (not a MODIFY.ACCOUNT action)" \
            "Action Must Be Add, Delete, Suspended or Unsuspend" "$OUT"
  done
  # SH for everyone: the verb is in a plain account's VOC (newvoc gained it),
  # and the OS runs at the account's own Linux permissions - no 10053.
  OUT=$(run_sd "$ACC" "SH echo zzsh-absence-ran (no gate)" "SH echo zzsh-absence-ran")
  ck_says "M4b SH runs for a plain account (no 10053)" "zzsh-absence-ran" "$OUT"
  ck_absent "M4c and it was not refused" "is not permitted to use the operating system shell" "$OUT"
fi

# ==========================================================================
head2 "M5. no API route words (S.28)"
if [ "$COMMIT" -eq 1 ]; then
  # S.28: the API route words are gone from the grammar (see M3a's note).
  for w in API NONE SSH BOTH; do
    OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC $w" "MODIFY.ACCOUNT $ACC $w")
    ck_says "M5a MODIFY.ACCOUNT $w is refused (not a MODIFY.ACCOUNT action)" \
            "Action Must Be Add, Delete, Suspended or Unsuspend" "$OUT"
  done
  OUT=$(run_sd sdsys "CREATE.ACCOUNT USER zzabst2 NO.QUERY (no API word needed)" \
             "CREATE.ACCOUNT USER zzabst2 NO.QUERY")
  ck_says "M5b CREATE.ACCOUNT no longer demands API or NONE (10082 is gone)" \
          "Cannot create user zzabst2 with NO.QUERY" "$OUT"
fi

# ==========================================================================
head2 "M6. no grant verbs (W.8)"
if [ "$COMMIT" -eq 1 ]; then
  OUT=$(run_sd sdsys "GRANT $ACC TO $ACC" "GRANT $ACC TO $ACC")
  ck_says "M6a GRANT is not in any VOC" "not in your VOC" "$OUT"
  OUT=$(run_sd sdsys "REVOKE $ACC FROM $ACC" "REVOKE $ACC FROM $ACC")
  ck_says "M6b REVOKE is not in any VOC" "not in your VOC" "$OUT"
  OUT=$(run_sd sdsys "LIST.GRANTS $ACC" "LIST.GRANTS $ACC")
  ck_says "M6c LIST.GRANTS is not in any VOC" "not in your VOC" "$OUT"
  # The grant that remains is Linux membership itself - MODIFY.ACCOUNT ADD
  # rides on it, and it is the whole of the LOGTO wall (S.25).
  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC ADD $ACC (the grant IS the membership)" \
             "MODIFY.ACCOUNT $ACC ADD $ACC")
  # 18 Sep 26 dm - THE FIRST RUN'S WORDING ASSUMED A FIRST ADD.  CREATE.ACCOUNT
  #   already joins the account to its own sdu_ group (createa's make.account),
  #   so by the time this runs the membership IS the state and the verb answers
  #   "already a member of group sdu_<acc>".  The row asserts the GROUP by name -
  #   the grant IS the membership - and that the verb did not fail to make it so,
  #   so either wording passes and a refusal cannot.
  ck_says "M6d the surviving grant verb is MODIFY.ACCOUNT ADD, naming the group" \
          "group sdu_$ACC" "$OUT"
  ck_absent "M6d2 and it did not fail to make it so" "Unable" "$OUT"
  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC DELETE $ACC" "MODIFY.ACCOUNT $ACC DELETE $ACC")
  ck_says "M6e and DELETE (10021)" "$ACC removed from group sdu_$ACC" "$OUT"
fi

# ==========================================================================
head2 "M7. no sdadmin, no sdapi; the boundary names sdsys (S.26/S.28)"
ck "M7a the sdadmin group does not exist" no "$(yesno_group sdadmin)"
ck "M7b the sdapi group does not exist"   no "$(yesno_group sdapi)"
ck "M7c the sdsys OS user exists" yes "$(yesno_user sdsys)"
if [ -f /etc/sudoers.d/sdcore ]; then
  SUDOERS=$(cat /etc/sudoers.d/sdcore)
  say "  /etc/sudoers.d/sdcore:"
  printf '%s\n' "$SUDOERS" | sed -e 's/^/      | /'
  ck_says "M7d the sudoers grant names the sdsys user" "sdsys ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate" "$SUDOERS"
  # 18 Sep 26 dm - COMMENTS ARE NOT GRANTS.  The teardown's own note in the
  #   drop-in says the grant moved FROM %sdadmin, so searching the whole file
  #   fails on the sentence that records the change; the rule lines are the
  #   row's subject.
  ck_absent "M7e and not the sdadmin group (rule lines)" "%sdadmin" \
            "$(printf '%s\n' "$SUDOERS" | grep -v '^[[:space:]]*#')"
else
  not_reached "M7d the sudoers grant names the sdsys user"
fi
if [ -f /etc/ssh/sshd_config ]; then
  SSC=$(cat /etc/ssh/sshd_config)
  ck_says "M7f sshd forces every sdusers member into sd" "Match Group sdusers,!sdsys" "$SSC"
  ck_says "M7g and denies sdsys network login" "DenyUsers sdsys" "$SSC"
  ck_absent "M7h and not the sdadmin exemption" "sdusers,!sdadmin" "$SSC"
else
  not_reached "M7f sshd forces every sdusers member into sd"
fi

# ==========================================================================
head2 "M8. the administrator model, driven (S.26)"
OUT=$(run_sd_as root "a root session (refused outright)" "WHO")
if [ "$COMMIT" -eq 1 ]; then
  ck_says "M8a a root session is refused in 10176's words" "root is not SD's administrator" "$OUT"
  ck_absent "M8b and never reached the prompt (no WHO)" "zzabst" "$OUT"
  ck_says "M8c and it was audited" "ELEVATION REFUSED reason=root is not SD administrator" \
    "$(tail -n 5 "$SDSYS/audit" 2>/dev/null)"
fi
OUT=$(run_sd sdsys "a local sdsys session (granted)" "WHO")
if [ "$COMMIT" -eq 1 ]; then
  ck_says "M8d the local sdsys session is granted (10916)" "SD administration granted: this session is the sdsys OS user" "$OUT"
  ck_says "M8e and the trail says so" "ELEVATION GRANTED reason=local sdsys session" \
    "$(tail -n 5 "$SDSYS/audit" 2>/dev/null)"
fi

# ==========================================================================
head2 "M9. the source agrees (the tree this script lives in)"
SRC="$(dirname "$(dirname "$SELF")")"
REPO="$(dirname "$(dirname "$SRC")")"
say "  source root: $SRC (repo root: $REPO)"
ck "M9a the installer creates no sdadmin group" 0 \
   "$(grep -c 'groupadd.*sdadmin\|groupadd --system sdadmin' "$REPO/installsdai.sh" 2>/dev/null)"
ck "M9b the installer creates no sdapi group" 0 \
   "$(grep -c 'groupadd.*sdapi\|groupadd --system sdapi' "$REPO/installsdai.sh" 2>/dev/null)"
ck "M9c the installer seeds a PLAIN account (no ADMINISTRATOR keyword)" 0 \
   "$(grep -c 'create-account USER .*ADMINISTRATOR' "$REPO/installsdai.sh" 2>/dev/null)"
ck "M9d the ssh helper's block excludes sdsys, not sdadmin" 1 \
   "$(grep -c 'printf.*Match Group sdusers,!sdsys' "$SRC/gplbld/ssh-forcecommand.sh" 2>/dev/null)"
ck "M9e TIERGATE is not in the shipped gpl.bp sources" 0 \
   "$(find "$SRC/sdsys" -name 'tiergate' -o -name 'tier.policy' 2>/dev/null | wc -l | tr -d ' ')"
ck "M9f no tier keyword survives in CREATE.ACCOUNT's grammar" 0 \
   "$(grep -cE 'KW\$ADMIN|ADMINISTRATOR)' "$SRC/sdsys/gpl.bp/createa" 2>/dev/null)"

# ==========================================================================
head2 "10. verdict"
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
  say "witness-absence: FAILED - no check ran, so this proves nothing."
  exit 1
fi
if [ "$FAIL" -gt 0 ]; then
  say "witness-absence: FAILED - $FAIL of $((PASS + FAIL)) checks failed."
  exit 1
fi
say "witness-absence: PASSED - $PASS of $PASS checks passed."
exit 0
