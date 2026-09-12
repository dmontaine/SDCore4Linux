#!/usr/bin/env bash
#
# verify-tier-layer.sh - does every ADMINISTRATOR account hold its tier's whole
#                        VOC layer?  PORT_ADOPTION 16.
#
#   bash gplbld/verify-tier-layer.sh
#
# ***NO SUDO.***  It compiles and runs verify-tier-layer.bp - an ordinary,
# non-$internal program - in your own SD account, and reads the register and
# the account VOCs, all of which a plain session may do.
#
# Exit 0 the walk ran and every ADMINISTRATOR account is complete, 1 at least
# one is SHORT, 2 the question could not be answered (no install, no account,
# BP in use, the probe would not compile, or it compiled and did not finish).
# Three answers, as assert-current.py has three and for the same reason: "could
# not measure" is not "nothing is wrong".
#
# WHY IT EXISTS.  Until 11 Sep 2026 the only things that copied the tier layer
# into an account VOC were CREATE.ACCOUNT at creation and MODIFY.ACCOUNT when a
# tier MOVED, so an account quietly fell behind by every verb added to the layer
# after it was made - DON was measured at 10 of 18, missing create.account,
# delete.account, modify.account and update.accounts among them.  LOGIN's
# update.voc now closes that on an upgrade.  Run this before an upgrade and
# after it, and compare.
#
# It stages into <your account>/BP and puts that back exactly as it found it -
# the program, the BP.OUT directory the compiler creates, and the BP.OUT VOC
# record that "rm" does not remove.  It REFUSES to start if BP is not empty,
# rather than clobbering work of yours.

set -u

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SRC=$HERE/verify-tier-layer.bp
SD=/usr/local/sdsys/bin/sd
ACCT=/home/sd/user_accounts/$USER
BP=$ACCT/BP
PROBE=TLPROBE
OUT=$(mktemp)

strip() { sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/\r//g'; }

echo "verify-tier-layer.sh - PORT_ADOPTION 16"
echo "date     : $(date '+%Y-%m-%d %H:%M:%S')"
echo "sd       : $SD"
echo "account  : $ACCT"
echo "probe    : $SRC"
echo ""

[[ -x $SD ]]   || { echo "CANNOT ANSWER: no $SD - is SD installed?"; exit 2; }
[[ -d $ACCT ]] || { echo "CANNOT ANSWER: no SD account directory at $ACCT"; exit 2; }
[[ -d $BP ]]   || { echo "CANNOT ANSWER: no BP file at $BP"; exit 2; }
[[ -f $SRC ]]  || { echo "CANNOT ANSWER: $SRC is missing"; exit 2; }

if [[ -n $(ls -A "$BP" 2>/dev/null) ]]; then
  echo "CANNOT ANSWER: $BP is not empty.  This stages into it and cleans it out"
  echo "afterwards, and will not touch work that is already there:"
  ls -A "$BP" | sed 's/^/    /'
  exit 2
fi

cleanup() {
  rm -f "$BP"/* 2>/dev/null
  rm -rf "$ACCT/BP.OUT" 2>/dev/null
  ( cd "$ACCT" && printf 'DELETE VOC BP.OUT\nCOUNT VOC\nOFF\n' \
      | timeout 60 "$SD" 2>&1 ) | strip | grep -iE 'counted' \
      | sed 's/^/  after cleanup: COUNT VOC /'
  rm -f "$OUT" 2>/dev/null
}
trap cleanup EXIT

cp "$SRC" "$BP/$PROBE"

( cd "$ACCT" && printf 'BASIC BP %s\nRUN BP %s\nOFF\n' "$PROBE" "$PROBE" \
    | timeout 120 "$SD" 2>&1 ) | strip > "$OUT"

# Anchored on the wording only a clean compile prints.
if ! grep -q 'Compiled 1 program(s) with no errors' "$OUT"; then
  echo "CANNOT ANSWER: the probe did not compile, so nothing below is a"
  echo "measurement.  Raw output:"
  grep -vE '^[[:space:]]*$' "$OUT" | tail -15 | sed 's/^/    /'
  exit 2
fi
echo "probe compiled: 0 errors"

# ***AND COMPILING IS NOT RUNNING.***  The first version of this probe compiled
# cleanly and then aborted at a select-list number an ordinary program may not
# use, printing a heading and no verdict.  So the RUN is confirmed on the
# summary line, which only the end of the walk can print.
if ! grep -q 'account(s) in the register' "$OUT"; then
  echo "CANNOT ANSWER: the probe compiled but did not finish its walk, so what"
  echo "it printed is not a measurement.  Raw output:"
  grep -vE '^[[:space:]]*$' "$OUT" | tail -15 | sed 's/^/    /'
  exit 2
fi
echo ""

sed -n '/TLPROBE  -/,/short of the layer\./p' "$OUT"
echo ""

if grep -q 'no ADMINISTRATOR account was found' "$OUT"; then
  echo "CANNOT ANSWER: there is no ADMINISTRATOR account, so the layer was"
  echo "never tested.  That is not the same as finding it complete."
  exit 2
fi

if grep -qE ', 0 short of the layer\.' "$OUT"; then
  echo "Every ADMINISTRATOR account holds the whole layer."
  exit 0
fi

echo "At least one ADMINISTRATOR account is SHORT of its tier layer."
echo "An upgrade (a reinstall keeping accounts) should close it; failing that,"
echo "move the account's tier down and back up so MODIFY.ACCOUNT re-derives it."
exit 1
