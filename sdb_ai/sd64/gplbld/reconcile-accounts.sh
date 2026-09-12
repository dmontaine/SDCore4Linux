#!/usr/bin/env bash
#
# reconcile-accounts.sh - find the ACCOUNTS records whose Linux user has gone,
#                         and (with --sweep) remove them and their directories.
#
#   bash gplbld/reconcile-accounts.sh              report, change nothing
#   bash gplbld/reconcile-accounts.sh --sweep      remove them (needs root)
#   bash gplbld/reconcile-accounts.sh --sdsys DIR --accounts-root DIR
#
# Exit 0 the register is clean, 1 something stale is still there (reported, or
# refused, or it would not go), 2 the question could not be answered.
#
# PORT_ADOPTION 19; the port's gplbld/reconcile-accounts.ps1 and its
# PRE_RELEASE_FIXES 93 and 65.
#
# WHAT IS WRONG.  @SDSYS/ACCOUNTS is the account register and nothing ever
# reconciles it against the operating system.  A Linux user can be removed from
# OUTSIDE SD - userdel, a decommission script, a directory change - and nothing
# in SD is consulted, so the record outlives the user.  LIST SD.ACCOUNTS then
# answers wrongly, and CREATE.ACCOUNT refuses to recreate the name: true of the
# record and false of the world.
#
# THE RULING IS ON THE FILE, NOT ON ITS READERS.  Owner to the port, 1 Sep 2026:
# "the ACCOUNTS directory should contain no deleted accounts - there should be
# NO invalid records in it."  So this is not a reconcile-on-read and not a
# truer message at one caller: the register is the inventory, and an inventory
# with invalid rows is wrong however it is read.
#
# ***AND REMOVING THE DIRECTORY IS NOT A HARD CALL, BECAUSE THE MODEL ALREADY
# HAS A PLACE FOR "KEEP THE DATA".***  Owner, 12 Sep 2026: "this is why
# suspended accounts exist - you want to retain data, suspend the account; you
# want everything deleted, delete the account."  A stale record means somebody
# DELETED the Linux user, which is the second of those, so taking the directory
# with it is carrying out the intent rather than destroying something a person
# meant to keep.  ***SO THE ONLY QUESTION THIS FILE HAS TO GET RIGHT IS "IS THE
# USER REALLY GONE", NOT "SHOULD A GONE USER'S DIRECTORY GO"*** - which is why
# every guard below is about the reliability of that one lookup, and none of
# them is about second-guessing the removal.
#
# ======================================================================
#   THE LINUX HAZARD THE PORT DOES NOT HAVE - READ THIS BEFORE --sweep
# ======================================================================
#
# ***SD'S OWN IDEA OF "THIS USER EXISTS" IS NARROWER THAN THE SYSTEM'S, AND THE
# GAP IS INVISIBLE UNTIL IT IS NOT.***  !is_user (GPL.BP/IS_USER:52) does
# openpath "/etc" and reads "passwd" DIRECTLY.  It never consults NSS.  This
# machine's /etc/nsswitch.conf reads "passwd: files systemd sss" and sssd is
# ENABLED though currently inactive (measured 12 Sep 2026), so a domain-joined
# install has users that the system resolves and SD cannot see at all.
#
# A sweep keyed on SD's view would therefore mark EVERY directory-backed
# account stale and delete its directory.  That is the expensive version of
# PRE_RELEASE 96's defect, and it is why this file asks TWO sources and acts
# only when they agree that the user is gone:
#
#   getent says yes, /etc/passwd says yes   live, not stale
#   getent says no,  /etc/passwd says no    definitely absent - the only
#                                           case that is ever acted on
#   getent says yes, /etc/passwd says no    directory-backed user: the system
#                                           has them and SD cannot see them.
#                                           REFUSED, and reported, because it
#                                           is a real problem of its own
#   getent fails / disagrees the other way  could not tell.  REFUSED
#
# ======================================================================
#   THE THREE RULES CARRIED FROM THE PORT
# ======================================================================
#
# 1. AN ACCOUNT WITH NO LINUX USER IS NOT NECESSARILY A STALE ACCOUNT, AND THE
#    REGISTER SAYS SO ITSELF.  CREATE.ACCOUNT has three types and only USER has
#    a login.  ACC$GROUP (field 3) is "sdu_<login>" for a USER account and the
#    group's own name otherwise, so it identifies the type AND carries the
#    login.  SDSYS's record says "sdsys" and is exempt by that rule rather than
#    by its name - the name is checked too, as a second row, because the port's
#    own first attempt marked SDSYS dead.
#
# 2. "I COULD NOT TELL" IS NOT "NO".  Every lookup reports three states and
#    only the middle one is acted on.  There is a control as well: the account
#    enumeration must succeed and be plausibly sized before any verdict is
#    believed, because a machine with almost no accounts does not exist and an
#    empty answer is a broken instrument rather than an empty register.
#
# 3. BOTH HALVES OR NEITHER, AND THE DIRECTORY FIRST.  The record is the only
#    handle anything else has on the directory, so removing it first would
#    strand a directory nobody can find again.  A record whose directory would
#    not go is kept and reported, and the next run tries again.
#
# WHAT IT REFUSES TO TOUCH - each skipped BY NAME, never in silence, so the next
# run reports it again rather than a person having to notice a quiet:
#
#   the lookup did not complete             a name service that is down
#   the two sources disagree                directory-backed, or worse
#   the record id is an escaped file name   %E/%G/%L, not decoded here
#   ACC$GROUP does not begin sdu_           GROUP, OTHER, SDSYS: no login
#   the account is named SDSYS              the same, said by name
#   the user still resolves                 not stale at all
#   field 1 is not <root>/<id downcased>    a record pointing somewhere else
#   the path IS the accounts root           or the root itself
#
# WHAT IT DELIBERATELY DOES NOT DO.  The sdu_<name> GROUP is left alone: the
# ruling names the record and the directory, a group is not part of the
# register, and over-deleting as root is the worse failure.  A surviving group
# is reported against the record and left for a person.
#
# START-HISTORY:
# 12 Sep 26 dm  written.  PORT_ADOPTION 19.
# END-HISTORY

set -u

SDSYS=/usr/local/sdsys
ACCROOT=/home/sd/user_accounts
MODE=list
ALLOW_REMOTE=no

while [[ $# -gt 0 ]]; do
  case $1 in
    --sweep)             MODE=sweep ;;
    --list)              MODE=list ;;
    --allow-remote-nss)  ALLOW_REMOTE=yes ;;
    --sdsys)             shift; SDSYS=${1:-} ;;
    --accounts-root)     shift; ACCROOT=${1:-} ;;
    *) echo "usage: reconcile-accounts.sh [--list|--sweep] [--allow-remote-nss] [--sdsys DIR] [--accounts-root DIR]" >&2; exit 2 ;;
  esac
  shift
done

REG=$SDSYS/ACCOUNTS

echo "reconcile-accounts.sh - PORT_ADOPTION 19"
echo "date          : $(date '+%Y-%m-%d %H:%M:%S')"
echo "register      : $REG"
echo "accounts root : $ACCROOT"
echo "mode          : $MODE"
echo ""

[[ -d $REG ]] || { echo "CANNOT ANSWER: no register at $REG"; exit 2; }

# THE TEST IS "CAN I WRITE THE REGISTER", NOT "AM I ROOT", AND THAT IS
# DELIBERATE.  The real register is root-owned, so in practice this still means
# root - but a caller who can already write it could remove records with rm, so
# demanding uid 0 would add no safety, only a misleading error.  What it buys
# is that --sweep can be exercised against a fixture tree the caller owns,
# which is the only way the REMOVAL path gets tested at all before it is
# pointed at somebody's accounts.
if [[ $MODE == sweep && ! -w $REG ]]; then
  echo "CANNOT ANSWER: --sweep removes directories and register records, and"
  echo "$REG is not writable by $(id -un).  Run it as root."
  echo "--list needs no privilege."
  exit 2
fi

# Rule 2's control.  A machine with almost no accounts is a broken instrument,
# not an empty register, and every verdict below rests on this enumeration.
ENUM=$(getent passwd 2>/dev/null | wc -l)
if [[ $ENUM -lt 10 ]]; then
  echo "CANNOT ANSWER: 'getent passwd' returned $ENUM entries.  That is not a"
  echo "real machine's account list, so no verdict below would be worth having."
  exit 2
fi
echo "control       : getent passwd returned $ENUM entries"

# ======================================================================
#   THE BOOT-TIME GUARD.  READ THIS BEFORE REMOVING IT.
# ======================================================================
#
# ***THE PER-RECORD TWO-SOURCE TEST IS NOT ENOUGH WHEN THIS RUNS AT BOOT.***
# sd.service calls this from ExecStartPre, which can run BEFORE a directory
# service is up.  A user who lives only in LDAP is then absent from NSS *and*
# absent from /etc/passwd - which is exactly the signature this file treats as
# "definitely gone" - so the sweep would delete their account directory because
# sssd had not started yet.  No per-record test can tell that apart from a real
# removal, because the two states are byte-for-byte identical.
#
# So the question is asked one level up: is a REMOTE name source configured at
# all?  If it is, "both sources say absent" stops being conclusive and this
# reports instead of removing.  On a files-only machine - which is what the
# installer targets - nothing changes and the sweep runs as ruled.
#
# --allow-remote-nss overrides it, for an administrator who knows the directory
# is up and wants the sweep anyway.
NSSLINE=$(grep -E '^[[:space:]]*passwd:' /etc/nsswitch.conf 2>/dev/null | head -1)
NSSREMOTE=""
for src in $(printf '%s' "${NSSLINE#*:}"); do
  case $src in
    files|systemd|compat|db|cache|[\[]*|*[\]]) : ;;
    *) NSSREMOTE="$NSSREMOTE $src" ;;
  esac
done

if [[ -n $NSSREMOTE ]]; then
  echo "name sources  :${NSSREMOTE} (remote) as well as files"
  if [[ $MODE == sweep && $ALLOW_REMOTE == no ]]; then
    echo ""
    echo "REFUSING TO SWEEP:${NSSREMOTE} can serve users that are in no local"
    echo "file, and this may be running before that service is up - at boot it"
    echo "usually is.  A directory user would then look absent in BOTH sources,"
    echo "which is the one signature this treats as gone, and their account"
    echo "directory would be deleted because a name service was slow."
    echo "Reporting instead.  Pass --allow-remote-nss to sweep anyway."
    MODE=list
  fi
else
  echo "name sources  : local files only"
fi
echo ""

stale=0; refused=0; live=0; removed=0; kept=0

for id in $(ls "$REG" 2>/dev/null | sort); do
  rec=$REG/$id
  [[ -f $rec ]] || continue

  path=$(sed -n '1p' "$rec")
  grp=$(sed -n '3p' "$rec")

  # An escaped file name is a record id this cannot decode.
  if [[ $id == *%* ]]; then
    echo "SKIP  $id - escaped record id, not decoded here"; refused=$((refused+1)); continue
  fi
  if [[ ${id^^} == SDSYS ]]; then
    echo "SKIP  $id - SDSYS, exempt by name"; refused=$((refused+1)); continue
  fi
  if [[ $grp != sdu_* ]]; then
    echo "SKIP  $id - group '$grp' is not sdu_, so not a USER account"; refused=$((refused+1)); continue
  fi

  user=${grp#sdu_}

  # Two sources.  Only "both say absent" is ever acted on.
  in_nss=no; getent passwd "$user" >/dev/null 2>&1 && in_nss=yes
  in_files=no; cut -d: -f1 /etc/passwd 2>/dev/null | grep -qx -- "$user" && in_files=yes

  if [[ $in_nss == yes && $in_files == yes ]]; then
    echo "LIVE  $id - user '$user' resolves"; live=$((live+1)); continue
  fi
  if [[ $in_nss == yes && $in_files == no ]]; then
    echo "SKIP  $id - user '$user' resolves through NSS but is NOT in /etc/passwd."
    echo "      A directory-backed user: the system has them and SD's !is_user"
    echo "      cannot see them.  Refused here, and worth fixing separately."
    refused=$((refused+1)); continue
  fi
  if [[ $in_nss == no && $in_files == yes ]]; then
    echo "SKIP  $id - user '$user' is in /etc/passwd but NSS will not resolve it."
    echo "      The sources disagree, so this cannot be called stale."
    refused=$((refused+1)); continue
  fi

  # Both say absent.
  stale=$((stale+1))
  echo "STALE $id - user '$user' is gone from both /etc/passwd and NSS"

  want=$ACCROOT/${id,,}
  if [[ $path != "$want" ]]; then
    echo "      KEPT: field 1 is '$path', not '$want' - points elsewhere"
    kept=$((kept+1)); continue
  fi
  if [[ $path == "$ACCROOT" || $path == / ]]; then
    echo "      KEPT: that is the accounts root itself"
    kept=$((kept+1)); continue
  fi
  if getent group "$grp" >/dev/null 2>&1; then
    echo "      NOTE: group '$grp' still exists and is deliberately left alone"
  fi

  if [[ $MODE != sweep ]]; then
    echo "      would remove $path and the register record (run with --sweep)"
    kept=$((kept+1)); continue
  fi

  # Rule 3: the directory first, because the record is the only handle on it.
  if [[ -d $path ]]; then
    if rm -rf -- "$path" 2>/dev/null; then
      echo "      removed directory $path"
    else
      echo "      KEPT: directory $path would not go; record left so the next run retries"
      kept=$((kept+1)); continue
    fi
  else
    echo "      no directory at $path"
  fi
  if rm -f -- "$rec" 2>/dev/null; then
    echo "      removed register record $id"
    removed=$((removed+1))
  else
    echo "      KEPT: register record $id would not go"
    kept=$((kept+1))
  fi
done

echo ""
echo "$live live, $stale stale, $refused skipped, $removed removed, $kept left"

if [[ $stale -eq 0 ]]; then
  echo "The register names no account whose Linux user is gone."
  exit 0
fi
[[ $kept -eq 0 && $MODE == sweep ]] && { echo "Every stale record was removed."; exit 0; }
echo "Stale records remain.  Run with --sweep as root, or deal with the"
echo "skipped rows above by hand."
exit 1
