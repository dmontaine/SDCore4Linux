#!/bin/bash
#
# test-install-acctroot.sh - W.11 F3 (security-model evaluation, 24 Oct 2026): the installer leaves /home/sd, /home/sd/user_accounts and
# /home/sd/group_accounts mode 755 (sdsys:sdusers), not 775.  With the group able to write there, any SD user could rename another account's
# directory and put one of their own under the same name.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-acctroot.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-acctroot.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-acctroot.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (a function here), no install, no real chown (a stub logs what it was asked).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run (no block found, or a scenario that did nothing).
#
# WHAT IT RUNS.  The lines between "# ACCTROOT-BEGIN" and "# ACCTROOT-END" are cut out of the installer and run under the installer's OWN
# `set` and `IFS` lines (the 19 Oct lesson: a block tested under `set` alone had been green and then did nothing on the real install), on a
# scratch directory with `umask 002` - so a mkdir that is not corrected makes 775, the wrong answer, and a `chmod` taken out of the block
# shows.  The modes are read back from the disk (`stat`); the real mkdir and chmod run; only chown is a stub.
#
#   A1  a fresh install: the three directories exist, mode 755, and are chowned sdsys:sdusers (exactly three chown calls, on those paths)
#   A2  an upgrade: the three exist at 775 (what the install of 19 Oct left): they end 755
#   A3  nothing is writable by the group or others on any of the three (read from `stat -c %A`)
#   A4  static: no chmod of an account root to anything but 755 in installsdcore.sh, and deletesdcore.sh does not chmod /home/sd at all
# ANCHORED ON THE DISK, not on the block's output: the mode a directory has afterwards.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"
DELETER="$(cd "$HERE/../../.." && pwd)/deletesdcore.sh"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, sed expression
    local name="$1" expr="$2" f="$T/$1.sh" rc
    total=$((total+1))
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  B='/^# ACCTROOT-BEGIN/,/^# ACCTROOT-END/'
  mutant user-accounts-775   "$B s|^sudo chmod 755 \"\$ACCT_PATH\"/user_accounts|sudo chmod 775 \"\$ACCT_PATH\"/user_accounts|"
  mutant group-accounts-775  "$B s|^sudo chmod 755 \"\$ACCT_PATH\"/group_accounts|sudo chmod 775 \"\$ACCT_PATH\"/group_accounts|"
  mutant root-775            "$B s|^sudo chmod 755 \"\$ACCT_PATH\"\$|sudo chmod 775 \"\$ACCT_PATH\"|"
  mutant user-accounts-777   "$B s|^sudo chmod 755 \"\$ACCT_PATH\"/user_accounts|sudo chmod 777 \"\$ACCT_PATH\"/user_accounts|"
  mutant user-accounts-g-w   "$B s|^sudo chmod 755 \"\$ACCT_PATH\"/user_accounts|sudo chmod g+w \"\$ACCT_PATH\"/user_accounts|"
  mutant user-chmod-removed  "$B{/^sudo chmod 755 \"\$ACCT_PATH\"\/user_accounts/d;}"
  mutant group-chmod-removed "$B{/^sudo chmod 755 \"\$ACCT_PATH\"\/group_accounts/d;}"
  mutant root-chmod-removed  "$B{/^sudo chmod 755 \"\$ACCT_PATH\"\$/d;}"
  mutant root-chown-removed  "$B{/^sudo chown sdsys:sdusers \"\$ACCT_PATH\"\$/d;}"
  mutant user-chown-wrong    "$B s|^sudo chown sdsys:sdusers \"\$ACCT_PATH\"/user_accounts|sudo chown root:root \"\$ACCT_PATH\"/user_accounts|"
  mutant mkdir-removed       "$B{/^sudo mkdir -p/d;}"
  mutant begin-marker-gone   "s|^# ACCTROOT-BEGIN|# acctroot-begin|"
  mutant end-marker-gone     "s|^# ACCTROOT-END|# acctroot-end|"
  mutant stray-chmod-later   "\$a sudo chmod 775 \"\$ACCT_PATH\"/user_accounts"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

BLOCK=$(awk '/^# ACCTROOT-BEGIN$/{f=1;next} /^# ACCTROOT-END$/{f=0} f{print}' "$INST")
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-acctroot: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-acctroot: CANNOT RUN - no ACCTROOT block in the installer"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | grep -c .) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# run the block once on $1 (the scratch ACCT_PATH); the chown calls go to $1.chown
runblock() {
  local acct="$1"
  : > "$acct.chown"
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" ACCT="$acct" bash -c '
      eval "$OPTS"; eval "$IFSL"
      umask 002
      sudo() { "$@"; }
      chown() { printf "%s %s\n" "$1" "$2" >> "$ACCT.chown"; }
      ACCT_PATH="$ACCT"
      eval "$BLOCK"
      echo REACHED-END' 2>&1
}
modes() { printf '%s %s %s' "$(stat -c %a "$1")" "$(stat -c %a "$1/user_accounts")" "$(stat -c %a "$1/group_accounts")"; }
perms() { printf '%s %s %s' "$(stat -c %A "$1")" "$(stat -c %A "$1/user_accounts")" "$(stat -c %A "$1/group_accounts")"; }

# A1 fresh
A1="$T/fresh"
out=$(runblock "$A1")
case "$out" in *REACHED-END*) reached=0 ;; *) reached=1 ;; esac
row "A0 the block runs to its end under the installer's set and IFS" "$reached" "$out"
m=$(modes "$A1" 2>&1)
row "A1 a fresh install: /home/sd, user_accounts and group_accounts are 755 (read from the disk)" "$([ "$m" = "755 755 755" ] && echo 0 || echo 1)" "modes: $m"
n=$(grep -c . "$A1.chown")
ok=1
[ "$n" -eq 3 ] && grep -qx "sdsys:sdusers $A1" "$A1.chown" && grep -qx "sdsys:sdusers $A1/user_accounts" "$A1.chown" && grep -qx "sdsys:sdusers $A1/group_accounts" "$A1.chown" && ok=0
row "A1b and the block asks for exactly three chowns, to sdsys:sdusers, on those three paths" "$ok" "$n calls: $(tr '\n' ';' < "$A1.chown")"

# A2 upgrade from 775
A2="$T/upgrade"
mkdir -p "$A2/user_accounts" "$A2/group_accounts"
chmod 775 "$A2" "$A2/user_accounts" "$A2/group_accounts"
before=$(modes "$A2")
out=$(runblock "$A2")
m=$(modes "$A2" 2>&1)
row "A2 an upgrade: directories left at 775 by the earlier installer end 755 (before: $before)" "$([ "$before" = "775 775 775" ] && [ "$m" = "755 755 755" ] && echo 0 || echo 1)" "before $before, after $m"

# A3 nothing writable by group or others
p=$(perms "$A2")
w=0
for x in $p; do case "${x:5:1}${x:8:1}" in *w*) w=1 ;; esac; done
row "A3 no write bit for the group or others on any of the three (read from stat %A: $p)" "$w" "permissions: $p"

# A4 static
bad=$(grep -n -E 'chmod[^#]*(ACCT_PATH|acct_path|/home/sd)' "$INST" | grep -v -E 'chmod 755 ' | grep -v -E '^\s*[0-9]+:\s*#' || true)
row "A4 installsdcore.sh chmods an account root only to 755" "$([ -z "$bad" ] && echo 0 || echo 1)" "$bad"
bad=$(grep -n -E 'chmod[^#]*(acct_path|/home/sd)' "$DELETER" || true)
row "A4b deletesdcore.sh does not chmod /home/sd" "$([ -z "$bad" ] && echo 0 || echo 1)" "$bad"

echo "test-install-acctroot: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-acctroot: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
