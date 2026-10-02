#!/bin/bash
#
# test-install-pass3.sh - installsdcore.sh's "Bootstrap pass 3" block, run the
#                         way the installer runs it.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-pass3.sh
#
# FREE CHECK: no sudo, no install, no sd.  Exit 0 all rows pass, 1 a row
# failed, 2 it could not run.
#
# WHY IT EXISTS (29 Sep 2026, S.48).  The pass-3 check stopped TWO real
# installs silently, right after a clean pass 3: installsdcore.sh runs under
# "set -euo pipefail", and "x=$(... | grep ... | head -1)" with grep finding
# nothing - the clean case - is a failing assignment, which ends the script
# with no message.  The first harness evaluated the block WITHOUT those
# options and passed 10/10.  So this one reads the options from the
# installer's own "set" line and evaluates the block, extracted verbatim,
# under them, with sudo stubbed to print canned sd output.
#
# Rows: a clean run goes on quietly; a stop word, a missing COMPLETE or sd's
# non-zero exit stops the install WITH its message ("Install terminated") -
# never silently (the check is strict again, owner 29 Sep 2026).  If the real
# output of an install is on this machine (/var/tmp/sdcore-install-pass3.log,
# written by the installer), it is the first row.

INST="$(cd "$(dirname "$0")/../../.." && pwd)/installsdcore.sh"
REAL=/var/tmp/sdcore-install-pass3.log
OPTS=$(grep -m1 -E '^set -' "$INST")
BLOCK=$(awk '/^echo "Bootstrap pass 3."/{f=1} f{print} f&&/^fi$/{n++} f&&n==2{exit}' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}"
[ -z "$OPTS" ] && { echo "test-install-pass3: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-pass3: CANNOT RUN - no pass-3 block in the installer"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | wc -l) lines"
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT
export BLOCK OPTS LOG

pass=0; fail=0
run_case() {   # name, want-stop (stop|go), want-warn (warn|quiet), want-msg (msg|nomsg), rc, output
  local name="$1" wstop="$2" wwarn="$3" wmsg="$4" rc="$5" out="$6" res stop warn msg r
  res=$(CANNED="$out" CANNED_RC="$rc" bash -c '
      eval "$OPTS"
      sudo() { if [ "$1" = tee ]; then shift; command tee "$@" >/dev/null; else printf "%s" "$CANNED"; return "$CANNED_RC"; fi; }
      sdsysdir=/x; RED=; NC=
      B=${BLOCK//\/var\/tmp\/sdcore-install-pass3.log/$LOG}
      eval "$B"
      echo REACHED-END' 2>&1)
  case "$res" in *REACHED-END*) stop=go ;; *) stop=stop ;; esac
  case "$res" in *WARNING:*) warn=warn ;; *) warn=quiet ;; esac
  case "$res" in *"Install terminated"*) msg=msg ;; *) msg=nomsg ;; esac
  if [ "$stop$warn$msg" = "$wstop$wwarn$wmsg" ]; then pass=$((pass+1)); r=PASS; else fail=$((fail+1)); r=FAIL; fi
  printf '  [%s] %-34s want=%s/%s/%s got=%s/%s/%s\n' "$r" "$name" "$wstop" "$wwarn" "$wmsg" "$stop" "$warn" "$msg"
}
if [ -r "$REAL" ]; then
  run_case "real install output ($REAL)" go quiet nomsg 0 "$(grep -v '^sd exit code:' "$REAL")"
else
  echo "  (no $REAL on this machine - the real-output row is skipped)"
fi
run_case "clean, CR line ends, rc 0"    go   quiet nomsg 0 $'\e[H\e[J\r\nDICTIONARY: voc.dic x\r\nCOMPLETE\r\n'
run_case "error opening, rc 0"          stop quiet msg   0 $'ERROR OPENING FILE: /x\nPROCESS ABORTED\n'
run_case "session refused, rc 0"        stop quiet msg   0 $'Connection terminated\n'
run_case "no COMPLETE, rc 0"            stop quiet msg   0 $'DICTIONARY: voc.dic x\n'
run_case "INCOMPLETE is not COMPLETE"   stop quiet msg   0 $'INCOMPLETE\n'
run_case "sd rc=1 stops, with message"  stop quiet msg   1 $'COMPLETE\n'
echo "test-install-pass3: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-pass3: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
