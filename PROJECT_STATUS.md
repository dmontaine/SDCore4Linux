# PROJECT_STATUS.md

Handoff document for SD Core for Linux. See [CLAUDE.md](CLAUDE.md) for how to
maintain it: terse, `file:line` over description, updated in the same commit as
the work, nothing in "Verified" that was not observed that session.

## START HERE

*Handoff updated 9 Sep 2026. Steps 2 and 3 implemented, neither exercised on a
running system. Step 4's §G is complete; `G2` is built but not installed.*

**The plan is `/home/don/Documents/claude_plan.md`** (and `.pdf`), outside the
repository, with a `file:line` verification table for every defect it claims.
Work follows its "Suggested order". **Steps 0–3 are done; nothing in steps 2–3
has been exercised on an installed system.**

### Your next task

**Step 4 — the shrink, IN PROGRESS.** See "Step 4" below. Done: `I1` TAPE, `G3`
OPGEN, `G1` BP test programs (PY_* kept), `G4` SDNet, `G2` VFS. **All of §G is
done.** Remaining is the VOC-coherence set as **one pass**: `I3` SED · `I4`
UPDATE.RECORD · `I5` MODIFY · `I2` PROC. `I2` is the deep one — compiler +
opcode `OP_PROCREAD`, report "PROC not supported" at `CPROC:1530`, RETIRE the
opcode slot. Fold in the lower-case migration here.

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
- `G2`: `sd` has not started from a pcode library built without `_EXTENDLIST`.
  Loud rather than silent if wrong — `load_pcode()` refuses to start — so the
  next install witnesses it. See the Step-4 note.

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
| I3 | SED — `GPL.BP/SED`, `VOC_TEMPLATE/SED`, its key file | pending |
| I4 | UPDATE.RECORD — `GPL.BP/UPDREC`, `VOC_TEMPLATE/UPDATE.RECORD` | pending |
| I5 | MODIFY — `GPL.BP/MODIFY`, `VOC_TEMPLATE/MODIFY`. **Keep `MODIFYA`, `MODIFY.PASSWORD`** | pending |
| I2 | PROC — `GPL.BP/PROC`+`BBPROC`, `bbcmp.py` compile step + `installsdai.sh:500`, `LISTPQ`, `OP_PROCREAD`/`op_procread()` + BCOMP, `CPROC:1530` dispatch. Report "not supported" at dispatch; RETIRE the opcode | pending |
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

## Open

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

**Standing gaps:**

- **No `assert-current` equivalent.** Nothing refuses to run a check against an
  install older than its source, so a green result can come from the previous
  build. This matters more from step 2 on, where a wrong answer is silent.
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
