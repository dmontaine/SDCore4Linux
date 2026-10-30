#!/bin/bash
#
# test-install-ipcmode.sh - installsdcore.sh gives the file $ipc to its owner and its group only (W.11, Opus's decision of 30 Oct 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-ipcmode.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-ipcmode.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-ipcmode.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a missing block is exit 2, never a pass).
#
# WHY IT EXISTS.  $ipc is a hashed file in the system directory that every SD user's process writes: the command a phantom is told to run, the DATA queues and the user
# messages.  It was mode 775, so every operating-system user on the machine, an SD user or not, could read them.  Nothing outside the group sdusers needs it.  The block between
# IPCMODE-BEGIN and IPCMODE-END is cut out of the installer and run under its own "set" AND "IFS" lines, with sudo a function, on a scratch tree standing for $sdsysdir/$ipc:
#
#   A  a tree that others could read and write is left with NO bit for others, and owner and group keep read and write (execute only where it was a directory or was set)
#   B  every directory has the setgid bit (a subfile an SD user's process makes belongs to sdusers, not to that user's primary group)
#   C  the null case: the tree had bits for others before the block ran, so a block that did nothing could not pass A
#   D  the block comes once, inside the branch that names $ipc, before the owner is set

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, sed expression
    local name="$1" expr="$2" f="$T/$1.sh" rc
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -5 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant back-to-775       's/sudo chmod -R u=rwX,g=rwX,o= "\${sdsysdir}\/\${bootstrap_dir}"/sudo chmod -R 775 "${sdsysdir}\/${bootstrap_dir}"/'
  mutant others-may-read   's/sudo chmod -R u=rwX,g=rwX,o= /sudo chmod -R u=rwX,g=rwX,o=rX /'
  mutant no-setgid         's/-type d -exec chmod g+s {} +/-type d -exec chmod g+x {} +/'
  mutant files-only-setgid 's/-type d -exec chmod g+s {} +/-type f -exec chmod g+s {} +/'
  echo "selftest: $caught of 4 mutants caught, $missed missed"
  [ "$caught" -eq 4 ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST"; grep -m1 -E '^IFS=' "$INST")
case "$OPTS" in *IFS=*) ;; *) echo "test-install-ipcmode: CANNOT RUN - no IFS line in the installer (the block must be run under it)"; exit 2;; esac
BLOCK=$(awk '/# IPCMODE-BEGIN$/{f=1;next} /# IPCMODE-END$/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : $(printf '%s' "$OPTS" | tr '\n' ' ')"
[ -z "$BLOCK" ] && { echo "test-install-ipcmode: CANNOT RUN - no IPCMODE block in the installer (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | grep -v '^ *#' | wc -l) lines of code"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}

# the scratch tree: $ipc is a directory holding the subfiles of a hashed file (two plain files) and, as a dynamic file would, a subdirectory with a file in it
SYS="$T/sdsys"
IPC="$SYS/\$ipc"
mkdir -p "$IPC/sub"
printf 'a' > "$IPC/%0"; printf 'b' > "$IPC/%1"; printf 'c' > "$IPC/sub/%2"
chmod 775 "$IPC" "$IPC/sub"; chmod 775 "$IPC/%0"; chmod 664 "$IPC/%1" "$IPC/sub/%2"
before_others=$(find "$IPC" -perm /007 | wc -l)

body=$(printf '%s\n' "$BLOCK")
out=$(bash -c "$OPTS"$'\n'"sudo() { \"\$@\"; }"$'\n'"sdsysdir='$SYS'"$'\n'"bootstrap_dir='\$ipc'"$'\n'"$body" 2>&1); rc=$?

row "C: the block ran (exit 0, no output) and the tree HAD bits for others before it ($before_others paths), so a block that did nothing could not pass A" \
    $([ "$rc" -eq 0 ] && [ -z "$out" ] && [ "$before_others" -ge 4 ] && echo 0 || echo 1) "rc=$rc out=$out before=$before_others"
others=$(find "$IPC" -perm /007 | wc -l)
row "A: no path of the tree has a bit for others" $([ "$others" -eq 0 ] && echo 0 || echo 1) "$others path(s) still carry one: $(find "$IPC" -perm /007 | tr '\n' ' ')"
lost=$(find "$IPC" \( -type f -o -type d \) ! -perm -060 | wc -l)
row "A: ...and owner and group keep read and write on every file and directory" $([ "$lost" -eq 0 ] && echo 0 || echo 1) "$lost path(s) lost a bit"
nodirx=$(find "$IPC" -type d ! -perm -070 | wc -l)
row "A: ...every directory still has execute for owner and group (it can be entered)" $([ "$nodirx" -eq 0 ] && echo 0 || echo 1) "$nodirx"
nosg=$(find "$IPC" -type d ! -perm -2000 | wc -l)
row "B: every directory has the setgid bit" $([ "$nosg" -eq 0 ] && echo 0 || echo 1) "$nosg director(ies) without it"
newx=$(find "$IPC" -type f -perm /111 | wc -l)
row "A: ...and a plain file that had execute for nobody but 'other' got none (only %0, which was 775, may keep its owner/group execute): at most 1 executable file" \
    $([ "$newx" -le 1 ] && echo 0 || echo 1) "$newx executable files"

# D: text
lb=$(grep -n '# IPCMODE-BEGIN$' "$INST" | head -1 | cut -d: -f1)
le=$(grep -n '# IPCMODE-END$' "$INST" | head -1 | cut -d: -f1)
li=$(grep -n "if \[ \"\${bootstrap_dir}\" = '\\\$ipc' \]; then" "$INST" | head -1 | cut -d: -f1)
lo=$(awk -v s="${le:-0}" 'NR>s && /chown -R sdsys:sdusers/{print NR; exit}' "$INST")
row "D: one block, inside the branch that names \$ipc, before the owner is set (lines: if ${li:-?}, begin ${lb:-?}, end ${le:-?}, chown ${lo:-?})" \
    $([ "$(grep -c '# IPCMODE-BEGIN$' "$INST")" = 1 ] && [ -n "$li" ] && [ -n "$lb" ] && [ -n "$le" ] && [ -n "$lo" ] && [ "$li" -lt "$lb" ] && [ "$lb" -lt "$le" ] && [ "$le" -lt "$lo" ] && echo 0 || echo 1) "see the lines"

echo "test-install-ipcmode: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
