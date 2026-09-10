#!/bin/bash
#
# ssh-forcecommand.sh - the ssh half of the tier boundary for SD Core for Linux.
#
# START-HISTORY:
# 10 Sep 26 dm  Written for PRE_RELEASE 13, the owner's ruling of 9 Sep 2026: a
#               STANDARD account does not get a real login shell, the tier is a
#               BOUNDARY, and SD writes sshd_config to hold it.  Mechanism ruled
#               the same day: a fenced "Match Group sdusers,!sdadmin" block that
#               ForceCommands every non-administrator SD account into sd.
# END-HISTORY
#
# START-DESCRIPTION:
#
# THE HOLE IT CLOSES.  An SD account is an ordinary Unix user with a login shell
# (CREATEA runs usermod -aG sdusers on an account adduser already made).  The
# installer installs an ssh server.  So a STANDARD account that SD denies SH and
# ! inside SD just ssh's in and gets a shell, never entering SD - the tier
# boundary does not reach the edge of the machine.  The Windows port measured
# this exact failure on 21 Aug 2026; PRE_RELEASE 13 carries the detail.
#
# THE MECHANISM, and why this shape.  A fenced block appended to sshd_config:
#
#     Match Group sdusers,!sdadmin
#         ForceCommand /usr/local/sdsys/bin/sd
#
# The negation matches a member of sdusers who is NOT in sdadmin - every
# non-administrator SD account.  PROGRAMMER is treated as STANDARD over ssh
# (owner, 9 Sep 26): the tiers are told apart by the in-SD permission model
# (PRE_RELEASE 23), not by sshd.  Administrators are in sdadmin, the negation
# excludes them, and that is their full ssh access.  root is not in sdusers, so
# root ssh is untouched.
#
# WHY ForceCommand AND NOT AllowGroups.  AllowGroups decides who may AUTHENTICATE
# and locks everyone out if its group is empty or misnamed - the port's sharpest
# lock-out.  ForceCommand cannot lock anyone out of authentication: it only
# changes WHAT RUNS once a non-admin SD user is in, and an administrator (excluded
# by !sdadmin) always keeps a real shell to recover with.  That is the fail-safe
# that makes this the least dangerous of the three mechanisms considered.
#
# WHY sd IS NOT setuid AND THIS STILL WORKS.  sd is not setuid (system(27) =
# getuid()), so an admin-granted non-admin (MODIFY.ACCOUNT SH-ON, PRE_RELEASE 23)
# who ssh's in lands in sd by ForceCommand and then SH gives them a shell AS
# THEMSELVES.  The grant lives entirely inside SD's permission model, so the
# fenced block stays one uniform group rule and needs no per-account carve-out.
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
#
# Exit 0 done (or nothing to do), 1 failed, 2 refused.
#
# TESTING SURFACE.  Point SD_SSHD_CONFIG at a scratch file and SD_SSHD_BIN at a
# stub to drive --install/--remove with no root and no real sshd; that is what
# gplbld/test-ssh-forcecommand.py drives.  When SD_SSHD_CONFIG is left at the
# real /etc/ssh/sshd_config, root is required and the service is reloaded; with
# it overridden, neither happens.
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

# The four-line block, as an array so the writer and the test agree on it.
block_lines() {
  printf '%s\n' "$BEGIN" "Match Group sdusers,!sdadmin" "    ForceCommand $SD_BIN" "$END"
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
    /^[[:space:]]*Match([[:space:]]|$)/ && (/sdusers/ || /sdadmin/) {
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
  if has_block; then say "SD block present  yes (before)"; else say "SD block present  no (before)"; fi
}

print_block() {
  say "the block it writes:"
  block_lines | sed 's/^/    /'
}

# ------------------------------------------------------------------------ main

MODE=${1:-}
[[ -n $MODE ]] || die "no mode; want --check, --install or --remove"

case $MODE in

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
    say "INSTALLED - non-administrator SD accounts are forced into sd over ssh"
    say "original kept at $BACKUP"
    production && reload_sshd
    exit 0
    ;;

  *)
    die "unknown mode '$MODE'; want --check, --install or --remove"
    ;;
esac
