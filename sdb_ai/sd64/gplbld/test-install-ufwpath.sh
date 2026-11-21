#!/bin/bash
# test-install-ufwpath.sh - S.294 (22 Nov 2026): installsdcore.sh and deletesdcore.sh find ufw by `command -v ufw` OR the file /usr/sbin/ufw.  An ordinary user's
# PATH on Debian has no /usr/sbin, so `command -v` alone found nothing: with ufw ACTIVE the install opened the API to other computers, added NO rule and said "no ufw
# or firewalld found", and the uninstall never removed one (seen on a fresh Debian 13 clone, S.292's witness; Solo's fix of the same fault is S.288, 6e38165).  Text
# only, no sudo, no install.  Exit 0 every row held, 1 one did not, 2 it could not run.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-ufwpath.sh [--selftest]
#
# THE ROWS.  U1 the installer defines have_ufw as both tests; U2 its two uses of ufw in the choice of firewall go through have_ufw and no bare `command -v ufw`
# remains outside it; U3 the uninstaller's ufw step is guarded by both tests.  It cannot say a real firewall changed: that is the VM row.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THIS="$HERE/$(basename "${BASH_SOURCE[0]}")"
ROOT="$(cd "$HERE/../../.." && pwd)"
INSTALLER="${INSTALLER:-$ROOT/installsdcore.sh}"
REMOVER="${REMOVER:-$ROOT/deletesdcore.sh}"
passed=0; failed=0
row() { if [ "$2" = 0 ]; then passed=$((passed+1)); echo "  [PASS] $1"; else failed=$((failed+1)); echo "  [FAIL] $1${3:+   <- $3}"; fi; }

if [ "${1:-}" = "--selftest" ]; then
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, i|r, sed expression
    local f="$T/$1.sh" ei="$ROOT/installsdcore.sh" er="$ROOT/deletesdcore.sh" src
    if [ "$2" = i ]; then src="$ei"; else src="$er"; fi
    sed -e "$3" "$src" > "$f"
    if cmp -s "$src" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); return; fi
    if [ "$2" = i ]; then ei="$f"; else er="$f"; fi
    if INSTALLER="$ei" REMOVER="$er" bash "$THIS" > "$T/$1.out" 2>&1; then echo "  [MISSED] $1: the check still passed"; missed=$((missed+1))
    else echo "  [caught] $1"; caught=$((caught+1)); fi
  }
  echo "selftest: the real scripts first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real scripts do not pass:"; tail -6 "$T/real.out"; exit 1; }
  echo "  [ok] the real scripts pass"
  mutant have-ufw-path-only  i 's# || \[ -x /usr/sbin/ufw \]; }$#; }#'
  mutant active-bare         i 's#^if have_ufw \&\& sudo ufw status#if command -v ufw >/dev/null 2>\&1 \&\& sudo ufw status#'
  mutant installed-bare      i 's#^elif have_ufw; then fw_tool=ufw#elif command -v ufw >/dev/null 2>\&1; then fw_tool=ufw#'
  mutant remover-path-only   r 's#^if command -v ufw >/dev/null 2>&1 || \[ -x /usr/sbin/ufw \]; then#if command -v ufw >/dev/null 2>\&1; then#'
  echo "selftest: $caught caught, $missed missed"
  [ "$missed" -eq 0 ]; exit $?
fi

for f in "$INSTALLER" "$REMOVER"; do [ -r "$f" ] || { echo "test-install-ufwpath: CANNOT RUN - $f is not there"; exit 2; }; done
echo "installer : $INSTALLER"; echo "remover   : $REMOVER"
row "U1 the installer's have_ufw is 'command -v ufw' OR the file /usr/sbin/ufw" \
  "$(grep -qxF 'have_ufw() { command -v ufw >/dev/null 2>&1 || [ -x /usr/sbin/ufw ]; }' "$INSTALLER" && echo 0 || echo 1)"
row "U2 the choice of firewall asks have_ufw twice (active, then installed) and no other line asks 'command -v ufw'" \
  "$([ "$(grep -c -E '^(if|elif) have_ufw' "$INSTALLER")" = 2 ] && [ "$(grep -v '^ *#' "$INSTALLER" | grep -c 'command -v ufw')" = 1 ] && echo 0 || echo 1)" \
  "uses=$(grep -c -E '^(if|elif) have_ufw' "$INSTALLER") bare=$(grep -v '^ *#' "$INSTALLER" | grep -c 'command -v ufw')"
row "U3 the uninstaller's ufw step is guarded by 'command -v ufw' OR /usr/sbin/ufw, and nothing else asks 'command -v ufw'" \
  "$(grep -qxF 'if command -v ufw >/dev/null 2>&1 || [ -x /usr/sbin/ufw ]; then' "$REMOVER" && [ "$(grep -v '^ *#' "$REMOVER" | grep -c 'command -v ufw')" = 1 ] && echo 0 || echo 1)"
echo
echo "test-install-ufwpath: $passed passed, $failed failed"
[ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]
