# PROJECT_STATUS.md

Handoff document for SD Core for Linux. See [CLAUDE.md](CLAUDE.md) for how to
maintain it: terse, `file:line` over description, updated in the same commit as
the work, nothing in "Verified" that was not observed that session.

## START HERE

*Handoff written 8 Sep 2026, end of session. Tree clean, everything pushed.*

**The plan is `/home/don/Documents/claude_plan.md`** (and `.pdf`), outside the
repository, with a `file:line` verification table for every defect it claims.
Work follows its "Suggested order". **Steps 0 and 1 are done; step 2 is being
taken in thirds at the owner's request, and the first third is done.**

### Your next task

**Step 2, final third — `A1`, commit rollback.** The second third (`A2`, `A3`,
`A4`) is committed; see "Step 2, second third" below. `A1` is the one real piece
of work in step 2: before-images for every record a commit overwrites, restored
if the commit fails part way, with a summary line to `errlog`.

The Windows port has it built — `txn.c` there carries `capture_undo()`,
`replay_undo()`, `free_undo()`, the `TXN_UNDO` stack, and the `replay_undo()`
call at the head of `txn_abort()` (the far side of the `k_error()` longjmp).
UPSTREAM_FIXES 32 is the write-up; PRE_RELEASE_FIXES 102 the port. It also needs
one piece of groundwork the directory-file code lacks: a `dir_read()` shaped
like `dir_write()`, because the only current reader (`read_record()`) can only
be reached by executing a READ opcode and a commit cannot. **The lock half of
entry 32 travels with it** — `txn_abort()` releasing `commit_txn_id`, and
`op_txncmt()` clearing `commit_txn_id` on the success path — so `commit_txn_id`
becomes load-bearing (non-zero = "a commit is in flight") and gets an explicit
`= 0` initialiser. None of that was touched this session.

### ***BEFORE YOU IMPLEMENT ANYTHING, GREP THE WINDOWS RECORD***

Not a formality. It corrected the plan **twice in one session**, and both times
the fix would otherwise have looked complete and been wrong — see "Step 2, first
third" below for what it caught. `/home/don/Projects/SDCoreProject/sd4windows`
has `PRE_RELEASE_FIXES.md`, `UPSTREAM_FIXES.md` and `HISTORY.md`; the entries are
long, and the detail near the end of one is usually the correction.

```sh
grep -n -i -E 'txn\.c|dir_write|txn_id' /home/don/Projects/SDCoreProject/sd4windows/*.md
```

### State of the tree

- **Clean and pushed.** `main` tracks `origin/main`; remote is
  `git@github.com:dmontaine/SDCore4Linux.git` — **capitalised**, the lower-case
  form only works through a redirect that warns on every push.
- Renamed from `sdscripts_ai` on 8 Sep 2026. Git identity is **repo-local**
  (`.git/config`, `dmontaine@gmail.com`); there is no `~/.gitconfig`, so other
  repositories will still ask.
- ***THIRTEEN FIXES ARE COMMITTED AND NOT ONE HAS BEEN EXERCISED.*** The owner
  ran an install (of the first ten) and could log in, so that tree builds and
  runs — all it establishes. The three added this session (`A2`, `A3`, `A4`)
  compile and link; the install predates them. Per-fix checks are listed under
  step 1 and the second-third section; none has been run.

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

## Open

**Exercise the step 1 fixes.** The table above lists the check for each. `D3` and
`B1`/`B2` are minutes of work on the installed system and are the two most worth
doing, because a wrong catalogue gate would refuse an administrator.

**Step 2's remaining third (`A1`) is in START HERE.**

***STEP 2 IS WHERE "IT COMPILED" IS WORTH LEAST.*** Every item touches
transactions or index structure, and `A5`'s failure mode is a permanently
damaged index rather than an error. Build a way to exercise a fix before making
it, not after.

**Standing gaps:**

- **No `assert-current` equivalent.** Nothing refuses to run a check against an
  install older than its source, so a green result can come from the previous
  build. This matters more from step 2 on, where a wrong answer is silent.
- **Two generated headers are kept in step by hand and have drifted.**
  `SYSCOM/ERR.H` from `gplsrc/err.h` (wrong sign, C spelling, missing codes), and
  `GPL.BP/REVSTAMP.H` from `gplsrc/revstamp.h` — `revstamp.h:36-38` says so in a
  comment. Plan §D5/§J4 is the generator that ends both, and §N needs it.

**Undecided:**

- `AI_Modification_Notes.zip` is a redundant archive of `AI_Modification_Notes/`,
  which is tracked. It is in `.gitignore` for now rather than deleted; deleting it
  is probably right.
