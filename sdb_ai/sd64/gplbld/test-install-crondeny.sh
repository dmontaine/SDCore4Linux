#!/bin/bash
#
# test-install-crondeny.sh - the installer's CRONDENY block (S.102, 2 Nov 2026; the owner: "deny them"): the sdsys user in /etc/cron.deny and, where at
# is installed, /etc/at.deny; an existing sdsys crontab MOVED out of the spool (Debian's cron daemon goes on running it after a deny - measured); queued
# sdsys at jobs removed; an allow file left to decide by itself.  And the deleter's half: the "sdsys" line goes when the sdsys user goes.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-crondeny.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-crondeny.sh --selftest
#   INSTALLER=<copy> DELETER=<copy> bash .../test-install-crondeny.sh                       (what --selftest uses)
#
# FREE CHECK: no install, no sudo, no root.  The block is cut out between its markers, its path variables are pointed at a scratch tree, and it runs
# under the installer's own `set -euo pipefail` and IFS with sudo a function (chown, chmod and install's -o/-g are logged, not done: they need root)
# and at, atq, atrm stubs on PATH.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  ANCHORED ON THE DISK and on the stubs' logs.
#
#   C1  a machine with no deny or allow file: cron.deny is made holding sdsys, given root:crontab 0640, and the block says the user may not use cron or at
#   C2  a second run adds no second line
#   C3  a cron.allow that does not name sdsys decides by itself: no cron.deny is made, no warning
#   C4  a cron.allow that names sdsys: a WARNING, no success line, cron.deny untouched
#   C5  an existing sdsys crontab is MOVED: the copy in the backup directory has its bytes, the spool file is gone, the block says where it went
#   C6  at installed: at.deny gets sdsys (root:daemon 0640), atrm is called for sdsys's queued jobs and for no one else's
#   C7  at not installed and no at.deny: none is made
#   C8  a deny file that cannot be written: a WARNING, no success line, and the install goes on (the block ends)
#   C9  the block runs to its end under the installer's own set options and IFS (C1's run)
#   T1  the block sits after the sdsys user's home is made and before the sudoers drop-in
#   D1  the deleter removes the exact line "sdsys" from both deny files only in its DELETE branch, after userdel, and removes a file the line was alone in

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
DEL="${DELETER:-$TREE/deletesdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, file (inst|del), old text, new text
    local name=$1 which=$2 src f
    if [ "$which" = inst ]; then src="$TREE/installsdcore.sh"; else src="$TREE/deletesdcore.sh"; fi
    f="$T/$name.$which"
    python3 -I -c 'import sys; t=open(sys.argv[1]).read(); o=sys.argv[3]; n=sys.argv[4]
if t.count(o) != 1: sys.exit(3)
open(sys.argv[2], "w").write(t.replace(o, n))' "$src" "$f" "$3" "$4" || { echo "  [CANNOT] $name: its text is not in the file once"; missed=$((missed+1)); total=$((total+1)); return; }
    total=$((total+1))
    if [ "$which" = inst ]; then INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; else DELETER="$f" bash "$THIS" > "$T/$name.out" 2>&1; fi
    if [ $? -ne 0 ]; then echo "  [caught] $name"; caught=$((caught+1)); else echo "  [MISSED] $name"; missed=$((missed+1)); fi
  }
  mutant "the spool crontab is left running" inst '    && sudo chmod 0600 "$crondeny_saved" && sudo rm -f "$crondeny_spool"; then' '    && sudo chmod 0600 "$crondeny_saved"; then'
  mutant "the allow file is ignored" inst '      crondeny_ok=0
    fi
    return 0
  fi' '      crondeny_ok=0
    fi
  fi'
  mutant "sdsys is added twice" inst "  if ! sudo grep -qx 'sdsys' \"\$1\" 2>/dev/null; then
    if ! printf" "  if true; then
    if ! printf"
  mutant "everyone's at jobs are removed" inst "awk '\$NF == \"sdsys\" {print \$1}'" "awk '{print \$1}'"
  mutant "the deny file is world-readable" inst 'sudo chmod 0640 "$1"; }; then' 'sudo chmod 0644 "$1"; }; then'
  mutant "success is claimed after a warning" inst 'if [ "$crondeny_ok" = 1 ]; then
  echo "The sdsys user may not use cron or at' 'if true; then
  echo "The sdsys user may not use cron or at'
  mutant "at.deny is made without at" inst 'if command -v at > /dev/null 2>&1 || sudo test -e "$crondeny_at_deny"; then' 'if true; then'
  mutant "the deleter keeps the line" del "            sudo sed -i '/^sdsys\$/d' \"\$dny\"" "            true"
  echo "test-install-crondeny --selftest: $total mutant(s), $missed not caught"
  [ "$missed" -eq 0 ] && [ "$total" -ge 8 ] && exit 0 || exit 1
fi

pass=0; fail=0
row() {   # id, label, condition-exit-status
  if [ "$3" -eq 0 ]; then echo "  [PASS] $1 $2"; pass=$((pass+1)); else echo "  [FAIL] $1 $2"; fail=$((fail+1)); fi
}

[ -f "$INST" ] && [ -f "$DEL" ] || { echo "test-install-crondeny: CANNOT RUN - no installer or deleter"; exit 2; }
BLOCK=$(awk '/^# CRONDENY-BEGIN$/{f=1} f{print} /^# CRONDENY-END$/{f=0}' "$INST")
[ -n "$BLOCK" ] && grep -q 'CRONDENY-END' <<<"$BLOCK" || { echo "test-install-crondeny: CANNOT RUN - no CRONDENY block in $INST"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

scene() {   # NAME [at] - a scratch machine; prints its directory
  local d="$T/$1"
  mkdir -p "$d/etc" "$d/spool" "$d/backups" "$d/bin"
  : > "$d/log"
  if [ "${2:-}" = at ]; then
    printf '#!/bin/bash\nexit 0\n' > "$d/bin/at"
    printf '#!/bin/bash\nprintf "11\\tMon Nov  2 12:00:00 2026 a sdsys\\n12\\tMon Nov  2 12:00:00 2026 a don\\n13\\tMon Nov  2 13:00:00 2026 a sdsys\\n"\n' > "$d/bin/atq"
    printf '#!/bin/bash\necho "atrm $*" >> "%s/log"\n' "$d" > "$d/bin/atrm"
    chmod 755 "$d/bin/at" "$d/bin/atq" "$d/bin/atrm"
  fi
  printf '%s' "$d"
}

run_block() {   # DIR - runs the block on DIR's scratch tree under the installer's set options and IFS; prints its output, then "BLOCK-ENDED"
  local d=$1
  local body
  body=$(sed -e "s|^crondeny_cron_deny=.*|crondeny_cron_deny=$d/etc/cron.deny|" -e "s|^crondeny_cron_allow=.*|crondeny_cron_allow=$d/etc/cron.allow|" \
             -e "s|^crondeny_spool=.*|crondeny_spool=$d/spool/sdsys|" -e "s|^crondeny_at_deny=.*|crondeny_at_deny=$d/etc/at.deny|" \
             -e "s|^crondeny_at_allow=.*|crondeny_at_allow=$d/etc/at.allow|" -e "s|^crondeny_backup=.*|crondeny_backup=$d/backups|" <<<"$BLOCK")
  ( export PATH="$d/bin:/usr/bin:/bin"
    LOG="$d/log"
    bash -c "set -euo pipefail
IFS=\$'\\n\\t'
LOG='$LOG'
sudo() { case \$1 in chown|chmod) echo \"\$1 \$2 \$3\" >> \"\$LOG\"; return \${STUB_CHOWN_RC:-0};; install) shift; local a=(); while [ \$# -gt 0 ]; do case \$1 in -o|-g) shift 2;; *) a+=(\"\$1\"); shift;; esac; done; command install \"\${a[@]}\";; *) \"\$@\";; esac; }
getent() { [ \"\$1\" = group ] && { [ \"\$2\" = crontab ] || [ \"\$2\" = daemon ]; }; }
date() { echo 20261102120000; }
$body
echo BLOCK-ENDED" 2>&1 )
}

# C1 / C9
d=$(scene c1); out=$(run_block "$d")
row C1 "no deny or allow file: cron.deny holds sdsys, root:crontab 0640, and the success line" \
  $( [ "$(cat "$d/etc/cron.deny" 2>/dev/null)" = sdsys ] && grep -qx "chown root:crontab $d/etc/cron.deny" "$d/log" && grep -qx "chmod 0640 $d/etc/cron.deny" "$d/log" \
     && grep -q 'may not use cron or at' <<<"$out"; echo $?)
row C9 "the block runs to its end under the installer's set -euo pipefail and IFS" $(grep -q BLOCK-ENDED <<<"$out"; echo $?)
out2=$(run_block "$d")
row C2 "a second run adds no second line" $( [ "$(grep -cx sdsys "$d/etc/cron.deny")" = 1 ]; echo $?)
# C3
d=$(scene c3); printf 'root\nalice\n' > "$d/etc/cron.allow"; out=$(run_block "$d")
row C3 "a cron.allow without sdsys decides by itself: no cron.deny, no warning" $( [ ! -e "$d/etc/cron.deny" ] && ! grep -q WARNING <<<"$out" && grep -q 'may not use cron' <<<"$out"; echo $?)
# C4
d=$(scene c4); printf 'root\nsdsys\n' > "$d/etc/cron.allow"; out=$(run_block "$d")
row C4 "a cron.allow that names sdsys: a WARNING, no success line, no cron.deny" $(grep -q 'WARNING: .*cron.allow names sdsys' <<<"$out" && ! grep -q 'may not use cron' <<<"$out" && [ ! -e "$d/etc/cron.deny" ]; echo $?)
# C5
d=$(scene c5); printf '* * * * * date >> /tmp/x\n' > "$d/spool/sdsys"; out=$(run_block "$d")
saved="$d/backups/sdcore-sdsys-crontab.20261102120000"
row C5 "an existing sdsys crontab is MOVED: the backup has its bytes, the spool file is gone, the block says where" \
  $( [ "$(cat "$saved" 2>/dev/null)" = '* * * * * date >> /tmp/x' ] && [ ! -e "$d/spool/sdsys" ] && grep -q "moved to $saved" <<<"$out" && grep -qx "chmod 0600 $saved" "$d/log"; echo $?)
# C6
d=$(scene c6 at); out=$(run_block "$d")
row C6 "at installed: at.deny holds sdsys (root:daemon 0640); atrm for sdsys's jobs 11 and 13 only" \
  $( [ "$(cat "$d/etc/at.deny" 2>/dev/null)" = sdsys ] && grep -qx "chown root:daemon $d/etc/at.deny" "$d/log" && grep -qx 'atrm 11' "$d/log" && grep -qx 'atrm 13' "$d/log" \
     && ! grep -qx 'atrm 12' "$d/log"; echo $?)
# C7
d=$(scene c7); out=$(run_block "$d")
row C7 "at not installed and no at.deny: none is made" $( [ ! -e "$d/etc/at.deny" ]; echo $?)
# C8
d=$(scene c8); chmod 555 "$d/etc"; out=$(run_block "$d"); chmod 755 "$d/etc"
row C8 "a deny file that cannot be written: a WARNING, no success line, the block still ends" $(grep -q 'WARNING: could not add sdsys' <<<"$out" && ! grep -q 'may not use cron' <<<"$out" && grep -q BLOCK-ENDED <<<"$out"; echo $?)
# T1
n_home=$(grep -n '^sudo install -d -o sdsys -g sdusers -m 750 /home/sdsys$' "$INST" | head -1 | cut -d: -f1)
n_b=$(grep -n '^# CRONDENY-BEGIN$' "$INST" | cut -d: -f1)
n_sudoers=$(grep -n 'PRE_RELEASE 14, the owner' "$INST" | head -1 | cut -d: -f1)
row T1 "the block sits after the sdsys user's home is made and before the sudoers drop-in, once" $( [ -n "$n_home" ] && [ -n "$n_b" ] && [ -n "$n_sudoers" ] && [ "$n_home" -lt "$n_b" ] && [ "$n_b" -lt "$n_sudoers" ] \
  && [ "$(grep -c '^# CRONDENY-BEGIN$' "$INST")" = 1 ]; echo $?)
# D1
del_branch=$(awk '/^# remove sdsys user and sdusers group only if deleting ACCOUNTS/{g=1} g&&/^if \[ "\$keep_accts" = "DELETE" \]; then$/{f=1} f{print} f&&/^fi$/{exit}' "$DEL")
row D1 "the deleter takes the exact line sdsys out of both deny files in its DELETE branch, after userdel, and removes a file left empty" \
  $(grep -q "for dny in /etc/cron.deny /etc/at.deny; do" <<<"$del_branch" && grep -F -q "sudo sed -i '/^sdsys\$/d' \"\$dny\"" <<<"$del_branch" \
    && grep -F -q 'if ! sudo test -s "$dny"; then sudo rm -f "$dny"; fi' <<<"$del_branch" \
    && [ "$(grep -n '^ *sudo userdel sdsys' <<<"$del_branch" | tail -1 | cut -d: -f1)" -lt "$(grep -n 'for dny in' <<<"$del_branch" | cut -d: -f1)" ]; echo $?)

echo "test-install-crondeny: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -ge 10 ]
