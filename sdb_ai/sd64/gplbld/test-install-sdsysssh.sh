#!/bin/bash
#
# test-install-sdsysssh.sh - the installer's question whether to open sdsys over ssh (S.155, 7 Nov 2026; owner, after an install on a headless container: "If sd is
# being installed on a headless server there is no way to give the remote access without these additional steps which are not documented"; he chose "Summary +
# question").  Three blocks of installsdcore.sh: SDSYS-SSH-ASK (the question, default No), SDSYS-SSH-OPEN (ssh-forcecommand --open-sdsys on a y only, after the
# sdsys password, and the state read back) and SDSYS-SSH-SUMMARY (the closing line, with the sudo command that a server with no screen can use).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysssh.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysssh.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-sdsysssh.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no sshd (ssh-forcecommand is a stub that logs its arguments; FC_OPEN_RC makes --open-sdsys fail, FC_STATE is what
# --sdsys-state prints).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
#   Q1  only y, Y, yes, YES (any case) open it; Enter, n, no, "maybe" and an ended input leave it shut - read from what the block set
#   Q2  the question is asked once, ends "(y/N)", and the block runs to its end under the installer's own set options and IFS (an ended input included)
#   O1  a y with the ssh boundary in place runs ssh-forcecommand --open-sdsys once, then --sdsys-state, and says "sdsys can now sign in over ssh"
#   O2  an n never runs --open-sdsys (only --sdsys-state)
#   O3  a y with the boundary NOT in place does not run --open-sdsys, warns and names sudo /usr/local/sbin/sd-elevate sdsys-ssh on, and goes on to the end
#   O4  a y whose --open-sdsys fails warns with the same command and goes on to the end with status 0
#   S1  sdsys-arm=open -> "SDSYS over ssh: open." and the off command; S2 closed -> "shut." and the sudo ... sdsys-ssh on command; S3 anything else -> "not known" and
#       the status command; none of them claims a state it was not given
#   S4  open with no sdsys Linux password (skipped, or no terminal) adds that ssh cannot let sdsys in until sudo passwd sdsys; with one set or kept it does not
#   W1  the installer runs --open-sdsys in that block only, and nowhere opens sdsys without the y
#   W2  order: GATES-ASK, then SDSYS-SSH-ASK, then the ssh boundary (--install), then the sdsys password, then SDSYS-SSH-OPEN, then SDSYS-SSH-SUMMARY
#   W3  the old summary line ("open it with  remote.sdsys on  at the SD prompt", which a server with no screen cannot use) is gone
# ANCHORED ON THE ARGUMENTS the stubbed helper was given, the variable the question set, and the block's exit status; the printed words are checked only for the
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
  awk '/^# SDSYS-SSH-OPEN-BEGIN$/,/^# SDSYS-SSH-OPEN-END$/' "$TREE/installsdcore.sh" > "$T/openblock"   # for open-moved-up: the open placed straight after the question
  A='/^# SDSYS-SSH-ASK-BEGIN/,/^# SDSYS-SSH-ASK-END/'
  O='/^# SDSYS-SSH-OPEN-BEGIN/,/^# SDSYS-SSH-OPEN-END/'
  S='/^# SDSYS-SSH-SUMMARY-BEGIN/,/^# SDSYS-SSH-SUMMARY-END/'
  inst_mutant default-yes        "$A s/^open_sdsys_ssh=n/open_sdsys_ssh=y/"
  inst_mutant any-answer-opens   "$A s/case \$yn_sdsys_ssh in \[yY\]|\[yY\]\[eE\]\[sS\] )/case \$yn_sdsys_ssh in *)/"
  inst_mutant prompt-yn-swapped  "$A s|(y/N)|(Y/n)|"
  inst_mutant open-without-y     "$O s/^if \[ \"\$open_sdsys_ssh\" = y \]; then/if true; then/"
  inst_mutant no-boundary-test   "$O s/\[ \"\$ssh_boundary_ok\" = 1 \] \&\& //"
  inst_mutant open-fatal         "$O{/sd-elevate sdsys-ssh on\"/a\\        exit 1
}"
  inst_mutant no-readback        "$O s/^sdsys_ssh_state=.*/sdsys_ssh_state=\"sdsys-arm=closed\"/"
  inst_mutant summary-open-wrong "$S s/SDSYS over ssh: open\./SDSYS over ssh: shut./"
  inst_mutant summary-no-sudo    "$S s|To open it from any login with sudo:  sudo /usr/local/sbin/sd-elevate sdsys-ssh on|To open it:  remote.sdsys on|"
  inst_mutant no-password-silent "$S{/sdsys has no Linux password yet/d}"
  inst_mutant summary-guesses   "$S s/SDSYS over ssh: not known\./SDSYS over ssh: shut./"
  inst_mutant open-moved-up      "/^# SDSYS-SSH-OPEN-BEGIN/,/^# SDSYS-SSH-OPEN-END/d;/^# SDSYS-SSH-ASK-END/r $T/openblock"
  inst_mutant old-line-back      "/^# SDSYS-SSH-SUMMARY-END/a echo \"SDSYS over ssh: shut (open it with  remote.sdsys on  at the SD prompt).\""
  inst_mutant ask-marker-gone    "s/^# SDSYS-SSH-ASK-BEGIN/# sdsys-ssh-ask-begin/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

cut_block() { awk -v b="# $1-BEGIN" -v e="# $1-END" '$0 == b {f=1; next} $0 == e {f=0} f {print}' "$INST"; }
ASK=$(cut_block SDSYS-SSH-ASK); OPEN=$(cut_block SDSYS-SSH-OPEN); SUMM=$(cut_block SDSYS-SSH-SUMMARY)
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-sdsysssh: CANNOT RUN - no set line in the installer"; exit 2; }
for b in ASK OPEN SUMM; do
  [ -z "${!b}" ] && { echo "test-install-sdsysssh: CANNOT RUN - no $b block in the installer"; exit 2; }
done

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# run BLOCK with stdin INPUT; prints the output, then VAR=<value of open_sdsys_ssh> and REACHED-END; the helper's calls go to LOG
runblock() {   # block-text input log boundary-ok open-rc state
  printf '%s' "$2" | OPTS="$OPTS" IFSL="$IFSL" BLOCK="$1" LOG="$3" BOK="$4" ORC="$5" STATE="$6" bash -c '
      eval "$OPTS"; eval "$IFSL"
      RED=""; NC=""; YELLOW=""
      open_sdsys_ssh=${OPEN_PRESET:-n}; ssh_boundary_ok=$BOK; sdsys_ssh_state=$STATE; sdsys_pw_state=${PWS:-set}
      fc() {
        { printf "fc"; printf " %s" "$@"; echo; } >> "$LOG"
        case "$1" in
          --open-sdsys) return "$ORC" ;;
          --sdsys-state) printf "%s\n" "$STATE"; return 0 ;;
          *) return 0 ;;
        esac
      }
      sudo() { if [ "$1" = /usr/local/sbin/ssh-forcecommand ]; then shift; fc "$@"; else "$@"; fi; }
      eval "$BLOCK"
      echo "VAR=$open_sdsys_ssh"
      echo REACHED-END' 2>&1
}

# Q1 / Q2: the answers
qbad=""
for a in "y" "Y" "yes" "YES" "Yes"; do
  out=$(runblock "$ASK" "$a"$'\n' /dev/null 1 0 ""); rc=$?
  [[ "$out" == *"VAR=y"* && "$out" == *REACHED-END* && $rc = 0 ]] || qbad="$qbad '$a'->not-open"
done
for a in "" "n" "no" "maybe" "yess"; do
  out=$(runblock "$ASK" "$a"$'\n' /dev/null 1 0 ""); rc=$?
  [[ "$out" == *"VAR=n"* && "$out" == *REACHED-END* && $rc = 0 ]] || qbad="$qbad '$a'->open"
done
row "Q1 only y or yes (any case) opens it; Enter, n, no, maybe and yess leave it shut" "$([ -z "$qbad" ] && echo 0 || echo 1)" "$qbad"
out=$(runblock "$ASK" "" /dev/null 1 0 ""); rc=$?
nq=$(printf '%s\n' "$ASK" | grep -c 'read -r -p')
row "Q2 one question ending (y/N); an ended input leaves it shut and reaches the end under the installer's set and IFS" \
    "$([ "$nq" = 1 ] && printf '%s\n' "$ASK" | grep -q -F 'read -r -p "Let sdsys sign in over ssh with its password? (y/N) "' && [[ "$out" == *"VAR=n"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "questions=$nq rc=$rc out: $out"

# O1-O4: the open
: > "$T/o1"; out=$(OPEN_PRESET=y runblock "$OPEN" "" "$T/o1" 1 0 "sdsys-arm=open"); rc=$?
row "O1 a y with the boundary runs --open-sdsys once, then --sdsys-state, and says so" \
    "$([ "$(tr '\n' '|' < "$T/o1")" = "fc --open-sdsys|fc --sdsys-state|" ] && [[ "$out" == *"sdsys can now sign in over ssh"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "calls: $(tr '\n' '|' < "$T/o1") out: $out"
: > "$T/o2"; out=$(OPEN_PRESET=n runblock "$OPEN" "" "$T/o2" 1 0 "sdsys-arm=closed"); rc=$?
row "O2 an n never runs --open-sdsys" \
    "$([ "$(tr '\n' '|' < "$T/o2")" = "fc --sdsys-state|" ] && [[ "$out" != *"sdsys can now"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "calls: $(tr '\n' '|' < "$T/o2") out: $out"
: > "$T/o3"; out=$(OPEN_PRESET=y runblock "$OPEN" "" "$T/o3" 0 0 "absent"); rc=$?
row "O3 a y without the ssh boundary does not open, warns with the sudo command and goes on" \
    "$(! grep -q -- --open-sdsys "$T/o3" && [[ "$out" == *"WARNING: sdsys over ssh could not be opened"* && "$out" == *"sudo /usr/local/sbin/sd-elevate sdsys-ssh on"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "calls: $(tr '\n' '|' < "$T/o3") out: $out"
: > "$T/o4"; out=$(OPEN_PRESET=y runblock "$OPEN" "" "$T/o4" 1 1 "sdsys-arm=closed"); rc=$?
row "O4 a failing --open-sdsys warns with the sudo command and goes on with status 0" \
    "$([ "$rc" = 0 ] && [[ "$out" == *"WARNING: sdsys over ssh could not be opened"* && "$out" == *"sudo /usr/local/sbin/sd-elevate sdsys-ssh on"* && "$out" != *"sdsys can now"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "rc=$rc out: $out"

# S1-S3: the summary line
out=$(runblock "$SUMM" "" /dev/null 1 0 "sdsys-arm=open")
row "S1 open -> 'SDSYS over ssh: open.' and the off command" \
    "$([[ "$out" == *"SDSYS over ssh: open."* && "$out" == *"sd-elevate sdsys-ssh off"* && "$out" != *"SDSYS over ssh: shut"* ]] && echo 0 || echo 1)" "$out"
out=$(runblock "$SUMM" "" /dev/null 1 0 "sdsys-arm=closed")
row "S2 closed -> 'SDSYS over ssh: shut.' and the sudo ... sdsys-ssh on command for a login with sudo" \
    "$([[ "$out" == *"SDSYS over ssh: shut."* && "$out" == *"sudo /usr/local/sbin/sd-elevate sdsys-ssh on"* && "$out" != *"open."* ]] && echo 0 || echo 1)" "$out"
sbad=""
for st in "absent" "sdsys-arm=legacy" ""; do
  out=$(runblock "$SUMM" "" /dev/null 1 0 "$st")
  [[ "$out" == *"SDSYS over ssh: not known."* && "$out" == *"sdsys-ssh status"* && "$out" != *"shut"* && "$out" != *"open."* ]] || sbad="$sbad '$st'"
done
row "S3 any other state -> 'not known' and the status command, claiming nothing" "$([ -z "$sbad" ] && echo 0 || echo 1)" "wrong for:$sbad"
pbad=""
for pw in "set" "kept from the previous install"; do
  out=$(PWS="$pw" runblock "$SUMM" "" /dev/null 1 0 "sdsys-arm=open"); [[ "$out" != *"sudo passwd sdsys"* ]] || pbad="$pbad '$pw'->told"
done
for pw in "not set" "not set - there was no terminal to ask at"; do
  out=$(PWS="$pw" runblock "$SUMM" "" /dev/null 1 0 "sdsys-arm=open"); [[ "$out" == *"sdsys has no Linux password yet"* && "$out" == *"sudo passwd sdsys"* ]] || pbad="$pbad '$pw'->silent"
done
row "S4 open with no sdsys Linux password says ssh cannot let it in until sudo passwd sdsys; with one set or kept it says nothing" "$([ -z "$pbad" ] && echo 0 || echo 1)" "$pbad"

# W1-W3: the installer as text
code=$(grep -n -v '^ *#' "$INST")
opens=$(printf '%s\n' "$code" | grep -E 'ssh-forcecommand[^#]*--open-sdsys|sd-elevate[^#]*sdsys-ssh on' | grep -v -E ':\s*echo ' || true)
n_open=$(printf '%s\n' "$opens" | grep -c . || true)
in_block=$(printf '%s\n' "$OPEN" | grep -c -E 'ssh-forcecommand --open-sdsys' || true)
row "W1 --open-sdsys is run in the SDSYS-SSH-OPEN block only" "$([ "$n_open" = 1 ] && [ "$in_block" = 1 ] && echo 0 || echo 1)" "lines: $opens"
ln() { grep -n -m1 -E "$1" "$INST" | cut -d: -f1; }
lg=$(ln '^# GATES-ASK-END'); la=$(ln '^# SDSYS-SSH-ASK-BEGIN'); lb=$(ln '^if sudo /usr/local/sbin/ssh-forcecommand --install; then')
lp=$(ln 'echo "2 of 3: Password for the LINUX sdsys account"'); lo=$(ln '^# SDSYS-SSH-OPEN-BEGIN'); ls=$(ln '^# SDSYS-SSH-SUMMARY-BEGIN')
echo "  W2 lines: gates-ask-end=$lg ask=$la boundary=$lb password=$lp open=$lo summary=$ls"
row "W2 order: gates question, sdsys ssh question, ssh boundary, sdsys password, open, summary" \
    "$([ -n "$lg" ] && [ -n "$la" ] && [ -n "$lb" ] && [ -n "$lp" ] && [ -n "$lo" ] && [ -n "$ls" ] && [ "$lg" -lt "$la" ] && [ "$la" -lt "$lb" ] && [ "$lb" -lt "$lp" ] && [ "$lp" -lt "$lo" ] && [ "$lo" -lt "$ls" ] && echo 0 || echo 1)" "out of order"
old=$(grep -n -F 'open it with  remote.sdsys on  at the SD prompt' "$INST" || true)
row "W3 the old summary line, unusable on a server with no screen, is gone" "$([ -z "$old" ] && echo 0 || echo 1)" "$old"

echo "test-install-sdsysssh: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-sdsysssh: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
