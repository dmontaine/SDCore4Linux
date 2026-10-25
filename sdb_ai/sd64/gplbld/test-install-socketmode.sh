#!/bin/bash
#
# test-install-socketmode.sh - W.11 F5 (security-model evaluation, 24 Oct 2026): the API listener's Unix socket is mode 0660 (group sdusers), not 0666.
# With no SocketMode= systemd makes a Unix socket 0666, so SocketGroup=sdusers restricted nothing and anybody on the machine could reach the first
# stage of an API connection, which runs as root.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-socketmode.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-socketmode.sh --selftest
#   INSTALLER=<copy of the installer> UNIT=<copy of the unit> bash .../test-install-socketmode.sh      (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no root.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  A row that needs the
# user's systemd and cannot get it prints SKIPPED and is NOT counted as a pass.
#
#   U1  the unit the tree ships: SocketGroup=sdusers, exactly one SocketMode=0660, never 0666, and the unit's other lines are what they were
#   B1  the installer's SOCKETMODE block, cut out and run under the installer's own `set` and `IFS`, on scratch copies of the unit:
#       an install made before this release (no SocketMode=) gains exactly one SocketMode=0660 and nothing else changes; running it twice adds nothing;
#       a unit with SocketMode=0660 (this release's own) and one with an administrator's SocketMode=0666 are left byte for byte; a unit with no
#       SocketGroup= line gets it under [Socket]; no unit at all is not an error
#   R1  RUNTIME (the user's systemd, a transient socket unit): with no SocketMode= the socket file is 0666 (the control - what the live system had),
#       and with the value this tree's unit carries it is 0660, read from the disk with stat
# ANCHORED ON THE DISK: the lines the file ends up with, and the mode the socket file has.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
UNIT="${UNIT:-$TREE/sdb_ai/sd64/usr/lib/systemd/system/sdclient.socket}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  judge() {   # name, rc-of-the-run, what-it-changed
    total=$((total+1))
    if [ "$2" -ne 0 ]; then echo "  [caught] $1 (exit $2)"; caught=$((caught+1))
    else echo "  [MISSED] $1: the check still passed"; missed=$((missed+1)); fi
  }
  inst_mutant() {   # name, sed expression applied to the installer
    local f="$T/$1.sh"
    sed -e "$2" "$TREE/installsdcore.sh" > "$f"
    if cmp -s "$TREE/installsdcore.sh" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); total=$((total+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$1.out" 2>&1; judge "$1" $?
  }
  unit_mutant() {   # name, sed expression applied to the unit
    local f="$T/$1.socket"
    sed -e "$2" "$UNIT" > "$f"
    if cmp -s "$UNIT" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); total=$((total+1)); return; fi
    UNIT="$f" bash "$THIS" > "$T/$1.out" 2>&1; judge "$1" $?
  }
  echo "selftest: the real files first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real files do not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real files pass"
  B='/^# SOCKETMODE-BEGIN/,/^# SOCKETMODE-END/'
  inst_mutant block-writes-0666       "$B s/SocketMode=0660/SocketMode=0666/"
  inst_mutant block-no-guard          "$B s/ \&\& ! grep -q '\^SocketMode=' \"\$SYSTEMDPATH\/sdclient.socket\"//"
  inst_mutant block-no-fallback       "$B s#sudo sed -i 's\#^\\\\\[Socket\\\\\]\$\#\\[Socket\\]\\\\nSocketMode=0660\#' \"\$SYSTEMDPATH/sdclient.socket\"#true#"
  inst_mutant block-wrong-file        "$B{/sudo sed -i 's#^SocketGroup/s|sdclient\\.socket\"\$|sdclient@.service\"|;}"
  inst_mutant block-no-file-test      "$B s/if \[ -f \"\$SYSTEMDPATH\/sdclient.socket\" \] \&\& /if /"
  inst_mutant begin-marker-gone       "s/^# SOCKETMODE-BEGIN/# socketmode-begin/"
  inst_mutant end-marker-gone         "s/^# SOCKETMODE-END/# socketmode-end/"
  unit_mutant unit-0666               "s/^SocketMode=0660/SocketMode=0666/"
  unit_mutant unit-no-socketmode      "/^SocketMode=/d"
  unit_mutant unit-two-socketmodes    "s/^SocketMode=0660/SocketMode=0660\nSocketMode=0660/"
  unit_mutant unit-no-group           "/^SocketGroup=/d"
  unit_mutant unit-group-wrong        "s/^SocketGroup=sdusers/SocketGroup=users/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

[ -r "$UNIT" ] || { echo "test-install-socketmode: CANNOT RUN - no unit at $UNIT"; exit 2; }
BLOCK=$(awk '/^# SOCKETMODE-BEGIN$/{f=1;next} /^# SOCKETMODE-END$/{f=0} f{print}' "$INST")
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "unit      : $UNIT"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-socketmode: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-socketmode: CANNOT RUN - no SOCKETMODE block in the installer"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0; skipped=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# U1 the shipped unit
n_mode=$(grep -c '^SocketMode=' "$UNIT")
mode=$(sed -n 's/^SocketMode=//p' "$UNIT" | head -1)
grp=$(grep -c '^SocketGroup=sdusers$' "$UNIT")
CODE="$T/unit.code"; grep -v '^#' "$UNIT" > "$CODE"      # the comments of the unit mention 0666 and 0.0.0.0 in words; the rows judge the settings
row "U1 the shipped unit has SocketGroup=sdusers and exactly one SocketMode=0660 (never 0666)" "$([ "$n_mode" = 1 ] && [ "$mode" = 0660 ] && [ "$grp" = 1 ] && ! grep -q '0666' "$CODE" && echo 0 || echo 1)" "SocketMode lines $n_mode, value '$mode', SocketGroup lines $grp"
row "U1b and it still listens on the Unix socket and on 127.0.0.1:4247 only" "$([ "$(grep -c '^ListenStream=/tmp/sdsys/sdclient.socket$' "$CODE")" = 1 ] && [ "$(grep -c '^ListenStream=127.0.0.1:4247$' "$CODE")" = 1 ] && ! grep -q '0\.0\.0\.0' "$CODE" && echo 0 || echo 1)" "ListenStream lines: $(grep '^ListenStream=' "$CODE" | tr '\n' ' ')"

# the unit as an install made before this release has it (no SocketMode=)
OLD="$T/old.socket"
printf '%s\n' '[Unit]' 'Description=String Database (SD)  Per-Connection client Server' '' '[Socket]' 'SocketGroup=sdusers' 'ListenStream=/tmp/sdsys/sdclient.socket' \
  'ListenStream=127.0.0.1:4247' 'Accept=true' '' '[Install]' 'WantedBy=sockets.target' > "$OLD"

runblock() {   # unit-dir -> output; the return code is the block's
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" DIR="$1" bash -c '
      eval "$OPTS"; eval "$IFSL"
      sudo() { "$@"; }
      SYSTEMDPATH="$DIR"
      eval "$BLOCK"
      echo REACHED-END' 2>&1
}

# B1 an install made before this release
d="$T/b1"; mkdir "$d"; cp "$OLD" "$d/sdclient.socket"
out=$(runblock "$d"); rc=$?
case "$out" in *REACHED-END*) reached=0 ;; *) reached=1 ;; esac
n=$(grep -c '^SocketMode=0660$' "$d/sdclient.socket")
others=$(grep -v '^SocketMode=' "$d/sdclient.socket" | cmp -s - "$OLD" && echo same || echo different)
row "B1 an older unit gains exactly one SocketMode=0660, says so, and every other line is as it was" "$([ "$reached" = 0 ] && [ "$n" = 1 ] && [ "$others" = same ] && [[ "$out" == *"SocketMode=0660"* ]] && echo 0 || echo 1)" "reached=$reached mode lines=$n others=$others output: $out"
out=$(runblock "$d")
n=$(grep -c '^SocketMode=' "$d/sdclient.socket")
row "B1b a second run adds nothing (still one SocketMode= line)" "$([ "$n" = 1 ] && echo 0 || echo 1)" "SocketMode lines: $n"

# B1c this release's own unit and an administrator's value are left byte for byte
d="$T/b2"; mkdir "$d"; cp "$UNIT" "$d/sdclient.socket"; out=$(runblock "$d")
row "B1c this release's own unit (SocketMode=0660 already) is left byte for byte, and the block says nothing" "$(cmp -s "$UNIT" "$d/sdclient.socket" && [[ "$out" != *Restricting* ]] && echo 0 || echo 1)" "output: $out"
d="$T/b3"; mkdir "$d"; sed 's/^SocketMode=.*/SocketMode=0666/' "$UNIT" > "$d/sdclient.socket"; cp "$d/sdclient.socket" "$d/before"; out=$(runblock "$d")
row "B1d an administrator's own SocketMode=0666 is left alone (the install tightens a default, it does not overrule a choice)" "$(cmp -s "$d/before" "$d/sdclient.socket" && echo 0 || echo 1)" "now: $(grep '^SocketMode' "$d/sdclient.socket" | tr '\n' ' ')"

# B1e no SocketGroup line
d="$T/b4"; mkdir "$d"; grep -v '^SocketGroup=' "$OLD" > "$d/sdclient.socket"; out=$(runblock "$d")
n=$(grep -c '^SocketMode=0660$' "$d/sdclient.socket")
row "B1e a unit with no SocketGroup= line gets SocketMode=0660 under [Socket]" "$([ "$n" = 1 ] && awk '/^\[Socket\]$/{s=1;next} /^\[/{s=0} s&&/^SocketMode=0660$/{f=1} END{exit f?0:1}' "$d/sdclient.socket" && echo 0 || echo 1)" "mode lines $n"

# B1f no unit at all
d="$T/b5"; mkdir "$d"; out=$(runblock "$d"); rc=$?
row "B1f no sdclient.socket at all is not an error and creates nothing" "$([ "$rc" = 0 ] && [[ "$out" == *REACHED-END* ]] && [ -z "$(ls -A "$d")" ] && echo 0 || echo 1)" "rc=$rc output: $out"

# R1 runtime: what systemd makes of it
if systemctl --user is-system-running >/dev/null 2>&1 || [ "$(systemctl --user is-system-running 2>/dev/null)" = degraded ]; then
  RD="$T/run"; mkdir "$RD"; stamp=$$-$RANDOM
  systemd-run --user --quiet --collect --unit=zzsm-ctl-$stamp --socket-property=ListenStream="$RD/ctl.sock" --socket-property=Accept=yes -- /bin/true >/dev/null 2>&1
  systemd-run --user --quiet --collect --unit=zzsm-set-$stamp --socket-property=ListenStream="$RD/set.sock" --socket-property=SocketMode="$mode" --socket-property=Accept=yes -- /bin/true >/dev/null 2>&1
  for i in 1 2 3 4 5 6 7 8 9 10; do [ -S "$RD/ctl.sock" ] && [ -S "$RD/set.sock" ] && break; sleep 0.3; done
  mc=$(stat -c %a "$RD/ctl.sock" 2>/dev/null); ms=$(stat -c %a "$RD/set.sock" 2>/dev/null)
  systemctl --user stop "zzsm-ctl-$stamp.socket" "zzsm-set-$stamp.socket" >/dev/null 2>&1
  row "R1 the control: a socket unit with no SocketMode= makes a 666 Unix socket (what the live system had)" "$([ "$mc" = 666 ] && echo 0 || echo 1)" "mode '$mc'"
  row "R1b and with SocketMode=$mode (the value the shipped unit carries) it is 660" "$([ "$ms" = 660 ] && echo 0 || echo 1)" "mode '$ms'"
else
  skipped=$((skipped+2)); echo "  [SKIPPED] R1, R1b: the user's systemd is not available here; the runtime rows did not run and are not passes"
fi

echo "test-install-socketmode: $pass passed, $fail failed, $skipped skipped"
[ "$pass" -eq 0 ] && { echo "test-install-socketmode: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
