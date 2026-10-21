#!/bin/bash
#
# test-install-agentpack.sh - installsdcore.sh's block that puts the AI guide and knowledge pack in /usr/local/sdsys/agent-pack
#                             (S.69 rows 1 and 1b), run the way the installer runs it.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-agentpack.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-agentpack.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-agentpack.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (it is a function here), no install, no sd.  Everything happens in a scratch directory.  Exit 0 every row passed,
# 1 a row failed, 2 it could not run (a refusal to pass on nothing: a missing block or an anchor that is not in the installer).
#
# WHY IT EXISTS.  test-install-pass3.sh says why a block must be tested under the installer's own "set -euo pipefail": a harness
# that evaluated one without those options passed a block that stopped two real installs.  This block is a pipeline-and-test
# block of exactly that kind (a sed that finds no stamp, a file that is not there), and it must NEVER stop an install: the pack is
# documents, an older tag has none, and a documents-only feature does not get to fail an install.
#
# WHAT IT RUNS.  The text between "# AGENTPACK-BEGIN" and "# AGENTPACK-END" (the copy) and between "# AGENTPACK-MODE-BEGIN" and
# "# AGENTPACK-MODE-END" (the file mode, which runs AFTER the installer's "chmod -R 755"), cut out verbatim and evaluated under the
# options read from the installer's own "set" line, with sudo a function that logs what it was asked and runs it as the caller.  The
# "clone" is a scratch copy of this tree's real agent-pack/; sdsysdir is a scratch directory holding the real gpl.bp/revstamp.h.
#
#   A1  the real pack installs: the success line names the version, guide and every pack file are there and byte-equal to the clone's,
#       and the stub WAS called (the null case)
#   A2  nothing else is copied: no skill, templates, recipe, generator or notes
#   A3  no agent-pack in the clone / the guide but no manifest / no core.md: a note, no copy, rc 0, and the block reached its end
#   A4  the manifest's rev_stamp is not the installed revstamp.h's: not installed, the note names both, rc 0
#   A5  no revstamp.h at all: not installed, rc 0 (the case that would stop an install under pipefail)
#   A6  the mode block: files 644, directories 755, nothing writable by group or other; with no agent-pack it does nothing
#   A7  the order in the installer (text): the copy comes after "cp -R sdsys /usr/local" and the microcfg copy and before the first
#       "chown -R sdsys:sdusers"; the mode block comes after the last "chmod -R 755"
#   A8  the block has no exit in it
#
# NOT MEASURED HERE, and said so: that a real install leaves it sdsys:sdusers and unwritable by an SD user (gplbld/verify-sysperms.py
# derives its read-only set, so agent-pack is covered the day it exists), and that deletesdcore.sh removes it (it ends with rm -fr
# of the whole tree).  gplbld/witness-agentpack.sh does both on a real install; it has not been run.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
SD64="$(cd "$HERE/.." && pwd)"
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
  mutant copy-removed            's#^        sudo cp -R agent-pack/guide agent-pack/pack "\$sdsysdir/agent-pack/"$#        true#'
  mutant mkdir-removed           's#^        sudo mkdir -p "\$sdsysdir/agent-pack"$#        true#'
  mutant skill-copied-too        's#sudo cp -R agent-pack/guide agent-pack/pack "#sudo cp -R agent-pack/guide agent-pack/pack agent-pack/skill "#'
  mutant generator-copied-too    's#sudo cp -R agent-pack/guide agent-pack/pack "#sudo cp -R agent-pack/guide agent-pack/pack agent-pack/mkpack.py "#'
  mutant stamp-test-inverted     's#\[ "\$pack_stamp" = "\$tree_stamp" \]#[ "$pack_stamp" != "$tree_stamp" ]#'
  mutant stamp-test-removed      's#\[ -n "\$pack_stamp" \] \&\& \[ "\$pack_stamp" = "\$tree_stamp" \]#true#'
  mutant hard-stop-when-absent   's#^    echo "Note: the download holds no complete AI guide and knowledge pack (agent-pack/), so none was installed."$#    exit 1#'
  mutant hard-stop-on-mismatch   's#^        echo "Note: the AI knowledge pack in the download is for version .*#        exit 1#'
  mutant completeness-dropped    's# \&\& \[ -f agent-pack/pack/core.md \]##'
  mutant manifest-test-dropped   's# \&\& \[ -f agent-pack/pack/manifest.json \]##'
  mutant unguarded-revstamp-read 's#2>/dev/null) || tree_stamp=""#2>/dev/null)#'
  mutant unguarded-manifest-read 's#agent-pack/pack/manifest.json) || pack_stamp=""#agent-pack/pack/manifest.json)#'
  mutant block-after-the-chown   '/^# AGENTPACK-BEGIN$/i sudo chown -R sdsys:sdusers "$sdsysdir"'
  mutant mode-block-too-early    '/^# AGENTPACK-MODE-END$/a sudo chmod -R 755 "$sdsysdir"'
  mutant files-group-writable    's#-exec chmod 644 {} +#-exec chmod 664 {} +#'
  mutant mode-block-removed      's#^    sudo find "\$sdsysdir/agent-pack" -type f -exec chmod 644 {} +$#    true#'
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$caught" -eq "$total" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
BLK=$(awk '/^# AGENTPACK-BEGIN$/{f=1;next} /^# AGENTPACK-END$/{f=0} f{print}' "$INST")
MODE=$(awk '/^# AGENTPACK-MODE-BEGIN$/{f=1;next} /^# AGENTPACK-MODE-END$/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
echo "tree      : $SD64"
[ -z "$OPTS" ] && { echo "test-install-agentpack: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLK" ]  && { echo "test-install-agentpack: CANNOT RUN - no block between AGENTPACK-BEGIN and AGENTPACK-END (nothing to check)"; exit 2; }
[ -z "$MODE" ] && { echo "test-install-agentpack: CANNOT RUN - no block between AGENTPACK-MODE-BEGIN and AGENTPACK-MODE-END (nothing to check)"; exit 2; }
[ -d "$SD64/agent-pack/pack" ] && [ -f "$SD64/agent-pack/guide/sd-basic-guide.md" ] || { echo "test-install-agentpack: CANNOT RUN - this tree has no agent-pack/guide and agent-pack/pack to install"; exit 2; }
[ -f "$SD64/sdsys/gpl.bp/revstamp.h" ] || { echo "test-install-agentpack: CANNOT RUN - no sdsys/gpl.bp/revstamp.h"; exit 2; }
echo "block     : $(printf '%s\n' "$BLK" | wc -l) lines;  mode block: $(printf '%s\n' "$MODE" | wc -l) lines"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export BLK MODE OPTS T
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}

setup() {   # a fresh installed tree (just the stamp) and a fresh clone of this tree's agent-pack
  rm -rf "$T/sdsys" "$T/work"; mkdir -p "$T/sdsys/gpl.bp" "$T/work"
  cp "$SD64/sdsys/gpl.bp/revstamp.h" "$T/sdsys/gpl.bp/revstamp.h"
  cp -R "$SD64/agent-pack" "$T/work/agent-pack"
  : > "$T/sudo.log"
}
run() {   # run BLOCK-VARIABLE-NAME: prints what the block printed, then REACHED-END and RC
  SUDO_LOG="$T/sudo.log" SDSYSDIR="$T/sdsys" WHICH="$1" bash -c '
      eval "$OPTS"
      sdsysdir="$SDSYSDIR"; RED=; NC=
      sudo() { printf "%s\n" "$*" >> "$SUDO_LOG"; "$@"; }
      cd "$T/work"
      eval "${!WHICH}"
      echo "REACHED-END"' 2>&1
}
DEST="$T/sdsys/agent-pack"
GOOD=$(sed -n '/"rev_stamp"/{s/^[^:]*: *"\([^"]*\)".*/\1/p;q}' "$SD64/agent-pack/pack/manifest.json")
[ -n "$GOOD" ] || { echo "test-install-agentpack: CANNOT RUN - the real manifest holds no rev_stamp"; exit 2; }
OK="Installed the AI guide and knowledge pack (version $GOOD): "

echo "--- A1, A2: the real pack"
setup; OUT=$(run BLK)
printf '%s\n' "$OUT" | sed 's/^/      | /'
row "A1 the success line names the version and the block reached its end" \
    "$(printf '%s' "$OUT" | grep -q -F "$OK" && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "$OUT"
row "A1b ...sudo WAS asked to make the directory and copy guide and pack (the null case: a block that did nothing prints nothing here)" \
    "$(grep -q '^mkdir -p ' "$T/sudo.log" && grep -q '^cp -R agent-pack/guide agent-pack/pack ' "$T/sudo.log" && echo 0 || echo 1)" "sudo log: $(tr '\n' ';' < "$T/sudo.log")"
row "A1c ...the guide and every file of pack/ are in the destination, byte for byte (and there are some)" \
    "$([ -f "$DEST/guide/sd-basic-guide.md" ] && [ "$(find "$DEST/pack" -type f | wc -l)" -ge 10 ] && diff -r "$T/work/agent-pack/pack" "$DEST/pack" > /dev/null && diff -r "$T/work/agent-pack/guide" "$DEST/guide" > /dev/null && echo 0 || echo 1)" "$(ls -R "$DEST" 2>&1 | head -5)"
row "A2 only guide/ and pack/ are copied: no skill, templates, recipe, generator or notes" \
    "$([ "$(ls "$DEST" | tr '\n' ' ')" = "guide pack " ] && echo 0 || echo 1)" "destination holds: $(ls "$DEST" | tr '\n' ' ')"

absent() {   # name, what-to-remove-from-the-clone
  setup; ( cd "$T/work" && rm -rf $2 )
  OUT=$(run BLK)
  row "$1: a note, nothing copied, the install is not stopped" \
      "$(printf '%s' "$OUT" | grep -q 'Note: the download holds no complete AI guide' && printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DEST" ] && ! grep -q '^cp ' "$T/sudo.log" && echo 0 || echo 1)" "$OUT / dest: $(ls "$DEST" 2>&1 | head -2)"
}
echo "--- A3: nothing, or half, to install"
absent "A3 no agent-pack at all (an older tag)" "agent-pack"
absent "A3b the guide but no manifest" "agent-pack/pack/manifest.json"
absent "A3c the manifest but no core.md" "agent-pack/pack/core.md"
absent "A3d the pack but no guide" "agent-pack/guide/sd-basic-guide.md"

echo "--- A4: a pack for another version"
setup
sed 's/"rev_stamp": "[^"]*"/"rev_stamp": "L9.9-9"/' "$T/work/agent-pack/pack/manifest.json" > "$T/m.json" && cp "$T/m.json" "$T/work/agent-pack/pack/manifest.json"
grep -q 'L9.9-9' "$T/work/agent-pack/pack/manifest.json" || { echo "test-install-agentpack: CANNOT RUN - the manifest edit changed nothing"; exit 2; }
OUT=$(run BLK)
row "A4 not installed, the note names the pack's version L9.9-9 and the installed one $GOOD, the install goes on" \
    "$(printf '%s' "$OUT" | grep -q -F "for version 'L9.9-9' and this is '$GOOD'" && printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DEST" ] && ! grep -q '^cp ' "$T/sudo.log" && echo 0 || echo 1)" "$OUT"

echo "--- A5: no installed revstamp.h (would stop an install under pipefail)"
setup; rm -f "$T/sdsys/gpl.bp/revstamp.h"
OUT=$(run BLK)
row "A5 not installed, the install goes on, the note says the installed version is unknown" \
    "$(printf '%s' "$OUT" | grep -q -F "and this is '?'" && printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DEST" ] && echo 0 || echo 1)" "$OUT"
setup; printf '{\n "chunk_count": 1\n}\n' > "$T/work/agent-pack/pack/manifest.json"
OUT=$(run BLK)
row "A5b a manifest with no rev_stamp: not installed, the install goes on" \
    "$(printf '%s' "$OUT" | grep -q -F "for version '?'" && printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DEST" ] && echo 0 || echo 1)" "$OUT"

setup; chmod 000 "$T/work/agent-pack/pack/manifest.json"
if [ -r "$T/work/agent-pack/pack/manifest.json" ]; then
  echo "  (A5c skipped: this caller can read a mode-000 file, so it cannot make a manifest unreadable)"
else
  OUT=$(run BLK)
  row "A5c a manifest that cannot be read: not installed, the install goes on (the read is guarded, not assumed to work)" \
      "$(printf '%s' "$OUT" | grep -q -F "for version '?'" && printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DEST" ] && echo 0 || echo 1)" "$OUT"
fi
chmod 644 "$T/work/agent-pack/pack/manifest.json"

echo "--- A6: the mode block (after the installer's chmod -R 755)"
setup; run BLK > /dev/null
chmod -R 755 "$T/sdsys"                       # what the installer has just done to the whole tree
OUT=$(run MODE)
row "A6 every file of agent-pack is 644 (the text is not a program) and the block reached its end" \
    "$([ -z "$(find "$DEST" -type f ! -perm 644)" ] && [ -n "$(find "$DEST" -type f)" ] && printf '%s' "$OUT" | grep -q REACHED-END && echo 0 || echo 1)" "not 644: $(find "$DEST" -type f ! -perm 644 | head -3 | tr '\n' ' ') / $OUT"
row "A6b ...directories stay 755 and nothing in it is writable by group or other (an SD user cannot plant text for another user's agent)" \
    "$([ -z "$(find "$DEST" -type d ! -perm 755)" ] && [ -z "$(find "$DEST" -perm /022)" ] && echo 0 || echo 1)" "writable by group/other or not 755: $(find "$DEST" -perm /022 | head -3 | tr '\n' ' ')"
setup; chmod -R 755 "$T/sdsys"; OUT=$(run MODE)
row "A6c no agent-pack installed: the mode block does nothing and does not stop the install" \
    "$(printf '%s' "$OUT" | grep -q REACHED-END && [ ! -e "$DEST" ] && ! grep -q 'find' "$T/sudo.log" && echo 0 || echo 1)" "$OUT"

echo "--- A7: the order in the installer"
ln_of() { grep -n -m1 -F -x -- "$1" "$INST" | cut -d: -f1; }
ln_last() { grep -n -F -x -- "$1" "$INST" | tail -1 | cut -d: -f1; }
L_SD=$(ln_of 'sudo cp -R sdsys /usr/local'); L_MC=$(ln_of 'sudo cp -r gplbld/microcfg "$sdsysdir"')
L_B=$(ln_of '# AGENTPACK-BEGIN'); L_CH=$(ln_of 'sudo chown -R sdsys:sdusers "$sdsysdir"')
L_M=$(ln_of '# AGENTPACK-MODE-BEGIN'); L_C755=$(ln_last 'sudo chmod -R 755 "$sdsysdir"')
echo "      lines: cp sdsys $L_SD, microcfg $L_MC, copy block $L_B, first chown -R $L_CH, last chmod -R 755 $L_C755, mode block $L_M"
if [ -z "$L_SD" ] || [ -z "$L_MC" ] || [ -z "$L_B" ] || [ -z "$L_CH" ] || [ -z "$L_M" ] || [ -z "$L_C755" ]; then
  echo "test-install-agentpack: CANNOT RUN - an anchor line is not in the installer (so the order cannot be judged)"; exit 2
fi
row "A7 the copy comes after the tree is copied in and before the first chown -R of the whole tree (so it lands sdsys:sdusers)" \
    "$([ "$L_SD" -lt "$L_B" ] && [ "$L_MC" -lt "$L_B" ] && [ "$L_B" -lt "$L_CH" ] && echo 0 || echo 1)" "lines $L_SD $L_MC < $L_B < $L_CH"
row "A7b the mode block comes after the last chmod -R 755 (which would otherwise make the text 755 again)" \
    "$([ "$L_M" -gt "$L_C755" ] && echo 0 || echo 1)" "mode block $L_M, last chmod -R 755 $L_C755"
row "A8 neither block contains an exit (a documents-only feature never ends an install)" \
    "$(printf '%s\n%s\n' "$BLK" "$MODE" | grep -q -E '(^|[^a-z_])exit([^a-z_]|$)' && echo 1 || echo 0)" "an exit is in the block"

echo "test-install-agentpack: $pass passed, $fail failed"
[ "$((pass + fail))" -eq 0 ] && { echo "test-install-agentpack: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
