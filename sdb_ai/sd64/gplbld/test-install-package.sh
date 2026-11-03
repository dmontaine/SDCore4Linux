#!/bin/bash
#
# test-install-package.sh - the installer's PACKAGE-SOURCE block: a release package is checked before any question, and a damaged or changed one stops the install (S.144; owner, 3 Nov 2026:
# "for this version the source code will be included in the installer zip so that it does not need to be downloaded during install"), and a release-candidate tag is named as a pre-release
# (owner, 3 Nov 2026: "put it in the installer, not on the login banner").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-package.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-package.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-package.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Everything happens in a scratch directory.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a refusal to pass on nothing: no block).
#
# WHAT IT RUNS.  The text between "# PACKAGE-SOURCE-BEGIN" and "# PACKAGE-SOURCE-END", under the installer's OWN "set -euo pipefail" AND ITS IFS, with installer_dir set to a package made here: a source
# folder (source/sdb_ai/sd64), the list of its files (SHA256SUMS) and source/SDCORE-RELEASE.
#
#   P1  a good package: exit 0, pkg_source is its source folder, the commit and the branch are read from SDCORE-RELEASE
#   P2  a source file changed after the list was made: exit 1, nothing set, the message says the file does not match
#   P3  a file under source/ the list does not name: exit 1;  P4  no SHA256SUMS: exit 1;  P5  SHA256SUMS a link: exit 1
#   P6  a fifo under source/: exit 1;  P7  SDCORE-RELEASE without a 40-digit commit, or with a bad branch: exit 1
#   P8  no source folder, a source folder that is a link, or no installer_dir: NOT package mode (pkg_source empty), exit 0
#   P9  a branch that ends -rcN names a pre-release (pkg_pre); main, Dev, v2.0 and v2.0-0 do not
#   S   the block comes before the first question and before the first sudo
#
# NOT MEASURED HERE, and said so: that the message is printed in a terminal in colour, and a real install from a package (the VM did one, 3 Nov 2026, d7e4c51b).

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
  B='/^# PACKAGE-SOURCE-BEGIN/,/^# PACKAGE-SOURCE-END/'
  mutant sums-not-checked        "$B s/^    elif ! (cd \"\$installer_dir\" \&\& sha256sum --quiet --strict -c SHA256SUMS .*; then\$/    elif false; then/"
  mutant unlisted-not-checked    "$B s/^    elif \[ \"\$(cd \"\$installer_dir\" \&\& find source -type f | wc -l)\" != .*; then\$/    elif false; then/"
  mutant special-not-checked     "$B s/^    elif \[ -n \"\$(cd \"\$installer_dir\" \&\& find source ! -type f ! -type d | head -1)\" \]; then\$/    elif false; then/"
  mutant no-sums-file-allowed    "$B s/^    if \[ ! -f \"\$installer_dir\/SHA256SUMS\" \] || \[ -L \"\$installer_dir\/SHA256SUMS\" \]; then\$/    if false; then/"
  mutant sums-link-followed      "$B s/ || \[ -L \"\$installer_dir\/SHA256SUMS\" \]//"
  mutant source-link-followed    "$B s/ \&\& \[ ! -L \"\$installer_dir\/source\" \]//"
  mutant release-file-unread     "$B s/^        if \[ -z \"\$pkg_commit\" \] || \[ -z \"\$pkg_branch\" \]; then pkg_bad=/        if false; then pkg_bad=/"
  mutant any-commit-accepted     "$B s/\\\\{40\\\\}/\\\\{1,\\\\}/"
  mutant any-branch-accepted     "$B s/\\[A-Za-z0-9._-\\]\\\\{1,40\\\\}/[^ ]*/"
  mutant refusal-continues       "$B s/^        exit 1\$/        true/"
  mutant rc-not-named            "$B s/\\*-rc\\[0-9\\]\\*)/*-zz[0-9]*)/"
  mutant everything-is-rc        "$B s/\\*-rc\\[0-9\\]\\*)/*)/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

# THE INSTALLER'S OWN set AND IFS.
OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
BLOCK=$(awk '/^# PACKAGE-SOURCE-BEGIN/{f=1;next} /^# PACKAGE-SOURCE-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-package: CANNOT RUN - no set line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-package: CANNOT RUN - no IFS line in the installer (the block must be run under it)"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-package: CANNOT RUN - no block between PACKAGE-SOURCE-BEGIN and PACKAGE-SOURCE-END (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

COMMIT=0123456789abcdef0123456789abcdef01234567

mkpkg() {   # mkpkg DIR [BRANCH]  - a good package; prints nothing
  local d="$1" br="${2:-Dev}"
  rm -rf "$d"; mkdir -p "$d/source/sdb_ai/sd64/gplsrc" "$d/source/docs/User/markdown"
  printf 'int main(void){return 0;}\n' > "$d/source/sdb_ai/sd64/gplsrc/main.c"
  printf '# a page\n' > "$d/source/docs/User/markdown/01.md"
  printf 'commit=%s\nbranch=%s\nversion=L2.0-0\n' "$COMMIT" "$br" > "$d/source/SDCORE-RELEASE"
  ( cd "$d" && find source -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS )
}

run() {   # run DIR - the block under the installer's set and IFS; prints its output, then SRC=... COMMIT=... BRANCH=... PRE=..., then RC=n
  local d="$1"
  OPTS="$OPTS" BLOCK="$BLOCK" bash -c '
      eval "$OPTS"; RED=; NC=
      installer_dir="$1"
      eval "$BLOCK"
      echo "SRC=$pkg_source COMMIT=$pkg_commit BRANCH=$pkg_branch PRE=$pkg_pre"' _ "$d" 2>&1
  echo "RC=$?"
}
rc_of() { printf '%s\n' "$1" | sed -n 's/^RC=//p' | tail -1; }
field() { printf '%s\n' "$1" | sed -n "s/^SRC=.*$2=\\([^ ]*\\).*/\\1/p" | tail -1; }

echo "--- P: the package"
P="$T/pkg"
mkpkg "$P" Dev
OUT=$(run "$P")
row "P1 a good package: exit 0, pkg_source is its source folder, the commit and the branch are read from SDCORE-RELEASE" \
    "$(ok "$([ "$(rc_of "$OUT")" = 0 ] && printf '%s' "$OUT" | grep -q "^SRC=$P/source COMMIT=$COMMIT BRANCH=Dev PRE=\$" && echo yes)")" "$OUT"

mkpkg "$P" Dev; printf '/* changed */\n' >> "$P/source/sdb_ai/sd64/gplsrc/main.c"
OUT=$(run "$P")
row "P2 a source file changed after the list was made: exit 1, the message says a file does not match, and nothing was set" \
    "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'does not match SHA256SUMS' && ! printf '%s' "$OUT" | grep -q '^SRC=' && echo yes)")" "$OUT"

mkpkg "$P" Dev; printf 'x\n' > "$P/source/unlisted-file"
OUT=$(run "$P")
row "P3 a file under source/ the list does not name: exit 1, the message says the list does not name it" \
    "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'SHA256SUMS does not list' && echo yes)")" "$OUT"

mkpkg "$P" Dev; rm -f "$P/SHA256SUMS"
OUT=$(run "$P")
row "P4 no SHA256SUMS: exit 1, the message says there is none" "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'no SHA256SUMS' && echo yes)")" "$OUT"

mkpkg "$P" Dev; mv "$P/SHA256SUMS" "$T/real-sums"; ln -s "$T/real-sums" "$P/SHA256SUMS"
OUT=$(run "$P")
row "P5 SHA256SUMS a link: exit 1" "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'no SHA256SUMS' && echo yes)")" "$OUT"

mkpkg "$P" Dev; mkfifo "$P/source/a-fifo"
OUT=$(run "$P")
row "P6 a fifo under source/: exit 1, the message says it is neither a file nor a directory" \
    "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'neither a file nor a directory' && echo yes)")" "$OUT"

mkpkg "$P" Dev; printf 'commit=abc123\nbranch=Dev\n' > "$P/source/SDCORE-RELEASE"; ( cd "$P" && find source -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS )
OUT=$(run "$P")
row "P7a SDCORE-RELEASE with a commit that is not 40 hex digits: exit 1, it does not name a commit and a branch" \
    "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'does not name a commit and a branch' && echo yes)")" "$OUT"
mkpkg "$P" 'bad;branch'
OUT=$(run "$P")
row "P7b ...a branch with a semicolon (no blank): exit 1 as well" "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'does not name a commit and a branch' && echo yes)")" "$OUT"
mkpkg "$P" 'bad branch'
OUT=$(run "$P")
row "P7c ...a branch with a blank: exit 1 as well" "$(ok "$([ "$(rc_of "$OUT")" = 1 ] && printf '%s' "$OUT" | grep -q 'does not name a commit and a branch' && echo yes)")" "$OUT"

echo "--- P8: not package mode"
mkpkg "$P" Dev; rm -rf "$P/source"
OUT=$(run "$P")
row "P8a no source folder: not package mode (pkg_source empty), exit 0" "$(ok "$([ "$(rc_of "$OUT")" = 0 ] && printf '%s' "$OUT" | grep -q '^SRC= COMMIT= BRANCH= PRE=$' && echo yes)")" "$OUT"
mkpkg "$P" Dev; mv "$P/source" "$T/real-source"; ln -s "$T/real-source" "$P/source"
OUT=$(run "$P")
row "P8b a source folder that is a link: not package mode, exit 0 (the package is not trusted through a link)" "$(ok "$([ "$(rc_of "$OUT")" = 0 ] && printf '%s' "$OUT" | grep -q '^SRC= COMMIT= BRANCH= PRE=$' && echo yes)")" "$OUT"
OUT=$(run "")
row "P8c no installer_dir (the script was not run from a file): not package mode, exit 0" "$(ok "$([ "$(rc_of "$OUT")" = 0 ] && printf '%s' "$OUT" | grep -q '^SRC= COMMIT= BRANCH= PRE=$' && echo yes)")" "$OUT"

echo "--- P9: a release candidate is named"
for br in v2.0-rc1 v2.0-rc12; do
  mkpkg "$P" "$br"; OUT=$(run "$P")
  row "P9 the branch $br names a pre-release (PRE=$br)" "$(ok "$([ "$(rc_of "$OUT")" = 0 ] && printf '%s' "$OUT" | grep -q "PRE=$br\$" && echo yes)")" "$OUT"
done
for br in main Dev v2.0 v2.0-0 rc1 v2.0-release; do
  mkpkg "$P" "$br"; OUT=$(run "$P")
  row "P9 the branch $br is not a pre-release (PRE empty)" "$(ok "$([ "$(rc_of "$OUT")" = 0 ] && printf '%s' "$OUT" | grep -q "BRANCH=$br PRE=\$" && echo yes)")" "$OUT"
done

echo "--- S: the places"
ln_end=$(grep -n '^# PACKAGE-SOURCE-END' "$INST" | head -1 | cut -d: -f1)
ln_q=$(grep -n '^[[:space:]]*read -r -p' "$INST" | head -1 | cut -d: -f1)
ln_sudo=$(grep -n '^sudo ' "$INST" | head -1 | cut -d: -f1)             # the first sudo of the main flow (column 0): the ones further in are inside functions, which are not run here
row "S1 the block comes before the first question (line $ln_q) and the first sudo (line $ln_sudo)" "$(ok "$([ "${ln_end:-0}" -gt 0 ] && [ "$ln_end" -lt "${ln_q:-0}" ] && [ "$ln_end" -lt "${ln_sudo:-0}" ] && echo yes)")" "block ends $ln_end"
row "S2 the installer says so at the start and at the end when the package is a pre-release" \
    "$(ok "$(grep -q 'This package is the pre-release ${pkg_pre}, for testing' "$INST" && grep -q 'Pre-release ${pkg_pre}, commit' "$INST" && echo yes)")" ""

echo
echo "test-install-package: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
