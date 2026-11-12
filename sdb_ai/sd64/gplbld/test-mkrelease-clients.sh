#!/bin/bash
#
# test-mkrelease-clients.sh - mkrelease.sh's three client-library options, --clients DIR (clients/Linux64, OpenSSL 3), --clients-openssl4 DIR
# (clients/Linux64-openssl4) and --clients-windows DIR (clients/Windows64), S.151
# (owner: "we distribute windows client information with the linux core server just as we distribute the linux clients with the windows core server").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-mkrelease-clients.sh
#
# FREE CHECK: no sudo, no install, no sd.  It RUNS the working tree's gplbld/mkrelease.sh itself, with STAGING_DIR and ZIPS_DIR pointed at a scratch directory
# (mktemp -d, so TMPDIR chooses the place); the real Project_Staging and Project_Zips are never named.  Nothing is fetched, tagged or committed.
# Exit 0 every row passed, 1 a row failed, 2 it could not run (said as CANNOT RUN: no documentation repository, no Changes document, no zip, a bad fixture).
#
# IT NEEDS what mkrelease.sh needs: the documentation repository beside this one (DOCS_REPO=...), with the Changes document and the chapter PDFs of the
# version in gplsrc/revstamp.h, and zip / unzip.  The package is made from the CURRENT BRANCH's last commit with --allow-dev (a test package), so what is
# staged under source/ is what is committed; the script that runs is the one in the working tree.
#
#   R1  --clients-windows with a folder that does not exist: exit 2, "no clients folder", the option named, nothing staged and no zip
#   R2  --clients-windows with an empty folder: exit 2, "is empty", the option named, nothing staged and no zip
#   R3  R4  the same two for --clients
#   R5  a clients folder that holds a folder: exit 2, "not a file", nothing staged
#   R6  --clients-windows with no value: exit 2
#   A   a package with --clients-windows only: made; clients/Windows64 holds exactly the fixture's files, the same bytes, in the staging folder AND in the
#       unpacked zip; no clients/Linux64; the summary says NOT INCLUDED for Linux64 and not for Windows64; SHA256SUMS names nothing under clients/;
#       the installer's PACKAGE-SOURCE block (the working tree's installsdcore.sh, under its own set and IFS) takes the unpacked package, and - the control -
#       refuses the same package once a file is added under source/
#   B   a package with --clients only: made; clients/Linux64 the same bytes; no clients/Windows64; the summary says NOT INCLUDED for Windows64 and not Linux64
#   R7  (12 Nov 26) --clients-openssl4 with an empty folder: exit 2, "is empty", the option named
#   C   (12 Nov 26) a package with all three (--clients, --clients-openssl4, --clients-windows): each folder the same bytes as its fixture, in the staging folder
#       and the unpacked zip; the summary says NOT INCLUDED for none of them; SHA256SUMS names nothing under clients/
#
# NOT MEASURED HERE, and said so: real Windows client libraries (none exist yet; the fixture files are random bytes with made-up names), an install from the
# package (the VM), and mutants of mkrelease.sh (the script finds the repository from its own path, so a mutated copy elsewhere would not run).

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
MK="$HERE/mkrelease.sh"
INST="$REPO/installsdcore.sh"
DOCS="${DOCS_REPO:-$(cd "$REPO/.." && pwd)/SDCore4LinuxDocs}"

cannot() { echo "test-mkrelease-clients: CANNOT RUN - $*"; exit 2; }

[ -f "$MK" ] || cannot "no $MK"
[ -f "$INST" ] || cannot "no $INST"
for c in zip unzip sha256sum cmp git; do command -v "$c" >/dev/null || cannot "$c is not installed"; done
VERSION=$(sed -n 's/^#define SD_REV_STAMP[[:space:]]*"\(L[0-9.-]*\)".*/\1/p' "$REPO/sdb_ai/sd64/gplsrc/revstamp.h" | head -1)
[ -n "$VERSION" ] || cannot "no SD_REV_STAMP in gplsrc/revstamp.h"
REF=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null) || cannot "$REPO is not a git repository"
git -C "$DOCS" rev-parse --git-dir >/dev/null 2>&1 || cannot "no documentation repository at $DOCS (DOCS_REPO=...)"
DOCSREF=$(git -C "$DOCS" rev-parse --abbrev-ref HEAD)
ls "$DOCS/Changes/pdf/"*"-changes-$VERSION.pdf" >/dev/null 2>&1 || cannot "no Changes document for $VERSION in $DOCS/Changes/pdf"

T=$(mktemp -d) || cannot "mktemp"
trap 'rm -rf "$T"' EXIT
export TMPDIR="$T"                       # mkrelease.sh's own scratch folder goes here too
mkdir "$T/st0" "$T/zp0" "$T/st" "$T/zp" "$T/win" "$T/lin" "$T/lin4" "$T/empty" "$T/withdir" "$T/withdir/sub"
head -c 4096 /dev/urandom > "$T/win/fixture-win-one.bin"
head -c 1500 /dev/urandom > "$T/win/fixture-win-two.bin"
head -c 3000 /dev/urandom > "$T/lin/fixture-lin-one.bin"
head -c 2000 /dev/urandom > "$T/lin4/fixture-lin4-one.bin"
printf 'x\n' > "$T/withdir/a-file"
ABSENT="$T/absent"

echo "script under test : $MK"
echo "installer (block) : $INST"
echo "version / ref     : $VERSION from $REF ($(git -C "$REPO" rev-parse --short=12 HEAD)), documentation $DOCS at $DOCSREF"
echo "scratch           : $T"
echo "fixtures          : win $(ls "$T/win" | wc -l) files, lin $(ls "$T/lin" | wc -l) file, empty $(ls -A "$T/empty" | wc -l) entries, absent $([ -e "$ABSENT" ] && echo EXISTS || echo 'does not exist')"
# THE NULL CASE: a fixture that is not what the rows say it is would let them pass on nothing
[ "$(ls "$T/win" | wc -l)" = 2 ] && [ "$(ls "$T/lin" | wc -l)" = 1 ] && [ "$(ls "$T/lin4" | wc -l)" = 1 ] && [ -d "$T/empty" ] && [ -z "$(ls -A "$T/empty")" ] && [ ! -e "$ABSENT" ] || cannot "the fixtures are not as made"

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

mk() {   # mk STAGING ZIPS args... - runs mkrelease.sh; prints the command, its whole output, then RC=n
  local st="$1" zp="$2"; shift 2
  echo "    run: STAGING_DIR=$st ZIPS_DIR=$zp DOCS_REPO=$DOCS bash $MK $*" >&2
  STAGING_DIR="$st" ZIPS_DIR="$zp" DOCS_REPO="$DOCS" bash "$MK" "$@" 2>&1
  echo "RC=$?"
}
rc_of() { printf '%s\n' "$1" | sed -n 's/^RC=//p' | tail -1; }
nothing() { [ -z "$(ls -A "$T/st0")" ] && [ -z "$(ls -A "$T/zp0")" ]; }     # the refusal rows' staging and zip folders are still empty
COMMON=("$VERSION" --ref "$REF" --docs-ref "$DOCSREF" --allow-dev)

refused() {   # refused NAME WORDING OPTIONNAME args... - exit 2, the refusal's own wording with the option named, no "Made", nothing staged
  local name="$1" words="$2" opt="$3" OUT; shift 3
  OUT=$(mk "$T/st0" "$T/zp0" "${COMMON[@]}" --label ref "$@")
  row "$name" "$(ok "$([ "$(rc_of "$OUT")" = 2 ] && printf '%s\n' "$OUT" | grep -q -F -- "$words" && printf '%s\n' "$OUT" | grep -q -F -- "($opt DIR" \
        && ! printf '%s\n' "$OUT" | grep -q '^Made ' && nothing && echo yes)")" "$OUT; staging: $(ls -A "$T/st0" | tr '\n' ' '); zips: $(ls -A "$T/zp0" | tr '\n' ' ')"
}

echo "--- R: the refusals (before anything is staged)"
refused "R1 --clients-windows, a folder that does not exist: exit 2, 'no clients folder', nothing staged, no zip" "no clients folder $ABSENT" --clients-windows --clients-windows "$ABSENT"
refused "R2 --clients-windows, an empty folder: exit 2, 'is empty', nothing staged, no zip" "the clients folder $T/empty is empty" --clients-windows --clients-windows "$T/empty"
refused "R3 --clients, a folder that does not exist: exit 2, 'no clients folder', nothing staged, no zip" "no clients folder $ABSENT" --clients --clients "$ABSENT"
refused "R4 --clients, an empty folder: exit 2, 'is empty', nothing staged, no zip" "the clients folder $T/empty is empty" --clients --clients "$T/empty"
refused "R5 --clients-windows, a folder that holds a folder: exit 2, 'not a file', nothing staged, no zip" "the clients folder $T/withdir holds something that is not a file" --clients-windows --clients-windows "$T/withdir"
OUT=$(mk "$T/st0" "$T/zp0" "${COMMON[@]}" --clients-windows)
row "R6 --clients-windows with no value: exit 2, it says a value is needed, nothing staged" \
    "$(ok "$([ "$(rc_of "$OUT")" = 2 ] && printf '%s\n' "$OUT" | grep -q -F -- '--clients-windows needs a value' && nothing && echo yes)")" "$OUT"
refused "R7 --clients-openssl4, an empty folder: exit 2, 'is empty', nothing staged, no zip" "the clients folder $T/empty is empty" --clients-openssl4 --clients-openssl4 "$T/empty"

same_files() {   # same_files FIXTUREDIR PACKAGEDIR - the same names and, for each, the same bytes; and at least one file
  local a="$1" b="$2" f n=0
  [ -d "$b" ] || return 1
  [ "$(cd "$a" && ls -A | LC_ALL=C sort)" = "$(cd "$b" && ls -A | LC_ALL=C sort)" ] || return 1
  for f in "$a"/*; do cmp -s "$f" "$b/$(basename "$f")" || return 1; n=$((n+1)); done
  [ "$n" -gt 0 ]
}

OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
BLOCK=$(awk '/^# PACKAGE-SOURCE-BEGIN/{f=1;next} /^# PACKAGE-SOURCE-END/{f=0} f{print}' "$INST")
installer_takes() {   # installer_takes DIR - the installer's PACKAGE-SOURCE block on an unpacked package; prints its output, SRC=..., RC=n
  OPTS="$OPTS" BLOCK="$BLOCK" bash -c '
      eval "$OPTS"; RED=; NC=
      installer_dir="$1"
      eval "$BLOCK"
      echo "SRC=$pkg_source"' _ "$1" 2>&1
  echo "RC=$?"
}

echo "--- A: a package with --clients-windows only"
OUT=$(mk "$T/st" "$T/zp" "${COMMON[@]}" --label tsa --clients-windows "$T/win")
PKG="SDCore-$VERSION-tsa"
printf '%s\n' "$OUT" | sed -n '/^Made /,$p' | sed 's/^/    | /'
made=$([ "$(rc_of "$OUT")" = 0 ] && printf '%s\n' "$OUT" | grep -q -x -F "Made $T/zp/$PKG.zip" && ! printf '%s\n' "$OUT" | grep -q 'CHECK FAILED' && [ -f "$T/zp/$PKG.zip" ] && echo yes)
row "A1 the package is made: exit 0, 'Made <zip>', no CHECK FAILED, the zip exists" "$(ok "$made")" "$OUT"
if [ "$made" = yes ]; then
  row "A2 clients/Windows64 in the staging folder holds exactly the fixture's files, the same bytes" "$(ok "$(same_files "$T/win" "$T/st/$PKG/clients/Windows64" && echo yes)")" "$(ls -lA "$T/st/$PKG/clients/Windows64" 2>&1)"
  mkdir "$T/ua"; unzip -q "$T/zp/$PKG.zip" -d "$T/ua"
  row "A3 ...and in the unpacked zip" "$(ok "$(same_files "$T/win" "$T/ua/$PKG/clients/Windows64" && echo yes)")" "$(ls -lA "$T/ua/$PKG/clients/Windows64" 2>&1)"
  row "A4 no clients/Linux64 was made (the option was not given)" "$(ok "$([ ! -e "$T/st/$PKG/clients/Linux64" ] && [ ! -e "$T/ua/$PKG/clients/Linux64" ] && echo yes)")" "$(ls -A "$T/st/$PKG/clients")"
  row "A5 the summary says NOT INCLUDED for clients/Linux64 and does not say it for clients/Windows64" \
      "$(ok "$(printf '%s\n' "$OUT" | grep -q -F 'NOT INCLUDED: clients/Linux64 (--clients DIR' && ! printf '%s\n' "$OUT" | grep -q -F 'NOT INCLUDED: clients/Windows64' && echo yes)")" "$(printf '%s\n' "$OUT" | grep 'NOT INCLUDED')"
  nsum=$(grep -c '' "$T/ua/$PKG/SHA256SUMS"); nsrc=$(cd "$T/ua/$PKG" && find source -type f | wc -l)
  row "A6 SHA256SUMS names nothing under clients/ and one line for each of the $nsrc files under source/ (lines: $nsum)" \
      "$(ok "$([ "$nsum" -gt 0 ] && [ "$nsum" = "$nsrc" ] && ! grep -q '  clients/' "$T/ua/$PKG/SHA256SUMS" && echo yes)")" "$(grep '  clients/' "$T/ua/$PKG/SHA256SUMS" | head -3)"
  [ -n "$OPTS" ] && [ -n "$BLOCK" ] || cannot "no set / IFS lines or no PACKAGE-SOURCE block in $INST"
  IO=$(installer_takes "$T/ua/$PKG")
  row "A7 the installer's PACKAGE-SOURCE block takes the unpacked package with clients/Windows64 in it: exit 0, pkg_source is its source folder" \
      "$(ok "$([ "$(rc_of "$IO")" = 0 ] && printf '%s\n' "$IO" | grep -q -x -F "SRC=$T/ua/$PKG/source" && ! printf '%s\n' "$IO" | grep -q 'cannot be installed' && echo yes)")" "$IO"
  printf 'x\n' > "$T/ua/$PKG/source/unlisted-file"
  IO=$(installer_takes "$T/ua/$PKG")
  row "A8 control: the same block refuses the same package once a file is added under source/ (the instrument can refuse)" \
      "$(ok "$([ "$(rc_of "$IO")" = 1 ] && printf '%s\n' "$IO" | grep -q 'SHA256SUMS does not list' && ! printf '%s\n' "$IO" | grep -q '^SRC=' && echo yes)")" "$IO"
else
  fail=$((fail+1)); echo "  [FAIL] A2-A8 NOT RUN: there is no package to look at"
fi

echo "--- B: a package with --clients only"
OUT=$(mk "$T/st" "$T/zp" "${COMMON[@]}" --label tsb --clients "$T/lin")
PKG="SDCore-$VERSION-tsb"
printf '%s\n' "$OUT" | sed -n '/^Made /,$p' | sed 's/^/    | /'
made=$([ "$(rc_of "$OUT")" = 0 ] && printf '%s\n' "$OUT" | grep -q -x -F "Made $T/zp/$PKG.zip" && ! printf '%s\n' "$OUT" | grep -q 'CHECK FAILED' && [ -f "$T/zp/$PKG.zip" ] && echo yes)
row "B1 the package is made: exit 0, 'Made <zip>', no CHECK FAILED, the zip exists" "$(ok "$made")" "$OUT"
if [ "$made" = yes ]; then
  mkdir "$T/ub"; unzip -q "$T/zp/$PKG.zip" -d "$T/ub"
  row "B2 clients/Linux64 holds exactly the fixture's file, the same bytes, in the staging folder and in the unpacked zip" \
      "$(ok "$(same_files "$T/lin" "$T/st/$PKG/clients/Linux64" && same_files "$T/lin" "$T/ub/$PKG/clients/Linux64" && echo yes)")" "$(ls -lA "$T/st/$PKG/clients/Linux64" "$T/ub/$PKG/clients/Linux64" 2>&1)"
  row "B3 no clients/Windows64 was made (the option was not given)" "$(ok "$([ ! -e "$T/st/$PKG/clients/Windows64" ] && [ ! -e "$T/ub/$PKG/clients/Windows64" ] && echo yes)")" "$(ls -A "$T/st/$PKG/clients")"
  row "B4 the summary says NOT INCLUDED for clients/Windows64, naming --clients-windows DIR, and does not say it for clients/Linux64" \
      "$(ok "$(printf '%s\n' "$OUT" | grep -q -F 'NOT INCLUDED: clients/Windows64 (--clients-windows DIR' && ! printf '%s\n' "$OUT" | grep -q -F 'NOT INCLUDED: clients/Linux64 (' && echo yes)")" "$(printf '%s\n' "$OUT" | grep 'NOT INCLUDED')"
else
  fail=$((fail+1)); echo "  [FAIL] B2-B4 NOT RUN: there is no package to look at"
fi

echo "--- C: a package with all three client folders"
OUT=$(mk "$T/st" "$T/zp" "${COMMON[@]}" --label tsc --clients "$T/lin" --clients-openssl4 "$T/lin4" --clients-windows "$T/win")
PKG="SDCore-$VERSION-tsc"
printf '%s\n' "$OUT" | sed -n '/^Made /,$p' | sed 's/^/    | /'
made=$([ "$(rc_of "$OUT")" = 0 ] && printf '%s\n' "$OUT" | grep -q -x -F "Made $T/zp/$PKG.zip" && ! printf '%s\n' "$OUT" | grep -q 'CHECK FAILED' && [ -f "$T/zp/$PKG.zip" ] && echo yes)
row "C1 the package is made: exit 0, 'Made <zip>', no CHECK FAILED, the zip exists" "$(ok "$made")" "$OUT"
if [ "$made" = yes ]; then
  mkdir "$T/uc"; unzip -q "$T/zp/$PKG.zip" -d "$T/uc"
  c2=yes
  for pair in "lin:Linux64" "lin4:Linux64-openssl4" "win:Windows64"; do
    same_files "$T/${pair%%:*}" "$T/st/$PKG/clients/${pair#*:}" && same_files "$T/${pair%%:*}" "$T/uc/$PKG/clients/${pair#*:}" || c2=no
  done
  row "C2 clients/Linux64, clients/Linux64-openssl4 and clients/Windows64 each hold exactly their fixture's files, the same bytes, staged and unpacked" \
      "$(ok "$c2")" "$(ls -lAR "$T/uc/$PKG/clients" 2>&1)"
  row "C3 the summary says NOT INCLUDED for no clients folder" "$(ok "$(! printf '%s\n' "$OUT" | grep -q -F 'NOT INCLUDED: clients/' && echo yes)")" "$(printf '%s\n' "$OUT" | grep 'NOT INCLUDED')"
  row "C4 SHA256SUMS names nothing under clients/" "$(ok "$(! grep -q '  clients/' "$T/uc/$PKG/SHA256SUMS" && echo yes)")" "$(grep '  clients/' "$T/uc/$PKG/SHA256SUMS" | head -3)"
else
  fail=$((fail+1)); echo "  [FAIL] C2-C4 NOT RUN: there is no package to look at"
fi

echo
echo "test-mkrelease-clients: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
