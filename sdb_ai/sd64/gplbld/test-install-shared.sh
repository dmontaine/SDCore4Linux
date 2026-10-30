#!/bin/bash
#
# test-install-shared.sh - the installer's two pieces for the shared account (S.66): shared_preflight and the creation block.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-shared.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-shared.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-shared.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd (bin/sd is a stub), no groupadd.  Everything happens in a scratch
# directory: the two places the installer looks for a register record are rewritten into it.  Exit 0 every row passed, 1 a row
# failed, 2 it could not run (a refusal to pass on nothing: a missing piece, or a stub that was never called, is exit 2).
#
# WHAT IT RUNS.  The function shared_preflight and the text between "# SHARED-CREATE-BEGIN" and "# SHARED-CREATE-END" are cut out of
# the installer, every "/home/sd/" in them is rewritten to the scratch directory, and each is run under the installer's OWN
# "set -euo pipefail" with sudo, stat and getent replaced by functions that report what the scenario says (a scratch directory cannot
# be sdusers 2775).  bin/sd is a stub that does what the real create-account does in each scenario, and that REFUSES when the
# one-shot marker is not there, as the real one does (message 11516).
#
#   P   the preflight: no account passes; "ours" (line 1 /home/sd/group_accounts/shared, line 3 sdg_shared) passes in either place; a
#       foreign account (wrong line 1, wrong line 3, an empty record) in either place refuses with 1, names the register file and says
#       nothing was changed.  The null case: both places must actually have been looked at.
#   C   the creation block: a good creation prints the success line; a stub that fails still removes the marker and says the account
#       was not registered; a wrong group, a wrong mode, a wrong directory group and an extra member each print their WARNING and the
#       success line does NOT appear; a registered account is kept and the stub is NOT called; a directory without a register is
#       a warning and the stub is NOT called.  The marker was there when the stub ran and is gone afterwards in every case that ran it.
#
# ANCHORED ON THE SUCCESS WORDING.  "Registered shared as a group account (group: sdg_shared)" is printed only when everything is
# right.  Every failing scenario is judged on that line being ABSENT and on its own WARNING being present; the good scenario on the
# line being present and no WARNING.
#
# NOT MEASURED HERE, and said so: that sd-elevate makes the group, the mode and the owner a real install gives (witness-accounts.sh),
# that the real create-account refuses without the marker (sandbox-shared.py cannot run groupadd either), or the order of the pieces
# in the whole installer (test-shared-units.py I2 and I3).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

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
  mutant preflight-lets-foreign-through '/^shared_preflight() {/,/^}/ s/    return 1$/    return 0/'
  mutant preflight-forgets-line3        '/^shared_preflight() {/,/^}/ s/ \&\& \[ "\$line3" = "sdg_shared" \]//'
  mutant preflight-forgets-line1        '/^shared_preflight() {/,/^}/ s/\[ "\$line1" = "\/home\/sd\/group_accounts\/shared" \] \&\& //'
  mutant preflight-forgets-live-register '/^shared_preflight() {/,/^}/ s/ "\${sdsysdir}\/accounts\/shared"; do/; do/'
  mutant preflight-does-not-name-file   '/^shared_preflight() {/,/^}/ s/Its register record is:  \$reg/Its register record is:  (not named)/'
  mutant preflight-says-nothing-unchanged '/^shared_preflight() {/,/^}/ s/Nothing has been changed\./Something has been changed./'
  mutant marker-not-made                's/^    sudo touch "\$shared_marker"$/    true/'
  mutant marker-not-removed             's/^    sudo rm -f "\$shared_marker"$/    true/'
  mutant failed-create-not-tolerated    's/create-account GROUP shared || shared_rc=\$?/create-account GROUP shared/'
  mutant success-line-unguarded         's/^    if \[ "\$shared_ok" = yes \]; then$/    if true; then/'
  mutant wrong-group-not-reported       's/if \[ "\$shared_line3" != "sdg_shared" \]; then/if false; then/'
  mutant wrong-mode-not-reported        's/if \[ "\$shared_stat" != "sdusers 2775" \]; then/if false; then/'
  mutant extra-members-not-reported     's/^        elif \[ -n "\$shared_extra" \]; then$/        elif false; then/'
  mutant not-registered-not-reported    's/^    if \[ -z "\$shared_line1" \]; then$/    if false; then/'
  mutant kept-account-recreated         's/^if sudo test -f "\$shared_reg"; then$/if false; then/'
  mutant directory-without-register-made 's/^elif sudo test -d "\$shared_dir"; then$/elif false; then/'
  mutant creates-without-internal       's/sudo bin\/sd -internal create-account GROUP shared/sudo bin\/sd create-account GROUP shared/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST"; grep -m1 -E '^IFS=' "$INST")        # 30 Oct 26 (S.89): the installer's IFS too - a block must be run under both
case "$OPTS" in *IFS=*) ;; *) echo "test-install-shared: CANNOT RUN - no IFS line in the installer (S.89)"; exit 2;; esac
PRE=$(awk '/^shared_preflight\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
BLK=$(awk '/^# SHARED-CREATE-BEGIN/{f=1;next} /^# SHARED-CREATE-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-shared: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$PRE" ]  && { echo "test-install-shared: CANNOT RUN - no shared_preflight function in the installer (nothing to check)"; exit 2; }
[ -z "$BLK" ]  && { echo "test-install-shared: CANNOT RUN - no block between SHARED-CREATE-BEGIN and SHARED-CREATE-END (nothing to check)"; exit 2; }
echo "preflight : $(printf '%s\n' "$PRE" | wc -l) lines;  creation block: $(printf '%s\n' "$BLK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# the installer's two places, moved into the scratch directory (a function that does not mention the real path is not what runs)
SUB() { sed -e "s#/home/sd/#$T/home/sd/#g"; }
PRE_T=$(printf '%s\n' "$PRE" | SUB)
BLK_T=$(printf '%s\n' "$BLK" | SUB)
OURS1="$T/home/sd/group_accounts/shared"         # what the installer's preflight expects on line 1, rewritten the same way
printf '%s\n' "$PRE_T" | grep -q -F "$OURS1" || { echo "test-install-shared: CANNOT RUN - the preflight does not mention /home/sd/group_accounts/shared"; exit 2; }
export PRE_T BLK_T OPTS T OURS1

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}

reset() { rm -rf "$T/home" "$T/sdsys" "$T/work"; mkdir -p "$T/home/sd/accounts" "$T/home/sd/group_accounts" "$T/sdsys/accounts" "$T/work/bin"; : > "$T/sudo.log"; : > "$T/sd.log"; }
register() {   # register FILE LINE1 LINE2 LINE3
  printf '%s\n%s\n%s\n' "$2" "$3" "$4" > "$1"
}

# ---- P. the preflight ----------------------------------------------------------------------------------------------------
run_pre() {   # prints the output, then RC=n
  SUDO_LOG="$T/sudo.log" SDSYSDIR="$T/sdsys" bash -c '
      eval "$OPTS"
      sdsysdir="$SDSYSDIR"; RED=; NC=
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$SUDO_LOG"; "$@"; }      # S.89: "$*" joins with the first character of IFS, a newline under the installer IFS
      eval "$PRE_T"
      rc=0; shared_preflight || rc=$?
      echo "RC=$rc"' 2>&1
}

echo "--- P: the preflight"
reset
OUT=$(run_pre)
row "P1 no shared account anywhere: passes (RC=0)" "$(printf '%s' "$OUT" | grep -q '^RC=0$' && echo 0 || echo 1)" "$OUT"
row "P1b ...and BOTH places were looked at (the null case: a preflight that looked at nothing passes too)" \
    "$(grep -q "test -f $T/home/sd/accounts/shared" "$T/sudo.log" && grep -q "test -f $T/sdsys/accounts/shared" "$T/sudo.log" && echo 0 || echo 1)" "sudo calls: $(tr '\n' ';' < "$T/sudo.log")"

reset; register "$T/home/sd/accounts/shared" "$OURS1" "" "sdg_shared"
OUT=$(run_pre)
row "P2 our own record in the SAVED register (a kept install): passes" "$(printf '%s' "$OUT" | grep -q '^RC=0$' && ! printf '%s' "$OUT" | grep -q 'already exists' && echo 0 || echo 1)" "$OUT"
row "P2b ...and the record was read (line 1 and line 3), not skipped" \
    "$(grep -q "sed -n 1p $T/home/sd/accounts/shared" "$T/sudo.log" && grep -q "sed -n 3p $T/home/sd/accounts/shared" "$T/sudo.log" && echo 0 || echo 1)" "sudo calls: $(tr '\n' ';' < "$T/sudo.log")"
reset; register "$T/sdsys/accounts/shared" "$OURS1" "" "sdg_shared"
OUT=$(run_pre)
row "P3 our own record in the LIVE register: passes" "$(printf '%s' "$OUT" | grep -q '^RC=0$' && echo 0 || echo 1)" "$OUT"
reset; register "$T/home/sd/accounts/shared" "$OURS1" "" "sdg_shared"; register "$T/sdsys/accounts/shared" "$OURS1" "" "sdg_shared"
OUT=$(run_pre)
row "P3b our own record in both: passes" "$(printf '%s' "$OUT" | grep -q '^RC=0$' && echo 0 || echo 1)" "$OUT"

foreign() {   # name, where(saved|live), line1, line3
  reset
  local f; [ "$2" = saved ] && f="$T/home/sd/accounts/shared" || f="$T/sdsys/accounts/shared"
  register "$f" "$3" "someone's account" "$4"
  OUT=$(run_pre)
  row "$1 refuses with RC=1" "$(printf '%s' "$OUT" | grep -q '^RC=1$' && echo 0 || echo 1)" "$OUT"
  row "${1%% *}b ...names the register file, says nothing has been changed, and shows what line 1 and line 3 were" \
      "$(printf '%s' "$OUT" | grep -q -F "Its register record is:  $f" && printf '%s' "$OUT" | grep -q 'Nothing has been changed' && printf '%s' "$OUT" | grep -q -F "line 1 is '$3'" && printf '%s' "$OUT" | grep -q -F "line 3 is '$4'" && echo 0 || echo 1)" "$OUT"
}
foreign "P4 a foreign shared (line 1 is someone else's directory), saved" saved "/home/jack/shared" "sdg_shared"
foreign "P5 a foreign shared (line 3 is sdusers), live" live "$OURS1" "sdusers"
foreign "P6 a foreign shared (both wrong), live" live "/home/sd/user_accounts/shared" "sdu_shared"
foreign "P7 a foreign shared (line 3 is sdg_shared but line 1 is the user-accounts directory), saved" saved "/home/sd/user_accounts/shared" "sdg_shared"
reset; : > "$T/home/sd/accounts/shared"
OUT=$(run_pre)
row "P8 an EMPTY register record named shared is not ours: refuses" "$(printf '%s' "$OUT" | grep -q '^RC=1$' && printf '%s' "$OUT" | grep -q -F "line 1 is '<empty>'" && echo 0 || echo 1)" "$OUT"

# ---- C. the creation block -----------------------------------------------------------------------------------------------
# the stub bin/sd: what the real create-account does for GROUP shared, by scenario.  It writes its own log first, notes whether
# the one-shot marker was there, and REFUSES when it was not (message 11516).
cat > "$T/stub-sd" <<'STUB'
#!/bin/bash
echo "ARGS: $*" >> "$SD_LOG"
if [ -e "$MARKER" ]; then echo "MARKER-PRESENT" >> "$SD_LOG"; else echo "MARKER-ABSENT" >> "$SD_LOG"; echo "stub: the account name shared is reserved"; exit 1; fi
rm -f "$MARKER"        # the real create-account consumes it at once
case "$SCENARIO" in
  fail)  echo "stub: create failed"; exit 1 ;;
  *)     mkdir -p "$SHARED_DIR"
         printf '%s\n%s\n%s\n' "$SHARED_DIR" "" "${REG_GROUP:-sdg_shared}" > "$SHARED_REG"
         echo "stub: registered"; exit 0 ;;
esac
STUB
chmod +x "$T/stub-sd"

run_blk() {   # run_blk SCENARIO STAT GETENT -- prints the output, then REACHED-END
  SCENARIO="$1" STAT_OUT="$2" GETENT_OUT="$3" SD_LOG="$T/sd.log" MARKER="$T/sdsys/\$shared.make" SHARED_DIR="$T/home/sd/group_accounts/shared" SHARED_REG="$T/sdsys/accounts/shared" \
  REG_GROUP="${REG_GROUP:-sdg_shared}" SUDO_LOG="$T/sudo.log" SDSYSDIR="$T/sdsys" bash -c '
      eval "$OPTS"
      sdsysdir="$SDSYSDIR"; RED=; NC=
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$SUDO_LOG"; "$@"; }      # S.89: "$*" joins with the first character of IFS, a newline under the installer IFS
      stat() { printf "%s\n" "$STAT_OUT"; }
      getent() { printf "%s\n" "$GETENT_OUT"; }
      cd "$T/work"
      eval "$BLK_T"
      echo "REACHED-END"' 2>&1
}
GOODSTAT="sdusers 2775"
GOODENT="sdg_shared:x:1234:root,sdsys"
OKLINE="Registered shared as a group account (group: sdg_shared)"


echo "--- C1: a good creation"
reset; cp "$T/stub-sd" "$T/work/bin/sd"
OUT=$(run_blk good "$GOODSTAT" "$GOODENT")
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "C1 the stub was RUN, with exactly: -internal create-account GROUP shared (the null case: a block that never ran it passes nothing)" \
    "$(grep -q '^ARGS: -internal create-account GROUP shared$' "$T/sd.log" && echo 0 || echo 1)" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
row "C1b ...the marker was there when it ran, and it is gone afterwards" \
    "$(grep -q '^MARKER-PRESENT$' "$T/sd.log" && [ ! -e "$T/sdsys/\$shared.make" ] && echo 0 || echo 1)" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
row "C1c ...the success line is printed, no WARNING is, and the block reached its end" \
    "$(printf '%s' "$OUT" | grep -q -F "$OKLINE" && ! printf '%s' "$OUT" | grep -q 'WARNING' && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "no success line, or a WARNING"
row "C1d ...and it says what the system actually holds (register line 1 and 3, the directory's group and mode, the members)" \
    "$(printf '%s' "$OUT" | grep -q -F "line 1 '$T/home/sd/group_accounts/shared', line 3 'sdg_shared'" && printf '%s' "$OUT" | grep -q -F "group and mode 'sdusers 2775'" && printf '%s' "$OUT" | grep -q -F "members of sdg_shared: 'root,sdsys'" && echo 0 || echo 1)" "$OUT"
row "C1e ...and tells the installing user the two defaults (read on unless shared-read-off, write only with shared-write-on)" \
    "$(printf '%s' "$OUT" | grep -q -F 'modify.account <name> shared-read-off' && printf '%s' "$OUT" | grep -q -F 'modify.account <name> shared-write-on' && echo 0 || echo 1)" "$OUT"

echo "--- C2: the stub fails"
reset; cp "$T/stub-sd" "$T/work/bin/sd"
OUT=$(run_blk fail "" "")
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "C2 the stub ran, the marker is gone though the create failed, and set -e did not end the install" \
    "$(grep -q '^ARGS:' "$T/sd.log" && [ ! -e "$T/sdsys/\$shared.make" ] && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "marker left, or the block ended: $(ls "$T/sdsys")"
row "C2b ...it says the account was not registered, and the success line is NOT printed" \
    "$(printf '%s' "$OUT" | grep -q 'WARNING: the shared account was not registered' && ! printf '%s' "$OUT" | grep -q -F "$OKLINE" && echo 0 || echo 1)" "$OUT"

warn_case() {   # name, stat, getent, reg_group, wanted WARNING words
  reset; cp "$T/stub-sd" "$T/work/bin/sd"
  OUT=$(REG_GROUP="$4" run_blk good "$2" "$3")
  printf '%s\n' "$OUT" | sed 's/^/      | /' | grep -E 'WARNING|Registered|REACHED'
  row "$1 prints '$5' and the success line does NOT appear" \
      "$(printf '%s' "$OUT" | grep -q -F "$5" && ! printf '%s' "$OUT" | grep -q -F "$OKLINE" && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "$OUT"
  row "${1%% *}b ...and the marker is gone" "$([ ! -e "$T/sdsys/\$shared.make" ] && echo 0 || echo 1)" "marker left"
}
echo "--- C3: a registered account that is not right"
warn_case "C3 the account was registered with the group sdusers" "$GOODSTAT" "$GOODENT" "sdusers" "WARNING: shared was registered with group"
warn_case "C4 the directory has the wrong mode" "sdusers 775" "$GOODENT" "sdg_shared" "WARNING: the shared directory is"
warn_case "C5 the directory belongs to sdg_shared" "sdg_shared 2775" "$GOODENT" "sdg_shared" "WARNING: the shared directory is"
warn_case "C6 an extra member of sdg_shared (left by an earlier install)" "$GOODSTAT" "sdg_shared:x:1234:root,sdsys,jack" "sdg_shared" "WARNING: sdg_shared has members besides root and sdsys"
warn_case "C7 the group does not exist" "$GOODSTAT" "" "sdg_shared" "WARNING: the group sdg_shared does not exist or has no members"
reset; cp "$T/stub-sd" "$T/work/bin/sd"
OUT=$(run_blk good "$GOODSTAT" "sdg_shared:x:1234:root,sdsys,jack,jill")
row "C6b ...the extra members are NAMED" "$(printf '%s' "$OUT" | grep -q -F 'besides root and sdsys: jack,jill' && echo 0 || echo 1)" "$OUT"

echo "--- C8: nothing to do"
reset; cp "$T/stub-sd" "$T/work/bin/sd"; register "$T/sdsys/accounts/shared" "$OURS1" "" "sdg_shared"
OUT=$(run_blk good "$GOODSTAT" "$GOODENT")
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "C8 a registered account is kept: the stub is NOT run, no marker is made, and no success line is claimed" \
    "$([ ! -s "$T/sd.log" ] && [ ! -e "$T/sdsys/\$shared.make" ] && printf '%s' "$OUT" | grep -q 'already registered and is kept' && ! printf '%s' "$OUT" | grep -q -F "$OKLINE" && echo 0 || echo 1)" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
reset; cp "$T/stub-sd" "$T/work/bin/sd"; mkdir -p "$T/home/sd/group_accounts/shared"
OUT=$(run_blk good "$GOODSTAT" "$GOODENT")
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "C9 a directory without a register is a WARNING that touches nothing: the stub is NOT run, no marker, no success line" \
    "$([ ! -s "$T/sd.log" ] && [ ! -e "$T/sdsys/\$shared.make" ] && printf '%s' "$OUT" | grep -q 'WARNING' && printf '%s' "$OUT" | grep -q 'left exactly as it is' && ! printf '%s' "$OUT" | grep -q -F "$OKLINE" && echo 0 || echo 1)" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
reset
OUT=$(run_blk good "$GOODSTAT" "$GOODENT")
row "C10 with no stub at all the block still ends (set -e), says the account was not registered, and leaves no marker" \
    "$(printf '%s' "$OUT" | grep -q REACHED-END && printf '%s' "$OUT" | grep -q 'WARNING: the shared account was not registered' && [ ! -e "$T/sdsys/\$shared.make" ] && echo 0 || echo 1)" "$OUT"

echo "test-install-shared: $pass passed, $fail failed"
[ "$((pass + fail))" -eq 0 ] && { echo "test-install-shared: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
