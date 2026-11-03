#!/bin/bash
#
# test-install-unitrefresh.sh - the installer's UNITREFRESH block (3 Nov 2026): on an upgrade, which keeps the units it has, the three units SD owns whole
# (sd.service, sd-lnxd.service, sdclient@.service) are put in place when they differ from this release's; sdclient.socket, which the installer edits in place, is not.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-unitrefresh.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-unitrefresh.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-unitrefresh.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no root, no systemd (a function here).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
#   U1  an upgrade whose sdclient@.service is older (the unit before W.11 F5: no ProtectKernelTunables= or the other sandbox settings) and whose sd-lnxd.service is missing: both are put in place byte for byte, installed root:root
#       0644, the up-to-date sd.service is not touched, systemd is reloaded once, and the block names each unit it refreshed
#   U2  sdclient.socket (an administrator's SocketMode=0666, a listener the installer rebound) is left exactly as it was
#   U3  a second run changes nothing, reloads nothing and says nothing
#   U4  a changed sd.service is refreshed too (the three are treated alike)
#   U5  no sd.service at all (no systemd install of SD) is not an error and creates nothing
#   U6  the block runs to its end under the installer's own `set` options and IFS (IFS is newline and tab: the unit list must still split)
# ANCHORED ON THE DISK: the files the directory ends up with, and the arguments the stubbed `install` and `systemctl` were given.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
SDU="$TREE/sdb_ai/sd64/usr/lib/systemd/system"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  judge() {   # name, rc-of-the-run
    total=$((total+1))
    if [ "$2" -ne 0 ]; then echo "  [caught] $1 (exit $2)"; caught=$((caught+1))
    else echo "  [MISSED] $1: the check still passed"; missed=$((missed+1)); fi
  }
  inst_mutant() {   # name, sed expression applied to the installer
    local f="$T/$1.sh"
    if ! sed -e "$2" "$TREE/installsdcore.sh" > "$f"; then echo "  [MISSED] $1: the sed expression did not apply"; missed=$((missed+1)); total=$((total+1)); return; fi
    if cmp -s "$TREE/installsdcore.sh" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); total=$((total+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$1.out" 2>&1; judge "$1" $?
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  B='/^# UNITREFRESH-BEGIN/,/^# UNITREFRESH-END/'
  inst_mutant no-sdclient-unit      "$B s/ sdclient@.service; do/; do/"
  inst_mutant no-lnxd-unit          "$B s/ sd-lnxd.service / /"
  inst_mutant socket-too            "$B s/sdclient@.service; do/sdclient@.service sdclient.socket; do/"
  inst_mutant always-install        "$B s/if ! cmp -s /if ! true || cmp -s /"
  inst_mutant never-install         "$B s/if ! cmp -s /if false \&\& cmp -s /"
  inst_mutant no-reload             "$B{/systemctl daemon-reload/d}"
  inst_mutant reload-always         "$B s/if \[ \"\$units_refreshed\" = 1 \]/if true/"
  inst_mutant mode-0666             "$B s/-m 0644/-m 0666/"
  inst_mutant owner-sdsys           "$B s/-o root -g root/-o sdsys -g sdusers/"
  inst_mutant silent                "$B{/echo \"Refreshing the systemd unit/d}"
  inst_mutant begin-marker-gone     "s/^# UNITREFRESH-BEGIN/# unitrefresh-begin/"
  inst_mutant end-marker-gone       "s/^# UNITREFRESH-END/# unitrefresh-end/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

for u in sd.service sd-lnxd.service sdclient@.service sdclient.socket; do
  [ -r "$SDU/$u" ] || { echo "test-install-unitrefresh: CANNOT RUN - the tree has no $u at $SDU"; exit 2; }
done
grep -q '^ProtectKernelTunables=yes' "$SDU/sdclient@.service" || { echo "test-install-unitrefresh: CANNOT RUN - this release's sdclient@.service has no ProtectKernelTunables=yes, so U1's older unit is no older"; exit 2; }
BLOCK=$(awk '/^# UNITREFRESH-BEGIN$/{f=1;next} /^# UNITREFRESH-END$/{f=0} f{print}' "$INST")
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "units     : $SDU"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-unitrefresh: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-unitrefresh: CANNOT RUN - no UNITREFRESH block in the installer"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# the clone the installer runs in: the units under their relative path
WORK="$T/clone"; mkdir -p "$WORK/usr/lib/systemd/system"
cp "$SDU"/* "$WORK/usr/lib/systemd/system/"

runblock() {   # unit-dir log -> output; the return code is the block's
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" DIR="$1" LOG="$2" WORK="$WORK" bash -c '
      eval "$OPTS"; eval "$IFSL"
      sudo() { "$@"; }
      install() { { printf "install"; printf " %s" "$@"; echo; } >> "$LOG"; cp "${@: -2:1}" "${@: -1}"; }
      systemctl() { printf "systemctl"; printf " %s" "$@"; echo; } >> "$LOG"
      SYSTEMDPATH="$DIR"
      cd "$WORK"
      eval "$BLOCK"
      echo REACHED-END' 2>&1
}

# U1/U2: an upgrade - this release's sd.service, an older sdclient@.service, no sd-lnxd.service, an edited sdclient.socket
d="$T/u1"; mkdir "$d"; : > "$T/u1.log"
cp "$SDU/sd.service" "$d/sd.service"
grep -v -E '^(Protect|Restrict|LockPersonality|SystemCallArchitectures|#)' "$SDU/sdclient@.service" > "$d/sdclient@.service"
sed -e 's/^SocketMode=.*/SocketMode=0666/' -e 's/^ListenStream=127\.0\.0\.1:/ListenStream=0.0.0.0:/' "$SDU/sdclient.socket" > "$d/sdclient.socket"
cp "$d/sdclient.socket" "$T/socket.before"
echo "  before U1: sdclient@.service Protect lines $(grep -c '^Protect' "$d/sdclient@.service"), sd-lnxd.service present: $([ -e "$d/sd-lnxd.service" ] && echo yes || echo no)"
out=$(runblock "$d" "$T/u1.log")
case "$out" in *REACHED-END*) reached=0 ;; *) reached=1 ;; esac
same_c=$(cmp -s "$SDU/sdclient@.service" "$d/sdclient@.service" && echo 0 || echo 1)
same_l=$(cmp -s "$SDU/sd-lnxd.service" "$d/sd-lnxd.service" && echo 0 || echo 1)
n_inst=$(grep -c '^install -o root -g root -m 0644 ' "$T/u1.log")
n_sd=$(grep -c '^install .*/sd\.service$' "$T/u1.log")
n_rel=$(grep -c '^systemctl daemon-reload' "$T/u1.log")
echo "  after U1: sdclient@.service Protect lines $(grep -c '^Protect' "$d/sdclient@.service"); log: $(tr '\n' '|' < "$T/u1.log")"
row "U1 the older sdclient@.service and the missing sd-lnxd.service are put in place byte for byte, root:root 0644, sd.service untouched, one reload, each named" \
    "$([ "$reached" = 0 ] && [ "$same_c" = 0 ] && [ "$same_l" = 0 ] && [ "$n_inst" = 2 ] && [ "$n_sd" = 0 ] && [ "$n_rel" = 1 ] && [[ "$out" == *"unit sdclient@.service"* ]] && [[ "$out" == *"unit sd-lnxd.service"* ]] && echo 0 || echo 1)" \
    "reached=$reached sdclient@ same=$same_c sd-lnxd same=$same_l installs=$n_inst sd.service installs=$n_sd reloads=$n_rel out: $out"
row "U2 sdclient.socket (SocketMode=0666, listener on 0.0.0.0) is left exactly as it was" \
    "$(cmp -s "$T/socket.before" "$d/sdclient.socket" && ! grep -q 'sdclient\.socket' "$T/u1.log" && echo 0 || echo 1)" "socket changed, or named in the log: $(tr '\n' '|' < "$T/u1.log")"

# U3 a second run
: > "$T/u3.log"; cp -r "$d" "$T/u3.before"
out=$(runblock "$d" "$T/u3.log")
row "U3 a second run changes nothing, reloads nothing and says nothing" \
    "$(diff -r "$T/u3.before" "$d" >/dev/null && [ ! -s "$T/u3.log" ] && [[ "$out" != *Refreshing* ]] && [[ "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "log: $(tr '\n' '|' < "$T/u3.log") out: $out"

# U4 a changed sd.service
d="$T/u4"; mkdir "$d"; : > "$T/u4.log"
cp "$SDU/sd-lnxd.service" "$SDU/sdclient@.service" "$d/"; { cat "$SDU/sd.service"; echo "# an older line"; } > "$d/sd.service"
out=$(runblock "$d" "$T/u4.log")
row "U4 a sd.service that differs is refreshed as well, and only it" \
    "$(cmp -s "$SDU/sd.service" "$d/sd.service" && [ "$(grep -c '^install ' "$T/u4.log")" = 1 ] && [ "$(grep -c '^systemctl daemon-reload' "$T/u4.log")" = 1 ] && echo 0 || echo 1)" "log: $(tr '\n' '|' < "$T/u4.log")"

# U5 no sd.service
d="$T/u5"; mkdir "$d"; : > "$T/u5.log"
out=$(runblock "$d" "$T/u5.log"); rc=$?
row "U5 no sd.service at all is not an error and creates nothing" "$([ "$rc" = 0 ] && [[ "$out" == *REACHED-END* ]] && [ -z "$(ls -A "$d")" ] && [ ! -s "$T/u5.log" ] && echo 0 || echo 1)" "rc=$rc output: $out"

# U6 under the installer's options: the run of U1 was under them; check the options were the installer's IFS
row "U6 the block ran under the installer's set options and IFS (newline and tab) and still split the unit list" \
    "$([ "$reached" = 0 ] && [ "$IFSL" = "IFS=\$'\\n\\t'" ] && [ "$n_inst" = 2 ] && echo 0 || echo 1)" "IFS line: $IFSL reached=$reached installs=$n_inst"

echo "test-install-unitrefresh: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-unitrefresh: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
