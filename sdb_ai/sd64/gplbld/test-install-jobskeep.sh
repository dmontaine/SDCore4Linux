#!/bin/bash
# test-install-jobskeep.sh - the scheduled jobs across a kept configuration (22 Nov 2026, S.284; owner, 21 Nov 2026: "settings do not get changes after
# delete and install if the user chooses keep data").  deletesdcore.sh JOBS-SAVE copies /etc/sdcore/jobs.d to /home/sd/jobs.saved when the configuration
# is kept; installsdcore.sh JOBS-RESTORE gives each saved definition to the helper's job-set again, as root with SUDO_USER taken out, and removes the copy.
# No sudo, no systemd, no install.  Exit 0 every row held, 1 one did not, 2 it could not run.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-jobskeep.sh [--selftest]
#
# THE BLOCKS.  JOBS-SAVE is cut out of the remover with /etc/sdcore/jobs.d pointed at a scratch directory and run with `sudo` a function; JOBS-RESTORE's
# function is cut out of the installer and run under its own `set -euo pipefail` and IFS with a STUB helper that records its arguments and whether it saw
# SUDO_USER.  The order (the save before the definitions go; the restore after the helper is installed) is read as TEXT.  It cannot say a real job-set
# schedules a real timer: that is a real-install row, NOT run for this change.
#
# --selftest breaks the two scripts in the ways listed at the end and requires the rows to notice each one.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THIS="$HERE/$(basename "${BASH_SOURCE[0]}")"
ROOT="$(cd "$HERE/../../.." && pwd)"
INSTALLER="${INSTALLER:-$ROOT/installsdcore.sh}"
REMOVER="${REMOVER:-$ROOT/deletesdcore.sh}"
passed=0; failed=0
row() {   # row "name" ok(0|1) ["detail"]
  if [ "$2" = 0 ]; then passed=$((passed+1)); echo "  [PASS] $1"
  else failed=$((failed+1)); echo "  [FAIL] $1${3:+   <- $3}"; fi
}

if [ "${1:-}" = "--selftest" ]; then
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  caught=0; missed=0
  mutant() {   # name, file (i or r), sed expression
    local f="$T/$1.sh" ei="$ROOT/installsdcore.sh" er="$ROOT/deletesdcore.sh" src
    if [ "$2" = i ]; then src="$ei"; else src="$er"; fi
    sed -e "$3" "$src" > "$f"
    if cmp -s "$src" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); return; fi
    if [ "$2" = i ]; then ei="$f"; else er="$f"; fi
    if INSTALLER="$ei" REMOVER="$er" bash "$THIS" > "$T/$1.out" 2>&1; then echo "  [MISSED] $1: the check still passed"; missed=$((missed+1))
    else echo "  [caught] $1"; caught=$((caught+1)); fi
  }
  echo "selftest: the real scripts first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real scripts do not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real scripts pass"
  mutant saved-on-delete     r 's/^if \[ "\$conf_deleted" = no \] \&\& sudo test -d \/etc\/sdcore\/jobs.d/if sudo test -d \/etc\/sdcore\/jobs.d/'
  mutant link-followed       r 's/ \&\& ! sudo test -L \/etc\/sdcore\/jobs.d; then/; then/'
  mutant sudo-user-kept      i 's/sudo env -u SUDO_USER "\$helper" job-set/sudo "$helper" job-set/'
  mutant schedule-one-word   i 's/"\${words\[@\]}" 2>\&1); then/"$sched" 2>\&1); then/'
  mutant refusal-counted-ok  i 's/            bad=\$((bad+1))/            ok=$((ok+1))/'
  mutant copy-left           i 's/^sudo rm -rf \/home\/sd\/jobs.saved$/true/'
  echo "selftest: $caught caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

for f in "$INSTALLER" "$REMOVER"; do [ -r "$f" ] || { echo "test-install-jobskeep: CANNOT RUN - $f is not there"; exit 2; }; done
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
echo "installer : $INSTALLER"; echo "remover   : $REMOVER"
awk '/^# JOBS-SAVE-BEGIN$/,/^# JOBS-SAVE-END$/' "$REMOVER" | sed -e "s#/etc/sdcore/jobs.d#$T/etc/jobs.d#g" > "$T/save.sh"
awk '/^# JOBS-RESTORE-BEGIN$/,/^# JOBS-RESTORE-END$/' "$INSTALLER" > "$T/restore.sh"
grep -q 'jobs.saved' "$T/save.sh" && grep -q '^restore_saved_jobs()' "$T/restore.sh" || { echo "test-install-jobskeep: CANNOT RUN - a block is missing"; exit 2; }
has() { printf '%s\n' "$1" | grep -qF -- "$2"; }

mkjobs() {   # mkjobs DIR: two definitions as job-set writes them
  mkdir -p "$1"
  printf '%s\n' '# an SD scheduled job' 'name=nightly' 'job=backup' 'command=backup.account all' 'schedule=daily 02:30' 'oncalendar=*-*-* 02:30:00' > "$1/nightly"
  printf '%s\n' '# an SD scheduled job' 'name=often' 'job=sync' 'command=sync.masters' 'schedule=every 15 minutes' 'oncalendar=*-*-* *:0/15:00' > "$1/often"
}
save() {   # save CONF_DELETED ACCT -> output
  acct_path="$2" conf_deleted="$1" bash -c 'set -uo pipefail; sudo() { "$@"; }; . "'"$T"'/save.sh"' 2>&1
}
mkjobs "$T/etc/jobs.d"; mkdir -p "$T/a1"
out="$(save no "$T/a1")"
row "J1 the configuration kept: both definitions are copied to jobs.saved (mode 700), and it is said" \
  "$([ -f "$T/a1/jobs.saved/nightly" ] && [ -f "$T/a1/jobs.saved/often" ] && [ "$(stat -c %a "$T/a1/jobs.saved")" = 700 ] && has "$out" "Saved the scheduled jobs' definitions" && echo 0 || echo 1)" "$out"
mkdir -p "$T/a2/jobs.saved"; echo old > "$T/a2/jobs.saved/stale"
out="$(save yes "$T/a2")"
row "J2 the configuration deleted: nothing is saved, and an older saved copy is removed" "$([ ! -e "$T/a2/jobs.saved" ] && ! has "$out" "Saved" && echo 0 || echo 1)" "$out"
rm -rf "$T/etc/jobs.d"; mkjobs "$T/real.d"; ln -s "$T/real.d" "$T/etc/jobs.d"; mkdir -p "$T/a3"
out="$(save no "$T/a3")"
row "J3 a jobs.d that is a LINK is not followed: nothing is saved" "$([ ! -e "$T/a3/jobs.saved" ] && echo 0 || echo 1)" "$out"

printf '%s\n' '#!/bin/bash' '{ printf "ARGS"; printf "|%s" "$@"; echo " SUDO_USER=${SUDO_USER-unset}"; } >> "$HLOG"' 'case "$3" in refuse-me) echo "sd-elevate: no such job" >&2; exit 1 ;; esac' 'exit 0' > "$T/helper"
chmod +x "$T/helper"
restore() {   # restore DIR -> output; the helper's log is $T/hlog
  : > "$T/hlog"
  HLOG="$T/hlog" SUDO_USER=don bash -c '
    set -euo pipefail
    IFS=$'"'"'\n\t'"'"'
    sudo() { "$@"; }
    . "'"$T"'/restore.sh"
    restore_saved_jobs "$1" "$2"
  ' _ "$1" "$T/helper" 2>&1
}
mkjobs "$T/r1"
out="$(restore "$T/r1")"
row "J4 each saved definition goes to job-set with its name, its job and its schedule as WORDS, with SUDO_USER taken out; the count is said" \
  "$(grep -qxF 'ARGS|job-set|nightly|backup|daily|02:30 SUDO_USER=unset' "$T/hlog" && grep -qxF 'ARGS|job-set|often|sync|every|15|minutes SUDO_USER=unset' "$T/hlog" && has "$out" "Scheduled jobs: 2 scheduled again, 0 NOT." && echo 0 || echo 1)" "log=$(tr '\n' ';' < "$T/hlog") out=$out"
mkdir -p "$T/r2"; printf '%s\n' 'name=bad' 'job=refuse-me' 'schedule=hourly' > "$T/r2/bad"; printf '%s\n' 'name=empty' 'schedule=hourly' > "$T/r2/empty"
out="$(restore "$T/r2")"
row "J5 a definition job-set refuses, and one with no job, are each named NOT scheduled; the count says 0 and 2" \
  "$(has "$out" "NOT scheduled again: bad" && has "$out" "NOT scheduled again: empty" && has "$out" "Scheduled jobs: 0 scheduled again, 2 NOT." && ! grep -q 'job-set|empty' "$T/hlog" && echo 0 || echo 1)" "$out"

l_save="$(grep -n '^# JOBS-SAVE-BEGIN$' "$REMOVER" | cut -d: -f1)"; l_rm="$(grep -n '^sudo rm -rf /etc/sdcore/jobs.d$' "$REMOVER" | cut -d: -f1)"
l_tim="$(grep -n 'sudo rm -f /etc/systemd/system/sdcore-job-\*.timer' "$REMOVER" | head -1 | cut -d: -f1)"
row "T1 the remover takes the timers out first, then saves, then removes the definitions" "$([ -n "$l_tim" ] && [ -n "$l_save" ] && [ -n "$l_rm" ] && [ "$l_tim" -lt "$l_save" ] && [ "$l_save" -lt "$l_rm" ] && echo 0 || echo 1)" "timers $l_tim, save $l_save, rm $l_rm"
l_hlp="$(grep -n 'sudo install -o root -g root -m 0755 gplbld/sd-elevate /usr/local/sbin/sd-elevate' "$INSTALLER" | cut -d: -f1)"
l_call="$(grep -n '^    restore_saved_jobs /home/sd/jobs.saved /usr/local/sbin/sd-elevate$' "$INSTALLER" | cut -d: -f1)"
l_del="$(grep -n '^sudo rm -rf /home/sd/jobs.saved$' "$INSTALLER" | cut -d: -f1)"
row "T2 the installer restores AFTER the helper is installed, and then removes the saved copy" "$([ -n "$l_hlp" ] && [ -n "$l_call" ] && [ -n "$l_del" ] && [ "$l_hlp" -lt "$l_call" ] && [ "$l_call" -lt "$l_del" ] && echo 0 || echo 1)" "helper $l_hlp, call $l_call, rm $l_del"

echo
echo "test-install-jobskeep: $passed passed, $failed failed"
[ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]
