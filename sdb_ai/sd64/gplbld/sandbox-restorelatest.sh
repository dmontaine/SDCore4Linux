#!/usr/bin/env bash
#
# sandbox-restorelatest.sh - RESTORE.ACCOUNT LATEST's real BASIC, run in a private SD built
#                            from this tree (sandbox-fromtree.py --s50).  No sudo, no install,
#                            never the live system.
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-restorelatest.sh
#
# Exit 0 every check passed, 1 one failed, 2 it could not run.
#
# WRITTEN 5 Oct 2026 for the owner's ruling that LATEST is the newest backup that actually
# HOLDS the account (a warning when a newer backup does not, a refusal when none does).
# test-restorelatest-units.py models the rule and reads the BASIC as text; "THE BASIC ITSELF
# HAS NOT BEEN RUN BY THAT GUARD".  This runs it: compiled by the sandbox's own bootstrap
# (216 programs, judged on the success wording), then driven through RESTORE.ACCOUNT LATEST.
#
# THE ZIPS ARE BUILT HERE, not made by BACKUP.ACCOUNT: the sandbox cannot back up a group
# account (no sdg_ groups) and the choice reads only a zip's NAME and MANIFEST.  They have
# the real layout - manifest.txt, accounts/<name>/ with one file, counts that agree with it -
# so the restore's own checks pass them.  Every scenario answers n, so nothing is restored;
# what is read is which zip was chosen, which message came before the question, and that no
# staging directory is left behind.
#
# EVERY ROW IS ANCHORED ON THE WORDING OF THE OUTCOME IT CLAIMS and refuses the wording of the
# outcomes it must not be (a row that expects a choice also refuses "No backup of").
set -u
export LC_ALL=C

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOL="$HERE/sandbox-fromtree.py"
HOST=$(hostname)
SBX=$(mktemp -d /tmp/sbx-latest.XXXXXX)
BAK="$SBX/bak"
PASS=0
FAIL=0

cleanup() {
    python3 "$TOOL" "$SBX" stop >/dev/null 2>&1
    rm -rf "$SBX"
}
trap cleanup EXIT

say() { printf '%s\n' "$*"; }
ck_says() {
    if printf '%s' "$3" | grep -qF -- "$2"; then PASS=$((PASS + 1)); say "  [PASS] $1: found \"$2\""
    else FAIL=$((FAIL + 1)); say "  [FAIL] $1: did NOT find \"$2\""; fi
}
ck_silent() {
    if printf '%s' "$3" | grep -qF -- "$2"; then FAIL=$((FAIL + 1)); say "  [FAIL] $1: found \"$2\" and must not have"
    else PASS=$((PASS + 1)); say "  [PASS] $1: \"$2\" absent, as required"; fi
}

[ -f "$TOOL" ] || { say "CANNOT RUN: $TOOL is missing"; exit 2; }
command -v python3 >/dev/null 2>&1 || { say "CANNOT RUN: python3 is missing"; exit 2; }
[ "$(id -u)" -ne 0 ] || { say "CANNOT RUN: do not run this as root"; exit 2; }

say "sandbox-restorelatest: building a private SD from $HERE/.. in $SBX"
if ! python3 "$TOOL" "$SBX" all --s50 > "$SBX.build.log" 2>&1; then
    say "CANNOT RUN: the sandbox did not bootstrap; the end of its log:"; tail -15 "$SBX.build.log"; rm -f "$SBX.build.log"; exit 2
fi
for want in "pass 1 (sd -i)" "pass 2 (SECOND.COMPILE) Compiled" "THIRD.COMPILE"; do
    grep -qF -- "[PASS] $want" "$SBX.build.log" || { say "CANNOT RUN: the bootstrap verdict '$want' is not PASS:"; grep -F '[' "$SBX.build.log" | tail -8; rm -f "$SBX.build.log"; exit 2; }
done
say "  bootstrap: $(grep -F '[PASS] pass 2' "$SBX.build.log" | sed 's/^ *//')"
rm -f "$SBX.build.log"
python3 "$TOOL" "$SBX" start >/dev/null 2>&1

# One session; the answer lines follow the verb that asks.  Output is what sd printed after the TERM line.
S() { python3 "$TOOL" "$SBX" sess "$SBX/user_accounts" "$@" 2>&1 | sed -e '1,/^:TERM 200,9999/d'; }

mk() {   # mk STAMP WHAT account...
    local stamp=$1 what=$2; shift 2
    python3 - "$BAK/SD-$HOST-$what-$stamp.zip" "$HOST" "$@" <<'PY'
import sys, zipfile
path, host, accts = sys.argv[1], sys.argv[2], sys.argv[3:]
man = ["format: 1", "product: linux-full", "sd.version: L1.1-3", "created: 2026-01-01T00:00:00", "host: " + host,
       "source.root: /home/sd", "accounts: %d" % len(accts), ""]
for a in accts:
    man += ["[account %s]" % a, "type: USER", "os.user: %s" % a, "os.group: sdu_%s" % a, "route.ssh: 1", "route.api: 1",
            "description: ", "suspended: 0", "source.path: /home/sd/user_accounts/%s" % a, "files: 1", "bytes: 1", "dirs: 0", ""]
with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.txt", "\n".join(man) + "\n")
    for a in accts:
        z.writestr("accounts/%s/" % a, b"")
        z.writestr("accounts/%s/f" % a, b"x")
PY
}

Z() { printf '%s/SD-%s-%s.zip' "$BAK" "$HOST" "$1"; }          # a zip's full path from "what-stamp"
NEWER="The most recent backup made on this computer, SD-$HOST-"   # 13049's opening
mkdir -p "$BAK"

OUT=$(S "SET.BACKUP.DIRECTORY $BAK")
ck_says "setup: the backup directory is saved" "Backup directory is now $BAK" "$OUT"

say ""; say "A  gaa (oldest), gab (newer)"
mk 20260101-000001 gaa gaa; mk 20260101-000002 gab gab
OUT=$(S "RESTORE.ACCOUNT LATEST gaa" "n")
ck_says "A1 a newer backup (gab's) lacks gaa: 13049 names it" "${NEWER}gab-20260101-000002.zip, does not hold gaa (or cannot be read)" "$OUT"
ck_says "A1 and the zip that holds gaa is chosen" "The newest backup that does is $(Z gaa-20260101-000001)" "$OUT"
ck_says "A1 it asks, and n abandons" "Restore abandoned. Nothing was changed." "$OUT"
ck_silent "A1 no refusal" "No backup of" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST gab" "n")
ck_says "A2 the newest backup holds gab: 13048" "The most recent backup is $(Z gab-20260101-000002)" "$OUT"
ck_silent "A2 and no warning" "does not hold" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST nosuch")
ck_says "A3 nothing holds nosuch: 13047" "No backup of nosuch made on this computer was found in $BAK." "$OUT"
ck_silent "A3 it did not ask" "Restore these accounts" "$OUT"

say ""; say "B  an ALL zip (gaa gab gac), newest"
mk 20260101-000003 all gaa gab gac
OUT=$(S "RESTORE.ACCOUNT LATEST gaa" "n")
ck_says "B1 the ALL zip is newest and holds gaa: 13048" "The most recent backup is $(Z all-20260101-000003)" "$OUT"
ck_silent "B1 no warning" "does not hold" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST gac" "n")
ck_says "B2 gac is only in the ALL zip: 13048" "The most recent backup is $(Z all-20260101-000003)" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST nosuch")
ck_says "B3 an ALL zip's NAME admits nosuch but its manifest does not: 13047 (it used to be 13014 after the choice)" "No backup of nosuch made on this computer was found in $BAK." "$OUT"
ck_silent "B3 not the old refusal" "is not in this backup" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST ALL" "n")
ck_says "B4 LATEST ALL: the ALL zip (13048)" "The most recent backup is $(Z all-20260101-000003)" "$OUT"

say ""; say "C  a newer ALL zip made after gac was deleted (gaa gab)"
mk 20260101-000004 all gaa gab
OUT=$(S "RESTORE.ACCOUNT LATEST gac" "n")
ck_says "C1 gac: the older ALL zip is used, and the newer one is named in the warning" "${NEWER}all-20260101-000004.zip, does not hold gac" "$OUT"
ck_says "C1 the older ALL zip is the choice" "The newest backup that does is $(Z all-20260101-000003)" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST gaa gab" "n")
ck_says "C2 gaa and gab: the newest ALL zip, 13048" "The most recent backup is $(Z all-20260101-000004)" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST gaa gac" "n")
ck_says "C3 gaa and gac: only the older ALL zip holds both" "The newest backup that does is $(Z all-20260101-000003)" "$OUT"

say ""; say "D  a corrupt zip named for gaa, newer than everything"
printf 'this is not a zip' > "$BAK/SD-$HOST-gaa-20260101-000005.zip"
OUT=$(S "RESTORE.ACCOUNT LATEST gaa" "n")
ck_says "D1 the unreadable newest is named in the warning" "${NEWER}gaa-20260101-000005.zip, does not hold gaa (or cannot be read)" "$OUT"
ck_says "D1 and skipped: the newest ALL zip that holds gaa is used" "The newest backup that does is $(Z all-20260101-000004)" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST ALL" "n")
ck_says "D2 LATEST ALL ignores it, no warning" "The most recent backup is $(Z all-20260101-000004)" "$OUT"
ck_silent "D2 no warning" "does not hold" "$OUT"

say ""; say "E  an <n>accounts zip, newer; and another computer's zip, newest of all"
mk 20260101-000006 2accounts gab gad
python3 - "$BAK/SD-otherhost-gaa-20260101-000007.zip" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w") as z: z.writestr("manifest.txt", "format: 1\n")
PY
OUT=$(S "RESTORE.ACCOUNT LATEST gad" "n")
ck_says "E1 the 2accounts zip holds gad: 13048" "The most recent backup is $(Z 2accounts-20260101-000006)" "$OUT"
OUT=$(S "RESTORE.ACCOUNT LATEST gaa" "n")
ck_says "E2 the 2accounts zip is the newest made HERE and lacks gaa; the other computer's zip is not the one named" "${NEWER}2accounts-20260101-000006.zip, does not hold gaa" "$OUT"
ck_says "E2 the chosen zip is the newest readable one that holds gaa" "The newest backup that does is $(Z all-20260101-000004)" "$OUT"
ck_silent "E2 the other computer's zip is never named" "otherhost" "$OUT"

say ""; say "F  answering y goes on to restore from the chosen zip"
OUT=$(S "RESTORE.ACCOUNT LATEST gad" "y")
ck_says "F1 it announces the zip" "The most recent backup is $(Z 2accounts-20260101-000006)" "$OUT"
ck_says "F1 it asks, and y goes on (the sandbox only pretends the Linux user, then asks for a password)" "sd-elevate (sandbox): checked, pretended: useradd gad" "$OUT"

say ""; say "G  nothing holds it"
rm -f "$BAK"/*.zip; mk 20260101-000009 gab gab
OUT=$(S "RESTORE.ACCOUNT LATEST gaa")
ck_says "G1 only gab's backup: 13047" "No backup of gaa made on this computer was found in $BAK." "$OUT"
rm -f "$BAK"/*.zip
OUT=$(S "RESTORE.ACCOUNT LATEST ALL")
ck_says "G2 no backup at all: 13047 for ALL" "No backup of ALL made on this computer was found in $BAK." "$OUT"

say ""
LEFT=$(ls -d "$SBX"/.sdrestore.* 2>/dev/null | wc -l)
if [ "$LEFT" -eq 0 ]; then PASS=$((PASS + 1)); say "  [PASS] no restore staging directory is left behind"
else FAIL=$((FAIL + 1)); say "  [FAIL] $LEFT restore staging directory(ies) left in $SBX"; fi

say ""
say "sandbox-restorelatest: $PASS passed, $FAIL failed"
if [ "$((PASS + FAIL))" -eq 0 ]; then say "VOID - no check ran."; exit 2; fi
[ "$FAIL" -eq 0 ] && exit 0
exit 1
