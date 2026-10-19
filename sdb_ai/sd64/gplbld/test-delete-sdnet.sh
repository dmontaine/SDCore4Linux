#!/bin/bash
#
# test-delete-sdnet.sh - deletesdcore.sh removes /var/lib/sd-net (every user's stored SDNet login) when the accounts OR the configuration are
# deleted, and keeps it only when BOTH are kept (owner, 19 Oct 2026; SDNet audit K8e).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-sdnet.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-delete-sdnet.sh --selftest
#   DELETER=<a copy of deletesdcore.sh> bash .../test-delete-sdnet.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (a function here), no install, no SD.  The text between "# SDNET-LOGINS-BEGIN" and "# SDNET-LOGINS-END" is cut out of the
# script, "/var/lib/sd-net" in it is rewritten to a scratch directory, and it is run under the script's OWN "set" and "IFS" lines (the lesson of
# 19 Oct: test-install-opengates.sh ran under "set" alone and was green while the real install, whose IFS has no space, failed) with sudo a function.
#
#   R  the four combinations of (accounts kept or deleted) x (configuration kept or deleted), each with the directory present and holding a
#      user's subdirectory and a file: only "both kept" leaves it, the other three remove all of it and say so; with the directory ABSENT every
#      combination exits 0 and prints nothing (the null case: a block that never looked passes the absent rows);
#   S  static: conf_deleted is set to no before the configuration case and to yes in the N branch alone, the block comes after that case and
#      before SD is stopped, and the markers occur once.
#
# ANCHORED ON THE WORDING: "Removed /var/lib/sd-net" appears only when the directory was removed, "Kept /var/lib/sd-net" only when it was left.
# NOT MEASURED HERE: a real DELETE cycle (the VM does that: sudo, the real directory).

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
  mutant condition-needs-both-deleted   '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/if \[ "\$keep_accts" = "DELETE" \] || \[ "\$conf_deleted" = yes \]; then/if [ "$keep_accts" = "DELETE" ] \&\& [ "$conf_deleted" = yes ]; then/'
  mutant config-deleted-ignored         '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/ || \[ "\$conf_deleted" = yes \]//'
  mutant accounts-deleted-ignored       '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/\[ "\$keep_accts" = "DELETE" \] || //'
  mutant never-removed                  '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/        sudo rm -rf \/var\/lib\/sd-net$/        true/'
  mutant always-removed                 '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/^if \[ "\$keep_accts" = "DELETE" \] || \[ "\$conf_deleted" = yes \]; then$/if true; then/'
  mutant removed-without-saying         '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/        echo "Removed \/var\/lib\/sd-net/        : "Removed \/var\/lib\/sd-net/'
  mutant kept-without-saying            '/^# SDNET-LOGINS-BEGIN/,/^# SDNET-LOGINS-END/ s/        echo "Kept \/var\/lib\/sd-net/        : "Kept \/var\/lib\/sd-net/'
  mutant n-branch-forgets-the-flag      's/^           conf_deleted=yes$/           true/'
  mutant y-branch-sets-the-flag         's/^           echo Configuration file saved;;$/           conf_deleted=yes; echo Configuration file saved;;/'
  mutant flag-never-initialised         's/^conf_deleted=no$/true/'
  mutant block-before-the-config-question 's/^# SDNET-LOGINS-BEGIN$/# SDNET-LOGINS-BEGIN-X/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$DEL" | head -2)
BLK=$(awk '/^# SDNET-LOGINS-BEGIN/{f=1;next} /^# SDNET-LOGINS-END/{f=0} f{print}' "$DEL")
echo "script    : $DEL"
echo "options   : $(printf '%s' "$OPTS" | tr '\n' ' ')"
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-delete-sdnet: CANNOT RUN - no set line in the script"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-delete-sdnet: CANNOT RUN - no IFS line in the script (the block must be run under it)"; exit 2; }
[ -z "$BLK" ] && { echo "test-delete-sdnet: CANNOT RUN - no block between SDNET-LOGINS-BEGIN and SDNET-LOGINS-END (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
NET="$T/var/lib/sd-net"
BLK_T=$(printf '%s\n' "$BLK" | sed -e "s#/var/lib/sd-net#$NET#g")
printf '%s\n' "$BLK_T" | grep -q -F "$NET" || { echo "test-delete-sdnet: CANNOT RUN - the block does not mention /var/lib/sd-net"; exit 2; }

pass=0; fail=0
row() { if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"; else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi; }
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

run_block() {   # run_block KEEP_ACCTS CONF_DELETED [present|absent]  - prints the output, then RC=n
  rm -rf "$T/var"
  if [ "${3:-present}" = present ]; then mkdir -p "$NET/don" "$NET/jane"; printf 'ClientKey\n' > "$NET/don/serverA"; printf 'ServerKey\n' > "$NET/jane/serverB"; fi
  OPTS="$OPTS" BLK_T="$BLK_T" KA="$1" CD="$2" bash -c '
      eval "$OPTS"
      keep_accts="$KA"; conf_deleted="$CD"
      sudo() { "$@"; }
      eval "$BLK_T"
      echo "RC=0"' 2>&1
}

echo "--- R: the four combinations"
OUT=$(run_block KEEP no)
row "R1 accounts KEPT, configuration KEPT: the directory is left, and the script says so" \
    "$(ok "$([ -d "$NET/don" ] && [ -f "$NET/jane/serverB" ] && printf '%s' "$OUT" | grep -q 'Kept .*stored SDNet logins' && ! printf '%s' "$OUT" | grep -q 'Removed' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
for combo in "DELETE no" "KEEP yes" "DELETE yes"; do
  set -- $combo
  OUT=$(run_block "$1" "$2")
  row "R2 accounts $1, configuration deleted=$2: ALL of it is removed (the user directories and the files), and the script says so" \
      "$(ok "$([ ! -e "$NET" ] && printf '%s' "$OUT" | grep -q 'Removed .*stored SDNet logins' && ! printf '%s' "$OUT" | grep -q 'Kept' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
done
for combo in "KEEP no" "DELETE no" "KEEP yes" "DELETE yes"; do
  set -- $combo
  OUT=$(run_block "$1" "$2" absent)
  row "R3 no directory at all, accounts $1, configuration deleted=$2: exit 0 and NOTHING printed (the null case)" \
      "$(ok "$([ "$(printf '%s' "$OUT" | grep -v '^RC=0$' | wc -c)" -eq 0 ] && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
done

echo "--- S: static"
CONF=$(awk '/^conf_deleted=no$/{f=1} f{print} /^esac$/{if(f) exit}' "$DEL")
row "S1 conf_deleted is set to no before the configuration case, and to yes in the N branch ALONE" \
    "$(ok "$([ "$(grep -c '^conf_deleted=no$' "$DEL")" -eq 1 ] && [ "$(printf '%s\n' "$CONF" | grep -c 'conf_deleted=yes')" -eq 1 ] \
        && printf '%s\n' "$CONF" | awk '/\[nN\] \)/{n=1} /\*\)/{n=0} /conf_deleted=yes/{exit !n}' && echo yes)")" "$CONF"
a=$(grep -n '^conf_deleted=no$' "$DEL" | head -1 | cut -d: -f1)
b=$(grep -n '^# SDNET-LOGINS-BEGIN$' "$DEL" | head -1 | cut -d: -f1)
s=$(grep -n 'bin/sd" -stop' "$DEL" | head -1 | cut -d: -f1)
row "S2 the block comes after the configuration case and before SD is stopped, and the two markers occur once each" \
    "$(ok "$([ -n "$a" ] && [ -n "$b" ] && [ -n "$s" ] && [ "$a" -lt "$b" ] && [ "$b" -lt "$s" ] && [ "$(grep -c '^# SDNET-LOGINS-BEGIN$' "$DEL")" -eq 1 ] && [ "$(grep -c '^# SDNET-LOGINS-END$' "$DEL")" -eq 1 ] && echo yes)")" "init $a block $b stop $s"
row "S3 'keep_accts' is the variable the accounts question sets (DELETE only on the typed word), so the block tests the same one" \
    "$(ok "$(grep -q "^keep_accts='KEEP'$" "$DEL" && [ "$(grep -c 'if \[ "\$keep_accts" = "DELETE" \]; then' "$DEL")" -ge 1 ] && echo yes)")" "keep_accts lines: $(grep -c keep_accts "$DEL")"

echo "test-delete-sdnet: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
