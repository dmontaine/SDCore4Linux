# PROJECT_STATUS.md

Handoff document for SD Core for Linux. See [CLAUDE.md](CLAUDE.md) for how to
maintain it: terse, `file:line` over description, updated in the same commit as
the work, nothing in "Verified" that was not observed that session.

## Status roll-up (10 Sep 2026)

**Keep this current when an entry closes; it is a scorecard, detail lives in
`PRE_RELEASE_FIXES.md` and below.**

- **PRE_RELEASE entries — 27 total: 15 done · 1 partial · 11 open.**
  - Done: `2, 8, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27`
  - Partial: `24` — installer seeds the admin (witnessed); the non-sudoer
    refusal at `installsdai.sh:236` (**24(2)**) is unrun.
  - Open: `1, 3, 4, 5, 6, 7, 9, 10, 11, 15, 16` — a mix of real work and notes.
    `1`/`15` are informational; `6` = step-2 fixes compiled but unexercised.
    **10 Sep: `3` ruled (EDIT = ED alias) and `4` superseded (port EDIT adopted)
    — both struck; the counts above predate that.**
- **Plan steps: 1–4 done.** Step 7 (§L1 + §M) is the remaining release-blocking
  block.
- **Release blockers:** ***§M*** — the lower-case conversion (= entry `7`),
  **not started**; ***§L1*** — the per-tier VOC, **core WITNESSED 10 Sep**
  (STANDARD tstd 368 records / no BASIC vs PROGRAMMER tprog 410 — Δ42 = the omit
  list; CREATUSR fix also witnessed); `LOGIN update.voc` tier filter and
  `MODIFYA` tier re-derivation **built + compiled 10 Sep (0 / red 3; 0 / red 9),
  unrun**; ADOPT still to build (Open section).
- **Parity audit vs the Windows port, 10 Sep:** 12 drifts corrected + compiled,
  **unrun**; key numbers renumbered so ***the tree `bin/sd` and GPL.BP must be
  installed together*** (Open, "Parity audit").
- **Goals (post-parity):** a **BASIC screen/widget library** — rich terminal
  admin apps / a terminal IDE, written in SD BASIC, GPL-clean, no dependency
  (owner, 10 Sep; design note in Open, stance in CLAUDE.md).
- **Runtime:** install built from `98b0c77` (hardened client lib witnessed over
  TCP 4243); HEAD then advances by documentation-only commits, so
  `assert-current` reads STALE while the shipped behaviour is current.

## START HERE

***⚠ 11 Sep 2026, ~03:45 — THE RUNNING SD IS WEDGED. REBOOT BEFORE RUNNING
ANYTHING, including `deletesdai.sh`. Caused by my overnight testing; measured,
not inferred.***
- `ipcs -s -i 0` (SD_SEM_KEY 0x716d0302): `ERRLOG_SEM`(1)=0 last op pid 36587,
  `REC_LOCK_SEM`(3)=0 pid 36509, `FILE_TABLE_LOCK`(4)=0 pid 36920. **36509 and
  36587 are dead** (processes I started; 36587 killed by me). 36920 is
  `/usr/local/sdsys/bin/sd -cleanup` as ROOT, launched by `sdlnxd` at
  03:44:06, holding FILE_TABLE_LOCK and spinning (state R) on REC_LOCK_SEM. Any
  new `sd` that opens a file spins the same way.
- **Chain, as observed:** (1) a record lock whose owner's slot is gone; (2)
  `LIST.READU` → `op_getlocks()` does `UserPtr(owner)->username` and
  `UserPtr()` is NULL for an unmapped user (`sysseg.h:192`) → **"Fault type 11"
  inside `$LISTRDU`**, while holding FILE_TABLE_LOCK + REC_LOCK_SEM; (3)
  `sdsem.c` takes semaphores with `IPC_NOWAIT` and **no `SEM_UNDO`** and the
  fault path does not release them, so they stay held for ever and every
  waiter busy-spins.
- **(1)'s cause is a HYPOTHESIS, untested:** my probe `OPENSEQ`'d a path that
  did not exist (`/proc/<dead pid>/status`), took the ELSE branch, and ended
  without `CLOSESEQ`; the next `OPENSEQ` of the same path (a later session)
  waited for ever. If an ELSE-branch OPENSEQ lock survives logout, its owner
  becomes unmapped. **Falsify after reboot:** run that sequence twice with a
  `timeout 10`, then `LIST.READU` under `timeout 10` — a second-run hang and a
  fault confirm it.
- **Not tonight's code:** `FL_HOLDERS` only reads; `reap_lost_user()` never ran
  (my LO16 probe exited on its own usage check before calling `logout()`).
- **Not done, deliberately:** resetting the semaphores myself. They are 0666 and
  both holders are dead, but a reboot is certain and complete, and a reset
  would leave the orphaned lock for the next LIST.READU to trip over.
- ***OVERNIGHT 10–11 Sep, END OF SESSION (credits).*** All commits LOCAL, none
  pushed. Built: PORT_ADOPTION queue 3, 3b, 4, 5, 6, 7, 8, 9, 10, 11, 20, 23,
  24, plus the `op_getlocks` NULL fix; the audit (186 + 37 entries) is done.
  Every BASIC change compiled 0 errors with a red control before the wedge.
  Witnessed on the tree binary: READSEQ CRLF (pre/post), the LOGIN
  terminal-type premise, the `!set_passwd` status premise, FL$HOLDERS. Status
  per item, with its witness command: PORT_ADOPTION "Built … while the owner
  slept". Decisions waiting: PORT_ADOPTION "Waiting for the owner" (0–4).
- **NEXT, in order:** reboot → `assert-current` → push → delete→install cycle →
  the witness column of that table → the reap witness (queue 10) and the
  orphaned-lock falsification above. Then the queue continues at 12
  (SUSPENDED), 13 (K$AUDIT), 14 (TIERGATE), 15–19, 21, 22, 25, and §M under
  the 11 Sep ruling.
- **A SANDBOX SD NOW EXISTS AS A RECIPE, and it is how to test without the live
  system:** a scratchpad copy of the build with `sddefs.h` keys changed to
  0x716d0901/0902 and `check_admin()` stubbed (scratch copy ONLY), a copy of
  `/usr/local/sdsys` and of the account, `ACCOUNTS/*` paths pointed at the
  copies, the other register records removed, and `SCARLET_CONFIG` (read by
  `inipath.c`) naming a private `sd.conf`. Witnessed: separate IPC keys, and
  the live semaphores unchanged by it; `WHO` `1 DON`, QSELECT runs. `-start`
  leaves stdout held by the daemon, so redirect it rather than pipe. The
  scratchpad does not survive the session; rebuild it from this note.
- ***TRAP, FOUND WHILE BUILDING IT: `gplbld/pcode_bld.py:15` HARD-CODES
  `/usr/local/sdsys` and WRITES `bin/pcode` THERE.*** Run outside the installer
  it overwrites the live pcode. Copy it and change the path for any other
  target.
- **After the reboot, clean my fixtures** (DON account): `rm -rf
  /home/sd/user_accounts/don/ZZ16 /home/sd/user_accounts/don/ZZ16.DIC
  /home/sd/user_accounts/don/BP/* /home/sd/user_accounts/don/BP.OUT`, then in
  `sd`: `DELETE VOC ZZ16`, `DELETE VOC BP.OUT`, `COUNT VOC` → 410.

***11 Sep 2026 — READ THIS BLOCK FIRST; what follows it is older. Opened on
`pull`; tree clean at `b0d4554`, `assert-current` = 0 (install built from HEAD
01:09, so kernel keys are ALIGNED again — the 10-Sep scratchpad harness for the
57–59→90–92 mismatch is no longer needed; a dev binary compiles GPL.BP straight
against the install).***
- **NEXT TASK is still `PORT_ADOPTION.md`'s queue, top down.** Its top two are
  now done in source: **queue 1** (QSELECT list-number, UPSTREAM 21) and
  **queue 2** (DELETE.INDEX case-fold, UPSTREAM 22). `QSELECT:231` now passes
  `tgt.list` as %2; `DELETEI` gained the LISTI-style case-fold block. **Both
  compiled 0 errors** (dev binary, staged in DON/BP, red control `QBAD` = 1
  error), DON restored to `COUNT VOC` 410, tree rebuilt PLAIN. Changelog + doc
  entries in the same commit.
- ***BOTH ARE NOW WITNESSED.*** The owner ran the delete→install cycle;
  `assert-current` = 0, install stamped `af879d3` 02:19:18. **QSELECT:**
  `qselect voc * saving 3` → `...select list 0`, `... to 2` → `...select list 2`
  (the number tracks the argument, 410 > 0 so not the null case). **DELETE.INDEX:**
  `delete.index zzak f1` (LOWER) → `Deleted index F1`, with control
  `delete.index zzak nosuchidx` → `Unrecognised index name (nosuchidx)`.
  Fixtures removed, `COUNT VOC` 410. Detail in PORT_ADOPTION "Adopted so far".
- ***QUEUE 3 (UPSTREAM 23) WAS REPRODUCED BY ACCIDENT AND IS WIDER THAN THE
  ENTRY SAYS*** — `delete.file zzak no.query` prompted on a PLAIN file (not the
  system-account path UPSTREAM 23 describes) and then BUSY-LOOPED on pipe EOF,
  98.9 MB in 40 s, process in state `R`. **Diagnosed on the source afterwards:**
  `no.query` IS parsed (`DELETEF:84`, honoured `:109`) but the DATA and DICT
  prompts (`DELETEF:221-232`, `:295-304`) are guarded by ***`not(force)`
  ALONE***, and each `loop … input yn … until yn='Y' or yn='N'` has no EOF
  escape (same shape `:112 :155 :187 :350`). So queue 3 is two fixes, not one.
  ***CORRECTED LATER THE SAME DAY: the first fault is the port's UPSTREAM 27,
  which PORT_ADOPTION had failed to list*** — an earlier line here said no entry
  named it. Only the EOF loop is in no UPSTREAM entry. Full note in
  PORT_ADOPTION, "Queue 3 — measured here". ***NOT FIXED — this is the next
  task.***
- ***§M RULED WIDER, 11 Sep 2026 (owner): LOWER CASE MUST BE COMPLETE, NOT THE
  PORT'S PARTIAL RESULT.*** Everything lower case — including the files
  `CREATE.FILE` makes and program/include names — with upper-case input converted
  on the fly, so no command, file or record id can exist in two casings. The port
  left `CREATEF:311`'s upcase, all of `gpl.bp`/`syscom`, `PT$INVERT`, and six VOC
  ids upper; NTFS hid it. Filed to the port as `BUGS_FROM_LINUX_PORT.md` 5
  (uncommitted there, like 1–4). Gap table and two UNRULED questions (users' own
  data record ids; account names) in PORT_ADOPTION "Queue 18". CLAUDE.md stance
  updated. **Nothing of §M is built.**
- ***IS THE PORT-ADOPTION AUDIT COMPLETE? NO — answered for the owner 11 Sep.***
  UPSTREAM_FIXES is now reconciled all 37 (28 done, 1 n/a, 8 open) — see
  PORT_ADOPTION "UPSTREAM_FIXES reconciliation"; 18 of them had been fixed on
  8–9 Sep under plan ids and never cross-referenced. ***The port's
  PRE_RELEASE_FIXES (186 rows) has NOT been walked entry by entry***, and this
  project's own open PRE_RELEASE entries are not in PORT_ADOPTION at all.
- **Instrument lesson, paid for twice this session:** ***DRIVING `sd` DOWN A
  PIPE IS ONLY SAFE FOR VERBS THAT DO NOT PROMPT, AND ALWAYS UNDER `timeout`.***
  `list.index` and `delete.file` each spun. A pty driver was tried and was worse
  (it captured the echo but not the results) — the plain pipe is the better
  instrument for non-prompting verbs. To remove a test file without the verb:
  `rm -rf <ACCT>/NAME <ACCT>/NAME.DIC` then `DELETE VOC name`.
- **Fixture recipe for an index witness** (there is no one-liner): a new file's
  dict has no field entries, so `create.index f f1` answers *"f1 is not defined
  in the dictionary"*. Write a D-type record — `1:'D' 2:<field no> 4:name
  5:'10L' 6:'S'` (`SYSCOM/DICTDICT.H`) — with a scratch BASIC program using
  `open 'DICT','<file>' to f`; an ordinary (non-`$internal`) program compiles as
  `don` with no dev build. ***`RUN BP <prog>` IS CASE-SENSITIVE*** — `run bp
  mkf1` answers "Program BP.OUT mkf1 not found" for an object filed as `MKF1`.
- **Compile recipe, simplified for the aligned-keys state:** `make
  EXTRA_C_FLAGS=-DSD_DEV_BUILD`; stage `<prog>` + the GPL.BP-LOCAL includes
  (`SYSCOM.H`, `INT$KEYS.H`, `AK_INFO.H` — the SYSCOM-resolved ones like `ERR.H`
  come via the account's VOC `SYSCOM` pointer) into `/home/sd/user_accounts/don/BP`;
  `bin/sd -internal BASIC BP <prog>`; read the TAIL (never grep `Compiled`);
  clean up `BP/*`, `DELETE VOC BP.OUT`; `rm -f gplobj/*.o && make` to rebuild
  plain. Red control = append an unbalanced bracket, NOT truncation.
- Next queue items (3 DELETE.FILE NO.QUERY, 5 LOGIN terminfo, 7 CPROC HELP) add
  new message records (10117/10149) and touch login/command paths — bigger than
  1/2, do them singly.

***END OF SESSION 10 Sep 2026 (credits ran low) — what follows is older.***
- **Commits, all pushed to `origin/main`:** `8a1b343` per-tier VOC (LOGIN,
  MODIFYA), MICRO fix, parity audit · `6f5bff8` DELETE.ACCOUNT REMOVE.HOME,
  Codeberg remote removed · `2d759f7` NANO/MICRO via the port's EDIT, nano
  highlighting · the session's last commit: port upstream C fixes + `PORT_ADOPTION.md`.
- ***NOTHING SINCE THE `1fa0e57` INSTALL HAS RUN ON AN INSTALL.*** Next: the
  delete → install cycle as `don`, no sudo (`deletesdai.sh`, then
  `installsdai.sh`), then the witness plans in Open: "Parity audit", "NANO and
  MICRO", REMOVE.HOME, §L1 LOGIN/MODIFYA.
- ***KERNEL KEYS 57–59 → 90–92: THE TREE `bin/sd` ABORTS AGAINST THE CURRENT
  INSTALL*** (`Illegal KERNEL() action key (58)`, measured). Until reinstall,
  compile GPL.BP with a harness: copy `sd64` minus `sdsys gplobj bin terminfo`
  to the scratchpad, copy `sdsys/GPL.BP` and `SYSCOM` in, overwrite
  `gplsrc/keys.h` with `git show dc05b88:sdb_ai/sd64/gplsrc/keys.h`, `make
  EXTRA_C_FLAGS=-DSD_DEV_BUILD` (log to an ABSOLUTE scratchpad path — the hook
  refuses a relative `.txt`), then `<harness>/bin/sd -internal BASIC BP <prog>`
  in DON's `BP`. Clean up `BP`, `BP.OUT`, `DELETE VOC BP.OUT` (`COUNT VOC` 410).
- **NEXT TASK: `PORT_ADOPTION.md`'s queue, top down.** Its "Not adoptable" table
  is the owner-requested list. Port defects are in the Windows port's
  `BUGS_FROM_LINUX_PORT.md` — pushed to GitHub `sd4windows` 11 Sep (`d746963`)
  from a fresh clone; the local `sd4windows` is a frozen comparison copy.
- **Last commit's C fixes** (UPSTREAM 1, 3, 8, 9, 10, 14, 18, 20, 29, 35; port
  PRE_RELEASE 174; plus sdtic's end-of-file path, a port defect): built clean.
  ***Witnessed pre-fix vs post-fix harness binaries:*** `CONFIG('NOSUCHKEY')`
  abort → `""`/1004; ids `draft%1`/`draft%` → both `draft` → whole (`%E`→`=`
  control unchanged); unlocked transaction WRITE `3023 (Possible full disk?)` →
  10151 branch (reads "Message not found" until an install ships 10151); sdtic
  bad fixture old 1 file exit 0 → new 2 files exit 1. **Compile-only:** 1, 3, 8,
  10, 14, 29, 174 — the sdrealpath probe did not compile (`OSPATH` is not a
  BASIC function here; find the right intrinsic).

***HEAD is `d791b4c` (origin/main, pushed 10 Sep 2026); the ssh tier boundary,
PRE_RELEASE 13, landed at `a6d96b1`: BUILT + pushed, unit-tested 16/0, `sshd
-t`-witnessed on this box — and now LIVE-ssh-WITNESSED 10 Sep 2026 (see step 3
below): a STANDARD account is forced into `sd`, an administrator gets a shell.
The delete→install cycle steps below remain the way to re-exercise it and to
witness 25/27.***

### Next: the delete→install cycle — witnesses 13, 25 and 27 at once

**Two scripts.** There is no unified script, and install REFUSES over an
existing install (`installsdai.sh:125`), so a cycle is delete then install. Run
both as `don`, **not** sudo — they elevate internally.

1. `/home/don/Projects/sdcore4linux/deletesdai.sh` — answer **Y** (keep
   accounts) and **Y** (keep configuration); answer **N** to its closing reboot
   prompt (`deletesdai.sh:297`) — a between-reboot is not needed for a keep
   cycle (groups and units unchanged). This keep-accounts path IS the upgrade,
   and it witnesses **25** (`sdadmin` survives holding `don`, no 10037 lock-out)
   and **27** (the `/home/sd` + `sd.conf` save path).
2. `/home/don/Projects/sdcore4linux/installsdai.sh` — builds `origin/main`, so
   it installs `728b542` and APPLIES entry 13. Watch near the end for `Applying
   the ssh tier boundary (PRE_RELEASE 13).` then either `ssh-forcecommand:
   INSTALLED …` (+ the banner's `sshd_config.before-sd` note) or a yellow
   WARNING if it refused. Take its closing reboot (the APIsrvr socket).
3. After: `assert-current` should answer **0**. Then witness 13 biting —
   `sudo systemctl start ssh` (sshd is inactive on this box), make a STANDARD
   account. **`no.query` needs the OS user to EXIST ALREADY** — `CREATUSR` is
   off, so CREATEA will not auto-create one and stops 6074 "Invalid user name"
   (`CREATEA:186`). So create the Unix user first from a shell —
   `sudo useradd -m <name> && sudo passwd <name>` — THEN, inside `sd`,
   `create-account user <name> no.query`. Then ssh as it → lands in `sd`, no
   shell; ssh as `don` (admin, excluded by `!sdadmin`) → normal shell. That
   live login is the half `sshd -t`/`-T` could not show offline (OpenSSH 10.3
   takes no `groups=` on `-T -C`).

***WITNESSED LIVE 10 Sep 2026 — ENTRY 13 IS NOW BEHAVIOURALLY RUN.*** OS user
`pete` created with `useradd`, then `create-account user pete no.query`.
`ssh pete@127.0.0.1` → SD banner, `:` prompt, `off` closed the connection: no
shell. `ssh don@127.0.0.1` (ADMINISTRATOR, in `sdadmin`) → normal Ubuntu
shell. That is the half `sshd -t`/`-T` could not show offline.

**Latent, not blocking:** neither script runs `systemctl daemon-reload`, so the
between-reboot has historically masked that; irrelevant to a keep cycle because
the unit files do not change. Fixing it (reload after delete removes units and
after install copies them) would retire the between-reboot by design.

***10 Sep 2026: THE FRESH INSTALL RAN AND SUCCEEDED FROM `dc36771` (origin/main
at the time; 27 was still unpushed), stamped 01:56:55 — AND PRE_RELEASE 24'S
SEED IS WITNESSED. The owner ran `sudo sd`: NO 10033 (the arm's silence is the
measurement — a registered ADMINISTRATOR exists), `User : don`, `Account :
SDSYS`, `Admin? : Yes`; `ACCOUNTS/DON` field 5 `ADMINISTRATOR` and `sdadmin`
holds `don`, read off disk. Plain `sd` stays non-admin by design: CPROC's grant
runs only inside `if system(27) = 0` (`CPROC:299`), so `logto sdsys` refusing in
an ordinary session is the two gates working, not a defect.***

### The one thing that matters before you believe anything

Run this first, every session:

```sh
python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/assert-current.py
```

No `sudo`. **0 current · 1 stale · 2 cannot answer.** As of the 15:11 install on
10 Sep it answers **0** — the install is stamped `242ae63`, which is HEAD and
`origin/main`, and `bin/sd` is newer than `gplsrc`. A later handoff commit puts
HEAD ahead again until the next install; that is the normal stale state, not a
fault.

### PRE_RELEASE 23 (OS-access tier gate + grant) — CLOSED, both gates witnessed end to end
Both commits pushed and installed. ***FULLY WITNESSED 10 Sep 2026 on the
`242ae63` install, STANDARD account `pete` — both gates, refuse → grant → allow
→ revoke → refuse:***
- **`SH` gate (10053):** `SH ls` refused **10053** → `MODIFY.ACCOUNT pete SH-ON`
  (10041) + re-entry runs it → `SH-OFF` (10042) + re-entry refuses again →
  `MODIFY.ACCOUNT don SH-ON` refused **10039** (admin tier always reaches the OS).
- **`OS.EXECUTE` gate (10054):** `pete` compiled a one-line `BP/ostest`
  (`OS.EXECUTE 'ls'`); `run bp ostest` gave `000000A9: pete is not permitted to
  use OS.EXECUTE` → `MODIFY.ACCOUNT pete OS-ON` (10041) + re-entry **ran `ls`** →
  `OS-OFF` (10042) + re-entry refused **10054** again. The admin-tier guard was
  not re-run for `OS-ON` (the identical `SH-ON` on `don` gave 10039; same shared
  `os.set` check).
- **Caveat on the 10054 witness (why a STANDARD account could compile):** it
  relied on `pete` compiling a program, which works ONLY because §L1's per-tier
  VOC is not built here yet — every account still gets the full VOC. Under
  conformity a STANDARD account has no `BASIC`: the Windows port omits the
  compiler/cataloguer/editors from STANDARD via `NEWVOC`'s `TIER.OMIT.STANDARD`
  (port `CREATEA`, owner 17 Aug 2026 — STANDARD *"can run an application but not
  build one"*). Once §L1 lands, re-witness 10054 with a PROGRAMMER account; the
  gate follows the PERSON, the compiler follows the ACCOUNT.
- **§L1 source (the port's model):** three VOC sources by tier — STANDARD =
  `NEWVOC` less `TIER.OMIT.STANDARD`; PROGRAMMER = `NEWVOC` entire; ADMINISTRATOR
  = `NEWVOC` entire plus `TIER.ADD.ADMINISTRATOR` (from `VOC_TEMPLATE`). Tier
  written to `ACC$TIER` field 5.

Also this session: the four admin-notice messages (10033/34/37/38) were wrapped
to <=79 cols so they fit the notice box (they were 81-141) — multi-line message
records, `op_sysmsg` turns the newlines into field marks. Ships on next install.

### Done this session — detail in PRE_RELEASE_FIXES.md, not repeated here

| entry | |
|---|---|
| **27** | the fresh install aborted at `installsdai.sh:631` — `chown /home/sd/group_accounts` — because 26 leaves `/home/sd` existing but empty, so the old `if [ ! -d /home/sd ]` skipped both mkdirs. Found by running, 10 Sep. Fix: unconditional `mkdir -p` for both, and a `/home/sd`-as-file refusal by name. **Sandbox-witnessed 5/5, control = pre-fix block on the empty state (dirs missing). Still unrun in the real script: the 01:56 retry installed from `dc36771`, before 27, and succeeded because `/home/sd` was absent (no `sd.conf` was saved), so the old guard was never hit.** Detail in PRE_RELEASE 27 |
| **26** | same review, same path: answering DELETE removes `/home/sd`, and `mv /etc/sd.conf /home/sd` then renamed the config to a **file** named `/home/sd`; the next install died at `mkdir -p /home/sd/user_accounts` (*"Not a directory"*). Fixed with `mkdir -p "$acct_path"` before the config save (`deletesdai.sh:140`). **Ran for real in the 10 Sep delete: it completed, and `/home/sd` was a directory holding `sd.conf` — the install that followed then aborted on 27.** Detail in PRE_RELEASE 26 |
| **25** | found while preparing 24's hand-over: `deletesdai.sh:186` deleted `sdadmin` unconditionally, so an upgrade that SAVES its accounts came back with an empty group and every administrator at **10037** — a lock-out with only an OS-root way back. Removal now conditional on `keep_accts = DELETE`, mirroring `sdsys`/`sdusers`. **Built, `bash -n` clean; unrun — the next saved-accounts upgrade is the witness.** Detail in PRE_RELEASE 25 |
| **24** | **Seeding witnessed 10 Sep 2026 on the 01:56 install (`dc36771`)**: `sudo sd` → no 10033, `User : don`, `Account : SDSYS`, `Admin? : Yes`; `ACCOUNTS/DON` field 5 `ADMINISTRATOR`; `sdadmin` holds `don`. The installer seeds the installing user as an SD ADMINISTRATOR (`installsdai.sh:783`, `ADMINISTRATOR` on `create-account`), and refuses a non-sudoer at the first `sudo -v` in words (`:236`) — **that refusal is still unrun**. Detail in PRE_RELEASE 24 |
| **23** | the OS-access tier gate, both commits. **Commit 1 (installed):** `op_sh` gates `OS.EXECUTE` to `$internal`/administrator (msg 10054). **Commit 2 (compiled, unrun):** `ACC$SH`(7)/`ACC$OS.EXEC`(8) grants, `MODIFY.ACCOUNT SH-ON\|SH-OFF\|OS-ON\|OS-OFF` (msgs 10039–10042), `SH` gate at `CPROC:3490`→admin-or-`K$SH` (msg 10053), flags loaded at account entry (LOGIN + CPROC logto). MODIFYA/CPROC/LOGIN each compiled **0 errors** with a red control (1 error); account restored to COUNT VOC 410; plain binary rebuilt. Detail in PRE_RELEASE 23 |
| **18** | closed. The tier gates: `CPROC` `grant.administrator`, a self-closing bootstrap arm, `MODIFY.ACCOUNT <acc> STANDARD\|PROGRAMMER\|ADMINISTRATOR`. **Witnessed end to end — the arm closed itself.** Its third requirement turned out already met |
| **21** | `sd -internal` was an unguarded route to the admin flag — **measured, uid 1000, no sudo**. Now behind `check_admin()`, with `make EXTRA_C_FLAGS=-DSD_DEV_BUILD` as the announced opt-out |
| **22** | `!set_passwd` / `!create_user` were globally catalogued with **no gate** |
| **14** | all 13 raw `sudo` calls now go through `sd-elevate`; `sdadmin` whitelisted; **`groupdel sdusers` was open and is now shut** |
| **17** | `L1.0-0`, and the banner is the owner's wording |
| **8** | `assert-current.py` + `test-assert-current.py` (10/10) + an install stamp |
| **12** | syntax highlighting reaches a user at last; **measured with two controls** |
| **20** | piece 1 witnessed — `WHO.AM.I` says `User : don` |

### Next task

***THE FRESH INSTALL, 24'S SEED, 13, AND ALL OF 23 ARE DONE. What remains is
24(2) and confirming the 25/27 delete transcript.***

- **25** — ***CLOSED BY OUTCOME 10 Sep 2026:*** after the 15:11 keep-accounts
  upgrade, `getent group sdadmin` = `sdadmin:x:965:don` — the group survived
  holding `don`, no 10037. The delete transcript was not captured this session,
  so this is the measured end state, not the run observed.
- **27** — the 15:11 install **completed** (`assert-current` current) and
  `/home/sd` is a directory holding `user_accounts`+`group_accounts`, so the
  `:631` abort did not recur. Same caveat: the keep-config precondition was
  inferred from the preserved trees, not watched.
- **24 (2)** — the non-sudoer refusal at `installsdai.sh:236` is still unrun.
- **23's gate** — ***CLOSED 10 Sep 2026*** (see PRE_RELEASE 23 above): both gates
  witnessed end to end, refuse → grant → allow → revoke → refuse (SH 10053 and
  OS.EXECUTE 10054). The 10054 repro is pre-§L1 (STANDARD can compile only until
  per-tier VOC lands; re-witness with a PROGRAMMER account after §L1).
- **13** — ***WITNESSED LIVE 10 Sep 2026***, re-confirmed on the `242ae63`
  install. `pete` (STANDARD) ssh → `sd`, no shell; `don` (admin) ssh → normal
  shell. Done.

`bash -n` clean, no BOM, 0 CR (both scripts).

***ENTRY 13 — THE ssh BOUNDARY — IS BUILT (10 Sep 2026), UNIT-TESTED 16/0,
SYNTAX-WITNESSED, AND LIVE-ssh-WITNESSED 10 Sep 2026*** (`pete` STANDARD → `sd`
no shell, `don` admin → shell; see START HERE step 3). Mechanism (ruled 9 Sep, owner):
`ForceCommand` into `sd` for `Match Group sdusers,!sdadmin`; PROGRAMMER = STANDARD
over ssh; administrators (in `sdadmin`) keep a real shell; admin-granted shell is
reached THROUGH SD (`sd` not setuid), so no per-user carve-outs. New helper
[ssh-forcecommand.sh](sdb_ai/sd64/gplbld/ssh-forcecommand.sh) (`--check`/`--install`/`--remove`),
installed root-owned to `/usr/local/sbin/ssh-forcecommand`; installer calls
`--install` non-fatally near the end, uninstaller `--remove` first. **Fenced
block in the main `/etc/ssh/sshd_config`, NOT a `sshd_config.d` drop-in** — owner
10 Sep: the other three distro families are being regained, so no Debian-specific
feature; the drop-in dir is not universal, the main config is. `sshd -t -f`
validates a candidate BEFORE the live file changes; refuses when no `sshd` is
found. Test [test-ssh-forcecommand.py](sdb_ai/sd64/gplbld/test-ssh-forcecommand.py).
***WITNESSED:*** `sshd -t` exit 0 on the exact block (OpenSSH 10.3p1); `sshd -T
-C user=` proves `Match`-block ForceCommand activation. ***NOW ALSO WITNESSED
LIVE 10 Sep 2026:*** the non-admin-forced / admin-free behaviour that `sshd -T
-C` could not show offline (it won't take `groups=` on 10.3) — `pete` forced
into `sd`, `don` free to a shell, over real ssh on 127.0.0.1. ***LOCK-OUT
SENSITIVE; the install path runs `sshd -t` as root, which is required — `sshd -t`
needs root to read host keys.*** Judgment call recorded in the helper header: the
refusal predicate covers `ForceCommand`/`Match`-naming-our-groups, not unrelated
`AllowGroups`. Detail in PRE_RELEASE_FIXES §13 / entry 13. ***Doc line-refs
`installsdai.sh:254-296` were stale (Debian-only now, one apt branch at `:307`).***

Cheaper things: `leave.sdadmin` has never run (`MODIFY.ACCOUNT DON PROGRAMMER`
exercises it); entry 6 needs an install; §L1's per-tier VOC is undesigned; §M is
release-blocking, scheduled at step 7.

### The instruments this session built or paid for

***COMPILING `GPL.BP` OUTSIDE AN INSTALL — the recipe, which this project did
not have before today:***

```sh
sudo sd -internal BASIC BP <prog>      # or build dev and drop the sudo
```

Arguments separate, **no pipe**. Stage the program plus its `$include` records
**from the working tree** into an empty `BP`. **Three traps, all paid for, all
in the session log below**: truncation is a *bad red control* (it passed three
times in five — inject an unbalanced bracket instead); **never grep the output
for `Compiled`** (a run that prints neither answer returns an empty match that
reads like a pass); and the compile creates a **`BP.OUT` VOC record** that
`rmdir` does not remove — clean up with `DELETE VOC BP.OUT` too. The `DON`
account's true empty `COUNT VOC` is **410**.

## Session log — 9 Sep 2026

*Detail behind the table above. The actionable handoff is the section before
this one; this is kept for the reasoning, not to be read first.*

***9 Sep 2026, LATER SESSION — ENTRY 18 COMMIT 2 IS BUILT AND THE BASIC WAS
COMPILED FOR REAL, WHICH THIS PROJECT HAD NOT MANAGED BEFORE.*** Opened on
`pull`, already up to date at `ef75eb2`.

**Built:** `CPROC` `grant.administrator` applies the owner's definition —
`sdadmin` membership **AND** `ACC$TIER`=`ADMINISTRATOR` for the real person — at
the **one** place `USR_ADMIN` is set, so the fourteen readers keep asking the
flag. `LOGTO SDSYS`, `CATALOG` ×2 and `DELCAT` swapped `system(27)` for the
flag. Messages 10033/10034. **`IsAdmin()` deleted** — it was already dead, entry
19 having removed its only caller, and it answers the wrong question.

***THE BOOTSTRAP ARM IS THE OWNER'S RULING AND IT WAS NEEDED, NOT PRECAUTIONARY.***
Measured on the 16:22 install: `ACCOUNTS/DON` had **three fields** (no tier) and
`sdadmin:x:965:` **no members**, so a strict gate refuses everybody and
`CREATEA:95` needs admin to register the first admin. With **no**
`ADMINISTRATOR` in the register the grant stands and prints 10033; the arm
closes itself once one exists.

***THAT MEASUREMENT MOVED THE SAME DAY AND THE CONCLUSION DID NOT — RE-READ ON
THE 17:53 INSTALL.*** `ACCOUNTS/DON` now has **five fields with `ACC$TIER` =
`STANDARD`**, up from three, so ***`PRE_RELEASE` 18 COMMIT 1's WRITE PATH HAS
RUN ON A LIVE SYSTEM***. `sdadmin` is still empty and **no account holds
`ADMINISTRATOR`**, so a strict gate would still refuse everybody — this is
exactly the state the bootstrap arm is for, and it is now the state the next
install will meet.

***THE COMPILE RECIPE, WHICH IS REUSABLE AND WAS THE MISSING INSTRUMENT:***
`sd -internal BASIC <file> <prog>`, arguments separate, **no pipe** — the port's
recipe at its `HISTORY.md:18916`. Stage the program plus its twelve `$include`
records **from the working tree** into an empty `BP`. ***AS OF `PRE_RELEASE` 21,
FIXED LATER THE SAME DAY, THIS NEEDS EITHER `sudo` OR A DEVELOPER BUILD*** — see
below; the runs recorded here predate the fix and ran as `don`. `CPROC` **0
errors on both
`IS_INSTALL` arms**, HEAD as the control also
0, and **two red runs** (a truncated `CPROC` → 10 errors; the same file without
`-internal` → the port's exact directive cascade). Fixtures removed.

***THREE TRAPS IN THIS RECIPE, ALL PAID FOR ON 9 Sep 26, AND NONE IS ABOUT THE
COMPILER.***

0. ***DO NOT USE TRUNCATION AS THE RED CONTROL. IT PASSED THREE TIMES OUT OF
   FIVE.*** Cutting a file short very often leaves a **valid** program — cut
   `MODIFYA` at 70 and you get a valid empty one; cut `SET_PASSWD` at 125 of 155
   and it compiles clean. **A red control that goes green is not a pass, it is a
   void run**, and it took three of them to learn it. ***INJECT A SYNTAX ERROR
   INSTEAD***: append one line with an unbalanced bracket — `if not(kernel(...)
   then` — which gives **1 error** reliably and changes nothing else.

1. ***DO NOT GREP THE OUTPUT FOR `Compiled`. READ THE TAIL.*** Twice in one
   session a run printed **neither** `0 error(s)` **nor** `N error(s)` — once
   because `-internal` was missing, once because `BASIC` could not open
   `BP.OUT` — and a grep for the success/failure words returned **nothing at
   all**, which reads exactly like a clean pass if you are only looking at the
   lines that matched. **A filter that can return empty is not a verdict.**
2. ***THE COMPILE CREATES A `BP.OUT` VOC RECORD, AND `rmdir` DOES NOT REMOVE
   IT.*** Delete the directory alone and the next compile dies with *"DATA part
   of file already exists / Unable to open newly created output file"*. Clean
   up with `DELETE VOC BP.OUT` as well. ***AND A `COUNT VOC` TAKEN AFTER THE
   FIRST COMPILE IS NOT A BASELINE*** — an earlier entry in this file claimed
   "411 either way, so nothing reached the VOC" when 411 already **included**
   the litter. **The account's true empty count is 410.**

***AND THE SESSION FOUND SOMETHING BIGGER THAN WHAT IT BUILT: `PRE_RELEASE` 21 —
NOW FOUND, RULED AND FIXED IN THE SAME SESSION.*** ***AS `don`, uid 1000, NO
`sudo`, A FIVE-LINE `$internal` PROGRAM SET ITS OWN ADMINISTRATOR FLAG*** —
`PRE admin flag = 0` → `POST admin flag = 1`, null case refused. `-INTERNAL` had
**no privilege check**, while `-I` three lines below called `check_admin()`. So
entry 18's gate — and any gate on that flag — was bypassable.

***THE OWNER RULED IT, 9 Sep 2026, AND THE RULING IS WIDER THAN THE ENTRY:
THIS SYSTEM SHIPS FOR PRODUCTION, NOT FOR DEVELOPERS.*** Source is available and
forkable, issues and comments welcome, **but no other human commits and the
installer is not a developer's tool.** ***THAT DISPOSES OF THE ONLY OBJECTION TO
THE FIX*** — a shipped production system owes an ordinary user no compiler for
its own internals, and the one person who needs the instrument has `sudo`.

**Built:** `-INTERNAL` calls `check_admin()`, and ***`check_admin()`'s
`in_group("admin")` arm is removed*** — not because it is dead here, which it
is, but because on Ubuntu-family systems `admin` was the old sudo group, so the
fix would have held on this machine and quietly not held elsewhere. `sdadmin`
was considered and rejected: it honours the owner's first gate and skips the
second. **Witnessed before/after/control as `don`, uid 1000**: installed binary
took `-internal WHO` (`3 DON`, exit 0), built binary refuses (exit 1), built
binary with no flag still works (`4 DON`, exit 0). **All three routes into
internal mode enumerated**; the `op_kernel.c:140` setter is reachable only
through the two gated flags, and all eleven `GPL.BP` uses of `K$INTERNAL` are
enquiries. ***Lead, not built***: that setter has no `HDR_INTERNAL` guard, which
is entry 19's shape.

***AND THE DEVELOPER'S COST WAS BOUGHT BACK, ON THE OWNER'S QUESTION: `make
EXTRA_C_FLAGS=-DSD_DEV_BUILD`.*** A build-time bypass of a privilege check is
normally the worst kind of divergence — the binary you tested is not the one
that ships. ***IT IS SAFE HERE FOR A REASON ALREADY IN CLAUDE.md AND NOWHERE
ELSE: `installsdai.sh` CLONES `main` FROM GITHUB AND BUILDS THAT***, so an
installed system is always built from a clean checkout with default flags and a
developer binary has no route to a user. **It announces itself on `--version`
and on every use of `-internal`**, plain `make` is untouched, and `bin/sd` in
the tree was rebuilt default afterwards. **`check_admin()`'s own tightening is
NOT conditional** — the `admin` arm is gone in both builds, because it was a
distribution-dependent weakness rather than a convenience.

***SO THE COMPILE RECIPE ABOVE STILL WORKS WITHOUT `sudo`, PROVIDED YOU BUILT
DEV*** — and the stderr line in the transcript is how you know you did.

***COMMIT 2 RAN ON THE 18:20 INSTALL AND THE ARM FIRED: `No SD administrator is
registered: granting rights to don for this session`, then `Admin? : Yes`.***
Message 10033 by number, naming the person, on exactly the predicted state.
Entry 21's `-internal` gate is on the same install, measured refusing `don`.

***THEN THE OWNER READ THE MESSAGE AND FOUND THAT ITS ADVICE COULD NOT BE
FOLLOWED — "kinda impossible" — AND HE WAS RIGHT TWICE OVER.*** `CREATEA:255`
refuses a name already in the register (6002) and `MODIFYA` had **zero**
references to `ACC$TIER`, so no existing account could ever become an
administrator and the arm could never close. ***AND THE COMMAND STRING IN THE
MESSAGE WAS ITSELF WRONG*** — `USER`/`GROUP`/`OTHER` has been required since rev
0.9.0 and only `OTHER` takes a pathname. **It was copied from `CREATEA`'s
`START-DESCRIPTION`, which is stale — and the port's copy is stale identically.**
***A COMMENT BLOCK IS NOT AN INSTRUMENT; THE SYNTAX THE VERB PRINTS AT
`CREATEA:246` IS.***

**Commit 3 fixes both:** `MODIFY.ACCOUNT <account> STANDARD | PROGRAMMER |
ADMINISTRATOR` (the port's grammar minus `SUSPENDED`, which needs `PRE_RELEASE`
13's doors), messages 10035/10036, 10033 rewritten to name the reachable route,
`CREATEA`'s description corrected. **Compiled 0 errors with a HEAD control —
and the first red control PASSED and was void**, cutting inside the header and
leaving a valid empty program; re-cut inside the body it gives 9.

***COMMIT 3 IS WITNESSED AND THE ARM CLOSED ITSELF, 9 Sep 2026.*** In one
sitting: the arm fired, `MODIFY.ACCOUNT DON ADMINISTRATOR` printed *"don added
to sdadmin"* and *"Account DON is now ADMINISTRATOR"*, and the next `sudo sd`
printed **no 10033** while still reporting `Admin? : Yes`. ***THE ABSENCE OF
10033 IS THE MEASUREMENT*** — it is the arm's only voice, so the rights came
from the register and the group. Read off disk afterwards, independently: field
5 `ADMINISTRATOR`, `sdadmin:x:965:don`, exactly one record holding the tier,
and `MESSAGES/10033` present so its silence is real.

***ENTRY 14's HANG DID NOT REACH IT, AND THE REASON MATTERS MORE THAN THE
RESULT***: `sudo usermod` returned unchallenged **because the session is uid 0**.
That says nothing about §14's ten call sites; it says this one runs where the
question never arises.

***THE REFUSAL CONTROL WAS RUN BY THE OWNER AND PASSED BOTH WAYS.*** He dropped
himself from `sdadmin` with the tier left at `ADMINISTRATOR`: **10034, `Admin?
No`, and 10033 correctly SILENT** — an administrator was still registered, so
the arm had no business firing. Restored with `gpasswd -a`, back to `Admin?
Yes` and no message. **The gate refused on the group half alone with the
register half held constant, which is the `AND` tested rather than argued.**
***AND `Account : DON` IS AN INDEPENDENT READOUT OF THE SAME FLAG***: with
`USR_ADMIN` clear, `LOGIN:240` stops matching and `:259` sends the session to
the person's own account. Nobody predicted that in advance; it moved in step.

***THAT RUN ALSO EXPOSED A DEFECT IN THE REFUSAL ITSELF, NOW FIXED.*** 10034
said *"not a registered SD administrator"* to a man who **was** registered,
sending the reader to the wrong half. There are three refusals now: **10034**
not registered, **10037** registered but not in `sdadmin`, **10038** the
register could not be READ. ***10038 IS THE THREE-ANSWER PROBLEM*** — the
unreadable arm was also printing 10034, a claim about what the register says
when nothing had been read. Compiled 0 errors on both `IS_INSTALL` arms, red
control 8 errors. **Unrun.**

**`leave.sdadmin` is still unrun** — `MODIFY.ACCOUNT DON PROGRAMMER` exercises
it.

***ENTRY 14 IS WIRED UP AND ENTRY 22 IS NEW.*** All **13** raw `sudo` calls in
`GPL.BP` now go through `sd-elevate`; the only grep hit left is a comment.
**Every mapping was validated with the helper's `--dry-run` before a line of
BASIC moved** — 13 of 13 resolved to the same command. ***THE JUSTIFICATION
CHANGED WHEN IT WAS CHECKED***: entry 14's hang is mostly unreachable (every
caller's real uid is 0, so `sudo` never challenges) — **except through entry
22**, `!set_passwd` / `!create_user`, which had no gate. The live bug is
**portability**: `sudo deluser` is Debian-only and `groupadd -U` is recent
shadow-utils, so demotion and group creation were broken on Arch and RHEL.
***`sdadmin` JOINS THE WHITELIST*** (delegation, not escalation — the caller
already holds it), ***AND THAT EXPOSED AN OLDER HOLE***: HEAD's helper builds
`groupdel -- sdusers` **exit 0**, measured by running it. Both system groups
are refused by name now. Self-test **36/0**, up from 30/0.

***`PRE_RELEASE` 8 IS BUILT: THIS PROJECT HAS AN `assert-current` AT LAST.***
`python3 gplbld/assert-current.py`, no `sudo`, **0 current / 1 stale / 2 cannot
answer**. A rewrite rather than a port, because the installer clones `main` from
GitHub so `bin/sd` is not what got installed: it checks the working tree is
committed, HEAD is `origin/main`, the install's **commit stamp** matches HEAD,
and `bin/sd` is newer than `gplsrc`. ***`installsdai.sh` NOW WRITES THAT STAMP***
(`$sdsysdir/.sdcore-install`, root-owned 644, written after the recursive
chown/chmod). **An install with no stamp answers 2, never 0.** Unit tests 10/10,
and the `CURRENT` row was watched failing first. **Live here it says STALE,
correctly** — the 18:39 install predates HEAD. ***USE IT BEFORE BELIEVING
ANYTHING MEASURED AGAINST THE INSTALLED TREE.***

***ENTRY 18 IS CLOSED, AND ITS LAST REQUIREMENT WAS ALREADY MET.*** The entry
claimed only a **forced** account is refused when unregistered. ***MEASURED 9
Sep 26 WITH A CONTROL: ALL THREE OF `LOGIN`'s ACCOUNT CASES READ THE REGISTER
AND TERMINATE ON A MISS*** — forced `:213`, administrator `:250`, and the
default `upcase(@logname)` at `:265`. `sd -ANOSUCHACCT` → *"not in register /
Connection terminated"*; `sd -ADON` → the session runs. **Nothing needed
building.**

***WHAT REMAINS IS §L1 AND IT IS NOT ENTRY 18.*** The per-tier VOC does not
exist, so a tier decides whether a verb **acts** but not whether an account
**has** it — the port's *"two gates, not one"* with only the second built. **Not
designed.**

*(The paragraph below was written before that install and is kept because its
method is the reusable part.)* ***COMMIT 2 HAD NOT RUN, AND THAT WAS CHECKED
RATHER THAN ASSUMED.*** The
17:53 install carries `K$REAL.USER` **×3** and `grant.administrator` **×0** in
`/usr/local/sdsys/GPL.BP/CPROC`, with `MESSAGES/10033` and `10034` **absent** —
so it is `origin/main` at `ef75eb2`, and the `Admin? Yes` above came from the
**old unconditional grant**. `8ef24bb` is committed and **not pushed**.
**Its witness is a further install of `origin/main` then `sudo sd`: expect
message 10033 naming `don` at start-up, and `WHO.AM.I` otherwise unchanged.**

*(Superseded — this was the note that opened the session logged above. The
session it describes ended at `51b5880`; the current head is `94085ac`.)*

***LAST SESSION ENDED 9 Sep 2026 (out of credits) AT `51b5880`. Tree clean,
pushed. This is the fresh-start note; the older lines below still stand.***

**Done this session (all pushed, all on `origin/main`):** entry 19 closed
(`op_kernel.c` admin-flag hole, `HDR_INTERNAL` gate); 14 & 13 measured and
ruled; **14's mechanism built** (`gplbld/sd-elevate` + `sdcore.sudoers` +
installer wiring + `test-sd-elevate.py` 30/0) — **installed and verified
present** (16:25 install: `sdadmin` group, `/usr/local/sbin/sd-elevate`
root:root 0755, `/etc/sudoers.d/sdcore` 0440); entry 18 **commit 1** (register
records a tier, `ACC$TIER`/`ACC$PRIOR.TIER`, `CREATEA` writes it + adds admins
to `sdadmin`); **`PRE_RELEASE` 20** filed and **piece 1 built** (`K$REAL.USER`
57 keeps the real person across the `sudo sd` drop). Adopted the port's
`test-fixlist-units.ps1` (pwsh, dev-only) — run it against `PRE_RELEASE_FIXES.md`.

~~***THE ONE THING BUILT BUT NOT YET WITNESSED: `PRE_RELEASE` 20 piece 1.***~~
***WITNESSED 9 Sep 2026 ON THE 17:53 INSTALL. The owner ran `WHO.AM.I` under
`sudo sd` and it said `User : don`.*** Baseline had been `User : sdsys`.
`Process UID 0` / `EUID 999` unmoved, `Admin? Yes`. **Message 10032 did not
fire**, so `SUDO_USER` reached the process and the unknown arm was never taken.
See `PRE_RELEASE` §20.

~~***NEXT TASK: ENTRY 18 COMMIT 2 — THE GATES.***~~ ***DONE, above.*** Two
things this paragraph said turned out to be wrong and the corrections are worth
keeping. **`IsAdmin()` needed no replacing — it was already dead**, entry 19
having removed its only caller; it is deleted rather than rewritten. **And the
`CN_SOCKET` guard does not arise**: `linuxio.c:110` sets
`command_processor = "$APISRVR"` for an API session, so `$CPROC`'s root-entry
block is not on that path at all and the port's every-API-session-is-admin hole
has no route here. `sd-elevate`/`sdadmin` are still inert until the ten raw
`sudo` call sites migrate (entry 14 tail).

**Step 5 (installer) is later, in planned order.** Owner's shape recorded above
(line ~164): ONE script for install/upgrade/delete; the in-place upgrade is
plan `F1`+`F2`.

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

### ~~Your next task~~ — *superseded 9 Sep 2026; the current one is under
"Next task" at the top of this file. The step-4 record below still stands.*

***STEP 4 IS COMPLETE.*** All of §G and all of §I are done — `I1` TAPE, `I3` SED,
`I4` UPDATE.RECORD, `I5` MODIFY, `I2` PROC, `G1` BP test programs (PY_* kept),
`G2` VFS, `G3` OPGEN, `G4` SDNet. **None of §I has been installed**; the BASIC
was not compiled this session (see "Step 4 / §I" for what instrument was tried
and why it could not).

***`PRE_RELEASE` 19 IS DONE (9 Sep 2026) — MEASURED, THEN FIXED TO MATCH THE
PORT.*** The `op_kernel.c` reading was confirmed on source (a positive argument
set `USR_ADMIN` with no `IsAdmin()` call, and `|| IsAdmin()` made `kernel(26,0)`
re-grant rather than clear for a root caller) — **but the "bypassable from any
BASIC program" claim is REFUTED**: `KERNEL` resolves only in internal mode
(`BCOMP:3758`), and a non-internal probe compiled from the non-root `don`
account failed *"Unrecognised statement"*, 2 errors. So the opcode is reachable
only from an `$internal` program (LOGIN, CPROC). Gated the flag change on
`HDR_INTERNAL` (the port's entry 170 fix); build clean, `bin/sd` boots.
The fix's `$internal`-path effect is **reasoned + conformity, not witnessed** —
an ordinary user cannot compile `$internal`, so it is unwitnessable from
ordinary BASIC, which is the same fact that makes the old hole unreachable. **An
install of `origin/main` would carry it to the running system** (`PRE_RELEASE`
15). See "Step 5 / PRE_RELEASE 19" below.

***YOUR NEXT TASK IS `PRE_RELEASE` 18***, now unblocked and specified: the owner
defined "administrator" on 9 Sep as **sudoers member AND registered SD
administrator, with unregistered users refused entry**. The gap table and the
port's `ACC$TIER 5` / `ACC$PRIOR.TIER 6` are in that entry.

***THE OWNER'S DEFINITION IS THE PORT'S MODEL IN LINUX WORDS, WHICH IS WORTH
KNOWING BEFORE IMPLEMENTING IT.*** The port's Administrator documentation opens
with *"there are two gates, not one"* — **the tier** decides whether the
account's VOC has the verb at all, **elevation** decides whether the verb does
anything (`SDCoreWindowsDocs/Administrator/markdown/01-accounts-and-security.md`,
which is local). "Registered SD administrator" is the first gate and "sudoers
member" is the second. **The shipped docs are local and are the prose model for
§L**; the port's code and record stay authoritative for `file:line`.

***`PRE_RELEASE` 14 AND 13 WERE RULED ON 9 Sep 2026 AND ARE NOW SPECIFIED WORK,
NOT OPEN QUESTIONS.*** Both are the owner's selections, recorded as selections
rather than as his words. **Neither is built.**

| | Ruled | What it commits to |
|---|---|---|
| **14** | SD ships a **`sudoers.d` drop-in for a group SD owns** | **18's second gate reads SD's own group** — portable across distributions, and it sidesteps the three-answer problem. ***MECHANISM BUILT 9 Sep, NOT WIRED UP*** — see below |
| **13** | **A STANDARD account gets no real login shell**; the tier is to be a **boundary** | ***SD must write to `sshd_config`*** — there is no way to hold the boundary without it. The port's fenced block + refusing preflight is the model |

***THE MEASUREMENTS BEHIND THEM, BECAUSE THE FIXES WILL BE CHECKED AGAINST
THEM.*** `sudo -n -v` answers *"a password is required"* and **0 of 10** call
sites pass `-n`, so the hang is real here; `sudo -n -l` exits **1** both for
"needs a password" and "may not sudo", so **a membership test on that exit code
refuses a legitimate administrator**; and every SD account today has a real
login shell (`don` `/bin/bash`, `sdsys` `/bin/sh`), which is the known-bad
starting state a §13 verifier must prove the system moved away from.

***ENTRY 18 IS HALF BUILT AND ITS SECOND HALF IS BLOCKED BY A NEW FINDING —
`PRE_RELEASE` 20. READ THAT BEFORE RESUMING.*** Commit 1 landed 9 Sep: the
register records a tier (`ACC$TIER` 5 / `ACC$PRIOR.TIER` 6 in `SYSCOM/KEYS.H`,
`CREATEA` writing it from `ADMINISTRATOR`/`PROGRAMMER`). ***COMMIT 2 WAS STARTED
AND DELIBERATELY STOPPED***, because the gates cannot be written as planned:

***ON `sudo sd`, `CPROC:285` REPLACES THE SESSION IDENTITY WITH `sdsys` BEFORE
`$LOGIN` RUNS***, so *"is this person a registered SD administrator"* has **no
person to look up**. `CPROC:2483`'s shipped `is_grp_member(@logname, …)` account
gate is already answered for `sdsys` rather than for whoever typed `sudo`.
***RULED 9 Sep 2026 — THE PORT'S MODEL, TWO IDENTITIES*** (owner's selection).
`@logname` keeps the real person, `USR_ADMIN` stays the session flag, and a
separate key answers *"is the signed-in person an administrator"*. **Not
built.** Three pieces, in `PRE_RELEASE` §20: **(1)** `CPROC:285` stops replacing
`@logname` — the euid drop stays, only the identity substitution goes.
***THE ENUMERATION IS DONE (9 Sep) — 14 sites, 8 files, in `PRE_RELEASE` §20,
AND IT FOUND THE LOCK-OUT.*** `LOGIN:191-195` tests
`is_grp_member(@logname,'sdusers')` and **terminates the connection**; it runs
**before** the account is chosen at `:240`. The sudo path passes it today *only
because* the identity is already `sdsys`, which is in `sdusers` (measured). Make
`@logname` the real person and **an administrator who is a sudoer but not in
`sdusers` is cut off with sysmsg 5009** — the port's exact failure, at a named
line. **It must be handled in the same change.** Also: `@USER` is the *same
slot* as `@logname` (both `SYSCOM.LOGNAME`, slot 14), `@WHO` is the account and
is untouched, and ***the substitution is in C — `sdext_eguid.c:67` — not in
`CPROC`***, so changing `CPROC:285` alone leaves `kernel(K$USERNAME,0)` still
answering `sdsys`. `CPROC:2890`/`:3110` and `LOGIN:259` are safe, for reasons
recorded there; **(2)** a new kernel key, **57 is free**;
**(3)** the gates read it. ***DO NOT COPY THE PORT'S `IsAdmin()`*** — its
`getgrouplist()` asks *"is this account an administrator"*, ours is
`getuid() == 0` and asks the wrong question; the Linux test is the owner's own
definition, sudoers **and** the register. ***AND CARRY THE PORT'S `CN_SOCKET`
GUARD***: this tree has `connection_type`/`CN_SOCKET` (`kernel.h:50,54`) and an
`IsAdmin()` reading the real uid, so the port's every-API-session-is-admin hole
is available here too. ***AND ENTRY 18 IS WRONG IN THE OTHER DIRECTION TOO***: the
sudoers half is largely enforced already, because reaching uid 0 via `sudo sd`
requires it. The missing half is the **register**, not sudoers.

***ONE THING THAT WAS CHECKED AND IS SOUND: THE ENTRY-19 FIX DOES NOT BREAK THE
`sudo sd` ADMINISTRATOR PATH.*** `CPROC:128` is `$internal`, so `CPROC:288`'s
`kernel(K$ADMINISTRATOR, 1)` still sets the flag under the new `HDR_INTERNAL`
gate. That was the one silent regression available and it did not happen.

***`PRE_RELEASE` 14's MECHANISM IS BUILT (9 Sep) AND IS INERT UNTIL ENTRY 18
LANDS. DO NOT READ IT AS DONE.*** `gplbld/sd-elevate` is one validated helper;
`gplbld/sdcore.sudoers` grants `%sdadmin` **that one command and not the eight
raw ones**, because `passwd`/`usermod`/`chmod g+s` are unrestricted by argument
and naming them would be root by another route. Installer creates `sdadmin`,
installs the helper **root-owned in `/usr/local/sbin`** (*not* under
`/usr/local/sdsys`, which is `chown -R sdsys:sdusers`'d — a helper there would
be sdsys-writable, and that is root), runs `visudo -cf` **before** installing,
and refuses when `/etc/sudoers` has no `includedir`. Uninstaller removes the
drop-in **before** the group it names. `test-sd-elevate.py`: **30 passed / 0
failed, 24 refusals + 6 controls**, ***and the test was watched failing*** —
6/24 against a stub that permits everything.

***WHAT MAKES IT INERT: THE CALL SITES STILL CALL RAW `sudo`.*** ***`sdadmin`
NOW GETS MEMBERS THOUGH*** — owner's ruling, 9 Sep: `CREATEA` adds an
ADMINISTRATOR-tier account's person to `sdadmin` (messages 10030/10031) beside
the `sdusers` add that was already there, so the drop-in is reachable for the
first time. **That add is an ELEVENTH raw `sudo` call and deliberately not the
helper**: the first administrator is not in `sdadmin` when the call runs, so the
helper would refuse the very call that creates them, and `sdadmin` is not in the
helper's group whitelist. ***THE MIGRATION MUST THEREFORE ALSO DECIDE whether
`sdadmin` joins that whitelist (an administrator creating administrators —
intended, but worth naming) and how the FIRST one is bootstrapped, which is the
installer's job rather than a verb's.*** Nothing installed; the installer edits
are unrun.

***TWO COSTS THE RULINGS DO NOT REMOVE, AND §14/§13 CARRY THEM:*** `sudo passwd`
and `usermod -aG` are **unrestricted by argument**, so a drop-in naming them
plainly is root by another route and they need wrapping; and a **malformed
`sudoers` file can lock `sudo` out of the machine**, so `visudo -cf` before
install, mode 0440, and no `.` or `~` in the filename. Open sub-decisions (the
group's name, who is put in it, the §13 mechanism, PROGRAMMER's case) are listed
in those two sections.

**Your next task after those is step 5, the installer.** ***`F9` IS SUPERSEDED — DO NOT DO
IT.*** The owner ruled on 9 Sep 2026 that the installer always clones `main`
from GitHub, which is the opposite of §F9's "drop the clone and build the
bundled tree". Done that day; see "Installer" below. Remaining: `F1` upgrade
split · `F2` `UPDATE.ACCOUNTS` · `F3` `[locked]` · `F4` config parser · `F5`
changelog location · `F7` self-check · `F6`, `F8`.

***OWNER'S SHAPE FOR STEP 5, 9 Sep 2026: ONE SCRIPT DOES INSTALL, UPGRADE AND
DELETE.*** Recorded as a selection of direction, not his exact words. Today the
two scripts (`installsdai.sh`, `deletesdai.sh`) and the fact that
`installsdai.sh:117-122` **refuses over an existing install** force the upstream
dance: run delete (saving `/home/sd/ACCOUNTS` + `sd.conf` to a staging area),
reboot, run install (which restores them at `:575-596`). **The owner wants that
collapsed into a single entry point that detects state and does the right thing
— install when absent, in-place upgrade when present, delete on request.** His
framing of why it matters: on Windows a user downloads a new *installer* and it
updates what is installed; ***on Linux the user downloads source and compiles***,
so the Linux equivalent is one script, not an installer binary. **Upstream's
delete-reboot-reinstall "does less account-upgrade work than the Windows port"**
— so the in-place upgrade must carry `F2`'s `UPDATE.ACCOUNTS` account refresh,
which is the part upstream skips. This does **not** reorder the F-items; it says
the container they land in is one unified script, and that `F1`'s "detect an
existing install" replaces the current refusal at `:117`.

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

### Step 5 / PRE_RELEASE 19 — the K$ADMINISTRATOR grant hole, 9 Sep 2026

`op_kernel.c:302-312`, `case K_ADMINISTRATOR`. Two questions: is the C hole
real, and is it reachable from ordinary BASIC.

***THE C HOLE IS REAL AT BOTH ENDS, CONFIRMED ON SOURCE.*** The old code
`if ((n > 0) || IsAdmin()) set; else clear;` set `USR_ADMIN` for any positive
argument with no `IsAdmin()` call, and for `n == 0` the `|| IsAdmin()` *re-set*
the flag whenever the caller ran as root — so `CPROC:2713`'s admin-drop on a
`LOGTO` did nothing for a root OS user. That second end is the reachable one.

***REACHABILITY MEASURED ON THE 11:35 INSTALL, AS uid 1000 (non-root), AND THE
"bypassable from any BASIC program" READING IS REFUTED.*** A probe
`BP/ADMTEST19` doing `KERNEL(26,1)` / `KERNEL(26,-1)`, compiled `BASIC BP
ADMTEST19` as an ordinary (non-internal) program, returned **`6: Unrecognised
statement` + `Matrix KERNEL is not referenced in a DIM statement`, 2 errors —
does not compile.** `KERNEL` is an `int.intrinsics` entry located only under
`if internal` (`BCOMP:3758,3781`), so a non-`$internal` program cannot emit the
opcode. The opcode is reachable only from LOGIN and CPROC, which are `$internal`
and own entry to an account. Fixture cleaned up: `COUNT VOC` **410 → 411 →
410** (the compile made a `BP.OUT` pointer; both it and `ADMTEST19` deleted).

***FIX: GATE THE FLAG CHANGE ON `HDR_INTERNAL`*** — the Windows port's exact fix
(`op_kernel.c:400-427` there, its entry 170, 13 Aug 26). Clean
`rm -f gplobj/op_kernel.o` rebuild, 0 warnings; `bin/sd --version` exit 0.

***WHAT IS NOT WITNESSED, WRITTEN IN THE CONDITIONAL.*** The fix would change
behaviour only for `$internal` callers, which an ordinary user cannot compile,
so it is unwitnessable from ordinary BASIC — the same fact that makes the old
hole unreachable. An install of `origin/main` would boot with it; if it did
not, a syntax/link fault would abort the two-stage bootstrap. `IsAdmin()` is now
prototyped-but-unused in `op_kernel.c` (defined in `linuxlb.c`, called
elsewhere) — no warning, it is `extern`.

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
fixes exist in the Windows tree as its entries 100 and 103, and those entries
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

### Conformity fix 10 Sep 2026 — CREATE.ACCOUNT always creates the OS user

***The `config('CREATUSR')` gate is removed from `CREATEA` `case 1`*** so
`create.account` ALWAYS creates the OS user — conforming to the port, whose
CREATEA removed the same gate 14 Aug 2026 on the owner's rule (*"SD has accounts,
not accounts-and-users; creating an account IS creating the OS account, nothing
to opt in to"*). Was: this tree required `CREATUSR=1` (off by default) **and** no
`no.query`, else 6074. Now: `create-account user <name>` creates the OS user +
prompts for its password + the SD account. `no.query` with no OS user is still
refused (creating needs the interactive password). Also applied the port's 21 Aug
fix: the missing minus on `@system.return.code` for a failed create (was `+6`).
Syntax-reviewed, compile-on-reinstall. `CREATUSR` still parses/prints; nothing
reads it. ***Witness: `create-account user tstd` now needs no prior `useradd`.***

### Parity audit against SD Core for Windows (10 Sep 2026) — CORRECTED + COMPILED, NOT RUN

Owner's instruction: audit every implemented feature against the port (the
reference) and correct drift except OS differences. **Scope: this project's own
work since 8 Sep** (plan steps 1–4, PRE_RELEASE entries, §L1, CREATUSR, MICRO);
the inherited AI layer (`9f82a52`) was not audited.

| # | Drift found | Correction |
|---|---|---|
| 1 | `SH ! CONFIG LISTU LIST.READU LIST.LOCKS CLEAR.LOCKS LOCK SET.DATE CLEAN.ACCOUNT` in NEWVOC = every tier | removed from NEWVOC, added to `TIER.ADD.ADMINISTRATOR` (port's 24 Aug split). UMASK stays (stance) |
| 2 | `NLS SET.LANGUAGE LOAD.LANGUAGE` in the VOCs | removed; programs kept (port 16 Aug, "English only") |
| 3 | `UPDATE.ACCOUNT` | `UPDATE.ACCOUNTS` + `ALL` (LOGIN mode 4; msgs 10170–10173, 10170/10172 adapted); heading verb 30→15 (port UPSTREAM 37) |
| 4 | messages 10030–10045 reused port ids with other meanings | port-equivalent → port id (10032 10033 10080 10102 10105 10106 10109 10113 10114 10157); Linux-only CPROC notices → **10900–10904**, a block the port does not use |
| 5 | kernel keys 57–59 = the port's `K$AUDIT/K$WINPATH/K$WINPID` | `K$REAL.USER/K$SH/K$OS.EXEC` → **90–92** in `gplsrc/keys.h` and `INT$KEYS.H`, agreement checked |
| 6 | Y/N prompts (port PRE_RELEASE 79) | 19 message records byte-copied from the port (trailing spaces); Enter = N at SETFILE, DELETEF, CREATEF, SETPTR, QPROC ×2, ED ×3 (incl. `yes.no`), LOGIN ×2 |
| 7 | VOC copy stripped field 1 (port PRE_RELEASE 136) | copied whole at CREATEA, LOGIN `update.voc`, MODIFYA `tier.build.rec` |
| 8 | DELACC: three prompts, `CREATUSR` gate, deletes any `sdu_` user | port flow: 10158 + one confirmation 10084/10085 (Enter = N), xref is a statement, ACCOUNTS deleted last; OS user deleted only if new `!is_sd_user` finds GECOS `SD account`, stamped by `sd-elevate useradd -c`. 6029/6031/10027 retired |
| 9 | CREATEA lacked `SH-ON`/`OS-ON` | added: USER account below ADMINISTRATOR, reported with 10102 |
| 10 | MODIFYA `os.set` accepted group accounts, reported one field | refuses non-`sdu_` (10105); reports both fields (10102) |
| 11 | DELCAT's admin test inside the loop | before the loop (port 18 Aug) |
| 12 | WEOFSEQ failure `goto` skipped `sq_file->base = -1` | the port's shape |

**Already equal to the port:** step 1–2 C fixes (`k_error`, keep-alive,
`get_ak_node` zero tests, `dh_file` chsize, `txn.c` `map_t1_id`/remove/`end_txn_level`,
commit rollback); PRE_RELEASE 19 `K_ADMINISTRATOR`; 21 `-internal` `check_admin()`;
TERM; `TIER.OMIT.STANDARD` (identical); WHOAMI; `check-msglen`, `checksyntax`,
`mkbasicsyntax`, `sdbasic.yaml`, `gen_includes` (header comments only).

**OS/model differences, kept:** per-account `ACC$SH`/`ACC$OS.EXEC` vs the port's
`os.users`; `sd-elevate`/sudoers vs elevation; the `SET_PASSWD`/`CREATE_USER` admin
gates; ssh ForceCommand vs `sdssh`/`sdapi` groups (no `ssh|api|both|none` keyword);
CATALOG's gcat chown; `clopts.c` `kill()` pid guard; UMASK; "Linux" in 2004/10024/6075;
lower-case names (§M, scheduled).

***PORT DEFECT FOUND:*** the port's `MODIFYA tier.build.rec` still strips field 1
after its own PRE_RELEASE 136, so every downgrade there compares unequal and counts
the verbs "left alone". Fixed here; the port needs the same one-routine change.

**Compile evidence** (dev build, recipe, as `don`, staged sha = tree sha each):
CPROC both `IS_INSTALL` arms, LOGIN, MODIFYA, CREATEA, DELCAT, SETFILE, DELETEF,
CREATEF, SETPTR, QPROC, ED, MICRO, DELACC, IS_SD_USER, CREATE_USER — **0 error(s)**.
Reds: `DELCATX` 7, `ISX` 2, `LOGINX` 1, none written to `BP.OUT`. sha256 of all 137
`gcat` entries identical before/after every run. **The first pass's verdicts were
lost** to a ugrep regex error and the pass was re-run. `test-sd-elevate.py`
**37/0** with a new STAMP row; red = the HEAD helper's dry run shows no stamp.
`op_seqio.c` and a full `rm gplobj/*.o` rebuild clean; fixtures removed,
`COUNT VOC` 410, plain `bin/sd` rebuilt.
***THE KEY RENUMBERING MAKES THE BINARY AND GPL.BP ONE UNIT — MEASURED:*** the
renumbered tree `bin/sd` against the installed `$LOGIN` aborts every session,
`Illegal KERNEL() action key (58) at line 286 of $LOGIN`. CPROC/LOGIN/MICRO were
compiled with a scratchpad harness built from HEAD's `keys.h` (deleted after).
**Do not run the tree `bin/sd` against the current install; install the commit.**

**Owner's ruling on the home directory, 10 Sep, BUILT + COMPILED, UNRUN:**
`DELETE.ACCOUNT <acc> REMOVE.HOME` (a parameter, so the port's one-confirmation
rule holds; 10905 names the home). Only for an SD-stamped user (else 10906, before
the question); home read from `getent`, result read off disk (10907/10908);
`userdel` exit 12 = user gone, home not. New `sd-elevate userdel-home` re-checks the
stamp and that home is exactly `<useradd -D HOME>/<user>`; `test-sd-elevate.py`
**42/0**, the `don` row refused *for the stamp* (reason printed). No ALLOW row is
possible on a box with no stamped user — the allowed half is an install witness.

**Objections and gaps, not done:**
- Users created before the stamp (`don`, `pete`, `tstd`, `tprog`, `tadm`) are left
  in place by DELETE.ACCOUNT (10036).
- Existing accounts keep the admin and language verbs already in their VOCs (an
  update never deletes); a tier change does not remove them either (not in a layer).
- A non-admin's SH-ON now needs the SH verb copied into that VOC (the port's
  model); entry 23's `pete` witness relied on SH being in NEWVOC.
- 10114's port text "nothing has changed" is false when VOC_TEMPLATE fails after
  the standard layer (the port's too).
- MICRO vs the port's `EDIT` (1002 lines: mark tokens, working copy removed on
  every exit — UPSTREAM 16's second half) is not converged.
- Port features not built here: SUSPENDED, TIERGATE, GRANT/REVOKE/LIST.GRANTS,
  `[locked]`, ADOPT, an upgrade running `UPDATE.ACCOUNTS ALL` (F2), MODIFY.PASSWORD,
  `K$AUDIT`, §M.

***Witness, after an install of the commit (conditional):*** a new PROGRAMMER
account has no `SH`/`CONFIG`/`LISTU`, an ADMINISTRATOR one has them;
`UPDATE.ACCOUNTS FOO` → 10173; `UPDATE.ACCOUNTS ALL` in SDSYS → 10170 then 10171 with
a count; `listf` in a new account shows descriptions; `CREATE.ACCOUNT USER x SH-ON`
→ 10102; `DELETE.ACCOUNT X` → one `(y/<n>)` naming the Linux user, user gone;
`DELETE.ACCOUNT PETE` → 10036, `pete` kept. Falsified by any of those not holding.

### NANO and MICRO — the port's EDIT program adopted (10 Sep 2026) — COMPILED, NOT RUN

Owner, 10 Sep: Microsoft Edit is not packaged for Linux; nano replaces it and
gets SD BASIC highlighting; the verb is `NANO`; `EDIT` stays an alias for `ED`.
`GPL.BP/MICRO` is **deleted**; new `GPL.BP/EDIT` (the port's, `$EDIT`) serves
`NANO` and `MICRO` (both templates `CA $EDIT`; `NANO` added to
`TIER.OMIT.STANDARD`, now 43). **Kept from the port:** lossless mark tokens
(`~~ ~\` ~! ~- ~,`), round-trip check, both gates before anything is written,
working copy removed on every exit, one `crt` per message line. **Adapted:**
`find.editor` = `command -v` (absolute path required); no `micro.home` (a Linux
user's `~/.config/micro` is already writable); micro syntax still copied per user
(`place.syntax`); `check.permitted` asks `K$OS.EXEC`; POSIX path from
`fileinfo(FL$PATH)` used as is; open folds case; single-quote names refused.
**nano highlighting:** new `gplbld/mknanosyntax.py` (the port's extraction, nanorc
writer, refuses a regex `grep -E` cannot compile) → `gplbld/nanocfg/sdbasic.nanorc`;
the installer places it in `/usr/share/nano` (Debian `/etc/nanorc:257` includes
`*.nanorc`), `deletesdai.sh` removes it.
**Evidence:** EDIT **0 error(s)** (harness, as `don`), gcat unchanged;
`test-edittokens-units.py` (adopted, path `GPL.BP`) **23/0 cases, 597 871
strings, 209 records (19 with specials), 0 lost**; nano measured in a pty (scratch
script, entry 12's method): `.sdbasic`+nanorc **11** distinct SGR vs `.plain`+nanorc
**3** and `.sdbasic`+empty rc **3**; `checksyntax` on the regenerated YAML 24/0;
both shell scripts `bash -n` clean. ***Witness after install (conditional):***
`nano bp x` and `micro bp x` open with colour; `~~` in the editor saves as a value
mark; a PROGRAMMER account without OS-ON is refused before `$HOLD` is touched.

### MICRO + plain-sd administrator OS access (BUILT + COMPILED 10 Sep 2026, NOT RUN — the MICRO program half is SUPERSEDED by the section above)

***Found by the owner, 10 Sep:*** `micro bp test` → *"File Error: bp could not be
opened"*; `MICRO BP TEST` → 10053, then *"Record was not saved"*. Entry 12's
witness drove micro in a pty and only compiled `MICRO`, so the verb had never run
through SD.
- **Cause 1:** `MICRO:226` launched with `execute "!"` = CPROC `os.command`, gated
  admin-or-`K$SH` (`CPROC:3502`). **Cause 2, entry 23's gap:** `USR_ADMIN` is set
  only under `sudo sd` (`CPROC:299`), so an ADMINISTRATOR in plain `sd` had no
  SH/`!`/OS.EXECUTE, and `MODIFYA` refused to grant (10039) on the false premise
  that the gates read the tier via `USR_ADMIN`. The port hit the same case (its
  `HISTORY.md` 29 Aug, *"AN UNELEVATED ADMINISTRATOR HAS NO sh"*; owner there:
  *"by default without escalating"*); ours, 9 Sep: *"by tier, automatic and
  unrevocable"*. **Cause 3:** `open` is case-sensitive and only `BP` exists (§M).
- **Fix:** `LOGIN:319` and CPROC logto (`:2777`) load `K$SH`/`K$OS.EXEC` true when
  the account's `ACC$TIER` is ADMINISTRATOR **and** `is_grp_member(@logname,
  'sdadmin')` — both halves of the owner's definition. Account-scoped: a LOGTO
  reloads from the target's record, so the port's LOGTO leak does not arise.
  `MICRO` takes the port `EDIT`'s shape: `check_permitted` first (blank `K$TTY` →
  refuse; `K$ADMINISTRATOR` or `K$OS.EXEC` → allow; else refuse naming OS-ON),
  `find_editor` via `os.execute "command -v micro" capturing` (entry 4), launch
  with `os.execute` (admitted on `HDR_INTERNAL`) + exit code in the failure text,
  file name as typed → lower → upper (§M1's order), single-quote record names
  refused. `$include int$keys.h` added.
- **Compile** (dev build, recipe, as `don`): LOGIN **0** / red **1**; MICRO **0** /
  red **2**; CPROC **0 on both `IS_INSTALL` arms** (tree `define_install.h` is the
  install arm; the runtime arm was staged as the installer's `*comment out *` line,
  `installsdai.sh:794`) / red **1**. `gcat/$LOGIN`, `$MICRO`, `$CPROC` sha unchanged;
  fixtures + `BP.OUT` removed, `COUNT VOC` 410; plain `bin/sd` rebuilt.
- **Not verified:** `os.execute … capturing` has no other caller in this `GPL.BP`
  (BCOMP parses it; runtime unwitnessed). `K$TTY` blank when stdin is not a tty is
  read from `kernel.c:177`, not measured.
- ***Witness, after an install (conditional):*** plain `sd` as `don` — `micro bp
  test` and `MICRO BP TEST` open micro; `SH ls` runs. PROGRAMMER `tprog` without
  OS-ON — `MICRO BP X` gives the OS-ON refusal and leaves no `$HOLD` working copy;
  after `MODIFY.ACCOUNT TPROG OS-ON` + re-entry, micro opens. From DON, `LOGTO` a
  non-admin account → `SH ls` refused 10053. Falsified by 10053 in DON, or by micro
  opening for `tprog` before OS-ON.

### ADOPT — the installer's pre-existing-user exception (TO BUILD, conditional)

***Owner's rule (10 Sep 2026): all SD users are created WITHIN SD (CREATE.ACCOUNT
makes the OS user — see the conformity fix above); the ONE exception is the
original installer, whose OS user already exists and is ADOPTED.*** The port does
this with an **ADOPT keyword** to CREATE.ACCOUNT — `CREATE.ACCOUNT USER <name>
ADOPT` uses a pre-existing OS user without creating it and defaults to the
ADMINISTRATOR tier (port `CREATEA:1617`: `if adopt and tier='STANDARD' then
tier='ADMINISTRATOR'`); the installer runs `sd -internal CREATE.ACCOUNT USER
<name> ADOPT`, the one path exempt from the install-time tier gates.

***Gap here:*** CREATEA has no ADOPT keyword; its `case is_user` SILENTLY adopts
ANY existing OS user, and the installer leans on that (`installsdai.sh:822`,
`create-account USER $tuser ADMINISTRATOR no.query`). That lets any pre-existing
OS user be taken in by plain create.account — against the rule.

***To build — one COUPLED, install-critical commit (CREATEA + installer together,
or the installer's own seeding breaks):***
- CREATEA: parse an `ADOPT` keyword (`more.args`); `case is_user` → if ADOPT, use
  the existing OS user and default the tier to ADMINISTRATOR (mirror port
  `:1617`); else **refuse** (a pre-existing OS user must be ADOPTed).
- `installsdai.sh:822`: seed the installer with `... USER $tuser ADOPT no.query`
  (ADOPT forces admin; no OS user is created, so `no.query` is fine).
- ***Install-critical:*** if refuse-unless-ADOPT lands without the installer
  switching to ADOPT, the install aborts at its own account step. Build atomic,
  let the bootstrap compile it, and witness with a clean install (the installer
  seeding itself is the witness) + a plain `create.account USER <existing-os-user>`
  being refused.
- ***Sequencing:*** build AFTER the pending SL1-core + CREATUSR verification
  reinstall — do not stack three unverified install-critical CREATEA changes.

### §L1 — per-tier VOC (CORE WITNESSED 10 Sep 2026; LOGIN filter + MODIFYA re-derivation COMPILED, unrun)

***`LOGIN` `update.voc` tier filter — BUILT AND COMPILED 10 Sep 2026, NOT RUN.***
The port's 17 Aug 2026 fix. All three call sites set `update.voc.tier`: mode 2
(`UPDATE.ACCOUNT`) and the `$RELEASE` prompt through new `get.acc.tier`
(`ACCOUNTS` by `@who`, own file variable — `acc.f` is closed by then); the
all-accounts walk off `acc.rec`. `update.voc` never copies the two control records
and skips `TIER.OMIT.STANDARD` ids unless the tier is blank/PROGRAMMER/ADMINISTRATOR
(blank = full, as the port). `SUSPENDED` → `ACC$PRIOR.TIER` at both resolvers
(nothing writes SUSPENDED here yet; carried for conformity). Also the port's
`old.rec = ''` before `READU` (upstream defect: a failed READU left the previous
id's record, so byte-identical adjacent ids like CATALOG/CATALOGUE were skipped).
**Not taken from the port's `update.voc`:** `[locked]` (= F3), Enter-defaults-N,
`upcase(id)='MD'` (§M), and its PRE_RELEASE 136 field-1 keep — `CREATEA:552` strips
field 1 too, so both sites must change together or the update undoes the create.
**Compile** (dev build, recipe, DON `BP`, as `don`): **0 error(s)**, *"with no
errors"*, staged sha = tree sha; red control = unbalanced bracket at the new
`get.acc.tier` line → **3 error(s)**, first `576: Right bracket not found`.
`BASIC:301` auto-runs `CATALOGUE BP $LOGIN` after a clean compile: refused
*"Command requires administrator privileges"*, and `gcat/$LOGIN` sha256 was
identical before and after (`gcat` is `sdsys` 0755). Fixtures + `BP.OUT` removed,
`COUNT VOC` **410**; plain `bin/sd` rebuilt (no DEVELOPER line).
***Witness, after an install of the commit (conditional):*** in STANDARD `tstd`
(368, no BASIC) set `$RELEASE` field 2 to an older stamp, log in as `tstd`, answer
`Y` → expect `COUNT VOC` 368 and `BASIC` not found. It would be falsified by 410.
The pre-fix control would be the same steps on the current install (expect 410 +
BASIC), which alters `tstd`.

***`MODIFYA` tier-change re-derivation — BUILT AND COMPILED 10 Sep 2026, NOT
RUN.*** The port's `voc.delta` + `tier.rank`/`tier.layer`/`tier.build.rec`/
`tier.add.one`/`tier.del.one` (port `gpl.bp/MODIFYA:1227-1440`), called in
`set.tier` **before** the register write (port order: a stopped run leaves the old
tier and a repeat converges); `voc.ok` false → **10044**, tier not written. Up
copies a layer in; down deletes only records equal to a tier build, else counts
them kept. `voc.from` is the raw field, so blank ranks PROGRAMMER; `old.tier`'s
blank-as-STANDARD stays, used only by the sdadmin test. Messages **10043** counts,
**10044** refusal (port 10114 says *"nothing has changed"*, false when the template
open fails after the standard layer — reworded to the register), **10045** failed
deletes. ***Adapted, not copied:*** `tier.build.rec` transforms NEWVOC records
only — `CREATEA:573-574` writes VOC_TEMPLATE records raw (`UNLOCK` keeps *"Verb to
unlock records"*), so transforming them would make every downgrade keep `UNLOCK`.
No SUSPENDED/route/promo/Windows-group parts (none exist here).
***Privilege — read from code, not measured:*** `sudo sd` drops to euid `sdsys`
(`CPROC:301`) and `sdext_eguid.c:66` sets no supplementary groups. `$MODIFYA` is
in `privileged_commands` (`CPROC:180`), so `CPROC:1682` restores euid 0 around it;
that is what would let it write `pete`/`don` VOCs, whose groups lack `sdsys`
(`sdu_pete:root,pete`; newer `sdu_tstd:root,sdsys,tstd`). ***Lead, unmeasured:***
`UPDATE.ACCOUNT` is `V|IN|15`, never raised, so its SDSYS all-accounts walk
probably cannot write user VOCs — hence the `$RELEASE` route for LOGIN's witness.
**Objections kept, not resolved:** (1) as the port, the register is written even
when deletes failed (10045), so the tier reads lower while verbs remain and a
repeat is a no-op (`from = to`); (2) `tier.layer` reads NEWVOC by the lists'
UPPER-CASE ids, so on ext4 §M must lower-case the lists and NEWVOC together or
every layer silently moves nothing.
**Compile** (dev build, recipe, as `don`): **0 error(s)**, staged sha = tree sha;
red = `(` injected in `tier.layer` → **9 error(s)**. Auto-`CATALOGUE $MODIFYA`
refused; `gcat/$MODIFYA` sha unchanged. Fixtures + `BP.OUT` removed, `COUNT VOC`
410. `check-msglen.py` REFUSED 10043 (exit 2, no `\n` escapes, so it measured
nothing); all three are one line, ≤69 chars, against a bound of 231.
***Witness, after an install of the commit (conditional)***, under `sudo sd`:
`MODIFY.ACCOUNT TSTD PROGRAMMER` → expect *"VOC: 42 records added, 0 removed, 0
left alone"* and tstd's `COUNT VOC` 410; back to `STANDARD` → *"0 … 42 removed"*,
368. `MODIFY.ACCOUNT TADM PROGRAMMER` → 5 removed (expect 410; also
`leave.sdadmin`'s first run), then `ADMINISTRATOR` → 5 added. Repeating a tier
should print 0/0/0. Any other count falsifies it. How to count another account's
VOC from SDSYS is untested (admin `LOGTO` gate, PRE_RELEASE 20 table).

***WITNESSED 10 Sep 2026 on a reinstall.*** CREATEA compiled (the install
completed). New accounts created on that install, counts read in-SD via `COUNT
VOC` / `LIST VOC 'BASIC'`: **STANDARD `tstd` = 368 records, BASIC NOT FOUND;
PROGRAMMER `tprog` = 410, BASIC present.** The gap is **exactly 42** — the 42
verbs in `TIER.OMIT.STANDARD`. So STANDARD gets NEWVOC less the omit list (cannot
build) and PROGRAMMER gets it entire — the tier VOC works at creation. Also
witnessed: the CREATUSR fix — `create-account user tprog programmer` (no
`no.query`) had SD create the OS user (`useradd`) and prompt for the password.
***Still pending: running the two builds above, and the ADOPT work (above).*** Build details: the two
control records
`sdsys/NEWVOC/TIER.OMIT.STANDARD` (42 dev verbs) and
`sdsys/NEWVOC/TIER.ADD.ADMINISTRATOR` (5 admin verbs: CREATE/DELETE/MODIFY/
UPDATE.ACCOUNT, UNLOCK), and the **tier-aware copy loop in `CREATEA`**
(`:517-580`) — STANDARD = NEWVOC less the omit list, PROGRAMMER = NEWVOC entire,
ADMINISTRATOR = that plus the add list from `VOC_TEMPLATE`; the two control
records are never copied; matching is case-insensitive. Block structure reviewed
by hand; ***the authoritative compile is the install's two-stage bootstrap***
(it aborts on a syntax error), so the witness is a reinstall + inspecting a new
account's VOC per tier. (`LOGIN` `update.voc` and the `MODIFYA` re-derivation are
built, above.) *(Design
follows.)*

### §L1 design — per-tier VOC (proposed 10 Sep 2026, conditional)

***The gates exist (entry 23); what is missing is that every tier still gets the
SAME verb set.*** §L1 would make the account's VOC depend on `ACC$TIER` (field 5,
already written by `CREATEA`/`MODIFYA`), conforming to the Windows port's model
(port `gpl.bp/CREATEA:1224-1440`, `newvoc/TIER.OMIT.STANDARD`,
`newvoc/TIER.ADD.ADMINISTRATOR`):

- **STANDARD** = NEWVOC less the verbs named in a new `NEWVOC` record
  `TIER.OMIT.STANDARD` — *"can run an application but not build one."*
- **PROGRAMMER** = NEWVOC entire (today's behaviour for everyone).
- **ADMINISTRATOR** = NEWVOC entire plus the verbs named in `TIER.ADD.ADMINISTRATOR`,
  copied from `VOC_TEMPLATE`.

**Two control records to add to `sdsys/NEWVOC`** (field 1 = description, fields 2+
= verb ids; the copy loop skips both records themselves):
- `TIER.OMIT.STANDARD` — the port's list transfers almost verbatim: **all 40 of
  its entries exist in this tree's NEWVOC** (checked 10 Sep, case-insensitively):
  `basic catalog(ue) delete.catalog(ue) compile.dict cd generate phantom run map
  debug ed edit micro create.file delete.file clear.file configure.file
  analyse/analyze.file fstat hsm set.trigger create/delete/build/make/list.index
  copy copyp delete rename reformat sreformat delete.common cname logout pstat
  pdebug pdump dump`.
- `TIER.ADD.ADMINISTRATOR` — ***must be curated for SD Core, NOT copied from the
  port.*** This tree's `VOC_TEMPLATE`−`NEWVOC` delta (17 ids) is mostly file /
  bootstrap entries; the actual admin VERBS in it are `create.account
  delete.account modify.account update.account unlock`. (The port also lists
  `grant revoke config listu sh !` etc.; here `sh`/`!` stay in every VOC and are
  gated at the C layer by entry 23, and the others are absent — so do not name
  them.)

**Three code sites (all must share one tier-filter, or the VOC drifts):**
1. `CREATEA` copy loop (`GPL.BP/CREATEA:517-534`) — read tier; skip the two
   control records; for STANDARD skip omit-list ids; for ADMINISTRATOR also copy
   the add-list records from `VOC_TEMPLATE`.
2. ***`LOGIN` `update.voc` (`GPL.BP/LOGIN:110-137,364-373`) re-copies NEWVOC on a
   release update*** — it must apply the SAME filter, or a VOC update silently
   restores a full VOC to a STANDARD account. ***THE PORT ALREADY HIT AND FIXED
   THIS (17 Aug 2026):*** its `update.voc` re-copied all of NEWVOC with no tier
   filter, handing a STANDARD account back `BASIC`, `CATALOG`, `RUN`, `ED`,
   `COPY`, `DELETE.CATALOG`, and was reachable from an ordinary login. Paid for
   next door — not a hypothesis. See the port's `HISTORY.md`.
3. `MODIFYA` on a tier change ***has NO VOC re-derivation today*** (checked 10
   Sep) — §L1 must add it so `MODIFY.ACCOUNT <a> STANDARD|PROGRAMMER|ADMINISTRATOR`
   re-derives the VOC; the port's `voc.delta`/`tier.set` is the model, and its
   PRE_RELEASE 57 rule (*a grant may go down or sideways, never up*) governs it.

**SD-Core adaptations / risks (what would falsify the plan):**
- ***Case.*** NEWVOC ids are still UPPER-CASE here (§M not applied), so the match
  must be case-insensitive (`upcase()=upcase()`, as the port) and must still work
  after §M lower-cases NEWVOC. §L1 and §M's fold interact — neither should assume
  the other's casing.
- ***SUSPENDED*** tier VOC is undecided; LOGIN already refuses a suspended login,
  so content may be moot — confirm.
- ***OBJECTION RAISED AND RESOLVED 10 Sep 2026 (owner) — the omit list stands as
  the port's, INCLUDING `run`, `phantom`, `logout`.*** The principle: **a STANDARD
  account only runs CATALOGUED programs.** The three are omitted on purpose —
  `run` (no uncatalogued programs), `phantom` (no background tasks), `logout` (no
  control of other users). A STANDARD user *"will probably never even see the
  command line."* The sanctioned way to give one account one extra feature is for
  an admin to **copy that VOC item into the user's VOC** — no tier change — so the
  omit list can be broad without being a trap. ***This decision and its rationale
  are the port's, recorded in its `HISTORY.md` ("17 Aug 2026 — Section 8"), the
  reference implementation; the owner confirmed it here.*** `PHANTOM` is omitted
  precisely because it runs a catalogued program in the *background* — the tier's
  "only run catalogued programs" is about foreground, attended use.
- ***RELATED INTENT, beyond §L1's VOC scope (note for later):*** because a STANDARD
  user is not expected to see the `:` prompt, such accounts likely want to be
  launched straight into an application (a forced `LOGIN`/menu entry) rather than
  dropped at the command line. That is a LOGIN-path decision, not a VOC one — flag
  it when §L1 lands, do not fold it in here.
- **Test after building:** a STANDARD account must have no `BASIC` (so the entry-23
  10054 witness moves to a PROGRAMMER account — already noted in PRE_RELEASE 23);
  PROGRAMMER = full VOC; ADMINISTRATOR = +admin verbs; a `MODIFY.ACCOUNT` tier
  change re-derives the VOC; a release `update.voc` preserves the tier's VOC.

### BASIC screen/widget library — design note (PROPOSED 10 Sep 2026, conditional; not started)

***Goal (owner, 10 Sep 2026):*** extend SD BASIC so a programmer builds rich
terminal screens — administrative apps rivalling the best TUI frameworks, up to
a traditional terminal-based IDE — WITHOUT leaving BASIC and WITHOUT any
commercial or client-side dependency. GPL-clean: standard ANSI/terminfo escape
sequences only, shipped as catalogued SD BASIC (thin C only where BASIC cannot
reach). AccuTerm is ruled out (commercial, needs a server-side API,
GPL-incompatible). Target terminal up to 160x48.

***What SD already provides:*** `KEYIN()` (raw key, timeout) + `KEYREADY()` (byte
pending) for input; the `@(...)` cursor/attribute set (`gplsrc/op_tio.c`) for
output; terminfo for portability. ***Missing:*** any widget layer, logical key
decoding (KEYIN returns raw bytes), and mouse.

***Architecture — a BASIC-facing API over layered catalogued subroutines:***
- **Event/key layer** — wrap KEYIN/KEYREADY into one `get.event()` decoding
  arrows, Tab, Enter, Esc, function keys (and mouse, below) into logical codes.
- **Screen/draw layer** — box-drawing, attributes, regions; ***double-buffered
  with minimal-diff redraw*** (write only changed cells) — the key to interactive
  speed in interpreted BASIC at large sizes.
- **Geometry/layout** — absolute plus simple layout managers (row/column/grid,
  anchoring, min/preferred size) so a screen reflows between 80x24 and 160x48.
- **Widgets** — label, button, text field (single/multi-line/masked), list box,
  table/grid (scroll/sort), tree, radio group, checkbox, dropdown/combo, menu +
  menu bar, tabs/notebook, scrollbar, progress bar, status bar, panel/frame,
  split pane, modal dialog, message/confirm box, and a text editor/viewer widget.
- **Form/focus manager** — owns a widget set, Tab/focus order, key dispatch,
  redraw, returns collected values; binds to MV dynamic arrays (field/value marks).
- **Theming** — colour via SGR (16/256/truecolor) / terminfo `setaf`/`setab`.

***Rendering:*** box-drawing via VT line-drawing (`acsc`/`smacs`) so it works in
the **default 8-bit build**; Unicode box-drawing is an **ECS-mode** enhancement
(SD's 8-bit-vs-ECS mode interacts here). Alternate screen + inhibit-cursor for a
clean full-screen app.

***Mouse:*** xterm SGR 1006. ***Likely pure BASIC*** — read the report sequence
(`ESC [ < … M/m`) via KEYIN/KEYREADY like any escape sequence — **IF** SD's input
path passes those bytes through KEYIN untouched. ***Verify that first;*** a small
`op_tio.c` addition only if it does not.

***THE MAIN TECHNICAL RISK — what would falsify the pure-BASIC engine: redraw
speed.*** 160x48 is ~7,680 cells; a full repaint or a fast scroll in interpreted
BASIC may be too slow to feel interactive. ***The FIRST task is to prototype the
diff-renderer and MEASURE a full redraw + a scroll at 160x48*** — if BASIC cannot
hit interactive latency, the draw/diff layer (and possibly key-decode / mouse)
moves to thin C behind the same BASIC API. The widgets come after that number is
known, not before it.

***North-star (owner): a terminal IDE*** — editor widget (SD-BASIC-aware), VOC/file
browser tree, multiple panes, menu + status bar, assembled from the widget set.
It is the validation that the toolkit is "rich enough", not the MVP.

***Staged (conditional):*** (1) prove the diff-renderer fast enough at 160x48;
(2) event/key-decode + draw + core widgets (field, button, listbox, menu,
checkbox, radio) + form manager, keyboard-only; (3) mouse; (4) advanced widgets
(table, tree, tabs, editor); (5) the IDE.

***Fits the port:*** GPL-clean, no dependency, AI-maintainable BASIC; rides the
ssh boundary + tiers — a STANDARD account ssh'd into SD lands in a catalogued
rich-screen app, which is the §L1 "launch into an application" note's natural
payload.

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

~~**Next planned work is step 3 (`D5`/`J4`/`D6`), in START HERE**~~ — *stale:
steps 3 and 4 are both done. The current next task is at the top of this file.*

***ADDED 9 Sep 2026 — TWO LEADS THAT ARE WRITTEN DOWN AND NOT BUILT.***
`op_kernel.c:140`'s `kernel(K$INTERNAL, n>=0)` **sets** internal mode and has no
`HDR_INTERNAL` guard — entry 19's shape exactly. It is contained today only
because both command-line routes in are now gated (`PRE_RELEASE` 21), and one
line would make that belt-and-braces. And `is_grp_member` (`GPL.BP/IS_GRP_MEMBER`)
reads only field 4 of `/etc/group`, the supplementary member list, so a person
whose **primary** group is the one being tested answers `false`. No shipped call
depends on that today; it would bite the first time somebody's primary group is
an SD group.

**ADDED 10 Sep 2026 — API port 4243; the two installer prompts + a TCP listener
BUILT + WITNESSED 10 Sep.** Owner: SD Core conforms to the Windows port, which
stays on **4243** (reconsidered 4243→4245→4243 this session; the durable reason
is that changing the API port across an upgrade is itself the problem, so the
port stays put and Linux matches it for upgrade compatibility). Built this
session on the owner's direction, approach **B** — bind-address gating, ufw NOT
force-enabled:
- **TCP listener, localhost by default.** `usr/lib/systemd/system/sdclient.socket`
  gains `ListenStream=127.0.0.1:4243` beside the Unix socket (the port's "LOCAL"
  state). `installsdai.sh` rewrites it to `0.0.0.0:4243` + `ufw allow 4243/tcp`
  only when **"Allow API access"** is yes; else it stays local and no rule added.
- ***C CHANGE, REVERSING A DELIBERATE DECISION — `gplsrc/linuxio.c`
  `start_connection()`*** accepted only `PF_UNIX` (mab, 2024-02-19). `PF_INET` is
  now accepted **for the API server only** (`is_sdApiSrvr`, i.e. `sd -n -q`); no
  `getpeereid` on a TCP peer, so the connection is gated by SD user/password
  (APISRVR SDConnect) plus the bind/firewall choice. `PF_INET6` still refused
  (listener is IPv4). Built: `make` **0 errors**, `linuxio.o` recompiled, `sd`
  linked.
- **Two installer prompts** (asked up front, both default NO): "Allow ssh access"
  = Y → `systemctl enable --now ssh` + `ufw allow 22/tcp`; "Allow API access" = Y
  → the 0.0.0.0 rebind + `ufw allow 4243/tcp`. ufw is not force-enabled — the
  gate is the bind address; the ufw rule is belt-and-braces for when ufw is on.
- ***WITNESSED 10 Sep 2026 on the `11571a7` install (API=Y, listener
  `0.0.0.0:4243`).*** The owner ran the headless client
  `scratchpad/apitest/apitest.py` (`sdclilibwrap.sdmeConnect` → a real TCP
  connect, not the Unix socket): `--user pete --account PETE` → `SDConnect`
  returned **1**, `SDConnected()=1`, and `WHO` over the connection returned
  `2 PETE` (SDExecute err 0). ***So the least-tested claim is confirmed: `sd -n
  -q` completes the SDConnect handshake + `login()` + `sdusers` check on a TCP fd
  exactly as on the Unix socket.*** Both installer prompts appeared on the run.
  Still to exercise if wanted: a **remote** host (`--host <ip>`), and a **default
  (API=N)** install to confirm the listener is then 127.0.0.1-only.
- **Client library HARDENED + default 4243, 10 Sep 2026.** `gplsrc/sdclilib.c`
  was replaced with the owner's standalone hardened `linuxsdclilib` (validated
  packet/arg lengths, index-packet overflow prevention, partial/interrupted I/O,
  desync abandonment, max-record enforcement, `SV_EMSG_PAIR`/`SV_ECONTXT`), plus
  new headers `gplsrc/sdclilib.h` + `gplsrc/client_ctype.c`. Its `SDConnect`
  default is now **4243** (was 4245). Repo's shared headers left untouched;
  `make` 0 errors, both `sdclilib.so`/`libsdcli.so` linked; the standalone repo's
  `make check` (smoke + internal) passed. ***WITNESSED on the installed runtime
  10 Sep 2026*** — after a reinstall from `origin/main`, `apitest.py` (loading
  the installed hardened `sdclilib.so`) connected TCP `127.0.0.1:4243` as `pete`:
  `SDConnect`=1, `SDConnected()`=1, `WHO`→`2 PETE`, err 0. Source published at
  `github.com/dmontaine/linuxsdclilib` (the Aug-15 hardened repo).
- **Still open, separate:** `gplsrc/sdclient.c:3404` (a different client, not the
  lib) still defaults `port = 4245`; and `changelog`'s historical 4243→4245 line
  runs against the ruling. Both minor, client-side.

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
  `mkbasicsyntax.py` are `micro`-editor syntax tooling — *(superseded: both were
  ported under `PRE_RELEASE` 2, ruled 9 Sep — micro stays, highlighting kept)* ·
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
