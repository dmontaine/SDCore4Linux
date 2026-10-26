#!/bin/bash
#
# test-install-sdsysgroups.sh - the installer's ruling on the sdsys user's place in the groups of the user accounts (F6, S.67 stage 2, alternative C; 26 Oct 26).
# The question is the block between SDSYSGROUPS-ASK-BEGIN and SDSYSGROUPS-ASK-END; the act is the function sdsys_groups_ruling.  (Before 26 Oct this file held
# the walk join_sdsys_groups, which put the sdsys user in EVERY user account's group; the owner's D7 of 17 Oct, replaced because the core direction is that high
# security is delivered and the administrator loosens it later.  Its rows are gone with it.)
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysgroups.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysgroups.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-sdsysgroups.sh        (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd-elevate (a stub script), no groups made or changed, no root.  Everything happens in a scratch
# directory.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing piece, a scenario in which the stub was never
# called, is exit 2).
#
# WHAT IT RUNS.  The block and the function are cut out of the installer; every "/home/sd/" in them is rewritten to the scratch directory and
# "/usr/local/sbin/sd-elevate" to the stub; they run under the installer's OWN "set -euo pipefail" AND ITS IFS (IFS=$'\n\t' - the first real install of the gates
# question failed because a list was one word under that IFS and the test had run under `set` alone), with `sudo` a function that runs its arguments, `chown` a
# function that logs (the scratch machine has no sdsys user) and `getent` a function that reads a fixture /etc/group.  The stub sd-elevate logs every call and
# does what the scenario says: take the sdsys user out of the group, refuse, say it was not in it, exit 0 and say nothing.
#
# THE SCENARIO (the groups are the fixture /etc/group; the question counts the user-account groups that list sdsys):
#   sdu_alice  lists sdsys          -> asked about, taken out
#   sdu_bob    does not             -> never touched
#   sdu_carol  lists sdsys, the helper refuses it   -> counted, named in the WARNING, the walk goes on, the marker is NOT written
#   sdu_dave   lists sdsys among others (root,dave,sdsys)  -> taken out
#   sdu_eve    lists "sdsys2"       -> not sdsys: untouched (a whole name, not a prefix)
#   sdu_fred   lists "xsdsys"       -> not sdsys: untouched
#   sdg_team   a group account's group, lists sdsys   -> NEVER touched (sdsys owns the files of a group account)
#   sdusers    lists sdsys          -> never touched (not an account's group)
#
# NOT MEASURED HERE, and said so: that sd-elevate really takes a user out of a group (test-sd-elevate.py measures its rules; the real change is witness-masters.sh's);
# that the marker is where a kept install keeps it, which is the position of /home/sd in a delete that keeps the accounts (the VM); that sudo works; that the
# prompt is shown on a terminal (bash prints a read prompt only when the input is a terminal, so the rows read the answer, not the prompt).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, sed expression (applied to the whole installer; the expressions name lines of the block, the function or the call)
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
  A='/^# SDSYSGROUPS-ASK-BEGIN$/,/^# SDSYSGROUPS-ASK-END$/'
  F='/^sdsys_groups_ruling() {/,/^}/'
  # ---- the question
  mutant asks-with-the-marker-present  "$A s#^if \[ ! -e \"/home/sd/\\\\\$groups.ruled\" \]; then#if true; then#"
  mutant default-is-keep               "$A s/^sdsys_keep=n\$/sdsys_keep=y/"
  mutant no-answer-is-keep             "$A s/echo \"No answer could be read: N.\"; sdsys_ans=n;/echo \"No answer could be read.\"; sdsys_ans=y;/"
  mutant any-answer-keeps              "$A s/case \$sdsys_ans in \[yY\]|\[yY\]\[eE\]\[sS\] ) sdsys_keep=y;; esac/sdsys_keep=y/"
  mutant question-counts-group-accounts "$A s/\\^sdu_\\./^sd[ug]_./"
  mutant question-counts-a-prefix      "$A s#/,sdsys,/#/sdsys/#"
  mutant question-reads-the-wrong-field "$A s/(\",\" \$4 \",\")/(\",\" \$3 \",\")/"
  mutant question-never-asks           "$A s/^if \[ -n \"\$sdsys_listed\" \]; then\$/if false; then/"
  mutant question-reads-no-input       "$A s/^    read -r -p .*\$/    sdsys_ans=n/"
  # ---- the act
  mutant keep-is-ignored               "$F s/^    elif \[ \"\$keep\" = y \]; then\$/    elif false; then/"
  mutant leaves-with-the-marker        "$F s/^    if \[ -e \"\$marker\" \]; then\$/    if false; then/"
  mutant counts-group-accounts         "$F s/\\^sdu_\\./^sd[ug]_./"
  mutant counts-a-prefix               "$F s#/,sdsys,/#/sdsys/#"
  mutant exit-status-only              "$F s#0:\\*\"gpasswd -d sdsys \\\${group}\"\\*|0:\\*\"sdsys is not in \\\${group}\"\\*)#0:*)#"
  mutant failure-aborts                "$F s/sdsys-leave \"\\\$group\" 2>&1) || rc=\\\$?/sdsys-leave \"\$group\" 2>\\&1)/"
  mutant wrong-verb                    "$F s#sd-elevate sdsys-leave \"\\\$group\"#sd-elevate sdsys-join \"\$group\"#"
  mutant warning-never                 "$F s/^        if \[ \"\\\$n_fail\" -gt 0 \]; then\$/        if false; then/"
  mutant marker-after-a-failure        "$F { /^            return 0\$/d; }"
  mutant marker-never-written          "$F { /^    sudo touch \"\\\$marker\"\$/d; }"
  mutant marker-not-handed-to-sdsys    "$F { /^    sudo chown sdsys:sdusers \"\\\$marker\"\$/d; }"
  mutant marker-mode-open              "$F s/^    sudo chmod 644 \"\\\$marker\"\$/    sudo chmod 666 \"\$marker\"/"
  mutant function-exits                "$F s/^        echo \"  The sdsys user was taken out of the group of /        exit 1; echo \"  The sdsys user was taken out of the group of /"
  # ---- the call
  mutant function-never-called         's/^sdsys_groups_ruling "\$ACCT_PATH\/\\$groups.ruled" "\$sdsys_keep"$/true/'
  mutant marker-in-the-sdsys-directory 's/^sdsys_groups_ruling "\$ACCT_PATH\/\\$groups.ruled"/sdsys_groups_ruling "$sdsysdir\/\\$groups.ruled"/'
  mutant called-with-the-wrong-answer  's/^sdsys_groups_ruling "\$ACCT_PATH\/\\$groups.ruled" "\$sdsys_keep"$/sdsys_groups_ruling "$ACCT_PATH\/\\$groups.ruled" y/'
  mutant called-after-the-masters      '/^sdsys_groups_ruling "\$ACCT_PATH\/\\$groups.ruled" "\$sdsys_keep"$/d;/^echo "account register: /a sdsys_groups_ruling "$ACCT_PATH/\\$groups.ruled" "$sdsys_keep"'
  mutant the-old-walk-is-back          's/^echo "Ruling on the sdsys user.s place in the groups of the user accounts."$/echo "x"; sudo \/usr\/local\/sbin\/sd-elevate sdsys-join sdu_x/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
ASK=$(awk '/^# SDSYSGROUPS-ASK-BEGIN$/{f=1;next} /^# SDSYSGROUPS-ASK-END$/{f=0} f{print}' "$INST")
FUNC=$(awk '/^sdsys_groups_ruling\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$IFSL" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no IFS line in the installer"; exit 2; }
[ -z "$ASK" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no SDSYSGROUPS-ASK block in the installer (nothing to check)"; exit 2; }
[ -z "$FUNC" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no function sdsys_groups_ruling in the installer (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$ASK" | wc -l) lines     function  : $(printf '%s\n' "$FUNC" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
rewrite() { sed -e "s#/home/sd/#$T/home/sd/#g" -e "s#/usr/local/sbin/sd-elevate#$T/bin/sd-elevate#g"; }
ASK_T=$(printf '%s\n' "$ASK" | rewrite)
FUNC_T=$(printf '%s\n' "$FUNC" | rewrite)
printf '%s\n' "$ASK_T" | grep -q -F "$T/home/sd/" || { echo "test-install-sdsysgroups: CANNOT RUN - the question does not look at the marker in /home/sd"; exit 2; }
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
  sdsys-leave)
    grp=${1:-}
    if grep -qxF "$grp" "$T/stub-leave-fail" 2>/dev/null; then echo "sd-elevate: REFUSED - stub: no for $grp" >&2; exit 2; fi
    if grep -qxF "$grp" "$T/stub-leave-silent" 2>/dev/null; then echo "sd-elevate: stub did something"; exit 0; fi
    if grep -qxF "$grp" "$T/stub-leave-notin" 2>/dev/null; then echo "sd-elevate: sdsys is not in $grp"; exit 0; fi
    sed -i -e "/^$grp:/ { s/,sdsys\$//; s/:sdsys,/:/; s/,sdsys,/,/; s/:sdsys\$/:/ }" "$T/etc/group"
    echo "sd-elevate: gpasswd -d sdsys $grp"; exit 0 ;;
esac
exit 3
STUB
chmod +x "$T/bin/sd-elevate"

# ---- the fixture ---------------------------------------------------------------------------------------------------------
MARKER="$T/home/sd/\$groups.ruled"
build() {   # build SCENARIO: kept | quiet | fresh
  rm -rf "$T/home" "$T/etc" "$T/calls.log" "$T/chown.log" "$T"/stub-*
  mkdir -p "$T/home/sd" "$T/etc"
  : > "$T/calls.log"; : > "$T/chown.log"
  case "$1" in
    empty)
      : > "$T/etc/group"
      ;;
    kept)
      printf 'sdusers:x:100:root,sdsys,alice,bob\nsdu_alice:x:2001:alice,sdsys\nsdu_bob:x:2002:bob\nsdu_carol:x:2003:carol,sdsys\nsdu_dave:x:2004:root,dave,sdsys\nsdu_eve:x:2005:eve,sdsys2\nsdu_fred:x:2006:xsdsys\nsdg_team:x:2007:sdsys,root\n' > "$T/etc/group"
      printf '%s\n' "sdu_carol" > "$T/stub-leave-fail"
      ;;
    kept-clean)
      printf 'sdusers:x:100:root,sdsys,alice,bob\nsdu_alice:x:2001:alice,sdsys\nsdu_bob:x:2002:bob\nsdu_carol:x:2003:carol,sdsys\nsdu_dave:x:2004:root,dave,sdsys\nsdu_eve:x:2005:eve,sdsys2\nsdu_fred:x:2006:xsdsys\nsdg_team:x:2007:sdsys,root\n' > "$T/etc/group"
      ;;
    quiet|fresh)
      printf 'sdusers:x:100:root,sdsys,alice,bob\nsdu_alice:x:2001:alice\nsdu_bob:x:2002:bob\nsdu_eve:x:2005:eve,sdsys2\nsdu_fred:x:2006:xsdsys\nsdg_team:x:2007:sdsys,root\n' > "$T/etc/group"
      ;;
  esac
}
HARNESS='
      eval "$OPTS"
      eval "$IFSL"
      RED=; NC=
      sudo() { "$@"; }
      getent() { if [ "$1" = group ]; then if [ -n "${2:-}" ]; then grep -m1 "^$2:" "$T/etc/group" || return 2; else cat "$T/etc/group"; fi; else return 2; fi; }
      chown() { { printf "chown"; printf " %s" "$@"; echo; } >> "$T/chown.log"; }     # not "$*": under the installer'"'"'s IFS that joins with a newline
      export T'
run_ask() {   # run_ask  (stdin = the answer)  - prints the block's output, then  KEEP=<y|n> LISTED=<names>
  OPTS="$OPTS" IFSL="$IFSL" ASK_T="$ASK_T" T="$T" bash -c "$HARNESS"'
      eval "$ASK_T"
      echo "KEEP=$sdsys_keep LISTED=$(printf "%s" "$sdsys_listed" | tr "\n" " ")"' 2>&1
}
run_fn() {   # run_fn KEEP  - prints the function's output, then  AFTER rc=<n>  (the line after the call: reached only if the function did not stop the shell)
  OPTS="$OPTS" IFSL="$IFSL" FUNC_T="$FUNC_T" T="$T" KEEP="$1" MARKER="$MARKER" bash -c "$HARNESS"'
      eval "$FUNC_T"
      sdsys_groups_ruling "$MARKER" "$KEEP"
      echo "AFTER rc=$?"' 2>&1
}
calls() { cat "$T/calls.log"; }
has_call() { calls | grep -q -x -F -- "$1" && echo yes; }
members() { grep "^$1:" "$T/etc/group" | cut -d: -f4; }
marker_mode() { stat -c %a "$MARKER" 2>/dev/null; }

# ---- A: the question ----------------------------------------------------------------------------------------------------------
echo "--- A: the question (up front)"
build kept
OUTN=$(printf 'n\n' | run_ask)
echo "--- answered n, output:"; printf '%s\n' "$OUTN" | sed -e 's/^/      /'
row "A1 the groups that list sdsys are counted from /etc/group as WHOLE names, user-account groups only: alice carol dave (not eve's sdsys2, fred's xsdsys, the group account team, sdusers) - 3 account(s)" \
    "$(ok "$(printf '%s' "$OUTN" | grep -q 'group of 3 user account(s)' && printf '%s' "$OUTN" | grep -q 'LISTED=sdu_alice sdu_carol sdu_dave$' && echo yes)")" "$OUTN"
row "A2 it says what the membership gives, what is delivered now, that it is asked once, and what n does" \
    "$(ok "$(printf '%s' "$OUTN" | grep -q 'can write everything those groups may write' && printf '%s' "$OUTN" | grep -q 'in no user account.s group' && printf '%s' "$OUTN" | grep -q 'modify.account <account> sdsys-on' && printf '%s' "$OUTN" | grep -q 'asked once' && printf '%s' "$OUTN" | grep -q 'Answer n to take it out' && echo yes)")" "$OUTN"
row "A3 the answer n is NO: keep stays n" "$(ok "$(printf '%s' "$OUTN" | grep -q '^KEEP=n ' && echo yes)")" "$OUTN"
for a in y Y yes YES Yes; do
  row "A4 the answer '$a' is yes: keep=y (the answer was READ: a y that was not consumed would leave n)" "$(ok "$(printf '%s\n' "$a" | run_ask | grep -q '^KEEP=y ' && echo yes)")" "$(printf '%s\n' "$a" | run_ask)"
done
for a in "" N no maybe yy ' y' "yes please" 1; do
  row "A5 the answer '$a' is NO" "$(ok "$(printf '%s\n' "$a" | run_ask | grep -q '^KEEP=n ' && echo yes)")" "$(printf '%s\n' "$a" | run_ask)"
done
OUTE=$(run_ask < /dev/null)
row "A6 NO INPUT AT ALL (a closed or empty input, no terminal): the answer is N, said in a line, and the shell goes on (the block printed its result)" \
    "$(ok "$(printf '%s' "$OUTE" | grep -q 'No answer could be read: N.' && printf '%s' "$OUTE" | grep -q '^KEEP=n ' && echo yes)")" "$OUTE"
row "A7 the same through a pipe that ends with no line (printf '' |)" "$(ok "$(printf '' | run_ask | grep -q '^KEEP=n ' && echo yes)")" "$(printf '' | run_ask)"
: > "$MARKER"
OUTM=$(printf 'y\n' | run_ask)
row "A8 with the marker present nothing is asked and nothing is counted: the y that is fed is not read (KEEP stays n) and the question is not printed" \
    "$(ok "$(printf '%s' "$OUTM" | grep -q '^KEEP=n LISTED=$' && ! printf '%s' "$OUTM" | grep -q 'user account(s)' && echo yes)")" "$OUTM"
build quiet
OUTQ=$(printf 'y\n' | run_ask)
row "A9 when no user-account group lists sdsys (alice, bob, eve's sdsys2, fred's xsdsys, the group account, sdusers) nothing is asked: the y is not read, KEEP stays n" \
    "$(ok "$(printf '%s' "$OUTQ" | grep -q '^KEEP=n LISTED=$' && ! printf '%s' "$OUTQ" | grep -q 'user account(s)' && echo yes)")" "$OUTQ"
build empty
OUTZ=$(printf 'y\n' | run_ask)
row "A10 an empty /etc/group: nothing is asked, the block does not stop the shell" "$(ok "$(printf '%s' "$OUTZ" | grep -q '^KEEP=n LISTED=$' && echo yes)")" "$OUTZ"

# ---- B: the act, the owner said no (or nothing) -------------------------------------------------------------------------------
echo "--- B: the act, answer n (a helper refusal on carol)"
build kept
OUT=$(run_fn n)
echo "--- output:"; printf '%s\n' "$OUT" | sed -e 's/^/      /'
echo "--- its calls:"; calls | sed -e 's/^/      /'
[ "$(calls | wc -l)" -ge 3 ] || { echo "test-install-sdsysgroups: CANNOT RUN - the stub was called $(calls | wc -l) times; the function did not do the walk"; exit 2; }
for g in sdu_alice sdu_carol sdu_dave; do
  row "B1 sdsys-leave $g was asked for (the group lists sdsys)" "$(ok "$(has_call "sdsys-leave $g")")" "calls: $(calls | tr '\n' ';')"
done
row "B2 nothing else was asked for: not bob (lacks sdsys), not eve's sdsys2 nor fred's xsdsys, not the group account team, not sdusers - the calls are exactly alice carol dave, verb sdsys-leave" \
    "$(ok "$([ "$(calls | sort | tr '\n' ' ')" = "sdsys-leave sdu_alice sdsys-leave sdu_carol sdsys-leave sdu_dave " ] && echo yes)")" "calls: $(calls | sort | tr '\n' ';')"
row "B3 the groups were changed as the stub does: alice and dave no longer list sdsys, dave still lists root and dave, bob's, eve's, fred's, team's and sdusers' lists are as they were" \
    "$(ok "$([ "$(members sdu_alice)" = alice ] && [ "$(members sdu_dave)" = root,dave ] && [ "$(members sdu_bob)" = bob ] && [ "$(members sdu_eve)" = eve,sdsys2 ] && [ "$(members sdu_fred)" = xsdsys ] && [ "$(members sdg_team)" = sdsys,root ] && [ "$(members sdusers)" = root,sdsys,alice,bob ] && [ "$(members sdu_carol)" = carol,sdsys ] && echo yes)")" "$(cat "$T/etc/group" | tr '\n' ';')"
row "B4 each one is said: alice and dave 'no longer in the group', carol 'could not be taken out' with the helper's last line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'the sdsys user is no longer in the group sdu_alice' && printf '%s' "$OUT" | grep -q 'the sdsys user is no longer in the group sdu_dave' && printf '%s' "$OUT" | grep -q 'the sdsys user could not be taken out of sdu_carol: sd-elevate: REFUSED - stub: no for sdu_carol' && echo yes)")" "$OUT"
row "B5 the summary counts 2 of 3, and the WARNING names carol and the command that repairs it" \
    "$(ok "$(printf '%s' "$OUT" | grep -q 'taken out of the group of 2 of 3 account(s)' && printf '%s' "$OUT" | grep -q 'WARNING: the sdsys user is still in the group of 1 account(s): sdu_carol' && printf '%s' "$OUT" | grep -q 'sd-elevate sdsys-leave <group>' && echo yes)")" "$OUT"
row "B6 a refused group does NOT write the marker (running the installer again asks and tries again)" "$(ok "$([ ! -e "$MARKER" ] && [ ! -s "$T/chown.log" ] && echo yes)")" "marker: $(ls "$T/home/sd" | tr '\n' ' ') chown: $(cat "$T/chown.log")"
row "B7 the shell was NOT stopped by the refusal: the line after the call ran, with status 0" "$(ok "$(printf '%s' "$OUT" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUT"

echo "--- C: the act, answer n, nothing refused"
build kept-clean
OUTC=$(run_fn n)
row "C1 all three are taken out (alice carol dave) and no WARNING" \
    "$(ok "$(printf '%s' "$OUTC" | grep -q 'taken out of the group of 3 of 3 account(s)' && ! printf '%s' "$OUTC" | grep -q WARNING && [ "$(calls | wc -l)" = 3 ] && echo yes)")" "$OUTC"
row "C2 the marker is written: a file in /home/sd called \$groups.ruled, handed to sdsys:sdusers (chown asked for exactly that), mode 644" \
    "$(ok "$([ -e "$MARKER" ] && [ "$(marker_mode)" = 644 ] && [ "$(cat "$T/chown.log")" = "chown sdsys:sdusers $MARKER" ] && echo yes)")" "mode=$(marker_mode) chown: $(cat "$T/chown.log")"
row "C3 it says where the ruling was recorded" "$(ok "$(printf '%s' "$OUTC" | grep -q 'Recorded in .*groups.ruled' && echo yes)")" "$OUTC"
OUTC2=$(run_fn n);
row "C4 RUN AGAIN with the marker there it does nothing: no further call (still 3), the groups are as they were, and it says it was ruled on earlier" \
    "$(ok "$([ "$(calls | wc -l)" = 3 ] && printf '%s' "$OUTC2" | grep -q 'ruled on at an earlier install' && printf '%s' "$OUTC2" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTC2"
# an administrator turns it on for dave afterwards; the next install must not take it out again
sed -i -e 's/^sdu_dave:x:2004:root,dave$/sdu_dave:x:2004:root,dave,sdsys/' "$T/etc/group"
OUTC3=$(run_fn n)
row "C5 THE POINT OF THE MARKER: sdsys-on for dave after the ruling (the group lists sdsys again), then an install with the answer n and no tty: still no call, dave still lists sdsys" \
    "$(ok "$([ "$(calls | wc -l)" = 3 ] && [ "$(members sdu_dave)" = root,dave,sdsys ] && echo yes)")" "calls: $(calls | tr '\n' ';') members: $(members sdu_dave)"

echo "--- D: the act, answer y"
build kept
OUTY=$(run_fn y)
row "D1 the answer y changes NOTHING: no call, every group as it was, the marker written, and it says the sdsys user stays in 3 account(s)" \
    "$(ok "$([ ! -s "$T/calls.log" ] && [ "$(members sdu_alice)" = alice,sdsys ] && [ "$(members sdu_dave)" = root,dave,sdsys ] && [ -e "$MARKER" ] && printf '%s' "$OUTY" | grep -q 'stays in the group of 3 account(s), as you answered' && printf '%s' "$OUTY" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTY"
row "D2 the marker is written in that case too (so the next install does not ask again), owner sdsys:sdusers, mode 644" \
    "$(ok "$([ "$(marker_mode)" = 644 ] && [ "$(cat "$T/chown.log")" = "chown sdsys:sdusers $MARKER" ] && echo yes)")" "mode=$(marker_mode) chown: $(cat "$T/chown.log")"

echo "--- E: a fresh install, and one that finds the sdsys user in no group"
build fresh
OUTF=$(run_fn n)
row "E1 nothing lists sdsys: no call to the helper, the marker is written (a LATER sdsys-on stands), no WARNING, and it says the sdsys user is in no user account's group" \
    "$(ok "$([ ! -s "$T/calls.log" ] && [ -e "$MARKER" ] && ! printf '%s' "$OUTF" | grep -q WARNING && printf '%s' "$OUTF" | grep -q 'in no user account.s group, as delivered' && printf '%s' "$OUTF" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTF"
row "E2 the groups are as they were (the group account team and sdusers still list sdsys)" "$(ok "$([ "$(members sdg_team)" = sdsys,root ] && [ "$(members sdusers)" = root,sdsys,alice,bob ] && echo yes)")" "$(cat "$T/etc/group" | tr '\n' ';')"
build empty
OUTZ2=$(run_fn n)
row "E3 an empty /etc/group: the marker is written and nothing else happens" "$(ok "$([ -e "$MARKER" ] && [ ! -s "$T/calls.log" ] && printf '%s' "$OUTZ2" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTZ2"

echo "--- F: what the helper may answer"
build kept-clean
printf '%s\n' "sdu_alice" > "$T/stub-leave-silent"
printf '%s\n' "sdu_dave" > "$T/stub-leave-notin"
OUTS=$(run_fn n)
row "F1 exit 0 WITHOUT the command line or the 'not in' line (alice) is NOT 'taken out': named in the WARNING, no marker" \
    "$(ok "$(printf '%s' "$OUTS" | grep -q 'could not be taken out of sdu_alice' && printf '%s' "$OUTS" | grep -q 'WARNING: the sdsys user is still in the group of 1 account(s): sdu_alice' && [ ! -e "$MARKER" ] && echo yes)")" "$OUTS"
row "F2 'sdsys is not in GROUP' (dave, changed by somebody else in between) counts as taken out" "$(ok "$(printf '%s' "$OUTS" | grep -q 'the sdsys user is no longer in the group sdu_dave' && echo yes)")" "$OUTS"

# ---- static ----------------------------------------------------------------------------------------------------------------------
echo "--- S: static"
row "S1 the function calls sd-elevate with ONE verb, sdsys-leave, and by its full path; the question calls nothing" \
    "$(ok "$(printf '%s\n' "$FUNC" | grep -o 'sbin/sd-elevate [a-z-]*' | sort -u | tr '\n' ' ' | grep -q -x -F 'sbin/sd-elevate sdsys-leave ' && ! printf '%s\n' "$ASK" | grep -q 'sd-elevate' && echo yes)")" "$(printf '%s\n' "$FUNC" | grep -o 'sbin/sd-elevate [a-z-]*' | sort -u | tr '\n' ' ')"
row "S2 neither the block nor the function names the old verbs: no sdsys-join, no group-write" \
    "$(ok "$(! printf '%s\n%s\n' "$ASK" "$FUNC" | grep -v '^ *#' | grep -q -E 'sdsys-join|group-write' && echo yes)")" ""
row "S3 the function never exits the install (no exit, no return 1)" "$(ok "$(printf '%s\n' "$FUNC" | grep -E '(^|[^a-z_])(exit|return 1)([^a-z_]|$)' | grep -v '^ *#' | grep -q . || echo yes)")" ""
CALLS_N=$(grep -c -x 'sdsys_groups_ruling "\$ACCT_PATH/\\\$groups.ruled" "\$sdsys_keep"' "$INST")
LINE_CALL=$(grep -n -x 'sdsys_groups_ruling "\$ACCT_PATH/\\\$groups.ruled" "\$sdsys_keep"' "$INST" | cut -d: -f1)
LINE_EDIT=$(grep -n 'RUN gpl.bp upgrade_editgates' "$INST" | head -1 | cut -d: -f1)
LINE_MASTERS=$(grep -n 'RUN gpl.bp upgrade_masters' "$INST" | head -1 | cut -d: -f1)
LINE_ASK=$(grep -n -x '# SDSYSGROUPS-ASK-BEGIN' "$INST" | cut -d: -f1)
LINE_CREDS=$(grep -n -x 'if ! sudo -v; then' "$INST" | head -1 | cut -d: -f1)
LINE_NOTE=$(grep -n -x 'echo "Ruling on the sdsys user.s place in the groups of the user accounts."' "$INST" | cut -d: -f1)
row "S4 the ruling is called once, with the marker in /home/sd (ACCT_PATH) and the answer of the question, after the edit gates are kept and BEFORE the master files are filled" \
    "$(ok "$([ "$CALLS_N" = 1 ] && [ -n "$LINE_CALL" ] && [ -n "$LINE_EDIT" ] && [ -n "$LINE_MASTERS" ] && [ "$LINE_EDIT" -lt "$LINE_CALL" ] && [ "$LINE_CALL" -lt "$LINE_MASTERS" ] && [ -n "$LINE_NOTE" ] && [ "$LINE_NOTE" -lt "$LINE_CALL" ] && echo yes)")" "calls=$CALLS_N edit=$LINE_EDIT call=$LINE_CALL masters=$LINE_MASTERS"
row "S5 the question is asked UP FRONT, with the others and before the first sudo, so that the rest of the install runs unattended" \
    "$(ok "$([ -n "$LINE_ASK" ] && [ -n "$LINE_CREDS" ] && [ "$LINE_ASK" -lt "$LINE_CREDS" ] && echo yes)")" "ask=$LINE_ASK sudo -v=$LINE_CREDS"
row "S6 the marker is the same file in the question and in the call, and it is NOT in the sdsys directory (deletesdcore.sh removes that directory on every cycle, which would lose the ruling)" \
    "$(ok "$(printf '%s\n' "$ASK" | grep -q -F '/home/sd/\$groups.ruled' && grep -q -F '"$ACCT_PATH/\$groups.ruled"' "$INST" && ! grep -v '^ *#' "$INST" | grep -q -F 'sdsysdir/\$groups.ruled' && echo yes)")" ""

echo
echo "test-install-sdsysgroups: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
