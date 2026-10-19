#!/usr/bin/env bash
#
# witness-sdnet-writegroup.sh - what only a root run on a real install shows about MODIFY.ACCOUNT files-on / files-off / files-write-on / files-write-off, and the ORPHAN
#                               (K4b, 19 Oct 2026; the S.65 finish).
#
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-writegroup.sh [--account NAME]
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-writegroup.sh --selftest        (no sudo, no sd: the helpers on known texts)
#
# ***NEEDS sudo.***  Run it from the owner's login (SUDO_USER must name a person, not root).  It CHANGES REAL STATE and puts it back: the membership of ONE person in the two
# Linux groups sdfiles and sdfileswrite.  The person is the Linux user of the SD account NAME (default: the account that has SUDO_USER's own name); their membership is read first
# and set back at the end, whatever happens (an EXIT trap), and the script says what it found and what it left.  It does not install and does not uninstall.
#
# WHY IT EXISTS.  K4a (19 Oct 2026) changed MODIFY.ACCOUNT: files-off removes the write group FIRST and then sdfiles, reading each back, and it works for a person who is in
# sdfileswrite and NOT in sdfiles (the ORPHAN); files-on removes a leftover write membership before it adds sdfiles.  gplbld/sandbox-filesgrp.py runs the real program against a
# SCRATCH group file and a stand-in for sd-elevate, 53 rows and 6 mutants; what a sandbox cannot show is the real helper, the real /etc/group and the real sudoers line.  This does.
#
# PREREQUISITE: an install made from a tree that has the K4a change (the script CHECKS: the installed modifya holds change.files.group and message 11482 reads "has files %2"),
# the groups sdfiles and sdfileswrite on the machine, the person in sdusers.  Install first, as the owner, no sudo (installsdcore-dev.sh; it asks questions).
#
# WHAT IT DOES, in order (each row needs the success wording AND the state of the real groups; a session that prints nothing fails its rows):
#   P  the premises: the person is in sdusers, the groups exist, the install has K4a
#   W1 neither -> files-on: sdfiles only, "Account X has files yes", no files-write line
#   W2 -> files-write-on: both, "has files-write yes"
#   W3 both -> files-off: neither; "has files-write no" printed BEFORE "has files no"; the helper's own lines show the write group taken out before sdfiles
#   W4 THE ORPHAN: the script puts the person in sdfileswrite ONLY (gpasswd), checks it did, then files-off: not "already had that access", the membership GONE
#   W5 the orphan again, then files-on: sdfiles only (the write membership taken away BEFORE sdfiles was added), "has files-write no" before "has files yes"
#   W6 control: both -> files-on: "nothing changed", the write group kept (it was given on purpose)
#   W7 control: neither -> files-off: "nothing changed"
#   W8 files-write-on for a person not in sdfiles: refused (11523), nothing changed
#   W9 files-write-off with both: sdfiles kept, write gone, "has files-write no"
#   R  the person's membership is back as it was found
# NOT COVERED: a helper that FAILS half way (it cannot be made to fail on a real machine without breaking it) - the scratch-file suite does that - and a real files-only LOGIN
# (witness-sdnet-files-route.sh does that).
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-writegroup-<time>.log, handed back to the owner.
#
set -u
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
HERE=$(dirname "$SELF")
# shellcheck source=witness-sdnet-lib.sh
. "$HERE/witness-sdnet-lib.sh" || { echo "CANNOT RUN: no witness-sdnet-lib.sh beside $SELF"; exit 2; }

if [ "${1:-}" = "--selftest" ]; then wl_selftest; exit $?; fi
wl_logged "$SELF" witness-sdnet-writegroup "$@"
shift                                   # the "--logged" the re-exec added

ACC=""
if [ "${1:-}" = "--account" ]; then ACC=${2:-}; shift 2; fi
[ -n "$ACC" ] || ACC=$SUDO_USER

say "witness-sdnet-writegroup.sh  $(date +%Y%m%dT%H%M%S)"
say "  script  : $SELF"
say "  sudo    : $SUDO_USER (the owner)   account moved: $ACC"
say "  install : $(wl_commit_stamp)"
say "  sd      : $WL_SD   $(timeout 20 "$WL_SD" --version 2>&1 | head -1)"

# ------------------------------------------------------------------ P. premises
[ -x "$WL_SD" ] || need "$WL_SD is not installed - run the installer first"
[ -x "$WL_ELEVATE" ] || need "$WL_ELEVATE is not installed"
wl_group_exists sdfiles || need "no Linux group sdfiles on this machine (install from a tree that makes it)"
wl_group_exists sdfileswrite || need "no Linux group sdfileswrite on this machine (install from a tree that makes it)"
grep -q 'change.files.group' "$WL_SDSYS/gpl.bp/modifya" 2>/dev/null || need "the installed modifya has no change.files.group: this install predates K4a (19 Oct 2026); install a newer Dev"
grep -q 'has files %2' "$WL_SDSYS/messages/11482" 2>/dev/null || need "the installed message 11482 is not 'Account %1 has files %2': this install predates K2 (19 Oct 2026)"
PERSON=$(wl_account_user "$ACC")
[ -n "$PERSON" ] || need "the register record of account '$ACC' is not a user account (field 3 is not sdu_<user>): give --account NAME"
id "$PERSON" >/dev/null 2>&1 || need "no Linux user '$PERSON'"
wl_in_group "$PERSON" sdusers || need "$PERSON is not in sdusers (files-on refuses such a person, and the login would too)"
INIT=$(wl_state "$PERSON")
INIT_F=0; INIT_W=0
case $INIT in *sdfiles=1*) INIT_F=1 ;; esac
case $INIT in *sdfileswrite=1*) INIT_W=1 ;; esac
say "  person  : $PERSON  found: $INIT   (set back to exactly this at the end)"

restore() {
  say ""
  say "== putting state back =="
  wl_set_state "$PERSON" "$INIT_F" "$INIT_W"
  expect_eq "R the person's membership is back as it was found" "$(wl_state "$PERSON")" "$INIT"
}
trap restore EXIT

FILES_YES=$(wl_msg 11482 "$ACC" yes); FILES_NO=$(wl_msg 11482 "$ACC" no)
WRITE_YES=$(wl_msg 11522 "$ACC" yes); WRITE_NO=$(wl_msg 11522 "$ACC" no)
ALREADY=$(wl_msg 10080 "$ACC" ""); NEED_FILES=$(wl_msg 11523 "$ACC" "")
say "  texts   : [$FILES_YES] [$FILES_NO] [$WRITE_YES] [$WRITE_NO]"
[ -n "$FILES_YES" ] && [ -n "$WRITE_NO" ] && [ -n "$ALREADY" ] && [ -n "$NEED_FILES" ] || need "a message file could not be read"

# helper_order OUT SECOND   the helper (sd-elevate) prints the command it runs on a line of its own ("sd-elevate: gpasswd -d USER GROUP" to take a member out,
# "sd-elevate: usermod -aG GROUP -- USER" to put one in), and OS.EXECUTE shows it in the session.  0 when the line that takes PERSON out of sdfileswrite is ABOVE the
# line named by SECOND (remove = take PERSON out of sdfiles, add = put PERSON into sdfiles), 1 when it is below, 2 when either line is not in OUT.
helper_order() {
  local w f
  w=$(printf '%s\n' "$1" | grep -n -E "sd-elevate: gpasswd -d ${PERSON} sdfileswrite *$" | head -1 | cut -d: -f1)
  case $2 in
    remove) f=$(printf '%s\n' "$1" | grep -n -E "sd-elevate: gpasswd -d ${PERSON} sdfiles *$" | head -1 | cut -d: -f1) ;;
    add)    f=$(printf '%s\n' "$1" | grep -n -E "sd-elevate: usermod -aG sdfiles -- ${PERSON} *$" | head -1 | cut -d: -f1) ;;
  esac
  [ -n "$w" ] && [ -n "${f:-}" ] || return 2
  [ "$w" -lt "$f" ]
}
# helper_row NAME OUT SECOND   a row from helper_order.  If the session does not show the helper's lines the row is NOT counted (it says so): the order of the two changes is
# then witnessed by the order of the two messages alone (the wl_before row above it), and the claim about the helper's own order is not made.
helper_row() {
  local rc
  helper_order "$2" "$3"; rc=$?
  if [ "$rc" -eq 0 ]; then pass "$1: the helper's own lines take the write group out BEFORE sdfiles"
  elif [ "$rc" -eq 2 ]; then say "  NOTE  $1: the session does not show both of the helper's lines (sd-elevate: ...), so the helper's own order is not witnessed (not counted); the message order above stands alone"
  else fail "$1: the helper changed sdfiles BEFORE it took the write group out"; fi
}

# ------------------------------------------------------------------ W1 to W9
say ""; say "== W1. neither -> files-on =="
wl_set_state "$PERSON" 0 0
OUT=$(wl_sd_admin "files-on" "MODIFY.ACCOUNT $ACC FILES-ON")
expect_has "W1 the line says files yes" "$OUT" "$FILES_YES"
expect_lacks "W1 no files-write line (nothing to take away)" "$OUT" "has files-write"
expect_eq "W1 the real groups: sdfiles only" "$(wl_state "$PERSON")" "sdfiles=1 sdfileswrite=0"

say ""; say "== W2. -> files-write-on =="
OUT=$(wl_sd_admin "files-write-on" "MODIFY.ACCOUNT $ACC FILES-WRITE-ON")
expect_has "W2 the line says files-write yes" "$OUT" "$WRITE_YES"
expect_eq "W2 the real groups: both" "$(wl_state "$PERSON")" "sdfiles=1 sdfileswrite=1"

say ""; say "== W3. both -> files-off =="
OUT=$(wl_sd_admin "files-off" "MODIFY.ACCOUNT $ACC FILES-OFF")
expect_has "W3 the write group's line" "$OUT" "$WRITE_NO"
expect_has "W3 the files line" "$OUT" "$FILES_NO"
wl_before "W3 the write group is reported taken out BEFORE sdfiles" "$OUT" "$WRITE_NO" "$FILES_NO"
helper_row "W3" "$OUT" remove
expect_eq "W3 the real groups: neither" "$(wl_state "$PERSON")" "sdfiles=0 sdfileswrite=0"

say ""; say "== W4. THE ORPHAN: in sdfileswrite and NOT in sdfiles, files-off =="
wl_set_state "$PERSON" 0 1
expect_eq "W4 PREMISE (this script's own doing): the person is in the write group alone" "$(wl_state "$PERSON")" "sdfiles=0 sdfileswrite=1"
OUT=$(wl_sd_admin "files-off on the orphan" "MODIFY.ACCOUNT $ACC FILES-OFF")
expect_lacks "W4 NOT 'already had that access' (the 18 Oct build said so and left the membership)" "$OUT" "$ALREADY"
expect_has "W4 the write group's line says no" "$OUT" "$WRITE_NO"
expect_eq "W4 the real groups: the orphan is GONE" "$(wl_state "$PERSON")" "sdfiles=0 sdfileswrite=0"

say ""; say "== W5. the orphan again, then files-on =="
wl_set_state "$PERSON" 0 1
expect_eq "W5 PREMISE: the person is in the write group alone" "$(wl_state "$PERSON")" "sdfiles=0 sdfileswrite=1"
OUT=$(wl_sd_admin "files-on on the orphan" "MODIFY.ACCOUNT $ACC FILES-ON")
expect_has "W5 the files line says yes" "$OUT" "$FILES_YES"
expect_has "W5 the write group's line says no (the leftover was taken away)" "$OUT" "$WRITE_NO"
wl_before "W5 the leftover write membership is reported taken out BEFORE sdfiles is added" "$OUT" "$WRITE_NO" "$FILES_YES"
helper_row "W5" "$OUT" add
expect_eq "W5 the real groups: sdfiles only - the leftover did NOT become write access" "$(wl_state "$PERSON")" "sdfiles=1 sdfileswrite=0"

say ""; say "== W6. control: both -> files-on =="
wl_set_state "$PERSON" 1 1
OUT=$(wl_sd_admin "files-on when already so" "MODIFY.ACCOUNT $ACC FILES-ON")
expect_has "W6 'already had that access; nothing changed'" "$OUT" "$ALREADY"
expect_lacks "W6 no files line" "$OUT" "$FILES_YES"
expect_eq "W6 the real groups: both, the write group kept (it was given on purpose)" "$(wl_state "$PERSON")" "sdfiles=1 sdfileswrite=1"

say ""; say "== W7. control: neither -> files-off =="
wl_set_state "$PERSON" 0 0
OUT=$(wl_sd_admin "files-off when already so" "MODIFY.ACCOUNT $ACC FILES-OFF")
expect_has "W7 'already had that access; nothing changed'" "$OUT" "$ALREADY"
expect_eq "W7 the real groups: neither" "$(wl_state "$PERSON")" "sdfiles=0 sdfileswrite=0"

say ""; say "== W8. files-write-on for a person who is not in sdfiles =="
OUT=$(wl_sd_admin "files-write-on without files-on" "MODIFY.ACCOUNT $ACC FILES-WRITE-ON")
expect_has "W8 refused with 11523 (the group on its own gives nothing)" "$OUT" "$NEED_FILES"
expect_eq "W8 the real groups: neither" "$(wl_state "$PERSON")" "sdfiles=0 sdfileswrite=0"

say ""; say "== W9. files-write-off with both =="
wl_set_state "$PERSON" 1 1
OUT=$(wl_sd_admin "files-write-off" "MODIFY.ACCOUNT $ACC FILES-WRITE-OFF")
expect_has "W9 the line says files-write no" "$OUT" "$WRITE_NO"
expect_lacks "W9 no 'files' line (sdfiles is not touched)" "$OUT" "$FILES_NO"
expect_eq "W9 the real groups: sdfiles kept, write gone" "$(wl_state "$PERSON")" "sdfiles=1 sdfileswrite=0"

trap - EXIT
restore                                 # before the summary, so that its row is counted; the trap above covers a script that stops early
wl_summary
exit $?
