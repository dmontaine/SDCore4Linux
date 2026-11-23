#!/bin/bash
#
# test-install-routereset.sh - an install that finds no kept SD data empties the route groups (S.310, owner 22 Nov 2026, Windows row 393:
#                              "Yes, reset them, and tell linux").
#
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-routereset.sh
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-routereset.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-routereset.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a missing block is exit 2).
#
# START-HISTORY:
# 23 Nov 26 dm  New (S.310).  deletesdcore.sh keeps sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin, sdaiusers and sdsshnokey with their
#               members when the accounts are kept; a "fresh" install after that data was removed by hand reused them, members and all.
# END-HISTORY
#
# WHAT IT DOES.  The block between "# ROUTE-GROUPS-BEGIN" and "# ROUTE-GROUPS-END" is cut out of the installer and run under the installer's
# own "set" and IFS, with getent answering from a table, sudo a logging function, and /home/sd changed to a scratch directory (this machine's
# real /home/sd is a live install).  The evidence is the sudo calls made and the lines printed:
#   F  nothing kept: every route group that has members is emptied (gpasswd -M ""); sdsshnokey, which only refuses, is NOT (Windows' rule, T1820);
#      an empty group is left alone; a missing one made
#   K  /home/sd/user_accounts kept: no membership changed
#   R  only the account register /home/sd/accounts kept: no membership changed
#   U  an upgrade over a running install (upgrade_over=1): no membership changed
#   P  the block comes before the account directories are made and before any gate is granted to the installing user
# NOT MEASURED HERE: that gpasswd -M "" empties a real group (the VM install is that row).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, sed expression
    local name="$1" expr="$2" f="$T/$1.sh" rc
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant always-reset        's/^route_reset=0$/route_reset=1/'
  mutant never-reset         's/then route_reset=1; fi$/then route_reset=0; fi/'
  mutant register-ignored    's| \&\& \[ ! -d /home/sd/accounts \]||'
  mutant upgrade-ignored     's| \&\& \[ "\${upgrade_over:-0}" -eq 0 \]||'
  mutant nokey-emptied       's/^  echo "Group sdsshnokey already exists\."$/  route_group_found sdsshnokey/'
  mutant no-gpasswd          's/^    sudo gpasswd -M "" "\$g" > \/dev\/null$/    true/'
  echo "selftest: $caught of 6 mutants caught, $missed missed"
  [ "$caught" -eq 6 ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST"; grep -m1 -E '^IFS=' "$INST")
case "$OPTS" in *IFS=*) ;; *) echo "test-install-routereset: CANNOT RUN - no IFS line in the installer"; exit 2;; esac
BLOCK0=$(awk '/^# ROUTE-GROUPS-BEGIN$/{f=1} f{print} /^# ROUTE-GROUPS-END$/{exit}' "$INST")
echo "installer : $INST"
echo "options   : $(printf '%s' "$OPTS" | tr '\n' ' ')"
[ -z "$BLOCK0" ] && { echo "test-install-routereset: CANNOT RUN - no ROUTE-GROUPS block in the installer (nothing to check)"; exit 2; }
printf '%s\n' "$BLOCK0" | grep -q '^# ROUTE-GROUPS-END$' || { echo "test-install-routereset: CANNOT RUN - the block has no END marker"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK0" | wc -l) lines"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
BLOCK=$(printf '%s\n' "$BLOCK0" | sed "s|/home/sd/|$T/home/sd/|g")
CALLS="$T/calls"; GROUPS_TBL="$T/groups"
export BLOCK OPTS CALLS GROUPS_TBL

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
# The groups as found: three with members (one of them sdsshnokey), two empty, two missing.
table() {
  cat > "$GROUPS_TBL" <<'TBL'
sdssh:x:990:don,olduser
sdapi:x:991:don
sdfiles:x:992:
sdfileswrite:x:993:
sdsshnokey:x:996:olduser
TBL
}
run_block() {   # upgrade_over value; prints the block's output then REACHED-END
  : > "$CALLS"; table
  UPG="$1" bash -c '
      eval "$OPTS"
      upgrade_over="$UPG"
      getent() { [ "$1" = group ] || return 2; ( IFS=" "; grep -E "^$2:" "$GROUPS_TBL" ) || return 2; }
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$CALLS"; return 0; }
      eval "$BLOCK"
      echo "REACHED-END"' 2>&1
}
show() { printf '%s\n' "$1" | sed 's/^/      | /'; echo "      sudo: $(tr '\n' ';' < "$CALLS")"; }
emptied() { grep -c '^gpasswd -M  ' "$CALLS"; }       # "$*" joins gpasswd -M "" NAME as "gpasswd -M  NAME"

echo "--- F: nothing kept (a fresh install after the data was removed)"
mkdir -p "$T/home/sd"
OUT=$(run_block 0); show "$OUT"
row "F0 the block ran to its end" "$(printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "it stopped"
row "F1 sdssh and sdapi (the route groups with members) are emptied, and only they: sdsshnokey keeps its member" \
    "$([ "$(emptied)" = 2 ] && grep -qx 'gpasswd -M  sdssh' "$CALLS" && grep -qx 'gpasswd -M  sdapi' "$CALLS" && ! grep -q 'gpasswd -M  sdsshnokey' "$CALLS" && echo 0 || echo 1)" \
    "$(tr '\n' ';' < "$CALLS")"
row "F2 the empty groups are not touched and say they exist" \
    "$(! grep -q 'gpasswd -M  sdfiles$' "$CALLS" && printf '%s' "$OUT" | grep -qx 'Group sdfiles already exists.' && echo 0 || echo 1)" "sdfiles was touched or not reported"
row "F3 the missing groups are made (sdfilesadmin, sdaiusers)" \
    "$(grep -qx 'groupadd --system sdfilesadmin' "$CALLS" && grep -qx 'groupadd --system sdaiusers' "$CALLS" && echo 0 || echo 1)" "no groupadd"
row "F4 each emptied group is said so, naming the members removed" \
    "$([ "$(printf '%s\n' "$OUT" | grep -c 'its members from an earlier install were removed')" = 2 ] && printf '%s' "$OUT" | grep -q 'sdssh already exists.*were removed: don,olduser$' && printf '%s' "$OUT" | grep -q 'sdapi already exists.*were removed: don$' && printf '%s' "$OUT" | grep -qx 'Group sdsshnokey already exists.' && echo 0 || echo 1)" "not 2 lines, or sdsshnokey not left as it was"

for case in "K user_accounts kept:user_accounts:0" "R only the account register kept:accounts:0" "U an upgrade over a running install::1"; do
  id=${case%% *}; rest=${case#* }; label=${rest%%:*}; rest=${rest#*:}; dir=${rest%%:*}; upg=${rest#*:}
  echo "--- $id: $label"
  rm -rf "$T/home"; mkdir -p "$T/home/sd"; [ -n "$dir" ] && mkdir -p "$T/home/sd/$dir"
  OUT=$(run_block "$upg"); show "$OUT"
  row "${id}1 no membership is changed" "$([ "$(emptied)" = 0 ] && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "$(tr '\n' ';' < "$CALLS")"
  row "${id}2 and the groups that hold members say only that they exist" \
      "$(printf '%s' "$OUT" | grep -qx 'Group sdssh already exists.' && ! printf '%s' "$OUT" | grep -q 'were removed' && echo 0 || echo 1)" "wrong wording"
done

echo "--- P: where it sits in the installer"
code() { grep -n -E '^[[:space:]]*[^#[:space:]]' "$INST"; }
L_END=$(grep -n '^# ROUTE-GROUPS-END$' "$INST" | head -1 | cut -d: -f1)
L_MKDIR=$(code | grep -E 'mkdir -p "\$ACCT_PATH"/user_accounts' | head -1 | cut -d: -f1)
L_GATES=$(code | grep -E '^[0-9]+:[[:space:]]*open_installer_gates "' | head -1 | cut -d: -f1)     # the call, not the definition
L_UPG=$(code | grep -E '^[0-9]+:[[:space:]]*upgrade_over=1' | head -1 | cut -d: -f1)
echo "      block ends at ${L_END:-?}; upgrade_over=1 at ${L_UPG:-?}; account dirs made at ${L_MKDIR:-?}; gates opened at ${L_GATES:-?}"
row "P1 upgrade_over is known before the block" "$([ -n "$L_UPG" ] && [ -n "$L_END" ] && [ "$L_UPG" -lt "$L_END" ] && echo 0 || echo 1)" "order"
row "P2 the block ends before the account directories are made" "$([ -n "$L_MKDIR" ] && [ "$L_END" -lt "$L_MKDIR" ] && echo 0 || echo 1)" "order"
row "P3 and before any gate is opened for the installing user" "$([ -n "$L_GATES" ] && [ "$L_END" -lt "$L_GATES" ] && echo 0 || echo 1)" "order"
row "P4 the block holds no exit" "$(printf '%s\n' "$BLOCK0" | grep -q -E '^[[:space:]]*exit' && echo 1 || echo 0)" "an exit in the block"

echo "test-install-routereset: $pass passed, $fail failed"
[ "$((pass + fail))" -eq 0 ] && { echo "test-install-routereset: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
