#!/bin/bash
#
# test-install-restart.sh - installsdcore.sh's LAST STEP leaves SD running (S.58 (2), owner 7 Oct 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-restart.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-restart.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-restart.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd, no systemd.  Exit 0 every row passed, 1 a row failed, 2 it could
# not run (a refusal to pass on nothing: a missing block is exit 2, never a pass).
#
# WHY IT EXISTS.  The password steps start SD and stop it again with a bare "sd -stop", behind systemd's
# back: sd.service is Type=oneshot with RemainAfterExit=yes, so after an install it read "active (exited)"
# with no daemon, "systemctl start sd" was a no-op, and every "sd" and every witness answered "SD has not
# been started" until a reboot (the owner's reinstall of 7 Oct 2026, journal: the install's own -stop at
# 11:21:25 and nothing after it; the first witness-absence run failed 61 of 114 on it and measured nothing).
# The fix is a "systemctl restart sd.service" after the last password step.  What can be checked here is
# what the installer's own text controls:
#
#   A  the block runs the ONE command that fixes it - "systemctl restart sd.service", not "start" (the
#      no-op that was the bug) - under the installer's own "set -euo pipefail", and says it is running
#   B  when the restart fails the install GOES ON (set -e must not end it), says so, and names the
#      command that tries again
#   C  nothing stops SD after the restart - no sd_install_stop, no "sd -stop", no "systemctl stop" later in
#      the script - because a stop after it would put the bug back; and it comes before the closing banner
#      and before the "Restart Computer?" question
#   D  there is exactly one restart in the script
#   E  the closing text says "SD is running now." only behind the state the block sets
#
# NOT MEASURED HERE, and said so: that systemd really runs the unit's stop and start and leaves a daemon
# (that is the install itself - the owner's own "systemctl restart sd.service" on 7 Oct 11:24:33 did, from
# exactly this "active (exited), no daemon" state).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, sed expression
    local name="$1" expr="$2" f="$T/$1.sh" rc
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -5 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant restart-became-start  's/systemctl restart sd\.service/systemctl start sd.service/'
  mutant restart-removed       's/^if sudo systemctl restart sd\.service; then$/if true; then/'
  mutant restart-made-fatal    's/^if sudo systemctl restart sd\.service; then$/sudo systemctl restart sd.service; if true; then/'
  mutant stop-after-restart    's/^# display end of script message$/sd_install_stop/'
  mutant running-line-unguarded 's/^if \[ "\$sd_running_state" = running \]; then$/if true; then/'
  mutant retry-hint-removed    's/  SD did not start\.  Start it with:  sudo systemctl restart sd\.service/  SD did not start./'
  echo "selftest: $caught of 6 mutants caught, $missed missed"
  [ "$caught" -eq 6 ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
BLOCK=$(awk '/^sd_running_state="not started"/{f=1} f{print} f&&/^fi$/{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ]  && { echo "test-install-restart: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-restart: CANNOT RUN - no restart block in the installer (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines, from the sd_running_state line to its closing fi"
CALLS=$(mktemp); trap 'rm -f "$CALLS"' EXIT
export BLOCK OPTS CALLS

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
run_block() {   # rc the stubbed sudo returns; prints the block's output, then REACHED-END and the state
  : > "$CALLS"
  SUDO_RC="$1" bash -c '
      eval "$OPTS"
      sudo() { printf "%s\n" "$*" >> "$CALLS"; return "$SUDO_RC"; }
      RED=; NC=
      eval "$BLOCK"
      echo "REACHED-END state=$sd_running_state"' 2>&1
}

echo "--- A: the restart succeeds"
OUT=$(run_block 0)
printf '%s\n' "$OUT" | sed 's/^/      | /'
echo "      sudo was called with: $(tr '\n' ';' < "$CALLS")"
row "A1 the one command run is exactly: systemctl restart sd.service" \
    "$([ "$(cat "$CALLS")" = "systemctl restart sd.service" ] && echo 0 || echo 1)" "sudo calls: $(tr '\n' ';' < "$CALLS")"
row "A2 it says it is starting SD, and ends with the state 'running'" \
    "$(printf '%s' "$OUT" | grep -q 'Starting SD' && printf '%s' "$OUT" | grep -q 'REACHED-END state=running' && echo 0 || echo 1)" "no Starting SD, or no state=running"
row "A3 it did not claim a failure" \
    "$(printf '%s' "$OUT" | grep -q 'SD did not start' && echo 1 || echo 0)" "printed SD did not start on success"

echo "--- B: the restart fails (sudo returns 1)"
OUT=$(run_block 1)
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "B1 the install goes on: set -e did not end it" \
    "$(printf '%s' "$OUT" | grep -q 'REACHED-END' && echo 0 || echo 1)" "the block ended the script"
row "B2 it says SD did not start, and names the command that tries again" \
    "$(printf '%s' "$OUT" | grep -q 'SD did not start' && printf '%s' "$OUT" | grep -q 'sudo systemctl restart sd.service' && echo 0 || echo 1)" "message or retry hint missing"
row "B3 and the state stays 'not started' (the closing text must not say it is running)" \
    "$(printf '%s' "$OUT" | grep -q 'REACHED-END state=not started' && echo 0 || echo 1)" "state is not 'not started'"

echo "--- C, D, E: where it sits in the installer"
code() { grep -n -E '^[[:space:]]*[^#[:space:]]' "$INST"; }          # numbered lines that are not comments or blank
RUNS='^[0-9]+:[[:space:]]*(if +)?(! +)?sudo +systemctl +restart +sd\.service'   # a line that RUNS it, not an echo that names it
L_RESTART=$(code | grep -E "$RUNS" | head -1 | cut -d: -f1)
N_RESTART=$(code | grep -c -E "$RUNS")
echo "      the restart is at line ${L_RESTART:-<none>}; $N_RESTART line(s) in the script run it"
row "D1 exactly one line of code runs the restart" "$([ "$N_RESTART" = 1 ] && echo 0 || echo 1)" "$N_RESTART lines"
if [ -n "$L_RESTART" ]; then
  LATE=$(code | awk -F: -v r="$L_RESTART" '$1>r' | grep -E 'sd_install_stop|[^_]sd[^ ]* +-stop|systemctl +(stop|kill)|shutdown|poweroff|halt' | head -3)
  row "C1 nothing after the restart stops SD" "$([ -z "$LATE" ] && echo 0 || echo 1)" "a stop follows it: $LATE"
  L_BANNER=$(code | grep -E 'The SD server is installed' | head -1 | cut -d: -f1)
  L_ASK=$(code | grep -E 'read -r -p "Restart Computer' | head -1 | cut -d: -f1)
  L_LASTPW=$(code | awk -F: -v r="$L_RESTART" '$1<r' | grep -E 'sd_install_stop' | tail -1 | cut -d: -f1)
  echo "      the last password step's stop is at line ${L_LASTPW:-<none>}, the banner at ${L_BANNER:-<none>}, the reboot question at ${L_ASK:-<none>}"
  row "C2 it comes after the last password step's stop" "$([ -n "$L_LASTPW" ] && [ "$L_RESTART" -gt "$L_LASTPW" ] && echo 0 || echo 1)" "restart $L_RESTART, last stop ${L_LASTPW:-none}"
  row "C3 and before the closing banner and the reboot question" \
      "$([ -n "$L_BANNER" ] && [ -n "$L_ASK" ] && [ "$L_RESTART" -lt "$L_BANNER" ] && [ "$L_RESTART" -lt "$L_ASK" ] && echo 0 || echo 1)" "banner ${L_BANNER:-none}, question ${L_ASK:-none}"
  L_GUARD=$(code | grep -E 'if \[ "\$sd_running_state" = running \]; then' | head -1 | cut -d: -f1)
  L_SAYS=$(code | grep -E 'echo "SD is running now\."' | head -1 | cut -d: -f1)
  L_REBOOT=$(code | grep -E 'echo "Reboot to assure that group memberships' | head -1 | cut -d: -f1)
  row "E1 'SD is running now.' sits inside the guard on the block's state, before the reboot advice" \
      "$([ -n "$L_GUARD" ] && [ -n "$L_SAYS" ] && [ -n "$L_REBOOT" ] && [ "$L_GUARD" -lt "$L_SAYS" ] && [ "$L_SAYS" -lt "$L_REBOOT" ] && echo 0 || echo 1)" \
      "guard ${L_GUARD:-none}, says ${L_SAYS:-none}, reboot advice ${L_REBOOT:-none}"
else
  row "C/E  the restart line was not found in the installer's code" 1 "no 'if sudo ... systemctl restart sd.service' line"
fi
echo "test-install-restart: $pass passed, $fail failed"
[ "$((pass + fail))" -eq 0 ] && { echo "test-install-restart: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
