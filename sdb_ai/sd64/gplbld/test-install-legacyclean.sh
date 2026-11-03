#!/bin/bash
#
# test-install-legacyclean.sh - the installer's LEGACY-CLEAN block (S.106, 2 Nov 2026; the owner: "remove the authenticator from both local and remote logins"): what an older dev install
# left of the authenticator code - its PAM module, the secret and recovery codes (/etc/sdcore/totp), the public status file and the login markers (/run/sdcore/marks) - is removed, but ONLY
# after ssh-forcecommand --clean-legacy has taken the PAM lines out (a PAM line naming a missing module would fail a login), nothing else under those directories is touched, an empty
# directory the files leave behind is removed, and the install goes on whatever happens.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-legacyclean.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-legacyclean.sh --selftest
#   INSTALLER=<copy> bash .../test-install-legacyclean.sh                       (what --selftest uses)
#
# FREE CHECK: no install, no sudo, no root.  The block is cut out between its markers, every absolute path in it is pointed at a scratch tree, and it runs under the installer's own
# `set -euo pipefail` and IFS with sudo a function that runs the command and ssh-forcecommand a stub that logs its call (STUB_FC_RC makes it refuse).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.  ANCHORED ON THE DISK: what is there before and after is listed in the output.
#
#   C1  an upgrade from a dev install with all four leftovers: the helper is called once with --clean-legacy and the leftovers were STILL THERE when it was called; afterwards all are gone
#   C2  ...and their neighbours are all still there: /etc/sdcore/jobs.d and another file, a second file in /usr/local/lib/sd, another entry in /run/sdcore
#   C3  a fresh machine (nothing there): the block ends, says nothing and removes nothing, and the helper is still asked (the null case of C1: a block that did nothing must not pass C1)
#   C4  the helper refuses (exit 2): NOTHING is removed - module, secret, status file and markers all still there - a WARNING names --clean-legacy, and the block ends
#   C5  the leftovers alone in their directories: /usr/local/lib/sd and /run/sdcore go with them
#   C6  the block runs to its end under the installer's set -euo pipefail and IFS (C1's run)
#   T1  the block is in the installer once, after the ssh boundary is applied (--install) and before the remote-access prompts
#   T2  nothing in the installer builds or installs the PAM module, asks the authenticator question or enrols a code any more, and libpam0g-dev is off the package list

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mutant() {   # name, old text, new text (in the installer)
    local name=$1 f="$T/m$total.sh"
    python3 -I -c 'import sys; t=open(sys.argv[1]).read(); o=sys.argv[3]; n=sys.argv[4]
if t.count(o) != 1: sys.exit(3)
open(sys.argv[2], "w").write(t.replace(o, n))' "$TREE/installsdcore.sh" "$f" "$2" "$3" || { echo "  [CANNOT] $name: its text is not in the file once"; missed=$((missed+1)); total=$((total+1)); return; }
    total=$((total+1))
    if INSTALLER="$f" bash "$THIS" > "$f.out" 2>&1; then echo "  [MISSED] $name"; missed=$((missed+1)); else echo "  [caught] $name"; caught=$((caught+1)); fi
  }
  mutant "the secret is removed before the helper is asked" 'if sudo /usr/local/sbin/ssh-forcecommand --clean-legacy; then' 'sudo rm -rf /etc/sdcore/totp
if sudo /usr/local/sbin/ssh-forcecommand --clean-legacy; then'
  mutant "the helper is never asked" 'if sudo /usr/local/sbin/ssh-forcecommand --clean-legacy; then' 'if true; then'
  mutant "the module is removed even when the helper refuses" 'echo "WARNING: the authenticator code lines' 'sudo rm -f /usr/local/lib/sd/pam_sdtotp.so; echo "WARNING: the authenticator code lines'
  mutant "a refusal stops the install" 'echo "WARNING: the authenticator code lines' 'exit 1; echo "WARNING: the authenticator code lines'
  mutant "all of /etc/sdcore goes" 'sudo rm -rf /etc/sdcore/totp' 'sudo rm -rf /etc/sdcore'
  mutant "the secret is left" 'sudo rm -rf /etc/sdcore/totp' ':'
  mutant "the status file is left" 'sudo rm -f /etc/sdcore/totp.public /usr/local/lib/sd/pam_sdtotp.so' 'sudo rm -f /usr/local/lib/sd/pam_sdtotp.so'
  mutant "the module is left" 'sudo rm -f /etc/sdcore/totp.public /usr/local/lib/sd/pam_sdtotp.so' 'sudo rm -f /etc/sdcore/totp.public'
  mutant "the markers are left" 'sudo rm -rf /run/sdcore/marks' ':'
  mutant "the emptied directories are left" 'sudo rmdir /usr/local/lib/sd /run/sdcore 2>/dev/null || true' ':'
  mutant "the directories go with what is in them" 'sudo rmdir /usr/local/lib/sd /run/sdcore 2>/dev/null || true' 'sudo rm -rf /usr/local/lib/sd /run/sdcore'
  mutant "the PAM module is built again" '# LEGACY-CLEAN-END' '# LEGACY-CLEAN-END
make pam_sdtotp.so'
  mutant "the PAM development package is back" 'libssl-dev openssl openssh-server python3-dev; then' 'libssl-dev libpam0g-dev openssl openssh-server python3-dev; then'
  echo "test-install-legacyclean --selftest: $total mutant(s), $missed not caught"
  [ "$missed" -eq 0 ] && [ "$total" -ge 13 ] && exit 0 || exit 1
fi

pass=0; fail=0
row() {   # id, label, condition-exit-status
  if [ "$3" -eq 0 ]; then echo "  [PASS] $1 $2"; pass=$((pass+1)); else echo "  [FAIL] $1 $2"; fail=$((fail+1)); fi
}

[ -f "$INST" ] || { echo "test-install-legacyclean: CANNOT RUN - no installer at $INST"; exit 2; }
BLOCK=$(awk '/^# LEGACY-CLEAN-BEGIN$/{f=1} f{print} /^# LEGACY-CLEAN-END$/{f=0}' "$INST")
[ -n "$BLOCK" ] && grep -q 'LEGACY-CLEAN-END' <<<"$BLOCK" || { echo "test-install-legacyclean: CANNOT RUN - no LEGACY-CLEAN block in $INST"; exit 2; }
echo "installer: $INST"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

mkroot() {   # R - the stub helper, which logs its call and whether the module was still there when it was called
  local r=$1
  mkdir -p "$r/etc/sdcore" "$r/usr/local/lib/sd" "$r/run/sdcore"
  cat > "$r/fc" <<'EOF'
#!/bin/bash
r=$(dirname "$0")
printf 'called %s' "$*" >> "$r/fc.log"
[ -e "$r/usr/local/lib/sd/pam_sdtotp.so" ] && printf ' module-present' >> "$r/fc.log"
[ -e "$r/etc/sdcore/totp" ] && printf ' secret-present' >> "$r/fc.log"
printf '\n' >> "$r/fc.log"
exit "${STUB_FC_RC:-0}"
EOF
  chmod 755 "$r/fc"
}

leftovers() {   # R - the four things an older install left
  local r=$1
  mkdir -p "$r/etc/sdcore/totp" "$r/run/sdcore/marks"
  printf 'secret\n' > "$r/etc/sdcore/totp/store"
  printf 'sdtotp 1\nenrolled yes\nscope remote\n' > "$r/etc/sdcore/totp.public"
  printf 'module\n' > "$r/usr/local/lib/sd/pam_sdtotp.so"
  printf 'uid=1000 \n' > "$r/run/sdcore/marks/boot.1"
}

run_block() {   # R - runs the block with every absolute path moved under R, under the installer's set options and IFS; prints its output, then "BLOCK-ENDED"
  local r=$1 body
  body=$(sed -e "s#/usr/local/sbin/ssh-forcecommand#$r/fc#g" -e "s#/etc/sdcore#$r/etc/sdcore#g" -e "s#/usr/local/lib/sd#$r/usr/local/lib/sd#g" -e "s#/run/sdcore#$r/run/sdcore#g" <<<"$BLOCK")
  bash -c "set -euo pipefail
IFS=\$'\\n\\t'
YELLOW=''; NC=''
sudo() { \"\$@\"; }
$body
echo BLOCK-ENDED" 2>&1
}

listing() { (cd "$1" && find . -mindepth 1 ! -name fc ! -name fc.log | LC_ALL=C sort | tr '\n' ' '); }

# C1 / C2 / C6
r="$T/c1"; mkroot "$r"; leftovers "$r"
mkdir -p "$r/etc/sdcore/jobs.d"; printf 'job\n' > "$r/etc/sdcore/jobs.d/nightly"; printf 'k\n' > "$r/etc/sdcore/other"
printf 'other\n' > "$r/usr/local/lib/sd/other-file"; printf 'x\n' > "$r/run/sdcore/other"
echo "C1 before: $(listing "$r")"
out=$(run_block "$r")
echo "C1 after:  $(listing "$r")"
echo "C1 helper: $(tr '\n' '|' < "$r/fc.log")"
echo "C1 said:   $(tr '\n' '|' <<<"$out")"
gone=0; for p in etc/sdcore/totp etc/sdcore/totp.public usr/local/lib/sd/pam_sdtotp.so run/sdcore/marks; do [ -e "$r/$p" ] || [ -L "$r/$p" ] || gone=$((gone+1)); done
row C1 "the helper is called once with --clean-legacy, the module and the secret were still there when it was called, and afterwards all four leftovers are gone" \
  $( [ "$gone" -eq 4 ] && [ "$(wc -l < "$r/fc.log")" -eq 1 ] && [ "$(cat "$r/fc.log")" = "called --clean-legacy module-present secret-present" ]; echo $?)
row C2 "the neighbours are still there: jobs.d and its job, /etc/sdcore/other, lib/sd/other-file, run/sdcore/other" \
  $( [ -f "$r/etc/sdcore/jobs.d/nightly" ] && [ -f "$r/etc/sdcore/other" ] && [ -f "$r/usr/local/lib/sd/other-file" ] && [ -f "$r/run/sdcore/other" ]; echo $?)
row C6 "the block runs to its end under the installer's set -euo pipefail and IFS, with no WARNING" $(grep -q BLOCK-ENDED <<<"$out" && ! grep -q WARNING <<<"$out"; echo $?)

# C3
r="$T/c3"; mkroot "$r"; rmdir "$r/etc/sdcore" "$r/usr/local/lib/sd" "$r/run/sdcore"
out=$(run_block "$r")
echo "C3 helper: $(tr '\n' '|' < "$r/fc.log")  said: $(tr '\n' '|' <<<"$out")"
row C3 "a fresh machine: nothing removed or said, the block ends, and the helper is still asked" \
  $( ! grep -q -i 'WARNING\|removed' <<<"$out" && grep -q BLOCK-ENDED <<<"$out" && [ "$(cat "$r/fc.log")" = "called --clean-legacy" ]; echo $?)

# C4
r="$T/c4"; mkroot "$r"; leftovers "$r"
before=$(listing "$r")
out=$(STUB_FC_RC=2 run_block "$r")
after=$(listing "$r")
echo "C4 before: $before"
echo "C4 after:  $after"
echo "C4 said:   $(tr '\n' '|' <<<"$out")"
row C4 "the helper refuses: nothing is removed, a WARNING names --clean-legacy, the block ends" \
  $( [ "$before" = "$after" ] && grep -q "WARNING" <<<"$out" && grep -q -- "--clean-legacy" <<<"$out" && grep -q BLOCK-ENDED <<<"$out"; echo $?)

# C5
r="$T/c5"; mkroot "$r"; leftovers "$r"
out=$(run_block "$r")
echo "C5 after: $(listing "$r")"
row C5 "the leftovers alone in their directories: /usr/local/lib/sd and /run/sdcore are gone with them, /etc/sdcore stays (its jobs.d is SD's)" \
  $( [ ! -e "$r/usr/local/lib/sd" ] && [ ! -e "$r/run/sdcore" ] && [ -d "$r/etc/sdcore" ]; echo $?)

# T1
n_inst=$(grep -n '^if sudo /usr/local/sbin/ssh-forcecommand --install; then$' "$INST" | head -1 | cut -d: -f1)
n_b=$(grep -n '^# LEGACY-CLEAN-BEGIN$' "$INST" | cut -d: -f1)
n_next=$(grep -n '^# Remote-access prompts (owner, 10 Sep 2026, approach B) - enable ssh if asked' "$INST" | head -1 | cut -d: -f1)
echo "T1 lines: boundary install $n_inst, block $n_b, remote-access prompts $n_next"
row T1 "the block is in the installer once, after the ssh boundary is applied and before the remote-access prompts" \
  $( [ -n "$n_inst" ] && [ -n "$n_b" ] && [ -n "$n_next" ] && [ "$n_inst" -lt "$n_b" ] && [ "$n_b" -lt "$n_next" ] && [ "$(grep -c '^# LEGACY-CLEAN-BEGIN$' "$INST")" = 1 ]; echo $?)

# T2
hits=$(grep -v '^ *#' "$INST" | grep -E 'make pam_sdtotp|libpam0g-dev|totp-begin|totp-confirm|enrol_sdsys|sd-totp|install .*pam_sdtotp' || true)
echo "T2 hits: ${hits:-none}"
row T2 "nothing builds or installs the PAM module, asks the authenticator question or enrols a code; libpam0g-dev is off the package list" $( [ -z "$hits" ]; echo $?)

echo "test-install-legacyclean: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -ge 8 ]
