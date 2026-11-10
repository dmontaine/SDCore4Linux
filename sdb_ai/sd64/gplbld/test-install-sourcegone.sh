#!/bin/bash
#
# test-install-sourcegone.sh - installsdcore.sh compiles the last program and then leaves no source in the installed tree (S.198, 10 Nov 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sourcegone.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sourcegone.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-sourcegone.sh      (what --selftest uses)
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it could not run (a missing block is exit 2, never a pass).
#
# The block between SOURCE-GONE-BEGIN and SOURCE-GONE-END is cut out of the installer and run under its own "set" and "IFS" lines on a scratch tree, with
# sudo a function and bin/sd a stub that prints what the real session prints (measured on a sandbox, 10 Nov 26).  It cannot say SD still works with the
# source gone: that is witness-absence.sh M15 and a real install.
#
#   A  a good session: every source item is gone, the compiled programs and the rest of voc_template stay, define_install.h was written first
#   B  the compile fails (no success line): exit 1, the source is left where it is
#   C  the VOC records are not deleted: exit 1, the source is left
#   D  sd exits non-zero: exit 1
#   E  rm leaves an item behind: exit 1 and the item is named
#   F  the block is placed after the last compile of gpl.bp and before fix_gcat_modes; no line after it names the source

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  REAL="$(cd "$HERE/../../.." && pwd)/installsdcore.sh"
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; n=0
  mutant() {   # name, sed expression
    local name="$1" expr="$2" f="$T/$1.sh" rc
    n=$((n+1))
    sed -e "$expr" "$REAL" > "$f"
    if cmp -s "$REAL" "$f"; then echo "  [MISSED] $name: the mutation changed nothing"; missed=$((missed+1)); return; fi
    INSTALLER="$f" bash "$THIS" > "$T/$name.out" 2>&1; rc=$?
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc)"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -5 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  mutant keeps-gplbp        's/^for source_item in gpl\.bp /for source_item in /'
  mutant keeps-gplsrc       's/^\(for source_item in .*\) gplsrc /\1 /'
  mutant keeps-template     's/ voc_template\/gpl\.bp / /'
  mutant no-compile-check   "s/grep -qF 'Compiled 1 program(s) with no errors'/grep -qF ''/"
  mutant no-delete-check    "s/grep -qF '3 record(s) deleted'/grep -qF ''/"
  mutant no-rc-check        's/\[ "\$final_rc" -ne 0 \] ||/false ||/'
  mutant no-rm-check        's/if sudo test -e "\$sdsysdir\/\$source_item"; then/if false; then/'
  mutant no-voc-delete      's/DELETE VOC gpl\.bp first\.compile second\.compile\\n//'
  mutant no-define          '/define-install "\$sdsysdir/d'
  echo "selftest: $caught of $n mutants caught, $missed missed"
  [ "$caught" -eq "$n" ] && [ "$missed" -eq 0 ]
  exit $?
fi

OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
BLOCK=$(awk '/^# SOURCE-GONE-BEGIN$/{f=1;next} /^# SOURCE-GONE-END$/{f=0} f{print}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
echo "ifs       : ${IFSL:-<none found>}"
[ -z "$OPTS" ]  && { echo "test-install-sourcegone: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-sourcegone: CANNOT RUN - no SOURCE-GONE block in the installer (nothing to check)"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf '  [PASS] %s\n' "$1"
  else fail=$((fail+1)); printf '  [FAIL] %s   <- %s\n' "$1" "$3"; fi
}
SOURCE_ITEMS=$'gpl.bp\ngplsrc\ngplobj\ngplbld\ngpl.src\nMakefile\nvoc_template/gpl.bp\nvoc_template/first.compile\nvoc_template/second.compile'
make_tree() {   # dir: a scratch sdsys directory
  mkdir -p "$1/gpl.bp" "$1/gplsrc" "$1/gplobj" "$1/gplbld/FILES_DICTS" "$1/gpl.bp.out" "$1/voc_template" "$1/bin"
  echo x > "$1/gpl.bp/cproc"; echo x > "$1/gplsrc/sd.c"; echo x > "$1/gplobj/sd.o"; echo x > "$1/gpl.src"; echo x > "$1/Makefile"
  echo x > "$1/gpl.bp.out/cproc"; echo x > "$1/voc_template/gpl.bp"; echo x > "$1/voc_template/first.compile"; echo x > "$1/voc_template/second.compile"
  echo x > "$1/voc_template/gpl.bp.out"; echo x > "$1/voc_template/who"
}
run_block() {   # scratch dir, stub's output lines (\n escapes), stub's exit, what rm does: real or leave
  local d="$1" said="$2" code="$3" rmode="${4:-real}"
  bash -c "$OPTS"$'\n'"${IFSL:-}"$'\n'"sdsysdir='$d'; RED=''; NC=''
sudo() {
  case \"\$1\" in
    bin/sd)  cat > '$d/.session'; printf '$said'; return $code ;;
    rm)      if [ '$rmode' = leave ] && [ \"\${@: -1}\" = '$d/gplsrc' ]; then return 0; fi; \"\$@\" ;;
    *)       \"\$@\" ;;
  esac
}"$'\n'"$BLOCK"$'\n''echo BLOCK-FINISHED' 2>&1
}
GOOD='Compiling gpl.bp cproc\n0 error(s)\nCompiled 1 program(s) with no errors\n3 record(s) deleted\n'
present() { local d="$1" i n=0; while IFS= read -r i; do [ -e "$d/$i" ] && n=$((n+1)); done <<< "$SOURCE_ITEMS"; echo "$n"; }

# A
make_tree "$T/a"; out=$(run_block "$T/a" "$GOOD" 0); rc=$?
row "A: the block ends normally" $([ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q BLOCK-FINISHED && echo 0 || echo 1) "rc=$rc $out"
row "A0: the scratch tree had every item before the run (the null case)" $(make_tree "$T/a0"; [ "$(present "$T/a0")" -eq 9 ] && echo 0 || echo 1) "items: $(present "$T/a0")"
row "A1: every source item is gone" $([ "$(present "$T/a")" -eq 0 ] && echo 0 || echo 1) "left: $(present "$T/a")"
row "A2: the compiled programs stay (gpl.bp.out/cproc)" $([ -f "$T/a/gpl.bp.out/cproc" ] && echo 0 || echo 1) "gone"
row "A3: the rest of voc_template stays" $([ -f "$T/a/voc_template/gpl.bp.out" ] && [ -f "$T/a/voc_template/who" ] && echo 0 || echo 1) "gone"
row "A4: the session compiles cproc and only then deletes the three VOC records" $(awk '/BASIC gpl.bp cproc/{b=NR} /DELETE VOC gpl.bp first.compile second.compile/{d=NR} END{exit !(b && d && b<d)}' "$T/a/.session" && echo 0 || echo 1) "session: $(tr '\n' '|' < "$T/a/.session")"
d5=$(printf '%s\n' "$BLOCK" | grep -c 'IS_INSTALL')
row "A5: the block writes define_install.h (IS_INSTALL commented out)" $(printf '%s\n' "$BLOCK" | grep -q 'comment out \* \$define IS_INSTALL' && printf '%s\n' "$BLOCK" | grep -q 'define-install "\$sdsysdir/gpl.bp/define_install.h"' && echo 0 || echo 1) "lines naming IS_INSTALL: $d5"

# B, C, D: a bad session stops the install with the source still there
make_tree "$T/b"; out=$(run_block "$T/b" 'Compiling gpl.bp cproc\n3 error(s)\n3 record(s) deleted\n' 0); rc=$?
row "B: no success line: exit 1, the message, and the source is left" $([ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'CPROC recompile failed' && [ "$(present "$T/b")" -eq 9 ] && echo 0 || echo 1) "rc=$rc left=$(present "$T/b")"
make_tree "$T/c"; out=$(run_block "$T/c" 'Compiled 1 program(s) with no errors\n0 record(s) deleted\n' 0); rc=$?
row "C: the records not deleted: exit 1, and the source is left" $([ "$rc" -eq 1 ] && [ "$(present "$T/c")" -eq 9 ] && echo 0 || echo 1) "rc=$rc left=$(present "$T/c")"
make_tree "$T/d"; out=$(run_block "$T/d" "$GOOD" 3); rc=$?
row "D: sd exits non-zero: exit 1, and the source is left" $([ "$rc" -eq 1 ] && [ "$(present "$T/d")" -eq 9 ] && echo 0 || echo 1) "rc=$rc left=$(present "$T/d")"

# E
make_tree "$T/e"; out=$(run_block "$T/e" "$GOOD" 0 leave); rc=$?
row "E: an item rm left behind: exit 1, and it is named" $([ "$rc" -eq 1 ] && printf '%s' "$out" | grep -qF "$T/e/gplsrc could not be removed" && echo 0 || echo 1) "rc=$rc $out"

# F
lc=$(grep -n 'BASIC gpl\.bp' "$INST" | tail -1 | cut -d: -f1)
lb=$(grep -n '^# SOURCE-GONE-BEGIN$' "$INST" | cut -d: -f1)
le=$(grep -n '^# SOURCE-GONE-END$' "$INST" | cut -d: -f1)
lf=$(grep -n '^fix_gcat_modes$' "$INST" | tail -1 | cut -d: -f1)
row "F: the last compile of gpl.bp is inside the block, and the block ends before the last fix_gcat_modes" $([ -n "$lc" ] && [ -n "$lb" ] && [ -n "$le" ] && [ -n "$lf" ] && [ "$lb" -lt "$lc" ] && [ "$lc" -lt "$le" ] && [ "$le" -lt "$lf" ] && echo 0 || echo 1) "compile ${lc:-?} block ${lb:-?}-${le:-?} fix ${lf:-?}"
after=$(tail -n "+$((le + 1))" "$INST" | grep -vE '^[[:space:]]*#' | grep -nE '(sdsysdir|sdsys)/(gpl\.bp/|gpl\.bp"|gplsrc|gplobj|gplbld|gpl\.src)|bin/sd.* gpl\.bp ' || true)
row "F2: no command after the block names the installed source" $([ -z "$after" ] && echo 0 || echo 1) "$after"

echo "test-install-sourcegone: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
