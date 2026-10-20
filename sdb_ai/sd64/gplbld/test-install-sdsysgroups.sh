#!/bin/bash
#
# test-install-sdsysgroups.sh - the installer's walk that puts the sdsys user in the group of every account and makes each account's VOC and
# dictionaries writable by that group (S.67 stage 2, D7; owner 17 Oct 2026, warned).  The function is join_sdsys_groups.
#
#   bash /home/don/Projects/SDCore4Linux-wt-s67/sdb_ai/sd64/gplbld/test-install-sdsysgroups.sh
#   bash /home/don/Projects/SDCore4Linux-wt-s67/sdb_ai/sd64/gplbld/test-install-sdsysgroups.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-sdsysgroups.sh        (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd-elevate (a stub script), no groups made or changed, no root.  Everything
# happens in a scratch directory.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing piece,
# a scenario in which the stub was never called, is exit 2).
#
# WHAT IT RUNS.  The function join_sdsys_groups is cut out of the installer; every "/home/sd/" in it is rewritten to the scratch directory and
# "/usr/local/sbin/sd-elevate" to the stub; it runs under the installer's OWN "set -euo pipefail" AND ITS IFS (IFS=$'\n\t' - the first real
# install of the gates question failed because a list was one word under that IFS and the test had run under `set` alone), with `sudo` a
# function that runs its arguments, `getent` a function that reads a fixture /etc/group, and `stat -c %G` answering from a file beside the
# directory (a real directory's group cannot be sdu_alice here).  The stub sd-elevate logs every call and does what the scenario says: join,
# refuse, make a change, find nothing to change, exit 0 and say nothing.
#
# THE SCENARIO (the register is a directory of records, line 1 the path, line 3 the group, as the real one):
#   alice  user account, sdu_alice without sdsys            -> joined, modes changed
#   bob    user account, sdu_bob WITH sdsys                 -> not joined again, modes already right
#   carol  user account, the join is refused                -> counted, named in the WARNING; her modes are still made right
#   dave   user account, group-write is refused             -> WARNING
#   fred   user account, group-write exits 0 and prints no success line -> NOT "made right" (judged on the success line, not the exit status)
#   team   group account sdg_team, directory group sdg_team -> modes only, NO join (a group account's group is made with sdsys in it)
#   shared group account, register group sdg_shared, the directory's group sdusers -> neither (the S.66 account is left as it is)
#   other  user account whose path is outside /home/sd      -> joined, modes NOT asked for (a path outside the accounts root)
#   sdsys  the administrator's own record                   -> nothing
#   "bad name", UPPER, %0, .hidden                          -> skipped by name
#
# NOT MEASURED HERE, and said so: that sd-elevate really adds sdsys to a group or changes a mode (test-sd-elevate.py, test-accelevate-units.py
# measure its rules; the real change is witness-masters.sh's); that the register directory at the point of the install holds what the
# scenario holds; that sudo works.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, sed expression (applied to the whole installer; the expressions name lines of the function or of its call)
    local name="$1" expr="$2" f="$T/$1.sh" rc
    total=$((total+1))
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -12 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant joins-group-accounts-too   '/^join_sdsys_groups() {/,/^}/ s/^            sdu_?\*)$/            sdu_?*|sdg_?*)/'
  mutant joins-again-when-member    '/^join_sdsys_groups() {/,/^}/ s/\*",sdsys,"\*) n_have/*",nobody,"*) n_have/'
  mutant modes-of-shared-too        '/^join_sdsys_groups() {/,/^}/ s/\[ "\$dir_group" = "\$group" \]/true/'
  mutant modes-outside-the-root     '/^join_sdsys_groups() {/,/^}/ s#/home/sd/user_accounts/\*|/home/sd/group_accounts/\*)#*)#'
  mutant silent-success-counts      "/^join_sdsys_groups() {/,/^}/ s/\*'group-write: '\*' file(s) changed, '\*)/*)/"
  mutant join-failure-aborts        '/^join_sdsys_groups() {/,/^}/ s/sdsys-join "\$group" 2>&1) || rc=\$?/sdsys-join "$group" 2>\&1)/'
  mutant modes-failure-aborts       '/^join_sdsys_groups() {/,/^}/ s/group-write "\$path" 2>&1) || rc=\$?/group-write "$path" 2>\&1)/'
  mutant warning-never              '/^join_sdsys_groups() {/,/^}/ s/if \[ "\$n_fail" -gt 0 \] || \[ "\$n_fixfail" -gt 0 \]; then/if false; then/'
  mutant names-not-filtered         "/^join_sdsys_groups() {/,/^}/ s/^            ''|\\.\\*|%\\*|\\*\\[!a-z0-9\\._-\\]\\*) continue ;;\$/            ''|.*) continue ;;/"
  mutant group-from-the-wrong-line  "/^join_sdsys_groups() {/,/^}/ s/sed -n '3p'/sed -n '2p'/"
  mutant path-from-the-wrong-line   "/^join_sdsys_groups() {/,/^}/ s/sed -n '1p'/sed -n '2p'/"
  mutant modes-of-the-wrong-path    '/^join_sdsys_groups() {/,/^}/ s#sd-elevate group-write "\$path"#sd-elevate group-write "$reg_dir/$rec"#'
  mutant join-of-the-wrong-group    '/^join_sdsys_groups() {/,/^}/ s#sd-elevate sdsys-join "\$group"#sd-elevate sdsys-join "$rec"#'
  mutant directory-group-by-owner   "/^join_sdsys_groups() {/,/^}/ s/stat -c '%G'/stat -c '%U'/"
  mutant names-with-paths           "/^join_sdsys_groups() {/,/^}/ s/-printf '%f\\\\n'/-printf '%p\\\\n'/"
  mutant function-exits             '/^join_sdsys_groups() {/,/^}/ s/^    echo "  sdsys put in the group of /    exit 1; echo "  sdsys put in the group of /'
  mutant no-notice                  '/^join_sdsys_groups() {/,/^}/{/write access to those files in every account/d}'
  mutant any-group-name-joins       '/^join_sdsys_groups() {/,/^}/ s/^            sdu_?\*)$/            *)/'
  mutant function-never-called      's/^join_sdsys_groups "\$sdsysdir\/accounts"$/true/'
  mutant called-with-the-wrong-dir  's/^join_sdsys_groups "\$sdsysdir\/accounts"$/join_sdsys_groups "\/home\/sd\/accounts"/'
  mutant called-after-the-masters   '/^join_sdsys_groups "\$sdsysdir\/accounts"$/d;/^echo "account register: /a join_sdsys_groups "$sdsysdir/accounts"'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
FUNC=$(awk '/^join_sdsys_groups\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$IFSL" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no IFS line in the installer"; exit 2; }
[ -z "$FUNC" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no function join_sdsys_groups in the installer (nothing to check)"; exit 2; }
echo "function  : $(printf '%s\n' "$FUNC" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
FUNC_T=$(printf '%s\n' "$FUNC" | sed -e "s#/home/sd/#$T/home/sd/#g" -e "s#/usr/local/sbin/sd-elevate#$T/bin/sd-elevate#g")
printf '%s\n' "$FUNC_T" | grep -q -F "$T/bin/sd-elevate" || { echo "test-install-sdsysgroups: CANNOT RUN - the function does not call sd-elevate"; exit 2; }

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# ---- the stub sd-elevate -------------------------------------------------------------------------------------------------
mkdir -p "$T/bin"
cat > "$T/bin/sd-elevate" <<'STUB'
#!/bin/bash
echo "$*" >> "$T/calls.log"
verb=${1:-}; shift
case $verb in
  sdsys-join)
    grp=${1:-}
    if grep -qxF "$grp" "$T/stub-join-fail" 2>/dev/null; then echo "sd-elevate: REFUSED - stub: no for $grp" >&2; exit 2; fi
    sed -i -e "s/^\($grp:[^:]*:[^:]*:\)\(.*\)\$/\1\2,sdsys/" "$T/etc/group"
    echo "sd-elevate: usermod -aG $grp -- sdsys"; exit 0 ;;
  group-write)
    p=${1:-}
    if grep -qxF "$p" "$T/stub-gw-fail" 2>/dev/null; then echo "sd-elevate: REFUSED - stub: no for $p" >&2; exit 2; fi
    if grep -qxF "$p" "$T/stub-gw-silent" 2>/dev/null; then echo "sd-elevate: group-write $p (group x, gid 1; owners uid 1)"; exit 0; fi
    if grep -qxF "$p" "$T/stub-gw-clean" 2>/dev/null; then echo "sd-elevate: group-write: 0 directories and 0 file(s) changed, 5 already right, 0 skipped"; exit 0; fi
    echo "sd-elevate: group-write: 2 directories and 4 file(s) changed, 0 already right, 1 skipped"; exit 0 ;;
esac
exit 3
STUB
chmod +x "$T/bin/sd-elevate"

# ---- the fixture ---------------------------------------------------------------------------------------------------------
UA="$T/home/sd/user_accounts"; GA="$T/home/sd/group_accounts"
reg() {   # reg NAME PATH GROUP [DIRGROUP]  - a register record (line 1 path, line 2 blank, line 3 group) and the directory
  mkdir -p "$T/reg"
  printf '%s\n\n%s\n' "$2" "$3" > "$T/reg/$1"
  if [ -n "${4:-}" ]; then mkdir -p "$2"; printf '%s\n' "$4" > "$2.group"; fi
}
build() {   # build SCENARIO: full | small | empty
  rm -rf "$T/reg" "$T/home" "$T/etc" "$T/calls.log" "$T"/stub-*
  mkdir -p "$UA" "$GA" "$T/etc" "$T/reg"
  : > "$T/calls.log"
  case "$1" in
    empty) ;;
    small)
      reg alice "$UA/alice" sdu_alice sdu_alice
      reg bob "$UA/bob" sdu_bob sdu_bob
      reg team "$GA/team" sdg_team sdg_team
      printf 'sdu_alice:x:2001:alice\nsdu_bob:x:2002:bob,sdsys\nsdg_team:x:2003:sdsys,root\n' > "$T/etc/group"
      printf '%s\n' "$UA/bob" > "$T/stub-gw-clean"
      ;;
    full)
      reg alice "$UA/alice" sdu_alice sdu_alice
      reg bob "$UA/bob" sdu_bob sdu_bob
      reg carol "$UA/carol" sdu_carol sdu_carol
      reg dave "$UA/dave" sdu_dave sdu_dave
      reg fred "$UA/fred" sdu_fred sdu_fred
      reg team "$GA/team" sdg_team sdg_team
      reg shared "$GA/shared" sdg_shared sdusers
      reg other "$T/srv/other" sdu_other sdu_other
      reg sdsys "$T/usr/local/sdsys" ""
      reg "bad name" "$UA/badname" sdu_badname sdu_badname
      reg UPPER "$UA/upper" sdu_upper sdu_upper
      reg "%0" "$UA/pct" sdu_pct sdu_pct
      reg .hidden "$UA/hidden" sdu_hidden sdu_hidden
      printf 'sdu_alice:x:2001:alice\nsdu_bob:x:2002:bob,sdsys\nsdu_carol:x:2003:carol\nsdu_dave:x:2004:dave\nsdu_fred:x:2005:fred\nsdg_team:x:2006:sdsys,root\nsdg_shared:x:2007:sdsys,root\nsdu_other:x:2008:other\nsdu_badname:x:2009:x\nsdu_upper:x:2010:x\nsdu_pct:x:2011:x\nsdu_hidden:x:2012:x\n' > "$T/etc/group"
      printf '%s\n' "sdu_carol" > "$T/stub-join-fail"
      printf '%s\n' "$UA/dave" > "$T/stub-gw-fail"
      printf '%s\n' "$UA/fred" > "$T/stub-gw-silent"
      printf '%s\n' "$UA/bob" > "$T/stub-gw-clean"
      ;;
  esac
}
run_fn() {   # run_fn  - prints the function's output, then  AFTER rc=<n>  (the line after the call: reached only if the function did not stop the shell)
  OPTS="$OPTS" IFSL="$IFSL" FUNC_T="$FUNC_T" T="$T" bash -c '
      eval "$OPTS"
      eval "$IFSL"
      RED=; NC=
      sudo() { "$@"; }
      getent() { if [ "$1" = group ]; then grep -m1 "^$2:" "$T/etc/group" || return 2; else return 2; fi; }
      stat() { if [ "${1:-}" = -c ] && [ "${2:-}" = "%G" ] && [ -f "${3:-}.group" ]; then cat "$3.group"; else command stat "$@"; fi; }
      export T
      eval "$FUNC_T"
      join_sdsys_groups "$T/reg"
      echo "AFTER rc=$?"' 2>&1
}
calls() { cat "$T/calls.log"; }
has_call() { calls | grep -q -x -F -- "$1" && echo yes; }

# ---- the full scenario ----------------------------------------------------------------------------------------------------------
build full
OUT=$(run_fn)
echo "--- the full scenario, output:"; printf '%s\n' "$OUT" | sed -e 's/^/      /'
echo "--- its calls:"; calls | sed -e 's/^/      /'
[ "$(calls | wc -l)" -ge 8 ] || { echo "test-install-sdsysgroups: CANNOT RUN - the stub was called $(calls | wc -l) times; the function did not do the walk"; exit 2; }

echo "--- A: who is put in a group"
for g in sdu_alice sdu_dave sdu_fred sdu_other; do
  row "A1 sdsys-join $g was asked for (the group lacks sdsys)" "$(ok "$(has_call "sdsys-join $g")")" "calls: $(calls | tr '\n' ';')"
done
row "A2 sdsys-join sdu_carol was asked for and its refusal did not stop the walk (her modes were asked for after it)" \
    "$(ok "$(has_call 'sdsys-join sdu_carol' | grep -q yes && has_call "group-write $UA/carol" | grep -q yes && echo yes)")" "calls: $(calls | tr '\n' ';')"
row "A3 sdu_bob already lists sdsys: NOT asked for again" "$(ok "$([ -z "$(has_call 'sdsys-join sdu_bob')" ] && echo yes)")" "calls: $(calls | tr '\n' ';')"
row "A4 a group account's group (sdg_team, sdg_shared) is NEVER joined: sdsys is in it from the day it was made" \
    "$(ok "$([ -z "$(calls | grep -E 'sdsys-join sdg_')" ] && echo yes)")" "calls: $(calls | tr '\n' ';')"
row "A5 only sdu_ groups are ever asked for, and only by the verb sdsys-join: every sdsys-join call is  sdsys-join sdu_<name>  and the groups are exactly alice carol dave fred other" \
    "$(ok "$([ "$(calls | grep '^sdsys-join' | sort | tr '\n' ' ')" = "sdsys-join sdu_alice sdsys-join sdu_carol sdsys-join sdu_dave sdsys-join sdu_fred sdsys-join sdu_other " ] && echo yes)")" "calls: $(calls | grep '^sdsys-join' | sort | tr '\n' ';')"
echo "--- B: whose modes are asked for"
for a in alice bob carol dave fred; do
  row "B1 group-write was asked for $a's directory (its group is the register's group)" "$(ok "$(has_call "group-write $UA/$a")")" "calls: $(calls | tr '\n' ';')"
done
row "B2 group-write was asked for the group account team (directory group sdg_team = register group)" "$(ok "$(has_call "group-write $GA/team")")" "calls: $(calls | tr '\n' ';')"
row "B3 NOT for shared (register sdg_shared, directory group sdusers: S.66's account is left as it is)" "$(ok "$([ -z "$(has_call "group-write $GA/shared")" ] && echo yes)")" "calls: $(calls | tr '\n' ';')"
row "B4 NOT for an account whose path is outside /home/sd (other), nor sdsys's own record" \
    "$(ok "$([ -z "$(calls | grep -E "group-write ($T/srv|$T/usr)")" ] && echo yes)")" "calls: $(calls | tr '\n' ';')"
row "B5 only group-write calls with a directory directly under user_accounts or group_accounts, and exactly alice bob carol dave fred team" \
    "$(ok "$([ "$(calls | grep '^group-write' | sort | tr '\n' ' ')" = "group-write $GA/team group-write $UA/alice group-write $UA/bob group-write $UA/carol group-write $UA/dave group-write $UA/fred " ] && echo yes)")" "calls: $(calls | grep '^group-write' | sort | tr '\n' ';')"
echo "--- C: names the walk skips"
row "C1 'bad name', UPPER, %0 and .hidden are skipped by name: no call mentions badname, upper, pct or hidden" \
    "$(ok "$([ -z "$(calls | grep -E 'badname|upper|pct|hidden')" ] && echo yes)")" "calls: $(calls | tr '\n' ';')"
echo "--- D: what it says"
row "D1 it says plainly what the membership gives: write access to those files in every account" "$(ok "$(printf '%s' "$OUT" | grep -q 'write access to those files in every account' && echo yes)")" "$OUT"
row "D2 it says each join that was made (alice) and each that was not (carol)" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'sdsys is now in the group sdu_alice' && printf '%s' "$OUT" | grep -q 'sdsys could not be put in sdu_carol' && echo yes)")" "$OUT"
row "D3 the summary counts: put in the group of 4 (alice dave fred other), in it already 1 (bob); modes made right for 3 (alice carol team), right already 1 (bob), left as they are 1 (shared)" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'sdsys put in the group of 4 account(s); it was in 1 already.  Modes made right for 3 account(s); 1 were right already; 1 left as they are' && echo yes)")" "$OUT"
row "D4 a refused group-write (dave) is named" "$(ok "$(printf '%s' "$OUT" | grep -q 'the VOC and dictionaries of dave could not be made group-writable' && echo yes)")" "$OUT"
row "D5 a group-write that exits 0 and does NOT print its success line (fred) is not 'made right': it is named, and the summary does not count it" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'fred: sd-elevate group-write did not say what it did' && echo yes)")" "$OUT"
row "D6 the WARNING appears with the counts (1 group without sdsys, 2 accounts whose modes were not changed) and the commands that repair it" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'WARNING: SDSYS cannot yet write master edits into every account: 1 group(s) without sdsys, 2 account(s) whose modes were not changed' && printf '%s' "$OUT" | grep -q 'sd-elevate sdsys-join <group>' && printf '%s' "$OUT" | grep -q 'sd-elevate group-write .*/home/sd/user_accounts/<account>' && echo yes)")" "$OUT"
row "D7 the shell was NOT stopped by any of it: the line after the call ran, with status 0 (a failure is reported and the install goes on)" "$(ok "$(printf '%s' "$OUT" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUT"

# ---- the all-good scenario -------------------------------------------------------------------------------------------------------
build small
OUT2=$(run_fn)
echo "--- the small scenario (nothing wrong), output:"; printf '%s\n' "$OUT2" | sed -e 's/^/      /'
[ "$(calls | wc -l)" -ge 3 ] || { echo "test-install-sdsysgroups: CANNOT RUN - the small scenario made $(calls | wc -l) calls"; exit 2; }
echo "--- E: when nothing is wrong"
row "E1 no WARNING, and the summary counts one join (alice), one already (bob), modes made right for 2 (alice, team), one already right (bob)" \
    "$(ok "$(! printf '%s' "$OUT2" | grep -q WARNING && printf '%s' "$OUT2" | grep -q 'sdsys put in the group of 1 account(s); it was in 1 already.  Modes made right for 2 account(s); 1 were right already; 0 left as they are' && echo yes)")" "$OUT2"
row "E2 the calls are exactly: join alice; modes of alice, bob and team" \
    "$(ok "$([ "$(calls | sort | tr '\n' ' ')" = "group-write $GA/team group-write $UA/alice group-write $UA/bob sdsys-join sdu_alice " ] && echo yes)")" "calls: $(calls | sort | tr '\n' ';')"
row "E3 the shell went on (AFTER rc=0)" "$(ok "$(printf '%s' "$OUT2" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUT2"

# ---- the register is empty -------------------------------------------------------------------------------------------------------
build empty
OUT3=$(run_fn)
row "F1 an empty register: no call, no WARNING, the shell goes on - and the summary says 0 and 0" \
    "$(ok "$([ ! -s "$T/calls.log" ] && ! printf '%s' "$OUT3" | grep -q WARNING && printf '%s' "$OUT3" | grep -q 'put in the group of 0 account(s); it was in 0 already' && printf '%s' "$OUT3" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUT3"

# ---- static ----------------------------------------------------------------------------------------------------------------------
echo "--- S: static"
CALLS_IN_FN=$(printf '%s\n' "$FUNC" | grep -c 'sd-elevate')
row "S1 the function calls sd-elevate with two verbs only (sdsys-join and group-write) and by its full path" \
    "$(ok "$(printf '%s\n' "$FUNC" | grep -o 'sbin/sd-elevate [a-z-]*' | sort -u | tr '\n' ' ' | grep -q -x -F 'sbin/sd-elevate group-write sbin/sd-elevate sdsys-join ' && echo yes)")" "$(printf '%s\n' "$FUNC" | grep -o 'sbin/sd-elevate [a-z-]*' | sort -u | tr '\n' ' ')"
row "S2 the function never exits the install (no exit, no return 1)" "$(ok "$(printf '%s\n' "$FUNC" | grep -E '(^|[^a-z_])(exit|return 1)([^a-z_]|$)' | grep -v '^ *#' | grep -q . || echo yes)")" ""
LINE_CALL=$(grep -n -x 'join_sdsys_groups "\$sdsysdir/accounts"' "$INST" | cut -d: -f1)
LINE_EDIT=$(grep -n 'RUN gpl.bp upgrade_editgates' "$INST" | head -1 | cut -d: -f1)
LINE_MASTERS=$(grep -n 'RUN gpl.bp upgrade_masters' "$INST" | head -1 | cut -d: -f1)
row "S3 the walk is called once, with the live register, after the edit gates are kept and BEFORE the master files are filled" \
    "$(ok "$([ "$(grep -c -x 'join_sdsys_groups "\$sdsysdir/accounts"' "$INST")" = 1 ] && [ -n "$LINE_CALL" ] && [ -n "$LINE_EDIT" ] && [ -n "$LINE_MASTERS" ] && [ "$LINE_EDIT" -lt "$LINE_CALL" ] && [ "$LINE_CALL" -lt "$LINE_MASTERS" ] && echo yes)")" "edit=$LINE_EDIT call=$LINE_CALL masters=$LINE_MASTERS"

echo
echo "test-install-sdsysgroups: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
