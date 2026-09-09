# PROJECT_STATUS.md

Handoff document for SD Core for Linux. See [CLAUDE.md](CLAUDE.md) for how to
maintain it: terse, `file:line` over description, updated in the same commit as
the work, nothing in "Verified" that was not observed that session.

## START HERE

**The plan is `/home/don/Documents/claude_plan.md`** (and `.pdf`), outside the
repository. It carries a verification table with `file:line` for every defect it
claims. Next work is step 1 of its "Suggested order"; step 0 is done, below.

**Pushed to GitHub 8 Sep 2026.** `main` tracks `origin/main`; local and remote
both at `e5ceb16`, verified with `git ls-remote` and `git rev-parse` after the
push. The canonical remote is `git@github.com:dmontaine/SDCore4Linux.git` —
**capitalised**; the lower-case form works only via a redirect that prints
"This repository moved" on every push.

Renamed from `sdscripts_ai` to `sdcore4linux` on 8 Sep 2026. Git identity is set
**repo-local** (`.git/config`, `dmontaine@gmail.com`); there is no `~/.gitconfig`
on this machine, so other repositories will still ask.

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

**Partly observed since.** `make sd` was run this session after deleting four
`.o` files: it recompiled them, relinked `bin/sd`, and reported 0 errors and 0
warnings. ***THAT IS AN INCREMENTAL BUILD, NOT A FROM-SCRATCH ONE.*** A fresh
clone plus `make`, producing a working `bin/sd` and a repopulated `terminfo/`,
is still the test that would close this.

**Other observations this session:**

- `.claude/hooks/no-program-edits.py --selftest` → 32 cases, 0 failed, run from
  this directory.
- `ssh -T git@github.com` authenticates as `dmontaine`, key `~/.ssh/id_ed25519`.
- No file in the mode set was a script; `installsdai.sh` and `deletesdai.sh` keep
  their executable bit.

## Step 1 of the plan — all eight applied, 8 Sep 2026

The release is now **`L1.0-0`** and `sdsys/changelog` carries its section.

| | Where | Fix | State |
|---|---|---|---|
| D1 | `gplsrc/k_error.c:216` | size limit was `(LINES + LEN)+1` = 84 against a 241-byte buffer, and ignored the offset already written; now `sizeof(s) - n` | **compiles** |
| D2 | `gplsrc/op_skt.c:673` | `n = TRUE;` removed — it discarded the caller's keep-alive value | **compiles** |
| C1 | `gplsrc/clopts.c:300` | `process.user_no` → `user_no`; task locks were compared against the cleanup process, not the dead session | **compiles** |
| B4 | `gplsrc/sysseg.c:413` | guard `uptr->pid > 0` (and `sdlnxd_pid > 0`); pid 0 made `kill()` signal the caller's process group | **compiles** |
| B2 | `sdsys/GPL.BP/CATALOG` | one admin gate after the `end case`, covering the GLOBAL keyword *and* all three prefix routes | edited only |
| B1 | `sdsys/GPL.BP/DELCAT` | admin gate inside the branch that touches `gcat`; it had no check at all | edited only |
| D3 | `sdsys/GPL.BP/TERM` | `DEFAULT.WIDTH`/`DEFAULT.DEPTH` (120×36) instead of `MIN.WIDTH` and a literal 24 | edited only |
| E1 | `sdsys/VOC_TEMPLATE/ENCRYPT.FIELD` | removed; `$CRYPTO` is not in the distribution | removed |

**"compiles" means compiles.** `make sd` reported 0 errors and 0 warnings and
relinked `bin/sd`. ***NONE OF THE EIGHT HAS BEEN RUN.*** No install cycle was
done this session, so nothing here has been exercised against a live SD.

***THE FOUR BASIC CHANGES HAVE NOT EVEN BEEN COMPILED.*** `GPL.BP` is compiled by
the two-stage bootstrap during `installsdai.sh`, and there is no way to syntax
check it outside a running SD. A typo in `CATALOG`, `DELCAT` or `TERM` would not
show up until an install. **Run one before believing any of the bottom four
rows.**

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

## Open

**Next work — step 2 of the plan: data integrity.** `A5` `dh_ak.c:2750`
`get_ak_node()` returns 0 on error and no caller checks, so a failed index
extension writes over the index header; `A2`/`A3` the transaction directory-id
encoding in `txn.c:148,180,187`; `A6` unchecked `chsize64()` in
`op_seqio.c:752,1433`; `A4` nested commit; then `A1` commit rollback, the one
real piece of work.

**Before that, or with it: run an install.** Eight fixes are sitting uncompiled
or unexercised, and the plan's step 2 touches transactions and indexes, where
"it compiled" is worth very little.

**Standing gaps, from CLAUDE.md:**

- No equivalent of the Windows `assert-current` guard: nothing refuses to run a
  verification against a tree whose install is older than its source.
- `SYSCOM/ERR.H` is generated from `gplsrc/err.h` by hand and has drifted. So has
  `GPL.BP/REVSTAMP.H` from `gplsrc/revstamp.h` — `revstamp.h:36-38` says as much.
  Plan §D5/§J4 is the generator that ends both.

**Undecided:**

- `AI_Modification_Notes.zip` is a redundant archive of `AI_Modification_Notes/`,
  which is tracked. It is in `.gitignore` for now rather than deleted; deleting it
  is probably right.
