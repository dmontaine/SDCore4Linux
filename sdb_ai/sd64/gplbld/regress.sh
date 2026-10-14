#!/bin/bash
#
# regress.sh - run the sandbox suites, one fresh build each, and say which passed.  No install, no sudo.
#
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh                     all of them, about 12 minutes
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --skip ced          all but the pseudo-terminal one (3.8 minutes of the 12)
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --only coll,try     just those
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --tree DIR          the suites of the sd64 tree DIR, in that tree
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --free              then the gplbld/test-*.py free checks too
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --list              print the suites and stop
#
# Exit 0 every suite passed, 1 a suite failed (or gave no verdict), 2 something could not be run (an unknown suite,
# a sandbox already holding the sandbox shared memory keys, a suite that said CANNOT RUN).  No sudo.
#
# WHAT IT COUNTS AS A PASS.  A suite passes only when it exits 0 AND its own last line says "N passed, M failed" with
# M = 0 and N > 0.  A suite that printed no such line, exited non-zero, or passed no rows FAILS: "nothing went wrong"
# is not a verdict (CLAUDE.md, an instrument shows what it DID).  Every suite's whole output is kept in the log
# directory, which is printed, and the [FAIL] rows of a failed suite are shown.
#
# WHY A SNAPSHOT.  Each suite builds its sandbox from the tree it lives in, so editing a kernel source while the run
# is going voids the suites still to come.  To keep working, run it on a copy:
#   git ls-files -z --cached --others --exclude-standard sdb_ai | rsync -a --from0 --files-from=- ./ COPY/
#   cp sdb_ai/sd64/gplsrc/sdext_python_inc.h COPY/sdb_ai/sd64/gplsrc/      (git ignores it; the build needs it)
#   (cd COPY/sdb_ai/sd64 && make)                                           (SERIAL: make -j races sdtic and terminfo)
#   COPY/sdb_ai/sd64/gplbld/regress.sh --tree COPY/sdb_ai/sd64
# The suites use fixed shared memory keys (0x53434c91, 0x53434c92), so two cannot run at once, here or with a
# sandbox of your own; the run refuses to start while the keys are held.  Each sandbox leaves ~14,000 files in /tmp
# (1M inodes there) and is removed as soon as its suite ends.
#
# START-HISTORY:
# 12 Oct 26 dm  New.  The list and the loop had lived in a scratchpad script that was lost between sessions; the
#               timing (11.8 minutes for 26 suites, 15 s of each being the sandbox build) is from the run of 12 Oct.
# 12 Oct 26 dm  lock-b6 added (the 27th suite, 49 s; the 27 together took 14 minutes).
# 12 Oct 26 dm  file-b8 added (the 28th suite, about 80 s).
# 12 Oct 26 dm  lang-a15 added (the 29th suite).
# 12 Oct 26 dm  fix-b10 added (the 30th suite).
# 12 Oct 26 dm  sed-menu (SED's menu bar and the screen library's widgets, 81 rows) and screen (the SCREEN statement
#               through user programs) added (the 31st and 32nd suites); both on the branch sed-screenlib.
# 13 Oct 26 dm  gates added (S.63, the per-account OS-access gates): the 31st suite on Dev, the 33rd with the two above.
# 13 Oct 26 dm  syntax added (SED's syntax colour, 22 rows): the 34th on the branch.
# 13 Oct 26 dm  dbgui added (the debugger's full-screen display on the library, 16 rows): the 35th.
# 13 Oct 26 dm  sed-edit added (SED's undo and redo and its mouse, 71 rows): the 36th.
# 14 Oct 26 dm  ide added (the IDE, gpl.bp/ide, 52 rows): the 37th.
# END-HISTORY

set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TREE=$(dirname "$HERE")

# The suites, in the order that shows a failure soonest: the editor (the longest) and the newest first.
ALL_SUITES="ced screen sed-menu sed-edit ide syntax dbgui collfile dbgcoll akcase coll try oq2 bcomp-a1 stmt-b5 func-b4 qproc-a3 dict-a2 conv-b3 misc-a9 list-a7 input nocase callcase dictfold audit-b9 file-a8 option-a4 proc-a5 upgradenocase sys-b2 conf-b1 lock-b6 file-b8 lang-a15 fix-b10 gates"

ONLY=""
SKIP=""
FREE=0
SUITES_OFF=0
LIST=0
LOGS=""
LIMIT=3000

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tree) TREE=$(cd "$2" && pwd) || exit 2; shift 2 ;;
    --only) ONLY=$2; shift 2 ;;
    --skip) SKIP=$2; shift 2 ;;
    --free) FREE=1; shift ;;
    --no-suites) SUITES_OFF=1; shift ;;
    --list) LIST=1; shift ;;
    --logs) LOGS=$2; shift 2 ;;
    --limit) LIMIT=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "regress: unknown argument '$1' (try --help)" >&2; exit 2 ;;
  esac
done

if [ -n "$ONLY" ]; then SUITES=${ONLY//,/ }; else SUITES=$ALL_SUITES; fi
KEEP=""
for s in $SUITES; do
  skipped=0
  for k in ${SKIP//,/ }; do [ "$k" = "$s" ] && skipped=1; done
  [ $skipped -eq 0 ] && KEEP="$KEEP $s"
done
SUITES=${KEEP# }

if [ $LIST -eq 1 ]; then
  for s in $SUITES; do echo "$s"; done
  exit 0
fi

if [ ! -d "$TREE/gplbld" ]; then
  echo "regress: CANNOT RUN - $TREE has no gplbld directory" >&2
  exit 2
fi

echo "regress: tree     $TREE"

# An unknown suite is a refusal, not a pass over nothing.
if [ $SUITES_OFF -eq 0 ]; then
  for s in $SUITES; do
    if [ ! -f "$TREE/gplbld/sandbox-$s.py" ]; then
      echo "regress: CANNOT RUN - no suite '$s' ($TREE/gplbld/sandbox-$s.py is not there)" >&2
      exit 2
    fi
  done
  if [ -z "$SUITES" ]; then
    echo "regress: CANNOT RUN - no suite is selected" >&2
    exit 2
  fi
  held=$(ipcs -m 2>/dev/null | grep -i -E '0x53434c9[12]' | head -2)
  if [ -n "$held" ]; then
    echo "regress: CANNOT RUN - a sandbox already holds the shared memory keys 0x53434c91/92:" >&2
    echo "$held" >&2
    echo "         stop it with  python3 $TREE/gplbld/sandbox-fromtree.py <its directory> stop  (or ipcrm -M 0x53434c91; ipcrm -S 0x53434c92 if its directory is gone)" >&2
    exit 2
  fi
fi

RUN=$(mktemp -d "${TMPDIR:-/tmp}/sdregress.XXXXXX") || { echo "regress: CANNOT RUN - no scratch directory" >&2; exit 2; }
[ -n "$LOGS" ] || LOGS="$RUN/logs"
mkdir -p "$LOGS" || { echo "regress: CANNOT RUN - cannot make $LOGS" >&2; exit 2; }
echo "regress: logs     $LOGS"

CURRENT=""
cleanup() {
  if [ -n "$CURRENT" ]; then
    python3 "$TREE/gplbld/sandbox-fromtree.py" "$CURRENT" stop >/dev/null 2>&1
    rm -rf "${CURRENT:?}"
  fi
}
trap 'cleanup; echo "regress: interrupted" >&2; exit 2' INT TERM

n=0
total=0
passed_suites=0
failed_suites=0
notrun_suites=0
failed_list=""
notrun_list=""
count=$(echo $SUITES | wc -w)
T0=$(date +%s)

if [ $SUITES_OFF -eq 0 ]; then
  echo "regress: suites   $count:$(for s in $SUITES; do printf ' %s' "$s"; done)"
  echo "regress: each     python3 $TREE/gplbld/sandbox-<suite>.py <fresh directory> --build"
  echo
fi

for s in $SUITES; do
  [ $SUITES_OFF -eq 1 ] && break
  n=$((n + 1))
  d="$RUN/sbx-$s"
  CURRENT=$d
  log="$LOGS/$s.out"
  t1=$(date +%s)
  timeout "$LIMIT" python3 "$TREE/gplbld/sandbox-$s.py" "$d" --build > "$log" 2>&1
  rc=$?
  python3 "$TREE/gplbld/sandbox-fromtree.py" "$d" stop >/dev/null 2>&1
  rm -rf "${d:?}"
  CURRENT=""
  secs=$(( $(date +%s) - t1 ))
  total=$((total + secs))

  # The suite's own last line: "sandbox-NAME: N passed, M failed" - and nothing else is taken as a verdict.
  verdict=$(grep -E '^sandbox-[A-Za-z0-9._-]+: [0-9]+ passed, [0-9]+ failed' "$log" | tail -1)
  passed=0
  failed=0
  if [ -n "$verdict" ]; then
    passed=$(echo "$verdict" | sed -E 's/^[^:]+: ([0-9]+) passed, ([0-9]+) failed.*/\1/')
    failed=$(echo "$verdict" | sed -E 's/^[^:]+: ([0-9]+) passed, ([0-9]+) failed.*/\2/')
  fi

  why=""
  if [ "$rc" -eq 2 ] || grep -q 'CANNOT RUN' "$log"; then
    status="NOT RUN"
    why=$(grep -m1 'CANNOT RUN' "$log" | cut -c1-110)
    [ -n "$why" ] || why="exit $rc"
  elif [ -z "$verdict" ]; then
    status="FAIL"
    why="no verdict line (exit $rc)"
  elif [ "$rc" -ne 0 ]; then
    status="FAIL"
    why="exit $rc"
  elif [ "$failed" -ne 0 ]; then
    status="FAIL"
    why="$failed failed"
  elif [ "$passed" -eq 0 ]; then
    status="FAIL"
    why="no row passed"
  else
    status="PASS"
  fi

  printf '[%2d/%d] %-14s %-8s %5s passed  %4d s  %s\n' "$n" "$count" "$s" "$status" "$passed" "$secs" "$why"
  case "$status" in
    PASS) passed_suites=$((passed_suites + 1)) ;;
    FAIL)
      failed_suites=$((failed_suites + 1))
      failed_list="$failed_list $s"
      grep -E '\[FAIL\]' "$log" | head -5 | cut -c1-200 | sed 's/^/         /'
      ;;
    *)
      notrun_suites=$((notrun_suites + 1))
      notrun_list="$notrun_list $s"
      ;;
  esac
done

free_failed=0
free_ran=0
if [ $FREE -eq 1 ]; then
  echo
  echo "regress: free checks  (gplbld/test-*.py, run from $TREE)"
  for t in "$TREE"/gplbld/test-*.py; do
    [ -f "$t" ] || continue
    free_ran=$((free_ran + 1))
    if ! (cd "$TREE" && timeout 180 python3 "$t" > "$LOGS/$(basename "$t").out" 2>&1); then
      free_failed=$((free_failed + 1))
      echo "         FAIL $(basename "$t")   (see $LOGS/$(basename "$t").out)"
    fi
  done
  [ "$free_ran" -gt 0 ] || { echo "         no test-*.py found"; free_failed=$((free_failed + 1)); }
  echo "regress: free checks  $free_ran run, $free_failed failed"
fi

echo
elapsed=$(( $(date +%s) - T0 ))
if [ $SUITES_OFF -eq 0 ]; then
  echo "regress: $count suites: $passed_suites passed, $failed_suites failed${failed_list:+ ($failed_list )}, $notrun_suites not run${notrun_list:+ ($notrun_list )}; $total s in the suites, $elapsed s in all"
fi

rmdir "$RUN/logs" 2>/dev/null
if [ "$LOGS" != "$RUN/logs" ]; then rmdir "$RUN" 2>/dev/null; fi

if [ "$failed_suites" -gt 0 ] || [ "$free_failed" -gt 0 ]; then exit 1; fi
if [ "$notrun_suites" -gt 0 ]; then exit 2; fi
exit 0
