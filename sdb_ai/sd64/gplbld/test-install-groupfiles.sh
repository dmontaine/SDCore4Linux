#!/bin/bash
#
# test-install-groupfiles.sh - the installer's repair of the four record files of EXISTING group accounts (19 Oct 2026, the owner's yes:
# "in the installer's upgrade, for each group account except shared, give voc/%0, voc/%1 and $hold.dic/%0|%1 the group of the account
# directory (owner sdsys)").  Before 981a36a, create.account group left voc/%0, voc/%1, $hold.dic/%0 and $hold.dic/%1 in the group sdusers,
# which every SD user belongs to; the fix is for NEW accounts, this is for the ones already made.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-groupfiles.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-groupfiles.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-groupfiles.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no chown (a stub table plays the file system's owners).  Exit 0 every row
# passed, 1 a row failed, 2 it could not run (a missing piece, or a helper that was never called, is exit 2, never a pass).
#
# WHAT IT RUNS.  The function repair_group_account_files is cut out of the installer and run under the installer's OWN `set` and `IFS`
# lines (the 19 Oct lesson: a block tested under `set` alone had been green and then did nothing on the real install).  Owners come from a
# table: `stat` is a function that reads it, and the helper is `sudo /usr/local/sbin/sd-elevate`, which the stub answers by running the
# REAL gplbld/sd-elevate with --dry-run on the scratch accounts root (SD_ACCT_ROOT) - so the arguments the installer builds are judged by
# the helper's own validation (the record-file rule of 981a36a, the hard-link rule), and a refusal by it is a real refusal - and, when
# the helper accepts, by changing the table.  The files, links and directories are real, in a scratch directory.
#
#   S1  the main scenario: alpha has all four files in sdusers, beta two of its three files wrong, gamma has none, `shared` and an account
#       whose directory is not in an sdg_ group (odd) have wrong files too.  Exactly the five files of alpha and beta go to the helper,
#       in the order voc/%0, voc/%1, $hold.dic/%0, $hold.dic/%1, with `chown-account sdsys <the directory's group> <path>`; shared and
#       odd are never named; afterwards the table says sdsys:<group> for those five and is untouched for the rest.
#   S2  nothing wrong: not one call to the helper, and it says so.   S3  links: a %0 that is a symlink to another account's file, and a
#       voc that is a symlink to another account's voc, are left alone and the other account is never chowned through them.
#   S4  the helper refuses (a %0 with a second hard link): a WARNING naming it, the rest of the account is still done, the function
#       returns 0 under the installer's set -e.   S5  no group_accounts directory at all.   T   static: where it is called, the four names.
#
# ANCHORED ON THE SUCCESS WORDING: "Gave N record file(s)" is printed only for a file the helper accepted, and every failing scenario is
# judged on that count AND on the table, not on the function returning.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"
HELPER="$HERE/sd-elevate"

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
  F='/^repair_group_account_files() {/,/^}/'
  mutant shared-not-excluded      "$F s/if \[ \"\$gname\" = shared \]; then/if false; then/"
  mutant dir-group-not-required   "$F s/^            sdg_?\*) ;;\$/            *) ;;/"
  mutant file-link-check-removed  "$F s/if \[ \"\$fcanon\" != \"\$gcanon\/\$rel\" \]; then/if false; then/"
  mutant dir-link-check-removed   "$F s/if \[ \"\$gcanon\" != \"\$(realpath -e -- \"\$root\")\/group_accounts\/\$gname\" \]; then/if false; then/"
  mutant not-idempotent           "$F s/if \[ \"\$cur\" = \"sdsys:\${ggroup}\" \]; then/if false; then/"
  mutant owner-root               "$F s/chown-account sdsys \"\$ggroup\"/chown-account root \"\$ggroup\"/"
  mutant group-sdusers            "$F s/chown-account sdsys \"\$ggroup\"/chown-account sdsys sdusers/"
  mutant file-dropped             "$F s/ '\\\$hold.dic\/%1'; do/; do/"
  mutant file-added               "$F s/'\\\$hold.dic\/%1'; do/'\\\$hold.dic\/%1' voc\/readme; do/"
  mutant refusal-aborts-install   "$F s/if sudo \/usr\/local\/sbin\/sd-elevate chown-account sdsys \"\$ggroup\" \"\$f\"; then/sudo \/usr\/local\/sbin\/sd-elevate chown-account sdsys \"\$ggroup\" \"\$f\"; if true; then/"
  mutant refusal-not-warned       "$F s/if \[ \"\$left\" -gt 0 \]; then/if false; then/"
  mutant missing-file-not-skipped "$F s/if \[ ! -e \"\$f\" \] \&\& \[ ! -L \"\$f\" \]; then/if false; then/"
  mutant helper-not-used          "$F s/sudo \/usr\/local\/sbin\/sd-elevate chown-account sdsys \"\$ggroup\" \"\$f\"/sudo chown sdsys:\"\$ggroup\" \"\$f\"/"
  mutant call-removed             's/^    repair_group_account_files "\$ACCT_PATH"$/    true/'
  mutant call-wrong-root          's/repair_group_account_files "\$ACCT_PATH"/repair_group_account_files "\/home\/sd\/user_accounts"/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

# THE INSTALLER'S OWN set AND IFS (installsdcore.sh: IFS=$'\n\t').
OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
FUNC=$(awk '/^repair_group_account_files\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-groupfiles: CANNOT RUN - no IFS line in the installer (the function must be run under it)"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-groupfiles: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$FUNC" ] && { echo "test-install-groupfiles: CANNOT RUN - no function repair_group_account_files in the installer (nothing to check)"; exit 2; }
[ -r "$HELPER" ] || { echo "test-install-groupfiles: CANNOT RUN - $HELPER is not readable"; exit 2; }
echo "function  : $(printf '%s\n' "$FUNC" | wc -l) lines"

T=$(mktemp -d); T=$(cd "$T" && pwd -P); trap 'rm -rf "$T"' EXIT
ROOT="$T/home/sd"
OWNERS="$T/owners"

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# ---- the scratch tree: put DIR/FILE with an owner in the table ---------------------------------------------------------------
reset() { rm -rf "$T/home" "$OWNERS" "$T/elevate.log"; mkdir -p "$ROOT/group_accounts"; : > "$OWNERS"; : > "$T/elevate.log"; }
own() {   # own PATH USER:GROUP
  awk -F'\t' -v p="$1" '$1!=p' "$OWNERS" > "$OWNERS.n"; mv "$OWNERS.n" "$OWNERS"
  printf '%s\t%s\n' "$1" "$2" >> "$OWNERS"
}
acct() {   # acct NAME DIRGROUP  - the account directory, voc and $hold.dic directories
  mkdir -p "$ROOT/group_accounts/$1/voc" "$ROOT/group_accounts/$1/\$hold.dic"
  own "$ROOT/group_accounts/$1" "sdsys:$2"
}
rec() {   # rec NAME REL OWNER  - a record file of the account, in the table with OWNER
  : > "$ROOT/group_accounts/$1/$2"; own "$ROOT/group_accounts/$1/$2" "$3"
}
four() {   # four NAME OWNER  - all four record files with the same owner
  local r; for r in voc/%0 voc/%1 '$hold.dic/%0' '$hold.dic/%1'; do rec "$1" "$r" "$2"; done
}
who() { awk -F'\t' -v p="$1" '$1==p{print $2}' "$OWNERS"; }   # who PATH

# ---- run the function under the installer's set and IFS ------------------------------------------------------------------------
run_fn() {   # prints the output, then RC=n.  The function is a plain statement so that set -e judges it, as in the installer.
  OPTS="$OPTS" FUNC="$FUNC" T="$T" ROOT="$ROOT" OWNERS="$OWNERS" HELPER="$HELPER" bash -c '
      eval "$OPTS"; RED=; NC=
      stat() {   # stat -c %G|%U:%G PATH, from the table
        local ug; ug=$(awk -F"\t" -v p="$3" "\$1==p{print \$2; exit}" "$OWNERS")
        [ -n "$ug" ] || return 1
        case "$2" in %G) printf "%s\n" "${ug#*:}" ;; %U:%G) printf "%s\n" "$ug" ;; *) return 2 ;; esac
      }
      sudo() {
        if [ "$1" = /usr/local/sbin/sd-elevate ]; then
          ( IFS=" "; printf "%s\n" "$*" ) >> "$T/elevate.log"
          SD_ACCT_ROOT="$ROOT" bash "$HELPER" --dry-run "${@:2}" > "$T/helper.out" 2>&1 || { cat "$T/helper.out"; return 1; }
          local real; real=$(realpath -e -- "$5")
          awk -F"\t" -v p="$real" "\$1!=p" "$OWNERS" > "$OWNERS.n"; mv "$OWNERS.n" "$OWNERS"
          printf "%s\t%s:%s\n" "$real" "$3" "$4" >> "$OWNERS"
          return 0
        fi
        "$@"
      }
      eval "$FUNC"
      repair_group_account_files "$ROOT"
      echo "RC=0"' 2>&1
}
calls() { grep -c . "$T/elevate.log"; }
G="$ROOT/group_accounts"

# ---- S1 ---------------------------------------------------------------------------------------------------------------------
echo "--- S1: the main scenario"
reset
acct alpha sdg_alpha;  four alpha sdsys:sdusers
acct beta  sdg_beta;   rec beta voc/%0 sdsys:sdg_beta; rec beta voc/%1 sdsys:sdusers; rmdir "$G/beta/\$hold.dic"
acct gamma sdg_gamma
acct shared sdg_shared; four shared sdsys:sdusers   # the real one is in sdusers; here only the NAME can keep it out
acct odd sdusers;      four odd sdsys:sdusers
OUT=$(run_fn)
EXPECT=$(printf '%s\n' \
  "/usr/local/sbin/sd-elevate chown-account sdsys sdg_alpha $G/alpha/voc/%0" \
  "/usr/local/sbin/sd-elevate chown-account sdsys sdg_alpha $G/alpha/voc/%1" \
  "/usr/local/sbin/sd-elevate chown-account sdsys sdg_alpha $G/alpha/\$hold.dic/%0" \
  "/usr/local/sbin/sd-elevate chown-account sdsys sdg_alpha $G/alpha/\$hold.dic/%1" \
  "/usr/local/sbin/sd-elevate chown-account sdsys sdg_beta $G/beta/voc/%1")
row "S1a the helper was called (the null case: a function that does nothing passes every 'not named' row)" "$(ok "$([ "$(calls)" -gt 0 ] && echo yes)")" "calls: $(calls); output: $OUT"
row "S1b exactly the five files, in order, as 'chown-account sdsys <the directory's group> <path>'" \
    "$(ok "$([ "$(cat "$T/elevate.log")" = "$EXPECT" ] && echo yes)")" "got: $(cat "$T/elevate.log")"
row "S1c shared is never named" "$(ok "$(! grep -q 'shared' "$T/elevate.log" && [ "$(calls)" -gt 0 ] && echo yes)")" "$(cat "$T/elevate.log")"
row "S1d the account whose directory is not in an sdg_ group is never named, and the output says why" \
    "$(ok "$(! grep -q '/odd/' "$T/elevate.log" && printf '%s' "$OUT" | grep -q "odd: its directory belongs to 'sdusers', not to an sdg_ group; left alone" && echo yes)")" "$OUT"
row "S1e afterwards alpha's four files are sdsys:sdg_alpha and beta's voc/%1 is sdsys:sdg_beta" \
    "$(ok "$([ "$(who "$G/alpha/voc/%0")" = sdsys:sdg_alpha ] && [ "$(who "$G/alpha/voc/%1")" = sdsys:sdg_alpha ] && [ "$(who "$G/alpha/\$hold.dic/%0")" = sdsys:sdg_alpha ] && [ "$(who "$G/alpha/\$hold.dic/%1")" = sdsys:sdg_alpha ] && [ "$(who "$G/beta/voc/%1")" = sdsys:sdg_beta ] && echo yes)")" "$(cat "$OWNERS")"
row "S1f ...and shared's and odd's files are exactly as they were" \
    "$(ok "$([ "$(who "$G/shared/voc/%0")" = sdsys:sdusers ] && [ "$(who "$G/odd/voc/%1")" = sdsys:sdusers ] && [ "$(who "$G/beta/voc/%0")" = sdsys:sdg_beta ] && echo yes)")" "$(cat "$OWNERS")"
row "S1g the success line counts the five: 'Gave 5 record file(s)'" "$(ok "$(printf '%s' "$OUT" | grep -q 'Gave 5 record file(s) of the group accounts their own group' && echo yes)")" "$OUT"
row "S1h the function returned (RC=0 printed under the installer's set -e) and the odd account is reported in a WARNING" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING: 1 record file' && echo yes)")" "$OUT"

# ---- S2 ---------------------------------------------------------------------------------------------------------------------
echo "--- S2: nothing wrong"
reset
acct alpha sdg_alpha;  four alpha sdsys:sdg_alpha
acct beta sdg_beta;    four beta sdsys:sdg_beta
acct shared sdusers;   four shared sdsys:sdusers
OUT=$(run_fn)
row "S2a not one call to the helper" "$(ok "$([ "$(calls)" -eq 0 ] && echo yes)")" "calls: $(calls)"
row "S2b ...and it says every account is already right, with no WARNING and no 'Gave'" \
    "$(ok "$(printf '%s' "$OUT" | grep -q "Every group account's record files are already in its group" && ! printf '%s' "$OUT" | grep -q -E 'WARNING|Gave' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
OUT=$(run_fn)
row "S2c a second run of S1's end state is the same (idempotent): still no call" "$(ok "$([ "$(calls)" -eq 0 ] && echo yes)")" "calls: $(calls)"

# ---- S3 ---------------------------------------------------------------------------------------------------------------------
echo "--- S3: links"
reset
acct victim sdusers;   four victim sdsys:sdusers
acct delta sdg_delta;  ln -s "$G/victim/voc/%0" "$G/delta/voc/%0"; own "$G/delta/voc/%0" "sdsys:sdg_delta"
rec delta voc/%1 sdsys:sdg_delta
acct epsilon sdg_epsilon; rmdir "$G/epsilon/voc"; ln -s "$G/victim/voc" "$G/epsilon/voc"
acct linked sdg_linked;   four linked sdsys:sdusers; mkdir -p "$T/elsewhere"; mv "$G/linked" "$T/elsewhere/linked"; ln -s "$T/elsewhere/linked" "$G/linked"
OUT=$(run_fn)
row "S3a a %0 that is a symlink to another account's file is left alone: reported, never named to the helper" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'delta: voc/%0 is a link or sits behind one; left alone' && ! grep -q 'delta/voc/%0' "$T/elevate.log" && echo yes)")" "$OUT"
row "S3b a voc directory that is a symlink to another account's voc: both files left alone" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'epsilon: voc/%0 is a link or sits behind one' && printf '%s' "$OUT" | grep -q 'epsilon: voc/%1 is a link or sits behind one' && ! grep -q 'epsilon' "$T/elevate.log" && echo yes)")" "$OUT"
row "S3c an account directory that is itself a symlink is left alone" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'linked: its directory is a symbolic link; left alone' && ! grep -q 'linked' "$T/elevate.log" && echo yes)")" "$OUT"
row "S3d the victim's files were not chowned through any link (the table is untouched) and the helper was called for nothing here" \
    "$(ok "$([ "$(who "$G/victim/voc/%0")" = sdsys:sdusers ] && [ "$(who "$G/victim/voc/%1")" = sdsys:sdusers ] && [ "$(calls)" -eq 0 ] && echo yes)")" "calls: $(calls); $(cat "$OWNERS")"
row "S3e the function returned and warned" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING' && echo yes)")" "$OUT"

# ---- S4 ---------------------------------------------------------------------------------------------------------------------
echo "--- S4: the helper refuses"
reset
acct zeta sdg_zeta;    rec zeta voc/%0 sdsys:sdusers; rec zeta voc/%1 sdsys:sdusers; ln "$G/zeta/voc/%0" "$G/zeta/\$hold.dic/hardlinked"
OUT=$(run_fn)
row "S4a the helper was called for both files (it, not the installer, judged the hard link)" "$(ok "$([ "$(calls)" -eq 2 ] && echo yes)")" "calls: $(calls)"
row "S4b the refused %0 is named in the output, a WARNING follows, and it keeps its owner" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'zeta: sd-elevate refused voc/%0; left as it is' && printf '%s' "$OUT" | grep -q 'WARNING: 1 record file' && [ "$(who "$G/zeta/voc/%0")" = sdsys:sdusers ] && echo yes)")" "$OUT"
row "S4c the other file of the account was still done, and counted" \
    "$(ok "$([ "$(who "$G/zeta/voc/%1")" = sdsys:sdg_zeta ] && printf '%s' "$OUT" | grep -q 'Gave 1 record file(s)' && echo yes)")" "$OUT"
row "S4d the function returned (RC=0): a refusal does not stop the install" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"

# ---- S5 ---------------------------------------------------------------------------------------------------------------------
echo "--- S5: no group accounts at all"
reset; rmdir "$ROOT/group_accounts"
OUT=$(run_fn)
row "S5 no group_accounts directory: RC=0, no call, no error text from a glob that matched nothing" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && [ "$(calls)" -eq 0 ] && ! printf '%s' "$OUT" | grep -q -i -E 'no such|cannot|\*' && echo yes)")" "$OUT"
reset; mkdir -p "$ROOT/group_accounts"
OUT=$(run_fn)
row "S5b an empty group_accounts directory: the same" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && [ "$(calls)" -eq 0 ] && echo yes)")" "$OUT"

# ---- T. static ----------------------------------------------------------------------------------------------------------------
echo "--- T: static"
CALLS=$(grep -c '^    repair_group_account_files "\$ACCT_PATH"$' "$INST")
row "T1 the installer calls it exactly once, as repair_group_account_files \"\$ACCT_PATH\"" "$(ok "$([ "$CALLS" -eq 1 ] && echo yes)")" "calls found: $CALLS"
START=$(grep -n '^if \[ "\$accounts_kept" = yes \]; then$' "$INST" | head -1 | cut -d: -f1)
CALLN=$(grep -n '^    repair_group_account_files "\$ACCT_PATH"$' "$INST" | head -1 | cut -d: -f1)
EDITN=$(grep -n 'upgrade_editgates' "$INST" | grep -v '^[0-9]*:#' | tail -1 | cut -d: -f1)
ENDN=$(awk -v s="${START:-0}" 'NR>s && /^fi$/{print NR; exit}' "$INST")
row "T2 the call is inside the kept-accounts block, after the edit-gates walk (so the register is the finished one)" \
    "$(ok "$([ -n "$START" ] && [ -n "$CALLN" ] && [ -n "$EDITN" ] && [ -n "$ENDN" ] && [ "$CALLN" -gt "$EDITN" ] && [ "$CALLN" -lt "$ENDN" ] && [ "$CALLN" -gt "$START" ] && echo yes)")" "block $START-$ENDN, edit gates $EDITN, call $CALLN"
row "T3 the function names exactly the four files: voc/%0 voc/%1 \$hold.dic/%0 \$hold.dic/%1" \
    "$(ok "$(printf '%s\n' "$FUNC" | grep -q -F "for rel in voc/%0 voc/%1 '\$hold.dic/%0' '\$hold.dic/%1'; do" && echo yes)")" "$(printf '%s\n' "$FUNC" | grep 'for rel')"
row "T4 it changes owners only through the helper: no bare 'chown' command in the function" "$(ok "$(! printf '%s\n' "$FUNC" | grep -v '^ *#' | grep -q -E '(^|[ ;])chown ' && echo yes)")" "$(printf '%s\n' "$FUNC" | grep -n chown)"

echo
echo "test-install-groupfiles: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
