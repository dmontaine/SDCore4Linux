#!/bin/bash
#
# test-delete-homesd.sh - deletesdcore.sh removes an EMPTY /home/sd when the accounts and the configuration were both deleted (S.255, 16 Nov 2026:
# the deleter makes /home/sd again before the configuration question, so a delete that kept nothing left an empty root-owned directory).
#
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-homesd.sh
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-homesd.sh --selftest
#   DELETER=<a copy of deletesdcore.sh> bash .../test-delete-homesd.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (a function here that runs the command itself), no install, no SD.  The block HOMESD-TIDY is cut out of the script and run
# under the script's OWN "set" and "IFS" lines, with acct_path a scratch directory.
#
#   H1  DELETE and configuration deleted, the directory empty: it is removed and the script says so
#   H2  the same with a file in it: the directory and the file stay, and the script says it kept it
#   H3  accounts kept: nothing is removed and nothing is said
#   H4  configuration kept: nothing is removed and nothing is said
#   H5  no directory (the null case): nothing is said, exit 0
#   S   static: the block comes after the account groups are removed and before the restart question; markers once each
#
# ANCHORED ON THE WORDING: "Removed ... (empty: nothing was kept)." only after rmdir succeeded, "Kept ...: something is still in it." only after it failed.
# NOT MEASURED HERE: the real /home/sd on a real DELETE (the VM).

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
  mutant no-keep-test      '/^# HOMESD-TIDY-BEGIN/,/^# HOMESD-TIDY-END/ s/\[ "\$keep_accts" = "DELETE" \] \&\& //'
  mutant no-conf-test      '/^# HOMESD-TIDY-BEGIN/,/^# HOMESD-TIDY-END/ s/\[ "\$conf_deleted" = yes \] \&\& //'
  mutant rm-rf             '/^# HOMESD-TIDY-BEGIN/,/^# HOMESD-TIDY-END/ s/sudo rmdir "\$acct_path"/sudo rm -rf "$acct_path"/'
  mutant kept-claims-done  '/^# HOMESD-TIDY-BEGIN/,/^# HOMESD-TIDY-END/ s/echo "Kept \$acct_path: something is still in it."/echo "Removed $acct_path (empty: nothing was kept)."/'
  mutant block-at-start    's/^# HOMESD-TIDY-BEGIN$/# HOMESD-TIDY-BEGIN-X/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$DEL" | head -2)
BLK=$(awk '/^# HOMESD-TIDY-BEGIN$/{f=1;next} /^# HOMESD-TIDY-END$/{f=0} f{print}' "$DEL")
echo "script    : $DEL"
echo "options   : $(printf '%s' "$OPTS" | tr '\n' ' ')"
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-delete-homesd: CANNOT RUN - no set line in the script"; exit 2; }
[ -n "$BLK" ] || { echo "test-delete-homesd: CANNOT RUN - no HOMESD-TIDY block in the script"; exit 2; }

S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
pass=0; fail=0
row() { if [ "$2" = ok ]; then echo "  [PASS] $1"; pass=$((pass+1)); else echo "  [FAIL] $1   <- $3"; fail=$((fail+1)); fi; }

# run KEEP CONF MAKE: KEEP is keep_accts, CONF is conf_deleted, MAKE is empty|file|none; prints the block's output, then the exit status
run() {
  local d="$S/home-sd"
  rm -rf "$d"
  case "$3" in empty) mkdir "$d" ;; file) mkdir "$d"; echo kept > "$d/sd.conf" ;; none) ;; esac
  {
    printf '%s\n' "$OPTS"
    printf 'sudo() { "$@"; }\n'
    printf 'acct_path=%q\nkeep_accts=%q\nconf_deleted=%q\n' "$d" "$1" "$2"
    printf '%s\n' "$BLK"
  } > "$S/blk.sh"
  out=$(bash "$S/blk.sh" 2>&1); rc=$?
}

run DELETE yes empty
[ "$rc" = 0 ] && [ ! -e "$S/home-sd" ] && printf '%s' "$out" | grep -q "^Removed $S/home-sd (empty: nothing was kept)\.$" \
  && row "H1 nothing kept, empty: removed and said" ok || row "H1 nothing kept, empty: removed and said" no "rc=$rc out=$out exists=$([ -e "$S/home-sd" ] && echo yes || echo no)"

run DELETE yes file
[ "$rc" = 0 ] && [ -f "$S/home-sd/sd.conf" ] && printf '%s' "$out" | grep -q "^Kept $S/home-sd: something is still in it\.$" && ! printf '%s' "$out" | grep -q '^Removed' \
  && row "H2 a file in it: the directory and the file stay, said" ok || row "H2 a file in it: the directory and the file stay, said" no "rc=$rc out=$out"

run KEEP yes empty
[ "$rc" = 0 ] && [ -d "$S/home-sd" ] && [ -z "$out" ] && row "H3 accounts kept: nothing removed, nothing said" ok || row "H3 accounts kept: nothing removed, nothing said" no "rc=$rc out=$out"

run DELETE no empty
[ "$rc" = 0 ] && [ -d "$S/home-sd" ] && [ -z "$out" ] && row "H4 configuration kept: nothing removed, nothing said" ok || row "H4 configuration kept: nothing removed, nothing said" no "rc=$rc out=$out"

run DELETE yes none
[ "$rc" = 0 ] && [ -z "$out" ] && row "H5 no directory (the null case): nothing said, exit 0" ok || row "H5 no directory (the null case): nothing said, exit 0" no "rc=$rc out=$out"

nb=$(grep -c '^# HOMESD-TIDY-BEGIN$' "$DEL"); ne=$(grep -c '^# HOMESD-TIDY-END$' "$DEL")
lb=$(grep -n '^# HOMESD-TIDY-BEGIN$' "$DEL" | head -1 | cut -d: -f1)
lg=$(grep -n 'ACCTGROUPS-DEL-END' "$DEL" | head -1 | cut -d: -f1)
lr=$(grep -n 'read -r -p "Restart computer now' "$DEL" | head -1 | cut -d: -f1)
[ "$nb" = 1 ] && [ "$ne" = 1 ] && [ -n "$lb" ] && [ -n "$lg" ] && [ -n "$lr" ] && [ "$lg" -lt "$lb" ] && [ "$lb" -lt "$lr" ] \
  && row "S  the block once, after the account groups go and before the restart question" ok || row "S  the block once, after the account groups go and before the restart question" no "markers $nb/$ne, lines groups=$lg block=$lb restart=$lr"

echo "test-delete-homesd: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
