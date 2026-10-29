#!/usr/bin/env python3
#
# tuirows.py - the result counter shared by the four S.88 suites (sandbox-realkeys, sandbox-tk-resize, sandbox-ide-fresh, sandbox-termsafe).
#
#   from tuirows import Rows
#   R = Rows("realkeys")
#   R.row("K1 F1 as xterm sends it is f1", ok, detail, phase=1)     # phase = the phase of Opus_TUI_Plan.txt whose change makes it pass
#   sys.exit(R.finish())
#
# WHY IT EXISTS.  The plan (~/Documents/Audits/TUI/Opus_TUI_Plan.txt, section 6) builds the test net first and fixes in phases.  A row for a fault
# that a later phase fixes must be RED on the tree before its fix (the instrument rule), yet a suite that is red on purpose would fail every
# targeted regression that selects it.  So a failing row whose phase has not landed (is not in LANDED) is counted PENDING, not failed, and the verdict line
# says so; `--strict` (or SDTUI_STRICT=1) counts every row at its face value, which is how the red run is made and shown.  A row with no phase,
# or a phase that has landed, always counts.  Each phase's commit adds its number to LANDED, in this file, so that its rows are then
# held to the pass.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88, Phase 0).
# END-HISTORY
import os
import sys

# The phases of the plan whose change has landed (S.88).  Phase 1 (the input layer) landed 28 Oct 26; Phase 4 (the IDE: untitled buffer, name form, save under a lock) landed 28 Oct 26
# BEFORE phases 2 and 3 on the owner's word, so this is a set and not "the last phase": a failing row of phase 2 or 3 is still pending.  A phase's commit adds its number here.
LANDED = (1, 2, 4)                # Phase 2 (data loss and terminal safety) built 28 Oct 26, its suites written and NOT yet run (the owner's rule: one complete run when all the full-screen phases are done)

STRICT = ("--strict" in sys.argv) or os.environ.get("SDTUI_STRICT") == "1"


class Rows:
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.pending = 0

    def row(self, name, ok, detail="", phase=None):
        if ok:
            self.passed += 1
            print("  [PASS] " + name)
        elif phase is not None and phase not in LANDED and not STRICT:
            self.pending += 1
            print("  [PEND phase %d] %s%s" % (phase, name, ("   <- " + detail) if detail else ""))
        else:
            self.failed += 1
            tag = " (phase %d)" % phase if phase is not None else ""
            print("  [FAIL]%s %s%s" % (tag, name, ("   <- " + detail) if detail else ""))
        sys.stdout.flush()
        return ok

    def finish(self):
        """Print the verdict line regress.sh reads and return the exit status: 1 for a failed row, 0 otherwise."""
        print("sandbox-%s: %d passed, %d failed, %d pending%s" % (self.name, self.passed, self.failed, self.pending, " (strict)" if STRICT else ""))
        sys.stdout.flush()
        return 1 if self.failed else 0
