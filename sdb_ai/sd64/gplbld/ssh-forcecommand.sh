#!/bin/bash
#
# ssh-forcecommand.sh - the ssh half of the SD boundary for SD Core for Linux.
#
# START-HISTORY:
# 20 Sep 26 dm S.29 part 3: THE BLOCK NOW READS sdssh, AND THIS SCRIPT IS ALSO
#           THE REFUSAL.  Parts 1 and 2 made sdssh membership the ssh route and
#           gave MODIFY.ACCOUNT the words to change it; nothing read the group,
#           so NONE was reported and not enforced.  A third Match arm, written
#           FIRST so sshd's first-obtained-value rule picks it, sends an sdusers
#           member who is not in sdssh to "--refuse" instead of to sd, and shuts
#           the forwarding channels for that arm so "no ssh route" also means no
#           tunnel.  --refuse prints message 10074 and exits 1.
# 18 Sep 26 dm TEARDOWN (S.28).  The sdadmin split is gone: every sdusers
#           member is forced into sd over ssh, and the sdsys OS account is
#           denied network login outright - SDSYS is entered only from a local
#           session (W.6).
# 10 Sep 26 dm  Written for PRE_RELEASE 13, the owner's ruling of 9 Sep 2026: a
#               STANDARD account does not get a real login shell, the tier is a
#               BOUNDARY, and SD writes sshd_config to hold it.  Mechanism ruled
#               the same day: a fenced "Match Group sdusers,!sdadmin" block that
#               ForceCommands every non-administrator SD account into sd.
# END-HISTORY
#
# START-DESCRIPTION:
#
# WHAT THE BLOCK IS NOW.  Three arms: sdsys is denied network login outright,
# an SD account WITHOUT the ssh route is refused as soon as it connects, and
# every other SD account is ForceCommanded into sd.
#
#     Match User sdsys
#         DenyUsers sdsys
#     Match Group sdusers,!sdsys,!sdssh
#         ForceCommand /usr/local/sbin/ssh-forcecommand --refuse
#         AllowTcpForwarding no
#         AllowStreamLocalForwarding no
#         AllowAgentForwarding no
#         PermitTunnel no
#     Match Group sdusers,!sdsys
#         ForceCommand /usr/local/sdsys/bin/sd
#
# MEMBERSHIP OF sdssh IS THE ssh ROUTE (S.29, the owner's ruling of 18/19 Sep
# 2026 relayed by the port).  CREATE.ACCOUNT joins the group by default and
# MODIFY.ACCOUNT <acc> SSH|API|BOTH|NONE takes it away and gives it back; this
# block is what makes those words mean something at the door.
#
# ORDER IS LOAD-BEARING AND IT IS THE ONE THING TO GET WRONG HERE.  sshd uses
# the FIRST obtained value for a keyword, so the narrow ,!sdssh arm must come
# BEFORE the general arm or every SD account gets sd and the route is bookkeeping
# again.  The two arms are mutually exclusive in intent but not in sshd's
# matching: both match a non-member, and only the order parts them.
#
# AN ALLOW GROUP, SO A MISSING sdssh REFUSES EVERY SD ACCOUNT rather than
# admitting every one: !sdssh matches when the group does not exist.  That is
# the direction part 1 chose on the port's objection (a deny group fails OPEN),
# and it is why sd-elevate will not delete sdssh.  It is not a login lock-out:
# root and non-SD users are untouched, and the refused account is told why.
#
# AND THE REFUSAL ARM SHUTS FORWARDING, which ForceCommand alone does not.
# ForceCommand replaces the command; it leaves -L, -R, -D, agent forwarding and
# PermitTunnel working, so without those four lines an account with NO ssh route
# could still open a tunnel through this host.  "No route" has to mean no route.
#
# SDSYS IS DENIED AT sshd, NOT LEFT TO SD ALONE.  CPROC and LOGIN both refuse a
# non-local sdsys session (W.6, the SSH_CONNECTION/SSH_TTY test), but a real
# login shell on the sdsys OS account would still be a remote shell on the
# administrator account - so sshd denies it first, and SD's own gates are the
# second half of the door.  root is not in sdusers, so root ssh is untouched.
#
# WHY ForceCommand AND NOT AllowGroups.  AllowGroups decides who may AUTHENTICATE
# and locks everyone out if its group is empty or misnamed - the port's sharpest
# lock-out.  ForceCommand cannot lock anyone out of authentication: it only
# changes WHAT RUNS once an SD user is in.  DenyUsers for the one account is the
# smallest possible deny list, and the only one that can exist after the
# teardown.
#
# THE ONE THING THIS BLOCK CANNOT WIN AGAINST: sshd processes DenyUsers before
# AllowUsers, so a pre-existing "AllowUsers sdsys" (or an AllowGroups that
# includes sdsys) lets sdsys authenticate regardless.  The helper does not
# police Allow* directives - they are the administrator's own policy.  SD's
# second half of the door (CPROC and LOGIN refuse a non-local sdsys session,
# W.6) still holds.
#
# NOTHING HERE IS DISTRIBUTION-SPECIFIC, deliberately: the other three distro
# families come back (owner, 10 Sep 26).  /etc/ssh/sshd_config is the universal
# OpenSSH path on Linux; the sshd_config.d drop-in directory is NOT universal, so
# it is not used.  The sshd binary is discovered rather than assumed, and the
# service is reloaded under both the "ssh" (Debian/Ubuntu) and "sshd"
# (Arch/Fedora/openSUSE) unit names.
#
# LOCK-OUT-SENSITIVE, so three rules are not optional:
#   1. A candidate file is validated with `sshd -t -f` BEFORE it replaces the
#      live config - the live file is never in a bad state even momentarily.
#   2. If no sshd binary can be found to validate with, it REFUSES rather than
#      writing an unchecked config.  No verdict from a check that did not run.
#   3. The original is copied to sshd_config.before-sd once, so there is always
#      a hand path back.
#
# INSTRUMENT RULE.  It prints the resolved config path, the resolved sshd used
# for validation, the ForceCommand target, and the exact block; it reports the
# block's presence BEFORE and AFTER; and --install confirms the block is really
# in the file before claiming success, so a write that silently did nothing
# fails rather than passes.
#
#   ssh-forcecommand.sh --check     print what it would do, touch nothing, no root
#   ssh-forcecommand.sh --install   write the block, validate, reload sshd
#   ssh-forcecommand.sh --remove    take SD's block back out, validate, reload
#   ssh-forcecommand.sh --refuse    the refusal arm's ForceCommand: say 10074, exit 1
#
# Exit 0 done (or nothing to do), 1 failed (and --refuse), 2 refused.
#
# WHY --refuse LIVES HERE rather than in a second installed file: the policy and
# the refusal it implies are one decision, and the installer already puts this
# script at /usr/local/sbin/ssh-forcecommand, root:root 0755, before the block is
# written.  A second file would be a second thing to install, a second thing to
# get the mode of, and a second thing for a later session to find.
#
# ***--refuse READS THE MESSAGE FILE; IT DOES NOT CARRY A COPY OF THE TEXT.***
# /usr/local/sdsys/messages/10074 is the one source, world-readable, with %1
# replaced by the login name - so the wording an ssh user sees and the wording an
# SD session sees cannot drift.  If the file cannot be read it STILL REFUSES,
# naming the file it wanted: a refusal that fails open is not a refusal.
#
# TESTING SURFACE.  Point SD_SSHD_CONFIG at a scratch file and SD_SSHD_BIN at a
# stub to drive --install/--remove with no root and no real sshd; that is what
# gplbld/test-ssh-forcecommand.py drives.  SD_SSH_REFUSE_BIN names the command
# the refusal arm points at and SD_MESSAGE_DIR the directory --refuse reads
# 10074 from.  When SD_SSHD_CONFIG is left at the real /etc/ssh/sshd_config, root
# is required and the service is reloaded; with it overridden, neither happens.
#
# END-DESCRIPTION
#

set -uo pipefail

PROG=${0##*/}

# ---------------------------------------------------------------- configuration

# The config we edit.  Overridable only for the test harness; the real path is
# the default and the only one that triggers the root check and the reload.
CONFIG=${SD_SSHD_CONFIG:-/etc/ssh/sshd_config}
REAL_CONFIG=/etc/ssh/sshd_config
BACKUP="$CONFIG.before-sd"

# Where the installed sd is.  installsdai.sh installs it here regardless of
# distribution, and symlinks /usr/local/bin/sd to it.  The canonical target is
# used so the block does not depend on PATH at ssh-login time.
SD_BIN=${SD_SSH_FORCECOMMAND:-/usr/local/sdsys/bin/sd}

# Where the refusal arm's command lives - this same script, as the installer
# puts it (installsdai.sh installs gplbld/ssh-forcecommand.sh there before it
# writes the block).  Named rather than derived from $0 on purpose: the block
# must carry the INSTALLED path, and $0 is the repository copy when the
# installer or the unit test runs it from gplbld/.
REFUSE_BIN=${SD_SSH_REFUSE_BIN:-/usr/local/sbin/ssh-forcecommand}

# Where --refuse reads message 10074 from.  The installed message directory,
# world-readable, is the single source of the wording.
MSG_DIR=${SD_MESSAGE_DIR:-/usr/local/sdsys/messages}

# Fence markers.  Comments, so they are inert to sshd; exactly these strings are
# matched on removal, so re-running replaces our block rather than stacking.
BEGIN='# --- BEGIN SD ssh-only model (PRE_RELEASE 13) - do not edit within this fence ---'
END='# --- END SD ssh-only model ---'

# ------------------------------------------------------------------- utilities

say()  { printf '%s: %s\n' "$PROG" "$1"; }
fail() { printf '%s: FAILED - %s\n'  "$PROG" "$1" >&2; exit 1; }
die()  { printf '%s: REFUSED - %s\n' "$PROG" "$1" >&2; exit 2; }

# Find an sshd to validate with.  REFUSE rather than skip validation: an
# unchecked sshd_config is the lock-out this whole script exists to avoid.
# If SD_SSHD_BIN is set it is authoritative - exactly that binary, or nothing -
# which both lets the installer pin it and lets the test drive the "no sshd
# found" refusal by setting it empty.
find_sshd() {
  local c
  if [[ -n ${SD_SSHD_BIN+set} ]]; then
    [[ -n $SD_SSHD_BIN && -x $SD_SSHD_BIN ]] && { printf '%s' "$SD_SSHD_BIN"; return 0; }
    return 1
  fi
  for c in /usr/sbin/sshd /usr/bin/sshd /sbin/sshd; do
    [[ -x $c ]] && { printf '%s' "$c"; return 0; }
  done
  c=$(command -v sshd 2>/dev/null) && [[ -n $c ]] && { printf '%s' "$c"; return 0; }
  return 1
}

# The block, as one list so the writer and the test agree on it.  The ,!sdssh
# arm is SECOND on purpose - sshd takes the first obtained value for a keyword,
# so the narrow arm has to precede the general one (see the description).
block_lines() {
  printf '%s\n' "$BEGIN" \
    "Match User sdsys" \
    "    DenyUsers sdsys" \
    "Match Group sdusers,!sdsys,!sdssh" \
    "    ForceCommand $REFUSE_BIN --refuse" \
    "    AllowTcpForwarding no" \
    "    AllowStreamLocalForwarding no" \
    "    AllowAgentForwarding no" \
    "    PermitTunnel no" \
    "Match Group sdusers,!sdsys" \
    "    ForceCommand $SD_BIN" \
    "$END"
}

# --refuse: what the sdssh-less arm runs.  Message 10074 with %1 replaced by the
# login name, on stderr (stdout of a ForceCommand can be consumed by a client
# that asked for a command), and a non-zero exit so the ssh client reports
# failure rather than a clean session that did nothing.
#
# IT REFUSES WHETHER OR NOT IT CAN READ THE MESSAGE.  The exit code is the
# refusal; the text is a courtesy.  Naming the missing file is what turns "ssh
# closed with a blank error" into something an administrator can act on.
refuse_now() {
  local who=${USER:-$(id -un 2>/dev/null)} msg=$MSG_DIR/10074
  if [[ -r $msg ]]; then
    sed -e "s|%1|${who:-this account}|g" -- "$msg" >&2
  else
    printf 'ssh refused for %s: no SD ssh route, and %s could not be read to say so properly\n' \
      "${who:-this account}" "$msg" >&2
  fi
  exit 1
}

# Print the config with any existing SD fence removed.  Exact inverse of the
# append below: BEGIN through END inclusive, and nothing else, comes out.  No
# blank-line handling games - the block carries no blank line, so round trips
# are byte-stable (the port learned this one the hard way, its entry 14).
strip_block() {
  awk -v b="$BEGIN" -v e="$END" '
    $0 == b { drop = 1; next }
    $0 == e { drop = 0; next }
    !drop   { print }
  ' "$CONFIG"
}

# Does the live config already carry our fence?
has_block() {
  [[ -f $CONFIG ]] && grep -qxF "$END" "$CONFIG"
}

# What, outside our own fence, conflicts with the block.  Two things do: a
# ForceCommand already in force (global or any Match), and a Match rule that
# already names one of our groups.  Either means the administrator has taken
# control of exactly what we would write, and the ruling is to REFUSE and say
# so rather than edit their policy silently.  Connection restrictions
# (AllowGroups/DenyGroups/...) are deliberately NOT treated as conflicts: a
# trailing ForceCommand Match block composes with them without contradiction.
# This predicate is the judgment call inside the ruling; it is stated here so a
# later session can widen or narrow it deliberately.
existing_conflict() {
  strip_block | awk '
    /^[[:space:]]*ForceCommand([[:space:]]|$)/ {
      print "a ForceCommand directive is already present: " $0; found = 1
    }
    /^[[:space:]]*Match([[:space:]]|$)/ && (/sdusers/ || /sdsys/) {
      print "a Match rule already names an SD group: " $0; found = 1
    }
    END { exit (found ? 0 : 1) }
  '
}

# Validate a candidate file with sshd -t -f.  Returns 0 / non-zero and leaves
# the reason on stdout for the caller to surface.
validate() {
  local sshd=$1 file=$2
  "$sshd" -t -f "$file" 2>&1
}

reload_sshd() {
  # Only on the real path.  Reload, not restart: existing sessions keep running
  # (so this cannot drop the administrator who is running the install), and new
  # connections pick up the block.  Both unit names, because the service is
  # "ssh" on Debian/Ubuntu and "sshd" elsewhere.
  local unit
  for unit in ssh sshd; do
    if systemctl is-active --quiet "$unit" 2>/dev/null; then
      if systemctl reload "$unit" 2>/dev/null; then
        say "reloaded $unit.service"
      else
        say "could not reload $unit.service; the block applies on its next start"
      fi
      return 0
    fi
  done
  say "sshd is not running; the block applies whenever it next starts"
}

# Write $1 (a file) over the live config, keeping the config's own mode/owner by
# overwriting content in place.  Backs the original up once.
commit_file() {
  local src=$1
  [[ -f $BACKUP ]] || cp -- "$CONFIG" "$BACKUP"
  cp -- "$src" "$CONFIG"
}

production() { [[ $CONFIG == "$REAL_CONFIG" ]]; }

# --------------------------------------------------------------------- reports

report_target() {
  say "config            $CONFIG"
  say "ForceCommand ->   $SD_BIN"
  say "no-sdssh arm ->   $REFUSE_BIN --refuse"
  say "10074 read from   $MSG_DIR"
  if has_block; then say "SD block present  yes (before)"; else say "SD block present  no (before)"; fi
}

print_block() {
  say "the block it writes:"
  block_lines | sed 's/^/    /'
}

# ------------------------------------------------------------------------ main

MODE=${1:-}
[[ -n $MODE ]] || die "no mode; want --check, --install, --remove or --refuse"

case $MODE in

  # First, because this is the mode an ordinary ssh login runs: nothing above
  # it in this case statement, and nothing before it that needs root or a
  # readable sshd_config.
  --refuse)
    refuse_now
    ;;

  --check)
    report_target
    print_block
    if [[ ! -f $CONFIG ]]; then
      say "no $CONFIG yet - sshd has not written one; --install will refuse until it has"
      exit 0
    fi
    if has_block; then
      say "would replace the existing SD block (idempotent)"
    elif conflict=$(existing_conflict); then
      say "would REFUSE: $conflict"
      exit 2
    else
      say "would append the block"
    fi
    exit 0
    ;;

  --remove)
    if production && [[ ${EUID:-$(id -u)} -ne 0 ]]; then
      die "must run as root to edit $CONFIG"
    fi
    if [[ ! -f $CONFIG ]]; then
      say "no $CONFIG present, nothing to remove"
      exit 0
    fi
    if ! has_block; then
      say "no SD block present, nothing removed"
      exit 0
    fi
    sshd=$(find_sshd) || die "no sshd binary found to validate the result with; refusing to edit $CONFIG blind"
    tmp=$(mktemp) || fail "could not create a temp file"
    trap 'rm -f "$tmp"' EXIT
    strip_block > "$tmp"
    if ! out=$(validate "$sshd" "$tmp"); then
      fail "sshd -t rejected the config with our block removed (leaving it in place). sshd said: ${out:-<nothing>}"
    fi
    commit_file "$tmp"
    has_block && fail "removal did not take - the block is still in $CONFIG"
    say "REMOVED - SD ssh-only block is out of $CONFIG"
    production && reload_sshd
    exit 0
    ;;

  --install)
    if production && [[ ${EUID:-$(id -u)} -ne 0 ]]; then
      die "must run as root to edit $CONFIG"
    fi
    # Refuse to point ForceCommand at an sd that is not there: a block naming a
    # missing binary would let a non-admin authenticate and then fail instantly,
    # which reads as a lock-out.  In production sd is installed before this runs.
    [[ -x $SD_BIN ]] || die "sd binary $SD_BIN is missing or not executable; not writing a ForceCommand to it"
    # The same rule for the refusal arm, and for the same reason turned round:
    # a ForceCommand naming a command that is not there closes the connection
    # with no explanation, so the account cannot tell a withdrawn ssh route
    # from a broken installation.  20 Sep 26, S.29 part 3.
    [[ -x $REFUSE_BIN ]] || die "refusal command $REFUSE_BIN is missing or not executable; not writing a ForceCommand to it"
    if [[ ! -f $CONFIG ]]; then
      die "no $CONFIG - the ssh server has not written its config yet; install and start it first"
    fi
    # Preflight: an existing block is ours to replace; a real conflict is the
    # administrator's policy and we refuse it.
    if ! has_block; then
      if conflict=$(existing_conflict); then
        die "$conflict - refusing to edit a customised sshd_config; remove the conflict or write the block by hand"
      fi
    fi
    sshd=$(find_sshd) || die "no sshd binary found to validate the result with; refusing to edit $CONFIG blind"
    say "validating with  $sshd -t -f"
    report_target
    tmp=$(mktemp) || fail "could not create a temp file"
    trap 'rm -f "$tmp"' EXIT
    # Strip any prior block, then append ours at EOF.  A Match block runs to the
    # next Match or to EOF, so appending keeps it self-contained after every
    # global directive and after any Match blocks the administrator already has.
    { strip_block; block_lines; } > "$tmp"
    if ! out=$(validate "$sshd" "$tmp"); then
      fail "sshd -t rejected the candidate (the live config is untouched). sshd said: ${out:-<nothing>}"
    fi
    commit_file "$tmp"
    has_block || fail "the block was validated but is not in $CONFIG after the write"
    say "INSTALLED - SD accounts with the sdssh route are forced into sd over ssh;"
    say "            an SD account without it is refused (10074); sdsys is denied network login"
    say "original kept at $BACKUP"
    production && reload_sshd
    exit 0
    ;;

  *)
    die "unknown mode '$MODE'; want --check, --install, --remove or --refuse"
    ;;
esac
