#!/bin/bash
# test-install-upgradeover.sh - installsdcore.sh upgrades an installed SD in place (22 Nov 2026, S.282; owner, 21 Nov 2026: "the windows installers just
# install over and existing installation updating what needs to be updated there is no delete required").  It used to stop with "Uninstall it before running
# this script".  Now, when /usr/local/sdsys/bin/sd exists, upgrade_over_existing runs the uninstaller of the source just fetched with the four answers that keep
# the accounts and the configuration (go on, keep accounts, keep configuration, do not restart), and any failure stops the install in words.
# No install, no sudo, no sd.  Exit 0 every row held, 1 one did not, 2 it could not run.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-upgradeover.sh [--selftest]
#
# THE BLOCK.  installsdcore.sh keeps the function between "# UPGRADE-OVER-BEGIN" and "# UPGRADE-OVER-END".  This cuts it out and runs it under the installer's own
# `set -euo pipefail` and IFS with a STUB uninstaller that records what it was given on standard input and its arguments.  The wiring (the flag, the call after the
# source is fetched and before any change, no refusal left) and the uninstaller's own prompts (four, in this order) are read as TEXT.  It cannot say that the real
# uninstaller followed by the real install leaves every setting as it was: that is a real-install row on the VM, NOT run for this change.
#
# --selftest breaks the installer and the uninstaller in the ways listed at the end and requires the rows to notice each one.
set -euo pipefail
IFS=$'\n\t'
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THIS="$HERE/$(basename "${BASH_SOURCE[0]}")"
ROOT="$(cd "$HERE/../../.." && pwd)"
INSTALLER="${INSTALLER:-$ROOT/installsdcore.sh}"
REMOVER="${REMOVER:-$ROOT/deletesdcore.sh}"
passed=0; failed=0
row() {   # row "name" ok(0|1) ["detail"]
  if [ "$2" = 0 ]; then passed=$((passed+1)); echo "  [PASS] $1"
  else failed=$((failed+1)); echo "  [FAIL] $1${3:+   <- $3}"; fi
}

if [ "${1:-}" = "--selftest" ]; then
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, file (i installer, r remover), sed expression
    local f="$T/$1.sh" env_i="$ROOT/installsdcore.sh" env_r="$ROOT/deletesdcore.sh"
    if [ "$2" = i ]; then sed -e "$3" "$ROOT/installsdcore.sh" > "$f"; cmp -s "$ROOT/installsdcore.sh" "$f" && { echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); return; }; env_i="$f"
    else sed -e "$3" "$ROOT/deletesdcore.sh" > "$f"; cmp -s "$ROOT/deletesdcore.sh" "$f" && { echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); return; }; env_r="$f"; fi
    if INSTALLER="$env_i" REMOVER="$env_r" bash "$THIS" > "$T/$1.out" 2>&1; then echo "  [MISSED] $1: the check still passed"; missed=$((missed+1))
    else echo "  [caught] $1"; caught=$((caught+1)); fi
  }
  echo "selftest: the real files first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real files do not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real files pass"
  mutant wrong-answers        i "s/printf 'y\\\\ny\\\\ny\\\\nn\\\\n'/printf 'y\\\\ny\\\\nn\\\\nn\\\\n'/"
  mutant exit-status-ignored  i "s/    if ! printf 'y.*| bash \"\$del\"; then/    if false; then/"
  mutant missing-script-goes-on i "s/    if \[ ! -f \"\$del\" \]; then/    if false; then/"
  mutant refusal-is-back      i "s/^    upgrade_over=1\$/    echo 'Uninstall it before running this script.'; exit 1/"
  mutant call-dropped         i "s/^    upgrade_over_existing \"\\\${dflt_git_folder}\\/deletesdcore.sh\" || exit 1/    true/"
  mutant access-asked-again   i 's/^if \[ -f \/home\/sd\/sd.conf \] || \[ "\${upgrade_over:-0}" -eq 1 \]; then/if [ -f \/home\/sd\/sd.conf ]; then/'
  mutant uninstaller-new-prompt r "s/^read -r -p \"Restart computer now? (y\\/N) \" yn/read -r -p \"Sure? \" sure\\nread -r -p \"Restart computer now? (y\\/N) \" yn/"
  echo "selftest: $caught caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

[ -r "$INSTALLER" ] || { echo "test-install-upgradeover: CANNOT RUN - no installer at $INSTALLER"; exit 2; }
[ -r "$REMOVER" ] || { echo "test-install-upgradeover: CANNOT RUN - no uninstaller at $REMOVER"; exit 2; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
awk '/^# UPGRADE-OVER-BEGIN$/,/^# UPGRADE-OVER-END$/' "$INSTALLER" > "$T/block.sh"
echo "installer  : $INSTALLER"
echo "uninstaller: $REMOVER"
grep -q '^upgrade_over_existing()' "$T/block.sh" || { echo "test-install-upgradeover: CANNOT RUN - no upgrade_over_existing between # UPGRADE-OVER-BEGIN and # UPGRADE-OVER-END"; exit 2; }

# the stub uninstaller records its standard input and exits with $STUB_RC
printf '%s\n' '#!/bin/bash' 'cat > "$STUB_LOG"' 'exit "${STUB_RC:-0}"' > "$T/stub-del"
run_fn() {   # run_fn SCRIPT RC -> the function's output, then RC=<its status>
  STUB_LOG="$T/stdin.log" STUB_RC="$2" bash -c '
    set -euo pipefail
    IFS=$'"'"'\n\t'"'"'
    . "'"$T"'/block.sh"
    rc=0; upgrade_over_existing "$1" || rc=$?
    echo "RC=$rc"
  ' _ "$1" 2>&1
}
has() { printf '%s\n' "$1" | grep -qF -- "$2"; }

: > "$T/stdin.log"; out="$(run_fn "$T/stub-del" 0)"
row "U1 the uninstaller is run and gets exactly four answers in order: y (go on), y (keep the accounts), y (keep the configuration), n (do not restart); the function succeeds" \
  "$([ "$(tr '\n' ',' < "$T/stdin.log")" = "y,y,y,n," ] && has "$out" "RC=0" && has "$out" "upgrading it in place, keeping your accounts and your configuration" && echo 0 || echo 1)" "stdin='$(tr '\n' ',' < "$T/stdin.log")' out=$out"
rm -f "$T/stdin.log"; out="$(run_fn "$T/no-such-script" 0)"
row "U2 NULL CASE: no uninstaller in the fetched source: nothing is run, it says so and how to do it by hand, and fails" \
  "$([ ! -e "$T/stdin.log" ] && has "$out" "RC=1" && has "$out" "cannot be upgraded in place" && has "$out" "Run deletesdcore.sh" && echo 0 || echo 1)" "$out"
: > "$T/stdin.log"; out="$(run_fn "$T/stub-del" 3)"
row "U3 an uninstaller that fails stops the install: RC=1 and 'nothing was installed over it'" "$(has "$out" "RC=1" && has "$out" "nothing was installed over it" && echo 0 || echo 1)" "$out"

# ---- the wiring and the uninstaller's prompts (text) ----------------------------------------------------------------
code() { grep -v '^[[:space:]]*#' "$INSTALLER"; }
row "W1 the old refusal is gone from the code (no 'Uninstall it before running this script' that exits)" \
  "$(code | grep -qF 'Uninstall it before running this script' && echo 1 || echo 0)"
row "W2 an installed SD only sets the flag (upgrade_over=1 when /usr/local/sdsys/bin/sd is there) and changes nothing yet" \
  "$(code | awk '/^upgrade_over=0$/{f=1} f{print} f&&/^fi$/{exit}' | tr '\n' ' ' | tr -s ' ' | grep -qF 'upgrade_over=0 if [ -f "/usr/local/sdsys/bin/sd" ]; then upgrade_over=1 fi' && echo 0 || echo 1)"
l_src="$(grep -n 'if \[ -d "\${inst_folder}/sd64" \]; then' "$INSTALLER" | head -1 | cut -d: -f1)"
l_call="$(grep -n '^    upgrade_over_existing "\${dflt_git_folder}/deletesdcore.sh" || exit 1' "$INSTALLER" | head -1 | cut -d: -f1)"
l_grp="$(grep -n 'Create sdusers/sdsys only when absent' "$INSTALLER" | head -1 | cut -d: -f1)"
row "W3 the call comes AFTER the source is fetched and checked and BEFORE the users and groups are made (nothing is changed on a failed fetch)" \
  "$([ -n "$l_src" ] && [ -n "$l_call" ] && [ -n "$l_grp" ] && [ "$l_src" -lt "$l_call" ] && [ "$l_call" -lt "$l_grp" ] && echo 0 || echo 1)" "source check $l_src, call $l_call, users $l_grp"
row "W4 the uninstaller asks exactly four questions on an upgrade path (Continue?, accounts, configuration, restart) and one more only on the DELETE branch: a new prompt would shift the four answers" \
  "$([ "$(grep -c '^[[:space:]]*read -r -p' "$REMOVER")" = 5 ] && echo 0 || echo 1)" "read -r -p lines: $(grep -c '^[[:space:]]*read -r -p' "$REMOVER")"
q1="$(grep -n 'read -r -p "Continue?' "$REMOVER" | head -1 | cut -d: -f1)"; q2="$(grep -n 'read -r -p "Keep your existing accounts?' "$REMOVER" | head -1 | cut -d: -f1)"
q3="$(grep -n 'read -r -p "Keep your existing configuration?' "$REMOVER" | head -1 | cut -d: -f1)"; q4="$(grep -n 'read -r -p "Restart computer now?' "$REMOVER" | head -1 | cut -d: -f1)"
row "W5 ...in the order the answers are given in" "$([ -n "$q1" ] && [ -n "$q2" ] && [ -n "$q3" ] && [ -n "$q4" ] && [ "$q1" -lt "$q2" ] && [ "$q2" -lt "$q3" ] && [ "$q3" -lt "$q4" ] && echo 0 || echo 1)" "$q1 $q2 $q3 $q4"

acc="$(awk '/^# ACCESS-ASK-BEGIN$/,/^# ACCESS-ASK-END$/' "$INSTALLER")"
row "W6 an install over asks no access question: ACCESS-ASK keeps access when upgrade_over is 1, as when a saved sd.conf is there (found on the VM, 22 Nov)" \
  "$(printf '%s\n' "$acc" | grep -qF 'if [ -f /home/sd/sd.conf ] || [ "${upgrade_over:-0}" -eq 1 ]; then' && echo 0 || echo 1)"

echo
echo "test-install-upgradeover: $passed passed, $failed failed"
[ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]
