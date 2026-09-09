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

***THIS WAS READ FROM THE MAKEFILE, NOT OBSERVED BY RUNNING `make`.*** Per
CLAUDE.md, compiling is not running and reading is not either. **The first
session to run a build should confirm it and move this line to a stronger
claim** — a fresh clone plus `make` producing a working `bin/sd` is the test.

**Other observations this session:**

- `.claude/hooks/no-program-edits.py --selftest` → 32 cases, 0 failed, run from
  this directory.
- `ssh -T git@github.com` authenticates as `dmontaine`, key `~/.ssh/id_ed25519`.
- No file in the mode set was a script; `installsdai.sh` and `deletesdai.sh` keep
  their executable bit.

## Open

**Blocked on the owner:**

- The first push to `origin`.

**Next work — step 1 of the plan, all small and all with an exact location:**

| | Where | What |
|---|---|---|
| C1 | `gplsrc/clopts.c:300` | `== process.user_no` should be `== user_no` — one word |
| D2 | `gplsrc/op_skt.c:673` | `n = TRUE;` discards the caller's keep-alive value — delete the line |
| D1 | `gplsrc/k_error.c:216` | `(MAX_ERROR_LINES + MAX_EMSG_LEN)` should be `*` — one character |
| B2 | `sdsys/GPL.BP/CATALOG:143,156,170,180` | prefix routes set `CAT_GLOBAL` without the admin check at `:104-106` |
| B1 | `sdsys/GPL.BP/DELCAT` | no privilege check anywhere in the program |
| B4 | `gplsrc/sysseg.c:413` | `kill(uptr->pid, SIGTERM)` with pid unvalidated; pid 0 signals the process group |
| D3 | `sdsys/GPL.BP/TERM:165` | `TERM DEFAULT` sets `MIN.WIDTH`, not the documented 120×36 |
| E1 | `sdsys/VOC_TEMPLATE/ENCRYPT.FIELD` | verb points at `$CRYPTO`, which is not in the distribution |

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
