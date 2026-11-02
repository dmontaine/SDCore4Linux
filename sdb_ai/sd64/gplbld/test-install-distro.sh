#!/bin/bash
#
# test-install-distro.sh - installsdcore.sh refuses every distribution but Debian and Ubuntu, BEFORE it changes
# anything (S.105, owner 2 Nov 2026: "remove Fedora support for this release", then "Take it out").
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-distro.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-distro.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-distro.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd, no network.  Exit 0 every row passed, 1 a row failed, 2 it could not run
# (a missing function or call is exit 2, never a pass).
#
# WHAT IT CHECKS.
#   A  detect_distro() is cut out of the installer and RUN under the installer's own `set` and `IFS` lines (S.48 and
#      S.89: a block tested without them passed while real installs stopped), with /etc/os-release replaced in the
#      function's text by a fake file this test writes, and `sudo` a function that records any call.  Debian, Ubuntu,
#      Linux Mint and Pop!_OS go on quietly; Fedora, Rocky, AlmaLinux, RHEL, Arch, openSUSE, an ID that only CONTAINS
#      "debian" and a machine with no os-release file are refused: exit 1, the message names Debian and Ubuntu and
#      Fedora and says nothing has been changed, and sudo is never called.
#   B  the CALL, by position in the installer: exactly one, after the "already installed" refusal, before the network
#      check, the banner, the first question (Continue?), `sudo -v`, and every top-level line that runs sudo; and no
#      line of code is left that runs dnf or tests is_fedora (the package install is apt-get's alone).
#
# NOT MEASURED HERE, and said so: a real Fedora or Debian machine running the whole installer (that is the VM).

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

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
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -5 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant fedora-accepted       's/\*" debian "\*|\*" ubuntu "\*) return 0/*" debian "*|*" ubuntu "*|*" fedora "*) return 0/'
  mutant substring-match       's/\*" debian "\*|\*" ubuntu "\*) return 0/*debian*|*ubuntu*) return 0/'
  mutant no-file-accepted      's/^  local ids=""$/  local ids=" debian "/'
  mutant refusal-returns       '/^detect_distro() {/,/^}/ s/^  exit 1$/  return 0/'
  mutant call-deleted          '/^detect_distro$/d'
  mutant call-after-sudo       '/^detect_distro$/d; s/^if ! sudo -v; then$/detect_distro\n&/'
  mutant call-after-banner     '/^detect_distro$/d; s/^read -r -p "Continue? (y\/N) " yn$/detect_distro\n&/'
  mutant dnf-back              's/^sudo apt-get -y --ignore-missing install libcrypt-dev || true$/&\nsudo dnf -y install git || true/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST"; grep -m1 -E '^IFS=' "$INST")
case "$OPTS" in *IFS=*) ;; *) echo "test-install-distro: CANNOT RUN - no IFS line in the installer (S.89)"; exit 2;; esac
FN=$(awk '/^detect_distro\(\) \{/{f=1} f{print} f&&/^}$/{exit}' "$INST")
echo "installer : $INST"
echo "options   : $(printf '%s' "$OPTS" | tr '\n' ' ')"
[ -z "$FN" ] && { echo "test-install-distro: CANNOT RUN - no detect_distro() in the installer (nothing to check)"; exit 2; }
case "$FN" in *"/etc/os-release"*) ;; *) echo "test-install-distro: CANNOT RUN - detect_distro() does not read /etc/os-release"; exit 2;; esac
echo "function  : $(printf '%s\n' "$FN" | wc -l) lines, detect_distro() to its closing brace"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export OPTS

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
run_fn() {   # fake os-release path (may not exist); prints the output, then REACHED-END; rc is the function's
  FAKEFN="${FN//\/etc\/os-release/$1}" CALLS="$T/sudo.calls" bash -c '
      eval "$OPTS"
      sudo() { echo "$*" >> "$CALLS"; return 1; }
      RED=; NC=
      eval "$FAKEFN"
      detect_distro
      echo "REACHED-END"' 2>&1
}
case_os() {   # label, expect (go|refuse), os-release text or "<none>"
  local label="$1" expect="$2" text="$3" f="$T/os-release.$1" out rc
  rm -f "$T/sudo.calls"
  if [ "$text" != "<none>" ]; then printf '%s\n' "$text" > "$f"; fi
  out=$(run_fn "$f"); rc=$?
  echo "    $label  (os-release: $(printf '%s' "$text" | tr '\n' ' '))  rc=$rc"
  printf '%s\n' "$out" | sed '/^$/d; s/^/      | /'
  if [ -e "$T/sudo.calls" ]; then row "$label: sudo is never called" 1 "sudo called: $(tr '\n' ';' < "$T/sudo.calls")"; fi
  if [ "$expect" = go ]; then
    row "$label: goes on quietly" "$([ "$rc" -eq 0 ] && [ "$out" = "REACHED-END" ] && echo 0 || echo 1)" "rc=$rc"
  else
    row "$label: refused, exit 1, before going on" \
        "$([ "$rc" -eq 1 ] && ! printf '%s' "$out" | grep -q REACHED-END && echo 0 || echo 1)" "rc=$rc"
    row "$label: the refusal names Debian and Ubuntu, Fedora, and says nothing has been changed" \
        "$(printf '%s' "$out" | grep -q 'supports Debian and Ubuntu' && printf '%s' "$out" | grep -q 'Fedora, RHEL' \
           && printf '%s' "$out" | grep -q 'Nothing has been changed' && echo 0 || echo 1)" "wording missing"
    if [ "$text" = "<none>" ]; then
      row "$label: says there is no os-release to read" "$(printf '%s' "$out" | grep -q 'there is no' && echo 0 || echo 1)" "no such line"
    else
      local id; id=$(printf '%s\n' "$text" | sed -n 's/^ID=//p' | tr -d '"')
      # the path in the message is the fake file's (the function's text was rewritten), so match on ": ID)"
      row "$label: names the ID it read ($id)" "$(printf '%s' "$out" | grep -qF "not supported (read from $f: $id)." && echo 0 || echo 1)" "ID not named"
    fi
  fi
}

echo "--- A: detect_distro on fake os-release files"
case_os debian   go     'ID=debian'
case_os ubuntu   go     $'ID=ubuntu\nID_LIKE=debian'
case_os mint     go     $'ID=linuxmint\nID_LIKE=ubuntu'
case_os pop      go     $'ID=pop\nID_LIKE="ubuntu debian"'
case_os fedora   refuse 'ID=fedora'
case_os rocky    refuse $'ID="rocky"\nID_LIKE="rhel centos fedora"'
case_os alma     refuse $'ID="almalinux"\nID_LIKE="rhel centos fedora"'
case_os rhel     refuse $'ID="rhel"\nID_LIKE="fedora"'
case_os arch     refuse 'ID=arch'
case_os opensuse refuse $'ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"'
case_os mydebian refuse $'ID=mydebian\nID_LIKE=notubuntu'
case_os missing  refuse '<none>'

echo "--- B: where the call sits in the installer"
code() { grep -n -E '^[[:space:]]*[^#[:space:]]' "$INST"; }          # numbered lines that are not comments or blank
first() { code | grep -E "$1" | head -1 | cut -d: -f1; }
L_CALL=$(first '^[0-9]+:detect_distro[[:space:]]*$')
N_CALL=$(code | grep -c -E '^[0-9]+:[[:space:]]*detect_distro[[:space:]]*$')
L_GATE=$(first '^[0-9]+:if \[ -f +"/usr/local/sdsys/bin/sd" \]')
L_NET=$(first '^[0-9]+:net_preflight +github\.com')
L_BANNER=$(first '^[0-9]+:printf "%bSD installer')
L_ASK=$(first '^[0-9]+:read -r -p "Continue\?')
L_SUDOV=$(first '^[0-9]+:if ! sudo -v')
# The first sudo the script RUNS: a line outside every function body (bodies run only when called), where sudo is
# the command (at the start, after if / ! / && / || / ; / |), not a word in a message.
L_SUDO1=$(awk '/^[A-Za-z_][A-Za-z0-9_]*\(\) *\{/{infn=1} infn&&/^}/{infn=0; next}
               !infn && !/^[[:space:]]*#/ && /(^[[:space:]]*(if[[:space:]]+)?(![[:space:]]+)?|[;&|][[:space:]]*)sudo /{print NR; exit}' "$INST")
echo "      call ${L_CALL:-none} ($N_CALL in all); already-installed ${L_GATE:-?}; net_preflight ${L_NET:-?}; banner ${L_BANNER:-?};"
echo "      Continue? ${L_ASK:-?}; sudo -v ${L_SUDOV:-?}; first top-level sudo ${L_SUDO1:-?}"
[ -z "$L_CALL" ] && { row "B0 the installer calls detect_distro" 1 "no call"; echo "test-install-distro: $pass passed, $fail failed"; exit 1; }
lt() { [ -n "$1" ] && [ -n "$2" ] && [ "$1" -lt "$2" ] && echo 0 || echo 1; }
row "B1 exactly one call"                                  "$([ "$N_CALL" = 1 ] && echo 0 || echo 1)" "$N_CALL calls"
row "B2 after the 'already installed' refusal"             "$(lt "$L_GATE" "$L_CALL")" "gate $L_GATE call $L_CALL"
row "B3 before the network check"                          "$(lt "$L_CALL" "$L_NET")" "call $L_CALL net $L_NET"
row "B4 before the banner"                                 "$(lt "$L_CALL" "$L_BANNER")" "call $L_CALL banner $L_BANNER"
row "B5 before the first question (Continue?)"             "$(lt "$L_CALL" "$L_ASK")" "call $L_CALL ask $L_ASK"
row "B6 before sudo -v"                                    "$(lt "$L_CALL" "$L_SUDOV")" "call $L_CALL sudo -v $L_SUDOV"
row "B7 before the first top-level line that runs sudo"    "$(lt "$L_CALL" "$L_SUDO1")" "call $L_CALL sudo $L_SUDO1"
DNF=$(code | grep -E '(^|[^A-Za-z_-])(dnf|is_fedora)([^A-Za-z_-]|$)' | head -3)
row "B8 no line of code runs dnf or tests is_fedora"       "$([ -z "$DNF" ] && echo 0 || echo 1)" "$DNF"
APT=$(code | grep -E '^[0-9]+:if ! sudo apt-get -y install ' | head -1)
row "B9 the package install is apt-get's, at the top level (no distribution branch around it)" "$([ -n "$APT" ] && echo 0 || echo 1)" "no top-level apt-get install"

echo "test-install-distro: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
