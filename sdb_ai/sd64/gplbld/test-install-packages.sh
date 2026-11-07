#!/bin/bash
#
# test-install-packages.sh - the installer's PACKAGES block (3 Nov 2026, S.94; 7 Nov 2026): the one required apt-get install, then gpm, the console
# mouse daemon, in a call of its own whose failure is a warning (owner, 3 Nov 2026: "the decision was the the installer installs gpm, not mentions
# it"; 7 Nov 2026, after an install in a container stopped on it: "a gpm installation failure doesn't kill the install").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-packages.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-packages.sh --selftest
#   INSTALLER=<copy of the installer> bash .../test-install-packages.sh                     (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function here), no apt-get (a stub that logs its arguments; it fails the required call when RC_REQ is not 0 and
# the gpm call when RC_GPM is not 0).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
#   P1  the required call is ONE "apt-get -y install" of git build-essential micro lynx libsodium-dev libssl-dev openssl openssh-server python3-dev,
#       and gpm is NOT in it
#   P1b gpm is installed by a second call, "apt-get -y install gpm" alone, after the required one; nothing is removed when it succeeds
#   P2  a failing required call stops the installer with exit 1 and the same words as before ("Package installation using apt-get failed.  Exiting
#       script."), and gpm is never asked for
#   P6  a failing gpm call does NOT stop the installer: the block reaches its end with status 0, prints "WARNING: gpm could not be installed", and
#       asks apt-get to remove gpm (a package dpkg left half-configured would make every later apt-get fail)
#   P3  the installer does not enable, start or mask gpm itself anywhere (the package's postinst enables and starts it), and installs it in that one
#       call only
#   P4  deletesdcore.sh does not remove gpm (a distribution package, left installed like git and lynx)
#   P5  the block runs to its end under the installer's own `set` options and IFS
# ANCHORED ON THE ARGUMENTS the stubbed apt-get was given and the block's exit status; the words are checked only for the two messages a person reads.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
DEL="$TREE/deletesdcore.sh"
WANT="git build-essential micro lynx libsodium-dev libssl-dev openssl openssh-server python3-dev"

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
  inst_mutant gpm-back-in-required  "$B s/ lynx libsodium-dev / lynx gpm libsodium-dev /"
  inst_mutant gpm-call-gone         "$B s/apt-get -y install gpm; then/true; then/"
  inst_mutant gpm-fatal             "$B{/apt-get -y remove gpm/a\\    exit 1
}"
  inst_mutant gpm-no-remove         "$B s/sudo apt-get -y remove gpm/true/"
  inst_mutant gpm-no-warning        "$B s/WARNING: gpm could not be installed/gpm skipped/"
  inst_mutant gpm-first             "$B s/apt-get -y install git build-essential/apt-get -y install gpm git build-essential/"
  inst_mutant lynx-gone             "$B s/ micro lynx / micro /"
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

runblock() {   # log rc-required rc-gpm -> output; the return code is the block's (exit inside the block ends the bash -c)
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" LOG="$1" RC_REQ="$2" RC_GPM="$3" bash -c '
      eval "$OPTS"; eval "$IFSL"
      RED=""; NC=""
      sudo() { "$@"; }
      apt-get() {
        { printf "apt-get"; printf " %s" "$@"; echo; } >> "$LOG"
        local IFS=" "
        case " $* " in
          *" remove "*) return 0 ;;
          *" install gpm ") return "$RC_GPM" ;;
          *) return "$RC_REQ" ;;
        esac
      }
      eval "$BLOCK"
      echo REACHED-END' 2>&1
}

# P1 / P1b / P5: both calls succeed
: > "$T/p1.log"
out=$(runblock "$T/p1.log" 0 0); rc=$?
echo "  P1 apt-get was called: $(tr '\n' '|' < "$T/p1.log")"
n=$(grep -c '^apt-get' "$T/p1.log")
args=$(sed -n '1p' "$T/p1.log")
second=$(sed -n '2p' "$T/p1.log")
missing=""
for p in $(echo "$WANT" | tr ' ' '\n'); do
  case " $args " in *" $p "*) ;; *) missing="$missing $p" ;; esac
done
row "P1 the required call is one apt-get -y install of the required packages, gpm not among them" \
    "$([[ "$args" == "apt-get -y install "* ]] && [ -z "$missing" ] && [[ " $args " != *" gpm "* ]] && echo 0 || echo 1)" "args='$args' missing:$missing"
row "P1b gpm by a second call of its own after the required one, and nothing removed" \
    "$([ "$n" = 2 ] && [ "$second" = "apt-get -y install gpm" ] && echo 0 || echo 1)" "calls=$n second='$second'"
row "P5 the block reaches its end under the installer's own set options and IFS" "$([ "$rc" = 0 ] && [[ "$out" == *REACHED-END* ]] && echo 0 || echo 1)" "rc=$rc out: $out"

# P2: the required call fails
: > "$T/p2.log"
out=$(runblock "$T/p2.log" 100 0); rc=$?
row "P2 a failing required apt-get stops the installer with exit 1 and the same words, before gpm" \
    "$([ "$rc" = 1 ] && [[ "$out" != *REACHED-END* ]] && [[ "$out" == *"Package installation using apt-get failed.  Exiting script."* ]] && ! grep -q 'install gpm' "$T/p2.log" && echo 0 || echo 1)" "rc=$rc log: $(tr '\n' '|' < "$T/p2.log") out: $out"

# P6: the gpm call fails
: > "$T/p6.log"
out=$(runblock "$T/p6.log" 0 100); rc=$?
echo "  P6 apt-get was called: $(tr '\n' '|' < "$T/p6.log")"
row "P6 a failing gpm install warns, removes gpm and goes on to the end with status 0" \
    "$([ "$rc" = 0 ] && [[ "$out" == *REACHED-END* ]] && [[ "$out" == *"WARNING: gpm could not be installed"* ]] && grep -qx 'apt-get -y remove gpm' "$T/p6.log" && echo 0 || echo 1)" "rc=$rc log: $(tr '\n' '|' < "$T/p6.log") out: $out"

# P3: nothing else in the installer touches gpm as a service or installs it again
code=$(grep -v '^ *#' "$INST")
svc=$(printf '%s\n' "$code" | grep -n -E 'systemctl[^#]*gpm|update-rc\.d[^#]*gpm|service +gpm' || true)
twice=$(printf '%s\n' "$code" | grep -v -E '^ *echo ' | grep -n -E 'apt-get[^#]*install[^#]*\bgpm\b' | wc -l)
row "P3 the installer does not enable, start or mask gpm itself and installs it in that one call only" \
    "$([ -z "$svc" ] && [ "$twice" = 1 ] && echo 0 || echo 1)" "service lines: $svc; apt-get lines naming gpm: $twice"

# P4: the deleter leaves the package
dl=$(grep -v '^ *#' "$DEL" | grep -n -E '(apt-get|apt|dpkg)[^#]*(remove|purge|-r|-P)[^#]*\bgpm\b|systemctl[^#]*gpm' || true)
row "P4 deletesdcore.sh neither removes gpm nor stops or disables its service" "$([ -z "$dl" ] && echo 0 || echo 1)" "$dl"

echo "test-install-packages: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-packages: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
