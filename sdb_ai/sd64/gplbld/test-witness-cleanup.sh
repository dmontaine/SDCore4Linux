#!/bin/bash
#
# test-witness-cleanup.sh - witness-masters.sh's EXIT cleanup deletes only the accounts that run MADE (S.67, the independent verifier's low finding of 19 Oct 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-witness-cleanup.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-witness-cleanup.sh --selftest
#   WITNESS=<a copy of witness-masters.sh> bash .../test-witness-cleanup.sh        (what --selftest uses)
#
# FREE CHECK: no sudo (a stub script stands in for it), no install, no root, no SD.  Everything happens in a scratch directory.  Exit 0 every row passed, 1 a row failed,
# 2 it could not run (the function could not be cut out, or a scenario never reached the cleanup: a check that ran nothing is not a pass).
#
# THE FAULT.  The witness says it "will not touch state it did not create", and its cleanup deleted a register record named zwm1 or zwm2 through SD (DELETE.ACCOUNT, answer y)
# whenever one EXISTED, including after the script stopped at "CANNOT RUN - the ground is not clear" before it made anything: it removed the very account it had refused to touch.
# MADE_A1 and MADE_A2 were set and not used by that loop.
#
# WHAT IT RUNS.  cleanup() is cut out of witness-masters.sh by its first and last lines and run in a subshell with COMMIT=1, a scratch register (one empty file per record), `sudo`
# a stub that appends its arguments and its standard input to a log, and the flags the scenario sets.  A row passes on the stub's log: which DELETE.ACCOUNT sessions it was
# asked to run.  The cleanup's own banner must be in the output (the null case: a cleanup that did not run proves nothing).
#
# START-HISTORY:
# 19 Oct 26 dm  New (S.67 fix round).
# END-HISTORY

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
WIT="${WITNESS:-$HERE/witness-masters.sh}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, sed expression (applied to the whole witness script)
    local name="$1" expr="$2" f="$T/$1.sh" rc
    total=$((total+1))
    sed -e "$expr" "$WIT" > "$f"
    if cmp -s "$WIT" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    WITNESS="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real script first (must pass), then mutants (each must not)"
  WITNESS="$WIT" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real script does not pass:"; tail -12 "$T/real.out"; exit 1; }
  echo "  [ok] the real script passes"
  mutant deletes-any-record-that-exists   's/if \[ "\$MADE" -eq 1 \] \&\& \[ -e "\$REGISTER\/\$a" \]; then/if [ -e "$REGISTER\/$a" ]; then/'
  mutant made-flag-always-one             's/^        MADE=\$(\[ "\$a" = "\$A1" \] \&\& echo "\$MADE_A1" || echo "\$MADE_A2")$/        MADE=1/'
  mutant flags-swapped                    's/echo "\$MADE_A1" || echo "\$MADE_A2")$/echo "$MADE_A2" || echo "$MADE_A1")/'
  mutant record-test-dropped              's/if \[ "\$MADE" -eq 1 \] \&\& \[ -e "\$REGISTER\/\$a" \]; then/if [ "$MADE" -eq 1 ]; then/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ] && exit 0 || exit 1
fi

[ -f "$WIT" ] || { echo "test-witness-cleanup: CANNOT RUN - no $WIT"; exit 2; }
FUNC="$(sed -n '/^cleanup() {/,/^}/p' "$WIT")"
if [ "$(printf '%s\n' "$FUNC" | wc -l)" -lt 10 ]; then
  echo "test-witness-cleanup: CANNOT RUN - cleanup() was not cut out of $WIT (got $(printf '%s\n' "$FUNC" | wc -l) line(s))"
  exit 2
fi
echo "test-witness-cleanup: witness $WIT, cleanup() of $(printf '%s\n' "$FUNC" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"
cat > "$T/bin/sudo" <<'STUB'
#!/bin/sh
# the stub: one line in the log for each call, with the standard input the call was given
{ printf 'SUDO'; for a in "$@"; do printf ' [%s]' "$a"; done; printf ' STDIN<<%s>>\n' "$(tr '\n' '|')"; } >> "$SUDOLOG"
exit 0
STUB
chmod +x "$T/bin/sudo"

passed=0; failed=0
ok()  { passed=$((passed+1)); echo "  [PASS] $1"; }
bad() { failed=$((failed+1)); echo "  [FAIL] $1 <- $2"; }

scenario() {   # scenario NAME MADE_A1 MADE_A2 RECORD...   - runs cleanup(); leaves $T/out (its output) and $T/sudo.log (the stub's log)
  local name="$1" m1="$2" m2="$3"; shift 3
  rm -rf "$T/register" "$T/sudo.log" "$T/out"; mkdir -p "$T/register"
  local r
  for r in "$@"; do : > "$T/register/$r"; done
  echo "-- scenario $name: MADE_A1=$m1 MADE_A2=$m2, register holds: ${*:-nothing}"
  (
    export PATH="$T/bin:$PATH" SUDOLOG="$T/sudo.log"
    set -u
    SD=/usr/local/sdsys/bin/sd; COMMIT=1; STALE_PID=""; A1=zwm1; A2=zwm2; VU=zwmv; GROUND_CLEAR=0; WORK=""
    REGISTER="$T/register"; ACCOUNTS_ROOT="$T/accounts"; MADE_A1=$m1; MADE_A2=$m2
    say() { printf '%s\n' "$*"; }
    head2() { say "=== $*"; }
    yesno_user() { echo no; }
    yesno_group() { echo no; }
    yesno_path() { [ -e "$1" ] && echo yes || echo no; }
    eval "$FUNC"
    cleanup
  ) > "$T/out" 2>&1
  sed -e 's/^/      | /' "$T/out"
  [ -f "$T/sudo.log" ] && sed -e 's/^/      stub sudo: /' "$T/sudo.log"
  # the null case: the cleanup ran (its banner is there)
  if ! grep -qF "CLEANUP - removing whatever this run made" "$T/out"; then
    echo "test-witness-cleanup: CANNOT RUN - scenario $name never reached the cleanup"; exit 2
  fi
}

deleted() {   # the accounts the stub was asked to DELETE.ACCOUNT, in order, one per line
  [ -f "$T/sudo.log" ] || return 0
  grep -o 'DELETE\.ACCOUNT zwm[0-9]' "$T/sudo.log" | sed -e 's/DELETE\.ACCOUNT //'
}

scenario "nothing made, both records there (the run stopped at 'the ground is not clear')" 0 0 zwm1 zwm2
got="$(deleted | tr '\n' ' ')"
[ -z "$got" ] && ok "S1: no DELETE.ACCOUNT was run for a record this run did not make" || bad "S1: no DELETE.ACCOUNT was run for a record this run did not make" "deleted: $got"
grep -qF "left behind for zwm1: user=no group=no dir=no register=yes" "$T/out" && ok "S1a: ...and the report says the record is still there" || bad "S1a: ...and the report says the record is still there" "$(grep 'left behind for zwm1' "$T/out")"

scenario "zwm1 made, both records there" 1 0 zwm1 zwm2
got="$(deleted | tr '\n' ' ')"
[ "$got" = "zwm1 " ] && ok "S2: only zwm1, which this run made, was deleted" || bad "S2: only zwm1, which this run made, was deleted" "deleted: '$got'"
grep -qF "STDIN<<|TERM 200,9999|DELETE.ACCOUNT zwm1|y|OFF|>>" "$T/sudo.log" && ok "S2a: ...in the session the cleanup has always used (TERM, DELETE.ACCOUNT, the answer y, OFF)" || bad "S2a: the session" "$(cat "$T/sudo.log" 2>/dev/null)"

scenario "zwm2 made only, both records there" 0 1 zwm1 zwm2
got="$(deleted | tr '\n' ' ')"
[ "$got" = "zwm2 " ] && ok "S3: only zwm2, which this run made, was deleted" || bad "S3: only zwm2, which this run made, was deleted" "deleted: '$got'"

scenario "both made, both records there" 1 1 zwm1 zwm2
got="$(deleted | tr '\n' ' ')"
[ "$got" = "zwm1 zwm2 " ] && ok "S4: both were deleted, zwm1 first" || bad "S4: both were deleted, zwm1 first" "deleted: '$got'"

scenario "zwm1 made but its record is already gone" 1 0 zwm2
got="$(deleted | tr '\n' ' ')"
[ -z "$got" ] && ok "S5: a record that is not there is not deleted (and zwm2, not made, is left)" || bad "S5: a record that is not there is not deleted" "deleted: '$got'"

echo "test-witness-cleanup: $passed passed, $failed failed"
[ "$failed" -eq 0 ] && exit 0 || exit 1
