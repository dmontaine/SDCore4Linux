#!/bin/bash
#
# test-install-sdsysgroups.sh - the installer's default for the sdsys user's place in the groups of the user accounts (S.103, 1 Nov 2026): the sdsys user is in the group of
# EVERY user account as delivered.  The act is the function sdsys_groups_default.  (Until 1 Nov this file held the F6 ruling of 26 Oct - a question and sdsys_groups_ruling, which
# took the sdsys user OUT of the groups; the owner reversed it: "sdsys always read/write access to the /home/sd tree".  Its rows are gone with it.  Before that it held the walk
# join_sdsys_groups of 19 Oct, which is what this default is, minus the question and with the marker.)
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysgroups.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysgroups.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-sdsysgroups.sh        (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd-elevate (a stub script), no groups made or changed, no root.  Everything happens in a scratch
# directory.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing piece, a scenario in which the stub was never
# called, is exit 2).
#
# WHAT IT RUNS.  The function is cut out of the installer; every "/home/sd/" in it is rewritten to the scratch directory and "/usr/local/sbin/sd-elevate" to the stub; it
# runs under the installer's OWN "set -euo pipefail" AND ITS IFS (IFS=$'\n\t' - the first real install of the gates question failed because a list was one word under
# that IFS and the test had run under `set` alone), with `sudo` a function that runs its arguments, `chown` a function that logs (the scratch machine has no sdsys user)
# and `getent` a function that reads a fixture /etc/group.  The stub logs every call and does what the scenario says: join (and change the fixture group), refuse, or
# exit 0 and say nothing.
#
# THE SCENARIO (the groups are the fixture /etc/group; the account directories of alice, carol, dave and fred exist, bob's and eve's do not):
#   sdu_alice  does not list sdsys  -> joined, the account directory repaired (group-write)
#   sdu_bob    lists sdsys          -> never touched
#   sdu_carol  does not, the helper refuses the join   -> counted, named in the WARNING, the walk goes on, the marker is NOT written
#   sdu_dave   root,dave            -> joined, repaired
#   sdu_eve    lists "sdsys2"       -> not sdsys: JOINED (a whole name, not a prefix), no account directory: no group-write (named as "does not exist" since 2 Nov 26)
#   sdu_fred   lists "xsdsys"       -> not sdsys: JOINED, repaired
#   sdg_team   a group account's group, lists sdsys   -> NEVER touched (sdsys owns the files of a group account)
#   sdusers    lists sdsys          -> never touched (not an account's group)
# alice, carol, dave, eve and fred (and, adversarially, a record named sdg_ops) are in the fixture register ($T/sdsys/accounts/<name>: line 1 the path, line 3 the group), each at user_accounts/<name>.
#
# SCENARIO E (2 Nov 26, PROJECT_STATUS (95) follow-ups 2 and 3: only REGISTERED accounts' groups are joined, the modes are repaired at the REGISTERED path, and
# sd-elevate group-write is never handed a path outside the places it accepts):
#   sdu_gus   no register record                         -> left alone, never joined; named in ONE line
#   sdu_hal   a record whose line 3 is another group     -> left alone, never joined; named in the same line
#   sdu_ivy   registered at $T/elsewhere/ivy (a directory that exists)   -> joined; NOT handed to group-write; named as not repaired, with why
#   sdu_jan   registered at user_accounts/janet          -> joined; group-write on .../janet, NOT on .../jan (which exists too)
#   sdu_kim   registered at user_accounts/kim/           -> joined; group-write on .../kim (the trailing / taken off)
#   sdu_lou   registered at user_accounts/x/lou (nested, exists) -> joined; not repaired, named
#   sdu_max   registered with an empty path              -> joined; not repaired, named ("has no path")
#   sdu_ned   registered at user_accounts/ned, which does not exist -> joined; not repaired, named ("does not exist") - it used to be skipped without a word
#   no join failed, so the marker IS written: the four not repaired could not be repaired by running the installer again.
#
# NOT MEASURED HERE, and said so: that sd-elevate really puts a user in a group (test-sd-elevate.py measures its rules; the real change was witness-masters.sh's, retired 2 Nov 26 with the master files: a VM witness of it is owed); that the
# marker is where a kept install keeps it, which is the position of /home/sd in a delete that keeps the accounts (the VM); that sudo works.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, sed expression (applied to the whole installer; the expressions name lines of the function or the call)
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
  F='/^sdsys_groups_default() {/,/^}/'
  mutant leaves-with-the-marker        "$F s/^    if \[ -e \"\$marker\" \]; then\$/    if false; then/"
  mutant counts-group-accounts         "$F s/\\^sdu_\\./^sd[ug]_./"
  mutant joins-those-already-in        "$F s/(\",\" \$4 \",\") !~ /(\",\" \$4 \",\") ~ /"
  mutant counts-a-prefix               "$F s#!~ /,sdsys,/#!~ /sdsys/#"
  mutant reads-the-wrong-field         "$F s/(\",\" \$4 \",\")/(\",\" \$3 \",\")/"
  mutant wrong-verb                    "$F s#sd-elevate sdsys-join \"\\\$group\"#sd-elevate sdsys-leave \"\$group\"#"
  mutant exit-status-only              "$F s#0:\\*\"usermod -aG \\\${group} -- sdsys\"\\*)#0:*)#"
  mutant join-failure-aborts           "$F s/sdsys-join \"\\\$group\" 2>&1) || rc=\\\$?/sdsys-join \"\$group\" 2>\\&1)/"
  mutant no-group-write                "$F s#out=\$(sudo /usr/local/sbin/sd-elevate group-write \"\$dir\" 2>&1) || rc=\$?#out=\"sd-elevate: group-write: \"#"
  mutant group-write-unjudged          "$F s#0:\\*\"sd-elevate: group-write: \"\\*) ;;#*) ;;#"
  mutant group-write-without-a-dir     "$F s/^                if \[ -n \"\$dir\" \]; then\$/                if true; then/"
  mutant absent-dir-said-nothing       "$F s/^                if \[ -n \"\$dir\" \] && \[ ! -d \"\$dir\" \]; then\$/                if false; then/"
  mutant warning-never                 "$F s/^    if \[ \"\\\$n_fail\" -gt 0 \]; then\$/    if false; then/"
  mutant marker-after-a-failure        "$F { /^        return 0\$/{x;s/^/x/;/^xx/{x;d;};x;}; }"
  mutant marker-never-written          "$F { /^    sudo touch \"\\\$marker\"\$/d; }"
  mutant marker-not-handed-to-sdsys    "$F { /^    sudo chown sdsys:sdusers \"\\\$marker\"\$/d; }"
  mutant marker-mode-open              "$F s/^    sudo chmod 644 \"\\\$marker\"\$/    sudo chmod 666 \"\$marker\"/"
  mutant function-exits                "$F s/^        echo \"  The sdsys user was put in the group of /        exit 1; echo \"  The sdsys user was put in the group of /"
  mutant function-never-called         's/^sdsys_groups_default "\$ACCT_PATH\/\\$sdsys.access"$/true/'
  mutant marker-in-the-sdsys-directory 's/^sdsys_groups_default "\$ACCT_PATH\/\\$sdsys.access"/sdsys_groups_default "$sdsysdir\/\\$sdsys.access"/'
  mutant called-after-the-register     '/^sdsys_groups_default "\$ACCT_PATH\/\\$sdsys.access"$/d;/^echo "account register: /a sdsys_groups_default "$ACCT_PATH/\\$sdsys.access"'
  mutant joins-unregistered            "$F s/^        if \[ \"\$rgroup\" != \"\$group\" \]; then\$/        if false; then/"
  mutant wrong-register-line           "$F s/sed -n '3p' \"\$reg\"/sed -n '2p' \"\$reg\"/"
  mutant dir-from-the-name             "$F s#^                dir=\"\\\${dir%/}\"\$#                dir=\"/home/sd/user_accounts/\${name}\"#"
  mutant nested-path-handed-over       "$F s|case \"\\\${dir#/home/sd/\\*_accounts/}\" in|case \"x\" in|"
  mutant outside-path-handed-over      "$F s/^                        dir=\"\"\$/                        :/"
  mutant unowned-said-nothing          "$F s/^        echo \"  Left alone, no registered.*\$/        :/"
  mutant outside-warning-never         "$F s/^    if \[ -n \"\$outside\" \]; then\$/    if false; then/"
  mutant outside-holds-the-marker      "$F s/^    if \[ \"\\\$n_fail\" -gt 0 \]; then\$/    if [ \"\$n_fail\" -gt 0 ] || [ -n \"\$outside\" ]; then/"
  mutant the-old-question-is-back     's/^printf "%b\\n" "\$NC"$/read -r -p "Keep the sdsys user in the groups? (y\/N) " sdsys_ans; printf "%b\\n" "$NC"/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
FUNC=$(awk '/^sdsys_groups_default\(\) \{/{f=1} f{print} f&&/^\}/{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$IFSL" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no IFS line in the installer"; exit 2; }
[ -z "$FUNC" ] && { echo "test-install-sdsysgroups: CANNOT RUN - no function sdsys_groups_default in the installer (nothing to check)"; exit 2; }
echo "function  : $(printf '%s\n' "$FUNC" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
rewrite() { sed -e "s#/home/sd/#$T/home/sd/#g" -e "s#/usr/local/sbin/sd-elevate#$T/bin/sd-elevate#g"; }
FUNC_T=$(printf '%s\n' "$FUNC" | rewrite)
printf '%s\n' "$FUNC_T" | grep -q -F "$T/bin/sd-elevate" || { echo "test-install-sdsysgroups: CANNOT RUN - the function does not call sd-elevate"; exit 2; }
printf '%s\n' "$FUNC_T" | grep -q -F "$T/home/sd/user_accounts/" || { echo "test-install-sdsysgroups: CANNOT RUN - the function does not look at the account directories in /home/sd"; exit 2; }

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
    if grep -qxF "$grp" "$T/stub-join-silent" 2>/dev/null; then echo "sd-elevate: stub did something"; exit 0; fi
    sed -i -e "/^$grp:/ { s/\$/,sdsys/; s/:,sdsys\$/:sdsys/ }" "$T/etc/group"
    echo "sd-elevate: usermod -aG $grp -- sdsys"; exit 0 ;;
  group-write)
    dir=${1:-}
    if grep -qxF "$dir" "$T/stub-gw-fail" 2>/dev/null; then echo "sd-elevate: REFUSED - stub: no for $dir" >&2; exit 2; fi
    if grep -qxF "$dir" "$T/stub-gw-silent" 2>/dev/null; then exit 0; fi
    echo "sd-elevate: group-write $dir (group x, gid 1; owners uid 1)"
    echo "sd-elevate: group-write: 0 directories and 0 file(s) changed, 3 already right, 0 skipped"; exit 0 ;;
esac
exit 3
STUB
chmod +x "$T/bin/sd-elevate"

# ---- the fixture ---------------------------------------------------------------------------------------------------------
MARKER="$T/home/sd/\$sdsys.access"
GROUPS_MAIN='sdusers:x:100:root,sdsys,alice,bob\nsdu_alice:x:2001:alice\nsdu_bob:x:2002:bob,sdsys\nsdu_carol:x:2003:carol\nsdu_dave:x:2004:root,dave\nsdu_eve:x:2005:eve,sdsys2\nsdu_fred:x:2006:xsdsys\nsdg_team:x:2007:sdsys,root\nsdg_ops:x:2008:root\n'
regrec() {   # regrec NAME PATH GROUP - a register record as CREATE.ACCOUNT writes it: line 1 the path, line 2 the description, line 3 the group
  printf '%s\n\n%s\n' "$2" "$3" > "$T/sdsys/accounts/$1"
}
build() {   # build SCENARIO: main | clean | allin | empty | reg
  rm -rf "$T/home" "$T/etc" "$T/sdsys" "$T/elsewhere" "$T/calls.log" "$T/chown.log" "$T"/stub-*
  mkdir -p "$T/home/sd/user_accounts" "$T/etc" "$T/sdsys/accounts"
  : > "$T/calls.log"; : > "$T/chown.log"
  for a in alice carol dave fred; do mkdir -p "$T/home/sd/user_accounts/$a"; done
  for a in alice carol dave eve fred; do regrec "$a" "$T/home/sd/user_accounts/$a" "sdu_$a"; done
  # adversarial: a record NAMED after a group account's group, which says it owns that group.  Only the awk filter (sdu_ groups only) keeps sdg_ops out of the walk;
  # without this record the register lookup would hide a mutant of that filter (counts-group-accounts).
  regrec sdg_ops "$T/home/sd/group_accounts/ops" sdg_ops
  case "$1" in
    reg)
      printf 'sdusers:x:100:root,sdsys\nsdu_gus:x:2010:gus\nsdu_hal:x:2011:hal\nsdu_ivy:x:2012:ivy\nsdu_jan:x:2013:jan\nsdu_kim:x:2014:kim\nsdu_lou:x:2015:lou\nsdu_max:x:2016:max\nsdu_ned:x:2017:ned\n' > "$T/etc/group"
      mkdir -p "$T/elsewhere/ivy" "$T/home/sd/user_accounts/janet" "$T/home/sd/user_accounts/jan" "$T/home/sd/user_accounts/kim" "$T/home/sd/user_accounts/x/lou"
      regrec hal "$T/home/sd/user_accounts/hal" sdu_other
      regrec ivy "$T/elsewhere/ivy" sdu_ivy
      regrec jan "$T/home/sd/user_accounts/janet" sdu_jan
      regrec kim "$T/home/sd/user_accounts/kim/" sdu_kim
      regrec lou "$T/home/sd/user_accounts/x/lou" sdu_lou
      regrec max "" sdu_max
      regrec ned "$T/home/sd/user_accounts/ned" sdu_ned      # registered inside user_accounts, but the directory is not there
      ;;
    empty) : > "$T/etc/group" ;;
    main)  printf "$GROUPS_MAIN" > "$T/etc/group"; printf '%s\n' "sdu_carol" > "$T/stub-join-fail" ;;
    clean) printf "$GROUPS_MAIN" > "$T/etc/group" ;;
    allin) printf 'sdusers:x:100:root,sdsys,alice\nsdu_alice:x:2001:alice,sdsys\nsdu_bob:x:2002:bob,sdsys\nsdg_team:x:2007:sdsys,root\n' > "$T/etc/group" ;;
  esac
}
HARNESS='
      eval "$OPTS"
      eval "$IFSL"
      RED=; NC=
      sdsysdir="$T/sdsys"
      sudo() { "$@"; }
      getent() { if [ "$1" = group ]; then if [ -n "${2:-}" ]; then grep -m1 "^$2:" "$T/etc/group" || return 2; else cat "$T/etc/group"; fi; else return 2; fi; }
      chown() { { printf "chown"; printf " %s" "$@"; echo; } >> "$T/chown.log"; }     # not "$*": under the installer'"'"'s IFS that joins with a newline
      export T'
run_fn() {   # run_fn  - prints the function'"'"'s output, then  AFTER rc=<n>  (the line after the call: reached only if the function did not stop the shell)
  OPTS="$OPTS" IFSL="$IFSL" FUNC_T="$FUNC_T" T="$T" MARKER="$MARKER" bash -c "$HARNESS"'
      eval "$FUNC_T"
      sdsys_groups_default "$MARKER"
      echo "AFTER rc=$?"' 2>&1
}
calls() { cat "$T/calls.log"; }
has_call() { calls | grep -q -x -F -- "$1" && echo yes; }
no_call_with() { calls | grep -q -F -- "$1" && echo no || echo yes; }
members() { grep "^$1:" "$T/etc/group" | cut -d: -f4; }
marker_mode() { stat -c %a "$MARKER" 2>/dev/null; }
D="$T/home/sd/user_accounts"

# ---- A: the walk -------------------------------------------------------------------------------------------------------------
echo "--- A: the accounts that are there (the helper refuses carol)"
build main
OUTA=$(run_fn)
printf '%s\n' "$OUTA" | sed -e 's/^/      /'
row "A1 the groups that do not list sdsys are joined, as WHOLE names, user-account groups only: alice carol dave eve fred - in that order, each once" \
    "$(ok "$([ "$(calls | grep '^sdsys-join' | tr '\n' ' ')" = 'sdsys-join sdu_alice sdsys-join sdu_carol sdsys-join sdu_dave sdsys-join sdu_eve sdsys-join sdu_fred ' ] && echo yes)")" "$(calls)"
row "A2 a group that already lists sdsys (bob), a group account's group whether it lists sdsys (team) or not (ops), and sdusers are never touched" \
    "$(ok "$([ "$(no_call_with 'sdu_bob')" = yes ] && [ "$(no_call_with 'sdg_team')" = yes ] && [ "$(no_call_with 'sdg_ops')" = yes ] && [ "$(no_call_with 'sdusers')" = yes ] && echo yes)")" "$(calls)"
row "A3 'sdsys2' (eve) and 'xsdsys' (fred) are not sdsys: both are joined" \
    "$(ok "$([ "$(members sdu_eve)" = eve,sdsys2,sdsys ] && [ "$(members sdu_fred)" = xsdsys,sdsys ] && echo yes)")" "eve=$(members sdu_eve) fred=$(members sdu_fred)"
row "A4 the modes of an account whose group was joined are repaired (group-write on its directory): alice dave fred; not eve (no directory), not carol (the join failed)" \
    "$(ok "$([ "$(calls | grep '^group-write' | tr '\n' ' ')" = "group-write $D/alice group-write $D/dave group-write $D/fred " ] && echo yes)")" "$(calls)"
row "A5 the failed join (carol) is named in the WARNING with the command that repairs it, the walk went on, and there is NO marker" \
    "$(ok "$(printf '%s' "$OUTA" | grep -q 'the sdsys user could not be put in sdu_carol' && printf '%s' "$OUTA" | grep -q 'WARNING: 1 account(s) are not right yet: sdu_carol' && printf '%s' "$OUTA" | grep -q 'modify.account <account> sdsys-on' && [ ! -e "$MARKER" ] && echo yes)")" "$OUTA"
row "A6 it counts: put in the group of 4 of 5 accounts, and it never stops the install (AFTER rc=0)" \
    "$(ok "$(printf '%s' "$OUTA" | grep -q 'put in the group of 4 of 5 account(s)' && printf '%s' "$OUTA" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTA"
row "A7 the groups that were not joined are as they were (carol, the group account, sdusers)" \
    "$(ok "$([ "$(members sdu_carol)" = carol ] && [ "$(members sdg_team)" = sdsys,root ] && [ "$(members sdusers)" = root,sdsys,alice,bob ] && echo yes)")" "$(cat "$T/etc/group")"

echo "--- B: no failure: the marker"
build clean
OUTB=$(run_fn)
row "B1 every group joined, no 'not right yet' WARNING (only eve's absent directory named, 2 Nov 26), the marker is written (a LATER sdsys-off stands), handed to sdsys:sdusers, mode 644, and it says where" \
    "$(ok "$([ -e "$MARKER" ] && [ "$(marker_mode)" = 644 ] && grep -q "^chown sdsys:sdusers $MARKER\$" "$T/chown.log" && ! printf '%s' "$OUTB" | grep -q 'not right yet' && [ "$(printf '%s\n' "$OUTB" | grep 'WARNING' | grep -c -v 'does not exist: eve$')" = 0 ] && printf '%s' "$OUTB" | grep -q 'put in the group of 5 of 5 account(s)' && printf '%s' "$OUTB" | grep -q 'Recorded in' && printf '%s' "$OUTB" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTB / mode=$(marker_mode) / $(cat "$T/chown.log")"
OUTB2=$(run_fn)
row "B2 a second run with the marker present does NOTHING (no call, no change): an administrator's sdsys-off after the first run is not undone" \
    "$(ok "$(n=$(calls | wc -l); [ "$n" -eq 9 ] && printf '%s' "$OUTB2" | grep -q 'settled at an earlier install' && printf '%s' "$OUTB2" | grep -q '^AFTER rc=0$' && echo yes)")" "calls=$(calls | wc -l) $OUTB2"
build clean
: > "$T/home/sd/.keep"; : > "$MARKER"
OUTB3=$(run_fn)
row "B3 with the marker already there from the start: no call at all, the groups untouched" \
    "$(ok "$([ ! -s "$T/calls.log" ] && [ "$(members sdu_alice)" = alice ] && echo yes)")" "$(calls)"

echo "--- C: nothing to do"
build allin
OUTC=$(run_fn)
row "C1 every user group already lists sdsys: no call, the marker is written, it says so" \
    "$(ok "$([ ! -s "$T/calls.log" ] && [ -e "$MARKER" ] && printf '%s' "$OUTC" | grep -q 'in the group of every user account already' && ! printf '%s' "$OUTC" | grep -q WARNING && echo yes)")" "$OUTC"
build empty
OUTC2=$(run_fn)
row "C2 an empty /etc/group: the marker is written and nothing else happens" "$(ok "$([ -e "$MARKER" ] && [ ! -s "$T/calls.log" ] && printf '%s' "$OUTC2" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTC2"

echo "--- D: what the helper may answer"
build clean
printf '%s\n' "sdu_alice" > "$T/stub-join-silent"
printf '%s\n' "$D/dave" > "$T/stub-gw-fail"
printf '%s\n' "$D/fred" > "$T/stub-gw-silent"
OUTD=$(run_fn)
row "D1 a join that exits 0 WITHOUT the usermod line (alice) is NOT 'joined': named in the WARNING, no group-write for it" \
    "$(ok "$(printf '%s' "$OUTD" | grep -q 'could not be put in sdu_alice' && [ "$(members sdu_alice)" = alice ] && no_call_with "group-write $D/alice" | grep -q yes && echo yes)")" "$OUTD"
row "D2 a group-write that is refused (dave) is named (the modes could not be repaired) and counted, though the join worked" \
    "$(ok "$(printf '%s' "$OUTD" | grep -q "the modes of $D/dave could not be repaired" && [ "$(members sdu_dave)" = root,dave,sdsys ] && echo yes)")" "$OUTD"
row "D3 a group-write that exits 0 and says nothing (fred) is not 'repaired' either: judged on its words" \
    "$(ok "$(printf '%s' "$OUTD" | grep -q "the modes of $D/fred could not be repaired" && echo yes)")" "$OUTD"
row "D4 three failures: the WARNING counts them, names the three groups, and there is no marker" \
    "$(ok "$(printf '%s' "$OUTD" | grep -q 'WARNING: 3 account(s) are not right yet: sdu_alice sdu_dave sdu_fred' && [ ! -e "$MARKER" ] && echo yes)")" "$OUTD"

echo "--- E: the register decides (only registered accounts, at their registered path; group-write never handed a path it would not accept)"
build reg
OUTE=$(run_fn)
printf '%s\n' "$OUTE" | sed -e 's/^/      /'
row "E1 only the groups of REGISTERED accounts are joined: ivy jan kim lou max ned, in that order, each once; gus (no record) and hal (its record names another group) never, and their groups are as they were" \
    "$(ok "$([ "$(calls | grep '^sdsys-join' | tr '\n' ' ')" = 'sdsys-join sdu_ivy sdsys-join sdu_jan sdsys-join sdu_kim sdsys-join sdu_lou sdsys-join sdu_max sdsys-join sdu_ned ' ] && [ "$(no_call_with 'sdu_gus')" = yes ] && [ "$(no_call_with 'sdu_hal')" = yes ] && [ "$(members sdu_gus)" = gus ] && [ "$(members sdu_hal)" = hal ] && echo yes)")" "$(calls)"
row "E2 the groups no registered account owns are named in ONE line, and only there" \
    "$(ok "$([ "$(printf '%s\n' "$OUTE" | grep -c 'sdu_gus')" = 1 ] && [ "$(printf '%s\n' "$OUTE" | grep -c 'sdu_hal')" = 1 ] && printf '%s\n' "$OUTE" | grep -q -x '  Left alone, no registered SD account owns them: sdu_gus sdu_hal' && echo yes)")" "$OUTE"
row "E3 group-write is called on the REGISTERED paths that are directly inside user_accounts: .../janet (not .../jan, which exists) and .../kim (trailing / taken off); nothing else" \
    "$(ok "$([ "$(calls | grep '^group-write' | tr '\n' ' ')" = "group-write $D/janet group-write $D/kim " ] && echo yes)")" "$(calls)"
row "E4 ivy (outside), lou (nested), max (no path) and ned (a path that does not exist) are joined, NOT handed to group-write, each named as not repaired with why, and listed in a WARNING" \
    "$(ok "$([ "$(no_call_with "group-write $T/elsewhere")" = yes ] && [ "$(no_call_with "group-write $D/x")" = yes ] && [ "$(no_call_with "group-write $D/ned")" = yes ] \
            && printf '%s\n' "$OUTE" | grep -q "the modes of account ivy were not repaired: its registered path '$T/elsewhere/ivy' is not directly inside" \
            && printf '%s\n' "$OUTE" | grep -q "the modes of account lou were not repaired: its registered path '$D/x/lou' is not directly inside" \
            && printf '%s\n' "$OUTE" | grep -q "the modes of account max were not repaired: its register record has no path (line 1)" \
            && printf '%s\n' "$OUTE" | grep -q "the modes of account ned were not repaired: its registered path '$D/ned' does not exist" \
            && printf '%s\n' "$OUTE" | grep -q -F 'WARNING: the modes of these account(s) were not repaired - registered outside the account directories, with no path, or at a path that does not exist: ivy lou max ned' \
            && [ "$(members sdu_ivy)" = ivy,sdsys ] && [ "$(members sdu_max)" = max,sdsys ] && echo yes)")" "$OUTE"
row "E5 no join failed: 6 of 6, no 'not right yet' WARNING, the marker IS written (running again could not repair a path that is outside), AFTER rc=0" \
    "$(ok "$(printf '%s' "$OUTE" | grep -q 'put in the group of 6 of 6 account(s)' && ! printf '%s' "$OUTE" | grep -q 'not right yet' && [ -e "$MARKER" ] && printf '%s' "$OUTE" | grep -q '^AFTER rc=0$' && echo yes)")" "$OUTE / marker=$([ -e "$MARKER" ] && echo yes || echo no)"

# ---- static ----------------------------------------------------------------------------------------------------------------------
echo "--- S: static"
row "S6 the account directory comes from the register (\${sdsysdir}/accounts, line 1), never from the group's name; and sd-elevate is not touched by this change (the function never builds a path from the group)" \
    "$(ok "$(printf '%s\n' "$FUNC" | grep -q -F 'register="${sdsysdir}/accounts"' && printf '%s\n' "$FUNC" | grep -q -F "dir=\$(sudo sed -n '1p' \"\$reg\"" && ! printf '%s\n' "$FUNC" | grep -v '^ *#' | grep -q -E 'user_accounts/\$\{(group|name)' && echo yes)")" ""
row "S1 the function calls sd-elevate with TWO verbs only, sdsys-join and group-write, by their full path; never sdsys-leave" \
    "$(ok "$(printf '%s\n' "$FUNC" | grep -o 'sbin/sd-elevate [a-z-]*' | sort -u | tr '\n' ' ' | grep -q -x -F 'sbin/sd-elevate group-write sbin/sd-elevate sdsys-join ' && echo yes)")" "$(printf '%s\n' "$FUNC" | grep -o 'sbin/sd-elevate [a-z-]*' | sort -u | tr '\n' ' ')"
row "S2 the function asks nobody anything (no read), and the installer has no question about the sdsys user's groups any more" \
    "$(ok "$(! printf '%s\n' "$FUNC" | grep -v '^ *#' | grep -q -E '(^|[^a-z_])read ' && ! grep -v '^ *#' "$INST" | grep -q -E 'SDSYSGROUPS-ASK|sdsys_keep|sdsys_groups_ruling|read[^|]*[Kk]eep the sdsys' && ! grep -q -E '^# SDSYSGROUPS-ASK' "$INST" && echo yes)")" ""
row "S3 the function never exits the install (no exit, no return 1)" "$(ok "$(printf '%s\n' "$FUNC" | grep -E '(^|[^a-z_])(exit|return 1)([^a-z_]|$)' | grep -v '^ *#' | grep -q . || echo yes)")" ""
CALL='sdsys_groups_default "$ACCT_PATH/\$sdsys.access"'
CALLS_N=$(grep -c -x -F "$CALL" "$INST")
LINE_CALL=$(grep -n -x -F "$CALL" "$INST" | cut -d: -f1)
LINE_EDIT=$(grep -n 'RUN gpl.bp upgrade_editgates' "$INST" | head -1 | cut -d: -f1)
LINE_REG=$(grep -n -x -F 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"' "$INST" | head -1 | cut -d: -f1)   # 2 Nov 26 (S.96 M6): the master files it ran before are retired
LINE_NOTE=$(grep -n -x 'echo "Putting the sdsys user in the groups of the user accounts."' "$INST" | cut -d: -f1)
row "S4 it is called once, with the marker in /home/sd (ACCT_PATH), after the edit gates are kept and BEFORE the register is handed to sdsys" \
    "$(ok "$([ "$CALLS_N" = 1 ] && [ -n "$LINE_CALL" ] && [ -n "$LINE_EDIT" ] && [ -n "$LINE_REG" ] && [ "$LINE_EDIT" -lt "$LINE_CALL" ] && [ "$LINE_CALL" -lt "$LINE_REG" ] && [ -n "$LINE_NOTE" ] && [ "$LINE_NOTE" -lt "$LINE_CALL" ] && echo yes)")" "calls=$CALLS_N edit=$LINE_EDIT call=$LINE_CALL masters=$LINE_MASTERS note=$LINE_NOTE"
row "S5 the marker is NOT in the sdsys directory (deletesdcore.sh removes that directory on every cycle, which would lose the ruling) and is not the F6 marker" \
    "$(ok "$(! grep -v '^ *#' "$INST" | grep -q -F 'sdsysdir/\$sdsys.access' && ! grep -v '^ *#' "$INST" | grep -q -F '$groups.ruled' && echo yes)")" ""

echo
echo "test-install-sdsysgroups: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
