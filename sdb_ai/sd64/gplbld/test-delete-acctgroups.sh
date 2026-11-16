#!/bin/bash
#
# test-delete-acctgroups.sh - deletesdcore.sh removes, on a full DELETE, the Linux group of every account the register names (S.249; the owner, in
# the Windows chat 15 Nov 2026: "uninstall should probably remove everything if asked to remove accounts"; Windows row 322).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-acctgroups.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-acctgroups.sh --selftest
#   DELETER=<a copy of deletesdcore.sh> bash .../test-delete-acctgroups.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (a function here), no install, no SD.  The two blocks ACCTGROUPS-READ and ACCTGROUPS-DEL are cut out of the script and run
# under the script's OWN "set" and "IFS" lines: READ on a scratch register ("${sdsysdir}/accounts" rewritten), DEL with getent and groupdel stubs
# that log what they were asked.
#
#   R  READ on DELETE: exactly the sdu_/sdg_ names in field 3, sorted, each once; a field 3 that is another name (root), has a space, or a record
#      with no third line names nothing; a subdirectory is not read; KEEP reads nothing; no register reads nothing (the null case: exit 0)
#   D  DEL: every group named that exists is removed and the script says so; one that does not exist is not asked; a refused groupdel is said
#      and the script goes on; an empty list asks nothing
#   S  static: READ comes after "sd -stop" and before the system directory is removed; DEL is inside the DELETE branch; markers once each
#
# ANCHORED ON THE WORDING: "Removed group X." only after groupdel succeeded, "was not removed" only after it failed.
# NOT MEASURED HERE: a real DELETE cycle with real groups (the VM: sudo, groupdel, a user whose primary group it is).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
DEL="${DELETER:-$(cd "$HERE/../../.." && pwd)/deletesdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/deletesdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, sed expression
    local name="$1" expr="$2" f="$T/$1.sh" rc
    total=$((total+1))
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    DELETER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real script first (must pass), then mutants (each must not)"
  DELETER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real script does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real script passes"
  mutant read-on-keep          '/^# ACCTGROUPS-READ-BEGIN/,/^# ACCTGROUPS-READ-END/ s/if \[ "\$keep_accts" = "DELETE" \] \&\& /if /'
  mutant any-field             '/^# ACCTGROUPS-READ-BEGIN/,/^# ACCTGROUPS-READ-END/ s/FNR == 3 \&\& //'
  mutant any-name              '/^# ACCTGROUPS-READ-BEGIN/,/^# ACCTGROUPS-READ-END/ s/\/^sd\[ug\]_\[a-z0-9._-\]+\$\/ //'
  mutant never-deleted         '/ACCTGROUPS-DEL-BEGIN/,/ACCTGROUPS-DEL-END/ s/if sudo groupdel "\$g"; then/if true; then/'
  mutant no-exist-test         '/ACCTGROUPS-DEL-BEGIN/,/ACCTGROUPS-DEL-END/ s/if getent group "\$g" \&>\/dev\/null; then/if true; then/'
  mutant refusal-claims-done   '/ACCTGROUPS-DEL-BEGIN/,/ACCTGROUPS-DEL-END/ s/echo "Group \$g was not removed (groupdel refused it)."/echo "Removed group $g."/'
  mutant read-after-removal    's/^# ACCTGROUPS-READ-BEGIN$/# ACCTGROUPS-READ-BEGIN-X/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$DEL" | head -2)
RB=$(awk '/^# ACCTGROUPS-READ-BEGIN$/{f=1;next} /^# ACCTGROUPS-READ-END$/{f=0} f{print}' "$DEL")
DB=$(awk '/^ *# ACCTGROUPS-DEL-BEGIN$/{f=1;next} /^ *# ACCTGROUPS-DEL-END$/{f=0} f{print}' "$DEL")
echo "script    : $DEL"
echo "options   : $(printf '%s' "$OPTS" | tr '\n' ' ')"
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-delete-acctgroups: CANNOT RUN - no set line in the script"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-delete-acctgroups: CANNOT RUN - no IFS line in the script"; exit 2; }
[ -z "$RB" ] && { echo "test-delete-acctgroups: CANNOT RUN - no ACCTGROUPS-READ block"; exit 2; }
[ -z "$DB" ] && { echo "test-delete-acctgroups: CANNOT RUN - no ACCTGROUPS-DEL block"; exit 2; }
echo "blocks    : read $(printf '%s\n' "$RB" | wc -l) lines, del $(printf '%s\n' "$DB" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() { if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"; else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi; }
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

mkreg() {
  rm -rf "$T/sys"; mkdir -p "$T/sys/accounts/sub"
  printf '/home/sd/user_accounts/ann\n\nsdu_ann\n' > "$T/sys/accounts/ann"
  printf '/home/sd/group_accounts/team\n\nsdg_team\n' > "$T/sys/accounts/team"
  printf '/home/sd/user_accounts/bob\n\nsdu_ann\n' > "$T/sys/accounts/bob"            # the same group twice: named once
  printf '/x\n\nroot\n' > "$T/sys/accounts/evil"                                       # not an SD name
  printf '/x\n\nsdu_a b\n' > "$T/sys/accounts/spaced"                                  # a space: not an account name
  printf '/x\nsdu_wrongfield\n' > "$T/sys/accounts/short"                              # no third line; the name is in field 2
  printf '/x\n\nsdu_insub\n' > "$T/sys/accounts/sub/rec"                               # below the register: not read
}

run_read() {   # KEEP_ACCTS [noreg]
  [ "${2:-}" = noreg ] && rm -rf "$T/sys"
  OPTS="$OPTS" RB="$RB" KA="$1" SYS="$T/sys" bash -c '
      eval "$OPTS"
      keep_accts="$KA"; sdsysdir="$SYS"
      sudo() { "$@"; }
      eval "$RB"
      printf "G=%s\n" "$(printf "%s" "$sd_acct_groups" | tr "\n" ",")"
      echo "RC=0"' 2>&1
}

echo "--- R: reading the register"
mkreg
OUT=$(run_read DELETE)
row "R1 DELETE: exactly sdg_team and sdu_ann, sorted, each once (not root, not a name with a space, not field 2, not a record in a subdirectory)" \
    "$(ok "$(printf '%s' "$OUT" | grep -qx 'G=sdg_team,sdu_ann' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
OUT=$(run_read KEEP)
row "R2 KEEP: nothing is read" "$(ok "$(printf '%s' "$OUT" | grep -qx 'G=' && echo yes)")" "$OUT"
OUT=$(run_read DELETE noreg)
row "R3 no register at all: nothing, exit 0 (the null case)" "$(ok "$(printf '%s' "$OUT" | grep -qx 'G=' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"

run_del() {   # GROUPS EXISTING REFUSE
  OPTS="$OPTS" DB="$DB" GL="$1" EX="$2" RF="$3" LOG="$T/del.log" bash -c '
      eval "$OPTS"
      sd_acct_groups="$GL"
      : > "$LOG"
      sudo() { "$@"; }
      getent() { printf "%s\n" "$EX" | grep -qx "$2"; }
      groupdel() { echo "groupdel $1" >> "$LOG"; [ "$1" != "$RF" ]; }
      eval "$DB"
      echo "RC=0"' 2>&1
}

echo "--- D: removing the groups"
OUT=$(run_del $'sdg_team\nsdu_ann\nsdu_gone' $'sdg_team\nsdu_ann' '')
LOG=$(cat "$T/del.log")
row "D1 the two groups that exist are removed and said; sdu_gone, which does not exist, is not asked" \
    "$(ok "$([ "$LOG" = $'groupdel sdg_team\ngroupdel sdu_ann' ] && printf '%s' "$OUT" | grep -qx 'Removed group sdg_team.' && printf '%s' "$OUT" | grep -qx 'Removed group sdu_ann.' && ! printf '%s' "$OUT" | grep -q 'sdu_gone' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT / $LOG"
OUT=$(run_del $'sdg_team\nsdu_ann' $'sdg_team\nsdu_ann' 'sdg_team')
row "D2 a refused groupdel is said as not removed, never as removed, and the next group is still removed" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'Group sdg_team was not removed' && ! printf '%s' "$OUT" | grep -q 'Removed group sdg_team' && printf '%s' "$OUT" | grep -qx 'Removed group sdu_ann.' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
OUT=$(run_del '' 'sdg_team' '')
row "D3 an empty list asks nothing and prints nothing" "$(ok "$([ ! -s "$T/del.log" ] && [ "$(printf '%s' "$OUT" | grep -v '^RC=0$' | wc -c)" -eq 0 ] && echo yes)")" "$OUT"

echo "--- S: static"
r=$(grep -n '^# ACCTGROUPS-READ-BEGIN$' "$DEL" | head -1 | cut -d: -f1)
s=$(grep -n 'bin/sd" -stop' "$DEL" | head -1 | cut -d: -f1)
x=$(grep -n '^sudo rm -fr "\$sdsysdir"$' "$DEL" | head -1 | cut -d: -f1)
d=$(grep -n '^ *# ACCTGROUPS-DEL-BEGIN$' "$DEL" | head -1 | cut -d: -f1)
k=$(awk '/^if \[ "\$keep_accts" = "DELETE" \]; then$/{l=NR} /^else$/{if(l) {print l; exit}}' "$DEL")
row "S1 READ comes after sd -stop and before the system directory is removed; DEL comes after it, inside the DELETE branch; each marker once" \
    "$(ok "$([ -n "$r" ] && [ -n "$s" ] && [ -n "$x" ] && [ -n "$d" ] && [ "$s" -lt "$r" ] && [ "$r" -lt "$x" ] && [ "$x" -lt "$d" ] \
        && [ "$(grep -c 'ACCTGROUPS-READ-BEGIN' "$DEL")" -eq 1 ] && [ "$(grep -c 'ACCTGROUPS-DEL-BEGIN' "$DEL")" -eq 1 ] \
        && awk -v d="$d" '/^if \[ "\$keep_accts" = "DELETE" \]; then$/{l=NR} NR==d{exit !(l>0 && l<d)}' "$DEL" && echo yes)")" "stop $s read $r rm $x del $d"

echo "test-delete-acctgroups: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
