#!/bin/bash
#
# mkrelease.sh - stage the release package and zip it (S.144 and S.23; owner, 3 Nov 2026: "for this version the source code will be included in the
# installer zip so that it does not need to be downloaded during install"; 15 Sep: "staging directory and then a zip").
#
#   bash sdb_ai/sd64/gplbld/mkrelease.sh L2.0-0 [--ref REF] [--docs-ref REF] [--readme FILE] [--clients DIR] [--force]
#
#   VERSION        the release, as named in the Changes document: L2.0-0
#   --ref REF      main or a v* tag of THIS repository (default: main).  Only what is committed
#                  there goes in; the working tree is not read.  Nothing is fetched, pushed, merged or tagged.
#   --docs-ref REF the same for the documentation repository (default: the same name as REF, which must exist there)
#   --readme FILE  README.txt for the package (the owner reads it before anything is distributed; this script does not write one)
#   --clients DIR  a folder copied to clients/Linux64 (libsdcli.so and sdclilib.so: built files, not in the repository)
#   --force        replace an existing staging folder and zip of this version
#   --allow-dev    build from a branch other than main or a v* tag (a TEST package for the VM install; never distribute it)
#   --label LABEL  names a release candidate: SDCore-L2.0-0-rc1.zip, from the tag v2.0-rc1 (the installer says "pre-release" when the tag ends -rcN; the version stamp is unchanged)
#
# MAKES, beside the repositories:  Project_Staging/SDCore-VERSION/  and  Project_Zips/SDCore-VERSION.zip
#
#   installsdcore.sh, deletesdcore.sh   from REF (the same bytes as source/)
#   source/                             `git archive REF` (what a clone of REF holds, without .git), source/docs/{User,Administrator}/markdown from the
#                                       documentation repository, and source/SDCORE-RELEASE (commit=, branch=, version=, docs_commit=)
#   SHA256SUMS                          one line for EVERY file under source/ and no other: the installer's PACKAGE-SOURCE block refuses a package whose
#                                       list and tree differ in either direction
#   sd-core-for-linux-lVERSION-changes.{pdf,html,md}   the Changes document, lower case (the installer's CHANGES-DOC block copies only that pattern)
#   pdf/                                the per-chapter PDFs of the three books, as user-NN-..., administrator-NN-..., gettingstarted-NN-... (the names
#                                       collide otherwise: all three books have 00a-copyright-and-licence.pdf; docs.install takes lower case, 80 characters)
#   README.txt, clients/Linux64/        only when given
#
# THEN it unpacks the zip into a scratch folder and checks it as the installer will: SHA256SUMS, the tree against the list, SDCORE-RELEASE against REF,
# bash -n on both scripts.  Exit 0 made and checked, 1 a check failed (the zip is removed), 2 it could not start.
#
# NOT DONE HERE, and said so: rebuilding the PDFs (S.23; the script only warns when a book's markdown is newer than its PDFs), reading the README, an
# install from the zip on a VM (test-install-package.sh runs the verification block; the VM covers the rest), the merge to main, the tag, the push.

set -euo pipefail

die()  { echo "mkrelease: $*" >&2; exit 2; }
fail() { echo "mkrelease: CHECK FAILED: $*" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PROJECTS="$(cd "$REPO/.." && pwd)"
DOCS="${DOCS_REPO:-$PROJECTS/SDCore4LinuxDocs}"
STAGING="${STAGING_DIR:-$PROJECTS/Project_Staging}"
ZIPS="${ZIPS_DIR:-$PROJECTS/Project_Zips}"

version=""; ref=""; docs_ref=""; readme=""; clients=""; force=0; allow_dev=0; label=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ref)      [ $# -ge 2 ] || die "--ref needs a value"; ref="$2"; shift 2 ;;
        --docs-ref) [ $# -ge 2 ] || die "--docs-ref needs a value"; docs_ref="$2"; shift 2 ;;
        --readme)   [ $# -ge 2 ] || die "--readme needs a value"; readme="$2"; shift 2 ;;
        --clients)  [ $# -ge 2 ] || die "--clients needs a value"; clients="$2"; shift 2 ;;
        --force)    force=1; shift ;;
        --allow-dev) allow_dev=1; shift ;;
        --label)    [ $# -ge 2 ] || die "--label needs a value"; label="$2"; shift 2 ;;
        -h|--help)  sed -n '3,36p' "$0"; exit 0 ;;
        -*)         die "unknown option $1" ;;
        *)          [ -z "$version" ] || die "one VERSION only"; version="$1"; shift ;;
    esac
done
[[ "$version" =~ ^L[0-9]+\.[0-9]+-[0-9]+$ ]] || die "VERSION looks like L2.0-0"
lcver=$(printf '%s' "$version" | tr 'L' 'l')      # lower case, as the installer's name pattern needs it
[[ -z "$label" || "$label" =~ ^[a-z0-9]{1,12}$ ]] || die "--label is lower case letters and digits, up to 12 (rc1)"
name="SDCore-$version${label:+-$label}"           # SDCore-L2.0-0-rc1: a release candidate is not mistaken for the release (the version stamp inside is the same)

git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || die "$REPO is not a git repository"
git -C "$DOCS" rev-parse --git-dir >/dev/null 2>&1 || die "no documentation repository at $DOCS (DOCS_REPO=...)"
[ -d "$STAGING" ] || die "no staging folder $STAGING"
[ -d "$ZIPS" ] || die "no zip folder $ZIPS"
for c in zip unzip sha256sum tar; do command -v "$c" >/dev/null || die "$c is not installed"; done

[ -n "$ref" ] || ref=main
[[ "$ref" =~ ^[A-Za-z0-9._-]{1,40}$ ]] || die "REF must be a plain branch or tag name (letters, digits . _ -, up to 40): the package records it as branch="
commit=$(git -C "$REPO" rev-parse --verify -q "${ref}^{commit}") || die "no such ref in $REPO: $ref"
# a release is made from main (after Dev is merged into it) or from its tag, never from Dev (owner, 3 Nov 2026); --allow-dev makes a TEST package, named so
case "$ref" in
    main|v[0-9]*) ;;
    *) [ "$allow_dev" -eq 1 ] || die "a release package is made from main or a v* tag, not from $ref (merge Dev into main on the owner's word first; --allow-dev makes a test package that must not be distributed)" ;;
esac
[ -n "$docs_ref" ] || docs_ref="$ref"
docs_commit=$(git -C "$DOCS" rev-parse --verify -q "${docs_ref}^{commit}") || die "no such ref in $DOCS: $docs_ref (--docs-ref)"
[ -z "$readme" ] || [ -f "$readme" ] || die "no README file $readme"
[ -z "$clients" ] || [ -d "$clients" ] || die "no clients folder $clients"

if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]; then
    echo "NOTE: $REPO has uncommitted changes to tracked files; they are NOT in the package (it is made from $ref, ${commit:0:12})."
fi

# nothing the installer refuses may go in: a link or a special file in source/ stops the install, and a name with a newline or backslash cannot be listed
if git -C "$REPO" ls-tree -r "$commit" | awk '$1!="100644" && $1!="100755" {bad=1} END{exit !bad}'; then
    fail "$ref holds a link or a submodule (the installer refuses anything in source/ that is not a plain file)"
fi
if git -C "$REPO" ls-tree -r --name-only -z "$commit" | tr '\0' '\n' | grep -q '[\\]'; then
    fail "$ref holds a file name with a backslash"
fi

stage="$STAGING/$name"
zipf="$ZIPS/$name.zip"
if [ -e "$stage" ] || [ -e "$zipf" ]; then
    [ "$force" -eq 1 ] || die "$stage or $zipf exists (--force replaces both)"
    rm -rf -- "$stage"; rm -f -- "$zipf"
fi
scratch=$(mktemp -d); trap 'rm -rf "$scratch"' EXIT
mkdir "$stage" "$stage/source" "$stage/source/docs" "$stage/pdf"

echo "Making $version from $ref ${commit:0:12} (documentation $docs_ref ${docs_commit:0:12})"
git -C "$REPO" archive "$commit" | tar -x -C "$stage/source"
git -C "$DOCS" archive "$docs_commit" User/markdown Administrator/markdown | tar -x -C "$stage/source/docs"
[ -d "$stage/source/sdb_ai/sd64" ] || fail "the archive has no sdb_ai/sd64"
for d in User Administrator; do
    ls "$stage/source/docs/$d/markdown"/*.md >/dev/null 2>&1 || fail "the documentation repository has no $d/markdown/*.md at $docs_ref"
done
printf 'commit=%s\nbranch=%s\nversion=%s\ndocs_commit=%s\nlabel=%s\n' "$commit" "$ref" "$version" "$docs_commit" "$label" > "$stage/source/SDCORE-RELEASE"

# the installers sit beside source/, the same bytes as in it
for f in installsdcore.sh deletesdcore.sh; do
    [ -f "$stage/source/$f" ] || fail "$ref has no $f"
    cp -p "$stage/source/$f" "$stage/$f"
done

# the Changes document, under the lower-case name the installer copies into the shared account
for ext in pdf html md; do
    case "$ext" in md) dir=markdown ;; *) dir=$ext ;; esac
    src=$(ls "$DOCS/Changes/$dir/"*"-changes-$version.$ext" 2>/dev/null | head -1 || true)
    [ -n "$src" ] || fail "no Changes/$dir/*-changes-$version.$ext in $DOCS (the Changes document must be built first)"
    cp -p "$src" "$stage/sd-core-for-linux-$lcver-changes.$ext"
done

# the per-chapter PDFs, with the book in the name
npdf=0
for book in "User:user" "Administrator:administrator" "GettingStarted:gettingstarted"; do
    dir=${book%%:*}; pre=${book##*:}
    ls "$DOCS/$dir/pdf/"*.pdf >/dev/null 2>&1 || fail "no PDFs in $DOCS/$dir/pdf (rebuild them: S.23)"
    if [ -n "$(find "$DOCS/$dir/markdown" -name '*.md' -newer "$(ls -t "$DOCS/$dir/pdf/"*.pdf | head -1)" 2>/dev/null | head -1)" ]; then
        echo "WARNING: some $dir markdown is newer than the newest $dir PDF - the PDFs may be stale (S.23 rebuilds them)."
    fi
    for p in "$DOCS/$dir/pdf/"*.pdf; do
        name=$(basename "$p" .pdf)
        [ "$name" != index ] || continue          # the set's index page is not a chapter
        if [ ! -f "$DOCS/$dir/markdown/$name.md" ]; then
            echo "NOTE: $dir/pdf/$name.pdf has no markdown page of that name (left over from an earlier build); not packaged."
            continue
        fi
        b="$pre-$(basename "$p")"
        [[ "$b" =~ ^[a-z0-9][a-z0-9._-]{0,79}$ ]] || fail "the PDF name $b is not one docs.install takes (lower case letters, digits . _ -, up to 80)"
        [ ! -e "$stage/pdf/$b" ] || fail "two PDFs are named $b"
        head -c5 "$p" | grep -q '^%PDF-' || fail "$p is not a PDF"
        cp -p "$p" "$stage/pdf/$b"
        npdf=$((npdf+1))
    done
done

[ -z "$readme" ]  || cp -p "$readme" "$stage/README.txt"
[ -z "$clients" ] || { mkdir -p "$stage/clients/Linux64"; cp -p "$clients"/* "$stage/clients/Linux64/"; }

# SHA256SUMS: every file under source/, nothing else, paths relative to the package folder
(cd "$stage" && find source -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS)

(cd "$STAGING" && zip -q -r -X "$zipf" "$name")

# CHECK THE ZIP AS THE INSTALLER WILL FIND IT
rm_zip() { rm -f -- "$zipf"; }
unzip -q "$zipf" -d "$scratch"
u="$scratch/$name"
[ -d "$u/source/sdb_ai/sd64" ] || { rm_zip; fail "the unpacked zip has no source/sdb_ai/sd64"; }
(cd "$u" && sha256sum --quiet --strict -c SHA256SUMS >/dev/null 2>&1) || { rm_zip; fail "SHA256SUMS does not match the unpacked zip"; }
[ "$(cd "$u" && find source -type f | wc -l)" = "$(grep -c '' "$u/SHA256SUMS")" ] || { rm_zip; fail "SHA256SUMS and source/ list different files"; }
[ -z "$(cd "$u" && find source ! -type f ! -type d | head -1)" ] || { rm_zip; fail "source/ holds something that is neither a file nor a directory"; }
[ "$(sed -n 's/^commit=//p' "$u/source/SDCORE-RELEASE")" = "$commit" ] || { rm_zip; fail "SDCORE-RELEASE does not name $commit"; }
for f in installsdcore.sh deletesdcore.sh; do
    bash -n "$u/$f" || { rm_zip; fail "bash -n $f"; }
    cmp -s "$u/$f" "$u/source/$f" || { rm_zip; fail "$f beside the package differs from source/$f"; }
done
[ "$(git -C "$REPO" show "$commit:installsdcore.sh" | sha256sum | cut -d' ' -f1)" = "$(sha256sum < "$u/installsdcore.sh" | cut -d' ' -f1)" ] || { rm_zip; fail "installsdcore.sh is not the one committed at $ref"; }
ls "$u"/sd-core-for-linux-"$lcver"-changes.* >/dev/null 2>&1 || { rm_zip; fail "the Changes files are missing from the zip"; }

nsrc=$(grep -c '' "$stage/SHA256SUMS")
echo
echo "Made $zipf"
echo "  source files $nsrc, per-chapter PDFs $npdf, commit $commit, branch $ref"
[ -n "$readme" ]  || echo "  NOT INCLUDED: README.txt (--readme FILE; the owner reads it before anything is distributed)"
[ -n "$clients" ] || echo "  NOT INCLUDED: clients/Linux64 (--clients DIR; libsdcli.so and sdclilib.so are built files, not in the repository)"
echo "  sha256 for the README:"
echo "    installsdcore.sh  $(sha256sum < "$stage/installsdcore.sh" | cut -d' ' -f1)"
echo "    deletesdcore.sh   $(sha256sum < "$stage/deletesdcore.sh" | cut -d' ' -f1)"
echo "    SHA256SUMS        $(sha256sum < "$stage/SHA256SUMS" | cut -d' ' -f1)"
echo "    $(basename "$zipf")  $(sha256sum < "$zipf" | cut -d' ' -f1)"
