# PRE-RELEASE FIXES

**The defect tracker for the final-testing phase.** Things that need deciding or
fixing before **L1.0-0** is released. Started 9 Sep 2026.

***WHAT THIS FILE IS FOR, IN THE OWNER'S WORDS, 9 Sep 2026:*** in SD Core for
Windows it *"was created late in the project, so when the original plan was done
and we started final testing, we could track and fix the errors that the testing
revealed."* **That is its job here too: the place testing's findings go.**

***SO IT HAS BEEN STARTED EARLY, AND THAT IS DELIBERATE RATHER THAN A
MISREADING OF THE PORT.*** This project is at **step 4 of 10** and final testing
has not begun; the port created its copy at the equivalent of step 10. Started
now for two reasons: the owner asked for it on 9 Sep, and the entries below
already exist — they are **structural gaps that testing will never reveal**,
because no test finds a decision nobody made (entries 1, 2, 7) or a plan that is
silent on a subject (entries 1, 2, 5). Those are exactly the kind that go stale
in a handoff document and get lost.

***WHEN TESTING STARTS, THIS FILE'S CHARACTER CHANGES AND ITS RATE WILL DOMINATE
WHAT IS HERE NOW.*** The port reached 186 entries; nearly all of them came from
running the system, not from reading it. Expect the same, and do not read the
present low count as "the system is nearly clean" — it means testing has not
started.

**This file is maintained, not written once.** Add an entry when work or a test
turns something up; strike its number in the table when it is fixed, with the
date and the commit.

***IT LISTS WHAT WE WOULD SHIP, NOT WHOSE FAULT IT IS.*** A defect this project
inherited from upstream `sdb64`, or one the Windows port also has, still belongs
here: being somebody else's bug has never been a reason to ship it.

**Why a separate file from [PROJECT_STATUS.md](PROJECT_STATUS.md).**
PROJECT_STATUS is a *position* — what is done, what is next, what was measured.
This is a *worklist of things that would embarrass the release*. An item can sit
here for weeks without being the next task, which is exactly what PROJECT_STATUS
must not contain.

`SEV` is a recommendation, not a ruling: **B** blocks the release, **S** should
be fixed, **M** minor.

***THE TABLE IS THE INDEX. THE SECTIONS UNDER IT ARE DETAIL.*** A struck number
is done; **read the table, never the section headings** — short entries have no
section at all, so counting `## N.` headings gives an answer that is wrong and
looks authoritative.

***THE FIRST COLUMN IS THE ID AND ITS HEADER CELL IS DELIBERATELY EMPTY. DO NOT
"FIX" IT TO `| ID |`.*** The port's checker finds this table by matching
`^\|\s*\|\s*SEV\s*\|` (`test-fixlist-units.ps1:106`), so the empty cell is what
makes the table findable. **It said `| ID |` until 9 Sep 2026 and the checker
refused the whole file** — *"no index table found"*, exit 2. Changed on the
owner's ruling that day, for conformity with the port and to adopt the checker.

***NEXT FREE ID: 23.*** Take it from here and increment it; **do not derive it by
scanning.**

**Ported from SD Core for Windows**, whose `PRE_RELEASE_FIXES.md` is the model
and carries 186 entries. This one starts at 1 — the port's ids are its own and
the two files are not comparable by number.

| | SEV | What | Where |
|---|---|---|---|
| 23 | **B** | ***THE OS-ACCESS TIER GATE. COMMIT 1 BUILT AND COMPILED 9 Sep 2026, UNRUN.*** Owner's model, 9 Sep 2026, confirmed as the port's (its 157/80): *"os.execute and shell are off for anyone but administrators; administrators have full access to ssh, api, os.execute and shell"*, and an admin may grant a named non-admin account with `MODIFY.ACCOUNT OS-ON \| OS-OFF \| SH-ON \| SH-OFF`. ***THE HOLE COMMIT 1 CLOSES: `op_sh()` HAD NO PERMISSION CHECK AT ALL***, so a non-internal user program's `OS.EXECUTE` ran unconditionally — the tier's in-SD boundary did not exist at the C layer. **Commit 1** adds `os_permitted()` to `op_sh.c` = `HDR_INTERNAL \|\| USR_ADMIN`, else refused with new message **10054** (`%s is not permitted to use OS.EXECUTE` — the port's number and wording, `%s` because it is C-referenced through `k_error`). **Every shipped `OS.EXECUTE` caller is `$internal`** (all 11, checked 9 Sep 26), so nothing shipped breaks; the `SH`/`!` prompt path is already admin-only at `CPROC:3490` (`os.command`) and reaches `op_sh` as an internal caller, so it is unaffected and not double-gated. **Built clean, 0 warnings, `bin/sd` relinked; NOT witnessed — the install is STALE and builds `origin/main`, so it needs a reinstall to see the refusal.** ***COMMIT 2 (planned — written in the conditional):*** `ACC$SH`=7 / `ACC$OS.EXEC`=8 in `ACCOUNTS`; `MODIFYA` gains the four grant forms (refusing an administrator, the port's 10106 shape, and no-op reporting); and the reads that WIDEN the gate — the `SH` gate at `CPROC:3490` to admin-or-`ACC$SH`, and `op_sh` to admin-or-`ACC$OS.EXEC` via a new `USR_` flag loaded when the account is entered (login **and** `LOGTO`, the delicate path the record warns about). Gate-first ordering is deliberate: it avoids ever shipping an `OS-OFF` that claims to deny but does not — the trap `MODIFYA` names where it left `SUSPENDED` out. ***OBJECTION, RECORDED NOT RESOLVED:*** the port says `OS-ON` governs *"OS.EXECUTE and the screen editors"*, but here the editors are `$internal` and so bypass this gate — an `OS-OFF` would not restrain `ED`/`MICRO` on this tree unless commit 2 gates the editor launch separately. Whether that matters is undecided. | `gplsrc/op_sh.c` (`os_permitted`, `sh`); `sdsys/MESSAGES/10054`; `sdsys/GPL.BP/CPROC:3490`; entries 13, 18, 22; port 157/80 |
| ~~22~~ | **B** | ***`!set_passwd` AND `!create_user` WERE GLOBALLY CATALOGUED WITH NO GATE OF THEIR OWN, SO ANY ACCOUNT COULD MAKE SD RUN `sudo passwd` OR `sudo useradd`. FOUND AND FIXED 9 Sep 2026.*** Both are `$catalog !name` — global catalogue — and their **only** shipped caller is `CREATEA`, which is administrator-gated. ***THE GATE WAS ON THE VERB, NOT ON THE FUNCTION.*** **Measured, not reasoned**: a four-line program with **no `$internal`**, compiled and run as `don` (uid 1000, no `sudo`, against the *gated* binary of entry 21) called a `!` catalogued function and got a **discriminating** answer — 1 for a group `don` is in, 0 for one that does not exist — so it really executed. `SET_PASSWD:115` is `OS.EXECUTE "sudo passwd " : username` and `CREATE_USER:64` is `sudo useradd -m`. ***TWO CONSEQUENCES, AND THE SECOND IS ENTRY 14 ARRIVING FROM A DIRECTION THAT ENTRY DOES NOT CONSIDER***: for a sudoer it **runs**, so SD changes another person's password on the say-so of an unprivileged account; for a **non-sudoer** `sudo` challenges for a password inside a session not expecting to answer one — **the hang, and it is reachable without being an administrator at all.** **Fixed** by gating both on `kernel(K$ADMINISTRATOR,-1)`; both are already `$internal`, so `KERNEL` resolves, and both already had the return-a-status idiom. ***THE STATUS CODES DIFFER BETWEEN THE TWO FILES ON PURPOSE***: `SET_PASSWD` documents PAM codes and uses **6** (`PAM_PERM_DENIED`); `CREATE_USER` documents `useradd` exit codes where 6 is already *"specified group doesn't exist"*, so it uses **5**, which is unused there **and** is the port's own "access denied". **The port's 5 was not copied into `SET_PASSWD`** because 5 is `PAM_BUF_ERR` in that file's table — conformity on an integer whose meaning differs is a coincidence, not conformity. Compiled 0 errors each, red control 1 error. **Unrun.** | `sdsys/GPL.BP/SET_PASSWD:99-115`, `sdsys/GPL.BP/CREATE_USER:48-64`; entries 14, 21 |
| ~~21~~ | **B** | ***FIXED 9 Sep 2026 ON THE OWNER'S RULING THAT THIS SYSTEM SHIPS FOR PRODUCTION, NOT FOR DEVELOPERS.*** `-INTERNAL` now calls `check_admin()` (`sd.c:332`), and ***`check_admin()`'s `in_group("admin")` ARM IS REMOVED*** (`sd.c:586`) — not because it is dead here, which it is, but because on Ubuntu-family systems `admin` was the old sudo group, so the fix would have held on this machine and quietly not held on others. **Witnessed as `don`, uid 1000, no sudo, before/after/control**: the installed binary took `-internal WHO` and printed `3 DON` exit 0; the built binary refuses with *"Command requires administrator privileges"* exit 1; the same built binary with **no** flag still prints `4 DON` exit 0, so ordinary use is unbroken. **The third route in was enumerated**: `internal_mode` is assigned in three places, two now gated, and `op_kernel.c:140`'s `kernel(K$INTERNAL,n>=0)` setter is reachable only through them — **all eleven `K$INTERNAL` uses in `GPL.BP` are enquiries**. *(Lead, not built: that setter has no `HDR_INTERNAL` guard, which is entry 19's shape.)* ***AND THE COST IS BOUGHT BACK, ON THE OWNER'S QUESTION THE SAME DAY***: `make EXTRA_C_FLAGS=-DSD_DEV_BUILD` drops the check, and **that is safe here only because `installsdai.sh` clones and builds `main` from GitHub**, so a developer binary cannot reach a user. **It announces itself on `--version` and on every use of the flag**; plain `make` is untouched and `bin/sd` was rebuilt default afterwards. Without it, compiling `CPROC`/`CATALOG`/`LOGIN` outside an install needs `sudo`. *(The finding follows.)* ***ANY ORDINARY USER CAN GRANT THEMSELVES ADMINISTRATOR RIGHTS WITH `sd -internal`, AND THIS DEFEATS EVERY GATE INCLUDING 18's. MEASURED 9 Sep 2026, NOT REASONED.*** As `don`, uid **1000**, no `sudo`: a five-line `$internal` program compiled with `/usr/local/sdsys/bin/sd -internal BASIC BP ADMPROBE` and run with `RUN BP ADMPROBE` printed `PRE admin flag = 0`, then `POST admin flag = 1` after `void kernel(K$ADMINISTRATOR, 1)`. **The probe refuses the null case** — it stops and prints VOID if the flag was already set — and it printed uid, user and account, so it cannot have measured a privileged session by accident. ***THIS REFUTES THE CONTAINMENT ARGUMENT IN ENTRY 19, WHICH IS SOUND ON ITS OWN TERMS AND ASKS THE WRONG QUESTION.*** 19 measured that a **non-internal** program cannot compile `kernel(26,1)` — true, `BCOMP:3759` gates the intrinsic on `internal`, and `BCOMP:2853` gates the `$INTERNAL` directive on `kernel(K$INTERNAL,-1)`. **But `internal_mode` is set by the `-INTERNAL` command-line flag at `sd.c:310` WITH NO PRIVILEGE CHECK AT ALL** — and `-I`, three lines below at `:320`, calls `check_admin()` first. So the containment rests on a flag anyone may pass. **The fix is one line and it is named, not built**: `-INTERNAL` should call `check_admin()` the way `-I` does. ***IT IS NOT BUILT BECAUSE IT IS A RULING, NOT A TYPO*** — it decides who may compile `$internal` programs, and the cost is real: it removes the only instrument this project has for compiling `CPROC`, `CATALOG` and `LOGIN` outside an install (see §18 commit 2), and `installsdai.sh:645,672` already run `-internal` under `sudo` so the installer is unaffected. **And `check_admin()` (`sd.c:589`) is itself worth a second look**: it is `geteuid() != 0 && !in_group("admin")`, and ***no `admin` group exists on this machine*** — `don` is in `sudo`, `wheel` is absent — so today it means "euid 0" and its group arm is dead. | `gplsrc/sd.c:310`, `:320`, `:586-593`; `sdsys/GPL.BP/BCOMP:2853`, `:3759`; entries 19, 18 |
| ~~20~~ | **B** | ***PIECE 1 IS DONE AND WITNESSED, 9 Sep 2026 — `WHO.AM.I` UNDER `sudo sd` ON THE 17:53 INSTALL SAYS `User : don`, AGAINST A BANKED BASELINE OF `sdsys`.*** `UID 0` / `EUID 999` unmoved, `Admin? Yes`, and ***message 10032 did not fire***, so `SUDO_USER` reached the process and the unknown arm was never taken. **Pieces 2 and 3 landed with entry 18 commit 2** (`K$REAL.USER` 57 and the gates that read it), so what remains open here is only the `CPROC:2483` `LOGTO` widening recorded below and the `APISRVR:363` case, which is **still not verified**. *(The original entry follows.)* ***SD DOES NOT KNOW WHICH PERSON IS THE ADMINISTRATOR, AND THAT BLOCKS ENTRY 18's SECOND HALF.*** Measured 9 Sep 2026 by reading `CPROC`, and it **corrects entry 18's premise**. On `sudo sd`, `CPROC:279` sees uid 0, `CPROC:281` drops the effective uid with `!EUID_SET('sdsys')`, and ***`CPROC:285` REPLACES THE SESSION IDENTITY — `logname = kernel(K$USERNAME, 0)` makes `@logname` `sdsys`*** — before `$LOGIN` is called at `:291`. So by the time any gate could read the register, **the real person's name is gone**. The owner's *"is also a registered user of SD as an administrator"* has no person to look up, and `CPROC:2483`'s own `is_grp_member(@logname, …)` entry test is answered for `sdsys` rather than for whoever typed `sudo`. ***THIS ALSO NARROWS ENTRY 18's OTHER CLAIM***: the OS half is *effectively* enforced already, since reaching uid 0 by `sudo sd` requires sudoers membership — what is missing is the register half, not the sudoers half. **The port hit this and answered it with a SEPARATE concept**, `K$OS.ADMINISTRATOR` — *"is the SIGNED-IN PERSON an administrator"* as distinct from the session flag — keeping `@logname` the signed-in user. ***A RULING IS NEEDED BEFORE 18's GATES CAN BE WRITTEN***: whether SD preserves the real identity across the drop, and if so where. See §20 | `GPL.BP/CPROC:279-291`, `:2483`; entry 18 |
| 1 | **B** | ***THE PLAN HAS NO ANSWER FOR THE PORT'S 157 POWERSHELL HELPERS, AND §L IS SCHEDULED WITHOUT THE VERIFIERS THAT PROVED IT THERE.*** Classified 9 Sep from each script's own header: **113 testing, 38 admin, 6 build**. The testing half is 51 `verify-*`, **28 `test-*-units` that test the verifiers themselves**, 18 `probe-*` and 16 harness. Of the 38 admin, 19 are Windows mechanism with no counterpart here, **12 are the `secure-*` ACL family whose INTENT is §L's POSIX security posture**, and 7 have a direct Linux need the plan already schedules (`upgrade-voc`/`-dicts` §F1/F2, `check-install` §F7, `finish-install`, `clean-deadvoc`, `api-listener`, `restart-sd`). The plan mentions none of it: `verify-`, "the suite", "harness" and "verifier" return **two incidental hits in ~1,600 lines**. See §1 | plan §H "Windows-only work"; `sd4windows/sdb_ai/sd64/gplbld/*.ps1` |
| ~~2~~ | **S** | ***RULED AND IMPLEMENTED 9 Sep 2026.*** The plan did not mention the `MICRO` verb or the editors at all. **Owner's ruling:** *"for the linux version we just drop microsoft edit and maintain our practice of using whatever version of micro the distribution ships. The one thing we do want to retain from the windows version is the sdbasic syntax highlighting."* Done in `c8…` — `mkbasicsyntax.py` and `checksyntax.py` ported, `microcfg/syntax/sdbasic.yaml` generated from this tree's `BCOMP`, and `MICRO` now suffixes a BP working copy `.sdbasic` so detection fires. **Placement is entry 12.** See §2 | `sdb_ai/sd64/gplbld/mkbasicsyntax.py`, `microcfg/syntax/sdbasic.yaml`, `sdsys/GPL.BP/MICRO` |
| 3 | **S** | **`EDIT` MEANS DIFFERENT THINGS IN THE TWO SYSTEMS, WHICH IS A NEAR-MISS NAME WAITING TO BITE.** Here `VOC_TEMPLATE/EDIT` → `$ED`, the **line** editor. In the port `voc_template/edit` → `$EDIT`, the **full-screen** editor. A user or an agent moving between the two gets a different program from the same word | `sdsys/VOC_TEMPLATE/EDIT` vs `sd4windows/.../voc_template/edit` |
| 4 | **M** | **`MICRO` shells out to a hard-coded `micro` with no check that it exists and no test of the result.** `Editor = "micro"` at line 37, `execute "!" : editor : …` at line 201, and nothing between. The port's UPSTREAM #16 records the consequence: it reports *"Record is unchanged"* when the editor is absent, which blames the user's data for a missing binary | `sdsys/GPL.BP/MICRO:37,201` |
| 5 | **S** | ***`bbcmp.py` UPPER-CASES EVERY `$include` NAME, SO A LOWER-CASE INCLUDE IS UNRESOLVABLE ON ext4.*** Found 9 Sep 2026 trying to compile `CPROC`: `$include define_install.h` fails because the file on disk is lower case. **This is a third name lookup that plan §M1 does not name** — §M1 lists the colon prompt/query language and BASIC `OPEN`, and stops there | `sdb_ai/sd64/gplbld/bbcmp.py:7141` |
| 6 | **B** | **Step 2 (`A1`–`A6`) is committed, compiled and NOT ONE ITEM EXERCISED.** Every item touches transactions or index structure; `A5`'s failure mode is a permanently damaged index and `A1`'s a half-applied commit, **both silent**. `A1` needs an *induced* commit failure to reach at all | PROJECT_STATUS "Step 2" ×3 sections |
| 7 | **B** | ***§M, THE LOWER-CASE CONVERSION, IS RELEASE-BLOCKING BY THE OWNER'S RULING OF 9 Sep 2026*** — *"as long as it is done by the end"*. Recorded here as well as in PROJECT_STATUS because the failure mode is silence: deferred once more each step until the port ships with `GPL.BP` and `SYSCOM` still upper case | plan §M; PROJECT_STATUS "Open" |
| ~~8~~ | **S** | ***BUILT 9 Sep 2026 — `gplbld/assert-current.py`, `gplbld/test-assert-current.py` (10 rows, 10/0), AND AN INSTALL STAMP IN `installsdai.sh`.*** ***IT IS A REWRITE AND NOT A PORT, BECAUSE THE QUESTION IS DIFFERENT.*** The port compares the installed binary with `bin\sd.exe`, which works there because its installer stages what is in `bin\`. **Here the installer clones `main` from GitHub and builds that**, so `bin/sd` is not what got installed even on a perfectly current tree — comparing them would report stale on a good tree and current on a bad one. The Linux question has four parts, failing for different reasons: **A** the working tree is committed (an uncommitted change can never be in an install); **B** HEAD is `origin/main` (same reason, one step out); **C** the install was built from HEAD; **D** `bin/sd` is newer than `gplsrc` — the port's check A2, and about a **different tree**: the one you compile BASIC against. ***C IS EXACT ONLY BECAUSE THE INSTALLER NOW STAMPS THE COMMIT***: `git rev-parse HEAD` is read from the clone (the only moment it is known for certain) and written to `$sdsysdir/.sdcore-install` **after** the recursive `chown`/`chmod`, root-owned 644, because anything that can rewrite it can lie about what is installed. **Without a stamp the comparison is one-directional and says so** — older than the commit is decisive, newer is `UNKNOWN`, never `CURRENT`, because a newer mtime says nothing about *which* commit. **Three exit states — 0 current, 1 stale, 2 cannot answer** — and the test has rows for all three, because collapsing the third is the defect this will grow. ***WATCHED FAILING***: the `CURRENT` row failed first (the fixture did not gitignore `bin/`, so a built binary read as a dirty tree), which is exactly the flaw that would have left nine rows a guard saying STALE-to-everything would pass. **Live on this machine it correctly reports STALE**: install 18:39 predates HEAD. | `sdb_ai/sd64/gplbld/assert-current.py`, `installsdai.sh` |
| | | *(original entry)* **No `assert-current` equivalent.** Nothing refuses to run a check against an install older than its source, so a green result can come from the previous build. The port's is PowerShell, so this is a **rewrite, not a copy** — it is entry 1's most valuable single item | `sd4windows/sdb_ai/sd64/gplbld/assert-current.ps1` |
| 9 | **S** | ***`gplbld/check-stale-leads.py` CANNOT RUN HERE AT ALL, AND ADDING THIS FILE DOES NOT CHANGE THAT*** — measured 9 Sep 2026, not predicted. Copied verbatim and run, it exits **2 before any phase executes**: *"REFUSING - could not bound section 7"*. It is keyed to the port's PROJECT_STATUS structure — a section 7, `> ###` START HERE items, a `✅` task table — none of which exists here. **The unadapted copy was removed rather than committed**, because a tool that always exits 2 reads as a guard the project has. See §9 | `sd4windows/sdb_ai/sd64/gplbld/check-stale-leads.py` |
| 10 | **M** | **`sdsys/MESSAGES` lacks records `4100`, `4101`, `-10303`** (plan §D5). That is the runtime message file, not generated from `err.h`, so `gen_includes.py` does not touch it; adding the three is a deliberate data edit | `sdsys/MESSAGES/` |
| 11 | **M** | **`gplbld/check-msglen.py` hard-codes the bound 231 and will not say so if the constants move.** All four were verified against this tree when it was ported on 9 Sep, but nothing re-checks them; a change to `MAX_ERROR_LINES`, `MAX_EMSG_LEN`, the `"%08X: "` prefix or the D1 fix leaves a confident instrument answering from a stale premise | `sdb_ai/sd64/gplbld/check-msglen.py` |
| ~~19~~ | **B** | ***DONE 9 Sep 2026 — MEASURED, THEN FIXED TO MATCH THE PORT.*** The C hole was real at **both** ends (`op_kernel.c:302-312`): any positive argument set `USR_ADMIN` without calling `IsAdmin()`, and the `\|\| IsAdmin()` made `kernel(26,0)` *re-grant* rather than clear whenever the caller ran as root, so `CPROC:2713`'s admin-drop on `LOGTO` did nothing for a root OS user. ***BUT THE READING "bypassable from any BASIC program" IS REFUTED:*** `KERNEL` is an `int.intrinsics` entry resolved only in internal mode (`BCOMP:3758`), and a non-internal probe (`kernel(26,1)`) compiled from the non-root `don` account **fails with "Unrecognised statement", 2 errors** — KERNEL is unreachable from ordinary BASIC. So the opcode can only be emitted by an `$internal` program (LOGIN, CPROC). **Fixed by gating the flag change on `HDR_INTERNAL`**, the port's exact fix (its entry 170 / 13 Aug 26). Build clean, 0 warnings; `bin/sd` boots. The `$internal`-path effect is reasoned + conformity, not witnessed (an ordinary user cannot compile `$internal`). Unblocks entry 18 | `gplsrc/op_kernel.c:302-312` |
| ~~18~~ | **B** | ***ALL THREE PARTS OF THE OWNER'S DEFINITION ARE NOW MET, AND THE THIRD ONE TURNED OUT TO BE MET ALREADY.*** This entry said *"make the login path refuse an unregistered user rather than only a forced one"*, and its gap table said the default path was *"not established"*. ***IT IS NOW ESTABLISHED, AND THE PREMISE WAS WRONG***: `LOGIN` has **three** account cases and **every one** reads the register and terminates on a miss — forced (`:213`), administrator (`:250`), and the default `initial.account = upcase(@logname)` (`:265`). **Measured with a control, as `don`**: `sd -ANOSUCHACCT` → *"Account NOSUCHACCT not in register / Connection terminated"*; `sd -ADON` → the session runs and `WHO` prints `58 DON`. **Nothing needed building for this row.** ***WHAT REMAINS IS NOT THIS ENTRY***: §L1's per-tier VOC does not exist, so a tier decides whether a verb ACTS but not whether an account HAS it — the port's *"two gates, not one"* with only the second built. **That is §L1 and it is not designed.** *(The build record follows.)* ***BOTH COMMITS BUILT 9 Sep 2026, AND FOR THE FIRST TIME IN THIS PROJECT THE BASIC WAS REALLY COMPILED — `CPROC` 0 errors, both `IS_INSTALL` arms, with HEAD as the control and a red run to prove the check discriminates. See "Commit 2" below.*** ***IT IS NOT CLOSED, AND THE REASON IS ENTRY 21***: a gate is worth only as much as the flag it sets, and `sd -internal` lets any user set that flag directly. ***COMMIT 1 IS NOW WITNESSED ON A LIVE SYSTEM***: on the 17:53 install `ACCOUNTS/DON` carries **five fields with `ACC$TIER` = `STANDARD`**, up from three at 16:22, so `CREATEA`'s tier write really runs. ***ALL THREE COMMITS ARE NOW WITNESSED ON A RUNNING SYSTEM, 9 Sep 2026, IN ONE SITTING***: the bootstrap arm fired and named the person, `MODIFY.ACCOUNT DON ADMINISTRATOR` wrote the tier and added him to `sdadmin`, and the next `sudo sd` printed **no 10033** while still reporting `Admin? : Yes` — ***the arm closing itself, which is the whole design.*** Both halves read off disk afterwards: field 5 `ADMINISTRATOR`, `sdadmin:x:965:don`. ***THE ROW STAYS OPEN ON ITS THIRD REQUIREMENT, NOT ON THESE TWO***: *"unregistered → refused entry"* is still only half there (`LOGIN:210-213` refuses a **forced** account; the default path is unestablished), and **§L1's per-tier VOC does not exist** — every account still gets the same verbs. ***AND THE GATE HAS ONLY BEEN SEEN TO PASS***; the refusal control is named in commit 3 below and is unrun. *(Commit 1, below, stands as written.)* ***HALF BUILT 9 Sep 2026 (commit 1 of 2): THE REGISTER RECORDS A TIER, AND NOTHING READS IT YET.*** `SYSCOM/KEYS.H` gains `ACC$TIER` 5 / `ACC$PRIOR.TIER` 6; `CREATEA` takes `ADMINISTRATOR`/`PROGRAMMER` (token text, not `KW$`, so **no abbreviation**) and writes field 5, `STANDARD` being the default. **Field 4 is free in this tree — unlike the port — and is left free for conformity anyway.** ***Commit 2 is the gates, `sdadmin` membership and the ten call sites.*** Every account still gets the same VOC (§L1, undesigned). Compile check was **bounded**: `$internal`, so error classes were compared against HEAD and are identical, none on an added line. ***"ADMINISTRATOR" IN THE CATALOGUE GATES MEANS UID 0 — LITERAL root — AND §L'S ADMINISTRATOR TIER WILL NOT SATISFY IT.*** `CATALOG` (`:108`, `:202`) and `DELCAT` (`:119`) all gate on `system(27) # 0`, and `system(27)` is **`getuid()`** (`gplsrc/op_sys.c:222-223`). `sd` is not setuid, so a session runs as the invoking Unix user: **an SD ADMINISTRATOR who is not root is refused, and any ordinary user who is root is admitted.** The tier has no bearing on it. **Measured 9 Sep 2026 on the 11:35 install**, as uid 1000: `CATALOG BP $X`, `CATALOG GLOBAL BP X` and `DELETE.CATALOG $X` each refuse with sysmsg 2001, and a *local* `CATALOG BP X` does not — so the gate discriminates and works. **The defect is not the gate, it is what "administrator" is defined as.** ***OWNER'S DEFINITION, 9 Sep 2026, WHICH SETTLES IT:*** *"an administrator is a person who is a member of sudoers and is also a registered user of SD as an administrator. If they are not a registered user they should be refused entry."* And on the model: *"that is the current path in the windows version — you can be a windows administrator and still not have access to sd."* **Two conditions, ANDed, and neither is `getuid() == 0`.** See §18 for the measured gap | `GPL.BP/CATALOG:108,202`; `GPL.BP/DELCAT:119`; `gplsrc/op_sys.c:222` |
| ~~17~~ | **S** | ***DONE 9 Sep 2026 — `L1.0-0`, AND THE BANNER IS THE OWNER'S WORDING.*** `sd --version` now answers *"String Database (sd) Version **L1.0-0** 64 Bit"* (measured on a clean rebuild) and the sign-on line is *"SD Core, the Essential Multivalue String Database, version L1.0-0"* — the port's line minus *"for Windows"*, since here the platform rides on the **L**. *"(AI modified)"* is gone: the stamp is this project's own number, so there is nothing left to distinguish it from. **Five files, and they have to move together** — `gplsrc/revstamp.h` (the source), `sdsys/GPL.BP/REVSTAMP.H` (**generated**, via `gplbld/gen_includes.py`), `LOGIN`'s banner, and `$RELEASE` in **both** `VOC_TEMPLATE` and `NEWVOC`. ***`MAJOR_REV`/`MINOR_REV`/`BUILD` STAY AT UPSTREAM'S 1/0/2***, exactly as the port leaves them: `sysseg.c:48` packs them into a shared-segment compatibility word, so they are a binary interface and not a name. **Do not advance the trailing digit to track upstream** — owner, 24 Aug 26, of the port: *"our numbering sequence is different than upstream, hence the W in front of the number."* See §17 for the three traps this cost. | `gplsrc/revstamp.h:39-44`, `sdsys/GPL.BP/REVSTAMP.H`, `LOGIN:162`, `sdsys/VOC_TEMPLATE/$RELEASE`, `sdsys/NEWVOC/$RELEASE` |
| | | *(original entry)* ***THE SHIPPED BINARY TELLS THE USER IT IS VERSION 1.0-2, WHICH IS UPSTREAM'S NUMBER, NOT THIS PROJECT'S.*** Measured on the 11:35 install of 9 Sep 2026: `sd --version` answers *"String Database (sd) Version 1.0-2 64 Bit"* and every session banner says *"version 1.0-2 (AI modified)"*, while `sdsys/changelog` opens **`L1.0-0 - in progress`** and the project stance says release numbering follows SD Core for Windows rather than upstream. Source is `gplsrc/revstamp.h:43`, `#define SD_REV_STAMP "1.0-2"`. **`revstamp.h` also feeds `GPL.BP/REVSTAMP.H` through `gen_includes.py`**, so one edit carries to both — but the banner text and `MAJOR_REV`/`MINOR_REV` need checking with it. Plan §N | `gplsrc/revstamp.h:40-43`; `sdsys/changelog:1` |
| 16 | **S** | ***THE BUILD RUNS AS ROOT AND DOES NOT NEED TO*** — `installsdai.sh:359` is `sudo make -B`, so `gplobj/` and `terminfo/` inside the download come out owned by `root`. That is what made the 9 Sep install "fail" after it had succeeded: the ordinary-user `rm -fr` at the end could not remove them, returned 1, and `set -euo pipefail` aborted with no message. **Fixed by making the two cleanups `sudo rm -fr`, which treats the symptom.** The cause is that compiling needs no privilege at all — only *installing* does. Building as the calling user and `sudo`-ing just the copy into `/usr/local/sdsys` would remove a whole class of this | `installsdai.sh:359` |
| 15 | **S** | ***AN INSTALL NOW TESTS `origin/main`, NOT THE WORKING TREE — SO COMMIT AND PUSH BEFORE TESTING, OR YOU ARE TESTING SOMETHING ELSE.*** Owner's decision, 9 Sep 2026: the installer always clones `main` from GitHub. That **reverses plan §F9**, which removed the download precisely so an install would build the bundled `sdb_ai/` tree, and it reverses CLAUDE.md's *"builds from the `sdb_ai/` tree bundled in this repository, not from a clone."* The decision is the owner's and stands; **the consequence is that uncommitted work is invisible to an install and nothing detects that.** The port's answer to the same class of problem is `assert-current` (entry 8), which refuses to test a tree source has moved past. **Until something checks, the discipline is manual.** CLAUDE.md's project-constraint wording needs correcting to match | `installsdai.sh`; plan §F9; CLAUDE.md "Project constraints" |
| ~~14~~ | **B** | ***WIRED UP 9 Sep 2026. ALL 13 CALL SITES GO THROUGH `sd-elevate`; NO RAW `sudo` REMAINS IN `GPL.BP`*** (the one grep hit left is a comment in `LOGIN:246`). **Every mapping was validated with the helper's own `--dry-run` before a line of BASIC moved** — 13 of 13 resolved to exactly the command the raw call ran. ***TWO OF THEM WERE BROKEN ON HALF THE DISTRIBUTIONS THIS INSTALLER SERVES, WHICH IS A BUG FIX AND NOT A HARDENING***: `MODIFYA`'s two `sudo deluser` calls are **Debian-only** — the demotion path could never have worked on Arch or RHEL — and `CREATEA`'s `groupadd -U` is recent shadow-utils; the helper uses `gpasswd -d`/`gpasswd -a`, which are everywhere. ***`sdadmin` IS NOW IN THE HELPER'S GROUP WHITELIST — the decision this entry asked to be named.*** An administrator may make another administrator; that is delegation, not escalation, because reaching the helper at all already requires `sdadmin` or root. **The residual is stated in the script**: `sdadmin` membership is OS privilege independent of the register, so this widens who holds it — bounded by `require_sd_user` (root, `sdsys` and system accounts are unreachable) and by SD failing closed, since `CPROC` wants **both** halves. ***AND WHITELISTING IT EXPOSED A HOLE THAT WAS ALREADY THERE***: `groupdel` had no guard, so ***HEAD's HELPER BUILDS `groupdel -- sdusers`, exit 0*** — measured by running it, not read — which unregisters every SD user at once. Both system groups are now refused by name. Self-test **36 passed / 0 failed** (28 refusals, 8 controls), up from 30/0, with rows that fail if the whitelist entry is removed. Five programs compile **0 errors**, red control 1. **Unrun.** | `gplbld/sd-elevate`, `gplbld/test-sd-elevate.py`; `CREATEA`, `MODIFYA`, `DELACC`, `SET_PASSWD`, `CREATE_USER` |
| | | *(original entry)* ***RULED 9 Sep 2026, AND THE MECHANISM IS BUILT — BUT IT IS NOT WIRED UP AND THE HANG IS NOT YET FIXED.*** `gplbld/sd-elevate` (one validated helper), `gplbld/sdcore.sudoers` (`%sdadmin` → that one command, **not** the eight raw ones), installer/uninstaller wiring with `visudo -cf` and an `includedir` check, and `test-sd-elevate.py` **30 passed / 0 failed — 24 refusals, 6 controls — with the test watched FAILING (6/24) against a permissive stub.** ***THE TEN CALL SITES STILL CALL RAW `sudo` AND `sdadmin` HAS NO MEMBERS***, so migrating them now would deny account creation outright: **the migration belongs with entry 18**, which is what puts anybody in the group. Unrun — nothing installed. Also found: `MODIFYA:131`'s `deluser` is **Debian-only** and cannot work on the Arch/RHEL branches. ***"ELEVATION DOES NOT APPLY HERE" IS WRONG — IT IS SPELLED `sudo`, AND IT IS ALREADY LOAD-BEARING IN THE SHIPPED BASIC.*** **8 `GPL.BP` programs shell out to `sudo`** from `OS.EXECUTE`: `useradd -m` (`CREATE_USER:64`), `passwd` (`SET_PASSWD:115`), `userdel`/`groupdel` (`DELACC:223,197`), `usermod -aG`/`groupadd`/`chmod g+s` (`CREATEA:331,634,306`), `usermod`/`deluser` (`MODIFYA:108,131`). ***AND NOTHING CONFIGURES sudoers*** — zero hits for `sudoers`/`NOPASSWD`/`visudo` across the installer, uninstaller and all of `GPL.BP`. So an SD ADMINISTRATOR's real privilege is whatever the machine's sudo rules already say, not what §L1 grants: with broad sudo they are root (`sudo passwd root`), without it account management silently fails or blocks on a password prompt inside an SD session. **The plan says `sudo` zero times in ~1,600 lines.** ***MEASURED 9 Sep 2026: THE HANG IS REAL*** — `sudo -n -v` as `don` answers *"a password is required"* (exit 1) and **0 of 10 call sites pass `-n`**, so `create.account` blocks on a password prompt inside the session. **And the membership test has three answers, not two**: `sudo -n -l` exits 1 both for "needs a password" and for "may not sudo", so a test on that exit code refuses a legitimate administrator. Three shapes and a recommendation in §14 — **the ruling gates entry 18** |  `GPL.BP/{CREATE_USER,SET_PASSWD,CREATEA,DELACC,MODIFYA}`; plan:17, §H:853, §L1, §L5:1164 |
| 13 | **B** | ***RULED 9 Sep 2026 — A STANDARD ACCOUNT DOES NOT GET A REAL LOGIN SHELL; THE TIER IS TO BE A BOUNDARY*** (owner's selection), ***WHICH COMMITS SD TO WRITING `sshd_config`*** — the port's fenced block + refusing preflight is the model. Mechanism (`ForceCommand` vs restricted shell vs `AllowGroups`) and PROGRAMMER's case are still open; see §13. **Not built.** ***ssh IS AN UNGUARDED WAY PAST THE TIER MODEL, AND THE INSTALLER TURNS IT ON.*** Every distro branch installs an ssh server (`installsdai.sh:254,272,285,295`) and the Arch branch starts and enables `sshd` (`:265-266`). SD users are **ordinary Unix users** — `CREATEA:331` does `usermod -aG sdusers` on an account that already exists, so it keeps its login shell. **Nothing in this project writes `AllowGroups` or `ForceCommand`** (grep: zero hits across the installer and `GPL.BP`). So a STANDARD account that §L1 denies `SH` and `!` **just ssh's in and gets a shell**, never touching SD. This is the exact failure the port measured on 21 Aug 2026 — *"a stock sshd_config: no AllowGroups and, worse, no ForceCommand, so an sdsshonly account got a PowerShell prompt"* — except here it is the **default state rather than a regression**. ***MEASURED 9 Sep 2026: every SD account has a real login shell*** (`don` `/bin/bash`, `sdsys` `/bin/sh`, none `nologin`), so §L1's verb withholding is **a convenience, not a boundary**. `sshd` is inactive on this box, which makes the exposure latent here but not absent. See §13 | `installsdai.sh:254-296`; `sdsys/GPL.BP/CREATEA:331`; plan §L5, §H:854, plan:17 |
| ~~12~~ | **S** | ***DONE 9 Sep 2026 — SHAPE 1, AND THE HIGHLIGHTING IS MEASURED RATHER THAN ASSUMED.*** **Two gaps, not one**: the installer did not ship `sdbasic.yaml` *at all* (no reference to `microcfg` anywhere in it), and nothing placed it. `installsdai.sh` now copies `gplbld/microcfg` into `$sdsysdir` before the chown, and **`GPL.BP/MICRO` places it per-user on first use** — `mkdir -p "$HOME/.config/micro/syntax" && cp -u …`, no privilege, self-healing for accounts created later, and `cp -u` so a regenerated file reaches an existing user while a user's own edits survive until SD's genuinely moves on. **`$HOME` is left for the shell** — it knows the caller's home even on the `sudo` path where the account is `SDSYS` and the person is not. ***THE ENTRY DEMANDED HIGHLIGHTING BE CHECKED ON A REAL RECORD, AND IT WAS, WITH TWO CONTROLS.*** micro driven in a pty over the same five lines, counting distinct SGR sequences: **`.sdbasic` with the file installed → 13**; byte-identical content named `.plain` → **8**; `.sdbasic` with the file removed → **8**. So the five extra colours (purple 141, green 148, red 161, yellow 185 — keywords, strings, numbers) depend on **both** the filename and the file's presence, which isolates the cause to exactly what this change does. **The hand-placed copy was then deleted**, so the next test is honest. `checksyntax` 24 patterns / 0 bad; `MICRO` compiles 0 errors, red control 1. | `installsdai.sh`, `sdsys/GPL.BP/MICRO` `place_syntax_file` |
| | | *(original entry)* ***`sdbasic.yaml` IS GENERATED AND VALIDATED BUT NOTHING PUTS IT WHERE micro LOOKS***, so entry 2's highlighting does not yet reach a user. **Measured on this box, 9 Sep:** micro **2.0.15**, config dir `~/.config/micro`, and **no `/usr/share/micro`** — micro has no system-wide syntax path, so placement must be per-user and an installer running as root cannot do it for everyone. Three shapes in §12; the port's answer to the same problem was a per-user config home. **Until this lands the feature is inert, and inert is indistinguishable from working** — micro reports an unusable syntax file by not highlighting | `installsdai.sh`; `gplbld/microcfg/syntax/sdbasic.yaml` |

---

## 1. The PowerShell helpers, and the verifiers §L will need

**The plan is silent, and this was measured rather than assumed.** `verify-`,
*"the suite"*, *"harness"*, *"regression"* and *"verifier"* together return two
incidental hits across the plan's ~1,600 lines — plan:246 (a `$CRED` *verifier*,
a different sense of the word) and plan:1402 (a reference to CLAUDE.md's
instrument rule). Neither is about porting the suite.

***THE FIRST COUNT IN THIS ENTRY WAS A NAME-BASED GUESS AND UNDER-COUNTED THE
TESTING SIDE BADLY*** — it said "51 excluded, 31 relevant". Reclassified 9 Sep
2026 from **each script's own header line**, which is the classification below.
It is still mine rather than the plan's, but it is read rather than inferred.

| | | |
|---|---:|---|
| **Testing & verification** | **113** | 51 `verify-*` · **28 `test-*-units`** · 18 `probe-*` · 16 harness (`VerifyInstall1`/`2`, `assert-current`, `suite-only`, `elevate-once`, `capture-state`/`diff-capture`, the throwaway test account, the VM scripts) |
| **SD admin / operational** | **38** | see the split below |
| **Build & dev tooling** | **6** | `cycle`, `strip-comments`, `stale-binaries`, `check-datatree-litter`, `cleanup-devlitter`, `reword-yn-prompts` |

***A THIRD OF THE TESTING CODE TESTS THE TESTS*** — 28 `test-*-units` drive the
verifiers against fixtures. That is not over-engineering: it is the same rule
CLAUDE.md states, that a check which passes because it did nothing must fail.
**Whatever verification this project builds needs that layer or it will not know
when a check has gone blind.**

**The 38 admin scripts split three ways, and only the first is genuinely gone:**

- **13 Windows mechanism, no counterpart here** — the service, 3
  elevation/logon, profile reclamation, 3 Windows-account, system PATH, Windows
  Firewall, route groups, `micro-home` (an ACL problem Linux does not have), and
  `install-editors` (ruled out by entry 2). ***THE 3 ELEVATION SCRIPTS ARE IN
  THIS BUCKET FOR THEIR MECHANISM ONLY — UAC CONSENT HAS NO ANALOGUE — AND THE
  OWNER WAS RIGHT TO PUSH BACK ON THE WORDING.*** The **requirement** they serve,
  that some operations run with more privilege than the caller has, applies here
  in full and is `sudo`. That is **entry 14**, and it is not a porting job: this
  tree already does it, unconfigured.
- ***4 ssh SCRIPTS THAT THIS ENTRY FIRST GOT WRONG.*** They were filed as
  "Windows mechanism, no counterpart" and **the owner challenged it: this project
  uses ssh.** He is right, and the error is the same one this entry criticises in
  the `secure-*` family — sorting by mechanism and putting policy in the wrong
  bucket. Only `install-ssh` and `remove-ssh` are Windows-only (Linux gets sshd
  from the distribution; **this installer already installs it**).
  `allow-ssh-groups` writes `AllowGroups` and `ForceCommand`, which are
  **OpenSSH directives in `sshd_config`, identical on Linux** — it transfers more
  literally than almost anything else in the port. `restore-sshonly` and
  `ssh-firewall` are policy with a Linux mechanism (`ufw`/`firewalld`/`nftables`).
  `ssh-preflight` needs rethinking rather than porting: refusing to install
  because sshd exists is right on Windows and absurd here, but its real concern —
  **SD writing into an `sshd_config` it does not own** — is sharper on Linux, not
  softer. **This is entry 13.**
- ***12 `secure-*` — WINDOWS MECHANISM, TRANSFERABLE INTENT.*** Lock the global
  catalogue, the pcode library, the credential store, the audit log, the dump
  directory, the SDSYS system directories. On Linux these are POSIX modes,
  ownership and UMASK — **which is precisely §L's security posture**. Not ports;
  reimplementations of the same policy, and the port's scripts are the clearest
  statement of what that policy is.
- **7 with a direct Linux need, most already scheduled** — `upgrade-voc` and
  `upgrade-dicts` (§F1/§F2), `check-install` (§F7), `finish-install`,
  `clean-deadvoc`, `api-listener`, `restart-sd`.

***SO THE GAP IS NOT "31 SCRIPTS". IT IS AN ENTIRE VERIFICATION LAYER PLUS THE
POSIX EXPRESSION OF 12 SECURITY POLICIES.***

### PowerShell is on the development machine — measured 9 Sep 2026

***THE OWNER INSTALLED THE `pwsh` SNAP (7.6.5) FOR DEVELOPMENT AND RULED IT MUST
NOT BECOME AN INSTALL REQUIREMENT.*** Nothing this project ships uses it, and
the language split below is unchanged. **It is a reading aid, not a dependency.**

**What it actually buys, measured rather than hoped:**

| | |
|---|---|
| `.ps1` in the port | **157** |
| reference Windows-only mechanism (`Get-LocalUser`, ACLs, registry, services, `.exe`) | ***130*** — these cannot run here whatever interpreter exists |
| no obvious Windows mechanism | 27 |

***SO `pwsh` DOES NOT MAKE THE PORT'S SUITE PORTABLE, AND IT SETTLES ENTRY 8 BY
MEASUREMENT RATHER THAN BY READING***: `assert-current.ps1` carries **40**
Windows-mechanism hits, so *"a rewrite, not a copy"* stands.

***WHAT IT DID BUY, AND IT FOUND A REAL DEFECT IN AN HOUR.***
`test-fixlist-units.ps1` **runs on Linux** and is a consistency checker for
`PRE_RELEASE_FIXES.md` — index rows against detail sections, struck-in-index vs
silent-in-section, and citations of ids that do not exist. Against the port:
**284 passed, 0 failed**. It takes `-Root`, so it can be aimed here.

***AIMED AT THIS FILE IT REFUSED RATHER THAN SCORING GREEN*** — *"no index table
found - every check below would have passed by measuring nothing"*, exit 2 —
**the same null-case discipline entry 9 found in `check-stale-leads.py`**. The
sole blocker is one cell: it matches `^\|\s*\|\s*SEV\s*\|` (line 106), so the
port's header is `| | SEV | … |` and this file's said `| ID | SEV | … |`.

***AND WITH THAT ONE CELL CHANGED IT FOUND TWO GENUINE DEFECTS HERE:*** three
citations reading `PRE_RELEASE 170` and one reading `PRE_RELEASE 100 and 103`
**meant the PORT's entries** but are indistinguishable — to a reader or a tool —
from citations of *this* file's ids. **This file's own header says the two
numbering spaces are not comparable**, so the ambiguity was already a defect;
the tool merely named it. ***CONVENTION, ADOPTED 9 Sep 2026: A PORT ENTRY IS
CITED AS "the port's entry N", NEVER AS "PRE_RELEASE N".*** Fixed at all four
sites; the checker then reports **26 passed, 0 failed, exit 0**.

***ADOPTED ON THE OWNER'S RULING, 9 Sep 2026: THIS FILE'S HEADER IS NOW
`| | SEV | What | Where |` AND THE CHECKER RUNS AGAINST THE REAL FILE.***
**26 passed, 0 failed, exit 0**, and `## 2`'s heading gained its `DONE` marker
to clear the one standing NOTE — a note that is always present is a note nobody
reads. Run it with:

```sh
pwsh -NoProfile -File /home/don/Projects/SDCoreProject/sd4windows/sdb_ai/sd64/gplbld/test-fixlist-units.ps1 -Root /home/don/Projects/sdcore4linux
```

***IT HAS BEEN WATCHED REFUSING AND FAILING ON THIS FILE, NOT ONLY PASSING***,
which is what makes the green worth anything: **exit 2** *"no index table
found"* before the header changed, and **2 FAILs** on the citations before they
were fixed. **It is `pwsh`-only and lives in the port's tree** — a development
convenience, so nothing may come to depend on it; a Linux-native replacement is
still entry 9's business.

***AND IT ONLY CHECKS THIS FILE.*** It says nothing about PROJECT_STATUS.md,
which is the document `check-stale-leads.py` was for and where entry 9's real
gap remains.

### What language, and it should not default

**The owner's expectation, 9 Sep 2026:** *"most powershell scripts will need to
be converted to bash."* True for the count. **But the tree already answers this
two different ways, and the split is not arbitrary:**

- **`installsdai.sh` is bash and stays bash** — CLAUDE.md makes that a rule.
- ***EVERY BUILD AND CHECKING TOOL HERE IS ALREADY PYTHON*** — `bbcmp.py`,
  `bootstrap`-era `pcode_bld.py`, `gen_includes.py`, and this week
  `check-msglen.py`, `mkbasicsyntax.py`, `checksyntax.py`.

**A recommendation rather than a survey:**

| Kind | Language | Why |
|---|---|---|
| operational — start/stop, install packages, write a config block, set modes | **bash** | shell-shaped work, matches `installsdai.sh`, and the reader is an administrator |
| verifiers and their unit tests | **Python** | they parse output, compare before/after state and hold exit-code discipline. PowerShell's structured output has no bash analogue, and rewriting 51 verifiers plus **28 unit tests** in bash reproduces in `awk` and `sed` what the port got from objects |

***THE 28 UNIT TESTS ARE THE ARGUMENT.*** They are test code that drives other
test code against fixtures. In bash that is a large amount of quoting and
temporary files; in Python it is `unittest`, which is already available because
the build requires Python.

**Not a decision this file can take** — it is the owner's, and it should be taken
before the first verifier is written rather than discovered after twenty.

### The verifiers whose subjects are this project's too

| The port proved | With | The plan schedules it at |
|---|---|---|
| the three tiers | `verify-tiers`, `verify-tierapi`, `verify-tierchange` | §6 / §L — *"the largest block in the document and the one where half of it is worse than none of it"* |
| lower-case names | `verify-fold`, `verify-lcnames`, `verify-nocase` | §7 / §M |
| the upgrade path | `verify-upgrade`, `upgrade-voc`, `upgrade-dicts` | §5 / §F1 |
| the catalogue gates | `verify-catgate` | §1 / `B1`,`B2` — **already committed here, unexercised** |
| transactions | `verify-txn` | §2 / `A1`–`A6` — **entry 6** |

***THE DECISION IS NOT "PORT 31 SCRIPTS".*** It is what this project's
verification story is at all, and there are three shapes: reimplement the
relevant verifiers as shell or Python; build a smaller SD-BASIC harness that
runs inside `sd`; or accept manual check tables in PROJECT_STATUS and say so.
**The third is what is happening by default, and by default is the wrong way to
choose it** — steps 1 to 4 have accumulated an unexercised check table each,
which is the shape of a decision nobody made.

## 2. The editors — **S** — ***DONE 9 Sep 2026***

**What this tree has.** `GPL.BP/MICRO`, catalogued `$MICRO`, reached by
`MICRO` in both `VOC_TEMPLATE` and `NEWVOC`. `EDIT` and `ED` both point at
`$ED`, the line editor.

**What the port has.** No `MICRO` program — the owner ruled it out on 16 Aug
2026 (*"it launches an external editor"*, a containment concern) and it went on
17 Aug. In its place `gpl.bp/EDIT`, catalogued `$EDIT`, reached by **both**
`edit` and `micro`, selecting between **Microsoft Edit** and **micro**. Its
3 Sep 2026 changelog entry — *"the full-screen editors now come with SD,
installing no longer downloads them"* — is about bundling them in the installer.

**So the port's position is not "no external editors".** It removed one program
and shipped a better one, then bundled the editors it calls. Reading the 16 Aug
removal alone gives the opposite impression, and this entry exists partly to
stop that misreading.

***BOTH EDITORS ARE PRESENT ON THE DEVELOPMENT MACHINE*** — `/usr/bin/micro` and
`/usr/bin/edit`, checked 9 Sep 2026 — so on Linux the question is not
availability but whether SD ships them, depends on them, or degrades honestly
when they are absent (entry 4). §H excludes *"editor bundling via winget"*,
which is a **mechanism**; the packaging question here is `apt`/`dnf` and is not
the same question.

***THE OWNER RULED ON 9 Sep 2026 AND THE REASONING IS THE USEFUL PART.*** The
port bundled both editors *"as we wanted to know what version was included
rather than having a situation where whatever the user got was dependent on the
date of the download."* **That reason does not transfer**: on Linux the
distribution's package manager already pins and updates micro, and it is the
practice this project keeps. So:

- **Microsoft Edit is dropped.** Not excluded as Windows-only — it runs on Linux
  — but not wanted.
- **micro stays, at whatever version the distribution ships.** No bundling, no
  download step, nothing in the installer that fetches an editor.
- ***THE SD BASIC SYNTAX HIGHLIGHTING IS RETAINED, AND IT IS THE ONLY PIECE OF
  THE PORT'S EDITOR WORK THAT COMES ACROSS.***

**Implemented the same day.** `gplbld/mkbasicsyntax.py` and
`gplbld/checksyntax.py` ported; `gplbld/microcfg/syntax/sdbasic.yaml` generated
from **this tree's** `sdsys/GPL.BP/BCOMP` — 218 statements, 37 reserved words,
176 intrinsics, validated at 24 quoted patterns and 0 bad. Generated rather than
copied on principle: BCOMP is the compiler, so the highlighting cannot drift
from the language. **It came out byte-identical to the port's** apart from the
header, which is itself the measurement that the two trees' BCOMP tables agree.

***AND ONE THING HAD TO CHANGE IN SD OR THE FILE WOULD HAVE DONE NOTHING.***
micro picks a syntax file by matching a regex against the **file name it is
given** — the working copy's, not the record's. This tree's `MICRO` wrote
`<record>.editing`; `sdbasic.yaml` detects `\.sdbasic$`. So `MICRO` now appends
`.sdbasic` for a BP record, using the port's own test
(`DictText # "DICT" and upcase(InFileName[-2,2]) = "BP"`). Checked against the
regex: `MYPROG.editing.sdbasic` highlights, `MYPROG.editing` and
`DICT.MYPROG.editing` do not — which is the intended answer for a VOC or data
record.

**Still undecided, and NOT settled by the above:** whether `EDIT` should stop
meaning the line editor (entry 3), and whether `MICRO` should check the editor
exists before shelling out (entry 4). The ruling was about which editors ship,
not about those two.

## 14. `sudo` is this project's elevation model, and nothing defines it

***RULED 9 Sep 2026: SD SHIPS A `sudoers.d` DROP-IN FOR A GROUP SD OWNS.***
Shape 3 below, chosen by the owner from the three offered. **This is recorded as
a selection, not as his words** — he picked the shape; the wording here is mine.

**What the ruling settles, and what it therefore commits to:**

- **Entry 18's second gate reads SD's own group**, not `sudo`/`wheel` and not
  `sudo -n -l`. That is what makes it portable across the distributions the
  installer serves, and it sidesteps the three-answer problem below entirely.
- **The 10 call sites stop hanging**, because the named commands are `NOPASSWD`
  for that group.

***THE COST THE RULING DOES NOT REMOVE, AND IT MUST BE DESIGNED FOR:*** `sudo
passwd` is **unrestricted by argument**, so a drop-in that names it plainly is
root by another route — `sudo passwd root`. The same is true of `usermod -aG`
(add yourself to `sudo`). **These need wrapping in a script SD owns that refuses
`root` and any name not an SD account**, or the drop-in grants more than the
tier does.

**Open sub-decisions this ruling creates** (none is settled by it):

| | |
|---|---|
| the group's name | `sdusers` (all SD users) and `sdu_<name>` (per account) are taken. Something like `sdadmin` is the gap |
| who is put in it | `CREATEA` on an ADMINISTRATOR-tier account, presumably — which ties this to §L2 and entry 18 |
| where it is written | the installer, and `deletesdai.sh` must remove it |

***A TRAP TO WRITE INTO WHATEVER BUILDS THIS: A MALFORMED `sudoers` FILE CAN
LOCK `sudo` OUT OF THE MACHINE.*** The drop-in must be validated with
`visudo -cf <file>` **before** it is moved into `/etc/sudoers.d/`, installed
mode **0440**, and given a name with no `.` or `~` (sudo ignores those silently
— a file that is ignored looks exactly like one that grants nothing). **And
`#includedir /etc/sudoers.d` must be confirmed present in `/etc/sudoers` rather
than assumed**, or the drop-in is inert.

### Built 9 Sep 2026 — the mechanism. ***IT IS NOT YET WIRED UP***

| | |
|---|---|
| `gplbld/sd-elevate` | the helper. Verbs `useradd`/`userdel`/`passwd`/`groupadd`/`groupdel`/`addgroup`/`delgroup`/`setgid`. Installed `/usr/local/sbin/sd-elevate`, **root:root 0755** |
| `gplbld/sdcore.sudoers` | `%sdadmin ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate` — **one command, not eight**. Installed `/etc/sudoers.d/sdcore` 0440 |
| `gplbld/test-sd-elevate.py` | 30 rows: **24 refusals, 6 controls** |
| `installsdai.sh` | creates `sdadmin`, installs the helper, `visudo -cf` **before** installing the drop-in, and refuses if `/etc/sudoers` has no `includedir` |
| `deletesdai.sh` | removes drop-in, helper, group — **drop-in first**, so a sudoers rule never outlives the group it names |

**Whitelists, not blacklists**: groups must be `sdusers`/`sdu_*`/`sdg_*`, so
*"add me to `sudo`"* has no spelling; users must be ≥ `UID_MIN` and never
`root`/`sdsys`; `setgid` is confined to the accounts root with `realpath` first,
so a planted symlink cannot aim it out.

***THE HELPER IS NOT UNDER `/usr/local/sdsys` AND THAT IS DELIBERATE.***
`installsdai.sh` does `chown -R sdsys:sdusers "$sdsysdir"` and `chmod -R 755`.
A helper living there would be **sdsys-writable**, so reaching the `sdsys`
account would mean rewriting the one command sudoers grants — root. It lives in
`/usr/local/sbin`, root-owned, outside that recursive chown.

**Measured, not asserted:** self-test **30 passed / 0 failed** as uid 1000; and
***the test was watched FAILING*** — pointed at a stub that permits everything
it scores **6 passed / 24 failed, exit 1**, so the 30/0 is not a test that
passes regardless. `visudo -cf` likewise **discriminates**: the drop-in parses
OK, a deliberately malformed copy is rejected exit 1. All four scripts
`bash -n`/`py_compile` clean, no BOM, 0 CR.

***WHAT IS STILL INERT, AND THIS IS ENTRY 12's TRAP: THE CALL SITES STILL CALL
RAW `sudo`.*** `CREATE_USER:64`, `SET_PASSWD:115`, `DELACC:197,223`,
`CREATEA:306,331,634,636`, `MODIFYA:108,131` are **unchanged**. So the helper
ships and nothing invokes it — **the hang is not yet fixed.**

***`sdadmin` NOW GETS MEMBERS, 9 Sep 2026 — half the chicken-and-egg is gone.***
The owner ruled that `CREATEA` adds administrators to the groups, and it now
adds an ADMINISTRATOR-tier account's person to `sdadmin` (messages 10030/10031)
beside the `sdusers` add that was already there. **That makes the drop-in
reachable for the first time.**

***BUT IT ADDS AN ELEVENTH RAW `sudo` CALL RATHER THAN USING THE HELPER, AND
THAT IS DELIBERATE.*** It cannot use `sd-elevate` yet for two reasons: the
**first** administrator is not in `sdadmin` at the moment the call runs, so the
helper would refuse the very call that creates them; and the helper's group
whitelist is `sdusers`/`sdu_*`/`sdg_*` and **does not include `sdadmin`**.
***SO THE MIGRATION MUST ALSO DECIDE WHETHER `sdadmin` JOINS THAT WHITELIST***
— which means an administrator may create administrators, intended but worth
naming — **and how the first one is bootstrapped, which is the installer's job,
not a verb's.**

**Nothing here has been installed** — the installer edits are unrun
(`PRE_RELEASE` 15: an install builds `origin/main`).

**One latent bug found while writing it, worth having anyway:**
`MODIFYA:131` shells out to **`deluser`, which is Debian-only** — it cannot work
on the Arch and RHEL branches the installer serves. The helper uses portable
`gpasswd -d`. Same for `groupadd -U`, recent shadow-utils only; the helper adds
members with `gpasswd -a`.

***RAISED BY THE OWNER, 9 Sep 2026:*** *"I assume some scripts need to run as an
administrator here as they did on windows."* Correct, and it is already true of
code that ships — this is not future porting work.

**Eight `GPL.BP` programs shell out to `sudo` from `OS.EXECUTE`:**

| Program | Command |
|---|---|
| `CREATE_USER:64` | `sudo useradd -m <name>` |
| `SET_PASSWD:115` | `sudo passwd <name>` |
| `DELACC:197,223` | `sudo groupdel`, `sudo userdel` |
| `CREATEA:306,331,634,636` | `sudo chmod g+s`, `sudo usermod -aG sdusers`, `sudo groupadd` |
| `MODIFYA:108,131` | `sudo usermod -aG`, `sudo deluser` |

***AND NOTHING IN THE PROJECT CONFIGURES sudoers*** — zero hits for `sudoers`,
`NOPASSWD` or `visudo` across `installsdai.sh`, `deletesdai.sh` and all of
`GPL.BP`.

**So the ADMINISTRATOR tier's real privilege is decided outside SD**, by whatever
sudo rules the machine already has, and there are only two states:

- **Broad sudo** — then the SD administrator is root. `sudo passwd root` is in
  reach, and so is everything §L withholds. **The tier is then a UI convention,
  not a boundary**, exactly as entry 13 finds for ssh.
- **No sudo** — then `CREATE.ACCOUNT`, `DELETE.ACCOUNT` and password setting
  fail, or **block on a password prompt inside an SD session**, which is a
  hang rather than an error.

***THE PLAN SAYS `sudo` ZERO TIMES.*** It reasons about root — §L5:1164 says the
Windows elevated-session carve-out's *"Linux equivalent is root, and it should be
stated rather than inherited by accident"*, which is exactly the right instinct —
but it never connects that to the `sudo` calls already in `GPL.BP`, and plan:17
and §H:853 file elevation under *"none of it applies here"*.

**What has to be decided:** whether SD ships a `sudoers.d` drop-in naming exactly
these commands for a group (the narrow, auditable answer, and the closest thing
to the port's explicit elevation helper), or whether it documents a prerequisite
and refuses to run the verbs when it is absent. **What must not happen is the
present state**, where the answer depends on a machine's history and neither
outcome is detected. Note `sudo passwd` is unrestricted by argument, so a
`sudoers` entry for it is root by another route unless it is wrapped.

### Wired up, 9 Sep 2026 — and the hang was narrower than this entry claimed

***THE MIGRATION'S JUSTIFICATION CHANGED WHEN IT WAS CHECKED, AND THE CORRECTED
ONE IS STRONGER.*** This entry says *"the 10 call sites stop hanging"*. **The
hang is mostly unreachable**: every verb holding one of those calls is
administrator-gated, `USR_ADMIN` is granted only in `CPROC`'s root-entry block,
so the caller's **real uid is 0** and `sudo` never challenges. ***THE EXCEPTION
IS ENTRY 22***, found by asking this question — `!set_passwd` and
`!create_user` are globally catalogued with no gate of their own, so the hang
**is** reachable there, by any account, without being an administrator.

**So the reasons to migrate are these, in order, and only the second was in the
original entry:**

1. ***PORTABILITY, AND IT IS A LIVE BUG.*** `sudo deluser` (`MODIFYA`, twice) is
   **Debian-only**; `groupadd -U` (`CREATEA`, twice) is recent shadow-utils.
   The helper uses `gpasswd -d` and `gpasswd -a`. **MODIFY.ACCOUNT's demotion
   path could never have worked on Arch or RHEL.**
2. **Least privilege**: eight unrestricted-by-argument commands become one
   validated command.
3. **The hang**, where entry 22 shows it is reachable.

***EVERY MAPPING WAS VALIDATED WITH `--dry-run` BEFORE A LINE OF BASIC MOVED***,
which is what that flag is for — it validates and prints without acting and
without needing root. **13 of 13** resolved to exactly the command the raw call
ran. ***TWO SITES CHANGE ARGUMENT ORDER AND THAT IS THE EASY THING TO GET
WRONG***: raw `usermod -aG <group> <user>` becomes `addgroup <user> <group>`,
and raw `groupadd -U <members> <group>` becomes `groupadd <group> <members>`.

***`sdadmin` JOINS THE WHITELIST — THE DECISION THIS ENTRY ASKED TO BE NAMED.***
An administrator may make another administrator. **It is delegation, not
escalation**: reaching the helper at all means already holding `sdadmin` or
being root, so the caller gains nothing they lack. **The residual is real and is
written into the script**: `sdadmin` membership is an operating-system privilege
that stands independently of the register, so this widens who holds it. Two
things bound it — `require_sd_user` keeps root, `sdsys` and every system account
out of reach, and SD fails closed because `CPROC` wants **both** halves, so a
bare `sdadmin` member is not an SD administrator.

***AND THE CALL THIS ENTRY SAID COULD NEVER USE THE HELPER NOW DOES.*** It
records that `CREATEA`'s `sdadmin` add must stay raw, *"because the first
administrator is not in `sdadmin` when the call runs, so the helper would refuse
the very call that creates them"*. **That reasoning stops at sudo's policy and
the code never gets there**: this path only runs in a session that reached
`CPROC`'s root-entry block, so its real uid is 0, and **sudo permits root
whatever the drop-in says**. The `%sdadmin` rule is what a *non-root*
administrator would need, and there is no such caller.

***WHITELISTING `sdadmin` EXPOSED A HOLE THAT WAS ALREADY OPEN, AND IT WAS FOUND
BY WRITING A TEST ROW THAT FAILED.*** `groupdel` validated only *"is this an SD
group"*, which is the right question for adding somebody to a group and the
wrong one for destroying it. ***MEASURED BY RUNNING HEAD's OWN HELPER***:
`sd-elevate --dry-run groupdel sdusers` → `groupdel -- sdusers`, **exit 0**.
Deleting `sdusers` unregisters every SD user at once (`LOGIN`'s entry gate reads
it); deleting `sdadmin` leaves the sudoers drop-in naming a group that does not
exist, taking the helper from every administrator. **Both are now refused by
name**; only the per-account `sdu_*`/`sdg_*` groups are destroyable, which is
all `DELACC:197` ever asks for.

**Self-test 36 passed / 0 failed** (28 refusals, 8 controls), up from 30/0. The
four new rows are chosen so that **removing `sdadmin` from the whitelist fails
two of them** — the guard is against drift, not just against today.

### Measured on this machine, 9 Sep 2026 — the hang is real, not predicted

| | |
|---|---|
| `sudo -n -v` as `don` | ***"a password is required", exit 1*** — sudo here is password-required, not NOPASSWD |
| `sudo -n` at the call sites | ***0 of 10*** pass `-n`; none handles a password (grep over the 5 programs) |
| group names | `don` is in **`sudo`**; **`wheel` does not exist** on this box |

***SO `create.account` REACHING `sudo useradd` BLOCKS ON A PASSWORD PROMPT
INSIDE THE SD SESSION.*** That is the hang this entry predicted, now measured.

***AND THE MEMBERSHIP TEST HAS THREE ANSWERS, NOT TWO — THE PORT'S PRE_RELEASE
93 LESSON ARRIVING HERE.*** `sudo -n -l` exits **1** both when the caller is a
sudoer who needs a password **and** when the caller may not sudo at all. The
exit code cannot separate them; only locale-dependent message text can. **A
membership test built on that exit code refuses a legitimate administrator**,
which is entry 18's second gate failing closed on its own instrument.

**Three shapes, each with its flaw stated:**

1. **Group membership of `sudo`/`wheel`** — no password, deterministic, readable.
   **But the group name is distro-dependent** (`sudo` on Debian/Ubuntu, `wheel`
   on RHEL/Arch/SUSE) and this installer serves both families; and it **misses a
   user granted by a per-user `sudoers.d` rule** with no group.
2. **Ask sudo** (`sudo -n -l`) — authoritative, and defeated by the three-answer
   problem above.
3. ***SD SHIPS A `sudoers.d` DROP-IN FOR ITS OWN GROUP*** — then the test is
   membership of a group **SD owns and names**, identical on every distribution,
   and the 10 call sites stop hanging because the named commands are `NOPASSWD`.
   **This is the only one of the three that fixes the hang and the test with the
   same change.** Its cost is unchanged: `sudo passwd` unrestricted by argument
   is root by another route, so those commands need wrapping or constraining.

**Recommended: 3, with the wrapping caveat. It is the owner's ruling, not this
file's** — and it should be taken before entry 18 is implemented, because it
decides what entry 18's "member of sudoers" test actually reads.

## 20. SD does not know which person is the administrator

***FOUND 9 Sep 2026 WHILE STARTING ENTRY 18's SECOND COMMIT, AND IT STOPPED
IT.*** The gates were to be swapped for "read the register for this person's
tier". **There is no this-person to read.**

```
CPROC:279    if system(27) = 0 then          ;* entered as root?
CPROC:281      call !EUID_SET('sdsys',rstat) ;* drop to sdsys
CPROC:285      logname = kernel(K$USERNAME, 0)  ;* username in syscom -> sdsys
CPROC:288      void kernel(K$ADMINISTRATOR, 1)  ;* set admin bit
CPROC:291    i = '$LOGIN' ; call @i(j,0)
```

***THE IDENTITY IS REPLACED BEFORE `$LOGIN` RUNS.*** After `sudo sd`, `@logname`
is **`sdsys`**, not the person who typed it. Consequences, none of them
hypothetical:

- **Entry 18's register test has no subject.** *"A registered user of SD as an
  administrator"* needs a name, and the name is gone by `:285`.
- ***`CPROC:2483` IS ALREADY AFFECTED***, and it is shipped code, not planned
  work: `if not(is_grp_member(@logname, acc.record<ACC$GROUP>))` decides who may
  enter an account, and on this path it asks about `sdsys`.
- **An audit trail cannot name the administrator**, for the same reason.

***AND IT CORRECTS ENTRY 18 IN THE OTHER DIRECTION TOO, WHICH IS THE HALF THAT
MAKES THIS CHEAPER THAN IT LOOKS.*** Entry 18 says *"nothing tests sudoers"*.
**Reaching uid 0 through `sudo sd` requires sudoers membership**, so the OS half
is largely enforced already, by the operating system, before SD starts. What is
genuinely missing is the **register** half. (`su` with the root password, or
root's own shell, reach uid 0 without sudoers — so it is "largely", not
"wholly", and that gap is worth stating rather than rounding away.)

**The port's answer, and it is a design rather than a patch:** a separate
`K$OS.ADMINISTRATOR` — *"is the SIGNED-IN PERSON an administrator"* — kept
distinct from the session's `USR_ADMIN` flag, with `@logname` and the audit
message continuing to read the signed-in user.

***RULED 9 Sep 2026: THE PORT'S MODEL — TWO IDENTITIES.*** The owner's
selection from the four shapes offered; **recorded as a selection, not as his
words.** `@logname` keeps the real signed-in person, `USR_ADMIN` stays the
session flag, and a **separate** test answers *"is the signed-in person an
administrator"*. **Not built.**

**What the ruling commits to — three pieces, and the first is the load-bearing
one:**

1. ***`CPROC:285` STOPS REPLACING `@logname`.*** The euid drop at `:281` is for
   file ownership and umask and **stays**; what goes is the identity
   substitution. ***THE ENUMERATION IS DONE — see below.*** ***AND PIECE 1 IS
   BIGGER THAN THIS LINE. SEE "The person is not recoverable" below before
   starting it.***
2. **A new kernel key**, this tree's equivalent of the port's
   `K$OS.ADMINISTRATOR`. ***NEXT FREE NUMBER IS 57*** — `keys.h` runs to
   `K_RUNEXE 56`, checked 9 Sep.
3. **The gates read it** — `CATALOG:108,202`, `DELCAT:119` (today `system(27) #
   0`) and the `kernel(K$ADMINISTRATOR,-1)` sites.

***THE PORT'S `IsAdmin()` IS NOT OURS AND MUST NOT BE COPIED STRAIGHT.*** Its
version asks `getgrouplist()` — *"is this ACCOUNT an administrator"*. **Ours is
`getuid() == 0`** (`linuxlb.c:54-55`), which is *"is this process root"* and
answers the wrong question entirely. The Linux test has to be the owner's own
definition: **sudoers membership AND `ACC$TIER` = `ADMINISTRATOR` in the
register**, keyed on the preserved `@logname`.

***AND THE PORT'S `CN_SOCKET` GUARD TRANSFERS — CHECK IT RATHER THAN ASSUME IT
DOES NOT.*** Its `K_OS_ADMINISTRATOR` returns
`is_admin && (connection_type != CN_SOCKET)`, because an API session is forked
by a privileged service and only the *effective* uid changes, so the real uid
stays privileged and the test answers TRUE for every remote client. **This tree
has `CN_SOCKET 0x02` and `connection_type` (`kernel.h:50,54`)**, and its
`IsAdmin()` reads `getuid()` — the real uid — so ***the identical hole is
available here*** if the new key is written without the guard.

***A WARNING FOR WHOEVER IMPLEMENTS IT, FROM THE PORT'S RECORD RATHER THAN FROM
HERE.*** Its `sdusers` gate ran at `LOGIN:380` *before the account was chosen*,
and the model gave an administrator no account — so **every administrator would
have been refused at the door**. A login-path gate is the one change in this
area that can lock everybody out of the machine, and it should be built with
that failure in front of you.

### The enumeration, 9 Sep 2026 — what reads the identity, and what breaks

**Asked for by the owner before piece 1 is written.** Three things had to be
established first, and two of them corrected the question.

***(a) `@LOGNAME` AND `@USER` ARE THE SAME SLOT.*** `BCOMP:264,288` map both to
`SYSCOM.LOGNAME`, which is `$syscom` slot **14** (`GPL.BP/SYSCOM.H:144`).
**`@WHO` is slot 27** (`:157`) and holds the ACCOUNT, not the person — it is
untouched by this. **An enumeration of `@logname` alone would have missed two
sites**; `@user` is searched here too.

***(b) THE SUBSTITUTION IS IN C, NOT IN `CPROC`.*** `K_USERNAME` only *returns*
`process.username` (`op_kernel.c:232-234`) — it sets nothing. The rewrite is
***`gplsrc/sdext_eguid.c:67`***, where `EUID_SET` does
`strncpy(process.username, Arg, …)`, *"change sd process user name to match"*.
`CPROC:285` then copies that into slot 14. **So there are two layers and the C
one is the origin; changing `CPROC:285` alone leaves `kernel(K$USERNAME,0)`
still answering `sdsys`.**

**(c) The sites — 14, across 8 files:**

| Site | What it decides | After the change |
|---|---|---|
| ***`LOGIN:191-195`*** | `is_grp_member(@logname,'sdusers')` → **terminates the connection** | ***THE LOCK-OUT. See below*** |
| `CPROC:2483` | `is_grp_member(@logname, ACC$GROUP)` — account entry on `LOGTO` | asks about the person, not `sdsys` — **an administrator loses universal `LOGTO`** unless the gate gains an admin bypass |
| `APISRVR:363` | the same gate on the API path | **probably unaffected**: `APISRVR:119` sets its own `logname` and does not go through `CPROC`'s drop. **Not verified** |
| `CPROC:2890`, `:3110` | logout / PDUMP of other users' processes | ***no change*** — both sit inside `not(kernel(K$ADMINISTRATOR,-1))`, so admins skip them and non-admins already carry the real name |
| `LOGIN:259` | `initial.account = upcase(@logname)` | ***no change*** — `LOGIN:240` hard-codes `"SDSYS"` for the admin case and wins first, so the sudo path never reaches `:259` |
| `CPROC:3333` + `LOGIN:392` | command stack keyed by user | benign: history becomes per-person instead of shared under `sdsys` |
| `ED:645`, `ED:2400` | *"Updated by …"* in edited records | improves — names the person |
| `PDBG:52`, `PDEBUG:47` | debugger id `DR.<who>!<logname>` | cosmetic |
| `ATVAR:64,84` · `WHOAMI:43` | expose `@LOGNAME`/`@USER` | user-visible, improves. ***`WHOAMI` IS THE WITNESS*** — it prints User, Account, uid, euid and the admin flag together |

***THE LOCK-OUT IS REAL AND IT IS AT `LOGIN:191`, WHICH RUNS BEFORE THE ACCOUNT
IS CHOSEN AT `:240` AND ENDS THE CONNECTION.*** Today the `sudo` path passes it
**only because the identity has already been replaced**: `@logname` is `sdsys`,
and `sdsys` is in `sdusers` — measured, `sdusers:x:979:root,sdsys,don`. **Make
`@logname` the real person and the gate starts asking about that person**, so an
administrator who is a sudoer but was never added to `sdusers` is refused with
sysmsg 5009 and cut off.

***AND THAT PARAGRAPH OVERSTATED IT. CORRECTED 9 Sep 2026, SAME SESSION, BY
READING WHAT ALREADY POPULATES `sdusers`.*** Three paths already do:
`CREATEA:344-352` adds **every USER account's** person to `sdusers` whatever its
tier; `installsdai.sh:478` adds the installing user; `:404` adds `root`.
Measured: `sdusers:x:979:root,sdsys,don`. **So a registered SD user passes the
gate under the new identity too, and the people it would refuse are exactly the
ones with no SD account — which is the owner's stated intent** (*"if they are
not a registered user they should be refused entry"*). ***THE RESIDUAL RISK IS
NARROW RATHER THAN GENERAL***: a person who is a sudoer, has no SD account, and
today reaches a session only because the identity was masked as `sdsys`. **The
gate becoming honest about that is the point of the change, not a regression.**
The emphatic wording above is left standing, with this correction beneath it,
because the overstatement is the thing worth seeing.

### The person is not recoverable by removing the substitution — 9 Sep 2026

***PIECE 1 WAS STARTED AND STOPPED HERE, FOR A REASON WORTH READING BEFORE
TRYING AGAIN.*** *"Stop replacing `@logname`"* does **not** leave the real
person behind. **On `sudo sd` the process genuinely is root**: `getuid()` is 0,
and `process.username` is taken from `my_uptr->username` at `kernel.c:198`,
which is the OS identity. ***SO REMOVING THE `sdsys` REWRITE SWAPS `sdsys` FOR
`root`, NOT FOR THE PERSON.***

***AND THAT FAILS SILENTLY IN THE WORST DIRECTION — IT LOOKS LIKE IT WORKED.***
`root` is a member of `sdusers` **and** of the account groups: measured,
`sdusers:x:979:root,sdsys,don` and `sdu_don:x:1001:root,don`. **So
`LOGIN:191`'s test and `CPROC:2483`'s test would both PASS**, every gate would
go green, and every administrator action would still be attributed to a
non-person. **A verdict from an instrument that never reached the condition it
claimed to measure** — the exact shape CLAUDE.md's instrument rule exists for.

***THE REAL PERSON IS NOT IN THE PROCESS AT ALL, SO IT HAS TO BE FETCHED.***
`sudo` exposes the invoker only in the environment, and ***NOTHING IN THIS TREE
READS `SUDO_USER`*** — grep across `gplsrc/`, `sdsys/` and the installer:
**zero hits.** There is also **no general set-session-username kernel key** to
write it back with: `op_kernel.c:716` is `op_login()`, the API path only.

**Three candidate sources, none free:**

| | Works when | Fails when |
|---|---|---|
| `SUDO_USER` | the session came through `sudo` | `su`, a root login, or any non-sudo route — and it is an environment variable |
| `getlogin()` | there is a utmp entry | cron, containers, some ssh configurations return empty |
| owner of the controlling tty | interactive sessions | no tty at all — API, phantom, piped input |

***THE ENVIRONMENT-VARIABLE OBJECTION IS WEAKER THAN IT LOOKS AND SHOULD BE
SAID OUT LOUD:*** `SUDO_USER` can only be forged by somebody who is already
root, and a person who is already root has nothing left to gain. **The real
weakness is absence, not forgery** — which is why the null case matters more
than the trust case.

***WHATEVER IS CHOSEN MUST REFUSE TO GUESS.*** If no source answers, the
identity must be recorded as unknown and say so, rather than falling back to
`root` — because falling back to `root` is precisely the silent pass above.

### Piece 1 — ***WITNESSED 9 Sep 2026 ON THE 17:53 INSTALL***

***THE OWNER RAN `WHO.AM.I` UNDER `sudo sd` AND IT SAID `User : don`.*** The
predicted table below is met row for row.

```
User        : don          Process UID : 0      Admin?      : Yes
Account     : SDSYS        Process EUID: 999    umask       : 2
User Number : 2            Process GID : 0      Host Name   : gitorli
                           Process EGID: 979    Sys Path    : /usr/local/sdsys
```

***AND THE THIRD OF THE THREE DISTINGUISHABLE CAUSES BELOW WAS RESOLVED IN THE
GOOD DIRECTION WITHOUT ANYONE HAVING TO ASK: MESSAGE 10032 DID NOT FIRE.*** So
`SUDO_USER` reached the process, the `getlogin()` fallback was never needed, and
the unknown arm — the one this entry called a deliberate under-reach — was not
taken. **`Admin? Yes` re-confirms the entry-19 fix on the live path**, which was
the fifth row of the prediction and the one silent regression available.

***WHAT THIS RUN DOES NOT WITNESS, CHECKED RATHER THAN ASSUMED.*** The install
carries `K$REAL.USER` **×3** and `grant.administrator` **×0** in
`/usr/local/sdsys/GPL.BP/CPROC`, and `MESSAGES/10033` / `10034` are **absent**.
It is `origin/main` at `ef75eb2`. **So `Admin? Yes` here is the OLD
unconditional grant, not entry 18 commit 2's gate**, and reading it as evidence
for the gate would be a verdict from an instrument that never reached the
condition.

### Piece 1 as built, 9 Sep 2026 — the reasoning, written before the witness

***RULED: `SUDO_USER`, THEN `getlogin()`, ELSE UNKNOWN*** (owner's selection).

| Where | What |
|---|---|
| `gplsrc/keys.h:169` · `GPL.BP/INT$KEYS.H` | **`K_REAL_USER` / `K$REAL.USER` = 57**, free on both sides (checked) |
| `gplsrc/op_kernel.c`, beside `K_USERNAME` | the key: `SUDO_USER` → `getlogin()` → `""`. **Returns empty rather than guessing** |
| `GPL.BP/CPROC` (the drop) | `logname` now takes the **person**, not `kernel(K$USERNAME,0)`. The euid drop is untouched |
| `GPL.BP/CPROC` (the `LOGTO` gate) | administrators pass explicitly: `not(kernel(K$ADMINISTRATOR,-1)) and not(is_grp_member(…))` |
| `MESSAGES/10032` | the unknown-identity warning |

***THE `LOGTO` BYPASS IS NOT NEW PRIVILEGE, IT IS THE SAME PRIVILEGE MADE
LEGIBLE.*** `CREATEA:681` builds every account group with
`groupadd -U root,sdsys,<user>`, so `sdsys` was in every account it created and
a privileged session (`@logname` = `sdsys`) already entered them all — the
membership test was passing on a **side effect of how the groups are built**.
With `@logname` now the real person that side effect is gone, and without the
bypass `LOGTO` would begin refusing accounts it has always allowed.

***OBJECTION, RECORDED RATHER THAN RESOLVED*** (CLAUDE.md's rule): implicit and
explicit grants are equivalent only for accounts `CREATEA` actually made.
**Measured: `sdu_don` is `root,don` and has no `sdsys`**, so for *that* account
an administrator could not enter before and now can — **a widening, not a
preservation.** Why `sdu_don` differs remains an open lead.

***AND THE UNKNOWN ARM DOES NOT REFUSE THE SESSION, WHICH IS A DELIBERATE
UNDER-REACH.*** With no source able to name the person it keeps the old
behaviour (`logname` = `sdsys`) and **says so** with 10032, because turning an
unidentifiable privileged session away is a lock-out risk that belongs with a
ruling rather than with this line. ***THE COST IS REAL: an unidentified
privileged session still calls itself `sdsys`.*** **Whoever builds the register
gate must not let an unknown identity satisfy it** — `sdsys` is an account, not
a person, and that arm is exactly where it would slip through.

**Checked:** clean `rm -f gplobj/op_kernel.o` rebuild, **0 warnings**, `bin/sd`
boots exit 0 — and no implicit-declaration warning, so `getenv`/`getlogin` are
declared through `sd.h`. Message 10032 is 68 bytes against a bound of 231.
`CPROC` block counters **unchanged from HEAD** (`begin case` 31, `end case` 31,
`loop` 34, `repeat` 36), and the controlled compile comparison gives
**identical error classes AND counts**, so neither edit introduced one.

***WHAT IS NOT ESTABLISHED: NONE OF IT HAS RUN.*** `CPROC` is compiled only by
the install's two-stage bootstrap.

***THE WITNESS IS THE VERB `WHO.AM.I`, NOT `WHOAMI`. CORRECTED 9 Sep 2026 AFTER
THE OWNER TRIED IT AND IT WAS NOT THERE.*** This entry said `WHOAMI`, which is
the **program** name in `GPL.BP`; the **verb** is `WHO.AM.I`
(`VOC_TEMPLATE/WHO.AM.I` = `V` / `CA` / `$WHOAMI`, present in `NEWVOC` too).
`whoami` and `WHOAMI` both answer *"is not in your VOC"*, measured by the owner
under `sudo sd`. ***A NEAR-MISS NAME OF EXACTLY THE KIND CLAUDE.md WARNS
ABOUT***, and it cost a round trip.

***AND `WHO` IS A THIRD, DIFFERENT THING — DO NOT USE IT AS THE WITNESS.***
`VOC_TEMPLATE/WHO` is `V` / `IN` / `16`, a CPROC internal verb, and it prints
the **user number and the ACCOUNT** — the owner's run answered `65 SDSYS`. That
`SDSYS` is `@who`, the account, and it is **correct and unchanged by this
work**; it is not `@logname` and says nothing about the person.

***THE BASELINE IS BANKED. Owner ran `WHO.AM.I` under `sudo sd` on the 11:35
install, 9 Sep 2026, BEFORE any of this work is installed:***

```
User        : sdsys      Process UID : 0      Admin?      : Yes
Account     : SDSYS      Process EUID: 999    umask       : 2
User Number : 65         Process GID : 0      Host Name   : gitorli
                         Process EGID: 979    Sys Path    : /usr/local/sdsys
```

***`Process UID : 0` IS THE LINE THAT MATTERS, AND IT CONFIRMS BY MEASUREMENT
WHAT THIS ENTRY ARGUED FROM SOURCE.*** On `sudo sd` the **real** uid is 0, so
`process.username` would be `root` — **deleting the substitution would have
produced `root`, not the person**, and every gate would have passed silently.
The `K$REAL.USER` design is not belt-and-braces; it is the only thing that can
answer the question.

**And the drop is doing exactly its job:** `EUID 999` / `EGID 979` are `sdsys`
and `sdusers` (`sdsys:999:979`, checked), against `UID 0` / `GID 0` underneath.
***THE PRIVILEGE DROP AND THE IDENTITY ARE ALREADY SEPARATE THINGS ON THIS
SCREEN***, which is the whole premise of piece 1.

| Line | Baseline (measured) | After an install of this work |
|---|---|---|
| `User        :` | **`sdsys`** | ***the person*** — `don`, uid 1000 |
| `Account     :` | `SDSYS` | `SDSYS` — unchanged |
| `Process UID :` | `0` | `0` — unchanged |
| `Process EUID:` | `999` | `999` — unchanged, **the drop stays** |
| `Admin?      :` | `Yes` | `Yes` — **re-checks the entry-19 fix** on the live path |

***IF `User` STILL READS `sdsys` AFTER AN INSTALL, THE THREE CAUSES ARE
DISTINGUISHABLE, WHICH IS WHY THIS IS A USABLE INSTRUMENT.*** The install did
not carry the commits (check `sd --version` date / the binary's mtime); or
`SUDO_USER` never reached the process; or the unknown arm fired — **and that
last one prints message 10032 at start-up**, so it announces itself rather than
being inferred.

**Two incidental findings, both leads rather than established:**

- ***`sdu_don` IS `root,don` AND DOES NOT CONTAIN `sdsys`***, though
  `CREATEA:681` creates account groups with `groupadd -U root,sdsys,<user>`.
  **`-U` is supported on this box** (checked), so the likely explanation is that
  `don`'s group was not made by `CREATEA` — **not verified**.
- ***`ACCOUNTS/SDSYS` NAMES GROUP `sdsys`, AND NO SUCH GROUP EXISTS.*** So
  `CPROC:2483`'s test could never pass for SDSYS. It is masked today by an
  earlier gate: `LOGTO SDSYS` as uid 1000 answers *"SDSYS Account access is
  restricted to privileged users"*, measured, with `LOGTO DON` as the control
  that succeeds.

## 21. `sd -internal` is an unguarded route to the administrator flag

### ***FIXED 9 Sep 2026, AND THE OWNER'S RULING IS WHAT MADE THE COST ACCEPTABLE***

***OWNER, 9 Sep 2026:*** *"this version of SD will be for production, not
development. The source code will be available, but the installer in this
version is not for developers."* And: the project is AI-maintained with **one
human involved**, others forking and filing issues rather than committing.
***THAT DISPOSES OF THE OBJECTION THIS ENTRY RAISED AGAINST ITS OWN FIX.*** The
cost named below is that `-internal` is the only way to compile `CPROC`,
`CATALOG` or `LOGIN` outside an install. **A shipped production system owes an
ordinary user no compiler for its own internals**, and the one person who needs
that instrument has `sudo`.

**Both halves built:**

| | |
|---|---|
| `sd.c` `-INTERNAL` | calls `check_admin()` before setting `internal_mode`, exactly as `-I` does |
| `sd.c` `check_admin()` | ***the `in_group("admin")` arm is REMOVED***; it is now `geteuid() != 0` alone |
| `sd.c`, `Makefile` | ***`SD_DEV_BUILD`*** — the owner's question, below |

### The developer build, on the owner's question of 9 Sep 2026

***HE ASKED WHETHER THE ONE-LINE FIX COULD APPLY ONLY TO A DISTRIBUTION BUILD.
IT CAN, AND THIS PROJECT IS AN UNUSUALLY SAFE PLACE TO DO IT.*** A build-time
escape hatch normally means **the binary you tested is not the binary that
ships**, which is the worst possible place for a difference to hide — and worse
still when the one thing it changes is a privilege check. ***THAT OBJECTION DOES
NOT APPLY HERE, AND THE REASON IS A RULING ALREADY IN CLAUDE.md***:
`installsdai.sh` **clones `main` from GitHub and builds that**, so an installed
system is always built from a clean checkout with default flags. **A developer
binary has no route to a user.** (The same ruling is `PRE_RELEASE` 15's cost, so
this is one place where it pays.)

**Built:** `make EXTRA_C_FLAGS=-DSD_DEV_BUILD`. **`EXTRA_C_FLAGS` is empty
unless passed**, so plain `make` — which is what the installer runs — is
untouched.

***AND IT ANNOUNCES ITSELF TWICE, WHICH IS THE PART THAT MAKES IT ACCEPTABLE
RATHER THAN MERELY CONVENIENT.*** A silent bypass is a binary that cannot be
told from a shipped one by looking at it. `--version` gains
*"DEVELOPER BUILD - -internal is not privilege checked. Not for distribution."*,
and **every use of `-internal` prints a line to stderr**, so it lands in every
transcript rather than having to be remembered.

***THE MATRIX, MEASURED, ALL SIX CELLS, AS `don` uid 1000:***

| Build | `--version` | `-internal WHO` | `WHO`, no flag |
|---|---|---|---|
| default (`make`) | one line | ***refused, exit 1*** | `5 DON`, exit 0 |
| dev (`make EXTRA_C_FLAGS=-DSD_DEV_BUILD`) | ***two lines*** | `DEVELOPER BUILD` on stderr, then `6 DON`, exit 0 | *(unchanged)* |

**The no-flag column is the control**: a gate that refused everything would look
identical in the middle column. ***`bin/sd` IN THE TREE WAS REBUILT DEFAULT
AFTERWARDS***, so what is sitting there now is the shipping build — leaving a
developer binary in `bin/` is exactly the confusion the announcement exists to
prevent.

***`check_admin()`'s OWN TIGHTENING IS NOT CONDITIONAL.*** The `admin` group arm
is gone in both builds. It was never a developer convenience; it was a
distribution-dependent weakness.

***THE `admin` ARM WAS REMOVED FOR THE STRONGER OF TWO REASONS, AND THE WEAKER
ONE IS NOT THE ARGUMENT.*** The weak reason is that it is dead here — measured,
no `admin` group on this machine. **The real reason is that it is NOT dead
everywhere**: on Ubuntu-family systems `admin` was the old sudo group, so this
would have granted `-internal`, `-i`, `-start`, `-stop`, `-k` and `-restart` to
a group SD neither creates nor manages — ***and the fix above would have held on
this machine and quietly not held on those.*** **`sdadmin` was considered and
rejected as the replacement**: naming it would honour the owner's first gate and
skip the second, handing the register bypass back in a narrower form. These five
call sites are operating-system operations, so root is the right question.

***MEASURED, SAME USER, SAME COMMAND, ONE MINUTE APART. `don`, uid 1000, no
`sudo`:***

| Binary | Command | Result |
|---|---|---|
| `/usr/local/sdsys/bin/sd` — installed, **before** | `-internal WHO` | ***`3 DON`, exit 0*** — accepted |
| `.../sdb_ai/sd64/bin/sd` — built, **after** | `-internal WHO` | ***`Command requires administrator privileges`, exit 1*** |
| `.../sdb_ai/sd64/bin/sd` — built, **the control** | `WHO`, no flag | `4 DON`, **exit 0** — ordinary use unbroken |

**The control matters**: a gate that refused everything would score identically
on the first two rows.

***AND THE THIRD ROUTE INTO INTERNAL MODE WAS ENUMERATED RATHER THAN ASSUMED
AWAY.*** `internal_mode` is assigned in exactly three places: `sd.c:333`
(`-INTERNAL`, now gated), `sd.c:344` (`-I`, already gated) and
***`op_kernel.c:140` — `kernel(K$INTERNAL, n)` with `n >= 0` SETS IT***. That
third one is reachable only from a program that already compiled `KERNEL`, which
now requires the gate above; and **every one of the eleven `K$INTERNAL` uses in
`GPL.BP` is an enquiry (`-1`)**, so no shipped verb sets it. ***LEAD, NOT
BUILT***: `K_INTERNAL`'s setter has no `HDR_INTERNAL` guard, which is entry 19's
shape exactly. It is contained today by the gate above rather than by a check of
its own, and one line would make that belt-and-braces.

**Build: `rm -f gplobj/sd.o` then `make`, 0 warnings, `bin/sd` relinked.
`installsdai.sh:645` and `:672` are the only `-internal` invocations in the
project and both already run under `sudo`, so the installer is unaffected —
read, not run.**

### The finding, as measured 9 Sep 2026

***FOUND 9 Sep 2026 WHILE BUILDING 18's GATES, BY TRYING THE THING THE GATE
ASSUMES NOBODY CAN DO.*** Entry 19 argued the `K_ADMINISTRATOR` grant is
contained because ordinary BASIC cannot reach `KERNEL`. **That is true and it is
not the question.**

The chain, each link read in this tree:

| | |
|---|---|
| `BCOMP:3759` | the restricted intrinsics, `KERNEL` among them, resolve only `if internal` |
| `BCOMP:2853` | the `$INTERNAL` **directive** sets `internal`, gated on `kernel(K$INTERNAL,-1)` |
| `op_kernel.c:135` | `K_INTERNAL` just reports `internal_mode` |
| ***`sd.c:310`*** | ***`-INTERNAL` sets `internal_mode = TRUE` with no check of any kind*** |
| `sd.c:320` | `-I`, three lines below, calls `check_admin()` **first** |

**Measured, as `don`, uid 1000, no `sudo`, on the 16:22 install:**

```
ADMPROBE uid = 1000
ADMPROBE user = don
ADMPROBE account = DON
ADMPROBE PRE admin flag = 0
ADMPROBE POST admin flag = 1
ADMPROBE RESULT: ESCALATED - a non-root user granted itself admin
```

The probe was `$internal`, four statements, compiled with
`/usr/local/sdsys/bin/sd -internal BASIC BP ADMPROBE` and run with
`RUN BP ADMPROBE`. ***IT REFUSES THE NULL CASE***: it prints VOID and stops if
the flag is already set, so a privileged session cannot produce a false
ESCALATED. **It prints uid, user and account**, so what it ran as is on the
transcript rather than assumed. Fixture removed afterwards.

***THE FIX IS ONE LINE AND IT IS A RULING, NOT A TYPO.*** `-INTERNAL` should
call `check_admin()` as `-I` does. **What it costs, said out loud:** `-internal`
is the only way this project can compile `CPROC`, `CATALOG` or `LOGIN` outside
an install — §18's commit-2 evidence depends on it — and gating it moves that
instrument behind `sudo`. **The installer is unaffected**: `installsdai.sh:645`
and `:672` already run it under `sudo`.

***AND `check_admin()` ITSELF IS WORTH A SECOND LOOK BEFORE IT IS RELIED ON.***
`sd.c:589` is `geteuid() != 0 && !in_group("admin")`. ***NO `admin` GROUP EXISTS
ON THIS MACHINE*** — `don` is in `sudo`, `wheel` is absent, measured — so the
group arm is dead and the test means "euid 0". Under the owner's definition the
right group to name is `sdadmin`, which is the same answer §18's gate reaches.

## 17. The release stamp — three traps, none of which the C build catches

***THE TWO STAMPS MUST MOVE TOGETHER OR ORDINARY LOGINS STOP.*** `LOGIN:381` is
`if compare(system(1012), SD.REV.STAMP)` — `system(1012)` returns the **C**
value (`op_sys.c:355-358`) and `SD.REV.STAMP` is the **BASIC** one compiled into
`LOGIN`. On a mismatch it displays sysmsg **5029** and ***terminates the
connection*** for any session that is not internal. **That is a machine-level
lock-out, and it is why the BASIC copy is generated rather than typed.**

***AND `GPL.BP/REVSTAMP.H` IS GENERATED, WHICH THE FILE'S OWN NOTE DENIED.*** It
said *"Must manually edit REVSTAMP.H in GPL.BP OR run REVSTAMP in sd"*. The
`REVSTAMP` verb reads `./gplsrc/revstamp.h`, **so it cannot run on an installed
system at all**; `gplbld/gen_includes.py` replaced it, and `make check-includes`
enforces the result. The note is corrected in place.

***TRAP 1 — `gen_includes.py` UNDERSTANDS ONLY ONE-LINE `/* … */` COMMENTS.*** It
turns a line that **opens** a C comment into a BASIC `*` comment and passes every
other line through **unchanged**, so the continuation lines of a multi-line block
comment are emitted as ***bare BASIC***. ***MEASURED: a block comment written
into `revstamp.h` compiled clean in C, PASSED `make check-includes`, and then
gave 17 errors in BOTH `LOGIN` AND `CPROC`*** — every program that includes it.
**Neither the C compiler nor the include check can see this class**; only a
BASIC compile can. The rule is now stated at the top of the file itself.

***TRAP 2 — A COMMENT-OPENING SEQUENCE INSIDE A C COMMENT IS `-Wcomment`.*** The
first attempt at writing trap 1 down quoted the sequence literally and turned a
0-warning build into **13 warnings**. The file is built with `-Wall`.

***TRAP 3 — REGENERATING REWRITES ALL FOUR OUTPUTS AND STAMPS EACH WITH THE
TIME.*** `ERRTEXT.H` and `OPCODES.H` came back modified with **only** their
*"Generated by … at HH:MM:SS"* line changed — `--check` ignores that line, the
writer refreshes it. **Reverted both**, so the commit carries only what actually
changed. ***A `git status` that can be read is an instrument here***; do not let
generator churn into it.

**Verified**: `gen_includes.py --check` watched **failing** (`STALE`, exit 1)
then **passing**; clean `rm -f gplobj/*.o` rebuild **0 warnings**;
`sd --version` → `L1.0-0`; the generated header has **0 bare lines**; `LOGIN`
and `CPROC` **0 errors**, red control 6.

***WHAT THIS WILL DO ON THE NEXT LOGIN, AND IT IS NOT A FAULT.*** `LOGIN:347`
compares the account's own `$RELEASE` VOC record against the stamp, and an
account that already exists still says `1.0-2`. It will display sysmsg **5025**
*"Your VOC is at release level 1.0-2"* and **prompt** *"Update VOC to new
release?"*. **Answer Y** — that is `update.voc`, the designed upgrade path, and
it is how existing accounts take new VOC records. `SDSYS` is rebuilt from
`NEWVOC` by the install and will not ask.

## 18. What "administrator" means — the owner's definition, and the gap to it

***OWNER, 9 Sep 2026:*** *"An administrator is a person who is a member of
sudoers and is also a registered user of SD as an administrator. If they are not
a registered user they should be refused entry."* And: *"that is the current path
in the windows version — you can be a windows administrator and still not have
access to sd."* **So OS privilege is necessary and not sufficient**, which is the
opposite of what this tree implements.

**Measured against that, 9 Sep 2026 — three parts, and only one exists:**

| The definition needs | Today |
|---|---|
| member of **sudoers** | **nothing tests it.** Both admin tests are `getuid() == 0` — `system(27)` (`op_sys.c:222`) in the catalogue gates, and `IsAdmin()` (`linuxlb.c:54-55`) behind `kernel(K$ADMINISTRATOR)`. Root is not sudoers, and a sudoer is not root |
| **registered** in SD as an administrator | ***THERE IS NOWHERE TO RECORD IT.*** `@SDSYS/ACCOUNTS` has three fields — `ACC$PATH` 1, `ACC$DESCR` 2, `ACC$GROUP` 3 (`SYSCOM/KEYS.H:257-260`) — and no tier. Both shipped records carry an empty field 2 |
| unregistered → **refused entry** | ~~**partly there.**~~ ***ESTABLISHED 9 Sep 2026: IT IS WHOLLY THERE, AND THIS ROW WAS WRONG.*** All **three** of `LOGIN`'s account cases read the register and terminate on a miss with sysmsg 5018 — forced `:213`, administrator `:250`, and the default `upcase(@logname)` at `:265`. **Measured with a control**: `sd -ANOSUCHACCT` terminates, `sd -ADON` runs. **And `LOGIN:191-195` is a second, earlier gate** — not in `sdusers`, sysmsg 5009, connection terminated |

***THE PORT ALREADY HAS THE FIELD AND CONFORMITY SAYS TAKE IT:*** its
`syscom/KEYS.H:292,294` define **`ACC$TIER 5`** — STANDARD, PROGRAMMER,
ADMINISTRATOR — and **`ACC$PRIOR.TIER 6`**, the tier SUSPENDED displaced. **Field
4 is skipped in both trees and is retired** (`ACC$USERS`); do not reuse it.

**So the work is §L2, and it is now specified rather than open:** add
`ACC$TIER`/`ACC$PRIOR.TIER` to `SYSCOM/KEYS.H` at 5 and 6, have `CREATEA` write
the tier, replace `system(27) # 0` and `IsAdmin()` with a test that reads the
register **and** checks sudoers membership, and make the login path refuse an
unregistered user rather than only a forced one. **Entry 19 has to be settled
first** — if `kernel(K$ADMINISTRATOR, 1)` grants the flag to any caller, none of
this holds. ***ENTRY 19 IS SETTLED (9 Sep) — it does not.***

### Commit 3, 9 Sep 2026 — the exit from the bootstrap arm

***WITNESSED FIRST: THE 18:20 INSTALL RAN COMMIT 2 AND THE ARM FIRED.*** The
owner's transcript, `sudo /usr/local/sdsys/bin/sd`:

```
No SD administrator is registered: granting rights to don for this session. ...
:who.am.i
User : don   Account : SDSYS   Process UID : 0   Process EUID: 999   Admin? : Yes
```

**Message 10033 by number, naming the person, on exactly the state predicted**:
`ACCOUNTS/DON` tier `STANDARD`, `sdadmin` empty, no `ADMINISTRATOR` anywhere.
`WHO.AM.I` otherwise unchanged. **The `-internal` gate from entry 21 is on the
same install** — measured refusing `don` with exit 1.

***AND THE OWNER READ THE MESSAGE AND FOUND THE DEFECT IN IT. HIS WORDS: "ONLY
ADMINISTRATORS CAN CREATE ACCOUNTS SO KINDA IMPOSSIBLE."*** It is worse than the
circularity he names, and the sharper half is not visible from the message:
***`CREATEA:255` REFUSES A NAME ALREADY IN THE REGISTER*** with sysmsg 6002, and
***`MODIFYA` HAD ZERO REFERENCES TO `ACC$TIER`*** — checked, not assumed. So for
**anyone who already had an account**, which is everyone who matters, the only
route to ADMINISTRATOR was `DELETE.ACCOUNT` and its data loss. **The arm could
never close, and nothing in the gate itself would have shown that.**

**Built — `MODIFY.ACCOUNT <account> STANDARD | PROGRAMMER | ADMINISTRATOR`:**

| | |
|---|---|
| `MODIFYA` `set.tier` | writes `ACC$TIER`, then reconciles `sdadmin` — register first, group second, because the register is the record and the group is a consequence of it |
| `MODIFYA` `join`/`leave.sdadmin` | mirror `CREATEA:377-390` and the existing DELETE arm rather than inventing a second way; `valid_os_name` guards the shell in both |
| `MESSAGES/10035`, `10036` | the result, and the refusal for an account with no person |

***THE GRAMMAR IS THE PORT'S MINUS `SUSPENDED`, AND THAT OMISSION IS DELIBERATE.***
The port has `STANDARD | PROGRAMMER | ADMINISTRATOR | SUSPENDED`
(`sd4windows` `gpl.bp/MODIFYA:121`). **SUSPENDED denies access**, and the doors
it must close — `LOGIN`, `CPROC`'s account entry, ssh — are `PRE_RELEASE` 13 and
are not built here. **A SUSPENDED that wrote a tier and shut no door is a
control that does not act**, which the port's own record rules against.

***THE PERSON IS DERIVED FROM `ACC$GROUP`, NOT FROM THE ACCOUNT NAME***, because
`CREATEA:439` writes `sdu_<login>` and that is the only place the record carries
the login. **A GROUP or OTHER account has no person, so ADMINISTRATOR is refused
with 10036** rather than writing a tier nothing could act on; STANDARD and
PROGRAMMER are allowed, since `CREATEA` writes a tier for every account type.

***NOBODY CAN LOCK THE MACHINE OUT WITH IT, AND THAT IS THE BOOTSTRAP ARM
EARNING ITS KEEP.*** Demoting the last administrator — yourself included —
leaves the register with none, so the arm starts firing again on the next
privileged session. **Worth knowing before anyone adds a "you may not demote
yourself" rule.**

***A SECOND DEFECT THE OWNER CAUGHT IN THE SAME BREATH, AND IT IS THE MORE
INSTRUCTIVE ONE: THE COMMAND STRING IN 10033 WAS WRONG.*** It read
`CREATE.ACCOUNT name path ADMINISTRATOR`. ***THE VERB HAS REQUIRED
`USER`/`GROUP`/`OTHER` SINCE rev 0.9.0 AND ONLY `OTHER` TAKES A PATHNAME*** —
the syntax it prints at `CREATEA:246` says so. **The wrong string was copied
from `CREATEA`'s own `START-DESCRIPTION`, which still carried the pre-0.9.0
form — and the port's copy of that block is stale in exactly the same way.**
Corrected in this tree with the reason attached. ***THE LESSON IS NOT "CHECK THE
SYNTAX": IT IS THAT A COMMENT BLOCK IS NOT AN INSTRUMENT.*** The verb prints its
own grammar and that is what was true; the block was commentary and had drifted,
in both trees, unnoticed. **10033 now names `MODIFY.ACCOUNT`, which is the
reachable route, and says the rights are already granted for this session.**

***A CONFORMITY GAP NAMED WHILE CHECKING***: the port's documented grammar is
`create.account user <name> {administrator | programmer}
<ssh | api | both | none> {no.query}`, with the remote-access keyword
**required** for a user account
(`SDCoreWindowsDocs/Administrator/markdown/01-accounts-and-security.md:55`).
**This tree has no such keyword** — that is `PRE_RELEASE` 13, unbuilt. Absent
rather than optional, and recorded so it is not mistaken for a difference of
opinion.

***COMPILED, WITH A CONTROL AND A RED THAT HAD TO BE FIXED TO BE RED.***
`MODIFYA` edited **0 errors**, `MODIFYA` at HEAD **0 errors**, `CREATEA` edited
**0 errors**. ***THE FIRST RED CONTROL PASSED AND WAS THEREFORE VOID***: cutting
`MODIFYA` at line 70 landed inside the header, leaving a valid empty program
that compiled clean — **the null case, caught by its own control**. Re-cut at
line 152 of 292, inside the ADD/DELETE nest: ***9 errors***. Fixtures removed.
*(The `COUNT VOC` 411 this line used to cite was not a clean baseline — see the
withdrawal in commit 2 above. The account's true empty count is **410**.)*

***WITNESSED END TO END 9 Sep 2026 — THE ARM CLOSED ITSELF.*** The owner's
transcript, in one sitting:

```
$ sudo /usr/local/sdsys/bin/sd
No SD administrator is registered. Rights granted to don for this session ...
:MODIFY.ACCOUNT DON ADMINISTRATOR
don added to sdadmin, and may now use the SD privileged helper
Account DON is now ADMINISTRATOR
:OFF
$ sudo sd
:who.am.i          User : don   Process UID : 0   EUID: 999   Admin? : Yes
```

***THE SECOND SESSION PRINTED NO 10033, AND THAT ABSENCE IS THE MEASUREMENT.***
10033 is the bootstrap arm's **only** voice, so the rights on that second
session came from the register and the group rather than from the arm.

***BOTH HALVES WERE THEN READ OFF DISK INDEPENDENTLY RATHER THAN INFERRED FROM
THE SCREEN***: `ACCOUNTS/DON` field 5 is `ADMINISTRATOR`, `getent group sdadmin`
is `sdadmin:x:965:don`, and **exactly one** register record holds
`ADMINISTRATOR`. **`MESSAGES/10033` is present in the installed tree**, so its
silence is a real absence and not a missing message file.

***ENTRY 14's HANG DID NOT REACH THIS PATH, AND THE REASON MATTERS MORE THAN THE
RESULT.*** `join.sdadmin` shells `sudo usermod -aG sdadmin` with no `-n`, and it
returned without a password prompt — **because the session is uid 0, so sudo
does not challenge.** That is not evidence the ten call sites in §14 are safe;
it is evidence this one runs on a path where the question never arises.

***WHAT IS STILL UNWITNESSED, AND ONE OF IT IS A CONTROL THAT MATTERS.***

- **`leave.sdadmin` has never run.** `MODIFY.ACCOUNT DON PROGRAMMER` would
  exercise it and is reversible.
- **`leave.sdadmin` has still never run.** `MODIFY.ACCOUNT DON PROGRAMMER`
  would exercise it.

### The refusal control — run by the owner 9 Sep 2026, and it passed both ways

***THE GATE HAS NOW BEEN WATCHED REFUSING, WHICH IS THE HALF THAT MAKES IT A
CHECK.*** He dropped himself from `sdadmin` and **left the tier at
`ADMINISTRATOR`**, so only one half of the owner's definition changed.

| | 10033 | 10034 | `Admin?` | `Account` |
|---|---|---|---|---|
| bootstrap arm | ✓ | — | Yes | `SDSYS` |
| ***dropped from `sdadmin`, tier untouched*** | ***—*** | ***✓*** | ***No*** | ***`DON`*** |
| restored with `gpasswd -a` | — | — | Yes | `SDSYS` |

***10033 CORRECTLY STAYED SILENT***, which is the discriminating observation: an
`ADMINISTRATOR` was still registered, so the bootstrap arm had no business
firing, and it did not. **The gate refused on the group half alone with the
register half held constant** — that is the `AND`, tested rather than argued.

***AND `Account : DON` IS A FOURTH CONFIRMATION NOBODY PREDICTED IN ADVANCE.***
With `USR_ADMIN` clear, `LOGIN:240`'s `case kernel(K$ADMINISTRATOR,-1)` stops
matching and `:259` sends the session to `upcase(@logname)` instead of `SDSYS`.
**The account name on the screen is an independent readout of the same flag**,
and it moved in step with it.

### The refusal named the wrong half — fixed 9 Sep 2026

***THE MESSAGE SAID "don is not a registered SD administrator" AND HE WAS
REGISTERED.*** Field 5 still read `ADMINISTRATOR`; what he lacked was the group.
**A refusal that names the wrong half sends the reader to the wrong place** — an
administrator dropped from `sdadmin` would inspect the register, find it
correct, and have nothing left to look at. ***THIS IS THE SAME CLASS THE OWNER
CAUGHT IN 10033's COMMAND STRING, FOUND THE SAME WAY: BY READING WHAT THE THING
ACTUALLY PRINTED.***

The definition has two halves, so there are now three refusals rather than one:

| | |
|---|---|
| `10034` | not registered as an administrator |
| ***`10037`*** | **registered, but not in `sdadmin`** — the case above |
| ***`10038`*** | ***the register could not be READ*** |

***10038 IS THE THREE-ANSWER PROBLEM AND IT WAS THE SAME BUG WEARING A DIFFERENT
HAT.*** The unreadable-register arm also printed 10034 — *"is not a registered
administrator"* — which is a claim about what the register **says** when nothing
had been read. **Conflating "measured false" with "could not measure"** is what
§20 warns about and what the port paid for in its entry 93. The verdict is
unchanged (nothing measured, nothing granted); only the wording is now honest
about why.

**Compiled**: edited `CPROC` **0 errors on both `IS_INSTALL` arms**; red control
cut at line 903 of 3618, inside an open `loop`, **8 errors**.

### Where the notice appears — the owner's shape, 9 Sep 2026

***HE READ HIS OWN TRANSCRIPT AND SAW THAT THE MESSAGE LANDED ABOVE THE SIGN-ON
BANNER, "SO IT JUST LOOKS LIKE PART OF THE BANNER THAT PEOPLE ARE USED TO
IGNORING".*** That is the failure mode these messages exist to avoid — **a
warning nobody reads is not a warning** — so the presentation is part of the
mechanism, not decoration.

The notices are now **collected rather than printed** (`admin.notice`, one per
field) and displayed after `$LOGIN` returns, which is after the banner:

```
<banner>
<blank line>
------------------------------------------------------------------------------- (79)
don is not registered ...
-------------------------------------------------------------------------------
<blank line>
```

| | |
|---|---|
| the gap above | **the banner's own** — `LOGIN:170` already ends with a blank `display`, so it is not doubled |
| the rule width | **79, because the banner's widest line is 79** (`LOGIN:169`, measured) — the box reads as part of the same block and still fits 80 columns |
| `CMD.QUIET` | ***does NOT suppress it***, unlike the banner. The banner is a courtesy; this is the session saying what rights it has. A quiet flag should not be able to silence that |
| 10032 | **moved too.** It is the same class — a start-up notice about privilege — and it had the same defect |

**Compiled again after the move: 0 errors on both arms, red control at line 903
of 3665 gives 10.** ***CLEANED UP PROPERLY THIS TIME***: fixtures, `BP.OUT`, and
`DELETE VOC BP.OUT` — `COUNT VOC` back to **410**, the true baseline.

### Commit 2, 9 Sep 2026 — the gates

***THE GRANT IS GATED, NOT THE FOURTEEN READERS, AND THAT IS THE WHOLE DESIGN.***
`CPROC` is the **only** place `USR_ADMIN` is ever set — every other
`K$ADMINISTRATOR` site in `GPL.BP` reads it with `-1`, checked. So the owner's
definition is applied once, at the grant, and the readers keep asking the flag.
One test cannot then fall out of step with another.

| Where | What |
|---|---|
| `CPROC` `grant.administrator` | the test: `sdadmin` membership **and** `ACC$TIER`=`ADMINISTRATOR` on the person's own record, keyed on the `K$REAL.USER` `@logname` from piece 1 |
| `CPROC` (root entry) | `void kernel(K$ADMINISTRATOR,1)` → `gosub grant.administrator`, with the `IS_INSTALL` arm keeping the old unconditional grant |
| `CPROC` (`LOGTO SDSYS`) | `system(27) > 0` → `not(kernel(K$ADMINISTRATOR,-1))` |
| `CATALOG` (2 sites), `DELCAT` (1) | `system(27) # 0` → the flag. `DELCAT` gains `$include int$keys.h` |
| `MESSAGES/10033`, `10034` | the bootstrap notice and the refusal. 131 and 81 bytes against 231 |
| `gplsrc/linuxlb.c`, `op_kernel.c` | **`IsAdmin()` deleted** |

***THE RECORD MUST BE THE PERSON'S OWN, AND THAT IS A REAL CHECK RATHER THAN
BELT AND BRACES.*** The register is keyed by ACCOUNT name, so `ACC$GROUP` is
required to equal `sdu_<person>` (`CREATEA:439` is what writes it) — otherwise a
GROUP or OTHER account carrying a person's name would satisfy the gate.
**`ROOT` needs no special case**: `CREATEA:144` refuses it as an account name, so
no `ROOT` record can exist and the lookup simply fails. **`SDSYS` DOES need
one**, and it is the arm §20 named: with no source able to name the person,
`logname` stays `sdsys`, and `sdsys` is an account, not a person.

***THE BOOTSTRAP ARM IS THE OWNER'S RULING OF 9 Sep 2026, AND IT WAS ASKED FOR
BECAUSE THE STRICT GATE LOCKS THE MACHINE.*** ***MEASURED ON THE 16:22 INSTALL
BEFORE ANY OF THIS WAS WRITTEN***: `ACCOUNTS/DON` is
`/home/sd/user_accounts/don`, blank, `sdu_don` — **three fields, so no tier** —
and `sdadmin:x:965:` has **no members**.

***THAT READING IS SUPERSEDED AND THE CONCLUSION IS NOT. RE-MEASURED ON THE
17:53 INSTALL***: `ACCOUNTS/DON` now carries **five fields, `ACC$TIER` =
`STANDARD`** — ***which is commit 1's write path running on a live system, and
is the only witness this file has for it***. `sdadmin` is **still empty** and
**no account holds `ADMINISTRATOR`**. So the lock-out argument is unchanged: a
strict gate refuses `don` on the register half (STANDARD is not ADMINISTRATOR)
*and* on the group half. **The blank-tier reading was never the load-bearing
part; "nobody is registered as an administrator" was.**

A strict gate refuses on both halves,
and `CREATEA:95` needs administrator rights to register the first
administrator: a lock-out with no exit. So when the register holds **no**
`ADMINISTRATOR`-tier account at all, the grant stands and prints 10033. **The
arm closes itself the moment one is registered**, and it is not a widening — it
is exactly the behaviour that stood before this change, kept only while there is
nobody to gate on. **A register that will not open is refused rather than read
as "nobody is registered", because that answer grants.**

***OBJECTION, RECORDED RATHER THAN RESOLVED***: the bootstrap arm grants to an
**unknown** identity too, which §20 said a gate must never do. Refusing there is
the tidier rule and is also the one arm that could leave a box with no
`SUDO_USER` and no utmp entry unadministerable. **The lock-out risk decided it.
It is a deliberate under-reach, not an oversight.**

***AND THE BASIC WAS COMPILED FOR REAL, WHICH THIS PROJECT HAD NOT MANAGED
BEFORE.*** Commit 1 could only do a "controlled comparison" of error classes.
The recipe is the port's, at `HISTORY.md:18916`, and the missing piece was
`-internal`: **`sd -internal BASIC <file> <prog>`, arguments separate, no pipe.**
Fixtures — the edited program plus all twelve `$include` records, taken from the
**working tree** so `ACC$TIER` and `K$REAL.USER` resolve — were staged in the
`DON` account's empty `BP` and compiled as `don`, **unprivileged**.

***THAT LAST WORD IS ALREADY OUT OF DATE AND THE RECIPE NOW NEEDS `sudo`.***
Entry 21, fixed the same day, puts `-internal` behind `check_admin()`. **The
recipe is otherwise unchanged**, and the runs recorded below were taken before
that fix, on a binary that still accepted the flag — which is the same reason
they are valid: they measured the compiler, not the gate.

| Run | Result |
|---|---|
| `CPROCT`, `IS_INSTALL` **off** (the `grant.administrator` arm) | **0 error(s)**, *"Compiled 1 program(s) with no errors"* |
| `CPROCT`, `IS_INSTALL` **on** | **0 error(s)** |
| `CPROCH` (HEAD's `CPROC`), same way — the control | **0 error(s)** |
| `CATALOGT` / `CATALOGH`, `DELCATT` / `DELCATH` | **0 error(s)** each |
| ***`CPROCX`, deliberately truncated at line 400 — THE RED CONTROL*** | ***10 error(s)***, *"Compiled 1 program(s) with errors in:"* |
| the same `CPROCT` **without** `-internal` | ***the port's exact cascade***, `Unrecognised compiler directive` on `$internal` then ~30 errors downstream |

***SO THE INSTRUMENT HAS BEEN WATCHED FAILING TWICE AS WELL AS PASSING, AND IT
ANCHORS ON THE POSITIVE WORDING*** — `0 error(s)` and *"with no errors"* are
`BCOMP:1540` / `BASIC` on the success path; the failure path prints `N error(s)`
and *"with errors in:"*. **Fixtures removed by name**; the `DON` account is back
to its seven entries with `BP` empty and no `BP.OUT`.

***THE `COUNT VOC` CLAIM THAT USED TO END THIS PARAGRAPH WAS WRONG AND IS
WITHDRAWN.*** It read *"`COUNT VOC` is 411 with the fixtures gone as it was with
them there, so nothing reached the VOC."* ***THE FIRST COMPILE HAD ALREADY
CREATED A `BP.OUT` VOC RECORD BEFORE THAT "BASELINE" WAS TAKEN***, so 411
included the litter and the two readings agreed on a number that was already
wrong. **The unchanged count was real; the conclusion drawn from it was not** —
a before-and-after taken entirely after the event measures nothing. Found
9 Sep 26 when a later compile failed with *"DATA part of file already exists /
Unable to open newly created output file"*: the directory had been removed and
the VOC record had not. ***CLEANED FOR REAL***: `DELETE VOC BP.OUT`,
**1 record deleted**, and `COUNT VOC` is now **410**. **That is the true
baseline for this account, and it is one BELOW the number two entries in this
file were quoting.**

***WHAT IS STILL NOT ESTABLISHED: NONE OF IT HAS RUN.*** A compile is not an
install. The witness is an install of `origin/main` followed by `sudo sd` — it
should print **10033** and name `don`, because no `ADMINISTRATOR` account exists
yet, and `WHO.AM.I` should still say `Admin? : Yes`. **If it prints 10034
instead, the register lookup failed and the account is unadministerable until
the record is hand-edited.**

***AND ONE THING FOUND WHILE BUILDING IT THAT IS BIGGER THAN IT: ENTRY 21.***
The gate decides who gets `USR_ADMIN`, and `sd -internal` lets any user set that
flag directly — **measured, uid 1000, no sudo**. Read 21 before believing this
entry closes anything.

### Half built, 9 Sep 2026 — the register records a tier; nothing reads it

**Commit 1 of two.** `SYSCOM/KEYS.H` gains `ACC$TIER` **5** and
`ACC$PRIOR.TIER` **6**, and `CREATEA` takes `ADMINISTRATOR`/`PROGRAMMER` and
writes field 5 for every account type.

***FIELD 4 IS SKIPPED FOR A DIFFERENT REASON THAN THE PORT'S, AND THE
DIFFERENCE IS WORTH KEEPING.*** The port must skip it: records written there
between 13 and 14 Aug 26 carry a retired grant list, so a new meaning would read
old data as new. ***HERE FIELD 4 WAS NEVER WRITTEN*** — `ACC$USERS` survives
only as a history line, the define was never present, and the one shipped record
`ACCOUNTS/SDSYS` has **three** fields (checked, not assumed). **So field 4 is
genuinely free here and is left free anyway, for conformity** — the two
`ACCOUNTS` layouts stay comparable. A later session must not "reclaim" it.

**Keywords are matched on token text, not a `KW$` constant** — `PARSER.H`'s
numbers are a positional table shared by every verb, so adding one for a single
verb is the larger change. **The cost is that they cannot be abbreviated.**
`STANDARD` is the default and is *not* a keyword; `ADMINISTRATOR` wins over
`PROGRAMMER` in either order, so a later `PROGRAMMER` cannot silently downgrade.

***WHAT THIS HALF DOES NOT DO, AND IT IS MOST OF IT.*** Nothing reads field 5 —
the gates are commit 2 — and **every account still gets the same VOC**, because
the per-tier VOC delta is §L1 and is not designed. **A tier recorded here does
not yet change what an account may do.**

***THE COMPILE CHECK WAS BOUNDED AND SAYS SO.*** `CREATEA` is `$internal`, so an
ordinary account cannot compile it — `INT$KEYS.H` is internal-only. What was run
instead is a **controlled comparison**: HEAD's `CREATEA` and the edited one
compiled the same way, and the error classes are **identical** (`INT$KEYS.H not
found`, `$CATALOG`, `@ variable as lvalue`), every one landing on a
**pre-existing** `@system.return.code` line and **none on a line this change
added**. The one extra `@` row is the same error set shifted by the comment
lines (offset +21, checked). ***THAT IS NOT A COMPILE; THE INSTALL'S TWO-STAGE
BOOTSTRAP IS STILL THE ONLY REAL ONE***, and a syntax error there aborts the
install, which is the loud failure this relies on. Fixtures removed —
`COUNT VOC` 410 before and after.

## 13. ssh is an unguarded way past the tier model

***RAISED BY THE OWNER, 9 Sep 2026, AS A CHALLENGE TO A CLASSIFICATION*** — *"we
will be using ssh here so why is there no counterpart"* — and the answer turned
out to be bigger than the misfiling.

**Three measurements, none of them inferred:**

1. **The installer installs an ssh server on every distribution** —
   `installsdai.sh:254` (`openssh`), `:272` and `:285` (`openssh-server`), `:295`
   (`openssh`) — and the Arch branch **starts and enables `sshd`** at `:265-266`.
2. **An SD user is an ordinary Unix user with a login shell.** `CREATEA:331` runs
   `usermod -aG sdusers <name>` on an account that **already exists**; it does not
   create one and does not set a shell, so the account keeps whatever `adduser`
   gave it.
3. ***NOTHING IN THIS PROJECT WRITES `AllowGroups` OR `ForceCommand`.*** Grep
   across `installsdai.sh`, `deletesdai.sh` and all of `GPL.BP`: **zero hits.**

**So the tier boundary §L1 draws does not hold at the edge of the machine.** A
STANDARD account is denied `SH` and `!` inside SD, and then reaches a shell by
running `ssh` — never entering SD at all. **The port measured this exact failure**
on 21 Aug 2026, on a machine found with a stock `sshd_config`: *"no AllowGroups
and, worse, no ForceCommand, so an sdsshonly account got a PowerShell prompt."*
Here it is not a regression to guard against; **it is the state the installer
leaves behind.**

***THE PLAN EXCLUDES THIS BY NAME AND THE EXCLUSION IS TOO BROAD.*** Line 17
lists *"elevation, Windows groups and ACLs, the firewall, OpenSSH"* and says
**"None of it applies here"**; §H:854 repeats *"OpenSSH install/removal"*. What
those name is install/removal, which genuinely is Windows-only. **The ssh-only
account model is neither named nor considered anywhere in the plan** — `ssh`
appears on 4 lines of ~1,600.

***AND §L5 IS RIGHT ABOUT WHAT IT ADDRESSES, WHICH IS WHY THE GAP IS EASY TO
MISS.*** It argues that reaching a shell is *"a policy question, not a
privilege-escalation one"* here, because `sd` is not setuid so `SH` hands the
person a shell **as themselves**. That reasoning is sound — and it is entirely
about reaching the shell **from inside SD**. ssh reaches it from outside, with
SD absent from the path, and §L5 never considers it. **The conclusion "then
`os.users` is not needed and §L1 is the whole of the answer" does not survive
that.**

***RULED 9 Sep 2026: A STANDARD ACCOUNT DOES NOT GET A REAL LOGIN SHELL — THE
TIER IS TO BE A BOUNDARY.*** Chosen by the owner from the three offered;
**recorded as a selection, not as his words.** So the answer to this section's
first bullet is *no*, and `ForceCommand` or a restricted shell is the fix rather
than a documentation change.

***THAT DECIDES THE THIRD BULLET TOO: SD MUST WRITE TO `sshd_config`.*** There
is no way to hold the boundary without it. **The port's answer is the model to
copy** — an explicit, removable fenced block, plus a preflight that **refuses**
when someone else has written the file, rather than editing an administrator's
configuration silently. `allow-ssh-groups.ps1` writes exactly these directives
and is the one port script that transfers almost literally (entry 1).

**Still to decide inside the ruling** (it fixes the direction, not the
mechanism): whether the restriction is `ForceCommand` into `sd`, a restricted
login shell, or `AllowGroups` excluding STANDARD; and what PROGRAMMER gets,
which this ruling did not cover. ***AND THE MEASUREMENT BELOW IS WHAT THE FIX
WILL BE CHECKED AGAINST***: today every SD account has a real shell, so a
verifier for this has a known-bad starting state to prove it moved away from.

**What has to be decided, and it belongs with §L rather than after it:**

- Do SD accounts get a **real login shell** at all? If the answer for STANDARD is
  no, that is `ForceCommand` or a restricted shell, and it is the whole fix.
- If yes, then **§L1's verb withholding is a convenience, not a boundary**, and
  the documentation must say so rather than implying containment.
- Either way, **does SD write to `sshd_config`?** Doing so silently to a file the
  administrator owns is worse than not doing it; the port's answer was an
  explicit, removable fenced block plus a preflight that refuses when someone
  else has written the file.

### Ruled 9 Sep 2026 — the mechanism, PROGRAMMER, and who writes it

Owner's selections this session, recorded as selections. **Not built.**

- **Mechanism: `ForceCommand` into `sd`.** A fenced `Match Group sdusers,!sdadmin`
  block forces every non-administrator SD account into `bin/sd` on ssh login — no
  path to a bare shell from outside SD. `sshd` Match-Group negation matches a
  member of `sdusers` who is NOT in `sdadmin`; ***verify it with `sshd -t` on the
  target's sshd version before any install*** — this is the lock-out-sensitive
  line.
- **PROGRAMMER is treated as STANDARD over ssh**: forced into SD, no direct remote
  shell. The tiers are distinguished by the in-SD permission model (PRE_RELEASE
  23), not by sshd.
- **Administrators keep a real login shell** — they are in `sdadmin`, the negation
  excludes them, and that is their "full ssh access" (owner's phrase, 9 Sep 26).
- **The INSTALLER writes the fenced block**, with a preflight that REFUSES when the
  administrator has already customised `sshd_config` rather than editing it
  silently. The port's `allow-ssh-groups.ps1` is the model (entry 1).

***CONSEQUENCE, REASONED NOT WITNESSED:*** because `sd` is not setuid
(`system(27)` = `getuid()`, `op_sys.c:222`), an admin-granted non-admin (via
`MODIFY.ACCOUNT SH-ON`, PRE_RELEASE 23) ssh's in → `ForceCommand` lands them in
`sd` → `SH` gives them a shell **as themselves**. So the grant lives entirely
inside SD's permission model and needs NO per-user `sshd_config` carve-out; the
fenced block stays one uniform group rule, which is why "installer writes it"
beats "a verb writes per-account". This is the least-tested claim here and is what
the first ssh witness must check.

### Measured on this machine, 9 Sep 2026

| | |
|---|---|
| shells of `sdusers` members | `don` **`/bin/bash`**, `sdsys` **`/bin/sh`**, `root` `/bin/bash` — ***every SD account has a real login shell***, none is `nologin` |
| `AllowGroups`/`ForceCommand` written by this project | **0** (installer + all of `GPL.BP`) |
| `sshd` on this box | **inactive** — installed, not running |

***SO THE FIRST BULLET ABOVE IS ANSWERED FOR THE PRESENT STATE: SD ACCOUNTS DO
GET A REAL LOGIN SHELL, AND NOTHING RESTRICTS IT.*** §L1's verb withholding is
therefore **a convenience, not a boundary**, exactly as the second bullet
warns — and that is now measured rather than argued.

**One thing the measurement does NOT establish**, written in the conditional:
`sshd` being inactive here makes the exposure **latent on this box, not
absent**. The Arch branch starts and enables it (`installsdai.sh:265-266`), and
any administrator may start it on any distribution; **an inactive daemon is a
property of this machine today, not of the product.**

**Related verifiers that exist there and nowhere here:** `verify-sshonly`,
`verify-sshadmin`, `verify-allowgroups`, `probe-sshfirewall`,
`probe-sshpreflight`, `probe-sshremote` — the last of which is the one that
proved the scoping actually blocks a **remote** machine, host to guest, because
NAT could not show it.

## 12. Getting `sdbasic.yaml` to where micro looks

**Measured on the development machine, 9 Sep 2026:** micro **2.0.15**, its
configuration directory is `~/.config/micro`, and there is **no
`/usr/share/micro`** — stock micro has no system-wide syntax path. So the file
has to land in a **per-user** directory, and `installsdai.sh` runs under `sudo`
and cannot populate the home of every user who will ever run SD.

Three shapes, and the first is recommended:

1. ***`MICRO` PLACES IT ON FIRST USE.*** Before launching, copy the shipped
   `sdbasic.yaml` into `$HOME/.config/micro/syntax/` if it is absent or older.
   Per-user, needs no privilege, self-heals for accounts created later, and
   leaves the user's own micro settings alone. **Closest to the port**, whose
   `micro-home.ps1` solved the same problem by giving the caller a config home.
2. **The installer seeds it** for existing users and the skeleton profile.
   Misses every account created afterwards.
3. **`MICRO` passes `-config-dir`** at a shared location. Works, but **bypasses
   the user's own micro configuration**, which is theirs and not SD's to
   override.

***UNTIL THIS LANDS THE FEATURE IS INERT, AND INERT LOOKS EXACTLY LIKE
WORKING*** — `checksyntax.py`'s own header makes the point: micro reports a
syntax file it cannot use by simply not highlighting, which is what a file it
never found looks like too. **Whoever does this must check highlighting on a
real record, not just that the file was copied.**

## 9. Porting `check-stale-leads.py`

***THE ESTIMATE IN THIS ENTRY'S FIRST DRAFT WAS WRONG AND IS KEPT AS THE
CORRECTION.*** Reading the source suggested only phase 2 was coupled to the
port's documents, so adding this file plus a phase-2 fix would be enough.
**Running it says otherwise:** copied verbatim into `gplbld/` and run with no
arguments, it exits **2 immediately** —

```
REFUSING - could not bound section 7 (found %r..%r).  The headings
  may have been renamed; fix this rather than scanning everything.
```

— before phase 1. The entry-boundary machinery every phase depends on is built
from the port's own headings.

**The first column below is deliberately not a bare number.** `phase 1` rather
than `1`, because phase 4's index regex is `^\| *(~~)? *(\d+)`, and a detail
table whose rows start with a digit is counted as index rows — this table did
exactly that in draft and inflated the count from 11 to 15.

| | Reads | Here |
|---|---|---|
| bounds | "section 7" and the `> ### N.` START HERE items, to find where entries begin | ***refuses; neither exists*** |
| phase 1 | status words within one entry, `OPEN_PAT`/`CLOSE_PAT` | needs the boundaries above |
| phase 2 | the task table against the entries, both directions | its `ROW` regex wants `\| ✅ \| **N.Nx** \|`; **no such table here** |
| phase 3 | an entry that records something and then denies it | needs the boundaries above |
| phase 4 | this file's index rows, `^\| N \|` | **this file now satisfies it** |

***CREDIT WHERE IT IS DUE: EVERY ONE OF THOSE IS A REFUSAL, NOT A CLEAN RUN.***
Phase 2 refuses on zero rows (its line 438), phase 4 on zero index rows (663),
and the boundary step refuses rather than scanning the whole file. The port
built the null-case guards this project's CLAUDE.md asks for, which is why a
verbatim copy fails honestly instead of scoring green.

**So the work is an adaptation, not a copy**, and its scope is: decide what an
"entry" is in *this* PROJECT_STATUS, re-point the boundary detection at it,
either retire phase 2 or give this project the table it needs, and drive the
result against a fixture — the port ships `test-staleleads-units.py` precisely
so a dead scan cannot score clean.

**The fault it looks for is not hypothetical here.** On 9 Sep 2026
PROJECT_STATUS gained a step-4 note headed *"THE LOWER-CASE MIGRATION WAS NOT
FOLDED INTO STEP 4 … IS WITHDRAWN"* whose body said the opposite of what the
heading implied. **The owner caught it, not the tooling** — which is the
argument for doing this adaptation rather than shelving it.
