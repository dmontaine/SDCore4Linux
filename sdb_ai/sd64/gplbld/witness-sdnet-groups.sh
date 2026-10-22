#!/usr/bin/env bash
#
# witness-sdnet-groups.sh - what the installer and the uninstaller do to the four route groups, read from the REAL /etc/group.  (K6c v and vii, 19 Oct 2026.)
#
#   sudo bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-groups.sh MODE [options]
#   bash      /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-groups.sh --selftest        (no sudo: the helpers on known texts)
#
#   MODE  arrange-upgrade   save the state, take an EMPTY sdfileswrite away if there is one (this script's one change), say what to run next
#         after-upgrade     [--gates-for USER] [--install-log FILE]   compare with the saved state after you ran the installer over that install
#         before-delete     save the state before you run the uninstaller
#         after-delete      --accounts keep|delete [--delete-log FILE]   compare with the saved state after you ran it
#         status            print the four groups and their members (changes nothing)
#
# ***NEEDS sudo*** (every mode, so that the log is the owner's and the group file is read the same way).  This script NEVER runs the installer or the uninstaller: both are
# interactive, replace or destroy the install, and are the owner's to run (the DELETE cycle, then the install, as in the s.65 plan).  It reads getent group before and after,
# and compares.  The only thing it changes is in arrange-upgrade, and only an EMPTY group: groupdel sdfileswrite, to put the machine in the state of an install made before the write group.
# Items (v) and (vii) of K6c destroy or replace the install, so they are done LAST, after witness-sdnet-files-route.sh, witness-sdnet-writegroup.sh and witness-sdnet-gaps.sh.
#
# THE TWO SEQUENCES   (THIS below is /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-sdnet-groups.sh; the script prints the commands in full, copy those)
#   (v) an installer over an install that has sdfiles but no sdfileswrite (the 18 Oct install was a fresh one after a DELETE cycle, so the creation of an empty sdfileswrite on
#       an UPGRADE was never seen):
#         sudo bash THIS arrange-upgrade
#         bash /home/don/Projects/SDCore4Linux/installsdcore-dev.sh        (as you always do, no sudo, keeping the accounts; capture it with `script`, NOT tee: an installer
#                                                                           piped through tee leaves its password prompt visible)
#         sudo bash THIS after-upgrade --install-log FILE [--gates-for YOU]   (--gates-for YOU if you answered y to "open every access gate for your account")
#   (vii) a DELETE cycle, read from the group file afterwards, for the branch that removes the accounts and for the branch that keeps them (two cycles, two installs):
#         sudo bash THIS before-delete
#         bash /home/don/Projects/SDCore4Linux/deletesdcore.sh               (answer DELETE to remove the accounts, or the keep word to keep them)
#         sudo bash THIS after-delete --accounts delete|keep --delete-log FILE
#
# WHAT EACH ROW NEEDS: the saved state of the SAME four groups (a missing or half-written state file is "cannot run", never a pass), the wording the installer or remover prints
# when you give the log, and the real group file.  A null case - a group the script could not read at all - fails the row.
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is /var/tmp/witness-sdnet-groups-<time>.<six random characters>.log.
# Changed 19 Oct 26 (finish 2, the verifier's findings): the state directory is made or checked with wl_state_dir (a link, or a directory others can write into, is refused).
#
set -u
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
HERE=$(dirname "$SELF")
# shellcheck source=witness-sdnet-lib.sh
. "$HERE/witness-sdnet-lib.sh" || { echo "CANNOT RUN: no witness-sdnet-lib.sh beside $SELF"; exit 2; }

if [ "${1:-}" = "--selftest" ]; then wl_selftest; exit $?; fi
wl_logged "$SELF" witness-sdnet-groups "$@"
shift                                   # the "--logged" the re-exec added

MODE=${1:-}; [ -n "$MODE" ] || need "give a MODE: arrange-upgrade | after-upgrade | before-delete | after-delete | status (see the header)"
shift
GATES_FOR=""; INSTALL_LOG=""; DELETE_LOG=""; ACCOUNTS=""
while [ $# -gt 0 ]; do
  case $1 in
    --gates-for)   [ $# -ge 2 ] || need "--gates-for needs a user"; GATES_FOR=$2; shift 2 ;;
    --install-log) [ $# -ge 2 ] || need "--install-log needs a file"; INSTALL_LOG=$2; shift 2 ;;
    --delete-log)  [ $# -ge 2 ] || need "--delete-log needs a file"; DELETE_LOG=$2; shift 2 ;;
    --accounts)    [ $# -ge 2 ] || need "--accounts needs keep or delete"; ACCOUNTS=$2; shift 2 ;;
    *) need "unknown argument '$1'" ;;
  esac
done

STATE_DIR=$WL_TMP/witness-sdnet-groups
STATE=$STATE_DIR/state
GROUPS4="sdssh sdapi sdfiles sdfileswrite sdfilesadmin"      # (the variable keeps its first name; since S.73 item 3, 21 Oct 26, there are five route groups)
STAMP=$(date +%Y%m%dT%H%M%S)

say "witness-sdnet-groups.sh $MODE  $STAMP"
say "  script  : $SELF"
say "  sudo    : $SUDO_USER (the owner)"
say "  state   : $STATE"

# members_sorted GROUP   the supplementary members, sorted and comma separated
members_sorted() { wl_members "$1" | tr ',' '\n' | sort | paste -s -d, -; }
# grp_desc GROUP   "exists|a,b" or "absent|"
grp_desc() { if wl_group_exists "$1"; then printf 'exists|%s' "$(members_sorted "$1")"; else printf 'absent|'; fi; }
show_groups() { local g; for g in $GROUPS4; do say "    $g: $(grp_desc "$g")"; done; }

save_state() {   # save_state PREFIX
  local p=$1 g tmp
  wl_state_dir "$STATE_DIR"
  touch "$STATE"
  tmp=$(mktemp "$STATE_DIR/tmp.XXXXXX") || need "cannot make a temporary file"
  grep -a -v "^$p|" "$STATE" > "$tmp" || true
  for g in $GROUPS4; do printf '%s|%s|%s\n' "$p" "$g" "$(grp_desc "$g")" >> "$tmp"; done
  cat "$tmp" > "$STATE"; rm -f -- "$tmp"
  say "  saved the state under '$p':"; show_groups
}
saved() { grep -a "^$1|$2|" "$STATE" 2>/dev/null | head -1 | cut -d'|' -f3-; }   # saved PREFIX GROUP -> "exists|a,b" or ""
need_saved() {   # need_saved PREFIX   all four lines must be there
  local g
  [ -r "$STATE" ] || need "no saved state ($STATE): run the first half of the sequence first (see the header)"
  for g in $GROUPS4; do [ -n "$(saved "$1" "$g")" ] || need "the saved state '$1' has no line for $g (a half-written state file is not a baseline)"; done
}
exists_of() { printf '%s' "${1%%|*}"; }      # "exists|a,b" -> exists
members_of() { printf '%s' "${1#*|}"; }      # "exists|a,b" -> a,b

case $MODE in
# ------------------------------------------------------------------
status)
  say ""; say "== the four route groups now =="; show_groups
  exit 0
  ;;
# ------------------------------------------------------------------
arrange-upgrade)
  say ""; say "== arrange: the state of an install made before the write group =="
  wl_group_exists sdfiles || need "no group sdfiles: there is no S.65 install to upgrade over (install first, from a tree that has slice 2c)"
  if wl_group_exists sdfileswrite; then
    M=$(wl_members sdfileswrite)
    if [ -n "$M" ]; then need "sdfileswrite has members ($M): this script never drops a group that holds someone. Remove them with modify.account <account> files-write-off first, or pick another machine"; fi
    save_state upgrade-before-arrange
    groupdel sdfileswrite && say "  groupdel sdfileswrite: done (it was empty; this script's doing)" || need "groupdel sdfileswrite failed"
  else
    say "  sdfileswrite does not exist already: nothing to take away"
  fi
  save_state upgrade-before
  if wl_group_exists sdfileswrite; then fail "A1 sdfileswrite still exists"; else pass "A1 sdfileswrite does not exist (the state of an install made before the write group)"; fi
  if wl_group_exists sdfiles; then pass "A2 sdfiles exists (there is an install with the files route to upgrade)"; else fail "A2 sdfiles does not exist"; fi
  say ""
  say "  NEXT, by you, not by this script (no sudo; keep the accounts):"
  say "      bash /home/don/Projects/SDCore4Linux/installsdcore-dev.sh"
  say "  then:  sudo bash $SELF after-upgrade --install-log FILE${GATES_FOR:+ --gates-for $GATES_FOR}"
  wl_summary; exit $?
  ;;
# ------------------------------------------------------------------
after-upgrade)
  need_saved upgrade-before
  say ""; say "== after the installer ran over the install =="; show_groups
  [ "$(exists_of "$(saved upgrade-before sdfileswrite)")" = absent ] || need "the saved state says sdfileswrite EXISTED before the install: this is not the (v) sequence (run arrange-upgrade first)"
  [ "$(exists_of "$(saved upgrade-before sdfiles)")" = exists ] || need "the saved state says sdfiles did not exist before the install: this is not the (v) sequence"
  for g in $GROUPS4; do
    now=$(grp_desc "$g")
    if [ "$g" = sdfileswrite ]; then continue; fi
    expect_eq "U1 $g is exactly as it was before the install (existence and members)" "$now" "$(saved upgrade-before "$g")"
  done
  if wl_group_exists sdfileswrite; then pass "U2 sdfileswrite now EXISTS (the installer made the missing group)"; else fail "U2 sdfileswrite does not exist after the install"; fi
  WNOW=$(members_sorted sdfileswrite)
  if [ -n "$GATES_FOR" ]; then
    expect_eq "U3 you answered y to the gate question: sdfileswrite holds exactly $GATES_FOR and nobody else" "$WNOW" "$GATES_FOR"
  else
    expect_eq "U3 sdfileswrite is EMPTY: nobody is given the write right by an upgrade" "$WNOW" ""
    wl_group_exists sdfileswrite || fail "U3b the group is not there, so 'empty' is the null case"
  fi
  INTER=""
  for u in $(wl_members sdfiles | tr ',' ' '); do
    if wl_in_group "$u" sdfileswrite && [ "$u" != "${GATES_FOR:-}" ]; then INTER="$INTER $u"; fi
  done
  expect_eq "U4 nobody who was in sdfiles was moved into sdfileswrite (apart from the gate answer)" "$INTER" ""
  if [ -n "$INSTALL_LOG" ]; then
    [ -r "$INSTALL_LOG" ] || need "the install log $INSTALL_LOG cannot be read"
    LOGT=$(sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g' "$INSTALL_LOG")
    expect_has "U5 the installer said it made the group ('Creating group: sdfileswrite.')" "$LOGT" "Creating group: sdfileswrite."
    expect_has "U5 and that the others were already there ('Group sdfiles already exists.')" "$LOGT" "Group sdfiles already exists."
    expect_lacks "U5 and it did not say sdfiles was created" "$LOGT" "Creating group: sdfiles."
  else
    say "  (no --install-log: the installer's own wording is not checked, only the group file)"
  fi
  wl_summary; exit $?
  ;;
# ------------------------------------------------------------------
before-delete)
  say ""; say "== before the uninstaller =="
  for g in $GROUPS4; do wl_group_exists "$g" || say "  NOTE: $g does not exist now - the removal rows for it will say so"; done
  save_state delete-before
  say ""
  say "  NEXT, by you, not by this script:"
  say "      bash /home/don/Projects/SDCore4Linux/deletesdcore.sh      (answer DELETE to remove the accounts, or the keep word to keep them)"
  say "  then:  sudo bash $SELF after-delete --accounts delete|keep --delete-log FILE"
  exit 0
  ;;
# ------------------------------------------------------------------
after-delete)
  need_saved delete-before
  case $ACCOUNTS in keep|delete) ;; *) need "--accounts keep|delete is needed: say which branch of the uninstaller you ran" ;; esac
  say ""; say "== after the uninstaller ($ACCOUNTS the accounts) =="; show_groups
  for g in $GROUPS4; do
    was=$(saved delete-before "$g")
    if [ "$(exists_of "$was")" = absent ]; then say "  (NOTE: $g did not exist before the uninstaller, so its row proves nothing about removal)"; continue; fi
    if [ "$ACCOUNTS" = delete ]; then
      if wl_group_exists "$g"; then fail "D1 $g is still in the group file after a full DELETE (members: $(members_sorted "$g"))"; else pass "D1 $g is gone from the group file after a full DELETE"; fi
    else
      expect_eq "D2 $g is exactly as it was after the uninstaller kept the accounts (existence and members)" "$(grp_desc "$g")" "$was"
    fi
  done
  SAVED_COUNT=0
  for g in $GROUPS4; do [ "$(exists_of "$(saved delete-before "$g")")" = exists ] && SAVED_COUNT=$((SAVED_COUNT+1)); done
  [ "$SAVED_COUNT" -gt 0 ] && pass "D0 the baseline held $SAVED_COUNT of the four groups (so the rows above compared something)" || fail "D0 none of the four groups existed before: the removal rows measured nothing"
  if [ "$ACCOUNTS" = delete ]; then
    getent group sdusers >/dev/null 2>&1 && say "  (sdusers still exists: it is not one of the four and this script does not judge it)"
  fi
  if [ -n "$DELETE_LOG" ]; then
    [ -r "$DELETE_LOG" ] || need "the delete log $DELETE_LOG cannot be read"
    LOGT=$(sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\r//g' "$DELETE_LOG")
    if [ "$ACCOUNTS" = delete ]; then
      for g in $GROUPS4; do
        if [ "$(exists_of "$(saved delete-before "$g")")" = exists ]; then expect_has "D3 the remover said it took $g out" "$LOGT" "Removed group $g (the accounts went with it)."; fi
      done
    else
      expect_has "D3 the remover said the route groups were kept" "$LOGT" "sd ACCOUNTS were saved, so the route groups sdssh, sdapi, sdfiles, sdfileswrite and sdfilesadmin were kept."
      expect_lacks "D3 and it did not say it removed any" "$LOGT" "(the accounts went with it)"
    fi
  else
    say "  (no --delete-log: the remover's own wording is not checked, only the group file)"
  fi
  wl_summary; exit $?
  ;;
*)
  need "unknown MODE '$MODE' (arrange-upgrade | after-upgrade | before-delete | after-delete | status)"
  ;;
esac
