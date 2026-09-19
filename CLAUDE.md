# CLAUDE.md

## Where these rules came from

**This file is carried over from SD Core for Windows**
(`/home/don/Projects/SDCoreWindowsProject/sd4windows/CLAUDE.md`), on the owner's
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

It was created empty on 8 Sep 2026 and has been written to since. Add to it in
the same commit as your work; do not let it go stale, because a wrong claim in
it costs more than no claim at all.

**Its task table, at the top, is the authority on what is left** (owner,
14 Sep 2026). Before answering that question, read it and run
`python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/check-stale-leads.py`.
The upkeep rules are under "Writing it down".

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
grep -n -i -E 'get_ak_node' PROJECT_STATUS.md ChangesApplied.txt UnsafeProposed.txt /home/don/Projects/SDCoreWindowsProject/sd4windows/*.md
```

Read every hit. A hit is normally a session that has already paid for it.

**A broad term returns dozens of hits. Narrow it, do not skip it** — add a second
stage for warning language:

```sh
grep -n -i -E 'update\.accounts' /home/don/Projects/SDCoreWindowsProject/sd4windows/*.md |
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

## Check the Windows port history before you ask

Owner, 10 Sep 2026, after a session asked which verbs a STANDARD account should
lose when the decision and its rationale were already in the port's `HISTORY.md`
(*"17 Aug 2026 — Section 8"*). **Before asking the owner any question, search the
Windows port history for the answer first.**

The port is the reference implementation (see "Project stance"), and its record
carries decisions already made and paid for — `HISTORY.md`, `PROJECT_STATUS.md`
and `PRE_RELEASE_FIXES.md` under `/home/don/Projects/SDCoreWindowsProject/sd4windows`.
Its `.md` files have very long lines; extract a window around the match rather
than printing the whole line.

**Pull it whenever parity work needs it, without asking** (owner, 15 Sep 2026:
*"you have my permission to pull the windows repository whenever needed when
working on parity tasks"*). The Windows agent pushes from the Windows box, so
the local copy falls behind. Before reading it for parity work, run
`git -C /home/don/Projects/SDCoreWindowsProject/sd4windows pull --ff-only`. If the pull
refuses because of local changes or a diverged branch, stop and tell the owner.
Never merge or reset over the copy. The permission is to pull, not to commit or
push there.

**Forward the question to the owner only when** the port history has **no
definitive answer**, or its answer **cannot be implemented on Linux** — the
privilege model differs, so some of the port's security answers do not transfer
(the memory file's privilege-model note has the shape of this). A genuinely local
decision the record cannot settle — whether to push a commit now, say — is not a
port-history question and is asked normally. **When the record does answer and
the answer ports, act on it and cite where it came from, instead of asking.**

## Messages from the SD Core for Windows agent

Owner, 15 Sep 2026: the two ports are developed by two Claude agents on two
machines, and no Claude facility connects them. **They share a mailbox on
pCloud: `~/pCloudDrive/sdcore-mail/` here, `P:\sdcore-mail\` on Windows. Its
`README.md` holds the rules.**

- **When to read `to-linux/`:**
  - at the start of a session
  - when the owner says "check mail"
  - before changing anything the two ports must agree on: the API protocol and
    TLS, SDEXT and kernel key numbers, and message numbers (the memory note on
    shared number spaces)

  Skip `*.partial` files, because pCloud may hold only half of one.
- **Reply with a new file in `to-windows/`.** Write it under a name ending
  `.partial`, then rename it. Never edit the other agent's file. Move a message
  you have handled to `done/`.
- **Act on an in-scope message without asking, then report what you did** (owner,
  15 Sep 2026: *"you should act without asking"*). In scope:
  - a parity decision covered by the next bullet
  - an interop detail for work already under way
  - a defect the port reports in this tree, verified here before it is believed
    (the reader's half of "Writing it down")

  Move the message to `done/` once handled. Anything port-specific, a new
  capability, or a request outside those still goes to the owner. Never put a
  password, key or token in a message.
- **A parity decision approved in one port is approved in both** (owner, 15 Sep
  2026, recorded in the Windows `CLAUDE.md` and relayed by its agent). His words:
  *"when discussing making the functionality of the two systems the same, I do not
  have to be involved in every decision in both places — if it is approved in one,
  it is approved in both."* So a decision whose purpose is to make the two systems'
  functionality the same needs his approval in only one port, and a message
  reporting that approval is enough to act on here. It does not cover anything
  port-specific (the installer, the toolchain, a mechanism only one OS has) or a
  new capability neither port has shipped; those still go to him.
- **Git stays the record.** A message points at a commit or an entry. A finding
  that must last goes into PROJECT_STATUS.md, or into the port's
  `BUGS_FROM_LINUX_PORT.md`, not the mailbox.
- **The check runs from the start of every session** (owner, 15 Sep 2026).
  `.claude/hooks/mailbox-session-start.py`, a `SessionStart` hook in
  `.claude/settings.json`, lists the inbox and tells the session to start the
  `loop` skill every 15 minutes, once. A hook cannot start a loop itself, so if
  its instruction is in context and no loop is running, start it.
- **The check is adaptive: a watcher wakes the session within seconds, and the
  15-minute loop is the fallback** (owner, 15 Sep 2026). He first said *"when
  working on parity issues together the loop should be more often, otherwise
  processes could take hours"*. The Windows loop was then made adaptive *"so
  that parity discussions can happen quickly"*.
  - `.claude/mailbox-watch.sh` runs as a Monitor. It reports every message
    already in `to-linux/` when armed, then each new one within 5 seconds, and
    says when the mailbox becomes unreachable.
  - A Monitor expires after 30 minutes; re-arm it on each expiry.
  - Each 15-minute tick re-arms the watcher if it is not running, and handles
    anything the watcher missed.

  This replaced a fixed 2-minute cadence the same day. If the Windows port's
  adaptive design differs, its design is followed here (Project stance).

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
**All three parts, every time, in the same block** (the port's wording, 12 Sep
2026).

1. ***PROVE IT LOADS. A script you have not watched load is not ready to
   submit.*** Parse or compile it — `python3 -m py_compile file.py`,
   `bash -n file.sh` — and **byte-scan for the gremlins the parser waves through**:
   a BOM (`grep -a -b -o $'\xEF\xBB\xBF' file`), or CRLF endings on a shell script,
   which make `bash` fail with messages naming the wrong line. A parse-check alone
   is not enough; in the Windows record a BOM'd file parsed with **0 errors** and
   19 functions became 18. The one exemption is the inline one-liner whose failure
   you see at once.
2. ***THE ABSOLUTE PATH, WITH EVERY VARIABLE ALREADY EXPANDED.***
   `/home/don/Projects/SDCoreLinuxProject/sdcore4linux/installsdai.sh`, never `installsdai.sh`, never
   `$cwd/...`. A script that finds its own location internally does not change
   this: that makes it cwd-independent *once found*, which is the part a bare name
   breaks.
3. ***`sudo` OR NOT, SAID OUT LOUD — INCLUDING WHEN IT IS NOT.*** (Adapted: on
   Windows this was the elevation verdict.) Silence is not "probably fine". Some of
   this project's measurements are only valid as an ordinary user — anything
   testing what an unprivileged SD account may reach — so the wrong shell does not
   merely fail, **it can produce a clean-looking wrong answer.** The tiers are gone
   now (the teardown), and the rule only gets sharper: measurements that differ
   between an administrator and a plain account must still say which shell ran
   them.

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
(for SD verbs, `sdsys/gpl.bp/<VERB>` names the `display sysmsg(...)` calls), and
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
- ***THE TASK TABLE IS KEPT, NOT WRITTEN ONCE*** (owner, 14 Sep 2026, adopting
  the port's rule of 26 Aug, which followed a day of different "what is left"
  lists — this project had the same day). **The session that closes, compiles
  or witnesses something updates its row in the same commit**: tick it, strike
  the entry, date it. A headline claiming UNRUN or UNWITNESSED is a claim about
  a machine, and whoever changes the machine owns it. **New work gets a row
  when its entry is written.** Run `check-stale-leads.py` after editing these
  documents, and commit on its exit 0.
- ***WHEN YOU CLOSE PART OF AN ENTRY, FIX ITS FIRST SENTENCE*** (port, 26 Aug
  2026). A reader stops at the first status sentence, so a correction appended
  below a stale opening misleads everyone who does not read to the end.
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
  ***AND THE WINDOWS PORT'S DECISIONS ARE THIS PORT'S DECISIONS*** (owner, 15 Sep
  2026: *"the linux port should follow the windows port decisions where not
  contraindicated by the differences between the two operating systems"*). A
  decision taken there binds here, whether it is in the port's record or arrives
  through the mailbox, and is adopted without asking the owner again. The
  exception is a decision the OS difference contraindicates: the privilege
  model, a mechanism only one OS has, or a Windows-only workaround. Then say
  which difference applies and forward it to the owner, as "Check the Windows
  port history before you ask" already requires. Where the port stopped short,
  §M's rule to go further still stands.
- **Release numbering follows SD Core for Windows, not upstream.** Upstream's
  1.0-3 is not this project's next version.
- ***THE TIERED ACCOUNT MODEL IS RIPPED OUT*** (owner's decision, 18 Sep 2026 —
  the parity plan's §L is reversed; the teardown is S.25–S.28 in PROJECT_STATUS).
  One VOC layer (NEWVOC as shipped) for every account; one administrator, SDSYS —
  the `sdsys` OS user on a local session, never root, never remote; SH and
  OS.EXECUTE run at the account's own Linux permissions; ssh and the API are
  open to every account except SDSYS; GRANT/REVOKE/LIST.GRANTS are gone —
  `usermod -aG` is the grant; suspension is a plain account flag
  (`MODIFY.ACCOUNT ... SUSPENDED`/`UNSUSPENDED` — the port's word, 19 Sep 2026).  **The security-model evaluation
  the owner reserved follows once the teardown is witnessed on an install.**
  Built as one change set, 18 Sep 2026 (`e41d318`); ***witnessed on an
  install 19 Sep 2026 (`60ac74a`, the seventh cycle)*** - so the evaluation
  is now the owner's to start (W.11 in PROJECT_STATUS).
- **Lower case throughout**, matching the port. On a case-sensitive filesystem this
  needs real migration rather than the port's "both spellings work anyway".
  ***AND COMPLETE, WHICH THE PORT IS NOT*** (owner, 11 Sep 2026). The standard is
  **everything lower case** — names on disk, VOC entries, program and include
  names, and the files `CREATE.FILE` makes — with upper-case input converted on
  the fly, ***so no command, file or record id can exist in two casings.*** The
  port meant this and did not finish it; NTFS hid the gaps (measured list in
  PORT_ADOPTION queue 18, filed to the port as a bug). **Where the port stopped
  short, go past it: this outranks "the port wins" for §M.**
- **Kept, and deliberately different from the port:** embedded Python, and UMASK,
  which has no security effect on Windows and is a real mechanism here.
- **This system is maintained by AI.** An engineering constraint, not a note about
  process: it argues for machine-checkable invariants, generated headers, and a
  `git status` that can be read.
- ***THIS VERSION SHIPS FOR PRODUCTION, NOT FOR DEVELOPERS*** (owner, 9 Sep 2026).
  The source is public and forkable, comments and bug reports are welcome, and
  **other humans will not be committing** — one human is involved. **The
  installer is not a developer's tool.** *Use it when weighing a convenience for
  whoever builds from source against a weakness in what is installed:* **the
  shipped system owes an ordinary user nothing for development**, and the one
  person who needs a developer's facility has `sudo` and the source tree.
  `PRE_RELEASE` 21 is the worked example — `sd -internal` went behind
  `check_admin()` on this ruling, with `make EXTRA_C_FLAGS=-DSD_DEV_BUILD` as
  the opt-in hatch that **announces itself and cannot reach a user**, because
  the installer builds from a fresh clone.
- ***SECURITY SHIPS TIGHT AND THE ADMINISTRATOR RELAXES IT BY CHOICE*** (owner,
  12 Sep 2026). *"Security starts tighter but can be relaxed by choice."* Where
  a capability could reasonably default either way, **ship it off** and leave
  the administrator a deliberate act to turn it on — and make that act possible,
  documented and reversible. **The restrictive default is not a judgement that
  nobody should have the capability; it is a decision about who decides.**
  `MODIFY.PASSWORD` is the worked example: it is an administrator act
  (the sdsys OS user, local session — after the teardown there is no per-account
  relaxation for it; a deliberate divergence from the port, named in
  `set_acc_password`), and the general rule stands: ***SO A RESTRICTIVE DEFAULT
  WITH NO WAY TO RELAX IT IS THE THING TO AVOID***, and "a user cannot do X" is
  not by itself a defect to fix — check whether the administrator can grant it
  before treating it as one.
- ***A RICH BASIC SCREEN/WIDGET LIBRARY IS A GOAL — FOR 1.2, NOT 1.1*** (owner,
  10 Sep 2026; moved after the 1.1 release on 15 Sep 2026). Extend
  SD BASIC so a programmer builds rich terminal screens — administrative apps
  rivalling the best TUI frameworks, up to a traditional terminal-based IDE —
  **without leaving BASIC and without any commercial or client-side dependency.**
  GPL-clean: standard ANSI/terminfo escape sequences only, shipped as catalogued
  SD BASIC (thin C only where BASIC cannot reach). AccuTerm is ruled out
  (commercial, needs a server-side API, GPL-incompatible). Design note in
  PROJECT_STATUS.md's Open section.

## Where this repository lives

Renamed from `sdscripts_ai` to **`sdcore4linux`** on 8 Sep 2026, to match its new
home on GitHub. The directory is `/home/don/Projects/SDCoreLinuxProject/sdcore4linux`.

**Moved there from `/home/don/Projects/sdcore4linux` on 16 Sep 2026** (owner). The
repository itself did not change: one worktree, a real `.git` directory, same
`origin`, same HEAD. `SDCoreLinuxProject` is a containing folder outside the
repository, so the lower-case-throughout stance is unaffected. **A move breaks the
hand-over paths, which are absolute by rule** — 62 of them across 43 files were
retargeted the same day. If the folder moves again, sweep
`grep -rn '/home/don/Projects' --exclude-dir=.git --exclude-dir=gplobj --exclude-dir=bin`
before believing any documented command.

**The Windows port moved the same day**, from `/home/don/Projects/SDCoreProject/sd4windows`
to `/home/don/Projects/SDCoreWindowsProject/sd4windows` (owner, 16 Sep 2026); its
9 references here were retargeted in the same commit. That path is a dependency of
"Check the Windows port history before you ask" and of the record-grep rule, so a
stale one silently searches nothing — which reads as *"the port's record has no
answer"* and sends a question to the owner that the record already answers.

| Remote | URL | What it is |
|---|---|---|
| `origin` | `git@github.com:dmontaine/SDCore4Linux.git` | **The project's home, and the only remote.** ssh, key `~/.ssh/id_ed25519`, authenticates as `dmontaine` |

**Codeberg is no longer this project's repository** (owner, 10 Sep 2026). The
`codeberg` remote (`codeberg.org/stringdatabase/sdscripts_ai`, where the tree
came from) was removed that day; do not re-add it.

***MIND THE CAPITALISATION: THE GITHUB REPOSITORY IS `SDCore4Linux`, THE LOCAL
DIRECTORY IS `sdcore4linux`.*** The lower-case URL works but only through a
GitHub redirect, which prints *"This repository moved"* on every push. `origin`
is set to the canonical spelling; leave it that way. The directory stays lower
case to match the project's own lower-case-throughout stance.

`main` tracks `origin/main`. The first push was 8 Sep 2026, at `e5ceb16`, after
the four commits that made `git status` readable — see PROJECT_STATUS.md.

Upstream `sdb64` is a **third** thing and is not a remote here — clone it
separately when §K needs checking.

## Project constraints

- **Linux only.** Windows development lives in `sd4windows`. Do not add `#ifdef`
  branches to keep Windows building.
- **The installer is a shell script and stays one** — `installsdai.sh`. ***It
  clones `main` from `github.com/dmontaine/SDCore4Linux` and builds
  `sdb_ai/sd64` from the clone*** (owner, 9 Sep 2026, superseding plan §F9 and
  the earlier wording here, which said it built the bundled tree). **So an
  install tests `origin/main`, not your working tree — commit and push first, or
  you are testing something else.** Nothing stops such an install;
`assert-current` reports it afterwards (`PRE_RELEASE` 8, 15).
- **Binaries are not tracked, and must stay that way.** `.gitignore` covers
  `sd64/bin/` (except its README), `sd64/gplobj/`, `sd64/terminfo/`,
  `pcode_bld.log` and the installer-generated `gplsrc/sdext_python_inc.h`. All of
  it is rebuilt by `make` — the .gitignore cites the Makefile line for each. **A
  clean `git status` is now a working instrument here; do not break it.**

## Building

```sh
cd /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64 && make
```

`make` must run from `sdb_ai/sd64` — the Makefile uses `MAIN := $(shell pwd)/`.
After a toolchain or header change, clear stale objects with `rm -f gplobj/*.o`;
`make` relinks only what changed, which is not the same as "the tree is current".

**A developer build is the one documented deviation, and it is opt-in:**

```sh
make EXTRA_C_FLAGS=-DSD_DEV_BUILD
```

It drops the privilege check on `sd -internal` so `GPL.BP` can be compiled
without `sudo` — see "Testing" and `PRE_RELEASE` 21. ***REBUILD WITH PLAIN
`make` WHEN YOU ARE DONE***: `bin/sd` is what a hand-over points at, and a
developer binary differs from the shipping one in a privilege check. It says so
on `--version` and on every use of the flag, which is how you check rather than
remember.

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

~~***THIS PROJECT HAS NO EQUIVALENT OF THE WINDOWS `assert-current` GUARD.***~~
***IT HAS ONE NOW — 9 Sep 2026. RUN IT BEFORE BELIEVING ANY MEASUREMENT:***

```sh
python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/assert-current.py
```

No `sudo`. **Exit 0 current, 1 stale, 2 the question cannot be answered** — and
the third is a real answer, not a failure to produce one of the other two.

**It is a rewrite of the port's, not a copy, because the question differs**: the
installer here clones `main` from GitHub, so `bin/sd` is not what got installed
even on a current tree. It checks that the working tree is committed, that HEAD
is `origin/main`, that the install's own commit stamp matches HEAD, and that
`bin/sd` is newer than `gplsrc`. ***AN INSTALL PREDATING THE STAMP ANSWERS `2`,
NOT `0`*** — reinstall once and it becomes exact. Unit tests:
`gplbld/test-assert-current.py`, 10 rows.

## The free checks run on every change

Adopted from the port's tier 1 (its CLAUDE.md, 30 Aug 2026): checks that need
no install, no `sudo` and no `sd`. Run them as an ordinary user from
`sdb_ai/sd64`. **The first sixteen took 7.3 s, measured 14 Sep 2026**; the
seventeenth, `test-scram-vectors.py`, compiles a C test and is not in that
figure. A new free check joins this list in the commit that creates it.

In `gplbld/`: `test-accounts-units.py` · `test-assert-current.py` ·
`test-basicfuncs-units.py` · `test-configpath-units.py` (and `--selftest`, 8
mutants) · `test-editors-units.py` · `test-edittokens-units.py`
· `test-msglen-units.py` · `test-nonet-units.py` · `test-sd-elevate.py` · `test-sdverify-units.py` ·
`test-ssh-forcecommand.py` · `test-sysperms-units.py` ·
`test-staleleads-units.py` · `test-scram-vectors.py` · `test-tls-relay.py`
(C, needs OpenSSL headers - exit 2 without libssl-dev; S.19) ·
`test-tlsconsts-units.py` · `test-scramprobe-units.py` (loads libssl) ·
`verify-nocase.py` ·
`sdverify.py --selftest` · `check-storewriters.py` (and `--selftest`) ·
`check-stale-leads.py`. From the repository root:
`.claude/hooks/no-program-edits.py --selftest`.

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
