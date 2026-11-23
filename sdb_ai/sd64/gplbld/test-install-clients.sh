#!/bin/bash
#
# test-install-clients.sh - the installer's block that puts the clean-room client library from the release package into bin (S.262, 19 Nov 2026:
# the source builds no client library any more; the one SD ships is the clean-room one, binaries only, in the package's clients folder).
#
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-clients.sh
#   bash /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-clients.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-clients.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd.  Everything happens in a scratch directory.  Exit 0 every row passed, 1 a row failed,
# 2 it could not run (a refusal to pass on nothing: no block, no set line).
#
# WHAT IT RUNS.  The text between "# CLIENTS-BEGIN" and "# CLIENTS-END", under the installer's OWN "set -euo pipefail" and IFS, with sudo a function that
# logs each call and does an "install" with a cp (the real one would need root), and ldd a function that answers with the libssl the row names.
#
#   K1  OpenSSL 3: both files of clients/Linux64 are installed -o root -g root -m 755 into bin, their content equal; the success line counts 2
#   K2  OpenSSL 4: the files come from clients/Linux64-openssl4, not clients/Linux64
#   K3  no clients folder beside the installer, and no installer directory (not run from a file): nothing installed, said so, exit 0
#   K4  a clients folder with no build for this OpenSSL: nothing installed, said so, exit 0
#   K5  a file that is a symbolic link is left alone
#   K6  a failed install prints a WARNING and the block still ends 0
#   S   static: the block comes after ROOTBIN-EARLY-END (bin is root's) and before ROOTBIN-BEGIN (which seals bin); it has no exit
#
# NOT MEASURED HERE, and said so: that root really owns the files and that a release package really holds them (a real install from a package).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

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
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  B='/^# CLIENTS-BEGIN/,/^# CLIENTS-END/'
  mutant wrong-owner        "$B s/-o root -g root -m 755/-o sdsys -g sdusers -m 755/"
  mutant group-writable     "$B s/-m 755/-m 775/"
  mutant follows-links      "$B s/ \&\& \[ ! -L \"\$clients_src\/\$clients_f\" \]//"
  mutant ignores-openssl    "$B s/if \[ \"\$clients_ssl\" = \"4\" \]; then/if false; then/"
  mutant failure-aborts     "$B s/^        if sudo install -o root -g root -m 755 \"\$clients_src\/\$clients_f\" \"\$sdsysdir\/bin\/\$clients_f\"; then/        sudo install -o root -g root -m 755 \"\$clients_src\/\$clients_f\" \"\$sdsysdir\/bin\/\$clients_f\"; if true; then/"
  mutant counts-nothing     "$B s/clients_installed=\$((clients_installed+1))/:/"
  # (Taking out the test of an empty installer_dir is not a mutant this can catch: with it empty the folder test looks at /clients, which a
  #  machine does not have, so the block does the same either way.  K3's second row holds the outcome.)
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
BLOCK=$(awk '/^# CLIENTS-BEGIN/{f=1;next} /^# CLIENTS-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-clients: CANNOT RUN - no IFS line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-clients: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-clients: CANNOT RUN - no block between CLIENTS-BEGIN and CLIENTS-END (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# run_block PKGDIR(or -) SSL [FAIL]   - prints the block's output, then RC=n; the sudo log is $T/sudo.log, the bin is $T/sys/bin
run_block() {
  local pkg="$1" ssl="$2" failinst="${3:-}"
  rm -rf "$T/sys"; mkdir -p "$T/sys/bin"; : > "$T/sys/bin/sd"
  : > "$T/sudo.log"
  local instdir="$pkg"; [ "$pkg" = - ] && instdir=""
  {
    printf '%s\n' "$OPTS"
    echo "RED=''; NC=''"
    echo "installer_dir='$instdir'; sdsysdir='$T/sys'"
    echo "FAILINSTALL='$failinst'; SSLV='$ssl'"
    cat <<'EOS'
ldd() { printf '\tlibssl.so.%s => /usr/lib/x86_64-linux-gnu/libssl.so.%s (0x0)\n' "$SSLV" "$SSLV"; }
sudo() {
  { printf 'sudo'; printf ' %s' "$@"; echo; } >> "$LOGF"   # not "$*": the installer's IFS is a newline
  if [ "$1" = install ]; then
    [ -n "$FAILINSTALL" ] && return 1
    shift
    while [ "${1:-}" = -o ] || [ "${1:-}" = -g ] || [ "${1:-}" = -m ]; do shift 2; done
    cp "$1" "$2"; return
  fi
  return 0
}
EOS
    printf '%s\n' "$BLOCK"
    echo "echo END-OF-BLOCK"
  } > "$T/run.sh"
  LOGF="$T/sudo.log" bash "$T/run.sh" 2>&1; echo "RC=$?"
}
mkpkg() {   # mkpkg dir: clients/Linux64 and clients/Linux64-openssl4, each with both names, contents saying which
  rm -rf "$1"; mkdir -p "$1/clients/Linux64" "$1/clients/Linux64-openssl4"
  for n in sdclilib.so libsdcli.so; do echo "ssl3 $n" > "$1/clients/Linux64/$n"; echo "ssl4 $n" > "$1/clients/Linux64-openssl4/$n"; done
}

# ---- K1 -----------------------------------------------------------------------------------------------------------------
mkpkg "$T/pkg"
out=$(run_block "$T/pkg" 3)
row "K1 OpenSSL 3: both names installed"            "$(ok "$([ -f "$T/sys/bin/sdclilib.so" ] && [ -f "$T/sys/bin/libsdcli.so" ] && echo yes)")" "bin: $(ls "$T/sys/bin")"
row "K1 ... from clients/Linux64, content equal"     "$(ok "$(grep -q '^ssl3 sdclilib.so$' "$T/sys/bin/sdclilib.so" && grep -q '^ssl3 libsdcli.so$' "$T/sys/bin/libsdcli.so" && echo yes)")" "$(cat "$T/sys/bin/sdclilib.so" 2>/dev/null)"
row "K1 ... -o root -g root -m 755, twice"           "$(ok "$([ "$(grep -c -- 'install -o root -g root -m 755' "$T/sudo.log")" = 2 ] && echo yes)")" "$(grep install "$T/sudo.log" | head -2)"
row "K1 ... the success line counts 2, OpenSSL 3"    "$(ok "$(printf '%s' "$out" | grep -q 'Installed the client library (2 files, OpenSSL 3)' && echo yes)")" "$out"
row "K1 ... the block ends 0"                        "$(ok "$(printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- K2 -----------------------------------------------------------------------------------------------------------------
out=$(run_block "$T/pkg" 4)
row "K2 OpenSSL 4: from clients/Linux64-openssl4"    "$(ok "$(grep -q '^ssl4 sdclilib.so$' "$T/sys/bin/sdclilib.so" && grep -q '^ssl4 libsdcli.so$' "$T/sys/bin/libsdcli.so" && echo yes)")" "$(cat "$T/sys/bin/sdclilib.so" 2>/dev/null) | $out"
# ---- K3 -----------------------------------------------------------------------------------------------------------------
rm -rf "$T/bare"; mkdir "$T/bare"
out=$(run_block "$T/bare" 3)
row "K3 no clients folder: nothing installed, said so, exit 0" "$(ok "$(! grep -q 'install ' "$T/sudo.log" && printf '%s' "$out" | grep -q 'not run from a release package' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
out=$(run_block - 3)
row "K3 no installer directory: nothing looked for"  "$(ok "$(! grep -q 'install ' "$T/sudo.log" && printf '%s' "$out" | grep -q 'not run from a release package' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- K4 -----------------------------------------------------------------------------------------------------------------
rm -rf "$T/only4"; mkdir -p "$T/only4/clients/Linux64-openssl4"; echo x > "$T/only4/clients/Linux64-openssl4/sdclilib.so"
out=$(run_block "$T/only4" 3)
row "K4 no build for this OpenSSL: nothing installed, said so, exit 0" "$(ok "$(! grep -q 'install ' "$T/sudo.log" && printf '%s' "$out" | grep -q "No client library for this system's OpenSSL" && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- K5 -----------------------------------------------------------------------------------------------------------------
rm -rf "$T/lnk"; mkdir -p "$T/lnk/clients/Linux64"; echo target > "$T/lnk/real.so"; ln -s ../../real.so "$T/lnk/clients/Linux64/sdclilib.so"
echo "ssl3 libsdcli.so" > "$T/lnk/clients/Linux64/libsdcli.so"
out=$(run_block "$T/lnk" 3)
row "K5 a link is left alone, the plain file is installed" "$(ok "$([ ! -e "$T/sys/bin/sdclilib.so" ] && [ -f "$T/sys/bin/libsdcli.so" ] && echo yes)")" "bin: $(ls "$T/sys/bin") | $out"
# ---- K6 -----------------------------------------------------------------------------------------------------------------
out=$(run_block "$T/pkg" 3 fail)
row "K6 failed install: WARNING, the block ends 0"   "$(ok "$(printf '%s' "$out" | grep -q 'WARNING: the client library sdclilib.so was not installed' && printf '%s' "$out" | grep -q 'END-OF-BLOCK' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- S ------------------------------------------------------------------------------------------------------------------
l_early=$(grep -n '^# ROOTBIN-EARLY-END' "$INST" | cut -d: -f1); l_beg=$(grep -n '^# CLIENTS-BEGIN' "$INST" | cut -d: -f1)
l_seal=$(grep -n '^# ROOTBIN-BEGIN' "$INST" | cut -d: -f1)
row "S the block follows ROOTBIN-EARLY and precedes ROOTBIN" "$(ok "$([ -n "$l_early" ] && [ -n "$l_beg" ] && [ -n "$l_seal" ] && [ "$l_early" -lt "$l_beg" ] && [ "$l_beg" -lt "$l_seal" ] && echo yes)")" "lines $l_early $l_beg $l_seal"
row "S the block has no exit"                         "$(ok "$(printf '%s\n' "$BLOCK" | grep -q -E '(^|[^a-z_])exit( |$)' && echo no || echo yes)")" "an exit is in the block"

echo "test-install-clients: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
