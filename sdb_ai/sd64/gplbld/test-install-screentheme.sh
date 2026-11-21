#!/bin/bash
#
# test-install-screentheme.sh - installsdcore.sh leaves a restored sd.conf's SCREENTHEME exactly as it is (S.293, 22 Nov 2026).  Until then it gave the file
# the delivered theme: paper added where there was no line, and a restored SCREENTHEME=blue changed to paper once (S.88 3.7a, 29 Oct 2026; S.172, 8 Nov 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-screentheme.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-screentheme.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-screentheme.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a missing
# block is exit 2, never a pass).
#
# START-HISTORY:
# 29 Oct 26 dm  New (S.88 3.7a): blue added to a file without the line.
# 8 Nov 26 dm   S.172: the delivered theme is paper; rows F to H for the once-only change of a restored blue.
# 22 Nov 26 dm  S.293 (owner, 21 Nov 2026, relayed T0830, asked whether S.172's one-time change stands as an exception to "put back exactly as it was": "Each
#               user can change their theme, I would think they would get their existing theme back."): BOTH steps are gone.  The rows now say the opposite:
#               nothing is added, nothing is changed, nothing is written, nothing is said.
# END-HISTORY
#
# WHY IT EXISTS.  The shipped sd.conf says SCREENTHEME=paper and a keep-configuration install puts back an older file; CONFIG('SCREENTHEME') is what the screen
# library reads.  A user's own theme must come back as it was, so the block between SCREENTHEME-BEGIN and SCREENTHEME-END (now only the comment that says so)
# is cut out of the installer and run under its own "set" and IFS with sudo a function and /etc/sd.conf swapped for a scratch file:
#
#   A  a restored file with NO SCREENTHEME line is left byte for byte (nothing added: it stays on the library's own default), and nothing is said
#   B  SCREENTHEME=classic, mono, night, paper and a look-alike name are each left byte for byte
#   C  a comment and look-alike names do not make the block add the real line
#   D  a restored SCREENTHEME=blue is left as blue - not changed to paper, no marker line added
#   E  a file an OLDER install already converted (paper and the old marker line) is left byte for byte
#   F  the block comes once, after the DUMPDIR step, and the shipped sd.conf has SCREENTHEME=paper once, in the [sd] section (a NEW install gets paper from it)
#   G  the block holds no command at all, and no other line of the installer that is not a comment mentions SCREENTHEME

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"
SD64="$(cd "$HERE/.." && pwd)"
MARK='# SCREENTHEME blue was changed to paper by the installer (S.172); set it back to blue to keep the old look'

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
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -5 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  # each mutant puts one OLD behaviour (or a new one) back inside the block
  mutant adds-paper-to-lineless 's/^# SCREENTHEME-BEGIN$/&\nif ! grep -q "^SCREENTHEME=" \/etc\/sd.conf; then echo "SCREENTHEME=paper" | sudo tee -a \/etc\/sd.conf >\/dev\/null; fi/'
  mutant converts-blue          's/^# SCREENTHEME-BEGIN$/&\nsudo sed -i "s\/^SCREENTHEME=blue[[:space:]]*$\/SCREENTHEME=paper\/" \/etc\/sd.conf/'
  mutant writes-the-marker      's/^# SCREENTHEME-BEGIN$/&\necho "# marker" | sudo tee -a \/etc\/sd.conf >\/dev\/null/'
  mutant says-something         's/^# SCREENTHEME-BEGIN$/&\necho "SCREENTHEME is kept"/'
  mutant code-outside-block     's/^# SCREENTHEME-END$/&\nsudo sed -i "s\/SCREENTHEME=blue\/SCREENTHEME=paper\/" \/etc\/sd.conf/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST"; grep -m1 -E '^IFS=' "$INST")        # 30 Oct 26 (S.89): the installer's IFS too - a block must be run under both
case "$OPTS" in *IFS=*) ;; *) echo "test-install-screentheme: CANNOT RUN - no IFS line in the installer (S.89)"; exit 2;; esac
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
same() {   # conf-file -> 0 when the block leaves it byte for byte and prints nothing
  local f="$1" out
  cp "$f" "$f.before"; out=$(run_block "$f")
  cmp -s "$f" "$f.before" && [ -z "$out" ]
}

# A
cat > "$T/a.conf" <<'EOF'
[sd]
NUMFILES=80
DUMPDIR=/usr/local/sdsys/dumps
EOF
cp "$T/a.conf" "$T/a.before"; out=$(run_block "$T/a.conf")
row "A: a restored file with NO SCREENTHEME line is left byte for byte (it stays on the library's default)" $(cmp -s "$T/a.conf" "$T/a.before" && echo 0 || echo 1) "got: $(tr '\n' '|' < "$T/a.conf")"
row "A: ... and the block says nothing" $([ -z "$out" ] && echo 0 || echo 1) "output: $out"

# B
bad=""
for v in classic mono night paper bluex dark light; do
  printf '[sd]\nNUMFILES=80\nSCREENTHEME=%s\n' "$v" > "$T/b.conf"; same "$T/b.conf" || bad="$bad $v"
done
row "B: SCREENTHEME=classic, mono, night, paper, dark, light and a look-alike are each left byte for byte, nothing said" $([ -z "$bad" ] && echo 0 || echo 1) "changed for:$bad"

# C
cat > "$T/c.conf" <<'EOF'
[sd]
# SCREENTHEME=classic
XSCREENTHEME=1
 SCREENTHEME=classic
EOF
row "C: a comment and look-alike names are left alone too - the real line is NOT added" $(same "$T/c.conf" && echo 0 || echo 1) "changed: $(tr '\n' '|' < "$T/c.conf")"

# D
printf '[sd]\nNUMFILES=80\nSCREENTHEME=blue\nDUMPDIR=/x\n' > "$T/d.conf"
cp "$T/d.conf" "$T/d.before"; out=$(run_block "$T/d.conf")
row "D: a restored SCREENTHEME=blue stays blue (no change to paper, no marker line)" $(cmp -s "$T/d.conf" "$T/d.before" && ! grep -qF 'SCREENTHEME blue was changed' "$T/d.conf" && echo 0 || echo 1) "got: $(tr '\n' '|' < "$T/d.conf")"
row "D: ... and the block says nothing" $([ -z "$out" ] && echo 0 || echo 1) "output: $out"
printf '[sd]\nSCREENTHEME=blue   \n' > "$T/d2.conf"
row "D: blue with trailing spaces stays exactly as it was" $(same "$T/d2.conf" && echo 0 || echo 1) "changed"

# E
printf '[sd]\nSCREENTHEME=paper\n%s\n' "$MARK" > "$T/e.conf"
row "E: a file an OLDER install already converted (paper and the old marker line) is left byte for byte" $(same "$T/e.conf" && echo 0 || echo 1) "changed"
printf '[sd]\nSCREENTHEME=blue\n%s\n' "$MARK" > "$T/e2.conf"
row "E: blue set again after the old marker is left byte for byte" $(same "$T/e2.conf" && echo 0 || echo 1) "changed"

# F
nb=$(grep -c '^# SCREENTHEME-BEGIN$' "$INST")
ld=$(grep -n "^if ! grep -q '\^DUMPDIR='" "$INST" | head -1 | cut -d: -f1)
ls=$(grep -n '^# SCREENTHEME-BEGIN$' "$INST" | head -1 | cut -d: -f1)
row "F: the block is in the installer once and comes after the DUMPDIR step" $([ "$nb" = 1 ] && [ -n "$ld" ] && [ -n "$ls" ] && [ "$ld" -lt "$ls" ] && echo 0 || echo 1) "blocks $nb, dumpdir ${ld:-?} screentheme ${ls:-?}"
shipped=$(awk '/^\[/{sec=tolower($0)} /^SCREENTHEME=paper$/{if (sec=="[sd]") n++} END{print n+0}' "$SD64/sd.conf")
total=$(grep -c '^SCREENTHEME=' "$SD64/sd.conf")
row "F: the shipped sd.conf has SCREENTHEME=paper once, in [sd], and no other SCREENTHEME line (a NEW install gets paper from it)" $([ "$shipped" = 1 ] && [ "$total" = 1 ] && echo 0 || echo 1) "in [sd] $shipped, all $total"

# G
code=$(printf '%s\n' "$BLOCK" | grep -v -E '^[[:space:]]*(#|$)' || true)
row "G: the block holds no command at all (comments only)" $([ -z "$code" ] && echo 0 || echo 1) "commands: $code"
others=$(grep -n 'SCREENTHEME' "$INST" | grep -v -E '^[0-9]+:[[:space:]]*#' || true)
row "G: no line of the installer that is not a comment mentions SCREENTHEME" $([ -z "$others" ] && echo 0 || echo 1) "lines: $others"

echo "test-install-screentheme: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
