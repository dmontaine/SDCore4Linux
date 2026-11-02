#!/bin/bash
#
# test-install-opengates.sh - the installer's question about the installing user's access gates, and the function that opens them
# (owner, 19 Oct 2026: "installer asks once; y opens all gates for the installing user's account, default No").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-opengates.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-opengates.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-opengates.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd (bin/sd is a stub), no groupadd.  Everything happens in a scratch
# directory.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing piece, or a stub
# that was never called, is exit 2).
#
# WHAT IT RUNS.  The text between "# GATES-ASK-BEGIN" and "# GATES-ASK-END" and the function open_installer_gates are cut out of the
# installer; every "/home/sd/" in them is rewritten to the scratch directory; each runs under the installer's OWN "set -euo pipefail"
# with sudo and getent replaced by functions that report what the scenario says, `read` wrapped so that every call is logged (bash
# prints a read -p prompt only on a terminal, so the log is the evidence that the question was asked), and bin/sd a stub that does what
# the real modify.account does for each word - and that, like the real sd, EXITS 0 when it refuses.
#
#   A   the question: y, Y, yes, YES, Yes open; Enter, n, N, no, and anything else do not (DEFAULT NO); it is asked exactly once, with
#       the user's name and (y/N); it is NOT asked, and a typed y changes nothing, when the account already exists (an upgrade keeps
#       what it has); open_gates is n whenever it was not asked.
#   O   the opening: modify.account is run once per word, in the list's order, with the ACCOUNT name (lower case) and with its
#       input from /dev/null; the success line is judged on what the register and the Linux groups HOLD afterwards, never on sd's exit
#       status: a word the stub refuses (exit 0), one that crashes (exit 1), a register that cannot be read, groups that cannot be
#       read, and a half-done "both" each print a WARNING naming exactly the word to give, and the success line is ABSENT.  The
#       group tests use the Linux user's own spelling (Don), the commands the account's (don).
#   S   static: the word list is exactly what modify.account accepts to turn something on (so a gate added later fails here until it is
#       decided), files-on comes before files-write-on, the register lines the function reads are the ACC$ numbers of keys.h, the
#       function is called from the plain-account branch only when open_gates is y, and the old closed-account text is still the
#       else branch.
#
# ANCHORED ON THE SUCCESS WORDING.  "Opened every access gate for" is printed only when everything is open.  Every failing scenario is
# judged on that line being ABSENT and on "NOT open for" being present; the good scenario on the line being present and no WARNING.
#
#   Z   (1 Nov 2026) the last gate, sdsys-on: open_installer_sdsys runs modify.account <account> sdsys-on with its input from /dev/null and is
#       judged on the group sdu_<account> listing sdsys; it is called only when open_gates is y, and AFTER the call of sdsys_groups_default (S.103, 1 Nov: the
#       default puts the sdsys user in every account's group, so this gate is a repair; until then the F6 ruling would have taken it out again on a fresh install).
#
# 1 NOV 2026: BACK, AND EVERY GATE.  The test was deleted on 26 Oct with the question ("no question, keep it closed") and restored from 945e7662^ on
# 1 Nov, when the owner asked for the question back and chose "Every gate" (confirmed after the warning about ai-on, files-admin-on and sdsys-on).
# The list is now every on-word of modify.account but shared-read-on (on already) and sdsys-on (section Z); S2b and S2c say so.
#
# NOT MEASURED HERE, and said so: that the real modify.account, run by `sudo bin/sd -internal` while the install's own cproc is in
# place, accepts each word (it is the verb that sandbox-gates.py, sandbox-editgates and sandbox-net.py drive for the register words, and
# that a real install witnesses for the groups); that sd-elevate adds the Linux groups; that the question reads from a terminal.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"
MODIFYA="$HERE/../sdsys/gpl.bp/modifya"
KEYS="$HERE/../sdsys/syscom/keys.h"

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
  mutant ask-default-yes           '/^# GATES-ASK-BEGIN/,/^# GATES-ASK-END/ s/^open_gates=n$/open_gates=y/'
  mutant ask-even-when-account-kept '/^# GATES-ASK-BEGIN/,/^# GATES-ASK-END/ s/^if \[ ! -d "\/home\/sd\/user_accounts\/\${tuser_lc}" \]; then$/if true; then/'
  mutant ask-accepts-anything      '/^# GATES-ASK-BEGIN/,/^# GATES-ASK-END/ s/\[yY\]|\[yY\]\[eE\]\[sS\] )/* )/'
  mutant ask-only-lower-y          '/^# GATES-ASK-BEGIN/,/^# GATES-ASK-END/ s/\[yY\]|\[yY\]\[eE\]\[sS\] )/y )/'
  mutant ask-never-reads           '/^# GATES-ASK-BEGIN/,/^# GATES-ASK-END/ s/^    read -r -p .*$/    yn_gates=n/'
  mutant words-lose-net            '/^open_installer_gates() {/,/^}/ s/ net-on / /'
  mutant words-lose-shared-write   '/^open_installer_gates() {/,/^}/ s/ shared-write-on / /'
  mutant words-swap-files          '/^open_installer_gates() {/,/^}/ s/ files-on files-write-on / files-write-on files-on /'
  mutant words-add-unknown         '/^open_installer_gates() {/,/^}/ s/ pins-on"/ pins-on suspended"/'
  mutant words-lose-ai             '/^open_installer_gates() {/,/^}/ s/ ai-on / /'
  mutant words-lose-files-admin    '/^open_installer_gates() {/,/^}/ s/ files-admin-on / /'
  mutant words-hold-sdsys          '/^open_installer_gates() {/,/^}/ s/ pins-on"/ pins-on sdsys-on"/'
  mutant ai-group-forgotten        '/^open_installer_gates() {/,/^}/{/gate_grp sdaiusers ai-on/d}'
  mutant recovery-line-forgotten   '/^open_installer_gates() {/,/^}/{/gate_reg 19 recovery-on/d}'
  mutant sdsys-never-given         's/^    open_installer_sdsys "\$tuser" "\$tuser_lc"$/    true/'
  mutant sdsys-given-always        's/^if \[ "\${open_gates:-n}" = y \] && \[ -d "\/home\/sd\/user_accounts\/\${tuser_lc}" \]; then$/if [ -d "\/home\/sd\/user_accounts\/${tuser_lc}" ]; then/'
  mutant sdsys-unjudged            '/^open_installer_sdsys() {/,/^}/ s/\*",sdsys,"\*) echo/*) echo/'
  mutant sdsys-stdin-kept          '/^open_installer_sdsys() {/,/^}/ s/ sdsys-on < \/dev\/null || true$/ sdsys-on || true/'
  mutant stdin-kept                '/^open_installer_gates() {/,/^}/ s/ < \/dev\/null || true$/ || true/'
  mutant refusal-aborts-install    '/^open_installer_gates() {/,/^}/ s/ < \/dev\/null || true$/ < \/dev\/null/'
  mutant account-name-is-linux-name '/^open_installer_gates() {/,/^}/ s/modify.account "\$acct" "\$gate_word"/modify.account "\$user" "\$gate_word"/'
  mutant success-unguarded         '/^open_installer_gates() {/,/^}/ s/^    if \[ -z "\$gate_missing" \]; then$/    if true; then/'
  mutant register-never-judged     '/^open_installer_gates() {/,/^}/ s/ = yes \] || gate_missing="\${gate_missing} \$2"/ = yes ] || true/'
  mutant groups-never-judged       '/^open_installer_gates() {/,/^}/ s/^            \*",\${user},"\*) ;;$/            *) ;;/'
  mutant groups-judged-on-account-name '/^open_installer_gates() {/,/^}/ s/\*",\${user},"\*)/*",${acct},"*)/'
  mutant groups-failing-aborts     '/^open_installer_gates() {/,/^}/ s/ | cut -d: -f4) || gate_members=""$/ | cut -d: -f4)/'
  mutant ifs-left-strict           '/^open_installer_gates() {/,/^}/{/^    local IFS=/d}'
  mutant wrong-register-line      '/^open_installer_gates() {/,/^}/ s/gate_reg 10 voc-on/gate_reg 9 voc-on/'
  mutant files-write-group-forgotten '/^open_installer_gates() {/,/^}/{/gate_grp sdfileswrite files-write-on/d}'
  mutant function-never-called     's/^        open_installer_gates "\$tuser" "\$tuser_lc" "\$acct_reg"$/        true/'
  mutant function-called-always    's/^      if \[ "\$open_gates" = y \]; then$/      if true; then/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

# THE INSTALLER'S OWN set AND IFS.  Its IFS is $'\n\t' (installsdcore.sh:91, "predictable word splitting"): a space does NOT split a word, so an
# unquoted list in a for loop is ONE word.  This test first ran the function under the set line alone and was green; the first real install
# (19 Oct 2026, the VM) handed SD one argument "both sh-on os-on ..." and SD refused it ("does one action at a time").  Both lines now.
OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
FUNC=$(awk '/^open_installer_gates\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
ASK=$(awk '/^# GATES-ASK-BEGIN/{f=1;next} /^# GATES-ASK-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-opengates: CANNOT RUN - no set line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-opengates: CANNOT RUN - no IFS line in the installer (the function must be run under it)"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-opengates: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$FUNC" ] && { echo "test-install-opengates: CANNOT RUN - no function open_installer_gates in the installer (nothing to check)"; exit 2; }
[ -z "$ASK" ]  && { echo "test-install-opengates: CANNOT RUN - no block between GATES-ASK-BEGIN and GATES-ASK-END (nothing to check)"; exit 2; }
[ -r "$MODIFYA" ] || { echo "test-install-opengates: CANNOT RUN - $MODIFYA is not readable"; exit 2; }
[ -r "$KEYS" ]    || { echo "test-install-opengates: CANNOT RUN - $KEYS is not readable"; exit 2; }
echo "function  : $(printf '%s\n' "$FUNC" | wc -l) lines;  question block: $(printf '%s\n' "$ASK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
ASK_T=$(printf '%s\n' "$ASK" | sed -e "s#/home/sd/#$T/home/sd/#g")
printf '%s\n' "$ASK_T" | grep -q -F "$T/home/sd/user_accounts" || { echo "test-install-opengates: CANNOT RUN - the question block does not look at /home/sd/user_accounts"; exit 2; }

WORDS="both sh-on os-on sd-on voc-on bp-on dict-on recovery-on net-on shared-write-on files-on files-write-on files-admin-on ai-on pins-on"
NW=15
ALLMISS="sh-on os-on sd-on voc-on bp-on dict-on shared-write-on net-on pins-on recovery-on both files-on files-write-on files-admin-on ai-on"
GRPMISS="both files-on files-write-on files-admin-on ai-on"
SDSYSF=$(awk '/^open_installer_sdsys\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
[ -z "$SDSYSF" ] && { echo "test-install-opengates: CANNOT RUN - no function open_installer_sdsys in the installer"; exit 2; }

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# ---- A. the question ------------------------------------------------------------------------------------------------------
run_ask() {   # run_ask ANSWER [exists]   - prints the output, then OPEN_GATES=y|n
  rm -rf "$T/home"; mkdir -p "$T/home/sd/user_accounts"
  [ "${2:-}" = exists ] && mkdir -p "$T/home/sd/user_accounts/don"
  : > "$T/read.log"
  OPTS="$OPTS" ASK_T="$ASK_T" T="$T" bash -c '
      eval "$OPTS"
      YELLOW=; NC=
      tuser=Don
      read() { ( IFS=" "; printf "%s\n" "$*" ) >> "$T/read.log"; builtin read "$@"; }
      eval "$ASK_T"
      echo "OPEN_GATES=$open_gates"' <<< "$1" 2>&1
}

echo "--- A: the question"
for ans in y Y yes YES Yes; do
  OUT=$(run_ask "$ans")
  row "A1 the answer '$ans' opens (open_gates=y)" "$(ok "$(printf '%s' "$OUT" | grep -q '^OPEN_GATES=y$' && echo yes)")" "$OUT"
done
for ans in "" n N no NO x yy ye nope 1; do
  OUT=$(run_ask "$ans")
  row "A2 the answer '$ans' does NOT open (default No)" "$(ok "$(printf '%s' "$OUT" | grep -q '^OPEN_GATES=n$' && echo yes)")" "$OUT"
done
OUT=$(run_ask y)
nread=$(wc -l < "$T/read.log")
row "A3 it was asked: read ran once (the null case: a block that never asks passes every A2 row)" "$(ok "$([ "$nread" -eq 1 ] && echo yes)")" "read calls: $nread"
row "A3b ...with the prompt naming the user and (y/N)" \
    "$(ok "$(grep -q -F "Don" "$T/read.log" && grep -q -F "(y/N)" "$T/read.log" && grep -q -- '-r' "$T/read.log" && echo yes)")" "read.log: $(cat "$T/read.log")"
row "A3c ...after saying what the gates are and that they start closed" "$(ok "$(printf '%s' "$OUT" | grep -q -i 'closed' && echo yes)")" "$OUT"
OUT=$(run_ask y exists)
nread=$(wc -l < "$T/read.log")
row "A4 the account already exists (an upgrade): not asked, a typed y changes nothing" \
    "$(ok "$([ "$nread" -eq 0 ] && printf '%s' "$OUT" | grep -q '^OPEN_GATES=n$' && echo yes)")" "read calls: $nread; $OUT"

# ---- O. the opening ------------------------------------------------------------------------------------------------------
cat > "$T/sd-stub" <<'STUB'
#!/bin/bash
# bin/sd as the installer calls it: -internal modify.account <account> <word>.  Exits 0 when it refuses, like the real sd.
echo "ARGS: $*" >> "$SDLOG"
if [ -t 0 ]; then echo "STDIN: tty" >> "$SDLOG"; else echo "STDIN: $(readlink /proc/$$/fd/0)" >> "$SDLOG"; fi
word="$4"
[ -n "${CRASH:-}" ] && [ "$word" = "$CRASH" ] && exit 1
[ -n "${REFUSE:-}" ] && [ "$word" = "$REFUSE" ] && exit 0
[ -n "${NOEFFECT:-}" ] && exit 0
setline() { sed -i "$1s/.*/yes/" "$REG"; }
add() { printf '%s,%s' "$(cat "$T/groups/$1")" "Don" > "$T/groups/$1"; }
case "$word" in
  sh-on) setline 7;; os-on) setline 8;; sd-on) setline 9;; voc-on) setline 10;; bp-on) setline 11;; dict-on) setline 12;;
  shared-write-on) setline 14;; net-on) setline 15;; pins-on) setline 18;; recovery-on) setline 19;;
  both) add sdssh; [ -n "${HALFBOTH:-}" ] || add sdapi;;
  files-on) add sdfiles;; files-write-on) add sdfileswrite;; files-admin-on) add sdfilesadmin;; ai-on) add sdaiusers;;
  sdsys-on) printf '%s,%s' "$(cat "$T/groups/sdu_don")" "sdsys" > "$T/groups/sdu_don";;
esac
exit 0
STUB
chmod +x "$T/sd-stub"

run_open() {   # env knobs: REFUSE CRASH NOEFFECT HALFBOTH NOREG GRPBLIND ; prints the output, then RC=n
  rm -rf "$T/work" "$T/reg" "$T/groups"; mkdir -p "$T/work/bin" "$T/reg" "$T/groups"
  cp "$T/sd-stub" "$T/work/bin/sd"
  : > "$T/sd.log"; : > "$T/sudo.log"
  local g; for g in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers sdu_don; do printf 'root' > "$T/groups/$g"; done
  if [ -z "${NOREG:-}" ]; then
    printf '%s\n' "$T/home/sd/user_accounts/don" "" "sdu_don" "" "" "" no no "" no no no yes no no "" "" no no > "$T/reg/don"
  fi
  ( cd "$T/work" && OPTS="$OPTS" FUNC="$FUNC" T="$T" SDLOG="$T/sd.log" REG="$T/reg/don" bash -c '
      eval "$OPTS"; RED=; NC=
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$T/sudo.log"; "$@"; }
      getent() { [ -z "${GRPFAIL:-}" ] || return 2; if [ "$1" = group ] && [ -z "${GRPBLIND:-}" ]; then printf "%s:x:900:%s\n" "$2" "$(cat "$T/groups/$2" 2>/dev/null)"; fi; }
      eval "$FUNC"
      # called as a plain statement, as the installer calls it: under set -e a command the function lets fail ends the shell here,
      # and RC=0 is then never printed (an "|| rc=$?" would switch set -e off inside the function and hide exactly that)
      open_installer_gates Don don "$REG"
      echo "RC=0"' <<< "input the function must not read" 2>&1 )
}
run_sdsys() {   # env knobs: NOEFFECT GRPBLIND ; runs open_installer_sdsys as the installer does; prints the output, then RC=n
  rm -rf "$T/work" "$T/groups"; mkdir -p "$T/work/bin" "$T/groups"
  cp "$T/sd-stub" "$T/work/bin/sd"
  : > "$T/sd.log"; : > "$T/sudo.log"
  printf 'root' > "$T/groups/sdu_don"
  ( cd "$T/work" && OPTS="$OPTS" SDSYSF="$SDSYSF" T="$T" SDLOG="$T/sd.log" REG="$T/reg/don" bash -c '
      eval "$OPTS"; RED=; NC=
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$T/sudo.log"; "$@"; }
      getent() { if [ "$1" = group ] && [ -z "${GRPBLIND:-}" ]; then printf "%s:x:900:%s\n" "$2" "$(cat "$T/groups/$2" 2>/dev/null)"; fi; }
      eval "$SDSYSF"
      open_installer_sdsys Don don
      echo "RC=0"' <<< "input the function must not read" 2>&1 )
}
ncalls() { grep -c '^ARGS: ' "$T/sd.log"; }
called_words() { sed -n 's/^ARGS: -internal modify.account don //p' "$T/sd.log" | tr '\n' ' ' | sed 's/ $//'; }

echo "--- O: the opening"
OUT=$(run_open)
row "O1 everything holds: RC=0 and the success line" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'Opened every access gate for Don' && echo yes)")" "$OUT"
row "O1b ...no WARNING" "$(ok "$(! printf '%s' "$OUT" | grep -q -E 'WARNING|NOT open' && echo yes)")" "$OUT"
row "O1c ...bin/sd was RUN, once per word (the null case: a stub never called passes nothing)" \
    "$(ok "$([ "$(ncalls)" -eq $NW ] && echo yes)")" "calls: $(ncalls); sd.log: $(tr '\n' ';' < "$T/sd.log")"
row "O1d ...in the list's order, each as -internal modify.account <account in lower case> <word>" \
    "$(ok "$([ "$(called_words)" = "$WORDS" ] && echo yes)")" "got: $(called_words)"
row "O1e ...each with its input from /dev/null (a verb that asked a question would hang the install on a terminal)" \
    "$(ok "$([ "$(grep -c '^STDIN: /dev/null$' "$T/sd.log")" -eq $NW ] && echo yes)")" "stdin lines: $(grep '^STDIN' "$T/sd.log" | sort | uniq -c | tr '\n' ';')"
row "O1f ...and the register and the groups were READ to judge it (sed on lines 7-19, getent on the six groups)" \
    "$(ok "$(for n in 7 8 9 10 11 12 14 15 18 19; do grep -q "sed -n ${n}p " "$T/sudo.log" || exit 1; done; echo yes)")" "sudo.log: $(tr '\n' ';' < "$T/sudo.log")"

for w in $WORDS; do
  OUT=$(REFUSE="$w" run_open)
  row "O2 '$w' refused by sd (exit 0): the rest still run ($NW calls), WARNING names $w, no success line" \
      "$(ok "$([ "$(ncalls)" -eq $NW ] && printf '%s' "$OUT" | grep -q "NOT open for Don: $w\$" && ! printf '%s' "$OUT" | grep -q 'Opened every access gate' && echo yes)")" "calls $(ncalls): $OUT"
done
OUT=$(CRASH=sh-on run_open)
row "O3 sd CRASHES on sh-on (exit 1): the install goes on ($NW calls, RC=0), WARNING names sh-on, no success line" \
    "$(ok "$([ "$(ncalls)" -eq $NW ] && printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q "NOT open for Don: sh-on\$" && ! printf '%s' "$OUT" | grep -q 'Opened every access gate' && echo yes)")" "$OUT"
OUT=$(NOREG=1 NOEFFECT=1 run_open)
row "O4 no register record and nothing applied: all ten register words and the groups are named, no success line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q "NOT open for Don: ${ALLMISS}\$" && ! printf '%s' "$OUT" | grep -q 'Opened every access gate' && echo yes)")" "$OUT"
OUT=$(GRPBLIND=1 run_open)
row "O5 the groups cannot be read (the register is right): both and the four group words are named, no success line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q "NOT open for Don: ${GRPMISS}\$" && ! printf '%s' "$OUT" | grep -q 'Opened every access gate' && echo yes)")" "$OUT"
OUT=$(GRPFAIL=1 run_open)
row "O5b getent FAILS (exit 2, as for a group that does not exist): the install is not aborted (RC=0), the same are named" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q "NOT open for Don: ${GRPMISS}\$" && echo yes)")" "$OUT"
OUT=$(HALFBOTH=1 run_open)
row "O6 'both' puts the user in sdssh but not sdapi: 'both' is named once, nothing else is" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'NOT open for Don: both$' && ! printf '%s' "$OUT" | grep -q 'Opened every access gate' && echo yes)")" "$OUT"
OUT=$(NOEFFECT=1 run_open)
row "O7 sd applies nothing at all: every word is named (the registers start closed), no success line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q "NOT open for Don: ${ALLMISS}\$" && echo yes)")" "$OUT"

# ---- Z. the last gate, sdsys-on (1 Nov 2026) -----------------------------------------------------------------------------
echo "--- Z: sdsys-on, after the ruling"
OUT=$(run_sdsys)
row "Z1 sdsys-on given once, as -internal modify.account don sdsys-on, input /dev/null; the group holds sdsys and the success line says so; RC=0" \
    "$(ok "$([ "$(ncalls)" -eq 1 ] && grep -q '^ARGS: -internal modify.account don sdsys-on$' "$T/sd.log" && grep -q '^STDIN: /dev/null$' "$T/sd.log" && printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'The sdsys user is in the group of Don' && ! printf '%s' "$OUT" | grep -q WARNING && echo yes)")" "$OUT / $(tr '\n' ';' < "$T/sd.log")"
OUT=$(NOEFFECT=1 run_sdsys)
row "Z2 sd does nothing (exit 0): the WARNING names sdsys-on and sdu_don, no success line, RC=0" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'NOT in the group sdu_don' && ! printf '%s' "$OUT" | grep -q 'The sdsys user is in the group' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
OUT=$(GRPBLIND=1 run_sdsys)
row "Z3 the group cannot be read: the WARNING, not the success line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'NOT in the group sdu_don' && ! printf '%s' "$OUT" | grep -q 'The sdsys user is in the group' && echo yes)")" "$OUT"
RULE=$(grep -n '^sdsys_groups_default "\$ACCT_PATH/\\\$sdsys.access"$' "$INST" | head -1 | cut -d: -f1)
ZGUARD=$(grep -n '^if \[ "\${open_gates:-n}" = y \] && \[ -d "/home/sd/user_accounts/\${tuser_lc}" \]; then$' "$INST" | head -1 | cut -d: -f1)
ZCALL=$(grep -n '^    open_installer_sdsys "\$tuser" "\$tuser_lc"$' "$INST" | head -1 | cut -d: -f1)
row "Z4 the call is AFTER sdsys_groups_default (S.103: the sdsys user is in every account's group as delivered, so this is a repair that reads the group back), inside 'if open_gates = y' and the account exists" \
    "$(ok "$([ -n "$RULE" ] && [ -n "$ZGUARD" ] && [ -n "$ZCALL" ] && [ "$RULE" -lt "$ZGUARD" ] && [ "$ZGUARD" -lt "$ZCALL" ] && [ $((ZCALL - ZGUARD)) -eq 1 ] && echo yes)")" "ruling=$RULE guard=$ZGUARD call=$ZCALL"

# ---- S. static -------------------------------------------------------------------------------------------------------------
echo "--- S: static"
inst_words=$(printf '%s\n' "$FUNC" | sed -n 's/^ *gate_words="\(.*\)"$/\1/p')
row "S1 the function has ONE gate_words list" "$(ok "$([ -n "$inst_words" ] && [ "$(printf '%s\n' "$FUNC" | grep -c 'gate_words=')" -eq 1 ] && echo yes)")" "list: $inst_words"
row "S1b ...and it is the list this test expects" "$(ok "$([ "$inst_words" = "$WORDS" ] && echo yes)")" "got: $inst_words"
all_on_words=$(grep -o "case action = '[A-Z.-]*'" "$MODIFYA" | sed "s/case action = '\(.*\)'/\1/" | grep -E '^(BOTH|[A-Z.-]+-ON)$' \
            | grep -v '^SHARED-READ-ON$' | tr 'A-Z' 'a-z' | sort | tr '\n' ' ' | sed 's/ $//')
# 21 Oct 26, S.73 item 3 (owner, 20 Oct 2026, D4): files-admin-on is LEFT OUT of the "open every gate" answer on purpose - the right to administer files
# on this server is turned on by hand (core direction 1, a looser default declined); S2b holds it out and S2 holds the rest to the function's list.
# 26 Oct 26, F6 (alternative C): sdsys-on is left out too, and for the same reason - the sdsys user's write access to an account is given by hand (S2c holds it out).
# 26 Oct 26: ai-on (S.69 step 2, 23 Oct: the AI gate is OFF by default and wants the helper and a provider key first) and pins-on (22 Oct: not a gate, the permission
# to add one's own programs to the home screen) were never in the installer's list; this row was red from 23 Oct until they were named here as left out on purpose.
# 1 Nov 26 (owner: "Every gate", confirmed after the warning): the rows above that left files-admin-on, sdsys-on, ai-on and pins-on out are history; the
# list now holds every on-word but shared-read-on (on already) and sdsys-on, which open_installer_sdsys gives after the ruling (section Z).
mod_words=$(printf '%s\n' $all_on_words | grep -v -E '^(sdsys-on)$' | tr '\n' ' ' | sed 's/ $//')
mine=$(printf '%s\n' $inst_words | sort | tr '\n' ' ' | sed 's/ $//')
row "S2 the list is every word modify.account accepts to turn something on (shared-read-on is on by default; sdsys-on is section Z): a gate added later fails here" \
    "$(ok "$([ -n "$mod_words" ] && [ "$mod_words" = "$mine" ] && echo yes)")" "modifya: $mod_words / installer: $mine"
row "S2b the list holds ai-on, files-admin-on, pins-on and recovery-on (owner, 1 Nov 2026: every gate)" \
    "$(ok "$(case " $mine " in *" ai-on "*) case " $mine " in *" files-admin-on "*) case " $mine " in *" pins-on "*) case " $mine " in *" recovery-on "*) echo yes;; esac;; esac;; esac;; esac)")" "installer: $mine"
row "S2c sdsys-on is a word modify.account accepts and is NOT in the list (open_installer_sdsys gives it, after the ruling)" \
    "$(ok "$(case " $all_on_words " in *" sdsys-on "*) case " $mine " in *" sdsys-on "*) ;; *) echo yes;; esac;; esac)")" "modifya on-words: $all_on_words / installer: $mine"
row "S3 files-on comes before files-write-on" \
    "$(ok "$(case " $inst_words " in *" files-on files-write-on "*) echo yes;; esac)")" "list: $inst_words"
declare -A ACCOF=( [sh-on]='ACC$SH' [os-on]='ACC$OS.EXEC' [sd-on]='ACC$SD.ACCOUNTS' [voc-on]='ACC$VOC.EDIT' [bp-on]='ACC$BP.EDIT' [dict-on]='ACC$DICT.EDIT' [shared-write-on]='ACC$SHARED.WRITE' [net-on]='ACC$NET' [pins-on]='ACC$PINS' [recovery-on]='ACC$RECOVERY' )
n_reg=0
for w in "${!ACCOF[@]}"; do
  want=$(sed -n "s/^ *\$define ${ACCOF[$w]//\$/\\$} *\([0-9][0-9]*\).*/\1/p" "$KEYS" | head -1)
  have=$(printf '%s\n' "$FUNC" | sed -n "s/^ *gate_reg \([0-9][0-9]*\) $w\$/\1/p")
  n_reg=$((n_reg+1))
  row "S4 register line for $w is ${ACCOF[$w]} = ${want:-?} in keys.h" "$(ok "$([ -n "$want" ] && [ "$want" = "$have" ] && echo yes)")" "keys.h: '$want', installer: '$have'"
done
row "S4b ...all ten were checked (the null case)" "$(ok "$([ "$n_reg" -eq 10 ] && echo yes)")" "$n_reg"
for pair in "sdssh both" "sdapi both" "sdfiles files-on" "sdfileswrite files-write-on" "sdfilesadmin files-admin-on" "sdaiusers ai-on"; do
  set -- $pair
  row "S5 group $1 is judged and names $2" "$(ok "$(printf '%s\n' "$FUNC" | grep -q "^ *gate_grp $1 $2\$" && echo yes)")" "no 'gate_grp $1 $2' line"
done
CALLSITE=$(grep -n '^        open_installer_gates "\$tuser" "\$tuser_lc" "\$acct_reg"$' "$INST" | head -1 | cut -d: -f1)
CREATE=$(grep -n 'sudo bin/sd -internal create.account USER "\$tuser" ATTACH' "$INST" | head -1 | cut -d: -f1)     # create.account since 30 Oct 26 (S.87 batch 6 removed the hyphen form)
SEEDED=$(grep -n 'if \[ "\$seeded_group" = "sdu_\${tuser_lc}" \]; then' "$INST" | head -1 | cut -d: -f1)
GUARD=$(grep -n '^      if \[ "\$open_gates" = y \]; then$' "$INST" | head -1 | cut -d: -f1)
ELSEL=$(grep -n '^      else$' "$INST" | awk -F: -v g="${GUARD:-0}" '$1>g{print $1; exit}')
row "S6 the call exists, after the create-account line and the registered-group test, inside 'if open_gates = y'" \
    "$(ok "$([ -n "$CALLSITE" ] && [ -n "$CREATE" ] && [ -n "$SEEDED" ] && [ -n "$GUARD" ] && [ "$CREATE" -lt "$SEEDED" ] && [ "$SEEDED" -lt "$GUARD" ] && [ "$GUARD" -lt "$CALLSITE" ] && echo yes)")" \
    "create=$CREATE seeded=$SEEDED guard=$GUARD call=$CALLSITE"
row "S6b ...and the closed-account text (the three modify.account lines the editgates check reads) is the else branch" \
    "$(ok "$([ -n "$ELSEL" ] && [ -n "$CALLSITE" ] && [ "$CALLSITE" -lt "$ELSEL" ] && sed -n "${ELSEL},\$p" "$INST" | head -14 | grep -q 'starts with no ssh, no API, no shell and no OS.EXECUTE' && echo yes)")" "else at $ELSEL"
row "S7 the question block is above the first sudo (asked up front, like the ssh and API questions)" \
    "$(ok "$([ "$(grep -n '^# GATES-ASK-BEGIN' "$INST" | head -1 | cut -d: -f1)" -lt "$(grep -n '^if ! sudo -v; then' "$INST" | head -1 | cut -d: -f1)" ] && echo yes)")" "ask / sudo -v"
row "S8 the function is defined before the installer's main flow can call it" \
    "$(ok "$([ "$(grep -n '^open_installer_gates() {' "$INST" | head -1 | cut -d: -f1)" -lt "$(grep -n '^# GATES-ASK-BEGIN' "$INST" | head -1 | cut -d: -f1)" ] && echo yes)")" "function / ask"

echo "test-install-opengates: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
