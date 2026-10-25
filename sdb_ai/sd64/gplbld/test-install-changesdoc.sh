#!/bin/bash
#
# test-install-changesdoc.sh - the installer's block that copies the changes document into the shared account (owner, 24 Oct 2026: "included with the
# installer as an additional document and upon installation also copied into the 'shared' directory").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-changesdoc.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-changesdoc.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-changesdoc.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd.  Everything happens in a scratch directory.  Exit 0 every row passed, 1 a row failed,
# 2 it could not run (a refusal to pass on nothing: no block, no set line).
#
# WHAT IT RUNS.  The text between "# CHANGES-DOC-BEGIN" and "# CHANGES-DOC-END", under the installer's OWN "set -euo pipefail" and IFS (a block tested
# under another IFS once failed on the first real install), with sudo a function that logs each call, runs "test" for real and does an "install" with a
# cp (the real one would need root and the user sdsys).  installer_dir, shared_reg and shared_dir are set to scratch paths, as the installer sets them.
#
#   C1  three files beside the installer (pdf, html, md of a lower case name) are installed with -o sdsys -g sdusers -m 644 into the shared pdf
#       directory, their content equal, and the success line counts them
#   C2  no file beside the installer: nothing installed, "No changes document beside the installer", exit 0
#   C3  a symbolic link of the right name is left alone;  C4  a name with a capital, a space or other pdf files is left alone
#   C5  installer_dir empty (not run from a file): nothing is looked for;  C6  no shared account;  C7  no pdf directory
#   C8  a failed install prints a WARNING, the block still ends 0, and the count line says it could not be copied
#   S   static: the block comes after SHARED-CONTENT-END and before the VOC walk; installer_dir comes from BASH_SOURCE and only when that is a file;
#       the block has no exit
#
# NOT MEASURED HERE, and said so: that chown sdsys:sdusers works and that a release package really holds the three files (a real install from a package).

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
  B='/^# CHANGES-DOC-BEGIN/,/^# CHANGES-DOC-END/'
  mutant wrong-owner          "$B s/-o sdsys -g sdusers -m 644/-o root -g root -m 644/"
  mutant group-writable       "$B s/-m 644/-m 664/"
  mutant world-writable       "$B s/-m 644/-m 666/"
  mutant follows-links        "$B s/ \&\& \[ ! -L \"\$changes_f\" \]//"
  mutant any-name             "$B{/changes_b\" =~ /d}"
  mutant any-pdf              "$B s#sd-core-for-linux-\*-changes.pdf#*.pdf#"
  mutant without-installer-dir "$B s/^if \[ -n \"\$installer_dir\" \] \&\& /if /"
  mutant without-shared       "$B s/ \&\& sudo test -f \"\$shared_reg\"//"
  mutant without-pdf-dir      "$B s/ \&\& sudo test -d \"\${shared_dir}\/pdf\"//"
  mutant failure-aborts       "$B s/^        if sudo install -o sdsys -g sdusers -m 644 \"\$changes_f\" \"\${shared_dir}\/pdf\/\${changes_b}\"; then/        sudo install -o sdsys -g sdusers -m 644 \"\$changes_f\" \"\${shared_dir}\/pdf\/\${changes_b}\"; if true; then/"
  mutant counts-nothing       "$B s/changes_copied=\$((changes_copied+1))/:/"
  mutant installer-dir-from-cwd 's/^if \[ -f "\${BASH_SOURCE\[0\]:-}" \]; then installer_dir=.*$/installer_dir=$(pwd)/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
BLOCK=$(awk '/^# CHANGES-DOC-BEGIN/{f=1;next} /^# CHANGES-DOC-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-changesdoc: CANNOT RUN - no IFS line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-changesdoc: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-changesdoc: CANNOT RUN - no block between CHANGES-DOC-BEGIN and CHANGES-DOC-END (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# run_block PKGDIR(or -) REG(yes|no) PDFDIR(yes|no) [FAIL]   - prints the block's output, then RC=n; the sudo log is $T/sudo.log
run_block() {
  local pkg="$1" reg="$2" pdfd="$3" failinst="${4:-}"
  rm -rf "$T/shared" "$T/reg"; mkdir -p "$T/shared"
  [ "$pdfd" = yes ] && mkdir -p "$T/shared/pdf"
  [ "$reg" = yes ] && : > "$T/reg"
  : > "$T/sudo.log"
  local instdir="$pkg"; [ "$pkg" = - ] && instdir=""
  {
    printf '%s\n' "$OPTS"
    echo "RED=''; NC=''"
    echo "installer_dir='$instdir'; shared_reg='$T/reg'; shared_dir='$T/shared'"
    echo "FAILINSTALL='$failinst'"
    cat <<'EOS'
sudo() {
  { printf 'sudo'; printf ' %s' "$@"; echo; } >> "$LOGF"   # not "$*": the installer's IFS is a newline
  if [ "$1" = test ]; then shift; test "$@"; return; fi
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
mkpkg() {   # mkpkg dir: the three files of a good name and some that must be left alone
  rm -rf "$1"; mkdir -p "$1"
  for e in pdf html md; do echo "doc $e" > "$1/sd-core-for-linux-l1.2-0-changes.$e"; done
}

# ---- C1 -----------------------------------------------------------------------------------------------------------------
mkpkg "$T/pkg"
out=$(run_block "$T/pkg" yes yes)
n=$(ls "$T/shared/pdf" 2>/dev/null | wc -l)
row "C1 three files copied"                       "$(ok "$([ "$n" = 3 ] && echo yes)")" "found $n files in the pdf directory"
row "C1 content equal"                            "$(ok "$(cmp -s "$T/pkg/sd-core-for-linux-l1.2-0-changes.pdf" "$T/shared/pdf/sd-core-for-linux-l1.2-0-changes.pdf" && echo yes)")" "pdf differs"
row "C1 installed owner sdsys group sdusers 644"  "$(ok "$([ "$(grep -c -- 'install -o sdsys -g sdusers -m 644' "$T/sudo.log")" = 3 ] && echo yes)")" "$(grep install "$T/sudo.log" | head -2)"
row "C1 success line counts three"                "$(ok "$(printf '%s' "$out" | grep -q 'Copied the changes document (3 files)' && echo yes)")" "$out"
row "C1 the block ends 0"                         "$(ok "$(printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- C2 -----------------------------------------------------------------------------------------------------------------
rm -rf "$T/empty"; mkdir "$T/empty"
out=$(run_block "$T/empty" yes yes)
row "C2 none beside: nothing installed"           "$(ok "$([ "$(ls "$T/shared/pdf" | wc -l)" = 0 ] && ! grep -q 'install ' "$T/sudo.log" && echo yes)")" "files: $(ls "$T/shared/pdf")"
row "C2 none beside: said so, exit 0"             "$(ok "$(printf '%s' "$out" | grep -q 'No changes document beside the installer' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- C3, C4 -------------------------------------------------------------------------------------------------------------
rm -rf "$T/odd"; mkdir "$T/odd"; echo target > "$T/odd/real.txt"
ln -s real.txt "$T/odd/sd-core-for-linux-l9-changes.pdf"
echo x > "$T/odd/sd-core-for-linux-L1.2-0-changes.pdf"
echo x > "$T/odd/sd-core-for-linux-l1 2-changes.html"
echo x > "$T/odd/readme.pdf"
echo x > "$T/odd/other-changes.pdf"
out=$(run_block "$T/odd" yes yes)
row "C3 a link is left alone"                     "$(ok "$([ ! -e "$T/shared/pdf/sd-core-for-linux-l9-changes.pdf" ] && echo yes)")" "copied"
row "C4 capital, space and other pdfs left alone" "$(ok "$([ "$(ls "$T/shared/pdf" | wc -l)" = 0 ] && echo yes)")" "copied: $(ls "$T/shared/pdf")"
# ---- C5, C6, C7 ---------------------------------------------------------------------------------------------------------
out=$(run_block - yes yes)
row "C5 no installer directory: nothing looked for" "$(ok "$(! grep -q 'install ' "$T/sudo.log" && printf '%s' "$out" | grep -q 'No changes document was copied' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
mkpkg "$T/pkg"
out=$(run_block "$T/pkg" no yes)
row "C6 no shared account: nothing copied"        "$(ok "$([ "$(ls "$T/shared/pdf" | wc -l)" = 0 ] && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
out=$(run_block "$T/pkg" yes no)
row "C7 no pdf directory: nothing copied"         "$(ok "$(! grep -q 'install ' "$T/sudo.log" && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- C8 -----------------------------------------------------------------------------------------------------------------
out=$(run_block "$T/pkg" yes yes fail)
row "C8 failed install: WARNING"                  "$(ok "$(printf '%s' "$out" | grep -q 'WARNING: sd-core-for-linux-l1.2-0-changes' && echo yes)")" "$out"
row "C8 failed install: could not be copied, exit 0" "$(ok "$(printf '%s' "$out" | grep -q 'could not be copied' && printf '%s' "$out" | grep -q 'END-OF-BLOCK' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- S ------------------------------------------------------------------------------------------------------------------
l_end=$(grep -n '^# SHARED-CONTENT-END' "$INST" | cut -d: -f1); l_beg=$(grep -n '^# CHANGES-DOC-BEGIN' "$INST" | cut -d: -f1)
l_voc=$(grep -n 'AN UPGRADE BRINGS EVERY ACCOUNT' "$INST" | head -1 | cut -d: -f1)
row "S the block follows the shared content, precedes the VOC walk" "$(ok "$([ -n "$l_end" ] && [ -n "$l_beg" ] && [ -n "$l_voc" ] && [ "$l_end" -lt "$l_beg" ] && [ "$l_beg" -lt "$l_voc" ] && echo yes)")" "lines $l_end $l_beg $l_voc"
row "S installer_dir from BASH_SOURCE, only when it is a file" "$(ok "$(grep -q '^if \[ -f "\${BASH_SOURCE\[0\]:-}" \]; then installer_dir=' "$INST" && echo yes)")" "line not found"
row "S the block has no exit"                     "$(ok "$(printf '%s\n' "$BLOCK" | grep -q -E '(^|[^a-z_])exit( |$)' && echo no || echo yes)")" "an exit is in the block"

echo "test-install-changesdoc: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
