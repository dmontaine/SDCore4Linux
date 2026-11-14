#!/bin/bash
#
# test-install-sdsysssh.sh - sdsys over ssh is never asked about and never opened by the installer (S.155, rewritten 14 Nov 2026; owner, 13 Nov 2026, Windows chat:
# "should we always install remote ssh admin off and then the admin has to turn it on, preventing the need to enter that password during install or even ask about
# remote ssh admin.  It's just an available feature that can be turned on", then "i like the design better and would prefer it in both versions").  Two blocks of
# installsdcore.sh: SDSYS-SSH-STATE (the state read back from the helper) and SDSYS-SSH-SUMMARY (the closing line, with the sudo command a server with no screen
# can use - the reason for the 7 Nov question, kept).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysssh.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysssh.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-sdsysssh.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no sshd (ssh-forcecommand is a stub that logs its arguments; the state it prints is given per row).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
#   N1  the installer asks no question about sdsys over ssh (no prompt naming sdsys and ssh, no open_sdsys_ssh variable)
#   N2  no command line of the installer opens it: no ssh-forcecommand --open-sdsys, no sd-elevate sdsys-ssh on (an echo telling a person the command is allowed)
#   R1  SDSYS-SSH-STATE calls the helper once, with --sdsys-state only, sets sdsys_ssh_state from it and reaches its end under the installer's set and IFS,
#       also when the helper fails
#   S1  sdsys-arm=open -> "SDSYS over ssh: open." and the off command; S2 closed -> "shut." and the sudo ... sdsys-ssh on command; S3 anything else -> "not known" and
#       the status command; none of them claims a state it was not given
#   S4  open with no sdsys Linux password (skipped, or no terminal) adds that ssh cannot let sdsys in until sudo passwd sdsys; with one set or kept it does not
#   W2  order: the ssh boundary (--install), then the sdsys password, then SDSYS-SSH-STATE, then SDSYS-SSH-SUMMARY
#   W3  the old summary line ("open it with  remote.sdsys on  at the SD prompt", which a server with no screen cannot use) is gone
# ANCHORED ON THE ARGUMENTS the stubbed helper was given, the variable the block set, and the block's exit status; the printed words are checked only for the
# lines a person reads.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  judge() {
    total=$((total+1))
    if [ "$2" -ne 0 ]; then echo "  [caught] $1 (exit $2)"; caught=$((caught+1))
    else echo "  [MISSED] $1: the check still passed"; missed=$((missed+1)); fi
  }
  inst_mutant() {   # name, sed expression applied to the installer
    local f="$T/$1.sh"
    if ! sed -e "$2" "$TREE/installsdcore.sh" > "$f"; then echo "  [MISSED] $1: the sed expression did not apply"; missed=$((missed+1)); total=$((total+1)); return; fi
    if cmp -s "$TREE/installsdcore.sh" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); total=$((total+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$1.out" 2>&1; judge "$1" $?
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  awk '/^# SDSYS-SSH-STATE-BEGIN$/,/^# SDSYS-SSH-STATE-END$/' "$TREE/installsdcore.sh" > "$T/stateblock"
  R='/^# SDSYS-SSH-STATE-BEGIN/,/^# SDSYS-SSH-STATE-END/'
  S='/^# SDSYS-SSH-SUMMARY-BEGIN/,/^# SDSYS-SSH-SUMMARY-END/'
  inst_mutant question-back      "/^# GATES-ASK-END/a read -r -p \"Let sdsys sign in over ssh with its password? (y/N) \" yn_sdsys_ssh || yn_sdsys_ssh=\"\""
  inst_mutant variable-back      "/^# GATES-ASK-END/a open_sdsys_ssh=n"
  inst_mutant open-back          "/^# SDSYS-SSH-STATE-BEGIN/a sudo /usr/local/sbin/ssh-forcecommand --open-sdsys || true"
  inst_mutant elevate-open-back  "/^# SDSYS-SSH-STATE-BEGIN/a sudo /usr/local/sbin/sd-elevate sdsys-ssh on || true"
  inst_mutant no-readback        "$R s/^sdsys_ssh_state=.*/sdsys_ssh_state=\"sdsys-arm=closed\"/"
  inst_mutant readback-fatal     "$R s/ || true)/)/"
  inst_mutant summary-open-wrong "$S s/SDSYS over ssh: open\./SDSYS over ssh: shut./"
  inst_mutant summary-no-sudo    "$S s|To open it from any login with sudo:  sudo /usr/local/sbin/sd-elevate sdsys-ssh on|To open it:  remote.sdsys on|"
  inst_mutant no-password-silent "$S{/sdsys has no Linux password yet/d}"
  inst_mutant summary-guesses    "$S s/SDSYS over ssh: not known\./SDSYS over ssh: shut./"
  inst_mutant state-moved-up     "/^# SDSYS-SSH-STATE-BEGIN/,/^# SDSYS-SSH-STATE-END/d;/^# GATES-ASK-END/r $T/stateblock"
  inst_mutant old-line-back      "/^# SDSYS-SSH-SUMMARY-END/a echo \"SDSYS over ssh: shut (open it with  remote.sdsys on  at the SD prompt).\""
  inst_mutant state-marker-gone  "s/^# SDSYS-SSH-STATE-BEGIN/# sdsys-ssh-state-begin/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

cut_block() { awk -v b="# $1-BEGIN" -v e="# $1-END" '$0 == b {f=1; next} $0 == e {f=0} f {print}' "$INST"; }
STATE=$(cut_block SDSYS-SSH-STATE); SUMM=$(cut_block SDSYS-SSH-SUMMARY)
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-sdsysssh: CANNOT RUN - no set line in the installer"; exit 2; }
for b in STATE SUMM; do
  [ -z "${!b}" ] && { echo "test-install-sdsysssh: CANNOT RUN - no $b block in the installer"; exit 2; }
done

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# run BLOCK; prints the output, then VAR=<sdsys_ssh_state> and REACHED-END; the helper's calls go to LOG
runblock() {   # block-text log state helper-rc
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$1" LOG="$2" STATE="$3" HRC="${4:-0}" bash -c '
      eval "$OPTS"; eval "$IFSL"
      RED=""; NC=""; YELLOW=""
      sdsys_ssh_state=$STATE; sdsys_pw_state=${PWS:-set}
      fc() {
        { printf "fc"; printf " %s" "$@"; echo; } >> "$LOG"
        case "$1" in
          --sdsys-state) printf "%s\n" "$STATE"; return "$HRC" ;;
          *) return 0 ;;
        esac
      }
      sudo() { if [ "$1" = /usr/local/sbin/ssh-forcecommand ]; then shift; fc "$@"; else "$@"; fi; }
      eval "$BLOCK"
      echo "VAR=$sdsys_ssh_state"
      echo REACHED-END' < /dev/null 2>&1
}

# N1 / N2: nothing asked, nothing opened
code=$(grep -n -v '^ *#' "$INST")
asks=$(printf '%s\n' "$code" | grep -E 'read [^#]*-p' | grep -i -E 'sdsys' | grep -i -E 'ssh' || true)
var=$(printf '%s\n' "$code" | grep -E 'open_sdsys_ssh' || true)
row "N1 no question about sdsys over ssh, no open_sdsys_ssh variable" "$([ -z "$asks$var" ] && echo 0 || echo 1)" "asks: $asks var: $var"
opens=$(printf '%s\n' "$code" | grep -E 'ssh-forcecommand[^#]*--open-sdsys|sd-elevate[^#]*sdsys-ssh on' | grep -v -E ':\s*echo ' || true)
row "N2 no installer command opens sdsys over ssh" "$([ -z "$opens" ] && echo 0 || echo 1)" "lines: $opens"

# R1: the read-back
rbad=""
for st in "sdsys-arm=open" "sdsys-arm=closed" "absent"; do
  : > "$T/r"; out=$(runblock "$STATE" "$T/r" "$st" 0); rc=$?
  [ "$(tr '\n' '|' < "$T/r")" = "fc --sdsys-state|" ] && [[ "$out" == *"VAR=$st"* && "$out" == *REACHED-END* && $rc = 0 ]] || rbad="$rbad '$st'"
done
: > "$T/r"; out=$(runblock "$STATE" "$T/r" "" 1); rc=$?
[[ "$out" == *REACHED-END* && $rc = 0 ]] || rbad="$rbad helper-fails"
row "R1 SDSYS-SSH-STATE asks --sdsys-state once, keeps what it says and reaches its end (also when the helper fails)" "$([ -z "$rbad" ] && echo 0 || echo 1)" "wrong for:$rbad out: $out"

# S1-S4: the summary line
out=$(runblock "$SUMM" /dev/null "sdsys-arm=open")
row "S1 open -> 'SDSYS over ssh: open.' and the off command" \
    "$([[ "$out" == *"SDSYS over ssh: open."* && "$out" == *"sd-elevate sdsys-ssh off"* && "$out" != *"SDSYS over ssh: shut"* ]] && echo 0 || echo 1)" "$out"
out=$(runblock "$SUMM" /dev/null "sdsys-arm=closed")
row "S2 closed -> 'SDSYS over ssh: shut.' and the sudo ... sdsys-ssh on command for a login with sudo" \
    "$([[ "$out" == *"SDSYS over ssh: shut."* && "$out" == *"sudo /usr/local/sbin/sd-elevate sdsys-ssh on"* && "$out" != *"open."* ]] && echo 0 || echo 1)" "$out"
sbad=""
for st in "absent" "sdsys-arm=legacy" ""; do
  out=$(runblock "$SUMM" /dev/null "$st")
  [[ "$out" == *"SDSYS over ssh: not known."* && "$out" == *"sdsys-ssh status"* && "$out" != *"shut"* && "$out" != *"open."* ]] || sbad="$sbad '$st'"
done
row "S3 any other state -> 'not known' and the status command, claiming nothing" "$([ -z "$sbad" ] && echo 0 || echo 1)" "wrong for:$sbad"
pbad=""
for pw in "set" "kept from the previous install"; do
  out=$(PWS="$pw" runblock "$SUMM" /dev/null "sdsys-arm=open"); [[ "$out" != *"sudo passwd sdsys"* ]] || pbad="$pbad '$pw'->told"
done
for pw in "not set" "not set - there was no terminal to ask at"; do
  out=$(PWS="$pw" runblock "$SUMM" /dev/null "sdsys-arm=open"); [[ "$out" == *"sdsys has no Linux password yet"* && "$out" == *"sudo passwd sdsys"* ]] || pbad="$pbad '$pw'->silent"
done
row "S4 open with no sdsys Linux password says ssh cannot let it in until sudo passwd sdsys; with one set or kept it says nothing" "$([ -z "$pbad" ] && echo 0 || echo 1)" "$pbad"

# W2-W3: the installer as text
ln() { grep -n -m1 -E "$1" "$INST" | cut -d: -f1; }
lb=$(ln '^if sudo /usr/local/sbin/ssh-forcecommand --install; then')
lp=$(ln 'echo "2 of 3: Password for the LINUX sdsys account"'); lr=$(ln '^# SDSYS-SSH-STATE-BEGIN'); ls=$(ln '^# SDSYS-SSH-SUMMARY-BEGIN')
echo "  W2 lines: boundary=$lb password=$lp state=$lr summary=$ls"
row "W2 order: ssh boundary, sdsys password, state read back, summary" \
    "$([ -n "$lb" ] && [ -n "$lp" ] && [ -n "$lr" ] && [ -n "$ls" ] && [ "$lb" -lt "$lp" ] && [ "$lp" -lt "$lr" ] && [ "$lr" -lt "$ls" ] && echo 0 || echo 1)" "out of order"
old=$(grep -n -F 'open it with  remote.sdsys on  at the SD prompt' "$INST" || true)
row "W3 the old summary line, unusable on a server with no screen, is gone" "$([ -z "$old" ] && echo 0 || echo 1)" "$old"

echo "test-install-sdsysssh: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-sdsysssh: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
