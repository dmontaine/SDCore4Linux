#!/bin/bash
#
# test-install-retiredmasters.sh - the installer's RETIREDMASTERS block (S.96 M6, 2 Nov 2026; the owner: "retire"): the files of S.67's master-file copies
# (voc_master, dict_master, master_state, their dictionaries and $master.journal) are removed from the SDSYS directory by their exact names, a link among
# them is removed as a link and its target kept, nothing else in the directory is touched, and the install goes on whatever happens.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-retiredmasters.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-retiredmasters.sh --selftest
#   INSTALLER=<copy> bash .../test-install-retiredmasters.sh                       (what --selftest uses)
#
# FREE CHECK: no install, no sudo, no root.  The block is cut out between its markers, its directory variable is pointed at a scratch tree, and it runs
# under the installer's own `set -euo pipefail` and IFS with sudo a function that runs the command (STUB_RM_RC makes rm fail, to show the warning).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  ANCHORED ON THE DISK: what is there before and after is listed in the output.
#
#   R1  an upgrade's SDSYS directory holding all seven names (directories with files in them, and the journal): all seven are gone, and the block says 7
#   R2  ...and its neighbours are all still there: voc, accounts, a file voc_master.bak, a directory voc_master2, a file master_state.old
#   R3  a directory with none of the names: nothing is removed and nothing is said (the null case of R1: a block that did nothing must not pass R1)
#   R4  voc_master a LINK to a directory outside: the link is gone and the directory it named, with its file, is still there
#   R4b master_state a link that leads nowhere: it is removed too (test -e alone would not see it)
#   R5  a removal that fails: a WARNING naming the file, no "Removed" line, and the block still ends
#   R6  the block runs to its end under the installer's set -euo pipefail and IFS (R1's run)
#   T1  the block is in the installer once, after the sdsys user is put in the account groups and before the register is handed to sdsys, and the
#       installer no longer runs upgrade_masters or sync.masters

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
NAMES=(voc_master voc_master.dic dict_master dict_master.dic master_state master_state.dic '$master.journal')

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, old text, new text (in the installer)
    local name=$1 f="$T/m$total.sh"
    python3 -I -c 'import sys; t=open(sys.argv[1]).read(); o=sys.argv[3]; n=sys.argv[4]
if t.count(o) != 1: sys.exit(3)
open(sys.argv[2], "w").write(t.replace(o, n))' "$TREE/installsdcore.sh" "$f" "$2" "$3" || { echo "  [CANNOT] $name: its text is not in the file once"; missed=$((missed+1)); total=$((total+1)); return; }
    total=$((total+1))
    if INSTALLER="$f" bash "$THIS" > "$f.out" 2>&1; then echo "  [MISSED] $name"; missed=$((missed+1)); else echo "  [caught] $name"; caught=$((caught+1)); fi
  }
  mutant "the journal is forgotten" "master_state.dic '\$master.journal'; do" "master_state.dic; do"
  mutant "a dictionary is forgotten" "voc_master voc_master.dic dict_master" "voc_master dict_master"
  mutant "a wider pattern takes the neighbours too" 'if sudo rm -rf -- "$retired_masters_dir/$retired_masters_name"; then' 'if sudo rm -rf -- "$retired_masters_dir/$retired_masters_name"*; then'
  mutant "a link is followed" 'if sudo rm -rf -- "$retired_masters_dir/$retired_masters_name"; then' 'if sudo rm -rf -- "$retired_masters_dir/$retired_masters_name/"* "$retired_masters_dir/$retired_masters_name"; then'
  mutant "a link is not seen" '    if sudo test -e "$retired_masters_dir/$retired_masters_name" || sudo test -L "$retired_masters_dir/$retired_masters_name"; then' '    if sudo test -d "$retired_masters_dir/$retired_masters_name" || sudo test -f "$retired_masters_dir/$retired_masters_name"; then'
  mutant "a failure stops the install" '            echo "WARNING: could not remove' '            exit 1; echo "WARNING: could not remove'
  mutant "a failure is counted as removed" '            retired_masters_gone=$((retired_masters_gone + 1))
        else' '            retired_masters_gone=$((retired_masters_gone + 1))
        else
            retired_masters_gone=$((retired_masters_gone + 1))'
  mutant "the block says it removed files when there were none" 'if [ "$retired_masters_gone" -gt 0 ]; then' 'if [ "$retired_masters_gone" -ge 0 ]; then'
  mutant "the installer runs upgrade_masters again" '# RETIREDMASTERS-END' '# RETIREDMASTERS-END
om_out=$(sudo "$sdsysdir/bin/sd" -internal RUN gpl.bp upgrade_masters 2>&1) || om_rc=$?'
  echo "test-install-retiredmasters --selftest: $total mutant(s), $missed not caught"
  [ "$missed" -eq 0 ] && [ "$total" -ge 9 ] && exit 0 || exit 1
fi

pass=0; fail=0
row() {   # id, label, condition-exit-status
  if [ "$3" -eq 0 ]; then echo "  [PASS] $1 $2"; pass=$((pass+1)); else echo "  [FAIL] $1 $2"; fail=$((fail+1)); fi
}

[ -f "$INST" ] || { echo "test-install-retiredmasters: CANNOT RUN - no installer at $INST"; exit 2; }
BLOCK=$(awk '/^# RETIREDMASTERS-BEGIN$/{f=1} f{print} /^# RETIREDMASTERS-END$/{f=0}' "$INST")
[ -n "$BLOCK" ] && grep -q 'RETIREDMASTERS-END' <<<"$BLOCK" || { echo "test-install-retiredmasters: CANNOT RUN - no RETIREDMASTERS block in $INST"; exit 2; }
echo "installer: $INST"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

run_block() {   # DIR - runs the block on DIR under the installer's set options and IFS; prints its output, then "BLOCK-ENDED"
  local d=$1 body
  body=$(sed -e "s|^retired_masters_dir=.*|retired_masters_dir='$d'|" <<<"$BLOCK")
  bash -c "set -euo pipefail
IFS=\$'\\n\\t'
sudo() { if [ \"\$1\" = rm ] && [ -n \"\${STUB_RM_RC:-}\" ]; then return \"\$STUB_RM_RC\"; fi; \"\$@\"; }
$body
echo BLOCK-ENDED" 2>&1
}

listing() { (cd "$1" && find . -mindepth 1 | LC_ALL=C sort | tr '\n' ' '); }

# R1 / R2 / R6
d="$T/r1"; mkdir -p "$d/voc" "$d/accounts" "$d/voc_master2"
for n in "${NAMES[@]}"; do
  if [ "$n" = '$master.journal' ]; then printf 'line\n' > "$d/$n"; else mkdir -p "$d/$n"; printf 'x' > "$d/$n/%0"; printf 'y' > "$d/$n/%1"; fi
done
printf 'keep\n' > "$d/voc_master.bak"; printf 'keep\n' > "$d/master_state.old"; printf 'r\n' > "$d/accounts/acme"; printf 'v' > "$d/voc/%0"
echo "R1 before: $(listing "$d")"
out=$(run_block "$d")
echo "R1 after:  $(listing "$d")"
echo "R1 said:   $(tr '\n' '|' <<<"$out")"
gone=0; for n in "${NAMES[@]}"; do [ -e "$d/$n" ] || [ -L "$d/$n" ] || gone=$((gone+1)); done
row R1 "all seven names are gone and the block says it removed 7" $( [ "$gone" -eq 7 ] && grep -q "Removed 7 file(s) of the retired master-file copies" <<<"$out"; echo $?)
row R2 "the neighbours are still there: voc, accounts, voc_master.bak, voc_master2, master_state.old" \
  $( [ -f "$d/voc/%0" ] && [ -f "$d/accounts/acme" ] && [ -f "$d/voc_master.bak" ] && [ -d "$d/voc_master2" ] && [ -f "$d/master_state.old" ]; echo $?)
row R6 "the block runs to its end under the installer's set -euo pipefail and IFS" $(grep -q BLOCK-ENDED <<<"$out" && ! grep -q WARNING <<<"$out"; echo $?)

# R3
d="$T/r3"; mkdir -p "$d/voc" "$d/accounts"; printf 'v' > "$d/voc/%0"
before=$(listing "$d"); out=$(run_block "$d"); after=$(listing "$d")
echo "R3 before: $before  after: $after"
row R3 "a directory without the names: nothing removed, nothing said, the block ends" $( [ "$before" = "$after" ] && ! grep -q -i 'removed\|WARNING' <<<"$out" && grep -q BLOCK-ENDED <<<"$out"; echo $?)

# R4
d="$T/r4"; o="$T/outside"; mkdir -p "$d" "$o"; printf 'precious\n' > "$o/data"; ln -s "$o" "$d/voc_master"
out=$(run_block "$d")
echo "R4 after: link $( [ -L "$d/voc_master" ] && echo there || echo gone), outside: $(listing "$o")"
row R4 "voc_master as a link: the link is gone, the directory it named and its file are still there" \
  $( [ ! -L "$d/voc_master" ] && [ "$(cat "$o/data" 2>/dev/null)" = precious ] && grep -q "Removed 1 file(s)" <<<"$out"; echo $?)

# R4b
d="$T/r4b"; mkdir -p "$d"; ln -s "$T/nowhere" "$d/master_state"
out=$(run_block "$d")
row R4b "master_state a link that leads nowhere: it is removed too" $( [ ! -L "$d/master_state" ] && grep -q "Removed 1 file(s)" <<<"$out"; echo $?)

# R5
d="$T/r5"; mkdir -p "$d/dict_master"
out=$(STUB_RM_RC=1 run_block "$d")
echo "R5 said: $(tr '\n' '|' <<<"$out")"
row R5 "a removal that fails: a WARNING naming it, no Removed line, the block ends" \
  $(grep -q "WARNING: could not remove $d/dict_master" <<<"$out" && ! grep -q '^Removed' <<<"$out" && grep -q BLOCK-ENDED <<<"$out"; echo $?)

# T1
n_groups=$(grep -n '^sdsys_groups_default "\$ACCT_PATH/\\\$sdsys.access"$' "$INST" | head -1 | cut -d: -f1)
n_b=$(grep -n '^# RETIREDMASTERS-BEGIN$' "$INST" | cut -d: -f1)
n_reg=$(grep -n '^sudo chown -R sdsys:sdusers "\$sdsysdir/accounts"$' "$INST" | head -1 | cut -d: -f1)
echo "T1 lines: groups $n_groups, block $n_b, register $n_reg"
row T1 "the block is in the installer once, after sdsys_groups_default and before the register is handed over; no upgrade_masters or sync.masters is run" \
  $( [ -n "$n_groups" ] && [ -n "$n_b" ] && [ -n "$n_reg" ] && [ "$n_groups" -lt "$n_b" ] && [ "$n_b" -lt "$n_reg" ] && [ "$(grep -c '^# RETIREDMASTERS-BEGIN$' "$INST")" = 1 ] \
     && ! grep -v '^ *#' "$INST" | grep -q -E 'upgrade_masters|sync\.masters'; echo $?)

echo "test-install-retiredmasters: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -ge 7 ]
