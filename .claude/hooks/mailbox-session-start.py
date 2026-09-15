#!/usr/bin/env python3
"""SessionStart hook: look in the SD Core mailbox and ask the session to start
its mailbox loop.

Owner, 15 Sep 2026: the Linux and Windows agents share a pCloud mailbox (see
CLAUDE.md, "Messages from the SD Core for Windows agent"), and the check is to
run on a loop that starts at the beginning of every session here. A hook
cannot start a loop itself - only the session can - so this reads the inbox,
says what is in it, and tells the session to start the loop once.

Read-only: it lists file names and moves nothing. It always exits 0, because a
mailbox that cannot be read must not stop a session from starting; it says so
in the context instead.
"""

import json
import os
import sys

INBOX = os.path.expanduser("~/pCloudDrive/sdcore-mail/to-linux")

# 15 Sep 26 - the owner: act on in-scope messages without asking, and make the
# check adaptive so parity discussions move quickly.  A watcher Monitor
# (.claude/mailbox-watch.sh) wakes the session within seconds; this 15-minute
# loop is the fallback and keeps the watcher armed.  The rules are in CLAUDE.md.
LOOP_ARGS = (
    "15m Check the SD Core mailbox: list ~/pCloudDrive/sdcore-mail/to-linux/ "
    "(skip *.partial) and handle any new message following CLAUDE.md's "
    "section \"Messages from the SD Core for Windows agent\": act without "
    "asking on what it puts in scope (parity decisions approved in either "
    "port, interop details for work under way, defects to verify), move each "
    "handled message to done/, and report what was done; anything "
    "port-specific or a new capability goes to the owner. Then make sure the "
    "mailbox watcher is running: if no Monitor is armed for "
    "/home/don/Projects/sdcore4linux/.claude/mailbox-watch.sh, arm one with "
    "timeout_ms 1800000, and re-arm it whenever it expires. If there is "
    "nothing new, say nothing."
)


def main():
    try:
        source = json.load(sys.stdin).get("source", "")
    except (ValueError, AttributeError):
        source = ""

    if not os.path.isdir(INBOX):
        state = ("is NOT REACHABLE (%s does not exist - is pCloud Drive "
                 "mounted?). Tell the owner; do not start the loop." % INBOX)
        start = False
    else:
        names = sorted(n for n in os.listdir(INBOX)
                       if not n.startswith(".") and not n.endswith(".partial"))
        partial = [n for n in os.listdir(INBOX) if n.endswith(".partial")]
        if names:
            state = "holds %d message(s): %s." % (len(names), ", ".join(names))
        else:
            state = "is empty."
        if partial:
            state += " (%d file(s) still syncing, ignored.)" % len(partial)
        start = True

    context = "SD Core mailbox: %s %s" % (INBOX + "/", state)
    if start:
        context += (
            " START THE MAILBOX LOOP NOW, once for this session: invoke the "
            "loop skill with args: %s If a mailbox loop is already running in "
            "this session (session source: %s), do not start a second one."
            % (LOOP_ARGS, source or "unknown"))

    print(json.dumps({
        "systemMessage": "SD Core mailbox: " + state,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
