# CLAUDE.md

## Where these rules came from

**This file is carried over from SD Core for Windows**
(`/home/don/Projects/SDCoreProject/sd4windows/CLAUDE.md`), on the owner's
instruction of 8 September 2026. The behavioural rules below were each written
after a specific session lost time in *that* project; the incidents, dates and
evidence are in **its** `HISTORY.md` and `PROJECT_STATUS.md`, not in this
repository's record.

**That provenance matters when you read a rule and want to argue with it.** The
cost was paid, but it was paid next door. Where a rule names a Windows mechanism
it has been adapted to the Linux equivalent, and the adaptation is marked.

**Some rules have been merged.** The Windows file states four of them twice, from
different angles, and says so itself — *"the backslash rule, the CRLF trap and the
`Set-Content` trap are all the same lesson."* Merged here on the owner's
instruction, 8 Sep 2026. Nothing has been dropped, only stated once: the escape
traps sit under the file-editing rule, the success-wording rule under instruments,
and the emphatic-voice rule under writing things down.

**Refer to the Windows project freely.** It is the reference implementation for
this one — see "Project stance" — and its record is the history this project does
not yet have.

## Read this first

**[PROJECT_STATUS.md](PROJECT_STATUS.md) is the handoff document. Read it before
doing anything else in this repository.** It holds the current state, the
decisions already made and why, the traps that have already cost time, and the
ordered next steps.

***IT IS CURRENTLY EMPTY.*** It was created on 8 Sep 2026 and nothing has been
written into it yet. An empty handoff document is not permission to skip the
handoff — it means you are the session that starts filling it in.

The parity plan the project is working from lives outside the repository at
`/home/don/Documents/claude_plan.md` (and `.pdf`). Read it for what is being
changed and why; it carries a verification table with `file:line` for every
defect it claims.

## Search the record before you run anything

Owner, 23 Aug 2026, after three or four consecutive sessions in the Windows
project where the thing that went wrong **was already written down before the
session started.** Sessions are not lost to unknowns. They are lost to warnings
that were on disk and unread.

**Before running a command, grep the record for what you are about to run** — the
verb, script, path or flag you are about to type, most distinctive token first.
**Grep the Windows project too, which is where the history actually is:**

```sh
grep -n -i -E 'get_ak_node' PROJECT_STATUS.md ChangesApplied.txt UnsafeProposed.txt /home/don/Projects/SDCoreProject/sd4windows/*.md
```

Read every hit. A hit is normally a session that has already paid for it.

**A broad term returns dozens of hits. Narrow it, do not skip it** — add a second
stage for warning language:

```sh
grep -n -i -E 'update\.accounts' /home/don/Projects/SDCoreProject/sd4windows/*.md |
  grep -i -E 'NEVER|DO NOT|CANNOT|MUST|trap|hung|hang|cost|refus|wrong|stale'
```

**Everything needs the check except this list:** reading a file, `grep`/`find`,
and read-only `git` (`log`, `show`, `status`, `diff`). If you are deciding whether
something is harmless enough to skip, that is the moment the rule is for.

**Some warnings are in the memory file rather than these documents** — the
`MEMORY.md` index is loaded every session, so read it as part of the same check.

**Finding a warning does not forbid the command.** Overriding a stale one is
legitimate — say which warning, and why it does not apply, before you run.
Overriding one you never saw is what this rule exists to stop.

## Run standing procedures exactly as written

Owner, 23 Aug 2026, after a session ran a documented script with an undocumented
flag. His words: *"If I had been asked I would have asked for clarification and
said no."*

**The standing commands are written with their arguments.** Anything you add to
one is a change to the owner's procedure and needs his yes first. **A flag that
exists, is documented, and is off by default is not thereby approved.**

**Unattended operation is a GOAL, not a smell** (owner, 28 Aug 2026). Reducing the
number of times a person has to be present is wanted. But **pursue it by removing
the need for a prompt, not by skipping the step**, and ***no verdict may come from
a run nobody could have observed.*** Removing the need for a person to be
*present* is allowed; removing the evidence that would have let one disagree is
not.

**This is about deviating, not about doing.** Running the documented command as
documented needs no permission, and neither does ordinary reading, searching or
building.

## A file edit goes through Edit or Write

Owner, 28 Aug 2026. ***NOT `python`, NOT `sed -i`, NOT A HEREDOC REDIRECT.***

**The rule is about the FIRST reach, and that is where it keeps going wrong.** The
edit always looks mechanical enough to script — three rows, one regex — and that
is exactly the case the editing tools handle with **no encoding, line-ending or
escape surface at all.**

**This is enforced, not remembered.** `.claude/hooks/no-program-edits.py` is a
`PreToolUse` hook that refuses shell commands which write to a source or document
file. It was written for the Windows project after a session that had read the
rule broke it twice in one sitting — the second time *while writing the paragraph
about the first*. A guard that cannot be forgotten beats a rule that can. Run
`python3 .claude/hooks/no-program-edits.py --selftest` if you suspect it; it
reports 32 cases, 0 failed.

**What it deliberately does not block:** reading (`cat`, `grep`), redirects to temp
and `/dev/null`, heredocs feeding a *command* rather than a file
(`git commit -F - <<'EOF'`), and a transform written to a **script file** and run.

**If a transform genuinely is too large to do by hand** — the lower-case rename in
§"Project stance" will be — say so first, put it in a script file rather than
inline, and check the result: `git diff --stat`, plus a spot check that content and
not just names moved.

**Why the escape traps are filed here.** Three separate document corruptions in the
Windows record were each blamed on a different escape rule — backslashes, CRLF,
`Set-Content` — and each was written up as advice about *how* to write the snippet.
**They were followed and the file was still edited by a program.** So the rule is
about the tool, and the escape traps are only worth knowing for the script-file
escape hatch above:

1. **Unquoted heredoc (`<<EOF`)** — the *shell* eats `\` and expands `$`. Widely
   known, and the reason people reach for `<<'EOF'`.
2. **Quoted heredoc (`<<'EOF'`) feeding Python** — the shell is now innocent and
   **Python's own string literals** still interpret the escapes. `'\t'` becomes a
   tab and fails **silently**; `'\U'` fails at parse time. **Quoting the heredoc
   fixes 1 and does nothing for 2.**

## Handing something over: prove it loads, and say where and how to run it

Two owner rules, 23 and 28 Aug 2026, merged because they share a trigger: **the
moment something leaves you for the owner's terminal, its failure lands away from
you.** A rerun, a retry with a different flag, a command repeated from earlier in
the same message — each is a fresh hand-over and carries all three parts again.

1. ***PROVE IT LOADS. A script you have not watched load is not ready to
   submit.*** Parse or compile it — `python3 -m py_compile file.py`,
   `bash -n file.sh` — and **byte-scan for the gremlins the parser waves through**:
   a BOM (`grep -a -b -o $'\xEF\xBB\xBF' file`), or CRLF endings on a shell script,
   which make `bash` fail with messages naming the wrong line. A parse-check alone
   is not enough; in the Windows record a BOM'd file parsed with **0 errors** and
   19 functions became 18. The one exemption is the inline one-liner whose failure
   you see at once.
2. ***THE ABSOLUTE PATH, WITH EVERY VARIABLE ALREADY EXPANDED.***
   `/home/don/Projects/sdcore4linux/installsdai.sh`, never `installsdai.sh`, never
   `$cwd/...`. A script that finds its own location internally does not change
   this: that makes it cwd-independent *once found*, which is the part a bare name
   breaks.
3. ***`sudo` OR NOT, SAID OUT LOUD — INCLUDING WHEN IT IS NOT.*** (Adapted: on
   Windows this was the elevation verdict.) Silence is not "probably fine". Some of
   this project's measurements are only valid as an ordinary user — anything
   testing what an unprivileged SD account may reach — so the wrong shell does not
   merely fail, **it can produce a clean-looking wrong answer.** That is the whole
   point of the tier work below.

## An instrument shows what it DID, not just what it concluded

Owner, 23 Aug 2026, after three false verdicts in one session. **Every one was a
confident conclusion drawn from an instrument that never reached the condition it
claimed to measure.**

Any probe, test or verifier must print, in its own output:

1. ***THE REAL INPUTS IT USED*** — the exact command line and arguments passed, the
   resolved paths, the target account. Not what it intended to pass.
2. **The state it compared — BEFORE and AFTER**, not just the conclusion.
3. ***AND IT MUST REFUSE THE NULL CASE OUT LOUD.*** If the measurement could have
   run against nothing, test for that and say so. **A test that passes because it
   did nothing must fail, not pass.**

***AND ANCHOR ON THE SUCCESS WORDING, NOT ON ANY STRING THE FAILURE ALSO
CARRIES.*** A verification is a claim about a specific outcome, so its match text
must appear **only when that outcome happened** — never when the tool refused,
printed "not found", or merely echoed its own input. **A pattern shared by the
success and failure outputs is not a check; it is a false positive with a check's
name on it.** In the Windows record a step matched on the record id it had passed
in, which appeared in the echoed command, the refusal *and* the error — three
places on the failure path — and three runs were voided before anyone read the raw
output. Two fixes: match the wording the tool prints **on the positive path**
(for SD verbs, `sdsys/GPL.BP/<VERB>` names the `display sysmsg(...)` calls), and
**match the failure wording too and refuse if it appears** — `not in register`,
`not found`, `syntax error`.

**THE FIX IS NEVER THE ONE-LINE CAUSE.** Ask what would have caught it, not what
caused it.

## Writing it down, cheaply and honestly

Owner, 14 Aug 2026: **the ratio of time spent on the project to time spent
documenting it was too high.** PROJECT_STATUS.md is **written for the next AI
session, not for him** — he does not read it.

- **Terse and factual.** `file:line` over description. No narrative, no emphasis
  for effect, no restating a finding in several sections.
- **Documentation is a small fraction of a session.** If it approaches half, stop
  and cut. Do not print line counts in the files or re-measure to keep them true.
- **Update PROJECT_STATUS.md in the same commit as the work**, and never move
  anything into "Verified" without observing it yourself that session. **Compiling
  is not running.**
- **`sdb_ai/sd64/sdsys/changelog` is the exception**: it ships to users, stays
  plain English, and gets anything a user would notice, in the same commit. **Write
  it the way SD Core for Windows writes it** — what changed, why it mattered, and
  what it does *not* do — not as terse developer notes. That style is why 232
  changes could be reconstructed from one file.

***THE EMPHATIC VOICE IS FOR WHAT WAS OBSERVED. A PLAN IS WRITTEN IN THE
CONDITIONAL.*** (Owner, 5 Sep 2026 — the instrument rule applied to prose.)
ALL-CAPS and bold mean *"this was paid for"* everywhere else in these documents,
so spending them on a hypothesis transfers authority it has not earned. A plan for
work not yet begun names what would falsify it. ***And where a session raised an
objection to its own plan and resolved it in conversation, the objection goes in
the entry anyway*** — the resolution is the least-tested claim in the document, and
this is the clause that will feel most like clutter to write.

***THE READER'S HALF: A MEASUREMENT YOU TOOK BEATS A CLAIM YOU READ.*** When your
own trace disagrees with these documents, the documents are the thing to doubt —
they were written by a session that could not run the command you just ran. Say
which claim, show the measurement, and carry on.

## Project stance

Set by the owner, 8 September 2026. These are decisions, not preferences, and two
of them reverse what an earlier analysis recommended.

- **Smaller system, less historical cruft.** Removing an unwanted feature is a
  gain. Going: the TAPE/RESTORE subsystem, PROC, SED, UPDATE.RECORD, MODIFY,
  SDNet, the VFS scaffolding, OPGEN, the SDSYS `BP` test programs.
- ***CONFORMITY WITH SD CORE FOR WINDOWS IS THE GOAL, AND IT OUTRANKS CONFORMITY
  WITH UPSTREAM `sdb64`.*** Where the two disagree, the Windows port wins.
  Upstream is a source of fixes to take, not a contract to honour.
- **Release numbering follows SD Core for Windows, not upstream.** Upstream's
  1.0-3 is not this project's next version.
- **The three-tier account model is adopted** — STANDARD, PROGRAMMER,
  ADMINISTRATOR, plus SUSPENDED — with the security posture that goes with it.
  The largest single piece of conformity work.
- **Lower case throughout**, matching the port. On a case-sensitive filesystem this
  needs real migration rather than the port's "both spellings work anyway".
- **Kept, and deliberately different from the port:** embedded Python, and UMASK,
  which has no security effect on Windows and is a real mechanism here.
- **This system is maintained by AI.** An engineering constraint, not a note about
  process: it argues for machine-checkable invariants, generated headers, and a
  `git status` that can be read.

## Where this repository lives

Renamed from `sdscripts_ai` to **`sdcore4linux`** on 8 Sep 2026, to match its new
home on GitHub. The directory is `/home/don/Projects/sdcore4linux`.

| Remote | URL | What it is |
|---|---|---|
| `origin` | `git@github.com:dmontaine/sdcore4linux.git` | **The project's home.** ssh, key `~/.ssh/id_ed25519`, authenticates as `dmontaine` |
| `codeberg` | `https://codeberg.org/stringdatabase/sdscripts_ai` | Where it came from. Kept so nothing is lost; not the place to push |

***`main` STILL TRACKS `codeberg/main` AND GITHUB IS EMPTY.*** Nothing has been
pushed to `origin` yet, deliberately — see the binaries and the mode-only noise
under "Project constraints". **Do not push without the owner's yes**, and read
§J1–J3 of the plan first: what is in the working tree is not what should become the
first commit of a new repository.

Upstream `sdb64` is a **third** thing and is not a remote here — clone it
separately when §K needs checking.

## Project constraints

- **Linux only.** Windows development lives in `sd4windows`. Do not add `#ifdef`
  branches to keep Windows building.
- **The installer is a shell script and stays one** — `installsdai.sh`. It builds
  from the `sdb_ai/` tree bundled in this repository, not from a clone.
- **Binaries should not be tracked.** They currently are — `sd64/bin/` and 93 `.o`
  files under `sd64/gplobj/` — and there is no `.gitignore`. Fixing that is step 0
  of the plan. Until it is fixed, be careful what you claim `git status` shows.

## Building

```sh
cd /home/don/Projects/sdcore4linux/sdb_ai/sd64 && make
```

`make` must run from `sdb_ai/sd64` — the Makefile uses `MAIN := $(shell pwd)/`.
After a toolchain or header change, clear stale objects with `rm -f gplobj/*.o`;
`make` relinks only what changed, which is not the same as "the tree is current".

## Testing: a test cycle begins with a fresh install

Carried over from the Windows rule of 15 Aug 2026, where stale installs caused the
same failure repeatedly.

**Date what you are testing before believing any result from it**, and state the
full path of the binary under test. `/usr/local/sdsys/bin/sd` is the installed one;
`sdb_ai/sd64/bin/sd` is the built one; they are the same only just after an install.

**A CYCLE ENDS AT THE NEXT SOURCE CHANGE.** Any result taken from the tree after a
source change is void, not "probably still valid".

**The two-stage bootstrap is where BASIC changes actually land.** `installsdai.sh`
runs `sd -i` twice; a `GPL.BP` change that compiles is not thereby installed.

***THIS PROJECT HAS NO EQUIVALENT OF THE WINDOWS `assert-current` GUARD, AND THAT
IS A GAP RATHER THAN A DIFFERENCE.*** There, a script refuses to run any
verification against a tree whose install is older than its source. Here nothing
checks, so the discipline is yours. Writing that guard is worth a session.

## Conventions

- **Match the surrounding code.** It is a 2007 Ladybridge codebase with its own
  idioms — `Public`/`Private` macros, `START-HISTORY` blocks, banner comments. Add
  a dated line to a file's `START-HISTORY` block when changing it.
- **Mind the near-miss names.** `GPL.BP/MODIFY` is the record editor and is being
  removed; `GPL.BP/MODIFYA` is MODIFY.ACCOUNT and stays. `MODIFY.PASSWORD` stays.
- **Generated files are not edited by hand.** `SYSCOM/ERR.H` derives from
  `gplsrc/err.h` and has already drifted out of sync with it (wrong sign, C
  spelling, missing codes). `gplsrc/sdext_python_inc.h` is written by the installer.
- **Explain *why* in commit messages, not just what.** The reasoning is the part
  that does not survive in the diff.
