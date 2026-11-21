#!/bin/bash
# test-install-restorewarn.sh - S.292 (22 Nov 2026): what an install or an uninstall could not put back is collected and printed ONCE, as a boxed bold red
# block with the exact command for each (owner, 21 Nov 2026, Windows chat, relayed T0800: "if the admin says not to delete during a deletion then the system
# should be put back exactly as it was before the uninstall.  If that is impossible then the admin needs to be warned during the install the exact steps they
# must take to restore the system exactly as it was." and "If there are warnings they should not be buried in other text.  They need to be explicit, stand out
# so that they can not be missed.").  No sudo, no install, no systemd.  Exit 0 every row held, 1 one did not, 2 it could not run.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-restorewarn.sh [--selftest]
#
# THE BLOCK.  installsdcore.sh and deletesdcore.sh each hold the text between "# RESTORE-WARN-BEGIN" and "# RESTORE-WARN-END": restore_warn (collect one
# record), restore_warn_import (collect the records another script wrote to $SD_RESTORE_WARN_FILE) and restore_warn_block (print them).  The two copies must be
# byte for byte equal (B1).  This cuts the block out and runs it under the installer's own `set -euo pipefail` and IFS (F rows), then reads every CALL SITE as
# text (T rows): the closing block under the install's banner, the jobs, the API note, the API firewall rule, the sdsys ssh arm, the install-over hand-off, and
# the uninstaller's three "could not save" sites.  The behaviour of the sites that cut blocks (jobs, API note, sdsys ssh) is held by test-install-jobskeep.sh,
# test-install-keepaccess.sh, test-install-sdsysssh.sh and test-delete-sdsysssh.sh.  It cannot say what a real terminal shows: that is a real-install row.
#
# --selftest breaks the scripts in the ways listed at the end and requires the rows to notice each one.
set -uo pipefail
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
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real scripts do not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real scripts pass"
  mutant copies-differ       r 's/printf .\\n\\033\[1;31m%s\\n# %s\\n%s\\n. "\$rule"/printf "\\n\\033[1;31m%s\\n# %s\\n%s\\n" "$rule"/'
  mutant not-bold-red        i 's/\\033\[1;31m%s/\\033[0;31m%s/'
  mutant no-reset            i 's/printf .%s\\033\[0m\\n\\n. "\$rule"/printf "%s\\n\\n" "$rule"/'
  mutant prints-when-empty   i 's/^    \[ "\${#restore_warns\[@\]}" -gt 0 \] || return 0$/    :/'
  mutant no-numbering        i 's/printf .%s. %s\\n. "\$n" /printf "%s %s\\n" "-" /'
  mutant file-not-written    i 's/^    if \[ -n "\${SD_RESTORE_WARN_FILE:-}" \]; then printf/    if false; then printf/'
  mutant import-ignored      i 's/^    \[ -f "\$1" \] || return 0$/    return 0/'
  mutant install-block-gone  i 's/^restore_warn_block "THE INSTALL COULD NOT PUT BACK.*$/:/'
  mutant jobs-silent         i '/^                restore_warn "Scheduled job \$name was NOT scheduled again: its saved/d'
  mutant api-note-silent     i 's/^elif sudo test -e \/home\/sd\/api-access.saved || sudo test -L \/home\/sd\/api-access.saved; then$/elif false; then/'
  mutant fw-claim-unconditional i 's/ \&\& \[ "\${api_fw_added:-n}" = y \]; then$/; then/'
  mutant fw-failure-silent   i 's/^            restore_warn "The \$fw_tool rule for the API.*$/            :/'
  mutant ssh-arm-silent      i 's/^        restore_warn "SDSYS over ssh was open before the uninstall and could not be opened again.*$/        :/'
  mutant over-no-file        i 's/^    export SD_RESTORE_WARN_FILE="\$restore_warn_file"$/    :/'
  mutant over-no-import      i 's/^    restore_warn_import "\$restore_warn_file"$/    :/'
  mutant deleter-no-block    r 's/^restore_warn_block "THE UNINSTALL COULD NOT SAVE.*$/:/'
  mutant deleter-api-silent  r '/^                restore_warn "API access from other computers is open, but the note/d'
  mutant deleter-jobs-silent r '/^                restore_warn "Scheduled job \$jf: its definition could not be saved, so/d'
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
has() { printf '%s\n' "$1" | grep -qF -- "$2"; }
run_block() {   # run_block FILE 'script' -> output: the block under the installer's own options, then the script
  BLOCKFILE="$1" SCRIPT="$2" bash -c '
    set -euo pipefail
    IFS=$'"'"'\n\t'"'"'
    . "$BLOCKFILE"
    eval "$SCRIPT"
  ' 2>&1
}
ESC=$'\033'

row "B1 the two copies of the block (installer and remover) are byte for byte equal" "$(cmp -s "$T/inst-block.sh" "$T/del-block.sh" && echo 0 || echo 1)" "$(diff "$T/inst-block.sh" "$T/del-block.sh" | head -4)"

out="$(run_block "$T/inst-block.sh" 'restore_warn_block "H"')"
row "F1 NULL CASE: no records, so the block prints NOTHING at all" "$([ -z "$out" ] && echo 0 || echo 1)" "[$out]"
out="$(run_block "$T/inst-block.sh" 'restore_warn "API was open" "remote.api on"; restore_warn_block "THE HEADING"')"
nb="$(printf '%s\n' "$out" | grep -c -E '^(.\[1;31m)?#{80}(.\[0m)?$' || true)"   # the first rule carries the colour start, the last one the reset
row "F2 one record with a command: the heading, '1. what', 'Type:  command', three rules, bold red at the start and a reset at the end" \
  "$(has "$out" "# THE HEADING" && has "$out" "1. API was open" && has "$out" "       Type:  remote.api on" && has "$out" "${ESC}[1;31m" && printf '%s' "$out" | grep -qF "${ESC}[0m" && [ "$nb" = 3 ] && echo 0 || echo 1)" "rules=$nb out=$out"
out="$(run_block "$T/inst-block.sh" 'restore_warn "only words"; restore_warn_block "H"')"
row "F3 a record with no command prints no 'Type:' line" "$(has "$out" "1. only words" && ! has "$out" "Type:" && echo 0 || echo 1)" "$out"
out="$(run_block "$T/inst-block.sh" 'restore_warn "first" "c1"; restore_warn "second" "c2"; restore_warn_block "H"')"
l1="$(printf '%s\n' "$out" | grep -n -F '1. first' | cut -d: -f1)"; l2="$(printf '%s\n' "$out" | grep -n -F '2. second' | cut -d: -f1)"
row "F4 two records are numbered 1 and 2 in the order collected, each with its command" "$([ -n "$l1" ] && [ -n "$l2" ] && [ "$l1" -lt "$l2" ] && has "$out" "Type:  c1" && has "$out" "Type:  c2" && echo 0 || echo 1)" "$out"
CMD='sudo x job-set a\ b ;"q" $HOME %s %d \n'
out="$(CMD="$CMD" run_block "$T/inst-block.sh" 'restore_warn "w" "$CMD"; restore_warn_block "H"')"
row "F5 a command with spaces, quotes, a semicolon, \$, % and backslashes is printed exactly as given" "$(has "$out" "Type:  $CMD" && echo 0 || echo 1)" "$out"
WH='50% done %s \n and %d'
out="$(WH="$WH" run_block "$T/inst-block.sh" 'restore_warn "$WH" "c"; restore_warn_block "H"')"
row "F6 the WHAT text is printed literally too (no format characters acted on)" "$(has "$out" "1. $WH" && echo 0 || echo 1)" "$out"
rm -f "$T/rw1"; run_block "$T/inst-block.sh" 'restore_warn "a" "b"' > /dev/null
export_out="$(SD_RESTORE_WARN_FILE="$T/rw1" run_block "$T/inst-block.sh" 'restore_warn "one" "cmd one"; restore_warn "two" ""')"
row "F7 with SD_RESTORE_WARN_FILE set each record is appended there as 'what<TAB>command'; with it unset nothing is written" \
  "$([ "$(wc -l < "$T/rw1")" = 2 ] && [ "$(sed -n 1p "$T/rw1")" = "$(printf 'one\tcmd one')" ] && [ "$(sed -n 2p "$T/rw1")" = "$(printf 'two\t')" ] && [ ! -e "$T/rw2" ] && echo 0 || echo 1)" "$(cat -A "$T/rw1" 2>&1 | head -3)"
printf 'from file\tcmd from file\n\nlonely line\n' > "$T/imp"
out="$(IMP="$T/imp" NONE="$T/none" run_block "$T/inst-block.sh" 'restore_warn "first" "c0"; restore_warn_import "$IMP"; restore_warn_import "$NONE"; restore_warn_block "H"')"
n3="$(printf '%s\n' "$out" | grep -c -E '^[0-9]+\. ' || true)"
row "F8 import adds the file's records after the ones already collected; a line with no tab is a record with no command; a blank line and a missing file add nothing" \
  "$(has "$out" "1. first" && has "$out" "2. from file" && has "$out" "Type:  cmd from file" && has "$out" "3. lonely line" && [ "$n3" = 3 ] && echo 0 || echo 1)" "$out"
rm -f "$T/rt"
SD_RESTORE_WARN_FILE="$T/rt" run_block "$T/del-block.sh" 'restore_warn "from the uninstaller" "sudo thing one"' > /dev/null
out="$(IMP="$T/rt" run_block "$T/inst-block.sh" 'restore_warn_import "$IMP"; restore_warn_block "H"')"
row "F9 ROUND TRIP: a record the REMOVER's block writes to the hand-off file comes out of the INSTALLER's block, with its command" "$(has "$out" "1. from the uninstaller" && has "$out" "Type:  sudo thing one" && echo 0 || echo 1)" "$out"

# ---- the call sites, read as text ---------------------------------------------------------------------------------------------
BANNER='printf "%bThe SD server is installed.%b\n" "$RED" "$NC"'
l_ban="$(grep -n -x -F -m1 -- "$BANNER" "$INSTALLER" | cut -d: -f1)"
l_call="$(grep -n -F -m1 'restore_warn_block "THE INSTALL COULD NOT PUT BACK EVERYTHING YOU KEPT.' "$INSTALLER" | cut -d: -f1)"
l_sep="$(awk -v s="${l_call:-0}" 'NR>s && $0 == "echo \"---------------------------\"" {print NR; exit}' "$INSTALLER")"
row "T1 the install prints the block right under its banner, before the rest of the closing summary" \
  "$([ -n "$l_ban" ] && [ -n "$l_call" ] && [ -n "$l_sep" ] && [ "$l_ban" -lt "$l_call" ] && [ $((l_sep - l_call)) -le 3 ] && echo 0 || echo 1)" "banner $l_ban, call $l_call, next rule $l_sep"
jobs="$(awk '/^restore_saved_jobs\(\)/,/^}/' "$INSTALLER")"
nj="$(printf '%s\n' "$jobs" | grep -c 'restore_warn "Scheduled job' || true)"
row "T2 restore_saved_jobs collects BOTH kinds of failure (a refused definition, an unreadable one) and quotes the command with %q" \
  "$([ "$nj" = 2 ] && printf '%s\n' "$jobs" | grep -qF "%q job-set %q %q %s" && echo 0 || echo 1)" "calls=$nj"
keep="$(awk '/^# API-KEEP-BEGIN$/,/^# API-KEEP-END$/' "$INSTALLER")"
row "T3 an API note that is there but not honoured is collected with 'remote.api on'" \
  "$(printf '%s\n' "$keep" | grep -qF 'elif sudo test -e /home/sd/api-access.saved || sudo test -L /home/sd/api-access.saved; then' && printf '%s\n' "$keep" | grep -qF '" "remote.api on"' && echo 0 || echo 1)"
ssh="$(awk '/^# SDSYS-SSH-STATE-BEGIN$/,/^# SDSYS-SSH-STATE-END$/' "$INSTALLER")"
ns="$(printf '%s\n' "$ssh" | grep -c 'restore_warn "' || true)"
row "T4 the sdsys ssh arm collects both a failed reopen and an untrusted note, each with the sd-elevate command" \
  "$([ "$ns" = 2 ] && [ "$(printf '%s\n' "$ssh" | grep -c '" "sudo /usr/local/sbin/sd-elevate sdsys-ssh on"')" = 2 ] && printf '%s\n' "$ssh" | grep -qF 'sdsys_ssh_note_seen' && echo 0 || echo 1)" "calls=$ns"
row "T5 an API firewall rule that fails is collected with the tool's own command, and the closing summary says 'was added' only when it was" \
  "$(grep -qF 'restore_warn "The $fw_tool rule for the API' "$INSTALLER" && grep -qF 'ufw) fw_cmd="sudo ufw allow $sd_api_port/tcp"' "$INSTALLER" && grep -qF 'sudo firewall-cmd --permanent --add-port=$sd_api_port/tcp && sudo firewall-cmd --reload' "$INSTALLER" && grep -qF 'if [ "$fw_tool" != none ] && [ "${api_fw_added:-n}" = y ]; then' "$INSTALLER" && ! grep -qxF 'if [ "$fw_tool" != none ]; then' "$INSTALLER" && echo 0 || echo 1)"
l_exp="$(grep -n -x -F -m1 '    export SD_RESTORE_WARN_FILE="$restore_warn_file"' "$INSTALLER" | cut -d: -f1)"
l_run="$(grep -n -x -F -m1 '    upgrade_over_existing "${dflt_git_folder}/deletesdcore.sh" || exit 1' "$INSTALLER" | cut -d: -f1)"
l_uns="$(grep -n -x -F -m1 '    unset SD_RESTORE_WARN_FILE' "$INSTALLER" | cut -d: -f1)"
l_imp="$(grep -n -x -F -m1 '    restore_warn_import "$restore_warn_file"' "$INSTALLER" | cut -d: -f1)"
row "T6 the install-over gives the uninstaller the hand-off file, takes the variable away again, and imports the records" \
  "$([ -n "$l_exp" ] && [ -n "$l_run" ] && [ -n "$l_uns" ] && [ -n "$l_imp" ] && [ "$l_exp" -lt "$l_run" ] && [ "$l_run" -lt "$l_uns" ] && [ "$l_uns" -lt "$l_imp" ] && echo 0 || echo 1)" "export $l_exp, run $l_run, unset $l_uns, import $l_imp"
dapi="$(awk '/^# API-SAVE-BEGIN$/,/^# API-SAVE-END$/' "$REMOVER")"; dssh="$(awk '/^# SDSYS-SSH-SAVE-BEGIN$/,/^# SDSYS-SSH-SAVE-END$/' "$REMOVER")"; djob="$(awk '/^# JOBS-SAVE-BEGIN$/,/^# JOBS-SAVE-END$/' "$REMOVER")"
l_tidy="$(grep -n -x -F -m1 '# HOMESD-TIDY-END' "$REMOVER" | cut -d: -f1)"; l_dblk="$(grep -n -F -m1 'restore_warn_block "THE UNINSTALL COULD NOT SAVE' "$REMOVER" | cut -d: -f1)"
l_done="$(grep -n -F -m1 'echo "The deletesdcore.sh script has completed."' "$REMOVER" | cut -d: -f1)"
row "T7 the remover collects its three 'could not save' cases (API note, sdsys ssh note, each job's definition with job-set) and prints its block after the tidy-up, before 'has completed'" \
  "$(printf '%s\n' "$dapi" | grep -qF '" "remote.api on"' && printf '%s\n' "$dssh" | grep -qF '" "sudo /usr/local/sbin/sd-elevate sdsys-ssh on"' && [ "$(printf '%s\n' "$djob" | grep -c 'restore_warn "Scheduled job')" = 2 ] && printf '%s\n' "$djob" | grep -qF 'job-set %q %q %s' && [ -n "$l_tidy" ] && [ -n "$l_dblk" ] && [ -n "$l_done" ] && [ "$l_tidy" -lt "$l_dblk" ] && [ "$l_dblk" -lt "$l_done" ] && echo 0 || echo 1)" "tidy $l_tidy, block $l_dblk, completed $l_done"
hi="$(sed -n 's/^restore_warn_block "\(THE INSTALL[^"]*\)"$/\1/p' "$INSTALLER" | head -1)"; hr="$(sed -n 's/^restore_warn_block "\(THE UNINSTALL[^"]*\)"$/\1/p' "$REMOVER" | head -1)"
row "T8 both headings are in CAPITAL LETTERS and say what to do" "$([ -n "$hi" ] && [ -n "$hr" ] && [ "$hi" = "${hi^^}" ] && [ "$hr" = "${hr^^}" ] && has "$hi" "DO THESE STEPS" && has "$hr" "DO THESE STEPS" && echo 0 || echo 1)" "[$hi] [$hr]"

echo
echo "test-install-restorewarn: $passed passed, $failed failed"
[ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]
