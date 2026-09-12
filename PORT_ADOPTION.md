# PORT_ADOPTION.md

Owner, 10 Sep 2026: for every feature of SD Core for Windows not implemented
here, review the port's code and **adopt or adapt it unless it would fail on
Linux**; keep a list of the code that could not be adopted, the feature it
belongs to and why, and **use this list as the basis for future tasks**.
Reference tree: `/home/don/Projects/SDCoreProject/sd4windows`. Update this file
in the same commit as the work.

## Adopted so far (10 Sep 2026)

- Parity audit corrections — PROJECT_STATUS "Parity audit" (`8a1b343`).
- `gpl.bp/EDIT` as `NANO`/`MICRO`, `test-edittokens-units.py` (`2d759f7`).
- UPSTREAM_FIXES 1, 3, 8, 9, 10, 14, 18, 20, 29, 35 and port PRE_RELEASE 174
  (C). Witnessed pre/post: 9, 18, 20 (branch), 35. Compile-only: 1, 3, 8, 10,
  14, 29, 174.
- QSELECT list-number (UPSTREAM 21) + DELETE.INDEX case-fold (UPSTREAM 22),
  11 Sep 2026 (`af879d3`). ***BOTH WITNESSED ON THE `af879d3` INSTALL*** (stamp
  02:19:18, `assert-current` 0):
  - **QSELECT** — `qselect voc * saving 3` → `410 record(s) selected to select
    list 0`; `... to 2` → `... select list 2`. The number is present and TRACKS
    the TO argument, so %2 is the real target list, not a constant. 410 > 0, so
    not the null case. ***NOTE THE GRAMMAR: a record specifier is required***
    (`qselect voc saving 3` answers "No records specified to process" — the
    `qselect voc saving 3` in UPSTREAM 21's write-up does not run here).
  - **DELETE.INDEX** — fixture: dict entry `F1` written by a scratch BASIC
    program, `create.index zzak F1` → `Added index for F1`. Then
    `delete.index zzak f1` (LOWER) → ***`Deleted index F1`***. Control
    `delete.index zzak nosuchidx` → `Unrecognised index name (nosuchidx)`, so
    the refusal path still works and the success is not blind acceptance; the
    control also confirms an unmatched name is echoed AS TYPED.
  - Fixtures removed; DON back to `COUNT VOC` 410.

### Built 10–11 Sep 2026 while the owner slept — INSTALLED (`3bd4421`), WITNESSED 11 Sep except 8 (`op_getlocks` in the sandbox only)

Each compiled 0 errors with `scratchpad/cbp.sh` (dev binary, DON/BP, red
control = 1 error, `COUNT VOC` 410 afterwards). Pushed and installed 11 Sep;
results in "Witnessed on the install" below the table.

| Queue | What | Witness after install |
|---|---|---|
| 3, 4 | DELETEF: port 14, 26, 104, 113 + Enter = N on 6135/6140 (Linux; port bug 6). Msg 10117 new, 6135/6140 reworded. `open 'voc'` NOT taken (§M) | fixture as in "Adopted" above with a lower-case name: `delete.file zzak no.query` deletes with NO prompt; a file whose dict is `@SDSYS/...` + `no.query` → 6145 + 10117, file kept; `printf 'delete.file x\n' \| timeout 10 sd` on a path-differs file ends (N) instead of spinning |
| 23 | CPROC `.D name`: as typed → down → up, 5043 on a miss, each failed `readu` releases its own id (port 5) | `.D nosuch` → `nosuch not found in VOC`, no prompt; save a sentence, `.D` it in the other case → deleted |
| 5 | LOGIN: `TERM` with no shipped terminfo falls back to `linux` (UPSTREAM 12; port falls back to `windows`). ***PREMISE WITNESSED 11 Sep*** on the tree dev `bin/sd` (same C as the `af879d3` install) with a `$internal` probe: `xterm-256color` → in force stays `linux`; control `vt100` → `vt100`; `xterm-256color` again → stays `vt100`; `LINUX` → `linux` (so the downcase is needed). Shipped types: no `*-256color` at all | `TERM=xterm-256color sd`: the screen is cleared at sign-on (with the old LOGIN it is not); control `TERM=linux sd` unchanged |
| 8 | CREATEA reads `status()` after `!set_passwd` fails: 6 → 10120, 2 → 10909 (new, Linux), 10 → 10910 (new, Linux: passwd's "pam error" covers mismatch AND policy, so the port's 10118/10119 cannot be split), else 10121; no retry for 2/6. `SET_PASSWD` header corrected: status is passwd's exit code, not a PAM code. ***PREMISE WITNESSED***: installed `!set_passwd` called from a non-admin session (`Admin? : No`) → returned 0, caller's `status()` = 6. Only reachable when CREATUSR is on | with CREATUSR on, `create.account user x` and mistype the second password → 10910 then the retry prompt |
| 10 | Port 16: `FL$HOLDERS` (1021, C `op_dio2.c` + both KEYS.H), `reap_lost_user()` (`clopts.c`, cleanup()'s lock order; Linux `process_exists` counts EPERM as alive, so a live session of another user is never reaped), `op_logout` returns 2, CPROC prints 10167; six 2602 sites → 10168/10169; messages byte-identical to the port. LOGOUT was already PROGRAMMER here. ***FL$HOLDERS WITNESSED on the tree dev binary:*** nobody else → `[]`; session A holding ZZ16 → `[95 (don)]`; A SIGKILLed → slot 95 "process GONE" and still `[95 (don)]`. ***REAP NOT WITNESSED*** — the LO16 probe exited on its own usage check (`@sentence` field 4, not 3), then the live system wedged (START HERE) | `LOGOUT n` on a killed session → 10167, slot gone from LISTU, the blocked `cname`/`build.index` then succeeds |
| — | `op_getlocks()`: `lock_owner_name()` returns "(gone)" for an unmapped owner instead of dereferencing NULL (Linux-found; also in the port — bug 7). Built clean; not run | after the reboot, reproduce the orphaned lock (START HERE), then `LIST.READU` shows "(gone)" and does not fault |
| 11 | LOGIN `update.voc`: `[locked]` (upcased, anywhere after the type) on the ACCOUNT's record skips it (10165), except a verb, which is updated and reported (10166); both messages byte-identical to the port. Also `upcase(id) = 'MD'` (§M-safe) | in an account: `ED VOC LISTV` style — make a PA record `PA [locked] test`, change NEWVOC's copy, `UPDATE.ACCOUNTS` → 10165 names it, record unchanged; same on a V record → 10166 and replaced |
| 9 | Field 1 of 9 `VOC_TEMPLATE` F records and `NEWVOC/NEWVOC` = the port's description, byte-identical to it; the 8 the port leaves bare stay bare. Safe: `_VOC_REF:109` and every GPL.BP test read only `[1,1]`; no whole-field comparison exists (searched). CREATEA's own file descriptions already matched the port | `LISTF` in SDSYS: ten rows read `File - …`, none a bare `F` except the eight the port also leaves |
| 6 | ED preset `-ER$ARGS` (UPSTREAM 11) | an ED command error leaves `@SYSTEM.RETURN.CODE` < 0 |
| 20 | READSEQ CRLF (UPSTREAM 13), C. ***WITNESSED pre/post on the tree dev binary*** vs the installed one, same probe and fixtures: CRLF len 6+CR → 5; boundary-split CRLF 2048+CR → 2047; lone CR and CR-at-EOF kept; LF control identical; READCSV last field `B1`+CR → `B1` | repeat with `/usr/local/sdsys/bin/sd` after install: the installed binary must now give the "after" column |
| 7 | CPROC F1 prints 10149 (port 8). Text adapted: the port names its Start Menu check; here `@SDSYS/changelog`, which ships world-readable. Same number and meaning | F1 at an empty `:` prompt → the three-part message with `/usr/local/sdsys/changelog` |
| 3b | Enter = N at 3033–3035, 6131, 5040 | `catalog bp x` with x also local → prompt shows `(y/<n>)`, Enter keeps both |
| 24 | BCOMP: `until end.source` in the TRANSACTION inner loop (port 114). Also compiled by `bbcmp.py` (the installer's bootstrap compiler): HEAD 70722 bytes, new 70728 | a BP program with `BEGIN TRANSACTION` and no `END TRANSACTION`: `timeout 20 sd -internal BASIC BP x` ends with 2878, not a timeout |

### Witnessed on the install, 11 Sep 2026

Install `3bd4421`, stamped 05:04:46; the 05:05 reboot cleared the wedge (six
semaphores at 1). HEAD `36fceba` differs by comments and docs only (`op_lock.c`
3 comment lines, 1681 lines both sides), so `assert-current`'s 1 was overridden
for this. Driven as `don`, no sudo: `/usr/local/sdsys/bin/sd` down a pipe under
`timeout`, DON account, probe programs in `DON/BP`, each run guarded on no `sd`
process and semaphores `111111`.

| Queue | Result |
|---|---|
| 3, 4 | `DELETE.FILE zzq NO.QUERY`: no prompt; 6136, 6141, 6144; VOC 413→412, both dirs gone. Path differs (`zzp2` = copy of `zzp`'s record): 6135 and 6140 show `(y/<n>)`, Enter = N, `ZZP` kept, VOC unchanged — at end of input too (each prompt printed once). Dict `@SDSYS/VOC.DIC` + `NO.QUERY`: 6136, 6145, 10117, 6144; `/usr/local/sdsys/VOC.DIC` kept |
| 3b | 6131 (`CREATE.FILE ZZU`, `DELETE.FILE zzu`), 5040 (`.D zzsent`), 3033 (`CATALOG BP TXNOK LOCAL`, then private): each shows `(y/<n>)`, Enter keeps the file / record / entry, counts unchanged |
| 23 | `.D nosuch` → `'nosuch' not found in VOC`, no prompt, VOC 412 both sides. `.D ZZSENT` on record `zzsent` → prompt names `zzsent`, Y deletes (416→415) |
| 5 | `TERM=xterm-256color`: `env('TERM')` reaches the session; sign-on starts `\e[H\e[J`. Control `TERM=dumb` (SD's `dumb` has no `clear`): sign-on starts `SD Core`. ***The planned witness could not discriminate:*** at `:` the type is always `linux` (the account's LOGIN paragraph, `LOGIN:109-112`), and the Bash tool does not export `TERM`, so a bare pipe gets `vt100` |
| 6 | `execute 'ED NOSUCH.ZZFILE X'` → `File not found`, `@SYSTEM.RETURN.CODE` -1; control `COUNT VOC` just before → 414 |
| 7 | `TERM=linux`, `ESC [ [ A` at an empty prompt → 10149 once, naming `/usr/local/sdsys/changelog` |
| 9 | Field 1 of the 9 `VOC_TEMPLATE` records and `NEWVOC/NEWVOC` on the install byte-identical to the port's. `LISTF` in SDSYS not run (`sudo sd`) |
| 11 | `UPDATE.ACCOUNTS`, own account: 10165 names `NO.QUERY` ([locked] keyword; kept, still differs from NEWVOC); 10166 names `WHO` ([locked] verb; replaced); control `FORCE` (plain change) replaced. 396 written. DON lacked the verb (START HERE) — added from `VOC_TEMPLATE` for the run, removed after |
| 20 | Installed binary gives the "after" column: CRLF 5, split 2047, lone CR kept (5), CR at EOF kept (4, last 13), LF 5 |
| 24 | Control `TXNOK` 0 errors; `TXNX` → `4: Unterminated transaction construct`, 1 error, inside 30 s |
| 10 | ***Reap WITNESSED LIVE*** (11:53): `RUN BP HOLD16` holds `ZZ16` as user 49 → `CNAME ZZ16, ZZ16B` refused, 10168 `Holding it: 49 (don)`; `FL$HOLDERS` `[49 (don)]`. SIGKILL pid 27335 → slot 49 still in LISTU, still the holder, CNAME still refused → `LOGOUT 49` → `LOGOUT reaped user 49 (pid 27335, don) - process was gone.` + 10167 → slot gone, holders `[]`, CNAME renames and back. Semaphores 111111 throughout. Same sequence first in the sandbox (user 12), same result |
| — | ***`op_getlocks` WITNESSED IN THE SANDBOX, pre-fix binary as the control, on one lock state*** — an RU lock owned by gone user 25 (queue 27). Fixed: raw `GETLOCKS()` owner field `(gone)`; `LIST.READU` lists it, no fault. Pre-fix (`3bd4421^` `op_lock.c`): `Fault type 11. PC = 000001B8 (DE 16) in $LISTRDU`, exit 139, semaphores 111111 → 111001 (REC_LOCK_SEM, FILE_TABLE_LOCK held), next session hung — last night's wedge, reproduced. `LIST.READU` prints only the number; `(gone)` shows only through `GETLOCKS()`, an `$internal` function |
| **not run** | 8 (needs CREATUSR on) |

## Waiting for the owner — skipped overnight 10–11 Sep because they need a ruling

0. ~~Reboot first~~ — done 05:05 11 Sep. Still open, the two decisions the
   wedge raised: should `sdsem.c` take its semaphores with
   `SEM_UNDO` (the kernel then releases a dead holder's semaphore — no more
   system-wide hang, at the risk of exposing a half-updated structure), and
   should SD's fault path release the semaphores its own process holds?
   Neither is built.
1. **Push and install.** Everything after `c8409e2` is local. The builds below
   are compiled, not run; the next delete→install cycle is their witness.
2. **`DELETE.FILE` with an active select list (message 2050), what Enter
   means.** 2050 is shared by six verbs; `DELETE`, `CD`, `COPY`, `CT` and `ED`
   treat anything but N as yes, so its de-facto default is **Y**. In `DELETEF`
   only, Enter re-asks for ever. Y keeps one message meaning one thing, but here
   it means "delete the file the list names"; N follows port 79's
   destructive-means-N pattern and makes 2050 mean different things in
   different verbs.
3. **`DELETE.FILE` on a multifile (6133 "Delete all data components?").**
   Answering N does not mean "change nothing" — it jumps to `delete.dict` and
   deletes the dictionary anyway. So there is no safe answer for Enter to take
   until someone says what N should do.
4. **§M scope:** whether "no two casings" reaches record ids in a user's own
   data files, and account names (PORT_ADOPTION "Queue 18").
5. ~~Queue 10: live or sandbox?~~ — **owner: sandbox first. Done 11 Sep: reap
   witnessed in both, `op_getlocks` in the sandbox** ("Witnessed on the install",
   row 10). The orphaned lock was NOT recreated live: nothing clears it before
   an SD restart (queue 27). Original question:
   **Queue 10's reap and `op_getlocks` "(gone)": witness on the live install,
   or in the sandbox first?** Both reproduce the overnight chain on purpose (a
   SIGKILLed session holding `ZZ16`, then `LOGOUT n`; an orphaned lock, then
   `LIST.READU`). If either fix is wrong the live SD wedges again and needs a
   reboot. The sandbox (older START HERE block in PROJECT_STATUS) has its own IPC
   keys but runs a scratch build, not the install.

## UPSTREAM_FIXES reconciliation — all 37, 11 Sep 2026

Measured against this tree's source, because this file named only 19 of the 37
and most of the rest had been fixed on 8–9 Sep under the parity plan's own ids
(`PROJECT_STATUS` "Step 1" / "Step 2") without being cross-referenced here.

- **Done here (28):** 1, 3, 8, 9, 10, 14, 18, 20, 29, 35 (10 Sep C batch) ·
  21, 22 (11 Sep, witnessed) · 7 = B1/B2 · 19 = D2 · 24 = D3 · 25 = C1 ·
  26 = E1 · 28 = D1 · 30 = A5 · 33 = A6 · 32 = A1 (`txn.c:20`) · 36 = A2
  (`txn.c:257`) · 17 (`txn.c:831`) · 31 (`txn.c:338`) · 5 (`LOGIN:545`) ·
  37 (`CPROC:3185` already says verb 15) · 15 (VFS removed, plan G2) · 16
  (MICRO superseded by the port's EDIT).
- **Not applicable (1):** 2 — resolved in the port as *not* upstream's bug.
- **Open (8) — as of 11 Sep night, 6 of them BUILT:** 23, 27, 34 (DELETEF),
  12 (LOGIN), 11 (ED), 13 (READSEQ — witnessed on the tree binary) · 4 **does
  not apply**: the Linux client forks and passes the descriptor form `-C%d!%d`
  as one argument, which `sd.c:432` parses, and runs `<sysdir>/bin/sd`, which
  is where the binary is · 6 (CREATE.FILE's on-disk case) → queue 18, decided
  by the owner's lower-case ruling.

## PRE_RELEASE_FIXES reconciliation — all 186 of the port's entries, 11 Sep 2026

Each entry read from the port's index row, and every product-code entry checked
against this tree's source (not against this file's earlier claims). Classes:

- **Done here (25):** 1, 17, 18 (EDIT adopted, `2d759f7`) · 7 (`sort.item` not
  in `TIER.OMIT.STANDARD`) · 11, 12, 13, 15, 23, 24, 25, 87, 100, 101, 102,
  103, 154 (UPSTREAM fixes, see above) · 21 (no `ACC$PRIOR.TIER` test exists
  here to delete) · 79 (every Y/N message shows its default) · 94 (group calls
  test `OS.ERROR()`) · 95, 97, 110, 128 (parity audit / 10 Sep) · 174 (SH1 argv).
- **Open, already queued:** 8 → 7 · 14, 26 → 3 · 16 → 10 · 19, 111 → 12 ·
  22 → 8 · 27, 98 → 13 · 57, 91, 92 → 14 · 65, 93 → 19 · 70 → 16 ·
  104, 113 → 4 · 142 → 9 · 144 → 21.
- **Open, NEW — added to the queue as 23–25, and 63/136 folded into 9:** 5
  (`.D name`), 114 (BCOMP hang), 28 (dump directory), 63 + 136 (file-record
  descriptions).
- **Does not transfer — Linux privilege/access model (15, with 168):** 2, 37, 42, 56, 64,
  68, 69, 72 (CREATUSR is off, so CREATE.ACCOUNT makes no OS user to strand),
  96, 99, 125, 130, 167, 169 — `os.users`, `$cred`, S4U, routes and logon
  rights; Linux has entries 13/18/20/23 instead. ***And 168: the port deleted
  `EUID_SET`/`EUID_RESTORE` and `sdext_eguid.c` as dead code; HERE THEY ARE LIVE
  (`sudo sd` drops to `sdsys` through `sdext_eguid.c`). DO NOT ADOPT.*** Nor
  anything else that removes from the extension layer: embedded Python is kept
  and improved (owner, 11 Sep).
- **Ruled not a defect / no change in the port (8):** 3, 9 (UMASK kept both
  sides), 20, 44 (5161 left unchanged there too — but its Linux analog is real:
  a group added by CREATE.ACCOUNT reaches the person only at their next login),
  61, 62, 157, 163.
- **Windows mechanism — installer, service, firewall, ssh capability,
  profiles, registry (55):** 6, 29, 32, 33, 35, 36, 39, 49, 50, 66, 67, 74,
  75, 76, 77, 78, 81, 83, 85, 88, 89, 90, 115–124, 126, 127, 129, 132, 133,
  135, 138, 139, 140, 141, 145, 146, 147, 148, 150, 153, 155, 161, 171, 172,
  173, 176, 184.
- **Port's PowerShell verify/test harness (46) — intent is queue 22:** 10, 30,
  31, 38, 40, 41, 43, 45, 46, 47, 48, 51, 54, 59, 60, 73, 82, 84, 86, 105–109,
  112, 131, 134, 137, 143, 149, 151, 152, 156, 158, 159, 160, 162, 164, 165,
  166, 170, 177, 178, 182, 183, 185. (178 and 185 are still open in the port.)
- **Port's documentation set (13):** 4, 34, 52, 53, 55, 58, 71, 80, 175, 179,
  180, 181, 186, and 163's documentation half.

Counts **measured, not typed**: 25 + 19 + 5 + 15 + 8 + 55 + 46 + 13 = 186, no
number missing or in two classes (163 counted under "ruled"). The checker is a
throwaway script; re-derive by expanding the lists above. *A first hand-typed
count was wrong in six of eight classes — which is why it was checked.*

## Queue — adoptable, not yet done (suggested order)

| # | Feature | Port code | Linux adaptation |
|---|---|---|---|
| ~~3~~ | ~~DELETE.FILE NO.QUERY~~ — **BUILT 11 Sep**, see "Built … while the owner slept" | `DELETEF` | |
| ~~4~~ | ~~DELETEF takes the ospath result~~ — **BUILT 11 Sep**, with port 113 | `DELETEF` | |
| 3b | Every Y/N loop maps Enter to its default — **BUILT 11 Sep** for `CATALOG` ×3 (3033–3035), `DELETEF` 6131, `CPROC` 5040, all Enter = N. `SPVIEW` needs nothing (presets `yn = 'Y'` in a formatted field). **Left for the owner:** `DELETEF` 2050 and 6133 — see "Waiting for the owner" | | |
| ~~5~~ | ~~LOGIN falls back when TERM has no terminfo~~ — **BUILT 11 Sep** | `LOGIN` | |
| ~~6~~ | ~~ED return-code preset sign~~ — **BUILT 11 Sep** (`ED:60` was `+ER$ARGS`; CREATEA's twin already fixed) | `ED` | |
| ~~7~~ | ~~HELP / F1 say something, msg 10149~~ — **BUILT 11 Sep** | `CPROC` | |
| ~~8~~ | ~~CREATE.ACCOUNT names why a password failed~~ — **BUILT 11 Sep** | `CREATEA`, `SET_PASSWD` | |
| ~~9~~ | ~~File-record descriptions (port 63, 136, 142)~~ — **BUILT 11 Sep** | data | |
| ~~10~~ | ~~LOGOUT reaps a dead user; the holder is named~~ — **BUILT 11 Sep** | `CPROC` + C | |
| ~~11~~ | ~~`[locked]` VOC records~~ — **BUILT 11 Sep** | `LOGIN update.voc` | |
| 12 | SUSPENDED tier — ***WITNESSED 11 Sep 14:59 on install `c2b375d` (`assert-current` 0), owner-run `witness-sudo.sh`, 33 PASS / 0 FAIL:*** control tstd signs on (VOC 368); `MODIFY.ACCOUNT TSTD SUSPENDED` → 10109, `VOC: 0 … 0 … 0`, 10159, register `SUSPENDED`/prior `STANDARD`; again → 10110, field 6 kept; `DON SUSPENDED` → 10112, DON unchanged; tstd sign-on → 10107 + Connection terminated; plain don `LOGTO TSTD` → 10107, still DON; administrator `LOGTO TSTD` enters (control); `LIST SD.ACCOUNTS TIER PRIOR.TIER` → `TSTD SUSPENDED STANDARD`; restore → 10109, `0 0 0`, field 6 cleared; tstd signs on, VOC 368 both sides. ***NOT WITNESSED: the ssh and API doors.*** As built: `MODIFYA set.tier`: SUSPENDED in the grammar; `ACC$PRIOR.TIER` written only on the way in; 10110 on SUSPENDED→SUSPENDED only (***objection kept in the code: the port returns on any equal tier, but here a repeat reconciles sdadmin***); 10112 for `@logname`/`@who`; VOC left as is while suspended, delta from field 6 on the way back, 10108 when field 6 is empty; sdadmin untouched by a suspend, left on lifting to a lower tier; 10159 adapted (Linux groups, sudo sd). Doors: `LOGIN` after the account case (console + ssh, unconditional), `CPROC int.logto` (administrator still enters — the port's judgement call), `APISRVR vb.account` (10003). Messages 10107/10108/10110/10112 byte-identical to the port, 10159 adapted, 10158 now offers suspend (port's text). `ACCOUNTS.DIC^TIER`, `^PRIOR.TIER` (byte-identical), `@` = `PATH DESCR TIER BY @ID`. Compile: dev binary, all four 0 errors, no new warning, red control 1 error. ***Witness after install*** (needs `sudo sd`): `modify.account tstd suspended` → 10109, VOC `0 0 0`, 10159; again → 10110; `modify.account don suspended` → 10112; `sd` as tstd and `ssh tstd@127.0.0.1` → 10107; plain-`sd` don `LOGTO TSTD` → 10107 (control: an administrator session enters); `list sd.accounts` shows Tier/Was; `modify.account tstd standard` → VOC `0 0 0` back, field 6 cleared; control first: tstd signs on before the suspend | `MODIFYA`, `LOGIN`, `CPROC`, `APISRVR` | SD doors only |
| 13 | K$AUDIT trail — ***WITNESSED 11 Sep on install `c2b375d`.*** As `don`, 14:48: `O_RDONLY` → `EACCES` (mode), `O_WRONLY` without `O_APPEND` → `EPERM` (the attribute), size 300 unchanged; a sign-on +62 bytes. Owner-run `witness-sudo.sh`, 14:59: `lsattr` `-----a--------e-------`, `sdsys:sdusers 620`; 20 records added, identity right on every one (`user=root sudo=don` under `sudo sd`, `user=tstd`, `user=don`): `ELEVATION GRANTED`, `LOGIN account=SDSYS`, `MODIFY.ACCOUNT TIER account=TSTD from=STANDARD to=SUSPENDED` and back, `LOGIN REFUSED account=TSTD reason=the account is suspended`, `LOGTO REFUSED account=TSTD reason=suspended`, `LOGTO account=TSTD`; earlier `LOGTO REFUSED account=SDSYS reason=not an administrator`; still append-only after. The installer's own 4 SDSYS sign-ons are the first lines. ***NOT WITNESSED: rotation (needs 1MB); the trail across a keep-accounts delete→install (this install created it); ADD/DELETE, SH/OS, ELEVATION REFUSED and API REFUSED records.*** As built: ***KEY 57, THE PORT'S NUMBER — NOT 93 as this row first said:*** the parity audit freed 57-59 here for exactly this key, and the shared-number rule says reuse. `k_error.c` `audit_message()`: the port's record format, plus `sudo=<SUDO_USER>` only when the real uid is 0 (under `sudo sd` `my_uptr->username` is root, `kernel.c` `GetUserName`); `O_WRONLY\|O_APPEND`, never `O_CREAT`; control characters and marks → `?` (no forged second line). `audit_rotate()` in `start_sd()` (root): at 1MB lift `FS_APPEND_FL`, rename `audit.<yyyymmdd-hhmmss>`, restore it on the rotated file, create the new one with the old owner, mode and attribute. `installsdai.sh`: after the restore block, put back a saved trail, `touch`, `sdsys:sdusers 0620`, `chattr +a`, WARNING if `lsattr` does not show it. `deletesdai.sh`: after the services stop, `chattr -a` (else `rm -fr` stops part way) and move the trail to `/home/sd` unless DELETE (the port keeps it with the database). Records: LOGIN (success mode 0 + one at `terminate.connection`, `audit.reason` set at all 16 refusals, default `unspecified`); CPROC ELEVATION GRANTED ×2 (after the grant, port 98) / REFUSED ×3, LOGTO + REFUSED (SDSYS, suspended, not granted); MODIFYA ADD/DELETE (port 27) and, ***Linux additions offered to the port***, TIER and SH/OS grants; APISRVR API REFUSED ×6, a name only after `valid_os_name`. ***KNOWN LIMIT, SAME AS THE PORT'S ACL:*** an SD user with a shell can APPEND a line of their own outside SD; they cannot read, alter or remove one, and STANDARD has no shell (PRE_RELEASE 13). Compile: `make` 0 warnings, all three objects rebuilt and linked (`nm`); LOGIN/CPROC/MODIFYA/APISRVR 0 errors, no new warning; red control 1 error; both scripts `bash -n` clean, no BOM/CR. ***Witness after install:*** `sudo lsattr` shows `a`, `stat` `sdsys:sdusers 620`; as `don` `cat` refused, `: >` refused; `sd` then `sudo tail` → `LOGIN account=DON`; plain `sd` `LOGTO SDSYS` → `LOGTO REFUSED … not an administrator`; `sudo sd` → `ELEVATION GRANTED` with `user=root sudo=don`; a keep-accounts delete→install keeps the lines and the attribute. Rotation is unwitnessed (needs a 1MB trail) | `op_kernel`, `k_error.c`, `sysseg.c`, callers, both scripts | chattr +a + 0620 instead of `win32audit.c`'s ACL |
| 14 | TIERGATE, GRANT/REVOKE/LIST.GRANTS, ADD tier ordering, promotion report 10126–10129 (port 57). ***WITNESSED END TO END 11 Sep 22:08 ON INSTALL `f3fbb1f` (`assert-current` 0, `verify-grants.py` 16/0 both controls PASS), owner-run `witness-grants.sh`, 28 PASS / 1 / 0 FAIL, restore COMPLETE on all four values.*** The 1 is not a failure: phase 2's "before" is a ONE-SHOT that the 22:04 run consumed — a tier move adds the three verbs to TADM's VOC and restoring its TIER does not take them out, so `is not in your VOC` can be read once per account and never again. Witnessed at 22:04, and the script now says so instead of failing. ***What the 28 cover:*** `sudo sd` lands in SDSYS and ***SDSYS's own VOC carries the verbs*** (the bootstrap builds it from the whole of VOC_TEMPLATE); `LIST.GRANTS` 10047 + the 10911 provenance line; wrong-case user caught by name (10045); GRANT sideways allowed (10041) with the 10043 caveat; the listing then naming `pete`; a repeat answering 10017 not a second success; ***GRANT upward refused (10126)***; ***GRANT SDSYS refused to anybody (10126)***; GRANT to somebody with no SD account (10127); ***the promotion report naming the grant it voided (10128) and naming `pete`***; ***THE GATE — `pete`, still a member of `sdu_tstd` with the membership looking perfectly normal, refused at LOGTO with 10126***, control: with the tiers level again `pete` DOES enter; a DEMOTION printing no 10128; MODIFYA ADD refused / DELETE ungated; REVOKE 10042 then 10049; and the trail carrying `GRANT account=TSTD to=pete`, `REVOKE account=TSTD from=pete` and `LOGTO REFUSED account=TSTD reason=tier`. ***DIVERGENCE (1) IS VALIDATED BY THE RUN, NOT JUST ARGUED:*** `$GRANTA` is not in `privileged_commands`, the session was euid `sdsys` with real uid 0, and every group edit went through — so sudo does decide on the real uid, as claimed. ***STILL UNWITNESSED: 10043's own claim*** — every session here was started fresh by `sudo -u`, so the "already logged in, sees SD admit them and the filesystem refuse them" half is untested; it needs a person with a live session at the moment of the grant. `!tier_allows` **11/11** and `!grp_members` **6/6**, probes `TGPROBE`/`GMPROBE` run as ***plain `don`, no sudo, no dev build, no administrator rights*** — an ordinary program may call the `$internal` functions, which is how the decision function could be witnessed without touching a group. `!tier_allows` covered both directions (`TPROG`→`TSTD` allowed, `TSTD`→`TPROG` refused status 3), equal rank, own account, and ***all four refusal statuses*** (1 unknown/empty account, 2 person not in the register, 3 rank, 4 SDSYS by name even for an administrator), plus lower-case input giving the same answer. `!grp_members` compared against an independent second read of `/etc/group` inside the probe rather than hard-coded lists, and both refusals (no such group, empty name) answer `n=0 status=1`. DON restored, `COUNT VOC` 411. ***ALSO MEASURED, AND IT CHANGES HOW THE VERBS MUST BE TYPED:*** the parser does **not** upcase a token, and `!is_grp_member` compares exactly, so `GRANT TSTD TO PETE` is a different request from `... TO pete`. GRANTA upcases the ACCOUNT (register keys are upper) and deliberately leaves the USER alone (a Unix name is genuinely case sensitive); the wrong case is caught by `is_user` and answered 10045 "There is no Linux user named PETE", which is a clear refusal and not a silent one. ***WITNESSED SEPARATELY: `GRANT is not in your VOC` for DON*** — the prediction that an existing administrator account does not get the verbs, now measured rather than read off the code. As built: `GPL.BP/TIERGATE` (`!tier_allows`, the port's, statuses 0-4, SUSPENDED via `ACC$PRIOR.TIER`, unknown tier refused, SDSYS by name); `GPL.BP/GRP_MEMBERS` (`!grp_members`, the Linux answer to `os_group LISTMEM` — reads `/etc/group` as `!is_grp_member` does); `GPL.BP/GRANTA` (`$GRANTA`, the port's three verbs over `sd-elevate addgroup`/`delgroup`, `!grp_members` for the listing, `K$AUDIT` after each successful edit); `CPROC:2865` the gate (10126 + audit `reason=tier`), after the 10003 group test so a never-granted caller learns nothing, with the same `K$ADMINISTRATOR` bypass its two neighbours carry; `MODIFYA:201` the ADD-arm courtesy gate (not DELETE) and `promo.snapshot`/`promo.report` (`:514`, `:550`, called `:419` and `:469`) either side of the register write (10128/10129), measured across the write rather than predicted; `VOC_TEMPLATE/GRANT｜REVOKE｜LIST.GRANTS` = `V｜CA｜$GRANTA`; the three names in `NEWVOC/TIER.ADD.ADMINISTRATOR` after `CLEAN.ACCOUNT`, the port's placement; messages 10041-10050 + 10126-10129 at the port's numbers (10041/10042/10046/10048/10049/10050/10129 byte-identical; 10044/10045/10047/10126/10127/10128 Windows→Linux only). ***THREE DIVERGENCES FROM THE PORT, EACH DELIBERATE:*** (1) ***`$GRANTA` IS NOT IN CPROC's `privileged_commands` (`:197-201`)*** — it only reads the register, and the four premises are measured 11 Sep: `/usr/local/sdsys/ACCOUNTS/*` is `-rw-r--r-- root:root`; the trail is `sdsys:sdusers 0620`; `/etc/sudoers.d/sdcore` is `%sdadmin ALL=(root) NOPASSWD:` and sudo decides on the REAL uid; `os_permitted()` (`op_sh.c:136-144`) returns TRUE on `HDR_INTERNAL` first. ***THIS IS THE LEAST-TESTED CLAIM IN THE ENTRY*** — if any premise is wrong, GRANT fails at run time and the fix is one line in that list. (2) 10043 reworded, and it says something the port's does not: SD's gates read `/etc/group` per call so they admit at once, while the account directory (`drwxrwsr-x <user> sdu_<name>`, measured on all five) waits for the person's next Linux login — ***the split is read off the modes and the code, NOT measured end to end***; falsified by a granted, still-logged-in person who can write a record. (3) `LIST.GRANTS` prints a provenance line, 10911 (Linux-only range), because `!grp_members` cannot see a primary-group member; measured 11 Sep, all five accounts have a primary group of their own name, and the five `sdu_` groups are `root,<user>`. Also fixed: `TIERGATE` and `GRP_MEMBERS` had no final `end` and each warned `Final END statement is missing`; every other `GPL.BP` function has one (measured: 36 of 38 before, 38 of 38 after). Compile, dev binary, `-internal BASIC BP`: GRANTA, TIERGATE, GRP_MEMBERS, MODIFYA, CPROC all `0 error(s)` / `Compiled 1 program(s) with no errors`, no warning; red control `QBAD` (unbalanced bracket) 3 errors / `Compiled 1 program(s) with errors in:` — the success wording appears only on the positive path. Tree rebuilt PLAIN (`--version` carries no DEVELOPER line); DON restored, `COUNT VOC` 411. ***Witness after install*** (needs an administrator session): `list.grants tstd` → members + 10911; `grant tstd to pete` where pete is PROGRAMMER and tstd STANDARD → 10041 + 10043, `list.grants tstd` now names pete; `grant tprog to tstd` (STANDARD→PROGRAMMER) → 10126; `grant sdsys to don` → 10126 with SDSYS; `grant tstd to <no SD account>` → 10127; `revoke tstd from pete` → 10042; again → 10049; `modify.account tstd add <up-tier user>` → 10126 (control: DELETE of the same is allowed); `modify.account tstd programmer` while a STANDARD person is in `sdu_tstd` → 10128 naming them (control: `modify.account tstd standard` prints nothing); as that person, `logto tstd` → 10126 and an audit `reason=tier`; `sudo tail` the trail for `GRANT account=TSTD to=pete` and `REVOKE`. ***AND THE WITNESS CANNOT START WITH DON, WHICH IS MEASURED, NOT ASSUMED:*** a NEW administrator account gets the three verbs (CREATEA builds NEWVOC + `TIER.ADD.ADMINISTRATOR`), an OLD one gets them from ***neither*** `UPDATE.ACCOUNTS` (`LOGIN:596` — the tier verbs come from VOC_TEMPLATE, "so this routine neither adds nor removes them") ***nor a same-tier `MODIFY.ACCOUNT`*** (`MODIFYA:718` `if voc.from = voc.to then return`). Only a tier that MOVES rewrites the VOC. So the witness creates a fresh administrator account, or runs after a full delete→install that reseeds DON; demoting DON to reach it would drop the only administrator out of `sdadmin` and is not the way. An earlier draft of this row and of the changelog said a re-derivation would do it — wrong, corrected against the two lines above. ***AND THE FIRST WITNESS RUN CORRECTED THIS ROW RATHER THAN CONFIRMING IT, 11 Sep 22:04, 8 PASS / 19 FAIL, restore COMPLETE.*** The row said to test "GRANT run by a plain-`sd` administrator" as divergence (1)'s real test. ***THERE IS NO SUCH SESSION.*** `CPROC:328` calls `grant.administrator` only inside `if system(27) = 0` — real uid 0 — so `kernel(K$ADMINISTRATOR,-1)` is never true outside `sudo sd`, ***for anybody***, and GRANTA's own gate (the port's, byte-for-byte) answers 2001. 17 of the 19 failures are that one cause; this file already said it at "Plain `sd` stays non-admin by design" and the session reasoned past it. ***The verbs run under `sudo sd`, which lands in SDSYS — and phase 1 measured that SDSYS's own VOC DOES carry LIST.GRANTS***, because the bootstrap builds SDSYS's VOC from the whole of VOC_TEMPLATE. No code changes: the gate is the port's and every other account verb here behaves this way. ***TWO REAL RESULTS SURVIVED THE MISROUTING.*** (a) ***MODIFYA's ADD arm IS WITNESSED***: `MODIFY.ACCOUNT TPROG ADD tstd` → 10126, control `DELETE` not tier-gated. (b) ***THE CHANGELOG'S UPGRADE INSTRUCTION IS WITNESSED, AND THE EVIDENCE IS THAT THE REFUSAL MOVED***: TADM answered `LIST.GRANTS is not in your VOC` before the tier move and `Command requires administrator privileges` after it — the second can only be printed by GRANTA itself, so the verb was FOUND and ENTERED, which proves the record reached TADM's VOC more precisely than a success would. `MODIFY.ACCOUNT TSTD PROGRAMMER` also reported `VOC: 43 records added`. Everything else cascaded from the wrong session type and is re-run by the corrected script | `TIERGATE`, `GRANTA`, `CPROC`, `MODIFYA` | `os_group` → `sd-elevate addgroup/delgroup` + `!grp_members` |
| 15 | ADOPT keyword + installer seed. ***WITNESSED 11 Sep 22:38, 14 PASS / 0 FAIL — detail below.*** Installed 11 Sep 22:19 (`3650118`, `assert-current` 0; queue 14 still 16/0 after the cycle). ***THE ROW'S OWN WITNESS PLAN HAD BEEN WRONG ABOUT HOW IT WOULD BE WITNESSED, AND THAT LESSON IS KEPT RATHER THAN TIDIED AWAY.*** It said "a clean install seeds its user and prints the ADMINISTRATOR line", and ***the cycle KEPT its accounts***, so `/home/sd/user_accounts/don` existed and `installsdai.sh`'s seeding block — the only caller of ADOPT — was skipped by its own `if [ ! -d ... ]` guard. ***TWO THINGS THAT LOOK LIKE EVIDENCE AFTER THAT INSTALL ARE NOT:*** no `$adopt.*` marker is left behind (none was ever written) and DON is ADMINISTRATOR (it already was). Both are the null case wearing a green coat, and the row would have banked them. ***Only a full delete→install, or the scratchpad `witness-adopt.sh`, reaches the code*** — the latter creates two throwaway Linux users, adopts one, and removes all of it, so five real accounts need not be destroyed to witness a keyword. ***WITNESSED 11 Sep 22:38 ON INSTALL `3650118`, owner-run `witness-adopt.sh`, 14 PASS / 0 FAIL, cleanup COMPLETE:*** `create.account user zzadopt1` on an existing Linux user → ***10038 and NO account directory created*** (the silent take-over is closed); `create.account user zznotauser no.query` → 10039 naming the real reason; ***`ADOPT` typed by hand with no marker → `Unexpected token (ADOPT)`*** and no directory; then with the marker written, `sd -internal create-account USER zzadopt1 ADOPT no.query` → account directory and register record created, ***tier ADMINISTRATOR with no tier keyword given***, the person joined `sdadmin`, ***the marker CONSUMED***, and the Linux user still there and not recreated; and ***a marker naming `zzadopt1` did NOT let `zzadopt2` be adopted*** (`Unexpected token (ADOPT)`, no directory) while `zzadopt1`'s marker survived the attempt — one marker, one account. ***STILL UNWITNESSED, AND IT IS A SMALL GAP NOT A LARGE ONE:*** the witness ran the same command shape the installer now uses, but `installsdai.sh`'s own block — the marker write, the `-internal … ADOPT` call and the register read-back that warns in red — has not run, because only a FULL delete→install reaches it. ***THE PLAN IN PROJECT_STATUS UNDERSTATED IT AND THE PORT HISTORY IS WHY:*** that section says "parse an ADOPT keyword … else refuse", which is the port's 14 Aug design; the port then found on **21 Aug** that ***`K$INTERNAL` IS NOT ENOUGH ON ITS OWN*** and added a ***one-shot marker file***, and that is what was built here. As built — `CREATEA`: `adopt`/`adopt.marker` initialised beside the other flags (BCOMP fails the bootstrap on "is not assigned a value", and `more.args` is shared with the GROUP and OTHER arms, which never set `acc.uname`); the USER arm overwrites the marker with `@sdsys/$adopt.<downcased name>` after the name is parsed and before `more.args`, so one marker authorises ***one account***, not the verb; `more.args` takes ADOPT only on `upcase(token) = 'ADOPT' and kernel(K$INTERNAL,-1) and ospath(adopt.marker, OS$EXISTS)` and ***deletes the marker on acceptance***; ***the two gates are in the case CONDITION, so a shut gate falls through to "Unexpected token (ADOPT)"*** rather than a refusal that would confirm the keyword exists; `if adopt and tier = 'STANDARD' then tier = 'ADMINISTRATOR'` — a default, not an override. The two `case is_user` branches that said `null` are ***merged and now REFUSE (10038)*** unless ADOPT — they were silently attaching an SD account to somebody's existing Linux login; `case adopt` with no such user → 6074; `case no.query` → ***10039 instead of 6074***, because by then the name is fine and it is NO.QUERY that cannot work. 10038/10039 are the port's numbers, freed here by the 10 Sep parity renumber, Windows→Linux wording only. `installsdai.sh`: writes the marker, calls ***`sd -internal create-account USER $tuser ADOPT no.query`*** (`-internal` was NOT there before and the ADOPT gate needs it), removes the marker whatever happens, ***then READS BACK `ACCOUNTS/<NAME>` field 5 and prints a red WARNING naming the tier it actually got*** — the install is the only witness for the ADMINISTRATOR default, and a silent STANDARD is precisely the regression `installsdai.sh`'s own 10 Sep note describes. Compile: dev binary, CREATEA 0 errors no warning, red control `QBAD` 3 errors; `installsdai.sh` `bash -n` clean; tree rebuilt PLAIN, DON `COUNT VOC` 411. ***COUPLED AND INSTALL-CRITICAL: CREATEA and the installer must ship together*** — refuse-unless-ADOPT without the installer's ADOPT aborts the install at its own account step. ***Witness:*** a clean install seeds its user and prints the ADMINISTRATOR line (not the WARNING); then `create.account user <an existing Linux user>` → 10038; `create.account user <new name> no.query` → 10039; `create.account user <new> ADOPT` typed by hand → `Unexpected token (ADOPT)`; and `ls /usr/local/sdsys` shows no `$adopt.*` left behind | `CREATEA`, `installsdai.sh` | one-shot marker file; `sd -internal`; no `adopt-account.ps1` equivalent — the installer does it inline |
| 16 | Upgrade runs UPDATE.ACCOUNTS ALL (port 70). ***AND HERE THAT IS ONLY HALF THE FIX — MEASURED 11 Sep, BEFORE ANYONE ADOPTS THE PORT'S WALK AND ASSUMES IT CLOSES THE GAP.*** The port's 70 is "an upgrade replaces `newvoc` and `voc_template` but cannot reach a live VOC", found because four verbs added 30-31 Aug were not typeable in an upgraded account. On this tree `update.voc` (`LOGIN:562-625`) selects `@sdsys/NEWVOC` and ***never opens VOC_TEMPLATE at all***, so the walk would deliver new NEWVOC records and ***not*** new administrator verbs; `LOGIN:596` states the property from the not-removing side. The only two things that add a VOC_TEMPLATE verb here are `CREATEA` at account creation and `MODIFYA` `voc.delta` when the tier ***moves*** (`:718` returns when it does not). Found while planning queue 14's witness, which needs an administrator account holding GRANT / REVOKE / LIST.GRANTS. So this row is two pieces: the walk, and a way for an existing account to take a tier layer it did not have. ***UNRULED: which*** — re-derive the layer inside `update.voc`, or a separate verb. ***AND THE PORT DOES NOT ANSWER IT, MEASURED RATHER THAN ASSUMED:*** its `update.voc` opens `newvoc` only and skips the same two control records (port `LOGIN`, same shape as here), so its own 70 walk cannot add a `voc_template` verb either — and the four verbs its 70 was written for (`remote.api`, `remote.ssh`, `ssh.server`, `append.sd.path`) are in its `TIER.ADD.ADMINISTRATOR`, i.e. exactly the kind the walk cannot reach. ***NOT CHECKED: whether the port's 70 witness covered those four*** (its entry cites `who`, a NEWVOC record, and counts). ***BOTH HALVES BUILT AND COMPILED 11 Sep, NOT RUN.*** ***AND THE GAP WAS MEASURED FIRST, WHICH TURNED AN ABSTRACT DESIGN QUESTION INTO A CONCRETE ONE*** — probe `TLPROBE` on the live install: ***`DON`, the only registered administrator, held 10 of the 18 `TIER.ADD.ADMINISTRATOR` verbs and was missing 8*** — `CREATE.ACCOUNT`, `DELETE.ACCOUNT`, `MODIFY.ACCOUNT`, `UPDATE.ACCOUNTS`, `GRANT`, `REVOKE`, `LIST.GRANTS`, `UNLOCK`. `TADM` held all 18 ***only because queue 14's witness moved its tier*** and MODIFYA re-derived the layer; `SDSYS` holds all 18 because the bootstrap builds it from the whole of VOC_TEMPLATE. ***That last fact is why nobody had noticed:*** administration is done under `sudo sd`, which lands in SDSYS. **Half 1** — `installsdai.sh` runs `UPDATE.ACCOUNTS ALL` when accounts were kept, with `accounts_kept` captured BEFORE the seeding block because that block creates the directory the test asks about; `ALL` is mode 4, the unattended form that skips the "update all accounts?" question (`CPROC:3336`, built 10 Sep — ***the verb half of the port's 70 already existed here; only the installer call was missing***). **Half 2** — `LOGIN` `update.voc` now also copies the `TIER.ADD.ADMINISTRATOR` layer from VOC_TEMPLATE, which it had never opened. ***THE RULED DECISION, TAKEN RATHER THAN FORWARDED, AND EASY TO REVERSE:*** the row asked "re-derive inside `update.voc`, or a separate verb"; `update.voc` wins because the project stance is a smaller system with less cruft (a new verb nobody runs is the opposite), because it makes the port's own walk actually close the gap, and because it rides the triggers that already exist. ***ADD ONLY, NEVER OVERWRITE, NEVER REMOVE, AND ADMINISTRATOR ONLY*** — a plain `read` not `readu`, so it takes no lock it could strand; an id the account already holds is left exactly as it is, so no `[LOCKED]` test is needed because nothing is overwritten; a blank tier does NOT qualify, since guessing upward is the opposite of TIERGATE's rule. Message 10912 (Linux-only range). ***OBJECTION KEPT: it never removes***, so an account demoted outside MODIFY.ACCOUNT keeps verbs its tier no longer earns — `update.voc`'s existing property, and `voc.delta` is what deletes on the way down. Compile: dev binary, LOGIN 0 errors; ***a first attempt warned `LAYER.OLD is assigned a value but never used`*** and was rewritten to test the record's own content, 0 warnings after; red control `QBAD` 3 errors; `installsdai.sh` `bash -n` clean; tree rebuilt PLAIN, DON `COUNT VOC` 411. ***Witness — and the BEFORE is already taken, 11 Sep 23:45, `gplbld/verify-tier-layer.sh` exit 1:*** `the layer lists 18 verbs`; ***`DON: ADMINISTRATOR - has 10, MISSING 8`*** (`CREATE.ACCOUNT DELETE.ACCOUNT MODIFY.ACCOUNT UPDATE.ACCOUNTS GRANT REVOKE LIST.GRANTS UNLOCK`); `TADM: ADMINISTRATOR - has 18, MISSING 0`; `PETE`/`TSTD` STANDARD and `TPROG` PROGRAMMER out of scope; `SDSYS` tier `(none)` out of scope; `6 account(s) in the register, 2 ADMINISTRATOR, 1 short`. ***WITNESSED 11 Sep 23:55 ON INSTALL `06d3a4a` (upgrade cycle, accounts KEPT, `assert-current` 0): `verify-tier-layer.sh` EXIT 0 — `DON: ADMINISTRATOR - has 18, MISSING 0`, TADM 18/18, `6 account(s) … 2 ADMINISTRATOR, 0 short`.*** DON's `COUNT VOC` went ***411 → 419, exactly +8***, matching the 8 it had been missing — so nothing was double-added or overwritten. ***THE RESULT IS ATTRIBUTABLE TO THE NEW LAYER PASS AND TO NOTHING ELSE, CHECKED RATHER THAN ASSUMED:*** all 8 ids are in VOC_TEMPLATE and ***NONE is in NEWVOC***, so the pre-existing NEWVOC walk could not have written any of them. ***IDEMPOTENCE WITNESSED SEPARATELY:*** a second `UPDATE.ACCOUNTS` on DON (mode 2, plain `don`, no sudo) printed no `+` and no 10912, and `COUNT VOC` stayed 419 — it adds only what is absent. ***NOT SEEN: the install's own output***, so whether 10912 was displayed during the walk is unconfirmed; the mechanism is witnessed by the before/after and the count, not by the message. ***The verifier is committed rather than left in a scratchpad*** (`gplbld/verify-tier-layer.sh` + `.bp`, no sudo, exit 0 complete / 1 SHORT / 2 cannot answer) because the invariant recurs at every release that adds a verb. ***IT PAID FOR ITSELF WHILE BEING WRITTEN:*** the first probe compiled 0 errors and then aborted at run time on `select … to 11`, a numbered list above `HIGH_USER_SELECT` that a non-`$internal` program may not use (`sd.h:48`) — it printed a heading and no verdict, so the script now confirms the RUN on the summary line and not the compile | `upgrade-voc.ps1` | `installsdai.sh` when accounts are kept |
| 17 | MODIFY.PASSWORD — ***INSTALLED (`0095937`) AND WITNESSED 12 Sep: `gplbld/verify-setpw.py` 24 of 24, as `don`, no sudo, nothing changed.*** The three refusals reachable without sudo all fire, ***the ordering is proven (grammar before privilege: `MODIFY.PASSWORD PETE somethingextra` → 5276, NOT 2001)***, and the CONTROL gets past the syntax check to `passwd(1)`, is refused a wrong current password (10915, no 10914), and leaves `passwd -S don`'s last-change date unmoved at `2026-09-08` — before AND after. ***SO PORT_ADOPTION 17's UNWITNESSED PREMISE IS NOW MEASURED: the current-password demand comes from PAM, not from SD code*** (row C4 saw `Current password:` printed by `passwd`, not by SD). ***STILL NOT REACHABLE WITHOUT sudo, and the file says so rather than scoring it:*** 5018 and 10913 (the privilege test fires first for any account but your own) and the whole administrator arm (`!set_passwd` → `sd-elevate`). *(Earlier: BUILT AND COMPILED 12 Sep, NOT INSTALLED, NOT RUN; TIER PLACEMENT RULED 12 Sep, ADMINISTRATORS ONLY, see below.)* `GPL.BP/SET_ACC_PASSWORD` (`$MODIFY.PASSWORD`), the port's grammar and its refusals; `VOC_TEMPLATE/MODIFY.PASSWORD` + the name in `TIER.ADD.ADMINISTRATOR`, ***the port's placement*** (its `modify.password` is `voc_template`-only and in its tier list). Messages 5276 byte-identical to the port, 10913/10914/10915 Linux-only. ***THE CREDENTIAL HALF IS GONE AND THAT IS THE LINUX DESIGN, NOT AN OMISSION:*** the port keeps a `$cred` SCRAM register because a Windows SD account is not a Windows logon; ***here an SD account IS a Linux user*** (sd not setuid, the session runs as that user, LOGIN's gate is group membership), so the account's password is the Linux password and a second one could only disagree with the real one. No `$cred`, no `!CRED_SET`, no `!CRED_VERIFY`. ***SD NEVER SEES A PASSWORD*** — it does not prompt, hold or pass one; both arms hand off to `passwd(1)`. ***THE ARMS SPLIT ON `kernel(K$ADMINISTRATOR)`, NOT ON "own"***: an administrator session (which on Linux means `sudo sd`, `CPROC:328`) goes through `!set_passwd` → `sd-elevate passwd <user>` as root, no current password asked; any other session may reach only its OWN account and runs `passwd -- <user>` as itself, so ***"you must know your current password" is enforced by PAM and not by SD code***. ***THE USER NAME IS ALWAYS EXPLICIT*** — a bare `passwd` under `sudo sd` would target ROOT. A GROUP or OTHER account is refused (10913): no single person, no password. Compile: dev binary 0 errors no warning, red control `QBAD` 3 errors, tree rebuilt PLAIN, DON `COUNT VOC` 419. ***RULED BY THE OWNER, 12 Sep 2026: ADMINISTRATORS ONLY — full parity with the port — AND HIS REASON IS NOW A PROJECT STANCE (CLAUDE.md, 12 Sep): "Security starts tighter but can be relaxed by choice."*** The question put to him was whether a STANDARD account should have the verb, since PRE_RELEASE 13 forces one into `sd` over ssh. His answer was not that standard users should be denied it, but that ***the default should be off and the administrator should decide***: one who wants a particular user to set their own password copies the VOC record into that account, which works and grants nothing else (traced below). ***SO THE PLACEMENT IS FINAL AND IS NOT A GAP TO BE CLOSED LATER*** — `MODIFY.PASSWORD` stays out of `NEWVOC`, and a session that finds a standard user unable to change a password is seeing the ruling, not a defect. ***THE NON-ADMIN ARM IS STILL REACHABLE AND IS NOT DEAD CODE:*** only an ADMINISTRATOR-tier account holds the verb, but such an account in a PLAIN `sd` session has no `K$ADMINISTRATOR` (that flag needs `sudo sd`, `CPROC:328`), so an administrator changing their OWN password without sudo runs `passwd -- <user>` as themselves and PAM demands the current one. That is the common case, not an edge. ***AND THE RULING IS ENFORCED BY WHERE THE VOC RECORD IS, NOT BY THE CODE — traced 12 Sep after the owner asked what happens if an administrator copies the record into a STANDARD account.*** It WORKS, and it is safe: the program never consults the caller's tier (checked), `os.execute` is permitted because the program is `$internal` — `os_permitted()`'s FIRST answer, before tier and before any OS-ON grant — and the register is world-readable, so the lookup succeeds. Such a user gets `passwd -- <themselves>` with PAM demanding their current password, which is what a shell would have given them; `modify.password <anybody else>` is still 2001, because `K$ADMINISTRATOR` needs `sudo sd` and they cannot sudo. ***SO THIS IS A POLICY BOUNDARY, NOT A CONTAINMENT ONE:*** even if the record reached every account, nobody could set another's password. Copying it into one account is therefore a safe deliberate escape hatch — with two wrinkles: ***an upgrade will NOT take it back out*** (`update.voc` never deletes and queue 16's layer pass only adds, and only to ADMINISTRATOR accounts), while ***a tier change WOULD*** (`voc.delta` on a demotion from ADMINISTRATOR removes layer records still matching the tier build, and `MODIFY.PASSWORD` is in `TIER.ADD.ADMINISTRATOR`). ***Code trace, not a measurement: queue 17 is not installed yet.*** | `SET_ACC_PASSWORD` | `sd-elevate passwd` / `passwd(1)`; no `$cred` |
| 18 | Lower-case conversion §M — ***COMPLETE, NOT THE PORT'S PARTIAL RESULT*** (owner, 11 Sep; see below) | port 5.12 | release-blocking; goes past the port |
| 19 | Register/OS reconciliation at start (port 93 and 65). ***BUILT AND WITNESSED 12 Sep against a fixture; `sd.service` RUNS `--sweep`, RULED BY THE OWNER 12 Sep. NOT YET RUN ON A REAL START.*** `gplbld/reconcile-accounts.sh`, installed as `/usr/local/sbin/sd-reconcile-accounts` beside `sd-elevate` and `ssh-forcecommand` (root-owned, removed by `deletesdai.sh`); `sd.service` gains `ExecStartPre=-… --list`, ***the leading `-` load-bearing*** because the script exits 1 on a finding and a stale record must never refuse to start SD. ***THE REVIEW THE ROW ASKED FOR FOUND A LINUX HAZARD THE PORT DOES NOT HAVE, AND IT IS THE REASON THE SWEEP IS NOT WIRED:*** `!is_user` (`IS_USER:52`) does `openpath "/etc"` and reads `passwd` ***DIRECTLY, never NSS***, while this machine's `/etc/nsswitch.conf` reads `passwd: files systemd sss` with sssd ***enabled*** though inactive (measured 12 Sep). So on a domain-joined install the system resolves users SD cannot see at all, and a sweep keyed on SD's view would mark ***every*** directory-backed account stale and delete its directory. The script therefore asks ***two*** sources and acts only when both say absent; `NSS yes / files no` is refused by name and reported, because it is a real defect of its own (SD blind to directory users) rather than a stale record. The port's three rules are carried: type read from `ACC$GROUP` not guessed (SDSYS exempt by rule and again by name — the port's own first attempt marked it dead); "could not tell" is never "no", with a control that `getent passwd` return a plausible count before any verdict; directory first, then record, since the record is the only handle on the directory. ***WITNESSED 12 Sep against a fixture tree*** (`--sdsys`/`--accounts-root` exist for this): clean register → `5 live, 0 stale`, exit 0; fixture → `STALE ZZGONE` removed directory ***and*** record under `--sweep`, `STALE ZZELSEWHERE` ***KEPT because field 1 was `/etc`*** and `/etc` verified intact afterwards, `ZZGROUP` skipped as not `sdu_`, `ZZLIVE` live; exit 1. Control: `--sweep` against the real register as `don` refuses. ***The root test is "can I write the register", not "am I uid 0"*** — a caller who can write it could `rm` the records anyway, and the writability form is what let the REMOVAL path be exercised at all before being pointed at real accounts. ***RULED BY THE OWNER, 12 Sep 2026: SWEEP, full port parity*** — `sd.service` runs `--sweep`, the register self-cleans at every start and the stale account's directory goes with the record. ***AND THE DIRECTORY HALF IS NOT A HARD CALL, BECAUSE THE TIER MODEL ALREADY HAS A PLACE FOR "KEEP THE DATA"*** (owner, 12 Sep): *"this is why suspended accounts exist - you want to retain data, suspend the account; you want everything deleted, delete the account."* A stale record means somebody DELETED the Linux user, which is the second of those, so taking the directory with it carries out the intent rather than destroying something meant to be kept. ***SO THE ONLY THING THIS SCRIPT HAS TO GET RIGHT IS "IS THE USER REALLY GONE", NOT "SHOULD A GONE USER'S DIRECTORY GO"*** — every guard in it is about the reliability of that one lookup, and a future session should not add one that second-guesses the removal. ***AND WIRING IT SURFACED A BOOT-TIME HAZARD THE PER-RECORD TEST CANNOT SEE, SO THE SWEEP CARRIES A SECOND GUARD:*** `ExecStartPre` can run ***before*** sssd or nslcd is up, and a directory user is then absent from NSS ***and*** from `/etc/passwd` — byte-for-byte the signature the sweep treats as "gone" — so their directory would be deleted because a name service was slow. No per-record test can separate those two states. ***So the question is asked one level up:*** if `nsswitch.conf`'s `passwd` line names any source outside `files/systemd/compat/db/cache`, `--sweep` refuses and reports instead; `--allow-remote-nss` overrides. On a files-only machine, which is what the installer targets, nothing changes and the sweep runs as ruled. ***CONSEQUENCE ON THIS BOX, MEASURED: it will REPORT, not sweep*** — `passwd: files systemd sss`, so the guard fires; removing `sss` from `nsswitch.conf` or passing the override is what makes it sweep here. Both halves witnessed 12 Sep against a fixture: with the guard the directory survived and the row read "would remove"; with `--allow-remote-nss` the directory and record were removed and the register left empty | `reconcile-accounts.ps1` | two-source lookup; `/usr/local/sbin`; no `os.users` half here |
| ~~20~~ | ~~UPSTREAM 4, 6, 13, 34~~ — **DONE 11 Sep**: 13 built + witnessed on the tree binary, 34 built (DELETEF), 4 does not apply, 6 → queue 18 | — | — |
| 21 | `check-stale-leads.py` (PRE_RELEASE 9 here) — ***BUILT AND RUN 12 Sep; IT FOUND THREE REAL LEADS ON ITS FIRST RUN AND TWO WERE AN HOUR OLD.*** Not the port's script and could not be: PRE_RELEASE 9 records the verbatim copy exiting 2 before any phase (*"REFUSING - could not bound section 7"*) because it is keyed to the port's structure, and it was removed rather than committed since a tool that always exits 2 reads like a guard the project has. This one is keyed to the shapes here — numbered table rows in PORT_ADOPTION / PRE_RELEASE_FIXES, and top-level bullets with their indented continuations in PROJECT_STATUS. ***ONE PHASE ONLY, AND IT SAYS SO*** — the port's other two need a task table this tree lacks and judgements a word-matcher cannot make; PRE_RELEASE 9's lesson is that one phase that runs beats three that half-run. ***TWO THINGS MAKE IT PRECISE RATHER THAN NOISY, AND BOTH WERE PAID FOR IN THE WRITING.*** (1) ***The LAST status word in the opening decides, not the first*** — queue 19's row opened "REPORT HALF BUILT AND WITNESSED …; THE SWEEP IS BUILT AND NOT WIRED, PENDING A RULING", and taking the first scored it closed and missed it. (2) ***Only UPPER CASE counts***, which is CLAUDE.md's own convention ("ALL-CAPS and bold mean this was paid for") — case-insensitive matching read "installed as `/usr/local/sbin/…`" as a status claim and scored row 19 clean again. Cost accepted: a lower-case "unrun" is missed; precision beats recall in a tool nobody will keep running if it cries wolf. Two tiers: ***opens OPEN → later CLOSED is a LEAD and sets exit 1***; opens CLOSED → later OPEN is the house style ("WITNESSED … NOT WITNESSED: which part", which CLAUDE.md asks for) and is listed without affecting the exit. Null case refused out loud: a document yielding no entries exits 2, because the shapes would have drifted and every clean verdict be worthless. ***FIRST RUN: 288 entries, 3 LEADS — rows 15, 17 and 19, all written by this session, all appended-correction-without-striking-the-lead.*** All three openings rewritten; ***the re-run leaves 1, row 19, READ AND ACCEPTED***: "NOT YET RUN ON A REAL START" and "WITNESSED against a fixture" are both true, and the entry was not distorted to force a green. Exit 0 is therefore NOT the goal — this ranks entries for reading | `check-stale-leads.py` | this tree's row and bullet shapes; upper-case-only matching |
| 22 | Verifier intent (the port's `verify-*`/`test-*` .ps1) — ***HARNESS BUILT, UNIT-TESTED AND WITNESSED 12 Sep: `verify-vocverbs.py` 34/34 on install `0095937`, `assert-current` 0, row B4 FAIL→PASS.*** The 79 instruments are classified below and the worklist is ranked. See "Queue 22" | `gplbld` | Python, per PRE_RELEASE 1 |
| ~~23~~ | ~~`.D name`~~ — **BUILT 11 Sep** | `CPROC` | |
| ~~24~~ | ~~BCOMP unterminated TRANSACTION~~ — **BUILT 11 Sep** | `BCOMP` | |
| 25 | Process dumps in their own directory, writable but not readable by SD users (port 28) | `sd.conf DUMPDIR`, installer | mode/group bits instead of the port's ACL; `pdump.c` already honours `DUMPDIR` |
| 26 | ***WITNESSED 11 Sep 14:48 on install `c2b375d`:*** `printf 'WHO\n' \| timeout 10 sd` → `4 DON`, exit 0, 0.01 s, 0 BEL (was exit 124, 369 207 BEL); control with `OFF` exit 0, 0 BEL; no dead slot in LISTU; the session still wrote its `LOGIN` audit record. ***The `:` prompt busy-loops at end of input*** (Linux-found 11 Sep, measured; PROJECT_STATUS START HERE). ***BUILT 11 Sep, COMPILED, NOT INSTALLED:*** CPROC `:1006` `if c = '' and status() = ER$EOF then goto int.quit`; dev binary `-internal BASIC BP CPROC` 0 errors, red control (CPROC + trailing text) 1 error; changelog entry. Witness after install: `printf 'WHO\n' \| timeout 10 sd` ends exit 0 with no BEL, no dead slot in LISTU; control: the same with `OFF` unchanged. At EOF the command processor ends the session as `OFF` does, the shell convention; `INPUT` in programs keeps returning `''` | none — port not measured | CPROC `get.command.line` (`:954`): `keycode()` = `''` with `status()` = ER$EOF (3030) → log out. ***Premise measured 11 Sep*** (probe `KCEOF`, last line of piped input, installed binary): `KEYCODE()` → len 0, `STATUS()` 3030; `KEYIN()` → len 0, 3030 |
| 27 | ***WITNESSED 11 Sep 14:49 ON INSTALL `c2b375d`:*** `MKSEQ` (`OPENSEQ` new file ELSE, `WRITESEQ` ×2, `CLOSESEQ`, reopen, `READSEQ`) → file 18 bytes, both lines read back; `LIST.READU` no locks before, after, and from a second session. (The orphan probe was not run live.) ***CAUSE FOUND, AND IT IS A PORT FIX NOT YET ADOPTED — BUILT 11 Sep.*** `op_seqio.c` `exit_op_openseq` tested the saved `status` (a 2026/06/10 cleaning-cycle change, `AI_Modification_Notes/C_Code/ChangesApplied.txt:132`, committed `9f82a52`) instead of `process.status`, so on `ER_RNF` — the new-record ELSE, a success — it freed `fvar` and `sq_file` that `fvar_descr` already pointed at and kept the record lock taken at `:652`. The port reverted it 15 Aug 2026 (port `op_seqio.c:835`, its PROJECT_STATUS §2 generation-2 audit); `9f82a52^` had `if (process.status)`. Reverted here to match, with the port's reasoning. ***WITNESSED 11 Sep in the sandbox, HEAD-`op_seqio.c` binary vs reverted binary, same account copy:*** probe `MKSEQ` (`OPENSEQ` new file ELSE, `WRITESEQ` ×2, `CLOSESEQ`, reopen, `READSEQ`) — **before: both `WRITESEQ` fail `3013` (`ER_NSEQ`), nothing written, reopen takes ELSE, and an `RU` lock on `mkseq.out` is stranded despite the `CLOSESEQ`** (owner `(gone)`); `ORPH` strands a second. **After: file created (18 bytes), both lines read back, `GETLOCKS()` empty; `ORPH` + `OFF` leaves no lock, `LIST.READU` "no active … locks", a second `ORPH` completes.** So every install since `9f82a52` could not create a sequential file this way. Live at 12:22: no stranded locks (the 05:05 reboot cleared any). Sweep of the port's generation-2 C findings (its HISTORY "ARCHIVE 21 Aug 2026", C side): `ctype.c` and `op_sdext.c` `malloc(1)` → NULL already here (10 Sep); this revert; `dh_open.c:257` trigger-on-OOM identical in both, flagged-not-fixed in the port too. Original measurement follows. ***An `OPENSEQ` that takes the ELSE branch leaves an update lock that outlives `OFF`*** (Linux-found 11 Sep, measured in the sandbox; the overnight hypothesis (1), confirmed). Probe `ORPH`: `OPENSEQ '/proc/999999999/status'` → ELSE with `STATUS()` **0** even though the directory does not exist; ends without `CLOSESEQ`; `OFF`. Then `LIST.READU` shows user 25 holding `RU` on id `status` in **file 3, the account system's VOC entry** — not the path opened; 25 is not in LISTU; a second session's same `OPENSEQ` waits until killed. Nothing clears it short of an SD restart: cleanup's `remove_user()` (`clopts.c:399`) acts only on registered dead slots. Leads, unverified: `get_file_entry()` matches by name when device and inode are 0 (`dh_open.c:455`), and `op_openseq` leaves them 0 for a path that does not stat (`op_seqio.c:420-421`); `unlock_record()` frees through the process's LLT list by `fno` + `fvar_index` (`op_lock.c:1387-1394`) | none — port not measured | find why the lock lands on file 3 and why neither the variable's release (`op_dio1.c:432`) nor logout frees it; do not recreate it on a live system |
| 28 | `RUN` of a runfile path over 128 characters fails `1135 Invalid runfile pathname` (`op_jumps.c:811-813`, `MAX_PROGRAM_NAME_LEN`) — measured on a sandbox account whose `BP.OUT/HOLD16` was 135. Low: accounts under `/home/sd/user_accounts` are far shorter, and a catalogued verb is found by path (limit 255) | — | lift the limit, or have 1135 say what the limit is |

## Queue 22 — the port's 79 test instruments, classified (12 Sep 2026)

PRE_RELEASE 1's complaint was that the plan has **no answer** for the port's
PowerShell helpers. This is the answer for the testing half: 51 `verify-*.ps1`
and 28 `test-*-units.ps1`, each read for its own stated intent (every one
carries it in its first comment or `.SYNOPSIS`), then classified against what
exists on Linux.

**Built this session.**

| File | What it is |
|---|---|
| `gplbld/sdverify.py` | The shared harness: result rows with a DECISIVE flag, the verdict (***no decisive row = FAILED***), case-sensitive regex helpers, the `sd` pipe driver, and the exit-2 preconditions. `--selftest` 26 cases, 0 failed |
| `gplbld/test-sdverify-units.py` | 34 cases, 0 failed. Drives the DRIVER against stub `sd`s — timeout, non-zero exit, ANSI, BEL — including the arms that must FAIL. Red control: `verdict()` mutated to pass the null case → 3 failures, exit 1 |
| `gplbld/verify-vocverbs.py` | The first verifier on it. Queue 1, 3 and 3b. No sudo |

***ONE MODULE, NOT 51 COPIES, AND THAT IS THE ADAPTATION.*** The port copies
the table, the verdict line and the driver into every verifier, and needs
`test-verdict-units.ps1` to assert the verdict line has stayed byte-identical
across four of them. That is a check on a smell. Importing it makes the drift
impossible and leaves one implementation to test.

**`verify-vocverbs.py` against install `06d3a4a`, 12 Sep, as `don`, no sudo:
33 of 34 decisive rows pass; row B4 FAILS, and B4 is the row the port's own
verifier does not have.** Detail under "Queue 22 — the defect the first
verifier found" below. The before-measurement is banked; the after-witness is
owed from the next install.

**The 51 verifiers, by what Linux does with the intent.**

| Class | Port files | Disposition |
|---|---|---|
| **Done here** | `vocverbs` | `verify-vocverbs.py`, this session |
| **Partly covered — an instrument exists, the port asserts more** | `tiers`, `registersweep`, `register`, `upgrade`, `doors`/`doors-admin`/`doors-suite`, `sshonly`, `allowgroups`, `accountrules` | `verify-tier-layer.sh` (queue 16), `reconcile-accounts.sh` (19), queue 12's SUSPENDED witness, `test-ssh-forcecommand.py` (PRE_RELEASE 13), `witness-adopt.sh` (15). The gap in each is the port's extra rows, not the mechanism |
| **To build — mechanism exists here, NOTHING measures it** | `setpw`, `txn`, `basicfuncs`, `parsertokens`, `keys`, `lineendings`, `nonet`, `nocase`, `editors`, `createaccount`, `delaccount`, `acctmsgs`, `catgate`, `cmdaudit`, `batchjob`, `logtoaccess`, `sdsysgate`, `sdsyswrite`, `sysdiracl`, `pcodeacl`, `accountacl`, `tierchange`, `notyet` | The worklist. Ranked below |
| **Routed to §M / queue 18** | `fold`, `lcnames` | Their intent IS the lower-case ruling; building them separately would fork it |
| **Unruled — depends on the API's state here** | `apiadmin`, `apiidentity`, `apiname`, `apiport`, `apiremote`, `tierapi`, `scramlogin`, `localconnect`, `peerlog`, `routes` | The `$cred`/SCRAM half is already "Not adoptable"; what remains of the API surface has not been walked. ***Do not build these until that walk happens*** |
| **No counterpart** | `osusers` (privilege model), `credacl` (SD never sees a password — queue 17), `profiledir` (Windows profile dir; the Linux analog is queues 15 and 19), `privundetermined` (Windows token) | Already in "Not adoptable" |
| ***Divergent — the port's assertion is INVERTED here*** | `sshadmin` | It proves an SD ADMINISTRATOR gets **no** ssh session. Here PRE_RELEASE 13 ruled the opposite and it is live-witnessed: ***a STANDARD account is forced into `sd`, an administrator gets a shell.*** A Linux `verify-sshadmin` must assert the Linux ruling. **Adopting the port's wording here would have written a passing check for behaviour this project deliberately does not have** |

**Ranked worklist for the "to build" class**, by what is unwitnessed today
rather than by how hard it is:

1. ~~`verify-setpw`~~ — ***DONE AND WITNESSED 12 Sep, `gplbld/verify-setpw.py`,
   24/24.*** See queue 17. It is the worked example of why the port pairs a
   treatment with a control: rows T1-T3 are refusals, and ***a verb that
   refused everything would have scored all three*** — C1-C5 are what stop
   that, by reaching `passwd(1)` and proving nothing changed.
2. ~~`verify-txn`~~ — ***DONE AND WITNESSED 12 Sep, `gplbld/verify-txn.py` +
   `verify-txn.bp`, 29/29; RED CONTROL `--probe` with the lock removed → 11 of
   29 fail, exit 1.*** Step 2's A2 write and A2 delete "cheap checks, none run"
   are now RUN. ***BOTH OF THE PORT'S HEADLINE DEFECTS ARE ABSENT HERE:***
   `SYSTEM(1008)` returns to 0 after COMMIT (L0 0 → L1 1 → L2 0), and a nested
   commit does NOT orphan the outer cache — the outer's `S2` written *before*
   the inner transaction still lands. ***SECTION 3 USES TWO INSTRUMENTS AND
   THEY AGREE:*** SD reads `,` and `=` back, and on disk the names are `%C` and
   `%E` with `%Y` gone and ***no raw-id file of any of the three***.
   ***STILL NOT COVERED, AND DELIBERATELY NOT ATTEMPTED ON THE LIVE SYSTEM:***
   A3 and A1's undo/locks need an INDUCED commit failure (a read-only record
   file, or one a second session holds). Given the 11 Sep wedge and queue 27's
   stranded lock, that belongs in the sandbox recipe, not in DON.
3. ~~`verify-editors`~~ — ***DONE AND WITNESSED 12 Sep, `gplbld/verify-editors.py`
   28/28, plus `test-editors-units.py` 19/19.*** The NANO/MICRO work of 10 Sep
   is no longer "COMPILED, NOT RUN" for everything except what a person must
   see. ***THE PORT'S QUESTION DID NOT TRANSFER WHOLE:*** it bundles the
   editors SHA-pinned and asks "is the bundled copy the one EDIT resolves";
   here they are deliberately NOT bundled (Microsoft Edit is not packaged for
   Linux; `find.editor` is `command -v` with an absolute path required,
   `EDIT:394-397`), so the Linux question is whether the SYNTAX CONFIGURATION —
   the part this project actually ships — is placed where the editor reads it.
   ***ROW A2 IS A GAP THE PORT DOES NOT HAVE:*** shipping
   `/usr/share/nano/sdbasic.nanorc` achieves nothing unless `/etc/nanorc`
   ***includes*** it, and that file is Debian's, not this project's.
   ***MEASURED: `/etc/nanorc:257` is live and globs the directory*** — and the
   three commented includes sitting directly below it are exactly why A2 parses
   the line instead of searching for the filename. ***ALSO WITNESSED: EDIT's
   TERMINAL GATE***, which refuses before opening anything — *"nano needs a
   terminal to draw on, and this session has none. ed, the line editor, works
   anywhere"* — and that gate is what makes the verb safe to drive down a pipe
   at all.
4. `verify-lineendings`, `verify-nonet` — pure tree checks, no `sd`, no sudo;
   `nonet`'s intent guards a project **stance** (the shrink), so it stays
   useful after the queue is empty.
5. `verify-basicfuncs` — the widest coverage per line of any of them.
6. The account family (`createaccount`, `delaccount`, `acctmsgs`,
   `accountrules`) — one cycle's worth, and it wants the FULL delete→install
   this file already owes.
7. The POSIX-mode family (`sysdiracl`, `pcodeacl`, `accountacl`, `sdsyswrite`,
   `sdsysgate`, `catgate`) — the port's ACL checks re-expressed as mode,
   ownership and group. Readable without sudo; **the writes they must attempt
   are not**, so each needs an owner-run half.

**The 28 `test-*-units.ps1` are not ported one for one, and the reason is the
one above.** They exist because the port has 51 independent verifiers whose
shared parts drift; two thirds of them test a helper this project either does
not have (`sdpath`, `elevonce`, `reclaim`, `stripcomments`, `upgradevoc`,
`dirscoverage`, `stemcoverage`, `suiteonly`, `diffcapture`, `transcriptwhole`)
or has already unit-tested under its own name (`test-sd-elevate.py`,
`test-ssh-forcecommand.py`, `test-assert-current.py`,
`test-edittokens-units.py`, `test-reconcile-units` → `reconcile-accounts.sh`'s
fixture run). **The intent that DOES transfer is "unit-test the instrument
before trusting it", and `test-sdverify-units.py` is where it now lives** —
one file for the shared half, and a per-verifier units file only where a
verifier grows logic of its own.

## Queue 22 — the defect the first verifier found (12 Sep 2026), FIXED AND WITNESSED

***WITNESSED ON INSTALL `0095937`, 12 Sep 01:50:36, `assert-current` 0, as
`don`, no sudo: `verify-vocverbs.py` 34 of 34 decisive rows, row B4 FAIL→PASS.***
The transcript is the evidence and not the verdict line: `DELETE.FILE ZZVVF
NO.QUERY` now prints 6145, then 10117, then goes straight to *"DICT part of
file does not exist"* and *"VOC entry 'ZZVVF' deleted"*. **No 6135, 0 BEL,
0.01 s, and the commands that follow it are no longer eaten.** The same run's
C rows (the lower-case fixture) and D rows (QSELECT's list number) pass, so
queue 1 and queue 3b are witnessed on this install too.

***AND THE DEFECT AS IT WAS, KEPT BECAUSE THE BEFORE-MEASUREMENT IS THE HALF
THAT PROVES THE FIX DID SOMETHING.*** On install `06d3a4a`,
`DELETE.FILE <ptr> NO.QUERY` honoured NO.QUERY and then asked a question
anyway, three times, on an empty path — and ate the two commands that
followed. Fixture was a copy of the account's own `SYSCOM` pointer.

- **Cause**, read after the measurement, not before: `DELETEF:232`'s `continue`
  re-entered the DATA loop at its FIRST statement rather than at `while more`,
  so `remove` ran again on an exhausted list and handed back an empty
  `data.path`; the empty path then failed the `data.path # default.path` test
  and raised 6135. ***The file's own 2024 comment predicts exactly this*** —
  *"using continue here will create endless loop"* — and the sibling site at
  `:265` already used `goto more_test` for it.
- **Fix**: `goto more_test`, the idiom the file already uses. `DELETEF:229-246`.
  Compiled 0 errors (dev binary, staged in DON/BP); ***red control: an
  unbalanced `<` in the same block → 1 error naming line 252.*** Tree rebuilt
  PLAIN. ***INSTALLED AND WITNESSED — see the top of this section.***
- **It is not the endless loop the 2024 note feared** only because the 11 Sep
  Enter=N fix turns end-of-input into N.
- ***THE OUTCOME WAS RIGHT AND ONLY THE ROUTE WAS WRONG*** — the VOC entry went,
  the system file stayed. That is why it survived: an outcome check cannot see
  it. B4 checks the ABSENCE of the prompt.
- ***THE PORT HAS THE SAME CODE at `gpl.bp/DELETEF:246`, AND ITS OWN
  verify-vocverbs.ps1 WOULD PASS ON IT*** — that script checks 10117 and the
  absence of 6146 on this fixture, and both were true here while the verb
  prompted three times. **Not measured on Windows.** Owed to the port as
  `BUGS_FROM_LINUX_PORT.md` 8, through a fresh clone; not yet filed.

## Queue 18 — lower case: the owner's ruling and where the port stopped short

***OWNER, 11 Sep 2026: "here everything needs to be lowercase so that we don't
have the situation of multiple commands, files or record ids that have the same
name but multiple casing."*** The port's §5.12 set that goal and did not reach it
— NTFS matches names regardless of case, so what was missed never failed there.
Filed to the port as a bug for its next version (`BUGS_FROM_LINUX_PORT.md` 5).

**Nothing of §M exists here yet** — measured 11 Sep: sdsys directories 12 of 18
upper, `NEWVOC` 395 upper / 1 lower, `VOC_TEMPLATE` 418 upper, and 0 lookups in
`GPL.BP` with a lower-case tier (the port has 76 in 38 files).

**What the port left upper case — do each of these here, rather than copy the
port's result** (measured on the port tree 11 Sep):

| Left upper in the port | Where | Plan §M covers it? |
|---|---|---|
| Files `CREATE.FILE` makes: OS name upper-cased unless `CREATE.FILE.CASE` is set, and nothing sets it | port `CREATEF:309-311` (here `:304-306`) — `create.file zzak` made `ZZAK` on this box | **no** |
| All 203 `gpl.bp` program sources, 12 of 15 `syscom` includes | `CPROC`, `QSELECT`, `ERR.H`, `KEYS.H` … | **no** |
| Case inversion at sign-on | port `LOGIN:624` / here `:250`, `pterm(PT$INVERT, @true)` | **no** |
| Account names, "forced to uppercase" | port `syscom/KEYS.H:269` | kept deliberately by the plan (§M3) — ***RE-RULE*** |
| VOC ids `$ACC`, `$MAP`, `$RELEASE`, `SD.VOCLIB`, `TIER.ADD.ADMINISTRATOR`, `TIER.OMIT.STANDARD` | port `newvoc`, `voc_template` | partly — §M3 renames "the `$` records" without naming these |
| Lookup sites the first pass missed | `.D` (port entry 5, open here — audit below), `_VOC_REF`, the `$SAVEDLISTS` literals | yes for the last two |

Not names, so correctly left alone: `%E` `%G` `%L` (and pairs) are the escaped
filenames of records `=` `>` `<`; `#` `&` `!` are symbols.

***OPEN FOR THE OWNER, NOT RULED:*** does "record ids" reach **record ids in a
user's own data files**? Plan §M3 keeps directory-file record ids case-sensitive
on ext4 because `SUE` and `sue` are two files there. Forcing an application's
data ids to lower case would change its data, so this was not assumed either way.
Likewise account names (row 4 above).

## Queue 3 — measured here, 11 Sep 2026, not read

***`delete.file zzak no.query` PROMPTED ANYWAY***, on an ordinary account file
with no system-account part, on the `af879d3` install. Measured while clearing a
DELETE.INDEX fixture, not while looking for it:

```
:delete.file zzak no.query
OK to delete DATA portion 'ZZAK'? OK to delete DATA portion 'ZZAK'? ...
```

**Two separate faults. The first is the port's UPSTREAM 27, which this file
failed to list; the second is in no UPSTREAM entry.** *(Corrected 11 Sep: an
earlier version of this note said UPSTREAM 23 named neither and presented fault
1 as new. The port had already written it up as #27 — "Separate from #23".)*

1. ***`NO.QUERY` IS PARSED AND SIMPLY DOES NOT REACH THESE TWO PROMPTS***
   (= UPSTREAM 27). `DELETEF:84` sets `no.query` and `:109` honours it for the
   select-list query, but the DATA-portion prompt at `DELETEF:221-232` and the
   DICT-portion prompt at `:295-304` are each guarded by ***`if not(force)`
   ALONE***. UPSTREAM 23 is the separate `check.sdsys.file` prompt; queue 3
   must take both 23 and 27.
2. ***BOTH PROMPTS BUSY-LOOP ON EOF, BY CONSTRUCTION.*** Each is
   `loop … input yn … until yn = 'Y' or yn = 'N' repeat`. At EOF `input` yields
   empty, `yn[1,1]` is neither `Y` nor `N`, and the loop has no escape — it spins
   rather than blocking (pid observed in state `R`, 98.9 MB in 40 s). The same
   `loop/until` shape is at `:112`, `:155`, `:187` and `:350`, so this is a
   pattern in the verb, not one bad site.

***AND IT IS NOT ONLY `DELETEF` — `LOGIN:492-511` HAS THE SAME SHAPE IN THE
SIGN-ON PATH*** (found 11 Sep while diagnosing something else, and it was NOT
the cause of that). The `$RELEASE` check compares field 2 of the account's VOC
`$RELEASE` record with `SD.REV.STAMP` and, when they differ, enters
`loop … display 5026 … input s …` with cases for `Y` and `N` only, a `display
char(7)` per turn and ***no EOF escape***: a terminal waits for ever, a pipe
spins on 5027 with a BEL each time. ***QUIET TODAY BECAUSE NOTHING DIFFERS —
measured 11 Sep, probe `RELPROBE`, all 6 accounts and the binary at `L1.0-0`***
— so it fires only on the first sign-on after a release change, which is
precisely when an installer or a script is driving `sd`. Fix it with queue 3's
fix, not separately.

**Why a plain `zzak` hit it — settled by UPSTREAM 27, and consistent with what
was measured:** the test is `data.path # default.path` (`:221`) with
`default.path = file.name` (`:219`), and `CREATE.FILE` upper-cases the OS name
unless `CREATE.FILE.CASE` is set, so `zzak` is stored as `ZZAK` (seen on disk:
`/home/sd/user_accounts/don/ZZAK`) and the two always differ for a lower-case
name.

**Consequence for instruments:** drive `sd` down a pipe only with verbs known not
to prompt, and always under `timeout`. `list.index` hung the same way earlier in
the session. The clean-up that avoids the verb entirely is `rm -rf` the file's
two directories plus `DELETE VOC <name>`.

## Not adoptable — code, feature, reason

| Port code | Feature | Why it cannot be adopted or adapted on Linux |
|---|---|---|
| `sd.iss`, `stage.py`, `bootstrap.py`, `test-upgradeiss-units.py`, `finish-install.ps1`, `install-service.ps1`, `check-install.ps1` | Windows installer and service | Inno Setup and the Windows service manager; the Linux installer is `installsdai.sh` |
| `ELEVATE`, `elevate-once.ps1`, `sd-elevate.ps1`, `sd-elevate-helper.ps1`, `PS_SCRIPT`, `PS_SCRIPTO` | Elevation | UAC and PowerShell do not exist; Linux uses `sudo` + `gplbld/sd-elevate` |
| `OS_GROUP`, `DELETE_USER` profile half, `PROFILE_DIR`, `reclaim-profiles.ps1`, `clean-test-profiles.ps1`, `secure-reclaim.ps1` | Local groups and user profiles | Win32 group APIs and the registry ProfileList; Linux: `sd-elevate` group verbs, `userdel [-r]` |
| `CRED_SET`, `CRED_VERIFY`, `$cred`, SCRAM in `APISRVR` (`vb.scram.first/final`), `secure-cred.ps1` | API login without OS passwords | Exists because a Windows service cannot check a Windows password; Linux `APISRVR` verifies the OS password (`login_user`). Would run on Linux but needs a client-protocol change on both sides — **owner decision** (the password crosses TCP 4243) |
| `os.users`, `secure-osusers.ps1`, `verify-osusers.ps1` | Per-person OS grants | Ruled model difference: per-account `ACC$SH`/`ACC$OS.EXEC` (privilege model) |
| `K$WINPATH`, `K$WINPID`, `K$SET.USERNAME`, `K$ASSUME.USER`, `K$IMPERSONATING`, `win32s4u.c` | Path conversion, S4U impersonation | Cygwin and Win32 token APIs; a Linux session already runs as its user |
| `K$OS.ADMINISTRATOR`, `K$INTERACTIVE`, `SDADMIN` | Elevation and desktop tests | Windows token/desktop; Linux answers with `sudo` + `CPROC grant.administrator` |
| `REMOTEAPI`, `REMOTESSH`, `SSHSRVR`, `api-firewall.ps1`, `ssh-firewall.ps1`, `install-ssh.ps1`, `remove-ssh.ps1`, `allow-ssh-groups.ps1`, `sync-route-groups.ps1`, `deny-logon.ps1`, `restore-sshonly.ps1`, `api-listener.ps1`, `ssh-preflight.ps1` | REMOTE.API / REMOTE.SSH / SSH.SERVER, ssh/api/both/none routes | Windows Firewall, the OpenSSH capability and logon rights; Linux ruled the ForceCommand tier boundary (PRE_RELEASE 13) and installer prompts. A systemctl/ufw version is possible — **owner ruling needed** |
| `APNDPATH` / APPEND.SD.PATH, `sd-path.ps1` | SD on the PATH | Registry PATH; the installer links `/usr/local/bin/sd` |
| `micro-home.ps1`, `install-editors.ps1`, Microsoft Edit | Editor configuration and bundling | Linux micro's home is already per-user writable; MS Edit is not packaged (owner); editors come from the distribution |
| `secure-*.ps1` (account-dirs, accounts, audit, dumps, gcat, log, pcode, psdir, sysdirs), `verify-*acl.ps1` | NTFS ACL hardening | ACL model does not exist; **the intent** (who may write gcat, audit, dumps, pcode) should be reviewed as owner/group/mode — future task |
| `win32audit.c` | Append-only audit file | Win32 FILE_APPEND_DATA; the feature itself is queue 13 |
| `exepath.c` directory split, `sdwind` naming | Program layout | Windows keeps executables apart from pcode; Linux keeps `sdsys/bin` |
| `mkvocdoc.py`, `SDCoreWindowsDocs` | Documentation build | Coupled to `sd.iss` and the Windows doc set |
| `probe-*.ps1`, `verify-*.ps1`, `test-*-units.ps1`, `cycle.ps1`, `VerifyInstall*.ps1`, `vm-*.ps1`, `capture-state.ps1` | Test and cycle instruments | PowerShell and Windows state; the intent is queue 22 |
| UMASK removal | Port removed UMASK | Kept here on purpose: real on Linux (stance) |

## Port defects found while adopting

Written to the port as `BUGS_FROM_LINUX_PORT.md` (10–11 Sep 2026; committed
and pushed to `github.com/dmontaine/sd4windows` 11 Sep, `d746963`, from a fresh
clone — the local `sd4windows` is frozen and never pushed): MODIFYA
`tier.build.rec` strips field 1; sdtic end-of-file skips the failure count;
10114 can be false; CREATEA stale description; plus 5 lower case, 6 DELETEF
prompts, 7 `op_getlocks` NULL. New entries go in through a fresh clone.
