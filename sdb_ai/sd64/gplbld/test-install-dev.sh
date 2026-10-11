#!/bin/bash
# test-install-dev.sh - the development installer (installsdcore-dev.sh) changes the
#                       installer's branch to Dev and nothing else, and refuses otherwise.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-dev.sh
#
# Free check: no sudo, no network, installs nothing.  Uses --check, which prepares and
# verifies the copy and stops.  Exit 0 every row passed, 1 a row failed.
#
# START-HISTORY:
# 10 Oct 26 dm  Written with installsdcore-dev.sh.
# END-HISTORY
#
# Each refusal row is run against a COPY of installsdcore.sh that has been damaged in one
# way, so the guard is shown to refuse - not assumed to.  The control runs the real file.

set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
dev="$root/installsdcore-dev.sh"
inst="$root/installsdcore.sh"
pass=0; fail=0
row() { if [[ $2 == ok ]]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi; }

[[ -f $dev && -f $inst ]] || { echo "test-install-dev: CANNOT RUN - $dev or $inst missing"; exit 2; }
echo "test-install-dev: $dev against $inst"

work="$(mktemp -d "${TMPDIR:-/tmp}/test-install-dev.XXXXXX")"
trap 'rm -rf "$work"' EXIT

# 1. the real pair
out=$(bash "$dev" --check 2>&1); rc=$?
[[ $rc -eq 0 ]] && row "the real pair passes --check" ok || row "the real pair passes --check" bad "exit $rc: $out"
grep -q '^    < REPO_BRANCH="main"$' <<<"$out" && grep -q '^    > REPO_BRANCH="Dev"$' <<<"$out" \
    && row "--check shows main -> Dev as the one change" ok || row "--check shows main -> Dev as the one change" bad "$out"
grep -q 'DEVELOPMENT INSTALLER' <<<"$out" && row "it announces itself as the development installer" ok \
    || row "it announces itself as the development installer" bad "no banner"

# 2. refusals, each against a damaged copy beside a copy of the dev script
try() {  # name, sed-or-append action, label
    local d="$work/$1"; mkdir -p "$d"; cp "$dev" "$d/installsdcore-dev.sh"
    case "$1" in
        absent)    sed 's/^REPO_BRANCH="main"$/REPO_BRANCH="release"/' "$inst" > "$d/installsdcore.sh" ;;
        twice)     { cat "$inst"; echo 'REPO_BRANCH="main"'; } > "$d/installsdcore.sh" ;;
        noinst)    : ;;
        nonparse)  { cat "$inst"; echo 'if then fi ('; } > "$d/installsdcore.sh" ;;
    esac
    local o; o=$(bash "$d/installsdcore-dev.sh" --check 2>&1); local r=$?
    if [[ $r -eq 2 ]] && ! grep -q 'nothing installed' <<<"$o"; then row "$3: refused with exit 2" ok
    else row "$3: refused with exit 2" bad "exit $r: ${o:0:200}"; fi
}
try absent   x "installsdcore.sh with no REPO_BRANCH=\"main\" line"
try twice    x "installsdcore.sh with the line twice"
try noinst   x "no installsdcore.sh beside it"
try nonparse x "installsdcore.sh with a syntax error appended (the prepared copy would not parse)"

# 3. the temporary copy is gone afterwards
left=$(ls "${TMPDIR:-/tmp}" 2>/dev/null | grep -c '^installsdcore-dev\.' || true)
[[ $left -eq 0 ]] && row "no installsdcore-dev.* copy left in the temporary directory" ok || row "no copy left in the temporary directory" bad "$left left"

echo "test-install-dev: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
