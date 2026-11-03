#!/bin/bash
#
# test-install-packages.sh - the installer's PACKAGES block (3 Nov 2026, S.94): the one required apt-get install, which now includes gpm, the console mouse
# daemon (owner, 3 Nov 2026: "the decision was the the installer installs gpm, not mentions it").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-packages.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-packages.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-packages.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no apt-get (a stub that logs its arguments; STUB_APT_RC makes it fail).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.
#
#   P1  ONE apt-get call, "-y install", and gpm is among its packages with the ones that were there before (git build-essential micro lynx libsodium-dev
#       libssl-dev openssl openssh-server python3-dev)
#   P2  a failing apt-get stops the installer with exit 1 and the same words as before ("Package installation using apt-get failed.  Exiting script.")
#   P3  the installer does not enable, start or mask gpm itself anywhere (the package's postinst enables and starts it), and does not install it a second time
#   P4  deletesdcore.sh does not remove gpm (a distribution package, left installed like git and lynx)
#   P5  the block runs to its end under the installer's own `set` options and IFS
# ANCHORED ON THE ARGUMENTS the stubbed apt-get was given and the block's exit status, not on the installer's own words.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
DEL="$TREE/deletesdcore.sh"
WANT="git build-essential micro lynx gpm libsodium-dev libssl-dev openssl openssh-server python3-dev"

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
  B='/^# PACKAGES-BEGIN/,/^# PACKAGES-END/'
  inst_mutant gpm-gone              "$B s/ lynx gpm / lynx /"
  inst_mutant gpm-optional          "$B s/ lynx gpm / lynx /;/^# PACKAGES-END/a sudo apt-get -y install gpm || true"
  inst_mutant lynx-gone             "$B s/ lynx gpm / gpm /"
  inst_mutant no-exit               "$B{/    exit 1/d}"
  inst_mutant exit-0                "$B s/    exit 1/    exit 0/"
  inst_mutant wording               "$B s/Package installation using apt-get failed/Package installation failed/"
  inst_mutant enable-gpm            "/^# PACKAGES-END/a sudo systemctl enable --now gpm.service || true"
  inst_mutant begin-marker-gone     "s/^# PACKAGES-BEGIN/# packages-begin/"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

[ -r "$DEL" ] || { echo "test-install-packages: CANNOT RUN - no deletesdcore.sh at $DEL"; exit 2; }
BLOCK=$(awk '/^# PACKAGES-BEGIN$/{f=1;next} /^# PACKAGES-END$/{f=0} f{print}' "$INST")
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "deleter   : $DEL"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-packages: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-packages: CANNOT RUN - no PACKAGES block in the installer"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

runblock() {   # log apt-rc -> output; the return code is the block's (exit inside the block ends the bash -c)
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" LOG="$1" RC="$2" bash -c '
      eval "$OPTS"; eval "$IFSL"
      RED=""; NC=""
      sudo() { "$@"; }
      apt-get() { { printf "apt-get"; printf " %s" "$@"; echo; } >> "$LOG"; return "$RC"; }
      eval "$BLOCK"
      echo REACHED-END' 2>&1
}

# P1 / P5: apt-get succeeds
: > "$T/p1.log"
out=$(runblock "$T/p1.log" 0); rc=$?
echo "  P1 apt-get was called: $(tr '\n' '|' < "$T/p1.log")"
n=$(grep -c '^apt-get' "$T/p1.log")
args=$(sed -n '1p' "$T/p1.log")
missing=""
for p in $(echo "$WANT" | tr ' ' '\n'); do
  case " $args " in *" $p "*) ;; *) missing="$missing $p" ;; esac
done
row "P1 one apt-get -y install, and gpm is in it beside the packages that were there before" \
    "$([ "$n" = 1 ] && [[ "$args" == "apt-get -y install "* ]] && [ -z "$missing" ] && echo 0 || echo 1)" "calls=$n args='$args' missing:$missing"
row "P5 the block reaches its end under the installer's own set options and IFS" "$([ "$rc" = 0 ] && [[ "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "rc=$rc out: $out"

# P2: apt-get fails
: > "$T/p2.log"
out=$(runblock "$T/p2.log" 100); rc=$?
row "P2 a failing apt-get stops the installer with exit 1 and the same words" \
    "$([ "$rc" = 1 ] && [[ "$out" != *REACHED-END* ]] && [[ "$out" == *"Package installation using apt-get failed.  Exiting script."* ]] && echo 0 || echo 1)" "rc=$rc out: $out"

# P3: nothing else in the installer touches gpm as a service or installs it again
code=$(grep -v '^ *#' "$INST")
svc=$(printf '%s\n' "$code" | grep -n -E 'systemctl[^#]*gpm|update-rc\.d[^#]*gpm|service +gpm' || true)
twice=$(printf '%s\n' "$code" | grep -n -E 'apt-get[^#]*install[^#]*\bgpm\b' | wc -l)
row "P3 the installer does not enable, start or mask gpm itself and installs it in that one call only" \
    "$([ -z "$svc" ] && [ "$twice" = 1 ] && echo 0 || echo 1)" "service lines: $svc; apt-get lines naming gpm: $twice"

# P4: the deleter leaves the package
dl=$(grep -v '^ *#' "$DEL" | grep -n -E '(apt-get|apt|dpkg)[^#]*(remove|purge|-r|-P)[^#]*\bgpm\b|systemctl[^#]*gpm' || true)
row "P4 deletesdcore.sh neither removes gpm nor stops or disables its service" "$([ -z "$dl" ] && echo 0 || echo 1)" "$dl"

echo "test-install-packages: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-packages: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
