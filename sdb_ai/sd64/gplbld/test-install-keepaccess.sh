#!/bin/bash
#
# test-install-keepaccess.sh - an upgrade keeps access from other computers as it was (owner, 14 Nov 2026: "those questions should not be asked during an
# upgrade if the config file has been saved.  If closed they stay closed, if open they stay open").  Three blocks:
#   installsdcore.sh ACCESS-ASK  the two questions, skipped when /home/sd/sd.conf (the saved configuration) is there
#   installsdcore.sh API-KEEP    the API opened again from the uninstaller's note /home/sd/api-access.saved
#   deletesdcore.sh  API-SAVE    the note written when the configuration is kept and the API listens for other computers; REMOTE.API's drop-in
#                                removed when the configuration is deleted
#
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-keepaccess.sh
#   bash /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-keepaccess.sh --selftest
#   INSTALLER=<copy> DELETER=<copy> bash .../test-install-keepaccess.sh      (what --selftest uses)
#
# FREE CHECK: no install, no sudo (a function), no systemd (systemctl a stub printing a given Listen).  /home/sd/ and /etc/systemd/system/ in a block
# become scratch directories; each block runs under its script's own set and IFS lines.
#
#   A1  no saved sd.conf: both questions asked; only y or yes turns each on
#   A2  a saved sd.conf: neither asked, keep_access=y, allow_ssh and allow_api stay n, and it says access is kept
#   K1  keep_access with a root-owned plain note saying open: allow_api=y and it says so; the note is gone
#   K2  a note not root's, a link, another word, or keep_access=n: allow_api unchanged; the note is gone either way
#   D1  configuration kept, the API listening on 0.0.0.0:4247 (or [::]:4247): the note says open, mode 600
#   D2  configuration kept, the API on 127.0.0.1 only: no note; a stale note is removed
#   D3  configuration deleted: no note, and REMOTE.API's drop-in is removed (with its directory when empty)
#   W   order: ACCESS-ASK before the first sudo of the installer; API-KEEP before the API bind block and before sd.conf is restored;
#       API-SAVE after the configuration question and before the firewall rule is removed
# ANCHORED ON THE VARIABLES the blocks set and the files on disk.

HERE="$(cd "$(dirname "$0")" && pwd)"
THIS="$HERE/$(basename "$0")"
TREE="$(cd "$HERE/../../.." && pwd)"
INST="${INSTALLER:-$TREE/installsdcore.sh}"
DEL="${DELETER:-$TREE/deletesdcore.sh}"

if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  caught=0; missed=0; total=0
  mut() {   # name, which (inst|del), sed expression
    local f="$T/$1.sh" src; [ "$2" = inst ] && src="$TREE/installsdcore.sh" || src="$TREE/deletesdcore.sh"
    total=$((total+1)); sed -e "$3" "$src" > "$f"
    if cmp -s "$src" "$f"; then echo "  [MISSED] $1: the mutation changed nothing"; missed=$((missed+1)); return; fi
    if [ "$2" = inst ]; then INSTALLER="$f" bash "$THIS" > "$T/$1.out" 2>&1; else DELETER="$f" bash "$THIS" > "$T/$1.out" 2>&1; fi
    if [ $? -ne 0 ]; then echo "  [caught] $1"; caught=$((caught+1)); else echo "  [MISSED] $1: the check still passed"; missed=$((missed+1)); fi
  }
  echo "selftest: the real scripts first (must pass), then mutants (each must not)"
  bash "$THIS" > "$T/real.out" 2>&1 || { echo "  [FAIL] the real scripts do not pass:"; tail -8 "$T/real.out"; exit 1; }
  echo "  [ok] the real scripts pass"
  A='/^# ACCESS-ASK-BEGIN/,/^# ACCESS-ASK-END/'; K='/^# API-KEEP-BEGIN/,/^# API-KEEP-END/'; S='/^# API-SAVE-BEGIN/,/^# API-SAVE-END/'
  mut asked-on-upgrade     inst "$A s/^if \[ -f \/home\/sd\/sd.conf \]; then$/if false; then/"
  mut upgrade-opens-ssh    inst "$A s/^    keep_access=y$/    keep_access=y; allow_ssh=y/"
  mut any-answer-opens     inst "$A s/case \$yn_api in \[yY\]|\[yY\]\[eE\]\[sS\] )/case \$yn_api in *)/"
  mut note-without-keep    inst "$K s/^if \[ \"\$keep_access\" = y \] \&\& /if /"
  mut note-any-owner       inst "$K s/\" = 0 \] \\\\$/\" ] \\\\/"
  mut note-any-word        inst "$K s/ = open \]; then$/ != x ]; then/"
  mut note-kept            inst "$K{/^sudo rm -f \/home\/sd\/api-access.saved$/d}"
  mut keep-after-bind      inst "/^# API-KEEP-BEGIN/,/^# API-KEEP-END/d"
  mut save-when-deleted    del  "$S s/^if \[ \"\$conf_deleted\" = no \]; then$/if true; then/"
  mut save-any-listen      del  "$S s/        \*\" 0.0.0.0:4247 \"\*|\*\" \[::\]:4247 \"\*|\*\" \*:4247 \"\*)/        *)/"
  mut save-world-readable  del  "$S s/chmod 600/chmod 644/"
  mut stale-note-kept      del  "$S{/^sudo rm -f \"\$acct_path\/api-access.saved\"$/d}"
  mut dropin-kept          del  "$S{/sd-remote-api.conf$/{/rm -f/d}}"
  mut save-after-firewall  del  "/^# API-SAVE-BEGIN/,/^# API-SAVE-END/d"
  echo "selftest: $caught of $total mutants caught, $missed missed"
  [ "$missed" -eq 0 ]; exit $?
fi

cut_block() { awk -v b="# $2-BEGIN" -v e="# $2-END" '$0 == b {f=1; next} $0 == e {f=0} f {print}' "$1"; }
ASK=$(cut_block "$INST" ACCESS-ASK); KEEP=$(cut_block "$INST" API-KEEP); SAVE=$(cut_block "$DEL" API-SAVE)
IOPTS=$(grep -E '^(set -|IFS=)' "$INST" | head -2); DOPTS=$(grep -E '^(set -|IFS=)' "$DEL" | head -2)
echo "installer : $INST"; echo "deleter   : $DEL"
for b in ASK KEEP SAVE; do [ -z "${!b}" ] && { echo "test-install-keepaccess: CANNOT RUN - no $b block"; exit 2; }; done
[ -z "$IOPTS" ] || [ -z "$DOPTS" ] && { echo "test-install-keepaccess: CANNOT RUN - no set line"; exit 2; }

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
H="$T/home"; E="$T/etc"; mkdir -p "$H" "$E/sdclient.socket.d"
pass=0; fail=0
row() { if [ "$2" -eq 0 ]; then pass=$((pass+1)); echo "  [PASS] $1"; else fail=$((fail+1)); echo "  [FAIL] $1   <- $3"; fi; }
sub() { local b="${1//\/home\/sd\//$H/}"; b="${b//\/etc\/systemd\/system\//$E/}"; printf '%s' "$b"; }

run_ask() {   # input
  printf '%s' "$1" | OPTS="$IOPTS" BLK="$(sub "$ASK")" bash -c '
      eval "$OPTS"; YELLOW=""; NC=""; sd_api_port=4247
      read() { [ "${2:-}" = -p ] && echo "PROMPT: $3"; builtin read "$@"; }
      eval "$BLK"; echo "KEEP=$keep_access SSH=$allow_ssh API=$allow_api"' 2>&1
}
run_keep() {   # keep owner
  OPTS="$IOPTS" BLK="$(sub "$KEEP")" KA="$1" OWN="$2" bash -c '
      eval "$OPTS"; keep_access=$KA; allow_api=n
      sudo() { if [ "$1" = stat ]; then echo "$OWN"; else "$@"; fi; }
      eval "$BLK"; echo "API=$allow_api"' 2>&1
}
run_save() {   # conf_deleted listen
  OPTS="$DOPTS" BLK="$(sub "$SAVE")" CD="$1" LISTEN="$2" AP="$H" bash -c '
      eval "$OPTS"; conf_deleted=$CD; acct_path=$AP
      sudo() { "$@"; }
      systemctl() { printf "%s\n" "$LISTEN"; }
      eval "$BLK"; echo REACHED-END' 2>&1
}

# A1 / A2
rm -f "$H/sd.conf"; bad=""
o=$(run_ask "y"$'\n'"y"$'\n'); [[ "$o" == *"KEEP=n SSH=y API=y"* ]] || bad="$bad yy"
o=$(run_ask $'\n'$'\n'); [[ "$o" == *"KEEP=n SSH=n API=n"* ]] || bad="$bad enter"
o=$(run_ask "n"$'\n'"yes"$'\n'); [[ "$o" == *"KEEP=n SSH=n API=y"* ]] || bad="$bad n-yes"
o=$(run_ask ""); [[ "$o" == *"KEEP=n SSH=n API=n"* ]] || bad="$bad ended"
np=$(printf '%s' "$(run_ask $'\n'$'\n')" | grep -c '^PROMPT: Allow ')
row "A1 no saved configuration: both asked, only y or yes turns each on" "$([ -z "$bad" ] && [ "$np" = 2 ] && echo 0 || echo 1)" "wrong for:$bad prompts=$np"
: > "$H/sd.conf"; o=$(run_ask "y"$'\n'"y"$'\n')
row "A2 a saved configuration: nothing asked, access kept, ssh and the API not switched on" \
    "$([[ "$o" == *"KEEP=y SSH=n API=n"* && "$o" == *"kept as it was"* && "$o" != *PROMPT:* ]] && echo 0 || echo 1)" "$o"
rm -f "$H/sd.conf"

# K1 / K2
N="$H/api-access.saved"
echo open > "$N"; o=$(run_keep y 0)
row "K1 keep + a root-owned note saying open: allow_api=y, said, note gone" "$([[ "$o" == *"API=y"* && "$o" == *"kept open"* ]] && [ ! -e "$N" ] && echo 0 || echo 1)" "$o"
bad=""
echo open > "$N"; o=$(run_keep y 1000); { [[ "$o" == *"API=n"* ]] && [ ! -e "$N" ]; } || bad="$bad not-root"
rm -f "$N" "$T/tgt"; echo open > "$T/tgt"; ln -s "$T/tgt" "$N"; o=$(run_keep y 0); { [[ "$o" == *"API=n"* ]] && [ ! -L "$N" ]; } || bad="$bad link"
echo opened > "$N"; o=$(run_keep y 0); { [[ "$o" == *"API=n"* ]] && [ ! -e "$N" ]; } || bad="$bad other-word"
echo open > "$N"; o=$(run_keep n 0); { [[ "$o" == *"API=n"* ]] && [ ! -e "$N" ]; } || bad="$bad no-keep"
row "K2 a note not root's, a link, another word, or no upgrade: the API not opened; the note gone" "$([ -z "$bad" ] && echo 0 || echo 1)" "wrong for:$bad"

# D1-D3
bad=""
for l in "/run/sd.sock (Stream)"$'\n'"0.0.0.0:4247 (Stream)" "[::]:4247 (Stream)"; do
  rm -f "$N"; o=$(run_save no "$l"); { [ "$(cat "$N" 2>/dev/null)" = open ] && [ "$(stat -c %a "$N")" = 600 ] && [[ "$o" == *REACHED-END* ]]; } || bad="$bad [$l]"
done
row "D1 kept + listening for other computers: note says open, mode 600" "$([ -z "$bad" ] && echo 0 || echo 1)" "wrong for:$bad"
echo open > "$N"; o=$(run_save no "/run/sd.sock (Stream)"$'\n'"127.0.0.1:4247 (Stream)")
row "D2 kept + local only: no note (a stale one removed)" "$([ ! -e "$N" ] && [[ "$o" == *REACHED-END* ]] && echo 0 || echo 1)" "$o"
echo open > "$N"; echo '[Socket]' > "$E/sdclient.socket.d/sd-remote-api.conf"; o=$(run_save yes "0.0.0.0:4247 (Stream)")
row "D3 configuration deleted: no note, REMOTE.API's drop-in and its empty directory removed" \
    "$([ ! -e "$N" ] && [ ! -e "$E/sdclient.socket.d/sd-remote-api.conf" ] && [ ! -d "$E/sdclient.socket.d" ] && [[ "$o" == *REACHED-END* ]] && echo 0 || echo 1)" "$o"

# W
ln_() { grep -n -m1 -E "$2" "$1" | cut -d: -f1; }
la=$(ln_ "$INST" '^# ACCESS-ASK-END'); ls_=$(ln_ "$INST" '^if ! sudo -v'); lk=$(ln_ "$INST" '^# API-KEEP-END'); lb=$(ln_ "$INST" 'Allowing API access from other computers')
lc=$(ln_ "$INST" '^    sudo mv /home/sd/sd.conf /etc'); lq=$(ln_ "$DEL" '^read -r -p "Keep your existing configuration'); lv=$(ln_ "$DEL" '^# API-SAVE-BEGIN'); lf=$(ln_ "$DEL" 'ufw delete allow 4247/tcp')
echo "  W lines: ask-end=$la first-sudo=$ls_ keep-end=$lk bind=$lb conf-restore=$lc | conf-q=$lq save=$lv fw-remove=$lf"
row "W the blocks are in order" "$([ -n "$la$ls_$lk$lb$lc$lq$lv$lf" ] && [ "$la" -lt "$ls_" ] && [ "$lk" -lt "$lb" ] && [ "$lk" -lt "$lc" ] && [ "$lq" -lt "$lv" ] && [ "$lv" -lt "$lf" ] && echo 0 || echo 1)" "out of order"

echo "test-install-keepaccess: $pass passed, $fail failed"
[ "$pass" -eq 0 ] && { echo "test-install-keepaccess: NOTHING RAN"; exit 2; }
[ "$fail" -eq 0 ]
