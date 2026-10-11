#!/bin/bash
#   installsdcore-dev.sh - install SD Core for Linux from the Dev branch.
#
#   FOR DEVELOPMENT ONLY.  NOT PART OF A RELEASE PACKAGE.  The shipped installer,
#   installsdcore.sh, clones main, which is the last release and must stay that
#   way (owner, 10 Oct 2026).  This one is the same script with its branch
#   changed to Dev, so a change pushed to Dev can be installed and tried.
#
#   Run it from the clone, as an ordinary user, exactly as installsdcore.sh:
#
#       /home/don/Projects/SDCore4Linux/installsdcore-dev.sh
#
#   It asks for sudo where installsdcore.sh does, because it IS installsdcore.sh.
#   Anything you give it is passed on.  It makes a private copy of
#   installsdcore.sh in the temporary directory, changes the one line
#   REPO_BRANCH="main"  to  REPO_BRANCH="Dev",  refuses unless that is the
#   only difference, runs the copy and deletes it.  The install records
#   branch=Dev in its stamp (/usr/local/sdsys/.sdcore-install).
#
#   An install tests what is on GitHub's Dev branch, not your working tree:
#   commit and push to Dev first.
#
#   installsdcore-dev.sh --check   prepares and checks the copy, shows the one
#                                  changed line, and stops.  Nothing is installed
#                                  and sudo is not used.
#
#   10 Oct 2026  Written, on the owner's ruling that work goes to Dev.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/installsdcore.sh"

die() { printf 'installsdcore-dev: %s\n' "$*" >&2; exit 2; }

[[ -f $src ]] || die "cannot find $src (this script goes with installsdcore.sh in the same directory)"

n=$(grep -c '^REPO_BRANCH="main"$' "$src" || true)
[[ $n -eq 1 ]] || die "expected exactly one REPO_BRANCH=\"main\" line in $src, found $n; installsdcore.sh changed shape and this script must be looked at"

tmp="$(mktemp "${TMPDIR:-/tmp}/installsdcore-dev.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

sed 's/^REPO_BRANCH="main"$/REPO_BRANCH="Dev"/' "$src" > "$tmp"

# The copy must differ from the original in that one line and nowhere else.
changed=$(diff "$src" "$tmp" | grep -c '^[<>]' || true)
[[ $changed -eq 2 ]] || die "the copy differs from installsdcore.sh in $changed lines, not 2; refusing"
grep -q '^REPO_BRANCH="Dev"$' "$tmp" || die "the copy does not carry REPO_BRANCH=\"Dev\"; refusing"
bash -n "$tmp" || die "the prepared copy does not parse; refusing"

echo
echo "================================================================"
echo " DEVELOPMENT INSTALLER - this installs the Dev branch of"
echo " github.com/dmontaine/SDCore4Linux, not the last release (main)."
echo "================================================================"
echo

if [[ ${1:-} == --check ]]; then
    echo "installsdcore-dev: --check, nothing installed."
    echo "installsdcore-dev: source   $src"
    echo "installsdcore-dev: the one changed line:"
    { diff "$src" "$tmp" || true; } | grep '^[<>]' | sed 's/^/    /'
    exit 0
fi

rc=0
bash "$tmp" "$@" || rc=$?
exit "$rc"
