#!/bin/bash
#
# test-install-nocase.sh - installsdcore.sh's "kept accounts are made case insensitive" block,
#                          run the way the installer runs it.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-nocase.sh
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 all rows pass, 1 a row failed, 2 it could not run.
#
# WHY IT EXISTS (7 Oct 2026, PAL-1 D2).  test-install-pass3.sh says why a block must be tested under
# the installer's own "set -euo pipefail": a harness that evaluated it without those options passed a
# block that stopped two real installs.  This block is new and runs only on an upgrade, so no install
# in the record has ever run it.  It reads the options from the installer's own "set" line and
# evaluates the block, extracted verbatim, under them, with sudo stubbed to print canned sd output.
#
# WHAT THE BLOCK MUST DO.  Never stop the install: an unconverted file works as it did, so even a run
# that failed outright goes on, but says so ("did not finish").  A clean run and a run that only names
# a twinned file say nothing of their own.  The success wording is COMPLETE on a line by itself; a
# line that merely CONTAINS it (INCOMPLETE) is not it, and neither is the sd exit code alone.

INST="$(cd "$(dirname "$0")/../../.." && pwd)/installsdcore.sh"
OPTS=$(grep -m1 -E '^set -' "$INST")
BLOCK=$(awk '/^    echo "Making every kept account.s files case insensitive."/{f=1} f{print} f&&/^    fi$/{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-nocase: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-nocase: CANNOT RUN - no nocase block in the installer"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT
export BLOCK OPTS LOG

pass=0; fail=0
run_case() {   # name, want-end (go|stop), want-warn (warn|quiet), rc, output
  local name="$1" wend="$2" wwarn="$3" rc="$4" out="$5" res end warn r
  res=$(CANNED="$out" CANNED_RC="$rc" bash -c '
      eval "$OPTS"
      sudo() { if [ "$1" = tee ]; then shift; command tee "$@" >/dev/null; else printf "%s" "$CANNED"; return "$CANNED_RC"; fi; }
      sdsysdir=/x; RED=; NC=
      B=${BLOCK//\/var\/tmp\/sdcore-install-nocase.log/$LOG}
      eval "$B"
      echo REACHED-END' 2>&1)
  case "$res" in *REACHED-END*) end=go ;; *) end=stop ;; esac
  case "$res" in *"did not finish"*) warn=warn ;; *) warn=quiet ;; esac
  if [ "$end$warn" = "$wend$wwarn" ]; then pass=$((pass+1)); r=PASS; else fail=$((fail+1)); r=FAIL; fi
  printf '  [%s] %-40s want=%s/%s got=%s/%s\n' "$r" "$name" "$wend" "$wwarn" "$end" "$warn"
}
run_case "clean run, rc 0"                     go quiet 0 $'Checking every file...\r\nConverted 4 of 5 file(s) to case insensitive ids.\r\nCOMPLETE\r\n'
run_case "a twin is named, still COMPLETE"     go quiet 0 $'WARNING: 1 file(s) hold 1 record id(s)\nCOMPLETE\n'
run_case "ANSI around COMPLETE"                go quiet 0 $'\e[H\e[J\nCOMPLETE\e[0m\n'
run_case "no COMPLETE, rc 0: goes on, says so"  go warn  0 $'Checking every file...\n'
run_case "INCOMPLETE is not COMPLETE"          go warn  0 $'INCOMPLETE\n'
run_case "COMPLETE inside a sentence is not it" go warn 0 $'Not COMPLETE yet\n'
run_case "sd rc=1: goes on, says so"           go warn  1 $'COMPLETE\n'
run_case "sd prints nothing at all, rc 0"      go warn  0 ''
echo "test-install-nocase: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-nocase: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
