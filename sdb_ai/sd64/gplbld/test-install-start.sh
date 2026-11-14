#!/bin/bash
#
# test-install-start.sh - where a session starts, chosen at install (owner, 3 Nov 2026: "Can that be a question asked during the install?", then "the
# home/prompt question"): the installer's START-ASK and START-SET blocks and the deleter's START-SAVE block.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-start.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-start.sh --selftest
#
# FREE CHECK: no sudo (it is a function here), no install, no sd.  Everything happens in a scratch directory, where /home/sd is replaced by a scratch
# folder.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a block or the installer's set / IFS line missing).
#
#   A1  a fresh install (nothing saved), Enter: the home screen, the question offers (H/p);  A2  p: the prompt;  A3  "prompt": the prompt
#   A0  a fresh install asks once;  A4  an upgrade that saved terminal: the prompt, NOT ASKED (owner, 14 Nov 2026);  A5  an upgrade with the accounts
#       kept and nothing saved: the home screen, not asked;  A6  a saved file that says something else: the home screen, not asked
#   S1  terminal: set.start.default terminal is run by the installer's own sd, and the line says the prompt;  S2  the verb writes nothing: WARNING, ends 0
#   S3  menu: the verb is not run, the line says the home screen;  S4  the saved file is removed either way
#   D1  the deleter, keeping the accounts, saves start.default as start.default.saved, mode 644;  D2  DELETE (accounts removed): nothing saved
#   D3  no start.default: nothing saved
#   P   the question is asked after GATES-ASK and before the first sudo; START-SET follows MANUALS-PDF; no block has an exit
#
# NOT MEASURED HERE: the real set.start.default (sandbox-home's start rows) and a real install (the VM).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
ROOT="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$ROOT/installsdcore.sh}"
DEL="${DELETER:-$ROOT/deletesdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, file (inst|del), sed expression
    local name="$1" which="$2" expr="$3" src rc
    total=$((total+1))
    if [ "$which" = inst ]; then src="$ROOT/installsdcore.sh"; else src="$ROOT/deletesdcore.sh"; fi
    sed -e "$expr" "$src" > "$T/$name"
    if cmp -s "$src" "$T/$name"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    if [ "$which" = inst ]; then INSTALLER="$T/$name" bash "$THIS" > "$T/$name.out" 2>&1; else DELETER="$T/$name" bash "$THIS" > "$T/$name.out" 2>&1; fi
    rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1)); else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real scripts first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real scripts do not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real scripts pass"
  mutant default-prompt   inst '/^# START-ASK-BEGIN/,/^# START-ASK-END/ s/^start_choice=menu$/start_choice=terminal/'
  mutant ignores-saved    inst '/^# START-ASK-BEGIN/,/^# START-ASK-END/ s/ != menu \]; then start_choice=terminal; fi/ = never ]; then start_choice=terminal; fi/'
  mutant compiled-not-seen del '/^# START-SAVE-BEGIN/,/^# START-SAVE-END/ s/sudo test -e "\$sdsysdir\/gpl.bp.out\/tool_home" || //'
  mutant upgrade-asks     inst '/^# START-ASK-BEGIN/,/^# START-ASK-END/ s/^if \[ -n "\$start_saved" \] || \[ -d \/home\/sd\/user_accounts \]; then$/if false; then/'
  mutant kept-accounts-ask inst '/^# START-ASK-BEGIN/,/^# START-ASK-END/ s/ || \[ -d \/home\/sd\/user_accounts \]; then$/; then/'
  mutant judged-by-nothing inst '/^# START-SET-BEGIN/,/^# START-SET-END/ s/if sudo grep -qsx .terminal. "\$sdsysdir\/start.default"; then/if true; then/'
  mutant keeps-saved      inst '/^# START-SET-BEGIN/,/^# START-SET-END/{/rm -f \/home\/sd\/start.default.saved/d}'
  mutant saves-on-delete  del  '/^# START-SAVE-BEGIN/,/^# START-SAVE-END/ s/^if \[ "\$keep_accts" != "DELETE" \]; then/if true; then/'
  mutant old-install-to-menu del '/^# START-SAVE-BEGIN/,/^# START-SAVE-END/ s/^        echo terminal | sudo tee/        echo menu | sudo tee/'
  mutant no-old-install-rule del '/^# START-SAVE-BEGIN/,/^# START-SAVE-END/ s/ || sudo test -e "\$sdsysdir\/gpl.bp\/tool_home"; then/ || true; then/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
ASK=$(awk '/^# START-ASK-BEGIN/{f=1;next} /^# START-ASK-END/{f=0} f{print}' "$INST")
SET=$(awk '/^# START-SET-BEGIN/{f=1;next} /^# START-SET-END/{f=0} f{print}' "$INST")
SAVE=$(awk '/^# START-SAVE-BEGIN/{f=1;next} /^# START-SAVE-END/{f=0} f{print}' "$DEL")
echo "installer : $INST"
echo "deleter   : $DEL"
printf '%s\n' "$OPTS" | grep -q '^IFS=' && printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-start: CANNOT RUN - no set or IFS line in the installer"; exit 2; }
for b in ASK SET SAVE; do [ -n "${!b}" ] || { echo "test-install-start: CANNOT RUN - no START-$b block (nothing to check)"; exit 2; }; done

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() { if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"; else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi; }
ok() { [ "$1" = yes ] && echo 0 || echo 1; }
STUB=$(cat <<'EOS'
sudo() {
  { printf 'sudo'; printf ' %s' "$@"; echo; } >> "$LOGF"
  case "$1" in
    test|grep|cp|chmod|rm|tee) "$@"; return ;;
    bin/sd) [ "$2" = -internal ] && [ "$3" = set.start.default ] || return 1
            [ -n "${NOWRITE:-}" ] && return 0
            printf '%s\n' "$4" > "$SDSYSDIR/start.default"; return 0 ;;
  esac
  return 0
}
EOS
)
# run BLOCK-TEXT [input]  - the block with /home/sd replaced by $T/home, under the installer's own set and IFS; prints output, then RC=n and CHOICE=
run() {
  local blk="$1" input="${2:-}"
  : > "$T/sudo.log"
  { printf '%s\n' "$OPTS"; echo "RED=''; NC=''"; echo "sdsysdir='$T/sys'; acct_path='$T/home'"; printf '%s\n' "$STUB"
    echo 'read() { [ "${2:-}" = -p ] && echo "PROMPT: $3"; builtin read "$@"; }   # read -p shows no prompt off a terminal'
    printf '%s\n' "${blk//\/home\/sd\//$T/home/}"; echo 'echo "CHOICE=${start_choice:-}"'; } > "$T/run.sh"
  printf '%s\n' "$input" | LOGF="$T/sudo.log" SDSYSDIR="$T/sys" bash "$T/run.sh" 2>&1; echo "RC=$?"
}
fresh() { rm -rf "$T/home" "$T/sys"; mkdir -p "$T/home" "$T/sys"; }

# ---- A: the question --------------------------------------------------------------------------------------------------------
fresh; out=$(run "$ASK" "")
row "A1 fresh, Enter: the home screen" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=menu' && echo yes)")" "$out"
row "A0 a fresh install asks once, offering (H/p): Enter is the home screen" "$(ok "$([ "$(printf '%s\n' "$out" | grep -c '^PROMPT: ')" = 1 ] && printf '%s\n' "$out" | grep -q '^PROMPT: .*(H/p) ' && echo yes)")" "$out"
fresh; out=$(run "$ASK" "p")
row "A2 fresh, p: the prompt" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=terminal' && echo yes)")" "$out"
fresh; out=$(run "$ASK" "prompt")
row "A3 fresh, prompt: the prompt" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=terminal' && echo yes)")" "$out"
# 14 Nov 26 (owner: "it is still asking the home screen or command prompt question, that should just take the existing situation")
fresh; echo terminal > "$T/home/start.default.saved"; out=$(run "$ASK" "h")
row "A4 upgrade that saved terminal: the prompt, not asked (a typed h changes nothing), and it says so" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=terminal' && ! printf '%s' "$out" | grep -q '^PROMPT: ' && printf '%s' "$out" | grep -q 'where they did before: at the command prompt' && echo yes)")" "$out"
# 14 Nov 26 (owner: "an upgrade from 1.1-3 will always be prompt, so the installer should assume that if there is no setting")
fresh; mkdir -p "$T/home/user_accounts"; out=$(run "$ASK" "h")
row "A5 upgrade with the accounts kept and nothing saved (L1.1-3's own deleter): the prompt, not asked (a typed h changes nothing)" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=terminal' && ! printf '%s' "$out" | grep -q '^PROMPT: ' && printf '%s' "$out" | grep -q 'where they did before: at the command prompt' && echo yes)")" "$out"
fresh; echo menu > "$T/home/start.default.saved"; out=$(run "$ASK" "p")
row "A7 upgrade that saved menu: the home screen, not asked (a typed p changes nothing)" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=menu' && ! printf '%s' "$out" | grep -q '^PROMPT: ' && printf '%s' "$out" | grep -q 'where they did before: at the home screen' && echo yes)")" "$out"
fresh; echo 'rm -rf /' > "$T/home/start.default.saved"; out=$(run "$ASK" "h")
row "A6 a saved file with another word: the prompt (only menu means the home screen), not asked" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=terminal' && ! printf '%s' "$out" | grep -q '^PROMPT: ' && echo yes)")" "$out"
# ---- S: applying it ---------------------------------------------------------------------------------------------------------
fresh; echo terminal > "$T/home/start.default.saved"; out=$(run "start_choice=terminal
$SET")
row "S1 terminal: the installer's sd runs set.start.default terminal, and the line says the prompt" "$(ok "$(grep -q -x 'sudo bin/sd -internal set.start.default terminal' "$T/sudo.log" && grep -qx terminal "$T/sys/start.default" && printf '%s' "$out" | grep -q 'start at the command prompt' && echo yes)")" "$out"
row "S4 the saved file is removed" "$(ok "$([ ! -e "$T/home/start.default.saved" ] && echo yes)")" "still there"
fresh; out=$(NOWRITE=1 run "start_choice=terminal
$SET")
row "S2 the verb writes nothing: WARNING with the command, ends 0" "$(ok "$(printf '%s' "$out" | grep -q 'WARNING: the start setting was not written' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
fresh; echo terminal > "$T/home/start.default.saved"; out=$(run "start_choice=menu
$SET")
row "S3 menu: the verb is not run, the line says the home screen, the saved file goes" "$(ok "$(! grep -q set.start.default "$T/sudo.log" && printf '%s' "$out" | grep -q 'start at the home screen' && [ ! -e "$T/home/start.default.saved" ] && echo yes)")" "$out"
# ---- D: the deleter ---------------------------------------------------------------------------------------------------------
home_install() { mkdir -p "$T/sys/gpl.bp"; : > "$T/sys/gpl.bp/tool_home"; }      # an install that has the home screen (2.0-0 on)
old_install()  { mkdir -p "$T/sys/gpl.bp"; : > "$T/sys/gpl.bp/login"; }          # an install from before it (L1.1-3): no tool_home
fresh; home_install; echo terminal > "$T/sys/start.default"; out=$(run "keep_accts=Y
$SAVE")
row "D1 keeping the accounts: start.default saved as start.default.saved, mode 644" "$(ok "$(grep -qx terminal "$T/home/start.default.saved" 2>/dev/null && [ "$(stat -c %a "$T/home/start.default.saved")" = 644 ] && echo yes)")" "$out"
fresh; home_install; echo terminal > "$T/sys/start.default"; out=$(run "keep_accts=DELETE
$SAVE")
row "D2 accounts deleted: nothing saved" "$(ok "$([ ! -e "$T/home/start.default.saved" ] && echo yes)")" "$out"
fresh; home_install; out=$(run "keep_accts=Y
$SAVE")
row "D3 a home-screen install with no start.default (the home screen): saved as menu, mode 644" "$(ok "$(grep -qx menu "$T/home/start.default.saved" 2>/dev/null && [ "$(stat -c %a "$T/home/start.default.saved")" = 644 ] && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
fresh; mkdir -p "$T/sys/gpl.bp.out"; : > "$T/sys/gpl.bp.out/tool_home"; out=$(run "keep_accts=Y
$SAVE")
row "D3b a 2.0 install (no gpl.bp, only the compiled gpl.bp.out/tool_home) with no start.default: saved as menu" "$(ok "$(grep -qx menu "$T/home/start.default.saved" 2>/dev/null && echo yes)")" "$out"
fresh; out=$(run "keep_accts=Y
$SAVE")
row "D6 no gpl.bp and no tool_home at all: saved as terminal" "$(ok "$(grep -qx terminal "$T/home/start.default.saved" 2>/dev/null && echo yes)")" "$out"
fresh; old_install; out=$(run "keep_accts=Y
$SAVE")
row "D4 an install from before the home screen (L1.1-3): saved as terminal, mode 644, so the upgrade keeps the prompt" "$(ok "$(grep -qx terminal "$T/home/start.default.saved" 2>/dev/null && [ "$(stat -c %a "$T/home/start.default.saved")" = 644 ] && printf '%s' "$out" | grep -q 'before the home screen' && echo yes)")" "$out"
fresh; old_install; out=$(run "keep_accts=DELETE
$SAVE")
row "D5 the same with the accounts deleted: nothing saved (a fresh start is the home screen)" "$(ok "$([ ! -e "$T/home/start.default.saved" ] && echo yes)")" "$out"
# the whole upgrade from L1.1-3: the deleter's save, then the installer's question with Enter
fresh; old_install; run "keep_accts=Y
$SAVE" > /dev/null; out=$(run "$ASK" "")
row "U1 an upgrade from L1.1-3, Enter at the question: the prompt is kept" "$(ok "$(printf '%s' "$out" | grep -q 'CHOICE=terminal' && echo yes)")" "$out"
# ---- P: placement -----------------------------------------------------------------------------------------------------------
# 9 Nov 26 (S.187): the reader questions (VIEWER-ASK) are gone; 14 Nov 26 (S.155): so is the sdsys ssh question, and the question follows the gates question
l_v=$(grep -n '^# GATES-ASK-END' "$INST" | cut -d: -f1); l_a=$(grep -n '^# START-ASK-BEGIN' "$INST" | cut -d: -f1); l_s=$(grep -n '^if ! sudo -v' "$INST" | head -1 | cut -d: -f1)
l_m=$(grep -n '^# MANUALS-PDF-END' "$INST" | cut -d: -f1); l_t=$(grep -n '^# START-SET-BEGIN' "$INST" | cut -d: -f1)
row "P the question after GATES-ASK and before the first sudo; START-SET after MANUALS-PDF" "$(ok "$([ -n "$l_v" ] && [ -n "$l_a" ] && [ -n "$l_s" ] && [ -n "$l_m" ] && [ -n "$l_t" ] && [ "$l_v" -lt "$l_a" ] && [ "$l_a" -lt "$l_s" ] && [ "$l_m" -lt "$l_t" ] && echo yes)")" "lines $l_v $l_a $l_s $l_m $l_t"
row "P no block has an exit" "$(ok "$(printf '%s\n%s\n%s\n' "$ASK" "$SET" "$SAVE" | grep -q -E '(^|[^a-z_])exit( |$)' && echo no || echo yes)")" "an exit is in a block"

echo "test-install-start: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
