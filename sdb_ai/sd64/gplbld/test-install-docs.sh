#!/bin/bash
#
# test-install-docs.sh - the installer's block that sets up the shared account's documentation (S.75, plan .claude/plan-fullscreen-toolkit.md sections 14.5
# to 14.7: the file context.help and the pdf directory), and since S.187 its removal of the old list of PDF readers.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-docs.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-docs.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-docs.sh      (what --selftest uses)
#
# START-HISTORY:
# 9 Nov 26 dm  S.187 (owner, 9 Nov 2026, told the pdf verb only works at the machine's own display: "remove"): the reader questions (VIEWER-ASK),
#              the reader install (READER-INSTALL) and the set.viewer step are gone from the installer, and their rows and mutants from here.  New:
#              the content block removes the system directory's file viewers on an upgrade (rows V), and nothing in the installer names the
#              removed verbs or blocks (row S0).
# END-HISTORY
#
# FREE CHECK: no sudo (it is a function here), no install, no sd (bin/sd is a stub).  Everything happens in a scratch directory.  Exit 0 every row passed,
# 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing block, or a stub that was never called).
#
# WHAT IT RUNS.  The text between "# SHARED-CONTENT-BEGIN" and "# SHARED-CONTENT-END" is cut out of the installer; /usr/local/sdsys and /home/sd are rewritten
# to the scratch directory; it runs under the installer's OWN "set -euo pipefail" AND ITS IFS (the first real install of a function that used a for list failed
# under that IFS and not under set alone, 19 Oct 2026), with sudo replaced by a function that logs the call and bin/sd a stub that does what the real load.help
# does on success - and that, like the real sd, EXITS 0 when it refuses.
#
#   C  the content: with the shared account registered, the pdf directory is made, owned sdsys:sdusers, mode 755; load.help is run once with input from /dev/null
#      and cannot stop the install, and its result is judged on the file context.help; with no shared account none of it runs.
#   V  the old list of readers (viewers in the system directory) is removed whether or not the shared account is there, and its absence is no error.
#   S  static: nothing in the installer names the pdf verb's pieces any more; the content block comes after the shared account is made and before the VOC walk.
#
# NOT MEASURED HERE, and said so: that the real load.help, run by `sudo bin/sd -internal` while the install's own cproc is in place, enters the shared account and fills the file
# (sandbox-docs.py runs it on a private SD; a real install witnesses the rest); that chown sdsys:sdusers works on the real machine.

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
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  mutant pdf-dir-group-writable     '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/chmod 755 /chmod 775 /'
  mutant pdf-dir-wrong-owner        '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/chown sdsys:sdusers /chown root:root /'
  mutant pdf-dir-not-made           '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/{/sudo mkdir -p/d}'
  mutant help-keeps-stdin           '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/load.help < \/dev\/null || true/load.help || true/'
  mutant help-failure-aborts        '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/load.help < \/dev\/null || true/load.help < \/dev\/null/'
  mutant help-never-run             '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/{/sudo bin\/sd -internal load.help/d}'
  mutant help-never-judged          '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/^    if sudo test -e "\${shared_dir}\/context.help"; then$/    if true; then/'
  mutant content-without-shared     '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/^if sudo test -f "\$shared_reg" \&\& sudo test -d "\$shared_dir"; then$/if true; then/'
  mutant viewers-kept               '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/{/sudo rm -f "\${sdsysdir}\/viewers"/d}'
  mutant viewers-rm-fails-on-absent '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/sudo rm -f "\${sdsysdir}\/viewers"/sudo rm "${sdsysdir}\/viewers"/'
  mutant viewer-question-back       's/^# SDSYS-SSH-ASK-END$/# SDSYS-SSH-ASK-END\n# VIEWER-ASK-BEGIN\n# VIEWER-ASK-END/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

# THE INSTALLER'S OWN set AND IFS (see above).
OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
CONT=$(awk '/^# SHARED-CONTENT-BEGIN/{f=1;next} /^# SHARED-CONTENT-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-docs: CANNOT RUN - no set line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-docs: CANNOT RUN - no IFS line in the installer (the block must be run under it)"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-docs: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$CONT" ] && { echo "test-install-docs: CANNOT RUN - no block between SHARED-CONTENT-BEGIN and SHARED-CONTENT-END (nothing to check)"; exit 2; }
echo "block     : content $(printf '%s\n' "$CONT" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# ---- C. the content ---------------------------------------------------------------------------------------------------
cat > "$T/sd-stub" <<'STUB'
#!/bin/bash
# bin/sd as the installer calls it: -internal load.help.  Exits 0 when it refuses, like the real sd.
echo "ARGS: $*" >> "$SDLOG"
if [ -t 0 ]; then echo "STDIN: tty" >> "$SDLOG"; else echo "STDIN: $(readlink /proc/$$/fd/0)" >> "$SDLOG"; fi
case "$2" in
  load.help)
    [ -n "${CRASH_HELP:-}" ] && exit 1
    [ -n "${NOHELP:-}" ] && exit 0
    mkdir -p "$SHARED/context.help"; exit 0;;
esac
exit 0
STUB
chmod +x "$T/sd-stub"
CONT_T=$(printf '%s\n' "$CONT" | sed -e "s#/usr/local/sdsys#$T/sdsys#g" -e "s#/home/sd/#$T/home/sd/#g")

run_cont() {   # env knobs: CRASH_HELP NOHELP NOSHARED VIEWERS(1: the old list is there) ; prints the output, then RC=0
  rm -rf "$T/work" "$T/sdsys" "$T/home"; mkdir -p "$T/work/bin" "$T/sdsys" "$T/home/sd/group_accounts"
  cp "$T/sd-stub" "$T/work/bin/sd"
  : > "$T/sd.log"; : > "$T/sudo.log"
  if [ -z "${NOSHARED:-}" ]; then mkdir -p "$T/home/sd/group_accounts/shared"; : > "$T/sdsys/accounts-shared"; fi
  if [ -n "${VIEWERS:-}" ]; then printf 'pdf /usr/bin/evince\n' > "$T/sdsys/viewers"; fi
  ( cd "$T/work" && OPTS="$OPTS" CONT_T="$CONT_T" T="$T" SDLOG="$T/sd.log" SDSYS="$T/sdsys" SHARED="$T/home/sd/group_accounts/shared" bash -c '
      eval "$OPTS"; RED=; NC=
      sdsysdir="$T/sdsys"
      shared_reg="$T/sdsys/accounts-shared"
      shared_dir="$T/home/sd/group_accounts/shared"
      sudo() { ( IFS=" "; printf "%s\n" "$*" ) >> "$T/sudo.log"; case "$1" in chown) return 0;; esac; "$@"; }
      eval "$CONT_T"
      echo "RC=0"' <<< "input the block must not read" 2>&1 )
}
sdcalls() { grep -c '^ARGS: ' "$T/sd.log"; }

echo "--- C: the content"
OUT=$(run_cont)
row "C1 the shared account is there: RC=0, the pdf directory exists (mkdir -p, chown sdsys:sdusers, chmod 755 were run, in that order)" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && [ -d "$T/home/sd/group_accounts/shared/pdf" ] && [ "$(grep -n -E '^(mkdir -p|chown|chmod)' "$T/sudo.log" | cut -d: -f2 | cut -d' ' -f1 | tr '\n' ' ')" = "mkdir chown chmod " ] && echo yes)")" "sudo.log: $(tr '\n' ';' < "$T/sudo.log"); $OUT"
row "C1b ...owner and group sdsys:sdusers, mode 755, on the pdf directory only" \
    "$(ok "$(grep -q -E '^chown sdsys:sdusers .*/shared/pdf$' "$T/sudo.log" && grep -q -E '^chmod 755 .*/shared/pdf$' "$T/sudo.log" && [ "$(grep -c -E '^(chown|chmod)' "$T/sudo.log")" -eq 2 ] && echo yes)")" "sudo.log: $(tr '\n' ';' < "$T/sudo.log")"
row "C2 load.help was RUN once (the null case: a stub never called passes nothing), as -internal load.help, with its input from /dev/null; nothing else was run" \
    "$(ok "$([ "$(grep -c '^ARGS: -internal load.help$' "$T/sd.log")" -eq 1 ] && [ "$(sdcalls)" -eq 1 ] && grep -q '^STDIN: /dev/null$' "$T/sd.log" && echo yes)")" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
row "C3 ...the file was made, so the install says it is loaded and prints no WARNING" "$(ok "$(printf '%s' "$OUT" | grep -q 'Context help is loaded' && ! printf '%s' "$OUT" | grep -q WARNING && echo yes)")" "$OUT"
OUT=$(NOHELP=1 run_cont)
row "C5 load.help exits 0 and makes nothing: RC=0, a WARNING says the [?] buttons have no text and names load.help, no 'is loaded' line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING' && printf '%s' "$OUT" | grep -q 'run:  load.help' && ! printf '%s' "$OUT" | grep -q 'Context help is loaded' && echo yes)")" "$OUT"
OUT=$(CRASH_HELP=1 run_cont)
row "C6 load.help CRASHES (exit 1): the install goes on (RC=0) and says so" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING' && echo yes)")" "$OUT"
OUT=$(NOSHARED=1 run_cont)
row "C12 no shared account: nothing is run or made (no sd call, no pdf directory, no mkdir/chown/chmod), the install says why, RC=0" \
    "$(ok "$([ "$(sdcalls)" -eq 0 ] && [ ! -d "$T/home/sd/group_accounts/shared/pdf" ] && ! grep -q -E '^(mkdir|chown|chmod)' "$T/sudo.log" && printf '%s' "$OUT" | grep -q 'The shared account is not there' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "calls $(sdcalls); $OUT"

echo "--- V: the old list of readers"
OUT=$(VIEWERS=1 run_cont)
row "V1 an upgrade with the old list (viewers in the system directory): it is removed (the null case: the file was there before the block ran), RC=0" \
    "$(ok "$([ ! -e "$T/sdsys/viewers" ] && grep -q "^rm -f $T/sdsys/viewers$" "$T/sudo.log" && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "sudo.log: $(tr '\n' ';' < "$T/sudo.log"); $OUT"
OUT=$(VIEWERS=1 NOSHARED=1 run_cont)
row "V2 ...also when the shared account is not there" "$(ok "$([ ! -e "$T/sdsys/viewers" ] && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"
OUT=$(run_cont)
row "V3 a fresh install, no list: nothing to remove and the install goes on (RC=0)" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "$OUT"

echo "--- S: the places"
gone=$(grep -n -E 'VIEWER-ASK|READER-INSTALL|allow_viewer|install_reader|set\.viewer|pdf lists' "$INST" | grep -v '^[0-9]*:#' | head -3)
row "S0 nothing but comments in the installer names the pdf verb's pieces (the reader questions, set.viewer, 'pdf lists')" "$(ok "$([ -z "$gone" ] && ! grep -q -E '^# VIEWER-ASK-(BEGIN|END)' "$INST" && echo yes)")" "$gone"
ln_cr=$(grep -n '^# SHARED-CREATE-END' "$INST" | head -1 | cut -d: -f1)
ln_ct=$(grep -n '^# SHARED-CONTENT-BEGIN' "$INST" | head -1 | cut -d: -f1)
ln_walk=$(grep -n "AN UPGRADE BRINGS EVERY ACCOUNT'S VOC FORWARD" "$INST" | head -1 | cut -d: -f1)
row "S2 the content block comes after the shared account is made and before the walk that brings every account's VOC forward" "$(ok "$([ "${ln_cr:-0}" -gt 0 ] && [ "$ln_cr" -lt "${ln_ct:-0}" ] && [ "${ln_ct:-0}" -lt "${ln_walk:-0}" ] && echo yes)")" "create-end $ln_cr, content $ln_ct, walk ${ln_walk:-none}"
echo
echo "test-install-docs: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
