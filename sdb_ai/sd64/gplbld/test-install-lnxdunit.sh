#!/bin/bash
#
# test-install-lnxdunit.sh - the restart of a dead audit daemon, option A (25 Oct 2026): the installer's LNXDUNIT block puts sd-lnxd.service, and the sd.service that
# wants it, in place over an sd.service that does not mention it.  (The first-install copy does it for a machine with no sd.service; this block is for the one that has
# an older sd.service, whose "sd -start" would fork a daemon with nothing to restart it.)
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-lnxdunit.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-lnxdunit.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-lnxdunit.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no root, no systemd (a function here).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
#   B1  an older sd.service (no sd-lnxd.service in it): both of this release's files are put in place, byte for byte, installed root:root mode 0644, systemd reloaded once, and
#       the block says so
#   B2  a second run changes nothing, reloads nothing and says nothing
#   B3  a sd.service that already wants sd-lnxd.service (the first-install copy did its work) is left alone: nothing installed, nothing reloaded
#   B4  no sd.service at all is not an error and creates nothing
#   B5  the block runs to its end under the installer's own `set` options and IFS (the first real installs failed on code that had only been run under `set` alone)
# ANCHORED ON THE DISK: the files the directory ends up with, and the arguments the stubbed `install` was given.

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
    sed -e "$2" "$TREE/installsdcore.sh" > "$f"
    if cmp -s "$TREE/installsdcore.sh" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); total=$((total+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$1.out" 2>&1; judge "$1" $?
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  B='/^# LNXDUNIT-BEGIN/,/^# LNXDUNIT-END/'
  inst_mutant block-always            "$B s/ \&\& ! grep -q 'sd-lnxd\\\\.service' \"\$SYSTEMDPATH\/sd.service\"//"
  inst_mutant block-never             "$B s/if \[ -f \"\$SYSTEMDPATH\/sd.service\" \] \&\& /if false \&\& /"
  inst_mutant block-no-unit-copy      "$B /sd-lnxd.service \"\$SYSTEMDPATH\/sd-lnxd.service\"\$/d"
  inst_mutant block-no-service-copy   "$B /usr\/lib\/systemd\/system\/sd.service \"\$SYSTEMDPATH\/sd.service\"\$/d"
  inst_mutant block-no-reload         "$B /systemctl daemon-reload/d"
  inst_mutant block-mode-0666         "$B s/-m 0644/-m 0666/"
  inst_mutant block-owner-sdsys       "$B s/-o root -g root/-o sdsys -g sdusers/"
  inst_mutant block-wrong-grep-file   "$B s/grep -q 'sd-lnxd\\\\.service' \"\$SYSTEMDPATH\/sd.service\"/grep -q 'sd-lnxd\\\\.service' \"\$SYSTEMDPATH\/sdclient.socket\"/"
  inst_mutant begin-marker-gone       "s/^# LNXDUNIT-BEGIN/# lnxdunit-begin/"
  inst_mutant end-marker-gone         "s/^# LNXDUNIT-END/# lnxdunit-end/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

[ -r "$SDU/sd.service" ] && [ -r "$SDU/sd-lnxd.service" ] || { echo "test-install-lnxdunit: CANNOT RUN - the tree has no sd.service and sd-lnxd.service at $SDU"; exit 2; }
BLOCK=$(awk '/^# LNXDUNIT-BEGIN$/{f=1;next} /^# LNXDUNIT-END$/{f=0} f{print}' "$INST")
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "units     : $SDU"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-lnxdunit: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-lnxdunit: CANNOT RUN - no LNXDUNIT block in the installer"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# the clone the installer runs in: the two units under their relative path
WORK="$T/clone"; mkdir -p "$WORK/usr/lib/systemd/system"
cp "$SDU/sd.service" "$SDU/sd-lnxd.service" "$WORK/usr/lib/systemd/system/"

# sd.service as an install made before this release has it
OLD="$T/old.service"
printf '%s\n' '[Unit]' 'Description=SD service start' '' '[Service]' 'Type=oneshot' 'RemainAfterExit=yes' 'ExecStart=/usr/local/sdsys/bin/sd -start' \
  'ExecStop=/usr/local/sdsys/bin/sd -stop' '' '[Install]' 'WantedBy=default.target' > "$OLD"

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
# B1 an older sd.service
d="$T/b1"; mkdir "$d"; cp "$OLD" "$d/sd.service"; : > "$T/b1.log"
out=$(runblock "$d" "$T/b1.log"); rc=$?
case "$out" in *REACHED-END*) reached=0 ;; *) reached=1 ;; esac
same_s=$(cmp -s "$SDU/sd.service" "$d/sd.service" && echo 0 || echo 1)
same_l=$(cmp -s "$SDU/sd-lnxd.service" "$d/sd-lnxd.service" && echo 0 || echo 1)
n_inst=$(grep -c '^install -o root -g root -m 0644 ' "$T/b1.log")
n_rel=$(grep -c '^systemctl daemon-reload' "$T/b1.log")
row "B1 an older sd.service gets both of this release's files, installed root:root 0644, systemd reloaded once, and the block says so" \
    "$([ "$reached" = 0 ] && [ "$same_s" = 0 ] && [ "$same_l" = 0 ] && [ "$n_inst" = 2 ] && [ "$n_rel" = 1 ] && [[ "$out" == *"sd-lnxd.service"* ]] && echo 0 || echo 1)" \
    "reached=$reached sd.service same=$same_s sd-lnxd same=$same_l installs=$n_inst reloads=$n_rel out: $out; log: $(cat "$T/b1.log" | tr '\n' '|')"

# B2 a second run
: > "$T/b2.log"; cp "$d/sd.service" "$T/before.s"; cp "$d/sd-lnxd.service" "$T/before.l"
out=$(runblock "$d" "$T/b2.log")
row "B2 a second run changes nothing, reloads nothing and says nothing" \
    "$(cmp -s "$T/before.s" "$d/sd.service" && cmp -s "$T/before.l" "$d/sd-lnxd.service" && [ ! -s "$T/b2.log" ] && [[ "$out" != *Installing* ]] && echo 0 || echo 1)" "log: $(cat "$T/b2.log" | tr '\n' '|') out: $out"

# B3 a sd.service that already wants the unit
d="$T/b3"; mkdir "$d"; cp "$SDU/sd.service" "$d/sd.service"; : > "$T/b3.log"
out=$(runblock "$d" "$T/b3.log")
row "B3 this release's own sd.service (it mentions sd-lnxd.service) is left alone: nothing installed, nothing reloaded, no sd-lnxd.service made" \
    "$(cmp -s "$SDU/sd.service" "$d/sd.service" && [ ! -s "$T/b3.log" ] && [ ! -e "$d/sd-lnxd.service" ] && echo 0 || echo 1)" "log: $(cat "$T/b3.log" | tr '\n' '|')"

# B4 no sd.service at all
d="$T/b4"; mkdir "$d"; : > "$T/b4.log"
out=$(runblock "$d" "$T/b4.log"); rc=$?
row "B4 no sd.service at all is not an error and creates nothing" "$([ "$rc" = 0 ] && [[ "$out" == *REACHED-END* ]] && [ -z "$(ls -A "$d")" ] && [ ! -s "$T/b4.log" ] && echo 0 || echo 1)" "rc=$rc output: $out"

# B5 under the installer's options
case "$(runblock "$T/b1" "$T/b5.log")" in *REACHED-END*) r5=0 ;; *) r5=1 ;; esac
row "B5 the block reaches its end under the installer's own set options and IFS" "$r5" "did not reach the end"

echo "test-install-lnxdunit: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-lnxdunit: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
