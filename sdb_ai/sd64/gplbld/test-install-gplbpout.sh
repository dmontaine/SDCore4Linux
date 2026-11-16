#!/bin/bash
#
# test-install-gplbpout.sh - S.240: the installer gives the compiled programs (gpl.bp.out) to sdsys:sdusers, files 0644 and folders 0755,
# once, after the last compile.  Free: no sudo (a function here), no install.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-gplbpout.sh [--selftest]
#   INSTALLER=<a copy of installsdcore.sh> bash .../test-install-gplbpout.sh      (what --selftest uses)
#
#   G1  the block, run under the installer's own set and IFS on a scratch gpl.bp.out (files 0664, a folder 0775), leaves files 0644 and folders
#       0755, and asks chown -R sdsys:sdusers of exactly that folder (chown is a logging stub: no root here)
#   G2  a file that was 0600 is 0644 after (the mode is set, not only narrowed)
#   S   the block once; its call once, after SOURCE-GONE-END (the source and the last compile are behind it)
# NOT HERE: real ownership (the VM; measured 16 Nov 26 before the change: sessions and the S.256 witness unchanged).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INS="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; total=0
  mutant() {
    local name="$1" expr="$2" f="$T/$1.sh"
    total=$((total+1))
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: changed nothing"; return; fi
    if INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; then echo "  [MISSED] $name"; else echo "  [caught] $name"; caught=$((caught+1)); fi
  }
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass"; tail -5 "$T/real.out"; exit 1; }
  mutant no-chown    '/^# GPLBPOUT-MODE-BEGIN/,/^# GPLBPOUT-MODE-END/ s/    sudo chown -R sdsys:sdusers "$sdsysdir\/gpl.bp.out"/    :/'
  mutant files-664   '/^# GPLBPOUT-MODE-BEGIN/,/^# GPLBPOUT-MODE-END/ s/-type f -exec chmod 644/-type f -exec chmod 664/'
  mutant not-called  's/^fix_gplbpout_modes$/:/'
  echo "selftest: $caught of $total mutants caught"
  [ "$caught" -eq "$total" ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$INS" | head -2)
BLK=$(awk '/^# GPLBPOUT-MODE-BEGIN$/{f=1;next} /^# GPLBPOUT-MODE-END$/{f=0} f{print}' "$INS")
echo "installer : $INS"
[ -n "$BLK" ] || { echo "test-install-gplbpout: CANNOT RUN - no GPLBPOUT-MODE block"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-gplbpout: CANNOT RUN - no set line"; exit 2; }

S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
pass=0; fail=0
row() { if [ "$2" = ok ]; then echo "  [PASS] $1"; pass=$((pass+1)); else echo "  [FAIL] $1   <- $3"; fail=$((fail+1)); fi; }

mkdir -p "$S/sdsys/gpl.bp.out/sub"
echo x > "$S/sdsys/gpl.bp.out/a"; chmod 664 "$S/sdsys/gpl.bp.out/a"
echo x > "$S/sdsys/gpl.bp.out/sub/b"; chmod 600 "$S/sdsys/gpl.bp.out/sub/b"
chmod 775 "$S/sdsys/gpl.bp.out" "$S/sdsys/gpl.bp.out/sub"
{
  printf '%s\n' "$OPTS"
  printf 'sudo() { if [ "$1" = chown ]; then printf "CHOWN"; printf " %%s" "$@"; printf "\\n"; else "$@"; fi >> %q; }\n' "$S/log"
  printf 'sdsysdir=%q\n' "$S/sdsys"
  printf '%s\n' "$BLK"
  printf 'fix_gplbpout_modes\n'
} > "$S/run.sh"
out=$(bash "$S/run.sh" 2>&1); rc=$?
ma=$(stat -c %a "$S/sdsys/gpl.bp.out/a"); mb=$(stat -c %a "$S/sdsys/gpl.bp.out/sub/b"); md=$(stat -c %a "$S/sdsys/gpl.bp.out/sub"); mt=$(stat -c %a "$S/sdsys/gpl.bp.out")
log=$(cat "$S/log" 2>/dev/null)
[ "$rc" = 0 ] && [ "$ma" = 644 ] && [ "$md" = 755 ] && [ "$mt" = 755 ] && [ "$log" = "CHOWN chown -R sdsys:sdusers $S/sdsys/gpl.bp.out" ] \
  && row "G1 files 0644, folders 0755, chown -R sdsys:sdusers of gpl.bp.out itself" ok || row "G1 files 0644, folders 0755, chown -R sdsys:sdusers of gpl.bp.out itself" no "rc=$rc a=$ma sub=$md top=$mt log=$log out=$out"
[ "$mb" = 644 ] && row "G2 a 0600 file is 0644 after" ok || row "G2 a 0600 file is 0644 after" no "b=$mb"

nb=$(grep -c '^# GPLBPOUT-MODE-BEGIN$' "$INS"); nc=$(grep -c '^fix_gplbpout_modes$' "$INS")
lg=$(grep -n '^# SOURCE-GONE-END$' "$INS" | head -1 | cut -d: -f1); lc=$(grep -n '^fix_gplbpout_modes$' "$INS" | head -1 | cut -d: -f1)
[ "$nb" = 1 ] && [ "$nc" = 1 ] && [ -n "$lg" ] && [ -n "$lc" ] && [ "$lc" -gt "$lg" ] \
  && row "S  the block once, called once, after SOURCE-GONE-END" ok || row "S  the block once, called once, after SOURCE-GONE-END" no "block=$nb calls=$nc gone=$lg call=$lc"

echo "test-install-gplbpout: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
