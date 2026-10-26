#!/bin/bash
#
# test-install-rootbin.sh - W.11 F11 (security-model evaluation, 26 Oct 2026): the installer makes the files root runs - bin/sd, bin/sdlnxd, bin/sdidx and
# bin/pcode, with the directory bin and everything in it - root:root with no group or other write, and makes bin immutable (chattr +i) so that the sdsys user,
# who owns the system directory, cannot rename bin away and put a bin of its own in its place.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-rootbin.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-rootbin.sh --selftest
#   INSTALLER=<a copy of the installer> bash .../test-install-rootbin.sh      (what --selftest uses)
#
# FREE CHECK: no sudo (a function here), no install, no root.  Exit 0 every row passed, 1 a row failed, 2 it could not run (no block, or a scenario that did nothing).
#
# WHAT IT RUNS.  The lines between "# ROOTBIN-BEGIN" and "# ROOTBIN-END" are cut out of the installer and run under the installer's OWN `set` and `IFS` lines (the
# 19 Oct lesson: a block tested under `set` alone had been green and then did nothing on the real install) on a scratch system directory.  The real `find`, `chmod`,
# `awk`, `cut` and `head` run.  FOUR COMMANDS ARE STUBS because the user running this is not root and the scratch directory is not on an attribute-keeping file system:
#   chown   writes the call to a log and records the owner it was asked for in a table (with -R, every path below it too).  It FAILS on a path that is in the
#           immutable table, as the kernel does - so the `chattr -i` before the chown is load-bearing in the second run.  CHOWN_MISS=<path> makes it skip that one
#           path (a chown that did not take).
#   stat    prints the owner from that table (else the real one) and the real mode, in the only two formats the block uses; any other format is an error.
#   chattr  logs the call and keeps the immutable table; CHATTR_MODE=fail refuses (a file system without attributes), =noflag says yes and keeps nothing.
#   lsattr  prints a flag line with `i` for a path in the immutable table.
# What the real kernel does with the attribute, and who owns a file after a real chown, are NOT shown here: witness-f11.py on a real install.
#
#   R0  the block is there once and runs to its end under the installer's set and IFS
#   R1  a fresh tree: ONE chown -R root:root on bin; no entry of bin (hidden files, the directory, a 775 library, the 664 pcode.old included) has group or other
#       write afterwards; the executables keep their execute bits; chattr -i then chattr +i on bin, in that order; the four files are listed root:root; the success
#       line is printed and no WARNING
#   R2  a second run over the result (bin already immutable): it still seals - the stub chown refuses an immutable path, so this fails if `chattr -i` is not first
#   R3  an OPTIONAL file missing (sdfix, pcode.old): sealed, success line
#   R3b each of the four files missing in turn: a WARNING naming it, no success line, the rest still sealed
#   R4  a symlink in bin (where sd should be): everything LEFT EXACTLY AS IT WAS (no chown, no chattr, the modes unchanged), a WARNING naming it, no success line
#   R5  bin itself a symlink: refused the same way
#   R6  bin absent (the null case): refused, no call at all, no success line
#   R7  chattr refused: owner and mode are done, no success line, a WARNING that says the directory could not be made immutable and why that matters
#   R8  chattr says yes and the flag does not show (a file system that ignores it): the same as R7 - the verdict reads lsattr, not the exit status
#   R9  a chown that did not take on one file: that file is named under "Not root's", no success line
#   R10 rootbin_sealed (the flag the closing summary reads) is 1 after the all-good runs and 0 after every run that printed a WARNING
#   S1  static: the block gives nothing to the group or others (no chmod but go-w) and mentions sdsys only as the variable $sdsysdir
# ANCHORED ON THE DISK AND ON THE SUCCESS WORDING: "Root-run files are root's" is printed only on the all-good path; every failure path says "NOT".

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
INST="${INSTALLER:-$(cd "$HERE/../../.." && pwd)/installsdcore.sh}"
OKLINE="Root-run files are root's"

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
    if [ "$rc" -ne 0 ]; then echo "  [caught] $name (exit $rc: $(grep -m1 -E '^\s*\[FAIL\]' "$T/$name.out" | cut -c1-70))"; caught=$((caught+1))
    else echo "  [MISSED] $name: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real installer first (must pass), then mutants (each must not)"
  INSTALLER="$REAL" bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real installer does not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real installer passes"
  B='/^# ROOTBIN-BEGIN/,/^# ROOTBIN-END/'
  mutant chown-removed        "$B{/^    sudo chown -R root:root \"\$rootbin\"\$/d;}"
  mutant chown-not-recursive  "$B s|^    sudo chown -R root:root \"\$rootbin\"\$|    sudo chown root:root \"\$rootbin\"|"
  mutant chown-to-sdsys       "$B s|^    sudo chown -R root:root \"\$rootbin\"\$|    sudo chown -R sdsys:sdusers \"\$rootbin\"|"
  mutant chmod-removed        "$B{/^    sudo chmod -R go-w \"\$rootbin\"\$/d;}"
  mutant chmod-group-write    "$B s|^    sudo chmod -R go-w \"\$rootbin\"\$|    sudo chmod -R g+w \"\$rootbin\"|"
  mutant chmod-not-recursive  "$B s|^    sudo chmod -R go-w \"\$rootbin\"\$|    sudo chmod go-w \"\$rootbin\"|"
  mutant immutable-removed    "$B s|^    if sudo chattr +i \"\$rootbin\" 2>/dev/null; then|    if true; then|"
  mutant immutable-lifted     "$B s|^    if sudo chattr +i \"\$rootbin\" 2>/dev/null; then|    if sudo chattr -i \"\$rootbin\" 2>/dev/null; then|"
  mutant lift-before-removed  "$B{/^    sudo chattr -i \"\$rootbin\" 2>\/dev\/null || true\$/d;}"
  mutant symlink-test-gone    "$B s#^if \[ -L \"\$rootbin\" \] || \[ ! -d \"\$rootbin\" \]; then#if [ ! -d \"\$rootbin\" ]; then#"
  mutant absent-test-gone     "$B s#^if \[ -L \"\$rootbin\" \] || \[ ! -d \"\$rootbin\" \]; then#if [ -L \"\$rootbin\" ]; then#"
  mutant odd-find-blind       "$B s|-mindepth 1 \\\\! -type f|-mindepth 1 -name zz-no-such-name|"
  mutant odd-test-gone        "$B s|^if \[ -n \"\$rootbin_odd\" \]; then|if false; then|"
  mutant success-needs-no-imm "$B s#&& \[ \"\$rootbin_imm\" = yes \]; then#; then#"
  mutant success-ignores-bad  "$B s#^    if \[ -z \"\$rootbin_bad\" \] && #    if #"
  mutant success-ignores-miss "$B s#\[ -z \"\$rootbin_miss\" \] && ##"
  mutant verify-blind         "$B s|^    rootbin_bad=\$(.*|    rootbin_bad=\"\"|"
  mutant verify-no-glob       "$B s|\"\$rootbin\" \"\$rootbin\"/\* 2>|\"\$rootbin\" 2>|"
  mutant list-lost-sdidx      "$B s|^rootbin_files=(sd sdlnxd sdidx pcode)|rootbin_files=(sd sdlnxd pcode)|"
  mutant list-lost-pcode      "$B s|^rootbin_files=(sd sdlnxd sdidx pcode)|rootbin_files=(sd sdlnxd sdidx)|"
  mutant list-lost-sdlnxd     "$B s|^rootbin_files=(sd sdlnxd sdidx pcode)|rootbin_files=(sd sdidx pcode)|"
  mutant list-lost-sd         "$B s|^rootbin_files=(sd sdlnxd sdidx pcode)|rootbin_files=(sdlnxd sdidx pcode)|"
  mutant miss-test-gone       "$B s#^        \[ -f \"\$rootbin/\$f\" \] || rootbin_miss=.*#        :#"
  mutant sealed-never-set     "$B{/^        rootbin_sealed=1\$/d;}"
  mutant sealed-set-at-start  "$B s|^rootbin_sealed=0\$|rootbin_sealed=1|"
  mutant begin-marker-gone    "s|^# ROOTBIN-BEGIN|# rootbin-begin|"
  mutant end-marker-gone      "s|^# ROOTBIN-END|# rootbin-end|"
  mutant block-twice          "s|^# ROOTBIN-END\$|# ROOTBIN-END\n# ROOTBIN-BEGIN\n:\n# ROOTBIN-END|"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]
  exit $?
fi

BLOCK=$(awk '/^# ROOTBIN-BEGIN$/{f=1;next} /^# ROOTBIN-END$/{f=0} f{print}' "$INST")
NBEGIN=$(grep -c '^# ROOTBIN-BEGIN$' "$INST" || true)
OPTS=$(grep -m1 -E '^set -' "$INST")
IFSL=$(grep -m1 -E '^IFS=' "$INST")
echo "installer : $INST"
echo "options   : ${OPTS:-<none found>}   ${IFSL:-<no IFS line>}"
[ -z "$OPTS" ] && { echo "test-install-rootbin: CANNOT RUN - no set line in the installer"; exit 2; }
[ -z "$BLOCK" ] && { echo "test-install-rootbin: CANNOT RUN - no ROOTBIN block in the installer"; exit 2; }
echo "block     : $(printf '%s\n' "$BLOCK" | grep -c .) lines, $NBEGIN begin marker(s)"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
row() {   # name, ok(0/1), detail
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi
}

# the fixture: what the installer's `chown -R sdsys:sdusers` and `chmod -R 755` and the bootstrap leave in bin (pcode.old made by a root session, 664)
mkbin() {   # $1 = scratch system directory
  local d="$1/bin" f
  mkdir -p "$d"
  for f in sd sdlnxd sdidx sdfix sdconv sdtic sdclilib.so libsdcli.so pcode README; do printf 'x %s\n' "$f" > "$d/$f"; chmod 755 "$d/$f"; done
  printf 'old\n' > "$d/pcode.old"; chmod 664 "$d/pcode.old"
  printf 'h\n' > "$d/.hidden"; chmod 666 "$d/.hidden"
  chmod 775 "$d/libsdcli.so"
  chmod 775 "$d"
}

# run the block once on the scratch system directory $1; tables and logs are $1.owned $1.imm $1.calls; $2 = CHATTR_MODE, $3 = CHOWN_MISS
runblock() {
  local sd="$1"
  [ -e "$sd.owned" ] || : > "$sd.owned"
  [ -e "$sd.imm" ] || : > "$sd.imm"
  : > "$sd.calls"
  OPTS="$OPTS" IFSL="$IFSL" BLOCK="$BLOCK" SD="$sd" CHATTR_MODE="${2:-ok}" CHOWN_MISS="${3:-}" bash -c '
      eval "$OPTS"; eval "$IFSL"
      RED=""; NC=""
      OWNED="$SD.owned"; IMM="$SD.imm"; CALLS="$SD.calls"
      sudo() { "$@"; }
      chown() {
        local rec=0 p
        if [ "$1" = -R ]; then rec=1; shift; fi
        printf "chown %s %s%s\n" "$1" "$2" "$([ "$rec" = 1 ] && echo " (recursive)")" >> "$CALLS"
        if grep -Fxq -- "$2" "$IMM"; then echo "chown: changing ownership of $2: Operation not permitted" >&2; return 1; fi
        if [ "$1" = root:root ]; then
          { printf "%s\n" "$2"; if [ "$rec" = 1 ]; then command find "$2" -mindepth 1 -print; fi; } | while IFS= read -r p; do
            [ -n "$CHOWN_MISS" ] && [ "$p" = "$CHOWN_MISS" ] && continue
            printf "%s\n" "$p" >> "$OWNED"
          done
        fi
        return 0
      }
      chattr() {
        printf "chattr %s %s\n" "$1" "$2" >> "$CALLS"
        case "$CHATTR_MODE" in fail) return 1 ;; noflag) return 0 ;; esac
        case "$1" in
          +i) printf "%s\n" "$2" >> "$IMM" ;;
          -i) { grep -Fxv -- "$2" "$IMM" || true; } > "$IMM.t"; mv "$IMM.t" "$IMM" ;;
        esac
        return 0
      }
      lsattr() {
        [ "$1" = -d ] || return 2
        if grep -Fxq -- "$2" "$IMM"; then printf -- "----i---------e------- %s\n" "$2"; else printf -- "--------------e------- %s\n" "$2"; fi
      }
      stat() {
        local fmt p o
        [ "$1" = -c ] || { echo "stat stub: only -c is modelled" >&2; return 2; }
        fmt=$2; shift 2
        for p in "$@"; do
          [ -e "$p" ] || [ -L "$p" ] || { echo "stat: cannot statx $p: No such file or directory" >&2; return 1; }
          if grep -Fxq -- "$p" "$OWNED"; then o=root:root; else o=$(command stat -c "%U:%G" "$p"); fi
          case "$fmt" in
            "%U:%G %A %n") printf "%s %s %s\n" "$o" "$(command stat -c %A "$p")" "$p" ;;
            "%U:%G %a")    printf "%s %s\n" "$o" "$(command stat -c %a "$p")" ;;
            *) echo "stat stub: the format $fmt is not one the block uses" >&2; return 2 ;;
          esac
        done
      }
      sdsysdir="$SD"
      eval "$BLOCK"
      echo "SEALED=${rootbin_sealed:-unset}"
      echo REACHED-END' 2>&1 | tee "$sd.out"
}
reached() { case "$1" in *REACHED-END*) echo 0 ;; *) echo 1 ;; esac; }
okline() { case "$1" in *"$OKLINE"*) echo 0 ;; *) echo 1 ;; esac; }      # 0 when the success line is there
warned() { case "$1" in *"WARNING"*) echo 0 ;; *) echo 1 ;; esac; }      # 0 when a WARNING is there
gow() { find "$1" -perm /022 2>/dev/null | wc -l; }                       # entries with group or other write
snapshot() { find "$1" -mindepth 0 -printf '%p %m\n' 2>/dev/null | LC_ALL=C sort; }

# ---- R0, R1 a fresh tree ------------------------------------------------------------------------------------------------------------------------------------
R1="$T/fresh"; mkbin "$R1"
before_x=$(stat -c %a "$R1/bin/sd")
out=$(runblock "$R1")
row "R0 the block runs to its end under the installer's set and IFS" "$(reached "$out")" "$out"
[ "$(reached "$out")" = 0 ] || { echo "test-install-rootbin: CANNOT RUN - the block did not reach its end"; exit 2; }
ncho=$(grep -c '^chown ' "$R1.calls" || true)
okchown=1
[ "$ncho" = 1 ] && grep -qx "chown root:root $R1/bin (recursive)" "$R1.calls" && okchown=0
row "R1 exactly ONE chown, recursive, to root:root, on bin" "$okchown" "calls: $(tr '\n' ';' < "$R1.calls")"
row "R1 no entry of bin has group or other write afterwards (the directory, a hidden 666 file, a 775 library and the 664 pcode.old included): $(gow "$R1/bin") left" "$([ "$(gow "$R1/bin")" = 0 ] && echo 0 || echo 1)" "$(find "$R1/bin" -perm /022 | tr '\n' ' ')"
row "R1 the executables keep their execute bits (sd was $before_x, is $(stat -c %a "$R1/bin/sd"))" "$([ "$(stat -c %a "$R1/bin/sd")" = 755 ] && [ "$(stat -c %a "$R1/bin/sdlnxd")" = 755 ] && [ "$(stat -c %a "$R1/bin")" = 755 ] && echo 0 || echo 1)" "sd $(stat -c %a "$R1/bin/sd"), sdlnxd $(stat -c %a "$R1/bin/sdlnxd"), bin $(stat -c %a "$R1/bin")"
row "R1 the 664 pcode.old a root session made is 644 now" "$([ "$(stat -c %a "$R1/bin/pcode.old")" = 644 ] && echo 0 || echo 1)" "mode $(stat -c %a "$R1/bin/pcode.old")"
seq_ok=1
[ "$(grep '^chattr ' "$R1.calls" | tr '\n' ';')" = "chattr -i $R1/bin;chattr +i $R1/bin;" ] && seq_ok=0
row "R1 chattr -i then chattr +i, on bin and nothing else (so a re-run can chown)" "$seq_ok" "calls: $(grep '^chattr ' "$R1.calls" | tr '\n' ';')"
row "R1 bin is immutable in the table the stub keeps" "$(grep -Fxq "$R1/bin" "$R1.imm" && echo 0 || echo 1)" "table: $(tr '\n' ' ' < "$R1.imm")"
four=0
for f in sd sdlnxd sdidx pcode; do
  case "$out" in *"bin/$f root:root "*) ;; *) four=1 ;; esac
done
row "R1 the four root-run files are listed root:root, each with its mode (the printed line, read from what the stub's stat reports)" "$four" "$out"
row "R1 the success line is printed" "$(okline "$out")" "$out"
row "R1 and no WARNING" "$([ "$(warned "$out")" = 1 ] && echo 0 || echo 1)" "$out"

# ---- R2 a second run over the result ------------------------------------------------------------------------------------------------------------------------
out=$(runblock "$R1")
row "R2 a second run over a bin that is already immutable still seals it: success line, no WARNING (the stub chown refuses an immutable path)" "$([ "$(okline "$out")" = 0 ] && [ "$(warned "$out")" = 1 ] && echo 0 || echo 1)" "$out"
row "R2 and it lifted the attribute before the chown" "$([ "$(grep -v '^$' "$R1.calls" | head -1)" = "chattr -i $R1/bin" ] && echo 0 || echo 1)" "calls: $(tr '\n' ';' < "$R1.calls")"

# ---- R3 an optional file missing ----------------------------------------------------------------------------------------------------------------------------
R3="$T/optional"; mkbin "$R3"; rm -f "$R3/bin/sdfix" "$R3/bin/pcode.old"
out=$(runblock "$R3")
row "R3 sdfix and pcode.old missing (not root-run): sealed, success line, no WARNING" "$([ "$(okline "$out")" = 0 ] && [ "$(warned "$out")" = 1 ] && [ "$(gow "$R3/bin")" = 0 ] && echo 0 || echo 1)" "$out"

# ---- R3b each root-run file missing in turn -----------------------------------------------------------------------------------------------------------------
for f in sd sdlnxd sdidx pcode; do
  d="$T/miss-$f"; mkbin "$d"; rm -f "$d/bin/$f"
  out=$(runblock "$d")
  ok=1
  case "$out" in *"Missing from $d/bin: $f"*) [ "$(okline "$out")" = 1 ] && [ "$(warned "$out")" = 0 ] && [ "$(gow "$d/bin")" = 0 ] && ok=0 ;; esac
  row "R3b $f missing: the WARNING names it, no success line, the rest is still sealed (no group or other write: $(gow "$d/bin") left)" "$ok" "$out"
done

# ---- R4 a symlink in bin ------------------------------------------------------------------------------------------------------------------------------------
R4="$T/link"; mkbin "$R4"; rm -f "$R4/bin/sd"; ln -s "$R4/evil" "$R4/bin/sd"; : > "$R4/evil"
snap0=$(snapshot "$R4/bin")
out=$(runblock "$R4")
snap1=$(snapshot "$R4/bin")
nc=$(grep -c . "$R4.calls" || true)
row "R4 a symlink in bin: NOTHING was done (no chown, no chattr), and every mode is as it was" "$([ "$nc" = 0 ] && [ "$snap0" = "$snap1" ] && echo 0 || echo 1)" "calls: $(tr '\n' ';' < "$R4.calls")"
row "R4 a WARNING says NOT sealed and names the link; no success line" "$([ "$(warned "$out")" = 0 ] && [ "$(okline "$out")" = 1 ] && case "$out" in *"NOT sealed"*"$R4/bin/sd"*) echo 0 ;; *) echo 1 ;; esac)" "$out"

# ---- R5 bin itself a symlink ---------------------------------------------------------------------------------------------------------------------------------
R5="$T/binlink"; mkdir -p "$R5" "$T/elsewhere"; printf 'x\n' > "$T/elsewhere/sd"; chmod 666 "$T/elsewhere/sd"; ln -s "$T/elsewhere" "$R5/bin"
out=$(runblock "$R5")
row "R5 bin a symlink: nothing done, the target's mode untouched ($(stat -c %a "$T/elsewhere/sd")), a WARNING, no success line" "$([ "$(grep -c . "$R5.calls" || true)" = 0 ] && [ "$(stat -c %a "$T/elsewhere/sd")" = 666 ] && [ "$(warned "$out")" = 0 ] && [ "$(okline "$out")" = 1 ] && echo 0 || echo 1)" "$out"

# ---- R6 bin absent: the null case ---------------------------------------------------------------------------------------------------------------------------
R6="$T/absent"; mkdir -p "$R6"
out=$(runblock "$R6")
row "R6 no bin at all: nothing done, a WARNING, no success line, and the block still reached its end" "$([ "$(grep -c . "$R6.calls" || true)" = 0 ] && [ "$(warned "$out")" = 0 ] && [ "$(okline "$out")" = 1 ] && [ "$(reached "$out")" = 0 ] && echo 0 || echo 1)" "$out"

# ---- R7 chattr refused, R8 chattr says yes and no flag shows --------------------------------------------------------------------------------------------------
for mode in fail noflag; do
  d="$T/chattr-$mode"; mkbin "$d"
  out=$(runblock "$d" "$mode")
  ok=1
  if [ "$(okline "$out")" = 1 ] && [ "$(warned "$out")" = 0 ] && [ "$(gow "$d/bin")" = 0 ] && [ "$(grep -c '^chown ' "$d.calls" || true)" = 1 ]; then
    case "$out" in *"could not be made immutable"*"rename bin away"*) ok=0 ;; esac
  fi
  case $mode in fail) rid=R7 ;; *) rid=R8 ;; esac
  row "$rid chattr $mode: owner and mode are done, no success line, the WARNING says bin could not be made immutable and what that allows" "$ok" "$out"
done

# ---- R9 a chown that did not take on one file -----------------------------------------------------------------------------------------------------------------
R9="$T/missed"; mkbin "$R9"
out=$(runblock "$R9" ok "$R9/bin/sdidx")
ok=1
if [ "$(okline "$out")" = 1 ] && [ "$(warned "$out")" = 0 ]; then
  case "$out" in *"Not root's"*"$R9/bin/sdidx"*) ok=0 ;; esac
fi
row "R9 one file the chown did not reach (sdidx): named under 'Not root's', no success line" "$ok" "$out"

# ---- R10 the flag the closing summary reads (26 Oct 26, review of F11) ------------------------------------------------------------------------------------------
bad=""
for d in fresh optional; do grep -qx 'SEALED=1' "$T/$d.out" 2>/dev/null || bad="$bad $d"; done
row "R10 rootbin_sealed is 1 after the all-good runs (fresh, a second run, optional files missing)" "$([ -z "$bad" ] && echo 0 || echo 1)" "not 1 after:$bad"
bad=""
for d in miss-sd miss-sdlnxd miss-sdidx miss-pcode link binlink absent chattr-fail chattr-noflag missed; do grep -qx 'SEALED=0' "$T/$d.out" 2>/dev/null || bad="$bad $d"; done
row "R10 rootbin_sealed is 0 after every run that printed a WARNING (a missing file, a link, bin absent, chattr refused or ignored, a chown that missed): the closing summary repeats the warning" "$([ -z "$bad" ] && echo 0 || echo 1)" "not 0 after:$bad"

# ---- S1 static -----------------------------------------------------------------------------------------------------------------------------------------------
code=$(printf '%s\n' "$BLOCK" | grep -v -E '^\s*#' | grep -v -E '^\s*(echo|printf) ' || true)      # the commands, not the messages
bad=$(printf '%s\n' "$code" | grep -E 'chmod' | grep -v -E 'chmod -R go-w "\$rootbin"$' || true)
row "S1 the only chmod in the block is 'chmod -R go-w' on bin (nothing is given to the group or others)" "$([ -z "$bad" ] && printf '%s\n' "$code" | grep -q 'chmod -R go-w "\$rootbin"$' && echo 0 || echo 1)" "$bad"
bad=$(printf '%s\n' "$code" | grep -E 'chown' | grep -v -E 'chown -R root:root "\$rootbin"$' || true)
row "S1 the only chown in the block is -R to root:root on bin" "$([ -z "$bad" ] && printf '%s\n' "$code" | grep -q 'chown -R root:root "\$rootbin"$' && echo 0 || echo 1)" "$bad"
bad=$(printf '%s\n' "$code" | sed 's/\$sdsysdir//g' | grep -w -E 'sdsys|sdusers' || true)
row "S1 no command of the block names sdsys or sdusers (the messages may)" "$([ -z "$bad" ] && echo 0 || echo 1)" "$bad"
row "S1 exactly one ROOTBIN block in the installer" "$([ "$NBEGIN" = 1 ] && [ "$(grep -c '^# ROOTBIN-END$' "$INST" || true)" = 1 ] && echo 0 || echo 1)" "begin markers: $NBEGIN"

echo "test-install-rootbin: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-rootbin: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
