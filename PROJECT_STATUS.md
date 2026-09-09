# PROJECT_STATUS.md

Handoff document for SD Core for Linux. See [CLAUDE.md](CLAUDE.md) for how to
maintain it: terse, `file:line` over description, updated in the same commit as
the work, nothing in "Verified" that was not observed that session.

## START HERE

*Handoff updated 9 Sep 2026. **Step 4 is complete.** Steps 2 and 3 implemented,
neither exercised on a running system; §I built nothing and compiled nothing —
the next install is what proves it.*

**[PRE_RELEASE_FIXES.md](PRE_RELEASE_FIXES.md) is the release worklist** —
started 9 Sep 2026 on the owner's ask. It is the tracker the port created for
final testing; here it also carries **gaps testing will never find**, including
two the plan is silent on: **the port's 31 relevant PowerShell helpers**
(`PRE_RELEASE` 1) and **the editor story** (2). Read its table, not its section
headings.

**The plan is `/home/don/Documents/claude_plan.md`** (and `.pdf`), outside the
repository, with a `file:line` verification table for every defect it claims.
**Its detail has been wrong** — see the §I note — so confirm a claimed
`file:line` before acting on it.
Work follows its "Suggested order". **Steps 0–3 are done; nothing in steps 2–3
has been exercised on an installed system.**

### Your next task

***STEP 4 IS COMPLETE.*** All of §G and all of §I are done — `I1` TAPE, `I3` SED,
`I4` UPDATE.RECORD, `I5` MODIFY, `I2` PROC, `G1` BP test programs (PY_* kept),
`G2` VFS, `G3` OPGEN, `G4` SDNet. **None of §I has been installed**; the BASIC
was not compiled this session (see "Step 4 / §I" for what instrument was tried
and why it could not).

***START WITH `PRE_RELEASE` 19 — IT IS ONE SHORT PROGRAM AND IT GATES §L.***
Session ended out of credits, 9 Sep 2026, mid-investigation. `op_kernel.c:305-307`
**reads as though** `kernel(K$ADMINISTRATOR, 1)` sets `USR_ADMIN` for any caller,
short-circuiting `IsAdmin()`. **Read, not measured** — the check is a BASIC
program doing `x = kernel(26, 1)` then `crt kernel(26, -1)` from a non-root
account; **1 means the hole is real** and every administrator gate is bypassable,
including `LOGIN:217`'s SDSYS restriction. A test machine and a live install were
available, and `CREATE.FILE BP DIRECTORY` is how to get a program into an account
without an editor — that is how the `PQ` fixture was made.

**Then `PRE_RELEASE` 18**, which is now specified rather than open: the owner
defined "administrator" on 9 Sep as **sudoers member AND registered SD
administrator, with unregistered users refused entry**. The gap table and the
port's `ACC$TIER 5` / `ACC$PRIOR.TIER 6` are in that entry.

**Your next task after those is step 5, the installer.** ***`F9` IS SUPERSEDED — DO NOT DO
IT.*** The owner ruled on 9 Sep 2026 that the installer always clones `main`
from GitHub, which is the opposite of §F9's "drop the clone and build the
bundled tree". Done that day; see "Installer" below. Remaining: `F1` upgrade
split · `F2` `UPDATE.ACCOUNTS` · `F3` `[locked]` · `F4` config parser · `F5`
changelog location · `F7` self-check · `F6`, `F8`.

***AND THE CONSEQUENCE F9 EXISTED TO PREVENT IS NOW LIVE: AN INSTALL TESTS
`origin/main`, NOT THE WORKING TREE.*** Commit and push before testing, or you
are testing something else and nothing will tell you. `PRE_RELEASE` 15.

***THE LOWER-CASE CONVERSION IS NOT IN QUESTION AND NOTHING HAS BEEN DROPPED.***
It is the owner's standing decision — CLAUDE.md Project stance, 8 Sep 2026,
*"lower case throughout, matching the port"* — and it is **conformity with SD
Core for Windows**, which outranks conformity with upstream. §M happens.

***OWNER'S RULING ON THE TIMING, 9 Sep 2026: "no problem with delaying it until
later in the port as long as it is done by the end."*** So the schedule below is
settled, and §M is a **commitment on the port, not a plan item that may lapse**.
It is listed in Open as release-blocking for that reason: **the port is not
finished with `GPL.BP` and `SYSCOM` still upper case.** A later session that
finds §M inconvenient may re-order it; it may not drop it.

**What was withdrawn is a SCHEDULING suggestion, and it was a prior session's,
not the owner's.** The line *"a good place to insist on the lower-case migration
going in with it"* entered this file in `3d61b3a` (step 3) and hardened by
recopying into *"fold in the lower-case migration here"* — an emphatic
imperative with no ruling or measurement behind it. **§M stays where the plan
puts it, at step 7**, for two reasons that are dependencies rather than taste:

- §M2's migration is *"a rename step for an existing tree, per account and for
  `sdsys`"* **inside `installsdai.sh` and `update.accounts`**. `update.accounts`
  does not exist here — only a singular `VOC_TEMPLATE/UPDATE.ACCOUNT` — and §F2
  (step 5) opens by saying to check whether `GPL.BP` has an equivalent. The
  container is unbuilt work.
- §M1: *"The order is not optional: fold, then rename. Renaming first breaks
  every existing name until the fold lands."* The rename is the half that looks
  like it belongs with a bulk removal pass; it is precisely the half §M1 forbids
  going first.

***STEP 4 MOVED §M FORWARD RATHER THAN BACK.*** `I3`/`I4`/`I5`/`I2` deleted four
programs and nine VOC records that would otherwise need renaming, and §M1's own
text says `UPDATE.RECORD`'s keyword fold is *"moot — §I4 removes it"*. **`M1`'s
fold has no dependency on `update.accounts` and can be started at any time** if
the owner wants §M begun before step 5.

***Step 4 installs, boots and runs at `2b4d9f0`*** (owner, 9 Sep — see State of
the tree). **`G4` is CLOSED by the owner's decision, 9 Sep.** Its read side was
observed: `SELECT VOC` / `LIST VOC ID.SUP` / `COUNT VOC` listed records normally,
exercising op_open, read_record, op_readv and op_select. Write, delete and record
lock were *not* run; the owner accepted them on the read-side witness plus
conformity with the Windows port, which exercised these paths. That acceptance is
reasoning, not a measurement — if a G4 file-I/O fault ever surfaces, op_write /
op_delete (`op_dio3.c`) and the six `op_lock.c` sites are where to look first.

***Testing bar for the shrink (owner's ruling, 9 Sep):*** because this walks a
path the Windows port already walked, an occasional compile-and-run test is
enough for now; more extensive testing comes later. So the remaining removals
(`G2`, `I3`/`I4`/`I5`/`I2`) are held to "compiles clean and the tree still
installs and runs a command", not a per-fix exercise — with the deferred testing
tracked in Open.

***The plan says take §I as ONE release, not scattered commits*** (plan I intro):
`I3`/`I4`/`I5` and PROC's `LISTPQ` all edit `VOC_TEMPLATE`/`NEWVOC`/`SD.VOCLIB`,
and doing them in one pass means those are edited once and `update.accounts`
(§F2) runs once. `I1` TAPE was exempt — it is copied in from `tape/` at install,
never shipped in `VOC_TEMPLATE` — so it went alone. Do the VOC-touching removals
together. Mind the near-miss names (`MODIFY` the record editor goes; `MODIFYA` =
MODIFY.ACCOUNT stays; `MODIFY.PASSWORD` stays). `I2` PROC is the deep one
(compiler + opcode `OP_PROCREAD`); the plan says report "PROC not supported" at
the `CPROC:1530` dispatch and RETIRE the opcode slot rather than reuse it. A good
place to fold in the lower-case migration.

**Deferred to a later testing pass** (owner's testing-bar ruling, 9 Sep — see the
Step-4 note above: compile-and-run is enough for now). These behaviours are not
individually exercised and are collected here so the later pass has the list:
- Step 2 (`A1`–`A6`) is where a wrong fix is silent; `A1` needs an *induced
  commit failure* (a read-only or externally-locked record) to reach at all.
- Step 3's regenerated `ERR.H`/`ERRTEXT.H` — an error from a crypto/Python code
  should show message text, not a bare number. **No BASIC references the renamed
  defines** (checked: they flow as numbers, ERRTEXT.H maps number→text).
- `G4` write/delete/record-lock (read/select observed; see the Step-4 note).
- ~~`G2`: `sd` has not started from a pcode library built without
  `_EXTENDLIST`.~~ ***CLOSED 9 Sep 2026 — see "The 11:35 install" below.***
- ~~§I: the edited `CPROC` has not been compiled.~~ ***CLOSED 9 Sep 2026 — same
  install.*** **Still open from §I:** a VOC record of type `PQ` printing message
  `10099` naming the verb, **not** sysmsg 5053 "invalid dispatch code". Nothing
  shipped is type `PQ`, so this needs one written by hand.

**Higher-value unpaid debt first: EXERCISE steps 2 and 3.** Nothing in either has
run on an installed system.
- Step 2 (`A1`–`A6`) is where a wrong fix is silent; `A1` needs an *induced
  commit failure* (a read-only or externally-locked record) to reach at all.
- Step 3 regenerated `SYSCOM/ERR.H`, `GPL.BP/ERRTEXT.H`, `REVSTAMP.H` and
  reformatted every SDEXT/crypto/Python error `$define` from C spelling to SD
  spelling. **No BASIC references the renamed defines** (checked: they flow as
  numbers, ERRTEXT.H maps number→text), so the risk is low, but it has not been
  seen on a running system. An install would confirm error text now displays.

### ***BEFORE YOU IMPLEMENT ANYTHING, GREP THE WINDOWS RECORD***

Not a formality. It corrected the plan **twice** in step 2's first third and
shaped every fix since — the port is the reference implementation and
`UPSTREAM_FIXES.md` / `PRE_RELEASE_FIXES.md` carry the *why*.
`/home/don/Projects/SDCoreProject/sd4windows` has those plus `HISTORY.md`; the
entries are long, and the detail near the end of one is usually the correction.
For step 4 the removals each have a §I/§G entry; grep the record for the one you
start with, e.g.:

```sh
grep -n -i -E 'PROC|TAPE|SDNet|OPGEN|VFS' /home/don/Projects/SDCoreProject/sd4windows/*.md
```

### The 11:35 install, 9 Sep 2026 — G2 and §I are closed

***THE OWNER RAN THE REWRITTEN INSTALLER AND IT WORKED.*** He ran it; this
session did not. `/usr/local/sdsys/bin/sd`, **11:35:04**, 1,592,528 bytes. What
follows was then measured **on the installed tree**, this session, every row
against a control that fired:

| On `/usr/local/sdsys` | removed | control |
|---|---|---|
| `GPL.BP/_EXTENDLIST` · `PCODE.OUT/_EXTENDLIST` | **0**, **0** | `_DELLIST` **1**, **1** |
| `GPL.BP/SED` · `MODIFY` · `PROC` · `UPDREC` | **0** each | `ED`, `MODIFYA`, `QPROC`, `BBPROC` **1** each |
| `VOC_TEMPLATE`+`NEWVOC`: `SED`, `UPDATE.RECORD`, `MODIFY`, `LISTPQ` | **0** each | `MODIFY.ACCOUNT`, `ED`, `EDIT` present |
| `MESSAGES/10099` — must be **PRESENT** | **1** | `5053` **1** |

***THE FOUR CONTROLS IN ROW 2 ARE THE NEAR-MISS NAMES***, so that table also
shows the removal took the right things and not their neighbours.

**`G2` is closed, and the chain matters more than the conclusion.**
`GPL.BP.OUT/CPROC` exists, dated **11:35:12**. It is produced by the bootstrap's
`sd -i` compiling `GPL.BP`; for that `sd` had to run; for `sd` to run
`load_pcode()` had to succeed; and `load_pcode()` **refuses to start** when a
`Pcode()` entry has no library object. `bin/pcode` was rebuilt from the
`pcode_fs` list with `_EXTENDLIST` gone. **So `sd` started from a pcode library
built without it** — the loud failure mode did not fire.

**§I is closed on the same object.** The edited `CPROC` compiled: a syntax error
in the replaced `PQ` arm would have aborted bootstrap pass 1 and there would be
no object. This is what `bbcmp.py` could not do (it aborts on `$IFNDEF`).

***AND §I IS ALSO VERIFIED AT RUN TIME, NOT ONLY ON DISK.*** `sd` runs
non-interactively as an ordinary user with **no sudo** — `sd --version` exit 0 is
the control that it runs at all, and `sd COUNT VOC` answers **410 record(s)**.
Against a live account VOC:

| `COUNT VOC WITH @ID =` | result | |
|---|---|---|
| `SED`, `MODIFY`, `UPDATE.RECORD`, `LISTPQ`, `PROC` | **0** each | removed |
| `ED`, `EDIT`, `CATALOG` | **1** each | controls |

***THE MEASUREMENT IS DATED, WHICH IS WHAT MAKES IT WORTH ANYTHING.*** An account
VOC can survive a reinstall, and this one did not: `/home/sd/user_accounts/don`
and its `VOC` are stamped **11:35:12**, eight seconds after the binary, so it was
built by this install.

**Two controls came back 0 and both are explained rather than waved away.**
`MODIFY.ACCOUNT` and `MODIFY.PASSWORD` are absent from a user VOC because
***`CREATEA:422` BUILDS A NEW ACCOUNT'S VOC FROM `NEWVOC`, NOT `VOC_TEMPLATE`***,
and neither name is in `NEWVOC`. `MODIFY.PASSWORD` is in neither file at all,
which is plan §E5 confirmed.

***THAT IS WORTH KEEPING FOR §L: THE PRODUCT ALREADY SHIPS TWO VOCABULARIES.***
`VOC_TEMPLATE` 423 records, `NEWVOC` 407, and the 17 only in `VOC_TEMPLATE` are
exactly the administrative set — `CREATE.ACCOUNT`, `DELETE.ACCOUNT`,
`MODIFY.ACCOUNT`, `UPDATE.ACCOUNT`, `ACCOUNTS`, `MESSAGES`, `GPL.BP`, `BP`,
`QFILE`, `UNLOCK`, the three compile passes, `LOAD.LANGUAGE`, `$HOLD`,
`BP.OUT`, `GPL.BP.OUT`. Only `%t` is in `NEWVOC` alone. **§L's tiers can extend
an existing split rather than invent one**, and the plan does not say this.

### Exercised on the live install, 9 Sep 2026 — §I2 and B1/B2 CLOSED

The owner: *"this is a test machine — you don't have to worry about the running
sd, it is only there for testing."* So the two checks held back were run.

***§I2's `PQ` DISPATCH IS RUN, NOT JUST COMPILED.*** A type-`PQ` VOC record was
built by hand — `CREATE.FILE PQSRC DIRECTORY`, the record written as an ordinary
file (a directory file's records **are** OS files, which avoids driving `ED`),
then `COPY FROM PQSRC TO VOC TESTPQ`, *1 record(s) copied*. Invoking it:

```
PROC is not supported in this version of SD, and TESTPQ is a PROC.
```

**Anchored both ways, as the instrument rule asks:** the success wording present
**1**, and `invalid dispatch code` (sysmsg 5053, the arm a deleted case would
have fallen into) present **0**, as are *not found* and *Unexpected token*.
**Cleaned up afterwards** — `COUNT VOC` 410 before, 412 with the fixtures, **410
after**.

***B1 AND B2 ARE CLOSED — the two the Open list called most worth doing.*** As
uid 1000:

| run as an ordinary user | sysmsg 2001 |
|---|---|
| `CATALOG BP $X` — the prefix route B2 was written for | **refused** |
| `CATALOG GLOBAL BP X` — the keyword route | **refused** |
| `DELETE.CATALOG $X` — B1 | **refused** |
| `CATALOG BP X` — **local, the control** | **not refused** (fails *"File BP.OUT not found"*) |

The control is what makes the other three mean anything: the gate discriminates
rather than refusing everything.

***AND THE MEASUREMENT FOUND SOMETHING THE FIX DID NOT: `system(27)` IS
`getuid()`*** (`gplsrc/op_sys.c:222`). So "administrator" in these gates is
**literal root**, `sd` is not setuid, and a session runs as the invoking Unix
user — **an SD ADMINISTRATOR who is not root will be refused, and any user who is
root admitted.** B1/B2 are correct as written and follow the existing rev 0.9.0
convention; **what needs deciding is what "administrator" means**, before §L can
grant the tier anything. `PRE_RELEASE` 18, and the same root as 14.

***WHAT IS STILL NOT ESTABLISHED.*** Steps 2 and 3 remain unexercised, and the
rest of step 1 (`D1`, `D2`, `C1`, `D3`, `B4`). This install was of
**`origin/main`**, not the working tree (`PRE_RELEASE` 15).

### State of the tree

- **Clean and pushed.** `main` tracks `origin/main`; remote is
  `git@github.com:dmontaine/SDCore4Linux.git` — **capitalised**, the lower-case
  form only works through a redirect that warns on every push.
- Renamed from `sdscripts_ai` on 8 Sep 2026. Git identity is **repo-local**
  (`.git/config`, `dmontaine@gmail.com`); there is no `~/.gitconfig`, so other
  repositories will still ask.
- **9 Sep 2026: the owner reinstalled the WHOLE tree at `2b4d9f0` (through
  step 4/G4), rebooted, started `sd` and ran a command — no problems.** ***What
  that establishes: the tree builds, installs, boots and runs.*** The two-stage
  bootstrap recompiled every edited `GPL.BP` program (DEBUG, ERRTEXT, APISRVR,
  CPROC, the removed-verb VOC), so D6's commented `$execute`s, D5's regenerated
  headers and the G4 removals all load; a syntax error in any would have aborted
  the install. ***WHAT IT DOES NOT ESTABLISH: the fixes' own behaviour.*** A
  generic command boots the VM but does not touch the open/read/write/delete/
  lock/select dispatch G4 rewrote, D5's error-text display, or A1's undo (which
  needs an induced commit failure). The per-step check tables still stand
  unrun. ***The one most worth doing is a file-I/O smoke test for G4*** —
  `SELECT`/`LIST`/`COUNT VOC` plus a create/write/read/delete on a scratch file.

## Verified — 8 Sep 2026

**Step 0 of the plan is done: `git status` went from 2667 modified files to 7.**
Three commits, in this order:

| Commit | What |
|---|---|
| `9f82a52` | The AI hardening layer, 174 files. It had been sitting unstaged on `main` and was not backed up |
| `67f696e` | `.gitignore` added; 203 build artifacts untracked (files left on disk) |
| `6181c36` | 2285 data records `100755` → `100644` |

Measured before and after, not inferred: 2667 dirty → 334 with content change →
0 after the three commits; the residual 7 were the untracked documents committed
alongside this file.

**Build directories are recreated by the build** — so untracking them is safe:

- `Makefile:67` — `$(shell mkdir -p $(GPLOBJ) $(GPLBIN))` creates `gplobj/` and
  `bin/`.
- `Makefile:104-108` — the `terminfo` target does `rm -Rf`, `mkdir -p`, then
  regenerates from the tracked `terminfo.src` with `sdtic`.
- `Makefile:74` — `sd:` depends on `terminfo`, so a plain `make` rebuilds it.

**CLOSED 8 Sep 2026: the owner ran `installsdai.sh` and it built, installed and
let him log in.** The installer builds from this tree, so untracking `gplobj/`,
`bin/`, `terminfo/` and the rest cost nothing — a build after them produces a
working system. (`make sd` had also been run in-session after deleting four `.o`
files: 0 errors, 0 warnings, `bin/sd` relinked. That was incremental; the install
is the stronger evidence.)

**Other observations this session:**

- `.claude/hooks/no-program-edits.py --selftest` → 32 cases, 0 failed, run from
  this directory.
- `ssh -T git@github.com` authenticates as `dmontaine`, key `~/.ssh/id_ed25519`.
- No file in the mode set was a script; `installsdai.sh` and `deletesdai.sh` keep
  their executable bit.

## Step 1 of the plan — all eight applied, 8 Sep 2026

The release is now **`L1.0-0`** and `sdsys/changelog` carries its section.

| | Where | Fix |
|---|---|---|
| D1 | `gplsrc/k_error.c:216` | size limit was `(LINES + LEN)+1` = 84 against a 241-byte buffer, and ignored the offset already written; now `sizeof(s) - n` |
| D2 | `gplsrc/op_skt.c:673` | `n = TRUE;` removed — it discarded the caller's keep-alive value |
| C1 | `gplsrc/clopts.c:300` | `process.user_no` → `user_no`; task locks were compared against the cleanup process, not the dead session |
| B4 | `gplsrc/sysseg.c:413` | guard `uptr->pid > 0` (and `sdlnxd_pid > 0`); pid 0 made `kill()` signal the caller's process group |
| B2 | `sdsys/GPL.BP/CATALOG` | one admin gate after the `end case`, covering the GLOBAL keyword *and* all three prefix routes |
| B1 | `sdsys/GPL.BP/DELCAT` | admin gate inside the branch that touches `gcat`; it had no check at all |
| D3 | `sdsys/GPL.BP/TERM` | `DEFAULT.WIDTH`/`DEFAULT.DEPTH` (120×36) instead of `MIN.WIDTH` and a literal 24 |
| E1 | `sdsys/VOC_TEMPLATE/ENCRYPT.FIELD` | removed; `$CRYPTO` is not in the distribution |

**Owner ran a full install, 8 Sep 2026: it compiles, it installs, and he could
log in.** He ran it; this session did not. That report closes three questions the
session could not close for itself:

- **The four BASIC changes compile.** `installsdai.sh` aborts on bootstrap pass 1
  failure, and the bootstrap is what compiles `GPL.BP` — so a syntax error in
  `CATALOG`, `DELCAT` or `TERM` would have stopped the install.
- **Removing `ENCRYPT.FIELD` did not break account setup.** Login reaches the
  `LOGIN` paragraph through a `VOC` built from the edited `VOC_TEMPLATE`.
- **A from-scratch build works**, which is the test the previous entry left open.

***WHAT IT DOES NOT ESTABLISH: NOT ONE OF THE EIGHT FIXES HAS BEEN EXERCISED.***
Signing in does not touch keep-alive, task locks, the `sd -stop` pid guard, error
message length, either catalogue gate, or `term default`. **"It installed and I
logged in" means the tree is sound, not that any of these behaves as claimed.**

The cheap checks that would actually exercise them, in rough order of
value-per-minute — none has been run:

| Fix | Check |
|---|---|
| D3 | `term default` then `term` — expect `120` × `36`, not `20` × `24` |
| B1/B2 | from a non-administrator account: `CATALOG BP $X` and `DELETE.CATALOG $X` — both should now refuse with sysmsg 2001. **Anchor on the refusal wording, not on `$X` appearing in the output** |
| D1 | any error whose message runs past ~84 characters — previously cut off mid-sentence |
| C1 | take `LOCK 3` in a phantom, kill it, `sd -cleanup`, then take `LOCK 3` again |
| D2 | `SET.SOCKET.MODE(skt, SKT$INFO.KEEP.ALIVE, 0)` then `SOCKET.INFO(...)` — the two used to disagree |
| B4 | hardest to stage safely: needs a user-table entry with pid 0 |

Two judgement calls worth knowing, per CLAUDE.md's rule about recording the
objection as well as the resolution:

- **B1/B2 use one gate at a chokepoint rather than the check copied into each
  route.** Copying it four times is what let the original drift — rev 0.9.0 added
  it to the keyword route and not the three prefix routes. The keyword route keeps
  its own early check for the better message; the chokepoint is what holds.
- **D3 drops the `@term.type = 'sdterm'` special case** that set depth 25 instead
  of 24, because `LOGIN:85,90` makes no such distinction when sizing a session.
  **This was not measured on an sdterm terminal.** If sdterm really has 25 usable
  lines, `GPL.BP/TERM` is the line to revisit.

## Step 2, first third — unchecked return values, 8 Sep 2026

`A5` and `A6`. **`make sd`: 0 errors, 0 warnings**; `dh_ak.o`, `op_seqio.o`,
`dh_file.o` recompiled, `sd` relinked. **Not exercised** — forcing either needs
an induced I/O failure (read-only file, mandatory lock, full disk).

***THE RECORD CHECK PAID FOR ITSELF HERE AND IT IS WORTH SAYING WHY.*** Both
fixes exist in the Windows tree as PRE_RELEASE 100 and 103, and its entries
corrected the plan on two points this session would otherwise have got wrong:

1. **Seven call sites, not four.** `/home/don/Documents/claude_plan.md` §A5 lists
   `2280`, `2301`, `2429`, `3471`. There are also `3524`, `3895` and `3929`.
   Counted in this tree: 7 calls, 7 guards.
2. ***A CALLER-SIDE TEST FOR 0 WOULD NOT HAVE BEEN ENOUGH.*** `get_ak_node()` has
   three failure paths and the middle one — `dh_read_group` failing on the free
   node — assigned `new_node_num` from `GetAKFwdLink()` **before** the read, then
   fell to the exit **without clearing it**. It returned a non-zero node number,
   the head of the free chain, with `free_chain` never advanced: a node the file
   still believes is free, which two allocations could be given. The 0 convention
   is now total inside the function.

| | Where | Fix |
|---|---|---|
| A5 | `gplsrc/dh_ak.c` | `get_ak_node()` failure made total (free-node path clears, `chsize64` checked → `DHE_AK_WRITE_ERROR`); all 7 call sites abort on 0 using each function's own idiom — `goto exit_ak_write`, `goto exit_update_internal_node`, `head = 0; goto exit_write_ak_big_rec` |
| A5 | `dh_ak.c` root split | `node_ptr->node_num = get_ak_node(...)` took a temporary `old_root_node_num`; it assigned straight into the node structure, so a test after the store reads a value already committed |
| A6 | `gplsrc/op_seqio.c:1433` | `WEOFSEQ` — truncate checked, `process.status = -ER_IOE` + `os_error` |
| A6 | `gplsrc/op_seqio.c:752` | `OPENSEQ … OVERWRITE` — same |
| A6 | `gplsrc/dh_file.c:831` | `SetFileSize()` returns `chsize64(...) == 0` instead of unconditional `TRUE` |

**Two details taken from the record rather than rediscovered:**

- ***THE STATUS HAS TO BE NEGATIVE.*** Both opcodes already carry a `k_error`
  guarded on `process.status < 0` (`sysmsg(1420)` in `op_weofseq`, `sysmsg(1416)`
  in `op_openseq`), and positive values are handed back to the program. A
  positive status would have left the report unable to fire.
- **The `goto exit_op_openseq` was checked in this tree, not assumed.** The
  truncate is at `:752`, the file variable is not published into `fvar_descr`
  until `:761`, and the exit frees `fvar` and `sq_file` whenever status is set.

**`SetFileSize` is behaviour-neutral today** — its only callers, `dh_clear.c:107`
and `:114`, still discard the result. It is fixed so that a caller *can* check.

**One instrument lesson from this session, recorded because it nearly cost a
wrong edit:** a `grep | head -12` cut off the line defining `DHE_AK_WRITE_ERROR`
and I briefly concluded the symbol did not exist. It is `err.h:261`. A truncated
instrument reads exactly like a negative result.

## Step 2, second third — transactions, the localised half, 8 Sep 2026

`A2`, `A3`, `A4`, all in `gplsrc/txn.c`. **`make`: only `txn.o` recompiled, `sd`
relinked, 0 errors, 0 warnings. Not exercised** — every check below needs a fresh
install and an induced condition; none was run this session. Step 2 is where "it
compiled" is worth least.

| | Where | Fix |
|---|---|---|
| A2 | `txn.c` TXN_WRITE/DIRECTORY_FILE (`:187`) | `map_t1_id(txn->id, …, mapped_id)` then `dir_write(fvar, mapped_id, …)`; map failure raises 1422 rather than skip |
| A2 | `txn.c` TXN_DELETE/DIRECTORY_FILE (`:225`) | same map, **before** the statistics counters; `snprintf` uses `mapped_id` |
| A3 | `txn.c` same delete arm (`:255`–`:268`) | `stat`/`S_IFREG` guard + tested `remove()` (`errno != ENOENT` → `ER_PERM`, `log_permissions_error`, 1423), copied line-for-line from the non-transactional twin `op_dio3.c:390`–`:403` |
| A4 | `txn.c` `end_txn_level()` | reinstate-and-decrement lifted out of `rollback()` into `end_txn_level()`; called from `op_txncmt()` too, **before** `exit_op_txncmt:` |

**What the Windows record (UPSTREAM_FIXES 17/31/36) added beyond the plan:**

- **A2 — the cache is right to hold the raw id; do not "fix" the write-side
  split.** `op_dio3.c:817`/`:846` deliberately pass the raw `id` to
  `txn_write()`/`txn_delete()`, because `txn_read`/`txn_write`/`txn_delete`/
  `clear_parent` all match the cache against the id the BASIC statement used.
  The mapping belongs only at the point of contact with the disk — the two
  `op_txncmt()` arms — which is where this went.
- **A2 — map failure raises the arm's own error, not a silent skip.** It cannot
  fire (both entry points validate before caching) but a silent skip is the null
  case the instrument rules refuse.
- **A3 was more than "test `remove()`".** The plan named only the discarded
  result; the record adds the `S_IFREG` device-name guard, so the arm now matches
  its non-transactional twin exactly.
- **A4 needs no `op_sys.c` edit.** `op_sys.c:336` merely reads `txn_depth`;
  fixing the decrement makes `SYSTEM(1008)` balanced. The plan's `op_sys.c:335`
  reference is the read site, not an edit site.

**Objection raised and resolved (CLAUDE.md rule):** placing `end_txn_level()`
before `exit_op_txncmt:` means the five `k_error()` paths do **not** pop the
level — correct, a broken commit must not pop as though it committed. That leaves
a **pre-existing** gap: on those error paths `process.txn_id` was zeroed at the
top, so `txn_abort()`/`op_txnrbk()` find nothing and the level stays counted with
the stack orphaned. This third does **not** widen it (the directory-file delete
could not fail before A3, and now can, reaching that state more often — the trade
is deliberate: the alternative is reporting a deletion that did not happen). The
gap is `A1`'s to close, because it needs a decision about the records already
written, not a decrement.

**Cheap checks, none run:**

| Fix | Check |
|---|---|
| A2 write | inside a transaction, `WRITE rec ON dirfile, ','` then `COMMIT`, then `READ … FROM dirfile, ','` — must read back. On disk the file is `%C`, not `,` |
| A2 delete | inside a transaction, `DELETE dirfile, ';'` then `COMMIT` — `%Y` must be gone, and a later `READ` must return not-found |
| A3 | make a directory-file record's on-disk file read-only, delete it inside a transaction — the commit must now report the error, not succeed silently |
| A4 | outer txn writes `R2`, inner txn writes `R3` and commits, outer commits — both `R2` and `R3` must land; `SYSTEM(1008)` balanced across the pair; `SYSTEM(1007)` names the parent after the inner commit |

## Step 2, final third — A1, commit rollback, 9 Sep 2026

The one real piece of work in step 2. **Clean `rm -f gplobj/*.o` build: 0 errors,
0 warnings; `txn.o` and `op_dio3.o` recompiled, `sd` linked. NOT exercised** —
the undo only fires on a commit that fails part way, which needs an induced
failure (a read-only record file, or a record a second session holds) and was
not staged. Verified against UPSTREAM_FIXES 32.

Two halves, both landing in `txn_abort()` (the far side of the `k_error()`
longjmp, since `op_txncmt()`'s `goto exit_op_txncmt` paths are dead code):

| | Where | Fix |
|---|---|---|
| A1 undo | `txn.c` `capture_undo`/`replay_undo`/`free_undo` + `TXN_UNDO` stack | `capture_undo()` reads each record's before-image in the commit loop, immediately before the action; `replay_undo()` writes them back in reverse from `txn_abort()` if the commit longjmps; `free_undo()` drops them on success. Summary line to `errlog` either way |
| A1 locks | `txn.c:txn_abort` + `op_txncmt` | `txn_abort()` releases `commit_txn_id`'s locks (nothing did, so a failed commit held them for the life of the process); `op_txncmt()` clears `commit_txn_id` on success so a later unrelated abort cannot unlock a reissued id |
| groundwork | `op_dio3.c` `dir_read()` + `t1_unmap_chunk()`; `sd.h` prototype | the directory code had a write API and no callable read API; `dir_read()` is shaped like `dir_write()`. The newline→field-mark conversion is lifted out of `read_record()` into shared `t1_unmap_chunk()` so a capture cannot reverse it differently from an ordinary read |

**Deliberately different from the Windows port, and why:**

- **`t1_unmap_chunk()` is LF-only here.** The port folds CR/CRLF (Windows text
  files); this tree's `read_record()` only ever converted `\n`, so the extracted
  helper carries exactly that and no `cr_pending` state. Sharing the *identical*
  body with `dir_read()` is the whole point — a capture that unmapped marks even
  slightly differently would restore the wrong record, silently, on the failure
  path.
- **`process.status`/`os_error` are `int32_t` in this tree** (the port's saved
  locals were `int16_t`); `capture_undo()`'s save/restore locals match, so no
  truncation.

**Refcount checked, not assumed:** `dh_read` returns `ref_ct 1` (its `op_read`
descriptor path assigns without incrementing, unlike the cache path which does
`++`), and `dir_read`'s `ts_terminate()` sets the head chunk `ref_ct = 1`
(`strings.c:467`). So `TXN_UNDO` owns the single reference and `free_undo`/
`replay_undo` decrement it to 0; empty records (`NULL` str) and the not-found
case are guarded.

**Still open after A1** (the pre-existing gap the A4 comment named): on a commit
that fails, the transaction *level* stays counted and its cache stays orphaned on
`txn_stack`, because `process.txn_id` was zeroed at the top of `op_txncmt()` so
`op_txnrbk()`/`txn_abort()`'s `while` finds nothing. A1 closes the locks and the
records; the level/stack cleanup is a separate decision and was not taken.

**Cheap checks, none run:**

| | Check |
|---|---|
| undo | force a commit to fail on its 2nd of 3 writes (make the 2nd record's file read-only, or lock it from another session). Expect: R1 restored to its old value, R3 never written, an `errlog` line `… N restored, M removed, K could not be undone` |
| undo (create) | a transaction that *creates* a record then fails — the created record must be gone, not left half-written |
| locks | after such a failed commit, a second session must be able to lock/read the records — before A1 they stayed locked until the first session died |
| dir_read | as groundwork, an ordinary `READ` from a directory file must still read back byte-for-byte (the shared `t1_unmap_chunk` must not have changed normal reads) |

## Step 3 — build correctness (D5, J4, D6), 9 Sep 2026

Ported the Windows port's header generator and switched off the in-compile
build tools. **Not exercised on a running system** — an install would confirm
error text now displays; the reasoning below is why the risk is low.

| | Where | What |
|---|---|---|
| D5 | `gplbld/gen_includes.py` (new) | ports the Windows generator verbatim (only the header comment and a case-insensitive `sdsys` sub-dir resolver differ). Generates `SYSCOM/ERR.H`, `GPL.BP/ERRTEXT.H`, `GPL.BP/REVSTAMP.H`, `GPL.BP/OPCODES.H` from `gplsrc/{err,revstamp,opcodes}.h`; `--check` writes nothing and exits non-zero on drift |
| D5 | the four generated headers | regenerated. Every SDEXT/crypto/Python/EUID error `$define` went from C spelling + wrong (positive) sign to SD spelling + correct negative sign (e.g. `SD_Mem_Err 10100` → `SD$Mem.Err -10100`); `ERRTEXT.H` gained message text for all the previously-textless codes |
| J4 | `Makefile:70`, `:166` | `all: check-includes sd`; `check-includes` runs `gen_includes.py --check`. Drift is now a build failure |
| D6 | `GPL.BP/ERRTEXT:33`, `GPL.BP/APISRVR:62-63` | the `$execute 'RUN … ERRGEN'` / `REVSTAMP` directives commented out, matching `CPROC:131-132`. They read `./gplsrc` (dev-tree only) and ERRGEN truncates `ERR.H` before regenerating — a compile on an installed tree could wipe the error definitions |

**The instrument, and why it is trusted:** `--check` before regenerating
reported `OPCODES.H` **byte-for-byte in sync** and the other three STALE. The
in-sync `OPCODES.H` is the control — it proves the port reproduces the BASIC
generators exactly (the same translation feeds all four), so the three STALE
results are real drift, not a porting artefact. After regenerating, `--check`
is clean (exit 0) and `make` runs it.

**Why the rename is safe:** grep of `GPL.BP`/`SYSCOM` finds **no BASIC reference
to any renamed error define** — the codes flow as numbers and `ERRTEXT.H` maps
number→text; the only `SD_EUID_*` hits are the *key* names `SD_EUID_SET`/
`_RESTORE` (102/103 in `KEYS.H`), which are a different thing and untouched.

**Deliberately different from the port:** output dirs are upper-case here
(`GPL.BP`, `SYSCOM`) pending the lower-case migration, so the generator resolves
the `sdsys` sub-directory case-insensitively rather than hard-coding `gpl.bp`.
`OPGEN`'s BASIC source still exists (its removal is step 4 §G3); the generator
already covers `OPCODES.H`, so removing it later loses nothing.

**Regenerating rewrites a timestamp line** in each output (`* Generated by … at`),
which `--check` ignores but a write refreshes — so a manual regenerate always
dirties the four files even when content is identical. The build only ever runs
`--check`, which is timestamp-blind, so this does not dirty ordinary builds.

**Cheap checks, none run:**

| | Check |
|---|---|
| D5 | on an installed system, trigger a Python or crypto error and confirm the message text shows, not a bare number |
| J4 | edit `gplsrc/err.h`, run `make` — it must fail at `check-includes` until `gen_includes.py` is run |
| D6 | compile `ERRTEXT`/`APISRVR` in the bootstrap — must succeed without running ERRGEN/REVSTAMP (the tracked `.H` files are current) |

## Step 4 — the shrink (in progress), 9 Sep 2026

One release (L1.0-0). Removing subsystems named in the project stance. Ordered
so the VOC-touching ones go together; TAPE was independent and went first.

| | What | Done? |
|---|---|---|
| I1 | TAPE/RESTORE: deleted `sd64/tape/` (24 records — 5 `GPL.BP`, 19 `VOC` verbs) and the install prompt at `installsdai.sh:475`. It was copied in at install from `tape/`, never shipped in `VOC_TEMPLATE`, so nothing else referenced it (grep confirmed). `bash -n installsdai.sh` clean | **done** |
| I3 | SED — `GPL.BP/SED` + `VOC_TEMPLATE/SED` + `NEWVOC/SED`. **Its "key file" is `&SED.BINDINGS&`, created per account at run time and never shipped, so there was nothing to delete.** SED's own messages `6694`/`6695` kept, as the port kept them | **done** |
| I4 | UPDATE.RECORD — `GPL.BP/UPDREC` + `VOC_TEMPLATE/UPDATE.RECORD` + `NEWVOC/UPDATE.RECORD` | **done** |
| I5 | MODIFY — `GPL.BP/MODIFY` + `VOC_TEMPLATE/MODIFY` + `NEWVOC/MODIFY` | **done** |
| I2 | PROC — `GPL.BP/PROC` and `LISTPQ` in all three places (`SD.VOCLIB`, `VOC_TEMPLATE`, `NEWVOC`). PROC is a VOC record **TYPE**, not a verb, so it has no VOC record of its own. `CPROC`'s `PQ` case is **replaced, not deleted** — it refuses by name with new `MESSAGES/10099`, the port's number and its wording. **`OP_PROCREAD`, `op_procread()` and BCOMP's `st.procread`/`st.procwrite` are KEPT** (owner's ruling, 9 Sep — see below). `proc.*` SYSCOM slots kept | **done** |
| G1 | SDSYS `BP` test programs: removed 18 (`BIGSTR_TEST`, `MSGTEST`, `PCL`, `PCL.GRID`, `PCODE_LIST`, `SDTEST_V8`, `SD_ENCRYPT`/`_B64`/`_EXT`, `SD_EXT`, `TEST.THEN.ELSE`, `TESTSZ`, `U0032`, `U50BB`, `VFS.CLS`, `pref_t`, `sdTests`, `tilde_test`). **Kept `PY_JSON`/`PY_TERM`/`PY_TEST`/`PY_TEST2`** (owner decision 9 Sep — the documented examples for the kept Python feature). Verified no VOC verb dispatches to the `BP` dir and no bootstrap program names them; the `PCL` name-collision is with the `GPL.BP/PCL` printer subsystem (a different dir, stays) — `NEWVOC/PCL` is only a printer keyword. No changelog entry (SDSYS dev cleanup, no product function) | **done** |
| G2 | VFS scaffolding: the BASIC advertised a virtual file system the C never implemented. Removed `VFS_FILE` 5 (`descr.h`), `SEL_VFS` (`dh.h:154`), `FL_TYPE_VFS` (`keys.h:57`) and the three uses — `op_dio3.c:509` guard, `kernel.c:600` flag test, `pdump.c:227` print. **RETIRED, comments left in place: `DHF_VFS` 0x40 (`dh.h:105`, a file-header bit), `PF_IS_VFS` 0x00200000 (`kernel.h:101`, an object-header bit), errors 3038–3040 (`err.h:147`).** BASIC: `FTYPE`'s `VFS:` case, `_VOC_REF`'s branch that left a `VFS:` pathname relative, `FL$TYPE.VFS` (`SYSCOM/KEYS.H:29`); `ERR.H`/`ERRTEXT.H` regenerated. `GPL.BP/_EXTENDLIST` deleted with its four registrations (`pcode.h:38`, `gplbld/pcode_bld.py`, `gplbld/COMP_PCODE`, the record). **Left alone by ruling: `examples/windows.c/winsdclilib/err.h`** — the client library's public error header, so removing codes there is an API change. Clean `rm -f gplobj/*.o` build, 79 files, 0 warnings; 12 removal checks each against a control. **Not installed** | **done** |
| G3 | OPGEN: deleted `GPL.BP/OPGEN` (no VOC, no `$execute`, nothing calls it — superseded by `gen_includes.py`, whose `OPCODES.H` output is byte-identical, proven in step 3). Updated the two "generated using OPGEN" comments (`bbcmp.py:138`, `BCOMP:58`) to name `gen_includes.py`. No changelog entry — no user-visible effect | **done** |
| G4 | SDNet: deleted `gplsrc/netfiles.c` (removed from `gpl.src`), the `;` dispatch + `net_open` in `op_dio1.c`, and **every `NET_FILE` case / `net_*` call across `op_dio1/2/3/4.c`, `op_lock.c`, `dh_ak.c`** (~30 sites); removed the `NET_FILE` type (`descr.h`, `FVAR.NET` in `DEBUG.H` + the "(Networked)" DEBUG arm), the `net_*` prototypes (`sd.h`), and the 3 verbs (`GPL.BP/SETSRVR`/`DELSRVR`/`LISTSRVR`, `VOC_TEMPLATE/SET.SERVER`/`DELETE.SERVER`/`LIST.SERVERS`). `K$GET.SDNET.CONNECTIONS` now returns empty. **Kept (deliberate residue): `sdnet.h` (socket/termios portability header, NOT SDNet — build breaks without it), `NETFILES` config + sysseg field, `USR_SDNET`, `K$SDNET`, `SrvrOpenSDNet`.** Clean `rm -f gplobj/*.o` build; installs and runs at `2b4d9f0`; read side observed (`SELECT`/`LIST`/`COUNT VOC`). **CLOSED 9 Sep** (owner) — write/delete/lock accepted on conformity, not measured | **done** |

**Not exercised.** I1 removed data records and an install prompt; nothing in the
C build depends on them, so `make` is unaffected, but an install that used to
offer the TAPE prompt has not been re-run.

**G2's checks.** 12 removed/control pairs, every control fired: the four C
`#define`s against `SEQ_FILE`/`DHF_NOCASE`/`SEL_DH`/`PF_IS_TRIGGER`, the two
BASIC ones against `FL$TYPE.SEQ`/`ER$ENCRYPTED`, `'VFS:'` in `FTYPE` and
`_VOC_REF`, and `_EXTENDLIST`'s four registrations against `_DELLIST`.
**Anchored on `^ *\$define` / `^#define`, not the bare name** — Windows
HISTORY.md ~611 records that version reading its own removal comments as hits.
One check ran on the artefact rather than the source: `strings bin/sd` finds
`VFS handler` 0 against `Is trigger` 1.

***WHAT NONE OF THAT REACHES: `sd` HAS NOT STARTED FROM A PCODE LIBRARY BUILT
WITHOUT `_EXTENDLIST`.*** That is G2's one failure mode with teeth, and it is
loud rather than silent — `load_pcode()` (`sd.c:597`) prints *"Pcode item ... not
found"* and refuses to start if a `Pcode()` entry has no library object. Read
rather than assumed: it matches on `obj->ext_hdr.prog.program_name`
(`sd.c:620`), so entries are found **by name and removing one shifts nothing**,
and `bin/pcode` is concatenated strictly from the `pcode_fs` list
(`pcode_bld.py:144`), so dropping the name drops the object. All four
registrations went together. **An install is what would witness it.**

**Two objections raised against G2 in-session and resolved, recorded per
CLAUDE.md:**

- **Why `SEL_VFS` and `FL_TYPE_VFS` were deleted outright while `DHF_VFS` and
  `PF_IS_VFS` were retired.** The first two are in-memory only — a select-list
  type index and a `FILEINFO` return value — so a future feature may have the
  numbers. The second two occupy bits in a *persisted* header (`dh.h:98` says
  the LS 16 bits come from the file header; `kernel.h`'s LS 16 come from the
  object header), and a file or object written by another MultiValue
  implementation could carry them. Same reasoning the port used.
- **An in-place upgrade leaves stale copies behind.** `GPL.BP/_EXTENDLIST` and
  `PCODE.OUT/_EXTENDLIST` are not deleted from an existing `/usr/local/sdsys` by
  the installer, which copies over rather than clearing. Harmless — nothing
  looks either up, and `bin/pcode` is rebuilt from the list — but **the
  installed tree will not match the source tree** until a clean install. The
  Windows port did not face this: its upgrade writes `Type: filesandordirs` and
  deletes the whole directory first.

### Step 4 / §I — where the plan was wrong, and what was not checked

***THE PLAN'S §I2 IS WRONG IN THREE PLACES AND THE RECORD CAUGHT ALL THREE
BEFORE ANYTHING WAS DELETED.*** This is the grep-the-record rule paying for
itself; each was then confirmed against source rather than taken on the
document's word.

| Plan says | Measured |
|---|---|
| "`GPL.BP/PROC` and `GPL.BP/BBPROC` (the PROC compiler)" | ***`BBPROC` IS NOT PROC.*** Its own first line reads *"BootStrap Build process … a mini command processor … compile from source the basic programs needed by sd to run"*. It is one of `bbcmp.py`'s three bootstrap seeds (`installsdai.sh:491`). **Deleting it would have broken every install.** Windows HISTORY.md:31800 says it in one line: *"`QPROC` and `BBPROC` are not PROC despite the names"* |
| "`installsdai.sh:500` is one of three bootstrap compile steps and goes with it" | Line 500 is `chown -R sdsys:sdusers`. The three `bbcmp.py` steps are 491–493 and compile `BBPROC`, `BCOMP`, `PATHTKN` — **none is PROC. The installer needed no change at all** |
| "Retire the opcode … as the port did" | **The port kept `OP_PROCREAD`** — `opcodes.h:516` and `op_misc.c:1208` carry it in `sd4windows` today. The plan cites the port as its authority for the opposite of what the port did |

***OWNER'S RULING, 9 Sep 2026: KEEP `PROCREAD`/`PROCWRITE`, MATCH THE PORT.***
So §I2 is BASIC-only and **no C file was touched**. Three measurements backed
the question: the port kept them; `op_procread()` (`op_misc.c:1226`) already
self-guards by walking the call stack for a program named `$PROC` and returning
empty plus error status when it is absent, so with `GPL.BP/PROC` gone it answers
correctly with **no C change**; and `PROCWRITE` has no opcode at all — `BCOMP`
compiles it to a store into `SYSCOM.PROC.IBUF`, and those common slots must stay
because removing one shifts every slot after it.

**Four near-miss names, each checked and each kept** — the first three are the
port's list, the fourth is new here: `QPROC` (query processor) · `PDBG`/`PDEBUG`
(PHANTOM debugger, not PROC's) · `_KEYEDIT`/`KEYCODE.H` (`OP_KEYEDIT` is a BASIC
opcode, `opcodes.h:441`, and `_BINDKEY`, `_KEYCODE` and `BCOMP` reference them,
so they are not orphaned by SED/UPDREC going) · **`ST.MODIFY` in `bbcmp.py:5826`
and `BCOMP` is the BASIC `MODIFY btree, data` statement, nothing to do with the
`MODIFY` verb.** `MODIFYA` is reached by `VOC_TEMPLATE/MODIFY.ACCOUNT` → `$MODIFYA`,
a different catalogue name from the deleted `$MODIFY`. All nine were asserted
present after the deletions, as controls on the `git rm`.

***THE BASIC WAS NOT COMPILED THIS SESSION, AND THE INSTRUMENT THAT WAS TRIED
COULD NOT DO IT.*** `gplbld/bbcmp.py` cannot compile `CPROC`: it aborts on
`$IFNDEF`, which `CPROC` uses, and before that it fails to resolve
`$include define_install.h` because **`bbcmp.py:7141` upper-cases every include
name** and the file on disk is lower case. It is the restricted bootstrap
compiler for `BBPROC`/`BCOMP`/`PATHTKN` only. So the check that stands is
structural: `begin case`/`end case` **31/31 unchanged**, `loop` and `repeat`
each down by exactly **1** — the single pair removed from the `PQ` arm. **The
install's two-stage bootstrap is what compiles `CPROC`, and a syntax error there
aborts the install**, which is the loud failure this is relying on.

***AND THAT `bbcmp.py` UPPER-CASING IS A §M TRAP WORTH KEEPING.*** On a
case-sensitive filesystem an include whose file is lower case is unresolvable to
that compiler. The real `BCOMP` evidently resolves it, since installs work — but
§M1's "fold, then rename" has a second lookup here that the plan does not name.

## Open

***RELEASE-BLOCKING: §M, THE LOWER-CASE CONVERSION.*** Owner's ruling, 9 Sep
2026 — later in the port is fine, **by the end is not optional**. Scheduled at
step 7 with §N, per the plan; the reasoning and the two dependencies are in the
step-4 note above. `M1`'s fold (the colon prompt and query language, and BASIC
`OPEN` including Q-pointers — order **as typed, then lower case, then upper
case**) has no dependency on `update.accounts` and may be started at any time.
Known traps: `M2`'s both-spellings-exist guard must **refuse, not guess**;
`git mv` may need a two-step for a case-only rename, verified with
`git ls-files` rather than by looking at the working tree; and
**`bbcmp.py:7141` upper-cases every `$include` name**, which is a third lookup
the plan does not name (found 9 Sep — see the §I note).

**Exercise the step 1 fixes.** The table above lists the check for each. `D3` and
`B1`/`B2` are minutes of work on the installed system and are the two most worth
doing, because a wrong catalogue gate would refuse an administrator.

**Exercise step 2 — all of it (`A1`–`A6`).** Committed and compiled, none run.
The check tables are under each step-2 section. `A1`'s undo is the one that needs
an *induced commit failure* to reach at all.

***STEP 2 IS WHERE "IT COMPILED" IS WORTH LEAST.*** Every item touches
transactions or index structure; `A5`'s failure mode is a permanently damaged
index and `A1`'s is a half-applied commit, both silent. Build a way to exercise
a fix before making it, not after — that discipline was not met for step 2, which
is the standing risk to retire before step 4's removals bury it.

**Next planned work is step 3 (`D5`/`J4`/`D6`), in START HERE** — the `ERR.H`
generator, which also closes the drifted-header gap below.

**Guards ported from the Windows version — surveyed 9 Sep 2026, owner's ask.**
The survey is recorded so it is not repeated: the port has **1** Claude hook and
**170** `gplbld` scripts (157 `.ps1`, 13 `.py`).

- ***THE CLAUDE HOOK WAS ALREADY HERE AND IS ALREADY IDENTICAL.***
  `.claude/hooks/no-program-edits.py` and `.claude/settings.json` are
  **byte-identical** to the port's, `python` resolves at `/usr/bin/python` so the
  settings command is not silently taking its `|| exit 0` branch, and
  `--selftest` reports **32 cases (14 deny, 18 allow), 0 failed**. It also fired
  for real this session, on an inline `python -c` writing a scratch fixture.
  There were no user-level or `settings.local.json` hooks in either project, and
  no active git hooks in either.
- **`gplbld/check-msglen.py` is ported, byte-for-byte.** Does a message fit
  `k_error()`'s buffer once `sysmsg()` expands it. **Copied rather than adapted
  because all four constants were checked against this tree first and all four
  match** — `MAX_ERROR_LINES` 3 / `MAX_EMSG_LEN` 80 (`sddefs.h:124-125`), the
  buffer declaration and 10-byte `"%08X: "` prefix (`k_error.c:160,212`), the D1
  `sizeof(s) - n` fix (`k_error.c:226`), and the `\n`→LF+CR substitution
  (`messages.c:337-340`). **It hard-codes the bound 231 and will not notice if
  those change**, which its header now says.
- **Run on `MESSAGES/10099`, added this session: 165 rendered against a bound of
  231, 3 escapes, exit 0.** The instrument was shown to discriminate rather than
  merely pass — an over-long fixture gives `fits: False` exit **1**, and one with
  no escapes is **REFUSED** at exit **2** rather than passing. *Worth knowing:*
  10099 renders as **4 lines where `k_error` is sized for 3**, which is not a
  fault here because `CPROC` shows it with BASIC `display sysmsg(...)` rather
  than raising it through `k_error()`; the port ships the same 4-line text.
- **Examined and NOT ported, each for a stated reason** — do not redo this:
  `stage.py` and `bootstrap.py` build a Windows *installer*; here
  `installsdai.sh` bootstraps on the target machine · `checksyntax.py` /
  `mkbasicsyntax.py` are `micro`-editor syntax tooling — **and whether `micro`
  belongs in this port at all is now `PRE_RELEASE` 2, not settled** ·
  `mkvocdoc.py` is coupled to `sd.iss` and the port's 26 Aug CONFIG-display
  decision · the other 157 are `.ps1`, **of which only 51 are on subjects §H
  excludes — the remaining 31 relevant ones are `PRE_RELEASE` 1.**
- ***`check-stale-leads.py`: THE NOTE HERE OF 9 Sep WAS WRONG TWICE AND IS
  CORRECTED.*** It said the script refuses at its line 637 for want of
  `PRE_RELEASE_FIXES.md`, and that a verbatim copy would be *"a silent no-op"*.
  **Both were read off the source rather than measured.** That file now exists,
  and the script still cannot run: copied verbatim it exits **2 before any
  phase** — *"could not bound section 7"* — because the entry-boundary machinery
  every phase depends on is built from the port's headings. And it is **not
  silent**: it refuses loudly, as the port designed it to. The unadapted copy was
  removed rather than committed. Scope of the real work is `PRE_RELEASE` 9.

**Standing gaps:**

- **No `assert-current` equivalent.** Nothing refuses to run a check against an
  install older than its source, so a green result can come from the previous
  build. This matters more from step 2 on, where a wrong answer is silent.
  **The port's is `gplbld/assert-current.ps1` — PowerShell, so this is a rewrite
  and not a copy**, which is why the 9 Sep survey above did not close it.
- ~~**Two generated headers drifted.**~~ **CLOSED 9 Sep 2026** — see "Step 3"
  below. `gplbld/gen_includes.py` regenerates `SYSCOM/ERR.H`,
  `GPL.BP/ERRTEXT.H`, `GPL.BP/REVSTAMP.H`, `GPL.BP/OPCODES.H` from the C
  headers; `make` runs its `--check` first, so drift is now a build failure.
- **`sdsys/MESSAGES` still lacks records `4100`, `4101`, `-10303`** (plan §D5).
  That is the runtime message file, not generated from `err.h`, so the generator
  does not touch it; adding those three is a separate deliberate data edit.

**Undecided:**

- `AI_Modification_Notes.zip` is a redundant archive of `AI_Modification_Notes/`,
  which is tracked. It is in `.gitignore` for now rather than deleted; deleting it
  is probably right.
