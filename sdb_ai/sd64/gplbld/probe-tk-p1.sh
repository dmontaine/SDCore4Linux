#!/bin/bash
#
# probe-tk-p1.sh - Phase 0 question P1 of the full-screen toolkit plan (.claude/plan-fullscreen-toolkit.md, section 3): does a privileged verb give the same answer when a
# PROGRAM calls it with EXECUTE as when it is typed at the prompt?  A MEASUREMENT on a machine with SD installed (the Debian 13 clone VM).  It changes nothing on the
# machine except one scratch program in each of two accounts, which it deletes.
#
#   sudo bash /var/tmp/probe-tk-p1.sh ORDINARY_OS_USER
#
# Run as root.  The administrator session is `sudo -u sdsys sd` (SDSYS's OS user, a local pipe); the ordinary one is `sudo -u ORDINARY_OS_USER sd` (an SD account's
# user).  For each audience it prints what the verbs print when TYPED and what the same two verbs print when a program EXECUTEs them CAPTURING the output.  The verbs:
# list.servers and modify.account with no arguments, both SDSYS only and both read-only.  Every line of the program's output is tagged P1.
set -u
OU=${1:-}
[ -n "$OU" ] || { echo "usage: $0 ORDINARY_OS_USER" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "probe-tk-p1: needs root" >&2; exit 2; }
SDSYS_DIR=/usr/local/sdsys
SD=$SDSYS_DIR/bin/sd
[ -x "$SD" ] || { echo "probe-tk-p1: CANNOT RUN - no $SD" >&2; exit 2; }
echo "probe-tk-p1: $(head -1 $SDSYS_DIR/changelog 2>/dev/null)  sd=$SD"

PROG='   execute "list.servers" capturing a
   crt "P1 PROG list.servers [": convert(@fm, "|", trim(a))[1, 90] : "] bytes=": len(a)
   execute "modify.account" capturing b
   crt "P1 PROG modify.account [": convert(@fm, "|", trim(b))[1, 90] : "] bytes=": len(b)
end'

acctdir() { # os-user -> the directory of its SD account
  if [ "$1" = sdsys ]; then echo "$SDSYS_DIR"; return; fi
  local p; p=$(head -1 "$SDSYS_DIR/accounts/$1" 2>/dev/null)
  p=${p/@USRDIR/$SDSYS_DIR\/user_accounts}
  echo "$p"
}

run() { # os-user label
  local who=$1 label=$2 dir
  dir=$(acctdir "$who")
  echo "--- $label (OS user $who, account directory ${dir:-UNKNOWN})"
  [ -d "$dir/bp" ] || { echo "    CANNOT RUN: no $dir/bp"; return 1; }
  printf '%s\n' "$PROG" > "$dir/bp/zzp1"
  chown "$who" "$dir/bp/zzp1" 2>/dev/null
  # SDSYS is entered only by a real login (S.26): the machine's login id must be sdsys's.  Root can write it (the bridge witness-masters.sh uses): /proc/self/loginuid.
  # The ordinary account needs no bridge.
  printf 'TERM 200,9999\nBASIC BP ZZP1\nlist.servers\nmodify.account\nRUN BP ZZP1\nOFF\n' | sudo sh -c '
      if [ "$1" = sdsys ]; then printf "%s\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; fi
      exec sudo -u "$1" env TERM=xterm "$2"' probe-run "$who" "$SD" 2>&1 \
    | sed 's/\x1b\[[0-9;?]*[A-Za-z]//g' | tr -d '\r' | grep -v '^$' | cut -c1-200
  rm -f "$dir/bp/zzp1" "$dir/bp.out/zzp1" 2>/dev/null
}
run sdsys "the administrator"
run "$OU" "an ordinary account"
