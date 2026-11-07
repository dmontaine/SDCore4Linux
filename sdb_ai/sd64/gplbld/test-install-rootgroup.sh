#!/bin/bash
#
# test-install-rootgroup.sh - the installer's ROOT-SDUSERS block (S.158, 7 Nov 2026; owner: "Yes, remove at the end"): root joins sdusers for the install's own
# root-run SD sessions and is taken out again once the last of them has run.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-rootgroup.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-rootgroup.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-rootgroup.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function), getent and gpasswd stubs (MEMBERS is the group's member list; GP_RC makes gpasswd fail).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.
#
#   R1  root in the group (first, middle, last, alone): ONE "gpasswd -d root sdusers", the line saying so, the block's end reached
#   R2  root not in the group, a member whose name only CONTAINS root (rootless, xroot) and an empty group: no gpasswd at all
#   R3  a failing gpasswd warns with the command and the block still reaches its end with status 0
#   R4  order: the block comes AFTER the final CPROC compile and after every "sudo bin/sd" / "sudo $sdsysdir/bin/sd" session command (sd -start/-stop, which open
#       no session, and the sudo -u sdsys password steps excepted), and the "usermod -a -G sdusers root" that put root in comes before all of them
#   R5  the block is the only gpasswd -d of root in the installer
# ANCHORED ON THE ARGUMENTS gpasswd was given and the block's exit status.

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
  inst_mutant() {
    local f="$T/$1.sh"
    if ! sed -e "$2" "$TREE/installsdcore.sh" > "$f"; then echo "  [MISSED] $1: the sed expression did not apply"; missed=$((missed+1)); total=$((total+1)); return; fi
    if cmp -s "$TREE/installsdcore.sh" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); total=$((total+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$1.out" 2>&1; judge "$1" $?
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  awk '/^# ROOT-SDUSERS-BEGIN$/,/^# ROOT-SDUSERS-END$/' "$TREE/installsdcore.sh" > "$T/block"
  B='/^# ROOT-SDUSERS-BEGIN/,/^# ROOT-SDUSERS-END/'
  inst_mutant always-remove     "$B s/^if getent group sdusers .*; then/if true; then/"
  inst_mutant substring-match   "$B s/grep -qx root/grep -q root/"
  inst_mutant fatal-failure     "$B{/sudo gpasswd -d root sdusers\"$/a\\        exit 1
}"
  inst_mutant no-warning        "$B s/WARNING: root could not be taken out of sdusers/root kept/"
  inst_mutant block-too-early   "/^# ROOT-SDUSERS-BEGIN/,/^# ROOT-SDUSERS-END/d;/^echo \"Compiling CPROC without IS_INSTALL defined.\"/{
r $T/block
}"
  inst_mutant session-after     "/^# ROOT-SDUSERS-END/a sudo bin/sd -internal load.help < /dev/null || true"
  inst_mutant begin-marker-gone "s/^# ROOT-SDUSERS-BEGIN/# root-sdusers-begin/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

BLOCK=$(awk '$0 == "# ROOT-SDUSERS-BEGIN" {f=1; next} $0 == "# ROOT-SDUSERS-END" {f=0} f {print}' "$INST")
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-rootgroup: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-rootgroup: CANNOT RUN - no ROOT-SDUSERS block in the installer"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

runblock() {   # members log gpasswd-rc
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" MEMBERS="$1" LOG="$2" GP_RC="$3" bash -c '
      eval "$OPTS"; eval "$IFSL"
      RED=""; NC=""; YELLOW=""
      sudo() { "$@"; }
      getent() { [ "$1" = group ] && [ "$2" = sdusers ] && printf "sdusers:x:979:%s\n" "$MEMBERS"; }
      gpasswd() { { printf "gpasswd"; printf " %s" "$@"; echo; } >> "$LOG"; return "$GP_RC"; }
      eval "$BLOCK"
      echo REACHED-END' 2>&1
}

bad=""
for m in "root" "root,sdsys,don" "sdsys,root,don" "sdsys,don,root"; do
  : > "$T/log"; out=$(runblock "$m" "$T/log" 0); rc=$?
  [ "$(cat "$T/log")" = "gpasswd -d root sdusers" ] && [ "$rc" = 0 ] && [[ "$out" == *"root is no longer in sdusers"* && "$out" == *REACHED-END* ]] || bad="$bad [$m]"
done
row "R1 root in the group anywhere in the list: one gpasswd -d root sdusers, said, end reached" "$([ -z "$bad" ] && echo 0 || echo 1)" "wrong for:$bad"
bad=""
for m in "sdsys,don" "rootless,xroot,sdsys" ""; do
  : > "$T/log"; out=$(runblock "$m" "$T/log" 0); rc=$?
  [ ! -s "$T/log" ] && [ "$rc" = 0 ] && [[ "$out" == *REACHED-END* && "$out" != *"no longer"* ]] || bad="$bad [$m]"
done
row "R2 root not a member (also rootless, xroot, an empty group): no gpasswd" "$([ -z "$bad" ] && echo 0 || echo 1)" "wrong for:$bad"
: > "$T/log"; out=$(runblock "sdsys,root" "$T/log" 1); rc=$?
row "R3 a failing gpasswd warns with the command and goes on with status 0" \
    "$([ "$rc" = 0 ] && [[ "$out" == *"WARNING: root could not be taken out of sdusers"* && "$out" == *"sudo gpasswd -d root sdusers"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "rc=$rc out: $out"

ln_of() { grep -n -m1 -E "$1" "$INST" | cut -d: -f1; }
lu=$(ln_of '^sudo usermod -a -G sdusers root$')
lc=$(ln_of '^if ! sudo bin/sd -internal BASIC gpl.bp cproc; then$')
lb=$(ln_of '^# ROOT-SDUSERS-BEGIN$')
# the last root-run SD session command: sudo ... bin/sd (or $sdsysdir/bin/sd) with anything but -start / -stop, not sudo -u sdsys, not a comment or an echo
# Function BODIES are left out (a function's line says nothing of when it runs); the call of a function that holds one stands for it.
toplevel=$(awk '/^[a-z_]+\(\) *\{/ {inf=1} !inf {printf "%d:%s\n", NR, $0} inf && /^\}/ {inf=0}' "$INST")
sessions=$(printf '%s\n' "$toplevel" | grep -E 'sudo +("?\$\{?sdsysdir\}?/bin/sd"?|bin/sd) |^[0-9]+:\s*open_installer_(gates|sdsys) ' | grep -v -E '^[0-9]+:\s*#|echo |-u sdsys| -(start|stop)\b')
last=$(printf '%s\n' "$sessions" | tail -1 | cut -d: -f1)
first=$(printf '%s\n' "$sessions" | head -1 | cut -d: -f1)
echo "  R4 lines: usermod=$lu first-root-session=$first final-cproc=$lc last-root-session=$last block=$lb"
row "R4 root joins before the first root session, leaves after the final compile and the last root session" \
    "$([ -n "$lu" ] && [ -n "$first" ] && [ -n "$lc" ] && [ -n "$last" ] && [ -n "$lb" ] && [ "$lu" -lt "$first" ] && [ "$lc" -lt "$lb" ] && [ "$last" -lt "$lb" ] && echo 0 || echo 1)" "out of order"
n=$(grep -v -E '^\s*#|echo ' "$INST" | grep -c -E 'gpasswd -d root' || true)
row "R5 the block is the only gpasswd -d of root" "$([ "$n" = 1 ] && echo 0 || echo 1)" "count=$n"

echo "test-install-rootgroup: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-rootgroup: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
