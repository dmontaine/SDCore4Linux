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
#       refused as unexpected tokens, and SUSPENDED/UNSUSPENDED are the flag
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
#       (10190, audited) and a local sdsys session is granted (10916).
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
MARKER="$SDSYS/\$attach.$ACC"   # 19 Sep 26: ADOPT renamed ATTACH, the port's name
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
#   18 Sep 26 dm, NIGHT - S.26's corrected route: ONLY A REAL SDSYS LOGIN
#   administers, so a bare "sudo -u sdsys sd" is REFUSED (10195) - its
#   loginuid is whoever ran the witness.  The witness runs as root (--commit
#   is sudo), and root alone may adopt a loginuid: the bridge writes sdsys's
#   uid into /proc/self/loginuid of exactly this process tree and execs sudo,
#   reproducing the credential state of a genuine sdsys login (OS user sdsys,
#   local, loginuid sdsys).  It grants nothing to anybody who is not already
#   root; M8f measures the un-bridged route and must be refused.
    out=$(printf '%s' "$body" | timeout 90 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD_BIN" 2>&1 | strip)
  elif [ "$user" = root ]; then
    out=$(printf '%s' "$body" | timeout 90 "$SD_BIN" 2>&1 | strip)
  else
#   18 Sep 26 - a PLAIN ACCOUNT'S OWN SESSION.  M4b used run_sd "$ACC", and
#   run_sd's first argument is a TITLE on a sdsys session - so "SH runs for a
#   plain account" was measured as the administrator and passed on nothing
#   (the 20:39 run: the admin banner inside the "as zzabst" transcript).  The
#   account's session is its own uid, the way the account itself would run sd.
    out=$(printf '%s' "$body" | timeout 90 sudo -u "$user" "$SD_BIN" 2>&1 | strip)
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
[ "$(yesno_file "$MARKER")" = yes ] && { say "  DIRTY: an ATTACH marker for $ACC exists"; DIRTY=1; }
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
      | timeout 90 sudo sh -c 'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"' sd-run "$SD_BIN" >/dev/null 2>&1
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
  PW_OS="Zz9-$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-14)"
fi
# 19 Sep 26 - S.32: A WEAK ENTRY FIRST, so M2g/M2h have something to read.
#   "weakpass" is 8 lower-case letters - it lacks three of the four kinds, so
#   set_passwd refuses it, counts it, and asks again without ever reaching the
#   repeat; the good password then goes in twice as before.  UNRUN when
#   written: this line and M2g/M2h are owed the next cycle.
OUT=$(run_sd "CREATE.ACCOUNT USER $ACC (a weak Linux password, then a good one)" \
             "CREATE.ACCOUNT USER $ACC" "weakpass" "_PW_" "_PW_")
PW_OS=""
# 20 Sep 26 - kept for M5f: this is the only creation in the run that passes NO
# route word, so it is the only place the S.29 default can be read.
CREATE_OUT="$OUT"
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
  # 19 Sep 26 - THE LINUX PASSWORD IS SD'S NOW (owner's ruling: SD requires a
  #   complex password whatever the OS allows).  SD asks, applies !pw_complex,
  #   and sd-elevate setpw sets it from stdin - not an interactive passwd.
  ck_says "M2e the Linux password was set by SD, through setpw" "Linux password set for $ACC" "$OUT"
  ck_absent "M2f and not by an interactive passwd" "sd-elevate: passwd -- " "$OUT"
  # 19 Sep 26 - S.32: the rule and the attempt count at THIS prompt too.  M2h
  #   anchors on 10921 fully expanded - a bare number, an empty expansion or a
  #   missing message record all read differently, and none of them matches.
  ck_says "M2g the weak Linux password is refused in 10920's words" "A password needs at least 8 characters" "$OUT"
  ck_says "M2h and is counted in 10921's words" "That was attempt 1 of 3." "$OUT"
fi

# ==========================================================================
head2 "M3. no tier keyword in MODIFY.ACCOUNT (S.25/W.7)"
OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC STANDARD (refused: not an action word)" \
             "MODIFY.ACCOUNT $ACC STANDARD")
if [ "$COMMIT" -eq 1 ]; then
  # 18 Sep 26 dm - THE WORDING IS THE REWRITE'S (S.25).  modifya's grammar is
  #   MODIFY.ACCOUNT <acc> ADD|DELETE|SUSPENDED|UNSUSPENDED, so a tier word is
  #   answered by the action rule and not by the old parse's "Unexpected
  #   token".  The row's subject is that the word is REFUSED, which this is.
  # 19 Sep 26 - UNSUSPEND joins the refused words: the keyword is the Windows
  #   port's UNSUSPENDED now, and the old spelling must not linger as an alias.
  for w in STANDARD PROGRAMMER ADMINISTRATOR UNSUSPEND; do
    OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC $w" "MODIFY.ACCOUNT $ACC $w")
    ck_says "M3a $w is refused (not a MODIFY.ACCOUNT action)" \
            "Action Must Be Add, Delete, Ssh, Api, Both, None," "$OUT"
  done
  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC SUSPENDED, then UNSUSPENDED (the flag, W.7)" \
             "MODIFY.ACCOUNT $ACC SUSPENDED" "MODIFY.ACCOUNT $ACC UNSUSPENDED")
  ck_says "M3b SUSPENDED is the flag (10193)" "is now suspended" "$OUT"
  # 19 Sep 26: a MISSING record also reads blank, and M3c passed on the third
  # cycle with no account at all.  The null case is refused out loud.
  if [ -f "$REGISTER/$ACC" ]; then
    ck "M3c and UNSUSPENDED cleared it on disk" "" "$(sed -n '5p' "$REGISTER/$ACC")"
  else
    not_reached "M3c and UNSUSPENDED cleared it on disk (no register record to read)"
  fi
fi

# ==========================================================================
head2 "M4. no OS-access grants (S.27)"
if [ "$COMMIT" -eq 1 ]; then
  # S.27: the OS-access words are gone from the grammar, so they are refused by
  # the action rule (see M3a's note) - the row's subject is the REFUSAL.
  for w in SH-ON SH-OFF OS-ON OS-OFF; do
    OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC $w" "MODIFY.ACCOUNT $ACC $w")
    ck_says "M4a $w is refused (not a MODIFY.ACCOUNT action)" \
            "Action Must Be Add, Delete, Ssh, Api, Both, None," "$OUT"
  done
  # SH for everyone: the verb is in a plain account's VOC (newvoc gained it),
  # and the OS runs at the account's own Linux permissions - no 10053.  This
  # is run_sd_as, NOT run_sd: the session must BE the account (see the note
  # in run_sd_as), or the row measures the administrator's SH instead.
  OUT=$(run_sd_as "$ACC" "SH echo zzsh-absence-ran (no gate)" "SH echo zzsh-absence-ran")
  ck_says "M4b SH runs for a plain account (no 10053)" "zzsh-absence-ran" "$OUT"
  ck_absent "M4c and it was not refused" "is not permitted to use the operating system shell" "$OUT"
fi

# ==========================================================================
# 20 Sep 26 - M5 MEASURED THE OPPOSITE UNTIL TODAY.  S.28 deleted the route
# words and this section proved them refused; S.29 brings them back on the
# owner's ruling, so the same four words are now driven for their effect.
# ***THE DOOR IS DRIVEN BOTH WAYS ON PURPOSE***: a narrowing-only build passes
# every obvious test, which is how the tier teardown left no way to lift a
# suspension.  NONE first, so every later row starts from nothing and a row
# that changed nothing cannot read as success.  Membership is read from the
# machine (id -nG), not from what the verb said about itself.
in_group() {   # user, group -> yes/no
  id -nG "$1" 2>/dev/null | tr ' ' '\n' | grep -qx "$2" && echo yes || echo no
}
head2 "M5. the route words narrow AND re-widen (S.29)"
if [ "$COMMIT" -eq 1 ] && [ ! -f "$REGISTER/$ACC" ]; then
  for r in "M5a NONE" "M5b SSH" "M5c API" "M5d BOTH" "M5e BOTH again" "M5f the default at create"; do
    not_reached "$r"; done
elif [ "$COMMIT" -eq 1 ]; then
  say "  before: $ACC in sdssh=$(in_group "$ACC" sdssh) sdapi=$(in_group "$ACC" sdapi)"
  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC NONE" "MODIFY.ACCOUNT $ACC NONE")
  ck_says "M5a NONE takes both routes away (10079)" "has no remote access" "$OUT"
  ck "M5a2 and the machine agrees: neither group" "no no" \
     "$(in_group "$ACC" sdssh) $(in_group "$ACC" sdapi)"

  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC SSH" "MODIFY.ACCOUNT $ACC SSH")
  ck_says "M5b SSH re-widens one route (10076)" "ssh only, not the API" "$OUT"
  ck "M5b2 and the machine agrees: sdssh only" "yes no" \
     "$(in_group "$ACC" sdssh) $(in_group "$ACC" sdapi)"

  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC API" "MODIFY.ACCOUNT $ACC API")
  ck_says "M5c API swaps the routes over (10077)" "the API only, not ssh" "$OUT"
  ck "M5c2 and the machine agrees: sdapi only" "no yes" \
     "$(in_group "$ACC" sdssh) $(in_group "$ACC" sdapi)"

  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC BOTH" "MODIFY.ACCOUNT $ACC BOTH")
  ck_says "M5d BOTH restores what NONE took (10078)" "ssh and the API" "$OUT"
  ck "M5d2 and the machine agrees: both groups" "yes yes" \
     "$(in_group "$ACC" sdssh) $(in_group "$ACC" sdapi)"

  OUT=$(run_sd sdsys "MODIFY.ACCOUNT $ACC BOTH (again)" "MODIFY.ACCOUNT $ACC BOTH")
  ck_says "M5e asking twice changes nothing and says so (10080)" \
          "already had that access" "$OUT"

  # The default: M2 created $ACC with no route word at all.
  ck_says "M5f CREATE.ACCOUNT with no route word gave both (10078)" \
          "SD routes for $ACC: ssh and the API" "$CREATE_OUT"

  OUT=$(run_sd sdsys "CREATE.ACCOUNT USER zzabst2 NO.QUERY (no route word needed)" \
             "CREATE.ACCOUNT USER zzabst2 NO.QUERY")
  ck_says "M5g CREATE.ACCOUNT does not demand a route word (10082 is not reached)" \
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
  ck_says "M7d2 and sdusers only the three cred-own lists (W.10)" \
    "%sdusers ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate cred-own query, /usr/local/sbin/sd-elevate cred-own verify, /usr/local/sbin/sd-elevate cred-own set" "$SUDOERS"
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
  ck_says "M8a a root session is refused in 10190's words" "root is not SD's administrator" "$OUT"
  ck_absent "M8b and never reached the prompt (no WHO)" "zzabst" "$OUT"
  ck_says "M8c and it was audited" "ELEVATION REFUSED reason=root is not SD administrator" \
    "$(tail -n 5 "$SDSYS/audit" 2>/dev/null)"
fi
OUT=$(run_sd sdsys "a sdsys login session, by the bridge (granted)" "WHO")
if [ "$COMMIT" -eq 1 ]; then
  ck_says "M8d the sdsys login session is granted (10916)" "SD administration granted: this session is the sdsys OS user" "$OUT"
  ck_says "M8e and the trail says so" "ELEVATION GRANTED reason=sdsys login" \
    "$(tail -n 5 "$SDSYS/audit" 2>/dev/null)"
fi
if [ "$COMMIT" -eq 1 ]; then
# 18 Sep 26 dm, NIGHT - THE OWNER'S RULING AS A ROW: no path from another
#   user into sdsys.  The witness's own loginuid is the owner's (it arrives
#   by sudo from a don session), so a BARE "sudo -u sdsys sd" - no bridge -
#   is exactly the route that must be refused, in 10195's words, audited,
#   never reaching the prompt.
  OUT=$(printf '\nTERM 200,9999\nWHO\nOFF\n' | timeout 90 sudo -u sdsys "$SD_BIN" 2>&1 | strip)
  printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
  # 19 Sep 26: the anchor must sit inside ONE line of 10195 - "not logged in as
  # sdsys" spans its line break and failed on the third cycle although the
  # refusal was right (M8g/M8h passed).
  ck_says "M8f sudo -u sdsys is refused (10195)" "but the machine was not logged in as" "$OUT"
  ck_absent "M8g and never reached the prompt (no grant banner)" "SD administration granted" "$OUT"
  ck_says "M8h and it was audited" "ELEVATION REFUSED reason=sdsys session without a sdsys login" \
    "$(tail -n 5 "$SDSYS/audit" 2>/dev/null)"
fi

# ==========================================================================
# 19 Sep 26 dm - M12, SDSYS HAS NO REMOTE ACCESS (owner, 19 Sep 2026: "sdsys
# should not have any remote access from ssh or api").  CPROC now refuses a
# sdsys session that arrives over a remote transport, at the door (10191),
# instead of letting it start and leaving LOGIN to refuse the ACCOUNT (10002).
#
# ***THIS MEASURES SD'S HALF AND SAYS SO.***  A real ssh login as sdsys cannot
# be staged here: sshd's DenyUsers refuses it, which is the other half of the
# door and is measured by test-ssh-forcecommand.py against the config.  What
# CPROC actually reads is SSH_CONNECTION / SSH_TTY, so that is what is set -
# reproducing the environment an ssh session would hand it.  The limit is the
# point: this proves SD refuses, not that sshd does.
#
# THE BRIDGE IS STILL USED, so the session is otherwise a GOOD one - OS user
# sdsys, loginuid sdsys.  Without it the refusal would be 10195 and the row
# would pass for the wrong reason; M12b is the control that says which refusal
# fired.  UNRUN WHEN WRITTEN: owed the next cycle.
head2 "M12. sdsys over a remote transport is refused at the door (owner, 19 Sep)"
if [ "$COMMIT" -eq 0 ]; then
  for r in "M12a refused in 10191's words" "M12b not the 10195 refusal" "M12c no grant" "M12d audited"; do not_reached "$r"; done
else
  say "  a bridged sdsys session (loginuid sdsys) with SSH_CONNECTION set"
  OUT=$(printf '\nTERM 200,9999\nWHO\nOFF\n' | timeout 90 sudo sh -c \
        'printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys SSH_CONNECTION="10.0.0.9 51000 10.0.0.1 22" "$1"' \
        sd-run "$SD_BIN" 2>&1 | strip)
  printf '%s\n' "$OUT" | sed -e 's/^/      | /' >&2
  # The anchor sits inside ONE line of 10191 - M8f was fixed on the third cycle
  # for spanning a line break, and this message wraps in the same way.
  ck_says "M12a refused in 10191's words" "may not administer over ssh or the API" "$OUT"
  ck_absent "M12b and NOT as a session without a sdsys login (10195)" "was not logged in as" "$OUT"
  ck_absent "M12c no administrator grant" "SD administration granted" "$OUT"
  ck_says "M12d audited as a remote transport" "ELEVATION REFUSED reason=sdsys session from a remote transport" \
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
# 19 Sep 26 - W.10: a person sets their OWN SD password.  MODIFY.PASSWORD's
# prompts are hidden and need a tty, so no instrument drives them; what this
# measures is the machinery underneath, on the real install: the sudoers grant
# (sdusers may run exactly "cred-own query|set"), the helper's confinement to
# the caller's own record, and the current-password proof.  Fixed test keys,
# never a real password; the record goes with the account at cleanup.
head2 "M10. a person's own SD password, underneath (W.10)"
ELEV=/usr/local/sbin/sd-elevate
CREDF="$SDSYS/\$cred/$ACC"
if [ "$COMMIT" -eq 1 ] && [ ! -f "$REGISTER/$ACC" ]; then
  for r in "M10a query" "M10b other verbs refused by sudo" "M10b3 helper never ran" "M10c first set" "M10d record owner/mode" \
           "M10e wrong current refused" "M10f right current accepted" \
           "M10g verify refuses wrong" "M10h verify accepts right"; do not_reached "$r"; done
elif [ "$COMMIT" -eq 1 ]; then
  K1=$(head -c 32 /dev/zero | tr '\0' '\021' | base64)
  K2=$(head -c 32 /dev/zero | tr '\0' '\042' | base64)
  SALT=$(head -c 16 /dev/zero | tr '\0' '\063' | base64)
  as_acc() { sudo -u "$ACC" sudo -n "$ELEV" "$@" 2>&1; }
  OUT=$(as_acc cred-own query); say "      > (as $ACC) sudo -n sd-elevate cred-own query"; say "      | $OUT"
  case "$OUT" in none|salt\ *) ck "M10a the account's own query answers" yes yes ;;
                 *) ck "M10a the account's own query answers" "none or salt" "$OUT" ;; esac
  OUT=$(as_acc useradd zzw10probe); say "      > (as $ACC) sudo -n sd-elevate useradd zzw10probe"; say "      | $OUT"
  # 19 Sep 26 - fifth cycle: this box's sudo is sudo-rs (0.2.14), whose -n
  # refusal is "I'm afraid I can't do that", not C sudo's "a password is
  # required"; the refusal was right and the anchor failed it.  Either
  # implementation's wording passes, and M10b3 proves the helper never ran
  # (it prints "sd-elevate:" whenever it does).
  case "$OUT" in
    *"a password is required"*) ck_says "M10b any other helper verb is refused by sudo itself" "a password is required" "$OUT" ;;
    *) ck_says "M10b any other helper verb is refused by sudo itself" "I'm afraid I can't do that" "$OUT" ;;
  esac
  ck "M10b2 and nothing was made" no "$(yesno_user zzw10probe)"
  ck_absent "M10b3 and the helper never ran" "sd-elevate:" "$OUT"
  CUR=""; [ -f "$CREDF" ] && CUR=$(sed -n '5p' "$CREDF")
  say "      (a credential existed before: $([ -n "$CUR" ] && echo yes || echo no))"
  OUT=$(printf '%s\n' "$CUR" 2 SCRAM-SHA-256 "$SALT" 600000 "$K1" "$K1" | as_acc cred-own set)
  say "      > (as $ACC) cred-own set, the current key as found"; say "      | $OUT"
  ck_says "M10c the account sets its own record" "SD password set for $ACC" "$OUT"
  ck "M10d the record is sdsys:sdusers 600" "sdsys:sdusers 600" "$(stat -c '%U:%G %a' "$CREDF" 2>/dev/null)"
  OUT=$(printf '%s\n' "$K2" 2 SCRAM-SHA-256 "$SALT" 600000 "$K2" "$K2" | as_acc cred-own set)
  say "      > (as $ACC) cred-own set, a WRONG current key"; say "      | $OUT"
  ck_says "M10e a wrong current password is refused" "the current password is not correct" "$OUT"
  ck "M10e2 and the record kept its key" "$K1" "$(sed -n '5p' "$CREDF" 2>/dev/null)"
  OUT=$(printf '%s\n' "$K1" 2 SCRAM-SHA-256 "$SALT" 600000 "$K2" "$K2" | as_acc cred-own set)
  say "      > (as $ACC) cred-own set, the RIGHT current key"; say "      | $OUT"
  ck_says "M10f the right current password is accepted" "SD password set for $ACC" "$OUT"
  ck "M10f2 and the record changed" "$K2" "$(sed -n '5p' "$CREDF" 2>/dev/null)"
  # 19 Sep 26 - verify, what MODIFY.PASSWORD now asks BEFORE the new password
  #   (the owner at the keyboard: a wrong current one used to reach the new-
  #   password prompts).  The record now holds K2.
  OUT=$(printf '%s\n' "$K1" | as_acc cred-own verify)
  say "      > (as $ACC) cred-own verify, a WRONG current key"; say "      | $OUT"
  ck_says "M10g verify refuses a wrong current password" "the current password is not correct" "$OUT"
  OUT=$(printf '%s\n' "$K2" | as_acc cred-own verify)
  say "      > (as $ACC) cred-own verify, the RIGHT current key"; say "      | $OUT"
  ck_says "M10h verify accepts the right one" "the current password is correct" "$OUT"
  ck_absent "M10h2 and it wrote nothing" "write " "$OUT"
fi

# ==========================================================================
# 19 Sep 26 - M11, SD'S PASSWORD RULE ON THE SD PASSWORD (owner's ruling: 8+
# characters, a lower-case letter, an upper-case letter, a digit and a
# symbol).  The administrator sets zzabst's SD password: three entries that
# each lack exactly one kind are refused before the repeat is asked, and the
# command ends with nothing written; then a good one is taken.  The record is
# read before and after, so a refusal that wrote anyway cannot pass.
head2 "M11. SD's password rule on MODIFY.PASSWORD (owner, 19 Sep)"
if [ "$COMMIT" -eq 1 ] && [ ! -f "$REGISTER/$ACC" ]; then
  for r in "M11a weak refused" "M11a2 attempt counted" "M11b ended unchanged" "M11c record untouched" "M11d a good one taken"; do not_reached "$r"; done
elif [ "$COMMIT" -eq 1 ]; then
  SK_BEFORE=$(sed -n '5p' "$CREDF" 2>/dev/null)
  OUT=$(run_sd "MODIFY.PASSWORD $ACC, three weak entries" \
               "MODIFY.PASSWORD $ACC" "abcdef1!" "ABCDEF1!" "Abcdefg1")
  ck_says "M11a a weak password is refused in 10920's words" "A password needs at least 8 characters" "$OUT"
  # 19 Sep 26 - S.32: the third weak entry is the LAST of the three, so the
  #   anchor is the count at its limit.  It matches only when 10921 expanded
  #   BOTH arguments; UNRUN when written, owed the next cycle.
  ck_says "M11a2 and counted in 10921's words, up to the limit" "That was attempt 3 of 3." "$OUT"
  ck_says "M11b three weak entries end the command" "Password not changed." "$OUT"
  ck_absent "M11b2 and the repeat was never asked" "Repeat new password" "$OUT"
  ck "M11c the credential record is untouched" "$SK_BEFORE" "$(sed -n '5p' "$CREDF" 2>/dev/null)"
  OUT=$(run_sd "MODIFY.PASSWORD $ACC, a good entry" \
               "MODIFY.PASSWORD $ACC" "Zz9-good-Pass" "Zz9-good-Pass")
  ck_says "M11d a password meeting the rule is taken" "Password set for account $ACC" "$OUT"
fi

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
