#!/usr/bin/env bash
#
# witness-agentpack.sh - what only a REAL install shows about the AI guide and knowledge pack that installsdcore.sh puts in
#                        /usr/local/sdsys/agent-pack (S.69 rows 1 and 1b, installer change of 20 Oct 2026).
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/witness-agentpack.sh [<repository's sdb_ai/sd64>]
#
# NO sudo, AND NOT AS A CONVENIENCE.  It must run as an ordinary login that is a member of sdusers: as root every write
# would succeed or fail for the wrong reason, and as a non-member the refusal would come from the "other" bits, a weaker claim
# wearing the same word (verify-sysperms.py refuses both callers for the same reason, and so does this).  It changes nothing: it
# reads, and it TRIES one write that must be refused.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  The log is
# /var/tmp/witness-agentpack-<time>.log.
#
# PREREQUISITE: the product installed by installsdcore.sh from a tree that has the agent pack (the installer of 20 Oct 2026 or
# later).  An install made before that has no /usr/local/sdsys/agent-pack, and this FAILS on it, which is its first row working.
# To witness an unreleased tree use installsdcore-dev.sh (it clones Dev; test-install-dev.sh guards it) on a VM or the QEMU guest.
#
# NOT RUN when this was written: there was no install made by the new installer on the machine it was written on.  Written from
# the installer block and gplbld/test-install-agentpack.sh, which does run (free, on scratch files).
#
# WHAT IT ASKS.  1 the files are there; 2 only guide/ and pack/ are (no skill, templates, recipe, generator); 3 the manifest's
# rev_stamp is the installed revstamp.h's; 4 owner sdsys, group sdusers, files 644, directories 755; 5 nothing in it is writable
# by group or other, and an actual write by this login is refused (the decisive row, not the mode bits); 6 when the repository
# tree is given and the install was made from its HEAD, the installed copy equals the repository's; 7 verify-sysperms.py passes.

set -u
SYSD=/usr/local/sdsys
AP="$SYSD/agent-pack"
SRC="${1:-}"
STAMP=$(date +%Y%m%dT%H%M%S)
LOG=/var/tmp/witness-agentpack-$STAMP.log
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PASS=0; FAIL=0
exec > >(tee "$LOG") 2>&1
say() { printf '%s\n' "$*"; }
pass() { PASS=$((PASS+1)); say "  PASS  $1"; }
fail() { FAIL=$((FAIL+1)); say "  FAIL  $1"; }
need() { say "CANNOT RUN: $1"; exit 2; }

[ "$(id -u)" -ne 0 ] || need "run as an ordinary login, not root (every write would succeed, or fail for the wrong reason)"
id -nG | tr ' ' '\n' | grep -qx sdusers || need "this login ($(id -un)) is not in sdusers; its refusals would come from the 'other' bits, a weaker claim"
[ -x "$SYSD/bin/sd" ] || need "no installed SD at $SYSD"
say "witness-agentpack: caller $(id -un), groups: $(id -nG)"
say "witness-agentpack: install $SYSD, stamp file $(cat "$SYSD/.sdcore-install" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"

# 1
for f in guide/sd-basic-guide.md pack/manifest.json pack/core.md pack/index.json pack/reference/tcl-verbs.md pack/reference/messages.md; do
  if [ -s "$AP/$f" ]; then pass "1 $f is there and not empty ($(stat -c '%U:%G %a %s bytes' "$AP/$f"))"; else fail "1 $f is missing or empty under $AP"; fi
done
# 2
if [ -d "$AP" ]; then
  got=$(ls "$AP" | tr '\n' ' ')
  [ "$got" = "guide pack " ] && pass "2 agent-pack holds exactly: $got" || fail "2 agent-pack holds '$got' (wanted 'guide pack ')"
else
  fail "2 there is no $AP at all (an install made before the agent pack, or the installer skipped it: read its output for the Note: line)"
fi
# 3
pst=$(sed -n '/"rev_stamp"/{s/^[^:]*: *"\([^"]*\)".*/\1/p;q}' "$AP/pack/manifest.json" 2>/dev/null)
ist=$(sed -n '/^\$define SD\.REV\.STAMP/{s/^[^"]*"\([^"]*\)".*/\1/p;q}' "$SYSD/gpl.bp/revstamp.h" 2>/dev/null)
if [ -n "$pst" ] && [ "$pst" = "$ist" ]; then pass "3 the manifest's rev_stamp '$pst' is the installed revstamp.h's"; else fail "3 manifest rev_stamp '${pst:-?}' vs installed '${ist:-?}'"; fi
# 4
if [ -d "$AP" ]; then
  bad_owner=$(find "$AP" ! -user sdsys -o ! -group sdusers | head -3 | tr '\n' ' ')
  bad_file=$(find "$AP" -type f ! -perm 644 | head -3 | tr '\n' ' ')
  bad_dir=$(find "$AP" -type d ! -perm 755 | head -3 | tr '\n' ' ')
  [ -z "$bad_owner" ] && pass "4 everything is owned sdsys:sdusers" || fail "4 not sdsys:sdusers: $bad_owner"
  [ -z "$bad_file" ] && pass "4b every file is 644" || fail "4b not 644: $bad_file"
  [ -z "$bad_dir" ] && pass "4c every directory is 755" || fail "4c not 755: $bad_dir"
  # 5
  wr=$(find "$AP" -perm /022 | head -3 | tr '\n' ' ')
  [ -z "$wr" ] && pass "5 nothing is writable by group or other" || fail "5 writable by group or other: $wr"
  tgt="$AP/guide/sd-basic-guide.md"
  before=$(sha256sum "$tgt" 2>/dev/null | cut -d' ' -f1)
  if ( : >> "$tgt" ) 2>/dev/null; then
    fail "5b a WRITE to the guide by $(id -un) (an sdusers member) SUCCEEDED - any SD user could plant text for another user's agent"
  else
    after=$(sha256sum "$tgt" 2>/dev/null | cut -d' ' -f1)
    [ -n "$before" ] && [ "$before" = "$after" ] && pass "5b a write to the guide by $(id -un) was refused and the file is unchanged ($before)" || fail "5b the write was refused but the file's digest changed or could not be read"
  fi
fi
# 6
if [ -n "$SRC" ]; then
  [ -d "$SRC/agent-pack/pack" ] || need "$SRC has no agent-pack/pack"
  ic=$(sed -n 's/^commit=//p' "$SYSD/.sdcore-install" 2>/dev/null)
  hc=$(git -C "$SRC" rev-parse HEAD 2>/dev/null)
  if [ -n "$ic" ] && [ "$ic" = "$hc" ]; then
    if diff -r "$SRC/agent-pack/pack" "$AP/pack" > /dev/null 2>&1 && diff -r "$SRC/agent-pack/guide" "$AP/guide" > /dev/null 2>&1; then
      pass "6 the installed guide and pack equal the repository's at the commit the install was made from ($ic)"
    else
      fail "6 the installed copy differs from the repository's at $ic"
    fi
  else
    say "  (6 skipped: the install is from commit '${ic:-?}' and the repository is at '${hc:-?}', so equality is not the question)"
  fi
else
  say "  (6 skipped: no repository tree given as an argument)"
fi
# 7
vs="$HERE/verify-sysperms.py"
if [ -f "$vs" ]; then
  out=$(python3 "$vs" 2>&1); rc=$?
  say "      verify-sysperms.py exit $rc: $(printf '%s' "$out" | tail -2 | tr '\n' ' ' | cut -c1-200)"
  [ "$rc" -eq 0 ] && pass "7 verify-sysperms.py passes on this install (its read-only set is derived, so agent-pack is covered)" || fail "7 verify-sysperms.py exit $rc"
else
  say "  (7 skipped: no verify-sysperms.py beside this script)"
fi

say "witness-agentpack: $PASS passed, $FAIL failed (log: $LOG)"
[ "$((PASS + FAIL))" -eq 0 ] && { say "witness-agentpack: NOTHING RAN"; exit 2; }
[ "$FAIL" -eq 0 ]
