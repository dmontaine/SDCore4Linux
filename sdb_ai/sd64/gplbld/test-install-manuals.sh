#!/bin/bash
#
# test-install-manuals.sh - the installer's block that puts the documentation PDFs of a release package into the shared account (S.143; owner,
# 3 Nov 2026: "Yes, installer copies them").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-manuals.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-manuals.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-manuals.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd.  Everything happens in a scratch directory.  Exit 0 every row passed, 1 a row failed,
# 2 it could not run (no block, no set or IFS line).
#
# WHAT IT RUNS.  The text between "# MANUALS-PDF-BEGIN" and "# MANUALS-PDF-END", under the installer's OWN "set -euo pipefail" and IFS, with sudo a
# function that logs each call, runs "test" and "cmp" for real, skips "find" (the chown needs root), and plays docs.install for "bin/sd -internal
# docs.install DIR": it copies each *.pdf of DIR whose name is lower case letters, digits and . _ - and whose contents begin %PDF-, as the verb does.
#
#   M1  a pdf folder of three good PDFs: docs.install is asked for exactly that folder, the copies are made, the chown is asked, the line counts 3
#   M2  one of three has a capital in its name: the verb skips it, the block says WARNING 2 of 3 and the command to run
#   M3  no pdf folder: nothing is asked, the note says so;  M4  the pdf folder is a link: the same;  M5  installer_dir empty: the same
#   M6  no shared account: docs.install is not asked;  M7  docs.install copies nothing: WARNING 0 of 2, the block still ends 0
#   S   the block follows CHANGES-DOC-END and precedes the VOC walk; it copies only through docs.install (no cp or install); it has no exit
#
# NOT MEASURED HERE, and said so: the real docs.install (sandbox-docs.py runs it), the chown, and a real install from a package (the VM).

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
  B='/^# MANUALS-PDF-BEGIN/,/^# MANUALS-PDF-END/'
  mutant follows-link        "$B s/ \&\& \[ ! -L \"\$installer_dir\/pdf\" \]//"
  mutant without-shared      "$B s/^elif sudo test -f \"\$shared_reg\" \&\& /elif /"
  mutant no-chown            "$B{/-exec chown sdsys:sdusers/d}"
  mutant judged-by-nothing   "$B s/manuals_ok=\$((manuals_ok+1))/manuals_ok=\$manuals_n/"
  mutant failure-aborts      "$B s/docs.install \"\$installer_dir\/pdf\" < \/dev\/null || true/docs.install \"\$installer_dir\/pdf\" < \/dev\/null; [ \"\$(ls \"\${shared_dir}\/pdf\" | wc -l)\" -gt 0 ] || exit 3/"
  mutant wrong-folder        "$B s/docs.install \"\$installer_dir\/pdf\"/docs.install \"\$installer_dir\"/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
BLOCK=$(awk '/^# MANUALS-PDF-BEGIN/{f=1;next} /^# MANUALS-PDF-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-manuals: CANNOT RUN - no IFS line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-manuals: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-manuals: CANNOT RUN - no block between MANUALS-PDF-BEGIN and MANUALS-PDF-END (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# run_block PKGDIR(or -) REG(yes|no) [FAILDOCS]   - prints the block's output, then RC=n; the sudo log is $T/sudo.log
run_block() {
  local pkg="$1" reg="$2" faildocs="${3:-}"
  rm -rf "$T/shared" "$T/reg"; mkdir -p "$T/shared/pdf"
  [ "$reg" = yes ] && : > "$T/reg"
  : > "$T/sudo.log"
  local instdir="$pkg"; [ "$pkg" = - ] && instdir=""
  {
    printf '%s\n' "$OPTS"
    echo "RED=''; NC=''"
    echo "installer_dir='$instdir'; shared_reg='$T/reg'; shared_dir='$T/shared'"
    echo "FAILDOCS='$faildocs'"
    cat <<'EOS'
sudo() {
  { printf 'sudo'; printf ' %s' "$@"; echo; } >> "$LOGF"   # not "$*": the installer's IFS is a newline
  case "$1" in
    test) shift; test "$@"; return ;;
    cmp)  shift; cmp "$@"; return ;;
    find) return 0 ;;
    bin/sd)
      [ "$2" = -internal ] && [ "$3" = docs.install ] || return 1
      [ -n "$FAILDOCS" ] && return 0
      local f b
      for f in "$4"/*.pdf; do
        [ -f "$f" ] || continue
        b=$(basename "$f")
        [[ "$b" =~ ^[a-z0-9][a-z0-9._-]*\.pdf$ ]] || { echo "  $b skipped: the name is not lower case letters, digits and . _ -"; continue; }
        [ "$(head -c 5 "$f")" = "%PDF-" ] || { echo "  $b skipped: it does not start with %PDF-"; continue; }
        cp "$f" "$SHARED_PDF/$b"
      done
      return 0 ;;
  esac
  return 0
}
EOS
    echo "SHARED_PDF='$T/shared/pdf'"
    printf '%s\n' "$BLOCK"
    echo "echo END-OF-BLOCK"
  } > "$T/run.sh"
  LOGF="$T/sudo.log" bash "$T/run.sh" 2>&1; echo "RC=$?"
}
mkpkg() {   # mkpkg dir name...: a package with a pdf folder holding the named PDFs
  local d="$1"; shift
  rm -rf "$d"; mkdir -p "$d/pdf"
  for n in "$@"; do printf '%%PDF-1.4 %s\n' "$n" > "$d/pdf/$n"; done
}

# ---- M1 -----------------------------------------------------------------------------------------------------------------
mkpkg "$T/pkg" 01-accounts-and-security.pdf 02-sessions-and-locks.pdf 29-sd-tcl-the-terminal-and-the-session.pdf
out=$(run_block "$T/pkg" yes)
row "M1 docs.install is asked for the package's pdf folder" "$(ok "$(grep -q -x "sudo bin/sd -internal docs.install $T/pkg/pdf" "$T/sudo.log" && echo yes)")" "$(cat "$T/sudo.log")"
row "M1 the three PDFs are in the shared folder"            "$(ok "$([ "$(ls "$T/shared/pdf" | wc -l)" = 3 ] && echo yes)")" "found: $(ls "$T/shared/pdf")"
row "M1 the copies are given to sdsys:sdusers"              "$(ok "$(grep -q 'sudo find .* -user root -exec chown sdsys:sdusers' "$T/sudo.log" && echo yes)")" "no chown asked"
row "M1 the line counts three, the block ends 0"            "$(ok "$(printf '%s' "$out" | grep -q 'Installed the documentation PDFs (3)' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- M2 -----------------------------------------------------------------------------------------------------------------
mkpkg "$T/pkg" 01-accounts-and-security.pdf 02-sessions-and-locks.pdf Admin-Guide.pdf
out=$(run_block "$T/pkg" yes)
row "M2 a capital in a name: WARNING 2 of 3 and the command" "$(ok "$(printf '%s' "$out" | grep -q 'WARNING: 2 of 3 documentation PDFs were installed' && printf '%s' "$out" | grep -q "docs.install $T/pkg/pdf" && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- M3, M4, M5 ---------------------------------------------------------------------------------------------------------
rm -rf "$T/nopdf"; mkdir "$T/nopdf"
out=$(run_block "$T/nopdf" yes)
row "M3 no pdf folder: nothing asked, a note"               "$(ok "$(! grep -q docs.install "$T/sudo.log" && printf '%s' "$out" | grep -q 'No documentation PDFs beside the installer' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
mkpkg "$T/real" 01-accounts-and-security.pdf
rm -rf "$T/lnk"; mkdir "$T/lnk"; ln -s "$T/real/pdf" "$T/lnk/pdf"
out=$(run_block "$T/lnk" yes)
row "M4 a pdf folder that is a link is not used"            "$(ok "$(! grep -q docs.install "$T/sudo.log" && [ "$(ls "$T/shared/pdf" | wc -l)" = 0 ] && echo yes)")" "$out"
out=$(run_block - yes)
row "M5 no installer directory: nothing asked"              "$(ok "$(! grep -q docs.install "$T/sudo.log" && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- M6, M7 -------------------------------------------------------------------------------------------------------------
mkpkg "$T/pkg" 01-accounts-and-security.pdf 02-sessions-and-locks.pdf
out=$(run_block "$T/pkg" no)
row "M6 no shared account: docs.install not asked, a note"  "$(ok "$(! grep -q docs.install "$T/sudo.log" && printf '%s' "$out" | grep -q 'were not installed: there is no shared account' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
out=$(run_block "$T/pkg" yes fail)
row "M7 docs.install copies nothing: WARNING 0 of 2, ends 0" "$(ok "$(printf '%s' "$out" | grep -q 'WARNING: 0 of 2 documentation PDFs' && printf '%s' "$out" | grep -q 'END-OF-BLOCK' && printf '%s' "$out" | grep -q '^RC=0$' && echo yes)")" "$out"
# ---- S ------------------------------------------------------------------------------------------------------------------
l_chg=$(grep -n '^# CHANGES-DOC-END' "$INST" | cut -d: -f1); l_beg=$(grep -n '^# MANUALS-PDF-BEGIN' "$INST" | cut -d: -f1)
l_voc=$(grep -n 'AN UPGRADE BRINGS EVERY ACCOUNT' "$INST" | head -1 | cut -d: -f1)
row "S the block follows the changes document, precedes the VOC walk" "$(ok "$([ -n "$l_chg" ] && [ -n "$l_beg" ] && [ -n "$l_voc" ] && [ "$l_chg" -lt "$l_beg" ] && [ "$l_beg" -lt "$l_voc" ] && echo yes)")" "lines $l_chg $l_beg $l_voc"
row "S it copies only through docs.install (no cp, no install)" "$(ok "$(printf '%s\n' "$BLOCK" | grep -v '^\s*#' | grep -q -E '(^|[ ;])(sudo )?(cp|install) ' && echo no || echo yes)")" "a cp or install is in the block"
row "S the block has no exit"                                "$(ok "$(printf '%s\n' "$BLOCK" | grep -q -E '(^|[^a-z_])exit( |$)' && echo no || echo yes)")" "an exit is in the block"

echo "test-install-manuals: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
