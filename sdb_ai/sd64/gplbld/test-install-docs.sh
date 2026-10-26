#!/bin/bash
#
# test-install-docs.sh - the installer's question about a PDF reader and its block that sets up the shared account's documentation (S.75, plan
# .claude/plan-fullscreen-toolkit.md sections 14.5 to 14.7: the file context.help, the pdf directory, the reader the person said yes to).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-docs.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-docs.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-docs.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd (bin/sd is a stub).  Everything happens in a scratch directory.  Exit 0 every row passed,
# 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing block, or a stub that was never called).
#
# WHAT IT RUNS.  The text between "# VIEWER-ASK-BEGIN" and "# VIEWER-ASK-END", and between "# SHARED-CONTENT-BEGIN" and "# SHARED-CONTENT-END", is cut out of the installer; the
# directories /usr/bin /usr/local/bin /bin and /usr/local/sdsys and /home/sd are rewritten to the scratch directory; each runs under the installer's OWN "set -euo pipefail" AND ITS IFS
# (the first real install of a function that used a for list failed under that IFS and not under set alone, 19 Oct 2026), with sudo replaced by a function that logs the call and
# bin/sd a stub that does what the real set.viewer and load.help do on success - and that, like the real sd, EXITS 0 when it refuses.
#
#   Q  the question: y, Y, yes, YES, Yes allow; Enter, n, N, no and anything else do not (DEFAULT NO); it is asked exactly once, naming the reader and (y/N); it is NOT asked
#      when the list already has a pdf line (an upgrade keeps what the administrator chose) or when no known reader is installed; the first reader of the list is the one offered.
#   C  the content: with the shared account registered, the pdf directory is made, owned sdsys:sdusers, mode 755; load.help is run once with input from /dev/null and cannot stop
#      the install, and its result is judged on the file context.help; set.viewer runs only after a y, with input from /dev/null, and the success line is printed only when the
#      list holds a pdf line afterwards (sd exits 0 when it refuses); with no shared account none of it runs.
#   S  static: the question comes after the API question (the gates question it used to follow was dropped on 26 Oct 26) and before the colour reset; the content block comes after the shared account is made and before the VOC walk.
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
  echo "  [ok] the real installer passes"
  mutant ask-default-yes            '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/^allow_viewer=n$/allow_viewer=y/'
  mutant ask-when-already-allowed   '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/^if ! grep -qs .*; then$/if true; then/'
  mutant ask-accepts-anything       '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/\[yY\]|\[yY\]\[eE\]\[sS\] )/* )/'
  mutant ask-only-lower-y           '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/\[yY\]|\[yY\]\[eE\]\[sS\] )/y )/'
  mutant ask-never-reads            '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/^    read -r -p .*$/    yn_viewer=n/'
  mutant ask-without-a-reader       '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/^if \[ -n "\$allow_viewer_name" \]; then$/if true; then/'
  mutant ask-last-reader-wins       '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/ \&\& \[ -z "\$allow_viewer_name" \]//'
  mutant ask-allows-itself          '/^# VIEWER-ASK-BEGIN/,/^# VIEWER-ASK-END/ s/^allow_viewer=n$/allow_viewer=n; sudo bin\/sd -internal set.viewer add pdf evince/'
  mutant pdf-dir-group-writable     '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/chmod 755 /chmod 775 /'
  mutant pdf-dir-wrong-owner        '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/chown sdsys:sdusers /chown root:root /'
  mutant pdf-dir-not-made           '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/{/sudo mkdir -p/d}'
  mutant help-keeps-stdin           '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/load.help < \/dev\/null || true/load.help || true/'
  mutant help-failure-aborts        '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/load.help < \/dev\/null || true/load.help < \/dev\/null/'
  mutant help-never-run             '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/{/sudo bin\/sd -internal load.help/d}'
  mutant help-never-judged          '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/^    if sudo test -e "\${shared_dir}\/context.help"; then$/    if true; then/'
  mutant viewer-without-a-yes       '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/^    if \[ "\$allow_viewer" = y \] \&\& \[ -n "\$allow_viewer_name" \]; then$/    if [ -n "$allow_viewer_name" ]; then/'
  mutant viewer-keeps-stdin         '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/set.viewer add pdf "\$allow_viewer_name" < \/dev\/null || true/set.viewer add pdf "$allow_viewer_name" || true/'
  mutant viewer-failure-aborts      '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/set.viewer add pdf "\$allow_viewer_name" < \/dev\/null || true/set.viewer add pdf "$allow_viewer_name" < \/dev\/null/'
  mutant viewer-success-unjudged    '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/^        if sudo grep -qs .*; then$/        if true; then/'
  mutant content-without-shared     '/^# SHARED-CONTENT-BEGIN/,/^# SHARED-CONTENT-END/ s/^if sudo test -f "\$shared_reg" \&\& sudo test -d "\$shared_dir"; then$/if true; then/'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

# THE INSTALLER'S OWN set AND IFS (see above).
OPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2)
ASK=$(awk '/^# VIEWER-ASK-BEGIN/{f=1;next} /^# VIEWER-ASK-END/{f=0} f{print}' "$INST")
CONT=$(awk '/^# SHARED-CONTENT-BEGIN/{f=1;next} /^# SHARED-CONTENT-END/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-docs: CANNOT RUN - no set line in the installer"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^IFS=' || { echo "test-install-docs: CANNOT RUN - no IFS line in the installer (the blocks must be run under it)"; exit 2; }
printf '%s\n' "$OPTS" | grep -q '^set -' || { echo "test-install-docs: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$ASK" ]  && { echo "test-install-docs: CANNOT RUN - no block between VIEWER-ASK-BEGIN and VIEWER-ASK-END (nothing to check)"; exit 2; }
[ -z "$CONT" ] && { echo "test-install-docs: CANNOT RUN - no block between SHARED-CONTENT-BEGIN and SHARED-CONTENT-END (nothing to check)"; exit 2; }
echo "blocks    : question $(printf '%s\n' "$ASK" | wc -l) lines;  content $(printf '%s\n' "$CONT" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
ASK_T=$(printf '%s\n' "$ASK" | sed -e "s#/usr/local/bin#$T/b2#g" -e "s#/usr/bin#$T/b1#g" -e "s#/bin#$T/b3#g")
printf '%s\n' "$ASK_T" | grep -q -F "$T/b1" || { echo "test-install-docs: CANNOT RUN - the question block does not look in /usr/bin"; exit 2; }

pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
ok() { [ "$1" = yes ] && echo 0 || echo 1; }

# ---- Q. the question ----------------------------------------------------------------------------------------------------
run_ask() {   # run_ask ANSWER [readers...]   - prints the output, then ALLOW=y|n NAME=...
  local ans="$1"; shift
  rm -rf "$T/b1" "$T/b2" "$T/b3" "$T/sdsys"; mkdir -p "$T/b1" "$T/b2" "$T/b3" "$T/sdsys"
  local r; for r in "$@"; do case "$r" in alreadyallowed) printf 'pdf /usr/bin/evince\n' > "$T/sdsys/viewers";; *:*) : > "$T/${r%%:*}/${r##*:}"; chmod +x "$T/${r%%:*}/${r##*:}";; esac; done
  : > "$T/read.log"
  OPTS="$OPTS" ASK_T="$ASK_T" T="$T" bash -c '
      eval "$OPTS"
      sdsysdir="$T/sdsys"
      read() { ( IFS=" "; printf "%s\n" "$*" ) >> "$T/read.log"; builtin read "$@"; }
      eval "$ASK_T"
      echo "ALLOW=$allow_viewer NAME=$allow_viewer_name"' <<< "$ans" 2>&1
}

echo "--- Q: the question"
for ans in y Y yes YES Yes; do
  OUT=$(run_ask "$ans" b2:evince)
  row "Q1 the answer '$ans' allows (allow_viewer=y, the reader is evince)" "$(ok "$(printf '%s' "$OUT" | grep -q '^ALLOW=y NAME=evince$' && echo yes)")" "$OUT"
done
for ans in "" n N no NO x yy ye nope 1; do
  OUT=$(run_ask "$ans" b2:evince)
  row "Q2 the answer '$ans' does NOT allow (default No)" "$(ok "$(printf '%s' "$OUT" | grep -q '^ALLOW=n NAME=evince$' && echo yes)")" "$OUT"
done
OUT=$(run_ask y b2:evince)
nread=$(wc -l < "$T/read.log")
row "Q3 it was asked: read ran once (the null case: a block that never asks passes every Q2 row)" "$(ok "$([ "$nread" -eq 1 ] && echo yes)")" "read calls: $nread"
row "Q3b ...with the prompt naming the reader and (y/N)" "$(ok "$(grep -q -F "evince" "$T/read.log" && grep -q -F "(y/N)" "$T/read.log" && grep -q -- '-r' "$T/read.log" && echo yes)")" "read.log: $(cat "$T/read.log")"
row "Q3c ...after saying that nothing is allowed as delivered" "$(ok "$(printf '%s' "$OUT" | grep -q 'nothing is allowed as delivered' && echo yes)")" "$OUT"
OUT=$(run_ask y b2:evince alreadyallowed)
nread=$(wc -l < "$T/read.log")
row "Q4 the list already has a pdf line (an upgrade): not asked, a typed y changes nothing" "$(ok "$([ "$nread" -eq 0 ] && printf '%s' "$OUT" | grep -q '^ALLOW=n NAME=$' && echo yes)")" "read calls: $nread; $OUT"
OUT=$(run_ask y)
nread=$(wc -l < "$T/read.log")
row "Q5 no known reader installed: not asked" "$(ok "$([ "$nread" -eq 0 ] && printf '%s' "$OUT" | grep -q '^ALLOW=n NAME=$' && echo yes)")" "read calls: $nread; $OUT"
OUT=$(run_ask y b1:okular b2:evince b3:zathura)
row "Q6 the FIRST reader of the list is offered whichever directory has it (evince before okular and zathura)" "$(ok "$(printf '%s' "$OUT" | grep -q '^ALLOW=y NAME=evince$' && echo yes)")" "$OUT"
OUT=$(run_ask y b1:xdg-open b3:gimp)
row "Q7 a program that is not in the list of readers is never offered (xdg-open, gimp)" "$(ok "$(printf '%s' "$OUT" | grep -q '^ALLOW=n NAME=$' && echo yes)")" "$OUT"

# ---- C. the content ---------------------------------------------------------------------------------------------------
cat > "$T/sd-stub" <<'STUB'
#!/bin/bash
# bin/sd as the installer calls it: -internal load.help, or -internal set.viewer add pdf <name>.  Exits 0 when it refuses, like the real sd.
echo "ARGS: $*" >> "$SDLOG"
if [ -t 0 ]; then echo "STDIN: tty" >> "$SDLOG"; else echo "STDIN: $(readlink /proc/$$/fd/0)" >> "$SDLOG"; fi
case "$2" in
  load.help)
    [ -n "${CRASH_HELP:-}" ] && exit 1
    [ -n "${NOHELP:-}" ] && exit 0
    mkdir -p "$SHARED/context.help"; exit 0;;
  set.viewer)
    [ -n "${CRASH_VIEWER:-}" ] && exit 1
    [ -n "${REFUSE_VIEWER:-}" ] && exit 0
    printf 'pdf /usr/bin/%s\n' "$5" >> "$SDSYS/viewers"; exit 0;;
esac
exit 0
STUB
chmod +x "$T/sd-stub"
CONT_T=$(printf '%s\n' "$CONT" | sed -e "s#/usr/local/sdsys#$T/sdsys#g" -e "s#/home/sd/#$T/home/sd/#g")

run_cont() {   # env knobs: ALLOW(y/n) NAME CRASH_HELP NOHELP CRASH_VIEWER REFUSE_VIEWER NOSHARED ; prints the output, then RC=0
  rm -rf "$T/work" "$T/sdsys" "$T/home"; mkdir -p "$T/work/bin" "$T/sdsys" "$T/home/sd/group_accounts"
  cp "$T/sd-stub" "$T/work/bin/sd"
  : > "$T/sd.log"; : > "$T/sudo.log"
  if [ -z "${NOSHARED:-}" ]; then mkdir -p "$T/home/sd/group_accounts/shared"; : > "$T/sdsys/accounts-shared"; fi
  ( cd "$T/work" && OPTS="$OPTS" CONT_T="$CONT_T" T="$T" SDLOG="$T/sd.log" SDSYS="$T/sdsys" SHARED="$T/home/sd/group_accounts/shared" bash -c '
      eval "$OPTS"; RED=; NC=
      sdsysdir="$T/sdsys"
      shared_reg="$T/sdsys/accounts-shared"
      shared_dir="$T/home/sd/group_accounts/shared"
      allow_viewer="${ALLOW:-n}"; allow_viewer_name="${NAME-evince}"
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
row "C2 load.help was RUN once (the null case: a stub never called passes nothing), as -internal load.help, with its input from /dev/null" \
    "$(ok "$([ "$(grep -c '^ARGS: -internal load.help$' "$T/sd.log")" -eq 1 ] && grep -q '^STDIN: /dev/null$' "$T/sd.log" && echo yes)")" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
row "C3 ...the file was made, so the install says it is loaded and prints no WARNING" "$(ok "$(printf '%s' "$OUT" | grep -q 'Context help is loaded' && ! printf '%s' "$OUT" | grep -q WARNING && echo yes)")" "$OUT"
row "C4 ...no reader was asked for (allow_viewer=n): set.viewer was NOT run" "$(ok "$(! grep -q 'set.viewer' "$T/sd.log" && echo yes)")" "sd.log: $(tr '\n' ';' < "$T/sd.log")"

OUT=$(NOHELP=1 run_cont)
row "C5 load.help exits 0 and makes nothing: RC=0, a WARNING says the [?] buttons have no text and names load.help, no 'is loaded' line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING' && printf '%s' "$OUT" | grep -q 'run:  load.help' && ! printf '%s' "$OUT" | grep -q 'Context help is loaded' && echo yes)")" "$OUT"
OUT=$(CRASH_HELP=1 run_cont)
row "C6 load.help CRASHES (exit 1): the install goes on (RC=0) and says so" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING' && echo yes)")" "$OUT"

OUT=$(ALLOW=y NAME=evince run_cont)
row "C7 a y: set.viewer add pdf evince was run once, with its input from /dev/null" \
    "$(ok "$([ "$(grep -c '^ARGS: -internal set.viewer add pdf evince$' "$T/sd.log")" -eq 1 ] && [ "$(grep -c '^STDIN: /dev/null$' "$T/sd.log")" -eq 2 ] && echo yes)")" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
row "C7b ...and the list now holds the line, so the install says the reader is allowed and where the PDFs go (docs.install)" \
    "$(ok "$(grep -q '^pdf /usr/bin/evince$' "$T/sdsys/viewers" && printf '%s' "$OUT" | grep -q 'Allowed evince to show the documentation' && printf '%s' "$OUT" | grep -q 'docs.install' && ! printf '%s' "$OUT" | grep -q WARNING && echo yes)")" "$OUT"
OUT=$(ALLOW=y NAME=evince REFUSE_VIEWER=1 run_cont)
row "C8 set.viewer exits 0 and refuses (the program failed the test): RC=0, a WARNING with the command to give by hand, NO 'Allowed' line" \
    "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'WARNING: evince was not allowed' && printf '%s' "$OUT" | grep -q 'set.viewer add pdf evince' && ! printf '%s' "$OUT" | grep -q 'Allowed evince' && echo yes)")" "$OUT"
OUT=$(ALLOW=y NAME=evince CRASH_VIEWER=1 run_cont)
row "C9 set.viewer CRASHES: the install goes on (RC=0) and says it was not allowed" "$(ok "$(printf '%s' "$OUT" | grep -q '^RC=0$' && printf '%s' "$OUT" | grep -q 'was not allowed' && echo yes)")" "$OUT"
OUT=$(ALLOW=n NAME=evince run_cont)
row "C10 a name but no y: set.viewer is not run (the answer, not the name, allows)" "$(ok "$(! grep -q 'set.viewer' "$T/sd.log" && echo yes)")" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
OUT=$(ALLOW=y NAME= run_cont)
row "C11 a y but no reader name: set.viewer is not run" "$(ok "$(! grep -q 'set.viewer' "$T/sd.log" && echo yes)")" "sd.log: $(tr '\n' ';' < "$T/sd.log")"
OUT=$(NOSHARED=1 ALLOW=y run_cont)
row "C12 no shared account: nothing is run or made (no sd call, no pdf directory, no sudo), the install says why, RC=0" \
    "$(ok "$([ "$(sdcalls)" -eq 0 ] && [ ! -d "$T/home/sd/group_accounts/shared/pdf" ] && ! grep -q -E '^(mkdir|chown|chmod)' "$T/sudo.log" && printf '%s' "$OUT" | grep -q 'The shared account is not there' && printf '%s' "$OUT" | grep -q '^RC=0$' && echo yes)")" "calls $(sdcalls); $OUT"

# ---- S. static --------------------------------------------------------------------------------------------------------
echo "--- S: the places"
ln_gates=$(grep -n '^read -r -p "Allow API access from other computers?' "$INST" | head -1 | cut -d: -f1)       # 26 Oct 26: the gates question is gone; the reader question follows the API question
ln_ask=$(grep -n '^# VIEWER-ASK-BEGIN' "$INST" | head -1 | cut -d: -f1)
ln_askend=$(grep -n '^# VIEWER-ASK-END' "$INST" | head -1 | cut -d: -f1)
ln_nc=$(awk -v s="$ln_askend" 'NR>s && /^printf "%b\\n" "\$NC"$/ {print NR; exit}' "$INST")
ln_cr=$(grep -n '^# SHARED-CREATE-END' "$INST" | head -1 | cut -d: -f1)
ln_ct=$(grep -n '^# SHARED-CONTENT-BEGIN' "$INST" | head -1 | cut -d: -f1)
ln_walk=$(grep -n "AN UPGRADE BRINGS EVERY ACCOUNT'S VOC FORWARD" "$INST" | head -1 | cut -d: -f1)
row "S1 the reader question comes after the API question and before the colour reset that ends the questions" "$(ok "$([ "${ln_gates:-0}" -gt 0 ] && [ "$ln_gates" -lt "${ln_ask:-0}" ] && [ "${ln_ask:-0}" -lt "${ln_nc:-0}" ] && echo yes)")" "API question $ln_gates, ask $ln_ask, reset ${ln_nc:-none}"
row "S2 the content block comes after the shared account is made and before the walk that brings every account's VOC forward" "$(ok "$([ "${ln_cr:-0}" -gt 0 ] && [ "$ln_cr" -lt "${ln_ct:-0}" ] && [ "${ln_ct:-0}" -lt "${ln_walk:-0}" ] && echo yes)")" "create-end $ln_cr, content $ln_ct, walk ${ln_walk:-none}"

echo
echo "test-install-docs: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
