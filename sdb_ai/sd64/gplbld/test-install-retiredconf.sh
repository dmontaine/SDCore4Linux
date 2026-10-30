#!/bin/bash
#
# test-install-retiredconf.sh - installsdcore.sh takes the sd.conf parameters SD no longer has out of a restored sd.conf (S.87, 27 Oct 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-retiredconf.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-retiredconf.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-retiredconf.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a missing
# block is exit 2, never a pass).
#
# WHY IT EXISTS.  config.c refuses an unrecognised parameter and SD then does not start.  A keep-configuration install puts
# back an sd.conf written while a parameter existed, so the installer must remove the lines of the ones that went.  The
# block between RETIRED-CONF-BEGIN and RETIRED-CONF-END is cut out of the installer and run under its own "set" AND "IFS" lines
# (S.89, 30 Oct 26: the installer's IFS is $'\n\t', which made a list kept in a variable ONE word and the block remove nothing, while
# this check, run under the default IFS, passed) with sudo a function and /etc/sd.conf swapped for a scratch file:
#
#   A  a file holding a retired parameter loses that line and nothing else, in the same order
#   A2 a name from the middle of the list and the last name are both removed (the loop goes on past the first name; it does NOT check that the
#      list is COMPLETE - that would need config.c as it was in the last release, read through git)
#   B  a file without one is left byte for byte as it was, and the block says nothing
#   C  a comment, and a name that merely starts or ends the same way, are left alone
#   D  every name in the list is one config.c no longer parses and config.table no longer lists
#   E  the block comes after the sd.conf restore and before the DUMPDIR step

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
  mutant delete-anywhere    's/sed -i "\/\^\${retired_key}=\/d"/sed -i "\/${retired_key}\/d"/'
  mutant no-equals-sign     's/sed -i "\/\^\${retired_key}=\/d"/sed -i "\/^${retired_key}\/d"/'
  mutant list-has-live-key  's/^for retired_key in INVCASE /for retired_key in INVCASE NUMFILES /'
  # 30 Oct 26 (S.89): the ways the loop was, or could be, broken under the installer's IFS
  mutant list-in-a-variable 's/^for retired_key in \(.*\); do$/retired_conf_keys="\1"\nfor retired_key in $retired_conf_keys; do/'
  mutant only-the-first-name 's/^for retired_key in INVCASE .*; do$/for retired_key in INVCASE; do/'
  mutant last-name-dropped  's/ FILERULE; do$/; do/'
  mutant ifs-line-missing   '/^IFS=/d'
  echo "selftest: $caught of 7 mutants caught, $missed missed"
  [ "$caught" -eq 7 ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")        # 30 Oct 26 (S.89): the block runs under the installer's IFS too; without it a list in a variable split on spaces here and not in the install
BLOCK=$(awk '/^# RETIRED-CONF-BEGIN$/{f=1;next} /^# RETIRED-CONF-END$/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
echo "ifs       : ${IFSL:-<none found>}"
[ -z "$OPTS" ]  && { echo "test-install-retiredconf: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$IFSL" ]  && { echo "test-install-retiredconf: CANNOT RUN - no IFS line in the installer (the block must be run under it)"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-retiredconf: CANNOT RUN - no RETIRED-CONF block in the installer (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"
KEYS=$(printf '%s\n' "$BLOCK" | sed -n 's/^for retired_key in \(.*\); do$/\1/p')
echo "keys      : ${KEYS:-<none found>}"
[ -z "$KEYS" ] && { echo "test-install-retiredconf: CANNOT RUN - no 'for retired_key in <the names>; do' line (the names must be the literal words of the for: S.89)"; exit 2; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
run_block() {   # scratch file -> block's output
  local scr="$1"
  local body; body=$(printf '%s\n' "$BLOCK" | sed "s#/etc/sd\.conf#$scr#g")
  bash -c "$OPTS"$'\n'"$IFSL"$'\n'"sudo() { \"\$@\"; }"$'\n'"$body" 2>&1
}

# A
cat > "$T/a.conf" <<'EOF'
[sd]
NUMFILES=80
INVCASE=1
MAXIDLEN=63
EOF
out=$(run_block "$T/a.conf")
want=$'[sd]\nNUMFILES=80\nMAXIDLEN=63'
got=$(cat "$T/a.conf")
row "A: a retired parameter's line is removed and the others stay in order" $([ "$got" = "$want" ] && echo 0 || echo 1) "got: $(printf '%s' "$got" | tr '\n' '|')"
row "A: ... and the block says which" $(printf '%s' "$out" | grep -q 'Removed the retired parameter INVCASE' && echo 0 || echo 1) "output: $out"

# A2 (S.89): a name from the MIDDLE of the list and the LAST one, both at once - the loop must reach every name, not just the first
cat > "$T/a2.conf" <<'EOF'
[sd]
NUMFILES=80
APILOGIN=1
MAXIDLEN=63
FILERULE=2
EOF
out=$(run_block "$T/a2.conf")
want=$'[sd]\nNUMFILES=80\nMAXIDLEN=63'
got=$(cat "$T/a2.conf")
row "A2: a name from the middle of the list (APILOGIN) and the last (FILERULE) are both removed, under the installer's IFS" $([ "$got" = "$want" ] && echo 0 || echo 1) "got: $(printf '%s' "$got" | tr '\n' '|')"
row "A2: ... and the block says which, once each (two lines, one for each)" $(printf '%s' "$out" | grep -q 'Removed the retired parameter APILOGIN' && printf '%s' "$out" | grep -q 'Removed the retired parameter FILERULE' && [ "$(printf '%s\n' "$out" | grep -c 'Removed the retired parameter')" -eq 2 ] && echo 0 || echo 1) "output: $out"

# B
cat > "$T/b.conf" <<'EOF'
[sd]
NUMFILES=80
EOF
cp "$T/b.conf" "$T/b.before"
out=$(run_block "$T/b.conf")
row "B: a file without one is left byte for byte" $(cmp -s "$T/b.conf" "$T/b.before" && echo 0 || echo 1) "changed"
row "B: ... and the block prints nothing" $([ -z "$out" ] && echo 0 || echo 1) "output: $out"

# C
cat > "$T/c.conf" <<'EOF'
INVCASE=1
# INVCASE=1
INVCASEX=1
XINVCASE=1
 INVCASE=1
EOF
out=$(run_block "$T/c.conf")
want=$'# INVCASE=1\nINVCASEX=1\nXINVCASE=1\n INVCASE=1'
got=$(cat "$T/c.conf")
row "C: with the real line present, a comment and look-alike names are left alone" $([ "$got" = "$want" ] && echo 0 || echo 1) "got: $(printf '%s' "$got" | tr '\n' '|')"

# D0 (the null case of D): the names read from the for line are plain upper-case words; a variable or an array there would leave D with nothing to check
case "$KEYS" in *[!A-Z0-9\ ]*) d0=1;; *) d0=0;; esac
row "D0: the names in the for line are plain upper-case words (not a variable or an array)" "$d0" "keys: $KEYS"

# D
bad=""
for k in $KEYS; do
  if grep -q "\"$k=\|\"$k=%" "$SD64/gplsrc/config.c"; then bad="$bad $k(config.c)"; fi
  if grep -q "^$k|" "$SD64/sdsys/config.table"; then bad="$bad $k(config.table)"; fi
done
row "D: no retired name is still parsed by config.c or listed in config.table" $([ -z "$bad" ] && echo 0 || echo 1) "still live:$bad"

# E
lr=$(grep -n '^# Copy saved sd\.conf file if it exists' "$INST" | head -1 | cut -d: -f1)
lb=$(grep -n '^# RETIRED-CONF-BEGIN$' "$INST" | head -1 | cut -d: -f1)
ld=$(grep -n "^if ! grep -q '\^DUMPDIR='" "$INST" | head -1 | cut -d: -f1)
row "E: the block comes after the sd.conf restore and before the DUMPDIR step" $([ -n "$lr" ] && [ -n "$lb" ] && [ -n "$ld" ] && [ "$lr" -lt "$lb" ] && [ "$lb" -lt "$ld" ] && echo 0 || echo 1) "lines: restore ${lr:-?} block ${lb:-?} dumpdir ${ld:-?}"

echo "test-install-retiredconf: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
