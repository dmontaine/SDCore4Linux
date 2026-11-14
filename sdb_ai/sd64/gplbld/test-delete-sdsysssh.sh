#!/bin/bash
#
# test-delete-sdsysssh.sh - deletesdcore.sh notes an OPEN sdsys-over-ssh door in /home/sd/sdsys-ssh.saved when the configuration is kept, so that an
# upgrade keeps it open (owner, 13 Nov 2026, Windows chat: "I don't believe an upgrade should shut something that is already open").  The installer's
# half (the reopen) is test-install-sdsysssh.sh.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-sdsysssh.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-sdsysssh.sh --selftest
#   DELETER=<a copy of deletesdcore.sh> bash .../test-delete-sdsysssh.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (a function here), no install, no sshd.  The text between "# SDSYS-SSH-SAVE-BEGIN" and "# SDSYS-SSH-SAVE-END" is cut out of the
# script, the helper's path is rewritten to a stub that prints a given state, and it runs under the script's OWN "set" and "IFS" lines.
#
#   K1  configuration kept, door open: the note holds the word open, is mode 600, and the script says so
#   K2  configuration kept, door closed / state unknown: no note
#   K3  configuration deleted, door open: no note (a full uninstall removes it)
#   K4  a stale note from an earlier cycle is removed in every case, and no helper at all leaves none
#   K5  a note that cannot be written warns with the sudo command and the block still reaches its end
#   S   static: the block comes after the configuration question and BEFORE ssh-forcecommand --remove, and its markers occur once
# ANCHORED ON THE NOTE ON DISK (its content and mode), not on the words printed.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
DEL="${DELETER:-$(cd "$HERE/../../.." && pwd)/deletesdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/deletesdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  B='/^# SDSYS-SSH-SAVE-BEGIN/,/^# SDSYS-SSH-SAVE-END/'
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
  awk '/^# SDSYS-SSH-SAVE-BEGIN$/,/^# SDSYS-SSH-SAVE-END$/' "$REAL" > "$T/block"   # for after-remove: the block moved behind --remove
  mutant config-ignored      "$B s/\[ \"\$conf_deleted\" = no \] \&\& //"
  mutant any-state-saved     "$B s/\*sdsys-arm=open\*)/*)/"
  mutant stale-kept          "$B{/^sudo rm -f \"\$acct_path\/sdsys-ssh.saved\"$/d}"
  mutant world-readable      "$B s/chmod 600/chmod 644/"
  mutant wrong-word          "$B s/echo open | sudo tee/echo yes | sudo tee/"
  mutant write-fatal         "$B{/could not note that/a\\                exit 1
}"
  mutant after-remove        "/^# SDSYS-SSH-SAVE-BEGIN/,/^# SDSYS-SSH-SAVE-END/d;/^    sudo rm -f \/usr\/local\/sbin\/ssh-forcecommand$/r $T/block"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$DEL" | head -2)
BLK=$(awk '/^# SDSYS-SSH-SAVE-BEGIN$/{f=1;next} /^# SDSYS-SSH-SAVE-END$/{f=0} f{print}' "$DEL")
echo "deleter : $DEL"
[ -z "$BLK" ] && { echo "test-delete-sdsysssh: CANNOT RUN - no SDSYS-SSH-SAVE block"; exit 2; }
[ -z "$OPTS" ] && { echo "test-delete-sdsysssh: CANNOT RUN - no set / IFS line"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() { if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi; }

# a stub helper: prints $STATE for --sdsys-state
cat > "$T/fc" <<'EOF'
#!/bin/bash
[ "$1" = --sdsys-state ] && printf '%s\n' "$STATE"
exit 0
EOF
chmod +x "$T/fc"

run() {   # conf_deleted state helper-present(1/0) note-dir-writable(1/0)
  local blk="${BLK//\/usr\/local\/sbin\/ssh-forcecommand/$T/fc}"
  [ "$3" = 1 ] || blk="${BLK//\/usr\/local\/sbin\/ssh-forcecommand/$T/no-such-helper}"
  mkdir -p "$T/acct"; chmod 755 "$T/acct"; [ "$4" = 1 ] || chmod 555 "$T/acct"
  OPTS="$OPTS" BLK="$blk" CD="$1" STATE="$2" AP="$T/acct" bash -c '
      eval "$OPTS"
      sudo() { "$@"; }
      conf_deleted=$CD; acct_path=$AP
      eval "$BLK"
      echo REACHED-END' 2>&1
  local rc=$?
  chmod 755 "$T/acct"
  return $rc
}
N="$T/acct/sdsys-ssh.saved"

rm -f "$N"; out=$(run no "sdsys-arm=open" 1 1); rc=$?
row "K1 kept + open: the note says open, mode 600" "$([ $rc = 0 ] && [ "$(cat "$N" 2>/dev/null)" = open ] && [ "$(stat -c %a "$N")" = 600 ] && [[ "$out" == *"next install opens it again"* ]] && echo 0 || echo 1)" "rc=$rc out: $out"
bad=""
for st in "sdsys-arm=closed" "absent" ""; do rm -f "$N"; out=$(run no "$st" 1 1); [ -e "$N" ] && bad="$bad '$st'"; done
row "K2 kept + closed or unknown: no note" "$([ -z "$bad" ] && echo 0 || echo 1)" "noted for:$bad"
rm -f "$N"; out=$(run yes "sdsys-arm=open" 1 1)
row "K3 configuration deleted + open: no note" "$([ ! -e "$N" ] && echo 0 || echo 1)" "$out"
bad=""
for args in "no sdsys-arm=closed 1" "yes sdsys-arm=open 1" "no sdsys-arm=open 0"; do
  echo open > "$N"; set -- $args; out=$(run "$1" "$2" "$3" 1); [ -e "$N" ] && bad="$bad [$args]"
done
row "K4 a stale note is removed (closed, configuration deleted, no helper)" "$([ -z "$bad" ] && echo 0 || echo 1)" "left for:$bad"
rm -f "$N"; out=$(run no "sdsys-arm=open" 1 0); rc=$?
row "K5 a note that cannot be written warns with the sudo command and goes on" "$([ $rc = 0 ] && [ ! -e "$N" ] && [[ "$out" == *"could not note that"* && "$out" == *"sd-elevate sdsys-ssh on"* && "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "rc=$rc out: $out"

lq=$(grep -n -m1 '^read -r -p "Keep your existing configuration' "$DEL" | cut -d: -f1)
lb=$(grep -n -m1 '^# SDSYS-SSH-SAVE-BEGIN$' "$DEL" | cut -d: -f1)
lr=$(grep -n -m1 'ssh-forcecommand --remove' "$DEL" | cut -d: -f1)
nb=$(grep -c '^# SDSYS-SSH-SAVE-BEGIN$' "$DEL"); ne=$(grep -c '^# SDSYS-SSH-SAVE-END$' "$DEL")
row "S the block is after the configuration question and before --remove; markers once" "$([ -n "$lq" ] && [ -n "$lb" ] && [ -n "$lr" ] && [ "$lq" -lt "$lb" ] && [ "$lb" -lt "$lr" ] && [ "$nb" = 1 ] && [ "$ne" = 1 ] && echo 0 || echo 1)" "lines q=$lq block=$lb remove=$lr markers=$nb/$ne"

echo "test-delete-sdsysssh: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-delete-sdsysssh: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
