#!/usr/bin/env bash
#
# mailbox-watch.sh - one line per message arriving in the SD Core mailbox.
#
# Owner, 15 Sep 2026: parity discussions with the Windows agent must move
# quickly - "otherwise processes could take hours" - so a message wakes the
# session within seconds instead of waiting for a timer.  The session runs this
# as a Monitor (CLAUDE.md, "Messages from the SD Core for Windows agent"); each
# line it prints is a notification.  A 15-minute check is the fallback.
#
#   bash /home/don/Projects/sdcore4linux/.claude/mailbox-watch.sh [INBOX] [SECONDS]
#
# Read-only: it lists names and touches nothing.  It polls rather than using
# inotify, because files pCloud syncs in from the other machine need not raise
# inotify events on the FUSE mount.
#
# What it prints, and nothing else:
#   WATCHING <inbox> every <n>s                once, so the arming is visible
#   NEW MESSAGE: <path>                         each file not seen before - and
#                                               every file already there when it
#                                               starts, so nothing waiting is missed
#   MAILBOX UNREACHABLE: <inbox>                when the directory disappears
#   MAILBOX REACHABLE AGAIN: <inbox>            when it comes back
# *.partial files (still being written or synced) and dotfiles are never reported.

inbox=${1:-$HOME/pCloudDrive/sdcore-mail/to-linux}
interval=${2:-5}
declare -A seen
unreachable=0

echo "WATCHING $inbox every ${interval}s"
while true; do
  if [ ! -d "$inbox" ]; then
    [ "$unreachable" -eq 0 ] && echo "MAILBOX UNREACHABLE: $inbox"
    unreachable=1
  else
    [ "$unreachable" -eq 1 ] && echo "MAILBOX REACHABLE AGAIN: $inbox"
    unreachable=0
    for f in "$inbox"/*; do
      [ -f "$f" ] || continue
      name=${f##*/}
      case $name in
        *.partial|.*) continue ;;
      esac
      if [ -z "${seen[$name]+x}" ]; then
        seen[$name]=1
        echo "NEW MESSAGE: $f"
      fi
    done
  fi
  sleep "$interval"
done
