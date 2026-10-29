#!/bin/bash
#
# test-install-screentheme.sh - installsdcore.sh adds SCREENTHEME=blue to a restored sd.conf that has no SCREENTHEME line (S.88 3.7a, 29 Oct 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-screentheme.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-screentheme.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-screentheme.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a missing
# block is exit 2, never a pass).
#
# WHY IT EXISTS.  The shipped sd.conf says SCREENTHEME=blue, but a keep-configuration install puts back a file written
# before the line existed, and CONFIG('SCREENTHEME') is what the screen library reads.  The block between
# SCREENTHEME-BEGIN and SCREENTHEME-END is cut out of the installer and run under its own "set" with sudo a function
# and /etc/sd.conf swapped for a scratch file:
#
#   A  a file without the line gets SCREENTHEME=blue at the end, the other lines untouched and in order, and the block says so
#   B  a file with SCREENTHEME=classic is left byte for byte as it was, and the block prints nothing
#   C  an explicit SCREENTHEME=mono is left alone (the administrator's choice stands)
#   D  a comment and a look-alike name do not count as the line: the real one is added
#   E  the block comes once, after the DUMPDIR step, and the shipped sd.conf has the line once, in the [sd] section

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"
SD64="$(cd "$HERE/.." && pwd)"

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
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -5 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant unanchored-test    's/grep -q .^SCREENTHEME=. /grep -q SCREENTHEME /'
  mutant wrong-theme        's/echo "SCREENTHEME=blue"/echo "SCREENTHEME=mono"/'
  mutant overwrites-file    's/echo "SCREENTHEME=blue" | sudo tee -a/echo "SCREENTHEME=blue" | sudo tee/'
  echo "selftest: $caught of 3 mutants caught, $missed missed"
  [ "$caught" -eq 3 ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
BLOCK=$(awk '/^# SCREENTHEME-BEGIN$/{f=1;next} /^# SCREENTHEME-END$/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ]  && { echo "test-install-screentheme: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-screentheme: CANNOT RUN - no SCREENTHEME block in the installer (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
run_block() {   # scratch file -> block's output
  local scr="$1"
  local body; body=$(printf '%s\n' "$BLOCK" | sed "s#/etc/sd\.conf#$scr#g")
  bash -c "$OPTS"$'\n'"sudo() { \"\$@\"; }"$'\n'"$body" 2>&1
}

# A
cat > "$T/a.conf" <<'EOF'
[sd]
NUMFILES=80
DUMPDIR=/usr/local/sdsys/dumps
EOF
out=$(run_block "$T/a.conf")
want=$'[sd]\nNUMFILES=80\nDUMPDIR=/usr/local/sdsys/dumps\nSCREENTHEME=blue'
got=$(cat "$T/a.conf")
row "A: the line is added at the end and the others stay in order" $([ "$got" = "$want" ] && echo 0 || echo 1) "got: $(printf '%s' "$got" | tr '\n' '|')"
row "A: ... and the block says it added SCREENTHEME=blue" $(printf '%s' "$out" | grep -q '^Added SCREENTHEME=blue to ' && echo 0 || echo 1) "output: $out"
out2=$(run_block "$T/a.conf")
row "A: ... and a second run changes nothing and says nothing" $([ "$(cat "$T/a.conf")" = "$want" ] && [ -z "$out2" ] && echo 0 || echo 1) "output: $out2"

# B
printf '[sd]\nNUMFILES=80\nSCREENTHEME=classic\n' > "$T/b.conf"
cp "$T/b.conf" "$T/b.before"
out=$(run_block "$T/b.conf")
row "B: a file with SCREENTHEME=classic is left byte for byte" $(cmp -s "$T/b.conf" "$T/b.before" && echo 0 || echo 1) "changed"
row "B: ... and the block prints nothing" $([ -z "$out" ] && echo 0 || echo 1) "output: $out"

# C
printf '[sd]\nSCREENTHEME=mono\n' > "$T/c.conf"
cp "$T/c.conf" "$T/c.before"
out=$(run_block "$T/c.conf")
row "C: an explicit SCREENTHEME=mono is left alone" $(cmp -s "$T/c.conf" "$T/c.before" && [ -z "$out" ] && echo 0 || echo 1) "output: $out"

# D
cat > "$T/d.conf" <<'EOF'
[sd]
# SCREENTHEME=classic
XSCREENTHEME=1
 SCREENTHEME=classic
EOF
out=$(run_block "$T/d.conf")
want=$'[sd]\n# SCREENTHEME=classic\nXSCREENTHEME=1\n SCREENTHEME=classic\nSCREENTHEME=blue'
got=$(cat "$T/d.conf")
row "D: a comment and look-alike names do not count; the real line is added" $([ "$got" = "$want" ] && echo 0 || echo 1) "got: $(printf '%s' "$got" | tr '\n' '|')"

# E
nb=$(grep -c '^# SCREENTHEME-BEGIN$' "$INST")
ld=$(grep -n "^if ! grep -q '\^DUMPDIR='" "$INST" | head -1 | cut -d: -f1)
ls=$(grep -n '^# SCREENTHEME-BEGIN$' "$INST" | head -1 | cut -d: -f1)
row "E: the block is in the installer once and comes after the DUMPDIR step" $([ "$nb" = 1 ] && [ -n "$ld" ] && [ -n "$ls" ] && [ "$ld" -lt "$ls" ] && echo 0 || echo 1) "blocks $nb, dumpdir ${ld:-?} screentheme ${ls:-?}"
shipped=$(awk '/^\[/{sec=tolower($0)} /^SCREENTHEME=blue$/{if (sec=="[sd]") n++} END{print n+0}' "$SD64/sd.conf")
total=$(grep -c '^SCREENTHEME=' "$SD64/sd.conf")
row "E: the shipped sd.conf has SCREENTHEME=blue once, in [sd], and no other SCREENTHEME line" $([ "$shipped" = 1 ] && [ "$total" = 1 ] && echo 0 || echo 1) "in [sd] $shipped, all $total"

echo "test-install-screentheme: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
