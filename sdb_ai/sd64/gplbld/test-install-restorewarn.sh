#!/bin/bash
# test-install-restorewarn.sh - S.292, S.299 (22 Nov 2026): what an install or an uninstall could not put back is collected and printed ONCE, in bold red, with
# the line to type for each (owner, 21 Nov 2026, Windows chat, relayed T0800: "if the admin says not to delete during a deletion then the system should be put
# back exactly as it was before the uninstall.  If that is impossible then the admin needs to be warned during the install the exact steps they must take to
# restore the system exactly as it was." and "If there are warnings they should not be buried in other text.  They need to be explicit, stand out so that they
# can not be missed."; 22 Nov 2026: "use the same wording and format that windows is using").  No sudo, no install, no systemd.  Exit 0 every row held, 1 one
# did not, 2 it could not run.
#
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-restorewarn.sh [--selftest]
#
# S.299 IS THE DEFECT THIS CHECK MISSED: it matched that a command was printed, and the commands printed were refused when typed.  So the F rows compare the
# printed box whole, T2 is the CLOSED list of every item a script can print (a new item fails it until it is added here, with the line typed on an SD), and T3
# finds each verb and word in the verb's own program.  W holds the words to SD Core for Windows' installer, skipped with a notice when that tree is not here.
# The sites that cut blocks (jobs, API note, sdsys ssh) are run by test-install-jobskeep.sh, test-install-keepaccess.sh, test-install-sdsysssh.sh and
# test-delete-sdsysssh.sh.  It cannot say that a step works on an install: that is a real-install row.
#
# --selftest breaks the scripts in the ways listed at the end and requires the rows to notice each one.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THIS="$HERE/$(basename "${BASH_SOURCE[0]}")"
ROOT="$(cd "$HERE/../../.." && pwd)"
INSTALLER="${INSTALLER:-$ROOT/installsdcore.sh}"
REMOVER="${REMOVER:-$ROOT/deletesdcore.sh}"
ISS="${ISS:-/home/don/SDCoreProject/SDCore4Windows/sdb_ai/sd64/gplbld/sd.iss}"
SYS="$HERE/../sdsys"
passed=0; failed=0
row() {   # row "name" ok(0|1) ["detail"]
  if [ "$2" = 0 ]; then passed=$((passed+1)); echo "  [PASS] $1"
  else failed=$((failed+1)); echo "  [FAIL] $1${3:+   <- $3}"; fi
}

if [ "${1:-}" = "--selftest" ]; then
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, file (i or r), sed expression
    local f="$T/$1.sh" ei="$ROOT/installsdcore.sh" er="$ROOT/deletesdcore.sh" src
    if [ "$2" = i ]; then src="$ei"; else src="$er"; fi
    sed -e "$3" "$src" > "$f"
    if cmp -s "$src" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); return; fi
    if [ "$2" = i ]; then ei="$f"; else er="$f"; fi
    if INSTALLER="$ei" REMOVER="$er" bash "$THIS" > "$T/$1.out" 2>&1; then echo "  [MISSED] $1: the check still passed"; missed=$((missed+1))
    else echo "  [caught] $1"; caught=$((caught+1)); fi
  }
  echo "selftest: the real scripts first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real scripts do not pass:"; tail -12 "$T/real.out"; exit 1; }
  echo "  [ok] the real scripts pass"
  mutant copies-differ       r 's/At the colon prompt type:\\n/At the prompt type:\\n/'
  mutant not-bold-red        i 's/\\033\[1;31mWARNING: SOME/\\033[0;31mWARNING: SOME/'
  mutant no-reset            i 's/^    printf .\\033\[0m.$/    :/'
  mutant prints-when-empty   i 's/^    \[ "\${#restore_warns\[@\]}" -gt 0 \] || return 0$/    :/'
  mutant no-grouping         i 's/^        case "\$seen" in .*$/        :/'
  mutant no-indent           i "s/printf '     %s\\\\n' \"\\\${other#/printf '%s\\\\n' \"\\\${other#/"
  mutant printed-twice       i 's/^            case "\$shown" in .*$/            :/'
  mutant file-not-written   i 's/^    if \[ -n "\${SD_RESTORE_WARN_FILE:-}" \]; then printf/    if false; then printf/'
  mutant import-ignored      i 's/^    \[ -f "\$1" \] || return 0$/    return 0/'
  mutant install-block-gone  i 's/^restore_warn_block "To correct.*$/:/'
  mutant old-sudo-step       i 's/restore_warn "REMOTE ADMINISTRATION IS OFF." "remote.sdsys on"/restore_warn "REMOTE ADMINISTRATION IS OFF." "sudo sd-elevate sdsys-ssh on"/'
  mutant wrong-word          i 's/"THE API IS LOCAL ONLY." "remote.api on"/"THE API IS LOCAL ONLY." "remote.api open"/'
  mutant reason-comes-back   i 's/restore_warn "THE API IS LOCAL ONLY."/restore_warn "THE API IS LOCAL ONLY: the note was not trusted."/'
  mutant jobs-silent         i '/^            restore_warn "SCHEDULED JOBS COULD NOT/d'
  mutant fw-failure-silent   i 's/^            api_fw_failed=y.*$/            :/'
  mutant fw-words            i 's/remote.api local\\" for this/remote.api off\\" for this/; s/or "remote.api local" for this/or "remote.api off" for this/'
  mutant fw-claim-unconditional i 's/ \&\& \[ "\${api_fw_added:-n}" = y \]; then$/; then/'
  mutant over-no-file        i 's/^    export SD_RESTORE_WARN_FILE="\$restore_warn_file"$/    :/'
  mutant over-no-import      i 's/^    restore_warn_import "\$restore_warn_file"$/    :/'
  mutant deleter-no-block    r 's/^restore_warn_block "To correct.*$/:/'
  mutant deleter-says-now    r 's/^restore_warn_block "To correct, after the next install sign/restore_warn_block "To correct, sign/'
  mutant deleter-api-silent  r '/^                restore_warn "THE API IS LOCAL ONLY."/d'
  mutant deleter-jobs-silent r '/^            restore_warn "SCHEDULED JOBS COULD NOT/d'
  echo "selftest: $caught caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

for f in "$INSTALLER" "$REMOVER"; do [ -r "$f" ] || { echo "test-install-restorewarn: CANNOT RUN - $f is not there"; exit 2; }; done
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
echo "installer : $INSTALLER"; echo "remover   : $REMOVER"
awk '/^# RESTORE-WARN-BEGIN$/,/^# RESTORE-WARN-END$/' "$INSTALLER" > "$T/inst-block.sh"
awk '/^# RESTORE-WARN-BEGIN$/,/^# RESTORE-WARN-END$/' "$REMOVER" > "$T/del-block.sh"
for b in inst-block del-block; do
  grep -q '^restore_warn_block()' "$T/$b.sh" || { echo "test-install-restorewarn: CANNOT RUN - no RESTORE-WARN block in $b"; exit 2; }
done
run_block() {   # run_block FILE 'script' -> output: the block under the installer's own options, then the script
  BLOCKFILE="$1" SCRIPT="$2" bash -c '
    set -euo pipefail
    IFS=$'"'"'\n\t'"'"'
    . "$BLOCKFILE"
    eval "$SCRIPT"
  ' 2>&1
}
HOW='To correct, sign into Linux as sdsys, and start SD Core.'
HOWR='To correct, after the next install sign into Linux as sdsys, and start SD Core.'

row "B1 the two copies of the block (installer and remover) are byte for byte equal" "$(cmp -s "$T/inst-block.sh" "$T/del-block.sh" && echo 0 || echo 1)" "$(diff "$T/inst-block.sh" "$T/del-block.sh" | head -4)"

out="$(run_block "$T/inst-block.sh" 'restore_warn_block "H"')"
row "F1 NULL CASE: no records, so the block prints NOTHING at all" "$([ -z "$out" ] && echo 0 || echo 1)" "[$out]"
out="$(HOW="$HOW" run_block "$T/inst-block.sh" '
restore_warn "REMOTE ADMINISTRATION IS OFF." "remote.sdsys on"
restore_warn "SCHEDULED JOBS COULD NOT BE SCHEDULED AGAIN." "set.job add nightly backup-all daily 02:30"
restore_warn "THE API IS LOCAL ONLY." "remote.api on"
restore_warn "SCHEDULED JOBS COULD NOT BE SCHEDULED AGAIN." "set.job change often update-accounts hourly"
restore_warn_block "$HOW"; echo END')"
want="$(printf '%b' '\n\033[1;31mWARNING: SOME SETTINGS NEED TO BE FIXED.\n\n'\
"1. REMOTE ADMINISTRATION IS OFF.\n$HOW\nAt the colon prompt type:\n     remote.sdsys on\n\n"\
"2. SCHEDULED JOBS COULD NOT BE SCHEDULED AGAIN.\n$HOW\nAt the colon prompt type:\n     set.job add nightly backup-all daily 02:30\n     set.job change often update-accounts hourly\n\n"\
"3. THE API IS LOCAL ONLY.\n$HOW\nAt the colon prompt type:\n     remote.api on\n\n"\
'\033[0mEND')"
row "F2 the whole box, exactly: the heading, numbered items, how to correct, the commands 5 spaces in, one item per heading, bold red and a reset" "$([ "$out" = "$want" ] && echo 0 || echo 1)" "$(diff <(printf '%s\n' "$out") <(printf '%s\n' "$want") | head -8)"
out="$(run_block "$T/inst-block.sh" 'restore_warn "T." "remote.api on"; restore_warn "T." "remote.api on"; restore_warn_block "H"')"
row "F2b the same step collected twice (both scripts of an install-over) is printed once" "$([ "$(printf '%s\n' "$out" | grep -c '^     remote.api on$')" = 1 ] && echo 0 || echo 1)" "$out"
CMD='x a\ b ;"q" $HOME %s %d \n'
out="$(CMD="$CMD" run_block "$T/inst-block.sh" 'restore_warn "50% %s." "$CMD"; restore_warn_block "H"')"
row "F3 a heading and a command are printed literally (no format characters acted on)" "$(printf '%s\n' "$out" | grep -qxF -- "     $CMD" && printf '%s\n' "$out" | grep -qxF -- "1. 50% %s." && echo 0 || echo 1)" "$out"
rm -f "$T/rw1"
run_block "$T/inst-block.sh" 'restore_warn "a" "b"' > /dev/null
SD_RESTORE_WARN_FILE="$T/rw1" run_block "$T/inst-block.sh" 'restore_warn "one" "cmd one"' > /dev/null
row "F4 with SD_RESTORE_WARN_FILE set a record is appended there as 'heading<TAB>command'" "$([ "$(cat "$T/rw1" 2>/dev/null)" = "$(printf 'one\tcmd one')" ] && echo 0 || echo 1)"
rm -f "$T/rt"
SD_RESTORE_WARN_FILE="$T/rt" run_block "$T/del-block.sh" 'restore_warn "SAME." "from the uninstaller"' > /dev/null
out="$(IMP="$T/rt" NONE="$T/none" run_block "$T/inst-block.sh" 'restore_warn "SAME." "from the installer"; restore_warn_import "$IMP"; restore_warn_import "$NONE"; restore_warn_block "H"')"
row "F5 ROUND TRIP: the REMOVER's record comes out of the INSTALLER's box, in the same item; a missing file adds nothing" \
  "$(printf '%s\n' "$out" | grep -qxF '     from the uninstaller' && [ "$(printf '%s\n' "$out" | grep -c '^[0-9]\. ')" = 1 ] && echo 0 || echo 1)" "$out"

# ---- the call sites ---------------------------------------------------------------------------------------------
BANNER='printf "%bThe SD server is installed.%b\n" "$RED" "$NC"'
l_ban="$(grep -n -x -F -m1 -- "$BANNER" "$INSTALLER" | cut -d: -f1)"
l_call="$(grep -n -x -F -m1 -- "restore_warn_block \"$HOW\"" "$INSTALLER" | cut -d: -f1)"
row "T1 the install prints the box, with sdsys named, right under its banner" \
  "$([ -n "$l_ban" ] && [ -n "$l_call" ] && [ "$l_ban" -lt "$l_call" ] && [ $((l_call - l_ban)) -le 4 ] && echo 0 || echo 1)" "banner $l_ban, call $l_call"
calls() { grep -E '^ +restore_warn "' "$1" | sed 's/^ *//' | LC_ALL=C sort; }
wanti="$(LC_ALL=C sort <<'EOF'
restore_warn "THE API IS LOCAL ONLY." "remote.api on"
restore_warn "SCHEDULED JOBS COULD NOT BE SCHEDULED AGAIN." "$(job_step "$action" "$name" "$job" "$sched")"
restore_warn "REMOTE ADMINISTRATION IS OFF." "remote.sdsys on"
restore_warn "REMOTE ADMINISTRATION IS OFF." "remote.sdsys on"
EOF
)"
wantr="$(LC_ALL=C sort <<'EOF'
restore_warn "THE API IS LOCAL ONLY." "remote.api on"
restore_warn "REMOTE ADMINISTRATION IS OFF." "remote.sdsys on"
restore_warn "SCHEDULED JOBS COULD NOT BE SCHEDULED AGAIN." "$(job_step add "$jf" "$jb" "$js")"
EOF
)"
row "T2 the CLOSED list: every item either script can print is one of these, a heading in capitals and one line for the colon prompt" \
  "$([ "$(calls "$INSTALLER")" = "$wanti" ] && [ "$(calls "$REMOVER")" = "$wantr" ] && echo 0 || echo 1)" "$(diff <(calls "$INSTALLER") <(printf '%s\n' "$wanti") | head -4) $(diff <(calls "$REMOVER") <(printf '%s\n' "$wantr") | head -4)"
bad=""
for v in remote.api remote.sdsys set.job; do [ -f "$SYS/voc_template/$v" ] || bad="$bad no-verb:$v"; done
grep -qF "case action = 'ON'" "$SYS/gpl.bp/remoteapi" || bad="$bad remote.api-on"
grep -qF "case action = 'LOCAL'" "$SYS/gpl.bp/remoteapi" || bad="$bad remote.api-local"
grep -qF "if action # 'on' and action # 'off' then" "$SYS/gpl.bp/remotesdsys" || bad="$bad remote.sdsys-on"
grep -qF "if (action = 'add' or action = 'change') and n.words >= 5" "$SYS/gpl.bp/set_job" || bad="$bad set.job-add-change"
row "T3 each verb printed is one sdsys has, and its own program takes the word printed after it" "$([ -z "$bad" ] && echo 0 || echo 1)" "$bad"
FW='WARNING: NO FIREWALL RULE LETS OTHER COMPUTERS REACH THE SD CORE API. To allow it, in SD Core as an administrator:\n\n    remote.api on\n\nor "remote.api local" for this computer only.'
row "T4 an API firewall rule that fails gets Windows' warning under the box, and the summary says 'added' only when it was" \
  "$(grep -q '^            api_fw_failed=y' "$INSTALLER" && grep -qxF 'if [ "${api_fw_failed:-n}" = y ]; then' "$INSTALLER" && grep -qF -- "$FW" "$INSTALLER" && grep -qF 'if [ "$fw_tool" != none ] && [ "${api_fw_added:-n}" = y ]; then' "$INSTALLER" && echo 0 || echo 1)"
l_exp="$(grep -n -x -F -m1 '    export SD_RESTORE_WARN_FILE="$restore_warn_file"' "$INSTALLER" | cut -d: -f1)"
l_run="$(grep -n -x -F -m1 '    upgrade_over_existing "${dflt_git_folder}/deletesdcore.sh" || exit 1' "$INSTALLER" | cut -d: -f1)"
l_uns="$(grep -n -x -F -m1 '    unset SD_RESTORE_WARN_FILE' "$INSTALLER" | cut -d: -f1)"
l_imp="$(grep -n -x -F -m1 '    restore_warn_import "$restore_warn_file"' "$INSTALLER" | cut -d: -f1)"
row "T5 the install-over gives the uninstaller the hand-off file, takes the variable away again, and imports the records" \
  "$([ -n "$l_exp" ] && [ -n "$l_run" ] && [ -n "$l_uns" ] && [ -n "$l_imp" ] && [ "$l_exp" -lt "$l_run" ] && [ "$l_run" -lt "$l_uns" ] && [ "$l_uns" -lt "$l_imp" ] && echo 0 || echo 1)" "export $l_exp, run $l_run, unset $l_uns, import $l_imp"
l_tidy="$(grep -n -x -F -m1 '# HOMESD-TIDY-END' "$REMOVER" | cut -d: -f1)"; l_dblk="$(grep -n -x -F -m1 -- "restore_warn_block \"$HOWR\"" "$REMOVER" | cut -d: -f1)"
l_done="$(grep -n -F -m1 'echo "The deletesdcore.sh script has completed."' "$REMOVER" | cut -d: -f1)"
row "T6 the remover prints its box after the tidy-up, before 'has completed', and says the steps are for after the next install" \
  "$([ -n "$l_tidy" ] && [ -n "$l_dblk" ] && [ -n "$l_done" ] && [ "$l_tidy" -lt "$l_dblk" ] && [ "$l_dblk" -lt "$l_done" ] && echo 0 || echo 1)" "tidy $l_tidy, block $l_dblk, completed $l_done"

if [ -r "$ISS" ]; then
  bad=""
  for s in 'WARNING: SOME SETTINGS NEED TO BE FIXED.' 'REMOTE ADMINISTRATION IS OFF.' 'SCHEDULED JOBS COULD NOT BE SCHEDULED AGAIN.' 'At the colon prompt type:' \
           'To correct, sign into Windows as SDSYS, and start SD Core.' 'WARNING: NO FIREWALL RULE LETS OTHER COMPUTERS REACH THE SD CORE API. To allow it, '; do
    grep -qF -- "$s" "$ISS" || bad="$bad windows-changed:[$s]"
  done
  w='To correct, sign into Windows as SDSYS, and start SD Core.'; w="${w/Windows/Linux}"; w="${w/SDSYS/sdsys}"
  [ "$w" = "$HOW" ] || bad="$bad how"
  row "W the words are still SD Core for Windows' (only Linux and sdsys differ)" "$([ -z "$bad" ] && echo 0 || echo 1)" "$bad"
else
  echo "  [SKIP] W SD Core for Windows' installer is not at $ISS"
fi

echo
echo "test-install-restorewarn: $passed passed, $failed failed"
[ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]
