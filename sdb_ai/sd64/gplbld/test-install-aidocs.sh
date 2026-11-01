#!/bin/bash
#
# test-install-aidocs.sh - installsdcore.sh's two blocks that put the documentation under /usr/local/sdsys/docs for the AI line (S.100), run the way the installer runs them.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-aidocs.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-aidocs.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-aidocs.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no network (git is a function here), no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# WHAT IT RUNS.  The text between "# DOCS-CORPUS-BEGIN" and "# DOCS-CORPUS-END" (the fetch and copy) and between "# DOCS-MODE-BEGIN" and "# DOCS-MODE-END" (the modes, which run AFTER the
# installer's "chmod -R 755"), cut out verbatim and evaluated under the options and the IFS read from the installer's own lines, with sudo a function that logs and runs as the caller and
# chown a function that logs (the caller is not root).  "git clone" copies a scratch documentation tree and logs its arguments.
#
#   B1  a good clone: the success line, docs/user holds the User pages and docs/admin the Administrator pages (and nothing crossed over), the clone was asked for the installer's branch and
#       the documentation repository, a page left by an older install is gone, the block reached its end
#   B2  the clone fails / has no Administrator/markdown / has no User/markdown / mktemp fails: a note, the install goes on, and the OLDER docs are still there untouched
#   B3  the modes: docs/user 755 and 644; docs/admin 700 and 600 and NOTHING in it open to group or other; chown asked for sdsys:sdusers; with no docs the block does nothing
#   B4  the order in the installer (text) and no exit in either block
#
# NOT MEASURED HERE: that a real clone from GitHub works (the first install that runs it), and that the operating system refuses an account holder's session the administrator's pages
# (a sandbox is not a different user: .claude/vmtools has the witness).

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
  mutant old-docs-kept           's#^    sudo rm -rf "\$sdsysdir/docs"$#    true#'
  mutant admin-into-user         's#"\$docs_tmp"/docs/Administrator/markdown/\*.md "\$sdsysdir/docs/admin/"#"$docs_tmp"/docs/Administrator/markdown/*.md "$sdsysdir/docs/user/"#'
  mutant user-into-admin         's#"\$docs_tmp"/docs/User/markdown/\*.md "\$sdsysdir/docs/user/"#"$docs_tmp"/docs/User/markdown/*.md "$sdsysdir/docs/admin/"#'
  mutant branch-ignored          's#--branch "\$REPO_BRANCH" --depth 1 "\$DOCS_URL"#--depth 1 "$DOCS_URL"#'
  mutant wrong-repository        's#--depth 1 "\$DOCS_URL" "\$docs_tmp/docs"#--depth 1 "$REPO_URL" "$docs_tmp/docs"#'
  mutant admin-test-dropped      's# \&\& \[ -d "\$docs_tmp/docs/Administrator/markdown" \]##'
  mutant user-test-dropped       's# \&\& \[ -d "\$docs_tmp/docs/User/markdown" \]##'
  mutant hard-stop-on-failure    's#^    echo "Note: the documentation could not be fetched from .*#    exit 1#'
  mutant tmp-guard-dropped       's#docs_tmp=\$(mktemp -d 2>/dev/null) || docs_tmp=""#docs_tmp=$(mktemp -d)#'
  mutant admin-dir-open          's#sudo chmod 700 "\$sdsysdir/docs/admin"#sudo chmod 755 "$sdsysdir/docs/admin"#'
  mutant admin-files-open        's#sudo find "\$sdsysdir/docs/admin" -type f -exec chmod 600 {} +#sudo find "$sdsysdir/docs/admin" -type f -exec chmod 644 {} +#'
  mutant user-files-writable     's#sudo find "\$sdsysdir/docs/user" -type f -exec chmod 644 {} +#sudo find "$sdsysdir/docs/user" -type f -exec chmod 664 {} +#'
  mutant chown-removed           's#^    sudo chown -R sdsys:sdusers "\$sdsysdir/docs"$#    true#'
  mutant mode-block-too-early    '/^# DOCS-MODE-END$/a sudo chmod -R 755 "$sdsysdir"'
  mutant corpus-after-the-chown  '/^# DOCS-CORPUS-BEGIN$/i sudo chown -R sdsys:sdusers "$sdsysdir"'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST"; grep -m1 -E '^IFS=' "$INST")
case "$OPTS" in *IFS=*) ;; *) echo "test-install-aidocs: CANNOT RUN - no IFS line in the installer"; exit 2;; esac
BLK=$(awk '/^# DOCS-CORPUS-BEGIN$/{f=1;next} /^# DOCS-CORPUS-END$/{f=0} f{print}' "$INST")
MODE=$(awk '/^# DOCS-MODE-BEGIN$/{f=1;next} /^# DOCS-MODE-END$/{f=0} f{print}' "$INST")
REPO_BRANCH_V=$(sed -n 's/^REPO_BRANCH="\(.*\)"$/\1/p' "$INST" | head -1)
DOCS_URL_V=$(sed -n 's/^DOCS_URL="\(.*\)"$/\1/p' "$INST" | head -1)
REPO_URL_V=$(sed -n 's/^REPO_URL="\(.*\)"$/\1/p' "$INST" | head -1)
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-aidocs: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLK" ]  && { echo "test-install-aidocs: CANNOT RUN - no block between DOCS-CORPUS-BEGIN and DOCS-CORPUS-END (nothing to check)"; exit 2; }
[ -z "$MODE" ] && { echo "test-install-aidocs: CANNOT RUN - no block between DOCS-MODE-BEGIN and DOCS-MODE-END (nothing to check)"; exit 2; }
[ -n "$REPO_BRANCH_V" ] && [ -n "$DOCS_URL_V" ] && [ -n "$REPO_URL_V" ] || { echo "test-install-aidocs: CANNOT RUN - REPO_BRANCH, REPO_URL or DOCS_URL is not set in the installer"; exit 2; }
echo "block     : $(printf '%s\n' "$BLK" | wc -l) lines;  mode block: $(printf '%s\n' "$MODE" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export BLK MODE OPTS T REPO_BRANCH_V DOCS_URL_V REPO_URL_V
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}

setup() {   # a scratch system directory, a scratch "documentation repository", empty logs
  rm -rf "$T/sdsys" "$T/repo" "$T/work"; mkdir -p "$T/sdsys" "$T/work" "$T/repo/User/markdown" "$T/repo/Administrator/markdown"
  printf '# Guide\n\nUser page one, zzuserword.\n' > "$T/repo/User/markdown/01-guide.md"
  printf '# Tutorial\n\nUser page two.\n' > "$T/repo/User/markdown/02-tutorial.md"
  printf '# Accounts\n\nAdministrator page, zzadminword.\n' > "$T/repo/Administrator/markdown/01-accounts.md"
  : > "$T/sudo.log"; : > "$T/git.log"; : > "$T/chown.log"
}
run() {   # run BLOCK-VARIABLE-NAME [extra shell to run first]: prints what the block printed, then REACHED-END
  SUDO_LOG="$T/sudo.log" SDSYSDIR="$T/sdsys" WHICH="$1" EXTRA="${2:-}" bash -c '
      eval "$OPTS"
      sdsysdir="$SDSYSDIR"; RED=; NC=
      mkdir -p "$T/tmpd"; export TMPDIR="$T/tmpd"
      REPO_BRANCH="$REPO_BRANCH_V"; DOCS_URL="$DOCS_URL_V"; REPO_URL="$REPO_URL_V"
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$SUDO_LOG"; "$@"; }
      chown() { ( IFS=" "; printf "%s\n" "$*" ) >> "$T/chown.log"; }
      git() {
        ( IFS=" "; printf "%s\n" "$*" ) >> "$T/git.log"
        if [ -n "${GITFAIL:-}" ]; then return 128; fi
        local dest; for dest in "$@"; do :; done
        mkdir -p "$dest" && cp -R "$T/repo/." "$dest/"
      }
      eval "$EXTRA"
      cd "$T/work"
      eval "${!WHICH}"
      echo "REACHED-END"' 2>&1
}
DOCS="$T/sdsys/docs"
older() {   # an older install's docs
  mkdir -p "$DOCS/user" "$DOCS/admin"; printf 'old user page\n' > "$DOCS/user/stale.md"; printf 'old admin page\n' > "$DOCS/admin/stale.md"
}

echo "--- B1: a good clone"
setup; older; OUT=$(run BLK)
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "B1 the success line, and the block reached its end" "$(printf '%s' "$OUT" | grep -q -F "Installed the documentation the AI line draws on: $T/sdsys/docs" && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "$OUT"
row "B1b docs/user holds the User pages and nothing else (and there are some)" \
    "$([ "$(ls "$DOCS/user" | tr '\n' ' ')" = "01-guide.md 02-tutorial.md " ] && cmp -s "$T/repo/User/markdown/01-guide.md" "$DOCS/user/01-guide.md" && echo 0 || echo 1)" "user: $(ls "$DOCS/user" | tr '\n' ' ')"
row "B1c docs/admin holds the Administrator pages and nothing else" \
    "$([ "$(ls "$DOCS/admin" | tr '\n' ' ')" = "01-accounts.md " ] && cmp -s "$T/repo/Administrator/markdown/01-accounts.md" "$DOCS/admin/01-accounts.md" && echo 0 || echo 1)" "admin: $(ls "$DOCS/admin" | tr '\n' ' ')"
row "B1d the page an older install left is gone from both (the null case for the removal: it was there before)" "$([ ! -e "$DOCS/user/stale.md" ] && [ ! -e "$DOCS/admin/stale.md" ] && echo 0 || echo 1)" "stale pages are still there"
row "B1e the clone asked for the installer's branch ($REPO_BRANCH_V), one level deep, from the documentation repository ($DOCS_URL_V) and not the source's" \
    "$(grep -q -F -- "clone --quiet --branch $REPO_BRANCH_V --depth 1 $DOCS_URL_V " "$T/git.log" && ! grep -q -F "$REPO_URL_V " "$T/git.log" && echo 0 || echo 1)" "git log: $(cat "$T/git.log")"
row "B1f the scratch clone was removed afterwards" "$([ -d "$T/tmpd" ] && [ -z "$(ls -A "$T/tmpd")" ] && echo 0 || echo 1)" "left behind: $(ls -A "$T/tmpd" 2>&1)"

echo "--- B2: no documentation: a note, the install goes on, an older install's docs are untouched"
chk() {   # name, extra, mutate (shell run in the scratch repository first)
  setup; older; ( eval "$3" ); OUT=$(run BLK "$2")
  row "$1: a note, REACHED-END, the older pages are still there, nothing was removed or copied" \
      "$(printf '%s' "$OUT" | grep -q 'Note: the documentation could not be fetched' && printf '%s' "$OUT" | grep -q REACHED-END && [ -e "$DOCS/user/stale.md" ] && [ -e "$DOCS/admin/stale.md" ] && ! grep -q -E '^(rm|cp) ' "$T/sudo.log" && echo 0 || echo 1)" "$OUT"
}
chk "B2 the clone fails" "GITFAIL=1" "true"
chk "B2b the clone has no Administrator/markdown" "" "rm -rf '$T/repo/Administrator'"
chk "B2c the clone has no User/markdown" "" "rm -rf '$T/repo/User'"
chk "B2d mktemp fails" "mktemp() { return 1; }" "true"

echo "--- B3: the modes (after the installer's chmod -R 755)"
setup; run BLK > /dev/null; chmod -R 755 "$T/sdsys"; OUT=$(run MODE)
row "B3 docs/user is 755 and its files 644" "$([ "$(stat -c %a "$DOCS/user")" = 755 ] && [ -z "$(find "$DOCS/user" -type f ! -perm 644)" ] && [ -n "$(find "$DOCS/user" -type f)" ] && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "user: $(stat -c %a "$DOCS/user"); files not 644: $(find "$DOCS/user" -type f ! -perm 644 | head -2 | tr '\n' ' ')"
row "B3b docs/admin is 700 and its files 600: nothing in it is open to group or other" "$([ "$(stat -c %a "$DOCS/admin")" = 700 ] && [ -z "$(find "$DOCS/admin" -type f ! -perm 600)" ] && [ -n "$(find "$DOCS/admin" -type f)" ] && [ -z "$(find "$DOCS/admin" -perm /077)" ] && echo 0 || echo 1)" "admin: $(stat -c %a "$DOCS/admin"); open: $(find "$DOCS/admin" -perm /077 | head -3 | tr '\n' ' ')"
row "B3c docs and everything under it is chowned sdsys:sdusers, and nothing is writable by group or other" "$(grep -q -F -- "-R sdsys:sdusers $T/sdsys/docs" "$T/chown.log" && [ -z "$(find "$DOCS" -perm /022)" ] && echo 0 || echo 1)" "chown log: $(cat "$T/chown.log"); writable: $(find "$DOCS" -perm /022 | head -2 | tr '\n' ' ')"
setup; chmod -R 755 "$T/sdsys"; OUT=$(run MODE)
row "B3d no docs installed: the mode block does nothing and does not stop the install" "$(printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DOCS" ] && ! grep -q 'find' "$T/sudo.log" && echo 0 || echo 1)" "$OUT"

echo "--- B4: the order in the installer"
ln_of() { grep -n -m1 -F -x -- "$1" "$INST" | cut -d: -f1; }
ln_last() { grep -n -F -x -- "$1" "$INST" | tail -1 | cut -d: -f1; }
L_SD=$(ln_of 'sudo cp -R sdsys /usr/local'); L_B=$(ln_of '# DOCS-CORPUS-BEGIN'); L_CH=$(ln_of 'sudo chown -R sdsys:sdusers "$sdsysdir"')
L_M=$(ln_of '# DOCS-MODE-BEGIN'); L_C755=$(ln_last 'sudo chmod -R 755 "$sdsysdir"')
echo "      lines: cp sdsys $L_SD, fetch block $L_B, first chown -R $L_CH, last chmod -R 755 $L_C755, mode block $L_M"
if [ -z "$L_SD" ] || [ -z "$L_B" ] || [ -z "$L_CH" ] || [ -z "$L_M" ] || [ -z "$L_C755" ]; then echo "test-install-aidocs: CANNOT RUN - an anchor line is not in the installer"; exit 2; fi
row "B4 the fetch comes after the tree is copied in and before the first chown -R (so the pages land sdsys:sdusers)" "$([ "$L_SD" -lt "$L_B" ] && [ "$L_B" -lt "$L_CH" ] && echo 0 || echo 1)" "lines $L_SD < $L_B < $L_CH"
row "B4b the mode block comes after the last chmod -R 755" "$([ "$L_M" -gt "$L_C755" ] && echo 0 || echo 1)" "mode block $L_M, last chmod -R 755 $L_C755"
row "B4c neither block contains an exit (documentation never ends an install)" "$(printf '%s\n%s\n' "$BLK" "$MODE" | grep -q -E '(^|[^a-z_])exit([^a-z_]|$)' && echo 1 || echo 0)" "an exit is in the block"

echo "test-install-aidocs: $pass passed, $fail failed"
[ "$((pass + fail))" -eq 0 ] && { echo "test-install-aidocs: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
